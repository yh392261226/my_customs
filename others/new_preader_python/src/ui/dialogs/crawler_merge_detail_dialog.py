"""
合并详情弹窗 —— 允许用户逐组查看、排序、选择书籍后确认合并

流程：
1. 按组展示该组内所有书籍
2. 支持勾选/取消、上下移动排序
3. 输入合并后的书名
4. 合并当前组后自动进入下一组
"""

import os
from copy import deepcopy
from typing import Dict, Any, List, Optional, ClassVar

from send2trash import send2trash
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label, DataTable, Input, Static, Select
from textual import on

from src.locales.i18n_manager import get_global_i18n
from src.utils.file_utils import FileUtils
from src.themes.theme_manager import ThemeManager
from src.core.database_manager import DatabaseManager
from src.ui.dialogs.crawler_merge_mode_dialog import BookGroup
from src.ui.utils.smart_title_utils import SmartTitleUtils
from src.utils.logger import get_logger

logger = get_logger(__name__)


class _MergePreviewDialog(ModalScreen[None]):
    """合并详情弹窗内部使用的书籍预览弹窗（避免循环导入）"""

    CSS_PATH = "../styles/crawler_management_bookpreview_dialog_overrides.tcss"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("escape", "close", get_global_i18n().t('common.close')),
    ]

    def action_close(self) -> None:
        self.dismiss()

    def __init__(self, theme_manager: ThemeManager, title: str, content: str):
        super().__init__()
        self.theme_manager = theme_manager
        self.title = title
        self.content = content
        self.i18n = get_global_i18n()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Vertical(
                Label(f"📖 {self.i18n.t('crawler.preview_title')}", id="preview-title", classes="section-title"),
                Label(f"{self.content} ......", id="preview-content", classes="preview-text"),
                Horizontal(
                    Button(self.i18n.t('common.close'), id="preview-close-btn", variant="primary"),
                    id="preview-buttons", classes="btn-row",
                ),
                id="preview-container",
            ),
            id="preview-window",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.theme_manager.apply_theme_to_screen(self)
        preview_content = self.query_one("#preview-content")
        preview_content.border_title = self.title
        preview_content.border_subtitle = self.title
        try:
            self.query_one("#preview-close-btn", Button).focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "preview-close-btn":
            self.dismiss()


