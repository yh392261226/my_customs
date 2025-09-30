"""
更新的应用程序集成方案
将新的样式隔离系统集成到现有应用程序中
"""

from typing import Any
from textual.app import App
from textual.screen import Screen

from .comprehensive_style_manager import (
    initialize_comprehensive_style_manager,
    get_comprehensive_style_manager,
    apply_comprehensive_style_management
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

def integrate_style_management_to_app(app: "App[Any]") -> None:
    """
    将样式管理系统集成到应用程序中
    
    Args:
        app: Textual应用程序实例
    """
    try:
        # 初始化综合样式管理器
        style_manager = initialize_comprehensive_style_manager(app)
        
        # 将样式管理器附加到应用程序
        app.style_manager = style_manager
        
        # 保存原始的屏幕方法
        original_install_screen = app.install_screen
        original_push_screen = app.push_screen
        original_pop_screen = app.pop_screen
        
        def enhanced_install_screen(screen, *, name: str = None, **kwargs):
            """增强的安装屏幕方法"""
            # 为屏幕应用样式管理
            if isinstance(screen, type):
                # 如果是屏幕类，需要在实例化后应用
                result = original_install_screen(screen, name=name, **kwargs)
                # 获取实例化的屏幕
                screen_instance = app.get_screen(name) if name else None
                if screen_instance:
                    apply_comprehensive_style_management(screen_instance)
                return result
            else:
                # 如果是屏幕实例，直接应用
                apply_comprehensive_style_management(screen)
                return original_install_screen(screen, name=name, **kwargs)
        
        def enhanced_push_screen(screen, callback=None, **kwargs):
            """增强的推送屏幕方法"""
            # 如果是屏幕实例，应用样式管理
            if hasattr(screen, '__class__') and issubclass(screen.__class__, Screen):
                apply_comprehensive_style_management(screen)
            
            return original_push_screen(screen, callback=callback, **kwargs)
        
        def enhanced_pop_screen():
            """增强的弹出屏幕方法"""
            # 获取当前屏幕进行清理
            current_screen = app.screen
            if current_screen and style_manager:
                style_manager.on_screen_unmount(current_screen)
            
            return original_pop_screen()
        
        # 替换应用程序的方法
        app.install_screen = enhanced_install_screen
        app.push_screen = enhanced_push_screen
        app.pop_screen = enhanced_pop_screen
        
        logger.info("样式管理系统已成功集成到应用程序")
        
    except Exception as e:
        logger.error(f"集成样式管理系统失败: {e}")
        raise


def update_existing_screens_with_style_management(app: "App[Any]") -> None:
    """
    为现有屏幕更新样式管理
    
    Args:
        app: Textual应用程序实例
    """
    try:
        # 获取所有已安装的屏幕
        if hasattr(app, '_installed_screens'):
            for screen_name, screen_info in app._installed_screens.items():
                if hasattr(screen_info, 'screen'):
                    screen = screen_info.screen
                    if screen:
                        apply_comprehensive_style_management(screen)
                        logger.debug(f"为现有屏幕 {screen_name} 应用样式管理")
        
        logger.info("现有屏幕样式管理更新完成")
        
    except Exception as e:
        logger.error(f"更新现有屏幕样式管理失败: {e}")


class StyleManagedApp(App[Any]):
    """
    带有样式管理的应用程序基类
    继承此类可自动获得样式管理功能
    """
    
    def __init__(self, **kwargs):
        """初始化带样式管理的应用程序"""
        super().__init__(**kwargs)
        
        # 在应用程序初始化后集成样式管理
        self.call_after_refresh(self._integrate_style_management)
    
    def _integrate_style_management(self) -> None:
        """集成样式管理系统"""
        try:
            integrate_style_management_to_app(self)
        except Exception as e:
            logger.error(f"应用程序样式管理集成失败: {e}")
    
    def on_mount(self) -> None:
        super().on_mount()
        
        # 确保样式管理系统已初始化
        if not hasattr(self, 'style_manager'):
            self._integrate_style_management()


def create_style_aware_screen_class(base_screen_class):
    创建样式感知的屏幕类
    
    Args:
        base_screen_class: 基础屏幕类
        
    Returns:
        带有样式管理功能的屏幕类
    class StyleAwareScreen(base_screen_class):
        """样式感知的屏幕类"""
        
        def on_mount(self) -> None:
            # 应用样式管理
            style_manager = get_comprehensive_style_manager()
            if style_manager:
                style_manager.on_screen_mount(self)
            
            # 调用父类方法
            super().on_mount()
        
        def on_unmount(self) -> None:
            # 清理样式
            style_manager = get_comprehensive_style_manager()
            if style_manager:
                style_manager.on_screen_unmount(self)
            
            # 调用父类方法
            super().on_unmount()
    
    # 保持原始类名
    StyleAwareScreen.__name__ = base_screen_class.__name__
    StyleAwareScreen.__qualname__ = base_screen_class.__qualname__
    
    return StyleAwareScreen


# 装饰器版本
def style_managed_screen(screen_class):
    样式管理屏幕装饰器
    
    Args:
        screen_class: 要装饰的屏幕类
        
    Returns:
        带有样式管理功能的屏幕类
    return create_style_aware_screen_class(screen_class)


# 便捷函数
def apply_style_management_to_screen(screen: "Screen[Any]") -> None:
    为单个屏幕应用样式管理
    
    Args:
        screen: 屏幕实例
    apply_comprehensive_style_management(screen)


def cleanup_app_style_management(app: "App[Any]") -> None:
    清理应用程序的样式管理
    
    Args:
        app: 应用程序实例
    try:
        if hasattr(app, 'style_manager'):
            app.style_manager.cleanup()
            delattr(app, 'style_manager')
        
        logger.info("应用程序样式管理清理完成")
        
    except Exception as e:
        logger.error(f"清理应用程序样式管理失败: {e}")