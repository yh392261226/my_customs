"""
欢迎屏幕
"""


from typing import Dict, Any, Optional, List, ClassVar

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, Header, Footer
from textual.app import ComposeResult, App
from textual.reactive import reactive
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.core.statistics_direct import StatisticsManagerDirect
from src.ui.styles.quick_fix_isolation import QuickIsolationMixin
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

from src.utils.logger import get_logger

logger = get_logger(__name__)

class WelcomeScreen(QuickIsolationMixin, Screen[None]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        super().on_mount()
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """欢迎屏幕"""
    
    TITLE: ClassVar[Optional[str]] = None
    CSS_PATH = '../styles/welcome_screen_overrides.tcss'

    # 使用 Textual BINDINGS 进行快捷键绑定
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("f1,1", "open_book", get_global_i18n().t('welcome.shortcut_f1')),
        ("f2,2", "browse_library", get_global_i18n().t('welcome.shortcut_f2')),
        ("f3,3", "get_books", get_global_i18n().t('welcome.shortcut_f3')),
        ("f4,4", "open_user_management", get_global_i18n().t('welcome.shortcut_f4')),
        ("f5,5", "open_settings", get_global_i18n().t('welcome.shortcut_f5')),
        ("f6,6", "open_statistics", get_global_i18n().t('welcome.shortcut_f6')),
        ("f7,7", "open_help", get_global_i18n().t('welcome.shortcut_f7')),
        ("escape,q", "exit_app", get_global_i18n().t('welcome.shortcut_esc'))
    ]
    
    def __init__(self, theme_manager: ThemeManager, bookshelf: Bookshelf):
        """
        初始化欢迎屏幕
        
        Args:
            theme_manager: 主题管理器
            bookshelf: 书架
        """
        super().__init__()
        self.title = t("welcome.title_main")
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
    
    def compose(self) -> ComposeResult:
        """
        组合欢迎屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Vertical(
                # Label(get_global_i18n().t('welcome.title_main'), id="welcome-title"),
                Label(get_global_i18n().t('app.description'), id="welcome-subtitle"),
                Label(get_global_i18n().t('welcome.description'), id="welcome-description"),
                Horizontal(
                    Button(get_global_i18n().t('welcome.open_book'), id="open-book-btn"),
                    Button(get_global_i18n().t('welcome.browse_library'), id="browse-library-btn"),
                    Button(get_global_i18n().t('welcome.get_books'), id="get-books-btn"),
                    Button(get_global_i18n().t('welcome.manage'), id="manage-btn"),
                    Button(get_global_i18n().t('welcome.settings'), id="settings-btn"),
                    Button(get_global_i18n().t('welcome.statistics'), id="statistics-btn"),
                    Button(get_global_i18n().t('welcome.help'), id="help-btn"),
                    Button(get_global_i18n().t('welcome.exit'), id="exit-btn"),
                    id="welcome-buttons", classes="btn-row"
                ),
                # 功能描述区域
                Vertical(
                    Label(get_global_i18n().t('welcome.features_title'), id="features-title"),
                    Label(get_global_i18n().t('welcome.feature_1'), id="feature-1"),
                    Label(get_global_i18n().t('welcome.feature_2'), id="feature-2"), 
                    Label(get_global_i18n().t('welcome.feature_3'), id="feature-3"),
                    Label(get_global_i18n().t('welcome.feature_4'), id="feature-4"),
                    Label(get_global_i18n().t('welcome.feature_5'), id="feature-5"),
                    id="features-container"
                ),
                # 快捷键状态栏
                # Horizontal(
                #     Label(get_global_i18n().t('welcome.shortcut_f1'), id="shortcut-f1"),
                #     Label(get_global_i18n().t('welcome.shortcut_f2'), id="shortcut-f2"),
                #     Label(get_global_i18n().t('welcome.shortcut_f3'), id="shortcut-f3"),
                #     Label(get_global_i18n().t('welcome.shortcut_f4'), id="shortcut-f4"),
                #     Label(get_global_i18n().t('welcome.shortcut_f5'), id="shortcut-f5"),
                #     Label(get_global_i18n().t('welcome.shortcut_f6'), id="shortcut-f6"),
                #     Label(get_global_i18n().t('welcome.shortcut_f7'), id="shortcut-f7"),
                #     Label(get_global_i18n().t('welcome.shortcut_esc'), id="shortcut-esc"),
                #     id="shortcuts-bar", classes="status-bar"
                # ),
                id="welcome-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 调用父类的on_mount方法（包含样式隔离）
        super().on_mount()
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)

        # 运行时更新快捷键描述，避免导入阶段访问未初始化的 i18n
        try:
            i18n = get_global_i18n()
            type(self).BINDINGS = [
                ("f1,1", "open_book", i18n.t('welcome.open_book')),
                ("f2,2", "browse_library", i18n.t('welcome.browse_library')),
                ("f3,3", "get_books", i18n.t('welcome.get_books')),
                ("f4,4", "open_user_management", i18n.t('welcome.manage')),
                ("f5,5", "open_settings", i18n.t('welcome.settings')),
                ("f6,6", "open_statistics", i18n.t('welcome.statistics')),
                ("f7,7", "open_help", i18n.t('welcome.help')),
                ("escape,q", "exit_app", i18n.t('welcome.exit')),
            ]
        except Exception:
            pass

        # 按权限禁用“管理”按钮
        try:
            if not getattr(self.app, "has_permission", lambda k: True)("admin.manage_users"):
                self.query_one("#manage-btn", Button).disabled = True
        except Exception:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        has_perm = getattr(self.app, "has_permission", lambda k: True)
        
        if event.button.id == "open-book-btn":
            if has_perm("welcome.open_book"):
                self._open_file_explorer()
            else:
                self.notify(get_global_i18n().t('welcome.np_open_book'), severity="warning")
        elif event.button.id == "browse-library-btn":
            if has_perm("welcome.browse_library"):
                self.app.push_screen("bookshelf")
            else:
                self.notify(get_global_i18n().t('welcome.np_open_bookshelf'), severity="warning")
        elif event.button.id == "get-books-btn":
            if has_perm("welcome.get_books"):
                self.app.push_screen("get_books")
            else:
                self.notify(get_global_i18n().t('welcome.np_get_books'), severity="warning")
        elif event.button.id == "settings-btn":
            if has_perm("welcome.settings"):
                self.app.push_screen("settings")
            else:
                self.notify(get_global_i18n().t('welcome.np_open_settings'), severity="warning")
        elif event.button.id == "statistics-btn":
            if has_perm("welcome.statistics"):
                self.app.push_screen("statistics")
            else:
                self.notify(get_global_i18n().t('welcome.np_open_statistics'), severity="warning")
        elif event.button.id == "help-btn":
            if has_perm("welcome.help"):
                self.app.push_screen("help")
            else:
                self.notify(get_global_i18n().t('welcome.np_open_help'), severity="warning")
        elif event.button.id == "manage-btn":
            if has_perm("welcome.manage"):
                self.app.push_screen("users_management")
            else:
                self.notify(get_global_i18n().t('welcome.np_open_manageuser'), severity="warning")
        elif event.button.id == "exit-btn":
            # 退出按钮不需要权限检查，用户总是可以退出应用
            self.app.exit()


    def key_f1(self) -> None:
        """F1快捷键 - 打开书籍"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.open_book"):
            self._open_file_explorer()
        else:
            self.notify(get_global_i18n().t('welcome.np_open_book'), severity="warning")

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
            self.notify(f"{get_global_i18n().t('welcome.open_file_explorer_failed')}: {str(e)}", severity="error")

    def key_f2(self) -> None:
        """F2快捷键 - 浏览书库"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.browse_library"):
            self.app.push_screen("bookshelf")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_bookshelf'), severity="warning")

    def key_f3(self) -> None:
        """F3快捷键 - 获取书籍"""
        if getattr(self.app, "has_permission", lambda k: True)("bookshelf.get_books"):
            self.app.push_screen("get_books")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_getbooks'), severity="warning")

    def key_f5(self) -> None:
        """F5快捷键 - 打开设置"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.settings"):
            self.app.push_screen("settings")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_settings'), severity="warning")

    def key_f6(self) -> None:
        """F6快捷键 - 打开统计"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.statistics"):
            self.app.push_screen("statistics")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_statistics'), severity="warning")

    def key_f7(self) -> None:
        """F7快捷键 - 打开帮助"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.help"):
            self.app.push_screen("help")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_help'), severity="warning")

    def key_f4(self) -> None:
        """F4快捷键 - 管理用户"""
        if getattr(self.app, "has_permission", lambda k: True)("admin.manage_users"):
            self.app.push_screen("users_management")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_manageuser'), severity="warning")

    # Actions for BINDINGS
    def action_open_book(self) -> None:
        self._open_file_explorer()

    def action_browse_library(self) -> None:
        self.app.push_screen("bookshelf")

    def action_get_books(self) -> None:
        if getattr(self.app, "has_permission", lambda k: True)("bookshelf.get_books"):
            self.app.push_screen("get_books")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_getbooks'), severity="warning")

    def action_open_settings(self) -> None:
        self.app.push_screen("settings")

    def action_open_statistics(self) -> None:
        self.app.push_screen("statistics")

    def action_open_help(self) -> None:
        self.app.push_screen("help")

    def action_open_user_management(self) -> None:
        """Action: 管理用户（F7）"""
        if getattr(self.app, "has_permission", lambda k: True)("admin.manage_users"):
            self.app.push_screen("users_management")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_manageuser'), severity="warning")

    # 移除 ESC 直接退出，保留显式“退出”按钮行为
    def action_exit_app(self) -> None:
        self.app.exit()

    def on_key(self, event: events.Key) -> None:
        """已由 BINDINGS 处理，避免重复触发"""
        pass