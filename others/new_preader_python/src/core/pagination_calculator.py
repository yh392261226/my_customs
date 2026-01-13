"""
分页计算器 - 基于终端尺寸和字体设置进行精确分页
采用面向对象设计，与UI层完全解耦
支持智能预加载和后台分页处理
"""

import math
import re
import asyncio
import threading
from typing import List, Tuple, Dict, Any, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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


class PaginationStrategy(ABC):
    """分页策略抽象基类"""

    @abstractmethod
    def paginate(self, content: str, metrics: PageMetrics) -> List[str]:
        """将内容分页"""
        pass


class SimpleTextPagination(PaginationStrategy):
    """简单文本分页策略"""

    def paginate(self, content: str, metrics: PageMetrics) -> List[str]:
        """基于字符数的简单分页"""
        if not content or metrics.chars_per_page <= 0:
            return []

        pages = []
        remaining = content

        while remaining:
            # 获取当前页内容
            page_content = self._get_page_content(remaining, metrics)
            pages.append(page_content)
            remaining = remaining[len(page_content):]

            # 安全限制，避免无限循环
            if len(pages) > 1000:
                break

        return pages

    def _get_page_content(self, content: str, metrics: PageMetrics) -> str:
        """获取单页内容"""
        if len(content) <= metrics.chars_per_page:
            return content

        # 查找最佳分页点
        target_pos = metrics.chars_per_page

        # 优先在段落边界分页
        paragraph_end = content[:target_pos].rfind('\n\n')
        if paragraph_end > 0 and paragraph_end > target_pos * 0.7:
            return content[:paragraph_end + 2]

        # 其次在句子边界分页
        sentence_ends = ['. ', '? ', '! ', '。', '？', '！']
        for end_marker in sentence_ends:
            end_pos = content[:target_pos].rfind(end_marker)
            if end_pos > 0 and end_pos > target_pos * 0.6:
                return content[:end_pos + len(end_marker)]

        # 最后在单词边界分页
        space_pos = content[:target_pos].rfind(' ')
        if space_pos > 0 and space_pos > target_pos * 0.5:
            return content[:space_pos + 1]

        # 如果找不到合适的分页点，按字符数分页
        return content[:target_pos]


class SmartTextPagination(PaginationStrategy):
    """智能文本分页策略 - 考虑段落和句子结构"""

    def paginate(self, content: str, metrics: PageMetrics) -> List[str]:
        """智能分页，保持段落完整性"""
        if not content or metrics.chars_per_page <= 0:
            return []

        # 首先按段落分割
        paragraphs = self._split_paragraphs(content)
        pages = []
        current_page_lines = []
        current_page_chars = 0

        for paragraph in paragraphs:
            # 处理每个段落
            paragraph_pages = self._process_paragraph(paragraph, metrics,
                                                     current_page_chars,
                                                     current_page_lines)

            for page_content in paragraph_pages:
                if isinstance(page_content, tuple):  # 继续当前页
                    current_page_lines, current_page_chars = page_content
                else:  # 新页面
                    if current_page_lines:
                        pages.append('\n'.join(current_page_lines))
                    current_page_lines = [page_content]
                    current_page_chars = len(page_content)

        # 添加最后一页
        if current_page_lines:
            pages.append('\n'.join(current_page_lines))

        return pages

    def _split_paragraphs(self, content: str) -> List[str]:
        """分割内容为段落"""
        # 按空行分割段落
        paragraphs = re.split(r'\n\s*\n', content)
        return [p.strip() for p in paragraphs if p.strip()]

    def _process_paragraph(self, paragraph: str, metrics: PageMetrics,
                          current_chars: int, current_lines: List[str]) -> List:
        """处理单个段落"""
        result = []
        lines = paragraph.split('\n')

        for line in lines:
            # 处理超长行的换行
            wrapped_lines = self._wrap_line(line, metrics.content_width)

            for wrapped_line in wrapped_lines:
                line_chars = len(wrapped_line)

                # 检查是否超出当前页容量
                if (current_chars + line_chars > metrics.chars_per_page and
                    current_chars > metrics.chars_per_page * 0.3):  # 当前页已有一定内容
                    # 完成当前页，开始新页
                    result.append('\n'.join(current_lines))
                    current_lines = []
                    current_chars = 0

                current_lines.append(wrapped_line)
                current_chars += line_chars

        # 返回继续当前页的状态
        result.append((current_lines, current_chars))
        return result

    def _wrap_line(self, line: str, max_width: int) -> List[str]:
        """行换行处理"""
        if len(line) <= max_width:
            return [line]

        words = line.split()
        wrapped_lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)
            if current_length + word_length + len(current_line) > max_width:
                wrapped_lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                current_line.append(word)
                current_length += word_length

        if current_line:
            wrapped_lines.append(' '.join(current_line))

        return wrapped_lines


