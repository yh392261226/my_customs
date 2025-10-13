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
# 移除样式隔离以避免潜在的输入/事件被覆盖

class PasswordDialog(ModalScreen[Optional[str]]):

    """密码输入对话框"""
    CSS_PATH = '../styles/password_dialog_overrides.tcss'

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
            try:
                setattr(self.app, "_modal_active", False)
            except Exception:
                pass
            self.dismiss(None)
        elif event.button.id == "submit-btn":
            password_input = self.query_one("#password-input", Input)
            password = password_input.value
            self.logger.info(f"PasswordDialog.submit clicked, has_password={bool(password)}")
            # 允许空密码提交，因为有些PDF可能使用空密码
            self.attempts += 1
            try:
                setattr(self.app, "_modal_active", False)
            except Exception:
                pass
            # 关闭对话框并返回密码（允许空字符串）
            self.dismiss(password)
    
    def on_mount(self) -> None:
        """挂载时应用样式并设置焦点"""
        self.logger.info("PasswordDialog.on_mount")
        # 标记模态弹窗激活，供外部抑制动画/后台刷新
        try:
            setattr(self.app, "_modal_active", True)
        except Exception:
            pass
        # 设置 tooltip 显示完整路径（如支持）
        try:
            filename_label = self.query_one("#password-filename", Label)
            setattr(filename_label, "tooltip", self.file_path)
        except Exception as e:
            self.logger.warning(f"PasswordDialog.set_tooltip failed: {e}")
        # 聚焦输入框，确保键盘输入有效
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
            # 关闭对话框并返回密码（允许空字符串）
            self.dismiss(password)

    def on_key(self, event) -> None:
        """显式处理键盘事件，确保弹窗期间可交互"""
        try:
            key = getattr(event, "key", "")
            self.logger.info(f"PasswordDialog.on_key: {key}")
            if key in ("enter", "return"):
                password_input = self.query_one("#password-input", Input)
                try:
                    setattr(self.app, "_modal_active", False)
                except Exception:
                    pass
                self.dismiss(password_input.value)
            elif key in ("escape", "ctrl+c"):
                try:
                    setattr(self.app, "_modal_active", False)
                except Exception:
                    pass
                self.dismiss(None)
        except Exception as e:
            self.logger.warning(f"PasswordDialog.on_key failed: {e}")
