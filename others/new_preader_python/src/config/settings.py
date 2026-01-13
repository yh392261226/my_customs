"""
NewReader 配置管理器
处理应用程序的各种配置选项
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import configparser

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config_data: Dict[str, Any] = {}
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        home_dir = Path.home()
        config_dir = home_dir / ".config" / "newreader"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "config.json")
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                self.config_data = self._get_default_config()
        else:
            # 配置文件不存在，使用默认配置
            self.config_data = self._get_default_config()
            self.save_config()  # 创建默认配置文件
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "appearance": {
                "theme": "dark",
                "font_size": 14,
                "line_spacing": 1.2,
                "window_width": 80,
                "window_height": 24
            },
            "reading": {
                "auto_page_turn": False,
                "auto_page_interval": 30,
                "remember_position": True,
                "highlight_search": True
            },
            "behavior": {
                "confirm_exit": True,
                "check_updates": True,
                "enable_animations": True
            },
            "advanced": {
                "cache_size": 100,
                "max_recent_books": 10,
                "enable_logging": True
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置数据"""
        return self.config_data.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键（如 "appearance.theme"）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
            
        Returns:
            是否设置成功
        """
        keys = key.split('.')
        config_ref = self.config_data
        
        # 导航到目标嵌套字典
        for k in keys[:-1]:
            if k not in config_ref or not isinstance(config_ref[k], dict):
                config_ref[k] = {}
            config_ref = config_ref[k]
        
        # 设置最终值
        config_ref[keys[-1]] = value
        return True
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """重置为默认配置"""
        self.config_data = self._get_default_config()
        return self.save_config()


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    config_manager = get_config_manager()
    return config_manager.get(key, default)


def set_config_value(key: str, value: Any) -> bool:
    """设置配置值的便捷函数"""
    config_manager = get_config_manager()
    return config_manager.set(key, value)