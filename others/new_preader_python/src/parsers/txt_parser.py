"""
TXT文件解析器
"""

import os

from typing import Dict, Any, List

from src.parsers.base_parser import BaseParser

from src.utils.logger import get_logger

logger = get_logger(__name__)

class TxtParser(BaseParser):
    """TXT文件解析器"""
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析TXT文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        logger.info(f"解析TXT文件: {file_path}")
        
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                logger.error(f"无法解码文件: {file_path}")
                raise ValueError(f"无法解码文件: {file_path}")
            
            # 提取元数据
            metadata = self.extract_metadata(content)
            
            # 如果没有从内容中提取到标题，使用文件名作为标题
            if "title" not in metadata or not metadata["title"]:
                metadata["title"] = os.path.splitext(os.path.basename(file_path))[0]
            
            # 提取章节
            chapters = self.extract_chapters(content)
            
            return {
                "content": content,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", "未知作者"),
                "chapters": chapters,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"解析TXT文件时出错: {e}")
            raise
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".txt"]