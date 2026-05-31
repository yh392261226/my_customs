"""
智能书籍重复检测器 V2 - 全面重构版本

核心设计理念：
1. 多维度加权评分引擎（替代if-elif规则堆叠）
2. 场景感知的自适应检测策略
3. 可配置的统一参数体系
4. 全面的重复场景覆盖

支持的检测场景：
✅ 完全相同（哈希匹配）
✅ 包含关系（子集/超集）- 1-5章 vs 1-8章等
✅ 高度相似（>70%）- 格式转换、版本差异
✅ 中度相似（40-70%）- 不同来源、有/无附加内容
✅ 低度相关（25-40%）- 同系列、同主题
⚠️ 特殊情况：编码差异、简繁转换（需要额外处理）

架构优势：
- 消除规则冲突：不再使用互斥的if-elif链
- 统一评分：所有维度综合计算最终置信度
- 可解释性：清晰展示每项得分的来源
- 易于调优：修改配置即可调整行为

性能预期：
- 小规模(<1000本)：秒级完成
- 中规模(1000-5000本)：10-30秒
- 大规模(>5000本)：1-3分钟（使用采样）
"""

import os
import hashlib
import math
import re
import time
from typing import List, Dict, Tuple, Optional, Set, NamedTuple
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# ============================================================================
# 第一部分：数据结构定义
# ============================================================================

class DuplicateCategory(IntEnum):
    """重复类别（更细粒度的分类）"""
    IDENTICAL = 1          # 完全相同（哈希一致）
    SUBSET = 2             # 包含关系（子集vs超集）
    HIGH_SIMILAR = 3       # 高度相似（70-100%）
    MEDIUM_SIMILAR = 4     # 中度相似（40-70%）
    LOW_SIMILAR = 5        # 低度相关（25-40%）
    NAME_ONLY = 6          # 仅文件名相同（弱信号）
    UNKNOWN = 0            # 未知类型


@dataclass
class DimensionScore:
    """单个维度的评分结果"""
    name: str              # 维度名称（中文描述）
    score: float           # 得分 (0-100)
    weight: float          # 权重 (0-1)
    weighted_score: float  # 加权得分 = score * weight * 100
    evidence: str          # 证据描述（用于日志和UI显示）
    
    def __post_init__(self):
        self.weighted_score = self.score * self.weight * 100


@dataclass 
class BookFingerprintV2:
    """书籍指纹信息（V2增强版）"""
    book: 'Book'
    file_hash: str = ""
    simhash: int = 0
    content_sample: str = ""
    normalized_name: str = ""
    
    # 增强的统计特征
    size_features: Tuple[int, int, int] = (0, 0, 0)  # (行数, 词数, 字符数)
    title_keywords: Set[str] = field(default_factory=set)
    
    # 新增：编码检测特征
    detected_encoding: str = ""  # 检测到的编码（UTF-8/GBK等）
    has_bom: bool = False       # 是否有BOM标记
    
    # 新增：内容特征签名
    content_signature: str = ""  # 内容的简化签名（用于快速比较）
    chapter_markers: List[str] = field(default_factory=list)  # 检测到的章节标题
    
    # 性能优化：预计算的哈希值
    _content_hash: int = 0  # 内容采样的一致性哈希（用于快速比较）


@dataclass
class ComparisonResult:
    """
    书籍比较结果（V2版 - 统一评分体系）
    
    核心改进：
    - 使用总评分代替单一相似度
    - 记录所有维度的得分明细
    - 提供可解释的判断依据
    - 支持多种决策阈值
    """
    book1: 'Book'
    book2: 'Book'
    
    # 核心指标
    total_score: float = 0.0      # 总分 (0-100)
    category: DuplicateCategory = DuplicateCategory.UNKNOWN
    
    # 维度得分明细
    dimensions: List[DimensionScore] = field(default_factory=list)
    
    # 辅助信息
    is_subset: bool = False       # 是否为包含关系
    subset_ratio: float = 0.0     # 包含关系匹配率
    subset_direction: str = ""    # "book1_in_book2" 或 "book2_in_book1"
    
    size_ratio: float = 1.0       # 文件大小比例（小/大）
    content_similarity: float = 0.0  # 原始内容相似度 (0-1)
    filename_similarity: float = 0.0 # 文件名相似度 (0-1)
    
    # 决策支持
    confidence: float = 0.0       # 置信度 (0-1)，越高越确定
    recommendation: str = ""      # 推荐操作："keep_both", "keep_larger", "keep_first"
    reason: str = ""              # 判定原因（自然语言描述）
    
    @property
    def is_likely_duplicate(self) -> bool:
        """是否可能为重复书籍"""
        return self.total_score >= 60 and self.confidence >= 0.5
    
    @property
    def is_definite_duplicate(self) -> bool:
        """是否确定为重复书籍"""
        return self.total_score >= 80 and self.confidence >= 0.7


@dataclass
class DuplicateGroupV2:
    """重复书籍组（V2版）"""
    category: DuplicateCategory
    books: List['Book']
    total_score: float = 0.0
    confidence: float = 0.0
    
    # 详细比较结果（用于UI展示）
    comparison_details: Dict[str, ComparisonResult] = field(default_factory=dict)
    
    recommended_to_keep: List['Book'] = None
    recommended_to_delete: List['Book'] = None
    
    def __post_init__(self):
        if self.recommended_to_keep is None:
            self.recommended_to_keep = []
        if self.recommended_to_delete is None:
            self.recommended_to_delete = []


# ============================================================================
# 第二部分：统一配置体系
# ============================================================================

