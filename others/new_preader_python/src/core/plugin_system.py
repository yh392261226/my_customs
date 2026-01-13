"""
插件系统
用于扩展应用程序功能的插件架构
"""

import os
import sys
import importlib
import importlib.util
from typing import Dict, List, Any, Optional, Protocol, runtime_checkable
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

class PluginType(Enum):
    """插件类型枚举"""
    PARSER = "parser"
    EXPORTER = "exporter"
    IMPORTER = "importer"
    ANALYZER = "analyzer"
    UI_COMPONENT = "ui_component"
    OTHER = "other"


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = None
    api_version: str = "1.0.0"
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


@runtime_checkable
class PluginInterface(Protocol):
    """插件接口协议"""
    
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        ...
    
    def initialize(self) -> bool:
        """初始化插件"""
        ...
    
    def cleanup(self) -> bool:
        """清理插件资源"""
        ...


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = None):
        """
        初始化插件管理器
        
        Args:
            plugins_dir: 插件目录路径，默认为 'plugins'
        """
        self.plugins_dir = plugins_dir or os.path.join(os.path.dirname(__file__), "..", "..", "plugins")
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.enabled_plugins: List[str] = []
        
        # 确保插件目录存在
        os.makedirs(self.plugins_dir, exist_ok=True)
    
    def load_plugin(self, plugin_path: str) -> bool:
        """
        加载单个插件
        
        Args:
            plugin_path: 插件文件路径
            
        Returns:
            是否加载成功
        """
        try:
            plugin_name = os.path.splitext(os.path.basename(plugin_path))[0]
            
            # 动态导入插件模块
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None:
                logger.error(f"无法创建插件规范: {plugin_path}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            
            if spec.loader is None:
                logger.error(f"插件加载器为空: {plugin_path}")
                return False
            
            spec.loader.exec_module(module)
            
            # 查找插件类（通常以Plugin结尾）
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (hasattr(attr, '__bases__') and 
                    any('Plugin' in base.__name__ for base in attr.__bases__) and
                    hasattr(attr, 'get_metadata') and hasattr(attr, 'initialize')):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                logger.error(f"未找到有效的插件类: {plugin_path}")
                return False
            
            # 实例化插件
            plugin_instance = plugin_class()
            
            # 验证插件接口
            if not isinstance(plugin_instance, PluginInterface):
                logger.error(f"插件不实现PluginInterface: {plugin_path}")
                return False
            
            # 获取元数据并验证依赖
            metadata = plugin_instance.get_metadata()
            if not self._check_dependencies(metadata.dependencies):
                logger.error(f"插件依赖未满足: {plugin_name}")
                return False
            
            # 初始化插件
            if not plugin_instance.initialize():
                logger.error(f"插件初始化失败: {plugin_name}")
                return False
            
            # 注册插件
            self.plugins[plugin_name] = plugin_instance
            self.plugin_metadata[plugin_name] = metadata
            logger.info(f"插件加载成功: {plugin_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"加载插件失败 {plugin_path}: {e}")
            return False
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """
        检查插件依赖是否满足
        
        Args:
            dependencies: 依赖列表
            
        Returns:
            依赖是否满足
        """
        if not dependencies:
            return True
        
        for dep in dependencies:
            if dep not in self.plugins:
                logger.warning(f"依赖插件未找到: {dep}")
                return False
        
        return True
    
    def load_all_plugins(self) -> int:
        """
        加载所有插件
        
        Returns:
            成功加载的插件数量
        """
        loaded_count = 0
        
        # 遰找所有Python插件文件
        plugin_files = []
        for root, dirs, files in os.walk(self.plugins_dir):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    plugin_files.append(os.path.join(root, file))
        
        # 按文件名排序以保证加载顺序一致
        plugin_files.sort()
        
        for plugin_file in plugin_files:
            if self.load_plugin(plugin_file):
                loaded_count += 1
        
        logger.info(f"总共加载了 {loaded_count} 个插件")
        return loaded_count
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否卸载成功
        """
        if plugin_name not in self.plugins:
            logger.warning(f"插件不存在: {plugin_name}")
            return False
        
        try:
            plugin = self.plugins[plugin_name]
            
            # 清理插件资源
            if hasattr(plugin, 'cleanup'):
                plugin.cleanup()
            
            # 从注册表中移除
            del self.plugins[plugin_name]
            if plugin_name in self.plugin_metadata:
                del self.plugin_metadata[plugin_name]
            if plugin_name in self.enabled_plugins:
                self.enabled_plugins.remove(plugin_name)
            
            logger.info(f"插件已卸载: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"卸载插件失败 {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """
        获取插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件实例，如果不存在则返回None
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        """
        获取所有插件
        
        Returns:
            插件字典
        """
        return self.plugins.copy()
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> Dict[str, PluginInterface]:
        """
        按类型获取插件
        
        Args:
            plugin_type: 插件类型
            
        Returns:
            指定类型的插件字典
        """
        return {
            name: plugin for name, plugin in self.plugins.items()
            if self.plugin_metadata[name].plugin_type == plugin_type
        }
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """
        启用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否启用成功
        """
        if plugin_name in self.plugins and plugin_name not in self.enabled_plugins:
            self.enabled_plugins.append(plugin_name)
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """
        禁用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否禁用成功
        """
        if plugin_name in self.enabled_plugins:
            self.enabled_plugins.remove(plugin_name)
            return True
        return False
    
    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        检查插件是否启用
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件是否启用
        """
        return plugin_name in self.enabled_plugins
    
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        获取插件元数据
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件元数据，如果不存在则返回None
        """
        return self.plugin_metadata.get(plugin_name)
    
    def get_all_metadata(self) -> Dict[str, PluginMetadata]:
        """
        获取所有插件元数据
        
        Returns:
            插件元数据字典
        """
        return self.plugin_metadata.copy()


class BasePlugin:
    """插件基类"""
    
    def __init__(self):
        self.initialized = False
        self.name = self.__class__.__name__
    
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据 - 子类必须实现"""
        raise NotImplementedError("子类必须实现 get_metadata 方法")
    
    def initialize(self) -> bool:
        """初始化插件"""
        try:
            self.initialized = True
            logger.info(f"插件初始化成功: {self.name}")
            return True
        except Exception as e:
            logger.error(f"插件初始化失败: {self.name}, 错误: {e}")
            return False
    
    def cleanup(self) -> bool:
        """清理插件资源"""
        try:
            self.initialized = False
            logger.info(f"插件清理完成: {self.name}")
            return True
        except Exception as e:
            logger.error(f"插件清理失败: {self.name}, 错误: {e}")
            return False