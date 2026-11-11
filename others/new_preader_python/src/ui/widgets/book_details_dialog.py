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

结构
----
与书籍预览弹窗一致：屏幕级 ``Header`` / ``Footer``（dock 到上下边缘），
中间是居中的详情窗口；窗口内保留自定义标题条。快捷键由 ``Footer`` 统一展示。

快捷键
------
* ``escape`` / ``q``：关闭弹窗
* ``i``：关闭弹窗（与书库/爬取页的 “i 查看详情” 形成开关；在主页面按 i 打开，
  在弹窗内按 i 关闭）
* ``F``：查看文件（在文件管理器中定位）
* ``v``：打开预览弹窗
"""
from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple, Callable

from textual.screen import ModalScreen
from textual.containers import Container, VerticalScroll, Horizontal
from textual.widgets import Static, Button, RichLog, Header, Footer
from textual.app import ComposeResult
from textual import on

from rich.text import Text

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager


def _binding_desc(key: str, fallback: str) -> str:
    """BINDINGS 在类定义时求值；i18n 若尚未初始化则回退到字面量文案。"""
    try:
        return get_global_i18n().t(key)
    except Exception:
        return fallback


class BookDetailsDialog(ModalScreen[None]):
    """可复用的书籍详情弹窗。"""

    # 样式统一放在 CSS_PATH（与 BookPreviewDialog 一致）：app 级 common.tcss 的
    # Container / ScrollableContainer 规则会覆盖 Screen 的 DEFAULT_CSS，导致
    # 窗口变成全屏、Footer 被撑满内容区，只有 CSS_PATH 中的规则能稳定生效。
    CSS_PATH = "../styles/book_details_dialog_overrides.tcss"

    # BINDINGS 在类定义时即被求值，本模块可能在 i18n 初始化之前被导入，
    # 故通过 _binding_desc 取文案并带字面量回退；与预览弹窗一致使用多语言描述，
    # 便于 Footer 在不同语言环境下显示统一风格。
    BINDINGS: list[tuple[str, str, str]] = [
        ("escape", "close", _binding_desc("common.close", "关闭")),
        ("q", "close", _binding_desc("common.close", "关闭")),
        # 与书库/爬取页 “i 查看详情” 对应：弹窗内按 i 关闭
        ("i", "close", _binding_desc("common.close", "关闭")),
        # 与书库/爬取管理页保持一致：F 查看文件、v 预览
        ("F", "view_file", _binding_desc("common.view_file", "查看文件")),
        ("v", "preview", _binding_desc("common.preview", "预览")),
    ]

    def __init__(
        self,
        title: str,
        details: List[Tuple[str, Any]],
        content: Optional[str] = None,
        theme_manager: Optional[ThemeManager] = None,
        file_path: Optional[str] = None,
        preview_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        """初始化详情弹窗。

        Args:
            title: 弹窗标题（如 “书籍详情”）。
            details: 详情条目列表，每个元素为 (标签, 值)。值会自动转为字符串。
            content: 可选的正文预览内容（如书籍片段），不传则只展示元数据。
            theme_manager: 可选的主题管理器，用于给弹窗应用当前主题。
            file_path: 可选的文件路径，传入后显示「查看文件」按钮（在文件管理器中定位）。
            preview_factory: 可选的预览弹窗工厂（延迟构建），传入后显示「预览」按钮。
        """
        super().__init__()
        self.dialog_title = title
        self.details: List[Tuple[str, Any]] = details
        self.content = content
        self.theme_manager = theme_manager
        self.file_path = file_path
        self.preview_factory = preview_factory

    def compose(self) -> ComposeResult:
        # 与 BookPreviewDialog 及项目内多数弹窗一致：屏幕级 Header / Footer，
        # Header 展示应用标题与时钟，Footer 统一展示本弹窗 BINDINGS 快捷键。
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
                    get_global_i18n().t("common.view_file"),
                    id="book-details-view-file-btn",
                    variant="default",
                ),
                Button(
                    get_global_i18n().t("common.preview"),
                    id="book-details-preview-btn",
                    variant="default",
                ),
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

        # 按终端实际行数设置窗口高度（屏幕的 70%），并为按钮预留固定空间，
        # 避免依赖 CSS 的百分比/fr 高度在滚动容器上不生效而导致按钮被裁掉。
        self._apply_sizing()

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

        # 无文件路径时禁用「查看文件」按钮
        if not self.file_path:
            try:
                self.query_one("#book-details-view-file-btn", Button).disabled = True
            except Exception:
                pass

        # 未提供预览弹窗工厂时禁用「预览」按钮
        if self.preview_factory is None:
            try:
                self.query_one("#book-details-preview-btn", Button).disabled = True
            except Exception:
                pass

    def on_resize(self, event) -> None:
        """终端尺寸变化时重新计算高度。"""
        self._apply_sizing()

    def _apply_sizing(self) -> None:
        """将窗口高度固定为屏幕的 70%，并把正文区限制为剩余高度。

        使用终端实际单元格数（而非 CSS 百分比/fr），确保所有环境下按钮都
        始终保留在窗口底部、不会被滚动容器撑出可视区。
        """
        try:
            window = self.query_one("#book-details-window")
            screen_height = self.app.size.height
            # 窗口总高度（含边框与内边距）= 屏幕的 70%；
            # app 级样式给 Screen 加了 round 边框（上下各 1 行），
            # 再加 Header / Footer 各 dock 占 1 行，共需预留 4 行。
            total = max(15, int(screen_height * 0.7))
            total = min(total, max(10, screen_height - 4))
            window.styles.height = total
            # 窗口内除正文外固定占用的行数（styles.height 含边框与内边距）：
            #   窗口上边框 1 + 窗口上内边距 1 + 标题 1 + 标题下边距 1
            # + 按钮区上边距 1 + 按钮区 3 + 窗口下内边距 1 + 窗口下边框 1 = 10
            body_height = total - 10
            body_height = max(3, body_height)
            self.query_one("#book-details-body").styles.height = body_height
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

    @on(Button.Pressed, "#book-details-view-file-btn")
    def _on_view_file_pressed(self, event: Button.Pressed) -> None:
        """「查看文件」按钮：在系统文件管理器中定位文件"""
        event.stop()
        self._view_file_location()

    def _view_file_location(self) -> None:
        """查看文件（按钮与 F 快捷键共用）。"""
        try:
            from src.utils.file_helpers import reveal_in_file_manager

            if not self.file_path or not os.path.exists(self.file_path):
                self.notify(get_global_i18n().t("common.file_not_exist"), severity="warning")
                return
            if reveal_in_file_manager(self.file_path):
                self.notify(get_global_i18n().t("bookshelf.opened_in_file_explorer"), severity="information")
            else:
                self.notify(get_global_i18n().t("bookshelf.view_file_failed"), severity="error")
        except Exception as e:
            self.notify(f"{get_global_i18n().t('common.action_failed')}: {e}", severity="error")

    @on(Button.Pressed, "#book-details-preview-btn")
    def _on_preview_pressed(self, event: Button.Pressed) -> None:
        """「预览」按钮：用预览弹窗替换当前详情弹窗（不叠加屏幕栈）。"""
        event.stop()
        self._open_preview_dialog()

    def _open_preview_dialog(self) -> None:
        """打开预览（按钮与 v 快捷键共用）。"""
        try:
            if self.preview_factory is None:
                return
            preview_screen = self.preview_factory()
            if preview_screen is None:
                return
            # switch_screen 会关闭当前栈顶弹窗并换上新的，保证「详情 ↔ 预览」
            # 反复跳转时屏幕上始终只有一个弹窗，不会堆叠出多层。
            switch = getattr(self.app, "switch_screen", None)
            if callable(switch):
                switch(preview_screen)
            else:
                # 兼容旧版 Textual（无 switch_screen）：先关闭自身再压入新弹窗
                self.dismiss()
                self.app.push_screen(preview_screen)
        except Exception as e:
            self.notify(f"{get_global_i18n().t('common.action_failed')}: {e}", severity="error")

    def action_close(self) -> None:
        """关闭弹窗（escape / q / i 共用）。"""
        self.dismiss()

    def action_view_file(self) -> None:
        """F 键 —— 查看文件（在文件管理器中定位）。"""
        self._view_file_location()

    def action_preview(self) -> None:
        """v 键 —— 打开预览弹窗（替换当前详情弹窗）。"""
        self._open_preview_dialog()