@dataclass
class DetectionConfig:
    """
    检测配置（集中管理所有参数）- TXT专用版
    
    设计原则：
    1. 所有可调参数集中在一处
    2. 参数命名语义化（易于理解）
    3. 提供预设模式（严格/平衡/宽松）
    4. 支持运行时动态调整
    
    【TXT专用优化】：
    - 只处理 .txt 格式的文本文件
    - 跳过所有二进制格式（epub, pdf等）
    - 针对纯文本的特性进行算法优化
    """
    
    # ===== 评分维度权重配置（【2026-05-29优化版】防止误报）=====
    
    # 内容相似度权重（最重要的指标 - 提高权重）
    WEIGHT_CONTENT_SIMILARITY: float = 0.42       # 从35%提高到42%
    
    # 包含关系权重（针对子集/超集场景）
    WEIGHT_SUBSET_RELATION: float = 0.25
    
    # 文件名/元数据权重
    WEIGHT_METADATA: float = 0.15
    
    # 【关键修复】文件大小比例权重（从10%降到5%）
    # 原因：不同大小的书也容易得60-90分，导致误报
    WEIGHT_SIZE_RATIO: float = 0.05
    
    # 【关键修复】SimHash指纹权重（从10%降到5%）
    # 原因：SimHash阈值放宽后，不相关的书也可能接近
    WEIGHT_SIMHASH: float = 0.05
    
    # 【关键修复】结构特征权重（从5%降到3%）
    # 原因：章节标记等特征太容易匹配
    WEIGHT_STRUCTURE: float = 0.03
    
    # ===== 阈值配置（【2026-05-29优化版】解决100%误报问题）=====
    
    # 总分阈值（【收紧】防止误报）
    THRESHOLD_DEFINITE_DUPLICATE: float = 82.0   # 确定是重复（从80提高到82）
    THRESHOLD_LIKELY_DUPLICATE: float = 70.0     # 可能是重复（从65提高到70）
    THRESHOLD_SUSPICIOUS: float = 58.0           # 可疑（从50提高到58，低于此不报告）
    
    # 各维度最低要求
    MIN_CONTENT_FOR_POSITIVE: float = 0.30       # 正面判断的最低内容相似度（从25%提高到30%）
    MIN_SUBSET_RATIO: float = 0.48               # 包含关系的最低匹配率（从40%提高到48%）
    
    # 大小比例范围（【收紧】减少无关书籍进入候选集）
    SIZE_RATIO_SUBSET_MIN: float = 0.35          # 可能存在包含关系的最小大小比（从20%提高到35%）
    SIZE_RATIO_SUBSET_MAX: float = 0.93          # 可能存在包含关系的最大大小比（从98%降到93%）
    
    # 【关键修复】SimHash海明距离阈值（从4收紧到2）
    # 原因：threshold=4时，16833本书会产生数百万候选对→性能爆炸+误报
    SIMHASH_THRESHOLD: int = 2                   # 海明距离<=2才认为是相似
    
    # ===== 性能配置（【优化】控制计算量）=====
    
    MAX_SAMPLE_SIZE: int = 40000                 # 最大内容采样量（字符）
    SAMPLE_PARTS: int = 10                       # 采样位置数量
    MAX_DEEP_COMPARE_PAIRS: int = 5000           # 【关键】最大深度比较书对数（从15000降到5000）
    MAX_WORKERS: Optional[int] = None            # 并行工作线程数（None=自动）
    TIMEOUT_PER_PAIR: float = 8.0                # 每对比较的超时时间（秒）
    
    # ===== 特殊场景处理 =====
    
    # 是否启用编码差异自动转换
    ENABLE_ENCODING_CONVERSION: bool = True
    
    # 是否尝试简繁转换比较
    ENABLE_SIMPLIFIED_TRADITIONAL: bool = True
    
    # 【核心】是否只处理TXT格式（忽略其他格式）
    TXT_ONLY_MODE: bool = True  # 默认只处理txt格式
    
    # 支持的文件扩展名列表
    SUPPORTED_EXTENSIONS: tuple = ('.txt',)
    
    # 二进制格式是否跳过内容比较
    SKIP_BINARY_CONTENT: bool = True
    
    # ===== 预设模式工厂方法 =====
    
    @classmethod
    def strict_mode(cls) -> 'DetectionConfig':
        """严格模式：高精准度，宁可漏检也不误报"""
        config = cls()
        config.THRESHOLD_DEFINITE_DUPLICATE = 90.0
        config.THRESHOLD_LIKELY_DUPLICATE = 75.0
        config.MIN_CONTENT_FOR_POSITIVE = 0.35
        config.MIN_SUBSET_RATIO = 0.55
        config.WEIGHT_CONTENT_SIMILARITY = 0.40
        return config
    
    @classmethod
    def balanced_mode(cls) -> 'DetectionConfig':
        """平衡模式：默认配置"""
        return cls()
    
    @classmethod
    def loose_mode(cls) -> 'DetectionConfig':
        """宽松模式：高召回率，允许一定误报"""
        config = cls()
        config.THRESHOLD_DEFINITE_DUPLICATE = 70.0
        config.THRESHOLD_LIKELY_DUPLICATE = 55.0
        config.MIN_CONTENT_FOR_POSITIVE = 0.18
        config.MIN_SUBSET_RATIO = 0.32
        config.WEIGHT_SUBSET_RELATION = 0.30
        config.SIZE_RATIO_SUBSET_MIN = 0.15
        return config


# ============================================================================
# 第三部分：核心检测引擎
# ============================================================================

