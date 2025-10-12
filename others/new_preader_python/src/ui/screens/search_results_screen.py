from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Label, Button, Static
from textual.containers import VerticalScroll, Horizontal, Container
from textual import on, events
from typing import Optional, Any, Dict, List, ClassVar, cast
from src.core.pagination.terminal_paginator import TerminalPaginator
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SearchResultsScreen(Screen[None]):
    # 使用 Textual BINDINGS（逐步替代 on_key）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "press('#back-button')", "返回"),
        ("n", "next_page", "下一页"),
        ("p", "prev_page", "上一页"),
    ]

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        super().on_mount()
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """搜索结果展示屏幕"""
    
    def __init__(self, search_query: str, results: List[Dict[str, Any]], theme_manager, renderer=None) -> None:
        super().__init__()
        self.search_query = search_query
        self.results = results
        self.theme_manager = theme_manager
        self.renderer = renderer
        self.db_manager = DatabaseManager()  # 数据库管理器
        self.selected_result_index = 0
        
        # 分页相关属性
        self._current_page = 1
        self._results_per_page = 20
        self._total_pages = max(1, (len(results) + self._results_per_page - 1) // self._results_per_page)

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            return self.db_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许

    def compose(self) -> ComposeResult:
        with Container(id="search-results-container"):
            # 顶部标题栏
            with Horizontal(id="search-header"):
                yield Button(f"← {get_global_i18n().t('common.back')}", id="back-button", variant="primary")
                yield Label(f"🔍 {get_global_i18n().t('search_results_screen.title')}: {self.search_query} ({get_global_i18n().t('search_results_screen.total_results', count=len(self.results))})", id="search-title")
            
            # 使用DataTable显示搜索结果列表
            if not self.results:
                yield Static(get_global_i18n().t('search_results_screen.no_results'), id="no-results")
            else:
                # 分页信息显示
                yield Label(f"{get_global_i18n().t('search_results_screen.page_info', page=self._current_page, total_pages=self._total_pages, total_results=len(self.results))}", id="page-info")
                
                table = DataTable(id="results-table", cursor_type="row", zebra_stripes=True)
                table.add_columns(
                    get_global_i18n().t('search_results_screen.column_page'),
                    get_global_i18n().t('search_results_screen.column_preview')
                )
                
                # 计算当前页的结果范围
                start_index = (self._current_page - 1) * self._results_per_page
                end_index = min(start_index + self._results_per_page, len(self.results))
                current_page_results = self.results[start_index:end_index]
                
                for result in current_page_results:
                    page_info = get_global_i18n().t('reader.page_current', page=result.get('page', 1))
                    preview = result.get('preview', '')[:80] + "..." if len(result.get('preview', '')) > 80 else result.get('preview', '')
                    # 高亮显示匹配文本
                    match_text = result.get('match_text', '')
                    if match_text:
                        preview = preview.replace(match_text, f"[bold yellow]{match_text}[/bold yellow]")
                    
                    table.add_row(page_info, preview)
                
                yield table

    def on_mount(self) -> None:
        """屏幕挂载时设置焦点"""
        if self.results:
            table = self.query_one("#results-table", DataTable)
            if table:
                table.focus()
                # 默认选择第一行
                if table.row_count > 0:
                    table.move_cursor(row=0)

    def on_key(self, event: events.Key) -> None:
        """处理键盘导航"""
        if event.key == "escape":
            if not self._has_permission("search_results.escape"):
                self.notify("无权限退出搜索结果页面", severity="error")
                event.stop()
                return
            self.app.pop_screen()
            event.stop()
        elif event.key == "n":
            # N键下一页
            if not self._has_permission("search_results.navigation"):
                self.notify("无权限翻页", severity="error")
                event.stop()
                return
            if self._current_page < self._total_pages:
                self._current_page += 1
                self._refresh_table()
            event.prevent_default()
        elif event.key == "p":
            # P键上一页
            if not self._has_permission("search_results.navigation"):
                self.notify("无权限翻页", severity="error")
                event.stop()
                return
            if self._current_page > 1:
                self._current_page -= 1
                self._refresh_table()
            event.prevent_default()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            if not self._has_permission("search_results.navigation"):
                self.notify("无权限翻页", severity="error")
                event.stop()
                return
            table = self.query_one("#results-table", DataTable)
            if (table.cursor_row == len(table.rows) - 1 and 
                self._current_page < self._total_pages):
                self._current_page += 1
                self._refresh_table()
                # 将光标移动到新页面的第一行
                table = self.query_one("#results-table", DataTable)
                table.action_cursor_down()  # 先向下移动一次
                table.action_cursor_up()     # 再向上移动一次，确保在第一行
                event.prevent_default()
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            if not self._has_permission("search_results.navigation"):
                self.notify("无权限翻页", severity="error")
                event.stop()
                return
            table = self.query_one("#results-table", DataTable)
            if table.cursor_row == 0 and self._current_page > 1:
                self._current_page -= 1
                self._refresh_table()
                # 将光标移动到新页面的最后一行
                table = self.query_one("#results-table", DataTable)
                for _ in range(len(table.rows) - 1):
                    table.action_cursor_down()  # 移动到最底部
                event.prevent_default()

    # Actions for BINDINGS
    def action_next_page(self) -> None:
        if not self._has_permission("search_results.navigation"):
            self.notify("无权限翻页", severity="error")
            return
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._refresh_table()

    def action_prev_page(self) -> None:
        if not self._has_permission("search_results.navigation"):
            self.notify("无权限翻页", severity="error")
            return
        if self._current_page > 1:
            self._current_page -= 1
            self._refresh_table()

    def _refresh_table(self) -> None:
        """刷新表格显示"""
        # 更新分页信息
        page_info = self.query_one("#page-info", Label)
        page_info.update(f"{get_global_i18n().t('search_results_screen.page_info', page=self._current_page, total_pages=self._total_pages, total_results=len(self.results))}")
        
        # 重新填充表格
        table = self.query_one("#results-table", DataTable)
        table.clear()
        
        # 计算当前页的结果范围
        start_index = (self._current_page - 1) * self._results_per_page
        end_index = min(start_index + self._results_per_page, len(self.results))
        current_page_results = self.results[start_index:end_index]
        
        for result in current_page_results:
            page_info = get_global_i18n().t('reader.page_current', page=result.get('page', 1))
            preview = result.get('preview', '')[:80] + "..." if len(result.get('preview', '')) > 80 else result.get('preview', '')
            # 高亮显示匹配文本
            match_text = result.get('match_text', '')
            if match_text:
                preview = preview.replace(match_text, f"[bold yellow]{match_text}[/bold yellow]")
            
            table.add_row(page_info, preview)
        
        # 设置焦点并选择第一行
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0)

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择事件"""
        if not self.results:
            return
            
        # 计算实际结果索引（考虑分页）
        row_index = event.cursor_row
        actual_index = (self._current_page - 1) * self._results_per_page + row_index
        
        if 0 <= actual_index < len(self.results):
            result = self.results[actual_index]
            page = result.get('page', 1)
            
            # 如果提供了renderer，直接跳转页面
            if hasattr(self, 'renderer') and self.renderer:
                if self.renderer.goto_page(page):
                    self.app.pop_screen()
                    # 通知阅读器页面已跳转
                    reader_screen = self.app.screen_stack[-1] if self.app.screen_stack else None
                    if reader_screen is not None:
                        screen_any = cast(Any, reader_screen)
                        if hasattr(screen_any, "_on_page_change"):
                            screen_any._on_page_change(page)
            else:
                # 返回到阅读器并传递跳转信息
                self.dismiss(page)

    @on(Button.Pressed, "#back-button")
    def on_back_button_pressed(self, event: Button.Pressed) -> None:
        """返回按钮点击处理"""
        self.app.pop_screen()

