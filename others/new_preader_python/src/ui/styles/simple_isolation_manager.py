"""
简单样式隔离管理器
提供最实用的样式隔离解决方案
"""

from typing import Dict, Set, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

class SimpleIsolationManager:
    """
    简单样式隔离管理器
    通过CSS类名命名空间实现样式隔离
    """
    
    def __init__(self):
        """初始化简单样式隔离管理器"""
        self._active_namespaces: Set[str] = set()
        self._screen_namespaces: Dict[str, str] = {}
        
        # 预定义屏幕命名空间映射
        self._namespace_mapping = {
            "WelcomeScreen": "screen-welcome",
            "BookshelfScreen": "screen-bookshelf", 
            "ReaderScreen": "screen-reader",
            "SettingsScreen": "screen-settings",
            "FileExplorerScreen": "screen-fileexplorer",
            "StatisticsScreen": "screen-statistics",
            "HelpScreen": "screen-help",
            "BossKeyScreen": "screen-bosskey",
            "GetBooksScreen": "screen-getbooks",
            "ProxyListScreen": "screen-proxylist",
            "NovelSitesManagementScreen": "screen-novelsites",
            "CrawlerManagementScreen": "screen-crawler",
            "BookmarksScreen": "screen-bookmarks",
            "SearchResultsScreen": "screen-searchresults",
        }
    
    def get_namespace(self, screen_name: str) -> str:
        """获取屏幕的命名空间"""
        return self._namespace_mapping.get(screen_name, f"screen-{screen_name.lower().replace('screen', '')}")
    
    def apply_isolation(self, screen) -> None:
        """为屏幕应用样式隔离"""
        if not screen:
            return
            
        screen_name = screen.__class__.__name__
        namespace = self.get_namespace(screen_name)
        
        try:
            # 清除之前的命名空间
            self._clear_previous_namespaces(screen)
            
            # 添加新的命名空间类
            if hasattr(screen, 'add_class'):
                screen.add_class(namespace)
                screen.add_class('isolated-screen')
                self._active_namespaces.add(namespace)
            
            # 为主要容器添加隔离类
            self._apply_container_isolation(screen, namespace)
            
            logger.debug(f"为屏幕 {screen_name} 应用样式隔离: {namespace}")
            
        except Exception as e:
            logger.error(f"应用样式隔离失败 {screen_name}: {e}")
    
    def _clear_previous_namespaces(self, screen) -> None:
        """清除之前的命名空间类"""
        try:
            if hasattr(screen, 'remove_class'):
                # 移除所有活动的命名空间类
                for namespace in list(self._active_namespaces):
                    screen.remove_class(namespace)
                
                # 移除通用隔离类
                screen.remove_class('isolated-screen')
            
            # 清空活动命名空间记录
            self._active_namespaces.clear()
            
        except Exception as e:
            logger.debug(f"清除命名空间类时出错: {e}")
    
    def _apply_container_isolation(self, screen, namespace: str) -> None:
        """为容器应用隔离类"""
        try:
            # 常见的容器选择器
            container_selectors = [
                "Container", "Vertical", "Horizontal", "Grid", 
                "ScrollableContainer", "TabbedContent", "TabPane"
            ]
            
            for selector in container_selectors:
                try:
                    if hasattr(screen, 'query'):
                        containers = screen.query(selector)
                        for container in containers:
                            if hasattr(container, 'add_class'):
                                container.add_class(namespace)
                                container.add_class('isolated-container')
                except Exception:
                    # 容器可能不存在，继续尝试其他选择器
                    continue
                    
        except Exception as e:
            logger.debug(f"应用容器隔离时出错: {e}")
    
    def remove_isolation(self, screen) -> None:
        """移除屏幕的样式隔离"""
        if not screen:
            return
            
        screen_name = screen.__class__.__name__
        namespace = self.get_namespace(screen_name)
        
        try:
            # 移除命名空间类
            if hasattr(screen, 'remove_class'):
                screen.remove_class(namespace)
                screen.remove_class('isolated-screen')
            
            # 移除容器的隔离类
            self._remove_container_isolation(screen, namespace)
            
            # 从活动命名空间中移除
            self._active_namespaces.discard(namespace)
            
            logger.debug(f"移除屏幕 {screen_name} 的样式隔离")
            
        except Exception as e:
            logger.error(f"移除样式隔离失败 {screen_name}: {e}")
    
    def _remove_container_isolation(self, screen, namespace: str) -> None:
        """移除容器的隔离类"""
        try:
            container_selectors = [
                "Container", "Vertical", "Horizontal", "Grid",
                "ScrollableContainer", "TabbedContent", "TabPane"
            ]
            
            for selector in container_selectors:
                try:
                    if hasattr(screen, 'query'):
                        containers = screen.query(selector)
                        for container in containers:
                            if hasattr(container, 'remove_class'):
                                container.remove_class(namespace)
                                container.remove_class('isolated-container')
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug(f"移除容器隔离时出错: {e}")
    
    def reset(self) -> None:
        """重置隔离管理器状态"""
        self._active_namespaces.clear()
        self._screen_namespaces.clear()
        logger.debug("样式隔离管理器状态已重置")


# 全局简单隔离管理器实例
_simple_isolation_manager: Optional[SimpleIsolationManager] = None

def get_simple_isolation_manager() -> SimpleIsolationManager:
    """获取简单样式隔离管理器"""
    global _simple_isolation_manager
    if _simple_isolation_manager is None:
        _simple_isolation_manager = SimpleIsolationManager()
    return _simple_isolation_manager

def apply_simple_isolation(screen) -> None:
    """为屏幕应用简单样式隔离"""
    manager = get_simple_isolation_manager()
    manager.apply_isolation(screen)

def remove_simple_isolation(screen) -> None:
    """移除屏幕的简单样式隔离"""
    manager = get_simple_isolation_manager()
    manager.remove_isolation(screen)

def reset_simple_isolation() -> None:
    """重置简单样式隔离状态"""
    manager = get_simple_isolation_manager()
    manager.reset()


def enhance_screen_with_isolation(screen_class):
    """
    为屏幕类增强样式隔离功能的装饰器
    """
    original_on_mount = getattr(screen_class, 'on_mount', None)
    original_on_unmount = getattr(screen_class, 'on_unmount', None)
    
    def enhanced_on_mount(self):
        """增强的挂载方法"""
        # 调用原始方法
        if original_on_mount:
            original_on_mount(self)
        
        # 应用样式隔离
        apply_simple_isolation(self)
    
    def enhanced_on_unmount(self):
        """增强的卸载方法"""
        # 移除样式隔离
        remove_simple_isolation(self)
        
        # 调用原始方法
        if original_on_unmount:
            original_on_unmount(self)
    
    # 替换方法
    screen_class.on_mount = enhanced_on_mount
    screen_class.on_unmount = enhanced_on_unmount
    
    return screen_class


class IsolatedScreenMixin:
    """
    样式隔离混合类
    为屏幕提供样式隔离功能
    """
    
    def on_mount(self) -> None:
        """屏幕挂载时应用样式隔离"""
        # 应用样式隔离
        apply_simple_isolation(self)
        
        # 调用父类方法（如果存在）
        try:
            super().on_mount()
        except AttributeError:
            pass
    
    def on_unmount(self) -> None:
        """屏幕卸载时移除样式隔离"""
        # 移除样式隔离
        remove_simple_isolation(self)
        
        # 调用父类方法（如果存在）
        try:
            super().on_unmount()
        except AttributeError:
            pass