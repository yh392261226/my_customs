"""
全局国际化管理器，提供应用程序范围内的i18n访问
"""

import os
from typing import Optional
from .i18n import I18n

# 全局i18n实例
_global_i18n: Optional[I18n] = None

def init_global_i18n(locale_dir: str = "src/locales", default_locale: str = "zh_CN") -> None:
    """
    初始化全局i18n实例（稳健路径解析 + 可用语言回退）
    
    Args:
        locale_dir: 语言包目录（可相对或绝对）
        default_locale: 默认语言（如 'zh_CN' 或 'en_US'）
    """
    global _global_i18n

    # 解析候选路径，避免依赖当前工作目录
    candidates: list[str] = []
    try:
        # 1) 传入值原样（可能是绝对或相对）
        candidates.append(locale_dir)
        # 2) 传入值的绝对路径
        import os
        candidates.append(os.path.abspath(locale_dir))
        # 3) 以当前模块目录为基准的 locales 目录
        module_dir = os.path.dirname(__file__)
        # 如果传入默认 'src/locales'，模块目录即为该路径
        if locale_dir == "src/locales":
            candidates.append(os.path.abspath(module_dir))
        else:
            # 其他情况尝试组合
            candidates.append(os.path.abspath(os.path.join(module_dir, "..", os.path.basename(locale_dir))))
    except Exception:
        pass

    # 选择第一个存在的目录
    resolved = None
    for p in candidates:
        if isinstance(p, str):
            try:
                if os.path.isdir(p):
                    resolved = p
                    break
            except Exception:
                continue

    # 若仍未解析成功，兜底使用传入值
    if resolved is None:
        resolved = locale_dir

    # 初始化 I18n
    _global_i18n = I18n(resolved, default_locale)

    # 如果默认语言不可用，尝试回退到英文
    try:
        available = getattr(_global_i18n, "available_locales", []) or []
        if isinstance(available, list) and default_locale not in available and "en_US" in available:
            _global_i18n.set_locale("en_US")  # type: ignore[attr-defined]
    except Exception:
        # 回退失败时忽略，保持默认逻辑
        pass

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