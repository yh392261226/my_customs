"""
加载动画Widget - Textual框架中的加载动画组件
提供与Textual框架集成的加载动画显示
"""

from textual.widget import Widget
from textual.reactive import reactive
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime

from .loading_animation import AnimationManager, AnimationType


class LoadingWidget(Widget):
    """
    加载动画Widget - 在Textual框架中显示加载动画
    """
    
    CSS = """
    LoadingWidget {
        width: 100%;
        height: 100%;
        align: center middle;
        content-align: center middle;
    }
    
    LoadingWidget.-hidden {
        display: none;
    }
    """
    
    def __init__(self, animation_manager: AnimationManager, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.animation_manager = animation_manager
        self._is_visible = False
        self._animation_task: Optional[asyncio.Task] = None
        
    def on_mount(self) -> None:
        """组件挂载时初始化"""
        self.add_class("-hidden")
        
    async def show(self, message: str = "加载中...", animation_type: AnimationType = AnimationType.SPINNER) -> None:
        """显示加载动画"""
        self._is_visible = True
        self.remove_class("-hidden")
        self.animation_manager.set_default_animation(animation_type)
        
        # 启动动画任务
        if self._animation_task:
            self._animation_task.cancel()
            
        self._animation_task = asyncio.create_task(self._animate(message))
        
    async def hide(self) -> None:
        """隐藏加载动画"""
        self._is_visible = False
        self.add_class("-hidden")
        
        if self._animation_task:
            self._animation_task.cancel()
            self._animation_task = None
            
    async def _animate(self, message: str) -> None:
        """动画循环"""
        frame_index = 0
        start_time = datetime.now()
        
        while self._is_visible:
            # 获取当前动画帧
            frames = self.animation_manager.get_animation_frames()
            if frames:
                current_frame = frames[frame_index % len(frames)]
                
                # 更新显示
                self.update(f"{current_frame} {message}")
                
                # 下一帧
                frame_index += 1
                
                # 计算动画速度（基于耗时）
                elapsed = (datetime.now() - start_time).total_seconds()
                speed = self.animation_manager.calculate_animation_speed(elapsed)
                
                # 等待下一帧
                await asyncio.sleep(speed)
            else:
                await asyncio.sleep(0.1)
                
    def render(self) -> str:
        """渲染组件"""
        if not self._is_visible:
            return ""
            
        # 获取当前动画帧
        frames = self.animation_manager.get_animation_frames()
        if frames and self._animation_task:
            current_frame = frames[0]  # 第一帧
            return f"{current_frame} 加载中..."
        else:
            return "⏳ 加载中..."
            
    def on_unmount(self) -> None:
        """组件卸载时清理"""
        if self._animation_task:
            self._animation_task.cancel()
            self._animation_task = None