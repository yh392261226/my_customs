"""
扫描进度对话框，显示目录扫描的进度和结果
"""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, ProgressBar
from textual import events, work

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.book_manager import BookManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class ScanProgressDialog(ModalScreen[Dict[str, Any]]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """扫描进度对话框"""
    
    def __init__(self, theme_manager: ThemeManager, 
                 book_manager: BookManager, directory: str):
        """
        初始化扫描进度对话框
        
        Args:
            theme_manager: 主题管理器
            book_manager: 书籍管理器实例
            directory: 要扫描的目录路径
        """
        super().__init__()
        self.i18n = get_global_i18n()
        self.theme_manager = theme_manager
        self.book_manager = book_manager
        self.directory = directory
        self.scan_result: Optional[Dict[str, Any]] = None
        self.total_files = 0
        self.processed_files = 0
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="scan-progress-dialog"):
            yield Label(get_global_i18n().t("bookshelf.scanning_directory"), id="scan-title")
            yield ProgressBar(total=100, show_eta=False, id="scan-progress")
            yield Static("", id="scan-status")
            yield Static("", id="scan-results")
            
            with Horizontal(id="scan-buttons"):
                yield Button(get_global_i18n().t("common.ok"), id="ok-btn", disabled=True)
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-btn")
    
    def on_mount(self) -> None:
        """挂载时开始扫描并应用主题"""
        self.theme_manager.apply_theme_to_screen(self)
        self.start_scan()
        
    def start_scan(self) -> None:
        """开始扫描目录"""
        def progress_callback(processed: int, total: int):
            """进度回调函数"""
            self.total_files = total
            self.processed_files = processed
            progress_percent = int((processed / total) * 100) if total > 0 else 0
            
            # 在主线程更新进度
            self.app.call_from_thread(lambda: self._update_scan_progress(progress_percent))
            
        def result_callback(added_count: int, failed_files: List[str]):
            """结果回调函数"""
            
            self.scan_result = {
                "added_count": added_count,
                "failed_files": failed_files,
                "success": added_count > 0 or len(failed_files) == 0
            }
            
            # 在主线程更新完成状态
            self.app.call_from_thread(self._update_scan_complete)
            
        # 使用书籍管理器进行扫描
        self.book_manager.scan_directory(
            self.directory,
            progress_callback=progress_callback,
            result_callback=result_callback
        )
        
    def _update_scan_progress(self, progress_percent: int) -> None:
        """更新扫描进度"""
        progress_bar = self.query_one("#scan-progress", ProgressBar)
        progress_bar.update(progress=progress_percent)
        
        status = self.query_one("#scan-status", Static)
        if self.total_files > 0:
            status.update(
                f"{get_global_i18n().t('bookshelf.scanning_directory')} "
                f"({self.processed_files}/{self.total_files})"
            )
    
    def _update_scan_complete(self) -> None:
        """更新扫描完成状态"""
        progress_bar = self.query_one("#scan-progress", ProgressBar)
        progress_bar.advance(100)
        
        status = self.query_one("#scan-status", Static)
        results = self.query_one("#scan-results", Static)
        ok_btn = self.query_one("#ok-btn", Button)
        
        if self.scan_result:
            status.update(get_global_i18n().t("bookshelf.scan_complete"))
            results_text = get_global_i18n().t("bookshelf.scan_success", count=self.scan_result["added_count"])
            
            if self.scan_result["failed_files"]:
                results_text += f"\n{get_global_i18n().t('bookshelf.scan_failed_files')}: {len(self.scan_result['failed_files'])}"
                
            results.update(results_text)
            ok_btn.disabled = False
    
    def _update_scan_error(self) -> None:
        """更新扫描错误状态"""
        if self.scan_result:
            status = self.query_one("#scan-status", Static)
            results = self.query_one("#scan-results", Static)
            ok_btn = self.query_one("#ok-btn", Button)
            
            status.update(get_global_i18n().t("bookshelf.scan_error", error=self.scan_result.get("error", "未知错误")))
            results.update("")
            ok_btn.disabled = False
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "ok-btn":
            self.dismiss(self.scan_result or {})
        elif event.button.id == "cancel-btn":
            # 取消扫描（需要实现扫描取消逻辑）
            self.dismiss({"cancelled": True})

