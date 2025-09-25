"""
搜索结果对话框
"""

from typing import List, Optional, Any, Tuple
from webbrowser import get
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label, DataTable
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n

class SearchResultsDialog(ModalScreen[Optional[int]]):
    """搜索结果对话框，返回选择的页码"""
    
    AUTO_FOCUS = None
    CSS_PATH= "../styles/search_results_dialog.css"
    
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
    
    def compose(self) -> ComposeResult:
        """组合对话框组件"""
        with Vertical(id="search-results-dialog"):
            yield Label(f"{get_global_i18n().t('common.search}: {self.search_query}", id="search-query")
            yield Label(get_global_i18n().t("search_results_dialog.found_results", results=len(self.results)), id="search-count")
            
            # 结果表格
            table = DataTable(id="results-table")
            table.add_columns(get_global_i18n().t("search_results_dialog.page_number"), get_global_i18n().t("search_results_dialog.context"))
            for page, context in self.results:
                # 显示页码（从1开始）
                table.add_row(get_global_i18n().t("search_results_dialog.page", page=page + 1), context[:100] + "..." if len(context) > 100 else context)
            yield table
            
            with Horizontal(id="search-buttons"):
                yield Button(get_global_i18n().t("common.select"), id="select-button")
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-button")
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        self.query_one("#results-table").focus()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """行选择事件"""
        if event.cursor_row < len(self.results):
            self.selected_page = self.results[event.cursor_row][0]
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """单元格选择事件"""
        if event.coordinate.row < len(self.results):
            self.selected_page = self.results[event.coordinate.row][0]
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """行高亮事件"""
        if event.cursor_row < len(self.results):
            self.selected_page = self.results[event.cursor_row][0]
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下事件"""
        if event.button.id == "select-button":
            if self.selected_page is not None:
                self.dismiss(self.selected_page)
            else:
                self.notify(get_global_i18n().t("search_results_dialog.select_result_first"), severity="warning")
        elif event.button.id == "cancel-button":
            self.dismiss(None)
    
    def key_enter(self) -> None:
        """回车键选择当前结果"""
        if self.selected_page is not None:
            self.dismiss(self.selected_page)