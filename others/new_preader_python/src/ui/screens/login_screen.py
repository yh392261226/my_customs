"""
登录屏幕（伪用户系统，采用 LockScreen 风格的布局与样式）
"""
from typing import Optional, Dict, Any
from datetime import datetime

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Label, Input, Button, Digits
from textual.containers import Vertical, Horizontal
from textual.timer import Timer

from src.themes.theme_manager import ThemeManager
from src.core.database_manager import DatabaseManager
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation
from src.utils.logger import get_logger
from src.utils.multi_user_manager import multi_user_manager

logger = get_logger(__name__)


class LoginScreen(Screen[Optional[Dict[str, Any]]]):
    """
    采用 lock_screen 的更美观布局与样式，但保留登录逻辑（用户名/密码，dismiss 返回用户信息）
    """
    # 使用与 LockScreen 相同的样式文件以获得一致的观感
    CSS_PATH = "../styles/login_screen_overrides.tcss"

    def __init__(self, theme_manager: ThemeManager, db_manager: DatabaseManager):
        self.db_manager = db_manager  # 数据库管理器
        super().__init__()
        self.theme_manager = theme_manager
        self.db_manager = db_manager
        self._username = ""
        self._password = ""
        self._clock_timer: Optional[Timer] = None

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            return self.db_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许

    def on_mount(self) -> None:
        # 检查多用户设置，如果禁用则自动跳过登录
        if not multi_user_manager.should_show_login():
            # 多用户功能禁用，直接返回超级管理员信息
            super_admin_info = {
                "id": 0,
                "username": "super_admin",
                "role": "super_admin",
                "permissions": ["read", "write", "delete", "manage_users", "manage_books", "manage_settings"]
            }
            self.dismiss(super_admin_info)
            return

        # 统一样式隔离（与 LockScreen 保持一致，避免外层干扰）
        try:
            apply_universal_style_isolation(self)
        except Exception:
            pass

        # 应用主题（保留原有行为）
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass

        # 聚焦用户名输入框更符合登录流程
        try:
            self.query_one("#username-input", Input).focus()
        except Exception:
            pass

        # 初始化并启动时钟
        self._update_clock_once()
        try:
            self._clock_timer = self.set_interval(1.0, self._update_clock_once)
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        t = get_global_i18n()
        title = t.t("login.title")
        username_ph = t.t("login.username")
        password_ph = t.t("login.password")
        ok_text = t.t("login.login")
        guest_text = t.t("login.guest")

        with Vertical(id="lock-screen-container"):
            # 登录表单区域：标题 + 用户名 + 密码 + 操作按钮
            yield Label(title, id="login-title")
            # 顶部时钟区域（复用 LockScreen 的结构与 ID）
            with Horizontal(id="clock-container"):
                try:
                    now_str = datetime.now().strftime("%H:%M:%S")
                except Exception:
                    now_str = "--:--:--"
                yield Digits(now_str, id="lock-clock")
                yield Label(now_str, id="lock-clock-fallback")

            # 用户名输入（单独一行）
            # with Horizontal(id="username-container"):
            #     yield Input(placeholder=username_ph, id="username-input")

            # 密码与操作按钮横排（尽量贴合 LockScreen 的布局风格）
            with Horizontal(id="password-container"):
                yield Input(placeholder=username_ph, id="username-input")
                yield Input(placeholder=password_ph, password=True, id="password-input")
                yield Button(ok_text, id="login-btn", variant="primary")
                yield Button(guest_text, id="guest-btn")

    def _update_clock_once(self) -> None:
        """每秒更新时间显示：优先 Digits，不可用时更新 Label 备用"""
        now = datetime.now().strftime("%H:%M:%S")
        # 优先 Digits
        try:
            clk = self.query_one("#lock-clock", Digits)
            clk.update(now)
            return
        except Exception:
            ...
        # 备用 Label
        try:
            lbl = self.query_one("#lock-clock-fallback", Label)
            lbl.update(now)
        except Exception:
            ...

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-btn":
            try:
                user = self.db_manager.authenticate(self._username.strip(), self._password)
                if user:
                    self.dismiss(user)
                else:
                    self.notify("登录失败：用户名或密码错误", severity="error")
            except Exception as e:
                logger.error(f"登录失败: {e}")
                self.notify("登录失败", severity="error")
        elif event.button.id == "guest-btn":
            # 访客进入，返回 None
            self.dismiss(None)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "username-input":
            self._username = event.value or ""
        elif event.input.id == "password-input":
            self._password = event.value or ""

    def on_key(self, event) -> None:
        """
        处理键盘事件
        
        Args:
            event: 键盘事件
        """
        if event.key == "escape":
            if not self._has_permission("login.escape"):
                self.notify("无权限退出登录", severity="error")
                event.stop()
                return
            self.app.exit()  