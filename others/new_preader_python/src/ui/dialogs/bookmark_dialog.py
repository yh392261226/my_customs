"""
书签备注输入对话框 - 用于为书签添加备注信息
"""

from typing import Dict, Any
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input
from textual import events
from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n, t

class BookmarkDialog(ModalScreen[Dict[str, Any]]):
    """书签备注输入对话框"""
    
    CSS_PATH = "../styles/bookmark_dialog.css"
    
    def __init__(self, bookmark_data: Dict[str, Any]) -> None:
        super().__init__()
        self.bookmark_data = bookmark_data

    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(get_global_i18n().t("add_bookmark_note"), id="dialog-title")
            yield Input(
                placeholder=get_global_i18n().t("enter_bookmark_note_optional"),
                id="notes-input"
            )
            with Container(id="dialog-buttons"):
                yield Button(get_global_i18n().t("common.ok"), id="confirm-button", variant="primary")
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-button", variant="error")

    def on_mount(self) -> None:
        """对话框挂载时的回调"""
        input_widget = self.query_one("#notes-input", Input)
        input_widget.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "confirm-button":
            self._confirm_bookmark()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """输入框提交时的回调"""
        self._confirm_bookmark()

    def _confirm_bookmark(self) -> None:
        """确认书签添加"""
        input_widget = self.query_one("#notes-input", Input)
        note = input_widget.value.strip()
        
        # 更新书签数据
        bookmark_data = self.bookmark_data.copy()
        if note:
            bookmark_data["note"] = note
        
        self.dismiss(bookmark_data)

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回，效果与点击取消按钮相同
            self.dismiss(None)
            event.prevent_default()

# 工厂函数
def create_bookmark_dialog(bookmark_data: Dict[str, Any]) -> BookmarkDialog:
    """创建书签备注对话框实例"""
    return BookmarkDialog(bookmark_data)