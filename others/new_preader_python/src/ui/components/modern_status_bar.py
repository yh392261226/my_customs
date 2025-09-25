"""
现代化状态栏组件 - 美观的底部状态信息显示
采用现代化设计语言，支持图标、动画和响应式布局
"""

from typing import Dict, Any, List, Optional, ClassVar, Union
from dataclasses import dataclass
from enum import Enum
from textual.widgets import Static, Label, ProgressBar
from textual.containers import Horizontal, Container, Grid
from textual.reactive import reactive
from textual.app import ComposeResult
import time

class StatusBarTheme(Enum):
    """状态栏主题枚举"""
    LIGHT = "light"
    DARK = "dark"
    MINIMAL = "minimal"
    COMPACT = "compact"

class StatusBarLayout(Enum):
    """状态栏布局枚举"""
    HORIZONTAL = "horizontal"
    GRID = "grid"
    STACKED = "stacked"
    FLOATING = "floating"

@dataclass
class StatusBarConfig:
    """状态栏配置"""
    theme: StatusBarTheme = StatusBarTheme.LIGHT
    layout: StatusBarLayout = StatusBarLayout.HORIZONTAL
    show_icons: bool = True
    show_progress: bool = True
    show_stats: bool = True
    show_shortcuts: bool = True
    animation_enabled: bool = True
    compact_mode: bool = False
    opacity: float = 0.95

