"""
书签列表屏幕 - 显示和管理所有书签（数据库版本）
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from webbrowser import get
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, ListView, ListItem, Input
from textual import events, on
from textual.message import Message
from src.locales.i18n_manager import set_global_locale, get_global_i18n, t
from src.core.bookmark import BookmarkManager, Bookmark
from src.ui.dialogs.bookmark_edit_dialog import BookmarkEditDialog

# 延迟导入以避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.ui.screens.terminal_reader_screen import ReaderScreen

class BookmarksScreen(Screen[None]):
    """书签列表屏幕 - 使用数据库存储"""
    
    TITLE: Optional[str] = None  # 在运行时设置
    CSS_PATH = "../styles/bookmarks.css"  # 这个文件存在
    
    def __init__(self, book_id: str):
        super().__init__()
        self.book_id = book_id
        self.screen_title = get_global_i18n().t("bookmarks.title")
        # 设置类的TITLE属性
        self.__class__.TITLE = self.screen_title
        self.bookmark_manager = BookmarkManager()
        self.bookmarks = self.bookmark_manager.get_bookmarks(book_id)
        
        # 分页相关属性
        self._current_page = 1
        self._bookmarks_per_page = 20
        self._total_pages = max(1, (len(self.bookmarks) + self._bookmarks_per_page - 1) // self._bookmarks_per_page)
    
    def compose(self) -> ComposeResult:
        """组合书签列表界面"""
        yield Container(
            Vertical(
                # 标题栏
                Horizontal(
                    Label(self.screen_title, id="screen-title"),
                    id="header-container"
                ),
                
                # 操作按钮栏
                Horizontal(
                    Button(get_global_i18n().t("bookmarks.goto"), id="goto-selected-btn", variant="primary"),
                    Button(get_global_i18n().t("common.delete"), id="delete-selected-btn", variant="error"),
                    Button(get_global_i18n().t("common.edit"), id="edit-note-btn", variant="default"),
                    Button(get_global_i18n().t("bookmarks.clear_all"), id="clear-all-btn", variant="warning"),
                    Button(get_global_i18n().t("common.back"), id="back-button", variant="error"),
                    id="action-buttons"
                ),
                
                # 分页信息显示
                Label(f"{get_global_i18n().t('bookmarks.page_info', page=self._current_page, total_pages=self._total_pages, total_bookmarks=len(self.bookmarks))}", id="page-info"),
                
                # 书签列表
                ListView(
                    *self._get_bookmark_items(),
                    id="bookmarks-list"
                ),
                
                # 统计信息和帮助
                Vertical(
                    Label(self._get_stats_text(), id="stats-info"),
                    Label(get_global_i18n().t("bookmarks.help_info"), id="help-info"),
                    id="footer-container"
                ),
                
                id="bookmarks-container"
            )
        )
    
    def _get_bookmark_items(self) -> List[ListItem]:
        """获取书签列表项，如果为空则显示提示"""
        if not self.bookmarks:
            return [ListItem(Label(get_global_i18n().t("bookmarks.no_bookmarks_hint")))]
        
        # 计算当前页的书签范围
        start_index = (self._current_page - 1) * self._bookmarks_per_page
        end_index = min(start_index + self._bookmarks_per_page, len(self.bookmarks))
        current_page_bookmarks = self.bookmarks[start_index:end_index]
        
        return [self._create_bookmark_item(bookmark) for bookmark in current_page_bookmarks]
    
    def _create_bookmark_item(self, bookmark: Bookmark) -> ListItem:
        """创建书签列表项"""
        try:
            # 尝试将position转换为整数页码
            page_num = int(bookmark.position)
            page_text = f"📖 {get_global_i18n().t('reader.page_current', page=page_num + 1)}"
        except (ValueError, TypeError):
            # 如果position不是数字，直接显示
            page_text = f"📍 位置: {bookmark.position}"
            
        time_text = self._format_timestamp(bookmark.created_date)
        notes_text = f"💭 {bookmark.note}" if bookmark.note else f"💭 {get_global_i18n().t('bookmarks.no_note')}"
        
        # 创建多行显示内容
        content = f"{page_text}  🕒 {time_text}\n{notes_text}"
        
        # 不设置ID，避免冲突
        return ListItem(Label(content))
    
    def _format_timestamp(self, timestamp: str) -> str:
        """格式化时间戳显示"""
        if not timestamp:
            return get_global_i18n().t('bookmarks.time_unknown')
        
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return get_global_i18n().t('bookmarks.time_unknown')
    
    def _get_stats_text(self) -> str:
        """获取统计信息文本"""
        total = len(self.bookmarks)
        with_notes = sum(1 for bm in self.bookmarks if bm.note)
        
        return get_global_i18n().t('bookmarks.stats_info', total=total, with_notes=with_notes)
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        self.title = self.screen_title
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "back-button":
            self.app.pop_screen()
        elif event.button.id == "goto-selected-btn":
            self._goto_selected_bookmark()
        elif event.button.id == "delete-selected-btn":
            self._delete_selected_bookmark()
        elif event.button.id == "edit-note-btn":
            self._edit_selected_note()
        elif event.button.id == "clear-all-btn":
            self._clear_all_bookmarks()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """书签项选择时的回调"""
        try:
            list_view = self.query_one("#bookmarks-list", ListView)
            if list_view.index is not None:
                # 检查是否有书签
                if not self.bookmarks:
                    self.notify(get_global_i18n().t("bookmarks.add_bookmark_first"), severity="warning")
                    return
                
                # 计算实际书签索引（考虑分页）
                actual_index = (self._current_page - 1) * self._bookmarks_per_page + list_view.index
                
                if 0 <= actual_index < len(self.bookmarks):
                    bookmark = self.bookmarks[actual_index]
                    # 直接跳转到选中的书签
                    self._goto_bookmark(bookmark)
                else:
                    self.notify(get_global_i18n().t("bookmarks.select_valid_bookmark"), severity="warning")
            else:
                self.notify(get_global_i18n().t("bookmarks.select_bookmark_first"), severity="warning")
        except Exception as e:
            self.notify(f"{get_global_i18n().t("bookmarks.goto_failed")}: {e}", severity="error")
    
    def _goto_bookmark(self, bookmark: Bookmark) -> None:
        """跳转到书签位置"""
        try:
            # bookmark.position 存储的是 0-based 页码索引
            page_index = int(bookmark.position)
            display_page = page_index + 1  # 显示用的 1-based 页码
            
            # 通过屏幕类名查找阅读器屏幕
            reader_screen = None
            for screen in self.app.screen_stack:
                if screen.__class__.__name__ == "ReaderScreen":
                    reader_screen = screen
                    break
            
            if reader_screen is None:
                self.notify(get_global_i18n().t("bookmarks.reader_screen_not_found"), severity="error")
                return
            
            # 使用反射调用阅读器屏幕的方法
            if hasattr(reader_screen, 'renderer') and hasattr(reader_screen.renderer, 'goto_page'):
                # goto_page 期望 1-based 页码
                success = reader_screen.renderer.goto_page(display_page)
                if success:
                    # 更新屏幕状态为 0-based 索引
                    reader_screen.current_page = page_index
                    reader_screen.total_pages = reader_screen.renderer.total_pages
                    if hasattr(reader_screen, '_on_page_change'):
                        reader_screen._on_page_change(page_index)
                    if hasattr(reader_screen, '_update_scroll_indicator'):
                        reader_screen._update_scroll_indicator()
                    
                    self.notify(get_global_i18n().t("bookmarks.jump_success", page=display_page), severity="information")
                    # 只有跳转成功时才关闭书签列表
                    self.app.pop_screen()
                else:
                    self.notify(get_global_i18n().t("bookmarks.jump_failed", page=display_page), severity="error")
            else:
                self.notify(get_global_i18n().t("bookmarks.page_jump_not_supported"), severity="error")
        except (ValueError, TypeError) as e:
            self.notify(get_global_i18n().t('bookmarks.cannot_jump_to_position', position=bookmark.position, error=str(e)), severity="error")
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.jump_error", error=str(e)), severity="error")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            self.app.pop_screen()
        elif event.key == "delete":
            self._delete_selected_bookmark()
        elif event.key == "enter":
            self._goto_selected_bookmark()
        elif event.key == "n":
            # N键下一页
            if self._current_page < self._total_pages:
                self._current_page += 1
                self._refresh_bookmark_list()
            event.prevent_default()
        elif event.key == "p":
            # P键上一页
            if self._current_page > 1:
                self._current_page -= 1
                self._refresh_bookmark_list()
            event.prevent_default()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            list_view = self.query_one("#bookmarks-list", ListView)
            if (list_view.index == len(list_view.children) - 1 and 
                self._current_page < self._total_pages):
                self._current_page += 1
                self._refresh_bookmark_list()
                # 将光标移动到新页面的第一项
                list_view = self.query_one("#bookmarks-list", ListView)
                list_view.index = 0
                event.prevent_default()
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            list_view = self.query_one("#bookmarks-list", ListView)
            if list_view.index == 0 and self._current_page > 1:
                self._current_page -= 1
                self._refresh_bookmark_list()
                # 将光标移动到新页面的最后一项
                list_view = self.query_one("#bookmarks-list", ListView)
                list_view.index = len(list_view.children) - 1
                event.prevent_default()
    
    def _goto_selected_bookmark(self) -> None:
        """跳转到选中的书签"""
        try:
            list_view = self.query_one("#bookmarks-list", ListView)
            if list_view.index is not None:
                # 检查是否有书签
                if not self.bookmarks:
                    self.notify(get_global_i18n().t("bookmarks.add_bookmark_first"), severity="warning")
                    return
                
                # 计算实际书签索引（考虑分页）
                actual_index = (self._current_page - 1) * self._bookmarks_per_page + list_view.index
                
                if 0 <= actual_index < len(self.bookmarks):
                    bookmark = self.bookmarks[actual_index]
                    self._goto_bookmark(bookmark)
                else:
                    self.notify(get_global_i18n().t("bookmarks.select_valid_bookmark"), severity="warning")
            else:
                self.notify(get_global_i18n().t("bookmarks.select_bookmark_first"), severity="warning")
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.jump_error", error=str(e)), severity="error")
    
    def _delete_selected_bookmark(self) -> None:
        """删除选中的书签"""
        try:
            list_view = self.query_one("#bookmarks-list", ListView)
            if list_view.index is not None:
                # 检查是否有书签
                if not self.bookmarks:
                    self.notify(get_global_i18n().t("bookmarks.no_bookmarks_to_delete"), severity="warning")
                    return
                
                # 计算实际书签索引（考虑分页）
                actual_index = (self._current_page - 1) * self._bookmarks_per_page + list_view.index
                
                if 0 <= actual_index < len(self.bookmarks):
                    bookmark = self.bookmarks[actual_index]
                    if bookmark.id and self.bookmark_manager.remove_bookmark(bookmark.id):
                        self.bookmarks.pop(actual_index)
                        self._refresh_bookmark_list()
                        self.notify(get_global_i18n().t("bookmarks.bookmark_deleted"), severity="information")
                    else:
                        self.notify(get_global_i18n().t("bookmarks.failed_to_delete_bookmark"), severity="error")
                else:
                    self.notify(get_global_i18n().t("bookmarks.select_valid_bookmark"), severity="warning")
            else:
                self.notify(get_global_i18n().t("bookmarks.select_bookmark_first"), severity="warning")
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.delete_failed", error=str(e)), severity="error")
    
    def _edit_selected_note(self) -> None:
        """编辑选中书签的备注"""
        try:
            list_view = self.query_one("#bookmarks-list", ListView)
            if list_view.index is not None:
                # 检查是否有书签
                if not self.bookmarks:
                    self.notify(get_global_i18n().t("bookmarks.add_bookmark_first"), severity="warning")
                    return
                
                # 计算实际书签索引（考虑分页）
                actual_index = (self._current_page - 1) * self._bookmarks_per_page + list_view.index
                
                if 0 <= actual_index < len(self.bookmarks):
                    bookmark = self.bookmarks[actual_index]
                    
                    # 创建书签信息字符串
                    try:
                        page_num = int(bookmark.position) + 1
                        bookmark_info = get_global_i18n().t('reader.page_current', page=page_num)
                    except (ValueError, TypeError):
                        bookmark_info = f"{get_global_i18n().t('search.position')}: {bookmark.position}"
                    
                    # 打开编辑对话框
                    dialog = BookmarkEditDialog(bookmark_info, bookmark.note or "")
                    self.app.push_screen(dialog, self._on_edit_result)
                else:
                    self.notify(get_global_i18n().t("bookmarks.select_valid_bookmark"), severity="warning")
            else:
                self.notify(get_global_i18n().t("bookmarks.select_bookmark_first"), severity="warning")
        except Exception as e:
            self.notify(get_global_i18n().t('bookmarks.edit_failed', error=str(e)), severity="error")
    
    def _on_edit_result(self, result: str | None) -> None:
        """编辑对话框结果回调"""
        if result is None:
            # 用户取消了编辑
            return
        
        try:
            list_view = self.query_one("#bookmarks-list", ListView)
            if list_view.index is not None:
                # 计算实际书签索引（考虑分页）
                actual_index = (self._current_page - 1) * self._bookmarks_per_page + list_view.index
                
                if 0 <= actual_index < len(self.bookmarks):
                    bookmark = self.bookmarks[actual_index]
                    
                    # 检查书签ID是否有效
                    if not bookmark.id:
                        self.notify(get_global_i18n().t("bookmarks.invalid_bookmark_id"), severity="error")
                        return
                    
                    # 更新书签备注
                    success = self.bookmark_manager.update_bookmark_note(bookmark.id, result)
                    if success:
                        # 更新本地书签对象
                        bookmark.note = result
                        # 刷新列表显示
                        self._refresh_bookmark_list()
                        self.notify(get_global_i18n().t("bookmarks.bookmark_note_updated"), severity="information")
                    else:
                        self.notify(get_global_i18n().t("bookmarks.failed_to_update_note"), severity="error")
                else:
                    self.notify(get_global_i18n().t("bookmarks.no_valid_bookmark_selected"), severity="warning")
            else:
                self.notify(get_global_i18n().t("bookmarks.no_valid_bookmark_selected"), severity="warning")
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.failed_to_save_note", error=str(e)), severity="error")
    
    def _clear_all_bookmarks(self) -> None:
        """清空所有书签"""
        try:
            if len(self.bookmarks) == 0:
                self.notify(get_global_i18n().t("bookmarks.no_bookmarks_to_clear"), severity="warning")
                return
            
            # 删除所有书签
            for bookmark in self.bookmarks:
                if bookmark.id:
                    self.bookmark_manager.remove_bookmark(bookmark.id)
            
            self.bookmarks.clear()
            self._refresh_bookmark_list()
            self.notify(get_global_i18n().t("bookmarks.all_bookmarks_cleared"), severity="information")
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.clear_failed", error=str(e)), severity="error")
    
    def _refresh_bookmark_list(self) -> None:
        """刷新书签列表显示"""
        try:
            # 更新分页信息
            page_info = self.query_one("#page-info", Label)
            page_info.update(f"{get_global_i18n().t('bookmarks.page_info', page=self._current_page, total_pages=self._total_pages, total_bookmarks=len(self.bookmarks))}")
            
            list_view = self.query_one("#bookmarks-list", ListView)
            current_index = list_view.index  # 保存当前选中的索引
            
            # 清空并重新填充列表
            list_view.clear()
            
            # 重新获取书签数据以确保最新
            self.bookmarks = self.bookmark_manager.get_bookmarks(self.book_id)
            # 重新计算总页数
            self._total_pages = max(1, (len(self.bookmarks) + self._bookmarks_per_page - 1) // self._bookmarks_per_page)
            
            # 添加当前页的书签项
            if self.bookmarks:
                # 计算当前页的书签范围
                start_index = (self._current_page - 1) * self._bookmarks_per_page
                end_index = min(start_index + self._bookmarks_per_page, len(self.bookmarks))
                current_page_bookmarks = self.bookmarks[start_index:end_index]
                
                for bookmark in current_page_bookmarks:
                    list_view.append(self._create_bookmark_item(bookmark))
                
                # 恢复选中状态
                if current_index is not None and 0 <= current_index < len(current_page_bookmarks):
                    list_view.index = current_index
                elif len(current_page_bookmarks) > 0:
                    list_view.index = 0  # 默认选择第一项
            else:
                # 如果没有书签，显示提示信息
                list_view.append(ListItem(Label(get_global_i18n().t("bookmarks.no_bookmarks_hint"))))
            
            # 更新统计信息
            stats_label = self.query_one("#stats-info", Label)
            stats_label.update(self._get_stats_text())
            
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.refresh_failed", error=str(e)), severity="error")