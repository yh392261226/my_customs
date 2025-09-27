"""
确认对话框
"""

from typing import Optional
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ConfirmDialog(ModalScreen[bool]):
    """确认对话框"""
    
    def __init__(self, theme_manager: ThemeManager, title: str, message: str):
        """
        初始化确认对话框
        
        Args:
            theme_manager: 主题管理器
            title: 对话框标题
            message: 确认消息
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.title = title
        self.message = message
    
    def compose(self) -> ComposeResult:
        """
        组合确认对话框界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Vertical(
                Static(self.title, id="confirm-dialog-title"),
                Static(self.message, id="confirm-dialog-message"),
                
                # 操作按钮
                Horizontal(
                    Button(get_global_i18n().t('confirm_dialog.confirm'), id="confirm-btn", variant="primary"),
                    Button(get_global_i18n().t('confirm_dialog.cancel'), id="cancel-btn"),
                    id="confirm-dialog-buttons"
                ),
                id="confirm-dialog-container"
            )
        )
    
    def on_mount(self) -> None:
        """对话框挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "confirm-btn":
            self.dismiss(True)  # 确认
        elif event.button.id == "cancel-btn":
            self.dismiss(False)  # 取消
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键取消
            self.dismiss(False)
            event.prevent_default()
        elif event.key == "enter":
            # Enter键确认
            self.dismiss(True)
            event.prevent_default()