class PreloadPaginationCalculator:
    """支持预加载的分页计算器"""

    def __init__(self, strategy: str = "smart", max_preload_pages: int = 5):
        """
        初始化分页计算器

        Args:
            strategy: 分页策略，可选 "simple" 或 "smart"
            max_preload_pages: 最大预加载页数
        """
        self.strategies = {
            "simple": SimpleTextPagination(),
            "smart": SmartTextPagination()
        }
        self.current_strategy = self.strategies.get(strategy, self.strategies["smart"])
        self.metrics = PageMetrics()
        self.max_preload_pages = max_preload_pages

        # 预加载相关属性
        self._preload_cache: Dict[str, List[str]] = {}
        self._preload_lock = threading.RLock()
        self._preload_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="preload_worker")
        self._current_task = None
        self._last_access_time = time.time()

        # 用户阅读习惯追踪
        self._reading_speed = 300  # 字/分钟，初始值
        self._reading_history = []  # [(page_idx, time_spent), ...]
        self._max_history = 10  # 保留最近10次阅读记录

    def calculate_metrics(self, container_width: int, container_height: int,
                        font_size: int = 16, line_spacing: float = 1.5,
                        paragraph_spacing: float = 1.2) -> PageMetrics:
        """
        计算页面度量

        Args:
            container_width: 容器宽度（字符数）
            container_height: 容器高度（字符数）
            font_size: 字体大小
            line_spacing: 行间距
            paragraph_spacing: 段落间距

        Returns:
            PageMetrics: 页面度量数据
        """
        # 计算内容区域尺寸（考虑边距）
        content_width = max(1, container_width - 4)  # 左右各2字符边距
        content_height = max(1, container_height - 4)  # 上下各2字符边距

        # 计算每行字符数（终端中通常每个字符宽度为1）
        chars_per_line = content_width

        # 计算每页行数（基于行高）
        line_height = max(1, int(font_size * line_spacing))
        lines_per_page = max(1, int(content_height / line_height))

        # 计算每页字符数
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
            paragraph_spacing=paragraph_spacing
        )

        return self.metrics

    def paginate(self, content: str, metrics: PageMetrics = None) -> List[str]:
        """
        分页内容

        Args:
            content: 要分页的内容
            metrics: 页面度量，如果为None则使用内部度量

        Returns:
            List[str]: 分页后的页面列表
        """
        if metrics is None:
            metrics = self.metrics

        # 生成缓存键
        cache_key = self._generate_cache_key(content, metrics)

        # 检查缓存
        with self._preload_lock:
            if cache_key in self._preload_cache:
                return self._preload_cache[cache_key]

        # 执行分页
        pages = self.current_strategy.paginate(content, metrics)

        # 缓存结果
        with self._preload_lock:
            self._preload_cache[cache_key] = pages
            # 限制缓存大小
            if len(self._preload_cache) > 10:  # 最多缓存10个不同的内容
                # 移除最旧的缓存项
                oldest_key = next(iter(self._preload_cache))
                del self._preload_cache[oldest_key]

        # 启动预加载任务
        self._start_preload_task(content, metrics, len(pages))

        return pages

    def _generate_cache_key(self, content: str, metrics: PageMetrics) -> str:
        """生成缓存键"""
        content_hash = hash(content[:100])  # 只使用内容前100字符的哈希
        metrics_hash = hash((
            metrics.container_width,
            metrics.container_height,
            metrics.font_size,
            metrics.line_spacing,
            metrics.paragraph_spacing
        ))
        return f"{content_hash}_{metrics_hash}"

    def _start_preload_task(self, content: str, metrics: PageMetrics, total_pages: int):
        """启动预加载任务"""
        # 取消之前的预加载任务
        if self._current_task:
            # 注意：在实际实现中，这里需要更复杂的任务取消逻辑
            pass

        # 启动新的预加载任务
        self._current_task = self._preload_executor.submit(
            self._preload_pages, content, metrics, total_pages
        )

    def _preload_pages(self, content: str, metrics: PageMetrics, total_pages: int):
        """预加载页面"""
        try:
            # 根据用户阅读习惯预测需要预加载的页面
            pages_to_preload = self._predict_pages_to_preload(total_pages)

            # 预加载指定页面
            for page_idx in pages_to_preload:
                if page_idx >= total_pages:
                    continue

                # 这里我们实际上不需要重新分页，因为整个内容已经分好页了
                # 预加载的真正意义在于将页面内容加载到内存中
                # 但在当前实现中，所有页面已经生成，所以预加载主要是缓存访问
                pass

        except Exception as e:
            print(f"预加载任务出错: {e}")

    def _predict_pages_to_preload(self, total_pages: int) -> List[int]:
        """根据用户阅读习惯预测需要预加载的页面"""
        # 基于阅读速度和历史记录预测
        if not self._reading_history:
            # 如果没有历史记录，预加载当前页后的几页
            return list(range(1, min(self.max_preload_pages + 1, total_pages)))

        # 计算平均阅读速度
        if len(self._reading_history) > 1:
            avg_time_per_page = sum(h[1] for h in self._reading_history) / len(self._reading_history)
            pages_per_minute = 60 / avg_time_per_page if avg_time_per_page > 0 else 300

            # 预加载未来几分钟可能需要的页面
            pages_to_preload = min(int(pages_per_minute * 2), self.max_preload_pages)  # 预加载未来2分钟的页面
            return list(range(1, min(pages_to_preload + 1, total_pages)))
        else:
            # 如果只有一次记录，使用默认值
            return list(range(1, min(self.max_preload_pages + 1, total_pages)))

    def record_reading_time(self, page_idx: int, time_spent: float):
        """记录页面阅读时间，用于优化预加载策略"""
        self._reading_history.append((page_idx, time_spent))

        # 限制历史记录数量
        if len(self._reading_history) > self._max_history:
            self._reading_history = self._reading_history[-self._max_history:]

        # 更新阅读速度估计
        if len(self._reading_history) > 0:
            avg_time = sum(h[1] for h in self._reading_history) / len(self._reading_history)
            self._reading_speed = 60 / avg_time if avg_time > 0 else 300

    def get_preloaded_pages(self, start_page: int, count: int) -> List[str]:
        """获取预加载的页面"""
        # 这里返回空列表，因为当前实现中所有页面都已生成
        # 在实际的异步预加载实现中，这里会返回预加载的页面
        return []

    def set_strategy(self, strategy: str) -> bool:
        """
        设置分页策略

        Args:
            strategy: 策略名称，"simple" 或 "smart"

        Returns:
            bool: 是否设置成功
        """
        if strategy in self.strategies:
            self.current_strategy = self.strategies[strategy]
            return True
        return False

    def get_metrics(self) -> PageMetrics:
        """获取当前页面度量"""
        return self.metrics

    def shutdown(self):
        """关闭分页计算器，清理资源"""
        self._preload_executor.shutdown(wait=True)


