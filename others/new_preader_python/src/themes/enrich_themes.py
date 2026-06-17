#!/usr/bin/env python3
"""
主题文件永久更新工具：为所有 .theme 文件补充完整的 CSS 变量

将 theme_manager.py 中 _build_complete_variables 的逻辑
永久写入所有 .theme 文件，确保主题文件自给自足。

用法：
    python3 src/themes/enrich_themes.py
"""

import json
import os


# ── 颜色工具（与 theme_manager.py 保持一致）─────────────────────────────────

def hex_to_rgb(hex_color: str) -> tuple:
    css_names = {
        "black": "#000000", "white": "#FFFFFF", "red": "#FF0000",
        "green": "#008000", "blue": "#0000FF", "yellow": "#FFFF00",
        "cyan": "#00FFFF", "magenta": "#FF00FF", "gray": "#808080",
        "grey": "#808080", "orange": "#FFA500", "purple": "#800080",
        "transparent": "#00000000",
    }
    if hex_color.lower() in css_names:
        hex_color = css_names[hex_color.lower()]
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) == 8:
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def luminance(rgb: tuple) -> float:
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def is_dark(hex_color: str) -> bool:
    try:
        return luminance(hex_to_rgb(hex_color)) < 0.5
    except Exception:
        return True


def darken(hex_color: str, amount: float = 0.075) -> str:
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = max(0, int(r * (1 - amount)))
        g = max(0, int(g * (1 - amount)))
        b = max(0, int(b * (1 - amount)))
        return rgb_to_hex(r, g, b)
    except Exception:
        return hex_color


def lighten(hex_color: str, amount: float = 0.075) -> str:
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * amount))
        g = min(255, int(g + (255 - g) * amount))
        b = min(255, int(b + (255 - b) * amount))
        return rgb_to_hex(r, g, b)
    except Exception:
        return hex_color


def mix_colors(c1: str, c2: str, ratio: float = 0.5) -> str:
    try:
        r1, g1, b1 = hex_to_rgb(c1)
        r2, g2, b2 = hex_to_rgb(c2)
        r = int(r1 * ratio + r2 * (1 - ratio))
        g = int(g1 * ratio + g2 * (1 - ratio))
        b = int(b1 * ratio + b2 * (1 - ratio))
        return rgb_to_hex(r, g, b)
    except Exception:
        return c1


# ── 变量生成 ────────────────────────────────────────────────────────────────

def build_complete_variables(
    primary: str, secondary: str, accent: str,
    warning: str, error: str, success: str,
    foreground: str, background: str,
    surface: str, panel: str, boost: str,
    name: str = "", existing: dict = None,
) -> dict:
    """根据核心颜色生成完整的 CSS 变量字典（与 theme_manager 一致）"""
    existing = existing or {}
    is_glass = "glass" in name.lower() or "transparent" in name.lower()
    cursor_bg = background if not is_glass else "#000000"

    def keep_or(key: str, computed: str) -> str:
        return existing.get(key, computed)

    v = {}

    # 1. 核心颜色
    v["primary"] = primary
    v["secondary"] = secondary
    v["accent"] = accent
    v["warning"] = warning
    v["error"] = error
    v["success"] = success
    v["foreground"] = foreground
    v["background"] = background
    v["surface"] = surface
    v["panel"] = panel
    v["boost"] = boost

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

    # 3. darken/lighten 变体
    v["primary-darken-1"] = darken(primary, 0.075)
    v["primary-lighten-1"] = lighten(primary, 0.075)
    v["surface-darken-1"] = darken(surface, 0.075)
    v["success-darken-1"] = darken(success, 0.075)
    v["panel-darken-1"] = darken(panel, 0.075)

    # 4. Muted 变体
    v["primary-muted"] = darken(primary, 0.3)
    v["secondary-muted"] = darken(secondary, 0.3)
    v["accent-muted"] = darken(accent, 0.3)
    v["warning-muted"] = darken(warning, 0.3)
    v["error-muted"] = darken(error, 0.3)
    v["success-muted"] = darken(success, 0.3)
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
    v["scrollbar"] = primary
    v["scrollbar-hover"] = primary
    v["scrollbar-active"] = accent
    v["scrollbar-background"] = surface
    v["scrollbar-background-hover"] = surface
    v["scrollbar-background-active"] = surface
    v["scrollbar-corner-color"] = surface

    # 8. 块悬停
    v["block-hover-background"] = surface

    # 9. Footer
    v["footer-foreground"] = foreground
    v["footer-background"] = surface
    v["footer-key-foreground"] = primary
    v["footer-key-background"] = surface
    v["footer-description-foreground"] = foreground
    v["footer-description-background"] = surface
    v["footer-item-background"] = surface

    # 10. Surface 激活态
    v["surface-active"] = lighten(surface, 0.05)

    # 11. 链接
    v["link-background"] = "transparent"
    v["link-background-hover"] = f"{primary} 10%"
    v["link-color"] = primary
    v["link-style"] = "underline"
    v["link-color-hover"] = primary
    v["link-style-hover"] = "bold underline"

    # 12. 选择高亮
    v["screen-selection-background"] = f"{primary} 35%"
    v["screen-selection-foreground"] = foreground

    # 13. ANSI
    v["ansi-background"] = keep_or("ansi-background", foreground)
    v["ansi-foreground"] = keep_or("ansi-foreground", cursor_bg)

    # 14. 按钮
    v["button-foreground"] = foreground
    v["button-color-foreground"] = foreground

    # 15. Markdown 标题
    for i in range(1, 7):
        v[f"markdown-h{i}-color"] = primary

    return v


