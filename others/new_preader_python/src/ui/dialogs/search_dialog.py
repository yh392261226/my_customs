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
        # table.cursor_type = "row"
        table.add_columns(
            (get_global_i18n().t("search.position"), "position"),
            (get_global_i18n().t("search.preview"), "preview"),
            (get_global_i18n().t("bookshelf.view_file"), "view_action"),  # 查看文件按钮列
            (get_global_i18n().t("bookshelf.delete"), "delete_action")      # 删除按钮列
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
            
            # 添加操作按钮
            view_file_button = f"[{get_global_i18n().t('bookshelf.view_file')}]"
            delete_button = f"[{get_global_i18n().t('bookshelf.delete')}]"
            
            table.add_row(
                result.position,
                result.preview,
                view_file_button,  # 查看文件按钮
                delete_button,     # 删除按钮
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
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """
        数据表单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        # 获取选中的单元格信息
        cell_value = event.value
        coordinate = event.coordinate
        cell_key = event.cell_key
        
        # 检查是否是操作按钮列
        column_key = cell_key.column_key.value
        if column_key in ["view_action", "delete_action"]:
            # 获取书籍ID
            row_key = cell_key.row_key.value
            if not row_key:
                return
                
            # 从行键中提取书籍路径（格式为"路径:索引"）
            book_path = row_key.split(":")[0]
            
            # 根据列键判断点击的是哪个按钮
            if column_key == "view_action":
                self._view_file(book_path)
            elif column_key == "delete_action":
                self._delete_book(book_path)
            
            # 阻止默认的行选择行为
            event.prevent_default()
    
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
    
    def _view_file(self, book_path: str) -> None:
        """查看书籍文件"""
        try:
            import os
            import subprocess
            import platform
            
            # 检查文件是否存在
            if not os.path.exists(book_path):
                self.notify(f"{get_global_i18n().t('bookshelf.file_not_exists')}: {book_path}", severity="error")
                return
            
            # 根据操作系统打开文件管理器
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", "-R", book_path], check=False)
            elif system == "Windows":
                subprocess.run(["explorer", "/select,", book_path], check=False)
            elif system == "Linux":
                subprocess.run(["xdg-open", os.path.dirname(book_path)], check=False)
            else:
                # 通用方法：打开文件所在目录
                folder_path = os.path.dirname(book_path)
                if os.path.exists(folder_path):
                    subprocess.run(["open", folder_path], check=False)
                else:
                    self.notify(get_global_i18n().t("bookshelf.open_directory_failed"), severity="warning")
                    return
            
            self.notify(f"{get_global_i18n().t('bookshelf.opened_in_file_explorer')}: {os.path.basename(book_path)}", severity="information")
            
        except Exception as e:
            self.notify(f"{get_global_i18n().t('bookshelf.view_file_failed')}: {e}", severity="error")
    
    def _delete_book(self, book_path: str) -> None:
        """删除书籍"""
        try:
            from src.core.bookshelf import Bookshelf
            
            # 获取书籍信息用于确认对话框
            bookshelf = Bookshelf()
            book = bookshelf.get_book(book_path)
            
            if not book:
                self.notify(get_global_i18n().t("bookshelf.did_not_find_book"), severity="error")
                return
            
            # 显示确认对话框
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            
            def handle_delete_result(result: Optional[bool]) -> None:
                """处理删除确认结果"""
                if result:
                    # 确认删除
                    try:
                        # 从书架中删除书籍
                        success = bookshelf.remove_book(book_path)
                        if success:
                            self.notify(get_global_i18n().t("bookshelf.delete_book_success"), severity="information")
                            # 重新执行搜索以刷新列表
                            self._perform_search()
                        else:
                            self.notify(get_global_i18n().t("bookshelf.delete_book_failed"), severity="error")
                    except Exception as e:
                        self.notify(f"{get_global_i18n().t('bookshelf.delete_book_failed')}: {e}", severity="error")
            
            # 显示确认对话框
            confirm_dialog = ConfirmDialog(
                self.theme_manager,
                get_global_i18n().t("bookshelf.confirm_delete"),
                get_global_i18n().t("bookshelf.confirm_delete_message", book=book.title)
            )
            self.app.push_screen(confirm_dialog, handle_delete_result)
                
        except Exception as e:
            self.notify(f"{get_global_i18n().t('bookshelf.delete_book_failed')}: {e}", severity="error")