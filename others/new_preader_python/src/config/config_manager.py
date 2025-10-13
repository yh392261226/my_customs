"""
配置管理器，负责加载、保存和管理应用程序配置
"""

import os
import json

from pathlib import Path
from typing import Dict, Any, Optional

from src.config.default_config import DEFAULT_CONFIG

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ConfigManager:
    """配置管理器类，负责处理应用程序配置"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，如果为None则使用默认目录
        """
        if config_dir is None:
            # 默认配置目录为用户主目录下的.config/new_preader文件夹
            self.config_dir = os.path.join(str(Path.home()), ".config", "new_preader")
        else:
            self.config_dir = config_dir
            
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件，如果不存在则创建默认配置
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    
                # 合并用户配置和默认配置，确保所有必要的配置项都存在
                config = self._merge_configs(DEFAULT_CONFIG, user_config)
                logger.info("配置已从文件加载")
                return config
            else:
                # 如果配置文件不存在，则创建默认配置
                self.save_config(DEFAULT_CONFIG)
                logger.info("已创建默认配置文件")
                return DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error(f"加载配置时出错: {e}")
            logger.info("使用默认配置")
            return DEFAULT_CONFIG.copy()
    
    def _merge_configs(self, default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归合并两个配置字典，确保所有默认配置项都存在
        
        Args:
            default_config: 默认配置字典
            user_config: 用户配置字典
            
        Returns:
            Dict[str, Any]: 合并后的配置字典
        """
        result = default_config.copy()
        
        for key, value in user_config.items():
            # 如果用户配置中的值是字典，且默认配置中也有这个键
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                # 递归合并子字典
                result[key] = self._merge_configs(result[key], value)
            else:
                # 否则直接使用用户配置的值
                result[key] = value
                
        return result
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置，如果为None则保存当前配置
            
        Returns:
            bool: 保存是否成功
        """
        if config is None:
            config = self.config
            
        try:
            # 统一同步语言：若配置中存在 advanced.language，则更新全局 i18n
            try:
                from src.locales.i18n_manager import get_global_i18n
                adv = (config or {}).get("advanced", {}) if isinstance(config, dict) else {}
                lang = adv.get("language")
                if isinstance(lang, str) and lang:
                    try:
                        get_global_i18n().set_locale(lang)
                    except Exception:
                        pass
            except Exception:
                pass
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info("配置已保存到文件")
            return True
        except Exception as e:
            logger.error(f"保存配置时出错: {e}")
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict[str, Any]: 当前配置字典
        """
        return self.config
    
    def update_config(self, section: str, key: str, value: Any) -> bool:
        """
        更新配置中的特定项
        
        Args:
            section: 配置部分名称
            key: 配置项名称
            value: 新的配置值
            
        Returns:
            bool: 更新是否成功
        """
        try:
            if section in self.config and key in self.config[section]:
                self.config[section][key] = value
                # 若更新的是语言设置，先同步到全局 i18n
                try:
                    if section == "advanced" and key == "language" and isinstance(value, str) and value:
                        from src.locales.i18n_manager import get_global_i18n
                        try:
                            get_global_i18n().set_locale(value)
                        except Exception:
                            pass
                except Exception:
                    pass
                return self.save_config()
            else:
                logger.error(f"配置项 {section}.{key} 不存在")
                return False
        except Exception as e:
            logger.error(f"更新配置时出错: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """
        重置配置为默认值
        
        Returns:
            bool: 重置是否成功
        """
        try:
            self.config = DEFAULT_CONFIG.copy()
            return self.save_config()
        except Exception as e:
            logger.error(f"重置配置时出错: {e}")
            return False