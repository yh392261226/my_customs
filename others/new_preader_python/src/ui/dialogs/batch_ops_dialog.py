"""
批量操作对话框
"""


import os
import json
from datetime import datetime
from typing import List, Set, Optional, Dict, Any, Tuple
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Center
from textual.widgets import Header, Static, Button, Label, Input, Select, Header, Footer
from textual.widgets import DataTable
from textual import on, events
from src.ui.messages import RefreshBookshelfMessage
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.ui.dialogs.confirm_dialog import ConfirmDialog
from src.config.default_config import SUPPORTED_FORMATS
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BatchInputDialog(ModalScreen[str]):
    """批量输入对话框"""
    
    CSS_PATH = "../styles/batch_input_overrides.tcss"
    
    def __init__(self, title: str, placeholder: str, description: str = "") -> None:
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        # 保证描述为字符串，避免 None 传入 Label
        self.description = str(description) if description else ""
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        # 借鉴旧版本的简洁布局
        with Container(id="batch-input-dialog-container"):
            with Vertical(id="batch-input-dialog"):
                yield Label(str(self.title), id="batch-input-title")
                if self.description and self.description != "":
                    yield Label(str(self.description), id="batch-input-description")
                yield Center(Input(placeholder=self.placeholder, id="batch-input"))
                with Horizontal(id="batch-input-buttons"):
                    yield Button(get_global_i18n().t("common.ok"), id="ok-btn", variant="primary")
                    yield Button(get_global_i18n().t("common.cancel"), id="cancel-btn")
    
    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 借鉴旧版本的样式隔离实现
        apply_universal_style_isolation(self)
        input_widget = self.query_one("#batch-input", Input)
        input_widget.focus()
    
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
        ("x", "clear_search_params", get_global_i18n().t('crawler.clear_search_params')),
        ("j", "jump_to", get_global_i18n().t('bookshelf.jump_to')),
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
    ]
    # 支持的书籍文件扩展名（从配置文件读取）
    SUPPORTED_EXTENSIONS = set(SUPPORTED_FORMATS)
    
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
        self._books_per_page = 15
        self._total_pages = 1
        self._all_books: List[Any] = []
        
        # 搜索相关属性
        self._search_keyword = ""
        self._selected_format = "all"
        self._selected_author = "all"
        
        # 排序相关属性
        self._sorted_books: List[str] = []  # 存储排序后的书籍路径顺序
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        # 动态生成搜索选择框选项
        search_options = [(get_global_i18n().t("search.all_formats"), "all")]
        # 根据SUPPORTED_EXTENSIONS生成格式选项
        for ext in self.SUPPORTED_EXTENSIONS:
            # 去掉点号，转换为大写作为显示名称
            display_name = ext.upper().lstrip('.')
            search_options.append((display_name, ext.lstrip('.')))

        # 使用 Bookshelf 类的 load_author_options 方法加载作者选项
        author_options = self.bookshelf.load_author_options()
        yield Header()
        yield Container(
            Vertical(
                # 标题
                Label(get_global_i18n().t("bookshelf.batch_ops.title"), id="batch-ops-title", classes="section-title"),
                
                # 操作按钮区域
                Horizontal(
                    Button(get_global_i18n().t("bookshelf.batch_ops.select_all"), id="select-all-btn"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.invert_selection"), id="invert-selection-btn"),
                    Button(get_global_i18n().t("bookshelf.batch_ops.deselect_all"), id="deselect-all-btn"),
                    Button(get_global_i18n().t("batch_ops.move_up"), id="move-up-btn"),
                    Button(get_global_i18n().t("batch_ops.move_down"), id="move-down-btn"),
                    Button(get_global_i18n().t("batch_ops.merge"), id="merge-btn", variant="warning"),
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
                    options=search_options,
                    value="all",
                    id="search-format-filter",
                    prompt=get_global_i18n().t("common.select_ext_prompt")
                ),
                    Select(
                    options=author_options,
                    value="all",
                    id="search-author-filter",
                    prompt=get_global_i18n().t("bookshelf.select_source")
                ),
                    Button(get_global_i18n().t("common.search"), id="search-btn"),
                    id="batch-ops-search-contain", classes="form-row"
                ),
                
                # 分页信息显示
                Label("", id="batch-ops-page-info"),
                
                # 书籍列表
                DataTable(id="batch-ops-table"),
                
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
                Label(get_global_i18n().t("batch_ops.status_info"), id="batch-ops-status"),
                
                id="batch-ops-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        
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
        
        # 确保表格获得焦点
        try:
            table.focus()
        except Exception:
            pass
    
    def _load_books(self) -> None:
        """加载书籍数据"""
        # 获取所有书籍
        all_books = self.bookshelf.get_all_books()
        
        # 应用搜索过滤
        filtered_books = self._filter_books(all_books)
        
        # 如果有排序列表，根据排序列表重新排序当前页的书籍
        if self._sorted_books:
            # 创建路径到书籍对象的映射
            book_map = {book.path: book for book in filtered_books}
            
            # 按照排序列表的顺序重新排列书籍
            sorted_books = []
            remaining_books = filtered_books.copy()
            
            # 先添加排序列表中的书籍
            for path in self._sorted_books:
                if path in book_map and book_map[path] in remaining_books:
                    sorted_books.append(book_map[path])
                    remaining_books.remove(book_map[path])
            
            # 再添加剩余的书籍
            sorted_books.extend(remaining_books)
            
            filtered_books = sorted_books
        else:
            # 如果没有排序列表，初始化排序列表为当前显示书籍的顺序
            self._sorted_books = [book.path for book in filtered_books]
        
        self._all_books = filtered_books
        
        # 计算总页数
        self._total_pages = max(1, (len(self._all_books) + self._books_per_page - 1) // self._books_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 计算当前页的书籍范围
        start_index = (self._current_page - 1) * self._books_per_page
        end_index = min(start_index + self._books_per_page, len(self._all_books))
        current_page_books = self._all_books[start_index:end_index]
        
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 保存当前光标位置和选中状态
        old_cursor_row = table.cursor_row if hasattr(table, 'cursor_row') and table.cursor_row is not None else None
        
        # 保存当前焦点路径
        old_focus_path = None
        if old_cursor_row is not None and 0 <= old_cursor_row < len(table.rows):
            row_keys = list(table.rows.keys())
            row_key = row_keys[old_cursor_row]
            if hasattr(row_key, 'value'):
                old_focus_path = str(row_key.value)
            else:
                old_focus_path = str(row_key)
        
        table.clear()
        
        # 创建全局排序序号映射
        global_sort_order = {}
        
        # 确保排序列表只包含当前显示的书籍
        current_display_paths = [book.path for book in self._all_books]
        filtered_sorted_books = [path for path in self._sorted_books if path in current_display_paths]
        
        # 添加当前显示但不在排序列表中的书籍
        for path in current_display_paths:
            if path not in filtered_sorted_books:
                filtered_sorted_books.append(path)
        
        # 使用过滤后的排序列表
        if filtered_sorted_books:
            # 使用排序列表中的位置作为序号
            for sort_index, path in enumerate(filtered_sorted_books):
                global_sort_order[path] = sort_index + 1
        else:
            # 如果没有自定义排序，使用原始顺序
            for i, book in enumerate(self._all_books):
                global_sort_order[book.path] = i + 1
        
        for i, book in enumerate(current_page_books):
            # 使用全局排序序号，而不是当前页的位置
            index = global_sort_order.get(book.path, (self._current_page - 1) * self._books_per_page + i + 1)
            
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
        
        # 恢复光标位置 - 优先根据焦点路径恢复位置
        if old_focus_path and len(table.rows) > 0:
            # 根据焦点路径找到新位置
            for i, row_key in enumerate(table.rows.keys()):
                if hasattr(row_key, 'value'):
                    book_path = str(row_key.value)
                else:
                    book_path = str(row_key)
                
                if book_path == old_focus_path:
                    # 找到焦点路径对应的行，设置光标位置
                    if hasattr(table, 'cursor_coordinate'):
                        from textual.coordinate import Coordinate
                        table.cursor_coordinate = Coordinate(row=i, column=0)
                    # 使用move_cursor方法设置光标位置
                    if hasattr(table, 'move_cursor'):
                        table.move_cursor(row=i)
                    break
        elif old_cursor_row is not None and len(table.rows) > 0:
            # 如果没有焦点路径，使用原来的光标行
            new_cursor_row = min(old_cursor_row, len(table.rows) - 1)
            
            # 确保光标坐标同步
            if hasattr(table, 'cursor_coordinate'):
                from textual.coordinate import Coordinate
                table.cursor_coordinate = Coordinate(row=new_cursor_row, column=0)
            # 使用move_cursor方法设置光标位置
            if hasattr(table, 'move_cursor'):
                table.move_cursor(row=new_cursor_row)
        
        # 强制刷新表格显示以确保选中状态正确显示
        table.refresh()
        
        # 更新状态信息，显示当前页选中数量
        self._update_status()
    
    def _refresh_table(self) -> None:
        """强制重新渲染表格，确保选中状态正确显示"""
        # 直接调用_load_books()来重新渲染整个表格
        self._load_books()
    
    def on_data_table_row_selected(self, event) -> None:
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
        # if event.key == "space":
        #     # 直接处理空格键，不依赖BINDINGS系统
        #     table = self.query_one("#batch-ops-table", DataTable)
            
        #     # 简化光标获取逻辑 - 直接使用表格的cursor_row
        #     current_row_index = getattr(table, 'cursor_row', None)
            
        #     # 如果cursor_row无效，尝试通过表格的焦点系统获取
        #     if current_row_index is None:
        #         try:
        #             # 尝试获取当前焦点行
        #             if hasattr(table, 'cursor_coordinate'):
        #                 coord = table.cursor_coordinate
        #                 if coord and hasattr(coord, 'row'):
        #                     current_row_index = coord.row
        #         except Exception:
        #             pass
            
        #     # 执行选择操作
        #     if current_row_index is not None and 0 <= current_row_index < len(table.rows):
        #         row_keys = list(table.rows.keys())
        #         row_key = row_keys[current_row_index]
        #         # 统一使用 row_key.value 获取书籍路径（与鼠标点击保持一致）
        #         if hasattr(row_key, 'value') and row_key.value:
        #             book_id = str(row_key.value)
        #         else:
        #             book_id = str(row_key)
        #         self._toggle_book_selection(book_id, table, current_row_index)
        #     else:
        #         # 如果无法确定当前行，显示提示信息
        #         self.notify("请先选择一行", severity="warning")
            
        #     event.stop()
        if event.key == "escape":
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
                self._go_to_next_page()
                # 将光标移动到新页面的第一行
                table.move_cursor(row=0, column=0)  # 直接移动到第一行第一列
                event.prevent_default()
                event.stop()
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            table = self.query_one("#batch-ops-table", DataTable)
            if table.cursor_row == 0 and self._current_page > 1:
                self._go_to_prev_page()
                last_row_index = len(table.rows) - 1
                table.move_cursor(row=last_row_index, column=0)  # 直接移动到最后一行第一列
                event.prevent_default()
                event.stop()

    def on_data_table_cell_selected(self, event) -> None:
        """
        单元格选择事件：无论点击哪一列，都设置光标位置；
        仅当点击“已选择”列（最后一列）时，切换该行的选中状态。
        """
        table = event.data_table
        
        # 设置光标位置：使用move_cursor方法而不是直接赋值
        if hasattr(table, 'move_cursor'):
            table.move_cursor(row=event.coordinate.row)
        
        # 计算是否点击的是最后一列（已选择列）
        try:
            # 确保使用正确的列键类型
            if hasattr(table, 'columns') and table.columns:
                selected_col_index = len(table.columns) - 1
            elif hasattr(table, 'ordered_columns') and table.ordered_columns:
                selected_col_index = len(table.ordered_columns) - 1
            else:
                selected_col_index = 0
        except Exception:
            selected_col_index = 0
        
        if event.coordinate.column != selected_col_index:
            return  # 非“已选择”列，不切换选中状态

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
        self._toggle_book_selection(str(book_id), table, row_index)
        event.stop()
    
    def _toggle_book_selection(self, book_id: str, table: DataTable[str], row_index: int) -> None:
        """切换书籍选中状态"""
        try:
            # 获取行键对象
            if row_index < len(table.rows):
                row_key = list(table.rows.keys())[row_index]
                
                # 获取列键对象（最后一列，选中状态列）
                column_key = 'selected'  # 默认列键
                
                # 尝试获取列键，兼容不同版本的DataTable
                column_key = None
                if hasattr(table, 'ordered_columns') and len(table.ordered_columns) > 0:
                    last_index = len(table.ordered_columns) - 1
                    if last_index >= 0:
                        column_key = table.ordered_columns[last_index].key
                elif hasattr(table, 'columns') and len(table.columns) > 0:
                    last_index = len(table.columns) - 1
                    if last_index >= 0 and hasattr(table.columns[last_index], 'key'):
                        column_key = table.columns[last_index].key
                
                if book_id in self.selected_books:
                    self.selected_books.discard(book_id)
                    # 从排序列表中移除
                    if book_id in self._sorted_books:
                        self._sorted_books.remove(book_id)
                    if column_key:
                        try:
                            table.update_cell(row_key, column_key, "□")
                        except Exception:
                            # 如果update_cell失败，重新渲染表格
                            self._load_books()
                    else:
                        # 如果无法获取column_key，重新渲染表格
                        self._load_books()
                else:
                    self.selected_books.add(book_id)
                    # 添加到排序列表
                    if book_id not in self._sorted_books:
                        self._sorted_books.append(book_id)
                    if column_key:
                        try:
                            table.update_cell(row_key, column_key, "✓")
                        except Exception:
                            # 如果update_cell失败，重新渲染表格
                            self._load_books()
                    else:
                        # 如果无法获取column_key，重新渲染表格
                        self._load_books()
                
                self._update_status()
        except Exception as e:
            # 如果出错，重新加载表格
            try:
                self._load_books()
            except Exception:
                pass
    
    def _update_status(self) -> None:
        """更新状态信息"""
        status_label = self.query_one("#batch-ops-status", Label)
        selected_count = len(self.selected_books)
        
        # 计算当前页面的选中数量
        current_page_books = []
        if len(self._all_books) > 0:
            start_index = (self._current_page - 1) * self._books_per_page
            end_index = min(start_index + self._books_per_page, len(self._all_books))
            current_page_books = self._all_books[start_index:end_index]
        
        current_page_selected_count = sum(1 for book in current_page_books if book.path in self.selected_books)
        
        # 显示总选中数量和当前页选中数量
        if selected_count > 0:
            status_label.update(
                get_global_i18n().t("batch_ops.selected_info", count=selected_count, current_count=current_page_selected_count)
            )
        else:
            status_label.update(
                get_global_i18n().t("batch_ops.selected_count", count=selected_count)
            )
    
    def _filter_books(self, books: List[Any]) -> List[Any]:
        """根据搜索关键词、文件格式和作者过滤书籍"""
        filtered_books = books
        
        # 按名称搜索（支持标题、拼音、作者、标签）
        if self._search_keyword:
            keyword = self._search_keyword.lower()
            
            # 支持使用英文逗号分割多个关键词
            keywords = [k.strip() for k in keyword.split(',') if k.strip()]
            
            if keywords:
                filtered_books = [
                    book for book in filtered_books
                    if any(
                        k in book.title.lower() or 
                        k in book.author.lower() or
                        (hasattr(book, 'pinyin') and book.pinyin and k in book.pinyin.lower()) or
                        (book.tags and k in book.tags.lower())
                        for k in keywords
                    )
                ]
        
        # 按文件格式过滤
        if self._selected_format != "all":
            filtered_books = [
                book for book in filtered_books
                if book.format and hasattr(book.format, 'lower') and book.format.lower() and book.format.lower().lstrip('.') == (self._selected_format.lower() if self._selected_format else "")
            ]
        
        # 按作者过滤
        if self._selected_author != "all":
            filtered_books = [
                book for book in filtered_books
                if book.author and hasattr(book.author, 'lower') and book.author.lower() and book.author.lower() == (self._selected_author.lower() if self._selected_author else "")
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
        
        # 更新分页按钮状态
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
            logger.error(f"更新分页按钮状态失败: {e}")

    # 通过 BINDINGS 触发的动作（保留 on_key 作为过渡）
    def action_toggle_row(self) -> None:
        """切换当前行选中状态"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 简化光标获取逻辑 - 直接使用表格的cursor_row
        current_row_index = getattr(table, 'cursor_row', None)
        
        # 如果cursor_row无效，尝试通过表格的焦点系统获取
        if current_row_index is None:
            try:
                # 尝试获取当前焦点行
                if hasattr(table, 'cursor_coordinate'):
                    coord = table.cursor_coordinate
                    if coord and hasattr(coord, 'row'):
                        current_row_index = coord.row
            except Exception:
                pass
        
        # 执行选择操作
        if current_row_index is not None and 0 <= current_row_index < len(table.rows):
            row_keys = list(table.rows.keys())
            row_key = row_keys[current_row_index]
            # 统一使用 row_key.value 获取书籍路径（与鼠标点击保持一致）
            if hasattr(row_key, 'value') and row_key.value:
                book_id = str(row_key.value)
            else:
                book_id = str(row_key)
            self._toggle_book_selection(book_id, table, current_row_index)
        else:
            # 如果无法确定当前行，显示提示信息
            self.notify("请先选择一行", severity="warning")

    def action_next_page(self) -> None:
        """下一页"""
        self._go_to_next_page()

    def action_prev_page(self) -> None:
        """上一页"""
        self._go_to_prev_page()
    
    def action_jump_to(self) -> None:
        self._show_jump_dialog()

    # 分页导航方法
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self._current_page != 1:
            self._current_page = 1
            self._load_books()
    
    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._load_books()
    
    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_books()
    
    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._load_books()
    
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
                            self._load_books()
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

    def action_cancel(self) -> None:
        """取消返回"""
        self.dismiss({"refresh": False})

    def action_clear_search_params(self) -> None:
        """清除搜索参数"""
        self.query_one("#search-input-field", Input).value = ""
        self.query_one("#search-input-field", Input).placeholder = get_global_i18n().t("bookshelf.search_placeholder")
        self.query_one("#search-author-filter", Select).value = "all"
        self._perform_search()
    
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
        elif event.button.id == "move-up-btn":
            self._move_selected_book_up()
        elif event.button.id == "move-down-btn":
            self._move_selected_book_down()
        elif event.button.id == "merge-btn":
            await self._merge_selected_books()
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
        elif event.button.id == "cancel-btn":
            self.dismiss({"refresh": False})
    
    def _select_all_books(self) -> None:
        """选择当前显示的所有书籍（搜索过滤后的书籍）"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 只选择当前显示的书籍（搜索过滤后的书籍）
        for row_key in table.rows.keys():
            # 从表格行键中获取书籍路径（使用value属性）
            if hasattr(row_key, 'value') and row_key.value:
                book_path = str(row_key.value)
                self.selected_books.add(book_path)
                # 添加到排序列表
                if book_path not in self._sorted_books:
                    self._sorted_books.append(book_path)
        
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
                # 从排序列表中移除
                if book_path in self._sorted_books:
                    self._sorted_books.remove(book_path)
                table.update_cell(row_key, column_key, "□")
            else:
                # 如果未选中，则选中
                self.selected_books.add(book_path)
                # 添加到排序列表
                if book_path not in self._sorted_books:
                    self._sorted_books.append(book_path)
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
            # 从排序列表中移除
            if book_path in self._sorted_books:
                self._sorted_books.remove(book_path)
        
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
        
        # 获取作者筛选
        author_select = self.query_one("#search-author-filter", Select)
        # 规避 NoSelection/None：统一为 "all"
        author_value = getattr(author_select, "value", None)
        try:
            # Textual Select 的 NoSelection 可能没有可比性，转字符串判断
            author_is_valid = isinstance(author_value, str) and author_value != ""
        except Exception:
            author_is_valid = False
        self._selected_author = author_value if author_is_valid else "all"
        
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
        # 注意：不需要强制设置光标到第一行，保持当前光标位置
    
    def _update_table_selection(self) -> None:
        """更新表格中的选中状态显示"""
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 获取列键对象（最后一列，选中状态列）
        if hasattr(table, 'ordered_columns') and len(table.ordered_columns) > 0:
            last_index = len(table.ordered_columns) - 1
            if last_index >= 0:
                column_key = table.ordered_columns[last_index].key
            else:
                return
        elif hasattr(table, 'columns') and len(table.columns) > 0:
            last_index = len(table.columns) - 1
            if last_index >= 0 and hasattr(table.columns[last_index], 'key'):
                column_key = table.columns[last_index].key
            else:
                return
        else:
            # 如果无法获取列键，直接返回
            return
        
        # 更新所有行的选中状态
        for row_index, row_key in enumerate(table.rows.keys()):
            # 从表格行键中获取书籍路径
            book_path = str(row_key)
            
            # 根据选中状态更新显示
            if book_path in self.selected_books:
                try:
                    table.update_cell(row_key, column_key, "✓")
                except Exception:
                    # 如果更新失败，继续处理其他行
                    continue
            else:
                try:
                    table.update_cell(row_key, column_key, "□")
                except Exception:
                    # 如果更新失败，继续处理其他行
                    continue
    
    def _move_selected_book_up(self) -> None:
        """将选中的书籍上移一位，优先使用光标所在行，若无光标则使用第一个选中的书籍"""
        # 1. 验证是否有选中的书籍数据
        if not self.selected_books:
            self.notify(get_global_i18n().t("batch_ops.no_books_selected"), severity="warning")
            return
        
        # 获取当前表格
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 获取当前光标位置
        current_row_index = getattr(table, 'cursor_row', None)
        
        # 初始化书籍路径
        book_path = None
        
        # 如果有光标位置且光标所在行被选中，使用光标所在行
        if current_row_index is not None and current_row_index >= 0 and current_row_index < len(table.rows):
            row_keys = list(table.rows.keys())
            row_key = row_keys[current_row_index]
            # 从行键中提取书籍路径，兼容不同格式的行键
            cursor_book_path = str(row_key)
            if hasattr(row_key, 'value') and row_key.value:
                cursor_book_path = str(row_key.value)
            
            # 如果光标所在行被选中，使用它
            if cursor_book_path in self.selected_books:
                book_path = cursor_book_path
        
        # 如果没有有效的书籍路径（光标行未被选中或无效），使用第一个选中的书籍
        if not book_path:
            # 尝试找到第一个选中的书籍在当前显示列表中的位置
            for path in self.selected_books:
                # 检查该书籍是否在当前显示列表中
                for i, row_key in enumerate(table.rows.keys()):
                    # 从行键中提取书籍路径，兼容不同格式的行键
                    row_key_path = str(row_key)
                    if hasattr(row_key, 'value') and row_key.value:
                        row_key_path = str(row_key.value)
                    
                    if row_key_path == path:
                        current_row_index = i
                        book_path = path
                        break
                if book_path:
                    break
        
        if not book_path:
            self.notify("请先选择书籍或点击一行", severity="warning")
            return
        
        # 2. 获取当前显示的书籍路径（所有搜索结果，不仅仅是当前页）
        all_books = self.bookshelf.get_all_books()
        filtered_books = self._filter_books(all_books)
        current_display_paths = [book.path for book in filtered_books]
        
        # 如果排序列表为空，初始化排序列表为当前显示书籍的顺序
        if not self._sorted_books:
            self._sorted_books = current_display_paths.copy()
        
        # 确保排序列表只包含当前显示的书籍
        filtered_sorted_books = [path for path in self._sorted_books if path in current_display_paths]
        
        # 获取当前光标所在书籍在排序列表中的位置
        if book_path not in filtered_sorted_books:
            # 如果书籍不在排序列表中，添加到末尾
            filtered_sorted_books.append(book_path)
            current_index = len(filtered_sorted_books) - 1
        else:
            current_index = filtered_sorted_books.index(book_path)
        
        # 检查是否能够上移（不在最前面）
        if current_index == 0:
            self.notify(get_global_i18n().t("batch_ops.books_already_at_top"), severity="warning")
            return
        
        # 保存当前选中的书籍路径
        saved_selected_books = self.selected_books.copy()
        
        # 交换当前书籍和上一本书籍的位置
        filtered_sorted_books[current_index], filtered_sorted_books[current_index - 1] = \
            filtered_sorted_books[current_index - 1], filtered_sorted_books[current_index]
        
        # 更新排序列表
        self._sorted_books = filtered_sorted_books
        
        # 重新加载书籍列表以反映排序变化
        self._load_books()
        
        # 恢复选中状态
        self.selected_books = saved_selected_books
        
        # 强制重新渲染表格以确保选中状态正确显示
        self._refresh_table()
        
        # 更新状态信息
        self._update_status()
        
        self.notify(get_global_i18n().t("batch_ops.books_moved_up"), severity="information")
    
    def _move_selected_book_down(self) -> None:
        """将选中的书籍下移一位，优先使用光标所在行，若无光标则使用第一个选中的书籍"""
        # 1. 验证是否有选中的书籍数据
        if not self.selected_books:
            self.notify(get_global_i18n().t("batch_ops.no_books_selected"), severity="warning")
            return
        
        # 获取当前表格
        table = self.query_one("#batch-ops-table", DataTable)
        
        # 获取当前光标位置
        current_row_index = getattr(table, 'cursor_row', None)
        
        # 初始化书籍路径
        book_path = None
        
        # 如果有光标位置且光标所在行被选中，使用光标所在行
        if current_row_index is not None and current_row_index >= 0 and current_row_index < len(table.rows):
            row_keys = list(table.rows.keys())
            row_key = row_keys[current_row_index]
            # 从行键中提取书籍路径，兼容不同格式的行键
            cursor_book_path = str(row_key)
            if hasattr(row_key, 'value') and row_key.value:
                cursor_book_path = str(row_key.value)
            
            # 如果光标所在行被选中，使用它
            if cursor_book_path in self.selected_books:
                book_path = cursor_book_path
        
        # 如果没有有效的书籍路径（光标行未被选中或无效），使用第一个选中的书籍
        if not book_path:
            # 尝试找到第一个选中的书籍在当前显示列表中的位置
            for path in self.selected_books:
                # 检查该书籍是否在当前显示列表中
                for i, row_key in enumerate(table.rows.keys()):
                    # 从行键中提取书籍路径，兼容不同格式的行键
                    row_key_path = str(row_key)
                    if hasattr(row_key, 'value') and row_key.value:
                        row_key_path = str(row_key.value)
                    
                    if row_key_path == path:
                        current_row_index = i
                        book_path = path
                        break
                if book_path:
                    break
        
        if not book_path:
            self.notify("请先选择书籍或点击一行", severity="warning")
            return
        
        # 2. 获取当前显示的书籍路径（所有搜索结果，不仅仅是当前页）
        all_books = self.bookshelf.get_all_books()
        filtered_books = self._filter_books(all_books)
        current_display_paths = [book.path for book in filtered_books]
        
        # 如果排序列表为空，初始化排序列表为当前显示书籍的顺序
        if not self._sorted_books:
            self._sorted_books = current_display_paths.copy()
        
        # 确保排序列表只包含当前显示的书籍
        filtered_sorted_books = [path for path in self._sorted_books if path in current_display_paths]
        
        # 获取当前光标所在书籍在排序列表中的位置
        if book_path not in filtered_sorted_books:
            # 如果书籍不在排序列表中，添加到末尾
            filtered_sorted_books.append(book_path)
            current_index = len(filtered_sorted_books) - 1
        else:
            current_index = filtered_sorted_books.index(book_path)
        
        # 检查是否能够下移（不在最后面）
        if current_index == len(filtered_sorted_books) - 1:
            self.notify(get_global_i18n().t("batch_ops.books_already_at_bottom"), severity="warning")
            return
        
        # 保存当前选中的书籍路径
        saved_selected_books = self.selected_books.copy()
        
        # 交换当前书籍和下一本书籍的位置
        filtered_sorted_books[current_index], filtered_sorted_books[current_index + 1] = \
            filtered_sorted_books[current_index + 1], filtered_sorted_books[current_index]
        
        # 更新排序列表
        self._sorted_books = filtered_sorted_books
        
        # 重新加载书籍列表以反映排序变化
        self._load_books()
        
        # 恢复选中状态
        self.selected_books = saved_selected_books
        
        # 强制重新渲染表格以确保选中状态正确显示
        self._refresh_table()
        
        # 更新状态信息
        self._update_status()
        
        self.notify(get_global_i18n().t("batch_ops.books_moved_down"), severity="information")
    
    async def _merge_selected_books(self) -> None:
        """合并选中的书籍"""
        if not self.selected_books:
            self.notify(get_global_i18n().t("batch_ops.no_books_selected"), severity="warning")
            return
        
        if len(self.selected_books) < 2:
            self.notify(get_global_i18n().t("batch_ops.merge_need_at_least_two"), severity="warning")
            return
        
        # 获取排序后的书籍路径（如果用户进行了排序）
        if self._sorted_books:
            # 只保留选中的书籍并按排序顺序排列
            books_to_merge = [path for path in self._sorted_books if path in self.selected_books]
        else:
            # 如果没有排序，使用原始选中顺序
            books_to_merge = list(self.selected_books)
        
        # 弹出输入对话框获取新书籍标题
        def on_title_input(new_title: Optional[str]) -> None:
            if not new_title or not new_title.strip():
                self.notify(get_global_i18n().t("batch_ops.merge_title_required"), severity="warning")
                return
            
            # 弹出输入对话框获取新书籍作者
            def on_author_input(new_author: Optional[str]) -> None:
                # 弹出输入对话框获取新书籍标签
                def on_tags_input(new_tags: Optional[str]) -> None:
                    # 执行合并操作
                    try:
                        new_book = self.bookshelf.merge_books(
                            books_to_merge,
                            new_title.strip(),
                            new_author.strip() if new_author else "",
                            new_tags.strip() if new_tags else ""
                        )
                        
                        if new_book:
                            self.notify(
                                get_global_i18n().t("batch_ops.merge_success", title=new_title),
                                severity="information"
                            )
                            
                            # 重新加载书籍列表
                            self._load_books()
                            self.selected_books.clear()
                            self._sorted_books.clear()
                            self._clear_table_selection()
                            self._update_status()
                            
                            # 设置返回结果为需要刷新
                            self.dismiss({"refresh": True})
                        else:
                            self.notify(
                                get_global_i18n().t("batch_ops.merge_failed"),
                                severity="error"
                            )
                            
                    except Exception as e:
                        logger.error(f"合并书籍失败: {e}")
                        self.notify(
                            get_global_i18n().t("batch_ops.merge_failed"),
                            severity="error"
                        )
                
                # 弹出标签输入对话框
                self.app.push_screen(
                    BatchInputDialog(
                        get_global_i18n().t("batch_ops.merge_enter_tags"),
                        get_global_i18n().t("batch_ops.merge_tags_placeholder"),
                        get_global_i18n().t("batch_ops.merge_tags_description")
                    ),
                    callback=on_tags_input
                )
            
            # 弹出作者输入对话框
            self.app.push_screen(
                BatchInputDialog(
                    get_global_i18n().t("batch_ops.merge_enter_author"),
                    get_global_i18n().t("batch_ops.merge_author_placeholder"),
                    get_global_i18n().t("batch_ops.merge_author_description")
                ),
                callback=on_author_input
            )
        
        # 弹出标题输入对话框
        self.app.push_screen(
            BatchInputDialog(
                get_global_i18n().t("batch_ops.merge_enter_title"),
                get_global_i18n().t("batch_ops.merge_title_placeholder"),
                get_global_i18n().t("batch_ops.merge_description")
            ),
            callback=on_title_input
        )

