"""
搜索对话框组件
"""

from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, DataTable, Select
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.search import SearchResult
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class SearchDialog(ModalScreen[Optional[SearchResult]]):


    """搜索对话框"""
    
    CSS_PATH = "../styles/search_dialog_overrides.tcss"
    BINDINGS = [
        ("enter", "press('#select-btn')", get_global_i18n().t('common.select')),
        ("escape", "press('#cancel-btn')", get_global_i18n().t('common.cancel')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, 
                 book_id: Optional[str] = None):
        """
        初始化搜索对话框
        
        Args:
            theme_manager: 主题管理器
            book_id: 可选，限制搜索的书籍ID
        """
        super().__init__()
        self.i18n = get_global_i18n()
        self.theme_manager = theme_manager
        self.book_id = book_id
        self.results: List[SearchResult] = []
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="search-dialog"):
            yield Label(get_global_i18n().t("search.title"), id="search-title", classes="section-title")
            with Vertical(id="search-filters", classes="form-row"):
                yield Input(placeholder=get_global_i18n().t("search.placeholder"), id="search-input")
                yield Select(
                    [
                        (get_global_i18n().t("search.all_formats"), "all"),
                        ("TXT", "txt"),
                        ("EPUB", "epub"),
                        ("MOBI", "mobi"),
                        ("PDF", "pdf"),
                        ("AZW3", "azw3")
                    ],
                    value="all",
                    id="format-filter",
                    prompt=get_global_i18n().t("search.file_format")
                )
            yield DataTable(id="results-table")
            with Horizontal(id="search-buttons", classes="btn-row"):
                yield Button("← " + get_global_i18n().t("common.cancel"), id="cancel-btn", variant="primary")
                yield Button(get_global_i18n().t("common.select"), id="select-btn", disabled=True)
    
    def on_mount(self) -> None:
        """挂载时应用主题并初始化表格"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        # 应用当前主题
        current_theme = self.theme_manager.get_current_theme_name()
        self.theme_manager.set_theme(current_theme)
        table = self.query_one("#results-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(
            get_global_i18n().t("search.position"),
            get_global_i18n().t("search.preview")
        )
        table.zebra_stripes = True
        
    async def on_input_changed(self, event: Input.Changed) -> None:
        """输入变化时执行搜索"""
        if event.input.id == "search-input" and event.input.value:
            await self._perform_search()
    
    async def on_select_changed(self, event: Select.Changed) -> None:
        """文件类型选择变化时执行搜索"""
        if event.select.id == "format-filter":
            await self._perform_search()
    
    async def _perform_search(self) -> None:
        """执行搜索操作"""
        search_input = self.query_one("#search-input", Input)
        format_filter = self.query_one("#format-filter", Select)
        
        # 如果搜索输入框为空且没有选择特定格式，则不搜索
        if not search_input.value and format_filter.value == "all":
            return
            
        from src.core.bookshelf import Bookshelf
        
        # 获取文件类型筛选条件（添加点号前缀）
        selected_format = f".{format_filter.value}" if format_filter.value and format_filter.value != "all" else None
        
        # 使用书架进行书籍搜索，支持文件类型筛选
        bookshelf = Bookshelf()
        books = bookshelf.search_books(search_input.value, format=selected_format)
        
        table = self.query_one("#results-table", DataTable)
        table.clear()
        
        # 更新搜索结果
        self.results = []
        for i, book in enumerate(books):
            # 创建搜索结果对象
            from src.core.search import SearchResult
            result = SearchResult(
                book_id=book.path,
                position=get_global_i18n().t("search.book"),  # 显示为书籍而不是具体位置
                preview=f"{book.title} - {book.author} ({book.format})",
                score=0.0
            )
            self.results.append(result)
            
            table.add_row(
                result.position,
                result.preview,
                key=f"{result.book_id}:{i}"
            )
        
        # 如果有结果，自动选择第一行
        if self.results:
            from textual.coordinate import Coordinate
            table.cursor_coordinate = Coordinate(0, 0)
            self.query_one("#select-btn", Button).disabled = False
        
        # 更新选择按钮状态
        self.query_one("#select-btn", Button).disabled = len(self.results) == 0
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """行选择时更新选择按钮状态"""
        self.query_one("#select-btn", Button).disabled = False
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "select-btn":
            self._select_current_result()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
            

            
    def _select_current_result(self) -> None:
        """选择当前选中的搜索结果"""
        table = self.query_one("#results-table", DataTable)
        if table.cursor_row is not None:
            selected_index = table.cursor_row
            if 0 <= selected_index < len(self.results):
                self.dismiss(self.results[selected_index])

    def on_key(self, event: events.Key) -> None:
        """键盘事件处理：确保 ESC 能关闭，Enter 能选择"""
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
        elif event.key == "enter":
            # 与按钮一致的行为：选择当前结果
            self._select_current_result()
            event.stop()