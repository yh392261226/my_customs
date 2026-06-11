"""
智能书籍重复检测器 V3 - 基于Ultra架构的完整实现

【设计理念】：
1. 100%兼容Ultra的所有功能和接口
2. 完整实现4级检测流程（哈希→SimHash→深度内容→文件名）
3. 兼容batch_callback格式：(groups, batch_index, total_batches, processing_remaining)
4. 正确处理空结果（不弹窗，只通知）
5. 推荐删除功能正常工作
6. 在此基础上进行智能优化（不是推翻重来）

【与Ultra的关系】：
- V3 = Ultra + 智能优化层
- 保留所有Ultra已验证的逻辑
- 新增多维度加权评分作为辅助验证
- 可通过配置切换"纯Ultra模式"或"增强模式"

【核心改进】：
1. 包含关系检测增强（针对1-N章场景）
2. 内容采样量增加（30000字符 vs Ultra的15000）
3. 多尺度滑动窗口算法
4. TXT专用优化（自动过滤非txt文件）
"""

import os
import hashlib
import math
import re
import time
from typing import List, Dict, Tuple, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 【修复】添加TYPE_CHECKING以支持类型注解的前向引用
if TYPE_CHECKING:
    from src.core.book import Book

# 【修复】添加全局logger（与Ultra保持一致）
from src.utils.logger import get_logger
logger = get_logger(__name__)


# ============================================================================
# 第一部分：数据结构定义（完全兼容Ultra）
# ============================================================================

# 【新增】常见网站/来源前缀列表（用于文件名标准化）
SOURCE_PREFIXES = [
    '成人小说网_', '龙腾小说网_', 'AA阅读_', '晋江_', '起点中文网_', '纵横中文网_',
    '17k小说_', '小说阅读网_', '书旗小说_', '番茄小说_', '七猫小说_',
    '掌阅_', 'QQ阅读_', '豆瓣_', '知乎_', '百度_', '搜狗_',
]

class DuplicateType(Enum):
    """重复类型（与Ultra完全相同）"""
    FILE_NAME = "文件名相同"
    CONTENT_SIMILAR = "内容相似"
    HASH_IDENTICAL = "哈希值相同"
    CONTENT_SUBSET = "内容子集"
    SIMHASH_SIMILAR = "SimHash相似"


@dataclass
class DuplicateGroup:
    """重复书籍组（与Ultra完全相同的结构）"""
    duplicate_type: DuplicateType
    books: List['Book']
    similarity: float = 0.0
    recommended_to_keep: Optional[List['Book']] = None  # 【修复】改为 Optional
    recommended_to_delete: Optional[List['Book']] = None  # 【修复】改为 Optional
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.recommended_to_keep is None:
            self.recommended_to_keep = []
        if self.recommended_to_delete is None:
            self.recommended_to_delete = []


@dataclass
class BookFingerprint:
    """书籍指纹信息"""
    book: 'Book'
    file_hash: str = ""
    simhash: int = 0
    size_features: Tuple[int, int, int] = (0, 0, 0)
    title_keywords: Set[str] = field(default_factory=set)
    content_sample: str = ""
    normalized_name: str = ""
    
    # V3新增字段（不影响Ultra兼容性）
    detected_encoding: str = ""
    chapter_markers: List[str] = field(default_factory=list)


@dataclass
class BookComparison:
    """书籍比较结果（用于深度内容检测返回）"""
    book1: 'Book'
    book2: 'Book'
    file_name_match: bool = False
    similarity: float = 0.0
    hash_match: bool = False
    duplicate_types: List[DuplicateType] = field(default_factory=list)
    confidence: float = 0.0


# ============================================================================
# 第二部分：核心检测器（Ultra架构 + 增强功能）
# ============================================================================

