"""
书架管理器，负责管理书籍集合和相关操作
"""

import os

import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path

from src.core.book import Book
from src.core.database_manager import DatabaseManager
from src.config.default_config import SUPPORTED_FORMATS
from src.utils.logger import LoggerSetup

from src.utils.logger import get_logger

logger = get_logger(__name__)

@LoggerSetup.debug_log
def debug_logged(func):
    """调试日志装饰器"""
    return func

class Bookshelf:
    """书架类，管理书籍集合"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化书架
        
        Args:
            data_dir: 数据目录，如果为None则使用默认目录
        """
        if data_dir is None:
            # 默认数据目录为用户主目录下的.config/new_preader/books文件夹
            self.data_dir = os.path.join(str(Path.home()), ".config", "new_preader", "books")
        else:
            self.data_dir = data_dir
            
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        
        self.books: Dict[str, Book] = {}  # 书籍字典，键为书籍路径
        self.reading_history: List[Dict[str, Any]] = []  # 阅读历史记录
        
        # 加载书籍数据
        self._load_books()
        self._load_reading_history()
    
    def _load_books(self) -> None:
        """从数据库加载书籍数据"""
        try:
            books = self.db_manager.get_all_books()
            for book in books:
                # 检查书籍文件是否仍然存在，但即使不存在也保留记录
                if book.path and os.path.exists(book.path):
                    self.books[book.path] = book
                else:
                    logger.warning(f"书籍文件不存在，但保留记录: {book.path}")
                    # 即使文件不存在，也保留书籍记录，但标记为文件丢失
                    self.books[book.path] = book
                    
            logger.info(f"已加载 {len(self.books)} 本书籍")
        except Exception as e:
            logger.error(f"从数据库加载书籍数据时出错: {e}")
    
    def _load_reading_history(self) -> None:
        """从数据库加载阅读历史记录"""
        try:
            self.reading_history = self.db_manager.get_reading_history()
            logger.info(f"已加载 {len(self.reading_history)} 条阅读历史记录")
        except Exception as e:
            logger.error(f"从数据库加载阅读历史记录时出错: {e}")
    
    @debug_logged
    def save(self) -> bool:
        """
        保存书架数据到数据库
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 保存所有书籍到数据库
            for book in self.books.values():
                if not self.db_manager.add_book(book):
                    logger.error(f"保存书籍到数据库失败: {book.title}")
                    return False
            
            logger.info("书架数据已保存到数据库")
            return True
        except Exception as e:
            logger.error(f"保存书架数据时出错: {e}")
            return False
    
    @debug_logged
    def add_book(self, path: str, title: Optional[str] = None, author: Optional[str] = None) -> Optional[Book]:
        """
        添加书籍
        
        Args:
            path: 书籍文件路径
            title: 书籍标题，如果为None则使用文件名
            author: 书籍作者，如果为None则为"未知作者"
            
        Returns:
            Optional[Book]: 添加的书籍对象，如果添加失败则返回None
        """
        try:
            # 检查文件是否已存在于书架中
            abs_path = os.path.abspath(path)
            
            # 使用数据库检查书籍是否已存在
            existing_book = self.db_manager.get_book(abs_path)
            if existing_book:
                logger.warning(f"书籍已存在于书架中: {abs_path}")
                return existing_book
            
            # 创建书籍对象
            book = Book(abs_path, title, author)
            
            # 将书籍保存到数据库
            self.db_manager.add_book(book)
            
            # 更新内存中的书籍字典（用于向后兼容）
            self.books[abs_path] = book
            
            logger.info(f"已添加书籍到数据库: {book.title}")
            return book
        except Exception as e:
            logger.error(f"添加书籍时出错: {e}")
            return None
    
    @debug_logged
    def remove_book(self, path: str) -> bool:
        """
        移除书籍
        
        Args:
            path: 书籍文件路径
            
        Returns:
            bool: 是否成功移除
        """
        abs_path = os.path.abspath(path)
        if abs_path in self.books:
            del self.books[abs_path]
            
            # 从数据库中删除书籍
            self.db_manager.delete_book(abs_path)
            
            # 从阅读历史中移除相关记录
            self.reading_history = [record for record in self.reading_history if record["path"] != abs_path]
            
            logger.info(f"已从数据库中移除书籍: {abs_path}")
            return True
        else:
            logger.warning(f"书籍不存在于书架中: {abs_path}")
            return False
    
    @debug_logged
    def get_book(self, path: str) -> Optional[Book]:
        """
        获取书籍
        
        Args:
            path: 书籍文件路径
            
        Returns:
            Optional[Book]: 书籍对象，如果不存在则返回None
        """
        abs_path = os.path.abspath(path)
        return self.books.get(abs_path)
    
    def get_all_books(self) -> List[Book]:
        """
        获取所有书籍
        
        Returns:
            List[Book]: 书籍列表
        """
        return list(self.books.values())
    
    def search_books(self, keyword: str, format: Optional[str] = None) -> List[Book]:
        """
        搜索书籍
        
        Args:
            keyword: 搜索关键词
            format: 可选，文件格式筛选
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        # 使用数据库进行搜索，支持文件格式筛选
        return self.db_manager.search_books(keyword, format)
    
    def filter_books_by_format(self, format_: str) -> List[Book]:
        """
        按格式筛选书籍
        
        Args:
            format_: 文件格式（如".txt", ".epub"等）
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        if not format_.startswith('.'):
            format_ = f".{format_}"
            
        return [book for book in self.books.values() if book.format == format_.lower()]
    
    def filter_books_by_tag(self, tag: str) -> List[Book]:
        """
        按标签筛选书籍
        
        Args:
            tag: 标签名称
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        return [book for book in self.books.values() if tag in book.tags]
    
    def filter_books_by_author(self, author: str) -> List[Book]:
        """
        按作者筛选书籍
        
        Args:
            author: 作者名称
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        author = author.lower()
        return [book for book in self.books.values() if author in book.author.lower()]
    
    def sort_books(self, key: str, reverse: bool = False) -> List[Book]:
        """
        排序书籍（使用数据库排序）
        
        Args:
            key: 排序键，可选值为"title", "author", "add_date", "last_read_date", "progress"
            reverse: 是否倒序
            
        Returns:
            List[Book]: 排序后的书籍列表
        """
        try:
            # 使用数据库管理器进行排序
            return self.db_manager.get_sorted_books(key, reverse)
        except Exception as e:
            logger.error(f"数据库排序失败，使用内存排序: {e}")
            # 降级到内存排序
            return self._sort_books_in_memory(key, reverse)
    
    def _sort_books_in_memory(self, key: str, reverse: bool = False) -> List[Book]:
        """
        内存排序（数据库排序失败时的降级方案）
        
        Args:
            key: 排序键
            reverse: 是否倒序
            
        Returns:
            List[Book]: 排序后的书籍列表
        """
        books = list(self.books.values())
        
        if key == "title":
            return sorted(books, key=lambda x: x.title.lower(), reverse=reverse)
        elif key == "author":
            return sorted(books, key=lambda x: x.author.lower(), reverse=reverse)
        elif key == "add_date":
            return sorted(books, key=lambda x: x.add_date, reverse=reverse)
        elif key == "last_read_date":
            # 将没有阅读记录的书籍排在最后
            def get_last_read_date(book):
                if book.last_read_date:
                    return book.last_read_date
                # 返回一个极早的日期，确保没有阅读记录的书籍排在最后
                # 无论升序还是降序，没有阅读记录的都应该排在最后
                return datetime.min.isoformat()
            return sorted(books, key=get_last_read_date, reverse=reverse)
        elif key == "progress":
            return sorted(books, key=lambda x: x.reading_progress or 0, reverse=reverse)
        else:
            logger.warning(f"不支持的排序键: {key}，将使用标题排序")
            return sorted(books, key=lambda x: x.title.lower(), reverse=reverse)
    
    def get_recently_read_books(self, limit: int = 3) -> List[Book]:
        """
        获取最近阅读的书籍
        
        Args:
            limit: 返回的书籍数量
            
        Returns:
            List[Book]: 最近阅读的书籍列表
        """
        # 按最后阅读时间排序，确保last_read_date不为None
        books = [book for book in self.books.values() if book.last_read_date]
        books.sort(key=lambda x: x.last_read_date or "", reverse=True)
        return books[:limit]
    
    def add_reading_record(self, book: Book, duration: int, pages_read: int = 0, reading_time: Optional[int] = None) -> None:
        """
        添加阅读记录
        
        Args:
            book: 书籍对象
            duration: 阅读时长（秒）
            pages_read: 阅读页数（可选）
            reading_time: 阅读时间（秒，可选，已弃用，使用duration参数）
        """
        # 保持向后兼容性：如果传入了reading_time，使用它，否则使用duration
        effective_duration = reading_time if reading_time is not None else duration
        
        record = {
            "path": book.path,
            "title": book.title,
            "author": book.author,
            "timestamp": datetime.now().isoformat(),
            "duration": effective_duration,
            "progress": book.reading_progress,
            "pages_read": pages_read
        }
        
        self.reading_history.append(record)
        
        # 更新书籍的阅读时间
        book.add_reading_time(effective_duration)
        
        # 保存书架数据
        self.save()
    
    def get_reading_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取阅读历史记录
        
        Args:
            limit: 返回的记录数量，如果为None则返回所有记录
            
        Returns:
            List[Dict[str, Any]]: 阅读历史记录列表
        """
        if limit is None:
            return self.reading_history
        return self.reading_history[-limit:]
    
    def clear_reading_history(self, book_path: Optional[str] = None) -> None:
        """
        清除阅读历史记录
        
        Args:
            book_path: 书籍路径，如果为None则清除所有记录
        """
        if book_path is None:
            self.reading_history = []
        else:
            abs_path = os.path.abspath(book_path)
            self.reading_history = [record for record in self.reading_history if record["path"] != abs_path]
        
        # 保存书架数据
        self.save()
    
    @debug_logged
    def scan_directory(self, directory: str) -> Tuple[int, List[str]]:
        """
        扫描目录并添加书籍
        
        Args:
            directory: 目录路径
            
        Returns:
            Tuple[int, List[str]]: (添加的书籍数量, 失败的文件列表)
        """
        if not os.path.isdir(directory):
            logger.error(f"目录不存在: {directory}")
            return 0, []
        
        added_count = 0
        failed_files = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                if file_ext in SUPPORTED_FORMATS:
                    try:
                        if self.add_book(file_path):
                            added_count += 1
                        else:
                            failed_files.append(file_path)
                    except Exception as e:
                        logger.error(f"添加书籍时出错: {e}")
                        failed_files.append(file_path)
        
        logger.info(f"已从目录 {directory} 添加 {added_count} 本书籍")
        return added_count, failed_files
    
    def batch_set_author(self, book_paths: List[str], author: str) -> int:
        """
        批量设置作者
        
        Args:
            book_paths: 书籍路径列表
            author: 作者名称
            
        Returns:
            int: 成功设置的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            abs_path = os.path.abspath(path)
            if abs_path in self.books:
                book = self.books[abs_path]
                book.author = author
                # 直接更新数据库
                if self.db_manager.update_book(book):
                    success_count += 1
        
        return success_count
    
    def batch_set_tags(self, book_paths: List[str], tags: List[str]) -> int:
        """
        批量设置标签
        
        Args:
            book_paths: 书籍路径列表
            tags: 标签列表
            
        Returns:
            int: 成功设置的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            abs_path = os.path.abspath(path)
            if abs_path in self.books:
                book = self.books[abs_path]
                # 将标签列表转换为逗号分隔的字符串
                book.tags = ",".join(tags) if tags else ""
                # 直接更新数据库
                if self.db_manager.update_book(book):
                    success_count += 1
        
        return success_count
    

    
    def batch_delete_books(self, book_paths: List[str]) -> int:
        """
        批量删除书籍
        
        Args:
            book_paths: 书籍路径列表
            
        Returns:
            int: 成功删除的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            if self.remove_book(path):
                success_count += 1
        
        return success_count
    
    def batch_clear_history(self, book_paths: List[str]) -> int:
        """
        批量清除阅读历史记录
        
        Args:
            book_paths: 书籍路径列表
            
        Returns:
            int: 成功清除历史记录的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            abs_path = os.path.abspath(path)
            initial_count = len(self.reading_history)
            self.clear_reading_history(abs_path)
            if len(self.reading_history) < initial_count:
                success_count += 1
        
        return success_count
    
    @debug_logged
    def export_data(self, export_path: str) -> bool:
        """
        导出书架数据
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 从数据库获取所有书籍
            books = self.db_manager.get_all_books()
            # 从数据库获取阅读历史
            reading_history = self.db_manager.get_reading_history()
            
            export_data = {
                "books": [book.to_dict() for book in books],
                "reading_history": reading_history,
                "export_time": datetime.now().isoformat()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"书架数据已导出到: {export_path}")
            return True
        except Exception as e:
            logger.error(f"导出书架数据时出错: {e}")
            return False
    
    @debug_logged
    def import_data(self, import_path: str) -> Tuple[int, int]:
        """
        导入书架数据
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            Tuple[int, int]: (导入的书籍数量, 导入的历史记录数量)
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 导入书籍
            books_added = 0
            for book_data in import_data.get("books", []):
                try:
                    # 检查文件是否存在
                    if not os.path.exists(book_data["path"]):
                        logger.warning(f"书籍文件不存在，跳过: {book_data['path']}")
                        continue
                        
                    book = Book.from_dict(book_data)
                    # 添加到数据库
                    if self.db_manager.add_book(book):
                        # 更新内存字典（用于向后兼容）
                        self.books[book.path] = book
                        books_added += 1
                except Exception as e:
                    logger.error(f"导入书籍时出错: {e}")
            
            # 导入阅读历史记录
            history_added = 0
            for record in import_data.get("reading_history", []):
                if record not in self.reading_history:
                    self.reading_history.append(record)
                    # 添加到数据库
                    if self.db_manager.add_reading_record(
                        record["book_path"], 
                        record.get("duration", 0),
                        record.get("pages_read", 0)
                    ):
                        history_added += 1
            
            logger.info(f"已导入 {books_added} 本书籍和 {history_added} 条阅读历史记录")
            return books_added, history_added
        except Exception as e:
            logger.error(f"导入书架数据时出错: {e}")
            return 0, 0

    def batch_clear_tags(self, book_paths: List[str]) -> int:
        """批量清空标签
        
        Args:
            book_paths: 书籍路径列表
            
        Returns:
            int: 成功清空标签的书籍数量
        """
        if not book_paths:
            return 0
            
        success_count = 0
        # 更新数据库，清空标签
        for book_path in book_paths:
            abs_path = os.path.abspath(book_path)
            if abs_path in self.books:
                book = self.books[abs_path]
                book.tags = ""  # 清空标签，设置为空字符串
                # 直接更新数据库
                if self.db_manager.update_book(book):
                    success_count += 1
        
        return success_count