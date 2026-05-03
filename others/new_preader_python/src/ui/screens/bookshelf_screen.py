"""
书架屏幕
"""


import os
from typing import Dict, Any, Optional, List, ClassVar, Set
from webbrowser import get
from src.core import book
from src.core.book import Book
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid, VerticalScroll
from textual.widgets import Static, Button, Label, Header, Footer, LoadingIndicator, Input, Select
from textual.widgets import DataTable
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
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("a", "press('#add-book-btn')", get_global_i18n().t('common.add')),
        ("d", "press('#scan-directory-btn')", get_global_i18n().t('bookshelf.scan_directory')),
        ("s", "press('#search-btn')", get_global_i18n().t('common.search')),
        ("r", "press('#sort-btn')", get_global_i18n().t('bookshelf.sort_name')),
        ("l", "press('#batch-ops-btn')", get_global_i18n().t('bookshelf.batch_ops_name')),
        ("g", "press('#get-books-btn')", get_global_i18n().t('bookshelf.get_books')),
        ("f", "press('#refresh-btn')", get_global_i18n().t('bookshelf.refresh')),
        ("x", "clear_search_params", get_global_i18n().t('bookshelf.clear_search_params')),
        ("j", "jump_to", get_global_i18n().t('bookshelf.jump_to')),
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

        # 刷新时保持当前搜索条件
        self._load_books(
            search_keyword=self._search_keyword,
            search_format=self._search_format,
            search_author=self._search_author,
            from_search=self._search_keyword != "" or self._search_format != "all" or self._search_author != "all"
        )
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
        self._books_per_page = 15
        self._total_pages = 1
        self._all_books: List[Book] = []
        
        # 分页优化：缓存和性能相关
        self._books_cache: Dict[str, List[Book]] = {}  # 缓存搜索结果
        self._last_cache_key = ""  # 上次缓存键
        self._cache_timestamp = 0  # 缓存时间戳
        self._cache_ttl = 300  # 缓存有效期（秒）
        self._cache_max_size = 1000  # 最大缓存条目数
        self._cache_hits = 0  # 缓存命中次数
        self._cache_misses = 0  # 缓存未命中次数
        self._cache_eviction_policy = "lru"  # 缓存淘汰策略
        self._cache_memory_limit = 100 * 1024 * 1024  # 内存限制100MB
        
        # 表格初始化状态
        self._table_initialized = False
        
        # 初始化数据表列
        self.columns = [
            ("ID", "id"),
            (get_global_i18n().t("common.book_name"), "title"),
            (get_global_i18n().t("bookshelf.author"), "author"),
            (get_global_i18n().t("bookshelf.format"), "format"),
            (get_global_i18n().t("bookshelf.size"), "size"),  # 新增文件大小列
            (get_global_i18n().t("bookshelf.last_read"), "last_read"),
            (get_global_i18n().t("bookshelf.progress"), "progress"),
            (get_global_i18n().t("bookshelf.tags"), "tags"),
            (get_global_i18n().t("bookshelf.read"), "read_action"),  # 阅读按钮列
            (get_global_i18n().t("bookshelf.browser_read"), "browser_read_action"),  # 浏览器阅读按钮列
            (get_global_i18n().t("bookshelf.view_file"), "view_action"),  # 查看文件按钮列
            (get_global_i18n().t("bookshelf.rename"), "rename_action"),  # 重命名按钮列
            (get_global_i18n().t("bookshelf.delete"), "delete_action"),  # 删除按钮列
        ]
        
        # 初始化搜索状态变量
        self._search_keyword = ""
        self._search_format = "all"
        self._search_author = "all"
        
        # 搜索历史（存储最近10个搜索关键词）
        self._search_history: List[str] = []
        self._max_search_history = 10
        
        # 初始化加载指示器变量
        self.loading_indicator = None
        
        # 作者列表缓存（性能优化）
        self._author_options_cache = None
        self._author_options_loaded = False
        
        # 阅读信息缓存（性能优化）
        self._reading_info_cache: Dict[str, Dict[str, Any]] = {}
        self._reading_info_cache_timestamp: Dict[str, float] = {}
        self._reading_info_cache_ttl = 60  # 缓存60秒

        # 排序相关属性
        self._sort_column: Optional[str] = None  # 当前排序的列
        self._sort_reverse: bool = True  # 排序方向，True表示倒序
    

    
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
        sort_key_options = [
            (get_global_i18n().t("common.book_name"), 'book_name'),
            (get_global_i18n().t("bookshelf.author"), 'author'),
            (get_global_i18n().t("bookshelf.add_date"), 'add_date'),
            (get_global_i18n().t("bookshelf.last_read"), 'last_read'),
            (get_global_i18n().t("bookshelf.progress"), 'progress'),
            (get_global_i18n().t("bookshelf.file_size"), 'file_size'),
        ]
        sort_order_options = [
            (get_global_i18n().t("sort.ascending"), "asc"),
            (get_global_i18n().t("sort.descending"), "desc"),
        ]

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
                    Horizontal(
                        # 排序
                        Select(
                            id="sort-key-radio",
                            options=sort_key_options, 
                            prompt=get_global_i18n().t("sort.sort_by"),
                            classes="bookshelf-sort-key"
                        ),
                        Select(
                            id="sort-order-radio",
                            options=sort_order_options,
                            prompt=get_global_i18n().t("sort.order"),
                            classes="bookshelf-sort-order"
                        ),
                        # 搜索
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
                # 底部状态栏（分页导航和统计信息）
                Horizontal(
                    Button("◀◀", id="first-page-btn", classes="pagination-btn"),
                    Button("◀", id="prev-page-btn", classes="pagination-btn"),
                    Label("", id="page-info", classes="page-info"),
                    Button("▶", id="next-page-btn", classes="pagination-btn"),
                    Button("▶▶", id="last-page-btn", classes="pagination-btn"),
                    Button(get_global_i18n().t("bookshelf.jump_to"), id="jump-page-btn", classes="pagination-btn"),
                    id="pagination-bar",
                    classes="pagination-bar"
                ),
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
        grid.styles.grid_size_rows = 4
        grid.styles.grid_size_columns = 1
        grid.styles.grid_rows = ("25%", "55%", "10%", "10%")
        
        # 原生 LoadingIndicator（初始隐藏），挂载到书籍统计区域
        try:
            self.loading_indicator = LoadingIndicator(id="bookshelf-loading-indicator")
            self.loading_indicator.display = False
            loading_area = self.query_one("#books-stats-area")
            loading_area.mount(self.loading_indicator)
        except Exception:
            pass
        
        # 初始化数据表（每次挂载时确保列已正确添加）
        table = self.query_one("#books-table", DataTable)
        
        # 清除现有列，重新添加（确保虚拟滚动组件列正确）
        table.clear(columns=True)
        
        # 根据权限过滤操作列
        can_read = getattr(self.app, "has_permission", lambda k: True)("bookshelf.read")
        can_view = getattr(self.app, "has_permission", lambda k: True)("bookshelf.view_file")
        can_delete = getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book")
        cols = []
        for label, key in self.columns:
            if key == "read_action" and not can_read:
                continue
            if key == "browser_read_action" and not can_read:
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
                # 单用户模式：设置为超级管理员以查看所有书籍
                if current_user:
                    # 如果有用户信息，也设置为超级管理员
                    user_id = current_user.get('id')
                    self.bookshelf.set_current_user(user_id, "superadmin")
                    self.logger.debug(f"单用户模式：设置用户 ID={user_id} 为超级管理员")
                else:
                    # 单用户模式无用户时设置为超级管理员
                    self.bookshelf.set_current_user(None, "superadmin")
                    self.logger.debug("单用户模式：设置为超级管理员")
            
            # 初始化用户ID缓存
            self._last_user_id = current_user.get('id') if current_user else None
            
        except Exception as e:
            self.logger.warning(f"设置书架管理器用户失败: {e}")
        
        # 加载书籍数据
        self._load_books()
        
        # 初始化分页按钮状态
        self._update_pagination_buttons()
        
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
            if key == "browser_read_action" and not can_read:
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
    
    def _load_books(self, search_keyword: str = "", search_format: str = "all", search_author: str = "all", from_search: bool = False) -> None:
        """加载书籍数据
        
        Args:
            search_keyword: 搜索关键词
            search_format: 文件格式筛选
            search_author: 作者筛选
            from_search: 是否来自搜索操作（搜索时不设置表格焦点）
        """
        # 显示加载动画
        self._show_loading_animation(f"{get_global_i18n().t('book_on_loadding')}", progress=0)
        
        table = self.query_one("#books-table", DataTable)
        
        # 性能优化：检查是否只需要更新当前页数据（分页切换时）
        current_search_params = f"{search_keyword}_{search_format}_{search_author}"
        page_change_only = False

        # 如果搜索条件未改变且书籍数据已存在，只需更新分页
        # 除非：有自定义排序（_sort_column 不为 None）
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
                    # 单用户模式：设置为超级管理员以查看所有书籍
                    if current_user:
                        # 如果有用户信息，也设置为超级管理员
                        user_id = current_user.get('id')
                        self.bookshelf.set_current_user(user_id, "superadmin")
                        self.logger.debug(f"单用户模式：设置用户 ID={user_id} 为超级管理员")
                    else:
                        # 单用户模式无用户时设置为超级管理员
                        self.bookshelf.set_current_user(None, "superadmin")
                        self.logger.debug("单用户模式：设置为超级管理员")
                
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

        # 如果只是分页切换但有自定义排序，需要重新应用排序
        if page_change_only and self._sort_column is not None:
            # 核心概念：阅读进度 100% 的永远在最后面，无论什么排序方式
            not_completed_books = []
            completed_books = []

            for book in self._all_books:
                reading_info = self.bookshelf._reading_info_cache.get(book.path, {})
                progress = reading_info.get('reading_progress', 0)
                if progress >= 1.0:
                    completed_books.append(book)
                else:
                    not_completed_books.append(book)

            self.logger.debug(f"重新排序前 - 未完成: {len(not_completed_books)}, 已完成: {len(completed_books)}")

            # 预先获取阅读信息
            reading_info_cache = {}
            for book in not_completed_books + completed_books:
                reading_info = self.bookshelf.get_book_reading_info(book.path)
                reading_info_cache[book.path] = reading_info

            def get_sort_key(book):
                return self._get_sort_key_with_cache(book, self._sort_column, reading_info_cache)

            not_completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)
            completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)

            self._all_books = not_completed_books + completed_books

            self.logger.debug(f"重新应用排序: {self._sort_column}, 倒序: {self._sort_reverse}")
            if not_completed_books:
                self.logger.debug(f"未完成前3本: {[b.title[:15] for b in not_completed_books[:3]]}")
            if completed_books:
                self.logger.debug(f"已完成前3本: {[b.title[:15] for b in completed_books[:3]]}")
            self.logger.debug(f"合并后前3本: {[b.title[:15] for b in self._all_books[:3]]}")
            if len(self._all_books) > 3:
                self.logger.debug(f"合并后最后3本: {[b.title[:15] for b in self._all_books[-3:]]}")

        # 性能优化：使用缓存
        cache_key = self._get_cache_key()
        if not page_change_only:
            # 尝试从缓存获取数据
            cached_books = self._load_books_from_cache(cache_key)
            if cached_books is not None:
                filtered_books = cached_books
                self.logger.debug("使用缓存的书架数据")
                # 更新进度：缓存命中
                self._show_loading_animation(f"{get_global_i18n().t('book_on_loadding')}", progress=20)
                # 当使用缓存时，需要重新获取所有书籍用于筛选
                all_books = list(self.bookshelf.books.values())
            else:
                # 获取已经按用户权限过滤后的书籍进行搜索
                all_books = list(self.bookshelf.books.values())
                filtered_books = []
            
            # 支持多关键词搜索（逗号分隔，支持AND/OR逻辑）
            # 格式: "关键词1,关键词2" (OR逻辑) 或 "关键词1+关键词2" (AND逻辑)
            keywords = []
            search_logic = "or"  # 默认OR逻辑
            
            if search_keyword:
                if "+" in search_keyword:
                    # AND逻辑: 关键词1+关键词2
                    keywords = [k.strip() for k in search_keyword.split("+") if k.strip()]
                    search_logic = "and"
                else:
                    # OR逻辑: 关键词1,关键词2
                    keywords = [k.strip() for k in search_keyword.split(",") if k.strip()]
                    search_logic = "or"
            
            # 处理search_format参数，确保正确处理NoSelection对象
            actual_search_format = "all"
            if search_format != "all" and search_format is not None:
                # 检查是否是空值或NoSelection对象
                if search_format == "" or (hasattr(search_format, 'value') and getattr(search_format, 'value', '') == ""):
                    actual_search_format = "all"
                else:
                    # 确保search_format是字符串类型
                    actual_search_format = str(search_format) if search_format else "all"
            
            # 处理search_author参数，确保正确处理NoSelection对象
            actual_search_author = "all"
            if search_author != "all" and search_author is not None:
                # 检查是否是空值或NoSelection对象
                if search_author == "" or (hasattr(search_author, 'value') and getattr(search_author, 'value', '') == ""):
                    actual_search_author = "all"
                else:
                    # 确保search_author是字符串类型
                    actual_search_author = str(search_author) if search_author else "all"
            
            # 性能优化：批量处理书籍筛选
            if actual_search_format == "all" and actual_search_author == "all" and not keywords:
                # 没有搜索条件时，直接使用所有书籍
                filtered_books = all_books
                # 更新进度：筛选完成
                self._show_loading_animation(f"{get_global_i18n().t('book_on_loadding')}", progress=40)
            else:
                # 有搜索条件时进行筛选
                total_books = len(all_books)
                filtered_books = []
                
                for i, book in enumerate(all_books):
                    # 更新筛选进度
                    if i % 10 == 0:  # 每10本书更新一次进度
                        progress = 40 + (i / total_books * 20)  # 40% - 60%
                        self._show_loading_animation(f"{get_global_i18n().t('book_on_loadding')}", progress=progress)
                    
                    # 检查文件格式
                    format_match = True
                    
                    if actual_search_format != "all":
                        # 书籍的format包含点号（如.txt），下拉框值没有点号（如txt）
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
                            if search_logic == "and":
                                # AND逻辑：所有关键词都必须匹配
                                keyword_match = True
                                for keyword in keywords:
                                    # 模糊搜索：检查标题、作者、拼音、标签
                                    title_match = keyword.lower() in book.title.lower()
                                    author_match_keyword = keyword.lower() in book.author.lower()
                                    pinyin_match = (hasattr(book, 'pinyin') and book.pinyin and 
                                                   keyword.lower() in book.pinyin.lower())
                                    tags_match = (book.tags and keyword.lower() in book.tags.lower())
                                    
                                    # 如果任意一个字段匹配当前关键词，继续检查下一个
                                    if not (title_match or author_match_keyword or pinyin_match or tags_match):
                                        keyword_match = False
                                        break
                            else:
                                # OR逻辑：任意一个关键词匹配即可
                                for keyword in keywords:
                                    title_match = keyword.lower() in book.title.lower()
                                    author_match_keyword = keyword.lower() in book.author.lower()
                                    pinyin_match = (hasattr(book, 'pinyin') and book.pinyin and 
                                                   keyword.lower() in book.pinyin.lower())
                                    tags_match = (book.tags and keyword.lower() in book.tags.lower())
                                    
                                    if title_match or author_match_keyword or pinyin_match or tags_match:
                                        keyword_match = True
                                        break
                        else:
                            # 没有关键词时，只按格式和作者筛选
                            keyword_match = True
                    
                    if keyword_match and author_match and format_match:
                        filtered_books.append(book)
            
            # 更新进度：排序开始
            self._show_loading_animation(f"{get_global_i18n().t('book_on_loadding')}", progress=60)

            # 对筛选后的书籍进行排序
            # 核心概念：阅读进度 100% 的永远在最后面，无论什么排序方式
            # 先分组：未完成和已完成
            not_completed_books = []
            completed_books = []

            for book in filtered_books:
                reading_info = self.bookshelf._reading_info_cache.get(book.path, {})
                progress = reading_info.get('reading_progress', 0)
                # self.logger.debug(f"书籍: {book.title[:20]}, 进度: {progress}")
                if progress >= 1.0:
                    completed_books.append(book)
                else:
                    not_completed_books.append(book)

            self.logger.debug(f"未完成: {len(not_completed_books)}, 已完成: {len(completed_books)}")

            # 根据选择的排序字段对两组分别排序
            if self._sort_column is not None:
                # 用户点击了表头，使用自定义排序
                # 预先获取阅读信息，避免在排序时重复查询
                reading_info_cache = {}
                for book in not_completed_books + completed_books:
                    reading_info = self.bookshelf.get_book_reading_info(book.path)
                    reading_info_cache[book.path] = reading_info

                def get_sort_key(book):
                    return self._get_sort_key_with_cache(book, self._sort_column, reading_info_cache)

                not_completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)
                completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)

                self.logger.debug(f"排序字段: {self._sort_column}, 倒序: {self._sort_reverse}")
                if not_completed_books:
                    self.logger.debug(f"未完成前3本: {[b.title[:15] for b in not_completed_books[:3]]}")
                if completed_books:
                    self.logger.debug(f"已完成前3本: {[b.title[:15] for b in completed_books[:3]]}")
            else:
                # 默认按最后阅读时间排序
                not_completed_books.sort(key=lambda book: self.bookshelf._reading_info_cache.get(book.path, {}).get('last_read_date', ""), reverse=True)
                completed_books.sort(key=lambda book: self.bookshelf._reading_info_cache.get(book.path, {}).get('last_read_date', ""), reverse=True)

            # 合并：未完成在前，已完成在后
            self._all_books = not_completed_books + completed_books

            self.logger.debug(f"合并后前3本: {[b.title[:15] for b in self._all_books[:3]]}")
            if len(self._all_books) > 3:
                self.logger.debug(f"合并后最后3本: {[b.title[:15] for b in self._all_books[-3:]]}")
        
        # 计算总页数
        self._total_pages = max(1, (len(self._all_books) + self._books_per_page - 1) // self._books_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 获取当前页的书籍
        start_index = (self._current_page - 1) * self._books_per_page
        end_index = min(start_index + self._books_per_page, len(self._all_books))
        current_page_books = self._all_books[start_index:end_index]
        
        # 每次加载都要重新创建映射，确保行键正确
        self._book_index_mapping = {}
        self._row_key_mapping = {}

        # 性能优化：直接使用书架缓存的阅读信息，避免重复查询数据库
        reading_info_cache = {}
        for book in current_page_books:
            # 从书架缓存中获取阅读信息，避免重复查询数据库
            reading_info = self.bookshelf._reading_info_cache.get(book.path, {})
            reading_info_cache[book.path] = reading_info
        
        # 清空当前页的数据，但保留列
        if page_change_only:
            # 只清除行数据，保留列定义
            table.clear()
        else:
            # 非页面切换时，确保列已正确设置
            table.clear(columns=True)
            self._add_table_columns(table)
        
        # 准备虚拟滚动数据
        virtual_data = []
        for index, book in enumerate(current_page_books):
            # 计算全局索引（从1开始）
            global_index = start_index + index + 1
            # 存储序号到路径的映射
            self._book_index_mapping[str(global_index)] = book.path
            # 存储行键到路径的映射
            row_key = f"{book.path}_{global_index}"
            self._row_key_mapping[row_key] = book.path
            
            # 从缓存中获取阅读信息
            reading_info = reading_info_cache.get(book.path, {})
            last_read = reading_info.get('last_read_date') or ""
            # 数据库中存储的是小数(0-1),需要乘以100转换为百分比显示
            progress = reading_info.get('reading_progress', 0) * 100
            
            # 格式化标签显示（直接显示逗号分隔的字符串）
            tags_display = book.tags if book.tags else ""
            
            # 如果文件不存在，在标题前添加标记
            display_title = book.title
            if getattr(book, 'file_not_found', False):
                display_title = f"[🈚] {book.title}"
            
            # 添加基础列数据
            from src.utils.file_utils import FileUtils
            size_display = FileUtils.format_file_size(book.file_size) if hasattr(book, 'file_size') and book.file_size else ""
            
            # 构建行数据
            row_data = {
                'id': str(global_index),  # 添加ID列显示全局索引
                'title': display_title,
                'author': book.author,
                'format': book.format.upper(),
                'size_display': size_display,
                'last_read': last_read,
                'progress': f"{progress:.1f}%",
                'tags': tags_display,
                'read_action': '',
                'browser_read_action': '',
                'view_action': '',
                'rename_action': '',
                'delete_action': '',
                '_row_key': row_key,  # 添加行键信息用于虚拟滚动组件
                '_global_index': global_index  # 添加全局索引用于显示
            }
            
            # 根据权限设置操作按钮
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read") and not getattr(book, 'file_not_found', False):
                row_data['read_action'] = f"[{get_global_i18n().t('bookshelf.read')}]"
                row_data['browser_read_action'] = f"[{get_global_i18n().t('bookshelf.browser_read')}]"
            
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.view_file") and not getattr(book, 'file_not_found', False):
                row_data['view_action'] = f"[{get_global_i18n().t('bookshelf.view_file')}]"
            
            if not getattr(book, 'file_not_found', False):
                row_data['rename_action'] = f"[{get_global_i18n().t('bookshelf.rename')}]"
            
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book"):
                row_data['delete_action'] = f"[{get_global_i18n().t('bookshelf.delete')}]"
            
            virtual_data.append(row_data)
        
        # 填充表格数据
        table.clear()
        for row_data in virtual_data:
            table.add_row(
                row_data['id'],
                row_data['title'],
                row_data['author'],
                row_data['format'],
                row_data['size_display'],
                row_data['last_read'],
                row_data['progress'],
                row_data['tags'],
                row_data['read_action'],
                row_data['browser_read_action'],
                row_data['view_action'],
                row_data['rename_action'],
                row_data['delete_action']
            )
        
        # 更新书籍统计信息
        self._update_books_stats(self._all_books)
        
        # 更新分页信息显示
        self._update_pagination_info()
        
        # 性能优化：保存数据到缓存
        if not page_change_only:
            self._save_books_to_cache(cache_key, self._all_books)
        
        # 更新分页按钮状态
        self._update_pagination_buttons()
        
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
            
            # 添加筛选状态信息
            filter_conditions = []
            if self._search_keyword:
                filter_conditions.append(f"关键词: {self._search_keyword}")
            if self._search_format != "all":
                filter_conditions.append(f"格式: {self._search_format.upper()}")
            if self._search_author != "all":
                filter_conditions.append(f"作者: {self._search_author}")
            
            if filter_conditions:
                stats_text += f" [筛选: {' + '.join(filter_conditions)}]"
            
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
        
        # 记录搜索历史（非空关键词）
        if self._search_keyword and self._search_keyword not in self._search_history:
            # 添加到搜索历史
            self._search_history.insert(0, self._search_keyword)
        # 限制搜索历史数量
        if len(self._search_history) > self._max_search_history:
            self._search_history = self._search_history[:self._max_search_history]
        
        # 处理下拉框值，确保正确处理NoSelection对象和_BLANK值
        format_value = format_filter.value
        if (format_value is None or 
            format_value == "" or 
            (hasattr(format_value, 'value') and getattr(format_value, 'value', '') == "") or
            (hasattr(format_value, 'is_blank') and getattr(format_value, 'is_blank', False)) or
            str(format_value) == 'Select.BLANK'):
            self._search_format = "all"
        else:
            # 确保format_value是字符串类型
            self._search_format = str(format_value) if format_value else "all"
        
        author_value = author_filter.value
        if (author_value is None or 
            author_value == "" or 
            (hasattr(author_value, 'value') and getattr(author_value, 'value', '') == "") or
            (hasattr(author_value, 'is_blank') and getattr(author_value, 'is_blank', False)) or
            str(author_value) == 'Select.BLANK'):
            self._search_author = "all"
        else:
            # 确保author_value是字符串类型
            self._search_author = str(author_value) if author_value else "all"
        
        # 重置到第一页
        self._current_page = 1
        
        # 重新加载书籍数据（应用搜索条件）
        self._load_books(self._search_keyword, self._search_format, self._search_author, from_search=True)
        
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
        
        # 分页导航按钮处理
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
    
    def on_input_changed(self, event) -> None:
        """输入框内容变化时的回调"""
        if event.input.id == "bookshelf-search-input":
            # 输入框内容变化时立即执行搜索
            self._perform_search()
            # 执行搜索后，保持焦点在搜索框
            self.set_timer(0.1, lambda: self._focus_search_input())
    
    def on_select_changed(self, event) -> None:
        """下拉框选择变化时的回调"""
        if event.select.id == "bookshelf-format-filter" :
            # 文件格式选择变化时立即执行搜索
            self._perform_search()
        if event.select.id == "bookshelf-source-filter" :
            logger.info("来源下拉框选择变化")
            self._perform_search()
        
        # 处理排序选择变化
        if event.select.id in ["sort-key-radio", "sort-order-radio"]:
            self._perform_sort_from_select()
    
    def _focus_search_input(self) -> None:
        """将焦点设置回搜索框"""
        try:
            search_input = self.query_one("#bookshelf-search-input", Input)
            search_input.focus()
        except Exception as e:
            logger.debug(f"设置搜索框焦点失败: {e}")
    
    def _perform_sort_from_select(self) -> None:
        """根据Select组件的选择执行排序"""
        try:
            # 获取排序字段选择
            sort_key_select = self.query_one("#sort-key-radio", Select)
            sort_key = sort_key_select.value

            # 获取排序顺序选择
            sort_order_select = self.query_one("#sort-order-radio", Select)
            sort_order = sort_order_select.value

            # 转换排序顺序
            reverse = sort_order == "desc"

            # 映射字段名
            key_mapping = {
                "book_name": "title",
                "author": "author",
                "add_date": "add_date",
                "last_read": "last_read_date",
                "progress": "progress",
                "file_size": "file_size"
            }

            actual_sort_key = key_mapping.get(sort_key, "title")

            # 保存排序配置
            self._sort_column = actual_sort_key
            self._sort_reverse = reverse

            # 对当前书籍列表进行排序（保持搜索条件）
            # 核心概念：阅读进度 100% 的永远在最后面，无论什么排序方式
            not_completed_books = []
            completed_books = []

            for book in self._all_books:
                reading_info = self.bookshelf._reading_info_cache.get(book.path, {})
                progress = reading_info.get('reading_progress', 0)
                if progress >= 1.0:
                    completed_books.append(book)
                else:
                    not_completed_books.append(book)

            self.logger.debug(f"排序前 - 未完成: {len(not_completed_books)}, 已完成: {len(completed_books)}")

            # 预先获取阅读信息
            reading_info_cache = {}
            for book in not_completed_books + completed_books:
                reading_info = self.bookshelf.get_book_reading_info(book.path)
                reading_info_cache[book.path] = reading_info

            def get_sort_key(book):
                return self._get_sort_key_with_cache(book, self._sort_column, reading_info_cache)

            not_completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)
            completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)

            # 合并：未完成在前，已完成在后
            self._all_books = not_completed_books + completed_books

            self.logger.debug(f"排序后 - 总计: {len(self._all_books)}, 排序字段: {self._sort_column}, 倒序: {self._sort_reverse}")
            if not_completed_books:
                self.logger.debug(f"未完成前3本: {[b.title[:15] for b in not_completed_books[:3]]}")
            if completed_books:
                self.logger.debug(f"已完成前3本: {[b.title[:15] for b in completed_books[:3]]}")

            # 重新计算分页信息
            self._total_pages = max(1, (len(self._all_books) + self._books_per_page - 1) // self._books_per_page)
            # 回到第一页
            self._current_page = 1

            # 刷新表格显示（只显示当前页的数据）
            self._load_current_page(from_search=False)
            
            # 更新分页控件状态
            self._update_pagination_controls()
            
            # 获取显示文本
            sort_key_display = ""
            for option in sort_key_select._options:
                if option[1] == sort_key:
                    sort_key_display = str(option[0])
                    break
            
            # 显示通知
            order_text = get_global_i18n().t("sort.descending") if reverse else get_global_i18n().t("sort.ascending")
            self.notify(f"{get_global_i18n().t('sort.sorted_by')} {sort_key_display} ({order_text})")
            
        except Exception as e:
            logger.error(f"排序失败: {e}")
            self.notify(get_global_i18n().t("sort.sort_failed"), severity="error")
    
    def _load_current_page(self, page_change_only: bool = False, from_search: bool = False) -> None:
        """加载当前页的书籍数据
        
        Args:
            page_change_only: 是否仅更改页面（不需要重新加载数据）
            from_search: 是否来自搜索操作（搜索时不设置表格焦点）
        """
        try:
            table = self.query_one("#books-table", DataTable)
            
            # 获取当前页的书籍
            start_index = (self._current_page - 1) * self._books_per_page
            end_index = min(start_index + self._books_per_page, len(self._all_books))
            current_page_books = self._all_books[start_index:end_index]
            
            # 每次加载都要重新创建映射，确保行键正确
            self._book_index_mapping = {}
            self._row_key_mapping = {}
            
            # 性能优化：批量处理阅读历史信息
            reading_info_cache = {}
            for book in current_page_books:
                reading_info = self.bookshelf.get_book_reading_info(book.path)
                reading_info_cache[book.path] = reading_info
            
            # 清空当前页的数据，但保留列
            if page_change_only:
                # 只清除行数据，保留列定义
                table.clear()
            else:
                # 非页面切换时，确保列已正确设置
                table.clear(columns=True)
                self._add_table_columns(table)
            
            # 准备虚拟滚动数据
            virtual_data = []
            for index, book in enumerate(current_page_books):
                # 计算全局索引（从1开始）
                global_index = start_index + index + 1
                # 存储序号到路径的映射
                self._book_index_mapping[str(global_index)] = book.path
                # 存储行键到路径的映射
                row_key = f"{book.path}_{global_index}"
                self._row_key_mapping[row_key] = book.path
                
                # 从缓存中获取阅读信息
                reading_info = reading_info_cache.get(book.path, {})
                last_read = reading_info.get('last_read_date') or ""
                # 数据库中存储的是小数(0-1),需要乘以100转换为百分比显示
                progress = reading_info.get('reading_progress', 0) * 100
                
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
                    str(global_index),  # 显示数字序号而不是路径
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
                    key=f"{book.path}_{global_index}"  # 使用唯一的key，避免重复（book.path + 索引）
                )
            
            # 只有在不是来自搜索时才设置表格焦点
            if not from_search:
                table.focus()
                
        except Exception as e:
            logger.error(f"加载当前页失败: {e}")
            self.notify("加载当前页失败", severity="error")
    
    def _update_pagination_controls(self) -> None:
        """更新分页控件状态"""
        try:
            # 更新分页信息显示
            pagination_info = f" | {get_global_i18n().t('bookshelf.page_info', page=self._current_page, total_pages=self._total_pages)}"
            
            # 更新分页按钮状态
            first_btn = self.query_one("#first-page-btn", Button)
            prev_btn = self.query_one("#prev-page-btn", Button)
            next_btn = self.query_one("#next-page-btn", Button)
            last_btn = self.query_one("#last-page-btn", Button)
            
            first_btn.disabled = self._current_page <= 1
            prev_btn.disabled = self._current_page <= 1
            next_btn.disabled = self._current_page >= self._total_pages
            last_btn.disabled = self._current_page >= self._total_pages
            
            # 更新页面信息标签
            page_label = self.query_one("#page-info", Label)
            page_label.update(f"{self._current_page}/{self._total_pages}")
            
        except Exception as e:
            logger.error(f"更新分页控件失败: {e}")
    
    def _refresh_books_table(self, books: List[Book], from_search: bool = False) -> None:
        """刷新书籍表格显示（已弃用，使用_load_current_page）
        
        Args:
            books: 书籍列表
            from_search: 是否来自搜索操作（搜索时不设置表格焦点）
        """
        # 为了兼容性保留此方法，但实际使用_load_current_page
        self._all_books = books
        self._load_current_page(from_search=from_search)
    
    @on(DataTable.HeaderSelected, "#books-table")
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """数据表格表头点击事件 - 处理排序"""
        try:
            column_key = event.column_key.value or ""

            self.logger.debug(f"表头点击事件: column={column_key}")

            # 只对特定列进行排序：ID、标题、作者、格式、大小、最后阅读时间、进度、标签
            sortable_columns = ["id", "title", "author", "format", "size", "last_read", "progress", "tags"]

            if column_key in sortable_columns:
                # 切换排序方向
                if self._sort_column == column_key:
                    self._sort_reverse = not self._sort_reverse
                else:
                    self._sort_column = column_key
                    self._sort_reverse = True  # 新列默认倒序

                # 重新加载表格显示（会在 _load_books 中应用排序）
                self._load_books(self._search_keyword, self._search_format, self._search_author)

                # 显示排序提示
                sort_direction = get_global_i18n().t('common.desc') if self._sort_reverse else get_global_i18n().t('common.asc')
                column_names = {
                    "id": "ID",
                    "title": get_global_i18n().t('common.book_name'),
                    "author": get_global_i18n().t('bookshelf.author'),
                    "format": get_global_i18n().t('bookshelf.format'),
                    "size": get_global_i18n().t('bookshelf.size'),
                    "last_read": get_global_i18n().t('bookshelf.last_read'),
                    "progress": get_global_i18n().t('bookshelf.progress'),
                    "tags": get_global_i18n().t('bookshelf.tags')
                }
                column_name = column_names.get(column_key, column_key)
                self.notify(f"Sort by {column_name} {sort_direction}", severity="information")

        except Exception as e:
            self.logger.error(f"表头点击事件处理失败: {e}")

    def _get_sort_key_with_cache(self, book: Book, column_key: str, reading_info_cache: Dict[str, Dict[str, Any]]) -> Any:
        """获取书籍的排序键值（使用缓存的阅读信息）

        Args:
            book: 书籍对象
            column_key: 排序的列键
            reading_info_cache: 阅读信息缓存

        Returns:
            排序键值
        """
        if column_key == "id":
            # ID排序，使用路径作为唯一标识
            return book.path or ""
        elif column_key == "title":
            # 标题排序
            return book.title or ""
        elif column_key == "author":
            # 作者排序
            return book.author or ""
        elif column_key == "format":
            # 格式排序，转换为小写进行比较
            return book.format.lower() if book.format else ""
        elif column_key == "size":
            # 大小排序，使用原始字节数
            return book.size or 0
        elif column_key == "file_size":
            # 文件大小排序，使用原始字节数
            return getattr(book, 'file_size', 0) or 0
        elif column_key == "last_read" or column_key == "last_read_date":
            # 最后阅读时间排序
            from datetime import datetime
            try:
                reading_info = reading_info_cache.get(book.path, {})
                last_read = reading_info.get('last_read_date') or ""
                if last_read:
                    return datetime.fromisoformat(last_read)
                else:
                    return datetime.min
            except:
                return datetime.min
        elif column_key == "progress":
            # 进度排序，从阅读信息中获取
            try:
                reading_info = reading_info_cache.get(book.path, {})
                return reading_info.get('reading_progress', 0) or 0
            except:
                return 0.0
        elif column_key == "tags":
            # 标签排序
            return book.tags or ""
        elif column_key == "add_date":
            # 添加日期排序
            from datetime import datetime
            try:
                if hasattr(book, 'add_date') and book.add_date:
                    return datetime.fromisoformat(book.add_date)
                else:
                    return datetime.min
            except:
                return datetime.min
        # 默认返回空字符串，避免None导致的比较错误
        return ""

    @on(DataTable.CellSelected, "#books-table")
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """
        数据表单元格选择时的回调 - 支持点击筛选和操作按钮
        
        Args:
            event: 单元格选择事件
        """
        self.logger.debug(f"单元格选择事件触发: {event}")
        
        try:
            # 检查是否点击了操作按钮列
            if hasattr(event, 'coordinate'):
                column_key = event.coordinate.column
                row_index = event.coordinate.row
                
                self.logger.debug(f"点击的列: {column_key}, 行: {row_index}")
                
                # 获取当前页的数据
                start_index = (self._current_page - 1) * self._books_per_page
                if row_index is not None and row_index < len(self._all_books) - start_index:
                    book = self._all_books[start_index + row_index]
                    
                    if not book:
                        return
                        
                    book_id = book.path
                    
                    # 处理操作按钮列（阅读、浏览器阅读、查看文件、重命名、删除）
                    # 列索引从0开始：8=阅读, 9=浏览器阅读, 10=查看文件, 11=重命名, 12=删除
                    if column_key in [8, 9, 10, 11, 12]:
                        
                        # 根据列索引执行不同的操作
                        if column_key == 8:  # 阅读按钮列
                            self.logger.info(f"点击阅读按钮打开书籍: {book_id}")
                            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                                self._open_book_fallback(book_id)
                            else:
                                self.notify(get_global_i18n().t("bookshelf.np_read"), severity="warning")
                        elif column_key == 9:  # 浏览器阅读按钮列
                            self.logger.info(f"点击浏览器阅读按钮打开书籍: {book_id}")
                            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                                self._open_book_in_browser(book_id)
                            else:
                                self.notify(get_global_i18n().t("bookshelf.np_read"), severity="warning")
                        elif column_key == 10:  # 查看文件按钮列
                            self.logger.info(f"点击查看文件按钮: {book_id}")
                            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.view_file"):
                                self._view_file(book_id)
                            else:
                                self.notify(get_global_i18n().t("bookshelf.np_view_file"), severity="warning")
                        elif column_key == 11:  # 重命名按钮列
                            self.logger.info(f"点击重命名按钮: {book_id}")
                            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.rename_book"):
                                self._rename_book(book_id)
                            else:
                                self.notify(get_global_i18n().t("bookshelf.np_rename"), severity="warning")
                        elif column_key == 12:  # 删除按钮列
                            self.logger.info(f"点击删除按钮: {book_id}")
                            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book"):
                                self._delete_book(book_id)
                            else:
                                self.notify(get_global_i18n().t("bookshelf.np_delete"), severity="warning")
                        
                        # 阻止事件冒泡，避免触发其他处理程序
                        event.stop()
                    
                    # 处理标题列点击：复制书名到剪贴板
                    # 列索引从0开始：1=标题列
                    elif column_key == 1:
                        self._copy_book_title_to_clipboard(book.title)
                        event.stop()

                    # 处理筛选列（作者、格式、标签）
                    # 列索引从0开始：2=作者, 3=格式, 7=标签
                    elif column_key in [2, 3, 7]:
                        self._handle_column_filter(column_key, book)
                        event.stop()
                        
                else:
                    self.logger.warning(f"行索引超出范围: row_index={row_index}, 总数据长度={len(self._all_books)}, 起始索引={start_index}")
            else:
                self.logger.debug("单元格选择事件没有坐标信息")
        except Exception as e:
            self.logger.error(f"处理单元格选择时出错: {e}")
    
    def _copy_book_title_to_clipboard(self, title: str) -> None:
        """复制书名到剪贴板
        
        Args:
            title: 书籍标题
        """
        try:
            # 使用pyperclip复制到剪贴板
            import pyperclip
            pyperclip.copy(title)
            self.notify(get_global_i18n().t("bookshelf.title_copied", title=title), severity="information")
        except ImportError:
            # 如果pyperclip未安装，尝试使用系统命令
            import subprocess
            import platform
            
            system = platform.system()
            try:
                if system == 'Darwin':  # macOS
                    subprocess.run(['pbcopy'], input=title, text=True, check=True)
                elif system == 'Windows':  # Windows
                    subprocess.run(['clip'], input=title, text=True, check=True, shell=True)
                else:  # Linux
                    # 尝试使用xclip或xsel
                    try:
                        subprocess.run(['xclip', '-selection', 'clipboard'], input=title, text=True, check=True)
                    except (subprocess.SubprocessError, FileNotFoundError):
                        subprocess.run(['xsel', '--clipboard', '--input'], input=title, text=True, check=True)
                
                self.notify(get_global_i18n().t("bookshelf.title_copied", title=title), severity="information")
            except Exception as e:
                self.logger.error(f"复制书名到剪贴板失败: {e}")
                self.notify(get_global_i18n().t("cannot_copy"), severity="error")
        except Exception as e:
            self.logger.error(f"复制书名到剪贴板失败: {e}")
            self.notify(get_global_i18n().t("cannot_copy"), severity="error")

    def _copy_focused_book_title(self) -> None:
        """复制当前焦点所在行的书籍标题到剪贴板"""
        try:
            table = self.query_one("#books-table", DataTable)
            
            # 检查是否有有效行
            if not table.rows or table.cursor_row is None or table.cursor_row < 0:
                self.notify(get_global_i18n().t("bookshelf.no_books"), severity="warning")
                return
            
            # 计算当前光标行对应的书籍索引
            start_index = (self._current_page - 1) * self._books_per_page
            row_index = table.cursor_row
            
            # 检查是否超出范围
            if row_index >= len(self._all_books) - start_index:
                self.logger.warning(f"行索引超出范围: row_index={row_index}, 总数据长度={len(self._all_books)}, 起始索引={start_index}")
                return
            
            # 获取对应书籍
            book = self._all_books[start_index + row_index]
            if not book:
                return
            
            # 复制书籍标题（去除可能的前缀标记）
            title = book.title
            if title.startswith("[🈚] ") or title.startswith("[书籍文件不存在] "):
                # 提取原始标题
                if title.startswith("[🈚] "):
                    title = title[5:]  # 去掉 "[🈚] " 前缀
                else:
                    title = title[len("[书籍文件不存在] "):]  # 去掉前缀
            
            self._copy_book_title_to_clipboard(title)
            
        except Exception as e:
            self.logger.error(f"复制焦点书籍标题失败: {e}")
            self.notify(get_global_i18n().t("cannot_copy"), severity="error")

    def _handle_column_filter(self, column_key: int, book) -> None:
        """处理列筛选功能
        
        Args:
            column_key: 列索引
            book: 书籍对象
        """
        try:
            # 根据列索引处理不同的筛选逻辑
            if column_key == 2:  # 作者列
                filter_value = book.author
                filter_type = "author"
                filter_display = f"作者: {filter_value}"
            elif column_key == 3:  # 格式列
                filter_value = book.format.lower().lstrip('.')
                filter_type = "format"
                filter_display = f"格式: {filter_value.upper()}"
            elif column_key == 7:  # 标签列
                filter_value = book.tags if book.tags else ""
                filter_type = "tags"
                filter_display = f"标签: {filter_value}"
            else:
                return
            
            # 如果筛选值为空，则不执行筛选
            if not filter_value:
                self.notify(f"{filter_display} 为空，无法筛选", severity="warning")
                return
            
            # 执行筛选操作
            self._perform_column_filter(filter_type, filter_value, filter_display)
            
        except Exception as e:
            self.logger.error(f"处理列筛选时出错: {e}")
            self.notify(f"筛选操作失败: {e}", severity="error")
    
    def _perform_column_filter(self, filter_type: str, filter_value: str, filter_display: str) -> None:
        """执行列筛选操作
        
        Args:
            filter_type: 筛选类型（author/format/tags）
            filter_value: 筛选值
            filter_display: 筛选显示文本
        """
        try:
            # 重置到第一页
            self._current_page = 1
            
            # 根据筛选类型设置不同的搜索条件
            if filter_type == "author":
                # 作者筛选
                self._search_keyword = ""
                self._search_format = "all"
                self._search_author = filter_value
                
                # 更新作者筛选下拉框
                author_filter = self.query_one("#bookshelf-source-filter", Select)
                author_filter.value = filter_value
                
            elif filter_type == "format":
                # 格式筛选
                self._search_keyword = ""
                self._search_format = filter_value
                self._search_author = "all"
                
                # 更新格式筛选下拉框
                format_filter = self.query_one("#bookshelf-format-filter", Select)
                format_filter.value = filter_value
                
            elif filter_type == "tags":
                # 标签筛选 - 使用关键词搜索
                self._search_keyword = filter_value
                self._search_format = "all"
                self._search_author = "all"
                
                # 更新搜索输入框
                search_input = self.query_one("#bookshelf-search-input", Input)
                search_input.value = filter_value
                
                # 重置下拉框
                format_filter = self.query_one("#bookshelf-format-filter", Select)
                format_filter.value = "all"
                author_filter = self.query_one("#bookshelf-source-filter", Select)
                author_filter.value = "all"
            
            # 重新加载书籍数据
            self._load_books(self._search_keyword, self._search_format, self._search_author)
            
            # 显示筛选结果通知
            total_books = len(self._all_books)
            self.notify(
                f"已按 {filter_display} 筛选，共找到 {total_books} 本书", 
                severity="information"
            )
            
        except Exception as e:
            self.logger.error(f"执行列筛选操作时出错: {e}")
            self.notify(f"筛选操作失败: {e}", severity="error")
    
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
    
    def _open_book_in_browser(self, book_path: str) -> None:
        """使用浏览器打开书籍"""
        try:
            from src.utils.browser_reader import BrowserReader
            
            # 检查文件是否存在
            if not os.path.exists(book_path):
                self.notify(f"{get_global_i18n().t("bookshelf.file_not_exists")}: {book_path}", severity="error")
                return
            
            # 获取书籍
            book = self.bookshelf.get_book(book_path)
            if not book:
                self.notify(get_global_i18n().t("bookshelf.find_book_failed"), severity="error")
                return
            
            # 保存书籍路径，避免回调函数中的作用域问题
            book_path_for_callback = book.path
            
            # 保存进度回调
            def on_progress_save(progress: float, scroll_top: int, scroll_height: int,
                             current_page: Optional[int] = None, total_pages: Optional[int] = None,
                             word_count: Optional[int] = None) -> None:
                """保存阅读进度"""
                self.logger.info(f"收到保存进度回调: progress={progress:.4f} (小数), scrollTop={scroll_top}px, scrollHeight={scroll_height}px")
                if current_page is not None:
                    self.logger.info(f"current_page={current_page}, total_pages={total_pages}")
                if word_count is not None:
                    self.logger.info(f"word_count={word_count}")

                try:
                    # 保存阅读进度到数据库
                    from src.core.bookmark import BookmarkManager
                    bookmark_manager = BookmarkManager()

                    # 如果前端没有传递页数信息，根据进度估算
                    if total_pages is None or total_pages <= 0:
                        total_pages = int(scroll_height / 1000)  # 假设每页1000px
                    if current_page is None:
                        current_page = int(progress * total_pages)

                    self.logger.info(f"准备保存到数据库: book_path={book_path_for_callback}, current_page={current_page}, total_pages={total_pages}")

                    # 保存阅读信息
                    success = bookmark_manager.save_reading_info(
                        book_path_for_callback,
                        current_page=current_page,
                        total_pages=total_pages,
                        reading_progress=progress,
                        scroll_top=scroll_top,
                        scroll_height=scroll_height,
                        word_count=word_count if word_count is not None else None
                    )

                    if success:
                        self.logger.info(f"保存浏览器阅读进度成功: {progress:.4f} ({progress*100:.2f}%), 位置: {scroll_top}px")
                    else:
                        self.logger.error(f"保存浏览器阅读进度失败: save_reading_info 返回 False")
                except Exception as e:
                    self.logger.error(f"保存阅读进度异常: {e}", exc_info=True)
            
            # 加载进度回调
            def on_progress_load() -> Optional[Dict[str, Any]]:
                """加载阅读进度"""
                try:
                    from src.core.bookmark import BookmarkManager
                    bookmark_manager = BookmarkManager()

                    reading_info = bookmark_manager.get_reading_info(book_path_for_callback)
                    self.logger.debug(f"从数据库获取到阅读信息: {reading_info}")

                    if reading_info:
                        progress = reading_info.get('progress', 0)
                        scroll_top = reading_info.get('scrollTop', 0)
                        scroll_height = reading_info.get('scrollHeight', 0)

                        # 只要有 progress 数据就返回，即使 scroll_top 为 0 也返回
                        if progress > 0:
                            self.logger.debug(f"返回阅读进度: {progress:.2f}%, 位置: {scroll_top}px, 高度: {scroll_height}px")
                            return {
                                'progress': progress,
                                'scrollTop': scroll_top,
                                'scrollHeight': scroll_height if scroll_height > 0 else 10000
                            }
                        else:
                            self.logger.debug("阅读进度为 0，不返回进度数据")
                    else:
                        self.logger.debug("数据库中没有阅读进度数据")
                except Exception as e:
                    self.logger.error(f"加载阅读进度失败: {e}")

                return None
            
            # 使用自定义浏览器阅读器打开，支持进度同步
            success, message = BrowserReader.open_book_in_browser(
                book_path,
                on_progress_save=on_progress_save,
                on_progress_load=on_progress_load
            )
            
            if success:
                self.notify(message, severity="information")
            else:
                self.notify(message, severity="error")
            
        except Exception as e:
            self.logger.error(f"浏览器打开书籍失败: {e}")
            self.notify(f"浏览器打开书籍失败: {e}", severity="error")
    
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
                            # 清空缓存以强制重新加载
                            self.clear_cache()
                            # 设置一个特殊的搜索参数，强制_load_books认为搜索条件已改变
                            self._last_search_params = "__force_reload__"
                            # 刷新书库内存缓存和书架列表（保持当前搜索条件）
                            self.bookshelf._load_books()
                            self._load_books(
                                search_keyword=self._search_keyword,
                                search_format=self._search_format,
                                search_author=self._search_author,
                                from_search=self._search_keyword != "" or self._search_format != "all" or self._search_author != "all"
                            )
                            # 发送书架刷新消息，通知 FileExplorerScreen 更新
                            try:
                                self.app.push_screen(RefreshBookshelfMessage())
                                logger.info("已发送书架刷新消息（删除了 1 本书籍）")
                            except Exception as e:
                                logger.error(f"发送书架刷新消息失败: {e}")
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
    
    def on_data_table_row_selected(self, event) -> None:
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
        # 只在当前屏幕是活动屏幕时才处理快捷键,避免 ModalScreen 打开时的事件穿透
        if self.app.screen is not self:
            return

        table = self.query_one("#books-table", DataTable)
        
        if event.key == "s":
            # S键搜索
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._show_search_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_search"), severity="warning")
            event.prevent_default()
            event.stop()
        elif event.key == "r":
            # R键排序
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._show_sort_menu()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_sort"), severity="warning")
            event.prevent_default()
            event.stop()
        elif event.key == "l":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.delete_book"):
                self._show_batch_ops_menu()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_opts"), severity="warning")
            event.prevent_default()
            event.stop()
        elif event.key == "a":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.add_book"):
                self._show_add_book_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_add_books"), severity="warning")
            event.prevent_default()
            event.stop()
        elif event.key == "d":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.scan_directory"):
                self._show_scan_directory_dialog()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_scan_directory"), severity="warning")
            event.prevent_default()
            event.stop()
        elif event.key == "g":
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.get_books"):
                self._get_books()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_get_books"), severity="warning")
            event.prevent_default()
            event.stop()
        elif event.key == "f":
            # F键刷新书架
            if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                self._refresh_bookshelf()
            else:
                self.notify(get_global_i18n().t("bookshelf.np_refresh"), severity="warning")
            event.prevent_default()
            event.stop()
        elif event.key == "escape" or event.key == "q":
            # ESC键或Q键返回（仅一次 pop，并停止冒泡）
            self.app.pop_screen()
            event.stop()
        elif event.key == "y":
            # Y键复制当前焦点书籍标题
            self._copy_focused_book_title()
            event.prevent_default()
            event.stop()
        
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            table = self.query_one("#books-table", DataTable)
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
            table = self.query_one("#books-table", DataTable)
            if table.cursor_row == 0 and self._current_page > 1:
                self._go_to_prev_page()
                # 将光标移动到新页面的最后一行
                last_row_index = len(table.rows) - 1
                table.move_cursor(row=last_row_index, column=0)  # 直接移动到最后一行第一列
                event.prevent_default()
                event.stop()
                return

        # 方向键翻页功能（在N/P键之前检查，确保优先处理）
        elif event.key == "n":
            # N键下一页
            self._go_to_next_page()
            event.prevent_default()
        elif event.key == "p":
            # P键上一页
            self._go_to_prev_page()
            event.prevent_default()
        elif event.key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            # 数字键1-9：打开对应序号的书籍, 0: 打开第10个书籍
            book_key = "10" if event.key == "0" else event.key
            if book_key in self._book_index_mapping:
                book_path = self._book_index_mapping[book_key]
                display_key = "0" if book_key == "10" else book_key
                self.logger.info(f"按数字键 {display_key} 打开书籍: {book_path}")
                # 使用备用方法打开书籍
                if getattr(self.app, "has_permission", lambda k: True)("bookshelf.read"):
                    self._open_book_fallback(book_path)
                else:
                    self.notify(get_global_i18n().t("bookshelf.np_read"), severity="warning")
                event.prevent_default()
            else:
                # 如果该序号没有对应的书籍，显示提示
                display_key = "0" if book_key == "10" else book_key
                self.notify(
                    get_global_i18n().t("bookshelf.no_book_position", book_index=display_key),
                    severity="warning"
                )
                event.prevent_default()
        
        
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
                # 保存排序配置
                self._sort_column = result["sort_key"]
                self._sort_reverse = result["reverse"]

                # 对当前书籍列表进行排序（保持搜索条件）
                # 核心概念：阅读进度 100% 的永远在最后面，无论什么排序方式
                not_completed_books = []
                completed_books = []

                for book in self._all_books:
                    reading_info = self.bookshelf._reading_info_cache.get(book.path, {})
                    progress = reading_info.get('reading_progress', 0)
                    if progress >= 1.0:
                        completed_books.append(book)
                    else:
                        not_completed_books.append(book)

                self.logger.debug(f"排序前 - 未完成: {len(not_completed_books)}, 已完成: {len(completed_books)}")

                # 预先获取阅读信息
                reading_info_cache = {}
                for book in not_completed_books + completed_books:
                    reading_info = self.bookshelf.get_book_reading_info(book.path)
                    reading_info_cache[book.path] = reading_info

                def get_sort_key(book):
                    return self._get_sort_key_with_cache(book, self._sort_column, reading_info_cache)

                not_completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)
                completed_books.sort(key=get_sort_key, reverse=self._sort_reverse)

                # 合并：未完成在前，已完成在后
                sorted_books = not_completed_books + completed_books

                self.logger.debug(f"排序后 - 总计: {len(sorted_books)}, 排序字段: {self._sort_column}, 倒序: {self._sort_reverse}")
                if not_completed_books:
                    self.logger.debug(f"未完成前3本: {[b.title[:15] for b in not_completed_books[:3]]}")
                if completed_books:
                    self.logger.debug(f"已完成前3本: {[b.title[:15] for b in completed_books[:3]]}")

                # 更新当前书籍列表
                self._all_books = sorted_books

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
                    # 数据库中存储的是小数(0-1),需要乘以100转换为百分比显示
                    progress = reading_info.get('reading_progress', 0) * 100

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

                # 重新计算分页信息
                self._total_pages = max(1, (len(self._all_books) + self._books_per_page - 1) // self._books_per_page)
                # 回到第一页
                self._current_page = 1

                # 更新分页控件状态
                self._update_pagination_controls()

                # 将字段名映射到翻译文本
                sort_key_translations = {
                    "title": get_global_i18n().t("common.book_name"),
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
                # 重新加载书籍数据（保持当前搜索条件）
                self._load_books(
                    search_keyword=self._search_keyword,
                    search_format=self._search_format,
                    search_author=self._search_author,
                    from_search=self._search_keyword != "" or self._search_format != "all" or self._search_author != "all"
                )
                self.notify(
                    get_global_i18n().t("batch_ops.operation_completed"),
                    severity="information"
                )
        
        # 显示批量操作对话框
        dialog = BatchOpsDialog(self.theme_manager, self.bookshelf)
        self.app.push_screen(dialog, handle_batch_ops)
        
    def _show_add_book_dialog(self) -> None:
        """显示添加书籍对话框 - 使用文件资源管理器屏幕"""
        def handle_add_book_result(result: Optional[str | List[str]]) -> None:
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
                            self._load_books(
                                search_keyword=self._search_keyword,
                                search_format=self._search_format,
                                search_author=self._search_author,
                                from_search=self._search_keyword != "" or self._search_format != "all" or self._search_author != "all"
                            )
                            # 发送书架刷新消息，通知 FileExplorerScreen 更新
                            try:
                                self.app.push_screen(RefreshBookshelfMessage())
                                logger.info(f"已发送书架刷新消息（添加了 {added_count} 本书籍）")
                            except Exception as e:
                                logger.error(f"发送书架刷新消息失败: {e}")
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
                            self._load_books(
                                search_keyword=self._search_keyword,
                                search_format=self._search_format,
                                search_author=self._search_author,
                                from_search=self._search_keyword != "" or self._search_format != "all" or self._search_author != "all"
                            )
                            # 发送书架刷新消息，通知 FileExplorerScreen 更新
                            try:
                                self.app.push_screen(RefreshBookshelfMessage())
                                logger.info("已发送书架刷新消息（添加了 1 本书籍）")
                            except Exception as e:
                                logger.error(f"发送书架刷新消息失败: {e}")
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
                            self._load_books(
                                search_keyword=self._search_keyword,
                                search_format=self._search_format,
                                search_author=self._search_author,
                                from_search=self._search_keyword != "" or self._search_format != "all" or self._search_author != "all"
                            )
                            # 发送书架刷新消息，通知 FileExplorerScreen 更新
                            try:
                                self.app.push_screen(RefreshBookshelfMessage())
                                logger.info(f"已发送书架刷新消息（扫描添加了 {added_count} 本书籍）")
                            except Exception as e:
                                logger.error(f"发送书架刷新消息失败: {e}")
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
    
    def _show_loading_animation(self, message: Optional[str] = None, progress: Optional[float] = None) -> None:
        """显示加载动画
        
        Args:
            message: 加载消息
            progress: 加载进度 (0-100)
        """
        if message is None:
            message = get_global_i18n().t("common.on_action")
        
        try:
            # 显示详细的加载状态
            progress_text = f"{progress:.1f}%" if progress is not None else "0%"
            logger.info(f"🔄 开始加载: {message} - 进度: {progress_text}")
            
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

            # 更新状态栏显示加载状态和进度
            try:
                stats_label = self.query_one("#books-stats-label", Label)
                progress_text = f" ({progress:.1f}%)" if progress is not None else ""
                stats_label.update(f"🔄 {message}{progress_text}...")
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
        self._search_keyword = ""
        self._search_format = "all"
        self._search_author = "all"
        self.query_one("#sort-key-radio", Select).value = "last_read"
        self.query_one("#sort-order-radio", Select).value = "desc"
        self.query_one("#bookshelf-search-input", Input).value = ""
        self.query_one("#bookshelf-search-input", Input).placeholder = get_global_i18n().t("bookshelf.search_placeholder")
        self.query_one("#bookshelf-format-filter", Select).value = "all"
        self.query_one("#bookshelf-source-filter", Select).value = "all"
        # 重新加载书籍数据以应用清除的搜索条件
        self._load_books()

    def action_jump_to(self) -> None:
        self._show_jump_dialog()

    # 分页导航方法
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self._current_page != 1:
            self._show_loading_animation(get_global_i18n().t("bookshelf.page_first"), progress=0)
            self._current_page = 1
            self._load_books(self._search_keyword, self._search_format, self._search_author)
            self._hide_loading_animation()

    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self._current_page > 1:
            self._show_loading_animation(get_global_i18n().t("bookshelf.page_prev"), progress=0)
            self._current_page -= 1
            self._load_books(self._search_keyword, self._search_format, self._search_author)
            self._hide_loading_animation()

    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        if self._current_page < self._total_pages:
            self._show_loading_animation(get_global_i18n().t("bookshelf.page_next"), progress=0)
            self._current_page += 1
            self._load_books(self._search_keyword, self._search_format, self._search_author)
            self._hide_loading_animation()

    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        if self._current_page != self._total_pages:
            self._show_loading_animation(get_global_i18n().t("bookshelf.page_last"), progress=0)
            self._current_page = self._total_pages
            self._load_books(self._search_keyword, self._search_format, self._search_author)
            self._hide_loading_animation()

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
                            self._load_books(self._search_keyword, self._search_format, self._search_author)
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
            self.logger.error(f"更新分页按钮状态失败: {e}")

    def _get_cache_key(self) -> str:
        """生成缓存键"""
        return f"{self._search_keyword}_{self._search_format}_{self._search_author}"

    def _load_books_from_cache(self, cache_key: str) -> Optional[List[Book]]:
        """从缓存加载书籍数据"""
        import time
        import sys
        current_time = time.time()
        
        # 检查缓存是否有效
        if cache_key in self._books_cache:
            # 检查缓存是否过期
            if current_time - self._cache_timestamp < self._cache_ttl:
                self._cache_hits += 1
                self.logger.debug(f"缓存命中: {cache_key}, 命中率: {self._get_cache_hit_rate():.2%}")
                return self._books_cache[cache_key]
            else:
                # 缓存过期，移除
                del self._books_cache[cache_key]
                self.logger.debug(f"缓存过期已移除: {cache_key}")
        
        self._cache_misses += 1
        self.logger.debug(f"缓存未命中: {cache_key}, 命中率: {self._get_cache_hit_rate():.2%}")
        return None

    def _save_books_to_cache(self, cache_key: str, books: List[Book]) -> None:
        """保存书籍数据到缓存"""
        import time
        import sys
        
        # 检查内存使用情况，如果超过限制则自动清理
        if self._check_cache_memory_limit() and self._books_cache:
            self.auto_clean_cache(target_memory_mb=50.0)
            
            # 如果清理后仍然超过限制，使用淘汰策略
            if self._check_cache_memory_limit():
                self._evict_cache_entries()
        
        # 保存到缓存
        self._books_cache[cache_key] = books
        self._cache_timestamp = time.time()
        self._last_cache_key = cache_key
        self.logger.debug(f"缓存已保存: {cache_key}, 缓存大小: {len(self._books_cache)}")
        
        # 记录缓存统计
        stats = self.get_cache_stats()
        if stats['memory_usage_mb'] > 10.0:
            self.logger.info(f"缓存统计: {stats['total_entries']} 个条目, {stats['memory_usage_mb']:.2f}MB, 命中率: {stats['hit_rate']:.2%}")
    
    def _get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / total if total > 0 else 0.0
    
    def _check_cache_memory_limit(self) -> bool:
        """检查是否超过内存限制"""
        import sys
        # 估算缓存占用的内存
        cache_size = sum(sys.getsizeof(book_list) for book_list in self._books_cache.values())
        return cache_size > self._cache_memory_limit or len(self._books_cache) > self._cache_max_size
    
    def _evict_cache_entries(self) -> None:
        """根据淘汰策略移除缓存条目"""
        if self._cache_eviction_policy == "lru":
            # LRU策略：移除最久未使用的缓存
            # 这里简化实现，移除最早的缓存条目
            if self._books_cache:
                oldest_key = next(iter(self._books_cache.keys()))
                del self._books_cache[oldest_key]
                self.logger.debug(f"LRU缓存淘汰: {oldest_key}")
        elif self._cache_eviction_policy == "random":
            # 随机移除一个缓存条目
            import random
            if self._books_cache:
                random_key = random.choice(list(self._books_cache.keys()))
                del self._books_cache[random_key]
                self.logger.debug(f"随机缓存淘汰: {random_key}")
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._books_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self.logger.debug("缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        import sys
        cache_size = sum(sys.getsizeof(book_list) for book_list in self._books_cache.values())
        return {
            "total_entries": len(self._books_cache),
            "memory_usage_bytes": cache_size,
            "memory_usage_mb": cache_size / (1024 * 1024),
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": self._get_cache_hit_rate(),
            "max_size": self._cache_max_size,
            "memory_limit_mb": self._cache_memory_limit / (1024 * 1024),
            "eviction_policy": self._cache_eviction_policy
        }
    
    def auto_clean_cache(self, target_memory_mb: float = 50.0) -> None:
        """自动清理缓存到目标内存大小"""
        import sys
        current_memory = sum(sys.getsizeof(book_list) for book_list in self._books_cache.values()) / (1024 * 1024)
        
        if current_memory <= target_memory_mb:
            self.logger.debug(f"当前缓存内存使用: {current_memory:.2f}MB, 无需清理")
            return
        
        target_bytes = target_memory_mb * 1024 * 1024
        entries_to_remove = []
        current_total = 0
        
        # 计算需要移除的缓存条目
        for key, book_list in self._books_cache.items():
            entry_size = sys.getsizeof(book_list)
            if current_total + entry_size > target_bytes:
                entries_to_remove.append(key)
            else:
                current_total += entry_size
        
        # 移除超出限制的缓存
        for key in entries_to_remove:
            del self._books_cache[key]
        
        self.logger.debug(f"自动清理缓存: 移除 {len(entries_to_remove)} 个条目, 内存从 {current_memory:.2f}MB 降至 {current_total / (1024 * 1024):.2f}MB")