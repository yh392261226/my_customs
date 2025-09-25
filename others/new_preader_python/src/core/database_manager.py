"""
数据库管理器，负责处理书籍元数据的数据库存储
"""

import os
import sqlite3

import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from src.core.book import Book
from src.config.config_manager import ConfigManager

from src.utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """数据库管理器类"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用配置中的路径
        """
        if db_path is None:
            config = ConfigManager().get_config()
            self.db_path = os.path.expanduser(config["paths"]["database"])
        else:
            # 如果传入的是目录路径，则拼接完整的数据库文件路径
            if os.path.isdir(db_path):
                self.db_path = os.path.join(db_path, "database.sqlite")
            else:
                self.db_path = os.path.expanduser(db_path)
            
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建书籍表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    format TEXT NOT NULL,
                    add_date TEXT NOT NULL,
                    last_read_date TEXT,
                    reading_progress REAL DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    word_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            # 创建阅读历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_path TEXT NOT NULL,
                    read_date TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    pages_read INTEGER DEFAULT 0,
                    FOREIGN KEY (book_path) REFERENCES books (path) ON DELETE CASCADE
                )
            """)
            
            # 创建书签表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_path TEXT NOT NULL,
                    position TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    timestamp REAL NOT NULL,
                    created_date TEXT NOT NULL,
                    FOREIGN KEY (book_path) REFERENCES books (path) ON DELETE CASCADE
                )
            """)
            
            # 创建书签索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_book ON bookmarks(book_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_timestamp ON bookmarks(timestamp)")
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_add_date ON books(add_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_last_read ON books(last_read_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_date ON reading_history(read_date)")
            
            conn.commit()
    
    def add_book(self, book: Book) -> bool:
        """
        添加书籍到数据库
        
        Args:
            book: 书籍对象
            
        Returns:
            bool: 添加是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO books 
                    (path, title, author, format, add_date, last_read_date, reading_progress, total_pages, word_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    book.path,
                    book.title,
                    book.author,
                    book.format,
                    book.add_date,
                    book.last_read_date,
                    book.reading_progress,
                    book.total_pages,
                    book.word_count,
                    json.dumps(book.to_dict())
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"添加书籍到数据库失败: {e}")
            return False
    
    def get_book(self, book_path: str) -> Optional[Book]:
        """
        从数据库获取书籍
        
        Args:
            book_path: 书籍路径
            
        Returns:
            Optional[Book]: 书籍对象，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM books WHERE path = ?", (book_path,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_book(row)
                return None
        except sqlite3.Error as e:
            logger.error(f"从数据库获取书籍失败: {e}")
            return None
    
    def get_all_books(self) -> List[Book]:
        """
        获取所有书籍
        
        Returns:
            List[Book]: 书籍列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM books ORDER BY add_date DESC")
                rows = cursor.fetchall()
                
                return [self._row_to_book(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取所有书籍失败: {e}")
            return []
    
    def update_book(self, book: Book) -> bool:
        """
        更新书籍信息
        
        Args:
            book: 书籍对象
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE books 
                    SET title = ?, author = ?, format = ?, last_read_date = ?, 
                        reading_progress = ?, total_pages = ?, word_count = ?, metadata = ?
                    WHERE path = ?
                """, (
                    book.title,
                    book.author,
                    book.format,
                    book.last_read_date,
                    book.reading_progress,
                    book.total_pages,
                    book.word_count,
                    json.dumps(book.to_dict()),
                    book.path
                ))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"更新书籍信息失败: {e}")
            return False
    
    def delete_book(self, book_path: str) -> bool:
        """
        删除书籍
        
        Args:
            book_path: 书籍路径
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM books WHERE path = ?", (book_path,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除书籍失败: {e}")
            return False
    
    def search_books(self, keyword: str, format: Optional[str] = None) -> List[Book]:
        """
        搜索书籍（按标题和作者）
        
        Args:
            keyword: 搜索关键词
            format: 可选，文件格式筛选
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                search_pattern = f"%{keyword}%"
                
                if format:
                    cursor.execute("""
                        SELECT * FROM books 
                        WHERE (title LIKE ? OR author LIKE ?) AND format = ?
                        ORDER BY add_date DESC
                    """, (search_pattern, search_pattern, format.lower()))
                else:
                    cursor.execute("""
                        SELECT * FROM books 
                        WHERE title LIKE ? OR author LIKE ?
                        ORDER BY add_date DESC
                    """, (search_pattern, search_pattern))
                    
                rows = cursor.fetchall()
                
                return [self._row_to_book(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"搜索书籍失败: {e}")
            return []
    
    def add_reading_record(self, book_path: str, duration: int, pages_read: int = 0) -> bool:
        """
        添加阅读记录
        
        Args:
            book_path: 书籍路径
            duration: 阅读时长（秒）
            pages_read: 阅读页数
            
        Returns:
            bool: 添加是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO reading_history (book_path, read_date, duration, pages_read)
                    VALUES (?, ?, ?, ?)
                """, (
                    book_path,
                    datetime.now().isoformat(),
                    duration,
                    pages_read
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"添加阅读记录失败: {e}")
            return False
    
    def get_reading_history(self, book_path: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取阅读历史记录
        
        Args:
            book_path: 可选，指定书籍路径
            limit: 返回的记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 阅读历史记录列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if book_path:
                    cursor.execute("""
                        SELECT * FROM reading_history 
                        WHERE book_path = ? 
                        ORDER BY read_date DESC 
                        LIMIT ?
                    """, (book_path, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM reading_history 
                        ORDER BY read_date DESC 
                        LIMIT ?
                    """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取阅读历史记录失败: {e}")
            return []
    
    def _row_to_book(self, row: sqlite3.Row) -> Book:
        """
        将数据库行转换为Book对象
        
        Args:
            row: 数据库行
            
        Returns:
            Book: 书籍对象
        """
        try:
            # 首先尝试从metadata字段恢复完整的书籍对象
            if row['metadata']:
                metadata = json.loads(row['metadata'])
                book = Book.from_dict(metadata)
                return book
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"从元数据恢复书籍失败，使用基本属性: {e}")
        
        # 如果元数据恢复失败，使用基本属性创建书籍对象
        book = Book(
            path=row['path'],
            title=row['title'],
            author=row['author']
        )
        
        # 设置其他属性
        book.format = row['format']
        
        # 日期字段保持为字符串格式
        book.add_date = row['add_date']
        book.last_read_date = row['last_read_date']
        
        book.reading_progress = row['reading_progress'] or 0
        book.total_pages = row['total_pages'] or 0
        book.word_count = row['word_count'] or 0
        
        return book

    def add_bookmark(self, book_path: str, position: str, note: str = "") -> bool:
        """
        添加书签
        
        Args:
            book_path: 书籍路径
            position: 书签位置
            note: 书签备注
            
        Returns:
            bool: 添加是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = time.time()
                created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute("""
                    INSERT INTO bookmarks (book_path, position, note, timestamp, created_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (book_path, position, note, timestamp, created_date))
                
                conn.commit()
                return cursor.lastrowid is not None
        except sqlite3.Error as e:
            logger.error(f"添加书签失败: {e}")
            return False

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """
        删除书签
        
        Args:
            bookmark_id: 书签ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除书签失败: {e}")
            return False

    def get_bookmarks(self, book_path: str) -> List[Dict[str, Any]]:
        """
        获取指定书籍的所有书签
        
        Args:
            book_path: 书籍路径
            
        Returns:
            List[Dict[str, Any]]: 书签列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM bookmarks 
                    WHERE book_path = ? 
                    ORDER BY timestamp DESC
                """, (book_path,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取书签失败: {e}")
            return []

    def get_all_bookmarks(self) -> List[Dict[str, Any]]:
        """
        获取所有书签
        
        Returns:
            List[Dict[str, Any]]: 书签列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bookmarks ORDER BY timestamp DESC")
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取所有书签失败: {e}")
            return []

    def update_bookmark_note(self, bookmark_id: int, note: str) -> bool:
        """
        更新书签备注
        
        Args:
            bookmark_id: 书签ID
            note: 新的备注内容
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bookmarks SET note = ? WHERE id = ?
                """, (note, bookmark_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"更新书签备注失败: {e}")
            return False