"""
书籍比较工具类，提供书籍重复检测和内容比较功能
"""

import os
from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from src.core.book import Book
from src.utils.file_utils import FileUtils
from src.utils.string_utils import StringUtils
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DuplicateType(Enum):
    """重复类型"""
    FILE_NAME = "文件名相同"
    CONTENT_SIMILAR = "内容相似"
    HASH_IDENTICAL = "哈希值相同"
    CONTENT_SUBSET = "内容子集"

@dataclass
class DuplicateGroup:
    """重复书籍组"""
    duplicate_type: DuplicateType
    books: List[Book]
    similarity: float = 0.0
    recommended_to_keep: List[Book] = None
    recommended_to_delete: List[Book] = None
    
    def __post_init__(self):
        if self.recommended_to_keep is None:
            self.recommended_to_keep = []
        if self.recommended_to_delete is None:
            self.recommended_to_delete = []

@dataclass
class BookComparison:
    """书籍比较结果"""
    book1: Book
    book2: Book
    file_name_match: bool
    similarity: float
    hash_match: bool
    duplicate_types: List[DuplicateType]

class BookDuplicateDetector:
    """书籍重复检测器"""
    
    @staticmethod
    def find_duplicates(books: List[Book], progress_callback=None) -> List[DuplicateGroup]:
        """
        查找重复书籍
        
        Args:
            books: 书籍列表
            progress_callback: 进度回调函数
            
        Returns:
            List[DuplicateGroup]: 重复书籍组列表
        """
        duplicate_groups = []
        processed_indices = set()
        total = len(books)
        
        logger.info(f"开始检测{total}本书籍中的重复项")
        
        for i, book1 in enumerate(books):
            if progress_callback:
                progress_callback(i, total)
                
            if i in processed_indices:
                continue
                
            # 查找与当前书籍重复的书籍
            related_books = [book1]
            duplicate_types_found = set()
            max_similarity = 0.0
            
            for j, book2 in enumerate(books):
                if i == j or j in processed_indices:
                    continue
                    
                comparison = BookDuplicateDetector.compare_books(book1, book2)
                
                if comparison.duplicate_types:
                    related_books.append(book2)
                    processed_indices.add(j)
                    
                    # 记录所有发现的重复类型
                    duplicate_types_found.update(comparison.duplicate_types)
                    
                    # 记录最高相似度
                    if comparison.similarity > max_similarity:
                        max_similarity = comparison.similarity
            
            # 如果找到重复项，创建重复组
            if len(related_books) > 1:
                # 确定主要重复类型（优先级：哈希值相同 > 内容相似 > 文件名相同）
                primary_type = DuplicateType.FILE_NAME
                if DuplicateType.CONTENT_SIMILAR in duplicate_types_found:
                    primary_type = DuplicateType.CONTENT_SIMILAR
                if DuplicateType.HASH_IDENTICAL in duplicate_types_found:
                    primary_type = DuplicateType.HASH_IDENTICAL
                
                # 创建重复组
                group = DuplicateGroup(
                    duplicate_type=primary_type,
                    books=related_books,
                    similarity=max_similarity
                )
                
                # 推荐保留和删除的书籍
                BookDuplicateDetector._recommend_deletion(group)
                
                duplicate_groups.append(group)
                
                # 标记当前书籍为已处理
                processed_indices.add(i)
        
        if progress_callback:
            progress_callback(total, total)
            
        logger.info(f"检测完成，共发现{len(duplicate_groups)}组重复书籍")
        
        return duplicate_groups
    
    @staticmethod
    def compare_books(book1: Book, book2: Book) -> BookComparison:
        """
        比较两本书籍
        
        Args:
            book1: 书籍1
            book2: 书籍2
            
        Returns:
            BookComparison: 比较结果
        """
        # 检查文件名是否相同
        file_name_match = book1.file_name.lower() == book2.file_name.lower()
        
        # 计算内容相似度
        similarity = 0.0
        try:
            content1 = BookDuplicateDetector._get_book_content(book1)
            content2 = BookDuplicateDetector._get_book_content(book2)
            
            if content1 and content2:
                similarity = StringUtils.book_content_similarity(content1, content2)
        except Exception as e:
            logger.error(f"比较书籍内容时出错: {e}")
        
        # 检查哈希值是否相同
        hash_match = False
        try:
            if os.path.exists(book1.path) and os.path.exists(book2.path):
                hash1 = FileUtils.calculate_file_sha256(book1.path)
                hash2 = FileUtils.calculate_file_sha256(book2.path)
                hash_match = hash1 == hash2
        except Exception as e:
            logger.error(f"计算文件哈希时出错: {e}")
        
        # 确定重复类型
        duplicate_types = []
        if hash_match:
            duplicate_types.append(DuplicateType.HASH_IDENTICAL)
        if similarity >= 0.2:  # 相似度超过20%
            duplicate_types.append(DuplicateType.CONTENT_SIMILAR)
        if file_name_match:
            duplicate_types.append(DuplicateType.FILE_NAME)
        
        return BookComparison(
            book1=book1,
            book2=book2,
            file_name_match=file_name_match,
            similarity=similarity,
            hash_match=hash_match,
            duplicate_types=duplicate_types
        )
    
    @staticmethod
    def _recommend_deletion(group: DuplicateGroup):
        """
        推荐删除选择
        
        Args:
            group: 重复书籍组
        """
        if not group.books or len(group.books) < 2:
            return
        
        # 对于包含关系类型，优先保留大书
        if group.duplicate_type == DuplicateType.CONTENT_SUBSET:
            # 按文件大小排序，大的优先
            sorted_books = sorted(group.books, key=lambda b: b.size if b.size else 0, reverse=True)
        else:
            # 其他类型按照优先级排序：文件大小 > 修改时间 > 阅读进度
            sorted_books = sorted(group.books, key=lambda b: (
                b.size,  # 文件大小
                b.modified_time if hasattr(b, 'modified_time') else 0,  # 修改时间
                b.read_progress if hasattr(b, 'read_progress') else 0  # 阅读进度
            ), reverse=True)
        
        # 保留第一个（最优的），其余推荐删除
        group.recommended_to_keep = [sorted_books[0]]
        group.recommended_to_delete = sorted_books[1:]
    
    @staticmethod
    def _get_book_content(book: Book, max_size: int = 1024 * 1024) -> Optional[str]:
        """
        获取书籍内容（采样）
        
        Args:
            book: 书籍对象
            max_size: 最大读取大小
            
        Returns:
            Optional[str]: 书籍内容
        """
        try:
            if not os.path.exists(book.path):
                return None
                
            # 检查文件扩展名，跳过二进制格式文件
            _, ext = os.path.splitext(book.path.lower())
            binary_extensions = {'.epub', '.mobi', '.azw', '.azw3', '.pdf', '.djvu', '.cbr', '.cbz', '.fb2', '.lit', '.pdb', '.tcr'}
            
            if ext in binary_extensions:
                # 对于二进制格式文件，尝试通过应用读取内容（如果有内容的话）
                # 这里返回None表示无法直接读取内容进行比较
                return None
                
            # 如果文件太大，只读取部分内容
            file_size = os.path.getsize(book.path)
            if file_size > max_size:
                with open(book.path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 读取开头部分
                    chunk_size = max_size // 2
                    start = f.read(chunk_size)
                    
                    # 尝试读取结尾部分，但处理可能的seek错误
                    try:
                        # 保存当前位置
                        current_pos = f.tell()
                        # 尝试seek到文件末尾
                        f.seek(0, os.SEEK_END)
                        end_pos = f.tell()
                        # 计算需要读取的结尾部分起始位置
                        seek_pos = max(0, end_pos - chunk_size)
                        f.seek(seek_pos)
                        end = f.read(chunk_size)
                        return start + "\n...\n" + end
                    except (OSError, ValueError):
                        # 如果seek失败，返回已读取的开头部分
                        return start + "\n...\n[文件结尾无法读取]"
            else:
                with open(book.path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"读取书籍内容时出错: {e}")
            return None
    
    @staticmethod
    def compare_books_content(book1: Book, book2: Book) -> Dict[str, Any]:
        """
        详细比较两本书籍的内容
        
        Args:
            book1: 书籍1
            book2: 书籍2
            
        Returns:
            Dict[str, Any]: 比较结果
        """
        result = {
            "book1_info": {
                "title": book1.title,
                "path": book1.path,
                "size": FileUtils.format_file_size(book1.size),
                "format": book1.format
            },
            "book2_info": {
                "title": book2.title,
                "path": book2.path,
                "size": FileUtils.format_file_size(book2.size),
                "format": book2.format
            },
            "similarity": 0.0,
            "samples": {
                "book1": {"start": "", "middle": "", "end": ""},
                "book2": {"start": "", "middle": "", "end": ""}
            }
        }
        
        try:
            content1 = BookDuplicateDetector._get_book_content(book1)
            content2 = BookDuplicateDetector._get_book_content(book2)
            
            if content1 and content2:
                result["similarity"] = StringUtils.book_content_similarity(content1, content2)
                
                # 提取采样内容用于对比
                sample_size = 1000
                samples1 = StringUtils._sample_content(content1, sample_size)
                samples2 = StringUtils._sample_content(content2, sample_size)
                
                if len(samples1) >= 3:
                    result["samples"]["book1"]["start"] = samples1[0]
                    result["samples"]["book1"]["middle"] = samples1[1]
                    result["samples"]["book1"]["end"] = samples1[2]
                
                if len(samples2) >= 3:
                    result["samples"]["book2"]["start"] = samples2[0]
                    result["samples"]["book2"]["middle"] = samples2[1]
                    result["samples"]["book2"]["end"] = samples2[2]
        except Exception as e:
            logger.error(f"详细比较书籍内容时出错: {e}")
        
        return result