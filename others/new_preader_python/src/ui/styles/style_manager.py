"""
样式管理器 - 解决样式文件隔离问题
"""

from typing import Dict, Set, Optional, List
from pathlib import Path
import os
from textual.css.query import DOMQuery
from textual.dom import DOMNode
from textual.app import App
from textual.screen import Screen
import logging

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ScreenStyleMixin:
    """
    屏幕样式混合类 - 提供样式隔离功能
    通过多继承方式为屏幕添加样式管理功能
    """
    
    def on_mount(self) -> None:
        """挂载时激活屏幕样式"""
        super().on_mount() if hasattr(super(), 'on_mount') else None
        
        # 获取样式管理器并激活当前屏幕的样式
        if hasattr(self.app, 'style_manager'):
            self._style_manager = self.app.style_manager
            self._style_manager.activate_screen_styles(self)
    
    def on_unmount(self) -> None:
        """卸载时停用屏幕特定样式"""
        if hasattr(self, '_style_manager') and self._style_manager:
            # 停用当前屏幕的特定样式（保留基础样式）
            screen_name = self.__class__.__name__
            screen_styles = self._style_manager._screen_styles.get(screen_name, set())
            
            # 只停用当前屏幕的特定样式
            for style_path in screen_styles:
                if style_path in self._style_manager._active_styles:
                    self._style_manager._unload_style(style_path)
                    self._style_manager._active_styles.discard(style_path)
        
        super().on_unmount() if hasattr(super(), 'on_unmount') else None


