"""
状态栏组件 - 阅读器底部状态栏
包含快捷键提示、进度条和阅读统计信息
采用面向对象设计，支持高度可定制
"""

from typing import Dict, Any, List, Optional
from textual.widgets import Static, Label, ProgressBar
from textual.containers import Horizontal, Container, Vertical
from textual.reactive import reactive
from textual import events
from textual.app import ComposeResult

class StatusBar(Container):
    """阅读器状态栏组件 - 现代化设计"""
    
    CSS = """
    StatusBar {
        width: 100%;
        height: 1;
        background: $panel;
        border-top: solid $accent;
        padding: 0 1;
        layout: horizontal;
        align: center middle;
    }
    
    .status-text {
        color: $text;
        text-style: bold;
        margin: 0 1;
    }
    """
    
    def __init__(self, config: Dict[str, Any], shortcuts: Optional[List[Dict[str, str]]] = None):
        """
        初始化状态栏
        
        Args:
            config: 配置信息
            shortcuts: 快捷键列表，格式为 [{"key": "快捷键", "desc": "描述"}]
        """
        super().__init__(id="status-bar")
        self.config = config
        
        # 默认快捷键配置
        self.shortcuts = shortcuts or [
            {"key": "←→", "desc": "翻页"},
            {"key": "↑↓", "desc": "滚动"},
            {"key": "G", "desc": "跳转"},
            {"key": "B", "desc": "书签"},
            {"key": "S", "desc": "搜索"},
            {"key": "A", "desc": "自动翻页"},
            {"key": "ESC", "desc": "返回"}
        ]
        
        # 状态信息
        self.current_page = 0
        self.total_pages = 0
        self.reading_time = 0
        self.reading_speed = 0
        self.words_read = 0
        self.total_words = 0
    
    def compose(self) -> ComposeResult:
        """组合状态栏界面"""
        # 简化的单行状态栏
        yield Static("", id="status-text", classes="status-text")
    
    def update_status(self, status_data: Dict[str, Any]) -> None:
        """更新状态信息"""
        self.current_page = status_data.get("current_page", 0)
        self.total_pages = status_data.get("total_pages", 0)
        self.reading_time = status_data.get("reading_time", 0)
        self.reading_speed = status_data.get("reading_speed", 0)
        self.words_read = status_data.get("words_read", 0)
        self.total_words = status_data.get("total_words", 0)
        
        self._update_display()
    
    def on_mount(self) -> None:
        """组件挂载时的回调"""
        # 组件挂载后立即更新显示
        self._update_display()
    
    def _update_display(self) -> None:
        """更新显示内容"""
        # 只有在组件挂载后才更新UI
        if not self.is_mounted:
            return
            
        try:
            # 计算进度
            progress = self._calculate_progress()
            
            # 构建状态文本
            shortcuts_text = " | ".join([f"[{s['key']}]{s['desc']}" for s in self.shortcuts[:4]])  # 只显示前4个快捷键
            status_text = f"{shortcuts_text} | 📄 {self.current_page + 1}/{self.total_pages} | ⏱️ {self._format_time(self.reading_time)} | 📊 {progress:.1f}%"
            
            # 更新状态文本
            status_widget = self.query_one("#status-text", Static)
            status_widget.update(status_text)
        except Exception as e:
            # 忽略查询错误，可能在组件未完全挂载时发生
            pass
    
    def _calculate_progress(self) -> float:
        """计算阅读进度"""
        if self.total_pages == 0:
            return 0.0
        # 修复进度计算：current_page是从0开始的，所以需要+1
        # 当在最后一页时，进度应该是100%
        progress = ((self.current_page + 1) / self.total_pages) * 100
        return min(progress, 100.0)
    
    def _format_time(self, seconds: int) -> str:
        """格式化时间显示"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def set_shortcuts(self, shortcuts: List[Dict[str, str]]) -> None:
        """设置快捷键配置"""
        self.shortcuts = shortcuts
        self._update_shortcuts_display()
    
    def _update_shortcuts_display(self) -> None:
        """更新快捷键显示"""
        try:
            shortcuts_row = self.query_one("#shortcuts-row", Horizontal)
            shortcuts_row.remove_children()
            
            for shortcut in self.shortcuts:
                shortcuts_row.mount(
                    Static(f"[{shortcut['key']}] {shortcut['desc']}", 
                          classes="shortcut-item")
                )
        except Exception:
            # 忽略更新错误
            pass

# 工厂函数
def create_status_bar(config: Dict[str, Any], 
                     shortcuts: Optional[List[Dict[str, str]]] = None) -> StatusBar:
    """创建状态栏组件实例"""
    return StatusBar(config, shortcuts)