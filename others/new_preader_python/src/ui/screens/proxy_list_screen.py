"""
代理列表管理屏幕
支持多条代理信息管理，同一时间只能开启一个代理
"""

import asyncio
from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, DataTable, Input, Select, Checkbox
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events
from pathlib import Path

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager

logger = get_logger(__name__)

class ProxyListScreen(Screen[None]):
    """代理列表管理屏幕"""
    
    # 加载CSS样式
    CSS_PATH = "../styles/proxy_list_screen.css"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化代理列表管理屏幕
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        try:
            self.title = get_global_i18n().t('proxy_list.title')
        except RuntimeError:
            # 如果全局i18n未初始化，使用默认标题
            self.title = "代理列表管理"
        self.theme_manager = theme_manager
        self.database_manager = DatabaseManager()
        self.proxy_list = []
        self.selected_proxy_id = None
    
    def compose(self) -> ComposeResult:
        """
        组合代理列表管理屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        # 获取i18n文本，如果未初始化则使用默认值
        try:
            i18n = get_global_i18n()
            title = i18n.t('proxy_list.title')
            description = i18n.t('proxy_list.description')
            add_proxy = i18n.t('proxy_list.add_proxy')
            test_connection = i18n.t('proxy_list.test_connection')
            edit_proxy = i18n.t('proxy_list.edit_proxy')
            delete_proxy = i18n.t('proxy_list.delete_proxy')
            enable_proxy = i18n.t('proxy_list.enable_proxy')
            back = i18n.t('proxy_list.back')
            shortcut_a = i18n.t('proxy_list.shortcut_a')
            shortcut_t = i18n.t('proxy_list.shortcut_t')
            shortcut_e = i18n.t('proxy_list.shortcut_e')
            shortcut_d = i18n.t('proxy_list.shortcut_d')
            shortcut_esc = i18n.t('proxy_list.shortcut_esc')
        except RuntimeError:
            # 使用默认值
            title = "代理列表管理"
            description = "管理多条代理信息，同一时间只能开启一个代理"
            add_proxy = "添加代理"
            test_connection = "测试连接"
            edit_proxy = "编辑"
            delete_proxy = "删除"
            enable_proxy = "启用"
            back = "返回"
            shortcut_a = "A: 添加代理"
            shortcut_t = "T: 测试连接"
            shortcut_e = "E: 编辑代理"
            shortcut_d = "D: 删除代理"
            shortcut_esc = "ESC: 返回"
        
        yield Container(
            Vertical(
                # 固定标题
                Label(title, id="proxy-list-title"),
                Label(description, id="proxy-list-description"),
                
                # 操作按钮区域
                Horizontal(
                    Button(add_proxy, id="add-proxy-btn", variant="primary"),
                    Button(test_connection, id="test-connection-btn"),
                    Button(edit_proxy, id="edit-proxy-btn"),
                    Button(delete_proxy, id="delete-proxy-btn", variant="warning"),
                    Button(back, id="back-btn"),
                    id="proxy-list-buttons"
                ),
                
                # 状态信息
                Label("", id="proxy-list-status"),
                
                # 代理列表表格
                DataTable(id="proxy-list-table"),
                
                # 快捷键状态栏
                Horizontal(
                    Label(shortcut_a, id="shortcut-a"),
                    Label(shortcut_t, id="shortcut-t"),
                    Label(shortcut_e, id="shortcut-e"),
                    Label(shortcut_d, id="shortcut-d"),
                    Label(shortcut_esc, id="shortcut-esc"),
                    id="shortcuts-bar"
                ),
                id="proxy-list-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 加载代理列表
        self._load_proxy_list()
        
        # 初始化表格
        self._init_table()
        
        # 设置默认焦点到表格
        table = self.query_one("#proxy-list-table", DataTable)
        if table:
            self.set_focus(table)
    
    def _load_proxy_list(self) -> None:
        """从数据库加载代理列表"""
        self.proxy_list = self.database_manager.get_all_proxy_settings()
    
    def _init_table(self) -> None:
        """初始化表格"""
        table = self.query_one("#proxy-list-table", DataTable)
        table.clear()
        
        # 启用表格交互功能
        table.cursor_type = "row"  # 启用行光标
        table.zebra_stripes = True  # 启用斑马纹
        table.add_columns(
            "状态",
            "名称", 
            "类型",
            "主机",
            "端口",
            "用户名",
            "更新时间"
        )
        
        # 加载数据并填充表格
        self._load_proxy_list()
        self._fill_table_data()
        
        # 设置默认选中第一行
        if len(self.proxy_list) > 0:
            table.move_cursor(row=0)
            self.selected_proxy_id = self.proxy_list[0].get("id")
        
    def _fill_table_data(self) -> None:
        """填充表格数据"""
        table = self.query_one("#proxy-list-table", DataTable)
        
        # 添加数据行
        for proxy in self.proxy_list:
            status = "✓" if proxy.get("enabled") else "○"
            table.add_row(
                status,
                proxy.get("name", ""),
                proxy.get("type", ""),
                proxy.get("host", ""),
                proxy.get("port", ""),
                proxy.get("username", "") or "",
                proxy.get("updated_at", "")[:16]  # 只显示日期和时间部分
            )
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """处理表格行选择事件"""
        self.selected_proxy_id = None
        if event.cursor_row is not None:
            # 获取选中的代理ID
            row_index = event.cursor_row
            if 0 <= row_index < len(self.proxy_list):
                self.selected_proxy_id = self.proxy_list[row_index].get("id")
                logger.debug(f"选中代理ID: {self.selected_proxy_id}")
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """处理表格单元格选择事件"""
        self.selected_proxy_id = None
        if event.cursor_row is not None:
            # 获取选中的代理ID
            row_index = event.cursor_row
            if 0 <= row_index < len(self.proxy_list):
                self.selected_proxy_id = self.proxy_list[row_index].get("id")
                logger.debug(f"选中代理ID: {self.selected_proxy_id}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "add-proxy-btn":
            self._add_proxy()
        elif event.button.id == "test-connection-btn":
            self._test_connection()
        elif event.button.id == "edit-proxy-btn":
            self._edit_proxy()
        elif event.button.id == "delete-proxy-btn":
            self._delete_proxy()
        elif event.button.id == "back-btn":
            self.app.pop_screen()
    
    def _add_proxy(self) -> None:
        """添加代理"""
        # 创建代理编辑对话框
        from src.ui.dialogs.proxy_edit_dialog import ProxyEditDialog
        
        def on_proxy_saved(proxy_data: Optional[Dict[str, Any]]) -> None:
            """处理代理保存结果"""
            if proxy_data:
                # 添加新代理
                success = self.database_manager.add_proxy_setting(proxy_data)
                if success:
                    self._update_status("代理添加成功", "success")
                    self._refresh_list()
                else:
                    self._update_status("代理添加失败", "error")
        
        self.app.push_screen(
            ProxyEditDialog(self.theme_manager),
            callback=on_proxy_saved
        )
    
    def _edit_proxy(self) -> None:
        """编辑代理"""
        if not self.selected_proxy_id:
            self._update_status("请先选择一个代理", "warning")
            return
        
        # 获取选中的代理数据
        proxy_data = None
        for proxy in self.proxy_list:
            if proxy.get("id") == self.selected_proxy_id:
                proxy_data = proxy
                break
        
        if not proxy_data:
            self._update_status("未找到选中的代理", "error")
            return
        
        # 创建代理编辑对话框
        from src.ui.dialogs.proxy_edit_dialog import ProxyEditDialog
        
        def on_proxy_saved(updated_data: Optional[Dict[str, Any]]) -> None:
            """处理代理保存结果"""
            if updated_data:
                # 更新代理
                success = self.database_manager.update_proxy_setting(self.selected_proxy_id, updated_data)
                if success:
                    self._update_status("代理更新成功", "success")
                    self._refresh_list()
                else:
                    self._update_status("代理更新失败", "error")
        
        self.app.push_screen(
            ProxyEditDialog(self.theme_manager, proxy_data),
            callback=on_proxy_saved
        )
    
    def _delete_proxy(self) -> None:
        """删除代理"""
        if not self.selected_proxy_id:
            self._update_status("请先选择一个代理", "warning")
            return
        
        # 创建确认对话框
        from src.ui.dialogs.confirm_dialog import ConfirmDialog
        
        def on_confirm(confirmed: bool) -> None:
            """处理确认结果"""
            if confirmed:
                # 删除代理
                success = self.database_manager.delete_proxy_setting(self.selected_proxy_id)
                if success:
                    self._update_status("代理删除成功", "success")
                    self._refresh_list()
                    self.selected_proxy_id = None
                else:
                    self._update_status("代理删除失败", "error")
        
        self.app.push_screen(
            ConfirmDialog(
                self.theme_manager,
                "确认删除",
                f"确定要删除选中的代理吗？此操作不可撤销。"
            ),
            callback=on_confirm
        )
    
    def _test_connection(self) -> None:
        """测试代理连接"""
        if not self.selected_proxy_id:
            self._update_status("请先选择一个代理", "warning")
            return
        
        # 获取选中的代理数据
        proxy_data = None
        for proxy in self.proxy_list:
            if proxy.get("id") == self.selected_proxy_id:
                proxy_data = proxy
                break
        
        if not proxy_data:
            self._update_status("未找到选中的代理", "error")
            return
        
        # 测试连接
        self._update_status("正在测试连接...", "information")
        
        # 模拟测试（实际实现中应该进行真实的网络测试）
        import time
        time.sleep(1)
        
        # 随机返回结果
        import random
        if random.random() > 0.3:
            self._update_status("连接测试成功", "success")
        else:
            self._update_status("连接测试失败", "error")
    
    def _refresh_list(self) -> None:
        """刷新代理列表"""
        self._load_proxy_list()
        self._init_table()
    
    def _update_status(self, message: str, severity: str = "information") -> None:
        """更新状态信息"""
        status_label = self.query_one("#proxy-list-status", Label)
        status_label.update(message)
        
        # 根据严重程度设置样式
        if severity == "success":
            status_label.styles.color = "green"
        elif severity == "error":
            status_label.styles.color = "red"
        elif severity == "warning":
            status_label.styles.color = "yellow"
        else:
            status_label.styles.color = "blue"
    
    def key_a(self) -> None:
        """A键 - 添加代理"""
        self._add_proxy()
    
    def key_t(self) -> None:
        """T键 - 测试连接"""
        self._test_connection()
    
    def key_e(self) -> None:
        """E键 - 编辑代理"""
        self._edit_proxy()
    
    def key_d(self) -> None:
        """D键 - 删除代理"""
        self._delete_proxy()
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        table = self.query_one("#proxy-list-table", DataTable)
        
        if event.key == "escape":
            # ESC键返回
            self.app.pop_screen()
            event.prevent_default()
        elif event.key in ["up", "down"]:
            # 上下键移动时更新选中状态
            if table.cursor_row is not None:
                row_index = table.cursor_row
                if 0 <= row_index < len(self.proxy_list):
                    self.selected_proxy_id = self.proxy_list[row_index].get("id")
                    logger.debug(f"键盘移动选中代理ID: {self.selected_proxy_id}")