"""
书架管理器，负责管理书籍集合和相关操作
"""

import os

import json
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path

from src.core.book import Book
from src.core.database_manager import DatabaseManager
from src.config.default_config import SUPPORTED_FORMATS
from src.utils.logger import LoggerSetup

from src.utils.logger import get_logger

logger = get_logger(__name__)

@LoggerSetup.debug_log
def debug_logged(func):
    """调试日志装饰器"""
    return func

class Bookshelf:
    """书架类，管理书籍集合"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化书架
        
        Args:
            data_dir: 数据目录，如果为None则使用默认目录
        """
        if data_dir is None:
            # 默认数据目录为用户主目录下的.config/new_preader/books文件夹
            self.data_dir = os.path.join(str(Path.home()), ".config", "new_preader", "books")
        else:
            self.data_dir = data_dir
            
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        # 当前登录用户ID（伪用户系统）
        self.current_user_id: Optional[int] = None
        self.current_user_role: str = "user"
        
        self.books: Dict[str, Book] = {}  # 书籍字典，键为书籍路径
        self.reading_history: List[Dict[str, Any]] = []  # 阅读历史记录
        
        # 加载书籍数据
        self._load_books()
        self._load_reading_history()
    
    def _load_books(self) -> None:
        """从数据库加载书籍数据（按当前用户过滤）"""
        try:
            self.books.clear()
            books: List[Book]
            # 超级管理员可以看所有的书籍，普通用户只能看自己的书籍
            # 如果当前用户ID为None，则直接为空列表，不进行过滤
            if self.current_user_role == "superadmin" or self.current_user_role == "super_admin" : 
                books = self.db_manager.get_all_books()
            elif self.current_user_id is not None :
                books = self.db_manager.get_books_for_user(self.current_user_id)
            else:
                books = []

            for book in books:
                if book.path and os.path.exists(book.path):
                    self.books[book.path] = book
                else:
                    logger.warning(f"书籍文件不存在，但保留记录: {book.path}")
                    self.books[book.path] = book
            logger.info(f"已加载 {len(self.books)} 本书籍（用户过滤：{self.current_user_id is not None}）")
        except Exception as e:
            logger.error(f"从数据库加载书籍数据时出错: {e}")
    
    def _load_reading_history(self) -> None:
        """从数据库加载阅读历史记录"""
        try:
            self.reading_history = self.db_manager.get_reading_history()
            logger.info(f"已加载 {len(self.reading_history)} 条阅读历史记录")
        except Exception as e:
            logger.error(f"从数据库加载阅读历史记录时出错: {e}")
    
    @debug_logged
    def save(self) -> bool:
        """
        保存书架数据到数据库
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 保存所有书籍到数据库
            for book in self.books.values():
                if not self.db_manager.add_book(book):
                    logger.error(f"保存书籍到数据库失败: {book.title}")
                    return False
            
            logger.info("书架数据已保存到数据库")
            return True
        except Exception as e:
            logger.error(f"保存书架数据时出错: {e}")
            return False
    
    @debug_logged
    def add_book(self, path: str, title: Optional[str] = None, author: Optional[str] = None, tags: Optional[str] = None) -> Optional[Book]:
        """
        添加书籍
        
        Args:
            path: 书籍文件路径
            title: 书籍标题，如果为None则使用文件名
            author: 书籍作者，如果为None则为"未知作者"
            tags: 书籍标签，如果为None则为空字符串
            
        Returns:
            Optional[Book]: 添加的书籍对象，如果添加失败则返回None
        """
        try:
            # 检查文件是否已存在于书架中
            abs_path = os.path.abspath(path)
            
            # 使用数据库检查书籍是否已存在
            existing_book = self.db_manager.get_book(abs_path)
            if existing_book:
                logger.warning(f"书籍已存在于书架中: {abs_path}")
                return existing_book
            
            # 创建书籍对象
            book = Book(abs_path, title, author, tags=tags)
            
            # 若为非 txt/md 且作者为空或未知，尝试解析作者（失败忽略）
            try:
                ext = os.path.splitext(abs_path)[1].lower()
                is_txt_like = ext in ('.txt', '.md')
                need_author = (not author) or (isinstance(author, str) and author.strip() in ("", "未知作者"))
                if (not is_txt_like) and need_author:
                    extracted = self._try_extract_author(abs_path, ext)
                    if extracted and isinstance(extracted, str) and extracted.strip():
                        book.author = extracted.strip()
            except Exception:
                # 静默忽略，保证导入流程不中断
                pass
            
            # 将书籍保存到数据库
            self.db_manager.add_book(book)
            # 记录归属用户（不用于显示，仅过滤）
            try:
                if self.current_user_id is not None:
                    self.db_manager.assign_book_to_user(self.current_user_id, abs_path)
            except Exception:
                pass
            # 更新内存中的书籍字典（用于向后兼容）
            self.books[abs_path] = book
            
            logger.info(f"已添加书籍到数据库: {book.title}")
            return book
        except Exception as e:
            logger.error(f"添加书籍时出错: {e}")
            return None
    
    @debug_logged
    def remove_book(self, path: str) -> bool:
        """
        移除书籍
        
        Args:
            path: 书籍文件路径
            
        Returns:
            bool: 是否成功移除
        """
        abs_path = os.path.abspath(path)
        if abs_path in self.books:
            del self.books[abs_path]
            
            # 从数据库中删除书籍
            self.db_manager.delete_book(abs_path)
            
            # 从阅读历史中移除相关记录
            self.reading_history = [record for record in self.reading_history if record.get("path") != abs_path and record.get("book_path") != abs_path]
            
            logger.info(f"已从数据库中移除书籍: {abs_path}")
            return True
        else:
            logger.warning(f"书籍不存在于书架中: {abs_path}")
            return False
    
    @debug_logged
    def get_book(self, path: str) -> Optional[Book]:
        """
        获取书籍
        
        Args:
            path: 书籍文件路径
            
        Returns:
            Optional[Book]: 书籍对象，如果不存在则返回None
        """
        # 首先尝试直接查找
        if path in self.books:
            return self.books[path]
        
        # 如果直接查找失败，尝试使用绝对路径查找
        abs_path = os.path.abspath(path)
        if abs_path in self.books:
            return self.books[abs_path]
        
        # 如果绝对路径也失败，尝试规范化路径后查找
        norm_path = os.path.normpath(path)
        if norm_path in self.books:
            return self.books[norm_path]
        
        # 最后尝试所有可能的路径格式
        for book_path, book in self.books.items():
            if (os.path.abspath(book_path) == abs_path or 
                os.path.normpath(book_path) == norm_path or
                book_path == path):
                return book
        
        return None
    
    def get_all_books(self) -> List[Book]:
        """
        获取所有书籍
        
        Returns:
            List[Book]: 书籍列表
        """
        return list(self.books.values())
    
    def search_books(self, keyword: str, format: Optional[str] = None) -> List[Book]:
        """
        搜索书籍
        
        Args:
            keyword: 搜索关键词
            format: 可选，文件格式筛选
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        # 使用数据库进行搜索，支持文件格式筛选
        return self.db_manager.search_books(keyword, format)
    
    def filter_books_by_format(self, format_: str) -> List[Book]:
        """
        按格式筛选书籍
        
        Args:
            format_: 文件格式（如".txt", ".epub"等）
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        if not format_.startswith('.'):
            format_ = f".{format_}"
            
        return [book for book in self.books.values() if book.format == format_.lower()]
    
    def filter_books_by_tag(self, tag: str) -> List[Book]:
        """
        按标签筛选书籍
        
        Args:
            tag: 标签名称
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        return [book for book in self.books.values() if tag in book.tags]
    
    def filter_books_by_author(self, author: str) -> List[Book]:
        """
        按作者筛选书籍
        
        Args:
            author: 作者名称
            
        Returns:
            List[Book]: 匹配的书籍列表
        """
        author = author.lower()
        return [book for book in self.books.values() if author in book.author.lower()]
    
    def sort_books(self, key: str, reverse: bool = False) -> List[Book]:
        """
        排序书籍（使用数据库排序）
        
        Args:
            key: 排序键，可选值为"title", "author", "add_date", "last_read_date", "progress"
            reverse: 是否倒序
            
        Returns:
            List[Book]: 排序后的书籍列表
        """
        try:
            # 使用数据库管理器进行排序
            return self.db_manager.get_sorted_books(key, reverse)
        except Exception as e:
            logger.error(f"数据库排序失败，使用内存排序: {e}")
            # 降级到内存排序
            return self._sort_books_in_memory(key, reverse)
    
    def _sort_books_in_memory(self, key: str, reverse: bool = False) -> List[Book]:
        """
        内存排序（数据库排序失败时的降级方案）
        
        Args:
            key: 排序键
            reverse: 是否倒序
            
        Returns:
            List[Book]: 排序后的书籍列表
        """
        books = list(self.books.values())
        
        if key == "title":
            return sorted(books, key=lambda x: x.title.lower(), reverse=reverse)
        elif key == "author":
            return sorted(books, key=lambda x: x.author.lower(), reverse=reverse)
        elif key == "add_date":
            return sorted(books, key=lambda x: x.add_date, reverse=reverse)
        elif key == "last_read_date":
            # 将没有阅读记录的书籍排在最后
            def get_last_read_date(book):
                if book.last_read_date:
                    return book.last_read_date
                # 返回一个极早的日期，确保没有阅读记录的书籍排在最后
                # 无论升序还是降序，没有阅读记录的都应该排在最后
                return datetime.min.isoformat()
            return sorted(books, key=get_last_read_date, reverse=reverse)
        elif key == "progress":
            return sorted(books, key=lambda x: x.reading_progress or 0, reverse=reverse)
        else:
            logger.warning(f"不支持的排序键: {key}，将使用标题排序")
            return sorted(books, key=lambda x: x.title.lower(), reverse=reverse)
    
    def get_recently_read_books(self, limit: int = 3) -> List[Book]:
        """
        获取最近阅读的书籍
        
        Args:
            limit: 返回的书籍数量
            
        Returns:
            List[Book]: 最近阅读的书籍列表
        """
        # 按最后阅读时间排序，确保last_read_date不为None
        books = [book for book in self.books.values() if book.last_read_date]
        books.sort(key=lambda x: x.last_read_date or "", reverse=True)
        return books[:limit]
    
    def add_reading_record(self, book: Book, duration: int, pages_read: int = 0, reading_time: Optional[int] = None) -> None:
        """
        添加阅读记录
        
        Args:
            book: 书籍对象
            duration: 阅读时长（秒）
            pages_read: 阅读页数（可选）
            reading_time: 阅读时间（秒，可选，已弃用，使用duration参数）
        """
        # 保持向后兼容性：如果传入了reading_time，使用它，否则使用duration
        effective_duration = reading_time if reading_time is not None else duration
        
        record = {
            "path": book.path,
            "title": book.title,
            "author": book.author,
            "timestamp": datetime.now().isoformat(),
            "duration": effective_duration,
            "progress": book.reading_progress,
            "pages_read": pages_read
        }
        
        self.reading_history.append(record)
        
        # 更新书籍的阅读时间
        book.add_reading_time(effective_duration)
        
        # 保存阅读记录到数据库
        try:
            self.db_manager.add_reading_record(
                book_path=book.path,
                duration=effective_duration,
                pages_read=pages_read
            )
            logger.info(f"已保存阅读记录到数据库: {book.title}, 时长: {effective_duration}秒")
        except Exception as e:
            logger.error(f"保存阅读记录到数据库失败: {e}")
        
        # 保存书架数据
        self.save()
    
    def get_reading_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取阅读历史记录
        
        Args:
            limit: 返回的记录数量，如果为None则返回所有记录
            
        Returns:
            List[Dict[str, Any]]: 阅读历史记录列表
        """
        if limit is None:
            return self.reading_history
        return self.reading_history[-limit:]
    
    def clear_reading_history(self, book_path: Optional[str] = None) -> None:
        """
        清除阅读历史记录
        
        Args:
            book_path: 书籍路径，如果为None则清除所有记录
        """
        if book_path is None:
            self.reading_history = []
        else:
            abs_path = os.path.abspath(book_path)
            self.reading_history = [record for record in self.reading_history if record["path"] != abs_path]
        
        # 保存书架数据
        self.save()
    
    @debug_logged
    def scan_directory(self, directory: str) -> Tuple[int, List[str]]:
        """
        扫描目录并添加书籍（并发 + 限速）
        
        Args:
            directory: 目录路径
            
        Returns:
            Tuple[int, List[str]]: (添加的书籍数量, 失败的文件列表)
        """
        if not os.path.isdir(directory):
            logger.error(f"目录不存在: {directory}")
            return 0, []
        
        # 收集待处理文件（仅支持的格式）
        to_process: List[str] = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in SUPPORTED_FORMATS:
                    to_process.append(file_path)
        if not to_process:
            logger.info(f"目录 {directory} 无可导入文件")
            return 0, []
        
        # 默认并发与速率
        try:
            max_workers = min(8, max(2, (os.cpu_count() or 4)))
        except Exception:
            max_workers = 4
        rate_per_sec = 10  # 每秒最多处理文件数，可按需调节
        
        # 令牌桶限速
        import time
        import threading
        tokens = {"count": float(rate_per_sec), "last": time.monotonic()}
        lock = threading.Lock()
        def acquire_token():
            while True:
                with lock:
                    now = time.monotonic()
                    elapsed = now - tokens["last"]
                    if elapsed > 0:
                        tokens["count"] = min(float(rate_per_sec), tokens["count"] + elapsed * rate_per_sec)
                        tokens["last"] = now
                    if tokens["count"] >= 1.0:
                        tokens["count"] -= 1.0
                        return
                time.sleep(0.02)
        
        added_count = 0
        failed_files: List[str] = []
        import concurrent.futures
        
        def worker(fp: str) -> bool:
            try:
                acquire_token()
                return bool(self.add_book(fp))
            except Exception as e:
                logger.error(f"添加书籍时出错: {e}")
                return False
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(worker, fp): fp for fp in to_process}
            for fut in concurrent.futures.as_completed(futures):
                fp = futures[fut]
                try:
                    ok = fut.result()
                    if ok:
                        added_count += 1
                    else:
                        failed_files.append(fp)
                except Exception:
                    failed_files.append(fp)
        
        logger.info(f"已从目录 {directory} 添加 {added_count} 本书籍")
        return added_count, failed_files
    
    def batch_set_author(self, book_paths: List[str], author: str) -> int:
        """
        批量设置作者
        
        Args:
            book_paths: 书籍路径列表
            author: 作者名称
            
        Returns:
            int: 成功设置的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            abs_path = os.path.abspath(path)
            if abs_path in self.books:
                book = self.books[abs_path]
                book.author = author
                # 直接更新数据库
                if self.db_manager.update_book(book):
                    success_count += 1
        
        return success_count

    def extract_author_from_path(self, path: str) -> Optional[str]:
        """
        从书籍文件中尝试提取作者（非 .txt/.md 适用；pdf 支持加密后解密再获取）。
        成功返回作者字符串，失败返回 None（静默）。
        """
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in ('.txt', '.md'):
                return None
            return self._try_extract_author(os.path.abspath(path), ext)
        except Exception:
            return None

    def maybe_update_author(self, book: Book) -> bool:
        """
        若书籍作者为空或为“未知作者”，从文件尝试提取作者并更新数据库。
        成功更新返回 True；未更新或失败返回 False（静默）。
        """
        try:
            current = (book.author or "").strip()
            if current and current != "未知作者":
                return False
            if not book.path or not os.path.exists(book.path):
                return False
            author = self.extract_author_from_path(book.path)
            if author and author != "未知作者":
                book.author = author
                try:
                    return bool(self.db_manager.update_book(book))
                except Exception:
                    return False
            return False
        except Exception:
            return False

    def _safe_async_parse(self, coro_func, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """
        安全调用解析器的异步 parse：
        - 若当前无事件循环：新建 event loop 并运行
        - 若当前有事件循环：在线程池中新建 loop 执行，避免跨 loop 错误
        """
        try:
            import asyncio
            try:
                asyncio.get_running_loop()
                # 已在事件循环内：用线程运行新的事件循环
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    def _run():
                        loop = asyncio.new_event_loop()
                        try:
                            asyncio.set_event_loop(loop)
                            return loop.run_until_complete(coro_func(*args, **kwargs))
                        finally:
                            loop.close()
                    return executor.submit(_run).result(timeout=120)
            except RuntimeError:
                # 无事件循环：直接运行
                loop = asyncio.new_event_loop()
                try:
                    import asyncio as _aio
                    _aio.set_event_loop(loop)
                    return loop.run_until_complete(coro_func(*args, **kwargs))
                finally:
                    loop.close()
        except Exception as e:
            logger.debug(f"安全异步解析失败: {e}")
            return None

    def _try_extract_author(self, abs_path: str, ext: str) -> Optional[str]:
        """
        尝试通过对应解析器解析文件元数据以获取作者：
        - pdf：优先用 PyPDF2 检测是否加密；加密则用 PdfEncryptParser 触发解密流程
        - epub/mobi/azw/azw3：用相应解析器
        - 任何异常/失败均返回 None
        """
        try:
            parser = None
            # PDF 分支：先检测加密
            if ext == '.pdf':
                try:
                    import PyPDF2
                    with open(abs_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        is_encrypted = bool(getattr(reader, "is_encrypted", False))
                except Exception:
                    is_encrypted = False
                if is_encrypted:
                    # 加密PDF不在后台解析作者，避免触发密码弹窗
                    result = None
                else:
                    try:
                        from src.parsers.pdf_parser import PdfParser
                        parser = PdfParser()
                        result = self._safe_async_parse(parser.parse, abs_path)
                    except Exception:
                        result = None
            elif ext == '.epub':
                try:
                    from src.parsers.epub_parser import EpubParser
                    parser = EpubParser()
                    result = self._safe_async_parse(parser.parse, abs_path)
                except Exception:
                    result = None
            elif ext == '.mobi':
                try:
                    from src.parsers.mobi_parser import MobiParser
                    parser = MobiParser()
                    result = self._safe_async_parse(parser.parse, abs_path)
                except Exception:
                    result = None
            elif ext in ('.azw', '.azw3'):
                try:
                    from src.parsers.azw_parser import AzwParser
                    parser = AzwParser()
                    result = self._safe_async_parse(parser.parse, abs_path)
                except Exception:
                    result = None
            else:
                result = None

            if isinstance(result, dict):
                # 先看顶层 author
                auth = result.get("author")
                if isinstance(auth, str) and auth.strip() and auth.strip() != "未知作者":
                    return auth.strip()
                # 再看 metadata.author
                meta = result.get("metadata")
                if isinstance(meta, dict):
                    auth2 = meta.get("author")
                    if isinstance(auth2, str) and auth2.strip() and auth2.strip() != "未知作者":
                        return auth2.strip()
            return None
        except Exception:
            return None
    
    def batch_set_tags(self, book_paths: List[str], tags: List[str]) -> int:
        """
        批量设置标签
        
        Args:
            book_paths: 书籍路径列表
            tags: 标签列表
            
        Returns:
            int: 成功设置的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            abs_path = os.path.abspath(path)
            if abs_path in self.books:
                book = self.books[abs_path]
                # 将标签列表转换为逗号分隔的字符串
                book.tags = ",".join(tags) if tags else ""
                # 直接更新数据库
                if self.db_manager.update_book(book):
                    success_count += 1
        
        return success_count
    

    
    def batch_delete_books(self, book_paths: List[str]) -> int:
        """
        批量删除书籍
        
        Args:
            book_paths: 书籍路径列表
            
        Returns:
            int: 成功删除的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            if self.remove_book(path):
                success_count += 1
        
        return success_count
    
    def batch_clear_history(self, book_paths: List[str]) -> int:
        """
        批量清除阅读历史记录
        
        Args:
            book_paths: 书籍路径列表
            
        Returns:
            int: 成功清除历史记录的书籍数量
        """
        success_count = 0
        
        for path in book_paths:
            abs_path = os.path.abspath(path)
            initial_count = len(self.reading_history)
            self.clear_reading_history(abs_path)
            if len(self.reading_history) < initial_count:
                success_count += 1
        
        return success_count
    
    @debug_logged
    def export_data(self, export_path: str) -> bool:
        """
        导出书架数据
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 从数据库获取所有书籍
            books = self.db_manager.get_all_books()
            # 从数据库获取阅读历史
            reading_history = self.db_manager.get_reading_history()
            
            export_data = {
                "books": [book.to_dict() for book in books],
                "reading_history": reading_history,
                "export_time": datetime.now().isoformat()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"书架数据已导出到: {export_path}")
            return True
        except Exception as e:
            logger.error(f"导出书架数据时出错: {e}")
            return False
    
    @debug_logged
    def import_data(self, import_path: str) -> Tuple[int, int]:
        """
        导入书架数据
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            Tuple[int, int]: (导入的书籍数量, 导入的历史记录数量)
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 导入书籍
            books_added = 0
            for book_data in import_data.get("books", []):
                try:
                    # 检查文件是否存在
                    if not os.path.exists(book_data["path"]):
                        logger.warning(f"书籍文件不存在，跳过: {book_data['path']}")
                        continue
                        
                    book = Book.from_dict(book_data)
                    # 添加到数据库
                    if self.db_manager.add_book(book):
                        # 更新内存字典（用于向后兼容）
                        self.books[book.path] = book
                        books_added += 1
                except Exception as e:
                    logger.error(f"导入书籍时出错: {e}")
            
            # 导入阅读历史记录
            history_added = 0
            for record in import_data.get("reading_history", []):
                if record not in self.reading_history:
                    self.reading_history.append(record)
                    # 添加到数据库
                    if self.db_manager.add_reading_record(
                        record["book_path"], 
                        record.get("duration", 0),
                        record.get("pages_read", 0)
                    ):
                        history_added += 1
            
            logger.info(f"已导入 {books_added} 本书籍和 {history_added} 条阅读历史记录")
            return books_added, history_added
        except Exception as e:
            logger.error(f"导入书架数据时出错: {e}")
            return 0, 0

    def batch_clear_tags(self, book_paths: List[str]) -> int:
        """批量清空标签
        
        Args:
            book_paths: 书籍路径列表
            
        Returns:
            int: 成功清空标签的书籍数量
        """
        if not book_paths:
            return 0
            
        success_count = 0
        # 更新数据库，清空标签
        for book_path in book_paths:
            abs_path = os.path.abspath(book_path)
            if abs_path in self.books:
                book = self.books[abs_path]
                book.tags = ""  # 清空标签，设置为空字符串
                # 直接更新数据库
                if self.db_manager.update_book(book):
                    success_count += 1
        
        return success_count

    def verify_and_remove_missing_books(self) -> Tuple[int, List[str]]:
        """
        验证并删除不存在的书籍
        
        Returns:
            Tuple[int, List[str]]: (删除的书籍数量, 删除的书籍路径列表)
        """
        removed_count = 0
        removed_books = []
        
        # 获取所有书籍
        all_books = self.get_all_books()
        
        for book in all_books:
            if not os.path.exists(book.path):
                # 书籍文件不存在，删除该书籍
                if self.remove_book(book.path):
                    removed_count += 1
                    removed_books.append(book.path)
                    logger.info(f"删除不存在书籍: {book.title} ({book.path})")
        
        logger.info(f"验证完成: 删除了 {removed_count} 本不存在的书籍")
        return removed_count, removed_books

    # 伪用户系统：设置当前用户
    def set_current_user(self, user_id: Optional[int], role: str = "user") -> None:
        self.current_user_id = user_id
        self.current_user_role = role or "user"
        # 切换用户后，刷新书籍加载
        try:
            self._load_books()
        except Exception:
            pass