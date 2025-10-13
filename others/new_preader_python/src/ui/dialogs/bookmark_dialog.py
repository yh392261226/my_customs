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
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class BookmarkDialog(ModalScreen[Dict[str, Any]]):


    
    CSS_PATH = "../styles/bookmark_dialog_overrides.tcss"
    BINDINGS = [
        ("enter", "press('#confirm-button')", get_global_i18n().t("common.ok")),
    ]
    
    def __init__(self, bookmark_data: Dict[str, Any]) -> None:
        super().__init__()
        self.bookmark_data = bookmark_data

    def compose(self) -> ComposeResult:
        with Container(id="dialog-container", classes="panel"):
            yield Label(get_global_i18n().t("add_bookmark_note"), id="dialog-title", classes="section-title")
            yield Input(
                placeholder=get_global_i18n().t("enter_bookmark_note_optional"),
                id="notes-input",
                classes="input-std"
            )
            with Container(id="dialog-buttons", classes="btn-row"):
                yield Button(get_global_i18n().t("common.ok"), id="confirm-button", variant="primary", classes="btn")
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-button", variant="error", classes="btn")

    def on_mount(self) -> None:
        """对话框挂载时应用样式并聚焦输入框"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        # 聚焦输入框
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
            # ESC键仅关闭弹窗，阻止事件冒泡到父屏幕
            self.dismiss(None)
            if hasattr(event, "prevent_default"):
                event.prevent_default()
            if hasattr(event, "stop"):
                event.stop()

# 工厂函数
def create_bookmark_dialog(bookmark_data: Dict[str, Any]) -> BookmarkDialog:
    """创建书签备注对话框实例"""
    return BookmarkDialog(bookmark_data)