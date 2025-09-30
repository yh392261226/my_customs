"""
综合样式管理器
整合所有样式隔离和管理功能，提供统一的样式管理接口
"""

from typing import Dict, Set, List, Optional, Any
from textual.app import App
from textual.screen import Screen

from .enhanced_style_isolation import EnhancedStyleIsolation, initialize_enhanced_isolation
from .style_reset import StyleResetManager, initialize_style_reset_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ComprehensiveStyleManager:
    """
    综合样式管理器
    整合样式隔离、重置和管理功能
    """
    
    def __init__(self, app: App):
        """初始化综合样式管理器"""
        self.app = app
        
        # 初始化子管理器
        self.isolation_manager = initialize_enhanced_isolation(app)
        self.reset_manager = initialize_style_reset_manager(app)
        
        # 屏幕栈，用于跟踪屏幕切换
        self._screen_stack: List[str] = []
        self._active_screen: Optional[str] = None
        
        logger.info("综合样式管理器初始化完成")
    
    def on_screen_mount(self, screen: Screen) -> None:
        """屏幕挂载时的处理"""
        screen_name = screen.__class__.__name__
        
        try:
            # 备份当前屏幕的样式状态
            self.reset_manager.backup_screen_styles(screen)
            
            # 如果有之前的活动屏幕，先重置其样式
            if self._active_screen and self._active_screen != screen_name:
                self._cleanup_previous_screen()
            
            # 应用样式隔离
            self.isolation_manager.apply_screen_isolation(screen)
            
            # 更新活动屏幕
            self._active_screen = screen_name
            if screen_name not in self._screen_stack:
                self._screen_stack.append(screen_name)
            
            logger.debug(f"屏幕 {screen_name} 挂载完成，应用样式隔离")
            
        except Exception as e:
            logger.error(f"屏幕挂载时样式处理失败 {screen_name}: {e}")
    
    def on_screen_unmount(self, screen: Screen) -> None:
        """屏幕卸载时的处理"""
        screen_name = screen.__class__.__name__
        
        try:
            # 移除样式隔离
            self.isolation_manager.remove_screen_isolation(screen)
            
            # 重置屏幕样式
            self.reset_manager.reset_screen_styles(screen)
            
            # 从屏幕栈中移除
            if screen_name in self._screen_stack:
                self._screen_stack.remove(screen_name)
            
            # 清除样式备份
            self.reset_manager.clear_screen_backup(screen_name)
            
            # 更新活动屏幕
            if self._active_screen == screen_name:
                self._active_screen = self._screen_stack[-1] if self._screen_stack else None
            
            logger.debug(f"屏幕 {screen_name} 卸载完成，清理样式")
            
        except Exception as e:
            logger.error(f"屏幕卸载时样式处理失败 {screen_name}: {e}")
    
    def on_screen_resume(self, screen: Screen) -> None:
        """屏幕恢复时的处理"""
        screen_name = screen.__class__.__name__
        
        try:
            # 重新应用样式隔离
            self.isolation_manager.apply_screen_isolation(screen)
            
            # 更新活动屏幕
            self._active_screen = screen_name
            
            logger.debug(f"屏幕 {screen_name} 恢复，重新应用样式隔离")
            
        except Exception as e:
            logger.error(f"屏幕恢复时样式处理失败 {screen_name}: {e}")
    
    def on_screen_suspend(self, screen: Screen) -> None:
        """屏幕挂起时的处理"""
        screen_name = screen.__class__.__name__
        
        try:
            # 备份当前样式状态
            self.reset_manager.backup_screen_styles(screen)
            
            logger.debug(f"屏幕 {screen_name} 挂起，备份样式状态")
            
        except Exception as e:
            logger.error(f"屏幕挂起时样式处理失败 {screen_name}: {e}")
    
    def _cleanup_previous_screen(self) -> None:
        """清理前一个屏幕的样式影响"""
        if not self._active_screen:
            return
        
        try:
            # 这里可以添加更多的清理逻辑
            # 例如移除全局样式、重置特定属性等
            logger.debug(f"清理前一个屏幕 {self._active_screen} 的样式影响")
            
        except Exception as e:
            logger.error(f"清理前一个屏幕样式失败: {e}")
    
    def force_reset_all_styles(self) -> None:
        """强制重置所有样式（紧急情况使用）"""
        try:
            # 清理所有管理器状态
            self.isolation_manager.cleanup()
            self.reset_manager.cleanup()
            
            # 重置内部状态
            self._screen_stack.clear()
            self._active_screen = None
            
            logger.warning("强制重置所有样式完成")
            
        except Exception as e:
            logger.error(f"强制重置样式失败: {e}")
    
    def get_active_screen(self) -> Optional[str]:
        """获取当前活动屏幕"""
        return self._active_screen
    
    def get_screen_stack(self) -> List[str]:
        """获取屏幕栈"""
        return self._screen_stack.copy()
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            self.isolation_manager.cleanup()
            self.reset_manager.cleanup()
            self._screen_stack.clear()
            self._active_screen = None
            logger.info("综合样式管理器清理完成")
        except Exception as e:
            logger.error(f"综合样式管理器清理失败: {e}")


