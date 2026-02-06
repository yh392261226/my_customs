"""
统计屏幕
"""

import json
import os
from typing import Dict, Any, Optional, List, ClassVar
from datetime import datetime, timedelta
from webbrowser import get

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.widgets import Static, Button, Label, DataTable, ProgressBar, TabbedContent, TabPane, Header, Footer
from textual.widgets import DataTable
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

    """统计屏幕"""
    CSS_PATH = "../styles/statistics_overrides.tcss"
    # 使用 Textual BINDINGS 进行快捷键绑定（不移除 on_key，逐步过渡）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "press('#back-btn')", get_global_i18n().t('common.back')),
        ("r", "press('#refresh-btn')", get_global_i18n().t('bookshelf.refresh')),
        ("e", "press('#export-btn')", get_global_i18n().t('batch_ops.export')),
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
        self.title = get_global_i18n().t("statistics.title")
        
        # 初始化统计数据为空，将在 on_mount 中加载
        self.global_stats = {}
        self.book_stats = []
        self.authors_stats = []
    
    def compose(self) -> ComposeResult:
        """
        组合统计屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        with Container(id="stats-container"):
            # yield Horizontal(
            #     Label(get_global_i18n().t("statistics.title"), id="statistics-title"), 
            #     id="statistics-title-container"
            #     )
                
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
            
            # # 快捷键状态栏
            # with Horizontal(id="shortcuts-bar", classes="status-bar"):
            #     yield Label("R: 刷新", id="shortcut-r")
            #     yield Label("E: 导出", id="shortcut-e")
            #     yield Label("ESC: 返回", id="shortcut-esc")
        yield Footer()
    
    def _get_user_context(self) -> tuple[Optional[int], Optional[str], bool]:
        """
        获取用户上下文信息(用户ID,用户角色,是否多用户模式)

        Returns:
            tuple: (user_id, user_role, is_multi_user)
        """
        try:
            from src.utils.multi_user_manager import multi_user_manager

            # 检查是否是多用户模式
            is_multi_user = multi_user_manager.is_multi_user_enabled()

            # 获取当前用户信息
            current_user = getattr(self.app, 'current_user', None)
            if current_user is None:
                current_user = multi_user_manager.get_current_user()

            # 获取用户ID和角色
            user_id = current_user.get('id') if current_user else None
            user_role = current_user.get('role') if current_user else None

            return (user_id, user_role, is_multi_user)
        except Exception as e:
            logger.error(f"获取用户上下文失败: {e}")
            return (None, None, False)

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限（兼容单/多用户）"""
        try:
            # 检查是否是多用户模式
            from src.utils.multi_user_manager import multi_user_manager
            is_multi_user = multi_user_manager.is_multi_user_enabled()
            
            # 单用户模式：所有操作都不需要权限验证
            if not is_multi_user:
                return True
                
            # 多用户模式：获取当前用户信息
            current_user = getattr(self.app, 'current_user', None)
            if current_user is None:
                current_user = multi_user_manager.get_current_user()
            
            # 如果没有当前用户，拒绝操作
            if current_user is None:
                return False
                
            # 检查是否是超级管理员
            user_role = current_user.get('role')
            is_super_admin = user_role == "super_admin" or user_role == "superadmin"
            
            # 超级管理员：所有操作都不需要权限验证
            if is_super_admin:
                return True
                
            # 非超级管理员：需要验证权限
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            current_user_id = current_user.get('id')
            
            # 适配 has_permission 签名 (user_id, perm_key, role) 或 (perm_key)
            try:
                return db_manager.has_permission(current_user_id, permission_key, user_role)  # type: ignore[misc]
            except TypeError:
                return db_manager.has_permission(permission_key)  # type: ignore[misc]
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
                refresh_btn.tooltip = get_global_i18n().t("statistics.no_permission")
            else:
                refresh_btn.disabled = False
                refresh_btn.tooltip = None
                
            if not self._has_permission("statistics.export"):
                export_btn.disabled = True
                export_btn.tooltip = get_global_i18n().t("statistics.no_permission")
            else:
                export_btn.disabled = False
                export_btn.tooltip = None
                
            if not self._has_permission("statistics.reset"):
                reset_btn.disabled = True
                reset_btn.tooltip = get_global_i18n().t("statistics.no_permission")
            else:
                reset_btn.disabled = False
                reset_btn.tooltip = None
                
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        # 应用样式隔离
        from src.ui.styles.style_manager import apply_style_isolation
        apply_style_isolation(self)
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 检查按钮权限并禁用/启用按钮
        self._check_button_permissions()
        
        # 延迟初始化数据表，确保DOM完全构建
        self.set_timer(0.1, self._initialize_tables)

        # 启用隔行变色效果
        table_author= self.query_one("#authors-table", DataTable)
        table_author.zebra_stripes = True
        table_book = self.query_one("#book-stats-table", DataTable)
        table_book.zebra_stripes = True
        table_progress = self.query_one("#progress-table", DataTable)
        table_progress.zebra_stripes = True
        
    
    def _format_global_stats(self) -> str:
        """格式化全局统计数据"""
        total_time = self.global_stats.get("reading_time", 0)
        total_books = self.global_stats.get("books_read", 0)
        total_pages = self.global_stats.get("pages_read", 0)
        
        # 如果没有数据，显示提示信息
        if total_time == 0 and total_books == 0 and total_pages == 0:
            return get_global_i18n().t("statistics.no_data")
        
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
        """
        加载所有统计数据（直接从数据库获取，支持多用户过滤）
        """
        try:
            # 获取用户上下文
            user_id, user_role, is_multi_user = self._get_user_context()

            # 非多用户模式：直接查询所有数据，不使用user_id过滤
            if not is_multi_user:
                self.global_stats = self.statistics_manager.get_total_stats()
                self.book_stats = self.statistics_manager.get_most_read_books()
                self.authors_stats = self.statistics_manager.get_most_read_authors()

                logger.debug(f"DEBUG: 非多用户模式 - 直接查询所有数据")
            else:
                # 多用户模式：检查是否是超级管理员
                is_super_admin = user_role in ["super_admin", "superadmin"]

                # 如果是超级管理员，查询所有数据
                if is_super_admin:
                    self.global_stats = self.statistics_manager.get_total_stats()
                    self.book_stats = self.statistics_manager.get_most_read_books()
                    self.authors_stats = self.statistics_manager.get_most_read_authors()
                    logger.debug(f"DEBUG: 多用户模式 - 超级管理员 - 查询所有数据")
                elif user_id is not None:
                    # 普通用户：使用用户ID过滤
                    self.global_stats = self.statistics_manager.get_total_stats(user_id=user_id)
                    self.book_stats = self.statistics_manager.get_most_read_books(user_id=user_id)
                    self.authors_stats = self.statistics_manager.get_most_read_authors(user_id=user_id)
                    logger.debug(f"DEBUG: 多用户模式 - 用户ID过滤 - user_id={user_id}")
                else:
                    # 如果无法获取用户ID，回退到查询所有数据
                    self.global_stats = self.statistics_manager.get_total_stats()
                    self.book_stats = self.statistics_manager.get_most_read_books()
                    self.authors_stats = self.statistics_manager.get_most_read_authors()
                    logger.warning(f"DEBUG: 多用户模式 - 无法获取用户ID，回退到查询所有数据")

            # 加载各个数据表
            self._load_book_stats()
            self._load_authors_stats()
            self._load_progress_stats()
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
            # 回退到原始逻辑（无用户ID过滤）
            self.global_stats = self.statistics_manager.get_total_stats()
            self.book_stats = self.statistics_manager.get_most_read_books()
            self.authors_stats = self.statistics_manager.get_most_read_authors()

            logger.warning(f"DEBUG: Fallback - 无用户ID过滤")

            self._load_book_stats()
            self._load_authors_stats()
            self._load_progress_stats()

        # 更新静态内容
        self._update_static_content()

        # 如果没有数据，显示提示信息
        has_books_data = self.book_stats and len(self.book_stats) > 0
        has_global_data = (
            self.global_stats.get("reading_time", 0) > 0 or
            self.global_stats.get("books_read", 0) > 0 or
            self.global_stats.get("pages_read", 0) > 0
        )

        if not has_books_data and not has_global_data:
            self.notify(get_global_i18n().t('statistics.no_data'), severity="information")
    
    def _load_book_stats(self) -> None:
        """加载书籍统计数据"""
        try:
            table = self.query_one("#book-stats-table", DataTable)
            table.clear()

            # 准备虚拟滚动数据
            virtual_data = []

            if not self.book_stats:
                # 如果没有数据，显示提示信息
                virtual_data.append({
                    "title": get_global_i18n().t("statistics.no_data"),
                    "reading_time": "-",
                    "open_count": "-",
                    "progress": "-",
                    "_row_key": "no_data"
                })
            else:
                # 获取用户上下文
                user_id, user_role, is_multi_user = self._get_user_context()

                # 导入书架以获取真实的阅读进度
                from src.core.bookshelf import Bookshelf

                bookshelf = Bookshelf(app=self.app)

                # 更新书架的用户ID设置
                bookshelf.current_user_id = user_id
                bookshelf.current_user_role = user_role or 'user'

                for idx, book_stats in enumerate(self.book_stats):
                    reading_time = book_stats.get("reading_time", 0)
                    open_count = book_stats.get('open_count', 0)
                    book_path = book_stats.get("path", "")

                    # 从书架获取真实的阅读进度
                    progress_val = 0
                    if book_path:
                        reading_info = bookshelf.get_book_reading_info(book_path)
                        progress_val = reading_info.get('reading_progress', 0)

                    # 数据库中存储的是小数(0-1),需要乘以100转换为百分比显示
                    progress = progress_val * 100

                    virtual_data.append({
                        "title": book_stats.get("title", get_global_i18n().t("statistics.unknown_book")),
                        "reading_time": self._format_time(reading_time),
                        "open_count": str(open_count),
                        "progress": f"{progress:.1f}%",
                        "_row_key": f"book_{idx}"
                    })

            # 填充表格数据
            table.clear()
            for row_data in virtual_data:
                table.add_row(
                    row_data.get("title", ""),
                    row_data.get("reading_time", ""),
                    row_data.get("open_count", ""),
                    row_data.get("progress", "")
                )
        except Exception as e:
            logger.error(f"加载书籍统计数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _load_authors_stats(self) -> None:
        """加载作者统计数据"""
        try:
            table = self.query_one("#authors-table", DataTable)
            table.clear()
            
            # 准备虚拟滚动数据
            virtual_data = []
            
            # 使用已经加载的作者统计数据
            if not hasattr(self, 'authors_stats') or not self.authors_stats:
                # 如果没有数据，显示提示信息
                virtual_data.append({
                    "author": get_global_i18n().t("statistics.no_data"),
                    "reading_time": "-",
                    "book_count": "-",
                    "_row_key": "no_data"
                })
            else:
                for idx, author_stats in enumerate(self.authors_stats):
                    virtual_data.append({
                        "author": author_stats.get("author", get_global_i18n().t("statistics.unknown_author")),
                        "reading_time": self._format_time(author_stats.get("reading_time", 0)),
                        "book_count": str(author_stats.get("book_count", 0)),
                        "_row_key": f"author_{idx}"
                    })
            
            # 填充表格数据
            table.clear()
            for row_data in virtual_data:
                table.add_row(
                    row_data.get("author", ""),
                    row_data.get("reading_time", ""),
                    row_data.get("book_count", "")
                )
        except Exception as e:
            logger.error(f"加载作者统计数据失败: {e}")
    
    def _load_progress_stats(self) -> None:
        """加载阅读进度统计数据"""
        try:
            table = self.query_one("#progress-table", DataTable)
            table.clear()

            # 准备虚拟滚动数据
            virtual_data = []

            # 获取用户上下文
            user_id, user_role, is_multi_user = self._get_user_context()

            # 导入书架
            from src.core.bookshelf import Bookshelf

            bookshelf = Bookshelf(app=self.app)

            # 更新书架的用户ID设置
            bookshelf.current_user_id = user_id
            bookshelf.current_user_role = user_role or 'user'

            # 获取所有书籍
            all_books = list(bookshelf.books.values())

            if not all_books:
                virtual_data.append({
                    "title": get_global_i18n().t("statistics.no_data"),
                    "current_page": "-",
                    "total_pages": "-",
                    "progress": "-",
                    "_row_key": "no_data"
                })
            else:
                # 按最后阅读时间排序,显示前10本
                books_with_progress = []
                for book in all_books:
                    reading_info = bookshelf.get_book_reading_info(book.path)
                    progress_val = reading_info.get('reading_progress', 0)
                    last_read_date = reading_info.get('last_read_date', '')

                    if last_read_date:  # 只显示有阅读记录的书籍
                        books_with_progress.append({
                            'book': book,
                            'progress': progress_val,
                            'last_read_date': last_read_date,
                            'current_page': reading_info.get('current_page', 0),
                            'total_pages': reading_info.get('total_pages', 0)
                        })

                # 按最后阅读时间降序排序
                books_with_progress.sort(key=lambda x: x['last_read_date'] or '', reverse=True)

                # 只显示前10本
                for idx, book_data in enumerate(books_with_progress[:10]):
                    book = book_data['book']
                    progress = book_data['progress'] * 100
                    current_page_val = book_data['current_page']
                    total_pages_val = book_data['total_pages']

                    # 格式化页数显示
                    current_page = str(int(current_page_val)) if current_page_val > 0 else "-"
                    total_pages = str(int(total_pages_val)) if total_pages_val > 0 else "-"

                    virtual_data.append({
                        "title": book.title,
                        "current_page": current_page,
                        "total_pages": total_pages,
                        "progress": f"{progress:.1f}%",
                        "_row_key": f"progress_{idx}"
                    })

                # 如果没有阅读记录,显示提示
                if len(virtual_data) == 0:
                    virtual_data.append({
                        "title": get_global_i18n().t("statistics.no_reading_record"),
                        "current_page": "-",
                        "total_pages": "-",
                        "progress": "-",
                        "_row_key": "no_data"
                    })

            # 填充表格数据
            table.clear()
            for row_data in virtual_data:
                table.add_row(
                    row_data.get("title", ""),
                    row_data.get("current_page", ""),
                    row_data.get("total_pages", ""),
                    row_data.get("progress", "")
                )
        except Exception as e:
            logger.error(f"加载阅读进度统计数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
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
    
    def _has_button_permission(self, button_id: Optional[str]) -> bool:
        """检查按钮权限"""
        if not button_id:
            return False
            
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
            self.notify(get_global_i18n().t("statistics.np_action"), severity="warning")
            return
            
        if event.button.id == "refresh-btn":
            if self._has_permission("statistics.refresh"):
                self._refresh_stats()
            else:
                self.notify(get_global_i18n().t("statistics.np_refresh"), severity="warning")
        elif event.button.id == "export-btn":
            if self._has_permission("statistics.export"):
                import asyncio
                asyncio.create_task(self._export_stats())
            else:
                self.notify(get_global_i18n().t("statistics.np_export"), severity="warning")
        elif event.button.id == "reset-btn":
            if self._has_permission("statistics.reset"):
                import asyncio
                asyncio.create_task(self._reset_stats())
            else:
                self.notify(get_global_i18n().t("statistics.np_reset"), severity="warning")
        elif event.button.id == "back-btn":
            self.app.pop_screen()
    
    def _refresh_stats(self) -> None:
        """刷新统计数据"""
        self._load_all_stats()
        self.notify(get_global_i18n().t("statistics.refreshed"), severity="information")
    
    async def _export_stats(self) -> None:
        """导出统计数据到JSON文件"""
        try:
            # 检查权限并获取需要导出的用户ID范围
            export_user_id = self._get_export_reset_user_id()
            
            # 检查权限
            if export_user_id == -1:
                self.notify(get_global_i18n().t("statistics.no_permission_export"), severity="warning")
                return
            
            # 获取所有统计数据
            stats_data = {
                "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "global_stats": self.statistics_manager.get_total_stats(user_id=export_user_id),
                "book_stats": self.statistics_manager.get_most_read_books(user_id=export_user_id),
                "authors_stats": self.statistics_manager.get_most_read_authors(user_id=export_user_id),
                "reading_trend": self.statistics_manager.get_reading_trend(30, user_id=export_user_id),  # 最近30天
                "daily_stats": self.statistics_manager.get_daily_stats(user_id=export_user_id),
                "period_stats": {
                    "last_7_days": self.statistics_manager.get_period_stats(
                        (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                        datetime.now().strftime("%Y-%m-%d"),
                        user_id=export_user_id
                    ),
                    "last_30_days": self.statistics_manager.get_period_stats(
                        (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                        datetime.now().strftime("%Y-%m-%d"),
                        user_id=export_user_id
                    )
                }
            }
            
            # 生成导出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if export_user_id is None:
                filename = f"statistics_export_all_{timestamp}.json"
            else:
                filename = f"statistics_export_user_{export_user_id}_{timestamp}.json"
            
            # 构建导出路径
            export_path =  os.path.join(os.path.expanduser("~"), "Downloads", filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            # 写入JSON文件
            import json
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
            
            self.notify(f"{get_global_i18n().t('statistics.export_success')}: {export_path}", severity="information")
            
        except Exception as e:
            logger.error(f"导出统计数据失败: {e}")
            self.notify(f"{get_global_i18n().t('statistics.export_failed')}: {e}", severity="error")
    
    async def _reset_stats(self) -> None:
        """重置统计数据"""
        try:
            # 检查权限并获取需要重置的用户ID范围
            reset_user_id = self._get_export_reset_user_id()
            
            # 检查权限
            if reset_user_id == -1:
                self.notify(get_global_i18n().t("statistics.no_permission_reset"), severity="warning")
                return
            
            # 检查权限并确认操作
            if not await self._confirm_reset():
                return
            
            # 执行重置操作
            success = self.statistics_manager.reset_statistics(reset_user_id)
            
            if success:
                self.notify(get_global_i18n().t('statistics.reset_success'), severity="information")
                # 刷新统计数据
                self._refresh_stats()
            else:
                self.notify(get_global_i18n().t('statistics.reset_failed'), severity="error")
                
        except Exception as e:
            logger.error(f"重置统计数据失败: {e}")
            self.notify(f"{get_global_i18n().t('statistics.reset_failed')}: {e}", severity="error")
    
    def _get_export_reset_user_id(self) -> Optional[int]:
        """
        根据权限逻辑获取导出/重置操作的用户ID范围
        
        Returns:
            Optional[int]: 用户ID，None表示所有用户数据
        """
        try:
            # 检查是否是多用户模式
            from src.utils.multi_user_manager import multi_user_manager
            is_multi_user = multi_user_manager.is_multi_user_enabled()
            
            # 非多用户模式：直接操作所有数据
            if not is_multi_user:
                return None
            
            # 多用户模式：获取当前用户信息
            current_user = getattr(self.app, 'current_user', None)
            if current_user is None:
                current_user = multi_user_manager.get_current_user()
            
            if current_user is None:
                # 无法获取用户信息，拒绝操作
                return -1  # 特殊值表示无权限
            
            # 检查是否是超级管理员
            user_role = current_user.get('role')
            is_super_admin = user_role == "super_admin" or user_role == "superadmin"
            
            if is_super_admin:
                # 超级管理员：操作所有用户数据
                return None
            else:
                # 非超级管理员：只操作当前用户的数据
                return current_user.get('id')
                
        except Exception as e:
            logger.error(f"获取导出重置用户ID失败: {e}")
            return -1  # 出错时返回特殊值表示无权限
    
    def _get_export_path(self, filename: str) -> str:
        """
        获取导出文件路径
        
        Args:
            filename: 文件名
            
        Returns:
            str: 完整的导出文件路径
        """
        try:
            export_dir = os.path.join(os.path.expanduser("~"), "Downloads", filename)
            
            # 确保目录存在
            os.makedirs(export_dir, exist_ok=True)
            
            return os.path.join(export_dir, filename)
            
        except Exception as e:
            logger.error(f"获取导出路径失败: {e}")
            # 回退到当前目录
            return filename
    
    async def _confirm_reset(self) -> bool:
        """
        确认重置操作
        
        Returns:
            bool: 用户是否确认重置
        """
        try:
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            
            # 检查权限
            user_id = self._get_export_reset_user_id()
            
            # 构建确认消息
            if user_id is None:
                message = get_global_i18n().t("statistics.reset_all_confirm")
            else:
                message = get_global_i18n().t("statistics.reset_user_confirm")
            
            # 创建并显示确认对话框
            confirm_dialog = ConfirmDialog(
                theme_manager=self.theme_manager,
                title=get_global_i18n().t("statistics.reset_confirm_title"),
                message=message
            )
            
            # 推入对话框并等待结果 - 使用正确的异步方式
            result = await self.app.push_screen(confirm_dialog)
            
            return result or False
            
        except Exception as e:
            logger.error(f"确认重置操作失败: {e}")
            return False
    
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
                self.notify(get_global_i18n().t("statistics.np_refresh"), severity="warning")
            event.prevent_default()
        elif event.key == "e":
            # 导出统计需要权限
            if self._has_permission("statistics.export"):
                import asyncio
                asyncio.create_task(self._export_stats())
            else:
                self.notify(get_global_i18n().t("statistics.np_export"), severity="warning")
            event.prevent_default()
    
    def _format_reading_trend(self) -> str:
        """格式化阅读趋势数据"""
        try:
            # 获取用户上下文
            user_id, user_role, is_multi_user = self._get_user_context()

            # 非多用户模式或超级管理员：不使用user_id
            if not is_multi_user or user_role in ["super_admin", "superadmin"]:
                trend_data = self.statistics_manager.get_reading_trend(7)  # 最近7天
            elif user_id is not None:
                # 普通用户：使用用户ID过滤
                trend_data = self.statistics_manager.get_reading_trend(7, user_id=user_id)  # 最近7天
            else:
                # 无法获取用户ID，回退到查询所有数据
                trend_data = self.statistics_manager.get_reading_trend(7)  # 最近7天

            if not trend_data:
                return get_global_i18n().t("statistics.no_trend_data")

            trend_text = f"{get_global_i18n().t('statistics.trend_7days_data')}:\n"
            for date, minutes in trend_data:
                hours = minutes // 60
                mins = minutes % 60
                trend_text += f"{date}: {hours}{get_global_i18n().t('statistics.hours')}{mins}{get_global_i18n().t('statistics.minutes')}\n"

            return trend_text.strip()
        except Exception as e:
            logger.error(f"{get_global_i18n().t('statistics.format_trend_failed')}: {e}")
            return get_global_i18n().t("statistics.load_trend_failed")

    def _format_daily_stats(self) -> str:
        """格式化每日统计数据"""
        try:
            # 获取用户上下文
            user_id, user_role, is_multi_user = self._get_user_context()

            # 非多用户模式或超级管理员：不使用user_id
            if not is_multi_user or user_role in ["super_admin", "superadmin"]:
                daily_stats = self.statistics_manager.get_daily_stats()
            elif user_id is not None:
                # 普通用户：使用用户ID过滤
                daily_stats = self.statistics_manager.get_daily_stats(user_id=user_id)
            else:
                # 无法获取用户ID，回退到查询所有数据
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
            # 获取用户上下文
            user_id, user_role, is_multi_user = self._get_user_context()

            # 获取最近7天和30天的统计数据
            today = datetime.now()
            week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")

            # 非多用户模式或超级管理员：不使用user_id
            if not is_multi_user or user_role in ["super_admin", "superadmin"]:
                weekly_stats = self.statistics_manager.get_period_stats(week_ago, today.strftime("%Y-%m-%d"))
                monthly_stats = self.statistics_manager.get_period_stats(month_ago, today.strftime("%Y-%m-%d"))
            elif user_id is not None:
                # 普通用户：使用用户ID过滤
                weekly_stats = self.statistics_manager.get_period_stats(week_ago, today.strftime("%Y-%m-%d"), user_id=user_id)
                monthly_stats = self.statistics_manager.get_period_stats(month_ago, today.strftime("%Y-%m-%d"), user_id=user_id)
            else:
                # 无法获取用户ID，回退到查询所有数据
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
                    book_table.add_column(get_global_i18n().t("statistics.book_title"), key="title")
                    book_table.add_column(get_global_i18n().t("statistics.reading_time"), key="reading_time")
                    book_table.add_column(get_global_i18n().t("statistics.open_count"), key="open_count")
                    book_table.add_column(get_global_i18n().t("statistics.progress"), key="progress")
            except Exception as e:
                logger.warning(f"初始化书籍统计表失败: {e}")
            
            # 初始化作者统计数据表
            try:
                authors_table = self.query_one("#authors-table", DataTable)
                if not authors_table.columns:  # 避免重复添加列
                    authors_table.add_column(get_global_i18n().t("statistics.author"), key="author")
                    authors_table.add_column(get_global_i18n().t("statistics.reading_time"), key="reading_time")
                    authors_table.add_column(get_global_i18n().t("statistics.book_count"), key="book_count")
            except Exception as e:
                logger.warning(f"初始化作者统计表失败: {e}")
            
            # 初始化阅读进度数据表
            try:
                progress_table = self.query_one("#progress-table", DataTable)
                if not progress_table.columns:  # 避免重复添加列
                    progress_table.add_column(get_global_i18n().t("statistics.book_title"), key="title")
                    progress_table.add_column(get_global_i18n().t("statistics.current_page"), key="current_page")
                    progress_table.add_column(get_global_i18n().t("statistics.total_pages"), key="total_pages")
                    progress_table.add_column(get_global_i18n().t("statistics.progress"), key="progress")
            except Exception as e:
                logger.warning(f"初始化进度统计表失败: {e}")
            
            # 延迟加载统计数据，确保表格完全初始化
            self.set_timer(0.1, self._load_all_stats)
            
        except Exception as e:
            logger.error(f"{get_global_i18n().t('statistics.init_failed')}: {e}")
            # 如果初始化失败，再次尝试
            self.set_timer(0.3, self._initialize_tables)