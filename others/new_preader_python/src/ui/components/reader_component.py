"""
阅读器组件基类 - 采用面向对象和面向切片设计
提供统一的组件接口和事件机制
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable


from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderComponent(ABC):
    """阅读器组件抽象基类"""
    
    def __init__(self, component_id: str):
        """
        初始化组件
        
        Args:
            component_id: 组件唯一标识
        """
        self.component_id = component_id
        self._callbacks: Dict[str, List[Callable]] = {}
        self._parent = None
    
    @abstractmethod
    def initialize(self) -> None:
        """初始化组件"""
        pass
    
    @abstractmethod
    def update(self, data: Dict[str, Any]) -> None:
        """更新组件状态"""
        pass
    
    @abstractmethod
    def render(self) -> Dict[str, Any]:
        """渲染组件内容"""
        pass
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """注册事件回调"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
        """触发事件"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"组件 {self.component_id} 事件回调错误 {event}: {e}")
    
    def set_parent(self, parent: 'ReaderComponent') -> None:
        """设置父组件"""
        self._parent = parent
    
    def get_parent(self) -> Optional['ReaderComponent']:
        """获取父组件"""
        return self._parent
    
    def on_config_change(self, config: Dict[str, Any]) -> None:
        """配置变化时的回调"""
        pass
    
    def destroy(self) -> None:
        """销毁组件"""
        self._callbacks.clear()
        self._parent = None

class ContentComponent(ReaderComponent):
    """内容显示组件"""
    
    def __init__(self, component_id: str = "content"):
        super().__init__(component_id)
        self.content = ""
        self.current_page = 0
        self.total_pages = 0
    
    def initialize(self) -> None:
        """初始化内容组件"""
        self.content = ""
        self.current_page = 0
        self.total_pages = 0
    
    def update(self, data: Dict[str, Any]) -> None:
        """更新内容状态"""
        if "content" in data:
            self.content = data["content"]
        if "current_page" in data:
            self.current_page = data["current_page"]
        if "total_pages" in data:
            self.total_pages = data["total_pages"]
        
    
    def render(self) -> Dict[str, Any]:
        """渲染内容数据"""
        return {
            "content": self.content,
            "current_page": self.current_page + 1,  # 1-based for display
            "total_pages": self.total_pages,
            "progress": self._get_progress()
        }
    
    def _get_progress(self) -> float:
        """获取阅读进度"""
        if self.total_pages == 0:
            return 0.0
        return self.current_page / self.total_pages

class StatusComponent(ReaderComponent):
    """状态显示组件"""
    
    def __init__(self, component_id: str = "status"):
        super().__init__(component_id)
        self.stats: Dict[str, Any] = {}
    
    def initialize(self) -> None:
        """初始化状态组件"""
        self.stats = {}
    
    def update(self, data: Dict[str, Any]) -> None:
        """更新状态信息"""
        self.stats.update(data)
    
    def render(self) -> Dict[str, Any]:
        """渲染状态数据"""
        return self.stats.copy()

class ControlComponent(ReaderComponent):
    """控制组件"""
    
    def __init__(self, component_id: str = "controls"):
        super().__init__(component_id)
        self.controls: Dict[str, Any] = {}
    
    def initialize(self) -> None:
        """初始化控制组件"""
        self.controls = {
            "auto_page_turn": False,
            "font_size": 16,
            "theme": "light"
        }
    
    def update(self, data: Dict[str, Any]) -> None:
        """更新控制状态"""
        self.controls.update(data)
    
    def render(self) -> Dict[str, Any]:
        """渲染控制数据"""
        return self.controls.copy()
    
    def handle_action(self, action: str, data: Any = None) -> None:
        """处理用户操作"""

class ComponentManager:
    """组件管理器 - 管理所有阅读器组件"""
    
    def __init__(self):
        self.components: Dict[str, ReaderComponent] = {}
        self._event_bus: Dict[str, List[Callable]] = {}
    
    def register_component(self, component: ReaderComponent) -> bool:
        """注册组件"""
        if component.component_id in self.components:
            logger.warning(f"组件 {component.component_id} 已存在")
            return False
        
        self.components[component.component_id] = component
        component.set_parent(self)
        return True
    
    def unregister_component(self, component_id: str) -> bool:
        """注销组件"""
        if component_id in self.components:
            component = self.components[component_id]
            component.destroy()
            del self.components[component_id]
            return True
        return False
    
    def get_component(self, component_id: str) -> Optional[ReaderComponent]:
        """获取组件"""
        return self.components.get(component_id)
    
    def update_component(self, component_id: str, data: Dict[str, Any]) -> bool:
        """更新组件状态"""
        component = self.get_component(component_id)
        if component:
            component.update(data)
            return True
        return False
    
    def render_all(self) -> Dict[str, Any]:
        """渲染所有组件"""
        result = {}
        for component_id, component in self.components.items():
            result[component_id] = component.render()
        return result
    
    def broadcast_event(self, event: str, *args, **kwargs) -> None:
        """广播事件到所有组件"""
        for component in self.components.values():
    
    def register_global_callback(self, event: str, callback: Callable) -> None:
        """注册全局事件回调"""
        if event not in self._event_bus:
            self._event_bus[event] = []
        self._event_bus[event].append(callback)
    
    def emit_global_event(self, event: str, *args, **kwargs) -> None:
        """触发全局事件"""
        if event in self._event_bus:
            for callback in self._event_bus[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"全局事件回调错误 {event}: {e}")
    
    def destroy(self) -> None:
        """销毁所有组件"""
        for component in list(self.components.values()):
            self.unregister_component(component.component_id)
        self._event_bus.clear()

# 组件工厂
class ComponentFactory:
    """组件工厂 - 创建标准组件"""
    
    @staticmethod
    def create_content_component() -> ContentComponent:
        """创建内容组件"""
        return ContentComponent()
    
    @staticmethod
    def create_status_component() -> StatusComponent:
        """创建状态组件"""
        return StatusComponent()
    
    @staticmethod
    def create_control_component() -> ControlComponent:
        """创建控制组件"""
        return ControlComponent()
    
    @staticmethod
    def create_component_manager() -> ComponentManager:
        """创建组件管理器"""
        return ComponentManager()