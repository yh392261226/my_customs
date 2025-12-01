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
import platform, os
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
        table.add_column(get_global_i18n().t('get_books.proxy_enabled'), key="proxy_enabled")
        table.add_column(get_global_i18n().t('get_books.parser'), key="parser")
        table.add_column(get_global_i18n().t('get_books.rating'), key="rating")
        table.add_column(get_global_i18n().t('get_books.enter'), key="enter")
        
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        # 启用行选择功能
        table.cursor_type = "row"

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
            # 确保表格的光标类型设置为行
            table.cursor_type = "row"
            # 确保表格能够接收键盘事件
            table.can_focus = True
        except Exception:
            pass
    
    def on_screen_resume(self) -> None:
        """屏幕恢复时的回调（从其他屏幕返回时调用）"""
        # 重新加载代理设置，确保显示最新状态
        self._load_proxy_settings()
        self._load_novel_sites()
        
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

    def _load_novel_sites(self, search_keyword: str = "", search_parser: str = "all", search_proxy_enabled: str = "all") -> None:
        """加载书籍网站数据
        
        Args:
            search_keyword: 搜索关键词
            search_parser: 解析器筛选
            search_proxy_enabled: 代理启用筛选
        """
        # 从数据库加载书籍网站数据
        all_sites = self.database_manager.get_novel_sites()
        
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
            
            if keyword_match and parser_match and proxy_match:
                filtered_sites.append(site)
        
        # 按照星级倒序排序（rating高的在前）
        filtered_sites.sort(key=lambda x: x.get("rating", 0), reverse=True)
        
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
            
            row_data = {
                "sequence": str(global_index),
                "name": site.get("name", ""),
                "url": site.get("url", ""),
                "proxy_enabled": proxy_status,
                "parser": site.get("parser", ""),
                "rating": rating_display,
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
                row_data["proxy_enabled"],
                row_data["parser"],
                row_data["rating"],
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
        
        # 为数字快捷键1-9建立行索引映射
        try:
            self._shortcut_index_map = {str(i + 1): i for i in range(min(9, len(current_page_sites)))}
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
            status_text = f"{get_global_i18n().t('get_books.novel_sites_list')} - 总共 {total_sites} 个网站 | 第 {self._current_page} / {self._total_pages} 页"
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
        
        # 重置到第一页
        self._current_page = 1
        
        # 重新加载数据
        self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled)

    # 分页导航方法
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self._current_page != 1:
            self._current_page = 1
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled)

    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled)

    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled)

    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled)

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
                            self._load_novel_sites(self._search_keyword, self._search_parser, self._search_proxy_enabled)
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
                novel_sites_btn.tooltip = "无权限"
            else:
                novel_sites_btn.disabled = False
                novel_sites_btn.tooltip = None
                
            if not self._has_permission("get_books.manage_proxy"):
                proxy_settings_btn.disabled = True
                proxy_settings_btn.tooltip = "无权限"
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

    @on(DataTable.CellSelected, "#novel-sites-table")
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """
        数据表单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        logger.debug(f"单元格选择事件触发: {event}")
        
        try:
            # 检查是否点击了"进入"按钮列（第6列，从0开始）
            if hasattr(event, 'coordinate'):
                column_key = event.coordinate.column
                row_index = event.coordinate.row
                
                logger.debug(f"点击的列: {column_key}, 行: {row_index}")
                
                # 只处理"进入"按钮列（第6列）
                if column_key == 6:  # "进入"按钮列
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
                        
                        # 阻止事件冒泡，避免触发其他处理程序
                        event.stop()
                    else:
                        logger.warning(f"行索引超出范围: row_index={row_index}, 总数据长度={len(self._all_sites)}, 起始索引={start_index}")
                else:
                    # 如果不是"进入"按钮列，只是移动光标到该行
                    # 这样用户可以通过键盘导航到不同行，然后按回车或空格键打开
                    logger.debug(f"点击了非按钮列: {column_key}")
            else:
                logger.debug("单元格选择事件没有坐标信息")
        except Exception as e:
            logger.error(f"处理单元格选择时出错: {e}")
    
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
    
    @on(DataTable.RowSelected, "#novel-sites-table")
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """
        数据表行选择时的回调（双击或回车）
        
        Args:
            event: 行选择事件
        """
        logger.debug(f"行选择事件触发: {event}")
        
        try:
            # 获取当前选中的行索引
            table = self.query_one("#novel-sites-table", DataTable)
            
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
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """处理输入框内容变化事件"""
        # 搜索输入框变化时自动执行搜索
        if event.input.id == "novel-sites-search-input":
            self._perform_search()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """处理选择框变化事件"""
        # 筛选器变化时自动执行搜索
        if event.select.id in ["novel-sites-parser-filter", "novel-sites-proxy-filter"]:
            self._perform_search()

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        table = self.query_one("#novel-sites-table", DataTable)
        
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
        
        # 数字键 1-9：打开对应行的"进入"
        if event.key in ["1","2","3","4","5","6","7","8","9"]:
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
            self.app.pop_screen()
            event.stop()