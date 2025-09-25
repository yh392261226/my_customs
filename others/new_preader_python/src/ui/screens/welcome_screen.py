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

from src.utils.logger import get_logger

logger = get_logger(__name__)

class WelcomeScreen(Screen[None]):
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
        WelcomeScreen.TITLE = get_global_i18n().t('welcome.title')
        # self.i18n = get_global_i18n()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        self.screen_title = t("welcome.title")
    
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
                    Label(get_global_i18n().t('welcome.shortcut_esc'), id="shortcut-esc"),
                    id="shortcuts-bar"
                ),
                id="welcome-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "open-book-btn":
            # 显示文件路径输入框
            self._show_file_input()
        elif event.button.id == "browse-library-btn":
            self.app.push_screen("bookshelf")  # 使用标准方法切换屏幕
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
        # 显示文件路径输入框
        self._show_file_input()

    def _show_file_input(self) -> None:
        """显示文件选择对话框"""
        # 创建一个简单的输入对话框，不使用复杂的文件选择器
        from textual.screen import ModalScreen
        from textual.containers import Vertical, Horizontal
        from textual.widgets import Input, Button, Label
        from textual.app import ComposeResult
        
        class SimpleFileInputDialog(ModalScreen[Optional[str]]):
            """简单的文件输入对话框"""
            
            def __init__(self, title: str, placeholder: str):
                super().__init__()
                self.title = title
                self.placeholder = placeholder
            
            def compose(self) -> ComposeResult:
                with Vertical(id="simple-file-dialog"):
                    yield Label(self.title, id="dialog-title")
                    yield Input(placeholder=self.placeholder, id="file-input")
                    with Horizontal(id="dialog-buttons"):
                        yield Button(get_global_i18n().t('common.select'), id="select-btn", variant="primary")
                        yield Button(get_global_i18n().t('common.cancel'), id="cancel-btn")
            
            def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "select-btn":
                    file_input = self.query_one("#file-input", Input)
                    file_path = file_input.value.strip()
                    if file_path:
                        self.dismiss(file_path)
                    else:
                        self.notify(get_global_i18n().t('welcome.notify_warning'), severity="warning")
                elif event.button.id == "cancel-btn":
                    self.dismiss(None)
            
            def on_key(self, event) -> None:
                """处理键盘事件"""
                if event.key == "escape":
                    # ESC键返回，效果与点击取消按钮相同
                    self.dismiss(None)
                    event.prevent_default()
        
        # 创建并显示对话框
        dialog = SimpleFileInputDialog(
            title=get_global_i18n().t('welcome.select_book_title'),
            placeholder=get_global_i18n().t('welcome.select_book_placeholder')
        )
        
        self.app.push_screen(dialog, self._handle_simple_file_selection)
    
    def _handle_simple_file_selection(self, result: Optional[str]) -> None:
        """
        处理简单文件选择结果
        
        Args:
            result: 选择的文件路径，如果取消则为None
        """
        if result:
            try:
                # 验证文件是否存在
                import os
                if not os.path.exists(result):
                    self.notify(get_global_i18n().t('welcome.file_does_not_exists'), severity="error")
                    return
                
                if not os.path.isfile(result):
                    self.notify(get_global_i18n().t('welcome.path_not_file'), severity="error")
                    return
                
                # 检查文件格式
                from src.utils.file_utils import FileUtils
                file_ext = FileUtils.get_file_extension(result)
                supported_formats = ['.txt', '.epub', '.pdf', '.mobi', '.azw3', '.azw', '.md']
                if file_ext not in supported_formats:
                    self.notify(f"{get_global_i18n().t('welcome.not_suppose_ext', ext=file_ext)}: {', '.join(supported_formats)}", severity="error")
                    return
                
                # 验证书籍是否在书架中
                if not self._is_book_in_bookshelf(result):
                    # 如果不在书架中，自动添加到书架
                    self._add_book_to_bookshelf(result)
                    self.notify(get_global_i18n().t('welcome.added_to_bookshelf'), severity="information")
                
                # 调用应用程序的文件打开方法
                self.app._open_book_file(result)
            except Exception as e:
                self.notify(f"{get_global_i18n().t('welcome.open_failed')}: {str(e)}", severity="error")
    


    def _is_book_in_bookshelf(self, file_path: str) -> bool:
        """检查书籍是否在书架中"""
        try:
            # 使用应用程序的书架实例检查书籍是否存在
            book = self.app.bookshelf.get_book(file_path)
            return book is not None
        except Exception as e:
            self.notify(f"{get_global_i18n().t('welcome.check_bookshelf_error')}: {str(e)}", severity="error")
            return False

    def _add_book_to_bookshelf(self, file_path: str) -> None:
        """将书籍添加到书架"""
        try:
            # 使用应用程序的书架实例添加书籍
            book = self.app.bookshelf.add_book(file_path)
            if book:
                import os
                book_name = os.path.basename(file_path)
                self.notify(f"《{book_name}》{get_global_i18n().t('welcome.added_success')}", severity="success")
            else:
                self.notify(get_global_i18n().t('welcome.added_failed'), severity="error")
        except Exception as e:
            self.notify(f"{get_global_i18n().t('welcome.added_error')}: {str(e)}", severity="error")

    def key_f2(self) -> None:
        """F2快捷键 - 浏览书库"""
        self.app.push_screen("bookshelf")

    def key_f3(self) -> None:
        """F3快捷键 - 打开设置"""
        self.app.push_screen("settings")

    def key_f4(self) -> None:
        """F4快捷键 - 打开统计"""
        self.app.push_screen("statistics")

    def key_f5(self) -> None:
        """F5快捷键 - 打开帮助"""
        self.app.push_screen("help")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键退出阅读器
            self.app.exit()
            event.prevent_default()