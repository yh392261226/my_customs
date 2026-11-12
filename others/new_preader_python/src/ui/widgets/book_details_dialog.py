"""兼容导入层：书籍详情 / 预览 / 查看文件已统一到 ``book_view_dialog``。

新代码请直接使用::

    from src.ui.widgets.book_view_dialog import BookViewDialog, BookViewData
    from src.ui.utils.book_view_utils import open_book_view_for_path

本模块仅保留旧的导入路径，避免历史引用失效；实现不再放在这里。
"""
from src.ui.widgets.book_view_dialog import (
    BookDetailsDialog,
    BookPreviewDialog,
    BookViewData,
    BookViewDialog,
)

__all__ = ["BookDetailsDialog", "BookPreviewDialog", "BookViewData", "BookViewDialog"]
