"""设置中心：分类名称与识别别名维护对话框。"""
from __future__ import annotations

from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label

from src.core.book_categories import (
    add_category,
    delete_category,
    load_category_rules,
    save_category_rules,
    update_category,
)
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.ui.dialogs.confirm_dialog import ConfirmDialog
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _split_aliases(raw: str) -> List[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


class CategoryManageDialog(ModalScreen[None]):
    """维护分类规则：新增、改名、修改别名、删除。"""

    CSS_PATH = "../styles/category_manage_dialog.tcss"
    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t("common.cancel")),
    ]

    def __init__(self, theme_manager: ThemeManager) -> None:
        super().__init__()
        self.theme_manager = theme_manager
        self._names: List[str] = []

    def compose(self) -> ComposeResult:
        t = get_global_i18n().t
        yield Header()
        with Container(id="category-manage-window"):
            yield Label(t("category_manage.title"), id="category-manage-title")
            yield Label(t("category_manage.subtitle"), id="category-manage-subtitle")

            yield Label(t("category_manage.add_section"), classes="category-manage-section")
            with Horizontal(classes="category-manage-row"):
                yield Input(placeholder=t("category_manage.name"), id="manage-new-name")
                yield Input(placeholder=t("category_manage.aliases"), id="manage-new-aliases")
                yield Button(t("category_manage.add_button"), id="manage-add-btn", variant="primary")

            yield Label(t("category_manage.existing"), classes="category-manage-section")
            with VerticalScroll(id="category-manage-list"):
                for idx, (name, aliases) in enumerate(load_category_rules().items()):
                    self._names.append(name)
                    with Horizontal(classes="category-manage-row"):
                        yield Input(value=name, id=f"manage-name-{idx}")
                        yield Input(value=",".join(aliases), id=f"manage-alias-{idx}")
                        yield Button(t("category_manage.save_button"), id=f"manage-save-{idx}")
                        yield Button(t("category_manage.delete_button"), id=f"manage-delete-{idx}")

            with Horizontal(id="category-manage-buttons", classes="btn-row"):
                yield Button(t("common.close"), id="manage-close-btn")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass

    def _value(self, widget_id: str) -> str:
        try:
            return (self.query_one(f"#{widget_id}", Input).value or "").strip()
        except Exception:
            return ""

    def _collect_rules(self) -> Dict[str, List[str]]:
        rules: Dict[str, List[str]] = {}
        for idx, old_name in enumerate(self._names):
            name = self._value(f"manage-name-{idx}") or old_name
            aliases = _split_aliases(self._value(f"manage-alias-{idx}"))
            rules[name] = aliases
        return rules

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id or ""

        if button_id == "manage-close-btn":
            self.action_cancel()
            return

        if button_id == "manage-add-btn":
            name = self._value("manage-new-name")
            aliases = _split_aliases(self._value("manage-new-aliases"))
            if not name:
                return
            add_category(name, aliases)
            self.notify(get_global_i18n().t("common.categories_updated"), severity="information")
            self.dismiss(None)
            return

        if button_id.startswith("manage-save-"):
            idx = int(button_id.rsplit("-", 1)[-1])
            old_name = self._names[idx]
            new_name = self._value(f"manage-name-{idx}") or old_name
            aliases = _split_aliases(self._value(f"manage-alias-{idx}"))
            update_category(old_name, new_name, aliases)
            self.notify(get_global_i18n().t("common.categories_updated"), severity="information")
            self.dismiss(None)
            return

        if button_id.startswith("manage-delete-"):
            idx = int(button_id.rsplit("-", 1)[-1])
            name = self._names[idx]
            message = get_global_i18n().t("category_manage.confirm_delete").format(name=name)

            def _confirm(confirmed: Optional[bool]) -> None:
                if confirmed:
                    delete_category(name)
                    self.notify(
                        get_global_i18n().t("common.categories_updated"),
                        severity="information",
                    )
                self.dismiss(None)

            self.app.push_screen(ConfirmDialog(self.theme_manager, name, message), _confirm)
