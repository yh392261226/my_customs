"""
主题管理器，负责处理应用程序的主题和样式
"""


from typing import Dict, Any, List, Optional

from rich.style import Style
from rich.color import Color
from rich.theme import Theme as RichTheme
from textual.theme import Theme
from src.config.default_config import AVAILABLE_THEMES

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ThemeManager:
    """主题管理器类，负责处理应用程序的主题和样式"""
    
    def __init__(self, default_theme: str = "dark"):
        """
        初始化主题管理器
        
        Args:
            default_theme: 默认主题名称
        """
        self.themes = {}
        self.current_theme_name = default_theme
        
        # 加载所有内置主题
        self._load_builtin_themes()
        
        # 设置当前主题
        self.set_theme(default_theme)
    
    def _load_builtin_themes(self) -> None:
        """加载所有内置主题"""
        # 加载深色主题
        self.themes["dark"] = {
            "app.title": Style(color="#90EE90", bold=True),
            "app.subtitle": Style(color="#C8E6C9"),
            "app.accent": Style(color="#00BFFF"),
            "app.highlight": Style(color="#FFD700"),
            "app.warning": Style(color="#FF6B6B"),
            "app.success": Style(color="#32CD32"),
            "app.info": Style(color="#87CEEB"),
            "app.muted": Style(color="#708090"),
            
            "ui.border": Style(color="#708090"),
            "ui.background": Style(bgcolor="black"),
            "ui.panel": Style(bgcolor="#2F2F2F"),
            "ui.panel.title": Style(color="#90EE90", bold=True),
            "ui.label": Style(color="#C8E6C9"),
            "ui.button": Style(color="#2E3440", bgcolor="#D8DEE9"),
            "ui.button.primary": Style(color="#ECEFF4", bgcolor="#5E81AC"),
            "ui.button.success": Style(color="#ECEFF4", bgcolor="#A3BE8C"),
            "ui.button.warning": Style(color="#2E3440", bgcolor="#EBCB8B"),
            "ui.button.danger": Style(color="#ECEFF4", bgcolor="#BF616A"),
            "ui.input": Style(color="#C8E6C9", bgcolor="#434C5E"),
            "ui.input.focus": Style(color="#90EE90", bgcolor="#4C566A"),
            "ui.selection": Style(bgcolor="#3F3F3F"),
            
            "content.text": Style(color="#C8E6C9"),
            "content.heading": Style(color="#90EE90", bold=True),
            "content.subheading": Style(color="#C8E6C9", bold=True),
            "content.link": Style(color="#00BFFF", underline=True),
            "content.quote": Style(color="#C8E6C9", italic=True),
            "content.code": Style(color="#32CD32", bgcolor="#2F2F2F"),
            "content.highlight": Style(color="#000000", bgcolor="#FFD700"),
            
            "progress.bar": Style(color="#00BFFF"),
            "progress.text": Style(color="#C8E6C9"),
            "progress.percentage": Style(color="#90EE90"),
            
            "bookshelf.title": Style(color="#90EE90", bold=True),
            "bookshelf.author": Style(color="#C8E6C9"),
            "bookshelf.progress": Style(color="#00BFFF"),
            "bookshelf.tag": Style(color="#708090", bgcolor="#3F3F3F"),
            "bookshelf.selected": Style(bgcolor="#3b3b3b"),
            
            "reader.text": Style(color="#C8E6C9"),
            "reader.chapter": Style(color="#90EE90", bold=True),
            "reader.page_number": Style(color="#708090"),
            "reader.bookmark": Style(color="#FFD700"),
            "reader.search_result": Style(color="#000000", bgcolor="#FFD700"),
        }
        
        # 加载浅色主题
        self.themes["light"] = {
            "app.title": Style(color="black", bold=True),
            "app.subtitle": Style(color="#808080"),
            "app.accent": Style(color="blue"),
            "app.highlight": Style(color="#FFD700"),
            "app.warning": Style(color="red"),
            "app.success": Style(color="green"),
            "app.info": Style(color="cyan"),
            "app.muted": Style(color="#808080"),
            
            "ui.border": Style(color="#808080"),
            "ui.background": Style(bgcolor="white"),
            "ui.panel": Style(bgcolor="#eeeeee"),
            "ui.panel.title": Style(color="black", bold=True),
            "ui.label": Style(color="#262626"),
            "ui.button": Style(color="white", bgcolor="#808080"),
            "ui.button.primary": Style(color="white", bgcolor="blue"),
            "ui.button.success": Style(color="white", bgcolor="green"),
            "ui.button.warning": Style(color="white", bgcolor="#FFD700"),
            "ui.button.danger": Style(color="white", bgcolor="red"),
            "ui.input": Style(color="black", bgcolor="#d9d9d9"),
            "ui.input.focus": Style(color="black", bgcolor="#c7c7c7"),
            "ui.selection": Style(bgcolor="#d9d9d9"),
            
            "content.text": Style(color="#262626"),
            "content.heading": Style(color="black", bold=True),
            "content.subheading": Style(color="#4d4d4d", bold=True),
            "content.link": Style(color="blue", underline=True),
            "content.quote": Style(color="#4d4d4d", italic=True),
            "content.code": Style(color="green", bgcolor="#eeeeee"),
            "content.highlight": Style(color="white", bgcolor="#FFD700"),
            
            "progress.bar": Style(color="blue"),
            "progress.text": Style(color="#4d4d4d"),
            "progress.percentage": Style(color="black"),
            
            "bookshelf.title": Style(color="black", bold=True),
            "bookshelf.author": Style(color="#4d4d4d"),
            "bookshelf.progress": Style(color="blue"),
            "bookshelf.tag": Style(color="#808080", bgcolor="#d9d9d9"),
            "bookshelf.selected": Style(bgcolor="#d9d9d9"),
            
            "reader.text": Style(color="#262626"),
            "reader.chapter": Style(color="black", bold=True),
            "reader.page_number": Style(color="#808080"),
            "reader.bookmark": Style(color="#FFD700"),
            "reader.search_result": Style(color="white", bgcolor="#FFD700"),
        }
        
        # 加载Nord主题 - 使用多样化的颜色
        self.themes["nord"] = {
            "app.title": Style(color="#ECEFF4", bold=True),
            "app.subtitle": Style(color="#D8DEE9"),
            "app.accent": Style(color="#88C0D0"),
            "app.highlight": Style(color="#EBCB8B"),
            "app.warning": Style(color="#BF616A"),
            "app.success": Style(color="#A3BE8C"),
            "app.info": Style(color="#81A1C1"),
            "app.muted": Style(color="#4C566A"),
            
            "ui.border": Style(color="#4C566A"),
            "ui.background": Style(bgcolor="#2e3440"),  # 深蓝色背景
            "ui.panel": Style(bgcolor="#3B4252"),
            "ui.panel.title": Style(color="#ECEFF4", bold=True),
            "ui.label": Style(color="#e5e9f0"),  # 北极浅蓝色字体
            "ui.button": Style(color="#2E3440", bgcolor="#D8DEE9"),
            "ui.button.primary": Style(color="#ECEFF4", bgcolor="#5E81AC"),
            "ui.button.success": Style(color="#ECEFF4", bgcolor="#A3BE8C"),
            "ui.button.warning": Style(color="#ECEFF4", bgcolor="#EBCB8B"),
            "ui.button.danger": Style(color="#ECEFF4", bgcolor="#BF616A"),
            "ui.input": Style(color="#ECEFF4", bgcolor="#434C5E"),
            "ui.input.focus": Style(color="#ECEFF4", bgcolor="#4C566A"),
            "ui.selection": Style(bgcolor="#434C5E"),
            
            "content.text": Style(color="#e5e9f0"),  # 北极浅蓝色字体
            "content.heading": Style(color="#ECEFF4", bold=True),
            "content.subheading": Style(color="#D8DEE9", bold=True),
            "content.link": Style(color="#88C0D0", underline=True),
            "content.quote": Style(color="#D8DEE9", italic=True),
            "content.code": Style(color="#A3BE8C", bgcolor="#3B4252"),
            "content.highlight": Style(color="#ECEFF4", bgcolor="#EBCB8B"),
            
            "progress.bar": Style(color="#88C0D0"),
            "progress.text": Style(color="#D8DEE9"),
            "progress.percentage": Style(color="#ECEFF4"),
            
            "bookshelf.title": Style(color="#ECEFF4", bold=True),
            "bookshelf.author": Style(color="#D8DEE9"),
            "bookshelf.progress": Style(color="#88C0D0"),
            "bookshelf.tag": Style(color="#D8DEE9", bgcolor="#434C5E"),
            "bookshelf.selected": Style(bgcolor="#434C5E"),
            
            "reader.text": Style(color="#e5e9f0"),  # 北极浅蓝色字体
            "reader.chapter": Style(color="#ECEFF4", bold=True),
            "reader.page_number": Style(color="#4C566A"),
            "reader.bookmark": Style(color="#EBCB8B"),
            "reader.search_result": Style(color="#ECEFF4", bgcolor="#EBCB8B"),
        }
        
        # 加载Dracula主题
        self.themes["dracula"] = {
            "app.title": Style(color="#F8F8F2", bold=True),
            "app.subtitle": Style(color="#BFBFBF"),
            "app.accent": Style(color="#BD93F9"),
            "app.highlight": Style(color="#F1FA8C"),
            "app.warning": Style(color="#FF5555"),
            "app.success": Style(color="#50FA7B"),
            "app.info": Style(color="#8BE9FD"),
            "app.muted": Style(color="#6272A4"),
            
            "ui.border": Style(color="#6272A4"),
            "ui.background": Style(bgcolor="#282A36"),
            "ui.panel": Style(bgcolor="#44475A"),
            "ui.panel.title": Style(color="#F8F8F2", bold=True),
            "ui.label": Style(color="#BD93F9"),
            "ui.button": Style(color="#282A36", bgcolor="#8BE9FD"),
            "ui.button.primary": Style(color="#282A36", bgcolor="#BD93F9"),
            "ui.button.success": Style(color="#282A36", bgcolor="#50FA7B"),
            "ui.button.warning": Style(color="#282A36", bgcolor="#F1FA8C"),
            "ui.button.danger": Style(color="#F8F8F2", bgcolor="#FF5555"),
            "ui.input": Style(color="#8BE9FD", bgcolor="#44475A"),
            "ui.input.focus": Style(color="#F1FA8C", bgcolor="#6272A4"),
            "ui.selection": Style(bgcolor="#44475A"),
            
            "content.text": Style(color="#BD93F9"),  # 改为紫色字体
            "content.heading": Style(color="#BD93F9", bold=True),
            "content.subheading": Style(color="#F1FA8C", bold=True),
            "content.link": Style(color="#FF79C6", underline=True),
            "content.quote": Style(color="#F1FA8C", italic=True),
            "content.code": Style(color="#50FA7B", bgcolor="#282A36"),
            "content.highlight": Style(color="#282A36", bgcolor="#F1FA8C"),
            
            "progress.bar": Style(color="#BD93F9"),
            "progress.text": Style(color="#BD93F9"),  # 改为紫色字体
            "progress.percentage": Style(color="#BD93F9"),  # 改为紫色字体
            
            "bookshelf.title": Style(color="#BD93F9", bold=True),
            "bookshelf.author": Style(color="#BD93F9"),  # 改为紫色字体
            "bookshelf.progress": Style(color="#FF79C6"),
            "bookshelf.tag": Style(color="#8BE9FD", bgcolor="#44475A"),  # 浅蓝色字体
            "bookshelf.selected": Style(bgcolor="#6272A4"),
            
            "reader.text": Style(color="#BD93F9"),  # 改为紫色字体
            "reader.chapter": Style(color="#BD93F9", bold=True),
            "reader.page_number": Style(color="#F1FA8C"),
            "reader.bookmark": Style(color="#FF79C6"),
            "reader.search_result": Style(color="#282A36", bgcolor="#F1FA8C"),
        }
        
        # 加载Material主题
        self.themes["material"] = {
            "app.title": Style(color="#FFFFFF", bold=True),
            "app.subtitle": Style(color="#B0BEC5"),
            "app.accent": Style(color="#80CBC4"),
            "app.highlight": Style(color="#FFD600"),
            "app.warning": Style(color="#FF5252"),
            "app.success": Style(color="#69F0AE"),
            "app.info": Style(color="#40C4FF"),
            "app.muted": Style(color="#546E7A"),
            
            "ui.border": Style(color="#455A64"),
            "ui.background": Style(bgcolor="#263238"),
            "ui.panel": Style(bgcolor="#37474F"),
            "ui.panel.title": Style(color="#80CBC4", bold=True),
            "ui.label": Style(color="#FFD600"),
            "ui.button": Style(color="#263238", bgcolor="#FFD600"),
            "ui.button.primary": Style(color="#263238", bgcolor="#80CBC4"),
            "ui.button.success": Style(color="#263238", bgcolor="#69F0AE"),
            "ui.button.warning": Style(color="#263238", bgcolor="#FFD600"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF5252"),
            "ui.input": Style(color="#FFD600", bgcolor="#455A64"),
            "ui.input.focus": Style(color="#80CBC4", bgcolor="#546E7A"),
            "ui.selection": Style(bgcolor="#455A64"),
            
            "content.text": Style(color="#FFD600"),
            "content.heading": Style(color="#80CBC4", bold=True),
            "content.subheading": Style(color="#69F0AE", bold=True),
            "content.link": Style(color="#40C4FF", underline=True),
            "content.quote": Style(color="#69F0AE", italic=True),
            "content.code": Style(color="#69F0AE", bgcolor="#263238"),
            "content.highlight": Style(color="#263238", bgcolor="#FFD600"),
            
            "progress.bar": Style(color="#80CBC4"),
            "progress.text": Style(color="#B0BEC5"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#80CBC4", bold=True),
            "bookshelf.author": Style(color="#FFD600"),
            "bookshelf.progress": Style(color="#40C4FF"),
            "bookshelf.tag": Style(color="#69F0AE", bgcolor="#455A64"),
            "bookshelf.selected": Style(bgcolor="#546E7A"),
            
            "reader.text": Style(color="#FFD600"),
            "reader.chapter": Style(color="#80CBC4", bold=True),
            "reader.page_number": Style(color="#69F0AE"),
            "reader.bookmark": Style(color="#40C4FF"),
            "reader.search_result": Style(color="#263238", bgcolor="#FFD600"),
        }

        # 加载GitHub暗色主题
        self.themes["github-dark"] = {
            "app.title": Style(color="#FFFFFF", bold=True),
            "app.subtitle": Style(color="#8B949E"),
            "app.accent": Style(color="#58A6FF"),
            "app.highlight": Style(color="#D29922"),
            "app.warning": Style(color="#FF7B72"),
            "app.success": Style(color="#3FB950"),
            "app.info": Style(color="#79C0FF"),
            "app.muted": Style(color="#6E7681"),
            
            "ui.border": Style(color="#30363D"),
            "ui.background": Style(bgcolor="#0D1117"),
            "ui.panel": Style(bgcolor="#161B22"),
            "ui.panel.title": Style(color="#58A6FF", bold=True),
            "ui.label": Style(color="#D29922"),
            "ui.button": Style(color="#0D1117", bgcolor="#D29922"),
            "ui.button.primary": Style(color="#0D1117", bgcolor="#58A6FF"),
            "ui.button.success": Style(color="#0D1117", bgcolor="#3FB950"),
            "ui.button.warning": Style(color="#0D1117", bgcolor="#D29922"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#DA3633"),
            "ui.input": Style(color="#D29922", bgcolor="#161B22"),
            "ui.input.focus": Style(color="#58A6FF", bgcolor="#21262D"),
            "ui.selection": Style(bgcolor="#161B22"),
            
            "content.text": Style(color="#D29922"),
            "content.heading": Style(color="#58A6FF", bold=True),
            "content.subheading": Style(color="#3FB950", bold=True),
            "content.link": Style(color="#FF7B72", underline=True),
            "content.quote": Style(color="#3FB950", italic=True),
            "content.code": Style(color="#3FB950", bgcolor="#0D1117"),
            "content.highlight": Style(color="#0D1117", bgcolor="#D29922"),
            
            "progress.bar": Style(color="#58A6FF"),
            "progress.text": Style(color="#8B949E"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#58A6FF", bold=True),
            "bookshelf.author": Style(color="#D29922"),
            "bookshelf.progress": Style(color="#FF7B72"),
            "bookshelf.tag": Style(color="#3FB950", bgcolor="#161B22"),
            "bookshelf.selected": Style(bgcolor="#21262D"),
            
            "reader.text": Style(color="#D29922"),
            "reader.chapter": Style(color="#58A6FF", bold=True),
            "reader.page_number": Style(color="#3FB950"),
            "reader.bookmark": Style(color="#FF7B72"),
            "reader.search_result": Style(color="#0D1117", bgcolor="#D29922"),
        }

        # 加载GitHub亮色主题
        self.themes["github-light"] = {
            "app.title": Style(color="#24292F", bold=True),
            "app.subtitle": Style(color="#656D76"),
            "app.accent": Style(color="#0969DA"),
            "app.highlight": Style(color="#BF8700"),
            "app.warning": Style(color="#CF222E"),
            "app.success": Style(color="#1A7F37"),
            "app.info": Style(color="#0969DA"),
            "app.muted": Style(color="#8C959F"),
            
            "ui.border": Style(color="#D0D7DE"),
            "ui.background": Style(bgcolor="#FFFFFF"),
            "ui.panel": Style(bgcolor="#F6F8FA"),
            "ui.panel.title": Style(color="#24292F", bold=True),
            "ui.label": Style(color="#24292F"),
            "ui.button": Style(color="#24292F", bgcolor="#F6F8FA"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#0969DA"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#1A7F37"),
            "ui.button.warning": Style(color="#24292F", bgcolor="#BF8700"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#CF222E"),
            "ui.input": Style(color="#24292F", bgcolor="#FFFFFF"),
            "ui.input.focus": Style(color="#24292F", bgcolor="#F6F8FA"),
            "ui.selection": Style(bgcolor="#F6F8FA"),
            
            "content.text": Style(color="#24292F"),
            "content.heading": Style(color="#24292F", bold=True),
            "content.subheading": Style(color="#656D76", bold=True),
            "content.link": Style(color="#0969DA", underline=True),
            "content.quote": Style(color="#656D76", italic=True),
            "content.code": Style(color="#1A7F37", bgcolor="#F6F8FA"),
            "content.highlight": Style(color="#24292F", bgcolor="#FFF8C5"),
            
            "progress.bar": Style(color="#0969DA"),
            "progress.text": Style(color="#656D76"),
            "progress.percentage": Style(color="#24292F"),
            
            "bookshelf.title": Style(color="#24292F", bold=True),
            "bookshelf.author": Style(color="#656D76"),
            "bookshelf.progress": Style(color="#0969DA"),
            "bookshelf.tag": Style(color="#656D76", bgcolor="#F6F8FA"),
            "bookshelf.selected": Style(bgcolor="#F6F8FA"),
            
            "reader.text": Style(color="#24292F"),
            "reader.chapter": Style(color="#24292F", bold=True),
            "reader.page_number": Style(color="#8C959F"),
            "reader.bookmark": Style(color="#BF8700"),
            "reader.search_result": Style(color="#24292F", bgcolor="#FFF8C5"),
        }

        # 加载Solarized暗色主题
        self.themes["solarized-dark"] = {
            "app.title": Style(color="#FDF6E3", bold=True),
            "app.subtitle": Style(color="#93A1A1"),
            "app.accent": Style(color="#268BD2"),
            "app.highlight": Style(color="#B58900"),
            "app.warning": Style(color="#DC322F"),
            "app.success": Style(color="#859900"),
            "app.info": Style(color="#2AA198"),
            "app.muted": Style(color="#586E75"),
            
            "ui.border": Style(color="#586E75"),
            "ui.background": Style(bgcolor="#002B36"),
            "ui.panel": Style(bgcolor="#073642"),
            "ui.panel.title": Style(color="#268BD2", bold=True),
            "ui.label": Style(color="#B58900"),
            "ui.button": Style(color="#002B36", bgcolor="#B58900"),
            "ui.button.primary": Style(color="#002B36", bgcolor="#268BD2"),
            "ui.button.success": Style(color="#002B36", bgcolor="#859900"),
            "ui.button.warning": Style(color="#002B36", bgcolor="#B58900"),
            "ui.button.danger": Style(color="#FDF6E3", bgcolor="#DC322F"),
            "ui.input": Style(color="#B58900", bgcolor="#073642"),
            "ui.input.focus": Style(color="#268BD2", bgcolor="#586E75"),
            "ui.selection": Style(bgcolor="#073642"),
            
            "content.text": Style(color="#B58900"),
            "content.heading": Style(color="#268BD2", bold=True),
            "content.subheading": Style(color="#859900", bold=True),
            "content.link": Style(color="#2AA198", underline=True),
            "content.quote": Style(color="#859900", italic=True),
            "content.code": Style(color="#859900", bgcolor="#002B36"),
            "content.highlight": Style(color="#002B36", bgcolor="#B58900"),
            
            "progress.bar": Style(color="#268BD2"),
            "progress.text": Style(color="#93A1A1"),
            "progress.percentage": Style(color="#FDF6E3"),
            
            "bookshelf.title": Style(color="#268BD2", bold=True),
            "bookshelf.author": Style(color="#B58900"),
            "bookshelf.progress": Style(color="#2AA198"),
            "bookshelf.tag": Style(color="#859900", bgcolor="#073642"),
            "bookshelf.selected": Style(bgcolor="#586E75"),
            
            "reader.text": Style(color="#B58900"),
            "reader.chapter": Style(color="#268BD2", bold=True),
            "reader.page_number": Style(color="#859900"),
            "reader.bookmark": Style(color="#2AA198"),
            "reader.search_result": Style(color="#002B36", bgcolor="#B58900"),
        }

        # 加载Solarized亮色主题
        self.themes["solarized-light"] = {
            "app.title": Style(color="#002B36", bold=True),
            "app.subtitle": Style(color="#586E75"),
            "app.accent": Style(color="#268BD2"),
            "app.highlight": Style(color="#B58900"),
            "app.warning": Style(color="#DC322F"),
            "app.success": Style(color="#859900"),
            "app.info": Style(color="#2AA198"),
            "app.muted": Style(color="#93A1A1"),
            
            "ui.border": Style(color="#93A1A1"),
            "ui.background": Style(bgcolor="#FDF6E3"),
            "ui.panel": Style(bgcolor="#EEE8D5"),
            "ui.panel.title": Style(color="#002B36", bold=True),
            "ui.label": Style(color="#073642"),
            "ui.button": Style(color="#FDF6E3", bgcolor="#586E75"),
            "ui.button.primary": Style(color="#FDF6E3", bgcolor="#268BD2"),
            "ui.button.success": Style(color="#FDF6E3", bgcolor="#859900"),
            "ui.button.warning": Style(color="#002B36", bgcolor="#B58900"),
            "ui.button.danger": Style(color="#FDF6E3", bgcolor="#DC322F"),
            "ui.input": Style(color="#073642", bgcolor="#EEE8D5"),
            "ui.input.focus": Style(color="#073642", bgcolor="#D5D5D5"),
            "ui.selection": Style(bgcolor="#EEE8D5"),
            
            "content.text": Style(color="#073642"),
            "content.heading": Style(color="#002B36", bold=True),
            "content.subheading": Style(color="#586E75", bold=True),
            "content.link": Style(color="#268BD2", underline=True),
            "content.quote": Style(color="#586E75", italic=True),
            "content.code": Style(color="#859900", bgcolor="#EEE8D5"),
            "content.highlight": Style(color="#002B36", bgcolor="#B58900"),
            
            "progress.bar": Style(color="#268BD2"),
            "progress.text": Style(color="#586E75"),
            "progress.percentage": Style(color="#002B36"),
            
            "bookshelf.title": Style(color="#002B36", bold=True),
            "bookshelf.author": Style(color="#586E75"),
            "bookshelf.progress": Style(color="#268BD2"),
            "bookshelf.tag": Style(color="#586E75", bgcolor="#EEE8D5"),
            "bookshelf.selected": Style(bgcolor="#EEE8D5"),
            
            "reader.text": Style(color="#073642"),
            "reader.chapter": Style(color="#002B36", bold=True),
            "reader.page_number": Style(color="#93A1A1"),
            "reader.bookmark": Style(color="#B58900"),
            "reader.search_result": Style(color="#002B36", bgcolor="#B58900"),
        }

        # 加载Amethyst主题
        self.themes["amethyst"] = {
            "app.title": Style(color="#FFFFFF", bold=True),
            "app.subtitle": Style(color="#C5B4E3"),
            "app.accent": Style(color="#9A77CF"),
            "app.highlight": Style(color="#FFD700"),
            "app.warning": Style(color="#FF6B6B"),
            "app.success": Style(color="#6BCB77"),
            "app.info": Style(color="#4FC3F7"),
            "app.muted": Style(color="#6D5D8F"),
            
            "ui.border": Style(color="#6D5D8F"),
            "ui.background": Style(bgcolor="#2D1B69"),
            "ui.panel": Style(bgcolor="#3A2A7A"),
            "ui.panel.title": Style(color="#9A77CF", bold=True),
            "ui.label": Style(color="#FFD700"),
            "ui.button": Style(color="#2D1B69", bgcolor="#FFD700"),
            "ui.button.primary": Style(color="#2D1B69", bgcolor="#9A77CF"),
            "ui.button.success": Style(color="#2D1B69", bgcolor="#6BCB77"),
            "ui.button.warning": Style(color="#2D1B69", bgcolor="#FFD700"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF6B6B"),
            "ui.input": Style(color="#FFD700", bgcolor="#3A2A7A"),
            "ui.input.focus": Style(color="#9A77CF", bgcolor="#4A3A8A"),
            "ui.selection": Style(bgcolor="#3A2A7A"),
            
            "content.text": Style(color="#FFD700"),
            "content.heading": Style(color="#9A77CF", bold=True),
            "content.subheading": Style(color="#6BCB77", bold=True),
            "content.link": Style(color="#4FC3F7", underline=True),
            "content.quote": Style(color="#6BCB77", italic=True),
            "content.code": Style(color="#6BCB77", bgcolor="#2D1B69"),
            "content.highlight": Style(color="#2D1B69", bgcolor="#FFD700"),
            
            "progress.bar": Style(color="#9A77CF"),
            "progress.text": Style(color="#C5B4E3"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#9A77CF", bold=True),
            "bookshelf.author": Style(color="#FFD700"),
            "bookshelf.progress": Style(color="#4FC3F7"),
            "bookshelf.tag": Style(color="#6BCB77", bgcolor="#3A2A7A"),
            "bookshelf.selected": Style(bgcolor="#4A3A8A"),
            
            "reader.text": Style(color="#FFD700"),
            "reader.chapter": Style(color="#9A77CF", bold=True),
            "reader.page_number": Style(color="#6BCB77"),
            "reader.bookmark": Style(color="#4FC3F7"),
            "reader.search_result": Style(color="#2D1B69", bgcolor="#FFD700"),
        }

        # 加载Forest Green主题
        self.themes["forest-green"] = {
            "app.title": Style(color="#FFFFFF", bold=True),
            "app.subtitle": Style(color="#A5D6A7"),
            "app.accent": Style(color="#4CAF50"),
            "app.highlight": Style(color="#FFEB3B"),
            "app.warning": Style(color="#F44336"),
            "app.success": Style(color="#66BB6A"),
            "app.info": Style(color="#29B6F6"),
            "app.muted": Style(color="#2E7D32"),
            
            "ui.border": Style(color="#2E7D32"),
            "ui.background": Style(bgcolor="#1B5E20"),
            "ui.panel": Style(bgcolor="#2E7D32"),
            "ui.panel.title": Style(color="#4CAF50", bold=True),
            "ui.label": Style(color="#FFEB3B"),
            "ui.button": Style(color="#1B5E20", bgcolor="#FFEB3B"),
            "ui.button.primary": Style(color="#1B5E20", bgcolor="#4CAF50"),
            "ui.button.success": Style(color="#1B5E20", bgcolor="#66BB6A"),
            "ui.button.warning": Style(color="#1B5E20", bgcolor="#FFEB3B"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#F44336"),
            "ui.input": Style(color="#FFEB3B", bgcolor="#2E7D32"),
            "ui.input.focus": Style(color="#4CAF50", bgcolor="#388E3C"),
            "ui.selection": Style(bgcolor="#2E7D32"),
            
            "content.text": Style(color="#FFEB3B"),
            "content.heading": Style(color="#4CAF50", bold=True),
            "content.subheading": Style(color="#66BB6A", bold=True),
            "content.link": Style(color="#29B6F6", underline=True),
            "content.quote": Style(color="#66BB6A", italic=True),
            "content.code": Style(color="#66BB6A", bgcolor="#1B5E20"),
            "content.highlight": Style(color="#1B5E20", bgcolor="#FFEB3B"),
            
            "progress.bar": Style(color="#4CAF50"),
            "progress.text": Style(color="#A5D6A7"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#4CAF50", bold=True),
            "bookshelf.author": Style(color="#FFEB3B"),
            "bookshelf.progress": Style(color="#29B6F6"),
            "bookshelf.tag": Style(color="#66BB6A", bgcolor="#2E7D32"),
            "bookshelf.selected": Style(bgcolor="#388E3C"),
            
            "reader.text": Style(color="#FFEB3B"),
            "reader.chapter": Style(color="#4CAF50", bold=True),
            "reader.page_number": Style(color="#66BB6A"),
            "reader.bookmark": Style(color="#29B6F6"),
            "reader.search_result": Style(color="#1B5E20", bgcolor="#FFEB3B"),
        }

        # 加载Crimson主题
        self.themes["crimson"] = {
            "app.title": Style(color="#FFFFFF", bold=True),
            "app.subtitle": Style(color="#FFCCCB"),
            "app.accent": Style(color="#DC143C"),
            "app.highlight": Style(color="#FFD700"),
            "app.warning": Style(color="#FF4500"),
            "app.success": Style(color="#32CD32"),
            "app.info": Style(color="#1E90FF"),
            "app.muted": Style(color="#8B0000"),
            
            "ui.border": Style(color="#8B0000"),
            "ui.background": Style(bgcolor="#800000"),
            "ui.panel": Style(bgcolor="#8B0000"),
            "ui.panel.title": Style(color="#DC143C", bold=True),
            "ui.label": Style(color="#FFD700"),
            "ui.button": Style(color="#800000", bgcolor="#FFD700"),
            "ui.button.primary": Style(color="#800000", bgcolor="#DC143C"),
            "ui.button.success": Style(color="#800000", bgcolor="#32CD32"),
            "ui.button.warning": Style(color="#800000", bgcolor="#FFD700"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF4500"),
            "ui.input": Style(color="#FFD700", bgcolor="#8B0000"),
            "ui.input.focus": Style(color="#DC143C", bgcolor="#A52A2A"),
            "ui.selection": Style(bgcolor="#8B0000"),
            
            "content.text": Style(color="#FFD700"),
            "content.heading": Style(color="#DC143C", bold=True),
            "content.subheading": Style(color="#32CD32", bold=True),
            "content.link": Style(color="#1E90FF", underline=True),
            "content.quote": Style(color="#32CD32", italic=True),
            "content.code": Style(color="#32CD32", bgcolor="#800000"),
            "content.highlight": Style(color="#800000", bgcolor="#FFD700"),
            
            "progress.bar": Style(color="#DC143C"),
            "progress.text": Style(color="#FFCCCB"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#DC143C", bold=True),
            "bookshelf.author": Style(color="#FFD700"),
            "bookshelf.progress": Style(color="#1E90FF"),
            "bookshelf.tag": Style(color="#32CD32", bgcolor="#8B0000"),
            "bookshelf.selected": Style(bgcolor="#A52A2A"),
            
            "reader.text": Style(color="#FFD700"),
            "reader.chapter": Style(color="#DC143C", bold=True),
            "reader.page_number": Style(color="#32CD32"),
            "reader.bookmark": Style(color="#1E90FF"),
            "reader.search_result": Style(color="#800000", bgcolor="#FFD700"),
        }

        # 加载Slate主题
        self.themes["slate"] = {
            "app.title": Style(color="#FFFFFF", bold=True),
            "app.subtitle": Style(color="#B0B0B0"),
            "app.accent": Style(color="#708090"),
            "app.highlight": Style(color="#FFA500"),
            "app.warning": Style(color="#FF6347"),
            "app.success": Style(color="#3CB371"),
            "app.info": Style(color="#4682B4"),
            "app.muted": Style(color="#556B2F"),
            
            "ui.border": Style(color="#556B2F"),
            "ui.background": Style(bgcolor="#2F4F4F"),
            "ui.panel": Style(bgcolor="#36454F"),
            "ui.panel.title": Style(color="#708090", bold=True),
            "ui.label": Style(color="#FFA500"),
            "ui.button": Style(color="#2F4F4F", bgcolor="#FFA500"),
            "ui.button.primary": Style(color="#2F4F4F", bgcolor="#708090"),
            "ui.button.success": Style(color="#2F4F4F", bgcolor="#3CB371"),
            "ui.button.warning": Style(color="#2F4F4F", bgcolor="#FFA500"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF6347"),
            "ui.input": Style(color="#FFA500", bgcolor="#36454F"),
            "ui.input.focus": Style(color="#708090", bgcolor="#556B2F"),
            "ui.selection": Style(bgcolor="#36454F"),
            
            "content.text": Style(color="#FFA500"),
            "content.heading": Style(color="#708090", bold=True),
            "content.subheading": Style(color="#3CB371", bold=True),
            "content.link": Style(color="#4682B4", underline=True),
            "content.quote": Style(color="#3CB371", italic=True),
            "content.code": Style(color="#3CB371", bgcolor="#2F4F4F"),
            "content.highlight": Style(color="#2F4F4F", bgcolor="#FFA500"),
            
            "progress.bar": Style(color="#708090"),
            "progress.text": Style(color="#B0B0B0"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#708090", bold=True),
            "bookshelf.author": Style(color="#FFA500"),
            "bookshelf.progress": Style(color="#4682B4"),
            "bookshelf.tag": Style(color="#3CB371", bgcolor="#36454F"),
            "bookshelf.selected": Style(bgcolor="#556B2F"),
            
            "reader.text": Style(color="#FFA500"),
            "reader.chapter": Style(color="#708090", bold=True),
            "reader.page_number": Style(color="#3CB371"),
            "reader.bookmark": Style(color="#4682B4"),
            "reader.search_result": Style(color="#2F4F4F", bgcolor="#FFA500"),
        }

        # 加载透明暗色主题
        self.themes["transparent-dark"] = {
            "app.title": Style(color="#8BC1FF", bold=True),
            "app.subtitle": Style(color="#A6C6FF"),
            "app.accent": Style(color="#5D9CEC"),
            "app.highlight": Style(color="#FAC51C"),
            "app.warning": Style(color="#DA4453"),
            "app.success": Style(color="#37BC9B"),
            "app.info": Style(color="#3BAFDA"),
            "app.muted": Style(color="#656D78"),
            
            "ui.border": Style(color="#434A54", dim=True),
            "ui.background": Style(bgcolor=None),
            "ui.panel": Style(bgcolor="#2F2F2F", dim=True),
            "ui.panel.title": Style(color="#8BC1FF", bold=True),
            "ui.label": Style(color="#A6C6FF"),
            "ui.button": Style(color="#A6C6FF", bgcolor="#434A54", dim=True),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#5D9CEC", dim=True),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#37BC9B", dim=True),
            "ui.button.warning": Style(color="#000000", bgcolor="#F6BB42", dim=True),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#DA4453", dim=True),
            "ui.input": Style(color="#A6C6FF", bgcolor="#2F2F2F", dim=True),
            "ui.input.focus": Style(color="#8BC1FF", bgcolor="#434A54", dim=True),
            "ui.selection": Style(bgcolor="#2F2F2F", dim=True),
            
            "content.text": Style(color="#A6C6FF"),
            "content.heading": Style(color="#8BC1FF", bold=True),
            "content.subheading": Style(color="#A6C6FF", bold=True),
            "content.link": Style(color="#5D9CEC", underline=True),
            "content.quote": Style(color="#A6C6FF", italic=True),
            "content.code": Style(color="#37BC9B", bgcolor="#2F2F2F", dim=True),
            "content.highlight": Style(color="#000000", bgcolor="#FAC51C"),
            
            "progress.bar": Style(color="#5D9CEC", dim=True),
            "progress.text": Style(color="#A6C6FF"),
            "progress.percentage": Style(color="#8BC1FF"),
            
            "bookshelf.title": Style(color="#8BC1FF", bold=True),
            "bookshelf.author": Style(color="#A6C6FF"),
            "bookshelf.progress": Style(color="#5D9CEC"),
            "bookshelf.tag": Style(color="#A6C6FF", bgcolor="#2F2F2F", dim=True),
            "bookshelf.selected": Style(bgcolor="#2F2F2F", dim=True),
            
            "reader.text": Style(color="#A6C6FF"),
            "reader.chapter": Style(color="#8BC1FF", bold=True),
            "reader.page_number": Style(color="#656D78"),
            "reader.bookmark": Style(color="#FAC51C"),
            "reader.search_result": Style(color="#000000", bgcolor="#FAC51C"),
        }

        # 加载透明亮色主题
        self.themes["transparent-light"] = {
            "app.title": Style(color="#000000", bold=True),
            "app.subtitle": Style(color="#666666"),
            "app.accent": Style(color="#4A89DC"),
            "app.highlight": Style(color="#F6BB42"),
            "app.warning": Style(color="#DA4453"),
            "app.success": Style(color="#37BC9B"),
            "app.info": Style(color="#3BAFDA"),
            "app.muted": Style(color="#AAB2BD"),
            
            "ui.border": Style(color="#E6E9ED", dim=True),
            "ui.background": Style(bgcolor="white", dim=True),
            "ui.panel": Style(bgcolor="#F5F7FA", dim=True),
            "ui.panel.title": Style(color="#000000", bold=True),
            "ui.label": Style(color="#434A54"),
            "ui.button": Style(color="#000000", bgcolor="#E6E9ED", dim=True),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#4A89DC", dim=True),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#37BC9B", dim=True),
            "ui.button.warning": Style(color="#000000", bgcolor="#F6BB42", dim=True),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#DA4453", dim=True),
            "ui.input": Style(color="#000000", bgcolor="#F5F7FA", dim=True),
            "ui.input.focus": Style(color="#000000", bgcolor="#E6E9ED", dim=True),
            "ui.selection": Style(bgcolor="#F5F7FA", dim=True),
            
            "content.text": Style(color="#434A54"),
            "content.heading": Style(color="#000000", bold=True),
            "content.subheading": Style(color="#666666", bold=True),
            "content.link": Style(color="#4A89DC", underline=True),
            "content.quote": Style(color="#666666", italic=True),
            "content.code": Style(color="#37BC9B", bgcolor="#F5F7FA", dim=True),
            "content.highlight": Style(color="#000000", bgcolor="#F6BB42"),
            
            "progress.bar": Style(color="#4A89DC", dim=True),
            "progress.text": Style(color="#666666"),
            "progress.percentage": Style(color="#000000"),
            
            "bookshelf.title": Style(color="#000000", bold=True),
            "bookshelf.author": Style(color="#666666"),
            "bookshelf.progress": Style(color="#4A89DC"),
            "bookshelf.tag": Style(color="#666666", bgcolor="#F5F7FA", dim=True),
            "bookshelf.selected": Style(bgcolor="#F5F7FA", dim=True),
            
            "reader.text": Style(color="#434A54"),
            "reader.chapter": Style(color="#000000", bold=True),
            "reader.page_number": Style(color="#AAB2BD"),
            "reader.bookmark": Style(color="#F6BB42"),
            "reader.search_result": Style(color="#000000", bgcolor="#F6BB42"),
        }

        # 加载Paper White主题（纯白背景）
        self.themes["paper-white"] = {
            "app.title": Style(color="#000000", bold=True),
            "app.subtitle": Style(color="#555555"),
            "app.accent": Style(color="#0066CC"),
            "app.highlight": Style(color="#FF9900"),
            "app.warning": Style(color="#CC0000"),
            "app.success": Style(color="#009900"),
            "app.info": Style(color="#0099CC"),
            "app.muted": Style(color="#888888"),
            
            "ui.border": Style(color="#DDDDDD"),
            "ui.background": Style(bgcolor="#FFFFFF"),
            "ui.panel": Style(bgcolor="#F8F8F8"),
            "ui.panel.title": Style(color="#000000", bold=True),
            "ui.label": Style(color="#333333"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#666666"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#0066CC"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#009900"),
            "ui.button.warning": Style(color="#000000", bgcolor="#FF9900"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#CC0000"),
            "ui.input": Style(color="#000000", bgcolor="#F0F0F0"),
            "ui.input.focus": Style(color="#000000", bgcolor="#E8E8E8"),
            "ui.selection": Style(bgcolor="#E8E8E8"),
            
            "content.text": Style(color="#222222"),
            "content.heading": Style(color="#000000", bold=True),
            "content.subheading": Style(color="#444444", bold=True),
            "content.link": Style(color="#0066CC", underline=True),
            "content.quote": Style(color="#555555", italic=True),
            "content.code": Style(color="#009900", bgcolor="#F5F5F5"),
            "content.highlight": Style(color="#000000", bgcolor="#FFF8DC"),
            
            "progress.bar": Style(color="#0066CC"),
            "progress.text": Style(color="#666666"),
            "progress.percentage": Style(color="#000000"),
            
            "bookshelf.title": Style(color="#000000", bold=True),
            "bookshelf.author": Style(color="#555555"),
            "bookshelf.progress": Style(color="#0066CC"),
            "bookshelf.tag": Style(color="#666666", bgcolor="#F0F0F0"),
            "bookshelf.selected": Style(bgcolor="#F0F0F0"),
            
            "reader.text": Style(color="#222222"),
            "reader.chapter": Style(color="#000000", bold=True),
            "reader.page_number": Style(color="#888888"),
            "reader.bookmark": Style(color="#FF9900"),
            "reader.search_result": Style(color="#000000", bgcolor="#FFEBCD"),
        }

        # 加载Cream主题（奶油色背景）
        self.themes["cream"] = {
            "app.title": Style(color="#2C1810", bold=True),
            "app.subtitle": Style(color="#5D4037"),
            "app.accent": Style(color="#7B1FA2"),
            "app.highlight": Style(color="#FF9800"),
            "app.warning": Style(color="#D32F2F"),
            "app.success": Style(color="#388E3C"),
            "app.info": Style(color="#0288D1"),
            "app.muted": Style(color="#795548"),
            
            "ui.border": Style(color="#BCAAA4"),
            "ui.background": Style(bgcolor="#FFF8E1"),
            "ui.panel": Style(bgcolor="#FFECB3"),
            "ui.panel.title": Style(color="#2C1810", bold=True),
            "ui.label": Style(color="#4E342E"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#8D6E63"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#7B1FA2"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#388E3C"),
            "ui.button.warning": Style(color="#2C1810", bgcolor="#FF9800"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#D32F2F"),
            "ui.input": Style(color="#2C1810", bgcolor="#FFE082"),
            "ui.input.focus": Style(color="#2C1810", bgcolor="#FFD54F"),
            "ui.selection": Style(bgcolor="#FFE082"),
            
            "content.text": Style(color="#3E2723"),
            "content.heading": Style(color="#2C1810", bold=True),
            "content.subheading": Style(color="#5D4037", bold=True),
            "content.link": Style(color="#7B1FA2", underline=True),
            "content.quote": Style(color="#5D4037", italic=True),
            "content.code": Style(color="#388E3C", bgcolor="#FFECB3"),
            "content.highlight": Style(color="#2C1810", bgcolor="#FFE57F"),
            
            "progress.bar": Style(color="#7B1FA2"),
            "progress.text": Style(color="#5D4037"),
            "progress.percentage": Style(color="#2C1810"),
            
            "bookshelf.title": Style(color="#2C1810", bold=True),
            "bookshelf.author": Style(color="#5D4037"),
            "bookshelf.progress": Style(color="#7B1FA2"),
            "bookshelf.tag": Style(color="#5D4037", bgcolor="#FFECB3"),
            "bookshelf.selected": Style(bgcolor="#FFECB3"),
            
            "reader.text": Style(color="#3E2723"),
            "reader.chapter": Style(color="#2C1810", bold=True),
            "reader.page_number": Style(color="#795548"),
            "reader.bookmark": Style(color="#FF9800"),
            "reader.search_result": Style(color="#2C1810", bgcolor="#FFE57F"),
        }

        # 加载Sky Blue主题（天蓝色背景）
        self.themes["sky-blue"] = {
            "app.title": Style(color="#0D47A1", bold=True),
            "app.subtitle": Style(color="#1565C0"),
            "app.accent": Style(color="#FF6D00"),
            "app.highlight": Style(color="#FFD600"),
            "app.warning": Style(color="#D50000"),
            "app.success": Style(color="#00C853"),
            "app.info": Style(color="#0091EA"),
            "app.muted": Style(color="#546E7A"),
            
            "ui.border": Style(color="#90CAF9"),
            "ui.background": Style(bgcolor="#E3F2FD"),
            "ui.panel": Style(bgcolor="#BBDEFB"),
            "ui.panel.title": Style(color="#0D47A1", bold=True),
            "ui.label": Style(color="#1565C0"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#64B5F6"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#FF6D00"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#00C853"),
            "ui.button.warning": Style(color="#0D47A1", bgcolor="#FFD600"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#D50000"),
            "ui.input": Style(color="#0D47A1", bgcolor="#E1F5FE"),
            "ui.input.focus": Style(color="#0D47A1", bgcolor="#B3E5FC"),
            "ui.selection": Style(bgcolor="#E1F5FE"),
            
            "content.text": Style(color="#0D47A1"),
            "content.heading": Style(color="#0D47A1", bold=True),
            "content.subheading": Style(color="#1565C0", bold=True),
            "content.link": Style(color="#FF6D00", underline=True),
            "content.quote": Style(color="#1565C0", italic=True),
            "content.code": Style(color="#00C853", bgcolor="#BBDEFB"),
            "content.highlight": Style(color="#0D47A1", bgcolor="#FFECB3"),
            
            "progress.bar": Style(color="#FF6D00"),
            "progress.text": Style(color="#1565C0"),
            "progress.percentage": Style(color="#0D47A1"),
            
            "bookshelf.title": Style(color="#0D47A1", bold=True),
            "bookshelf.author": Style(color="#1565C0"),
            "bookshelf.progress": Style(color="#FF6D00"),
            "bookshelf.tag": Style(color="#1565C0", bgcolor="#BBDEFB"),
            "bookshelf.selected": Style(bgcolor="#BBDEFB"),
            
            "reader.text": Style(color="#0D47A1"),
            "reader.chapter": Style(color="#0D47A1", bold=True),
            "reader.page_number": Style(color="#546E7A"),
            "reader.bookmark": Style(color="#FFD600"),
            "reader.search_result": Style(color="#0D47A1", bgcolor="#FFECB3"),
        }

        # 加载Mint Green主题（薄荷绿背景）
        self.themes["mint-green"] = {
            "app.title": Style(color="#1B5E20", bold=True),
            "app.subtitle": Style(color="#2E7D32"),
            "app.accent": Style(color="#E65100"),
            "app.highlight": Style(color="#FFAB00"),
            "app.warning": Style(color="#C62828"),
            "app.success": Style(color="#2E7D32"),
            "app.info": Style(color="#0277BD"),
            "app.muted": Style(color="#4CAF50"),
            
            "ui.border": Style(color="#A5D6A7"),
            "ui.background": Style(bgcolor="#E8F5E9"),
            "ui.panel": Style(bgcolor="#C8E6C9"),
            "ui.panel.title": Style(color="#1B5E20", bold=True),
            "ui.label": Style(color="#2E7D32"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#66BB6A"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#E65100"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#2E7D32"),
            "ui.button.warning": Style(color="#1B5E20", bgcolor="#FFAB00"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#C62828"),
            "ui.input": Style(color="#1B5E20", bgcolor="#F1F8E9"),
            "ui.input.focus": Style(color="#1B5E20", bgcolor="#DCEDC8"),
            "ui.selection": Style(bgcolor="#F1F8E9"),
            
            "content.text": Style(color="#1B5E20"),
            "content.heading": Style(color="#1B5E20", bold=True),
            "content.subheading": Style(color="#2E7D32", bold=True),
            "content.link": Style(color="#E65100", underline=True),
            "content.quote": Style(color="#2E7D32", italic=True),
            "content.code": Style(color="#2E7D32", bgcolor="#C8E6C9"),
            "content.highlight": Style(color="#1B5E20", bgcolor="#FFF9C4"),
            
            "progress.bar": Style(color="#E65100"),
            "progress.text": Style(color="#2E7D32"),
            "progress.percentage": Style(color="#1B5E20"),
            
            "bookshelf.title": Style(color="#1B5E20", bold=True),
            "bookshelf.author": Style(color="#2E7D32"),
            "bookshelf.progress": Style(color="#E65100"),
            "bookshelf.tag": Style(color="#2E7D32", bgcolor="#C8E6C9"),
            "bookshelf.selected": Style(bgcolor="#C8E6C9"),
            
            "reader.text": Style(color="#1B5E20"),
            "reader.chapter": Style(color="#1B5E20", bold=True),
            "reader.page_number": Style(color="#4CAF50"),
            "reader.bookmark": Style(color="#FFAB00"),
            "reader.search_result": Style(color="#1B5E20", bgcolor="#FFF9C4"),
        }

        # 加载Lavender主题（薰衣草紫背景）
        self.themes["lavender"] = {
            "app.title": Style(color="#4A148C", bold=True),
            "app.subtitle": Style(color="#6A1B9A"),
            "app.accent": Style(color="#FF6F00"),
            "app.highlight": Style(color="#FFD740"),
            "app.warning": Style(color="#D32F2F"),
            "app.success": Style(color="#388E3C"),
            "app.info": Style(color="#0277BD"),
            "app.muted": Style(color="#7B1FA2"),
            
            "ui.border": Style(color="#CE93D8"),
            "ui.background": Style(bgcolor="#F3E5F5"),
            "ui.panel": Style(bgcolor="#E1BEE7"),
            "ui.panel.title": Style(color="#4A148C", bold=True),
            "ui.label": Style(color="#6A1B9A"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#BA68C8"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#FF6F00"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#388E3C"),
            "ui.button.warning": Style(color="#4A148C", bgcolor="#FFD740"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#D32F2F"),
            "ui.input": Style(color="#4A148C", bgcolor="#EDE7F6"),
            "ui.input.focus": Style(color="#4A148C", bgcolor="#D1C4E9"),
            "ui.selection": Style(bgcolor="#EDE7F6"),
            
            "content.text": Style(color="#4A148C"),
            "content.heading": Style(color="#4A148C", bold=True),
            "content.subheading": Style(color="#6A1B9A", bold=True),
            "content.link": Style(color="#FF6F00", underline=True),
            "content.quote": Style(color="#6A1B9A", italic=True),
            "content.code": Style(color="#388E3C", bgcolor="#E1BEE7"),
            "content.highlight": Style(color="#4A148C", bgcolor="#FFF59D"),
            
            "progress.bar": Style(color="#FF6F00"),
            "progress.text": Style(color="#6A1B9A"),
            "progress.percentage": Style(color="#4A148C"),
            
            "bookshelf.title": Style(color="#4A148C", bold=True),
            "bookshelf.author": Style(color="#6A1B9A"),
            "bookshelf.progress": Style(color="#FF6F00"),
            "bookshelf.tag": Style(color="#6A1B9A", bgcolor="#E1BEE7"),
            "bookshelf.selected": Style(bgcolor="#E1BEE7"),
            
            "reader.text": Style(color="#4A148C"),
            "reader.chapter": Style(color="#4A148C", bold=True),
            "reader.page_number": Style(color="#7B1FA2"),
            "reader.bookmark": Style(color="#FFD740"),
            "reader.search_result": Style(color="#4A148C", bgcolor="#FFF59D"),
        }
        
        # 额外增加色彩丰富主题
        self.themes["neon-pop"] = {
            "app.title": Style(color="#39FF14", bold=True),
            "app.subtitle": Style(color="#FF6EC7"),
            "app.accent": Style(color="#00FFFF"),
            "app.highlight": Style(color="#FFD300"),
            "app.warning": Style(color="#FF3131"),
            "app.success": Style(color="#39FF14"),
            "app.info": Style(color="#7DF9FF"),
            "app.muted": Style(color="#808080"),

            "ui.border": Style(color="#FF6EC7"),
            "ui.background": Style(bgcolor="#0F0F0F"),
            "ui.panel": Style(bgcolor="#1A1A1A"),
            "ui.panel.title": Style(color="#39FF14", bold=True),
            "ui.label": Style(color="#E0FFE0"),
            "ui.button": Style(color="#0F0F0F", bgcolor="#39FF14"),
            "ui.button.primary": Style(color="#0F0F0F", bgcolor="#00FFFF"),
            "ui.button.success": Style(color="#0F0F0F", bgcolor="#39FF14"),
            "ui.button.warning": Style(color="#0F0F0F", bgcolor="#FFD300"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF3131"),
            "ui.input": Style(color="#E0FFE0", bgcolor="#222222"),
            "ui.input.focus": Style(color="#39FF14", bgcolor="#2B2B2B"),
            "ui.selection": Style(bgcolor="#222222"),

            "content.text": Style(color="#E0FFE0"),
            "content.heading": Style(color="#39FF14", bold=True),
            "content.subheading": Style(color="#FFD300", bold=True),
            "content.link": Style(color="#00FFFF", underline=True),
            "content.quote": Style(color="#FF6EC7", italic=True),
            "content.code": Style(color="#39FF14", bgcolor="#1A1A1A"),
            "content.highlight": Style(color="#0F0F0F", bgcolor="#FFD300"),

            "progress.bar": Style(color="#00FFFF"),
            "progress.text": Style(color="#E0FFE0"),
            "progress.percentage": Style(color="#39FF14"),

            "bookshelf.title": Style(color="#39FF14", bold=True),
            "bookshelf.author": Style(color="#FF6EC7"),
            "bookshelf.progress": Style(color="#00FFFF"),
            "bookshelf.tag": Style(color="#FFD300", bgcolor="#222222"),
            "bookshelf.selected": Style(bgcolor="#2B2B2B"),

            "reader.text": Style(color="#E0FFE0"),
            "reader.chapter": Style(color="#39FF14", bold=True),
            "reader.page_number": Style(color="#FFD300"),
            "reader.bookmark": Style(color="#00FFFF"),
            "reader.search_result": Style(color="#0F0F0F", bgcolor="#FFD300"),
        }

        self.themes["sunset"] = {
            "app.title": Style(color="#FF6E40", bold=True),
            "app.subtitle": Style(color="#FAD6A5"),
            "app.accent": Style(color="#FF9E80"),
            "app.highlight": Style(color="#FFC13B"),
            "app.warning": Style(color="#FF4E00"),
            "app.success": Style(color="#78C091"),
            "app.info": Style(color="#FF9E80"),
            "app.muted": Style(color="#A36F4E"),

            "ui.border": Style(color="#A36F4E"),
            "ui.background": Style(bgcolor="#2B1D1A"),
            "ui.panel": Style(bgcolor="#3A2622"),
            "ui.panel.title": Style(color="#FFC13B", bold=True),
            "ui.label": Style(color="#FAD6A5"),
            "ui.button": Style(color="#2B1D1A", bgcolor="#FF6E40"),
            "ui.button.primary": Style(color="#2B1D1A", bgcolor="#FFC13B"),
            "ui.button.success": Style(color="#2B1D1A", bgcolor="#78C091"),
            "ui.button.warning": Style(color="#2B1D1A", bgcolor="#FF9E80"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF4E00"),
            "ui.input": Style(color="#FAD6A5", bgcolor="#3A2622"),
            "ui.input.focus": Style(color="#FFC13B", bgcolor="#4A302B"),
            "ui.selection": Style(bgcolor="#3A2622"),

            "content.text": Style(color="#FAD6A5"),
            "content.heading": Style(color="#FFC13B", bold=True),
            "content.subheading": Style(color="#FF9E80", bold=True),
            "content.link": Style(color="#FF6E40", underline=True),
            "content.quote": Style(color="#78C091", italic=True),
            "content.code": Style(color="#78C091", bgcolor="#2B1D1A"),
            "content.highlight": Style(color="#2B1D1A", bgcolor="#FFC13B"),

            "progress.bar": Style(color="#FF9E80"),
            "progress.text": Style(color="#FAD6A5"),
            "progress.percentage": Style(color="#FFC13B"),

            "bookshelf.title": Style(color="#FFC13B", bold=True),
            "bookshelf.author": Style(color="#FAD6A5"),
            "bookshelf.progress": Style(color="#FF6E40"),
            "bookshelf.tag": Style(color="#78C091", bgcolor="#3A2622"),
            "bookshelf.selected": Style(bgcolor="#4A302B"),

            "reader.text": Style(color="#FAD6A5"),
            "reader.chapter": Style(color="#FFC13B", bold=True),
            "reader.page_number": Style(color="#FF9E80"),
            "reader.bookmark": Style(color="#FF6E40"),
            "reader.search_result": Style(color="#2B1D1A", bgcolor="#FFC13B"),
        }

        self.themes["ocean"] = {
            "app.title": Style(color="#00B3D8", bold=True),
            "app.subtitle": Style(color="#80D7E6"),
            "app.accent": Style(color="#00D1FF"),
            "app.highlight": Style(color="#FFDD57"),
            "app.warning": Style(color="#FF6B6B"),
            "app.success": Style(color="#2ECC71"),
            "app.info": Style(color="#00D1FF"),
            "app.muted": Style(color="#4CA3AF"),

            "ui.border": Style(color="#4CA3AF"),
            "ui.background": Style(bgcolor="#062C43"),
            "ui.panel": Style(bgcolor="#0B3A53"),
            "ui.panel.title": Style(color="#00D1FF", bold=True),
            "ui.label": Style(color="#80D7E6"),
            "ui.button": Style(color="#062C43", bgcolor="#00B3D8"),
            "ui.button.primary": Style(color="#062C43", bgcolor="#00D1FF"),
            "ui.button.success": Style(color="#062C43", bgcolor="#2ECC71"),
            "ui.button.warning": Style(color="#062C43", bgcolor="#FFDD57"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF6B6B"),
            "ui.input": Style(color="#80D7E6", bgcolor="#0B3A53"),
            "ui.input.focus": Style(color="#00D1FF", bgcolor="#104761"),
            "ui.selection": Style(bgcolor="#0B3A53"),

            "content.text": Style(color="#80D7E6"),
            "content.heading": Style(color="#00D1FF", bold=True),
            "content.subheading": Style(color="#2ECC71", bold=True),
            "content.link": Style(color="#00B3D8", underline=True),
            "content.quote": Style(color="#2ECC71", italic=True),
            "content.code": Style(color="#2ECC71", bgcolor="#062C43"),
            "content.highlight": Style(color="#062C43", bgcolor="#FFDD57"),

            "progress.bar": Style(color="#00D1FF"),
            "progress.text": Style(color="#80D7E6"),
            "progress.percentage": Style(color="#00D1FF"),

            "bookshelf.title": Style(color="#00D1FF", bold=True),
            "bookshelf.author": Style(color="#80D7E6"),
            "bookshelf.progress": Style(color="#00B3D8"),
            "bookshelf.tag": Style(color="#2ECC71", bgcolor="#0B3A53"),
            "bookshelf.selected": Style(bgcolor="#104761"),

            "reader.text": Style(color="#80D7E6"),
            "reader.chapter": Style(color="#00D1FF", bold=True),
            "reader.page_number": Style(color="#2ECC71"),
            "reader.bookmark": Style(color="#FFDD57"),
            "reader.search_result": Style(color="#062C43", bgcolor="#FFDD57"),
        }

        self.themes["pastel-dream"] = {
            "app.title": Style(color="#6C5B7B", bold=True),
            "app.subtitle": Style(color="#C06C84"),
            "app.accent": Style(color="#F8B195"),
            "app.highlight": Style(color="#F6C1C1"),
            "app.warning": Style(color="#E84A5F"),
            "app.success": Style(color="#99B898"),
            "app.info": Style(color="#F8B195"),
            "app.muted": Style(color="#A8A7A7"),

            "ui.border": Style(color="#A8A7A7"),
            "ui.background": Style(bgcolor="#FDF1ED"),
            "ui.panel": Style(bgcolor="#FEE9E1"),
            "ui.panel.title": Style(color="#6C5B7B", bold=True),
            "ui.label": Style(color="#6C5B7B"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#C06C84"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#F8B195"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#99B898"),
            "ui.button.warning": Style(color="#6C5B7B", bgcolor="#F6C1C1"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#E84A5F"),
            "ui.input": Style(color="#6C5B7B", bgcolor="#FEE9E1"),
            "ui.input.focus": Style(color="#6C5B7B", bgcolor="#FADCD7"),
            "ui.selection": Style(bgcolor="#FEE9E1"),

            "content.text": Style(color="#6C5B7B"),
            "content.heading": Style(color="#6C5B7B", bold=True),
            "content.subheading": Style(color="#C06C84", bold=True),
            "content.link": Style(color="#F8B195", underline=True),
            "content.quote": Style(color="#99B898", italic=True),
            "content.code": Style(color="#99B898", bgcolor="#FDF1ED"),
            "content.highlight": Style(color="#6C5B7B", bgcolor="#F6C1C1"),

            "progress.bar": Style(color="#F8B195"),
            "progress.text": Style(color="#6C5B7B"),
            "progress.percentage": Style(color="#6C5B7B"),

            "bookshelf.title": Style(color="#6C5B7B", bold=True),
            "bookshelf.author": Style(color="#C06C84"),
            "bookshelf.progress": Style(color="#F8B195"),
            "bookshelf.tag": Style(color="#99B898", bgcolor="#FEE9E1"),
            "bookshelf.selected": Style(bgcolor="#FADCD7"),

            "reader.text": Style(color="#6C5B7B"),
            "reader.chapter": Style(color="#6C5B7B", bold=True),
            "reader.page_number": Style(color="#C06C84"),
            "reader.bookmark": Style(color="#F8B195"),
            "reader.search_result": Style(color="#6C5B7B", bgcolor="#F6C1C1"),
        }

        self.themes["cyberpunk"] = {
            "app.title": Style(color="#00FFFF", bold=True),
            "app.subtitle": Style(color="#FF00FF"),
            "app.accent": Style(color="#FCEE09"),
            "app.highlight": Style(color="#FCEE09"),
            "app.warning": Style(color="#FF003C"),
            "app.success": Style(color="#00FF9F"),
            "app.info": Style(color="#00FFFF"),
            "app.muted": Style(color="#A0A0A0"),

            "ui.border": Style(color="#FF00FF"),
            "ui.background": Style(bgcolor="#0A0F1E"),
            "ui.panel": Style(bgcolor="#12172A"),
            "ui.panel.title": Style(color="#00FFFF", bold=True),
            "ui.label": Style(color="#FCEE09"),
            "ui.button": Style(color="#0A0F1E", bgcolor="#00FFFF"),
            "ui.button.primary": Style(color="#0A0F1E", bgcolor="#FCEE09"),
            "ui.button.success": Style(color="#0A0F1E", bgcolor="#00FF9F"),
            "ui.button.warning": Style(color="#0A0F1E", bgcolor="#FF00FF"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF003C"),
            "ui.input": Style(color="#FCEE09", bgcolor="#12172A"),
            "ui.input.focus": Style(color="#00FFFF", bgcolor="#1B2240"),
            "ui.selection": Style(bgcolor="#12172A"),

            "content.text": Style(color="#D8F6FF"),
            "content.heading": Style(color="#00FFFF", bold=True),
            "content.subheading": Style(color="#FCEE09", bold=True),
            "content.link": Style(color="#FF00FF", underline=True),
            "content.quote": Style(color="#00FF9F", italic=True),
            "content.code": Style(color="#00FF9F", bgcolor="#0A0F1E"),
            "content.highlight": Style(color="#0A0F1E", bgcolor="#FCEE09"),

            "progress.bar": Style(color="#00FFFF"),
            "progress.text": Style(color="#FCEE09"),
            "progress.percentage": Style(color="#00FFFF"),

            "bookshelf.title": Style(color="#00FFFF", bold=True),
            "bookshelf.author": Style(color="#FCEE09"),
            "bookshelf.progress": Style(color="#FF00FF"),
            "bookshelf.tag": Style(color="#00FF9F", bgcolor="#12172A"),
            "bookshelf.selected": Style(bgcolor="#1B2240"),

            "reader.text": Style(color="#D8F6FF"),
            "reader.chapter": Style(color="#00FFFF", bold=True),
            "reader.page_number": Style(color="#FCEE09"),
            "reader.bookmark": Style(color="#FF00FF"),
            "reader.search_result": Style(color="#0A0F1E", bgcolor="#FCEE09"),
        }

        # 颜色鲜艳主题 1：Rainbow Bright（深色）
        self.themes["rainbow-bright"] = {
            "app.title": Style(color="#FF3B3B", bold=True),
            "app.subtitle": Style(color="#FFD93B"),
            "app.accent": Style(color="#3B82F6"),
            "app.highlight": Style(color="#F59E0B"),
            "app.warning": Style(color="#F97316"),
            "app.success": Style(color="#22C55E"),
            "app.info": Style(color="#06B6D4"),
            "app.muted": Style(color="#9CA3AF"),

            "ui.border": Style(color="#9333EA"),
            "ui.background": Style(bgcolor="#141414"),
            "ui.panel": Style(bgcolor="#1F1F1F"),
            "ui.panel.title": Style(color="#FF3B3B", bold=True),
            "ui.label": Style(color="#FFD93B"),
            "ui.button": Style(color="#141414", bgcolor="#3B82F6"),
            "ui.button.primary": Style(color="#141414", bgcolor="#FF3B3B"),
            "ui.button.success": Style(color="#141414", bgcolor="#22C55E"),
            "ui.button.warning": Style(color="#141414", bgcolor="#F59E0B"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#F97316"),
            "ui.input": Style(color="#FFD93B", bgcolor="#1F1F1F"),
            "ui.input.focus": Style(color="#3B82F6", bgcolor="#262626"),
            "ui.selection": Style(bgcolor="#1F1F1F"),

            "content.text": Style(color="#E5E7EB"),
            "content.heading": Style(color="#FF3B3B", bold=True),
            "content.subheading": Style(color="#FFD93B", bold=True),
            "content.link": Style(color="#3B82F6", underline=True),
            "content.quote": Style(color="#22C55E", italic=True),
            "content.code": Style(color="#22C55E", bgcolor="#141414"),
            "content.highlight": Style(color="#141414", bgcolor="#FFD93B"),

            "progress.bar": Style(color="#3B82F6"),
            "progress.text": Style(color="#FFD93B"),
            "progress.percentage": Style(color="#FF3B3B"),

            "bookshelf.title": Style(color="#FF3B3B", bold=True),
            "bookshelf.author": Style(color="#9CA3AF"),
            "bookshelf.progress": Style(color="#3B82F6"),
            "bookshelf.tag": Style(color="#22C55E", bgcolor="#1F1F1F"),
            "bookshelf.selected": Style(bgcolor="#262626"),

            "reader.text": Style(color="#E5E7EB"),
            "reader.chapter": Style(color="#FF3B3B", bold=True),
            "reader.page_number": Style(color="#FFD93B"),
            "reader.bookmark": Style(color="#3B82F6"),
            "reader.search_result": Style(color="#141414", bgcolor="#FFD93B"),
        }

        # 颜色鲜艳主题 2：Tropical（深色）
        self.themes["tropical"] = {
            "app.title": Style(color="#00C897", bold=True),
            "app.subtitle": Style(color="#7AE582"),
            "app.accent": Style(color="#FF6F5E"),
            "app.highlight": Style(color="#FFC857"),
            "app.warning": Style(color="#F94144"),
            "app.success": Style(color="#43AA8B"),
            "app.info": Style(color="#577590"),
            "app.muted": Style(color="#8D99AE"),

            "ui.border": Style(color="#577590"),
            "ui.background": Style(bgcolor="#0F2E2E"),
            "ui.panel": Style(bgcolor="#16403C"),
            "ui.panel.title": Style(color="#00C897", bold=True),
            "ui.label": Style(color="#7AE582"),
            "ui.button": Style(color="#0F2E2E", bgcolor="#FF6F5E"),
            "ui.button.primary": Style(color="#0F2E2E", bgcolor="#FFC857"),
            "ui.button.success": Style(color="#0F2E2E", bgcolor="#43AA8B"),
            "ui.button.warning": Style(color="#0F2E2E", bgcolor="#F94144"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#F94144"),
            "ui.input": Style(color="#7AE582", bgcolor="#16403C"),
            "ui.input.focus": Style(color="#00C897", bgcolor="#1C524C"),
            "ui.selection": Style(bgcolor="#16403C"),

            "content.text": Style(color="#D8F3DC"),
            "content.heading": Style(color="#00C897", bold=True),
            "content.subheading": Style(color="#FFC857", bold=True),
            "content.link": Style(color="#FF6F5E", underline=True),
            "content.quote": Style(color="#43AA8B", italic=True),
            "content.code": Style(color="#43AA8B", bgcolor="#0F2E2E"),
            "content.highlight": Style(color="#0F2E2E", bgcolor="#FFC857"),

            "progress.bar": Style(color="#FF6F5E"),
            "progress.text": Style(color="#7AE582"),
            "progress.percentage": Style(color="#00C897"),

            "bookshelf.title": Style(color="#00C897", bold=True),
            "bookshelf.author": Style(color="#8D99AE"),
            "bookshelf.progress": Style(color="#FF6F5E"),
            "bookshelf.tag": Style(color="#43AA8B", bgcolor="#16403C"),
            "bookshelf.selected": Style(bgcolor="#1C524C"),

            "reader.text": Style(color="#D8F3DC"),
            "reader.chapter": Style(color="#00C897", bold=True),
            "reader.page_number": Style(color="#FFC857"),
            "reader.bookmark": Style(color="#FF6F5E"),
            "reader.search_result": Style(color="#0F2E2E", bgcolor="#FFC857"),
        }

        # 颜色鲜艳主题 3：Candy Pop（亮色）
        self.themes["candy-pop"] = {
            "app.title": Style(color="#E91E63", bold=True),
            "app.subtitle": Style(color="#9C27B0"),
            "app.accent": Style(color="#3F51B5"),
            "app.highlight": Style(color="#FFC107"),
            "app.warning": Style(color="#FF5722"),
            "app.success": Style(color="#4CAF50"),
            "app.info": Style(color="#00BCD4"),
            "app.muted": Style(color="#616161"),

            "ui.border": Style(color="#BDBDBD"),
            "ui.background": Style(bgcolor="#FFF0F6"),
            "ui.panel": Style(bgcolor="#FFE4EF"),
            "ui.panel.title": Style(color="#E91E63", bold=True),
            "ui.label": Style(color="#9C27B0"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#E91E63"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#3F51B5"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#4CAF50"),
            "ui.button.warning": Style(color="#9C27B0", bgcolor="#FFC107"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF5722"),
            "ui.input": Style(color="#9C27B0", bgcolor="#FFE4EF"),
            "ui.input.focus": Style(color="#9C27B0", bgcolor="#FFD6E6"),
            "ui.selection": Style(bgcolor="#FFE4EF"),

            "content.text": Style(color="#6A1B9A"),
            "content.heading": Style(color="#E91E63", bold=True),
            "content.subheading": Style(color="#9C27B0", bold=True),
            "content.link": Style(color="#3F51B5", underline=True),
            "content.quote": Style(color="#4CAF50", italic=True),
            "content.code": Style(color="#4CAF50", bgcolor="#FFE4EF"),
            "content.highlight": Style(color="#6A1B9A", bgcolor="#FFF8E1"),

            "progress.bar": Style(color="#3F51B5"),
            "progress.text": Style(color="#9C27B0"),
            "progress.percentage": Style(color="#E91E63"),

            "bookshelf.title": Style(color="#E91E63", bold=True),
            "bookshelf.author": Style(color="#616161"),
            "bookshelf.progress": Style(color="#3F51B5"),
            "bookshelf.tag": Style(color="#4CAF50", bgcolor="#FFE4EF"),
            "bookshelf.selected": Style(bgcolor="#FFD6E6"),

            "reader.text": Style(color="#6A1B9A"),
            "reader.chapter": Style(color="#E91E63", bold=True),
            "reader.page_number": Style(color="#3F51B5"),
            "reader.bookmark": Style(color="#FFC107"),
            "reader.search_result": Style(color="#6A1B9A", bgcolor="#FFF8E1"),
        }

        # 颜色鲜艳主题 4：Flamingo（亮色）
        self.themes["flamingo"] = {
            "app.title": Style(color="#F06292", bold=True),
            "app.subtitle": Style(color="#CE93D8"),
            "app.accent": Style(color="#26C6DA"),
            "app.highlight": Style(color="#FFCA28"),
            "app.warning": Style(color="#EF5350"),
            "app.success": Style(color="#66BB6A"),
            "app.info": Style(color="#29B6F6"),
            "app.muted": Style(color="#8D6E63"),

            "ui.border": Style(color="#D7CCC8"),
            "ui.background": Style(bgcolor="#FFF3F5"),
            "ui.panel": Style(bgcolor="#FFE9EE"),
            "ui.panel.title": Style(color="#F06292", bold=True),
            "ui.label": Style(color="#CE93D8"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#F06292"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#26C6DA"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#66BB6A"),
            "ui.button.warning": Style(color="#8D6E63", bgcolor="#FFCA28"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#EF5350"),
            "ui.input": Style(color="#8D6E63", bgcolor="#FFE9EE"),
            "ui.input.focus": Style(color="#8D6E63", bgcolor="#FFDDE3"),
            "ui.selection": Style(bgcolor="#FFE9EE"),

            "content.text": Style(color="#6D4C41"),
            "content.heading": Style(color="#F06292", bold=True),
            "content.subheading": Style(color="#CE93D8", bold=True),
            "content.link": Style(color="#26C6DA", underline=True),
            "content.quote": Style(color="#66BB6A", italic=True),
            "content.code": Style(color="#66BB6A", bgcolor="#FFE9EE"),
            "content.highlight": Style(color="#6D4C41", bgcolor="#FFF8E1"),

            "progress.bar": Style(color="#26C6DA"),
            "progress.text": Style(color="#CE93D8"),
            "progress.percentage": Style(color="#F06292"),

            "bookshelf.title": Style(color="#F06292", bold=True),
            "bookshelf.author": Style(color="#8D6E63"),
            "bookshelf.progress": Style(color="#26C6DA"),
            "bookshelf.tag": Style(color="#66BB6A", bgcolor="#FFE9EE"),
            "bookshelf.selected": Style(bgcolor="#FFDDE3"),

            "reader.text": Style(color="#6D4C41"),
            "reader.chapter": Style(color="#F06292", bold=True),
            "reader.page_number": Style(color="#26C6DA"),
            "reader.bookmark": Style(color="#FFCA28"),
            "reader.search_result": Style(color="#6D4C41", bgcolor="#FFF8E1"),
        }

        # 颜色鲜艳主题 5：Lime Punch（深色）
        self.themes["lime-punch"] = {
            "app.title": Style(color="#B8FF3B", bold=True),
            "app.subtitle": Style(color="#D7FF6B"),
            "app.accent": Style(color="#00D8FF"),
            "app.highlight": Style(color="#FFB703"),
            "app.warning": Style(color="#FB5607"),
            "app.success": Style(color="#80ED99"),
            "app.info": Style(color="#48CAE4"),
            "app.muted": Style(color="#94A3B8"),

            "ui.border": Style(color="#10B981"),
            "ui.background": Style(bgcolor="#0D0F0A"),
            "ui.panel": Style(bgcolor="#141913"),
            "ui.panel.title": Style(color="#B8FF3B", bold=True),
            "ui.label": Style(color="#D7FF6B"),
            "ui.button": Style(color="#0D0F0A", bgcolor="#B8FF3B"),
            "ui.button.primary": Style(color="#0D0F0A", bgcolor="#00D8FF"),
            "ui.button.success": Style(color="#0D0F0A", bgcolor="#80ED99"),
            "ui.button.warning": Style(color="#0D0F0A", bgcolor="#FFB703"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FB5607"),
            "ui.input": Style(color="#D7FF6B", bgcolor="#141913"),
            "ui.input.focus": Style(color="#00D8FF", bgcolor="#1A2018"),
            "ui.selection": Style(bgcolor="#141913"),

            "content.text": Style(color="#E2E8F0"),
            "content.heading": Style(color="#B8FF3B", bold=True),
            "content.subheading": Style(color="#00D8FF", bold=True),
            "content.link": Style(color="#00D8FF", underline=True),
            "content.quote": Style(color="#80ED99", italic=True),
            "content.code": Style(color="#80ED99", bgcolor="#0D0F0A"),
            "content.highlight": Style(color="#0D0F0A", bgcolor="#FFB703"),

            "progress.bar": Style(color="#00D8FF"),
            "progress.text": Style(color="#D7FF6B"),
            "progress.percentage": Style(color="#B8FF3B"),

            "bookshelf.title": Style(color="#B8FF3B", bold=True),
            "bookshelf.author": Style(color="#94A3B8"),
            "bookshelf.progress": Style(color="#00D8FF"),
            "bookshelf.tag": Style(color="#80ED99", bgcolor="#141913"),
            "bookshelf.selected": Style(bgcolor="#1A2018"),

            "reader.text": Style(color="#E2E8F0"),
            "reader.chapter": Style(color="#B8FF3B", bold=True),
            "reader.page_number": Style(color="#00D8FF"),
            "reader.bookmark": Style(color="#FFB703"),
            "reader.search_result": Style(color="#0D0F0A", bgcolor="#FFB703"),
        }

        # 颜色鲜艳主题 6：Electric Blue（深色）
        self.themes["electric-blue"] = {
            "app.title": Style(color="#00A8E8", bold=True),
            "app.subtitle": Style(color="#90E0EF"),
            "app.accent": Style(color="#0077B6"),
            "app.highlight": Style(color="#F9C74F"),
            "app.warning": Style(color="#F94144"),
            "app.success": Style(color="#43AA8B"),
            "app.info": Style(color="#00A8E8"),
            "app.muted": Style(color="#6C757D"),

            "ui.border": Style(color="#0077B6"),
            "ui.background": Style(bgcolor="#0B132B"),
            "ui.panel": Style(bgcolor="#1C2541"),
            "ui.panel.title": Style(color="#00A8E8", bold=True),
            "ui.label": Style(color="#90E0EF"),
            "ui.button": Style(color="#0B132B", bgcolor="#00A8E8"),
            "ui.button.primary": Style(color="#0B132B", bgcolor="#F9C74F"),
            "ui.button.success": Style(color="#0B132B", bgcolor="#43AA8B"),
            "ui.button.warning": Style(color="#0B132B", bgcolor="#F94144"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#F94144"),
            "ui.input": Style(color="#90E0EF", bgcolor="#1C2541"),
            "ui.input.focus": Style(color="#00A8E8", bgcolor="#3A506B"),
            "ui.selection": Style(bgcolor="#1C2541"),

            "content.text": Style(color="#E0FBFC"),
            "content.heading": Style(color="#00A8E8", bold=True),
            "content.subheading": Style(color="#F9C74F", bold=True),
            "content.link": Style(color="#0077B6", underline=True),
            "content.quote": Style(color="#43AA8B", italic=True),
            "content.code": Style(color="#43AA8B", bgcolor="#0B132B"),
            "content.highlight": Style(color="#0B132B", bgcolor="#F9C74F"),

            "progress.bar": Style(color="#00A8E8"),
            "progress.text": Style(color="#90E0EF"),
            "progress.percentage": Style(color="#F9C74F"),

            "bookshelf.title": Style(color="#00A8E8", bold=True),
            "bookshelf.author": Style(color="#6C757D"),
            "bookshelf.progress": Style(color="#0077B6"),
            "bookshelf.tag": Style(color="#43AA8B", bgcolor="#1C2541"),
            "bookshelf.selected": Style(bgcolor="#3A506B"),

            "reader.text": Style(color="#E0FBFC"),
            "reader.chapter": Style(color="#00A8E8", bold=True),
            "reader.page_number": Style(color="#F9C74F"),
            "reader.bookmark": Style(color="#0077B6"),
            "reader.search_result": Style(color="#0B132B", bgcolor="#F9C74F"),
        }

        # 颜色鲜艳主题 7：Magenta Blast（深色）
        self.themes["magenta-blast"] = {
            "app.title": Style(color="#FF2D95", bold=True),
            "app.subtitle": Style(color="#FF7AC8"),
            "app.accent": Style(color="#8A2BE2"),
            "app.highlight": Style(color="#FFD166"),
            "app.warning": Style(color="#EF476F"),
            "app.success": Style(color="#06D6A0"),
            "app.info": Style(color="#118AB2"),
            "app.muted": Style(color="#A0AEC0"),

            "ui.border": Style(color="#8A2BE2"),
            "ui.background": Style(bgcolor="#1A1423"),
            "ui.panel": Style(bgcolor="#2A1E35"),
            "ui.panel.title": Style(color="#FF2D95", bold=True),
            "ui.label": Style(color="#FF7AC8"),
            "ui.button": Style(color="#1A1423", bgcolor="#FF2D95"),
            "ui.button.primary": Style(color="#1A1423", bgcolor="#FFD166"),
            "ui.button.success": Style(color="#1A1423", bgcolor="#06D6A0"),
            "ui.button.warning": Style(color="#1A1423", bgcolor="#EF476F"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#EF476F"),
            "ui.input": Style(color="#FF7AC8", bgcolor="#2A1E35"),
            "ui.input.focus": Style(color="#8A2BE2", bgcolor="#352545"),
            "ui.selection": Style(bgcolor="#2A1E35"),

            "content.text": Style(color="#F1EAF1"),
            "content.heading": Style(color="#FF2D95", bold=True),
            "content.subheading": Style(color="#FFD166", bold=True),
            "content.link": Style(color="#8A2BE2", underline=True),
            "content.quote": Style(color="#06D6A0", italic=True),
            "content.code": Style(color="#06D6A0", bgcolor="#1A1423"),
            "content.highlight": Style(color="#1A1423", bgcolor="#FFD166"),

            "progress.bar": Style(color="#8A2BE2"),
            "progress.text": Style(color="#FF7AC8"),
            "progress.percentage": Style(color="#FFD166"),

            "bookshelf.title": Style(color="#FF2D95", bold=True),
            "bookshelf.author": Style(color="#A0AEC0"),
            "bookshelf.progress": Style(color="#8A2BE2"),
            "bookshelf.tag": Style(color="#06D6A0", bgcolor="#2A1E35"),
            "bookshelf.selected": Style(bgcolor="#352545"),

            "reader.text": Style(color="#F1EAF1"),
            "reader.chapter": Style(color="#FF2D95", bold=True),
            "reader.page_number": Style(color="#FFD166"),
            "reader.bookmark": Style(color="#8A2BE2"),
            "reader.search_result": Style(color="#1A1423", bgcolor="#FFD166"),
        }

        # 颜色鲜艳主题 8：Citrus Burst（亮色）
        self.themes["citrus-burst"] = {
            "app.title": Style(color="#F59E0B", bold=True),
            "app.subtitle": Style(color="#FB923C"),
            "app.accent": Style(color="#10B981"),
            "app.highlight": Style(color="#FCD34D"),
            "app.warning": Style(color="#EF4444"),
            "app.success": Style(color="#22C55E"),
            "app.info": Style(color="#06B6D4"),
            "app.muted": Style(color="#6B7280"),

            "ui.border": Style(color="#E5E7EB"),
            "ui.background": Style(bgcolor="#FFF7ED"),
            "ui.panel": Style(bgcolor="#FFEDD5"),
            "ui.panel.title": Style(color="#F59E0B", bold=True),
            "ui.label": Style(color="#FB923C"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#F59E0B"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#10B981"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#22C55E"),
            "ui.button.warning": Style(color="#6B7280", bgcolor="#FCD34D"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#EF4444"),
            "ui.input": Style(color="#6B7280", bgcolor="#FFEDD5"),
            "ui.input.focus": Style(color="#6B7280", bgcolor="#FFE4D6"),
            "ui.selection": Style(bgcolor="#FFEDD5"),

            "content.text": Style(color="#7C2D12"),
            "content.heading": Style(color="#F59E0B", bold=True),
            "content.subheading": Style(color="#10B981", bold=True),
            "content.link": Style(color="#10B981", underline=True),
            "content.quote": Style(color="#22C55E", italic=True),
            "content.code": Style(color="#22C55E", bgcolor="#FFEDD5"),
            "content.highlight": Style(color="#7C2D12", bgcolor="#FEF3C7"),

            "progress.bar": Style(color="#10B981"),
            "progress.text": Style(color="#FB923C"),
            "progress.percentage": Style(color="#F59E0B"),

            "bookshelf.title": Style(color="#F59E0B", bold=True),
            "bookshelf.author": Style(color="#6B7280"),
            "bookshelf.progress": Style(color="#10B981"),
            "bookshelf.tag": Style(color="#22C55E", bgcolor="#FFEDD5"),
            "bookshelf.selected": Style(bgcolor="#FFE4D6"),

            "reader.text": Style(color="#7C2D12"),
            "reader.chapter": Style(color="#F59E0B", bold=True),
            "reader.page_number": Style(color="#10B981"),
            "reader.bookmark": Style(color="#FCD34D"),
            "reader.search_result": Style(color="#7C2D12", bgcolor="#FEF3C7"),
        }

        # 颜色鲜艳主题 9：Galaxy（深色）
        self.themes["galaxy"] = {
            "app.title": Style(color="#7DD3FC", bold=True),
            "app.subtitle": Style(color="#C4B5FD"),
            "app.accent": Style(color="#22D3EE"),
            "app.highlight": Style(color="#FDE68A"),
            "app.warning": Style(color="#F87171"),
            "app.success": Style(color="#34D399"),
            "app.info": Style(color="#60A5FA"),
            "app.muted": Style(color="#9CA3AF"),

            "ui.border": Style(color="#6D28D9"),
            "ui.background": Style(bgcolor="#0B1026"),
            "ui.panel": Style(bgcolor="#161A35"),
            "ui.panel.title": Style(color="#7DD3FC", bold=True),
            "ui.label": Style(color="#C4B5FD"),
            "ui.button": Style(color="#0B1026", bgcolor="#6D28D9"),
            "ui.button.primary": Style(color="#0B1026", bgcolor="#22D3EE"),
            "ui.button.success": Style(color="#0B1026", bgcolor="#34D399"),
            "ui.button.warning": Style(color="#0B1026", bgcolor="#FDE68A"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#F87171"),
            "ui.input": Style(color="#C4B5FD", bgcolor="#161A35"),
            "ui.input.focus": Style(color="#22D3EE", bgcolor="#1E2449"),
            "ui.selection": Style(bgcolor="#161A35"),

            "content.text": Style(color="#E5E7EB"),
            "content.heading": Style(color="#7DD3FC", bold=True),
            "content.subheading": Style(color="#22D3EE", bold=True),
            "content.link": Style(color="#6D28D9", underline=True),
            "content.quote": Style(color="#34D399", italic=True),
            "content.code": Style(color="#34D399", bgcolor="#0B1026"),
            "content.highlight": Style(color="#0B1026", bgcolor="#FDE68A"),

            "progress.bar": Style(color="#22D3EE"),
            "progress.text": Style(color="#C4B5FD"),
            "progress.percentage": Style(color="#FDE68A"),

            "bookshelf.title": Style(color="#7DD3FC", bold=True),
            "bookshelf.author": Style(color="#9CA3AF"),
            "bookshelf.progress": Style(color="#6D28D9"),
            "bookshelf.tag": Style(color="#34D399", bgcolor="#161A35"),
            "bookshelf.selected": Style(bgcolor="#1E2449"),

            "reader.text": Style(color="#E5E7EB"),
            "reader.chapter": Style(color="#7DD3FC", bold=True),
            "reader.page_number": Style(color="#22D3EE"),
            "reader.bookmark": Style(color="#FDE68A"),
            "reader.search_result": Style(color="#0B1026", bgcolor="#FDE68A"),
        }

        # 颜色鲜艳主题 10：Fiesta（深色）
        self.themes["fiesta"] = {
            "app.title": Style(color="#FF006E", bold=True),
            "app.subtitle": Style(color="#FB5607"),
            "app.accent": Style(color="#3A86FF"),
            "app.highlight": Style(color="#FFBE0B"),
            "app.warning": Style(color="#E63946"),
            "app.success": Style(color="#06D6A0"),
            "app.info": Style(color="#118AB2"),
            "app.muted": Style(color="#A8A9AD"),

            "ui.border": Style(color="#3A86FF"),
            "ui.background": Style(bgcolor="#121212"),
            "ui.panel": Style(bgcolor="#1E1E1E"),
            "ui.panel.title": Style(color="#FF006E", bold=True),
            "ui.label": Style(color="#FB5607"),
            "ui.button": Style(color="#121212", bgcolor="#FF006E"),
            "ui.button.primary": Style(color="#121212", bgcolor="#3A86FF"),
            "ui.button.success": Style(color="#121212", bgcolor="#06D6A0"),
            "ui.button.warning": Style(color="#121212", bgcolor="#FFBE0B"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#E63946"),
            "ui.input": Style(color="#FB5607", bgcolor="#1E1E1E"),
            "ui.input.focus": Style(color="#3A86FF", bgcolor="#272727"),
            "ui.selection": Style(bgcolor="#1E1E1E"),

            "content.text": Style(color="#EAEAEA"),
            "content.heading": Style(color="#FF006E", bold=True),
            "content.subheading": Style(color="#3A86FF", bold=True),
            "content.link": Style(color="#3A86FF", underline=True),
            "content.quote": Style(color="#06D6A0", italic=True),
            "content.code": Style(color="#06D6A0", bgcolor="#121212"),
            "content.highlight": Style(color="#121212", bgcolor="#FFBE0B"),

            "progress.bar": Style(color="#3A86FF"),
            "progress.text": Style(color="#FB5607"),
            "progress.percentage": Style(color="#FFBE0B"),

            "bookshelf.title": Style(color="#FF006E", bold=True),
            "bookshelf.author": Style(color="#A8A9AD"),
            "bookshelf.progress": Style(color="#3A86FF"),
            "bookshelf.tag": Style(color="#06D6A0", bgcolor="#1E1E1E"),
            "bookshelf.selected": Style(bgcolor="#272727"),

            "reader.text": Style(color="#EAEAEA"),
            "reader.chapter": Style(color="#FF006E", bold=True),
            "reader.page_number": Style(color="#3A86FF"),
            "reader.bookmark": Style(color="#FFBE0B"),
            "reader.search_result": Style(color="#121212", bgcolor="#FFBE0B"),
        }

        # 玻璃感/透明主题：玻璃蓝（暗）
        self.themes["glass-cyan"] = {
            "app.title": Style(color="#8BE9FD", bold=True),
            "app.subtitle": Style(color="#AEEBFF"),
            "app.accent": Style(color="#00D1FF"),
            "app.highlight": Style(color="#FADB14"),
            "app.warning": Style(color="#FF4D4F"),
            "app.success": Style(color="#36CFC9"),
            "app.info": Style(color="#40A9FF"),
            "app.muted": Style(color="#8C8C8C"),
            
            "ui.border": Style(color="#69C0FF", dim=True),
            "ui.background": Style(bgcolor="black", dim=True),
            "ui.panel": Style(bgcolor=None),
            "ui.panel.title": Style(color="#8BE9FD", bold=True),
            "ui.label": Style(color="#E6F7FF"),
            "ui.button": Style(color="#0A0A0A", bgcolor="#40A9FF", dim=True),
            "ui.button.primary": Style(color="#0A0A0A", bgcolor="#00D1FF", dim=True),
            "ui.button.success": Style(color="#0A0A0A", bgcolor="#36CFC9", dim=True),
            "ui.button.warning": Style(color="#0A0A0A", bgcolor="#FADB14", dim=True),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF4D4F", dim=True),
            "ui.input": Style(color="#E6F7FF", bgcolor="#1f1f1f", dim=True),
            "ui.input.focus": Style(color="#8BE9FD", bgcolor="#2a2a2a", dim=True),
            "ui.selection": Style(bgcolor=None),

            "content.text": Style(color="#E6F7FF"),
            "content.heading": Style(color="#8BE9FD", bold=True),
            "content.subheading": Style(color="#00D1FF", bold=True),
            "content.link": Style(color="#40A9FF", underline=True),
            "content.quote": Style(color="#36CFC9", italic=True),
            "content.code": Style(color="#36CFC9"),
            "content.highlight": Style(color="#0A0A0A", bgcolor="#FADB14"),

            "progress.bar": Style(color="#40A9FF", dim=True),
            "progress.text": Style(color="#AEEBFF"),
            "progress.percentage": Style(color="#8BE9FD"),

            "bookshelf.title": Style(color="#8BE9FD", bold=True),
            "bookshelf.author": Style(color="#AEEBFF"),
            "bookshelf.progress": Style(color="#40A9FF"),
            "bookshelf.tag": Style(color="#AEEBFF", bgcolor="#1f1f1f", dim=True),
            "bookshelf.selected": Style(bgcolor="#1f1f1f", dim=True),

            "reader.text": Style(color="#E6F7FF"),
            "reader.chapter": Style(color="#8BE9FD", bold=True),
            "reader.page_number": Style(color="#69C0FF"),
            "reader.bookmark": Style(color="#FADB14"),
            "reader.search_result": Style(color="#0A0A0A", bgcolor="#FADB14"),
        }

        # 玻璃感/透明主题：玻璃玫红（暗）
        self.themes["glass-rose"] = {
            "app.title": Style(color="#FF6EC7", bold=True),
            "app.subtitle": Style(color="#FFC0E6"),
            "app.accent": Style(color="#FF2D95"),
            "app.highlight": Style(color="#FFD166"),
            "app.warning": Style(color="#EF476F"),
            "app.success": Style(color="#06D6A0"),
            "app.info": Style(color="#7AD7F0"),
            "app.muted": Style(color="#A0A0A0"),
            
            "ui.border": Style(color="#FF6EC7", dim=True),
            "ui.background": Style(bgcolor=None),
            "ui.panel": Style(bgcolor=None),
            "ui.panel.title": Style(color="#FF6EC7", bold=True),
            "ui.label": Style(color="#FFE6F5"),
            "ui.button": Style(color="#141414", bgcolor="#FF2D95", dim=True),
            "ui.button.primary": Style(color="#141414", bgcolor="#FFD166", dim=True),
            "ui.button.success": Style(color="#141414", bgcolor="#06D6A0", dim=True),
            "ui.button.warning": Style(color="#141414", bgcolor="#FF6EC7", dim=True),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#EF476F", dim=True),
            "ui.input": Style(color="#FFE6F5", bgcolor="#232323", dim=True),
            "ui.input.focus": Style(color="#FF6EC7", bgcolor="#2d2d2d", dim=True),
            "ui.selection": Style(bgcolor=None),

            "content.text": Style(color="#FFE6F5"),
            "content.heading": Style(color="#FF6EC7", bold=True),
            "content.subheading": Style(color="#FFD166", bold=True),
            "content.link": Style(color="#FF2D95", underline=True),
            "content.quote": Style(color="#06D6A0", italic=True),
            "content.code": Style(color="#06D6A0"),
            "content.highlight": Style(color="#141414", bgcolor="#FFD166"),

            "progress.bar": Style(color="#FF6EC7", dim=True),
            "progress.text": Style(color="#FFC0E6"),
            "progress.percentage": Style(color="#FFD166"),

            "bookshelf.title": Style(color="#FF6EC7", bold=True),
            "bookshelf.author": Style(color="#FFC0E6"),
            "bookshelf.progress": Style(color="#FF2D95"),
            "bookshelf.tag": Style(color="#06D6A0", bgcolor="#232323", dim=True),
            "bookshelf.selected": Style(bgcolor="#2d2d2d", dim=True),

            "reader.text": Style(color="#FFE6F5"),
            "reader.chapter": Style(color="#FF6EC7", bold=True),
            "reader.page_number": Style(color="#FFD166"),
            "reader.bookmark": Style(color="#FF2D95"),
            "reader.search_result": Style(color="#141414", bgcolor="#FFD166"),
        }

        # 玻璃感/透明主题：玻璃琥珀（亮）
        self.themes["glass-amber"] = {
            "app.title": Style(color="#000000", bold=True),
            "app.subtitle": Style(color="#7A7A7A"),
            "app.accent": Style(color="#FFB200"),
            "app.highlight": Style(color="#FFDD57"),
            "app.warning": Style(color="#E63946"),
            "app.success": Style(color="#2BC48A"),
            "app.info": Style(color="#4098FF"),
            "app.muted": Style(color="#A0A0A0"),
            
            "ui.border": Style(color="#E6E9ED", dim=True),
            "ui.background": Style(bgcolor=None),
            "ui.panel": Style(bgcolor=None),
            "ui.panel.title": Style(color="#000000", bold=True),
            "ui.label": Style(color="#4D4D4D"),
            "ui.button": Style(color="#000000", bgcolor="#FFDD57", dim=True),
            "ui.button.primary": Style(color="#000000", bgcolor="#FFB200", dim=True),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#2BC48A", dim=True),
            "ui.button.warning": Style(color="#000000", bgcolor="#FFD666", dim=True),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#E63946", dim=True),
            "ui.input": Style(color="#000000", bgcolor="#FAFAFA", dim=True),
            "ui.input.focus": Style(color="#000000", bgcolor="#EDEFF3", dim=True),
            "ui.selection": Style(bgcolor=None),

            "content.text": Style(color="#333333"),
            "content.heading": Style(color="#000000", bold=True),
            "content.subheading": Style(color="#7A7A7A", bold=True),
            "content.link": Style(color="#FFB200", underline=True),
            "content.quote": Style(color="#2BC48A", italic=True),
            "content.code": Style(color="#2BC48A"),
            "content.highlight": Style(color="#000000", bgcolor="#FFF7CC"),

            "progress.bar": Style(color="#FFB200", dim=True),
            "progress.text": Style(color="#7A7A7A"),
            "progress.percentage": Style(color="#000000"),

            "bookshelf.title": Style(color="#000000", bold=True),
            "bookshelf.author": Style(color="#7A7A7A"),
            "bookshelf.progress": Style(color="#FFB200"),
            "bookshelf.tag": Style(color="#7A7A7A", bgcolor="#FAFAFA", dim=True),
            "bookshelf.selected": Style(bgcolor="#FAFAFA", dim=True),

            "reader.text": Style(color="#333333"),
            "reader.chapter": Style(color="#000000", bold=True),
            "reader.page_number": Style(color="#A0A0A0"),
            "reader.bookmark": Style(color="#FFDD57"),
            "reader.search_result": Style(color="#000000", bgcolor="#FFF7CC"),
        }

        # 玻璃感/透明主题：玻璃青柠（亮）
        self.themes["glass-lime"] = {
            "app.title": Style(color="#0F5132", bold=True),
            "app.subtitle": Style(color="#2E7D32"),
            "app.accent": Style(color="#82CD47"),
            "app.highlight": Style(color="#C3F73A"),
            "app.warning": Style(color="#D9480F"),
            "app.success": Style(color="#2BC48A"),
            "app.info": Style(color="#2EA6FF"),
            "app.muted": Style(color="#6E7F74"),
            
            "ui.border": Style(color="#CFE8CF", dim=True),
            "ui.background": Style(bgcolor=None),
            "ui.panel": Style(bgcolor=None),
            "ui.panel.title": Style(color="#0F5132", bold=True),
            "ui.label": Style(color="#1B5E20"),
            "ui.button": Style(color="#0F5132", bgcolor="#C3F73A", dim=True),
            "ui.button.primary": Style(color="#0F5132", bgcolor="#82CD47", dim=True),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#2BC48A", dim=True),
            "ui.button.warning": Style(color="#0F5132", bgcolor="#FFCD3C", dim=True),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#D9480F", dim=True),
            "ui.input": Style(color="#0F5132", bgcolor="#F3FFF3", dim=True),
            "ui.input.focus": Style(color="#0F5132", bgcolor="#E5F9E5", dim=True),
            "ui.selection": Style(bgcolor=None),

            "content.text": Style(color="#1B5E20"),
            "content.heading": Style(color="#0F5132", bold=True),
            "content.subheading": Style(color="#2E7D32", bold=True),
            "content.link": Style(color="#82CD47", underline=True),
            "content.quote": Style(color="#2BC48A", italic=True),
            "content.code": Style(color="#2BC48A"),
            "content.highlight": Style(color="#0F5132", bgcolor="#F0FFCC"),

            "progress.bar": Style(color="#82CD47", dim=True),
            "progress.text": Style(color="#2E7D32"),
            "progress.percentage": Style(color="#0F5132"),

            "bookshelf.title": Style(color="#0F5132", bold=True),
            "bookshelf.author": Style(color="#2E7D32"),
            "bookshelf.progress": Style(color="#82CD47"),
            "bookshelf.tag": Style(color="#2BC48A", bgcolor="#F3FFF3", dim=True),
            "bookshelf.selected": Style(bgcolor="#E5F9E5", dim=True),

            "reader.text": Style(color="#1B5E20"),
            "reader.chapter": Style(color="#0F5132", bold=True),
            "reader.page_number": Style(color="#6E7F74"),
            "reader.bookmark": Style(color="#C3F73A"),
            "reader.search_result": Style(color="#0F5132", bgcolor="#F0FFCC"),
        }

        # 玻璃感/更强通透主题：紫玻璃
        self.themes["glass-violet"] = {
            "app.title": Style(color="#B794F4", bold=True),
            "app.subtitle": Style(color="#D6BCFA"),
            "app.accent": Style(color="#8B5CF6"),
            "app.highlight": Style(color="#F6E05E"),
            "app.warning": Style(color="#F56565"),
            "app.success": Style(color="#48BB78"),
            "app.info": Style(color="#63B3ED"),
            "app.muted": Style(color="#A3A3A3"),

            "ui.border": Style(color="#C4B5FD", dim=True),
            "ui.panel.title": Style(color="#B794F4", bold=True),
            "ui.label": Style(color="#EDE9FE"),
            "ui.button": Style(color="#EDE9FE"),
            "ui.button.primary": Style(color="#8B5CF6"),
            "ui.button.success": Style(color="#48BB78"),
            "ui.button.warning": Style(color="#F6E05E"),
            "ui.button.danger": Style(color="#F56565"),
            "ui.input": Style(color="#EDE9FE"),
            "ui.input.focus": Style(color="#B794F4"),

            "content.text": Style(color="#EDE9FE"),
            "content.heading": Style(color="#B794F4", bold=True),
            "content.subheading": Style(color="#8B5CF6", bold=True),
            "content.link": Style(color="#8B5CF6", underline=True),
            "content.quote": Style(color="#48BB78", italic=True),
            "content.code": Style(color="#48BB78"),
            "content.highlight": Style(color="#B794F4"),

            "progress.bar": Style(color="#8B5CF6"),
            "progress.text": Style(color="#D6BCFA"),
            "progress.percentage": Style(color="#B794F4"),

            "bookshelf.title": Style(color="#B794F4", bold=True),
            "bookshelf.author": Style(color="#D6BCFA"),
            "bookshelf.progress": Style(color="#8B5CF6"),
            "bookshelf.tag": Style(color="#48BB78"),
            "bookshelf.selected": Style(color="#D6BCFA"),

            "reader.text": Style(color="#EDE9FE"),
            "reader.chapter": Style(color="#B794F4", bold=True),
            "reader.page_number": Style(color="#C4B5FD"),
            "reader.bookmark": Style(color="#F6E05E"),
            "reader.search_result": Style(color="#B794F4"),
        }

        # 玻璃感/更强通透主题：翠玻璃
        self.themes["glass-emerald"] = {
            "app.title": Style(color="#6EE7B7", bold=True),
            "app.subtitle": Style(color="#A7F3D0"),
            "app.accent": Style(color="#10B981"),
            "app.highlight": Style(color="#FBBF24"),
            "app.warning": Style(color="#F87171"),
            "app.success": Style(color="#34D399"),
            "app.info": Style(color="#60A5FA"),
            "app.muted": Style(color="#94A3B8"),

            "ui.border": Style(color="#34D399", dim=True),
            "ui.panel.title": Style(color="#6EE7B7", bold=True),
            "ui.label": Style(color="#ECFDF5"),
            "ui.button": Style(color="#ECFDF5"),
            "ui.button.primary": Style(color="#10B981"),
            "ui.button.success": Style(color="#34D399"),
            "ui.button.warning": Style(color="#FBBF24"),
            "ui.button.danger": Style(color="#F87171"),
            "ui.input": Style(color="#ECFDF5"),
            "ui.input.focus": Style(color="#6EE7B7"),

            "content.text": Style(color="#ECFDF5"),
            "content.heading": Style(color="#6EE7B7", bold=True),
            "content.subheading": Style(color="#10B981", bold=True),
            "content.link": Style(color="#10B981", underline=True),
            "content.quote": Style(color="#34D399", italic=True),
            "content.code": Style(color="#34D399"),
            "content.highlight": Style(color="#6EE7B7"),

            "progress.bar": Style(color="#10B981"),
            "progress.text": Style(color="#A7F3D0"),
            "progress.percentage": Style(color="#6EE7B7"),

            "bookshelf.title": Style(color="#6EE7B7", bold=True),
            "bookshelf.author": Style(color="#A7F3D0"),
            "bookshelf.progress": Style(color="#10B981"),
            "bookshelf.tag": Style(color="#34D399"),
            "bookshelf.selected": Style(color="#A7F3D0"),

            "reader.text": Style(color="#ECFDF5"),
            "reader.chapter": Style(color="#6EE7B7", bold=True),
            "reader.page_number": Style(color="#34D399"),
            "reader.bookmark": Style(color="#FBBF24"),
            "reader.search_result": Style(color="#6EE7B7"),
        }

        # 玻璃感/更强通透主题：珊瑚玻璃
        self.themes["glass-coral"] = {
            "app.title": Style(color="#FF8A80", bold=True),
            "app.subtitle": Style(color="#FFD1C4"),
            "app.accent": Style(color="#FF6F61"),
            "app.highlight": Style(color="#FFD166"),
            "app.warning": Style(color="#EF4444"),
            "app.success": Style(color="#22C55E"),
            "app.info": Style(color="#60A5FA"),
            "app.muted": Style(color="#9CA3AF"),

            "ui.border": Style(color="#FF8A80", dim=True),
            "ui.panel.title": Style(color="#FF8A80", bold=True),
            "ui.label": Style(color="#FFE2DC"),
            "ui.button": Style(color="#FFE2DC"),
            "ui.button.primary": Style(color="#FF6F61"),
            "ui.button.success": Style(color="#22C55E"),
            "ui.button.warning": Style(color="#FFD166"),
            "ui.button.danger": Style(color="#EF4444"),
            "ui.input": Style(color="#FFE2DC"),
            "ui.input.focus": Style(color="#FF8A80"),

            "content.text": Style(color="#FFE2DC"),
            "content.heading": Style(color="#FF8A80", bold=True),
            "content.subheading": Style(color="#FF6F61", bold=True),
            "content.link": Style(color="#FF6F61", underline=True),
            "content.quote": Style(color="#22C55E", italic=True),
            "content.code": Style(color="#22C55E"),
            "content.highlight": Style(color="#FF8A80"),

            "progress.bar": Style(color="#FF6F61"),
            "progress.text": Style(color="#FFD1C4"),
            "progress.percentage": Style(color="#FF8A80"),

            "bookshelf.title": Style(color="#FF8A80", bold=True),
            "bookshelf.author": Style(color="#FFD1C4"),
            "bookshelf.progress": Style(color="#FF6F61"),
            "bookshelf.tag": Style(color="#22C55E"),
            "bookshelf.selected": Style(color="#FFD1C4"),

            "reader.text": Style(color="#FFE2DC"),
            "reader.chapter": Style(color="#FF8A80", bold=True),
            "reader.page_number": Style(color="#FF6F61"),
            "reader.bookmark": Style(color="#FFD166"),
            "reader.search_result": Style(color="#FF8A80"),
        }

        # 玻璃感/更强通透主题：天青玻璃
        self.themes["glass-sky"] = {
            "app.title": Style(color="#7DD3FC", bold=True),
            "app.subtitle": Style(color="#BAE6FD"),
            "app.accent": Style(color="#38BDF8"),
            "app.highlight": Style(color="#FDE047"),
            "app.warning": Style(color="#F87171"),
            "app.success": Style(color="#34D399"),
            "app.info": Style(color="#60A5FA"),
            "app.muted": Style(color="#93A3B3"),

            "ui.border": Style(color="#60A5FA", dim=True),
            "ui.panel.title": Style(color="#7DD3FC", bold=True),
            "ui.label": Style(color="#E0F2FE"),
            "ui.button": Style(color="#E0F2FE"),
            "ui.button.primary": Style(color="#38BDF8"),
            "ui.button.success": Style(color="#34D399"),
            "ui.button.warning": Style(color="#FDE047"),
            "ui.button.danger": Style(color="#F87171"),
            "ui.input": Style(color="#E0F2FE"),
            "ui.input.focus": Style(color="#7DD3FC"),

            "content.text": Style(color="#E0F2FE"),
            "content.heading": Style(color="#7DD3FC", bold=True),
            "content.subheading": Style(color="#38BDF8", bold=True),
            "content.link": Style(color="#38BDF8", underline=True),
            "content.quote": Style(color="#34D399", italic=True),
            "content.code": Style(color="#34D399"),
            "content.highlight": Style(color="#7DD3FC"),

            "progress.bar": Style(color="#38BDF8"),
            "progress.text": Style(color="#BAE6FD"),
            "progress.percentage": Style(color="#7DD3FC"),

            "bookshelf.title": Style(color="#7DD3FC", bold=True),
            "bookshelf.author": Style(color="#BAE6FD"),
            "bookshelf.progress": Style(color="#38BDF8"),
            "bookshelf.tag": Style(color="#34D399"),
            "bookshelf.selected": Style(color="#BAE6FD"),

            "reader.text": Style(color="#E0F2FE"),
            "reader.chapter": Style(color="#7DD3FC", bold=True),
            "reader.page_number": Style(color="#60A5FA"),
            "reader.bookmark": Style(color="#FDE047"),
            "reader.search_result": Style(color="#7DD3FC"),
        }

        # 玻璃感/更强通透主题：莓果玻璃
        self.themes["glass-berry"] = {
            "app.title": Style(color="#FB6F92", bold=True),
            "app.subtitle": Style(color="#FFC2D1"),
            "app.accent": Style(color="#F72585"),
            "app.highlight": Style(color="#FFD166"),
            "app.warning": Style(color="#E63946"),
            "app.success": Style(color="#06D6A0"),
            "app.info": Style(color="#4CC9F0"),
            "app.muted": Style(color="#A0A0A0"),

            "ui.border": Style(color="#F72585", dim=True),
            "ui.panel.title": Style(color="#FB6F92", bold=True),
            "ui.label": Style(color="#FFE3EC"),
            "ui.button": Style(color="#FFE3EC"),
            "ui.button.primary": Style(color="#F72585"),
            "ui.button.success": Style(color="#06D6A0"),
            "ui.button.warning": Style(color="#FFD166"),
            "ui.button.danger": Style(color="#E63946"),
            "ui.input": Style(color="#FFE3EC"),
            "ui.input.focus": Style(color="#FB6F92"),

            "content.text": Style(color="#FFE3EC"),
            "content.heading": Style(color="#FB6F92", bold=True),
            "content.subheading": Style(color="#F72585", bold=True),
            "content.link": Style(color="#4CC9F0", underline=True),
            "content.quote": Style(color="#06D6A0", italic=True),
            "content.code": Style(color="#06D6A0"),
            "content.highlight": Style(color="#FB6F92"),

            "progress.bar": Style(color="#4CC9F0"),
            "progress.text": Style(color="#FFC2D1"),
            "progress.percentage": Style(color="#FB6F92"),

            "bookshelf.title": Style(color="#FB6F92", bold=True),
            "bookshelf.author": Style(color="#FFC2D1"),
            "bookshelf.progress": Style(color="#4CC9F0"),
            "bookshelf.tag": Style(color="#06D6A0"),
            "bookshelf.selected": Style(color="#FFC2D1"),

            "reader.text": Style(color="#FFE3EC"),
            "reader.chapter": Style(color="#FB6F92", bold=True),
            "reader.page_number": Style(color="#4CC9F0"),
            "reader.bookmark": Style(color="#FFD166"),
            "reader.search_result": Style(color="#FB6F92"),
        }

        # 玻璃感/更强通透主题：芒果玻璃
        self.themes["glass-mango"] = {
            "app.title": Style(color="#FFB703", bold=True),
            "app.subtitle": Style(color="#FFE7A1"),
            "app.accent": Style(color="#FFA500"),
            "app.highlight": Style(color="#FFF176"),
            "app.warning": Style(color="#E76F51"),
            "app.success": Style(color="#2A9D8F"),
            "app.info": Style(color="#4EA8DE"),
            "app.muted": Style(color="#9E9E9E"),

            "ui.border": Style(color="#FFD166", dim=True),
            "ui.panel.title": Style(color="#FFB703", bold=True),
            "ui.label": Style(color="#FFF4CC"),
            "ui.button": Style(color="#FFF4CC"),
            "ui.button.primary": Style(color="#FFA500"),
            "ui.button.success": Style(color="#2A9D8F"),
            "ui.button.warning": Style(color="#FFF176"),
            "ui.button.danger": Style(color="#E76F51"),
            "ui.input": Style(color="#FFF4CC"),
            "ui.input.focus": Style(color="#FFB703"),

            "content.text": Style(color="#4E342E"),
            "content.heading": Style(color="#FFB703", bold=True),
            "content.subheading": Style(color="#FFA500", bold=True),
            "content.link": Style(color="#FFA500", underline=True),
            "content.quote": Style(color="#2A9D8F", italic=True),
            "content.code": Style(color="#2A9D8F"),
            "content.highlight": Style(color="#FFB703"),

            "progress.bar": Style(color="#FFA500"),
            "progress.text": Style(color="#FFE7A1"),
            "progress.percentage": Style(color="#FFB703"),

            "bookshelf.title": Style(color="#FFB703", bold=True),
            "bookshelf.author": Style(color="#FFE7A1"),
            "bookshelf.progress": Style(color="#FFA500"),
            "bookshelf.tag": Style(color="#2A9D8F"),
            "bookshelf.selected": Style(color="#FFE7A1"),

            "reader.text": Style(color="#4E342E"),
            "reader.chapter": Style(color="#FFB703", bold=True),
            "reader.page_number": Style(color="#FFA500"),
            "reader.bookmark": Style(color="#FFF176"),
            "reader.search_result": Style(color="#FFB703"),
        }

        # 玻璃感/更强通透主题：薄荷玻璃
        self.themes["glass-mint"] = {
            "app.title": Style(color="#64E1DC", bold=True),
            "app.subtitle": Style(color="#B2F1EF"),
            "app.accent": Style(color="#2DD4BF"),
            "app.highlight": Style(color="#FDE047"),
            "app.warning": Style(color="#FB7185"),
            "app.success": Style(color="#22C55E"),
            "app.info": Style(color="#60A5FA"),
            "app.muted": Style(color="#94A3B8"),

            "ui.border": Style(color="#2DD4BF", dim=True),
            "ui.panel.title": Style(color="#64E1DC", bold=True),
            "ui.label": Style(color="#ECFEFF"),
            "ui.button": Style(color="#ECFEFF"),
            "ui.button.primary": Style(color="#2DD4BF"),
            "ui.button.success": Style(color="#22C55E"),
            "ui.button.warning": Style(color="#FDE047"),
            "ui.button.danger": Style(color="#FB7185"),
            "ui.input": Style(color="#ECFEFF"),
            "ui.input.focus": Style(color="#64E1DC"),

            "content.text": Style(color="#ECFEFF"),
            "content.heading": Style(color="#64E1DC", bold=True),
            "content.subheading": Style(color="#2DD4BF", bold=True),
            "content.link": Style(color="#2DD4BF", underline=True),
            "content.quote": Style(color="#22C55E", italic=True),
            "content.code": Style(color="#22C55E"),
            "content.highlight": Style(color="#64E1DC"),

            "progress.bar": Style(color="#2DD4BF"),
            "progress.text": Style(color="#B2F1EF"),
            "progress.percentage": Style(color="#64E1DC"),

            "bookshelf.title": Style(color="#64E1DC", bold=True),
            "bookshelf.author": Style(color="#B2F1EF"),
            "bookshelf.progress": Style(color="#2DD4BF"),
            "bookshelf.tag": Style(color="#22C55E"),
            "bookshelf.selected": Style(color="#B2F1EF"),

            "reader.text": Style(color="#ECFEFF"),
            "reader.chapter": Style(color="#64E1DC", bold=True),
            "reader.page_number": Style(color="#2DD4BF"),
            "reader.bookmark": Style(color="#FDE047"),
            "reader.search_result": Style(color="#64E1DC"),
        }

        # 玻璃感/更强通透主题：岩浆玻璃
        self.themes["glass-lava"] = {
            "app.title": Style(color="#FF4D4F", bold=True),
            "app.subtitle": Style(color="#FF9A8B"),
            "app.accent": Style(color="#FF3B3B"),
            "app.highlight": Style(color="#FFCA3A"),
            "app.warning": Style(color="#E63946"),
            "app.success": Style(color="#2ECC71"),
            "app.info": Style(color="#339AF0"),
            "app.muted": Style(color="#A8ADB4"),

            "ui.border": Style(color="#FF4D4F", dim=True),
            "ui.panel.title": Style(color="#FF4D4F", bold=True),
            "ui.label": Style(color="#FFE5E5"),
            "ui.button": Style(color="#FFE5E5"),
            "ui.button.primary": Style(color="#FF3B3B"),
            "ui.button.success": Style(color="#2ECC71"),
            "ui.button.warning": Style(color="#FFCA3A"),
            "ui.button.danger": Style(color="#E63946"),
            "ui.input": Style(color="#FFE5E5"),
            "ui.input.focus": Style(color="#FF4D4F"),

            "content.text": Style(color="#FFE5E5"),
            "content.heading": Style(color="#FF4D4F", bold=True),
            "content.subheading": Style(color="#FF3B3B", bold=True),
            "content.link": Style(color="#339AF0", underline=True),
            "content.quote": Style(color="#2ECC71", italic=True),
            "content.code": Style(color="#2ECC71"),
            "content.highlight": Style(color="#FF4D4F"),

            "progress.bar": Style(color="#339AF0"),
            "progress.text": Style(color="#FF9A8B"),
            "progress.percentage": Style(color="#FF4D4F"),

            "bookshelf.title": Style(color="#FF4D4F", bold=True),
            "bookshelf.author": Style(color="#FF9A8B"),
            "bookshelf.progress": Style(color="#339AF0"),
            "bookshelf.tag": Style(color="#2ECC71"),
            "bookshelf.selected": Style(color="#FF9A8B"),

            "reader.text": Style(color="#FFE5E5"),
            "reader.chapter": Style(color="#FF4D4F", bold=True),
            "reader.page_number": Style(color="#339AF0"),
            "reader.bookmark": Style(color="#FFCA3A"),
            "reader.search_result": Style(color="#FF4D4F"),
        }

        # 玻璃感/更强通透主题：水玻璃
        self.themes["glass-aqua"] = {
            "app.title": Style(color="#7DF9FF", bold=True),
            "app.subtitle": Style(color="#C4F1F9"),
            "app.accent": Style(color="#00E5FF"),
            "app.highlight": Style(color="#FFF176"),
            "app.warning": Style(color="#FF6B6B"),
            "app.success": Style(color="#00E676"),
            "app.info": Style(color="#4FC3F7"),
            "app.muted": Style(color="#9AA7B2"),

            "ui.border": Style(color="#00E5FF", dim=True),
            "ui.panel.title": Style(color="#7DF9FF", bold=True),
            "ui.label": Style(color="#E6FDFF"),
            "ui.button": Style(color="#E6FDFF"),
            "ui.button.primary": Style(color="#00E5FF"),
            "ui.button.success": Style(color="#00E676"),
            "ui.button.warning": Style(color="#FFF176"),
            "ui.button.danger": Style(color="#FF6B6B"),
            "ui.input": Style(color="#E6FDFF"),
            "ui.input.focus": Style(color="#7DF9FF"),

            "content.text": Style(color="#E6FDFF"),
            "content.heading": Style(color="#7DF9FF", bold=True),
            "content.subheading": Style(color="#00E5FF", bold=True),
            "content.link": Style(color="#00E5FF", underline=True),
            "content.quote": Style(color="#00E676", italic=True),
            "content.code": Style(color="#00E676"),
            "content.highlight": Style(color="#7DF9FF"),

            "progress.bar": Style(color="#00E5FF"),
            "progress.text": Style(color="#C4F1F9"),
            "progress.percentage": Style(color="#7DF9FF"),

            "bookshelf.title": Style(color="#7DF9FF", bold=True),
            "bookshelf.author": Style(color="#C4F1F9"),
            "bookshelf.progress": Style(color="#00E5FF"),
            "bookshelf.tag": Style(color="#00E676"),
            "bookshelf.selected": Style(color="#C4F1F9"),

            "reader.text": Style(color="#E6FDFF"),
            "reader.chapter": Style(color="#7DF9FF", bold=True),
            "reader.page_number": Style(color="#00E5FF"),
            "reader.bookmark": Style(color="#FFF176"),
            "reader.search_result": Style(color="#7DF9FF"),
        }

        # 玻璃感/更强通透主题：石墨玻璃（单色系）
        self.themes["glass-graphite"] = {
            "app.title": Style(color="#E5E7EB", bold=True),
            "app.subtitle": Style(color="#D1D5DB"),
            "app.accent": Style(color="#9CA3AF"),
            "app.highlight": Style(color="#FCD34D"),
            "app.warning": Style(color="#F87171"),
            "app.success": Style(color="#34D399"),
            "app.info": Style(color="#60A5FA"),
            "app.muted": Style(color="#9CA3AF"),

            "ui.border": Style(color="#9CA3AF", dim=True),
            "ui.panel.title": Style(color="#E5E7EB", bold=True),
            "ui.label": Style(color="#F3F4F6"),
            "ui.button": Style(color="#F3F4F6"),
            "ui.button.primary": Style(color="#9CA3AF"),
            "ui.button.success": Style(color="#34D399"),
            "ui.button.warning": Style(color="#FCD34D"),
            "ui.button.danger": Style(color="#F87171"),
            "ui.input": Style(color="#F3F4F6"),
            "ui.input.focus": Style(color="#E5E7EB"),

            "content.text": Style(color="#F3F4F6"),
            "content.heading": Style(color="#E5E7EB", bold=True),
            "content.subheading": Style(color="#9CA3AF", bold=True),
            "content.link": Style(color="#9CA3AF", underline=True),
            "content.quote": Style(color="#34D399", italic=True),
            "content.code": Style(color="#34D399"),
            "content.highlight": Style(color="#E5E7EB"),

            "progress.bar": Style(color="#9CA3AF"),
            "progress.text": Style(color="#D1D5DB"),
            "progress.percentage": Style(color="#E5E7EB"),

            "bookshelf.title": Style(color="#E5E7EB", bold=True),
            "bookshelf.author": Style(color="#D1D5DB"),
            "bookshelf.progress": Style(color="#9CA3AF"),
            "bookshelf.tag": Style(color="#34D399"),
            "bookshelf.selected": Style(color="#D1D5DB"),

            "reader.text": Style(color="#F3F4F6"),
            "reader.chapter": Style(color="#E5E7EB", bold=True),
            "reader.page_number": Style(color="#9CA3AF"),
            "reader.bookmark": Style(color="#FCD34D"),
            "reader.search_result": Style(color="#E5E7EB"),
        }

        # 玻璃感/更强通透主题：青柠薄荷玻璃
        self.themes["glass-limefresh"] = {
            "app.title": Style(color="#C6F432", bold=True),
            "app.subtitle": Style(color="#E4FF8D"),
            "app.accent": Style(color="#A3E635"),
            "app.highlight": Style(color="#FFEA00"),
            "app.warning": Style(color="#FB7185"),
            "app.success": Style(color="#22C55E"),
            "app.info": Style(color="#38BDF8"),
            "app.muted": Style(color="#94A3B8"),

            "ui.border": Style(color="#A3E635", dim=True),
            "ui.panel.title": Style(color="#C6F432", bold=True),
            "ui.label": Style(color="#F7FFCC"),
            "ui.button": Style(color="#F7FFCC"),
            "ui.button.primary": Style(color="#A3E635"),
            "ui.button.success": Style(color="#22C55E"),
            "ui.button.warning": Style(color="#FFEA00"),
            "ui.button.danger": Style(color="#FB7185"),
            "ui.input": Style(color="#F7FFCC"),
            "ui.input.focus": Style(color="#C6F432"),

            "content.text": Style(color="#1B5E20"),
            "content.heading": Style(color="#C6F432", bold=True),
            "content.subheading": Style(color="#A3E635", bold=True),
            "content.link": Style(color="#A3E635", underline=True),
            "content.quote": Style(color="#22C55E", italic=True),
            "content.code": Style(color="#22C55E"),
            "content.highlight": Style(color="#C6F432"),

            "progress.bar": Style(color="#A3E635"),
            "progress.text": Style(color="#E4FF8D"),
            "progress.percentage": Style(color="#C6F432"),

            "bookshelf.title": Style(color="#C6F432", bold=True),
            "bookshelf.author": Style(color="#E4FF8D"),
            "bookshelf.progress": Style(color="#A3E635"),
            "bookshelf.tag": Style(color="#22C55E"),
            "bookshelf.selected": Style(color="#E4FF8D"),

            "reader.text": Style(color="#1B5E20"),
            "reader.chapter": Style(color="#C6F432", bold=True),
            "reader.page_number": Style(color="#A3E635"),
            "reader.bookmark": Style(color="#FFEA00"),
            "reader.search_result": Style(color="#C6F432"),
        }

        # 玻璃感/更强通透主题：极光玻璃
        self.themes["glass-aurora"] = {
            "app.title": Style(color="#7DF9FF", bold=True),
            "app.subtitle": Style(color="#B5E8F7"),
            "app.accent": Style(color="#80FFEA"),
            "app.highlight": Style(color="#FFF176"),
            "app.warning": Style(color="#FF6B6B"),
            "app.success": Style(color="#9DFFAD"),
            "app.info": Style(color="#A78BFA"),
            "app.muted": Style(color="#A0AEC0"),

            "ui.border": Style(color="#80FFEA", dim=True),
            "ui.panel.title": Style(color="#7DF9FF", bold=True),
            "ui.label": Style(color="#E6FDFF"),
            "ui.button": Style(color="#E6FDFF"),
            "ui.button.primary": Style(color="#80FFEA"),
            "ui.button.success": Style(color="#9DFFAD"),
            "ui.button.warning": Style(color="#FFF176"),
            "ui.button.danger": Style(color="#FF6B6B"),
            "ui.input": Style(color="#E6FDFF"),
            "ui.input.focus": Style(color="#7DF9FF"),

            "content.text": Style(color="#E6FDFF"),
            "content.heading": Style(color="#7DF9FF", bold=True),
            "content.subheading": Style(color="#80FFEA", bold=True),
            "content.link": Style(color="#80FFEA", underline=True),
            "content.quote": Style(color="#9DFFAD", italic=True),
            "content.code": Style(color="#9DFFAD"),
            "content.highlight": Style(color="#7DF9FF"),

            "progress.bar": Style(color="#80FFEA"),
            "progress.text": Style(color="#B5E8F7"),
            "progress.percentage": Style(color="#7DF9FF"),

            "bookshelf.title": Style(color="#7DF9FF", bold=True),
            "bookshelf.author": Style(color="#B5E8F7"),
            "bookshelf.progress": Style(color="#80FFEA"),
            "bookshelf.tag": Style(color="#9DFFAD"),
            "bookshelf.selected": Style(color="#B5E8F7"),

            "reader.text": Style(color="#E6FDFF"),
            "reader.chapter": Style(color="#7DF9FF", bold=True),
            "reader.page_number": Style(color="#80FFEA"),
            "reader.bookmark": Style(color="#FFF176"),
            "reader.search_result": Style(color="#7DF9FF"),
        }

        # 玻璃感/更强通透主题：樱桃玻璃
        self.themes["glass-cherry"] = {
            "app.title": Style(color="#FF4D6D", bold=True),
            "app.subtitle": Style(color="#FF9EB5"),
            "app.accent": Style(color="#E5383B"),
            "app.highlight": Style(color="#FFD166"),
            "app.warning": Style(color="#EF4444"),
            "app.success": Style(color="#06D6A0"),
            "app.info": Style(color="#3A86FF"),
            "app.muted": Style(color="#A3A3A3"),

            "ui.border": Style(color="#FF4D6D", dim=True),
            "ui.panel.title": Style(color="#FF4D6D", bold=True),
            "ui.label": Style(color="#FFE3EA"),
            "ui.button": Style(color="#FFE3EA"),
            "ui.button.primary": Style(color="#E5383B"),
            "ui.button.success": Style(color="#06D6A0"),
            "ui.button.warning": Style(color="#FFD166"),
            "ui.button.danger": Style(color="#EF4444"),
            "ui.input": Style(color="#FFE3EA"),
            "ui.input.focus": Style(color="#FF4D6D"),

            "content.text": Style(color="#FFE3EA"),
            "content.heading": Style(color="#FF4D6D", bold=True),
            "content.subheading": Style(color="#E5383B", bold=True),
            "content.link": Style(color="#3A86FF", underline=True),
            "content.quote": Style(color="#06D6A0", italic=True),
            "content.code": Style(color="#06D6A0"),
            "content.highlight": Style(color="#FF4D6D"),

            "progress.bar": Style(color="#3A86FF"),
            "progress.text": Style(color="#FF9EB5"),
            "progress.percentage": Style(color="#FF4D6D"),

            "bookshelf.title": Style(color="#FF4D6D", bold=True),
            "bookshelf.author": Style(color="#FF9EB5"),
            "bookshelf.progress": Style(color="#3A86FF"),
            "bookshelf.tag": Style(color="#06D6A0"),
            "bookshelf.selected": Style(color="#FF9EB5"),

            "reader.text": Style(color="#FFE3EA"),
            "reader.chapter": Style(color="#FF4D6D", bold=True),
            "reader.page_number": Style(color="#3A86FF"),
            "reader.bookmark": Style(color="#FFD166"),
            "reader.search_result": Style(color="#FF4D6D"),
        }

        logger.info(f"已加载内置主题: {', '.join(self.themes.keys())}")
    
    def get_available_themes(self) -> List[str]:
        """
        获取所有可用的主题名称
        
        Returns:
            List[str]: 主题名称列表
        """
        return list(self.themes.keys())
    
    def get_current_theme_name(self) -> str:
        """
        获取当前主题名称
        
        Returns:
            str: 当前主题名称
        """
        return self.current_theme_name
    
    def set_theme(self, theme_name: str) -> bool:
        """
        设置当前主题
        
        Args:
            theme_name: 主题名称
            
        Returns:
            bool: 设置是否成功
        """
        if theme_name not in self.themes:
            logger.error(f"主题不存在: {theme_name}")
            return False
        
        self.current_theme_name = theme_name
        logger.info(f"当前主题已设置为: {theme_name}")
        return True
    
    def convert_color_to_string(self, color_obj) -> str:
        """将Rich Color对象转换为Textual颜色字符串"""
        if hasattr(color_obj, 'name') and color_obj.name:
            return color_obj.name
        elif hasattr(color_obj, 'triplet'):
            r, g, b = color_obj.triplet
            return f"#{r:02x}{g:02x}{b:02x}"
        else:
            return "white"
    
    def get_simple_theme_colors(self, theme_name: str) -> tuple[str, str]:
        """获取简单的主题颜色（没有theme_manager时的备用方案）"""
        if "light" in theme_name.lower():
            return "white", "black"
        else:
            return "black", "white"
    
    def get_style(self, style_name: str) -> Optional[Style]:
        """
        获取指定样式
        
        Args:
            style_name: 样式名称
            
        Returns:
            Optional[Style]: 样式对象，如果不存在则返回None
        """
        if self.current_theme_name not in self.themes:
            logger.error(f"当前主题不存在: {self.current_theme_name}")
            return None
        
        theme = self.themes[self.current_theme_name]
        if style_name not in theme:
            logger.warning(f"样式不存在: {style_name}")
            return None
        
        return theme[style_name]
    
    def get_rich_theme(self) -> RichTheme:
        """
        获取Rich库使用的主题对象
        
        Returns:
            RichTheme: Rich库主题对象
        """
        if self.current_theme_name not in self.themes:
            logger.error(f"当前主题不存在: {self.current_theme_name}")
            return RichTheme()
        
        theme = self.themes[self.current_theme_name]
        styles = {name: style for name, style in theme.items()}
        return RichTheme(styles=styles)
    
    def get_theme_colors(self) -> Dict[str, str]:
        """
        获取当前主题的颜色映射
        
        Returns:
            Dict[str, str]: 颜色名称到颜色值的映射
        """
        if self.current_theme_name not in self.themes:
            logger.error(f"当前主题不存在: {self.current_theme_name}")
            return {}
        
        theme = self.themes[self.current_theme_name]
        colors = {}
        
        for name, style in theme.items():
            if style.color:
                colors[f"{name}.fg"] = style.color
            if style.bgcolor:
                colors[f"{name}.bg"] = style.bgcolor
        
        return colors
    
    def create_custom_theme(self, name: str, styles: Dict[str, Style]) -> bool:
        """
        创建自定义主题
        
        Args:
            name: 主题名称
            styles: 样式字典
            
        Returns:
            bool: 创建是否成功
        """
        if name in self.themes:
            logger.warning(f"主题已存在，将被覆盖: {name}")
        
        self.themes[name] = styles
        logger.info(f"已创建自定义主题: {name}")
        return True

    def apply_theme_to_screen(self, screen) -> None:
        """
        应用主题到屏幕

        Args:
            screen: 要应用主题的屏幕对象
        """
        if not hasattr(screen, "app"):
            return
        # 应用未运行或正在退出时，不更新样式
        if hasattr(screen.app, "is_running") and not screen.app.is_running:
            return
            
        # 使用Textual内置的主题支持
        if self.current_theme_name in ["dark", "dracula", "nord", "material", "github-dark", "solarized-dark", "amethyst", "forest-green", "crimson", "slate", "transparent-dark", "cyberpunk", "rainbow-bright", "tropical", "lime-punch", "electric-blue", "magenta-blast", "galaxy", "fiesta", "glass-cyan", "glass-rose"]:
            screen.app.dark = True
        else:
            screen.app.dark = False
        # 同步到 Textual 主题（尽力而为）
        try:
            self.apply_textual_theme(screen.app, self.current_theme_name)
        except Exception as _e:
            logger.debug(f"应用 Textual 主题失败（可忽略）：{_e}")
            
        # 获取当前主题的颜色配置
        theme_config = self.themes.get(self.current_theme_name, {})
        
        # 设置Textual CSS变量来覆盖默认颜色
        if theme_config:
            # 获取主要颜色
            text_style = theme_config.get("content.text") or theme_config.get("ui.label")
            primary_style = theme_config.get("app.accent") or theme_config.get("app.primary")
            accent_style = theme_config.get("app.highlight") or theme_config.get("app.accent")
            background_style = theme_config.get("ui.background")
            surface_style = theme_config.get("ui.panel")
            border_style = theme_config.get("ui.border")
            
            # 提取颜色值
            text_color = getattr(text_style, "color", None) if text_style else None
            primary_color = getattr(primary_style, "color", None) if primary_style else None
            accent_color = getattr(accent_style, "color", None) if accent_style else None
            background_color = getattr(background_style, "bgcolor", None) if background_style else None
            surface_color = getattr(surface_style, "bgcolor", None) if surface_style else None
            border_color = getattr(border_style, "color", None) if border_style else None
            
            # 设置CSS变量
            if text_color:
                screen.styles.set_rule("$text", text_color)
                screen.styles.set_rule("$text-muted", text_color)
                # 提供 $foreground 变量，供 TSS 使用
                screen.styles.set_rule("$foreground", text_color)
            else:
                # 当正文颜色缺失时，提供 $foreground 回退（light 等主题）
                _fg_fallback = primary_color or accent_color or surface_color or "#333333"
                if _fg_fallback:
                    screen.styles.set_rule("$foreground", _fg_fallback)
            
            if primary_color:
                screen.styles.set_rule("$primary", primary_color)
                # 提供主色的衍生变量，兼容 TSS 中的 lighten/darken 用法
                def _adjust_hex_lightness(hex_color: str, delta: int) -> str:
                    try:
                        c = hex_color.strip()
                        if c.startswith("#"):
                            c = c[1:]
                        # 支持简写 #rgb
                        if len(c) == 3:
                            c = "".join(ch*2 for ch in c)
                        r = int(c[0:2], 16)
                        g = int(c[2:4], 16)
                        b = int(c[4:6], 16)
                        def clamp(x): 
                            return max(0, min(255, x))
                        r = clamp(r + delta)
                        g = clamp(g + delta)
                        b = clamp(b + delta)
                        return f"#{r:02x}{g:02x}{b:02x}"
                    except Exception:
                        # 回退原色
                        return hex_color
                screen.styles.set_rule("$primary-lighten-1", _adjust_hex_lightness(primary_color, 20))
                screen.styles.set_rule("$primary-darken-1", _adjust_hex_lightness(primary_color, -20))
            
            if accent_color:
                screen.styles.set_rule("$accent", accent_color)
            if border_color:
                # 提供 $border 变量，供 TSS 使用（如 border: tall $border）
                screen.styles.set_rule("$border", border_color)
            else:
                # 主题缺少边框色时的回退（保证 TSS 的 border 解析）
                _border_fallback = primary_color or text_color or accent_color or surface_color or "#808080"
                if _border_fallback:
                    screen.styles.set_rule("$border", _border_fallback)
            
            if background_color:
                screen.styles.set_rule("$background", background_color)
            
            if surface_color:
                screen.styles.set_rule("$surface", surface_color)
                # 不设置 $panel（在 Textual 默认 CSS 中，$panel 用作 hatch 的百分比）
                # 提供表面色的衍生变量（用于边框/hover 等）
                def _adjust_hex_lightness(hex_color: str, delta: int) -> str:
                    try:
                        c = hex_color.strip()
                        if c.startswith("#"):
                            c = c[1:]
                        if len(c) == 3:
                            c = "".join(ch*2 for ch in c)
                        r = int(c[0:2], 16)
                        g = int(c[2:4], 16)
                        b = int(c[4:6], 16)
                        def clamp(x): 
                            return max(0, min(255, x))
                        r = clamp(r + delta)
                        g = clamp(g + delta)
                        b = clamp(b + delta)
                        return f"#{r:02x}{g:02x}{b:02x}"
                    except Exception:
                        return hex_color
                screen.styles.set_rule("$surface-lighten-1", _adjust_hex_lightness(surface_color, 20))
                screen.styles.set_rule("$surface-darken-1", _adjust_hex_lightness(surface_color, -20))
            else:
                # 不再为 $panel 提供颜色兜底，避免覆盖其“百分比”语义
                pass
            
            # 应用更多主题样式（稳健：若根节点未就绪则延迟）
            target_screen = getattr(screen.app, "screen", None) or screen

            def _do_apply():
                app_obj = getattr(target_screen, "app", None) or getattr(screen, "app", None)
                if app_obj is None or (hasattr(app_obj, "is_running") and not app_obj.is_running):
                    return
                try:
                    self._apply_comprehensive_theme_styles(target_screen, theme_config)
                except Exception as _e:
                    logger.debug(f"应用全面主题样式失败（可忽略）：{_e}")

            if hasattr(target_screen, "styles") and getattr(target_screen, "is_mounted", True):
                _do_apply()
            elif hasattr(target_screen, "call_later"):
                app_obj = getattr(target_screen, "app", None) or getattr(screen, "app", None)
                if app_obj is None or (hasattr(app_obj, "is_running") and not app_obj.is_running):
                    pass
                else:
                    try:
                        target_screen.call_later(_do_apply)
                    except Exception as _e:
                        logger.debug(f"延迟应用主题样式失败（可忽略）：{_e}")
            else:
                return
    
    def _apply_comprehensive_theme_styles(self, screen, theme_config: Dict[str, Any]) -> None:
        """应用全面的主题样式到屏幕组件"""
        if not hasattr(screen, "styles"):
            return

        # 如果未挂载，延迟应用
        if hasattr(screen, "is_mounted") and not screen.is_mounted:
            if hasattr(screen, "call_later"):
                try:
                    screen.call_later(lambda: self._apply_comprehensive_theme_styles(screen, theme_config))
                except Exception as _e:
                    logger.debug(f"延迟应用全面样式失败（可忽略）：{_e}")
            return
            
        # 应用UI组件样式
        self._apply_ui_component_styles(screen, theme_config)
        
        # 应用内容样式
        self._apply_content_styles(screen, theme_config)
        
        # 应用特殊组件样式
        self._apply_special_component_styles(screen, theme_config)
    
    def _apply_ui_component_styles(self, screen, theme_config: Dict[str, Any]) -> None:
        """应用UI组件样式"""
        # 按钮样式
        button_style = theme_config.get("ui.button")
        if button_style:
            screen.styles.set_rule("Button", f"color: {self.convert_color_to_string(button_style.color)}; background: {self.convert_color_to_string(button_style.bgcolor)}")
        
        # 输入框样式
        input_style = theme_config.get("ui.input")
        if input_style:
            screen.styles.set_rule("Input", f"color: {self.convert_color_to_string(input_style.color)}; background: {self.convert_color_to_string(input_style.bgcolor)}")
        
        # 标签样式
        label_style = theme_config.get("ui.label")
        if label_style:
            screen.styles.set_rule("Label", f"color: {self.convert_color_to_string(label_style.color)}")
    
    def _apply_content_styles(self, screen, theme_config: Dict[str, Any]) -> None:
        """应用内容样式"""
        # 标题样式
        title_style = theme_config.get("app.title")
        if title_style:
            screen.styles.set_rule(".title", f"color: {self.convert_color_to_string(title_style.color)}; font-weight: bold")
        
        # 副标题样式
        subtitle_style = theme_config.get("app.subtitle")
        if subtitle_style:
            screen.styles.set_rule(".subtitle", f"color: {self.convert_color_to_string(subtitle_style.color)}")
        
        # 强调样式
        accent_style = theme_config.get("app.accent")
        if accent_style:
            screen.styles.set_rule(".accent", f"color: {self.convert_color_to_string(accent_style.color)}")
        
        # 高亮样式
        highlight_style = theme_config.get("app.highlight")
        if highlight_style:
            screen.styles.set_rule(".highlight", f"color: {self.convert_color_to_string(highlight_style.color)}")
        
        # 警告样式
        warning_style = theme_config.get("app.warning")
        if warning_style:
            screen.styles.set_rule(".warning", f"color: {self.convert_color_to_string(warning_style.color)}")
        
        # 成功样式
        success_style = theme_config.get("app.success")
        if success_style:
            screen.styles.set_rule(".success", f"color: {self.convert_color_to_string(success_style.color)}")
        
        # 信息样式
        info_style = theme_config.get("app.info")
        if info_style:
            screen.styles.set_rule(".info", f"color: {self.convert_color_to_string(info_style.color)}")
        
        # 静音样式
        muted_style = theme_config.get("app.muted")
        if muted_style:
            screen.styles.set_rule(".muted", f"color: {self.convert_color_to_string(muted_style.color)}")
    
    def _apply_special_component_styles(self, screen, theme_config: Dict[str, Any]) -> None:
        """应用特殊组件样式"""
        # 进度条样式
        progress_bar_style = theme_config.get("progress.bar")
        if progress_bar_style:
            screen.styles.set_rule("ProgressBar", f"color: {self.convert_color_to_string(progress_bar_style.color)}")
        
        # 书架样式
        bookshelf_title_style = theme_config.get("bookshelf.title")
        if bookshelf_title_style:
            screen.styles.set_rule(".bookshelf-title", f"color: {self.convert_color_to_string(bookshelf_title_style.color)}; font-weight: bold")
        
        # 阅读器样式
        reader_text_style = theme_config.get("reader.text")
        if reader_text_style:
            screen.styles.set_rule(".reader-text", f"color: {self.convert_color_to_string(reader_text_style.color)}")
            
        # 刷新屏幕以应用主题变化
        screen.refresh()

    def _build_textual_theme_payload(self, theme_name: str) -> Dict[str, str]:
        """将内部主题映射为 Textual 主题字段负载"""
        theme = self.themes.get(theme_name, {})
        def pick(names: List[str]) -> Optional[str]:
            for n in names:
                st = theme.get(n)
                if st and getattr(st, "color", None):
                    return self.convert_color_to_string(st.color)
                if st and getattr(st, "bgcolor", None):
                    return self.convert_color_to_string(st.bgcolor)
            return None

        payload = {
            # 基础/语义文本色
            "text": pick(["reader.text", "content.text", "ui.label"]) or ("#ffffff" if "dark" in theme_name else "#000000"),
            "text_muted": pick(["app.muted", "bookshelf.author"]) or ( "#9CA3AF" if "dark" in theme_name else "#6B7280"),
            # 品牌与强调
            "primary": pick(["app.accent", "app.primary"]) or "#3B82F6",
            "accent": pick(["app.highlight", "app.accent"]) or "#F59E0B",
            # 状态色
            "success": pick(["app.success"]) or "#22C55E",
            "warning": pick(["app.warning"]) or "#F59E0B",
            "info": pick(["app.info"]) or "#0EA5E9",
            # 背景与容器
            "background": pick(["ui.background"]) or ("#000000" if "dark" in theme_name else "#ffffff"),
            "surface": pick(["ui.panel"]) or pick(["ui.background"]) or ("#111827" if "dark" in theme_name else "#f3f4f6"),
            "panel": pick(["ui.panel"]) or pick(["ui.background"]) or ("#111827" if "dark" in theme_name else "#f3f4f6"),
            # 辅助语义
            "border": pick(["ui.border"]) or ( "#4B5563" if "dark" in theme_name else "#D1D5DB"),
            "link": pick(["content.link"]) or pick(["app.accent"]) or "#3B82F6",
            "heading": pick(["content.heading", "app.title"]) or ( "#F9FAFB" if "dark" in theme_name else "#111827"),
            "quote": pick(["content.quote"]) or pick(["text"]) or ( "#D1D5DB" if "dark" in theme_name else "#374151"),
            "code": pick(["content.code"]) or pick(["success"]) or "#10B981",
            "code_background": pick(["content.code"]) or pick(["surface"]) or ("#1F2937" if "dark" in theme_name else "#E5E7EB"),
        }
        # 对玻璃感主题，不注入背景相关变量，避免填充背景
        if theme_name.startswith("glass-"):
            # 玻璃主题不注入背景相关变量，但保留 panel，以满足 Textual 默认 CSS 对 $panel 的依赖
            for k in ("background", "surface", "code_background"):
                payload.pop(k, None)
        # 确保 panel 始终存在（避免 App.DEFAULT_CSS 中 hatch: right $panel 解析失败）
        if not payload.get("panel"):
            payload["panel"] = payload.get("surface") or payload.get("background") or "#2f2f2f"
        return {k: v for k, v in payload.items() if v}


    def apply_textual_theme(self, app, name: Optional[str] = None) -> None:
        """应用主题到 Textual App（设置语义色或调用内置 API）"""
        try:
            theme_name = name or self.current_theme_name
            payload = self._build_textual_theme_payload(theme_name)

            # 应用未运行或正在退出时，不继续主题注册/样式注入
            if hasattr(app, "is_running") and not app.is_running:
                return

            # 尽力确保已注册（与 _register_one_with_textual 相同的多入口逻辑）
            try:
                import importlib
                from typing import Any
                theme_obj = None

                def _try_module(module_name: str) -> bool:
                    try:
                        mod: Any = importlib.import_module(module_name)
                    except Exception:
                        return False
                    for fn in ("register_theme", "add_theme", "register", "add"):
                        callable_fn = getattr(mod, fn, None)
                        if callable(callable_fn):
                            try:
                                callable_fn(theme_name, payload)
                                logger.debug(f"确保注册：{module_name}.{fn} -> {theme_name}")
                                return True
                            except Exception:
                                continue
                    return False

                ok = _try_module("textual.theme")
                if not ok:
                    ok = _try_module("textual.themes")
                if not ok:
                    # 兜底注入 textual.theme.THEMES
                    try:
                        import importlib
                        mod = importlib.import_module("textual.theme")
                        themes_dict = getattr(mod, "THEMES", None)
                        if isinstance(themes_dict, dict):
                            themes_dict[theme_name] = payload
                            logger.debug(f"确保注册：textual.theme.THEMES -> {theme_name}")
                    except Exception:
                        pass
            except Exception:
                pass

            if hasattr(app, "set_theme") and callable(getattr(app, "set_theme")):
                app.set_theme(theme_name)
            elif hasattr(app, "theme"):
                try:
                    app.theme = theme_name
                except Exception:
                    pass

            try:
                if hasattr(app, "stylesheet") and hasattr(app.stylesheet, "add_source"):
                    # 使用 Textual TSS 变量语法，顶层声明：$var: value;
                    css_lines = [f"${k}: {v};" for k, v in payload.items()]
                    app.stylesheet.add_source("\n".join(css_lines))
                    if hasattr(app, "screen_stack") and app.screen_stack:
                        target = app.screen_stack[-1]
                        try:
                            if hasattr(target, "is_mounted") and not target.is_mounted and hasattr(target, "call_later"):
                                target.call_later(lambda: app.stylesheet.update(target))
                            else:
                                app.stylesheet.update(target)
                        except Exception as e:
                            logger.debug(f"更新样式表失败（可忽略）：{e}")
            except Exception as e:
                logger.debug(f"注入主题 CSS 变量失败（可忽略）：{e}")
        except Exception as e:
            logger.debug(f"应用 Textual 主题失败（可忽略）：{e}")

    def _register_one_with_textual(self, theme_name: str) -> bool:
        """将单个主题注册到 Textual 的主题系统（尽力兼容不同版本的 API）"""
        try:
            payload = self._build_textual_theme_payload(theme_name)

            # 根据名称判断暗色/亮色，用于某些版本 Theme 需要的标记
            is_dark = any(x in theme_name for x in ["dark", "dracula", "nord", "material", "github-dark", "solarized-dark", "amethyst", "forest-green", "crimson", "slate", "transparent-dark", "cyberpunk", "rainbow-bright", "tropical", "lime-punch", "electric-blue", "magenta-blast", "galaxy", "fiesta", "glass-cyan", "glass-rose"])
            is_light = not is_dark

            import importlib
            from typing import Any
            from textual.theme import Theme as TextualTheme  # 可能不同版本签名差异，运行时尝试

            def _call_with_variants(callable_fn, module_name: str, fn_name: str) -> bool:
                # 依次尝试不同签名：dict 负载、Theme(colors=payload)、Theme(name, colors=payload)、Theme(name=name, colors=payload, dark=...)
                try:
                    callable_fn(theme_name, payload)
                    logger.debug(f"主题注册成功（dict）：{module_name}.{fn_name} -> {theme_name}")
                    return True
                except Exception:
                    pass
                try:
                    theme_obj = None
                    # 多种构造尝试
                    for ctor in (
                        lambda: TextualTheme(payload),
                        lambda: TextualTheme(colors=payload),
                        lambda: TextualTheme(theme_name, payload),
                        lambda: TextualTheme(name=theme_name, colors=payload),
                        lambda: TextualTheme(name=theme_name, colors=payload, dark=is_dark, light=is_light),
                    ):
                        try:
                            theme_obj = ctor()
                        except Exception:
                            theme_obj = None
                        if theme_obj is None:
                            continue
                        try:
                            callable_fn(theme_name, theme_obj)
                            logger.debug(f"主题注册成功（Theme）：{module_name}.{fn_name} -> {theme_name}")
                            return True
                        except Exception:
                            continue
                except Exception:
                    pass
                return False

            def _try_module(module_name: str) -> bool:
                try:
                    mod: Any = importlib.import_module(module_name)
                except Exception:
                    return False
                for fn in ("register_theme", "add_theme", "register", "add"):
                    callable_fn = getattr(mod, fn, None)
                    if callable(callable_fn):
                        if _call_with_variants(callable_fn, module_name, fn):
                            return True
                return False

            ok = _try_module("textual.theme")
            if not ok:
                ok = _try_module("textual.themes")
            if not ok:
                # 兜底：直接写入 textual.theme.THEMES，同时尝试写入 Theme 实例和 dict
                try:
                    mod = importlib.import_module("textual.theme")
                    themes_dict = getattr(mod, "THEMES", None)
                    if isinstance(themes_dict, dict):
                        try:
                            themes_dict[theme_name] = payload
                        except Exception:
                            pass
                        try:
                            # Theme 实例也放进去，兼容期望类型为 Theme 的版本
                            themes_dict[theme_name] = TextualTheme(name=theme_name, colors=payload)  # 类型可能不匹配但尽量尝试
                        except Exception:
                            pass
                        logger.debug(f"主题兜底写入：textual.theme.THEMES -> {theme_name}")
                        ok = True
                    else:
                        ok = False
                except Exception:
                    ok = False
            return ok
        except Exception as e:
            logger.debug(f"注册单个主题到 Textual 失败（可忽略）：{e}")
            return False

    def register_with_textual(self) -> None:
        """批量将所有内置主题注册到 Textual 的主题选择器（Ctrl-P 可见）"""
        try:
            names = list(self.themes.keys())
            if not names:
                logger.debug("没有可注册的主题")
                return
            success = 0
            for name in names:
                if self._register_one_with_textual(name):
                    success += 1
            # 注册后读取 Textual 实际主题表的键，帮助诊断 Ctrl-P 来源
            try:
                import importlib
                mod = importlib.import_module("textual.theme")
                themes_dict = getattr(mod, "THEMES", {})
                keys = list(getattr(themes_dict, "keys", lambda: [])())
                logger.info(f"Textual 全局 THEMES 当前包含：{', '.join(keys) if keys else '(空)'}")
            except Exception:
                pass
            logger.info(f"已向 Textual 注册主题：{success}/{len(names)}")
        except Exception as e:
            logger.debug(f"批量注册主题到 Textual 失败（可忽略）：{e}")