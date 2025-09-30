"""
实用样式隔离解决方案
专注于解决实际的样式污染问题，简单有效
"""

import os
from pathlib import Path
from typing import Dict, Set, List, Optional, Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

class PracticalStyleIsolation:
    """
    实用样式隔离管理器
    通过CSS命名空间和样式重置解决样式污染问题
    """
    
    def __init__(self):
        """初始化实用样式隔离管理器"""
        self._active_screen_classes: Set[str] = set()
        self._screen_namespaces: Dict[str, str] = {}
        
        # 屏幕到CSS文件的映射
        self._screen_css_mapping = {
            "WelcomeScreen": ["styles.css"],
            "BookshelfScreen": ["bookshelf.css", "styles.css"],
            "ReaderScreen": ["terminal_reader.css", "styles.css", "reader_components/reader_content.css"],
            "SettingsScreen": ["settings_screen.css", "styles.css"],
            "FileExplorerScreen": ["file_explorer.css", "styles.css"],
            "StatisticsScreen": ["statistics.css", "styles.css"],
            "HelpScreen": ["help_screen.css", "styles.css"],
            "BossKeyScreen": ["boss_key.css", "styles.css"],
            "GetBooksScreen": ["get_books_screen.css", "styles.css"],
            "ProxyListScreen": ["proxy_list_screen.css", "styles.css"],
            "NovelSitesManagementScreen": ["novel_sites_management_screen.css", "styles.css"],
            "CrawlerManagementScreen": ["crawler_management_screen.css", "styles.css"],
            "BookmarksScreen": ["bookmarks.css", "styles.css"],
            "SearchResultsScreen": ["search_results_dialog.css", "styles.css"],
        }
    
    def get_screen_namespace(self, screen_name: str) -> str:
        """获取屏幕的CSS命名空间"""
        if screen_name not in self._screen_namespaces:
            # 生成唯一的命名空间
            namespace = f"screen-{screen_name.lower().replace('screen', '')}"
            self._screen_namespaces[screen_name] = namespace
        return self._screen_namespaces[screen_name]
    
    def apply_screen_isolation(self, screen) -> None:
        """为屏幕应用样式隔离"""
        screen_name = screen.__class__.__name__
        namespace = self.get_screen_namespace(screen_name)
        
        try:
            # 清除之前的屏幕类
            self._clear_previous_screen_classes(screen)
            
            # 为屏幕添加命名空间类
            if hasattr(screen, 'add_class'):
                screen.add_class(namespace)
                screen.add_class('isolated-screen')  # 通用隔离类
                self._active_screen_classes.add(namespace)
            
            # 为屏幕的主要容器添加命名空间
            self._apply_container_isolation(screen, namespace)
            
            logger.debug(f"为屏幕 {screen_name} 应用样式隔离，命名空间: {namespace}")
            
        except Exception as e:
            logger.error(f"应用屏幕样式隔离失败 {screen_name}: {e}")
    
    def _clear_previous_screen_classes(self, screen) -> None:
        """清除之前屏幕的样式类"""
        try:
            if hasattr(screen, 'remove_class'):
                # 移除之前的屏幕命名空间类
                for class_name in list(self._active_screen_classes):
                    screen.remove_class(class_name)
                
                # 移除通用隔离类
                screen.remove_class('isolated-screen')
            
            # 清除记录
            self._active_screen_classes.clear()
            
        except Exception as e:
            logger.debug(f"清除之前屏幕类时出错: {e}")
    
    def _apply_container_isolation(self, screen, namespace: str) -> None:
        """为屏幕的容器应用隔离"""
        try:
            # 查找主要容器并添加命名空间类
            container_selectors = [
                "#main-container", "#app-content", ".container",
                "Container", "Vertical", "Horizontal", "Grid"
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
    
    def remove_screen_isolation(self, screen) -> None:
        """移除屏幕的样式隔离"""
        screen_name = screen.__class__.__name__
        namespace = self.get_screen_namespace(screen_name)
        
        try:
            # 移除命名空间类
            if hasattr(screen, 'remove_class'):
                screen.remove_class(namespace)
                screen.remove_class('isolated-screen')
            
            # 移除容器的隔离类
            self._remove_container_isolation(screen, namespace)
            
            # 从活动类集合中移除
            self._active_screen_classes.discard(namespace)
            
            logger.debug(f"移除屏幕 {screen_name} 的样式隔离")
            
        except Exception as e:
            logger.error(f"移除屏幕样式隔离失败 {screen_name}: {e}")
    
    def _remove_container_isolation(self, screen, namespace: str) -> None:
        """移除容器的隔离类"""
        try:
            container_selectors = [
                "#main-container", "#app-content", ".container",
                "Container", "Vertical", "Horizontal", "Grid"
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
    
    def reset_global_styles(self) -> None:
        """重置全局样式状态"""
        try:
            # 清除所有活动的屏幕类记录
            self._active_screen_classes.clear()
            
            logger.debug("重置全局样式状态完成")
            
        except Exception as e:
            logger.error(f"重置全局样式状态失败: {e}")
    
    def get_screen_css_files(self, screen_name: str) -> List[str]:
        """获取屏幕使用的CSS文件列表"""
        return self._screen_css_mapping.get(screen_name, ["styles.css"])
    
    def cleanup(self) -> None:
        """清理资源"""
        self._active_screen_classes.clear()
        self._screen_namespaces.clear()


# 全局实用样式隔离管理器实例
_practical_isolation_manager: Optional[PracticalStyleIsolation] = None

def get_practical_isolation_manager() -> PracticalStyleIsolation:
    """获取实用样式隔离管理器"""
    global _practical_isolation_manager
    if _practical_isolation_manager is None:
        _practical_isolation_manager = PracticalStyleIsolation()
    return _practical_isolation_manager

def apply_practical_style_isolation(screen) -> None:
    """为屏幕应用实用样式隔离"""
    manager = get_practical_isolation_manager()
    manager.apply_screen_isolation(screen)

def remove_practical_style_isolation(screen) -> None:
    """移除屏幕的实用样式隔离"""
    manager = get_practical_isolation_manager()
    manager.remove_screen_isolation(screen)

def reset_practical_styles() -> None:
    """重置实用样式状态"""
    manager = get_practical_isolation_manager()
    manager.reset_global_styles()


class PracticalStyleMixin:
    """
    实用样式混合类
    为屏幕提供简单有效的样式隔离功能
    """
    
    def on_mount(self) -> None:
        """屏幕挂载时应用样式隔离"""
        # 调用父类的on_mount方法
        if hasattr(super(), 'on_mount'):
            super().on_mount()
        
        # 应用样式隔离
        apply_practical_style_isolation(self)
    
    def on_unmount(self) -> None:
        """屏幕卸载时移除样式隔离"""
        # 移除样式隔离
        remove_practical_style_isolation(self)
        
        # 调用父类的on_unmount方法
        if hasattr(super(), 'on_unmount'):
            super().on_unmount()


def enhance_screen_with_practical_isolation(screen) -> None:
    """
    为屏幕增强实用样式隔离功能（装饰器模式）
    适用于无法修改类继承的情况
    """
    # 保存原始方法
    original_on_mount = getattr(screen, 'on_mount', None)
    original_on_unmount = getattr(screen, 'on_unmount', None)
    
    def enhanced_on_mount():
        """增强的挂载方法"""
        # 调用原始方法
        if original_on_mount:
            original_on_mount()
        
        # 应用样式隔离
        apply_practical_style_isolation(screen)
    
    def enhanced_on_unmount():
        """增强的卸载方法"""
        # 移除样式隔离
        remove_practical_style_isolation(screen)
        
        # 调用原始方法
        if original_on_unmount:
            original_on_unmount()
    
    # 替换方法
    screen.on_mount = enhanced_on_mount
    screen.on_unmount = enhanced_on_unmount