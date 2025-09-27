"""
UI 消息定义
"""

from __future__ import annotations

from typing import Optional
import asyncio
from textual.message import Message


class RefreshBookshelfMessage(Message):
    """刷新书架消息"""
    def __init__(self) -> None:
        super().__init__()


class RequestPasswordMessage(Message):
    """
    解析线程请求在主线程显示密码输入对话框
    - file_path: 需要输入密码的 PDF 路径（用于展示）
    - max_attempts: 最大尝试次数（UI 可用）
    - future: 主线程获得结果后 set_result 到该 Future；结果为密码或 None
    """
    def __init__(self, file_path: str, max_attempts: int, future: asyncio.Future[Optional[str]]) -> None:
        super().__init__()
        self.file_path = file_path
        self.max_attempts = max_attempts
        self.future = future


class RefreshContentMessage(Message):
    """刷新内容显示消息"""
    def __init__(self) -> None:
        super().__init__()


class CrawlCompleteNotification(Message):
    """爬取完成通知消息"""
    def __init__(self, success: bool, novel_title: str, message: str = "") -> None:
        super().__init__()
        self.success = success
        self.novel_title = novel_title
        self.message = message