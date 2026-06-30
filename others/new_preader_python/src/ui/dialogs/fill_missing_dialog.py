"""
补缺弹窗 —— 两阶段模式：爬取 → 分组合并确认
阶段1：爬取新书籍内容
阶段2：多选书籍 + 分配到前/中/后三组 + 独立位置控制 + 预览搜索 + 执行合并
"""

import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, ClassVar, List, Set

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Button, Label, Input, Select,
    Static, DataTable,
)
from textual import on
from textual import events

from src.locales.i18n_manager import get_global_i18n
from src.utils.logger import get_logger
from src.utils.visual_merge_helper import VisualMergeHelper

logger = get_logger(__name__)


class FillMissingDialog(ModalScreen[Dict[str, Any]]):
    """可复用的补缺弹窗 - 支持多文件分组分配合并"""

    CSS_PATH = "../styles/fill_missing_dialog.tcss"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "cancel", get_global_i18n().t('common.close')),
        ("s", "toggle_crawl", get_global_i18n().t('crawler.toggle_crawl')),
        ("e", "toggle_monitor", get_global_i18n().t('crawler.toggle_monitor')),
        ("/", "search_preview", get_global_i18n().t('fill_missing.search_key')),
        ("a", "toggle_select_all", get_global_i18n().t('fill_missing.toggle_select_shortcut')),
        ("space", "toggle_row", get_global_i18n().t('fill_missing.toggle_row_shortcut')),
        ("v", "visual_merge", get_global_i18n().t('fill_missing.visual_merge_btn')),
    ]

    # 预览最大行数（避免超大文件导致性能问题）
    PREVIEW_MAX_LINES: int = 500
    PREVIEW_CONTEXT_LINES: int = 5

    # 预览区内容列的基础宽度（会根据终端宽度动态调整）
    PREVIEW_CONTENT_BASE_WIDTH: int = 100

    # 分组键
    GROUP_FRONT = "front"
    GROUP_MIDDLE = "middle"
    GROUP_BACK = "back"

    def __init__(
        self,
        theme_manager,
        novel_site: Dict[str, Any],
        target_book: Optional[Dict[str, Any]] = None,
        db_manager=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme_manager = theme_manager
        self.i18n = get_global_i18n()
        self.novel_site = novel_site or {}
        self.target_book = target_book or {}
        self.db_manager = db_manager

        self._stage: str = "crawl"

        # 爬取状态
        self.is_crawling: bool = False
        self.current_task_id: Optional[str] = None
        self.selected_browser: str = "chrome"
        self.selected_window_index: Optional[int] = None
        self.window_options: List[Dict[str, Any]] = []
        self.browser_monitor = None
        self.browser_monitor_active: bool = False
        self._crawler_manager = None
        self._crawling_novel_ids: List[str] = []

        # 合并状态 - 多分组
        self._crawled_books: List[Dict[str, Any]] = []
        self._selected_indices: Set[int] = set()  # 当前选中的书籍索引（在列表中的原始位置）
        # 三个插入组: {group_key -> {"books": [原始索引列表], "line": Optional[int]}}
        self._insert_groups: Dict[str, Dict[str, Any]] = {
            self.GROUP_FRONT: {"books": [], "line": None},
            self.GROUP_MIDDLE: {"books": [], "line": None},
            self.GROUP_BACK: {"books": [], "line": None},
        }
        self._target_lines: List[str] = []  # 目标文件按行分割的内容

        # ── 搜索导航状态 ──
        self._search_matches: List[int] = []  # 匹配的行号列表
        self._search_current_match: int = -1  # 当前显示的匹配索引（0-based，-1=无）
        self._current_search_keyword: str = ""  # 当前的搜索关键词

    # ─── Compose ────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        title = self.target_book.get('novel_title', '') or ''
        novel_id = str(self.target_book.get('novel_id', '')) or ''
        status = self.target_book.get('status', '') or ''
        book_info = f"{title}  |  ID: {novel_id}  |  {status}"

        yield Container(
            Vertical(
                Label(f"  {self.i18n.t('fill_missing.title')}  ", id="fm-title"),
                Static(book_info, id="fm-book-info"),

                # ═══ 顶部：爬取操作行（始终可见，可继续爬取）═══
                Horizontal(
                    *([Button(self.i18n.t('crawler.select_books'), id="fm-choose-books-btn")]
                      if self.novel_site.get("selectable_enabled", True) else []),
                    Input(placeholder=self.i18n.t('crawler.novel_id_placeholder_multi'), id="fm-novel-id-input"),
                    Button(self.i18n.t('crawler.start_crawl'), id="fm-toggle-crawl-btn", variant="primary"),
                    Button(self.i18n.t('crawler.copy_ids'), id="fm-copy-ids-btn"),
                    Button(self.i18n.t('crawler.toggle_monitor'), id="fm-toggle-monitor-btn", variant="success"),
                    Select(id="fm-browser-select",
                        options=[(self.i18n.t('crawler.browser_label'), "chrome"), ("Chrome", "chrome"), ("Safari", "safari"), ("Brave", "brave")],
                        value="chrome",
                    ),
                    Select(id="fm-window-select", options=[(self.i18n.t('crawler.all_windows'), "all")], value="all"),
                    Button(self.i18n.t('crawler.refresh_windows'), id="fm-refresh-window-btn"),
                    id="fm-fill-row",
                ),

                # ═══ 中部：左右分栏（书籍选择 | 分组结果）═══
                Horizontal(
                    # 左侧：新爬取书籍 DataTable + 操作按钮
                    Vertical(
                        Label(self.i18n.t('fill_missing.new_books_label'), id="fm-new-books-label"),
                        DataTable(id="fm-books-table"),
                        # 选择+分配按钮行
                        Horizontal(
                            Button(self.i18n.t('fill_missing.select_all'), id="fm-select-all-btn", variant="default"),
                            Button(self.i18n.t('fill_missing.assign_front'), id="fm-assign-front-btn", variant="success"),
                            Button(self.i18n.t('fill_missing.assign_middle'), id="fm-assign-middle-btn", variant="warning"),
                            Button(self.i18n.t('fill_missing.assign_back'), id="fm-assign-back-btn", variant="primary"),
                            id="fm-sel-ops-row",
                        ),
                        id="fm-left-panel",
                    ),

                    # 右侧：分组显示 + 行号输入
                    Vertical(
                        Label(self.i18n.t('fill_missing.group_plan'), id="fm-group-plan-label"),
                        Static("", id="fm-group-display", classes="group-display"),
                        # 中间组的行号输入 + 快速定位
                        Horizontal(
                            Label(f"{self.i18n.t('fill_missing.middle_line')}:", classes="label-text"),
                            Input(placeholder=self.i18n.t('fill_missing.line_placeholder'), id="fm-middle-line-input"),
                            Button(self.i18n.t('fill_missing.preview_btn'), id="fm-middle-preview-btn"),
                            Select(
                                id="fm-quick-pos-select",
                                options=[
                                    (self.i18n.t('fill_missing.quick_pos_hint'), ""),
                                    (self.i18n.t('fill_missing.quick_pos_beginning'), "beginning"),
                                    (self.i18n.t('fill_missing.quick_pos_middle'), "middle"),
                                    (self.i18n.t('fill_missing.quick_pos_end'), "end"),
                                ],
                                value="",
                            ),
                            id="fm-middle-line-row",
                        ),
                        id="fm-right-top-panel",
                    ),
                    id="fm-main-split",
                ),

                # 搜索+预览区（含导航按钮）
                Horizontal(
                    Input(placeholder=self.i18n.t('fill_missing.search_placeholder'), id="fm-search-input"),
                    Button(self.i18n.t('fill_missing.search_btn'), id="fm-search-btn"),
                    Button("◀", id="fm-search-prev-btn", variant="default"),
                    Label("", id="fm-search-match-label", classes="label-text"),
                    Button("▶", id="fm-search-next-btn", variant="default"),
                    Button(self.i18n.t('fill_missing.set_as_insert_pos'), id="fm-set-insert-pos-btn", variant="warning"),
                    Button(self.i18n.t('fill_missing.load_preview_btn'), id="fm-load-preview-btn"),
                    Button(self.i18n.t('fill_missing.visual_merge_btn'), id="fm-visual-merge-btn", variant="success"),
                    id="fm-search-row",
                ),
                # 预览区（DataTable，支持点击行号设为插入位置）
                DataTable(id="fm-preview-content"),

                # 底部：新书名 + 合并按钮 + 取消
                Horizontal(
                    Label(self.i18n.t('fill_missing.new_name') + ": ", classes="label-text"),
                    Input(id="fm-new-name-input", value=title),
                    Button(self.i18n.t('fill_missing.confirm_merge'), id="fm-confirm-btn", variant="primary"),
                    Button(self.i18n.t('common.cancel'), id="fm-cancel-btn", variant="error"),
                    id="fm-rename-row",
                ),

                Label("", id="fm-status"),

                Horizontal(
                    id="fm-buttons",
                ),
                id="fm-container",
            )
        )
        yield Footer()

    # ─── Mount ──────────────────────────────────────────────

    def on_mount(self) -> None:
        self.theme_manager.apply_theme_to_screen(self)
        try:
            input_widget = self.query_one("#fm-novel-id-input", Input)
            input_widget.focus()
        except Exception:
            pass

    # ─── 阶段切换 ──────────────────────────────────────────

    def _switch_to_merge_stage(self) -> None:
        """进入合并模式：填充数据并初始化显示（单屏模式，无需切换面板）"""
        try:
            self._stage = "merge"
            logger.info("进入合并模式")
            self._populate_merge_data()
            # 自动加载目标文件预览
            self._load_target_preview()

        except Exception as e:
            logger.error(f"进入合并模式失败: {e}")

    def _switch_to_crawl_stage(self) -> None:
        """返回爬取模式（单屏模式下仅重置状态）"""
        self._stage = "crawl"
        self._update_status_text(self.i18n.t('fill_missing.returned_to_crawl'))

    # ─── 数据填充与显示更新 ───────────────────────────────

    def _populate_merge_data(self) -> None:
        """填充合并预览数据"""
        try:
            # 目标书籍摘要 — 更新到状态栏（单屏模式不再有独立区域）
            t_title = self.target_book.get('novel_title', '') or ''
            t_file = self.target_book.get('file_path', '') or ''
            has_content = os.path.exists(t_file) and os.path.getsize(t_file) > 0 if t_file else False
            summary = f"{self.i18n.t('fill_missing.target')}: {t_title}"
            if has_content:
                size_kb = os.path.getsize(t_file) / 1024
                total_lines = sum(1 for _ in open(t_file, 'r', encoding='utf-8'))
                summary += f"  ({size_kb:.1f} KB / {total_lines} {self.i18n.t('fill_missing.lines')})"
            else:
                summary += f"  ({self.i18n.t('fill_missing.no_file_or_empty')})"
            self._update_status_text(summary)

            # 新爬取的书籍列表（带复选标记）
            self._refresh_books_list_display()

            # 刷新分组显示
            self._refresh_group_display()

            # 默认新书名建议
            name_input = self.query_one("#fm-new-name-input", Input)
            if not name_input.value.strip():
                suggested = self._suggest_merged_name()
                if suggested:
                    name_input.value = suggested
        except Exception as e:
            logger.error(f"填充合并数据失败: {e}")

    def _refresh_books_list_display(self, restore_cursor: bool = True, target_cursor: int = -1) -> None:
        """刷新新爬取书籍列表显示（DataTable），标注选中状态和已分配状态"""
        try:
            table = self.query_one("#fm-books-table", DataTable)

            # 保存当前光标位置（或使用指定的目标位置）
            if target_cursor >= 0:
                current_cursor = target_cursor
            else:
                current_cursor = table.cursor_row

            table.clear(columns=True)

            # 定义列（第一列为独立的选择状态列，参考爬取管理页面）
            table.add_column(get_global_i18n().t('batch_ops.selected'), key="selected", width=5)
            table.add_column("#", key="idx", width=4)
            table.add_column(self.i18n.t('fill_missing.col_title'), key="title", width=40)
            table.add_column(self.i18n.t('fill_missing.col_group'), key="group", width=4)

            if not self._crawled_books:
                return

            assigned_indices: Set[int] = set()
            for group_data in self._insert_groups.values():
                assigned_indices.update(group_data["books"])

            for i, book in enumerate(self._crawled_books):
                b_title = book.get('title', book.get('novel_title', ''))
                b_file = book.get('file_path', '')
                exists = os.path.exists(b_file) if b_file else False

                # 独立选中列
                is_selected = i in self._selected_indices
                sel_mark = "✓" if is_selected else ""

                # 分配状态
                group_mark = ""
                if i in assigned_indices:
                    for gkey, gdata in self._insert_groups.items():
                        if i in gdata["books"]:
                            glabel = {self.GROUP_FRONT: "F", self.GROUP_MIDDLE: "M", self.GROUP_BACK: "B"}.get(gkey, "?")
                            group_mark = f"[{glabel}]"
                            break

                status_tag = "" if exists else " ✗"

                row_key = str(i)
                table.add_row(
                    sel_mark,
                    str(i + 1),
                    f"{b_title}{status_tag}",
                    group_mark,
                    key=row_key,
                )

            # 恢复光标位置（仅当 restore_cursor=True 时）
            if restore_cursor and current_cursor is not None and 0 <= current_cursor < len(table.rows):
                if hasattr(table, 'move_cursor'):
                    table.move_cursor(row=current_cursor)

        except Exception as e:
            logger.error(f"刷新书籍列表显示失败: {e}")

    def _refresh_group_display(self) -> None:
        """刷新分组计划显示"""
        try:
            display_el = self.query_one("#fm-group-display", Static)
            lines = []
            total_assigned = 0

            # 前置组
            front_books = self._insert_groups[self.GROUP_FRONT]["books"]
            total_assigned += len(front_books)
            if front_books:
                titles = " → ".join([self._crawled_books[idx].get('title', self._crawled_books[idx].get('novel_title', f'#{idx+1}')) for idx in front_books])
                lines.append(f"  ├─ {self.i18n.t('fill_missing.group_front')}: {titles}")

            # 中间组
            mid_books = self._insert_groups[self.GROUP_MIDDLE]["books"]
            mid_line = self._insert_groups[self.GROUP_MIDDLE]["line"]
            total_assigned += len(mid_books)
            if mid_books:
                titles = " → ".join([self._crawled_books[idx].get('title', self._crawled_books[idx].get('novel_title', f'#{idx+1}')) for idx in mid_books])
                line_str = f"@{mid_line}" if mid_line is not None else "?"
                lines.append(f"  ├─ {self.i18n.t('fill_missing.group_middle')}({line_str}): {titles}")
                # 同步行号到输入框
                try:
                    line_input = self.query_one("#fm-middle-line-input", Input)
                    if mid_line is not None and line_input.value.strip() != str(mid_line):
                        line_input.value = str(mid_line)
                except Exception:
                    pass

            # 后置组
            back_books = self._insert_groups[self.GROUP_BACK]["books"]
            total_assigned += len(back_books)
            if back_books:
                titles = " → ".join([self._crawled_books[idx].get('title', self._crawled_books[idx].get('novel_title', f'#{idx+1}')) for idx in back_books])
                lines.append(f"  └─ {self.i18n.t('fill_missing.group_back')}: {titles}")

            unassigned = len(self._crawled_books) - total_assigned
            if not lines:
                lines.append(f"  ({self.i18n.t('fill_missing.no_group_yet')})")
            elif unassigned > 0:
                lines.append(f"\n  {self.i18n.t('fill_missing.unassigned_count').format(count=unassigned)}")

            display_el.update("\n".join(lines))
        except Exception as e:
            logger.error(f"刷新分组显示失败: {e}")

    def _suggest_merged_name(self) -> str:
        try:
            target_title = self.target_book.get('novel_title', '') or ''
            new_titles = [b.get('title', b.get('novel_title', '')) for b in self._crawled_books]
            all_titles = new_titles + [target_title]
            import re
            numbers = []
            for t in all_titles:
                match = re.search(r'(\d+)(?:\s*[-\u2013\u2014~]\s*(\d+))?', t)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else start
                    numbers.append((start, end))
            if len(numbers) >= 2:
                nums_sorted = sorted(set(n[0] for n in numbers) | set(n[1] for n in numbers))
                prefix = re.split(r'\d', target_title)[0].strip() if target_title else ''
                return f"{prefix}{nums_sorted[0]}-{nums_sorted[-1]}"
            return target_title
        except Exception:
            return self.target_book.get('novel_title', '') or ''

    # ─── 选择操作（全选/反选/分配）────────────────────────

    @on(Button.Pressed, "#fm-select-all-btn")
    def on_select_all_btn(self):
        """全选/取消全选按钮：切换"""
        self._toggle_select_all()

    def action_toggle_select_all(self):
        """快捷键 a: 全选/取消全选切换"""
        if self._stage == "merge":
            self._toggle_select_all()

    def _toggle_select_all(self):
        """内部实现：全选↔取消全选切换"""
        all_count = len(self._crawled_books)
        if len(self._selected_indices) >= all_count:
            # 已全选 → 取消全选
            self._selected_indices = set()
        else:
            # 未全选 → 全选
            self._selected_indices = set(range(all_count))
        self._refresh_books_list_display()
        # 更新按钮文字显示当前状态
        btn = self.query_one("#fm-select-all-btn", Button)
        if len(self._selected_indices) >= all_count:
            btn.label = self.i18n.t('fill_missing.deselect_all')
        else:
            btn.label = self.i18n.t('fill_missing.select_all')

    # ─── 数字键排序 + 快捷键（DataTable自带方向键导航） ──────

    def action_toggle_row(self) -> None:
        """空格键 - 选中或取消选中当前行"""
        if self._stage != "merge" or not self._crawled_books:
            return
        try:
            table = self.query_one("#fm-books-table", DataTable)
            cursor = table.cursor_row
            if cursor is not None and 0 <= cursor < len(self._crawled_books):
                if cursor in self._selected_indices:
                    self._selected_indices.discard(cursor)
                else:
                    self._selected_indices.add(cursor)
                self._refresh_books_list_display()
        except Exception as e:
            logger.debug(f"切换选中状态失败: {e}")

    def on_key(self, event: events.Key) -> None:
        """键盘事件：1-0 排序（空格已由 action_toggle_row 处理）"""
        if self._stage != "merge" or not self._crawled_books:
            return

        total = len(self._crawled_books)

        try:
            table = self.query_one("#fm-books-table", DataTable)
            cursor = table.cursor_row
        except Exception:
            return

        # 数字键 1-0 排序（0=第10位）
        if event.key in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"):
            target_pos = 9 if event.key == "0" else int(event.key) - 1
            if target_pos < total and cursor is not None and cursor >= 0 and cursor != target_pos:
                self._move_book_to_position(cursor, target_pos)
            event.stop()
            return

    def _move_book_to_position(self, from_idx: int, to_idx: int) -> None:
        """
        将书籍列表中 from_idx 位置的元素移动到 to_idx 位置。
        同时更新所有依赖原始索引的数据结构（选中集、分组）。
        """
        if from_idx < 0 or from_idx >= len(self._crawled_books):
            return
        to_idx = max(0, min(to_idx, len(self._crawled_books) - 1))

        # 1. 移动书籍
        book = self._crawled_books.pop(from_idx)
        self._crawled_books.insert(to_idx, book)

        # 2. 构建旧索引→新索引的映射（用于更新选中集和分组）
        old_indices = list(range(len(self._crawled_books)))
        new_indices = old_indices.copy()
        moved_val = new_indices.pop(from_idx)
        new_indices.insert(to_idx, moved_val)

        old_to_new = {old: new for old, new in zip(old_indices, new_indices)}

        # 3. 更新选中索引集合
        updated_selected = set()
        for idx in self._selected_indices:
            updated_selected.add(old_to_new.get(idx, idx))
        self._selected_indices = updated_selected

        # 4. 更新各分组中的书籍索引
        for gdata in self._insert_groups.values():
            updated_group_books = []
            for idx in gdata["books"]:
                updated_group_books.append(old_to_new.get(idx, idx))
            gdata["books"] = updated_group_books

        # 5. 刷新显示（光标跟随到新位置 to_idx）
        self._refresh_books_list_display(restore_cursor=False, target_cursor=to_idx)

        # 显示提示信息
        display_key = "0" if to_idx == 9 else str(to_idx + 1)
        book_title = book.get('title', book.get('novel_title', f'#{to_idx+1}'))
        self.notify(
            self.i18n.t('fill_missing.sort_moved').format(key=display_key, title=book_title),
            severity="information",
            timeout=2,
        )

    @on(Button.Pressed, "#fm-assign-front-btn")
    def on_assign_front(self):
        """将选中的书籍分配到前置组"""
        self._assign_selected_to_group(self.GROUP_FRONT)

    @on(Button.Pressed, "#fm-assign-middle-btn")
    def on_assign_middle(self):
        """将选中的书籍分配到中间组"""
        self._assign_selected_to_group(self.GROUP_MIDDLE)

    @on(Button.Pressed, "#fm-assign-back-btn")
    def on_assign_back(self):
        """将选中的书籍分配到后置组"""
        self._assign_selected_to_group(self.GROUP_BACK)

    def _assign_selected_to_group(self, group_key: str) -> None:
        """
        将当前选中的书籍分配到指定组。
        规则：
        - 如果书籍已在其他组，先移除再添加到目标组
        - 保持书籍在列表中的原始顺序
        - 添加到目标组的末尾
        """
        if not self._selected_indices:
            self.notify(self.i18n.t('fill_missing.no_selection_hint'), severity="warning", timeout=2)
            return

        selected_sorted = sorted(self._selected_indices)

        # 从所有其他组移除这些索引
        for gk, gv in self._insert_groups.items():
            if gk != group_key:
                gv["books"] = [idx for idx in gv["books"] if idx not in self._selected_indices]

        # 添加到目标组（保持顺序，追加到末尾）
        target_group = self._insert_groups[group_key]
        for idx in selected_sorted:
            if idx not in target_group["books"]:
                target_group["books"].append(idx)

        # 清空选择
        self._selected_indices.clear()

        # 刷新显示
        self._refresh_books_list_display()
        self._refresh_group_display()

        # 提示
        gname = {self.GROUP_FRONT: self.i18n.t('fill_missing.group_front'),
                 self.GROUP_MIDDLE: self.i18n.t('fill_missing.group_middle'),
                 self.GROUP_BACK: self.i18n.t('fill_missing.group_back')}.get(group_key, group_key)
        self.notify(self.i18n.t('fill_missing.assigned_msg').format(gname=gname, count=len(selected_sorted)), timeout=2)

    # ─── 中间组行号设置 ─────────────────────────────────────

    @on(Button.Pressed, "#fm-middle-preview-btn")
    def on_middle_preview(self):
        """预览中间组指定行号附近的内容"""
        try:
            line_input = self.query_one("#fm-middle-line-input", Input)
            raw_val = line_input.value.strip()
            if not raw_val:
                self.notify(self.i18n.t('fill_missing.enter_line_number'), severity="warning", timeout=2)
                return
            try:
                line_num = int(raw_val)
                if line_num < 0:
                    line_num = 1
                self._insert_groups[self.GROUP_MIDDLE]["line"] = line_num
                self._show_line_context(line_num)
            except ValueError:
                self.notify(self.i18n.t('fill_invalid_line_number'), severity="error", timeout=2)
        except Exception as e:
            logger.error(f"中间行预览失败: {e}")

    @on(Input.Submitted, "#fm-middle-line-input")
    def on_middle_line_submitted(self):
        """中间行号回车触发预览"""
        self.on_middle_preview()

    def _get_preview_content_width(self) -> int:
        """动态计算预览区内容列的最大可用宽度"""
        try:
            # 尝试获取应用/终端的实际宽度
            app_width = 120  # 默认值
            if self.app and hasattr(self.app, 'size') and self.app.size:
                app_width = self.app.size.width
            elif hasattr(self, 'size') and self.size:
                app_width = self.size.width

            # 减去行号列宽度（6）、边距（约10）、表格边框等
            content_width = max(60, app_width - 18)
            # 限制最大宽度，避免过宽影响布局
            return min(content_width, self.PREVIEW_CONTENT_BASE_WIDTH)
        except Exception:
            return self.PREVIEW_CONTENT_BASE_WIDTH

    def _show_line_context(self, line_num: int) -> None:
        """显示指定行的上下文内容到 DataTable"""
        if not self._target_lines:
            return
        try:
            table = self.query_one("#fm-preview-content", DataTable)
            table.clear(columns=True)

            content_width = self._get_preview_content_width()
            table.add_column("#", key="line_num", width=6)
            table.add_column(
                self.i18n.t('fill_missing.preview_content_col'),
                key="content",
                width=content_width,
            )

            start = max(1, line_num - self.PREVIEW_CONTEXT_LINES)
            end = min(len(self._target_lines), line_num + self.PREVIEW_CONTEXT_LINES)
            for i in range(start, end + 1):
                text = self._target_lines[i - 1].rstrip()
                row_str = str(i)
                if i == line_num:
                    row_str = f">>> {row_str}"
                table.add_row(row_str, text, key=str(i))
        except Exception as e:
            logger.error(f"显示行上下文失败: {e}")

    # ─── 搜索与预览 ─────────────────────────────────────────

    @on(Button.Pressed, "#fm-search-btn")
    def on_search(self):
        """在目标文件中搜索关键词"""
        try:
            search_input = self.query_one("#fm-search-input", Input)
            keyword = search_input.value.strip()
            if not keyword:
                self.notify(self.i18n.t('fill_missing.enter_search_keyword'), severity="warning", timeout=2)
                return
            self._do_search(keyword)
        except Exception as e:
            logger.error(f"搜索失败: {e}")

    @on(Button.Pressed, "#fm-load-preview-btn")
    def on_load_preview(self):
        """重新加载完整预览"""
        self._load_target_preview()

    @on(Button.Pressed, "#fm-visual-merge-btn")
    def on_visual_merge(self):
        """在浏览器中打开可视化拖拽补缺页面"""
        self._open_visual_merge()

    def _open_visual_merge(self) -> None:
        """启动浏览器可视化补缺工具"""
        try:
            # 确保有目标文件内容
            if not self._target_lines:
                t_file = self.target_book.get('file_path', '')
                if t_file and os.path.exists(t_file):
                    with open(t_file, 'r', encoding='utf-8') as f:
                        self._target_lines = f.readlines()
                else:
                    self.notify(self.i18n.t('fill_missing.no_target_for_visual'), severity="warning", timeout=3)
                    return

            helper = VisualMergeHelper.get_instance()

            # 定义回调：浏览器确认后更新分组数据
            def on_visual_result(data: Dict[str, Any]) -> None:
                self._apply_visual_merge_result(data)

            success = helper.open_visual_merge(
                target_file_path=self.target_book.get('file_path', ''),
                target_lines=self._target_lines,
                crawled_books=self._crawled_books,
                existing_groups={
                    "front": {"books": self._insert_groups[self.GROUP_FRONT]["books"], "line": None},
                    "middle": {"books": self._insert_groups[self.GROUP_MIDDLE]["books"], "line": self._insert_groups[self.GROUP_MIDDLE]["line"]},
                    "back": {"books": self._insert_groups[self.GROUP_BACK]["books"], "line": None},
                },
                callback=on_visual_result,
            )

            if success:
                self.notify(
                    self.i18n.t('fill_missing.visual_merge_opened'),
                    severity="information",
                    timeout=4,
                )
            else:
                self.notify(self.i18n.t('fill_missing.visual_merge_failed'), severity="error", timeout=3)

        except Exception as e:
            logger.error(f"打开可视化补缺失败: {e}")
            self.notify(f"{self.i18n.t('fill_missing.visual_merge_failed')}: {e}", severity="error", timeout=4)

    def _apply_visual_merge_result(self, data: Dict[str, Any]) -> None:
        """应用从浏览器返回的可视化补缺结果"""
        try:
            # 清空现有分组
            for gkey in (self.GROUP_FRONT, self.GROUP_MIDDLE, self.GROUP_BACK):
                self._insert_groups[gkey]["books"] = []

            # 应用前置区书籍
            front_books = data.get("front_books") or []
            for book in front_books:
                idx = book.get("index")
                if idx is not None and idx < len(self._crawled_books):
                    self._insert_groups[self.GROUP_FRONT]["books"].append(idx)

            # 应用中间区书籍 + 行号
            middle_books = data.get("middle_books") or []
            for book in middle_books:
                idx = book.get("index")
                if idx is not None and idx < len(self._crawled_books):
                    self._insert_groups[self.GROUP_MIDDLE]["books"].append(idx)
            mid_line = data.get("middle_line")
            if mid_line is not None:
                self._insert_groups[self.GROUP_MIDDLE]["line"] = int(mid_line)
                # 同步行号到输入框
                try:
                    line_input = self.query_one("#fm-middle-line-input", Input)
                    line_input.value = str(mid_line)
                except Exception:
                    pass
                # 高亮显示该行上下文
                self._show_line_context(int(mid_line))

            # 应用后置区书籍
            back_books = data.get("back_books") or []
            for book in back_books:
                idx = book.get("index")
                if idx is not None and idx < len(self._crawled_books):
                    self._insert_groups[self.GROUP_BACK]["books"].append(idx)

            # 应用新标题
            new_title = data.get("new_title")
            if new_title:
                try:
                    name_input = self.query_one("#fm-new-name-input", Input)
                    name_input.value = new_title
                except Exception:
                    pass

            # 刷新所有显示
            self._refresh_books_list_display()
            self._refresh_group_display()

            f_count = len(self._insert_groups[self.GROUP_FRONT]["books"])
            m_count = len(self._insert_groups[self.GROUP_MIDDLE]["books"])
            b_count = len(self._insert_groups[self.GROUP_BACK]["books"])

            self.notify(
                self.i18n.t('fill_missing.visual_merge_applied').format(
                    front=f_count, middle=m_count, back=b_count, line=mid_line or "-"
                ),
                severity="success",
                timeout=5,
            )
            logger.info(
                f"可视化补缺结果已应用: 前{f_count}+中{m_count}@L{mid_line or '?'}+后{b_count}"
            )
            
            # 自动执行合并
            self.app.call_later(self._execute_merge)

        except Exception as e:
            logger.error(f"应用可视化补缺结果失败: {e}", exc_info=True)
            self.notify(f"应用失败: {e}", severity="error", timeout=3)

    @on(Input.Submitted, "#fm-search-input")
    def on_search_submitted(self):
        """搜索框回车触发搜索"""
        self.on_search()

    def action_search_preview(self):
        """快捷键 / 触发搜索框聚焦"""
        try:
            search_input = self.query_one("#fm-search-input", Input)
            search_input.focus()
        except Exception:
            pass

    def _load_target_preview(self) -> None:
        """加载目标文件内容到预览区（DataTable）"""
        try:
            t_file = self.target_book.get('file_path', '')
            table = self.query_one("#fm-preview-content", DataTable)
            table.clear(columns=True)

            content_width = self._get_preview_content_width()

            if not t_file or not os.path.exists(t_file):
                table.add_column("#", key="line_num", width=6)
                table.add_column(
                    self.i18n.t('fill_missing.preview_content_col'),
                    key="content",
                    width=content_width,
                )
                table.add_row("?", f"  {self.i18n.t('fill_missing.file_not_found_for_preview')}", key="err")
                self._target_lines = []
                return

            with open(t_file, 'r', encoding='utf-8') as f:
                self._target_lines = f.readlines()

            # 定义列（动态宽度）
            table.add_column("#", key="line_num", width=6)
            table.add_column(
                self.i18n.t('fill_missing.preview_content_col'),
                key="content",
                width=content_width,
            )

            total = len(self._target_lines)
            display_count = min(total, self.PREVIEW_MAX_LINES)
            for i in range(display_count):
                line_text = self._target_lines[i].rstrip()
                row_key = str(i + 1)  # 用行号作为 key
                table.add_row(str(i + 1), line_text, key=row_key)

            if total > self.PREVIEW_MAX_LINES:
                table.add_row(
                    "",
                    f"  ... {self.i18n.t('fill_missing.more_lines').format(more=total - self.PREVIEW_MAX_LINES)}",
                    key="more",
                )

        except Exception as e:
            logger.error(f"加载预览失败: {e}")
            try:
                table = self.query_one("#fm-preview-content", DataTable)
                table.clear(columns=True)
                content_width = self._get_preview_content_width()
                table.add_column("#", key="line_num", width=6)
                table.add_column(
                    self.i18n.t('fill_missing.preview_content_col'),
                    key="content",
                    width=content_width,
                )
                table.add_row("?", f"  Error: {e}", key="err")
            except Exception:
                pass
            self._target_lines = []

    def _do_search(self, keyword: str) -> None:
        """执行搜索，保存全部匹配结果，显示当前匹配项"""
        if not self._target_lines:
            self._load_target_preview()

        # 搜索全部匹配
        keyword_lower = keyword.lower()
        matches = []
        for idx, line in enumerate(self._target_lines):
            if keyword_lower in line.lower():
                matches.append(idx + 1)  # 1-based 行号

        self._search_matches = matches
        self._current_search_keyword = keyword

        if not matches:
            self._search_current_match = -1
            self._update_search_nav_ui()
            self._update_status_text(self.i18n.t('fill_missing.no_match'))
            return

        # 默认显示第一个匹配
        self._search_current_match = 0
        self._display_current_search_result()

    def _display_current_search_result(self) -> None:
        """显示当前搜索结果的上下文到 DataTable（带导航状态）"""
        if not self._search_matches or self._search_current_match < 0 or self._search_current_match >= len(self._search_matches):
            return

        line_num = self._search_matches[self._search_current_match]
        table = self.query_one("#fm-preview-content", DataTable)
        table.clear(columns=True)

        total = len(self._search_matches)
        kw = self._current_search_keyword or ""
        content_width = self._get_preview_content_width()

        # 表头行作为状态提示（动态宽度）
        table.add_column("#", key="line_num", width=6)
        table.add_column(
            self.i18n.t('fill_missing.preview_content_col'),
            key="content",
            width=content_width,
        )

        # 状态行
        status_text = f"🔍 {self.i18n.t('fill_missing.search_result_nav').format(current=self._search_current_match + 1, total=total, kw=kw)}"
        table.add_row("", status_text, key="status")

        # 上下文行
        start = max(0, line_num - self.PREVIEW_CONTEXT_LINES)
        end = min(len(self._target_lines), line_num + self.PREVIEW_CONTEXT_LINES)
        for i in range(start, end):
            line_text = self._target_lines[i].rstrip()
            row_num_str = str(i + 1)
            if i == line_num - 1:
                row_num_str = f">>> {row_num_str}"
            table.add_row(row_num_str, line_text, key=str(i + 1))

        # 自动填入中间组行号
        self._insert_groups[self.GROUP_MIDDLE]["line"] = line_num
        try:
            line_input = self.query_one("#fm-middle-line-input", Input)
            line_input.value = str(line_num)
        except Exception:
            pass

        # 更新导航按钮状态和标签
        self._update_search_nav_ui()

    def _update_search_nav_ui(self) -> None:
        """更新搜索导航 UI（标签文字、按钮可用状态）"""
        try:
            label = self.query_one("#fm-search-match-label", Label)
            prev_btn = self.query_one("#fm-search-prev-btn", Button)
            next_btn = self.query_one("#fm-search-next-btn", Button)
            set_pos_btn = self.query_one("#fm-set-insert-pos-btn", Button)

            total = len(self._search_matches)
            if total > 0 and 0 <= self._search_current_match < total:
                label.update(f"{self._search_current_match + 1}/{total}")
                prev_btn.disabled = (self._search_current_match <= 0)
                next_btn.disabled = (self._search_current_match >= total - 1)
                set_pos_btn.disabled = False
            else:
                label.update("")
                prev_btn.disabled = True
                next_btn.disabled = True
                set_pos_btn.disabled = True
        except Exception:
            pass

    # ─── 搜索导航按钮事件 ─────────────────────────────────

    @on(Button.Pressed, "#fm-search-prev-btn")
    def on_search_prev(self):
        """上一条搜索结果"""
        if self._search_current_match > 0:
            self._search_current_match -= 1
            self._display_current_search_result()

    @on(Button.Pressed, "#fm-search-next-btn")
    def on_search_next(self):
        """下一条搜索结果"""
        if self._search_matches and self._search_current_match < len(self._search_matches) - 1:
            self._search_current_match += 1
            self._display_current_search_result()

    @on(Button.Pressed, "#fm-set-insert-pos-btn")
    def on_set_insert_pos(self):
        """将当前搜索结果行号设为中间组插入位置（并提示确认）"""
        if not self._search_matches or self._search_current_match < 0 or self._search_current_match >= len(self._search_matches):
            return
        line_num = self._search_matches[self._search_current_match]
        self._insert_groups[self.GROUP_MIDDLE]["line"] = line_num
        try:
            line_input = self.query_one("#fm-middle-line-input", Input)
            line_input.value = str(line_num)
        except Exception:
            pass
        self.notify(
            self.i18n.t('fill_missing.insert_pos_set').format(line=line_num),
            severity="information",
            timeout=2,
        )

    # ─── 预览 DataTable 行点击事件 ─────────────────────────

    @on(DataTable.RowSelected, "#fm-preview-content")
    def on_preview_row_selected(self, event: DataTable.RowSelected) -> None:
        """点击预览区行号 → 自动填入中间组插入位置"""
        try:
            row_key = str(event.row_key.value) if event.row_key else ""
            if not row_key or not row_key.isdigit():
                return
            line_num = int(row_key)
            if line_num < 1:
                return

            # 设为中间组行号
            self._insert_groups[self.GROUP_MIDDLE]["line"] = line_num
            line_input = self.query_one("#fm-middle-line-input", Input)
            line_input.value = str(line_num)

            # 高亮提示
            self.notify(
                self.i18n.t('fill_missing.preview_line_clicked').format(line=line_num),
                severity="information",
                timeout=2,
            )
        except Exception as e:
            logger.debug(f"预览行点击处理失败: {e}")

    # ─── 快速定位 Select ──────────────────────────────────────

    @on(Select.Changed, "#fm-quick-pos-select")
    def on_quick_pos_changed(self, event: Select.Changed):
        """快速定位下拉框：开头 / 中间(50%) / 末尾"""
        if not self._target_lines or event.value is None or not event.value:
            return
        total_lines = len(self._target_lines)
        pos = event.value  # "beginning" | "middle" | "end"
        if pos == "beginning":
            target = 1
        elif pos == "middle":
            target = max(1, total_lines // 2)
        elif pos == "end":
            target = max(1, total_lines)
        else:
            return

        self._insert_groups[self.GROUP_MIDDLE]["line"] = target
        try:
            line_input = self.query_one("#fm-middle-line-input", Input)
            line_input.value = str(target)
        except Exception:
            pass
        # 显示该位置的上下文预览
        self._show_line_context(target)
        self.notify(
            self.i18n.t('fill_missing.quick_pos_applied').format(pos=pos, line=target),
            severity="information",
            timeout=2,
        )
        # 重置下拉框为空白状态，避免下次误操作
        try:
            sel = self.query_one("#fm-quick-pos-select", Select)
            sel.value = ""
        except Exception:
            pass

    # ─── CrawlerManager ─────────────────────────────────────

    def _get_crawler_manager(self):
        if self._crawler_manager is None:
            try:
                from src.core.crawler_manager import CrawlerManager
                self._crawler_manager = CrawlerManager()
                self._crawler_manager.register_status_callback(self._on_crawl_status_change)
                self._crawler_manager.register_notification_callback(self._on_crawl_success_notify)
            except Exception as e:
                logger.error(f"初始化 CrawlerManager 失败: {e}")
        return self._crawler_manager

    # ─── 爬取状态回调 ─────────────────────────────────────

    def _on_crawl_status_change(self, task_id: str, task: Any) -> None:
        try:
            from src.core.crawler_manager import CrawlStatus
            if task_id != self.current_task_id:
                return
            if task.status in (CrawlStatus.COMPLETED, CrawlStatus.FAILED, CrawlStatus.STOPPED):
                self.is_crawling = False
                self.current_task_id = None
                if task.status == CrawlStatus.COMPLETED:
                    self.app.call_later(self._on_crawl_completed)
                    self.app.call_later(self._check_and_continue_crawl)
                elif task.status == CrawlStatus.FAILED:
                    self.app.call_later(self.notify, self.i18n.t('crawler.crawl_failed'), severity="error", timeout=3)
                    self.app.call_later(self._update_crawl_button_state)
        except Exception as e:
            logger.error(f"爬取状态回调失败: {e}")

    def _on_crawl_completed(self) -> None:
        try:
            self._update_crawl_button_state()
            self.notify(self.i18n.t('crawler.crawl_success'), timeout=3)
            novel_id_input = self.query_one("#fm-novel-id-input", Input)
            remaining = novel_id_input.value.strip()
            if not remaining:
                # 输入框为空，收集所有已爬取书籍并进入合并模式
                count = self._collect_crawled_books(reset=False)
                if self._crawled_books:
                    self._switch_to_merge_stage()
                    name_input = self.query_one("#fm-new-name-input", Input)
                    if not name_input.value.strip():
                        suggested = self._suggest_merged_name()
                        if suggested:
                            name_input.value = suggested
                else:
                    self._update_status_text(self.i18n.t('fill_missing.no_valid_new_files'))
            else:
                # 还有剩余 ID，增量收集当前已完成的书籍到表格
                count = self._collect_crawled_books(reset=False)
                self._update_status_text(
                    f"{self.i18n.t('fill_missing.crawl_completed')}  |  {self.i18n.t('fill_missing.books_in_table').format(count=len(self._crawled_books))}"
                )
        except Exception as e:
            logger.error(f"爬取完成回调失败: {e}")

    def _collect_crawled_books(self, reset: bool = False) -> int:
        """
        从爬取历史中收集已成功爬取的书籍并追加到列表。
        单屏模式下支持增量追加（不重置已有数据）。
        返回本次新收集的数量。
        """
        if not self.db_manager or not self._crawling_novel_ids:
            return 0

        if reset:
            self._crawled_books = []
            self._selected_indices = set()
            self._insert_groups = {
                self.GROUP_FRONT: {"books": [], "line": None},
                self.GROUP_MIDDLE: {"books": [], "line": None},
                self.GROUP_BACK: {"books": [], "line": None},
            }

        existing_nids = {b['novel_id'] for b in self._crawled_books}
        added_count = 0

        try:
            site_id = self.novel_site.get('id')
            if not site_id:
                return 0

            for nid in self._crawling_novel_ids:
                if nid in existing_nids:
                    continue  # 已在列表中，跳过
                records = self.db_manager.get_crawl_history_by_site(site_id, limit=20)
                if records:
                    for rec in reversed(records):
                        if str(rec.get('novel_id', '')) == nid \
                                and rec.get('status') == 'success' \
                                and rec.get('file_path'):
                            fp = rec.get('file_path', '')
                            if fp and os.path.exists(fp):
                                self._crawled_books.append({
                                    'novel_id': nid,
                                    'title': rec.get('novel_title', nid),
                                    'file_path': fp,
                                    'record_id': rec.get('id'),
                                })
                                existing_nids.add(nid)
                                added_count += 1
                            break

            logger.info(f"收集到 {len(self._crawled_books)} 本有效的新爬取书籍（本轮新增 {added_count} 本）")

            # 刷新 DataTable 显示
            if self._crawled_books:
                self._refresh_books_list_display()
                self._refresh_group_display()

            return added_count

        except Exception as e:
            logger.error(f"收集已爬取书籍失败: {e}")
            return 0

    def _check_and_continue_crawl(self) -> None:
        try:
            if self.is_crawling:
                return
            novel_id_input = self.query_one("#fm-novel-id-input", Input)
            novel_ids_input = novel_id_input.value.strip()
            if not novel_ids_input:
                return
            from urllib.parse import unquote
            novel_ids = [unquote(id.strip()) for id in novel_ids_input.split(',') if id.strip()]
            if not novel_ids:
                return
            logger.info(f"检测到输入框中还有 {len(novel_ids)} 个书籍ID，自动继续爬取")
            self.app.call_later(self._start_crawl)
        except Exception as e:
            logger.error(f"检查并继续爬取失败: {e}")

    def _on_crawl_success_notify(self, task_id: str, novel_id: str, novel_title: str, already_exists: bool) -> None:
        try:
            self.app.call_later(self._remove_id_from_input, novel_id)
            self.app.call_later(self.notify, f"{self.i18n.t('crawler.crawl_success')}: {novel_title}", timeout=2)
            # 每完成一本，立即收集并刷新到 DataTable
            if not already_exists:
                self.app.call_later(lambda: self._collect_single_book(novel_id, novel_title))
        except Exception:
            pass

    def _collect_single_book(self, novel_id: str, novel_title: str = '') -> None:
        """收集单本已完成爬取的书籍并立即刷新表格"""
        try:
            site_id = self.novel_site.get('id')
            if not site_id or not self.db_manager:
                return

            # 检查是否已在列表中
            existing_nids = {b['novel_id'] for b in self._crawled_books}
            if novel_id in existing_nids:
                return

            records = self.db_manager.get_crawl_history_by_site(site_id, limit=20)
            if not records:
                return
            for rec in reversed(records):
                if (str(rec.get('novel_id', '')) == novel_id
                        and rec.get('status') == 'success'
                        and rec.get('file_path')):
                    fp = rec.get('file_path', '')
                    if fp and os.path.exists(fp):
                        self._crawled_books.append({
                            'novel_id': novel_id,
                            'title': rec.get('novel_title', novel_title),
                            'file_path': fp,
                            'record_id': rec.get('id'),
                        })
                        logger.info(f"单本收集成功: {novel_title} ({novel_id})，当前共 {len(self._crawled_books)} 本")
                        # 立即刷新 DataTable
                        self._refresh_books_list_display()
                    break
        except Exception as e:
            logger.debug(f"单本收集失败: {e}")

    def _remove_id_from_input(self, novel_id: str) -> None:
        try:
            from urllib.parse import unquote
            decoded_id = unquote(novel_id)
            inp = self.query_one("#fm-novel-id-input", Input)
            current = inp.value.strip()
            ids = [unquote(id.strip()) for id in current.split(',') if id.strip()]
            filtered = [id for id in ids if id != decoded_id]
            inp.value = ', '.join(filtered) + ',' if filtered else ''
            inp.action_end()
        except Exception as e:
            logger.debug(f"移除ID失败: {e}")

    # ─── 智能预检：复用已爬取记录 ────────────────────────────

    def _precheck_existing_crawls(self, novel_ids: List[str]) -> tuple:
        """
        检查每个ID是否已有成功的爬取记录且文件存在。
        返回 (cached_books_info, uncached_ids)：
          - cached_books_info: 已缓存的书籍信息列表（可直接加入 _crawled_books）
          - uncached_ids: 需要实际爬取的 ID 列表
        """
        cached = []
        need_crawl = []
        if not self.db_manager or not novel_ids:
            return [], list(novel_ids)

        site_id = self.novel_site.get('id')
        if not site_id:
            return [], list(novel_ids)

        # 已有ID集合，避免重复添加
        existing_nids = {str(b.get('novel_id', '')) for b in self._crawled_books}

        try:
            all_history = self.db_manager.get_crawl_history_by_site(site_id, limit=200)
            if not all_history:
                return [], list(novel_ids)

            # 构建 novel_id → 最新成功记录的映射
            nid_to_record = {}
            for rec in reversed(all_history):
                if rec.get('status') != 'success' or not rec.get('file_path'):
                    continue
                nid = str(rec.get('novel_id', ''))
                if nid and nid not in nid_to_record:
                    nid_to_record[nid] = rec

            for nid in novel_ids:
                if nid in existing_nids or nid in [b['novel_id'] for b in cached]:
                    continue  # 已处理过，跳过
                rec = nid_to_record.get(nid)
                if rec:
                    fp = rec.get('file_path', '')
                    if fp and os.path.exists(fp):
                        cached.append({
                            'novel_id': nid,
                            'title': rec.get('novel_title', nid),
                            'file_path': fp,
                            'record_id': rec.get('id'),
                        })
                        self.notify(
                            self.i18n.t('fill_missing.cached_found').format(title=rec.get('novel_title', nid)),
                            severity="information",
                            timeout=2,
                        )
                        logger.info(f"智能预检: ID {nid} 已有爬取记录，直接复用")
                    else:
                        need_crawl.append(nid)
                else:
                    need_crawl.append(nid)

            # 将缓存的结果追加到 _crawled_books 并立即刷新表格
            if cached:
                self._crawled_books.extend(cached)
                for b in cached:
                    existing_nids.add(b['novel_id'])
                # 立即刷新 DataTable 显示
                self._refresh_books_list_display()

            return cached, need_crawl

        except Exception as e:
            logger.error(f"智能预检失败: {e}")
            return [], list(novel_ids)

    # ─── 爬取控制 ─────────────────────────────────────────

    def _update_crawl_button_state(self) -> None:
        try:
            btn = self.query_one("#fm-toggle-crawl-btn", Button)
            if self.is_crawling:
                btn.label = self.i18n.t('crawler.stop_crawl'); btn.variant = "error"
            else:
                btn.label = self.i18n.t('crawler.start_crawl'); btn.variant = "primary"
        except Exception: pass

    def _start_crawl(self) -> None:
        if not self.novel_site:
            self.notify(self.i18n.t('crawler.no_site_id'), severity="warning", timeout=2); return
        if self.is_crawling: self._stop_crawl(); return
        try:
            novel_id_input = self.query_one("#fm-novel-id-input", Input)
            ids_input = novel_id_input.value.strip()
            if not ids_input:
                self.notify(self.i18n.t('crawler.enter_novel_id'), severity="warning", timeout=2); return
            from urllib.parse import unquote
            novel_ids = [unquote(id.strip()) for id in ids_input.split(',') if id.strip()]
            site_id = self.novel_site.get('id')
            if not site_id:
                self.notify(self.i18n.t('crawler.no_site_id'), severity="warning", timeout=2); return

            # ── 智能预检：过滤已爬取成功的ID，直接复用 ──
            cached_ids, uncached_ids = self._precheck_existing_crawls(novel_ids)

            # 从输入框移除已缓存的ID（避免重复处理）
            for cid in cached_ids:
                self.app.call_later(self._remove_id_from_input, cid)

            if not uncached_ids:
                # 全部已有记录，直接进入合并阶段
                if cached_ids:
                    self._update_status_text(
                        self.i18n.t('fill_missing.all_already_crawled').format(count=len(cached_ids))
                    )
                    self._switch_to_merge_stage()
                else:
                    self.notify(self.i18n.t('crawler.enter_novel_id'), severity="warning", timeout=2)
                return

            proxy_config = {'enabled': False, 'proxy_url': ''}
            try:
                proxy_enabled = self.novel_site.get('proxy_enabled', False)
                if proxy_enabled and self.db_manager:
                    ep = self.db_manager.get_enabled_proxy()
                    if ep:
                        pt = ep.get('type', 'HTTP').lower(); h = ep.get('host', ''); p = ep.get('port', ''); u = ep.get('username', ''); pw = ep.get('password', '')
                        if h and p:
                            proxy_config = {'enabled': True, 'proxy_url': f"{pt}://{u}:{pw}@{h}:{p}" if u and pw else f"{pt}://{h}:{p}"}
            except Exception: pass

            cm = self._get_crawler_manager()
            if not cm:
                self.notify(self.i18n.t('crawler.start_crawl_failed'), severity="error", timeout=3); return
            self.is_crawling = True
            if not self._crawling_novel_ids:
                self._crawling_novel_ids = list(uncached_ids)
            else:
                self._crawling_novel_ids.extend(uncached_ids)
            task_id = cm.start_crawl_task(site_id, uncached_ids, proxy_config)
            if task_id:
                self.current_task_id = task_id
                self._update_crawl_button_state()
                hint_msg = ""
                if cached_ids:
                    hint_msg = f" | {self.i18n.t('fill_missing.cached_skip_hint').format(count=len(cached_ids))}"
                self._update_status_text(f"{self.i18n.t('crawler.starting_crawl')} ({len(uncached_ids)} {self.i18n.t('crawler.books')}{hint_msg})")
            else:
                self.is_crawling = False
                self.notify(self.i18n.t('crawler.start_crawl_failed'), severity="error", timeout=3)
        except Exception as e:
            self.is_crawling = False
            logger.error(f"启动爬取失败: {e}")
            self.notify(f"{self.i18n.t('crawler.start_crawl_failed')}: {e}", severity="error", timeout=3)

    def _stop_crawl(self) -> None:
        try:
            if self.current_task_id and self._crawler_manager:
                self._crawler_manager.stop_crawl_task(self.current_task_id)
            self.is_crawling = False; self.current_task_id = None
            self._update_crawl_button_state()
            self.notify(self.i18n.t('crawler.crawl_stopped'), timeout=2)
        except Exception as e:
            logger.error(f"停止爬取失败: {e}")

    # ─── 浏览器监听 ─────────────────────────────────────────

    def _init_browser_monitor(self) -> None:
        if not self.novel_site: return
        try:
            from src.utils.browser_tab_monitor import BrowserTabMonitor, BrowserType
            bt_map = {"safari": BrowserType.SAFARI, "brave": BrowserType.BRAVE}
            bt = bt_map.get(self.selected_browser, BrowserType.CHROME)
            self.browser_monitor = BrowserTabMonitor(
                novel_sites=[self.novel_site], on_url_detected=self._on_browser_url_detected,
                headless=False, browser_type=bt,
            )
            self.browser_monitor.selected_window_index = self.selected_window_index  # type: ignore
            self.browser_monitor.on_window_refresh_callback = self._on_window_refresh_from_monitor  # type: ignore
            self._refresh_window_options()
        except Exception as e:
            logger.error(f"初始化浏览器监听器失败: {e}")
            self.browser_monitor = None

    def _on_browser_url_detected(self, novel_info: Dict[str, Any]) -> None:
        try:
            novel_id = novel_info.get('novel_id', '') if isinstance(novel_info, dict) else str(novel_info)
            url = novel_info.get('url', '') if isinstance(novel_info, dict) else ''
            if novel_id:
                self.app.call_later(self._append_detected_id, novel_id)
            if url and self.browser_monitor:
                try: self.browser_monitor.close_tab(url)
                except Exception: pass
        except Exception as e:
            logger.error(f"URL检测回调失败: {e}")

    def _append_detected_id(self, novel_id: str) -> None:
        try:
            inp = self.query_one("#fm-novel-id-input", Input)
            existing = inp.value.strip()
            parts = [p.strip() for p in existing.split(',')] if existing else []
            if novel_id not in parts:
                inp.value = f"{existing},{novel_id}" if existing else novel_id
                self.notify(f"已添加ID: {novel_id}", timeout=2)
        except Exception: pass

    def _on_window_refresh_from_monitor(self) -> None:
        try: self.app.call_from_thread(self._refresh_window_options)
        except Exception: pass

    def _refresh_window_options(self) -> None:
        try:
            if not self.browser_monitor: return
            windows = self.browser_monitor.get_browser_windows()
            options = [(self.i18n.t('crawler.all_windows'), "all")]
            for w in windows:
                label = f"{self.i18n.t('crawler.window_label')} {w['index']} ({w['tab_count']} {self.i18n.t('crawler.tabs')})"
                if w.get('title'): label += f" - {w['title'][:30]}"
                options.append((label, str(w['index'])))
            self.window_options = windows
            ws = self.query_one("#fm-window-select", Select)
            cv = str(self.selected_window_index) if self.selected_window_index is not None else "all"
            ws.set_options(options)
            if cv == "all" or any(str(w['index']) == cv for w in windows):
                ws.value = cv
            else:
                ws.value = "all"; self.selected_window_index = None
        except Exception as e:
            logger.error(f"刷新窗口选项失败: {e}")

    def _toggle_browser_monitor(self) -> None:
        try:
            if self.browser_monitor_active: self._stop_browser_monitor()
            else: self._start_browser_monitor()
        except Exception as e:
            logger.error(f"切换监听失败: {e}")

    def _start_browser_monitor(self) -> None:
        try:
            if not self.browser_monitor: self._init_browser_monitor()
            if not self.browser_monitor:
                self.notify(self.i18n.t('crawler.monitor_start_failed'), severity="error", timeout=2); return
            self.browser_monitor.selected_window_index = self.selected_window_index  # type: ignore
            if self.browser_monitor.start_monitoring():
                self.browser_monitor_active = True; self._update_monitor_button_state()
                self.notify(self.i18n.t('crawler.monitor_started'), timeout=2)
            else:
                self.notify(self.i18n.t('crawler.monitor_start_failed'), severity="error", timeout=2)
        except Exception as e:
            logger.error(f"启动监听失败: {e}")
            self.notify(f"启动监听失败: {e}", severity="error", timeout=3)

    def _stop_browser_monitor(self) -> None:
        try:
            if self.browser_monitor: self.browser_monitor.stop_monitoring()
            self.browser_monitor_active = False; self._update_monitor_button_state()
            self.notify(self.i18n.t('crawler.monitor_stopped'), timeout=2)
        except Exception as e:
            logger.error(f"停止监听失败: {e}")

    def _update_monitor_button_state(self) -> None:
        try:
            btn = self.query_one("#fm-toggle-monitor-btn", Button)
            if self.browser_monitor_active:
                btn.label = self.i18n.t('crawler.stop_monitor'); btn.variant = "error"
            else:
                btn.label = self.i18n.t('crawler.start_monitor'); btn.variant = "success"
        except Exception: pass

    # ─── 执行多组合并（核心逻辑）──────────────────────────

    def _execute_merge(self) -> None:
        """执行多分组合并操作 - 前组/中间组/后组分别处理"""
        # 参数校验
        target_file = self.target_book.get('file_path', '')
        if not target_file or not os.path.exists(target_file):
            self.notify(self.i18n.t('fill_missing.target_file_not_found'), severity="error", timeout=3)
            return

        valid_files = [b for b in self._crawled_books if b.get('file_path') and os.path.exists(b.get('file_path', ''))]
        if not valid_files:
            self.notify(self.i18n.t('fill_missing.no_valid_new_files'), severity="warning", timeout=3)
            return

        # 检查是否有任何分配
        has_any_assignment = any(len(g["books"]) > 0 for g in self._insert_groups.values())
        if not has_any_assignment:
            self.notify(self.i18n.t('fill_missing.no_group_assign'), severity="warning", timeout=3)
            return

        # 校验中间组行号
        middle_group = self._insert_groups[self.GROUP_MIDDLE]
        if middle_group["books"] and middle_group["line"] is None:
            raw = ""
            try:
                line_input = self.query_one("#fm-middle-line-input", Input)
                raw = line_input.value.strip()
            except Exception:
                pass
            if not raw:
                self.notify(self.i18n.t('fill_missing.middle_line_required'), severity="warning", timeout=3)
                return
            try:
                middle_group["line"] = int(raw)
                if middle_group["line"] < 1:
                    middle_group["line"] = 1
            except ValueError:
                self.notify(self.i18n.t('fill_invalid_line_number'), severity="error", timeout=2)
                return

        # 新书名
        name_input = self.query_one("#fm-new-name-input", Input)
        new_name = name_input.value.strip() or self.target_book.get('novel_title', '')

        # 读取目标内容（按行）
        if not self._target_lines:
            with open(target_file, 'r', encoding='utf-8') as f:
                self._target_lines = f.readlines()
        target_lines_raw = self._target_lines[:]

        # 备份
        backup_path = target_file + '.fill_backup'
        try: shutil.copy2(target_file, backup_path)
        except Exception as e: logger.warning(f"备份失败: {e}")

        separator = "\n\n" + "=" * 50 + "\n\n"

        try:
            # 构建各组的内容块
            def build_content_block(indices: List[int]) -> str:
                contents = []
                for idx in indices:
                    if idx < len(valid_files):
                        bf = valid_files[idx]
                        try:
                            with open(bf['file_path'], 'r', encoding='utf-8') as f:
                                c = f.read().strip()
                                if c: contents.append(c)
                        except Exception as e:
                            logger.warning(f"读取文件失败 {bf.get('file_path', '')}: {e}")
                return separator.join(contents) if contents else ""

            # 按前→中→后的顺序组装最终内容
            result_parts = []

            # 1. 前置组内容
            front_block = build_content_block(self._insert_groups[self.GROUP_FRONT]["books"])
            if front_block:
                result_parts.append(front_block)

            # 2. 原始内容的分段
            middle_indices = self._insert_groups[self.GROUP_MIDDLE]["books"]
            middle_line = self._insert_groups[self.GROUP_MIDDLE]["line"]

            if middle_indices and middle_line is not None:
                # 有中间组：需要把原内容拆成两段
                split_idx = min(middle_line, len(target_lines_raw))
                before_part = target_lines_raw[:split_idx]
                after_part = target_lines_raw[split_idx:]

                result_parts.extend(before_part) if before_part else None

                # 中间组内容
                middle_block = build_content_block(middle_indices)
                if middle_block:
                    result_parts.append(middle_block)

                result_parts.extend(after_part) if after_part else None
            else:
                # 无中间组，原内容作为整体
                result_parts.extend(target_lines_raw)

            # 3. 后置组内容
            back_block = build_content_block(self._insert_groups[self.GROUP_BACK]["books"])
            if back_block:
                result_parts.append(back_block)

            # 统计信息
            front_count = len(self._insert_groups[self.GROUP_FRONT]["books"])
            mid_count = len(self._insert_groups[self.GROUP_MIDDLE]["books"])
            back_count = len(self._insert_groups[self.GROUP_BACK]["books"])
            total_merged = front_count + mid_count + back_count

            direction_parts = []
            if front_count > 0:
                direction_parts.append(self.i18n.t('fill_missing.dir_front').format(count=front_count))
            if mid_count > 0:
                direction_parts.append(self.i18n.t('fill_missing.dir_middle').format(count=mid_count, line=middle_line or 0))
            if back_count > 0:
                direction_parts.append(self.i18n.t('fill_missing.dir_back').format(count=back_count))
            direction_text = "; ".join(direction_parts)

            # 写入文件
            with open(target_file, 'w', encoding='utf-8') as f:
                f.writelines(result_parts)

            # 更新数据库标题
            self._update_target_book_title(new_name)

            # 收集所有被合并的有效文件（用于清理）
            merged_valid_files = []
            all_assigned_indices = (self._insert_groups[self.GROUP_FRONT]["books"] +
                                   self._insert_groups[self.GROUP_MIDDLE]["books"] +
                                   self._insert_groups[self.GROUP_BACK]["books"])
            for idx in all_assigned_indices:
                if idx < len(valid_files):
                    merged_valid_files.append(valid_files[idx])

            # 清理临时文件和记录
            self._cleanup_crawled_records(merged_valid_files)

            msg = self.i18n.t('fill_missing.merge_success_multi').format(total=total_merged, detail=direction_text, name=new_name)
            self._update_status_text(msg)
            self.notify(msg, severity="success", timeout=5)
            logger.info(f"补缺合并完成: 前{front_count}+中{mid_count}@L{middle_line}+后{back_count}, 新名={new_name}")

            self.dismiss({
                "success": True, "action": "merged",
                "groups": {
                    "front": {"count": front_count, "indices": list(self._insert_groups[self.GROUP_FRONT]["books"])},
                    "middle": {"count": mid_count, "line": middle_line, "indices": list(middle_indices)},
                    "back": {"count": back_count, "indices": list(self._insert_groups[self.GROUP_BACK]["books"])},
                },
                "new_name": new_name,
                "merged_files": [f.get('file_path', '') for f in merged_valid_files],
            })

        except Exception as write_err:
            if os.path.exists(backup_path): shutil.copy2(backup_path, target_file)
            raise write_err
        finally:
            if os.path.exists(backup_path):
                try: os.remove(backup_path)
                except Exception: pass

    def _cleanup_crawled_records(self, valid_files: List[Dict[str, Any]]) -> None:
        """清理新爬取的临时记录和文件"""
        if not self.db_manager:
            return
        for bf in valid_files:
            try:
                file_path = bf.get('file_path', '')
                record_id = bf.get('record_id')
                novel_id = bf.get('novel_id', '')

                if file_path:
                    try: self.db_manager.delete_book(file_path, cleanup_associated=True)
                    except Exception: pass

                if file_path and os.path.exists(file_path):
                    try: os.remove(file_path)
                    except Exception: pass

                if record_id:
                    try: self.db_manager.delete_crawl_history(record_id)
                    except Exception:
                        pass
                    logger.info(f"已删除爬取历史记录 ID={record_id}")
                elif novel_id:
                    try:
                        history = self.db_manager.get_crawl_history_by_site(self.novel_site.get('id', 0), limit=50)
                        for rec in reversed(history):
                            if str(rec.get('novel_id', '')) == novel_id and rec.get('file_path') == file_path:
                                self.db_manager.delete_crawl_history(rec.get('id'))
                                logger.info(f"已通过ID匹配删除爬取历史记录: {novel_id}")
                                break
                    except Exception: pass

            except Exception as e:
                logger.warning(f"清理临时记录失败: {e}")

    def _update_target_book_title(self, new_title: str) -> None:
        if not self.db_manager or not new_title: return
        try:
            target_file = self.target_book.get('file_path', '')
            record_id = self.target_book.get('id')
            if record_id:
                self.db_manager.update_crawl_history_full(record_id, novel_title=new_title)
            books = self.db_manager.get_all_books() if hasattr(self.db_manager, 'get_all_books') else []
            for book in books:
                if hasattr(book, 'path') and book.path == target_file:
                    book.title = new_title; break
            logger.info(f"已更新书籍标题为: {new_title}")
        except Exception as e:
            logger.warning(f"更新书籍标题失败: {e}")

    # ─── 辅助功能 ─────────────────────────────────────────

    def _copy_novel_ids(self) -> None:
        inp = self.query_one("#fm-novel-id-input", Input)
        text = inp.value.strip()
        if not text:
            self.notify(self.i18n.t('crawler.enter_novel_id'), severity="warning", timeout=2); return
        try: import pyperclip; pyperclip.copy(text)
        except ImportError:
            import subprocess, platform
            sys = platform.system()
            cmd = ['pbcopy'] if sys == 'Darwin' else ['xclip', '-selection', 'clipboard']
            try: subprocess.run(cmd, input=text, text=True, check=True)
            except Exception: subprocess.run(['xsel', '--clipboard', '--input'], input=text, text=True, check=True)
        self.notify(self.i18n.t('crawler.copy_ids_success').format(count=len(text.split(','))), timeout=2)

    def _open_select_books_dialog(self) -> None:
        if not self.novel_site or not self.novel_site.get("selectable_enabled", True): return
        from src.ui.dialogs.select_books_dialog import SelectBooksDialog
        def handle_result(result):
            if result:
                try:
                    inp = self.query_one("#fm-novel-id-input", Input)
                    existing = inp.value.strip()
                    inp.value = f"{existing},{result}" if existing else result
                except Exception: pass
        self.app.push_screen(SelectBooksDialog(self.theme_manager, self.novel_site), handle_result)

    def _update_status_text(self, message: str) -> None:
        try: self.query_one("#fm-status", Label).update(message)
        except Exception: pass

    # ─── 按钮事件 ───────────────────────────────────────────

    @on(Button.Pressed, "#fm-toggle-crawl-btn")
    def on_toggle_crawl(self):
        if self.is_crawling: self._stop_crawl()
        else: self._start_crawl()

    @on(Button.Pressed, "#fm-copy-ids-btn")
    def on_copy_ids(self): self._copy_novel_ids()

    @on(Button.Pressed, "#fm-toggle-monitor-btn")
    def on_toggle_monitor(self): self._toggle_browser_monitor()

    @on(Button.Pressed, "#fm-refresh-window-btn")
    def on_refresh_window(self):
        if not self.browser_monitor: self._init_browser_monitor()
        self._refresh_window_options()

    @on(Button.Pressed, "#fm-choose-books-btn")
    def on_choose_books(self): self._open_select_books_dialog()

    @on(Select.Changed, "#fm-browser-select")
    def on_browser_select_changed(self, event: Select.Changed):
        if event.value is not None:
            self.selected_browser = str(event.value)
            if self.browser_monitor and self.browser_monitor_active: self._stop_browser_monitor()
            self._init_browser_monitor()

    @on(Select.Changed, "#fm-window-select")
    def on_window_select_changed(self, event: Select.Changed):
        if event.value is not None and event.value != "all":
            try: self.selected_window_index = int(str(event.value))
            except (ValueError, TypeError): self.selected_window_index = None
        else: self.selected_window_index = None
        if self.browser_monitor: self.browser_monitor.selected_window_index = self.selected_window_index  # type: ignore

    @on(Button.Pressed, "#fm-cancel-btn")
    def on_cancel(self):
        if self.is_crawling: self._stop_crawl()
        if self.browser_monitor_active: self._stop_browser_monitor()
        self.dismiss({"success": False, "action": "cancel", "crawled_ids": self._crawling_novel_ids})

    @on(Button.Pressed, "#fm-confirm-btn")
    def on_confirm_merge(self):
        self._execute_merge()

    # ─── 快捷键 ─────────────────────────────────────────

    def action_cancel(self): self.on_cancel()

    def action_visual_merge(self):
        """快捷键 v: 打开可视化补缺"""
        if self._stage == "merge":
            self._open_visual_merge()

    def action_toggle_crawl(self):
        if self.is_crawling: self._stop_crawl()
        else: self._start_crawl()

    def action_toggle_monitor(self): self._toggle_browser_monitor()
