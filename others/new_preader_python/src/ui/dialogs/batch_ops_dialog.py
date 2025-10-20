"""
批量操作对话框
"""


import os
import json
from datetime import datetime
from typing import List, Set, Optional, Dict, Any
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, DataTable, Label, Input, Select
from textual import on, events
from src.ui.messages import RefreshBookshelfMessage
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.ui.dialogs.confirm_dialog import ConfirmDialog

from src.utils.logger import get_logger

logger = get_logger(__name__)

class BatchInputDialog(ModalScreen[str]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """批量输入对话框"""
    
    CSS_PATH = "../styles/batch_input_overrides.tcss"
    
    def __init__(self, title: str, placeholder: str, description: str = "") -> None:
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        # 保证描述为字符串，避免 None 传入 Label
        self.description = description or ""
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        # 构建按钮行
        buttons_row = Horizontal(
            Button(get_global_i18n().t("common.ok"), id="ok-btn", variant="primary"),
            Button(get_global_i18n().t("common.cancel"), id="cancel-btn"),
            id="batch-input-buttons"
        )
        # 构建内容
        children = [Label(self.title, id="batch-input-title")]
        if isinstance(self.description, str) and self.description != "":
            children.append(Label(self.description, id="batch-input-description"))
        children.extend([
            Input(placeholder=self.placeholder, id="batch-input"),
            buttons_row,
        ])
        # 以标准嵌套方式生成布局
        yield Container(
            Vertical(*children, id="batch-input-dialog"),
            id="batch-input-dialog-container"
        )
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        # 应用通用样式隔离，并聚焦输入框
        apply_universal_style_isolation(self)
        self.query_one("#batch-input", Input).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "ok-btn":
            input_widget = self.query_one("#batch-input", Input)
            self.dismiss(input_widget.value.strip())
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
    
    @on(Input.Submitted, "#batch-input")
    def on_input_submitted(self) -> None:
        """输入框回车提交"""
        input_widget = self.query_one("#batch-input", Input)
        self.dismiss(input_widget.value.strip())
    
    def on_key(self, event: events.Key) -> None:
        """按键事件处理"""
        if event.key == "escape":
            self.dismiss("")
            event.stop()

class BatchOpsDialog(ModalScreen[Dict[str, Any]]):
    """批量操作对话框"""
    
    CSS_PATH = "../styles/batch_ops_overrides.tcss"
    BINDINGS = [
        ("space", "toggle_row", get_global_i18n().t('batch_ops.toggle_row')),
        ("n", "next_page", get_global_i18n().t('batch_ops.next_page')),
        ("p", "prev_page", get_global_i18n().t('batch_ops.prev_page')),
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, bookshelf: Bookshelf):
        """
        初始化批量操作对话框
        
        Args:
            theme_manager: 主题管理器
            bookshelf: 书架
        """
        super().__init__()
        self.i18n = get_global_i18n()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        self.selected_books: Set[str] = set()
        
        # 分页相关属性
        self._current_page = 1
        self._books_per_page = 20
        self._total_pages = 1
        self._all_books: List[Any] = []
        
        # 搜索相关属性
        self._search_keyword = ""
        self._selected_format = "all"
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        yield Container(
            Vertical(
                # 标题
                Label(get_global_i18n().t("bookshelf.batch_ops.title"), id="batch-ops-title", classes="section-title"),
                
                # 操作按钮区域
                Horizontal(
                    Button(get_global_i18n().t("bookshelf.batch_ops.select_all"), id="select-all-btn"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.invert_selection"), id="invert-selection-btn"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.deselect_all"), id="deselect-all-btn"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.set_author"), id="set-author-btn", variant="primary"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.set_tags"), id="set-tags-btn", variant="primary"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.clear_tags"), id="clear-tags-btn", variant="warning"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.delete"), id="delete-btn", variant="error"),
                    Button(get_global_i18n().t("batch_ops.remove_missing"), id="remove-missing-btn", variant="error"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.export"), id="export-btn"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.cancel"), id="cancel-btn"),
                    id="batch-ops-buttons", classes="btn-row"
                ),

                # 搜索框
                Horizontal(
                    Input(placeholder=get_global_i18n().t("bookshelf.search_placeholder"), id="search-input-field"),
                    Select(
                    [
                        (get_global_i18n().t("batch_ops.all_formats"), "all"),
                        ("TXT", "txt"),
                        ("EPUB", "epub"),
                        ("MOBI", "mobi"),
                        ("PDF", "pdf"),
                        ("AZW3", "azw3")
                    ],
                    value="all",
                    id="search-format-filter",
                    prompt=get_global_i18n().t("batch_ops.file_format")
                ),
                    Button(get_global_i18n().t("common.search"), id="search-btn"),
                    id="batch-ops-search-contain", classes="form-row"
                ),
                
                # 分页信息显示
                Label("", id="batch-ops-page-info"),
                
                # 书籍列表
                DataTable(id="batch-ops-table"),
                
                # 状态信息
                Label(get_global_i18n().t("batch_ops.status_info"), id="batch-ops-status"),
                
                id="batch-ops-container"
            )
        )
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 初始化数据表 - 使用正确的列键设置方法
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 清除现有列
        table.clear(columns=True)
        
        # 添加带键的列
        table.add_column(get_global_i18n().t("batch_ops.index"), key="index")
        table.add_column(get_global_i18n().t("bookshelf.title"), key="title")
        table.add_column(get_global_i18n().t("bookshelf.author"), key="author")
        table.add_column(get_global_i18n().t("bookshelf.format"), key="format")
        table.add_column(get_global_i18n().t("bookshelf.tags"), key="tags")
        table.add_column(get_global_i18n().t("batch_ops.selected"), key="selected")
        
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        # 加载书籍数据
        self._load_books()
    
    def _load_books(self) -> None:
        """加载书籍数据"""
        # 获取所有书籍
        all_books = self.bookshelf.get_all_books()
        
        # 应用搜索过滤
        filtered_books = self._filter_books(all_books)
        self._all_books = filtered_books
        
        # 计算总页数
        self._total_pages = max(1, (len(self._all_books) + self._books_per_page - 1) // self._books_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 计算当前页的书籍范围
        start_index = (self._current_page - 1) * self._books_per_page
        end_index = min(start_index + self._books_per_page, len(self._all_books))
        current_page_books = self._all_books[start_index:end_index]
        
        table = self.query_one("#batch-ops-table", DataTable)
        table.clear()
        
        for i, book in enumerate(current_page_books):
            # 计算当前页的序号（从1开始）
            index = (self._current_page - 1) * self._books_per_page + i + 1
            
            # 格式化标签显示，直接显示逗号分隔的字符串
            tags_display = book.tags if book.tags else ""
            
            # 检查书籍是否已经被选中
            is_selected = book.path in self.selected_books
            selection_marker = "✓" if is_selected else "□"
            
            table.add_row(
                str(index),  # 序号
                book.title,
                book.author,
                book.format.upper(),
                tags_display,
                selection_marker,  # 根据选中状态显示不同的标记
                key=book.path
            )
        
        # 更新分页信息
        self._update_pagination_info()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        数据表行选择时的回调
        说明：不在行选择事件中切换选中状态，避免点击任意列都触发选中翻转。
        仅用于更新光标/高亮，具体切换逻辑在 on_data_table_cell_selected 中处理。
        """
        # 行选择事件不做选中切换，保持与单元格点击逻辑一致
        return
    
    @on(events.Key)
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "space":
            table = self.query_one("#batch-ops-table", DataTable)
            if table.cursor_row is not None:
                # 获取当前行的键（书籍路径）
                row_key = list(table.rows.keys())[table.cursor_row]
                if row_key and row_key.value:
                    book_id = row_key.value
                    self._toggle_book_selection(book_id, table, table.cursor_row)
            event.stop()
        elif event.key == "escape":
            # ESC键返回，效果与点击取消按钮相同
            self.dismiss({"refresh": False})
            event.stop()
        elif event.key == "n":
            # N键下一页
            if self._current_page < self._total_pages:
                self._current_page += 1
                self._load_books()
            event.stop()
        elif event.key == "p":
            # P键上一页
            if self._current_page > 1:
                self._current_page -= 1
                self._load_books()
            event.stop()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            table = self.query_one("#batch-ops-table", DataTable)
            if (table.cursor_row == len(table.rows) - 1 and 
                self._current_page < self._total_pages):
                self._current_page += 1
                self._load_books()
                # 将光标移动到新页面的第一行
                table = self.query_one("#batch-ops-table", DataTable)
                table.action_cursor_down()  # 先向下移动一次
                table.action_cursor_up()     # 再向上移动一次，确保在第一行
                event.stop()
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            table = self.query_one("#batch-ops-table", DataTable)
            if table.cursor_row == 0 and self._current_page > 1:
                self._current_page -= 1
                self._load_books()
                # 将光标移动到新页面的最后一行
                table = self.query_one("#batch-ops-table", DataTable)
                for _ in range(len(table.rows) - 1):
                    table.action_cursor_down()  # 移动到最底部
                event.stop()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """
        单元格选择事件：仅当点击“已选择”列（最后一列）时，切换该行的选中状态。
        """
        table = event.data_table
        # 计算是否点击的是最后一列（已选择列）
        try:
            selected_col_index = len(table.columns) - 1
        except Exception:
            # 兼容旧版本 DataTable 属性名
            selected_col_index = len(table.ordered_columns) - 1
        if event.coordinate.column != selected_col_index:
            return  # 非“已选择”列，不切换

        # 获取行索引与行键
        row_index = event.coordinate.row
        # 获取当前行的键（书籍路径）
        try:
            row_key = list(table.rows.keys())[row_index]
        except Exception:
            return
        if not row_key or not getattr(row_key, "value", None):
            return
        book_id = row_key.value

        # 执行切换并阻止事件进一步影响其他处理器
        self._toggle_book_selection(book_id, table, row_index)
        event.stop()
    
    def _toggle_book_selection(self, book_id: str, table: DataTable[Any], row_index: int) -> None:
        """切换书籍选中状态"""
        # 获取行键对象
        row_key = list(table.rows.keys())[row_index]
        
        # 获取列键对象（最后一列，选中状态列）
        column_key = table.ordered_columns[-1].key
        
        if book_id in self.selected_books:
            self.selected_books.discard(book_id)
            table.update_cell(row_key, column_key, "□")
        else:
            self.selected_books.add(book_id)
            table.update_cell(row_key, column_key, "✓")
        
        self._update_status()
    
    def _update_status(self) -> None:
        """更新状态信息"""
        status_label = self.query_one("#batch-ops-status", Label)
        selected_count = len(self.selected_books)
        status_label.update(
            get_global_i18n().t("batch_ops.selected_count", count=selected_count)
        )
    
    def _filter_books(self, books: List[Any]) -> List[Any]:
        """根据搜索关键词和文件格式过滤书籍"""
        filtered_books = books
        
        # 按名称搜索（支持标题、拼音、作者、标签）
        if self._search_keyword:
            keyword = self._search_keyword.lower()
            filtered_books = [
                book for book in filtered_books
                if (keyword in book.title.lower() or 
                    keyword in book.author.lower() or
                    (hasattr(book, 'pinyin') and book.pinyin and keyword in book.pinyin.lower()) or
                    (book.tags and keyword in book.tags.lower()))
            ]
        
        # 按文件格式过滤
        if self._selected_format != "all":
            filtered_books = [
                book for book in filtered_books
                if book.format.lower().lstrip('.') == self._selected_format.lower()
            ]
        
        return filtered_books
    
    def _update_pagination_info(self) -> None:
        """更新分页信息"""
        page_info_label = self.query_one("#batch-ops-page-info", Label)
        
        # 如果有搜索条件，显示过滤后的结果信息
        if self._search_keyword or self._selected_format != "all":
            page_info_label.update(
                get_global_i18n().t("batch_ops.page_info_filtered", 
                                   page=self._current_page, 
                                   total_pages=self._total_pages,
                                   filtered_count=len(self._all_books),
                                   total_count=len(self.bookshelf.get_all_books()))
            )
        else:
            page_info_label.update(
                get_global_i18n().t("batch_ops.page_info", 
                                   page=self._current_page, 
                                   total_pages=self._total_pages,
                                   total_books=len(self._all_books))
            )

    # 通过 BINDINGS 触发的动作（保留 on_key 作为过渡）
    def action_toggle_row(self) -> None:
        """切换当前行选中状态"""
        table = self.query_one("#batch-ops-table", DataTable)
        if table.cursor_row is not None:
            # 获取当前行的键（书籍路径）
            row_key = list(table.rows.keys())[table.cursor_row]
            if row_key and row_key.value:
                book_id = row_key.value
                self._toggle_book_selection(book_id, table, table.cursor_row)

    def action_next_page(self) -> None:
        """下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_books()

    def action_prev_page(self) -> None:
        """上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._load_books()

    def action_cancel(self) -> None:
        """取消返回"""
        self.dismiss({"refresh": False})
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "select-all-btn":
            self._select_all_books()
        elif event.button.id == "invert-selection-btn":
            self._invert_selection()
        elif event.button.id == "deselect-all-btn":
            self._deselect_all_books()
        elif event.button.id == "delete-btn":
            self._delete_selected_books()
        elif event.button.id == "set-author-btn":
            await self._set_author_for_selected_books()
        elif event.button.id == "set-tags-btn":
            await self._set_tags_for_selected_books()
        elif event.button.id == "clear-tags-btn":
            await self._clear_tags_for_selected_books()
        elif event.button.id == "remove-missing-btn":
            await self._remove_missing_books()
        elif event.button.id == "export-btn":
            self._export_selected_books()
        elif event.button.id == "search-btn":
            self._perform_search()
        elif event.button.id == "cancel-btn":
            self.dismiss({"refresh": False})
    
    def _select_all_books(self) -> None:
        """选择当前显示的所有书籍（搜索过滤后的书籍）"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 只选择当前显示的书籍（搜索过滤后的书籍）
        for row_key in table.rows.keys():
            # 从表格行键中获取书籍路径（RowKey转换为字符串）
            book_path = str(row_key)
            self.selected_books.add(book_path)
        
        # 获取列键对象（最后一列，选中状态列）
        column_key = table.ordered_columns[-1].key
        
        # 更新所有行的选中状态
        for row_index, row_key in enumerate(table.rows.keys()):
            table.update_cell(row_key, column_key, "✓")
        
        self._update_status()
    
    def _invert_selection(self) -> None:
        """反选当前显示的所有书籍（搜索过滤后的书籍）"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 获取列键对象（最后一列，选中状态列）
        column_key = table.ordered_columns[-1].key
        
        # 反选当前显示的书籍（搜索过滤后的书籍）
        for row_key in table.rows.keys():
            # 从表格行键中获取书籍路径（RowKey转换为字符串）
            book_path = str(row_key)
            
            if book_path in self.selected_books:
                # 如果已选中，则取消选中
                self.selected_books.discard(book_path)
                table.update_cell(row_key, column_key, "□")
            else:
                # 如果未选中，则选中
                self.selected_books.add(book_path)
                table.update_cell(row_key, column_key, "✓")
        
        self._update_status()
    
    def _deselect_all_books(self) -> None:
        """取消选择当前显示的所有书籍（搜索过滤后的书籍）"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 只取消选择当前显示的书籍（搜索过滤后的书籍）
        for row_key in table.rows.keys():
            # 从表格行键中获取书籍路径（RowKey转换为字符串）
            book_path = str(row_key)
            self.selected_books.discard(book_path)
        
        # 获取列键对象（最后一列，选中状态列）
        column_key = table.ordered_columns[-1].key
        
        # 更新所有行的选中状态
        for row_index, row_key in enumerate(table.rows.keys()):
            table.update_cell(row_key, column_key, "□")
        
        self._update_status()
    
    def _delete_selected_books(self) -> None:
        """删除选中的书籍"""
        if not self.selected_books:
            self.notify(get_global_i18n().t("batch_ops.no_books_selected"), severity="warning")
            return
        
        # 这里实现删除逻辑
        for book_id in self.selected_books:
            self.bookshelf.remove_book(book_id)
        
        self.notify(
            get_global_i18n().t("batch_ops.books_deleted", count=len(self.selected_books)),
            severity="information"
        )
        
        # 重新加载书籍列表
        self._load_books()
        self.selected_books.clear()
        self._update_status()
        
        # 设置返回结果为需要刷新
        self.dismiss({"refresh": True})
    
    def _export_selected_books(self) -> None:
        """导出选中的书籍"""
        if not self.selected_books:
            self.notify(get_global_i18n().t("batch_ops.no_books_selected"), severity="warning")
            return
        
        try:
            # 获取选中的书籍
            selected_books = []
            for book_path in self.selected_books:
                book = self.bookshelf.get_book(book_path)
                if book:
                    selected_books.append(book.to_dict())
            
            if not selected_books:
                self.notify(get_global_i18n().t("batch_ops.no_valid_books"), severity="warning")
                return
            
            # 创建导出数据
            export_data = {
                "books": selected_books,
                "export_time": datetime.now().isoformat(),
                "export_count": len(selected_books)
            }
            
            # 生成导出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_filename = f"books_export_{timestamp}.json"
            export_path = os.path.join(os.path.expanduser("~"), "Downloads", export_filename)
            
            # 确保下载目录存在
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            # 导出数据
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)

            self.selected_books.clear()  # 清空选中状态
            self._clear_table_selection()  # 清除表格的视觉选中状态
            self._update_status()
            
            self.notify(
                get_global_i18n().t("batch_ops.books_exported_success", 
                           count=len(selected_books), 
                           path=export_path),
                severity="information"
            )
            
        except Exception as e:
            logger.error(get_global_i18n().t("batch_ops.export_failed", error=e))
            self.notify(
                get_global_i18n().t("batch_ops.export_failed", error=str(e)),
                severity="error"
            )
    
    async def _set_author_for_selected_books(self) -> None:
        """为选中的书籍设置作者"""
        if not self.selected_books:
            self.notify(get_global_i18n().t("batch_ops.no_books_selected"), severity="warning")
            return
        
        def handle_author_input(author: Optional[str]) -> None:
            """处理作者输入结果"""
            if not author:  # 用户取消或输入为空
                return
            
            try:
                # 调用bookshelf的批量设置作者方法
                success_count = self.bookshelf.batch_set_author(list(self.selected_books), author)
                
                self.notify(
                    get_global_i18n().t("batch_ops.books_author_updated", count=success_count),
                    severity="information"
                )
                
                # 重新加载书籍列表以显示更新后的作者信息
                self._load_books()
                self.selected_books.clear()  # 清空选中状态
                self._clear_table_selection()  # 清除表格的视觉选中状态
                self._update_status()
                
                # 设置返回结果为需要刷新
                self.dismiss({"refresh": True})
                

                
            except Exception as e:
                logger.error(get_global_i18n().t("batch_ops.set_author_failed", error=str(e)))
                self.notify(
                    get_global_i18n().t("batch_ops.set_author_failed", error=str(e)),
                    severity="error"
                )
        
        # 弹出输入对话框获取作者
        self.app.push_screen(
            BatchInputDialog(
                get_global_i18n().t("batch_ops.set_author"),
                get_global_i18n().t("bookshelf.author"),
                get_global_i18n().t("batch_ops.set_author")
            ),
            callback=handle_author_input
        )
        

    
    async def _set_tags_for_selected_books(self) -> None:
        """为选中的书籍设置标签"""
        if not self.selected_books:
            self.notify(get_global_i18n().t("batch_ops.no_books_selected"), severity="warning")
            return
        
        # 弹出输入对话框获取标签（逗号分隔）
        def on_tags_input(tags_input: str | None) -> None:
            if not tags_input:  # 用户取消或输入为空
                return
            
            try:
                # 解析标签（逗号分隔，去除空格）
                # 注意：请勿将单个汉字用逗号分隔，应输入完整标签如"小说,科幻"
                tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                
                # 调用bookshelf的批量设置标签方法
                success_count = self.bookshelf.batch_set_tags(list(self.selected_books), tags)
                
                self.notify(
                    get_global_i18n().t("batch_ops.books_tags_updated", count=success_count),
                    severity="information"
                )
                
                # 重新加载书籍列表
                self._load_books()
                self.selected_books.clear()  # 清空选中状态
                self._clear_table_selection()  # 清除表格的视觉选中状态
                self._update_status()
                
                # 设置返回结果为需要刷新
                self.dismiss({"refresh": True})
                

                
            except Exception as e:
                logger.error(get_global_i18n().t("batch_ops.set_tags_failed", error=str(e)))
                self.notify(
                    get_global_i18n().t("batch_ops.set_tags_failed", error=str(e)),
                    severity="error"
                )
        
        self.app.push_screen(
            BatchInputDialog(
                get_global_i18n().t("batch_ops.set_tags"),
                get_global_i18n().t("bookshelf.tags"),
                get_global_i18n().t("batch_ops.set_tags") + "\n" + get_global_i18n().t("common.comma_separated") + "\n" + "请输入完整的标签，如：小说,科幻,经典"
            ),
            callback=on_tags_input
        )
    
    async def _clear_tags_for_selected_books(self) -> None:
        """清空选中书籍的标签"""
        if not self.selected_books:
            self.notify(
                get_global_i18n().t("batch_ops.no_books_selected"),
                severity="warning"
            )
            return
        
        # 使用ConfirmDialog实现确认功能
        def on_confirm(confirmed: Optional[bool]) -> None:
            """处理确认结果"""
            if not confirmed:
                return
            
            async def clear_tags_async():
                """异步清空标签"""
                try:
                    # 调用bookshelf的批量清空标签方法
                    success_count = self.bookshelf.batch_clear_tags(list(self.selected_books))
                    
                    self.notify(
                        get_global_i18n().t("batch_ops.books_tags_cleared", count=success_count),
                        severity="information"
                    )
                    
                    # 重新加载书籍列表
                    self._load_books()
                    self.selected_books.clear()  # 清空选中状态
                    self._clear_table_selection()  # 清除表格的视觉选中状态
                    self._update_status()
                    
                    # 设置返回结果为需要刷新
                    self.dismiss({"refresh": True})
                    

                    
                except Exception as e:
                    logger.error(get_global_i18n().t("batch_ops.clear_tags_failed", error=str(e)))
                    self.notify(
                        get_global_i18n().t("batch_ops.clear_tags_failed", error=str(e)),
                        severity="error"
                    )
            
            # 执行异步操作
            self.call_later(clear_tags_async)
        
        # 弹出确认对话框
        self.app.push_screen(
            ConfirmDialog(
                self.theme_manager,
                get_global_i18n().t("batch_ops.clear_tags_confirm"),
                get_global_i18n().t("batch_ops.clear_tags_confirm_message")
            ),
            callback=on_confirm
        )
    
    async def _remove_missing_books(self) -> None:
        """批量删除不存在的书籍"""
        # 使用ConfirmDialog实现确认功能
        def on_confirm(confirmed: Optional[bool]) -> None:
            """处理确认结果"""
            if not confirmed:
                return
            
            async def remove_missing_async():
                """异步删除不存在书籍"""
                try:
                    # 显示处理中消息
                    self.notify(
                        get_global_i18n().t("batch_ops.remove_missing_processing"),
                        severity="information"
                    )
                    
                    # 调用bookshelf的验证并删除不存在书籍方法
                    removed_count, removed_books = self.bookshelf.verify_and_remove_missing_books()
                    
                    if removed_count > 0:
                        self.notify(
                            get_global_i18n().t("batch_ops.remove_missing_completed", count=removed_count),
                            severity="information"
                        )
                    else:
                        self.notify(
                            get_global_i18n().t("batch_ops.remove_missing_no_books"),
                            severity="information"
                        )
                    
                    # 重新加载书籍列表
                    self._load_books()
                    self.selected_books.clear()  # 清空选中状态
                    self._clear_table_selection()  # 清除表格的视觉选中状态
                    self._update_status()
                    
                    # 设置返回结果为需要刷新
                    self.dismiss({"refresh": True})
                    
                except Exception as e:
                    logger.error(get_global_i18n().t("batch_ops.remove_missing_failed", error=str(e)))
                    self.notify(
                        get_global_i18n().t("batch_ops.remove_missing_failed", error=str(e)),
                        severity="error"
                    )
            
            # 执行异步操作
            self.call_later(remove_missing_async)
        
        # 弹出确认对话框
        self.app.push_screen(
            ConfirmDialog(
                self.theme_manager,
                get_global_i18n().t("batch_ops.remove_missing_confirm"),
                get_global_i18n().t("batch_ops.remove_missing_confirm_message")
            ),
            callback=on_confirm
        )
    
    def _invert_selection(self) -> None:
        """反选所有书籍"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 获取所有书籍路径
        all_books = {book.path for book in self.bookshelf.get_all_books()}
        
        # 反选逻辑：当前选中的变为未选中，未选中的变为选中
        new_selected_books = all_books - self.selected_books
        self.selected_books = new_selected_books
        
        # 获取列键对象（最后一列，选中状态列）
        column_key = table.ordered_columns[-1].key
        
        # 更新所有行的选中状态
        for row_index, row_key in enumerate(table.rows.keys()):
            book_id = row_key.value
            if book_id in self.selected_books:
                table.update_cell(row_key, column_key, "✓")
            else:
                table.update_cell(row_key, column_key, "□")
        
        self._update_status()
    
    def _perform_search(self) -> None:
        """执行搜索操作"""
        # 获取搜索关键词
        search_input = self.query_one("#search-input-field", Input)
        self._search_keyword = search_input.value.strip()
        
        # 获取文件格式筛选
        format_select = self.query_one("#search-format-filter", Select)
        # 规避 NoSelection/None：统一为 "all"
        value = getattr(format_select, "value", None)
        try:
            # Textual Select 的 NoSelection 可能没有可比性，转字符串判断
            is_valid = isinstance(value, str) and value != ""
        except Exception:
            is_valid = False
        self._selected_format = value if is_valid else "all"
        
        # 重置到第一页并重新加载书籍
        self._current_page = 1
        self._load_books()
    
    @on(Input.Submitted, "#search-input-field")
    def on_search_input_submitted(self) -> None:
        """搜索输入框回车提交"""
        self._perform_search()
    
    @on(Select.Changed, "#search-format-filter")
    def on_format_filter_changed(self, event: Select.Changed) -> None:
        """文件格式筛选器变化时自动搜索"""
        # 规避 NoSelection/None：统一为 "all"
        value = getattr(event.select, "value", None)
        is_valid = isinstance(value, str) and value != ""
        self._selected_format = value if is_valid else "all"
        self._current_page = 1
        self._load_books()
    
    def _clear_table_selection(self) -> None:
        """清除表格的视觉选中状态"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 获取列键对象（最后一列，选中状态列）
        column_key = table.ordered_columns[-1].key
        
        # 更新所有行的选中状态为未选中
        for row_index, row_key in enumerate(table.rows.keys()):
            table.update_cell(row_key, column_key, "□")
        
        # 清除DataTable的选中状态
        if hasattr(table, 'cursor_row') and table.cursor_row is not None:
            # 通过移动光标到第一行来清除选中状态
            from textual.coordinate import Coordinate
            table.cursor_coordinate = Coordinate(0, 0)

