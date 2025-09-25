"""
配置适配器
连接新的设置系统和现有的配置管理器
"""


from typing import Dict, Any, Optional
from .setting_registry import SettingRegistry
from .setting_observer import notify_setting_change

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ConfigAdapter:
    """
    配置适配器
    在新设置系统和现有配置管理器之间提供桥梁
    """
    
    def __init__(self, config_manager, setting_registry: SettingRegistry):
        """
        初始化配置适配器
        
        Args:
            config_manager: 现有的配置管理器实例
            setting_registry: 设置项注册表实例
        """
        self.config_manager = config_manager
        self.setting_registry = setting_registry
    
    def load_config_to_settings(self) -> int:
        """
        从现有配置加载值到设置项
        
        Returns:
            int: 成功加载的设置项数量
        """
        config = self.config_manager.get_config()
        count = 0
        
        for key, value in self._flatten_config(config).items():
            setting = self.setting_registry.get_setting(key)
            if setting:
                try:
                    old_value = setting.value
                    setting.value = value
                    count += 1
                    # 通知配置加载的变更
                    if old_value != setting.value:
                        notify_setting_change(key, old_value, setting.value, "config")
                except ValueError as e:
                    logger.warning(f"Failed to load setting {key}: {e}")
        
        logger.info(f"Loaded {count} settings from config")
        return count
    
    def save_settings_to_config(self) -> bool:
        """
        将设置项的值保存到现有配置
        
        Returns:
            bool: 保存是否成功
        """
        config = self.config_manager.get_config().copy()
        
        # 更新配置值
        for setting in self.setting_registry.get_all_settings().values():
            self._set_nested_config(config, setting.key, setting.value)
        
        # 保存配置
        return self.config_manager.save_config(config)
    
    def sync_to_config(self) -> bool:
        """同步设置项到配置（加载+保存）"""
        self.load_config_to_settings()
        return self.save_settings_to_config()
    
    def sync_from_config(self) -> bool:
        """从配置同步到设置项"""
        return self.load_config_to_settings() > 0
    
    def _flatten_config(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        扁平化嵌套配置
        
        Args:
            config: 嵌套配置字典
            prefix: 键名前缀
            
        Returns:
            Dict[str, Any]: 扁平化的配置字典
        """
        flat_config = {}
        
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # 递归处理嵌套字典
                flat_config.update(self._flatten_config(value, full_key))
            else:
                flat_config[full_key] = value
        
        return flat_config
    
    def _set_nested_config(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """
        在嵌套配置中设置值
        
        Args:
            config: 配置字典
            key: 点分隔的键名（如 "appearance.theme"）
            value: 要设置的值
        """
        keys = key.split('.')
        current = config
        
        # 遍历到最后一个键
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 设置最终值
        current[keys[-1]] = value
    
    def get_setting_value(self, key: str, default: Any = None) -> Any:
        """
        获取设置项的值
        
        Args:
            key: 设置项键名
            default: 默认值
            
        Returns:
            Any: 设置项的值
        """
        return self.setting_registry.get_value(key, default)
    
    def set_setting_value(self, key: str, value: Any) -> bool:
        """
        设置设置项的值
        
        Args:
            key: 设置项键名
            value: 新值
            
        Returns:
            bool: 设置是否成功
        """
        return self.setting_registry.set_value(key, value)
    
    def reset_settings_to_defaults(self, category: Optional[str] = None) -> int:
        """
        重置设置项为默认值
        
        Args:
            category: 可选，只重置指定分类的设置项
            
        Returns:
            int: 重置的设置项数量
        """
        count = self.setting_registry.reset_to_defaults(category)
        
        # 同步到配置
        if count > 0:
            self.save_settings_to_config()
        
        return count