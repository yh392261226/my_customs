"""
全文搜索模块
"""

import os
import re
from typing import Dict, List, Tuple, Optional
import sqlite3

from dataclasses import dataclass

from src.utils.logger import get_logger
from src.utils.string_utils import find_match_positions, normalize_match_text

logger = get_logger(__name__)

# contentless 模式下 FTS5 不保存正文，搜索预览需回源读书籍文件，
# 每条预览都要读一次文件，因此限制生成条数以免大量磁盘 I/O 拖慢搜索。
_PREVIEW_LIMIT = 20
# 生成预览时最多读取的文件前缀（字节），避免大文件被整个读入内存
_MAX_PREVIEW_BYTES = 4 * 1024 * 1024
# 索引归一化规则版本：规则变化时清空旧索引，由后台任务按新规则重建
_INDEX_NORM_VERSION = "1"

_FTS_CREATE_SQL = """
    CREATE VIRTUAL TABLE {name}
    USING fts5(book_id UNINDEXED, content, position UNINDEXED,
               content='', contentless_delete=1, contentless_unindexed=1)
"""

@dataclass
class SearchResult:
    """搜索结果数据类"""
    book_id: str
    position: str  # 可以是页码、章节或位置
    preview: str    # 匹配内容的预览
    score: float    # 匹配分数

