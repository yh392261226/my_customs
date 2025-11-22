"""
搜索结果对话框
"""

from typing import List, Optional, Any, Tuple
from webbrowser import get
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label, DataTable
from textual.widgets import DataTable
from textual import events, on

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.utils.logger import get_logger

logger = get_logger(__name__)

class SearchResultsDialog(ModalScreen[Optional[int]]):
    """搜索结果对话框，返回选择的页码"""
    
    AUTO_FOCUS = None
    CSS_PATH= "../styles/search_results_dialog_overrides.tcss"

    # 使用 BINDINGS：Enter 选择
    BINDINGS = [
        ("enter", "select", get_global_i18n().t('common.select')),
    ]
    
    def __init__(self, results: List[Tuple[int, str]], search_query: str):
        """
        初始化搜索结果对话框
        
        Args:
            results: 搜索结果列表，每个元素为(页码, 上下文)
            search_query: 搜索关键词
        """
        super().__init__()
        self.results = results
        self.search_query = search_query
        self.i18n = get_global_i18n()
        self.selected_page: Optional[int] = None
        
        # 分页相关属性
        self._current_page = 1
        self._results_per_page = 10
        self._total_pages = 1
        self._all_results: List[Tuple[int, str]] = results
    
    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        
        # 初始化数据表
        self._init_table()
        
        # 设置焦点到结果表格
        self.query_one("#results-table").focus()
    
    def _init_table(self) -> None:
        """初始化表格"""
        table = self.query_one("#results-table", DataTable)
        table.clear(columns=True)
        
        # 添加列
        table.add_column(get_global_i18n().t("search_results_dialog.page_number"), key="page_number")
        table.add_column(get_global_i18n().t("search_results_dialog.context"), key="context")
        
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        # 加载数据
        self._load_results()
    
    def compose(self) -> ComposeResult:
        """组合对话框组件"""
        with Grid(id="search-results-dialog"):
            # 顶部区域：搜索信息
            Vertical(
                # Label(f"{get_global_i18n().t('common.search')}: {self.search_query}", id="search-query", classes="section-title"),
                Label(get_global_i18n().t("search_results_dialog.found_results", results=len(self.results)), id="search-count"),
                id="search-header",
                classes="search-header-vertical"
            ),
            
            # 中间区域：结果表格
            Vertical(
                DataTable(id="results-table"),
                id="results-preview"
            ),
            
            # 底部区域1：分页导航
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
            
            # 底部区域2：操作按钮
            Horizontal(
                Button(get_global_i18n().t("common.select"), id="select-button"),
                Button(get_global_i18n().t("common.cancel"), id="cancel-button"),
                id="search-buttons",
                classes="btn-row"
            ),
            
            
    
    @on(DataTable.RowSelected, "#results-table")
    def on_data_table_row_selected(self, event) -> None:
        """行选择事件"""
        table = self.query_one("#results-table", DataTable)
        if hasattr(table, '_current_data') and len(table._current_data) > 0:
            # 获取当前选中行的数据
            row_keys = list(table._current_data.keys())
            if event.cursor_row is not None and event.cursor_row < len(row_keys):
                row_key = row_keys[event.cursor_row]
                if row_key in table._current_data:
                    # 从全局索引计算实际页码
                    global_index = table._current_data[row_key].get('_global_index', 0)
                    if global_index > 0 and global_index <= len(self._all_results):
                        self.selected_page = self._all_results[global_index - 1][0]
    
    @on(DataTable.CellSelected, "#results-table")
    def on_data_table_cell_selected(self, event) -> None:
        """单元格选择事件"""
        table = self.query_one("#results-table", DataTable)
        if hasattr(table, '_current_data') and len(table._current_data) > 0:
            # 获取点击行的数据
            row_keys = list(table._current_data.keys())
            if event.coordinate.row is not None and event.coordinate.row < len(row_keys):
                row_key = row_keys[event.coordinate.row]
                if row_key in table._current_data:
                    # 从全局索引计算实际页码
                    global_index = table._current_data[row_key].get('_global_index', 0)
                    if global_index > 0 and global_index <= len(self._all_results):
                        self.selected_page = self._all_results[global_index - 1][0]
    
    @on(DataTable.RowHighlighted, "#results-table")
    def on_data_table_row_highlighted(self, event) -> None:
        """行高亮事件"""
        table = self.query_one("#results-table", DataTable)
        if hasattr(table, '_current_data') and len(table._current_data) > 0:
            # 获取高亮行的数据
            row_keys = list(table._current_data.keys())
            if event.cursor_row is not None and event.cursor_row < len(row_keys):
                row_key = row_keys[event.cursor_row]
                if row_key in table._current_data:
                    # 从全局索引计算实际页码
                    global_index = table._current_data[row_key].get('_global_index', 0)
                    if global_index > 0 and global_index <= len(self._all_results):
                        self.selected_page = self._all_results[global_index - 1][0]
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下事件"""
        if event.button.id == "select-button":
            if self.selected_page is not None:
                self.dismiss(self.selected_page)
            else:
                self.notify(get_global_i18n().t("search_results_dialog.select_result_first"), severity="warning")
        elif event.button.id == "cancel-button":
            self.dismiss(None)
        # 分页按钮
        elif event.button.id == "first-page-btn":
            self._go_to_first_page()
        elif event.button.id == "prev-page-btn":
            self._go_to_prev_page()
        elif event.button.id == "next-page-btn":
            self._go_to_next_page()
        elif event.button.id == "last-page-btn":
            self._go_to_last_page()
        elif event.button.id == "jump-page-btn":
            self._show_jump_dialog()
    
    def key_enter(self) -> None:
        """回车键选择当前结果"""
        if self.selected_page is not None:
            self.dismiss(self.selected_page)

    # Actions for BINDINGS
    def action_select(self) -> None:
        if self.selected_page is not None:
            self.dismiss(self.selected_page)
    
    def _load_results(self) -> None:
        """加载搜索结果"""
        # 计算分页
        self._total_pages = max(1, (len(self._all_results) + self._results_per_page - 1) // self._results_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 获取当前页的数据
        start_index = (self._current_page - 1) * self._results_per_page
        end_index = min(start_index + self._results_per_page, len(self._all_results))
        current_page_results = self._all_results[start_index:end_index]
        
        # 准备虚拟滚动数据
        table = self.query_one("#results-table", DataTable)
        virtual_data = []
        
        for index, (page, context) in enumerate(current_page_results):
            # 显示页码（从1开始）
            page_display = get_global_i18n().t("search_results_dialog.page", page=page + 1)
            context_display = context[:100] + "..." if len(context) > 100 else context
            
            row_data = {
                "page_number": page_display,
                "context": context_display,
                "_row_key": f"result_{index}",
                "_global_index": start_index + index + 1
            }
            virtual_data.append(row_data)
        
        # 填充表格数据
        table.clear()
        for row_data in virtual_data:
            table.add_row(
                row_data["page_number"],
                row_data["context"]
            )
        
        # 更新分页信息
        self._update_pagination_info()
    
    def _update_pagination_info(self) -> None:
        """更新分页信息"""
        try:
            page_label = self.query_one("#page-info", Label)
            page_label.update(f"{self._current_page}/{self._total_pages}")
            
            # 更新分页按钮状态
            first_btn = self.query_one("#first-page-btn", Button)
            prev_btn = self.query_one("#prev-page-btn", Button) 
            next_btn = self.query_one("#next-page-btn", Button)
            last_btn = self.query_one("#last-page-btn", Button)
            
            # 设置按钮的禁用状态
            first_btn.disabled = self._current_page <= 1
            prev_btn.disabled = self._current_page <= 1
            next_btn.disabled = self._current_page >= self._total_pages
            last_btn.disabled = self._current_page >= self._total_pages
        except Exception as e:
            logger.error(f"更新分页信息失败: {e}")
    
    # 分页导航方法
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self._current_page != 1:
            self._current_page = 1
            self._load_results()
    
    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._load_results()
    
    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_results()
    
    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._load_results()
    
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
                            self._load_results()
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
            self.i18n,  # 使用 i18n 对象作为 theme_manager
            title=get_global_i18n().t("bookshelf.jump_to"),
            prompt=f"{get_global_i18n().t('batch_ops.type_num')} (1-{self._total_pages})",
            placeholder=f"{get_global_i18n().t('batch_ops.current')}: {self._current_page}/{self._total_pages}"
        )
        self.app.push_screen(dialog, handle_jump_result)