"""
字符串工具类，提供文本处理功能
"""

import re
import unicodedata
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
        计算两个文本的相似度（简单实现）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            float: 相似度（0-1）
        """
        # 将文本转换为小写并分词
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        # 计算交集和并集
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # 计算Jaccard相似度
        if not union:
            return 0.0
        
        return len(intersection) / len(union)