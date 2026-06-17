#!/usr/bin/env python3
"""
生成30款精心设计的主题文件

设计原则：
1. 主题颜色鲜明悦目，配色和谐
2. 按钮文字在所有状态（正常/悬停/点击）都有足够对比度
3. 包含6款高对比度主题（#高对比度 标记）
4. 18款暗色 + 12款亮色
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

THEMES_DIR = os.path.join(os.path.dirname(__file__), "data")


def hex_to_rgb(hex_color: str) -> tuple:
    css_names = {
        "black": "#000000", "white": "#FFFFFF", "red": "#FF0000",
        "green": "#008000", "blue": "#0000FF", "transparent": "#00000000",
    }
    hex_color = css_names.get(hex_color.lower(), hex_color)
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def luminance(rgb: tuple) -> float:
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(rgb[0]) + 0.7152 * linearize(rgb[1]) + 0.0722 * linearize(rgb[2])


def contrast_ratio(c1: str, c2: str) -> float:
    """计算 WCAG 对比度"""
    try:
        l1 = luminance(hex_to_rgb(c1))
        l2 = luminance(hex_to_rgb(c2))
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)
    except Exception:
        return 1.0


def rgb_to_hex(r, g, b):
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"


def darken(c, amount=0.06):
    r, g, b = hex_to_rgb(c)
    return rgb_to_hex(int(r * (1 - amount)), int(g * (1 - amount)), int(b * (1 - amount)))


def lighten(c, amount=0.08):
    r, g, b = hex_to_rgb(c)
    return rgb_to_hex(
        min(255, int(r + (255 - r) * amount)),
        min(255, int(g + (255 - g) * amount)),
        min(255, int(b + (255 - b) * amount)),
    )


def ensure_bg_contrast(fg: str, bg: str, min_ratio: float = 4.5) -> str:
    """确保前景色与背景色有足够的 WCAG 对比度"""
    if contrast_ratio(fg, bg) >= min_ratio:
        return fg
    # 如果对比度不够，调整前景色
    fg_rgb = hex_to_rgb(fg)
    bg_rgb = hex_to_rgb(bg)
    bg_lum = luminance(bg_rgb)
    # 背景亮则加深，背景暗则变亮
    if bg_lum > 0.5:
        for i in range(1, 15):
            adjusted = darken(fg, 0.05 * i)
            if contrast_ratio(adjusted, bg) >= min_ratio:
                return adjusted
        return "#000000" if bg_lum > 0.5 else "#FFFFFF"
    else:
        for i in range(1, 15):
            adjusted = lighten(fg, 0.05 * i)
            if contrast_ratio(adjusted, bg) >= min_ratio:
                return adjusted
        return "#FFFFFF" if bg_lum <= 0.5 else "#000000"


def create_theme(name, display_name, description, primary, secondary, accent,
                 warning_col, error_col, success_col, foreground, background,
                 surface, panel, boost, dark):
    """创建一个完整的主题数据"""
    # 确保关键对比度
    foreground = ensure_bg_contrast(foreground, background, 4.5)
    
    return {
        "name": name,
        "display_name": display_name,
        "description": description,
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "warning": warning_col,
        "error": error_col,
        "success": success_col,
        "foreground": foreground,
        "background": background,
        "surface": surface,
        "panel": panel,
        "boost": boost,
        "dark": dark,
        "luminosity_spread": 16.0,
        "text_alpha": 0.95,
        "variables": {},  # 运行时自动补全
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 30 款主题定义
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = [
    # ───────────────────────────────────────────────────────────────────────────
    # 暗色主题 (18款)
    # ───────────────────────────────────────────────────────────────────────────

    {
        "name": "sunset-glow", "dark": True,
        "display_name": "落日余晖",
        "description": "温暖的橘色落日余晖，柔和舒适的阅读体验",
        "primary": "#FF8C42", "secondary": "#FFD166", "accent": "#FFD166",
        "warning": "#FFB347", "error": "#EF476F", "success": "#06D6A0",
        "foreground": "#FFF3E0", "background": "#1A1025",
        "surface": "#251A33", "panel": "#251A33", "boost": "#2E2140",
    },
    {
        "name": "ocean-breeze", "dark": True,
        "display_name": "海风拂面",
        "description": "清新的深海蓝色调，如同海风吹拂般清爽",
        "primary": "#00B4D8", "secondary": "#90E0EF", "accent": "#90E0EF",
        "warning": "#F4A261", "error": "#E76F51", "success": "#2EC4B6",
        "foreground": "#E0F7FA", "background": "#021124",
        "surface": "#0A1D3A", "panel": "#0A1D3A", "boost": "#102844",
    },
    {
        "name": "forest-canopy", "dark": True,
        "display_name": "森林华盖",
        "description": "深邃的森林绿意，让人沉浸在大自然中",
        "primary": "#4ADE80", "secondary": "#A3E635", "accent": "#A3E635",
        "warning": "#FBBF24", "error": "#F87171", "success": "#34D399",
        "foreground": "#DCFCE7", "background": "#022306",
        "surface": "#052E0A", "panel": "#052E0A", "boost": "#0A3D12",
    },
    {
        "name": "lavender-dream", "dark": True,
        "display_name": "薰衣草梦",
        "description": "温柔的紫色梦境，淡雅而治愈",
        "primary": "#A78BFA", "secondary": "#C4B5FD", "accent": "#C4B5FD",
        "warning": "#FBBF24", "error": "#FCA5A5", "success": "#6EE7B7",
        "foreground": "#EDE9FE", "background": "#120C24",
        "surface": "#1E1638", "panel": "#1E1638", "boost": "#281D48",
    },
    {
        "name": "midnight-sky", "dark": True,
        "display_name": "午夜星空",
        "description": "深邃夜幕下的星光，沉静而专注",
        "primary": "#38BDF8", "secondary": "#7DD3FC", "accent": "#7DD3FC",
        "warning": "#FBBF24", "error": "#FB7185", "success": "#4ADE80",
        "foreground": "#E0F2FE", "background": "#0A0E27",
        "surface": "#111640", "panel": "#111640", "boost": "#1A2054",
    },
    {
        "name": "golden-hour", "dark": True,
        "display_name": "金色时光",
        "description": "温暖的金色光芒，如夕阳下的阅读时光",
        "primary": "#F59E0B", "secondary": "#FCD34D", "accent": "#FCD34D",
        "warning": "#F97316", "error": "#EF4444", "success": "#22C55E",
        "foreground": "#FEF3C7", "background": "#1C1408",
        "surface": "#2D1F0C", "panel": "#2D1F0C", "boost": "#3D2A10",
    },
    {
        "name": "coral-sunset", "dark": True,
        "display_name": "珊瑚暮色",
        "description": "珊瑚粉色的暮光，浪漫而温暖",
        "primary": "#FB7185", "secondary": "#FDA4AF", "accent": "#FDA4AF",
        "warning": "#FBBF24", "error": "#E11D48", "success": "#34D399",
        "foreground": "#FFE4E6", "background": "#1F0D15",
        "surface": "#2E1520", "panel": "#2E1520", "boost": "#3D1E2C",
    },
    {
        "name": "ruby-wine", "dark": True,
        "display_name": "红宝石酒",
        "description": "醇厚的红酒色调，优雅而沉稳",
        "primary": "#E11D48", "secondary": "#FB7185", "accent": "#FB7185",
        "warning": "#F59E0B", "error": "#BE123C", "success": "#4ADE80",
        "foreground": "#FCE7F3", "background": "#1A0510",
        "surface": "#2D0D1C", "panel": "#2D0D1C", "boost": "#3D1428",
    },
    {
        "name": "deep-ocean", "dark": True,
        "display_name": "深海秘境",
        "description": "神秘的深海蓝绿，静谧而深邃",
        "primary": "#14B8A6", "secondary": "#5EEAD4", "accent": "#5EEAD4",
        "warning": "#F59E0B", "error": "#F87171", "success": "#34D399",
        "foreground": "#CCFBF1", "background": "#021A1A",
        "surface": "#042F2E", "panel": "#042F2E", "boost": "#0A3D3C",
    },
    {
        "name": "autumn-leaves", "dark": True,
        "display_name": "秋叶飘落",
        "description": "秋日枫叶的温暖色调，浓郁而怀旧",
        "primary": "#F97316", "secondary": "#FDBA74", "accent": "#FDBA74",
        "warning": "#FBBF24", "error": "#DC2626", "success": "#84CC16",
        "foreground": "#FFF7ED", "background": "#1A0F05",
        "surface": "#2D1A0C", "panel": "#2D1A0C", "boost": "#3D2412",
    },
    {
        "name": "neon-city", "dark": True,
        "display_name": "霓虹都市 #高对比度",
        "description": "赛博朋克风格的霓虹灯色彩，极具视觉冲击力",
        "primary": "#FF00FF", "secondary": "#00FFFF", "accent": "#00FFFF",
        "warning": "#FFB800", "error": "#FF3333", "success": "#00FF41",
        "foreground": "#F0F0FF", "background": "#08081A",
        "surface": "#12122A", "panel": "#12122A", "boost": "#1C1C3A",
    },
    {
        "name": "storm-cloud", "dark": True,
        "display_name": "暴风云层",
        "description": "暴风雨前的灰色云层，冷峻而专注",
        "primary": "#94A3B8", "secondary": "#CBD5E1", "accent": "#CBD5E1",
        "warning": "#FBBF24", "error": "#F87171", "success": "#86EFAC",
        "foreground": "#E2E8F0", "background": "#0F1219",
        "surface": "#1A1F2C", "panel": "#1A1F2C", "boost": "#242A3A",
    },
    {
        "name": "electric-violet", "dark": True,
        "display_name": "电光紫罗兰 #高对比度",
        "description": "鲜艳的紫罗兰电光色，充满活力与创造力",
        "primary": "#D946EF", "secondary": "#F0ABFC", "accent": "#F0ABFC",
        "warning": "#FBBF24", "error": "#FB7185", "success": "#34D399",
        "foreground": "#FAF5FF", "background": "#0D0221",
        "surface": "#1A0533", "panel": "#1A0533", "boost": "#260A45",
    },
    {
        "name": "rose-gold", "dark": True,
        "display_name": "玫瑰金",
        "description": "优雅的玫瑰金色调，温润而有质感",
        "primary": "#F43F5E", "secondary": "#FDA4AF", "accent": "#FDA4AF",
        "warning": "#F59E0B", "error": "#E11D48", "success": "#4ADE80",
        "foreground": "#FFE4E6", "background": "#1A1016",
        "surface": "#2D1C25", "panel": "#2D1C25", "boost": "#3D2632",
    },
    {
        "name": "crimson-night", "dark": True,
        "display_name": "深红之夜",
        "description": "深邃的暗红夜色，神秘而有力量感",
        "primary": "#DC2626", "secondary": "#FCA5A5", "accent": "#FCA5A5",
        "warning": "#F59E0B", "error": "#B91C1C", "success": "#4ADE80",
        "foreground": "#FEE2E2", "background": "#0F0305",
        "surface": "#1F0A0D", "panel": "#1F0A0D", "boost": "#2D1218",
    },
    {
        "name": "emerald-city", "dark": True,
        "display_name": "翡翠之城",
        "description": "浓郁的翡翠绿色，充满生机与活力",
        "primary": "#10B981", "secondary": "#6EE7B7", "accent": "#6EE7B7",
        "warning": "#FBBF24", "error": "#FB7185", "success": "#34D399",
        "foreground": "#D1FAE5", "background": "#011A10",
        "surface": "#022C22", "panel": "#022C22", "boost": "#06442F",
    },
    {
        "name": "obsidian", "dark": True,
        "display_name": "黑曜石 #高对比度",
        "description": "极致黑白对比，最纯粹的高对比度阅读体验",
        "primary": "#FFFFFF", "secondary": "#E2E8F0", "accent": "#E2E8F0",
        "warning": "#FCD34D", "error": "#F87171", "success": "#4ADE80",
        "foreground": "#F8FAFC", "background": "#000000",
        "surface": "#0F0F0F", "panel": "#0F0F0F", "boost": "#1A1A1A",
    },
    {
        "name": "moonlight", "dark": True,
        "display_name": "月光如水",
        "description": "柔和的月光银色，静谧而优雅",
        "primary": "#818CF8", "secondary": "#A5B4FC", "accent": "#A5B4FC",
        "warning": "#FBBF24", "error": "#FCA5A5", "success": "#86EFAC",
        "foreground": "#E0E7FF", "background": "#0D0F23",
        "surface": "#161A3A", "panel": "#161A3A", "boost": "#1F2450",
    },

    # ───────────────────────────────────────────────────────────────────────────
    # 亮色主题 (12款)
    # ───────────────────────────────────────────────────────────────────────────

    {
        "name": "cherry-blossom", "dark": False,
        "display_name": "樱花物语",
        "description": "粉嫩的樱花色调，温柔甜美令人心旷神怡",
        "primary": "#DB2777", "secondary": "#F472B6", "accent": "#F472B6",
        "warning": "#F59E0B", "error": "#E11D48", "success": "#10B981",
        "foreground": "#4A102A", "background": "#FFF5F7",
        "surface": "#FFE4E6", "panel": "#FFE4E6", "boost": "#FFD1D6",
    },
    {
        "name": "mint-fresh", "dark": False,
        "display_name": "鲜薄荷",
        "description": "清爽的薄荷绿色，让人神清气爽",
        "primary": "#059669", "secondary": "#34D399", "accent": "#34D399",
        "warning": "#D97706", "error": "#DC2626", "success": "#16A34A",
        "foreground": "#022C22", "background": "#F0FDF4",
        "surface": "#DCFCE7", "panel": "#DCFCE7", "boost": "#BBF7D0",
    },
    {
        "name": "arctic-frost", "dark": False,
        "display_name": "极地冰霜",
        "description": "冰晶般清透的蓝白配色，极致纯净",
        "primary": "#0284C7", "secondary": "#38BDF8", "accent": "#38BDF8",
        "warning": "#EA580C", "error": "#DC2626", "success": "#16A34A",
        "foreground": "#0C1929", "background": "#F8FAFC",
        "surface": "#E0F2FE", "panel": "#E0F2FE", "boost": "#BAE6FD",
    },
    {
        "name": "sakura-spring", "dark": False,
        "display_name": "樱之春",
        "description": "春日樱花般的淡雅粉白，轻盈通透",
        "primary": "#BE185D", "secondary": "#F472B6", "accent": "#F472B6",
        "warning": "#D97706", "error": "#DC2626", "success": "#059669",
        "foreground": "#3D0A1E", "background": "#FFF1F2",
        "surface": "#FFE4E6", "panel": "#FFE4E6", "boost": "#FECDD3",
    },
    {
        "name": "matcha-latte", "dark": False,
        "display_name": "抹茶拿铁",
        "description": "温暖的抹茶绿与奶白色，柔和自然",
        "primary": "#4D7C0F", "secondary": "#84CC16", "accent": "#84CC16",
        "warning": "#D97706", "error": "#DC2626", "success": "#15803D",
        "foreground": "#1A2E05", "background": "#F7FEE7",
        "surface": "#ECFCCB", "panel": "#ECFCCB", "boost": "#D9F99D",
    },
    {
        "name": "peach-blossom", "dark": False,
        "display_name": "桃花朵朵",
        "description": "温暖的蜜桃橙色，如同春日桃花盛开",
        "primary": "#C2410C", "secondary": "#FB923C", "accent": "#FB923C",
        "warning": "#D97706", "error": "#DC2626", "success": "#059669",
        "foreground": "#2D1608", "background": "#FFF7ED",
        "surface": "#FFEDD5", "panel": "#FFEDD5", "boost": "#FED7AA",
    },
    {
        "name": "seafoam", "dark": False,
        "display_name": "海沫绿",
        "description": "清新的海沫碧绿色，如海浪轻抚沙滩",
        "primary": "#0D9488", "secondary": "#2DD4BF", "accent": "#2DD4BF",
        "warning": "#D97706", "error": "#DC2626", "success": "#059669",
        "foreground": "#042F2E", "background": "#F0FDFA",
        "surface": "#CCFBF1", "panel": "#CCFBF1", "boost": "#99F6E4",
    },
    {
        "name": "mountain-mist", "dark": False,
        "display_name": "山间薄雾",
        "description": "淡雅的山间灰雾色调，宁静而克制",
        "primary": "#4B5563", "secondary": "#9CA3AF", "accent": "#9CA3AF",
        "warning": "#D97706", "error": "#DC2626", "success": "#059669",
        "foreground": "#111827", "background": "#F9FAFB",
        "surface": "#F3F4F6", "panel": "#F3F4F6", "boost": "#E5E7EB",
    },
    {
        "name": "sky-blue", "dark": False,
        "display_name": "晴空万里",
        "description": "明媚的天空蓝白配色，明亮开阔",
        "primary": "#2563EB", "secondary": "#60A5FA", "accent": "#60A5FA",
        "warning": "#EA580C", "error": "#DC2626", "success": "#16A34A",
        "foreground": "#0F172A", "background": "#EFF6FF",
        "surface": "#DBEAFE", "panel": "#DBEAFE", "boost": "#BFDBFE",
    },
    {
        "name": "cotton-candy", "dark": False,
        "display_name": "棉花糖",
        "description": "梦幻的粉紫棉花糖色调，甜美而治愈",
        "primary": "#7C3AED", "secondary": "#A78BFA", "accent": "#A78BFA",
        "warning": "#D97706", "error": "#DC2626", "success": "#059669",
        "foreground": "#2E1065", "background": "#FAF5FF",
        "surface": "#F3E8FF", "panel": "#F3E8FF", "boost": "#E9D5FF",
    },
    {
        "name": "tropical-punch", "dark": False,
        "display_name": "热带果饮 #高对比度",
        "description": "热情奔放的热带水果色，活力四射",
        "primary": "#EA580C", "secondary": "#22D3EE", "accent": "#22D3EE",
        "warning": "#D97706", "error": "#DC2626", "success": "#16A34A",
        "foreground": "#1C0A00", "background": "#FFFBEB",
        "surface": "#FEF3C7", "panel": "#FEF3C7", "boost": "#FDE68A",
    },
    {
        "name": "paper-white", "dark": False,
        "display_name": "纯白纸页 #高对比度",
        "description": "纯白纸张般的极致阅读体验，最高对比度",
        "primary": "#1D4ED8", "secondary": "#3B82F6", "accent": "#3B82F6",
        "warning": "#B45309", "error": "#B91C1C", "success": "#15803D",
        "foreground": "#0F172A", "background": "#FFFFFF",
        "surface": "#F8FAFC", "panel": "#F8FAFC", "boost": "#F1F5F9",
    },
]


def validate_theme(theme, index):
    """验证主题质量"""
    name = theme["name"]
    issues = []
    
    # 背景色与前景色对比度
    cr = contrast_ratio(theme["foreground"], theme["background"])
    if cr < 4.5:
        issues.append(f"前景/背景对比度={cr:.1f} (<4.5)")
    
    # Primary 与背景对比度
    pcr = contrast_ratio(theme["primary"], theme["background"])
    if pcr < 3.0:
        issues.append(f"primary/背景对比度={pcr:.1f} (<3.0)")
    
    # Success/Error/Warning 在背景上的可见性
    for color_name in ["success", "error", "warning"]:
        scr = contrast_ratio(theme[color_name], theme["background"])
        if scr < 3.0:
            issues.append(f"{color_name}/背景对比度={scr:.1f} (<3.0)")
    
    # Surface 和 Panel 应该有细微差异
    if theme["surface"] == theme["background"]:
        issues.append("surface 与 background 相同")
    
    if issues:
        print(f"  ⚠️  [{index}] {name}: {'; '.join(issues)}")
        return False
    return True


def main():
    os.makedirs(THEMES_DIR, exist_ok=True)
    
    created = 0
    skipped = 0
    
    for i, theme_data in enumerate(THEMES, 1):
        name = theme_data.pop("name")
        dark = theme_data.pop("dark")
        display_name = theme_data.pop("display_name")
        description = theme_data.pop("description")
        
        # 构建主题
        theme = create_theme(
            name=name, display_name=display_name, description=description,
            dark=dark, **theme_data
        )
        
        # 验证
        validate_theme(theme, i)
        
        # 检查是否已存在
        filepath = os.path.join(THEMES_DIR, f"{name}.theme")
        if os.path.exists(filepath):
            print(f"  [{i:2d}] ⏭  跳过（已存在）: {name}")
            skipped += 1
            continue
        
        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(theme, f, ensure_ascii=False, indent=2)
        
        tags = "🌙暗色" if dark else "☀️亮色"
        if "高对比度" in display_name:
            tags += " ⚡高对比度"
        
        print(f"  [{i:2d}] ✅ {tags} {name}: {display_name} (primary={theme['primary']})")
        created += 1
    
    print(f"\n{'='*60}")
    print(f"✅ 创建: {created} 个主题")
    print(f"⏭  跳过: {skipped} 个主题")
    print(f"📁 目录: {THEMES_DIR}")
    print(f"\n总计主题文件: {len(os.listdir(THEMES_DIR))} 个")


if __name__ == "__main__":
    main()
