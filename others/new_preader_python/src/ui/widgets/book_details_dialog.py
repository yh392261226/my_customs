"""可复用的书籍详情弹窗组件（widgets）。

本组件只负责“展示一组 (标签, 值) 详情”，与具体业务数据（书库 Book / 爬取记录 dict）
完全解耦：调用方自行构建 ``details`` 列表后传入即可，因此书库页面与爬取管理页面
可复用同一份代码，避免重复实现。

用法示例
--------
    from src.ui.widgets.book_details_dialog import BookDetailsDialog

    details = [
        (get_global_i18n().t("common.book_name"), book.title),
        (get_global_i18n().t("common.author"), book.author),
        (get_global_i18n().t("book_details.source"), source),
        ...
    ]
    self.app.push_screen(
        BookDetailsDialog(
            title=get_global_i18n().t("book_details.title"),
            details=details,
            theme_manager=self.theme_manager,
        )
    )

快捷键
------
* ``escape`` / ``q``：关闭弹窗
* ``i``：关闭弹窗（与书库/爬取页的 “i 查看详情” 形成开关；在主页面按 i 打开，
  在弹窗内按 i 关闭）
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple

from textual.screen import ModalScreen
from textual.containers import Container, VerticalScroll, Horizontal
from textual.widgets import Static, Button, Header, Footer, RichLog
from textual.app import ComposeResult
from textual import on

from rich.text import Text

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager


class BookDetailsDialog(ModalScreen):
    """可复用的书籍详情弹窗。"""

    DEFAULT_CSS = """
    BookDetailsDialog {
        align: center middle;
    }

    #book-details-window {
        width: 60%;
        height: auto;
        max-height: 80%;
        min-width: 40;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    #book-details-title {
        width: 100%;
        height: 1;
        background: $accent;
        color: $text;
        text-style: bold;
        content-align: center middle;
        margin-bottom: 1;
    }

    #book-details-body {
        height: auto;
        max-height: 1fr;
        background: $background;
        border: round $panel;
        padding: 1;
    }

    #book-details-info {
        width: 100%;
        height: auto;
    }

    #book-details-content {
        height: 12;
        margin-top: 1;
        border: round $border;
        background: $background;
        padding: 0 1;
    }

    #book-details-buttons {
        height: 3;
        align: center bottom;
        margin-top: 1;
    }
    """

    # 注意：BINDINGS 在类定义时即被求值，而本模块可能在 i18n 初始化之前被导入
    # （app.py 顶层导入 src.ui.widgets）。因此此处描述使用字面量，避免触发
    # get_global_i18n() 导致“未初始化”异常。需要多语言描述时可在 on_mount 动态修改。
    BINDINGS: list = [
        ("escape", "close", "关闭"),
        ("q", "close", "关闭"),
        # 与书库/爬取页 “i 查看详情” 对应：弹窗内按 i 关闭
        ("i", "close", "关闭(I)"),
    ]

    def __init__(
        self,
        title: str,
        details: List[Tuple[str, Any]],
        content: Optional[str] = None,
        theme_manager: Optional[ThemeManager] = None,
    ) -> None:
        """初始化详情弹窗。

        Args:
            title: 弹窗标题（如 “书籍详情”）。
            details: 详情条目列表，每个元素为 (标签, 值)。值会自动转为字符串。
            content: 可选的正文预览内容（如书籍片段），不传则只展示元数据。
            theme_manager: 可选的主题管理器，用于给弹窗应用当前主题。
        """
        super().__init__()
        self.dialog_title = title
        self.details: List[Tuple[str, Any]] = details
        self.content = content
        self.theme_manager = theme_manager

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="book-details-window"):
            yield Static(self.dialog_title, id="book-details-title", classes="book-details-title")
            with VerticalScroll(id="book-details-body"):
                yield Static(id="book-details-info", classes="book-details-info")
                if self.content:
                    yield RichLog(
                        id="book-details-content",
                        classes="book-details-content",
                        wrap=True,
                        markup=False,
                        auto_scroll=False,
                    )
            yield Horizontal(
                Button(
                    get_global_i18n().t("common.close"),
                    id="book-details-close-btn",
                    variant="primary",
                ),
                id="book-details-buttons",
                classes="btn-row",
            )
        yield Footer()

    def on_mount(self) -> None:
        if self.theme_manager is not None:
            try:
                self.theme_manager.apply_theme_to_screen(self)
            except Exception:
                pass

        self.query_one("#book-details-info", Static).update(self._build_info_text())

        if self.content:
            log = self.query_one("#book-details-content", RichLog)
            try:
                log.write(Text(self.content))
                log.scroll_home(animate=False)
            except Exception:
                pass

        try:
            self.query_one("#book-details-close-btn", Button).focus()
        except Exception:
            pass

    def _build_info_text(self) -> Text:
        """将 details 列表渲染为带样式的富文本（避免 Markup 注入风险）。"""
        text = Text()
        for label, value in self.details:
            text.append(f"{label}：", style="bold cyan")
            text.append(f"{value}\n")
        return text

    @property
    def has_content(self) -> bool:
        return bool(self.content)

    @on(Button.Pressed, "#book-details-close-btn")
    def _on_close_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss()

    def action_close(self) -> None:
        """关闭弹窗（escape / q / i 共用）。"""
        self.dismiss()
