"""
书籍网站管理屏幕
"""

from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Label, DataTable, Input, Select, Checkbox, Header, Footer
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

logger = get_logger(__name__)

class NovelSitesManagementScreen(Screen[None]):

    # 使用 Textual BINDINGS 进行快捷键绑定
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("a", "add_site", get_global_i18n().t('common.add')),
        ("e", "edit_site", get_global_i18n().t('common.edit')),
        ("d", "delete_site", get_global_i18n().t('common.delete')),
        ("b", "batch_delete", get_global_i18n().t('novel_sites.batch_delete')),
        ("space", "toggle_select", get_global_i18n().t('common.select')),
        ("enter", "enter_crawler", get_global_i18n().t('get_books.enter')),
        
    ]

    """书籍网站管理屏幕"""
    
    CSS_PATH = "../styles/novel_sites_management_overrides.tcss"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化书籍网站管理屏幕
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        try:
            self.title = get_global_i18n().t('novel_sites.title')
        except RuntimeError:
            # 如果全局i18n未初始化，使用默认标题
            self.title = "书籍网站管理"
        self.theme_manager = theme_manager
        self.database_manager = DatabaseManager()
        self.novel_sites = []  # 书籍网站列表
        self.selected_sites = set()  # 选中的网站索引

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            return self.database_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def compose(self) -> ComposeResult:
        """
        组合书籍网站管理屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Vertical(
                # Label(get_global_i18n().t('novel_sites.title'), id="novel-sites-title", classes="section-title"),
                Label(get_global_i18n().t('novel_sites.description'), id="novel-sites-description"),
                
                # 操作按钮区域
                Horizontal(
                    Button(get_global_i18n().t('novel_sites.add'), id="add-btn"),
                    Button(get_global_i18n().t('novel_sites.edit'), id="edit-btn"),
                    Button(get_global_i18n().t('novel_sites.delete'), id="delete-btn"),
                    Button(get_global_i18n().t('novel_sites.batch_delete'), id="batch-delete-btn"),
                    Button(get_global_i18n().t('novel_sites.back'), id="back-btn"),
                    id="novel-sites-buttons", classes="btn-row"
                ),
                
                # 书籍网站列表
                DataTable(id="novel-sites-table"),
                
                # 状态信息
                Label("", id="novel-sites-status"),
                
                # 快捷键状态栏
                # Horizontal(
                #     Label(get_global_i18n().t('novel_sites.shortcut_a'), id="shortcut-a"),
                #     Label(get_global_i18n().t('novel_sites.shortcut_e'), id="shortcut-e"),
                #     Label(get_global_i18n().t('novel_sites.shortcut_d'), id="shortcut-d"),
                #     Label(get_global_i18n().t('novel_sites.shortcut_b'), id="shortcut-b"),
                #     Label(get_global_i18n().t('novel_sites.shortcut_space'), id="shortcut-space"),
                #     Label(get_global_i18n().t('novel_sites.shortcut_enter'), id="shortcut-enter"),
                #     Label(get_global_i18n().t('novel_sites.shortcut_esc'), id="shortcut-esc"),
                #     id="shortcuts-bar", classes="status-bar"
                # ),
                id="novel-sites-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 初始化数据表
        table = self.query_one("#novel-sites-table", DataTable)
        table.add_columns(
            get_global_i18n().t('novel_sites.selected'),
            get_global_i18n().t('novel_sites.site_name'),
            get_global_i18n().t('novel_sites.site_url'),
            get_global_i18n().t('novel_sites.storage_folder'),
            get_global_i18n().t('novel_sites.proxy_enabled'),
            get_global_i18n().t('novel_sites.parser')
        )
        
        # 加载书籍网站数据
        self._load_novel_sites()

        # 确保表格获得焦点并初始化光标到第一行
        try:
            table.focus()
        except Exception:
            pass
        try:
            if getattr(table, "cursor_row", None) is None and len(self.novel_sites) > 0:
                table.cursor_row = 0
        except Exception:
            pass
    
    def _load_novel_sites(self) -> None:
        """从数据库加载书籍网站数据"""
        self.novel_sites = self.database_manager.get_novel_sites()
        
        # 更新数据表
        self._update_table()
    
    def _update_table(self) -> None:
        """更新数据表显示（保持光标行）"""
        table = self.query_one("#novel-sites-table", DataTable)
        # 保存当前光标行（如果存在）
        prev_cursor = table.cursor_row if getattr(table, "cursor_row", None) is not None else None

        table.clear()
        
        for index, site in enumerate(self.novel_sites):
            selected = "✓" if index in self.selected_sites else ""
            proxy_status = get_global_i18n().t('common.yes') if site["proxy_enabled"] else get_global_i18n().t('common.no')
            table.add_row(
                selected,
                site["name"],
                site["url"],
                site["storage_folder"],
                proxy_status,
                site["parser"],
                key=str(index)
            )

        # 恢复光标行（尽可能回到原位置），如无则初始化到0
        if len(self.novel_sites) > 0:
            restored = 0
            if prev_cursor is not None:
                restored = min(prev_cursor, len(self.novel_sites) - 1)
            try:
                table.cursor_row = restored
            except Exception:
                try:
                    table.move_cursor(restored, 0)
                except Exception:
                    pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "add-btn":
            self._show_add_dialog()
        elif event.button.id == "edit-btn":
            self._show_edit_dialog()
        elif event.button.id == "delete-btn":
            self._delete_selected()
        elif event.button.id == "batch-delete-btn":
            self._batch_delete()
        elif event.button.id == "back-btn":
            self.app.pop_screen()  # 返回上一页
    
    def _show_add_dialog(self) -> None:
        """显示添加书籍网站对话框"""
        from src.ui.dialogs.novel_site_dialog import NovelSiteDialog
        dialog = NovelSiteDialog(self.theme_manager, None)
        self.app.push_screen(dialog, self._handle_add_result)
    
    def _show_edit_dialog(self) -> None:
        """显示编辑书籍网站对话框"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows):
            # 获取选中的行数据
            row_data = table.get_row_at(table.cursor_row)
            if row_data and len(row_data) > 0:
                # 第一列是网站名称，我们通过名称来查找对应的网站
                site_name = row_data[1]  # 第二列是网站名称
                site_index = -1
                for i, site in enumerate(self.novel_sites):
                    if site["name"] == site_name:
                        site_index = i
                        break
                
                if site_index >= 0 and site_index < len(self.novel_sites):
                    site = self.novel_sites[site_index]
                    from src.ui.dialogs.novel_site_dialog import NovelSiteDialog
                    dialog = NovelSiteDialog(self.theme_manager, site)
                    self.app.push_screen(dialog, lambda result: self._handle_edit_result(result, site_index))
                else:
                    self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            else:
                self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
        else:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
    
    def _handle_add_result(self, result: Optional[Dict[str, Any]]) -> None:
        """处理添加结果"""
        if result:
            # 保存到数据库
            success = self.database_manager.save_novel_site(result)
            if success:
                # 重新加载数据
                self._load_novel_sites()
                self._update_status(get_global_i18n().t('novel_sites.added_success'))
            else:
                self._update_status(get_global_i18n().t('novel_sites.add_failed'), "error")
        else:
            # 如果结果为None，说明用户取消了操作
            self._update_status(get_global_i18n().t('novel_sites.add_cancelled'))
    
    def _handle_edit_result(self, result: Optional[Dict[str, Any]], site_index: int) -> None:
        """处理编辑结果"""
        if result and 0 <= site_index < len(self.novel_sites):
            # 保存到数据库
            success = self.database_manager.save_novel_site(result)
            if success:
                # 重新加载数据
                self._load_novel_sites()
                self._update_status(get_global_i18n().t('novel_sites.edited_success'))
            else:
                self._update_status(get_global_i18n().t('novel_sites.edit_failed'), "error")
    
    def _delete_selected(self) -> None:
        """删除选中的书籍网站"""
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows):
            row_data = table.get_row_at(table.cursor_row)
            if row_data and len(row_data) > 0:
                site_name = row_data[1]  # 第二列是网站名称
                site_index = -1
                for i, site in enumerate(self.novel_sites):
                    if site["name"] == site_name:
                        site_index = i
                        break
                
                if site_index >= 0 and site_index < len(self.novel_sites):
                    # 显示确认对话框
                    from src.ui.dialogs.confirm_dialog import ConfirmDialog
                    dialog = ConfirmDialog(
                        self.theme_manager,
                        get_global_i18n().t('novel_sites.confirm_delete'),
                        f"{get_global_i18n().t('novel_sites.confirm_delete_message')}: {site_name}"
                    )
                    self.app.push_screen(dialog, lambda result: self._handle_delete_confirm(result, site_index))
                else:
                    self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
            else:
                self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
        else:
            self._update_status(get_global_i18n().t('novel_sites.select_site_first'))
    
    def _batch_delete(self) -> None:
        """批量删除选中的书籍网站"""
        if not self.selected_sites:
            self._update_status(get_global_i18n().t('novel_sites.select_sites_first'))
            return
        
        # 显示确认对话框
        from src.ui.dialogs.confirm_dialog import ConfirmDialog
        dialog = ConfirmDialog(
            self.theme_manager,
            get_global_i18n().t('novel_sites.confirm_batch_delete'),
            f"{get_global_i18n().t('novel_sites.confirm_batch_delete_message')}: {len(self.selected_sites)}"
        )
        self.app.push_screen(dialog, self._handle_batch_delete_confirm)
    
    def _handle_delete_confirm(self, result: Optional[bool], site_index: int) -> None:
        """处理删除确认"""
        if result and 0 <= site_index < len(self.novel_sites):
            site = self.novel_sites[site_index]
            site_id = site.get("id")
            if site_id:
                # 从数据库删除
                success = self.database_manager.delete_novel_site(site_id)
                if success:
                    # 重新加载数据
                    self._load_novel_sites()
                    self._update_status(f"{get_global_i18n().t('novel_sites.deleted_success')}: {site['name']}")
                else:
                    self._update_status(get_global_i18n().t('novel_sites.delete_failed'), "error")
            else:
                self._update_status(get_global_i18n().t('novel_sites.delete_failed'), "error")
    
    def _handle_batch_delete_confirm(self, result: Optional[bool]) -> None:
        """处理批量删除确认"""
        if result and self.selected_sites:
            deleted_count = 0
            failed_count = 0
            
            # 按索引从大到小删除，避免索引变化
            for index in sorted(self.selected_sites, reverse=True):
                if 0 <= index < len(self.novel_sites):
                    site = self.novel_sites[index]
                    site_id = site.get("id")
                    if site_id:
                        # 从数据库删除
                        success = self.database_manager.delete_novel_site(site_id)
                        if success:
                            deleted_count += 1
                        else:
                            failed_count += 1
            
            self.selected_sites.clear()
            # 重新加载数据
            self._load_novel_sites()
            
            if failed_count == 0:
                self._update_status(f"{get_global_i18n().t('novel_sites.batch_deleted_success')}: {deleted_count}")
            else:
                self._update_status(f"{get_global_i18n().t('novel_sites.batch_deleted_partial')}: {deleted_count}成功, {failed_count}失败", "error")
    
    def on_data_table_row_selected(self, event) -> None:
        """
        数据表行选择时的回调
        
        Args:
            event: 行选择事件
        """
        if event is None:
            # 处理从 key_enter 调用的情况
            table = self.query_one("#novel-sites-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(table.rows):
                row_data = table.get_row_at(table.cursor_row)
                if row_data and len(row_data) > 0:
                    site_name = row_data[1]  # 第二列是网站名称
                    for site in self.novel_sites:
                        if site["name"] == site_name:
                            # 进入爬取管理页面
                            self.app.push_screen("crawler_management", site)
                            break
        elif event.row_key and hasattr(event.row_key, 'value'):
            site_index = int(event.row_key.value)
            if 0 <= site_index < len(self.novel_sites):
                # 进入爬取管理页面
                site = self.novel_sites[site_index]
                self.app.push_screen("crawler_management", site)
    
    def on_data_table_cell_selected(self, event) -> None:
        """
        数据表单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        if event.coordinate and event.coordinate.row < len(self.novel_sites):
            # 通过行索引直接获取网站
            site_index = event.coordinate.row
            
            # 切换选择状态（第一列）
            if event.coordinate.column == 0:
                if site_index in self.selected_sites:
                    self.selected_sites.remove(site_index)
                else:
                    self.selected_sites.add(site_index)
                self._update_table()
    
    # Actions for BINDINGS
    def action_add_site(self) -> None:
        self._show_add_dialog()

    def action_edit_site(self) -> None:
        self._show_edit_dialog()

    def action_delete_site(self) -> None:
        self._delete_selected()

    def action_batch_delete(self) -> None:
        self._batch_delete()

    def action_toggle_select(self) -> None:
        table = self.query_one("#novel-sites-table", DataTable)
        # 确保表格获取焦点，这样按键行为与光标同步
        try:
            table.focus()
        except Exception:
            pass
        if table.cursor_row is not None and table.cursor_row < len(self.novel_sites):
            site_index = table.cursor_row
            if site_index in self.selected_sites:
                self.selected_sites.remove(site_index)
            else:
                self.selected_sites.add(site_index)
            self._update_table()

    def action_enter_crawler(self) -> None:
        table = self.query_one("#novel-sites-table", DataTable)
        if table.cursor_row is not None:
            self.on_data_table_row_selected(None)

    def action_back(self) -> None:
        self.app.pop_screen()

    def _update_status(self, message: str, severity: str = "information") -> None:
        """更新状态信息"""
        status_label = self.query_one("#novel-sites-status", Label)
        status_label.update(message)
        
        # 根据严重程度设置样式
        if severity == "success":
            status_label.styles.color = "green"
        elif severity == "error":
            status_label.styles.color = "red"
        else:
            status_label.styles.color = "blue"
    
    def key_a(self) -> None:
        """A键 - 添加书籍网站"""
        if self._has_permission("novel_sites.add"):
            self._show_add_dialog()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_add_site'), severity="warning")
    
    def key_e(self) -> None:
        """E键 - 编辑选中的书籍网站"""
        if self._has_permission("novel_sites.edit"):
            self._show_edit_dialog()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_edit_site'), severity="warning")
    
    def key_d(self) -> None:
        """D键 - 删除选中的书籍网站"""
        if self._has_permission("novel_sites.delete"):
            self._delete_selected()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_delete_site'), severity="warning")
    
    def key_b(self) -> None:
        """B键 - 批量删除"""
        if self._has_permission("novel_sites.batch_delete"):
            self._batch_delete()
        else:
            self.notify(get_global_i18n().t('novel_sites.np_batch_delete_site'), severity="warning")
    
    def key_enter(self) -> None:
        """Enter键 - 进入爬取管理页面"""
        if self._has_permission("novel_sites.enter_crawler"):
            table = self.query_one("#novel-sites-table", DataTable)
            if table.cursor_row is not None:
                self.on_data_table_row_selected(None)
        else:
            self.notify(get_global_i18n().t('novel_sites.np_open_carwler'), severity="warning")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回
            self.app.pop_screen()
            event.stop()
            return