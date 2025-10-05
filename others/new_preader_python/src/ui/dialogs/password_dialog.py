"""
密码输入对话框
"""

import os
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.utils.logger import get_logger
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class PasswordDialog(ModalScreen[Optional[str]]):

    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
    """密码输入对话框"""
    
    CSS_PATH = "../styles/password_dialog_overrides.tcss"
    logger = get_logger(__name__)
    
    def __init__(self, file_path: str, max_attempts: int = 3) -> None:
        super().__init__()
        self.file_path = file_path
        self.max_attempts = max_attempts
        self.attempts = 0
    
    def compose(self) -> ComposeResult:
        """组合对话框UI"""
        self.logger.info(f"PasswordDialog.compose for file: {self.file_path}")
        with Vertical(id="password-dialog"):
            yield Label(get_global_i18n().t("password_dialog.title"), id="password-title", classes="section-title")
            yield Label(os.path.basename(self.file_path), id="password-filename")
            yield Input(placeholder=get_global_i18n().t("password_dialog.placeholder"), password=True, id="password-input")
            with Horizontal(id="password-buttons", classes="btn-row"):
                yield Button(f"← {get_global_i18n().t('common.cancel')}", id="cancel-btn", variant="primary")
                yield Button(get_global_i18n().t("common.ok"), id="submit-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击事件"""
        self.logger.info(f"PasswordDialog.on_button_pressed: {event.button.id}")
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "submit-btn":
            password_input = self.query_one("#password-input", Input)
            password = password_input.value
            self.logger.info(f"PasswordDialog.submit clicked, has_password={bool(password)}")
            # 允许空密码提交，因为有些PDF可能使用空密码
            self.attempts += 1
            # 先通知刷新，再关闭对话框
            self._notify_content_refresh()
            self.dismiss(password)
    
    def on_mount(self) -> None:
        """挂载时设置焦点"""
        self.logger.info("PasswordDialog.on_mount")
        # 设置 tooltip 显示完整路径（如支持）
        try:
            filename_label = self.query_one("#password-filename", Label)
            # Textual 支持在运行时设置 tooltip
            setattr(filename_label, "tooltip", self.file_path)
        except Exception as e:
            self.logger.warning(f"PasswordDialog.set_tooltip failed: {e}")
        try:
            self.query_one("#password-input", Input).focus()
            self.logger.info("PasswordDialog.focus set to #password-input")
        except Exception as e:
            self.logger.error(f"PasswordDialog.focus failed: {e}")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理输入框回车提交事件"""
        self.logger.info(f"PasswordDialog.on_input_submitted: {event.input.id}")
        if event.input.id == "password-input":
            password = event.input.value
            self.logger.info(f"PasswordDialog.enter submitted, has_password={bool(password)}")
            # 允许空密码提交，因为有些PDF可能使用空密码
            self.attempts += 1
            # 先通知刷新，再关闭对话框
            self._notify_content_refresh()
            self.dismiss(password)

    def _notify_content_refresh(self) -> None:
        """通知终端阅读器重新加载内容"""
        try:
            from textual.app import App
            app = App.get_app()
            
            # 清除Book对象的缓存，强制重新解析
            if hasattr(app, 'screen') and hasattr(app.screen, 'book'):
                app.screen.book._content_loaded = False
                app.screen.book._content = None
            
            # 使用简单直接的方法：发送消息通知屏幕刷新
            if hasattr(app, 'screen') and hasattr(app.screen, '_load_book_content_async'):
                # 使用call_after_refresh确保在UI线程执行
                if hasattr(app, 'call_after_refresh'):
                    app.call_after_refresh(app.screen._load_book_content_async)
                else:
                    # 备用方案：直接调用
                    app.screen._load_book_content_async()
        except Exception as e:
            self.logger.warning(get_global_i18n().t('password_dialog.notify_refresh_failed', error=str(e)))