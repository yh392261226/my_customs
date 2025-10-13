"""
加载动画组件 - 提供统一的加载动画显示
采用面向对象和面向切片设计，支持多种动画效果
"""

import asyncio
import time

from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.ui.components.base_component import BaseComponent

from src.utils.logger import get_logger

logger = get_logger(__name__)

class AnimationType(Enum):
    """动画类型枚举"""
    SPINNER = "spinner"          # 旋转动画
    PROGRESS = "progress"        # 进度条动画
    DOTS = "dots"                # 点状动画
    BAR = "bar"                  # 条形动画
    PULSE = "pulse"              # 脉冲动画
    CUSTOM = "custom"            # 自定义动画

@dataclass
class AnimationConfig:
    """动画配置"""
    type: AnimationType = AnimationType.SPINNER
    message: str = "加载中..."
    duration: float = 0.0  # 0表示无限
    show_percentage: bool = False
    show_elapsed_time: bool = True
    show_remaining_time: bool = False
    update_interval: float = 0.1  # 更新间隔(秒)

class LoadingAnimation(BaseComponent):
    """加载动画组件基类"""
    
    def __init__(self, config: Dict[str, Any], component_id: str = "loading_animation"):
        """
        初始化加载动画组件
        
        Args:
            config: 组件配置
            component_id: 组件ID
        """
        super().__init__(config, component_id)
        self.animation_config = AnimationConfig()
        self._is_visible = False
        self._start_time = 0
        self._progress = 0.0
        self._total = 100.0
        self._animation_task = None
        self._callbacks: Dict[str, List[Callable]] = {}
    
    def _on_initialize(self) -> None:
        """组件初始化"""
        logger.debug(f"加载动画组件 {self.component_id} 初始化完成")
    
    def show(self, message: Optional[str] = None, config: Optional[AnimationConfig] = None) -> None:
        """
        显示加载动画
        
        Args:
            message: 加载消息
            config: 动画配置
        """
        if config:
            self.animation_config = config
        if message:
            self.animation_config.message = message
        
        self._is_visible = True
        self._start_time = time.time()
        self._progress = 0.0
        
        # 启动动画任务
        self._start_animation()
        
        self.emit_event("animation_started", self.animation_config)
        logger.debug(f"显示加载动画: {self.animation_config.message}")
    
    def hide(self) -> None:
        """隐藏加载动画"""
        self._is_visible = False
        self._stop_animation()
        self.emit_event("animation_stopped")
        logger.debug("隐藏加载动画")
    
    def update_progress(self, progress: float, total: float = 100.0) -> None:
        """
        更新进度
        
        Args:
            progress: 当前进度
            total: 总进度
        """
        self._progress = progress
        self._total = total
        self.emit_event("progress_updated", progress, total)
    
    def set_message(self, message: str) -> None:
        """
        设置加载消息
        
        Args:
            message: 新的加载消息
        """
        self.animation_config.message = message
        self.emit_event("message_updated", message)
    
    def _start_animation(self) -> None:
        """启动动画任务"""
        self._stop_animation()
        
        async def animation_loop():
            try:
                while self._is_visible:
                    # 计算动画帧
                    frame = self._render_frame()
                    
                    # 触发帧更新事件
                    self.emit_event("frame_updated", frame)
                    
                    # 等待下一帧
                    await asyncio.sleep(self.animation_config.update_interval)
                    
            except asyncio.CancelledError:
                logger.debug("动画任务被取消")
            except Exception as e:
                logger.error(f"动画任务出错: {e}")
        
        # 创建并启动动画任务
        self._animation_task = asyncio.create_task(animation_loop())
    
    def _stop_animation(self) -> None:
        """停止动画任务"""
        if self._animation_task and not self._animation_task.done():
            self._animation_task.cancel()
            self._animation_task = None
    
    def _render_frame(self) -> Dict[str, Any]:
        """
        渲染动画帧
        
        Returns:
            Dict[str, Any]: 动画帧数据
        """
        elapsed = time.time() - self._start_time
        progress_percent = (self._progress / self._total * 100) if self._total > 0 else 0
        
        frame_data = {
            "visible": self._is_visible,
            "message": self.animation_config.message,
            "type": self.animation_config.type.value,
            "elapsed_time": elapsed,
            "progress": progress_percent,
            "frame_time": time.time()
        }
        
        # 根据动画类型添加特定数据
        if self.animation_config.type == AnimationType.SPINNER:
            frame_data["spinner_frame"] = self._get_spinner_frame(elapsed)
        elif self.animation_config.type == AnimationType.DOTS:
            frame_data["dots_frame"] = self._get_dots_frame(elapsed)
        elif self.animation_config.type == AnimationType.PROGRESS:
            frame_data["progress_bar"] = self._get_progress_bar(progress_percent)
        elif self.animation_config.type == AnimationType.BAR:
            frame_data["bar_frame"] = self._get_bar_frame(elapsed)
        elif self.animation_config.type == AnimationType.PULSE:
            frame_data["pulse_intensity"] = self._get_pulse_intensity(elapsed)
        
        return frame_data
    
    def _get_spinner_frame(self, elapsed: float) -> str:
        """获取旋转动画帧"""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_index = int((elapsed * 10) % len(frames))
        return frames[frame_index]
    
    def _get_dots_frame(self, elapsed: float) -> str:
        """获取点状动画帧"""
        frames = [".  ", ".. ", "...", " ..", "  .", "   "]
        frame_index = int((elapsed * 3) % len(frames))
        return frames[frame_index]
    
    def _get_progress_bar(self, progress: float) -> str:
        """获取进度条"""
        bar_length = 20
        filled_length = int(bar_length * progress / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        return f"[{bar}] {progress:.1f}%"
    
    def _get_bar_frame(self, elapsed: float) -> str:
        """获取条形动画帧"""
        frames = ["[=   ]", "[ =  ]", "[  = ]", "[   =]", "[  = ]", "[ =  ]"]
        frame_index = int((elapsed * 4) % len(frames))
        return frames[frame_index]
    
    def _get_pulse_intensity(self, elapsed: float) -> float:
        """获取脉冲强度"""
        return (abs((elapsed % 1.0) - 0.5) * 2.0)  # 0.0到1.0的脉冲
    
    def render(self) -> Dict[str, Any]:
        """渲染组件内容"""
        return self._render_frame()
    
    def is_visible(self) -> bool:
        """检查动画是否可见"""
        return self._is_visible
    
    def get_elapsed_time(self) -> float:
        """获取动画运行时间"""
        return time.time() - self._start_time if self._is_visible else 0.0

class SpinnerAnimation(LoadingAnimation):
    """旋转动画组件"""
    
    def __init__(self, config: Dict[str, Any], component_id: str = "spinner_animation"):
        super().__init__(config, component_id)
        self.animation_config.type = AnimationType.SPINNER

class ProgressAnimation(LoadingAnimation):
    """进度条动画组件"""
    
    def __init__(self, config: Dict[str, Any], component_id: str = "progress_animation"):
        super().__init__(config, component_id)
        self.animation_config.type = AnimationType.PROGRESS
        self.animation_config.show_percentage = True

class DotsAnimation(LoadingAnimation):
    """点状动画组件"""
    
    def __init__(self, config: Dict[str, Any], component_id: str = "dots_animation"):
        super().__init__(config, component_id)
        self.animation_config.type = AnimationType.DOTS

# 动画管理器
class AnimationManager:
    """动画管理器 - 管理多个加载动画"""
    
    def __init__(self):
        self._animations: Dict[str, LoadingAnimation] = {}
        self._default_animation = None
    
    def register_animation(self, animation: LoadingAnimation) -> bool:
        """
        注册动画组件
        
        Args:
            animation: 动画组件
            
        Returns:
            bool: 是否成功注册
        """
        if animation.component_id in self._animations:
            logger.warning(f"动画组件 {animation.component_id} 已存在")
            return False
        
        self._animations[animation.component_id] = animation
        return True
    
    def unregister_animation(self, component_id: str) -> bool:
        """
        注销动画组件
        
        Args:
            component_id: 组件ID
            
        Returns:
            bool: 是否成功注销
        """
        if component_id in self._animations:
            animation = self._animations[component_id]
            animation.hide()
            del self._animations[component_id]
            return True
        return False
    
    def get_animation(self, component_id: str) -> Optional[LoadingAnimation]:
        """
        获取动画组件
        
        Args:
            component_id: 组件ID
            
        Returns:
            Optional[LoadingAnimation]: 动画组件
        """
        return self._animations.get(component_id)
    
    def show_animation(self, component_id: str, message: str, 
                      animation_type: AnimationType = AnimationType.SPINNER) -> bool:
        """
        显示指定动画
        
        Args:
            component_id: 组件ID
            message: 加载消息
            animation_type: 动画类型
            
        Returns:
            bool: 是否成功显示
        """
        animation = self.get_animation(component_id)
        if not animation:
            logger.warning(f"未找到动画组件: {component_id}")
            return False
        
        config = AnimationConfig(type=animation_type, message=message)
        animation.show(message, config)
        return True
    
    def hide_animation(self, component_id: str) -> bool:
        """
        隐藏指定动画
        
        Args:
            component_id: 组件ID
            
        Returns:
            bool: 是否成功隐藏
        """
        animation = self.get_animation(component_id)
        if not animation:
            return False
        
        animation.hide()
        return True
    
    def update_progress(self, component_id: str, progress: float, total: float = 100.0) -> bool:
        """
        更新动画进度
        
        Args:
            component_id: 组件ID
            progress: 当前进度
            total: 总进度
            
        Returns:
            bool: 是否成功更新
        """
        animation = self.get_animation(component_id)
        if not animation:
            return False
        
        animation.update_progress(progress, total)
        return True
    
    def set_default_animation(self, animation: LoadingAnimation) -> None:
        """设置默认动画组件"""
        self._default_animation = animation
    
    def show_default(self, message: str) -> bool:
        """
        显示默认动画（在模态弹窗期间抑制）
        
        Args:
            message: 加载消息
            
        Returns:
            bool: 是否成功显示
        """
        # 若 App 正在显示模态弹窗，则抑制动画
        try:
            app = None
            try:
                from src.ui.app import get_app_instance
                app = get_app_instance()
            except Exception:
                app = None
            if not app:
                try:
                    from textual.app import App
                    app = App.get_app()
                except Exception:
                    app = None
            if app and getattr(app, "_modal_active", False):
                logger.debug("模态弹窗激活，跳过显示传统默认动画")
                return False
        except Exception:
            pass
        if not self._default_animation:
            logger.warning("未设置默认动画组件")
            return False
        
        self._default_animation.show(message)
        return True
    
    def hide_default(self) -> bool:
        """
        隐藏默认动画
        
        Returns:
            bool: 是否成功隐藏
        """
        if not self._default_animation:
            return False
        
        self._default_animation.hide()
        return True

# 全局动画管理器实例
animation_manager = AnimationManager()
animation_manager.set_default_animation(SpinnerAnimation({}))

# 装饰器：用于在耗时操作中显示加载动画
def with_loading_animation(animation_id: str = "default", message: str = "处理中..."):
    """
    加载动画装饰器
    
    Args:
        animation_id: 动画组件ID
        message: 加载消息
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # 显示加载动画
            animation_manager.show_animation(animation_id, message)
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                # 隐藏加载动画
                animation_manager.hide_animation(animation_id)
        
        def sync_wrapper(*args, **kwargs):
            # 显示加载动画
            animation_manager.show_animation(animation_id, message)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # 隐藏加载动画
                animation_manager.hide_animation(animation_id)
        
        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# 上下文管理器：用于在代码块中显示加载动画
class LoadingContext:
    """加载动画上下文管理器"""
    
    def __init__(self, animation_id: str = "default", message: str = "处理中..."):
        self.animation_id = animation_id
        self.message = message
    
    def __enter__(self):
        animation_manager.show_animation(self.animation_id, self.message)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        animation_manager.hide_animation(self.animation_id)
        return False
    
    async def __aenter__(self):
        animation_manager.show_animation(self.animation_id, self.message)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        animation_manager.hide_animation(self.animation_id)
        return False