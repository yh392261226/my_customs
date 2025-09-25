"""
Markdown文件解析器
"""

import os
import re

from typing import Dict, Any, List

from src.parsers.base_parser import BaseParser

from src.utils.logger import get_logger

logger = get_logger(__name__)

class MarkdownParser(BaseParser):
    """Markdown文件解析器"""
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析Markdown文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        logger.info(f"解析Markdown文件: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取元数据
            metadata = self._extract_markdown_metadata(content)
            
            # 如果没有从内容中提取到标题，使用文件名作为标题
            if "title" not in metadata or not metadata["title"]:
                metadata["title"] = os.path.splitext(os.path.basename(file_path))[0]
            
            # 提取章节
            chapters = self._extract_markdown_chapters(content)
            
            return {
                "content": content,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", "未知作者"),
                "chapters": chapters,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"解析Markdown文件时出错: {e}")
            raise
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".md", ".markdown"]
    
    def _extract_markdown_metadata(self, content: str) -> Dict[str, Any]:
        """
        从Markdown内容中提取元数据
        
        Args:
            content: Markdown内容
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        metadata = {}
        
        # 检查是否有YAML前置元数据
        yaml_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        yaml_match = re.search(yaml_pattern, content, re.DOTALL)
        
        if yaml_match:
            yaml_content = yaml_match.group(1)
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip().lower()] = value.strip()
        
        # 如果没有YAML前置元数据，尝试从内容中提取
        if not metadata:
            # 尝试从一级标题中提取标题
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if title_match:
                metadata["title"] = title_match.group(1).strip()
            
            # 尝试查找作者信息
            author_match = re.search(r"(?:作者|author)[：:]\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
            if author_match:
                metadata["author"] = author_match.group(1).strip()
        
        return metadata
    
    def _extract_markdown_chapters(self, content: str) -> List[Dict[str, Any]]:
        """
        从Markdown内容中提取章节
        
        Args:
            content: Markdown内容
            
        Returns:
            List[Dict[str, Any]]: 章节列表
        """
        chapters = []
        
        # 移除YAML前置元数据
        yaml_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        content = re.sub(yaml_pattern, "", content, flags=re.DOTALL)
        
        # 使用标题作为章节分隔
        # 查找所有的一级和二级标题
        headers = re.finditer(r"^(#{1,2})\s+(.+)$", content, re.MULTILINE)
        
        last_pos = 0
        current_chapter = {"title": "未命名章节", "content": ""}
        
        for match in headers:
            header_level = len(match.group(1))
            header_text = match.group(2).strip()
            header_pos = match.start()
            
            # 如果已经有章节内容，保存当前章节
            if last_pos > 0:
                current_chapter["content"] = content[last_pos:header_pos].strip()
                chapters.append(current_chapter.copy())
            
            # 创建新章节
            current_chapter = {"title": header_text, "content": ""}
            last_pos = header_pos
        
        # 添加最后一个章节
        if last_pos < len(content):
            current_chapter["content"] = content[last_pos:].strip()
            chapters.append(current_chapter)
        
        # 如果没有找到章节，将整个内容作为一个章节
        if not chapters:
            chapters = [{"title": "全文", "content": content}]
        
        return chapters