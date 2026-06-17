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

    """欢迎屏幕"""
    
    TITLE: ClassVar[Optional[str]] = None
    CSS_PATH = '../styles/welcome_screen_overrides.tcss'

    # 使用 Textual BINDINGS 进行快捷键绑定
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("f1,1", "open_book", get_global_i18n().t('welcome.shortcut_f1')),
        ("f2,2", "browse_library", get_global_i18n().t('welcome.shortcut_f2')),
        ("f3,3", "get_books", get_global_i18n().t('welcome.shortcut_f3')),
        ("f4,4", "open_browser_reader", get_global_i18n().t('welcome.shortcut_f4')),
        ("f5,5", "open_user_management", get_global_i18n().t('welcome.shortcut_f5')),
        ("f6,6", "open_settings", get_global_i18n().t('welcome.shortcut_f6')),
        ("f7,7", "open_statistics", get_global_i18n().t('welcome.shortcut_f7')),
        ("f8,8", "open_help", get_global_i18n().t('welcome.shortcut_f8')),
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
        self.sub_title = t('app.description')
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
    
    def compose(self) -> ComposeResult:
        """
        组合欢迎屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header(
            time_format=None,
            show_clock=True,
            id="welcome-header",
            name="welcome-header",
        )
        yield Container(
            Vertical(
                # Label(get_global_i18n().t('welcome.title_main'), id="welcome-title"),
                Label(get_global_i18n().t('app.description'), id="welcome-subtitle"),
                Label(get_global_i18n().t('welcome.description'), id="welcome-description"),
                Horizontal(
                    Button(get_global_i18n().t('welcome.open_book'), id="open-book-btn"),
                    Button(get_global_i18n().t('welcome.browse_library'), id="browse-library-btn"),
                    Button(get_global_i18n().t('welcome.get_books'), id="get-books-btn"),
                    Button(get_global_i18n().t('welcome.browser_reader'), id="browser-reader-btn"),
                    Button(get_global_i18n().t('welcome.manage'), id="manage-btn"),
                    Button(get_global_i18n().t('welcome.settings'), id="settings-btn"),
                    Button(get_global_i18n().t('welcome.statistics'), id="statistics-btn"),
                    Button(get_global_i18n().t('welcome.help'), id="help-btn"),
                    Button(get_global_i18n().t('welcome.exit'), id="exit-btn"),
                    id="welcome-buttons", classes="btn-row"
                ),
                # 用户登陆信息区
                Vertical(
                    Label(get_global_i18n().t('welcome.welcome_message'), id="user-info-title"),
                    Label("", id="user-info"),
                    id="user-info-container",
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
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)

        # 运行时更新快捷键描述，避免导入阶段访问未初始化的 i18n
        try:
            i18n = get_global_i18n()
            type(self).BINDINGS = [
                ("f1,1", "open_book", i18n.t('welcome.open_book')),
                ("f2,2", "browse_library", i18n.t('welcome.browse_library')),
                ("f3,3", "get_books", i18n.t('welcome.get_books')),
                ("f4,4", "open_browser_reader", i18n.t('welcome.browser_reader')),
                ("f5,5", "open_user_management", i18n.t('welcome.manage')),
                ("f6,6", "open_settings", i18n.t('welcome.settings')),
                ("f7,7", "open_statistics", i18n.t('welcome.statistics')),
                ("f8,8", "open_help", i18n.t('welcome.help')),
                ("escape,q", "exit_app", i18n.t('welcome.exit')),
            ]
        except Exception:
            pass

        # 当多用户模式启用的时候, user-info-container会显示, 其他时候隐藏
        # 检查是否是多用户模式
        from src.utils.multi_user_manager import multi_user_manager
        is_multi_user = multi_user_manager.is_multi_user_enabled()
        current_user = getattr(self.app, 'current_user', None)

        if is_multi_user and current_user:
            userinfo = f"ID: {current_user.get('id')}  ▚  Name: {current_user.get('username')} "
            self.query_one("#user-info", Label).update(userinfo)
            self.query_one("#user-info-container", Vertical).visible = True
        else:
            self.query_one("#user-info-container", Vertical).visible = False

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
        elif event.button.id == "browser-reader-btn":
            if has_perm("welcome.browser_reader"):
                self._open_browser_reader()
            else:
                self.notify(get_global_i18n().t('welcome.np_browser_reader'), severity="warning")
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
        if getattr(self.app, "has_permission", lambda k: True)("welcome.get_books"):
            self.app.push_screen("get_books")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_getbooks'), severity="warning")

    def key_f5(self) -> None:
        """F5快捷键 - 管理用户"""
        if getattr(self.app, "has_permission", lambda k: True)("admin.manage_users"):
            self.app.push_screen("users_management")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_manageuser'), severity="warning")

    def key_f6(self) -> None:
        """F6快捷键 - 打开设置"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.settings"):
            self.app.push_screen("settings")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_settings'), severity="warning")

    def key_f7(self) -> None:
        """F7快捷键 - 打开统计"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.statistics"):
            self.app.push_screen("statistics")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_statistics'), severity="warning")

    def key_f8(self) -> None:
        """F8快捷键 - 打开帮助"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.help"):
            self.app.push_screen("help")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_help'), severity="warning")

    # Actions for BINDINGS
    def action_open_book(self) -> None:
        if getattr(self.app, "has_permission", lambda k: True)("welcome.open_book"):
            self._open_file_explorer()
        else:
            self.notify(get_global_i18n().t('welcome.np_open_book'), severity="warning")

    def action_browse_library(self) -> None:
        if getattr(self.app, "has_permission", lambda k: True)("welcome.browse_library"):
            self.app.push_screen("bookshelf")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_bookshelf'), severity="warning")
            
    def action_get_books(self) -> None:
        if getattr(self.app, "has_permission", lambda k: True)("welcome.get_books"):
            self.app.push_screen("get_books")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_getbooks'), severity="warning")

    def action_open_browser_reader(self) -> None:
        """Action: 打开浏览器阅读器（F4）"""
        if getattr(self.app, "has_permission", lambda k: True)("welcome.browser_reader"):
            self._open_browser_reader()
        else:
            self.notify(get_global_i18n().t('welcome.np_browser_reader'), severity="warning")

    def action_open_settings(self) -> None:
        if getattr(self.app, "has_permission", lambda k: True)("welcome.settings"):
            self.app.push_screen("settings")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_settings'), severity="warning")

    def action_open_statistics(self) -> None:
        if getattr(self.app, "has_permission", lambda k: True)("welcome.statistics"):
            self.app.push_screen("statistics")
        else:
            self.notify(get_global_i18n().t('welcome.np_open_statistics'), severity="warning")

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

    def _open_browser_reader(self) -> None:
            """打开浏览器阅读器（根据设置打开起始页）"""
            try:
                from src.utils.browser_reader import BrowserReader
                from src.core.bookmark import BookmarkManager
                from src.config.config_manager import ConfigManager
                import tempfile
                import os

                # 获取起始页设置
                config_manager = ConfigManager.get_instance()
                config = config_manager.get_config()
                start_page = config.get("browser", {}).get("start_page", "last_book")

                logger.info(f"浏览器阅读器起始页设置: {start_page}")

                # 根据起始页设置决定打开方式
                if start_page == "last_book":
                    # 尝试获取上一次阅读的书籍
                    last_book_path = None
                    try:
                        bookmark_manager = BookmarkManager()
                        # 获取最近有阅读记录的书籍
                        last_book = bookmark_manager.get_last_read_book()
                        if last_book:
                            last_book_path = last_book.get('book_path')
                            logger.info(f"找到上一次阅读的书籍: {last_book_path}")
                    except Exception as e:
                        logger.warning(f"获取上一次阅读书籍失败: {e}")

                    # 如果找到上一次的书籍，直接打开
                    if last_book_path and os.path.exists(last_book_path):
                        logger.info(f"打开上一次阅读的书籍: {last_book_path}")
                        success, message = BrowserReader.open_book_in_browser(
                            last_book_path,
                            theme="light"
                        )
                    else:
                        # 书籍不存在，创建欢迎页临时文件
                        logger.info("上一次阅读的书籍不存在，创建欢迎页临时文件")
                        success, message = self._create_welcome_temp_file()
                else:
                    # start_page == "welcome"，创建欢迎页临时文件
                    logger.info("使用欢迎页作为起始页")
                    success, message = self._create_welcome_temp_file()

                if success:
                    logger.info(f"浏览器阅读器已打开: {message}")
                    self.notify(get_global_i18n().t('welcome.browser_reader_opened', title="浏览器阅读器"), severity="information")
                else:
                    logger.error(f"浏览器阅读器打开失败: {message}")
                    self.notify(get_global_i18n().t('welcome.browser_reader_open_failed', message=message), severity="error")

            except Exception as e:
                logger.error(get_global_i18n().t('welcome.browser_reader_open_failed', message=str(e)))
                self.notify(get_global_i18n().t('welcome.browser_reader_open_failed', message=str(e)), severity="error")

    def _create_welcome_temp_file(self) -> tuple[bool, str]:
        """创建欢迎页临时文件并打开浏览器阅读器

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            from src.utils.browser_reader import BrowserReader
            import tempfile
            import os

            # 创建一个临时文件用于浏览器阅读器
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, "welcome.txt")

            # 创建临时文件内容
            library_content = """🌐 浏览器阅读器

欢迎使用浏览器阅读器！

请使用书库功能添加书籍，或者使用文件导入功能打开本地书籍文件。

提示：
- 支持TXT、EPUB等多种格式
- 自动保存阅读进度
- 可自定义主题和字体
"""

            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(library_content)

            # 使用open_book_in_browser打开，确保启动后端服务器
            success, message = BrowserReader.open_book_in_browser(
                temp_file,
                theme="light"
            )

            return success, message
        except Exception as e:
            logger.error(f"创建欢迎页临时文件失败: {e}")
            return False, str(e)