class CrawlerMergeDetailDialog(ModalScreen[Dict[str, Any]]):
    """合并详情弹窗 —— 逐组预览、排序、勾选后合并"""

    CSS_PATH = "../styles/crawler_merge_detail_dialog.tcss"

    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t('common.cancel_all')),
        ("space", "toggle_row", get_global_i18n().t('batch_ops.toggle_row')),
        ("up", "move_up", get_global_i18n().t('merge_detail.move_up')),
        ("down", "move_down", get_global_i18n().t('merge_detail.move_down')),
        ("y", "copy_title", get_global_i18n().t('merge_detail.copy_title')),
        ("x", "clear_title", get_global_i18n().t('merge_detail.clear_title')),
        ("v", "preview_book", get_global_i18n().t('merge_detail.preview')),
        ("d", "delete_book", get_global_i18n().t('merge_detail.delete_current')),
        ("D", "delete_selected", get_global_i18n().t('novel_sites.batch_delete')),
        ("a", "toggle_select_all", get_global_i18n().t('batch_ops.select_all')),
        ("g", "merge_this", get_global_i18n().t('merge_detail.merge_this')),
        ("t", "skip_this", get_global_i18n().t('merge_detail.skip_this')),
        ("m", "smart_title", get_global_i18n().t('merge_detail.smart_title')),
        ("X", "select_books", get_global_i18n().t('crawler.select_books')),
        ("s", "toggle_crawl", get_global_i18n().t('crawler.toggle_crawl')),
        ("e", "toggle_monitor", get_global_i18n().t('crawler.toggle_monitor')),
        ("f", "fill_missing", get_global_i18n().t('merge_detail.fill_missing')),
        ("S", "search_chapters", get_global_i18n().t('crawler.search_chapters_shortcut')),
        ("F", "view_current_file", get_global_i18n().t('crawler.shortcut_f')),
        ("p", "prev_group", get_global_i18n().t('duplicate_books.prev_group')),
        ("n", "next_group", get_global_i18n().t('duplicate_books.next_group')),
    ]

    def __init__(
        self,
        theme_manager: ThemeManager,
        groups: List[Dict[str, Any]],
        db_manager: Optional[DatabaseManager] = None,
        novel_site: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme_manager = theme_manager
        self.i18n = get_global_i18n()
        self.db_manager = db_manager
        self.novel_site = novel_site or {}

        # 深拷贝 groups，避免影响原始数据
        self.groups: List[Dict[str, Any]] = deepcopy(groups)
        # 按 display_title 长度降序排列（最长书名的组优先显示）
        self.groups.sort(key=lambda g: len(g.get('display_title', g.get('base_title', ''))), reverse=True)
        self._current_index: int = 0       # 当前在第几组
        self._total_groups: int = len(self.groups)

        # 每组维护：选中的书籍 id 集合、排序后的书籍列表
        self._group_state: Dict[int, Dict[str, Any]] = {}
        for i, g in enumerate(self.groups):
            books = g.get('books', [])
            # 默认只选中成功且有文件的
            selected = {
                b.get('id') for b in books
                if b.get('status') == 'success' and b.get('file_path')
            }
            self._group_state[i] = {
                'books': list(books),
                'selected_ids': selected,
                'merged_title': g.get('base_title', ''),
                'skipped': False,
                'auto_sorted': False,   # 是否已对该组执行过自动排序
            }

        # ── 补缺功能相关状态 ──
        self._fill_missing_visible: bool = False
        self.is_crawling: bool = False
        self.current_task_id: Optional[str] = None
        self.current_crawling_id: Optional[str] = None
        self.selected_browser: str = "chrome"
        self.selected_window_index: Optional[int] = None
        self.window_options: List[Dict[str, Any]] = []
        self.browser_monitor = None
        self.browser_monitor_active: bool = False
        self._crawler_manager = None  # 延迟初始化
        self._crawling_novel_ids: List[str] = []  # 本次爬取的书籍ID

        # ── 列标题排序相关状态 ──
        self._sort_column: Optional[str] = None  # 当前排序列 key
        self._sort_reverse: bool = False  # False=升序, True=降序

    # ─── Compose ────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                # 标题行：当前组 / 总组数
                Label("", id="merge-detail-title"),
                # 分组类型提示
                Static("", id="merge-detail-type-hint"),
                # 进度提示
                Label("", id="merge-detail-progress"),
                # 书名输入
                Horizontal(
                    Label(self.i18n.t('merge_detail.merged_title_label'), id="title-label"),
                    Input(placeholder=self.i18n.t('merge_detail.title_placeholder'), id="merge-title-input"),
                    Button(self.i18n.t('merge_detail.clear_title'), id="clear-title-btn"),
                    id="title-row",
                ),
                # 提示说明
                Label(self.i18n.t('merge_detail.table_hint'), id="table-hint"),
                # 书籍表格
                DataTable(id="merge-detail-table"),
                # 排序操作按钮
                Horizontal(
                    Button(self.i18n.t('merge_detail.move_up'), id="move-up-btn"),
                    Button(self.i18n.t('merge_detail.move_down'), id="move-down-btn"),
                    Button(self.i18n.t('merge_detail.sort_by_time'), id="sort-time-btn"),
                    Button(self.i18n.t('merge_detail.select_all'), id="select-all-btn"),
                    Button(self.i18n.t('merge_detail.deselect_all'), id="deselect-all-btn"),
                    Button(self.i18n.t('crawler.search_chapters'), id="search-chapters-btn", variant="warning"),
                    Button(self.i18n.t('merge_detail.fill_missing'), id="fill-missing-btn", variant="primary"),
                    Button(self.i18n.t('merge_detail.smart_title'), id="smart-title-btn", variant="success"),
                    id="sort-buttons",
                ),
                # 补缺操作行（默认隐藏）
                Vertical(
                    Horizontal(
                        *([Button(self.i18n.t('crawler.select_books'), id="md-choose-books-btn")] if self.novel_site.get("selectable_enabled", True) else []),
                        Input(placeholder=self.i18n.t('crawler.novel_id_placeholder_multi'), id="md-novel-id-input"),
                        Button(self.i18n.t('crawler.start_crawl'), id="md-toggle-crawl-btn", variant="primary"),
                        Button(self.i18n.t('crawler.copy_ids'), id="md-copy-ids-btn"),
                        Button(self.i18n.t('crawler.toggle_monitor'), id="md-toggle-monitor-btn", variant="success"),
                        Select(
                            id="md-browser-select",
                            options=[
                                (self.i18n.t('crawler.browser_label'), "chrome"),
                                ("Chrome", "chrome"),
                                ("Safari", "safari"),
                                ("Brave", "brave"),
                            ],
                            value="chrome",
                        ),
                        Select(
                            id="md-window-select",
                            options=[
                                (self.i18n.t('crawler.all_windows'), "all"),
                            ],
                            value="all",
                        ),
                        Button(self.i18n.t('crawler.refresh_windows'), id="md-refresh-window-btn"),
                        id="md-fill-missing-row",
                    ),
                    id="md-fill-missing-container",
                    classes="hidden",
                ),
                # 快速定位行
                Horizontal(
                    Label(self.i18n.t('merge_detail.move_to_pos'), id="pos-label"),
                    Input(
                        placeholder=self.i18n.t('merge_detail.pos_placeholder'),
                        id="move-to-pos-input",
                        type="integer",
                    ),
                    Button("Move", id="move-to-pos-btn", variant="primary"),
                    id="pos-row",
                ),
                # 状态栏
                Label("", id="merge-detail-status"),
                # 底部操作按钮
                Horizontal(
                    Button(self.i18n.t('duplicate_books.prev_group'), id="prev-group-btn"),
                    Button(self.i18n.t('merge_detail.merge_this'), id="merge-this-btn", variant="primary"),
                    Button(self.i18n.t('merge_detail.skip_this'), id="skip-this-btn"),
                    Button(self.i18n.t('duplicate_books.next_group'), id="next-group-btn"),
                    Button(self.i18n.t('common.cancel'), id="cancel-all-btn", variant="error"),
                    id="detail-buttons",
                ),
                id="merge-detail-container",
            )
        )
        yield Footer()

    # ─── Mount ──────────────────────────────────────────────

    def on_mount(self) -> None:
        self._refresh_display()

    # ─── 显示刷新 ───────────────────────────────────────────

    def _refresh_display(self) -> None:
        """刷新当前组的显示"""
        state = self._group_state[self._current_index]
        group = self.groups[self._current_index]
        is_auto = group.get('is_auto_same_book', False)

        # 标题
        title_label = self.query_one("#merge-detail-title", Label)
        title_label.update(
            self.i18n.t(
                'merge_detail.group_title',
                index=self._current_index + 1,
                total=self._total_groups,
                name=group.get('display_title', group.get('base_title', '')),
            )
        )

        # 类型提示
        hint = self.query_one("#merge-detail-type-hint", Static)
        if is_auto:
            hint.update(f"🔗 {self.i18n.t('merge_detail.auto_chapter_hint')}")
        else:
            hint.update(f"📚 {self.i18n.t('merge_detail.similar_books_hint')}")

        # 进度
        progress = self.query_one("#merge-detail-progress", Label)
        progress.update(
            self.i18n.t(
                'merge_detail.progress',
                current=self._current_index + 1,
                total=self._total_groups,
            )
        )

        # 智能排序：首次显示、或书籍数量增加（如爬取补全后加入新书）时按章节号升序排列；
        # 数量不变的后续显示保留用户手动排序结果（避免刷新/切组把手动顺序冲掉）。
        # 注意：之前在组内书 < 2 时 _smart_sort_books 会直接返回 False，但仍把 auto_sorted 置 True，
        # 导致之后补全加入新书后永不重排——这里用 auto_sorted_count 跟踪数量来修正。
        prev_count = state.get('auto_sorted_count', 0)
        if not state.get('auto_sorted', False) or len(state['books']) > prev_count:
            self._smart_sort_books()
            state['auto_sorted'] = True
            state['auto_sorted_count'] = len(state['books'])
        try:
            smart_title = self._generate_smart_title()
            if smart_title:
                state['merged_title'] = smart_title
            title_input = self.query_one("#merge-title-input", Input)
            title_input.value = smart_title or state.get('merged_title', '')
        except Exception as e:
            logger.debug(f"智能标题生成失败（已忽略）: {e}")
            # 使用已有的 merged_title 或 base_title
            title_input = self.query_one("#merge-title-input", Input)
            title_input.value = state.get('merged_title', group.get('base_title', ''))

        # 表格
        self._refresh_table()

        # 状态
        self._update_status()

        # 聚焦
        self.query_one("#merge-detail-table", DataTable).focus()

    def _refresh_table(self) -> None:
        """刷新书籍表格"""
        state = self._group_state[self._current_index]
        books = state['books']
        selected = state['selected_ids']

        table = self.query_one("#merge-detail-table", DataTable)
        table.clear()

        if not table.columns:
            # 排序方向箭头
            arrow = ""
            if self._sort_column:
                arrow = " ▼" if self._sort_reverse else " ▲"

            table.add_column("✓", key="selected", width=3)
            table.add_column(self.i18n.t('merge_detail.col_seq'), key="seq", width=4)
            table.add_column(
                (self.i18n.t('merge_detail.col_book_id') + arrow) if self._sort_column == "book_id" else self.i18n.t('merge_detail.col_book_id'),
                key="book_id", width=14,
            )
            table.add_column(
                (self.i18n.t('merge_detail.col_title') + arrow) if self._sort_column == "title" else self.i18n.t('merge_detail.col_title'),
                key="title", width=60,
            )
            table.add_column(
                (self.i18n.t('merge_detail.col_time') + arrow) if self._sort_column == "time" else self.i18n.t('merge_detail.col_time'),
                key="time", width=10,
            )
            table.add_column(
                (self.i18n.t('merge_detail.col_size') + arrow) if self._sort_column == "size" else self.i18n.t('merge_detail.col_size'),
                key="size", width=5,
            )
            table.add_column(self.i18n.t('merge_detail.col_preview'), key="preview", width=6)
            table.add_column(self.i18n.t('crawler.shortcut_f'), key="file", width=10)
            table.add_column(self.i18n.t('merge_detail.col_delete'), key="delete", width=10)
        elif self._sort_column:
            # 已有列定义时，更新排序列的标题显示箭头
            arrow = " ▼" if self._sort_reverse else " ▲"
            col_labels = {
                "book_id": self.i18n.t('merge_detail.col_book_id'),
                "title": self.i18n.t('merge_detail.col_title'),
                "time": self.i18n.t('merge_detail.col_time'),
                "size": self.i18n.t('merge_detail.col_size'),
            }
            base_label = col_labels.get(self._sort_column, '')
            if base_label:
                try:
                    table.set_label(self._sort_column, base_label + arrow)
                except Exception:
                    pass

        for idx, book in enumerate(books, 1):
            bid = book.get('id')
            check = "☑" if bid in selected else "☐"
            novel_id = str(book.get('novel_id', '') or '')
            title = book.get('novel_title', '')
            crawl_time = book.get('crawl_time', '')
            if isinstance(crawl_time, str) and len(crawl_time) >= 16:
                crawl_time = crawl_time[:16]
            # 从 file_path 获取实际文件大小（crawl_history 表无 file_size 字段）
            file_path = book.get('file_path', '')
            if file_path:
                try:
                    file_size = FileUtils.get_file_size(file_path)
                except Exception:
                    file_size = 0
            else:
                file_size = book.get('file_size', 0) or 0
            size_str = self._format_size(file_size)

            table.add_row(
                check,
                str(idx),
                novel_id[:20],
                title[:60] if len(title) > 60 else title,
                crawl_time,
                size_str,
                self.i18n.t('merge_detail.preview_btn'),
                self.i18n.t('crawler.shortcut_f'),
                self.i18n.t('merge_detail.delete_btn'),
                key=str(bid),
            )

    def _update_status(self) -> None:
        """更新状态栏"""
        state = self._group_state[self._current_index]
        selected_count = len(state['selected_ids'])
        total_count = len(state['books'])

        status = self.query_one("#merge-detail-status", Label)
        status.update(
            self.i18n.t(
                'merge_detail.status_text',
                selected=selected_count,
                total=total_count,
            )
        )

    @staticmethod
    def _format_size(size: int) -> str:
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        elif size >= 1024:
            return f"{size / 1024:.1f}KB"
        return f"{size}B"

    # ─── 行操作 ─────────────────────────────────────────────

    def _get_cursor_row(self) -> Optional[int]:
        """获取当前光标行号"""
        table = self.query_one("#merge-detail-table", DataTable)
        return getattr(table, 'cursor_row', None)

    def _get_cursor_book_id(self) -> Optional[int]:
        """获取当前光标行的书籍 ID"""
        table = self.query_one("#merge-detail-table", DataTable)
        cursor_row = getattr(table, 'cursor_row', None)
        if cursor_row is None or not (0 <= cursor_row < len(table.rows)):
            return None
        row_keys = list(table.rows.keys())
        key = row_keys[cursor_row]
        return int(str(key.value if hasattr(key, 'value') else key))

    def _toggle_current_row(self) -> None:
        """切换当前行的选中状态"""
        table = self.query_one("#merge-detail-table", DataTable)
        cursor_row = getattr(table, 'cursor_row', None)
        if cursor_row is None or not (0 <= cursor_row < len(table.rows)):
            return

        bid = self._get_cursor_book_id()
        if bid is None:
            return
        state = self._group_state[self._current_index]
        if bid in state['selected_ids']:
            state['selected_ids'].discard(bid)
        else:
            state['selected_ids'].add(bid)
        self._refresh_table()

        # 恢复光标到原位
        if cursor_row < len(table.rows):
            if hasattr(table, 'move_cursor'):
                table.move_cursor(row=cursor_row)
            else:
                while table.cursor_row > 0:
                    table.action_cursor_up()
                for _ in range(cursor_row):
                    table.action_cursor_down()
            table.focus()

        self._update_status()

    def _move_current_row(self, direction: int) -> None:
        """
        移动当前行。direction: -1 上移, 1 下移
        """
        table = self.query_one("#merge-detail-table", DataTable)
        cursor_row = getattr(table, 'cursor_row', None)
        if cursor_row is None:
            return

        state = self._group_state[self._current_index]
        books = state['books']

        new_index = cursor_row + direction
        if not (0 <= new_index < len(books)):
            return

        # 交换
        books[cursor_row], books[new_index] = books[new_index], books[cursor_row]

        # 刷新表格
        self._refresh_table()

        # 恢复光标到新位置
        if hasattr(table, 'move_cursor'):
            table.move_cursor(row=new_index)
        else:
            while table.cursor_row > 0:
                table.action_cursor_up()
            for _ in range(new_index):
                table.action_cursor_down()

        table.focus()

    def _move_to_position(self, target_pos: int) -> None:
        """
        将当前行移动到指定位置（1-based 序号）。

        Args:
            target_pos: 目标位置（从 1 开始）
        """
        table = self.query_one("#merge-detail-table", DataTable)
        cursor_row = getattr(table, 'cursor_row', None)
        if cursor_row is None:
            return

        state = self._group_state[self._current_index]
        books = state['books']

        # 转换为 0-based
        target_idx = target_pos - 1
        if target_idx < 0 or target_idx >= len(books) or target_idx == cursor_row:
            return

        # 将当前项插入到目标位置
        moved = books.pop(cursor_row)
        books.insert(target_idx, moved)

        # 刷新表格
        self._refresh_table()

        # 恢复光标到新位置
        if hasattr(table, 'move_cursor'):
            table.move_cursor(row=target_idx)
        else:
            while table.cursor_row > 0:
                table.action_cursor_up()
            for _ in range(target_idx):
                table.action_cursor_down()

        table.focus()

    # ─── 按钮事件 ───────────────────────────────────────────

    @on(Button.Pressed, "#move-up-btn")
    def on_move_up(self) -> None:
        self._move_current_row(-1)

    @on(Button.Pressed, "#move-down-btn")
    def on_move_down(self) -> None:
        self._move_current_row(1)

    @on(Button.Pressed, "#sort-time-btn")
    def on_sort_by_time(self) -> None:
        """按爬取时间排序"""
        state = self._group_state[self._current_index]
        state['books'].sort(key=lambda b: b.get('crawl_time', ''))
        self._refresh_table()
        self._update_status()

    def _sort_books_by_column(self, column_key: str, reverse: bool) -> None:
        """根据指定列对当前组书籍排序

        Args:
            column_key: 列 key（book_id / title / time / size）
            reverse: True=降序, False=升序
        """
        from datetime import datetime
        from urllib.parse import unquote

        state = self._group_state[self._current_index]

        def get_sort_key(book: Dict[str, Any]):
            if column_key == "book_id":
                val = book.get('novel_id', '')
                return unquote(val) if val else ''
            elif column_key == "title":
                return book.get('novel_title', '')
            elif column_key == "time":
                try:
                    time_str = book.get('crawl_time', '')
                    return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S") if time_str else datetime.min
                except Exception:
                    return datetime.min
            elif column_key == "size":
                file_path = book.get('file_path', '')
                if file_path:
                    try:
                        return FileUtils.get_file_size(file_path)
                    except Exception:
                        pass
                return book.get('file_size', 0) or 0
            return ''

        state['books'].sort(key=get_sort_key, reverse=reverse)

    @on(Button.Pressed, "#select-all-btn")
    def on_select_all(self) -> None:
        state = self._group_state[self._current_index]
        state['selected_ids'] = {b.get('id') for b in state['books']}
        self._refresh_table()
        self._update_status()

    @on(Button.Pressed, "#deselect-all-btn")
    def on_deselect_all(self) -> None:
        state = self._group_state[self._current_index]
        state['selected_ids'].clear()
        self._refresh_table()
        self._update_status()

    @on(Button.Pressed, "#merge-this-btn")
    def on_merge_this(self) -> None:
        """合并当前组并进入下一组"""
        title_input = self.query_one("#merge-title-input", Input)
        new_title = title_input.value.strip()

        if not new_title:
            self.notify(self.i18n.t('merge_detail.title_required'), severity="warning")
            return

        state = self._group_state[self._current_index]
        selected_ids = state['selected_ids']
        if len(selected_ids) < 2:
            self.notify(self.i18n.t('merge_detail.need_at_least_two'), severity="warning")
            return

        # 保存标题
        state['merged_title'] = new_title

        # 检查是否还有下一组
        if self._current_index + 1 < self._total_groups:
            self._current_index += 1
            self._refresh_display()
        else:
            # 所有组处理完毕，返回结果
            self._finish_and_return()

    @on(Button.Pressed, "#skip-this-btn")
    def on_skip_this(self) -> None:
        """跳过当前组"""
        # 标记当前组为跳过
        self._group_state[self._current_index]['skipped'] = True
        if self._current_index + 1 < self._total_groups:
            self._current_index += 1
            self._refresh_display()
        else:
            self._finish_and_return()

    @on(Button.Pressed, "#prev-group-btn")
    def on_prev_group(self) -> None:
        """返回上一组重新处理"""
        # 先保存当前组的输入状态
        state = self._group_state[self._current_index]
        title_input = self.query_one("#merge-title-input", Input)
        state['merged_title'] = title_input.value.strip()

        if self._current_index > 0:
            self._current_index -= 1
            self._refresh_display()
        else:
            self.notify(self.i18n.t('duplicate_books.already_first_group'), severity="warning", timeout=2)

    @on(Button.Pressed, "#next-group-btn")
    def on_next_group(self) -> None:
        """跳到下一组"""
        # 先保存当前组的输入状态
        state = self._group_state[self._current_index]
        title_input = self.query_one("#merge-title-input", Input)
        state['merged_title'] = title_input.value.strip()

        if self._current_index + 1 < self._total_groups:
            self._current_index += 1
            self._refresh_display()
        else:
            self.notify(self.i18n.t('duplicate_books.already_last_group'), severity="warning", timeout=2)

    @on(Button.Pressed, "#cancel-all-btn")
    def on_cancel_all(self) -> None:
        self.dismiss({
            "success": False,
            "action": "merge_detail",
            "message": self.i18n.t('batch_ops.cancel_merge'),
        })

    @on(Input.Submitted, "#merge-title-input")
    def on_title_submitted(self) -> None:
        """回车提交"""
        self.on_merge_this()

    # ─── 完成并返回 ─────────────────────────────────────────

    def _finish_and_return(self) -> None:
        """收集所有组的合并结果并返回"""
        merged_groups = []
        skipped_groups = []

        for i in range(self._total_groups):
            state = self._group_state[i]
            group = self.groups[i]

            # 显式跳过的组不合并
            if state.get('skipped', False):
                skipped_groups.append(group.get('display_title', f"Group {i + 1}"))
                continue

            selected_ids = state['selected_ids']

            if len(selected_ids) < 2:
                skipped_groups.append(group.get('display_title', f"Group {i + 1}"))
                continue

            # 按排序后的顺序提取选中的书籍
            selected_books = [
                b for b in state['books']
                if b.get('id') in selected_ids
            ]

            merged_groups.append({
                "group_id": group.get('group_id', i + 1),
                "new_title": (state.get('merged_title', group.get('base_title', '')) or '').replace('/', '').replace('\\', '').strip(),
                "selected_books": selected_books,
            })

        if not merged_groups:
            self.notify(self.i18n.t('merge_detail.no_groups_to_merge'), severity="warning")
            return

        self.dismiss({
            "success": True,
            "action": "merge_detail",
            "merged_groups": merged_groups,
            "skipped_groups": skipped_groups,
            "message": self.i18n.t(
                'merge_detail.completed',
                merged=len(merged_groups),
                skipped=len(skipped_groups),
            ),
        })

    # ─── 快速定位 ───────────────────────────────────────────

    @on(Button.Pressed, "#move-to-pos-btn")
    def on_pos_submitted(self, event: Button.Pressed) -> None:
        """输入目标位置并定位"""
        try:
            pos_input = self.query_one("#move-to-pos-input", Input)
            pos = int(pos_input.value.strip())
            self._move_to_position(pos)
            # 清空输入框
            pos_input.value = ""
        except ValueError:
            pass

    # ─── 快捷键 ─────────────────────────────────────────────

    def action_toggle_row(self) -> None:
        self._toggle_current_row()

    def action_move_up(self) -> None:
        self._move_current_row(-1)

    def action_move_down(self) -> None:
        self._move_current_row(1)

    def action_cancel(self) -> None:
        self.on_cancel_all()

    def action_copy_title(self) -> None:
        """y键：复制当前行书名"""
        self._copy_focused_book_title()

    def action_clear_title(self) -> None:
        """x键：清除标题输入框内容"""
        self._clear_title()

    def action_preview_book(self) -> None:
        """v键：预览当前光标所在行的书籍"""
        book = self._get_cursor_book()
        if book is not None:
            self._preview_book(book)

    def action_delete_book(self) -> None:
        """d键：删除当前光标所在行的书籍"""
        book = self._get_cursor_book()
        if book is not None:
            self._delete_book(book)

    def action_delete_selected(self) -> None:
        """D键：批量删除当前组中所有选中的书籍"""
        self._delete_selected_books()

    def _delete_selected_books(self) -> None:
        """批量删除所有选中的书籍"""
        if self.db_manager is None:
            self.notify(self.i18n.t('merge_detail.delete_unavailable'), severity="warning", timeout=2)
            return

        state = self._group_state[self._current_index]
        selected_ids = state['selected_ids'].copy()
        if not selected_ids:
            return

        # 获取要删除的书籍列表
        books_to_delete = [b for b in state['books'] if b.get('id') in selected_ids]
        if not books_to_delete:
            return

        try:
            from src.ui.dialogs.confirm_dialog import ConfirmDialog

            count = len(books_to_delete)
            titles = ', '.join([b.get('novel_title', '') for b in books_to_delete[:3]])
            if count > 3:
                titles += f' ... (共{count}本)'

            def handle_batch_delete_confirmation(confirmed: Optional[bool]) -> None:
                if not confirmed:
                    self.notify(self.i18n.t('crawler.delete_cancelled'), timeout=2)
                    return
                try:
                    db_manager = self.db_manager
                    success_count = 0
                    fail_count = 0

                    for book in books_to_delete:
                        try:
                            file_path = book.get('file_path', '')

                            # 1) 删除文件（若有）
                            if file_path and file_path != 'already_exists' and os.path.exists(file_path):
                                try:
                                    send2trash(file_path)
                                    logger.info(f"文件已移至回收站: {file_path}")
                                except Exception as e:
                                    logger.error(f"删除文件失败: {file_path} - {e}")

                            # 2) 删除数据库记录
                            history_id = book.get('id')
                            if history_id is not None:
                                try:
                                    db_manager.delete_crawl_history(int(history_id))
                                except Exception as e:
                                    logger.error(f"删除爬取历史记录失败: {history_id} - {e}")

                            success_count += 1
                        except Exception as e:
                            logger.error(f"删除书籍失败: {book.get('novel_title', '')} - {e}")
                            fail_count += 1

                    # 3) 从当前组状态中移除已删除的书籍
                    deleted_ids = {book.get('id') for book in books_to_delete}
                    state['books'] = [b for b in state['books'] if b.get('id') not in deleted_ids]
                    state['selected_ids'].clear()

                    # 4) 刷新界面
                    self._refresh_table()
                    self._update_status()

                    msg = self.i18n.t('merge_detail.batch_deleted', count=success_count)
                    if fail_count > 0:
                        msg += f' ({fail_count} {self.i18n.t("crawler.failed")})'
                    self.notify(msg, timeout=3)
                except Exception as e:
                    logger.error(f"批量删除书籍失败: {e}")
                    self.notify(
                        f"{self.i18n.t('crawler.delete_file_failed')}: {e}",
                        severity="error", timeout=3,
                    )

            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    self.i18n.t('merge_detail.confirm_batch_delete_title'),
                    self.i18n.t('merge_detail.confirm_batch_delete_message', count=count, titles=titles),
                ),
                handle_batch_delete_confirmation,
            )
        except Exception as e:
            logger.error(f"批量删除书籍失败: {e}")
            self.notify(
                f"{self.i18n.t('crawler.delete_file_failed')}: {e}",
                severity="error", timeout=3,
            )

    def _get_cursor_book(self) -> Optional[Dict[str, Any]]:
        """获取当前光标行对应的书籍字典"""
        bid = self._get_cursor_book_id()
        if bid is None:
            return None
        state = self._group_state[self._current_index]
        return next((b for b in state['books'] if b.get('id') == bid), None)

    @on(DataTable.HeaderSelected, "#merge-detail-table")
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """数据表格表头点击事件 - 按列排序"""
        try:
            column_key = str(event.column_key.value or "")

            # 可排序列
            sortable_columns = {"book_id", "title", "time", "size"}

            if column_key not in sortable_columns:
                return

            # 切换排序方向：同列切换，新列默认升序
            if self._sort_column == column_key:
                self._sort_reverse = not self._sort_reverse
            else:
                self._sort_column = column_key
                self._sort_reverse = False  # 新列默认升序

            # 执行排序
            self._sort_books_by_column(column_key, self._sort_reverse)

            # 刷新表格（会显示方向箭头）
            self._refresh_table()

            # 状态栏提示
            direction = self.i18n.t('merge_detail.sort_desc') if self._sort_reverse else self.i18n.t('merge_detail.sort_asc')
            column_names = {
                "book_id": self.i18n.t('merge_detail.col_book_id'),
                "title": self.i18n.t('merge_detail.col_title'),
                "time": self.i18n.t('merge_detail.col_time'),
                "size": self.i18n.t('merge_detail.col_size'),
            }
            col_name = column_names.get(column_key, column_key)
            status = self.query_one("#merge-detail-status", Label)
            status.update(f"{col_name} {direction}")
        except Exception as e:
            logger.error(f"表头点击排序失败: {e}")

    @on(DataTable.CellSelected, "#merge-detail-table")
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """单元格选择事件 —— 处理预览/删除按钮列点击"""
        try:
            column_key = event.cell_key.column_key.value or ""
            bid_str = event.cell_key.row_key.value or ""
            if not bid_str:
                return
            try:
                bid = int(bid_str)
            except ValueError:
                return
            state = self._group_state[self._current_index]
            book = next((b for b in state['books'] if b.get('id') == bid), None)
            if not book:
                return

            if column_key == "preview":
                self._preview_book(book)
            elif column_key == "file":
                self._view_file(book)
            elif column_key == "delete":
                self._delete_book(book)
        except Exception as e:
            logger.error(f"单元格选择事件处理失败: {e}")

    def _preview_book(self, book: Dict[str, Any]) -> None:
        """预览书籍内容（读取文件前 2000 字）"""
        try:
            file_path = book.get('file_path', '')
            if not file_path or file_path == 'already_exists':
                self.notify(self.i18n.t('crawler.no_file_path'), severity="warning", timeout=2)
                return
            if not os.path.exists(file_path):
                self.notify(self.i18n.t('crawler.file_not_exists'), severity="warning", timeout=2)
                return

            content = ""
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(2000)
            except Exception as e:
                logger.error(f"读取文件失败: {e}")
                self.notify(
                    self.i18n.t('crawler.preview_failed', error=str(e)),
                    severity="error", timeout=3,
                )
                return

            if not content.strip():
                self.notify(self.i18n.t('crawler.preview_empty'), timeout=2)
                return

            # 使用本弹窗内部定义的预览弹窗（避免循环导入）
            self.app.push_screen(
                _MergePreviewDialog(
                    self.theme_manager,
                    book.get('novel_title', ''),
                    content,
                )
            )
        except Exception as e:
            logger.error(f"预览书籍失败: {e}")
            self.notify(
                f"{self.i18n.t('crawler.preview_failed', error=str(e))}",
                severity="error", timeout=3,
            )

    def _delete_book(self, book: Dict[str, Any]) -> None:
        """删除光标所在行的书籍（文件 + 数据库记录）"""
        if self.db_manager is None:
            self.notify(self.i18n.t('merge_detail.delete_unavailable'), severity="warning", timeout=2)
            return
        db_manager = self.db_manager

        try:
            from src.ui.dialogs.confirm_dialog import ConfirmDialog

            novel_title = book.get('novel_title', '')
            file_path = book.get('file_path', '')

            def handle_delete_confirmation(confirmed: Optional[bool]) -> None:
                if not confirmed:
                    self.notify(self.i18n.t('crawler.delete_cancelled'), timeout=2)
                    return
                try:
                    # 1) 删除文件（若有）
                    if file_path and file_path != 'already_exists' and os.path.exists(file_path):
                        try:
                            send2trash(file_path)
                            logger.info(f"文件已移至回收站: {file_path}")
                        except Exception as e:
                            logger.error(f"删除文件失败: {file_path} - {e}")

                    # 2) 删除数据库记录
                    history_id = book.get('id')
                    if history_id is not None:
                        try:
                            db_manager.delete_crawl_history(int(history_id))
                        except Exception as e:
                            logger.error(f"删除爬取历史记录失败: {history_id} - {e}")

                    # 3) 从当前组状态中移除该书籍
                    state = self._group_state[self._current_index]
                    state['books'] = [b for b in state['books'] if b.get('id') != book.get('id')]
                    state['selected_ids'].discard(book.get('id'))

                    # 4) 刷新界面
                    self._refresh_table()
                    self._update_status()
                    self.notify(
                        self.i18n.t('merge_detail.book_deleted', title=novel_title),
                        timeout=2,
                    )
                except Exception as e:
                    logger.error(f"删除书籍失败: {e}")
                    self.notify(
                        f"{self.i18n.t('crawler.delete_file_failed')}: {e}",
                        severity="error", timeout=3,
                    )

            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    self.i18n.t('merge_detail.confirm_delete_title'),
                    self.i18n.t('merge_detail.confirm_delete_message', title=novel_title),
                ),
                handle_delete_confirmation,
            )
        except Exception as e:
            logger.error(f"删除书籍失败: {e}")
            self.notify(
                f"{self.i18n.t('crawler.delete_file_failed')}: {e}",
                severity="error", timeout=3,
            )


    def _clear_title(self) -> None:
        """清除标题输入框内容并保存空标题到当前组状态，并聚焦到输入框便于继续输入"""
        title_input = self.query_one("#merge-title-input", Input)
        title_input.value = ""
        # 同步保存到组状态
        self._group_state[self._current_index]['merged_title'] = ""
        # 聚焦到输入框，便于接下来的输入操作
        title_input.focus()

    @on(Button.Pressed, "#clear-title-btn")
    def on_clear_title_btn(self) -> None:
        """清除标题按钮"""
        self._clear_title()

    def _copy_focused_book_title(self) -> None:
        """复制当前光标所在行的书籍名称到剪贴板"""
        bid = self._get_cursor_book_id()
        if bid is None:
            return

        state = self._group_state[self._current_index]
        book = next((b for b in state['books'] if b.get('id') == bid), None)
        if not book:
            return

        novel_title = book.get('novel_title', '')
        if not novel_title:
            return

        try:
            import pyperclip
            pyperclip.copy(novel_title)
        except ImportError:
            import subprocess
            import platform
            system = platform.system()
            try:
                if system == 'Darwin':
                    subprocess.run(['pbcopy'], input=novel_title, text=True, check=True)
                elif system == 'Windows':
                    subprocess.run(['clip'], input=novel_title, text=True, check=True, shell=True)
                else:
                    try:
                        subprocess.run(['xclip', '-selection', 'clipboard'], input=novel_title, text=True, check=True)
                    except (subprocess.SubprocessError, FileNotFoundError):
                        subprocess.run(['xsel', '--clipboard', '--input'], input=novel_title, text=True, check=True)
            except Exception as copy_error:
                logger.error(f"复制书名到剪贴板失败: {copy_error}")
                self.notify(self.i18n.t('cannot_copy'), severity="error", timeout=2)
                return

        self.notify(
            self.i18n.t('crawler.title_copied', title=novel_title),
            timeout=2,
        )

    def on_key(self, event) -> None:
        """处理数字键快速定位"""
        if event.key == "escape":
            self.on_cancel_all()
            event.stop()
            return

        # 数字键 1-9：移动到对应行（1-based）
        if event.key.isdigit():
            pos = int(event.key)
            if 1 <= pos <= 9:
                state = self._group_state[self._current_index]
                if pos <= len(state['books']):
                    self._move_to_position(pos)
                    event.stop()

    # ─── 补缺功能 ───────────────────────────────────────────

    def _toggle_fill_missing(self) -> None:
        """切换补缺操作行的显示/隐藏"""
        self._fill_missing_visible = not self._fill_missing_visible
        try:
            container = self.query_one("#md-fill-missing-container")
            if self._fill_missing_visible:
                container.remove_class("hidden")
            else:
                container.add_class("hidden")
        except Exception:
            pass

    # ─── 搜索章节 ─────────────────────────────────────────
    def _open_search_chapters(self) -> None:
        """
        使用网站配置的搜索连接地址，以被补缺书籍书名（经智能搜索规范化）为关键词在浏览器中搜索章节。

        - 关键词处理与爬取管理页面的智能搜索一致：使用 normalize_book_title 规范化书名。
        - 搜索连接地址中的 {keyword} 占位符会被替换为 URL 编码后的关键词。
        - 若网站未配置搜索连接地址，提示"未配置搜索连接"。
        """
        site = self.novel_site or {}
        search_url = (site.get("search_url") or "").strip()
        if not search_url:
            self.notify(self.i18n.t('crawler.search_url_not_configured'), severity="warning", timeout=3)
            return

        # 被补缺书籍的书名：优先使用当前合并标题输入框内容，否则回退到组的基准/展示书名
        raw_title = ""
        try:
            title_input = self.query_one("#merge-title-input", Input)
            raw_title = title_input.value.strip()
        except Exception:
            pass
        if not raw_title:
            group = self.groups[self._current_index]
            raw_title = group.get('base_title') or group.get('display_title', '') or ''

        if not raw_title:
            self.notify(self.i18n.t('crawler.search_title_empty'), severity="warning", timeout=2)
            return

        # 智能搜索处理：规范化书名为搜索关键词（与爬取管理页面智能搜索一致）
        try:
            from src.ui.dialogs.crawler_merge_mode_dialog import normalize_book_title
            keyword = normalize_book_title(raw_title)
        except Exception as e:
            logger.debug(f"规范化书名失败，使用原始书名: {e}")
            keyword = raw_title
        if not keyword:
            keyword = raw_title

        from urllib.parse import quote
        encoded = quote(keyword)
        # 若地址包含 {keyword} 占位符则替换；否则直接把编码后的关键词追加到末尾
        if "{keyword}" in search_url:
            url = search_url.replace("{keyword}", encoded)
        else:
            url = search_url + encoded

        try:
            from src.utils.browser_manager import BrowserManager
            success = BrowserManager.open_url(url)
            if success:
                self.notify(
                    self.i18n.t('crawler.search_url_opened', keyword=keyword),
                    severity="information", timeout=3,
                )
            else:
                import webbrowser
                webbrowser.open(url)
                self.notify(
                    self.i18n.t('crawler.search_url_opened', keyword=keyword),
                    timeout=3,
                )
        except Exception as e:
            logger.error(f"打开搜索连接失败: {e}")
            self.notify(
                self.i18n.t('crawler.search_url_open_failed', error=str(e)),
                severity="error", timeout=3,
            )

    @on(Button.Pressed, "#fill-missing-btn")
    def on_fill_missing_btn(self) -> None:
        """补缺按钮"""
        self._toggle_fill_missing()

    @on(Button.Pressed, "#search-chapters-btn")
    def on_search_chapters_btn(self) -> None:
        """搜索章节按钮（位于补缺按钮前）"""
        self._open_search_chapters()

    def _get_crawler_manager(self):
        """延迟初始化 CrawlerManager"""
        if self._crawler_manager is None:
            try:
                from src.core.crawler_manager import CrawlerManager
                self._crawler_manager = CrawlerManager()
                self._crawler_manager.register_status_callback(self._on_crawl_status_change)
                self._crawler_manager.register_notification_callback(self._on_crawl_success_notify)
            except Exception as e:
                logger.error(f"初始化 CrawlerManager 失败: {e}")
        return self._crawler_manager

    def _on_crawl_status_change(self, task_id: str, task: Any) -> None:
        """爬取状态回调"""
        try:
            from src.core.crawler_manager import CrawlStatus

            if task_id != self.current_task_id:
                return

            if task.status in (CrawlStatus.COMPLETED, CrawlStatus.FAILED, CrawlStatus.STOPPED):
                self.is_crawling = False
                self.current_task_id = None
                if task.status == CrawlStatus.COMPLETED:
                    self.app.call_later(self._on_crawl_completed)
                    # 自动检查输入框中是否还有剩余ID，如果有则继续爬取（与爬取管理页面逻辑一致）
                    self.app.call_later(self._check_and_continue_crawl)
                elif task.status == CrawlStatus.FAILED:
                    self.app.call_later(
                        self.notify,
                        self.i18n.t('crawler.crawl_failed'),
                        severity="error", timeout=3,
                    )
                    self.app.call_later(self._update_crawl_button_state)
        except Exception as e:
            logger.error(f"爬取状态回调失败: {e}")

    def _on_crawl_completed(self) -> None:
        """爬取完成后的 UI 更新（在主线程中执行）"""
        try:
            self._update_crawl_button_state()
            self.notify(self.i18n.t('crawler.crawl_success'), timeout=3)
            self._refresh_books_from_db()
            # 隐藏补缺操作行
            if self._fill_missing_visible:
                self._fill_missing_visible = False
                try:
                    container = self.query_one("#md-fill-missing-container")
                    container.add_class("hidden")
                except Exception:
                    pass
            # 把新爬取的书籍并入排序，再重新生成智能标题
            self._smart_sort_books()
            self._refresh_table()
            self._apply_smart_title()
        except Exception as e:
            logger.error(f"爬取完成回调失败: {e}")

    def _check_and_continue_crawl(self) -> None:
        """检查输入框中是否还有新ID，如果有则继续爬取（与爬取管理页面逻辑一致）"""
        try:
            # 检查是否正在爬取
            if self.is_crawling:
                return

            # 获取输入框内容
            novel_id_input = self.query_one("#md-novel-id-input", Input)
            novel_ids_input = novel_id_input.value.strip()

            if not novel_ids_input:
                # 输入框为空，停止爬取
                return

            from urllib.parse import unquote
            # 分割多个小说ID
            novel_ids = [unquote(id.strip()) for id in novel_ids_input.split(',') if id.strip()]

            if not novel_ids:
                # 没有有效的ID，停止爬取
                return

            # 有剩余的ID，自动继续爬取
            logger.info(f"检测到输入框中还有 {len(novel_ids)} 个书籍ID，自动继续爬取")
            self.app.call_later(self._start_crawl)
        except Exception as e:
            logger.error(f"检查并继续爬取失败: {e}")

    def _on_crawl_success_notify(self, task_id: str, novel_id: str, novel_title: str, already_exists: bool) -> None:
        """爬取成功通知回调 —— 清理输入框中的已爬取ID"""
        try:
            self.app.call_later(self._remove_id_from_input, novel_id)
            self.app.call_later(
                self.notify,
                f"{self.i18n.t('crawler.crawl_success')}: {novel_title}",
                timeout=2,
            )
        except Exception:
            pass

    def _remove_id_from_input(self, novel_id: str) -> None:
        """从补缺输入框中移除指定的ID"""
        try:
            from urllib.parse import unquote
            decoded_novel_id = unquote(novel_id)
            novel_id_input = self.query_one("#md-novel-id-input", Input)
            current_value = novel_id_input.value.strip()

            ids = [unquote(id.strip()) for id in current_value.split(',') if id.strip()]
            filtered_ids = [id for id in ids if id != decoded_novel_id]

            if filtered_ids:
                novel_id_input.value = ', '.join(filtered_ids) + ','
            else:
                novel_id_input.value = ''
            novel_id_input.action_end()
        except Exception as e:
            logger.debug(f"从输入框中移除ID失败: {e}")

    def _refresh_books_from_db(self) -> None:
        """从数据库刷新当前组的书籍列表（仅添加本次爬取的书籍，追加到末尾，不自动选中）"""
        if not self.db_manager:
            return
        try:
            site_id = self.novel_site.get('id')
            if not site_id:
                return
            crawled_ids = self._crawling_novel_ids
            if not crawled_ids:
                return
            state = self._group_state[self._current_index]
            existing_db_ids = {b.get('id') for b in state['books']}
            existing_novel_ids = {b.get('novel_id') for b in state['books']}
            new_count = 0
            for novel_id in crawled_ids:
                # 跳过列表中已存在该 novel_id 的书籍
                if novel_id in existing_novel_ids:
                    continue
                # 按 novel_id 查询数据库
                records = self.db_manager.get_crawl_history_by_novel_id(site_id, novel_id)
                if records:
                    for item in records:
                        if item.get('id') not in existing_db_ids:
                            state['books'].append(item)
                            existing_db_ids.add(item.get('id'))
                            existing_novel_ids.add(item.get('novel_id'))
                            new_count += 1
            self._refresh_table()
            self._update_status()
            if new_count > 0:
                self.notify(
                    self.i18n.t('merge_detail.new_books_added', count=new_count),
                    timeout=3,
                )
            # 清空本次爬取记录
            self._crawling_novel_ids = []
        except Exception as e:
            logger.error(f"刷新书籍列表失败: {e}")

    def _update_crawl_button_state(self) -> None:
        """更新爬取按钮状态"""
        try:
            btn = self.query_one("#md-toggle-crawl-btn", Button)
            if self.is_crawling:
                btn.label = self.i18n.t('crawler.stop_crawl')
                btn.variant = "error"
            else:
                btn.label = self.i18n.t('crawler.start_crawl')
                btn.variant = "primary"
        except Exception:
            pass

    def _start_crawl(self) -> None:
        """开始爬取"""
        if not self.novel_site:
            self.notify(self.i18n.t('crawler.no_site_id'), severity="warning", timeout=2)
            return
        if self.is_crawling:
            self._stop_crawl()
            return

        try:
            novel_id_input = self.query_one("#md-novel-id-input", Input)
            novel_ids_input = novel_id_input.value.strip()
            if not novel_ids_input:
                self.notify(self.i18n.t('crawler.enter_novel_id'), severity="warning", timeout=2)
                return

            from urllib.parse import unquote
            novel_ids = [unquote(id.strip()) for id in novel_ids_input.split(',') if id.strip()]
            if not novel_ids:
                self.notify(self.i18n.t('crawler.enter_novel_id'), severity="warning", timeout=2)
                return

            site_id = self.novel_site.get('id')
            if not site_id:
                self.notify(self.i18n.t('crawler.no_site_id'), severity="warning", timeout=2)
                return

            # 检查代理要求
            proxy_config = {'enabled': False, 'proxy_url': ''}
            try:
                proxy_enabled = self.novel_site.get('proxy_enabled', False)
                if proxy_enabled and self.db_manager:
                    enabled_proxy = self.db_manager.get_enabled_proxy()
                    if enabled_proxy:
                        proxy_type = enabled_proxy.get('type', 'HTTP').lower()
                        host = enabled_proxy.get('host', '')
                        port = enabled_proxy.get('port', '')
                        username = enabled_proxy.get('username', '')
                        password = enabled_proxy.get('password', '')
                        if host and port:
                            if username and password:
                                proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
                            else:
                                proxy_url = f"{proxy_type}://{host}:{port}"
                            proxy_config = {'enabled': True, 'proxy_url': proxy_url}
            except Exception:
                pass

            crawler_manager = self._get_crawler_manager()
            if not crawler_manager:
                self.notify(self.i18n.t('crawler.start_crawl_failed'), severity="error", timeout=3)
                return

            self.is_crawling = True
            task_id = crawler_manager.start_crawl_task(site_id, novel_ids, proxy_config)
            if task_id:
                self.current_task_id = task_id
                self._crawling_novel_ids = novel_ids  # 记录本次爬取的书籍ID
                self._update_crawl_button_state()
                self.notify(
                    f"{self.i18n.t('crawler.starting_crawl')} ({len(novel_ids)} {self.i18n.t('crawler.books')})",
                    timeout=2,
                )
            else:
                self.is_crawling = False
                self.notify(self.i18n.t('crawler.start_crawl_failed'), severity="error", timeout=3)
        except Exception as e:
            self.is_crawling = False
            logger.error(f"启动爬取失败: {e}")
            self.notify(f"{self.i18n.t('crawler.start_crawl_failed')}: {e}", severity="error", timeout=3)

    def _stop_crawl(self) -> None:
        """停止爬取"""
        try:
            if self.current_task_id and self._crawler_manager:
                self._crawler_manager.stop_crawl_task(self.current_task_id)
            self.is_crawling = False
            self.current_task_id = None
            self._update_crawl_button_state()
            self.notify(self.i18n.t('crawler.crawl_stopped'), timeout=2)
        except Exception as e:
            logger.error(f"停止爬取失败: {e}")

    def _copy_novel_ids(self) -> None:
        """复制选中书籍的 novel_id 到剪贴板"""
        state = self._group_state[self._current_index]
        selected_ids = state['selected_ids']
        if not selected_ids:
            self.notify(self.i18n.t('batch_ops.no_selected_rows'), severity="warning", timeout=2)
            return

        book_ids = []
        for book in state['books']:
            if book.get('id') in selected_ids:
                nid = book.get('novel_id', '')
                if nid:
                    book_ids.append(str(nid))

        if not book_ids:
            self.notify(self.i18n.t('crawler.enter_novel_id'), severity="warning", timeout=2)
            return

        ids_text = ','.join(book_ids)
        try:
            import pyperclip
            pyperclip.copy(ids_text)
        except ImportError:
            import subprocess
            import platform
            system = platform.system()
            try:
                if system == 'Darwin':
                    subprocess.run(['pbcopy'], input=ids_text, text=True, check=True)
                else:
                    subprocess.run(['xclip', '-selection', 'clipboard'], input=ids_text, text=True, check=True)
            except Exception:
                subprocess.run(['xsel', '--clipboard', '--input'], input=ids_text, text=True, check=True)

        self.notify(
            self.i18n.t('crawler.copy_book_ids_success').format(count=len(book_ids)),
            timeout=2,
        )

    def _open_select_books_dialog(self) -> None:
        """打开选择书籍对话框"""
        if not self.novel_site:
            self.notify(self.i18n.t('crawler.no_site_id'), severity="warning", timeout=2)
            return
        if not self.novel_site.get("selectable_enabled", True):
            return

        from src.ui.dialogs.select_books_dialog import SelectBooksDialog

        def handle_result(result: Optional[str]) -> None:
            if result:
                try:
                    novel_id_input = self.query_one("#md-novel-id-input", Input)
                    existing = novel_id_input.value.strip()
                    if existing:
                        novel_id_input.value = f"{existing},{result}"
                    else:
                        novel_id_input.value = result
                except Exception:
                    pass

        self.app.push_screen(
            SelectBooksDialog(self.theme_manager, self.novel_site),
            handle_result,
        )

    def _init_browser_monitor(self) -> None:
        """初始化浏览器标签页监听器"""
        if not self.novel_site:
            return
        try:
            from src.utils.browser_tab_monitor import BrowserTabMonitor, BrowserType

            if self.selected_browser == "safari":
                browser_type = BrowserType.SAFARI
            elif self.selected_browser == "brave":
                browser_type = BrowserType.BRAVE
            else:
                browser_type = BrowserType.CHROME

            self.browser_monitor = BrowserTabMonitor(
                novel_sites=[self.novel_site],
                on_url_detected=self._on_browser_url_detected,
                headless=False,
                browser_type=browser_type,
            )
            self.browser_monitor.selected_window_index = self.selected_window_index  # type: ignore[assignment]
            self.browser_monitor.on_window_refresh_callback = self._on_window_refresh_from_monitor  # type: ignore[assignment]
            self._refresh_window_options()
        except Exception as e:
            logger.error(f"初始化浏览器监听器失败: {e}")
            self.browser_monitor = None

    def _on_browser_url_detected(self, novel_info: Dict[str, Any]) -> None:
        """浏览器 URL 检测回调 —— 将检测到的 novel_id 追加到输入框，并关闭标签页"""
        try:
            novel_id = novel_info.get('novel_id', '') if isinstance(novel_info, dict) else str(novel_info)
            url = novel_info.get('url', '') if isinstance(novel_info, dict) else ''
            if novel_id:
                self.app.call_later(self._append_detected_id, novel_id)
            # 关闭对应的标签页
            if url and self.browser_monitor:
                try:
                    self.browser_monitor.close_tab(url)
                except Exception as e:
                    logger.debug(f"关闭标签页失败: {e}")
        except Exception as e:
            logger.error(f"URL 检测回调失败: {e}")

    def _append_detected_id(self, novel_id: str) -> None:
        """将检测到的 novel_id 追加到输入框"""
        try:
            novel_id_input = self.query_one("#md-novel-id-input", Input)
            existing = novel_id_input.value.strip()
            if existing:
                parts = [p.strip() for p in existing.split(',')]
                if novel_id not in parts:
                    novel_id_input.value = f"{existing},{novel_id}"
                    self.notify(f"已添加ID: {novel_id}", timeout=2)
            else:
                novel_id_input.value = novel_id
                self.notify(f"已添加ID: {novel_id}", timeout=2)
        except Exception:
            pass

    def _on_window_refresh_from_monitor(self) -> None:
        """从后台线程刷新窗口列表"""
        try:
            self.app.call_from_thread(self._refresh_window_options)
        except Exception:
            pass

    def _refresh_window_options(self) -> None:
        """刷新窗口选择下拉框"""
        try:
            if not self.browser_monitor:
                return
            windows = self.browser_monitor.get_browser_windows()
            options = [(self.i18n.t('crawler.all_windows'), "all")]
            for win in windows:
                label = f"{self.i18n.t('crawler.window_label')} {win['index']} ({win['tab_count']} {self.i18n.t('crawler.tabs')})"
                if win.get('title'):
                    label += f" - {win['title'][:30]}"
                options.append((label, str(win['index'])))

            self.window_options = windows
            try:
                window_select = self.query_one("#md-window-select", Select)
                current_value = "all"
                if self.selected_window_index is not None:
                    current_value = str(self.selected_window_index)
                window_select.set_options(options)
                if current_value == "all" or any(str(w['index']) == current_value for w in windows):
                    window_select.value = current_value
                else:
                    window_select.value = "all"
                    self.selected_window_index = None
            except Exception:
                pass
        except Exception as e:
            logger.error(f"刷新窗口选项失败: {e}")

    def _toggle_browser_monitor(self) -> None:
        """切换浏览器监听状态"""
        try:
            if self.browser_monitor_active:
                self._stop_browser_monitor()
            else:
                self._start_browser_monitor()
        except Exception as e:
            logger.error(f"切换监听状态失败: {e}")

    def _start_browser_monitor(self) -> None:
        """开始监听"""
        try:
            if not self.browser_monitor:
                self._init_browser_monitor()
            if not self.browser_monitor:
                self.notify(self.i18n.t('crawler.monitor_start_failed'), severity="error", timeout=2)
                return

            self.browser_monitor.selected_window_index = self.selected_window_index  # type: ignore[assignment]
            success = self.browser_monitor.start_monitoring()
            if success:
                self.browser_monitor_active = True
                self._update_monitor_button_state()
                self.notify(self.i18n.t('crawler.monitor_started'), timeout=2)
            else:
                self.notify(self.i18n.t('crawler.monitor_start_failed'), severity="error", timeout=2)
        except Exception as e:
            logger.error(f"启动监听失败: {e}")
            self.notify(f"启动监听失败: {e}", severity="error", timeout=3)

    def _stop_browser_monitor(self) -> None:
        """停止监听"""
        try:
            if self.browser_monitor:
                self.browser_monitor.stop_monitoring()
            self.browser_monitor_active = False
            self._update_monitor_button_state()
            self.notify(self.i18n.t('crawler.monitor_stopped'), timeout=2)
        except Exception as e:
            logger.error(f"停止监听失败: {e}")

    def _update_monitor_button_state(self) -> None:
        """更新监听按钮状态"""
        try:
            btn = self.query_one("#md-toggle-monitor-btn", Button)
            if self.browser_monitor_active:
                btn.label = self.i18n.t('crawler.stop_monitor')
                btn.variant = "error"
            else:
                btn.label = self.i18n.t('crawler.start_monitor')
                btn.variant = "success"
        except Exception:
            pass

    # ─── 补缺按钮事件 ───────────────────────────────────────

    @on(Button.Pressed, "#md-choose-books-btn")
    def on_md_choose_books(self) -> None:
        self._open_select_books_dialog()

    @on(Button.Pressed, "#md-toggle-crawl-btn")
    def on_md_toggle_crawl(self) -> None:
        if self.is_crawling:
            self._stop_crawl()
        else:
            self._start_crawl()

    @on(Button.Pressed, "#md-copy-ids-btn")
    def on_md_copy_ids(self) -> None:
        self._copy_novel_ids()

    @on(Button.Pressed, "#md-toggle-monitor-btn")
    def on_md_toggle_monitor(self) -> None:
        self._toggle_browser_monitor()

    @on(Button.Pressed, "#md-refresh-window-btn")
    def on_md_refresh_window(self) -> None:
        if not self.browser_monitor:
            self._init_browser_monitor()
        self._refresh_window_options()

    @on(Select.Changed, "#md-browser-select")
    def on_md_browser_select_changed(self, event: Select.Changed) -> None:
        if event.value is not None:
            self.selected_browser = str(event.value)
            if self.browser_monitor:
                if self.browser_monitor_active:
                    self._stop_browser_monitor()
                self._init_browser_monitor()

    @on(Select.Changed, "#md-window-select")
    def on_md_window_select_changed(self, event: Select.Changed) -> None:
        if event.value is not None and event.value != "all":
            try:
                self.selected_window_index = int(str(event.value))
            except (ValueError, TypeError):
                self.selected_window_index = None
        else:
            self.selected_window_index = None
        if self.browser_monitor:
            self.browser_monitor.selected_window_index = self.selected_window_index  # type: ignore[assignment]

    # ─── 智能标题 ───────────────────────────────────────────

    def _smart_sort_books(self) -> bool:
        """
        按书名对当前组的书籍列表进行升序排序。
        
        优先级：
        1. 智能章节号排序（如 1-3, 4-6, 7-10）
        2. 回退：纯书名正序字符串排序

        Returns:
            True 表示已执行排序
        """
        state = self._group_state[self._current_index]
        books = state['books']

        if len(books) < 2:
            return False

        # 首先尝试智能章节号排序
        sorted_books, success = SmartTitleUtils.sort_books_by_chapter(books)
        if success:
            state['books'] = sorted_books
            return True
        
        # 智能排序失败，回退到按书名正序字符串排序
        books.sort(key=lambda b: b.get('novel_title', '').lower())
        return True

    def _generate_smart_title(self) -> Optional[str]:
        """
        从当前组选中的书籍中智能生成合并标题。
        
        使用 SmartTitleUtils 公共模块实现，支持：
        - 多种数字格式：阿拉伯、中文大小写、罗马数字
        - 章节标记识别：序、卷、部等
        - 智能范围合并
        """
        state = self._group_state[self._current_index]
        selected_ids = state['selected_ids']
        if len(selected_ids) < 2:
            return None

        selected_books = [b for b in state['books'] if b.get('id') in selected_ids]
        if len(selected_books) < 2:
            return None

        titles = [b.get('novel_title', '') for b in selected_books]
        if not all(titles):
            return None

        return SmartTitleUtils.generate_smart_title(titles)

    @on(Button.Pressed, "#smart-title-btn")
    def on_smart_title_btn(self) -> None:
        """智能标题按钮"""
        self._apply_smart_title()

    def _apply_smart_title(self) -> None:
        """生成智能标题填充到输入框（不改动书籍的现有排序，保留手动顺序）"""
        try:
            smart_title = self._generate_smart_title()
            if smart_title:
                title_input = self.query_one("#merge-title-input", Input)
                title_input.value = smart_title
                self._group_state[self._current_index]['merged_title'] = smart_title
                self.notify(
                    self.i18n.t('merge_detail.smart_title_applied', title=smart_title),
                    timeout=2,
                )
            else:
                self.notify(self.i18n.t('merge_detail.smart_title_failed'), severity="warning", timeout=2)
        except Exception as e:
            logger.error(f"智能标题生成失败: {e}")
            self.notify(self.i18n.t('merge_detail.smart_title_failed'), severity="warning", timeout=2)

    # ─── 快捷键 action 方法 ─────────────────────────────────

    def action_toggle_select_all(self) -> None:
        """a键：全选/取消全选切换（与合并模式弹窗一致）"""
        state = self._group_state[self._current_index]
        if state['selected_ids']:
            self.on_deselect_all()
        else:
            self.on_select_all()

    def action_merge_this(self) -> None:
        """g键：合并此组"""
        self.on_merge_this()

    def action_skip_this(self) -> None:
        """t键：跳过此组"""
        self.on_skip_this()

    def action_prev_group(self) -> None:
        """[键：返回上一组"""
        self.on_prev_group()

    def action_next_group(self) -> None:
        """]键：下一组"""
        self.on_next_group()

    def action_select_books(self) -> None:
        """X键：选择书籍"""
        self._open_select_books_dialog()

    def action_toggle_crawl(self) -> None:
        """s键：开始/停止爬取"""
        if self.is_crawling:
            self._stop_crawl()
        else:
            self._start_crawl()

    def action_toggle_monitor(self) -> None:
        """e键：开始/停止监听"""
        self._toggle_browser_monitor()

    def action_smart_title(self) -> None:
        """m键：智能标题"""
        self._apply_smart_title()

    def action_fill_missing(self) -> None:
        """f键：补缺"""
        self._toggle_fill_missing()

    def action_search_chapters(self) -> None:
        """S键：搜索章节（使用网站配置的搜索连接地址）"""
        self._open_search_chapters()

    def action_view_current_file(self) -> None:
        """F键：查看光标所在行的文件（在文件管理器中显示）"""
        book = self._get_cursor_book()
        if book is not None:
            self._view_file(book)

    def _view_file(self, book: Dict[str, Any]) -> None:
        """在文件管理器中显示书籍文件"""
        try:
            file_path = book.get('file_path', '')

            if not file_path or file_path == 'already_exists':
                self.notify(self.i18n.t('crawler.no_file_path'), severity="warning", timeout=2)
                return

            if not os.path.exists(file_path):
                self.notify(self.i18n.t('crawler.file_not_exists'), severity="warning", timeout=2)
                return

            import platform
            system = platform.system()

            if system == "Darwin":  # macOS
                os.system(f'open -R "{file_path}"')
            elif system == "Windows":
                os.system(f'explorer /select,"{file_path}"')
            elif system == "Linux":
                os.system(f'xdg-open "{os.path.dirname(file_path)}"')

            self.notify(self.i18n.t('crawler.file_opened'), timeout=2)
        except Exception as e:
            logger.error(f"查看文件失败: {e}")
            self.notify(
                f"{self.i18n.t('crawler.open_file_failed')}: {e}",
                severity="error", timeout=3,
            )
