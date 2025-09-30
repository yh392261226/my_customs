"""
通用样式隔离系统
为所有屏幕和对话框提供统一的样式隔离支持
"""

from typing import Dict, Any, Optional, Set, List, Type, Union
from textual.screen import Screen, ModalScreen
from textual.app import App
import logging
import os
import re

logger = logging.getLogger(__name__)

class UniversalStyleIsolationManager:
    """通用样式隔离管理器"""
    
    def __init__(self):
        self._active_components: Dict[str, Union[Screen, ModalScreen]] = {}
        self._component_styles: Dict[str, str] = {}
        self._original_css: Optional[str] = None
        self._style_stack: List[str] = []  # 样式栈，支持嵌套
        
    def register_component(self, component: Union[Screen, ModalScreen], component_name: str) -> None:
        """注册需要样式隔离的组件"""
        self._active_components[component_name] = component
        logger.debug(f"注册组件样式隔离: {component_name}")
        
    def unregister_component(self, component_name: str) -> None:
        """注销组件的样式隔离"""
        if component_name in self._active_components:
            del self._active_components[component_name]
        if component_name in self._component_styles:
            del self._component_styles[component_name]
        # 从样式栈中移除
        if component_name in self._style_stack:
            self._style_stack.remove(component_name)
        logger.debug(f"注销组件样式隔离: {component_name}")
        
    def apply_component_isolation(self, component: Union[Screen, ModalScreen], component_name: str) -> None:
        """为组件应用样式隔离"""
        try:
            # 注册组件
            self.register_component(component, component_name)
            
            # 添加到样式栈
            if component_name not in self._style_stack:
                self._style_stack.append(component_name)
            
            # 生成隔离样式
            isolated_css = self._generate_isolated_css(component, component_name)
            if isolated_css:
                self._apply_css_to_app(component.app, isolated_css)
                self._component_styles[component_name] = isolated_css
                
            logger.info(f"应用组件样式隔离成功: {component_name}")
            
        except Exception as e:
            logger.error(f"应用组件样式隔离失败 {component_name}: {e}")
            
    def remove_component_isolation(self, component: Union[Screen, ModalScreen], component_name: str) -> None:
        """移除组件的样式隔离"""
        try:
            # 从样式栈中移除
            if component_name in self._style_stack:
                self._style_stack.remove(component_name)
            
            # 恢复到上一个样式状态
            self._restore_previous_style(component.app)
            
            # 注销组件
            self.unregister_component(component_name)
            
            logger.info(f"移除组件样式隔离成功: {component_name}")
            
        except Exception as e:
            logger.error(f"移除组件样式隔离失败 {component_name}: {e}")
            
    def _restore_previous_style(self, app: App) -> None:
        """恢复到上一个样式状态"""
        try:
            if self._style_stack:
                # 应用栈顶的样式
                top_component = self._style_stack[-1]
                if top_component in self._component_styles:
                    css_content = self._component_styles[top_component]
                    self._apply_css_to_app(app, css_content)
                    return
            
            # 如果栈为空，恢复基础样式
            base_css = self._get_base_css()
            self._apply_css_to_app(app, base_css)
            
        except Exception as e:
            logger.error(f"恢复样式状态失败: {e}")
            
    def _generate_isolated_css(self, component: Union[Screen, ModalScreen], component_name: str) -> str:
        """生成隔离的CSS"""
        try:
            # 获取组件的原始CSS
            original_css = self._get_component_css(component)
            if not original_css:
                # 如果没有专用CSS，使用默认样式
                original_css = self._get_default_component_css(component)
                
            # 为CSS添加命名空间前缀
            isolated_css = self._add_namespace_to_css(original_css, component_name)
            
            # 添加基础样式
            base_css = self._get_base_css()
            
            return f"{base_css}\n\n/* {component_name} 隔离样式 */\n{isolated_css}"
            
        except Exception as e:
            logger.error(f"生成隔离CSS失败 {component_name}: {e}")
            return ""
            
    def _get_component_css(self, component: Union[Screen, ModalScreen]) -> str:
        """获取组件的CSS内容"""
        try:
            css_path = getattr(component, 'CSS_PATH', None)
            if not css_path:
                return ""
                
            # 构建完整路径
            if hasattr(component, '__file__'):
                base_dir = os.path.dirname(component.__file__)
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
            logger.error(f"读取组件CSS失败: {e}")
            return ""
            
    def _get_default_component_css(self, component: Union[Screen, ModalScreen]) -> str:
        """获取组件的默认CSS样式"""
        if isinstance(component, ModalScreen):
            # 对话框默认样式
            return """
/* 对话框默认样式 */
ModalScreen {
    align: center middle;
    background: $background 60%;
}

Container {
    background: $surface;
    border: solid $primary;
    width: auto;
    height: auto;
    max-width: 80;
    max-height: 24;
    padding: 1;
}

Button {
    background: $primary;
    color: white;
    margin: 0 1;
}

Button:hover {
    background: $primary-lighten-1;
}

Button:focus {
    background: $primary-darken-1;
}

Input {
    background: $surface;
    color: $text;
    border: solid $primary;
}

Input:focus {
    border: solid $accent;
}

Label {
    color: $text;
}

Static {
    color: $text;
}
"""
        else:
            # 屏幕默认样式
            return """
/* 屏幕默认样式 */
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
    margin: 0 1;
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
    border: solid $primary;
}

Input:focus {
    border: solid $accent;
}
"""
            
    def _add_namespace_to_css(self, css_content: str, namespace: str) -> str:
        """为CSS添加命名空间前缀"""
        try:
            lines = css_content.split('\n')
            namespaced_lines = []
            
            for line in lines:
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('/*') or line.startswith('*/') or '*/' in line:
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
                        namespaced_selectors.append(f".{namespace}-component {sel}")
                    elif sel.lower() in ['screen', 'modalscreen', 'container', 'vertical', 'horizontal', 'grid', 'datatable', 'button', 'label', 'static', 'input']:
                        # 组件选择器
                        namespaced_selectors.append(f".{namespace}-component {sel}")
                    else:
                        # 其他选择器
                        namespaced_selectors.append(f".{namespace}-component {sel}")
                        
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

