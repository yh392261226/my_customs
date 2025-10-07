"""
书籍管理器，负责处理书籍的添加、扫描和管理操作
遵循面向对象和面向切片的开发思路，保持低耦合和高可扩展性
"""

import os

import threading
from typing import Dict, List, Optional, Tuple, Callable, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.book import Book
from src.core.bookshelf import Bookshelf
from src.core.search import SearchEngine
from src.config.config_manager import ConfigManager
from src.config.default_config import SUPPORTED_FORMATS
from src.utils.file_utils import FileUtils
from src.utils.logger import LoggerSetup

from src.utils.logger import get_logger

logger = get_logger(__name__)

class BookManager:
    """书籍管理器类"""
    
    def __init__(self, bookshelf: Bookshelf, max_workers: int = 4):
        """
        初始化书籍管理器
        
        Args:
            bookshelf: 书架实例
            max_workers: 最大工作线程数
        """
        self.bookshelf = bookshelf
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._scan_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # 初始化搜索引擎
        config = ConfigManager().get_config()
        self.search_engine = SearchEngine(config["paths"]["database"])
        
    @LoggerSetup.debug_log
    def add_book(self, file_path: str, title: Optional[str] = None, 
                author: Optional[str] = None) -> Optional[Book]:
        """
        添加单本书籍
        
        Args:
            file_path: 书籍文件路径
            title: 书籍标题
            author: 书籍作者
            
        Returns:
            Optional[Book]: 添加的书籍对象
        """
        try:
            # 验证文件路径
            if not self._validate_file_path(file_path):
                logger.warning(f"无效的文件路径或格式: {file_path}")
                return None
                
            # 添加书籍到书架
            book = self.bookshelf.add_book(file_path, title, author)
            if book:
                logger.info(f"成功添加书籍: {book.title}")
                
                # 索引书籍内容到搜索数据库
                self._index_book_content(book)
                
                return book
            else:
                logger.warning(f"添加书籍失败: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"添加书籍时发生错误: {e}")
            return None
            
    @LoggerSetup.debug_log
    def add_books(self, file_paths: List[str]) -> Tuple[int, List[str]]:
        """
        批量添加书籍
        
        Args:
            file_paths: 书籍文件路径列表
            
        Returns:
            Tuple[int, List[str]]: (成功添加的数量, 失败的文件列表)
        """
        success_count = 0
        failed_files = []
        
        for file_path in file_paths:
            if self.add_book(file_path):
                success_count += 1
            else:
                failed_files.append(file_path)
                
        return success_count, failed_files
        
    @LoggerSetup.debug_log
    def scan_directory(self, directory: str, 
                      progress_callback: Optional[Callable[[int, int], None]] = None,
                      result_callback: Optional[Callable[[int, List[str]], None]] = None) -> None:
        """
        异步扫描目录并添加书籍
        
        Args:
            directory: 目录路径
            progress_callback: 进度回调函数
            result_callback: 结果回调函数
        """
        def scan_task():
            try:
                if not os.path.isdir(directory):
                    error_msg = f"目录不存在: {directory}"
                    logger.error(error_msg)
                    if result_callback:
                        result_callback(0, [error_msg])
                    return
                    
                # 查找所有支持的书籍文件
                book_files = []
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._validate_file_path(file_path):
                            book_files.append(file_path)
                            
                total_files = len(book_files)
                logger.info(f"在目录 {directory} 中找到 {total_files} 个支持的书籍文件")
                
                if progress_callback:
                    progress_callback(0, total_files)
                    
                # 分批处理文件
                success_count = 0
                failed_files = []
                
                for i, file_path in enumerate(book_files):
                    try:
                        if self.add_book(file_path, None, None):
                            success_count += 1
                        else:
                            failed_files.append(file_path)
                    except Exception as e:
                        logger.error(f"处理文件时出错 {file_path}: {e}")
                        failed_files.append(file_path)
                        
                    # 更新进度
                    if progress_callback:
                        progress_callback(i + 1, total_files)
                        
                logger.info(f"扫描完成: 成功添加 {success_count} 本书籍, 失败 {len(failed_files)} 个文件")
                
                if result_callback:
                    result_callback(success_count, failed_files)
                    
            except Exception as e:
                logger.error(f"扫描目录时发生错误: {e}")
                if result_callback:
                    result_callback(0, [str(e)])
                    
        # 在后台线程执行扫描任务
        threading.Thread(target=scan_task, daemon=True).start()
        
    def _validate_file_path(self, file_path: str) -> bool:
        """
        验证文件路径是否有效且为支持的格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否有效
        """
        if not os.path.exists(file_path):
            return False
            
        if not os.path.isfile(file_path):
            return False
            
        # 检查文件扩展名
        file_ext = FileUtils.get_file_extension(file_path)
        return file_ext in SUPPORTED_FORMATS
        
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的书籍格式列表
        
        Returns:
            List[str]: 支持的格式列表
        """
        return SUPPORTED_FORMATS.copy()
        
    def register_scan_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        注册扫描回调函数
        
        Args:
            callback: 回调函数
        """
        self._scan_callbacks.append(callback)
        
    def unregister_scan_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        取消注册扫描回调函数
        
        Args:
            callback: 回调函数
        """
        if callback in self._scan_callbacks:
            self._scan_callbacks.remove(callback)
            
    def _notify_scan_callbacks(self, result: Dict[str, Any]) -> None:
        """
        通知所有扫描回调函数
        
        Args:
            result: 扫描结果
        """
        for callback in self._scan_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"扫描回调函数执行错误: {e}")
    
    def _index_book_content(self, book: Book) -> None:
        """
        索引书籍内容到搜索数据库
        
        Args:
            book: 书籍对象
        """
        try:
            # 读取书籍内容进行索引
            content = book.get_content()
            if content:
                # 索引书籍内容，按章节或页面分割
                # 这里简化处理，将整个内容作为一个索引项
                self.search_engine.index_book(book.path, content, "full_content")
                logger.info(f"已索引书籍: {book.title}")
        except Exception as e:
            logger.error(f"索引书籍内容时出错: {e}")
                
    def cleanup(self) -> None:
        """清理资源"""
        self.executor.shutdown(wait=False)