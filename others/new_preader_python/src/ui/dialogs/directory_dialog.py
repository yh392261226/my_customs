"""
目录选择对话框
"""

import os
from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class DirectoryDialog(ModalScreen[Optional[str]]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """目录选择对话框"""
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化目录选择对话框
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        self.theme_manager = theme_manager
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="directory-dialog"):
            yield Label(get_global_i18n().t("bookshelf.select_directory"), id="directory-title")
            yield Input(placeholder=get_global_i18n().t("bookshelf.directory_path"), id="directory-input")
            with Horizontal(id="directory-buttons"):
                yield Button(get_global_i18n().t("common.select"), id="select-btn")
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-btn")
    
    def on_mount(self) -> None:
        """挂载时应用主题"""
        self.theme_manager.apply_theme_to_screen(self)
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "select-btn":
            directory_input = self.query_one("#directory-input", Input)
            directory_path = directory_input.value.strip()
            
            if directory_path and os.path.isdir(directory_path):
                self.dismiss(directory_path)
            else:
                self.notify(get_global_i18n().t("bookshelf.invalid_directory"), severity="error")
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
            
