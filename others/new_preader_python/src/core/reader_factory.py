"""
阅读器工厂 - 管理阅读器服务的创建和销毁
提供统一的阅读器服务访问接口，支持多书籍同时阅读
"""


from typing import Dict, Optional, Any
from weakref import WeakValueDictionary

from src.core.book import Book
from src.core.reader_service import ReaderService

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderFactory:
    """阅读器工厂类 - 管理阅读器服务的生命周期"""
    
    _instance: Optional['ReaderFactory'] = None
    _readers: WeakValueDictionary[str, ReaderService]  # 使用弱引用避免内存泄漏
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._readers = WeakValueDictionary()
        return cls._instance
    
    def get_reader_service(self, book: Book) -> ReaderService:
        """
        获取或创建阅读器服务
        
        Args:
            book: 书籍对象
            
        Returns:
            ReaderService: 阅读器服务实例
        """
        book_id = self._get_book_id(book)
        
        if book_id in self._readers:
            logger.debug(f"获取现有阅读器服务: {book_id}")
            return self._readers[book_id]
        else:
            logger.debug(f"创建新阅读器服务: {book_id}")
            reader_service = ReaderService()
            reader_service.start_reading_session(book)
            self._readers[book_id] = reader_service
            return reader_service
    
    def create_reader_service(self, book: Book) -> ReaderService:
        """
        创建新的阅读器服务（强制创建新实例）
        
        Args:
            book: 书籍对象
            
        Returns:
            ReaderService: 新的阅读器服务实例
        """
        book_id = self._get_book_id(book)
        logger.debug(f"强制创建新阅读器服务: {book_id}")
        
        reader_service = ReaderService()
        reader_service.start_reading_session(book)
        self._readers[book_id] = reader_service
        return reader_service
    
    def remove_reader_service(self, book: Book) -> bool:
        """
        移除阅读器服务
        
        Args:
            book: 书籍对象
            
        Returns:
            bool: 是否成功移除
        """
        book_id = self._get_book_id(book)
        
        if book_id in self._readers:
            logger.debug(f"移除阅读器服务: {book_id}")
            # 停止阅读会话并保存状态
            reader_service = self._readers[book_id]
            reader_service.stop_reading_session()
            reader_service.save_config()
            
            del self._readers[book_id]
            return True
        
        return False
    
    def has_reader_service(self, book: Book) -> bool:
        """
        检查是否存在阅读器服务
        
        Args:
            book: 书籍对象
            
        Returns:
            bool: 是否存在
        """
        return self._get_book_id(book) in self._readers
    
    def get_all_reader_services(self) -> Dict[str, ReaderService]:
        """
        获取所有阅读器服务
        
        Returns:
            Dict[str, ReaderService]: 阅读器服务字典
        """
        return dict(self._readers)
    
    def clear_all_reader_services(self) -> int:
        """
        清除所有阅读器服务
        
        Returns:
            int: 清除的服务数量
        """
        count = len(self._readers)
        
        # 停止所有阅读会话并保存配置
        for book_id, reader_service in self._readers.items():
            try:
                reader_service.stop_reading_session()
                reader_service.save_config()
                logger.debug(f"停止并保存阅读器服务: {book_id}")
            except Exception as e:
                logger.error(f"停止阅读器服务失败 {book_id}: {e}")
        
        self._readers.clear()
        logger.debug(f"已清除所有阅读器服务: {count}个")
        return count
    
    def save_all_configs(self) -> int:
        """
        保存所有阅读器服务的配置
        
        Returns:
            int: 成功保存的数量
        """
        success_count = 0
        
        for book_id, reader_service in self._readers.items():
            try:
                if reader_service.save_config():
                    success_count += 1
                    logger.debug(f"保存配置成功: {book_id}")
                else:
                    logger.warning(f"保存配置失败: {book_id}")
            except Exception as e:
                logger.error(f"保存配置异常 {book_id}: {e}")
        
        return success_count
    
    def _get_book_id(self, book: Book) -> str:
        """
        生成书籍的唯一标识符
        
        Args:
            book: 书籍对象
            
        Returns:
            str: 书籍ID
        """
        # 使用路径和修改时间作为唯一标识
        import os
        import time
        
        if book.path:
            mtime = os.path.getmtime(book.path) if os.path.exists(book.path) else 0
            return f"{book.path}:{mtime}"
        else:
            # 对于没有路径的书籍（如默认书籍），使用标题和添加时间
            return f"{book.title}:{book.add_date}"
    
    def cleanup(self) -> None:
        """清理资源"""
        self.clear_all_reader_services()
    
    def __del__(self):
        """析构函数，确保资源清理"""
        self.cleanup()

# 全局工厂实例访问函数
def get_reader_factory() -> ReaderFactory:
    """
    获取全局阅读器工厂实例
    
    Returns:
        ReaderFactory: 阅读器工厂实例
    """
    return ReaderFactory()

def get_reader_service(book: Book) -> ReaderService:
    """
    获取阅读器服务（快捷方式）
    
    Args:
        book: 书籍对象
        
    Returns:
        ReaderService: 阅读器服务实例
    """
    return get_reader_factory().get_reader_service(book)

def create_new_reader_service(book: Book) -> ReaderService:
    """
    创建新的阅读器服务（快捷方式）
    
    Args:
        book: 书籍对象
        
    Returns:
        ReaderService: 新的阅读器服务实例
    """
    return get_reader_factory().create_reader_service(book)

def remove_reader_service(book: Book) -> bool:
    """
    移除阅读器服务（快捷方式）
    
    Args:
        book: 书籍对象
        
    Returns:
        bool: 是否成功移除
    """
    return get_reader_factory().remove_reader_service(book)

def cleanup_readers() -> int:
    """
    清理所有阅读器服务（快捷方式）
    
    Returns:
        int: 清理的服务数量
    """
    return get_reader_factory().clear_all_reader_services()