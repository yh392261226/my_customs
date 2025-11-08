"""
排序对话框
"""

from typing import Optional, List, Dict, Any
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RadioSet, RadioButton
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

from src.themes.theme_manager import ThemeManager

class SortDialog(ModalScreen[Dict[str, Any]]):
    """排序对话框"""
    
    CSS_PATH = "../styles/sort_dialog_overrides.tcss"
    BINDINGS = [
        ("enter", "press('#apply-btn')", get_global_i18n().t('common.apply')),
        ("escape", "press('#cancel-btn')", get_global_i18n().t('common.cancel')),
    ]
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化排序对话框
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        self.i18n = get_global_i18n()
        self.theme_manager = theme_manager
        self.sort_key = "title"
        self.reverse = False
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="sort-dialog"):
            yield Label(get_global_i18n().t("sort.title"), id="sort-title", classes="section-title")
            
            # 排序字段选择
            yield Label(get_global_i18n().t("sort.sort_by"), id="sort-by-label", classes="section-title")
            with RadioSet(id="sort-key-radio"):
                yield RadioButton(get_global_i18n().t("common.book_name"), value=True, id="title-radio")
                yield RadioButton(get_global_i18n().t("bookshelf.author"), id="author-radio")
                yield RadioButton(get_global_i18n().t("bookshelf.add_date"), id="add-date-radio")
                yield RadioButton(get_global_i18n().t("bookshelf.last_read"), id="last-read-radio")
                yield RadioButton(get_global_i18n().t("bookshelf.progress"), id="progress-radio")
                yield RadioButton(get_global_i18n().t("bookshelf.file_size"), id="file-size-radio")
            
            # 排序顺序选择
            yield Label(get_global_i18n().t("sort.order"), id="order-label", classes="section-title")
            with RadioSet(id="sort-order-radio"):
                yield RadioButton(get_global_i18n().t("sort.ascending"), value=True, id="asc-radio")
                yield RadioButton(get_global_i18n().t("sort.descending"), id="desc-radio")
            
            # 操作按钮
            with Horizontal(id="sort-buttons", classes="btn-row"):
                yield Button(get_global_i18n().t("common.apply"), id="apply-btn", classes="btn")
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-btn", classes="btn")
    
    def on_mount(self) -> None:
        """挂载时应用主题"""
        # 应用当前主题
        current_theme = self.theme_manager.get_current_theme_name()
        self.theme_manager.set_theme(current_theme)
    
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """单选按钮变化时的回调"""
        radio_set = event.radio_set
        if radio_set.id == "sort-key-radio":
            # 更新排序字段
            pressed_button = radio_set.pressed_button
            if pressed_button and pressed_button.id == "title-radio":
                self.sort_key = "title"
            elif pressed_button and pressed_button.id == "author-radio":
                self.sort_key = "author"
            elif pressed_button and pressed_button.id == "add-date-radio":
                self.sort_key = "add_date"
            elif pressed_button and pressed_button.id == "last-read-radio":
                self.sort_key = "last_read_date"
            elif pressed_button and pressed_button.id == "progress-radio":
                self.sort_key = "progress"
            elif pressed_button and pressed_button.id == "file-size-radio":
                self.sort_key = "file_size"
        
        elif radio_set.id == "sort-order-radio":
            # 更新排序顺序
            pressed_button = radio_set.pressed_button
            if pressed_button and pressed_button.id == "asc-radio":
                self.reverse = False
            elif pressed_button and pressed_button.id == "desc-radio":
                self.reverse = True
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "apply-btn":
            # 返回排序参数
            self.dismiss({
                "sort_key": self.sort_key,
                "reverse": self.reverse
            })
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        """键盘事件处理：确保 ESC 能关闭，Enter 能应用"""
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
        elif event.key == "enter":
            self.dismiss({
                "sort_key": self.sort_key,
                "reverse": self.reverse
            })
            event.stop()

