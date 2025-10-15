"""
备注对话框
用于编辑书籍网站备注
"""

from typing import Optional
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Label, TextArea
from textual.app import ComposeResult
from textual import events

from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.locales.i18n_manager import get_global_i18n, t

logger = get_logger(__name__)

class NoteDialog(ModalScreen[Optional[str]]):
    """备注对话框"""
    CSS_PATH = ["../styles/utilities.tcss", '../styles/note_dialog_overrides.tcss']

    # 使用 BINDINGS 替代 on_key（Esc 取消，Ctrl+S 保存）
    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
        ("ctrl+s", "save", get_global_i18n().t('common.save')),
    ]

    
    def __init__(self, theme_manager: ThemeManager, site_name: str, initial_note: str = ""):
        """
        初始化备注对话框
        
        Args:
            theme_manager: 主题管理器
            site_name: 网站名称
            initial_note: 初始备注内容
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.site_name = site_name
        self.initial_note = initial_note
        self.title = f"{get_global_i18n().t('note.title')} - {site_name}"
    
    def compose(self) -> ComposeResult:
        """
        组合备注对话框界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Vertical(
                # 标题
                Label(f"{get_global_i18n().t('note.title')} - {self.site_name}", id="note-title", classes="section-title"),
                
                # 文本域
                TextArea(
                    self.initial_note,
                    id="note-textarea",
                    language="markdown",
                    show_line_numbers=True,
                    tab_behavior="indent",
                    placeholder=get_global_i18n().t('note.enter_note'),
                    classes="textarea-std"
                ),
                
                # 按钮区域
                Horizontal(
                    Button(get_global_i18n().t('note.save'), id="save-btn", variant="primary"),
                    Button(get_global_i18n().t('note.clear'), id="clear-btn"),
                    Button(get_global_i18n().t('note.cancel'), id="cancel-btn"),
                    id="note-buttons", classes="btn-row"
                ),
                
                id="note-container"
            ),
            id="note-screen-container"
        )
    
    def on_mount(self) -> None:
        """对话框挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 设置焦点到文本域
        textarea = self.query_one("#note-textarea", TextArea)
        if textarea:
            self.set_focus(textarea)
    
    # Actions for BINDINGS
    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_save(self) -> None:
        textarea = self.query_one("#note-textarea", TextArea)
        note_content = textarea.text
        self.dismiss(note_content)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        textarea = self.query_one("#note-textarea", TextArea)
        
        if event.button.id == "save-btn":
            # 保存备注
            note_content = textarea.text
            self.dismiss(note_content)
        elif event.button.id == "clear-btn":
            # 清除备注
            textarea.text = ""
        elif event.button.id == "cancel-btn":
            # 取消，返回None
            self.dismiss(None)
    
    def on_key(self, event: events.Key) -> None:
        """已由 BINDINGS 处理，避免重复触发"""
        pass