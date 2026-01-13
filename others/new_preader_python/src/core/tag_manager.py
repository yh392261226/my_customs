"""
标签管理器
用于管理书籍和书签的标签功能
"""

import json
import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager

logger = get_logger(__name__)

@dataclass
class Tag:
    """标签数据类"""
    id: Optional[int]
    name: str
    color: str = "#cccccc"  # 默认灰色
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class TagManager:
    """标签管理器"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化标签管理器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self._init_tags_table()
    
    def _init_tags_table(self):
        """初始化标签相关数据库表"""
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建标签表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#cccccc',
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 创建书籍标签关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS book_tags (
                    book_path TEXT NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (book_path, tag_id),
                    FOREIGN KEY (book_path) REFERENCES books (path) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            """)
            
            # 创建书签标签关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmark_tags (
                    bookmark_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (bookmark_id, tag_id),
                    FOREIGN KEY (bookmark_id) REFERENCES bookmarks (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_tags_book ON book_tags(book_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_tags_tag ON book_tags(tag_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmark_tags_bookmark ON bookmark_tags(bookmark_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookmark_tags_tag ON bookmark_tags(tag_id)")
            
            conn.commit()
    
    def create_tag(self, name: str, color: str = "#cccccc", description: str = "") -> Optional[Tag]:
        """
        创建新标签
        
        Args:
            name: 标签名称
            color: 标签颜色
            description: 标签描述
            
        Returns:
            创建的标签对象，如果已存在则返回None
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                created_at = datetime.now().isoformat()
                
                cursor.execute("""
                    INSERT INTO tags (name, color, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, color, description, created_at, created_at))
                
                tag_id = cursor.lastrowid
                conn.commit()
                
                return Tag(
                    id=tag_id,
                    name=name,
                    color=color,
                    description=description,
                    created_at=created_at,
                    updated_at=created_at
                )
        except Exception as e:
            logger.error(f"创建标签失败: {e}")
            return None
    
    def get_tag_by_id(self, tag_id: int) -> Optional[Tag]:
        """根据ID获取标签"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tags WHERE id = ?", (tag_id,))
                row = cursor.fetchone()
                
                if row:
                    return Tag(
                        id=row[0],
                        name=row[1],
                        color=row[2],
                        description=row[3],
                        created_at=row[4],
                        updated_at=row[5]
                    )
                return None
        except Exception as e:
            logger.error(f"获取标签失败: {e}")
            return None
    
    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        """根据名称获取标签"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
                row = cursor.fetchone()
                
                if row:
                    return Tag(
                        id=row[0],
                        name=row[1],
                        color=row[2],
                        description=row[3],
                        created_at=row[4],
                        updated_at=row[5]
                    )
                return None
        except Exception as e:
            logger.error(f"获取标签失败: {e}")
            return None
    
    def get_all_tags(self) -> List[Tag]:
        """获取所有标签"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tags ORDER BY name")
                rows = cursor.fetchall()
                
                return [
                    Tag(
                        id=row[0],
                        name=row[1],
                        color=row[2],
                        description=row[3],
                        created_at=row[4],
                        updated_at=row[5]
                    ) for row in rows
                ]
        except Exception as e:
            logger.error(f"获取所有标签失败: {e}")
            return []
    
    def update_tag(self, tag_id: int, name: str = None, color: str = None, 
                   description: str = None) -> bool:
        """
        更新标签信息
        
        Args:
            tag_id: 标签ID
            name: 新的标签名称
            color: 新的颜色
            description: 新的描述
            
        Returns:
            是否更新成功
        """
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if not updates:
                return True  # 没有更新内容，视为成功
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(tag_id)
            
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE tags SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新标签失败: {e}")
            return False
    
    def delete_tag(self, tag_id: int) -> bool:
        """
        删除标签（同时删除关联关系）
        
        Args:
            tag_id: 标签ID
            
        Returns:
            是否删除成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
                conn.commit()
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除标签失败: {e}")
            return False
    
    def add_tag_to_book(self, book_path: str, tag_id: int) -> bool:
        """
        为书籍添加标签
        
        Args:
            book_path: 书籍路径
            tag_id: 标签ID
            
        Returns:
            是否添加成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO book_tags (book_path, tag_id)
                    VALUES (?, ?)
                """, (book_path, tag_id))
                conn.commit()
                
                return True
        except Exception as e:
            logger.error(f"为书籍添加标签失败: {e}")
            return False
    
    def remove_tag_from_book(self, book_path: str, tag_id: int) -> bool:
        """
        从书籍移除标签
        
        Args:
            book_path: 书籍路径
            tag_id: 标签ID
            
        Returns:
            是否移除成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM book_tags
                    WHERE book_path = ? AND tag_id = ?
                """, (book_path, tag_id))
                conn.commit()
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"从书籍移除标签失败: {e}")
            return False
    
    def get_tags_for_book(self, book_path: str) -> List[Tag]:
        """获取书籍的所有标签"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.* FROM tags t
                    INNER JOIN book_tags bt ON t.id = bt.tag_id
                    WHERE bt.book_path = ?
                    ORDER BY t.name
                """, (book_path,))
                rows = cursor.fetchall()
                
                return [
                    Tag(
                        id=row[0],
                        name=row[1],
                        color=row[2],
                        description=row[3],
                        created_at=row[4],
                        updated_at=row[5]
                    ) for row in rows
                ]
        except Exception as e:
            logger.error(f"获取书籍标签失败: {e}")
            return []
    
    def add_tag_to_bookmark(self, bookmark_id: int, tag_id: int) -> bool:
        """
        为书签添加标签
        
        Args:
            bookmark_id: 书签ID
            tag_id: 标签ID
            
        Returns:
            是否添加成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO bookmark_tags (bookmark_id, tag_id)
                    VALUES (?, ?)
                """, (bookmark_id, tag_id))
                conn.commit()
                
                return True
        except Exception as e:
            logger.error(f"为书签添加标签失败: {e}")
            return False
    
    def remove_tag_from_bookmark(self, bookmark_id: int, tag_id: int) -> bool:
        """
        从书签移除标签
        
        Args:
            bookmark_id: 书签ID
            tag_id: 标签ID
            
        Returns:
            是否移除成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM bookmark_tags
                    WHERE bookmark_id = ? AND tag_id = ?
                """, (bookmark_id, tag_id))
                conn.commit()
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"从书签移除标签失败: {e}")
            return False
    
    def get_tags_for_bookmark(self, bookmark_id: int) -> List[Tag]:
        """获取书签的所有标签"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.* FROM tags t
                    INNER JOIN bookmark_tags bt ON t.id = bt.tag_id
                    WHERE bt.bookmark_id = ?
                    ORDER BY t.name
                """, (bookmark_id,))
                rows = cursor.fetchall()
                
                return [
                    Tag(
                        id=row[0],
                        name=row[1],
                        color=row[2],
                        description=row[3],
                        created_at=row[4],
                        updated_at=row[5]
                    ) for row in rows
                ]
        except Exception as e:
            logger.error(f"获取书签标签失败: {e}")
            return []
    
    def search_tags(self, keyword: str) -> List[Tag]:
        """搜索标签"""
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM tags
                    WHERE name LIKE ? OR description LIKE ?
                    ORDER BY name
                """, (f"%{keyword}%", f"%{keyword}%"))
                rows = cursor.fetchall()
                
                return [
                    Tag(
                        id=row[0],
                        name=row[1],
                        color=row[2],
                        description=row[3],
                        created_at=row[4],
                        updated_at=row[5]
                    ) for row in rows
                ]
        except Exception as e:
            logger.error(f"搜索标签失败: {e}")
            return []
    
    def get_popular_tags(self, limit: int = 10) -> List[tuple]:
        """
        获取热门标签（按使用次数排序）
        
        Returns:
            List of (Tag, count) tuples
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT t.*, 
                           (SELECT COUNT(*) FROM book_tags bt WHERE bt.tag_id = t.id) +
                           (SELECT COUNT(*) FROM bookmark_tags bmt WHERE bmt.tag_id = t.id) as usage_count
                    FROM tags t
                    ORDER BY usage_count DESC, t.name
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    tag = Tag(
                        id=row[0],
                        name=row[1],
                        color=row[2],
                        description=row[3],
                        created_at=row[4],
                        updated_at=row[5]
                    )
                    result.append((tag, row[6]))  # (Tag object, usage count)
                
                return result
        except Exception as e:
            logger.error(f"获取热门标签失败: {e}")
            return []