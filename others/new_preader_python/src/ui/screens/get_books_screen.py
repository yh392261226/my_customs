"""
获取书籍屏幕
"""

from ast import Yield
from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Label, Input, Select, Header, Footer, DataTable
from textual.widgets import DataTable
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events, on

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager
from src.config.config_manager import ConfigManager
import platform, os, subprocess, asyncio
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

logger = get_logger(__name__)

class GetBooksScreen(Screen[None]):

    # 使用 Textual BINDINGS 进行快捷键绑定
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("N", "open_novel_sites", get_global_i18n().t('get_books.shortcut_n')),
        ("P", "open_proxy_list", get_global_i18n().t('get_books.shortcut_p')),
        ("o", "open_books_folder", get_global_i18n().t('get_books.shortcut_o')),
        ("enter", "open_selected", get_global_i18n().t('get_books.shortcut_enter')),
        ("space", "open_selected", get_global_i18n().t('get_books.shortcut_space')),
        ("p", "prev_page", get_global_i18n().t('crawler.shortcut_p')),
        ("n", "next_page", get_global_i18n().t('crawler.shortcut_n')),
        ("x", "clear_search_params", get_global_i18n().t('crawler.clear_search_params')),
        ("j", "jump_to", get_global_i18n().t('bookshelf.jump_to')),
    ]


    
    # 加载CSS样式
    CSS_PATH = "../styles/get_books_screen_overrides.tcss"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化获取书籍屏幕
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        try:
            self.title = get_global_i18n().t('get_books.title')
        except RuntimeError:
            # 如果全局i18n未初始化，使用默认标题
            self.title = "获取书籍"
        self.theme_manager = theme_manager
        self.database_manager = DatabaseManager()
        self.novel_sites = []  # 书籍网站列表
        self.proxy_settings = {}  # 代理设置
        # 数字快捷键（1-9）对应的行索引映射
        self._shortcut_index_map: Dict[str, int] = {}
        
        # 分页相关属性
        self._current_page = 1
        self._sites_per_page = 10
        self._total_pages = 1
        self._all_sites: List[Dict[str, Any]] = []
        
        # 搜索相关属性
        self._search_keyword = ""
        self._search_parser = "all"
        self._search_proxy_enabled = "all"
        self._search_status = "all"
        self._search_rating = "all"
        
        # 排序相关属性
        self._sort_column: Optional[str] = None
        self._sort_reverse: bool = False
        
        # 按钮点击标志
        self._button_clicked = False
        
    def compose(self) -> ComposeResult:
        """
        组合获取书籍屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Grid(
                # 顶部区域：描述、按钮、搜索栏
                Vertical(
                    # Label(get_global_i18n().t('get_books.title'), id="get-books-title", classes="section-title"),
                    Label(get_global_i18n().t('get_books.description'), id="get-books-description", classes="section-title"),
                    
                    # 功能按钮区域
                    Horizontal(
                        Button(get_global_i18n().t('get_books.novel_sites'), id="novel-sites-btn", classes="btn"),
                        Button(get_global_i18n().t('get_books.proxy_settings'), id="proxy-settings-btn", classes="btn"),
                        Button(get_global_i18n().t('get_books.check_all'), id="check-all-sites-btn", classes="btn"),
                        Button(get_global_i18n().t('get_books.clear_all_invalid'), id="clear-all-invalid-btn", classes="btn", variant="error"),
                        Button(get_global_i18n().t('get_books.shortcut_o'), id="open-books-folder-btn", classes="btn"),
                        Button(get_global_i18n().t('get_books.back'), id="back-btn", classes="btn"),
                        id="get-books-buttons",
                        classes="btn-row"
                    ),
                    
                    # 搜索栏
                    Horizontal(
                        Input(
                            placeholder=get_global_i18n().t('search.site_placeholder'),
                            id="novel-sites-search-input",
                            classes="novel-sites-search-input"
                        ),
                        Select(
                            id="novel-sites-parser-filter",
                            options=[
                                (get_global_i18n().t('search.all_parsers'), "all"),
                                ("V2 Parser", "v2"),
                                ("Legacy Parser", "legacy")
                            ],
                            value="all",
                            prompt=get_global_i18n().t('search.select_parser_prompt'),
                            classes="novel-sites-search-select"
                        ),
                        Select(
                            id="novel-sites-proxy-filter",
                            options=[
                                (get_global_i18n().t('search.all_proxy'), "all"),
                                (get_global_i18n().t('common.yes'), "yes"),
                                (get_global_i18n().t('common.no'), "no")
                            ],
                            value="all",
                            prompt=get_global_i18n().t('search.select_proxy_prompt'),
                            classes="novel-sites-search-select"
                        ),
                        Select(
                            id="novel-sites-status-filter",
                            options=[
                                (get_global_i18n().t('search.all_status'), "all"),
                                (get_global_i18n().t('crawler.status_success'), "normal"),
                                (get_global_i18n().t('crawler.status_failed'), "abnormal")
                            ],
                            value="all",
                            prompt=get_global_i18n().t('search.select_status_prompt'),
                            classes="novel-sites-search-select"
                        ),
                        Select(
                            id="novel-sites-rating-filter",
                            options=[
                                (get_global_i18n().t('search.all_ratings'), "all"),
                                ("★★★★★", "5"),
                                ("★★★★☆", "4"),
                                ("★★★☆☆", "3"),
                                ("★★☆☆☆", "2"),
                                ("★☆☆☆☆", "1"),
                                ("☆☆☆☆☆", "0")
                            ],
                            value="all",
                            prompt=get_global_i18n().t('search.select_rating_prompt'),
                            classes="novel-sites-search-select"
                        ),
                        id="novel-sites-search-bar",
                        classes="novel-sites-search-bar"
                    ),
                    id="get-books-header",
                    classes="get-books-header-vertical"
                ),
                
                # 中间区域：书籍网站列表
                Vertical(
                    DataTable(id="novel-sites-table"),
                    id="novel-sites-preview"
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
                
                # 底部区域2：代理设置预览
                Vertical(
                    Vertical(
                    Label(get_global_i18n().t('get_books.novel_sites_list'), id="novel-sites-list-title"),
                    ),
                    Vertical(
                    Label(get_global_i18n().t('get_books.proxy_status'), id="proxy-status-title"),
                    Label("", id="proxy-status-info"),
                    id="proxy-settings-preview"
                    )
                ),
                
                id="get-books-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 先应用样式隔离，防止本屏样式污染其他屏幕
        try:
            apply_universal_style_isolation(self)
        except Exception:
            pass
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 初始化数据表
        table = self.query_one("#novel-sites-table", DataTable)
        
        # 清除现有列，重新添加
        table.clear(columns=True)
        
        # 添加列定义
        table.add_column(get_global_i18n().t('get_books.sequence'), key="sequence")
        table.add_column(get_global_i18n().t('get_books.site_name'), key="name")
        table.add_column(get_global_i18n().t('get_books.site_url'), key="url")
        table.add_column(get_global_i18n().t('get_books.status'), key="status")
        table.add_column(get_global_i18n().t('get_books.proxy_enabled'), key="proxy_enabled")
        table.add_column(get_global_i18n().t('get_books.parser'), key="parser")
        table.add_column(get_global_i18n().t('get_books.tags'), key="tags")
        table.add_column(get_global_i18n().t('get_books.rating'), key="rating")
        table.add_column(get_global_i18n().t('get_books.books_count'), key="books_count")
        table.add_column(get_global_i18n().t('get_books.check'), key="check")
        table.add_column(get_global_i18n().t('get_books.enter'), key="enter")
        
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        # 启用单元格选择功能，以便点击按钮
        table.cursor_type = "cell"
        logger.debug(f"表格光标类型已设置为: {table.cursor_type}")
        # 强制更新表格以应用单元格模式
        table.clear()

        # 加载书籍网站数据
        self._load_novel_sites()
        self._load_proxy_settings()
        
        # 检查按钮权限并禁用/启用按钮
        self._check_button_permissions()
        
        # 初始化分页按钮状态
        self._update_pagination_buttons()
        
        # 聚焦表格以接收键盘事件
        try:
            table = self.query_one("#novel-sites-table", DataTable)
            table.focus()
            # 确保表格的光标类型设置为单元格模式
            table.cursor_type = "cell"
            # 确保表格能够接收键盘事件
            table.can_focus = True
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        """屏幕恢复时的回调（从其他屏幕返回时调用）"""
        # 重新加载代理设置，确保显示最新状态
        self._load_proxy_settings()
        # 重置排序状态并重新加载数据（使用保存的搜索参数）
        self._sort_column = None
        self._sort_reverse = False
        self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)
        
    def on_unmount(self) -> None:
        """屏幕卸载时移除样式隔离，避免残留影响其他屏幕"""
        try:
            remove_universal_style_isolation(self)
        except Exception:
            pass
    
    def _get_rating_display(self, rating: int) -> str:
        """
        根据星级评分生成显示字符串
        
        Args:
            rating: 星级评分 (0-5)
            
        Returns:
            str: 星级显示字符串，如 "☆☆☆☆☆" 或 "★★★★★"
        """
        # 确保评分在0-5范围内
        rating = max(0, min(5, rating))
        
        # 使用实心星星表示评分，空心星星表示剩余
        filled_stars = "★" * rating
        empty_stars = "☆" * (5 - rating)
        
        return f"{filled_stars}{empty_stars}"

    def _focus_search_input(self) -> None:
        """将焦点设置回搜索框"""
        try:
            search_input = self.query_one("#novel-sites-search-input", Input)
            search_input.focus()
        except Exception as e:
            logger.debug(f"设置搜索框焦点失败: {e}")

    def _load_novel_sites(self, search_keyword: str = "", search_parser: str = "all", search_proxy_enabled: str = "all", search_status: str = "all", search_rating: str = "all", from_search: bool = False) -> None:
        """加载书籍网站数据

        Args:
            search_keyword: 搜索关键词
            search_parser: 解析器筛选
            search_proxy_enabled: 代理启用筛选
            search_status: 状态筛选
            search_rating: 评星筛选
            from_search: 是否来自搜索操作
        """
        # 如果没有排序条件，从数据库加载数据；否则使用已有数据
        if self._sort_column is None:
            # 从数据库加载书籍网站数据
            all_sites = self.database_manager.get_novel_sites()
        else:
            # 使用已有的数据（已经排序过的）
            all_sites = self._all_sites

        # 应用搜索筛选
        filtered_sites = []
        for site in all_sites:
            # 关键词搜索
            keyword_match = True
            if search_keyword:
                keyword_match = (
                    search_keyword.lower() in site.get("name", "").lower() or
                    search_keyword.lower() in site.get("url", "").lower() or
                    search_keyword.lower() in site.get("parser", "").lower()
                )

            # 解析器筛选
            parser_match = True
            if search_parser != "all":
                parser_value = site.get("parser", "").lower()
                if search_parser == "v2":
                    parser_match = parser_value.endswith("_v2")
                elif search_parser == "legacy":
                    parser_match = not parser_value.endswith("_v2")
                else:
                    parser_match = parser_value == search_parser.lower()

            # 代理启用筛选
            proxy_match = True
            if search_proxy_enabled != "all":
                proxy_enabled = site.get("proxy_enabled", False)
                if search_proxy_enabled == "yes":
                    proxy_match = proxy_enabled
                else:
                    proxy_match = not proxy_enabled

            # 状态筛选
            status_match = True
            if search_status != "all":
                site_status = site.get("status", "正常")
                if search_status == "normal":
                    status_match = site_status == "正常"
                elif search_status == "abnormal":
                    status_match = site_status != "正常"

            # 评星筛选
            rating_match = True
            if search_rating != "all":
                site_rating = site.get("rating", 0)
                rating_match = str(site_rating) == search_rating

            if keyword_match and parser_match and proxy_match and status_match and rating_match:
                filtered_sites.append(site)
        
        # 数据库已经按照 rating 降序排序，无需再次排序
        self._all_sites = filtered_sites
        
        # 计算分页
        self._total_pages = max(1, (len(self._all_sites) + self._sites_per_page - 1) // self._sites_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 获取当前页的数据
        start_index = (self._current_page - 1) * self._sites_per_page
        end_index = min(start_index + self._sites_per_page, len(self._all_sites))
        current_page_sites = self._all_sites[start_index:end_index]
        
        # 更新数据表
        table = self.query_one("#novel-sites-table", DataTable)
        
        # 准备虚拟滚动数据
        virtual_data = []
        for index, site in enumerate(current_page_sites):
            global_index = start_index + index + 1
            proxy_status = get_global_i18n().t('common.yes') if site.get("proxy_enabled", False) else get_global_i18n().t('common.no')
            rating = site.get("rating", 2)  # 默认2星
            rating_display = self._get_rating_display(rating)
            
            # 获取该网站爬取成功的书籍数量
            books_count = self.database_manager.get_crawled_books_count(site.get("id", 0))
            
            # 获取网站状态，默认为正常
            site_status = site.get("status", "正常")
            # 根据状态显示不同的emoji
            status_display = "✅" if site_status == "正常" else "❌"
            
            # 获取网站标签
            tags = site.get("tags", "")
            tags_display = tags if tags else "-"
            
            row_data = {
                "sequence": str(global_index),
                "name": site.get("name", ""),
                "url": site.get("url", ""),
                "status": status_display,
                "proxy_enabled": proxy_status,
                "parser": site.get("parser", ""),
                "tags": tags_display,
                "rating": rating_display,
                "books_count": str(books_count),
                "check": "🔍 " + get_global_i18n().t('get_books.check'),
                "enter": "➤ " + get_global_i18n().t('get_books.enter'),
                "_row_key": f"{site.get('id', '')}_{global_index}",
                "_global_index": global_index
            }
            virtual_data.append(row_data)
        
        # 填充表格数据
        table.clear()
        for row_data in virtual_data:
            table.add_row(
                row_data["sequence"],
                row_data["name"],
                row_data["url"],
                row_data["status"],
                row_data["proxy_enabled"],
                row_data["parser"],
                row_data["tags"],
                row_data["rating"],
                row_data["books_count"],
                row_data["check"],
                row_data["enter"]
            )
        
        # 确保光标位置正确设置
        try:
            if len(virtual_data) > 0:
                # DataTable的cursor_row是只读属性，不能直接设置
                # 光标位置会在表格获得焦点时自动设置
                pass
        except Exception as e:
            logger.debug(f"设置光标位置失败: {e}")
        
        # 再次确保表格是单元格模式
        try:
            table = self.query_one("#novel-sites-table", DataTable)
            table.cursor_type = "cell"
            # 只有在不是来自搜索时才设置表格焦点
            if not from_search:
                table.focus()
            # 刷新表格以应用设置
            table.refresh()
        except Exception as e:
            logger.debug(f"设置单元格模式失败: {e}")
        
        # 为数字快捷键1-9和0（第10项）建立行索引映射
        try:
            # 1-9键映射到前9项
            self._shortcut_index_map = {str(i + 1): i for i in range(min(9, len(current_page_sites)))}
            # 如果有第10项，将0键映射到索引9
            if len(current_page_sites) >= 10:
                self._shortcut_index_map["0"] = 9
        except Exception:
            self._shortcut_index_map = {}
            
        # 更新分页信息
        self._update_pagination_info()
        self._update_pagination_buttons()

    def _update_pagination_info(self) -> None:
        """更新分页信息显示"""
        try:
            total_sites = len(self._all_sites)
            status_label = self.query_one("#novel-sites-list-title", Label)
            status_text = f"{get_global_i18n().t('get_books.novel_sites_list')} - {get_global_i18n().t('page_info', total=total_sites, current=self._current_page, pages=self._total_pages)}"
            status_label.update(status_text)
            
            # 调试信息
            logger.info(f"分页信息更新: 总网站数={total_sites}, 当前页={self._current_page}, 总页数={self._total_pages}")
        except Exception as e:
            logger.error(f"更新分页信息失败: {e}")

    def _update_pagination_buttons(self) -> None:
        """更新分页按钮状态"""
        try:
            page_label = self.query_one("#page-info", Label)
            page_label.update(f"{self._current_page}/{self._total_pages}")
            
            # 更新分页按钮状态
            first_btn = self.query_one("#first-page-btn", Button)
            prev_btn = self.query_one("#prev-page-btn", Button) 
            next_btn = self.query_one("#next-page-btn", Button)
            last_btn = self.query_one("#last-page-btn", Button)
            
            # 设置按钮的可见性和禁用状态
            first_btn.disabled = self._current_page <= 1
            prev_btn.disabled = self._current_page <= 1
            next_btn.disabled = self._current_page >= self._total_pages
            last_btn.disabled = self._current_page >= self._total_pages
            
            # # 确保按钮始终可见
            # first_btn.display = True
            # prev_btn.display = True
            # next_btn.display = True
            # last_btn.display = True
            
            # 调试信息
            logger.debug(f"分页状态: 当前页={self._current_page}, 总页数={self._total_pages}")
            logger.debug(f"下一页按钮禁用状态: {next_btn.disabled}")
            logger.debug(f"尾页按钮禁用状态: {last_btn.disabled}")
        except Exception as e:
            logger.error(f"更新分页按钮状态失败: {e}")

    def _perform_search(self) -> None:
        """执行搜索操作"""
        # 获取搜索输入框和筛选器的值
        search_input = self.query_one("#novel-sites-search-input", Input)
        parser_filter = self.query_one("#novel-sites-parser-filter", Select)
        proxy_filter = self.query_one("#novel-sites-proxy-filter", Select)
        status_filter = self.query_one("#novel-sites-status-filter", Select)
        rating_filter = self.query_one("#novel-sites-rating-filter", Select)

        # 更新搜索状态
        self._search_keyword = search_input.value or ""

        # 处理下拉框值，确保正确处理NoSelection对象和_BLANK值
        parser_value = parser_filter.value
        if (parser_value is None or
            parser_value == "" or
            (hasattr(parser_value, 'value') and getattr(parser_value, 'value', '') == "") or
            (hasattr(parser_value, 'is_blank') and getattr(parser_value, 'is_blank', False)) or
            str(parser_value) == 'Select.BLANK'):
            self._search_parser = "all"
        else:
            self._search_parser = str(parser_value) if parser_value else "all"

        proxy_value = proxy_filter.value
        if (proxy_value is None or
            proxy_value == "" or
            (hasattr(proxy_value, 'value') and getattr(proxy_value, 'value', '') == "") or
            (hasattr(proxy_value, 'is_blank') and getattr(proxy_value, 'is_blank', False)) or
            str(proxy_value) == 'Select.BLANK'):
            self._search_proxy_enabled = "all"
        else:
            self._search_proxy_enabled = str(proxy_value) if proxy_value else "all"

        # 状态筛选
        status_value = status_filter.value
        if (status_value is None or
            status_value == "" or
            (hasattr(status_value, 'value') and getattr(status_value, 'value', '') == "") or
            (hasattr(status_value, 'is_blank') and getattr(status_value, 'is_blank', False)) or
            str(status_value) == 'Select.BLANK'):
            self._search_status = "all"
        else:
            self._search_status = str(status_value) if status_value else "all"

        # 评星筛选
        rating_value = rating_filter.value
        if (rating_value is None or
            rating_value == "" or
            (hasattr(rating_value, 'value') and getattr(rating_value, 'value', '') == "") or
            (hasattr(rating_value, 'is_blank') and getattr(rating_value, 'is_blank', False)) or
            str(rating_value) == 'Select.BLANK'):
            self._search_rating = "all"
        else:
            self._search_rating = str(rating_value) if rating_value else "all"

        # 重置到第一页
        self._current_page = 1

        # 重置排序状态
        self._sort_column = None
        self._sort_reverse = False

        # 重新加载数据
        self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating, from_search=True)

    # 分页导航方法
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self._current_page != 1:
            self._current_page = 1
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)

    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)

    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)

    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)

    def _sort_sites(self, column_key: str, reverse: bool) -> None:
        """根据指定列对网站进行排序

        Args:
            column_key: 排序的列键
            reverse: 是否倒序
        """
        try:
            def get_sort_key(site: Dict[str, Any]) -> Any:
                """获取排序键值"""
                if column_key == "name":
                    return site.get("name", "")
                elif column_key == "url":
                    return site.get("url", "")
                elif column_key == "status":
                    return site.get("status", "")
                elif column_key == "rating":
                    return site.get("rating", 0)
                elif column_key == "proxy_enabled":
                    return site.get("proxy_enabled", False)
                elif column_key == "parser":
                    return site.get("parser", "")
                elif column_key == "tags":
                    return site.get("tags", "")
                elif column_key == "books_count":
                    return self.database_manager.get_crawled_books_count(site.get("id", 0))
                return None

            self._all_sites.sort(key=get_sort_key, reverse=reverse)

        except Exception as e:
            logger.error(f"排序失败: {e}")

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
                            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)
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

    def _check_site_status(self, site: Dict[str, Any]) -> None:
        """检测网站状态"""
        try:
            site_id = site.get("id")
            site_url = site.get("url", "")
            site_name = site.get("name", "未知网站")
            
            if not site_id or not site_url:
                self.notify(get_global_i18n().t('get_books.site_info_incomplete') + " - " + get_global_i18n().t('get_books.cannot_check_site'), severity="error")
                return
                
            # 显示检测中状态
            self.notify(get_global_i18n().t('get_books.checking_site', name=site_name), severity="information")
            
            # 执行网站检测
            result = self.database_manager.check_site_availability(site_url)
            
            # 更新数据库中的状态
            self.database_manager.update_novel_site_status(site_id, result["status"])

            # 重新加载数据表，显示最新状态
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)
            
            # 显示检测结果
            self.notify(result["message"], severity="success" if result["status"] == "正常" else "warning")
            
        except Exception as e:
            logger.error(f"检测网站状态失败: {e}")
            self.notify(get_global_i18n().t('get_books.check_site_status_failed', error=str(e)), severity="error")
    
    async def _check_all_sites_status(self) -> None:
        """异步一键检测所有网站状态"""
        import concurrent.futures
        
        try:
            # 获取所有书籍网站
            all_sites = self.database_manager.get_novel_sites()
            
            if not all_sites:
                self.app.call_later(self.notify, get_global_i18n().t('get_books.no_sites_found'), severity="warning")
                return
            
            # 统计检测结果
            total_sites = len(all_sites)
            success_count = 0
            failed_count = 0
            
            # 创建一个进度跟踪变量
            checked_count = 0
            
            # 创建线程池执行器，用于运行同步的网站检测
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # 逐个检测网站状态
                for site in all_sites:
                    try:
                        site_id = site.get("id")
                        site_url = site.get("url", "")
                        site_name = site.get("name", "未知网站")
                        
                        if not site_id or not site_url:
                            logger.warning(f"网站信息不完整，跳过检测: {site_name}")
                            continue
                            
                        # 在线程池中执行网站检测，避免阻塞事件循环
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            executor, 
                            self.database_manager.check_site_availability, 
                            site_url
                        )
                        
                        # 更新数据库中的状态
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            executor, 
                            self.database_manager.update_novel_site_status, 
                            site_id, 
                            result["status"]
                        )
                        
                        # 统计结果
                        if result["status"] == "正常":
                            success_count += 1
                        else:
                            failed_count += 1
                        
                        # 增加已检测计数
                        checked_count += 1
                        
                        # 每检测完1个网站，更新一次界面（保持更好的响应性）
                        progress_message = get_global_i18n().t('get_books.checking_progress', count=checked_count, total=total_sites)
                        # 使用 app.call_later 来安全地更新UI
                        self.app.call_later(self.notify, progress_message, severity="information")
                        self.app.call_later(
                            self._load_novel_sites, 
                            self._search_keyword, 
                            self._search_parser, 
                            self._search_proxy_enabled
                        )
                        
                        # 让出控制权，确保事件循环有机会处理其他任务
                        await asyncio.sleep(0.01)

                    except Exception as e:
                        logger.error(f"检测网站 {site.get('name', '未知')} 状态失败: {e}")
                        failed_count += 1
                        checked_count += 1

            # 最终重新加载数据表，显示最新状态
            self.app.call_later(
                self._load_novel_sites,
                self._search_keyword,
                self._search_parser,
                self._search_proxy_enabled,
                self._search_status,
                self._search_rating
            )
            
            # 显示检测结果
            message = get_global_i18n().t('get_books.check_complete', success=success_count, failed=failed_count, total=total_sites)
            self.app.call_later(
                self.notify, 
                message, 
                severity="success" if failed_count == 0 else "warning"
            )
            
        except Exception as e:
            logger.error(f"一键检测所有网站状态失败: {e}")
            self.app.call_later(
                self.notify, 
                get_global_i18n().t('get_books.check_all_failed') + f": {str(e)}", 
                severity="error"
            )
    
    def _check_all_sites_status_async(self) -> None:
        """调用线程检测网站状态的方法"""
        # 显示开始检测的通知
        self.notify(get_global_i18n().t('get_books.checking_all'), severity="information")
        
        # 在后台线程中执行检测
        self.app.run_worker(self._check_all_sites_status, name="check-all-sites-worker")
    
    async def _yield_async(self) -> None:
        """异步让出控制权，确保界面不卡死"""
        # 在Textual中，使用sleep(0)可以立即让出控制权给事件循环
        await self.sleep(0)
    
    def _toggle_site_status(self, site: Dict[str, Any]) -> None:
        """切换网站状态（正常/异常）"""
        try:
            site_id = site.get("id")
            site_name = site.get("name", "未知网站")
            current_status = site.get("status", "正常")
            
            if not site_id:
                self.notify(get_global_i18n().t('get_books.site_info_incomplete') + " - " + get_global_i18n().t('get_books.cannot_switch_status'), severity="error")
                return
            
            # 切换状态
            new_status = "异常" if current_status == "正常" else "正常"
            
            # 更新数据库中的状态
            success = self.database_manager.update_novel_site_status(site_id, new_status)

            if success:
                # 重新加载数据表，显示最新状态
                self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)
                
                # 显示切换结果
                self.notify(get_global_i18n().t('get_books.toggle_site_status_failed', name=site_name) + " -> " + new_status, severity="success")
            else:
                self.notify(get_global_i18n().t('get_books.toggle_site_status_failed', name=site_name), severity="error")
            
        except Exception as e:
            logger.error(f"切换网站状态失败: {e}")
            self.notify(get_global_i18n().t('get_books.toggle_site_status_error', error=str(e)), severity="error")
    
    def _open_url_in_browser(self, url: str, site_name: str) -> None:
        """使用浏览器打开网站网址"""
        try:
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # 使用BrowserManager打开URL
            try:
                from src.utils.browser_manager import BrowserManager
                
                success = BrowserManager.open_url(url)
                if success:
                    browser_name = BrowserManager.get_default_browser()
                    self.notify(f"正在使用{browser_name}浏览器打开网站: {site_name}", severity="success")
                else:
                    # 如果BrowserManager失败，使用默认浏览器
                    import webbrowser
                    webbrowser.open(url)
                    self.notify(get_global_i18n().t('get_books.using_default_browser', name=site_name), severity="success")
            except Exception as e:
                # 如果BrowserManager失败，回退到默认浏览器
                import webbrowser
                webbrowser.open(url)
                self.notify(get_global_i18n().t('get_books.using_default_browser', name=site_name), severity="success")
                logger.warning(f"BrowserManager失败，使用默认浏览器: {e}")
                
        except Exception as e:
            logger.error(f"打开网址失败: {e}")
            self.notify(get_global_i18n().t('get_books.open_url_failed', error=str(e)), severity="error")
    
    def _load_proxy_settings(self) -> None:
        """加载代理设置"""
        # 从数据库加载代理设置
        proxies = self.database_manager.get_all_proxy_settings()
        enabled_proxy = next((proxy for proxy in proxies if proxy["enabled"]), None)
        
        # 更新代理状态显示
        status_label = self.query_one("#proxy-status-info", Label)
        if enabled_proxy:
            status_text = f"{get_global_i18n().t('get_books.proxy_enabled')}: {enabled_proxy.get('name', '未知')} ({enabled_proxy.get('host', '未知')}:{enabled_proxy.get('port', '未知')})"
        else:
            status_text = get_global_i18n().t('get_books.proxy_disabled')
        status_label.update(status_text)
    
    def _has_permission(self, permission_key: str) -> bool:
        """检查权限（兼容单/多用户）"""
        try:
            # 获取当前用户ID（如果应用支持多用户）
            current_user_id = getattr(self.app, "current_user_id", None)
            if current_user_id is None:
                # 如果未启用多用户或未登录，默认允许（与其他屏幕保持一致）
                if not getattr(self.app, "multi_user_enabled", False):
                    return True
                else:
                    # 多用户启用但无当前用户，默认拒绝
                    return False
            # 传入用户ID与权限键
            return self.database_manager.has_permission(current_user_id, permission_key)  # type: ignore[misc]
        except TypeError:
            # 兼容旧签名：仅接收一个权限键参数
            try:
                return self.database_manager.has_permission(permission_key)  # type: ignore[misc]
            except Exception:
                return True
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def _check_button_permissions(self) -> None:
        """检查按钮权限并禁用/启用按钮"""
        try:
            novel_sites_btn = self.query_one("#novel-sites-btn", Button)
            proxy_settings_btn = self.query_one("#proxy-settings-btn", Button)
            
            # 检查权限并设置按钮状态
            if not self._has_permission("get_books.manage_sites"):
                novel_sites_btn.disabled = True
                novel_sites_btn.tooltip = get_global_i18n().t('get_books.no_permission')
            else:
                novel_sites_btn.disabled = False
                novel_sites_btn.tooltip = None
                
            if not self._has_permission("get_books.manage_proxy"):
                proxy_settings_btn.disabled = True
                proxy_settings_btn.tooltip = get_global_i18n().t('get_books.no_permission')
            else:
                proxy_settings_btn.disabled = False
                proxy_settings_btn.tooltip = None
                
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        # 检查权限
        button_id = event.button.id or ""
        if not self._has_button_permission(button_id):
            self.notify(get_global_i18n().t('get_books.np_action'), severity="warning")
            return
            
        # 处理分页按钮
        if event.button.id == "first-page-btn":
            self._go_to_first_page()
        elif event.button.id == "prev-page-btn":
            self._go_to_prev_page()
        elif event.button.id == "next-page-btn":
            self._go_to_next_page()
        elif event.button.id == "last-page-btn":
            self._go_to_last_page()
        elif event.button.id == "jump-page-btn":
            self._show_jump_dialog()
        # 处理原有按钮
        elif event.button.id == "novel-sites-btn":
            if self._has_permission("get_books.manage_sites"):
                self.app.push_screen("novel_sites_management")  # 打开书籍网站管理页面
            else:
                self.notify(get_global_i18n().t('get_books.np_manage_booksites'), severity="warning")
        elif event.button.id == "proxy-settings-btn":
            if self._has_permission("get_books.manage_proxy"):
                self.app.push_screen("proxy_list")  # 打开代理列表页面
            else:
                self.notify(get_global_i18n().t('get_books.np_manage_proxy'), severity="warning")
        elif event.button.id == "check-all-sites-btn":
            self._check_all_sites_status_async()
        elif event.button.id == "clear-all-invalid-btn":
            self._clear_all_invalid_records()
        elif event.button.id == "open-books-folder-btn":
            self.action_open_books_folder()
        elif event.button.id == "back-btn":
            self.app.pop_screen()  # 返回上一页
    
    def _has_button_permission(self, button_id: str) -> bool:
        """检查按钮权限"""
        permission_map = {
            "novel-sites-btn": "get_books.manage_sites",
            "proxy-settings-btn": "get_books.manage_proxy"
        }
        
        if button_id in permission_map:
            return self._has_permission(permission_map[button_id])
        
        return True  # 默认允许未知按钮
    
    def _open_site_by_row_index(self, row_index: int) -> None:
        """根据行索引打开对应站点的爬取管理页面
        
        Args:
            row_index: 当前页内的行索引（0-based）
        """
        # 计算在全部数据中的实际索引
        start_index = (self._current_page - 1) * self._sites_per_page
        actual_index = start_index + row_index
        
        if 0 <= actual_index < len(self._all_sites):
            site = self._all_sites[actual_index]
            if self._has_permission("crawler.open"):
                from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                self.app.push_screen(crawler_screen)
            else:
                self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")

    @on(DataTable.HeaderSelected, "#novel-sites-table")
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """数据表格表头点击事件 - 处理排序"""
        try:
            column_key = event.column_key.value or ""

            logger.debug(f"表头点击事件: column={column_key}")

            # 只对特定列进行排序：网站名称、网站URL、状态、评分、代理启用、解析器、标签、书籍数量
            sortable_columns = ["name", "url", "status", "proxy_enabled", "parser", "tags", "rating", "books_count"]

            if column_key in sortable_columns:
                # 切换排序方向
                if self._sort_column == column_key:
                    self._sort_reverse = not self._sort_reverse
                else:
                    self._sort_column = column_key
                    self._sort_reverse = True  # 新列默认倒序

                # 执行排序
                self._sort_sites(column_key, self._sort_reverse)

                # 重新加载表格显示（由于有排序条件，会使用已有的排序数据）
                self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)

                # 显示排序提示
                sort_direction = "倒序" if self._sort_reverse else "正序"
                column_names = {
                    "name": "网站名称",
                    "url": "网站URL",
                    "status": "状态",
                    "proxy_enabled": "代理启用",
                    "parser": "解析器",
                    "tags": "标签",
                    "rating": "评分",
                    "books_count": "书籍数量"
                }
                column_name = column_names.get(column_key, column_key)
                self.notify(f"已按 {column_name} {sort_direction} 排列", severity="information")

        except Exception as e:
            logger.error(f"表头点击事件处理失败: {e}")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        数据表行选择时的回调（双击或回车）
        
        Args:
            event: 行选择事件
        """
        logger.debug(f"行选择事件触发: {event}")
        
        try:
            # 如果是按钮点击触发的行选择事件，直接返回
            if getattr(self, '_button_clicked', False):
                logger.debug("按钮点击触发的行选择事件，忽略")
                # 重置标志
                self._button_clicked = False
                return
            
            # 获取当前选中的行索引
            table = self.query_one("#novel-sites-table", DataTable)
            
            # 使用 cursor_row 获取当前光标所在行
            if hasattr(table, 'cursor_row') and table.cursor_row is not None:
                row_index = table.cursor_row
                
                # 对于行选择事件（双击或回车），直接打开站点
                # 权限校验：打开爬取管理页面需 crawler.open
                if self._has_permission("crawler.open"):
                    self._open_site_by_row_index(row_index)
                else:
                    self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
            
        except Exception as e:
            logger.error(f"处理行选择时出错: {e}")
    
    def on_click(self, event: events.Click) -> None:
        """处理鼠标点击事件"""
        # 按钮点击现在由on_data_table_cell_selected处理
        # 这个方法保持为空，以避免干扰
        pass
    

    
    def _restore_cursor_position(self, table: DataTable, row: int, col: int) -> None:
        """
        恢复光标位置到指定的行列
        
        Args:
            table: 数据表
            row: 行索引
            col: 列索引
        """
        try:
            # 确保表格有焦点
            table.focus()
            
            # 使用Textual的标准方法恢复光标位置
            if hasattr(table, 'cursor_coordinate'):
                table.cursor_coordinate = (row, col)
            elif hasattr(table, 'cursor_row') and hasattr(table, 'cursor_column'):
                table.cursor_row = row
                table.cursor_column = col
            elif hasattr(table, '_cursor_row') and hasattr(table, '_cursor_column'):
                table._cursor_row = row
                table._cursor_column = col
                
            # 强制刷新表格显示
            table.refresh()
        except Exception as e:
            logger.debug(f"恢复光标位置失败: {e}")
            # 如果恢复失败，至少确保表格有焦点
            try:
                table.focus()
            except Exception:
                pass
    
    @on(DataTable.RowHighlighted, "#novel-sites-table")
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """
        数据表行高亮时的回调（用于方向键移动）
        
        Args:
            event: 行高亮事件
        """
        logger.debug(f"行高亮事件触发: {event}")
        
        try:
            # 获取高亮行的键
            row_key = getattr(event, 'row_key', None)
            if row_key is None:
                return
            
        except Exception as e:
            logger.error(f"处理行高亮时出错: {e}")
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        数据表行选择时的回调（双击或回车）
        
        Args:
            event: 行选择事件
        """
        logger.debug(f"行选择事件触发: {event}")
        
        try:
            # 如果是按钮点击触发的行选择事件，直接返回
            if getattr(self, '_button_clicked', False):
                logger.debug("按钮点击触发的行选择事件，忽略")
                # 重置标志
                self._button_clicked = False
                return
            
            # 获取当前选中的行索引
            table = self.query_one("#novel-sites-table", DataTable)
            
            # 确保表格是单元格模式
            if table.cursor_type != "cell":
                logger.debug(f"在行选择事件中，表格模式不是cell，重新设置为cell")
                table.cursor_type = "cell"
            
            # 使用 cursor_row 获取当前光标所在行
            if hasattr(table, 'cursor_row') and table.cursor_row is not None:
                row_index = table.cursor_row
                
                # 权限校验：打开爬取管理页面需 crawler.open
                if self._has_permission("crawler.open"):
                    self._open_site_by_row_index(row_index)
                else:
                    self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
            
        except Exception as e:
            logger.error(f"处理行选择时出错: {e}")

    # Actions for BINDINGS
    def action_open_novel_sites(self) -> None:
        if self._has_permission("get_books.manage_sites"):
            self.app.push_screen("novel_sites_management")
        else:
            self.notify(get_global_i18n().t('get_books.np_manage_booksites'), severity="warning")

    def action_open_proxy_list(self) -> None:
        if self._has_permission("get_books.manage_proxy"):
            self.app.push_screen("proxy_list")
        else:
            self.notify(get_global_i18n().t('get_books.np_manage_proxy'), severity="warning")

    def action_open_books_folder(self) -> None:
        config_manager = ConfigManager.get_instance()
        config = config_manager.get_config()
        books_folder_path = os.path.expanduser(config.get("paths", {}).get("library", ""))
        if not os.path.exists(books_folder_path):
            self.notify(f"{books_folder_path}:{get_global_i18n().t('get_books.books-folder-not-exist')}", severity="warning")
            return
        # 在文件管理器中显示文件
        system = platform.system()
        if system == "Darwin":  # macOS
            os.system(f'open "{books_folder_path}/"')
        elif system == "Windows":
            os.system(f'explorer /select,"{books_folder_path}/"')
        elif system == "Linux":
            os.system(f'xdg-open "{os.path.dirname(books_folder_path)}/"')
        

    def action_open_selected(self) -> None:
        """打开选中的书籍网站"""
        if self._has_permission("crawler.open"):
            table = self.query_one("#novel-sites-table", DataTable)
            # 获取当前光标所在的行
            current_row = None
            
            # 尝试多种方式获取当前行
            if hasattr(table, 'cursor_row') and table.cursor_row is not None:
                current_row = table.cursor_row
            elif hasattr(table, 'cursor_row'):
                # 如果 cursor_row 存在但是 None，尝试获取 DataTable 的实际光标位置
                try:
                    current_row = super(DataTable, table).cursor_row
                except:
                    pass
            
            if current_row is not None and current_row >= 0:
                self._open_site_by_row_index(current_row)
            else:
                # 如果没有光标行，尝试使用第一行
                if hasattr(table, '_current_data') and len(table._current_data) > 0:
                    self._open_site_by_row_index(0)
        else:
            self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")

    def action_back(self) -> None:
        self.app.pop_screen()
    
    def action_prev_page(self) -> None:
        self._go_to_prev_page()

    def action_next_page(self) -> None:
        self._go_to_next_page()

    def action_jump_to(self) -> None:
        self._show_jump_dialog()

    def action_clear_search_params(self) -> None:
        """清除搜索参数"""
        self.query_one("#novel-sites-search-input", Input).value = ""
        self.query_one("#novel-sites-search-input", Input).placeholder = get_global_i18n().t('search.site_placeholder')
        self.query_one("#novel-sites-parser-filter", Select).value = "all"
        self.query_one("#novel-sites-proxy-filter", Select).value = "all"
        self.query_one("#novel-sites-status-filter", Select).value = "all"
        self.query_one("#novel-sites-rating-filter", Select).value = "all"
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理输入框内容变化事件"""
        # 搜索输入框变化时自动执行搜索
        if event.input.id == "novel-sites-search-input":
            self._perform_search()
            # 执行搜索后，保持焦点在搜索框
            self.set_timer(0.1, lambda: self._focus_search_input())
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """处理选择框变化事件"""
        # 筛选器变化时自动执行搜索
        if event.select.id in ["novel-sites-parser-filter", "novel-sites-proxy-filter", "novel-sites-status-filter", "novel-sites-rating-filter"]:
            self._perform_search()

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """
        数据表单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        logger.debug(f"单元格选择事件触发: {event}")
        
        try:
            # 获取表格
            table = self.query_one("#novel-sites-table", DataTable)
            
            # 确保表格是单元格模式
            if table.cursor_type != "cell":
                logger.debug(f"表格模式不是cell，重新设置为cell")
                table.cursor_type = "cell"
            
            # 获取点击的行和列
            if hasattr(event, 'coordinate') and event.coordinate is not None:
                row_index = event.coordinate.row
                col_index = event.coordinate.column
                
                # 保存当前光标位置
                saved_row = row_index
                saved_col = col_index
                
                logger.debug(f"点击位置: 行={row_index}, 列={col_index}")
                
                # 获取列键名
                column_key_name = None
                try:
                    # 通过表格的列索引获取列键名
                    if hasattr(table, 'columns') and col_index < len(table.columns):
                        column_key_name = table.columns[col_index].key
                    logger.debug(f"列键名: {column_key_name}")
                except Exception as e:
                    logger.debug(f"获取列键名失败: {e}")
                    # 如果无法获取列键名，则使用索引继续处理
                    column_key_name = None
                
                # 判断是否点击了按钮列
                is_check_column = False
                is_enter_column = False
                
                # 首先尝试使用列键名判断
                if column_key_name == "check":
                    is_check_column = True
                elif column_key_name == "enter":
                    is_enter_column = True
                # 如果无法获取列键名，则使用列索引判断
                elif column_key_name is None:
                    if col_index == 9:  # "检测"按钮列
                        is_check_column = True
                    elif col_index == 10:  # "进入"按钮列
                        is_enter_column = True
                
                logger.debug(f"是否是检测列: {is_check_column}, 是否是进入列: {is_enter_column}")
                
                # 处理检测按钮点击
                if is_check_column:
                    # 设置按钮点击标志
                    self._button_clicked = True
                    logger.debug(f"设置按钮点击标志为True")
                    
                    # 获取当前页的数据
                    start_index = (self._current_page - 1) * self._sites_per_page
                    if row_index is not None and row_index < len(self._all_sites) - start_index:
                        site = self._all_sites[start_index + row_index]
                        logger.debug(f"检测的站点: {site.get('name', 'Unknown')}")
                        
                        # 执行网站检测
                        self._check_site_status(site)
                    else:
                        logger.warning(f"行索引超出范围: row_index={row_index}, 总数据长度={len(self._all_sites)}, 起始索引={start_index}")
                    
                    # 恢复光标位置
                    self._restore_cursor_position(table, saved_row, saved_col)
                
                # 处理进入按钮点击
                elif is_enter_column:
                    # 设置按钮点击标志
                    self._button_clicked = True
                    logger.debug(f"设置按钮点击标志为True")
                    
                    # 获取当前页的数据
                    start_index = (self._current_page - 1) * self._sites_per_page
                    if row_index is not None and row_index < len(self._all_sites) - start_index:
                        site = self._all_sites[start_index + row_index]
                        logger.debug(f"选中的站点: {site.get('name', 'Unknown')}")
                        
                        # 权限校验：打开爬取管理页面需 crawler.open
                        if self._has_permission("crawler.open"):
                            from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                            crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                            self.app.push_screen(crawler_screen)  # 打开爬取管理页面
                        else:
                            self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
                    else:
                        logger.warning(f"行索引超出范围: row_index={row_index}, 总数据长度={len(self._all_sites)}, 起始索引={start_index}")
                    
                    # 恢复光标位置
                    self._restore_cursor_position(table, saved_row, saved_col)
                
                # 处理状态列点击 - 切换网站状态
                elif column_key_name == "status" or col_index == 3:  # 状态列
                    # 设置按钮点击标志
                    self._button_clicked = True
                    logger.debug(f"设置按钮点击标志为True")
                    
                    # 获取当前页的数据
                    start_index = (self._current_page - 1) * self._sites_per_page
                    if row_index is not None and row_index < len(self._all_sites) - start_index:
                        site = self._all_sites[start_index + row_index]
                        logger.debug(f"切换状态的站点: {site.get('name', 'Unknown')}")
                        
                        # 切换网站状态
                        self._toggle_site_status(site)
                    else:
                        logger.warning(f"行索引超出范围: row_index={row_index}, 总数据长度={len(self._all_sites)}, 起始索引={start_index}")
                    
                    # 恢复光标位置
                    self._restore_cursor_position(table, saved_row, saved_col)
                
                # 处理其他列点击 - 不执行任何操作，只恢复光标位置
                else:
                    # 检查是否点击了网站网址列
                    is_url_column = False
                    if column_key_name == "url" or col_index == 2:  # 网站网址列
                        is_url_column = True
                    
                    if is_url_column:
                        # 设置按钮点击标志
                        self._button_clicked = True
                        logger.debug(f"设置按钮点击标志为True")
                        
                        # 获取当前页的数据
                        start_index = (self._current_page - 1) * self._sites_per_page
                        if row_index is not None and row_index < len(self._all_sites) - start_index:
                            site = self._all_sites[start_index + row_index]
                            site_url = site.get("url", "")
                            site_name = site.get("name", "未知网站")
                            logger.debug(f"打开的站点网址: {site_url}")
                            
                            if site_url:
                                # 使用系统默认浏览器打开网址
                                self._open_url_in_browser(site_url, site_name)
                            else:
                                self.notify(get_global_i18n().t('get_books.site_url_empty'), severity="warning")
                        else:
                            logger.warning(f"行索引超出范围: row_index={row_index}, 总数据长度={len(self._all_sites)}, 起始索引={start_index}")
                        
                        # 恢复光标位置
                        self._restore_cursor_position(table, saved_row, saved_col)
                    else:
                        # 对于非特殊功能列的点击，不执行任何操作
                        logger.debug(f"点击的是普通列: {col_index}")
                        # 恢复光标位置
                        self._restore_cursor_position(table, saved_row, saved_col)
            else:
                logger.debug("单元格选择事件没有坐标信息")
                
        except Exception as e:
            logger.error(f"处理单元格选择时出错: {e}")
            
        # 阻止事件冒泡，防止触发行选择
        event.stop()
        event.prevent_default()

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        table = self.query_one("#novel-sites-table", DataTable)
        
        # 如果是按钮点击触发的键盘事件，直接返回
        if getattr(self, '_button_clicked', False):
            logger.debug("按钮点击触发的键盘事件，忽略")
            # 重置标志
            self._button_clicked = False
            return
        
        # 回车键或空格键：打开当前选中的站点
        if event.key == "space":
            # 获取当前选中的行
            if table.cursor_row is not None:
                # 权限校验：打开爬取管理页面需 crawler.open
                if self._has_permission("crawler.open"):
                    self._open_site_by_row_index(table.cursor_row)
                else:
                    self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
                # 完全阻止事件传播，避免传递到新页面
                event.prevent_default()
                event.stop()
                return
        if event.key == "enter":
            # 获取当前选中的行
            if table.cursor_row is not None:
                # 权限校验：打开爬取管理页面需 crawler.open
                if self._has_permission("crawler.open"):
                    self._open_site_by_row_index(table.cursor_row)
                else:
                    self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
                # 不阻止回车的默认行为
        
        # 数字键 1-9：打开对应行的"进入"，0键打开第10行
        if event.key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            # 默认索引计算
            if event.key == "0":
                idx = 9  # 0键映射到第10项（索引9）
            else:
                idx = int(event.key) - 1
                
            # 使用映射，确保与当前表格行一致
            if event.key in getattr(self, "_shortcut_index_map", {}):
                idx = self._shortcut_index_map[event.key]
            
            if self._has_permission("crawler.open"):
                self._open_site_by_row_index(idx)
            else:
                self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
            event.prevent_default()
            return

        # 方向键翻页功能
        if event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
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
            if table.cursor_row == 0 and self._current_page > 1:
                self._go_to_prev_page()
                # 将光标移动到新页面的最后一行
                last_row_index = len(table.rows) - 1
                table.move_cursor(row=last_row_index, column=0)  # 直接移动到最后一行第一列
                event.prevent_default()
                event.stop()
                return

        if event.key == "escape":
            # ESC键返回（仅一次）
            if len(self.app.screen_stack) > 1:
                self.app.pop_screen()
            event.stop()

    def _clear_all_invalid_records(self) -> None:
        """清理所有无效记录（没有文件的记录和爬取失败的记录）"""
        import sqlite3

        try:
            # 检查权限
            if not self._has_permission("crawler.delete_record"):
                self.notify(get_global_i18n().t('get_books.np_clear_all_invalid'), severity="error")
                return

            # 查询所有无效记录
            invalid_records = []
            try:
                with sqlite3.connect(self.database_manager.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # 1. 查询所有失败的记录
                    cursor.execute("""
                        SELECT id, site_id, novel_id, novel_title, file_path, status, error_message
                        FROM crawl_history
                        WHERE status = 'failed'
                    """)
                    failed_rows = cursor.fetchall()
                    for row in failed_rows:
                        invalid_records.append(dict(row))

                    # 2. 查询所有成功的记录，然后检查文件是否存在
                    cursor.execute("""
                        SELECT id, site_id, novel_id, novel_title, file_path, status, error_message
                        FROM crawl_history
                        WHERE status = 'success'
                    """)
                    success_rows = cursor.fetchall()
                    for row in success_rows:
                        record = dict(row)
                        # 检查文件路径是否为空或文件是否存在
                        if not record.get('file_path') or not os.path.exists(record['file_path']):
                            invalid_records.append(record)

            except Exception as e:
                logger.error(f"查询无效记录失败: {e}")
                self.notify(get_global_i18n().t('get_books.clear_all_invalid_failed', error=str(e)), severity="error")
                return

            # 如果没有无效记录
            if not invalid_records:
                self.notify(get_global_i18n().t('get_books.clear_all_invalid_no_data'), severity="information")
                return

            # 显示确认对话框
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_clear_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        deleted_count = 0
                        failed_count = 0

                        # 删除所有无效记录
                        for record in invalid_records:
                            try:
                                record_id = record['id']
                                if self.database_manager.delete_crawl_history(record_id):
                                    deleted_count += 1
                                else:
                                    failed_count += 1
                            except Exception as e:
                                logger.error(f"删除记录失败: {record['id']}, 错误: {e}")
                                failed_count += 1

                        # 刷新书籍网站列表（更新书籍数量）
                        self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled, self._search_status, self._search_rating)

                        # 显示结果
                        if failed_count > 0:
                            self.notify(
                                get_global_i18n().t('get_books.clear_all_invalid_success', success=deleted_count, fail=failed_count),
                                severity="warning"
                            )
                        else:
                            self.notify(
                                get_global_i18n().t('get_books.clear_all_invalid_success', success=deleted_count, fail=failed_count),
                                severity="success"
                            )
                    except Exception as e:
                        logger.error(f"清理无效记录失败: {e}")
                        self.notify(get_global_i18n().t('get_books.clear_all_invalid_failed', error=str(e)), severity="error")
                elif confirmed is False:
                    self.notify(get_global_i18n().t('crawler.delete_cancelled'))

            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t('get_books.clear_all_invalid_confirm'),
                    get_global_i18n().t('get_books.clear_all_invalid_desc', count=len(invalid_records))
                ),
                handle_clear_confirmation
            )

        except Exception as e:
            logger.error(f"清理无效记录操作失败: {e}")
            self.notify(get_global_i18n().t('get_books.clear_all_invalid_failed', error=str(e)), severity="error")