# 全局综合样式管理器实例
_comprehensive_style_manager: Optional[ComprehensiveStyleManager] = None

def initialize_comprehensive_style_manager(app: App) -> ComprehensiveStyleManager:
    """初始化综合样式管理器"""
    global _comprehensive_style_manager
    _comprehensive_style_manager = ComprehensiveStyleManager(app)
    return _comprehensive_style_manager

def get_comprehensive_style_manager() -> Optional[ComprehensiveStyleManager]:
    """获取综合样式管理器"""
    return _comprehensive_style_manager


class StyleAwareScreenMixin:
    """
    样式感知屏幕混合类
    为屏幕提供自动样式管理功能
    """
    
    def on_mount(self) -> None:
        """屏幕挂载时自动应用样式管理"""
        # 调用父类的on_mount方法
        if hasattr(super(), 'on_mount'):
            super().on_mount()
        
        # 应用样式管理
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_mount(self)
    
    def on_unmount(self) -> None:
        """屏幕卸载时自动清理样式"""
        # 清理样式
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_unmount(self)
        
        # 调用父类的on_unmount方法
        if hasattr(super(), 'on_unmount'):
            super().on_unmount()
    
    def on_resume(self) -> None:
        """屏幕恢复时重新应用样式"""
        # 调用父类的on_resume方法
        if hasattr(super(), 'on_resume'):
            super().on_resume()
        
        # 重新应用样式
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_resume(self)
    
    def on_suspend(self) -> None:
        """屏幕挂起时备份样式"""
        # 备份样式
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_suspend(self)
        
        # 调用父类的on_suspend方法
        if hasattr(super(), 'on_suspend'):
            super().on_suspend()


def apply_comprehensive_style_management(screen: Screen) -> None:
    """
    为屏幕应用综合样式管理（装饰器模式）
    适用于无法使用多继承的情况
    """
    # 保存原始方法
    original_on_mount = getattr(screen, 'on_mount', None)
    original_on_unmount = getattr(screen, 'on_unmount', None)
    original_on_resume = getattr(screen, 'on_resume', None)
    original_on_suspend = getattr(screen, 'on_suspend', None)
    
    def enhanced_on_mount():
        """增强的挂载方法"""
        # 应用样式管理
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_mount(screen)
        
        # 调用原始方法
        if original_on_mount:
            original_on_mount()
    
    def enhanced_on_unmount():
        """增强的卸载方法"""
        # 清理样式
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_unmount(screen)
        
        # 调用原始方法
        if original_on_unmount:
            original_on_unmount()
    
    def enhanced_on_resume():
        """增强的恢复方法"""
        # 重新应用样式
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_resume(screen)
        
        # 调用原始方法
        if original_on_resume:
            original_on_resume()
    
    def enhanced_on_suspend():
        """增强的挂起方法"""
        # 备份样式
        style_manager = get_comprehensive_style_manager()
        if style_manager:
            style_manager.on_screen_suspend(screen)
        
        # 调用原始方法
        if original_on_suspend:
            original_on_suspend()
    
    # 替换方法
    screen.on_mount = enhanced_on_mount
    screen.on_unmount = enhanced_on_unmount
    screen.on_resume = enhanced_on_resume
    screen.on_suspend = enhanced_on_suspend