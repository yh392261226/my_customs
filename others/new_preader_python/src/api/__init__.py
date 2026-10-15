"""
后端数据接口包（api）

提供书库 / 书籍网站 / 爬取管理 的带分页、带搜索的 REST 接口，
以及 补缺 / 合并 / 批量操作 等操作接口。每个接口均支持数据的上传(POST/PUT)
与下拉(GET)，便于浏览器阅读器接入。

实现采用标准库 http.server，无需额外依赖。
"""

from .server import start_api_server, get_api_base_url, set_open_book_callback  # noqa: F401

__all__ = ["start_api_server", "get_api_base_url", "set_open_book_callback"]