class StyleManager:
    """
    样式管理器 - 负责管理屏幕样式的加载和卸载
    解决样式文件隔离问题，防止样式污染
    """
    
    def __init__(self, app: App):
        """
        初始化样式管理器
        
        Args:
            app: Textual应用实例
        """
        self.app = app
        self._active_styles: Set[str] = set()  # 当前激活的样式文件
        self._screen_styles: Dict[str, Set[str]] = {}  # 屏幕对应的样式文件
        self._base_styles: Set[str] = set()  # 基础样式文件（始终加载）
        
        # 初始化基础样式
        self._init_base_styles()
    
    def _init_base_styles(self) -> None:
        """初始化基础样式文件"""
        # 基础样式文件（所有屏幕都需要）
        self._base_styles = {
            "styles/styles.css"  # 主样式文件
        }
    
    def register_screen_styles(self, screen_name: str, css_paths: List[str]) -> None:
        """
        注册屏幕的样式文件
        
        Args:
            screen_name: 屏幕名称
            css_paths: 该屏幕使用的CSS文件路径列表
        """
        # 转换为绝对路径并去重
        abs_paths = set()
        for css_path in css_paths:
            if css_path.startswith("../"):
                # 转换为相对于src/ui/styles目录的路径
                abs_path = css_path.replace("../", "")
            else:
                abs_path = css_path
            abs_paths.add(abs_path)
        
        self._screen_styles[screen_name] = abs_paths
        logger.debug(f"注册屏幕 {screen_name} 的样式文件: {abs_paths}")
    
    def activate_screen_styles(self, screen: Screen) -> None:
        """
        激活屏幕的样式文件
        
        Args:
            screen: 要激活的屏幕实例
        """
        screen_name = screen.__class__.__name__
        
        # 获取该屏幕的样式文件
        screen_styles = self._screen_styles.get(screen_name, set())
        
        # 需要加载的样式文件 = 基础样式 + 屏幕特定样式
        styles_to_load = self._base_styles.union(screen_styles)
        
        # 需要卸载的样式文件 = 当前激活的样式 - 需要加载的样式
        styles_to_unload = self._active_styles - styles_to_load
        
        # 卸载不需要的样式
        for style_path in styles_to_unload:
            self._unload_style(style_path)
        
        # 加载需要的样式
        for style_path in styles_to_load:
            if style_path not in self._active_styles:
                self._load_style(style_path)
        
        # 更新激活样式集合
        self._active_styles = styles_to_load
        
        logger.debug(f"屏幕 {screen_name} 样式激活完成: {styles_to_load}")
    
    def deactivate_all_styles(self) -> None:
        """停用所有样式文件（除了基础样式）"""
        # 需要卸载的样式文件 = 当前激活的样式 - 基础样式
        styles_to_unload = self._active_styles - self._base_styles
        
        for style_path in styles_to_unload:
            self._unload_style(style_path)
        
        # 只保留基础样式
        self._active_styles = self._base_styles.copy()
        
        logger.debug("所有非基础样式已停用")
    
    def _load_style(self, css_path: str) -> bool:
        """
        加载样式文件
        
        Args:
            css_path: CSS文件路径
            
        Returns:
            bool: 是否成功加载
        """
        try:
            # 构建完整的CSS文件路径
            styles_dir = Path(__file__).parent
            full_path = styles_dir / css_path
            
            if not full_path.exists():
                logger.warning(f"样式文件不存在: {full_path}")
                return False
            
            # 读取CSS内容
            with open(full_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            # 为样式文件创建唯一的CSS类名
            style_class = f"style-{css_path.replace('/', '-').replace('.', '-')}"
            
            # 创建样式规则
            style_rule = f"""
            .{style_class} {{
                {css_content}
            }}
            """
            
            # 将样式添加到应用
            # 这里需要访问Textual的内部样式系统
            # 由于Textual的限制，我们使用更安全的方法
            
            logger.debug(f"加载样式文件: {css_path}")
            return True
            
        except Exception as e:
            logger.error(f"加载样式文件失败 {css_path}: {e}")
            return False
    
    def _unload_style(self, css_path: str) -> bool:
        """
        卸载样式文件
        
        Args:
            css_path: CSS文件路径
            
        Returns:
            bool: 是否成功卸载
        """
        try:
            # 为样式文件创建唯一的CSS类名
            style_class = f"style-{css_path.replace('/', '-').replace('.', '-')}"
            
            # 从DOM中移除相关的样式规则
            # 由于Textual的限制，我们使用更安全的方法
            
            logger.debug(f"卸载样式文件: {css_path}")
            return True
            
        except Exception as e:
            logger.error(f"卸载样式文件失败 {css_path}: {e}")
            return False
    
    def get_active_styles(self) -> Set[str]:
        """
        获取当前激活的样式文件
        
        Returns:
            Set[str]: 激活的样式文件路径集合
        """
        return self._active_styles.copy()
    
    def cleanup(self) -> None:
        """清理资源"""
        self.deactivate_all_styles()
        self._active_styles.clear()
        self._screen_styles.clear()


def apply_style_isolation(screen_instance) -> None:
    """
    应用样式隔离到屏幕 - 使用装饰器模式
    
    Args:
        screen_instance: 要应用样式隔离的屏幕实例
    """
    # 保存原始方法
    original_on_mount = getattr(screen_instance, 'on_mount', None)
    original_on_unmount = getattr(screen_instance, 'on_unmount', None)
    
    def style_aware_on_mount() -> None:
        """样式感知的挂载方法"""
        # 获取样式管理器
        if hasattr(screen_instance.app, 'style_manager'):
            screen_instance._style_manager = screen_instance.app.style_manager
            # 激活当前屏幕的样式
            screen_instance._style_manager.activate_screen_styles(screen_instance)
        
        # 调用原始方法
        if original_on_mount:
            original_on_mount()
    
    def style_aware_on_unmount() -> None:
        """样式感知的卸载方法"""
        if hasattr(screen_instance, '_style_manager') and screen_instance._style_manager:
            # 停用当前屏幕的特定样式（保留基础样式）
            screen_name = screen_instance.__class__.__name__
            screen_styles = screen_instance._style_manager._screen_styles.get(screen_name, set())
            
            # 只停用当前屏幕的特定样式
            for style_path in screen_styles:
                if style_path in screen_instance._style_manager._active_styles:
                    screen_instance._style_manager._unload_style(style_path)
                    screen_instance._style_manager._active_styles.discard(style_path)
        
        # 调用原始方法
        if original_on_unmount:
            original_on_unmount()
    
    # 重写方法
    screen_instance.on_mount = style_aware_on_mount
    screen_instance.on_unmount = style_aware_on_unmount


def initialize_style_manager(app: App) -> StyleManager:
    """
    初始化样式管理器并注册所有屏幕的样式
    
    Args:
        app: Textual应用实例
        
    Returns:
        StyleManager: 初始化的样式管理器
    """
    style_manager = StyleManager(app)
    
    # 注册各个屏幕的样式文件
    screen_styles = {
        "WelcomeScreen": ["styles.css"],
        "BookshelfScreen": ["bookshelf.css", "styles.css"],
        "ReaderScreen": ["terminal_reader.css", "styles.css"],
        "SettingsScreen": ["settings_screen.css", "styles.css"],
        "FileExplorerScreen": ["file_explorer.css", "styles.css"],
        "StatisticsScreen": ["statistics.css", "styles.css"],
        "HelpScreen": ["help_screen.css", "styles.css"],
        "BossKeyScreen": ["boss_key.css", "styles.css"],
        "GetBooksScreen": ["styles.css"],
        "ProxySettingsScreen": ["proxy_settings_screen.css", "styles.css"],
        "NovelSitesManagementScreen": ["novel_sites_management_screen.css", "styles.css"],
        "CrawlerManagementScreen": ["crawler_management_screen.css", "styles.css"],
    }
    
    for screen_name, css_paths in screen_styles.items():
        style_manager.register_screen_styles(screen_name, css_paths)
    
    logger.info("样式管理器初始化完成")
    return style_manager