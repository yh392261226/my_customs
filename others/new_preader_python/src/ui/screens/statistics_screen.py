"""
统计屏幕
"""


from typing import Dict, Any, Optional, List, ClassVar
from datetime import datetime, timedelta
from webbrowser import get

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.widgets import Static, Button, Label, DataTable, ProgressBar, TabbedContent, TabPane
from textual.reactive import reactive
from textual import on, events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.statistics_direct import StatisticsManagerDirect
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

from src.utils.logger import get_logger

# 导入统计页面样式
from pathlib import Path

logger = get_logger(__name__)

class StatisticsScreen(Screen[None]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        super().on_mount()
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """统计屏幕"""
    CSS_PATH = ["../styles/statistics_overrides.tcss"]
    # 使用 Textual BINDINGS 进行快捷键绑定（不移除 on_key，逐步过渡）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "press('#back-btn')", "返回"),
        ("r", "press('#refresh-btn')", "刷新"),
        ("e", "press('#export-btn')", "导出"),
    ]
    
    def __init__(self, theme_manager: ThemeManager, statistics_manager: StatisticsManagerDirect):
        """
        初始化统计屏幕
        
        Args:
            theme_manager: 主题管理器
            statistics_manager: 直接数据库统计管理器
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.statistics_manager = statistics_manager
        self.screen_title = get_global_i18n().t("statistics.title")
        
        # 初始化统计数据（直接从数据库获取）
        self.global_stats = self.statistics_manager.get_total_stats()
        self.book_stats = self.statistics_manager.get_most_read_books()
    
    def compose(self) -> ComposeResult:
        """
        组合统计屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        with Container(id="stats-container"):
            with TabbedContent():
                # 全局统计标签页
                with TabPane(get_global_i18n().t("statistics.global_stats"), id="global-stats-tab"):
                    yield Vertical(
                        Static(self._format_global_stats(), id="global-stats-content"),
                        Label(get_global_i18n().t("statistics.reading_trend"), id="trend-title", classes="section-title"),
                        Static(self._format_reading_trend(), id="trend-content"),
                        Label(get_global_i18n().t("statistics.most_read_authors"), id="authors-title", classes="section-title"),
                        DataTable(id="authors-table"),
                        id="global-tab"
                    )
                
                # 书籍统计标签页
                with TabPane(get_global_i18n().t("statistics.book_stats"), id="book-stats-tab"):
                    yield Vertical(
                        Label(get_global_i18n().t("statistics.most_read_books"), id="books-title", classes="section-title"),
                        DataTable(id="book-stats-table"),
                        Label(get_global_i18n().t("statistics.reading_progress"), id="progress-title", classes="section-title"),
                        DataTable(id="progress-table"),
                        id="books-tab"
                    )
                
                # 详细统计标签页
                with TabPane(get_global_i18n().t("statistics.detailed_stats"), id="detailed-stats-tab"):
                    yield Vertical(
                        Label(get_global_i18n().t("statistics.daily_stats"), id="daily-title", classes="section-title"),
                        Static(self._format_daily_stats(), id="daily-content"),
                        Label(get_global_i18n().t("statistics.weekly_monthly"), id="period-title", classes="section-title"),
                        Static(self._format_period_stats(), id="period-content"),
                        id="detailed-tab"
                    )
            
            # 底部控制按钮区域
            with Horizontal(id="stats-controls", classes="btn-row"):
                yield Button(get_global_i18n().t("statistics.refresh"), id="refresh-btn")
                yield Button(get_global_i18n().t("statistics.export"), id="export-btn")
                yield Button(get_global_i18n().t("statistics.reset"), id="reset-btn")
                yield Button(get_global_i18n().t("statistics.back"), id="back-btn")
            
            # 快捷键状态栏
            with Horizontal(id="shortcuts-bar", classes="status-bar"):
                yield Label("R: 刷新", id="shortcut-r")
                yield Label("E: 导出", id="shortcut-e")
                yield Label("ESC: 返回", id="shortcut-esc")
    
    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            return db_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def _check_button_permissions(self) -> None:
        """检查按钮权限并禁用/启用按钮"""
        try:
            refresh_btn = self.query_one("#refresh-btn", Button)
            export_btn = self.query_one("#export-btn", Button)
            reset_btn = self.query_one("#reset-btn", Button)
            
            # 检查权限并设置按钮状态
            if not self._has_permission("statistics.refresh"):
                refresh_btn.disabled = True
                refresh_btn.tooltip = "无权限"
            else:
                refresh_btn.disabled = False
                refresh_btn.tooltip = None
                
            if not self._has_permission("statistics.export"):
                export_btn.disabled = True
                export_btn.tooltip = "无权限"
            else:
                export_btn.disabled = False
                export_btn.tooltip = None
                
            if not self._has_permission("statistics.reset"):
                reset_btn.disabled = True
                reset_btn.tooltip = "无权限"
            else:
                reset_btn.disabled = False
                reset_btn.tooltip = None
                
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        from src.ui.styles.style_manager import apply_style_isolation
        apply_style_isolation(self)
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 检查按钮权限并禁用/启用按钮
        self._check_button_permissions()
        
        # 延迟初始化数据表，确保DOM完全构建
        self.set_timer(0.1, self._initialize_tables)
    
    def _format_global_stats(self) -> str:
        """格式化全局统计数据"""
        total_time = self.global_stats.get("total_reading_time", 0)
        total_books = self.global_stats.get("total_books", 0)
        total_pages = self.global_stats.get("total_pages", 0)
        
        return f"""
{get_global_i18n().t("statistics.total_reading_time")}: {self._format_time(total_time)}
{get_global_i18n().t("statistics.total_books")}: {total_books}
{get_global_i18n().t("statistics.total_pages")}: {total_pages}
"""
    
    def _format_time(self, seconds: int) -> str:
        """格式化时间"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} {get_global_i18n().t('statistics.hours')} {minutes} {get_global_i18n().t('statistics.minutes')}"
    
    def _load_all_stats(self) -> None:
        """加载所有统计数据（直接从数据库获取）"""
        # 从数据库获取最新数据
        self.global_stats = self.statistics_manager.get_total_stats()
        self.book_stats = self.statistics_manager.get_most_read_books()
        
        # 加载各个数据表
        self._load_book_stats()
        self._load_authors_stats()
        self._load_progress_stats()
        
        # 更新静态内容
        self._update_static_content()
        
        # 如果没有数据，显示提示信息
        if not self.book_stats and not self.global_stats.get("books_read", 0):
            self.notify(get_global_i18n().t('statistics.no_data'), severity="information")
    
    def _load_book_stats(self) -> None:
        """加载书籍统计数据"""
        try:
            table = self.query_one("#book-stats-table", DataTable)
            table.clear()
            
            if not self.book_stats:
                # 如果没有数据，显示提示信息
                table.add_row(
                    get_global_i18n().t("statistics.no_data"),
                    "-",
                    "-",
                    "-"
                )
                return
                
            for book_stats in self.book_stats:
                reading_time = book_stats.get("reading_time", 0)
                progress = book_stats.get("progress", 0)
                
                table.add_row(
                    book_stats.get("title", get_global_i18n().t("statistics.unknown_book")),
                    self._format_time(reading_time),
                    f"{book_stats.get('open_count', 0)}",
                    f"{progress * 100:.1f}%"
                )
        except Exception as e:
            logger.error(f"加载书籍统计数据失败: {e}")
    
    def _load_authors_stats(self) -> None:
        """加载作者统计数据"""
        try:
            table = self.query_one("#authors-table", DataTable)
            table.clear()
            
            authors_stats = self.statistics_manager.get_most_read_authors()
            if not authors_stats:
                # 如果没有数据，显示提示信息
                table.add_row(
                    get_global_i18n().t("statistics.no_data"),
                    "-",
                    "-"
                )
                return
                
            for author_stats in authors_stats:
                table.add_row(
                    author_stats.get("author", get_global_i18n().t("statistics.unknown_author")),
                    self._format_time(author_stats.get("reading_time", 0)),
                    str(author_stats.get("book_count", 0))
                )
        except Exception as e:
            logger.error(f"加载作者统计数据失败: {e}")
    
    def _load_progress_stats(self) -> None:
        """加载阅读进度统计数据"""
        try:
            table = self.query_one("#progress-table", DataTable)
            table.clear()
            
            # 由于直接数据库版本没有bookshelf引用，简化进度显示
            # 只显示最常阅读书籍的进度信息
            if not self.book_stats:
                table.add_row(
                    get_global_i18n().t("statistics.no_data"),
                    "-",
                    "-",
                    "-"
                )
                return
                
            for book in self.book_stats[:10]:  # 只显示前10本
                progress = book.get("progress", 0)
                table.add_row(
                    book.get("title", get_global_i18n().t("statistics.unknown_book")),
                    "-",  # 当前页数信息需要从数据库获取，暂时留空
                    "-",  # 总页数信息需要从数据库获取，暂时留空
                    f"{progress * 100:.1f}%"
                )
        except Exception as e:
            logger.error(f"加载阅读进度统计数据失败: {e}")
    
    def _update_static_content(self) -> None:
        """更新静态内容"""
        # 更新全局统计
        global_content = self.query_one("#global-stats-content", Static)
        global_content.update(self._format_global_stats())
        
        # 更新趋势内容
        trend_content = self.query_one("#trend-content", Static)
        trend_content.update(self._format_reading_trend())
        
        # 更新每日统计
        daily_content = self.query_one("#daily-content", Static)
        daily_content.update(self._format_daily_stats())
        
        # 更新周期统计
        period_content = self.query_one("#period-content", Static)
        period_content.update(self._format_period_stats())
    
    def _has_button_permission(self, button_id: str) -> bool:
        """检查按钮权限"""
        permission_map = {
            "refresh-btn": "statistics.refresh",
            "export-btn": "statistics.export",
            "reset-btn": "statistics.reset"
        }
        
        if button_id in permission_map:
            return self._has_permission(permission_map[button_id])
        
        return True  # 默认允许未知按钮
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        # 检查权限
        if not self._has_button_permission(event.button.id):
            self.notify("无权限执行此操作", severity="warning")
            return
            
        if event.button.id == "refresh-btn":
            if self._has_permission("statistics.refresh"):
                self._refresh_stats()
            else:
                self.notify("无权限刷新统计", severity="warning")
        elif event.button.id == "export-btn":
            if self._has_permission("statistics.export"):
                self._export_stats()
            else:
                self.notify("无权限导出统计", severity="warning")
        elif event.button.id == "reset-btn":
            if self._has_permission("statistics.reset"):
                self._reset_stats()
            else:
                self.notify("无权限重置统计", severity="warning")
        elif event.button.id == "back-btn":
            self.app.pop_screen()
    
    def _refresh_stats(self) -> None:
        """刷新统计数据"""
        self._load_all_stats()
        self.notify(get_global_i18n().t("statistics.refreshed"), severity="information")
    
    def _export_stats(self) -> None:
        """导出统计数据（直接数据库版本暂不支持导出）"""
        self.notify(get_global_i18n().t('statistics.export_not_supported'), severity="information")
    
    def _reset_stats(self) -> None:
        """重置统计数据（直接数据库版本不支持重置）"""
        self.notify(get_global_i18n().t('statistics.not_suppose_reset'), severity="information")
    
    def on_key(self, event) -> None:
        """
        处理键盘事件
        
        Args:
            event: 键盘事件
        """
        if event.key == "escape":
            self.app.pop_screen()
            event.stop()
        elif event.key == "r":
            # 刷新统计需要权限
            if self._has_permission("statistics.refresh"):
                self._refresh_stats()
            else:
                self.notify("无权限刷新统计", severity="warning")
            event.prevent_default()
        elif event.key == "e":
            # 导出统计需要权限
            if self._has_permission("statistics.export"):
                self._export_stats()
            else:
                self.notify("无权限导出统计", severity="warning")
            event.prevent_default()
    
    def _format_reading_trend(self) -> str:
        """格式化阅读趋势数据"""
        try:
            trend_data = self.statistics_manager.get_reading_trend(7)  # 最近7天
            if not trend_data:
                return get_global_i18n().t("statistics.no_trend_data")
            
            trend_text = f"{get_global_i18n().t("statistics.trend_7days_data")}:\n"
            for date, minutes in trend_data:
                hours = minutes // 60
                mins = minutes % 60
                trend_text += f"{date}: {hours}{get_global_i18n().t("statistics.hours")}{mins}{get_global_i18n().t("statistics.minutes")}\n"
            
            return trend_text.strip()
        except Exception as e:
            logger.error(f"{get_global_i18n().t("statistics.format_trend_failed")}: {e}")
            return get_global_i18n().t("statistics.load_trend_failed")
    
    def _format_daily_stats(self) -> str:
        """格式化每日统计数据"""
        try:
            daily_stats = self.statistics_manager.get_daily_stats()
            
            reading_time = daily_stats.get("reading_time", 0)
            books_read = daily_stats.get("books_read", 0)
            
            return f"""{get_global_i18n().t("statistics.today_stats")}:
{get_global_i18n().t("statistics.reading_time")}: {self._format_time(reading_time)}
{get_global_i18n().t("statistics.reading_books")}: {books_read} {get_global_i18n().t("bookshelf.books")}"""
        except Exception as e:
            logger.error(f"{get_global_i18n().t("statistics.format_daily_failed")}: {e}")
            return get_global_i18n().t("statistics.load_daily_failed")
    
    def _format_period_stats(self) -> str:
        """格式化周期统计数据"""
        try:
            # 获取最近7天和30天的统计数据
            today = datetime.now()
            week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            
            weekly_stats = self.statistics_manager.get_period_stats(week_ago, today.strftime("%Y-%m-%d"))
            monthly_stats = self.statistics_manager.get_period_stats(month_ago, today.strftime("%Y-%m-%d"))
            
            return f"""{get_global_i18n().t("statistics.period_stats")}:
{get_global_i18n().t("statistics.nearly_7days")}: {self._format_time(weekly_stats.get('reading_time', 0))} ({weekly_stats.get('books_read', 0)} {get_global_i18n().t("statistics.books_unit")})
{get_global_i18n().t("statistics.nearly_30days")}: {self._format_time(monthly_stats.get('reading_time', 0))} ({monthly_stats.get('books_read', 0)} {get_global_i18n().t("statistics.books_unit")})"""
        except Exception as e:
            logger.error(f"{get_global_i18n().t("statistics.format_period_data_failed")}: {e}")
            return get_global_i18n().t("statistics.load_period_data_failed")
    
    def _initialize_tables(self) -> None:
        """初始化数据表"""
        try:
            # 初始化书籍统计数据表
            try:
                book_table = self.query_one("#book-stats-table", DataTable)
                if not book_table.columns:  # 避免重复添加列
                    book_table.add_columns(
                        get_global_i18n().t("statistics.book_title"),
                        get_global_i18n().t("statistics.reading_time"),
                        get_global_i18n().t("statistics.open_count"),
                        get_global_i18n().t("statistics.progress")
                    )
            except Exception as e:
                logger.warning(f"初始化书籍统计表失败: {e}")
            
            # 初始化作者统计数据表
            try:
                authors_table = self.query_one("#authors-table", DataTable)
                if not authors_table.columns:  # 避免重复添加列
                    authors_table.add_columns(
                        get_global_i18n().t("statistics.author"),
                        get_global_i18n().t("statistics.reading_time"),
                        get_global_i18n().t("statistics.book_count")
                    )
            except Exception as e:
                logger.warning(f"初始化作者统计表失败: {e}")
            
            # 初始化阅读进度数据表
            try:
                progress_table = self.query_one("#progress-table", DataTable)
                if not progress_table.columns:  # 避免重复添加列
                    progress_table.add_columns(
                        get_global_i18n().t("statistics.book_title"),
                        get_global_i18n().t("statistics.current_page"),
                        get_global_i18n().t("statistics.total_pages"),
                        get_global_i18n().t("statistics.progress")
                    )
            except Exception as e:
                logger.warning(f"初始化进度统计表失败: {e}")
            
            # 延迟加载统计数据，确保表格完全初始化
            self.set_timer(0.1, self._load_all_stats)
            
        except Exception as e:
            logger.error(f"{get_global_i18n().t('statistics.init_failed')}: {e}")
            # 如果初始化失败，再次尝试
            self.set_timer(0.3, self._initialize_tables)