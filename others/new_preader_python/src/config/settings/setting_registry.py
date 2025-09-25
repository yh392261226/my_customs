"""
设置项注册表
管理所有设置项的注册和访问
"""


from typing import Dict, List, Optional, Any
from .base_setting import BaseSetting
from .setting_section import SettingSection

from src.utils.logger import get_logger

logger = get_logger(__name__)

class SettingRegistry:
    """
    设置项注册表
    单例模式，管理所有设置项的注册和访问
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.settings: Dict[str, BaseSetting] = {}
        self.sections: Dict[str, SettingSection] = {}
        self._initialized = True
    
    def register_setting(self, setting: BaseSetting) -> bool:
        """
        注册设置项
        
        Args:
            setting: 要注册的设置项
            
        Returns:
            bool: 注册是否成功
        """
        if setting.key in self.settings:
            # logger.warning(f"Setting already registered: {setting.key}")
            return False
        
        self.settings[setting.key] = setting
        # logger.debug(f"Registered setting: {setting.key}")
        return True
    
    def register_section(self, section: SettingSection) -> bool:
        """
        注册设置项分组
        
        Args:
            section: 要注册的分组
            
        Returns:
            bool: 注册是否成功
        """
        if section.name in self.sections:
            # logger.warning(f"Section already registered: {section.name}")
            return False
        
        self.sections[section.name] = section
        
        # 注册分组中的所有设置项
        for setting in section.settings:
            self.register_setting(setting)
        
        # logger.debug(f"Registered section: {section.name}")
        return True
    
    def get_setting(self, key: str) -> Optional[BaseSetting]:
        """
        获取设置项
        
        Args:
            key: 设置项键名
            
        Returns:
            Optional[BaseSetting]: 设置项对象，如果不存在则返回None
        """
        return self.settings.get(key)
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取设置项的值
        
        Args:
            key: 设置项键名
            default: 默认值（如果设置项不存在）
            
        Returns:
            Any: 设置项的值
        """
        setting = self.get_setting(key)
        if setting is None:
            return default
        return setting.value
    
    def set_value(self, key: str, value: Any) -> bool:
        """
        设置设置项的值
        
        Args:
            key: 设置项键名
            value: 新值
            
        Returns:
            bool: 设置是否成功
        """
        setting = self.get_setting(key)
        if setting is None:
            logger.error(f"Setting not found: {key}")
            return False
        
        try:
            setting.value = value
            return True
        except ValueError as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    def get_all_settings(self) -> Dict[str, BaseSetting]:
        """
        获取所有设置项
        
        Returns:
            Dict[str, BaseSetting]: 所有设置项的字典
        """
        return self.settings.copy()
    
    def get_visible_settings(self) -> Dict[str, BaseSetting]:
        """
        获取所有可见的设置项
        
        Returns:
            Dict[str, BaseSetting]: 所有可见设置项的字典
        """
        return {k: v for k, v in self.settings.items() if not v.is_hidden}
    
    def get_settings_by_category(self, category: str) -> List[BaseSetting]:
        """
        按分类获取设置项
        
        Args:
            category: 分类名称
            
        Returns:
            List[BaseSetting]: 该分类下的设置项列表
        """
        return [s for s in self.settings.values() if s.category == category and not s.is_hidden]
    
    def get_all_categories(self) -> List[str]:
        """
        获取所有分类
        
        Returns:
            List[str]: 所有分类名称列表
        """
        categories = set()
        for setting in self.settings.values():
            if not setting.is_hidden:
                categories.add(setting.category)
        return sorted(list(categories))
    
    def get_section(self, name: str) -> Optional[SettingSection]:
        """
        获取设置项分组
        
        Args:
            name: 分组名称
            
        Returns:
            Optional[SettingSection]: 分组对象，如果不存在则返回None
        """
        return self.sections.get(name)
    
    def get_all_sections(self) -> Dict[str, SettingSection]:
        """
        获取所有分组
        
        Returns:
            Dict[str, SettingSection]: 所有分组的字典
        """
        return self.sections.copy()
    
    def reset_to_defaults(self, category: Optional[str] = None) -> int:
        """
        重置设置项为默认值
        
        Args:
            category: 可选，只重置指定分类的设置项
            
        Returns:
            int: 重置的设置项数量
        """
        count = 0
        for setting in self.settings.values():
            if category is None or setting.category == category:
                setting.reset_to_default()
                count += 1
        
        logger.info(f"Reset {count} settings to defaults")
        return count
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 所有设置项的字典表示
        """
        return {key: setting.to_dict() for key, setting in self.settings.items()}
    
    def from_dict(self, data: Dict[str, Any]) -> int:
        """
        从字典加载设置项
        
        Args:
            data: 设置项数据字典
            
        Returns:
            int: 成功加载的设置项数量
        """
        count = 0
        for key, setting_data in data.items():
            setting = self.get_setting(key)
            if setting and 'value' in setting_data:
                try:
                    setting.value = setting_data['value']
                    count += 1
                except ValueError as e:
                    logger.warning(f"Failed to load setting {key}: {e}")
        
        logger.info(f"Loaded {count} settings from dict")
        return count