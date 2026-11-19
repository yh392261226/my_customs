"""浏览器阅读器的书籍公开标识。

数据库以 ``path`` 作为主键，但局域网书库页面不能把物理路径暴露到 URL 里。
这里用规范化后的书籍路径生成稳定、不可逆的短 key，供 ``/reader?book=``、
``/download_book?book=`` 与离线书库缓存使用。路径不变时 key 不变，
程序重启、换端口或换设备访问都不会影响它。
"""

import hashlib
import os
import re
from pathlib import Path
from typing import Optional

_BOOK_KEY_RE = re.compile(r"^[0-9a-f]{20}$")


def book_key_for_path(path: str) -> str:
    """根据书籍路径生成 20 位十六进制公开标识；路径为空时返回空串。"""
    if not path:
        return ""
    try:
        normalized = os.path.normcase(os.path.realpath(os.path.abspath(str(path))))
    except Exception:
        normalized = str(path)
    try:
        data = normalized.encode("utf-8", "surrogatepass")
    except Exception:
        data = normalized.encode("utf-8", "replace")
    return hashlib.sha256(data).hexdigest()[:20]


def is_book_key(value: str) -> bool:
    """判断字符串是否像本模块生成的公开标识。"""
    return bool(_BOOK_KEY_RE.fullmatch((value or "").strip().lower()))


def book_id_for_path(path: str) -> str:
    """内部书籍 ID：沿用文件名（不含扩展名），保持进度/标注等历史数据兼容。"""
    if not path:
        return ""
    try:
        return Path(str(path)).stem
    except Exception:
        return str(path)


def book_path_from_dict_or_obj(item) -> str:
    """兼容 Book 对象与 dict 两种书库记录形式。"""
    if isinstance(item, dict):
        value = item.get("path")
    else:
        value = getattr(item, "path", "")
    return str(value or "")


def known_book_paths():
    """返回允许通过浏览器阅读器打开的路径：书库 + 爬取成功记录。"""
    paths = []
    seen = set()

    def add(path):
        value = str(path or "").strip()
        if not value or value == "already_exists":
            return
        try:
            norm = os.path.normcase(os.path.realpath(os.path.abspath(value)))
        except Exception:
            norm = value
        if norm not in seen:
            seen.add(norm)
            paths.append(value)

    try:
        from src.core.bookshelf import Bookshelf
        for book in Bookshelf().get_all_books() or []:
            add(book_path_from_dict_or_obj(book))
    except Exception:
        pass

    try:
        from src.api import db
        if "file_path" in db.get_columns("crawl_history"):
            conn = db.get_conn()
            try:
                rows = conn.execute(
                    "SELECT file_path FROM crawl_history "
                    "WHERE file_path IS NOT NULL AND file_path != ''"
                ).fetchall()
                for row in rows:
                    add(row[0])
            finally:
                conn.close()
    except Exception:
        pass

    return paths


def is_known_book_path(path: str) -> bool:
    """路径白名单：书库或爬取记录中登记过的文件才允许浏览器打开。"""
    target = str(path or "").strip()
    if not target:
        return False
    try:
        target = os.path.normcase(os.path.realpath(os.path.abspath(target)))
    except Exception:
        pass
    for candidate in known_book_paths():
        try:
            norm = os.path.normcase(os.path.realpath(os.path.abspath(candidate)))
        except Exception:
            norm = candidate
        if norm == target:
            return True
    return False


def resolve_path_by_book_key(book_key: str) -> str:
    """把公开标识反查为书库/爬取记录中的物理路径。"""
    key = str(book_key or "").strip().lower()
    if not key:
        return ""
    for path in known_book_paths():
        if book_key_for_path(path) == key:
            return path
    return ""
