"""爬取管理页高级筛选对话框。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, RadioButton, RadioSet

from src.core.book_categories import NO_CATEGORY, get_filter_category_options
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.string_utils import normalize_match_text


@dataclass
class CrawlerFilter:
    """爬取管理筛选条件。多选分类按命中任一处理。"""

    categories: List[str] = field(default_factory=list)
    status: str = "any"
    serial: str = "any"
    file: str = "any"
    size_min: Optional[float] = None
    size_max: Optional[float] = None
    crawl_after: Optional[str] = None
    crawl_before: Optional[str] = None

    def is_empty(self) -> bool:
        return not (
            self.categories or self.status != "any" or self.serial != "any"
            or self.file != "any" or self.size_min is not None or self.size_max is not None
            or self.crawl_after or self.crawl_before
        )

    def describe(self) -> str:
        parts: List[str] = []
        if self.categories:
            from src.locales.i18n_manager import get_global_i18n
            names = [
                get_global_i18n().t("common.no_category") if c == NO_CATEGORY else c
                for c in self.categories
            ]
            parts.append("分类 " + " | ".join(names))
        if self.status != "any":
            parts.append("结果 " + self.status)
        if self.serial != "any":
            parts.append("连载 " + self.serial)
        if self.file != "any":
            parts.append("文件 " + self.file)
        if self.size_min is not None or self.size_max is not None:
            lo = f"{self.size_min}MB" if self.size_min is not None else "*"
            hi = f"{self.size_max}MB" if self.size_max is not None else "*"
            parts.append(f"大小 {lo}-{hi}")
        if self.crawl_after or self.crawl_before:
            parts.append(f"爬取 {self.crawl_after or '*'}~{self.crawl_before or '*'}")
        return " + ".join(parts) if parts else "全部记录"

    def matches(self, item: Dict[str, Any]) -> bool:
        if self.categories:
            wanted = {normalize_match_text(c) for c in self.categories if str(c).strip()}
            actual = {
                normalize_match_text(c)
                for c in (item.get("categories") or "").split(",")
                if c.strip()
            }
            want_no_category = NO_CATEGORY in self.categories
            wanted.discard(NO_CATEGORY)
            if not ((wanted & actual) or (want_no_category and not actual)):
                return False

        if self.status != "any" and item.get("status_raw") != self.status:
            return False

        serial_mode = bool(item.get("serial_mode"))
        if self.serial == "serial" and not serial_mode:
            return False
        if self.serial == "short" and serial_mode:
            return False

        has_file = bool(item.get("file_path"))
        if self.file == "has" and not has_file:
            return False
        if self.file == "no" and has_file:
            return False

        size_mb = float(item.get("file_size") or 0) / (1024 * 1024)
        if self.size_min is not None and size_mb < self.size_min:
            return False
        if self.size_max is not None and size_mb > self.size_max:
            return False

        crawl_time = str(item.get("crawl_time") or "")
        if self.crawl_after and crawl_time[:10] < self.crawl_after:
            return False
        if self.crawl_before and crawl_time[:10] > self.crawl_before:
            return False
        return True


class CrawlerFilterDialog(ModalScreen[Optional[CrawlerFilter]]):
    """按分类、状态、连载、文件、大小和时间筛选爬取记录。"""

    CSS_PATH = "../styles/crawler_filter_dialog.tcss"
    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t("common.cancel")),
    ]

    def __init__(self, theme_manager: ThemeManager,
                 current: Optional[CrawlerFilter] = None) -> None:
        super().__init__()
        self.theme_manager = theme_manager
        self.current = current or CrawlerFilter()
        self._category_options: List[str] = []

    def compose(self) -> ComposeResult:
        t = get_global_i18n().t
        yield Header()
        with ScrollableContainer(id="crawler-filter-window"):
            yield Label(t("crawler_filter.title"), id="crawler-filter-title")
            yield Label(t("crawler_filter.description"), id="crawler-filter-desc")

            yield Label(t("crawler_filter.categories"), classes="crawler-filter-cat")
            try:
                self._category_options = get_filter_category_options()
            except Exception:
                self._category_options = [NO_CATEGORY]
            with VerticalScroll(id="crawler-filter-categories"):
                for idx, name in enumerate(self._category_options):
                    label = t("common.no_category") if name == NO_CATEGORY else name
                    yield Checkbox(
                        label,
                        value=name in self.current.categories,
                        id=f"crawler-filter-category-{idx}",
                    )

            yield Label(t("crawler_filter.status"), classes="crawler-filter-cat")
            with RadioSet(id="crawler-filter-status"):
                yield RadioButton(t("crawler_filter.any"), value=self.current.status == "any", id="status-any")
                yield RadioButton(t("common.success"), value=self.current.status == "success", id="status-success")
                yield RadioButton(t("common.failed"), value=self.current.status == "failed", id="status-failed")

            yield Label(t("crawler_filter.serial"), classes="crawler-filter-cat")
            with RadioSet(id="crawler-filter-serial"):
                yield RadioButton(t("crawler_filter.any"), value=self.current.serial == "any", id="serial-any")
                yield RadioButton(t("crawler.serial_mode"), value=self.current.serial == "serial", id="serial-yes")
                yield RadioButton(t("crawler_filter.short"), value=self.current.serial == "short", id="serial-no")

            yield Label(t("crawler_filter.file"), classes="crawler-filter-cat")
            with RadioSet(id="crawler-filter-file"):
                yield RadioButton(t("crawler_filter.any"), value=self.current.file == "any", id="file-any")
                yield RadioButton(t("crawler_filter.has_file"), value=self.current.file == "has", id="file-has")
                yield RadioButton(t("crawler_filter.no_file"), value=self.current.file == "no", id="file-no")

            yield Label(t("crawler_filter.size"), classes="crawler-filter-cat")
            with Horizontal(classes="crawler-filter-range"):
                yield Input(
                    placeholder=t("crawler_filter.min_mb"),
                    value="" if self.current.size_min is None else str(self.current.size_min),
                    id="crawler-size-min",
                )
                yield Input(
                    placeholder=t("crawler_filter.max_mb"),
                    value="" if self.current.size_max is None else str(self.current.size_max),
                    id="crawler-size-max",
                )

            yield Label(t("crawler_filter.crawl_time"), classes="crawler-filter-cat")
            with Horizontal(classes="crawler-filter-range"):
                yield Input(
                    placeholder="YYYY-MM-DD",
                    value=self.current.crawl_after or "",
                    id="crawler-date-after",
                )
                yield Input(
                    placeholder="YYYY-MM-DD",
                    value=self.current.crawl_before or "",
                    id="crawler-date-before",
                )

            with Horizontal(id="crawler-filter-buttons", classes="btn-row"):
                yield Button(t("common.confirm"), id="crawler-filter-confirm", variant="primary")
                yield Button(t("common.cancel"), id="crawler-filter-cancel")
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

    def _radio(self, radio_set_id: str, default: str) -> str:
        try:
            button = self.query_one(f"#{radio_set_id}", RadioSet).pressed_button
            value = button.id or "" if button else ""
        except Exception:
            return default
        return value.rsplit("-", 1)[-1] if value else default

    def _collect(self) -> CrawlerFilter:
        categories: List[str] = []
        for idx, name in enumerate(self._category_options):
            try:
                if self.query_one(f"#crawler-filter-category-{idx}", Checkbox).value:
                    categories.append(name)
            except Exception:
                continue

        def number(value: str) -> Optional[float]:
            try:
                return float(value) if value else None
            except ValueError:
                return None

        return CrawlerFilter(
            categories=categories,
            status=self._radio("crawler-filter-status", self.current.status),
            serial=self._radio("crawler-filter-serial", self.current.serial),
            file=self._radio("crawler-filter-file", self.current.file),
            size_min=number(self._value("crawler-size-min")),
            size_max=number(self._value("crawler-size-max")),
            crawl_after=self._value("crawler-date-after") or None,
            crawl_before=self._value("crawler-date-before") or None,
        )

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "crawler-filter-confirm":
            self.dismiss(self._collect())
        elif event.button.id == "crawler-filter-cancel":
            self.action_cancel()
