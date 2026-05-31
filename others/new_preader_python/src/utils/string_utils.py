"""
字符串工具类，提供文本处理功能
"""

import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional, Tuple

from src.utils.logger import get_logger
from src.core.book import Book

logger = get_logger(__name__)

class StringUtils:
    """字符串工具类"""
    
    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = "...") -> str:
        """
        截断文本
        
        Args:
            text: 原始文本
            max_length: 最大长度
            suffix: 截断后的后缀
            
        Returns:
            str: 截断后的文本
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def normalize(text: str) -> str:
        """
        规范化文本（去除特殊字符、多余空格等）
        
        Args:
            text: 原始文本
            
        Returns:
            str: 规范化后的文本
        """
        # 将全角字符转换为半角字符
        text = unicodedata.normalize('NFKC', text)
        
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def count_words(text: str) -> int:
        """
        计算文本中的单词数
        
        Args:
            text: 文本
            
        Returns:
            int: 单词数
        """
        # 对于中文，按字符计数
        if re.search(r'[\u4e00-\u9fff]', text):
            # 移除标点符号和空格
            clean_text = re.sub(r'[^\u4e00-\u9fff]', '', text)
            return len(clean_text)
        else:
            # 对于英文，按单词计数
            words = re.findall(r'\b\w+\b', text)
            return len(words)
    
    @staticmethod
    def count_lines(text: str) -> int:
        """
        计算文本中的行数
        
        Args:
            text: 文本
            
        Returns:
            int: 行数
        """
        return text.count('\n') + 1
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 文本
            max_keywords: 最大关键词数量
            
        Returns:
            List[str]: 关键词列表
        """
        # 简单实现：移除停用词，按频率排序
        # 在实际应用中，可以使用更复杂的算法，如TF-IDF
        
        # 停用词列表（简化版）
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'to', 'of', 'for', 'in', 'that', 'by', 'on',
            'with', 'as', 'at', 'from', 'this', 'that', 'these', 'those',
            '的', '了', '和', '是', '在', '有', '我', '他', '她', '它',
            '们', '你', '我们', '他们', '她们', '它们', '你们'
        }
        
        # 分词
        if re.search(r'[\u4e00-\u9fff]', text):
            # 中文分词（简化处理）
            words = list(text)
        else:
            # 英文分词
            words = re.findall(r'\b\w+\b', text.lower())
        
        # 过滤停用词和短词
        filtered_words = [word for word in words if word.lower() not in stop_words and len(word) > 1]
        
        # 计算词频
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前N个关键词
        return [word for word, _ in sorted_words[:max_keywords]]
    
    @staticmethod
    def format_time(seconds: int) -> str:
        """
        格式化时间（秒）
        
        Args:
            seconds: 秒数
            
        Returns:
            str: 格式化后的时间
        """
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{int(hours)}小时{int(minutes)}分钟"
        elif minutes > 0:
            return f"{int(minutes)}分钟{int(seconds)}秒"
        else:
            return f"{int(seconds)}秒"
    
    @staticmethod
    def format_number(number: int) -> str:
        """
        格式化数字（添加千位分隔符）
        
        Args:
            number: 数字
            
        Returns:
            str: 格式化后的数字
        """
        return f"{number:,}"
    
    @staticmethod
    def similarity(text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（改进版，支持中文）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            float: 相似度（0-1）
        """
        if not text1 or not text2:
            return 0.0
        
        # 规范化文本
        text1 = StringUtils._normalize_for_comparison(text1)
        text2 = StringUtils._normalize_for_comparison(text2)
        
        # 使用SequenceMatcher计算序列相似度（对中文更友好）
        matcher = SequenceMatcher(None, text1, text2)
        ratio = matcher.ratio()
        
        return ratio
    
    @staticmethod
    def _normalize_for_comparison(text: str) -> str:
        """
        规范化文本用于比较（更激进的清理）
        
        Args:
            text: 原始文本
            
        Returns:
            str: 规范化后的文本
        """
        # 移除所有空白字符（包括空格、换行、制表符等）
        text = re.sub(r'\s+', '', text)
        
        # 移除标点符号（中文和英文）
        text = re.sub(r'[^\u4e00-\u9fff\w]', '', text)
        
        # 统一为小写
        text = text.lower()
        
        return text
    
    @staticmethod
    def book_content_similarity(content1: str, content2: str, sample_size: int = 10000) -> float:
        """
        计算两个书籍内容的相似度（适用于大文件，改进版）
        
        Args:
            content1: 书籍内容1
            content2: 书籍内容2
            sample_size: 采样大小（字符数），默认10000以提高准确性
            
        Returns:
            float: 相似度（0-1）
        """
        if not content1 or not content2:
            return 0.0
        
        # 规范化文本（去除空白字符）
        content1 = re.sub(r'\s+', '', content1)
        content2 = re.sub(r'\s+', '', content2)
        
        # 计算实际内容长度
        len1 = len(content1)
        len2 = len(content2)
        
        # 如果文件较小，直接比较全部内容
        if len1 <= sample_size and len2 <= sample_size:
            return StringUtils.similarity(content1, content2)
        
        # 对于大文件，采用多段采样方式比较
        samples1 = StringUtils._sample_content(content1, sample_size)
        samples2 = StringUtils._sample_content(content2, sample_size)
        
        # 计算各采样部分的相似度，并加权平均
        similarities = []
        weights = []
        
        for i, (s1, s2) in enumerate(zip(samples1, samples2)):
            sim = StringUtils.similarity(s1, s2)
            similarities.append(sim)
            
            # 开头和结尾部分权重更高（0.4），中间部分权重较低（0.2）
            if i == 0 or i == len(samples1) - 1:
                weights.append(0.4)
            else:
                weights.append(0.2)
        
        # 计算加权平均相似度
        if similarities:
            weighted_sum = sum(s * w for s, w in zip(similarities, weights))
            total_weight = sum(weights)
            return weighted_sum / total_weight
        
        return 0.0
    
    @staticmethod
    def _sample_content(content: str, sample_size: int, parts: int = 3) -> List[str]:
        """
        对内容进行采样
        
        Args:
            content: 原始内容
            sample_size: 采样总大小
            parts: 采样部分数
            
        Returns:
            List[str]: 采样内容列表
        """
        if len(content) <= sample_size:
            return [content]
        
        part_size = sample_size // parts
        samples = []
        
        # 采样开头
        samples.append(content[:part_size])
        
        # 采样中间
        middle_start = (len(content) - part_size) // 2
        samples.append(content[middle_start:middle_start + part_size])
        
        # 采样结尾
        samples.append(content[-part_size:])
        
        return samples
    
    @staticmethod
    def is_content_subset(content1: str, content2: str, min_match_ratio: float = 0.70) -> Tuple[bool, float]:
        """
        检测一个内容是否是另一个内容的子集（优化版 - 针对整本vs章节场景增强）
        
        【核心改进】：
        1. 降低默认匹配率要求：从0.8降到0.7
        2. 增加滑动窗口的覆盖范围：窗口更小、步长更短
        3. 新增基于章节/段落边界的智能检测
        4. 增加SimHash辅助验证（降低海明距离阈值）
        
        Args:
            content1: 内容1（较小的内容）
            content2: 内容2（较大的内容）
            min_match_ratio: 最小匹配比例，默认0.7
            
        Returns:
            Tuple[bool, float]: (是否为子集, 匹配比例)
        """
        if not content1 or not content2:
            return False, 0.0
        
        # 规范化文本
        content1_clean = re.sub(r'\s+', '', content1)
        content2_clean = re.sub(r'\s+', '', content2)
        
        len1 = len(content1_clean)
        len2 = len(content2_clean)
        
        if len1 == 0 or len2 == 0:
            return False, 0.0
        
        # 如果两者长度相同或更长，不可能是子集
        if len1 >= len2:
            return False, 0.0
        
        # ===== 策略1：快速检查 - 完整连续子串 =====
        if content1_clean in content2_clean:
            return True, 1.0
        
        # ===== 策略2：滑动窗口检测（【优化】增强版）=====
        # 【关键改进】：使用更小的窗口和更短的步长，提高对"部分重叠"场景的敏感性
        window_size = min(600, max(300, len1 // 5))  # 窗口大小：至少300字符，最多600，或len1/5
        step_size = max(80, window_size // 3)  # 步长：【缩短】从window_size//2改为window_size//3（重叠67%）
        
        found_windows = 0
        total_windows = (len1 - window_size) // step_size + 1
        
        for i in range(0, len1 - window_size + 1, step_size):
            window_content = content1_clean[i:i + window_size]
            
            if window_content in content2_clean:
                found_windows += 1
        
        # 【优化】降低匹配率要求：从min_match_ratio*0.9降到min_match_ratio*0.8
        if total_windows > 0 and found_windows / total_windows >= min_match_ratio * 0.80:
            return True, found_windows / total_windows
        
        # ===== 【新增】策略2.5：多尺度滑动窗口检测 =====
        # 使用不同大小的窗口进行二次检测（捕获不同粒度的重复模式）
        if found_windows / max(total_windows, 1) >= min_match_ratio * 0.60:  # 如果第一轮接近但未达标
            # 使用更大的窗口重新检测
            large_window_size = min(1000, len1 // 3)
            large_step_size = large_window_size // 3
            large_found = 0
            large_total = (len1 - large_window_size) // large_step_size + 1
            
            for i in range(0, len1 - large_window_size + 1, large_step_size):
                large_window = content1_clean[i:i + large_window_size]
                if large_window in content2_clean:
                    large_found += 1
            
            # 综合两轮结果
            combined_ratio = (found_windows + large_found) / max(total_windows + large_total, 1)
            if combined_ratio >= min_match_ratio * 0.65:  # 综合匹配率>=45.5%（当min_match_ratio=0.7时）
                return True, combined_ratio
        
        # ===== 策略3：基于指纹的模糊匹配（【优化】放宽条件）======
        simhash1 = StringUtils._compute_simhash_fast(content1_clean)
        simhash2 = StringUtils._compute_simhash_fast(content2_clean)
        
        hamming_dist = StringUtils._hamming_distance(simhash1, simhash2)
        
        # 【优化】从海明距离<=5且长度比<0.7 改为 <=6且<0.75
        if hamming_dist <= 6 and len1 < len2 * 0.75:
            # 进一步用SequenceMatcher验证
            matcher = SequenceMatcher(None, content1_clean[:min(4000, len1)], 
                                    content2_clean[:min(5000 + int(len1 * 1.5), len2)])
            ratio = matcher.quick_ratio()
            
            # 【优化】降低验证阈值
            if ratio >= min_match_ratio * 0.90:  # 从min_match_ratio改为min_match_ratio*0.9
                return True, ratio
        
        # ===== 策略4：关键段落匹配 =====
        # 提取content1的关键特征段落（开头、中间、结尾各取一段）
        key_segments = []
        segment_len = min(800, len1 // 6)  # 每段长度
        
        # 开头段
        if len1 >= segment_len:
            key_segments.append((content1_clean[:segment_len], "head"))
        
        # 中间段（可能有多处）
        mid_positions = [len1 // 3, len1 // 2, 2 * len1 // 3]
        for pos in mid_positions:
            if pos + segment_len <= len1:
                key_segments.append((content1_clean[pos:pos + segment_len], f"mid_{pos}"))
        
        # 结尾段
        if len1 >= segment_len:
            key_segments.append((content1_clean[-segment_len:], "tail"))
        
        matched_segments = 0
        total_segments = len(key_segments)
        
        for seg_content, seg_name in key_segments:
            if len(seg_content) >= 200:  # 至少200字符才有效
                if seg_content in content2_clean:
                    matched_segments += 1
                else:
                    # 尝试模糊匹配：允许少量差异
                    matcher = SequenceMatcher(None, seg_content, content2_clean)
                    match_blocks = matcher.get_matching_blocks()
                    
                    # 找到最长的连续匹配块
                    best_match_len = max(block.size for block in match_blocks)
                    
                    if best_match_len >= len(seg_content) * 0.85:  # 85%匹配
                        matched_segments += 1
        
        # 如果超过80%的关键段落都匹配成功
        if total_segments > 0 and matched_segments / total_segments >= 0.75:
            return True, matched_segments / total_segments
        
        # ===== 最终回退：SequenceMatcher全局匹配 =====
        matcher = SequenceMatcher(None, content1_clean, content2_clean)
        matches = matcher.get_opcodes()
        
        matched_length = 0
        for op in matches:
            if op[0] == 'equal':
                matched_length += op[2] - op[1]
        
        match_ratio = matched_length / len1 if len1 > 0 else 0.0
        
        if match_ratio >= min_match_ratio:
            return True, match_ratio
        
        return False, match_ratio
    
    @staticmethod
    def _compute_simhash_fast(text: str, bits: int = 64) -> int:
        """快速计算文本的SimHash指纹"""
        if not text or len(text) == 0:
            return 0
        
        import hashlib
        
        # 分词（简单按字符分组）
        chunk_size = max(10, len(text) // bits)
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        v = [0] * bits
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
                
            # 用MD5哈希每个chunk
            chunk_hash = hashlib.md5(chunk.encode('utf-8')).hexdigest()
            bin_hash = bin(int(chunk_hash[:16], 16))[2:].zfill(bits)
            
            weight = 1.0  # 统一权重
            
            for j in range(bits):
                if j < len(bin_hash) and bin_hash[j] == '1':
                    v[j] += weight
                else:
                    v[j] -= weight
        
        fingerprint = 0
        for j in range(bits):
            if v[j] > 0:
                fingerprint |= (1 << (bits - 1 - j))
        
        return fingerprint
    
    @staticmethod
    def _hamming_distance(hash1: int, hash2: int) -> int:
        """计算两个整数之间的海明距离"""
        xor = hash1 ^ hash2
        distance = 0
        while xor:
            distance += xor & 1
            xor >>= 1
        return distance
    
    @staticmethod
    def check_subset_relationship(book1: Book, book2: Book) -> Tuple[Optional[str], float]:
        """
        检查两本书之间的包含关系
        
        Args:
            book1: 书籍1
            book2: 书籍2
            
        Returns:
            Tuple[Optional[str], float]: (包含关系类型, 相似度)
                - "subset": book1 是 book2 的子集
                - "superset": book1 是 book2 的超集
                - "none": 无包含关系
        """
        try:
            # 获取内容采样（改进版：增加采样大小和采样位置）
            # 对于整本和部分章节的情况，需要更全面的采样
            content1 = StringUtils._read_book_sample_enhanced(book1.path, sample_size=20000)
            content2 = StringUtils._read_book_sample_enhanced(book2.path, sample_size=20000)
            
            if not content1 or not content2:
                return "none", 0.0
            
            # 检查 book1 是否是 book2 的子集（降低阈值到60%）
            is_subset, ratio1 = StringUtils.is_content_subset(content1, content2, min_match_ratio=0.6)
            if is_subset:
                return "subset", ratio1
            
            # 检查 book2 是否是 book1 的子集（降低阈值到60%）
            is_subset, ratio2 = StringUtils.is_content_subset(content2, content1, min_match_ratio=0.6)
            if is_subset:
                return "superset", ratio2
            
            # 如果未检测到明确子集关系，检查部分匹配
            # 对于整本和章节的情况，可能只是部分匹配
            part_match, part_ratio = StringUtils._check_partial_subset(content1, content2, min_ratio=0.5)
            if part_match == "subset":
                return "subset", part_ratio
            elif part_match == "superset":
                return "superset", part_ratio
            
            return "none", 0.0
        except Exception as e:
            logger.error(f"检查包含关系时出错: {e}")
            return "none", 0.0
    
    @staticmethod
    def _read_book_sample(book_path: str, sample_size: int = 10000) -> Optional[str]:
        """
        读取书籍内容采样
        
        Args:
            book_path: 书籍路径
            sample_size: 采样大小
            
        Returns:
            Optional[str]: 内容采样
        """
        return StringUtils._read_book_sample_enhanced(book_path, sample_size)
    
    @staticmethod
    def _read_book_sample_enhanced(book_path: str, sample_size: int = 30000, parts: int = 10) -> Optional[str]:
        """
        增强的书籍内容采样（用于子集检测 - 支持任意位置嵌入）
        
        改进策略：
        1. 增加采样位置数量（从5个到10个）
        2. 添加基于文件大小的自适应采样密度
        3. 添加少量随机采样（覆盖非均匀分布的内容）
        4. 增大总采样量（从20000到30000）
        
        Args:
            book_path: 书籍路径
            sample_size: 总采样大小
            parts: 采样部分数
            
        Returns:
            Optional[str]: 合并的采样内容
        """
        try:
            if not os.path.exists(book_path):
                return None
            
            # 检查文件扩展名
            _, ext = os.path.splitext(book_path.lower())
            binary_extensions = {'.epub', '.mobi', '.azw', '.azw3', '.pdf', '.djvu', '.cbr', '.cbz', '.fb2'}
            
            if ext in binary_extensions:
                return None
            
            # 获取文件大小
            file_size = os.path.getsize(book_path)
            
            # 根据文件大小自适应调整采样策略
            actual_sample_size = sample_size
            actual_parts = parts
            
            if file_size > 5000000:  # >5MB
                actual_sample_size = min(45000, sample_size)
                actual_parts = 12
            elif file_size > 1000000:  # >1MB
                actual_sample_size = min(38000, sample_size)
                actual_parts = 10
            else:  # <1MB
                actual_sample_size = min(35000, sample_size)
                actual_parts = 8
            
            if file_size <= actual_sample_size:
                # 文件较小，直接读取全部
                with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(actual_sample_size)
            
            part_size = actual_sample_size // actual_parts
            sampled_content = []
            
            with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 1. 开头部分（最重要）
                sampled_content.append(f.read(part_size))
                
                # 2. 均匀分布的中间部分（高密度）
                for i in range(1, actual_parts - 2):
                    seek_position = int(file_size * i / (actual_parts - 1))
                    f.seek(seek_position)
                    sampled_content.append(f.read(part_size))
                
                # 3. 结尾部分
                f.seek(max(0, file_size - part_size))
                sampled_content.append(f.read(part_size))
                
                # 4. 【新增】随机位置额外采样（捕获非均匀分布的子集）
                import random
                random.seed(hash(book_path))  # 固定种子确保可复现
                
                num_random_samples = min(5, max(2, int(file_size / 1500000)))
                
                for _ in range(num_random_samples):
                    rand_pos = random.randint(part_size * 2, max(part_size * 2 + 1, file_size - part_size * 3))
                    f.seek(rand_pos)
                    rand_sample = f.read(part_size // 2)
                    
                    if len(rand_sample.strip()) >= 80:
                        sampled_content.append(rand_sample)
            
            return ''.join(sampled_content)
        except Exception as e:
            logger.error(f"读取书籍内容时出错: {e}")
            # 回退到简单采样
            try:
                with open(book_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(sample_size)
            except Exception:
                return None
    
    @staticmethod
    def _check_partial_subset(content1: str, content2: str, min_ratio: float = 0.5) -> Tuple[Optional[str], float]:
        """
        检测部分包含关系（增强版 - 支持任意位置嵌入的子集检测）
        
        专门用于检测：
        - 整本书 vs 某几章（子集在任意位置）
        - A书包含B书的全部内容（但B书内容分散/嵌套在A书中间）
        
        Args:
            content1: 内容1
            content2: 内容2
            min_ratio: 最小匹配比例
            
        Returns:
            Tuple[Optional[str], float]: (关系类型, 匹配比例)
                - "subset": content1 是 content2 的子集
                - "superset": content1 是 content2 的超集
                - "none": 无关系
        """
        if not content1 or not content2:
            return "none", 0.0
        
        # 规范化文本
        content1 = re.sub(r'\s+', '', content1)
        content2 = re.sub(r'\s+', '', content2)
        
        len1 = len(content1)
        len2 = len(content2)
        
        if len1 == 0 or len2 == 0:
            return "none", 0.0
        
        # ===== 快速检查1：直接包含 =====
        if content1 in content2:
            return "subset", 1.0
        
        if content2 in content1:
            return "superset", 1.0
        
        # ===== 新增：滑动窗口深度检测 =====
        def check_sliding_window_subset(small_content: str, large_content: str) -> float:
            """使用滑动窗口检测small是否是large的子集"""
            small_len = len(small_content)
            large_len = len(large_content)
            
            if small_len >= large_len:
                return 0.0
            
            if small_len < 500:  # 太短，直接用in检查
                return 1.0 if small_content in large_content else 0.0
            
            # 窗口大小和步长
            window_size = min(400, small_len // 3)
            step_size = max(80, window_size // 2)
            
            found_count = 0
            total_windows = (small_len - window_size) // step_size + 1
            
            for i in range(0, small_len - window_size + 1, step_size):
                window = small_content[i:i + window_size]
                
                if window in large_content:
                    found_count += 1
            
            return found_count / total_windows if total_windows > 0 else 0.0
        
        # 检测两个方向（【优化】降低匹配率要求以提高召回）
        subset_ratio_12 = check_sliding_window_subset(content1, content2)
        subset_ratio_21 = check_sliding_window_subset(content2, content1)
        
        # 【优化】判断方向 - 从72%降到65%（更宽松）
        if len1 < len2 and subset_ratio_12 >= 0.65:  # content1较短且大部分窗口匹配
            return "subset", subset_ratio_12
        
        if len2 < len1 and subset_ratio_21 >= 0.65:  # content2较短且大部分窗口匹配
            return "superset", subset_ratio_21
        
        # ===== 新增：关键段落匹配检测 =====
        def extract_key_paragraphs(text: str, num_paragraphs: int = 6) -> List[str]:
            """提取文本中的关键段落"""
            paragraphs = []
            text_len = len(text)
            
            if text_len <= 1000:
                return [text]
            
            para_len = min(600, text_len // (num_paragraphs + 1))
            
            # 开头、结尾必须包含
            paragraphs.append(text[:para_len])
            paragraphs.append(text[-para_len:])
            
            # 均匀分布的中间段落
            positions = [
                text_len * i // (num_paragraphs + 1) 
                for i in range(1, num_paragraphs + 1)
            ]
            
            for pos in positions:
                start = max(0, int(pos))
                end = min(text_len, start + para_len)
                if end > start + 100:  # 至少100字符有效
                    paragraphs.append(text[start:end])
            
            return paragraphs
        
        key_paras_1 = extract_key_paragraphs(content1, num_paragraphs=5)
        key_paras_2 = extract_key_paragraphs(content2, num_paragraphs=5)
        
        # 统计关键段落匹配数
        matched_1_in_2 = sum(1 for p in key_paras_1 if len(p) >= 200 and p in content2)
        matched_2_in_1 = sum(1 for p in key_paras_2 if len(p) >= 200 and p in content1)
        
        match_rate_1_in_2 = matched_1_in_2 / len(key_paras_1) if key_paras_1 else 0
        match_rate_2_in_1 = matched_2_in_1 / len(key_paras_2) if key_paras_2 else 0
        
        # 【优化】判断 - 放宽长度差异要求和匹配率要求
        if len1 < len2 * 0.7 and match_rate_1_in_2 >= 0.60:  # 从0.6放宽到0.7，匹配率从70%降到60%
            return "subset", match_rate_1_in_2
        
        if len2 < len1 * 0.7 and match_rate_2_in_1 >= 0.60:  # 同上优化
            return "superset", match_rate_2_in_1
        
        # ===== 回退：SequenceMatcher相似度判断（【优化】增强版）=====
        # 增加采样量以提高准确性
        sample_len_1 = min(6000, len1)  # 从4000增加到6000
        sample_len_2 = min(6000 + int(len1 * 1.5), len2)  # 动态调整，考虑可能的超集内容
        matcher = SequenceMatcher(None, content1[:sample_len_1], content2[:sample_len_2])
        similarity = matcher.quick_ratio()
        
        # 根据相似度和长度比综合判断（【优化】放宽条件）
        len_ratio = min(len1, len2) / max(len1, len2)
        
        # 长度差异大(>25%)且相似度高(>50%)→ 可能是包含关系（从30%/60%放宽）
        if len_ratio < 0.75 and similarity >= max(min_ratio, 0.50):
            if len1 < len2:
                return "subset", similarity
            else:
                return "superset", similarity
        
        return "none", similarity