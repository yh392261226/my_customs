"""
全面的样式隔离解决方案
解决书架页面、阅读器页面、爬取管理页面之间的样式污染问题
"""

from typing import Dict, Any, Optional, Set, List
from textual.screen import Screen
from textual.app import App
import logging

logger = logging.getLogger(__name__)

class StyleIsolationManager:
    """样式隔离管理器"""
    
    def __init__(self):
        self._active_screens: Dict[str, Screen] = {}
        self._screen_styles: Dict[str, str] = {}
        self._original_css: Optional[str] = None
        
    def register_screen(self, screen: Screen, screen_name: str) -> None:
        """注册需要样式隔离的屏幕"""
        self._active_screens[screen_name] = screen
        logger.debug(f"注册屏幕样式隔离: {screen_name}")
        
    def unregister_screen(self, screen_name: str) -> None:
        """注销屏幕的样式隔离"""
        if screen_name in self._active_screens:
            del self._active_screens[screen_name]
        if screen_name in self._screen_styles:
            del self._screen_styles[screen_name]
        logger.debug(f"注销屏幕样式隔离: {screen_name}")
        
    def apply_screen_isolation(self, screen: Screen, screen_name: str) -> None:
        """为屏幕应用样式隔离"""
        try:
            # 注册屏幕
            self.register_screen(screen, screen_name)
            
            # 清除之前的样式
            self._clear_previous_styles(screen.app)
            
            # 应用当前屏幕的隔离样式
            isolated_css = self._generate_isolated_css(screen, screen_name)
            if isolated_css:
                self._apply_css_to_app(screen.app, isolated_css)
                self._screen_styles[screen_name] = isolated_css
                
            logger.info(f"应用样式隔离成功: {screen_name}")
            
        except Exception as e:
            logger.error(f"应用样式隔离失败 {screen_name}: {e}")
            
    def remove_screen_isolation(self, screen: Screen, screen_name: str) -> None:
        """移除屏幕的样式隔离"""
        try:
            # 清除当前屏幕的样式
            self._clear_screen_styles(screen.app, screen_name)
            
            # 注销屏幕
            self.unregister_screen(screen_name)
            
            logger.info(f"移除样式隔离成功: {screen_name}")
            
        except Exception as e:
            logger.error(f"移除样式隔离失败 {screen_name}: {e}")
            
    def _clear_previous_styles(self, app: App) -> None:
        """清除之前的样式"""
        try:
            # 重置应用的CSS为基础样式
            if hasattr(app, 'stylesheet') and app.stylesheet:
                # 保存原始CSS（如果还没保存）
                if self._original_css is None:
                    self._original_css = str(app.stylesheet)
                
                # 清除所有屏幕特定的样式
                base_css = self._get_base_css()
                app.stylesheet.parse(base_css)
                app.stylesheet.update()
                
        except Exception as e:
            logger.error(f"清除之前样式失败: {e}")
            
    def _clear_screen_styles(self, app: App, screen_name: str) -> None:
        """清除特定屏幕的样式"""
        try:
            if hasattr(app, 'stylesheet') and app.stylesheet:
                # 重置为基础样式
                base_css = self._get_base_css()
                app.stylesheet.parse(base_css)
                app.stylesheet.update()
                
        except Exception as e:
            logger.error(f"清除屏幕样式失败 {screen_name}: {e}")
            
    def _generate_isolated_css(self, screen: Screen, screen_name: str) -> str:
        """生成隔离的CSS"""
        try:
            # 获取屏幕的原始CSS
            original_css = self._get_screen_css(screen)
            if not original_css:
                return ""
                
            # 为CSS添加命名空间前缀
            isolated_css = self._add_namespace_to_css(original_css, screen_name)
            
            # 添加基础样式
            base_css = self._get_base_css()
            
            return f"{base_css}\n\n/* {screen_name} 隔离样式 */\n{isolated_css}"
            
        except Exception as e:
            logger.error(f"生成隔离CSS失败 {screen_name}: {e}")
            return ""
            
    def _get_screen_css(self, screen: Screen) -> str:
        """获取屏幕的CSS内容"""
        try:
            css_path = getattr(screen, 'CSS_PATH', None)
            if not css_path:
                return ""
                
            # 构建完整路径
            import os
            if hasattr(screen, '__file__'):
                base_dir = os.path.dirname(screen.__file__)
            else:
                base_dir = os.path.dirname(__file__)
                
            full_path = os.path.join(base_dir, css_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"CSS文件不存在: {full_path}")
                return ""
                
        except Exception as e:
            logger.error(f"读取屏幕CSS失败: {e}")
            return ""
            
    def _add_namespace_to_css(self, css_content: str, namespace: str) -> str:
        """为CSS添加命名空间前缀"""
        try:
            lines = css_content.split('\n')
            namespaced_lines = []
            
            for line in lines:
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('/*') or line.startswith('*/'):
                    namespaced_lines.append(line)
                    continue
                    
                # 处理CSS选择器
                if '{' in line and not line.startswith('@'):
                    # 提取选择器部分
                    selector_part = line.split('{')[0].strip()
                    style_part = '{' + line.split('{', 1)[1] if '{' in line else ''
                    
                    # 为选择器添加命名空间
                    namespaced_selector = self._add_namespace_to_selector(selector_part, namespace)
                    namespaced_lines.append(f"{namespaced_selector} {style_part}")
                else:
                    namespaced_lines.append(line)
                    
            return '\n'.join(namespaced_lines)
            
        except Exception as e:
            logger.error(f"添加CSS命名空间失败: {e}")
            return css_content
            
    def _add_namespace_to_selector(self, selector: str, namespace: str) -> str:
        """为单个选择器添加命名空间"""
        try:
            # 分割多个选择器（逗号分隔）
            selectors = [s.strip() for s in selector.split(',')]
            namespaced_selectors = []
            
            for sel in selectors:
                if sel:
                    # 为每个选择器添加命名空间前缀
                    if sel.startswith('#') or sel.startswith('.'):
                        # ID或类选择器
                        namespaced_selectors.append(f".{namespace}-screen {sel}")
                    elif sel.lower() in ['screen', 'container', 'vertical', 'horizontal', 'grid', 'datatable', 'button', 'label', 'static', 'input']:
                        # 组件选择器
                        namespaced_selectors.append(f".{namespace}-screen {sel}")
                    else:
                        # 其他选择器
                        namespaced_selectors.append(f".{namespace}-screen {sel}")
                        
            return ', '.join(namespaced_selectors)
            
        except Exception as e:
            logger.error(f"添加选择器命名空间失败: {e}")
            return selector
            
    def _apply_css_to_app(self, app: App, css_content: str) -> None:
        """将CSS应用到应用"""
        try:
            if hasattr(app, 'stylesheet') and app.stylesheet:
                app.stylesheet.parse(css_content)
                app.stylesheet.update()
                
        except Exception as e:
            logger.error(f"应用CSS到应用失败: {e}")
            
    def _get_base_css(self) -> str:
        """获取基础CSS样式"""
        return """
/* 基础样式重置 */
Screen {
    background: $background;
    color: $text;
}

Container {
    background: transparent;
}

Button {
    background: $primary;
    color: white;
}

Button:hover {
    background: $primary-lighten-1;
}

Button:focus {
    background: $primary-darken-1;
}

DataTable {
    background: $surface;
    color: $text;
}

Label {
    color: $text;
}

Static {
    color: $text;
}

Input {
    background: $surface;
    color: $text;
}
"""

