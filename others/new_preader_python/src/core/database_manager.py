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
    from pypinyin import pinyin, Style  # type: ignore[reportMissingImports]
    _PY_PINYIN_AVAILABLE = True
except Exception:
    _PY_PINYIN_AVAILABLE = False
    pinyin = None  # type: ignore[assignment]
    Style = None   # type: ignore[assignment]
    logger.warning("pypinyin库未安装，拼音功能将不可用")

def convert_to_pinyin(text: str) -> str:
    """
    将中文转换为拼音
    
    Args:
        text: 中文字符串
        
    Returns:
        str: 拼音字符串
    """
    if not _PY_PINYIN_AVAILABLE:
        return ""
    
    try:
        # 使用普通风格，不带声调
        pinyin_list = pinyin(text, style=Style.NORMAL)  # type: ignore
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
            config = ConfigManager.get_instance().get_config()
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
    
    def _add_column_if_not_exists(self, cursor: sqlite3.Cursor, table_name: str, column_name: str, 
                                  column_type: str, default_value: str = "") -> None:
        """
        如果列不存在则添加列
        
        Args:
            cursor: 数据库游标
            table_name: 表名
            column_name: 列名
            column_type: 列类型
            default_value: 默认值
        """
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        if column_name not in columns:
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value:
                alter_sql += f" DEFAULT {default_value}"
            cursor.execute(alter_sql)
            logger.info(f"已为{table_name}表添加{column_name}列")
    
    def _init_database(self) -> None:
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建书籍表（删除last_read_date、reading_progress、total_pages、word_count字段）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    path TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    pinyin TEXT,
                    author TEXT NOT NULL,
                    format TEXT NOT NULL,
                    add_date TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT,
                    file_size INTEGER DEFAULT 0  -- 新增文件大小字段，单位为字节
                )
            """)
            
            # 伪用户系统：用户、权限、归属表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    key TEXT PRIMARY KEY,
                    description TEXT DEFAULT ''
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_permissions (
                    user_id INTEGER NOT NULL,
                    perm_key TEXT NOT NULL,
                    allowed INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, perm_key),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (perm_key) REFERENCES permissions (key) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_books (
                    user_id INTEGER NOT NULL,
                    book_path TEXT NOT NULL,
                    PRIMARY KEY (user_id, book_path),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (book_path) REFERENCES books (path) ON DELETE CASCADE
                )
            """)
            # 完整权限预置（若不存在则插入）- 包含所有页面的按钮权限
            default_perms = [
                # 欢迎屏幕权限
                ('welcome.open_book', '欢迎屏幕.打开书籍'),
                ('welcome.browse_library', '欢迎屏幕.浏览书库'),
                ('welcome.get_books', '欢迎屏幕.获取书籍'),
                ('welcome.settings', '欢迎屏幕.打开设置'),
                ('welcome.statistics', '欢迎屏幕.打开统计'),
                ('welcome.help', '欢迎屏幕.打开帮助'),
                ('welcome.manage', '欢迎屏幕.管理用户'),
                ('welcome.exit', '欢迎屏幕.退出应用'),
                
                # 书架权限
                ('bookshelf.read', '书库.阅读书籍'),
                ('bookshelf.view_file', '书库.查看书籍文件'),
                ('bookshelf.delete_book', '书库.删除书籍'),
                ('bookshelf.add_book', '书库.添加书籍'),
                ('bookshelf.scan_directory', '书库.扫描目录添加书籍'),
                ('bookshelf.get_books', '书库.获取书籍页面'),
                ('bookshelf.search', '书库.搜索书籍'),
                ('bookshelf.sort', '书库.排序书籍'),
                ('bookshelf.batch_ops', '书库.批量操作书籍'),
                ('bookshelf.refresh', '书库.刷新书架'),
                
                # 文件资源管理器权限
                ('file_explorer.back', '文件资源管理器.返回上级目录'),
                ('file_explorer.go', '文件资源管理器.导航到路径'),
                ('file_explorer.home', '文件资源管理器.返回主目录'),
                ('file_explorer.select', '文件资源管理器.选择文件/目录'),
                ('file_explorer.cancel', '文件资源管理器.取消操作'),
                
                # 目录对话框权限
                ('directory_dialog.select', '目录对话框.选择目录'),
                ('directory_dialog.cancel', '目录对话框.取消操作'),
                
                # 文件选择器对话框权限
                ('file_chooser.select', '文件选择器对话框.选择文件'),
                ('file_chooser.cancel', '文件选择器对话框.取消操作'),
                ('file_chooser.add_file', '文件选择器对话框.添加文件'),
                
                # 获取书籍权限
                ('get_books.novel_sites', '获取书籍页面.小说网站管理'),
                ('get_books.proxy_settings', '获取书籍页面.代理设置'),
                ('get_books.back', '获取书籍页面.离开获取书籍'),
                
                # 设置权限
                ('settings.save', '设置中心.保存设置'),
                ('settings.cancel', '设置中心.取消设置'),
                ('settings.reset', '设置中心.重置设置'),
                ('settings.open', '设置中心.打开设置'),
                
                # 统计权限
                ('statistics.refresh', '统计页面.刷新统计'),
                ('statistics.export', '统计页面.导出统计'),
                ('statistics.reset', '统计页面.重置统计'),
                ('statistics.back', '统计页面.离开统计'),
                ('statistics.open', '统计页面.打开统计'),
                
                # 用户管理权限
                ('users.add_user', '用户管理.添加用户'),
                ('users.edit_user', '用户管理.编辑用户'),
                ('users.delete_user', '用户管理.删除用户'),
                ('users.set_permissions', '用户管理.设置权限'),
                ('users.view_permissions', '用户管理.查看权限'),
                ('users.back', '用户管理.离开管理用户与权限'),
                ('admin.manage_users', '用户管理.管理用户与权限'),
                
                # 登录权限
                ('login.login', '用户登录'),
                ('login.guest', '访客登录'),
                
                # 锁定屏幕权限
                ('lock.submit', '提交密码'),
                ('lock.cancel', '取消锁定'),
                
                # 爬虫权限
                ('crawler.open', '打开爬取管理页面'),
                ('crawler.run', '执行爬取任务'),
                
                # 书签权限
                ('bookmarks.add', '书签.添加书签'),
                ('bookmarks.edit', '书签.编辑书签'),
                ('bookmarks.delete', '书签.删除书签'),
                ('bookmarks.view', '书签.查看书签'),
                
                # 帮助权限
                ('help.open', '打开帮助中心'),
                ('help.back', '离开帮助中心'),
                
                # 老板键权限
                ('boss_key.activate', '激活老板键'),
                ('boss_key.deactivate', '取消老板键')
            ]
            for k, d in default_perms:
                cursor.execute("INSERT OR IGNORE INTO permissions (key, description) VALUES (?, ?)", (k, d))
            # 默认超级管理员账号：admin/admin
            try:
                cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
                row = cursor.fetchone()
                if not row:
                    cursor.execute(
                        "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                        ("admin", self._hash_password("admin"), "superadmin", datetime.now().isoformat())
                    )
                    # 获取新创建的admin用户ID
                    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
                    admin_row = cursor.fetchone()
                    if admin_row:
                        admin_id = admin_row[0]
                        # 为admin用户分配文件资源管理器相关权限
                        file_explorer_perms = [
                            'file_explorer.back', 'file_explorer.go', 'file_explorer.home',
                            'file_explorer.select', 'file_explorer.cancel'
                        ]
                        for perm in file_explorer_perms:
                            cursor.execute(
                                "INSERT OR REPLACE INTO user_permissions (user_id, perm_key, allowed) VALUES (?, ?, 1)",
                                (admin_id, perm)
                            )
                        
                        # 为admin用户分配对话框相关权限
                        dialog_perms = [
                            'directory_dialog.select', 'directory_dialog.cancel',
                            'file_chooser.select', 'file_chooser.cancel', 'file_chooser.add_file'
                        ]
                        for perm in dialog_perms:
                            cursor.execute(
                                "INSERT OR REPLACE INTO user_permissions (user_id, perm_key, allowed) VALUES (?, ?, 1)",
                                (admin_id, perm)
                            )
            except Exception as _e:
                logger.warning(f"创建默认超级管理员失败（可忽略）：{_e}")
            
            # 创建阅读历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reading_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_path TEXT NOT NULL,
                    read_date TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    pages_read INTEGER DEFAULT 0,
                    user_id INTEGER DEFAULT 0,
                    reading_progress REAL DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    word_count INTEGER DEFAULT 0,
                    metadata TEXT,
                    FOREIGN KEY (book_path) REFERENCES books (path) ON DELETE CASCADE
                )
            """)
            
            # 创建书籍元数据表（每本书+每个用户只有一个metadata记录）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS book_metadata (
                    book_path TEXT NOT NULL,
                    user_id INTEGER DEFAULT 0,
                    metadata TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (book_path, user_id),
                    FOREIGN KEY (book_path) REFERENCES books (path) ON DELETE CASCADE
                )
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_metadata_book_user ON book_metadata(book_path, user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_metadata_user ON book_metadata(user_id)")
            
            # 创建书签表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_path TEXT NOT NULL,
                    position TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    timestamp REAL NOT NULL,
                    created_date TEXT NOT NULL,
                    -- 新增：锚点字段（迁移时通过 PRAGMA+ALTER 添加）
                    anchor_text TEXT DEFAULT '',
                    anchor_hash TEXT DEFAULT '',
                    -- 新增：用户ID字段，支持多用户模式
                    user_id INTEGER DEFAULT 0,
                    FOREIGN KEY (book_path) REFERENCES books (path) ON DELETE CASCADE
                )
            """)
            
            # 创建书签索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_book ON bookmarks(book_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_timestamp ON bookmarks(timestamp)")
            # 迁移：检查并添加缺失的锚点列
            self._add_column_if_not_exists(cursor, "bookmarks", "anchor_text", "TEXT", "''")
            self._add_column_if_not_exists(cursor, "bookmarks", "anchor_hash", "TEXT", "''")
            
            # 检查并添加pinyin列（如果不存在）
            self._add_column_if_not_exists(cursor, "books", "pinyin", "TEXT")
            
            # 检查并添加tags列（如果不存在）
            self._add_column_if_not_exists(cursor, "books", "tags", "TEXT")
            
            # 检查并添加file_size列（如果不存在）
            self._add_column_if_not_exists(cursor, "books", "file_size", "INTEGER DEFAULT 0")
            
            # 检查并添加file_size列（如果不存在）
            self._add_column_if_not_exists(cursor, "books", "file_size", "INTEGER DEFAULT 0")
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_pinyin ON books(pinyin)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_add_date ON books(add_date)")
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
            self._add_column_if_not_exists(cursor, "proxy_settings", "name", "TEXT NOT NULL", "'默认代理'")
            self._add_column_if_not_exists(cursor, "proxy_settings", "created_at", "TEXT NOT NULL", "'2024-01-01T00:00:00'")

            # 插入代理数据（使用INSERT OR IGNORE避免重复）
            proxy_settings_data = [
                (1, '7892', 0, 'SOCKS5', '127.0.0.1', '7892', '', '', datetime.now().isoformat(), datetime.now().isoformat()),
                (2, '7890', 1, 'SOCKS5', '127.0.0.1', '7890', '', '', datetime.now().isoformat(), datetime.now().isoformat()),
                (3, '51837', 0, 'SOCKS5', '127.0.0.1', '51837', '', '', datetime.now().isoformat(), datetime.now().isoformat())
            ]
            
            for proxy_data in proxy_settings_data:
                cursor.execute(
                    "INSERT OR IGNORE INTO proxy_settings (id, name, enabled, type, host, port, username, password, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    proxy_data
                )
            
            # 创建书籍网站表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS novel_sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    storage_folder TEXT NOT NULL,
                    proxy_enabled BOOLEAN NOT NULL DEFAULT 0,
                    selectable_enabled BOOLEAN NOT NULL DEFAULT 1,
                    parser TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # 插入书籍网站表（使用INSERT OR IGNORE避免重复）
            novel_sites_data = [
                ('人妻小说网', 'https://www.renqixiaoshuo.net', '/Users/yanghao/Documents/novels/datas', 1, 1, 'renqixiaoshuo_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('龙腾小说网', 'https://www.87nb.com', '/Users/yanghao/Documents/novels/datas', 1, 1, '87nb_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('91PORNA', 'https://91porna.com/novels/new', '/Users/yanghao/Documents/novels/datas', 1, 1, '91porna_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345678901'),
                ('AAA成人小說', 'https://aaanovel.com', '/Users/yanghao/Documents/novels/datas/', 0, 0, 'aaanovel_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '2025/11/05/小说名'),
                ('色情小说网', 'https://www.book18.me', '/Users/yanghao/Documents/novels/datas/', 0, 0, 'book18_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '书籍名(长篇)或12345(短篇)'),
                ('禁忌书屋', 'https://www.cool18.com/bbs4/index.php', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'cool18_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345678'),
                ('成人小说网', 'https://crxs.me', '/Users/yanghao/Documents/novels/datas/', 0, 0, 'crxs_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '5fd28afaf29d8'),
                ('风月文学网', 'http://www.h528.com', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'h528_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('色情001', 'https://seqing001.com', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'seqing001_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '1234'),
                ('中文成人文學網', 'https://blog.xbookcn.com', '/Users/yanghao/Documents/novels/datas/', 0, 0, 'xbookcn_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '2022/01/blog-post_30'),
                ('小黄书XCHINA', 'http://xchina.co/', '/Users/yanghao/Documents/novels/datas/', 0, 0, 'xchina_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), ''),
                ('69文学网', 'https://www.69hnovel.com/erotic-novel.html', '/Users/yanghao/Documents/novels/datas/', 0, 0, '69hnovel_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), 'anime/article-8629'),
                ('TXTXi', 'https://www.txtxi.com/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'txtxi_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '123456'),
                ('不雅污书', 'https://www.buya6.xyz/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'buya6_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('撸撸色书', 'https://www.lulu6.xyz/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'lulu6_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('AA阅读', 'https://aaread.cc/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'aaread_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('都市小说网', 'https://comcom.cyou/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'comcom_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('肉肉阅读', 'https://xxread.net/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'xxread_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('夜色书阁', 'http://5l15cquy.yssg2.cfd/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'yssg_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345'),
                ('咪咕文学', 'https://74qyavudmbzu1.migu1.top/', '/Users/yanghao/Documents/novels/datas/', 0, 1, 'migu_v2', '🔞成人', datetime.now().isoformat(), datetime.now().isoformat(), '12345')
            ]
            
            for site_data in novel_sites_data:
                cursor.execute(
                    "INSERT OR IGNORE INTO novel_sites (name, url, storage_folder, proxy_enabled, selectable_enabled, parser, tags, created_at, updated_at, book_id_example) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    site_data
                )
            
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
            
            # 检查并添加novel_sites表的tags列（如果不存在）
            self._add_column_if_not_exists(cursor, "novel_sites", "tags", "TEXT", "''")
            
            # 检查并添加novel_sites表的selectable_enabled列（如果不存在）
            self._add_column_if_not_exists(cursor, "novel_sites", "selectable_enabled", "BOOLEAN NOT NULL", "1")
            
            # 检查并添加novel_sites表的book_id_example列（如果不存在）
            self._add_column_if_not_exists(cursor, "novel_sites", "book_id_example", "TEXT", "''")

            conn.commit()
    
    def _build_minimal_metadata(self, book: Book) -> str:
        """
        构建精简的metadata JSON字符串
        
        Args:
            book: 书籍对象
            
        Returns:
            str: metadata JSON字符串
        """
        minimal_metadata = {}
        
        # 存储章节信息（列表结构，适合存储在metadata中）
        if book.chapters:
            minimal_metadata['chapters'] = book.chapters
        
        # 存储书签信息（列表结构，适合存储在metadata中）
        if book.bookmarks:
            minimal_metadata['bookmarks'] = book.bookmarks
        
        # 存储锚点信息（用于跨分页纠偏）
        if book.anchor_text:
            minimal_metadata['anchor_text'] = book.anchor_text
        
        if book.anchor_hash:
            minimal_metadata['anchor_hash'] = book.anchor_hash
        
        # 存储文件不存在标记（布尔值，适合存储在metadata中）
        if book.file_not_found:
            minimal_metadata['file_not_found'] = book.file_not_found
        
        # 存储PDF密码（敏感信息，适合存储在metadata中）
        if book.password:
            minimal_metadata['password'] = book.password
        
        # 注意：文件大小现在有专门的file_size字段存储，不再在metadata中重复存储
        # 这样可以避免数据冗余和不一致的问题
        
        # 确保metadata不为空时进行序列化
        return json.dumps(minimal_metadata) if minimal_metadata else ""
    
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
            
            # 构建精简的metadata
            metadata_json = self._build_minimal_metadata(book)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO books 
                    (path, title, pinyin, author, format, add_date, tags, metadata, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    book.path,
                    book.title,
                    pinyin_text,
                    book.author,
                    book.format,
                    book.add_date,
                    book.tags if book.tags else "",  # 直接使用字符串
                    metadata_json,
                    book.file_size
                ))
                conn.commit()
                
                logger.info(f"书籍已添加到数据库: {book.title} (metadata大小: {len(metadata_json)} 字节)")
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
        获取所有书籍（不区分用户）
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
    
    def get_books_for_user(self, user_id: int) -> List[Book]:
        """
        获取某用户的书籍列表（根据 user_books 归属表）
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT b.* FROM books b
                    JOIN user_books ub ON ub.book_path = b.path
                    WHERE ub.user_id = ?
                    ORDER BY b.pinyin ASC
                """, (user_id,))
                rows = cursor.fetchall()
                return [self._row_to_book(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"按用户获取书籍失败: {e}")
            return []
    
    def update_book(self, book: Book, old_path: Optional[str] = None) -> bool:
        """
        更新书籍信息
        
        Args:
            book: 书籍对象
            old_path: 可选的原书籍路径，用于路径更新时的定位
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 生成书名拼音
            pinyin_text = convert_to_pinyin(book.title) if book.title else ""
            
            # 构建精简的metadata
            metadata_json = self._build_minimal_metadata(book)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 如果提供了旧路径，使用旧路径作为WHERE条件（用于路径更新）
                where_path = old_path if old_path is not None else book.path
                
                cursor.execute("""
                    UPDATE books 
                    SET title = ?, pinyin = ?, author = ?, format = ?, tags = ?, metadata = ?, file_size = ?
                    WHERE path = ?
                """, (
                    book.title,
                    pinyin_text,
                    book.author,
                    book.format,
                    book.tags if book.tags else "",
                    metadata_json,
                    book.file_size,
                    where_path
                ))
                conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"书籍信息已更新: {book.title} (metadata大小: {len(metadata_json)} 字节)")
                
                return success
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
            keyword: 搜索关键词（支持英文逗号分割多个关键词）
            format: 可选，文件格式筛选
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 支持使用英文逗号分割多个关键词
                keywords = [k.strip() for k in keyword.split(',') if k.strip()]
                
                if not keywords:
                    # 如果没有有效关键词，返回空列表
                    return []
                
                # 构建SQL查询条件
                conditions = []
                params = []
                
                # 为每个关键词构建搜索条件
                for k in keywords:
                    search_pattern = f"%{k}%"
                    # 每个关键词在标题、拼音、作者、标签中搜索
                    condition = "(title LIKE ? OR pinyin LIKE ? OR author LIKE ? OR tags LIKE ?)"
                    conditions.append(condition)
                    params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
                
                # 组合所有条件（OR关系）
                where_clause = " OR ".join(conditions)
                
                if format:
                    sql = f"""
                        SELECT * FROM books 
                        WHERE ({where_clause}) AND format = ?
                        ORDER BY add_date DESC
                    """
                    params.append(format.lower())
                else:
                    sql = f"""
                        SELECT * FROM books 
                        WHERE {where_clause}
                        ORDER BY add_date DESC
                    """
                
                cursor.execute(sql, params)
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
    
    def add_reading_record(self, book_path: str, duration: int, pages_read: int = 0, 
                          user_id: Optional[int] = None) -> bool:
        """
        添加阅读记录（已优化：不再包含metadata字段，metadata由专门的book_metadata表管理）
        
        Args:
            book_path: 书籍路径
            duration: 阅读时长（秒）
            pages_read: 阅读页数
            user_id: 用户ID，如果为None则使用默认值0
            
        Returns:
            bool: 添加是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 设置用户ID（多用户模式关闭时使用0）
                user_id_value = user_id if user_id is not None else 0
                
                # 获取当前时间
                current_time = datetime.now().isoformat()
                
                # 从新的book_metadata表获取阅读进度相关信息
                reading_progress = 0
                total_pages = 0
                word_count = 0
                
                # 尝试从book_metadata表获取最新的元数据
                metadata_json = self.get_book_metadata(book_path, user_id_value)
                if metadata_json:
                    try:
                        metadata_dict = json.loads(metadata_json)
                        reading_progress = metadata_dict.get('reading_progress', 0)
                        total_pages = metadata_dict.get('total_pages', 0)
                        word_count = metadata_dict.get('word_count', 0)
                    except (json.JSONDecodeError, KeyError):
                        # 如果解析失败，使用默认值
                        pass
                
                cursor.execute("""
                    INSERT INTO reading_history (book_path, read_date, duration, pages_read, 
                                                user_id, reading_progress, total_pages, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    book_path,
                    current_time,
                    duration,
                    pages_read,
                    user_id_value,
                    reading_progress,
                    total_pages,
                    word_count
                ))
                
                # 同时更新book_metadata表中的最后阅读时间
                # 从book_metadata表获取现有的元数据
                existing_metadata_json = self.get_book_metadata(book_path, user_id_value)
                existing_metadata = {}
                if existing_metadata_json:
                    try:
                        existing_metadata = json.loads(existing_metadata_json)
                    except json.JSONDecodeError:
                        pass
                
                # 更新最后阅读时间
                existing_metadata['last_read_date'] = current_time
                
                # 保存更新后的元数据
                updated_metadata_json = json.dumps(existing_metadata, ensure_ascii=False)
                cursor.execute("""
                    INSERT OR REPLACE INTO book_metadata (book_path, user_id, metadata, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (
                    book_path,
                    user_id_value,
                    updated_metadata_json,
                    current_time
                ))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"添加阅读记录失败: {e}")
            return False
    
    def get_reading_history(self, book_path: Optional[str] = None, limit: int = 100, 
                           user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取阅读历史记录
        
        Args:
            book_path: 可选，指定书籍路径
            limit: 返回的记录数量限制
            user_id: 可选，用户ID，如果为None则不按用户过滤
            
        Returns:
            List[Dict[str, Any]]: 阅读历史记录列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM reading_history"
                params = []
                
                # 构建查询条件
                conditions = []
                
                if book_path:
                    conditions.append("book_path = ?")
                    params.append(book_path)
                
                if user_id is not None and user_id > 0:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY read_date DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取阅读历史记录失败: {e}")
            return []

    def get_latest_reading_record(self, book_path: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        获取指定书籍的最新阅读记录
        
        Args:
            book_path: 书籍路径
            user_id: 可选，用户ID，如果为None则不按用户过滤
            
        Returns:
            Optional[Dict[str, Any]]: 最新的阅读记录，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM reading_history WHERE book_path = ?"
                params = [book_path]
                
                if user_id is not None and user_id > 0:
                    query += " AND user_id = ?"
                    params.append(str(user_id))
                
                query += " ORDER BY read_date DESC LIMIT 1"
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    record = dict(row)
                    # 将read_date作为last_read_date返回，保持接口兼容性
                    record['last_read_date'] = record.get('read_date')
                    return record
                return None
        except sqlite3.Error as e:
            logger.error(f"获取最新阅读记录失败: {e}")
            return None
    
    def _row_to_book(self, row: sqlite3.Row) -> Book:
        """
        将数据库行转换为Book对象
        
        Args:
            row: 数据库行
            
        Returns:
            Book: 书籍对象
        """
        # 优先使用独立字段创建书籍对象
        pinyin_value = row['pinyin'] if 'pinyin' in row else None
        
        # 创建基础书籍对象
        book = Book(
            path=row['path'],
            title=row['title'],
            author=row['author'],
            tags=row['tags'],
            pinyin=pinyin_value
        )
        
        # 设置格式字段
        book.format = row['format']
        
        # 设置日期字段
        book.add_date = row['add_date']
        
        # 设置文件大小字段
        if 'file_size' in row:
            book.file_size = row['file_size']
            book.size = book.file_size  # 保持兼容性
        
        # 设置文件大小字段
        if 'file_size' in row:
            book.file_size = row['file_size']
            book.size = book.file_size  # 保持兼容性
        
        # 注意：last_read_date、reading_progress、total_pages、word_count字段
        # 现在存储在reading_history表中，不在books表中
        # 这些字段将通过其他方法从reading_history表获取
        
        # 设置拼音字段（如果存在）
        if 'pinyin' in row:
            book.pinyin = row['pinyin'] or ""
        
        # 设置标签字段（如果存在）
        if 'tags' in row:
            book.tags = row['tags'] or ""
        
        # 只有在独立字段缺失或需要补充数据时，才使用metadata字段
        if row['metadata']:
            try:
                metadata = json.loads(row['metadata'])
                
                # 仅使用metadata字段补充缺失的数据
                # 只有在独立字段为空或无效时，才使用metadata中的对应字段
                if not book.title or book.title == "未知标题":
                    book.title = metadata.get('title', book.title)
                
                if not book.author or book.author == "未知作者":
                    book.author = metadata.get('author', book.author)
                
                if not book.pinyin:
                    book.pinyin = metadata.get('pinyin', book.pinyin)
                
                if not book.tags:
                    book.tags = metadata.get('tags', book.tags)
                
                # 补充其他可能缺失的字段（阅读相关字段已迁移到reading_history表）
                # reading_progress, total_pages, word_count 等字段应从reading_history表获取
                
                # 补充章节信息（如果不存在）
                if not book.chapters and 'chapters' in metadata:
                    book.chapters = metadata.get('chapters', [])
                
                # 补充书签信息（如果不存在）
                if not book.bookmarks and 'bookmarks' in metadata:
                    book.bookmarks = metadata.get('bookmarks', [])
                    
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"解析metadata字段失败，已使用独立字段: {e}")
        
        return book

    def add_bookmark(self, book_path: str, position: str, note: str = "", anchor_text: Optional[str] = None, anchor_hash: Optional[str] = None, user_id: Optional[int] = None) -> bool:
        """
        添加书签（支持锚点，可选）
        
        Args:
            book_path: 书籍路径
            position: 书签位置
            note: 书签备注
            user_id: 用户ID，如果为None则使用默认值0
            
        Returns:
            bool: 添加是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = time.time()
                created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 设置用户ID（多用户模式关闭时使用0）
                user_id_value = user_id if user_id is not None else 0
                
                # 兼容：如表结构已有锚点列则写入，否则写基础列
                cursor.execute("PRAGMA table_info(bookmarks)")
                bm_columns = [column[1] for column in cursor.fetchall()]
                if 'anchor_text' in bm_columns and 'anchor_hash' in bm_columns:
                    cursor.execute("""
                        INSERT INTO bookmarks (book_path, position, note, timestamp, created_date, anchor_text, anchor_hash, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (book_path, position, note, timestamp, created_date, anchor_text or "", anchor_hash or "", user_id_value))
                else:
                    cursor.execute("""
                        INSERT INTO bookmarks (book_path, position, note, timestamp, created_date, user_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (book_path, position, note, timestamp, created_date, user_id_value))
                
                conn.commit()
                return cursor.lastrowid is not None
        except sqlite3.Error as e:
            logger.error(f"添加书签失败: {e}")
            return False

    def delete_bookmark(self, bookmark_id: int, user_id: Optional[int] = None) -> bool:
        """
        删除书签
        
        Args:
            bookmark_id: 书签ID
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if user_id is not None and user_id > 0:
                    cursor.execute("DELETE FROM bookmarks WHERE id = ? AND user_id = ?", (bookmark_id, user_id))
                else:
                    cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
                
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除书签失败: {e}")
            return False

    def get_bookmarks(self, book_path: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定书籍的所有书签
        
        Args:
            book_path: 书籍路径
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            List[Dict[str, Any]]: 书签列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if user_id is not None and user_id > 0:
                    cursor.execute("""
                        SELECT * FROM bookmarks 
                        WHERE book_path = ? AND user_id = ?
                        ORDER BY timestamp DESC
                    """, (book_path, user_id))
                else:
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

    def get_all_bookmarks(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取所有书签
        
        Args:
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            List[Dict[str, Any]]: 书签列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if user_id is not None and user_id > 0:
                    cursor.execute("SELECT * FROM bookmarks WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
                else:
                    cursor.execute("SELECT * FROM bookmarks ORDER BY timestamp DESC")
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取所有书签失败: {e}")
            return []

    def update_bookmark_note(self, bookmark_id: int, note: str, user_id: Optional[int] = None) -> bool:
        """
        更新书签备注
        
        Args:
            bookmark_id: 书签ID
            note: 新的备注内容
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if user_id is not None and user_id > 0:
                    cursor.execute("""
                        UPDATE bookmarks SET note = ? WHERE id = ? AND user_id = ?
                    """, (note, bookmark_id, user_id))
                else:
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
                    record = dict(row)
                    # 将read_date作为last_read_date返回，保持接口兼容性
                    record['last_read_date'] = record.get('read_date')
                    return record
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
                        SET name = ?, url = ?, storage_folder = ?, proxy_enabled = ?, selectable_enabled = ?, parser = ?, tags = ?, book_id_example = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        site_data["name"],
                        site_data["url"],
                        site_data["storage_folder"],
                        site_data["proxy_enabled"],
                        site_data.get("selectable_enabled", True),
                        site_data["parser"],
                        site_data.get("tags", ""),
                        site_data.get("book_id_example", ""),
                        now,
                        site_data["id"]
                    ))
                else:
                    # 插入新网站
                    cursor.execute("""
                        INSERT INTO novel_sites 
                        (name, url, storage_folder, proxy_enabled, selectable_enabled, parser, tags, book_id_example, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        site_data["name"],
                        site_data["url"],
                        site_data["storage_folder"],
                        site_data["proxy_enabled"],
                        site_data.get("selectable_enabled", True),
                        site_data["parser"],
                        site_data.get("tags", ""),
                        site_data.get("book_id_example", ""),
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
                cursor.execute("SELECT * FROM novel_sites ORDER BY created_at")
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
                    record = dict(row)
                    # 将read_date作为last_read_date返回，保持接口兼容性
                    record['last_read_date'] = record.get('read_date')
                    return record
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

    # ===================== 伪用户系统 API =====================
    def _hash_password(self, password: str) -> str:
        import hashlib
        return hashlib.sha256(("newreader_salt_" + (password or "")).encode("utf-8")).hexdigest()

    def create_user(self, username: str, password: str, role: str = "user") -> Optional[int]:
        """创建用户；返回用户ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?)
                """, (username, self._hash_password(password), role, now))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"创建用户失败: {e}")
            return None

    def set_user_password(self, user_id: int, new_password: str) -> bool:
        """设置用户密码"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (self._hash_password(new_password), user_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"设置用户密码失败: {e}")
            return False

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """认证，成功返回用户字典"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    return None
                ok = (row["password_hash"] == self._hash_password(password))
                if not ok:
                    return None
                return {"id": row["id"], "username": row["username"], "role": row["role"]}
        except sqlite3.Error as e:
            logger.error(f"认证失败: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户ID获取用户信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return {"id": row["id"], "username": row["username"], "role": row["role"]}
        except sqlite3.Error as e:
            logger.error(f"获取用户信息失败: {e}")
            return None

    def set_user_permissions(self, user_id: int, perm_keys: List[str]) -> bool:
        """设置用户权限（覆盖式）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
                for key in perm_keys:
                    cursor.execute("INSERT OR REPLACE INTO user_permissions (user_id, perm_key, allowed) VALUES (?, ?, 1)", (user_id, key))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"设置用户权限失败: {e}")
            return False

    def _has_permission(self, perm_key: str) -> bool:
        """检查权限；超级管理拥有全部权限"""
        # 简化版本：检查当前用户是否有权限
        try:
            from src.utils.multi_user_manager import multi_user_manager
            
            # 如果多用户关闭，默认有所有权限
            if not multi_user_manager.is_multi_user_enabled():
                return True
                
            current_user = multi_user_manager.get_current_user()
            
            # 如果当前用户是超级管理员，有所有权限
            if current_user and current_user.get("role") == "super_admin":
                return True
                
            # 检查用户权限
            user_id = current_user.get("id") if current_user else 0
            role = current_user.get("role") if current_user else None
            return self.has_permission(user_id, perm_key, role)
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return True  # 出错时默认允许
    
    def has_permission(self, user_id: Optional[int], perm_key: str, role: Optional[str] = None) -> bool:
        """检查权限；超级管理拥有全部权限"""
        try:
            if role == "superadmin" or role == "super_admin":
                return True
            # 如果user_id为None或0，表示未登录用户，默认无权限
            if not user_id:
                return False
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT allowed FROM user_permissions WHERE user_id = ? AND perm_key = ?", (user_id, perm_key))
                row = cursor.fetchone()
                return bool(row and (row[0] == 1))
        except sqlite3.Error as e:
            logger.error(f"检查权限失败: {e}")
            return False

    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """
        获取所有权限的完整信息（包括key和description）
        
        Returns:
            List[Dict[str, Any]]: 权限列表，每个权限包含key和description
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT key, description FROM permissions ORDER BY key")
                rows = cursor.fetchall()
                return [dict(row) for row in rows if row]
        except sqlite3.Error as e:
            logger.error(f"获取所有权限失败: {e}")
            return []

    def assign_book_to_user(self, user_id: int, book_path: str) -> bool:
        """将书籍标注为该用户的书籍（不用于显示，仅过滤用）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO user_books (user_id, book_path) VALUES (?, ?)", (user_id, book_path))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"书籍归属用户失败: {e}")
            return False

    def get_user_permissions(self, user_id: int) -> List[str]:
        """
        获取用户的权限列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[str]: 用户拥有的权限键列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT perm_key FROM user_permissions 
                    WHERE user_id = ? AND allowed = 1
                """, (user_id,))
                rows = cursor.fetchall()
                return [row[0] for row in rows if row and row[0]]
        except sqlite3.Error as e:
            logger.error(f"获取用户权限失败: {e}")
            return []

    def update_bookmarks_path(self, old_path: str, new_path: str) -> bool:
        """
        更新书签表中的书籍路径引用
        
        Args:
            old_path: 原书籍路径
            new_path: 新书籍路径
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE bookmarks SET book_path = ? WHERE book_path = ?", (new_path, old_path))
                conn.commit()
                logger.info(f"更新书签表路径引用: {old_path} -> {new_path}")
                return True
        except sqlite3.Error as e:
            logger.error(f"更新书签表路径引用失败: {e}")
            return False

    def update_crawl_history_path(self, old_path: str, new_path: str) -> bool:
        """
        更新爬取历史表中的书籍路径引用和名称
        
        Args:
            old_path: 原书籍路径
            new_path: 新书籍路径
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # 从新路径中提取新的书籍名称（去掉目录路径和文件扩展名）
                new_title = os.path.splitext(os.path.basename(new_path))[0]
                
                # 更新文件路径和书籍名称
                cursor.execute("UPDATE crawl_history SET file_path = ?, novel_title = ? WHERE file_path = ?", 
                             (new_path, new_title, old_path))
                conn.commit()
                logger.info(f"更新爬取历史表路径引用和名称: {old_path} -> {new_path}, 新名称: {new_title}")
                return True
        except sqlite3.Error as e:
            logger.error(f"更新爬取历史表路径引用和名称失败: {e}")
            return False

    def update_reading_history_path(self, old_path: str, new_path: str) -> bool:
        """
        更新阅读历史表中的书籍路径引用
        
        Args:
            old_path: 原书籍路径
            new_path: 新书籍路径
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE reading_history SET book_path = ? WHERE book_path = ?", (new_path, old_path))
                conn.commit()
                logger.info(f"更新阅读历史表路径引用: {old_path} -> {new_path}")
                return True
        except sqlite3.Error as e:
            logger.error(f"更新阅读历史表路径引用失败: {e}")
            return False

    # ===================== 书籍元数据表相关方法 =====================
    def save_book_metadata(self, book_path: str, metadata: str, user_id: Optional[int] = None) -> bool:
        """
        保存书籍元数据到新表
        
        Args:
            book_path: 书籍路径
            metadata: 元数据JSON字符串
            user_id: 用户ID，如果为None则使用默认值0
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 设置用户ID（多用户模式关闭时使用0）
                user_id_value = user_id if user_id is not None else 0
                
                # 使用INSERT OR REPLACE来确保每个书籍+用户组合只有一个记录
                cursor.execute("""
                    INSERT OR REPLACE INTO book_metadata 
                    (book_path, user_id, metadata, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (book_path, user_id_value, metadata, last_updated))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"保存书籍元数据失败: {e}")
            return False

    def get_book_metadata(self, book_path: str, user_id: Optional[int] = None) -> Optional[str]:
        """
        获取书籍元数据
        
        Args:
            book_path: 书籍路径
            user_id: 用户ID，如果为None则使用默认值0
            
        Returns:
            Optional[str]: 元数据JSON字符串，如果不存在则返回None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 设置用户ID（多用户模式关闭时使用0）
                user_id_value = user_id if user_id is not None else 0
                
                cursor.execute("""
                    SELECT metadata FROM book_metadata 
                    WHERE book_path = ? AND user_id = ?
                """, (book_path, user_id_value))
                
                row = cursor.fetchone()
                if row:
                    return row[0]
                return None
        except sqlite3.Error as e:
            logger.error(f"获取书籍元数据失败: {e}")
            return None

    def delete_book_metadata(self, book_path: str, user_id: Optional[int] = None) -> bool:
        """
        删除书籍元数据
        
        Args:
            book_path: 书籍路径
            user_id: 用户ID，如果为None则使用默认值0
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 设置用户ID（多用户模式关闭时使用0）
                user_id_value = user_id if user_id is not None else 0
                
                cursor.execute("""
                    DELETE FROM book_metadata 
                    WHERE book_path = ? AND user_id = ?
                """, (book_path, user_id_value))
                
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"删除书籍元数据失败: {e}")
            return False

    def update_book_metadata_path(self, old_path: str, new_path: str) -> bool:
        """
        更新书籍元数据表中的书籍路径引用
        
        Args:
            old_path: 原书籍路径
            new_path: 新书籍路径
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE book_metadata SET book_path = ? WHERE book_path = ?", (new_path, old_path))
                conn.commit()
                logger.info(f"更新书籍元数据表路径引用: {old_path} -> {new_path}")
                return True
        except sqlite3.Error as e:
            logger.error(f"更新书籍元数据表路径引用失败: {e}")
            return False

    def migrate_reading_history_metadata(self) -> bool:
        """
        将现有reading_history表中的metadata迁移到新的book_metadata表
        
        Returns:
            bool: 迁移是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取所有有metadata的阅读记录
                cursor.execute("""
                    SELECT DISTINCT book_path, user_id, metadata 
                    FROM reading_history 
                    WHERE metadata IS NOT NULL AND metadata != ''
                """)
                
                rows = cursor.fetchall()
                migrated_count = 0
                
                for row in rows:
                    book_path, user_id, metadata = row
                    
                    # 迁移到新表
                    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("""
                        INSERT OR REPLACE INTO book_metadata 
                        (book_path, user_id, metadata, last_updated)
                        VALUES (?, ?, ?, ?)
                    """, (book_path, user_id or 0, metadata, last_updated))
                    
                    migrated_count += 1
                
                conn.commit()
                logger.info(f"成功迁移 {migrated_count} 条metadata记录到新表")
                return True
        except sqlite3.Error as e:
            logger.error(f"迁移metadata失败: {e}")
            return False

    def update_user_books_path(self, old_path: str, new_path: str) -> bool:
        """
        更新用户书籍关联表中的书籍路径引用
        
        Args:
            old_path: 原书籍路径
            new_path: 新书籍路径
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE user_books SET book_path = ? WHERE book_path = ?", (new_path, old_path))
                conn.commit()
                logger.info(f"更新用户书籍关联表路径引用: {old_path} -> {new_path}")
                return True
        except sqlite3.Error as e:
            logger.error(f"更新用户书籍关联表路径引用失败: {e}")
            return False

    def update_vocabulary_path(self, old_path: str, new_path: str) -> bool:
        """
        更新词汇表中的书籍路径引用
        
        Args:
            old_path: 原书籍路径
            new_path: 新书籍路径
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE vocabulary SET book_id = ? WHERE book_id = ?", (new_path, old_path))
                conn.commit()
                logger.info(f"更新词汇表路径引用: {old_path} -> {new_path}")
                return True
        except sqlite3.Error as e:
            logger.error(f"更新词汇表路径引用失败: {e}")
            return False