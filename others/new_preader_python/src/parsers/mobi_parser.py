"""
MOBI文件解析器
"""

import os

import re
from typing import Dict, Any, List
try:
    import mobi
    MOBI_AVAILABLE = True
except ImportError:
    MOBI_AVAILABLE = False
    logger.warning("mobi库未安装，MOBI文件解析功能将受限")

from bs4 import BeautifulSoup
from src.parsers.base_parser import BaseParser

from src.utils.logger import get_logger

logger = get_logger(__name__)

class MobiParser(BaseParser):
    """MOBI文件解析器"""
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析MOBI文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        logger.info(f"解析MOBI文件: {file_path}")
        
        if not MOBI_AVAILABLE:
            raise ImportError("mobi库未安装，无法解析MOBI文件。请运行: pip install mobi")
        
        tempdir = None
        try:
            # 创建临时目录
            tempdir = os.path.join(os.path.dirname(file_path), ".temp_mobi")
            os.makedirs(tempdir, exist_ok=True)
            
            # 使用mobi库的extract函数解析MOBI文件
            from mobi import extract
            
            # 提取MOBI文件内容
            extracted_data = extract(file_path)
            
            # 提取元数据
            metadata = self._extract_mobi_metadata_from_extracted(extracted_data)
            
            # 如果没有从内容中提取到标题，使用文件名作为标题
            if "title" not in metadata or not metadata["title"]:
                metadata["title"] = os.path.splitext(os.path.basename(file_path))[0]
            
            # 提取内容和章节
            content, chapters = self._extract_mobi_content_from_extracted(extracted_data)
            
            return {
                "content": content,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", "未知作者"),
                "chapters": chapters,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"解析MOBI文件时出错: {e}")
            raise
        finally:
            # 清理临时文件
            if tempdir and os.path.exists(tempdir):
                import shutil
                shutil.rmtree(tempdir, ignore_errors=True)
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".mobi"]
    
    def _extract_mobi_metadata_from_extracted(self, extracted_data) -> Dict[str, Any]:
        """
        从提取的MOBI数据中提取元数据
        
        Args:
            extracted_data: 提取的MOBI数据
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        metadata = {}
        
        # 尝试从提取的数据中获取元数据
        if hasattr(extracted_data, 'title') and extracted_data.title:
            metadata["title"] = extracted_data.title
        
        if hasattr(extracted_data, 'author') and extracted_data.author:
            metadata["author"] = extracted_data.author
        
        if hasattr(extracted_data, 'publisher') and extracted_data.publisher:
            metadata["publisher"] = extracted_data.publisher
        
        return metadata
    
    def _extract_mobi_content_from_extracted(self, extracted_data) -> tuple:
        """
        从MOBI书籍中提取内容和章节，严格注意章节顺序
        
        Args:
            extracted_data: MOBI提取数据（通常是包含路径的元组）
            
        Returns:
            tuple: (完整内容, 章节列表)
        """
        chapters = []
        full_content = ""
        
        try:
            # extracted_data通常是一个包含路径的元组
            if isinstance(extracted_data, tuple) and len(extracted_data) >= 2:
                # 第二个元素通常是EPUB文件路径
                epub_path = extracted_data[1]
                if os.path.exists(epub_path) and epub_path.endswith('.epub'):
                    # 使用EPUB解析器处理转换后的文件
                    from src.parsers.epub_parser import EpubParser
                    epub_parser = EpubParser()
                    try:
                        import asyncio
                        # 检查是否已经在事件循环中
                        try:
                            loop = asyncio.get_running_loop()
                            # 如果已经在事件循环中，创建新的任务
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, epub_parser.parse(epub_path))
                                epub_result = future.result()
                        except RuntimeError:
                            # 如果没有运行的事件循环，直接运行
                            epub_result = asyncio.run(epub_parser.parse(epub_path))
                        
                        return epub_result.get('content', ''), epub_result.get('chapters', [])
                    except Exception as e:
                        logger.warning(f"使用EPUB解析器处理MOBI转换文件时出错: {e}")
                        # 继续使用目录提取方法
                
                # 如果第一个元素是目录路径，查找HTML文件
                extract_dir = extracted_data[0]
                if os.path.exists(extract_dir):
                    return self._extract_from_directory(extract_dir)
            
            # 尝试获取HTML内容（备用方法）
            if hasattr(extracted_data, 'text'):
                raw_content = extracted_data.text
            elif hasattr(extracted_data, 'content'):
                raw_content = extracted_data.content
            else:
                raw_content = str(extracted_data) if extracted_data else ""
            
            # 检查是否为HTML格式并进行彻底清理
            if raw_content and ("<html" in raw_content.lower() or "<body" in raw_content.lower() or "<p>" in raw_content.lower()):
                # 使用BeautifulSoup解析HTML并提取纯文本
                soup = BeautifulSoup(raw_content, 'html.parser')
                
                # 移除脚本和样式标签
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # 查找章节标记
                chapter_elements = self._find_chapter_elements(soup)
                
                if chapter_elements:
                    # 按照在文档中的顺序处理章节
                    for i, element in enumerate(chapter_elements):
                        chapter_title = self._extract_chapter_title(element)
                        chapter_content = self._extract_chapter_content(element, soup, i, chapter_elements)
                        
                        # 从HTML中提取纯文本
                        if chapter_content:
                            chapter_soup = BeautifulSoup(chapter_content, 'html.parser')
                            # 移除脚本和样式
                            for script in chapter_soup(["script", "style"]):
                                script.decompose()
                            clean_content = chapter_soup.get_text(separator='\n', strip=True)
                            clean_content = re.sub(r'\n\s*\n', '\n\n', clean_content)  # 规范化换行
                            clean_content = self._clean_text_content(clean_content)  # 进一步清理
                            
                            chapters.append({
                                "title": chapter_title,
                                "content": clean_content
                            })
                            
                            full_content += clean_content + "\n\n"
                else:
                    # 如果没有找到明确的章节标记，提取整个文本内容
                    full_content = soup.get_text(separator='\n', strip=True)
                    full_content = re.sub(r'\n\s*\n', '\n\n', full_content)
                    full_content = self._clean_text_content(full_content)  # 进一步清理
                    
                    # 尝试基于文本内容分析章节
                    chapters = self._extract_text_chapters(full_content)
            else:
                # 纯文本内容，也需要清理
                full_content = self._clean_text_content(raw_content)
                chapters = self._extract_text_chapters(full_content)
                
        except Exception as e:
            logger.warning(f"提取MOBI章节时出错: {e}")
            # 回退到简单的文本处理
            if hasattr(extracted_data, 'text'):
                full_content = extracted_data.text
            elif hasattr(extracted_data, 'content'):
                full_content = extracted_data.content
            else:
                full_content = str(extracted_data) if extracted_data else ""
            chapters = self._extract_text_chapters(full_content)
        
        return full_content, chapters
    
    def _find_chapter_elements(self, soup: BeautifulSoup) -> List:
        """查找章节元素"""
        chapter_elements = []
        
        # 查找常见的章节标记
        # 1. 标题标签 (h1, h2, h3)
        for tag in ['h1', 'h2', 'h3']:
            elements = soup.find_all(tag)
            for element in elements:
                text = element.get_text().strip()
                if self._is_chapter_title(text):
                    chapter_elements.append(element)
        
        # 2. 包含章节关键词的div或p标签
        for tag in ['div', 'p']:
            elements = soup.find_all(tag)
            for element in elements:
                text = element.get_text().strip()
                if self._is_chapter_title(text) and len(text) < 100:  # 标题通常较短
                    chapter_elements.append(element)
        
        # 按在文档中的出现顺序排序
        chapter_elements.sort(key=lambda x: list(soup.descendants).index(x))
        
        return chapter_elements
    
    def _is_chapter_title(self, text: str) -> bool:
        """判断文本是否为章节标题"""
        if not text:
            return False
        
        # 章节标题模式
        patterns = [
            r"第\s*\d+\s*章",  # 第X章
            r"Chapter\s*\d+",  # Chapter X
            r"CHAPTER\s*\d+",  # CHAPTER X
            r"第\s*[一二三四五六七八九十百千万]+\s*章",  # 第X章（中文数字）
            r"卷\s*\d+",  # 卷X
            r"Part\s*\d+",  # Part X
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_chapter_title(self, element) -> str:
        """提取章节标题"""
        title = element.get_text().strip()
        # 清理标题，移除多余的空白字符
        title = re.sub(r'\s+', ' ', title)
        return title if title else "未命名章节"
    
    def _extract_chapter_content(self, chapter_element, soup: BeautifulSoup, 
                               chapter_index: int, all_chapters: List) -> str:
        """提取章节内容"""
        content_parts = []
        
        # 获取当前章节元素之后的所有兄弟元素
        current = chapter_element.next_sibling
        
        # 确定章节结束位置
        next_chapter = all_chapters[chapter_index + 1] if chapter_index + 1 < len(all_chapters) else None
        
        while current:
            if current == next_chapter:
                break
            
            if hasattr(current, 'get_text'):
                text = current.get_text().strip()
                if text:
                    content_parts.append(str(current))
            
            current = current.next_sibling
        
        return '\n'.join(content_parts)
    
    def _extract_text_chapters(self, content: str) -> List[Dict[str, Any]]:
        """从纯文本中提取章节"""
        chapters = []
        
        # 使用正则表达式查找章节标题
        chapter_patterns = [
            r"第\s*(\d+)\s*章\s*([^\n]*)",  # 第X章
            r"Chapter\s*(\d+)\s*[:\.\s]*([^\n]*)",  # Chapter X
            r"CHAPTER\s*(\d+)\s*[:\.\s]*([^\n]*)",  # CHAPTER X
            r"第\s*([一二三四五六七八九十百千万]+)\s*章\s*([^\n]*)",  # 第X章（中文数字）
        ]
        
        # 存储所有匹配到的章节位置
        chapter_positions = []
        
        for pattern in chapter_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                chapter_num = match.group(1)
                chapter_title = match.group(2).strip() if len(match.groups()) > 1 else ""
                position = match.start()
                full_title = match.group(0).strip()
                
                if not chapter_title:
                    chapter_title = full_title
                else:
                    chapter_title = f"第{chapter_num}章 {chapter_title}"
                
                chapter_positions.append((position, chapter_title))
        
        # 按位置排序章节，确保顺序正确
        chapter_positions.sort(key=lambda x: x[0])
        
        # 根据章节位置分割内容
        if chapter_positions:
            for i in range(len(chapter_positions)):
                start_pos = chapter_positions[i][0]
                title = chapter_positions[i][1]
                
                # 确定章节结束位置
                if i < len(chapter_positions) - 1:
                    end_pos = chapter_positions[i+1][0]
                else:
                    end_pos = len(content)
                
                # 提取章节内容
                chapter_content = content[start_pos:end_pos].strip()
                
                chapters.append({
                    "title": title,
                    "content": chapter_content
                })
        else:
            # 如果没有找到章节，将整个内容作为一个章节
            chapters = [{"title": "全文", "content": content}]
        
        return chapters
    
    def _extract_from_directory(self, extract_dir: str) -> tuple:
        """
        从解包目录中提取内容
        
        Args:
            extract_dir: 解包目录路径
            
        Returns:
            tuple: (完整内容, 章节列表)
        """
        chapters = []
        full_content = ""
        
        try:
            # 查找HTML文件
            html_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith(('.html', '.htm', '.xhtml')):
                        html_files.append(os.path.join(root, file))
            
            # 按文件名排序，确保章节顺序正确
            html_files.sort()
            
            if html_files:
                for i, html_file in enumerate(html_files):
                    try:
                        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                            html_content = f.read()
                        
                        if html_content.strip():
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # 移除脚本和样式标签
                            for script in soup(["script", "style"]):
                                script.decompose()
                            
                            # 提取纯文本
                            text_content = soup.get_text(separator='\n', strip=True)
                            text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
                            text_content = self._clean_text_content(text_content)
                            
                            if text_content.strip():
                                # 尝试提取章节标题
                                chapter_title = self._extract_chapter_title_from_file(soup, html_file, i)
                                
                                chapters.append({
                                    "title": chapter_title,
                                    "content": text_content
                                })
                                
                                full_content += text_content + "\n\n"
                    
                    except Exception as e:
                        logger.warning(f"处理HTML文件时出错 {html_file}: {e}")
                        continue
            
            # 如果没有找到HTML文件，查找文本文件
            if not full_content:
                txt_files = []
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith('.txt'):
                            txt_files.append(os.path.join(root, file))
                
                txt_files.sort()
                
                for i, txt_file in enumerate(txt_files):
                    try:
                        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                            text_content = f.read()
                        
                        text_content = self._clean_text_content(text_content)
                        
                        if text_content.strip():
                            chapter_title = f"章节 {i+1}"
                            chapters.append({
                                "title": chapter_title,
                                "content": text_content
                            })
                            
                            full_content += text_content + "\n\n"
                    
                    except Exception as e:
                        logger.warning(f"处理文本文件时出错 {txt_file}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"从目录提取内容时出错: {e}")
        
        return full_content, chapters
    
    def _extract_chapter_title_from_file(self, soup: BeautifulSoup, file_path: str, index: int) -> str:
        """从文件中提取章节标题"""
        # 查找标题标签
        for tag in ['h1', 'h2', 'h3', 'title']:
            title_element = soup.find(tag)
            if title_element:
                title = title_element.get_text().strip()
                if title and len(title) < 100:  # 标题通常较短
                    return title
        
        # 使用文件名作为标题
        filename = os.path.basename(file_path)
        title = filename.replace('.html', '').replace('.htm', '').replace('.xhtml', '')
        title = title.replace('_', ' ').replace('-', ' ')
        
        if title and len(title) > 2:
            return title
        
        return f"章节 {index + 1}"
    
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