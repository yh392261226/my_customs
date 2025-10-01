"""
主题管理器，负责处理应用程序的主题和样式
"""


from typing import Dict, Any, List, Optional

from rich.style import Style
from rich.color import Color
from rich.theme import Theme as RichTheme

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
            "app.title": Style(color="bright_white", bold=True),
            "app.subtitle": Style(color="grey70"),
            "app.accent": Style(color="bright_blue"),
            "app.highlight": Style(color="bright_yellow"),
            "app.warning": Style(color="bright_red"),
            "app.success": Style(color="bright_green"),
            "app.info": Style(color="bright_cyan"),
            "app.muted": Style(color="grey50"),
            
            "ui.border": Style(color="grey50"),
            "ui.background": Style(bgcolor="black"),
            "ui.panel": Style(bgcolor="grey15"),
            "ui.panel.title": Style(color="bright_white", bold=True),
            "ui.label": Style(color="grey85"),
            "ui.button": Style(color="black", bgcolor="grey70"),
            "ui.button.primary": Style(color="white", bgcolor="bright_blue"),
            "ui.button.success": Style(color="white", bgcolor="bright_green"),
            "ui.button.warning": Style(color="white", bgcolor="bright_yellow"),
            "ui.button.danger": Style(color="white", bgcolor="bright_red"),
            "ui.input": Style(color="white", bgcolor="grey23"),
            "ui.input.focus": Style(color="white", bgcolor="grey30"),
            "ui.selection": Style(bgcolor="grey23"),
            
            "content.text": Style(color="grey85"),
            "content.heading": Style(color="bright_white", bold=True),
            "content.subheading": Style(color="grey70", bold=True),
            "content.link": Style(color="bright_blue", underline=True),
            "content.quote": Style(color="grey70", italic=True),
            "content.code": Style(color="bright_green", bgcolor="grey15"),
            "content.highlight": Style(color="black", bgcolor="bright_yellow"),
            
            "progress.bar": Style(color="bright_blue"),
            "progress.text": Style(color="grey70"),
            "progress.percentage": Style(color="bright_white"),
            
            "bookshelf.title": Style(color="bright_white", bold=True),
            "bookshelf.author": Style(color="grey70"),
            "bookshelf.progress": Style(color="bright_blue"),
            "bookshelf.tag": Style(color="grey50", bgcolor="grey23"),
            "bookshelf.selected": Style(bgcolor="grey23"),
            
            "reader.text": Style(color="grey85"),
            "reader.chapter": Style(color="bright_white", bold=True),
            "reader.page_number": Style(color="grey50"),
            "reader.bookmark": Style(color="bright_yellow"),
            "reader.search_result": Style(color="black", bgcolor="bright_yellow"),
        }
        
        # 加载浅色主题
        self.themes["light"] = {
            "app.title": Style(color="black", bold=True),
            "app.subtitle": Style(color="grey50"),
            "app.accent": Style(color="blue"),
            "app.highlight": Style(color="yellow4"),
            "app.warning": Style(color="red"),
            "app.success": Style(color="green"),
            "app.info": Style(color="cyan"),
            "app.muted": Style(color="grey50"),
            
            "ui.border": Style(color="grey50"),
            "ui.background": Style(bgcolor="white"),
            "ui.panel": Style(bgcolor="grey93"),
            "ui.panel.title": Style(color="black", bold=True),
            "ui.label": Style(color="grey15"),
            "ui.button": Style(color="white", bgcolor="grey50"),
            "ui.button.primary": Style(color="white", bgcolor="blue"),
            "ui.button.success": Style(color="white", bgcolor="green"),
            "ui.button.warning": Style(color="white", bgcolor="yellow4"),
            "ui.button.danger": Style(color="white", bgcolor="red"),
            "ui.input": Style(color="black", bgcolor="grey85"),
            "ui.input.focus": Style(color="black", bgcolor="grey78"),
            "ui.selection": Style(bgcolor="grey85"),
            
            "content.text": Style(color="grey15"),
            "content.heading": Style(color="black", bold=True),
            "content.subheading": Style(color="grey30", bold=True),
            "content.link": Style(color="blue", underline=True),
            "content.quote": Style(color="grey30", italic=True),
            "content.code": Style(color="green", bgcolor="grey93"),
            "content.highlight": Style(color="white", bgcolor="yellow4"),
            
            "progress.bar": Style(color="blue"),
            "progress.text": Style(color="grey30"),
            "progress.percentage": Style(color="black"),
            
            "bookshelf.title": Style(color="black", bold=True),
            "bookshelf.author": Style(color="grey30"),
            "bookshelf.progress": Style(color="blue"),
            "bookshelf.tag": Style(color="grey50", bgcolor="grey85"),
            "bookshelf.selected": Style(bgcolor="grey85"),
            
            "reader.text": Style(color="grey15"),
            "reader.chapter": Style(color="black", bold=True),
            "reader.page_number": Style(color="grey50"),
            "reader.bookmark": Style(color="yellow4"),
            "reader.search_result": Style(color="white", bgcolor="yellow4"),
        }
        
        # 加载Nord主题
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
            "ui.background": Style(bgcolor="#2E3440"),
            "ui.panel": Style(bgcolor="#3B4252"),
            "ui.panel.title": Style(color="#ECEFF4", bold=True),
            "ui.label": Style(color="#E5E9F0"),
            "ui.button": Style(color="#2E3440", bgcolor="#D8DEE9"),
            "ui.button.primary": Style(color="#ECEFF4", bgcolor="#5E81AC"),
            "ui.button.success": Style(color="#ECEFF4", bgcolor="#A3BE8C"),
            "ui.button.warning": Style(color="#2E3440", bgcolor="#EBCB8B"),
            "ui.button.danger": Style(color="#ECEFF4", bgcolor="#BF616A"),
            "ui.input": Style(color="#ECEFF4", bgcolor="#434C5E"),
            "ui.input.focus": Style(color="#ECEFF4", bgcolor="#4C566A"),
            "ui.selection": Style(bgcolor="#434C5E"),
            
            "content.text": Style(color="#E5E9F0"),
            "content.heading": Style(color="#ECEFF4", bold=True),
            "content.subheading": Style(color="#D8DEE9", bold=True),
            "content.link": Style(color="#88C0D0", underline=True),
            "content.quote": Style(color="#D8DEE9", italic=True),
            "content.code": Style(color="#A3BE8C", bgcolor="#3B4252"),
            "content.highlight": Style(color="#2E3440", bgcolor="#EBCB8B"),
            
            "progress.bar": Style(color="#88C0D0"),
            "progress.text": Style(color="#D8DEE9"),
            "progress.percentage": Style(color="#ECEFF4"),
            
            "bookshelf.title": Style(color="#ECEFF4", bold=True),
            "bookshelf.author": Style(color="#D8DEE9"),
            "bookshelf.progress": Style(color="#88C0D0"),
            "bookshelf.tag": Style(color="#D8DEE9", bgcolor="#434C5E"),
            "bookshelf.selected": Style(bgcolor="#434C5E"),
            
            "reader.text": Style(color="#E5E9F0"),
            "reader.chapter": Style(color="#ECEFF4", bold=True),
            "reader.page_number": Style(color="#4C566A"),
            "reader.bookmark": Style(color="#EBCB8B"),
            "reader.search_result": Style(color="#2E3440", bgcolor="#EBCB8B"),
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
            "ui.label": Style(color="#F8F8F2"),
            "ui.button": Style(color="#282A36", bgcolor="#BFBFBF"),
            "ui.button.primary": Style(color="#F8F8F2", bgcolor="#BD93F9"),
            "ui.button.success": Style(color="#F8F8F2", bgcolor="#50FA7B"),
            "ui.button.warning": Style(color="#282A36", bgcolor="#F1FA8C"),
            "ui.button.danger": Style(color="#F8F8F2", bgcolor="#FF5555"),
            "ui.input": Style(color="#F8F8F2", bgcolor="#44475A"),
            "ui.input.focus": Style(color="#F8F8F2", bgcolor="#6272A4"),
            "ui.selection": Style(bgcolor="#44475A"),
            
            "content.text": Style(color="#F8F8F2"),
            "content.heading": Style(color="#F8F8F2", bold=True),
            "content.subheading": Style(color="#BFBFBF", bold=True),
            "content.link": Style(color="#8BE9FD", underline=True),
            "content.quote": Style(color="#BFBFBF", italic=True),
            "content.code": Style(color="#50FA7B", bgcolor="#44475A"),
            "content.highlight": Style(color="#282A36", bgcolor="#F1FA8C"),
            
            "progress.bar": Style(color="#BD93F9"),
            "progress.text": Style(color="#BFBFBF"),
            "progress.percentage": Style(color="#F8F8F2"),
            
            "bookshelf.title": Style(color="#F8F8F2", bold=True),
            "bookshelf.author": Style(color="#BFBFBF"),
            "bookshelf.progress": Style(color="#BD93F9"),
            "bookshelf.tag": Style(color="#BFBFBF", bgcolor="#44475A"),
            "bookshelf.selected": Style(bgcolor="#44475A"),
            
            "reader.text": Style(color="#F8F8F2"),
            "reader.chapter": Style(color="#F8F8F2", bold=True),
            "reader.page_number": Style(color="#6272A4"),
            "reader.bookmark": Style(color="#F1FA8C"),
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
            "ui.panel.title": Style(color="#FFFFFF", bold=True),
            "ui.label": Style(color="#E0E0E0"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#546E7A"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#009688"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#00E676"),
            "ui.button.warning": Style(color="#212121", bgcolor="#FFD600"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF5252"),
            "ui.input": Style(color="#FFFFFF", bgcolor="#455A64"),
            "ui.input.focus": Style(color="#FFFFFF", bgcolor="#546E7A"),
            "ui.selection": Style(bgcolor="#455A64"),
            
            "content.text": Style(color="#E0E0E0"),
            "content.heading": Style(color="#FFFFFF", bold=True),
            "content.subheading": Style(color="#B0BEC5", bold=True),
            "content.link": Style(color="#80CBC4", underline=True),
            "content.quote": Style(color="#B0BEC5", italic=True),
            "content.code": Style(color="#69F0AE", bgcolor="#37474F"),
            "content.highlight": Style(color="#212121", bgcolor="#FFD600"),
            
            "progress.bar": Style(color="#80CBC4"),
            "progress.text": Style(color="#B0BEC5"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#FFFFFF", bold=True),
            "bookshelf.author": Style(color="#B0BEC5"),
            "bookshelf.progress": Style(color="#80CBC4"),
            "bookshelf.tag": Style(color="#B0BEC5", bgcolor="#455A64"),
            "bookshelf.selected": Style(bgcolor="#455A64"),
            
            "reader.text": Style(color="#E0E0E0"),
            "reader.chapter": Style(color="#FFFFFF", bold=True),
            "reader.page_number": Style(color="#546E7A"),
            "reader.bookmark": Style(color="#FFD600"),
            "reader.search_result": Style(color="#212121", bgcolor="#FFD600"),
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
            "ui.panel.title": Style(color="#FFFFFF", bold=True),
            "ui.label": Style(color="#F0F6FC"),
            "ui.button": Style(color="#F0F6FC", bgcolor="#21262D"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#238636"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#3FB950"),
            "ui.button.warning": Style(color="#0D1117", bgcolor="#D29922"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#DA3633"),
            "ui.input": Style(color="#F0F6FC", bgcolor="#161B22"),
            "ui.input.focus": Style(color="#F0F6FC", bgcolor="#21262D"),
            "ui.selection": Style(bgcolor="#161B22"),
            
            "content.text": Style(color="#F0F6FC"),
            "content.heading": Style(color="#FFFFFF", bold=True),
            "content.subheading": Style(color="#8B949E", bold=True),
            "content.link": Style(color="#58A6FF", underline=True),
            "content.quote": Style(color="#8B949E", italic=True),
            "content.code": Style(color="#3FB950", bgcolor="#161B22"),
            "content.highlight": Style(color="#0D1117", bgcolor="#D29922"),
            
            "progress.bar": Style(color="#58A6FF"),
            "progress.text": Style(color="#8B949E"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#FFFFFF", bold=True),
            "bookshelf.author": Style(color="#8B949E"),
            "bookshelf.progress": Style(color="#58A6FF"),
            "bookshelf.tag": Style(color="#8B949E", bgcolor="#161B22"),
            "bookshelf.selected": Style(bgcolor="#161B22"),
            
            "reader.text": Style(color="#F0F6FC"),
            "reader.chapter": Style(color="#FFFFFF", bold=True),
            "reader.page_number": Style(color="#6E7681"),
            "reader.bookmark": Style(color="#D29922"),
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
            "ui.panel.title": Style(color="#FDF6E3", bold=True),
            "ui.label": Style(color="#EEE8D5"),
            "ui.button": Style(color="#002B36", bgcolor="#93A1A1"),
            "ui.button.primary": Style(color="#FDF6E3", bgcolor="#268BD2"),
            "ui.button.success": Style(color="#FDF6E3", bgcolor="#859900"),
            "ui.button.warning": Style(color="#002B36", bgcolor="#B58900"),
            "ui.button.danger": Style(color="#FDF6E3", bgcolor="#DC322F"),
            "ui.input": Style(color="#EEE8D5", bgcolor="#073642"),
            "ui.input.focus": Style(color="#EEE8D5", bgcolor="#586E75"),
            "ui.selection": Style(bgcolor="#073642"),
            
            "content.text": Style(color="#EEE8D5"),
            "content.heading": Style(color="#FDF6E3", bold=True),
            "content.subheading": Style(color="#93A1A1", bold=True),
            "content.link": Style(color="#268BD2", underline=True),
            "content.quote": Style(color="#93A1A1", italic=True),
            "content.code": Style(color="#859900", bgcolor="#073642"),
            "content.highlight": Style(color="#002B36", bgcolor="#B58900"),
            
            "progress.bar": Style(color="#268BD2"),
            "progress.text": Style(color="#93A1A1"),
            "progress.percentage": Style(color="#FDF6E3"),
            
            "bookshelf.title": Style(color="#FDF6E3", bold=True),
            "bookshelf.author": Style(color="#93A1A1"),
            "bookshelf.progress": Style(color="#268BD2"),
            "bookshelf.tag": Style(color="#93A1A1", bgcolor="#073642"),
            "bookshelf.selected": Style(bgcolor="#073642"),
            
            "reader.text": Style(color="#EEE8D5"),
            "reader.chapter": Style(color="#FDF6E3", bold=True),
            "reader.page_number": Style(color="#586E75"),
            "reader.bookmark": Style(color="#B58900"),
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
            "ui.panel.title": Style(color="#FFFFFF", bold=True),
            "ui.label": Style(color="#E0D6FF"),
            "ui.button": Style(color="#2D1B69", bgcolor="#C5B4E3"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#9A77CF"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#6BCB77"),
            "ui.button.warning": Style(color="#2D1B69", bgcolor="#FFD700"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF6B6B"),
            "ui.input": Style(color="#E0D6FF", bgcolor="#3A2A7A"),
            "ui.input.focus": Style(color="#E0D6FF", bgcolor="#4A3A8A"),
            "ui.selection": Style(bgcolor="#3A2A7A"),
            
            "content.text": Style(color="#E0D6FF"),
            "content.heading": Style(color="#FFFFFF", bold=True),
            "content.subheading": Style(color="#C5B4E3", bold=True),
            "content.link": Style(color="#9A77CF", underline=True),
            "content.quote": Style(color="#C5B4E3", italic=True),
            "content.code": Style(color="#6BCB77", bgcolor="#3A2A7A"),
            "content.highlight": Style(color="#2D1B69", bgcolor="#FFD700"),
            
            "progress.bar": Style(color="#9A77CF"),
            "progress.text": Style(color="#C5B4E3"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#FFFFFF", bold=True),
            "bookshelf.author": Style(color="#C5B4E3"),
            "bookshelf.progress": Style(color="#9A77CF"),
            "bookshelf.tag": Style(color="#C5B4E3", bgcolor="#3A2A7A"),
            "bookshelf.selected": Style(bgcolor="#3A2A7A"),
            
            "reader.text": Style(color="#E0D6FF"),
            "reader.chapter": Style(color="#FFFFFF", bold=True),
            "reader.page_number": Style(color="#6D5D8F"),
            "reader.bookmark": Style(color="#FFD700"),
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
            "ui.panel.title": Style(color="#FFFFFF", bold=True),
            "ui.label": Style(color="#E8F5E9"),
            "ui.button": Style(color="#1B5E20", bgcolor="#A5D6A7"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#4CAF50"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#66BB6A"),
            "ui.button.warning": Style(color="#1B5E20", bgcolor="#FFEB3B"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#F44336"),
            "ui.input": Style(color="#E8F5E9", bgcolor="#2E7D32"),
            "ui.input.focus": Style(color="#E8F5E9", bgcolor="#388E3C"),
            "ui.selection": Style(bgcolor="#2E7D32"),
            
            "content.text": Style(color="#E8F5E9"),
            "content.heading": Style(color="#FFFFFF", bold=True),
            "content.subheading": Style(color="#A5D6A7", bold=True),
            "content.link": Style(color="#4CAF50", underline=True),
            "content.quote": Style(color="#A5D6A7", italic=True),
            "content.code": Style(color="#66BB6A", bgcolor="#2E7D32"),
            "content.highlight": Style(color="#1B5E20", bgcolor="#FFEB3B"),
            
            "progress.bar": Style(color="#4CAF50"),
            "progress.text": Style(color="#A5D6A7"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#FFFFFF", bold=True),
            "bookshelf.author": Style(color="#A5D6A7"),
            "bookshelf.progress": Style(color="#4CAF50"),
            "bookshelf.tag": Style(color="#A5D6A7", bgcolor="#2E7D32"),
            "bookshelf.selected": Style(bgcolor="#2E7D32"),
            
            "reader.text": Style(color="#E8F5E9"),
            "reader.chapter": Style(color="#FFFFFF", bold=True),
            "reader.page_number": Style(color="#2E7D32"),
            "reader.bookmark": Style(color="#FFEB3B"),
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
            "ui.panel.title": Style(color="#FFFFFF", bold=True),
            "ui.label": Style(color="#FFE4E1"),
            "ui.button": Style(color="#800000", bgcolor="#FFCCCB"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#DC143C"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#32CD32"),
            "ui.button.warning": Style(color="#800000", bgcolor="#FFD700"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF4500"),
            "ui.input": Style(color="#FFE4E1", bgcolor="#8B0000"),
            "ui.input.focus": Style(color="#FFE4E1", bgcolor="#A52A2A"),
            "ui.selection": Style(bgcolor="#8B0000"),
            
            "content.text": Style(color="#FFE4E1"),
            "content.heading": Style(color="#FFFFFF", bold=True),
            "content.subheading": Style(color="#FFCCCB", bold=True),
            "content.link": Style(color="#DC143C", underline=True),
            "content.quote": Style(color="#FFCCCB", italic=True),
            "content.code": Style(color="#32CD32", bgcolor="#8B0000"),
            "content.highlight": Style(color="#800000", bgcolor="#FFD700"),
            
            "progress.bar": Style(color="#DC143C"),
            "progress.text": Style(color="#FFCCCB"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#FFFFFF", bold=True),
            "bookshelf.author": Style(color="#FFCCCB"),
            "bookshelf.progress": Style(color="#DC143C"),
            "bookshelf.tag": Style(color="#FFCCCB", bgcolor="#8B0000"),
            "bookshelf.selected": Style(bgcolor="#8B0000"),
            
            "reader.text": Style(color="#FFE4E1"),
            "reader.chapter": Style(color="#FFFFFF", bold=True),
            "reader.page_number": Style(color="#8B0000"),
            "reader.bookmark": Style(color="#FFD700"),
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
            "ui.panel.title": Style(color="#FFFFFF", bold=True),
            "ui.label": Style(color="#F5F5F5"),
            "ui.button": Style(color="#2F4F4F", bgcolor="#B0B0B0"),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#708090"),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#3CB371"),
            "ui.button.warning": Style(color="#2F4F4F", bgcolor="#FFA500"),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#FF6347"),
            "ui.input": Style(color="#F5F5F5", bgcolor="#36454F"),
            "ui.input.focus": Style(color="#F5F5F5", bgcolor="#556B2F"),
            "ui.selection": Style(bgcolor="#36454F"),
            
            "content.text": Style(color="#F5F5F5"),
            "content.heading": Style(color="#FFFFFF", bold=True),
            "content.subheading": Style(color="#B0B0B0", bold=True),
            "content.link": Style(color="#708090", underline=True),
            "content.quote": Style(color="#B0B0B0", italic=True),
            "content.code": Style(color="#3CB371", bgcolor="#36454F"),
            "content.highlight": Style(color="#2F4F4F", bgcolor="#FFA500"),
            
            "progress.bar": Style(color="#708090"),
            "progress.text": Style(color="#B0B0B0"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#FFFFFF", bold=True),
            "bookshelf.author": Style(color="#B0B0B0"),
            "bookshelf.progress": Style(color="#708090"),
            "bookshelf.tag": Style(color="#B0B0B0", bgcolor="#36454F"),
            "bookshelf.selected": Style(bgcolor="#36454F"),
            
            "reader.text": Style(color="#F5F5F5"),
            "reader.chapter": Style(color="#FFFFFF", bold=True),
            "reader.page_number": Style(color="#556B2F"),
            "reader.bookmark": Style(color="#FFA500"),
            "reader.search_result": Style(color="#2F4F4F", bgcolor="#FFA500"),
        }

        # 加载透明暗色主题
        self.themes["transparent-dark"] = {
            "app.title": Style(color="#FFFFFF", bold=True),
            "app.subtitle": Style(color="#CCCCCC"),
            "app.accent": Style(color="#5D9CEC"),
            "app.highlight": Style(color="#FAC51C"),
            "app.warning": Style(color="#DA4453"),
            "app.success": Style(color="#37BC9B"),
            "app.info": Style(color="#3BAFDA"),
            "app.muted": Style(color="#656D78"),
            
            "ui.border": Style(color="#434A54", dim=True),
            "ui.background": Style(bgcolor="black", dim=True),
            "ui.panel": Style(bgcolor="#2F2F2F", dim=True),
            "ui.panel.title": Style(color="#FFFFFF", bold=True),
            "ui.label": Style(color="#E6E9ED"),
            "ui.button": Style(color="#FFFFFF", bgcolor="#434A54", dim=True),
            "ui.button.primary": Style(color="#FFFFFF", bgcolor="#5D9CEC", dim=True),
            "ui.button.success": Style(color="#FFFFFF", bgcolor="#37BC9B", dim=True),
            "ui.button.warning": Style(color="#FFFFFF", bgcolor="#F6BB42", dim=True),
            "ui.button.danger": Style(color="#FFFFFF", bgcolor="#DA4453", dim=True),
            "ui.input": Style(color="#FFFFFF", bgcolor="#2F2F2F", dim=True),
            "ui.input.focus": Style(color="#FFFFFF", bgcolor="#434A54", dim=True),
            "ui.selection": Style(bgcolor="#2F2F2F", dim=True),
            
            "content.text": Style(color="#E6E9ED"),
            "content.heading": Style(color="#FFFFFF", bold=True),
            "content.subheading": Style(color="#CCCCCC", bold=True),
            "content.link": Style(color="#5D9CEC", underline=True),
            "content.quote": Style(color="#CCCCCC", italic=True),
            "content.code": Style(color="#37BC9B", bgcolor="#2F2F2F", dim=True),
            "content.highlight": Style(color="#000000", bgcolor="#FAC51C"),
            
            "progress.bar": Style(color="#5D9CEC", dim=True),
            "progress.text": Style(color="#CCCCCC"),
            "progress.percentage": Style(color="#FFFFFF"),
            
            "bookshelf.title": Style(color="#FFFFFF", bold=True),
            "bookshelf.author": Style(color="#CCCCCC"),
            "bookshelf.progress": Style(color="#5D9CEC"),
            "bookshelf.tag": Style(color="#CCCCCC", bgcolor="#2F2F2F", dim=True),
            "bookshelf.selected": Style(bgcolor="#2F2F2F", dim=True),
            
            "reader.text": Style(color="#E6E9ED"),
            "reader.chapter": Style(color="#FFFFFF", bold=True),
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
            "content.highlight": Style(color="#FFFFFF", bgcolor="#F6BB42"),
            
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
            "reader.search_result": Style(color="#FFFFFF", bgcolor="#F6BB42"),
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
            
        # 使用Textual内置的主题支持
        if self.current_theme_name in ["dark", "dracula", "nord"]:
            screen.app.dark = True
        else:
            screen.app.dark = False
            
        # 刷新屏幕以应用主题变化
        screen.refresh()