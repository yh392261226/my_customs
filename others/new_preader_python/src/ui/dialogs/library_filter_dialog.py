"""
书库高级筛选对话框。

作者 / 标签 / 文件 / 拼音：每轴一个单选组（不限 / 无 / 有），默认「不限」。

阅读状态：单选组（不限 / 未读 / 已读 / 已读完）。

大小 / 入库时间：两段范围输入。不同分组之间为 AND，可并行组合。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Static,
)

from src.core.library_filter import LibraryFilter
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager


def _str(value: Any) -> str:
    """把范围字段的可选值转为输入框文本（None 显示为空）。"""
    return "" if value is None else str(value)


# 二元轴：轴 -> (无字段, 有字段)，用单选组（不限/无/有）控制
TRI_AXES: List[tuple] = [
    ("author", "no_author", "has_author"),
    ("tags", "no_tags", "has_tags"),
    ("file", "no_file", "file_exists"),
    ("pinyin", "no_pinyin", "has_pinyin"),
]

# 阅读状态选项（单选组，默认不限）
STATUS_OPTIONS: List[tuple] = [
    ("none", "tri_none"),
    ("unread", "unread"),
    ("read", "read"),
    ("finished", "finished"),
]


class LibraryFilterDialog(ModalScreen[Optional[Dict[str, Any]]]):
    """多条件组合筛选（同组内单选，跨组 AND 并行）。"""

    CSS_PATH = "../styles/library_filter_dialog.tcss"

    BINDINGS = [
        ("escape", "cancel", "取消"),
        ("enter", "apply", "应用"),
        ("x", "clear", "清除"),
    ]

    def __init__(self, theme_manager: ThemeManager,
                 current: Optional[LibraryFilter] = None) -> None:
        super().__init__()
        self.theme_manager = theme_manager
        self.current = current or LibraryFilter()

    def _axis_suffix(self, axis: str, no_field: str, has_field: str) -> str:
        """根据当前筛选值推断该轴应选的分段（none/no/has）。"""
        if getattr(self.current, no_field):
            return "no"
        if getattr(self.current, has_field):
            return "has"
        return "none"

    def compose(self) -> ComposeResult:
        t = get_global_i18n().t
        yield Header()
        with Container(id="library-filter-window"):
            yield Static(t("library_filter.title"), id="library-filter-title")
            yield Static(t("library_filter.description"), id="library-filter-desc")
            with VerticalScroll(id="library-filter-body"):
                # 二元轴：不限 / 无 / 有
                for axis, no_field, has_field in TRI_AXES:
                    yield Label(t(f"library_filter.cat_{axis}"), classes="library-filter-cat")
                    with Horizontal(classes="library-filter-row"):
                        yield RadioSet(
                            RadioButton(t("library_filter.tri_none"), id=f"{axis}-none"),
                            RadioButton(t("library_filter.tri_no"), id=f"{axis}-no"),
                            RadioButton(t("library_filter.tri_has"), id=f"{axis}-has"),
                            id=f"cond-{axis}",
                        )
                # 阅读状态：不限 / 未读 / 已读 / 已读完
                yield Label(t("library_filter.cat_status"), classes="library-filter-cat")
                with Horizontal(classes="library-filter-row"):
                    yield RadioSet(
                        *(RadioButton(t(f"library_filter.{label_key}"), id=f"status-{key}")
                          for key, label_key in STATUS_OPTIONS),
                        id="cond-status",
                    )
                # 大小范围（MB）
                yield Label(t("library_filter.cat_size"), classes="library-filter-cat")
                with Horizontal(classes="library-filter-range"):
                    yield Input(value=_str(self.current.size_min), placeholder=t("library_filter.size_min"),
                                id="cond-size_min", classes="library-filter-input")
                    yield Label("-", classes="library-filter-dash")
                    yield Input(value=_str(self.current.size_max), placeholder=t("library_filter.size_max"),
                                id="cond-size_max", classes="library-filter-input")
                    yield Label(t("library_filter.size_unit"), classes="library-filter-unit")
                # 入库时间范围
                yield Label(t("library_filter.cat_added"), classes="library-filter-cat")
                with Horizontal(classes="library-filter-range"):
                    yield Input(value=_str(self.current.added_after), placeholder=t("library_filter.added_after"),
                                id="cond-added_after", classes="library-filter-input")
                    yield Label("-", classes="library-filter-dash")
                    yield Input(value=_str(self.current.added_before), placeholder=t("library_filter.added_before"),
                                id="cond-added_before", classes="library-filter-input")
                    yield Label(t("library_filter.date_format"), classes="library-filter-unit")
            with Horizontal(id="library-filter-buttons", classes="btn-row"):
                yield Button(t("library_filter.apply"), id="lf-apply-btn", variant="primary")
                yield Button(t("library_filter.clear"), id="lf-clear-btn")
                yield Button(t("common.cancel"), id="lf-cancel-btn")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass
        # 根据当前筛选值设置各单选组默认选中项
        for axis, no_field, has_field in TRI_AXES:
            self._set_radio(f"cond-{axis}", f"{axis}-{self._axis_suffix(axis, no_field, has_field)}")
        status_val = "none"
        for key, _ in STATUS_OPTIONS[1:]:
            if getattr(self.current, key):
                status_val = f"status-{key}"
                break
        self._set_radio("cond-status", status_val)

    def _set_radio(self, radio_id: str, button_id: str) -> None:
        # 直接设置该单选按钮为选中、其余取消，确保视觉勾选与读取一致
        try:
            rs = self.query_one(f"#{radio_id}", RadioSet)
            for btn in rs.query(RadioButton):
                try:
                    btn.value = (btn.id == button_id)
                except Exception:
                    pass
        except Exception:
            pass

    def _radio_suffix(self, radio_id: str) -> str:
        """返回某单选组中当前选中项的后缀（none/no/has 或 status 键名）。"""
        try:
            rs = self.query_one(f"#{radio_id}", RadioSet)
            for btn in rs.query(RadioButton):
                if getattr(btn, "value", False):
                    return (btn.id or "").split("-")[-1]
        except Exception:
            pass
        return ""

    def _collect(self) -> LibraryFilter:
        state: Dict[str, Any] = {}
        # 二元轴单选组
        for axis, no_field, has_field in TRI_AXES:
            suffix = self._radio_suffix(f"cond-{axis}")
            state[no_field] = (suffix == "no")
            state[has_field] = (suffix == "has")
        # 阅读状态单选组
        status_suffix = self._radio_suffix("cond-status")
        for key, _ in STATUS_OPTIONS[1:]:
            state[key] = (status_suffix == key)

        def _num(idx: str) -> Optional[float]:
            v = (self.query_one(f"#cond-{idx}", Input).value or "").strip()
            if not v:
                return None
            try:
                return float(v)
            except Exception:
                return None

        state["size_min"] = _num("size_min")
        state["size_max"] = _num("size_max")
        state["added_after"] = (self.query_one("#cond-added_after", Input).value or "").strip() or None
        state["added_before"] = (self.query_one("#cond-added_before", Input).value or "").strip() or None
        return LibraryFilter(**state)

    def action_apply(self) -> None:
        condition = self._collect()
        self.dismiss({"filter": None if condition.is_empty() else condition.to_dict()})

    def action_clear(self) -> None:
        self.dismiss({"filter": None})

    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "lf-apply-btn":
            self.action_apply()
        elif event.button.id == "lf-clear-btn":
            self.action_clear()
        elif event.button.id == "lf-cancel-btn":
            self.action_cancel()
