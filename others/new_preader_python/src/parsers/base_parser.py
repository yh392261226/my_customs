"""
基础解析器模块，定义解析器接口
"""


from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import asyncio

from src.utils.logger import get_logger
from .progress_callback import ParsingContext, ProgressCallback

logger = get_logger(__name__)

class BaseParser(ABC):
    """基础解析器抽象类，定义解析器接口"""

    @abstractmethod
    async def parse(self, file_path: str, parsing_context: Optional[ParsingContext] = None) -> Dict[str, Any]:
        """
        解析文件

        Args:
            file_path: 文件路径
            parsing_context: 解析上下文，包含进度回调等信息

        Returns:
            Dict[str, Any]: 解析结果，包含以下字段：
                - content: 文本内容
                - title: 标题
                - author: 作者
                - chapters: 章节列表
                - metadata: 元数据
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式

        Returns:
            List[str]: 支持的文件格式列表
        """
        pass

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        从内容中提取元数据

        Args:
            content: 文本内容

        Returns:
            Dict[str, Any]: 元数据字典
        """
        metadata = {}

        # 尝试提取标题和作者
        lines = content.split('\n')
        if lines:
            # 假设第一行可能是标题
            metadata["title"] = lines[0].strip()

            # 尝试查找作者信息
            for i in range(1, min(10, len(lines))):
                line = lines[i].lower()
                if "作者" in line or "author" in line:
                    parts = line.replace("作者", "").replace("author", "").replace(":", "").replace("：", "").strip()
                    if parts:
                        metadata["author"] = parts
                        break

        return metadata

    def extract_chapters(self, content: str) -> List[Dict[str, Any]]:
        """
        从内容中提取章节

        Args:
            content: 文本内容

        Returns:
            List[Dict[str, Any]]: 章节列表，每个章节包含标题和内容
        """
        chapters = []

        # 简单的章节提取逻辑
        lines = content.split('\n')
        current_chapter = {"title": "未命名章节", "content": ""}
        chapter_started = False

        for line in lines:
            # 检查是否是章节标题
            if (line.strip().startswith("第") and ("章" in line or "节" in line)) or \
               (line.strip().startswith("Chapter") or line.strip().startswith("CHAPTER")):
                # 如果已经有章节内容，保存当前章节
                if chapter_started and current_chapter["content"]:
                    chapters.append(current_chapter.copy())

                # 创建新章节
                current_chapter = {"title": line.strip(), "content": ""}
                chapter_started = True
            elif chapter_started:
                # 添加内容到当前章节
                current_chapter["content"] += line + "\n"
            else:
                # 如果还没有找到章节标题，将内容添加到第一个未命名章节
                current_chapter["content"] += line + "\n"

        # 添加最后一个章节
        if current_chapter["content"]:
            chapters.append(current_chapter)

        # 如果没有找到章节，将整个内容作为一个章节
        if not chapters:
            chapters = [{"title": "全文", "content": content}]

        return chapters

    async def parse_incremental(self, file_path: str,
                               parsing_context: Optional[ParsingContext] = None,
                               chunk_callback=None) -> Dict[str, Any]:
        """
        增量解析文件，适用于大文件

        Args:
            file_path: 文件路径
            parsing_context: 解析上下文
            chunk_callback: 每个数据块的回调函数

        Returns:
            Dict[str, Any]: 解析结果
        """
        # 默认实现：调用常规解析方法
        return await self.parse(file_path, parsing_context)