"""
书籍网站管理屏幕
"""

from typing import Dict, Any, Optional, List, ClassVar
from urllib.parse import unquote
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Label, Input, Select, Checkbox, Header, Footer
from textual.widgets import DataTable
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.ui.dialogs.note_dialog import NoteDialog

logger = get_logger(__name__)

class NovelSitesManagementScreen(Screen[None]):

    # 使用 Textual BINDINGS 进行快捷键绑定
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("a", "add_site", get_global_i18n().t('common.add')),
        ("e", "edit_site", get_global_i18n().t('common.edit')),
        ("d", "delete_site", get_global_i18n().t('common.delete')),
        ("b", "batch_delete", get_global_i18n().t('novel_sites.batch_delete')),
        ("m", "note", get_global_i18n().t('crawler.shortcut_b')),
        ("enter", "enter_crawler", get_global_i18n().t('get_books.enter')),
        ("p", "prev_page", get_global_i18n().t('crawler.shortcut_p')),
        ("n", "next_page", get_global_i18n().t('crawler.shortcut_n')),
        ("x", "clear_search_params", get_global_i18n().t('crawler.clear_search_params')),
        ("j", "jump_to", get_global_i18n().t('bookshelf.jump_to')),
        ("space", "toggle_row", get_global_i18n().t('batch_ops.toggle_row')),
    ]

    """书籍网站管理屏幕"""
    
    CSS_PATH = "../styles/novel_sites_management_overrides.tcss"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化书籍网站管理屏幕
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        try:
            self.title = get_global_i18n().t('novel_sites.title')
        except RuntimeError:
            # 如果全局i18n未初始化，使用默认标题
            self.title = "书籍网站管理"
        self.theme_manager = theme_manager
        self.database_manager = DatabaseManager()
        self.novel_sites = []  # 书籍网站列表
        self.selected_sites = set()  # 选中的网站索引
        
        # 分页相关属性
        self._current_page = 1
        self._total_pages = 1
        self._sites_per_page = 10  # 每页显示的网站数量
        
        # 搜索相关属性
        self._search_keyword = ""
        self._search_parser = "all"
        self._search_proxy_enabled = "all"

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

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            # 使用应用的权限检查方法，而不是直接调用database_manager
            if hasattr(self.app, 'has_permission'):
                return self.app.has_permission(permission_key)
            else:
                # 如果应用没有权限检查方法，默认允许
                return True
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def compose(self) -> ComposeResult:
        """
        组合书籍网站管理屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Grid(
                # 顶部区域：描述、按钮、搜索栏
                Vertical(
                    # Label(get_global_i18n().t('novel_sites.title'), id="novel-sites-title", classes="section-title"),
                    Label(get_global_i18n().t('novel_sites.description'), id="novel-sites-description", classes="section-title"),
                    
                    # 操作按钮区域
                    Horizontal(
                        Button(get_global_i18n().t('novel_sites.add'), id="add-btn", classes="btn"),
                        Button(get_global_i18n().t('novel_sites.edit'), id="edit-btn", classes="btn"),
                        Button(get_global_i18n().t('novel_sites.delete'), id="delete-btn", classes="btn"),
                        Button(get_global_i18n().t('novel_sites.batch_delete'), id="batch-delete-btn", classes="btn"),
                        Button(get_global_i18n().t('novel_sites.back'), id="back-btn", classes="btn"),
                        id="novel-sites-buttons",
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
                    id="novel-sites-header",
                    classes="novel-sites-header-vertical"
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
                
                # 底部区域2：状态信息
                Vertical(
                    Label("", id="novel-sites-status"),
                    id="novel-sites-status-area"
                ),
                
                id="novel-sites-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        apply_universal_style_isolation(self)
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 设置Grid布局的行高分配
        try:
            grid = self.query_one("Grid")
            grid.styles.grid_size_rows = 4
            grid.styles.grid_size_columns = 1
            grid.styles.grid_rows = ("35%", "45%", "10%", "10%")
        except Exception:
            pass
        
        # 初始化数据表
        table = self.query_one("#novel-sites-table", DataTable)
        table.add_column(get_global_i18n().t('novel_sites.selected'), key="selected")
        table.add_column(get_global_i18n().t('novel_sites.site_name'), key="site_name")
        table.add_column(get_global_i18n().t('novel_sites.site_url'), key="site_url")
        table.add_column(get_global_i18n().t('novel_sites.rating'), key="rating")
        table.add_column(get_global_i18n().t('novel_sites.proxy_enabled'), key="proxy_enabled")
        table.add_column(get_global_i18n().t('novel_sites.parser'), key="parser")
        table.add_column(get_global_i18n().t('novel_sites.book_id_example'), key="book_id_example")
        table.add_column(get_global_i18n().t('crawler.note'), key="note")
        
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        # 加载书籍网站数据
        self._load_novel_sites()

        # 确保表格获得焦点并初始化光标到第一行
        try:
            table.focus()
        except Exception:
            pass
        try:
            if getattr(table, "cursor_row", None) is None and len(self.novel_sites) > 0:
                table._ensure_cursor_coordinate(0)
        except Exception:
            pass
    
    def _load_novel_sites(self, search_keyword: str = "", search_parser: str = "all", search_proxy_enabled: str = "all") -> None:
        """从数据库加载书籍网站数据
        
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
        
        self.novel_sites = filtered_sites
        
        # 更新数据表
        self._update_table()
    
    def _update_table(self) -> None:
        """更新数据表显示（使用虚拟滚动和分页）"""
        table = self.query_one("#novel-sites-table", DataTable)
        
        # 保存当前光标位置
        current_cursor_row = table.cursor_row
        
        # 计算分页
        self._total_pages = max(1, (len(self.novel_sites) + self._sites_per_page - 1) // self._sites_per_page)
        self._current_page = min(self._current_page, self._total_pages)
        
        # 获取当前页的数据
        start_index = (self._current_page - 1) * self._sites_per_page
        end_index = min(start_index + self._sites_per_page, len(self.novel_sites))
        current_page_sites = self.novel_sites[start_index:end_index]
        
        # 准备虚拟滚动数据
        virtual_data = []
        for i, site in enumerate(current_page_sites):
            global_index = start_index + i
            selected = "✓" if global_index in self.selected_sites else ""
            proxy_status = get_global_i18n().t('common.yes') if site["proxy_enabled"] else get_global_i18n().t('common.no')
            # 获取星级评分，如果没有则默认为2星
            rating = site.get("rating", 2)
            rating_display = self._get_rating_display(rating)
            
            # 对book_id_example进行URL解码，避免显示乱码
            book_id_example = site.get("book_id_example", "")
            decoded_book_id_example = unquote(book_id_example) if book_id_example else ""
            
            row_data = {
                "selected": selected,
                "site_name": site["name"],
                "site_url": site["url"],
                "rating": rating_display,
                "proxy_enabled": proxy_status,
                "parser": site["parser"],
                "book_id_example": decoded_book_id_example,
                "_row_key": str(global_index),
                "_global_index": global_index + 1
            }
            virtual_data.append(row_data)
        
        # 填充表格数据
        table.clear()
        for row_data in virtual_data:
            table.add_row(
                row_data["selected"],
                row_data["site_name"],
                row_data["site_url"],
                row_data["rating"],
                row_data["proxy_enabled"],
                row_data["parser"],
                row_data["book_id_example"],
                get_global_i18n().t('crawler.note')
            )
        
        # 更新分页信息
        self._update_pagination_info()
        self._update_pagination_buttons()
        
        # 恢复光标位置，确保光标不会跳回第一行
        if current_cursor_row is not None and current_cursor_row >= 0:
            # 确保光标位置在有效范围内
            if current_cursor_row < min(self._sites_per_page, len(self.novel_sites) - start_index):
                if hasattr(table, 'move_cursor'):
                    table.move_cursor(row=current_cursor_row)
                # 如果move_cursor不存在，使用键盘操作来移动光标
                else:
                    # 将光标移动到正确位置
                    # 先将光标移动到第一行
                    while table.cursor_row > 0:
                        table.action_cursor_up()
                    # 然后向下移动到目标位置
                    for _ in range(current_cursor_row):
                        table.action_cursor_down()
        
        # 确保表格获得焦点
        table.focus()

    def _toggle_site_selection(self, table: DataTable, current_row_index: int) -> None:
        """切换网站选中状态（参考批量操作页面的实现）"""
        try:
            # 计算当前页面的起始索引和全局索引
            start_index = (self._current_page - 1) * self._sites_per_page
            global_index = start_index + current_row_index
            
            if global_index >= len(self.novel_sites):
                return
                
            # 切换选中状态
            if global_index in self.selected_sites:
                self.selected_sites.remove(global_index)
            else:
                self.selected_sites.add(global_index)
            
            # 重新渲染表格以更新选中状态显示
            self._update_table()
            
            # 更新状态显示
            selected_count = len(self.selected_sites)
            self._update_status(get_global_i18n().t('novel_sites.already_selected', counts=selected_count), "information")
                
        except Exception:
            # 如果出错，重新渲染整个表格
            self._update_table()
    
    def _update_cell_display(self, table: DataTable, row_key, column_key, value: str) -> None:
        """尝试更新单元格显示，如果失败则重新渲染表格"""
        try:
            # 尝试使用update_cell方法（如果存在）
            if hasattr(table, 'update_cell'):
                table.update_cell(row_key, column_key, value)
            else:
                # 如果update_cell不存在，重新渲染表格
                self._update_table()
        except Exception:
            # 如果失败，重新渲染表格
            self._update_table()
    
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
                            self._update_table()
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
    
    
    
    def _show_add_dialog(self) -> None:
        """显示添加书籍网站对话框"""
        from src.ui.dialogs.novel_site_dialog import NovelSiteDialog
        dialog = NovelSiteDialog(self.theme_manager, None)
        self.app.push_screen(dialog, self._handle_add_result)
    
    def _edit_site(self) -> None:
        """显示编辑书籍网站对话框"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            # 计算当前页面的起始索引
            start_index = (self._current_page - 1) * self._sites_per_page
            # 计算全局索引
            global_index = start_index + table.cursor_row
            
            if global_index < len(self.novel_sites):
                site = self.novel_sites[global_index]
                from src.ui.dialogs.novel_site_dialog import NovelSiteDialog
                dialog = NovelSiteDialog(self.theme_manager, site)
                self.app.push_screen(dialog, lambda result: self._handle_edit_result(result, global_index))
            else:
                self._update_status(get_global_i18n().t('novel_sites.site_not_found'), "error")
    
    def _handle_add_result(self, result: Optional[Dict[str, Any]]) -> None:
        """处理添加结果"""
        if result:
            # 保存到数据库
            success = self.database_manager.save_novel_site(result)
            if success:
                # 重新加载数据
                self._load_novel_sites()
                self._update_status(get_global_i18n().t('novel_sites.added_success'))
            else:
                self._update_status(get_global_i18n().t('novel_sites.add_failed'), "error")
        else:
            # 如果结果为None，说明用户取消了操作
            self._update_status(get_global_i18n().t('novel_sites.add_cancelled'))
    
    def _handle_edit_result(self, result: Optional[Dict[str, Any]], site_index: int) -> None:
        """处理编辑结果"""
        if result and 0 <= site_index < len(self.novel_sites):
            # 保存到数据库
            success = self.database_manager.save_novel_site(result)
            if success:
                # 重新加载数据
                self._load_novel_sites()
                self._update_status(get_global_i18n().t('novel_sites.edited_success'))
            else:
                self._update_status(get_global_i18n().t('novel_sites.edit_failed'), "error")
    
    def _delete_site(self) -> None:
        """删除选中的书籍网站"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            # 计算当前页面的起始索引
            start_index = (self._current_page - 1) * self._sites_per_page
            # 计算全局索引
            global_index = start_index + table.cursor_row
            
            if global_index < len(self.novel_sites):
                site = self.novel_sites[global_index]
                # 显示确认对话框
                from src.ui.dialogs.confirm_dialog import ConfirmDialog
                dialog = ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t('novel_sites.confirm_delete'),
                    f"{get_global_i18n().t('novel_sites.confirm_delete_message')}: {site['name']}"
                )
                self.app.push_screen(dialog, lambda confirmed: self._handle_delete_result(confirmed, global_index))
            else:
                self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
        else:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
    
    def _batch_delete(self) -> None:
        """批量删除选中的书籍网站"""
        if not self.selected_sites:
            self._update_status(get_global_i18n().t('novel_sites.select_sites_first'))
            return
        
        # 显示确认对话框
        from src.ui.dialogs.confirm_dialog import ConfirmDialog
        dialog = ConfirmDialog(
            self.theme_manager,
            get_global_i18n().t('novel_sites.confirm_batch_delete'),
            f"{get_global_i18n().t('novel_sites.confirm_batch_delete_message')}: {len(self.selected_sites)}"
        )
        self.app.push_screen(dialog, self._handle_batch_delete_confirm)
    
    def _handle_delete_result(self, result: Optional[bool], site_index: int) -> None:
        """处理删除结果"""
        if result and 0 <= site_index < len(self.novel_sites):
            site = self.novel_sites[site_index]
            site_id = site.get("id")
            if site_id:
                # 从数据库删除
                success = self.database_manager.delete_novel_site(site_id)
                if success:
                    # 重新加载数据
                    self._load_novel_sites()
                    self._update_status(f"{get_global_i18n().t('novel_sites.deleted_success')}: {site['name']}")
                else:
                    self._update_status(get_global_i18n().t('novel_sites.delete_failed'), "error")
            else:
                self._update_status(get_global_i18n().t('novel_sites.delete_failed'), "error")
    
    def _handle_delete_confirm(self, result: Optional[bool], site_index: int) -> None:
        """处理删除确认"""
        if result and 0 <= site_index < len(self.novel_sites):
            site = self.novel_sites[site_index]
            site_id = site.get("id")
            if site_id:
                # 从数据库删除
                success = self.database_manager.delete_novel_site(site_id)
                if success:
                    # 重新加载数据
                    self._load_novel_sites()
                    self._update_status(f"{get_global_i18n().t('novel_sites.deleted_success')}: {site['name']}")
                else:
                    self._update_status(get_global_i18n().t('novel_sites.delete_failed'), "error")
            else:
                self._update_status(get_global_i18n().t('novel_sites.delete_failed'), "error")
    
    def _handle_batch_delete_confirm(self, result: Optional[bool]) -> None:
        """处理批量删除确认"""
        if result and self.selected_sites:
            deleted_count = 0
            failed_count = 0
            
            # 按索引从大到小删除，避免索引变化
            for index in sorted(self.selected_sites, reverse=True):
                if 0 <= index < len(self.novel_sites):
                    site = self.novel_sites[index]
                    site_id = site.get("id")
                    if site_id:
                        # 从数据库删除
                        success = self.database_manager.delete_novel_site(site_id)
                        if success:
                            deleted_count += 1
                        else:
                            failed_count += 1
            
            self.selected_sites.clear()
            # 重新加载数据
            self._load_novel_sites()
            
            if failed_count == 0:
                self._update_status(f"{get_global_i18n().t('novel_sites.batch_deleted_success')}: {deleted_count}")
            else:
                self._update_status(f"{get_global_i18n().t('novel_sites.batch_deleted_partial')}: {deleted_count}成功, {failed_count}失败", "error")
    
    def _show_edit_dialog(self) -> None:
        """显示编辑书籍网站对话框"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            # 计算当前页面的起始索引
            start_index = (self._current_page - 1) * self._sites_per_page
            # 计算全局索引
            global_index = start_index + table.cursor_row
            
            if global_index < len(self.novel_sites):
                site = self.novel_sites[global_index]
                from src.ui.dialogs.novel_site_dialog import NovelSiteDialog
                dialog = NovelSiteDialog(self.theme_manager, site)
                self.app.push_screen(dialog, lambda result: self._handle_edit_result(result, global_index))
            else:
                self._update_status(get_global_i18n().t('novel_sites.site_not_found'), "error")
        else:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
    
    def _open_note_dialog(self, site: Dict[str, Any]) -> None:
        """打开备注对话框"""
        try:
            # 获取当前网站的备注内容
            site_id = site.get('id')
            if not site_id:
                self._update_status(get_global_i18n().t('crawler.no_site_id'), "error")
                return
            
            # 从数据库加载现有备注
            current_note = self.database_manager.get_novel_site_note(site_id) or ""
            
            # 打开备注对话框
            def handle_note_dialog_result(result: Optional[str]) -> None:
                if result is not None:
                    # 保存备注到数据库
                    if self.database_manager.save_novel_site_note(site_id, result):
                        self._update_status(get_global_i18n().t('crawler.note_saved'), "success")
                    else:
                        self._update_status(get_global_i18n().t('crawler.note_save_failed'), "error")
                # 如果result为None，表示用户取消了操作
            
            self.app.push_screen(
                NoteDialog(
                    self.theme_manager,
                    site['name'],
                    current_note
                ),
                handle_note_dialog_result
            )
            
        except Exception as e:
            logger.error(f"打开备注对话框失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.open_note_dialog_failed')}: {str(e)}", "error")
    
    def _delete_selected(self) -> None:
        """删除选中的书籍网站"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            # 计算当前页面的起始索引
            start_index = (self._current_page - 1) * self._sites_per_page
            # 计算全局索引
            global_index = start_index + table.cursor_row
            
            if global_index < len(self.novel_sites):
                site = self.novel_sites[global_index]
                # 显示确认对话框
                from src.ui.dialogs.confirm_dialog import ConfirmDialog
                dialog = ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t('novel_sites.confirm_delete'),
                    f"{get_global_i18n().t('novel_sites.confirm_delete_message')}: {site['name']}"
                )
                self.app.push_screen(dialog, lambda confirmed: self._handle_delete_result(confirmed, global_index))
            else:
                self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
        else:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
    
    def _update_selection_display(self, table: DataTable, row_index: int) -> None:
        """更新选中状态显示（已废弃，通过_update_table统一更新）"""
        # 这个方法不再使用，通过_update_table统一处理选中状态显示
        pass
    
    def on_data_table_row_selected(self, event) -> None:
        """
        数据表行选择时的回调
        
        Args:
            event: 行选择事件
        """
        if event is None:
            # 处理从 key_enter 调用的情况
            table = self.query_one("#novel-sites-table", DataTable)
            if table.cursor_row is not None:
                # 计算当前页面的起始索引
                start_index = (self._current_page - 1) * self._sites_per_page
                # 计算全局索引
                global_index = start_index + table.cursor_row
                if global_index < len(self.novel_sites):
                    # 进入爬取管理页面
                    site = self.novel_sites[global_index]
                    self.app.push_screen("crawler_management", site)
        elif hasattr(event, 'row_key') and event.row_key is not None:
            # 从事件中获取全局索引
            try:
                global_index = int(event.row_key)
                if 0 <= global_index < len(self.novel_sites):
                    # 进入爬取管理页面
                    site = self.novel_sites[global_index]
                    try:
                        from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                        crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                        self.app.push_screen(crawler_screen)
                    except ImportError:
                        self.notify(get_global_i18n().t('novel_sites.crawl_page_unavailable'), severity="error")
            except (ValueError, TypeError):
                # 如果转换失败，尝试通过行数据查找
                table = self.query_one("#novel-sites-table", DataTable)
                if hasattr(event, 'cursor_row') and event.cursor_row is not None:
                    start_index = (self._current_page - 1) * self._sites_per_page
                    global_index = start_index + event.cursor_row
                    if global_index < len(self.novel_sites):
                        site = self.novel_sites[global_index]
                        try:
                            from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                            crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                            self.app.push_screen(crawler_screen)
                        except ImportError:
                            self.notify(get_global_i18n().t('novel_sites.crawl_page_unavailable'), severity="error")
    
    def on_virtual_data_table_row_selected(self, event) -> None:
        """处理虚拟数据表行选中事件（空格键触发）"""
        if hasattr(event, 'row_key') and event.row_key is not None:
            # 从事件中获取全局索引
            try:
                global_index = int(event.row_key)
                if 0 <= global_index < len(self.novel_sites):
                    # 切换选中状态
                    if global_index in self.selected_sites:
                        self.selected_sites.remove(global_index)
                    else:
                        self.selected_sites.add(global_index)
                    
                    # 更新选中状态显示
                    table = self.query_one("#novel-sites-table", DataTable)
                    self._update_selection_display(table, table.cursor_row if hasattr(table, 'cursor_row') and table.cursor_row is not None else 0)
            except (ValueError, TypeError):
                pass
    
    def on_data_table_cell_selected(self, event) -> None:
        """
        数据表单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        if event.coordinate is not None:
            # 获取表格和当前光标位置
            table = self.query_one("#novel-sites-table", DataTable)
            
            # 保存当前光标位置
            saved_row = event.coordinate.row
            saved_col = event.coordinate.column
            
            # 计算当前页面的起始索引
            start_index = (self._current_page - 1) * self._sites_per_page
            # 计算全局索引
            global_index = start_index + event.coordinate.row
            
            if global_index < len(self.novel_sites):
                site = self.novel_sites[global_index]
                
                # 切换选择状态（第一列）
                if event.coordinate.column == 0:
                    if global_index in self.selected_sites:
                        self.selected_sites.remove(global_index)
                    else:
                        self.selected_sites.add(global_index)
                    
                    # 重新渲染表格
                    self._update_table()
                    
                    # 恢复光标位置
                    try:
                        # 确保表格有焦点
                        table.focus()
                        
                        # 使用Textual的标准方法恢复光标位置
                        if hasattr(table, 'cursor_coordinate'):
                            table.cursor_coordinate = (saved_row, saved_col)
                        elif hasattr(table, 'cursor_row') and hasattr(table, 'cursor_column'):
                            table.cursor_row = saved_row
                            table.cursor_column = saved_col
                        elif hasattr(table, '_cursor_row') and hasattr(table, '_cursor_column'):
                            table._cursor_row = saved_row
                            table._cursor_column = saved_col
                            
                        # 强制刷新表格显示
                        table.refresh()
                    except Exception:
                        # 如果恢复失败，至少确保表格有焦点
                        try:
                            table.focus()
                        except Exception:
                            pass
                
                # 备注按钮（最后一列，索引为7）
                elif event.coordinate.column == 7:
                    self._open_note_dialog(site)
                    
                    # 恢复光标位置
                    try:
                        table.focus()
                        if hasattr(table, 'cursor_coordinate'):
                            table.cursor_coordinate = (saved_row, saved_col)
                        elif hasattr(table, 'cursor_row') and hasattr(table, 'cursor_column'):
                            table.cursor_row = saved_row
                            table.cursor_column = saved_col
                        elif hasattr(table, '_cursor_row') and hasattr(table, '_cursor_column'):
                            table._cursor_row = saved_row
                            table._cursor_column = saved_col
                        table.refresh()
                    except Exception:
                        try:
                            table.focus()
                        except Exception:
                            pass
    
    # Actions for BINDINGS
    def action_add_site(self) -> None:
        self._show_add_dialog()

    def action_edit_site(self) -> None:
        self._show_edit_dialog()

    def action_delete_site(self) -> None:
        self._delete_selected()

    def action_batch_delete(self) -> None:
        self._batch_delete()

    def action_toggle_row(self) -> None:
        """空格键 - 选中或取消选中当前行"""
        # 直接处理空格键，不依赖BINDINGS系统
        table = self.query_one("#novel-sites-table", DataTable)
        
        # 获取当前光标位置
        current_row_index = None
        
        # 首先尝试使用cursor_row
        if hasattr(table, 'cursor_row') and table.cursor_row is not None:
            current_row_index = table.cursor_row
        # 其次尝试使用cursor_coordinate
        elif hasattr(table, 'cursor_coordinate') and table.cursor_coordinate:
            coord = table.cursor_coordinate
            current_row_index = coord.row
        
        # 检查是否有有效的行索引
        if current_row_index is None:
            # 显示提示信息，要求用户先选择一行
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 检查行索引是否在有效范围内
        current_page_row_count = min(self._sites_per_page, len(self.novel_sites) - (self._current_page - 1) * self._sites_per_page)
        if current_row_index < 0 or current_row_index >= current_page_row_count:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 计算当前页的起始索引
        start_index = (self._current_page - 1) * self._sites_per_page
        
        # 检查当前行是否有数据
        if start_index + current_row_index >= len(self.novel_sites):
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 获取当前行的网站项
        site_item = self.novel_sites[start_index + current_row_index]
        if not site_item:
            return
        
        # 获取全局索引（与selected_sites中存储的索引类型一致）
        global_index = start_index + current_row_index
        
        # 切换选中状态
        if global_index in self.selected_sites:
            self.selected_sites.remove(global_index)
        else:
            self.selected_sites.add(global_index)
        
        # 更新表格显示
        self._update_table()
        
        # 更新状态显示
        selected_count = len(self.selected_sites)
        self._update_status(get_global_i18n().t('novel_sites.already_selected', counts=selected_count), "information")
        
        # 确保表格保持焦点
        try:
            table.focus()
        except Exception:
            pass
    
    def action_note(self) -> None:
        """M键 - 打开当前选中网站的备注对话框"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            # 计算当前页面的起始索引
            start_index = (self._current_page - 1) * self._sites_per_page
            # 计算全局索引
            global_index = start_index + table.cursor_row
            
            if global_index < len(self.novel_sites):
                site = self.novel_sites[global_index]
                self._open_note_dialog(site)
            else:
                self._update_status(get_global_i18n().t('novel_sites.site_not_found'), "error")
        else:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
        
        # 获取当前光标位置
        current_row_index = None
        current_col_index = 0
        
        # 首先尝试使用cursor_coordinate
        if hasattr(table, 'cursor_coordinate') and table.cursor_coordinate:
            coord = table.cursor_coordinate
            current_row_index = coord.row
            current_col_index = coord.column
        # 其次尝试使用cursor_row和cursor_column
        elif hasattr(table, 'cursor_row') and table.cursor_row is not None:
            current_row_index = table.cursor_row
            if hasattr(table, 'cursor_column') and table.cursor_column is not None:
                current_col_index = table.cursor_column
        # 最后尝试使用内部属性
        elif hasattr(table, '_cursor_row') and table._cursor_row is not None:
            current_row_index = table._cursor_row
            if hasattr(table, '_cursor_column') and table._cursor_column is not None:
                current_col_index = table._cursor_column
        
        # 检查是否有有效的行索引
        if current_row_index is None:
            # 显示提示信息，要求用户先选择一行
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 检查行索引是否在有效范围内
        current_page_row_count = min(self._sites_per_page, len(self.novel_sites) - (self._current_page - 1) * self._sites_per_page)
        if current_row_index < 0 or current_row_index >= current_page_row_count:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            return
        
        # 保存当前光标位置
        saved_row = current_row_index
        saved_col = current_col_index
        
        # 执行选择操作
        self._toggle_site_selection(table, current_row_index)
        
        # 恢复光标位置
        try:
            # 确保表格有焦点
            table.focus()
            
            # 使用Textual的标准方法恢复光标位置
            if hasattr(table, 'cursor_coordinate'):
                table.cursor_coordinate = (saved_row, saved_col)
            elif hasattr(table, 'cursor_row') and hasattr(table, 'cursor_column'):
                table.cursor_row = saved_row
                table.cursor_column = saved_col
            elif hasattr(table, '_cursor_row') and hasattr(table, '_cursor_column'):
                table._cursor_row = saved_row
                table._cursor_column = saved_col
                
            # 强制刷新表格显示
            table.refresh()
        except Exception:
            # 如果恢复失败，至少确保表格有焦点
            try:
                table.focus()
            except Exception:
                pass

    def action_enter_crawler(self) -> None:
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            self.on_data_table_row_selected(None)

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


    def _update_status(self, message: str, severity: str = "information") -> None:
        """更新状态信息"""
        status_label = self.query_one("#novel-sites-status", Label)
        status_label.update(message)
        
        # 根据严重程度设置样式
        if severity == "success":
            status_label.styles.color = "green"
        elif severity == "error":
            status_label.styles.color = "red"
        else:
            status_label.styles.color = "blue"
    
    def key_a(self) -> None:
        """A键 - 添加书籍网站"""
        if self._has_permission("novel_sites.add"):
            self._show_add_dialog()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_add_site'), severity="warning")
    
    def key_e(self) -> None:
        """E键 - 编辑选中的书籍网站"""
        if self._has_permission("novel_sites.edit"):
            self._show_edit_dialog()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_edit_site'), severity="warning")
    
    def key_d(self) -> None:
        """D键 - 删除选中的书籍网站"""
        if self._has_permission("novel_sites.delete"):
            self._delete_selected()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_delete_site'), severity="warning")
    
    def key_b(self) -> None:
        """B键 - 批量删除"""
        if self._has_permission("novel_sites.batch_delete"):
            self._batch_delete()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_batch_delete_site'), severity="warning")
    
    def key_enter(self) -> None:
        """Enter键 - 进入爬取管理页面"""
        if self._has_permission("novel_sites.enter_crawler"):
            table = self.query_one("#novel-sites-table", DataTable)
            # 使用DataTable的原生光标机制
            try:
                # 获取当前光标行
                if hasattr(table, 'cursor_row') and table.cursor_row is not None:
                    row_index = table.cursor_row
                    if row_index < len(table.rows):
                        # 计算当前页面的起始索引
                        start_index = (self._current_page - 1) * self._sites_per_page
                        # 计算全局索引
                        global_index = start_index + row_index
                        if global_index < len(self.novel_sites):
                            try:
                                from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                                site = self.novel_sites[global_index]
                                crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                                self.app.push_screen(crawler_screen)
                            except ImportError:
                                self.notify("爬取管理页面不可用", severity="error")
                else:
                    # 如果没有光标行，使用第一行
                    if len(table.rows) > 0:
                        start_index = (self._current_page - 1) * self._sites_per_page
                        global_index = start_index + 0
                        if global_index < len(self.novel_sites):
                            try:
                                from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                                site = self.novel_sites[global_index]
                                crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                                self.app.push_screen(crawler_screen)
                            except ImportError:
                                self.notify("爬取管理页面不可用", severity="error")
            except Exception as e:
                # 如果出错，尝试第一行
                try:
                    if len(table.rows) > 0:
                        start_index = (self._current_page - 1) * self._sites_per_page
                        global_index = start_index + 0
                        if global_index < len(self.novel_sites):
                            try:
                                from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                                site = self.novel_sites[global_index]
                                crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                                self.app.push_screen(crawler_screen)
                            except ImportError:
                                self.notify("爬取管理页面不可用", severity="error")
                except Exception:
                    pass
        else:
            self.notify(get_global_i18n().t('novel_sites.np_open_carwler'), severity="warning")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        # 获取表格控件
        table = self.query_one("#novel-sites-table", DataTable)
        
        # 先检查跨页导航条件
        if event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            if table.cursor_row == len(table.rows) - 1 and self._current_page < self._total_pages:
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
        
        if event.key == "escape" or event.key == "q":
            # ESC键或Q键返回
            self.app.pop_screen()
            event.stop()
        elif event.key == "enter":
            # Enter键进入爬取管理页面
            self.key_enter()
            event.prevent_default()
        elif event.key == "a":
            # A键添加网站
            if self._has_permission("novel_sites.add"):
                self._show_add_dialog()
            else:
                self.notify(get_global_i18n().t('novel_sites.np_add_site'), severity="warning")
            event.prevent_default()
        elif event.key == "e":
            # E键编辑选中的网站
            if self._has_permission("novel_sites.edit"):
                self._show_edit_dialog()
            else:
                self.notify(get_global_i18n().t('novel_sites.np_edit_site'), severity="warning")
            event.prevent_default()
        elif event.key == "d":
            # D键删除选中的网站
            if self._has_permission("novel_sites.delete"):
                self._delete_selected()
            else:
                self.notify(get_global_i18n().t('novel_sites.np_delete_site'), severity="warning")
            event.prevent_default()
        elif event.key == "b":
            # B键批量删除
            if self._has_permission("novel_sites.batch_delete"):
                self._batch_delete()
            else:
                self.notify(get_global_i18n().t('novel_sites.np_batch_delete_site'), severity="warning")
            event.prevent_default()
        elif event.key == "n":
            # N键下一页
            self._go_to_next_page()
            event.prevent_default()
        elif event.key == "p":
            # P键上一页
            self._go_to_prev_page()
            event.prevent_default()
        # 数字键功能 - 根据是否有选中项执行不同操作
        elif event.key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
            # 0键映射到第10位
            target_position = 9 if event.key == "0" else int(event.key) - 1
            
            # 将光标移动到当前页对应行
            self._move_cursor_to_position(target_position)
            event.stop()
    
    def _move_cursor_to_position(self, target_position: int) -> None:
        """将光标移动到当前页的指定行"""
        try:
            # 获取表格
            table = self.query_one("#novel-sites-table", DataTable)
            
            # 计算当前页的实际行数
            start_index = (self._current_page - 1) * self._sites_per_page
            current_page_rows = min(self._sites_per_page, len(self.novel_sites) - start_index)
            
            # 检查目标位置是否超出当前页的行数
            if target_position >= current_page_rows:
                target_position = current_page_rows - 1
            
            # 移动光标到目标行
            if hasattr(table, 'move_cursor'):
                table.move_cursor(row=target_position)
            else:
                # 使用键盘操作来移动光标
                # 先将光标移动到第一行
                while table.cursor_row > 0:
                    table.action_cursor_up()
                # 然后向下移动到目标位置
                for _ in range(target_position):
                    table.action_cursor_down()
            
            # 确保表格获得焦点
            table.focus()
            
            # 显示成功信息
            display_position = target_position + 1
            if display_position == 10:
                display_key = "0"
            else:
                display_key = str(display_position)
            
        except Exception as e:
            logger.error(f"移动光标失败: {e}")

    def _update_pagination_info(self) -> None:
        """更新分页信息显示"""
        try:
            total_sites = len(self.novel_sites)
            status_label = self.query_one("#novel-sites-status", Label)
            status_text = f"总共 {total_sites} 个网站 | 第 {self._current_page} / {self._total_pages} 页"
            status_label.update(status_text)
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
            
            first_btn.disabled = self._current_page <= 1
            prev_btn.disabled = self._current_page <= 1
            next_btn.disabled = self._current_page >= self._total_pages
            last_btn.disabled = self._current_page >= self._total_pages
        except Exception as e:
            logger.error(f"更新分页按钮状态失败: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
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
        elif event.button.id == "add-btn":
            self._show_add_dialog()
        elif event.button.id == "edit-btn":
            self._show_edit_dialog()
        elif event.button.id == "delete-btn":
            self._delete_selected()
        elif event.button.id == "batch-delete-btn":
            self._batch_delete()
        elif event.button.id == "back-btn":
            self.app.pop_screen()  # 返回上一页
    
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