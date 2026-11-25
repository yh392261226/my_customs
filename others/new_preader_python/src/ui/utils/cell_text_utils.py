"""表格单元格文本格式化工具。

用于在 DataTable 中显示竖线分隔的分类等可能过长的元数据：按终端显示宽度
（中日韩字符按 2 列）截断，超出部分用省略号，完整内容由调用方放入 tooltip。
"""
from __future__ import annotations

import unicodedata
from typing import Any, Iterable


def display_width(text: str) -> int:
    """返回字符串在终端中占用的列宽（全角/宽字符按 2 列）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def truncate_for_cell(text: str, max_width: int = 18, suffix: str = "…") -> str:
    """按终端显示宽度截断文本；未超长时原样返回。"""
    if not text or display_width(text) <= max_width:
        return text
    result: list[str] = []
    width = 0
    for ch in text:
        ch_width = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if width + ch_width + len(suffix) > max_width:
            break
        result.append(ch)
        width += ch_width
    return "".join(result).rstrip(" |,") + suffix


def normalize_category_values(values: Any) -> list[str]:
    """把列表/逗号串统一为去重后的非空分类名。"""
    if isinstance(values, str):
        raw: Iterable[Any] = values.split(",")
    elif isinstance(values, (list, tuple, set)):
        raw = values
    else:
        raw = [values] if values else []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw:
        name = str(item or "").strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def category_text(values: Any) -> str:
    """把分类序列化为带空格的竖线分隔字符串（数据库仍按逗号存储）。"""
    return " | ".join(normalize_category_values(values))


def format_categories_for_cell(values: Any, max_width: int = 18) -> str:
    """分类显示文本：竖线分隔，超长截断。"""
    return truncate_for_cell(category_text(values), max_width)
