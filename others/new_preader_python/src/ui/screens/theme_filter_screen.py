"""
主题过滤选择器屏幕
提供搜索/过滤功能，从大量主题中快速定位
"""
from typing import Optional
from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import Input, OptionList, Label
from textual import on, events
from textual.app import ComposeResult

from src.locales.i18n_manager import get_global_i18n
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThemeFilterScreen(ModalScreen[Optional[str]]):
    """带搜索过滤的主题选择弹窗，类似 Textual 内置主题切换器的过滤体验"""

    CSS_PATH = "../styles/theme_filter_screen.tcss"

    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t("common.cancel")),
    ]

    def __init__(self, themes: list[str], current_theme: str) -> None:
        super().__init__()
        self._all_themes = sorted(themes, key=str.lower)
        self._current_theme = current_theme
        self._filter_text: str = ""

    def compose(self) -> ComposeResult:
        i18n = get_global_i18n()
        with Container(id="theme-filter-container"):
            yield Label(i18n.t("settings.theme_filter_title", default="主题选择"), id="theme-filter-title")
            yield Input(
                placeholder=i18n.t("settings.theme_filter_placeholder", default="输入关键词筛选主题..."),
                id="theme-filter-input",
            )
            yield OptionList(*self._all_themes, id="theme-filter-list")

    def on_mount(self) -> None:
        """挂载后聚焦到搜索框，并高亮当前主题"""
        try:
            input_widget = self.query_one("#theme-filter-input", Input)
            input_widget.focus()
        except Exception:
            pass
        # 高亮当前使用的主题
        self._highlight_current()

    def _highlight_current(self) -> None:
        """在列表中高亮当前使用的主题（如果可见）"""
        try:
            option_list = self.query_one("#theme-filter-list", OptionList)
            for i, opt in enumerate(option_list._options):
                prompt = str(getattr(opt, "prompt", ""))
                if prompt == self._current_theme:
                    option_list.highlighted = i
                    break
        except Exception:
            pass

    def _get_filtered_themes(self) -> list[str]:
        """根据当前过滤文本，返回匹配的主题列表"""
        if not self._filter_text:
            return self._all_themes
        lower_filter = self._filter_text.lower()
        return [t for t in self._all_themes if lower_filter in t.lower()]

    def _rebuild_list(self) -> None:
        """根据过滤条件重建 OptionList"""
        try:
            option_list = self.query_one("#theme-filter-list", OptionList)
            filtered = self._get_filtered_themes()
            option_list.clear_options()
            if filtered:
                option_list.add_options(filtered)
            option_list.highlighted = 0
        except Exception as e:
            logger.debug(f"重建主题列表失败: {e}")

    @on(Input.Changed, "#theme-filter-input")
    def on_filter_input_changed(self, event: Input.Changed) -> None:
        """过滤文本变化时实时更新列表"""
        self._filter_text = event.value or ""
        self._rebuild_list()

    @on(OptionList.OptionSelected, "#theme-filter-list")
    def on_theme_selected(self, event: OptionList.OptionSelected) -> None:
        """选中某个主题后关闭弹窗并返回主题名"""
        try:
            name = str(getattr(event.option, "prompt", ""))
        except Exception:
            name = ""
        if name:
            self.dismiss(name)

    def action_cancel(self) -> None:
        """取消选择"""
        self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        """键盘事件：在 Input 中按上下方向键时导航列表，按回车选择"""
        if event.key == "down":
            try:
                option_list = self.query_one("#theme-filter-list", OptionList)
                filtered = self._get_filtered_themes()
                if filtered:
                    hl = option_list.highlighted
                    if hl < len(filtered) - 1:
                        option_list.highlighted = hl + 1
                    else:
                        option_list.highlighted = 0
                event.stop()
            except Exception:
                pass
        elif event.key == "up":
            try:
                option_list = self.query_one("#theme-filter-list", OptionList)
                filtered = self._get_filtered_themes()
                if filtered:
                    hl = option_list.highlighted
                    if hl > 0:
                        option_list.highlighted = hl - 1
                    else:
                        option_list.highlighted = len(filtered) - 1
                event.stop()
            except Exception:
                pass
        elif event.key == "enter":
            try:
                option_list = self.query_one("#theme-filter-list", OptionList)
                filtered = self._get_filtered_themes()
                hl = option_list.highlighted
                if 0 <= hl < len(filtered):
                    self.dismiss(filtered[hl])
                event.stop()
            except Exception:
                pass
