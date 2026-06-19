"""
合并模式日期范围选择弹窗

用户选择从哪天到哪天的爬取记录作为合并依据。
"""
from typing import Optional, Dict
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Label, Input
from textual.app import ComposeResult

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrawlerMergeDateRangeDialog(ModalScreen[Optional[Dict[str, str]]]):
    """日期范围选择弹窗"""

    CSS_PATH = "../styles/crawler_merge_date_range_dialog.tcss"

    BINDINGS = [
        ("enter", "confirm", "确认"),
        ("escape", "cancel", "取消"),
    ]

    def __init__(
        self,
        theme_manager: ThemeManager,
        min_date: str,
        max_date: str,
        site_name: str = "",
    ) -> None:
        super().__init__()
        self.theme_manager = theme_manager
        self.min_date = min_date
        self.max_date = max_date
        self.site_name = site_name
        self.i18n = get_global_i18n()

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                # 标题
                Label(
                    self.i18n.t('merge_range.title', site=self.site_name),
                    id="merge-range-title",
                ),
                # 说明
                Label(
                    self.i18n.t(
                        'merge_range.hint',
                        min_date=self.min_date,
                        max_date=self.max_date,
                    ),
                    id="merge-range-hint",
                ),
                # 起始日期
                Horizontal(
                    Label(self.i18n.t('merge_range.start_date'), classes="range-label"),
                    Input(
                        value=self.min_date,
                        placeholder="YYYY-MM-DD",
                        id="start-date-input",
                    ),
                    id="range-start-row",
                ),
                # 结束日期
                Horizontal(
                    Label(self.i18n.t('merge_range.end_date'), classes="range-label"),
                    Input(
                        value=self.max_date,
                        placeholder="YYYY-MM-DD",
                        id="end-date-input",
                    ),
                    id="range-end-row",
                ),
                # 按钮
                Horizontal(
                    Button(
                        self.i18n.t('merge_range.confirm'),
                        id="range-confirm-btn",
                        variant="primary",
                    ),
                    Button(
                        self.i18n.t('common.cancel'),
                        id="range-cancel-btn",
                    ),
                    id="range-buttons",
                ),
                id="merge-range-container",
            ),
            id="merge-range-outer",
        )

    def on_mount(self) -> None:
        self.theme_manager.apply_theme_to_screen(self)
        start_input = self.query_one("#start-date-input", Input)
        self.set_focus(start_input)

    def action_confirm(self) -> None:
        """确认选择"""
        start = self.query_one("#start-date-input", Input).value.strip()
        end = self.query_one("#end-date-input", Input).value.strip()

        if not start or not end:
            return

        if start > end:
            start, end = end, start

        self.dismiss({"start_date": start, "end_date": end})

    def action_cancel(self) -> None:
        """取消"""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "range-confirm-btn":
            self.action_confirm()
        elif event.button.id == "range-cancel-btn":
            self.action_cancel()
