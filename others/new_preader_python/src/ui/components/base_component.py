"""
组件基类 - 提供统一的组件接口和生命周期管理
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, TypeVar, Generic


T = TypeVar('T')

from src.utils.logger import get_logger

logger = get_logger(__name__)

class BaseComponent(ABC):
    """组件基类 - 所有UI组件的抽象基类"""
    
    def __init__(self, config: Dict[str, Any], component_id: str):
        """
        初始化组件
        
        Args:
            config: 组件配置
            component_id: 组件唯一标识符
        """
        self.config = config
        self.component_id = component_id
        self.callbacks: Dict[str, Callable[..., Any]] = {}
        self._initialized = False
        
    def initialize(self) -> None:
        """初始化组件"""
        if not self._initialized:
            self._on_initialize()
            self._initialized = True
            logger.debug(f"组件 {self.component_id} 已初始化")
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新组件配置"""
        old_config = self.config.copy()
        self.config.update(new_config)
        self._on_config_change(old_config, new_config)
    
    def register_callback(self, event_name: str, callback: Callable[..., Any]) -> None:
        """注册事件回调"""
        self.callbacks[event_name] = callback
    
    def emit_event(self, event_name: str, *args, **kwargs) -> None:
        """触发事件"""
        if event_name in self.callbacks:
            try:
                self.callbacks[event_name](*args, **kwargs)
            except Exception as e:
                logger.error(f"事件回调执行失败: {event_name}, 错误: {e}")
    
    @abstractmethod
    def render(self) -> str:
        """渲染组件内容 - 抽象方法，子类必须实现"""
        pass
    
    def _on_initialize(self) -> None:
        """组件初始化回调 - 子类可重写"""
        pass
    
    def _on_config_change(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """配置变化回调 - 子类可重写"""
        pass
    
    def cleanup(self) -> None:
        """清理组件资源"""
        self.callbacks.clear()
        self._initialized = False
        logger.debug(f"组件 {self.component_id} 已清理")