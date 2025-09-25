"""
全局国际化管理器，提供应用程序范围内的i18n访问
"""

import os
from typing import Optional
from .i18n import I18n

# 全局i18n实例
_global_i18n: Optional[I18n] = None

def init_global_i18n(locale_dir: str, default_locale: str = "zh_CN") -> None:
    """
    初始化全局i18n实例
    
    Args:
        locale_dir: 语言包目录
        default_locale: 默认语言
    """
    global _global_i18n
    _global_i18n = I18n(locale_dir, default_locale)

def get_global_i18n() -> I18n:
    """
    获取全局i18n实例
    
    Returns:
        I18n: 全局i18n实例
        
    Raises:
        RuntimeError: 如果全局i18n未初始化
    """
    if _global_i18n is None:
        raise RuntimeError("全局i18n未初始化，请先调用init_global_i18n()")
    return _global_i18n

def set_global_locale(locale: str) -> bool:
    """
    设置全局语言
    
    Args:
        locale: 语言代码
        
    Returns:
        bool: 设置是否成功
    """
    try:
        i18n = get_global_i18n()
        return i18n.set_locale(locale)
    except RuntimeError:
        return False

def get_global_translation(key: str, **kwargs) -> str:
    """
    获取全局翻译
    
    Args:
        key: 翻译键
        **kwargs: 格式化参数
        
    Returns:
        str: 翻译后的文本，如果未初始化则返回键本身
    """
    try:
        i18n = get_global_i18n()
        return i18n.t(key, **kwargs)
    except RuntimeError:
        return key

def is_global_i18n_initialized() -> bool:
    """
    检查全局i18n是否已初始化
    
    Returns:
        bool: 是否已初始化
    """
    return _global_i18n is not None

# 创建快捷函数
def t(key: str, **kwargs) -> str:
    """
    翻译快捷函数
    
    Args:
        key: 翻译键
        **kwargs: 格式化参数
        
    Returns:
        str: 翻译后的文本
    """
    return get_global_translation(key, **kwargs)