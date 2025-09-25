"""
KindleUnpack库包装器，用于处理AZW文件
"""

import os
import sys

import tempfile
import shutil
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from src.utils.logger import get_logger

logger = get_logger(__name__)

class KindleUnpackWrapper:
    """KindleUnpack库的包装器"""
    
    def __init__(self):
        """初始化KindleUnpack包装器"""
        self.kindle_unpack_path = self._find_kindle_unpack_path()
        if self.kindle_unpack_path:
            # 将KindleUnpack库路径添加到Python路径
            if self.kindle_unpack_path not in sys.path:
                sys.path.insert(0, self.kindle_unpack_path)
    
    def _find_kindle_unpack_path(self) -> Optional[str]:
        """查找KindleUnpack库路径"""
        # 查找可能的KindleUnpack路径
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "..", "..", "library", "KindleUnpack"),
            os.path.join(os.path.dirname(__file__), "..", "..", "KindleUnpack"),
            os.path.join(os.path.dirname(__file__), "KindleUnpack"),
        ]
        
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path) and os.path.exists(os.path.join(abs_path, "lib", "kindleunpack.py")):
                logger.info(f"找到KindleUnpack库: {abs_path}")
                return abs_path
        
        logger.warning("未找到KindleUnpack库")
        return None
    
    def is_available(self) -> bool:
        """检查KindleUnpack是否可用"""
        return self.kindle_unpack_path is not None
    
    def unpack_azw(self, azw_file_path: str, output_dir: str) -> Dict[str, Any]:
        """
        解包AZW文件
        
        Args:
            azw_file_path: AZW文件路径
            output_dir: 输出目录
            
        Returns:
            Dict[str, Any]: 解包结果，包含内容和元数据
        """
        if not self.is_available():
            raise ImportError("KindleUnpack库不可用")
        
        try:
            # 导入KindleUnpack模块
            from lib.kindleunpack import unpackBook
            
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 解包AZW文件
            logger.info(f"开始解包AZW文件: {azw_file_path}")
            
            # 调用KindleUnpack的unpackBook函数
            # 参数: infile, outdir, apnxfile, epubver, use_hd, dodump, dowriteraw, dosplitcombos
            unpackBook(azw_file_path, output_dir, None, "2", False, False, False, False)
            
            # 解析解包后的内容
            result = self._parse_unpacked_content(output_dir)
            
            logger.info(f"AZW文件解包完成: {azw_file_path}")
            return result
            
        except Exception as e:
            logger.error(f"解包AZW文件时出错: {e}")
            raise
    
    def _parse_unpacked_content(self, output_dir: str) -> Dict[str, Any]:
        """
        解析解包后的内容
        
        Args:
            output_dir: 解包输出目录
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        result = {
            "content": "",
            "title": "",
            "author": "未知作者",
            "chapters": [],
            "metadata": {}
        }
        
        try:
            # 查找主要的HTML文件（包括XHTML）
            html_files = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file.endswith(('.html', '.htm', '.xhtml')):
                        # 跳过封面页面
                        if 'cover_page' in file.lower():
                            continue
                        html_files.append(os.path.join(root, file))
            
            # 按文件名排序，确保章节顺序正确
            html_files.sort()
            
            if html_files:
                # 处理HTML文件
                from bs4 import BeautifulSoup
                import re
                
                full_content = ""
                chapters = []
                
                for i, html_file in enumerate(html_files):
                    try:
                        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                            html_content = f.read()
                        
                        # 跳过空文件
                        if not html_content.strip():
                            continue
                        
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # 移除脚本和样式标签
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # 提取文本内容
                        text_content = soup.get_text(separator='\n', strip=True)
                        text_content = re.sub(r'\n\s*\n', '\n\n', text_content)
                        
                        # 进一步清理文本
                        text_content = self._clean_text_content(text_content)
                        
                        # 尝试提取章节标题
                        chapter_title = self._extract_chapter_title_from_html(soup, i)
                        
                        if text_content.strip() and len(text_content.strip()) > 10:  # 确保内容不为空且有意义
                            chapters.append({
                                "title": chapter_title,
                                "content": text_content
                            })
                            
                            full_content += text_content + "\n\n"
                    
                    except Exception as e:
                        logger.warning(f"处理HTML文件时出错 {html_file}: {e}")
                        continue
                
                result["content"] = full_content.strip()
                result["chapters"] = chapters
            
            # 尝试读取OPF文件获取元数据
            opf_files = []
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    if file.endswith('.opf'):
                        opf_files.append(os.path.join(root, file))
            
            if opf_files:
                metadata = self._parse_opf_metadata(opf_files[0])
                result["metadata"] = metadata
                result["title"] = metadata.get("title", "")
                result["author"] = metadata.get("author", "未知作者")
            
            # 如果没有找到标题，使用默认标题
            if not result["title"]:
                result["title"] = "AZW文档"
            
            # 如果没有章节，将整个内容作为一个章节
            if not result["chapters"] and result["content"]:
                result["chapters"] = [{"title": "全文", "content": result["content"]}]
            
        except Exception as e:
            logger.error(f"解析解包内容时出错: {e}")
            # 返回基本结果
            result = {
                "content": "解析AZW文件内容时出错",
                "title": "AZW文档",
                "author": "未知作者",
                "chapters": [{"title": "全文", "content": "解析AZW文件内容时出错"}],
                "metadata": {}
            }
        
        return result
    
    def _extract_chapter_title_from_html(self, soup: BeautifulSoup, chapter_index: int) -> str:
        """从HTML中提取章节标题"""
        # 查找标题标签
        for tag in ['h1', 'h2', 'h3', 'title']:
            title_element = soup.find(tag)
            if title_element:
                title = title_element.get_text().strip()
                if title and len(title) < 100:  # 标题通常较短
                    return title
        
        # 查找包含章节关键词的元素
        for element in soup.find_all(['div', 'p', 'span']):
            text = element.get_text().strip()
            if text and len(text) < 100:
                # 检查是否包含章节关键词
                if any(keyword in text.lower() for keyword in ['chapter', '章', '第', 'part']):
                    return text
        
        # 如果没有找到合适的标题，使用默认标题
        return f"章节 {chapter_index + 1}"
    
    def _parse_opf_metadata(self, opf_file_path: str) -> Dict[str, Any]:
        """解析OPF文件中的元数据"""
        metadata = {}
        
        try:
            from bs4 import BeautifulSoup
            
            with open(opf_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                opf_content = f.read()
            
            soup = BeautifulSoup(opf_content, 'xml')
            
            # 提取标题
            title_element = soup.find('dc:title')
            if title_element:
                metadata["title"] = title_element.get_text().strip()
            
            # 提取作者
            creator_element = soup.find('dc:creator')
            if creator_element:
                metadata["author"] = creator_element.get_text().strip()
            
            # 提取语言
            language_element = soup.find('dc:language')
            if language_element:
                metadata["language"] = language_element.get_text().strip()
            
            # 提取出版商
            publisher_element = soup.find('dc:publisher')
            if publisher_element:
                metadata["publisher"] = publisher_element.get_text().strip()
            
            # 提取出版日期
            date_element = soup.find('dc:date')
            if date_element:
                metadata["date"] = date_element.get_text().strip()
            
            # 提取描述
            description_element = soup.find('dc:description')
            if description_element:
                metadata["description"] = description_element.get_text().strip()
            
        except Exception as e:
            logger.warning(f"解析OPF元数据时出错: {e}")
        
        return metadata
    
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
        
        import re
        import html
        
        # 移除残留的HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除HTML实体
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


# 创建全局实例
kindle_unpack_wrapper = KindleUnpackWrapper()