class ModernStatusBar(Container):
    """现代化状态栏组件"""
    
    CSS = """
    ModernStatusBar {
        height: auto;
        padding: 0.5rem 1rem;
        background: $surface;
        border-top: solid 1px $border;
        transition: all 0.3s ease;
    }
    
    .status-bar-light {
        background: #ffffff;
        color: #1e293b;
        border-color: #e2e8f0;
    }
    
    .status-bar-dark {
        background: #1e293b;
        color: #f1f5f9;
        border-color: #334155;
    }
    
    .status-bar-minimal {
        background: transparent;
        border: none;
    }
    
    .status-bar-compact {
        padding: 0.25rem 0.5rem;
        height: 2rem;
    }
    
    .status-bar-floating {
        border-radius: 0.75rem;
        margin: 0.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: none;
    }
    
    .status-content {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    
    .status-horizontal {
        layout: horizontal;
        align: center space-between;
        height: 100%;
    }
    
    .status-grid {
        layout: grid;
        grid-size: 3;
        grid-gutter: 1;
        align: center middle;
    }
    
    .status-stacked {
        layout: vertical;
        align: center middle;
    }
    
    .stat-item {
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        background: $background;
        margin: 0 0.25rem;
        min-width: 4rem;
        text-align: center;
    }
    
    .stat-item:hover {
        background: $primary-lighten-3;
    }
    
    .stat-label {
        font-size: 0.75rem;
        color: $text-muted;
        margin-bottom: 0.125rem;
    }
    
    .stat-value {
        font-size: 0.875rem;
        font-weight: bold;
        color: $text;
    }
    
    .shortcut-item {
        padding: 0.25rem 0.5rem;
        background: $primary-lighten-3;
        border-radius: 0.375rem;
        margin: 0 0.25rem;
        font-size: 0.75rem;
    }
    
    .shortcut-key {
        background: $primary;
        color: white;
        padding: 0.125rem 0.25rem;
        border-radius: 0.25rem;
        margin-right: 0.25rem;
        font-weight: bold;
    }
    
    .progress-container {
        width: 100%;
        height: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .modern-progress {
        width: 100%;
        height: 100%;
        background: $background;
        border-radius: 0.25rem;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        background: $primary;
        border-radius: 0.25rem;
        transition: width 0.3s ease;
    }
    
    .progress-text {
        font-size: 0.75rem;
        color: $text-muted;
        text-align: center;
        margin-top: 0.25rem;
    }
    
    /* 图标样式 */
    .stat-icon {
        margin-right: 0.25rem;
        font-size: 0.875rem;
    }
    
    /* 动画效果 */
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .animate-in {
        animation: fade-in 0.3s ease-out;
    }
    """
    
    def __init__(self, config: Optional[StatusBarConfig] = None):
        """
        初始化现代化状态栏
        
        Args:
            config: 状态栏配置
        """
        super().__init__(id="modern-status-bar")
        self.config = config or StatusBarConfig()
        
        # 状态数据
        self.current_page: int = 0
        self.total_pages: int = 0
        self.reading_time: int = 0
        self.reading_speed: float = 0.0
        self.words_read: int = 0
        self.total_words: int = 0
        self.progress: float = 0.0
        
        # 快捷键配置
        self.shortcuts = [
            {"key": "←/→", "desc": "翻页", "icon": "↔"},
            {"key": "G", "desc": "跳转", "icon": "🔍"},
            {"key": "B", "desc": "书签", "icon": "🔖"},
            {"key": "S", "desc": "搜索", "icon": "🔎"},
            {"key": "A", "desc": "自动", "icon": "⏯"},
            {"key": "T", "desc": "主题", "icon": "🎨"}
        ]
        
        # 图标映射
        self.icons = {
            "page": "📄",
            "time": "⏱",
            "speed": "🚀", 
            "words": "📝",
            "progress": "📊"
        }

    def compose(self) -> ComposeResult:
        """组合状态栏界面"""
        # 根据布局选择不同的容器
        if self.config.layout == StatusBarLayout.GRID:
            container = Grid(classes="status-content status-grid")
        elif self.config.layout == StatusBarLayout.STACKED:
            container = Container(classes="status-content status-stacked")
        else:
            container = Horizontal(classes="status-content status-horizontal")
        
        # 返回主容器
        yield container
        
        # 存储容器引用，用于后续挂载
        self._main_container = container
        self._pending_sections = {
            'shortcuts': self.config.show_shortcuts,
            'stats': self.config.show_stats,
            'progress': self.config.show_progress
        }

    def on_mount(self) -> None:
        """组件挂载后处理挂载逻辑"""
        # 在主容器挂载后添加子组件
        if self._pending_sections['shortcuts']:
            self._mount_shortcuts_section(self._main_container)
        
        if self._pending_sections['stats']:
            self._mount_stats_section(self._main_container)
        
        if self._pending_sections['progress']:
            self._mount_progress_section(self._main_container)
        
        # 清空待处理状态
        self._pending_sections.clear()

    def _create_shortcuts_section(self) -> Horizontal:
        """创建快捷键区域"""
        shortcuts_container = Horizontal(classes="shortcuts-section")
        
        for shortcut in self.shortcuts:
            shortcut_text = f"{shortcut['icon']} {shortcut['key']}"
            if not self.config.compact_mode:
                shortcut_text += f": {shortcut['desc']}"
            
            shortcut_label = Label(shortcut_text, classes="shortcut-item")
            shortcuts_container.mount(shortcut_label)
        
        return shortcuts_container

    def _create_stats_section(self) -> Horizontal:
        """创建统计信息区域"""
        stats_container = Horizontal(classes="stats-section")
        
        # 页码信息
        stats_container.mount(self._create_stat_item(
            "page", "页码", f"{self.current_page}/{self.total_pages}"
        ))
        
        # 阅读时间
        stats_container.mount(self._create_stat_item(
            "time", "时间", self._format_time(self.reading_time)
        ))
        
        # 阅读速度
        stats_container.mount(self._create_stat_item(
            "speed", "速度", f"{self.reading_speed:.1f}字/分"
        ))
        
        # 字数统计
        stats_container.mount(self._create_stat_item(
            "words", "字数", f"{self.words_read}/{self.total_words}"
        ))
        
        return stats_container

    def _create_stat_item(self, icon_type: str, label: str, value: str) -> Container:
        """创建统计信息项"""
        icon = self.icons.get(icon_type, "📊") if self.config.show_icons else ""
        
        return Container(
            Label(f"{icon} {label}", classes="stat-label"),
            Label(value, classes="stat-value"),
            classes="stat-item animate-in"
        )

    def _create_progress_section(self) -> Container:
        """创建进度条区域"""
        progress_container = Container(classes="progress-section")
        
        # 进度条
        progress_bar = Container(
            Container(classes="progress-bar", styles={"width": f"{self.progress}%"}),
            classes="modern-progress"
        )
        
        # 进度文本
        progress_text = Label(
            f"{self.progress:.1f}% 完成", 
            classes="progress-text"
        )
        
        progress_container.mount(progress_bar)
        progress_container.mount(progress_text)
        
        return progress_container

    def update_status(self, status_data: Dict[str, Any]) -> None:
        """更新状态信息"""
        self.current_page = status_data.get("current_page", 0)
        self.total_pages = status_data.get("total_pages", 0)
        self.reading_time = status_data.get("reading_time", 0)
        self.reading_speed = status_data.get("reading_speed", 0.0)
        self.words_read = status_data.get("words_read", 0)
        self.total_words = status_data.get("total_words", 0)
        self.progress = status_data.get("progress", 0.0)
        
        self._update_display()

    def _update_display(self) -> None:
        """更新显示内容"""
        if not self.is_mounted:
            return
            
        try:
            # 更新统计信息
            self._update_stats_display()
            
            # 更新进度条
            self._update_progress_display()
            
        except Exception as e:
            # 忽略可能的查询错误
            pass

    def _update_stats_display(self) -> None:
        """更新统计信息显示"""
        try:
            # 更新页码信息
            page_item = self.query_one(".stat-item:nth-child(1) .stat-value")
            page_item.update(f"{self.current_page}/{self.total_pages}")
            
            # 更新时间信息
            time_item = self.query_one(".stat-item:nth-child(2) .stat-value")
            time_item.update(self._format_time(self.reading_time))
            
            # 更新速度信息
            speed_item = self.query_one(".stat-item:nth-child(3) .stat-value")
            speed_item.update(f"{self.reading_speed:.1f}字/分")
            
            # 更新字数信息
            words_item = self.query_one(".stat-item:nth-child(4) .stat-value")
            words_item.update(f"{self.words_read}/{self.total_words}")
            
        except Exception as e:
            # 忽略查询错误，可能在组件未完全挂载时发生
            pass

    def _update_progress_display(self) -> None:
        """更新进度条显示"""
        try:
            # 更新进度条宽度
            progress_bar = self.query_one(".progress-bar")
            progress_bar.styles.width = f"{self.progress}%"
            
            # 更新进度文本
            progress_text = self.query_one(".progress-text")
            progress_text.update(f"{self.progress:.1f}% 完成")
            
        except Exception as e:
            # 忽略查询错误
            pass

    def _format_time(self, seconds: int) -> str:
        """格式化时间显示"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def set_theme(self, theme: StatusBarTheme) -> None:
        """设置主题"""
        self.config.theme = theme
        self._apply_theme()

    def set_layout(self, layout: StatusBarLayout) -> None:
        """设置布局"""
        self.config.layout = layout
        self.refresh()

    def set_shortcuts(self, shortcuts: List[Dict[str, str]]) -> None:
        """设置快捷键"""
        self.shortcuts = shortcuts
        self.refresh()

    def _apply_theme(self) -> None:
        """应用主题样式"""
        # 移除所有主题类
        for theme in StatusBarTheme:
            self.remove_class(f"status-bar-{theme.value}")
        
        # 添加当前主题类
        self.add_class(f"status-bar-{self.config.theme.value}")
        
        # 应用紧凑模式
        if self.config.compact_mode:
            self.add_class("status-bar-compact")
        else:
            self.remove_class("status-bar-compact")
        
        # 应用浮动模式
        if self.config.layout == StatusBarLayout.FLOATING:
            self.add_class("status-bar-floating")
        else:
            self.remove_class("status-bar-floating")

    def on_mount(self) -> None:
        """组件挂载时的回调"""
        self._apply_theme()

    def on_resize(self) -> None:
        """窗口大小变化时的回调"""
        # 在移动设备上自动切换到紧凑模式
        if self.screen and hasattr(self.screen, "size"):
            width = self.screen.size.width
            self.config.compact_mode = width < 768
            self._apply_theme()

    def _mount_shortcuts_section(self, container: Union[Grid, Container, Horizontal]) -> None:
        """挂载快捷键区域"""
        if self.config.show_shortcuts:
            shortcuts_container = self._create_shortcuts_section()
            container.mount(shortcuts_container)

    def _mount_stats_section(self, container: Union[Grid, Container, Horizontal]) -> None:
        """挂载统计信息区域"""
        if self.config.show_stats:
            stats_container = self._create_stats_section()
            container.mount(stats_container)

    def _mount_progress_section(self, container: Union[Grid, Container, Horizontal]) -> None:
        """挂载进度区域"""
        if self.config.show_progress:
            progress_container = self._create_progress_section()
            container.mount(progress_container)

# 工厂函数
def create_modern_status_bar(config: Optional[StatusBarConfig] = None) -> ModernStatusBar:
    """创建现代化状态栏实例"""
    return ModernStatusBar(config)

# 快捷配置函数
def create_light_status_bar() -> ModernStatusBar:
    """创建亮色主题状态栏"""
    return ModernStatusBar(StatusBarConfig(theme=StatusBarTheme.LIGHT))

def create_dark_status_bar() -> ModernStatusBar:
    """创建暗色主题状态栏"""
    return ModernStatusBar(StatusBarConfig(theme=StatusBarTheme.DARK))

def create_minimal_status_bar() -> ModernStatusBar:
    """创建简约风格状态栏"""
    return ModernStatusBar(StatusBarConfig(
        theme=StatusBarTheme.MINIMAL,
        show_icons=False,
        compact_mode=True
    ))

def create_floating_status_bar() -> ModernStatusBar:
    """创建浮动状态栏"""
    return ModernStatusBar(StatusBarConfig(
        layout=StatusBarLayout.FLOATING,
        opacity=0.9
    ))

