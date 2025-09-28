"""
书架屏幕
"""


from typing import Dict, Any, Optional, List, ClassVar, Set
from webbrowser import get
from src.core.book import Book
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid, VerticalScroll
from textual.widgets import Static, Button, Label, DataTable
from textual.reactive import reactive
from textual import on
from textual import events

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.core.book_manager import BookManager
from src.core.statistics_direct import StatisticsManagerDirect
from src.ui.dialogs.batch_ops_dialog import BatchOpsDialog
from src.ui.dialogs.search_dialog import SearchDialog
from src.ui.dialogs.sort_dialog import SortDialog
from src.ui.dialogs.directory_dialog import DirectoryDialog
from src.ui.dialogs.file_chooser_dialog import FileChooserDialog
from src.ui.dialogs.scan_progress_dialog import ScanProgressDialog
from src.ui.messages import RefreshBookshelfMessage

from src.utils.logger import get_logger

logger = get_logger(__name__)

class BookshelfScreen(Screen[None]):
    """书架屏幕"""
    
    TITLE: ClassVar[Optional[str]] = None  # 在运行时设置
    CSS_PATH="../styles/bookshelf.css"
    
    @on(RefreshBookshelfMessage)
    def handle_refresh_message(self, message: RefreshBookshelfMessage) -> None:
        """处理刷新书架消息"""
        self._load_books()
    
    def __init__(self, theme_manager: ThemeManager, bookshelf: Bookshelf, statistics_manager: StatisticsManagerDirect):
        """
        初始化书架屏幕
        
        Args:
            theme_manager: 主题管理器
            bookshelf: 书架
            statistics_manager: 统计管理器
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        self.statistics_manager = statistics_manager
        self.book_manager = BookManager(bookshelf)
        self.title = get_global_i18n().t("bookshelf.title")
        # 设置类的TITLE属性
        self.__class__.TITLE = self.title
        self.logger = get_logger(__name__)
        
        # 初始化序号到书籍路径的映射
        self._book_index_mapping: Dict[str, str] = {}
        
        # 分页相关属性
        self._current_page = 1
        self._books_per_page = 20
        self._total_pages = 1
        self._all_books: List[Book] = []
        
        # 初始化数据表列
        self.columns = [
            ("ID", "id"),
            (get_global_i18n().t("bookshelf.title"), "title"),
            (get_global_i18n().t("bookshelf.author"), "author"),
            (get_global_i18n().t("bookshelf.format"), "format"),
            (get_global_i18n().t("bookshelf.last_read"), "last_read"),
            (get_global_i18n().t("bookshelf.progress"), "progress"),
            (get_global_i18n().t("bookshelf.tags"), "tags"),
            (get_global_i18n().t("bookshelf.actions"), "actions"),  # 添加操作列
        ]
    
    def compose(self) -> ComposeResult:
        """
        组合书架屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Grid(
                # 顶部标题和工具栏
                Vertical(
                    Label(get_global_i18n().t("bookshelf.library"), id="bookshelf-title"),
                    Horizontal(
                        Button(get_global_i18n().t("bookshelf.search"), id="search-btn"),
                        Button(get_global_i18n().t("bookshelf.sort.title"), id="sort-btn"),
                        Button(get_global_i18n().t("bookshelf.batch_ops.title"), id="batch-ops-btn"),
                        Button(get_global_i18n().t("bookshelf.refresh"), id="refresh-btn"),
                        id="bookshelf-toolbar"
                    ),
                    id="bookshelf-header"
                ),
                # 中间数据表区域
                DataTable(id="books-table"),
                # 书籍统计信息区域
                Vertical(
                    Label("", id="books-stats-label"),
                    id="books-stats-area"
                ),
                # 底部控制栏和状态栏
                Vertical(
                    Horizontal(
                        Button(get_global_i18n().t("bookshelf.add_book"), id="add-book-btn"),
                        Button(get_global_i18n().t("bookshelf.scan_directory"), id="scan-directory-btn"),
                        Button(get_global_i18n().t("bookshelf.get_books"), id="get-books-btn"),
                        Button(get_global_i18n().t("bookshelf.back"), id="back-btn"),
                        id="bookshelf-controls"
                    ),
                    # 快捷键状态栏
                    Horizontal(
                        Label(f"↑↓: {get_global_i18n().t('bookshelf.choose_book')}", id="shortcut-arrows"),
                        Label(f"Enter: {get_global_i18n().t('bookshelf.open_book')}", id="shortcut-enter"),
                        Label(f"S: {get_global_i18n().t('bookshelf.search')}", id="shortcut-s"),
                        Label(f"R: {get_global_i18n().t('bookshelf.sort_name')}", id="shortcut-r"),
                        Label(f"L: {get_global_i18n().t('bookshelf.batch_ops_name')}", id="shortcut-l"),
                        Label(f"A: {get_global_i18n().t('bookshelf.add_book')}", id="shortcut-a"),
                        Label(f"D: {get_global_i18n().t('bookshelf.scan_directory')}", id="shortcut-d"),
                        Label(f"F: {get_global_i18n().t('bookshelf.refresh')}", id="shortcut-f"),
                        Label(f"P: {get_global_i18n().t('bookshelf.prev_page')}", id="shortcut-p"),
                        Label(f"N: {get_global_i18n().t('bookshelf.next_page')}", id="shortcut-n"),
                        Label(f"ESC: {get_global_i18n().t('bookshelf.back')}", id="shortcut-esc"),
                        id="shortcuts-bar",
                        classes="footer"
                    ),
                    id="bookshelf-footer"
                ),
                id="bookshelf-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 设置Grid布局的行高分配 - 使用百分比确保底部显示
        grid = self.query_one("Grid")
        grid.styles.grid_size_rows = 4
        grid.styles.grid_size_columns = 1
        grid.styles.grid_rows = ("15%", "60%", "10%", "20%")
        
        # 初始化数据表
        table = self.query_one("#books-table", DataTable)
        for col in self.columns:
            table.add_column(col[0], key=col[1])
        
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        # 加载书籍数据
        self._load_books()
        
        # 设置数据表焦点，使其能够接收键盘事件
        table = self.query_one("#books-table", DataTable)
        table.focus()
    
    def _load_books(self) -> None:
        """加载书籍数据"""
        # 显示加载动画
        self._show_loading_animation(f"{get_global_i18n().t('book_on_loadding')}")
        
        table = self.query_one("#books-table", DataTable)
        table.clear()
        
        # 默认按照最后阅读时间倒序排序
        self._all_books = self.bookshelf.sort_books("last_read_date", reverse=True)
        
        # 计算总页数
        self._total_pages = max(1, (len(self._all_books) + self._books_per_page - 1) // self._books_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 获取当前页的书籍
        start_index = (self._current_page - 1) * self._books_per_page
        end_index = min(start_index + self._books_per_page, len(self._all_books))
        current_page_books = self._all_books[start_index:end_index]
        
        # 创建序号到书籍路径的映射
        self._book_index_mapping = {}
        
        for index, book in enumerate(current_page_books, start_index + 1):
            # 存储序号到路径的映射
            self._book_index_mapping[str(index)] = book.path
            
            # 直接使用Book对象的属性，而不是Statistics类的方法
            last_read = book.last_read_date or ""
            progress = book.reading_progress * 100  # 转换为百分比
            
            # 格式化标签显示（逗号分隔）
            tags_display = ", ".join(book.tags) if book.tags else ""
            
            # 添加阅读按钮
            read_button = f"[{get_global_i18n().t('bookshelf.read')}]"
            
            table.add_row(
                str(index),  # 显示数字序号而不是路径
                book.title,
                book.author,
                book.format.upper(),
                last_read,
                f"{progress:.1f}%",
                tags_display,
                read_button,  # 阅读按钮
                key=book.path  # 仍然使用路径作为行键
            )
        
        # 更新书籍统计信息
        self._update_books_stats(self._all_books)
        
        # 更新分页信息显示
        self._update_pagination_info()
        
        # 隐藏加载动画
        self._hide_loading_animation()
    
    def _update_books_stats(self, books: List[Book]) -> None:
        """更新书籍统计信息"""
        try:
            # 统计总数和各格式数量
            total_count = len(books)
            format_counts = {}
            
            for book in books:
                format_name = book.format.upper()
                format_counts[format_name] = format_counts.get(format_name, 0) + 1
            
            # 构建统计信息文本
            stats_text = get_global_i18n().t("bookshelf.total_books", count=total_count)
            
            if format_counts:
                format_parts = []
                for format_name, count in sorted(format_counts.items()):
                    format_parts.append(f"{format_name}: {count}{get_global_i18n().t('bookshelf.books')}")
                
                if format_parts:
                    stats_text += " (" + ", ".join(format_parts) + ")"
            
            # 更新显示
            stats_label = self.query_one("#books-stats-label", Label)
            stats_label.update(stats_text)
            
        except Exception as e:
            logger.error(get_global_i18n().t('update_stats_failed', error=str(e)))
    
    def _update_pagination_info(self) -> None:
        """更新分页信息显示"""
        try:
            # 更新分页信息到统计标签
            stats_label = self.query_one("#books-stats-label", Label)
            # 获取当前显示的文本内容
            current_text = ""
            try:
                # 尝试获取renderable的字符串表示
                current_text = str(stats_label.renderable)
            except:
                # 如果失败，使用空字符串
                current_text = ""
            
            # 移除可能存在的旧分页信息
            if "| 第" in current_text:
                current_text = current_text.split("| 第")[0].strip()
            
            # 添加分页信息
            pagination_info = f" | 第 {self._current_page}/{self._total_pages} 页"
            stats_label.update(current_text + pagination_info)
            
        except Exception as e:
            logger.error(f"更新分页信息失败: {e}")
    
    def _refresh_bookshelf(self) -> None:
        """刷新书架内容"""
        self.logger.info("刷新书架内容")
        # 重置到第一页
        self._current_page = 1
        # 重新加载书籍数据
        self._load_books()
        # 显示刷新成功的提示
        self.notify(get_global_i18n().t("bookshelf.refresh_success"))

    def _get_books(self) -> None:
        """获取书籍列表"""
        self.logger.info("获取书籍列表")
        # 获取书籍列表
        self.app.push_screen("get_books")  # 打开获取书籍页面
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "add-book-btn":
            self._show_add_book_dialog()
        elif event.button.id == "scan-directory-btn":
            self._show_scan_directory_dialog()
        elif event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "search-btn":
            self._show_search_dialog()
        elif event.button.id == "sort-btn":
            self._show_sort_menu()
        elif event.button.id == "batch-ops-btn":
            self._show_batch_ops_menu()
        elif event.button.id == "refresh-btn":
            self._refresh_bookshelf()
        elif event.button.id == "get-books-btn":
            self._get_books()
    
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
        
        # 如果是操作列的阅读按钮被点击
        if cell_key.column_key.value == "actions" and cell_value == f"[{get_global_i18n().t('bookshelf.read')}]":
            book_id = cell_key.row_key.value
            self.logger.info(f"点击阅读按钮打开书籍: {book_id}")
            # 类型安全的open_book调用
            app_instance = self.app
            if hasattr(app_instance, 'open_book'):
                app_instance.open_book(book_id)  # type: ignore
            else:
                # 如果app没有open_book方法，尝试其他方式打开书籍
                if book_id:
                    self._open_book_fallback(book_id)
                else:
                    self.logger.error("书籍ID为空，无法打开书籍")
    
    def _open_book_fallback(self, book_path: str) -> None:
        """备用方法打开书籍"""
        try:
            # 从书架中获取书籍对象
            book = self.bookshelf.get_book(book_path)
            if book:
                # 创建阅读器屏幕并推入
                from src.ui.screens.reader_screen import ReaderScreen
                from src.core.bookmark import BookmarkManager
                
                bookmark_manager = BookmarkManager()
                reader_screen = ReaderScreen(
                    book=book,
                    theme_manager=self.theme_manager,
                    statistics_manager=self.statistics_manager,
                    bookmark_manager=bookmark_manager,
                    bookshelf=self.bookshelf
                )
                self.app.push_screen(reader_screen)
            else:
                self.logger.error(f"未找到书籍: {book_path}")
                self.notify(f"未找到书籍: {book_path}", severity="error")
        except Exception as e:
            self.logger.error(f"打开书籍失败: {e}")
            self.notify(f"打开书籍失败: {e}", severity="error")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        数据表行选择时的回调
        
        Args:
            event: 行选择事件
        """
        book_id = event.row_key.value
        self.logger.info(f"选择书籍: {book_id}")
        # 类型安全的open_book调用
        app_instance = self.app
        if hasattr(app_instance, 'open_book'):
            app_instance.open_book(book_id)  # type: ignore
        
    def on_key(self, event: events.Key) -> None:
        """
        键盘事件处理
        
        Args:
            event: 键盘事件
        """
        table = self.query_one("#books-table", DataTable)
        
        if event.key == "enter":
            # 获取当前选中的行
            if table.cursor_row is not None:
                # 获取选中行的键（书籍路径）
                row_key = list(table.rows.keys())[table.cursor_row]
                if row_key and row_key.value:
                    book_id = row_key.value  # 使用行键（书籍路径）而不是第一列数据
                    self.logger.info(get_global_i18n().t('bookshelf.press_enter_open_book', book_id=book_id))
                    # 类型安全的open_book调用
                    app_instance = self.app
                    if hasattr(app_instance, 'open_book'):
                        app_instance.open_book(book_id)
                    event.prevent_default()
        elif event.key == "s":
            # S键搜索
            self._show_search_dialog()
            event.prevent_default()
        elif event.key == "r":
            # R键排序
            self._show_sort_menu()
            event.prevent_default()
        elif event.key == "l":
            self._show_batch_ops_menu()
            event.prevent_default()
        elif event.key == "a":
            self._show_add_book_dialog()
            event.prevent_default()
        elif event.key == "d":
            self._show_scan_directory_dialog()
            event.prevent_default()
        elif event.key == "f":
            # F键刷新书架
            self._refresh_bookshelf()
            event.prevent_default()
        elif event.key == "escape":
            # ESC键返回
            self.app.pop_screen()
            event.prevent_default()
        elif event.key == "n":
            # N键下一页
            if self._current_page < self._total_pages:
                self._current_page += 1
                self._load_books()
            event.prevent_default()
        elif event.key == "p":
            # P键上一页
            if self._current_page > 1:
                self._current_page -= 1
                self._load_books()
            event.prevent_default()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            if (table.cursor_row == len(table.rows) - 1 and 
                self._current_page < self._total_pages):
                self._current_page += 1
                self._load_books()
                # 将光标移动到新页面的第一行
                table = self.query_one("#books-table", DataTable)
                table.action_cursor_down()  # 先向下移动一次
                table.action_cursor_up()     # 再向上移动一次，确保在第一行
                event.prevent_default()
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            if table.cursor_row == 0 and self._current_page > 1:
                self._current_page -= 1
                self._load_books()
                # 将光标移动到新页面的最后一行
                table = self.query_one("#books-table", DataTable)
                for _ in range(len(table.rows) - 1):
                    table.action_cursor_down()  # 移动到最底部
                event.prevent_default()
        elif event.key in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            # 数字键1-9：打开对应序号的书籍
            book_index = event.key
            if book_index in self._book_index_mapping:
                book_path = self._book_index_mapping[book_index]
                self.logger.info(f"按数字键 {book_index} 打开书籍: {book_path}")
                # 直接调用open_book方法
                app_instance = self.app
                if hasattr(app_instance, 'open_book'):
                    app_instance.open_book(book_path)  # type: ignore
                event.prevent_default()
            else:
                # 如果该序号没有对应的书籍，显示提示
                self.notify(
                    f"第 {book_index} 个位置没有书籍",
                    severity="warning"
                )
                event.prevent_default()
        # 其他按键让父类处理
        
    def _show_search_dialog(self) -> None:
        """显示搜索对话框"""
        def handle_search_result(result: Any) -> None:
            """处理搜索结果"""
            if result:
                # 搜索对话框返回的是SearchResult对象，直接打开对应的书籍
                from src.core.search import SearchResult
                if isinstance(result, SearchResult):
                    app_instance = self.app
                    if hasattr(app_instance, 'open_book'):
                        app_instance.open_book(result.book_id)
        
        # 使用现有的搜索对话框
        from src.ui.dialogs.search_dialog import SearchDialog
        dialog = SearchDialog(self.theme_manager)
        self.app.push_screen(dialog, handle_search_result)
        
    def _show_sort_menu(self) -> None:
        """显示排序菜单"""
        def handle_sort_result(result: Optional[Dict[str, Any]]) -> None:
            """处理排序结果"""
            if result:
                # 使用bookshelf的排序功能
                sorted_books = self.bookshelf.sort_books(
                    result["sort_key"], 
                    result["reverse"]
                )
                
                # 更新表格显示排序后的书籍
                table = self.query_one("#books-table", DataTable)
                table.clear()
                
                # 更新序号到书籍路径的映射
                self._book_index_mapping = {}
                
                for index, book in enumerate(sorted_books, 1):
                    # 存储序号到路径的映射
                    self._book_index_mapping[str(index)] = book.path
                    
                    last_read = book.last_read_date or ""
                    progress = book.reading_progress * 100  # 转换为百分比
                    
                    table.add_row(
                        str(index),  # 显示数字序号而不是路径
                        book.title,
                        book.author,
                        book.format.upper(),
                        last_read,
                        f"{progress:.1f}%",
                        key=book.path  # 仍然使用路径作为行键
                    )
                
                # 将字段名映射到翻译文本
                sort_key_translations = {
                    "title": get_global_i18n().t("bookshelf.title"),
                    "author": get_global_i18n().t("bookshelf.author"),
                    "add_date": get_global_i18n().t("bookshelf.add_date"),
                    "last_read_date": get_global_i18n().t("bookshelf.last_read"),
                    "progress": get_global_i18n().t("bookshelf.progress")
                }
                
                # 将排序顺序映射到翻译文本
                order_translations = {
                    False: get_global_i18n().t("sort.ascending"),
                    True: get_global_i18n().t("sort.descending")
                }
                
                translated_sort_key = sort_key_translations.get(
                    result["sort_key"], result["sort_key"]
                )
                translated_order = order_translations.get(
                    result["reverse"], result["reverse"]
                )
                
                self.notify(
                    get_global_i18n().t("sort.applied", sort_key=translated_sort_key, order=translated_order),
                    severity="information"
                )
        
        # 显示排序对话框
        dialog = SortDialog(self.theme_manager)
        self.app.push_screen(dialog, handle_sort_result)
        
    def _show_batch_ops_menu(self) -> None:
        """显示批量操作菜单"""
        def handle_batch_ops(result: Optional[Dict[str, Any]]) -> None:
            """处理批量操作结果"""
            if result and result.get("refresh"):
                # 重新加载书籍数据
                self._load_books()
                self.notify(
                    get_global_i18n().t("batch_ops.operation_completed"),
                    severity="information"
                )
        
        # 显示批量操作对话框
        dialog = BatchOpsDialog(self.theme_manager, self.bookshelf)
        self.app.push_screen(dialog, handle_batch_ops)
        
    def _show_add_book_dialog(self) -> None:
        """显示添加书籍对话框"""
        def handle_add_book_result(result: Optional[List[str]]) -> None:
            """处理添加书籍结果"""
            if result:
                # 显示加载动画
                self._show_loading_animation(get_global_i18n().t("bookshelf.adding_books"))
                
                added_count = 0
                for file_path in result:
                    try:
                        book = self.bookshelf.add_book(file_path)
                        if book:
                            added_count += 1
                    except Exception as e:
                        logger.error(f"{get_global_i18n().t('bookshelf.add_book_failed')}: {e}")
                
                # 隐藏加载动画
                self._hide_loading_animation()
                
                if added_count > 0:
                    self.notify(
                        get_global_i18n().t("bookshelf.book_added", count=added_count),
                        severity="information"
                    )
                    self._load_books()
        
        # 显示文件选择器对话框
        dialog = FileChooserDialog(
            self.theme_manager,
            get_global_i18n().t("bookshelf.add_single_book"),
            get_global_i18n().t("bookshelf.file_path"),
            multiple=True
        )
        self.app.push_screen(dialog, handle_add_book_result)
        
    def _show_scan_directory_dialog(self) -> None:
        """显示扫描目录对话框"""
        def handle_directory_result(result: Optional[str]) -> None:
            """处理目录选择结果"""
            if result:
                # 显示扫描进度对话框
                def handle_scan_result(scan_result: Optional[Dict[str, Any]]) -> None:
                    """处理扫描结果"""
                    if scan_result and scan_result.get("success"):
                        added_count = scan_result.get("added_count", 0)
                        if added_count > 0:
                            self.notify(
                                get_global_i18n().t("bookshelf.scan_success", count=added_count),
                                severity="information"
                            )
                            self._load_books()
                        else:
                            self.notify(
                                get_global_i18n().t("bookshelf.no_books_found"),
                                severity="warning"
                            )
                
                scan_dialog = ScanProgressDialog(
                    self.theme_manager,
                    self.book_manager,
                    result
                )
                self.app.push_screen(scan_dialog, handle_scan_result)
        
        # 显示目录选择对话框
        dialog = DirectoryDialog(
            self.theme_manager
        )
        self.app.push_screen(dialog, handle_directory_result)
    
    def _show_loading_animation(self, message: Optional[str] = None) -> None:
        """显示加载动画"""
        if message is None:
            message = get_global_i18n().t("common.on_action")
        try:
            # 优先使用Textual集成的加载动画
            from src.ui.components.textual_loading_animation import textual_animation_manager
            
            if textual_animation_manager.show_default(message):
                logger.debug(f"{get_global_i18n().t('common.show_loading_animation')}: {message}")
                return
            
            # 回退到原有的加载动画组件
            from src.ui.components.loading_animation import animation_manager
            animation_manager.show_default(message)
            logger.debug(f"{get_global_i18n().t('common.show_classicle_animation')}: {message}")
            
        except ImportError:
            logger.warning(get_global_i18n().t("common.abort_animation"))
        except Exception as e:
            logger.error(f"{get_global_i18n().t('common.animation_failed')}: {e}")
    
    def _hide_loading_animation(self) -> None:
        """隐藏加载动画"""
        try:
            # 优先使用Textual集成的加载动画
            from src.ui.components.textual_loading_animation import textual_animation_manager
            
            if textual_animation_manager.hide_default():
                logger.debug(get_global_i18n().t("common.hide_animation"))
                return
            
            # 回退到原有的加载动画组件
            from src.ui.components.loading_animation import animation_manager
            animation_manager.hide_default()
            logger.debug(get_global_i18n().t("common.hide_classicle_animation"))
            
        except ImportError:
            logger.warning(get_global_i18n().t("common.abort_hide_animation"))
        except Exception as e:
            logger.error(f"{get_global_i18n().t("common.hide_failed")}: {e}")