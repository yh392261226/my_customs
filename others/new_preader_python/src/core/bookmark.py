"""
书签管理模块 - 使用数据库存储
"""

import os
import json
from typing import List, Dict, Optional, Any
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

    def save_reading_info(self, book_path: str, current_page: int = 0, total_pages: int = 0,
                         reading_progress: float = 0.0, scroll_top: int = 0, scroll_height: int = 0,
                         word_count: Optional[int] = None, user_id: Optional[int] = None) -> bool:
        """
        保存阅读信息到数据库

        Args:
            book_path: 书籍路径
            current_page: 当前页码
            total_pages: 总页数
            reading_progress: 阅读进度（0-1的小数）
            scroll_top: 浏览器滚动位置（像素）
            scroll_height: 浏览器内容总高度（像素）
            word_count: 字数（可选）
            user_id: 用户ID，如果为None则使用默认值0

        Returns:
            bool: 保存是否成功
        """
        import sqlite3

        try:
            logger.info(f"BookmarkManager.save_reading_info 开始: book_path={book_path}, progress={reading_progress:.4f}, scrollTop={scroll_top}px")

            # 获取现有元数据
            metadata_json = self.db_manager.get_book_metadata(book_path, user_id)
            metadata = {}
            previous_progress = 0.0
            previous_reading_time = 0
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                    previous_progress = metadata.get('reading_progress', 0.0)
                    previous_reading_time = metadata.get('reading_time', 0)
                    logger.info(f"从数据库加载到现有元数据: {metadata}")
                except json.JSONDecodeError as e:
                    logger.warning(f"解析现有元数据失败: {e}")
                    pass
            else:
                # 如果没有现有元数据，初始化完整的元数据
                import os
                file_name = os.path.basename(book_path)
                title = os.path.splitext(file_name)[0]
                author = "未知作者"
                format_ext = os.path.splitext(book_path)[1].lower()

                # 尝试从books表中获取作者信息
                try:
                    with sqlite3.connect(self.db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT title, author FROM books WHERE path = ?", (book_path,))
                        result = cursor.fetchone()
                        if result:
                            if result[0]:  # title
                                title = result[0]
                            if result[1]:  # author
                                author = result[1]
                            logger.info(f"从books表获取到书籍信息: title={title}, author={author}")
                except Exception as e:
                    logger.warning(f"从books表获取书籍信息失败: {e}")

                metadata = {
                    'path': book_path,
                    'title': title,
                    'author': author,
                    'format': format_ext,
                    'current_position': 0,
                    'reading_time': 0,
                    'last_read_date': datetime.now().isoformat()
                }
                logger.info(f"初始化新元数据: {metadata}")

            # 更新元数据
            metadata['current_page'] = current_page
            metadata['total_pages'] = total_pages
            metadata['reading_progress'] = reading_progress
            metadata['scroll_top'] = scroll_top
            metadata['scroll_height'] = scroll_height

            # 如果提供了字数，更新字数信息
            if word_count is not None:
                metadata['word_count'] = word_count

            # 估算阅读时长（每次保存至少30秒，最多5分钟）
            progress_delta = abs(reading_progress - previous_progress)
            estimated_duration = max(30, min(300, int(progress_delta * 300)))  # 最少30秒，最多5分钟

            # 更新总阅读时间
            metadata['reading_time'] = previous_reading_time + estimated_duration
            metadata['last_read_date'] = datetime.now().isoformat()
            metadata['last_updated'] = datetime.now().isoformat()

            logger.info(f"更新后的元数据: {metadata}")

            # 保存元数据
            updated_metadata_json = json.dumps(metadata, ensure_ascii=False)

            # 直接使用数据库连接更新元数据
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO book_metadata (book_path, user_id, metadata, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (book_path, user_id if user_id is not None else 0, updated_metadata_json,
                      datetime.now().isoformat()))

                # 同时向 reading_history 表添加阅读记录
                # 估算阅读页数
                pages_read = max(1, int(progress_delta * total_pages)) if total_pages > 0 else 1

                cursor.execute("""
                    INSERT INTO reading_history (book_path, read_date, duration, pages_read,
                                                user_id, reading_progress, total_pages, word_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    book_path,
                    datetime.now().isoformat(),
                    estimated_duration,
                    pages_read,
                    user_id if user_id is not None else 0,
                    reading_progress,
                    total_pages,
                    metadata.get('word_count', 0)
                ))

                conn.commit()

            logger.info(f"保存阅读信息成功: {book_path}, 进度: {reading_progress:.4f} ({reading_progress*100:.2f}%), 滚动位置: {scroll_top}px, 阅读时长: {estimated_duration}秒")
            return True

        except Exception as e:
            logger.error(f"保存阅读信息失败: {e}", exc_info=True)
            return False

    def get_reading_info(self, book_path: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        获取阅读信息

        Args:
            book_path: 书籍路径
            user_id: 用户ID，如果为None则使用默认值0

        Returns:
            Optional[Dict[str, Any]]: 阅读信息字典，包含:
                - progress: 阅读进度百分比
                - scrollTop: 浏览器滚动位置
                - scrollHeight: 浏览器内容总高度
                - current_page: 当前页码
                - total_pages: 总页数
                - current_position: 当前位置（字符偏移）
                - last_updated: 最后更新时间
        """
        try:
            metadata_json = self.db_manager.get_book_metadata(book_path, user_id)
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                    return {
                        'progress': metadata.get('reading_progress', 0.0),
                        'scrollTop': metadata.get('scroll_top', 0),
                        'scrollHeight': metadata.get('scroll_height', 0),
                        'current_page': metadata.get('current_page', 0),
                        'total_pages': metadata.get('total_pages', 0),
                        'current_position': metadata.get('current_position', 0),
                        'last_updated': metadata.get('last_updated', '')
                    }
                except json.JSONDecodeError:
                    pass
            return None
        except Exception as e:
            logger.error(f"获取阅读信息失败: {e}")
            return None
