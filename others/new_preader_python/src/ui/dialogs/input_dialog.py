"""
输入对话框组件
"""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from textual import events

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation

class InputDialog(ModalScreen[Optional[str]]):
    """输入对话框"""
    
    CSS_PATH = "../styles/input_dialog_overrides.tcss"
    BINDINGS = [
        ("enter", "press('#ok-btn')", get_global_i18n().t('common.ok')),
        ("escape", "press('#cancel-btn')", get_global_i18n().t('common.cancel')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, title: str, prompt: str, placeholder: str = ""):
        """
        初始化输入对话框
        
        Args:
            theme_manager: 主题管理器
            title: 对话框标题
            prompt: 提示文本
            placeholder: 输入框占位符
        """
        super().__init__()
        self.i18n = get_global_i18n()
        self.theme_manager = theme_manager
        self.title = title
        self.prompt = prompt
        self.placeholder = placeholder
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="input-dialog"):
            yield Label(self.title, id="input-title", classes="dialog-title")
            yield Label(self.prompt, id="input-prompt")
            yield Input(placeholder=self.placeholder, id="input-field")
            with Horizontal(id="input-buttons", classes="btn-row"):
                yield Button(get_global_i18n().t('common.cancel'), id="cancel-btn", variant="primary")
                yield Button(get_global_i18n().t('common.ok'), id="ok-btn")
    
    def on_mount(self) -> None:
        """挂载时应用主题并设置焦点"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        # 应用当前主题
        current_theme = self.theme_manager.get_current_theme_name()
        self.theme_manager.set_theme(current_theme)
        # 设置输入框焦点
        self.query_one("#input-field", Input).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "ok-btn":
            input_field = self.query_one("#input-field", Input)
            self.dismiss(input_field.value)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
    
    def on_key(self, event: events.Key) -> None:
        """键盘事件处理"""
        if event.key == "enter":
            input_field = self.query_one("#input-field", Input)
            self.dismiss(input_field.value)
            event.stop()
        elif event.key == "escape":
            self.dismiss(None)
            event.stop()