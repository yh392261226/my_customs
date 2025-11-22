from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListView, ListItem
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.locales.i18n_manager import get_global_i18n

class ChapterDialog(ModalScreen[None]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """章节选择对话框"""
    
    def __init__(self, chapters: list[str], title: str = "选择章节") -> None:
        super().__init__()
        self.chapters = chapters
        self.title = title

    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            yield Label(self.title, id="dialog-title")
            yield ListView(
                *[ListItem(Label(chapter)) for chapter in self.chapters],
                id="chapter-list"
            )
            yield Button(get_global_i18n().t("common.cancel"), id="cancel-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected_chapter = self.chapters[event.item_index]
        self.dismiss(selected_chapter)