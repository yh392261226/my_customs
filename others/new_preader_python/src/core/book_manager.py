"""
书籍管理器，负责处理书籍的添加、扫描和管理操作
遵循面向对象和面向切片的开发思路，保持低耦合和高可扩展性
"""

import os
import shutil

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

    # _organize_imported_file 的特殊返回值：表示「放弃导入该文件」
    # （如目标 _imported 目录已存在同名且更大的文件），调用方不应再按原路径登记。
    _SKIP_IMPORT = object()
    
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
        # 后台补索引任务运行标志（保证全局只有一个补索引任务在跑）
        self._indexing = False
        
        # 初始化搜索引擎
        config = ConfigManager.get_instance().get_config()
        self.search_engine = SearchEngine(config["paths"]["database"])
        
    @LoggerSetup.debug_log
    def add_book(self, file_path: str, title: Optional[str] = None, 
                author: Optional[str] = None, index_content: bool = True) -> Optional[Book]:
        """
        添加单本书籍
        
        Args:
            file_path: 书籍文件路径
            title: 书籍标题
            author: 书籍作者
            index_content: 是否立即为书籍内容建立全文搜索索引。
                批量导入时传 False，交由后台 index_unindexed_books 统一补建，
                避免目录书籍过多时导入卡顿。
            
        Returns:
            Optional[Book]: 添加的书籍对象
        """
        try:
            # 验证文件路径
            if not self._validate_file_path(file_path):
                logger.warning(f"无效的文件路径或格式: {file_path}")
                return None

            # 将导入的书籍整理进分层目录（书籍库/来源网站/首字母 或 书籍库/_imported/首字母）
            organized = self._organize_imported_file(file_path)
            if organized is self._SKIP_IMPORT:
                # 同名去重：目标位置已有同名且更大（或等大）的文件，放弃导入
                logger.info(f"跳过重复导入（_imported 已存在同名且不小于该文件的书籍）: {file_path}")
                return None
            if organized:
                file_path = organized

            # 添加书籍到书架
            book = self.bookshelf.add_book(file_path, title, author)
            if book:
                logger.info(f"成功添加书籍: {book.title}")
                
                # 索引书籍内容到搜索数据库（批量导入阶段可跳过，由后台补建）
                if index_content:
                    self._index_book_content(book)
                
                return book
            else:
                logger.warning(f"添加书籍失败: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"添加书籍时发生错误: {e}")
            return None
            
    def _organize_imported_file(self, src_path: str) -> Optional[str]:
        """将导入的书籍文件整理进分层目录，避免单一目录堆积过多文件。

        导入流程的规范位置为 书籍库/_imported/<首字母>/（导入书籍无来源网站）。规则：
        - 已登记且已处于正确分层位置（_imported/<首字母> 或 网站目录）的书籍：不移动。
        - 已登记但仍扁平在书籍库根目录、或位于 _imported 内错字母/错位置的旧书：
          移动到 书籍库/_imported/<首字母>/，并同步更新所有引用该路径的表。
        - 书籍库根目录的扁平新文件：移动到 书籍库/_imported/<首字母>/。
        - 位于 _imported 内错字母/错位置（如直接丢在 _imported 下或错字母目录）的新文件：
          移动到正确字母目录。
        - 位于书籍库之外的新文件：复制到 书籍库/_imported/<首字母>/（保留原文件）。
        - 位于网站(site)目录下的文件：属爬虫管理区域，导入流程不挪动，
          以免把爬虫书籍误判为「导入书籍」而改变其归类。站点目录通过数据库中的
          站点名（novel_sites）计算的目录名来识别。
        - 位于书籍库内其它一级目录（用户临时存放区）下的文件：这些文件可能只是
          临时放在该文件夹中，添加书籍时应移动到 书籍库/_imported/<首字母>/
          规范位置并登记新路径，而不是直接按文件的当前位置入库。
        - 同名去重（主要针对 _imported 目录）：目标位置已存在完全同名文件时比较
          文件大小，保留较大者——新文件更大则覆盖旧文件（路径不变）；新文件不大于
          旧文件则放弃导入（库内临时文件会被删除，库外文件保留原样），并返回
          _SKIP_IMPORT 让调用方按导入失败处理，而不是按当前位置登记。
        返回整理后的新路径；无需移动或失败时返回 None。
        """
        from src.utils.storage_layout import IMPORT_DIR_NAME, get_import_storage_dir

        if not os.path.isfile(src_path):
            return None
        library_root = getattr(self.bookshelf, "data_dir", None)
        if not library_root:
            return None

        abs_src = os.path.abspath(src_path)
        abs_root = os.path.abspath(os.path.expanduser(library_root))

        try:
            rel = os.path.relpath(abs_src, abs_root)
        except ValueError:
            rel = ".." + os.sep
        in_library = not rel.startswith("..")
        parts = rel.split(os.sep)

        # 是否已在书架中登记
        existing_book = None
        try:
            existing_book = self.bookshelf.db_manager.get_book(abs_src)
        except Exception:
            pass

        # 库外文件：仅新文件复制到库内规范位置（已登记的库外书籍不动）
        if not in_library:
            if existing_book:
                return None
            title = os.path.splitext(os.path.basename(abs_src))[0]
            target_dir = get_import_storage_dir(abs_root, title)
            os.makedirs(target_dir, exist_ok=True)
            target = os.path.join(target_dir, os.path.basename(abs_src))
            import_new, target = self._resolve_import_name_conflict(abs_src, target)
            if not import_new:
                return self._SKIP_IMPORT
            try:
                shutil.copy2(abs_src, target)
                logger.info(f"导入书籍已整理进分层目录: {abs_src} -> {target}")
                return target
            except Exception as e:
                logger.error(f"整理导入书籍失败: {e}")
                return None

        # 库内文件：top 为相对 library_root 的第一级目录名（扁平文件则为 None）
        top = parts[0] if len(parts) > 1 else None

        # 网站(site)目录：属爬虫管理区域，不挪动。站点目录按数据库中的站点名
        # 计算目录名来识别；其它一级目录视为用户的临时存放区，文件可能只是
        # 临时放在那里，添加书籍时应移动到规范分层位置而不是按当前位置登记。
        if top is not None and top != IMPORT_DIR_NAME:
            site_dirs = self._get_known_site_dirnames()
            if site_dirs is None or top in site_dirs:
                return None

        # top 为 None（根目录扁平）或 _imported（需检查字母是否正确）
        title = os.path.splitext(os.path.basename(abs_src))[0]
        canon_dir = get_import_storage_dir(abs_root, title)

        # 已在 _imported 的正确字母目录中：无需移动
        if top == IMPORT_DIR_NAME and os.path.abspath(os.path.dirname(abs_src)) == os.path.abspath(canon_dir):
            return None

        os.makedirs(canon_dir, exist_ok=True)
        target = os.path.join(canon_dir, os.path.basename(abs_src))
        import_new, target = self._resolve_import_name_conflict(abs_src, target)
        if not import_new:
            # 同名且新文件不大于现有文件：保留现有大文件，把较小的新文件移入回收站
            # （而非真正删除），以便用户在回收站中恢复。仅针对未在书架登记的文件。
            if not existing_book:
                try:
                    from src.core.recycle_bin import get_recycle_bin
                    rb = get_recycle_bin(self.bookshelf.db_manager)
                    moved = rb.trash_file(
                        abs_src, operation="import_dedup",
                        reason="导入去重：新文件不大于已存在同名文件",
                    )
                except Exception as rb_err:
                    moved = False
                    logger.warning(f"导入去重移入回收站失败，回退为真删: {abs_src}: {rb_err}")
                if not moved:
                    try:
                        os.remove(abs_src)
                        logger.info(f"同名书籍现有文件更大，已丢弃较小的新文件: {abs_src}")
                    except OSError as e:
                        logger.warning(f"丢弃较小的新文件失败（忽略）: {abs_src}: {e}")
            return self._SKIP_IMPORT
        try:
            shutil.move(abs_src, target)
        except Exception as e:
            logger.error(f"整理导入书籍失败: {e}")
            return None

        # 若书籍已在书架登记（此前可能以扁平/错位置路径入库），同步更新所有引用路径
        if existing_book:
            try:
                self._update_book_path_everywhere(abs_src, target)
            except Exception as e:
                logger.error(f"更新书籍路径失败: {e}")

        logger.info(f"导入书籍已整理进分层目录: {abs_src} -> {target}")
        return target

    def _resolve_import_name_conflict(self, abs_src: str, target: str) -> Tuple[bool, Optional[str]]:
        """处理导入目标位置已存在完全同名文件的冲突（主要针对 _imported 目录）。

        文件名完全相同时比较文件大小，保留较大者：
        - 目标不存在同名文件：直接导入，返回 (True, target)。
        - 新文件更大：删除目标位置的旧文件后仍用原路径导入，返回 (True, target)，
          已登记书籍的路径无需变更，下次打开即为新内容。
        - 新文件不大于旧文件（更小或等大，视为重复）：放弃导入，返回 (False, None)。
        - 大小比较或删除旧文件失败：保守起见放弃导入，返回 (False, None)。
        """
        if abs_src == os.path.abspath(target) or not os.path.exists(target):
            return True, target
        try:
            new_size = os.path.getsize(abs_src)
            old_size = os.path.getsize(target)
        except OSError as e:
            logger.error(f"比较同名文件大小失败，放弃导入: {abs_src} vs {target}: {e}")
            return False, None
        if new_size <= old_size:
            logger.info(
                f"目标位置已存在同名文件且不小于新文件，跳过导入: "
                f"{abs_src} ({new_size}B) <= {target} ({old_size}B)"
            )
            return False, None
        try:
            from src.core.recycle_bin import get_recycle_bin
            rb = get_recycle_bin(self.bookshelf.db_manager)
            # 旧文件若已在书架登记，走 trash_book（会一并快照其关联数据）；
            # 否则仅作为未登记文件移入回收站。两者都保留物理文件以便恢复。
            old_book = self.bookshelf.db_manager.get_book(target)
            if old_book is not None:
                moved = rb.trash_book(
                    target, delete_file=True, operation="import_replace",
                    reason="导入替换：新文件更大，旧文件入回收站",
                    rename_in_place=True,
                )
            else:
                moved = rb.trash_file(
                    target, operation="import_replace",
                    reason="导入替换：新文件更大，旧文件入回收站",
                    rename_in_place=True,
                )
        except Exception as rb_err:
            moved = False
            logger.warning(f"导入替换移入回收站失败，回退为真删: {target}: {rb_err}")
        if not moved:
            try:
                os.remove(target)
            except OSError as e:
                logger.error(f"删除同名旧文件失败，放弃导入: {target}: {e}")
                return False, None
        logger.info(
            f"目标位置已存在同名文件但新文件更大，覆盖旧文件: "
            f"{abs_src} ({new_size}B) -> {target} ({old_size}B)"
        )
        return True, target

    def _get_known_site_dirnames(self) -> Optional[set]:
        """返回所有爬虫站点对应的书籍库一级目录名（用于识别爬虫管理区域）。

        爬虫书籍存储在 书籍库/<站点目录名>/<首字母>/ 下，站点目录名由站点名
        经 safe_site_dirname 计算得到。查询失败时返回 None，调用方应保守地
        不挪动任何非 _imported 一级目录下的文件，避免误移爬虫书籍。
        """
        try:
            from src.utils.storage_layout import safe_site_dirname
            sites = self.bookshelf.db_manager.get_novel_sites() or []
            return {
                safe_site_dirname(s.get("name") or "")
                for s in sites if (s.get("name") or "").strip()
            }
        except Exception as e:
            logger.error(f"获取站点目录名失败: {e}")
            return None

    def _update_book_path_everywhere(self, old_path: str, new_path: str) -> None:
        """将书籍在数据库各表中的路径引用由 old_path 更新为 new_path。"""
        db = self.bookshelf.db_manager
        book = db.get_book(old_path)
        if book is not None:
            try:
                book.path = new_path
                db.update_book(book, old_path)
            except Exception as e:
                logger.error(f"更新 books 表路径失败: {e}")
        try:
            db.update_user_books_path(old_path, new_path)
            db.update_reading_history_path(old_path, new_path)
            db.update_bookmarks_path(old_path, new_path)
            db.update_book_metadata_path(old_path, new_path)
            db.update_vocabulary_path(old_path, new_path)
            db.update_crawl_history_path(old_path, new_path)
        except Exception as e:
            logger.error(f"更新关联表路径失败: {e}")

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
        
    def index_unindexed_books(self,
                              start_callback: Optional[Callable[[], None]] = None,
                              progress_callback: Optional[Callable[[int, int], None]] = None,
                              done_callback: Optional[Callable[[], None]] = None) -> None:
        """
        后台为所有尚未建立全文搜索索引的书籍补建索引（幂等、可重入）。
        
        批量导入时 add_book 传入 index_content=False 跳过即时索引，由本方法在
        后台统一补建，避免目录书籍过多时导入卡顿。可通过回调反馈进度。
        """
        if self._indexing:
            return
        # 快速预检：无未索引书籍则直接返回，避免无谓的动画闪烁与线程开销
        try:
            todo = self._get_unindexed_books()
        except Exception as e:
            logger.error(f"获取未索引书籍列表失败: {e}")
            todo = []
        if not todo:
            return
        
        self._indexing = True
        if start_callback:
            try:
                start_callback()
            except Exception:
                pass
        total = len(todo)
        
        def task() -> None:
            try:
                for i, book in enumerate(todo):
                    try:
                        self._index_book_content(book)
                    except Exception as e:
                        logger.error(f"后台索引书籍失败 {book.path}: {e}")
                    if progress_callback:
                        try:
                            progress_callback(i + 1, total)
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"后台索引任务出错: {e}")
            finally:
                self._indexing = False
                if done_callback:
                    try:
                        done_callback()
                    except Exception:
                        pass
        
        threading.Thread(target=task, daemon=True).start()
    
    def _get_unindexed_books(self) -> List[Book]:
        """返回书架中尚未建立全文搜索索引的书籍列表（基于一次查询，避免逐本查询）"""
        indexed = self.search_engine.get_indexed_book_ids()
        return [b for b in self.bookshelf.get_all_books()
                if b.path and b.path not in indexed]
    
    def get_unindexed_count(self) -> int:
        """返回尚未建立全文搜索索引的书籍数量"""
        try:
            return len(self._get_unindexed_books())
        except Exception as e:
            logger.error(f"获取未索引书籍数量失败: {e}")
            return 0
    
    @property
    def is_indexing(self) -> bool:
        """后台补索引/重建索引任务是否正在运行"""
        return self._indexing
    
    def rebuild_index(self,
                      start_callback: Optional[Callable[[], None]] = None,
                      progress_callback: Optional[Callable[[int, int], None]] = None,
                      done_callback: Optional[Callable[[], None]] = None) -> None:
        """
        重建全文搜索索引：清空已有索引后重新为所有书籍建立索引。
        适用于索引损坏或不一致时手动触发；清空后若中途退出，下次启动会自动继续补建。
        """
        if self._indexing:
            return
        try:
            self.search_engine.clear_index()
        except Exception as e:
            logger.error(f"清空搜索索引失败: {e}")
        # 清空后所有书籍均视为未索引，复用后台补索引逻辑
        self.index_unindexed_books(start_callback, progress_callback, done_callback)
    
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