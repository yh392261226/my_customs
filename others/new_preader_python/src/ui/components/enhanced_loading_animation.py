"""
增强的加载动画组件 - 提供更详细的进度指示和状态反馈
"""

import asyncio
import time
from typing import Optional, Dict, Any, Callable
from textual.widgets import Static, Label
from textual.reactive import reactive
from textual.timer import Timer
from textual.containers import Container, Vertical
from textual.app import ComposeResult

from src.utils.logger import get_logger

logger = get_logger(__name__)

class EnhancedLoadingAnimation(Container):
    """增强的加载动画组件，包含进度条和状态信息"""
    
    # 响应式属性
    message = reactive("加载中...")
    progress = reactive(0.0)
    total = reactive(100.0)
    is_visible = reactive(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animation_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_frame = 0
        self.start_time = 0
        self.timer: Optional[Timer] = None
        self.progress_label: Optional[Label] = None
        self.spinner_label: Optional[Label] = None
        self.message_label: Optional[Label] = None
        
    def compose(self) -> ComposeResult:
        """组合组件界面"""
        with Vertical():
            yield Label("", id="spinner-label", classes="loading-spinner")
            yield Label("", id="message-label", classes="loading-message")
            yield Label("", id="progress-label", classes="loading-progress")
            
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self.styles.display = "none"  # 初始隐藏
        self.progress_label = self.query_one("#progress-label", Label)
        self.spinner_label = self.query_one("#spinner-label", Label)
        self.message_label = self.query_one("#message-label", Label)
        
    def show(self, message: str = "加载中...", progress: float = 0.0, total: float = 100.0) -> None:
        """显示加载动画"""
        self.message = message
        self.progress = progress
        self.total = total
        self.is_visible = True
        self.start_time = time.time()
        self.current_frame = 0
        
        # 显示组件
        self.styles.display = "block"
        
        # 启动动画定时器
        if self.timer:
            self.timer.stop()
        self.timer = self.set_interval(0.1, self._update_animation)
        
        logger.info(f"🔄 显示加载动画: {message}")
        
    def hide(self) -> None:
        """隐藏加载动画"""
        self.is_visible = False
        
        # 隐藏组件
        self.styles.display = "none"
        
        # 停止动画定时器
        if self.timer:
            self.timer.stop()
            self.timer = None
            
        logger.debug("✅ 隐藏加载动画")
        
    def update_progress(self, progress: float, total: float = 100.0) -> None:
        """更新进度"""
        self.progress = progress
        self.total = total
        self._update_display()
        
    def set_message(self, message: str) -> None:
        """设置消息"""
        self.message = message
        self._update_display()
        
    def _update_animation(self) -> None:
        """更新动画帧"""
        if not self.is_visible:
            return
            
        # 更新动画帧
        self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
        self._update_display()
        
    def _update_display(self) -> None:
        """更新显示内容"""
        if not self.is_visible or not all([self.spinner_label, self.message_label, self.progress_label]):
            return
            
        # 计算进度百分比和运行时间
        progress_percent = (self.progress / self.total * 100) if self.total > 0 else 0
        elapsed = time.time() - self.start_time
        
        # 更新旋转动画
        spinner = self.animation_frames[self.current_frame]
        self.spinner_label.update(spinner)
        
        # 更新消息
        self.message_label.update(f"{self.message}")
        
        # 更新进度信息
        if self.total > 0:
            progress_text = f"进度: {progress_percent:.1f}% ({int(self.progress)}/{int(self.total)})"
        else:
            progress_text = f"已运行: {elapsed:.1f}s"
        
        self.progress_label.update(progress_text)
        
    def watch_message(self, message: str) -> None:
        """监听消息变化"""
        if self.is_visible:
            self._update_display()
            
    def watch_progress(self, progress: float) -> None:
        """监听进度变化"""
        if self.is_visible:
            self._update_display()
            
    def watch_total(self, total: float) -> None:
        """监听总量变化"""
        if self.is_visible:
            self._update_display()
            
    def watch_is_visible(self, visible: bool) -> None:
        """监听可见性变化"""
        if visible:
            self.styles.display = "block"
            self.start_time = time.time()  # 重置计时器
        else:
            self.styles.display = "none"
            
class LoadingProgress:
    """加载进度管理类，用于长时间操作的进度跟踪"""
    
    def __init__(self, callback: Callable, total_steps: int = 100):
        self.callback = callback  # 进度回调函数
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = None
        self.message = "加载中..."
        
    def start(self, message: str = "加载中..."):
        """开始进度跟踪"""
        self.start_time = time.time()
        self.message = message
        self.current_step = 0
        
    def update(self, step: int = 1, message: Optional[str] = None):
        """更新进度"""
        self.current_step = min(self.current_step + step, self.total_steps)
        if message:
            self.message = message
            
        # 计算进度百分比和预估剩余时间
        progress_percent = (self.current_step / self.total_steps * 100)
        elapsed = time.time() - self.start_time
        
        if self.current_step > 0:
            estimated_total = elapsed / (self.current_step / self.total_steps)
            remaining = estimated_total - elapsed
            
            # 调用回调函数更新UI
            self.callback(
                progress=progress_percent,
                message=self.message,
                elapsed=elapsed,
                remaining=remaining
            )
            
    def finish(self):
        """完成进度跟踪"""
        self.current_step = self.total_steps
        elapsed = time.time() - self.start_time
        
        self.callback(
            progress=100.0,
            message="完成",
            elapsed=elapsed,
            remaining=0
        )