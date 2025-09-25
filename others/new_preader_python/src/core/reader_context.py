"""
阅读器上下文管理器 - 优雅地管理阅读器服务的生命周期
使用上下文管理器模式确保资源的正确获取和释放
"""


from typing import Optional, Any, Dict
from contextlib import contextmanager

from src.core.book import Book
from src.core.reader_service import ReaderService
from src.core.reader_factory import get_reader_factory

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderContext:
    """阅读器上下文管理器类"""
    
    def __init__(self, book: Book, create_new: bool = False):
        """
        初始化阅读器上下文
        
        Args:
            book: 书籍对象
            create_new: 是否创建新的阅读器服务
        """
        self.book = book
        self.create_new = create_new
        self.reader_service: Optional[ReaderService] = None
        self.factory = get_reader_factory()
    
    def __enter__(self) -> ReaderService:
        """进入上下文，获取阅读器服务"""
        if self.create_new:
            self.reader_service = self.factory.create_reader_service(self.book)
        else:
            self.reader_service = self.factory.get_reader_service(self.book)
        
        # 加载内容并启动阅读会话
        if not self.reader_service.load_content():
            logger.error(f"加载书籍内容失败: {self.book.title}")
            raise RuntimeError(f"无法加载书籍内容: {self.book.title}")
        
        self.reader_service.start_reading_session()
        logger.debug(f"阅读器上下文已启动: {self.book.title}")
        
        return self.reader_service
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """退出上下文，清理资源"""
        if self.reader_service:
            try:
                # 停止阅读会话并获取统计信息
                stats = self.reader_service.stop_reading_session()
                
                # 保存配置
                self.reader_service.save_config()
                
                logger.debug(f"阅读器上下文已清理: {self.book.title}, 统计: {stats}")
                
                # 如果发生异常，记录日志但不阻止异常传播
                if exc_type:
                    logger.error(
                        f"阅读器上下文异常: {self.book.title}, "
                        f"异常类型: {exc_type}, 异常值: {exc_val}"
                    )
                    return False  # 不捕获异常
                
                return True  # 正常退出
                
            except Exception as e:
                logger.error(f"清理阅读器上下文失败 {self.book.title}: {e}")
                if exc_type:
                    return False  # 不捕获原始异常
                raise
        
        return True
    
    def get_service(self) -> Optional[ReaderService]:
        """获取阅读器服务（不启动上下文）"""
        return self.reader_service

@contextmanager
def reader_context(book: Book, create_new: bool = False):
    """
    阅读器上下文管理器（函数形式）
    
    Args:
        book: 书籍对象
        create_new: 是否创建新的阅读器服务
        
    Yields:
        ReaderService: 阅读器服务实例
    """
    context = ReaderContext(book, create_new)
    try:
        yield context.__enter__()
    finally:
        context.__exit__(None, None, None)

class ReaderSession:
    """阅读会话管理类"""
    
    def __init__(self, book: Book):
        """
        初始化阅读会话
        
        Args:
            book: 书籍对象
        """
        self.book = book
        self.reader_service: Optional[ReaderService] = None
        self._is_active = False
    
    def start(self) -> bool:
        """开始阅读会话"""
        try:
            self.reader_service = get_reader_factory().get_reader_service(self.book)
            
            if not self.reader_service.load_content():
                logger.error(f"加载书籍内容失败: {self.book.title}")
                return False
            
            self.reader_service.start_reading_session()
            self._is_active = True
            logger.debug(f"阅读会话已开始: {self.book.title}")
            return True
            
        except Exception as e:
            logger.error(f"开始阅读会话失败 {self.book.title}: {e}")
            return False
    
    def stop(self) -> Optional[Dict[str, Any]]:
        """停止阅读会话并返回统计信息"""
        if self.reader_service and self._is_active:
            try:
                stats = self.reader_service.stop_reading_session()
                self.reader_service.save_config()
                self._is_active = False
                logger.debug(f"阅读会话已停止: {self.book.title}")
                return stats
            except Exception as e:
                logger.error(f"停止阅读会话失败 {self.book.title}: {e}")
        
        return None
    
    def is_active(self) -> bool:
        """检查会话是否活跃"""
        return self._is_active
    
    def get_service(self) -> Optional[ReaderService]:
        """获取阅读器服务"""
        return self.reader_service
    
    def __enter__(self):
        """上下文管理器入口"""
        if self.start():
            return self.reader_service
        raise RuntimeError(f"无法开始阅读会话: {self.book.title}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
        return False  # 不捕获异常

# 使用示例函数
def with_reader_session(book: Book, callback: callable, create_new: bool = False) -> Any:
    """
    使用阅读器会话执行回调函数
    
    Args:
        book: 书籍对象
        callback: 回调函数，接收ReaderService参数
        create_new: 是否创建新的阅读器服务
        
    Returns:
        Any: 回调函数的返回值
        
    Raises:
        RuntimeError: 如果无法创建阅读器会话
    """
    with ReaderContext(book, create_new) as reader_service:
        return callback(reader_service)

def read_book(book: Book, page_callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    阅读书籍并返回统计信息
    
    Args:
        book: 书籍对象
        page_callback: 页面变化回调函数
        
    Returns:
        Dict[str, Any]: 阅读统计信息
    """
    def _read(reader_service: ReaderService) -> Dict[str, Any]:
        # 设置页面变化回调
        if page_callback:
            reader_service.set_callbacks(page_change_cb=page_callback)
        
        # 这里可以添加具体的阅读逻辑
        # 例如：自动翻页、用户交互等
        
        # 返回最终统计信息
        return reader_service.get_reading_statistics()
    
    return with_reader_session(book, _read)

# 异步支持（如果需要）
try:
    import asyncio
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def async_reader_context(book: Book, create_new: bool = False):
        """异步阅读器上下文管理器"""
        context = ReaderContext(book, create_new)
        try:
            yield await asyncio.to_thread(context.__enter__)
        finally:
            await asyncio.to_thread(context.__exit__, None, None, None)
    
except ImportError:
    # 如果没有asyncio，不提供异步支持
    pass