def enrich_theme(data: dict) -> dict:
    """增强单个主题文件"""
    name = data.get("name", "unknown")
    is_glass = "glass" in name.lower() or "transparent" in name.lower()

    # 修复 dark 标志
    background = data.get("background", "#000000")
    if not is_glass:
        try:
            data["dark"] = is_dark(background)
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

    # 生成完整变量
    data["variables"] = build_complete_variables(
        primary=primary, secondary=secondary, accent=accent,
        warning=warning, error=error, success=success,
        foreground=foreground, background=background,
        surface=surface, panel=panel, boost=boost,
        name=name,
        existing=data.get("variables", {}),
    )

    return data


# ── 主程序 ──────────────────────────────────────────────────────────────────

def main():
    themes_dir = os.path.join(os.path.dirname(__file__), "data")
    backup_dir = os.path.join(os.path.dirname(__file__), "data_backup_before_enrich")

    os.makedirs(backup_dir, exist_ok=True)

    stats = {"total": 0, "dark_fixed": 0, "vars_added": 0, "errors": 0}

    for filename in sorted(os.listdir(themes_dir)):
        if not filename.endswith(".theme"):
            continue

        filepath = os.path.join(themes_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            old_vars = len(data.get("variables", {}))
            old_dark = data.get("dark")

            # 备份
            backup_path = os.path.join(backup_dir, filename)
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 增强
            enriched = enrich_theme(data)
            new_vars = len(enriched.get("variables", {}))
            new_dark = enriched.get("dark")

            # 写入
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(enriched, f, ensure_ascii=False, indent=2)

            changes = []
            if new_vars != old_vars:
                changes.append(f"variables: {old_vars}→{new_vars}")
                stats["vars_added"] += 1
            if new_dark != old_dark:
                changes.append(f"dark: {old_dark}→{new_dark}")
                stats["dark_fixed"] += 1

            if changes:
                print(f"✅ {filename}: {', '.join(changes)}")
            else:
                print(f"   {filename}: 已是最新")
            stats["total"] += 1

        except Exception as e:
            print(f"❌ {filename}: {e}")
            stats["errors"] += 1

    print(f"\n{'='*60}")
    print(f"处理完成: {stats['total']} 个主题")
    print(f"修复 dark 标志: {stats['dark_fixed']} 个")
    print(f"增加变量: {stats['vars_added']} 个")
    if stats["errors"]:
        print(f"错误: {stats['errors']} 个")
    print(f"备份: {backup_dir}")


if __name__ == "__main__":
    main()
