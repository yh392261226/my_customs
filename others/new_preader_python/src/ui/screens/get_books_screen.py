"""
获取书籍屏幕
"""

from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Label, DataTable, Input
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


    
    # 加载CSS样式
    CSS_PATH = "../styles/get_books_screen.css"
    
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
        
    def compose(self) -> ComposeResult:
        """
        组合获取书籍屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Horizontal(
                Label(get_global_i18n().t('get_books.title'), id="get-books-title"),
                Label(get_global_i18n().t('get_books.description'), id="get-books-description"),
                
                # 功能按钮区域
                Horizontal(
                    Button(get_global_i18n().t('get_books.novel_sites'), id="novel-sites-btn"),
                    Button(get_global_i18n().t('get_books.proxy_settings'), id="proxy-settings-btn"),
                    Button(get_global_i18n().t('get_books.back'), id="back-btn"),
                    id="get-books-buttons"
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
                Horizontal(
                    Label(get_global_i18n().t('get_books.shortcut_n'), id="shortcut-n"),
                    Label(get_global_i18n().t('get_books.shortcut_p'), id="shortcut-p"),
                    Label(get_global_i18n().t('get_books.shortcut_enter'), id="shortcut-enter"),
                    Label(get_global_i18n().t('get_books.shortcut_esc'), id="shortcut-esc"),
                    id="get-books-shortcuts-bar"
                ),
                id="get-books-container"
            )
        )
    
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
            get_global_i18n().t('get_books.site_name'),
            get_global_i18n().t('get_books.site_url'),
            get_global_i18n().t('get_books.proxy_enabled'),
            get_global_i18n().t('get_books.parser'),
            get_global_i18n().t('get_books.enter')  # 进入按钮列
        )
        
        # 加载书籍网站数据
        self._load_novel_sites()
        self._load_proxy_settings()
    
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
    
    def _load_novel_sites(self) -> None:
        """加载书籍网站数据"""
        # 从数据库加载书籍网站数据
        self.novel_sites = self.database_manager.get_novel_sites()
        
        # 更新数据表
        table = self.query_one("#novel-sites-table", DataTable)
        table.clear()
        
        for site in self.novel_sites:
            proxy_status = get_global_i18n().t('common.yes') if site.get("proxy_enabled", False) else get_global_i18n().t('common.no')
            table.add_row(
                site.get("name", ""),
                site.get("url", ""),
                proxy_status,
                site.get("parser", ""),
                "➤ " + get_global_i18n().t('get_books.enter')  # 进入按钮
            )
    
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
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "novel-sites-btn":
            self.app.push_screen("novel_sites_management")  # 打开书籍网站管理页面
        elif event.button.id == "proxy-settings-btn":
            self.app.push_screen("proxy_list")  # 打开代理列表页面
        elif event.button.id == "back-btn":
            self.app.pop_screen()  # 返回上一页
    
    def on_data_table_cell_selected(self, event) -> None:
        """
        数据表单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        # 检查是否点击了"进入"按钮列（第5列，索引4）
        if event.coordinate.column == 4:  # 第5列是进入按钮列
            table = self.query_one("#novel-sites-table", DataTable)
            row_index = event.coordinate.row
            if 0 <= row_index < len(self.novel_sites):
                site = self.novel_sites[row_index]
                # 动态创建爬取管理屏幕实例
                from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                self.app.push_screen(crawler_screen)  # 打开爬取管理页面
    
    def on_data_table_row_selected(self, event) -> None:
        """
        数据表行选择时的回调
        
        Args:
            event: 行选择事件
        """
        if event is None:
            # 处理从 key_enter 调用的情况
            table = self.query_one("#novel-sites-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(table.rows):
                row_data = table.get_row_at(table.cursor_row)
                if row_data and len(row_data) > 0:
                    site_name = row_data[0]  # 第一列是网站名称
                    for site in self.novel_sites:
                        if site["name"] == site_name:
                            # 动态创建爬取管理屏幕实例
                            from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                            crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                            self.app.push_screen(crawler_screen)  # 打开爬取管理页面
                            break
        elif event.row_key and hasattr(event.row_key, 'value'):
            site_index = int(event.row_key.value)
            if 0 <= site_index < len(self.novel_sites):
                site = self.novel_sites[site_index]
                # 动态创建爬取管理屏幕实例
                from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
                crawler_screen = CrawlerManagementScreen(self.theme_manager, site)
                self.app.push_screen(crawler_screen)  # 打开爬取管理页面
    
    def key_n(self) -> None:
        """N键 - 打开书籍网站管理"""
        self.app.push_screen("novel_sites_management")
    
    def key_p(self) -> None:
        """P键 - 打开代理设置"""
        self.app.push_screen("proxy_list")
    
    def key_enter(self) -> None:
        """Enter键 - 打开选中的书籍网站"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            self.on_data_table_row_selected(None)
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回
            self.app.pop_screen()
            event.prevent_default()