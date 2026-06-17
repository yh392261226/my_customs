"""
主题管理器：基于 Textual 原生 Theme 系统的主题管理
"""

import os
import json
from typing import Dict, Any, List, Optional

from textual.theme import Theme as TextualTheme

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── 颜色工具函数 ──────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str):
    """将十六进制颜色转换为 RGB 元组"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _luminance(rgb) -> float:
    """计算 sRGB 颜色相对亮度"""
    def _linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _is_color_dark(hex_color: str) -> bool:
    """判断颜色是否为深色"""
    try:
        return _luminance(_hex_to_rgb(hex_color)) < 0.5
    except Exception:
        return True


def _lighten(hex_color: str, amount: float = 0.08) -> str:
    """将颜色变亮一定比例"""
    try:
        r, g, b = _hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * amount))
        g = min(255, int(g + (255 - g) * amount))
        b = min(255, int(b + (255 - b) * amount))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


def _darken(hex_color: str, amount: float = 0.075) -> str:
    """将颜色变暗一定比例"""
    try:
        r, g, b = _hex_to_rgb(hex_color)
        r = max(0, int(r * (1 - amount)))
        g = max(0, int(g * (1 - amount)))
        b = max(0, int(b * (1 - amount)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


def _mix_colors(c1: str, c2: str, ratio: float = 0.5) -> str:
    """混合两个颜色，ratio 为 c1 的权重"""
    try:
        r1, g1, b1 = _hex_to_rgb(c1)
        r2, g2, b2 = _hex_to_rgb(c2)
        r = int(r1 * ratio + r2 * (1 - ratio))
        g = int(g1 * ratio + g2 * (1 - ratio))
        b = int(b1 * ratio + b2 * (1 - ratio))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return c1


def _pick_color(styles: dict, keys: list, default: str = None) -> Optional[str]:
    """从 styles 字典中按优先级选取 color 值"""
    for key in keys:
        style = styles.get(key, {})
        if isinstance(style, dict) and style.get("color"):
            return style["color"]
    return default


def _pick_bgcolor(styles: dict, keys: list, default: str = None) -> Optional[str]:
    """从 styles 字典中按优先级选取 bgcolor 值"""
    for key in keys:
        style = styles.get(key, {})
        if isinstance(style, dict) and style.get("bgcolor"):
            return style["bgcolor"]
    return default


# ── 完整的 CSS 变量生成 ─────────────────────────────────────────────────────


def _build_complete_variables(
    primary: str,
    secondary: str,
    accent: str,
    warning: str,
    error: str,
    success: str,
    foreground: str,
    background: str,
    surface: str,
    panel: str,
    boost: str,
    dark: bool,
    name: str = "",
    existing_vars: dict = None,
) -> dict:
    """根据核心颜色生成完整的 CSS 变量字典

    包含项目中所有 .tcss 和 .py 文件用到的颜色变量，
    确保主题文件自给自足，不依赖 Textual 自动生成的不确定性。
    """
    existing = existing_vars or {}
    is_glass = "glass" in name.lower() or "transparent" in name.lower()
    cursor_bg = background if not is_glass else "#000000"

    def _keep_or(existing_key: str, computed: str) -> str:
        """保留已有的值或使用计算值"""
        return existing.get(existing_key, computed)

    variables = {}

    # ── 1. 核心颜色（.tcss 中的 $primary/$secondary 等直接引用）──
    variables["primary"] = primary
    variables["secondary"] = secondary
    variables["accent"] = accent
    variables["warning"] = warning
    variables["error"] = error
    variables["success"] = success
    variables["foreground"] = foreground
    variables["background"] = background
    variables["surface"] = surface
    variables["panel"] = panel
    variables["boost"] = boost

    # ── 2. 文本色系 ──
    variables["text"] = foreground
    variables["text-muted"] = _mix_colors(foreground, background, 0.65)
    variables["text-disabled"] = _mix_colors(foreground, background, 0.45)
    variables["text-primary"] = primary
    variables["text-secondary"] = secondary
    variables["text-warning"] = warning
    variables["text-error"] = error
    variables["text-success"] = success
    variables["text-accent"] = accent

    # ── 3. darken/lighten 变体（.tcss 中使用）──
    variables["primary-darken-1"] = _darken(primary, 0.075)
    variables["primary-lighten-1"] = _lighten(primary, 0.075)
    variables["surface-darken-1"] = _darken(surface, 0.075)
    variables["success-darken-1"] = _darken(success, 0.075)
    variables["panel-darken-1"] = _darken(panel, 0.075)

    # ── 4. Muted 变体 ──
    variables["primary-muted"] = _darken(primary, 0.3)
    variables["secondary-muted"] = _darken(secondary, 0.3)
    variables["accent-muted"] = _darken(accent, 0.3)
    variables["warning-muted"] = _darken(warning, 0.3)
    variables["error-muted"] = _darken(error, 0.3)
    variables["success-muted"] = _darken(success, 0.3)
    variables["foreground-muted"] = _mix_colors(foreground, background, 0.5)
    variables["foreground-disabled"] = _mix_colors(foreground, background, 0.35)

    # ── 5. 边框 ──
    variables["border"] = _keep_or("border", _mix_colors(primary, surface, 0.45))
    variables["border-blurred"] = _keep_or("border-blurred", _darken(surface, 0.025))

    # ── 6. 光标 ──
    variables["block-cursor-foreground"] = _keep_or("block-cursor-foreground", cursor_bg)
    variables["block-cursor-background"] = primary
    variables["block-cursor-text-style"] = "none"
    variables["block-cursor-blurred-foreground"] = foreground
    variables["block-cursor-blurred-background"] = f"{primary} 30%"

    variables["input-cursor-background"] = foreground
    variables["input-cursor-foreground"] = _keep_or("input-cursor-foreground", cursor_bg)
    variables["input-cursor-text-style"] = "reverse"
    variables["input-selection-background"] = f"{primary} 35%"
    variables["input-selection-foreground"] = foreground

    # ── 7. 滚动条 ──
    variables["scrollbar"] = primary
    variables["scrollbar-hover"] = primary
    variables["scrollbar-active"] = accent
    variables["scrollbar-background"] = surface
    variables["scrollbar-background-hover"] = surface
    variables["scrollbar-background-active"] = surface
    variables["scrollbar-corner-color"] = surface

    # ── 8. 块悬停 ──
    variables["block-hover-background"] = surface

    # ── 9. Footer ──
    variables["footer-foreground"] = foreground
    variables["footer-background"] = surface
    variables["footer-key-foreground"] = primary
    variables["footer-key-background"] = surface
    variables["footer-description-foreground"] = foreground
    variables["footer-description-background"] = surface
    variables["footer-item-background"] = surface

    # ── 10. Surface 激活态 ──
    variables["surface-active"] = _lighten(surface, 0.05)

    # ── 11. 链接样式 ──
    variables["link-background"] = "transparent"
    variables["link-background-hover"] = f"{primary} 10%"
    variables["link-color"] = primary
    variables["link-style"] = "underline"
    variables["link-color-hover"] = primary
    variables["link-style-hover"] = "bold underline"

    # ── 12. 选择高亮 ──
    variables["screen-selection-background"] = f"{primary} 35%"
    variables["screen-selection-foreground"] = foreground

    # ── 13. ANSI 终端色彩 ──
    variables["ansi-background"] = _keep_or("ansi-background", foreground)
    variables["ansi-foreground"] = _keep_or("ansi-foreground", cursor_bg)

    # ── 14. 按钮 ──
    variables["button-foreground"] = foreground
    variables["button-color-foreground"] = foreground

    # ── 15. Markdown 标题色 ──
    for i in range(1, 7):
        variables[f"markdown-h{i}-color"] = primary

    return variables


def _ensure_complete_variables(data: dict) -> dict:
    """确保新格式主题文件具有完整的变量定义

    修复 dark 标志，补充缺失的 CSS 变量。
    """
    name = data.get("name", "")
    is_glass = "glass" in name.lower() or "transparent" in name.lower()

    # 修复 dark 标志（如 light.theme 错写为 true）
    background = data.get("background", "#000000")
    if not is_glass:
        try:
            correct_dark = _is_color_dark(background)
            data["dark"] = correct_dark
        except Exception:
            pass
    dark = data.get("dark", True)

    # 提取核心颜色
    primary = data.get("primary", "#60A5FA")
    secondary = data.get("secondary", primary)
    accent = data.get("accent", secondary)
    warning = data.get("warning", "#F87171")
    error = data.get("error", warning)
    success = data.get("success", "#34D399")
    foreground = data.get("foreground", "#E5E7EB")
    surface = data.get("surface", "#1F2937")
    panel = data.get("panel", surface)
    boost = data.get("boost", surface)

    # 生成完整变量（保留已有变量值）
    existing_vars = data.get("variables", {})
    data["variables"] = _build_complete_variables(
        primary=primary,
        secondary=secondary,
        accent=accent,
        warning=warning,
        error=error,
        success=success,
        foreground=foreground,
        background=background,
        surface=surface,
        panel=panel,
        boost=boost,
        dark=dark,
        name=name,
        existing_vars=existing_vars,
    )

    return data


# ── 旧格式 → 新格式转换 ────────────────────────────────────────────────────

def _convert_old_theme(data: dict) -> dict:
    """将旧格式主题数据转换为 Textual Theme 兼容格式"""
    styles = data.get("styles", {})
    name = data.get("name", "unknown")

    primary = _pick_color(styles, ["app.accent", "app.primary"])
    secondary = _pick_color(styles, ["app.highlight", "app.secondary"])
    accent = _pick_color(styles, ["app.highlight", "app.accent"])
    warning = _pick_color(styles, ["app.warning"])
    error = _pick_color(styles, ["app.warning", "app.error"])
    success = _pick_color(styles, ["app.success"])
    foreground = _pick_color(styles, ["reader.text", "content.text"])
    background = _pick_bgcolor(styles, ["ui.background"])
    surface = _pick_bgcolor(styles, ["ui.panel"])
    panel = _pick_bgcolor(styles, ["ui.panel"])
    border = _pick_color(styles, ["ui.border"])
    muted = _pick_color(styles, ["app.muted"])
    info = _pick_color(styles, ["app.info"])

    # 背景为空表示玻璃/透明主题
    is_glass = "glass" in name or "transparent" in name
    if not background:
        background = ""
    if not surface:
        surface = ""

    # 判断 dark
    check_bg = background if background else ("#000000" if not is_glass else "#FFFFFF")
    dark = _is_color_dark(check_bg)

    # 默认值
    if not primary:
        primary = "#60A5FA" if dark else "#3B82F6"
    if not secondary:
        secondary = "#FBBF24" if dark else "#F59E0B"
    if not accent:
        accent = secondary
    if not warning:
        warning = "#F87171" if dark else "#EF4444"
    if not error:
        error = warning
    if not success:
        success = "#34D399" if dark else "#22C55E"
    if not foreground:
        foreground = "#E5E7EB" if dark else "#111827"
    if not background:
        background = "#00000000" if is_glass else ("#111827" if dark else "#FFFFFF")
    if not surface:
        surface = _darken(background) if background != "#00000000" else "#FFFFFF10"
    if not panel:
        panel = surface
    if not border:
        border = "#4B5563" if dark else "#D1D5DB"
    if not muted:
        muted = "#9CA3AF" if dark else "#6B7280"
    if not info:
        info = "#0EA5E9"

    boost = _lighten(surface) if not surface.startswith("#") or (len(surface) == 9 and surface.endswith("00")) else _lighten(surface)

    # 保留旧格式中的 border/muted 值用于 variables
    existing_vars = {}
    if border:
        existing_vars["border"] = border
    if muted:
        existing_vars["border-blurred"] = muted

    # 生成完整的 CSS 变量
    variables = _build_complete_variables(
        primary=primary,
        secondary=secondary,
        accent=accent,
        warning=warning,
        error=error,
        success=success,
        foreground=foreground,
        background=background,
        surface=surface,
        panel=panel,
        boost=boost,
        dark=dark,
        name=name,
        existing_vars=existing_vars,
    )

    return {
        "name": name,
        "display_name": data.get("display_name", name),
        "description": data.get("description", ""),
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "warning": warning,
        "error": error,
        "success": success,
        "foreground": foreground,
        "background": background,
        "surface": surface,
        "panel": panel,
        "boost": boost,
        "dark": dark,
        "luminosity_spread": 16.0,
        "text_alpha": 0.95,
        "variables": variables,
    }


class ThemeManager:
    """主题管理器类，基于 Textual 原生 Theme 系统"""

    def __init__(self, default_theme: str = "dark"):
        self._theme_objects: Dict[str, TextualTheme] = {}
        self._theme_data: Dict[str, dict] = {}  # 原始数据（含 display_name 等元信息）
        self._theme_files: Dict[str, dict] = {}  # 文件路径与修改时间
        self.current_theme_name: str = default_theme
        self._app = None  # Textual App 引用，在 register_with_textual 时设置

        self.themes_dir = os.path.join(os.path.dirname(__file__), "data")
        self._load_all_themes()

    # ── 加载 ──────────────────────────────────────────────────────────────

    def _load_all_themes(self) -> None:
        """加载所有主题文件"""
        if not os.path.exists(self.themes_dir):
            os.makedirs(self.themes_dir, exist_ok=True)
            logger.info(f"创建主题目录: {self.themes_dir}")
            return
        self._load_theme_files()

    def _load_theme_files(self) -> None:
        """从 data/ 目录加载所有 .theme 文件"""
        for filename in sorted(os.listdir(self.themes_dir)):
            if filename.endswith(".theme"):
                theme_path = os.path.join(self.themes_dir, filename)
                try:
                    self._load_single_theme_file(theme_path)
                except Exception as e:
                    logger.error(f"加载主题文件失败 {filename}: {e}")

    def _load_single_theme_file(self, theme_path: str) -> None:
        """加载单个主题文件（自动兼容新旧格式，并补全变量）"""
        with open(theme_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        theme_name = data.get("name")
        if not theme_name:
            logger.warning(f"主题文件缺少 name: {theme_path}")
            return

        # 检测是否为新格式
        if "primary" in data and "dark" in data and "styles" not in data:
            # 已是新格式，但需要确保变量完整
            theme_data = _ensure_complete_variables(data)
        else:
            # 旧格式，自动转换
            theme_data = _convert_old_theme(data)

        # 创建 Textual Theme 对象
        theme_obj = TextualTheme(
            name=theme_data["name"],
            primary=theme_data["primary"],
            secondary=theme_data.get("secondary", theme_data["primary"]),
            warning=theme_data.get("warning", theme_data["primary"]),
            error=theme_data.get("error", theme_data.get("warning", theme_data["primary"])),
            success=theme_data.get("success", theme_data["primary"]),
            accent=theme_data.get("accent", theme_data.get("secondary", theme_data["primary"])),
            foreground=theme_data.get("foreground", "#FFFFFF"),
            background=theme_data.get("background", "#000000"),
            surface=theme_data.get("surface", theme_data.get("background", "#111827")),
            panel=theme_data.get("panel", theme_data.get("surface", "#111827")),
            boost=theme_data.get("boost", theme_data.get("surface", "#1F2937")),
            dark=theme_data.get("dark", True),
            luminosity_spread=theme_data.get("luminosity_spread", 16.0),
            text_alpha=theme_data.get("text_alpha", 0.95),
            variables=theme_data.get("variables", {}),
        )

        self._theme_objects[theme_name] = theme_obj
        self._theme_data[theme_name] = theme_data
        self._theme_files[theme_name] = {
            "path": theme_path,
            "modified_time": os.path.getmtime(theme_path),
        }

    # ── Textual 集成 ──────────────────────────────────────────────────────

    def register_with_textual(self, app) -> None:
        """向 Textual App 注册所有主题"""
        self._app = app
        for name, theme_obj in self._theme_objects.items():
            try:
                app.register_theme(theme_obj)
            except Exception as e:
                logger.debug(f"注册主题 {name} 失败: {e}")
        logger.info(f"已注册 {len(self._theme_objects)} 个主题到 Textual")

        # 设置当前主题
        self._apply_to_app(app, self.current_theme_name)

    def _apply_to_app(self, app, theme_name: str) -> bool:
        """直接设置 app.theme"""
        if theme_name not in self._theme_objects:
            logger.error(f"主题不存在: {theme_name}")
            return False
        try:
            app.theme = theme_name
            return True
        except Exception as e:
            logger.error(f"应用主题失败 {theme_name}: {e}")
            return False

    def set_theme(self, theme_name: str) -> bool:
        """设置当前主题名称（不直接应用到 App，由调用方负责）"""
        self.reload_theme_files()
        if theme_name not in self._theme_objects:
            logger.error(f"主题不存在: {theme_name}")
            return False
        self.current_theme_name = theme_name
        logger.info(f"当前主题已设置为: {theme_name}")
        return True

    def apply_theme_to_screen(self, screen) -> None:
        """将当前主题应用到屏幕（通过 App）"""
        app = getattr(screen, "app", None) or self._app
        if app and self.current_theme_name in self._theme_objects:
            try:
                # 先确保主题已注册
                try:
                    app.register_theme(self._theme_objects[self.current_theme_name])
                except Exception:
                    pass
                app.theme = self.current_theme_name
            except Exception as e:
                logger.debug(f"应用主题到屏幕失败: {e}")
        try:
            screen.refresh()
        except Exception:
            pass

    def apply_theme_to_app(self, app) -> None:
        """将当前主题应用到 App 并刷新所有屏幕"""
        if self.current_theme_name not in self._theme_objects:
            return
        try:
            try:
                app.register_theme(self._theme_objects[self.current_theme_name])
            except Exception:
                pass
            app.theme = self.current_theme_name
        except Exception as e:
            logger.debug(f"应用主题到 App 失败: {e}")
        try:
            app.refresh(layout=True)
        except Exception:
            try:
                app.refresh()
            except Exception:
                pass

    # ── 查询 ──────────────────────────────────────────────────────────────

    def get_available_themes(self) -> List[str]:
        """获取所有可用的主题名称"""
        self.reload_theme_files()
        return sorted(self._theme_objects.keys())

    def get_current_theme_name(self) -> str:
        """获取当前主题名称"""
        return self.current_theme_name

    def get_theme_info(self, theme_name: str) -> Dict[str, Any]:
        """获取主题详细信息"""
        if theme_name not in self._theme_data:
            return {}
        data = self._theme_data[theme_name]
        file_info = self._theme_files.get(theme_name, {})
        return {
            "name": data.get("name", theme_name),
            "display_name": data.get("display_name", theme_name),
            "description": data.get("description", ""),
            "dark": data.get("dark", True),
            "path": file_info.get("path"),
        }

    def get_theme_object(self, theme_name: str = None) -> Optional[TextualTheme]:
        """获取指定名称的 Textual Theme 对象"""
        name = theme_name or self.current_theme_name
        return self._theme_objects.get(name)

    def get_simple_theme_colors(self, theme_name: str) -> tuple:
        """获取简单的主题颜色（无 theme_manager 时的备用方案）"""
        if theme_name in self._theme_data:
            data = self._theme_data[theme_name]
            return data.get("background", "#000000"), data.get("foreground", "#FFFFFF")
        if "light" in theme_name.lower():
            return "#FFFFFF", "#000000"
        return "#000000", "#FFFFFF"

    # ── 热更新 ────────────────────────────────────────────────────────────

    def reload_theme_files(self) -> None:
        """重新扫描主题文件目录，处理增删改"""
        # 检查现有文件变更
        for theme_name, file_info in list(self._theme_files.items()):
            theme_path = file_info["path"]
            if os.path.exists(theme_path):
                current_mtime = os.path.getmtime(theme_path)
                if current_mtime > file_info["modified_time"]:
                    logger.info(f"检测到主题文件更新: {theme_name}")
                    self._load_single_theme_file(theme_path)

        # 检查新增文件
        existing = {info["path"] for info in self._theme_files.values()}
        for filename in sorted(os.listdir(self.themes_dir)):
            if filename.endswith(".theme"):
                theme_path = os.path.join(self.themes_dir, filename)
                if theme_path not in existing:
                    logger.info(f"检测到新主题文件: {filename}")
                    self._load_single_theme_file(theme_path)

        # 检查删除
        removed = []
        for theme_name, file_info in list(self._theme_files.items()):
            if not os.path.exists(file_info["path"]):
                removed.append(theme_name)
        for name in removed:
            logger.info(f"检测到主题文件删除: {name}")
            self._theme_objects.pop(name, None)
            self._theme_data.pop(name, None)
            self._theme_files.pop(name, None)

        if removed and self.current_theme_name in removed:
            logger.warning(f"当前主题 {self.current_theme_name} 已删除，回退到 dark")
            self.current_theme_name = "dark"


# 保持向后兼容：导出 ThemeManager 类
__all__ = ["ThemeManager"]
