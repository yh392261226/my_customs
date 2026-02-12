"""
爬取管理屏幕
"""

import os
import glob
import subprocess
import platform
import asyncio
from send2trash import send2trash
from typing import Dict, Any, Optional, List, ClassVar, Set
from urllib.parse import unquote
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, Input, Link, Header, Footer, LoadingIndicator, Select
from textual.widgets import DataTable, Log
from textual.app import ComposeResult
from textual import events, on
from textual.screen import ModalScreen
from textual.containers import Center, Middle, Horizontal, Vertical

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger
from src.ui.dialogs.note_dialog import NoteDialog
from src.ui.dialogs.select_books_dialog import SelectBooksDialog
from src.utils.browser_tab_monitor import BrowserTabMonitor, BrowserType
from src.config.config_manager import ConfigManager
import threading
import time

logger = get_logger(__name__)

class LogViewerPopup(ModalScreen):
    """日志查看器弹窗"""
    
    BINDINGS = [("escape", "close", get_global_i18n().t('crawler.close_popup')),
            ("q", "force_close", get_global_i18n().t('crawler.force_close')),
            ("e", "scroll_to_bottom", get_global_i18n().t('crawler.scroll_to_bottom')),
            ("c", "sync_close", get_global_i18n().t('crawler.sync_close'))]  # 将在__init__中动态设置
    
    DEFAULT_CSS = """
    LogViewerPopup {
        height: 80%;
        width: 80%;
        align: center middle;
    }
    
    LogViewerPopup > Container {
        width: 90%;  /* 从85%增加到90% */
        height: 90%;  /* 从85%增加到90% */
        align: center middle;
        background: $surface;
        border: solid $accent;
    }
    
    .log-popup-container {
        width: 85%;
        height: 85%;
        align: center middle;
        layout: vertical;
    }
    
    .log-popup-header {
        height: 1;  /* 从3行减少到2行 */
        background: $accent;
        color: $text;
        content-align: center middle;
    }
    
    .log-popup-controls {
        height: 4;  /* 从3行减少到2行 */
        margin: 0 0 1 0;
    }

    #close-log-btn, #toggle-scroll-btn, #clear-log-btn, #refresh-log-btn {
        margin: 0;
        padding: 0;
        border: none;
        height: 3;
    }
    
    .log-popup-content {
        height: 55%;  /* 使用弹性布局占据剩余空间 */
        background: $background;
    }
    
    #log-viewer {
        width: 100%;
        height: 40%;
        background: $background;
        /* 增加内边距确保显示完整内容 */
        padding: 5 1 5 1;  /* 上 右 下 左 - 增加底部内边距 */
        border: solid $border;
        overflow: auto;
    }
    """
    
    def __init__(self, log_file_path: str):
        super().__init__()
        self.log_file_path = log_file_path
        self.auto_scroll = True
        self.last_position = 0
        self.file_watcher_task = None
        self.stop_watching = False
        
    def compose(self) -> ComposeResult:
        """组合日志查看器界面"""
        yield Header()
        yield Container(
            Vertical(
                # 标题栏
                Horizontal(
                    Label(f"📋 {get_global_i18n().t('crawler.viewing_logs')}: {os.path.basename(self.log_file_path)}", classes="log-popup-title"),
                    classes="log-popup-header"
                ),
                
                # 控制按钮
                Horizontal(
                    Button(get_global_i18n().t('common.close'), id="close-log-btn", variant="primary"),
                    Button(get_global_i18n().t('crawler.toggle_auto_scroll'), id="toggle-scroll-btn", variant="default"),
                    Button(get_global_i18n().t('crawler.clear_display'), id="clear-log-btn", variant="warning"),
                    Button(get_global_i18n().t('crawler.refresh_log'), id="refresh-log-btn", variant="success"),
                    classes="log-popup-controls"
                ),
                
                # 日志内容区域
                
                Log(id="log-viewer", auto_scroll=True, max_lines=1000, classes="log-popup-content"),
                
                classes="log-popup-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """弹窗挂载时的回调"""
        self._load_initial_log_content()
        self._start_file_watching()
        
        # 设置焦点到关闭按钮，方便操作
        try:
            self.query_one("#close-log-btn", Button).focus()
        except Exception:
            pass
        
        # 确保滚动到底部（考虑滚动条影响），更快响应
        self.set_timer(0.05, self._ensure_scroll_to_bottom)
    
    async def on_unmount(self) -> None:
        """弹窗卸载时的回调"""
        await self._stop_file_watching()
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下事件处理"""
        if event.button.id == "close-log-btn":
            # 异步关闭
            asyncio.create_task(self._async_close())
        elif event.button.id == "toggle-scroll-btn":
            self._toggle_auto_scroll()
        elif event.button.id == "clear-log-btn":
            self._clear_log_content()
        elif event.button.id == "refresh-log-btn":
            self._refresh_log_content()
    
    async def _async_close(self) -> None:
        """异步关闭弹窗"""
        try:
            await self._stop_file_watching()
            self.dismiss()
        except Exception as e:
            logger.error(f"关闭日志查看器失败: {e}")
            # 强制关闭
            self._force_close()
    
    def _load_initial_log_content(self) -> None:
        """加载初始日志内容"""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    log_viewer = self.query_one("#log-viewer", Log)
                    log_viewer.clear()
                    # 只显示最后1000行
                    lines = content.split('\n')
                    if len(lines) > 1000:
                        lines = lines[-1000:]
                    log_viewer.write('\n'.join(lines))
                    
                    # 记录当前位置
                    self.last_position = len(content.encode('utf-8'))
                    
                    # 滚动到底部
                    if self.auto_scroll:
                        # 减少延迟，更快响应，并滚动到真正的底部
                        self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
                        # 再次确保滚动到绝对底部
                        self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
            else:
                log_viewer = self.query_one("#log-viewer", Log)
                log_viewer.write(f"📁 {get_global_i18n().t('crawler.log_file_not_found')}: {self.log_file_path}")
        except Exception as e:
            logger.error(f"加载日志内容失败: {e}")
            log_viewer = self.query_one("#log-viewer", Log)
            log_viewer.write(f"❌ {get_global_i18n().t('crawler.load_log_failed')}: {e}")
    
    def _start_file_watching(self) -> None:
        """启动文件监控任务"""
        self.stop_watching = False
        self.file_watcher_task = asyncio.create_task(self._watch_file_changes())
    
    async def _stop_file_watching(self) -> None:
        """停止文件监控"""
        try:
            self.stop_watching = True
            if self.file_watcher_task and not self.file_watcher_task.done():
                # 取消任务，等待它完成
                self.file_watcher_task.cancel()
                try:
                    await asyncio.wait_for(self.file_watcher_task, timeout=0.1)
                except asyncio.CancelledError:
                    pass  # 任务被正常取消
                except asyncio.TimeoutError:
                    pass  # 超时也没关系，任务会被取消
        except Exception as e:
            logger.error(f"停止文件监控失败: {e}")
            # 不抛出异常，继续关闭流程
    
    async def _watch_file_changes(self) -> None:
        """异步监控文件变化"""
        while not self.stop_watching:
            try:
                # 检查是否应该停止
                if self.stop_watching:
                    break
                    
                if os.path.exists(self.log_file_path):
                    current_size = os.path.getsize(self.log_file_path)
                    if current_size > self.last_position:
                        # 文件有新内容
                        with open(self.log_file_path, 'r', encoding='utf-8') as f:
                            f.seek(self.last_position)
                            new_content = f.read()
                            
                            # 更新UI（在主线程中）
                            try:
                                log_viewer = self.query_one("#log-viewer", Log)
                                log_viewer.write(new_content)
                                if self.auto_scroll:
                                    # 减少延迟，更快响应，滚动到绝对底部
                                    self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
                                    # 再次确保滚动到真正的底部
                                    self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
                            except Exception:
                                # 弹窗可能已经关闭，停止监控
                                self.stop_watching = True
                                break
                            
                            self.last_position = current_size
                else:
                    self.last_position = 0
                    
            except Exception as e:
                logger.error(f"监控日志文件变化失败: {e}")
                # 出错时也停止监控，避免无限循环
                self.stop_watching = True
                break
            
            # 使用更短的异步睡眠，可以被取消，提高响应速度
            try:
                await asyncio.sleep(0.2)  # 从0.5秒减少到0.2秒
            except asyncio.CancelledError:
                break
    
    def _toggle_auto_scroll(self) -> None:
        """切换自动滚动"""
        self.auto_scroll = not self.auto_scroll
        log_viewer = self.query_one("#log-viewer", Log)
        log_viewer.auto_scroll = self.auto_scroll
        
        # 更新按钮文本
        toggle_btn = self.query_one("#toggle-scroll-btn", Button)
        toggle_btn.label = f"{get_global_i18n().t('crawler.auto_scroll')}: {'开' if self.auto_scroll else '关'}"
        
        if self.auto_scroll:
            self.app.notify(get_global_i18n().t('crawler.auto_scroll_enabled'))
            # 立即滚动到底部，考虑滚动条影响，更快响应
            self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
            # 再次确保滚动到真正的底部
            self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
        else:
            self.app.notify(get_global_i18n().t('crawler.auto_scroll_disabled'))
        
        # 如果开启自动滚动，立即滚动到底部
        if self.auto_scroll:
            log_viewer.scroll_end(animate=False)
    
    def _clear_log_content(self) -> None:
        """清空日志内容显示"""
        log_viewer = self.query_one("#log-viewer", Log)
        log_viewer.clear()
        log_viewer.write(f"📝 {get_global_i18n().t('crawler.log_cleared_message')}")
    
    def _refresh_log_content(self) -> None:
        """刷新日志内容"""
        self.last_position = 0  # 重置位置，重新加载全部内容
        self._load_initial_log_content()
        self.app.notify(f"📋 {get_global_i18n().t('crawler.log_refreshed')}")
        
    async def action_close(self) -> None:
        """关闭弹窗"""
        try:
            await self._stop_file_watching()
            self.dismiss()
            # 显示关闭提示
            self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
        except Exception as e:
            logger.error(f"关闭日志查看器失败: {e}")
            # 强制关闭
            await self._force_close()
    
    async def action_force_close(self) -> None:
        """强制关闭弹窗"""
        await self._force_close()
    
    async def _force_close(self) -> None:
        """强制关闭弹窗的内部方法"""
        try:
            self.stop_watching = True
            if self.file_watcher_task and not self.file_watcher_task.done():
                # 取消异步任务
                self.file_watcher_task.cancel()
                # 等待任务真正取消
                try:
                    await asyncio.wait_for(self.file_watcher_task, timeout=0.1)
                except asyncio.TimeoutError:
                    pass  # 超时也没关系，继续关闭
            self.dismiss()
            # 显示强制关闭提示
            self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
        except Exception as e:
            logger.error(f"{get_global_i18n().t('crawler.force_close_failed')}: {e}")
            # 最后的手段：直接移除
            try:
                self.remove()
                # 即使移除也显示提示
                self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
            except Exception:
                pass  # 最后的手段失败，什么都不做
    
    def action_sync_close(self) -> None:
        """同步关闭弹窗（备用方法）"""
        try:
            self.stop_watching = True
            # 不等待异步任务，直接关闭
            self.dismiss()
            # 显示同步关闭提示
            self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
        except Exception as e:
            logger.error(f"{get_global_i18n().t('crawler.sync_close_failed')}: {e}")
            try:
                self.remove()
                # 即使移除也显示提示
                self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
            except Exception:
                pass
    
    def _ensure_scroll_to_bottom(self) -> None:
        """确保滚动到底部的内部方法"""
        try:
            log_viewer = self.query_one("#log-viewer", Log)
            log_viewer.scroll_end(animate=False)
        except Exception:
            pass
    
    def action_scroll_to_bottom(self) -> None:
            """手动滚动到底部"""
            try:
                log_viewer = self.query_one("#log-viewer", Log)
                # 立即滚动，然后再次确保滚动到绝对底部，更快响应
                log_viewer.scroll_end(animate=False)
                self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
                self.app.notify(get_global_i18n().t('crawler.scrolled_to_bottom'))
            except Exception as e:
                logger.error(f"{get_global_i18n().t('crawler.scroll_to_bottom_failed')}: {e}")


class CrawlerManagementScreen(Screen[None]):
    """爬取管理屏幕"""
    
    CSS_PATH = ["../styles/utilities.tcss", "../styles/crawler_management_overrides.tcss"]
    TITLE: ClassVar[Optional[str]] = None
    # 统一快捷键绑定（含 ESC 返回）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("o", "open_browser", get_global_i18n().t('crawler.shortcut_o')),
        ("r", "view_history", get_global_i18n().t('crawler.shortcut_r')),
        ("b", "note", get_global_i18n().t('crawler.shortcut_b')),
        ("l", "view_logs", get_global_i18n().t('crawler.view_logs')),
        ("escape", "back", get_global_i18n().t('common.back')),
        ("X", "select_books", get_global_i18n().t('crawler.select_books')),
        ("s", "start_crawl", get_global_i18n().t('crawler.shortcut_s')),
        ("v", "stop_crawl", get_global_i18n().t('crawler.shortcut_v')),
        ("p", "prev_page", get_global_i18n().t('crawler.shortcut_p')),
        ("n", "next_page", get_global_i18n().t('crawler.shortcut_n')),
        ("x", "clear_search_params", get_global_i18n().t('crawler.clear_search_params')),
        ("j", "jump_to", get_global_i18n().t('bookshelf.jump_to')),
        ("space", "toggle_row", get_global_i18n().t('batch_ops.toggle_row')),
    ]

    def action_open_browser(self) -> None:
        self._open_browser()
        self._update_status(get_global_i18n().t('crawler.browser_opened'), "warning")

    def action_view_history(self) -> None:
        self._view_history()
        self._update_status(get_global_i18n().t('crawler.history_loaded'), "warning")

    def action_start_crawl(self) -> None:
        self._start_crawl()
        self._update_status(get_global_i18n().t('crawler.crawling'), "warning")

    def action_stop_crawl(self) -> None:
        self._stop_crawl()
        self._update_status(get_global_i18n().t('crawler.crawl_stopped'), "warning")

    def action_note(self) -> None:
        self._open_note_dialog()

    def action_view_logs(self) -> None:
        """打开日志查看器弹窗"""
        self._open_log_viewer()

    def action_prev_page(self) -> None:
        self._go_to_prev_page()

    def action_next_page(self) -> None:
        self._go_to_next_page()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_select_books(self) -> None:
        # 如果未开启支持选择书籍，则不做任何处理
        if self.novel_site.get("selectable_enabled", True):
            self._open_select_books_dialog()
        else:
            # 弹窗提示未开启支持选择书籍
            self._update_status(get_global_i18n().t('crawler.disabled_selectable'), "error")
    
    def action_toggle_row(self) -> None:
        """空格键 - 选中或取消选中当前行"""
        # 直接处理空格键，不依赖BINDINGS系统
        table = self.query_one("#crawl-history-table", DataTable)
        
        # 获取当前光标位置
        current_row_index = None
        
        # 首先尝试使用cursor_row
        if hasattr(table, 'cursor_row') and table.cursor_row is not None:
            current_row_index = table.cursor_row
        # 其次尝试使用cursor_coordinate
        elif hasattr(table, 'cursor_coordinate') and table.cursor_coordinate:
            coord = table.cursor_coordinate
            current_row_index = coord.row
        
        # 检查是否有有效的行索引
        if current_row_index is None:
            # 显示提示信息，要求用户先选择一行
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 检查行索引是否在有效范围内
        current_page_row_count = min(self.items_per_page, len(self.crawler_history) - (self.current_page - 1) * self.items_per_page)
        if current_row_index < 0 or current_row_index >= current_page_row_count:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 计算当前页的起始索引
        start_index = (self.current_page - 1) * self.items_per_page
        
        # 检查当前行是否有数据
        if start_index + current_row_index >= len(self.crawler_history):
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 获取当前行的历史记录项
        history_item = self.crawler_history[start_index + current_row_index]
        if not history_item:
            return
        
        # 获取记录ID
        record_id = str(history_item["id"])
        
        # 切换选中状态
        if record_id in self.selected_history:
            self.selected_history.remove(record_id)
        else:
            self.selected_history.add(record_id)
        
        # 更新表格显示
        self._update_history_table()
        
        # 更新状态显示
        selected_count = len(self.selected_history)
        self._update_status(get_global_i18n().t('crawler.already_selected', count=selected_count), "information")
        
        # 确保表格保持焦点
        try:
            table.focus()
        except Exception:
            pass

    def action_clear_search_params(self) -> None:
        """清除搜索参数"""
        self.query_one("#search-input-field", Input).value = ""
        self.query_one("#search-input-field", Input).placeholder = get_global_i18n().t('crawler.search_placeholder')

    def action_jump_to(self) -> None:
        self._show_jump_dialog()

    def _toggle_site_selection(self, table: DataTable, current_row_index: int) -> None:
        """切换网站选中状态（参考批量操作页面的实现）"""
        try:
            # 计算当前页面的起始索引和全局索引
            start_index = (self.current_page - 1) * self.items_per_page
            
            # 检查当前行是否有数据
            if start_index + current_row_index >= len(self.crawler_history):
                return
            
            # 获取当前行的历史记录项
            history_item = self.crawler_history[start_index + current_row_index]
            if not history_item:
                return
            
            # 获取记录ID
            record_id = str(history_item["id"])
            
            # 切换选中状态
            if record_id in self.selected_history:
                self.selected_history.remove(record_id)
            else:
                self.selected_history.add(record_id)
            
            # 重新渲染表格以更新选中状态显示
            self._update_history_table()
            
            # 更新状态显示
            selected_count = len(self.selected_history)
            self._update_status(get_global_i18n().t('crawler.already_selected', count=selected_count), "information")
                
        except Exception:
            # 如果出错，重新渲染整个表格
            self._update_history_table()

    def __init__(self, theme_manager: ThemeManager, novel_site: Dict[str, Any]):
        """
        初始化爬取管理屏幕
        
        Args:
            theme_manager: 主题管理器
            novel_site: 书籍网站信息
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.novel_site = novel_site
        self.crawler_history = []  # 爬取历史记录
        self.current_page = 1
        self.items_per_page = 10
        self.total_pages = 0
        self.db_manager = DatabaseManager()  # 数据库管理器
        
        # 后台爬取管理器
        from src.core.crawler_manager import CrawlerManager
        self.crawler_manager = CrawlerManager()
        
        # 爬取状态
        self.current_task_id: Optional[str] = None  # 当前任务ID
        self.is_crawling = False  # 爬取状态标志（用于UI显示）
        # 当前正在爬取的ID（用于状态显示）
        self.current_crawling_id: Optional[str] = None
        self.loading_animation = None  # 加载动画组件
        self.loading_indicator = None  # 原生 LoadingIndicator 引用
        self.is_mounted_flag = False  # 组件挂载标志
        self.title = get_global_i18n().t('crawler.title')
        
        # 多选相关属性
        self.selected_history: Set[str] = set()  # 选中的历史记录ID
        
        # 搜索相关属性
        self._search_keyword = ""  # 搜索关键词
        
        # 排序相关属性
        self._sorted_history: List[str] = []  # 排序后的历史记录ID顺序
        self._sort_column: Optional[str] = None  # 当前排序的列
        self._sort_reverse: bool = True  # 排序方向，True表示倒序

        # 浏览器选择相关属性
        self.selected_browser = "chrome"  # 默认选择Chrome
        self.browser_options = ["chrome", "safari", "brave", "firefox"]
        
        # 浏览器标签页监听器（AppleScript模式）
        self.browser_monitor: Optional[BrowserTabMonitor] = None
        self.browser_monitor_active = False  # 监听器状态
        
        # 注册回调函数
        self.crawler_manager.register_status_callback(self._on_crawl_status_change)
        self.crawler_manager.register_notification_callback(self._on_crawl_success_notify)

    def _load_browser_config(self) -> None:
        """加载浏览器配置"""
        try:
            # 从配置管理器中读取默认浏览器
            try:
                config_manager = ConfigManager.get_instance()
                config = config_manager.get_config()
                default_browser = config.get("browser", {}).get("default_browser", "chrome")
                if default_browser in self.browser_options:
                    self.selected_browser = default_browser
                    logger.info(f"从配置管理器加载默认浏览器: {default_browser}")
                else:
                    logger.warning(f"设置的浏览器 {default_browser} 不在支持列表中，使用默认Chrome")
                    self.selected_browser = "chrome"
            except Exception as e:
                logger.error(f"从配置管理器读取浏览器配置失败: {e}")
                self.selected_browser = "chrome"
        except Exception as e:
            logger.error(f"加载浏览器配置失败: {e}")

    def _save_browser_config(self) -> None:
        """保存浏览器配置"""
        try:
            # 保存到配置管理器中
            try:
                config_manager = ConfigManager.get_instance()
                config = config_manager.get_config()
                
                # 确保 browser 配置节存在
                if "browser" not in config:
                    config["browser"] = {}
                
                config["browser"]["default_browser"] = self.selected_browser
                
                if config_manager.save_config(config):
                    logger.info(f"保存浏览器配置到配置管理器: {self.selected_browser}")
                else:
                    logger.error(f"保存浏览器配置失败: 保存操作返回 False")
            except Exception as e:
                logger.error(f"保存浏览器配置到配置管理器失败: {e}")
        except Exception as e:
            logger.error(f"保存浏览器配置失败: {e}")

    def _get_rating_display(self, rating: int) -> str:
        """
        根据星级评分生成显示字符串
        
        Args:
            rating: 星级评分 (0-5)
            
        Returns:
            str: 星级显示字符串，如 "☆☆☆☆☆" 或 "★★★★★"
        """
        # 确保评分在0-5范围内
        rating = max(0, min(5, rating))
        
        # 使用实心星星表示评分，空心星星表示剩余
        filled_stars = "★" * rating
        empty_stars = "☆" * (5 - rating)
        
        return f"{filled_stars}{empty_stars}"

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限（兼容单/多用户）"""
        try:
            db_manager = self.db_manager if hasattr(self, "db_manager") else DatabaseManager()
            # 获取当前用户ID
            current_user_id = getattr(self.app, 'current_user_id', None)
            if current_user_id is None:
                # 如果没有当前用户，检查是否是多用户模式
                if not getattr(self.app, 'multi_user_enabled', False):
                    # 单用户模式默认允许所有权限
                    return True
                else:
                    # 多用户模式但没有当前用户，默认拒绝
                    return False
            # 传入用户ID与权限键
            return db_manager.has_permission(current_user_id, permission_key)  # type: ignore[misc]
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def compose(self) -> ComposeResult:
        """
        组合爬取管理屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Vertical(
                # Label(f"{get_global_i18n().t('crawler.title')} - {self.novel_site['name']}", id="crawler-title", classes="section-title"),
                Link(f"{self.novel_site['url']}", url=f"{self.novel_site['url']}", id="crawler-url", tooltip=f"{get_global_i18n().t('crawler.click_me')}"),
                # 显示星级评分
                Label(self._get_rating_display(self.novel_site.get('rating', 2)), id="rating-label", classes="rating-display"),
                # 对书籍ID示例进行URL解码，避免显示乱码
                Label(f"{get_global_i18n().t('crawler.book_id_example')}: {unquote(self.novel_site.get('book_id_example', ''))}", id="book-id-example-label"),

                # 顶部操作按钮（固定）
                Horizontal(
                    Button(get_global_i18n().t('crawler.open_browser'), id="open-browser-btn"),
                    Button(get_global_i18n().t('crawler.view_history'), id="view-history-btn"),
                    Button(get_global_i18n().t('crawler.note'), id="note-btn"),
                    Button(get_global_i18n().t('crawler.view_logs'), id="view-logs-btn", variant="success"),
                    Button(get_global_i18n().t('crawler.clear_invalid'), id="clear-invalid-btn", variant="error"),
                    # 多选操作按钮
                    Button(get_global_i18n().t('bookshelf.batch_ops.select_all'), id="select-all-btn"),
                    Button(get_global_i18n().t('bookshelf.batch_ops.invert_selection'), id="invert-selection-btn"),
                    Button(get_global_i18n().t('bookshelf.batch_ops.deselect_all'), id="deselect-all-btn"),
                    Button(get_global_i18n().t('batch_ops.move_up'), id="move-up-btn"),
                    Button(get_global_i18n().t('batch_ops.move_down'), id="move-down-btn"),
                    Button(get_global_i18n().t('batch_ops.merge'), id="merge-btn", variant="warning"),
                    Button(get_global_i18n().t('crawler.delete_file'), id="delete-file-btn", variant="warning"),
                    Button(get_global_i18n().t('crawler.delete_record'), id="delete-record-btn", variant="warning"),
                    Button(get_global_i18n().t('crawler.back'), id="back-btn"),
                    id="crawler-buttons", classes="btn-row"
                ),

                # 中部可滚动区域：搜索区 + 输入区 + 历史表格
                Vertical(
                    # 搜索区域
                    Vertical(
                        Horizontal(
                            Input(placeholder=get_global_i18n().t('crawler.search_placeholder'), id="search-input-field"),
                            Button(get_global_i18n().t('common.search'), id="search-btn"),
                            Button(get_global_i18n().t('crawler.clear_search'), id="clear-search-btn"),
                            id="search-container", classes="form-row"
                        ),
                        id="search-section"
                    ),
                    
                    # 小说ID输入区域
                    Vertical(
                        Horizontal(
                            # 根据书籍网站的"是否支持选择书籍"设置显示选择书籍按钮
                            *([Button(get_global_i18n().t('crawler.select_books'), id="choose-books-btn")] if self.novel_site.get("selectable_enabled", True) else []),
                            Input(placeholder=get_global_i18n().t('crawler.novel_id_placeholder_multi'), id="novel-id-input"),
                            Button(get_global_i18n().t('crawler.start_crawl'), id="start-crawl-btn", variant="primary"),
                            Button(get_global_i18n().t('crawler.stop_crawl'), id="stop-crawl-btn", variant="error", disabled=True),
                            Button(get_global_i18n().t('crawler.copy_ids'), id="copy-ids-btn"),
                            Button(get_global_i18n().t('crawler.toggle_monitor'), id="toggle-monitor-btn", variant="success"),
                            # Label(get_global_i18n().t('crawler.browser_label'), id="browser-label", classes="browser-label"),
                            Select(
                                id="browser-select",
                                options=[
                                    (get_global_i18n().t('crawler.browser_label'), "chrome"),
                                    ("Chrome", "chrome"),
                                    ("Safari", "safari"),
                                    ("Brave", "brave")
                                ],
                                value="chrome",
                                classes="browser-select"
                            ),
                            id="novel-id-container", classes="form-row"
                        ),
                        id="novel-id-section"
                    ),

                    # 爬取历史区域
                    Vertical(
                        # Label(get_global_i18n().t('crawler.crawl_history'), id="crawl-history-title"),
                        DataTable(id="crawl-history-table"),
                        id="crawl-history-section"
                    ),
                    id="crawler-scroll", classes="scroll-y"
                ),

                # 分页导航
                Horizontal(
                    Button("◀◀", id="first-page-btn", classes="pagination-btn"),
                    Button("◀", id="prev-page-btn", classes="pagination-btn"),
                    Label("", id="page-info", classes="page-info"),
                    Button("▶", id="next-page-btn", classes="pagination-btn"),
                    Button("▶▶", id="last-page-btn", classes="pagination-btn"),
                    Button(get_global_i18n().t('bookshelf.jump_to'), id="jump-page-btn", classes="pagination-btn"),
                    id="pagination-bar",
                    classes="pagination-bar"
                ),

                # 状态信息
                Label("", id="crawler-status"),

                # 加载动画区域
                Static("", id="loading-animation"),

                # 快捷键状态栏
                # Horizontal(
                #     Label(get_global_i18n().t('crawler.shortcut_o'), id="shortcut-o"),
                #     Label(get_global_i18n().t('crawler.shortcut_r'), id="shortcut-r"),
                #     Label(get_global_i18n().t('crawler.shortcut_s'), id="shortcut-s"),
                #     Label(get_global_i18n().t('crawler.shortcut_v'), id="shortcut-v"),
                #     Label(get_global_i18n().t('crawler.shortcut_b'), id="shortcut-b"),
                #     Label(get_global_i18n().t('crawler.shortcut_p'), id="shortcut-p"),
                #     Label(get_global_i18n().t('crawler.shortcut_n'), id="shortcut-n"),
                #     Label(get_global_i18n().t('crawler.shortcut_esc'), id="shortcut-esc"),
                #     id="shortcuts-bar", classes="status-bar"
                # ),
                id="crawler-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 设置挂载标志
        self.is_mounted_flag = True
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 权限提示与按钮状态
        try:
            start_btn = self.query_one("#start-crawl-btn", Button)
            if not getattr(self.app, "has_permission", lambda k: True)("crawler.run"):
                start_btn.disabled = True
                self._update_status(get_global_i18n().t('crawler.np_crawler'), "warning")
        except Exception:
            pass
        
        # 初始化数据表
        table = self.query_one("#crawl-history-table", DataTable)
        table.clear(columns=True)
        
        # 添加列定义
        table.add_column(get_global_i18n().t('batch_ops.selected'), key="selected")
        table.add_column(get_global_i18n().t('crawler.sequence'), key="sequence")
        table.add_column(get_global_i18n().t('crawler.novel_id'), key="novel_id")
        table.add_column(get_global_i18n().t('crawler.novel_title'), key="novel_title")
        table.add_column(get_global_i18n().t('bookshelf.size'), key="file_size")
        table.add_column(get_global_i18n().t('crawler.crawl_time'), key="crawl_time")
        table.add_column(get_global_i18n().t('crawler.status'), key="status")
        table.add_column(get_global_i18n().t('crawler.view_file'), key="view_file")
        table.add_column(get_global_i18n().t('crawler.read_book'), key="read_book")
        table.add_column("浏览器阅读", key="browser_read_book")
        table.add_column(get_global_i18n().t('crawler.delete_file'), key="delete_file")
        table.add_column(get_global_i18n().t('crawler.delete_record'), key="delete_record")
        table.add_column(get_global_i18n().t('crawler.view_reason'), key="view_reason")
        table.add_column(get_global_i18n().t('crawler.retry'), key="retry")
        
        table.zebra_stripes = True
        
        # 初始化加载动画
        self._initialize_loading_animation()

        # 加载浏览器配置 - 必须在初始化监听器之前
        self._load_browser_config()

        # 更新浏览器选择下拉框的值为加载的配置
        try:
            browser_select = self.query_one("#browser-select", Select)
            browser_select.value = self.selected_browser
            logger.info(f"浏览器选择下拉框已更新为: {self.selected_browser}")
        except Exception as e:
            logger.warning(f"更新浏览器选择下拉框失败: {e}")

        # 初始化Chrome监听器 - 使用加载后的配置
        self._init_browser_monitor()

        # 加载爬取历史
        self._load_crawl_history()

        # 设置焦点到表格，确保光标位置能够正确恢复
        try:
            table = self.query_one("#crawl-history-table", DataTable)
            table.focus()
            # 确保表格能够接收键盘事件
            table.can_focus = True
        except Exception:
            # 如果表格焦点设置失败，回退到输入框
            self.query_one("#novel-id-input", Input).focus()
    
    def _on_crawl_status_change(self, task_id: str, task: Any) -> None:
        """爬取状态变化回调"""
        try:
            from src.core.crawler_manager import CrawlStatus
            
            # 更新UI状态
            if task.status == CrawlStatus.RUNNING:
                self.is_crawling = True
                self.current_crawling_id = task.current_novel_id
                
                # 更新状态显示
                if task.current_novel_id:
                    status_text = f"{get_global_i18n().t('crawler.crawling')} ({task.progress}/{task.total}): {task.current_novel_id}"
                    self.app.call_later(self._update_status, status_text)
                
            elif task.status in [CrawlStatus.COMPLETED, CrawlStatus.FAILED, CrawlStatus.STOPPED]:
                self.is_crawling = False
                self.current_crawling_id = None
                self.current_task_id = None
                
                # 显示最终结果
                if task.status == CrawlStatus.COMPLETED:
                    status_text = f"{get_global_i18n().t('crawler.crawl_completed')}: {task.success_count} {get_global_i18n().t('crawler.success')}, {task.failed_count} {get_global_i18n().t('crawler.failed')}"
                elif task.status == CrawlStatus.FAILED:
                    status_text = f"{get_global_i18n().t('crawler.crawl_failed')}: {task.error_message}"
                else:
                    status_text = get_global_i18n().t('crawler.crawl_stopped')
                
                self.app.call_later(self._update_status, status_text)
                self.app.call_later(self._update_crawl_button_state)
                self.app.call_later(self._hide_loading_animation)
                
                # 刷新历史记录
                self.app.call_later(self._load_crawl_history)
                
                # 自动验证：如果输入框中还有ID，继续爬取下一个
                if task.status == CrawlStatus.COMPLETED:
                    self.app.call_later(self._check_and_continue_crawl)
                
                # 自动验证：如果输入框中还有ID，继续爬取下一个
                if task.status == CrawlStatus.COMPLETED:
                    self.app.call_later(self._check_and_continue_crawl)
            
        except Exception as e:
            logger.error(f"爬取状态回调处理失败: {e}")
    
    def _on_crawl_success_notify(self, task_id: str, novel_id: str, novel_title: str, already_exists: bool = False) -> None:
        """爬取成功通知回调
        
        Args:
            task_id: 任务ID
            novel_id: 小说ID
            novel_title: 小说标题
            already_exists: 是否文件已存在
        """
        try:
            # 清理输入框中的ID（无论文件是否存在都要清理）
            self.app.call_later(self._remove_id_from_input, novel_id)
            
            # 如果文件已存在，不需要添加数据库记录和发送全局通知
            if already_exists:
                logger.info(f"小说文件已存在，跳过添加数据库记录: {novel_title}")
                # 只显示消息，不发送全局通知，不刷新历史记录
                self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.novel_exists')}: {novel_title}", "information")
                return
            
            # 发送全局通知（跨页面）
            def send_global_notification():
                try:
                    # 发送全局通知到书架页面，更新书架列表
                    if hasattr(self.app, 'post_message'):
                        try:
                            from src.ui.messages import RefreshBookshelfMessage
                            self.app.post_message(RefreshBookshelfMessage())
                        except ImportError:
                            logger.debug("RefreshBookshelfMessage 导入失败，使用备用通知方式")
                    
                    # 在主界面显示成功通知
                    if hasattr(self.app, 'post_message'):
                        try:
                            from src.ui.messages import CrawlCompleteNotification
                            self.app.post_message(CrawlCompleteNotification(
                                success=True,
                                novel_title=novel_title,
                                message=f"成功爬取小说: {novel_title}"
                            ))
                        except ImportError:
                            logger.debug("CrawlCompleteNotification 导入失败，使用备用通知方式")
                except Exception as e:
                    logger.debug(f"发送全局通知失败: {e}")
            
            self.app.call_later(send_global_notification)
            
            # 刷新当前页面的历史记录
            self.app.call_later(self._load_crawl_history)
            
        except Exception as e:
            logger.error(f"爬取成功通知回调处理失败: {e}")
    
    def _load_crawl_history(self, from_search: bool = False) -> None:
        """加载爬取历史记录
        
        Args:
            from_search: 是否来自搜索操作（搜索时不设置表格焦点）
        """
        try:
            # 从数据库加载爬取历史
            site_id = self.novel_site.get('id')
            if site_id:
                # 为了支持分页，不限制查询数量，由UI分页控制显示
                db_history = self.db_manager.get_crawl_history_by_site(site_id, limit=None)
                
                # 转换数据库格式为显示格式
                self.crawler_history = []
                for item in db_history:
                    # 转换状态显示文本
                    status_text = get_global_i18n().t('crawler.status_success') if item['status'] == 'success' else get_global_i18n().t('crawler.status_failed')
                    
                    # 转换时间格式
                    try:
                        from datetime import datetime
                        crawl_time = datetime.fromisoformat(item['crawl_time']).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        crawl_time = item['crawl_time']
                    
                    # 获取文件大小
                    file_size = 0
                    if item['file_path']:
                        try:
                            from src.utils.file_utils import FileUtils
                            file_size = FileUtils.get_file_size(item['file_path'])
                        except Exception as e:
                            # logger.debug(f"获取文件大小失败: {e}")
                            file_size = 0
                    
                    self.crawler_history.append({
                        "id": item['id'],
                        "novel_id": item['novel_id'],
                        "novel_title": item['novel_title'],
                        "crawl_time": crawl_time,
                        "status": status_text,
                        "file_path": item['file_path'] or "",
                        "file_size": file_size,
                        "error_message": item.get('error_message', '')
                    })
            else:
                self.crawler_history = []
        except Exception as e:
            logger.error(f"加载爬取历史记录失败: {e}")
            self.crawler_history = []
        
        # 应用搜索过滤
        self.crawler_history = self._filter_history(self.crawler_history)
        self._update_history_table(from_search=from_search)
    
    def _filter_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据搜索关键词过滤历史记录"""
        if not self._search_keyword:
            return history
        
        # 对搜索关键词进行URL解码，以便能正确匹配
        keyword = unquote(self._search_keyword).lower()
        filtered_history = []
        
        for item in history:
            # 获取解码后的novel_id
            item_novel_id = item.get('novel_id', '')
            decoded_novel_id = unquote(item_novel_id) if item_novel_id else ''
            
            # 搜索小说标题、小说ID（解码后）、状态
            if (keyword in item.get('novel_title', '').lower() or 
                keyword in decoded_novel_id.lower() or 
                keyword in item.get('status', '').lower()):
                filtered_history.append(item)
        
        return filtered_history
    
    def _update_history_table(self, from_search: bool = False) -> None:
        """更新历史记录表格
        
        Args:
            from_search: 是否来自搜索操作（搜索时不设置表格焦点）
        """
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟更新历史记录表格")
                # 延迟100ms后重试
                self.set_timer(0.1, self._update_history_table)
                return

            table = self.query_one("#crawl-history-table", DataTable)
            
            # 保存当前光标位置
            current_cursor_row = table.cursor_row
            
            table.clear()
            
            # 计算当前页的起始索引
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = min(start_index + self.items_per_page, len(self.crawler_history))
            
            # 添加当前页的数据行
            for i in range(start_index, end_index):
                item = self.crawler_history[i]
                
                # 检查是否选中
                # 注意：selected_history 中存储的是字符串类型的ID，需要将item["id"]转换为字符串进行比较
                is_selected = "✓" if str(item["id"]) in self.selected_history else ""
                
                # 对novel_id进行URL解码，避免显示乱码
                novel_id = item.get("novel_id", "")
                decoded_novel_id = unquote(novel_id) if novel_id else ""
                
                # 格式化文件大小显示
                size_display = ""
                if "file_size" in item and item["file_size"]:
                    try:
                        from src.utils.file_utils import FileUtils
                        size_display = FileUtils.format_file_size(item["file_size"])
                    except Exception as e:
                        logger.debug(f"格式化文件大小失败: {e}")
                        size_display = ""
                
                row_data = {
                    "selected": is_selected,
                    "sequence": str(i + 1),
                    "novel_id": decoded_novel_id,
                    "novel_title": item["novel_title"],
                    "file_size": size_display,
                    "crawl_time": item["crawl_time"],
                    "status": item["status"],
                    "view_file": get_global_i18n().t('crawler.view_file') if item["status"] == get_global_i18n().t('crawler.status_success') else "",
                    "read_book": get_global_i18n().t('crawler.read_book') if item["status"] == get_global_i18n().t('crawler.status_success') else "",
                    "browser_read_book": get_global_i18n().t('crawler.browser_read_book') if item["status"] == get_global_i18n().t('crawler.status_success') else "",
                    "delete_file": get_global_i18n().t('crawler.delete_file') if item["status"] == get_global_i18n().t('crawler.status_success') else "",
                    "delete_record": get_global_i18n().t('crawler.delete_record'),
                    "view_reason": get_global_i18n().t('crawler.view_reason') if item["status"] == get_global_i18n().t('crawler.status_failed') else "",
                    "retry": get_global_i18n().t('crawler.retry') if item["status"] == get_global_i18n().t('crawler.status_failed') else ""
                }
                
                table.add_row(*row_data.values(), key=str(item["id"]))
            
            # 更新分页信息
            self._update_pagination_info()
            
            # 更新选择状态
            self._update_selection_status()
            
            # 恢复光标位置，确保光标不会跳回第一行
            if current_cursor_row is not None and current_cursor_row >= 0:
                # 确保光标位置在有效范围内
                if current_cursor_row < min(self.items_per_page, len(self.crawler_history) - start_index):
                    if hasattr(table, 'move_cursor'):
                        table.move_cursor(row=current_cursor_row)
                    # 如果move_cursor不存在，使用键盘操作来移动光标
                    else:
                        # 将光标移动到正确位置
                        # 先将光标移动到第一行
                        while table.cursor_row > 0:
                            table.action_cursor_up()
                        # 然后向下移动到目标位置
                        for _ in range(current_cursor_row):
                            table.action_cursor_down()
            
            # 只有在不是来自搜索时才设置表格焦点
            if not from_search:
                table.focus()
            
        except Exception as e:
            logger.debug(f"更新历史记录表格失败: {e}")
            # 延迟重试
            self.set_timer(0.1, self._update_history_table)
    
    def _update_pagination_info(self) -> None:
        """更新分页信息"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟更新分页信息")
                # 延迟100ms后重试
                self.set_timer(0.1, self._update_pagination_info)
                return

            total_pages = max(1, (len(self.crawler_history) + self.items_per_page - 1) // self.items_per_page)
            page_info = get_global_i18n().t('page_info', total=len(self.crawler_history), current=self.current_page, pages=total_pages)
            
            page_label = self.query_one("#page-info", Label)
            page_label.update(page_info)
            
            # 更新分页按钮状态
            self.query_one("#first-page-btn", Button).disabled = self.current_page <= 1
            self.query_one("#prev-page-btn", Button).disabled = self.current_page <= 1
            self.query_one("#next-page-btn", Button).disabled = self.current_page >= total_pages
            self.query_one("#last-page-btn", Button).disabled = self.current_page >= total_pages
            
        except Exception as e:
            logger.error(f"更新分页信息失败: {e}")
    
    def _update_status(self, message: str, severity: str = "information") -> None:
        """更新状态信息"""
        try:
            status_label = self.query_one("#crawler-status", Label)
            status_label.update(message)
            
            # 设置样式类
            status_label.remove_class("status-info")
            status_label.remove_class("status-warning")
            status_label.remove_class("status-error")
            
            if severity == "warning":
                status_label.add_class("status-warning")
            elif severity == "error":
                status_label.add_class("status-error")
            else:
                status_label.add_class("status-info")
                
        except Exception as e:
            logger.error(f"更新状态信息失败: {e}")
    
    def _initialize_loading_animation(self) -> None:
        """初始化加载动画"""
        try:
            # 创建原生LoadingIndicator
            self.loading_indicator = LoadingIndicator()
            self.loading_indicator.styles.display = "none"  # 默认隐藏
            
            # 将加载指示器添加到加载动画区域
            loading_container = self.query_one("#loading-animation", Static)
            loading_container.mount(self.loading_indicator)
            
        except Exception as e:
            logger.error(f"初始化加载动画失败: {e}")
    
    # ==================== 搜索功能 ====================
    
    def _focus_search_input(self) -> None:
        """将焦点设置回搜索框"""
        try:
            search_input = self.query_one("#search-input-field", Input)
            search_input.focus()
        except Exception as e:
            logger.debug(f"设置搜索框焦点失败: {e}")
    
    def _perform_search(self) -> None:
        """执行搜索"""
        try:
            search_input = self.query_one("#search-input-field", Input)
            self._search_keyword = search_input.value.strip()
            
            # 重新加载历史记录并应用搜索过滤
            self._load_crawl_history(from_search=True)
            
            if self._search_keyword:
                self._update_status(get_global_i18n().t('crawler.search_complete', count=len(self.crawler_history)))
            else:
                self._update_status(get_global_i18n().t('crawler.all_records_shown'))
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            self._update_status(get_global_i18n().t('crawler.search_failed'), "error")
    
    def _clear_search(self) -> None:
        """清除搜索"""
        try:
            search_input = self.query_one("#search-input-field", Input)
            search_input.value = ""
            self._search_keyword = ""
            
            # 重新加载历史记录
            self._load_crawl_history(from_search=True)
            self._update_status(get_global_i18n().t('crawler.search_cleared'))
        except Exception as e:
            logger.error(f"清除搜索失败: {e}")
            self._update_status(get_global_i18n().t('crawler.clear_search_failed'), "error")
    
    # ==================== 多选操作方法 ====================
    
    def _handle_selection_click(self, row_index: int) -> None:
        """处理选择列的点击"""
        try:
            # 获取当前页的数据
            start_index = (self.current_page - 1) * self.items_per_page
            if row_index is not None and row_index < len(self.crawler_history) - start_index:
                history_item = self.crawler_history[start_index + row_index]
                
                if not history_item:
                    return
                
                record_id = history_item["id"]
                
                # 切换选择状态
                if record_id in self.selected_history:
                    self.selected_history.remove(record_id)
                else:
                    self.selected_history.add(record_id)
                
                # 更新表格显示
                self._update_history_table()
                
                # 更新状态显示
                self._update_selection_status()
                
        except Exception as e:
            logger.error(f"处理选择点击失败: {e}")
    
    def _handle_cell_selection(self, row_key: str) -> None:
        """处理单元格选择（空格键或鼠标点击）"""
        try:
            # row_key 就是历史记录ID，直接使用
            record_id = row_key
            
            # 检查记录ID是否存在
            # 注意：record_id是字符串类型，需要与历史记录ID进行比较时进行类型转换
            record_exists = any(str(item["id"]) == record_id for item in self.crawler_history)
            if not record_exists:
                logger.debug(f"无法找到对应的历史记录: {record_id}")
                return
            
            # 切换选择状态
            if record_id in self.selected_history:
                self.selected_history.remove(record_id)
            else:
                self.selected_history.add(record_id)
            
            # 更新表格显示
            self._update_history_table()
            
            # 更新状态显示
            self._update_selection_status()
            
        except Exception as e:
            logger.error(f"处理单元格选择失败: {e}")
    
    def _update_selection_status(self) -> None:
        """更新选择状态显示"""
        selected_count = len(self.selected_history)
        self._update_status(get_global_i18n().t('batch_ops.selected_count', count=selected_count))
    
    def _select_all(self) -> None:
        """全选"""
        try:
            # 选择当前显示的所有记录
            for item in self.crawler_history:
                # 确保类型一致：将item["id"]转换为字符串
                self.selected_history.add(str(item["id"]))
            
            # 更新表格显示
            self._update_history_table()
            self._update_selection_status()
            
        except Exception as e:
            logger.error(f"全选失败: {e}")
    
    def _select_all_rows(self) -> None:
        """全选当前页"""
        try:
            # 计算当前页的起始索引和结束索引
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = min(start_index + self.items_per_page, len(self.crawler_history))
            
            # 只选择当前页的记录
            for i in range(start_index, end_index):
                item = self.crawler_history[i]
                # 确保类型一致：将item["id"]转换为字符串
                record_id = str(item["id"])
                self.selected_history.add(record_id)
            
            # 更新表格显示
            self._update_history_table()
            self._update_selection_status()
            
        except Exception as e:
            logger.error(f"全选失败: {e}")
    
    def _invert_selection(self) -> None:
        """反选当前页"""
        try:
            # 计算当前页的起始索引和结束索引
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = min(start_index + self.items_per_page, len(self.crawler_history))
            
            # 只反选当前页的记录
            for i in range(start_index, end_index):
                item = self.crawler_history[i]
                # 确保类型一致：将item["id"]转换为字符串
                record_id = str(item["id"])
                if record_id in self.selected_history:
                    self.selected_history.remove(record_id)
                else:
                    self.selected_history.add(record_id)
            
            # 更新表格显示
            self._update_history_table()
            self._update_selection_status()
            
        except Exception as e:
            logger.error(f"反选失败: {e}")
    
    def _deselect_all_rows(self) -> None:
        """取消全选"""
        try:
            self.selected_history.clear()
            
            # 更新表格显示
            self._update_history_table()
            self._update_selection_status()
            
        except Exception as e:
            logger.error(f"取消全选失败: {e}")
    
    def _move_selected_up(self) -> None:
        """上移光标所在行"""
        try:
            # 获取当前光标所在行
            table = self.query_one("#crawl-history-table", DataTable)
            cursor_row = table.cursor_row
            
            if cursor_row is None or cursor_row < 0:
                return
            
            # 计算当前页的起始索引
            start_index = (self.current_page - 1) * self.items_per_page
            
            # 计算实际索引
            actual_index = start_index + cursor_row
            
            # 检查索引是否有效
            if actual_index >= len(self.crawler_history):
                return
            
            # 检查是否可以上移
            if actual_index <= 0:
                return
            
            # 交换位置
            self.crawler_history[actual_index], self.crawler_history[actual_index-1] = self.crawler_history[actual_index-1], self.crawler_history[actual_index]
            
            # 保存新的光标位置（上移后光标应该向上移动一行）
            new_cursor_row = max(0, cursor_row - 1)
            
            # 更新表格显示
            self._update_history_table()
            
            # 恢复光标到正确位置
            if hasattr(table, 'move_cursor'):
                table.move_cursor(row=new_cursor_row)
            else:
                # 使用键盘操作来移动光标
                # 先将光标移动到第一行
                while table.cursor_row > 0:
                    table.action_cursor_up()
                # 然后向下移动到目标位置
                for _ in range(new_cursor_row):
                    table.action_cursor_down()
            
            # 只有在不是来自搜索时才设置表格焦点
            if not from_search:
                table.focus()
            
            
        except Exception as e:
            logger.error(f"上移失败: {e}")
    
    def _move_selected_down(self) -> None:
        """下移光标所在行"""
        try:
            # 获取当前光标所在行
            table = self.query_one("#crawl-history-table", DataTable)
            cursor_row = table.cursor_row
            
            if cursor_row is None or cursor_row < 0:
                return
            
            # 计算当前页的起始索引
            start_index = (self.current_page - 1) * self.items_per_page
            
            # 计算实际索引
            actual_index = start_index + cursor_row
            
            # 检查索引是否有效
            if actual_index >= len(self.crawler_history):
                return
            
            # 检查是否可以下移
            if actual_index >= len(self.crawler_history) - 1:
                return
            
            # 交换位置
            self.crawler_history[actual_index], self.crawler_history[actual_index+1] = self.crawler_history[actual_index+1], self.crawler_history[actual_index]
            
            # 保存新的光标位置（下移后光标应该向下移动一行）
            new_cursor_row = min(cursor_row + 1, self.items_per_page - 1)
            
            # 计算当前页的实际行数
            current_page_rows = min(self.items_per_page, len(self.crawler_history) - start_index)
            
            # 确保新光标位置不超过当前页的实际行数
            if new_cursor_row >= current_page_rows:
                new_cursor_row = current_page_rows - 1
            
            # 更新表格显示
            self._update_history_table()
            
            # 恢复光标到正确位置
            if hasattr(table, 'move_cursor'):
                table.move_cursor(row=new_cursor_row)
            else:
                # 使用键盘操作来移动光标
                # 先将光标移动到第一行
                while table.cursor_row > 0:
                    table.action_cursor_up()
                # 然后向下移动到目标位置
                for _ in range(new_cursor_row):
                    table.action_cursor_down()
            
            # 只有在不是来自搜索时才设置表格焦点
            if not from_search:
                table.focus()
            
            
        except Exception as e:
            logger.error(f"下移失败: {e}")
    
    def _move_to_position(self, target_position: int) -> None:
        """将当前光标所在的项移动到指定位置"""
        try:
            # 获取当前光标所在行
            table = self.query_one("#crawl-history-table", DataTable)
            cursor_row = table.cursor_row
            
            if cursor_row is None or cursor_row < 0:
                self._update_status(get_global_i18n().t('crawler.no_selection'))
                return
            
            # 计算当前页的起始索引
            start_index = (self.current_page - 1) * self.items_per_page
            
            # 计算当前项的实际索引
            current_index = start_index + cursor_row
            
            # 检查索引是否有效
            if current_index >= len(self.crawler_history):
                self._update_status(get_global_i18n().t('crawler.id_error'))
                return
            
            # 检查选中项数量
            selected_count = len(self.selected_history)
            
            # 如果没有选中项，提示用户
            if selected_count == 0:
                self._update_status(get_global_i18n().t('crawler.no_selection'))
                return
            
            # 获取当前项
            current_item = self.crawler_history[current_index]
            
            # 检查当前项是否为选中项
            current_item_id = str(current_item.get("id"))
            if current_item_id not in self.selected_history:
                self._update_status(get_global_i18n().t('crawler.sort_only_selected'))
                return
            
            # 如果目标位置超出选中项数量，调整到末尾
            if target_position >= selected_count:
                target_position = selected_count - 1
            
            # 重新排序选中项：先获取所有选中项
            selected_items = []
            other_items = []
            
            for i, item in enumerate(self.crawler_history):
                item_id = str(item.get("id"))
                if item_id in self.selected_history:
                    selected_items.append((i, item))
                else:
                    other_items.append((i, item))
            
            # 找到当前项在选中项中的位置
            current_selected_index = -1
            for i, (orig_idx, item) in enumerate(selected_items):
                if str(item.get("id")) == current_item_id:
                    current_selected_index = i
                    break
            
            if current_selected_index == -1:
                return
            
            # 从选中项列表中移除当前项
            current_selected_item = selected_items.pop(current_selected_index)[1]
            
            # 将当前项插入到目标位置
            selected_items.insert(target_position, (None, current_selected_item))  # 位置用None临时占位
            
            # 重建完整的列表：保持非选中项的相对位置，只调整选中项的顺序
            new_crawler_history = []
            selected_iter = iter(selected_items)
            
            for item in self.crawler_history:
                item_id = str(item.get("id"))
                if item_id in self.selected_history:
                    # 使用选中项中的下一个项
                    _, selected_item = next(selected_iter)
                    new_crawler_history.append(selected_item)
                else:
                    # 保持非选中项不变
                    new_crawler_history.append(item)
            
            # 更新历史记录
            self.crawler_history = new_crawler_history
            
            # 计算移动后当前项的新索引
            new_current_index = -1
            for i, item in enumerate(self.crawler_history):
                if str(item.get("id")) == current_item_id:
                    new_current_index = i
                    break
            
            if new_current_index == -1:
                return
            
            # 计算移动后新的光标位置
            if new_current_index < start_index:
                # 移动到当前页之前，将光标移动到当前页第一行
                new_cursor_row = 0
            elif new_current_index >= start_index + self.items_per_page:
                # 移动到当前页之后，可能需要翻页
                new_cursor_row = min(self.items_per_page - 1, len(self.crawler_history) - start_index - 1)
            else:
                # 移动到当前页内，计算新的光标位置
                new_cursor_row = new_current_index - start_index
            
            # 更新表格显示
            self._update_history_table()
            
            # 如果移动到其他页，计算新页码
            new_page = new_current_index // self.items_per_page + 1
            if new_page != self.current_page:
                self.current_page = new_page
                self._update_history_table()
            
            # 恢复光标到正确位置
            if hasattr(table, 'move_cursor'):
                table.move_cursor(row=new_cursor_row)
            else:
                # 使用键盘操作来移动光标
                # 先将光标移动到第一行
                while table.cursor_row > 0:
                    table.action_cursor_up()
                # 然后向下移动到目标位置
                for _ in range(new_cursor_row):
                    table.action_cursor_down()
            
            # 只有在不是来自搜索时才设置表格焦点
            if not from_search:
                table.focus()
            
            # 显示成功信息
            display_position = target_position + 1
            if display_position == 10:
                display_key = "0"
            else:
                display_key = str(display_position)
            
        except Exception as e:
            logger.error(f"移动到指定位置失败: {e}")
    
    def _move_cursor_to_position(self, target_position: int) -> None:
        """将光标移动到当前页的指定行"""
        try:
            # 获取表格
            table = self.query_one("#crawl-history-table", DataTable)
            
            # 计算当前页的实际行数
            start_index = (self.current_page - 1) * self.items_per_page
            current_page_rows = min(self.items_per_page, len(self.crawler_history) - start_index)
            
            # 检查目标位置是否超出当前页的行数
            if target_position >= current_page_rows:
                target_position = current_page_rows - 1
            
            # 移动光标到目标行
            if hasattr(table, 'move_cursor'):
                table.move_cursor(row=target_position)
            else:
                # 使用键盘操作来移动光标
                # 先将光标移动到第一行
                while table.cursor_row > 0:
                    table.action_cursor_up()
                # 然后向下移动到目标位置
                for _ in range(target_position):
                    table.action_cursor_down()
            
            # 只有在不是来自搜索时才设置表格焦点
            if not from_search:
                table.focus()
            
            # 显示成功信息
            display_position = target_position + 1
            if display_position == 10:
                display_key = "0"
            else:
                display_key = str(display_position)
            
        except Exception as e:
            logger.error(f"移动光标失败: {e}")
    
    def _merge_selected(self) -> None:
        """合并选中项"""
        try:
            if not self.selected_history:
                self._update_status(get_global_i18n().t('crawler.merge_selection'))
                return
            
            if len(self.selected_history) < 2:
                self._update_status(get_global_i18n().t('crawler.merge_at_least_two'))
                return
            
            # 获取选中项
            selected_items = []
            for item in self.crawler_history:
                # 确保类型一致：将item["id"]转换为字符串进行比较
                if str(item["id"]) in self.selected_history:
                    selected_items.append(item)
            
            # 检查是否都是成功状态
            for item in selected_items:
                if item["status"] != get_global_i18n().t('crawler.status_success'):
                    self._update_status(get_global_i18n().t('crawler.merge_successful_records'))
                    return
            
            # 打开合并对话框
            from src.ui.dialogs.crawler_merge_dialog import CrawlerMergeDialog
            
            def handle_merge_result(result: Optional[Dict[str, Any]]) -> None:
                if not result:
                    return  # 如果结果为None，直接返回
                
                if result.get('success'):
                    new_title = result.get('new_title', '')
                    selected_items = result.get('selected_items', [])
                    
                    try:
                        # 执行实际的合并操作
                        if self._perform_actual_merge(selected_items, new_title):
                            self._update_status(f"{get_global_i18n().t('crawler.merge_success')}: {new_title}")
                            # 清除已合并的选中项
                            for item in selected_items:
                                item_id = item.get("id")
                                if item_id and str(item_id) in self.selected_history:
                                    self.selected_history.remove(str(item_id))
                            # 刷新历史记录
                            self._load_crawl_history()
                        else:
                            self._update_status(get_global_i18n().t('crawler.merge_failed'), "error")
                    except Exception as e:
                        logger.error(f"合并操作异常: {e}")
                        self._update_status(get_global_i18n().t('crawler.merge_exception', e=e), "error")
                else:
                    message = result.get('message', '未知错误')
                    if message != get_global_i18n().t('batch_ops.cancel_merge'):  # 不显示取消合并的错误
                        self._update_status(get_global_i18n().t('crawler.merge_failed_with_message', message=message), "error")
            
            self.app.push_screen(
                CrawlerMergeDialog(
                    self.theme_manager,
                    selected_items
                ),
                handle_merge_result
            )
            
        except Exception as e:
            logger.error(f"合并失败: {e}")
            self._update_status(get_global_i18n().t('crawler.merge_failed'), "error")
    
    def _perform_actual_merge(self, selected_items: List[Dict[str, Any]], new_title: str) -> bool:
        """
        执行实际的合并操作
        
        Args:
            selected_items: 选中的爬取历史记录
            new_title: 新书籍标题
            
        Returns:
            bool: 合并是否成功
        """
        try:
            if not selected_items or len(selected_items) < 2:
                logger.error("合并失败：至少需要选择2条记录")
                return False
            
            # 收集需要合并的文件路径和记录信息
            file_paths = []
            record_ids = []
            for item in selected_items:
                if item.get("file_path"):
                    file_paths.append(item["file_path"])
                    record_ids.append(item["id"])
            
            if not file_paths:
                logger.error("合并失败：没有找到可合并的文件")
                return False
            
            # 检查文件是否存在
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    logger.error(f"合并失败：文件不存在 - {file_path}")
                    return False
            
            # 创建新的合并文件
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 获取第一个文件的目录作为合并文件的保存目录
            first_file_dir = os.path.dirname(file_paths[0])
            merged_filename = f"{new_title}_{timestamp}.txt"
            merged_file_path = os.path.join(first_file_dir, merged_filename)
            
            # 合并文件内容
            with open(merged_file_path, 'w', encoding='utf-8') as merged_file:
                for i, file_path in enumerate(file_paths):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as source_file:
                            content = source_file.read().strip()
                            if content:
                                # 添加章节分隔符（如果有多个文件）
                                if i > 0:
                                    merged_file.write("\n\n" + "="*50 + "\n\n")
                                merged_file.write(content)
                    except Exception as e:
                        logger.error(f"读取文件失败 {file_path}: {e}")
                        continue
            
            # 保存合并记录到数据库
            site_id = self.novel_site.get('id')
            if not isinstance(site_id, int):
                site_id = 0  # 默认值
            
            self.db_manager.add_crawl_history(
                site_id=site_id,
                novel_id=f"merged_{timestamp}",
                novel_title=new_title,
                status="success",
                file_path=merged_file_path,
                error_message=""
            )
            
            # 将合并后的书籍添加到书库
            try:
                from src.core.book import Book
                
                # 创建书籍对象
                # 使用当前操作网站的数据库名称作为author字段
                author = self.novel_site.get('name', '未知作者')
                site_tags = self.novel_site.get('tags', '')
                
                book = Book(merged_file_path, new_title, author, tags=site_tags)
                
                # 检查书籍是否已经存在
                existing_books = self.db_manager.get_all_books()
                book_exists = any(book.path == merged_file_path for book in existing_books)
                
                if not book_exists:
                    # 添加到书库
                    if self.db_manager.add_book(book):
                        logger.info(f"合并书籍已添加到书库: {new_title}")
                    else:
                        logger.warning(f"合并书籍添加到书库失败: {new_title}")
                else:
                    logger.info(f"合并书籍已存在于书库: {new_title}")
                    
            except Exception as e:
                logger.error(f"添加合并书籍到书库失败: {e}")
            
            # 删除源文件和源数据
            for i, (file_path, record_id) in enumerate(zip(file_paths, record_ids)):
                try:
                    # 删除源文件
                    if os.path.exists(file_path):
                        send2trash(file_path)
                        logger.info(f"源文件已移至回收站: {file_path}")
                    
                    # 删除书架中的对应书籍
                    books = self.db_manager.get_all_books()
                    for book in books:
                        if hasattr(book, 'path') and book.path == file_path:
                            if self.db_manager.delete_book(book.path):
                                logger.info(f"删除书架中的书籍: {book.title}")
                            else:
                                logger.warning(f"删除书架书籍失败: {book.title}")
                            break
                    
                    # 删除爬取历史记录
                    if record_id:
                        self.db_manager.delete_crawl_history(record_id)
                        logger.info(f"删除爬取历史记录: {record_id}")
                        
                except Exception as e:
                    logger.error(f"删除源文件或数据失败 {i}: {e}")
            
            # 发送书架刷新消息
            try:
                from src.ui.messages import RefreshBookshelfMessage
                self.app.post_message(RefreshBookshelfMessage())
                logger.info("已发送书架刷新消息")
            except Exception as msg_error:
                logger.debug(f"发送刷新书架消息失败: {msg_error}")
            
            # 记录合并操作日志
            logger.info(f"合并成功：{len(selected_items)}个文件合并为 {new_title}")
            
            return True
            
        except Exception as e:
            logger.error(f"合并操作异常: {e}")
            return False
    


    @on(DataTable.HeaderSelected, "#crawl-history-table")
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """数据表格表头点击事件 - 处理排序"""
        try:
            column_key = event.column_key.value or ""

            logger.debug(f"表头点击事件: column={column_key}")

            # 只对特定列进行排序：序号、书籍ID、书籍标题、大小、爬取时间、状态
            sortable_columns = ["sequence", "novel_id", "novel_title", "file_size", "crawl_time", "status"]

            if column_key in sortable_columns:
                # 切换排序方向
                if self._sort_column == column_key:
                    self._sort_reverse = not self._sort_reverse
                else:
                    self._sort_column = column_key
                    self._sort_reverse = True  # 新列默认倒序

                # 执行排序
                self._sort_history(column_key, self._sort_reverse)

                # 更新表格显示
                self._update_history_table()

                # 显示排序提示
                sort_direction = "倒序" if self._sort_reverse else "正序"
                column_names = {
                    "sequence": "序号",
                    "novel_id": "书籍ID",
                    "novel_title": "书籍标题",
                    "file_size": "大小",
                    "crawl_time": "爬取时间",
                    "status": "状态"
                }
                column_name = column_names.get(column_key, column_key)
                self._update_status(f"已按 {column_name} {sort_direction} 排列", "information")

        except Exception as e:
            logger.error(f"表头点击事件处理失败: {e}")

    def _sort_history(self, column_key: str, reverse: bool) -> None:
        """根据指定列对历史记录进行排序

        Args:
            column_key: 排序的列键
            reverse: 是否倒序
        """
        try:
            def get_sort_key(item: Dict[str, Any]) -> Any:
                """获取排序键值"""
                if column_key == "sequence":
                    # 序号无法直接排序，使用原始数据顺序
                    # 由于排序后序号会重新编号，这里使用ID作为替代
                    return item.get("id", "")
                elif column_key == "novel_id":
                    # 书籍ID排序，需要URL解码
                    novel_id = item.get("novel_id", "")
                    return unquote(novel_id) if novel_id else ""
                elif column_key == "novel_title":
                    # 书籍标题排序
                    return item.get("novel_title", "")
                elif column_key == "file_size":
                    # 大小排序，使用原始文件大小数值
                    return item.get("file_size", 0)
                elif column_key == "crawl_time":
                    # 爬取时间排序，需要解析时间字符串
                    try:
                        from datetime import datetime
                        time_str = item.get("crawl_time", "")
                        return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        return datetime.min
                elif column_key == "status":
                    # 状态排序
                    return item.get("status", "")
                return None

            # 使用 sort 函数进行排序
            self.crawler_history.sort(key=get_sort_key, reverse=reverse)

        except Exception as e:
            logger.error(f"排序失败: {e}")

    @on(DataTable.CellSelected, "#crawl-history-table")
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """数据表格单元格选择事件"""
        try:
            cell_key = event.cell_key
            column = cell_key.column_key.value or ""
            row_key = cell_key.row_key.value or ""
            
            logger.debug(f"单元格选择事件: column={column}, row_key={row_key}")
            
            # 处理选择列点击
            if column == "selected":
                self._handle_cell_selection(row_key)
                
            # 处理其他列的按钮点击
            elif column in ["view_file", "read_book", "browser_read_book", "delete_file", "delete_record", "view_reason", "retry"]:
                self._handle_button_click(column, row_key)
                
            # 处理空格键选择：当点击任何非按钮列时，触发选择切换
            elif column not in ["selected", "view_file", "read_book", "browser_read_book", "delete_file", "delete_record", "view_reason", "retry"]:
                self._handle_cell_selection(row_key)
                    
        except Exception as e:
            logger.error(f"单元格选择事件处理失败: {e}")
    
    def _handle_button_click(self, column: str, row_key: str) -> None:
        """处理按钮点击"""
        try:
            # row_key 就是历史记录ID，直接查找对应的历史记录
            # 注意：row_key是字符串类型，需要与历史记录ID进行比较时进行类型转换
            history_item = None
            for item in self.crawler_history:
                # 将历史记录ID转换为字符串与row_key进行比较
                if str(item.get("id")) == row_key:
                    history_item = item
                    break
            
            if not history_item:
                logger.debug(f"无法找到对应的历史记录: {row_key}")
                return
            
            # 根据列名调用相应的处理方法
            if column == "view_file":
                self._view_file(history_item)
            elif column == "read_book":
                self._read_book(history_item)
            elif column == "browser_read_book":
                self._read_book_in_browser(history_item)
            elif column == "delete_file":
                self._delete_file(history_item)
            elif column == "delete_record":
                self._delete_record_only(history_item)
            elif column == "view_reason":
                self._view_reason(history_item)
            elif column == "retry":
                self._retry_crawl(history_item)
                
        except Exception as e:
            logger.debug(f"处理按钮点击失败: {e}")
    
    @on(DataTable.RowSelected, "#crawl-history-table")
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """数据表格行选择事件 - 支持空格键选择"""
        try:
            row_key = event.row_key.value or ""
            logger.debug(f"行选择事件: row_key={row_key}")
            
            # 切换选择状态
            self._handle_cell_selection(row_key)
                    
        except Exception as e:
            logger.error(f"行选择事件处理失败: {e}")
    
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self.current_page != 1:
            self.current_page = 1
            self._update_history_table()
    
    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self._update_history_table()
    
    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        total_pages = max(1, (len(self.crawler_history) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self._update_history_table()
    
    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        total_pages = max(1, (len(self.crawler_history) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page != total_pages:
            self.current_page = total_pages
            self._update_history_table()
    
    def _show_jump_dialog(self) -> None:
        """显示跳转页码对话框"""
        def handle_jump_result(result: Optional[str]) -> None:
            if result and result.strip():
                try:
                    total_pages = max(1, (len(self.crawler_history) + self.items_per_page - 1) // self.items_per_page)
                    page_num = int(result.strip())
                    if 1 <= page_num <= total_pages:
                        if page_num != self.current_page:
                            self.current_page = page_num
                            self._update_history_table()
                    else:
                        self._update_status(get_global_i18n().t('crawler.page_out_of_range', total_pages=total_pages), "error")
                except ValueError:
                    self._update_status(get_global_i18n().t('crawler.invalid_page_number'), "error")
        
        from src.ui.dialogs.input_dialog import InputDialog
        dialog = InputDialog(
            self.theme_manager,
            title=get_global_i18n().t('crawler.goto_page'),
            prompt=get_global_i18n().t('crawler.goto_page_message'),
            placeholder=get_global_i18n().t('crawler.page_number')
        )
        self.app.push_screen(dialog, handle_jump_result)
    
    # ==================== 基础功能方法 ====================
    
    def _open_browser(self) -> None:
        """在浏览器中打开网站"""
        try:
            # 使用BrowserManager打开URL
            try:
                from src.utils.browser_manager import BrowserManager
                
                success = BrowserManager.open_url(self.novel_site['url'])
                if success:
                    browser_name = BrowserManager.get_default_browser()
                    self._update_status(get_global_i18n().t('crawler.browser_opened_with', browser=browser_name), "information")
                else:
                    # 如果BrowserManager失败，使用默认浏览器
                    import webbrowser
                    webbrowser.open(self.novel_site['url'])
                    self._update_status(get_global_i18n().t('crawler.browser_opened'))
            except Exception as e:
                # 如果BrowserManager失败，回退到默认浏览器
                import webbrowser
                webbrowser.open(self.novel_site['url'])
                self._update_status(get_global_i18n().t('crawler.browser_opened'))
                logger.warning(f"BrowserManager失败，使用默认浏览器: {e}")
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.open_browser_failed')}: {str(e)}", "error")
    
    def _view_history(self) -> None:
        """查看爬取历史"""
        # 刷新历史记录
        self._load_crawl_history()
        self._update_status(get_global_i18n().t('crawler.history_loaded'))
    
    def _open_note_dialog(self) -> None:
        """打开备注对话框"""
        try:
            # 获取当前网站的备注内容
            site_id = self.novel_site.get('id')
            if not site_id:
                self._update_status(get_global_i18n().t('crawler.no_site_id'), "error")
                return
            
            # 从数据库加载现有备注
            current_note = self.db_manager.get_novel_site_note(site_id) or ""
            
            # 打开备注对话框
            def handle_note_dialog_result(result: Optional[str]) -> None:
                if result is not None:
                    # 保存备注到数据库
                    if self.db_manager.save_novel_site_note(site_id, result):
                        self._update_status(get_global_i18n().t('crawler.note_saved'), "success")
                    else:
                        self._update_status(get_global_i18n().t('crawler.note_save_failed'), "error")
                # 如果result为None，表示用户取消了操作
            
            self.app.push_screen(
                NoteDialog(
                    self.theme_manager,
                    self.novel_site['name'],
                    current_note
                ),
                handle_note_dialog_result
            )
            
        except Exception as e:
            logger.error(f"打开备注对话框失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.open_note_dialog_failed')}: {str(e)}", "error")

    def _open_select_books_dialog(self) -> None:
        """打开选择书籍对话框，回填选中ID到输入框"""
        try:
            def handle_selected_ids(result: Optional[str]) -> None:
                if result:
                    try:
                        # 对选择的ID进行URL解码
                        decoded_result = unquote(result)
                        novel_id_input = self.query_one("#novel-id-input", Input)
                        current_value = novel_id_input.value.strip()
                        
                        if current_value:
                            # 如果输入框中已有内容，则在原有内容末尾添加逗号后再追加新内容
                            new_value = f"{current_value},{decoded_result}"
                        else:
                            # 如果输入框为空，则直接使用新内容
                            new_value = decoded_result
                        
                        novel_id_input.value = new_value
                        novel_id_input.focus()
                        self._update_status(get_global_i18n().t('crawler.filled_ids'))
                    except Exception as e:
                        logger.debug(f"回填选中ID失败: {e}")
            self.app.push_screen(
                SelectBooksDialog(self.theme_manager, self.novel_site),
                handle_selected_ids
            )
        except Exception as e:
            logger.error(f"打开选择书籍对话框失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.open_dialog_failed')}: {str(e)}", "error")

    def _stop_crawl(self) -> None:
        """停止爬取"""
        if not self.is_crawling and not self.current_task_id:
            self._update_status(get_global_i18n().t('crawler.no_crawl_in_progress'))
            return
        
        # 立即更新UI状态
        self.is_crawling = False
        self._update_crawl_button_state()
        
        # 如果有后台任务，停止它
        if self.current_task_id:
            if self.crawler_manager.stop_crawl_task(self.current_task_id):
                self._update_status(get_global_i18n().t('crawler.crawl_stopped'))
            else:
                self._update_status(get_global_i18n().t('crawler.stop_crawl_failed'), "error")
        else:
            # 如果没有后台任务，直接显示停止状态
            self._update_status(get_global_i18n().t('crawler.crawl_stopped'))
    
    def _copy_novel_ids(self) -> None:
        """复制输入框中的所有书籍ID"""
        try:
            # 获取输入框中的内容
            novel_id_input = self.query_one("#novel-id-input", Input)
            novel_ids_input = novel_id_input.value.strip()
            
            if not novel_ids_input:
                self._update_status(get_global_i18n().t('crawler.enter_novel_id'))
                return
            
            # 分割多个小说ID并处理
            novel_ids = [id.strip() for id in novel_ids_input.split(',') if id.strip()]
            
            if not novel_ids:
                self._update_status(get_global_i18n().t('crawler.enter_novel_id'))
                return
            
            # 将ID列表转换为字符串，使用逗号分隔，保持原始格式
            ids_text = ', '.join(novel_ids)
            
            # 显示成功消息
            count = len(novel_ids)
            
            # 使用pyperclip复制到剪贴板
            try:
                import pyperclip
                pyperclip.copy(ids_text)
                self._update_status(f"{get_global_i18n().t('crawler.copy_ids_success')}: {count} {get_global_i18n().t('crawler.books_count')}")
            except ImportError:
                # 如果pyperclip未安装，尝试使用系统命令
                import subprocess
                import platform
                
                # 根据操作系统选择不同的复制命令
                system = platform.system()
                if system == 'Darwin':  # macOS
                    process = subprocess.run(['pbcopy'], input=ids_text, text=True, check=True)
                elif system == 'Windows':  # Windows
                    process = subprocess.run(['clip'], input=ids_text, text=True, check=True, shell=True)
                else:  # Linux
                    # 尝试使用xclip或xsel
                    try:
                        process = subprocess.run(['xclip', '-selection', 'clipboard'], input=ids_text, text=True, check=True)
                    except (subprocess.SubprocessError, FileNotFoundError):
                        process = subprocess.run(['xsel', '--clipboard', '--input'], input=ids_text, text=True, check=True)
                
                self._update_status(f"{get_global_i18n().t('crawler.copy_ids_success')}: {count} {get_global_i18n().t('crawler.books_count')}")
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.copy_ids_failed')}: {str(e)}", "error")
    
    def _start_crawl(self) -> None:
        """开始爬取小说"""
        # 权限校验：执行爬取任务需 crawler.run
        if not getattr(self.app, "has_permission", lambda k: True)("crawler.run"):
            self._update_status(get_global_i18n().t('crawler.np_crawler'), "error")
            return
        if self.is_crawling:
            self._update_status(get_global_i18n().t('crawler.crawling_in_progress'), "warning")
            return  # 如果正在爬取，忽略新的爬取请求
        
        # 设置爬取状态
        self.is_crawling = True
        self._update_crawl_button_state()
        
        novel_id_input = self.query_one("#novel-id-input", Input)
        novel_ids_input = novel_id_input.value.strip()
        
        if not novel_ids_input:
            self._update_status(get_global_i18n().t('crawler.enter_novel_id'))
            return
        
        # 分割多个小说ID
        novel_ids = [id.strip() for id in novel_ids_input.split(',') if id.strip()]
        
        # 对每个书籍ID进行URL解码（如果是URL编码的话）
        novel_ids = [unquote(id) for id in novel_ids]
        
        if not novel_ids:
            self._update_status(get_global_i18n().t('crawler.enter_novel_id'))
            return
        
        # 验证每个小说ID格式（支持多种格式：数字、字母、中文、日期路径等）
        invalid_ids = []
        for novel_id in novel_ids:
            # 支持以下格式：
            # 1. 2022/02/blog-post_70 (日期路径格式)
            # 2. 中文标题名 (纯中文)
            # 3. 2025/06/09/中文标题 (混合格式)
            # 4. 数字字母组合 (如68fa7dcff3de0)
            if not novel_id:
                invalid_ids.append(novel_id)
                continue
            
            # 检查是否包含非法字符（简化验证，主要排除英文逗号作为分隔符）
            # 允许的字符：字母、数字、中文、常见标点符号、空格等
            # 注意：英文逗号(,)用于分隔多个ID，所以不能在单个ID中使用
            if ',' in novel_id:
                invalid_ids.append(novel_id)
        
        if invalid_ids:
            self._update_status(f"{get_global_i18n().t('crawler.invalid_novel_id')}: {', '.join(invalid_ids)}")
            return
        
        # 检查是否已经下载过且文件存在
        site_id = self.novel_site.get('id')
        existing_novels = []
        if site_id:
            for novel_id in novel_ids:
                if self.db_manager.check_novel_exists(site_id, novel_id):
                    existing_novels.append(novel_id)
        
        if existing_novels:
            # 自动跳过并清理已存在的ID
            try:
                for _eid in existing_novels:
                    # 清理输入框中的已存在ID
                    self.app.call_later(self._remove_id_from_input, _eid)
                    # 单独提示每个被跳过的ID
                    try:
                        self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.skipped')}: {_eid}", "information")
                    except Exception:
                        pass
            except Exception:
                pass
            # 过滤掉已存在的ID，继续爬取剩余的
            novel_ids = [nid for nid in novel_ids if nid not in existing_novels]
            if not novel_ids:
                self._update_status(f"{get_global_i18n().t('crawler.novel_already_exists')}: {', '.join(existing_novels)}")
                # 重置爬取状态和按钮状态
                self.is_crawling = False
                self._update_crawl_button_state()
                return
            else:
                # 汇总提示，继续爬取剩余ID
                self._update_status(f"{get_global_i18n().t('crawler.novel_already_exists')}: {', '.join(existing_novels)}，{get_global_i18n().t('crawler.skip')}", "information")
        
        # 检查代理要求
        proxy_check_result = self._check_proxy_requirements_sync()
        if not proxy_check_result['can_proceed']:
            self._update_status(proxy_check_result['message'], "error")
            return
        
        proxy_config = proxy_check_result['proxy_config']
        
        # 清空之前的提示信息
        self._update_status("")
        
        # 使用后台爬取管理器启动任务
        site_id = self.novel_site.get('id')
        if not site_id:
            # 回滚爬取状态
            self.is_crawling = False
            self._update_crawl_button_state()
            self._update_status(get_global_i18n().t('crawler.no_site_id'), "error")
            return
        
        # 启动后台爬取任务
        try:
            task_id = self.crawler_manager.start_crawl_task(site_id, novel_ids, proxy_config)
            if not task_id:
                # 任务启动失败，回滚状态
                self.is_crawling = False
                self._update_crawl_button_state()
                self._update_status(get_global_i18n().t('crawler.start_crawl_failed'), "error")
                return
            
            self.current_task_id = task_id
            
            # 显示启动状态
            self._update_status(f"{get_global_i18n().t('crawler.starting_crawl')} ({len(novel_ids)} {get_global_i18n().t('crawler.books')})")
            
        except Exception as e:
            # 启动过程中发生异常，回滚状态
            self.is_crawling = False
            self._update_crawl_button_state()
            logger.error(f"启动爬取任务失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.start_crawl_failed')}: {str(e)}", "error")
            return
        
        # 状态更新由回调函数处理，这里不需要手动设置
    
    def _check_proxy_requirements_sync(self) -> Dict[str, Any]:
        """
        同步检查代理要求
        
        Returns:
            包含检查结果的字典
        """
        try:
            # 检查网站是否启用了代理
            proxy_enabled = self.novel_site.get('proxy_enabled', False)
            
            if not proxy_enabled:
                # 网站未启用代理，返回空代理配置
                return {
                    'can_proceed': True,
                    'proxy_config': {
                        'enabled': False,
                        'proxy_url': ''
                    },
                    'message': get_global_i18n().t('crawler.not_enabled_proxy')
                }
            
            # 网站启用了代理，获取可用的代理设置
            enabled_proxy = self.db_manager.get_enabled_proxy()
            
            if not enabled_proxy:
                # 没有启用的代理，提示用户
                return {
                    'can_proceed': False,
                    'proxy_config': None,
                    'message': get_global_i18n().t('crawler.need_proxy')
                }
            
            # 构建代理URL
            proxy_type = enabled_proxy.get('type', 'HTTP').lower()
            host = enabled_proxy.get('host', '')
            port = enabled_proxy.get('port', '')
            username = enabled_proxy.get('username', '')
            password = enabled_proxy.get('password', '')
            
            if not host or not port:
                return {
                    'can_proceed': False,
                    'proxy_config': None,
                    'message': get_global_i18n().t('crawler.proxy_error')
                }
            
            # 构建代理URL
            if username and password:
                proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"{proxy_type}://{host}:{port}"
            
            # 测试代理连接
            proxy_test_result = self._test_proxy_connection(proxy_url)
            if not proxy_test_result:
                return {
                    'can_proceed': False,
                    'proxy_config': None,
                    'message': get_global_i18n().t("crawler.proxy_error_url", proxy_url=proxy_url)
                }
            
            return {
                'can_proceed': True,
                'proxy_config': {
                    'enabled': True,
                    'proxy_url': proxy_url,
                    'name': enabled_proxy.get('name', get_global_i18n().t("crawler.unnamed_proxy"))
                },
                'message': f"{get_global_i18n().t("crawler.use_proxy")}: {enabled_proxy.get('name', get_global_i18n().t("crawler.unnamed_proxy"))} ({host}:{port})"
            }
            
        except Exception as e:
            logger.error(f"检查代理要求失败: {e}")
            return {
                'can_proceed': False,
                'proxy_config': None,
                'message': f'{get_global_i18n().t("crawler.check_proxy_failed")}: {str(e)}'
            }

    def _test_proxy_connection(self, proxy_url: str) -> bool:
        """
        测试代理连接是否可用
        
        Args:
            proxy_url: 代理URL
            
        Returns:
            bool: 代理是否可用
        """
        import requests
        import time
        
        try:
            # 设置代理
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 测试连接 - 先使用简单的网站测试代理连通性
            test_urls = [
                "http://httpbin.org/ip",  # 测试代理IP
                "https://www.baidu.com",  # 备用测试站点
                "https://www.renqixiaoshuo.net"  # 目标网站
            ]
            
            # 设置超时时间 - 增加到30秒
            timeout = 30
            connect_timeout = 15  # 连接超时
            read_timeout = 15     # 读取超时
            
            for test_url in test_urls:
                try:
                    start_time = time.time()
                    response = requests.get(
                        test_url, 
                        proxies=proxies, 
                        timeout=(connect_timeout, read_timeout),
                        stream=True,  # 使用流式下载，避免大文件下载卡住
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                            'Connection': 'keep-alive'
                        }
                    )
                    
                    # 只读取前1KB内容来验证连接
                    content = response.raw.read(1024)
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        logger.info(f"{get_global_i18n().t('crawler.test_success')}: {proxy_url} ({get_global_i18n().t('crawler.response_time')}: {end_time - start_time:.2f}s)")
                        return True
                    else:
                        logger.warning(f"测试站点 {test_url} 返回状态码: {response.status_code}")
                        # 继续尝试下一个URL
                        
                except requests.exceptions.ConnectTimeout:
                    logger.warning(f"代理连接超时 (连接超时 {connect_timeout}s): {proxy_url}")
                    continue  # 尝试下一个URL
                except requests.exceptions.ReadTimeout:
                    logger.warning(f"代理读取超时 (读取超时 {read_timeout}s): {proxy_url}")
                    continue  # 尝试下一个URL
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"代理连接错误: {proxy_url}, 错误: {e}")
                    continue  # 尝试下一个URL
                except Exception as e:
                    logger.warning(f"代理测试异常 (URL: {test_url}): {e}")
                    continue  # 尝试下一个URL
            
            # 所有URL都失败
            logger.error(f"代理测试失败: 所有测试URL都无法连接")
            return False
                
        except Exception as e:
            logger.error(f"代理测试异常: {e}")
            return False

    async def _actual_crawl_multiple(self, novel_ids: List[str], proxy_config: Dict[str, Any]) -> None:
        """实际爬取多个小说（异步执行）"""
        import asyncio
        import time
        
        # 开始爬取 - 使用app.call_later来安全地更新UI
        self.app.call_later(self._update_status, get_global_i18n().t("crawler.start_to_crawler_books", counts=len(novel_ids)))
        
        try:
            # 获取解析器名称
            parser_name = self.novel_site.get('parser')
            if not parser_name:
                self.app.call_later(self._update_status, get_global_i18n().t("crawler.no_parser"), "error")
                return
            
            # 导入解析器
            from src.spiders import create_parser
            
            # 创建解析器实例，传递数据库中的网站名称作为作者信息和网站URL
            parser = create_parser(parser_name, proxy_config, self.novel_site.get('name'), self.novel_site.get('url'))
            
            if not parser:
                self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.parser_not_found')}: {parser_name}", "error")
                return
            
            # 爬取每个小说
            success_count = 0
            failed_count = 0
            
            for i, novel_id in enumerate(novel_ids):
                if not self.is_crawling:
                    self.app.call_later(self._update_status, get_global_i18n().t('crawler.crawl_stopped'))
                    break
                
                # 更新当前爬取状态
                self.current_crawling_id = novel_id
                self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawling')} ({i+1}/{len(novel_ids)}): {novel_id}")
                
                try:
                    # 执行爬取
                    result = await self._async_parse_novel_detail(parser, novel_id)
                    
                    if result['success']:
                        success_count += 1
                        
                        # 保存到数据库
                        site_id = self.novel_site.get('id')
                        if site_id:
                            self.db_manager.add_crawl_history(
                                site_id=site_id,
                                novel_id=novel_id,
                                novel_title=result['title'],
                                status="success",
                                file_path=result['file_path'],
                                error_message=""
                            )
                        
                        self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_success')}: {novel_id}")
                        # 爬取成功后清理输入框中的ID
                        self.app.call_later(self._remove_id_from_input, novel_id)
                    else:
                        failed_count += 1
                        
                        # 保存失败记录到数据库
                        site_id = self.novel_site.get('id')
                        if site_id:
                            self.db_manager.add_crawl_history(
                                site_id=site_id,
                                novel_id=novel_id,
                                novel_title=novel_id,
                                status="failed",
                                file_path="",
                                error_message=result.get('error_message', get_global_i18n().t('crawler.unknown_error'))
                            )
                        
                        self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_failed')}: {novel_id} - {result.get('error_message', get_global_i18n().t('crawler.unknown_error'))}", "error")
                
                except Exception as e:
                    failed_count += 1
                    logger.error(f"爬取小说 {novel_id} 时发生异常: {e}")
                    
                    # 保存异常记录到数据库
                    site_id = self.novel_site.get('id')
                    if site_id:
                        self.db_manager.add_crawl_history(
                            site_id=site_id,
                            novel_id=novel_id,
                            novel_title=novel_id,
                            status="failed",
                            file_path="",
                            error_message=str(e)
                        )
                    
                    self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_exception')}: {novel_id} - {str(e)}", "error")
                
                # 短暂延迟，避免过于频繁的请求
                await asyncio.sleep(1)
            
            # 更新最终状态
            if self.is_crawling:
                self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_completed')}: {success_count} {get_global_i18n().t('crawler.success')}, {failed_count} {get_global_i18n().t('crawler.failed')}")
                
                # 刷新历史记录
                self.app.call_later(self._load_crawl_history)
            
        except Exception as e:
            logger.error(f"批量爬取过程中发生异常: {e}")
            self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.batch_crawl_exception')}: {str(e)}", "error")
        
        finally:
            # 重置爬取状态
            self.is_crawling = False
            self.current_crawling_id = None
            self.app.call_later(self._update_crawl_button_state)
            self.app.call_later(self._hide_loading_animation)
    
    def _remove_id_from_input(self, novel_id: str) -> None:
        """从输入框中移除指定的ID"""
        try:
            # 对要移除的ID进行URL解码，确保能正确匹配
            decoded_novel_id = unquote(novel_id)
            novel_id_input = self.query_one("#novel-id-input", Input)
            current_value = novel_id_input.value.strip()
            
            # 分割并对每个ID进行URL解码，然后过滤掉指定的ID
            ids = [unquote(id.strip()) for id in current_value.split(',') if id.strip()]
            filtered_ids = [id for id in ids if id != decoded_novel_id]
            
            # 重新组合并更新输入框
            if filtered_ids:
                # 如果还有其他ID，在最后一个ID后面添加逗号，方便继续输入
                novel_id_input.value = ', '.join(filtered_ids) + ','
            else:
                # 如果没有其他ID了，清空输入框
                novel_id_input.value = ''
                
            # 将光标移动到输入框末尾
            novel_id_input.action_end()
        except Exception as e:
            logger.debug(f"从输入框中移除ID失败: {e}")
    
    def _update_crawl_button_state(self) -> None:
        """更新爬取按钮状态"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟更新按钮状态")
                # 延迟100ms后重试
                self.set_timer(0.1, self._update_crawl_button_state)
                return

            # 使用正确的CSS选择器语法，需要#号
            start_crawl_button = self.query_one("#start-crawl-btn", Button)
            stop_crawl_button = self.query_one("#stop-crawl-btn", Button)
            
            if self.is_crawling:
                start_crawl_button.label = get_global_i18n().t('crawler.crawling_in_progress')
                start_crawl_button.disabled = True
                stop_crawl_button.disabled = False
            else:
                start_crawl_button.label = get_global_i18n().t('crawler.start_crawl')
                start_crawl_button.disabled = False
                stop_crawl_button.disabled = True
            
            logger.debug("爬取按钮状态更新成功")
        except Exception as e:
            # 如果按钮不存在，记录错误但不中断程序
            logger.debug(f"更新爬取按钮状态失败: {e}")
            # 延迟重试
            self.set_timer(0.1, self._update_crawl_button_state)
    
    def _show_loading_animation(self) -> None:
        """显示加载动画"""
        try:
            if self.loading_indicator:
                self.loading_indicator.styles.display = "block"
        except Exception as e:
            logger.error(f"显示加载动画失败: {e}")
    
    def _hide_loading_animation(self) -> None:
        """隐藏加载动画"""
        try:
            if self.loading_indicator:
                self.loading_indicator.styles.display = "none"
        except Exception as e:
            logger.error(f"隐藏加载动画失败: {e}")
    
    def _reset_crawl_state(self) -> None:
        """重置爬取状态"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                return
            
            # 重置所有爬取相关的状态
            self.is_crawling = False
            self.current_crawling_id = None
            self.current_task_id = None
            
            # 更新UI状态
            self._update_crawl_button_state()
            self._hide_loading_animation()
            
            # 重置状态显示
            self.app.call_later(self._update_status, get_global_i18n().t('crawler.ready'))
            
            logger.debug("爬取状态已重置")
        except Exception as e:
            logger.error(f"重置爬取状态失败: {e}")
    
    def _sync_ui_state_with_crawler(self) -> None:
        """同步UI状态与爬取器状态"""
        try:
            from src.core.crawler_manager import CrawlStatus
            
            # 检查当前是否有正在运行的任务
            if self.current_task_id:
                task = self.crawler_manager.get_task_by_id(self.current_task_id)
                if task and task.status != CrawlStatus.COMPLETED and task.status != CrawlStatus.FAILED:
                    # 任务仍在运行，同步状态
                    self.is_crawling = True
                    self.current_crawling_id = task.current_novel_id
                else:
                    # 任务已完成或失败，重置状态
                    self._reset_crawl_state()
            else:
                # 没有任务，确保状态正确
                self._reset_crawl_state()
            
            # 更新UI
            self._update_crawl_button_state()
            
        except Exception as e:
            logger.error(f"同步UI状态失败: {e}")
            # 如果同步失败，保守地重置状态
            self._reset_crawl_state()
            self.set_timer(0.1, self._reset_crawl_state)
            return

            self.is_crawling = False
            self._update_crawl_button_state()
            self._hide_loading_animation()
            
            # 自动继续爬取剩余ID（如果输入框中还有）
            try:
                novel_id_input = self.query_one("#novel-id-input", Input)
                raw = (novel_id_input.value or "").strip()
                remaining_ids = [i.strip() for i in raw.split(",") if i.strip()]
                if remaining_ids and not self.is_crawling:
                    # 在UI刷新后触发下一轮爬取
                    self.call_after_refresh(self._start_crawl)
            except Exception as e:
                logger.debug(f"重置爬取状态失败: {e}")
                # 延迟重试
                self.set_timer(0.1, self._reset_crawl_state)
    
    async def _async_parse_novel_detail(self, parser, novel_id: str) -> Dict[str, Any]:
        """异步解析小说详情
        
        Args:
            parser: 解析器实例
            novel_id: 小说ID
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        import asyncio
        import aiohttp
        
        try:
            # 使用异步方式执行网络请求
            await asyncio.sleep(0.5)  # 添加小延迟避免同时请求过多
            
            # 异步获取小说内容
            novel_url = parser.get_novel_url(novel_id)
            
            # 准备代理配置
            proxies = None
            if parser.proxy_config.get('enabled', False):
                proxy_url = parser.proxy_config.get('proxy_url', '')
                if proxy_url:
                    proxies = proxy_url
            
            # 使用aiohttp进行异步请求
            async with aiohttp.ClientSession(headers=parser.session.headers) as session:
                try:
                    # 设置超时时间
                    timeout = aiohttp.ClientTimeout(total=60, connect=15)
                    
                    # 发送异步请求
                    async with session.get(novel_url, proxy=proxies, timeout=timeout) as response:
                        if response.status == 200:
                            # 读取内容，处理编码问题
                            try:
                                # 先尝试使用UTF-8解码
                                content = await response.text()
                            except UnicodeDecodeError:
                                # 如果UTF-8失败，尝试使用其他编码
                                raw_content = await response.read()
                                # 尝试多种编码
                                encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin1']
                                content = None
                                for encoding in encodings:
                                    try:
                                        content = raw_content.decode(encoding)
                                        logger.debug(f"使用 {encoding} 编码成功解码内容")
                                        break
                                    except UnicodeDecodeError:
                                        continue
                                if content is None:
                                    logger.warning("无法解码内容，使用latin1作为最后手段")
                                    content = raw_content.decode('latin1', errors='ignore')
                            
                            # 检测并处理高级反爬虫机制
                            if parser._detect_advanced_anti_bot(content):
                                logger.warning(f"检测到高级反爬虫机制，回退到同步方法: {novel_url}")
                                # 如果检测到高级反爬虫，回退到同步方法
                                content = parser._get_url_content(novel_url)
                                if not content:
                                    return {
                                        'success': False,
                                        'error_message': f"无法获取小说页面: {novel_url}"
                                    }
                        else:
                            logger.warning(f"HTTP {response.status} 获取失败，回退到同步方法: {novel_url}")
                            # 如果异步请求失败，回退到同步方法
                            content = parser._get_url_content(novel_url)
                            if not content:
                                return {
                                    'success': False,
                                    'error_message': f"无法获取小说页面: {novel_url}"
                                }
                except Exception as async_error:
                    logger.warning(f"异步请求失败，回退到同步方法: {async_error}")
                    # 如果异步请求失败，回退到同步方法
                    content = parser._get_url_content(novel_url)
                    if not content:
                        return {
                            'success': False,
                            'error_message': f"无法获取小说页面: {novel_url}"
                        }
            
            # 自动检测书籍类型
            book_type = parser._detect_book_type(content)
            
            # 提取标题
            title = parser._extract_with_regex(content, parser.title_reg)
            if not title:
                return {
                    'success': False,
                    'error_message': "无法提取小说标题"
                }
            
            # 根据书籍类型选择处理方式
            if book_type == "多章节":
                novel_content = parser._parse_multichapter_novel(content, novel_url, title)
            elif book_type == "内容页内分页":
                novel_content = parser._parse_content_pagination_novel(content, novel_url, title)
            else:
                novel_content = parser._parse_single_chapter_novel(content, novel_url, title)
            
            # 获取存储文件夹
            storage_folder = self.novel_site.get('storage_folder', 'novels')
            # 展开路径中的 ~ 符号
            storage_folder = os.path.expanduser(storage_folder)
            
            # 保存小说到文件
            file_path = parser.save_to_file(novel_content, storage_folder)

            if file_path == 'already_exists':
                return {
                    'success': False,
                    'error_message': 'File exists'
                }
            
            return {
                'success': True,
                'title': novel_content.get('title', novel_id),
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"异步解析小说详情失败: {e}")
            return {
                'success': False,
                'error_message': str(e)
            }
    
    def _detect_advanced_anti_bot(self, content: str) -> bool:
        """
        检测是否存在高级反爬虫机制（如 Cloudflare Turnstile）
        
        Args:
            content: 页面内容
            
        Returns:
            是否存在高级反爬虫机制
        """
        try:
            import re
            turnstile_patterns = [
                r'challenges\.cloudflare\.com',
                r'cf-turnstile',
                r'data-sitekey',
                r'turnstile\.cloudflare\.com'
            ]
            
            for pattern in turnstile_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
            
            return False
        except Exception:
            return False
    
    
    
    def _view_file(self, history_item: Dict[str, Any]) -> None:
        """查看文件"""
        try:
            file_path = history_item.get('file_path')
            
            # 如果文件路径为空或为"already_exists"，尝试从数据库中重新获取
            if not file_path or file_path == 'already_exists':
                site_id = self.novel_site.get('id')
                novel_id = history_item.get('novel_id')
                if site_id and novel_id:
                    crawl_history = self.db_manager.get_crawl_history_by_novel_id(site_id, novel_id)
                    if crawl_history:
                        # 获取最新的成功记录
                        for record in crawl_history:
                            if record.get('status') == 'success' and record.get('file_path') and record.get('file_path') != 'already_exists':
                                file_path = record.get('file_path')
                                # 更新内存中的记录
                                history_item['file_path'] = file_path
                                break
            
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            # 如果文件路径仍然是"already_exists"，尝试查找实际文件
            if file_path == 'already_exists':
                # 尝试根据小说标题查找文件
                novel_title = history_item.get('novel_title', '')
                storage_folder = self.novel_site.get('storage_folder', 'novels')
                
                # 查找可能的文件
                storage_folder = os.path.expanduser(storage_folder)
                possible_files = glob.glob(os.path.join(storage_folder, f"*{novel_title}*"))
                if possible_files:
                    file_path = possible_files[0]  # 使用第一个匹配的文件
                    # 更新内存中的记录
                    history_item['file_path'] = file_path
                else:
                    self._update_status(f"{get_global_i18n().t('crawler.file_not_exists')}{get_global_i18n().t('crawler.not_found')}")
                    return
            
            if not os.path.exists(file_path):
                # 尝试更新数据库记录状态为失败
                site_id = self.novel_site.get('id')
                novel_id = history_item.get('novel_id')
                if site_id and novel_id:
                    # 查找并更新记录
                    crawl_history = self.db_manager.get_crawl_history_by_novel_id(site_id, novel_id)
                    for record in crawl_history:
                        if record.get('file_path') == file_path:
                            # 更新状态为文件不存在
                            self.db_manager.update_crawl_history_status(
                                site_id=site_id,
                                novel_id=novel_id,
                                status='failed',
                                file_path=file_path,
                                novel_title=history_item.get('novel_title', ''),
                                error_message='文件不存在'
                            )
                            # 重新加载历史记录
                            self._load_crawl_history()
                            break
                
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
                
            # 在文件管理器中显示文件
            import platform
            system = platform.system()
            
            if system == "Darwin":  # macOS
                os.system(f'open -R "{file_path}"')
            elif system == "Windows":
                os.system(f'explorer /select,"{file_path}"')
            elif system == "Linux":
                os.system(f'xdg-open "{os.path.dirname(file_path)}"')
                
            self._update_status(get_global_i18n().t('crawler.file_opened'))
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.open_file_failed')}: {str(e)}", "error")

    def _delete_file_only(self, history_item: Dict[str, Any]) -> None:
        """只删除文件，不删除数据库记录（同时删除书架中的对应书籍）"""
        try:
            file_path = history_item.get('file_path')
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
                
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        # 只删除文件，不删除数据库记录
                        send2trash(file_path)
                        logger.info(f"文件已移至回收站: {file_path}")
                        
                        # 同时删除书架中的对应书籍
                        try:
                            # 直接使用文件路径删除书架中的书籍
                            if self.db_manager.delete_book(file_path):
                                # 发送全局刷新书架消息，确保书架屏幕能够接收
                                try:
                                    from src.ui.messages import RefreshBookshelfMessage
                                    self.app.post_message(RefreshBookshelfMessage())
                                    logger.info("已发送书架刷新消息，书籍已从书架删除")
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，{get_global_i18n().t('crawler.book_deleted')}")
                                except Exception as msg_error:
                                    logger.debug(f"发送刷新书架消息失败: {msg_error}")
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，{get_global_i18n().t('crawler.refresh_failed')}")
                            else:
                                # 如果删除失败，检查书籍是否存在于书架中
                                books = self.db_manager.get_all_books()
                                book_exists = any(book.path == file_path for book in books)
                                if book_exists:
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，{get_global_i18n().t('crawler.delete_failed')}")
                                else:
                                    self._update_status(get_global_i18n().t('crawler.file_deleted'))
                        except Exception as shelf_error:
                            logger.error(f"删除书架书籍失败: {shelf_error}")
                            self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，{get_global_i18n().t('crawler.delete_error')}")
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                    except Exception as e:
                        self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（{get_global_i18n().t('crawler.delete_file_and_book')}）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')} {get_global_i18n().t('crawler.delete_book_tip')}"
                ),
                handle_delete_confirmation
            )
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")

    def _delete_record_only(self, history_item: Dict[str, Any]) -> None:
        """只删除数据库记录，不删除文件"""
        try:
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        # 只删除数据库记录，不删除文件
                        history_id = history_item.get('id')
                        if history_id:
                            self.db_manager.delete_crawl_history(history_id)
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                        self._update_status(get_global_i18n().t('crawler.file_deleted'))
                    except Exception as e:
                        self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（{get_global_i18n().t('crawler.only_delete')}）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')}"
                ),
                handle_delete_confirmation
            )
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
    
    def _delete_file(self, history_item: Dict[str, Any]) -> None:
        """删除文件（同时删除文件和记录）"""
        try:
            file_path = history_item.get('file_path')
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
                
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        # 先删除文件
                        send2trash(file_path)
                        logger.info(f"文件已移至回收站: {file_path}")
                        
                        # 从数据库中删除对应的记录
                        history_id = history_item.get('id')
                        if history_id:
                            self.db_manager.delete_crawl_history(history_id)
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                        self._update_status(get_global_i18n().t('crawler.file_deleted'))
                    except Exception as e:
                        self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（{get_global_i18n().t('crawler.both_file_data')}）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')}"
                ),
                handle_delete_confirmation
            )
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        table = self.query_one("#crawl-history-table", DataTable)
        
        # 动态计算总页数
        total_pages = max(1, (len(self.crawler_history) + self.items_per_page - 1) // self.items_per_page)
        
        # 方向键翻页功能
        if event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            if (table.cursor_row == len(table.rows) - 1 and 
                self.current_page < total_pages):
                self._go_to_next_page()
                # 将光标移动到新页面的第一行
                table.move_cursor(row=0, column=0)  # 直接移动到第一行第一列
                event.prevent_default()
                event.stop()
                return
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            if table.cursor_row == 0 and self.current_page > 1:
                self._go_to_prev_page()
                # 将光标移动到新页面的最后一行
                last_row_index = len(table.rows) - 1
                table.move_cursor(row=last_row_index, column=0)  # 直接移动到最后一行第一列
                event.prevent_default()
                event.stop()
                return
        
        if event.key == "escape":
            # ESC键返回 - 爬取继续在后台运行
            self.app.pop_screen()
            event.stop()
        
        # 数字键功能 - 根据是否有选中项执行不同操作
        if event.key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            # 0键映射到第10位
            target_position = 9 if event.key == "0" else int(event.key) - 1
            
            # 检查是否有选中项
            if self.selected_history:
                # 有选中项时，将当前光标所在行排序到指定位置
                self._move_to_position(target_position)
            else:
                # 没有选中项时，将光标移动到当前页对应行
                self._move_cursor_to_position(target_position)
            event.stop()
    
    def _view_reason(self, history_item: Dict[str, Any]) -> None:
        """查看失败原因"""
        try:
            # 检查是否为失败状态
            if history_item.get("status") != get_global_i18n().t('crawler.status_failed'):
                self._update_status(get_global_i18n().t('crawler.no_reason_to_view'), "warning")
                return
                
            # 获取错误信息
            error_message = history_item.get('error_message', '')
            
            if not error_message:
                self._update_status(get_global_i18n().t('crawler.no_error_message'), "information")
                return
                
            # 在状态信息区域显示错误信息
            self._update_status(f"{get_global_i18n().t('crawler.failure_reason')}: {error_message}", "error")
                
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.view_reason_failed')}: {str(e)}", "error")

    def _read_book(self, history_item: Dict[str, Any]) -> None:
        """阅读书籍"""
        try:
            file_path = history_item.get('file_path')
            
            # 如果文件路径为空或为"already_exists"，尝试从数据库中重新获取
            if not file_path or file_path == 'already_exists':
                site_id = self.novel_site.get('id')
                novel_id = history_item.get('novel_id')
                if site_id and novel_id:
                    crawl_history = self.db_manager.get_crawl_history_by_novel_id(site_id, novel_id)
                    if crawl_history:
                        # 获取最新的成功记录
                        for record in crawl_history:
                            if record.get('status') == 'success' and record.get('file_path') and record.get('file_path') != 'already_exists':
                                file_path = record.get('file_path')
                                # 更新内存中的记录
                                history_item['file_path'] = file_path
                                break
            
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            # 如果文件路径仍然是"already_exists"，尝试查找实际文件
            if file_path == 'already_exists':
                # 尝试根据小说标题查找文件
                novel_title = history_item.get('novel_title', '')
                storage_folder = self.novel_site.get('storage_folder', 'novels')
                
                # 查找可能的文件
                storage_folder = os.path.expanduser(storage_folder)
                possible_files = glob.glob(os.path.join(storage_folder, f"*{novel_title}*"))
                if possible_files:
                    file_path = possible_files[0]  # 使用第一个匹配的文件
                    # 更新内存中的记录
                    history_item['file_path'] = file_path
                else:
                    self._update_status(f"{get_global_i18n().t('crawler.file_not_exists')}get_global_i18n().t('crawler.not_found')")
                    return
            
            if not os.path.exists(file_path):
                # 尝试更新数据库记录状态为失败
                site_id = self.novel_site.get('id')
                novel_id = history_item.get('novel_id')
                if site_id and novel_id:
                    # 查找并更新记录
                    crawl_history = self.db_manager.get_crawl_history_by_novel_id(site_id, novel_id)
                    for record in crawl_history:
                        if record.get('file_path') == file_path:
                            # 更新状态为文件不存在
                            self.db_manager.update_crawl_history_status(
                                site_id=site_id,
                                novel_id=novel_id,
                                status='failed',
                                file_path=file_path,
                                novel_title=history_item.get('novel_title', ''),
                                error_message='文件不存在'
                            )
                            # 重新加载历史记录
                            self._load_crawl_history()
                            break
                
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
            
            # 从文件路径创建书籍对象
            from src.core.book import Book
            book_title = history_item.get('novel_title', get_global_i18n().t('crawler.unknown_book'))
            book_source = self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source'))
            book = Book(file_path, book_title, book_source)
            
            # 检查书籍是否有效
            if not book.path or not os.path.exists(book.path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
            
            # 使用 app 的 open_book 方法打开书籍（运行时安全检查，避免类型检查告警）
            open_book = getattr(self.app, "open_book", None)
            if callable(open_book):
                open_book(file_path)  # type: ignore[misc]
                self._update_status(f"{get_global_i18n().t('crawler.on_reading')}: {book_title}", "success")
            else:
                self._update_status(get_global_i18n().t('crawler.cannot_open_book'), "error")
                
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.open_failed')}: {str(e)}", "error")
    
    def _read_book_in_browser(self, history_item: Dict[str, Any]) -> None:
        """使用浏览器阅读书籍"""
        try:
            from src.utils.browser_reader import BrowserReader
            
            file_path = history_item.get('file_path')
            
            # 如果文件路径为空或为"already_exists"，尝试从数据库中重新获取
            if not file_path or file_path == 'already_exists':
                site_id = self.novel_site.get('id')
                novel_id = history_item.get('novel_id')
                if site_id and novel_id:
                    crawl_history = self.db_manager.get_crawl_history_by_novel_id(site_id, novel_id)
                    if crawl_history:
                        # 获取最新的成功记录
                        for record in crawl_history:
                            if record.get('status') == 'success' and record.get('file_path') and record.get('file_path') != 'already_exists':
                                file_path = record.get('file_path')
                                # 更新内存中的记录
                                history_item['file_path'] = file_path
                                break
            
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            # 如果文件路径仍然是"already_exists"，尝试查找实际文件
            if file_path == 'already_exists':
                # 尝试根据小说标题查找文件
                novel_title = history_item.get('novel_title', '')
                storage_folder = self.novel_site.get('storage_folder', 'novels')
                
                # 查找可能的文件
                storage_folder = os.path.expanduser(storage_folder)
                possible_files = glob.glob(os.path.join(storage_folder, f"*{novel_title}*"))
                if possible_files:
                    file_path = possible_files[0]  # 使用第一个匹配的文件
                    # 更新内存中的记录
                    history_item['file_path'] = file_path
                else:
                    self._update_status(f"{get_global_i18n().t('crawler.file_not_exists')}get_global_i18n().t('crawler.not_found')")
                    return
            
            if not os.path.exists(file_path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return

            # 捕获文件路径，避免闭包问题
            captured_file_path = file_path

            # 保存进度回调
            logger.info(f"[爬取管理-浏览器阅读] 注册进度保存回调函数: file_path={captured_file_path}")
            def on_progress_save(progress: float, scroll_top: int, scroll_height: int,
                                 current_page: Optional[int] = None, total_pages: Optional[int] = None,
                                 word_count: Optional[int] = None) -> None:
                """保存阅读进度"""
                logger.info(f"[爬取管理-浏览器阅读] 收到保存进度回调: progress={progress:.4f} (小数), scrollTop={scroll_top}px, scrollHeight={scroll_height}px")
                if current_page is not None:
                    logger.info(f"[爬取管理-浏览器阅读] current_page={current_page}, total_pages={total_pages}")
                if word_count is not None:
                    logger.info(f"[爬取管理-浏览器阅读] word_count={word_count}")

                try:
                    # 保存阅读进度到数据库
                    from src.core.bookmark import BookmarkManager
                    bookmark_manager = BookmarkManager()

                    # 如果前端没有传递页数信息，根据进度估算
                    if total_pages is None or total_pages <= 0:
                        total_pages = int(scroll_height / 1000)  # 假设每页1000px
                    if current_page is None:
                        current_page = int(progress * total_pages)

                    logger.info(f"[爬取管理-浏览器阅读] 准备保存到数据库: book_path={captured_file_path}, current_page={current_page}, total_pages={total_pages}")

                    # 保存阅读信息
                    success = bookmark_manager.save_reading_info(
                        captured_file_path,
                        current_page=current_page,
                        total_pages=total_pages,
                        reading_progress=progress,
                        scroll_top=scroll_top,
                        scroll_height=scroll_height,
                        word_count=word_count if word_count is not None else None
                    )

                    if success:
                        logger.info(f"[爬取管理-浏览器阅读] 保存浏览器阅读进度成功: {progress:.4f} ({progress*100:.2f}%), 位置: {scroll_top}px")
                    else:
                        logger.error(f"[爬取管理-浏览器阅读] 保存浏览器阅读进度失败: save_reading_info 返回 False")
                except Exception as e:
                    logger.error(f"[爬取管理-浏览器阅读] 保存阅读进度异常: {e}", exc_info=True)

            # 加载进度回调
            logger.info(f"[爬取管理-浏览器阅读] 注册进度加载回调函数: file_path={captured_file_path}")
            def on_progress_load() -> Optional[Dict[str, Any]]:
                """加载阅读进度"""
                try:
                    from src.core.bookmark import BookmarkManager
                    bookmark_manager = BookmarkManager()

                    reading_info = bookmark_manager.get_reading_info(captured_file_path)
                    logger.debug(f"[爬取管理-浏览器阅读] 从数据库获取到阅读信息: {reading_info}")

                    if reading_info:
                        progress = reading_info.get('progress', 0)
                        scroll_top = reading_info.get('scrollTop', 0)
                        scroll_height = reading_info.get('scrollHeight', 0)

                        # 只要有 progress 数据就返回，即使 scroll_top 为 0 也返回
                        if progress > 0:
                            logger.debug(f"[爬取管理-浏览器阅读] 返回阅读进度: {progress:.2f}%, 位置: {scroll_top}px, 高度: {scroll_height}px")
                            return {
                                'progress': progress,
                                'scrollTop': scroll_top,
                                'scrollHeight': scroll_height if scroll_height > 0 else 10000
                            }
                        else:
                            logger.debug("[爬取管理-浏览器阅读] 阅读进度为 0，不返回进度数据")
                    else:
                        logger.debug("[爬取管理-浏览器阅读] 数据库中没有阅读进度数据")
                except Exception as e:
                    logger.error(f"[爬取管理-浏览器阅读] 加载阅读进度失败: {e}")

                return None

            # 使用自定义浏览器阅读器打开，支持进度同步
            logger.info(f"[爬取管理-浏览器阅读] 正在打开浏览器阅读器: file_path={file_path}")
            success, message = BrowserReader.open_book_in_browser(
                file_path,
                on_progress_save=on_progress_save,
                on_progress_load=on_progress_load
            )
            logger.info(f"[爬取管理-浏览器阅读] 浏览器阅读器打开结果: success={success}, message={message}")

            if success:
                book_title = history_item.get('novel_title', get_global_i18n().t('crawler.unknown_book'))
                self._update_status(f"{message}: {book_title}", "success")
            else:
                self._update_status(message, "error")
                
        except Exception as e:
            self._update_status(f"浏览器打开失败: {str(e)}", "error")
    
    def _retry_crawl(self, history_item: Dict[str, Any]) -> None:
        """重试爬取失败的记录"""
        try:
            # 检查权限：执行爬取任务需 crawler.run
            if not getattr(self.app, "has_permission", lambda k: True)("crawler.run"):
                self._update_status(get_global_i18n().t('crawler.np_crawler'), "error")
                return
                
            # 检查是否正在爬取
            if self.is_crawling:
                self._update_status(get_global_i18n().t('crawler.crawling_in_progress'), "error")
                return
                
            # 获取小说ID
            novel_id = history_item.get('novel_id')
            if not novel_id:
                self._update_status(get_global_i18n().t('crawler.invalid_novel_id'), "error")
                return
                
            # 检查记录是否为失败状态
            if history_item.get('status') != get_global_i18n().t('crawler.status_failed'):
                self._update_status(get_global_i18n().t('crawler.only_retry_failed'), "error")
                return
            
            # 注意：手动重试时不检查历史失败次数，允许用户主动重试
            # 只有在自动爬取时才会检查连续失败次数限制
                
            # 检查代理要求
            proxy_check_result = self._check_proxy_requirements_sync()
            if not proxy_check_result['can_proceed']:
                self._update_status(proxy_check_result['message'], "error")
                return
                
            proxy_config = proxy_check_result['proxy_config']
            
            # 设置爬取状态
            self.is_crawling = True
            self.current_crawling_id = novel_id
            
            # 更新按钮状态和显示加载动画
            self._update_crawl_button_state()
            self._show_loading_animation()
            
            # 显示重试状态
            self._update_status(f"{get_global_i18n().t('crawler.retrying')} ID: {novel_id}")
            
            # 异步执行重试爬取
            self.app.run_worker(self._retry_crawl_single(novel_id, proxy_config, history_item), name="crawl-retry-worker")
            
        except Exception as e:
            logger.error(f"重试爬取失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.retry_failed')}: {str(e)}", "error")
            # 重置爬取状态
            self._reset_crawl_state()
    
    async def _retry_crawl_single(self, novel_id: str, proxy_config: Dict[str, Any], history_item: Dict[str, Any]) -> None:
        """异步重试单个小说的爬取"""
        import asyncio
        import time
        
        try:
            # 获取解析器名称
            parser_name = self.novel_site.get('parser')
            if not parser_name:
                self.app.call_later(self._update_status, get_global_i18n().t('crawler.no_parser'), "error")
                return
            
            # 导入解析器
            from src.spiders import create_parser
            
            # 创建解析器实例，传递数据库中的网站名称作为作者信息和网站URL
            parser_instance = create_parser(parser_name, proxy_config, self.novel_site.get('name'), self.novel_site.get('url'))
            
            # 使用异步方式执行网络请求
            await asyncio.sleep(0.5)  # 添加小延迟避免同时请求过多
            
            # 解析小说详情
            novel_content = await self._async_parse_novel_detail(parser_instance, novel_id)
            
            # 检查解析是否成功
            if not novel_content.get('success', False):
                error_msg = novel_content.get('error_message', get_global_i18n().t('crawler.parse_failed'))
                logger.warning(f"重试解析失败: {error_msg}")
                
                # 检查是否是临时错误，如果是则等待后重试
                if any(keyword in error_msg.lower() for keyword in ['timeout', 'connection', 'network', 'ssl', 'verify', 'nonetype', 'string or bytes-like']):
                    logger.info(f"检测到临时错误，5秒后自动重试...")
                    await asyncio.sleep(5)
                    
                    # 重试一次
                    try:
                        logger.info(f"开始第二次重试: novel_id={novel_id}")
                        novel_content = await self._async_parse_novel_detail(parser_instance, novel_id)
                        if novel_content.get('success', False):
                            logger.info("第二次重试成功！")
                        else:
                            logger.error(f"第二次重试仍然失败: {novel_content.get('error_message', '未知错误')}")
                    except Exception as retry_error:
                        logger.error(f"第二次重试异常: {retry_error}")
                        novel_content = {'success': False, 'error_message': f'重试异常: {str(retry_error)}'}
                
                # 如果最终还是失败，更新数据库记录
                if not novel_content.get('success', False):
                    site_id = self.novel_site.get('id')
                    if site_id:
                        self.db_manager.update_crawl_history_status(
                            site_id=site_id,
                            novel_id=novel_id,
                            status='failed',
                            novel_title=history_item.get('novel_title', ''),
                            error_message=novel_content.get('error_message', get_global_i18n().t('crawler.parse_failed'))
                        )
                    
                    # 更新内存中的历史记录
                    for i, item in enumerate(self.crawler_history):
                        if item.get('novel_id') == novel_id and item.get('status') == get_global_i18n().t('crawler.status_failed'):
                            self.crawler_history[i] = {
                                "novel_id": novel_id,
                                "novel_title": history_item.get('novel_title', ''),
                                "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "status": get_global_i18n().t('crawler.status_failed'),
                                "error_message": novel_content.get('error_message', '解析失败')
                            }
                            break
                    
                    # 更新状态
                    self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.retry_failed')}: {novel_content.get('error_message', '解析失败')}", "error")
                    return
            
            # 解析成功，获取标题
            novel_title = novel_content.get('title', history_item.get('novel_title', ''))
            file_path = novel_content.get('file_path', '')
            
            logger.info(f"=== 重试成功 === novel_id={novel_id}, novel_title={novel_title}, file_path={file_path}")
            
            # 更新数据库中的记录
            site_id = self.novel_site.get('id')
            logger.info(f"准备更新数据库状态: site_id={site_id}, novel_id={novel_id}, novel_title={novel_title}")
            if site_id:
                logger.info(f"调用 update_crawl_history_status 更新状态为 success")
                success = self.db_manager.update_crawl_history_status(
                    site_id=site_id,
                    novel_id=novel_id,
                    status='success',
                    novel_title=novel_title,
                    file_path=file_path,
                    error_message=''
                )
                logger.info(f"update_crawl_history_status 返回结果: {success}")
            else:
                logger.error(f"无法获取 site_id，novel_site={self.novel_site}")
            
            # 更新内存中的历史记录
            for i, item in enumerate(self.crawler_history):
                if item.get('novel_id') == novel_id and item.get('status') == get_global_i18n().t('crawler.status_failed'):
                    self.crawler_history[i] = {
                        "novel_id": novel_id,
                        "novel_title": novel_title,
                        "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": get_global_i18n().t('crawler.status_success'),
                        "file_path": file_path
                    }
                    break
            
            # 自动将书籍加入书架
            try:
                # 将新书加入书架（优先使用内存书架以便立刻可读，失败时退回直接写DB）
                try:
                    bs = getattr(self.app, "bookshelf", None)
                    book = None
                    if bs and hasattr(bs, "add_book"):
                        # 使用"未知作者"而不是硬编码的网站名称作为author
                        author = "未知作者"
                        # 获取网站标签
                        site_tags = self.novel_site.get('tags', '')
                        book = bs.add_book(file_path, author=author, tags=site_tags)
                    if not book:
                        from src.core.book import Book
                        # 使用"未知作者"而不是硬编码的网站名称作为author
                        author = "未知作者"
                        # 获取网站标签
                        site_tags = self.novel_site.get('tags', '')
                        book = Book(file_path, novel_title, author, tags=site_tags)
                        self.db_manager.add_book(book)
                        
                    # 发送全局刷新书架消息
                    try:
                        from src.ui.messages import RefreshBookshelfMessage
                        self.app.post_message(RefreshBookshelfMessage())
                        logger.info(f"已发送书架刷新消息，书籍已添加到书架: {novel_title}")
                    except Exception as msg_error:
                        logger.debug(f"发送刷新书架消息失败: {msg_error}")
                        
                except Exception as add_err:
                    logger.error(f"添加书籍到书架失败: {add_err}")
                    logger.warning(f"添加书籍到书架失败: {novel_title}")
                    
            except Exception as e:
                logger.error(f"添加书籍到书架失败: {e}")
            
            # 重新加载数据库中的历史记录
            self.app.call_later(self._load_crawl_history)
            
            # 显示成功消息
            self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.retry_success')}: {novel_title}", "success")
            
            # 发送全局爬取完成通知
            try:
                from src.ui.messages import CrawlCompleteNotification
                self.app.post_message(CrawlCompleteNotification(
                    success=True,
                    novel_title=novel_title,
                    message=f"{get_global_i18n().t('crawler.retry_success')}: {novel_title}"
                ))
            except Exception as msg_error:
                logger.debug(f"发送爬取完成通知失败: {msg_error}")
            
            # 重置爬取状态
            self.app.call_later(self._reset_crawl_state)
        except Exception as e:
            logger.error(f"重试爬取过程失败: {e}")
            self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.retry_failed')}: {str(e)}", "error")
    
    def _check_and_continue_crawl(self) -> None:
        """检查输入框中是否还有新ID，如果有则继续爬取"""
        try:
            # 检查是否正在爬取
            if self.is_crawling:
                return
            
            # 获取输入框内容
            novel_id_input = self.query_one("#novel-id-input", Input)
            novel_ids_input = novel_id_input.value.strip()
            
            if not novel_ids_input:
                # 输入框为空，停止爬取
                self._update_status(get_global_i18n().t('crawler.crawl_finished'))
                return
            
            # 分割多个小说ID
            novel_ids = [id.strip() for id in novel_ids_input.split(',') if id.strip()]
            
            if not novel_ids:
                # 没有有效的ID，停止爬取
                self._update_status(get_global_i18n().t('crawler.crawl_finished'))
                return
            
            # 过滤掉已存在的ID和连续失败3次以上的ID
            site_id = self.novel_site.get('id')
            if site_id:
                valid_novel_ids = []
                skipped_novel_ids = []
                for novel_id in novel_ids:
                    # 检查是否已存在
                    if self.db_manager.check_novel_exists(site_id, novel_id):
                        continue
                    
                    # 检查连续失败次数
                    consecutive_failures = self.db_manager.get_consecutive_failure_count(site_id, novel_id)
                    if consecutive_failures >= 3:
                        skipped_novel_ids.append(novel_id)
                        logger.info(f"自动跳过小说 {novel_id}，连续失败次数已达 {consecutive_failures} 次")
                        continue
                    
                    valid_novel_ids.append(novel_id)
                
                # 更新输入框内容，只保留有效的ID
                novel_id_input.value = ', '.join(valid_novel_ids)
                novel_ids = valid_novel_ids
                
                # 如果有被跳过的ID，显示信息
                if skipped_novel_ids:
                    self._update_status(f"已跳过 {len(skipped_novel_ids)} 个连续失败3次以上的小说", "warning")
                
                if not valid_novel_ids:
                    # 没有有效的ID，停止爬取
                    if skipped_novel_ids:
                        self._update_status(get_global_i18n().t('crawler.no_valid_novels'), "warning")
                    else:
                        self._update_status(get_global_i18n().t('crawler.all_novels_exist'))
                    novel_id_input.value = ""  # 清空输入框
                    return
            
            # 检查代理要求
            proxy_check_result = self._check_proxy_requirements_sync()
            if not proxy_check_result['can_proceed']:
                self._update_status(proxy_check_result['message'], "error")
                return
            
            proxy_config = proxy_check_result['proxy_config']
            
            # 设置爬取状态
            self.is_crawling = True
            self._update_crawl_button_state()
            
            # 使用后台爬取管理器启动任务
            site_id = self.novel_site.get('id')
            if not site_id:
                self._update_status(get_global_i18n().t('crawler.no_site_id'), "error")
                return
            
            # 启动后台爬取任务
            task_id = self.crawler_manager.start_crawl_task(site_id, novel_ids, proxy_config)
            self.current_task_id = task_id
            
            # 显示启动状态
            self._update_status(f"{get_global_i18n().t('crawler.continuing_crawl')} ({len(novel_ids)} {get_global_i18n().t('crawler.books')})")
            
        except Exception as e:
            logger.error(f"自动继续爬取检查失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.continue_crawl_failed')}: {str(e)}", "error")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        button_id = event.button.id
        
        if button_id == "open-browser-btn":
            self._open_browser()
        elif button_id == "view-history-btn":
            self._view_history()
        elif button_id == "note-btn":
            self._open_note_dialog()
        elif button_id == "view-logs-btn":
            self._open_log_viewer()
        elif button_id == "clear-invalid-btn":
            self._clear_invalid_records()
        elif button_id == "delete-file-btn":
            self._batch_delete_files()
        elif button_id == "delete-record-btn":
            self._batch_delete_records()
        elif button_id == "back-btn":
            self.app.pop_screen()
        elif button_id == "search-btn":
            self._perform_search()
            # 执行搜索后，保持焦点在搜索框
            self.set_timer(0.1, lambda: self._focus_search_input())
        elif button_id == "clear-search-btn":
            self._clear_search()
            # 清除搜索后，保持焦点在搜索框
            self.set_timer(0.1, lambda: self._focus_search_input())
        elif button_id == "start-crawl-btn":
            self._start_crawl()
        elif button_id == "stop-crawl-btn":
            self._stop_crawl()
        elif button_id == "copy-ids-btn":
            self._copy_novel_ids()
        elif button_id == "choose-books-btn":
            self._open_select_books_dialog()
        elif button_id == "first-page-btn":
            self._go_to_first_page()
        elif button_id == "prev-page-btn":
            self._go_to_prev_page()
        elif button_id == "next-page-btn":
            self._go_to_next_page()
        elif button_id == "last-page-btn":
            self._go_to_last_page()
        elif button_id == "jump-page-btn":
            self._show_jump_dialog()
        elif button_id == "select-all-btn":
            self._select_all_rows()
        elif button_id == "invert-selection-btn":
            self._invert_selection()
        elif button_id == "deselect-all-btn":
            self._deselect_all_rows()
        elif button_id == "move-up-btn":
            self._move_selected_up()
        elif button_id == "move-down-btn":
            self._move_selected_down()
        elif button_id == "merge-btn":
            self._merge_selected()
        elif button_id == "toggle-monitor-btn":
            self._toggle_browser_monitor()
    
    def _batch_delete_files(self) -> None:
        """批量删除选中的文件"""
        try:
            # 获取选中的记录ID
            selected_ids = self.selected_history
            if not selected_ids:
                self._update_status(get_global_i18n().t('batch_ops.no_selected_rows'), "warning")
                return
            
            # 从crawler_history中获取对应的完整行数据
            selected_rows = []
            for item in self.crawler_history:
                if str(item.get("id")) in selected_ids:
                    selected_rows.append(item)
            
            if not selected_rows:
                self._update_status(get_global_i18n().t('batch_ops.no_data'), "warning")
                return
            
            # 检查权限
            if not getattr(self.app, "has_permission", lambda k: True)("crawler.delete_file"):
                self._update_status(get_global_i18n().t('crawler.np_delete_file'), "error")
                return
            
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        deleted_count = 0
                        failed_count = 0
                        
                        for row_data in selected_rows:
                            file_path = row_data.get('file_path')
                            if not file_path:
                                continue
                                
                            try:
                                import os
                                # 检查文件是否存在
                                if os.path.exists(file_path):
                                    # 删除文件
                                    send2trash(file_path)
                                    logger.info(f"文件已移至回收站: {file_path}")
                                    
                                    # 同时删除书架中的对应书籍
                                    try:
                                        if self.db_manager.delete_book(file_path):
                                            # 发送全局刷新书架消息
                                            try:
                                                from src.ui.messages import RefreshBookshelfMessage
                                                self.app.post_message(RefreshBookshelfMessage())
                                            except Exception as msg_error:
                                                logger.debug(f"发送刷新书架消息失败: {msg_error}")
                                    except Exception as shelf_error:
                                        logger.error(f"删除书架书籍失败: {shelf_error}")
                                        
                                    deleted_count += 1
                                else:
                                    failed_count += 1
                            except Exception as e:
                                logger.error(f"删除文件失败: {file_path}, 错误: {e}")
                                failed_count += 1
                        
                        # 清除选中状态
                        self.selected_history.clear()
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                        
                        # 显示结果
                        if failed_count > 0:
                            self._update_status(get_global_i18n().t('crawler.multi_delete_file_success', deletes=deleted_count, fails=failed_count), "warning")
                        else:
                            self._update_status(get_global_i18n().t('crawler.multi_delete_file_success2', deletes=deleted_count), "success")
                        
                        
                    except Exception as e:
                        self._update_status(get_global_i18n().t('crawler.multi_delete_file_failed', err=str(e)), "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t('crawler.confirm_title', counts=len(selected_rows)),
                    get_global_i18n().t('crawler.confirm_desc', counts=len(selected_rows))
                ),
                handle_delete_confirmation
            )
            
        except Exception as e:
            self._update_status(get_global_i18n().t('crawler.multi_delete_file_failed', err=str(e)), "error")
    
    def _batch_delete_records(self) -> None:
        """批量删除选中的数据库记录"""
        try:
            # 获取选中的记录ID
            selected_ids = self.selected_history
            if not selected_ids:
                self._update_status(get_global_i18n().t('batch_ops.no_selected_rows'), "warning")
                return
            
            # 检查权限
            if not getattr(self.app, "has_permission", lambda k: True)("crawler.delete_record"):
                self._update_status(get_global_i18n().t('crawler.np_delete_record'), "error")
                return
            
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        deleted_count = 0
                        failed_count = 0
                        
                        for record_id in selected_ids:
                            try:
                                # 删除数据库记录，将字符串ID转换为整数
                                if self.db_manager.delete_crawl_history(int(record_id)):
                                    deleted_count += 1
                                else:
                                    failed_count += 1
                            except Exception as e:
                                logger.error(f"删除记录失败: {record_id}, 错误: {e}")
                                failed_count += 1
                        
                        # 清除选中状态
                        self.selected_history.clear()
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                        
                        # 显示结果
                        if failed_count > 0:
                            self._update_status(get_global_i18n().t('crawler.multi_delete_record_success', deletes=deleted_count, fails=failed_count), "warning")
                        else:
                            self._update_status(get_global_i18n().t('crawler.multi_delete_record_success2', deletes=deleted_count), "success")
                        
                          
                    except Exception as e:
                        self._update_status(get_global_i18n().t('crawler.multi_delete_record_failed', err=str(e)), "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t('crawler.confirm_record_title', counts=len(selected_ids)),
                    get_global_i18n().t('crawler.confirm_record_desc', counts=len(selected_ids))
                ),
                handle_delete_confirmation
            )

        except Exception as e:
            self._update_status(get_global_i18n().t('crawler.confirm_record_title', err=str(e)), "error")

    def _clear_invalid_records(self) -> None:
        """清理无效记录（没有文件的记录和爬取失败的记录）"""
        try:
            # 获取网站ID
            site_id = self.novel_site.get('id')
            if not site_id:
                self._update_status(get_global_i18n().t('crawler.no_site_id'), "error")
                return

            # 检查权限
            if not getattr(self.app, "has_permission", lambda k: True)("crawler.delete_record"):
                self._update_status(get_global_i18n().t('crawler.np_clear_invalid'), "error")
                return

            # 查询无效记录
            import sqlite3
            invalid_records = []
            try:
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # 1. 查询所有失败的记录
                    cursor.execute("""
                        SELECT id, novel_id, novel_title, file_path, status, error_message
                        FROM crawl_history
                        WHERE site_id = ? AND status = 'failed'
                    """, (site_id,))
                    failed_rows = cursor.fetchall()
                    for row in failed_rows:
                        invalid_records.append(dict(row))

                    # 2. 查询所有成功的记录，然后检查文件是否存在
                    cursor.execute("""
                        SELECT id, novel_id, novel_title, file_path, status, error_message
                        FROM crawl_history
                        WHERE site_id = ? AND status = 'success'
                    """, (site_id,))
                    success_rows = cursor.fetchall()
                    for row in success_rows:
                        record = dict(row)
                        # 检查文件路径是否为空或文件是否存在
                        if not record.get('file_path') or not os.path.exists(record['file_path']):
                            invalid_records.append(record)

            except Exception as e:
                logger.error(f"查询无效记录失败: {e}")
                self._update_status(get_global_i18n().t('crawler.clear_invalid_failed', error=str(e)), "error")
                return

            # 如果没有无效记录
            if not invalid_records:
                self._update_status(get_global_i18n().t('crawler.clear_invalid_no_data'), "information")
                return

            # 显示确认对话框
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_clear_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        deleted_count = 0
                        failed_count = 0

                        # 删除所有无效记录
                        for record in invalid_records:
                            try:
                                record_id = record['id']
                                if self.db_manager.delete_crawl_history(record_id):
                                    deleted_count += 1
                                else:
                                    failed_count += 1
                            except Exception as e:
                                logger.error(f"删除记录失败: {record['id']}, 错误: {e}")
                                failed_count += 1

                        # 刷新历史记录
                        self._load_crawl_history()

                        # 显示结果
                        if failed_count > 0:
                            self._update_status(
                                get_global_i18n().t('crawler.clear_invalid_success', success=deleted_count, fail=failed_count),
                                "warning"
                            )
                        else:
                            self._update_status(
                                get_global_i18n().t('crawler.clear_invalid_success', success=deleted_count, fail=failed_count),
                                "success"
                            )
                    except Exception as e:
                        logger.error(f"清理无效记录失败: {e}")
                        self._update_status(get_global_i18n().t('crawler.clear_invalid_failed', error=str(e)), "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))

            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t('crawler.clear_invalid_confirm'),
                    get_global_i18n().t('crawler.clear_invalid_desc', count=len(invalid_records))
                ),
                handle_clear_confirmation
            )

        except Exception as e:
            logger.error(f"清理无效记录操作失败: {e}")
            self._update_status(get_global_i18n().t('crawler.clear_invalid_failed', error=str(e)), "error")

    # Chrome标签页监听器相关方法
    def _init_browser_monitor(self) -> None:
        """初始化浏览器标签页监听器"""
        try:
            # 初始化浏览器监听器（AppleScript模式） - 只监听当前网站
            # 根据选择确定浏览器类型
            if self.selected_browser == "safari":
                browser_type = BrowserType.SAFARI
            elif self.selected_browser == "brave":
                browser_type = BrowserType.BRAVE
            elif self.selected_browser == "firefox":
                browser_type = BrowserType.FIREFOX
            else:  # chrome
                browser_type = BrowserType.CHROME

            try:
                self.browser_monitor = BrowserTabMonitor(
                    novel_sites=[self.novel_site],  # 只传入当前网站，而不是所有网站
                    on_url_detected=self._on_browser_url_detected,
                    headless=False,  # AppleScript模式不需要headless
                    browser_type=browser_type  # 传递浏览器类型
                )
                logger.info(f"初始化监听器: selected_browser={self.selected_browser}, browser_type={browser_type}, BrowserType.SAFARI={BrowserType.SAFARI}")
                logger.info(f"{self.selected_browser}浏览器标签页监听器初始化成功")
            except Exception as e:
                logger.error(f"{self.selected_browser}监听器初始化失败: {e}")
                self.browser_monitor = None

        except Exception as e:
            logger.error(f"初始化浏览器监听器失败: {e}")

    def _reinit_monitor_with_browser(self) -> None:
        """使用新浏览器类型重新初始化监听器"""
        try:
            # 停止并清理旧监听器
            if self.browser_monitor and hasattr(self.browser_monitor, 'stop_monitoring'):
                self.browser_monitor.stop_monitoring()

            # 将旧监听器设置为None
            self.browser_monitor = None

            # 重新初始化监听器
            self._init_browser_monitor()
            self.browser_monitor_active = False

            logger.info(f"监听器已重新初始化,使用浏览器类型: {self.selected_browser}")

        except Exception as e:
            logger.error(f"重新初始化监听器失败: {e}")
            self._update_status(f"初始化浏览器监听器失败: {str(e)}", "error")

    def _on_browser_url_detected(self, result: Dict[str, Any]) -> None:
        """
        Chrome监听器检测到URL时的回调函数
        
        Args:
            result: 包含网站信息、小说ID和URL的字典
        """
        try:
            site = result.get('site_config')
            novel_id = result['novel_id']
            url = result['url']
            
            logger.info(f"检测到小说URL: {url}, 小说ID: {novel_id}")
            
            # 验证书籍ID是否已爬取过
            if self._is_novel_already_crawled(site.get('id'), novel_id):
                logger.info(f"小说 {novel_id} 已爬取过，跳过")
                # 关闭对应的标签页
                if self.browser_monitor:
                    self.browser_monitor.close_tab(url)
                return
            
            # 将小说ID添加到输入框
            self._add_novel_id_to_input(novel_id)
            
            # 关闭对应的标签页
            if self.browser_monitor:
                self.browser_monitor.close_tab(url)
            
            # 更新状态
            novel_title = site.get('name', '未知网站')
            self._update_status(f"自动检测到小说: {novel_id} ({novel_title})", "success")
            
        except Exception as e:
            logger.error(f"处理检测到的URL失败: {e}")

    def _get_log_file_path(self) -> str:
        """
        获取当前日志文件路径
        
        Returns:
            str: 日志文件路径
        """
        try:
            # 获取配置管理器
            config_manager = ConfigManager.get_instance()
            
            # 获取日志目录
            log_dir = os.path.join(os.path.expanduser("~"), ".config", "new_preader", "logs")
            
            # 根据调试模式确定日志文件名
            if config_manager.get_debug_mode():
                # 开发模式使用带日期的日志文件
                from datetime import date
                log_file = os.path.join(log_dir, f'application_{date.today()}.log')
            else:
                # 生产模式使用应用主日志文件
                log_file = os.path.join(log_dir, 'application.log')
            
            # 如果主日志文件不存在，尝试查找最新的日志文件
            if not os.path.exists(log_file):
                if os.path.exists(log_dir):
                    # 查找目录下最新的.log文件
                    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                    if log_files:
                        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
                        log_file = os.path.join(log_dir, log_files[0])
            
            return log_file
            
        except Exception as e:
            logger.error(f"获取日志文件路径失败: {e}")
            # 返回默认路径
            return os.path.join(os.path.expanduser("~"), ".config", "new_preader", "logs", "application.log")

    def _open_log_viewer(self) -> None:
        """打开日志查看器弹窗"""
        try:
            log_file_path = self._get_log_file_path()
            
            # 检查日志文件是否存在
            if not os.path.exists(log_file_path):
                self._update_status(get_global_i18n().t('crawler.log_file_not_found'), "warning")
                self.app.notify(f"📁 {get_global_i18n().t('crawler.log_file_not_found')}")
                return
            
            # 检查是否已经有日志查看器弹窗存在
            existing_screens = self.app.screen_stack
            log_viewer_exists = any(isinstance(screen, LogViewerPopup) for screen in existing_screens)
            
            if log_viewer_exists:
                # 如果弹窗已存在，不重复显示消息
                return
            
            # 创建并显示日志查看器弹窗
            log_viewer = LogViewerPopup(log_file_path)
            self.app.push_screen(log_viewer)
            
            self._update_status(f"📋 {get_global_i18n().t('crawler.log_viewer_opened')}", "information")
            self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_opened')}")
            
        except Exception as e:
            logger.error(f"打开日志查看器失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.open_log_viewer_failed')}: {e}", "error")
            self.app.notify(f"❌ {get_global_i18n().t('crawler.open_log_viewer_failed')}: {e}")

    def _is_novel_already_crawled(self, site_id: str, novel_id: str) -> bool:
        """
        检查小说是否已经爬取过
        
        Args:
            site_id: 网站ID
            novel_id: 小说ID
            
        Returns:
            是否已爬取过
        """
        try:
            # 从数据库查询
            crawl_history = self.db_manager.get_crawl_history_by_novel_id(site_id, novel_id)
            if crawl_history:
                # 检查是否有成功的记录
                for record in crawl_history:
                    if record.get('status') == 'success':
                        return True
            return False
            
        except Exception as e:
            logger.error(f"检查小说爬取状态失败: {e}")
            return False

    def _add_novel_id_to_input(self, novel_id: str) -> None:
        """
        将小说ID添加到输入框（追加形式）
        
        Args:
            novel_id: 小说ID
        """
        try:
            input_field = self.query_one("#novel-id-input", Input)
            current_value = input_field.value.strip()
            
            # URL解码小说ID
            from urllib.parse import unquote
            decoded_novel_id = unquote(novel_id)
            
            if current_value:
                # 如果已有内容，用逗号追加到末尾
                new_value = f"{current_value},{decoded_novel_id}"
            else:
                # 如果为空，直接设置
                new_value = decoded_novel_id
            
            input_field.value = new_value
            logger.info(f"已将小说ID {decoded_novel_id} 添加到输入框")
            
        except Exception as e:
            logger.error(f"添加小说ID到输入框失败: {e}")

    def _toggle_browser_monitor(self) -> None:
            """切换监听状态"""
            try:
                if self.browser_monitor_active:
                    self._stop_browser_monitor()
                else:
                    self._start_browser_monitor()
            except Exception as e:
                logger.error(f"切换监听状态失败: {e}")
                self._update_status(f"切换监听状态失败: {str(e)}", "error")

    def _start_browser_monitor(self) -> None:
        """开始监听"""
        try:
            if not self.browser_monitor:
                self._update_status("监听器未初始化", "error")
                return
            
            success = self.browser_monitor.start_monitoring()
            if success:
                self.browser_monitor_active = True
                self._update_status(get_global_i18n().t('crawler.monitor_started'), "success")
                self._update_monitor_button_state()
            else:
                self._update_status(get_global_i18n().t('crawler.monitor_start_failed'), "error")
                
        except Exception as e:
            logger.error(f"启动监听失败: {e}")
            self._update_status(f"启动监听失败: {str(e)}", "error")

    def _stop_browser_monitor(self) -> None:
        """停止监听"""
        try:
            # 停止Chrome监听
            if self.browser_monitor:
                success = self.browser_monitor.stop_monitoring()
                if not success:
                    logger.warning("停止监听可能未完全成功")
            
            self.browser_monitor_active = False
            self._update_status(get_global_i18n().t('crawler.monitor_stopped'), "information")
            self._update_monitor_button_state()
            
        except Exception as e:
            logger.error(f"停止监听失败: {e}")
            self._update_status(f"停止监听失败: {str(e)}", "error")
    def _update_monitor_button_state(self) -> None:
        """更新监听按钮状态"""
        try:
            toggle_btn = self.query_one("#toggle-monitor-btn", Button)
            if self.browser_monitor_active:
                toggle_btn.label = get_global_i18n().t("crawler.stop_monitor")
                toggle_btn.variant = "error"
            else:
                toggle_btn.label = get_global_i18n().t("crawler.start_monitor")
                toggle_btn.variant = "success"
        except Exception:
            pass

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        """
        下拉选择框值变化时的回调

        Args:
            event: 下拉选择框变化事件
        """
        if event.select.id == "browser-select" and event.value is not None:
            # 更新当前选择的浏览器
            self.selected_browser = event.value
            browser_name = {
                "chrome": "Chrome",
                "safari": "Safari",
                "brave": "Brave"
            }.get(self.selected_browser, "Chrome")
            logger.info(f"浏览器选择已更改为: {browser_name}")
            self._update_status(get_global_i18n().t("crawler.browser_changed", browser=browser_name), "information")
            # 保存浏览器配置
            self._save_browser_config()

            # 检查当前监听器的浏览器类型是否与新选择一致
            logger.info(f"浏览器切换检查: self.selected_browser={self.selected_browser}, self.browser_monitor_active={self.browser_monitor_active}")

            # 无论监听器是否正在运行,都需要重新初始化以确保使用正确的浏览器类型
            if self.browser_monitor:
                logger.info("检测到监听器对象存在,准备重新初始化...")
                # 如果监听器正在运行,先停止
                if self.browser_monitor_active:
                    self._stop_browser_monitor()
                # 重新初始化监听器以使用新浏览器类型
                self._reinit_monitor_with_browser()
            else:
                logger.info("监听器对象不存在,创建新监听器...")
                # 直接初始化监听器
                self._init_browser_monitor()



    def on_unmount(self) -> None:
        """屏幕卸载时的回调"""
        # 停止Chrome监听器
        if self.browser_monitor and self.browser_monitor_active:
            try:
                self.browser_monitor.stop_monitoring()
                self.browser_monitor_active = False
                logger.info("页面卸载，Chrome监听器已停止")
            except Exception as e:
                logger.error(f"停止Chrome监听器失败: {e}")
        
        # 调用父类的卸载方法
        self.is_mounted_flag = False
        # 确保爬取状态被正确清理
        self.is_crawling = False
        self.current_crawling_id = None
        # 注意：这里不停止爬取工作线程，让爬取继续在后台运行
        # 爬取工作线程会通过app.call_later和app.post_message来更新UI
        # 即使页面卸载，这些消息也会被正确处理
        logger.debug("爬取管理页面卸载，爬取工作线程继续在后台运行")

