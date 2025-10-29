"""
健壮的分页计算器 - 处理各种边界情况的内容分页
"""

import math
import re
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
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


class ContentTracker:
    """内容完整性跟踪器"""
    
    def __init__(self, original_content: str):
        self.original_content = original_content
        self.processed_content = []
    
    def add_line(self, line: str):
        """添加处理的行内容"""
        self.processed_content.append(line)
    
    def verify_integrity(self) -> Dict[str, Any]:
        """验证内容完整性"""
        processed_text = '\n'.join(self.processed_content)
        
        # 标准化比较：移除所有空白字符差异
        original_normalized = self._normalize_content(self.original_content)
        processed_normalized = self._normalize_content(processed_text)
        
        # 简单检查：比较字符数
        original_len = len(original_normalized)
        processed_len = len(processed_normalized)
        
        missing_chars = original_len - processed_len
        
        # 更严格的检查：验证关键内容是否存在
        # 检查原始内容的前100个字符是否在处理后的内容中
        check_segment = original_normalized[:min(100, len(original_normalized))]
        is_segment_found = check_segment in processed_normalized
        
        # 检查原始内容的最后100个字符是否在处理后的内容中
        if len(original_normalized) > 100:
            end_segment = original_normalized[-100:]
            is_end_found = end_segment in processed_normalized
        else:
            is_end_found = True
        
        # 允许一定的字符差异（主要是空白字符差异）
        is_complete = (missing_chars <= 10) and is_segment_found and is_end_found
        
        return {
            "is_complete": is_complete,
            "missing_chars": max(0, missing_chars),
            "original_length": len(self.original_content),
            "processed_length": len(processed_text),
            "segment_found": is_segment_found,
            "end_found": is_end_found
        }
    
    def _normalize_content(self, content: str) -> str:
        """标准化内容，移除多余的空白字符"""
        # 移除多余的空格和换行符，保留基本格式
        # 将多个连续空格替换为单个空格
        content = re.sub(r'\s+', ' ', content)
        # 移除首尾空格
        content = content.strip()
        return content


class PaginationStrategy(ABC):
    """分页策略抽象基类"""
    
    @abstractmethod
    def paginate(self, content: str, metrics: PageMetrics) -> List[List[str]]:
        """将内容分页"""
        pass


