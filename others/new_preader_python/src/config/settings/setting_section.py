"""
设置项分组
将相关的设置项组织在一起
"""

from typing import List, Optional, Dict, Any
from .base_setting import BaseSetting

class SettingSection:
    """
    设置项分组
    将相关的设置项组织在一起，便于管理和显示
    """
    
    def __init__(
        self,
        name: str,
        display_name: str,
        description: str = "",
        settings: Optional[List[BaseSetting]] = None,
        icon: str = "⚙️",
        order: int = 0
    ):
        """
        初始化设置项分组
        
        Args:
            name: 分组名称（唯一标识）
            display_name: 显示名称
            description: 描述信息
            settings: 包含的设置项列表
            icon: 分组图标
            order: 显示顺序（数字越小越靠前）
        """
        self.name = name
        self.display_name = display_name
        self.description = description
        self.settings = settings or []
        self.icon = icon
        self.order = order
    
    def add_setting(self, setting: BaseSetting) -> None:
        """
        添加设置项到分组
        
        Args:
            setting: 要添加的设置项
        """
        self.settings.append(setting)
    
    def remove_setting(self, setting_key: str) -> bool:
        """
        从分组中移除设置项
        
        Args:
            setting_key: 设置项键名
            
        Returns:
            bool: 移除是否成功
        """
        for i, setting in enumerate(self.settings):
            if setting.key == setting_key:
                self.settings.pop(i)
                return True
        return False
    
    def get_setting(self, key: str) -> Optional[BaseSetting]:
        """
        获取分组中的设置项
        
        Args:
            key: 设置项键名
            
        Returns:
            Optional[BaseSetting]: 设置项对象，如果不存在则返回None
        """
        for setting in self.settings:
            if setting.key == key:
                return setting
        return None
    
    def get_visible_settings(self) -> List[BaseSetting]:
        """
        获取分组中所有可见的设置项
        
        Returns:
            List[BaseSetting]: 可见设置项列表
        """
        return [s for s in self.settings if not s.is_hidden]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 分组的字典表示
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "settings_count": len(self.settings),
            "icon": self.icon,
            "order": self.order
        }
    
    def __str__(self) -> str:
        return f"SettingSection(name={self.name}, settings={len(self.settings)})"
    
    def __repr__(self) -> str:
        return str(self)