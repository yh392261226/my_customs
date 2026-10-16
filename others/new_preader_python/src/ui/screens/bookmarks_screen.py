"""
书签列表屏幕 - 显示和管理所有书签（数据库版本）
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from webbrowser import get
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, ListView, ListItem, Input, Header, Footer
from textual import events, on
from textual.message import Message
from src.locales.i18n_manager import set_global_locale, get_global_i18n, t
from src.core.bookmark import BookmarkManager, Bookmark
from src.ui.dialogs.bookmark_edit_dialog import BookmarkEditDialog
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger

# 类型与协议（消除对具体 ReaderScreen 的静态依赖）
from typing import Protocol, runtime_checkable, cast, Any

logger = get_logger(__name__)

@runtime_checkable
class ReaderLike(Protocol):
    renderer: Any
    current_page: int
    total_pages: int
    book: Any
    def goto_offset_or_anchor(self, approx_offset: int, anchor_text: str, anchor_hash: str) -> bool: ...
    def _rehydrate_offset_from_anchor(self, anchor_text: str, anchor_hash: str, original: str) -> int | None: ...
    def _find_page_for_offset(self, offset: int) -> int: ...
    _line_offsets_per_page: list[list[int]]
    def _set_scroll_to_line(self, line_index: int) -> None: ...
    def _on_page_change(self, page_index: int) -> None: ...
    def _update_scroll_indicator(self) -> None: ...

class BookmarksScreen(Screen[None]):
    """书签列表屏幕 - 使用数据库存储"""
    
    TITLE: Optional[str] = None  # 在运行时设置
    CSS_PATH = "../styles/bookmarks_overrides.tcss"  # 这个文件存在
    
    def __init__(self, book_id: str):
        super().__init__()
        self.book_id = book_id
        self.screen_title = get_global_i18n().t("common.bookmark_list")
        # 设置类的TITLE属性
        self.__class__.TITLE = self.screen_title
        self.bookmark_manager = BookmarkManager()
        # 获取当前用户ID - 使用与应用实例一致的方式
        current_user = getattr(self.app, 'current_user', None)
        if current_user:
            current_user_id = current_user.get('id')

        # 如果没有从应用实例获取到用户信息，回退到多用户管理器
        if current_user_id is None:
            from src.utils.multi_user_manager import multi_user_manager
            current_user = multi_user_manager.get_current_user()
            current_user_id = current_user.get('id') if current_user else None
        
        # 如果多用户模式关闭，user_id应该为None（查询所有数据）
        if current_user_id is not None:
            from src.utils.multi_user_manager import multi_user_manager
            if not multi_user_manager.is_multi_user_enabled():
                user_id = None
            else:
                user_id = current_user_id

            if current_user.get('role') == 'superadmin' or current_user.get('role') == 'super_admin':
                user_id = None
        else:
            user_id = None
        
        self.bookmarks = self.bookmark_manager.get_bookmarks(book_id, user_id)
        
        # 分页相关属性
        self._current_page = 1
        self._bookmarks_per_page = 20
        self._total_pages = max(1, (len(self.bookmarks) + self._bookmarks_per_page - 1) // self._bookmarks_per_page)
        self.db_manager = DatabaseManager()  # 数据库管理器

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            return self.db_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def compose(self) -> ComposeResult:
        """组合书签列表界面"""
        yield Header()
        yield Container(
            Vertical(
                # 标题栏
                Horizontal(
                    Label(self.screen_title, id="screen-title", classes="section-title"),
                    id="header-container"
                ),
                
                # 操作按钮栏
                Horizontal(
                    Button(get_global_i18n().t("bookmarks.goto"), id="goto-selected-btn", variant="primary", classes="btn"),
                    Button(get_global_i18n().t("common.delete"), id="delete-selected-btn", variant="error", classes="btn"),
                    Button(get_global_i18n().t("common.edit"), id="edit-note-btn", variant="default", classes="btn"),
                    Button(get_global_i18n().t("common.clear"), id="clear-all-btn", variant="warning", classes="btn"),
                    Button(get_global_i18n().t("common.back"), id="back-button", variant="error", classes="btn"),
                    id="action-buttons",
                    classes="btn-row"
                ),
                
                # 分页信息显示
                Label(f"{get_global_i18n().t('bookmarks.page_info', page=self._current_page, total_pages=self._total_pages, total_bookmarks=len(self.bookmarks))}", id="page-info"),
                
                # 书签列表
                ListView(
                    *self._get_bookmark_items(),
                    id="bookmarks-list"
                ),
                
                # 分页导航
                Horizontal(
                    Button("◀◀", id="first-page-btn", classes="pagination-btn"),
                    Button("◀", id="prev-page-btn", classes="pagination-btn"),
                    Label("", id="page-info-nav", classes="page-info"),
                    Button("▶", id="next-page-btn", classes="pagination-btn"),
                    Button("▶▶", id="last-page-btn", classes="pagination-btn"),
                    Button(get_global_i18n().t('bookshelf.jump_to'), id="jump-page-btn", classes="pagination-btn"),
                    id="pagination-bar",
                    classes="pagination-bar"
                ),
                
                # 统计信息和帮助
                Vertical(
                    Label(self._get_stats_text(), id="stats-info"),
                    Label(get_global_i18n().t("bookmarks.help_info"), id="help-info"),
                    id="footer-container"
                ),
                
                id="bookmarks-container"
            ),
            id="bookmarks-screen-container"
        )
        yield Footer()
    
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
        # 统一按绝对字符偏移显示位置（更稳健）
        try:
            pos_val = int(getattr(bookmark, "position", 0) or 0)
        except Exception:
            pos_val = 0
        page_text = f"📍 位置: {pos_val}"
        time_text = self._format_timestamp(getattr(bookmark, "created_date", "") or "")
        notes_text = f"💭 {bookmark.note}" if bookmark.note else f"💭 {get_global_i18n().t('bookmarks.no_note')}"
        content = f"{page_text}  🕒 {time_text}\n{notes_text}"
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

        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        self.title = self.screen_title
        # 更新分页信息
        self._update_pagination_info()
    
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
        # 分页按钮
        elif event.button.id == "first-page-btn":
            self._go_to_first_page()
        elif event.button.id == "prev-page-btn":
            self._go_to_prev_page()
        elif event.button.id == "next-page-btn":
            self._go_to_next_page()
        elif event.button.id == "last-page-btn":
            self._go_to_last_page()
        elif event.button.id == "jump-page-btn":
            self._show_jump_dialog()
    
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
            self.notify(f"{get_global_i18n().t('bookmarks.goto_failed')}: {e}", severity="error")
    
    def _goto_bookmark(self, bookmark: Bookmark) -> None:
        """跳转到书签位置（优先用锚点纠偏 + 绝对偏移映射）"""
        try:
            # 通过屏幕类名查找阅读器屏幕，并按 ReaderLike 进行类型断言（仅类型层面）
            _reader_obj = None
            for screen in self.app.screen_stack:
                if screen.__class__.__name__ == "ReaderScreen":
                    _reader_obj = screen
                    break
            if _reader_obj is None:
                self.notify(get_global_i18n().t("bookmarks.reader_screen_not_found"), severity="error")
                return
            reader_screen = cast(ReaderLike, _reader_obj)
            
            # 获取原文与辅助方法
            try:
                original = getattr(reader_screen.renderer, "_original_content", "") or (getattr(reader_screen, "book").get_content() if hasattr(reader_screen, "book") and hasattr(getattr(reader_screen, "book"), "get_content") else "")
            except Exception:
                original = getattr(reader_screen.renderer, "_original_content", "") or ""
            approx_offset = 0
            try:
                approx_offset = int(getattr(bookmark, "position", 0) or 0)
            except Exception:
                approx_offset = 0
            anchor_text = getattr(bookmark, "anchor_text", "") or ""
            anchor_hash = getattr(bookmark, "anchor_hash", "") or ""
            
            # 若 ReaderScreen 暴露统一入口则优先用
            if hasattr(reader_screen, "goto_offset_or_anchor"):
                ok = reader_screen.goto_offset_or_anchor(approx_offset, anchor_text, anchor_hash)
                if ok:
                    self.notify(get_global_i18n().t("bookmarks.jump_success", page=getattr(reader_screen, "current_page", 0) + 1), severity="information")
                    self.app.pop_screen()
                    return
                else:
                    self.notify(get_global_i18n().t("bookmarks.jump_failed", page=getattr(reader_screen, "current_page", 0) + 1), severity="error")
                    return
            
            # 否则：本地使用 ReaderScreen 的内部方法组合实现
            corrected_offset = approx_offset
            try:
                if hasattr(reader_screen, "_rehydrate_offset_from_anchor") and (anchor_text or anchor_hash):
                    corrected = reader_screen._rehydrate_offset_from_anchor(anchor_text, anchor_hash, original)  # type: ignore[attr-defined]
                    if isinstance(corrected, int) and corrected >= 0:
                        corrected_offset = corrected
            except Exception:
                pass
            
            # 映射到页码
            page_index = 0
            if hasattr(reader_screen, "_find_page_for_offset"):
                page_index = reader_screen._find_page_for_offset(corrected_offset)  # type: ignore[attr-defined]
            display_page = page_index + 1
            
            # 跳转到页
            if hasattr(reader_screen, "renderer") and hasattr(reader_screen.renderer, "goto_page"):
                success = reader_screen.renderer.goto_page(display_page)
                if not success:
                    self.notify(get_global_i18n().t("bookmarks.jump_failed", page=display_page), severity="error")
                    return
                # 页内精确滚动：利用行偏移二分定位
                try:
                    if hasattr(reader_screen, "_line_offsets_per_page"):
                        lines = reader_screen._line_offsets_per_page[page_index]  # type: ignore[attr-defined]
                        # 二分找到小于等于 corrected_offset 的最大行索引
                        lo, hi, line_idx = 0, len(lines) - 1, 0
                        while lo <= hi:
                            mid = (lo + hi) // 2
                            if lines[mid] <= corrected_offset:
                                line_idx = mid
                                lo = mid + 1
                            else:
                                hi = mid - 1
                        if hasattr(reader_screen, "_set_scroll_to_line"):
                            reader_screen._set_scroll_to_line(line_idx)  # type: ignore[attr-defined]
                except Exception:
                    pass
                
                # 更新状态并提示
                if hasattr(reader_screen, "_on_page_change"):
                    reader_screen._on_page_change(page_index)
                if hasattr(reader_screen, "_update_scroll_indicator"):
                    reader_screen._update_scroll_indicator()
                reader_screen.current_page = page_index
                reader_screen.total_pages = reader_screen.renderer.total_pages
                self.notify(get_global_i18n().t("bookmarks.jump_success", page=display_page), severity="information")
                self.app.pop_screen()
            else:
                self.notify(get_global_i18n().t("bookmarks.page_jump_not_supported"), severity="error")
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.jump_error", error=str(e)), severity="error")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            self.app.pop_screen()
            event.stop()
        elif event.key == "delete":
            if not self._has_permission("bookmarks.delete"):
                self.notify(get_global_i18n().t("bookmarks.np_delete_bookmark"), severity="error")
                event.stop()
                return
            self._delete_selected_bookmark()
        elif event.key == "enter":
            if not self._has_permission("bookmarks.goto"):
                self.notify(get_global_i18n().t("bookmarks.np_goto_bookmark"), severity="error")
                event.stop()
                return
            self._goto_selected_bookmark()
        elif event.key == "n":
            # N键下一页
            self._go_to_next_page()
            event.prevent_default()
        elif event.key == "p":
            # P键上一页
            self._go_to_prev_page()
            event.prevent_default()
        elif event.key == "down":
            # 下键：如果到达当前页底部且有下一页，则翻到下一页
            if not self._has_permission("bookmarks.navigation"):
                self.notify(get_global_i18n().t("common.no_perm_page"), severity="error")
                event.stop()
                return
            list_view = self.query_one("#bookmarks-list", ListView)
            if (list_view.index == len(list_view.children) - 1 and 
                self._current_page < self._total_pages):
                self._go_to_next_page()
                # 将光标移动到新页面的第一项
                list_view.index = 0
                event.prevent_default()
        elif event.key == "up":
            # 上键：如果到达当前页顶部且有上一页，则翻到上一页
            if not self._has_permission("bookmarks.navigation"):
                self.notify(get_global_i18n().t("common.no_perm_page"), severity="error")
                event.stop()
                return
            list_view = self.query_one("#bookmarks-list", ListView)
            if list_view.index == 0 and self._current_page > 1:
                self._go_to_prev_page()
                # 将光标移动到新页面的最后一项
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
                    # 获取当前用户ID
                    from src.utils.multi_user_manager import multi_user_manager
                    current_user = multi_user_manager.get_current_user()
                    user_id = current_user.get('id') if current_user else None
                    
                    # 获取当前用户ID - 使用标准模式
                    current_user = getattr(self.app, 'current_user', None)
                    user_id = current_user.get('id') if current_user else None
                    
                    # 如果没有从应用实例获取到用户信息，回退到多用户管理器
                    if user_id is None:
                        from src.utils.multi_user_manager import multi_user_manager
                        current_user = multi_user_manager.get_current_user()
                        user_id = current_user.get('id') if current_user else None
                    
                    # 如果多用户模式关闭，user_id应该为None（查询所有数据）
                    if user_id is not None:
                        from src.utils.multi_user_manager import multi_user_manager
                        if not multi_user_manager.is_multi_user_enabled():
                            user_id = None
                    
                    if bookmark.id and self.bookmark_manager.remove_bookmark(bookmark.id, user_id):
                        self.bookmarks.pop(actual_index)
                        self._refresh_bookmark_list()
                        self.notify(get_global_i18n().t("common.bookmark_deleted"), severity="information")
                    else:
                        self.notify(get_global_i18n().t("common.delete_bookmark_failed"), severity="error")
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
                        bookmark_info = f"{get_global_i18n().t('common.position')}: {bookmark.position}"
                    
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
                    
                    # 获取当前用户ID - 使用标准模式
                    current_user = getattr(self.app, 'current_user', None)
                    user_id = current_user.get('id') if current_user else None
                    
                    # 如果没有从应用实例获取到用户信息，回退到多用户管理器
                    if user_id is None:
                        from src.utils.multi_user_manager import multi_user_manager
                        current_user = multi_user_manager.get_current_user()
                        user_id = current_user.get('id') if current_user else None
                    
                    # 如果多用户模式关闭，user_id应该为None（查询所有数据）
                    if user_id is not None:
                        from src.utils.multi_user_manager import multi_user_manager
                        if not multi_user_manager.is_multi_user_enabled():
                            user_id = None
                    
                    # 更新书签备注
                    success = self.bookmark_manager.update_bookmark_note(bookmark.id, result, user_id)
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
            
            # 获取当前用户ID - 使用标准模式
            current_user = getattr(self.app, 'current_user', None)
            user_id = current_user.get('id') if current_user else None
            
            # 如果没有从应用实例获取到用户信息，回退到多用户管理器
            if user_id is None:
                from src.utils.multi_user_manager import multi_user_manager
                current_user = multi_user_manager.get_current_user()
                user_id = current_user.get('id') if current_user else None
            
            # 如果多用户模式关闭，user_id应该为None（查询所有数据）
            if user_id is not None:
                from src.utils.multi_user_manager import multi_user_manager
                if not multi_user_manager.is_multi_user_enabled():
                    user_id = None
            
            # 删除所有书签
            for bookmark in self.bookmarks:
                if bookmark.id:
                    self.bookmark_manager.remove_bookmark(bookmark.id, user_id)
            
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
            # 获取当前用户ID - 使用标准模式
            current_user = getattr(self.app, 'current_user', None)
            user_id = current_user.get('id') if current_user else None
            
            # 如果没有从应用实例获取到用户信息，回退到多用户管理器
            if user_id is None:
                from src.utils.multi_user_manager import multi_user_manager
                current_user = multi_user_manager.get_current_user()
                user_id = current_user.get('id') if current_user else None
            
            # 如果多用户模式关闭，user_id应该为None（查询所有数据）
            if user_id is not None:
                from src.utils.multi_user_manager import multi_user_manager
                if not multi_user_manager.is_multi_user_enabled():
                    user_id = None
            
            self.bookmarks = self.bookmark_manager.get_bookmarks(self.book_id, user_id)
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
            
            # 更新分页信息
            self._update_pagination_info()
            
        except Exception as e:
            self.notify(get_global_i18n().t("bookmarks.refresh_failed", error=str(e)), severity="error")
    
    def _update_pagination_info(self) -> None:
        """更新分页信息"""
        try:
            page_label = self.query_one("#page-info-nav", Label)
            page_label.update(f"{self._current_page}/{self._total_pages}")
            
            # 更新分页按钮状态
            first_btn = self.query_one("#first-page-btn", Button)
            prev_btn = self.query_one("#prev-page-btn", Button) 
            next_btn = self.query_one("#next-page-btn", Button)
            last_btn = self.query_one("#last-page-btn", Button)
            
            # 设置按钮的禁用状态
            first_btn.disabled = self._current_page <= 1
            prev_btn.disabled = self._current_page <= 1
            next_btn.disabled = self._current_page >= self._total_pages
            last_btn.disabled = self._current_page >= self._total_pages
        except Exception as e:
            self.notify(f"更新分页信息失败: {e}", severity="error")
    
    # 分页导航方法
    def _go_to_first_page(self) -> None:
        """跳转到第一页"""
        if self._current_page != 1:
            self._current_page = 1
            self._refresh_bookmark_list()
    
    def _go_to_prev_page(self) -> None:
        """跳转到上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self._refresh_bookmark_list()
    
    def _go_to_next_page(self) -> None:
        """跳转到下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._refresh_bookmark_list()
    
    def _go_to_last_page(self) -> None:
        """跳转到最后一页"""
        if self._current_page != self._total_pages:
            self._current_page = self._total_pages
            self._refresh_bookmark_list()
    
    def _show_jump_dialog(self) -> None:
        """显示跳转页码对话框"""
        def handle_jump_result(result: Optional[str]) -> None:
            """处理跳转结果"""
            if result and result.strip():
                try:
                    page_num = int(result.strip())
                    if 1 <= page_num <= self._total_pages:
                        if page_num != self._current_page:
                            self._current_page = page_num
                            self._refresh_bookmark_list()
                    else:
                        self.notify(
                            get_global_i18n().t("batch_ops.page_error_info", pages=self._total_pages), 
                            severity="error"
                        )
                except ValueError:
                    self.notify(get_global_i18n().t("batch_ops.page_error"), severity="error")
        
        # 导入并显示页码输入对话框
        from src.ui.dialogs.input_dialog import InputDialog
        dialog = InputDialog(
            None,  # bookmarks_screen doesn't have theme_manager
            title=get_global_i18n().t("bookshelf.jump_to"),
            prompt=f"{get_global_i18n().t('batch_ops.type_num')} (1-{self._total_pages})",
            placeholder=f"{get_global_i18n().t('batch_ops.current')}: {self._current_page}/{self._total_pages}"
        )
        self.app.push_screen(dialog, handle_jump_result)