"""
获取书籍屏幕
"""

from ast import Yield
from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Label, DataTable, Input, Header, Footer
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

logger = get_logger(__name__)

class GetBooksScreen(Screen[None]):

    # 使用 Textual BINDINGS 进行快捷键绑定
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("n", "open_novel_sites", get_global_i18n().t('get_books.shortcut_n')),
        ("p", "open_proxy_list", get_global_i18n().t('get_books.shortcut_p')),
        ("enter", "open_selected", get_global_i18n().t('get_books.shortcut_enter')),
        ("space", "open_selected", get_global_i18n().t('get_books.shortcut_space')),
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
        
    def compose(self) -> ComposeResult:
        """
        组合获取书籍屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Horizontal(
                # Label(get_global_i18n().t('get_books.title'), id="get-books-title", classes="section-title"),
                Label(get_global_i18n().t('get_books.description'), id="get-books-description"),
                
                # 功能按钮区域
                Horizontal(
                    Button(get_global_i18n().t('get_books.novel_sites'), id="novel-sites-btn", classes="btn"),
                    Button(get_global_i18n().t('get_books.proxy_settings'), id="proxy-settings-btn", classes="btn"),
                    Button(get_global_i18n().t('get_books.back'), id="back-btn", classes="btn"),
                    id="get-books-buttons",
                    classes="btn-row"
                ),
                
                # 书籍网站列表预览
                Vertical(
                    Label(get_global_i18n().t('get_books.novel_sites_list'), id="novel-sites-list-title"),
                    DataTable(id="novel-sites-table"),
                    id="novel-sites-preview"
                ),
                
                # 代理设置预览
                Vertical(
                    Label(get_global_i18n().t('get_books.proxy_status'), id="proxy-status-title"),
                    Label("", id="proxy-status-info"),
                    id="proxy-settings-preview"
                ),
                
                # 快捷键状态栏
                # Horizontal(
                #     Label(get_global_i18n().t('get_books.shortcut_n'), id="shortcut-n"),
                #     Label(get_global_i18n().t('get_books.shortcut_p'), id="shortcut-p"),
                #     Label(f"{get_global_i18n().t('get_books.shortcut_space')} {get_global_i18n().t('get_books.shortcut_enter')}", id="shortcut-enter"),
                #     Label(get_global_i18n().t('get_books.shortcut_esc'), id="shortcut-esc"),
                #     id="get-books-shortcuts-bar",
                #     classes="status-bar"
                # ),
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
        table.add_columns(
            get_global_i18n().t('get_books.sequence'),  # 序号列
            get_global_i18n().t('get_books.site_name'),
            get_global_i18n().t('get_books.site_url'),
            get_global_i18n().t('get_books.proxy_enabled'),
            get_global_i18n().t('get_books.parser'),
            get_global_i18n().t('get_books.rating'),  # 星级列
            get_global_i18n().t('get_books.enter')  # 进入按钮列
        )
        
        # 启用隔行变色效果
        table.zebra_stripes = True

        # 加载书籍网站数据
        self._load_novel_sites()
        self._load_proxy_settings()
        
        # 检查按钮权限并禁用/启用按钮
        self._check_button_permissions()
        # 聚焦表格以接收键盘事件
        try:
            self.query_one("#novel-sites-table", DataTable).focus()
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

    def _load_novel_sites(self) -> None:
        """加载书籍网站数据"""
        # 从数据库加载书籍网站数据
        self.novel_sites = self.database_manager.get_novel_sites()
        
        # 更新数据表
        table = self.query_one("#novel-sites-table", DataTable)
        table.clear()
        
        for i, site in enumerate(self.novel_sites):
            proxy_status = get_global_i18n().t('common.yes') if site.get("proxy_enabled", False) else get_global_i18n().t('common.no')
            rating = site.get("rating", 2)  # 默认2星
            rating_display = self._get_rating_display(rating)
            
            table.add_row(
                str(i + 1),  # 序号，从1开始
                site.get("name", ""),
                site.get("url", ""),
                proxy_status,
                site.get("parser", ""),
                rating_display,  # 星级显示
                "➤ " + get_global_i18n().t('get_books.enter')  # 进入按钮
            )
    
        # 为数字快捷键1-9建立行索引映射
        try:
            self._shortcut_index_map = {str(i + 1): i for i in range(min(9, len(self.novel_sites)))}
        except Exception:
            self._shortcut_index_map = {}

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
            
        if event.button.id == "novel-sites-btn":
            if self._has_permission("get_books.manage_sites"):
                self.app.push_screen("novel_sites_management")  # 打开书籍网站管理页面
            else:
                self.notify(get_global_i18n().t('get_books.np_manage_booksites'), severity="warning")
        elif event.button.id == "proxy-settings-btn":
            if self._has_permission("get_books.manage_proxy"):
                self.app.push_screen("proxy_list")  # 打开代理列表页面
            else:
                self.notify(get_global_i18n().t('get_books.np_manage_proxy'), severity="warning")
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
        """根据行索引打开对应站点的爬取管理页面"""
        if 0 <= row_index < len(self.novel_sites):
            site = self.novel_sites[row_index]
            if self._has_permission("crawler.open"):
                from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                self.app.push_screen(crawler_screen)
            else:
                self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")

    def on_data_table_cell_selected(self, event) -> None:
        """
        数据表单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        # 检查是否点击了"进入"按钮列（第7列，索引6）
        if event.coordinate.column == 6:  # 第7列是进入按钮列
            table = self.query_one("#novel-sites-table", DataTable)
            row_index = event.coordinate.row
            if 0 <= row_index < len(self.novel_sites):
                site = self.novel_sites[row_index]
                # 权限校验：打开爬取管理页面需 crawler.open
                if self._has_permission("crawler.open"):
                    from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                    crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                    self.app.push_screen(crawler_screen)  # 打开爬取管理页面
                else:
                    self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
    
    def on_data_table_row_selected(self, event) -> None:
        """
        数据表行选择时的回调
        
        Args:
            event: 行选择事件
        """
        table = self.query_one("#novel-sites-table", DataTable)
        
        # 获取当前选中的行索引
        if event is None:
            # 处理从 key_enter 调用的情况
            row_index = table.cursor_row
        elif hasattr(event, 'row_key') and event.row_key is not None:
            # 处理行选择事件
            row_index = int(event.row_key.value)
        else:
            return
            
        # 确保行索引有效
        if row_index is None or row_index < 0 or row_index >= len(self.novel_sites):
            return
            
        # 获取对应的网站数据
        site = self.novel_sites[row_index]
        
        # 权限校验：打开爬取管理页面需 crawler.open
        if self._has_permission("crawler.open"):
            from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
            crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
            self.app.push_screen(crawler_screen)  # 打开爬取管理页面
        else:
            self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")
    
    def key_n(self) -> None:
        """N键 - 打开书籍网站管理"""
        if self._has_permission("get_books.manage_sites"):
            self.app.push_screen("novel_sites_management")
        else:
            self.notify(get_global_i18n().t('get_books.np_manage_booksites'), severity="warning")
    
    def key_p(self) -> None:
        """P键 - 打开代理设置"""
        if self._has_permission("get_books.manage_proxy"):
            self.app.push_screen("proxy_list")
        else:
            self.notify(get_global_i18n().t('get_books.np_manage_proxy'), severity="warning")
    
    def key_enter(self) -> None:
        """Enter键 - 打开选中的书籍网站"""
        if self._has_permission("crawler.open"):
            table = self.query_one("#novel-sites-table", DataTable)
            if table.cursor_row is not None:
                self.on_data_table_row_selected(None)
        else:
            self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")

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

    def action_open_selected(self) -> None:
        if self._has_permission("crawler.open"):
            table = self.query_one("#novel-sites-table", DataTable)
            if table.cursor_row is not None:
                self.on_data_table_row_selected(None)
        else:
            self.notify(get_global_i18n().t('get_books.np_open_carwler'), severity="warning")

    def action_back(self) -> None:
        self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        # 数字键 1-9：打开对应行的“进入”
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

        if event.key == "escape":
            # ESC键返回（仅一次）
            self.app.pop_screen()
            event.stop()