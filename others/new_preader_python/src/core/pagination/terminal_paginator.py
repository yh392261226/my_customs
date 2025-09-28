"""
终端分页计算器 - 基于终端尺寸和字体设置进行精确分页
采用面向对象设计，与UI层完全解耦
"""

import math
import re
import cjkwrap
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


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
    font_size: int = 16
    line_spacing: float = 1.5
    paragraph_spacing: float = 1.2
    margin_left: int = 2
    margin_right: int = 2
    margin_top: int = 1
    margin_bottom: int = 1


class PaginationStrategy(ABC):
    """分页策略抽象基类"""
    
    @abstractmethod
    def paginate(self, content: str, metrics: PageMetrics) -> List[List[str]]:
        """将内容分页"""
        pass


class SmartTextPagination(PaginationStrategy):
    """智能文本分页策略 - 基于行数和智能换行的分页"""
    
    def paginate(self, content: str, metrics: PageMetrics) -> List[List[str]]:
        """智能分页，基于实际终端显示容量和间距设置的精确计算"""
        if not content:
            return [[""]]
        
        logger.debug(f"开始分页: 内容长度={len(content)}字符, 容器尺寸={metrics.content_width}x{metrics.lines_per_page}")
        logger.debug(f"间距设置: 行间距={metrics.line_spacing}, 段落间距={metrics.paragraph_spacing}")
        
        # 首先将内容按段落分割
        paragraphs = self._split_paragraphs(content)
        pages = []
        current_page_lines = []
        
        # 计算实际可用的行数 - 考虑间距设置
        # 行间距：0=无空行，1=1行空行，2=2行空行，以此类推
        # 段落间距：段落之间的空行数
        line_spacing = int(metrics.line_spacing)
        paragraph_spacing = int(metrics.paragraph_spacing)
        
        logger.debug(f"分页间距设置: 行间距={line_spacing}, 段落间距={paragraph_spacing}")
        
        # 基础可用行数 - 直接使用metrics.lines_per_page
        # 这个值是物理显示行数，但间距会占用额外的显示空间
        # 我们需要计算考虑间距后的实际内容行数容量
        max_lines_per_page = metrics.lines_per_page
        
        # 计算间距对内容容量的影响
        # 行间距：每行内容之间会添加line_spacing个空行
        # 段落间距：每个段落之间会添加paragraph_spacing个空行
        # 使用更合理的计算方法：考虑间距但不过度限制内容行数
        if line_spacing > 0 or paragraph_spacing > 0:
            # 更合理的估计：考虑间距但保留更多内容行数
            # 每页至少保留大部分内容行数，间距只占用部分空间
            spacing_reduction = min(max_lines_per_page // 4, line_spacing + paragraph_spacing)
            effective_content_lines = max(5, max_lines_per_page - spacing_reduction)
        else:
            effective_content_lines = max_lines_per_page
        
        logger.debug(f"最大每页行数: {max_lines_per_page}, 有效内容行数: {effective_content_lines}, 行间距: {line_spacing}, 段落间距: {paragraph_spacing}")
        
        # 使用有效内容行数作为分页限制
        max_content_lines_per_page = effective_content_lines
        
        for paragraph_idx, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                # 空段落，添加空行（如果还有空间）
                if len(current_page_lines) < max_content_lines_per_page:
                    current_page_lines.append("")
                continue
            
            # 对每个段落进行智能换行
            wrapped_lines = self._smart_chinese_wrap(paragraph, metrics.content_width)
            
            # 检查当前页是否能容纳这些行（包括间距）
            for line_idx, line in enumerate(wrapped_lines):
                # 计算添加这一行需要的总行数（包括行间距）
                lines_needed = 1  # 当前行
                if line_idx < len(wrapped_lines) - 1:  # 不是段落的最后一行
                    lines_needed += line_spacing  # 添加行间距空行
                
                # 检查是否需要开始新页（在添加当前行之前）
                if len(current_page_lines) + lines_needed > max_content_lines_per_page:
                    if current_page_lines:  # 确保不添加空页
                        pages.append(current_page_lines[:])  # 创建副本
                        logger.debug(f"完成第{len(pages)}页: {len(current_page_lines)}行")
                    current_page_lines = []
                
                # 添加当前行
                current_page_lines.append(line)
                
                # 添加行间距空行（除了段落的最后一行）
                if line_idx < len(wrapped_lines) - 1:
                    for _ in range(line_spacing):
                        if len(current_page_lines) < max_content_lines_per_page:
                            current_page_lines.append("")
                        else:
                            # 如果添加空行时空间不足，创建新页
                            if current_page_lines:  # 确保不添加空页
                                pages.append(current_page_lines[:])
                                logger.debug(f"完成第{len(pages)}页（空行溢出）: {len(current_page_lines)}行")
                            current_page_lines = [""]  # 新页以空行开始
            
            # 段落间添加空行（如果页面还有空间且不是最后一个段落）
            if paragraph_idx < len(paragraphs) - 1 and current_page_lines:
                # 检查是否有足够空间添加段落间距
                if len(current_page_lines) + paragraph_spacing <= max_content_lines_per_page:
                    for _ in range(paragraph_spacing):
                        current_page_lines.append("")
                else:
                    # 空间不足，创建新页
                    if current_page_lines:  # 确保不添加空页
                        pages.append(current_page_lines[:])
                        logger.debug(f"完成第{len(pages)}页（段落间距溢出）: {len(current_page_lines)}行")
                    current_page_lines = [""]  # 新页以空行开始
        
        # 添加最后一页
        if current_page_lines:
            pages.append(current_page_lines)
            logger.debug(f"完成最后一页: {len(current_page_lines)}行")
        
        # 确保至少有一页
        if not pages:
            pages = [[""]]
        
        logger.debug(f"分页完成: 总共{len(pages)}页, 平均每页{len(content)//len(pages) if pages else 0}字符")
        return pages
    
    def _split_paragraphs(self, content: str) -> List[str]:
        """分割内容为段落"""
        # 按双换行符分割段落，保持单换行符
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # 如果只有一个段落且长度超过500字符，尝试按句子分割
        if len(paragraphs) == 1 and len(paragraphs[0]) > 500:
            # 尝试按中文标点符号分割
            import re
            # 中文句子分割模式：句号、问号、感叹号、分号等
            sentence_pattern = r'([。！？；：]+)'
            sentences = re.split(sentence_pattern, paragraphs[0])
            
            # 重新组合句子
            new_paragraphs = []
            current_paragraph = ""
            
            for i, part in enumerate(sentences):
                if not part.strip():
                    continue
                    
                # 如果是标点符号，添加到前一部分
                if re.match(sentence_pattern, part):
                    if current_paragraph:
                        current_paragraph += part
                        new_paragraphs.append(current_paragraph.strip())
                        current_paragraph = ""
                    elif new_paragraphs:
                        new_paragraphs[-1] = new_paragraphs[-1] + part
                else:
                    current_paragraph += part
                    
                    # 如果当前段落已经很长，或者这是最后一部分，添加到结果
                    if len(current_paragraph) > 200 or i == len(sentences) - 1:
                        new_paragraphs.append(current_paragraph.strip())
                        current_paragraph = ""
            
            # 添加最后一个段落
            if current_paragraph:
                new_paragraphs.append(current_paragraph.strip())
                
            if new_paragraphs:
                paragraphs = new_paragraphs
        
        return paragraphs
    
    def _smart_chinese_wrap(self, text: str, width: int) -> List[str]:
        """
        智能中文文本换行，保持段落格式和标点完整性
        """
        if not text.strip():
            return [""]
        
        # 处理全角空格和制表符
        text = text.replace('\u3000', '  ')  # 全角空格转换为两个半角空格
        text = text.expandtabs(4)  # 制表符转换为4个空格
        
        # 按现有换行符分割
        input_lines = text.split('\n')
        result_lines = []
        
        for input_line in input_lines:
            if not input_line.strip():
                result_lines.append("")
                continue
                
            # 对每行进行智能换行
            wrapped = self._wrap_single_line(input_line, width)
            result_lines.extend(wrapped)
        
        return result_lines
    
    def _wrap_single_line(self, line: str, width: int) -> List[str]:
        """对单行文本进行智能换行 - 优化的中文换行算法"""
        if not line:
            return [""]
            
        # 如果行长度不超过宽度，直接返回
        if self._calculate_display_width(line) <= width:
            return [line]
        
        lines = []
        current_line = ""
        current_width = 0
        
        # 优化的中文标点符号处理
        # 不能在行首的标点
        no_line_start = "，。；：！？、）】》"
        # 不能在行尾的标点  
        no_line_end = "（【《"
        
        i = 0
        while i < len(line):
            char = line[i]
            char_width = self._get_char_width(char)
            
            # 检查是否需要换行（使用更宽松的条件）
            if current_width + char_width > width and current_line:
                # 如果当前行已经有内容，尝试寻找更好的换行点
                # 优先在标点符号或空格处换行
                if char in no_line_start:
                    # 标点符号不能出现在行首，强制加入当前行
                    current_line += char
                    current_width += char_width
                    i += 1
                else:
                    # 寻找合适的换行点
                    # 如果当前字符是空格或标点，直接换行
                    if char in " \t" or char in no_line_end:
                        lines.append(current_line)
                        current_line = char
                        current_width = char_width
                        i += 1
                    else:
                        # 尝试在当前字符前换行
                        lines.append(current_line)
                        current_line = char
                        current_width = char_width
                        i += 1
            else:
                current_line += char
                current_width += char_width
                i += 1
        
        # 添加最后一行
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
    def _get_char_width(self, char: str) -> int:
        """获取字符显示宽度 - 优化的中文字符宽度计算"""
        # 中文字符范围（更全面）
        if '\u4e00' <= char <= '\u9fff':  # CJK统一汉字
            return 2
        elif '\u3400' <= char <= '\u4dbf':  # CJK扩展A
            return 2
        elif '\u20000' <= char <= '\u2a6df':  # CJK扩展B
            return 2
        elif '\uff00' <= char <= '\uffef':  # 全角字符
            return 2
        elif '\u3000' <= char <= '\u303f':  # CJK符号和标点
            return 2
        elif char in "，。；：！？、（）【】《》""''「」『』〈〉〔〕〖〗〘〙〚〛":  # 中文标点
            return 2
        elif char in "　":  # 全角空格
            return 2
        # 对于半角标点符号，使用更合理的宽度计算
        elif char in ".,;:!?()[]{}<>\"'":  # 半角标点符号
            return 1
        else:
            return 1
    
    def _calculate_display_width(self, text: str) -> int:
        """计算文本显示宽度"""
        return sum(self._get_char_width(char) for char in text)





class TerminalPaginator:
    """终端分页计算器 - 核心分页组件"""
    
    def __init__(self, strategy: str = "smart"):
        """
        初始化分页计算器
        
        Args:
            strategy: 分页策略，支持 "smart" (智能文本分页)
        """
        self.strategies = {
            "smart": SmartTextPagination()
        }
        self.current_strategy = self.strategies.get(strategy, SmartTextPagination())
        self.metrics = PageMetrics()
    
    def calculate_metrics(self, container_width: int, container_height: int,
                        font_size: int = 16, line_spacing: float = 1.5,
                        paragraph_spacing: float = 1.2,
                        margin_left: int = 2, margin_right: int = 2,
                        margin_top: int = 1, margin_bottom: int = 1) -> PageMetrics:
        """
        计算页面度量
        
        Args:
            container_width: 容器宽度（字符数）
            container_height: 容器高度（字符数）
            font_size: 字体大小
            line_spacing: 行间距（影响显示行数）
            paragraph_spacing: 段落间距（影响显示行数）
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
        
        # 计算每行字符数（终端中通常每个字符宽度为1）
        chars_per_line = content_width
        
        # 计算每页行数（考虑行间距和段落间距对显示的影响）
        # 在智能分页中，lines_per_page表示实际显示的行数限制
        # 行间距和段落间距会影响内容的视觉布局，需要在分页时考虑
        lines_per_page = content_height
        
        logger.debug(f"可用行数计算: 内容高度={content_height}, 行间距={line_spacing}, 段落间距={paragraph_spacing}")
        
        # 计算每页字符数（用于简单分页策略）
        chars_per_page = chars_per_line * lines_per_page
        
        self.metrics = PageMetrics(
            container_width=container_width,
            container_height=container_height,
            content_width=content_width,
            content_height=content_height,
            chars_per_line=chars_per_line,
            lines_per_page=lines_per_page,
            chars_per_page=chars_per_page,
            font_size=font_size,
            line_spacing=line_spacing,
            paragraph_spacing=paragraph_spacing,
            margin_left=margin_left,
            margin_right=margin_right,
            margin_top=margin_top,
            margin_bottom=margin_bottom
        )
        
        logger.debug(f"页面度量计算: 容器={container_width}x{container_height}, "
                   f"字体={font_size}, 行间距={line_spacing}, 段落间距={paragraph_spacing}, "
                   f"边距=({margin_left},{margin_right},{margin_top},{margin_bottom}), "
                   f"每页行数={lines_per_page}, 每页字符数={chars_per_page}")
        
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
        
        return self.current_strategy.paginate(content, metrics)
    
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
    
    def find_page_by_position(self, content: str, char_position: int,
                            metrics: Optional[PageMetrics] = None) -> int:
        """
        根据字符位置查找所在页码
        
        Args:
            content: 原始内容
            char_position: 字符位置
            metrics: 页面度量数据
            
        Returns:
            int: 页码（从0开始）
        """
        pages = self.paginate(content, metrics)
        current_pos = 0
        
        for page_num, page_content in enumerate(pages):
            page_length = len(page_content)
            if current_pos <= char_position < current_pos + page_length:
                return page_num
            current_pos += page_length
        
        # 如果位置超出内容范围，返回最后一页
        return len(pages) - 1 if pages else 0
    
    def update_strategy(self, strategy: str) -> None:
        """
        更新分页策略
        
        Args:
            strategy: 分页策略名称
        """
        if strategy in self.strategies:
            self.current_strategy = self.strategies[strategy]
        else:
            logger.warning(f"未知的分页策略: {strategy}, 使用默认策略")
    
    def set_margins(self, left: int = 2, right: int = 2, top: int = 1, bottom: int = 1) -> None:
        """
        设置页面边距
        
        Args:
            left: 左边距（字符数）
            right: 右边距（字符数）
            top: 上边距（字符数）
            bottom: 下边距（字符数）
        """
        self.metrics.margin_left = max(0, left)
        self.metrics.margin_right = max(0, right)
        self.metrics.margin_top = max(0, top)
        self.metrics.margin_bottom = max(0, bottom)
        
        # 重新计算内容区域尺寸
        self.metrics.content_width = max(1, self.metrics.container_width - 
                                       self.metrics.margin_left - self.metrics.margin_right)
        self.metrics.content_height = max(1, self.metrics.container_height - 
                                        self.metrics.margin_top - self.metrics.margin_bottom)
        
        # 重新计算每页字符数和行数
        self.metrics.chars_per_line = self.metrics.content_width
        self.metrics.lines_per_page = self.metrics.content_height
        self.metrics.chars_per_page = self.metrics.chars_per_line * self.metrics.lines_per_page


# 工厂函数
def create_paginator(strategy: str = "smart") -> TerminalPaginator:
    """
    创建分页计算器实例
    
    Args:
        strategy: 分页策略
        
    Returns:
        TerminalPaginator: 分页计算器实例
    """
    return TerminalPaginator(strategy)