"""
代理列表管理屏幕
支持多条代理信息管理，同一时间只能开启一个代理
"""

import asyncio
from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, DataTable, Input, Select, Checkbox, Header, Footer
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events
from pathlib import Path

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

logger = get_logger(__name__)

class ProxyListScreen(Screen[None]):

    # 使用 Textual BINDINGS 进行快捷键绑定
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("a", "add_proxy", get_global_i18n().t('common.add')),
        ("t", "test_connection", get_global_i18n().t('proxy_settings.test_connection')),
        ("e", "edit_proxy", get_global_i18n().t('common.edit')),
        ("d", "delete_proxy", get_global_i18n().t('common.delete')),
        
    ]

    """代理列表管理屏幕"""
    
    # 加载CSS样式
    CSS_PATH = "../styles/proxy_list_overrides.tcss"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化代理列表管理屏幕
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        self.title = get_global_i18n().t('proxy_list.title')
        self.theme_manager = theme_manager
        self.database_manager = DatabaseManager()
        self.proxy_list = []
        self.selected_proxy_id = None

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            return self.database_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def compose(self) -> ComposeResult:
        """
        组合代理列表管理屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        # 获取i18n文本
        i18n = get_global_i18n()
        title = i18n.t('proxy_list.title')
        description = i18n.t('proxy_list.description')
        add_proxy = i18n.t('proxy_list.add_proxy')
        test_connection = i18n.t('proxy_list.test_connection')
        edit_proxy = i18n.t('proxy_list.edit_proxy')
        delete_proxy = i18n.t('proxy_list.delete_proxy')
        enable_proxy = i18n.t('proxy_list.enable_proxy')
        back = i18n.t('proxy_list.back')
        shortcut_a = f"{i18n.t('proxy_list.shortcut_a') } {i18n.t('proxy_list.shortcut_t')} {i18n.t('proxy_list.shortcut_e')} {i18n.t('proxy_list.shortcut_d')} {i18n.t('proxy_list.shortcut_esc')}"
        
        
        yield Header()
        yield Container(
            Vertical(
                # 固定标题
                # Label(title, id="proxy-list-title", classes="section-title"),
                Label(description, id="proxy-list-description"),
                
                # 操作按钮区域
                Horizontal(
                    Button(add_proxy, id="add-proxy-btn", variant="primary"),
                    Button(test_connection, id="test-connection-btn"),
                    Button(edit_proxy, id="edit-proxy-btn"),
                    Button(delete_proxy, id="delete-proxy-btn", variant="warning"),
                    Button(back, id="back-btn"),
                    id="proxy-list-buttons", classes="btn-row"
                ),
                
                # 状态信息
                Label("", id="proxy-list-status"),
                
                # 代理列表表格
                DataTable(id="proxy-list-table"),
                
                # 快捷键状态栏
                # Horizontal(
                #     Label(shortcut_a, id="shortcut-a"),
                #     id="shortcuts-bar",
                #     classes="status-bar"
                # ),
                id="proxy-list-container"
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
        if event.coordinate.row is not None:
            # 获取选中的代理ID
            row_index = event.coordinate.row
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
        
        # 确保代理ID是整数类型
        try:
            proxy_id = int(self.selected_proxy_id)
        except (TypeError, ValueError):
            self._update_status("代理ID格式错误", "error")
            return
        
        # 创建代理编辑对话框
        from src.ui.dialogs.proxy_edit_dialog import ProxyEditDialog
        
        def on_proxy_saved(updated_data: Optional[Dict[str, Any]]) -> None:
            """处理代理保存结果"""
            if updated_data:
                # 更新代理
                success = self.database_manager.update_proxy_setting(proxy_id, updated_data)
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
        
        # 确保代理ID是整数类型
        try:
            proxy_id = int(self.selected_proxy_id)
        except (TypeError, ValueError):
            self._update_status("代理ID格式错误", "error")
            return
        
        # 创建确认对话框
        from src.ui.dialogs.confirm_dialog import ConfirmDialog
        
        def on_confirm(confirmed: Optional[bool]) -> None:
            """处理确认结果"""
            if confirmed:
                # 删除代理
                success = self.database_manager.delete_proxy_setting(proxy_id)
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
        
        # 验证代理数据
        if not proxy_data.get("host") or not proxy_data.get("port"):
            self._update_status("代理设置不完整，请检查主机地址和端口号", "error")
            return
        
        # 验证端口号格式
        try:
            port = int(proxy_data.get("port"))
            if port < 1 or port > 65535:
                self._update_status("端口号必须在1-65535之间", "error")
                return
        except (ValueError, TypeError):
            self._update_status("端口号必须是数字", "error")
            return
        
        # 测试连接
        self._update_status("正在测试连接...", "information")
        
        # 构建代理URL
        proxy_type = proxy_data.get("type", "HTTP").lower()
        host = proxy_data.get("host")
        port = proxy_data.get("port")
        username = proxy_data.get("username", "")
        password = proxy_data.get("password", "")
        
        if username and password:
            proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
        else:
            proxy_url = f"{proxy_type}://{host}:{port}"
        
        # 执行真实的代理连接测试
        test_result = self._real_test_proxy_connection(proxy_url)
        
        if test_result:
            self._update_status("连接测试成功", "success")
        else:
            self._update_status("连接测试失败", "error")
    
    # Actions for BINDINGS
    def action_add_proxy(self) -> None:
        self._add_proxy()

    def action_test_connection(self) -> None:
        self._test_connection()

    def action_edit_proxy(self) -> None:
        self._edit_proxy()

    def action_delete_proxy(self) -> None:
        self._delete_proxy()

    def action_back(self) -> None:
        self.app.pop_screen()

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
        if self._has_permission("proxy.add"):
            self._add_proxy()
        else:
            self._update_status("无权限添加代理", "warning")
    
    def key_t(self) -> None:
        """T键 - 测试连接"""
        if self._has_permission("proxy.test"):
            self._test_connection()
        else:
            self._update_status("无权限测试连接", "warning")
    
    def key_e(self) -> None:
        """E键 - 编辑代理"""
        if self._has_permission("proxy.edit"):
            self._edit_proxy()
        else:
            self._update_status("无权限编辑代理", "warning")
    
    def key_d(self) -> None:
        """D键 - 删除代理"""
        if self._has_permission("proxy.delete"):
            self._delete_proxy()
        else:
            self._update_status("无权限删除代理", "warning")
    
    def _real_test_proxy_connection(self, proxy_url: str) -> bool:
        """
        真实的代理连接测试
        
        Args:
            proxy_url: 代理URL
            
        Returns:
            bool: 代理是否可用
        """
        import requests
        import time
        
        try:
            # 设置代理
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 测试连接 - 使用目标网站进行测试
            test_url = "https://www.renqixiaoshuo.net"
            
            # 设置超时时间
            timeout = 10
            
            start_time = time.time()
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            end_time = time.time()
            
            if response.status_code == 200:
                logger.info(f"代理连接测试成功: {proxy_url} (响应时间: {end_time - start_time:.2f}s)")
                return True
            else:
                logger.error(f"代理连接测试失败: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectTimeout:
            logger.error(f"代理连接超时: {proxy_url}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"代理连接错误: {proxy_url}")
            return False
        except Exception as e:
            logger.error(f"代理测试异常: {e}")
            return False

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        table = self.query_one("#proxy-list-table", DataTable)
        
        if event.key == "escape":
            # ESC键返回
            self.app.pop_screen()
            event.stop()
        elif event.key in ["up", "down"]:
            # 上下键移动时更新选中状态
            if hasattr(table, 'cursor_row') and table.cursor_row is not None:
                row_index = table.cursor_row
                if 0 <= row_index < len(self.proxy_list):
                    self.selected_proxy_id = self.proxy_list[row_index].get("id")
                    logger.debug(f"键盘移动选中代理ID: {self.selected_proxy_id}")