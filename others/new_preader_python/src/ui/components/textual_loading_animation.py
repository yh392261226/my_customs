"""
Textual集成的加载动画组件
"""

import asyncio
import time
from typing import Optional, Dict, Any
from textual.widgets import Static
from textual.reactive import reactive
from textual.timer import Timer

from src.utils.logger import get_logger

logger = get_logger(__name__)

class TextualLoadingAnimation(Static):
    """与Textual集成的加载动画组件"""
    
    # 响应式属性
    message = reactive("加载中...")
    is_visible = reactive(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animation_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_frame = 0
        self.start_time = 0
        self.timer: Optional[Timer] = None
        
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self.styles.display = "none"  # 初始隐藏
        
    def show(self, message: str = "加载中...") -> None:
        """显示加载动画"""
        self.message = message
        self.is_visible = True
        self.start_time = time.time()
        self.current_frame = 0
        
        # 显示组件
        self.styles.display = "block"
        
        # 启动动画定时器
        if self.timer:
            self.timer.stop()
        self.timer = self.set_interval(0.1, self._update_animation)
        
        logger.debug(f"显示加载动画: {message}")
        
    def hide(self) -> None:
        """隐藏加载动画"""
        self.is_visible = False
        
        # 隐藏组件
        self.styles.display = "none"
        
        # 停止动画定时器
        if self.timer:
            self.timer.stop()
            self.timer = None
            
        logger.debug("隐藏加载动画")
        
    def _update_animation(self) -> None:
        """更新动画帧"""
        if not self.is_visible:
            return
            
        # 更新动画帧
        self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
        
        # 计算运行时间
        elapsed = time.time() - self.start_time
        
        # 更新显示内容
        spinner = self.animation_frames[self.current_frame]
        content = f"{spinner} {self.message} ({elapsed:.1f}s)"
        self.update(content)
        
    def watch_message(self, message: str) -> None:
        """监听消息变化"""
        if self.is_visible:
            self._update_animation()
            
    def watch_is_visible(self, visible: bool) -> None:
        """监听可见性变化"""
        if visible:
            self.styles.display = "block"
        else:
            self.styles.display = "none"

class TextualAnimationManager:
    """Textual动画管理器"""
    
    def __init__(self):
        self._default_animation: Optional[TextualLoadingAnimation] = None
        self._animations: Dict[str, TextualLoadingAnimation] = {}
        
    def set_default_animation(self, animation: TextualLoadingAnimation) -> None:
        """设置默认动画"""
        self._default_animation = animation
        
    def register_animation(self, name: str, animation: TextualLoadingAnimation) -> None:
        """注册动画"""
        self._animations[name] = animation
        
    def show_default(self, message: str = "加载中...") -> bool:
        """显示默认动画"""
        if self._default_animation:
            self._default_animation.show(message)
            return True
        else:
            logger.warning("未设置默认动画")
            return False
            
    def hide_default(self) -> bool:
        """隐藏默认动画"""
        if self._default_animation:
            self._default_animation.hide()
            return True
        else:
            logger.warning("未设置默认动画")
            return False
            
    def show_animation(self, name: str, message: str = "加载中...") -> bool:
        """显示指定动画"""
        animation = self._animations.get(name)
        if animation:
            animation.show(message)
            return True
        else:
            logger.warning(f"未找到动画: {name}")
            return False
            
    def hide_animation(self, name: str) -> bool:
        """隐藏指定动画"""
        animation = self._animations.get(name)
        if animation:
            animation.hide()
            return True
        else:
            logger.warning(f"未找到动画: {name}")
            return False

# 全局动画管理器实例
textual_animation_manager = TextualAnimationManager()