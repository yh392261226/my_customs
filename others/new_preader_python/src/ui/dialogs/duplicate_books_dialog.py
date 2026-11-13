"""
重复书籍对话框，用于显示和选择要删除的重复书籍
"""

import os
from typing import List, Dict, Any, Optional
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label, DataTable
from textual import on

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.book_duplicate_detector import BookDuplicateDetector, DuplicateGroup, DuplicateType
from src.core.book import Book
from src.ui.dialogs.confirm_dialog import ConfirmDialog
from src.ui.dialogs.book_comparison_dialog import BookComparisonDialog
from src.ui.messages import UpdateDuplicateGroupsMessage
from src.utils import dedup_staging
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DuplicateBooksDialog(ModalScreen[Dict[str, Any]]):
    """重复书籍对话框（支持取消后台任务）"""
    
    CSS_PATH = "../styles/duplicate_books_dialog.tcss"

    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
        ("space", "toggle_row", get_global_i18n().t('duplicate_books.toggle_row')),
        ("s", "select_current", get_global_i18n().t('duplicate_books.select_current')),
        ("a", "toggle_select_current_page", get_global_i18n().t('duplicate_books.toggle_select_current_page')),
        ("A", "toggle_select_all_pages", get_global_i18n().t('duplicate_books.toggle_select_all_pages')),
        ("v", "preview_current", get_global_i18n().t('common.preview')),
        ("n", "next_group", get_global_i18n().t('duplicate_books.next_group')),
        ("p", "prev_group", get_global_i18n().t('duplicate_books.prev_group')),
        ("t", "skip_group", get_global_i18n().t('common.skip_group')),
        ("F", "view_file_current", get_global_i18n().t('duplicate_books.view_file_current')),
        ("D", "select_current_group_recommended", get_global_i18n().t('duplicate_books.select_current_group_recommended')),
        ("y", "copy_current_title", get_global_i18n().t('common.copy_title')),
        ("u", "undo_last_delete", get_global_i18n().t('recycle_bin.undo_last')),
        ("ctrl+s", "save_staging", get_global_i18n().t('duplicate_books.staging')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, duplicate_groups: List[DuplicateGroup],
                 current_batch: int = 0, total_batches: int = 1, processing_remaining: bool = False,
                 elapsed_seconds: float = None, staging_state: Optional[Dict[str, Any]] = None):
        """
        初始化重复书籍对话框

        Args:
            theme_manager: 主题管理器
            duplicate_groups: 重复书籍组列表
            current_batch: 当前批次数(0表示初始批次,即哈希值或文件名相同的重复组)
            total_batches: 总批次数
            processing_remaining: 是否还有剩余批次需要处理
            elapsed_seconds: 对比/检测耗时（秒），为 None 时表示未知
            staging_state: 从去重暂存恢复出来的进度（存在时自动恢复到上次位置）
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.duplicate_groups = duplicate_groups
        self.selected_books: set[str] = set()  # 选中的书籍路径
        self.recommended_selected_books: set[str] = set()  # 推荐选中的书籍路径
        self.skipped_groups: set[frozenset] = set()  # 已跳过组的稳定标识（组内书籍路径集合），避免列表重排导致索引失效
        self.current_group_index = 0  # 当前显示的重复组索引
        self.current_batch = current_batch  # 当前批次数(0表示初始批次)
        self.total_batches = total_batches  # 总批次数
        self.processing_remaining = processing_remaining  # 是否还有剩余批次需要处理
        self.elapsed_seconds: float = elapsed_seconds  # 对比耗时（秒）
        
        # 【新增】实例级取消标志 - 用于通知后台线程停止
        self._is_cancelled = False

        # 记录所有组中推荐的删除书籍（供「选中推荐」按钮使用）
        for group in duplicate_groups:
            for book in group.recommended_to_delete:
                self.recommended_selected_books.add(book.path)

        # 【误操作防护】不再默认勾选「所有组」的推荐删除项。
        # 过去初始化时直接全选，用户只处理了当前组就点删除，会把后面
        # 大量尚未查看的组按推荐一并删掉。现在只预选打开时看到的第 1 组，
        # 其余组需要用户主动查看并用 D / 「选中推荐」确认。
        self.selected_books = set()
        self._viewed_groups: set[frozenset] = set()
        if duplicate_groups:
            for book in duplicate_groups[0].recommended_to_delete:
                self.selected_books.add(book.path)
            self._viewed_groups.add(self._group_key(duplicate_groups[0]))

        # 最近一次删除所属的回收站批次（用于一键撤销）
        self._last_recycle_batch_id: Optional[str] = None

        # 去重暂存：恢复信息（供 on_mount 提示）与检测是否完成的标记
        self._staging_restored_count = 0
        self._staging_complete = True
        self._staging_saved_at = ""
        if staging_state:
            self._apply_staging_state(staging_state)

    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        yield Header()
        yield Container(
            Vertical(
                # 标题和说明
                Label(get_global_i18n().t("duplicate_books.title")),
                Label(
                    get_global_i18n().t(
                        "duplicate_books.description", 
                        groups_count=len(self.duplicate_groups),
                        selected_count=len(self.selected_books)
                    ),
                    id="duplicate-books-description"
                ),
                
                # 重复组信息
                Label("", id="duplicate-group-info"),

                # 对比耗时信息
                Label("", id="duplicate-elapsed-info"),
                
                # 书籍对比表格
                DataTable(id="duplicate-books-table"),
                
                # 操作按钮：拆成两行，避免按钮过多时在窄终端里被挤出去
                Horizontal(
                    Button(get_global_i18n().t("duplicate_books.staging"), id="staging-btn", variant="success"),
                    Button(get_global_i18n().t("duplicate_books.compare_selected"), id="compare-btn", variant="primary"),
                    Button(get_global_i18n().t("duplicate_books.select_recommended"), id="select-recommended-btn", variant="primary"),
                    Button(get_global_i18n().t("common.deselect"), id="deselect-all-btn"),
                    Button(get_global_i18n().t("common.delete_selected"), id="delete-btn", variant="error"),
                    Button(get_global_i18n().t("duplicate_books.next_group"), id="next-group-btn"),
                    Button(get_global_i18n().t("duplicate_books.prev_group"), id="prev-group-btn"),
                    Button(get_global_i18n().t("common.skip_group"), id="skip-group-btn", variant="warning"),
                    Button(get_global_i18n().t("duplicate_books.deselect_before"), id="deselect-before-btn"),
                    Button(get_global_i18n().t("duplicate_books.deselect_after"), id="deselect-after-btn"),
                    Button(get_global_i18n().t("recycle_bin.undo_last"), id="undo-delete-btn"),
                    Button(get_global_i18n().t("common.cancel"), id="cancel-btn"),
                    id="duplicate-books-buttons"
                ),
                Horizontal(
                    id="duplicate-books-buttons-nav"
                ),
                
                # 状态信息
                Label("", id="duplicate-books-status"),
                id="duplicate-books-dialog-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 延迟初始化数据表，确保DOM完全构建
        self.set_timer(0.5, self._initialize_table)

        t = get_global_i18n().t
        if self._staging_restored_count:
            self.notify(
                t("duplicate_books.staging_restored",
                  count=self._staging_restored_count,
                  index=self.current_group_index + 1,
                  saved_at=self._staging_saved_at),
                timeout=5,
            )
        if not self._staging_complete:
            self.notify(
                t("duplicate_books.staging_incomplete", count=len(self.duplicate_groups)),
                severity="warning",
                timeout=6,
            )

    # ─── 去重暂存 ──────────────────────────────────────────

    def _refresh_description(self) -> None:
        """刷新顶部「找到 N 组 / 已选 N 本」说明"""
        try:
            self.query_one("#duplicate-books-description", Label).update(
                get_global_i18n().t(
                    "duplicate_books.description",
                    groups_count=len(self.duplicate_groups),
                    selected_count=len(self.selected_books),
                )
            )
        except Exception as e:
            logger.debug(f"刷新去重描述失败（可忽略）: {e}")

    def _apply_staging_state(self, state: Dict[str, Any]) -> None:
        """套用从暂存恢复的进度，并定位到上次的中断位置"""
        self.selected_books = set(state.get("selected_books", set()))
        self.recommended_selected_books = set(state.get("recommended_selected_books", set()))
        self.skipped_groups = set(state.get("skipped_groups", set()))
        self._viewed_groups = set(state.get("viewed_groups", set()))
        self.current_batch = int(state.get("current_batch", 0) or 0)
        self.total_batches = int(state.get("total_batches", 1) or 1)
        self.elapsed_seconds = state.get("elapsed_seconds")
        self._staging_restored_count = int(state.get("restored_count", len(self.duplicate_groups)) or 0)
        self._staging_complete = bool(state.get("complete", True))
        self._staging_saved_at = str(state.get("saved_at", ""))
        # 恢复自磁盘，本会话不启动后台检测
        self.processing_remaining = False

        last_index = max(0, min(
            int(state.get("current_group_index", 0) or 0),
            max(len(self.duplicate_groups) - 1, 0),
        ))
        target = last_index
        if self.duplicate_groups and self._group_key(self.duplicate_groups[last_index]) in self.skipped_groups:
            # 上次停留的组已跳过：优先跳到第一个未跳过且未查看的组；
            # 若都已查看过，则退回到第一个未跳过的组
            unprocessed = [
                i for i, g in enumerate(self.duplicate_groups)
                if self._group_key(g) not in self.skipped_groups
                and self._group_key(g) not in self._viewed_groups
            ]
            remaining = [
                i for i, g in enumerate(self.duplicate_groups)
                if self._group_key(g) not in self.skipped_groups
            ]
            target = (unprocessed or remaining or [last_index])[0]
        self.current_group_index = target

    def _staging_processed_count(self) -> int:
        """已查看或已跳过的分组数（用于暂存提示）"""
        keys = {self._group_key(g) for g in self.duplicate_groups}
        return len(keys & (self.skipped_groups | self._viewed_groups))

    def _save_staging_snapshot(self) -> bool:
        """保存检测结果 + 人工选择；没有剩余分组时直接清除暂存"""
        if not self.duplicate_groups:
            dedup_staging.clear_staging()
            return True
        snapshot = dedup_staging.build_snapshot(
            self.duplicate_groups,
            self.selected_books,
            self.recommended_selected_books,
            self.skipped_groups,
            self._viewed_groups,
            self.current_group_index,
            self.current_batch,
            self.total_batches,
            self.processing_remaining,
            self.elapsed_seconds,
        )
        return dedup_staging.save_staging(snapshot)

    def _sync_staging(self, clear: bool = False) -> None:
        """静默同步暂存：撤销恢复 / 全部处理完时清除，否则落盘当前进度"""
        if clear:
            dedup_staging.clear_staging()
        else:
            self._save_staging_snapshot()

    def _dismiss_with_sync(self, result: Dict[str, Any], clear: bool = False) -> None:
        """关闭前自动暂存，避免用户忘了点「暂存」又要重新检测一遍"""
        self._sync_staging(clear=clear)
        self.dismiss(result)

    def action_save_staging(self) -> None:
        """ctrl+s /「暂存」按钮：立即保存检测结果与人工处理进度"""
        t = get_global_i18n().t
        if self._save_staging_snapshot():
            self.notify(
                t("duplicate_books.staging_saved",
                  count=len(self.duplicate_groups),
                  processed=self._staging_processed_count()),
                severity="information",
                timeout=4,
            )
        else:
            self.notify(t("duplicate_books.staging_failed"), severity="error", timeout=4)

    @on(Button.Pressed, "#staging-btn")
    def on_staging_pressed(self) -> None:
        self.action_save_staging()

    def _initialize_table(self) -> None:
        """延迟初始化数据表"""
        try:
            # 尝试使用更基础的方法查找表格
            table = None
            for widget in self.walk_children():
                if hasattr(widget, "id") and widget.id == "duplicate-books-table":
                    table = widget
                    break
            
            if not table:
                logger.error("无法找到DataTable组件")
                self.notify("无法初始化重复书籍对话框", severity="error")
                return
            
            # 清除现有列
            table.clear(columns=True)
            
            # 添加列
            table.add_column(get_global_i18n().t("batch_ops.index"), key="index")
            table.add_column(get_global_i18n().t("common.bookshelf"), key="title")
            table.add_column(get_global_i18n().t("common.author"), key="author")
            table.add_column(get_global_i18n().t("common.size"), key="size")
            table.add_column(get_global_i18n().t("common.format"), key="format")
            table.add_column(get_global_i18n().t("duplicate_books.recommended"), key="recommended")
            table.add_column(get_global_i18n().t("common.view_file"), key="view_action")  # 查看文件按钮列
            table.add_column(get_global_i18n().t("common.preview"), key="preview")  # 预览按钮列
            table.add_column(get_global_i18n().t("common.checked"), key="selected")
            
            # 启用隔行变色效果
            table.zebra_stripes = True
            
            # 设置表格选择模式
            try:
                # 使用列选择模式，以便能够点击特定列（如查看文件按钮）
                table.cursor_type = "cell"
                table.show_cursor = True
            except AttributeError as e:
                logger.warning(f"表格不支持某些选择属性: {e}")
            
            # 如果有重复组，显示当前组（从暂存恢复时是上次停留的组，而不是第一组）
            if self.duplicate_groups:
                self._display_duplicate_group(self.current_group_index)
                self._refresh_description()
            
            # 确保表格获得焦点
            try:
                table.focus()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"初始化数据表失败: {e}")
            self.notify("无法初始化重复书籍对话框", severity="error")
    
    def _display_duplicate_group(self, group_index: int, preserve_cursor: Optional[bool] = None) -> None:
        """显示指定索引的重复组
        
        Args:
            group_index: 组索引
            preserve_cursor: 是否保持原有光标位置；None 表示只在组未切换时保持
                （刷新同一组时保持光标，切换组时回到第一行）
        """
        if not self.duplicate_groups or group_index < 0 or group_index >= len(self.duplicate_groups):
            return
        
        if preserve_cursor is None:
            # 同一组内刷新（如空格切换选中）保持光标；切换到其它组时回到第一行
            preserve_cursor = (group_index == self.current_group_index)
        
        self.current_group_index = group_index
        group = self.duplicate_groups[group_index]
        # 标记为「已查看」，删除确认中会提示尚未查看组的选中项
        self._viewed_groups.add(self._group_key(group))
        
        # 更新组信息
        group_info_label = self.query_one("#duplicate-group-info", Label)
        duplicate_type_text = ""
        if group.duplicate_type == DuplicateType.FILE_NAME:
            duplicate_type_text = get_global_i18n().t("duplicate_books.type_file_name")
        elif group.duplicate_type == DuplicateType.CONTENT_SIMILAR:
            duplicate_type_text = get_global_i18n().t("duplicate_books.type_content_similar", similarity=f"{group.similarity:.1%}")
        elif group.duplicate_type == DuplicateType.HASH_IDENTICAL:
            duplicate_type_text = get_global_i18n().t("duplicate_books.type_hash_identical")
        elif group.duplicate_type == DuplicateType.CONTENT_SUBSET:
            duplicate_type_text = get_global_i18n().t("duplicate_books.type_content_subset", similarity=f"{group.similarity:.1%}")
        
        skip_mark = "（已跳过）" if self._group_key(group) in self.skipped_groups else ""
        group_info_label.update(
            get_global_i18n().t(
                "duplicate_books.group_info",
                current_group=group_index + 1,
                total_groups=len(self.duplicate_groups),
                duplicate_type=duplicate_type_text,
                books_count=len(group.books)
            ) + skip_mark
        )
        
        # 更新书籍表格
        table = None
        for widget in self.walk_children():
            if hasattr(widget, "id") and widget.id == "duplicate-books-table":
                table = widget
                break
        
        if not table:
            logger.error("无法找到DataTable组件")
            return
        
        # 记录当前光标位置：下面会清空并重建所有行，光标会被重置到第一行
        prev_cursor_row = getattr(table, "cursor_row", None)
        prev_cursor_column = getattr(table, "cursor_column", None)
        
        # 准备所有行数据和选中的键
        rows_data = []
        selected_keys = set()
        
        for i, book in enumerate(group.books):
            # 检查是否为推荐的保留书籍
            is_recommended_keep = book in group.recommended_to_keep
            recommended_text = "保留" if is_recommended_keep else "删除"
            
            # 检查是否被选中（不再强制添加推荐书籍，让用户自由选择）
            is_selected = book.path in self.selected_books
            if is_selected:
                selected_keys.add(book.path)
            
            # 获取文件大小
            size_str = ""
            try:
                if hasattr(book, 'size') and book.size:
                    # 格式化文件大小
                    if book.size < 1024 * 1024:  # 小于1MB
                        size_kb = book.size / 1024.0
                        size_str = f"{size_kb:.1f} KB"
                    else:
                        size_mb = book.size / (1024.0 * 1024.0)
                        size_str = f"{size_mb:.1f} MB"
            except:
                size_str = "未知"
            
            # 添加查看文件按钮
            view_file_button = f"[{get_global_i18n().t('common.view_file')}]"
            # 添加预览按钮
            preview_button = f"[{get_global_i18n().t('common.preview')}]"
            
            # 准备行数据 - 使用书籍路径作为键
            try:
                rows_data.append(
                    (book.path,  # 键
                    str(i + 1),
                    book.title,
                    book.author,
                    size_str,
                    book.format.upper() if book.format else "",
                    recommended_text,
                    view_file_button,  # 查看文件按钮
                    preview_button,    # 预览按钮
                    "✓" if is_selected else "□")  # 直接在这里设置选中标记
                )
            except Exception as e:
                # 如果出错，跳过这本书
                logger.warning(f"准备行数据时出错: {book.path}, 错误: {e}")
                continue
        
        # 清空表格
        table.clear()
        
        # 直接添加所有行，选中标记已在准备数据时设置
        for row_data in rows_data:
            try:
                # 获取书籍路径
                book_path = row_data[0]
                
                # 添加行，使用书籍路径作为键
                table.add_row(
                    str(row_data[1]),  # 索引
                    row_data[2],       # 书名
                    row_data[3],       # 作者
                    row_data[4],       # 大小
                    row_data[5],       # 格式
                    row_data[6],       # 推荐
                    row_data[7],       # 查看文件按钮
                    row_data[8],       # 预览按钮
                    row_data[9],       # 选中标记（已在准备数据时设置）
                    key=book_path      # 使用书籍路径作为键
                )
            except Exception as add_error:
                logger.warning(f"添加行时出错: {add_error}")
                continue
        
        # 恢复光标位置：重建行后光标会被重置到第一行，这里还原到原来的行列
        if preserve_cursor:
            self._restore_table_cursor(table, prev_cursor_row, prev_cursor_column)
        
        # 更新状态信息
        self._update_status()
    
    @staticmethod
    def _restore_table_cursor(table, row: Optional[int], column: Optional[int] = None) -> None:
        """把表格光标恢复到指定行列（行不存在时收敛到最近的有效行）"""
        if row is None:
            return
        try:
            row_count = len(table.rows) if hasattr(table, "rows") else 0
            if row_count <= 0:
                return
            target_row = max(0, min(int(row), row_count - 1))
            move_kwargs = {"row": target_row}
            if column is not None:
                column_count = len(table.columns) if hasattr(table, "columns") else 0
                if column_count > 0:
                    move_kwargs["column"] = max(0, min(int(column), column_count - 1))
            table.move_cursor(**move_kwargs)
        except Exception as e:
            logger.debug(f"恢复表格光标失败（可忽略）: {e}")
    
    @staticmethod
    def _group_key(group) -> frozenset:
        """生成组的稳定标识：组内所有书籍路径的集合（不依赖列表位置，列表重排也不会失效）"""
        return frozenset(book.path for book in group.books)

    def _is_path_skipped(self, path: str) -> bool:
        """判断某书籍路径是否属于任一被跳过的组"""
        return any(path in key for key in self.skipped_groups)

    def _update_status(self) -> None:
        """更新状态信息"""
        status_label = None
        elapsed_label = None
        for widget in self.walk_children():
            if hasattr(widget, "id") and widget.id == "duplicate-books-status":
                status_label = widget
            elif hasattr(widget, "id") and widget.id == "duplicate-elapsed-info":
                elapsed_label = widget
        
        if not status_label:
            logger.error("无法找到状态标签组件")
            return
        
        # 计算当前组中选中的书籍数量（排除被跳过组的书籍）
        current_group = self.duplicate_groups[self.current_group_index]
        current_group_selected = sum(1 for book in current_group.books if book.path in self.selected_books)

        # 总选中数也排除被跳过组的书籍（用稳定组 key，避免列表重排后索引越界）
        skipped_paths = set()
        for key in self.skipped_groups:
            skipped_paths.update(key)
        total_selected = sum(1 for p in self.selected_books if p not in skipped_paths)

        status_label.update(
            get_global_i18n().t(
                "duplicate_books.status_info",
                total_selected=total_selected,
                current_group_selected=current_group_selected
            )
        )

        # 显示对比耗时
        if elapsed_label is not None:
            if self.elapsed_seconds is not None:
                elapsed_label.update(
                    get_global_i18n().t(
                        "duplicate_books.elapsed_info",
                        seconds=f"{self.elapsed_seconds:.1f}"
                    )
                )
            else:
                elapsed_label.update("")
    
    def action_cancel(self) -> None:
        """取消操作 - 停止后台检测线程并退出"""
        # 【关键】设置取消标志，通知后台线程停止
        self._is_cancelled = True
        DuplicateBooksDialog._cancel_requested = True  # 类级别标志
        
        logger.info("用户按ESC取消去重操作，正在停止后台检测...")
        
        try:
            # 尝试通知父对话框也设置取消标志
            parent_screen = self.app.screen_stack[-2] if len(self.app.screen_stack) > 1 else None
            if hasattr(parent_screen, '_duplicate_cancel_requested'):
                parent_screen._duplicate_cancel_requested = True
        except Exception:
            pass
        
        # 立即关闭对话框（不等待后台线程）；已检测出的分组与选择自动暂存
        self._dismiss_with_sync({"refresh": False, "cancelled": True})
    
    def action_toggle_row(self) -> None:
        """切换当前行选中状态"""
        try:
            table = self.query_one("#duplicate-books-table", DataTable)
            
            # 获取当前光标所在的行
            current_row_index = getattr(table, 'cursor_row', None)
            
            # 如果无法确定当前行，显示提示信息
            if current_row_index is None or not (0 <= current_row_index < len(table.rows)):
                self.notify("请先选择一行", severity="warning")
                return
            
            # 获取行键
            row_keys = list(table.rows.keys())
            row_key = row_keys[current_row_index]
            
            # 切换选中状态
            if hasattr(row_key, 'value') and row_key.value:
                book_path = str(row_key.value)
            else:
                book_path = str(row_key)
            
            if book_path in self.selected_books:
                self.selected_books.remove(book_path)
            else:
                self.selected_books.add(book_path)
            
            # 重新加载表格显示
            self._display_duplicate_group(self.current_group_index)
        except Exception as e:
            logger.error(f"切换当前行选中状态失败: {e}")
    
    def action_select_current(self) -> None:
        """选择当前行"""
        self.action_toggle_row()  # 复用切换行的处理逻辑

    def action_toggle_select_current_page(self) -> None:
        """a键 - 全选/取消全选当前页（当前重复组）
        当前页有任意选中项时取消全选当前页；无任何选中项时全选当前页
        """
        if not self.duplicate_groups or self.current_group_index < 0 \
                or self.current_group_index >= len(self.duplicate_groups):
            return

        current_group = self.duplicate_groups[self.current_group_index]
        current_books = current_group.books
        if not current_books:
            return

        # 当前页有任意选中项则取消全选当前页，否则全选当前页
        has_selected = any(book.path in self.selected_books for book in current_books)
        if has_selected:
            removed = 0
            for book in current_books:
                if book.path in self.selected_books:
                    self.selected_books.discard(book.path)
                    removed += 1
            self.notify(
                get_global_i18n().t(
                    "duplicate_books.deselect_current_page_all",
                    count=removed
                ),
                severity="information"
            )
        else:
            added = 0
            for book in current_books:
                if book.path not in self.selected_books:
                    self.selected_books.add(book.path)
                    added += 1
            self.notify(
                get_global_i18n().t(
                    "duplicate_books.select_current_page_all",
                    count=added
                ),
                severity="information"
            )

        # 重新加载当前组显示
        self._display_duplicate_group(self.current_group_index)

    def action_toggle_select_all_pages(self) -> None:
        """A键 - 全选/取消全选全部页（所有重复组）
        有任意选中项时取消全选（清空所有选择）；无任何选中项时全选所有组
        """
        # 有任意选中项则取消全选（清空所有选择），否则全选所有组
        if self.selected_books:
            total = len(self.selected_books)
            self.selected_books.clear()
            self.notify(
                get_global_i18n().t(
                    "duplicate_books.deselect_all_pages_all",
                    count=total
                ),
                severity="information"
            )
        else:
            all_books = []
            for group in self.duplicate_groups:
                all_books.extend(group.books)

            if not all_books:
                return

            added = 0
            for book in all_books:
                if book.path not in self.selected_books:
                    self.selected_books.add(book.path)
                    added += 1
            self.notify(
                get_global_i18n().t(
                    "duplicate_books.select_all_pages_all",
                    count=added
                ),
                severity="information"
            )

        # 重新加载当前组显示
        self._display_duplicate_group(self.current_group_index)

    def action_preview_current(self) -> None:
        """v键 - 预览当前光标所在行的书籍内容"""
        try:
            table = self.query_one("#duplicate-books-table", DataTable)
            
            # 获取当前光标所在的行
            current_row_index = getattr(table, 'cursor_row', None)
            
            if current_row_index is None or not (0 <= current_row_index < len(table.rows)):
                self.notify("请先选择一行", severity="warning")
                return
            
            # 获取行键
            row_keys = list(table.rows.keys())
            row_key = row_keys[current_row_index]
            
            # 获取书籍路径
            if hasattr(row_key, 'value') and row_key.value:
                book_path = str(row_key.value)
            else:
                book_path = str(row_key)
            
            # 获取当前组的书籍对象
            if not self.duplicate_groups or self.current_group_index < 0 or self.current_group_index >= len(self.duplicate_groups):
                return
            
            group = self.duplicate_groups[self.current_group_index]
            book = None
            for b in group.books:
                if b.path == book_path:
                    book = b
                    break
            
            if not book:
                self.notify("未找到对应的书籍", severity="warning")
                return
            
            # 调用预览方法
            self._preview_book(book)
            
        except Exception as e:
            logger.error(f"预览当前行失败: {e}")
            self.notify(f"预览失败: {e}", severity="error")

    def action_view_file_current(self) -> None:
        """F键 - 查看当前光标所在行的书籍文件"""
        try:
            table = self.query_one("#duplicate-books-table", DataTable)

            # 获取当前光标所在的行
            current_row_index = getattr(table, 'cursor_row', None)

            if current_row_index is None or not (0 <= current_row_index < len(table.rows)):
                self.notify(get_global_i18n().t("duplicate_books.view_file_no_row"), severity="warning")
                return

            # 获取行键
            row_keys = list(table.rows.keys())
            row_key = row_keys[current_row_index]

            # 获取书籍路径
            if hasattr(row_key, 'value') and row_key.value:
                book_path = str(row_key.value)
            else:
                book_path = str(row_key)

            # 校验路径确实属于当前组（避免越界/错位）
            if not self.duplicate_groups or self.current_group_index < 0 or self.current_group_index >= len(self.duplicate_groups):
                self.notify(get_global_i18n().t("duplicate_books.view_file_no_row"), severity="warning")
                return

            group = self.duplicate_groups[self.current_group_index]
            if not any(b.path == book_path for b in group.books):
                self.notify(get_global_i18n().t("duplicate_books.view_file_no_row"), severity="warning")
                return

            # 在文件管理器中定位该文件
            self._view_file(book_path)

        except Exception as e:
            logger.error(f"查看当前行文件失败: {e}")
            self.notify(f"查看文件失败: {e}", severity="error")

    def action_select_current_group_recommended(self) -> None:
        """D键 - 自动选中当前组中的推荐删除书籍"""
        try:
            if not self.duplicate_groups or self.current_group_index < 0 or self.current_group_index >= len(self.duplicate_groups):
                return

            group = self.duplicate_groups[self.current_group_index]
            recommended_paths = {book.path for book in group.recommended_to_delete}

            if not recommended_paths:
                self.notify(
                    get_global_i18n().t("duplicate_books.select_recommended_current_group_none"),
                    severity="information",
                )
                return

            # 将当前组推荐删除的书籍加入选中集合
            self.selected_books.update(recommended_paths)

            # 重新加载当前组表格显示（同步勾选状态）并更新统计信息
            self._display_duplicate_group(self.current_group_index)
            self._update_status()

            self.notify(
                get_global_i18n().t(
                    "duplicate_books.select_recommended_current_group",
                    count=len(recommended_paths),
                ),
                severity="information",
            )

        except Exception as e:
            logger.error(f"选中当前组推荐失败: {e}")
            self.notify(f"选中推荐失败: {e}", severity="error")

    def action_copy_current_title(self) -> None:
        """y键 - 复制当前光标所在行的书籍标题"""
        try:
            if not self.duplicate_groups or self.current_group_index < 0 or self.current_group_index >= len(self.duplicate_groups):
                return

            table = self.query_one("#duplicate-books-table", DataTable)
            current_row_index = getattr(table, 'cursor_row', None)

            if current_row_index is None or not (0 <= current_row_index < len(table.rows)):
                self.notify(get_global_i18n().t("duplicate_books.copy_title_no_row"), severity="warning")
                return

            # 通过行键（书籍路径）在当前组中查找书籍，获取其标题
            row_keys = list(table.rows.keys())
            row_key = row_keys[current_row_index]
            if hasattr(row_key, 'value') and row_key.value:
                book_path = str(row_key.value)
            else:
                book_path = str(row_key)

            group = self.duplicate_groups[self.current_group_index]
            book = next((b for b in group.books if b.path == book_path), None)
            if book is None:
                self.notify(get_global_i18n().t("duplicate_books.copy_title_no_row"), severity="warning")
                return

            title = getattr(book, 'title', '') or ''
            if not title:
                self.notify(get_global_i18n().t("duplicate_books.copy_title_empty"), severity="warning")
                return

            # 复制到剪贴板（优先 pyperclip，回退到系统命令）
            try:
                import pyperclip
                pyperclip.copy(title)
            except ImportError:
                import subprocess
                import platform
                system = platform.system()
                try:
                    if system == 'Darwin':
                        subprocess.run(['pbcopy'], input=title, text=True, check=True)
                    elif system == 'Windows':
                        subprocess.run(['clip'], input=title, text=True, check=True, shell=True)
                    else:
                        try:
                            subprocess.run(['xclip', '-selection', 'clipboard'], input=title, text=True, check=True)
                        except (subprocess.SubprocessError, FileNotFoundError):
                            subprocess.run(['xsel', '--clipboard', '--input'], input=title, text=True, check=True)
                except Exception as copy_error:
                    logger.error(f"复制标题到剪贴板失败: {copy_error}")
                    self.notify(get_global_i18n().t("duplicate_books.copy_title_failed"), severity="error")
                    return

            self.notify(
                get_global_i18n().t("duplicate_books.copy_title_success", title=title),
                severity="information",
            )

        except Exception as e:
            logger.error(f"复制当前行标题失败: {e}")
            self.notify(f"复制标题失败: {e}", severity="error")

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self) -> None:
        """取消按钮按下时的回调（自动暂存当前进度）"""
        self._dismiss_with_sync({"refresh": False})
    
    @on(Button.Pressed, "#next-group-btn")
    def on_next_group_pressed(self) -> None:
        """下一组按钮按下时的回调"""
        if self.current_group_index < len(self.duplicate_groups) - 1:
            self._display_duplicate_group(self.current_group_index + 1)
    
    @on(Button.Pressed, "#prev-group-btn")
    def on_prev_group_pressed(self) -> None:
        """上一组按钮按下时的回调"""
        if self.current_group_index > 0:
            self._display_duplicate_group(self.current_group_index - 1)

    def action_next_group(self) -> None:
        """快捷键 n：下一组"""
        if self.current_group_index < len(self.duplicate_groups) - 1:
            self._display_duplicate_group(self.current_group_index + 1)

    def action_prev_group(self) -> None:
        """快捷键 p：上一组"""
        if self.current_group_index > 0:
            self._display_duplicate_group(self.current_group_index - 1)

    def action_skip_group(self) -> None:
        """快捷键 k：跳过当前组（组内书籍无论是否选中都不删除）"""
        idx = self.current_group_index
        if idx < 0 or idx >= len(self.duplicate_groups):
            return
        group = self.duplicate_groups[idx]
        # 记录跳过用的是稳定组 key（组内书籍路径集合），列表重排后依然有效
        self.skipped_groups.add(self._group_key(group))
        for book in group.books:
            self.selected_books.discard(book.path)
        logger.info(f"跳过重复组 {idx + 1}/{len(self.duplicate_groups)}: {group.books[0].file_name}")
        if self.current_group_index < len(self.duplicate_groups) - 1:
            self._display_duplicate_group(self.current_group_index + 1)
        else:
            self._update_status()
    
    @on(Button.Pressed, "#skip-group-btn")
    def on_skip_group_pressed(self) -> None:
        """跳过按钮回调"""
        self.action_skip_group()

    def _deselect_groups_range(self, before: bool) -> None:
        """取消当前组之前/之后所有组内书籍的选中状态（不含当前组）"""
        if not self.duplicate_groups:
            return
        idx = self.current_group_index
        target_groups = (
            self.duplicate_groups[:idx] if before
            else self.duplicate_groups[idx + 1:]
        )
        paths = {book.path for group in target_groups for book in group.books}
        removed = len(paths & self.selected_books)
        self.selected_books.difference_update(paths)

        # 刷新表格勾选标记、状态栏与顶部说明
        self._display_duplicate_group(self.current_group_index)
        self._refresh_description()

        key = "duplicate_books.deselect_before_result" if before else "duplicate_books.deselect_after_result"
        self.notify(
            get_global_i18n().t(key, groups=len(target_groups), count=removed),
            timeout=3,
        )

    @on(Button.Pressed, "#deselect-before-btn")
    def on_deselect_before_pressed(self) -> None:
        """取消当前组之前所有组的选中状态"""
        self._deselect_groups_range(before=True)

    @on(Button.Pressed, "#deselect-after-btn")
    def on_deselect_after_pressed(self) -> None:
        """取消当前组之后所有组的选中状态"""
        self._deselect_groups_range(before=False)

    @on(Button.Pressed, "#select-recommended-btn")
    def on_select_recommended_pressed(self) -> None:
        """选择推荐按钮按下时的回调"""
        # 清除所有选择
        self.selected_books.clear()
        
        # 选择所有推荐的删除书籍
        for group in self.duplicate_groups:
            for book in group.recommended_to_delete:
                self.selected_books.add(book.path)
        
        # 重新加载当前组显示
        self._display_duplicate_group(self.current_group_index)
    
    @on(Button.Pressed, "#deselect-all-btn")
    def on_deselect_all_pressed(self) -> None:
        """取消全选按钮按下时的回调"""
        # 清除所有选择
        self.selected_books.clear()
        
        # 重新加载当前组显示
        self._display_duplicate_group(self.current_group_index)
    
    @on(DataTable.RowSelected, "#duplicate-books-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """表格行选中时的回调"""
        # 处理行选择事件，但不处理列点击
        # 列点击由CellSelected事件处理
        # 这里只处理空格键等直接触发的行选择事件
        pass
    
    @on(Button.Pressed, "#compare-btn")
    def on_compare_pressed(self) -> None:
        """比较按钮按下时的回调"""
        # 获取选中的书籍
        current_group = self.duplicate_groups[self.current_group_index]
        selected_books = [book for book in current_group.books if book.path in self.selected_books]
        
        if len(selected_books) < 2:
            self.notify(get_global_i18n().t("duplicate_books.compare_need_at_least_two"), severity="warning")
            return
        
        if len(selected_books) > 2:
            self.notify(get_global_i18n().t("duplicate_books.compare_max_two"), severity="warning")
            return
        
        # 显示比较对话框
        comparison_dialog = BookComparisonDialog(self.theme_manager, selected_books[0], selected_books[1])
        self.app.push_screen(comparison_dialog)
    
    @on(Button.Pressed, "#delete-btn")
    def on_delete_pressed(self) -> None:
        """删除按钮按下时的回调"""
        if not self.selected_books:
            self.notify(get_global_i18n().t("duplicate_books.no_books_selected"), severity="warning")
            return
        
        # 删除确认：显式提示「尚未查看的组」以及回收站可撤销，避免误删
        t = get_global_i18n().t
        selected_for_delete = [p for p in self.selected_books if not self._is_path_skipped(p)]
        unreviewed = [
            p for p in selected_for_delete
            if not any(p in key for key in self._viewed_groups)
        ]
        message = t("duplicate_books.delete_confirm_message", count=len(selected_for_delete))
        if unreviewed:
            message += "\n" + t("recycle_bin.delete_unreviewed_warning", count=len(unreviewed))
        message += "\n" + t("recycle_bin.undo_hint")

        confirm_dialog = ConfirmDialog(
            self.theme_manager,
            t("duplicate_books.delete_confirm"),
            message,
        )
        
        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                # 执行删除操作
                self._delete_selected_books()
        
        self.app.push_screen(confirm_dialog, on_confirm)

    def action_undo_last_delete(self) -> None:
        """u 键 - 撤销最近一次批量去重删除（整批恢复）。"""
        t = get_global_i18n().t
        batch_id = self._last_recycle_batch_id
        if not batch_id:
            self.notify(t("recycle_bin.no_undo"), severity="warning")
            return

        def on_confirm(confirmed: Optional[bool]) -> None:
            if not confirmed:
                return
            from src.core.recycle_bin import get_recycle_bin
            from src.ui.messages import RefreshBookshelfMessage

            bookshelf = getattr(self.app, "bookshelf", None)
            result = get_recycle_bin(
                getattr(bookshelf, "db_manager", None) if bookshelf is not None else None
            ).restore_batch(batch_id)
            self._last_recycle_batch_id = None
            try:
                self.app.bookshelf._load_books()
                self.app.post_message(RefreshBookshelfMessage())
            except Exception:
                pass
            self.notify(t("recycle_bin.undo_success", count=result.get("ok", 0)),
                        severity="information")
            # 恢复后原有重复组缓存已失效，清除暂存并关闭对话框让用户重新检测
            self._dismiss_with_sync({"refresh": True, "reopen_deduplicate": True}, clear=True)

        self.app.push_screen(
            ConfirmDialog(
                self.theme_manager,
                t("recycle_bin.undo_confirm"),
                t("recycle_bin.undo_confirm_message"),
            ),
            on_confirm,
        )

    @on(Button.Pressed, "#undo-delete-btn")
    def on_undo_delete_pressed(self) -> None:
        self.action_undo_last_delete()

    def _delete_selected_books(self) -> None:
        """删除选中的书籍（整批进回收站，可一键撤销）"""
        try:
            deleted_count = 0
            failed_count = 0
            
            # 获取书库对象
            bookshelf = getattr(self.app, "bookshelf", None)
            if not bookshelf:
                logger.error("无法获取书库对象")
                self.notify("无法获取书库对象", severity="error")
                return

            # 整次删除共用一个回收站批次，可整体恢复
            from src.core.recycle_bin import OP_DEDUPLICATE, get_recycle_bin
            batch_id = get_recycle_bin(bookshelf.db_manager).create_batch(
                OP_DEDUPLICATE, "批量去重删除"
            )

            # 记录被删除的书籍路径
            deleted_book_paths = set()

            # 跳过组内的书籍不参与删除（用稳定组 key 判断，避免列表重排后索引越界）
            selected_for_delete = [p for p in self.selected_books if not self._is_path_skipped(p)]

            for book_path in selected_for_delete:
                try:
                    # 文件与数据库记录统一交给回收站处理；
                    # 文件已不存在时也能删掉书库里的残留记录。
                    if bookshelf.remove_book(
                        book_path,
                        delete_file=True,
                        operation=OP_DEDUPLICATE,
                        reason="重复组推荐删除",
                        batch_id=batch_id,
                    ):
                        deleted_count += 1
                        deleted_book_paths.add(book_path)
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"删除书籍失败: {book_path}, 错误: {e}")
                    failed_count += 1

            self._last_recycle_batch_id = batch_id if deleted_count else None
            
            # 从选中集合中移除已删除的书籍
            for book_path in deleted_book_paths:
                self.selected_books.discard(book_path)
                self.recommended_selected_books.discard(book_path)
            
            # 识别包含已删除书籍的组
            groups_to_remove = []
            remaining_books_from_deleted_groups = []  # 收集被删除组中剩余的书籍
            
            for i, group in enumerate(self.duplicate_groups):
                has_deleted_book = any(book.path in deleted_book_paths for book in group.books)
                if has_deleted_book:
                    groups_to_remove.append(i)
                    # 收集该组中未被删除的书籍
                    for book in group.books:
                        if book.path not in deleted_book_paths:
                            remaining_books_from_deleted_groups.append(book)
            
            # 【性能优化】删除后处理策略
            # 原问题：删除后会重新执行完整的4级重复检测（非常慢）
            # 优化：只做轻量级的组清理，不重新检测
            
            # 从后往前删除，避免索引变化问题
            for i in reversed(groups_to_remove):
                del self.duplicate_groups[i]
            
            # 清理空组和单书组（只保留有效重复组）
            valid_groups = [g for g in self.duplicate_groups if len(g.books) >= 2]
            self.duplicate_groups = valid_groups
            
            logger.info(f"删除完成 | 删除:{deleted_count} 失败:{failed_count} | 剩余重复组:{len(self.duplicate_groups)}")

            if deleted_count:
                self.notify(get_global_i18n().t("recycle_bin.undo_hint"),
                            severity="information", timeout=6)

            # 显示结果
            if failed_count == 0:
                self.notify(
                    get_global_i18n().t("duplicate_books.books_deleted", count=deleted_count),
                    severity="success"
                )
            else:
                self.notify(
                    get_global_i18n().t("duplicate_books.deleted_count", count=deleted_count) +
                    get_global_i18n().t("duplicate_books.some_delete_failed", count=failed_count),
                    severity="warning"
                )
            
            # 删完一批立即落盘：即使应用中途退出，也能从暂存继续，无需重新检测
            self._sync_staging()

            # 检查是否还有重复组
            if not self.duplicate_groups:
                # 没有重复组了，清除暂存并关闭对话框
                self.notify(get_global_i18n().t("duplicate_books.all_duplicates_processed"), severity="information")
                self._dismiss_with_sync({"refresh": True}, clear=True)
                return
            
            # 检查当前组索引是否仍然有效
            if self.current_group_index >= len(self.duplicate_groups):
                self.current_group_index = len(self.duplicate_groups) - 1
            
            # 无论后台检测是否仍在继续，只要还有分组就留在弹窗里继续处理，
            # 避免每删一批都要重新执行一次耗时的全量检测
            if 0 <= self.current_group_index < len(self.duplicate_groups):
                self._display_duplicate_group(self.current_group_index)
            elif self.duplicate_groups:
                self._display_duplicate_group(0)

            self._refresh_description()

            # 如果发现了新的重复组，显示提示
            if remaining_books_from_deleted_groups and any(
                any(book.path in [rb.path for rb in remaining_books_from_deleted_groups] for book in group.books)
                for group in self.duplicate_groups
            ):
                self.notify(
                    "发现新的重复关系，请检查并处理",
                    severity="information"
                )
            
            # 通知用户删除成功但继续处理
            self.notify(
                get_global_i18n().t("duplicate_books.books_deleted_continue_processing", count=deleted_count),
                severity="information"
            )
        except Exception as e:
            logger.error(f"删除书籍失败: {e}")
            self.notify(get_global_i18n().t("duplicate_books.delete_failed"), severity="error")
    
    @on(DataTable.CellSelected, "#duplicate-books-table")
    def on_cell_selected(self, event: DataTable.CellSelected) -> None:
        """表格单元格选中时的回调"""
        # 获取行键和列信息
        try:
            if event.coordinate is None:
                return
                
            # 获取行索引
            row_index = event.coordinate.row
            
            # 获取表格
            table = self.query_one("#duplicate-books-table", DataTable)
            
            # 获取行键
            if row_index < 0 or row_index >= len(table.rows):
                return
                
            row_keys = list(table.rows.keys())
            row_key = row_keys[row_index]
            
            # 获取书籍路径 - 现在row key格式为 {group_index}_{i}_{book.path}
            if hasattr(row_key, 'value') and row_key.value:
                row_key_str = str(row_key.value)
            else:
                row_key_str = str(row_key)
            
            # 从row key中提取书籍路径（格式：group_index_i_book_path）
            if '_' in row_key_str:
                # 分割字符串，最后一部分是书籍路径
                parts = row_key_str.split('_', 2)  # 最多分割成3部分
                if len(parts) >= 3:
                    book_path = parts[2]  # 获取书籍路径部分
                else:
                    book_path = row_key_str
            else:
                book_path = row_key_str
            
            # 获取当前组的书籍
            if not self.duplicate_groups or self.current_group_index < 0 or self.current_group_index >= len(self.duplicate_groups):
                return
                
            group = self.duplicate_groups[self.current_group_index]
            book = None
            for b in group.books:
                if b.path == book_path:
                    book = b
                    break
            
            if not book:
                return
            
            # 列索引映射：
            # 0=索引, 1=书名, 2=作者, 3=大小, 4=格式, 5=推荐, 6=查看文件按钮, 7=预览按钮, 8=已选择列
            
            # 处理查看文件按钮列的点击（索引6）
            if event.coordinate.column == 6:
                self._view_file(book.path)
                event.stop()
                return
            
            # 处理预览按钮列的点击（索引7）
            if event.coordinate.column == 7:
                self._preview_book(book)
                event.stop()
                return
            
            # 处理已选择列的点击（最后一列，索引8）
            if event.coordinate.column == 8:
                # 切换选中状态
                if book_path in self.selected_books:
                    self.selected_books.remove(book_path)
                else:
                    self.selected_books.add(book_path)
                
                # 重新加载表格显示
                self._display_duplicate_group(self.current_group_index)
                event.stop()
                return
                
        except Exception as e:
            logger.error(f"处理单元格选择失败: {e}")
    
    def _view_file(self, book_path: str) -> None:
        """查看书籍文件（统一走 book_view_utils 的文件定位逻辑）。"""
        from src.ui.utils.book_view_utils import reveal_book_file
        reveal_book_file(self, book_path)
    
    def _preview_book(self, book: Book) -> None:
        """预览书籍内容（统一书籍视图，兼具详情 / 查看文件 / 预览全部）。"""
        from src.ui.utils.book_view_utils import build_view_data, open_book_view

        try:
            file_path = book.path
            if not file_path:
                self.notify(get_global_i18n().t("crawler.no_file_path"), severity="warning")
                return
            if not os.path.exists(file_path):
                self.notify(f"{get_global_i18n().t('common.file_not_exist')}: {file_path}", severity="warning")
                return

            data = build_view_data(
                file_path,
                title=book.title,
                metadata={
                    "author": getattr(book, "author", ""),
                    "format": getattr(book, "format", ""),
                    "size": getattr(book, "size", 0),
                    "tags": getattr(book, "tags", ""),
                    "path": getattr(book, "path", ""),
                },
            )
            if not data.content.strip():
                self.notify(get_global_i18n().t("crawler.preview_empty"), severity="information")
                return
            open_book_view(self.app, data, self.theme_manager, "preview")
        except Exception as e:
            logger.error(f"预览书籍失败: {e}")
            self.notify(f"{get_global_i18n().t('crawler.preview_failed')}: {str(e)}", severity="error")
    
    @on(UpdateDuplicateGroupsMessage)
    def on_update_duplicate_groups(self, message: UpdateDuplicateGroupsMessage) -> None:
        """处理更新重复组消息"""
        logger.info(f"收到UpdateDuplicateGroupsMessage消息，批次索引: {message.batch_index}, 组数: {len(message.batch_groups)}")
        self.update_duplicate_groups(
            message.batch_groups,
            message.batch_index,
            message.total_batches,
            message.processing_remaining
        )
    
    def update_duplicate_groups(self, new_groups: List[DuplicateGroup], batch_index: int, 
                          total_batches: int, processing_remaining: bool) -> None:
        """动态更新重复书籍组（用于分批处理）
        
        Args:
            new_groups: 新增的重复组
            batch_index: 批次索引
            total_batches: 总批次数
            processing_remaining: 是否还有剩余批次需要处理
        """
        try:
            # 更新状态变量
            self.current_batch = batch_index + 1
            self.total_batches = total_batches
            self.processing_remaining = processing_remaining
            
            # 添加新组到现有列表
            self.duplicate_groups.extend(new_groups)
            
            # 显示通知
            if processing_remaining:
                self.notify(
                    get_global_i18n().t("duplicate_books.new_batch_added", 
                                        batch=batch_index+1, count=len(new_groups)),
                    severity="information"
                )
            else:
                # 所有批次已完成 - 显示完整完成提示
                total_groups = len(self.duplicate_groups)
                self.notify(
                    get_global_i18n().t("duplicate_books.all_batches_completed") +
                    f"！共找到 {total_groups} 组重复书籍",
                    severity="information"
                )
            
            # 如果有新组，直接显示新添加的第一组
            if new_groups and len(self.duplicate_groups) > 0:
                # 显示新添加的第一组
                new_group_index = len(self.duplicate_groups) - len(new_groups)
                
                # 显示新组
                self._display_duplicate_group(new_group_index)
            else:
                # 没有新组，刷新当前显示
                self._display_duplicate_group(self.current_group_index)
            
            # 显示通知
            if processing_remaining:
                self.notify(
                    get_global_i18n().t("duplicate_books.new_batch_added", 
                                        batch=batch_index+1, count=len(new_groups)),
                    severity="information"
                )
            else:
                # 所有批次已完成 - 显示完整完成提示（第二次，移除重复通知）
                # 注释：上面的代码已经显示了完成提示，这里不需要重复
                pass
            
            # 如果还有剩余批次，显示处理状态
            if processing_remaining:
                # 更新标题显示处理状态
                try:
                    title_label = self.query_one("#duplicate-books-status", Label)
                    title_label.update(
                        f"{get_global_i18n().t('duplicate_books.processing_remaining', batch=self.current_batch, total=self.total_batches)}"
                    )
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"更新重复组失败: {e}")