class SmartDuplicateDetectorV3:
    """
    智能书籍重复检测器 V3 - Ultra完整实现版 + 增强功能
    
    【架构说明】：
    本检测器严格遵循Ultra的4级检测流程：
    
    Level 0: 文件哈希匹配 (progress: 10%)     → DuplicateType.HASH_IDENTICAL
    Level 1: SimHash检测   (progress: 30%)     → DuplicateType.SIMHASH_SIMILAR  
    Level 2: 深度内容检测 (progress: 60-95%) → DuplicateType.CONTENT_SIMILAR / CONTENT_SUBSET
    Level 3: 文件名兜底     (progress: 100%)    → DuplicateType.FILE_NAME
    
    【与Ultra的差异】：
    ✅ 完全兼容Ultra的所有接口和返回格式
    ✅ batch_callback格式: (groups, batch_index, total_batches, processing_remaining)
    ✅ 空结果处理正确（不弹窗，只通知）
    ✅ 推荐删除功能正常工作
    ⚡ 增强功能（可通过配置启用/禁用）
       - 更大的内容采样(30000字符)
       - 多尺度包含关系检测
       - TXT专用过滤
       - 【V5新增】智能文件名标准化(去除来源前缀、副标题)
       - 【V5新增】文本归一化(消除格式差异)
    """
    
    # 【新增】静态方法：智能标准化书籍文件名（解决类型①②③⑤）
    @staticmethod
    def _normalize_book_name(file_name: str) -> str:
        """
        智能标准化书籍文件名，去除来源前缀、副标题等噪声
        
        处理规则：
        1. 去除常见网站/来源前缀（成人小说网_、龙腾小说网_等）
        2. 去除括号内的副标题（如（妖刀记前传）、(全集)等）
        3. 去除文件扩展名
        4. 统一空格和特殊字符
        
        示例：
        - "成人小说网_黄蓉智斗群雄之饮鸩止渴.txt" → "黄蓉智斗群雄之饮鸩止渴"
        - "AA阅读_鱼龙舞（妖刀记前传）.txt" → "鱼龙舞"
        - "龙腾小说网_高考后的假期.txt" → "高考后的假期"
        """
        if not file_name:
            return ""
        
        name = file_name
        
        # 1. 去除扩展名
        base_name, _ = os.path.splitext(name)
        name = base_name if base_name else name
        
        # 2. 去除常见网站/来源前缀
        for prefix in SOURCE_PREFIXES:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        
        # 3. 去除括号内的副标题（支持中文括号、英文括号、全角括号）
        # 匹配模式：（...）、(...)、〔...〕、【...】、<...>、《...》
        import re as _re
        # 先去除《》内的内容（书名号，通常包含完整书名）
        # 保留《》外的括号内容作为副标题去除
        name = _re.sub(r'[（(][^）)]*[）)]', '', name)   # 中文/英文圆括号
        name = _re.sub(r'[【[][^】]*[】]]', '', name)   # 中文方括号
        name = _re.sub(r'[[].*?[]]', '', name)           # 英文方括号
        name = _re.sub(r'<[^>]*>', '', name)             # 尖括号
        name = _re.sub(r'[〔[^〕]*〕]', '', name)         # 全角括号
        
        # 4. 去除下划线、连字符等分隔符（有些文件名用下划线代替空格）
        name = name.replace('_', ' ').replace('-', ' ')
        
        # 5. 去除多余空格并转小写
        name = ' '.join(name.split()).lower().strip()
        
        return name
    
    # 【新增】静态方法：文本归一化（用于SimHash计算前，解决类型④）
    @staticmethod
    def _normalize_text_for_comparison(text: str) -> str:
        """
        文本归一化处理，消除格式差异对相似度计算的影响（V7增强版）
        
        处理内容：
        0. 【V7新增】繁简中文转换（解决简体/繁体同书无法匹配的核心问题）
        1. 统一章节标记格式（## 第X章 / ## 第X页 / ## Chapter X）
        2. 去除HTML标签
        3. 统一中文标点（全角→半角或统一处理）
        4. 去除多余的空白字符
        """
        if not text:
            return ""
        
        import re as _re

        # 【V7新增】步骤0: 繁体中文 → 简体中文转换
        try:
            from src.utils.string_utils import _ChineseConverter
            text = _ChineseConverter.to_simplified(text)
        except Exception:
            pass  # 转换失败时继续使用原文

        # 1. 统一章节标记：将各种章节标记统一为空格
        text = _re.sub(r'#{1,6}\s*第\s*\d+\s*[章节回页折卷篇部]\s*', ' ', text)
        text = _re.sub(r'#{1,6}\s*第\s*\d+\s*页\s*', ' ', text)
        text = _re.sub(r'#{1,6}\s*Chapter\s+\d+', ' ', text, flags=_re.IGNORECASE)
        
        # 2. 去除HTML/XML标签
        text = _re.sub(r'<[^>]+>', '', text)
        
        # 3. 去除URL链接
        text = _re.sub(r'https?://\S+', '', text)
        
        # 4. 统一常见中文标点（保留基本结构但减少差异）
        text = text.replace('，', ',').replace('。', '.').replace('！', '!').replace('？', '?')
        text = text.replace('：', ':').replace('；', ';').replace('"', '"').replace('"', '"')
        
        # 5. 去除多余空白但保留单词边界
        text = _re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    # ===== Ultra原始参数（V3优化版）=====
    SIMHASH_BITS = 64
    SIMHASH_THRESHOLD = 3  # SimHash汉明距离阈值
    
    # ===== V7优化后的规则参数（平衡精准度与召回率）=====
    MIN_CONTENT_SIMILARITY = 0.32      # 规则A：从0.22提高到0.32（减少误报）
    HIGH_CONFIDENCE = 0.76             # 最终置信度门槛：从0.70提高到0.76（与Ultra一致）
    SUBSET_MIN_RATIO = 0.45            # 包含关系最低匹配率：从0.35提高到0.45（减少误报）
    SUBSET_SIZE_MIN_RATIO = 0.05       # 大小差异下限：从0.08降到0.05
    SUBSET_SIZE_MAX_RATIO = 0.98       # 大小差异上限：从0.95升到0.98
    FINGERPRINT_SLICE_SIZE = 800       # 指纹切片大小（字符）
    FINGERPRINT_MIN_OVERLAP = 0.40     # 切片重叠率门槛（判断子集）

    # ===== 【V6更新】防误报参数（适应0.1KB~30MB范围）=====
    MIN_FILE_SIZE_FOR_DETECTION = 256    # 最小文件大小(字节)【从1024降到256，适应0.1KB小文件】
    SHORT_CONTENT_THRESHOLD = 2000       # 短篇内容阈值(字节)
    FEATURE_SIMILARITY_WEIGHT = 0.15
    LARGE_FILE_THRESHOLD = 5 * 1024 * 1024   # 【新增】大文件阈值：5MB
    LARGE_FILE_SAMPLE_SIZE = 50000           # 【新增】大文件采样量：50KB
    
    # ===== V3增强参数（可选开启）=====
    ENABLE_ENHANCED_SAMPLING = True     # 是否使用增强采样（30000 vs 15000）
    ENABLE_MULTI_SCALE_SUBSET = True      # 是否使用多尺度包含检测
    ENABLE_TXT_ONLY_MODE = True          # 是否只处理TXT文件
    
    # ===== 性能参数（保持Ultra设置）=====
    MAX_DEEP_DETECT_SIZE = 2500
    MAX_PAIRS_PER_GROUP = 8000
    MAX_WORKERS = None
    SAMPLE_SIZE_ULTRA = 15000           # Ultra原始采样量
    SAMPLE_SIZE_V3 = 30000              # V3增强采样量
    
    # 缓存（线程安全）
    _hash_cache: Dict[str, str] = {}
    _content_cache: Dict[str, str] = {}
    _fingerprint_cache: Dict[str, BookFingerprint] = {}
    _cache_lock = threading.Lock()
    
    # 【修复】初始化_last_subset_result实例变量
    _last_subset_result: Tuple[bool, Optional['BookComparison']] = (False, None)
    
    # 取消标志
    _cancelled: bool = False
    _active_executors: List[ThreadPoolExecutor] = []
    _executors_lock = threading.Lock()
    
    @classmethod
    def request_cancel(cls):
        """请求取消"""
        cls._cancelled = True
        with cls._executors_lock:
            for executor in cls._active_executors:
                try:
                    # 【修复】兼容 Python < 3.9
                    try:
                        executor.shutdown(wait=False, cancel_futures=True)
                    except TypeError:
                        executor.shutdown(wait=False)
                except Exception:
                    pass
            cls._active_executors.clear()
    
    @classmethod
    def is_cancelled(cls) -> bool:
        return cls._cancelled
    
    @classmethod
    def reset_cancel(cls):
        cls._cancelled = False
    
    @classmethod
    def register_executor(cls, executor: ThreadPoolExecutor):
        with cls._executors_lock:
            cls._active_executors.append(executor)
    
    @classmethod
    def unregister_executor(cls, executor: ThreadPoolExecutor):
        with cls._executors_lock:
            if executor in cls._active_executors:
                cls._active_executors.remove(executor)
    
    @classmethod
    def clear_cache(cls):
        with cls._cache_lock:
            cls._hash_cache.clear()
            cls._content_cache.clear()
            cls._fingerprint_cache.clear()
    
    # =========================================================================
    # 公开接口（完全兼容Ultra）
    # =========================================================================
    
    @staticmethod
    def find_duplicates(
        books: List['Book'],
        progress_callback=None,
        batch_callback=None
    ) -> List[DuplicateGroup]:
        """
        查找重复书籍（V3版本 - Ultra完全兼容接口）
        
        Args:
            books: 书籍列表
            progress_callback: 进度回调(current, total) - 与Ultra相同
            batch_callback: 批次回调(groups, batch_idx, total_batches, processing_remaining) - 与Ultra相同
            
        Returns:
            List[DuplicateGroup]: 重复书籍组列表（与Ultra格式100%兼容）
        """
        detector = SmartDuplicateDetectorV3()
        
        try:
            result = detector._find_duplicates_impl(books, progress_callback, batch_callback)
            return result
        except (KeyboardInterrupt, SystemExit, Exception) as e:
            logger = detector._get_logger()
            logger.warning(f"⚠️ 去重检测被中断: {type(e).__name__} - {e}")
            return []
    
    def _find_duplicates_impl(self, books, progress_callback=None, batch_callback=None):
        """实现重复检测的主流程（严格遵循Ultra的4级流程）"""
        logger = self._get_logger()
        start_time = time.time()
        total = len(books)
        
        self.reset_cancel()
        logger.info(f"🚀 V3检测器启动 | 书籍总数: {total}")
        
        all_duplicate_groups = []
        
        # ===== 阶段1：预处理和指纹提取（progress: 0% → 10%）=====
        if progress_callback:
            progress_callback(0, 100)
        
        # 【修复】安全处理progress_callback可能为None的情况
        _callback = progress_callback  # 局部变量捕获
        safe_callback = (lambda c, t: _callback(c // 10, t)) if _callback else None
        
        fingerprints = self._compute_all_fingerprints(
            books,
            progress_callback=safe_callback
        )
        
        if self.is_cancelled():
            return all_duplicate_groups
        
        # ===== 阶段2：多级过滤检测（完全遵循Ultra流程）=====
        # 【类型注解】使用Tuple因为各检测函数签名不同，在调用时根据phase_name区分
        phases: List[Tuple[str, object, int]] = [
            ("Level 0: 文件哈希匹配", self._detect_by_hash, 10),
            ("Level 1: SimHash检测", self._detect_by_simhash, 30),
            ("Level 2: 深度内容检测", self._detect_by_deep_content, 60),
            ("Level 3: 文件名兜底", self._detect_by_filename, 90),
        ]
        
        processed_books = set()
        
        for phase_name, detect_func, progress_pct in phases:
            if self.is_cancelled():
                break
                
            if progress_callback:
                progress_callback(progress_pct, 100)
            
            # 排除已处理的书籍（Ultra逻辑）
            remaining_fps = [fp for fp in fingerprints 
                          if fp.book.path not in processed_books]
            
            # 【修复】_detect_by_filename需要额外传入已有结果
            # 根据phase_name调用不同签名的函数
            if phase_name == "Level 3: 文件名兜底":
                phase_groups = self._detect_by_filename(remaining_fps, all_duplicate_groups)
            else:
                # 根据phase_name调用对应的检测函数
                if phase_name == "Level 0: 文件哈希匹配":
                    phase_groups = self._detect_by_hash(remaining_fps)
                elif phase_name == "Level 1: SimHash检测":
                    phase_groups = self._detect_by_simhash(remaining_fps)
                elif phase_name == "Level 2: 深度内容检测":
                    phase_groups = self._detect_by_deep_content(remaining_fps, progress_callback=None)
                else:
                    phase_groups = []
            
            all_duplicate_groups.extend(phase_groups)
            
            # 记录已处理的书籍
            for group in phase_groups:
                for book in group.books:
                    processed_books.add(book.path)
            
            logger.info(f"  ✓ {phase_name}: {len(phase_groups)} 组")
            
            # 调用批次回调（Ultra格式）
            if batch_callback and phase_groups:
                try:
                    batch_callback(phase_groups, phases.index((phase_name, detect_func, progress_pct)), 
                                 len(phases), True)
                except Exception as e:
                    logger.debug(f"批回调异常: {e}")
        
        # 最终完成回调（空列表表示完成）
        if batch_callback:
            try:
                batch_callback([], len(phases), len(phases), False)
            except Exception as e:
                logger.debug(f"最终回调异常: {e}")
        
        if progress_callback:
            progress_callback(100, 100)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 检测完成！共发现 {len(all_duplicate_groups)} 组 | 耗时{elapsed:.2f}s")
        
        # 对每组进行删除推荐（Ultra的功能）
        for group in all_duplicate_groups:
            self._recommend_deletion(group)
        
        return all_duplicate_groups
    
    # =========================================================================
    # 阶段1：预处理（完全遵循Ultra逻辑）
    # =========================================================================
    
    def _compute_all_fingerprints(self, books, progress_callback=None):
        """计算所有书籍指纹（并行化，与Ultra相同）"""
        fingerprints = []
        completed = [0]
        lock = threading.Lock()
        
        def compute_one(book):
            try:
                fp = BookFingerprint(book=book)
                # 【V5改进】使用智能文件名标准化（去除来源前缀、副标题）
                fp.normalized_name = SmartDuplicateDetectorV3._normalize_book_name(book.file_name)
                
                fp.file_hash = self._get_cached_hash(book.path)
                
                # 【V6改进】动态采样策略（适应0.1KB~30MB范围）
                book_size = book.size if hasattr(book, 'size') and book.size else 0
                
                if book_size > self.LARGE_FILE_THRESHOLD:
                    # 大文件(>5MB)：增加采样量以获得更好代表性
                    sample_size = self.LARGE_FILE_SAMPLE_SIZE  # 50KB
                elif book_size < 1024:
                    # 小文件(<1KB)：读取全部内容
                    sample_size = min(book_size * 2, 4096) if book_size > 0 else 2048
                else:
                    # 普通文件：使用默认采样
                    sample_size = self.SAMPLE_SIZE_V3 if self.ENABLE_ENHANCED_SAMPLING else self.SAMPLE_SIZE_ULTRA
                
                content = self._read_book_content(book.path, sample_size)
                
                if content:
                    # 【V5改进】对内容进行归一化处理后再计算SimHash（解决类型④格式差异）
                    content_for_simhash = SmartDuplicateDetectorV3._normalize_text_for_comparison(content)
                    fp.content_sample = content[:5000] if len(content) > 5000 else content
                    fp.simhash = self._compute_simhash(content_for_simhash)
                    
                    lines = content.count('\n')
                    words = len(re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', content))
                    chars = len(re.sub(r'\s+', '', content))
                    fp.size_features = (lines, words, chars)
                    fp.title_keywords = self._extract_title_keywords(book.title or "")
                
                with lock:
                    completed[0] += 1
                    if progress_callback and completed[0] % 50 == 0:
                        progress_callback(completed[0], len(books))
                
                return fp
            except Exception as e:
                logger.error(f"计算指纹失败: {book.path}, {e}")
                return None
        
        # 【V7修复】指纹计算阶段：逐个submit避免shutdown后崩溃
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            self.register_executor(executor)
            
            futures = []
            for book in books:
                if self.is_cancelled():
                    break
                try:
                    future = executor.submit(compute_one, book)
                    futures.append(future)
                except RuntimeError as re_err:
                    if "cannot schedule new futures after shutdown" in str(re_err):
                        logger.debug("指纹计算: Executor已关闭，停止提交")
                        break
                    raise
            
            if not futures or self.is_cancelled():
                # 【V7修复关键】取消时必须先drain所有pending future，避免executor shutdown时
                # 打印 "Exception in thread Thread-X" 错误（Python默认线程异常处理）
                for f in futures:
                    try:
                        f.result(timeout=1)
                        r = f.result()
                        if r:
                            fingerprints.append(r)
                    except Exception:
                        pass
                return fingerprints
            
            for future in as_completed(futures):
                if self.is_cancelled():
                    break
                try:
                    result = future.result(timeout=3)
                    if result:
                        fingerprints.append(result)
                except Exception:
                    pass
        
        return fingerprints
    
    def _read_book_content(self, path: str, sample_size: int = 15000) -> str:
        """读取书籍内容（TXT优化版）"""
        cache_key = path
        if cache_key in self._content_cache:
            return self._content_cache[cache_key]
        
        try:
            if not os.path.exists(path):
                return ""
            
            _, ext = os.path.splitext(path.lower())
            
            # TXT专用模式检查
            if self.ENABLE_TXT_ONLY_MODE and ext != '.txt':
                return ""
            
            file_size = os.path.getsize(path)
            
            if file_size <= sample_size:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(sample_size)
            else:
                parts = 8 if not self.ENABLE_ENHANCED_SAMPLING else 5
                part_size = sample_size // parts
                samples = []
                
                # 【修复】所有文件操作必须在with块内部完成
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    samples.append(f.read(part_size))
                    
                    for i in range(1, parts):
                        pos = int(file_size * i / (parts - 1)) if parts > 1 else 0
                        f.seek(pos)
                        f.readline()
                        samples.append(f.read(part_size))
                    
                    # 【关键修复】读取文件末尾部分（必须在with块内）
                    f.seek(max(0, file_size - part_size))
                    samples.append(f.read(part_size))
                
                return ''.join(samples)
        except Exception as e:
            logger.error(f"读取失败: {path}, {e}")
            return ""
    
    # =========================================================================
    # 阶段2A：Level 0 - 文件哈希匹配（与Ultra完全相同）
    # =========================================================================
    
    def _detect_by_hash(self, fingerprints) -> List[DuplicateGroup]:
        """Level 0: 通过SHA256哈希检测完全相同的书籍"""
        groups = []
        hash_map: Dict[str, List[BookFingerprint]] = defaultdict(list)
        
        for fp in fingerprints:
            if fp.file_hash:
                hash_map[fp.file_hash].append(fp)
        
        for file_hash, fps in hash_map.items():
            if len(fps) > 1:
                group = DuplicateGroup(
                    duplicate_type=DuplicateType.HASH_IDENTICAL,
                    books=[fp.book for fp in fps],
                    similarity=1.0,
                    confidence=1.0
                )
                groups.append(group)
        
        return groups
    
    # =========================================================================
    # 阶段2B：Level 1 - SimHash检测（与Ultra相同逻辑）
    # =========================================================================
    
    def _detect_by_simhash(self, fingerprints) -> List[DuplicateGroup]:
        """Level 1: 使用SimHash进行快速相似性检测"""
        groups = []
        n = len(fingerprints)
        
        if n < 2:
            return groups
        
        valid_fps = [fp for fp in fingerprints if fp.simhash != 0]
        invalid_fps = [fp for fp in fingerprints if fp.simhash == 0]
        
        # 对无效SimHash的书籍使用简单方法
        if len(invalid_fps) >= 2:
            simple_groups = self._detect_simple(invalid_fps)
            groups.extend(simple_groups)
        
        if len(valid_fps) < 2:
            return groups
        
        if len(valid_fps) <= 3000:
            groups.extend(self._simhash_small_scale(valid_fps))
        else:
            groups.extend(self._simhash_large_scale(valid_fps))
        
        return groups
    
    def _simhash_small_scale(self, valid_fps) -> List[DuplicateGroup]:
        """小规模SimHash检测（≤3000本）- 与Ultra相同"""
        groups = []
        processed_indices = set()
        
        for i in range(len(valid_fps)):
            if i in processed_indices:
                continue
                
            fp1 = valid_fps[i]
            candidate_pairs = []
            
            for j in range(i + 1, len(valid_fps)):
                if j in processed_indices:
                    continue
                    
                fp2 = valid_fps[j]
                
                dist = self.hamming_distance(fp1.simhash, fp2.simhash)
                
                if dist <= self.SIMHASH_THRESHOLD:
                    # 【防误报】检查文件大小，小文件需要更高的SimHash匹配度
                    size1 = fp1.book.size if hasattr(fp1.book, 'size') and fp1.book.size else 0
                    size2 = fp2.book.size if hasattr(fp2.book, 'size') and fp2.book.size else 0
                    min_size = min(size1, size2)

                    # 对于极小文件，只接受完全相同的SimHash（dist=0）或dist=1
                    if min_size > 0 and min_size < self.SHORT_CONTENT_THRESHOLD:
                        if dist > 1:  # 小文件且汉明距离>1，跳过
                            continue

                    content_sim = 0.0
                    if fp1.content_sample and fp2.content_sample and \
                       len(fp1.content_sample) > 50 and len(fp2.content_sample) > 50:
                        from src.utils.string_utils import StringUtils
                        content_sim = StringUtils.book_content_similarity(
                            fp1.content_sample, fp2.content_sample, sample_size=8000
                        )

                    should_include = (
                        content_sim >= 0.32 or  # 【V7】从0.28提高到0.32
                        (content_sim == 0 and dist <= 1) or
                        fp1.normalized_name == fp2.normalized_name
                    )
                    
                    if should_include:
                        candidate_pairs.append((fp2, content_sim))
                        processed_indices.add(j)
            
            if len(candidate_pairs) >= 1:
                max_sim = max([cs for _, cs in candidate_pairs], default=0.0)
                
                has_name_match = any(
                    fp.normalized_name == fp1.normalized_name 
                    for fp, _ in candidate_pairs
                )
                
                should_create = (
                    max_sim >= 0.30 or  # 【V7】从0.25提高到0.30
                    (max_sim >= 0.22 and has_name_match) or  # 【V7】从0.18到0.22
                    len(candidate_pairs) >= 3
                )
                
                if should_create:
                    books = [fp1.book] + [fp.book for fp, _ in candidate_pairs]
                    
                    base_conf = 0.65
                    sim_bonus = min(0.25, max_sim * 0.4)
                    count_bonus = min(0.10, len(candidate_pairs) * 0.02)
                    name_bonus = 0.05 if has_name_match else 0
                    
                    confidence = min(0.95, base_conf + sim_bonus + count_bonus + name_bonus)
                    
                    group = DuplicateGroup(
                        duplicate_type=DuplicateType.SIMHASH_SIMILAR,
                        books=books,
                        similarity=max_sim,
                        confidence=confidence
                    )
                    self._recommend_deletion(group)
                    groups.append(group)
                    processed_indices.add(i)
        
        return groups
    
    def _simhash_large_scale(self, valid_fps) -> List[DuplicateGroup]:
        """大规模SimHash检测（>3000本）- 使用分块索引"""
        groups = []
        BLOCK_SIZE = 4
        NUM_BLOCKS = self.SIMHASH_BITS // BLOCK_SIZE
        THRESHOLD = self.SIMHASH_THRESHOLD
        
        block_indexes: List[Dict[int, List[int]]] = [defaultdict(list) for _ in range(NUM_BLOCKS)]
        
        for idx, fp in enumerate(valid_fps):
            simhash = fp.simhash
            for block_num in range(NUM_BLOCKS):
                shift = (NUM_BLOCKS - 1 - block_num) * BLOCK_SIZE
                mask = (1 << BLOCK_SIZE) - 1
                block_value = (simhash >> shift) & mask
                block_indexes[block_num][block_value].append(idx)
        
        candidate_pairs: Set[Tuple[int, int]] = set()
        
        def check_and_add_pair(i, j):
            if i >= j:
                return
            dist = self.hamming_distance(valid_fps[i].simhash, valid_fps[j].simhash)
            if dist <= THRESHOLD:
                candidate_pairs.add((i, j))
        
        total_buckets = sum(len(block_indexes[b]) for b in range(NUM_BLOCKS))
        
        for block_num in range(NUM_BLOCKS):
            for bucket_value, indices_in_bucket in block_indexes[block_num].items():
                bucket_size = len(indices_in_bucket)
                
                if bucket_size < 2:
                    continue
                    
                if bucket_size <= 100:
                    for i_idx in range(bucket_size):
                        for j_idx in range(i_idx + 1, bucket_size):
                            check_and_add_pair(indices_in_bucket[i_idx], indices_in_bucket[j_idx])
                else:
                    import random
                    sample_size = min(5000, bucket_size)
                    sampled_indices = random.sample(indices_in_bucket, sample_size)
                    
                    for i_idx in range(len(sampled_indices)):
                        for j_idx in range(i_idx + 1, len(sampled_indices)):
                            check_and_add_pair(sampled_indices[i_idx], sampled_indices[j_idx])
        
        # 并查集聚类
        if candidate_pairs:
            parent = {}  # 【修复】使用空字典实例，而不是dict类型
            
            def find(x):
                if x not in parent:
                    parent[x] = x
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            
            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py
            
            for i, j in candidate_pairs:
                union(i, j)
            
            clusters: Dict[int, Set[int]] = defaultdict(set)
            for path in parent:
                root = find(path)
                clusters[root].add(path)
            
            for root, member_indices in clusters.items():
                if len(member_indices) >= 2:
                    member_fps = [valid_fps[idx] for idx in member_indices]
                    
                    max_sim = 0.0
                    verified_pairs = 0
                    sample_size = min(8, len(member_fps))
                    
                    for i_idx in range(sample_size):
                        for j_idx in range(i_idx + 1, sample_size):
                            try:
                                fp1, fp2 = member_fps[i_idx], member_fps[j_idx]
                                
                                if fp1.content_sample and fp2.content_sample and \
                                   len(fp1.content_sample) > 50 and len(fp2.content_sample) > 50:
                                    from src.utils.string_utils import StringUtils
                                    sim = StringUtils.book_content_similarity(
                                        fp1.content_sample, fp2.content_sample, sample_size=8000
                                    )
                                    max_sim = max(max_sim, sim)
                                    
                                    if sim >= 0.20:
                                        verified_pairs += 1
                            except Exception:
                                pass
                    
                    total_possible_pairs = (sample_size * (sample_size - 1)) // 2
                    verification_ratio = verified_pairs / max(total_possible_pairs, 1)
                    
                    has_name_match = all(
                        member_fps[0].normalized_name == fp.normalized_name 
                        for fp in member_fps[1:]
                    )
                    
                    should_create = (
                        (max_sim >= 0.28) or  # 【V7】从0.22提高到0.28
                        (max_sim >= 0.20 and has_name_match) or  # 【V7】从0.15到0.20
                        (verified_pairs >= max(1, total_possible_pairs * 0.30))  # 【V7】从0.25到0.30
                    )
                    
                    if should_create:
                        books = [fp.book for fp in member_fps]
                        
                        base_conf = 0.60
                        sim_bonus = min(0.25, max_sim * 0.45)
                        verify_bonus = min(0.15, verification_ratio * 0.3)
                        name_bonus = 0.08 if has_name_match else 0
                        size_bonus = min(0.05, len(member_indices) * 0.01)
                        
                        confidence = min(0.93, base_conf + sim_bonus + verify_bonus + name_bonus + size_bonus)
                        
                        group = DuplicateGroup(
                            duplicate_type=DuplicateType.SIMHASH_SIMILAR,
                            books=books,
                            similarity=max_sim,
                            confidence=confidence
                        )
                        self._recommend_deletion(group)
                        groups.append(group)
        
        return groups
    
    def _detect_simple(self, fingerprints) -> List[DuplicateGroup]:
        """对无法计算SimHash的书籍使用简单方法（【加强版】防误报）"""
        groups = []
        name_to_fps: Dict[str, List[BookFingerprint]] = {}
        
        for fp in fingerprints:
            name = fp.normalized_name
            if name not in name_to_fps:
                name_to_fps[name] = []
            name_to_fps[name].append(fp)
        
        for name, fps_list in name_to_fps.items():
            if len(fps_list) > 1:
                potential_dupes = []
                for i in range(len(fps_list)):
                    for j in range(i + 1, len(fps_list)):
                        fp1, fp2 = fps_list[i], fps_list[j]
                        
                        # 【防误报】检查文件大小
                        size1 = fp1.book.size if hasattr(fp1.book, 'size') and fp1.book.size else 0
                        size2 = fp2.book.size if hasattr(fp2.book, 'size') and fp2.book.size else 0
                        
                        # 【收紧】两个条件都要满足：
                        # 1. 大小比例 >= 0.5（从0.3提高到0.5）
                        # 2. 至少有一个文件 > 最小检测阈值（排除极小文件）
                        if size1 and size2:
                            ratio = min(size1, size2) / max(size1, size2)
                            min_size = min(size1, size2)
                            if ratio >= 0.5 and min_size >= self.MIN_FILE_SIZE_FOR_DETECTION:
                                potential_dupes.extend([fp1, fp2])
                            elif ratio >= 0.8:  # 极高相似度的才允许小文件
                                potential_dupes.extend([fp1, fp2])
                
                if potential_dupes:
                    unique_books = list(set(fp.book for fp in potential_dupes))
                    
                    # 【新增】至少需要内容采样不为空
                    valid_books = [b for b in unique_books
                                  if any(fp.book == b and fp.content_sample 
                                         for fps in [fps_list] for fp in fps)]
                    
                    # 如果没有有效内容采样的书籍，使用原始结果但降低置信度
                    final_books = valid_books if len(valid_books) > 1 else unique_books
                    
                    if len(final_books) > 1:
                        group = DuplicateGroup(
                            duplicate_type=DuplicateType.FILE_NAME,
                            books=final_books,
                            similarity=0.0,
                            confidence=0.38 if len(valid_books) > 1 else 0.32  # 降低置信度
                        )
                        self._recommend_deletion(group)
                        groups.append(group)
        
        return groups
    
    # =========================================================================
    # 阶段2C：Level 2 - 深度内容检测（Ultra逻辑 + V3增强）
    # =========================================================================
    
    def _detect_by_deep_content(self, fingerprints, progress_callback=None) -> List[DuplicateGroup]:
        """Level 2: 深度内容相似度检测（遵循Ultra的多层验证机制）"""
        groups = []
        n = len(fingerprints)
        
        if n < 2:
            return groups
        
        size_groups = self._group_by_size_similarity(fingerprints)
        
        all_similar_pairs: Set[Tuple[str, str]] = set()
        
        for size_group_key, group_fps in size_groups.items():
            # 【V7修复】外层循环：取消时立即退出
            if self.is_cancelled():
                break
                
            if len(group_fps) < 2:
                continue
            
            pairs_to_check = [
                (group_fps[i], group_fps[j]) 
                for i in range(len(group_fps)) 
                for j in range(i + 1, len(group_fps))
            ]
            
            if len(pairs_to_check) > self.MAX_PAIRS_PER_GROUP:
                import random
                pairs_to_check = random.sample(pairs_to_check, self.MAX_PAIRS_PER_GROUP)
            
            def check_pair_with_cancel(pair):
                if self.is_cancelled():
                    return None
                    
                fp1, fp2 = pair
                try:
                    comparison = self._compare_fingerprints_detailed(fp1, fp2)
                    if comparison and comparison.confidence >= self.HIGH_CONFIDENCE:
                        pair_key = tuple(sorted([fp1.book.path, fp2.book.path]))
                        all_similar_pairs.add(pair_key)
                except Exception as e:
                    logger.debug(f"比较失败: {fp1.book.path} vs {fp2.book.path}, {e}")
                return None
            
            # 【V7修复】使用显式循环替代列表推导式，避免 shutdown 后继续 submit 导致崩溃
            with DaemonThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                self.register_executor(executor)
                
                futures = []
                # 逐个提交任务，每次检查取消标志
                submit_error = False
                for pair in pairs_to_check:
                    if self.is_cancelled():
                        break
                    try:
                        future = executor.submit(check_pair_with_cancel, pair)
                        futures.append(future)
                    except RuntimeError as re_err:
                        if "cannot schedule new futures after shutdown" in str(re_err):
                            logger.debug("Executor已关闭，停止提交新任务")
                            submit_error = True
                            break
                        raise
                
                if submit_error or not futures:
                    continue
                
                for future in as_completed(futures):
                    if self.is_cancelled():
                        # 【关键】中断循环，但先drain剩余future避免异常
                        break
                    
                    try:
                        result = future.result(timeout=1)
                        if result:
                            pair_key = tuple(sorted([result.book1.path, result.book2.path]))
                            all_similar_pairs.add(pair_key)
                    except Exception:
                        pass
                
                # 【V7修复】取消时drain所有未完成的future，避免 "Exception in thread" 崩溃
                if self.is_cancelled():
                    for f in futures:
                        try:
                            f.cancel()
                            f.result(timeout=0.5)
                        except Exception:
                            pass
                
                # 确保线程池关闭
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    executor.shutdown(wait=False)
                self.unregister_executor(executor)
        
        groups = self._cluster_pairs_into_groups(all_similar_pairs, fingerprints)
        
        return groups
    
    def _group_by_size_similarity(self, fingerprints):
        """按文件大小相似性分组（与Ultra相同）"""
        from collections import defaultdict
        size_groups = defaultdict(list)
        
        for fp in fingerprints:
            if fp.book.size:
                size_group_key = str(int(math.log10(max(fp.book.size, 1)) * 3))
            else:
                size_group_key = "unknown"
            size_groups[size_group_key].append(fp)
        
        final_groups = {}
        for key, group in size_groups.items():
            if len(group) > 1000:
                sub_groups = self._split_large_group(group, num_parts=5)
                for i, sub_group in enumerate(sub_groups):
                    final_groups[f"{key}_part{i}"] = sub_group
            else:
                final_groups[key] = group
        
        return final_groups
    
    def _split_large_group(self, group, num_parts=5):
        if len(group) <= num_parts:
            return [[fp] for fp in group]
        
        sorted_group = sorted(group, key=lambda fp: fp.book.size or 0)
        sub_groups = [[] for _ in range(num_parts)]
        for i, fp in enumerate(sorted_group):
            sub_groups[i % num_parts].append(fp)
        return [g for g in sub_groups if g]
    
    def _compare_fingerprints_detailed(self, fp1, fp2):
        """
        详细比较两个书籍指纹（Ultra的多层验证 + V3包含关系增强 + 防误报）【V5性能优化版】
        """
        try:
            book1, book2 = fp1.book, fp2.book

            # 【防误报】检查文件大小，极小文件跳过深度检测
            size1 = book1.size if hasattr(book1, 'size') and book1.size else 0
            size2 = book2.size if hasattr(book2, 'size') and book2.size else 0
            min_size = min(size1, size2)

            if min_size > 0 and min_size < self.MIN_FILE_SIZE_FOR_DETECTION:
                # 极小文件（<1KB）只有在以下情况才检测：
                # 1. 文件名完全相同 AND 文件大小非常接近(可能是副本)
                # 2. 否则直接跳过
                if not (fp1.normalized_name == fp2.normalized_name and
                        max(size1, size2) > 0 and
                        min_size / max(size1, size2) > 0.9):
                    return None

            file_name_match = fp1.normalized_name == fp2.normalized_name

            if fp1.file_hash and fp2.file_hash and fp1.file_hash == fp2.file_hash:
                return None

            if self._is_likely_false_positive(fp1, fp2):
                return None
            
            # 【V5新增】快速预筛选 - 避免不必要的深度计算
            # 如果文件名不匹配 且 大小比例极低(<5%) 且 SimHash距离大(>10)，直接跳过
            size_ratio = 1.0
            if size1 and size2 and max(size1, size2) > 0:
                size_ratio = min(size1, size2) / max(size1, size2)
            
            simhash_dist = float('inf')
            if fp1.simhash != 0 and fp2.simhash != 0:
                simhash_dist = self.hamming_distance(fp1.simhash, fp2.simhash)
            
            # 【V5】快速路径：明显不相似的配对提前退出
            if (not file_name_match and 
                size_ratio < 0.05 and 
                simhash_dist > 10):
                return None
            
            # 【V3增强】阶段2.5: 包含关系预检测（针对整本vs章节）
            # 【V5优化】只在满足条件时才执行（避免不必要的IO）
            should_check_subset = (
                0.05 <= size_ratio <= 0.95 or  # 大小有一定关联
                file_name_match or              # 或文件名匹配
                simhash_dist <= 7               # 或SimHash较接近
            )
            
            subset_result = None
            if should_check_subset:
                subset_result = self._check_subset_relation_enhanced(fp1, fp2)
            
            if subset_result and subset_result[0]:  # (is_duplicate, comparison)
                return subset_result[1]  # 返回ComparisonResult
            
            # 阶段3: 计算各维度
            content_similarity = 0.0
            subset_ratio_val = 0.0  # 【修复】重命名避免与外部变量冲突
            has_enough_content = False
            
            if fp1.content_sample and fp2.content_sample:
                if len(fp1.content_sample) > 100 and len(fp2.content_sample) > 100:
                    has_enough_content = True
                    from src.utils.string_utils import StringUtils
                    content_similarity = StringUtils.book_content_similarity(
                        fp1.content_sample, fp2.content_sample, sample_size=12000
                    )
            
            feature_sim = self._feature_similarity(fp1, fp2)
            
            # 阶段4: V4多层验证判断（规则A/B/C/D - 大幅提升召回率）
            is_duplicate = False
            duplicate_types = []
            confidence = 0.0
            
            # 获取文件大小用于后续判断
            size1 = book1.size if hasattr(book1, 'size') and book1.size else 0
            size2 = book2.size if hasattr(book2, 'size') and book2.size else 0
            
            # 规则A: 高内容相似度（V4: 降低门槛 + 大小合理性验证）
            if has_enough_content and content_similarity >= self.MIN_CONTENT_SIMILARITY:
                is_duplicate = True
                duplicate_types.append(DuplicateType.CONTENT_SIMILAR)
                
                base_confidence = 0.55  # 从0.58降到0.55
                content_bonus = min(0.28, content_similarity * 0.48)  # 增加bonus比例
                feature_bonus = feature_sim * self.FEATURE_SIMILARITY_WEIGHT
                
                # 【V4新增】大小合理性加分：如果大小比例合理（不是极端差异），提高置信度
                size_reasonableness = 0.0
                if 0.20 <= size_ratio <= 0.95:
                    size_reasonableness = 0.04  # 大小接近 → 加分
                elif size_ratio >= 0.10:
                    size_reasonableness = 0.02  # 有一定关联 → 小幅加分
                
                confidence = min(0.94, base_confidence + content_bonus + feature_bonus + size_reasonableness)
                
                if file_name_match:
                    confidence = min(0.96, confidence + 0.04)  # 从0.03提高到0.04
            
            # 规则B: 包含关系（V4: 使用增强检测结果 + 更宽松的阈值）
            elif hasattr(self, '_last_subset_result') and self._last_subset_result[0]:
                # 使用V4增强的包含关系结果
                is_duplicate = True
                duplicate_types.append(DuplicateType.CONTENT_SUBSET)
                
                subset_result_obj = self._last_subset_result[1]
                # _last_subset_result[1] 现在是 BookComparison 对象，包含 similarity 和 confidence
                if subset_result_obj and hasattr(subset_result_obj, 'similarity'):
                    ratio_val = subset_result_obj.similarity
                else:
                    ratio_val = 0.5
                
                if subset_result_obj and hasattr(subset_result_obj, 'confidence'):
                    confidence = max(confidence, subset_result_obj.confidence)
                else:
                    confidence = 0.60 + ratio_val * 0.25  # 范围: 0.60-0.85
                    
            else:
                # 使用StringUtils原生检测作为兜底
                subset_relationship = None
                subset_ratio_val = 0.0
                
                if book1.size and book2.size and self.SUBSET_SIZE_MIN_RATIO < size_ratio < self.SUBSET_SIZE_MAX_RATIO:
                    try:
                        from src.utils.string_utils import StringUtils
                        subset_rel, sub_rat = StringUtils.check_subset_relationship(book1, book2)
                        
                        if subset_rel in ["subset", "superset"] and sub_rat >= (self.SUBSET_MIN_RATIO * 0.8):  # 从0.50降到0.40
                            subset_relationship = subset_rel
                            subset_ratio_val = sub_rat
                    except Exception as e:
                        logger.debug(f"包含关系检查异常: {e}")
                
                if subset_relationship in ["subset", "superset"]:
                    is_duplicate = True
                    duplicate_types.append(DuplicateType.CONTENT_SUBSET)
                    
                    # V4: 放宽置信度计算条件
                    if subset_ratio_val >= self.SUBSET_MIN_RATIO:
                        confidence = 0.62 + subset_ratio_val * 0.22
                    elif subset_ratio_val >= 0.35 and size_ratio < 0.80:  # 从0.48降到0.35, 从0.75升到0.80
                        if file_name_match or feature_sim >= 0.50:  # 特征门槛从0.60降到0.50
                            confidence = 0.58 + subset_ratio_val * 0.24
                    elif subset_ratio_val >= 0.30 and size_ratio < 0.65:  # 新增更低档
                        if file_name_match and feature_sim >= 0.45:
                            confidence = 0.55 + subset_ratio_val * 0.25
            
            # 规则C: 中等相似度 + 多维辅助证据（V4: 针对类型②③增强）
            if (not is_duplicate and has_enough_content and 
                  content_similarity >= 0.18 and  # 【V4】从0.24降到0.18，捕获更多"内容相同"
                  (file_name_match or feature_sim >= 0.50 or simhash_dist <= 5)):  # 全面放宽
                
                additional_evidence = 0.0
                
                if file_name_match:
                    additional_evidence += 0.15  # 从0.13增加到0.15（针对类型③）
                if feature_sim >= 0.50:  # 从0.58降到0.50
                    additional_evidence += 0.12  # 从0.10增加到0.12
                if simhash_dist <= 5:  # 从4放宽到5
                    additional_evidence += 0.10  # 从0.08增加到0.10
                if simhash_dist <= 2:  # 极近海明距离额外加分
                    additional_evidence += 0.06
                
                # 【V4新增】大小合理性加分
                if size1 > self.MIN_FILE_SIZE_FOR_DETECTION and size2 > self.MIN_FILE_SIZE_FOR_DETECTION:
                    if 0.30 <= size_ratio <= 0.95:
                        additional_evidence += 0.05  # 两本都是有效文件且大小合理
                    elif size_ratio >= 0.15:
                        additional_evidence += 0.03
                
                combined_confidence = (
                    content_similarity * 0.52 +   # 内容权重略降
                    feature_sim * 0.18 + 
                    additional_evidence
                )
                
                # 【V4】动态阈值：根据辅助证据数量调整
                evidence_count = sum([
                    1 for v in [file_name_match, feature_sim >= 0.50, simhash_dist <= 5] if v
                ])
                dynamic_threshold = 0.52 - (evidence_count - 1) * 0.04  # 【V7】从0.48提高到0.52，最低从0.42升到0.48
                dynamic_threshold = max(0.48, dynamic_threshold)
                
                if combined_confidence >= dynamic_threshold:
                    is_duplicate = True
                    # 根据情况选择重复类型
                    if content_similarity >= 0.25 or (content_similarity >= 0.20 and file_name_match):
                        duplicate_types.append(DuplicateType.CONTENT_SIMILAR)
                    else:
                        duplicate_types.append(DuplicateType.CONTENT_SUBSET)  # 低相似但有其他证据时标记为子集
                        
                    if file_name_match:
                        duplicate_types.append(DuplicateType.FILE_NAME)
                    
                    confidence = min(0.84, combined_confidence + 0.14)  # 提高上限
            
            # 规则D: 仅文件名相同（【V7收紧】减少误报）
            if (not is_duplicate and file_name_match and
                  feature_sim >= 0.85 and      # 【V7】从0.78提高到0.85
                  has_enough_content and
                  content_similarity >= 0.30 and # 【V7】从0.22提高到0.30
                  size1 > self.MIN_FILE_SIZE_FOR_DETECTION and  
                  size2 > self.MIN_FILE_SIZE_FOR_DETECTION):

                is_duplicate = True
                duplicate_types.append(DuplicateType.FILE_NAME)
                
                # 根据实际相似度动态计算置信度
                name_factor = 1.0 if file_name_match else 0.8
                confidence = 0.54 + content_similarity * 0.45 + (feature_sim - 0.78) * 0.6
                confidence *= name_factor
                confidence = min(0.78, confidence)  # 上限从0.76提到0.78
            
            # 最终决策
            if not is_duplicate or not duplicate_types:
                return None
            
            # 【V4调整】置信度门槛检查
            if confidence < self.HIGH_CONFIDENCE:
                if confidence >= 0.64:  # 从0.70降到0.64，记录更多边界情况
                    logger.debug(f"低置信度候选: {book1.file_name} vs {book2.file_name}, conf={confidence:.2f}")
                return None
            
            return BookComparison(
                book1=book1,
                book2=book2,
                file_name_match=file_name_match,
                similarity=max(content_similarity, subset_ratio_val),
                hash_match=False,
                duplicate_types=duplicate_types,
                confidence=min(confidence, 0.99)
            )
            
        except Exception as e:
            logger.error(f"详细比较失败: {e}")
            return None
    
    def _check_subset_relation_enhanced(self, fp1, fp2):
        """
        V4重写：增强的包含关系检测（支持任意位置子集/中间截断/非连续重叠）
        
        核心改进：
        1. 指纹切片匹配：将内容切分成多段hash，支持任意位置的子集检测
        2. 双向检测：不再限制len_small <= len_large，支持"中间截断"场景
        3. 非连续匹配：即使内容有增删（如A是B的第3,5,7章），也能检测到
        4. 多层交叉验证：结合大小比例、文件名、特征相似度综合判断
        """
        from src.utils.string_utils import StringUtils
        
        try:
            book1, book2 = fp1.book, fp2.book
            
            # 【V5性能优化】分阶段读取内容（先快速检查，再完整检测）
            # 第一阶段：读取较小样本进行快速筛选
            content1 = self._read_book_content(book1.path, 8000)
            content2 = self._read_book_content(book2.path, 8000)
            
            if not content1 or not content2:
                self._last_subset_result = (False, None)
                return self._last_subset_result
            
            # 【V5新增】快速预检：如果归一化后前1000字符完全没有重叠，直接返回
            quick1 = SmartDuplicateDetectorV3._normalize_text_for_comparison(content1[:1000])
            quick2 = SmartDuplicateDetectorV3._normalize_text_for_comparison(content2[:1000])
            quick1_clean = re.sub(r'\s+', '', quick1)
            quick2_clean = re.sub(r'\s+', '', quick2)
            
            if len(quick1_clean) > 50 and len(quick2_clean) > 50:
                # 检查是否有任何公共子串（长度>=20）
                has_common = False
                for start in range(max(0, len(quick1_clean) - 100), len(quick1_clean)):
                    substr = quick1_clean[start:start+20]
                    if substr in quick2_clean:
                        has_common = True
                        break
                
                if not has_common:
                    # 再用字符集合做最后检查
                    common_chars = len(set(quick1_clean) & set(quick2_clean))
                    if common_chars < 30:  # 完全没有共同字符
                        self._last_subset_result = (False, None)
                        return self._last_subset_result
            
            # 【V6】只有通过快速预检才读取完整内容（动态采样量）
            size1 = book1.size if hasattr(book1, 'size') and book1.size else 0
            size2 = book2.size if hasattr(book2, 'size') and book2.size else 0
            
            # 根据文件大小动态决定第二阶段采样量
            max_size = max(size1, size2)
            if max_size > self.LARGE_FILE_THRESHOLD:
                deep_sample_size = min(80000, max_size // 10)  # 大文件：最多80KB或文件大小的10%
            elif max_size > 1024 * 1024:  # >1MB
                deep_sample_size = 40000   # 中大文件：40KB
            elif max_size < 2048:  # <2KB的小文件
                deep_sample_size = min(max_size, 8192)  # 小文件：读取全部但不超过8KB
            else:
                deep_sample_size = 25000  # 普通文件：25KB
            
            content1 = self._read_book_content(book1.path, deep_sample_size)
            content2 = self._read_book_content(book2.path, deep_sample_size)
            
            if not content1 or not content2:
                self._last_subset_result = (False, None)
                return self._last_subset_result
            
            # 【V5改进】对内容进行归一化处理（消除格式差异，解决类型④）
            content1_clean = SmartDuplicateDetectorV3._normalize_text_for_comparison(content1)
            content2_clean = SmartDuplicateDetectorV3._normalize_text_for_comparison(content2)
            
            clean1 = re.sub(r'\s+', '', content1_clean)
            clean2 = re.sub(r'\s+', '', content2_clean)
            len1, len2 = len(clean1), len(clean2)
            
            if len1 == 0 or len2 == 0:
                self._last_subset_result = (False, None)
                return self._last_subset_result
            
            # 确定大小关系（但不再因此跳过）
            small_content, large_content = (clean1, clean2) if len1 <= len2 else (clean2, clean1)
            small_len, large_len = len(small_content), len(large_content)
            size_ratio = small_len / large_len
            
            # ===== 新核心算法：指纹切片匹配 =====
            fingerprint_overlap = self._fingerprint_slice_match(small_content, large_content)
            
            # 快速检查：直接包含
            direct_contains = 1.0 if small_content in large_content else 0.0
            
            # 多尺度滑动窗口（保留作为辅助验证）
            window_ratio = self._multi_scale_sliding_window(small_content, large_content)
            
            # 关键段落匹配
            paragraph_ratio = self._key_paragraph_check(small_content, large_content)
            
            # ===== 综合判定（V4新权重）=====
            # 指纹切片是最可靠的指标，给予最高权重
            final_ratio = (
                max(direct_contains, fingerprint_overlap) * 0.45 +  # 直接包含或指纹匹配
                window_ratio * 0.25 +                              # 滑动窗口
                paragraph_ratio * 0.15 +                            # 关键段落
                min(size_ratio * 1.5, 0.15)                        # 大小合理性（封顶）
            )
            
            # 动态阈值：根据辅助证据调整
            file_name_match = fp1.normalized_name == fp2.normalized_name
            feature_sim = self._feature_similarity(fp1, fp2)
            
            dynamic_threshold = 0.32  # 基础阈值从0.42大幅降低
            
            # 如果有辅助证据，进一步放宽阈值
            if file_name_match:
                dynamic_threshold -= 0.05   # 文件名相同 → 降低到0.27
            if feature_sim >= 0.50:
                dynamic_threshold -= 0.04   # 特征相似 → 降低到0.28
            if size_ratio >= 0.40 and size_ratio <= 0.90:
                dynamic_threshold -= 0.03   # 大小合理 → 再降
            
            dynamic_threshold = max(0.22, dynamic_threshold)  # 最低不低于0.22
            
            is_duplicate = final_ratio >= dynamic_threshold
            
            if is_duplicate:
                # 置信度计算（V4优化）
                base_conf = 0.55
                ratio_bonus = min(0.25, final_ratio * 0.35)
                name_bonus = 0.06 if file_name_match else 0
                feature_bonus = min(0.08, feature_sim * 0.12)
                size_bonus = min(0.05, size_ratio * 0.08) if 0.15 < size_ratio < 0.95 else 0
                
                confidence = min(0.92, base_conf + ratio_bonus + name_bonus + feature_bonus + size_bonus)
                
                result = BookComparison(
                    book1=book1,
                    book2=book2,
                    file_name_match=file_name_match,
                    similarity=final_ratio,
                    hash_match=False,
                    duplicate_types=[DuplicateType.CONTENT_SUBSET],
                    confidence=confidence
                )
                
                self._last_subset_result = (True, result)
                return (True, result)
            else:
                self._last_subset_result = (False, None)
                return self._last_subset_result
                
        except Exception as e:
            logger.debug(f"包含关系检查异常: {e}")
            self._last_subset_result = (False, None)
            return self._last_subset_result
    
    def _fingerprint_slice_match(self, small_content: str, large_content: str) -> float:
        """
        【V4新增】指纹切片匹配算法 - 核心创新
        
        原理：
        将较小内容切成固定大小的片段，每个片段计算hash，
        然后检查这些hash中有多少能在较大内容中找到。
        
        优势：
        1. 能检测任意位置的子集（不限于开头/结尾）
        2. 对"中间截断"场景特别有效（如第3-8章 vs 第1-10章）
        3. 计算效率高，不需要逐字符比较
        
        返回值：0.0 - 1.0，表示匹配程度
        """
        import hashlib as hl
        
        small_len = len(small_content)
        large_len = len(large_content)
        
        if small_len < 200 or large_len < 200:
            return 1.0 if small_content in large_content else 0.0
        
        slice_size = self.FINGERPRINT_SLICE_SIZE
        step_size = int(slice_size * 0.7)  # 70%重叠，提高覆盖精度
        
        # 切分小内容的指纹
        small_fingerprints = set()
        
        for start in range(0, small_len - slice_size + 1, step_size):
            chunk = small_content[start:start + slice_size]
            if len(chunk) >= slice_size // 2:  # 至少半个有效切片
                fp_hash = hl.md5(chunk.encode('utf-8')).hexdigest()[:12]
                small_fingerprints.add(fp_hash)
        
        # 如果小内容太短，不足一个完整切片
        if not small_fingerprints and small_len >= 100:
            fp_hash = hl.md5(small_content[:min(small_len, slice_size)].encode('utf-8')).hexdigest()[:12]
            small_fingerprints.add(fp_hash)
        
        if not small_fingerprints:
            return 0.0
        
        # 在大内容中查找这些指纹
        matched_count = 0
        total_checked = 0
        
        for start in range(0, large_len - slice_size + 1, step_size):
            chunk = large_content[start:start + slice_size]
            if len(chunk) >= slice_size // 2:
                fp_hash = hl.md5(chunk.encode('utf-8')).hexdigest()[:12]
                total_checked += 1
                if fp_hash in small_fingerprints:
                    matched_count += 1
        
        if total_checked == 0:
            return 0.0
        
        # 匹配率：匹配到的切片数 / 大内容总切片数
        raw_match_rate = matched_count / total_checked
        
        # 归一化修正：考虑大小比例的影响
        size_factor = min(large_len / small_len, 10.0) / 10.0  # 0-1范围
        adjusted_rate = raw_match_rate * (1 + size_factor * 0.3)
        
        return min(1.0, adjusted_rate)
    
    def _multi_scale_sliding_window(self, small_content, large_content) -> float:
        """多尺度滑动窗口检测（V3增强）"""
        small_len = len(small_content)
        
        if small_len < 300:
            return 1.0 if small_content in large_content else 0.0
        
        found_total = 0
        window_count = 0
        
        scales = [
            (min(800, small_len // 3), 3),
            (min(500, small_len // 5), 3),
            (min(300, small_len // 8), 3),
        ]
        
        for window_size, overlap_div in scales:
            step_size = max(80, window_size // overlap_div)
            
            for start in range(0, small_len - window_size + 1, step_size):
                window = small_content[start:start + window_size]
                if window in large_content:
                    found_total += 1
                window_count += 1
        
        return found_total / window_count if window_count > 0 else 0.0
    
    def _key_paragraph_check(self, small_content, large_content) -> float:
        """关键段落匹配检测"""
        small_len = len(small_content)
        
        if small_len < 500:
            return 1.0 if small_content in large_content else 0.0
        
        paragraphs = []
        num_paras = 6
        para_len = min(600, small_len // (num_paras + 1))
        
        paragraphs.append(small_content[:para_len])
        paragraphs.append(small_content[-para_len:])
        
        for i in range(1, num_paras - 1):
            pos = small_len * i // num_paras
            paragraphs.append(small_content[pos:pos + para_len])
        
        matched = sum(1 for p in paragraphs if len(p) >= 200 and p in large_content)
        return matched / len(paragraphs) if paragraphs else 0.0
    
    # =========================================================================
    # 阶段2D: Level 3 - 文件名兜底检测（与Ultra相同）
    # =========================================================================
    
    def _detect_by_filename(self, fingerprints, existing_groups) -> List[DuplicateGroup]:
        """Level 3: 检测文件名相同但在之前阶段未被捕获的书籍【V5增强版】"""
        groups = []
        
        existing_paths = set()
        for group in existing_groups:
            for book in group.books:
                existing_paths.add(book.path)
        
        name_to_fps: Dict[str, List[BookFingerprint]] = {}
        for fp in fingerprints:
            name = fp.normalized_name
            if not name:  # 【V5】跳过空名称
                continue
            if name not in name_to_fps:
                name_to_fps[name] = []
            name_to_fps[name].append(fp)
        
        for name, fps_list in name_to_fps.items():
            remaining = [fp for fp in fps_list if fp.book.path not in existing_paths]
            
            if len(remaining) < 2:
                continue
            
            # 【V5增强】分两级验证
            verified = []
            for fp in remaining:
                # 基本验证：有内容采样或文件哈希
                if fp.content_sample or fp.file_hash:
                    size = fp.book.size if hasattr(fp.book, 'size') and fp.book.size else 0
                    # 【V6更新】使用统一的常量（256字节），适应0.1KB小文件
                    if size >= self.MIN_FILE_SIZE_FOR_DETECTION:
                        verified.append(fp)
            
            # 【V6新增】如果标准化后文件名完全相同但都太小，也加入候选列表
            if len(verified) < 2 and len(remaining) >= 2:
                # 检查是否有多个极小文件且文件名相同
                tiny_files = [fp for fp in remaining 
                             if (not fp.content_sample and not fp.file_hash) or
                             (fp.book.size or 0) < self.MIN_FILE_SIZE_FOR_DETECTION]
                if len(tiny_files) >= 2:
                    # 对极小文件做基本检查：文件名+大小完全匹配
                    sizes = [fp.book.size if hasattr(fp.book, 'size') and fp.book.size else 0 
                            for fp in tiny_files]
                    if len(set(sizes)) == 1:  # 大小完全相同
                        verified.extend(tiny_files[:2])  # 只取前2个避免误报
            
            if len(verified) < 2:
                continue
            
            # 【V5新增】智能内容相似度快速检查（替代原来的严格字符串包含）
            has_content_evidence = False
            content_evidence_score = 0.0
            
            for i in range(len(verified)):
                for j in range(i + 1, len(verified)):
                    if (verified[i].content_sample and verified[j].content_sample and
                        len(verified[i].content_sample) > 50 and
                        len(verified[j].content_sample) > 50):
                        
                        s1 = verified[i].content_sample[:800]
                        s2 = verified[j].content_sample[:800]
                        
                        # 【V5】使用多种宽松策略判断内容相关
                        score = 0.0
                        
                        # 策略1: 直接包含（权重高）
                        if s1 in s2 or s2 in s1:
                            score += 0.8
                        
                        # 策略2: 归一化后包含（处理格式差异）
                        s1_clean = re.sub(r'\s+', '', s1[:300])
                        s2_clean = re.sub(r'\s+', '', s2[:300])
                        if s1_clean in s2_clean or s2_clean in s1_clean:
                            score += 0.6
                        elif len(s1_clean) > 0 and len(s2_clean) > 0:
                            # 策略3: 字符集重叠度（放宽从200到100）
                            common_chars = len(set(s1_clean) & set(s2_clean))
                            if common_chars > 100:
                                score += min(0.5, common_chars / 400)
                            
                            # 策略4: 使用StringUtils相似度（最准确）
                            try:
                                from src.utils.string_utils import StringUtils
                                quick_sim = StringUtils.book_content_similarity(
                                    verified[i].content_sample[:2000],
                                    verified[j].content_sample[:2000],
                                    sample_size=2000
                                )
                                if quick_sim >= 0.15:  # 【V5放宽】从隐含的0.3降到0.15
                                    score += quick_sim * 0.5
                            except Exception:
                                pass
                        
                        content_evidence_score = max(content_evidence_score, score)
                        
                        if score >= 0.50:  # 【V7收紧】从0.35提高到0.50（减少文件名误报）
                            has_content_evidence = True
                            break
                
                if has_content_evidence:
                    break
            
            # 【V5放宽决策条件】
            # 条件1: 有内容证据（阈值降低）
            # 条件2: 书籍数量>=3（保持不变）
            # 条件3: 【新增】文件名标准化后完全相同 + 大小合理（针对类型①②③）
            is_size_reasonable = True
            if len(verified) == 2:
                sizes = [fp.book.size if hasattr(fp.book, 'size') and fp.book.size else 0 
                        for fp in verified]
                if sizes[0] > 0 and sizes[1] > 0:
                    ratio = min(sizes) / max(sizes)
                    is_size_reasonable = ratio >= 0.10  # 大小比例不太极端
            
            should_create = (
                has_content_evidence or 
                len(verified) >= 3 or
                (len(verified) >= 2 and is_size_reasonable and content_evidence_score >= 0.30)  # 【V7】从0.15提高到0.30
            )
            
            if should_create:
                books = [fp.book for fp in verified]
                
                # 【V5】根据证据强度动态调整置信度
                if has_content_evidence:
                    confidence = 0.52 + min(0.20, content_evidence_score * 0.3)
                elif len(verified) >= 3:
                    confidence = 0.45
                else:
                    confidence = 0.40  # 仅靠文件名+大小，置信度较低但仍然接受
                
                group = DuplicateGroup(
                    duplicate_type=DuplicateType.FILE_NAME,
                    books=books,
                    similarity=content_evidence_score,
                    confidence=min(confidence, 0.75)
                )
                self._recommend_deletion(group)
                groups.append(group)
        
        return groups
    
    # =========================================================================
    # 辅助方法（与Ultra相同）
    # =========================================================================
    
    def _is_likely_false_positive(self, fp1, fp2):
        """快速识别可能的误报（与Ultra相同）"""
        book1, book2 = fp1.book, fp2.book
        
        name1_parts = set(fp1.normalized_name.replace('.', ' ').split())
        name2_parts = set(fp2.normalized_name.replace('.', ' ').split())
        common_keywords = name1_parts & name2_parts
        
        stop_words = {'txt', 'epub', 'pdf', 'mobi', 'azw', 'azw3'}
        meaningful_common = common_keywords - stop_words
        
        if len(meaningful_common) == 0:
            if book1.size and book2.size:
                size_ratio = min(book1.size, book2.size) / max(book1.size, book2.size)
                if size_ratio < 0.2:
                    return True
        
        author1 = getattr(book1, 'author', '') or ''
        author2 = getattr(book2, 'author', '') or ''
        
        if author1 and author2:
            if author1.lower() != author2.lower():
                if len(meaningful_common) <= 1:
                    return True
        
        return False
    
    def _feature_similarity(self, fp1, fp2):
        """特征向量相似度（与Ultra相同）"""
        size_sim = 0.0
        if all(f != (0, 0, 0) for f in [fp1.size_features, fp2.size_features]):
            lines1, words1, chars1 = fp1.size_features
            lines2, words2, chars2 = fp2.size_features
            
            line_ratio = min(lines1, lines2) / max(lines1, lines2) if max(lines1, lines2) > 0 else 0
            word_ratio = min(words1, words2) / max(words1, words2) if max(words1, words2) > 0 else 0
            char_ratio = min(chars1, chars2) / max(chars1, chars2) if max(chars1, chars2) > 0 else 0
            
            size_sim = (line_ratio + word_ratio + char_ratio) / 3
        
        keyword_overlap = 0.0
        if fp1.title_keywords and fp2.title_keywords:
            intersection = fp1.title_keywords & fp2.title_keywords
            union = fp1.title_keywords | fp2.title_keywords
            keyword_overlap = len(intersection) / len(union) if union else 0
        
        return size_sim * 0.6 + keyword_overlap * 0.4
    
    def hamming_distance(self, h1, h2):
        xor = h1 ^ h2
        distance = 0
        while xor:
            distance += xor & 1
            xor >>= 1
        return distance
    
    @staticmethod
    def _compute_simhash(text, bits=64):
        """计算文本的SimHash指纹（V7增强版 - 支持繁简中文统一）"""
        # 【V7新增】繁简转换预处理
        if text:
            try:
                from src.utils.string_utils import _ChineseConverter
                text = _ChineseConverter.to_simplified(text)
            except Exception:
                pass
            # 基本清理：去空白转小写
            import re as _re
            text = _re.sub(r'\s+', '', text).lower()
        
        words = re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', text)
        if not words:
            return 0
        
        word_weights = {}
        for word in words:
            word_weights[word] = word_weights.get(word, 0) + 1
        
        v = [0] * bits
        for word, weight in word_weights.items():
            word_hash = hashlib.md5(word.encode('utf-8')).hexdigest()
            bin_hash = bin(int(word_hash[:16], 16))[2:].zfill(bits)
            
            for i in range(bits):
                if bin_hash[i] == '1':
                    v[i] += weight
                else:
                    v[i] -= weight
        
        fingerprint = 0
        for i in range(bits):
            if v[i] > 0:
                fingerprint |= (1 << (bits - 1 - i))
        
        return fingerprint
    
    @staticmethod
    def _extract_title_keywords(title):
        if not title:
            return set()
        
        keywords = set(re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', title))
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不',
                      '人', '都', '一', '一个', '上', '也', '很'}
        keywords -= stop_words
        return keywords
    
    # =========================================================================
    # 结果聚类（与Ultra相同）
    # =========================================================================
    
    def _cluster_pairs_into_groups(self, similar_pairs, fingerprints):
        """将相似书对聚类成组（与Ultra相同）"""
        if not similar_pairs:
            return []
        
        path_to_fp = {fp.book.path: fp for fp in fingerprints}
        parent = {}
        
        def find(x):
            if x not in parent:
                parent[x] = x
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        for path1, path2 in similar_pairs:
            union(path1, path2)
        
        clusters = defaultdict(set)
        for path in parent:
            root = find(path)
            clusters[root].add(path)
        
        groups = []
        for root, member_paths in clusters.items():
            if len(member_paths) >= 2:
                books = [path_to_fp[p].book for p in member_paths if p in path_to_fp]
                if len(books) >= 2:
                    group = DuplicateGroup(
                        duplicate_type=DuplicateType.CONTENT_SIMILAR,
                        books=books,
                        similarity=0.5,
                        confidence=0.7
                    )
                    self._recommend_deletion(group)
                    groups.append(group)
        
        return groups
    
    # =========================================================================
    # 推荐删除（与Ultra相同）
    # =========================================================================
    
    @staticmethod
    def _recommend_deletion(group):
        """推荐删除选择（与Ultra完全相同）"""
        if not group.books or len(group.books) < 2:
            return
        
        def score_book(book):
            s = 0.0
            if book.size:
                s += math.log10(max(book.size, 1)) * 2
            if hasattr(book, 'reading_progress') and book.reading_progress:
                s += 10
            format_pref = {'txt': 3, 'epub': 3, 'pdf': 2}
            if book.format and book.format.lower() in format_pref:
                s += format_pref[book.format.lower()]
            if book.file_name and not any(c in book.file_name for c in ['%', '#']):
                s += 1
            path_depth = book.path.count(os.sep)
            s += max(0, 5 - path_depth) * 0.5
            return s
        
        sorted_books = sorted(group.books, key=score_book, reverse=True)
        group.recommended_to_keep = [sorted_books[0]]
        group.recommended_to_delete = sorted_books[1:]
    
    # =========================================================================
    # 缓存管理
    # =========================================================================
    
    def _get_cached_hash(self, path):
        if path in self._hash_cache:
            return self._hash_cache[path]
        
        try:
            if os.path.exists(path):
                from src.utils.file_utils import FileUtils
                h = FileUtils.calculate_file_sha256(path)
                with self._cache_lock:
                    self._hash_cache[path] = h
                return h
        except Exception:
            pass
        return ""
    
    def _get_logger(self):
        from src.utils.logger import get_logger
        return get_logger(__name__)


# ============================================================================
# DaemonThreadPoolExecutor（与Ultra相同）
# ============================================================================

class DaemonThreadPoolExecutor(ThreadPoolExecutor):
    """自定义线程池执行器 - 所有工作线程都是daemon线程"""
    
    def submit(self, fn, *args, **kwargs):
        future = super().submit(fn, *args, **kwargs)
        
        for t in self._threads:
            if not t.daemon:
                try:
                    t.daemon = True
                except (RuntimeError, ValueError):
                    pass
        return future


# ============================================================================
# 便捷接口（100%兼容Ultra）
# ============================================================================

def find_duplicates_v3(books, progress_callback=None, batch_callback=None):
    """
    使用V3检测引擎查找重复书籍（Ultra完全兼容接口）
    
    参数格式与Ultra.find_duplicates完全一致
    """
    return SmartDuplicateDetectorV3.find_duplicates(
        books,
        progress_callback=progress_callback,
        batch_callback=batch_callback
    )


# 兼容性别名
SmartDuplicateDetector = SmartDuplicateDetectorV3  # 让用户可以使用旧名称调用
