"""
页面选择对话框 - 用于跳转到指定页面
"""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input
from textual import events
from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class PageDialog(ModalScreen[int]):
    """页面选择对话框"""

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    
    CSS_PATH = "../styles/bookmark_dialog_overrides.tcss"
    
    def __init__(self, total_pages: int, current_page: int = 0) -> None:
        super().__init__()
        self.total_pages = total_pages
        self.current_page = current_page

    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(get_global_i18n().t("goto_page"), id="dialog-title")
            yield Input(
                value=str(self.current_page + 1),
                placeholder=f"{get_global_i18n().t('enter_page_number')} (1-{self.total_pages})",
                id="page-input"
            )
            with Container(id="dialog-buttons"):
                yield Button(get_global_i18n().t("common.ok"), id="confirm-button", variant="primary")
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "confirm-button":
            self._confirm_selection()

    def _confirm_selection(self) -> None:
        """确认页面选择"""
        input_widget = self.query_one("#page-input", Input)
        try:
            page_num = int(input_widget.value)
            if 1 <= page_num <= self.total_pages:
                self.dismiss(page_num - 1)  # 返回0-based索引
            else:
                self.notify(get_global_i18n().t('page_between', page=self.total_pages), severity="error")
        except ValueError:
            self.notify(get_global_i18n().t('page_invalid'), severity="error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """输入框提交时的回调"""
        self._confirm_selection()

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回，效果与点击取消按钮相同
            self.dismiss(None)
            event.stop()
            event.prevent_default()