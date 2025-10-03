
from typing import Dict, List, Optional, Any, Tuple
from textual.widgets import Static
from textual.reactive import reactive
from textual.widgets import Static
from rich.text import Text as RichText
from rich.style import Style
from src.core.pagination.terminal_paginator import TerminalPaginator, PageMetrics
from src.config.settings.setting_observer import SettingObserver, SettingChangeEvent, register_component_observers

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ContentRenderer(Static):
    """内容渲染器组件 - 优化的分页和滚动实现"""
    
    # 配置项
    config = reactive({})
    
    def __init__(
        self,
        container_width: int = 80,
        container_height: int = 24,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        初始化内容渲染器
        
        Args:
            container_width: 容器宽度（字符数）
            container_height: 容器高度（行数）
            config: 配置字典
        """
        super().__init__()
        self.container_width = container_width
        self.container_height = container_height
        self.config = config or {}
        
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
        获取当前可见内容，应用行间距和段落间距
        
        Returns:
            当前可见的文本内容
        """
        if not self.current_page_lines:
            return "暂无内容"
            
        # 计算可见行范围，确保不超出边界
        start_idx = min(self._scroll_offset, max(0, len(self.current_page_lines) - self.visible_lines))
        end_idx = min(start_idx + self.visible_lines, len(self.current_page_lines))
        
        # 获取可见行，确保不超出列表范围
        visible_lines = self.current_page_lines[start_idx:end_idx] if start_idx < len(self.current_page_lines) else []
        
        # 应用行间距和段落间距
        formatted_lines = self._apply_spacing_to_lines(visible_lines)
        
        # 如果格式化后的行数少于容器高度，用空行填充
        while len(formatted_lines) < self.visible_lines:
            formatted_lines.append("")
        
        return "\n".join(formatted_lines)
    
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
        """应用主题样式到内容渲染器"""
        try:
            # 获取当前主题名称
            theme_name = self.config.get("theme", "dark")
            
            # 定义浅色主题列表
            light_themes = [
                "light", "github-light", "solarized-light", "transparent-light",
                "paper-white", "cream", "sky-blue", "mint-green", "lavender"
            ]
            
            # 根据主题名称设置对应的颜色 - 使用更多样化的字体颜色
            if theme_name == "light":
                self.styles.background = "white"
                self.styles.color = "#2c3e50"  # 深蓝灰色，比纯黑更柔和
            elif theme_name == "github-light":
                self.styles.background = "#ffffff"
                self.styles.color = "#1f2328"  # GitHub风格的深灰色
            elif theme_name == "solarized-light":
                self.styles.background = "#fdf6e3"
                self.styles.color = "#586e75"  # 太阳能化的蓝灰色
            elif theme_name == "transparent-light":
                self.styles.background = "white"
                self.styles.color = "#37474f"  # 材料设计的深蓝灰色
            elif theme_name == "paper-white":
                self.styles.background = "white"
                self.styles.color = "#263238"  # 深石板灰色
            elif theme_name == "cream":
                self.styles.background = "#fff8e1"
                self.styles.color = "#5d4037"  # 温暖的深棕色
            elif theme_name == "sky-blue":
                self.styles.background = "#e3f2fd"
                self.styles.color = "#1565c0"  # 明亮的深蓝色
            elif theme_name == "mint-green":
                self.styles.background = "#e8f5e9"
                self.styles.color = "#2e7d32"  # 清新的深绿色
            elif theme_name == "lavender":
                self.styles.background = "#f3e5f5"
                self.styles.color = "#6a1b9a"  # 优雅的深紫色
            else:
                # 默认暗色主题 - 使用多样化的背景和字体颜色
                if theme_name == "dark":
                    self.styles.background = "#1a1a1a"  # 深灰色背景
                    self.styles.color = "#e0e0e0"  # 浅灰色字体
                elif theme_name == "nord":
                    self.styles.background = "#2e3440"  # Nord深蓝色背景
                    self.styles.color = "#e5e9f0"  # 北极浅蓝色字体
                elif theme_name == "dracula":
                    self.styles.background = "#282a36"  # Dracula深紫色背景
                    self.styles.color = "#8BE9FD"  # Dracula浅蓝色字体
                elif theme_name == "material":
                    self.styles.background = "#263238"  # Material深蓝灰色背景
                    self.styles.color = "#e0e0e0"  # 材料浅灰色字体
                elif theme_name == "github-dark":
                    self.styles.background = "#0d1117"  # GitHub深蓝色背景
                    self.styles.color = "#f0f6fc"  # GitHub浅蓝色字体
                elif theme_name == "solarized-dark":
                    self.styles.background = "#002b36"  # Solarized深蓝绿色背景
                    self.styles.color = "#eee8d5"  # 太阳能化米色字体
                elif theme_name == "amethyst":
                    self.styles.background = "#2d1b69"  # 紫水晶深紫色背景
                    self.styles.color = "#e0d6ff"  # 紫水晶浅紫色字体
                elif theme_name == "forest-green":
                    self.styles.background = "#1b4332"  # 森林深绿色背景
                    self.styles.color = "#e8f5e9"  # 森林浅绿色字体
                elif theme_name == "crimson":
                    self.styles.background = "#590d22"  # 深红色背景
                    self.styles.color = "#ffe4e1"  # 深红浅粉色字体
                elif theme_name == "slate":
                    self.styles.background = "#2f3e46"  # 石板深灰色背景
                    self.styles.color = "#f5f5f5"  # 石板浅灰色字体
                elif theme_name == "transparent-dark":
                    self.styles.background = "black"  # 纯黑背景
                    self.styles.color = "#e6e9ed"  # 透明浅灰色字体
                else:
                    self.styles.background = "black"  # 默认黑色背景
                    self.styles.color = "white"  # 默认白色字体
            
            # 设置内边距
            self.styles.padding = (0, 1)
            
            logger.debug(f"应用主题样式: {theme_name}, 背景: {self.styles.background}, 文字: {self.styles.color}")
            
        except Exception as e:
            logger.error(f"应用主题样式失败: {e}")
            # 出错时使用默认样式
            self.styles.background = "white"
            self.styles.color = "black"
            self.styles.padding = (0, 1)
    
    def _update_visible_content(self) -> None:
        """更新可见内容显示"""
        visible_content = self.get_visible_content()
        
        # 直接更新文本内容，使用组件自身样式（self.styles.color）
        self.update(visible_content)
        
        # 强制刷新样式，确保字体颜色被应用
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
        加载指定页面的内容
        
        Args:
            page_num: 页码（0-based）
        """
        if 0 <= page_num < len(self.all_pages):
            self.current_page_lines = self.all_pages[page_num]
            self._scroll_offset = 0
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