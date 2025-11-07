"""
多用户管理工具类
用于检查多用户设置状态和权限管理
"""

from typing import Optional
from src.config.config_manager import ConfigManager


class MultiUserManager:
    """多用户管理器"""
    
    @staticmethod
    def is_multi_user_enabled() -> bool:
        """
        检查是否启用了多用户功能
        
        Returns:
            bool: 如果启用了多用户功能返回True，否则返回False
        """
        try:
            config_manager = ConfigManager.get_instance()
            config = config_manager.get_config()
            multi_user_enabled = config.get("advanced", {}).get("multi_user_enabled", False)
            return bool(multi_user_enabled)
        except Exception:
            # 如果出现异常，默认禁用多用户功能
            return False
    
    @staticmethod
    def is_super_admin_mode() -> bool:
        """
        检查是否处于超级管理员模式（多用户禁用时）
        
        Returns:
            bool: 如果多用户禁用，返回True（超级管理员模式）
        """
        return not MultiUserManager.is_multi_user_enabled()
    
    @staticmethod
    def should_show_user_management() -> bool:
        """
        检查是否应该显示用户管理功能
        
        Returns:
            bool: 如果应该显示用户管理功能返回True
        """
        return MultiUserManager.is_multi_user_enabled()
    
    @staticmethod
    def should_show_login() -> bool:
        """
        检查是否应该显示登录界面
        
        Returns:
            bool: 如果应该显示登录界面返回True
        """
        return MultiUserManager.is_multi_user_enabled()
    
    @staticmethod
    def should_show_permissions() -> bool:
        """
        检查是否应该显示权限管理功能
        
        Returns:
            bool: 如果应该显示权限管理功能返回True
        """
        return MultiUserManager.is_multi_user_enabled()
    
    @staticmethod
    def get_current_user_permissions() -> list[str]:
        """
        获取当前用户的权限列表
        
        Returns:
            list[str]: 权限列表，如果多用户禁用则返回所有权限
        """
        if MultiUserManager.is_super_admin_mode():
            # 超级管理员模式，返回所有权限
            return ["read", "write", "delete", "manage_users", "manage_books", "manage_settings"]
        
        # TODO: 在多用户模式下，从当前登录用户获取权限
        # 这里需要根据实际的用户认证系统来实现
        return ["read"]  # 默认只读权限
    
    @staticmethod
    def get_current_user() -> Optional[dict]:
        """
        获取当前登录用户信息
        
        Returns:
            Optional[dict]: 用户信息字典，包含id和role字段，如果多用户禁用则返回超级管理员信息
        """
        if MultiUserManager.is_super_admin_mode():
            # 超级管理员模式，返回超级管理员信息
            return {"id": 1, "role": "super_admin"}
        
        # 在多用户模式下，从全局应用状态获取当前用户信息
        try:
            # 尝试从应用实例获取当前用户信息
            import src.ui.app as app_module
            if hasattr(app_module, 'app_instance') and hasattr(app_module.app_instance, 'current_user'):
                return app_module.app_instance.current_user
            # 如果无法获取，返回默认用户信息（需要实际实现用户会话管理）
            return {"id": 0, "role": "user"}
        except Exception:
            # 如果出现异常，返回默认用户信息
            return {"id": 0, "role": "user"}
    
    @staticmethod
    def has_permission(permission: str) -> bool:
        """
        检查当前用户是否具有指定权限
        
        Args:
            permission: 权限名称
            
        Returns:
            bool: 如果具有权限返回True
        """
        if MultiUserManager.is_super_admin_mode():
            # 超级管理员模式，拥有所有权限
            return True
        
        user_permissions = MultiUserManager.get_current_user_permissions()
        return permission in user_permissions


# 创建全局实例
multi_user_manager = MultiUserManager()