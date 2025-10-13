"""
启动锁屏（密码输入）屏幕
"""

from typing import Optional, ClassVar
from datetime import datetime
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button, Digits
from textual.containers import Vertical, Horizontal
from textual.timer import Timer
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation
from src.utils.logger import get_logger

logger = get_logger(__name__)

class LockScreen(ModalScreen[bool]):
    """启动时的密码锁屏：全屏、不可取消，密码比对成功后进入应用"""

    CSS_PATH = "../styles/lock_screen_overrides.tcss"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("enter", "on_submit", "确认验证密码"),
        ("escape", "on_exit", "退出"),
    ]

    def __init__(self, expected_password: str) -> None:
        super().__init__()
        self.expected_password = expected_password or ""
        self._clock_timer: Optional[Timer] = None

    def on_mount(self) -> None:
        # 应用通用样式隔离
        try:
            apply_universal_style_isolation(self)
        except Exception:
            pass
        # 聚焦输入框
        try:
            self.query_one("#lock-password-input", Input).focus()
        except Exception:
            pass

        self.update_clock()
        try:
            self._clock_timer = self.set_interval(1.0, self.update_clock)
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        i18n = get_global_i18n()
        title = i18n.t("lock_screen.title")
        placeholder = i18n.t("lock_screen.placeholder")
        confirm_text = i18n.t("common.ok")

        with Vertical(id="lock-screen-container"):
            # 时钟区域（顶部，Digits + Label 备用）
            with Horizontal(id="clock-container"):
                try:
                    now_str = datetime.now().strftime("%H:%M:%S")
                except Exception:
                    now_str = "--:--:--"
                # 优先使用 Digits
                yield Digits(now_str, id="lock-clock")
                # 备用 Label（Digits 不可用时显示）
                yield Label(now_str, id="lock-clock-fallback")
            
            # 密码输入区域（横排）
            with Horizontal(id="password-container"):
                yield Input(password=True, id="lock-password-input", placeholder=placeholder)
                yield Button(confirm_text, id="lock-submit-btn", variant="primary")
                yield Button(i18n.t("common.cancel") if i18n else "取消", id="lock-cancel-btn", variant="error")

    def update_clock(self) -> None:
        """每秒更新时钟显示：优先 Digits，失败则更新备用 Label"""
        now = datetime.now().strftime("%H:%M:%S")
        # 先尝试更新 Digits
        try:
            clk = self.query_one("#lock-clock", Digits)
            clk.update(now)
            return
        except Exception:
            ...
        # 如果 Digits 不可用，更新 Label 备用
        try:
            lbl = self.query_one("#lock-clock-fallback", Label)
            lbl.update(now)
        except Exception:
            ...

    def _try_submit(self) -> None:
        try:
            inp = self.query_one("#lock-password-input", Input)
            entered = inp.value or ""
            if entered == self.expected_password:
                self.dismiss(True)
            else:
                try:
                    self.app.notify(i18n.t("lock_screen.wrong_password"), severity="error")
                except Exception:
                    logger.info("密码错误")
                # 不关闭屏幕，允许重试
        except Exception as e:
            logger.error(f"LockScreen submit failed: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "lock-submit-btn":
            self._try_submit()
        elif event.button.id == "lock-cancel-btn":
            self.app.exit() # 退出阅读器

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "lock-password-input":
            self._try_submit()

    def action_on_submit(self) -> None:
        self._try_submit()
    
    def action_on_exit(self) -> None:
        self.app.exit()