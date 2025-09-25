"""
设置项基类
定义所有设置项的通用接口和行为
"""


import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Callable, Dict, List
from dataclasses import dataclass

from .setting_observer import notify_setting_change

from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class SettingValidationResult:
    """设置项验证结果"""
    is_valid: bool
    message: Optional[str] = None
    suggested_value: Optional[Any] = None

class BaseSetting(ABC):
    """
    设置项抽象基类
    提供统一的设置项接口和验证机制
    """
    
    def __init__(
        self,
        key: str,
        default_value: Any,
        display_name: str,
        description: str = "",
        category: str = "general",
        validator: Optional[Callable[[Any], SettingValidationResult]] = None,
        on_change: Optional[Callable[[Any, Any], None]] = None,
        is_hidden: bool = False
    ):
        """
        初始化设置项
        
        Args:
            key: 设置项的唯一键名
            default_value: 默认值
            display_name: 显示名称
            description: 描述信息
            category: 分类
            validator: 验证函数
            on_change: 值变化时的回调函数
            is_hidden: 是否隐藏该设置项
        """
        self.key = key
        self._value = default_value
        self.default_value = default_value
        self.display_name = display_name
        self.description = description
        self.category = category
        self.validator = validator
        self.on_change = on_change
        self.is_hidden = is_hidden
        
    @property
    def value(self) -> Any:
        """获取当前值"""
        return self._value
        
    @value.setter
    def value(self, new_value: Any) -> None:
        """设置新值，会触发验证和回调"""
        old_value = self._value
        
        # 验证新值
        validation_result = self.validate(new_value)
        if not validation_result.is_valid:
            if validation_result.suggested_value is not None:
                new_value = validation_result.suggested_value
            else:
                raise ValueError(f"Invalid value for setting {self.key}: {validation_result.message}")
        
        # 设置新值
        self._value = new_value
        
        # 触发变化回调
        if self.on_change and old_value != new_value:
            try:
                self.on_change(old_value, new_value)
            except Exception as e:
                logger.error(f"Error in on_change callback for setting {self.key}: {e}")
        
        # 发送设置变更通知
        if old_value != new_value:
            try:
                notify_setting_change(self.key, old_value, new_value, "user")
            except Exception as e:
                logger.error(f"Error notifying setting change for {self.key}: {e}")
    
    def validate(self, value: Any) -> SettingValidationResult:
        """
        验证设置值
        
        Args:
            value: 要验证的值
            
        Returns:
            SettingValidationResult: 验证结果
        """
        # 首先调用自定义验证器
        if self.validator:
            result = self.validator(value)
            if not result.is_valid:
                return result
        
        # 然后调用类型特定的验证
        return self._validate_type_specific(value)
    
    @abstractmethod
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """
        类型特定的验证逻辑
        子类必须实现此方法
        
        Args:
            value: 要验证的值
            
        Returns:
            SettingValidationResult: 验证结果
        """
        pass
    
    def reset_to_default(self) -> None:
        """重置为默认值"""
        self.value = self.default_value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "key": self.key,
            "value": self.value,
            "default_value": self.default_value,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "is_hidden": self.is_hidden
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseSetting':
        """从字典创建设置项"""
        raise NotImplementedError("Subclasses must implement from_dict")
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(key={self.key}, value={self.value})"
    
    def __repr__(self) -> str:
        return str(self)