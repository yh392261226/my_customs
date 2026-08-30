"""
全文搜索模块
"""

import os
import re
from typing import Dict, List, Tuple, Optional
import sqlite3

from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger(__name__)

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
        self._init_db()
    
    def _init_db(self) -> None:
        """初始化数据库"""
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
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS search_content 
                USING fts5(book_id, content, position)
            """)
            conn.commit()
    
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
            # 全文内容只写入 FTS5 索引表（搜索实际只查询该表）
            cursor.execute("""
                INSERT OR REPLACE INTO search_content 
                VALUES (?, ?, ?)
            """, (book_id, content, position))
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
            
        # 清理查询字符串，移除可能导致SQL错误的特殊字符
        cleaned_query = self._clean_search_query(query)
        if not cleaned_query:
            return []
            
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if book_id:
                    cursor.execute("""
                        SELECT book_id, position, snippet(search_content, 2, '<b>', '</b>', '...', 20) as snippet, 
                               bm25(search_content) as score
                        FROM search_content
                        WHERE content MATCH ? AND book_id = ?
                        ORDER BY score
                        LIMIT 100
                    """, (cleaned_query, book_id))
                else:
                    cursor.execute("""
                        SELECT book_id, position, snippet(search_content, 2, '<b>', '</b>', '...', 20) as snippet, 
                               bm25(search_content) as score
                        FROM search_content
                        WHERE content MATCH ?
                        ORDER BY score
                        LIMIT 100
                    """, (cleaned_query,))
                
                for row in cursor:
                    results.append(SearchResult(
                        book_id=row['book_id'],
                        position=row['position'],
                        preview=row['snippet'],
                        score=row['score']
                    ))
        except sqlite3.Error as e:
            logger.error(f"搜索执行失败: {e}")
            return []
        
        return results
    
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
        # 移除SQL注入风险的特殊字符
        cleaned = re.sub(r'[;"\'\\]', '', query)
        # 移除首尾空格
        cleaned = cleaned.strip()
        # 确保查询不为空
        return cleaned if cleaned else ""