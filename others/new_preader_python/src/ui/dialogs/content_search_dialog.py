"""
简单搜索对话框组件 - 用于在当前小说内容中搜索关键词
"""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from textual import events

from src.themes.theme_manager import ThemeManager
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class ContentSearchDialog(ModalScreen[Optional[str]]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """简单搜索关键词对话框 - 用于在当前小说内容中搜索关键词"""
    
    CSS_PATH = "../styles/search_dialog.css"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化搜索关键词对话框
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        self.theme_manager = theme_manager
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="search-dialog"):
            yield Label(get_global_i18n().t("simple_search_dialog.search_current"), id="search-title")
            yield Input(placeholder=get_global_i18n().t("simple_search_dialog.enter_keywords"), id="search-input")
            with Horizontal(id="search-buttons"):
                yield Button(f"← {get_global_i18n().t("common.cancel")}", id="cancel-btn", variant="primary")
                yield Button(get_global_i18n().t("common.search"), id="search-btn", disabled=True)
    
    def on_mount(self) -> None:
        """挂载时应用主题并聚焦输入框"""
        # 应用当前主题
        current_theme = self.theme_manager.get_current_theme_name()
        self.theme_manager.set_theme(current_theme)
        # 聚焦输入框
        self.query_one("#search-input", Input).focus()
        
    def on_input_changed(self, event: Input.Changed) -> None:
        """输入变化时更新搜索按钮状态"""
        if event.input.id == "search-input":
            has_text = bool(event.input.value and event.input.value.strip())
            self.query_one("#search-btn", Button).disabled = not has_text
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "search-btn":
            search_input = self.query_one("#search-input", Input)
            search_text = search_input.value.strip()
            if search_text:
                self.dismiss(search_text)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
            
    def on_key(self, event: events.Key) -> None:
        """键盘事件处理"""
        if event.key == "enter":
            # 回车键执行搜索
            search_input = self.query_one("#search-input", Input)
            search_text = search_input.value.strip()
            if search_text:
                self.dismiss(search_text)
        elif event.key == "escape":
            self.dismiss(None)