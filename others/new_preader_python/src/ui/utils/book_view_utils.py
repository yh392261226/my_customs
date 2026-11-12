"""
书籍视图公共工具：数据组装、预览读取、打开弹窗、查看文件。

书库 / 批量操作 / 重复书籍 / 补足缺失 / 爬取管理 / 文件资源管理器等页面，
过去各自重复实现「查书 → 组装详情 → 读前 2000 字 → 组装 metadata →
构造详情或预览弹窗 → 处理文件不存在」。现在统一走本模块 + 单一
``src.ui.widgets.book_view_dialog.BookViewDialog``。

典型用法::

    from src.ui.utils.book_view_utils import open_book_view_for_path

    # 查看详情（自动带预览与查看文件能力）
    open_book_view_for_path(self.app, book.path, bookshelf=self.bookshelf,
                            theme_manager=self.theme_manager)

    # 直接进入预览视图
    open_book_view_for_path(self.app, book.path, bookshelf=self.bookshelf,
                            initial_view="preview")

    # 自定义详情（爬取记录 / 文件系统条目）
    open_book_view_for_path(self.app, path, title="...", details=details,
                            metadata=metadata)

    # 只想在文件管理器中定位文件
    reveal_book_file(self, path)
"""
from __future__ import annotations

import os
import re
import time
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.file_helpers import read_file_preview
from src.utils.logger import get_logger

logger = get_logger(__name__)

PREVIEW_CHARS = 2000


# ---------------------------------------------------------------------- 基础工具

def get_theme_manager(app: Any = None) -> ThemeManager:
    """统一获取主题管理器（兼容没有 app.theme_manager 的场景）。"""
    manager = getattr(app, "theme_manager", None) if app is not None else None
    return manager if manager is not None else ThemeManager()


def reveal_book_file(screen: Any, file_path: str) -> bool:
    """查看文件：在系统文件管理器中定位，并统一给出提示。"""
    t = get_global_i18n().t
    try:
        if not file_path or not os.path.exists(file_path):
            screen.notify(t("common.file_not_exist"), severity="warning")
            return False
        from src.utils.file_helpers import reveal_in_file_manager
        ok = reveal_in_file_manager(file_path)
        screen.notify(
            t("bookshelf.opened_in_file_explorer") if ok
            else t("bookshelf.view_file_failed"),
            severity="information" if ok else "error",
        )
        return ok
    except Exception as e:
        logger.error(f"查看文件位置失败: {e}")
        try:
            screen.notify(f"{t('common.action_failed')}: {e}", severity="error")
        except Exception:
            pass
        return False


