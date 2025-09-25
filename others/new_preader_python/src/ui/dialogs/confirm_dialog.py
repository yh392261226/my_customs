"""
确认对话框组件
"""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual import on, events

from src.locales.i18n_manager import get_global_i18n

class ConfirmDialog(ModalScreen[bool]):
    """确认对话框"""
    
    CSS_PATH = "../styles/confirm_dialog.css"
    
    def __init__(self, title: str, message: str, confirm_text: str = None, cancel_text: str = None):
        """
        初始化确认对话框
        
        Args:
            title: 对话框标题
            message: 确认消息内容
            confirm_text: 确认按钮文本（默认为"确认"）
            cancel_text: 取消按钮文本（默认为"取消"）
        """
        super().__init__()
        self.i18n = get_global_i18n()
        self.title = title
        self.message = message
        self.confirm_text = confirm_text or self.i18n.t("common.confirm")
        self.cancel_text = cancel_text or self.i18n.t("common.cancel")
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="confirm-dialog"):
            yield Label(self.title, id="confirm-title")
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button(self.confirm_text, id="confirm-btn", variant="primary")
                yield Button(self.cancel_text, id="cancel-btn")
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        self.query_one("#confirm-btn", Button).focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "confirm-btn":
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.dismiss(False)
    
    @on(events.Key)
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "enter":
            self.dismiss(True)
        elif event.key == "escape":
            self.dismiss(False)