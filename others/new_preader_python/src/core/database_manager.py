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

# 拼音转换工具
try:
    from pypinyin import pinyin, Style
    PY_PINYIN_AVAILABLE = True
except ImportError:
    PY_PINYIN_AVAILABLE = False
    logger.warning("pypinyin库未安装，拼音功能将不可用")

def convert_to_pinyin(text: str) -> str:
    """
    将中文转换为拼音
    
    Args:
        text: 中文字符串
        
    Returns:
        str: 拼音字符串
    """
    if not PY_PINYIN_AVAILABLE:
        return ""
    
    try:
        # 使用普通风格，不带声调
        pinyin_list = pinyin(text, style=Style.NORMAL)
        return "".join([item[0] for item in pinyin_list if item])
    except Exception as e:
        logger.error(f"拼音转换失败: {e}")
        return ""

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
            
        # 确保数据库目录存在（如果是内存数据库则跳过）
        if self.db_path != ':memory:':
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
                    pinyin TEXT,
                    author TEXT NOT NULL,
                    format TEXT NOT NULL,
                    add_date TEXT NOT NULL,
                    last_read_date TEXT,
                    reading_progress REAL DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    word_count INTEGER DEFAULT 0,
                    tags TEXT,
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
            
            # 检查并添加pinyin列（如果不存在）
            cursor.execute("PRAGMA table_info(books)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'pinyin' not in columns:
                cursor.execute("ALTER TABLE books ADD COLUMN pinyin TEXT")
            
            # 检查并添加tags列（如果不存在）
            if 'tags' not in columns:
                cursor.execute("ALTER TABLE books ADD COLUMN tags TEXT")
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_pinyin ON books(pinyin)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_add_date ON books(add_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_last_read ON books(last_read_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_date ON reading_history(read_date)")
            
            # 创建代理设置表（支持多条记录）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS proxy_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL DEFAULT '默认代理',
                    enabled BOOLEAN NOT NULL DEFAULT 0,
                    type TEXT NOT NULL DEFAULT 'HTTP',
                    host TEXT NOT NULL DEFAULT '127.0.0.1',
                    port TEXT NOT NULL DEFAULT '7890',
                    username TEXT DEFAULT '',
                    password TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 检查并添加缺失的字段
            cursor.execute("PRAGMA table_info(proxy_settings)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 如果缺少name字段，则添加
            if 'name' not in columns:
                cursor.execute("ALTER TABLE proxy_settings ADD COLUMN name TEXT NOT NULL DEFAULT '默认代理'")
            
            # 如果缺少created_at字段，则添加
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE proxy_settings ADD COLUMN created_at TEXT NOT NULL DEFAULT '2024-01-01T00:00:00'")
            
            # 创建书籍网站表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS novel_sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    storage_folder TEXT NOT NULL,
                    proxy_enabled BOOLEAN NOT NULL DEFAULT 0,
                    parser TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 创建爬取历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crawl_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    novel_id TEXT NOT NULL,
                    novel_title TEXT NOT NULL,
                    crawl_time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    file_path TEXT,
                    error_message TEXT,
                    FOREIGN KEY (site_id) REFERENCES novel_sites (id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_novel_sites_name ON novel_sites(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_novel_sites_url ON novel_sites(url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_crawl_history_site_id ON crawl_history(site_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_crawl_history_novel_id ON crawl_history(novel_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_crawl_history_crawl_time ON crawl_history(crawl_time)")
            
             # 创建书籍网站备注表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS novel_site_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL UNIQUE,
                    note_content TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (site_id) REFERENCES novel_sites (id) ON DELETE CASCADE
                )
            """)
            
            # 创建备注表索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_novel_site_notes_site_id ON novel_site_notes(site_id)")

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
            # 生成书名拼音
            pinyin_text = convert_to_pinyin(book.title) if book.title else ""
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO books 
                    (path, title, pinyin, author, format, add_date, last_read_date, reading_progress, total_pages, word_count, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    book.path,
                    book.title,
                    pinyin_text,
                    book.author,
                    book.format,
                    book.add_date,
                    book.last_read_date,
                    book.reading_progress,
                    book.total_pages,
                    book.word_count,
                    book.tags if book.tags else "",  # 直接使用字符串
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
                cursor.execute("SELECT * FROM books ORDER BY pinyin ASC")
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
            # 生成书名拼音
            pinyin_text = convert_to_pinyin(book.title) if book.title else ""
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE books 
                    SET title = ?, pinyin = ?, author = ?, format = ?, last_read_date = ?, 
                        reading_progress = ?, total_pages = ?, word_count = ?, tags = ?, metadata = ?
                    WHERE path = ?
                """, (
                    book.title,
                    pinyin_text,
                    book.author,
                    book.format,
                    book.last_read_date,
                    book.reading_progress,
                    book.total_pages,
                    book.word_count,
                    book.tags if book.tags else "",
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
        搜索书籍（按标题、拼音、作者和标签）
        
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
                        WHERE (title LIKE ? OR pinyin LIKE ? OR author LIKE ? OR tags LIKE ?) 
                              AND format = ?
                        ORDER BY add_date DESC
                    """, (search_pattern, search_pattern, search_pattern, search_pattern, 
                          format.lower()))
                else:
                    cursor.execute("""
                        SELECT * FROM books 
                        WHERE title LIKE ? OR pinyin LIKE ? OR author LIKE ? OR tags LIKE ?
                        ORDER BY add_date DESC
                    """, (search_pattern, search_pattern, search_pattern, search_pattern))
                    
                rows = cursor.fetchall()
                
                return [self._row_to_book(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"搜索书籍失败: {e}")
            return []
    
    def get_sorted_books(self, sort_key: str, reverse: bool = False) -> List[Book]:
        """
        获取排序后的书籍列表（使用数据库排序）
        
        Args:
            sort_key: 排序键，可选值为"title", "author", "add_date", "last_read_date", "progress"
            reverse: 是否倒序
            
        Returns:
            List[Book]: 排序后的书籍列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建排序SQL
                order_by_clause = self._build_order_by_clause(sort_key, reverse)
                
                cursor.execute(f"SELECT * FROM books {order_by_clause}")
                rows = cursor.fetchall()
                
                return [self._row_to_book(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取排序书籍失败: {e}")
            return []
    
    def _build_order_by_clause(self, sort_key: str, reverse: bool) -> str:
        """
        构建ORDER BY子句
        
        Args:
            sort_key: 排序键
            reverse: 是否倒序
            
        Returns:
            str: ORDER BY子句
        """
        # 字段映射
        field_mapping = {
            "title": "pinyin",  # 按书名排序时使用拼音字段
            "author": "author", 
            "add_date": "add_date",
            "last_read_date": "last_read_date",
            "progress": "reading_progress"
        }
        
        # 默认排序字段
        field = field_mapping.get(sort_key, "add_date")
        
        # 排序方向
        direction = "DESC" if reverse else "ASC"
        
        # 特殊处理：对于title，如果pinyin字段为空，则使用title字段
        if sort_key == "title":
            return f"ORDER BY CASE WHEN {field} IS NULL OR {field} = '' THEN title ELSE {field} END {direction}"
        
        # 特殊处理：对于last_read_date，NULL值排在最后
        if sort_key == "last_read_date":
            return f"ORDER BY CASE WHEN {field} IS NULL THEN 1 ELSE 0 END, {field} {direction}"
        
        # 特殊处理：对于progress，NULL值排在最后
        if sort_key == "progress":
            return f"ORDER BY CASE WHEN {field} IS NULL THEN 1 ELSE 0 END, {field} {direction}"
        
        return f"ORDER BY {field} {direction}"
    
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
        pinyin_value = row['pinyin'] if 'pinyin' in row else None
        book = Book(
            path=row['path'],
            title=row['title'],
            author=row['author'],
            pinyin=pinyin_value
        )
        
        # 设置其他属性
        book.format = row['format']
        
        # 日期字段保持为字符串格式
        book.add_date = row['add_date']
        book.last_read_date = row['last_read_date']
        
        book.reading_progress = row['reading_progress'] or 0
        book.total_pages = row['total_pages'] or 0
        book.word_count = row['word_count'] or 0
        
        # 设置拼音字段（如果存在）
        if 'pinyin' in row:
            book.pinyin = row['pinyin']
        
        # 设置标签字段（如果存在）
        if 'tags' in row and row['tags']:
            try:
                # 从逗号分隔的字符串解析标签
                tags_data = row['tags'].split(",") if row['tags'] else []
                book.tags = set(tags_data) if tags_data else set()
            except Exception:
                book.tags = set()
        
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

    # 代理设置相关方法（支持多条记录）
    def save_proxy_settings(self, settings: Dict[str, Any]) -> bool:
        """
        保存代理设置（兼容旧版本，只保存一条记录）
        
        Args:
            settings: 代理设置字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                updated_at = datetime.now().isoformat()
                created_at = datetime.now().isoformat()
                
                # 先删除现有设置（只保留一条记录）
                cursor.execute("DELETE FROM proxy_settings")
                
                cursor.execute("""
                    INSERT INTO proxy_settings 
                    (name, enabled, type, host, port, username, password, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    settings.get("name", "默认代理"),
                    settings.get("enabled", False),
                    settings.get("type", "HTTP"),
                    settings.get("host", "127.0.0.1"),
                    settings.get("port", "7890"),
                    settings.get("username", ""),
                    settings.get("password", ""),
                    created_at,
                    updated_at
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"保存代理设置失败: {e}")
            return False

    def get_proxy_settings(self) -> Dict[str, Any]:
        """
        获取代理设置（兼容旧版本，返回第一条记录）
        
        Returns:
            Dict[str, Any]: 代理设置字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM proxy_settings ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                
                if row:
                    return {
                        "id": row["id"],
                        "name": row["name"],
                        "enabled": bool(row["enabled"]),
                        "type": row["type"],
                        "host": row["host"],
                        "port": row["port"],
                        "username": row["username"],
                        "password": row["password"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"]
                    }
                else:
                    # 返回默认设置
                    return {
                        "id": 0,
                        "name": "默认代理",
                        "enabled": False,
                        "type": "HTTP",
                        "host": "127.0.0.1",
                        "port": "7890",
                        "username": "",
                        "password": "",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
        except sqlite3.Error as e:
            logger.error(f"获取代理设置失败: {e}")
            return {
                "id": 0,
                "name": "默认代理",
                "enabled": False,
                "type": "HTTP",
                "host": "127.0.0.1",
                "port": "7890",
                "username": "",
                "password": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
    
    def get_all_proxy_settings(self) -> List[Dict[str, Any]]:
        """
        获取所有代理设置
        
        Returns:
            List[Dict[str, Any]]: 代理设置列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM proxy_settings ORDER BY name")
                rows = cursor.fetchall()
                
                # 确保每个代理设置都有name字段
                proxy_list = []
                for row in rows:
                    proxy_data = dict(row)
                    # 如果name字段为空，设置默认值
                    if not proxy_data.get('name'):
                        proxy_data['name'] = f"代理{proxy_data.get('id', '')}"
                    proxy_list.append(proxy_data)
                
                return proxy_list
        except sqlite3.Error as e:
            logger.error(f"获取所有代理设置失败: {e}")
            return []
    
    def add_proxy_setting(self, proxy_data: Dict[str, Any]) -> bool:
        """
        添加代理设置
        
        Args:
            proxy_data: 代理设置数据
            
        Returns:
            bool: 添加是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                created_at = datetime.now().isoformat()
                updated_at = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO proxy_settings 
                    (name, enabled, type, host, port, username, password, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    proxy_data.get("name", "新代理"),
                    proxy_data.get("enabled", False),
                    proxy_data.get("type", "HTTP"),
                    proxy_data.get("host", "127.0.0.1"),
                    proxy_data.get("port", "7890"),
                    proxy_data.get("username", ""),
                    proxy_data.get("password", ""),
                    created_at,
                    updated_at
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"添加代理设置失败: {e}")
            return False
    
    def update_proxy_setting(self, proxy_id: int, proxy_data: Dict[str, Any]) -> bool:
        """
        更新代理设置
        
        Args:
            proxy_id: 代理ID
            proxy_data: 代理设置数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                updated_at = datetime.now().isoformat()
                
                cursor.execute("""
                    UPDATE proxy_settings 
                    SET name = ?, enabled = ?, type = ?, host = ?, port = ?, 
                        username = ?, password = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    proxy_data.get("name", "新代理"),
                    proxy_data.get("enabled", False),
                    proxy_data.get("type", "HTTP"),
                    proxy_data.get("host", "127.0.0.1"),
                    proxy_data.get("port", "7890"),
                    proxy_data.get("username", ""),
                    proxy_data.get("password", ""),
                    updated_at,
                    proxy_id
                ))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"更新代理设置失败: {e}")
            return False
    
    def delete_proxy_setting(self, proxy_id: int) -> bool:
        """
        删除代理设置
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM proxy_settings WHERE id = ?", (proxy_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除代理设置失败: {e}")
            return False
    
    def enable_proxy_setting(self, proxy_id: int) -> bool:
        """
        启用代理设置（同时禁用其他所有代理）
        
        Args:
            proxy_id: 代理ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                updated_at = datetime.now().isoformat()
                
                # 禁用所有代理
                cursor.execute("UPDATE proxy_settings SET enabled = 0, updated_at = ?", (updated_at,))
                
                # 启用指定代理
                cursor.execute("UPDATE proxy_settings SET enabled = 1, updated_at = ? WHERE id = ?", (updated_at, proxy_id))
                
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"启用代理设置失败: {e}")
            return False
    
    def get_enabled_proxy(self) -> Optional[Dict[str, Any]]:
        """
        获取当前启用的代理设置
        
        Returns:
            Optional[Dict[str, Any]]: 启用的代理设置，如果没有则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM proxy_settings WHERE enabled = 1 LIMIT 1")
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
        except sqlite3.Error as e:
            logger.error(f"获取启用的代理设置失败: {e}")
            return None

    # 书籍网站管理相关方法
    def save_novel_site(self, site_data: Dict[str, Any]) -> bool:
        """
        保存书籍网站配置
        
        Args:
            site_data: 网站配置字典
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                if "id" in site_data and site_data["id"]:
                    # 更新现有网站
                    cursor.execute("""
                        UPDATE novel_sites 
                        SET name = ?, url = ?, storage_folder = ?, proxy_enabled = ?, parser = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        site_data["name"],
                        site_data["url"],
                        site_data["storage_folder"],
                        site_data["proxy_enabled"],
                        site_data["parser"],
                        now,
                        site_data["id"]
                    ))
                else:
                    # 插入新网站
                    cursor.execute("""
                        INSERT INTO novel_sites 
                        (name, url, storage_folder, proxy_enabled, parser, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        site_data["name"],
                        site_data["url"],
                        site_data["storage_folder"],
                        site_data["proxy_enabled"],
                        site_data["parser"],
                        now,
                        now
                    ))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"保存书籍网站配置失败: {e}")
            return False

    def get_novel_sites(self) -> List[Dict[str, Any]]:
        """
        获取所有书籍网站配置
        
        Returns:
            List[Dict[str, Any]]: 网站配置列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM novel_sites ORDER BY name")
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取书籍网站配置失败: {e}")
            return []

    def delete_novel_site(self, site_id: int) -> bool:
        """
        删除书籍网站配置
        
        Args:
            site_id: 网站ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM novel_sites WHERE id = ?", (site_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除书籍网站配置失败: {e}")
            return False

    def delete_novel_site_by_id(self, site_id: int) -> bool:
        """
        根据ID删除书籍网站配置（别名方法）
        
        Args:
            site_id: 网站ID
            
        Returns:
            bool: 删除是否成功
        """
        return self.delete_novel_site(site_id)

    def get_novel_site_by_id(self, site_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取书籍网站配置
        
        Args:
            site_id: 网站ID
            
        Returns:
            Optional[Dict[str, Any]]: 网站配置字典，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM novel_sites WHERE id = ?", (site_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
        except sqlite3.Error as e:
            logger.error(f"根据ID获取书籍网站配置失败: {e}")
            return None

    # 爬取历史记录相关方法
    def add_crawl_history(self, site_id: int, novel_id: str, novel_title: str, 
                         status: str, file_path: Optional[str] = None, 
                         error_message: Optional[str] = None) -> bool:
        """
        添加爬取历史记录
        
        Args:
            site_id: 网站ID
            novel_id: 小说ID
            novel_title: 小说标题
            status: 爬取状态（success/failed）
            file_path: 文件路径（成功时）
            error_message: 错误信息（失败时）
            
        Returns:
            bool: 添加是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                crawl_time = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO crawl_history 
                    (site_id, novel_id, novel_title, crawl_time, status, file_path, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    site_id,
                    novel_id,
                    novel_title,
                    crawl_time,
                    status,
                    file_path,
                    error_message
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"添加爬取历史记录失败: {e}")
            return False

    def get_crawl_history_by_site(self, site_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取指定网站的爬取历史记录
        
        Args:
            site_id: 网站ID
            limit: 返回的记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 爬取历史记录列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM crawl_history 
                    WHERE site_id = ? 
                    ORDER BY crawl_time DESC 
                    LIMIT ?
                """, (site_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取爬取历史记录失败: {e}")
            return []

    def get_crawl_history_by_novel_id(self, site_id: int, novel_id: str) -> List[Dict[str, Any]]:
        """
        根据小说ID获取爬取历史记录
        
        Args:
            site_id: 网站ID
            novel_id: 小说ID
            
        Returns:
            List[Dict[str, Any]]: 爬取历史记录列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM crawl_history 
                    WHERE site_id = ? AND novel_id = ? 
                    ORDER BY crawl_time DESC
                """, (site_id, novel_id))
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"根据小说ID获取爬取历史记录失败: {e}")
            return []

    def check_novel_exists(self, site_id: int, novel_id: str) -> bool:
        """
        检查小说是否已经下载过且文件存在
        
        Args:
            site_id: 网站ID
            novel_id: 小说ID
            
        Returns:
            bool: 如果小说已下载且文件存在则返回True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT file_path FROM crawl_history 
                    WHERE site_id = ? AND novel_id = ? AND status = 'success'
                    ORDER BY crawl_time DESC 
                    LIMIT 1
                """, (site_id, novel_id))
                row = cursor.fetchone()
                
                if row and row["file_path"]:
                    # 检查文件是否存在
                    return os.path.exists(row["file_path"])
                return False
        except sqlite3.Error as e:
            logger.error(f"检查小说是否存在失败: {e}")
            return False

    def delete_crawl_history(self, history_id: int) -> bool:
        """
        删除爬取历史记录
        
        Args:
            history_id: 历史记录ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM crawl_history WHERE id = ?", (history_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除爬取历史记录失败: {e}")
            return False
    
    # 书籍网站备注相关方法
    def save_novel_site_note(self, site_id: int, note_content: str) -> bool:
        """
        保存书籍网站备注
        
        Args:
            site_id: 网站ID
            note_content: 备注内容
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                
                # 使用INSERT OR REPLACE来确保每个网站只有一个备注
                cursor.execute("""
                    INSERT OR REPLACE INTO novel_site_notes 
                    (site_id, note_content, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    site_id,
                    note_content,
                    now,
                    now
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"保存书籍网站备注失败: {e}")
            return False

    def get_novel_site_note(self, site_id: int) -> Optional[str]:
        """
        获取书籍网站备注
        
        Args:
            site_id: 网站ID
            
        Returns:
            Optional[str]: 备注内容，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT note_content FROM novel_site_notes 
                    WHERE site_id = ?
                """, (site_id,))
                row = cursor.fetchone()
                
                if row:
                    return row[0]
                return None
        except sqlite3.Error as e:
            logger.error(f"获取书籍网站备注失败: {e}")
            return None

    def delete_novel_site_note(self, site_id: int) -> bool:
        """
        删除书籍网站备注
        
        Args:
            site_id: 网站ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM novel_site_notes WHERE site_id = ?", (site_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除书籍网站备注失败: {e}")
            return False