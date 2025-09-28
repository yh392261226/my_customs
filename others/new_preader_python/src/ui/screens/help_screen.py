"""
帮助屏幕
"""


from typing import Dict, Any, Optional, List, ClassVar

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, MarkdownViewer
from textual.reactive import reactive

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n, t
from src.utils.logger import get_logger

logger = get_logger(__name__)

class HelpScreen(Screen[None]):
    """帮助屏幕"""
    CSS_PATH = "../styles/help_screen.css"
    
    def __init__(self):
        """
        初始化帮助屏幕
        """
        super().__init__()
        self.screen_title = "帮助中心"
        
        # 准备帮助内容
        self.help_content = f"""
# {get_global_i18n().t("help.title")}

## {get_global_i18n().t("help.keyboard_shortcuts")}

### {get_global_i18n().t("help.reading_operations")}

- ←/→ : {get_global_i18n().t("help.prev_next_page")}
- ↑/↓ : {get_global_i18n().t("help.scroll_content")}
- g   : {get_global_i18n().t("help.go_to_page")}
- a   : {get_global_i18n().t("help.auto_page_turn")}
- b   : {get_global_i18n().t("help.bookmark")}
- B   : {get_global_i18n().t("help.open_bookmark_list")}
- f   : {get_global_i18n().t("help.search")}
- r   : {get_global_i18n().t("help.text_to_speech")}

### {get_global_i18n().t("help.ui_settings")}

- s   : {get_global_i18n().t("help.open_settings")}
- q   : {get_global_i18n().t("help.quit")}

### {get_global_i18n().t("help.advanced_features")}

- /   : {get_global_i18n().t("help.boss_key")}

## {get_global_i18n().t("help.about")}

{get_global_i18n().t("help.about_content")}
"""
    
    def compose(self) -> ComposeResult:
        """
        组合帮助屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Vertical(
                MarkdownViewer(self.help_content, id="help-content"),
                Horizontal(
                    Button(get_global_i18n().t("help.back"), id="back-btn"),
                    id="help-controls"
                ),
                # 快捷键状态栏
                Horizontal(
                    Label(f"ESC: {get_global_i18n().t('common.back')}", id="shortcut-esc"),
                    id="shortcuts-bar"
                ),
                id="help-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        from src.ui.styles.style_manager import apply_style_isolation
        apply_style_isolation(self)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "back-btn":
            self.app.pop_screen()
    
    def on_key(self, event) -> None:
        """
        处理键盘事件
        
        Args:
            event: 键盘事件
        """
        if event.key == "escape":
            self.app.pop_screen()
            event.prevent_default()