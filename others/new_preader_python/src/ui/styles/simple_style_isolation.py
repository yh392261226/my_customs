"""
简单样式隔离解决方案
通过为每个屏幕添加唯一的CSS类名来实现样式隔离
"""

from typing import Dict, Set
from pathlib import Path
import logging

from src.utils.logger import get_logger

logger = get_logger(__name__)

class SimpleStyleIsolation:
    """
    简单样式隔离管理器
    通过为每个屏幕添加唯一的CSS类名来隔离样式
    """
    
    def __init__(self):
        """初始化简单样式隔离管理器"""
        self._screen_classes: Dict[str, str] = {}
        
        # 屏幕到CSS文件的映射
        self._screen_css_mapping = {
            "WelcomeScreen": ["styles.css"],
            "BookshelfScreen": ["bookshelf.css", "styles.css"],
            "ReaderScreen": ["terminal_reader.css", "styles.css"],
            "SettingsScreen": ["settings_screen.css", "styles.css"],
            "FileExplorerScreen": ["file_explorer.css", "styles.css"],
            "StatisticsScreen": ["statistics.css", "styles.css"],
            "HelpScreen": ["help_screen.css", "styles.css"],
            "BossKeyScreen": ["boss_key.css", "styles.css"],
            "GetBooksScreen": ["styles.css"],
            "ProxyListScreen": ["proxy_list_screen.css", "styles.css"],
            "NovelSitesManagementScreen": ["novel_sites_management_screen.css", "styles.css"],
            "CrawlerManagementScreen": ["crawler_management_screen.css", "styles.css"],
        }
    
    def get_screen_class(self, screen_name: str) -> str:
        """
        获取屏幕的CSS类名
        
        Args:
            screen_name: 屏幕名称
            
        Returns:
            str: CSS类名
        """
        if screen_name not in self._screen_classes:
            # 生成唯一的CSS类名
            class_name = f"screen-{screen_name.lower().replace('screen', '')}"
            self._screen_classes[screen_name] = class_name
        
        return self._screen_classes[screen_name]
    
    def apply_isolation(self, screen_instance) -> None:
        """
        为屏幕实例应用样式隔离
        
        Args:
            screen_instance: 屏幕实例
        """
        screen_name = screen_instance.__class__.__name__
        screen_class = self.get_screen_class(screen_name)
        
        # 为屏幕容器添加唯一的CSS类名
        try:
            # 直接为屏幕实例添加CSS类
            if hasattr(screen_instance, 'add_class'):
                screen_instance.add_class(screen_class)
                logger.debug(f"为屏幕 {screen_name} 应用样式隔离类: {screen_class}")
            
            # 如果屏幕有特定的容器，也为该容器添加类名
            if hasattr(screen_instance, 'query_one'):
                try:
                    main_container = screen_instance.query_one("#main-container")
                    if main_container:
                        main_container.add_class(screen_class)
                except Exception:
                    # 如果找不到主容器，忽略错误
                    pass
                    
        except Exception as e:
            logger.warning(f"为屏幕 {screen_name} 应用样式隔离失败: {e}")
    
    def get_screen_css_files(self, screen_name: str) -> Set[str]:
        """
        获取屏幕使用的CSS文件
        
        Args:
            screen_name: 屏幕名称
            
        Returns:
            Set[str]: CSS文件路径集合
        """
        return set(self._screen_css_mapping.get(screen_name, ["styles.css"]))


# 创建全局实例
_style_isolation = SimpleStyleIsolation()

def apply_simple_style_isolation(screen_instance) -> None:
    """
    为屏幕实例应用简单样式隔离
    
    Args:
        screen_instance: 屏幕实例
    """
    _style_isolation.apply_isolation(screen_instance)

def get_screen_isolation_class(screen_name: str) -> str:
    """
    获取屏幕的隔离类名
    
    Args:
        screen_name: 屏幕名称
        
    Returns:
        str: CSS类名
    """
    return _style_isolation.get_screen_class(screen_name)

def get_screen_css_files(screen_name: str) -> Set[str]:
    """
    获取屏幕使用的CSS文件
    
    Args:
        screen_name: 屏幕名称
        
    Returns:
        Set[str]: CSS文件路径集合
    """
    return _style_isolation.get_screen_css_files(screen_name)