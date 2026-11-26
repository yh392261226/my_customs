"""分类多选对话框：为单本或批量书籍设置题材分类。"""
from __future__ import annotations

import os
import re
from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label

from src.core.book_categories import get_known_categories
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CategoryPickerDialog(ModalScreen[Optional[List[str]]]):
    """勾选已有分类，并可输入新分类名（逗号或竖线分隔）。"""

    CSS_PATH = "../styles/category_picker_dialog.tcss"
    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t("common.cancel")),
    ]

    def __init__(self, theme_manager: ThemeManager,
                 categories: Optional[List[str]] = None,
                 title: Optional[str] = None,
                 suggest_path: Optional[str] = None,
                 suggest_title: Optional[str] = None,
                 suggest_tags: Optional[str] = None) -> None:
        super().__init__()
        self.theme_manager = theme_manager
        self.current = list(categories or [])
        self.dialog_title = title or get_global_i18n().t("category_picker.title")
        self._category_options: List[str] = []
        self.auto_suggestions: List[str] = []
        self.auto_detected: List[str] = []
        self.auto_checked = bool(suggest_path)

        # 单本编辑时，按书名/标签/正文摘要预先识别，合并到当前勾选里；
        # 批量设置不传路径，避免对多本书重复读文件。
        if suggest_path:
            try:
                from src.core.book_categories import classify_book_file
                title_for_detect = suggest_title or os.path.splitext(
                    os.path.basename(suggest_path)
                )[0]
                detected = classify_book_file(
                    suggest_path,
                    title=title_for_detect,
                    tags=suggest_tags or "",
                )
                self.auto_detected = list(detected)
                self.auto_suggestions = [c for c in detected if c not in self.current]
                for name in self.auto_suggestions:
                    self.current.append(name)
                logger.info(
                    "分类弹窗自动识别: path=%s, title=%s, detected=%s, newly_prechecked=%s",
                    suggest_path, title_for_detect, detected, self.auto_suggestions,
                )
            except Exception as exc:
                self.auto_suggestions = []
                self.auto_detected = []
                logger.warning(
                    "分类弹窗自动识别失败: path=%s, error=%s", suggest_path, exc
                )

    def compose(self) -> ComposeResult:
        t = get_global_i18n().t
        yield Header()
        with Container(id="category-picker-window"):
            yield Label(self.dialog_title, id="category-picker-title")
            if self.auto_detected:
                hint = t("category_picker.auto_hint").format(
                    categories=" | ".join(self.auto_detected)
                )
            elif self.auto_checked:
                hint = t("category_picker.no_auto_hint")
            else:
                hint = t("category_picker.hint")
            yield Label(hint, id="category-picker-hint")
            try:
                self._category_options = get_known_categories()
            except Exception:
                self._category_options = []
            for name in self.current:
                if name not in self._category_options:
                    self._category_options.append(name)
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
        logger.info(
            "分类弹窗提交: selected=%s, auto_prechecked=%s", result, self.auto_suggestions
        )
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