class SearchEngine:
    """全文搜索引擎"""
    
    def __init__(self, db_path: str):
        """
        初始化搜索引擎
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = os.path.expanduser(db_path)
        self._pending_migration = False
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库（只做轻量建表，重建索引交给后台任务）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 已索引书籍登记表：仅记录已建立全文索引的 book_id，用于判断
            # 哪些书尚未索引，避免每次启动重复索引。
            # 全文内容只保留一份（FTS5 表），不再额外保存原始内容副本，
            # 原先的 search_index 表与 FTS5 内容重复，会让数据库体积翻倍。
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_indexed_books (
                    book_id TEXT PRIMARY KEY
                )
            """)
            # FTS5 采用 contentless 模式：只保留倒排索引，不再保存正文原文副本。
            #   contentless_unindexed=1 —— 允许读取 book_id / position 两个 UNINDEXED 列；
            #   contentless_delete=1 —— 支持 DELETE，否则删除书籍/清空索引会静默失败。
            cursor.execute(_FTS_CREATE_SQL.format(name="search_content").replace(
                "CREATE VIRTUAL TABLE", "CREATE VIRTUAL TABLE IF NOT EXISTS", 1))
            cursor.execute("CREATE TABLE IF NOT EXISTS search_meta (key TEXT PRIMARY KEY, value TEXT)")
            row = cursor.execute(
                "SELECT value FROM search_meta WHERE key = 'norm_version'"
            ).fetchone()
            # 索引表可能非常大（本机 3 万条、库 10GB），DROP/DELETE 都可能耗时几十秒。
            # 这里只标记待迁移，由后台补索引任务执行，避免阻塞 UI 启动。
            self._pending_migration = row is None or row[0] != _INDEX_NORM_VERSION
            conn.commit()

    def has_pending_migration(self) -> bool:
        return self._pending_migration

    def apply_pending_migration(self) -> None:
        """在后台任务中重建索引（简繁/大小写规则升级时调用一次）。"""
        if not self._pending_migration:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS search_content")
            # contentless FTS5 中若存在名为 content 的列，SQLite 会留下
            # search_content_content 影子表，重建前需一并清掉。
            cursor.execute("DROP TABLE IF EXISTS search_content_content")
            cursor.execute(_FTS_CREATE_SQL.format(name="search_content"))
            cursor.execute("DELETE FROM search_indexed_books")
            cursor.execute(
                "INSERT OR REPLACE INTO search_meta (key, value) VALUES ('norm_version', ?)",
                (_INDEX_NORM_VERSION,),
            )
            conn.commit()
        self._pending_migration = False
        logger.info("全文索引已按新归一化规则重建，后台将重新索引书籍")
    
    def index_book(self, book_id: str, content: str, position: str) -> None:
        """
        索引书籍内容
        
        Args:
            book_id: 书籍ID
            content: 要索引的内容
            position: 内容位置(页码/章节等)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # FTS5 表对 book_id 没有唯一约束，INSERT OR REPLACE 永远不会覆盖旧记录、
            # 只会不断追加，重建索引时会让索引翻倍膨胀并使搜索结果重复。
            # 因此这里先清除该书已有索引，再重新写入。
            cursor.execute("DELETE FROM search_content WHERE book_id = ?", (book_id,))
            # 全文内容只写入 FTS5 索引表（搜索实际只查询该表）
            cursor.execute("""
                INSERT INTO search_content 
                VALUES (?, ?, ?)
            """, (book_id, normalize_match_text(content or ""), position))
            # 仅登记已索引状态，开销极小
            cursor.execute("""
                INSERT OR REPLACE INTO search_indexed_books (book_id) VALUES (?)
            """, (book_id,))
            conn.commit()
    
    def get_indexed_book_ids(self) -> set:
        """
        返回已建立全文索引的 book_id 集合
        
        Returns:
            set: 已索引的 book_id 集合
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT book_id FROM search_indexed_books")
                return {row[0] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"获取已索引书籍列表失败: {e}")
            return set()
    
    def is_book_indexed(self, book_id: str) -> bool:
        """
        判断指定书籍是否已建立全文索引
        
        Args:
            book_id: 书籍ID（即书籍路径）
            
        Returns:
            bool: 是否已索引
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM search_indexed_books WHERE book_id = ? LIMIT 1", (book_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"检查书籍索引状态失败: {e}")
            return False
    
    def clear_index(self) -> None:
        """清空全部全文搜索索引（用于重建索引）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_indexed_books")
            cursor.execute("DELETE FROM search_content")
            conn.commit()
    
    def search(self, query: str, book_id: Optional[str] = None) -> List[SearchResult]:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            book_id: 可选，限制搜索的书籍ID
            
        Returns:
            搜索结果列表
        """
        # 验证和清理查询字符串
        if not query or not query.strip():
            return []
            
        # 与索引侧使用同一套归一化（繁简/全半角/大小写），再清理 FTS 特殊字符
        cleaned_query = self._clean_search_query(normalize_match_text(query))
        if not cleaned_query:
            return []
            
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if book_id:
                    cursor.execute("""
                        SELECT book_id, position, bm25(search_content) as score
                        FROM search_content
                        WHERE content MATCH ? AND book_id = ?
                        ORDER BY score
                        LIMIT 100
                    """, (cleaned_query, book_id))
                else:
                    cursor.execute("""
                        SELECT book_id, position, bm25(search_content) as score
                        FROM search_content
                        WHERE content MATCH ?
                        ORDER BY score
                        LIMIT 100
                    """, (cleaned_query,))
                
                rows = cursor.fetchall()
            
            # contentless 模式不保存正文，snippet() 不可用，
            # 预览改为按需从书籍文件（数据源头）生成，且只为前若干条生成。
            for idx, row in enumerate(rows):
                preview = ""
                if idx < _PREVIEW_LIMIT:
                    preview = self.make_preview(row['book_id'], cleaned_query)
                results.append(SearchResult(
                    book_id=row['book_id'],
                    position=row['position'],
                    preview=preview,
                    score=row['score']
                ))
        except sqlite3.Error as e:
            logger.error(f"搜索执行失败: {e}")
            return []
        
        return results
    
    def make_preview(self, book_id: str, query: str, radius: int = 60) -> str:
        """
        从书籍原文件中定位关键词，生成带高亮的预览片段
        
        contentless 模式下 FTS5 不保存正文，snippet() 无法使用，
        因此回源到书籍文件本身读取一小段来生成预览。
        
        Args:
            book_id: 书籍ID（即书籍文件路径）
            query: 搜索关键词
            radius: 关键词前后保留的字符数
            
        Returns:
            str: 预览片段；文件不存在或读取失败时返回空字符串
        """
        try:
            if not book_id or not os.path.exists(book_id):
                return ""
            with open(book_id, 'rb') as f:
                raw = f.read(_MAX_PREVIEW_BYTES)
            
            text = None
            for encoding in ('utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'big5'):
                try:
                    text = raw.decode(encoding)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            if text is None:
                text = raw.decode('utf-8', errors='ignore')
            
            # 折叠换行，避免预览里出现大段空白
            flat = text.replace('\r', ' ').replace('\n', ' ')
            matches = find_match_positions(flat, query)
            if not matches:
                # 关键词不在已读取的前缀中，退化为返回文件开头片段
                return flat[:radius * 2].strip()
            
            pos, hit_end, matched_text = matches[0]
            start = max(0, pos - radius)
            end = min(len(flat), hit_end + radius)
            body = (
                flat[start:pos] + f"<b>{matched_text}</b>" + flat[hit_end:end]
            ).strip()
            return ('...' if start > 0 else '') + body + ('...' if end < len(flat) else '')
        except Exception as e:
            logger.debug(f"生成搜索预览失败 {book_id}: {e}")
            return ""
    
    def remove_book(self, book_id: str) -> None:
        """
        从索引中移除书籍
        
        Args:
            book_id: 要移除的书籍ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_indexed_books WHERE book_id = ?", (book_id,))
            cursor.execute("DELETE FROM search_content WHERE book_id = ?", (book_id,))
            conn.commit()
    
    def _clean_search_query(self, query: str) -> str:
        """
        清理搜索查询字符串，移除可能导致SQL错误的特殊字符
        
        Args:
            query: 原始查询字符串
            
        Returns:
            清理后的查询字符串
        """
        # 移除 SQL/FTS5 特殊字符（含归一化后可能出现的方括号）
        cleaned = re.sub(r'[;"\'\\[\\]]', '', query)
        # 移除首尾空格
        cleaned = cleaned.strip()
        # 确保查询不为空
        return cleaned if cleaned else ""