def clean_preview_text(text: str) -> str:
    """清洗预览文本，移除可能破坏 Textual 渲染的控制/格式字符与乱码。"""
    if not text:
        return ""
    cleaned: List[str] = []
    for char in text:
        category = unicodedata.category(char)
        if category.startswith(("L", "N", "P", "S")):
            cleaned.append(char)
        elif category == "Zs" or category in ("Zl", "Zp"):
            cleaned.append(char)
        elif category == "Cc":
            if char in ("\n", "\r", "\t"):
                cleaned.append(char)
        elif category == "Co":
            cleaned.append("□")
        # Cf（BOM / 零宽字符）与 Cn（未分配）直接丢弃
    result = "".join(cleaned)
    result = re.sub(r"[ÿþ]{2,}", "... ", result)
    result = re.sub(r"[«»]{3,}", "...", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return "\n".join(line.rstrip() for line in result.split("\n"))


def read_preview_content(file_path: str, max_chars: int = PREVIEW_CHARS) -> str:
    """读取文件前 N 字（编码自适应）并清洗成可安全渲染的文本。"""
    if not file_path or not os.path.isfile(file_path):
        return ""
    try:
        return clean_preview_text(read_file_preview(file_path, max_chars=max_chars))
    except Exception as e:
        logger.error(f"读取文件预览失败: {file_path}: {e}")
        return ""


# ---------------------------------------------------------------------- 数据组装

def build_book_metadata(book: Any) -> Dict[str, Any]:
    """从 Book 对象构建预览侧栏所需的 metadata。"""
    return {
        "author": getattr(book, "author", "") or "",
        "format": getattr(book, "format", "") or "",
        "size": getattr(book, "size", 0) or 0,
        "tags": getattr(book, "tags", "") or "",
        "path": getattr(book, "path", "") or "",
    }


def build_book_details(book: Any, bookshelf: Any = None,
                       source_getter: Optional[Callable[[str], str]] = None,
                       source: Optional[str] = None) -> List[Tuple[str, Any]]:
    """从 Book 对象构建完整详情条目（书库 / 批量操作 / 去重通用）。"""
    from src.utils.file_utils import FileUtils

    t = get_global_i18n().t
    reading_info: Dict[str, Any] = {}
    if bookshelf is not None and hasattr(bookshelf, "get_book_reading_info"):
        try:
            reading_info = bookshelf.get_book_reading_info(book.path) or {}
        except Exception:
            reading_info = {}
    progress = float(reading_info.get("reading_progress", 0) or 0) * 100

    source_text = source
    if source_text is None and source_getter is not None:
        try:
            source_text = source_getter(book.path)
        except Exception:
            source_text = None
    if source_text is None:
        source_text = t("book_details.local_import")

    file_size = getattr(book, "file_size", 0) or getattr(book, "size", 0) or 0
    return [
        (t("common.book_name"), book.title),
        (t("common.author"), book.author),
        (t("book_details.source"), source_text),
        (t("book_details.file_name"), getattr(book, "file_name", "")),
        (t("common.file_path"), book.path),
        (t("common.format"), book.format),
        (t("common.size"), FileUtils.format_file_size(file_size)),
        (t("book_details.file_status"),
         t("book_details.file_missing") if getattr(book, "file_not_found", False)
         else t("book_details.file_normal")),
        (t("common.tag"), getattr(book, "tags", "") or ""),
        (t("book_details.add_date"), getattr(book, "add_date", "") or ""),
        (t("common.progress"), f"{progress:.1f}%"),
        (t("book_details.last_read"), reading_info.get("last_read_date") or ""),
        (t("book_details.word_count"), str(reading_info.get("word_count", 0) or 0)),
        (t("book_details.open_count"), str(getattr(book, "open_count", 0) or 0)),
    ]


def build_path_details(path: str) -> List[Tuple[str, Any]]:
    """为任意文件/目录构建基础详情（文件资源管理器等场景）。"""
    t = get_global_i18n().t
    from src.utils.file_utils import FileUtils

    details: List[Tuple[str, Any]] = [
        (t("book_details.file_name"), os.path.basename(path) or path),
        (t("common.file_path"), path),
        (t("file_explorer.type"),
         t("file_explorer.detail_dir") if os.path.isdir(path)
         else t("file_explorer.detail_file")),
    ]
    if os.path.isfile(path):
        details.append((t("file_explorer.detail_extension"),
                        FileUtils.get_file_extension(path) or "-"))
        try:
            details.append((t("common.size"),
                            FileUtils.format_file_size(FileUtils.get_file_size(path))))
            details.append((t("file_explorer.detail_modified"),
                            time.strftime("%Y-%m-%d %H:%M:%S",
                                          time.localtime(os.path.getmtime(path)))))
        except OSError:
            pass
    return details


def build_view_data(file_path: str, *, title: Optional[str] = None,
                    details: Optional[List[Tuple[str, Any]]] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    bookshelf: Any = None,
                    source_getter: Optional[Callable[[str], str]] = None,
                    source: Optional[str] = None,
                    allow_preview: bool = True,
                    max_chars: int = PREVIEW_CHARS,
                    content: Optional[str] = None) -> "BookViewData":
    """组装统一视图数据：详情、预览内容、metadata 一次备齐。"""
    from src.ui.widgets.book_view_dialog import BookViewData

    path = os.path.abspath(os.path.expanduser(file_path or ""))
    exists = bool(path) and os.path.isfile(path)
    book = None
    if bookshelf is not None and hasattr(bookshelf, "get_book"):
        try:
            book = bookshelf.get_book(path)
        except Exception:
            book = None

    if details is None:
        if book is not None:
            details = build_book_details(book, bookshelf, source_getter, source)
        elif path:
            details = build_path_details(path)
        else:
            details = []

    if metadata is None:
        metadata = build_book_metadata(book) if book is not None else (
            {"file_path": path} if path else {}
        )

    if content is None:
        content = read_preview_content(path, max_chars) if (exists and allow_preview) else ""

    view_title = title or (book.title if book is not None else (os.path.basename(path) or ""))
    return BookViewData(
        title=view_title,
        details=details or [],
        content=content or "",
        file_path=path,
        metadata=metadata or {},
        allow_preview=allow_preview and bool(content),
        allow_full_preview=allow_preview and exists,
        allow_view_file=bool(path),
    )


# ---------------------------------------------------------------------- 打开弹窗

def make_book_view_dialog(data: "BookViewData",
                          theme_manager: Optional[ThemeManager] = None,
                          initial_view: str = "details") -> "BookViewDialog":
    """构建统一视图弹窗（调用方自行 push_screen 时使用）。"""
    from src.ui.widgets.book_view_dialog import BookViewDialog
    return BookViewDialog(data, theme_manager, initial_view)


def open_book_view(app: Any, data: "BookViewData",
                   theme_manager: Optional[ThemeManager] = None,
                   initial_view: str = "details") -> "BookViewDialog":
    """打开统一视图弹窗。"""
    dialog = make_book_view_dialog(
        data, theme_manager or get_theme_manager(app), initial_view
    )
    app.push_screen(dialog)
    return dialog


def open_book_view_for_path(app: Any, file_path: str, *,
                            bookshelf: Any = None,
                            theme_manager: Optional[ThemeManager] = None,
                            initial_view: str = "details",
                            title: Optional[str] = None,
                            details: Optional[List[Tuple[str, Any]]] = None,
                            metadata: Optional[Dict[str, Any]] = None,
                            source_getter: Optional[Callable[[str], str]] = None,
                            source: Optional[str] = None,
                            allow_preview: bool = True,
                            max_chars: int = PREVIEW_CHARS,
                            content: Optional[str] = None) -> bool:
    """按文件路径打开统一视图（详情或预览），失败时给出统一提示。"""
    try:
        data = build_view_data(
            file_path,
            title=title,
            details=details,
            metadata=metadata,
            bookshelf=bookshelf,
            source_getter=source_getter,
            source=source,
            allow_preview=allow_preview,
            max_chars=max_chars,
            content=content,
        )
        if data.file_path and not os.path.exists(data.file_path):
            try:
                app.notify(get_global_i18n().t("common.file_not_exist"),
                           severity="warning")
            except Exception:
                pass
        open_book_view(app, data, theme_manager, initial_view)
        return True
    except Exception as e:
        logger.error(f"打开书籍视图失败: {file_path}: {e}")
        try:
            app.notify(f"{get_global_i18n().t('common.action_failed')}: {e}",
                       severity="error")
        except Exception:
            pass
        return False


def open_book_details_for_path(app: Any, file_path: str, **kwargs: Any) -> bool:
    """快捷入口：打开详情视图。"""
    kwargs.pop("initial_view", None)
    return open_book_view_for_path(app, file_path, initial_view="details", **kwargs)


def open_book_preview_for_path(app: Any, file_path: str, **kwargs: Any) -> bool:
    """快捷入口：打开预览视图。"""
    kwargs.pop("initial_view", None)
    return open_book_view_for_path(app, file_path, initial_view="preview", **kwargs)
