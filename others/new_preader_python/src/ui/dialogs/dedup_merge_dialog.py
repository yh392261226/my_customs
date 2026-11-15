"""
去重分组页「合并选中」弹窗。

与爬取管理页的「选中合并」保持一致的交互：
- 数字键 1-9、0（第 10 位）把光标所在行移动到指定位置；
- k/j（及上下方向键）上移 / 下移当前行；
- 智能章节排序 + 自动识别书名与章节号（SmartTitleUtils）；
- 合并顺序即列表顺序，可反复调整后再确认。

网站（作者）处理：
- 被合并书籍通常来自同一网站；"作者为空" 视为没有网站记录。
- 只有一个网站时：没有网站的书在合并后作者自动设为该网站名。
- 出现两个及以上不同网站时：显示下拉框列出全部网站，由用户选择合并到哪个网站。
- 合并完成后，向所选网站的爬取历史表写入一条合并记录。
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select, Static
from textual import on

from src.core.book import Book
from src.core.database_manager import DatabaseManager
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.ui.utils.smart_title_utils import SmartTitleUtils
from src.utils.file_utils import FileUtils
from src.utils.logger import get_logger

logger = get_logger(__name__)

_NONE_SITE = "__none__"


class DedupMergeDialog(ModalScreen[Dict[str, Any]]):
    """把去重组中选中的书籍按可调顺序合并为一本，并归到正确的书籍网站。"""

    CSS_PATH = "../styles/dedup_merge_dialog.tcss"

    BINDINGS = [
        Binding("escape", "cancel", get_global_i18n().t("common.cancel")),
        Binding("space", "toggle_row", get_global_i18n().t("batch_ops.toggle_row")),
        Binding("k", "move_up", get_global_i18n().t("merge_detail.move_up")),
        Binding("j", "move_down", get_global_i18n().t("merge_detail.move_down")),
        Binding("up", "move_up", get_global_i18n().t("merge_detail.move_up")),
        Binding("down", "move_down", get_global_i18n().t("merge_detail.move_down")),
        Binding("m", "smart_sort", get_global_i18n().t("dedup_merge.smart_sort")),
        Binding("t", "smart_title", get_global_i18n().t("merge_detail.smart_title")),
    ]

    def __init__(
        self,
        theme_manager: ThemeManager,
        books: List[Book],
        db_manager: Optional[DatabaseManager] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme_manager = theme_manager
        self.i18n = get_global_i18n()
        self.db_manager = db_manager
        self.books: List[Book] = list(books)

        # 内部条目：合并顺序 = self._order 中 path 的先后顺序
        self._items: Dict[str, Dict[str, Any]] = {}
        for book in self.books:
            title = FileUtils.strip_filename_timestamp(book.title or book.file_name or "")
            self._items[book.path] = {
                "path": book.path,
                "novel_title": title,
                "author": (book.author or "").strip(),
                "size": getattr(book, "size", 0) or 0,
                "format": (getattr(book, "format", "") or "").upper(),
                "tags": getattr(book, "tags", "") or "",
                "site_id": None,
                "site_name": "",
            }
        self._order: List[str] = [book.path for book in self.books]
        self._checked: Set[str] = set(self._order)

        # 网站解析
        self._sites: Dict[int, Dict[str, Any]] = {}
        self._site_ids: List[int] = []
        self._site_default: str = _NONE_SITE

        # 书库与回收站
        self._bookshelf = None
        self._merging = False

    # ─── 网站解析 ─────────────────────────────────────────────

    def _resolve_sites(self) -> None:
        """解析每本书的来源网站；确定下拉框选项与默认网站。"""
        db = self.db_manager
        if not db:
            return
        try:
            sites = db.get_novel_sites() or []
            self._sites = {
                int(s["id"]): s for s in sites if s.get("id") is not None
            }
        except Exception as e:
            logger.debug(f"读取书籍网站配置失败: {e}")
            self._sites = {}

        by_name = {
            (s.get("name") or "").strip(): s
            for s in self._sites.values()
            if (s.get("name") or "").strip()
        }

        src_map: Dict[str, Dict[str, Any]] = {}
        try:
            src_map = db.get_crawl_history_source_map(
                [p for p in self._order]
            ) or {}
        except Exception as e:
            logger.debug(f"反查爬取历史来源失败: {e}")

        for path, item in self._items.items():
            sid = src_map.get(os.path.abspath(path), {}).get("site_id")
            sname = ""
            if sid is not None and int(sid) in self._sites:
                sid = int(sid)
                sname = (self._sites[sid].get("name") or "").strip()
            else:
                sid = None
                author = item.get("author", "")
                if author and author in by_name:
                    site = by_name[author]
                    sid = int(site["id"])
                    sname = (site.get("name") or "").strip()
            item["site_id"] = sid
            item["site_name"] = sname

        # 去重后的真实网站（有 site_id 的），保持出现顺序
        seen: Set[int] = set()
        self._site_ids = []
        for path in self._order:
            sid = self._items[path].get("site_id")
            if sid is not None and sid not in seen:
                seen.add(sid)
                self._site_ids.append(sid)

        if len(self._site_ids) == 1:
            self._site_default = str(self._site_ids[0])
        elif len(self._site_ids) > 1:
            # 选择出现次数最多的网站作为默认项
            counts: Dict[int, int] = {}
            for path in self._order:
                sid = self._items[path].get("site_id")
                if sid is not None:
                    counts[sid] = counts.get(sid, 0) + 1
            top = sorted(self._site_ids, key=lambda s: counts.get(s, 0), reverse=True)[0]
            self._site_default = str(top)
        else:
            self._site_default = _NONE_SITE

    # ─── Compose ──────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        t = self.i18n.t
        self._resolve_sites()
        self._bookshelf = getattr(self.app, "bookshelf", None)

        site_options: List[Tuple[str, str]] = [
            ((self._sites.get(sid, {}).get("name") or f"site {sid}"), str(sid))
            for sid in self._site_ids
        ]

        yield Header()
        with Container(id="dedup-merge-container"):
            with Vertical():
                yield Label(t("dedup_merge.title"), id="dedup-merge-title")
                yield Static(t("dedup_merge.table_hint"), id="dedup-merge-hint")

                yield DataTable(id="dedup-merge-table")

                with Horizontal(id="dedup-merge-sort-row"):
                    yield Button(t("merge_detail.move_up"), id="dm-move-up-btn")
                    yield Button(t("merge_detail.move_down"), id="dm-move-down-btn")
                    yield Button(t("dedup_merge.smart_sort"), id="dm-smart-sort-btn", variant="success")
                    yield Button(t("merge_detail.smart_title"), id="dm-smart-title-btn", variant="success")
                    yield Button(t("merge_detail.select_all"), id="dm-select-all-btn")
                    yield Button(t("merge_detail.deselect_all"), id="dm-deselect-all-btn")

                with Horizontal(id="dedup-merge-title-row"):
                    yield Label(t("merge_detail.merged_title_label"), id="dm-title-label")
                    yield Input(
                        placeholder=t("merge_detail.title_placeholder"),
                        id="dm-title-input",
                    )

                site_row_classes = "" if len(self._site_ids) > 1 else "hidden"
                with Horizontal(id="dedup-merge-site-row", classes=site_row_classes):
                    yield Label(t("dedup_merge.site_label"), id="dm-site-label")
                    yield Select(
                        options=site_options or [(_NONE_SITE, _NONE_SITE)],
                        value=self._site_default,
                        id="dm-site-select",
                    )
                    yield Static(t("dedup_merge.site_hint_multi"), id="dm-site-hint")

                yield Label("", id="dedup-merge-status")

                with Horizontal(id="dedup-merge-buttons"):
                    yield Button(t("dedup_merge.confirm"), id="dm-confirm-btn", variant="primary")
                    yield Button(t("common.cancel"), id="dm-cancel-btn", variant="error")
        yield Footer()

    # ─── Mount ────────────────────────────────────────────────

    def on_mount(self) -> None:
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass
        table = self.query_one("#dedup-merge-table", DataTable)
        try:
            table.cursor_type = "row"
            table.zebra_stripes = True
        except Exception:
            pass
        self._build_table()
        self._apply_smart_title(notify=False)
        try:
            table.focus()
        except Exception:
            pass

    # ─── 表格 ─────────────────────────────────────────────────

    def _build_table(self, preserve_cursor: bool = True) -> None:
        t = self.i18n.t
        table = self.query_one("#dedup-merge-table", DataTable)
        prev_row = getattr(table, "cursor_row", None)
        prev_col = getattr(table, "cursor_column", None)
        table.clear()

        if not table.columns:
            table.add_column(t("dedup_merge.col_check"), key="check", width=4)
            table.add_column(t("dedup_merge.col_seq"), key="seq", width=5)
            table.add_column(t("dedup_merge.col_title"), key="title", width=48)
            table.add_column(t("common.author"), key="site", width=18)
            table.add_column(t("common.size"), key="size", width=10)
            table.add_column(t("common.format"), key="format", width=8)

        seq = 0
        for path in self._order:
            item = self._items[path]
            checked = path in self._checked
            if checked:
                seq += 1
                seq_text = str(seq)
                check_text = "✓"
            else:
                seq_text = "·"
                check_text = "□"
            size_text = self._format_size(item.get("size", 0))
            site_text = item.get("site_name") or item.get("author") or t("dedup_merge.no_site")
            table.add_row(
                check_text,
                seq_text,
                item.get("novel_title", ""),
                site_text,
                size_text,
                item.get("format", ""),
                key=path,
            )

        if preserve_cursor:
            self._restore_cursor(table, prev_row, prev_col)
        self._update_status()

    @staticmethod
    def _restore_cursor(table: DataTable, row, column=None) -> None:
        if row is None:
            return
        try:
            row_count = len(table.rows)
            if row_count <= 0:
                return
            target_row = max(0, min(int(row), row_count - 1))
            kwargs = {"row": target_row}
            if column is not None:
                col_count = len(table.columns)
                if col_count > 0:
                    kwargs["column"] = max(0, min(int(column), col_count - 1))
            table.move_cursor(**kwargs)
        except Exception as e:
            logger.debug(f"恢复光标失败（可忽略）: {e}")

    @staticmethod
    def _format_size(size) -> str:
        try:
            size = float(size or 0)
            if size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            return f"{size / (1024 * 1024):.1f} MB"
        except Exception:
            return ""

    def _update_status(self) -> None:
        t = self.i18n.t
        try:
            label = self.query_one("#dedup-merge-status", Label)
            label.update(
                t("dedup_merge.status", selected=len(self._checked), total=len(self._order))
            )
        except Exception:
            pass

    def _cursor_path(self) -> Optional[str]:
        table = self.query_one("#dedup-merge-table", DataTable)
        row = getattr(table, "cursor_row", None)
        if row is None or not (0 <= row < len(self._order)):
            return None
        return self._order[row]

    # ─── 选择 / 移动 ──────────────────────────────────────────

    def action_toggle_row(self) -> None:
        path = self._cursor_path()
        if not path:
            return
        if path in self._checked:
            self._checked.discard(path)
        else:
            self._checked.add(path)
        row = self.query_one("#dedup-merge-table", DataTable).cursor_row
        self._build_table()
        self._restore_cursor(self.query_one("#dedup-merge-table", DataTable), row)

    def action_move_up(self) -> None:
        self._move_current_row(-1)

    def action_move_down(self) -> None:
        self._move_current_row(1)

    def _move_current_row(self, direction: int) -> None:
        table = self.query_one("#dedup-merge-table", DataTable)
        row = getattr(table, "cursor_row", None)
        if row is None:
            return
        target = row + direction
        if not (0 <= target < len(self._order)):
            return
        self._order[row], self._order[target] = self._order[target], self._order[row]
        self._build_table()
        self._restore_cursor(table, target)
        table.focus()

    def _on_move_up(self) -> None:
        self._move_current_row(-1)

    def _on_move_down(self) -> None:
        self._move_current_row(1)

    def on_key(self, event) -> None:
        """数字键 1-9、0（第 10 位）：把光标所在行移动到指定位置。

        Escape 交给 BINDINGS 处理，避免重复 dismiss；焦点在输入框时不拦截，
        以便标题里可以正常输入数字。
        """
        if not event.key.isdigit():
            return
        try:
            focused = self.focused
            if focused is not None and focused.id == "dm-title-input":
                return
        except Exception:
            pass
        digit = int(event.key)
        position = 10 if digit == 0 else digit
        if 1 <= position <= len(self._order):
            self._move_to_position(position)
            event.stop()

    def _move_to_position(self, position: int) -> None:
        table = self.query_one("#dedup-merge-table", DataTable)
        row = getattr(table, "cursor_row", None)
        if row is None:
            return
        target = position - 1
        if row == target:
            return
        path = self._order.pop(row)
        self._order.insert(target, path)
        self._build_table()
        self._restore_cursor(table, target)
        table.focus()

    def action_smart_sort(self) -> None:
        """按章节号智能排序（自动识别书名中的章节号）。"""
        items = [self._items[p] for p in self._order]
        sorted_items, success = SmartTitleUtils.sort_books_by_chapter(items)
        if not success:
            self.notify(self.i18n.t("dedup_merge.smart_sort_failed"), severity="warning", timeout=2)
            return
        self._order = [item["path"] for item in sorted_items]
        self._build_table()
        self._apply_smart_title(notify=False)
        self.notify(self.i18n.t("dedup_merge.smart_sorted"), timeout=2)

    def action_smart_title(self) -> None:
        self._apply_smart_title(notify=True)

    def _apply_smart_title(self, notify: bool = True) -> None:
        titles = [
            self._items[p]["novel_title"]
            for p in self._order
            if p in self._checked and self._items[p].get("novel_title")
        ]
        if len(titles) < 2:
            return
        try:
            smart_title = SmartTitleUtils.generate_smart_title(titles)
        except Exception as e:
            logger.debug(f"智能标题生成失败: {e}")
            smart_title = None
        if not smart_title:
            if notify:
                self.notify(self.i18n.t("merge_detail.smart_title_failed"), severity="warning", timeout=2)
            return
        title_input = self.query_one("#dm-title-input", Input)
        title_input.value = smart_title
        if notify:
            self.notify(self.i18n.t("merge_detail.smart_title_applied", title=smart_title), timeout=2)

    # ─── 按钮事件 ─────────────────────────────────────────────

    def _on_select_all(self) -> None:
        self._checked = set(self._order)
        self._build_table()

    def _on_deselect_all(self) -> None:
        self._checked.clear()
        self._build_table()

    def _chosen_site(self) -> Tuple[Optional[int], str]:
        if not self._site_ids:
            return None, ""
        site_id: Optional[int] = None
        if len(self._site_ids) > 1:
            try:
                select = self.query_one("#dm-site-select", Select)
                value = select.value
                if value and value != Select.BLANK and str(value) != _NONE_SITE:
                    site_id = int(value)
            except Exception as e:
                logger.debug(f"读取网站选择失败: {e}")
        if site_id is None and len(self._site_ids) == 1:
            site_id = self._site_ids[0]
        site_name = (self._sites.get(site_id, {}).get("name") or "").strip() if site_id else ""
        return site_id, site_name

    def _on_confirm(self) -> None:
        if self._merging:
            return
        t = self.i18n.t
        title = self.query_one("#dm-title-input", Input).value.strip()
        if not title:
            self.notify(t("merge_detail.title_required"), severity="warning", timeout=2)
            return
        title = title.replace("/", "").replace("\\", "").strip()

        selected_paths = [p for p in self._order if p in self._checked]
        if len(selected_paths) < 2:
            self.notify(t("merge_detail.need_at_least_two"), severity="warning", timeout=2)
            return

        file_paths = [
            p for p in selected_paths
            if p and p != "already_exists" and os.path.exists(p)
        ]
        if len(file_paths) < 2:
            self.notify(t("dedup_merge.files_missing"), severity="error", timeout=3)
            return

        site_id, site_name = self._chosen_site()
        # 没有网站记录时，沿用第一本非空作者，否则用"未知作者"
        fallback_author = ""
        for p in file_paths:
            author = self._items[p].get("author", "")
            if author:
                fallback_author = author
                break
        new_author = site_name or fallback_author or t("dedup_merge.unknown_author")

        bookshelf = self._bookshelf or getattr(self.app, "bookshelf", None)
        if not bookshelf:
            self.notify(t("dedup_merge.no_bookshelf"), severity="error", timeout=3)
            return

        self._merging = True
        try:
            from src.core.recycle_bin import OP_BATCH_MERGE, get_recycle_bin

            db_manager = getattr(bookshelf, "db_manager", None)
            batch_id = get_recycle_bin(db_manager).create_batch(OP_BATCH_MERGE, "去重合并选中")
            tags = self._items[file_paths[0]].get("tags", "") or ""
            new_book = bookshelf.merge_books(
                file_paths,
                title,
                new_author,
                tags,
                batch_id=batch_id,
                operation=OP_BATCH_MERGE,
            )
            if not new_book:
                self.notify(t("batch_ops.merge_failed"), severity="error", timeout=3)
                self._merging = False
                return

            # 合并完成后，向所选网站的爬取历史表写入一条合并记录
            if site_id and db_manager:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    db_manager.add_crawl_history(
                        site_id=site_id,
                        novel_id=f"merged_{timestamp}",
                        novel_title=title,
                        status="success",
                        file_path=new_book.path,
                        error_message="",
                    )
                except Exception as e:
                    logger.error(f"写入合并爬取历史失败 [{title}]: {e}")

            self.notify(t("batch_ops.merge_success", title=title), timeout=3)
            self.dismiss({
                "merged": True,
                "merged_paths": set(file_paths),
                "merged_book": new_book,
                "new_title": title,
                "batch_id": batch_id,
            })
        except Exception as e:
            logger.error(f"去重合并选中失败: {e}")
            self.notify(t("batch_ops.merge_failed"), severity="error", timeout=3)
            self._merging = False

    def _on_cancel(self) -> None:
        self.dismiss({"merged": False})

    def action_cancel(self) -> None:
        self._on_cancel()

    # ─── 事件绑定 ─────────────────────────────────────────────

    @on(Button.Pressed, "#dm-move-up-btn")
    def _btn_move_up(self) -> None:
        self._on_move_up()

    @on(Button.Pressed, "#dm-move-down-btn")
    def _btn_move_down(self) -> None:
        self._on_move_down()

    @on(Button.Pressed, "#dm-smart-sort-btn")
    def _btn_smart_sort(self) -> None:
        self.action_smart_sort()

    @on(Button.Pressed, "#dm-smart-title-btn")
    def _btn_smart_title(self) -> None:
        self.action_smart_title()

    @on(Button.Pressed, "#dm-select-all-btn")
    def _btn_select_all(self) -> None:
        self._on_select_all()

    @on(Button.Pressed, "#dm-deselect-all-btn")
    def _btn_deselect_all(self) -> None:
        self._on_deselect_all()

    @on(Button.Pressed, "#dm-confirm-btn")
    def _btn_confirm(self) -> None:
        self._on_confirm()

    @on(Button.Pressed, "#dm-cancel-btn")
    def _btn_cancel(self) -> None:
        self._on_cancel()
