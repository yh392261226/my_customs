"""
书架屏幕
"""


from typing import Dict, Any, Optional, List, ClassVar, Set
from webbrowser import get
from src.core import book
from src.core.book import Book
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid, VerticalScroll
from textual.widgets import Static, Button, Label, DataTable, Header, Footer, LoadingIndicator, Input, Select
from textual.reactive import reactive
from textual import on, events

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.core.book_manager import BookManager
from src.core.statistics_direct import StatisticsManagerDirect
from src.core.database_manager import DatabaseManager
from src.ui.dialogs.batch_ops_dialog import BatchOpsDialog
from src.ui.dialogs.search_dialog import SearchDialog
from src.ui.dialogs.sort_dialog import SortDialog
from src.ui.dialogs.directory_dialog import DirectoryDialog
from src.ui.dialogs.file_chooser_dialog import FileChooserDialog
from src.ui.dialogs.scan_progress_dialog import ScanProgressDialog
from src.ui.messages import RefreshBookshelfMessage
from src.ui.styles.style_manager import apply_style_isolation
from src.config.default_config import SUPPORTED_FORMATS
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BookshelfScreen(Screen[None]):
    """书架屏幕"""
    
    TITLE: ClassVar[Optional[str]] = None  # 在运行时设置
    CSS_PATH="../styles/bookshelf_overrides.tcss"
    # 使用 Textual BINDINGS 进行快捷键绑定（不移除 on_key，逐步过渡）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("a", "press('#add-book-btn')", get_global_i18n().t('common.add')),
        ("d", "press('#scan-directory-btn')", get_global_i18n().t('bookshelf.scan_directory')),
        ("s", "press('#search-btn')", get_global_i18n().t('common.search')),
        ("r", "press('#sort-btn')", get_global_i18n().t('bookshelf.sort_name')),
        ("l", "press('#batch-ops-btn')", get_global_i18n().t('bookshelf.batch_ops_name')),
        ("g", "press('#get-books-btn')", get_global_i18n().t('bookshelf.get_books')),
        ("f", "press('#refresh-btn')", get_global_i18n().t('bookshelf.refresh')),
        ("x", "clear_search_params", get_global_i18n().t('bookshelf.clear_search_params')),
    ]
    # 支持的书籍文件扩展名（从配置文件读取）
    SUPPORTED_EXTENSIONS = set(SUPPORTED_FORMATS)
    
    @on(RefreshBookshelfMessage)
    def handle_refresh_message(self, message: RefreshBookshelfMessage) -> None:
        """处理刷新书架消息"""
        self.logger.info("接收到书架刷新消息，正在重新加载书籍数据...")
        # 强制重新加载书架数据，确保数据同步
        try:
            # 重新加载书架数据（从数据库重新获取）
            self.bookshelf._load_books()
            self.logger.info("书架数据已重新加载")
        except Exception as e:
            self.logger.warning(f"重新加载书架数据失败: {e}")
        
        self._load_books()
        self.logger.info("书架数据已刷新")
    
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
        # 初始化行键到书籍路径的映射
        self._row_key_mapping: Dict[str, str] = {}
        
        # 分页相关属性
        self._current_page = 1
        self._books_per_page = 20
        self._total_pages = 1
        self._all_books: List[Book] = []
        
        # 表格初始化状态
        self._table_initialized = False
        
        # 初始化数据表列
        self.columns = [
            ("ID", "id"),
            (get_global_i18n().t("bookshelf.title"), "title"),
            (get_global_i18n().t("bookshelf.author"), "author"),
            (get_global_i18n().t("bookshelf.format"), "format"),
            (get_global_i18n().t("bookshelf.size"), "size"),  # 新增文件大小列
            (get_global_i18n().t("bookshelf.last_read"), "last_read"),
            (get_global_i18n().t("bookshelf.progress"), "progress"),
            (get_global_i18n().t("bookshelf.tags"), "tags"),
            (get_global_i18n().t("bookshelf.read"), "read_action"),  # 阅读按钮列
            (get_global_i18n().t("bookshelf.view_file"), "view_action"),  # 查看文件按钮列
            (get_global_i18n().t("bookshelf.rename"), "rename_action"),  # 重命名按钮列
            (get_global_i18n().t("bookshelf.delete"), "delete_action"),  # 删除按钮列
        ]
        
        # 初始化搜索状态变量
        self._search_keyword = ""
        self._search_format = "all"
        self._search_author = "all"
        
        # 初始化加载指示器变量
        self.loading_indicator = None
        
        # 作者列表缓存（性能优化）
        self._author_options_cache = None
        self._author_options_loaded = False
    

    
    def compose(self) -> ComposeResult:
        """
        组合书架屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
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
            Grid(
                # 顶部标题和工具栏
                Vertical(
                    # Label(get_global_i18n().t("bookshelf.library"), id="bookshelf-title", classes="section-title"),
                    Horizontal(
                        Button(get_global_i18n().t("bookshelf.add_book"), id="add-book-btn", classes="btn"),
                        Button(get_global_i18n().t("bookshelf.scan_directory"), id="scan-directory-btn", classes="btn"),
                        Button(get_global_i18n().t("bookshelf.search"), id="search-btn", classes="btn"),
                        Button(get_global_i18n().t("bookshelf.sort.title"), id="sort-btn", classes="btn"),
                        Button(get_global_i18n().t("bookshelf.batch_ops.title"), id="batch-ops-btn", classes="btn"),
                        Button(get_global_i18n().t("bookshelf.get_books"), id="get-books-btn", classes="btn"),
                        Button(get_global_i18n().t("bookshelf.refresh"), id="refresh-btn", classes="btn"),
                        Button(get_global_i18n().t("bookshelf.back"), id="back-btn", classes="btn"),
                        id="bookshelf-toolbar",
                        classes="btn-row"
                    ),
                    # 搜索栏
                    Horizontal(
                        Input(
                            placeholder=get_global_i18n().t("search.placeholder"), 
                            id="bookshelf-search-input", 
                            classes="bookshelf-search-input"
                        ),
                        Select(
                            id="bookshelf-format-filter",
                            options=search_options, 
                            value="all",
                            prompt=get_global_i18n().t("common.select_ext_prompt"),
                            classes="bookshelf-search-select"
                        ),
                        Select(
                            id="bookshelf-source-filter",
                            options=author_options,
                            value="all",
                            prompt=get_global_i18n().t("bookshelf.select_source"),
                            classes="bookshelf-source-select"
                        ),
                        id="bookshelf-search-bar",
                        classes="bookshelf-search-bar"
                    ),
                    id="bookshelf-header",
                    classes="bookshelf-header-vertical"
                ),
                # 中间数据表区域
                DataTable(id="books-table"),
                # 书籍统计信息区域
                Vertical(
                    Label("", id="books-stats-label"),
                    id="books-stats-area"
                ),
                # 底部状态栏（简化版本）
                # Horizontal(
                #     Label(f"↑↓: {get_global_i18n().t('bookshelf.choose_book')}", id="shortcut-arrows"),
                #     Label(f"Enter: {get_global_i18n().t('bookshelf.open_book')}", id="shortcut-enter"),
                #     Label(f"S: {get_global_i18n().t('bookshelf.search')}", id="shortcut-s"),
                #     Label(f"R: {get_global_i18n().t('bookshelf.sort_name')}", id="shortcut-r"),
                #     Label(f"L: {get_global_i18n().t('bookshelf.batch_ops_name')}", id="shortcut-l"),
                #     Label(f"A: {get_global_i18n().t('bookshelf.add_book')}", id="shortcut-a"),
                #     Label(f"D: {get_global_i18n().t('bookshelf.scan_directory')}", id="shortcut-d"),
                #     Label(f"G: {get_global_i18n().t('get_books.title')}", id="shortcut-g"),
                #     Label(f"F: {get_global_i18n().t('bookshelf.refresh')}", id="shortcut-f"),
                #     Label(f"P: {get_global_i18n().t('bookshelf.prev_page')}", id="shortcut-p"),
                #     Label(f"N: {get_global_i18n().t('bookshelf.next_page')}", id="shortcut-n"),
                #     Label(f"ESC: {get_global_i18n().t('bookshelf.back')}", id="shortcut-esc"),
                #     id="shortcuts-bar",
                #     classes="footer status-bar"
                # ),
                # id="bookshelf-container"
            ),
            id="bookshelf-screen",
            classes="bookshelf-screen"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        apply_style_isolation(self)
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 设置Grid布局的行高分配 - 与CSS保持一致
        grid = self.query_one("Grid")
        grid.styles.grid_size_rows = 3
        grid.styles.grid_size_columns = 1
        grid.styles.grid_rows = ("25%", "65%", "10%")
        
        # 原生 LoadingIndicator（初始隐藏），挂载到书籍统计区域
        try:
            self.loading_indicator = LoadingIndicator(id="bookshelf-loading-indicator")
            self.loading_indicator.display = False
            loading_area = self.query_one("#books-stats-area")
            loading_area.mount(self.loading_indicator)
        except Exception:
            pass
        
        # 初始化数据表（只在未初始化时添加列）
        table = self.query_one("#books-table", DataTable)
        if not self._table_initialized:
            # 根据权限过滤操作列
            can_read = getattr(self.app, "has_permission", lambda k: True)("bookshelf.read")
            can_view = getattr(self.app, "has_permission", lambda k: True)("bookshelf.view_file")
            can_delete = getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book")
            cols = []
            for label, key in self.columns:
                if key == "read_action" and not can_read:
                    continue
                if key == "view_action" and not can_view:
                    continue
                if key == "delete_action" and not can_delete:
                    continue
                cols.append((label, key))
            for col in cols:
                table.add_column(col[0], key=col[1])
            
            # 启用隔行变色效果
            table.zebra_stripes = True
            
            # 标记表格已初始化
            self._table_initialized = True

        # 按权限禁用/隐藏按钮
        try:
            self._apply_permissions()
        except Exception:
            pass
        
        # 多用户模式检查：确保书架管理器设置正确的用户
        try:
            current_user = getattr(self.app, 'current_user', None)
            config_manager = getattr(self.app, 'config_manager', None)
            
            # 检查是否启用多用户模式
            multi_user_enabled = False
            if config_manager:
                config = config_manager.get_config()
                multi_user_enabled = config.get('advanced', {}).get('multi_user_enabled', False)
            
            if multi_user_enabled:
                # 多用户模式：必须设置当前用户
                if current_user:
                    user_id = current_user.get('id')
                    user_role = current_user.get('role', 'user')
                    self.bookshelf.set_current_user(user_id, user_role)
                    self.logger.debug(f"多用户模式：设置用户 ID={user_id}, 角色={user_role}")
                else:
                    # 多用户模式下必须有用户，否则清空数据
                    self.bookshelf.set_current_user(None, "user")
                    self.logger.warning("多用户模式：未找到当前用户，已清空用户设置")
            else:
                # 单用户模式：使用默认用户或无用户
                if current_user:
                    # 如果有用户信息，也设置（兼容性）
                    user_id = current_user.get('id')
                    user_role = current_user.get('role', 'user')
                    self.bookshelf.set_current_user(user_id, user_role)
                    self.logger.debug(f"单用户模式：设置用户 ID={user_id}")
                else:
                    # 单用户模式无用户时使用默认设置
                    self.bookshelf.set_current_user(None, "user")
                    self.logger.debug("单用户模式：使用默认设置")
            
            # 初始化用户ID缓存
            self._last_user_id = current_user.get('id') if current_user else None
            
        except Exception as e:
            self.logger.warning(f"设置书架管理器用户失败: {e}")
        
        # 加载书籍数据
        self._load_books()
        
        # 设置数据表焦点，使其能够接收键盘事件
        table = self.query_one("#books-table", DataTable)
        table.focus()
    
    def _add_table_columns(self, table) -> None:
        """添加表格列定义"""
        # 根据权限过滤操作列
        can_read = getattr(self.app, "has_permission", lambda k: True)("bookshelf.read")
        can_view = getattr(self.app, "has_permission", lambda k: True)("bookshelf.view_file")
        can_delete = getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book")
        
        cols = []
        for label, key in self.columns:
            if key == "read_action" and not can_read:
                continue
            if key == "view_action" and not can_view:
                continue
            if key == "delete_action" and not can_delete:
                continue
            cols.append((label, key))
        
        for col in cols:
            table.add_column(col[0], key=col[1])
        
        # 启用隔行变色效果
        table.zebra_stripes = True
    
    def _load_books(self, search_keyword: str = "", search_format: str = "all", search_author: str = "all") -> None:
        """加载书籍数据
        
        Args:
            search_keyword: 搜索关键词
            search_format: 文件格式筛选
            search_author: 作者筛选
        """
        # 显示加载动画
        self._show_loading_animation(f"{get_global_i18n().t('book_on_loadding')}")
        
        table = self.query_one("#books-table", DataTable)
        
        # 性能优化：检查是否只需要更新当前页数据（分页切换时）
        current_search_params = f"{search_keyword}_{search_format}_{search_author}"
        page_change_only = False
        
        # 如果搜索条件未改变且书籍数据已存在，只需更新分页
        if (hasattr(self, '_last_search_params') and 
            self._last_search_params == current_search_params and 
            hasattr(self, '_all_books') and self._all_books):
            page_change_only = True
        
        if not page_change_only:
            # 完全清除表格数据，包括行键缓存
            table.clear(columns=True)
            # 重新添加列定义（因为columns=True会清除列）
            self._add_table_columns(table)
            
            # 性能优化：避免不必要的数据库重新加载
            # 只在真正需要刷新数据时重新加载书架
            force_reload = False
            if not hasattr(self, '_last_search_params') or self._last_search_params != current_search_params:
                force_reload = True
            
            try:
                # 多用户模式检查：确保用户权限和数据隔离
                current_user = getattr(self.app, 'current_user', None)
                config_manager = getattr(self.app, 'config_manager', None)
                
                # 检查是否启用多用户模式
                multi_user_enabled = False
                if config_manager:
                    config = config_manager.get_config()
                    multi_user_enabled = config.get('advanced', {}).get('multi_user_enabled', False)
                
                if multi_user_enabled:
                    # 多用户模式：必须设置当前用户
                    if current_user:
                        user_id = current_user.get('id')
                        user_role = current_user.get('role', 'user')
                        self.bookshelf.set_current_user(user_id, user_role)
                        self.logger.debug(f"多用户模式：设置用户 ID={user_id}, 角色={user_role}")
                    else:
                        # 多用户模式下必须有用户，否则清空数据
                        self.bookshelf.set_current_user(None, "user")
                        self.logger.warning("多用户模式：未找到当前用户，已清空用户设置")
                else:
                    # 单用户模式：使用默认用户或无用户
                    if current_user:
                        # 如果有用户信息，也设置（兼容性）
                        user_id = current_user.get('id')
                        user_role = current_user.get('role', 'user')
                        self.bookshelf.set_current_user(user_id, user_role)
                        self.logger.debug(f"单用户模式：设置用户 ID={user_id}")
                    else:
                        # 单用户模式无用户时使用默认设置
                        self.bookshelf.set_current_user(None, "user")
                        self.logger.debug("单用户模式：使用默认设置")
                
                # 性能优化：只在真正需要时重新加载书架数据
                # 多用户模式下的特殊处理：用户切换时强制重新加载
                user_changed = False
                if hasattr(self, '_last_user_id'):
                    current_user_id = current_user.get('id') if current_user else None
                    if self._last_user_id != current_user_id:
                        user_changed = True
                        self.logger.debug(f"用户已切换：{self._last_user_id} -> {current_user_id}")
                
                # 更新用户ID缓存
                self._last_user_id = current_user.get('id') if current_user else None
                
                # 决定是否需要重新加载数据
                should_reload = force_reload or user_changed
                
                if should_reload:
                    self.bookshelf._load_books()
                    if user_changed:
                        self.logger.debug("书架数据已重新加载（用户切换）")
                    else:
                        self.logger.debug("书架数据已重新加载（搜索条件改变）")
                else:
                    self.logger.debug("使用缓存的书架数据（搜索条件和用户未改变）")
            except Exception as e:
                self.logger.warning(f"重新加载书架数据失败: {e}")
            
            # 缓存搜索参数
            self._last_search_params = current_search_params
        
        # 获取已经按用户权限过滤后的书籍进行搜索
        all_books = list(self.bookshelf.books.values())
        
        if not page_change_only:
            filtered_books = []
            
            # 支持多关键词搜索（逗号分隔）
            keywords = [k.strip() for k in search_keyword.split(",") if k.strip()] if search_keyword else []
            
            # 处理search_format参数，确保正确处理NoSelection对象
            actual_search_format = "all"
            if search_format != "all" and search_format is not None:
                # 检查是否是NoSelection对象
                if hasattr(search_format, 'is_blank') and callable(getattr(search_format, 'is_blank', None)) and search_format.is_blank():
                    actual_search_format = "all"
                else:
                    # 确保search_format是字符串类型
                    actual_search_format = str(search_format) if search_format else "all"
            
            # 处理search_author参数，确保正确处理NoSelection对象
            actual_search_author = "all"
            if search_author != "all" and search_author is not None:
                # 检查是否是NoSelection对象
                if hasattr(search_author, 'is_blank') and callable(getattr(search_author, 'is_blank', None)) and search_author.is_blank():
                    actual_search_author = "all"
                else:
                    # 确保search_author是字符串类型
                    actual_search_author = str(search_author) if search_author else "all"
            
            # 性能优化：批量处理书籍筛选
            if actual_search_format == "all" and actual_search_author == "all" and not keywords:
                # 没有搜索条件时，直接使用所有书籍
                filtered_books = all_books
            else:
                # 有搜索条件时进行筛选
                for book in all_books:
                    # 检查文件格式
                    format_match = True
                    
                    if actual_search_format != "all":
                        # 书籍的format包含点号（如.txt），下拉框值没有点号（如txt）
                        # 需要将书籍格式去掉点号再比较
                        book_format_without_dot = book.format.lower().lstrip('.')
                        format_match = book_format_without_dot == actual_search_format.lower()
                    
                    # 检查作者匹配
                    author_match = True
                    if actual_search_author != "all":
                        author_match = book.author.lower() == actual_search_author.lower()
                    
                    # 检查关键词匹配
                    keyword_match = False
                    if format_match and author_match:
                        if keywords:
                            # 多关键词OR逻辑：只要匹配任意一个关键词
                            for keyword in keywords:
                                if (keyword.lower() in book.title.lower() or 
                                    keyword.lower() in book.author.lower() or 
                                    (hasattr(book, 'pinyin') and book.pinyin and keyword.lower() in book.pinyin.lower()) or
                                    (book.tags and keyword.lower() in book.tags.lower())):
                                    keyword_match = True
                                    break
                        else:
                            # 没有关键词时，只按格式和作者筛选
                            keyword_match = True
                    
                    if keyword_match and author_match and format_match:
                        filtered_books.append(book)
            
            # 对筛选后的书籍进行排序
            if search_keyword or search_format != "all" or search_author != "all":
                # 有搜索条件时，手动排序（使用从reading_history表获取的阅读时间）
                # 性能优化：批量获取阅读历史信息
                reading_info_cache = {}
                for book in filtered_books:
                    reading_info = self.bookshelf.get_book_reading_info(book.path)
                    reading_info_cache[book.path] = reading_info.get('last_read_date') or ""
                
                self._all_books = sorted(filtered_books, 
                                       key=lambda book: reading_info_cache.get(book.path, ""), 
                                       reverse=True)
            else:
                # 没有搜索条件时，使用书架管理器的排序方法（从reading_history表获取阅读时间）
                self._all_books = self.bookshelf.get_sorted_books("last_read_date", reverse=True)
        
        # 计算总页数
        self._total_pages = max(1, (len(self._all_books) + self._books_per_page - 1) // self._books_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 获取当前页的书籍
        start_index = (self._current_page - 1) * self._books_per_page
        end_index = min(start_index + self._books_per_page, len(self._all_books))
        current_page_books = self._all_books[start_index:end_index]
        
        if not page_change_only:
            # 创建序号到书籍路径的映射
            self._book_index_mapping = {}
            # 创建行键到书籍路径的映射
            self._row_key_mapping = {}
        
        # 性能优化：批量处理阅读历史信息
        reading_info_cache = {}
        for book in current_page_books:
            reading_info = self.bookshelf.get_book_reading_info(book.path)
            reading_info_cache[book.path] = reading_info
        
        # 清空当前页的数据
        if page_change_only:
            table.clear()
        
        for index, book in enumerate(current_page_books, start_index + 1):
            # 存储序号到路径的映射
            self._book_index_mapping[str(index)] = book.path
            # 存储行键到路径的映射
            row_key = f"{book.path}_{index}"
            self._row_key_mapping[row_key] = book.path
            
            # 从缓存中获取阅读信息
            reading_info = reading_info_cache.get(book.path, {})
            last_read = reading_info.get('last_read_date') or ""
            progress = reading_info.get('reading_progress', 0) * 100  # 转换为百分比
            
            # 格式化标签显示（直接显示逗号分隔的字符串）
            tags_display = book.tags if book.tags else ""
            
            # 如果文件不存在，在标题前添加标记
            display_title = book.title
            if getattr(book, 'file_not_found', False):
                display_title = f"[🈚] {book.title}"
            
            # 获取当前表格的实际列数
            column_count = len(table.columns)
            
            # 添加基础列数据
            from src.utils.file_utils import FileUtils
            size_display = FileUtils.format_file_size(book.file_size) if hasattr(book, 'file_size') and book.file_size else ""
            
            row_values = [
                str(index),
                display_title,
                book.author,
                book.format.upper(),
                size_display,  # 文件大小显示
                last_read,
                f"{progress:.1f}%",
                tags_display,
            ]
            
            # 根据实际列数动态添加操作按钮
            # 基础列数量为7个，操作列从第8列开始
            if column_count > 7:
                # 文件不存在时，不显示阅读、查看文件、重命名按钮
                if getattr(book, 'file_not_found', False):
                    row_values.append("")
                else:            
                    if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                        row_values.append(f"[{get_global_i18n().t('bookshelf.read')}]")
            
            if column_count > 8:
                if getattr(book, 'file_not_found', False):
                    row_values.append("")
                else:
                    if getattr(self.app, "has_permission", lambda k: True)("bookshelf.view_file"):
                        row_values.append(f"[{get_global_i18n().t('bookshelf.view_file')}]")
            
            if column_count > 9:
                if getattr(book, 'file_not_found', False):
                    row_values.append("")
                else:
                    row_values.append(f"[{get_global_i18n().t('bookshelf.rename')}]")
            
            if column_count > 10:
                if getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book"):
                    row_values.append(f"[{get_global_i18n().t('bookshelf.delete')}]")
            
            # 确保行数据列数与表格列数匹配
            while len(row_values) < column_count:
                row_values.append("")
            
            # 使用唯一的key，避免重复（book.path + 索引）
            table.add_row(*row_values, key=f"{book.path}_{index}")
        
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
            
            # 安全地获取当前显示的文本内容
            # 由于Textual的Label组件没有renderable属性，我们直接构建新的文本
            # 从统计信息重新构建，而不是尝试从Label中读取
            total_count = len(self._all_books)
            format_counts = {}
            
            for book in self._all_books:
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
            
            # 添加分页信息
            pagination_info = f" | {get_global_i18n().t('bookshelf.page_info', page=self._current_page, total_pages=self._total_pages)}"
            stats_label.update(stats_text + pagination_info)
            
        except Exception as e:
            logger.error(f"更新分页信息失败: {e}")
    
    def _refresh_bookshelf(self) -> None:
        """刷新书架内容"""
        self.logger.info("刷新书架内容")
        # 重置到第一页
        self._current_page = 1
        # 重新加载书籍数据（保持当前搜索条件）
        self._load_books(self._search_keyword, self._search_format, self._search_author)
        # 显示刷新成功的提示
        self.notify(get_global_i18n().t("bookshelf.refresh_success"))
    
    def _perform_search(self) -> None:
        """执行搜索操作"""
        # 获取搜索输入框和格式筛选器的值
        search_input = self.query_one("#bookshelf-search-input", Input)
        format_filter = self.query_one("#bookshelf-format-filter", Select)
        author_filter = self.query_one("#bookshelf-source-filter", Select)
        
        # 更新搜索状态
        self._search_keyword = search_input.value or ""
        
        # 处理下拉框值，确保正确处理NoSelection对象
        format_value = format_filter.value
        if format_value is None or (hasattr(format_value, 'is_blank') and callable(getattr(format_value, 'is_blank', None)) and format_value.is_blank()):
            self._search_format = "all"
        else:
            # 确保format_value是字符串类型
            self._search_format = str(format_value) if format_value else "all"
        
        author_value = author_filter.value
        if author_value is None or (hasattr(author_value, 'is_blank') and callable(getattr(author_value, 'is_blank', None)) and author_value.is_blank()):
            self._search_author = "all"
        else:
            # 确保format_value是字符串类型
            self._search_author = str(author_value) if author_value else "all"
        
        # 重置到第一页
        self._current_page = 1
        
        # 重新加载书籍数据（应用搜索条件）
        self._load_books(self._search_keyword, self._search_format, self._search_author)
        
        # 显示搜索结果的提示
        search_conditions = []
        if self._search_keyword:
            search_conditions.append(f"关键词: {self._search_keyword}")
        if self._search_format != "all":
            search_conditions.append(f"格式: {self._search_format.upper()}")
        if self._search_author != "all":
            search_conditions.append(f"作者: {self._search_author}")
        
        # if search_conditions:
        #     condition_text = "，".join(search_conditions)
        #     self.notify(
        #         f"{condition_text} - {get_global_i18n().t('search.results_found', count=len(self._all_books))}",
        #         severity="information"
        #     )

    def _get_books(self) -> None:
        """获取书籍列表"""
        self.logger.info("获取书籍列表")
        
        # 检查权限
        if not getattr(self.app, "has_permission", lambda k: True)("bookshelf.get_books"):
            self.notify(get_global_i18n().t("bookshelf.np_get_books"), severity="warning")
            return
        
        # 获取书籍列表
        self.app.push_screen("get_books")  # 打开获取书籍页面
    
    def _show_file_explorer(self) -> None:
        """显示文件资源管理器"""
        self.logger.info("打开文件资源管理器")
        # 导入文件资源管理器屏幕
        from src.ui.screens.file_explorer_screen import FileExplorerScreen
        # 打开文件资源管理器
        file_explorer_screen = FileExplorerScreen(
            self.theme_manager,
            self.bookshelf,
            self.statistics_manager
        )
        self.app.push_screen(file_explorer_screen)
    
    # def _has_permission(self, permission_key: str) -> bool:
    #     """检查权限"""
    #     try:
    #         from src.core.database_manager import DatabaseManager
    #         db_manager = DatabaseManager()
            
    #         # 获取当前用户ID和角色
    #         current_user_id = getattr(self.app, 'current_user_id', None)
    #         current_user = getattr(self.app, 'current_user', {})
    #         user_role = current_user.get('role') if current_user else None
            
    #         if current_user_id is None:
    #             # 如果没有当前用户，检查是否是多用户模式
    #             if not getattr(self.app, 'multi_user_enabled', False):
    #                 # 单用户模式默认允许所有权限
    #                 return True
    #             else:
    #                 # 多用户模式但没有当前用户，默认拒绝
    #                 return False
            
    #         return db_manager.has_permission(current_user_id, permission_key, user_role)
    #     except Exception as e:
    #         logger.error(f"检查权限失败: {e}")
    #         return True  # 出错时默认允许
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "add-book-btn":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.add_book"):
                self._show_add_book_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_add_books"), severity="warning")
        elif event.button.id == "scan-directory-btn":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.scan_directory"):
                self._show_scan_directory_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_scan_directory"), severity="warning")
        elif event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "search-btn":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._show_search_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_search"), severity="warning")
        elif event.button.id == "sort-btn":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._show_sort_menu()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_sort"), severity="warning")
        elif event.button.id == "batch-ops-btn":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book"):
                self._show_batch_ops_menu()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_opts"), severity="warning")
        elif event.button.id == "refresh-btn":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._refresh_bookshelf()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_refresh"), severity="warning")
        elif event.button.id == "get-books-btn":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.get_books"):
                self._get_books()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_get_books"), severity="warning")
    
    def on_input_changed(self, event) -> None:
        """输入框内容变化时的回调"""
        if event.input.id == "bookshelf-search-input":
            # 输入框内容变化时立即执行搜索
            self._perform_search()
    
    def on_select_changed(self, event) -> None:
        """下拉框选择变化时的回调"""
        if event.select.id == "bookshelf-format-filter" :
            # 文件格式选择变化时立即执行搜索
            self._perform_search()
        if event.select.id == "bookshelf-source-filter" :
            logger.info("来源下拉框选择变化")
            self._perform_search()
    
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
        if column_key in ["read_action", "view_action", "rename_action", "delete_action"]:
            row_key = cell_key.row_key.value
            if not row_key:
                self.logger.error("行键为空，无法执行操作")
                return
            
            # 通过行键映射获取实际书籍路径
            book_id = self._row_key_mapping.get(row_key)
            if not book_id:
                self.logger.error(f"未找到行键对应的书籍路径: {row_key}")
                return
                
            # 根据列键判断点击的是哪个按钮
            if column_key == "read_action":
                if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                    self.logger.info(f"点击阅读按钮打开书籍: {book_id}")
                    # 直接使用备用方法打开书籍
                    self._open_book_fallback(book_id)
                else:
                    self.notify(get_global_i18n().t("bookshelf.np_read"), severity="warning")
            elif column_key == "view_action":
                if getattr(self.app, "has_permission", lambda k: True)("bookshelf.view_file"):
                    self.logger.info(f"点击查看文件按钮: {book_id}")
                    self._view_file(book_id)
                else:
                    self.notify(get_global_i18n().t("bookshelf.np_view_file"), severity="warning")
            elif column_key == "rename_action":
                if getattr(self.app, "has_permission", lambda k: True)("bookshelf.rename_book"):
                    self.logger.info(f"点击重命名按钮: {book_id}")
                    self._rename_book(book_id)
                else:
                    self.notify(get_global_i18n().t("bookshelf.np_rename"), severity="warning")
            elif column_key == "delete_action":
                if getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book"):
                    self.logger.info(f"点击删除按钮: {book_id}")
                    self._delete_book(book_id)
                else:
                    self.notify(get_global_i18n().t("bookshelf.np_delete"), severity="warning")
    
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
                self.notify(f"{get_global_i18n().t("bookshelf.find_book_failed")}: {book_path}", severity="error")
        except Exception as e:
            self.logger.error(f"打开书籍失败: {e}")
            self.notify(f"{get_global_i18n().t("bookshelf.open_book_failed")}: {e}", severity="error")
    
    def _view_file(self, book_path: str) -> None:
        """查看书籍文件"""
        try:
            import os
            import subprocess
            import platform
            
            # 检查文件是否存在
            if not os.path.exists(book_path):
                self.notify(f"{get_global_i18n().t("bookshelf.file_not_exists")}: {book_path}", severity="error")
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
            
            self.notify(f"{get_global_i18n().t("bookshelf.opened_in_file_explorer")}: {os.path.basename(book_path)}", severity="information")
            
        except Exception as e:
            self.logger.error(f"查看文件失败: {e}")
            self.notify(f"{get_global_i18n().t("bookshelf.view_file_failed")}: {e}", severity="error")
    
    def _rename_book(self, book_path: str) -> None:
        """重命名书籍"""
        try:
            # 获取书籍信息
            book = self.bookshelf.get_book(book_path)
            if not book:
                self.notify(get_global_i18n().t("bookshelf.find_book_failed"), severity="error")
                return
            
            # 显示重命名对话框
            from src.ui.dialogs.rename_book_dialog import RenameBookDialog
            
            def handle_rename_result(result: Optional[Dict[str, Any]]) -> None:
                """处理重命名结果"""
                if result and result.get("success"):
                    new_title = result.get("new_title", "")
                    book_path = result.get("book_path", "")
                    
                    if not new_title or not book_path:
                        self.notify(get_global_i18n().t("bookshelf.rename_failed"), severity="error")
                        return
                    
                    # 执行重命名操作
                    if self.bookshelf.rename_book(book_path, new_title):
                        self.notify(
                            get_global_i18n().t("bookshelf.rename_success", title=new_title),
                            severity="information"
                        )
                        # 刷新书架显示
                        self._refresh_bookshelf()
                    else:
                        self.notify(get_global_i18n().t("bookshelf.rename_failed"), severity="error")
            
            # 弹出重命名对话框
            self.app.push_screen(
                RenameBookDialog(book.title, book_path),
                callback=handle_rename_result
            )
            
        except Exception as e:
            self.logger.error(f"重命名书籍失败: {e}")
            self.notify(f"{get_global_i18n().t('bookshelf.rename_failed')}: {e}", severity="error")

    def _delete_book(self, book_path: str) -> None:
        """删除书籍"""
        try:
            # 显示确认对话框
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            
            def handle_delete_result(result: Optional[bool]) -> None:
                """处理删除确认结果"""
                if result:
                    # 确认删除
                    try:
                        # 从书架中删除书籍
                        success = self.bookshelf.remove_book(book_path)
                        if success:
                            self.notify(get_global_i18n().t("bookshelf.delete_book_success"), severity="information")
                            # 刷新书库内存缓存和书架列表
                            self.bookshelf._load_books()
                            self._load_books()
                        else:
                            self.notify(get_global_i18n().t("bookshelf.delete_book_failed"), severity="error")
                    except Exception as e:
                        self.logger.error(f"删除书籍时发生错误: {e}")
                        self.notify(f"{get_global_i18n().t("bookshelf.delete_book_failed")}: {e}", severity="error")
            
            # 显示确认对话框
            book = self.bookshelf.get_book(book_path)
            if book:
                confirm_dialog = ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t("bookshelf.confirm_delete"),
                    get_global_i18n().t("bookshelf.confirm_delete_message", book=book.title)
                )
                self.app.push_screen(confirm_dialog, handle_delete_result)  # type: ignore
            else:
                self.notify(get_global_i18n().t("bookshelf.did_not_find_book"), severity="error")
                
        except Exception as e:
            self.logger.error(f"删除书籍失败: {e}")
            self.notify(f"{get_global_i18n().t("bookshelf.delete_book_failed")}: {e}", severity="error")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        数据表行选择时的回调
        
        Args:
            event: 行选择事件
        """
        row_key = event.row_key.value
        self.logger.info(f"选择书籍行键: {row_key}")
        
        # 通过行键映射获取实际书籍路径
        book_id = self._row_key_mapping.get(row_key)
        if not book_id:
            self.logger.error(f"未找到行键对应的书籍路径: {row_key}")
            return
            
        self.logger.info(f"选择书籍: {book_id}")
        # 类型安全的open_book调用
        app_instance = self.app
        if hasattr(app_instance, 'open_book'):
            app_instance.open_book(book_id)  # type: ignore[attr-defined]
        
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
                    # 使用行键映射获取实际书籍路径
                    book_id = self._row_key_mapping.get(row_key.value)
                    if not book_id:
                        self.logger.error(f"未找到行键对应的书籍路径: {row_key.value}")
                        return
                    self.logger.info(get_global_i18n().t('bookshelf.press_enter_open_book', book_id=book_id))
                    # 使用备用方法打开书籍（权限）
                    if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                        self._open_book_fallback(book_id)
                    else:
                        self.notify(get_global_i18n().t("bookshelf.np_read"), severity="warning")
                    event.prevent_default()
        elif event.key == "s":
            # S键搜索
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._show_search_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_search"), severity="warning")
            event.prevent_default()
        elif event.key == "r":
            # R键排序
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._show_sort_menu()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_sort"), severity="warning")
            event.prevent_default()
        elif event.key == "l":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book"):
                self._show_batch_ops_menu()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_opts"), severity="warning")
            event.prevent_default()
        elif event.key == "a":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.add_book"):
                self._show_add_book_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_add_books"), severity="warning")
            event.prevent_default()
        elif event.key == "d":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.scan_directory"):
                self._show_scan_directory_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_scan_directory"), severity="warning")
            event.prevent_default()
        elif event.key == "g":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.get_books"):
                self._get_books()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_get_books"), severity="warning")
            event.prevent_default()
        elif event.key == "f":
            # F键刷新书架
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._refresh_bookshelf()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_refresh"), severity="warning")
            event.prevent_default()
        elif event.key == "escape":
            # ESC键返回（仅一次 pop，并停止冒泡）
            self.app.pop_screen()
            event.stop()
        elif event.key == "n":
            # N键下一页
            if self._current_page < self._total_pages:
                self._current_page += 1
                self._load_books(self._search_keyword, self._search_format, self._search_author)
            event.prevent_default()
        elif event.key == "p":
            # P键上一页
            if self._current_page > 1:
                self._current_page -= 1
                self._load_books(self._search_keyword, self._search_format, self._search_author)
            event.prevent_default()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            if (table.cursor_row == len(table.rows) - 1 and 
                self._current_page < self._total_pages):
                self._current_page += 1
                self._load_books(self._search_keyword, self._search_format, self._search_author)
                # 将光标移动到新页面的第一行
                table = self.query_one("#books-table", DataTable)
                table.action_cursor_down()  # 先向下移动一次
                table.action_cursor_up()     # 再向上移动一次，确保在第一行
                event.prevent_default()
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            if table.cursor_row == 0 and self._current_page > 1:
                self._current_page -= 1
                self._load_books(self._search_keyword, self._search_format, self._search_author)
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
                # 使用备用方法打开书籍
                if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                    self._open_book_fallback(book_path)
                else:
                    self.notify(get_global_i18n().t("bookshelf.np_read"), severity="warning")
                event.prevent_default()
            else:
                # 如果该序号没有对应的书籍，显示提示
                self.notify(
                    get_global_i18n().t("bookshelf.no_book_position", book_index=book_index),
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
                        app_instance.open_book(result.book_id)  # type: ignore[attr-defined]
        
        # 使用现有的搜索对话框，传入已经设置了用户权限的书架实例
        from src.ui.dialogs.search_dialog import SearchDialog
        dialog = SearchDialog(self.theme_manager, bookshelf=self.bookshelf)
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
                # 创建行键到书籍路径的映射
                self._row_key_mapping = {}
                
                for index, book in enumerate(sorted_books, 1):
                    # 存储序号到路径的映射
                    self._book_index_mapping[str(index)] = book.path
                    # 存储行键到路径的映射
                    row_key = f"{book.path}_{index}"
                    self._row_key_mapping[row_key] = book.path
                    
                    # 从reading_history表获取阅读信息
                    reading_info = self.bookshelf.get_book_reading_info(book.path)
                    last_read = reading_info.get('last_read_date') or ""
                    progress = reading_info.get('reading_progress', 0) * 100  # 转换为百分比
                    
                    # 格式化标签显示（直接显示逗号分隔的字符串）
                    tags_display = book.tags if book.tags else ""
                    
                    # 添加操作按钮
                    # 文件不存在时，不显示阅读、查看文件、重命名按钮
                    if getattr(book, 'file_not_found', False):
                        read_button = ""
                        view_file_button = ""
                        rename_button = ""
                        delete_button = f"[{get_global_i18n().t('bookshelf.delete')}]"
                    else:
                        read_button = f"[{get_global_i18n().t('bookshelf.read')}]"
                        view_file_button = f"[{get_global_i18n().t('bookshelf.view_file')}]"
                        rename_button = f"[{get_global_i18n().t('bookshelf.rename')}]"
                        delete_button = f"[{get_global_i18n().t('bookshelf.delete')}]"
                    
                    # 如果文件不存在，在标题前添加标记
                    display_title = book.title
                    if getattr(book, 'file_not_found', False):
                        display_title = f"[书籍文件不存在] {book.title}"
                    
                    # 格式化文件大小显示
                    from src.utils.file_utils import FileUtils
                    size_display = FileUtils.format_file_size(book.file_size) if hasattr(book, 'file_size') and book.file_size else ""
                    
                    table.add_row(
                        str(index),  # 显示数字序号而不是路径
                        display_title,
                        book.author,
                        book.format.upper(),
                        size_display,  # 文件大小显示
                        last_read,
                        f"{progress:.1f}%",
                        tags_display,
                        read_button,  # 阅读按钮
                        view_file_button,  # 查看文件按钮
                        rename_button,  # 重命名按钮
                        delete_button,  # 删除按钮
                        key=f"{book.path}_{index}"  # 使用唯一的key，避免重复（book.path + 索引）
                    )
                
                # 将字段名映射到翻译文本
                sort_key_translations = {
                    "title": get_global_i18n().t("bookshelf.title"),
                    "author": get_global_i18n().t("bookshelf.author"),
                    "add_date": get_global_i18n().t("bookshelf.add_date"),
                    "last_read_date": get_global_i18n().t("bookshelf.last_read"),
                    "progress": get_global_i18n().t("bookshelf.progress"),
                    "file_size": get_global_i18n().t("bookshelf.file_size")
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
        
    def _apply_permissions(self) -> None:
        """按权限禁用/隐藏按钮（无权限时隐藏按钮）"""
        try:
            # 工具栏按钮 - 根据权限显示或隐藏
            search_btn = self.query_one("#search-btn", Button)
            search_btn.display = getattr(self.app, "has_permission", lambda k: True)("bookshelf.read")
            
            sort_btn = self.query_one("#sort-btn", Button)
            sort_btn.display = getattr(self.app, "has_permission", lambda k: True)("bookshelf.read")
            
            batch_ops_btn = self.query_one("#batch-ops-btn", Button)
            batch_ops_btn.display = getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book")
            
            refresh_btn = self.query_one("#refresh-btn", Button)
            refresh_btn.display = getattr(self.app, "has_permission", lambda k: True)("bookshelf.read")
        except Exception:
            pass
        try:
            # 底部按钮 - 根据权限显示或隐藏
            add_book_btn = self.query_one("#add-book-btn", Button)
            add_book_btn.display = getattr(self.app, "has_permission", lambda k: True)("bookshelf.add_book")
            
            scan_directory_btn = self.query_one("#scan-directory-btn", Button)
            scan_directory_btn.display = getattr(self.app, "has_permission", lambda k: True)("bookshelf.scan_directory")
            
            get_books_btn = self.query_one("#get-books-btn", Button)
            get_books_btn.display = getattr(self.app, "has_permission", lambda k: True)("bookshelf.get_books")
        except Exception:
            pass
    
    def action_press(self, selector: str) -> None:
        """重写press方法，添加权限检查"""
        # 检查按钮权限映射
        permission_mapping = {
            "#add-book-btn": "bookshelf.add_book",
            "#scan-directory-btn": "bookshelf.scan_directory", 
            "#search-btn": "bookshelf.read",
            "#sort-btn": "bookshelf.read",
            "#batch-ops-btn": "bookshelf.delete_book",
            "#get-books-btn": "bookshelf.get_books",
            "#refresh-btn": "bookshelf.read"
        }
        
        # 检查权限
        required_permission = permission_mapping.get(selector)
        if required_permission and not getattr(self.app, "has_permission", lambda k: True)(required_permission):
            # 无权限时显示警告
            permission_warnings = {
                "bookshelf.add_book": get_global_i18n().t("bookshelf.np_add_books"),
                "bookshelf.scan_directory": get_global_i18n().t("bookshelf.np_scan_directory"),
                "bookshelf.read": get_global_i18n().t("bookshelf.np_search"),
                "bookshelf.delete_book": get_global_i18n().t("bookshelf.np_opts"),
                "bookshelf.get_books": get_global_i18n().t("bookshelf.np_get_books"),
            }
            warning_message = permission_warnings.get(required_permission, get_global_i18n().t("bookshelf.np_get_books"))
            self.notify(warning_message, severity="warning")
            return
        
        # 有权限时调用按钮的press方法（如果有的话）
        # 注意：这里不能调用super().action_press(selector)，因为父类可能没有这个方法
        # 而是直接调用原始按钮处理逻辑
        pass


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
        """显示添加书籍对话框 - 使用文件资源管理器屏幕"""
        def handle_add_book_result(result: Optional[Union[str, List[str]]]) -> None:
            """处理添加书籍结果"""
            if result:
                # 显示加载动画
                self._show_loading_animation(get_global_i18n().t("bookshelf.adding_books"))
                
                try:
                    if isinstance(result, list):
                        # 多选模式 - 添加多个文件
                        added_count = 0
                        for file_path in result:
                            book = self.bookshelf.add_book(file_path)
                            if book:
                                added_count += 1
                        
                        if added_count > 0:
                            self.notify(
                                get_global_i18n().t("bookshelf.book_added", count=added_count),
                                severity="information"
                            )
                            self._load_books()
                        else:
                            self.notify(get_global_i18n().t("bookshelf.add_books_failed"), severity="error")
                    else:
                        # 单选模式 - 添加单个文件
                        book = self.bookshelf.add_book(result)
                        if book:
                            self.notify(
                                get_global_i18n().t("bookshelf.book_added", count=1),
                                severity="information"
                            )
                            self._load_books()
                        else:
                            self.notify(get_global_i18n().t("bookshelf.add_books_failed"), severity="error")
                except Exception as e:
                    logger.error(f"{get_global_i18n().t('bookshelf.add_books_failed')}: {e}")
                    self.notify(f"{get_global_i18n().t("bookshelf.add_books_failed")}: {e}", severity="error")
                
                # 隐藏加载动画
                self._hide_loading_animation()
        
        # 使用文件资源管理器屏幕，启用多选模式
        from src.ui.screens.file_explorer_screen import FileExplorerScreen
        
        file_explorer_screen = FileExplorerScreen(
            theme_manager=self.theme_manager,
            bookshelf=self.bookshelf,
            statistics_manager=self.statistics_manager,
            selection_mode="file",
            title=get_global_i18n().t("bookshelf.add_book"),
            multiple=True  # 启用多选模式
        )
        
        self.app.push_screen(file_explorer_screen, handle_add_book_result)
        
    def _show_scan_directory_dialog(self) -> None:
        """显示扫描目录对话框 - 使用文件资源管理器屏幕"""
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
        
        # 使用文件资源管理器屏幕
        from src.ui.screens.file_explorer_screen import FileExplorerScreen
        
        file_explorer_screen = FileExplorerScreen(
            theme_manager=self.theme_manager,
            bookshelf=self.bookshelf,
            statistics_manager=self.statistics_manager,
            selection_mode="directory",
            title=get_global_i18n().t("bookshelf.scan_directory")
        )
        
        self.app.push_screen(file_explorer_screen, handle_directory_result)
    
    def _show_loading_animation(self, message: Optional[str] = None) -> None:
        """显示加载动画"""
        if message is None:
            message = get_global_i18n().t("common.on_action")
        try:
            # 原生 LoadingIndicator：可见即动画
            try:
                if not hasattr(self, "loading_indicator"):
                    self.loading_indicator = self.query_one("#bookshelf-loading-indicator", LoadingIndicator)
            except Exception:
                pass
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    self.loading_indicator.display = True
            except Exception:
                pass

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
            # 原生 LoadingIndicator：隐藏
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    self.loading_indicator.display = False
            except Exception:
                pass

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

    def action_clear_search_params(self) -> None:
        """清除搜索参数"""
        self.query_one("#bookshelf-search-input", Input).value = ""
        self.query_one("#bookshelf-search-input", Input).placeholder = get_global_i18n().t("bookshelf.search_placeholder")
        self.query_one("#bookshelf-format-filter", Select).value = "all"
        self.query_one("#bookshelf-source-filter", Select).value = "all"