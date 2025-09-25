"""
AZW/AZW3文件解析器 - 使用KindleUnpack库专门处理AZW文件
"""

import os

import re
import tempfile
import shutil
from typing import Dict, Any, List

from src.parsers.base_parser import BaseParser
from src.parsers.kindle_unpack_wrapper import kindle_unpack_wrapper

from src.utils.logger import get_logger

logger = get_logger(__name__)

class AzwParser(BaseParser):
    """AZW/AZW3文件解析器 - 使用KindleUnpack库"""
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析AZW/AZW3文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        logger.info(f"解析AZW/AZW3文件: {file_path}")
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="azw_unpack_")
        
        try:
            # 优先使用KindleUnpack库
            if kindle_unpack_wrapper.is_available():
                logger.info("使用KindleUnpack库解析AZW文件")
                result = kindle_unpack_wrapper.unpack_azw(file_path, temp_dir)
                
                # 确保分页和内容完整性
                result = self._ensure_content_integrity(result)
                return result
            else:
                # 如果KindleUnpack不可用，尝试其他方法
                logger.warning("KindleUnpack库不可用，尝试备用方法")
                return await self._fallback_parse(file_path, temp_dir)
                
        except Exception as e:
            logger.error(f"解析AZW/AZW3文件时出错: {e}")
            
            # 尝试备用解析方法
            try:
                return await self._fallback_parse(file_path, temp_dir)
            except Exception as fallback_error:
                logger.error(f"备用解析方法也失败: {fallback_error}")
                
                # 返回基本错误信息
                metadata = {"title": os.path.splitext(os.path.basename(file_path))[0]}
                return {
                    "content": f"无法解析此AZW/AZW3文件。\n错误信息: {str(e)}",
                    "title": metadata.get("title", ""),
                    "author": "未知作者",
                    "chapters": [{"title": "全文", "content": f"无法解析此AZW/AZW3文件。\n错误信息: {str(e)}"}],
                    "metadata": metadata
                }
        finally:
            # 清理临时文件
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    async def _fallback_parse(self, file_path: str, temp_dir: str) -> Dict[str, Any]:
        """
        备用解析方法
        
        Args:
            file_path: 文件路径
            temp_dir: 临时目录
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        import subprocess
        
        # 方法1: 尝试使用calibre的ebook-convert工具
        try:
            epub_path = os.path.join(temp_dir, os.path.basename(file_path) + ".epub")
            
            subprocess.run(["ebook-convert", file_path, epub_path], 
                          check=True, capture_output=True, text=True)
            
            if os.path.exists(epub_path):
                from src.parsers.epub_parser import EpubParser
                epub_parser = EpubParser()
                result = await epub_parser.parse(epub_path)
                result = self._ensure_content_integrity(result)
                return result
            else:
                raise FileNotFoundError(f"转换后的EPUB文件不存在: {epub_path}")
                
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.warning(f"使用calibre转换AZW/AZW3文件失败: {e}")
        
        # 方法2: 尝试使用MOBI解析器
        try:
            from src.parsers.mobi_parser import MobiParser
            mobi_parser = MobiParser()
            result = await mobi_parser.parse(file_path)
            result = self._ensure_content_integrity(result)
            return result
        except Exception as e:
            logger.warning(f"使用MOBI解析器解析AZW文件失败: {e}")
            raise
    
    def _ensure_content_integrity(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保内容完整性和分页兼容性
        
        Args:
            result: 解析结果
            
        Returns:
            Dict[str, Any]: 处理后的结果
        """
        # 清理内容
        if result.get("content"):
            result["content"] = self._clean_text_content(result["content"])
        
        # 清理章节内容
        if result.get("chapters"):
            for chapter in result["chapters"]:
                if chapter.get("content"):
                    chapter["content"] = self._clean_text_content(chapter["content"])
        
        # 确保内容不为空
        if not result.get("content"):
            if result.get("chapters"):
                # 从章节重建完整内容
                content_parts = []
                for chapter in result["chapters"]:
                    if chapter.get("content"):
                        content_parts.append(chapter["content"])
                result["content"] = "\n\n".join(content_parts)
            else:
                result["content"] = "文件内容为空"
        
        # 确保章节列表不为空
        if not result.get("chapters"):
            result["chapters"] = [{"title": "全文", "content": result.get("content", "")}]
        
        # 验证章节内容完整性
        total_chapter_length = sum(len(chapter.get("content", "")) for chapter in result["chapters"])
        main_content_length = len(result.get("content", ""))
        
        # 如果章节内容总长度与主内容长度差异过大，重新构建章节
        if abs(total_chapter_length - main_content_length) > main_content_length * 0.1:
            logger.warning("检测到章节内容不完整，重新构建章节")
            result["chapters"] = self._rebuild_chapters(result["content"])
        
        # 确保标题和作者信息
        if not result.get("title"):
            result["title"] = "AZW文档"
        
        if not result.get("author"):
            result["author"] = "未知作者"
        
        return result
    
    def _rebuild_chapters(self, content: str) -> List[Dict[str, Any]]:
        """
        重新构建章节
        
        Args:
            content: 完整内容
            
        Returns:
            List[Dict[str, Any]]: 章节列表
        """
        if not content:
            return [{"title": "全文", "content": ""}]
        
        # 使用基类的章节提取方法
        chapters = self.extract_chapters(content)
        
        # 如果没有找到章节，将内容按段落分割
        if len(chapters) == 1 and chapters[0]["title"] == "未命名章节":
            paragraphs = content.split('\n\n')
            if len(paragraphs) > 10:  # 如果段落较多，尝试按段落分组
                chapter_size = max(5, len(paragraphs) // 10)  # 每章包含5-10个段落
                chapters = []
                for i in range(0, len(paragraphs), chapter_size):
                    chapter_paragraphs = paragraphs[i:i+chapter_size]
                    chapter_content = '\n\n'.join(chapter_paragraphs)
                    chapters.append({
                        "title": f"第{i//chapter_size + 1}部分",
                        "content": chapter_content
                    })
        
        return chapters
    
    def _clean_text_content(self, content: str) -> str:
        """
        彻底清理文本内容，确保返回纯文本
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清理后的纯文本内容
        """
        if not content:
            return ""
        
        # 移除残留的HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除HTML实体
        import html
        content = html.unescape(content)
        
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 规范化换行
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # 移除行首行尾空白
        lines = content.split('\n')
        lines = [line.strip() for line in lines]
        content = '\n'.join(lines)
        
        # 移除多余的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".azw", ".azw3"]