class RobustTextPagination(PaginationStrategy):
    """健壮文本分页策略 - 处理各种边界情况"""
    
    def paginate(self, content: str, metrics: PageMetrics) -> List[List[str]]:
        """健壮分页，确保内容完整性"""
        if not content:
            return [[""]]
        
        logger.debug(f"开始健壮分页: 内容长度={len(content)}字符, 容器尺寸={metrics.content_width}x{metrics.lines_per_page}")
        
        # 保存原始内容用于完整性验证
        original_content = content
        
        # 使用更健壮的段落分割
        paragraphs = self._robust_paragraph_split(content)
        pages = []
        current_page_lines = []
        
        # 计算实际可用的行数 - 考虑间距设置
        line_spacing = int(metrics.line_spacing)
        paragraph_spacing = int(metrics.paragraph_spacing)
        max_lines_per_page = metrics.lines_per_page
        
        logger.debug(f"分页间距设置: 行间距={line_spacing}, 段落间距={paragraph_spacing}")
        
        for paragraph_idx, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                # 空段落，添加空行（如果还有空间）
                if len(current_page_lines) < max_lines_per_page:
                    current_page_lines.append("")
                continue
            
            # 对每个段落进行智能换行
            wrapped_lines = self._smart_chinese_wrap(paragraph, metrics.content_width)
            
            # 处理段落中的每一行
            for line_idx, line in enumerate(wrapped_lines):
                # 检查当前行是否能添加到当前页
                if len(current_page_lines) >= max_lines_per_page:
                    # 当前页已满，创建新页
                    if current_page_lines:
                        pages.append(current_page_lines[:])
                        logger.debug(f"完成第{len(pages)}页: {len(current_page_lines)}行")
                    current_page_lines = []
                
                # 添加当前行
                current_page_lines.append(line)
                
                # 添加行间距空行（除了段落的最后一行）
                if line_idx < len(wrapped_lines) - 1 and line_spacing > 0:
                    # 检查是否有足够空间添加行间距
                    if len(current_page_lines) + line_spacing <= max_lines_per_page:
                        for _ in range(line_spacing):
                            current_page_lines.append("")
                    # 如果空间不足，跳过行间距
            
            # 段落间添加空行（如果页面还有空间且不是最后一个段落）
            if paragraph_idx < len(paragraphs) - 1:
                # 检查是否有足够空间添加段落间距
                if len(current_page_lines) + paragraph_spacing <= max_lines_per_page:
                    for _ in range(paragraph_spacing):
                        current_page_lines.append("")
                else:
                    # 空间不足，完成当前页，在新页开始
                    if current_page_lines:
                        pages.append(current_page_lines[:])
                        logger.debug(f"完成第{len(pages)}页（段落间距前完成）: {len(current_page_lines)}行")
                    current_page_lines = []
        
        # 添加最后一页
        if current_page_lines:
            pages.append(current_page_lines)
            logger.debug(f"完成最后一页: {len(current_page_lines)}行")
        
        # 确保至少有一页
        if not pages:
            pages = [[""]]
        
        # 验证内容完整性
        processed_text = '\n'.join('\n'.join(page) for page in pages)
        original_normalized = self._normalize_content(original_content)
        processed_normalized = self._normalize_content(processed_text)
        
        original_len = len(original_normalized)
        processed_len = len(processed_normalized)
        
        # 如果内容丢失超过5%，使用备用分页策略
        if original_len > 0 and (original_len - processed_len) / original_len > 0.05:
            logger.warning(f"内容完整性检查失败: 丢失{original_len - processed_len}字符")
            logger.warning(f"原始长度: {len(original_content)}, 处理后: {len(processed_text)}")
            # 使用备用分页策略
            pages = self._fallback_pagination(original_content, metrics, {
                "missing_chars": original_len - processed_len,
                "original_length": len(original_content),
                "processed_length": len(processed_text)
            })
        
        logger.debug(f"健壮分页完成: 总共{len(pages)}页")
        
        return pages
    
    def _normalize_content(self, content: str) -> str:
        """标准化内容，移除多余的空白字符"""
        # 移除多余的空格和换行符，保留基本格式
        # 将多个连续空格替换为单个空格
        content = re.sub(r'\s+', ' ', content)
        # 移除首尾空格
        content = content.strip()
        return content
    
    def _robust_paragraph_split(self, content: str) -> List[str]:
        """健壮的段落分割算法"""
        paragraphs = []
        current_paragraph = []
        
        # 使用多种分割符
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                # 空行表示段落分隔
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        # 添加最后一个段落
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        # 如果没有找到段落分隔，将整个内容作为一个段落
        if not paragraphs:
            paragraphs = [content.strip()] if content.strip() else [""]
        
        # 合并过短的段落
        merged_paragraphs = []
        for paragraph in paragraphs:
            if not merged_paragraphs or len(paragraph) < 20:
                # 如果段落很短，尝试合并到前一个段落
                if merged_paragraphs:
                    merged_paragraphs[-1] += " " + paragraph
                else:
                    merged_paragraphs.append(paragraph)
            else:
                merged_paragraphs.append(paragraph)
        
        return merged_paragraphs
    
    def _smart_chinese_wrap(self, text: str, width: int) -> List[str]:
        """智能中文文本换行，保持段落格式和标点完整性"""
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
        """对单行文本进行智能换行 - 健壮的中文换行算法"""
        if not line:
            return [""]
            
        # 如果行长度不超过宽度，直接返回
        if self._calculate_display_width(line) <= width:
            return [line]
        
        lines = []
        current_line = ""
        current_width = 0
        
        # 更全面的中文标点符号处理
        # 不能在行首的标点
        no_line_start = "，。；：！？、）】》'\"”』」】〗〙〛"
        # 不能在行尾的标点  
        no_line_end = "（【《'\"『「【〖〘〚"
        
        i = 0
        while i < len(line):
            char = line[i]
            char_width = self._get_char_width(char)
            
            # 检查是否需要换行
            if current_width + char_width > width and current_line:
                # 如果当前行已经有内容，寻找最佳换行点
                
                # 优先在空格处换行
                if char in " \t":
                    lines.append(current_line)
                    current_line = ""
                    current_width = 0
                    i += 1
                    continue
                
                # 检查标点符号规则
                if char in no_line_start:
                    # 标点符号不能出现在行首，检查是否可以加入当前行
                    # 如果当前行还有空间，加入当前行
                    if current_width + char_width <= width:
                        current_line += char
                        current_width += char_width
                    else:
                        # 空间不足，换行后添加标点
                        lines.append(current_line)
                        current_line = char
                        current_width = char_width
                    i += 1
                elif char in no_line_end:
                    # 标点符号不能出现在行尾，检查是否可以加入当前行
                    lines.append(current_line)
                    current_line = char
                    current_width = char_width
                    i += 1
                else:
                    # 普通字符，检查是否有更好的换行点
                    # 尝试寻找最近的标点或空格
                    break_pos = self._find_best_break_point(current_line, char, width)
                    if break_pos > 0:
                        # 在最佳位置换行
                        lines.append(current_line[:break_pos].rstrip())
                        remaining = current_line[break_pos:] + char
                        current_line = remaining
                        current_width = self._calculate_display_width(remaining)
                    else:
                        # 没有找到更好的换行点，强制换行
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
        """获取字符显示宽度 - 更健壮的中文字符宽度计算"""
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
        # 更全面的中文标点符号
        elif char in "，。；：！？、（）【】《》\"'\"'「」『』〈〉〔〕〖〗〘〙〚〛﹃﹄﹁﹂":
            return 2
        elif char in "—…～‖·‘’“”〔〕〈〉《》『』【】〖〗〘〙〚〛":
            return 2
        elif char in "　":  # 全角空格
            return 2
        # 对于半角标点符号，使用更合理的宽度计算
        elif char in ". , ; : ! ? ( ) [ ] { } < > \" '":  # 半角标点符号
            return 1
        # 特殊处理：常见格式标记字符
        elif char in "*#@$%&+-=^_`|~\\":  # 常见的格式标记字符，按半角处理
            return 1
        # 控制字符和不可见字符
        elif ord(char) < 32 or ord(char) == 127:
            return 0
        else:
            return 1
    
    def _calculate_display_width(self, text: str) -> int:
        """计算文本显示宽度"""
        return sum(self._get_char_width(char) for char in text)
    
    def _find_best_break_point(self, current_line: str, next_char: str, max_width: int) -> int:
        """寻找最佳换行点"""
        # 从当前行末尾开始寻找合适的换行点
        for i in range(len(current_line) - 1, -1, -1):
            char = current_line[i]
            # 优先在标点符号或空格处换行
            if char in " ，。；：！？、（）【】《》\"'\"'「」『』〈〉〔〕〖〗〘〙〚〛".replace(" ", ""):
                return i + 1
            elif char in " \t":
                return i + 1
        
        # 如果没有找到合适的换行点，返回-1表示强制换行
        return -1
    
    def _fallback_pagination(self, content: str, metrics: PageMetrics, 
                           integrity_check: Dict) -> List[List[str]]:
        """内容完整性检查失败时的备用分页策略"""
        logger.warning("使用备用分页策略处理内容丢失问题")
        
        # 简化策略：逐字符分页，确保内容完整性
        lines_per_page = metrics.lines_per_page
        chars_per_line = metrics.content_width
        
        # 将内容按段落分割
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        pages = []
        current_page_lines = []
        
        for paragraph in paragraphs:
            if not paragraph:
                continue
            
            # 逐字符处理，确保不丢失任何内容
            current_line = ""
            for char in paragraph:
                if self._calculate_display_width(current_line + char) <= chars_per_line:
                    current_line += char
                else:
                    # 当前行已满，添加到页面
                    if current_line:
                        current_page_lines.append(current_line)
                        current_line = char
                    
                    # 检查当前页是否已满
                    if len(current_page_lines) >= lines_per_page:
                        pages.append(current_page_lines[:])
                        current_page_lines = []
            
            # 添加段落的最后一行
            if current_line:
                current_page_lines.append(current_line)
                current_line = ""
            
            # 添加段落分隔空行
            if len(current_page_lines) < lines_per_page:
                current_page_lines.append("")
            
            # 检查当前页是否已满
            if len(current_page_lines) >= lines_per_page:
                pages.append(current_page_lines[:])
                current_page_lines = []
        
        # 添加最后一页
        if current_page_lines:
            pages.append(current_page_lines)
        
        # 确保至少有内容
        if not pages:
            pages = [[""]]
        
        return pages


class RobustTerminalPaginator:
    """健壮终端分页计算器 - 核心分页组件"""
    
    def __init__(self, strategy: str = "robust"):
        """
        初始化分页计算器
        
        Args:
            strategy: 分页策略，支持 "robust" (健壮文本分页)
        """
        self.strategies = {
            "robust": RobustTextPagination()
        }
        self.current_strategy = self.strategies.get(strategy, RobustTextPagination())
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
        对内容进行分页，包含完整性检查和备用策略
        
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
            page_length = sum(len(line) for line in page_content)
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
def create_robust_paginator(strategy: str = "robust") -> RobustTerminalPaginator:
    """
    创建健壮分页计算器实例
    
    Args:
        strategy: 分页策略
        
    Returns:
        RobustTerminalPaginator: 健壮分页计算器实例
    """
    return RobustTerminalPaginator(strategy)