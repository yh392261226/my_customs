"""
翻译配置管理器 - 管理第三方翻译API的配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from src.config.config_manager import ConfigManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TranslationConfig:
    """翻译配置管理器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化翻译配置管理器
        
        Args:
            config_manager: 配置管理器实例，如果为None则创建新实例
        """
        self.config_manager = config_manager if config_manager is not None else ConfigManager.get_instance()
        self.config: Dict[str, Any] = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """从系统配置加载翻译配置"""
        system_config = self.config_manager.get_config()
        translation_config = system_config.get("translation", {})
        
        # 确保配置结构完整
        if not translation_config:
            # 使用默认配置结构
            return {
                "translation_services": {
                    "baidu": {
                        "enabled": False,
                        "app_id": "",
                        "app_key": "",
                        "api_url": "https://fanyi-api.baidu.com/api/trans/vip/translate"
                    },
                    "youdao": {
                        "enabled": False,
                        "app_key": "",
                        "app_secret": "",
                        "api_url": "https://openapi.youdao.com/api"
                    },
                    "google": {
                        "enabled": False,
                        "api_key": "",
                        "api_url": "https://translation.googleapis.com/language/translate/v2"
                    },
                    "microsoft": {
                        "enabled": False,
                        "subscription_key": "",
                        "region": "global",
                        "api_url": "https://api.cognitive.microsofttranslator.com/translate"
                    }
                },
                "default_service": "baidu",
                "source_language": "auto",
                "target_language": "zh",
                "cache_enabled": True,
                "cache_duration": 3600,  # 1小时
                "timeout": 10,
                "retry_count": 3
            }
        
        return translation_config
    
    def save_config(self) -> bool:
        """保存配置到系统配置"""
        try:
            # 获取当前系统配置
            system_config = self.config_manager.get_config()
            # 更新翻译配置部分
            system_config["translation"] = self.config
            # 保存系统配置
            self.config_manager.save_config(system_config)
            
            logger.info("已保存翻译配置到系统配置")
            return True
        except Exception as e:
            logger.error(f"保存翻译配置失败: {e}")
            return False
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取指定翻译服务的配置"""
        return self.config.get("translation_services", {}).get(service_name)
    
    def set_service_config(self, service_name: str, config: Dict[str, Any]) -> None:
        """设置指定翻译服务的配置"""
        if "translation_services" not in self.config:
            self.config["translation_services"] = {}
        
        self.config["translation_services"][service_name] = config
    
    def enable_service(self, service_name: str) -> bool:
        """启用翻译服务"""
        service_config = self.get_service_config(service_name)
        if service_config:
            service_config["enabled"] = True
            return True
        return False
    
    def disable_service(self, service_name: str) -> bool:
        """禁用翻译服务"""
        service_config = self.get_service_config(service_name)
        if service_config:
            service_config["enabled"] = False
            return True
        return False
    
    def get_enabled_services(self) -> Dict[str, Dict[str, Any]]:
        """获取所有启用的翻译服务"""
        enabled_services = {}
        for name, config in self.config.get("translation_services", {}).items():
            if config.get("enabled", False):
                enabled_services[name] = config
        return enabled_services
    
    def set_default_service(self, service_name: str) -> bool:
        """设置默认翻译服务"""
        if service_name in self.config.get("translation_services", {}):
            self.config["default_service"] = service_name
            return True
        return False
    
    def get_default_service(self) -> str:
        """获取默认翻译服务"""
        return self.config.get("default_service", "baidu")
    
    def set_language_pair(self, source: str, target: str) -> None:
        """设置语言对"""
        self.config["source_language"] = source
        self.config["target_language"] = target
    
    def get_language_pair(self) -> tuple[str, str]:
        """获取语言对"""
        return (
            self.config.get("source_language", "auto"),
            self.config.get("target_language", "zh")
        )
    
    def validate_config(self) -> Dict[str, str]:
        """验证配置有效性"""
        errors = {}
        
        # 检查默认服务是否启用
        default_service = self.get_default_service()
        if default_service not in self.get_enabled_services():
            errors["default_service"] = f"默认服务 {default_service} 未启用"
        
        # 检查启用的服务配置是否完整
        for service_name, config in self.get_enabled_services().items():
            if service_name == "baidu":
                if not config.get("app_id") or not config.get("app_key"):
                    errors[service_name] = "百度翻译API配置不完整"
            elif service_name == "youdao":
                if not config.get("app_key") or not config.get("app_secret"):
                    errors[service_name] = "有道翻译API配置不完整"
            elif service_name == "google":
                if not config.get("api_key"):
                    errors[service_name] = "Google翻译API配置不完整"
            elif service_name == "microsoft":
                if not config.get("subscription_key"):
                    errors[service_name] = "微软翻译API配置不完整"
        
        return errors
    
    def is_configured(self) -> bool:
        """检查是否有可用的翻译服务配置"""
        enabled_services = self.get_enabled_services()
        if not enabled_services:
            return False
        
        # 检查至少有一个服务的配置是完整的
        for service_name, config in enabled_services.items():
            if service_name == "baidu":
                if config.get("app_id") and config.get("app_key"):
                    return True
            elif service_name == "youdao":
                if config.get("app_key") and config.get("app_secret"):
                    return True
            elif service_name == "google":
                if config.get("api_key"):
                    return True
            elif service_name == "microsoft":
                if config.get("subscription_key"):
                    return True
        
        return False


# 全局配置实例
_translation_config: Optional[TranslationConfig] = None


def get_translation_config() -> TranslationConfig:
    """获取全局翻译配置实例"""
    global _translation_config
    if _translation_config is None:
        _translation_config = TranslationConfig()
    return _translation_config


def set_translation_config(config: TranslationConfig) -> None:
    """设置全局翻译配置实例"""
    global _translation_config
    _translation_config = config