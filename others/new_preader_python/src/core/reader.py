"""
阅读器核心模块，负责处理书籍内容的显示和阅读功能
"""

import time

from typing import Dict, List, Any, Optional, Tuple, Callable, Any
from datetime import datetime

from src.core.book import Book
from src.core.bookshelf import Bookshelf

from src.utils.logger import get_logger

logger = get_logger(__name__)

class Reader:
    """阅读器类，处理书籍内容的显示和阅读功能"""
    
    def __init__(self, bookshelf: Bookshelf, config: Dict[str, Any]):
        """
        初始化阅读器
        
        Args:
            bookshelf: 书架对象
            config: 配置字典
        """
        self.bookshelf = bookshelf
        self.config = config
        
        # 当前书籍
        self.current_book: Optional[Book] = None
        
        # 阅读状态
        self.content: Optional[str] = None
        self.pages: List[str] = []
        self.current_page = 0
        self.total_pages = 0
        self.reading_start_time = 0
        self.auto_page_turn = False
        self.auto_page_turn_interval = config["reading"]["auto_page_turn_interval"]
        self.last_auto_turn_time = 0
        
        # 搜索状态
        self.search_results: List[Tuple[int, str]] = []
        self.current_search_index = -1
        
        # 文本朗读状态
        self.tts_enabled = config["audio"]["tts_enabled"]
        self.tts_active = False
        self.tts_paused = False
        self.tts_callback: Optional[Callable[[], None]] = None
    
    def open_book(self, book: Book) -> bool:
        """
        打开书籍
        
        Args:
            book: 书籍对象
            
        Returns:
            bool: 是否成功打开
        """
        try:
            self.current_book = book
            
            # 加载书籍内容
            self.content = book.get_content()
            
            # 分页
            self._paginate()
            
            # 恢复阅读位置
            if self.config["reading"]["remember_position"] and book.current_page > 0:
                self.current_page = min(book.current_page, self.total_pages - 1)
            else:
                self.current_page = 0
            
            # 更新书籍信息
            book.increment_open_count()
            book.update_reading_progress(self._get_position_from_page(self.current_page), 
                                        self.current_page, 
                                        self.total_pages)
            
            # 记录阅读开始时间
            self.reading_start_time = time.time()
            
            # 重置状态
            self.auto_page_turn = False
            self.search_results = []
            self.current_search_index = -1
            self.tts_active = False
            self.tts_paused = False
            
            logger.info(f"已打开书籍: {book.title}")
            return True
        except Exception as e:
            logger.error(f"打开书籍时出错: {e}")
            self.current_book = None
            self.content = None
            self.pages = []
            return False
    
    def close_book(self) -> bool:
        """
        关闭当前书籍
        
        Returns:
            bool: 是否成功关闭
        """
        if not self.current_book:
            return False
        
        try:
            # 停止文本朗读
            self.stop_tts()
            
            # 计算阅读时间
            reading_duration = int(time.time() - self.reading_start_time)
            
            # 更新书籍信息
            self.current_book.update_reading_progress(self._get_position_from_page(self.current_page), 
                                                    self.current_page, 
                                                    self.total_pages)
            
            # 添加阅读记录
            if reading_duration > 0:
                self.bookshelf.add_reading_record(self.current_book, reading_duration)
            
            # 保存书架数据
            self.bookshelf.save()
            
            # 重置状态
            book_title = self.current_book.title
            self.current_book = None
            self.content = None
            self.pages = []
            self.current_page = 0
            self.total_pages = 0
            self.reading_start_time = 0
            self.auto_page_turn = False
            self.search_results = []
            self.current_search_index = -1
            
            logger.info(f"已关闭书籍: {book_title}")
            return True
        except Exception as e:
            logger.error(f"关闭书籍时出错: {e}")
            return False
    
    def _paginate(self) -> None:
        """将内容分页（已废弃，由DynamicContentRenderer处理）"""
        if not self.content:
            self.pages = []
            self.total_pages = 0
            return
        
        # 旧的分页逻辑已废弃，现在由DynamicContentRenderer处理动态分页
        # 这里保留一个空页用于兼容性
        self.pages = [self.content]
        self.total_pages = 1
        logger.info("内容分页已由DynamicContentRenderer处理")
    
    def _get_position_from_page(self, page: int) -> int:
        """
        根据页码获取字符位置
        
        Args:
            page: 页码
            
        Returns:
            int: 字符位置
        """
        position = 0
        for i in range(page):
            if i < len(self.pages):
                position += len(self.pages[i])
        return position
    
    def get_current_page_content(self) -> str:
        """
        获取当前页内容
        
        Returns:
            str: 当前页内容
        """
        if not self.pages or self.current_page >= len(self.pages):
            return ""
        return self.pages[self.current_page]
    
    def get_page_content(self, page: int) -> str:
        """
        获取指定页内容
        
        Args:
            page: 页码
            
        Returns:
            str: 页面内容
        """
        if not self.pages or page < 0 or page >= len(self.pages):
            return ""
        return self.pages[page]
    
    def next_page(self) -> bool:
        """
        跳转到下一页
        
        Returns:
            bool: 是否成功跳转
        """
        if not self.current_book or self.current_page >= self.total_pages - 1:
            return False
        
        self.current_page += 1
        
        # 更新书籍进度
        if self.current_book:
            self.current_book.update_reading_progress(
                self._get_position_from_page(self.current_page),
                self.current_page,
                self.total_pages
            )
        
        return True
    
    def prev_page(self) -> bool:
        """
        跳转到上一页
        
        Returns:
            bool: 是否成功跳转
        """
        if not self.current_book or self.current_page <= 0:
            return False
        
        self.current_page -= 1
        
        # 更新书籍进度
        if self.current_book:
            self.current_book.update_reading_progress(
                self._get_position_from_page(self.current_page),
                self.current_page,
                self.total_pages
            )
        
        return True
    
    def goto_page(self, page: int) -> bool:
        """
        跳转到指定页
        
        Args:
            page: 页码
            
        Returns:
            bool: 是否成功跳转
        """
        if not self.current_book or page < 0 or page >= self.total_pages:
            return False
        
        self.current_page = page
        
        # 更新书籍进度
        if self.current_book:
            self.current_book.update_reading_progress(
                self._get_position_from_page(self.current_page),
                self.current_page,
                self.total_pages
            )
        
        return True
    
    def toggle_auto_page_turn(self) -> bool:
        """
        切换自动翻页
        
        Returns:
            bool: 自动翻页是否开启
        """
        self.auto_page_turn = not self.auto_page_turn
        self.last_auto_turn_time = time.time()
        return self.auto_page_turn
    
    def set_auto_page_turn_interval(self, seconds: int) -> None:
        """
        设置自动翻页间隔
        
        Args:
            seconds: 间隔秒数
        """
        self.auto_page_turn_interval = max(1, seconds)
        self.config["reading"]["auto_page_turn_interval"] = self.auto_page_turn_interval
    
    def update(self) -> bool:
        """
        更新阅读器状态，处理自动翻页等
        
        Returns:
            bool: 是否有状态更新
        """
        updated = False
        
        # 处理自动翻页
        if self.auto_page_turn and time.time() - self.last_auto_turn_time >= self.auto_page_turn_interval:
            if self.next_page():
                updated = True
            self.last_auto_turn_time = time.time()
        
        return updated
    
    def search(self, keyword: str) -> List[Tuple[int, str]]:
        """
        搜索内容
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Tuple[int, str]]: 搜索结果列表，每个元素为(页码, 上下文)
        """
        if not self.current_book or not self.content or not keyword:
            return []
        
        # 使用书籍的搜索方法
        raw_results = self.current_book.search(keyword)
        
        # 转换为页码和上下文
        results = []
        for position, context in raw_results:
            # 找到对应的页码
            page = 0
            pos = 0
            for i, page_content in enumerate(self.pages):
                if pos + len(page_content) > position:
                    page = i
                    break
                pos += len(page_content)
            
            results.append((page, context))
        
        self.search_results = results
        self.current_search_index = 0 if results else -1
        
        return results
    
    def goto_next_search_result(self) -> Optional[Tuple[int, str]]:
        """
        跳转到下一个搜索结果
        
        Returns:
            Optional[Tuple[int, str]]: (页码, 上下文)，如果没有更多结果则返回None
        """
        if not self.search_results or self.current_search_index < 0:
            return None
        
        result = self.search_results[self.current_search_index]
        self.goto_page(result[0])
        
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        
        return result
    
    def goto_prev_search_result(self) -> Optional[Tuple[int, str]]:
        """
        跳转到上一个搜索结果
        
        Returns:
            Optional[Tuple[int, str]]: (页码, 上下文)，如果没有更多结果则返回None
        """
        if not self.search_results or self.current_search_index < 0:
            return None
        
        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        result = self.search_results[self.current_search_index]
        self.goto_page(result[0])
        
        return result
    
    def clear_search(self) -> None:
        """清除搜索结果"""
        self.search_results = []
        self.current_search_index = -1
    
    def add_bookmark(self, note: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        在当前位置添加书签
        
        Args:
            note: 书签备注
            
        Returns:
            Optional[Dict[str, Any]]: 书签字典，如果添加失败则返回None
        """
        if not self.current_book:
            return None
        
        try:
            position = self._get_position_from_page(self.current_page)
            page_content = self.get_current_page_content()
            text = page_content[:100] + ("..." if len(page_content) > 100 else "")
            
            bookmark = self.current_book.add_bookmark(position, self.current_page, text, note)
            self.bookshelf.save()
            
            return bookmark
        except Exception as e:
            logger.error(f"添加书签时出错: {e}")
            return None
    
    def remove_bookmark(self, bookmark_id: str) -> bool:
        """
        移除书签
        
        Args:
            bookmark_id: 书签ID
            
        Returns:
            bool: 是否成功移除
        """
        if not self.current_book:
            return False
        
        if self.current_book.remove_bookmark(bookmark_id):
            self.bookshelf.save()
            return True
        return False
    
    def get_bookmarks(self) -> List[Dict[str, Any]]:
        """
        获取当前书籍的所有书签
        
        Returns:
            List[Dict[str, Any]]: 书签列表
        """
        if not self.current_book:
            return []
        
        return self.current_book.get_bookmarks()
    
    def goto_bookmark(self, bookmark_id: str) -> bool:
        """
        跳转到书签位置
        
        Args:
            bookmark_id: 书签ID
            
        Returns:
            bool: 是否成功跳转
        """
        if not self.current_book:
            return False
        
        for bookmark in self.current_book.get_bookmarks():
            if bookmark["id"] == bookmark_id:
                return self.goto_page(bookmark["page"])
        
        return False
    
    def start_tts(self, callback: Optional[Callable[[], None]] = None) -> bool:
        """
        开始文本朗读
        
        Args:
            callback: 朗读完成后的回调函数
            
        Returns:
            bool: 是否成功开始朗读
        """
        if not self.current_book or not self.tts_enabled:
            return False
        
        self.tts_active = True
        self.tts_paused = False
        self.tts_callback = callback
        
        # 实际的TTS实现将在UI层处理
        logger.info("开始文本朗读")
        return True
    
    def stop_tts(self) -> bool:
        """
        停止文本朗读
        
        Returns:
            bool: 是否成功停止朗读
        """
        if not self.tts_active:
            return False
        
        self.tts_active = False
        self.tts_paused = False
        
        # 实际的TTS实现将在UI层处理
        logger.info("停止文本朗读")
        return True
    
    def pause_tts(self) -> bool:
        """
        暂停文本朗读
        
        Returns:
            bool: 是否成功暂停朗读
        """
        if not self.tts_active or self.tts_paused:
            return False
        
        self.tts_paused = True
        
        # 实际的TTS实现将在UI层处理
        logger.info("暂停文本朗读")
        return True
    
    def resume_tts(self) -> bool:
        """
        恢复文本朗读
        
        Returns:
            bool: 是否成功恢复朗读
        """
        if not self.tts_active or not self.tts_paused:
            return False
        
        self.tts_paused = False
        
        # 实际的TTS实现将在UI层处理
        logger.info("恢复文本朗读")
        return True
    
    def toggle_tts(self) -> bool:
        """
        切换文本朗读状态
        
        Returns:
            bool: 朗读是否开启
        """
        if self.tts_active:
            self.stop_tts()
            return False
        else:
            return self.start_tts()
    
    def get_reading_progress(self) -> float:
        """
        获取阅读进度
        
        Returns:
            float: 阅读进度（0.0-1.0）
        """
        if not self.current_book or self.total_pages <= 0:
            return 0.0
        
        return self.current_page / self.total_pages
    
    def get_reading_statistics(self) -> Dict[str, Any]:
        """
        获取阅读统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        if not self.current_book:
            return {}
        
        # 计算当前阅读时间
        current_session_time = int(time.time() - self.reading_start_time)
        total_reading_time = self.current_book.reading_time + current_session_time
        
        # 不再使用基于字数的计算，阅读速度和剩余时间设为0
        reading_speed = 0
        estimated_time_left = 0
        
        # 计算已读页数
        pages_read = self.current_page
        
        return {
            "current_page": self.current_page + 1,  # 1-based for display
            "total_pages": self.total_pages,
            "progress": self.get_reading_progress(),
            "reading_time": total_reading_time,
            "words_read": words_read,
            "reading_speed": reading_speed,
            "estimated_time_left": estimated_time_left,
            "open_count": self.current_book.open_count
        }
    
    def reset_progress(self) -> bool:
        """
        重置阅读进度
        
        Returns:
            bool: 是否成功重置
        """
        if not self.current_book:
            return False
        
        self.current_book.reset_progress()
        self.current_page = 0
        self.bookshelf.save()
        
        return True
    
    def adjust_font_size(self, delta: int) -> int:
        """
        调整字体大小
        
        Args:
            delta: 变化量
            
        Returns:
            int: 调整后的字体大小
        """
        font_size = self.config["reading"]["font_size"]
        font_size = max(8, min(32, font_size + delta))
        self.config["reading"]["font_size"] = font_size
        return font_size
    
    def adjust_line_spacing(self, delta: float) -> float:
        """
        调整行间距
        
        Args:
            delta: 变化量
            
        Returns:
            float: 调整后的行间距
        """
        line_spacing = self.config["reading"]["line_spacing"]
        line_spacing = max(1.0, min(3.0, line_spacing + delta))
        self.config["reading"]["line_spacing"] = line_spacing
        return line_spacing
    
    def adjust_paragraph_spacing(self, delta: float) -> float:
        """
        调整段落间距
        
        Args:
            delta: 变化量
            
        Returns:
            float: 调整后的段落间距
        """
        paragraph_spacing = self.config["reading"]["paragraph_spacing"]
        paragraph_spacing = max(1.0, min(3.0, paragraph_spacing + delta))
        self.config["reading"]["paragraph_spacing"] = paragraph_spacing
        return paragraph_spacing