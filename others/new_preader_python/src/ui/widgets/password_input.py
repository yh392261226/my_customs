"""
密码输入框辅助工具（不再使用复合容器控件）。

设计要点：
- 密码字段就是一个带 ``id`` 的普通 ``Input``（password 类型），由页面负责布局/宽度。
- 在它**后面**紧跟一个切换按钮（同处一行），按钮 ``id`` 约定为 ``<input_id>__toggle``。
- 点击按钮时，按钮按约定找到对应 Input 并切换其 ``password`` 显隐，同步图标（🫣 / 👁）。
- 宽度、间距、对齐等全部由各页面 CSS 通过 ``#<input_id>`` 与 ``.password-toggle`` 控制，
  组件本身不强制任何布局，避免之前“跨页面样式互相覆盖”的问题。

用法::

    # 横向行内（登录/锁屏/代理/用户管理等已有 Horizontal 的场景）
    with Horizontal():
        yield password_input_field("password-input", placeholder="密码")
        yield password_toggle_button("password-input")

    # 纵向布局中需要独占一整行时（设置中心等）
    yield password_field("baidu-app-id-input", value=...)
"""

from typing import Optional

from textual.containers import Horizontal
from textual.widgets import Input, Button

TOGGLE_SUFFIX = "__toggle"
ICON_HIDDEN = "🫣"
ICON_SHOWN = "👁"


class PasswordToggleButton(Button):
    """密码显隐切换按钮。

    约定：``id`` 必须为 ``<input_id>__toggle``，且与对应的密码 ``Input`` 处于同一行、
    紧随其后。点击后切换该 ``Input`` 的 ``password`` 显隐。
    """

    def on_button_pressed(self, event: "Button.Pressed") -> None:
        if not self.id or not self.id.endswith(TOGGLE_SUFFIX):
            return
        input_id = self.id[: -len(TOGGLE_SUFFIX)]
        try:
            inp = self.screen.query_one(f"#{input_id}", Input)
        except Exception:
            return
        inp.password = not inp.password
        self.label = ICON_HIDDEN if inp.password else ICON_SHOWN

    @staticmethod
    def toggle_id(input_id: str) -> str:
        return f"{input_id}{TOGGLE_SUFFIX}"


def password_input_field(
    input_id: str,
    placeholder: str = "",
    value: str = "",
    *,
    classes: str = "pw-input",
) -> Input:
    """返回一个 password 类型的 ``Input``（带指定 ``id``，并附加 ``pw-input`` 类）。

    随后用 :func:`password_toggle_button` 在它后面追加切换按钮（同一行）。
    ``pw-input`` 类用于在各页面 CSS 中统一把密码框的纵向 margin 归零，
    以保证切换按钮与输入框严格同行（详见各页面 overrides）。
    """
    return Input(
        id=input_id,
        placeholder=placeholder,
        value=value,
        password=True,
        classes=classes,
    )


def password_toggle_button(
    input_id: str,
    *,
    classes: str = "password-toggle",
) -> PasswordToggleButton:
    """返回与 ``password_input_field(input_id)`` 配套的切换按钮，应紧随其后放置。"""
    return PasswordToggleButton(
        ICON_HIDDEN,
        id=PasswordToggleButton.toggle_id(input_id),
        classes=classes,
        tooltip="显示或隐藏密码",
    )


def password_field(
    input_id: str,
    placeholder: str = "",
    value: str = "",
    *,
    classes: str = "pw-input",
    row_classes: str = "password-field-row",
) -> Horizontal:
    """返回包含“密码 Input + 切换按钮”的整行 ``Horizontal``。

    适用于纵向布局（如设置中心）中需要密码框独占一行的场景；
    横向行内已有 ``Horizontal`` 时，直接用 ``password_input_field`` + ``password_toggle_button`` 即可。
    """
    return Horizontal(
        password_input_field(input_id, placeholder, value, classes=classes),
        password_toggle_button(input_id),
        classes=row_classes,
    )
