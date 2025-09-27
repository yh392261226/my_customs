"""
应用程序主界面
"""


from typing import Dict, Any, Optional, List

import os
from typing import Optional
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual import on
import asyncio
from textual.message import Message
from typing import Optional as _Optional
import asyncio as _asyncio

from src.ui.screens.welcome_screen import WelcomeScreen
from src.ui.screens.reader_screen import ReaderScreen
from src.ui.screens.bookshelf_screen import BookshelfScreen
from src.ui.screens.settings_screen import SettingsScreen
from src.ui.screens.help_screen import HelpScreen
from src.ui.screens.statistics_screen import StatisticsScreen
from src.ui.screens.boss_key_screen import BossKeyScreen
from src.core.bookshelf import Bookshelf
from src.core.database_manager import DatabaseManager
from src.core.statistics_direct import StatisticsManagerDirect
from src.config.config_manager import ConfigManager
from src.locales.i18n import I18n
from src.locales.i18n_manager import init_global_i18n, get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import LoggerSetup
from src.core.bookshelf import Bookshelf
from src.core.statistics import StatisticsManager
from src.config.settings.setting_registry import SettingRegistry
from src.config.settings.setting_factory import initialize_settings_registry
from src.ui.messages import RefreshBookshelfMessage, RequestPasswordMessage, RefreshContentMessage

from src.utils.logger import get_logger

logger = get_logger(__name__)

