"""
简单分页计算器 - 确保内容完整性的基础分页算法
"""

import re
from typing import List, Optional
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PageMetrics:
    """页面度量数据类"""
    container_width: int = 0
    container_height: int = 0
    content_width: int = 0
    content_height: int = 0
    chars_per_line: int = 0
    lines_per_page: int = 0
    chars_per_page: int = 0


class SimpleTextPagination:
    """简单文本分页策略 - 确保内容完整性的基础算法"""
    
    def paginate(self, content: str, metrics: PageMetrics) -> List[List[str]]:
        """简单分页，确保内容完整性"""
        if not content:
            return [[""]]
        
        logger.debug(f"开始简单分页: 内容长度={len(content)}字符, 容器尺寸={metrics.content_width}x{metrics.lines_per_page}")
        
        # 保存原始内容用于完整性验证
        original_content = content
        
        # 使用简单的段落分割
        paragraphs = self._simple_paragraph_split(content)
        pages = []
        current_page_lines = []
        
        max_lines_per_page = metrics.lines_per_page
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                # 空段落，添加空行（如果还有空间）
                if len(current_page_lines) < max_lines_per_page:
                    current_page_lines.append("")
                continue
            
            # 对每个段落进行简单换行
            wrapped_lines = self._simple_wrap(paragraph, metrics.content_width)
            
            # 处理段落中的每一行
            for line in wrapped_lines:
                # 检查当前行是否能添加到当前页
                if len(current_page_lines) >= max_lines_per_page:
                    # 当前页已满，创建新页
                    if current_page_lines:
                        pages.append(current_page_lines[:])
                        logger.debug(f"完成第{len(pages)}页: {len(current_page_lines)}行")
                    current_page_lines = []
                
                # 添加当前行
                current_page_lines.append(line)
        
        # 添加最后一页
        if current_page_lines:
            pages.append(current_page_lines)
            logger.debug(f"完成最后一页: {len(current_page_lines)}行")
        
        # 确保至少有一页
        if not pages:
            pages = [[""]]
        
        # 验证内容完整性
        processed_text = '\n'.join('\n'.join(page) for page in pages)
        
        # 简单检查：比较字符数（允许一定的空白字符差异）
        if len(original_content) != len(processed_text):
            logger.warning(f"内容完整性检查: 原始={len(original_content)}, 处理后={len(processed_text)}")
        
        logger.debug(f"简单分页完成: 总共{len(pages)}页")
        
        return pages
    
    def _simple_paragraph_split(self, content: str) -> List[str]:
        """简单的段落分割算法"""
        # 使用双换行符分割段落
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # 如果没有找到段落分隔，将整个内容作为一个段落
        if not paragraphs:
            paragraphs = [content.strip()] if content.strip() else [""]
        
        return paragraphs
    
    def _simple_wrap(self, text: str, width: int) -> List[str]:
        """简单换行算法"""
        if not text.strip():
            return [""]
        
        # 如果行长度不超过宽度，直接返回
        if len(text) <= width:
            return [text]
        
        lines = []
        current_line = ""
        
        # 按字符逐个处理，确保不丢失任何内容
        for char in text:
            if len(current_line) < width:
                current_line += char
            else:
                lines.append(current_line)
                current_line = char
        
        # 添加最后一行
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]


class SimpleTerminalPaginator:
    """简单终端分页计算器 - 确保内容完整性的基础分页组件"""
    
    def __init__(self):
        """初始化分页计算器"""
        self.strategy = SimpleTextPagination()
        self.metrics = PageMetrics()
    
    def calculate_metrics(self, container_width: int, container_height: int,
                        margin_left: int = 2, margin_right: int = 2,
                        margin_top: int = 1, margin_bottom: int = 1) -> PageMetrics:
        """
        计算页面度量
        
        Args:
            container_width: 容器宽度（字符数）
            container_height: 容器高度（字符数）
            margin_left: 左边距（字符数）
            margin_right: 右边距（字符数）
            margin_top: 上边距（字符数）
            margin_bottom: 下边距（字符数）
            
        Returns:
            PageMetrics: 页面度量数据
        """
        # 计算内容区域尺寸（考虑边距）
        content_width = max(1, container_width - margin_left - margin_right)
        content_height = max(1, container_height - margin_top - margin_bottom)
        
        # 计算每行字符数和每页行数
        chars_per_line = content_width
        lines_per_page = content_height
        chars_per_page = chars_per_line * lines_per_page
        
        self.metrics = PageMetrics(
            container_width=container_width,
            container_height=container_height,
            content_width=content_width,
            content_height=content_height,
            chars_per_line=chars_per_line,
            lines_per_page=lines_per_page,
            chars_per_page=chars_per_page
        )
        
        logger.debug(f"页面度量计算: 容器={container_width}x{container_height}, "
                   f"内容区域={content_width}x{content_height}, "
                   f"每页行数={lines_per_page}")
        
        return self.metrics
    
    def paginate(self, content: str, metrics: Optional[PageMetrics] = None) -> List[List[str]]:
        """
        对内容进行分页
        
        Args:
            content: 要分页的内容
            metrics: 页面度量数据，如果为None则使用当前度量
            
        Returns:
            List[List[str]]: 分页后的页面列表，每页包含多行文本
        """
        if metrics is None:
            metrics = self.metrics
        
        return self.strategy.paginate(content, metrics)
    
    def get_page_count(self, content: str, metrics: Optional[PageMetrics] = None) -> int:
        """
        获取内容的总页数
        
        Args:
            content: 要计算的内容
            metrics: 页面度量数据
            
        Returns:
            int: 总页数
        """
        pages = self.paginate(content, metrics)
        return len(pages)
    
    def get_page_content(self, content: str, page_number: int, 
                        metrics: Optional[PageMetrics] = None) -> Optional[List[str]]:
        """
        获取指定页的内容
        
        Args:
            content: 原始内容
            page_number: 页码（从0开始）
            metrics: 页面度量数据
            
        Returns:
            Optional[List[str]]: 指定页的内容（行列表），如果页码无效返回None
        """
        pages = self.paginate(content, metrics)
        if 0 <= page_number < len(pages):
            return pages[page_number]
        return None


# 工厂函数
def create_simple_paginator() -> SimpleTerminalPaginator:
    """
    创建简单分页计算器实例
        
    Returns:
        SimpleTerminalPaginator: 简单分页计算器实例
    """
    return SimpleTerminalPaginator()