"""
配置管理器 - 负责阅读器配置的统一管理
提供配置的加载、保存和验证功能
"""

import os
import json

from typing import Dict, Any, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_dir: str = "~/.config/newreader"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = os.path.expanduser(config_dir)
        self.config_file = os.path.join(self.config_dir, "reader_config.json")
        self.default_config = self._get_default_config()
        self.current_config: Dict[str, Any] = {}
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 加载配置
        self.load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "reading": {
                "font_size": 14,
                "line_spacing": 1.5,
                "paragraph_spacing": 1.2,
                "auto_page_turn_interval": 30,
                "remember_position": True,
                "highlight_search": True,
                "margin_left": 2,
                "margin_right": 2,
            },
            "appearance": {
                "theme": "dark",
                "show_progress_bar": True,
                "show_status_bar": True,
                "show_shortcuts": True,
            },
            "behavior": {
                "auto_save_interval": 60,  # 自动保存间隔(秒)
                "max_bookmarks": 100,
                "max_search_history": 50,
            }
        }
    
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 合并配置，确保所有必要的键都存在
                self.current_config = self._merge_configs(self.default_config, loaded_config)
                logger.info("配置加载成功")
                return True
            else:
                # 使用默认配置
                self.current_config = self.default_config.copy()
                self.save_config()  # 保存默认配置
                logger.info("使用默认配置")
                return True
                
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.current_config = self.default_config.copy()
            return False
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_config, f, indent=2, ensure_ascii=False)
            
            logger.info("配置保存成功")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def _merge_configs(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并两个配置字典"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点分隔符 (如 "reading.font_size")
            default: 默认值
            
        Returns:
            Any: 配置值
        """
        try:
            keys = key.split('.')
            value = self.current_config
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
        except (KeyError, AttributeError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键，支持点分隔符
            value: 配置值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            keys = key.split('.')
            config = self.current_config
            
            # 遍历到最后一个键的父级
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 设置值
            config[keys[-1]] = value
            
            # 自动保存
            self.save_config()
            return True
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            return False
    
    def update(self, new_config: Dict[str, Any]) -> bool:
        """
        批量更新配置
        
        Args:
            new_config: 新配置字典
            
        Returns:
            bool: 是否更新成功
        """
        try:
            self.current_config = self._merge_configs(self.current_config, new_config)
            self.save_config()
            return True
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """重置为默认配置"""
        self.current_config = self.default_config.copy()
        return self.save_config()
    
    def validate_config(self) -> Dict[str, Any]:
        """
        验证配置的有效性
        
        Returns:
            Dict[str, Any]: 验证结果，包含错误信息
        """
        errors = {}
        
        # 验证字体大小
        font_size = self.get("reading.font_size")
        if not isinstance(font_size, int) or font_size < 8 or font_size > 32:
            errors["reading.font_size"] = "字体大小必须在8-32之间"
        

        # 验证行间距
        line_spacing = self.get("reading.line_spacing")
        if not isinstance(line_spacing, (int, float)) or line_spacing < 1.0 or line_spacing > 3.0:
            errors["reading.line_spacing"] = "行间距必须在1.0-3.0之间"
        
        return errors
    
    def get_reader_config(self) -> Dict[str, Any]:
        """
        获取阅读器专用的配置
        
        Returns:
            Dict[str, Any]: 阅读器配置
        """
        return {

            "font_size": self.get("reading.font_size", 14),
            "line_spacing": self.get("reading.line_spacing", 1.5),
            "paragraph_spacing": self.get("reading.paragraph_spacing", 1.2),
            "auto_page_turn_interval": self.get("reading.auto_page_turn_interval", 30),
            "remember_position": self.get("reading.remember_position", True),
            "chapters": []  # 这个由具体的书籍提供
        }

# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None

def get_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_dir: 配置目录路径，如果为None则使用默认路径
        
    Returns:
        ConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        # 如果config_dir为None，使用ConfigManager的默认值
        if config_dir is None:
            _config_manager = ConfigManager()
        else:
            _config_manager = ConfigManager(config_dir)
    return _config_manager