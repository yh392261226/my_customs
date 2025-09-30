"""
批量输入对话框，用于批量设置作者和标签时的输入
"""

from typing import Optional, Callable
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Input, Label
from textual import on
from textual import events
from textual.events import Key

from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class BatchInputDialog(ModalScreen[str]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """批量输入对话框"""
    
    def __init__(self, title: str, placeholder: str = "", callback: Optional[Callable[[str], None]] = None):
        """
        初始化输入对话框
        
        Args:
            title: 对话框标题
            placeholder: 输入框占位符
            callback: 回调函数，接收输入的值
        """
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        self.callback = callback
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        i18n = get_global_i18n()
        
        with Container(id="batch-input-dialog"):
            with Vertical():
                yield Label(self.title, id="input-title")
                yield Input(placeholder=self.placeholder, id="input-field")
                
                with Container(id="input-buttons"):
                    yield Button(i18n.t("common.confirm"), id="confirm-btn", variant="primary")
                    yield Button(i18n.t("common.cancel"), id="cancel-btn")
    
    def on_mount(self) -> None:
        """挂载时设置焦点"""
        self.query_one("#input-field", Input).focus()
    
    @on(Button.Pressed, "#confirm-btn")
    def on_confirm(self) -> None:
        """确认按钮点击事件"""
        input_field = self.query_one("#input-field", Input)
        value = input_field.value.strip()
        
        if value and self.callback:
            self.callback(value)
        
        self.dismiss(value)
    
    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """取消按钮点击事件"""
        self.dismiss(None)
    
    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """输入框提交事件"""
        value = event.value.strip()
        
        if value and self.callback:
            self.callback(value)
        
        self.dismiss(value)
    
    def on_key(self, event: events.Key) -> None:
        """按键事件处理"""
        if event.key == "escape":
            self.dismiss(None)
            event.prevent_default()