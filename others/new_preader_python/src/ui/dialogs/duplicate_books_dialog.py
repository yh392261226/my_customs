"""
重复书籍对话框，用于显示和选择要删除的重复书籍
"""

import os
import shutil
from typing import List, Dict, Any
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
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DuplicateBooksDialog(ModalScreen[Dict[str, Any]]):
    """重复书籍对话框"""
    
    CSS_PATH = "../styles/duplicate_books_dialog.tcss"

    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
        ("space", "toggle_row", get_global_i18n().t('duplicate_books.toggle_row')),
        ("s", "select_current", get_global_i18n().t('duplicate_books.select_current')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, duplicate_groups: List[DuplicateGroup]):
        """
        初始化重复书籍对话框
        
        Args:
            theme_manager: 主题管理器
            duplicate_groups: 重复书籍组列表
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.duplicate_groups = duplicate_groups
        self.selected_books: set[str] = set()  # 选中的书籍路径
        self.recommended_selected_books: set[str] = set()  # 推荐选中的书籍路径
        self.current_group_index = 0  # 当前显示的重复组索引
        
        # 预先推荐选中所有组中推荐的删除书籍
        for group in duplicate_groups:
            for book in group.recommended_to_delete:
                self.recommended_selected_books.add(book.path)
        
        self.selected_books = self.recommended_selected_books.copy()
    
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
                    )
                ),
                
                # 重复组信息
                Label("", id="duplicate-group-info"),
                
                # 书籍对比表格
                DataTable(id="duplicate-books-table"),
                
                # 操作按钮
                Horizontal(
                    Button(get_global_i18n().t("duplicate_books.compare_selected"), id="compare-btn", variant="primary"),
                    Button(get_global_i18n().t("duplicate_books.select_recommended"), id="select-recommended-btn", variant="primary"),
                    Button(get_global_i18n().t("duplicate_books.deselect_all"), id="deselect-all-btn"),
                    Button(get_global_i18n().t("duplicate_books.delete_selected"), id="delete-btn", variant="error"),
                    Button(get_global_i18n().t("duplicate_books.next_group"), id="next-group-btn"),
                    Button(get_global_i18n().t("duplicate_books.prev_group"), id="prev-group-btn"),
                    Button(get_global_i18n().t("common.cancel"), id="cancel-btn")
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
            table.add_column(get_global_i18n().t("bookshelf.title"), key="title")
            table.add_column(get_global_i18n().t("bookshelf.author"), key="author")
            table.add_column(get_global_i18n().t("bookshelf.size"), key="size")
            table.add_column(get_global_i18n().t("bookshelf.format"), key="format")
            table.add_column(get_global_i18n().t("duplicate_books.recommended"), key="recommended")
            table.add_column(get_global_i18n().t("bookshelf.view_file"), key="view_action")  # 查看文件按钮列
            table.add_column(get_global_i18n().t("duplicate_books.selected"), key="selected")
            
            # 启用隔行变色效果
            table.zebra_stripes = True
            
            # 设置表格选择模式
            try:
                # 使用列选择模式，以便能够点击特定列（如查看文件按钮）
                table.cursor_type = "cell"
                table.show_cursor = True
            except AttributeError as e:
                logger.warning(f"表格不支持某些选择属性: {e}")
            
            # 如果有重复组，显示第一组
            if self.duplicate_groups:
                self._display_duplicate_group(0)
            
            # 确保表格获得焦点
            try:
                table.focus()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"初始化数据表失败: {e}")
            self.notify("无法初始化重复书籍对话框", severity="error")
    
    def _display_duplicate_group(self, group_index: int) -> None:
        """显示指定索引的重复组
        
        Args:
            group_index: 组索引
        """
        if not self.duplicate_groups or group_index < 0 or group_index >= len(self.duplicate_groups):
            return
        
        self.current_group_index = group_index
        group = self.duplicate_groups[group_index]
        
        # 更新组信息
        group_info_label = self.query_one("#duplicate-group-info", Label)
        duplicate_type_text = ""
        if group.duplicate_type == DuplicateType.FILE_NAME:
            duplicate_type_text = get_global_i18n().t("duplicate_books.type_file_name")
        elif group.duplicate_type == DuplicateType.CONTENT_SIMILAR:
            duplicate_type_text = get_global_i18n().t("duplicate_books.type_content_similar", similarity=f"{group.similarity:.1%}")
        elif group.duplicate_type == DuplicateType.HASH_IDENTICAL:
            duplicate_type_text = get_global_i18n().t("duplicate_books.type_hash_identical")
        
        group_info_label.update(
            get_global_i18n().t(
                "duplicate_books.group_info",
                current_group=group_index + 1,
                total_groups=len(self.duplicate_groups),
                duplicate_type=duplicate_type_text,
                books_count=len(group.books)
            )
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
        
        table.clear()
        
        for i, book in enumerate(group.books):
            # 检查是否为推荐的保留书籍
            is_recommended_keep = book in group.recommended_to_keep
            recommended_text = "保留" if is_recommended_keep else "删除"
            
            # 检查是否被选中
            is_selected = book.path in self.selected_books
            selection_marker = "✓" if is_selected else "□"
            
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
            view_file_button = f"[{get_global_i18n().t('bookshelf.view_file')}]"
            
            # 添加行
            table.add_row(
                str(i + 1),
                book.title,
                book.author,
                size_str,
                book.format.upper() if book.format else "",
                recommended_text,
                view_file_button,  # 查看文件按钮
                selection_marker,
                key=book.path
            )
        
        # 更新状态信息
        self._update_status()
    
    def _update_status(self) -> None:
        """更新状态信息"""
        status_label = None
        for widget in self.walk_children():
            if hasattr(widget, "id") and widget.id == "duplicate-books-status":
                status_label = widget
                break
        
        if not status_label:
            logger.error("无法找到状态标签组件")
            return
        
        # 计算当前组中选中的书籍数量
        current_group = self.duplicate_groups[self.current_group_index]
        current_group_selected = sum(1 for book in current_group.books if book.path in self.selected_books)
        
        status_label.update(
            get_global_i18n().t(
                "duplicate_books.status_info",
                total_selected=len(self.selected_books),
                current_group_selected=current_group_selected
            )
        )
    
    def action_cancel(self) -> None:
        """取消操作"""
        self.dismiss({"refresh": False})
    
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
    
    @on(Button.Pressed, "#cancel-btn")
    def on_cancel_pressed(self) -> None:
        """取消按钮按下时的回调"""
        self.dismiss({"refresh": False})
    
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
        
        # 显示确认对话框
        confirm_dialog = ConfirmDialog(
            self.theme_manager,
            get_global_i18n().t("duplicate_books.delete_confirm"),
            get_global_i18n().t(
                "duplicate_books.delete_confirm_message",
                count=len(self.selected_books)
            )
        )
        
        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                # 执行删除操作
                self._delete_selected_books()
        
        self.app.push_screen(confirm_dialog, on_confirm)
    
    def _delete_selected_books(self) -> None:
        """删除选中的书籍"""
        try:
            import shutil
            deleted_count = 0
            failed_count = 0
            
            # 获取书库对象
            bookshelf = getattr(self.app, "bookshelf", None)
            if not bookshelf:
                logger.error("无法获取书库对象")
                self.notify("无法获取书库对象", severity="error")
                return
            
            for book_path in self.selected_books:
                try:
                    if os.path.exists(book_path):
                        # 移动到回收站（根据操作系统）
                        trash_path = os.path.join(os.path.expanduser("~"), ".Trash", os.path.basename(book_path))
                        if not os.path.exists(os.path.dirname(trash_path)):
                            os.makedirs(os.path.dirname(trash_path), exist_ok=True)
                        
                        shutil.move(book_path, trash_path)
                        deleted_count += 1
                        
                        # 从书库中删除书籍
                        bookshelf.remove_book(book_path)
                except Exception as e:
                    logger.error(f"删除书籍失败: {book_path}, 错误: {e}")
                    failed_count += 1
            
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
            
            # 关闭对话框并刷新
            self.dismiss({"refresh": True})
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
            
            # 获取书籍路径
            if hasattr(row_key, 'value') and row_key.value:
                book_path = str(row_key.value)
            else:
                book_path = str(row_key)
            
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
            # 0=索引, 1=书名, 2=作者, 3=大小, 4=格式, 5=推荐, 6=查看文件按钮, 7=已选择列
            
            # 处理查看文件按钮列的点击（索引6）
            if event.coordinate.column == 6:
                self._view_file(book.path)
                event.stop()
                return
            
            # 处理已选择列的点击（最后一列）
            if event.coordinate.column == 7:
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
        """查看书籍文件"""
        try:
            # 导入需要的模块
            import platform
            import subprocess
            
            # 检查文件是否存在
            if not os.path.exists(book_path):
                self.notify(f"{get_global_i18n().t('bookshelf.file_not_exists')}: {book_path}", severity="error")
                return
            
            # 根据操作系统打开文件管理器
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", "-R", book_path], check=False)
            elif system == "Windows":
                subprocess.run(["explorer", "/select,", book_path], check=False)
            elif system == "Linux":
                subprocess.run(["xdg-open", os.path.dirname(book_path)], check=False)
            else:
                # 通用方法：打开文件所在目录
                folder_path = os.path.dirname(book_path)
                if os.path.exists(folder_path):
                    subprocess.run(["open", folder_path], check=False)
                else:
                    self.notify(get_global_i18n().t("bookshelf.open_directory_failed"), severity="warning")
                    return
            
            self.notify(f"{get_global_i18n().t('bookshelf.opened_in_file_explorer')}: {os.path.basename(book_path)}", severity="information")
            
        except Exception as e:
            self.notify(f"{get_global_i18n().t('bookshelf.view_file_failed')}: {e}", severity="error")