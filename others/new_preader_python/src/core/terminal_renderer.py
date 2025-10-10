"""
终端内容渲染器 - 专门针对终端环境优化的动态分页
采用面向对象设计，支持实时窗口尺寸计算和智能分页
"""

import re

from typing import Dict, List, Optional, Tuple, Callable, Any
from abc import ABC, abstractmethod
import math

from src.utils.logger import get_logger
from src.utils.cache_manager import paginate_cache, make_key
import asyncio

logger = get_logger(__name__)

class TerminalRenderStrategy(ABC):
    """终端渲染策略抽象基类"""
    
    @abstractmethod
    def paginate(self, content: str, container_size: Tuple[int, int], 
                config: Dict[str, Any]) -> List[str]:
        """将内容分页，考虑终端窗口尺寸"""
        pass
    
    @abstractmethod
    def render_page(self, page_content: str, config: Dict[str, Any]) -> str:
        """渲染单页内容"""
        pass

class SmartTerminalStrategy(TerminalRenderStrategy):
    """智能终端渲染策略 - 支持智能分页和格式优化"""
    
    def paginate(self, content: str, container_size: Tuple[int, int], 
                config: Dict[str, Any]) -> List[str]:
        """
        智能分页 - 基于终端窗口尺寸
        
        Args:
            content: 原始内容
            container_size: 容器尺寸 (width, height)
            config: 渲染配置
            
        Returns:
            List[str]: 分页后的内容列表
        """
        width, height = container_size
        
        # 计算有效显示区域（考虑边距）
        effective_width = max(1, width - 4)  # 左右各2字符边距
        effective_height = max(1, height - 4)  # 上下各2字符边距
        
        if not content:
            return []
        
        # 预处理内容：移除多余空行，统一换行符
        processed_content = self._preprocess_content(content)
        
        # 智能分页
        pages = []
        remaining_content = processed_content
        
        while remaining_content:
            page_content = self._get_smart_page(
                remaining_content, effective_width, effective_height, config
            )
            pages.append(page_content)
            remaining_content = remaining_content[len(page_content):].lstrip()
        
        return pages
    
    def _preprocess_content(self, content: str) -> str:
        """预处理内容"""
        # 统一换行符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除连续空行，最多保留2个空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除行首行尾空白
        lines = content.split('\n')
        processed_lines = [line.strip() for line in lines if line.strip()]
        
        return '\n'.join(processed_lines)
    
    def _get_smart_page(self, content: str, width: int, height: int, 
                       config: Dict[str, Any]) -> str:
        """
        智能获取页面内容
        
        Args:
            content: 剩余内容
            width: 有效宽度
            height: 有效高度
            config: 配置
            
        Returns:
            str: 页面内容
        """
        # 计算最大字符数
        max_chars = width * height
        
        if len(content) <= max_chars:
            return content
        
        # 查找段落边界
        paragraph_end = self._find_paragraph_boundary(content, max_chars)
        if paragraph_end > 0:
            return content[:paragraph_end]
        
        # 查找句子边界
        sentence_end = self._find_sentence_boundary(content, max_chars)
        if sentence_end > 0:
            return content[:sentence_end]
        
        # 查找行边界
        line_end = self._find_line_boundary(content, width, max_chars)
        if line_end > 0:
            return content[:line_end]
        
        # 最后在单词边界处分页
        word_end = self._find_word_boundary(content, max_chars)
        if word_end > 0:
            return content[:word_end]
        
        # 如果都找不到合适的边界，就在最大字符数处分页
        return content[:max_chars]
    
    def _find_paragraph_boundary(self, content: str, max_pos: int) -> int:
        """查找段落边界"""
        # 查找段落分隔符（两个换行符）
        para_pos = content.rfind('\n\n', 0, max_pos)
        if para_pos > 0:
            return para_pos + 2  # 包含分隔符
        
        # 查找章节标题
        chapter_patterns = [
            r'第[一二三四五六七八九十百千万零]+章',
            r'第\d+章',
            r'CHAPTER \d+',
            r'SECTION \d+'
        ]
        
        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, content[:max_pos]))
            if matches:
                last_match = matches[-1]
                # 在章节标题前分页
                if last_match.start() > 0:
                    return last_match.start()
        
        return 0
    
    def _find_sentence_boundary(self, content: str, max_pos: int) -> int:
        """查找句子边界"""
        sentence_enders = ['. ', '? ', '! ', '。', '？', '！', '."', '?"', '!"']
        
        for ender in sentence_enders:
            pos = content.rfind(ender, 0, max_pos)
            if pos > 0:
                return pos + len(ender)
        
        return 0
    
    def _find_line_boundary(self, content: str, width: int, max_pos: int) -> int:
        """查找行边界"""
        # 基于终端宽度查找换行位置
        lines = []
        current_pos = 0
        
        while current_pos < max_pos and current_pos < len(content):
            # 查找下一个换行符或行尾
            next_newline = content.find('\n', current_pos)
            if next_newline == -1 or next_newline >= max_pos:
                next_newline = max_pos
            
            line_content = content[current_pos:next_newline]
            
            # 如果行太长，需要智能换行
            if len(line_content) > width:
                # 在单词边界处换行
                break_pos = self._find_word_break(line_content, width)
                if break_pos > 0:
                    lines.append(line_content[:break_pos])
                    current_pos += break_pos
                else:
                    # 强制在宽度处分行
                    lines.append(line_content[:width])
                    current_pos += width
            else:
                lines.append(line_content)
                current_pos = next_newline + 1 if next_newline < len(content) else len(content)
        
        return current_pos
    
    def _find_word_boundary(self, content: str, max_pos: int) -> int:
        """查找单词边界"""
        # 查找空格分界
        space_pos = content.rfind(' ', 0, max_pos)
        if space_pos > 0:
            return space_pos + 1
        
        # 查找标点符号分界
        punctuation = [',', ';', ':', '，', '；', '：']
        for punc in punctuation:
            punc_pos = content.rfind(punc, 0, max_pos)
            if punc_pos > 0:
                return punc_pos + 1
        
        return 0
    
    def _find_word_break(self, line: str, width: int) -> int:
        """查找单词断点"""
        if len(line) <= width:
            return len(line)
        
        # 查找最后一个空格位置
        last_space = line.rfind(' ', 0, width)
        if last_space > 0:
            return last_space
        
        # 查找连字符
        hyphen_pos = line.rfind('-', 0, width)
        if hyphen_pos > 0:
            return hyphen_pos + 1
        
        # 如果找不到合适的断点，就在宽度处强制断开
        return width
    
    def render_page(self, page_content: str, config: Dict[str, Any]) -> str:
        """渲染页面内容"""
        # 应用基本格式
        lines = page_content.split('\n')
        formatted_lines = []
        
        for line in lines:
            # 移除行首行尾空白
            cleaned_line = line.strip()
            if cleaned_line:
                formatted_lines.append(cleaned_line)
        
        # 添加段落间距
        formatted_content = '\n'.join(formatted_lines)
        
        # 如果有章节信息，添加章节标题
        current_chapter = config.get('current_chapter')
        chapters = config.get('chapters', [])
        
        if current_chapter is not None and chapters and current_chapter < len(chapters):
            chapter_title = chapters[current_chapter].get('title', f'第{current_chapter + 1}章')
            formatted_content = f"{chapter_title}\n\n{formatted_content}"
        
        return formatted_content

