from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import DataTable, Label, Button, Static
from textual.containers import Horizontal, Container, Grid
from textual import on, events
from textual.widgets import DataTable
from typing import Any, Dict, List, ClassVar, cast, Optional
from src.locales.i18n_manager import get_global_i18n
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SearchResultsScreen(Screen[None]):
    # 使用 Textual BINDINGS（逐步替代 on_key）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "press('#back-button')", get_global_i18n().t('common.back')),
        ("n", "next_page", get_global_i18n().t('bookshelf.next_page')),
        ("p", "prev_page", get_global_i18n().t('bookshelf.prev_page')),
    ]
    
    CSS_PATH = "../styles/search_results_screen_overrides.tcss"
    
    # 分页相关属性
    _current_page: int = 1
    _results_per_page: int = 10
    _total_pages: int = 1

    """搜索结果展示屏幕"""
    
    def __init__(self, search_query: str, results: List[Dict[str, Any]], theme_manager, renderer=None) -> None:
        super().__init__()
        self.search_query = search_query
        self.results = results
        self.theme_manager = theme_manager
        self.renderer = renderer
        self.db_manager = DatabaseManager()  # 数据库管理器
        self.selected_result_index = 0
        
        # 行键映射
        self._row_key_mapping: Dict[str, int] = {}
        
        # 计算总页数
        self._total_pages = max(1, (len(results) + self._results_per_page - 1) // self._results_per_page)

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            return self.db_manager._has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许

    def compose(self) -> ComposeResult:
        with Container(id="search-results-container"):
            # 顶部标题栏
            with Horizontal(id="search-header"):
                yield Button(f"← {get_global_i18n().t('common.back')}", id="back-button", variant="primary")
                yield Label(f"🔍 {get_global_i18n().t('search_results_screen.title')}: {self.search_query} ({get_global_i18n().t('search_results_screen.total_results', count=len(self.results))})", id="search-title")
            
            # 使用Grid布局
            with Grid(id="search-results-grid"):
                # 搜索结果列表
                if not self.results:
                    yield Static(get_global_i18n().t('search_results_screen.no_results'), id="no-results")
                else:
                    # 使用DataTable显示搜索结果
                    table = DataTable(id="results-table", cursor_type="row", zebra_stripes=True)
                    table.add_column(get_global_i18n().t('search_results_screen.column_page'), key="page")
                    table.add_column(get_global_i18n().t('search_results_screen.column_preview'), key="preview")
                    yield table
                
                # 底部状态栏（分页导航）
                with Horizontal(id="pagination-bar"):
                    yield Button("◀◀", id="first-page-btn", classes="pagination-btn")
                    yield Button("◀", id="prev-page-btn", classes="pagination-btn")
                    yield Label("", id="page-info", classes="page-info")
                    yield Button("▶", id="next-page-btn", classes="pagination-btn")
                    yield Button("▶▶", id="last-page-btn", classes="pagination-btn")
                    yield Button(get_global_i18n().t("bookshelf.jump_to"), id="jump-page-btn", classes="pagination-btn")

    def on_mount(self) -> None:
        """屏幕挂载时设置焦点"""
        # 应用主题
        if hasattr(self, 'theme_manager'):
            self.theme_manager.apply_theme_to_screen(self)
        
        # 设置Grid布局的行高分配
        grid = self.query_one("#search-results-grid")
        grid.styles.grid_size_rows = 2
        grid.styles.grid_size_columns = 1
        grid.styles.grid_rows = ("90%", "10%")
        
        # 加载数据并设置焦点
        if self.results:
            self._load_results()
            table = self.query_one("#results-table", DataTable)
            if table:
                table.focus()
                # 默认选择第一行
                if table.row_count > 0:
                    table.move_cursor(row=0)
        
        # 更新分页按钮状态
        self._update_pagination_buttons()

    def on_key(self, event: events.Key) -> None:
        """处理键盘导航"""
        if event.key == "escape":
            self.app.pop_screen()
            event.stop()
        # elif event.key == "n":
        #     # N键下一页
        #     if not self._has_permission("search_results.navigation"):
        #         self.notify(get_global_i18n().t('search_results_screen.np_turn_page'), severity="error")
        #         event.stop()
        #         return
        #     if self._current_page < self._total_pages:
        #         self._current_page += 1
        #         self._refresh_table()
        #     event.prevent_default()
        # elif event.key == "p":
        #     # P键上一页
        #     if not self._has_permission("search_results.navigation"):
        #         self.notify(get_global_i18n().t('search_results_screen.np_turn_page'), severity="error")
        #         event.stop()
        #         return
        #     if self._current_page > 1:
        #         self._current_page -= 1
        #         self._refresh_table()
        #     event.prevent_default()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            # if not self._has_permission("search_results.navigation"):
            #     self.notify(get_global_i18n().t('search_results_screen.np_turn_page'), severity="error")
            #     event.stop()
            #     return
            table = self.query_one("#results-table", DataTable)
            if (table.cursor_row == len(table.rows) - 1 and 
                self._current_page < self._total_pages):
                self._go_to_next_page()
                # 将光标移动到新页面的第一行
                table.move_cursor(row=0, column=0)  # 直接移动到第一行第一列
                event.prevent_default()
                event.stop()
                return
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            # if not self._has_permission("search_results.navigation"):
            #     self.notify(get_global_i18n().t('search_results_screen.np_turn_page'), severity="error")
            #     event.stop()
            #     return
            table = self.query_one("#results-table", DataTable)
            if table.cursor_row == 0 and self._current_page > 1:
                self._go_to_prev_page()
                # 将光标移动到新页面的最后一行
                # 将光标移动到新页面的最后一行
                last_row_index = len(table.rows) - 1
                table.move_cursor(row=last_row_index, column=0)  # 直接移动到最后一行第一列
                event.prevent_default()
                event.stop()
                return

    # Actions for BINDINGS
    def action_next_page(self) -> None:
        if not self._has_permission("search_results.navigation"):
            self.notify(get_global_i18n().t('search_results_screen.np_turn_page'), severity="error")
            return
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._refresh_table()

    def action_prev_page(self) -> None:
        if not self._has_permission("search_results.navigation"):
            self.notify(get_global_i18n().t('search_results_screen.np_turn_page'), severity="error")
            return
        if self._current_page > 1:
            self._current_page -= 1
            self._refresh_table()

    def _load_results(self) -> None:
        """加载搜索结果到表格"""
        if not self.results:
            return
            
        table = self.query_one("#results-table", DataTable)
        table.clear()
        
        # 计算当前页的结果范围
        start_index = (self._current_page - 1) * self._results_per_page
        end_index = min(start_index + self._results_per_page, len(self.results))
        current_page_results = self.results[start_index:end_index]
        
        # 清空行键映射
        self._row_key_mapping = {}
        
        # 为DataTable准备数据
        table_data = []
        for idx, result in enumerate(current_page_results):
            page_info = get_global_i18n().t('reader.page_current', page=result.get('page', 1))
            preview = result.get('preview', '')[:80] + "..." if len(result.get('preview', '')) > 80 else result.get('preview', '')
            # 高亮显示匹配文本
            match_text = result.get('match_text', '')
            if match_text:
                preview = preview.replace(match_text, f"[bold yellow]{match_text}[/bold yellow]")
            
            # 使用行键映射
            row_key = f"result_{start_index + idx}"
            # 映射行键到实际结果索引
            self._row_key_mapping[row_key] = start_index + idx
            
            table_data.append({
                "page": page_info,
                "preview": preview,
                "_row_key": row_key  # 添加行键信息用于虚拟滚动组件
            })
        
        # 设置表格数据
        # 填充表格数据
        table.clear()
        for row_data in table_data:
            # 根据实际数据结构调整列（只添加2列，对应表格的2列）
            table.add_row(
                row_data.get("page", ""),
                row_data.get("preview", "")
            )
        
        # 更新分页信息
        page_info_label = self.query_one("#page-info", Label)
        page_info_label.update(f"{self._current_page}/{self._total_pages}")
    
    def _refresh_table(self) -> None:
        """刷新表格显示"""
        self._load_results()
        
        # 设置焦点并选择第一行
        table = self.query_one("#results-table", DataTable)
        table.focus()
        if table.row_count > 0:
            table.move_cursor(row=0)

    def _handle_result_selection(self, result_index: int) -> None:
        """处理结果选择跳转"""
        if not self.results or result_index < 0 or result_index >= len(self.results):
            return
            
        result = self.results[result_index]
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

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择事件（点击跳转）"""
        if not self.results:
            return
            
        # 获取当前选中行的索引
        table = self.query_one("#results-table", DataTable)
        selected_row = table.cursor_row
        
        # 计算实际结果索引（考虑分页）
        start_index = (self._current_page - 1) * self._results_per_page
        actual_index = start_index + selected_row
        
        if 0 <= actual_index < len(self.results):
            self._handle_result_selection(actual_index)

    def on_key(self, event: events.Key) -> None:
        """处理键盘导航"""
        if event.key == "escape":
            self.app.pop_screen()
            event.stop()
        elif event.key == "enter":
            # 回车键跳转当前选中行
            if not self.results:
                return
                
            table = self.query_one("#results-table", DataTable)
            selected_row = table.cursor_row
            
            # 计算实际结果索引
            start_index = (self._current_page - 1) * self._results_per_page
            actual_index = start_index + selected_row
            
            if 0 <= actual_index < len(self.results):
                self._handle_result_selection(actual_index)
                event.stop()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            table = self.query_one("#results-table", DataTable)
            if (table.cursor_row == len(table.rows) - 1 and 
                self._current_page < self._total_pages):
                self._go_to_next_page()
                # 将光标移动到新页面的第一行
                table.move_cursor(row=0, column=0)  # 直接移动到第一行第一列
                event.prevent_default()
                event.stop()
                return
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            table = self.query_one("#results-table", DataTable)
            if table.cursor_row == 0 and self._current_page > 1:
                self._go_to_prev_page()
                # 将光标移动到新页面的最后一行
                last_row_index = len(table.rows) - 1
                table.move_cursor(row=last_row_index, column=0)  # 直接移动到最后一行第一列
                event.prevent_default()
                event.stop()
                return

    @on(Button.Pressed, "#back-button")
    def on_back_button_pressed(self, event: Button.Pressed) -> None:
        """返回按钮点击处理"""
        self.app.pop_screen()
    
    # 分页导航方法
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self._current_page != 1:
            self._current_page = 1
            self._refresh_table()
            self._update_pagination_buttons()
    
    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._refresh_table()
            self._update_pagination_buttons()
    
    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._refresh_table()
            self._update_pagination_buttons()
    
    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._refresh_table()
            self._update_pagination_buttons()
    
    def _show_jump_dialog(self) -> None:
        """显示跳转页码对话框"""
        def handle_jump_result(result: Optional[str]) -> None:
            """处理跳转结果"""
            if result and result.strip():
                try:
                    page_num = int(result.strip())
                    if 1 <= page_num <= self._total_pages:
                        if page_num != self._current_page:
                            self._current_page = page_num
                            self._refresh_table()
                            self._update_pagination_buttons()
                    else:
                        self.notify(
                            get_global_i18n().t("batch_ops.page_error_info", pages=self._total_pages), 
                            severity="error"
                        )
                except ValueError:
                    self.notify(get_global_i18n().t("batch_ops.page_error"), severity="error")
        
        # 导入并显示页码输入对话框
        from src.ui.dialogs.input_dialog import InputDialog
        dialog = InputDialog(
            self.theme_manager,
            title=get_global_i18n().t("bookshelf.jump_to"),
            prompt=f"{get_global_i18n().t('batch_ops.type_num')} (1-{self._total_pages})",
            placeholder=f"{get_global_i18n().t('batch_ops.current')}: {self._current_page}/{self._total_pages}"
        )
        self.app.push_screen(dialog, handle_jump_result)
    
    def _update_pagination_buttons(self) -> None:
        """更新分页按钮状态"""
        try:
            # 更新分页信息显示
            page_label = self.query_one("#page-info", Label)
            page_label.update(f"{self._current_page}/{self._total_pages}")
            
            # 更新分页按钮状态
            first_btn = self.query_one("#first-page-btn", Button)
            prev_btn = self.query_one("#prev-page-btn", Button) 
            next_btn = self.query_one("#next-page-btn", Button)
            last_btn = self.query_one("#last-page-btn", Button)
            
            first_btn.disabled = self._current_page <= 1
            prev_btn.disabled = self._current_page <= 1
            next_btn.disabled = self._current_page >= self._total_pages
            last_btn.disabled = self._current_page >= self._total_pages
        except Exception as e:
            logger.error(f"更新分页按钮状态失败: {e}")
    
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        button_id = event.button.id
        
        # 分页导航按钮处理
        if button_id == "first-page-btn":
            self._go_to_first_page()
        elif button_id == "prev-page-btn":
            self._go_to_prev_page()
        elif button_id == "next-page-btn":
            self._go_to_next_page()
        elif button_id == "last-page-btn":
            self._go_to_last_page()
        elif button_id == "jump-page-btn":
            self._show_jump_dialog()

