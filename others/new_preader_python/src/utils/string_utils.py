"""
字符串工具类，提供文本处理功能
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

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