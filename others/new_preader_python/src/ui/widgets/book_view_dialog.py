"""
统一的「书籍视图」组件：一个 widget 同时提供 查看详情 / 预览 / 查看文件。

背景
----
历史上这三项功能分散在多个文件：
* ``widgets/book_details_dialog.py``（详情）
* ``screens/crawler_management_screen.py`` 里的 ``BookPreviewDialog``（预览）
* ``utils/file_helpers.py`` 的 ``reveal_in_file_manager``（查看文件）
各页面还各自重复实现「读前 2000 字 → 组装 metadata → push 弹窗」，
详情与预览之间靠 ``switch_screen`` 互换，屏幕上一次只能显示其一。

现在统一为：
* 本文件：``BookViewDialog``（单一弹窗，内部切换详情 / 预览视图，内置
  「查看文件」「预览全部」），以及 ``BookDetailsDialog`` / ``BookPreviewDialog``
  两个向后兼容的轻量适配类（旧的构造签名继续可用）。
* ``src/ui/utils/book_view_utils.py``：数据组装、预览读取、打开弹窗、
  文件定位等全部共用逻辑，各页面只需一行调用。

统一后不再需要两个弹窗互相 switch_screen，也不会出现重复实现漂移。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, RichLog, Static

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _binding_desc(key: str, fallback: str) -> str:
    """BINDINGS 在类定义期求值，i18n 未初始化时回退到字面量文案。"""
    try:
        return get_global_i18n().t(key)
    except Exception:
        return fallback


@dataclass
class BookViewData:
    """统一视图数据（由 book_view_utils 构建，widget 只负责渲染）。"""

    title: str = ""
    details: List[Tuple[str, Any]] = field(default_factory=list)
    content: str = ""
    file_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    allow_preview: bool = True
    allow_full_preview: bool = True
    allow_view_file: bool = True


class BookViewDialog(ModalScreen[None]):
    """详情 / 预览 / 查看文件三合一弹窗。"""

    CSS_PATH = "../styles/book_view_dialog.tcss"

    BINDINGS: List[Tuple[str, str, str]] = [
        ("escape", "close", _binding_desc("common.close", "关闭")),
        ("q", "close", _binding_desc("common.close", "关闭")),
        ("i", "show_details", _binding_desc("book_details.view_details", "查看详情")),
        ("v", "show_preview", _binding_desc("common.preview", "预览")),
        ("V", "toggle_preview", _binding_desc("book_view.preview_full", "预览全部")),
        ("F", "view_file", _binding_desc("common.view_file", "查看文件")),
        ("j", "scroll_down", _binding_desc("common.scroll_down", "向下滚动")),
        ("k", "scroll_up", _binding_desc("common.scroll_up", "向上滚动")),
    ]

    def __init__(self, data: BookViewData,
                 theme_manager: Optional[ThemeManager] = None,
                 initial_view: str = "details") -> None:
        super().__init__()
        self.data = data
        self.theme_manager = theme_manager
        self.view_title = data.title or ""
        self.content = data.content or ""
        self.metadata = data.metadata or {}
        self.file_path = data.file_path or ""
        self.original_content = self.content
        self._is_full = False
        self._current_view = initial_view if initial_view in ("details", "preview") else "details"
        # 兼容属性（旧代码可能读取）
        self.title = data.title or ""
        self.details = data.details or []

    # ------------------------------------------------------------------ 布局

    def compose(self) -> ComposeResult:
        t = get_global_i18n().t
        yield Header()
        with Container(id="bv-window"):
            yield Static(self.view_title, id="bv-title")
            with Vertical(id="bv-body"):
                with VerticalScroll(id="bv-details-view"):
                    yield Static(id="bv-details-text", classes="bv-details-text")
                    if self.content:
                        yield RichLog(
                            id="bv-details-content", wrap=True, markup=False,
                            auto_scroll=False, classes="bv-details-content",
                        )
                with Horizontal(id="bv-preview-view"):
                    with VerticalScroll(id="bv-sidebar"):
                        yield Static(id="bv-info-text", classes="bv-info-text")
                    yield RichLog(
                        id="bv-preview-text", wrap=True, markup=False,
                        auto_scroll=False, classes="bv-preview-text",
                    )
            with Horizontal(id="bv-buttons", classes="btn-row"):
                yield Button(t("book_view.details_tab"), id="bv-details-btn")
                yield Button(t("book_view.preview_tab"), id="bv-preview-btn")
                yield Button(t("book_view.preview_full"), id="bv-full-btn")
                yield Button(t("book_view.view_file"), id="bv-view-file-btn")
                yield Button(t("common.close"), id="bv-close-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        if self.theme_manager is not None:
            try:
                self.theme_manager.apply_theme_to_screen(self)
            except Exception:
                pass

        self.query_one("#bv-details-text", Static).update(self._build_details_text())
        self.query_one("#bv-info-text", Static).update(self._build_info_text())
        if self.content:
            try:
                self.query_one("#bv-details-content", RichLog).write(Text(self.content))
            except Exception:
                pass
        self._render_preview(self.content, "book_view.truncated_note")
        self._set_view(self._current_view)
        try:
            self.query_one("#bv-close-btn", Button).focus()
        except Exception:
            pass
        self._apply_sizing()

    def on_resize(self, event) -> None:
        self._apply_sizing()

    def _apply_sizing(self) -> None:
        """按终端行数固定窗口尺寸，保证底部按钮始终可见。"""
        try:
            window = self.query_one("#bv-window")
            height = self.app.size.height
            total = max(18, int(height * 0.82))
            total = min(total, max(12, height - 4))
            window.styles.height = total
        except Exception:
            pass

    # ------------------------------------------------------------------ 渲染

    def _build_details_text(self) -> Text:
        text = Text()
        for label, value in self.details:
            text.append(f"{label}：", style="bold cyan")
            text.append(f"{value}\n")
        if not self.details:
            text.append(self.view_title or "-", style="bold")
            text.append("\n")
        return text

    @staticmethod
    def _human_size(value: Any) -> str:
        try:
            n = int(value)
        except (TypeError, ValueError):
            return "-"
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        if n < 1024 * 1024 * 1024:
            return f"{n / 1024 / 1024:.1f} MB"
        return f"{n / 1024 / 1024 / 1024:.2f} GB"

    def _build_info_text(self) -> Text:
        """预览视图左侧信息面板：自适应展示有值的字段。"""
        t = get_global_i18n().t
        meta = self.metadata
        text = Text()
        text.append(f"{t('book_view.preview_title')}\n", style="bold underline")
        text.append("\n")

        def field_line(label: str, value: Any, style: str = "default") -> None:
            if value in (None, "", 0, "0"):
                return
            text.append(f"{label}\n", style="dim")
            text.append(f"{value}\n\n", style=style)

        field_line(t("crawler.preview_field_title"), self.view_title or "-", "bold")
        field_line(t("crawler.preview_field_author"), meta.get("author"))
        field_line(t("crawler.preview_field_type"),
                   meta.get("book_type") or meta.get("format"))
        status = meta.get("status")
        if status == "success":
            field_line(t("crawler.preview_field_status"),
                       "✓ " + t("crawler.status_success"), "bold green")
        elif status == "failed":
            field_line(t("crawler.preview_field_status"),
                       "✗ " + t("crawler.status_failed"), "bold red")
        else:
            field_line(t("crawler.preview_field_status"), status)
        field_line(t("crawler.preview_field_chapters"), meta.get("chapter_count"))
        field_line(t("crawler.preview_field_last_chapter"), meta.get("last_chapter_title"))
        size = meta.get("size")
        if size:
            field_line(t("crawler.preview_field_size"), self._human_size(size))
        field_line(t("crawler.preview_field_tags"), meta.get("tags"))
        text.append(f"{t('crawler.preview_field_preview_chars')}\n", style="dim")
        text.append(f"{len(self.content)}\n\n")
        field_line(t("crawler.preview_field_novel_id"), meta.get("novel_id"))
        field_line(t("crawler.preview_field_crawl_time"), meta.get("crawl_time"))
        field_line(t("crawler.preview_field_path"),
                   meta.get("file_path") or meta.get("path") or self.file_path)
        return text

    def _render_preview(self, content: str, note_key: str) -> None:
        """把内容写入预览 RichLog，并刷新左侧信息面板。"""
        try:
            log = self.query_one("#bv-preview-text", RichLog)
            log.clear()
            log.border_title = self.view_title
            log.write(Text(content or ""))
            note = Text()
            note.append("\n\n" + "─" * 40 + "\n", style="dim")
            note.append(get_global_i18n().t(note_key), style="italic dim")
            log.write(note)
            log.scroll_home(animate=False)
        except Exception as e:
            logger.debug(f"渲染书籍预览失败: {e}")
        self.content = content or ""
        try:
            self.query_one("#bv-info-text", Static).update(self._build_info_text())
        except Exception:
            pass

    # ------------------------------------------------------------------ 视图

    def _set_view(self, view: str) -> None:
        self._current_view = view
        try:
            self.query_one("#bv-details-view").display = (view == "details")
            self.query_one("#bv-preview-view").display = (view == "preview")
        except Exception:
            pass
        try:
            self.query_one("#bv-title", Static).update(
                f"{self.view_title}  ·  "
                + get_global_i18n().t(
                    "book_view.details_tab" if view == "details" else "book_view.preview_tab"
                )
            )
        except Exception:
            pass
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        try:
            self.query_one("#bv-view-file-btn", Button).disabled = not (
                self.data.allow_view_file and self.file_path
            )
            self.query_one("#bv-preview-btn", Button).disabled = (
                not self.data.allow_preview or not self.content
            )
            self.query_one("#bv-full-btn", Button).disabled = not (
                self.data.allow_full_preview and self.file_path
                and os.path.isfile(self.file_path)
            )
        except Exception:
            pass

    def action_show_details(self) -> None:
        """i 键 —— 切到详情；详情视图下再按 i 关闭（与旧版开关一致）。"""
        if self._current_view == "details":
            self.dismiss()
        else:
            self._set_view("details")

    def action_show_preview(self) -> None:
        """v 键 —— 切到预览。"""
        if not self.data.allow_preview:
            return
        if not self.content:
            self.notify(get_global_i18n().t("book_view.no_preview"), severity="warning")
            return
        self._set_view("preview")

    def action_toggle_preview(self) -> None:
        """V 键 —— 在截断预览与全文预览之间切换。"""
        self._toggle_full_preview()

    def _toggle_full_preview(self) -> None:
        if not self.file_path or not os.path.isfile(self.file_path):
            return
        try:
            full_btn = self.query_one("#bv-full-btn", Button)
        except Exception:
            return
        if not self._is_full:
            try:
                from src.utils.file_helpers import read_file_full
                content = read_file_full(self.file_path)
            except Exception as e:
                self.notify(f"{get_global_i18n().t('crawler.preview_failed')}: {e}",
                            severity="error")
                return
            if not content.strip():
                self.notify(get_global_i18n().t("crawler.preview_empty"),
                            severity="information")
                return
            self._render_preview(content, "book_view.full_note")
            full_btn.label = get_global_i18n().t("book_view.preview_short")
            self._is_full = True
        else:
            self._render_preview(self.original_content, "book_view.truncated_note")
            full_btn.label = get_global_i18n().t("book_view.preview_full")
            self._is_full = False
        self._set_view("preview")

    def action_view_file(self) -> None:
        """F 键 —— 在系统文件管理器中定位文件。"""
        from src.ui.utils.book_view_utils import reveal_book_file
        reveal_book_file(self, self.file_path)

    def action_scroll_down(self) -> None:
        try:
            self.query_one("#bv-preview-text", RichLog).scroll_down()
        except Exception:
            pass

    def action_scroll_up(self) -> None:
        try:
            self.query_one("#bv-preview-text", RichLog).scroll_up()
        except Exception:
            pass

    def action_close(self) -> None:
        self.dismiss()

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        handlers = {
            "bv-details-btn": lambda: self._set_view("details"),
            "bv-preview-btn": self.action_show_preview,
            "bv-full-btn": self._toggle_full_preview,
            "bv-view-file-btn": self.action_view_file,
            "bv-close-btn": self.action_close,
        }
        handler = handlers.get(event.button.id)
        if handler:
            handler()


# ---------------------------------------------------------------------- 兼容层

class BookDetailsDialog(BookViewDialog):
    """兼容旧签名：``BookDetailsDialog(title, details, ..., preview_factory)``。

    底层已统一为 :class:`BookViewDialog`；若调用方仍传入 ``preview_factory``，
    v 键会用旧方式打开外部预览屏幕，否则直接切到内置预览视图。
    """

    def __init__(self, title: str, details: List[Tuple[str, Any]],
                 content: Optional[str] = None,
                 theme_manager: Optional[ThemeManager] = None,
                 file_path: Optional[str] = None,
                 preview_factory: Optional[Callable[[], Any]] = None) -> None:
        data = BookViewData(
            title=title,
            details=details or [],
            content=content or "",
            file_path=file_path or "",
            allow_preview=bool(content or preview_factory),
        )
        super().__init__(data, theme_manager, initial_view="details")
        self.preview_factory = preview_factory
        self.dialog_title = title

    def action_show_preview(self) -> None:
        if self.preview_factory is not None:
            try:
                screen = self.preview_factory()
                if screen is None:
                    return
                switch = getattr(self.app, "switch_screen", None)
                if callable(switch):
                    switch(screen)
                else:
                    self.dismiss()
                    self.app.push_screen(screen)
                return
            except Exception as e:
                self.notify(f"{get_global_i18n().t('common.action_failed')}: {e}",
                            severity="error")
                return
        super().action_show_preview()


class BookPreviewDialog(BookViewDialog):
    """兼容旧签名：``BookPreviewDialog(theme_manager, title, content, metadata, details_factory)``。"""

    def __init__(self, theme_manager: ThemeManager, title: str, content: str,
                 metadata: Optional[Dict[str, Any]] = None,
                 details_factory: Optional[Callable[[], Any]] = None) -> None:
        meta = dict(metadata or {})
        file_path = meta.get("file_path") or meta.get("path") or ""
        data = BookViewData(
            title=title,
            details=[],
            content=content or "",
            file_path=file_path,
            metadata=meta,
        )
        super().__init__(data, theme_manager, initial_view="preview")
        self.details_factory = details_factory

    def action_show_details(self) -> None:
        if self.details_factory is not None:
            try:
                screen = self.details_factory()
                if screen is None:
                    return
                switch = getattr(self.app, "switch_screen", None)
                if callable(switch):
                    switch(screen)
                else:
                    self.dismiss()
                    self.app.push_screen(screen)
                return
            except Exception as e:
                self.notify(f"{get_global_i18n().t('common.action_failed')}: {e}",
                            severity="error")
                return
        super().action_show_details()

    # 旧版对外暴露的动作名
    def action_view_details(self) -> None:
        self.action_show_details()

    def action_toggle_preview(self) -> None:
        super().action_toggle_preview()
