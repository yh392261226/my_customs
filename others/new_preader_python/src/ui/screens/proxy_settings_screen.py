"""
代理设置屏幕
"""

import asyncio
from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, Input, Select, Checkbox
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events
from pathlib import Path

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager

logger = get_logger(__name__)

class ProxySettingsScreen(Screen[None]):
    """代理设置屏幕"""
    
    # 加载CSS样式
    CSS_PATH = "../styles/proxy_settings_screen.css"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化代理设置屏幕
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        try:
            self.title = get_global_i18n().t('proxy_settings.title')
        except RuntimeError:
            # 如果全局i18n未初始化，使用默认标题
            self.title = "代理设置"
        self.theme_manager = theme_manager
        self.database_manager = DatabaseManager()
        self.proxy_settings = {
            "enabled": False,
            "type": "HTTP",
            "host": "127.0.0.1",
            "port": "7890",
            "username": "",
            "password": ""
        }
    
    def compose(self) -> ComposeResult:
        """
        组合代理设置屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        # 获取i18n文本，如果未初始化则使用默认值
        try:
            i18n = get_global_i18n()
            title = i18n.t('proxy_settings.title')
            description = i18n.t('proxy_settings.description')
            enable_proxy = i18n.t('proxy_settings.enable_proxy')
            proxy_type = i18n.t('proxy_settings.proxy_type')
            host = i18n.t('proxy_settings.host')
            host_placeholder = i18n.t('proxy_settings.host_placeholder')
            port = i18n.t('proxy_settings.port')
            port_placeholder = i18n.t('proxy_settings.port_placeholder')
            username = i18n.t('proxy_settings.username')
            username_placeholder = i18n.t('proxy_settings.username_placeholder')
            password = i18n.t('proxy_settings.password')
            password_placeholder = i18n.t('proxy_settings.password_placeholder')
            test_connection = i18n.t('proxy_settings.test_connection')
            save = i18n.t('proxy_settings.save')
            cancel = i18n.t('proxy_settings.cancel')
            shortcut_s = i18n.t('proxy_settings.shortcut_s')
            shortcut_t = i18n.t('proxy_settings.shortcut_t')
            shortcut_tab = i18n.t('proxy_settings.shortcut_tab')
            shortcut_esc = i18n.t('proxy_settings.shortcut_esc')
        except RuntimeError:
            # 使用默认值
            title = "代理设置"
            description = "配置网络代理服务器设置"
            enable_proxy = "启用代理"
            proxy_type = "代理类型"
            host = "主机"
            host_placeholder = "例如：proxy.example.com"
            port = "端口"
            port_placeholder = "例如：8080"
            username = "用户名"
            username_placeholder = "可选"
            password = "密码"
            password_placeholder = "可选"
            test_connection = "测试连接"
            save = "保存"
            cancel = "取消"
            shortcut_s = "S: 保存"
            shortcut_t = "T: 测试"
            shortcut_tab = "Tab: 切换焦点"
            shortcut_esc = "Esc: 返回"
        
        yield Container(
            Vertical(
                # 固定标题
                Label(title, id="proxy-settings-title"),
                Label(description, id="proxy-settings-description"),
                
                # 可滚动的内容区域
                ScrollableContainer(
                    Vertical(
                        # 代理启用开关
                        Horizontal(
                            Checkbox(enable_proxy, id="enable-proxy"),
                            id="proxy-enable-container"
                        ),
                        
                        # 代理类型选择
                        Horizontal(
                            Label(proxy_type, id="proxy-type-label"),
                            Select(
                                [
                                    ("HTTP", "HTTP"),
                                    ("HTTPS", "HTTPS"),
                                    ("SOCKS5", "SOCKS5")
                                ],
                                id="proxy-type-select"
                            ),
                            id="proxy-type-container"
                        ),
                        
                        # 代理服务器设置
                        Vertical(
                            Horizontal(
                                Label(host, id="host-label"),
                                Input(placeholder=host_placeholder, id="host-input"),
                                id="host-container"
                            ),
                            Horizontal(
                                Label(port, id="port-label"),
                                Input(placeholder=port_placeholder, id="port-input"),
                                id="port-container"
                            ),
                            id="server-settings-container"
                        ),
                        
                        # 认证设置
                        Vertical(
                            Horizontal(
                                Label(username, id="username-label"),
                                Input(placeholder=username_placeholder, id="username-input"),
                                id="username-container"
                            ),
                            Horizontal(
                                Label(password, id="password-label"),
                                Input(placeholder=password_placeholder, id="password-input", password=True),
                                id="password-container"
                            ),
                            id="auth-settings-container"
                        ),
                        
                        id="proxy-settings-scrollable-content"
                    ),
                    id="proxy-settings-scroll-container"
                ),
                
                # 状态信息（显示在容器外面，与按钮在同一区域）
                Label("", id="proxy-status-info"),
                
                # 固定底部按钮和快捷键栏
                Horizontal(
                    Button(test_connection, id="test-btn"),
                    Button(save, id="save-btn", variant="primary"),
                    Button(cancel, id="cancel-btn"),
                    id="proxy-settings-buttons"
                ),
                
                # 快捷键状态栏
                Horizontal(
                    Label(shortcut_s, id="shortcut-s"),
                    Label(shortcut_t, id="shortcut-t"),
                    Label(shortcut_tab, id="shortcut-tab"),
                    Label(shortcut_esc, id="shortcut-esc"),
                    id="shortcuts-bar"
                ),
                id="proxy-settings-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 加载代理设置
        self._load_proxy_settings()
        
        # 更新界面显示
        self._update_ui_from_settings()
        
        # 设置默认焦点到第一个输入框
        host_input = self.query_one("#host-input", Input)
        if host_input:
            self.set_focus(host_input)
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回
            self.app.pop_screen()
            event.prevent_default()
        elif event.key == "tab":
            # 处理Tab键焦点切换
            self._handle_tab_navigation(event)
        else:
            # 允许其他键盘事件正常传播到输入框
            pass
    
    def _handle_tab_navigation(self, event: events.Key) -> None:
        """处理Tab键导航"""
        # 获取当前焦点元素
        current_focus = self.focused
        
        # 定义焦点顺序
        focus_order = [
            "#enable-proxy",  # 启用代理复选框
            "#proxy-type-select",  # 代理类型选择
            "#host-input",  # 主机输入框
            "#port-input",  # 端口输入框
            "#username-input",  # 用户名输入框
            "#password-input",  # 密码输入框
            "#test-btn",  # 测试连接按钮
            "#save-btn",  # 保存按钮
            "#cancel-btn"  # 取消按钮
        ]
        
        # 查找当前焦点在顺序中的位置
        current_index = -1
        for i, selector in enumerate(focus_order):
            try:
                widget = self.query_one(selector)
                if widget == current_focus:
                    current_index = i
                    break
            except:
                continue
        
        # 计算下一个焦点位置
        if current_index >= 0:
            next_index = (current_index + 1) % len(focus_order)
        else:
            next_index = 0
        
        # 设置下一个焦点
        try:
            next_widget = self.query_one(focus_order[next_index])
            self.set_focus(next_widget)
            event.prevent_default()
        except:
            # 如果找不到下一个焦点元素，保持当前焦点
            pass
    
    def _load_proxy_settings(self) -> None:
        """从数据库加载代理设置"""
        # 这个屏幕已经被新的代理列表屏幕替代，不再使用
        self.proxy_settings = {}
    
    def _update_ui_from_settings(self) -> None:
        """根据设置更新界面"""
        # 更新复选框
        checkbox = self.query_one("#enable-proxy", Checkbox)
        checkbox.value = bool(self.proxy_settings["enabled"])
        
        # 更新代理类型选择
        type_select = self.query_one("#proxy-type-select", Select)
        type_select.value = str(self.proxy_settings["type"])
        
        # 更新输入框
        host_input = self.query_one("#host-input", Input)
        host_input.value = str(self.proxy_settings["host"])
        
        port_input = self.query_one("#port-input", Input)
        port_input.value = str(self.proxy_settings["port"])
        
        username_input = self.query_one("#username-input", Input)
        username_input.value = str(self.proxy_settings["username"])
        
        password_input = self.query_one("#password-input", Input)
        password_input.value = str(self.proxy_settings["password"])
    
    def _update_settings_from_ui(self) -> None:
        """从界面更新设置"""
        # 获取复选框状态
        checkbox = self.query_one("#enable-proxy", Checkbox)
        self.proxy_settings["enabled"] = bool(checkbox.value)
        
        # 获取代理类型
        type_select = self.query_one("#proxy-type-select", Select)
        if type_select.value:
            self.proxy_settings["type"] = str(type_select.value)
        
        # 获取输入框值
        host_input = self.query_one("#host-input", Input)
        self.proxy_settings["host"] = str(host_input.value)
        
        port_input = self.query_one("#port-input", Input)
        self.proxy_settings["port"] = str(port_input.value)
        
        username_input = self.query_one("#username-input", Input)
        self.proxy_settings["username"] = str(username_input.value)
        
        password_input = self.query_one("#password-input", Input)
        self.proxy_settings["password"] = str(password_input.value)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "test-btn":
            self._test_connection()
        elif event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()  # 返回上一页
    
    def _test_connection(self) -> None:
        """测试代理连接"""
        self._update_settings_from_ui()
        
        if not self.proxy_settings["enabled"]:
            try:
                self._update_status(get_global_i18n().t('proxy_settings.proxy_disabled'))
            except RuntimeError:
                self._update_status("代理未启用")
            return
        
        # 验证必填字段
        if not self.proxy_settings["host"] or not self.proxy_settings["port"]:
            try:
                self._update_status(get_global_i18n().t('proxy_settings.fill_required_fields'))
            except RuntimeError:
                self._update_status("请填写必填字段")
            return
        
        # TODO: 实现代理连接测试
        # 这里应该使用实际的网络请求来测试代理连接
        try:
            self._update_status(get_global_i18n().t('proxy_settings.testing_connection'))
        except RuntimeError:
            self._update_status("正在测试连接...")
        
        # 模拟测试结果
        import time
        time.sleep(1)  # 模拟网络延迟
        
        # 随机返回成功或失败（实际实现中应该进行真实的网络测试）
        import random
        if random.random() > 0.3:  # 70%成功率
            try:
                self._update_status(get_global_i18n().t('proxy_settings.connection_success'), "success")
            except RuntimeError:
                self._update_status("连接成功", "success")
        else:
            try:
                self._update_status(get_global_i18n().t('proxy_settings.connection_failed'), "error")
            except RuntimeError:
                self._update_status("连接失败", "error")
    
    def _save_settings(self) -> None:
        """保存代理设置到数据库"""
        self._update_settings_from_ui()
        
        try:
            # 保存到数据库
            success = self.database_manager.save_proxy_settings(self.proxy_settings)
            
            if success:
                try:
                    self._update_status(get_global_i18n().t('proxy_settings.saved_success'), "success")
                except RuntimeError:
                    self._update_status("保存成功", "success")
                
                # 通知其他屏幕代理设置已更新
                self._notify_proxy_settings_changed()
                
                # 延迟返回上一页
                asyncio.create_task(self._delayed_pop())
            else:
                try:
                    self._update_status(get_global_i18n().t('proxy_settings.save_failed'), "error")
                except RuntimeError:
                    self._update_status("保存失败", "error")
            
        except Exception as e:
            try:
                self._update_status(f"{get_global_i18n().t('proxy_settings.save_failed')}: {str(e)}", "error")
            except RuntimeError:
                self._update_status(f"保存失败: {str(e)}", "error")
    
    def _notify_proxy_settings_changed(self) -> None:
        """通知其他屏幕代理设置已更新"""
        # 这里可以发送消息或事件来通知其他屏幕更新
        # 由于Textual的事件系统比较复杂，我们依赖on_screen_resume来更新
        pass
    
    async def _delayed_pop(self) -> None:
        """延迟返回上一页"""
        await asyncio.sleep(1)  # 等待1秒显示成功消息
        self.app.pop_screen()
    
    def _update_status(self, message: str, severity: str = "information") -> None:
        """更新状态信息"""
        status_label = self.query_one("#proxy-status-info", Label)
        status_label.update(message)
        
        # 根据严重程度设置样式
        if severity == "success":
            status_label.styles.color = "green"
        elif severity == "error":
            status_label.styles.color = "red"
        else:
            status_label.styles.color = "blue"
    
    def key_s(self) -> None:
        """S键 - 保存设置"""
        self._save_settings()
    
    def key_t(self) -> None:
        """T键 - 测试连接"""
        self._test_connection()
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回
            self.app.pop_screen()
            event.prevent_default()
        elif event.key == "tab":
            # 处理Tab键焦点切换
            self._handle_tab_navigation(event)
        else:
            # 允许其他键盘事件正常传播到输入框
            pass
    
    def _handle_tab_navigation(self, event: events.Key) -> None:
        """处理Tab键导航"""
        # 获取当前焦点元素
        current_focus = self.focused
        
        # 定义焦点顺序
        focus_order = [
            "#enable-proxy",  # 启用代理复选框
            "#proxy-type-select",  # 代理类型选择
            "#host-input",  # 主机输入框
            "#port-input",  # 端口输入框
            "#username-input",  # 用户名输入框
            "#password-input",  # 密码输入框
            "#test-btn",  # 测试连接按钮
            "#save-btn",  # 保存按钮
            "#cancel-btn"  # 取消按钮
        ]
        
        # 查找当前焦点在顺序中的位置
        current_index = -1
        for i, selector in enumerate(focus_order):
            try:
                widget = self.query_one(selector)
                if widget == current_focus:
                    current_index = i
                    break
            except:
                continue
        
        # 计算下一个焦点位置
        if current_index >= 0:
            next_index = (current_index + 1) % len(focus_order)
        else:
            next_index = 0
        
        # 设置下一个焦点
        try:
            next_widget = self.query_one(focus_order[next_index])
            self.set_focus(next_widget)
            event.prevent_default()
        except:
            # 如果找不到下一个焦点元素，保持当前焦点
            pass
    
    