"""
书签编辑对话框 - 用于编辑书签备注
"""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Input, Label
from textual import on
from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n, t

class BookmarkEditDialog(ModalScreen[str]):
    """书签编辑对话框"""
    
    CSS_PATH = "../styles/bookmark_edit_dialog.css"
    
    def __init__(self, bookmark_info: str, current_note: str = ""):
        super().__init__()
        self.bookmark_info = bookmark_info
        self.current_note = current_note or ""
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        yield Container(
            Vertical(
                Label(get_global_i18n().t('bookmark_edit.title'), id="title"),
                Label(get_global_i18n().t('bookmark_edit.info', bookmark_info=self.bookmark_info), id="info"),
                Container(
                    Input(
                        value=self.current_note,
                        placeholder=get_global_i18n().t('bookmark_edit.placeholder'),
                        id="note-input"
                    ),
                    id="input-container"
                ),
                Horizontal(
                    Button(get_global_i18n().t('common.ok'), variant="primary", id="confirm"),
                    Button(get_global_i18n().t('common.cancel'), variant="default", id="cancel"),
                    Button(get_global_i18n().t('bookmark_edit.clear'), variant="warning", id="clear"),
                    id="buttons"
                ),
                id="dialog"
            )
        )
    
    def on_mount(self) -> None:
        """挂载时聚焦到输入框"""
        input_widget = self.query_one("#note-input", Input)
        input_widget.focus()
        # 选中所有文本以便快速编辑
        if self.current_note:
            input_widget.cursor_position = len(self.current_note)
    
    @on(Button.Pressed, "#confirm")
    def on_confirm(self) -> None:
        """确定按钮"""
        input_widget = self.query_one("#note-input", Input)
        note = input_widget.value.strip()
        self.dismiss(note)
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self) -> None:
        """取消按钮"""
        self.dismiss(None)
    
    @on(Button.Pressed, "#clear")
    def on_clear(self) -> None:
        """清空按钮"""
        input_widget = self.query_one("#note-input", Input)
        input_widget.value = ""
        input_widget.focus()
    
    @on(Input.Submitted, "#note-input")
    def on_input_submitted(self) -> None:
        """输入框回车提交"""
        self.on_confirm()
    
    def on_key(self, event) -> None:
        """键盘事件处理"""
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "ctrl+s":
            self.on_confirm()