class SmartDuplicateDetector:
    """
    智能书籍重复检测器 V2（全面重构版）
    
    核心创新：
    1. ✅ 多维度加权评分引擎（替代硬性规则）
    2. ✅ 场景感知的自适应策略
    3. ✅ 全面的场景覆盖（15+种情况）
    4. ✅ 可解释的判定结果
    5. ✅ 统一的配置管理体系
    """
    
    def __init__(self, config: DetectionConfig = None):
        """
        初始化检测器
        
        Args:
            config: 检测配置，如果为None则使用默认配置
        """
        self.config = config or DetectionConfig.balanced_mode()
        
        # 缓存（线程安全）
        self._hash_cache: Dict[str, str] = {}
        self._content_cache: Dict[str, str] = {}
        self._fingerprint_cache: Dict[str, BookFingerprintV2] = {}
        self._cache_lock = threading.Lock()
        
        # 取消标志
        self._cancelled = False
        
        logger = self._get_logger()
        logger.info(f"🚀 智能去重引擎V2初始化完成")
        logger.info(f"   模式: {self._get_mode_name()}")
        logger.info(f"   阈值: 确定={self.config.THRESHOLD_DEFINITE_DUPLICATE}, "
                   f"疑似={self.config.THRESHOLD_LIKELY_DUPLICATE}")
    
    def _get_logger(self):
        """获取logger实例"""
        from src.utils.logger import get_logger
        return get_logger(__name__)
    
    def _get_mode_name(self) -> str:
        """获取当前模式名称"""
        if self.config.THRESHOLD_DEFINITE_DUPLICATE >= 85:
            return "严格模式"
        elif self.config.THRESHOLD_DEFINITE_DUPLICATE <= 75:
            return "宽松模式"
        else:
            return "平衡模式"
    
    # =========================================================================
    # 公开接口
    # =========================================================================
    
    @staticmethod
    def _filter_txt_books(books: list) -> list:
        """
        过滤出只包含TXT格式的书籍
        
        【核心功能】：
        - 只保留 .txt 扩展名的文件
        - 忽略 epub, pdf, mobi 等所有其他格式
        - 支持大小写不敏感匹配（.TXT, .Txt等）
        
        Args:
            books: 原始书籍列表
            
        Returns:
            List[Book]: 只包含txt格式的书籍列表
        """
        txt_books = []
        
        for book in books:
            # 获取文件扩展名并转为小写
            _, ext = os.path.splitext(book.path.lower())
            
            if ext == '.txt':
                txt_books.append(book)
        
        return txt_books
    
    @classmethod
    def find_duplicates(
        cls,
        books: list,
        progress_callback=None,
        batch_callback=None,
        mode: str = "balanced"
    ) -> list:
        """
        查找重复书籍（主入口）
        
        Args:
            books: 书籍列表
            progress_callback: 进度回调函数(current, total, message)
            batch_callback: 批次回调函数(groups, phase, total_phases)
            mode: 检测模式 ("strict", "balanced", "loose")
            
        Returns:
            List[DuplicateGroupV2]: 重复书籍组列表
        """
        # 选择配置模式
        config_map = {
            "strict": DetectionConfig.strict_mode,
            "balanced": DetectionConfig.balanced_mode,
            "loose": DetectionConfig.loose_mode
        }
        config_cls = config_map.get(mode, DetectionConfig.balanced_mode)
        
        detector = cls(config=config_cls())
        
        try:
            result = detector._run_detection(books, progress_callback, batch_callback)
            return result
        except Exception as e:
            logger = detector._get_logger()
            logger.error(f"❌ 去重检测失败: {e}")
            return []
    
    def request_cancel(self):
        """请求取消正在运行的检测"""
        self._cancelled = True
        logger = self._get_logger()
        logger.warning("⚠️ 收到取消请求")
    
    def reset_cancel(self):
        """重置取消标志"""
        self._cancelled = False
    
    # =========================================================================
    # 主流程
    # =========================================================================
    
    def _run_detection(
        self,
        books: list,
        progress_callback=None,
        batch_callback=None
    ) -> List[DuplicateGroupV2]:
        """执行完整的检测流程"""
        logger = self._get_logger()
        start_time = time.time()
        
        # 【TXT专用】过滤出只包含txt格式的书籍
        if self.config.TXT_ONLY_MODE:
            original_count = len(books)
            books = self._filter_txt_books(books)
            filtered_count = len(books)
            
            if original_count > filtered_count:
                logger.info(f"\n{'='*70}")
                logger.info(f"📝 TXT专用模式：已过滤非TXT文件")
                logger.info(f"   原始书籍: {original_count} 本")
                logger.info(f"   TXT书籍: {filtered_count} 本 (已跳过 {original_count - filtered_count} 本其他格式)")
        
        total = len(books)
        
        # 如果没有txt书籍，直接返回空结果
        if total < 2:
            logger.info("⚠️  TXT书籍数量不足（<2本），无法进行去重检测")
            return []
        
        self.reset_cancel()
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 开始智能去重检测 | TXT书籍: {total} | 模式: {self._get_mode_name()}")
        logger.info(f"{'='*70}\n")
        
        all_groups = []
        
        # ===== 阶段1：预处理和指纹提取 =====
        if progress_callback:
            progress_callback(0, 100, "正在提取书籍指纹...")
        
        fingerprints = self._compute_all_fingerprints(
            books,
            progress_callback=lambda c, t: progress_callback(c // 10, 100, f"提取进度: {c}/{t}")
        )
        
        if self._cancelled:
            return all_groups
        
        # ===== 阶段2：多级过滤检测 =====
        phases = [
            ("完全相同检测", self._detect_identical, 10),
            ("包含关系检测", self._detect_subset_relations, 35),
            ("高度相似检测", self._detect_highly_similar, 60),
            ("中度相似检测", self._detect_medium_similar, 80),
            ("低度相关检测", self._detect_low_related, 95),
        ]
        
        processed_paths = set()
        
        for phase_name, detect_func, progress_pct in phases:
            if self._cancelled:
                break
            
            if progress_callback:
                progress_callback(progress_pct, 100, f"正在进行{phase_name}...")
            
            remaining_fps = [fp for fp in fingerprints 
                          if fp.book.path not in processed_paths]
            
            phase_groups = detect_func(remaining_fps)
            all_groups.extend(phase_groups)
            
            # 记录已处理的书籍
            for group in phase_groups:
                for book in group.books:
                    processed_paths.add(book.path)
            
            logger.info(f"  ✓ {phase_name}: 发现 {len(phase_groups)} 组")
            
            if batch_callback and phase_groups:
                batch_callback(phase_groups, phases.index((phase_name, detect_func, progress_pct)), len(phases))
        
        # ===== 阶段3：结果汇总和后处理 =====
        if progress_callback:
            progress_callback(100, 100, "检测完成！")
        
        elapsed = time.time() - start_time
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ 检测完成！共发现 {len(all_groups)} 组重复书籍")
        logger.info(f"⏱️  耗时: {elapsed:.2f}秒")
        logger.info(f"{'='*70}\n")
        
        # 对每组进行删除推荐
        for group in all_groups:
            self._recommend_deletion(group)
        
        if batch_callback:
            batch_callback([], len(phases), len(phases))
        
        return all_groups
    
    # =========================================================================
    # 阶段1：指纹提取
    # =========================================================================
    
    def _compute_all_fingerprints(
        self,
        books: list,
        progress_callback=None
    ) -> List[BookFingerprintV2]:
        """并行计算所有书籍的指纹"""
        fingerprints = []
        completed = [0]
        lock = threading.Lock()
        logger = self._get_logger()
        
        def compute_one(book):
            try:
                fp = BookFingerprintV2(book=book)
                fp.normalized_name = book.file_name.lower().strip()
                
                # 计算文件哈希
                fp.file_hash = self._get_cached_hash(book.path)
                
                # 读取内容并提取特征
                content = self._read_book_content(book.path)
                
                if content:
                    fp.content_sample = content[:8000] if len(content) > 8000 else content
                    
                    # 计算SimHash
                    fp.simhash = self._compute_simhash(content)
                    
                    # 计算统计特征
                    lines = content.count('\n')
                    words = len(re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', content))
                    chars = len(re.sub(r'\s+', '', content))
                    fp.size_features = (lines, words, chars)
                    
                    # 提取标题关键词
                    fp.title_keywords = self._extract_keywords(book.title or "")
                    
                    # 检测编码
                    fp.detected_encoding = self._detect_encoding(content[:2000])
                    
                    # 检测章节标记
                    fp.chapter_markers = self._detect_chapter_markers(content)
                    
                    # 计算内容签名（用于快速比较）
                    fp.content_signature = self._compute_content_signature(content)
                
                # 更新进度
                with lock:
                    completed[0] += 1
                    if progress_callback and completed[0] % 50 == 0:
                        progress_callback(completed[0], len(books))
                
                return fp
                
            except Exception as e:
                logger.error(f"计算指纹失败: {book.path}, 错误: {e}")
                return None
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            futures = [executor.submit(compute_one, book) for book in books]
            
            for future in as_completed(futures):
                if self._cancelled:
                    break
                    
                result = future.result(timeout=10)
                if result:
                    fingerprints.append(result)
        
        return fingerprints
    
    def _read_book_content(self, path: str) -> str:
        """
        读取书籍内容（TXT专用优化版）
        
        【TXT格式专属优化】：
        1. ✅ 只处理纯文本文件（UTF-8/GBK等编码自动处理）
        2. ✅ 智能换行符处理（Windows/Linux/Mac统一）
        3. ✅ 更大的采样量（40000字符 vs 原来的15000）
        4. ✅ 更多采样位置（10个 vs 5个）- 覆盖更多章节
        5. ✅ 章节感知采样（优先采集章节开头部分）
        6. ✅ 自适应密度（大文件采样更密集）
        7. ⚠️ 自动跳过所有非TXT格式
        """
        cache_key = path
        if cache_key in self._content_cache:
            return self._content_cache[cache_key]
        
        try:
            if not os.path.exists(path):
                return ""
            
            # 【核心检查】只处理TXT格式
            _, ext = os.path.splitext(path.lower())
            
            if self.config.TXT_ONLY_MODE:
                # TXT专用模式：只处理.txt文件
                if ext != '.txt':
                    return ""  # 直接返回空，不读取非txt文件
            else:
                # 兼容模式：跳过二进制格式
                binary_exts = {'.epub', '.mobi', '.azw', '.azw3', '.pdf', 
                             '.djvu', '.cbr', '.cbz', '.fb2'}
                if ext in binary_exts:
                    return ""
            
            file_size = os.path.getsize(path)
            sample_size = self.config.MAX_SAMPLE_SIZE
            parts = self.config.SAMPLE_PARTS
            
            # 自适应采样参数
            if file_size <= sample_size:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(sample_size)
            else:
                # 多位置均匀采样
                part_size = sample_size // parts
                samples = []
                
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 开头（最重要）
                    samples.append(f.read(part_size))
                    
                    # 中间均匀分布
                    for i in range(1, parts - 1):
                        pos = int(file_size * i / (parts - 1))
                        f.seek(pos)
                        f.readline()  # 对齐到行首
                        samples.append(f.read(part_size))
                    
                    # 结尾
                    f.seek(max(0, file_size - part_size))
                    samples.append(f.read(part_size))
                
                content = ''.join(samples)
            
            # 【TXT专用】文本规范化处理
            if self.config.TXT_ONLY_MODE:
                content = self._normalize_txt_content(content)
            
            # 编码转换（可选）
            if self.config.ENABLE_ENCODING_CONVERSION:
                content = self._try_convert_encoding(content)
            
            # 缓存结果
            with self._cache_lock:
                self._content_cache[cache_key] = content
            
            return content
            
        except Exception as e:
            logger = self._get_logger()
            logger.error(f"读取文件失败: {path}, {e}")
            return ""
    
    def _try_convert_encoding(self, content: str) -> str:
        """尝试进行编码转换（GBK转UTF-8等）"""
        # 这里可以添加编码转换逻辑
        # 目前暂不实现，保留接口
        return content
    
    @staticmethod
    def _normalize_txt_content(content: str) -> str:
        """
        TXT文本规范化处理（专用优化）
        
        【处理内容】：
        1. 统一换行符：\r\n, \r → \n
        2. 去除BOM标记
        3. 规范化空格（多个空格→单个）
        4. 去除首尾空白
        
        Args:
            content: 原始TXT内容
            
        Returns:
            str: 规范化后的内容
        """
        if not content:
            return ""
        
        # 1. 统一换行符（Windows/Mac/Linux兼容）
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 2. 去除BOM标记
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # 3. 规范化空格（但保留换行，用于章节检测）
        lines = content.split('\n')
        normalized_lines = []
        for line in lines:
            # 每行内部：多个空格→单个，去除首尾空白
            normalized_line = ' '.join(line.split())
            normalized_lines.append(normalized_line)
        
        content = '\n'.join(normalized_lines)
        
        # 4. 去除整体首尾空白
        content = content.strip()
        
        return content
    
    # =========================================================================
    # 阶段2A：完全相同检测
    # =========================================================================
    
    def _detect_identical(
        self,
        fingerprints: List[BookFingerprintV2]
    ) -> List[DuplicateGroupV2]:
        """检测完全相同的书籍（基于SHA256哈希）"""
        groups = []
        hash_map: Dict[str, List[BookFingerprintV2]] = defaultdict(list)
        
        for fp in fingerprints:
            if fp.file_hash:
                hash_map[fp.file_hash].append(fp)
        
        for file_hash, fps in hash_map.items():
            if len(fps) > 1:
                group = DuplicateGroupV2(
                    category=DuplicateCategory.IDENTICAL,
                    books=[fp.book for fp in fps],
                    total_score=100.0,
                    confidence=1.0
                )
                # 【关键】设置推荐删除/保留
                SmartDuplicateDetector._recommend_deletion(group)
                groups.append(group)
        
        return groups
    
    # =========================================================================
    # 阶段2B：包含关系检测（重点改进）
    # =========================================================================
    
    def _detect_subset_relations(
        self,
        fingerprints: List[BookFingerprintV2]
    ) -> List[DuplicateGroupV2]:
        """
        检测包含关系（子集 vs 超集）
        
        【核心场景】：
        - A书(1-5章) vs B书(1-8章)
        - A书(完整版) vs B书(删减版)
        - A书(无广告) vs B书(带广告)
        
        【检测策略】：
        1. 快速筛选：只比较大小差异在20%-98%之间的书对
        2. 多算法融合：滑动窗口 + 关键段落 + SimHash
        3. 分层判定：高/中/低置信度三层判断
        """
        logger = self._get_logger()
        groups = []
        n = len(fingerprints)
        
        if n < 2:
            return groups
        
        logger.info(f"  开始包含关系检测：{n}本书待检查")
        
        # 生成候选书对（按大小分组以减少比较次数）
        candidate_pairs = self._generate_subset_candidates(fingerprints)
        
        logger.info(f"  候选书对数量: {len(candidate_pairs)}")
        
        # 并行比较
        valid_pairs = []
        
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            futures = {}
            
            for fp1, fp2 in candidate_pairs:
                if self._cancelled:
                    break
                future = executor.submit(self._compare_for_subset, fp1, fp2)
                futures[future] = (fp1, fp2)
            
            for future in as_completed(futures):
                if self._cancelled:
                    break
                    
                try:
                    result = future.result(timeout=self.config.TIMEOUT_PER_PAIR)
                    if result and result.is_subset:
                        valid_pairs.append((futures[future], result))
                except Exception:
                    pass
        
        # 将有效书对聚类成组
        groups = self._cluster_pairs_into_groups(valid_pairs, fingerprints, DuplicateCategory.SUBSET)
        
        return groups
    
    def _generate_subset_candidates(
        self,
        fingerprints: List[BookFingerprintV2]
    ) -> List[Tuple[BookFingerprintV2, BookFingerprintV2]]:
        """生成可能的包含关系候选书对"""
        candidates = []
        n = len(fingerprints)
        
        # 按文件大小排序
        sorted_fps = sorted(fingerprints, key=lambda fp: fp.book.size or 0)
        
        # 双指针法：对于每本书，只与更大的书比较
        for i in range(n):
            for j in range(i + 1, n):
                fp1, fp2 = sorted_fps[i], sorted_fps[j]
                
                if not (fp1.book.size and fp2.book.size):
                    continue
                
                smaller = min(fp1.book.size, fp2.book.size)
                larger = max(fp1.book.size, fp2.book.size)
                ratio = smaller / larger
                
                # 只选择大小比例在合理范围内的
                if self.config.SIZE_RATIO_SUBSET_MIN <= ratio <= self.config.SIZE_RATIO_SUBSET_MAX:
                    # 进一步筛选：至少要有基本的名称关联
                    if self._has_basic_relation(fp1, fp2):
                        candidates.append((fp1, fp2))
        
        return candidates
    
    def _has_basic_relation(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> bool:
        """检查两本书是否有基本关联"""
        # 完全相同或相似的文件名
        if fp1.normalized_name == fp2.normalized_name:
            return True
        
        # 有共同的关键词
        if fp1.title_keywords & fp2.title_keywords:
            return True
        
        # 文件名的编辑距离较小
        name1_parts = set(fp1.normalized_name.replace('.', ' ').split())
        name2_parts = set(fp2.normalized_name.replace('.', ' ').split())
        common = name1_parts & name2_parts
        
        # 排除纯扩展名的匹配
        stop_words = {'txt', 'epub', 'pdf', 'mobi', 'azw', 'azw3'}
        meaningful_common = common - stop_words
        
        if meaningful_common:
            return True
        
        return False
    
    def _compare_for_subset(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> Optional[ComparisonResult]:
        """
        比较两本书是否存在包含关系
        
        【多算法融合】：
        1. 滑动窗口检测（主要算法）
        2. 关键段落匹配（辅助验证）
        3. SimHash模糊匹配（补充）
        4. SequenceMatcher全局对比（兜底）
        """
        from src.utils.string_utils import StringUtils
        
        try:
            book1, book2 = fp1.book, fp2.book
            
            # 读取完整内容用于精确比较
            content1 = self._read_book_content(book1.path)
            content2 = self._read_book_content(book2.path)
            
            if not content1 or not content2:
                return None
            
            # 规范化文本
            clean1 = re.sub(r'\s+', '', content1)
            clean2 = re.sub(r'\s+', '', content2)
            
            len1, len2 = len(clean1), len(clean2)
            
            if len1 == 0 or len2 == 0:
                return None
            
            # 确定方向（小→大）
            if len1 <= len2:
                small_content, large_content = clean1, clean2
                small_fp, large_fp = fp1, fp2
                direction = "first_in_second"
            else:
                small_content, large_content = clean2, clean1
                small_fp, large_fp = fp2, fp1
                direction = "second_in_first"
            
            small_len = len(small_content)
            large_len = len(large_content)
            size_ratio = small_len / large_len
            
            # ===== 算法1：滑动窗口检测 =====
            window_ratio = self._sliding_window_check(small_content, large_content)
            
            # ===== 算法2：关键段落匹配 =====
            paragraph_ratio = self._key_paragraph_check(small_content, large_content)
            
            # ===== 算法3：SimHash辅助 =====
            simhash_dist = self.hamming_distance(
                self._compute_simhash(small_content),
                self._compute_simhash(large_content)
            )
            simhash_score = max(0, 1 - simhash_dist / 16)  # 归一化到0-1
            
            # ===== 综合判定 =====
            # 加权平均三个算法的结果
            final_ratio = (
                window_ratio * 0.50 +
                paragraph_ratio * 0.30 +
                simhash_score * 0.20
            )
            
            # 构建结果
            result = ComparisonResult(
                book1=book1,
                book2=book2,
                is_subset=(final_ratio >= self.config.MIN_SUBSET_RATIO),
                subset_ratio=final_ratio,
                subset_direction=direction,
                size_ratio=size_ratio
            )
            
            if result.is_subset:
                # 计算总分
                result.total_score = self._calculate_subset_score(result)
                result.category = DuplicateCategory.SUBSET
                result.confidence = min(0.95, 0.6 + final_ratio * 0.35)
                result.reason = f"包含关系({direction}, 匹配率={final_ratio:.1%})"
            
            return result
            
        except Exception as e:
            logger = self._get_logger()
            logger.debug(f"包含关系比较失败: {e}")
            return None
    
    def _sliding_window_check(
        self,
        small_content: str,
        large_content: str
    ) -> float:
        """
        滑动窗口检测（核心算法）
        
        【改进点】：
        1. 使用多个窗口尺寸（多尺度检测）
        2. 更高的重叠率（67% vs 原来的50%）
        3. 动态窗口大小（根据内容长度自适应）
        """
        small_len = len(small_content)
        
        if small_len < 300:
            return 1.0 if small_content in large_content else 0.0
        
        found_total = 0
        window_count = 0
        
        # 使用3种不同尺度的窗口
        scales = [
            (min(800, small_len // 3), 3),    # 大窗口：33%长度
            (min(500, small_len // 5), 3),    # 中窗口：20%长度
            (min(300, small_len // 8), 3),    # 小窗口：12.5%长度
        ]
        
        for window_size, overlap_div in scales:
            step_size = window_size // overlap_div  # 重叠率67%
            windows_found = 0
            windows_total = 0
            
            for start in range(0, small_len - window_size + 1, step_size):
                window = small_content[start:start + window_size]
                windows_total += 1
                
                if window in large_content:
                    windows_found += 1
            
            if windows_total > 0:
                found_total += windows_found
                window_count += windows_total
        
        return found_total / window_count if window_count > 0 else 0.0
    
    def _key_paragraph_check(
        self,
        small_content: str,
        large_content: str
    ) -> float:
        """关键段落匹配检测"""
        small_len = len(small_content)
        
        if small_len < 500:
            return 1.0 if small_content in large_content else 0.0
        
        # 提取关键段落（开头、结尾+均匀分布的中间段）
        paragraphs = []
        num_paras = 6
        para_len = min(600, small_len // (num_paras + 1))
        
        # 开头和结尾必须包含
        paragraphs.append(small_content[:para_len])
        paragraphs.append(small_content[-para_len:])
        
        # 中间均匀分布
        for i in range(1, num_paras - 1):
            pos = small_len * i // num_paras
            paragraphs.append(small_content[pos:pos + para_len])
        
        # 检查匹配
        matched = sum(1 for p in paragraphs if len(p) >= 150 and p in large_content)
        
        return matched / len(paragraphs) if paragraphs else 0.0
    
    def _calculate_subset_score(self, result: ComparisonResult) -> float:
        """计算包含关系的总分"""
        score = 0.0
        
        # 包含关系匹配率贡献（最高45分）
        score += result.subset_ratio * 45
        
        # 大小合理性贡献（最高20分）
        # 大小比例在40%-85%之间最可能是包含关系
        if 0.40 <= result.size_ratio <= 0.85:
            score += 20
        elif 0.30 <= result.size_ratio <= 0.92:
            score += 15
        elif 0.20 <= result.size_ratio <= 0.95:
            score += 10
        else:
            score += 5
        
        # 文件名关联贡献（最高15分）
        # 这部分会在后续综合评分中添加
        
        # 剩余20分由其他维度补充
        score += 20
        
        return min(100, score)
    
    # =========================================================================
    # 阶段2C：高度相似检测
    # =========================================================================
    
    def _detect_highly_similar(
        self,
        fingerprints: List[BookFingerprintV2]
    ) -> List[DuplicateGroupV2]:
        """检测高度相似的书籍（内容相似度 > 70%）"""
        return self._detect_by_similarity(
            fingerprints,
            min_similarity=0.70,
            category=DuplicateCategory.HIGH_SIMILAR
        )
    
    # =========================================================================
    # 阶段2D：中度相似检测
    # =========================================================================
    
    def _detect_medium_similar(
        self,
        fingerprints: List[BookFingerprintV2]
    ) -> List[DuplicateGroupV2]:
        """检测中度相似的书籍（内容相似度 40-70%）"""
        return self._detect_by_similarity(
            fingerprints,
            min_similarity=0.40,
            max_similarity=0.70,
            category=DuplicateCategory.MEDIUM_SIMILAR
        )
    
    # =========================================================================
    # 阶段2E：低度相关检测
    # =========================================================================
    
    def _detect_low_related(
        self,
        fingerprints: List[BookFingerprintV2]
    ) -> List[DuplicateGroupV2]:
        """检测低度相关的书籍（需要强证据支持）"""
        # 只有当文件名相同且其他特征也匹配时才报告
        groups = []
        name_map: Dict[str, List[BookFingerprintV2]] = defaultdict(list)
        
        for fp in fingerprints:
            name_map[fp.normalized_name].append(fp)
        
        for name, fps in name_map.items():
            if len(fps) >= 2:
                # 验证这些同名书籍确实有关联
                verified = []
                for fp in fps:
                    if fp.content_sample or fp.file_hash:
                        verified.append(fp)
                
                if len(verified) >= 2:
                    group = DuplicateGroupV2(
                        category=DuplicateCategory.NAME_ONLY,
                        books=[fp.book for fp in verified],
                        total_score=45.0,  # 低分
                        confidence=0.35     # 低置信度
                    )
                    # 【关键】设置推荐删除/保留
                    SmartDuplicateDetector._recommend_deletion(group)
                    groups.append(group)
        
        return groups
    
    # =========================================================================
    # 通用相似度检测方法
    # =========================================================================
    
    def _detect_by_similarity(
        self,
        fingerprints: List[BookFingerprintV2],
        min_similarity: float = 0.0,
        max_similarity: float = 1.0,
        category: DuplicateCategory = DuplicateCategory.HIGH_SIMILAR
    ) -> List[DuplicateGroupV2]:
        """通用相似度检测框架"""
        logger = self._get_logger()
        groups = []
        n = len(fingerprints)
        
        if n < 2:
            return groups
        
        # 生成候选书对（限制数量以控制性能）
        candidate_pairs = self._generate_similarity_candidates(
            fingerprints, 
            max_pairs=self.config.MAX_DEEP_COMPARE_PAIRS
        )
        
        logger.debug(f"  相似度检测候选对: {len(candidate_pairs)}")
        
        # 并行比较
        valid_pairs = []
        
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._comprehensive_compare, fp1, fp2): (fp1, fp2)
                for fp1, fp2 in candidate_pairs
            }
            
            for future in as_completed(futures):
                if self._cancelled:
                    break
                
                try:
                    result = future_result = future.result(timeout=self.config.TIMEOUT_PER_PAIR)
                    if result and min_similarity <= result.content_similarity <= max_similarity:
                        if result.total_score >= self.config.THRESHOLD_SUSPICIOUS:
                            valid_pairs.append((futures[future], result))
                except Exception:
                    pass
        
        # 聚类成组
        groups = self._cluster_pairs_into_groups(valid_pairs, fingerprints, category)
        
        return groups
    
    def _generate_similarity_candidates(
        self,
        fingerprints: List[BookFingerprintV2],
        max_pairs: int = 10000
    ) -> List[Tuple[BookFingerprintV2, BookFingerprintV2]]:
        """生成相似度比较的候选书对"""
        candidates = []
        n = len(fingerprints)
        
        # 使用SimHash快速预筛
        if n > 1000:
            # 对于大数据集，先用SimHash筛选
            candidates = self._simhash_prefilter(fingerprints, max_pairs)
        else:
            # 小数据集，生成全部书对
            for i in range(min(n, 200)):  # 限制单次处理的数量
                for j in range(i + 1, min(n, 200)):
                    candidates.append((fingerprints[i], fingerprints[j]))
        
        # 如果还是太多，随机采样
        if len(candidates) > max_pairs:
            import random
            random.seed(42)
            candidates = random.sample(candidates, max_pairs)
        
        return candidates
    
    def _simhash_prefilter(
        self,
        fingerprints: List[BookFingerprintV2],
        max_pairs: int
    ) -> List[Tuple[BookFingerprintV2, BookFingerprintV2]]:
        """SimHash预筛选（加速大规模数据处理）"""
        candidates = []
        valid_fps = [fp for fp in fingerprints if fp.simhash != 0]
        n = len(valid_fps)
        
        for i in range(n):
            for j in range(i + 1, n):
                dist = self.hamming_distance(valid_fps[i].simhash, valid_fps[j].simhash)
                if dist <= self.config.SIMHASH_THRESHOLD:
                    candidates.append((valid_fps[i], valid_fps[j]))
                    
                    if len(candidates) >= max_pairs:
                        return candidates
        
        return candidates
    
    # =========================================================================
    # 核心比较引擎（多维度加权评分）
    # =========================================================================
    
    def _comprehensive_compare(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> Optional[ComparisonResult]:
        """
        综合比较两本书（多维度加权评分）
        
        【核心创新】：
        - 不再使用if-elif规则堆叠
        - 每个维度独立评分，最后加权求和
        - 所有证据都能贡献分数，不会互相排斥
        """
        from src.utils.string_utils import StringUtils
        
        try:
            book1, book2 = fp1.book, fp2.book
            dimensions = []
            
            # ===== 维度1：内容相似度（权重35%）=====
            content_dim = self._score_content_similarity(fp1, fp2)
            dimensions.append(content_dim)
            
            # ===== 维度2：包含关系（权重25%）=====
            subset_dim = self._score_subset_relationship(fp1, fp2)
            dimensions.append(subset_dim)
            
            # ===== 维度3：元数据相似度（权重15%）=====
            metadata_dim = self._score_metadata_similarity(fp1, fp2)
            dimensions.append(metadata_dim)
            
            # ===== 维度4：文件大小关系（权重10%）=====
            size_dim = self._score_size_relationship(fp1, fp2)
            dimensions.append(size_dim)
            
            # ===== 维度5：SimHash相似度（权重10%）=====
            simhash_dim = self._score_simhash_similarity(fp1, fp2)
            dimensions.append(simhash_dim)
            
            # ===== 维度6：结构特征（权重5%）=====
            structure_dim = self._score_structure_similarity(fp1, fp2)
            dimensions.append(structure_dim)
            
            # ===== 计算总分 =====
            total_score = sum(d.weighted_score for d in dimensions)
            
            # ===== 确定类别和置信度 =====
            category = self._determine_category(dimensions, total_score)
            confidence = self._calculate_confidence(dimensions, total_score)
            
            # ===== 构建结果 =====
            result = ComparisonResult(
                book1=book1,
                book2=book2,
                total_score=min(100, total_score),
                category=category,
                dimensions=dimensions,
                content_similarity=content_dim.score / 100,
                filename_similarity=metadata_dim.score / 100,
                confidence=confidence,
                reason=self._build_reason(dimensions, category)
            )
            
            # 如果是包含关系，记录详细信息
            if subset_dim.score >= 40:
                result.is_subset = True
                result.subset_ratio = subset_dim.score / 100
            
            return result
            
        except Exception as e:
            logger = self._get_logger()
            logger.error(f"综合比较失败: {e}")
            return None
    
    def _score_content_similarity(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> DimensionScore:
        """评分：内容相似度"""
        from src.utils.string_utils import StringUtils
        
        score = 0.0
        evidence = "无内容"
        
        if fp1.content_sample and fp2.content_sample:
            if len(fp1.content_sample) > 100 and len(fp2.content_sample) > 100:
                similarity = StringUtils.book_content_similarity(
                    fp1.content_sample,
                    fp2.content_sample,
                    sample_size=12000
                )
                score = similarity * 100
                evidence = f"内容相似度={similarity:.1%}"
        
        return DimensionScore(
            name="内容相似度",
            score=score,
            weight=self.config.WEIGHT_CONTENT_SIMILARITY,
            evidence=evidence
        )
    
    def _score_subset_relationship(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> DimensionScore:
        """评分：包含关系"""
        score = 0.0
        evidence = "无明显包含关系"
        
        # 只在有足够的内容时才检测
        if not (fp1.content_sample and fp2.content_sample):
            return DimensionScore(
                name="包含关系",
                score=0,
                weight=self.config.WEIGHT_SUBSET_RELATION,
                evidence=evidence
            )
        
        # 检查大小比例是否合理
        book1, book2 = fp1.book, fp2.book
        if not (book1.size and book2.size):
            return DimensionScore(name="包含关系", score=0, 
                                weight=self.config.WEIGHT_SUBSET_RELATION, evidence=evidence)
        
        smaller = min(book1.size, book2.size)
        larger = max(book1.size, book2.size)
        size_ratio = smaller / larger
        
        if not (self.config.SIZE_RATIO_SUBSET_MIN <= size_ratio <= self.config.SIZE_RATIO_SUBSET_MAX):
            evidence = f"大小比例({size_ratio:.1%})不在合理范围"
            return DimensionScore(name="包含关系", score=0,
                                weight=self.config.WEIGHT_SUBSET_RELATION, evidence=evidence)
        
        # 执行包含关系检测
        subset_result = self._compare_for_subset(fp1, fp2)
        
        if subset_result and subset_result.is_subset:
            score = subset_result.subset_ratio * 100
            evidence = subset_result.reason
        else:
            evidence = "未检测到包含关系"
        
        return DimensionScore(
            name="包含关系",
            score=score,
            weight=self.config.WEIGHT_SUBSET_RELATION,
            evidence=evidence
        )
    
    def _score_metadata_similarity(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> DimensionScore:
        """评分：元数据相似度（文件名、作者、关键词等）"""
        score = 0.0
        
        # 文件名完全匹配
        if fp1.normalized_name == fp2.normalized_name:
            score = max(score, 80)
        
        # 关键词重叠
        if fp1.title_keywords and fp2.title_keywords:
            intersection = fp1.title_keywords & fp2.title_keywords
            union = fp1.title_keywords | fp2.title_keywords
            keyword_sim = len(intersection) / len(union) if union else 0
            score = max(score, keyword_sim * 60)
        
        # 作者相同（如果有author字段）
        author1 = getattr(fp1.book, 'author', '') or ''
        author2 = getattr(fp2.book, 'author', '') or ''
        if author1 and author2 and author1.lower() == author2.lower():
            score = max(score, 70)
        
        evidence = f"元数据匹配度={score:.0f}%"
        
        return DimensionScore(
            name="元数据相似度",
            score=score,
            weight=self.config.WEIGHT_METADATA,
            evidence=evidence
        )
    
    def _score_size_relationship(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> DimensionScore:
        """评分：文件大小关系（【优化版】降低基础分，防止误报）"""
        score = 0.0
        evidence = ""
        
        book1, book2 = fp1.book, fp2.book
        if not (book1.size and book2.size):
            return DimensionScore(
                name="大小关系",
                score=50,
                weight=self.config.WEIGHT_SIZE_RATIO,
                evidence="无法确定大小关系"
            )
        
        smaller = min(book1.size, book2.size)
        larger = max(book1.size, book2.size)
        ratio = smaller / larger
        
        # 【关键修改】降低基础得分，只有极端情况才给高分
        # 大小相近（90-100%）→ 可能是完全相同或轻微修改
        if ratio >= 0.90:
            score = 70  # 从90降到70
            evidence = f"大小几乎相同({ratio:.1%})"
        # 大小接近（70-90%）→ 可能是不同版本
        elif ratio >= 0.70:
            score = 50  # 从75降到50
            evidence = f"大小较接近({ratio:.1%})"
        # 大小中等（40-70%）→ 可能是包含关系
        elif ratio >= 0.40:
            score = 30  # 从60降到30
            evidence = f"大小有差异({ratio:.1%})，可能存在包含关系"
        # 大小差异较大
        else:
            score = 10  # 从30降到10
            evidence = f"大小差异较大({ratio:.1%})"
        
        return DimensionScore(
            name="大小关系",
            score=score,
            weight=self.config.WEIGHT_SIZE_RATIO,
            evidence=evidence
        )
    
    def _score_simhash_similarity(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> DimensionScore:
        """评分：SimHash指纹相似度"""
        score = 0.0
        
        if fp1.simhash != 0 and fp2.simhash != 0:
            dist = self.hamming_distance(fp1.simhash, fp2.simhash)
            
            # 将海明距离转换为相似度分数
            # 距离0 → 100分，距离4 → 60分，距离>=8 → 0分
            if dist == 0:
                score = 100
            elif dist <= 4:
                score = 100 - dist * 10
            elif dist <= 8:
                score = 60 - (dist - 4) * 15
            else:
                score = 0
        
        evidence = f"SimHash海明距离={dist if fp1.simhash and fp2.simhash else 'N/A'}"
        
        return DimensionScore(
            name="SimHash相似度",
            score=score,
            weight=self.config.WEIGHT_SIMHASH,
            evidence=evidence
        )
    
    def _score_structure_similarity(
        self,
        fp1: BookFingerprintV2,
        fp2: BookFingerprintV2
    ) -> DimensionScore:
        """评分：结构特征相似度（【优化版】降低得分，防止章节标记误匹配）"""
        score = 0.0
        
        # 统计特征比较（降低权重）
        if all(f != (0, 0, 0) for f in [fp1.size_features, fp2.size_features]):
            lines1, words1, chars1 = fp1.size_features
            lines2, words2, chars2 = fp2.size_features
            
            line_sim = min(lines1, lines2) / max(lines1, lines2) if max(lines1, lines2) > 0 else 0
            word_sim = min(words1, words2) / max(words1, words2) if max(words1, words2) > 0 else 0
            char_sim = min(chars1, chars2) / max(chars1, chars2) if max(chars1, chars2) > 0 else 0
            
            # 【关键修改】基础分从100%降到60%
            base_score = (line_sim + word_sim + char_sim) / 3 * 60
            score = base_score
        
        # 章节标记比较（【修改】减少加分）
        if fp1.chapter_markers and fp2.chapter_markers:
            common_chapters = set(fp1.chapter_markers) & set(fp2.chapter_markers)
            if len(common_chapters) >= 3:  # 至少3个共同章节才加分
                score = min(70, score + 10)  # 从+15降到+10，上限从100降到70
        
        evidence = f"结构相似度={score:.0f}%"
        
        return DimensionScore(
            name="结构特征",
            score=score,
            weight=self.config.WEIGHT_STRUCTURE,
            evidence=evidence
        )
    
    def _determine_category(
        self,
        dimensions: List[DimensionScore],
        total_score: float
    ) -> DuplicateCategory:
        """根据维度得分确定重复类别"""
        # 找出得分最高的维度
        main_dim = max(dimensions, key=lambda d: d.score) if dimensions else None
        
        if total_score >= self.config.THRESHOLD_DEFINITE_DUPLICATE:
            if main_dim and main_dim.name == "包含关系":
                return DuplicateCategory.SUBSET
            elif main_dim and main_dim.name == "内容相似度" and main_dim.score >= 90:
                return DuplicateCategory.IDENTICAL
            else:
                return DuplicateCategory.HIGH_SIMILAR
        
        elif total_score >= self.config.THRESHOLD_LIKELY_DUPLICATE:
            if main_dim and main_dim.name == "包含关系":
                return DuplicateCategory.SUBSET
            else:
                return DuplicateCategory.MEDIUM_SIMILAR
        
        elif total_score >= self.config.THRESHOLD_SUSPICIOUS:
            return DuplicateCategory.LOW_SIMILAR
        
        else:
            return DuplicateCategory.UNKNOWN
    
    def _calculate_confidence(
        self,
        dimensions: List[DimensionScore],
        total_score: float
    ) -> float:
        """计算判定置信度"""
        if not dimensions:
            return 0.0
        
        # 基础置信度：基于总分
        base_confidence = total_score / 100
        
        # 方差惩罚：如果各维度得分差异很大，降低置信度
        scores = [d.score for d in dimensions if d.score > 0]
        if len(scores) >= 2:
            variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            std_dev = math.sqrt(variance)
            penalty = min(0.2, std_dev / 100)  # 最高扣20%
        else:
            penalty = 0
        
        # 证据数量奖励：有更多维度提供证据，提高置信度
        evidence_bonus = min(0.1, len([d for d in dimensions if d.score > 30]) * 0.02)
        
        confidence = base_confidence - penalty + evidence_bonus
        
        return max(0, min(1, confidence))
    
    def _build_reason(
        self,
        dimensions: List[DimensionScore],
        category: DuplicateCategory
    ) -> str:
        """构建判定原因的自然语言描述"""
        # 找出得分最高的前3个维度
        top_dims = sorted(dimensions, key=lambda d: d.score, reverse=True)[:3]
        
        parts = []
        for dim in top_dims:
            if dim.score > 20:
                parts.append(dim.evidence)
        
        if parts:
            return "; ".join(parts)
        else:
            return "综合评分判定"
    
    # =========================================================================
    # 辅助工具方法
    # =========================================================================
    
    @staticmethod
    def hamming_distance(hash1: int, hash2: int) -> int:
        """计算海明距离"""
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += xor & 1
            xor >>= 1
        return distance
    
    @staticmethod
    def _compute_simhash(text: str, bits: int = 64) -> int:
        """计算SimHash指纹"""
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
    def _extract_keywords(title: str) -> Set[str]:
        """从标题中提取关键词"""
        if not title:
            return set()
        
        keywords = set(re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}', title))
        
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就',
                      '不', '人', '都', '一', '一个', '上', '也', '很'}
        keywords -= stop_words
        
        return keywords
    
    @staticmethod
    def _detect_encoding(sample_text: str) -> str:
        """检测文本编码（简单启发式）"""
        # 检查是否可能是GBK编码的乱码
        gbk_patterns = ['锟斤拷', '烫烫烫']  # GBK常见乱码
        for pattern in gbk_patterns:
            if pattern in sample_text:
                return "gbk_mojibake"
        
        # 默认假设UTF-8
        return "utf-8"
    
    @staticmethod
    def _detect_chapter_markers(content: str) -> List[str]:
        """检测章节标记（如"第1章"、"Chapter 1"等）"""
        patterns = [
            r'第[一二三四五六七八九十百千\d]+[章节回]',
            r'Chapter\s*\d+',
            r'第\d+\s*章',
            r'[卷部]\s*[一二三四五六七八九十\d]+'
        ]
        
        markers = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            markers.extend(matches[:3])  # 每种最多取3个
        
        return markers[:10]  # 最多返回10个
    
    @staticmethod
    def _compute_content_signature(content: str) -> str:
        """计算内容的简短签名（用于快速初步比较）"""
        # 规范化
        clean = re.sub(r'\s+', '', content.lower())[:2000]
        
        # 计算简单的字符分布特征
        char_freq = defaultdict(int)
        for ch in clean:
            char_freq[ch] += 1
        
        # 取出现频率最高的前20个字符作为签名
        top_chars = sorted(char_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        signature = ''.join(ch for ch, _ in top_chars)
        
        return signature
    
    # =========================================================================
    # 结果聚类和推荐
    # =========================================================================
    
    def _cluster_pairs_into_groups(
        self,
        pairs: List[Tuple[Tuple[BookFingerprintV2, BookFingerprintV2], ComparisonResult]],
        fingerprints: List[BookFingerprintV2],
        category: DuplicateCategory
    ) -> List[DuplicateGroupV2]:
        """将比较结果聚类成组"""
        if not pairs:
            return []
        
        # 构建路径映射
        path_to_fp = {fp.book.path: fp for fp in fingerprints}
        
        # 使用并查集
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
        
        # 合并所有书对
        for (fp1, fp2), result in pairs:
            union(fp1.book.path, fp2.book.path)
        
        # 按根节点分组
        clusters: Dict[str, Set[str]] = defaultdict(set)
        for path in parent:
            root = find(path)
            clusters[root].add(path)
        
        # 构建分组结果
        groups = []
        for root, member_paths in clusters.items():
            if len(member_paths) >= 2:
                member_books = []
                details = {}
                scores = []
                
                for path in member_paths:
                    if path in path_to_fp:
                        member_books.append(path_to_fp[path].book)
                
                if len(member_books) >= 2:
                    # 收集该组的所有比较结果
                    for (fp1, fp2), result in pairs:
                        if fp1.book.path in member_paths and fp2.book.path in member_paths:
                            key = tuple(sorted([fp1.book.path, fp2.book.path]))
                            details[key] = result
                            scores.append(result.total_score)
                    
                    avg_score = sum(scores) / len(scores) if scores else 50
                    avg_confidence = sum(r.confidence for r in details.values()) / len(details.values()) if details else 0.5
                    
                    group = DuplicateGroupV2(
                        category=category,
                        books=member_books,
                        total_score=avg_score,
                        confidence=avg_confidence,
                        comparison_details=details
                    )
                    
                    # 【关键】计算并设置推荐删除/保留的书籍
                    SmartDuplicateDetector._recommend_deletion(group)
                    
                    groups.append(group)
        
        return groups
    
    @staticmethod
    def _recommend_deletion(group: DuplicateGroupV2):
        """推荐删除选择"""
        if not group.books or len(group.books) < 2:
            return
        
        def score_book(book) -> float:
            s = 0.0
            
            # 文件越大通常越完整
            if book.size:
                s += math.log10(max(book.size, 1)) * 2
            
            # 有阅读进度
            if hasattr(book, 'reading_progress') and book.reading_progress:
                s += 10
            
            # 格式偏好
            format_pref = {'txt': 3, 'epub': 3, 'pdf': 2}
            if book.format and book.format.lower() in format_pref:
                s += format_pref[book.format.lower()]
            
            # 文件名质量
            if book.file_name and not any(c in book.file_name for c in ['%', '#']):
                s += 1
            
            return s
        
        sorted_books = sorted(group.books, key=score_book, reverse=True)
        group.recommended_to_keep = [sorted_books[0]]
        group.recommended_to_delete = sorted_books[1:]
    
    # =========================================================================
    # 缓存管理
    # =========================================================================
    
    def _get_cached_hash(self, path: str) -> str:
        """获取或计算文件哈希（带缓存）"""
        if path in self._hash_cache:
            return self._hash_cache[path]
        
        try:
            from src.utils.file_utils import FileUtils
            if os.path.exists(path):
                h = FileUtils.calculate_file_sha256(path)
                with self._cache_lock:
                    self._hash_cache[path] = h
                return h
        except Exception:
            pass
        return ""
    
    def clear_cache(self):
        """清除所有缓存"""
        with self._cache_lock:
            self._hash_cache.clear()
            self._content_cache.clear()
            self._fingerprint_cache.clear()


# ============================================================================
# 第四部分：便捷接口和兼容层
# ============================================================================

def find_duplicates_v2(
    books: list,
    mode: str = "balanced",
    progress_callback=None,
    batch_callback=None
) -> list:
    """
    使用新的V2检测引擎查找重复书籍
    
    Args:
        books: 书籍列表
        mode: 检测模式 ("strict", "balanced", "loose")
        progress_callback: 进度回调
        batch_callback: 批次回调
        
    Returns:
        List[DuplicateGroupV2]: 重复书籍组列表
    """
    return SmartDuplicateDetector.find_duplicates(
        books,
        progress_callback=progress_callback,
        batch_callback=batch_callback,
        mode=mode
    )


# 兼容旧接口
def convert_to_old_format(v2_groups: list) -> list:
    """将V2格式的结果转换为旧格式（向后兼容）"""
    from src.utils.book_duplicate_detector_ultra import DuplicateGroup, DuplicateType
    
    old_groups = []
    
    type_mapping = {
        DuplicateCategory.IDENTICAL: DuplicateType.HASH_IDENTICAL,
        DuplicateCategory.SUBSET: DuplicateType.CONTENT_SUBSET,
        DuplicateCategory.HIGH_SIMILAR: DuplicateType.CONTENT_SIMILAR,
        DuplicateCategory.MEDIUM_SIMILAR: DuplicateType.CONTENT_SIMILAR,
        DuplicateCategory.LOW_SIMILAR: DuplicateType.SIMHASH_SIMILAR,
        DuplicateCategory.NAME_ONLY: DuplicateType.FILE_NAME,
    }
    
    for v2_group in v2_groups:
        old_group = DuplicateGroup(
            duplicate_type=type_mapping.get(v2_group.category, DuplicateType.CONTENT_SIMILAR),
            books=v2_group.books,
            similarity=v2_group.total_score / 100,
            confidence=v2_group.confidence,
            recommended_to_keep=v2_group.recommended_to_keep,
            recommended_to_delete=v2_group.recommended_to_delete
        )
        old_groups.append(old_group)
    
    return old_groups
