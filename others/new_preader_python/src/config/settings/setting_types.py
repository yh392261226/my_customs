"""
具体设置项类型实现
"""

from typing import Any, List, Optional, Callable, Dict
from .base_setting import BaseSetting, SettingValidationResult

class BooleanSetting(BaseSetting):
    """布尔类型设置项"""
    
    def __init__(
        self,
        key: str,
        default_value: bool,
        display_name: str,
        description: str = "",
        category: str = "general",
        validator: Optional[Callable[[bool], SettingValidationResult]] = None,
        on_change: Optional[Callable[[bool, bool], None]] = None,
        is_hidden: bool = False
    ):
        super().__init__(
            key, default_value, display_name, description,
            category, validator, on_change, is_hidden
        )
    
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """验证布尔值"""
        if not isinstance(value, bool):
            try:
                # 尝试转换为布尔值
                if isinstance(value, str):
                    value = value.lower() in ('true', 'yes', '1', 'on')
                else:
                    value = bool(value)
                return SettingValidationResult(True, suggested_value=value)
            except (ValueError, TypeError):
                return SettingValidationResult(False, "Value must be a boolean")
        
        return SettingValidationResult(True)

class IntegerSetting(BaseSetting):
    """整数类型设置项"""
    
    def __init__(
        self,
        key: str,
        default_value: int,
        display_name: str,
        description: str = "",
        category: str = "general",
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        validator: Optional[Callable[[int], SettingValidationResult]] = None,
        on_change: Optional[Callable[[int, int], None]] = None,
        is_hidden: bool = False
    ):
        super().__init__(
            key, default_value, display_name, description,
            category, validator, on_change, is_hidden
        )
        self.min_value = min_value
        self.max_value = max_value
    
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """验证整数值"""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return SettingValidationResult(False, "Value must be an integer")
        
        # 检查范围
        if self.min_value is not None and int_value < self.min_value:
            return SettingValidationResult(
                False, 
                f"Value must be at least {self.min_value}",
                suggested_value=self.min_value
            )
        
        if self.max_value is not None and int_value > self.max_value:
            return SettingValidationResult(
                False,
                f"Value must be at most {self.max_value}",
                suggested_value=self.max_value
            )
        
        return SettingValidationResult(True, suggested_value=int_value)

class FloatSetting(BaseSetting):
    """浮点数类型设置项"""
    
    def __init__(
        self,
        key: str,
        default_value: float,
        display_name: str,
        description: str = "",
        category: str = "general",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        validator: Optional[Callable[[float], SettingValidationResult]] = None,
        on_change: Optional[Callable[[float, float], None]] = None,
        is_hidden: bool = False
    ):
        super().__init__(
            key, default_value, display_name, description,
            category, validator, on_change, is_hidden
        )
        self.min_value = min_value
        self.max_value = max_value
    
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """验证浮点数值"""
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return SettingValidationResult(False, "Value must be a number")
        
        # 检查范围
        if self.min_value is not None and float_value < self.min_value:
            return SettingValidationResult(
                False, 
                f"Value must be at least {self.min_value}",
                suggested_value=self.min_value
            )
        
        if self.max_value is not None and float_value > self.max_value:
            return SettingValidationResult(
                False,
                f"Value must be at most {self.max_value}",
                suggested_value=self.max_value
            )
        
        return SettingValidationResult(True, suggested_value=float_value)

class StringSetting(BaseSetting):
    """字符串类型设置项"""
    
    def __init__(
        self,
        key: str,
        default_value: str,
        display_name: str,
        description: str = "",
        category: str = "general",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        validator: Optional[Callable[[str], SettingValidationResult]] = None,
        on_change: Optional[Callable[[str, str], None]] = None,
        is_hidden: bool = False
    ):
        super().__init__(
            key, default_value, display_name, description,
            category, validator, on_change, is_hidden
        )
        self.min_length = min_length
        self.max_length = max_length
    
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """验证字符串值"""
        if not isinstance(value, str):
            try:
                str_value = str(value)
            except (ValueError, TypeError):
                return SettingValidationResult(False, "Value must be a string")
        else:
            str_value = value
        
        # 检查长度
        if self.min_length is not None and len(str_value) < self.min_length:
            return SettingValidationResult(
                False, 
                f"Value must be at least {self.min_length} characters long"
            )
        
        if self.max_length is not None and len(str_value) > self.max_length:
            return SettingValidationResult(
                False,
                f"Value must be at most {self.max_length} characters long",
                suggested_value=str_value[:self.max_length]
            )
        
        return SettingValidationResult(True, suggested_value=str_value)

class SelectSetting(BaseSetting):
    """选择类型设置项"""
    
    def __init__(
        self,
        key: str,
        default_value: Any,
        display_name: str,
        options: List[Any],
        option_labels: Optional[List[str]] = None,
        description: str = "",
        category: str = "general",
        validator: Optional[Callable[[Any], SettingValidationResult]] = None,
        on_change: Optional[Callable[[Any, Any], None]] = None,
        is_hidden: bool = False
    ):
        super().__init__(
            key, default_value, display_name, description,
            category, validator, on_change, is_hidden
        )
        self.options = options
        self.option_labels = option_labels or [str(opt) for opt in options]
    
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """验证选择值"""
        if value not in self.options:
            return SettingValidationResult(
                False, 
                f"Value must be one of: {self.options}",
                suggested_value=self.default_value
            )
        
        return SettingValidationResult(True)

class ListSetting(BaseSetting):
    """列表类型设置项"""
    
    def __init__(
        self,
        key: str,
        default_value: List[Any],
        display_name: str,
        description: str = "",
        category: str = "general",
        item_validator: Optional[Callable[[Any], bool]] = None,
        validator: Optional[Callable[[List[Any]], SettingValidationResult]] = None,
        on_change: Optional[Callable[[List[Any], List[Any]], None]] = None,
        is_hidden: bool = False
    ):
        super().__init__(
            key, default_value, display_name, description,
            category, validator, on_change, is_hidden
        )
        self.item_validator = item_validator
    
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """验证列表值"""
        if not isinstance(value, list):
            return SettingValidationResult(False, "Value must be a list")
        
        # 验证列表项
        if self.item_validator:
            for item in value:
                if not self.item_validator(item):
                    return SettingValidationResult(
                        False, 
                        f"Invalid item in list: {item}"
                    )
        
        return SettingValidationResult(True)


class SeparatorSetting(BaseSetting):
    """分隔符设置项，用于在UI中显示分隔线"""
    
    def __init__(
        self,
        key: str,
        display_name: str,
        description: str = "",
        category: str = "general",
        is_hidden: bool = False
    ):
        super().__init__(
            key, None, display_name, description,
            category, None, None, is_hidden
        )
    
    def _validate_type_specific(self, value: Any) -> SettingValidationResult:
        """分隔符设置项不需要验证值"""
        return SettingValidationResult(True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result["type"] = "separator"
        return result