"""
样式隔离管理器 - 简单有效的样式隔离解决方案
通过CSS类名隔离和样式重置，彻底解决样式污染问题
"""

from typing import Dict, Set
import logging

from src.utils.logger import get_logger

logger = get_logger(__name__)

class StyleIsolationManager:
    """
    样式隔离管理器
    通过CSS类名隔离和样式重置，彻底解决样式污染问题
    """
    
    def __init__(self):
        """初始化样式隔离管理器"""
        self._screen_classes: Dict[str, str] = {}
        self._active_screens: Set[str] = set()
        
    def apply_isolation(self, screen_instance) -> None:
        """
        为屏幕实例应用样式隔离
        
        Args:
            screen_instance: 屏幕实例
        """
        screen_name = screen_instance.__class__.__name__
        screen_class = self._get_screen_class(screen_name)
        
        try:
            # 为屏幕添加CSS类
            if hasattr(screen_instance, 'add_class'):
                screen_instance.add_class(screen_class)
                self._active_screens.add(screen_name)
                logger.debug(f"为屏幕 {screen_name} 应用样式隔离类: {screen_class}")
            
            # 激活当前屏幕
            self._activate_screen(screen_name)
            
        except Exception as e:
            logger.warning(f"为屏幕 {screen_name} 应用样式隔离失败: {e}")
    
    def remove_isolation(self, screen_instance) -> None:
        """
        从屏幕实例移除样式隔离
        
        Args:
            screen_instance: 屏幕实例
        """
        screen_name = screen_instance.__class__.__name__
        screen_class = self._screen_classes.get(screen_name)
        
        if screen_class:
            try:
                # 移除CSS类
                if hasattr(screen_instance, 'remove_class'):
                    screen_instance.remove_class(screen_class)
                    self._active_screens.discard(screen_name)
                    logger.debug(f"从屏幕 {screen_name} 移除样式隔离类: {screen_class}")
                
                # 停用当前屏幕
                self._deactivate_screen(screen_name)
                
            except Exception as e:
                logger.warning(f"从屏幕 {screen_name} 移除样式隔离失败: {e}")
    
    def _get_screen_class(self, screen_name: str) -> str:
        """
        获取屏幕的CSS类名
        
        Args:
            screen_name: 屏幕名称
            
        Returns:
            str: CSS类名
        """
        if screen_name not in self._screen_classes:
            # 生成唯一的CSS类名
            # 移除"Screen"后缀
            base_name = screen_name.replace('Screen', '')
            
            # 将驼峰命名转换为连字符命名
            import re
            # 在大写字母前插入连字符，然后转换为小写
            if base_name:
                class_name = re.sub(r'(?<!^)(?=[A-Z])', '-', base_name).lower()
                class_name = f"screen-{class_name}"
            else:
                class_name = f"screen-{screen_name.lower()}"
            self._screen_classes[screen_name] = class_name
        
        return self._screen_classes[screen_name]
    
    def _activate_screen(self, screen_name: str) -> None:
        """
        激活屏幕
        
        Args:
            screen_name: 屏幕名称
        """
        # 停用其他屏幕
        for active_screen in list(self._active_screens):
            if active_screen != screen_name:
                self._deactivate_screen(active_screen)
        
        # 激活当前屏幕
        self._active_screens.add(screen_name)
    
    def _deactivate_screen(self, screen_name: str) -> None:
        """
        停用屏幕
        
        Args:
            screen_name: 屏幕名称
        """
        self._active_screens.discard(screen_name)
    
    def get_active_screens(self) -> Set[str]:
        """
        获取当前激活的屏幕
        
        Returns:
            Set[str]: 激活的屏幕名称集合
        """
        return self._active_screens.copy()


# 创建全局实例
_isolation_manager = StyleIsolationManager()

def apply_style_isolation(screen_instance) -> None:
    """
    为屏幕实例应用样式隔离
    
    Args:
        screen_instance: 屏幕实例
    """
    _isolation_manager.apply_isolation(screen_instance)

def remove_style_isolation(screen_instance) -> None:
    """
    从屏幕实例移除样式隔离
    
    Args:
        screen_instance: 屏幕实例
    """
    _isolation_manager.remove_isolation(screen_instance)

def get_screen_isolation_class(screen_name: str) -> str:
    """
    获取屏幕的隔离类名
    
    Args:
        screen_name: 屏幕名称
        
    Returns:
        str: CSS类名
    """
    return _isolation_manager._get_screen_class(screen_name)