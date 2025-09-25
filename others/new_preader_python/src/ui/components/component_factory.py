"""
组件工厂 - 负责创建和管理阅读器组件
"""

from typing import Dict, Any, Type

from src.ui.components.base_component import BaseComponent
from src.ui.components.content_renderer import ContentRenderer
from src.ui.components.reader_header import ReaderHeader
from src.ui.components.reader_controls import ReaderControls

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ComponentFactory:
    """组件工厂 - 负责创建和管理阅读器组件"""
    
    # 组件注册表
    COMPONENT_REGISTRY: Dict[str, Type] = {
        "content_renderer": ContentRenderer,
        "reader_header": ReaderHeader,
        "reader_controls": ReaderControls
    }
    
    @classmethod
    def create_component(cls, component_type: str, config: Dict[str, Any], 
                        component_id: str = None) -> object:
        """
        创建指定类型的组件
        
        Args:
            component_type: 组件类型
            config: 组件配置
            component_id: 组件ID（可选）
            
        Returns:
            object: 组件实例
        """
        if component_type not in cls.COMPONENT_REGISTRY:
            raise ValueError(f"未知的组件类型: {component_type}")
            
        component_class = cls.COMPONENT_REGISTRY[component_type]
        component_id = component_id or f"{component_type}_{id(config)}"
        
        component = component_class(config, component_id)
        
        # 如果组件有initialize方法，调用它
        if hasattr(component, 'initialize'):
            component.initialize()
        
        logger.debug(f"创建组件: {component_type} (ID: {component_id})")
        return component
        
    @classmethod
    def create_all_components(cls, config: Dict[str, Any]) -> Dict[str, BaseComponent]:
        """
        创建所有注册的组件
        
        Args:
            config: 组件配置
            
        Returns:
            Dict[str, BaseComponent]: 组件字典
        """
        components = {}
        
        for component_type in cls.COMPONENT_REGISTRY:
            try:
                component = cls.create_component(component_type, config)
                components[component_type] = component
            except Exception as e:
                logger.error(f"创建组件 {component_type} 失败: {e}")
                # 继续创建其他组件
                continue
                
        logger.info(f"成功创建 {len(components)} 个组件")
        return components
        
    @classmethod
    def register_component(cls, component_type: str, component_class: Type[BaseComponent]) -> None:
        """
        注册新的组件类型
        
        Args:
            component_type: 组件类型名称
            component_class: 组件类
        """
        if not issubclass(component_class, BaseComponent):
            raise ValueError("组件类必须继承自 BaseComponent")
            
        cls.COMPONENT_REGISTRY[component_type] = component_class
        logger.debug(f"注册新组件类型: {component_type}")
        
    @classmethod
    def unregister_component(cls, component_type: str) -> None:
        """
        取消注册组件类型
        
        Args:
            component_type: 组件类型名称
        """
        if component_type in cls.COMPONENT_REGISTRY:
            del cls.COMPONENT_REGISTRY[component_type]
            logger.debug(f"取消注册组件类型: {component_type}")
            
    @classmethod
    def get_available_components(cls) -> list:
        """
        获取所有可用的组件类型
        
        Returns:
            list: 组件类型列表
        """
        return list(cls.COMPONENT_REGISTRY.keys())