class PaginationCalculator:
    """分页计算器 - 核心分页组件（向后兼容）"""

    def __init__(self, strategy: str = "smart"):
        """
        初始化分页计算器

        Args:
            strategy: 分页策略，可选 "simple" 或 "smart"
        """
        self._impl = PreloadPaginationCalculator(strategy)

    def calculate_metrics(self, container_width: int, container_height: int,
                        font_size: int = 16, line_spacing: float = 1.5,
                        paragraph_spacing: float = 1.2) -> PageMetrics:
        """
        计算页面度量
        """
        return self._impl.calculate_metrics(container_width, container_height,
                                         font_size, line_spacing, paragraph_spacing)

    def paginate(self, content: str, metrics: PageMetrics = None) -> List[str]:
        """
        分页内容
        """
        return self._impl.paginate(content, metrics)

    def set_strategy(self, strategy: str) -> bool:
        """
        设置分页策略
        """
        return self._impl.set_strategy(strategy)

    def get_metrics(self) -> PageMetrics:
        """获取当前页面度量"""
        return self._impl.get_metrics()

    def record_reading_time(self, page_idx: int, time_spent: float):
        """记录页面阅读时间"""
        self._impl.record_reading_time(page_idx, time_spent)

    def get_preloaded_pages(self, start_page: int, count: int) -> List[str]:
        """获取预加载的页面"""
        return self._impl.get_preloaded_pages(start_page, count)


# 单例模式
_pagination_calculator = None

def get_pagination_calculator(strategy: str = "smart") -> PaginationCalculator:
    """获取分页计算器实例"""
    global _pagination_calculator
    if _pagination_calculator is None:
        _pagination_calculator = PaginationCalculator(strategy)
    return _pagination_calculator