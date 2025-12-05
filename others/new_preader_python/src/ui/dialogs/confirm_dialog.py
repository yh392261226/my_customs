"""
确认对话框
用于确认操作
"""

from typing import Optional, ClassVar
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Label
from textual.app import ComposeResult
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

logger = get_logger(__name__)

class ConfirmDialog(ModalScreen[Optional[bool]]):
    """确认对话框"""
    
    # 加载CSS样式
    CSS_PATH = "../styles/confirm_dialog_overrides.tcss"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("enter", "press('#confirm-btn')", get_global_i18n().t('common.confirm')),
        ("escape", "press('#cancel-btn')", get_global_i18n().t('common.cancel')),
    ]
    
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
                # 标题
                Label(self.title, id="confirm-title", classes="section-title"),
                
                # 消息内容
                Label(self.message, id="confirm-message"),
                
                # 按钮区域
                Horizontal(
                    Button(get_global_i18n().t('common.confirm'), id="confirm-btn", variant="primary"),
                    Button(get_global_i18n().t('common.cancel'), id="cancel-btn"),
                    id="confirm-buttons", classes="btn-row"
                ),
                
                id="confirm-container"
            )
        )
    
    def on_mount(self) -> None:
        """对话框挂载时的回调"""
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 设置默认焦点到确认按钮
        confirm_btn = self.query_one("#confirm-btn", Button)
        if confirm_btn:
            self.set_focus(confirm_btn)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "confirm-btn":
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.dismiss(False)
    
