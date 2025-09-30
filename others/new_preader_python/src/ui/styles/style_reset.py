"""
样式重置工具
用于在屏幕切换时重置样式状态，防止样式污染
"""

from typing import Dict, Set, List, Optional
from textual.app import App
from textual.screen import Screen
from textual.dom import DOMNode

from src.utils.logger import get_logger

logger = get_logger(__name__)

class StyleResetManager:
    """
    样式重置管理器
    负责在屏幕切换时重置样式状态
    """
    
    def __init__(self, app: App):
        """初始化样式重置管理器"""
        self.app = app
        self._screen_style_states: Dict[str, Dict[str, any]] = {}
        self._global_style_backup: Optional[str] = None
    
    def backup_screen_styles(self, screen: Screen) -> None:
        """备份屏幕的样式状态"""
        screen_name = screen.__class__.__name__
        
        try:
            # 备份屏幕的样式相关属性
            style_state = {
                'classes': getattr(screen, 'classes', set()).copy(),
                'css_path': getattr(screen, 'CSS_PATH', None),
                'styles': {}
            }
            
            # 备份子组件的样式状态
            if hasattr(screen, 'query'):
                try:
                    for widget in screen.query("*"):
                        widget_id = getattr(widget, 'id', None)
                        if widget_id:
                            style_state['styles'][widget_id] = {
                                'classes': getattr(widget, 'classes', set()).copy(),
                                'styles': getattr(widget, 'styles', {}).copy() if hasattr(widget, 'styles') else {}
                            }
                except Exception as e:
                    logger.debug(f"备份子组件样式时出错: {e}")
            
            self._screen_style_states[screen_name] = style_state
            logger.debug(f"备份屏幕 {screen_name} 的样式状态")
            
        except Exception as e:
            logger.error(f"备份屏幕样式失败 {screen_name}: {e}")
    
    def reset_screen_styles(self, screen: Screen) -> None:
        """重置屏幕的样式状态"""
        screen_name = screen.__class__.__name__
        
        try:
            # 清除屏幕的动态添加的类
            if hasattr(screen, 'classes'):
                # 保留原始类，移除动态添加的类
                original_classes = {'screen', screen_name.lower()}
                current_classes = getattr(screen, 'classes', set())
                dynamic_classes = current_classes - original_classes
                
                for cls in dynamic_classes:
                    if hasattr(screen, 'remove_class'):
                        screen.remove_class(cls)
            
            # 重置子组件的样式
            if hasattr(screen, 'query'):
                try:
                    for widget in screen.query("*"):
                        self._reset_widget_styles(widget)
                except Exception as e:
                    logger.debug(f"重置子组件样式时出错: {e}")
            
            logger.debug(f"重置屏幕 {screen_name} 的样式状态")
            
        except Exception as e:
            logger.error(f"重置屏幕样式失败 {screen_name}: {e}")
    
    def _reset_widget_styles(self, widget) -> None:
        """重置单个组件的样式"""
        try:
            # 清除动态添加的类
            if hasattr(widget, 'classes'):
                # 获取组件的原始类名
                widget_type = widget.__class__.__name__.lower()
                original_classes = {widget_type}
                
                # 如果有ID，也保留ID相关的类
                if hasattr(widget, 'id') and widget.id:
                    original_classes.add(widget.id)
                
                current_classes = getattr(widget, 'classes', set())
                dynamic_classes = current_classes - original_classes
                
                for cls in dynamic_classes:
                    if hasattr(widget, 'remove_class'):
                        widget.remove_class(cls)
            
            # 重置内联样式（如果支持）
            if hasattr(widget, 'styles') and hasattr(widget.styles, 'clear'):
                # 不完全清除，只清除可能冲突的样式
                conflicting_styles = [
                    'background', 'color', 'border', 'margin', 'padding',
                    'width', 'height', 'display', 'position'
                ]
                
                for style_name in conflicting_styles:
                    if hasattr(widget.styles, style_name):
                        try:
                            delattr(widget.styles, style_name)
                        except:
                            pass
            
        except Exception as e:
            logger.debug(f"重置组件样式失败: {e}")
    
    def restore_screen_styles(self, screen: Screen) -> None:
        """恢复屏幕的样式状态"""
        screen_name = screen.__class__.__name__
        
        if screen_name not in self._screen_style_states:
            return
        
        try:
            style_state = self._screen_style_states[screen_name]
            
            # 恢复屏幕类
            if 'classes' in style_state and hasattr(screen, 'add_class'):
                for cls in style_state['classes']:
                    screen.add_class(cls)
            
            # 恢复子组件样式
            if 'styles' in style_state and hasattr(screen, 'query'):
                try:
                    for widget_id, widget_style in style_state['styles'].items():
                        try:
                            widget = screen.query_one(f"#{widget_id}")
                            
                            # 恢复类
                            if 'classes' in widget_style and hasattr(widget, 'add_class'):
                                for cls in widget_style['classes']:
                                    widget.add_class(cls)
                            
                        except Exception:
                            # 组件可能不存在，忽略
                            pass
                except Exception as e:
                    logger.debug(f"恢复子组件样式时出错: {e}")
            
            logger.debug(f"恢复屏幕 {screen_name} 的样式状态")
            
        except Exception as e:
            logger.error(f"恢复屏幕样式失败 {screen_name}: {e}")
    
    def clear_screen_backup(self, screen_name: str) -> None:
        """清除屏幕的样式备份"""
        if screen_name in self._screen_style_states:
            del self._screen_style_states[screen_name]
            logger.debug(f"清除屏幕 {screen_name} 的样式备份")
    
    def cleanup(self) -> None:
        """清理资源"""
        self._screen_style_states.clear()
        self._global_style_backup = None


# 全局样式重置管理器实例
_style_reset_manager: Optional[StyleResetManager] = None

def initialize_style_reset_manager(app: App) -> StyleResetManager:
    """初始化样式重置管理器"""
    global _style_reset_manager
    _style_reset_manager = StyleResetManager(app)
    return _style_reset_manager

def get_style_reset_manager() -> Optional[StyleResetManager]:
    """获取样式重置管理器"""
    return _style_reset_manager

def backup_screen_styles(screen: Screen) -> None:
    """备份屏幕样式"""
    if _style_reset_manager:
        _style_reset_manager.backup_screen_styles(screen)

def reset_screen_styles(screen: Screen) -> None:
    """重置屏幕样式"""
    if _style_reset_manager:
        _style_reset_manager.reset_screen_styles(screen)

def restore_screen_styles(screen: Screen) -> None:
    """恢复屏幕样式"""
    if _style_reset_manager:
        _style_reset_manager.restore_screen_styles(screen)