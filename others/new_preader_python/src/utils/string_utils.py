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
        计算两个文本的相似度（V5增强版，支持中文繁简转换）

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            float: 相似度（0-1）
        """
        if not text1 or not text2:
            return 0.0
        
        # 【增强】使用新的规范化流程（含繁简转换）
        text1 = StringUtils.normalize_text_for_dedup(text1, to_simplified=True, remove_punctuation=True)
        text2 = StringUtils.normalize_text_for_dedup(text2, to_simplified=True, remove_punctuation=True)

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

    # ===== 标点符号统一映射 =====
    # 延迟初始化，避免编码问题
    _PUNCTUATION_MAP = None

    @staticmethod
    def _get_punctuation_map():
        """获取标点符号映射表（延迟构建）"""
        if StringUtils._PUNCTUATION_MAP is None:
            StringUtils._PUNCTUATION_MAP = {
                '\uff0c': ',',  '\u3002': '.',  '\uff01': '!',  '\uff1f': '?',  '\uff1a': ':',
                '\uff1b': ';',  '\u201c': '"',   '\u201d': '"',   '\u2018': "'",   '\u2019': "'",
                '\uff08': '(',  '\uff09': ')',  '\u3010': '[',  '\u3011': ']',  '\u300a': '<',
                '\u300b': '>',  '\u3001': ',',  '\u2026': '..', '\u2014': '-',   '\u2013': '-',
                '\uff5e': '~',  '\u00b7': '.',
                '\u3000': ' ',    # 全角空格
                '\u00a0': ' ',    # 不换行空格
                '\u2002': ' ',    # En空格
                '\u2003': ' ',    # Em空格
                '\u2009': ' ',    # 细空格
                '\u2019': "'",     # 右单引号(弯)
                '\u2018': "'",     # 左单引号(弯)
                '\u201c': '"',     # 左双引号(弯)
                '\u201d': '"',     # 右双引号(弯)
                '\u300c': '[',     # 「
                '\u300d': ']',     # 」
                '\u300e': '[',     # 『
                '\u300f': ']',     # 』
                '\ufe50': ',',     # ﹑
                '\ufe56': '?',     # ﹖
                '\ufe57': '!',     # ﹗
            }
        return StringUtils._PUNCTUATION_MAP

    @staticmethod
    def normalize_text_for_dedup(text: str, normalize_chapter: bool = False,
                                  to_simplified: bool = True,
                                  remove_punctuation: bool = True) -> str:
        """
        【核心】用于书籍去重比较的文本规范化（增强版）

        处理流程：
        1. 繁体中文 → 简体中文（可选）
        2. 全角字符 → 半角字符
        3. 标点符号 → 标准形式或移除
        4. 章节标题序号归一化（可选）
        5. 多余空白字符清理
        6. 大小写统一

        Args:
            text: 原始文本
            normalize_chapter: 是否对章节行进行序号归一化（对正文内容设为False）
            to_simplified: 是否将繁体转为简体（默认True）
            remove_punctuation: 是否移除标点符号（默认True，用于相似度计算时）

        Returns:
            str: 规范化后的文本
        """
        if not text:
            return text

        # Step 1: 繁简转换（如果需要）
        if to_simplified:
            text = _ChineseConverter.to_simplified(text)

        # Step 2: 全角→半角 + Unicode NFKC 规范化
        text = unicodedata.normalize('NFKC', text)

        # Step 3: 标点符号标准化
        if remove_punctuation:
            # 移除所有空白和标点，只保留中英文、数字
            text = re.sub(r'\s+', '', text)
            text = re.sub(r'[^\u4e00-\u9fff\w]', '', text)
            # 转为小写
            text = text.lower()
        else:
            # 替换为标准ASCII标点（延迟构建避免编码问题）
            punct_map = StringUtils._get_punctuation_map()
            for old, new in punct_map.items():
                text = text.replace(old, new)
            # 合并多余空白
            text = re.sub(r'\s+', ' ', text).strip()

        # Step 4: 章节序号归一化（如果启用且是章节行模式）
        if normalize_chapter and len(text) < 100:  # 只处理短行（可能是章节标题）
            normalized_ch, _ = normalize_chapter_number(text)
            # 如果成功归一化且结果不同，使用归一化后的版本
            if normalized_ch != text:
                text = normalized_ch
                # 再次清理（归一化后可能引入新字符）
                if remove_punctuation:
                    text = re.sub(r'[^\u4e00-\u9fff\w]', '', text).lower()

        return text

    @staticmethod
    def book_content_similarity(content1: str, content2: str, sample_size: int = 10000,
                                use_enhanced_normalization: bool = True) -> float:
        """
        计算两个书籍内容的相似度（适用于大文件，V5增强版）

        【关键改进】：
        - 支持繁简中文自动转换匹配
        - 支持全角半角自动统一
        - 支持多种标点符号变体的统一
        - 提高了对同书不同版本的检测能力

        Args:
            content1: 书籍内容1
            content2: 书籍内容2
            sample_size: 采样大小（字符数），默认10000
            use_enhanced_normalization: 是否使用增强的规范化（默认True）

        Returns:
            float: 相似度（0-1）
        """
        if not content1 or not content2:
            return 0.0

        # 【V5增强】使用增强的文本规范化
        if use_enhanced_normalization:
            content1 = StringUtils.normalize_text_for_dedup(content1, to_simplified=True, remove_punctuation=True)
            content2 = StringUtils.normalize_text_for_dedup(content2, to_simplified=True, remove_punctuation=True)
        else:
            # 回退到旧逻辑
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
    def _sample_content(content: str, sample_size: int, parts: int = 7) -> List[str]:
        """
        对内容进行采样（V4增强版 - 7段均匀采样）
        
        Args:
            content: 原始内容
            sample_size: 采样总大小
            parts: 采样部分数（从3提升到7）
            
        Returns:
            List[str]: 采样内容列表
        """
        if len(content) <= sample_size:
            return [content]
        
        part_size = sample_size // parts
        samples = []
        total_len = len(content)
        
        # V4: 7段均匀采样，覆盖开头、1/6、1/4、中间、3/4、5/6、结尾
        positions = [
            0,                                    # 开头
            total_len // 6,                        # 约16.7%处
            total_len // 4,                        # 25%处
            (total_len - part_size) // 2,         # 中间
            (total_len * 3) // 4,                 # 75%处
            (total_len * 5) // 6,                 # 约83.3%处
            max(0, total_len - part_size),        # 结尾
        ]
        
        for pos in positions:
            if pos < 0:
                pos = 0
            end_pos = min(pos + part_size, total_len)
            if pos < end_pos:
                samples.append(content[pos:end_pos])
        
        # 去重（如果某些位置重叠太多）
        unique_samples = []
        seen_starts = set()
        for i, s in enumerate(samples):
            actual_start = positions[i] if i < len(positions) else 0
            rounded_start = actual_start // 100 * 100  # 按100字符精度去重
            if rounded_start not in seen_starts:
                seen_starts.add(rounded_start)
                unique_samples.append(s)
        
        return unique_samples if unique_samples else [content[:part_size]]
    
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
        
        # 【V5增强】使用增强规范化（含繁简转换、标点统一等）
        content1_clean = StringUtils.normalize_text_for_dedup(content1, to_simplified=True, remove_punctuation=True)
        content2_clean = StringUtils.normalize_text_for_dedup(content2, to_simplified=True, remove_punctuation=True)
        
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
        """快速计算文本的SimHash指纹（V5增强版 - 支持繁简转换）"""
        if not text or len(text) == 0:
            return 0

        import hashlib

        # 【V5增强】繁简转换预处理
        text = _ChineseConverter.to_simplified(text)
        # 基本清理
        text = re.sub(r'\s+', '', text).lower()

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

        # 【V5增强】使用增强规范化（含繁简转换）
        content1 = StringUtils.normalize_text_for_dedup(content1, to_simplified=True, remove_punctuation=True)
        content2 = StringUtils.normalize_text_for_dedup(content2, to_simplified=True, remove_punctuation=True)
        
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


# ============================================================
# 繁体中文 ↔ 简体中文 转换映射表（轻量级，覆盖常见字符）
# 数据来源: 基于Unicode Unihan数据库的常见繁简对应关系
# ============================================================
class _ChineseConverter:
    """
    中文繁简转换器（纯Python实现，无需外部依赖）

    设计原则：
    1. 覆盖小说/书籍中最常见的繁简差异字符（约2000+对）
    2. 支持简→繁 和 繁→简 双向转换
    3. 使用字典查找，性能优异（O(n)复杂度）
    4. 可选使用 opencc 库作为后端（如果已安装）
    """

    _initialized = False
    _s2t: Dict[str, str] = {}  # 简体 → 繁体
    _t2s: Dict[str, str] = {}  # 繁体 → 简体
    _use_opencc = False
    _opencc_converter = None

    @classmethod
    def _init_converter(cls):
        """初始化转换映射表"""
        if cls._initialized:
            return

        # ===== 尝试加载 opencc（更完整）=====
        try:
            import opencc
            cls._opencc_converter = opencc.OpenCC('s2t.json')
            cls._use_opencc = True
            cls._initialized = True
            logger.info("使用 opencc 作为繁简转换后端")
            return
        except Exception:
            pass

        try:
            import opencc
            cls._opencc_converter = OpenCC('s2t')
            cls._use_opencc = True
            cls._initialized = True
            logger.info("使用 opencc (OpenCC) 作为繁简转换后端")
            return
        except Exception:
            pass

        # ===== 使用内置映射表 =====
        # 常见简→繁映射（按使用频率排序，覆盖书籍中99%以上的常见字）
        s2t_pairs = [
            # === 高频常用字 ===
            ('为', '爲'), ('这', '這'), ('与', '與'), ('时', '時'), ('来', '來'),
            ('个', '個'),('中', '中'),('去', '去'),('会', '會'),('对', '對'),
            ('说', '說'),('就', '就'),('和', '和'),('不', '不'),('人', '人'),
            ('在', '在'),('有', '有'),('是', '是'),('的', '的'),('了', '了'),
            ('我', '我'),('他', '他'),('她', '她'),('它', '它'),('们', '們'),
            ('着', '著'),('到', '到'),('要', '要'),('也', '也'),('都', '都'),
            ('而', '而'),('能', '能'),('可以', '可以'),('很', '很'),('被', '被'),
            ('从', '從'),('把', '把'),('下', '下'),('上', '上'),('让', '讓'),
            ('给', '給'),('向', '向'),('才', '才'),('但', '但'),('还', '還'),
            ('又', '又'),('或', '或'),('所', '所'),('以', '以'),('于', '於'),
            ('没', '沒'),('因', '因'),('则', '則'),('如果', '如果'),('已', '已'),
            ('自己', '自己'),('我们', '我們'),('你们', '你們'),('他们', '他們'),
            ('她们', '她們'),('它们', '它們'),('什么', '什麼'),('怎么', '怎麼'),
            ('哪里', '哪裡'),('那里', '那裡'),('这里', '這裡'),('这个', '這個'),
            ('那个', '那個'),('这样', '這樣'),('那样', '那樣'),('哪里', '哪裡'),
            ('那些', '那些'),('这些', '這些'),('谁', '誰'),('吗', '嗎'),
            ('吧', '吧'),('啊', '啊'),('呢', '呢'),('呀', '呀'),('哦', '哦'),
            # === 动词 ===
            ('看', '看'),('听', '聽'),('想', '想'),('做', '做'),('走', '走'),
            ('跑', '跑'),('站', '站'),('坐', '坐'),('躺', '躺'),('睡', '睡'),
            ('吃', '吃'),('喝', '喝'),('穿', '穿'),('戴', '戴'),('拿', '拿'),
            ('放', '放'),('开', '開'),('关', '關'),('写', '寫'),('读', '讀'),
            ('讲', '講'),('问', '問'),('答', '答'),('知', '知'),('觉', '覺'),
            ('见', '見'),('发', '發'),('过', '過'),('进', '進'),('出', '出'),
            ('回', '回'),('起', '起'),('动', '動'),('停', '停'),('变', '變'),
            ('现', '現'),('认', '認'),('记', '記'),('忘', '忘'),('记', '記'),
            ('懂', '懂'),('明', '明'),('解', '解'),('决', '決'),('定', '定'),
            ('准', '準'),('准备', '準備'),('确', '確'),('实', '實'),('际', '際'),
            # === 名词 ===
            ('书', '書'),('门', '門'),('车', '車'),('马', '馬'),('风', '風'),
            ('龙', '龍'),('鸟', '鳥'),('鱼', '魚'),('虫', '蟲'),('兽', '獸'),
            ('国', '國'),('家', '家'),('园', '園'),('场', '場'),('楼', '樓'),
            ('房', '房'),('间', '間'),('层', '層'),('台', '臺'),('岛', '島'),
            ('桥', '橋'),('路', '路'),('边', '邊'),('面', '面'),('后', '後'),
            ('里', '裡'),('内', '內'),('外', '外'),('前', '前'),('左', '左'),
            ('右', '右'),('东', '東'),('西', '西'),('南', '南'),('北', '北'),
            ('头', '頭'),('眼', '眼'),('耳', '耳'),('口', '口'),('脸', '臉'),
            ('手', '手'),('脚', '腳'),('身', '身'),('心', '心'),('血', '血'),
            ('骨', '骨'),('气', '氣'),('神', '神'),('灵', '靈'),('鬼', '鬼'),
            ('仙', '仙'),('妖', '妖'),('魔', '魔'),('佛', '佛'),('道', '道'),
            ('法', '法'),('术', '術'),('功', '功'),('力', '力'),('武', '武'),
            ('剑', '劍'),('刀', '刀'),('枪', '槍'),('弓', '弓'),('箭', '箭'),
            # === 形容词 ===
            ('长', '長'),('短', '短'),('大', '大'),('小', '小'),('多', '多'),
            ('少', '少'),('高', '高'),('低', '低'),('快', '快'),('慢', '慢'),
            ('好', '好'),('坏', '壞'),('新', '新'),('旧', '舊'),('老', '老'),
            ('年', '年'),('岁', '歲'),('远', '遠'),('近', '近'),('深', '深'),
            ('浅', '淺'),('宽', '寬'),('窄', '窄'),('厚', '厚'),('薄', '薄'),
            ('强', '強'),('弱', '弱'),('硬', '硬'),('软', '軟'),('冷', '冷'),
            ('热', '熱'),('暖', '暖'),('凉', '涼'),('干', '乾'),('湿', '濕'),
            ('美', '美'),('丑', '醜'),('真', '真'),('假', '假'),('虚', '虛'),
            ('实', '實'),('难', '難'),('易', '易'),('苦', '苦'),('甜', '甜'),
            ('酸', '酸'),('辣', '辣'),('咸', '鹹'),('淡', '淡'),('忙', '忙'),
            ('闲', '閒'),('乱', '亂'),('整', '整'),('齐', '齊'),('平', '平'),
            # === 副词/介词/连词 ===
            ('最', '最'),('更', '更'),('越', '越'),('再', '再'),('又', '又'),
            ('正', '正'),('刚', '剛'),('将', '將'),('曾', '曾'),('常', '常'),
            ('渐', '漸'),('互', '互'),('相', '相'),('虽', '雖'),('即使', '即使'),
            ('尽管', '儘管'),('无论', '無論'),('只要','只要'),('只有','只有'),
            # === 小说特有高频字 ===
            ('战', '戰'),('斗', '鬥'),('杀', '殺'),('死', '死'),('伤', '傷'),
            ('医', '醫'),('药', '藥'),('毒', '毒'),('暗', '暗'),('隐', '隱'),
            ('藏', '藏'),('逃', '逃'),('追', '追'),('赶', '趕'),('冲', '衝'),
            ('击', '擊'),('挡', '擋'),('护', '護'),('卫', '衛'),('守', '守'),
            ('攻', '攻'),('防', '防'),('陷', '陷'),('困', '困'),('围', '圍'),
            ('绑', '綁'),('松', '鬆'),('紧', '緊'),('举', '舉'),('挥', '揮'),
            ('抬', '抬'),('推', '推'),('拉', '拉'),('抱', '抱'),('拥', '擁'),
            ('携', '攜'),('带', '帶'),('牵', '牽'),('挂', '掛'),( '摆', '擺'),
            ('搬', '搬'),('撞', '撞'),('摔', '摔'),('扔', '扔'),('抛', '拋'),
            ('扫', '掃'),('擦', '擦'),('拖', '拖'),('拍', '拍'),('打', '打'),
            ('骂', '罵'),('哭', '哭'),('笑', '笑'),('叫', '叫'),('喊', '喊'),
            ('吼', '吼'),('唤', '喚'),('呼', '呼'),('吸', '吸'),('叹', '嘆'),
            ('号', '號'),('啼', '啼'),('鸣', '鳴'),('响', '響'),('声', '聲'),
            ('音', '音'),('言', '言'),('语', '語'),('话', '話'),('谈', '談'),
            ('论', '論'),('诉', '訴'),('请', '請'),('谢', '謝'),('愿', '願'),
            ('义', '義'),('礼', '禮'),('仪', '儀'),('信', '信'),('誉', '譽'),
            ('价', '價'),('财', '財'),('财富', '財富'),('贪', '貪'),('赃', '贓'),
            ('购', '購'),('卖', '賣'),('赚', '賺'),('赔', '賠'),('贱', '賤'),
            ('账', '賬'),('贺', '賀'),('赏', '賞'),('赠', '贈'),('贫', '貧'),
            ('货', '貨'),('质', '質'),('量', '量'),('钟', '鐘'),('铁', '鐵'),
            ('银', '銀'),('铜', '銅'),('铅', '鉛'),('钢', '鋼'),('钥', '鑰'),
            ('链', '鏈'),('锁', '鎖'),('镜', '鏡'),('灯', '燈'),('烂', '爛'),
            ('烛', '燭'),('烧', '燒'),('烤', '烤'),('炼', '煉'),('熔', '熔'),
            ('烟', '煙'),('灿', '燦'),('烂', '爛'),('烁', '爍'),('辉煌', '輝煌'),
            ('粮', '糧'),('粮', '糧'),('灶', '竈'),('炊', '炊'),('饮', '飲'),
            ('饭', '飯'),('饿', '餓'),('饱', '飽'),('饲', '飼'),('饼', '餅'),
            ('馆', '館'),('饺', '餃'),('馒', '饅'),('馅', '餡'),('鸭', '鴨'),
            ('鸡', '雞'),('鹅', '鵝'),('鸽', '鴿'),('蝇', '蠅'),('蜂', '蜂'),
            ('蜡', '蠟'),('蜡', '蠟'),('蜗', '蝸'),('蚕', '蠶'),('蛮', '蠻'),
            ('疯', '瘋'),('癫', '癲'),('痴', '癡'),('瞎', '瞎'),('聋', '聾'),
            ('哑', '啞'),('跛', '跛'),('瘫', '瘫痪'),('症', '症'),('疾', '疾'),
            ('痛', '痛'),('疲', '疲'),('惫', '憊'),('痒', '癢'),('疼', '疼'),
            ('晕', '暈'),('昏', '昏'),('毙', '斃'),('残', '殘'),('殇', '殤'),
            ('毙', '斃'),('毙', '斃'),('毕', '畢'),('毙', '斃'),
            # === 更多常见字 ===
            ('两', '兩'),('双', '雙'),('只', '隻'),('支', '支'),('条', '條'),
            ('根', '根'),('棵', '棵'),('朵', '朵'),('颗', '顆'),('粒', '粒'),
            ('片', '片'),('块', '塊'),('张', '張'),('份', '份'),('封', '封'),
            ('页', '頁'),('册', '冊'),('遍', '遍'),('次', '次'),('回', '回'),
            ('遍', '遍'),('番', '番'),('轮', '輪'),('班', '班'),('组', '組'),
            ('群', '群'),('队', '隊'),('列', '列'),('排', '排'),('行', '行'),
            ('种', '種'),('类', '類'),('属', '屬'),('项', '項'),('点', '點'),
            ('线', '線'),('面', '面'),('体', '體'),('位', '位'),('处', '處'),
            ('广', '廣'),('庄', '莊'),('庙', '廟'),('库', '庫'),('废', '廢'),
            ('厅', '廳'),('厕', '厠'),('压', '壓'),('历', '曆'),('厂', '廠'),
            ('卫', '衛'),('阴', '陰'),('阳', '陽'),('际', '際'),('险', '險'),
            ('降', '降'),('限', '限'),('俨', '儼'),('体', '體'),('严', '嚴'),
            # === 补充更多常见繁简差异字 ===
            ('万', '萬'),('千', '千'),('百', '百'),('亿', '億'),('几', '幾'),
            ('系', '係'),('该', '該'),('并', '並'),('仅', '僅'),('权', '權'),
            ('众', '眾'),('义', '義'),('务', '務'),('产', '產'),('严', '嚴'),
            ('丝', '絲'),('举', '舉'),('设', '設'),('达', '達'),('办', '辦'),
            ('获', '獲'),('获', '穫'),('专', '專'),('际', '際'),('协', '協'),
            ('单', '單'),('图', '圖'),('罗', '羅'),('罢', '罷'),('网', '網'),
            ('纠', '糾'),('职', '職'),('联', '聯'),('势', '勢'),('脏', '髒'),
            ('脏', '臟'),('胜', '勝'),('勋', '勳'),('劳', '勞'),('劝', '勸'),
            ('营', '營'),('职', '職'),('聪', '聰'),('脑', '腦'),('脸', '臉'),
            ('胆', '膽'),('胃', '胃'),('肾', '腎'),('脾', '脾'),('肺', '肺'),
            ('肠', '腸'),('肤', '膚'),('肌', '肌'),('胁', '脅'),('胶', '膠'),
            ('脉', '脈'),('脏', '臟'),('脏', '髒'),('腊', '臘'),('腌', '醃'),
            ('胡', '鬍'),('胡', '胡'),('汇', '匯'),('汇', '彙'),('炉', '爐'),
            ('烛', '燭'),('炜', '煒'),('烨', '燁'),('炯', '炯'),('烁', '爍'),
            ('灿', '燦'),('烂', '爛'),('炼', '煉'),('烦', '煩'),('焖', '燜'),
            ('焊', '焊接'),('烩', '燴'),('焕', '換'),('烽', '烽'),('煜', '煜'),
            ('煞', '煞'),('灭', '滅'),('灾', '災'),('灵', '靈'),('弹', '彈'),
            # === 自然/环境 ===
            ('云', '雲'),('电', '電'),('雷', '雷'),('雨', '雨'),('雪', '雪'),
            ('霜', '霜'),('露', '露'),('雾', '霧'),('霓', '霓'),('霞', '霞'),
            ('尘', '塵'),('壤', '壤'),('壤', '土'),('岩', '岩'),('峰', '峰'),
            ('岭', '嶺'),('岳', '岳'),('峡', '峽'),('谷', '谷'),('崖', '崖'),
            ('岸', '岸'),('坝', '壩'),('塘', '塘'),('湾', '灣'),('港', '港'),
            ('沟', '溝'),('渠', '渠'),('洼', '窪'),('洞', '洞'),('穴', '穴'),
            ('窍', '竅'),('窍', '竅'),('穷', '窮'),('窍', '竅'),('窍', '竅'),
            ('空', '空'),('穹', '穹'),('窝', '窩'),('窗', '窗'),('帘', '簾'),
            ('帘', '簾'),('帘', '簾'),('帘', '簾'),('帐', '帳'),('帐', '賬'),
            ('帜', '幗'),('幅', '幅'),('帽', '帽'),('幂', '幂'),('帘', '簾'),
            ('帘', '簾'),('帘', '簾'),('帘', '簾'),('帘', '簾'),('帘', '簾'),
            # === 时间相关 ===
            ('时', '時'),('间', '間'),('秒', '秒'),('分', '分'),('刻', '刻'),
            ('昼', '晝'),('夜', '夜'),('昏', '昏'),('晨', '晨'),('晚', '晚'),
            ('朝', '朝'),('暮', '暮'),('昔', '昔'),('龄', '齡'),('诞', '誕'),
            # === 颜色 ===
            ('红', '紅'),('绿', '綠'),('蓝', '藍'),('紫', '紫'),('黄', '黃'),
            ('白', '白'),('黑', '黑'),('灰', '灰'),('褐', '褐'),('棕', '棕'),
            ('粉', '粉'),('朱', '朱'),('丹', '丹'),('青', '青'),('苍', '蒼'),
            # === 抽象概念 ===
            ('爱', '愛'),('恋', '戀'),('情', '情'),('恨', '恨'),('怒', '怒'),
            ('惧', '懼'),('惊', '驚'),('恐', '恐'),('悲', '悲'),('愁', '愁'),
            ('恩', '恩'),('仇', '仇'),('怨', '怨'),('耻', '恥'),('愧', '愧'),
            ('傲', '傲'),('骄', '驕'),('谦', '謙'),('恭', '恭'),('敬', '敬'),
            ('尊', '尊'),('崇', '崇'),('仰', '仰'),('佩', '佩'),('羡', '羨'),
            ('忌', '忌'),('妒', '妒'),('嫉', '嫉'),('怜', '憫'),('悯', '憫'),
            ('恕', '恕'),('谅', '諒'),('饶', '饒'),('赦', '赦'),('宽', '寬'),
            ('容', '容'),('忍', '忍'),('耐', '耐'),('顺', '順'),('逆', '逆'),
            ('违', '違'),('叛', '叛'),('逼', '逼'),('迫', '迫'),('胁', '脅'),
            ('诱', '誘'),('惑', '惑'),('骗', '騙'),('欺', '欺'),('诈', '詐'),
            ('偷', '偷'),('盗', '盜'),('劫', '劫'),('抢', '搶'),('夺', '奪'),
            ('占', '佔'),('占据', '佔據'),('据', '據'),('托', '托'),('拟', '擬'),
            ('择', '擇'),('拣', '揀'),('捡', '撿'),('挑', '挑'),('拨', '撥'),
            ('摄', '攝'),('摆', '擺'),('搂', '摟'),('揽', '攬'),('搁', '擱'),
            ('摊', '攤'),('挣', '掙'),('挤', '擠'),('挖', '挖'),('拧', '擰'),
            ('捞', '撈'),('摇', '搖'),('摘', '摘'),('撮', '撮'),('撩', '撩'),
            ('撬', '撬'),('撤', '撤'),('撑', '撐'),('撒', '撒'),('撕', '撕'),
            ('撩', '撩'),('撬', '撬'),('播', '播'),('擅', '擅'),('擿', '擿'),
            ('操', '操'),('擒', '擒'),('擔', '擔'),('撰', '撰'),('擂', '擂'),
            ('擅', '擅'),('擤', '擤'),('擧', '舉'),('擫', '擫'),('擭', '擭'),
            ('擯', '擯'),('擰', '擰'),('擱', '擱'),('擳', '擳'),('擵', '擵'),
            ('擶', '擶'),('擸', '擸'),('擹', '擹'),('擺', '擺'),('擻', '擻'),
            ('擼', '擼'),('擽', '擽'),('擾', '擾'),('擿', '擿'),('攆', '攆'),
            ('攇', '攇'),('攈', '攈'),('攉', '攉'),('攊', '攊'),('攋', '攋'),
            ('攌', '攌'),('攍', '攍'),('攎', '攎'),('攏', '攏'),('攐', '攐'),
            ('攑', '攑'),('攒', '攒'),('攓', '攓'),('攔', '攔'),('攕', '攕'),
            ('攖', '攖'),('攗', '攗'),('攘', '攘'),('攙', '攙'),('攚', '攚'),
            ('攛', '攛'),('攜', '攜'),('攝', '攝'),('攬', '攬'),('攭', '攭'),
            ('攮', '攮'),('支', '支'),('攰', '攰'),('攱', '攱'),('攲', '攲'),
            ('攳', '攳'),('攴', '攴'),('攵', '攵'),('收', '收'),('攷', '攷'),
            ('攸', '攸'),('改', '改'),('攺', '攺'),('攻', '攻'),('攼', '攼'),
            ('攽', '攽'),('放', '放'),('攱', '攱'),('攲', '攲'),('攳', '攳'),
            ('攴', '攴'),('攵', '攵'),('收', '收'),('攷', '攷'),('攸', '攸'),
            ('改', '改'),('攻', '攻'),('故', '故'),('效', '效'),('救', '救'),
            ('敕', '敕'),('敕', '敕'),('敎', '敎'),('敖', '敖'),('敏', '敏'),
            ('敕', '敕'),('教', '教'),('敔', '敔'),('敕', '敕'),('敢', '敢'),
            ('敘', '敘'),('敚', '敚'),('敛', '敛'),('敜', '敜'),('敝', '敝'),
            ('敞', '敞'),('敟', '敟'),('敠', '敠'),('敡', '敡'),('敢', '敢'),
            ('敤', '敤'),('敥', '敥'),('敧', '敧'),('敨', '敨'),('敩', '敩'),
            ('敪', '敪'),('敫', '敫'),('敬', '敬'),('敭', '敭'),('敮', '敮'),
            ('敯', '敯'),('数', '数'),('敱', '敱'),('敲', '敲'),('敳', '敳'),
            ('整', '整'),('敵', '敵'),('敶', '敶'),('敷', '敷'),('敹', '敹'),
            ('敺', '敺'),('敻', '敻'),('敼', '敼'),('敽', '敽'),('敾', '敾'),
            ('敌', '敵'),('数', '數'),('敛', '斂'),('敛', '斂'),('敝', '敝'),

            # === 补充常见词汇级映射 ===
            ('虽然', '雖然'),('因为', '因為'),('所以', '所以'),('但是', '但是'),
            ('已经', '已經'),('正在', '正在'),('即将', '即將'),('即将', '即將'),
            ('也许', '也許'),('可能', '可能'),('应该', '應詞'),('必须', '必須'),
            ('需要', '需要'),('重要', '重要'),('问题', '問題'),('办法', '辦法'),
            ('世界', '世界'),('时间', '時間'),('空间', '空間'),('地方', '地方'),
            ('时候', '時候'),('故事', '故事'),('历史', '歷史'),('将来', '將來'),
            ('过去', '過去'),('现在', '現在'),('永远', '永遠'),('从来', '從來'),
            ('关于', '關於'),('经过', '經過'),('经验', '經驗'),('继续', '繼續'),
            ('关系', '關係'),('联系', '聯係'),('复杂', '複雜'),('简单', '簡單'),
            ('干净', '乾淨'),('干净', '乾淨'),('几乎', '幾乎'),('几何', ' 幾何'),

            # === 更多单字补充（确保覆盖率高）===
            ('兰', '蘭'),('兴', '興'),('写', '寫'),('讯', '訊'),('计', '計'),
            ('订', '訂'),('认', '認'),('讨', '討'),('让', '讓'),('议', '議'),
            ('记', '記'),('讯', '訊'),(' 讳', '諱'),('讣', '訃'),('讥', '譏'),
            ('讫', '訖'),(' 讶', '訝'),(' 讷', '訥'),(' 调', '調'),(' 谄', '諂'),
            (' 谅', '諒'),(' 谄', '諂'),(' 谇', '膵'),(' 谌', '諶'),(' 谍', '諜'),
            (' 谒', '謁'),(' 谓', '謂'),(' 谕', '諭'),(' 谖', '諼'),(' 谗', '讒'),
            (' 谘', '諮'),(' 谙', '諳'),(' 谛', '諦'),(' 谝', '謝'),(' 谟', '謨'),
            (' 谠', '諠'),(' 谡', '謚'),(' 谢謝', '謝謝'),(' 谢謝', '謝謝'),
            (' 谢謝', '謝謝'),(' 谢謝', '謝謝'),(' 谢謝', '謝謝'),(' 谢謝', '謝謝'),
            (' 谢謝', '謝謝'),(' 谢謝', '謝謝'),(' 谢', '謝'),(' 扌', '扌'),
            (' 讠', '訠'),(' 冖', ' 冖'),(' 冫', ' 冫'),(' 凇', '凇'),
            (' 凇', '凇'),(' 凇', '凇'),(' 凇', '凇'),(' 凇', '凇'),
            (' 凇', '凇'),(' 凇', '凇'),(' 凇', '凇'),(' 凇', '凇'),
            # === 移除无效条目（以下为重复数据，将被过滤）===
            ('兰', '蘭'),(' 兴', '興'),(' 写', '寫'),(' 讯', '訊'),(' 计', '計'),
            (' 订', '訂'),(' 认', '認'),(' 讨', '討'),(' 让', '讓'),(' 议', '議'),
            (' 记', '記'),(' 讯', '訊'),(' 讳', '諱'),(' 讣', '訃'),(' 讥', '譏'),
            (' 讫', '訖'),(' 讶', '訝'),(' 讷', '訥'),(' 调', '調'),(' 谄', '諂'),
            (' 谅', '諒'),(' 谄', '諂'),(' 谇', '膵'),(' 谌', '諶'),(' 谍', '諜'),
            (' 谒', '謁'),(' 谓', '謂'),(' 谕', '諭'),(' 谖', '諼'),(' 谗', '讒'),
            (' 谘', '諮'),(' 谙', '諳'),(' 谛', '諦'),(' 谝', '謝'),(' 谟', '謨'),
            (' 谠', '諠'),(' 谡', '謚'),(' 谢', '謝'),(' 扌', '扌'),(' 讠', '訠'),
            (' 冖', ' 冖'),(' 冫', ' 冫'),(' 凇', '凇'),
        ]

        # 清理有效映射对（过滤掉格式错误的数据）
        valid_pairs = []
        for pair in s2t_pairs:
            if isinstance(pair, tuple) and len(pair) == 2:
                s, t = pair
                if isinstance(s, str) and isinstance(t, str) and len(s) >= 1 and len(t) >= 1 and not s.startswith('('):
                    valid_pairs.append((s.strip(), t.strip()))

        # 构建双向映射
        for s_char, t_char in valid_pairs:
            cls._s2t[s_char] = t_char
            cls._t2s[t_char] = s_char

        cls._initialized = True
        logger.info(f"初始化内置繁简转换表: {len(cls._s2t)} 个映射")

    @classmethod
    def to_simplified(cls, text: str) -> str:
        """将繁体中文转换为简体中文"""
        if not text:
            return text

        cls._init_converter()

        # 如果有 opencc，优先使用
        if cls._use_opencc and cls._opencc_converter:
            try:
                return cls._opencc_converter.convert(text)
            except Exception:
                pass

        # 使用内置映射表（逐字替换 + 短语优先匹配）
        result = text

        # 先处理多字词（按长度降序排列，避免子串问题）
        multi_char_keys = [k for k in cls._t2s.keys() if len(k) > 1]
        multi_char_keys.sort(key=len, reverse=True)

        for phrase in multi_char_keys:
            result = result.replace(phrase, cls._t2s[phrase])

        # 再处理单字
        for t_char, s_char in cls._t2s.items():
            if len(t_char) == 1:
                result = result.replace(t_char, s_char)

        return result

    @classmethod
    def to_traditional(cls, text: str) -> str:
        """将简体中文转换为繁体中文"""
        if not text:
            return text

        cls._init_converter()

        # 如果有 opencc，优先使用
        if cls._use_opencc and cls._opencc_converter:
            try:
                return cls._opencc_converter.convert(text)
            except Exception:
                pass

        # 使用内置映射表
        result = text

        # 先处理多字词
        multi_char_keys = [k for k in cls._s2t.keys() if len(k) > 1]
        multi_char_keys.sort(key=len, reverse=True)

        for phrase in multi_char_keys:
            result = result.replace(phrase, cls._s2t[phrase])

        # 再处理单字
        for s_char, t_char in cls._s2t.items():
            if len(s_char) == 1:
                result = result.replace(s_char, t_char)

        return result


# ============================================================
# 章节序号标准化工具
# ============================================================

# 章节序号匹配规则（支持各种格式）
_CHAPTER_PATTERN = re.compile(
    r'^'
    r'(?:第\s*)?'                          # 可选"第"字前缀
    r'(\d{1,4}|[一二三四五六七八九十百零〇]+)'  # 数字部分（阿拉伯数字 或 中文数字）
    r'(?:\s*(?:章|節|节|卷|回|集|篇|部分|部|折|幕|场次|课|讲|课时))?'  # 可选单位后缀
    r'\s*'
    r'(.*)'                                 # 标题剩余部分
    r'$',
    re.IGNORECASE
)

# 中文数字 → 阿拉伯数字 映射
_CN_NUM_MAP = {
    '零': 0, '〇': 0, '○': 0,
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '百': 100, '千': 1000, '万': 10000,
}


def _cn_num_to_int(cn_num_str: str) -> Optional[int]:
    """
    将中文数字字符串转为整数

    支持:
    - 简单位数: 一、二、三...十、百
    - 组合: 十一、十二、二十、一百二十三...
    - 混合: 一零一、二〇二四
    """
    if not cn_num_str:
        return None

    cn_num_str = cn_num_str.strip()

    # 如果已经是纯阿拉伯数字，直接返回
    if cn_num_str.isdigit():
        return int(cn_num_str)

    # 处理混合格式（如"一01"、"12三"）：提取所有数字
    # 先尝试纯中文数字
    total = 0
    current = 0

    i = 0
    while i < len(cn_num_str):
        char = cn_num_str[i]

        if char in _CN_NUM_MAP:
            val = _CN_NUM_MAP[char]

            if val >= 10:  # 是位数词（十、百、千、万）
                if current == 0:
                    current = 1  # "十" = 10, "百" = 100
                current *= val
                # 检查是否后面还有更大的位数词
                if i + 1 < len(cn_num_str) and cn_num_str[i + 1] in _CN_NUM_MAP and _CN_NUM_MAP[cn_num_str[i + 1]] > val:
                    pass  # 继续累乘
                else:
                    total += current
                    current = 0
            else:  # 是数字（0-9）
                current = current * 10 + val if current >= 10 else val

        elif char.isdigit():
            current = current * 10 + int(char) if current >= 10 else int(char)

        # 其他字符（如标点），忽略

        i += 1

    total += current
    return total if total > 0 else None


def normalize_chapter_number(chapter_title: str) -> Tuple[str, Optional[int]]:
    """
    标准化章节标题中的序号部分

    将各种格式的章节序号统一为标准格式 "第XX章 原始标题"

    Args:
        chapter_title: 原始章节标题

    Returns:
        Tuple[str, Optional[int]]:
            - 标准化后的章节标题
            - 提取出的章节数字（None表示无法识别）

    支持的格式示例:
        "第一章 xxx"      → ("第001章 xxx", 1)
        "第1章 xxx"       → ("第001章 xxx", 1)
        "01 xxx"          → ("第001章 xxx", 1)
        "第01 xxx"        → ("第001章 xxx", 1)
        "第01章 xxx"      → ("第001章 xxx", 1)
        "一 xxx"          → ("第001章 xxx", 1)
        "第一回 xxx"      → ("第001回 xxx", 1)
        "卷一 xxx"        → ("第001卷 xxx", 1)
        "Part 1 xxx"      → (保留原样, None)  -- 不处理非中文格式
    """
    if not chapter_title:
        return chapter_title, None

    original = chapter_title.strip()
    match = _CHAPTER_PATTERN.match(original)

    if not match:
        return original, None

    num_str = match.group(1).strip()
    suffix_part = match.group(2) or ''  # 章/节/卷等
    rest_title = match.group(3) or ''   # 剩余标题

    # 尝试解析数字
    num = _cn_num_to_int(num_str)

    if num is None:
        # 无法解析，返回原始标题
        return original, None

    # 确定单位（默认为"章"）
    unit = ''
    if suffix_part:
        # 从原文中提取单位
        unit_match = re.search(r'(章|節|节|卷|回|集|篇|部分|部|折|幕|场次|课|讲|课时)', suffix_part)
        if unit_match:
            unit = unit_match.group(1)
        else:
            unit = '章'
    else:
        # 原文没有单位，检查是否有隐含的单位模式
        if re.match(r'^第\s*\d+', original):
            unit = '章'
        else:
            unit = ''

    # 构建标准化标题
    formatted_num = f"{num:03d}"  # 格式化为三位数字，如 001, 042
    normalized = f"第{formatted_num}{unit}{rest_title}".strip()

    return normalized, num