class TerminalContentRenderer:
    """终端内容渲染器 - 核心渲染组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化终端内容渲染器
        
        Args:
            config: 渲染配置
        """
        self.config = config
        self.strategies: Dict[str, TerminalRenderStrategy] = {
            'smart': SmartTerminalStrategy()
        }
        self.current_strategy = 'smart'
        
        # 状态管理
        self.content: Optional[str] = None
        self.pages: List[str] = []
        self.rendered_pages: List[str] = []
        self.current_page = 0
        self.total_pages = 0
        self.container_size: Tuple[int, int] = (80, 24)  # 默认终端尺寸
        self._last_content_hash: str = ""
    
    def set_content(self, content: str) -> None:
        """设置要渲染的内容（优先使用缓存）"""
        self.content = content
        # 计算缓存键
        key = self._make_cache_key(content)
        cached = paginate_cache.get(key)
        if cached and isinstance(cached, dict) and "pages" in cached and "rendered" in cached:
            self.pages = cached["pages"]
            self.rendered_pages = cached["rendered"]
            self.total_pages = len(self.pages)
        # 更新内容哈希
        try:
            import hashlib
            safe_content = self.content or ""
            self._last_content_hash = hashlib.sha256(safe_content.encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            self._last_content_hash = "len:" + str(len(self.content or ""))
            return
        self._paginate()
        self._render_all_pages()
        # 写入缓存
        try:
            paginate_cache.set(key, {"pages": self.pages, "rendered": self.rendered_pages}, ttl_seconds=1800)
        except Exception:
            pass
    
    def set_container_size(self, width: int, height: int) -> None:
        """设置容器尺寸（触发分页缓存检查）"""
        if width != self.container_size[0] or height != self.container_size[1]:
            self.container_size = (width, height)
            if self.content:
                key = self._make_cache_key(self.content)
                cached = paginate_cache.get(key)
                if cached and isinstance(cached, dict):
                    self.pages = cached.get("pages", [])
                    self.rendered_pages = cached.get("rendered", [])
                    self.total_pages = len(self.pages)
                    if self.pages and self.rendered_pages:
                        return
                self._paginate()
                self._render_all_pages()
                try:
                    paginate_cache.set(key, {"pages": self.pages, "rendered": self.rendered_pages}, ttl_seconds=1800)
                except Exception:
                    pass
    
    def set_strategy(self, strategy_name: str) -> bool:
        """设置渲染策略"""
        if strategy_name in self.strategies:
            self.current_strategy = strategy_name
            if self.content:
                self._paginate()
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
        self.pages = strategy.paginate(
            self.content, self.container_size, self.config
        )
        self.total_pages = len(self.pages)
    
    def _render_all_pages(self) -> None:
        """渲染所有页面"""
        self.rendered_pages = []
        for i, page_content in enumerate(self.pages):
            render_config = self.config.copy()
            render_config['current_chapter'] = self._get_chapter_for_page(i)
            rendered = self.strategies[self.current_strategy].render_page(
                page_content, render_config
            )
            self.rendered_pages.append(rendered)

    def _get_chapter_for_page(self, page_num: int) -> int:
        """根据页码确定所属章节"""
        if not self.config.get('chapters'):
            return 0
        chapters = self.config.get('chapters', [])
        cumulative_chars = 0
        content_str = self.content or ""
        for chapter_idx, chapter in enumerate(chapters):
            start = chapter.get('start', 0)
            end = chapter.get('end', len(content_str))
            chapter_length = max(0, end - start)
            if self.total_pages > 0 and content_str:
                avg_page_length = len(content_str) / max(1, self.total_pages)
                chapter_pages = chapter_length / avg_page_length if avg_page_length > 0 else 0
                if page_num < (cumulative_chars / avg_page_length) + chapter_pages:
                    return chapter_idx
            cumulative_chars += chapter_length
        return max(0, len(chapters) - 1)
    
    def _make_cache_key(self, content: str) -> Tuple[Any, ...]:
        """生成分页缓存键"""
        # 内容哈希
        try:
            import hashlib
            content_hash = hashlib.sha256((content or "").encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            content_hash = str(len(content or ""))
        return make_key("paginate",
                        content_hash,
                        self.container_size,
                        self.current_strategy,
                        {
                            "font_size": self.config.get("reading", {}).get("font_size"),
                            "line_spacing": self.config.get("reading", {}).get("line_spacing"),
                            "paragraph_spacing": self.config.get("reading", {}).get("paragraph_spacing"),
                            "chapters_len": len(self.config.get("chapters", []))
                        })

    async def async_paginate_and_render(self, content: str) -> None:
        """
        异步计算分页与渲染，完成后写入缓存并通知 UI 刷新
        """
        key = self._make_cache_key(content)
        cached = paginate_cache.get(key)
        if cached and isinstance(cached, dict) and "pages" in cached and "rendered" in cached:
            self.pages = cached["pages"]
            self.rendered_pages = cached["rendered"]
            self.total_pages = len(self.pages)
            return

        def _compute():
            self.content = content
            self._paginate()
            self._render_all_pages()
            return {"pages": self.pages, "rendered": self.rendered_pages}

        try:
            result = await asyncio.to_thread(_compute)
            paginate_cache.set(key, result, ttl_seconds=1800)
            # 发送刷新消息
            try:
                import importlib
                msg_mod = importlib.import_module("src.ui.messages")
                RefreshContentMessage = getattr(msg_mod, "RefreshContentMessage", None)
                app_mod = importlib.import_module("src.ui.app")
                get_app_instance = getattr(app_mod, "get_app_instance", None)
                app = get_app_instance() if get_app_instance else None
                if app and RefreshContentMessage:
                    app.post_message(RefreshContentMessage())
            except Exception:
                pass
        except Exception:
            pass
    
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
        """更新配置并重新渲染（带缓存）"""
        self.config.update(new_config)
        if self.content:
            key = self._make_cache_key(self.content)
            cached = paginate_cache.get(key)
            if cached and isinstance(cached, dict):
                self.pages = cached.get("pages", [])
                self.rendered_pages = cached.get("rendered", [])
                self.total_pages = len(self.pages)
                if self.pages and self.rendered_pages:
                    return
            self._paginate()
            self._render_all_pages()
            try:
                paginate_cache.set(key, {"pages": self.pages, "rendered": self.rendered_pages}, ttl_seconds=1800)
            except Exception:
                pass

# 工厂函数
def create_terminal_renderer(config: Dict[str, Any]) -> TerminalContentRenderer:
    """创建终端内容渲染器"""
    return TerminalContentRenderer(config)