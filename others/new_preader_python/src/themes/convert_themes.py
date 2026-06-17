"""
主题文件转换工具：将旧格式的 .theme 文件转换为 Textual Theme 兼容格式

旧格式：
{
    "name": "...",
    "display_name": "...",
    "description": "...",
    "styles": {
        "app.title": {"color": "...", "bold": true},
        ...
    }
}

新格式：
{
    "name": "...",
    "display_name": "...",
    "description": "...",
    "primary": "#...",
    "secondary": "#...",
    "accent": "#...",
    "warning": "#...",
    "error": "#...",
    "success": "#...",
    "foreground": "#...",
    "background": "#...",
    "surface": "#...",
    "panel": "#...",
    "boost": "#...",
    "dark": true/false,
    "luminosity_spread": 16.0,
    "text_alpha": 0.95,
    "variables": {
        "block-cursor-foreground": "...",
        ...
    }
}
"""

import json
import os
import math


def hex_to_rgb(hex_color: str) -> tuple:
    """将十六进制颜色转换为 RGB 元组"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def luminance(rgb: tuple) -> float:
    """计算颜色的相对亮度 (sRGB)"""
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def is_dark(hex_color: str) -> bool:
    """判断颜色是否为深色"""
    try:
        return luminance(hex_to_rgb(hex_color)) < 0.5
    except Exception:
        return True  # 默认深色


def lighten(hex_color: str, amount: float = 0.08) -> str:
    """将颜色变亮一定比例"""
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * amount))
        g = min(255, int(g + (255 - g) * amount))
        b = min(255, int(b + (255 - b) * amount))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


def darken(hex_color: str, amount: float = 0.06) -> str:
    """将颜色变暗一定比例"""
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = max(0, int(r * (1 - amount)))
        g = max(0, int(g * (1 - amount)))
        b = max(0, int(b * (1 - amount)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


def pick_color(styles: dict, keys: list, default: str = None) -> str:
    """从 styles 中按优先级选取颜色值"""
    for key in keys:
        style = styles.get(key, {})
        if style and 'color' in style:
            return style['color']
    return default


def pick_bgcolor(styles: dict, keys: list, default: str = None) -> str:
    """从 styles 中按优先级选取背景色"""
    for key in keys:
        style = styles.get(key, {})
        if style and 'bgcolor' in style:
            return style['bgcolor']
    return default


def mix_colors(c1: str, c2: str, ratio: float = 0.5) -> str:
    """混合两个颜色"""
    try:
        r1, g1, b1 = hex_to_rgb(c1)
        r2, g2, b2 = hex_to_rgb(c2)
        r = int(r1 * ratio + r2 * (1 - ratio))
        g = int(g1 * ratio + g2 * (1 - ratio))
        b = int(b1 * ratio + b2 * (1 - ratio))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return c1


def _build_variables_for_convert(
    primary, secondary, accent, warning, error, success,
    foreground, background, surface, panel, boost,
    dark, name, existing,
) -> dict:
    """完整的 CSS 变量生成（与 theme_manager._build_complete_variables 一致）"""
    existing = existing or {}
    is_glass = "glass" in name.lower() or "transparent" in name.lower()
    cursor_bg = background if not is_glass else "#000000"

    def keep_or(key, computed):
        return existing.get(key, computed)

    v = {}

    # 1. 核心颜色
    for k, val in [("primary", primary), ("secondary", secondary), ("accent", accent),
                   ("warning", warning), ("error", error), ("success", success),
                   ("foreground", foreground), ("background", background),
                   ("surface", surface), ("panel", panel), ("boost", boost)]:
        v[k] = val

    # 2. 文本色系
    v["text"] = foreground
    v["text-muted"] = mix_colors(foreground, background, 0.65)
    v["text-disabled"] = mix_colors(foreground, background, 0.45)
    v["text-primary"] = primary
    v["text-secondary"] = secondary
    v["text-warning"] = warning
    v["text-error"] = error
    v["text-success"] = success
    v["text-accent"] = accent

    # 3. darken/lighten
    v["primary-darken-1"] = darken(primary, 0.075)
    v["primary-lighten-1"] = lighten(primary, 0.075)
    v["surface-darken-1"] = darken(surface, 0.075)
    v["success-darken-1"] = darken(success, 0.075)
    v["panel-darken-1"] = darken(panel, 0.075)

    # 4. Muted
    muted_colors = {
        "primary": primary, "secondary": secondary, "accent": accent,
        "warning": warning, "error": error, "success": success,
    }
    for name_key, color_val in muted_colors.items():
        v[f"{name_key}-muted"] = darken(color_val, 0.3)
    v["foreground-muted"] = mix_colors(foreground, background, 0.5)
    v["foreground-disabled"] = mix_colors(foreground, background, 0.35)

    # 5. 边框
    v["border"] = keep_or("border", mix_colors(primary, surface, 0.45))
    v["border-blurred"] = keep_or("border-blurred", darken(surface, 0.025))

    # 6. 光标
    v["block-cursor-foreground"] = keep_or("block-cursor-foreground", cursor_bg)
    v["block-cursor-background"] = primary
    v["block-cursor-text-style"] = "none"
    v["block-cursor-blurred-foreground"] = foreground
    v["block-cursor-blurred-background"] = f"{primary} 30%"
    v["input-cursor-background"] = foreground
    v["input-cursor-foreground"] = keep_or("input-cursor-foreground", cursor_bg)
    v["input-cursor-text-style"] = "reverse"
    v["input-selection-background"] = f"{primary} 35%"
    v["input-selection-foreground"] = foreground

    # 7. 滚动条
    for sk in ["scrollbar", "scrollbar-hover"]:
        v[sk] = primary
    v["scrollbar-active"] = accent
    for sk in ["scrollbar-background", "scrollbar-background-hover",
               "scrollbar-background-active", "scrollbar-corner-color"]:
        v[sk] = surface

    # 8-15. 其余
    v["block-hover-background"] = surface
    v["footer-foreground"] = foreground
    v["footer-background"] = surface
    v["footer-key-foreground"] = primary
    v["footer-key-background"] = surface
    v["footer-description-foreground"] = foreground
    v["footer-description-background"] = surface
    v["footer-item-background"] = surface
    v["surface-active"] = lighten(surface, 0.05)
    v["link-background"] = "transparent"
    v["link-background-hover"] = f"{primary} 10%"
    v["link-color"] = primary
    v["link-style"] = "underline"
    v["link-color-hover"] = primary
    v["link-style-hover"] = "bold underline"
    v["screen-selection-background"] = f"{primary} 35%"
    v["screen-selection-foreground"] = foreground
    v["ansi-background"] = keep_or("ansi-background", foreground)
    v["ansi-foreground"] = keep_or("ansi-foreground", cursor_bg)
    v["button-foreground"] = foreground
    v["button-color-foreground"] = foreground
    for i in range(1, 7):
        v[f"markdown-h{i}-color"] = primary

    return v


def convert_theme(old_data: dict) -> dict:
    """将旧格式主题数据转换为新格式"""
    styles = old_data.get('styles', {})
    name = old_data.get('name', 'unknown')

    # 提取核心颜色
    primary = pick_color(styles, ['app.accent', 'app.primary'])
    secondary = pick_color(styles, ['app.highlight', 'app.secondary'])
    accent = pick_color(styles, ['app.highlight', 'app.accent'])
    warning = pick_color(styles, ['app.warning'])
    error = pick_color(styles, ['app.warning', 'app.error'])
    success = pick_color(styles, ['app.success'])
    foreground = pick_color(styles, ['reader.text', 'content.text'])
    background = pick_bgcolor(styles, ['ui.background'])
    surface = pick_bgcolor(styles, ['ui.panel'])
    panel = pick_bgcolor(styles, ['ui.panel'])
    border = pick_color(styles, ['ui.border'])
    muted = pick_color(styles, ['app.muted'])
    info = pick_color(styles, ['app.info'])
    title = pick_color(styles, ['app.title'])

    # 提供合理的默认值
    if not background or background == '':
        background = 'transparent' if 'glass' in name or 'transparent' in name else '#000000'

    bg_for_dark_check = background if background != 'transparent' else '#000000'
    dark = is_dark(bg_for_dark_check)

    if not primary:
        primary = '#3B82F6' if not dark else '#60A5FA'
    if not secondary:
        secondary = '#F59E0B' if not dark else '#FBBF24'
    if not accent:
        accent = secondary or '#F59E0B'
    if not warning:
        warning = '#EF4444' if not dark else '#F87171'
    if not error:
        error = warning or '#EF4444'
    if not success:
        success = '#22C55E' if not dark else '#34D399'
    if not foreground:
        foreground = '#000000' if not dark else '#E5E7EB'
    if not surface or surface == '':
        surface = '#00000020' if 'glass' in name or 'transparent' in name else darken(background, 0.04) if background != 'transparent' else '#00000020'
    if not panel or panel == '':
        panel = surface or '#00000020'
    if not border:
        border = '#D1D5DB' if not dark else '#4B5563'
    if not muted:
        muted = '#6B7280' if not dark else '#9CA3AF'
    if not info:
        info = '#0EA5E9'

    # boost 是 surface 的变亮版本
    boost = lighten(surface, 0.06) if surface != 'transparent' and surface != '#00000020' else '#00000030'

    # 保留旧格式中的 border/muted 值用于 variables
    existing_vars = {}
    if border:
        existing_vars['border'] = border
    if muted:
        existing_vars['border-blurred'] = muted

    # 调用统一变量构建函数（从 theme_manager 导入或本地实现）
    variables = _build_variables_for_convert(
        primary, secondary, accent, warning, error, success,
        foreground, background, surface, panel, boost,
        dark, name, existing_vars,
    )

    return {
        'name': name,
        'display_name': old_data.get('display_name', name),
        'description': old_data.get('description', ''),
        'primary': primary,
        'secondary': secondary,
        'accent': accent,
        'warning': warning,
        'error': error,
        'success': success,
        'foreground': foreground,
        'background': background,
        'surface': surface,
        'panel': panel,
        'boost': boost,
        'dark': dark,
        'luminosity_spread': 16.0,
        'text_alpha': 0.95,
        'variables': variables,
    }


def main():
    themes_dir = os.path.join(os.path.dirname(__file__), 'data')
    backup_dir = os.path.join(os.path.dirname(__file__), 'data_backup_old')

    # 创建备份目录
    os.makedirs(backup_dir, exist_ok=True)

    count = 0
    for filename in sorted(os.listdir(themes_dir)):
        if not filename.endswith('.theme'):
            continue

        filepath = os.path.join(themes_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                old_data = json.load(f)

            # 检查是否已经是新格式
            if 'primary' in old_data and 'dark' in old_data and 'styles' not in old_data:
                print(f"跳过（已为新格式）: {filename}")
                continue

            # 备份旧文件
            backup_path = os.path.join(backup_dir, filename)
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(old_data, f, ensure_ascii=False, indent=2)

            # 转换
            new_data = convert_theme(old_data)

            # 写入新文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            print(f"已转换: {filename} -> dark={new_data['dark']}")
            count += 1

        except Exception as e:
            print(f"错误 {filename}: {e}")

    print(f"\n总共转换了 {count} 个主题文件")
    print(f"旧文件备份在: {backup_dir}")


if __name__ == '__main__':
    main()
