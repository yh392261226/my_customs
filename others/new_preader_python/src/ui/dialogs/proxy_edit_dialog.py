"""
代理编辑对话框
用于添加和编辑代理设置
"""

from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, Input, Select, Switch
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

logger = get_logger(__name__)

class ProxyEditDialog(ModalScreen[Optional[Dict[str, Any]]]):
    """代理编辑对话框"""
    
    # 加载CSS样式
    CSS_PATH = "../styles/proxy_edit_dialog_overrides.tcss"

    # 使用 BINDINGS：Esc 取消
    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, proxy_data: Optional[Dict[str, Any]] = None):
        """
        初始化代理编辑对话框
        
        Args:
            theme_manager: 主题管理器
            proxy_data: 代理数据，如果为None则表示添加新代理
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.proxy_data = proxy_data or {}
        self.is_editing = proxy_data is not None
    
    def compose(self) -> ComposeResult:
        """
        组合代理编辑对话框界面
        
        Returns:
            ComposeResult: 组合结果
        """
        # 获取i18n文本，如果未初始化则使用默认值
        try:
            i18n = get_global_i18n()
            title = i18n.t('proxy_settings.title')
            name_label = i18n.t('proxy_settings.name')
            name_placeholder = i18n.t('proxy_settings.name_placeholder')
            enable_label = i18n.t('proxy_settings.enable_proxy')
            type_label = i18n.t('proxy_settings.proxy_type')
            host_label = i18n.t('proxy_settings.host')
            host_placeholder = i18n.t('proxy_settings.host_placeholder')
            port_label = i18n.t('proxy_settings.port')
            port_placeholder = i18n.t('proxy_settings.port_placeholder')
            username_label = i18n.t('proxy_settings.username')
            username_placeholder = i18n.t('proxy_settings.username_placeholder')
            password_label = i18n.t('proxy_settings.password')
            password_placeholder = i18n.t('proxy_settings.password_placeholder')
            test_connection = i18n.t('proxy_settings.test_connection')
            save_btn = i18n.t('proxy_settings.save')
            cancel_btn = i18n.t('proxy_settings.cancel')
        except RuntimeError:
            # 使用默认值
            title = "编辑代理" if self.is_editing else "添加代理"
            name_label = "名称"
            name_placeholder = "输入代理名称"
            enable_label = "启用"
            type_label = "类型"
            host_label = "主机"
            host_placeholder = "例如：proxy.example.com"
            port_label = "端口"
            port_placeholder = "例如：8080"
            username_label = "用户名"
            username_placeholder = "可选"
            password_label = "密码"
            password_placeholder = "可选"
            test_connection = "测试连接"
            save_btn = "保存"
            cancel_btn = "取消"
        
        with Vertical(id="proxy-edit-container", classes="panel"):
            # 标题在边框外
            yield Label(title, id="proxy-edit-title", classes="section-title")
            
            # 可滚动的表单内容区域
            with ScrollableContainer(id="proxy-edit-scroll"):
                with Vertical(id="proxy-edit-form"):
                    # 基础设置
                    with Vertical(id="basic-container"):
                        # 代理名称
                        with Horizontal(id="name-container", classes="form-row center-h"):
                            yield Label(name_label, id="name-label", classes="label-right")
                            yield Input(
                                placeholder=name_placeholder,
                                id="name-input",
                                value=self.proxy_data.get("name", ""),
                                classes="input-std"
                            )
                        
                        # 代理类型
                        with Horizontal(id="type-container", classes="form-row center-h"):
                            yield Label(type_label, id="type-label", classes="label-right")
                            yield Select(
                                [
                                    ("HTTP", "HTTP"),
                                    ("HTTPS", "HTTPS"),
                                    ("SOCKS5", "SOCKS5")
                                ],
                                id="type-select",
                                value=self.proxy_data.get("type", "HTTP"),
                                classes="select-std"
                            )
                    
                    # 启用开关
                    with Vertical(id="enable-container"):
                        with Horizontal(id="enable-container-inside", classes="form-row center-h"):
                            yield Label(enable_label, id="enable-label", classes="label-right")
                            yield Switch(
                                id="enable-checkbox",
                                value=self.proxy_data.get("enabled", 0),
                                classes="switch-std"
                            )

                    # 服务器设置
                    with Vertical(id="server-container"):
                        with Horizontal(id="host-container", classes="form-row center-h"):
                            yield Label(host_label, id="host-label", classes="label-right")
                            yield Input(
                                placeholder=host_placeholder,
                                id="host-input",
                                value=self.proxy_data.get("host", ""),
                                classes="input-std"
                            )
                        with Horizontal(id="port-container", classes="form-row center-h"):
                            yield Label(port_label, id="port-label", classes="label-right")
                            yield Input(
                                placeholder=port_placeholder,
                                id="port-input",
                                value=self.proxy_data.get("port", ""),
                                classes="input-std"
                            )
                    
                    # 认证设置
                    with Vertical(id="auth-container"):
                        with Horizontal(id="username-container", classes="form-row center-h"):
                            yield Label(username_label, id="username-label", classes="label-right")
                            yield Input(
                                placeholder=username_placeholder,
                                id="username-input",
                                value=self.proxy_data.get("username", ""),
                                classes="input-std"
                            )
                        with Horizontal(id="password-container", classes="form-row center-h"):
                            yield Label(password_label, id="password-label", classes="label-right")
                            yield Input(
                                placeholder=password_placeholder,
                                id="password-input",
                                password=True,
                                value=self.proxy_data.get("password", ""),
                                classes="input-std"
                            )
            
            # 状态信息显示区域
            yield Label("", id="proxy-status-info")
            
            # 按钮区域在边框外
            with Horizontal(id="proxy-edit-buttons", classes="btn-row"):
                yield Button(test_connection, id="test-btn")
                yield Button(save_btn, id="save-btn", variant="primary")
                yield Button(cancel_btn, id="cancel-btn")
    
    def on_mount(self) -> None:
        """对话框挂载时的回调"""
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 设置启用复选框状态
        enable_checkbox = self.query_one("#enable-checkbox", Switch)
        enable_checkbox.value = bool(self.proxy_data.get("enabled", False))
        
        # 设置默认焦点到名称输入框
        name_input = self.query_one("#name-input", Input)
        if name_input:
            self.set_focus(name_input)
    
    # Actions for BINDINGS
    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "test-btn":
            self._test_connection()
        elif event.button.id == "save-btn":
            self._save_proxy()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
    
    def _save_proxy(self) -> None:
        """保存代理设置"""
        # 获取表单数据
        name_input = self.query_one("#name-input", Input)
        enable_checkbox = self.query_one("#enable-checkbox", Switch)
        type_select = self.query_one("#type-select", Select)
        host_input = self.query_one("#host-input", Input)
        port_input = self.query_one("#port-input", Input)
        username_input = self.query_one("#username-input", Input)
        password_input = self.query_one("#password-input", Input)
        
        # 验证必填字段
        if not name_input.value.strip():
            self._show_error("请输入代理名称")
            return
        
        if not host_input.value.strip():
            self._show_error("请输入主机地址")
            return
        
        if not port_input.value.strip():
            self._show_error("请输入端口号")
            return
        
        # 验证端口号格式
        try:
            port = int(port_input.value)
            if port < 1 or port > 65535:
                self._show_error("端口号必须在1-65535之间")
                return
        except ValueError:
            self._show_error("端口号必须是数字")
            return
        
        # 构建代理数据
        proxy_data = {
            "name": name_input.value.strip(),
            "enabled": bool(enable_checkbox.value),
            "type": type_select.value if type_select.value else "HTTP",
            "host": host_input.value.strip(),
            "port": port_input.value.strip(),
            "username": username_input.value.strip(),
            "password": password_input.value
        }
        
        # 关闭对话框并返回数据
        self.dismiss(proxy_data)
    
    def _test_connection(self) -> None:
        """测试代理连接"""
        # 获取当前表单数据
        host_input = self.query_one("#host-input", Input)
        port_input = self.query_one("#port-input", Input)
        type_select = self.query_one("#type-select", Select)
        username_input = self.query_one("#username-input", Input)
        password_input = self.query_one("#password-input", Input)
        
        # 验证必填字段
        if not host_input.value.strip():
            self._show_message("请输入主机地址", "error")
            return
        
        if not port_input.value.strip():
            self._show_message("请输入端口号", "error")
            return
        
        # 验证端口号格式
        try:
            port = int(port_input.value)
            if port < 1 or port > 65535:
                self._show_message("端口号必须在1-65535之间", "error")
                return
        except ValueError:
            self._show_message("端口号必须是数字", "error")
            return
        
        # 显示测试中状态
        self._show_message("正在测试连接...", "info")
        
        # 构建代理URL
        proxy_type = type_select.value if type_select.value else "HTTP"
        host = host_input.value.strip()
        port = port_input.value.strip()
        username = username_input.value.strip()
        password = password_input.value
        
        if username and password:
            proxy_url = f"{proxy_type.lower()}://{username}:{password}@{host}:{port}"
        else:
            proxy_url = f"{proxy_type.lower()}://{host}:{port}"
        
        # 执行真实的代理连接测试
        test_result = self._real_test_proxy_connection(proxy_url)
        
        if test_result:
            self._show_message("连接测试成功", "success")
        else:
            self._show_message("连接测试失败，请检查代理设置", "error")
    
    def _show_message(self, message: str, message_type: str = "info") -> None:
        """显示消息"""
        try:
            status_label = self.query_one("#proxy-status-info", Label)
            status_label.update(message)
            
            # 根据消息类型设置样式
            if message_type == "success":
                status_label.styles.color = "green"
            elif message_type == "error":
                status_label.styles.color = "red"
            else:
                status_label.styles.color = "blue"
        except:
            # 如果找不到状态标签，使用日志记录
            if message_type == "error":
                logger.error(message)
            elif message_type == "success":
                logger.info(f"SUCCESS: {message}")
            else:
                logger.info(message)
    
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

    def _show_error(self, message: str) -> None:
        """显示错误消息"""
        self._show_message(message, "error")
    
    def on_key(self, event: events.Key) -> None:
        """已由 BINDINGS 处理，避免重复触发"""
        pass