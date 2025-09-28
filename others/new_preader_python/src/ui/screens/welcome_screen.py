"""
欢迎屏幕
"""


from typing import Dict, Any, Optional, List, ClassVar

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.app import ComposeResult, App
from textual.reactive import reactive
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.core.statistics_direct import StatisticsManagerDirect
from src.ui.styles.style_manager import ScreenStyleMixin

from src.utils.logger import get_logger

logger = get_logger(__name__)

class WelcomeScreen(ScreenStyleMixin, Screen[None]):
    """欢迎屏幕"""
    
    TITLE: ClassVar[Optional[str]] = None
    
    def __init__(self, theme_manager: ThemeManager, bookshelf: Bookshelf):
        """
        初始化欢迎屏幕
        
        Args:
            theme_manager: 主题管理器
            bookshelf: 书架
        """
        super().__init__()
        try:
            self.screen_title = t("welcome.title")
        except RuntimeError:
            # 如果i18n未初始化，使用默认标题
            self.screen_title = "欢迎"
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
    
    def compose(self) -> ComposeResult:
        """
        组合欢迎屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Vertical(
                Label(get_global_i18n().t('welcome.title_main'), id="welcome-title"),
                Label(get_global_i18n().t('app.description'), id="welcome-subtitle"),
                Label(get_global_i18n().t('welcome.description'), id="welcome-description"),
                Horizontal(
                    Button(get_global_i18n().t('welcome.open_book'), id="open-book-btn"),
                    Button(get_global_i18n().t('welcome.browse_library'), id="browse-library-btn"),
                    Button(get_global_i18n().t('welcome.get_books'), id="get-books-btn"),
                    Button(get_global_i18n().t('welcome.settings'), id="settings-btn"),
                    Button(get_global_i18n().t('welcome.statistics'), id="statistics-btn"),
                    Button(get_global_i18n().t('welcome.help'), id="help-btn"),
                    Button(get_global_i18n().t('welcome.exit'), id="exit-btn"),
                    id="welcome-buttons"
                ),
                # 功能描述区域
                Vertical(
                    Label(get_global_i18n().t('welcome.features_title'), id="features-title"),
                    Label(get_global_i18n().t('welcome.feature_1'), id="feature-1"),
                    Label(get_global_i18n().t('welcome.feature_2'), id="feature-2"), 
                    Label(get_global_i18n().t('welcome.feature_3'), id="feature-3"),
                    Label(get_global_i18n().t('welcome.feature_4'), id="feature-4"),
                    id="features-container"
                ),
                # 快捷键状态栏
                Horizontal(
                    Label(get_global_i18n().t('welcome.shortcut_f1'), id="shortcut-f1"),
                    Label(get_global_i18n().t('welcome.shortcut_f2'), id="shortcut-f2"),
                    Label(get_global_i18n().t('welcome.shortcut_f3'), id="shortcut-f3"),
                    Label(get_global_i18n().t('welcome.shortcut_f4'), id="shortcut-f4"),
                    Label(get_global_i18n().t('welcome.shortcut_f5'), id="shortcut-f5"),
                    Label(get_global_i18n().t('welcome.shortcut_f6'), id="shortcut-f6"),
                    Label(get_global_i18n().t('welcome.shortcut_esc'), id="shortcut-esc"),
                    id="shortcuts-bar"
                ),
                id="welcome-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用简单样式隔离
        from src.ui.styles.simple_style_isolation import apply_simple_style_isolation
        apply_simple_style_isolation(self)
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "open-book-btn":
            # 直接跳转到文件资源管理器
            self._open_file_explorer()
        elif event.button.id == "browse-library-btn":
            self.app.push_screen("bookshelf")  # 使用标准方法切换屏幕
        elif event.button.id == "get-books-btn":
            self.app.push_screen("get_books")  # 打开获取书籍页面
        elif event.button.id == "settings-btn":
            self.app.push_screen("settings")  # 打开设置页面
        elif event.button.id == "statistics-btn":
            self.app.push_screen("statistics")  # 打开统计页面
        elif event.button.id == "help-btn":
            self.app.push_screen("help")  # 打开帮助页面
        elif event.button.id == "exit-btn":
            self.app.exit() # 退出阅读器


    def key_f1(self) -> None:
        """F1快捷键 - 打开书籍"""
        # 直接跳转到文件资源管理器
        self._open_file_explorer()

    def _open_file_explorer(self) -> None:
        """打开文件资源管理器"""
        try:
            # 导入文件资源管理器屏幕
            from src.ui.screens.file_explorer_screen import FileExplorerScreen
            from src.core.statistics_direct import StatisticsManagerDirect
            from src.core.database_manager import DatabaseManager
            
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            
            # 创建统计管理器实例
            statistics_manager = StatisticsManagerDirect(db_manager)
            
            # 创建文件资源管理器屏幕 - 使用文件选择模式，并设置直接打开功能
            try:
                title = get_global_i18n().t("welcome.open_book")
            except RuntimeError:
                title = "打开书籍"
                
            file_explorer_screen = FileExplorerScreen(
                theme_manager=self.theme_manager,
                bookshelf=self.bookshelf,
                statistics_manager=statistics_manager,
                selection_mode="file",  # 文件选择模式
                title=title,  # 使用打开书籍的标题
                direct_open=True  # 直接打开文件进行阅读
            )
            
            # 跳转到文件资源管理器 - 不处理返回结果，保持原有的直接打开功能
            self.app.push_screen(file_explorer_screen)
            
        except Exception as e:
            logger.error(f"打开文件资源管理器失败: {e}")
            self.notify(f"打开文件资源管理器失败: {str(e)}", severity="error")

    def key_f2(self) -> None:
        """F2快捷键 - 浏览书库"""
        self.app.push_screen("bookshelf")

    def key_f3(self) -> None:
        """F3快捷键 - 获取书籍"""
        self.app.push_screen("get_books")

    def key_f4(self) -> None:
        """F4快捷键 - 打开设置"""
        self.app.push_screen("settings")

    def key_f5(self) -> None:
        """F5快捷键 - 打开统计"""
        self.app.push_screen("statistics")

    def key_f6(self) -> None:
        """F6快捷键 - 打开帮助"""
        self.app.push_screen("help")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键退出阅读器
            self.app.exit()
            event.prevent_default()