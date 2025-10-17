"""
应用程序主界面
"""


from typing import Dict, Any, Optional, List

import os
from typing import Optional
from textual.app import App, ComposeResult
# 早期猴子补丁 Textual 框架默认 CSS 中的 hatch 行，避免 $panel 类型冲突
try:
    import textual.app as _txt_app_mod
    _def_css = getattr(_txt_app_mod.App, "DEFAULT_CSS", "")
    if isinstance(_def_css, str) and "hatch: right $panel;" in _def_css:
        _txt_app_mod.App.DEFAULT_CSS = _def_css.replace("hatch: right $panel;", "hatch: right #2f2f2f 40%;")
except Exception:
    pass
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, OptionList
from textual import on, events
# 兼容导入 Textual 的命令类与 Provider
_TxtCommand = None
_textual_command_decorator = None
try:
    from textual.command import Command as _TxtCommand
except Exception:
    _TxtCommand = None
try:
    from textual.command import Provider as _TxtProvider
    from textual.command import DiscoveryHit as _DiscoveryHit
except Exception:
    _TxtProvider = None
    _DiscoveryHit = None
# 命令装饰器（命令面板自动发现）
try:
    from textual.command import command as _textual_command_decorator
except Exception:
    _textual_command_decorator = None
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
from src.ui.screens.file_explorer_screen import FileExplorerScreen
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
from src.ui.styles.quick_fix_isolation import reset_quick_isolation

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ThemeSelectScreen(ModalScreen[str]):
    """App 内主题选择器：列出 ThemeManager 中的所有主题名"""
    def __init__(self, options: list[str]) -> None:
        super().__init__()
        self._options = options
        # 预览状态
        self._original_theme: Optional[str] = None
        self._last_previewed: Optional[str] = None
        self._confirmed: bool = False

    def compose(self) -> ComposeResult:
        # 仅传入字符串选项，避免旧版 OptionList 对 (label, id) 的不兼容
        return (yield OptionList(*self._options, id="theme-option-list"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:  # type: ignore[attr-defined]
        # 选择后关闭弹窗并返回主题名（从 prompt 读取字符串）
        # 标记已确认，退出时不回滚
        self._confirmed = True
        try:
            self.dismiss(str(getattr(event, "option", getattr(event, "prompt", None)).prompt))
        except Exception:
            try:
                # 一些版本事件结构不同，直接取 option.prompt 或 prompt
                if hasattr(event, "option") and hasattr(event.option, "prompt"):
                    self.dismiss(str(event.option.prompt))
                elif hasattr(event, "prompt"):
                    self.dismiss(str(event.prompt))
                else:
                    self.dismiss(None)
            except Exception:
                self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        """按键事件处理"""
        if event.key == "escape":
            # 未确认直接退出时，回滚主题
            try:
                if not self._confirmed and self._original_theme:
                    app = getattr(self, "app", None)
                    if app and hasattr(app, "_apply_theme_runtime"):
                        app._apply_theme_runtime(self._original_theme, notify=False, preview=True)
            except Exception:
                pass
            self.dismiss(None)
            event.stop()

    def on_mount(self) -> None:
        """挂载时记录进入前的主题，供取消时回滚"""
        try:
            app = getattr(self, "app", None)
            if app and hasattr(app, "theme_manager"):
                self._original_theme = app.theme_manager.get_current_theme_name()
        except Exception:
            self._original_theme = None

        # 将主题列表高度限制为 3 行，避免预览时遮挡内容
        try:
            ol = self.query_one("#theme-option-list")
            if hasattr(ol, "styles"):
                try:
                    ol.styles.height = 3
                except Exception:
                    pass
                try:
                    setattr(ol.styles, "max_height", 3)
                except Exception:
                    pass
        except Exception:
            pass

    def on_unmount(self) -> None:
        """关闭弹窗时，如未确认则回滚到进入前的主题"""
        try:
            if not self._confirmed and self._original_theme:
                app = getattr(self, "app", None)
                if app and hasattr(app, "_apply_theme_runtime"):
                    app._apply_theme_runtime(self._original_theme, notify=False, preview=True)
        except Exception:
            pass

    def on_option_list_option_highlighted(self, event) -> None:  # type: ignore[override]
        """移动高亮即预览主题（临时应用，不持久化）"""
        try:
            # 尽量兼容不同版本事件结构
            name = None
            if hasattr(event, "option") and hasattr(event.option, "prompt"):
                name = str(event.option.prompt)
            elif hasattr(event, "prompt"):
                name = str(event.prompt)
            elif hasattr(event, "option") and hasattr(event.option, "value"):
                name = str(event.option.value)
            if not name:
                return
            if name == self._last_previewed:
                return
            app = getattr(self, "app", None)
            if app and hasattr(app, "_apply_theme_runtime"):
                app._apply_theme_runtime(name, notify=False, preview=True)
                self._last_previewed = name
        except Exception:
            pass

# 命令提供者：将 ThemeManager 的主题注册到 Ctrl-P
if _TxtProvider is not None and _DiscoveryHit is not None:
    class NewReaderThemeProvider(_TxtProvider):
        """将系统内置主题作为命令提供给 Ctrl-P（CommandPalette）"""

        def __init__(self, screen, match_style):
            # Provider 的构造在 CommandPalette 中通过 provider_class(screen, match_style) 调用
            super().__init__(screen, match_style)
            self._app = screen.app  # 当前应用
            self._themes = []
            try:
                # 从 ThemeManager 获取全部主题名
                self._themes = self._app.theme_manager.get_available_themes()
            except Exception:
                self._themes = []

        def _post_init(self) -> None:
            """Provider 生命周期钩子：初始化后被调用"""
            # 不需要额外初始化
            return

        async def search(self, search_value: str):
            """实现抽象方法：委托到内部的 _search"""
            return self._search(search_value)

        async def _shutdown(self) -> None:
            """Provider 生命周期钩子：关闭时调用"""
            return

        async def _search(self, search_value: str):
            """按搜索值提供命令命中项（DiscoveryHit）"""
            query = (search_value or "").strip().lower()

            # 总入口：打开我们的主题选择器
            try:
                display = "Switch Theme (NewReader)"
                help_text = "Open NewReader theme picker"
                def _open_picker():
                    try:
                        self._app.action_pick_theme()
                    except Exception:
                        pass
                hit = _DiscoveryHit(display=display, command=_open_picker, text=display, help=help_text)
                # 仅当查询为空或匹配时提供
                if not query or "switch" in query or "theme" in query or "newreader" in query:
                    yield hit
            except Exception:
                pass

            # 不再为每个主题生成独立命令，保持命令面板简洁并保留框架自带命令
            return

class NewReaderApp(App[None]):
    """NewReader应用程序主类"""
    
    TITLE = None
    SUB_TITLE = None
    
    # 预置 $panel 为百分比，满足 hatch 语义（方向 + 百分比）
    CSS = "$panel: 40%;"
    CSS_PATH = ["styles/common.tcss"]
    # 仅前置 $panel 定义，保持父类 DEFAULT_CSS 原样
    DEFAULT_CSS = (getattr(App, "DEFAULT_CSS", "") or "").replace("hatch: right $panel;", "hatch: right #2f2f2f 40%;")

    # 向命令面板注册我们的 Provider（CommandPalette 会自动收集）
    # 注意：CommandPalette 在打开时会读取 App.COMMANDS 与 Screen.COMMANDS
    try:
        import textual.app as _textual_app_mod
        _default_commands = getattr(_textual_app_mod.App, "COMMANDS", [])
    except Exception:
        _default_commands = []
    if 'NewReaderThemeProvider' in globals() and _TxtProvider is not None:
        COMMANDS = list(_default_commands) + [NewReaderThemeProvider]
    else:
        COMMANDS = list(_default_commands)
    
    BINDINGS = [
        Binding("q", "quit", get_global_i18n().t('app.bindings.quit')),
        Binding("h", "show_help", get_global_i18n().t('app.bindings.help')),
        Binding("k", "show_bookshelf", get_global_i18n().t('app.bindings.bookshelf')),
        Binding("s", "show_settings", get_global_i18n().t('app.bindings.settings')),
        Binding("c", "show_statistics", get_global_i18n().t('app.bindings.statistics')),
        Binding("/", "boss_key", get_global_i18n().t('app.bindings.boss_key')),
        Binding("t", "pick_theme", get_global_i18n().t('app.bindings.theme')),
        Binding("escape", "back", get_global_i18n().t('app.bindings.back'))
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
        # 优先使用设置中心的 advanced.language，其次回退到 app.language，最后默认 zh_CN
        default_locale = config.get("advanced", {}).get("language", config.get("app", {}).get("language", "zh_CN"))
        
        # 初始化全局i18n实例
        init_global_i18n(locale_dir, default_locale)
        self.i18n = get_global_i18n()
        
        # 设置模块日志
        self.logger = logger
        self.logger.debug(get_global_i18n().t("app.init_start"))
        
        # 初始化主题管理器
        theme_name = config.get("app", {}).get("theme", "dark")
        self.theme_manager = ThemeManager(theme_name)
        # 提前向 Textual 注册所有主题，确保 Ctrl-P 主题选择器可见
        # try:
        #     self.theme_manager.register_with_textual()
        # except Exception as e:
        #     logger.debug(f"在应用启动阶段注册主题到 Textual 失败（可忽略）：{e}")

        # Ctrl-P 兼容：猴子补丁 Textual 的“Switch Theme”命令，使其列出 ThemeManager 的全部主题
        # try:
        #     def _install_ctrl_p_theme_patch(app_self):
        #         try:
        #             import importlib
        #             # 尝试 textual.commands（新版本）
        #             patched = False
        #             for mod_name in ("textual.commands", "textual.command"):
        #                 try:
        #                     mod = importlib.import_module(mod_name)
        #                 except Exception:
        #                     continue
        #                 # 找到可能的主题列表或生成函数并替换
        #                 # 常见形式：FUNCTION/变量包含 'theme' 且用于命令面板
        #                 for attr_name in dir(mod):
        #                     low = attr_name.lower()
        #                     if "theme" in low and ("list" in low or "names" in low or "available" in low):
        #                         try:
        #                             setattr(mod, attr_name, lambda: app_self.theme_manager.get_available_themes())
        #                             patched = True
        #                         except Exception:
        #                             pass
        #                 # 兜底：若存在切换主题的命令函数，包装它以使用我们的选择器
        #                 for attr_name in dir(mod):
        #                     if "switch" in attr_name.lower() and "theme" in attr_name.lower():
        #                         fn = getattr(mod, attr_name, None)
        #                         if callable(fn):
        #                             def _wrap_switch(*args, **kwargs):
        #                                 try:
        #                                     # 打开我们自己的主题选择器
        #                                     app_self.action_pick_theme()
        #                                 except Exception:
        #                                     # 失败时调用原方法
        #                                     return fn(*args, **kwargs)
        #                             try:
        #                                 setattr(mod, attr_name, _wrap_switch)
        #                                 patched = True
        #                             except Exception:
        #                                 pass
        #             return patched
        #         except Exception:
        #             return False

        #     _patched = _install_ctrl_p_theme_patch(self)
        #     if _patched:
        #         logger.info("已为 Ctrl-P 注入主题列表补丁（使用 ThemeManager 列表）")
        #     else:
        #         logger.info("未找到可补丁的 Ctrl-P 内置主题命令，将注册自定义命令作为兜底")
        # except Exception as e:
        #     logger.debug(f"Ctrl-P 主题命令补丁失败（可忽略）：{e}")

        # 显式向命令面板注册我们的命令（兼容多个 Textual 版本的注册入口）
        # try:
        #     def _register_theme_commands_to_palette(app_self):
        #         import importlib
        #         registered = False

        #         # 生成命令项：返回 [(label, callable)]
        #         def _build_entries():
        #             # 仅提供一个入口命令，不批量生成每主题项
        #             def _open_picker():
        #                 try:
        #                     app_self.action_switch_theme_newreader()
        #                 except Exception:
        #                     app_self.action_pick_theme()
        #             return [("Switch Theme (NewReader)", _open_picker)]

        #         entries = _build_entries()

        #         # 优先使用 textual.command / textual.commands 的注册 API
        #         for mod_name in ("textual.command", "textual.commands"):
        #             try:
        #                 mod = importlib.import_module(mod_name)
        #             except Exception:
        #                 continue

        #             # 1) register_command 函数
        #             fn = getattr(mod, "register_command", None)
        #             if callable(fn):
        #                 for label, cb in entries:
        #                     try:
        #                         fn(cb, name=label)
        #                         registered = True
        #                     except Exception:
        #                         pass

        #             # 2) Command 类 + 注册容器
        #             Cmd = getattr(mod, "Command", None)
        #             if Cmd:
        #                 # 常见注册容器：REGISTRY / registry（list/dict/obj）
        #                 for reg_name in ("REGISTRY", "registry"):
        #                     reg = getattr(mod, reg_name, None)
        #                     if reg is None:
        #                         continue
        #                     # 列表：追加
        #                     if isinstance(reg, list):
        #                         for label, cb in entries:
        #                             try:
        #                                 reg.append(Cmd(label, cb))
        #                                 registered = True
        #                             except Exception:
        #                                 pass
        #                     # 字典：写入
        #                     elif isinstance(reg, dict):
        #                         for label, cb in entries:
        #                             try:
        #                                 reg[label] = Cmd(label, cb)
        #                                 registered = True
        #                             except Exception:
        #                                 pass
        #                     else:
        #                         # 具备 add/register 方法的对象
        #                         for mname in ("add", "register", "add_command", "register_command"):
        #                         # noqa
        #                             method = getattr(reg, mname, None)
        #                             if callable(method):
        #                                 for label, cb in entries:
        #                                     try:
        #                                         method(Cmd(label, cb))
        #                                         registered = True
        #                                     except Exception:
        #                                         pass

        #             # 3) CommandRegistry 类：尝试获取单例或新建
        #             Registry = getattr(mod, "CommandRegistry", None)
        #             if Registry:
        #                 try:
        #                     registry = None
        #                     # 可能存在全局实例
        #                     for cand in ("REGISTRY", "registry"):
        #                         obj = getattr(mod, cand, None)
        #                         if isinstance(obj, Registry):
        #                             registry = obj
        #                             break
        #                     if registry is None:
        #                         try:
        #                             registry = Registry()
        #                         except Exception:
        #                             registry = None
        #                     if registry:
        #                         for label, cb in entries:
        #                             for mname in ("add", "register", "add_command", "register_command"):
        #                                 method = getattr(registry, mname, None)
        #                                 if callable(method):
        #                                     try:
        #                                         if getattr(mod, "Command", None):
        #                                             method(mod.Command(label, cb))
        #                                         else:
        #                                             method(label, cb)
        #                                         registered = True
        #                                     except Exception:
        #                                         pass
        #                 except Exception:
        #                     pass

        #         # 4) App 实例自身可能有命令注册器
        #         try:
        #             app_reg = getattr(app_self, "command_registry", None)
        #             if app_reg:
        #                 for label, cb in entries:
        #                     for mname in ("add", "register", "add_command", "register_command"):
        #                         method = getattr(app_reg, mname, None)
        #                         if callable(method):
        #                             try:
        #                                 method(label, cb)
        #                                 registered = True
        #                             except Exception:
        #                                 pass
        #         except Exception:
        #             pass

        #         return registered

        #     if _register_theme_commands_to_palette(self):
        #         logger.info("已向命令面板注册 NewReader 主题命令（显式注册）")
        #     else:
        #         logger.info("未能通过注册器显式注册命令，Ctrl-P 可能依赖 get_commands；已实现 get_commands 作为兜底")
        # except Exception as e:
        #     logger.debug(f"命令面板显式注册失败（可忽略）：{e}")
        
        # 初始化书架
        self.bookshelf = Bookshelf(config.get("app", {}).get("library_path", "library"))
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        # 伪用户系统：当前用户会话
        self.current_user: Optional[Dict[str, Any]] = None
        
        # 初始化主事件循环变量
        self._main_loop = None
        # 模态弹窗期间抑制加载动画
        self._modal_active: bool = False
        # 密码请求队列：避免重复弹窗（多个解析请求同时等待同一个密码输入）
        self._password_waiters: list = []
        
        # 初始化统计管理器
        self.statistics_manager = StatisticsManagerDirect(self.db_manager)
        
        # 初始化快速样式隔离系统
        try:
            reset_quick_isolation()
            logger.info("快速样式隔离系统已初始化")
        except Exception as e:
            logger.error(f"快速样式隔离系统初始化失败: {e}")
        
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
        from src.ui.screens.proxy_list_screen import ProxyListScreen
        from src.ui.screens.novel_sites_management_screen import NovelSitesManagementScreen
        from src.ui.screens.crawler_management_screen import CrawlerManagementScreen
        
        self.install_screen(GetBooksScreen(self.theme_manager), name="get_books")
        self.install_screen(ProxyListScreen(self.theme_manager), name="proxy_list")
        self.install_screen(NovelSitesManagementScreen(self.theme_manager), name="novel_sites_management")
        # 爬取管理屏幕需要动态创建，所以只注册类（Textual 支持注册类/工厂，运行时按 push_screen 传参实例化）
        self.install_screen(CrawlerManagementScreen, name="crawler_management")  # type: ignore[arg-type]
        
        # 安装文件资源管理器屏幕
        self.install_screen(FileExplorerScreen(self.theme_manager, self.bookshelf, self.statistics_manager), name="file_explorer")

        # 安装用户管理屏幕
        from src.ui.screens.users_management_screen import UsersManagementScreen
        self.install_screen(UsersManagementScreen(self.theme_manager, self.db_manager), name="users_management")
        
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

        # 启动对齐：若 appearance.theme 与 app.theme 不一致，统一为 appearance.theme 并持久化
        try:
            desired = None
            if hasattr(self, "settings_registry") and self.settings_registry:
                desired = self.settings_registry.get_value("appearance.theme", None)
            if desired and isinstance(desired, str):
                # 当前 ThemeManager 的主题名
                current = getattr(self.theme_manager, "current_theme_name", None)
                if not current:
                    # 从配置获取 app.theme
                    try:
                        cfg = self.config_manager.get_config()
                        current = cfg.get("app", {}).get("theme")
                    except Exception:
                        current = None
                if desired != current:
                    # 设置并持久化 app.theme
                    if self.theme_manager.set_theme(desired):
                        try:
                            cfg = self.config_manager.get_config()
                            app_cfg = cfg.get("app", {})
                            app_cfg["theme"] = desired
                            cfg["app"] = app_cfg
                            if hasattr(self.config_manager, "save_config"):
                                self.config_manager.save_config(cfg)  # type: ignore[attr-defined]
                        except Exception:
                            pass
        except Exception as e:
            logger.debug(f"启动主题名称对齐失败（可忽略）：{e}")

        # 应用当前主题
        self.theme_manager.apply_theme_to_screen(self)

        # 通过全局观察者联动：appearance.theme 改变时，同步 UI 主题为同名并刷新
        try:
            from src.config.settings.setting_observer import global_observer_manager, SettingObserver
            
            # 创建适当的观察者类来包装方法
            class AppThemeObserver(SettingObserver):
                def __init__(self, app_instance):
                    self.app = app_instance
                
                def on_setting_changed(self, event):
                    """设置变更时的回调"""
                    from src.config.settings.setting_observer import SettingChangeEvent
                    if isinstance(event, SettingChangeEvent):
                        self.app._on_content_theme_changed(event.new_value)
            
            # 注册观察者
            if hasattr(self, "_on_content_theme_changed"):
                observer = AppThemeObserver(self)
                global_observer_manager.register_observer(observer, "appearance.theme")

            # 注册语言联动观察者：advanced.language 改变后，同步全局 i18n 并刷新界面
            class AppLanguageObserver(SettingObserver):
                def __init__(self, app_instance):
                    self.app = app_instance
                def on_setting_changed(self, event):
                    from src.config.settings.setting_observer import SettingChangeEvent
                    try:
                        if isinstance(event, SettingChangeEvent):
                            new_locale = getattr(event, "new_value", None)
                            if isinstance(new_locale, str) and new_locale:
                                # 同步全局语言
                                try:
                                    get_global_i18n().set_locale(new_locale)
                                except Exception:
                                    pass
                                # 刷新标题（基于新语言）
                                try:
                                    self.app._title = get_global_i18n().t("app.name")
                                    self.app._sub_title = get_global_i18n().t("app.description")
                                except Exception:
                                    pass
                                # 触发界面刷新（尽量 recompose）
                                try:
                                    try:
                                        self.app.refresh(layout=True)
                                    except Exception:
                                        self.app.refresh()
                                    if hasattr(self.app, "screen") and self.app.screen and hasattr(self.app.screen, "refresh"):
                                        self.app.screen.refresh(recompose=True)
                                    # 刷新其它已安装屏幕
                                    screens = []
                                    if hasattr(self.app, "installed_screens"):
                                        screens = list(getattr(self.app, "installed_screens").values())  # type: ignore[attr-defined]
                                    elif hasattr(self.app, "screens"):
                                        screens = list(getattr(self.app, "screens").values())  # type: ignore[attr-defined]
                                    for sc in screens:
                                        if sc is not self.app.screen and hasattr(sc, "refresh"):
                                            sc.refresh(recompose=True)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            try:
                global_observer_manager.register_observer(AppLanguageObserver(self), "advanced.language")
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"注册主题联动观察者失败（可忽略）：{e}")
        
        # 初始化默认加载动画组件
        self._initialize_loading_animation()

        # 启动内存监控器：根据配置的缓存大小选择阈值
        try:
            from src.utils.memory_monitor import MemoryMonitor
            from src.utils.cache_manager import parse_cache, paginate_cache
            cfg = self.config_manager.get_config()
            adv = cfg.get("advanced", {})
            cache_mb = int(adv.get("cache_size", 100))
            # 高水位线：缓存大小的 1.5 倍；收缩目标为缓存大小
            high_water = max(64, int(cache_mb * 1.5)) * 1024 * 1024
            target = max(32, int(cache_mb)) * 1024 * 1024

            def on_pressure():
                # 收缩缓存，并尝试释放渲染结果
                try:
                    paginate_cache.shrink_to_target(target // 2)
                    parse_cache.shrink_to_target(target // 2)
                except Exception:
                    pass
                try:
                    # 释放当前屏幕的渲染结果（若支持）
                    if hasattr(self, "screen") and self.screen:
                        rdr = getattr(self.screen, "content_renderer", None)
                        if rdr and hasattr(rdr, "rendered_pages"):
                            rdr.rendered_pages = []
                except Exception:
                    pass

            self._memory_monitor = MemoryMonitor(high_water, target, on_pressure)
            self._memory_monitor.start(interval_sec=2.0)
        except Exception as e:
            logger.debug(f"内存监控启动失败（可忽略）：{e}")
        
        # 伪用户系统：显示登录屏幕（优先于启动密码）
        try:
            from src.ui.screens.login_screen import LoginScreen
            from src.ui.screens.lock_screen import LockScreen
            from src.utils.multi_user_manager import multi_user_manager
            
            async def _wait_login_then_enter():
                # 检查多用户设置，如果禁用则检查启动密码
                if not multi_user_manager.should_show_login():
                    # 多用户功能禁用，检查启动密码模式
                    config = self.config_manager.get_config()
                    advanced_config = config.get("advanced", {})
                    password_enabled = advanced_config.get("password_enabled", False)
                    startup_password = advanced_config.get("password", "")
                    
                    # 如果启动密码模式开启，需要验证密码
                    if password_enabled and startup_password:
                        password_correct = await self.push_screen_wait(LockScreen(startup_password))
                        if not password_correct:
                            # 密码错误或取消，退出应用
                            self.exit()
                            return
                    
                    # 多用户功能禁用，直接返回超级管理员信息
                    super_admin_info = {
                        "id": 0,
                        "username": "super_admin",
                        "role": "super_admin",
                        "permissions": ["read", "write", "delete", "manage_users", "manage_books", "manage_settings"]
                    }
                    self.current_user = super_admin_info
                    try:
                        # 同步到书架过滤
                        self.bookshelf.set_current_user(super_admin_info.get("id"), super_admin_info.get("role", "super_admin"))
                    except Exception:
                        pass
                    # 直接进入欢迎页
                    self.push_screen("welcome")
                    return
                
                # 多用户启用，显示登录界面（此时启动密码模式自动关闭）
                user = await self.push_screen_wait(LoginScreen(self.theme_manager, self.db_manager))
                # user 为 None 则匿名，仍可进入但无权限
                if isinstance(user, dict):
                    self.current_user = user
                    try:
                        # 同步到书架过滤
                        self.bookshelf.set_current_user(user.get("id"), user.get("role", "user"))
                    except Exception:
                        pass
                # 登录后进入欢迎页
                self.push_screen("welcome")
            self.run_worker(_wait_login_then_enter(), exclusive=True)
            return
        except Exception as e:
            logger.debug(f"登录屏幕加载失败（可忽略）：{e}")
            # 若登录屏幕异常，回退到欢迎页
            self.push_screen("welcome")
            return

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
        """显示书架屏幕（按权限）"""
        if self.has_permission("bookshelf.read"):
            self.push_screen(BookshelfScreen(self.theme_manager, self.bookshelf, self.statistics_manager))
        else:
            try:
                self.notify(get_global_i18n().t("app.open_bookshelf"), severity="warning")
            except Exception:
                logger.info("无权限访问书架")
    
    def action_show_settings(self) -> None:
        """显示设置屏幕（按权限）"""
        if self.has_permission("settings.open"):
            self.push_screen("settings")
        else:
            try:
                self.notify(get_global_i18n().t("app.open_settings"), severity="warning")
            except Exception:
                logger.info("无权限打开设置")
    
    def action_show_statistics(self) -> None:
        """显示统计屏幕（按权限）"""
        if self.has_permission("statistics.open"):
            self.push_screen(StatisticsScreen(self.theme_manager, self.statistics_manager))
        else:
            try:
                self.notify(get_global_i18n().t("app.open_statistics"), severity="warning")
            except Exception:
                logger.info("无权限打开统计")

    def action_switch_theme_newreader(self) -> None:
        """Switch Theme (NewReader)：通过内置主题选择器切换主题（Ctrl-P 可见兜底命令）"""
        try:
            self.action_pick_theme()
        except Exception as e:
            logger.error(f"NewReader 切换主题命令失败: {e}")

    # 装饰器命令：让 Ctrl-P 自动识别“Switch Theme (NewReader)”
    if _textual_command_decorator is not None:
        @_textual_command_decorator("Switch Theme (NewReader)")
        def switch_theme_newreader_cmd(self) -> None:
            try:
                self.action_pick_theme()
            except Exception as e:
                logger.error(f"Switch Theme (NewReader) 命令执行失败: {e}")

    # 向 Ctrl-P 提供命令列表（Textual 会调用此方法收集命令）
    def get_commands(self):
        cmds = []
        try:
            if _TxtCommand is not None:
                # 仅新增一个入口命令，不生成每主题快捷项
                cmds.append(_TxtCommand("Switch Theme (NewReader)", lambda: self.action_switch_theme_newreader()))
        except Exception as e:
            logger.debug(f"构建命令列表失败（可忽略）：{e}")
        return cmds

    def action_pick_theme(self) -> None:
        """在 worker 中打开主题选择器，选择后应用主题并同步设置（兼容旧版 Textual）"""
        try:
            themes = self.theme_manager.get_available_themes()
            if not themes:
                try:
                    self.notify(get_global_i18n().t("app.no_theme"), severity="warning")
                except Exception:
                    logger.info("没有可用主题")
                return

            async def _worker():
                try:
                    chosen = await self.push_screen_wait(ThemeSelectScreen(themes))
                    if not chosen:
                        return

                    def _apply():
                        # 使用通用运行时应用方法
                        self._apply_theme_runtime(chosen, notify=True)

                    # 在 UI 线程应用更改（使用通用调度，避免 call_from_thread 限制）
                    try:
                        if hasattr(self, "schedule_on_ui"):
                            self.schedule_on_ui(_apply)  # type: ignore[attr-defined]
                        elif hasattr(self, "call_after_refresh"):
                            self.call_after_refresh(_apply)  # type: ignore[attr-defined]
                        else:
                            _apply()
                    except Exception:
                        _apply()
                except Exception as e:
                    logger.error(f"主题选择失败: {e}")

            # 在 worker 中运行等待弹窗
            self.run_worker(_worker(), exclusive=True)
        except Exception as e:
            logger.error(f"主题选择失败: {e}")

    async def action_select_theme(self) -> None:
        """打开主题选择器，选择后应用主题并同步设置"""
        try:
            themes = self.theme_manager.get_available_themes()
            if not themes:
                try:
                    self.notify(get_global_i18n().t("app.no_theme"), severity="warning")
                except Exception:
                    logger.info("没有可用主题")
                return
            chosen = await self.push_screen_wait(ThemeSelectScreen(themes))
            if not chosen:
                return
            if self.theme_manager.set_theme(chosen):
                # 应用到 App（Textual + TSS 变量 + 现有样式注入）
                self.theme_manager.apply_theme_to_screen(self)
                # 临时主题切换：不同步设置中心、不持久化
                try:
                    pass
                except Exception:
                    pass
                # 深度强制刷新，确保所有部件立即应用新主题
                try:
                    if hasattr(self, "_force_theme_refresh"):
                        self._force_theme_refresh()
                except Exception:
                    pass
                # 提示
                try:
                    self.notify(f"{get_global_i18n().t("app.changed_theme")}：{chosen}", severity="information")
                except Exception:
                    logger.info(f"已切换主题：{chosen}")
        except Exception as e:
            logger.error(f"主题选择失败: {e}")
    
    def action_switch_theme(self) -> None:
        """覆盖内置 Switch Theme：调用自定义主题选择器"""
        try:
            self.action_pick_theme()
        except Exception as e:
            logger.error(f"切换主题失败: {e}")

    def switch_theme(self) -> None:
        """供 Ctrl-P 内置命令直接调用的同名方法，转到自定义主题选择器"""
        try:
            self.action_pick_theme()
        except Exception as e:
            logger.error(f"切换主题失败: {e}")

    def _apply_theme_runtime(self, name: str, notify: bool = False, preview: bool = False) -> None:
        """
        运行时应用主题到 App 与所有屏幕（不做持久化），可选提示。
        preview=True 时走“轻量应用”，避免在部件挂载期触发 recompose。
        """
        try:
            if not name:
                return
            if not self.theme_manager.set_theme(name):
                return
            # 1) 应用到 App（Textual + TSS 变量 + 现有样式注入）
            self.theme_manager.apply_theme_to_screen(self)

            if preview:
                # 预览：尽量不重载 CSS、不强制 recompose，仅请求一次轻量刷新
                try:
                    self.refresh()
                except Exception:
                    pass
            else:
                # 最终应用：完整刷新流程
                # 2) 强制重载 CSS（如果框架支持）
                try:
                    if hasattr(self, "reload_css") and callable(getattr(self, "reload_css")):
                        self.reload_css()  # type: ignore[attr-defined]
                except Exception:
                    pass
                # 3) 对所有已安装/注册的屏幕应用主题
                try:
                    screens = []
                    if hasattr(self, "installed_screens"):
                        screens = list(getattr(self, "installed_screens").values())  # type: ignore[attr-defined]
                    elif hasattr(self, "screens"):
                        screens = list(getattr(self, "screens").values())  # type: ignore[attr-defined]
                    for sc in screens:
                        try:
                            self.theme_manager.apply_theme_to_screen(sc)
                        except Exception:
                            pass
                except Exception:
                    pass
                # 4) 统一刷新：App 布局 + 当前屏幕重组 + 其它屏幕重组
                try:
                    try:
                        self.refresh(layout=True)
                    except Exception:
                        self.refresh()
                    # 当前屏幕
                    try:
                        if self.screen and hasattr(self.screen, "refresh"):
                            self.screen.refresh(recompose=True)
                    except Exception:
                        pass
                    # 其他屏幕
                    try:
                        screens = []
                        if hasattr(self, "installed_screens"):
                            screens = list(getattr(self, "installed_screens").values())  # type: ignore[attr-defined]
                        elif hasattr(self, "screens"):
                            screens = list(getattr(self, "screens").values())  # type: ignore[attr-defined]
                        for sc in screens:
                            if sc is not self.screen and hasattr(sc, "refresh"):
                                sc.refresh(recompose=True)
                    except Exception:
                        pass
                except Exception as ex:
                    logger.debug(f"主题应用后刷新失败（可忽略）：{ex}")
                # 5) 深度强制刷新，确保所有部件立即应用新主题
                try:
                    if hasattr(self, "_force_theme_refresh"):
                        self._force_theme_refresh()
                except Exception:
                    pass
                # 6) 可选提示
                if notify:
                    try:
                        self.notify(f"{get_global_i18n().t("app.changed_theme")}：{name}", severity="information")
                    except Exception:
                        logger.info(f"已切换主题：{name}")
        except Exception as _e:
            logger.debug(f"_apply_theme_runtime 失败（可忽略）：{_e}")
    
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
    
    async def action_back(self) -> None:
        """
        统一 ESC 行为：
        - 欢迎页：退出应用
        - 其他页面/对话框：返回上一层
        """
        try:
            # 若当前是欢迎页，退出
            from src.ui.screens.welcome_screen import WelcomeScreen as _WS
            if isinstance(self.screen, _WS):
                await self.action_quit() if hasattr(self, "action_quit") else self.exit()
                return
            # 非欢迎页：返回上一层
            # 优先关闭模态或子屏幕
            if hasattr(self, "pop_screen"):
                self.pop_screen()
        except Exception:
            # 兜底：如果没有可返回的页面，不执行退出
            pass

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
            
            # 在打开前尝试补全作者（静默忽略失败）
            try:
                if hasattr(self, "bookshelf") and self.bookshelf:
                    self.bookshelf.maybe_update_author(book)
            except Exception:
                pass
            # 加载书籍内容
            content = book.get_content()
            
            if not content:
                self.notify(f"{get_global_i18n().t("app.load_content_failed")}: {book_file}", severity="error")
                self.push_screen("bookshelf")
                return
            
            # 打开终端阅读器屏幕（使用新的现代化架构）
            self.push_screen(ReaderScreen(book, self.theme_manager, self.statistics_manager, self.bookmark_manager, self.bookshelf))
            
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
            print(f"\n{get_global_i18n().t('app.pdf_need_password')}: {os.path.basename(file_path)}")
            print(get_global_i18n().t('app.password_info'))
            password = getpass.getpass(get_global_i18n().t('app.prompt'))
            
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
            # 在打开前尝试补全作者（静默忽略失败）
            try:
                if hasattr(self, "bookshelf") and self.bookshelf:
                    self.bookshelf.maybe_update_author(book)
            except Exception:
                pass
            # 使用新的终端阅读器屏幕
            self.push_screen(ReaderScreen(book, self.theme_manager, self.statistics_manager, self.bookmark_manager, self.bookshelf))
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
            # 若已有弹窗激活，则仅登记等待者，避免重复弹窗
            if getattr(self, "_modal_active", False):
                try:
                    self._password_waiters.append(message.future)
                except Exception:
                    pass
                return
            # 打开弹窗，标记模态激活以抑制加载动画
            self._modal_active = True
            # 将当前请求加入等待队列
            try:
                self._password_waiters.append(message.future)
            except Exception:
                pass
            def _on_result(result):
                # 弹窗结束，取消模态标记，并回填所有等待者
                self._modal_active = False
                try:
                    waiters = list(getattr(self, "_password_waiters", []))
                    self._password_waiters = []
                except Exception:
                    waiters = [message.future]
                for fut in waiters:
                    try:
                        import asyncio as __aio
                        if isinstance(fut, __aio.Future):
                            loop = getattr(fut, "_loop", None) or getattr(self, "_main_loop", None)
                            if loop and hasattr(loop, "call_soon_threadsafe"):
                                loop.call_soon_threadsafe(lambda f=fut, r=result: (not f.done()) and f.set_result(r))
                            else:
                                if not fut.done():
                                    fut.set_result(result)
                        else:
                            if hasattr(fut, "done") and hasattr(fut, "set_result") and not fut.done():
                                fut.set_result(result)
                    except Exception:
                        pass
            self.push_screen(PasswordDialog(message.file_path, message.max_attempts), _on_result)
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
                # 若已有弹窗激活，则仅登记等待者，避免重复弹窗
                if getattr(self, "_modal_active", False):
                    try:
                        self._password_waiters.append(message.future)
                    except Exception:
                        pass
                    return
                # 打开弹窗，标记模态激活以抑制加载动画
                self._modal_active = True
                # 将当前请求加入等待队列
                try:
                    self._password_waiters.append(message.future)
                except Exception:
                    pass
                def _on_result(result):
                    # 弹窗结束，取消模态标记，并回填所有等待者
                    self._modal_active = False
                    try:
                        waiters = list(getattr(self, "_password_waiters", []))
                        self._password_waiters = []
                    except Exception:
                        waiters = [message.future]
                    for fut in waiters:
                        try:
                            import asyncio as __aio
                            if isinstance(fut, __aio.Future):
                                loop = getattr(fut, "_loop", None) or getattr(self, "_main_loop", None)
                                if loop and hasattr(loop, "call_soon_threadsafe"):
                                    loop.call_soon_threadsafe(lambda f=fut, r=result: (not f.done()) and f.set_result(r))
                                else:
                                    if not fut.done():
                                        fut.set_result(result)
                            else:
                                if hasattr(fut, "done") and hasattr(fut, "set_result") and not fut.done():
                                    fut.set_result(result)
                        except Exception:
                            pass
                self.push_screen(PasswordDialog(message.file_path, message.max_attempts), _on_result)
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
            # 仅处理刷新内容消息；RequestPasswordMessage 已由 @on 装饰器处理
            if isinstance(message, RefreshContentMessage):
                self.logger.info("App.on_message(RefreshContentMessage): routing refresh content message")
                if hasattr(self, 'screen') and self.screen:
                    self.screen.post_message(message)
        except Exception as e:
            self.logger.error(f"App.on_message routing failed: {e}")

    # 直接供解析线程调用的主线程桥接方法（通过 call_from_thread 调度）
    def request_password_async(self, file_path: str, max_attempts: int, future) -> None:
        """
        在 UI 线程直接 push_screen 打开密码弹窗，通过回调设置 future。
        不使用 run_worker/协程，避免在 Textual 6.3.0 下触发事件循环阻塞。
        """
        self.logger.info(f"App.request_password_async: entered for {file_path}")

        def _set_future_result(val):
            try:
                import asyncio as __aio
                if isinstance(future, __aio.Future):
                    loop = getattr(future, "_loop", None) or getattr(self, "_main_loop", None)
                    if loop and hasattr(loop, "call_soon_threadsafe"):
                        loop.call_soon_threadsafe(lambda: (not future.done()) and future.set_result(val))
                    else:
                        if not future.done():
                            future.set_result(val)
                else:
                    if hasattr(future, "done") and hasattr(future, "set_result") and not future.done():
                        future.set_result(val)
            except Exception:
                try:
                    if hasattr(future, "done") and hasattr(future, "set_result") and not future.done():
                        future.set_result(None)
                except Exception:
                    pass

        try:
            # 抑制默认动画，避免覆盖输入
            try:
                if hasattr(self, "animation_manager") and getattr(self, "animation_manager"):
                    self.animation_manager.hide_default()
            except Exception:
                pass

            from src.ui.dialogs.password_dialog import PasswordDialog
            self.logger.info(f"App.request_password_async: showing dialog for {file_path}")

            # 已有模态激活则进入队列，避免重复弹窗
            if getattr(self, "_modal_active", False):
                try:
                    self._password_waiters.append(future)
                except Exception:
                    pass
                return

            # 标记模态激活并登记等待者
            self._modal_active = True
            try:
                self._password_waiters.append(future)
            except Exception:
                pass

            def _on_result(result):
                # 弹窗结束，取消模态标记，并将结果分发给所有等待者
                self._modal_active = False
                try:
                    waiters = list(getattr(self, "_password_waiters", []))
                    self._password_waiters = []
                except Exception:
                    waiters = [future]
                for fut in waiters:
                    try:
                        if hasattr(fut, "done") and hasattr(fut, "set_result") and not fut.done():
                            _set_future_result(result if result is not None else None)
                    except Exception:
                        pass

            # 直接在 UI 线程推屏。调用方确保通过 schedule_on_ui/call_from_thread 投递到 UI 线程。
            self.push_screen(PasswordDialog(file_path, max_attempts), _on_result)
        except Exception as e:
            self.logger.error(f"App.request_password_async failed: {e}")
            _set_future_result(None)

    def on_screen_resume(self, screen: Screen[None]) -> None:
        """
        屏幕恢复时的回调
        
        Args:
            screen: 屏幕对象
        """
        # 更新标题
        if hasattr(screen, "TITLE"):
            self._sub_title = screen.TITLE

    def _on_content_theme_changed(self, name: str) -> None:
        """
        当设置中心的阅读内容主题名称变化时，联动应用 UI 主题到同名主题，并刷新全局。
        """
        try:
            if not name:
                return
            # 设置并应用到 App 与所有屏幕
            if self.theme_manager.set_theme(name):
                # 应用到 App
                self.theme_manager.apply_theme_to_screen(self)
                # 强制重载 CSS（若可用）
                try:
                    if hasattr(self, "reload_css") and callable(getattr(self, "reload_css")):
                        self.reload_css()  # type: ignore[attr-defined]
                except Exception:
                    pass
                # 应用到所有已安装屏幕
                try:
                    screens = []
                    if hasattr(self, "installed_screens"):
                        screens = list(getattr(self, "installed_screens").values())  # type: ignore[attr-defined]
                    elif hasattr(self, "screens"):
                        screens = list(getattr(self, "screens").values())  # type: ignore[attr-defined]
                    for sc in screens:
                        try:
                            self.theme_manager.apply_theme_to_screen(sc)
                        except Exception:
                            pass
                except Exception:
                    pass
                # 刷新当前屏幕
                try:
                    if hasattr(self, "screen"):
                        current_screen = getattr(self, "screen")
                        if current_screen and hasattr(current_screen, "refresh"):
                            current_screen.refresh(recompose=True)
                except Exception:
                    pass
                # 持久化 UI 主题到配置
                try:
                    if hasattr(self, "config_manager") and self.config_manager:
                        cfg = self.config_manager.get_config()
                        app_cfg = cfg.get("app", {})
                        app_cfg["theme"] = name
                        cfg["app"] = app_cfg
                        if hasattr(self.config_manager, "save_config"):
                            self.config_manager.save_config(cfg)  # type: ignore[attr-defined]
                except Exception:
                    pass
                # 全局刷新
                try:
                    try:
                        self.refresh(layout=True)
                    except Exception:
                        self.refresh()
                    if self.screen and hasattr(self.screen, "refresh"):
                        self.screen.refresh(recompose=True)
                    # 刷新其它屏幕
                    try:
                        screens = []
                        if hasattr(self, "installed_screens"):
                            screens = list(getattr(self, "installed_screens").values())  # type: ignore[attr-defined]
                        elif hasattr(self, "screens"):
                            screens = list(getattr(self, "screens").values())  # type: ignore[attr-defined]
                        for sc in screens:
                            if sc is not self.screen and hasattr(sc, "refresh"):
                                sc.refresh(recompose=True)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"联动应用 UI 主题失败（可忽略）：{e}")

    # 显式声明 schedule_on_ui 实例方法，委托到通用函数，消除类型检查告警
    def schedule_on_ui(self, fn) -> None:
        try:
            # 调用模块级封装
            from src.ui.app import schedule_on_ui as _schedule_on_ui
            _schedule_on_ui(self, fn)
        except Exception as ex:
            try:
                fn()
            except Exception:
                logger.debug(f"schedule_on_ui delegate failed: {ex}")

    def _force_theme_refresh(self) -> None:
        """
        深度强制刷新主题：
        - reload_css（若支持）
        - App 布局刷新
        - 当前屏幕与其他屏幕 recompose 刷新
        - 对当前屏幕所有子组件递归 refresh(recompose=True)
        """
        # 1) 强制重载 CSS（若可用）
        try:
            if hasattr(self, "reload_css") and callable(getattr(self, "reload_css")):
                self.reload_css()  # type: ignore[attr-defined]
        except Exception:
            pass

        # 2) App 刷新布局
        try:
            try:
                self.refresh(layout=True)
            except Exception:
                self.refresh()
        except Exception:
            pass

        # 3) 收集屏幕列表
        screens = []
        try:
            if hasattr(self, "installed_screens"):
                screens = list(getattr(self, "installed_screens").values())  # type: ignore[attr-defined]
            elif hasattr(self, "screens"):
                screens = list(getattr(self, "screens").values())  # type: ignore[attr-defined]
        except Exception:
            screens = []

        # 4) 当前屏幕优先深度刷新
        try:
            current = getattr(self, "screen", None)
            if current:
                try:
                    # recompose 当前屏幕
                    if hasattr(current, "refresh"):
                        current.refresh(recompose=True)
                except Exception:
                    pass
                # 遍历所有子部件递归 recompose
                try:
                    # 优先使用 query("*")
                    if hasattr(current, "query"):
                        for w in list(current.query("*")):
                            try:
                                if hasattr(w, "refresh"):
                                    w.refresh(recompose=True)
                            except Exception:
                                pass
                    else:
                        # 兜底：尝试 children 属性
                        children = getattr(current, "children", None)
                        if children:
                            for w in list(children):
                                try:
                                    if hasattr(w, "refresh"):
                                        w.refresh(recompose=True)
                                except Exception:
                                    pass
                except Exception:
                    pass
        except Exception:
            pass

        # 5) 其他屏幕 recompose
        try:
            for sc in screens:
                if sc is not getattr(self, "screen", None):
                    try:
                        if hasattr(sc, "refresh"):
                            sc.refresh(recompose=True)
                    except Exception:
                        pass
        except Exception:
            pass

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
    try:
        if hasattr(app, "_memory_monitor") and getattr(app, "_memory_monitor"):
            app._memory_monitor.stop()
    except Exception:
        pass

# 伪用户系统：权限检查
def _has_permission(app_self: NewReaderApp, perm_key: str) -> bool:
    try:
        # 检查多用户设置，如果禁用则自动授予所有权限
        from src.utils.multi_user_manager import multi_user_manager
        if multi_user_manager.is_super_admin_mode():
            return True
            
        user = getattr(app_self, "current_user", None)
        if not user:
            return False
        role = user.get("role")
        uid = int(user.get("id"))
        return app_self.db_manager.has_permission(uid, perm_key, role=role)
    except Exception:
        return False

setattr(NewReaderApp, "has_permission", lambda self, k: _has_permission(self, k))

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