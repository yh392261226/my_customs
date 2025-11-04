"""
书签管理模块 - 使用数据库存储
"""

import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from datetime import datetime
import time

from src.core.database_manager import DatabaseManager

from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class Bookmark:
    """书签数据类"""
    id: Optional[int] = None  # 数据库ID
    book_id: str = ""
    # 统一为“绝对字符偏移”（跨屏幕尺寸更稳健）
    position: int = 0
    note: str = ""
    timestamp: float = 0.0  # 创建时间戳
    created_date: str = ""  # 创建日期
    # 锚点（用于跨分页纠偏）
    anchor_text: str = ""
    anchor_hash: str = ""

class BookmarkManager:
    """书签管理器 - 使用数据库存储"""
    
    def __init__(self):
        """初始化书签管理器"""
        self.db_manager = DatabaseManager()
        self.bookmarks: Dict[str, List[Bookmark]] = {}
    
    def add_bookmark(self, bookmark: Bookmark, user_id: Optional[int] = None) -> bool:
        """
        添加书签到数据库
        
        Args:
            bookmark: 要添加的书签
            user_id: 用户ID，如果为None则使用默认值0
            
        Returns:
            bool: 添加是否成功
        """
        # 设置时间戳和创建日期
        if not bookmark.timestamp:
            bookmark.timestamp = time.time()
        if not bookmark.created_date:
            bookmark.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 使用数据库管理器添加书签
        success = self.db_manager.add_bookmark(
            bookmark.book_id,
            int(bookmark.position or 0),
            bookmark.note,
            bookmark.anchor_text,
            bookmark.anchor_hash,
            user_id
        )
        
        if success:
            # 更新本地缓存
            if bookmark.book_id not in self.bookmarks:
                self.bookmarks[bookmark.book_id] = []
            self.bookmarks[bookmark.book_id].append(bookmark)
        
        return success
    
    def get_bookmarks(self, book_id: str, user_id: Optional[int] = None) -> List[Bookmark]:
        """
        从数据库获取指定书籍的所有书签
        
        Args:
            book_id: 书籍ID
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            List[Bookmark]: 该书的所有书签列表
        """
        # 从数据库获取书签数据
        db_bookmarks = self.db_manager.get_bookmarks(book_id, user_id)
        
        # 转换为Bookmark对象
        bookmarks = []
        for bm_data in db_bookmarks:
            # 兼容旧库：position 可能是字符串
            try:
                pos_val = int(bm_data.get('position', 0) or 0)
            except Exception:
                pos_val = 0
            bookmark = Bookmark(
                id=bm_data.get('id'),
                book_id=bm_data.get('book_path', ''),
                position=pos_val,
                note=bm_data.get('note', ''),
                timestamp=bm_data.get('timestamp', 0.0),
                created_date=bm_data.get('created_date', ''),
                anchor_text=bm_data.get('anchor_text', '') if isinstance(bm_data, dict) else '',
                anchor_hash=bm_data.get('anchor_hash', '') if isinstance(bm_data, dict) else ''
            )
            bookmarks.append(bookmark)
        
        # 更新本地缓存
        self.bookmarks[book_id] = bookmarks
        return bookmarks
    
    def get_all_bookmarks(self, user_id: Optional[int] = None) -> List[Bookmark]:
        """
        从数据库获取所有书签
        
        Args:
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            List[Bookmark]: 所有书签列表
        """
        # 从数据库获取所有书签数据
        db_bookmarks = self.db_manager.get_all_bookmarks(user_id)
        
        # 转换为Bookmark对象
        bookmarks = []
        for bm_data in db_bookmarks:
            try:
                pos_val = int(bm_data.get('position', 0) or 0)
            except Exception:
                pos_val = 0
            bookmark = Bookmark(
                id=bm_data.get('id'),
                book_id=bm_data.get('book_path', ''),
                position=pos_val,
                note=bm_data.get('note', ''),
                timestamp=bm_data.get('timestamp', 0.0),
                created_date=bm_data.get('created_date', ''),
                anchor_text=bm_data.get('anchor_text', '') if isinstance(bm_data, dict) else '',
                anchor_hash=bm_data.get('anchor_hash', '') if isinstance(bm_data, dict) else ''
            )
            bookmarks.append(bookmark)
        
        return bookmarks
    
    def remove_bookmark(self, bookmark_id: int, user_id: Optional[int] = None) -> bool:
        """
        从数据库删除指定书签
        
        Args:
            bookmark_id: 书签ID
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            bool: 是否成功删除
        """
        # 使用数据库管理器删除书签
        success = self.db_manager.delete_bookmark(bookmark_id, user_id)
        
        if success:
            # 从本地缓存中删除
            for book_id in list(self.bookmarks.keys()):
                self.bookmarks[book_id] = [
                    bm for bm in self.bookmarks[book_id] 
                    if bm.id != bookmark_id
                ]
                # 如果该书没有书签了，删除对应的键
                if not self.bookmarks[book_id]:
                    del self.bookmarks[book_id]
        
        return success
    
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
        # 使用数据库管理器更新书签备注
        success = self.db_manager.update_bookmark_note(bookmark_id, note, user_id)
        
        if success:
            # 更新本地缓存
            for book_id in self.bookmarks:
                for bookmark in self.bookmarks[book_id]:
                    if bookmark.id == bookmark_id:
                        bookmark.note = note
                        break
        
        return success
    
    def get_bookmark_by_id(self, bookmark_id: int, user_id: Optional[int] = None) -> Optional[Bookmark]:
        """
        根据ID获取书签
        
        Args:
            bookmark_id: 书签ID
            user_id: 用户ID，如果为None则不按用户过滤
            
        Returns:
            Optional[Bookmark]: 书签对象，如果不存在则返回None
        """
        # 从所有书签中查找
        all_bookmarks = self.get_all_bookmarks(user_id)
        for bookmark in all_bookmarks:
            if bookmark.id == bookmark_id:
                return bookmark
        return None
    
