"""
书籍重命名对话框
"""

import os
from typing import Optional
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Center
from textual.widgets import Static, Button, Label, Input
from textual import on, events

from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

from src.utils.logger import get_logger

logger = get_logger(__name__)

class RenameBookDialog(ModalScreen[dict]):
    """书籍重命名对话框"""
    
    CSS_PATH = "../styles/rename_book_overrides.tcss"
    
    def __init__(self, book_title: str, book_path: str) -> None:
        super().__init__()
        self.book_title = book_title
        self.book_path = book_path
        self.new_title = ""
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        yield Container(
            Vertical(
                Label(get_global_i18n().t("bookshelf.rename_book"), id="rename-title", classes="section-title"),
                
                # 当前书籍信息
                Label(f"{get_global_i18n().t('bookshelf.current_title')}: {self.book_title}", id="current-title"),
                Label(f"{get_global_i18n().t('bookshelf.file_path')}: {os.path.basename(self.book_path)}", id="file-path"),
                
                # 新书名输入
                Horizontal(
                    Label(get_global_i18n().t("bookshelf.new_title"), id="new-title-label"),
                    Input(placeholder=get_global_i18n().t("bookshelf.enter_new_title"), id="new-title-input"),
                    id="input-row"
                ),
                
                # 按钮区域
                Horizontal(
                    Button(get_global_i18n().t("common.ok"), id="ok-btn", variant="primary"),
                    Button(get_global_i18n().t("common.cancel"), id="cancel-btn"),
                    id="rename-buttons"
                ),
                
                id="rename-container"
            ),
            id="rename-dialog-container"
        )
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        
        # 聚焦输入框
        input_widget = self.query_one("#new-title-input", Input)
        input_widget.value = self.book_title  # 默认填入当前书名
        input_widget.focus()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "ok-btn":
            input_widget = self.query_one("#new-title-input", Input)
            new_title = input_widget.value.strip()
            
            if not new_title:
                self.notify(get_global_i18n().t("bookshelf.title_empty"), severity="warning")
                return
            
            if new_title == self.book_title:
                self.notify(get_global_i18n().t("bookshelf.title_same"), severity="warning")
                return
            
            self.new_title = new_title
            self.dismiss({
                "success": True,
                "new_title": new_title,
                "book_path": self.book_path
            })
            
        elif event.button.id == "cancel-btn":
            self.dismiss({"success": False})
    
    @on(Input.Submitted, "#new-title-input")
    def on_input_submitted(self) -> None:
        """输入框回车提交"""
        input_widget = self.query_one("#new-title-input", Input)
        new_title = input_widget.value.strip()
        
        if not new_title:
            self.notify(get_global_i18n().t("bookshelf.title_empty"), severity="warning")
            return
        
        if new_title == self.book_title:
            self.notify(get_global_i18n().t("bookshelf.title_same"), severity="warning")
            return
        
        self.new_title = new_title
        self.dismiss({
            "success": True,
            "new_title": new_title,
            "book_path": self.book_path
        })
    
    def on_key(self, event: events.Key) -> None:
        """按键事件处理"""
        if event.key == "escape":
            self.dismiss({"success": False})
            event.stop()