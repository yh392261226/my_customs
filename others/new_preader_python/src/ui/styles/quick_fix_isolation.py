"""
快速修复样式隔离问题
提供立即可用的解决方案
"""

from typing import Dict, Set, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

class QuickStyleIsolation:
    """
    快速样式隔离解决方案
    专注于解决实际的样式污染问题
    """
    
    def __init__(self):
        """初始化快速样式隔离"""
        self._active_classes: Set[str] = set()
        
        # 屏幕到命名空间的映射
        self._screen_namespaces = {
            "WelcomeScreen": "welcome-screen",
            "BookshelfScreen": "bookshelf-screen", 
            "ReaderScreen": "reader-screen",
            "SettingsScreen": "settings-screen",
            "FileExplorerScreen": "fileexplorer-screen",
            "StatisticsScreen": "statistics-screen",
            "HelpScreen": "help-screen",
            "BossKeyScreen": "bosskey-screen",
            "GetBooksScreen": "getbooks-screen",
            "ProxyListScreen": "proxylist-screen",
            "NovelSitesManagementScreen": "novelsites-screen",
            "CrawlerManagementScreen": "crawler-screen",
            "BookmarksScreen": "bookmarks-screen",
            "SearchResultsScreen": "searchresults-screen",
        }
    
    def apply_isolation(self, screen) -> None:
        """为屏幕应用样式隔离"""
        if not screen:
            return
            
        screen_name = screen.__class__.__name__
        namespace = self._screen_namespaces.get(screen_name, f"{screen_name.lower()}-screen")
        
        try:
            # 清除之前的样式类
            self._clear_previous_classes(screen)
            
            # 添加新的隔离类
            if hasattr(screen, 'add_class'):
                screen.add_class(namespace)
                screen.add_class('isolated-screen')
                self._active_classes.add(namespace)
            
            logger.debug(f"为屏幕 {screen_name} 应用样式隔离: {namespace}")
            
        except Exception as e:
            logger.error(f"应用样式隔离失败 {screen_name}: {e}")
    
    def _clear_previous_classes(self, screen) -> None:
        """清除之前的样式类"""
        try:
            if hasattr(screen, 'remove_class'):
                # 移除所有活动的命名空间类
                for class_name in list(self._active_classes):
                    screen.remove_class(class_name)
                
                # 移除通用隔离类
                screen.remove_class('isolated-screen')
            
            # 清空记录
            self._active_classes.clear()
            
        except Exception as e:
            logger.debug(f"清除样式类时出错: {e}")
    
    def remove_isolation(self, screen) -> None:
        """移除屏幕的样式隔离"""
        if not screen:
            return
            
        screen_name = screen.__class__.__name__
        namespace = self._screen_namespaces.get(screen_name, f"{screen_name.lower()}-screen")
        
        try:
            if hasattr(screen, 'remove_class'):
                screen.remove_class(namespace)
                screen.remove_class('isolated-screen')
            
            self._active_classes.discard(namespace)
            
            logger.debug(f"移除屏幕 {screen_name} 的样式隔离")
            
        except Exception as e:
            logger.error(f"移除样式隔离失败 {screen_name}: {e}")
    
    def reset(self) -> None:
        """重置隔离状态"""
        self._active_classes.clear()
        logger.debug("样式隔离状态已重置")


# 全局实例
_quick_isolation: Optional[QuickStyleIsolation] = None

def get_quick_isolation() -> QuickStyleIsolation:
    """获取快速样式隔离实例"""
    global _quick_isolation
    if _quick_isolation is None:
        _quick_isolation = QuickStyleIsolation()
    return _quick_isolation

def apply_quick_isolation(screen) -> None:
    """为屏幕应用快速样式隔离"""
    isolation = get_quick_isolation()
    isolation.apply_isolation(screen)

def remove_quick_isolation(screen) -> None:
    """移除屏幕的快速样式隔离"""
    isolation = get_quick_isolation()
    isolation.remove_isolation(screen)

def reset_quick_isolation() -> None:
    """重置快速样式隔离状态"""
    isolation = get_quick_isolation()
    isolation.reset()


class QuickIsolationMixin:
    """
    快速样式隔离混合类
    最简单的使用方式
    """
    
    def on_mount(self) -> None:
        """屏幕挂载时应用样式隔离"""
        # 应用样式隔离
        apply_quick_isolation(self)
        
        # 调用父类方法
        try:
            super().on_mount()
        except AttributeError:
            pass
    
    def on_unmount(self) -> None:
        """屏幕卸载时移除样式隔离"""
        # 移除样式隔离
        remove_quick_isolation(self)
        
        # 调用父类方法
        try:
            super().on_unmount()
        except AttributeError:
            pass


def quick_isolation_decorator(screen_class):
    """
    快速样式隔离装饰器
    为现有屏幕类添加样式隔离功能
    """
    original_on_mount = getattr(screen_class, 'on_mount', None)
    original_on_unmount = getattr(screen_class, 'on_unmount', None)
    
    def enhanced_on_mount(self):
        """增强的挂载方法"""
        # 应用样式隔离
        apply_quick_isolation(self)
        
        # 调用原始方法
        if original_on_mount:
            original_on_mount(self)
    
    def enhanced_on_unmount(self):
        """增强的卸载方法"""
        # 移除样式隔离
        remove_quick_isolation(self)
        
        # 调用原始方法
        if original_on_unmount:
            original_on_unmount(self)
    
    # 替换方法
    screen_class.on_mount = enhanced_on_mount
    screen_class.on_unmount = enhanced_on_unmount
    
    return screen_class