ModalScreen {
    align: center middle;
    background: $background 60%;
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

# 全局通用样式隔离管理器实例
global_universal_isolation_manager = UniversalStyleIsolationManager()

class UniversalStyleIsolatedScreen(Screen):
    """带通用样式隔离的屏幕基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._component_name = self.__class__.__name__.lower().replace('screen', '')
        
    def on_mount(self) -> None:
        """屏幕挂载时应用样式隔离"""
        super().on_mount()
        
        # 添加组件命名空间类
        if hasattr(self, 'add_class'):
            self.add_class(f"{self._component_name}-component")
            
        # 应用样式隔离
        global_universal_isolation_manager.apply_component_isolation(self, self._component_name)
        
    def on_unmount(self) -> None:
        """屏幕卸载时移除样式隔离"""
        # 移除样式隔离
        global_universal_isolation_manager.remove_component_isolation(self, self._component_name)
        
        super().on_unmount()

class UniversalStyleIsolatedModalScreen(ModalScreen):
    """带通用样式隔离的对话框基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._component_name = self.__class__.__name__.lower().replace('dialog', '').replace('screen', '')
        
    def on_mount(self) -> None:
        """对话框挂载时应用样式隔离"""
        super().on_mount()
        
        # 添加组件命名空间类
        if hasattr(self, 'add_class'):
            self.add_class(f"{self._component_name}-component")
            
        # 应用样式隔离
        global_universal_isolation_manager.apply_component_isolation(self, self._component_name)
        
    def on_unmount(self) -> None:
        """对话框卸载时移除样式隔离"""
        # 移除样式隔离
        global_universal_isolation_manager.remove_component_isolation(self, self._component_name)
        
        super().on_unmount()

def apply_universal_style_isolation(component: Union[Screen, ModalScreen]) -> None:
    """为组件应用通用样式隔离"""
    component_name = component.__class__.__name__.lower().replace('screen', '').replace('dialog', '')
    
    # 添加组件命名空间类
    if hasattr(component, 'add_class'):
        component.add_class(f"{component_name}-component")
        
    # 应用样式隔离
    global_universal_isolation_manager.apply_component_isolation(component, component_name)

def remove_universal_style_isolation(component: Union[Screen, ModalScreen]) -> None:
    """移除组件的通用样式隔离"""
    component_name = component.__class__.__name__.lower().replace('screen', '').replace('dialog', '')
    
    # 移除组件命名空间类
    if hasattr(component, 'remove_class'):
        component.remove_class(f"{component_name}-component")
        
    # 移除样式隔离
    global_universal_isolation_manager.remove_component_isolation(component, component_name)

# 装饰器支持
def universal_style_isolation(cls):
    """类装饰器：为屏幕或对话框类添加通用样式隔离支持"""
    original_on_mount = getattr(cls, 'on_mount', None)
    original_on_unmount = getattr(cls, 'on_unmount', None)
    
    def new_on_mount(self):
        if original_on_mount:
            original_on_mount(self)
        apply_universal_style_isolation(self)
    
    def new_on_unmount(self):
        remove_universal_style_isolation(self)
        if original_on_unmount:
            original_on_unmount(self)
    
    cls.on_mount = new_on_mount
    cls.on_unmount = new_on_unmount
    
    return cls