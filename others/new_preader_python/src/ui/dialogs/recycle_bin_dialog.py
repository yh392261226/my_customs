"""
回收站对话框：查看 / 恢复 / 撤销批次 / 彻底删除 / 清空。

* 「恢复选中」：把选中的书籍连同阅读历史、书签、标签、元数据、用户归属、
  合并溯源等关联数据一起写回数据库，并把文件放回原路径。
* 「撤销本次操作」：按 batch_id 一次恢复整次批量去重 / 合并 / 批量合并的
  全部源书，同时移除该次操作生成的合并文件，完整回到操作前状态。
* 「彻底删除」「清空回收站」才会真正删除物理文件。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static
from textual import on

from src.core.recycle_bin import get_recycle_bin, operation_label
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.ui.dialogs.confirm_dialog import ConfirmDialog
from src.ui.messages import RefreshBookshelfMessage
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RecycleBinDialog(ModalScreen[Optional[Dict[str, Any]]]):
    """书籍回收站（支持按条目恢复与按操作批次撤销）。"""

    CSS_PATH = "../styles/recycle_bin_dialog.tcss"

    BINDINGS = [
        ("escape", "close", "关闭"),
        ("space", "toggle_row", "选中/取消"),
        ("a", "select_all", "全选"),
        ("r", "restore_selected", "恢复选中"),
        ("u", "undo_batch", "撤销本次操作"),
        ("d", "purge_selected", "彻底删除"),
        ("e", "empty_bin", "清空回收站"),
        ("R", "reload", "刷新"),
        ("p", "prev_page", "上一页"),
        ("n", "next_page", "下一页"),
        ("f", "view_file", "查看文件"),
        ("v", "preview_book", "预览"),
        ("i", "view_details", "查看详情"),
    ]

    def __init__(self, theme_manager: ThemeManager, bookshelf: Any = None) -> None:
        super().__init__()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        self.recycle_bin = get_recycle_bin(
            getattr(bookshelf, "db_manager", None) if bookshelf is not None else None
        )
        self._items: List[Dict[str, Any]] = []
        self._selected: Set[int] = set()
        self._search_text: str = ""
        self._changed = False
        self._current_page: int = 1
        self._items_per_page: int = 10
        self._total_pages: int = 1

    # ------------------------------------------------------------------ UI

    def compose(self) -> ComposeResult:
        t = get_global_i18n().t
        yield Header()
        with Container(id="recycle-bin-window"):
            yield Static(t("recycle_bin.title"), id="recycle-bin-title")
            yield Static("", id="recycle-bin-summary")
            with Horizontal(id="recycle-bin-search-row", classes="search-row"):
                yield Input(placeholder=t("recycle_bin.search_placeholder"),
                            id="recycle-bin-search", classes="recycle-bin-search")
                yield Button(t("recycle_bin.search"), id="rb-search-btn")
                yield Button(t("recycle_bin.clear_search"), id="rb-clear-search-btn")
            yield DataTable(id="recycle-bin-table", cursor_type="row", zebra_stripes=True)
            yield Horizontal(
                Button("◀◀", id="first-page-btn", classes="pagination-btn"),
                Button("◀", id="prev-page-btn", classes="pagination-btn"),
                Label("", id="page-info", classes="page-info"),
                Button("▶", id="next-page-btn", classes="pagination-btn"),
                Button("▶▶", id="last-page-btn", classes="pagination-btn"),
                Button(t("bookshelf.jump_to"), id="jump-page-btn", classes="pagination-btn"),
                id="pagination-bar",
                classes="pagination-bar",
            )
            with Horizontal(id="recycle-bin-buttons", classes="btn-row"):
                yield Button(t("recycle_bin.restore_selected"), id="rb-restore-btn", variant="primary")
                yield Button(t("recycle_bin.undo_batch"), id="rb-undo-btn", variant="warning")
                yield Button(t("recycle_bin.purge_selected"), id="rb-purge-btn", variant="error")
                yield Button(t("recycle_bin.empty_bin"), id="rb-empty-btn", variant="error")
                yield Button(t("common.refresh"), id="rb-refresh-btn")
                yield Button(t("common.close"), id="rb-close-btn")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass
        table = self.query_one("#recycle-bin-table", DataTable)
        t = get_global_i18n().t
        table.add_columns(
            t("recycle_bin.col_select"),
            t("recycle_bin.col_title"),
            t("recycle_bin.col_author"),
            t("recycle_bin.col_deleted"),
            t("recycle_bin.col_operation"),
            t("recycle_bin.col_batch"),
            t("recycle_bin.col_path"),
        )
        self._load()
        # 默认聚焦表格，使 v/f/i（及 space/a/p/n 等）快捷键打开即可用，
        # 需要搜索时再点击/ Tab 到搜索框。
        try:
            table.focus()
        except Exception:
            pass

    @on(Input.Submitted, "#recycle-bin-search")
    def _on_search_submitted(self) -> None:
        """在搜索框按回车也可触发搜索。"""
        self._apply_search()

    def _apply_search(self) -> None:
        """点击「搜索」按钮（或回车）才按关键字过滤。"""
        try:
            self._search_text = (self.query_one("#recycle-bin-search", Input).value or "").strip()
        except Exception:
            self._search_text = ""
        self._current_page = 1
        self._load()

    def action_clear_search(self) -> None:
        self._search_text = ""
        try:
            self.query_one("#recycle-bin-search", Input).value = ""
        except Exception:
            pass
        self._current_page = 1
        self._load()

    # ------------------------------------------------------------------ 数据

    def _auto_clear_days(self) -> int:
        try:
            from src.config.config_manager import ConfigManager
            config = ConfigManager.get_instance().get_config()
            return int(config.get("advanced", {}).get("recycle_bin_auto_clear_days", 10))
        except Exception:
            return 10

    def _load(self) -> None:
        """读取回收站条目、按关键字过滤，得到完整过滤列表后交给分页渲染。"""
        try:
            self.recycle_bin.auto_purge_from_config()
            items = self.recycle_bin.list_items()
        except Exception as e:
            logger.error(f"读取回收站失败: {e}")
            items = []
        # 关键字过滤（书名 / 作者 / 路径 / 操作 / 批次）
        kw = (self._search_text or "").strip().lower()
        if kw:
            def _hit(item: Dict[str, Any]) -> bool:
                hay = " ".join([
                    str(item.get("title") or ""),
                    str(item.get("author") or ""),
                    str(item.get("book_path") or ""),
                    operation_label(str(item.get("operation") or "")),
                    str(item.get("batch_id") or ""),
                ]).lower()
                return kw in hay
            items = [i for i in items if _hit(i)]
        self._items = items
        valid_ids = {int(item["id"]) for item in self._items}
        self._selected.intersection_update(valid_ids)
        self._render_page()

    def _render_page(self) -> None:
        """按当前页码渲染表格、摘要与分页信息（与爬取管理分页效果一致）。"""
        total = len(self._items)
        self._total_pages = max(1, (total + self._items_per_page - 1) // self._items_per_page)
        if self._current_page < 1:
            self._current_page = 1
        if self._current_page > self._total_pages:
            self._current_page = self._total_pages

        start = (self._current_page - 1) * self._items_per_page
        end = min(start + self._items_per_page, total)

        t = get_global_i18n().t
        table = self.query_one("#recycle-bin-table", DataTable)
        table.clear()
        for item in self._items[start:end]:
            item_id = int(item["id"])
            table.add_row(
                "☑" if item_id in self._selected else "□",
                str(item.get("title") or os.path.basename(item.get("book_path", ""))),
                str(item.get("author") or ""),
                str(item.get("deleted_at") or "")[:19].replace("T", " "),
                operation_label(str(item.get("operation") or "")),
                str(item.get("batch_id") or "")[:8],
                str(item.get("book_path") or ""),
                key=str(item_id),
            )

        days = self._auto_clear_days()
        auto_text = (t("recycle_bin.auto_clear_days", days=days) if days > 0
                     else t("recycle_bin.auto_clear_disabled"))
        self.query_one("#recycle-bin-summary", Static).update(
            f"{t('recycle_bin.summary', count=total, selected=len(self._selected))}  ·  {auto_text}"
        )
        has_selection = bool(self._selected)
        self.query_one("#rb-restore-btn", Button).disabled = not has_selection
        self.query_one("#rb-purge-btn", Button).disabled = not has_selection
        self.query_one("#rb-undo-btn", Button).disabled = not self._items
        self.query_one("#rb-empty-btn", Button).disabled = not self._items
        self._update_pagination_info()

    def _update_pagination_info(self) -> None:
        """更新分页信息标签与翻页按钮的可用状态。"""
        try:
            page_label = self.query_one("#page-info", Label)
            t = get_global_i18n().t
            page_label.update(t("page_info", total=len(self._items),
                                current=self._current_page, pages=self._total_pages))
            first_btn = self.query_one("#first-page-btn", Button)
            prev_btn = self.query_one("#prev-page-btn", Button)
            next_btn = self.query_one("#next-page-btn", Button)
            last_btn = self.query_one("#last-page-btn", Button)
            first_btn.disabled = self._current_page <= 1
            prev_btn.disabled = self._current_page <= 1
            next_btn.disabled = self._current_page >= self._total_pages
            last_btn.disabled = self._current_page >= self._total_pages
        except Exception as e:
            logger.error(f"更新回收站分页信息失败: {e}")

    # ------------------------------------------------------------------ 分页

    def _go_to_first_page(self) -> None:
        if self._current_page != 1:
            self._current_page = 1
            self._render_page()

    def _go_to_prev_page(self) -> None:
        if self._current_page > 1:
            self._current_page -= 1
            self._render_page()

    def _go_to_next_page(self) -> None:
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._render_page()

    def _go_to_last_page(self) -> None:
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._render_page()

    def action_prev_page(self) -> None:
        self._go_to_prev_page()

    def action_next_page(self) -> None:
        self._go_to_next_page()

    def action_view_file(self) -> None:
        """f键 - 查看光标所在条目的文件。"""
        self._view_file(self._cursor_item())

    def action_preview_book(self) -> None:
        """v键 - 预览光标所在条目。"""
        self._preview_book(self._cursor_item())

    def action_view_details(self) -> None:
        """i键 - 查看光标所在条目的详情。"""
        self._view_details(self._cursor_item())

    def _show_jump_dialog(self) -> None:
        """显示跳转页码对话框（与爬取管理一致）。"""
        def handle_jump_result(result: Optional[str]) -> None:
            if result and result.strip():
                try:
                    page_num = int(result.strip())
                    if 1 <= page_num <= self._total_pages:
                        if page_num != self._current_page:
                            self._current_page = page_num
                            self._render_page()
                    else:
                        self.notify(
                            get_global_i18n().t("batch_ops.page_error_info", pages=self._total_pages),
                            severity="error",
                        )
                except ValueError:
                    self.notify(get_global_i18n().t("batch_ops.page_error"), severity="error")

        from src.ui.dialogs.input_dialog import InputDialog
        t = get_global_i18n().t
        dialog = InputDialog(
            self.theme_manager,
            title=t("bookshelf.jump_to"),
            prompt=f"{t('batch_ops.type_num')} (1-{self._total_pages})",
            placeholder=f"{t('batch_ops.current')}: {self._current_page}/{self._total_pages}",
        )
        self.app.push_screen(dialog, handle_jump_result)

    def _cursor_item(self) -> Optional[Dict[str, Any]]:
        """返回光标所在行的回收站条目。"""
        table = self.query_one("#recycle-bin-table", DataTable)
        key = None
        try:
            from textual.coordinate import Coordinate
            cell_key = table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0))
            key = getattr(cell_key.row_key, "value", cell_key.row_key)
        except Exception:
            try:
                row_key = list(table.rows.keys())[table.cursor_row]
                key = getattr(row_key, "value", row_key)
            except Exception:
                return None
        for item in self._items:
            if str(item["id"]) == str(key):
                return item
        return None

    def _actual_file_path(self, item: Dict[str, Any]) -> str:
        """返回该条目文件当前所在的真实路径（默认仍在原位置；导入替换场景可能为原位改名后的路径）。"""
        return item.get("file_name") or item.get("book_path") or ""

    def _build_recycle_view_data(self, item: Dict[str, Any]):
        """组装回收站条目的统一视图数据（详情 / 预览共用）。"""
        from src.ui.utils.book_view_utils import build_view_data
        t = get_global_i18n().t
        actual_path = self._actual_file_path(item)
        if not actual_path:
            # 没有实际文件时，使用原始路径（通常也不存在），避免被解析为当前目录
            actual_path = item.get("book_path") or "recycle_bin://missing"
        original = item.get("book_path") or ""
        details = [
            (t("common.book_title"), item.get("title") or os.path.basename(original or actual_path or "")),
            (t("common.author"), item.get("author") or ""),
            (t("recycle_bin.col_operation"), operation_label(str(item.get("operation") or ""))),
            (t("recycle_bin.col_deleted"), str(item.get("deleted_at") or "")[:19].replace("T", " ")),
            (t("recycle_bin.col_batch"), str(item.get("batch_id") or "")),
            (t("recycle_bin.reason"), str(item.get("reason") or "")),
            (t("recycle_bin.original_path"), original),
            (t("recycle_bin.current_path"), actual_path),
        ]
        return build_view_data(
            actual_path,
            title=item.get("title") or os.path.basename(actual_path or original or ""),
            details=details,
            metadata={"file_path": actual_path, "book_path": original},
            allow_preview=True,
        )

    def _view_file(self, item: Optional[Dict[str, Any]]) -> None:
        """查看文件：在系统文件管理器中定位回收站条目当前所在的实际文件。"""
        if not item:
            return
        actual_path = self._actual_file_path(item)
        if not actual_path or not os.path.isfile(actual_path):
            self.notify(get_global_i18n().t("common.file_not_exist"), severity="warning")
            return
        from src.ui.utils.book_view_utils import reveal_book_file
        reveal_book_file(self, actual_path)

    def _view_details(self, item: Optional[Dict[str, Any]]) -> None:
        """查看详情：打开统一详情弹窗（弹窗内可继续预览 / 查看文件）。"""
        if not item:
            return
        t = get_global_i18n().t
        data = self._build_recycle_view_data(item)
        if data.file_path and not os.path.exists(data.file_path):
            self.notify(t("common.file_not_exist"), severity="warning")
        from src.ui.utils.book_view_utils import make_book_view_dialog
        self.app.push_screen(make_book_view_dialog(data, self.theme_manager, "details"))

    def _preview_book(self, item: Optional[Dict[str, Any]]) -> None:
        """预览：打开统一预览弹窗，显示回收站文件的前若干字内容。"""
        if not item:
            return
        t = get_global_i18n().t
        data = self._build_recycle_view_data(item)
        if not data.file_path or not os.path.exists(data.file_path):
            self.notify(t("common.file_not_exist"), severity="warning")
            return
        if not data.content.strip():
            self.notify(t("recycle_bin.preview_empty"), severity="information")
            return
        from src.ui.utils.book_view_utils import make_book_view_dialog
        self.app.push_screen(make_book_view_dialog(data, self.theme_manager, "preview"))

    def _notify_bookshelf(self) -> None:
        self._changed = True
        try:
            if self.bookshelf is not None:
                self.bookshelf._load_books()
        except Exception as e:
            logger.debug(f"刷新书架数据失败: {e}")
        try:
            self.app.post_message(RefreshBookshelfMessage())
        except Exception:
            pass

    def _confirm(self, title: str, message: str, callback) -> None:
        self.app.push_screen(ConfirmDialog(self.theme_manager, title, message), callback)

    # ------------------------------------------------------------------ 操作

    @on(DataTable.RowSelected, "#recycle-bin-table")
    def _on_row_selected(self) -> None:
        self.action_toggle_row()

    def action_toggle_row(self) -> None:
        item = self._cursor_item()
        if item is None:
            return
        item_id = int(item["id"])
        if item_id in self._selected:
            self._selected.discard(item_id)
        else:
            self._selected.add(item_id)
        self._load()

    def action_select_all(self) -> None:
        if len(self._selected) == len(self._items):
            self._selected.clear()
        else:
            self._selected = {int(item["id"]) for item in self._items}
        self._load()

    def action_restore_selected(self) -> None:
        t = get_global_i18n().t
        if not self._selected:
            self.notify(t("recycle_bin.no_selection"), severity="warning")
            return
        item_ids = sorted(self._selected)
        result = self.recycle_bin.restore_items(item_ids)
        self._selected.clear()
        self._notify_bookshelf()
        self._load()
        if result["files"] < result["ok"]:
            self.notify(t("recycle_bin.restored_without_file", count=result["ok"]), severity="warning")
        else:
            self.notify(t("recycle_bin.restored", count=result["ok"]), severity="information")

    def action_undo_batch(self) -> None:
        t = get_global_i18n().t
        item = self._cursor_item()
        if item is None:
            self.notify(t("recycle_bin.no_selection"), severity="warning")
            return
        batch_id = str(item.get("batch_id") or "")
        count = sum(1 for i in self._items if str(i.get("batch_id")) == batch_id)

        def on_confirm(confirmed: Optional[bool]) -> None:
            if not confirmed:
                return
            result = self.recycle_bin.restore_batch(batch_id)
            self._selected.clear()
            self._notify_bookshelf()
            self._load()
            self.notify(
                t("recycle_bin.undo_done", count=result.get("ok", 0),
                  created=result.get("removed_created", 0)),
                severity="information",
            )

        self._confirm(
            t("recycle_bin.confirm_undo"),
            t("recycle_bin.confirm_undo_message", count=count,
              operation=operation_label(str(item.get("operation") or ""))),
            on_confirm,
        )

    def action_purge_selected(self) -> None:
        t = get_global_i18n().t
        if not self._selected:
            self.notify(t("recycle_bin.no_selection"), severity="warning")
            return
        item_ids = sorted(self._selected)

        def on_confirm(confirmed: Optional[bool]) -> None:
            if not confirmed:
                return
            count = self.recycle_bin.purge_items(item_ids)
            self._selected.clear()
            self._load()
            self.notify(t("recycle_bin.purged", count=count), severity="information")

        self._confirm(
            t("recycle_bin.confirm_purge"),
            t("recycle_bin.confirm_purge_message", count=len(item_ids)),
            on_confirm,
        )

    def action_empty_bin(self) -> None:
        t = get_global_i18n().t
        if not self._items:
            self.notify(t("recycle_bin.already_empty"), severity="information")
            return

        def on_confirm(confirmed: Optional[bool]) -> None:
            if not confirmed:
                return
            count = self.recycle_bin.empty()
            self._selected.clear()
            self._load()
            self.notify(t("recycle_bin.emptied", count=count), severity="information")

        self._confirm(
            t("recycle_bin.confirm_empty"),
            t("recycle_bin.confirm_empty_message", count=len(self._items)),
            on_confirm,
        )

    def action_reload(self) -> None:
        self._load()

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        actions = {
            "rb-restore-btn": self.action_restore_selected,
            "rb-undo-btn": self.action_undo_batch,
            "rb-purge-btn": self.action_purge_selected,
            "rb-empty-btn": self.action_empty_bin,
            "rb-refresh-btn": self.action_reload,
            "rb-close-btn": self.action_close,
            "rb-search-btn": self._apply_search,
            "rb-clear-search-btn": self.action_clear_search,
            "first-page-btn": self._go_to_first_page,
            "prev-page-btn": self._go_to_prev_page,
            "next-page-btn": self._go_to_next_page,
            "last-page-btn": self._go_to_last_page,
            "jump-page-btn": self._show_jump_dialog,
        }
        handler = actions.get(event.button.id or "")
        if handler:
            handler()

    def action_close(self) -> None:
        self.dismiss({"refresh": self._changed})
