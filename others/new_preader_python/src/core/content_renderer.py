"""
内容渲染器模块 - 负责文本内容的分页、渲染和显示逻辑
采用面向对象设计，与UI层解耦，支持多种渲染策略
"""

import re

from typing import Dict, List, Optional, Tuple, Callable, Any
from abc import ABC, abstractmethod

from src.utils.logger import get_logger

logger = get_logger(__name__)

class RenderStrategy(ABC):
    """渲染策略抽象基类"""
    
    @abstractmethod
    def paginate(self, content: str, config: Dict[str, Any]) -> List[str]:
        """将内容分页"""
        pass
    
    @abstractmethod
    def render_page(self, page_content: str, config: Dict[str, Any]) -> str:
        """渲染单页内容"""
        pass

class SimpleTextRenderStrategy(RenderStrategy):
    """简单文本渲染策略"""
    
    def paginate(self, content: str, config: Dict[str, Any]) -> List[str]:
        """分页内容 - 使用动态分页，由DynamicContentRenderer处理"""
        # 动态分页由专门的DynamicContentRenderer组件处理
        # 这里保持简单的单页显示，避免重复分页逻辑
        return [content]
    
    def render_page(self, page_content: str, config: Dict[str, Any]) -> str:
        """简单渲染，保持原样"""
        return page_content

class ChapterAwareRenderStrategy(RenderStrategy):
    """章节感知渲染策略"""
    
    def paginate(self, content: str, config: Dict[str, Any]) -> List[str]:
        """基于章节信息分页"""
        chapters = config.get("chapters", [])
        if not chapters:
            # 如果没有章节信息，使用简单分页
            simple_strategy = SimpleTextRenderStrategy()
            return simple_strategy.paginate(content, config)
        
        pages = []
        for chapter in chapters:
            start = chapter.get("start", 0)
            end = chapter.get("end", len(content))
            chapter_content = content[start:end]
            
            # 对每个章节内容进行分页
            simple_strategy = SimpleTextRenderStrategy()
            chapter_pages = simple_strategy.paginate(chapter_content, config)
            pages.extend(chapter_pages)
        
        return pages
    
    def render_page(self, page_content: str, config: Dict[str, Any]) -> str:
        """渲染页面，添加章节标题"""
        current_chapter = config.get("current_chapter", 0)
        chapters = config.get("chapters", [])
        
        if chapters and current_chapter < len(chapters):
            chapter_title = chapters[current_chapter].get("title", f"第{current_chapter + 1}章")
            return f"{chapter_title}\n\n{page_content}"
        
        return page_content

class ContentRenderer:
    """内容渲染器 - 核心渲染组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化内容渲染器
        
        Args:
            config: 渲染配置
        """
        self.config = config
        self.strategies: Dict[str, RenderStrategy] = {
            "simple": SimpleTextRenderStrategy(),
            "chapter_aware": ChapterAwareRenderStrategy()
        }
        self.current_strategy = "simple"
        
        # 状态管理
        self.content: Optional[str] = None
        self.pages: List[str] = []
        self.rendered_pages: List[str] = []
        self.current_page = 0
        self.total_pages = 0
    
    def set_content(self, content: str) -> None:
        """设置要渲染的内容"""
        self.content = content
        self._paginate()
        self._render_all_pages()
    
    def set_strategy(self, strategy_name: str) -> bool:
        """设置渲染策略"""
        if strategy_name in self.strategies:
            self.current_strategy = strategy_name
            self._render_all_pages()
            return True
        return False
    
    def _paginate(self) -> None:
        """分页内容"""
        if not self.content:
            self.pages = []
            self.total_pages = 0
            return
        
        strategy = self.strategies[self.current_strategy]
        self.pages = strategy.paginate(self.content, self.config)
        self.total_pages = len(self.pages)
    
    def _render_all_pages(self) -> None:
        """渲染所有页面"""
        self.rendered_pages = []
        for i, page_content in enumerate(self.pages):
            render_config = self.config.copy()
            render_config["current_chapter"] = self._get_chapter_for_page(i)
            rendered = self.strategies[self.current_strategy].render_page(
                page_content, render_config
            )
            self.rendered_pages.append(rendered)
    
    def _get_chapter_for_page(self, page_num: int) -> int:
        """根据页码确定所属章节"""
        if not self.config.get("chapters"):
            return 0
        
        chapters = self.config["chapters"]
        cumulative_length = 0
        
        for chapter_idx, chapter in enumerate(chapters):
            chapter_length = chapter.get("end", 0) - chapter.get("start", 0)
            cumulative_length += chapter_length
            
            # 简单估算：假设每页平均长度
            avg_page_length = len(self.content) / self.total_pages if self.total_pages > 0 else 0
            if avg_page_length > 0:
                chapter_pages = chapter_length / avg_page_length
                if page_num < cumulative_length / avg_page_length:
                    return chapter_idx
        
        return len(chapters) - 1
    
    def get_current_page(self) -> str:
        """获取当前页渲染内容"""
        if not self.rendered_pages or self.current_page >= len(self.rendered_pages):
            return ""
        return self.rendered_pages[self.current_page]
    
    def get_page(self, page_num: int) -> str:
        """获取指定页码的渲染内容"""
        if not self.rendered_pages or page_num < 0 or page_num >= len(self.rendered_pages):
            return ""
        return self.rendered_pages[page_num]
    
    def next_page(self) -> bool:
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            return True
        return False
    
    def prev_page(self) -> bool:
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
    
    def goto_page(self, page_num: int) -> bool:
        """跳转到指定页"""
        if 0 <= page_num < self.total_pages:
            self.current_page = page_num
            return True
        return False
    
    def get_progress(self) -> float:
        """获取阅读进度"""
        if self.total_pages == 0:
            return 0.0
        return self.current_page / self.total_pages
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置并重新渲染"""
        self.config.update(new_config)
        if self.content:
            self._paginate()
            self._render_all_pages()

