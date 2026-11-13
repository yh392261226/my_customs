# -*- coding: utf-8 -*-
"""
书籍网站「爬取头」设置：普通 / 手机

站点表 novel_sites.crawl_header_mode 取值为 'normal' 或 'mobile'：
  - normal：完全保持原来的爬取请求头（桌面 UA），不做任何改动；
  - mobile：以移动端身份爬取，注入手机 User-Agent 与完整的移动端请求头
            （Sec-CH-UA-Mobile / Sec-CH-UA-Platform / Sec-Fetch-* / Referer 等），
            并让 cloudscraper / selenium / playwright 等降级分支也使用手机 UA 与手机视口。

移动端 UA 与设备预设复用 src/utils/mobile_simulator.py 的 DEVICE_PRESETS，
保证「HTML 手机模拟器」里看到的页面与爬虫抓到的页面使用同一套设备指纹。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.utils.logger import get_logger
from src.utils.mobile_simulator import DEFAULT_DEVICE, DEVICE_PRESETS

logger = get_logger(__name__)

MODE_NORMAL = "normal"
MODE_MOBILE = "mobile"
DEFAULT_MODE = MODE_NORMAL

# 数据库列名 / 站点字典键，集中定义避免各处拼写不一致
DB_COLUMN = "crawl_header_mode"

DEFAULT_DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_MOBILE_ALIASES = {"mobile", "phone", "手机", "true", "yes", "on", "1"}


def normalize_mode(value: Any) -> str:
    """把数据库/界面/API 里可能存在的各种取值归一成 normal / mobile。"""
    text = str(value or "").strip().lower()
    return MODE_MOBILE if text in _MOBILE_ALIASES else MODE_NORMAL


def mode_from_site(site: Optional[Dict[str, Any]]) -> str:
    """从书籍网站配置字典读取爬取头模式；缺省/异常一律按「普通」处理。"""
    if not isinstance(site, dict):
        return DEFAULT_MODE
    return normalize_mode(site.get(DB_COLUMN))


def is_mobile_mode(mode: Any) -> bool:
    return normalize_mode(mode) == MODE_MOBILE


def configured_mobile_device() -> str:
    """默认手机设备：复用手机模拟器的 device 配置，允许用户在设置里切换。"""
    try:
        from src.config.config_manager import ConfigManager
        cfg = ConfigManager.get_instance().get_config()
        device = str((cfg.get("mobile_simulator", {}) or {}).get("device") or DEFAULT_DEVICE)
        if device in DEVICE_PRESETS and device != "desktop":
            return device
    except Exception as e:
        logger.debug(f"读取手机设备配置失败，使用默认值: {e}")
    return DEFAULT_DEVICE


def mobile_user_agent(device: Optional[str] = None) -> str:
    preset = DEVICE_PRESETS.get(device or configured_mobile_device()) or DEVICE_PRESETS[DEFAULT_DEVICE]
    return str(preset["ua"])


def mobile_viewport(device: Optional[str] = None) -> Dict[str, int]:
    preset = DEVICE_PRESETS.get(device or configured_mobile_device()) or DEVICE_PRESETS[DEFAULT_DEVICE]
    return {"width": int(preset["width"]), "height": int(preset["height"])}


def build_crawl_headers(mode: Any, referer: str = "") -> Dict[str, str]:
    """
    生成需要覆盖到 requests.Session 上的请求头。

    「普通」模式返回空字典 —— 解析器原有的桌面请求头一个字节都不改变。
    「手机」模式返回一整套移动端导航请求头。
    """
    if not is_mobile_mode(mode):
        return {}
    preset = DEVICE_PRESETS.get(configured_mobile_device()) or DEVICE_PRESETS[DEFAULT_DEVICE]
    headers = {
        "User-Agent": str(preset["ua"]),
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                   "image/avif,image/webp,*/*;q=0.8"),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Sec-CH-UA-Mobile": "?1",
        "Sec-CH-UA-Platform": str(preset["ch_platform"]),
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def apply_to_parser(parser: Any, site: Optional[Dict[str, Any]] = None,
                    mode: Optional[str] = None) -> str:
    """
    在解析器实例构造完成后注入爬取头（此时子类 __init__ 里的 headers 已设置完毕，
    由本函数做最后一次覆盖，避免 cms_t4_v2 等子类把 UA 改回桌面）。

    Returns:
        实际生效的模式 normal / mobile
    """
    resolved = normalize_mode(mode) if mode is not None else mode_from_site(site)
    referer = ""
    if isinstance(site, dict):
        referer = str(site.get("url") or "").strip()

    headers = build_crawl_headers(resolved, referer=referer)
    try:
        parser.crawl_header_mode = resolved
        parser.crawl_headers = dict(headers)
    except Exception as e:  # 极少数解析器是 slots / 只读对象
        logger.debug(f"无法在解析器上保存爬取头标记: {e}")

    if headers:
        session = getattr(parser, "session", None)
        if session is not None and hasattr(session, "headers"):
            try:
                session.headers.update(headers)
                logger.info(f"已启用「手机」爬取头: UA={headers['User-Agent'][:48]}...")
            except Exception as e:
                logger.warning(f"注入手机爬取头失败: {e}")
    return resolved


def is_mobile_parser(parser: Any) -> bool:
    """判断解析器是否处于手机爬取模式（未注入过的解析器一律视为普通）。"""
    return is_mobile_mode(getattr(parser, "crawl_header_mode", DEFAULT_MODE))


def effective_user_agent(parser: Any, desktop_ua: str = DEFAULT_DESKTOP_UA) -> str:
    """给各降级分支用：手机模式返回手机 UA，否则返回调用方原来的桌面 UA。"""
    return mobile_user_agent() if is_mobile_parser(parser) else desktop_ua


def effective_window_size_arg(parser: Any,
                              desktop_arg: str = "--window-size=1920,1080") -> str:
    """Selenium / CloakBrowser 的窗口尺寸参数。"""
    if not is_mobile_parser(parser):
        return desktop_arg
    vp = mobile_viewport()
    return f"--window-size={vp['width']},{vp['height']}"


def resolve_site_mode_by_url(site_url: Optional[str]) -> str:
    """
    兜底：调用方没有传完整 site 字典时，按站点 URL 从数据库回查爬取头模式。
    查询失败一律返回「普通」，绝不因为配置读取失败而中断爬取。
    """
    if not site_url:
        return DEFAULT_MODE
    target = str(site_url).strip().rstrip("/").lower()
    if not target:
        return DEFAULT_MODE
    try:
        from src.core.database_manager import DatabaseManager
        for row in DatabaseManager().get_novel_sites() or []:
            url = str(row.get("url") or "").strip().rstrip("/").lower()
            if url and (url == target or target.startswith(url + "/") or url.startswith(target + "/")):
                return mode_from_site(row)
    except Exception as e:
        logger.debug(f"按网址回查爬取头模式失败，按普通模式处理: {e}")
    return DEFAULT_MODE
