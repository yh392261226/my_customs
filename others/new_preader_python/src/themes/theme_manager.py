"""
主题管理器，负责处理应用程序的主题和样式
"""


import os
import json
import time
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
        self.theme_files = {}  # 存储主题文件路径和修改时间
        self.themes_dir = os.path.join(os.path.dirname(__file__), "data")
        
        # 加载所有主题
        self._load_all_themes()
        
        # 设置当前主题
        self.set_theme(default_theme)
    
    def _load_all_themes(self) -> None:
        """加载所有主题，包括内置主题和文件主题"""
        # 先加载内置主题作为后备
        self._load_builtin_themes()
        
        # 然后加载文件主题，会覆盖内置主题
        self._load_theme_files()
    
    def _load_theme_files(self) -> None:
        """从主题文件加载主题"""
        if not os.path.exists(self.themes_dir):
            os.makedirs(self.themes_dir, exist_ok=True)
            logger.info(f"创建主题目录: {self.themes_dir}")
            return
        
        logger.info(f"开始加载主题文件，目录: {self.themes_dir}")
        
        for filename in os.listdir(self.themes_dir):
            if filename.endswith('.theme'):
                theme_path = os.path.join(self.themes_dir, filename)
                try:
                    self._load_single_theme_file(theme_path)
                except Exception as e:
                    logger.error(f"加载主题文件失败 {filename}: {e}")
    
    def _load_single_theme_file(self, theme_path: str) -> None:
        """加载单个主题文件"""
        try:
            with open(theme_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            theme_name = theme_data.get('name')
            if not theme_name:
                logger.warning(f"主题文件缺少名称字段: {theme_path}")
                return
            
            # 解析样式
            styles = {}
            for style_name, style_config in theme_data.get('styles', {}).items():
                styles[style_name] = self._parse_style(style_config)
            
            # 存储主题
            self.themes[theme_name] = styles
            
            # 记录文件信息，用于监控变化
            self.theme_files[theme_name] = {
                'path': theme_path,
                'modified_time': os.path.getmtime(theme_path)
            }
            
            logger.info(f"成功加载主题: {theme_name} from {theme_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"主题文件JSON格式错误 {theme_path}: {e}")
        except Exception as e:
            logger.error(f"加载主题文件异常 {theme_path}: {e}")
    
    def _parse_style(self, style_config: Dict[str, Any]) -> Style:
        """解析样式配置为Style对象"""
        kwargs = {}
        
        # 处理颜色
        if 'color' in style_config:
            kwargs['color'] = style_config['color']
        
        # 处理背景色
        if 'bgcolor' in style_config:
            kwargs['bgcolor'] = style_config['bgcolor']
        
        # 处理样式属性
        for attr in ['bold', 'italic', 'underline', 'blink', 'reverse', 'strike']:
            if attr in style_config:
                kwargs[attr] = style_config[attr]
        
        return Style(**kwargs)
    
    def reload_theme_files(self) -> None:
        """重新加载主题文件，检测变化"""
        logger.info("开始重新加载主题文件")
        
        # 检查现有主题文件是否有更新
        updated_themes = []
        for theme_name, file_info in self.theme_files.items():
            theme_path = file_info['path']
            if os.path.exists(theme_path):
                current_modified = os.path.getmtime(theme_path)
                if current_modified > file_info['modified_time']:
                    logger.info(f"检测到主题文件更新: {theme_name}")
                    self._load_single_theme_file(theme_path)
                    updated_themes.append(theme_name)
        
        # 检查新增的主题文件
        existing_files = {info['path'] for info in self.theme_files.values()}
        for filename in os.listdir(self.themes_dir):
            if filename.endswith('.theme'):
                theme_path = os.path.join(self.themes_dir, filename)
                if theme_path not in existing_files:
                    logger.info(f"检测到新主题文件: {filename}")
                    self._load_single_theme_file(theme_path)
        
        # 检查删除的主题文件
        removed_themes = []
        for theme_name, file_info in list(self.theme_files.items()):
            if not os.path.exists(file_info['path']):
                logger.info(f"检测到主题文件删除: {theme_name}")
                # 如果是文件主题，从内存中删除
                if theme_name in self.themes and theme_name in self.theme_files:
                    del self.themes[theme_name]
                    del self.theme_files[theme_name]
                    removed_themes.append(theme_name)
        
        # 如果当前主题被删除，切换到默认主题
        if self.current_theme_name in removed_themes:
            logger.warning(f"当前主题 {self.current_theme_name} 已被删除，切换到默认主题")
            self.set_theme("dark")
        
        # 如果当前主题有更新，重新应用
        elif self.current_theme_name in updated_themes:
            logger.info(f"当前主题 {self.current_theme_name} 已更新，重新应用")
            # 主题已经重新加载，不需要额外操作
        
        logger.info(f"主题重新加载完成，当前可用主题: {list(self.themes.keys())}")
    
    def _load_builtin_themes(self) -> None:
        """加载所有内置主题（作为后备）
        
        注意：所有主题现在都通过文件加载，此方法保留仅为兼容性。
        """
        # 不再加载内置主题，所有主题都通过文件加载
        pass
    
    def get_available_themes(self) -> List[str]:
        """
        获取所有可用的主题名称
        
        Returns:
            List[str]: 主题名称列表
        """
        # 检查主题文件是否有更新
        self.reload_theme_files()
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
        # 首先检查主题文件是否有更新
        self.reload_theme_files()
        
        if theme_name not in self.themes:
            logger.error(f"主题不存在: {theme_name}")
            return False
        
        self.current_theme_name = theme_name
        logger.info(f"当前主题已设置为: {theme_name}")
        return True
    
    def get_theme_info(self, theme_name: str) -> Dict[str, Any]:
        """
        获取主题的详细信息
        
        Args:
            theme_name: 主题名称
            
        Returns:
            Dict[str, Any]: 主题信息，包括名称、显示名称、描述等
        """
        if theme_name not in self.themes:
            return {}
        
        # 如果是文件主题，读取详细信息
        if theme_name in self.theme_files:
            try:
                theme_path = self.theme_files[theme_name]['path']
                with open(theme_path, 'r', encoding='utf-8') as f:
                    theme_data = json.load(f)
                return {
                    'name': theme_data.get('name', theme_name),
                    'display_name': theme_data.get('display_name', theme_name),
                    'description': theme_data.get('description', ''),
                    'is_file_theme': True,
                    'path': theme_path
                }
            except Exception as e:
                logger.error(f"读取主题信息失败 {theme_name}: {e}")
        
        # 内置主题的默认信息
        return {
            'name': theme_name,
            'display_name': theme_name.title(),
            'description': f'{theme_name} 内置主题',
            'is_file_theme': False,
            'path': None
        }
    
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
        
        for style_name, style in theme.items():
            if hasattr(style, 'color') and style.color:
                colors[style_name] = self.convert_color_to_string(style.color)
            if hasattr(style, 'bgcolor') and style.bgcolor:
                colors[f"{style_name}_bg"] = self.convert_color_to_string(style.bgcolor)
        
        return colors
    
    def apply_theme_to_screen(self, screen) -> None:
        """
        将主题应用到屏幕
        
        Args:
            screen: 要应用主题的屏幕对象
        """
        if self.current_theme_name not in self.themes:
            logger.warning(f"当前主题不存在: {self.current_theme_name}")
            return
        
        # 首先应用Textual主题系统
        try:
            # 获取screen的app实例
            app = getattr(screen, 'app', None)
            if app:
                self.apply_textual_theme(app)
        except Exception as e:
            logger.debug(f"应用Textual主题失败（可忽略）：{e}")
        
        theme_config = self.themes[self.current_theme_name]
        
        # 应用基础样式
        app_title_style = theme_config.get("app.title")
        if app_title_style:
            screen.styles.set_rule(".app-title", f"color: {self.convert_color_to_string(app_title_style.color)}; font-weight: bold")
        
        # 应用UI样式
        ui_background_style = theme_config.get("ui.background")
        if ui_background_style:
            screen.styles.set_rule("Screen", f"background: {self.convert_color_to_string(ui_background_style.bgcolor)}")
        
        # 应用书架样式
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