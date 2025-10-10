
from typing import Dict, List, Optional, Any, Tuple
from textual.widgets import Static
from textual.reactive import reactive
from textual.widgets import Static
from rich.text import Text as RichText
from rich.style import Style
from src.core.pagination.terminal_paginator import TerminalPaginator, PageMetrics
from src.config.settings.setting_observer import SettingObserver, SettingChangeEvent, register_component_observers
from src.themes.theme_manager import ThemeManager

from src.utils.logger import get_logger
from collections import OrderedDict
import asyncio

logger = get_logger(__name__)


class ContentRenderer(Static):
    def force_set_page(self, index_0: int) -> bool:
        """强制设置当前页索引为 0-based 并刷新可见内容"""
        try:
            if not isinstance(index_0, int):
                return False
            tp = int(getattr(self, "total_pages", 0) or 0)
            if tp <= 0:
                return False
            idx = max(0, min(index_0, tp - 1))
            # 设置当前页
            self.current_page = idx
            # 加载页面内容（重置滚动并预热渲染池）
            self._load_page_content(self.current_page)
            # 刷新显示
            if hasattr(self, "_update_visible_content"):
                try:
                    self._update_visible_content()
                except Exception:
                    if hasattr(self, "update_content"):
                        self.update_content()
            else:
                if hasattr(self, "update_content"):
                    self.update_content()
            return True
        except Exception:
            return False
    def force_set_page(self, index_0: int) -> bool:
        """强制设置当前页索引为 0-based 并刷新可见内容"""
        try:
            # 边界检查
            if not isinstance(index_0, int):
                return False
            tp = int(getattr(self, "total_pages", 0) or 0)
            if tp <= 0:
                return False
            idx = max(0, min(index_0, tp - 1))
            # 设置当前页
            self.current_page = idx
            # 关键修复：加载对应页内容，确保可见内容与页码同步
            try:
                self._load_page_content(self.current_page)
            except Exception:
                pass
            # 刷新可见内容
            if hasattr(self, "_update_visible_content"):
                try:
                    self._update_visible_content()
                except Exception:
                    # 兜底：调用 update_content
                    if hasattr(self, "update_content"):
                        self.update_content()
            elif hasattr(self, "update_content"):
                self.update_content()
            return True
        except Exception:
            return False
    """内容渲染器组件 - 优化的分页和滚动实现"""
    
    # 配置项
    config = reactive({})
    
    # 添加CSS类名，确保主题样式正确应用
    DEFAULT_CSS = """
    #content {
        width: 100%;
        height: 100%;
    }
    """
    
    def __init__(
        self,
        container_width: int = 80,
        container_height: int = 24,
        config: Optional[Dict[str, Any]] = None,
        theme_manager: Optional[ThemeManager] = None
    ) -> None:
        """
        初始化内容渲染器
        
        Args:
            container_width: 容器宽度（字符数）
            container_height: 容器高度（行数）
            config: 配置字典
            theme_manager: 主题管理器实例
        """
        super().__init__(id="content")
        self.container_width = container_width
        self.container_height = container_height
        self.config = config or {}
        self.theme_manager = theme_manager
        
        # 分页器 - 使用原有的终端分页器
        self.paginator = TerminalPaginator()
        
        # 内容相关属性 - 使用_original_content避免与Static的content冲突
        self._original_content: str = ""
        self.current_page: int = 0
        self.total_pages: int = 0
        self.current_page_lines: List[str] = []
        self.all_pages: List[List[str]] = []  # 存储所有分页后的页面
        self._scroll_offset: int = 0
        self.visible_lines: int = container_height
        self.metrics: Optional[PageMetrics] = None

        # 渲染池（整页格式化后的行列表），LRU 以页号为键
        self._render_pool: "OrderedDict[int, List[str]]" = OrderedDict()
        self._render_pool_limit: int = int(self.config.get("render_pool_size", 5) or 5)

        # 异步分页任务句柄（用于取消并发任务）
        self._paginate_task: Optional[asyncio.Task] = None
        
        # 设置基本样式 - 应用主题颜色
        self._apply_theme_styles()
        
        # 注册设置观察者，监听相关设置变更
        self._register_setting_observers()
    
    def set_container_size(self, width: int, height: int) -> None:
        """
        设置容器尺寸
        
        Args:
            width: 容器宽度（字符数）
            height: 容器高度（行数）
        """
        # 使用传入的尺寸，但确保最小可用尺寸
        self.container_width = max(40, width)  # 最小40字符宽度
        self.container_height = max(10, height)  # 最小10行高度，不减去额外行数
        self.visible_lines = self.container_height
        
        print(f"DEBUG: ContentRenderer.set_container_size: 传入尺寸={width}x{height}, 最终尺寸={self.container_width}x{self.container_height}")
        logger.debug(f"ContentRenderer.set_container_size: 传入尺寸={width}x{height}, 最终尺寸={self.container_width}x{self.container_height}")
        
        # 如果已经有内容，重新分页
        if self._original_content:
            print(f"DEBUG: 重新分页前内容长度: {len(self._original_content)}")
            self._paginate()
            self._update_visible_content()
            
        logger.debug(f"ContentRenderer.set_container_size: 分页完成，总页数={self.total_pages}")
    
    def set_content(self, content: str) -> None:
        """
        设置内容并进行分页
        
        Args:
            content: 要显示的文本内容
        """
        # 确保内容不为空
        if not content:
            self._original_content = ""
            self.current_page_lines = []
            self.all_pages = []
            self.total_pages = 0
            self._update_visible_content()
            return
            
        # 设置内容并分页 - 确保内容完整保存
        self._original_content = str(content)  # 确保是字符串类型
        
        self._paginate()
        
        # 确保至少有1页
        if not self.all_pages:
            self.all_pages = [[""]]
            self.total_pages = 1
            
        # 加载第一页内容
        self.current_page = 0
        self.current_page_lines = self.all_pages[0]
        self._scroll_offset = 0
        
        # 预热当前页与邻近页到渲染池
        try:
            self._preheat_pages([self.current_page - 1, self.current_page, self.current_page + 1])
        except Exception:
            pass

        # 更新显示
        self._update_visible_content()
        self._calculate_metrics()
    
    def _paginate(self) -> None:
        """对内容进行分页"""
        # 保存当前页面位置
        original_page = self.current_page
        
        # 更精确的度量计算 - 充分利用可用空间
        effective_width = self.container_width
        effective_height = self.container_height
        
        logger.debug(f"ContentRenderer._paginate: 开始分页，有效区域={effective_width}x{effective_height}")
        
        # 计算页面度量并设置到分页器 - 应用用户设置
        line_spacing = int(self.config.get("line_spacing", 0))  # 默认行间距为0
        paragraph_spacing = int(self.config.get("paragraph_spacing", 1))  # 默认段落间距为1
        
        self.paginator.calculate_metrics(
            container_width=effective_width,
            container_height=effective_height,
            line_spacing=line_spacing,
            paragraph_spacing=paragraph_spacing
        )
        
        logger.debug(f"分页间距设置: 行间距={line_spacing}, 段落间距={paragraph_spacing}")
        
        # 使用简单分页策略，确保充分利用容器空间
        pages = self.paginator.paginate(self._original_content)
        
        # 调试信息：显示分页结果
        if pages:
            logger.debug(f"分页结果: 总页数={len(pages)}, 第一页行数={len(pages[0])}")
            if len(pages[0]) > 0:
                logger.debug(f"第一页示例内容: {pages[0][:3]}...")
        
        # 确保至少有一页
        if not pages:
            pages = [[""]]
            
        self.total_pages = len(pages)
        self.all_pages = pages
        
        # 恢复当前页面位置
        self.current_page = min(original_page, self.total_pages - 1) if self.total_pages > 0 else 0
        
        # 加载当前页面内容
        self.current_page_lines = pages[self.current_page] if pages and self.current_page < len(pages) else []
        self._scroll_offset = 0
        self._calculate_metrics()
        
        logger.debug(f"ContentRenderer._paginate: 分页完成，总页数={self.total_pages}, 当前页={self.current_page}, 当前页行数={len(self.current_page_lines)}")
    
    def _calculate_metrics(self) -> None:
        """计算页面度量信息"""
        if not self.current_page_lines:
            self.metrics = None
            return
            
        self.metrics = PageMetrics(
            container_width=self.container_width,
            container_height=self.container_height,
            content_width=self.container_width,
            content_height=len(self.current_page_lines),
            chars_per_line=self.container_width,
            lines_per_page=len(self.current_page_lines)
        )
    
    def get_visible_content(self) -> str:
        """
        获取当前可见内容：优先使用渲染池中的整页格式化结果进行切片，
        降低重复格式化的成本；不足时回退即时格式化。
        """
        if not self.current_page_lines:
            return "暂无内容"

        # 尝试从渲染池获取整页格式化后的行
        formatted_page: Optional[List[str]] = self._render_pool.get(self.current_page)
        if formatted_page is None:
            try:
                formatted_page = self._format_page_lines(self.current_page_lines)
                self._render_pool_put(self.current_page, formatted_page)
            except Exception:
                formatted_page = None

        if formatted_page:
            # 基于格式化整页进行切片
            start_idx = min(self._scroll_offset, max(0, len(formatted_page) - self.visible_lines))
            end_idx = min(start_idx + self.visible_lines, len(formatted_page))
            visible_lines = formatted_page[start_idx:end_idx] if start_idx < len(formatted_page) else []
        else:
            # 回退：仅对可见窗口进行即时格式化
            start_idx = min(self._scroll_offset, max(0, len(self.current_page_lines) - self.visible_lines))
            end_idx = min(start_idx + self.visible_lines, len(self.current_page_lines))
            raw_lines = self.current_page_lines[start_idx:end_idx] if start_idx < len(self.current_page_lines) else []
            visible_lines = self._apply_spacing_to_lines(raw_lines)

        # 填充到容器高度
        while len(visible_lines) < self.visible_lines:
            visible_lines.append("")

        return "\n".join(visible_lines)
    
    def _apply_spacing_to_lines(self, lines: List[str]) -> List[str]:
        """
        对文本行应用行间距和段落间距
        
        Args:
            lines: 原始文本行列表
            
        Returns:
            应用间距后的文本行列表
        """
        if not lines:
            return lines
            
        line_spacing = int(self.config.get("line_spacing", 0))
        paragraph_spacing = int(self.config.get("paragraph_spacing", 0))
        
        formatted_lines = []
        
        for i, line in enumerate(lines):
            # 添加当前行
            formatted_lines.append(line)
            
            # 检查是否是段落结尾（当前行是空行或者下一行是空行）
            is_paragraph_end = (
                line.strip() == "" or  # 当前行是空行
                (i + 1 < len(lines) and lines[i + 1].strip() == "")  # 下一行是空行
            )
            
            # 如果是段落结尾，添加段落间距
            if is_paragraph_end:
                for _ in range(paragraph_spacing):
                    formatted_lines.append("")
            # 如果不是段落结尾且不是最后一行，添加行间距
            elif i < len(lines) - 1:
                for _ in range(line_spacing):
                    formatted_lines.append("")
        
        return formatted_lines
    
    def _apply_theme_styles(self) -> None:
        """应用主题样式到内容渲染器（同时构建富文本调色板）"""
        try:
            theme_name = self.config.get("theme", "dark")

            # 兜底
            def light_dark(default_light: str, default_dark: str) -> str:
                return default_light if "light" in theme_name.lower() else default_dark

            # 默认调色
            palette: Dict[str, Style] = {
                "text": Style(color=light_dark("black", "white")),
                "heading": Style(color=light_dark("black", "white")),
                "link": Style(color="#3B82F6"),
                "quote": Style(color=light_dark("#374151", "#D1D5DB")),
                "code": Style(color="#10B981", bgcolor=light_dark("#E5E7EB", "#1F2937")),
                "highlight": Style(color=light_dark("#000000", "#000000"), bgcolor=light_dark("#FFF8C5", "#EBCB8B")),
            }

            if self.theme_manager and hasattr(self.theme_manager, "themes") and theme_name in self.theme_manager.themes:
                tm = self.theme_manager
                theme = tm.themes[theme_name]

                def pick_color(style_key: str, attr: str) -> Optional[str]:
                    st = theme.get(style_key)
                    if not st:
                        return None
                    val = getattr(st, attr, None)
                    if not val:
                        return None
                    return tm.convert_color_to_string(val)

                # 基础前景/背景
                text_color = pick_color("reader.text", "color") or pick_color("content.text", "color") or light_dark("black", "white")
                bg_color = pick_color("ui.background", "bgcolor") or pick_color("ui.panel", "bgcolor") or light_dark("white", "black")

                # 细分色位
                heading_color = pick_color("reader.chapter", "color") or pick_color("content.heading", "color") or pick_color("app.title", "color") or text_color
                link_color = pick_color("content.link", "color") or pick_color("app.accent", "color") or "#3B82F6"
                quote_color = pick_color("content.quote", "color") or text_color
                code_fg = pick_color("content.code", "color") or "#10B981"
                code_bg = pick_color("content.code", "bgcolor") or (pick_color("ui.panel", "bgcolor") or bg_color)
                hl_fg = pick_color("reader.search_result", "color") or pick_color("content.highlight", "color") or light_dark("#000000", "#000000")
                hl_bg = pick_color("reader.search_result", "bgcolor") or pick_color("content.highlight", "bgcolor") or light_dark("#FFF8C5", "#EBCB8B")

                # 应用到组件样式
                self.styles.background = bg_color
                self.styles.color = text_color

                # 构建 Rich 调色板
                palette["text"] = Style(color=text_color)
                palette["heading"] = Style(color=heading_color, bold=True)
                palette["link"] = Style(color=link_color, underline=True)
                palette["quote"] = Style(color=quote_color, italic=True)
                palette["code"] = Style(color=code_fg, bgcolor=code_bg)
                palette["highlight"] = Style(color=hl_fg, bgcolor=hl_bg)
                logger.debug(f"应用主题样式: {theme_name}, 背景: {bg_color}, 文本: {text_color}")
            else:
                # 无主题管理器或未找到主题：仅基础色
                bg_color, text_color = (("white", "black") if "light" in theme_name.lower() else ("black", "white"))
                self.styles.background = bg_color
                self.styles.color = text_color

            # 存储调色板供渲染使用
            self._palette = palette
            # 代码块围栏状态
            self._code_fence_open = False

            # 内边距
            self.styles.padding = (0, 1)
        except Exception as e:
            logger.error(f"应用主题样式失败: {e}")
            self.styles.background = "white"
            self.styles.color = "black"
            self.styles.padding = (0, 1)
            # 基础调色板兜底
            self._palette = {
                "text": Style(color="black"),
                "heading": Style(color="black", bold=True),
                "link": Style(color="#3B82F6", underline=True),
                "quote": Style(color="#374151", italic=True),
                "code": Style(color="#10B981", bgcolor="#E5E7EB"),
                "highlight": Style(color="#000000", bgcolor="#FFF8C5"),
            }
    

    
    def _update_visible_content(self) -> None:
        """更新可见内容显示（使用 RichText 着色）"""
        text = RichText()
        palette = getattr(self, "_palette", None)

        # 获取可见行（保留现有间距处理）
        raw = self.get_visible_content()
        lines = raw.split("\n")

        import re
        url_re = re.compile(r"(https?://[^\s]+)")

        def is_heading(line: str) -> bool:
            s = line.strip()
            return (s.startswith("#")) or bool(re.match(r"^\s*(第.+章|Chapter|CHAPTER)\b", s))

        def is_quote(line: str) -> bool:
            return line.strip().startswith(">")

        def is_code_line(line: str) -> bool:
            s = line
            return s.startswith("    ") or s.startswith("\t")

        def toggle_code_fence(line: str) -> bool:
            s = line.strip()
            return s.startswith("```")

        for i, line in enumerate(lines):
            style = None

            # 代码围栏切换
            if toggle_code_fence(line):
                self._code_fence_open = not getattr(self, "_code_fence_open", False)
                # 围栏标记本身使用代码样式以示区分
                style = palette and palette.get("code")
            elif getattr(self, "_code_fence_open", False):
                style = palette and palette.get("code")
            elif is_heading(line):
                style = palette and palette.get("heading")
            elif is_quote(line):
                style = palette and palette.get("quote")
            elif is_code_line(line):
                style = palette and palette.get("code")
            else:
                style = palette and palette.get("text")

            # 添加行内容（为 style 提供安全兜底）
            safe_style = style if style is not None else ((palette and palette.get("text")) or Style())
            segment = RichText(line, style=safe_style)

            # 链接着色（只在非代码块内进行）
            if not getattr(self, "_code_fence_open", False):
                for m in url_re.finditer(line):
                    start, end = m.span()
                    if palette and palette.get("link"):
                        segment.stylize(palette["link"], start, end)

            # 追加换行（除最后一行）
            text.append(segment)
            if i < len(lines) - 1:
                text.append("\n")

        # 输出为富文本
        self.update(text)
        self.refresh()
    
    def next_page(self) -> bool:
        """
        翻到下一页
        
        Returns:
            是否成功翻页
        """
        if self.current_page >= self.total_pages - 1:
            logger.debug(f"ContentRenderer.next_page: 无法翻页，当前页={self.current_page}, 总页数={self.total_pages}")
            return False
            
        self.current_page += 1
        logger.debug(f"ContentRenderer.next_page: 翻到下一页，新页码={self.current_page}")
        self._load_page_content(self.current_page)
        return True
    
    def prev_page(self) -> bool:
        """
        翻到上一页
        
        Returns:
            是否成功翻页
        """
        if self.current_page <= 0:
            logger.debug(f"ContentRenderer.prev_page: 无法翻页，当前页={self.current_page}, 总页数={self.total_pages}")
            return False
            
        self.current_page -= 1
        logger.debug(f"ContentRenderer.prev_page: 翻到上一页，新页码={self.current_page}")
        self._load_page_content(self.current_page)
        return True
    
    def _load_page_content(self, page_num: int) -> None:
        """
        加载指定页面的内容，并预热邻近页到渲染池
        """
        if 0 <= page_num < len(self.all_pages):
            self.current_page_lines = self.all_pages[page_num]
            self._scroll_offset = 0
            # 预热当前与邻近页
            try:
                self._preheat_pages([page_num - 1, page_num, page_num + 1])
            except Exception:
                pass
            self._calculate_metrics()
            self._update_visible_content()

    def goto_page(self, page_num: int) -> bool:
        """
        跳转到指定页面
        
        Args:
            page_num: 页码（1-based，用户界面使用）
            
        Returns:
            是否成功跳转
        """
        # 转换为0-based页码
        target_page = page_num - 1
        
        # 调试信息
        logger.debug(f"goto_page: 用户输入页码={page_num}, 转换后页码={target_page}, 总页数={len(self.all_pages)}")
        
        # 检查页码有效性
        if target_page < 0 or target_page >= len(self.all_pages):
            logger.warning(f"goto_page: 页码无效，目标页={target_page}, 有效范围=[0, {len(self.all_pages)-1}]")
            return False
            
        # 跳转到目标页面
        self.current_page = target_page
        self._load_page_content(self.current_page)
        
        logger.debug(f"goto_page: 成功跳转到第{page_num}页（内部页码={target_page}）")
        return True
    
    def content_scroll_down(self, lines: int = 1) -> bool:
        """
        向下滚动内容
        
        Args:
            lines: 滚动行数
            
        Returns:
            是否成功滚动
        """
        if not self.current_page_lines:
            return False
            
        max_offset = max(0, len(self.current_page_lines) - self.visible_lines)
        if max_offset <= 0:
            return False
            
        new_offset = min(self._scroll_offset + lines, max_offset)
        if new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            # 重建渲染池（受行/段落间距影响）
            try:
                self._render_pool_clear()
                # 预热当前与邻近页
                self._preheat_pages([self.current_page - 1, self.current_page, self.current_page + 1])
            except Exception:
                pass
            self._update_visible_content()
            return True
        return False
    
    def content_scroll_up(self, lines: int = 1) -> bool:
        """
        向上滚动内容
        
        Args:
            lines: 滚动行数
            
        Returns:
            是否成功滚动
        """
        if self._scroll_offset <= 0:
            return False
            
        new_offset = max(self._scroll_offset - lines, 0)
        if new_offset != self._scroll_offset:
            self._scroll_offset = new_offset
            self._update_visible_content()
            return True
        return False
    
    def content_scroll_to_top(self) -> bool:
        """
        滚动到页面顶部
        
        Returns:
            是否成功滚动
        """
        if self._scroll_offset <= 0:
            # 已经在顶部，返回true表示操作成功（已经在目标位置）
            return True
            
        self._scroll_offset = 0
        self._update_visible_content()
        return True
    
    def content_scroll_to_bottom(self) -> bool:
        """
        滚动到页面底部
        
        Returns:
            是否成功滚动
        """
        max_offset = max(0, len(self.current_page_lines) - self.visible_lines)
        if self._scroll_offset >= max_offset:
            # 已经在底部或没有更多内容可滚动，返回true表示操作成功
            return True
            
        self._scroll_offset = max_offset
        self._update_visible_content()
        return True
    
    def has_more_content_below(self) -> bool:
        """检查下方是否有更多内容"""
        if not self.current_page_lines:
            return False
        return self._scroll_offset < len(self.current_page_lines) - self.visible_lines
    
    def has_more_content_above(self) -> bool:
        """检查上方是否有更多内容"""
        return self._scroll_offset > 0
    
    def get_progress(self) -> float:
        """获取阅读进度"""
        if self.total_pages == 0:
            return 0.0
        return self.current_page / self.total_pages
    
    def update_content(self) -> None:
        """更新显示内容"""
        visible_content = self.get_visible_content()
        self.update(visible_content)
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置并重新分页"""
        self.config.update(new_config)
        
        # 重新应用主题样式
        self._apply_theme_styles()
        
        # 如果有内容，重新分页以应用新配置
        if self._original_content:
            logger.debug(f"配置更新，重新分页。新配置: {new_config}")
            self._paginate()
            self._update_visible_content()
    
    def get_metrics(self) -> Optional[PageMetrics]:
        """获取当前页面度量"""
        return self.metrics
    
    def get_current_page(self) -> str:
        """获取当前页内容（兼容旧接口）"""
        return self.get_current_page_content()
    
    def get_current_page_content(self) -> str:
        """获取当前页完整内容"""
        if not self.current_page_lines:
            return ""
        return "\n".join(self.current_page_lines)
    
    def _register_setting_observers(self) -> None:
        """注册设置观察者"""
        try:
            from src.config.settings.setting_observer import global_observer_manager, SettingObserver, SettingChangeEvent
            
            # 创建内部观察者类
            class ContentRendererObserver(SettingObserver):
                def __init__(self, renderer):
                    self.renderer = renderer
                
                def on_setting_changed(self, event: SettingChangeEvent) -> None:
                    """设置变更时的回调"""
                    try:
                        logger.debug(f"ContentRenderer: 收到设置变更通知: {event.setting_key} = {event.new_value}")
                        
                        # 更新配置
                        if event.setting_key == "reading.line_spacing":
                            self.renderer.config["line_spacing"] = event.new_value
                        elif event.setting_key == "reading.paragraph_spacing":
                            self.renderer.config["paragraph_spacing"] = event.new_value
                        elif event.setting_key == "reading.font_size":
                            self.renderer.config["font_size"] = event.new_value
                        elif event.setting_key == "theme" or event.setting_key == "appearance.theme":
                            # 主题变更时重新应用主题样式（兼容设置中心键名）
                            self.renderer.config["theme"] = event.new_value
                            self.renderer._apply_theme_styles()
                            logger.debug(f"ContentRenderer: 已应用新主题: {event.new_value}")
                        
                        # 立即重新分页和刷新显示
                        if self.renderer._original_content:
                            # 保存当前页面位置
                            current_page = self.renderer.current_page
                            
                            # 重新分页
                            self.renderer._paginate()
                            
                            # 恢复页面位置（如果可能）
                            if current_page < len(self.renderer.all_pages):
                                self.renderer.current_page = current_page
                                self.renderer._load_page_content(current_page)
                            
                            # 刷新显示
                            self.renderer._update_visible_content()
                            logger.debug(f"ContentRenderer: 已应用设置变更并刷新显示")
                            
                    except Exception as e:
                        logger.error(f"ContentRenderer: 处理设置变更失败: {e}")
            
            # 创建并保存观察者实例
            self._setting_observer = ContentRendererObserver(self)
            
            # 注册监听阅读相关设置
            reading_settings = [
                "reading.line_spacing",
                "reading.paragraph_spacing", 
                "reading.font_size",
                "appearance.theme"
            ]
            
            for setting_key in reading_settings:
                global_observer_manager.register_observer(self._setting_observer, setting_key)
                
            logger.debug("ContentRenderer: 已注册设置观察者")
            
        except Exception as e:
            logger.error(f"注册设置观察者失败: {e}")
    
    def refresh_content(self) -> None:
        """刷新内容显示（公共接口）"""
        if self._original_content:
            self._paginate()
            try:
                self._render_pool_clear()
                self._preheat_pages([self.current_page - 1, self.current_page, self.current_page + 1])
            except Exception:
                pass
            self._update_visible_content()
    
    def _unregister_setting_observers(self) -> None:
        """取消注册设置观察者"""
        try:
            if hasattr(self, '_setting_observer'):
                from src.config.settings.setting_observer import global_observer_manager
                
                reading_settings = [
                    "reading.line_spacing",
                    "reading.paragraph_spacing", 
                    "reading.font_size"
                ]
                
                for setting_key in reading_settings:
                    global_observer_manager.unregister_observer(self._setting_observer, setting_key)
                
                logger.debug("ContentRenderer: 已取消注册设置观察者")
                
        except Exception as e:
            logger.error(f"取消注册设置观察者失败: {e}")

    # 渲染池与异步分页扩展
    def _render_pool_put(self, page_num: int, formatted_lines: List[str]) -> None:
        try:
            if page_num < 0:
                return
            # 更新为最新
            self._render_pool[page_num] = formatted_lines
            self._render_pool.move_to_end(page_num)
            # 超限逐出最旧
            while len(self._render_pool) > max(1, self._render_pool_limit):
                try:
                    self._render_pool.popitem(last=False)
                except Exception:
                    break
        except Exception:
            pass

    def _render_pool_clear(self) -> None:
        try:
            self._render_pool.clear()
        except Exception:
            pass

    def _format_page_lines(self, page_lines: List[str]) -> List[str]:
        """对整页行应用行间距与段落间距，供渲染池缓存"""
        try:
            return self._apply_spacing_to_lines(page_lines or [])
        except Exception:
            return page_lines or []

    def _preheat_pages(self, page_list: List[int]) -> None:
        """预热若干页到渲染池"""
        try:
            for p in page_list:
                if p is None or p < 0 or p >= len(self.all_pages):
                    continue
                if p in self._render_pool:
                    # 更新 LRU 顺序
                    self._render_pool.move_to_end(p)
                    continue
                formatted = self._format_page_lines(self.all_pages[p])
                self._render_pool_put(p, formatted)
        except Exception:
            pass

    async def async_paginate_and_render(self, content: str) -> None:
        """
        异步设置内容与分页，完成后预热并通知 UI 刷新。
        如果已有运行中的任务，会先取消旧任务避免并发重复计算。
        """
        # 取消旧任务
        try:
            if self._paginate_task and not self._paginate_task.done():
                self._paginate_task.cancel()
        except Exception:
            pass

        async def _do():
            def _compute():
                self._original_content = str(content or "")
                self._paginate()
                try:
                    self._render_pool_clear()
                    self._preheat_pages([self.current_page - 1, self.current_page, self.current_page + 1])
                except Exception:
                    pass
                return True

            try:
                await asyncio.to_thread(_compute)
                # 通知 UI 刷新
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
            except asyncio.CancelledError:
                # 任务被取消，静默结束
                return
            except Exception:
                # 失败时不抛给 UI
                return

        # 在当前事件循环中启动任务
        try:
            loop = asyncio.get_running_loop()
            self._paginate_task = loop.create_task(_do())
        except RuntimeError:
            # 无事件循环，则直接运行（可能阻塞）
            try:
                import asyncio as _aio
                _aio.run(_do())
            except Exception:
                pass