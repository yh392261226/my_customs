"""
爬取书籍格式化重排开关
======================

两级开关（逻辑与）：

* 总开关 ``advanced.crawl_format_enabled``（设置中心 -> 高级设置）
* 站点开关 ``novel_sites.format_enabled``（书籍网站编辑页）

只有两者同时开启时，爬取落盘才走统一的排版入口 ``build_body``；
任一关闭则保留网站返回的原始正文（``build_raw_body``），
不做自动切章、章节编号、段落重排、缩进与全角标点归一化。

两个开关默认值均为 True，因此升级后原有排版行为不变。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

CONFIG_SECTION = "advanced"
CONFIG_KEY = "crawl_format_enabled"
SITE_FIELD = "format_enabled"

DEFAULT_GLOBAL_ENABLED = True
DEFAULT_SITE_ENABLED = True

_TRUE_VALUES = ("1", "true", "yes", "on")
_FALSE_VALUES = ("0", "false", "no", "off")


def _as_bool(value: Any, default: bool) -> bool:
    """兼容 SQLite 的 0/1、bool 与配置中的字符串值。"""
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_VALUES:
            return True
        if normalized in _FALSE_VALUES:
            return False
        return default
    return bool(value)


def get_global_format_enabled() -> bool:
    """读取设置中心的总开关（后台爬取线程也可安全调用）。"""
    try:
        from src.config.config_manager import ConfigManager
        config = ConfigManager.get_instance().get_config() or {}
        section = config.get(CONFIG_SECTION) or {}
        return _as_bool(section.get(CONFIG_KEY), DEFAULT_GLOBAL_ENABLED)
    except Exception as e:
        logger.debug(f"读取格式化重排总开关失败，按默认开启处理: {e}")
        return DEFAULT_GLOBAL_ENABLED


def resolve_format_enabled(site: Optional[Dict[str, Any]] = None) -> bool:
    """判定某个书籍网站本次爬取是否格式化重排（总开关 AND 站点开关）。

    Args:
        site: 书籍网站配置字典；为 None 或不含该字段时按站点默认开启处理。

    Returns:
        bool: True 表示落盘时执行统一排版。
    """
    global_enabled = get_global_format_enabled()
    if not global_enabled:
        return False

    site = site or {}
    if SITE_FIELD in site:
        return _as_bool(site[SITE_FIELD], DEFAULT_SITE_ENABLED)

    # 少数调用方传入的是精简过或 UI 缓存的站点字典，按 id 回查数据库，
    # 保证「该网站开关关着就不格式化这个网站」在所有入口都成立
    site_id = site.get("id") or site.get("site_id")
    if site_id:
        try:
            from src.core.database_manager import DatabaseManager
            record = DatabaseManager().get_novel_site_by_id(int(site_id)) or {}
            if SITE_FIELD in record:
                return _as_bool(record[SITE_FIELD], DEFAULT_SITE_ENABLED)
        except Exception as e:
            logger.debug(f"回查书籍网站格式化开关失败，按默认开启处理: {e}")
    return DEFAULT_SITE_ENABLED
