"""
书库高级筛选条件。

把「作者 / 标签 / 文件情况 / 阅读状态 / 拼音 / 大小 / 入库时间」等条件抽象为可组合的
:class:`LibraryFilter`，书库界面、批量操作界面、Web 查询都可复用同一套判定逻辑。

条件之间为 AND 关系（全部满足才保留）；互斥条件（如「无作者」+「有作者」）自然得到
空结果，界面上的分组开关不会同时给出互斥组合。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

UNKNOWN_AUTHORS = {"", "未知作者", "unknown", "unknown author", "none", "null"}
# 大小输入框以 MB 为单位；存储与比较时换算为字节
MB = 1024 * 1024


# 筛选分组：类别 -> [(字段, 标签 i18n key)]
FILTER_GROUPS: List[Tuple[str, List[Tuple[str, str]]]] = [
    ("author", [
        ("no_author", "library_filter.no_author"),
        ("has_author", "library_filter.has_author"),
    ]),
    ("tags", [
        ("no_tags", "library_filter.no_tags"),
        ("has_tags", "library_filter.has_tags"),
    ]),
    ("file", [
        ("no_file", "library_filter.no_file"),
        ("file_exists", "library_filter.file_exists"),
    ]),
    ("status", [
        ("unread", "library_filter.unread"),
        ("read", "library_filter.read"),
        ("finished", "library_filter.finished"),
    ]),
    ("pinyin", [
        ("no_pinyin", "library_filter.no_pinyin"),
        ("has_pinyin", "library_filter.has_pinyin"),
    ]),
]

# 所有布尔型条件字段（用于序列化 / 收集）
BOOL_FIELDS: List[str] = [field for _, items in FILTER_GROUPS for field, _ in items]

# 字段短名（用于状态栏展示）
CONDITION_LABELS: Dict[str, str] = {
    "no_author": "无作者",
    "has_author": "有作者",
    "no_tags": "无标签",
    "has_tags": "有标签",
    "no_file": "无文件",
    "file_exists": "有文件",
    "unread": "未读",
    "read": "已读",
    "finished": "已读完",
    "no_pinyin": "无拼音",
    "has_pinyin": "有拼音",
}


@dataclass
class LibraryFilter:
    """书库筛选条件；所有布尔字段默认 False，范围字段默认 None（不限制）。"""

    # 作者
    no_author: bool = False
    has_author: bool = False
    # 标签
    no_tags: bool = False
    has_tags: bool = False
    # 文件情况
    no_file: bool = False
    file_exists: bool = False
    # 阅读状态
    unread: bool = False
    read: bool = False
    finished: bool = False
    # 拼音
    no_pinyin: bool = False
    has_pinyin: bool = False
    # 大小（MB），None 表示不限制
    size_min: Optional[float] = None
    size_max: Optional[float] = None
    # 入库时间（YYYY-MM-DD），None 表示不限制
    added_after: Optional[str] = None
    added_before: Optional[str] = None

    # -------------------------------------------------------------- 序列化

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "LibraryFilter":
        if not data:
            return cls()
        valid = {f.name for f in fields(cls)}
        kwargs: Dict[str, Any] = {}
        for name in valid:
            if name not in data:
                continue
            v = data[name]
            if name in ("size_min", "size_max"):
                kwargs[name] = float(v) if v not in (None, "", "None") else None
            elif name in ("added_after", "added_before"):
                kwargs[name] = str(v) if v not in (None, "", "None") else None
            else:
                kwargs[name] = bool(v)
        return cls(**kwargs)

    def is_empty(self) -> bool:
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, bool):
                if v:
                    return False
            elif v not in (None, ""):
                return False
        return True

    def active_keys(self) -> List[str]:
        """返回当前生效（非默认）的字段名列表，用于缓存签名等。"""
        keys: List[str] = []
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, bool):
                if v:
                    keys.append(f.name)
            elif v not in (None, ""):
                keys.append(f.name)
        return keys

    def describe(self) -> str:
        parts: List[str] = []
        for field in BOOL_FIELDS:
            if getattr(self, field):
                parts.append(CONDITION_LABELS.get(field, field))
        if self.size_min is not None or self.size_max is not None:
            lo = f"{self.size_min}MB" if self.size_min is not None else "*"
            hi = f"{self.size_max}MB" if self.size_max is not None else "*"
            parts.append(f"大小 {lo}-{hi}")
        if self.added_after or self.added_before:
            lo = self.added_after or "*"
            hi = self.added_before or "*"
            parts.append(f"入库 {lo}~{hi}")
        if not parts:
            return "全部书籍"
        return " + ".join(parts)


def _author_missing(book: Any) -> bool:
    author = str(getattr(book, "author", "") or "").strip()
    return author.lower() in UNKNOWN_AUTHORS


def _tags_missing(book: Any) -> bool:
    tags = getattr(book, "tags", "") or ""
    if isinstance(tags, (list, tuple, set)):
        return len(tags) == 0
    return not any(part.strip() for part in str(tags).split(","))


def _file_missing(book: Any) -> bool:
    if getattr(book, "file_not_found", False):
        return True
    path = getattr(book, "path", "") or ""
    return not path or not os.path.isfile(path)


def matches_book(book: Any, condition: Optional[LibraryFilter],
                 reading_info_getter: Optional[Callable[[str], Dict[str, Any]]] = None) -> bool:
    """判断一本书是否满足全部筛选条件（AND 关系）。"""
    if condition is None or condition.is_empty():
        return True

    no_author = _author_missing(book)
    no_tags = _tags_missing(book)
    no_file = _file_missing(book)
    pinyin_present = bool((getattr(book, "pinyin", "") or "").strip())

    bool_checks = (
        (condition.no_author, no_author),
        (condition.has_author, not no_author),
        (condition.no_tags, no_tags),
        (condition.has_tags, not no_tags),
        (condition.no_file, no_file),
        (condition.file_exists, not no_file),
        (condition.no_pinyin, not pinyin_present),
        (condition.has_pinyin, pinyin_present),
    )
    if any(enabled and not matched for enabled, matched in bool_checks):
        return False

    # 大小范围（输入框为 MB，book.file_size 为字节）
    if condition.size_min is not None or condition.size_max is not None:
        size_mb = (getattr(book, "file_size", 0) or 0) / MB
        if condition.size_min is not None and size_mb < condition.size_min:
            return False
        if condition.size_max is not None and size_mb > condition.size_max:
            return False

    # 入库时间范围（YYYY-MM-DD 比较，ISO 字符串可直接按字典序比较）
    if condition.added_after or condition.added_before:
        add_date = str(getattr(book, "add_date", "") or "")
        if condition.added_after and add_date < condition.added_after + "T00:00:00":
            return False
        if condition.added_before and add_date[:10] > condition.added_before:
            return False

    # 阅读状态（依赖阅读信息；仅在使用相关条件时才查询，避免无谓访问）
    if condition.unread or condition.read or condition.finished:
        info: Dict[str, Any] = {}
        if reading_info_getter is not None:
            try:
                info = reading_info_getter(getattr(book, "path", "")) or {}
            except Exception:
                info = {}
        progress = float(info.get("reading_progress", 0) or 0)
        if condition.unread and progress > 0:
            return False
        if condition.read and not (0 < progress < 1.0):
            return False
        if condition.finished and progress < 1.0:
            return False

    return True


def filter_books(books: Iterable[Any], condition: Optional[LibraryFilter],
                 reading_info_getter: Optional[Callable[[str], Dict[str, Any]]] = None) -> List[Any]:
    """按条件过滤书籍列表（供书库 / 批量操作 / API 复用）。"""
    if condition is None or condition.is_empty():
        return list(books)
    return [
        book for book in books
        if matches_book(book, condition, reading_info_getter)
    ]
