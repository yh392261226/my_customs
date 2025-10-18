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
        """组合对话框UI：直接产出完整结构，避免挂载期再动态插入造成样式错乱"""
        self.logger.info(f"PasswordDialog.compose for file: {self.file_path}")
        with Vertical(id="password-dialog"):
            # 标题与文件名
            yield Label(get_global_i18n().t("password_dialog.title"), id="password-title", classes="section-title")
            yield Label(os.path.basename(self.file_path), id="password-filename")
            # 密码输入（允许空密码）
            yield Input(placeholder=get_global_i18n().t("password_dialog.placeholder"), password=True, id="password-input")
            # 按钮行
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
        """挂载时设置模态状态与焦点"""
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
            input_widget = self.query_one("#password-input", Input)
            input_widget.focus()
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

    @staticmethod
    def show(app, file_path: str, callback=None) -> None:
        """
        通过 App 上下文安全显示密码弹窗。
        总是保证在 UI 线程执行 push_screen，避免 active_app LookupError。
        使用示例：
            PasswordDialog.show(self.app, file_path, callback=lambda pwd: ...)
        """
        logger = get_logger(__name__)
        try:
            # 定义实际推屏操作：在 UI 线程内构造并 push
            def _push():
                try:
                    dialog = PasswordDialog(file_path)
                    def _do_push():
                        try:
                            if callback is not None:
                                app.push_screen(dialog, callback=callback)
                            else:
                                app.push_screen(dialog)
                        except Exception as e2_inner:
                            logger.error(f"PasswordDialog.show _do_push failed: {e2_inner}")
                    # 将实际 push 放到下一帧渲染周期中执行，确保 active_app 已就绪
                    try:
                        if hasattr(app, "call_after_refresh") and callable(getattr(app, "call_after_refresh")):
                            app.call_after_refresh(_do_push)  # type: ignore[attr-defined]
                        else:
                            _do_push()
                    except Exception as e_after:
                        logger.error(f"PasswordDialog.show call_after_refresh failed: {e_after}")
                except Exception as e2:
                    logger.error(f"PasswordDialog.show push preparation failed: {e2}")
            # 优先使用应用提供的 UI 调度方法
            try:
                if hasattr(app, "schedule_on_ui") and callable(getattr(app, "schedule_on_ui")):
                    app.schedule_on_ui(_push)  # type: ignore[attr-defined]
                    return
            except Exception as e_sched:
                logger.debug(f"PasswordDialog.show schedule_on_ui failed: {e_sched}")
            try:
                if hasattr(app, "call_from_thread") and callable(getattr(app, "call_from_thread")):
                    app.call_from_thread(_push)
                    return
            except Exception as e_call:
                logger.debug(f"PasswordDialog.show call_from_thread failed: {e_call}")
            # 兜底：改走消息总线，让主线程处理显示，避免直接 push
            try:
                from src.ui.messages import RequestPasswordMessage  # 延迟导入以避免循环
                msg = RequestPasswordMessage(file_path, max_attempts=3, future=None)
                if hasattr(app, "post_message_from_thread") and callable(getattr(app, "post_message_from_thread")):
                    app.post_message_from_thread(msg)
                elif hasattr(app, "post_message") and callable(getattr(app, "post_message")):
                    app.post_message(msg)
                else:
                    raise RuntimeError("App message posting API unavailable")
            except Exception as e_msg:
                logger.error(f"PasswordDialog.show fallback via message failed: {e_msg}")
        except Exception as e:
            # 更明确的错误提示，帮助定位跨线程或上下文问题
            logger.error(f"PasswordDialog.show failed: {e}")
