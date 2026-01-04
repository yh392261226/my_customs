"""
优化后的书籍重复检测工具类，提供书籍重复检测和内容比较功能
"""

import os
import random
from typing import List, Dict, Tuple, Optional, Set
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

class OptimizedBookDuplicateDetector:
    """优化的书籍重复检测器"""
    
    @staticmethod
    def find_duplicates(books: List[Book], progress_callback=None, batch_callback=None) -> List[DuplicateGroup]:
        """
        查找重复书籍（优化版本）
        
        Args:
            books: 书籍列表
            progress_callback: 进度回调函数
            batch_callback: 批次完成回调函数，参数为(batch_groups, batch_index, total_batches, processing_remaining)
            
        Returns:
            List[DuplicateGroup]: 重复书籍组列表
        """
        duplicate_groups = []
        total = len(books)
        
        logger.info(f"开始检测{total}本书籍中的重复项")
        
        # 第一步：按哈希值分组（最快的方法）
        hash_to_books = {}
        
        # 第二步：按文件名分组
        normalized_name_to_books = {}
        
        # 初始化进度
        processed = 0
        
        # 收集所有文件哈希值和文件名
        for i, book in enumerate(books):
            if progress_callback and i % 100 == 0:
                # 三个主要阶段：哈希检测、文件名检测、内容相似度检测
                progress_callback(i, total * 3)
                
            # 计算文件哈希
            try:
                if os.path.exists(book.path):
                    file_hash = FileUtils.calculate_file_sha256(book.path)
                    if file_hash not in hash_to_books:
                        hash_to_books[file_hash] = []
                    hash_to_books[file_hash].append(book)
            except Exception as e:
                logger.error(f"计算文件哈希时出错: {e}")
            
            # 按文件名分组（不区分大小写）
            normalized_name = book.file_name.lower()
            if normalized_name not in normalized_name_to_books:
                normalized_name_to_books[normalized_name] = []
            normalized_name_to_books[normalized_name].append(book)
            
            processed += 1
        
        # 创建哈希值相同的组
        for file_hash, books_list in hash_to_books.items():
            if len(books_list) > 1:
                group = DuplicateGroup(
                    duplicate_type=DuplicateType.HASH_IDENTICAL,
                    books=books_list,
                    similarity=1.0  # 哈希相同表示内容完全相同
                )
                OptimizedBookDuplicateDetector._recommend_deletion(group)
                duplicate_groups.append(group)
        
        # 收集所有已经在哈希组中的书籍
        all_hash_books = set()
        for group in duplicate_groups:
            if group.duplicate_type == DuplicateType.HASH_IDENTICAL:
                all_hash_books.update(group.books)
                
        # 创建文件名相同的组（排除已经在哈希组中的书籍）
        for normalized_name, books_list in normalized_name_to_books.items():
            if len(books_list) > 1:
                # 过滤掉已经在哈希组中的书籍
                filtered_books = [book for book in books_list if book not in all_hash_books]
                if len(filtered_books) > 1:
                    group = DuplicateGroup(
                        duplicate_type=DuplicateType.FILE_NAME,
                        books=filtered_books,
                        similarity=0.0  # 文件名相同不保证内容相似
                    )
                    OptimizedBookDuplicateDetector._recommend_deletion(group)
                    duplicate_groups.append(group)
        
        # 更新进度
        if progress_callback:
            progress_callback(total * 2, total * 3)
        
        # 对剩余书籍进行内容相似度检测（限制数量以提高性能）
        # 收集所有已经在其他组中的书籍
        all_processed_books = set()
        for group in duplicate_groups:
            all_processed_books.update(group.books)
        
        # 只对未处理的书籍进行内容相似度检测
        remaining_books = [book for book in books if book not in all_processed_books]
        
        # 分批处理书籍，每批处理50本
        batch_size = 50
        total_batches = (len(remaining_books) + batch_size - 1) // batch_size
        
        logger.info(f"将进行内容相似度检测，共{len(remaining_books)}本书，分{total_batches}批处理，每批{batch_size}本")
        
        # 对剩余书籍进行两两内容相似度比较（分批处理）
        processed_books_in_content = 0  # 已处理的书籍数量（而不是比较次数）
        
        # 分批处理书籍
        content_similar_groups = []  # 用于存放内容相似度重复组
        
        for batch_index in range(total_batches):
            start_index = batch_index * batch_size
            end_index = min(start_index + batch_size, len(remaining_books))
            batch_books = remaining_books[start_index:end_index]
            
            logger.info(f"处理第{batch_index + 1}批书籍，共{len(batch_books)}本")
            
            # 在当前批内进行两两比较
            batch_found_duplicates = False
            batch_duplicate_groups = []
            
            for i in range(len(batch_books)):
                book1 = batch_books[i]
                similar_books = [book1]  # 始终包含当前书籍
                
                # 只与当前批中后续的书籍比较，避免跨批重复
                for j in range(i + 1, len(batch_books)):
                    book2 = batch_books[j]
                    
                    # 确保不是同一本书（路径不同）
                    if book1.path == book2.path:
                        continue
                    
                    # 只比较文件大小相近的书籍（减少比较次数）
                    if book1.size and book2.size:
                        size_ratio = min(book1.size, book2.size) / max(book1.size, book2.size)
                        if size_ratio < 0.5:  # 文件大小相差超过一倍，不太可能内容相似
                            continue
                    
                    try:
                        comparison = OptimizedBookDuplicateDetector._compare_books_fast(book1, book2)
                        if comparison.duplicate_types and DuplicateType.CONTENT_SIMILAR in comparison.duplicate_types:
                            similar_books.append(book2)
                            batch_found_duplicates = True
                    except Exception as e:
                        logger.error(f"比较书籍内容时出错: {e}")
                
                if len(similar_books) > 1:
                    # 计算最大相似度
                    max_sim = 0.0
                    for j in range(1, len(similar_books)):
                        try:
                            comparison = OptimizedBookDuplicateDetector._compare_books_fast(similar_books[0], similar_books[j])
                            if comparison.similarity > max_sim:
                                max_sim = comparison.similarity
                        except:
                            pass
                    
                    group = DuplicateGroup(
                        duplicate_type=DuplicateType.CONTENT_SIMILAR,
                        books=similar_books,
                        similarity=max_sim
                    )
                    OptimizedBookDuplicateDetector._recommend_deletion(group)
                    batch_duplicate_groups.append(group)
            
            # 更新已处理的书籍数量
            processed_books_in_content += len(batch_books)
            
            # 调用进度回调，使用已处理的书籍数量而不是比较次数
            if progress_callback:
                # 第三阶段进度是total*2 + 已处理的书籍数量
                progress_callback(total * 2 + processed_books_in_content, total * 3)
            
            # 将当前批的重复组添加到总列表
            content_similar_groups.extend(batch_duplicate_groups)
            
            # 如果是第一批或找到重复项，调用批次回调
            if batch_index == 0 or batch_found_duplicates:
                # 计算是否还有剩余批次需要处理
                processing_remaining = batch_index < total_batches - 1
                
                # 调用批次回调，更新UI
                if batch_callback:
                    batch_callback(
                        batch_duplicate_groups, 
                        batch_index, 
                        total_batches, 
                        processing_remaining
                    )
            
            # 记录日志
            if batch_found_duplicates:
                logger.info(f"第{batch_index + 1}批找到{len(batch_duplicate_groups)}组重复内容")
            elif batch_index == 0:
                logger.info(f"第{batch_index + 1}批未找到重复项，继续处理下一批")
            elif batch_index == total_batches - 1:
                logger.info(f"所有批次处理完成，共处理{len(remaining_books)}本书，内容相似组共{len(content_similar_groups)}组")
        
        # 将内容相似度组添加到总体重复组列表
        duplicate_groups.extend(content_similar_groups)
        
        if progress_callback:
            progress_callback(total * 3, total * 3)
        
        logger.info(f"重复检测完成，找到{len(duplicate_groups)}组重复书籍")
        return duplicate_groups
    
    @staticmethod
    def _compare_books_fast(book1: Book, book2: Book) -> BookComparison:
        """
        快速比较两本书籍（仅检查必要的条件）
        
        Args:
            book1: 书籍1
            book2: 书籍2
            
        Returns:
            BookComparison: 比较结果
        """
        # 检查文件名是否相同
        file_name_match = book1.file_name.lower() == book2.file_name.lower()
        
        # 计算内容相似度（仅当文件大小相近时）
        similarity = 0.0
        try:
            # 只在文件大小相近时才进行内容比较
            if book1.size and book2.size:
                size_ratio = min(book1.size, book2.size) / max(book1.size, book2.size)
                if size_ratio >= 0.5:  # 文件大小相近
                    content1 = OptimizedBookDuplicateDetector._get_book_content_sample(book1)
                    content2 = OptimizedBookDuplicateDetector._get_book_content_sample(book2)
                    
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
        if similarity >= 0.7:  # 相似度超过70%
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
    def _get_book_content_sample(book: Book, sample_size: int = 5000) -> Optional[str]:
        """
        获取书籍内容采样（快速版本，只读取开头部分）
        
        Args:
            book: 书籍对象
            sample_size: 采样大小
            
        Returns:
            Optional[str]: 书籍内容采样
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
                
            # 只读取开头部分，避免seek操作
            with open(book.path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(sample_size)
        except Exception as e:
            logger.error(f"读取书籍内容时出错: {e}")
            return None
    
    @staticmethod
    def _recommend_deletion(group: DuplicateGroup):
        """
        推荐删除选择
        
        Args:
            group: 重复书籍组
        """
        if not group.books or len(group.books) < 2:
            return
        
        # 按照优先级排序：文件大小 > 修改时间 > 阅读进度
        sorted_books = sorted(group.books, key=lambda b: (
            b.size,  # 文件大小
            b.modified_time if hasattr(b, 'modified_time') else 0,  # 修改时间
            b.read_progress if hasattr(b, 'read_progress') else 0  # 阅读进度
        ), reverse=True)
        
        # 保留第一个（最优的），其余推荐删除
        group.recommended_to_keep = [sorted_books[0]]
        group.recommended_to_delete = sorted_books[1:]