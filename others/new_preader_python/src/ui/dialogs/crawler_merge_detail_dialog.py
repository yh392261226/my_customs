"""
合并详情弹窗 —— 允许用户逐组查看、排序、选择书籍后确认合并

流程：
1. 按组展示该组内所有书籍
2. 支持勾选/取消、上下移动排序
3. 输入合并后的书名
4. 合并当前组后自动进入下一组
"""

from copy import deepcopy
from typing import Dict, Any, List, Optional

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label, DataTable, Input, Static
from textual import on

from src.locales.i18n_manager import get_global_i18n
from src.utils.file_utils import FileUtils
from src.themes.theme_manager import ThemeManager
from src.ui.dialogs.crawler_merge_mode_dialog import BookGroup
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrawlerMergeDetailDialog(ModalScreen[Dict[str, Any]]):
    """合并详情弹窗 —— 逐组预览、排序、勾选后合并"""

    CSS_PATH = "../styles/crawler_merge_detail_dialog.tcss"

    BINDINGS = [
        ("escape", "cancel", "取消全部"),
        ("space", "toggle_row", "切换选择"),
        ("up", "move_up", "上移"),
        ("down", "move_down", "下移"),
        ("y", "copy_title", "复制标题"),
    ]

    def __init__(
        self,
        theme_manager: ThemeManager,
        groups: List[Dict[str, Any]],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme_manager = theme_manager
        self.i18n = get_global_i18n()

        # 深拷贝 groups，避免影响原始数据
        self.groups: List[Dict[str, Any]] = deepcopy(groups)
        self._current_index: int = 0       # 当前在第几组
        self._total_groups: int = len(groups)

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
            }

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
                    id="sort-buttons",
                ),
                # 快速定位行
                Horizontal(
                    Label(self.i18n.t('merge_detail.move_to_pos'), id="pos-label"),
                    Input(
                        placeholder=self.i18n.t('merge_detail.pos_placeholder'),
                        id="move-to-pos-input",
                        type="integer",
                    ),
                    id="pos-row",
                ),
                # 状态栏
                Label("", id="merge-detail-status"),
                # 底部操作按钮
                Horizontal(
                    Button(self.i18n.t('merge_detail.merge_this'), id="merge-this-btn", variant="primary"),
                    Button(self.i18n.t('merge_detail.skip_this'), id="skip-this-btn"),
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

        # 标题输入
        title_input = self.query_one("#merge-title-input", Input)
        title_input.value = state.get('merged_title', '')

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
            table.add_column("✓", width=3)
            table.add_column(self.i18n.t('merge_detail.col_seq'), width=4)
            table.add_column(self.i18n.t('merge_detail.col_title'), width=80)
            table.add_column(self.i18n.t('merge_detail.col_time'), width=10)
            table.add_column(self.i18n.t('merge_detail.col_size'), width=5)

        for idx, book in enumerate(books, 1):
            bid = book.get('id')
            check = "☑" if bid in selected else "☐"
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
                title[:60] if len(title) > 60 else title,
                crawl_time,
                size_str,
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
                "new_title": state.get('merged_title', group.get('base_title', '')),
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

    @on(Input.Submitted, "#move-to-pos-input")
    def on_pos_submitted(self, event: Input.Submitted) -> None:
        """输入目标位置并定位"""
        try:
            pos = int(event.value.strip())
            self._move_to_position(pos)
            # 清空输入框
            pos_input = self.query_one("#move-to-pos-input", Input)
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