# 全局样式隔离管理器实例
global_style_isolation_manager = StyleIsolationManager()

class StyleIsolatedScreen(Screen):
    """带样式隔离的屏幕基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._screen_name = self.__class__.__name__.lower().replace('screen', '')
        
    def on_mount(self) -> None:
        """屏幕挂载时应用样式隔离"""
        super().on_mount()
        
        # 添加屏幕命名空间类
        if hasattr(self, 'add_class'):
            self.add_class(f"{self._screen_name}-screen")
            
        # 应用样式隔离
        global_style_isolation_manager.apply_screen_isolation(self, self._screen_name)
        
    def on_unmount(self) -> None:
        """屏幕卸载时移除样式隔离"""
        # 移除样式隔离
        global_style_isolation_manager.remove_screen_isolation(self, self._screen_name)
        
        super().on_unmount()

def apply_comprehensive_style_isolation(screen: Screen) -> None:
    """为屏幕应用全面的样式隔离"""
    screen_name = screen.__class__.__name__.lower().replace('screen', '')
    
    # 添加屏幕命名空间类
    if hasattr(screen, 'add_class'):
        screen.add_class(f"{screen_name}-screen")
        
    # 应用样式隔离
    global_style_isolation_manager.apply_screen_isolation(screen, screen_name)

def remove_comprehensive_style_isolation(screen: Screen) -> None:
    """移除屏幕的全面样式隔离"""
    screen_name = screen.__class__.__name__.lower().replace('screen', '')
    
    # 移除屏幕命名空间类
    if hasattr(screen, 'remove_class'):
        screen.remove_class(f"{screen_name}-screen")
        
    # 移除样式隔离
    global_style_isolation_manager.remove_screen_isolation(screen, screen_name)