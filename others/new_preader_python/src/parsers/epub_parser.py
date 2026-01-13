"""
EPUB文件解析器
"""

import os

import re
from typing import Dict, Any, List
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from src.parsers.base_parser import BaseParser

from src.utils.logger import get_logger

logger = get_logger(__name__)

class EpubParser(BaseParser):
    """EPUB文件解析器"""
    
    async def parse(self, file_path: str, parsing_context: Optional[ParsingContext] = None) -> Dict[str, Any]:
        """
        解析EPUB文件

        Args:
            file_path: 文件路径
            parsing_context: 解析上下文，包含进度回调等信息

        Returns:
            Dict[str, Any]: 解析结果
        """
        # 为了保持向后兼容，如果parsing_context为None，创建一个默认的
        if parsing_context is None:
            from .progress_callback import ParsingContext
            parsing_context = ParsingContext()

        logger.info(f"解析EPUB文件: {file_path}")

        try:
            # 使用ebooklib解析EPUB文件
            book = epub.read_epub(file_path)

            # 提取元数据
            metadata = self._extract_epub_metadata(book)

            # 如果没有从内容中提取到标题，使用文件名作为标题
            if "title" not in metadata or not metadata["title"]:
                metadata["title"] = os.path.splitext(os.path.basename(file_path))[0]

            # 提取章节和内容
            chapters, content = self._extract_epub_content(book, parsing_context)

            return {
                "content": content,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", "未知作者"),
                "chapters": chapters,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"解析EPUB文件时出错: {e}")
            raise

    def _extract_epub_content(self, book: epub.EpubBook, parsing_context: ParsingContext) -> tuple:
        """
        从EPUB书籍中提取章节和内容

        Args:
            book: EPUB书籍对象
            parsing_context: 解析上下文

        Returns:
            tuple: (章节列表, 完整内容)
        """
        chapters = []
        full_content = ""

        # 获取书籍的线性阅读顺序
        spine = book.spine
        items = []

        for item_id, _ in spine:
            item = book.get_item_with_id(item_id)
            if item is not None:
                items.append(item)

        # 如果没有线性阅读顺序，则使用所有HTML文档
        if not items:
            items = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]

        # 处理每个文档
        for i, item in enumerate(items):
            try:
                # 检查是否需要取消解析
                if parsing_context.cancel_requested or parsing_context.check_timeout():
                    logger.info("EPUB解析被取消或超时")
                    break

                # 更新进度 - 在同步方法中需要特别处理
                try:
                    if parsing_context.progress_callback:
                        # 检查回调是否是异步的
                        if hasattr(parsing_context.progress_callback, 'on_progress'):
                            import asyncio
                            if asyncio.iscoroutinefunction(parsing_context.progress_callback.on_progress):
                                # 如果是异步回调，需要特殊处理，这里简化处理
                                should_continue = parsing_context.progress_callback.on_progress(i + 1, len(items), f"处理章节 {i+1}/{len(items)}")
                            else:
                                should_continue = parsing_context.progress_callback.on_progress(i + 1, len(items), f"处理章节 {i+1}/{len(items)}")
                        else:
                            should_continue = True
                    else:
                        should_continue = True

                    if not should_continue:
                        logger.info("EPUB解析被用户取消")
                        break
                except Exception:
                    # 如果进度回调出错，继续解析
                    pass

                # 获取内容并检查是否为HTML文档
                content = item.get_content()
                if not content:
                    continue

                # 确保内容是文本格式
                if isinstance(content, bytes):
                    try:
                        # 检查是否为二进制文件（如图片、字体等）
                        if content.startswith(b'PK') or content.startswith(b'\x89PNG') or content.startswith(b'\xff\xd8\xff'):
                            # 跳过二进制文件
                            continue
                        content = content.decode('utf-8', errors='ignore')
                    except:
                        logger.warning(f"无法解码EPUB章节内容: {item.get_name()}")
                        continue

                # 再次检查解码后的内容是否包含二进制数据
                if isinstance(content, str):
                    # 检查是否包含大量不可打印字符（可能是二进制数据）
                    printable_chars = sum(1 for c in content[:1000] if c.isprintable() or c.isspace())
                    if len(content) > 100 and printable_chars / min(len(content), 1000) < 0.7:
                        # 如果可打印字符比例低于70%，可能是二进制数据
                        continue

                # 检查是否为HTML内容
                if not any(tag in content.lower() for tag in ['<html', '<body', '<p', '<div']):
                    # 如果不是HTML内容，跳过
                    continue

                # 解析HTML内容
                soup = BeautifulSoup(content, 'html.parser')

                # 移除脚本和样式标签
                for script in soup(["script", "style"]):
                    script.decompose()

                # 提取文本内容
                text = soup.get_text(separator='\n', strip=True)
                text = re.sub(r'\n\s*\n', '\n\n', text)  # 规范化换行
                text = self._clean_text_content(text)  # 进一步清理

                # 如果提取的文本为空或太短，跳过
                if not text or len(text.strip()) < 10:
                    continue

                # 尝试提取标题
                title = ""
                title_tag = soup.find(['h1', 'h2', 'h3', 'title'])
                if title_tag:
                    title = title_tag.get_text().strip()

                if not title:
                    # 尝试从文件名提取标题
                    item_name = item.get_name() if hasattr(item, 'get_name') else f"chapter_{i+1}"
                    title = item_name.replace('.html', '').replace('.xhtml', '').replace('_', ' ')
                    if not title or len(title) < 2:
                        title = f"章节 {i+1}"

                # 添加章节
                chapters.append({
                    "title": title,
                    "content": text
                })

                # 添加到完整内容
                full_content += text + "\n\n"

            except Exception as e:
                logger.warning(f"处理EPUB章节时出错: {e}")
                continue

        # 最终验证：确保返回的内容是纯文本
        full_content = self._ensure_pure_text(full_content)
        for chapter in chapters:
            if chapter.get('content'):
                chapter['content'] = self._ensure_pure_text(chapter['content'])

        return chapters, full_content
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".epub"]
    
    def _extract_epub_metadata(self, book: epub.EpubBook) -> Dict[str, Any]:
        """
        从EPUB书籍中提取元数据
        
        Args:
            book: EPUB书籍对象
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        metadata = {}
        
        # 提取标题
        if book.get_metadata('DC', 'title'):
            metadata["title"] = book.get_metadata('DC', 'title')[0][0]
        
        # 提取作者
        if book.get_metadata('DC', 'creator'):
            metadata["author"] = book.get_metadata('DC', 'creator')[0][0]
        
        # 提取语言
        if book.get_metadata('DC', 'language'):
            metadata["language"] = book.get_metadata('DC', 'language')[0][0]
        
        # 提取出版商
        if book.get_metadata('DC', 'publisher'):
            metadata["publisher"] = book.get_metadata('DC', 'publisher')[0][0]
        
        # 提取出版日期
        if book.get_metadata('DC', 'date'):
            metadata["date"] = book.get_metadata('DC', 'date')[0][0]
        
        # 提取描述
        if book.get_metadata('DC', 'description'):
            metadata["description"] = book.get_metadata('DC', 'description')[0][0]
        
        return metadata
    
    def _extract_epub_content(self, book: epub.EpubBook) -> tuple:
        """
        从EPUB书籍中提取章节和内容
        
        Args:
            book: EPUB书籍对象
            
        Returns:
            tuple: (章节列表, 完整内容)
        """
        chapters = []
        full_content = ""
        
        # 获取书籍的线性阅读顺序
        spine = book.spine
        items = []
        
        for item_id, _ in spine:
            item = book.get_item_with_id(item_id)
            if item is not None:
                items.append(item)
        
        # 如果没有线性阅读顺序，则使用所有HTML文档
        if not items:
            items = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
        
        # 处理每个文档
        for i, item in enumerate(items):
            try:
                # 获取内容并检查是否为HTML文档
                content = item.get_content()
                if not content:
                    continue
                
                # 确保内容是文本格式
                if isinstance(content, bytes):
                    try:
                        # 检查是否为二进制文件（如图片、字体等）
                        if content.startswith(b'PK') or content.startswith(b'\x89PNG') or content.startswith(b'\xff\xd8\xff'):
                            # 跳过二进制文件
                            continue
                        content = content.decode('utf-8', errors='ignore')
                    except:
                        logger.warning(f"无法解码EPUB章节内容: {item.get_name()}")
                        continue
                
                # 再次检查解码后的内容是否包含二进制数据
                if isinstance(content, str):
                    # 检查是否包含大量不可打印字符（可能是二进制数据）
                    printable_chars = sum(1 for c in content[:1000] if c.isprintable() or c.isspace())
                    if len(content) > 100 and printable_chars / min(len(content), 1000) < 0.7:
                        # 如果可打印字符比例低于70%，可能是二进制数据
                        continue
                
                # 检查是否为HTML内容
                if not any(tag in content.lower() for tag in ['<html', '<body', '<p', '<div']):
                    # 如果不是HTML内容，跳过
                    continue
                
                # 解析HTML内容
                soup = BeautifulSoup(content, 'html.parser')
                
                # 移除脚本和样式标签
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # 提取文本内容
                text = soup.get_text(separator='\n', strip=True)
                text = re.sub(r'\n\s*\n', '\n\n', text)  # 规范化换行
                text = self._clean_text_content(text)  # 进一步清理
                
                # 如果提取的文本为空或太短，跳过
                if not text or len(text.strip()) < 10:
                    continue
                
                # 尝试提取标题
                title = ""
                title_tag = soup.find(['h1', 'h2', 'h3', 'title'])
                if title_tag:
                    title = title_tag.get_text().strip()
                
                if not title:
                    # 尝试从文件名提取标题
                    item_name = item.get_name() if hasattr(item, 'get_name') else f"chapter_{i+1}"
                    title = item_name.replace('.html', '').replace('.xhtml', '').replace('_', ' ')
                    if not title or len(title) < 2:
                        title = f"章节 {i+1}"
                
                # 添加章节
                chapters.append({
                    "title": title,
                    "content": text
                })
                
                # 添加到完整内容
                full_content += text + "\n\n"
                
            except Exception as e:
                logger.warning(f"处理EPUB章节时出错: {e}")
                continue
        
        # 最终验证：确保返回的内容是纯文本
        full_content = self._ensure_pure_text(full_content)
        for chapter in chapters:
            if chapter.get('content'):
                chapter['content'] = self._ensure_pure_text(chapter['content'])
        
        return chapters, full_content
    
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
    
    def _ensure_pure_text(self, content: str) -> str:
        """
        确保内容是纯文本，过滤掉任何二进制数据
        
        Args:
            content: 输入内容
            
        Returns:
            str: 纯文本内容
        """
        if not content:
            return ""
        
        # 如果不是字符串，尝试转换
        if not isinstance(content, str):
            try:
                if isinstance(content, bytes):
                    # 检查是否为二进制文件
                    if content.startswith(b'PK') or content.startswith(b'\x89PNG') or content.startswith(b'\xff\xd8\xff'):
                        return ""
                    content = content.decode('utf-8', errors='ignore')
                else:
                    content = str(content)
            except:
                return ""
        
        # 过滤掉不可打印的字符（保留常见的空白字符）
        filtered_chars = []
        for char in content:
            if char.isprintable() or char in '\n\r\t ':
                filtered_chars.append(char)
            elif ord(char) < 32 and char not in '\n\r\t':
                # 跳过控制字符
                continue
            else:
                filtered_chars.append(char)
        
        content = ''.join(filtered_chars)
        
        # 检查内容质量
        if len(content) > 100:
            printable_ratio = sum(1 for c in content[:1000] if c.isprintable() or c.isspace()) / min(len(content), 1000)
            if printable_ratio < 0.8:
                # 如果可打印字符比例太低，可能是损坏的数据
                return ""
        
        # 最终清理
        content = self._clean_text_content(content)
        
        return content