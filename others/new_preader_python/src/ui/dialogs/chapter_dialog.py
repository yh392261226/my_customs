from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListView, ListItem

class ChapterDialog(ModalScreen[None]):
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
            yield Button("取消", id="cancel-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected_chapter = self.chapters[event.item_index]
        self.dismiss(selected_chapter)