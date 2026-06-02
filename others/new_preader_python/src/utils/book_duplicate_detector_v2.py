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
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 【修复】添加全局logger（与Ultra保持一致）
from src.utils.logger import get_logger
logger = get_logger(__name__)


# ============================================================================
# 第一部分：数据结构定义（完全兼容Ultra）
# ============================================================================

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
    recommended_to_keep: List['Book'] = None
    recommended_to_delete: List['Book'] = None
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
    """
    
    # ===== Ultra原始参数（V3优化版）=====
    SIMHASH_BITS = 64
    SIMHASH_THRESHOLD = 3  # SimHash汉明距离阈值
    
    # ===== V3优化后的规则参数（平衡灵敏度和精确度）=====
    MIN_CONTENT_SIMILARITY = 0.30      # 规则A：高内容相似度门槛（回调到0.30）
    HIGH_CONFIDENCE = 0.74             # 最终置信度门槛（回调到0.74）
    SUBSET_MIN_RATIO = 0.50            # 包含关系最低匹配率（回调到0.50）
    SUBSET_SIZE_MIN_RATIO = 0.08       # 大小差异下限（回调到0.08）
    SUBSET_SIZE_MAX_RATIO = 0.95       # 大小差异上限

    # ===== 【新增】防误报参数 =====
    MIN_FILE_SIZE_FOR_DETECTION = 1024   # 最小文件大小(字节)，低于此值的书籍跳过深度检测
    SHORT_CONTENT_THRESHOLD = 2000       # 短篇内容阈值(字节)
    FEATURE_SIMILARITY_WEIGHT = 0.15
    
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
                    executor.shutdown(wait=False, cancel_futures=True)
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
        
        fingerprints = self._compute_all_fingerprints(
            books,
            progress_callback=lambda c, t: progress_callback(c // 10, t)
        )
        
        if self.is_cancelled():
            return all_duplicate_groups
        
        # ===== 阶段2：多级过滤检测（完全遵循Ultra流程）=====
        phases = [
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
            if phase_name == "Level 3: 文件名兜底":
                phase_groups = detect_func(remaining_fps, all_duplicate_groups)
            else:
                phase_groups = detect_func(remaining_fps)
            
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
                fp.normalized_name = book.file_name.lower().strip()
                
                fp.file_hash = self._get_cached_hash(book.path)
                
                # 内容采样（根据模式选择大小）
                sample_size = self.SAMPLE_SIZE_V3 if self.ENABLE_ENHANCED_SAMPLING else self.SAMPLE_SIZE_ULTRA
                content = self._read_book_content(book.path, sample_size)
                
                if content:
                    fp.content_sample = content[:5000] if len(content) > 5000 else content
                    fp.simhash = self._compute_simhash(content)
                    
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
        
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            self.register_executor(executor)
            
            futures = [executor.submit(compute_one, book) for book in books]
            
            for future in as_completed(futures):
                if self.is_cancelled():
                    break
                result = future.result(timeout=10)
                if result:
                    fingerprints.append(result)
            
            self.unregister_executor(executor)
        
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
                        content_sim >= 0.28 or  # 【收紧】从0.25提高到0.28
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
                    max_sim >= 0.25 or
                    (max_sim >= 0.18 and has_name_match) or
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
                        (max_sim >= 0.22) or
                        (max_sim >= 0.15 and has_name_match) or
                        (verified_pairs >= max(1, total_possible_pairs * 0.25))
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
            
            with DaemonThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
                self.register_executor(executor)
                
                futures = [executor.submit(check_pair_with_cancel, pair) for pair in pairs_to_check]
                
                for future in as_completed(futures):
                    if self.is_cancelled():
                        break
                    
                    try:
                        result = future.result(timeout=5)
                        if result:
                            pair_key = tuple(sorted([result.book1.path, result.book2.path]))
                            all_similar_pairs.add(pair_key)
                    except Exception:
                        pass
                
                executor.shutdown(wait=False, cancel_futures=True)
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
        详细比较两个书籍指纹（Ultra的多层验证 + V3包含关系增强 + 防误报）
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
            
            # 【V3增强】阶段2.5: 包含关系预检测（针对整本vs章节）
            subset_result = self._check_subset_relation_enhanced(fp1, fp2)
            
            if subset_result and subset_result[0]:  # (is_duplicate, comparison)
                return subset_result[1]  # 返回ComparisonResult
            
            # 阶段3: 计算各维度
            content_similarity = 0.0
            subset_ratio = 0.0  # 【修复】提前初始化，避免UnboundLocalError
            has_enough_content = False
            
            if fp1.content_sample and fp2.content_sample:
                if len(fp1.content_sample) > 100 and len(fp2.content_sample) > 100:
                    has_enough_content = True
                    from src.utils.string_utils import StringUtils
                    content_similarity = StringUtils.book_content_similarity(
                        fp1.content_sample, fp2.content_sample, sample_size=12000
                    )
            
            feature_sim = self._feature_similarity(fp1, fp2)
            
            simhash_dist = float('inf')
            if fp1.simhash != 0 and fp2.simhash != 0:
                simhash_dist = self.hamming_distance(fp1.simhash, fp2.simhash)
            
            size_ratio = 1.0
            if book1.size and book2.size and max(book1.size, book2.size) > 0:
                size_ratio = min(book1.size, book2.size) / max(book1.size, book2.size)
            
            # 阶段4: Ultra多层验证判断（规则A/B/C/D）
            is_duplicate = False
            duplicate_types = []
            confidence = 0.0
            
            # 规则A: 高内容相似度
            if has_enough_content and content_similarity >= self.MIN_CONTENT_SIMILARITY:
                is_duplicate = True
                duplicate_types.append(DuplicateType.CONTENT_SIMILAR)
                
                base_confidence = 0.58
                content_bonus = min(0.25, content_similarity * 0.42)
                feature_bonus = feature_sim * self.FEATURE_SIMILARITY_WEIGHT
                
                confidence = min(0.94, base_confidence + content_bonus + feature_bonus)
                
                if file_name_match:
                    confidence = min(0.96, confidence + 0.03)
            
            # 规则B: 包含关系（使用V3增强检测结果或Ultra原逻辑）
            elif hasattr(self, '_last_subset_result') and self._last_subset_result[0]:
                # 使用V3增强的包含关系结果
                is_duplicate = True
                duplicate_types.append(DuplicateType.CONTENT_SUBSET)
                subset_ratio = self._last_subset_result[1]
                confidence = 0.65 + subset_ratio * 0.20
            else:
                # 使用Ultra原生的包含关系检测
                subset_relationship = None
                subset_ratio = 0.0
                
                if book1.size and book2.size and 0.08 < size_ratio < 0.92:
                    try:
                        from src.utils.string_utils import StringUtils
                        subset_rel, sub_rat = StringUtils.check_subset_relationship(book1, book2)
                        
                        if subset_rel in ["subset", "superset"] and sub_rat >= self.SUBSET_MIN_RATIO:
                            subset_relationship = subset_rel
                            subset_ratio = sub_rat
                    except Exception as e:
                        logger.debug(f"包含关系检查异常: {e}")
                
                if subset_relationship in ["subset", "superset"]:
                    is_duplicate = True
                    duplicate_types.append(DuplicateType.CONTENT_SUBSET)
                    
                    if subset_ratio >= self.SUBSET_MIN_RATIO:
                        confidence = 0.65 + subset_ratio * 0.20
                    elif subset_ratio >= 0.48 and size_ratio < 0.75:
                        if file_name_match or feature_sim >= 0.60:
                            confidence = 0.65 + subset_ratio * 0.20
                    elif subset_ratio >= 0.42 and size_ratio < 0.65:
                        if file_name_match and feature_sim >= 0.55:
                            confidence = 0.65 + subset_ratio * 0.20
            
            # 规则C: 中等相似度 + 辅助证据（V3优化版）
            if (not is_duplicate and has_enough_content and 
                  content_similarity >= 0.24 and  # 【优化】从0.28降到0.24
                  (file_name_match or feature_sim >= 0.58 or simhash_dist <= 4)):  # 【优化】放宽条件
                
                additional_evidence = 0
                
                if file_name_match:
                    additional_evidence += 0.13
                if feature_sim >= 0.58:  # 【优化】从0.65降到0.58
                    additional_evidence += 0.10
                if simhash_dist <= 4:  # 【优化】从3放宽到4
                    additional_evidence += 0.08
                
                combined_confidence = (
                    content_similarity * 0.55 + 
                    feature_sim * 0.18 + 
                    additional_evidence
                )
                
                if combined_confidence >= 0.52:  # 【优化】从0.56降到0.52
                    is_duplicate = True
                    duplicate_types.append(DuplicateType.CONTENT_SIMILAR)
                    confidence = min(0.82, combined_confidence + 0.12)
            
            # 规则D: 仅文件名相同（【收紧】高门槛防误报）
            # 只有当文件名完全相同 + 高特征相似度 + 较高内容相似度时才判定
            if (not is_duplicate and file_name_match and
                  feature_sim >= 0.88 and  # 【收紧】从0.80提高到0.88
                  has_enough_content and
                  content_similarity >= 0.30 and  # 【收紧】从0.18提高到0.30
                  size1 > self.MIN_FILE_SIZE_FOR_DETECTION and  # 【新增】两个文件都要足够大
                  size2 > self.MIN_FILE_SIZE_FOR_DETECTION):

                is_duplicate = True
                duplicate_types.append(DuplicateType.FILE_NAME)
                confidence = 0.58 + content_similarity * 0.4 + (feature_sim - 0.88) * 0.5
                confidence = min(0.76, confidence)
            
            # 最终决策
            if not is_duplicate or not duplicate_types:
                return None
            
            if confidence < self.HIGH_CONFIDENCE:
                if confidence >= 0.70:
                    logger.debug(f"低置信度候选: {book1.file_name} vs {book2.file_name}, conf={confidence:.2f}")
                return None
            
            return BookComparison(
                book1=book1,
                book2=book2,
                file_name_match=file_name_match,
                similarity=max(content_similarity, subset_ratio),
                hash_match=False,
                duplicate_types=duplicate_types,
                confidence=min(confidence, 0.99)
            )
            
        except Exception as e:
            logger.error(f"详细比较失败: {e}")
            return None
    
    def _check_subset_relation_enhanced(self, fp1, fp2):
        """
        V3增强的包含关系检测（针对1-N章场景）
        
        使用多尺度滑动窗口+关键段落匹配，比Ultra更灵敏但更准确
        """
        from src.utils.string_utils import StringUtils
        
        try:
            book1, book2 = fp1.book, fp2.book
            
            content1 = self._read_book_content(book1.path, 35000)
            content2 = self._read_book_content(book2.path, 35000)
            
            if not content1 or not content2:
                self._last_subset_result = (False, None)
                return self._last_subset_result
            
            clean1 = re.sub(r'\s+', '', content1)
            clean2 = re.sub(r'\s+', '', content2)
            len1, len2 = len(clean1), len(clean2)
            
            if len1 == 0 or len2 == 0 or len1 >= len2:
                self._last_subset_result = (False, None)
                return self._last_subset_result
            
            small_content, large_content = (clean1, clean2) if len1 <= len2 else (clean2, clean1)
            small_len, large_len = len(small_content), len(large_content)
            size_ratio = small_len / large_len
            
            # 快速检查：直接包含
            if small_content in large_content:
                self._last_subset_result = (True, 1.0)
                return self._last_subset_result
            
            # 多尺度滑动窗口
            window_ratio = self._multi_scale_sliding_window(small_content, large_content)
            
            # 关键段落匹配
            paragraph_ratio = self._key_paragraph_check(small_content, large_content)
            
            # 综合判定（V3优化版）
            final_ratio = (
                window_ratio * 0.50 +
                paragraph_ratio * 0.30 +
                (size_ratio * 0.20)  # 大小合理性加分
            )
            
            is_duplicate = final_ratio >= 0.42  # 【优化】从0.48降到0.42，大幅提升包含关系灵敏度
            
            if is_duplicate:
                # 构建ComparisonResult（提升置信度）
                score = 62 + final_ratio * 25  # 范围: 73-87
                confidence = min(0.90, 0.58 + final_ratio * 0.32)  # 【优化】提高置信度计算
                
                result = BookComparison(
                    book1=book1,
                    book2=book2,
                    file_name_match=(fp1.normalized_name == fp2.normalized_name),
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
        """Level 3: 检测文件名相同但在之前阶段未被捕获的书籍"""
        groups = []
        
        existing_paths = set()
        for group in existing_groups:
            for book in group.books:
                existing_paths.add(book.path)
        
        name_to_fps: Dict[str, List[BookFingerprint]] = {}
        for fp in fingerprints:
            name = fp.normalized_name
            if name not in name_to_fps:
                name_to_fps[name] = []
            name_to_fps[name].append(fp)
        
        for name, fps_list in name_to_fps.items():
            remaining = [fp for fp in fps_list if fp.book.path not in existing_paths]
            
            if len(remaining) > 1:
                # 【加强版】文件名兜底检测 - 需要更多验证
                verified = []
                for fp in remaining:
                    # 必须有内容采样或文件哈希
                    if fp.content_sample or fp.file_hash:
                        # 【新增】文件大小检查
                        size = fp.book.size if hasattr(fp.book, 'size') and fp.book.size else 0
                        if size >= self.MIN_FILE_SIZE_FOR_DETECTION:  # 只接受足够大的文件
                            verified.append(fp)

                # 【新增】进一步验证：检查是否有足够多的有效内容
                if len(verified) > 1:
                    # 检查是否至少有一对书籍有合理的内容相似度
                    has_content_evidence = False
                    for i in range(len(verified)):
                        for j in range(i + 1, len(verified)):
                            if (verified[i].content_sample and verified[j].content_sample and
                                len(verified[i].content_sample) > 100 and
                                len(verified[j].content_sample) > 100):
                                # 简单的字符串包含检查
                                s1, s2 = verified[i].content_sample[:500], verified[j].content_sample[:500]
                                if s1 in s2 or s2 in s1 or len(set(s1) & set(s2)) > 200:
                                    has_content_evidence = True
                                    break
                        if has_content_evidence:
                            break

                    # 只有在有内容证据或书籍数量>=3时才创建组（减少误报）
                    if has_content_evidence or len(verified) >= 3:
                        books = [fp.book for fp in verified]
                        group = DuplicateGroup(
                            duplicate_type=DuplicateType.FILE_NAME,
                            books=books,
                            similarity=0.0,
                            confidence=0.42 if has_content_evidence else 0.38  # 根据证据调整置信度
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
