"""
爬取历史合并对话框
"""

from itertools import count
from typing import Dict, Any, List
from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label
from src.themes.theme_manager import ThemeManager
from src.locales.i18n_manager import get_global_i18n


class CrawlerMergeDialog(ModalScreen[Dict[str, Any]]):
    """爬取历史合并对话框"""
    
    CSS_PATH = "../styles/crawler_merge_dialog_overrides.tcss"
    
    def __init__(self, theme_manager: ThemeManager, selected_items: List[Dict[str, Any]], **kwargs) -> None:
        super().__init__(**kwargs)
        self.theme_manager = theme_manager
        self.selected_items = selected_items
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(classes="crawler-merge-dialog"):
            yield Label(get_global_i18n().t('batch_ops.merge_description'), classes="dialog-title")
            
            # 显示选中的记录信息
            yield Label(f"{get_global_i18n().t('batch_ops.selected_count', count=len(self.selected_items))}", classes="info-label")
            
            # 输入新书籍标题
            yield Label(get_global_i18n().t('batch_ops.merge_enter_title'), classes="input-label")
            yield Input(placeholder=get_global_i18n().t('batch_ops.merge_title_placeholder'), id="merge-title-input")
            
            # 按钮区域
            with Center():
                yield Button(get_global_i18n().t('common.merge'), id="confirm-merge-btn", variant="primary")
                yield Button(get_global_i18n().t('common.cancel'), id="cancel-merge-btn")
    
    def on_mount(self) -> None:
        """挂载时设置焦点"""
        self.query_one("#merge-title-input", Input).focus()
    
    @on(Button.Pressed, "#confirm-merge-btn")
    def on_confirm_merge(self) -> None:
        """确认合并按钮点击事件"""
        title_input = self.query_one("#merge-title-input", Input)
        new_title = title_input.value.strip()
        
        if not new_title:
            # 显示错误提示
            self.notify(get_global_i18n().t('batch_ops.enter_new_title'), severity="error")
            return
        
        # 返回合并结果
        self.dismiss({
            "success": True,
            "action": "merge",
            "new_title": new_title,
            "selected_items": self.selected_items,
            "message": get_global_i18n().t('batch_ops.merge_submitted')
        })
    
    @on(Button.Pressed, "#cancel-merge-btn")
    def on_cancel_merge(self) -> None:
        """取消合并按钮点击事件"""
        self.dismiss({
            "success": False,
            "action": "merge",
            "message": get_global_i18n().t('batch_ops.cancel_merge')
        })
    
    @on(Input.Submitted, "#merge-title-input")
    def on_input_submitted(self) -> None:
        """输入框回车提交"""
        self.on_confirm_merge()
    
    def on_key(self, event) -> None:
        """按键事件处理"""
        if event.key == "escape":
            self.on_cancel_merge()
            event.stop()