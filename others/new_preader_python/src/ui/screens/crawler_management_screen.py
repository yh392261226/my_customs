"""
爬取管理屏幕
"""

import os
from typing import Dict, Any, Optional, List, ClassVar, Set
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, Input, Link, Header, Footer, LoadingIndicator
from textual.widgets import DataTable
from textual.app import ComposeResult
from textual import events, on

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger
from src.ui.dialogs.note_dialog import NoteDialog
from src.ui.dialogs.select_books_dialog import SelectBooksDialog

logger = get_logger(__name__)

class CrawlerManagementScreen(Screen[None]):
    """爬取管理屏幕"""
    
    CSS_PATH = ["../styles/utilities.tcss", "../styles/crawler_management_overrides.tcss"]
    TITLE: ClassVar[Optional[str]] = None
    # 统一快捷键绑定（含 ESC 返回）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("o", "open_browser", get_global_i18n().t('crawler.shortcut_o')),
        ("r", "view_history", get_global_i18n().t('crawler.shortcut_r')),
        ("b", "note", get_global_i18n().t('crawler.shortcut_b')),
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
        self._update_status(f"已选中 {selected_count} 项", "information")
        
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
            self._update_status(f"已选中 {selected_count} 项", "information")
                
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
        
        # 注册回调函数
        self.crawler_manager.register_status_callback(self._on_crawl_status_change)
        self.crawler_manager.register_notification_callback(self._on_crawl_success_notify)

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
                Label(f"{get_global_i18n().t('crawler.book_id_example')}: {self.novel_site.get('book_id_example', '')}", id="book-id-example-label"),

                # 顶部操作按钮（固定）
                Horizontal(
                    Button(get_global_i18n().t('crawler.open_browser'), id="open-browser-btn"),
                    Button(get_global_i18n().t('crawler.view_history'), id="view-history-btn"),
                    Button(get_global_i18n().t('crawler.note'), id="note-btn"),
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
                            id="novel-id-container", classes="form-row"
                        ),
                        id="novel-id-section"
                    ),

                    # 爬取历史区域
                    Vertical(
                        Label(get_global_i18n().t('crawler.crawl_history'), id="crawl-history-title"),
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
        table.add_column(get_global_i18n().t('crawler.crawl_time'), key="crawl_time")
        table.add_column(get_global_i18n().t('crawler.status'), key="status")
        table.add_column(get_global_i18n().t('crawler.view_file'), key="view_file")
        table.add_column(get_global_i18n().t('crawler.read_book'), key="read_book")
        table.add_column(get_global_i18n().t('crawler.delete_file'), key="delete_file")
        table.add_column(get_global_i18n().t('crawler.delete_record'), key="delete_record")
        table.add_column(get_global_i18n().t('crawler.view_reason'), key="view_reason")
        table.add_column(get_global_i18n().t('crawler.retry'), key="retry")
        
        table.zebra_stripes = True
        
        # 初始化加载动画
        self._initialize_loading_animation()
        
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
                self.app.call_later(self._update_status, f"小说已存在: {novel_title}", "information")
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
    
    def _load_crawl_history(self) -> None:
        """加载爬取历史记录"""
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
                    
                    self.crawler_history.append({
                        "id": item['id'],
                        "novel_id": item['novel_id'],
                        "novel_title": item['novel_title'],
                        "crawl_time": crawl_time,
                        "status": status_text,
                        "file_path": item['file_path'] or "",
                        "error_message": item.get('error_message', '')
                    })
            else:
                self.crawler_history = []
        except Exception as e:
            logger.error(f"加载爬取历史记录失败: {e}")
            self.crawler_history = []
        
        # 应用搜索过滤
        self.crawler_history = self._filter_history(self.crawler_history)
        self._update_history_table()
    
    def _filter_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据搜索关键词过滤历史记录"""
        if not self._search_keyword:
            return history
        
        keyword = self._search_keyword.lower()
        filtered_history = []
        
        for item in history:
            # 搜索小说标题、小说ID、状态
            if (keyword in item.get('novel_title', '').lower() or 
                keyword in item.get('novel_id', '').lower() or 
                keyword in item.get('status', '').lower()):
                filtered_history.append(item)
        
        return filtered_history
    
    def _update_history_table(self) -> None:
        """更新历史记录表格"""
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
                
                row_data = {
                    "selected": is_selected,
                    "sequence": str(i + 1),
                    "novel_id": item["novel_id"],
                    "novel_title": item["novel_title"],
                    "crawl_time": item["crawl_time"],
                    "status": item["status"],
                    "view_file": get_global_i18n().t('crawler.view_file') if item["status"] == get_global_i18n().t('crawler.status_success') else "",
                    "read_book": get_global_i18n().t('crawler.read_book') if item["status"] == get_global_i18n().t('crawler.status_success') else "",
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
            
            # 确保表格获得焦点
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
            page_info = f"第 {self.current_page} 页，共 {total_pages} 页，总计 {len(self.crawler_history)} 条记录"
            
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
    
    def _perform_search(self) -> None:
        """执行搜索"""
        try:
            search_input = self.query_one("#search-input-field", Input)
            self._search_keyword = search_input.value.strip()
            
            # 重新加载历史记录并应用搜索过滤
            self._load_crawl_history()
            
            if self._search_keyword:
                self._update_status(f"搜索完成: 找到 {len(self.crawler_history)} 条记录")
            else:
                self._update_status("已显示所有记录")
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            self._update_status("搜索失败", "error")
    
    def _clear_search(self) -> None:
        """清除搜索"""
        try:
            search_input = self.query_one("#search-input-field", Input)
            search_input.value = ""
            self._search_keyword = ""
            
            # 重新加载历史记录
            self._load_crawl_history()
            self._update_status("搜索已清除")
        except Exception as e:
            logger.error(f"清除搜索失败: {e}")
            self._update_status("清除搜索失败", "error")
    
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
        self._update_status(f"已选择 {selected_count} 项")
    
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
            self._update_status("全选失败", "error")
    
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
            self._update_status("全选失败", "error")
    
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
            self._update_status("反选失败", "error")
    
    def _deselect_all_rows(self) -> None:
        """取消全选"""
        try:
            self.selected_history.clear()
            
            # 更新表格显示
            self._update_history_table()
            self._update_selection_status()
            
        except Exception as e:
            logger.error(f"取消全选失败: {e}")
            self._update_status("取消全选失败", "error")
    
    def _move_selected_up(self) -> None:
        """上移光标所在行"""
        try:
            # 获取当前光标所在行
            table = self.query_one("#crawl-history-table", DataTable)
            cursor_row = table.cursor_row
            
            if cursor_row is None or cursor_row < 0:
                self._update_status("请先选择要移动的行")
                return
            
            # 计算当前页的起始索引
            start_index = (self.current_page - 1) * self.items_per_page
            
            # 计算实际索引
            actual_index = start_index + cursor_row
            
            # 检查索引是否有效
            if actual_index >= len(self.crawler_history):
                self._update_status("行索引无效")
                return
            
            # 检查是否可以上移
            if actual_index <= 0:
                self._update_status("已到达顶部，无法上移")
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
            
            # 确保表格获得焦点
            table.focus()
            
            self._update_status("上移成功")
            
        except Exception as e:
            logger.error(f"上移失败: {e}")
            self._update_status("上移失败", "error")
    
    def _move_selected_down(self) -> None:
        """下移光标所在行"""
        try:
            # 获取当前光标所在行
            table = self.query_one("#crawl-history-table", DataTable)
            cursor_row = table.cursor_row
            
            if cursor_row is None or cursor_row < 0:
                self._update_status("请先选择要移动的行")
                return
            
            # 计算当前页的起始索引
            start_index = (self.current_page - 1) * self.items_per_page
            
            # 计算实际索引
            actual_index = start_index + cursor_row
            
            # 检查索引是否有效
            if actual_index >= len(self.crawler_history):
                self._update_status("行索引无效")
                return
            
            # 检查是否可以下移
            if actual_index >= len(self.crawler_history) - 1:
                self._update_status("已到达底部，无法下移")
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
            
            # 确保表格获得焦点
            table.focus()
            
            self._update_status("下移成功")
            
        except Exception as e:
            logger.error(f"下移失败: {e}")
            self._update_status("下移失败", "error")
    
    def _merge_selected(self) -> None:
        """合并选中项"""
        try:
            if not self.selected_history:
                self._update_status("请先选择要合并的项")
                return
            
            if len(self.selected_history) < 2:
                self._update_status("请至少选择2项进行合并")
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
                    self._update_status("只能合并成功的爬取记录")
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
                            self._update_status(f"合并成功: {new_title}")
                            # 清除已合并的选中项
                            for item in selected_items:
                                item_id = item.get("id")
                                if item_id and str(item_id) in self.selected_history:
                                    self.selected_history.remove(str(item_id))
                            # 刷新历史记录
                            self._load_crawl_history()
                        else:
                            self._update_status("合并操作失败", "error")
                    except Exception as e:
                        logger.error(f"合并操作异常: {e}")
                        self._update_status(f"合并异常: {e}", "error")
                else:
                    message = result.get('message', '未知错误')
                    if message != get_global_i18n().t('batch_ops.cancel_merge'):  # 不显示取消合并的错误
                        self._update_status(f"合并失败: {message}", "error")
            
            self.app.push_screen(
                CrawlerMergeDialog(
                    self.theme_manager,
                    selected_items
                ),
                handle_merge_result
            )
            
        except Exception as e:
            logger.error(f"合并失败: {e}")
            self._update_status("合并失败", "error")
    
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
                author = self.novel_site.get('name', '未知来源')
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
                        os.remove(file_path)
                        logger.info(f"删除源文件: {file_path}")
                    
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
            elif column in ["view_file", "read_book", "delete_file", "delete_record", "view_reason", "retry"]:
                self._handle_button_click(column, row_key)
                
            # 处理空格键选择：当点击任何非按钮列时，触发选择切换
            elif column not in ["selected", "view_file", "read_book", "delete_file", "delete_record", "view_reason", "retry"]:
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
                        self._update_status(f"页码必须在 1 到 {total_pages} 之间", "error")
                except ValueError:
                    self._update_status("请输入有效的页码", "error")
        
        from src.ui.dialogs.input_dialog import InputDialog
        self.app.push_screen(
            InputDialog(
                self.theme_manager,
                title="跳转页码",
                prompt="请输入要跳转的页码：",
                placeholder="页码"
            )
        )
    
    # ==================== 基础功能方法 ====================
    
    def _open_browser(self) -> None:
        """在浏览器中打开网站"""
        try:
            import platform
            system = platform.system()
            if system == "Darwin":  # macOS
                os.system(f'open -a "Google Chrome" "{self.novel_site['url']}"')
            else:
                import webbrowser
                webbrowser.open(self.novel_site['url'])
            self._update_status(get_global_i18n().t('crawler.browser_opened'))
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
                        novel_id_input = self.query_one("#novel-id-input", Input)
                        novel_id_input.value = result
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
            
            # 创建解析器实例，传递数据库中的网站名称作为作者信息
            parser = create_parser(parser_name, proxy_config, self.novel_site.get('name'))
            
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
            novel_id_input = self.query_one("#novel-id-input", Input)
            current_value = novel_id_input.value.strip()
            
            # 分割并过滤掉指定的ID
            ids = [id.strip() for id in current_value.split(',') if id.strip()]
            filtered_ids = [id for id in ids if id != novel_id]
            
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
        
        try:
            # 使用异步方式执行网络请求
            await asyncio.sleep(0.5)  # 添加小延迟避免同时请求过多
            
            # 解析小说详情
            novel_content = parser.parse_novel_detail(novel_id)
            
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
            logger.error(f"解析小说详情失败: {e}")
            return {
                'success': False,
                'error_message': str(e)
            }
    
    def on_unmount(self) -> None:
        """屏幕卸载时的回调"""
        self.is_mounted_flag = False
        # 确保爬取状态被正确清理
        self.is_crawling = False
        self.current_crawling_id = None
        # 注意：这里不停止爬取工作线程，让爬取继续在后台运行
        # 爬取工作线程会通过app.call_later和app.post_message来更新UI
        # 即使页面卸载，这些消息也会被正确处理
        logger.debug("爬取管理页面卸载，爬取工作线程继续在后台运行")
    
    def _view_file(self, history_item: Dict[str, Any]) -> None:
        """查看文件"""
        try:
            file_path = history_item.get('file_path')
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
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
                        os.remove(file_path)
                        
                        # 同时删除书架中的对应书籍
                        try:
                            # 直接使用文件路径删除书架中的书籍
                            if self.db_manager.delete_book(file_path):
                                # 发送全局刷新书架消息，确保书架屏幕能够接收
                                try:
                                    from src.ui.messages import RefreshBookshelfMessage
                                    self.app.post_message(RefreshBookshelfMessage())
                                    logger.info("已发送书架刷新消息，书籍已从书架删除")
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，书架中的书籍已删除")
                                except Exception as msg_error:
                                    logger.debug(f"发送刷新书架消息失败: {msg_error}")
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，书架书籍删除但刷新失败")
                            else:
                                # 如果删除失败，检查书籍是否存在于书架中
                                books = self.db_manager.get_all_books()
                                book_exists = any(book.path == file_path for book in books)
                                if book_exists:
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，但删除书架书籍失败")
                                else:
                                    self._update_status(get_global_i18n().t('crawler.file_deleted'))
                        except Exception as shelf_error:
                            logger.error(f"删除书架书籍失败: {shelf_error}")
                            self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，但删除书架书籍时出错")
                        
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
                    f"{get_global_i18n().t('crawler.confirm_delete')}（删除文件及书架书籍）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')} 注意：此操作将同时删除书架中的对应书籍。"
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
                        os.remove(file_path)
                        
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
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
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
            
            # 创建解析器实例，传递数据库中的网站名称作为作者信息
            parser_instance = create_parser(parser_name, proxy_config, self.novel_site.get('name'))
            
            # 使用异步方式执行网络请求
            await asyncio.sleep(0.5)  # 添加小延迟避免同时请求过多
            
            # 解析小说详情
            novel_content = await self._async_parse_novel_detail(parser_instance, novel_id)
            novel_title = novel_content['title']
            
            # 获取存储文件夹
            storage_folder = self.novel_site.get('storage_folder', 'novels')
            # 展开路径中的 ~ 符号
            storage_folder = os.path.expanduser(storage_folder)
            
            # 保存小说到文件
            file_path = parser_instance.save_to_file(novel_content, storage_folder)
            
            # 更新数据库记录（将失败记录更新为成功）
            site_id = self.novel_site.get('id')
            if site_id:
                # 更新爬取历史记录
                self.db_manager.update_crawl_history_status(
                    site_id=site_id,
                    novel_id=novel_id,
                    status='success',
                    file_path=file_path,
                    novel_title=novel_title
                )
            
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
                        # 强制使用数据库中的书籍网站名称作为作者
                        author = self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source'))
                        # 获取网站标签
                        site_tags = self.novel_site.get('tags', '')
                        book = bs.add_book(file_path, author=author, tags=site_tags)
                    if not book:
                        from src.core.book import Book
                        # 强制使用数据库中的书籍网站名称作为作者
                        author = self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source'))
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
            
            # 过滤掉已存在的ID并更新输入框
            site_id = self.novel_site.get('id')
            if site_id:
                valid_novel_ids = []
                for novel_id in novel_ids:
                    if not self.db_manager.check_novel_exists(site_id, novel_id):
                        valid_novel_ids.append(novel_id)
                
                if not valid_novel_ids:
                    # 所有ID都已存在，停止爬取
                    self._update_status(get_global_i18n().t('crawler.all_novels_exist'))
                    novel_id_input.value = ""  # 清空输入框
                    return
                
                # 更新输入框内容，只保留未下载的ID
                novel_id_input.value = ', '.join(valid_novel_ids)
                novel_ids = valid_novel_ids
            
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
        elif button_id == "delete-file-btn":
            self._batch_delete_files()
        elif button_id == "delete-record-btn":
            self._batch_delete_records()
        elif button_id == "back-btn":
            self.app.pop_screen()
        elif button_id == "search-btn":
            self._perform_search()
        elif button_id == "clear-search-btn":
            self._clear_search()
        elif button_id == "start-crawl-btn":
            self._start_crawl()
        elif button_id == "stop-crawl-btn":
            self._stop_crawl()
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
                                    os.remove(file_path)
                                    
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

