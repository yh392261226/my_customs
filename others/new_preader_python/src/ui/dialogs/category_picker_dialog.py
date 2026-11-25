"""分类多选对话框：为单本或批量书籍设置题材分类。"""
from __future__ import annotations

import re
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label

from src.core.book_categories import get_known_categories
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager


class CategoryPickerDialog(ModalScreen[Optional[List[str]]]):
    """勾选已有分类，并可输入新分类名（逗号或竖线分隔）。"""

    CSS_PATH = "../styles/category_picker_dialog.tcss"
    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t("common.cancel")),
    ]

    def __init__(self, theme_manager: ThemeManager,
                 categories: Optional[List[str]] = None,
                 title: Optional[str] = None) -> None:
        super().__init__()
        self.theme_manager = theme_manager
        self.current = list(categories or [])
        self.dialog_title = title or get_global_i18n().t("category_picker.title")
        self._category_options: List[str] = []

    def compose(self) -> ComposeResult:
        t = get_global_i18n().t
        yield Header()
        with Container(id="category-picker-window"):
            yield Label(self.dialog_title, id="category-picker-title")
            yield Label(t("category_picker.hint"), id="category-picker-hint")
            try:
                self._category_options = get_known_categories()
            except Exception:
                self._category_options = []
            with VerticalScroll(id="category-picker-options"):
                for idx, name in enumerate(self._category_options):
                    yield Checkbox(
                        name,
                        value=name in self.current,
                        id=f"picker-category-{idx}",
                    )
            yield Input(
                placeholder=t("category_picker.custom"),
                id="picker-custom-input",
            )
            with Horizontal(id="category-picker-buttons", classes="btn-row"):
                yield Button(t("common.confirm"), id="picker-confirm-btn", variant="primary")
                yield Button(t("common.cancel"), id="picker-cancel-btn")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass

    def _custom_values(self) -> List[str]:
        try:
            raw = self.query_one("#picker-custom-input", Input).value or ""
        except Exception:
            return []
        return [part.strip() for part in re.split(r"[,|，]", raw) if part.strip()]

    def _collect(self) -> List[str]:
        result: List[str] = []
        for idx, name in enumerate(self._category_options):
            try:
                if self.query_one(f"#picker-category-{idx}", Checkbox).value:
                    result.append(name)
            except Exception:
                continue
        for name in self._custom_values():
            if name not in result:
                result.append(name)
        return result

    def action_confirm(self) -> None:
        self.dismiss(self._collect())

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "picker-confirm-btn":
            self.action_confirm()
        elif event.button.id == "picker-cancel-btn":
            self.action_cancel()
