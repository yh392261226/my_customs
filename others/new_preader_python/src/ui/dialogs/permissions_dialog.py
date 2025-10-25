"""
权限管理对话框
用于管理用户权限
"""

from typing import Optional, Set, List, Dict, Any
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Label, Checkbox, Static
from textual.app import ComposeResult
from textual import events

from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation
from src.core.database_manager import DatabaseManager

logger = get_logger(__name__)

class PermissionsDialog(ModalScreen[Optional[Set[str]]]):
    """权限管理对话框"""
    
    CSS_PATH = "../styles/permissions_dialog_overrides.tcss"
    
    BINDINGS = [
        ("enter", "confirm", get_global_i18n().t('common.confirm')),
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, user_id: int, username: str, all_permissions: List[str], user_permissions: Set[str], read_only: bool = False):
        """
        初始化权限管理对话框
        
        Args:
            theme_manager: 主题管理器
            user_id: 用户ID
            username: 用户名
            all_permissions: 所有可用权限列表
            user_permissions: 用户当前拥有的权限集合
            read_only: 是否只读模式（用于查看权限）
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.user_id = user_id
        self.username = username
        self.all_permissions = all_permissions
        self.user_permissions = user_permissions
        self.read_only = read_only
        self.checkboxes = {}  # 存储权限键到复选框的映射
        self.db_manager = DatabaseManager()  # 数据库管理器
        self.permissions_data = {}  # 存储权限的完整信息（key -> description）
        
        # 从数据库获取权限的完整信息
        self._load_permissions_data()
    
    def _load_permissions_data(self) -> None:
        """从数据库加载权限的完整信息"""
        try:
            permissions = self.db_manager.get_all_permissions()
            for perm in permissions:
                self.permissions_data[perm['key']] = perm['description']
        except Exception as e:
            logger.error(f"加载权限数据失败: {e}")
            # 如果加载失败，使用key作为fallback
            for perm_key in self.all_permissions:
                self.permissions_data[perm_key] = perm_key
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        i18n = get_global_i18n()
        
        # 根据模式设置标题
        if self.read_only:
            title = i18n.t("users_management.permissions_dialog.view_title", 
                          user_id=self.user_id, username=self.username)
        else:
            title = i18n.t("users_management.permissions_dialog.title", 
                          user_id=self.user_id, username=self.username)
        
        # 构建对话框内容
        dialog_content = [
            # 标题
            Label(
                title,
                id="permissions-title",
                classes="section-title"
            ),
            
            # 权限列表容器
            Vertical(
                *self._create_permission_checkboxes(),
                id="permissions-list",
                classes="scrollable-container"
            ),
            
            # 状态信息
            Label("", id="permissions-status"),
        ]
        
        # 添加按钮区域
        if not self.read_only:
            # 编辑模式：显示操作按钮
            dialog_content.append(
                Horizontal(
                    Button(i18n.t("users_management.select_all"), id="select-all-btn", classes="permissions_dialog_button"),
                    Button(i18n.t("users_management.deselect_all"), id="deselect-all-btn", classes="permissions_dialog_button"),
                    Button(i18n.t("users_management.invert_selection"), id="invert-selection-btn", classes="permissions_dialog_button"),
                    Button(i18n.t("common.confirm"), id="confirm-btn", variant="primary", classes="permissions_dialog_button"),
                    Button(i18n.t("common.cancel"), id="cancel-btn", classes="permissions_dialog_button"),
                    id="permissions-buttons-top",
                    classes="btn-row"
                )
            )
        else:
            # 只读模式：显示关闭按钮
            dialog_content.append(
                Horizontal(
                    Button(i18n.t("common.close"), id="close-btn", variant="primary", classes="permissions_dialog_button"),
                    id="permissions-buttons-readonly",
                    classes="btn-row"
                )
            )
        
        yield Container(
            Vertical(*dialog_content, id="permissions-container")
        )
    
    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 更新状态信息
        self._update_status()
        
        # 设置默认焦点
        if self.read_only:
            # 只读模式：焦点到关闭按钮
            close_btn = self.query_one("#close-btn", Button)
            if close_btn:
                self.set_focus(close_btn)
        else:
            # 编辑模式：焦点到确认按钮
            confirm_btn = self.query_one("#confirm-btn", Button)
            if confirm_btn:
                self.set_focus(confirm_btn)
    
    def _create_permission_checkboxes(self) -> List[Checkbox]:
        """创建权限复选框列表"""
        checkboxes = []
        for permission_key in sorted(self.all_permissions):
            checked = permission_key in self.user_permissions
            # 获取权限的描述信息（中文显示），如果没有则使用key作为fallback
            description = self.permissions_data.get(permission_key, permission_key)

            # 根据当前语言选择显示字段：中文 -> description；英文 -> key
            i18n = get_global_i18n()
            locale = None
            try:
                # 优先尝试属性
                locale = getattr(i18n, "current_locale", None)
                # 其次尝试方法
                if not locale and hasattr(i18n, "get_current_locale"):
                    locale = i18n.get_current_locale()
            except Exception:
                locale = None

            is_chinese = False
            if isinstance(locale, str):
                low = locale.lower()
                is_chinese = ("zh" in low) or (low in ("zh_cn", "zh-cn", "zh_hans", "zh-hans"))

            label_text = description if is_chinese else permission_key

            checkbox = Checkbox(
                label=label_text,
                value=checked,
                id=f"perm-{permission_key.replace('.', '-').replace(':', '-')}",
                classes="checkbox",
                disabled=self.read_only  # 只读模式下禁用复选框
            )
            self.checkboxes[permission_key] = checkbox  # 存储key到复选框的映射
            checkboxes.append(checkbox)
        return checkboxes
    
    def _update_status(self) -> None:
        """更新状态信息"""
        i18n = get_global_i18n()
        selected_count = len([cb for cb in self.checkboxes.values() if cb.value])
        total_count = len(self.all_permissions)
        
        status_label = self.query_one("#permissions-status", Label)
        status_label.update(
            i18n.t("users_management.permissions_dialog.status", 
                  selected=selected_count, total=total_count)
        )
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """复选框状态改变时的回调"""
        self._update_status()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "confirm-btn":
            # 收集选中的权限
            selected_permissions = {
                permission for permission, checkbox in self.checkboxes.items() 
                if checkbox.value
            }
            self.dismiss(selected_permissions)
            
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
            
        elif event.button.id == "close-btn":
            # 只读模式下的关闭按钮
            self.dismiss(None)
            
        elif event.button.id == "select-all-btn":
            # 全选
            for checkbox in self.checkboxes.values():
                checkbox.value = True
            self._update_status()
            
        elif event.button.id == "deselect-all-btn":
            # 全不选
            for checkbox in self.checkboxes.values():
                checkbox.value = False
            self._update_status()
            
        elif event.button.id == "invert-selection-btn":
            # 反选
            for checkbox in self.checkboxes.values():
                checkbox.value = not checkbox.value
            self._update_status()
    
    def action_confirm(self) -> None:
        """确认操作"""
        selected_permissions = {
            permission for permission, checkbox in self.checkboxes.items() 
            if checkbox.value
        }
        self.dismiss(selected_permissions)
    
    def action_cancel(self) -> None:
        """取消操作"""
        self.dismiss(None)