class NewReaderApp(App[None]):
    """NewReader应用程序主类"""
    
    TITLE = None
    SUB_TITLE = None
    
    CSS_PATH = "styles/styles.css"
    
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("h", "show_help", "帮助"),
        Binding("k", "show_bookshelf", "书架"),
        Binding("S", "show_settings", "设置"),
        Binding("c", "show_statistics", "统计"),
        Binding("/", "boss_key", "老板键"),
    ]
    
    def __init__(self, config_manager: ConfigManager, book_file: Optional[str] = None):
        """
        初始化应用程序
        
        Args:
            config_manager: 配置管理器实例
            book_file: 可选，直接打开的小说文件路径
        """
        super().__init__()
        
        # 初始化配置管理器
        self.config_manager = config_manager
        self.book_file = book_file
        
        # 初始化国际化支持
        config = self.config_manager.get_config()
        locale_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
        default_locale = config.get("app", {}).get("language", "zh_CN")
        
        # 初始化全局i18n实例
        init_global_i18n(locale_dir, default_locale)
        self.i18n = get_global_i18n()
        
        # 设置模块日志
        self.logger = logger
        self.logger.debug(get_global_i18n().t("app.init_start"))
        
        # 初始化主题管理器
        theme_name = config.get("app", {}).get("theme", "dark")
        self.theme_manager = ThemeManager(theme_name)
        
        # 初始化书架
        self.bookshelf = Bookshelf(config.get("app", {}).get("library_path", "library"))
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        
        # 初始化主事件循环变量
        self._main_loop = None
        
        # 初始化统计管理器
        self.statistics_manager = StatisticsManagerDirect(self.db_manager)
        
        # 初始化书签管理器
        from src.core.bookmark import BookmarkManager
        self.bookmark_manager = BookmarkManager()
        
        # 初始化动画管理器
        from src.ui.components.loading_animation import AnimationManager, AnimationType, SpinnerAnimation
        self.animation_manager = AnimationManager()
        self.animation_manager.set_default_animation(SpinnerAnimation({}))
        
        # 初始化设置系统
        self.settings_registry = SettingRegistry()
        initialize_settings_registry(self.settings_registry)
        
        # 从配置文件加载设置值
        self._load_settings_from_config()
        
        # 更新应用标题
        self._title = get_global_i18n().t("app.name")
        self._sub_title = get_global_i18n().t("app.description")
        
        # 安装所有屏幕
        self.install_screen(WelcomeScreen(self.theme_manager, self.bookshelf), name="welcome")
        self.install_screen(BookshelfScreen(self.theme_manager, self.bookshelf, self.statistics_manager), name="bookshelf")
        # 创建一个默认的Book对象用于初始化阅读器屏幕
        from src.core.book import Book
        default_book = Book("", get_global_i18n().t("app.default_book"), get_global_i18n().t("app.unknown_author"))
        self.install_screen(ReaderScreen(default_book, self.theme_manager, self.statistics_manager, self.bookmark_manager), name="terminal_reader")
        self.install_screen(SettingsScreen(self.theme_manager, self.config_manager), name="settings")
        self.install_screen(HelpScreen(), name="help")
        self.install_screen(StatisticsScreen(self.theme_manager, self.statistics_manager), name="statistics")
        
        # 安装获取书籍相关屏幕
        from src.ui.screens.get_books_screen import GetBooksScreen
        from src.ui.screens.proxy_settings_screen import ProxySettingsScreen
        from src.ui.screens.novel_sites_management_screen import NovelSitesManagementScreen
        from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
        
        self.install_screen(GetBooksScreen(self.theme_manager), name="get_books")
        self.install_screen(ProxySettingsScreen(self.theme_manager), name="proxy_settings")
        self.install_screen(NovelSitesManagementScreen(self.theme_manager), name="novel_sites_management")
        # 爬取管理屏幕需要动态创建，所以只注册类
        self.install_screen(CrawlerManagementScreen, name="crawler_management")
        
        logger.info(get_global_i18n().t("app.screen_installed"))
    
    def _load_settings_from_config(self) -> None:
        """从配置文件加载设置值到设置系统"""
        try:
            config = self.config_manager.get_config()
            
            # 加载阅读设置
            reading_config = config.get("reading", {})
            if "font_size" in reading_config:
                self.settings_registry.set_value("reading.font_size", reading_config["font_size"])
            if "line_spacing" in reading_config:
                self.settings_registry.set_value("reading.line_spacing", reading_config["line_spacing"])
            if "paragraph_spacing" in reading_config:
                self.settings_registry.set_value("reading.paragraph_spacing", reading_config["paragraph_spacing"])
            if "remember_position" in reading_config:
                self.settings_registry.set_value("reading.remember_position", reading_config["remember_position"])
            if "auto_page_turn_interval" in reading_config:
                self.settings_registry.set_value("reading.auto_page_turn_interval", reading_config["auto_page_turn_interval"])
            if "pagination_strategy" in reading_config:
                self.settings_registry.set_value("reading.pagination_strategy", reading_config["pagination_strategy"])
            
            # 加载外观设置
            appearance_config = config.get("appearance", {})
            if "theme" in appearance_config:
                self.settings_registry.set_value("appearance.theme", appearance_config["theme"])
            if "show_icons" in appearance_config:
                self.settings_registry.set_value("appearance.show_icons", appearance_config["show_icons"])
            if "animation_enabled" in appearance_config:
                self.settings_registry.set_value("appearance.animation_enabled", appearance_config["animation_enabled"])
            if "border_style" in appearance_config:
                self.settings_registry.set_value("appearance.border_style", appearance_config["border_style"])
            if "progress_bar_style" in appearance_config:
                self.settings_registry.set_value("appearance.progress_bar_style", appearance_config["progress_bar_style"])
            
            logger.info(get_global_i18n().t("app.loaded_settings"))
            
        except Exception as e:
            logger.error(f"{get_global_i18n().t("app.loaded_settings_failed")}: {e}")
    
    def compose(self) -> ComposeResult:
        """
        组合应用程序界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(id="app-content")
        yield Footer()
    
    def on_mount(self) -> None:
        """应用程序挂载时的回调"""
        # 设置全局 App 实例，供解析线程获取并在 UI 线程弹窗
        try:
            # 引用模块级变量并赋值
            global _app_instance
            _app_instance = self
        except Exception:
            pass
        # 记录主事件循环以便跨线程安全调度
        try:
            import asyncio as _asyncio
            self._main_loop = _asyncio.get_running_loop()
        except Exception:
            self._main_loop = None

        # 应用当前主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 初始化默认加载动画组件
        self._initialize_loading_animation()
        
        # 如果指定了小说文件，直接打开阅读
        if self.book_file:
            self._open_book_file(self.book_file)
        else:
            # 显示欢迎屏幕（作为默认页面）
            self.push_screen("welcome")
    
    def action_show_help(self) -> None:
        """显示帮助屏幕"""
        self.push_screen(HelpScreen())
    
    def action_show_bookshelf(self) -> None:
        """显示书架屏幕"""
        self.push_screen(BookshelfScreen(self.theme_manager, self.bookshelf, self.statistics_manager))
    
    def action_show_settings(self) -> None:
        """显示设置屏幕"""
        # 使用现代设置屏幕
        self.push_screen("settings")
    
    def action_show_statistics(self) -> None:
        """显示统计屏幕"""
        self.push_screen(StatisticsScreen(self.theme_manager, self.statistics_manager))
    
    def _initialize_loading_animation(self) -> None:
        """初始化加载动画组件"""
        try:
            from src.ui.components.loading_animation import SpinnerAnimation
            
            # 确保动画管理器已初始化
            if not hasattr(self, 'animation_manager') or self.animation_manager is None:
                from src.ui.components.loading_animation import AnimationManager
                self.animation_manager = AnimationManager()
            
            # 设置默认动画实例
            self.animation_manager.set_default_animation(SpinnerAnimation({}))
            
            logger.debug(get_global_i18n().t("common.default_animation_inited"))
            
        except ImportError as e:
            logger.warning(get_global_i18n().t("common.load_animation_failed", error=str(e)))
        except Exception as e:
            logger.error(get_global_i18n().t("common.init_animation_error", error=str(e)))
    
    def action_boss_key(self) -> None:
        """激活老板键"""
        self.push_screen(BossKeyScreen(self.theme_manager))
    
    def _open_book_file(self, book_file: str) -> None:
        """
        直接打开指定的书籍文件
        
        Args:
            book_file: 书籍文件路径
        """
        try:
            # 创建临时的Book对象
            from src.core.book import Book
            import os
            
            # 从文件路径提取书籍信息
            file_name = os.path.basename(book_file)
            book_name = os.path.splitext(file_name)[0]
            
            # 创建Book对象并加载内容
            book = Book(book_file, book_name, get_global_i18n().t("app.unknown_author"))
            
            # 检查是否为PDF文件，如果是加密PDF需要处理密码
            if book_file.lower().endswith('.pdf'):
                # 检查PDF是否需要密码
                from src.parsers.pdf_encrypt_parser import PdfEncryptParser
                pdf_parser = PdfEncryptParser(app=self)
                if pdf_parser.is_encrypted_pdf(book_file):
                    # CLI模式下需要从命令行获取密码
                    password = self._get_cli_password(book_file)
                    if password is not None:
                        # 使用密码重新创建Book对象
                        book = Book(book_file, book_name, get_global_i18n().t("app.unknown_author"), password=password)
            
            # 加载书籍内容
            content = book.get_content()
            
            if not content:
                self.notify(f"{get_global_i18n().t("app.load_content_failed")}: {book_file}", severity="error")
                self.push_screen("bookshelf")
                return
            
            # 打开终端阅读器屏幕（使用新的现代化架构）
            self.push_screen(ReaderScreen(book, self.theme_manager, self.statistics_manager, self.bookmark_manager))
            
        except Exception as e:
            self.notify(f"{get_global_i18n().t("app.open_book_failed")}: {e}", severity="error")
            # 失败时回退到书架界面
            self.push_screen("bookshelf")
    
    def _get_cli_password(self, file_path: str) -> Optional[str]:
        """
        CLI模式下获取PDF密码
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            密码字符串，如果用户取消则为None
        """
        try:
            import getpass
            print(f"\nPDF文件需要密码: {os.path.basename(file_path)}")
            print("请输入密码（直接回车使用空密码，输入'cancel'取消）: ")
            password = getpass.getpass("密码: ")
            
            if password.lower() == 'cancel':
                return None
            return password
        except Exception as e:
            logger.error(f"CLI密码输入失败: {e}")
            return None
    
    def open_book(self, book_id: str) -> None:
        """
        打开书籍
        
        Args:
            book_id: 书籍ID
        """
        book = self.bookshelf.get_book(book_id)
        if book:
            # 使用新的终端阅读器屏幕
            self.push_screen(ReaderScreen(book, self.theme_manager, self.statistics_manager, self.bookmark_manager))
        else:
            self.notify(get_global_i18n().t("error.book_not_found"), severity="error")
    
    @on(RequestPasswordMessage)
    async def handle_request_password(self, message: RequestPasswordMessage) -> None:
        """
        主线程处理解析线程发来的密码输入请求（装饰器版本）
        """
        try:
            try:
                if hasattr(self, "animation_manager") and getattr(self, "animation_manager"):
                    self.animation_manager.hide_default()
            except Exception:
                pass
            from src.ui.dialogs.password_dialog import PasswordDialog
            self.logger.info(f"App.handle_request_password: showing dialog for {message.file_path}")
            password = await self.push_screen_wait(PasswordDialog(message.file_path, message.max_attempts))
            if not message.future.done():
                message.future.set_result(password)
        except Exception as e:
            self.logger.error(f"App.handle_request_password failed: {e}")
            if not message.future.done():
                message.future.set_result(None)

    # 兼容模式：不依赖装饰器的传统命名处理函数
    def on_request_password(self, message: RequestPasswordMessage) -> None:
        """
        兼容旧版本 Textual 的消息处理函数：创建协程处理请求
        """
        async def _do():
            try:
                try:
                    if hasattr(self, "animation_manager") and getattr(self, "animation_manager"):
                        self.animation_manager.hide_default()
                except Exception:
                    pass
                from src.ui.dialogs.password_dialog import PasswordDialog
                self.logger.info(f"App.on_request_password: showing dialog for {message.file_path}")
                password = await self.push_screen_wait(PasswordDialog(message.file_path, message.max_attempts))
                if not message.future.done():
                    message.future.set_result(password)
            except Exception as e:
                self.logger.error(f"App.on_request_password failed: {e}")
                if not message.future.done():
                    message.future.set_result(None)
        try:
            asyncio.create_task(_do())
        except Exception as e:
            # 极端兜底：同步失败时直接回写 None，避免解析侧挂起
            self.logger.error(f"App.on_request_password scheduling failed: {e}")
            if not message.future.done():
                message.future.set_result(None)

    # 兜底总线：拦截所有消息，手动路由 RequestPasswordMessage
    def on_message(self, message: Message) -> None:
        try:
            from src.ui.messages import RequestPasswordMessage as _Req
            if isinstance(message, _Req):
                self.logger.info(f"App.on_message(RequestPasswordMessage): routing for {message.file_path}")
                # 调用兼容处理器，确保在主线程执行
                self.on_request_password(message)
            elif isinstance(message, RefreshContentMessage):
                self.logger.info("App.on_message(RefreshContentMessage): routing refresh content message")
                # 将刷新内容消息转发给当前屏幕
                if hasattr(self, 'screen') and self.screen:
                    self.screen.post_message(message)
        except Exception as e:
            self.logger.error(f"App.on_message routing failed: {e}")

    # 直接供解析线程调用的主线程桥接方法（通过 call_from_thread 调度）
    def request_password_async(self, file_path: str, max_attempts: int, future) -> None:
        """
        在 UI 线程启动一个 Textual worker，worker 内 await push_screen_wait；
        拿到结果后将其写回 future（兼容 asyncio.Future 与 concurrent.futures.Future）。
        """
        self.logger.info(f"App.request_password_async: entered for {file_path}")
        def _set_future_result(val):
            try:
                # asyncio.Future：必须在其绑定的 loop 里设置
                if isinstance(val, BaseException):
                    result_err = val
                    result_val = None
                else:
                    result_err = None
                    result_val = val
                import asyncio as __aio
                if isinstance(future, __aio.Future):
                    try:
                        loop = getattr(future, "_loop", None) or getattr(self, "_main_loop", None)
                        if loop and hasattr(loop, "call_soon_threadsafe"):
                            if result_err:
                                loop.call_soon_threadsafe(lambda: (not future.done()) and future.set_result(None))
                            else:
                                loop.call_soon_threadsafe(lambda: (not future.done()) and future.set_result(result_val))
                        else:
                            # 兜底：直接尝试（可能跨 loop，尽量避免）
                            if not future.done():
                                future.set_result(result_val if not result_err else None)
                    except Exception:
                        if not future.done():
                            future.set_result(None)
                else:
                    # concurrent.futures.Future 线程安全
                    if not future.done():
                        future.set_result(result_val if not result_err else None)
            except Exception:
                try:
                    if hasattr(future, "done") and hasattr(future, "set_result") and not future.done():
                        future.set_result(None)
                except Exception:
                    pass

        async def _worker():
            try:
                try:
                    if hasattr(self, "animation_manager") and getattr(self, "animation_manager"):
                        self.animation_manager.hide_default()
                except Exception:
                    pass
                from src.ui.dialogs.password_dialog import PasswordDialog
                self.logger.info(f"App.request_password_async: showing dialog for {file_path}")
                password = await self.push_screen_wait(PasswordDialog(file_path, max_attempts))
                _set_future_result(password)
            except Exception as e:
                self.logger.error(f"App.request_password_async failed: {e}")
                _set_future_result(e)

        try:
            # 必须在 UI 线程调度 worker
            def _start_worker():
                try:
                    self.run_worker(_worker(), exclusive=True)
                except Exception as ex:
                    self.logger.error(f"App.request_password_async worker start failed: {ex}")
                    _set_future_result(ex)
            # 优先用主事件循环投递
            if hasattr(self, "_main_loop") and self._main_loop:
                self._main_loop.call_soon_threadsafe(_start_worker)
            elif hasattr(self, "call_after_refresh"):
                self.call_after_refresh(_start_worker)  # type: ignore[attr-defined]
            else:
                # 最后兜底直接调用（若当前即在 UI 线程）
                _start_worker()
        except Exception as e:
            self.logger.error(f"App.request_password_async scheduling failed: {e}")
            _set_future_result(e)

    def on_screen_resume(self, screen: Screen[None]) -> None:
        """
        屏幕恢复时的回调
        
        Args:
            screen: 屏幕对象
        """
        # 更新标题
        if hasattr(screen, "TITLE"):
            self._sub_title = screen.TITLE

# 全局应用实例引用
_app_instance = None

def get_app_instance() -> Optional[NewReaderApp]:
    """
    获取全局应用实例
    
    Returns:
        Optional[NewReaderApp]: 应用实例，如果未初始化则为None
    """
    return _app_instance

# 在应用启动时设置全局实例
def on_app_start(app: NewReaderApp) -> None:
    """应用启动时的回调，设置全局实例"""
    global _app_instance
    _app_instance = app

# 在应用退出时清除全局实例
def on_app_exit(app: NewReaderApp) -> None:
    """应用退出时的回调，清除全局实例"""
    global _app_instance
    _app_instance = None

# 设置应用生命周期回调（Textual使用不同的生命周期方法名）
# 这些回调函数会在应用启动和退出时自动调用

# 提供一个通用的主线程调度方法，供解析线程调用
def schedule_on_ui(self: NewReaderApp, fn) -> None:
    """
    将回调安全地调度到 UI 主线程执行：
    - 仅使用 main_loop.call_soon_threadsafe 和 call_after_refresh/call_from_thread
    - 移除 threading.Timer 与直接调用，避免无事件循环环境导致错误
    - 使用一次性包装防止重复执行
    """
    executed = {"done": False}
    def do_once(tag: str):
        if executed["done"]:
            return
        executed["done"] = True
        try:
            logger.info(f"schedule_on_ui executing via {tag}")
            fn()
        except Exception as ex:
            logger.error(f"schedule_on_ui do_once({tag}) failed: {ex}")

    posted = False
    # 优先：asyncio 主循环
    try:
        if hasattr(self, "_main_loop") and self._main_loop:
            logger.info("schedule_on_ui posting via main_loop.call_soon_threadsafe")
            self._main_loop.call_soon_threadsafe(lambda: do_once("main_loop"))
            posted = True
    except Exception as e:
        logger.error(f"schedule_on_ui via main_loop failed: {e}")

    # 次优：Textual 的 call_from_thread（要求当前不在 UI 线程）
    if not posted:
        try:
            if hasattr(self, "call_from_thread"):
                logger.info("schedule_on_ui posting via call_from_thread")
                self.call_from_thread(lambda: do_once("call_from_thread"))
                posted = True
        except Exception as e2:
            logger.error(f"schedule_on_ui via call_from_thread failed: {e2}")

    # 兜底：下一帧执行
    if not posted:
        try:
            if hasattr(self, "call_after_refresh"):
                logger.info("schedule_on_ui posting via call_after_refresh")
                self.call_after_refresh(lambda: do_once("call_after_refresh"))  # type: ignore[attr-defined]
                posted = True
        except Exception as e4:
            logger.error(f"schedule_on_ui via call_after_refresh failed: {e4}")

    # 若仍未投递成功，则记录但不直接跨线程执行，避免无 loop 环境
    if not posted:
        logger.error("schedule_on_ui could not post to UI loop; callback dropped to avoid unsafe direct call")

# 将方法绑定到类（避免大范围修改）
setattr(NewReaderApp, "schedule_on_ui", schedule_on_ui)