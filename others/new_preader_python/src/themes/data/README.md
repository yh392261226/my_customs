# 主题系统使用指南

## 概述

NewReader 使用 Textual 框架的原生 Theme 系统。所有主题文件存放在 `src/themes/data/` 目录下，以 `.theme` 为扩展名，JSON 格式。

## 主题文件格式（新格式）

主题文件是 JSON 格式，包含以下字段：

```json
{
    "name": "dark",
    "display_name": "深色主题",
    "description": "经典的深色主题，适合长时间阅读",
    "primary": "#3B82F6",
    "secondary": "#F59E0B",
    "accent": "#F59E0B",
    "warning": "#EF4444",
    "error": "#EF4444",
    "success": "#22C55E",
    "foreground": "#E5E7EB",
    "background": "#000000",
    "surface": "#111827",
    "panel": "#111827",
    "boost": "#1F2937",
    "dark": true,
    "luminosity_spread": 16.0,
    "text_alpha": 0.95,
    "variables": {
        "border": "#4B5563",
        "border-blurred": "#9CA3AF",
        "block-cursor-foreground": "#000000",
        "block-cursor-background": "#3B82F6",
        "block-cursor-text-style": "none",
        "input-cursor-background": "#E5E7EB",
        "input-cursor-foreground": "#000000",
        "input-cursor-text-style": "reverse",
        "input-selection-background": "#3B82F6 35%",
        "input-selection-foreground": "#E5E7EB",
        "scrollbar": "#3B82F6",
        "scrollbar-hover": "#F59E0B",
        "scrollbar-active": "#F59E0B",
        "scrollbar-background": "#111827",
        "scrollbar-background-hover": "#111827",
        "scrollbar-background-active": "#111827",
        "scrollbar-corner-color": "#111827",
        "block-hover-background": "#111827",
        "footer-key-foreground": "#3B82F6",
        "footer-key-background": "#111827",
        "footer-description-foreground": "#E5E7EB",
        "footer-description-background": "#111827",
        "screen-selection-background": "#3B82F6 35%",
        "screen-selection-foreground": "#E5E7EB"
    }
}
```

### 必填字段

- `name`: 主题的唯一标识符，必须与文件名（不含扩展名）一致
- `primary`: 主色调
- `foreground`: 前景色（文字颜色）
- `background`: 背景色
- `dark`: 是否为深色主题

### 可选字段

- `display_name`: 显示名称
- `description`: 主题描述
- `secondary`: 次要色
- `accent`: 强调色
- `warning`: 警告色
- `error`: 错误色
- `success`: 成功色
- `surface`: 表面色（比背景稍亮）
- `panel`: 面板色
- `boost`: 高亮表面色
- `luminosity_spread`: 亮度扩散（默认 16.0）
- `text_alpha`: 文字透明度（默认 0.95）
- `variables`: Textual 主题变量字典

### variables 支持的变量

| 变量名 | 说明 |
|--------|------|
| `border` | 边框颜色 |
| `border-blurred` | 失焦边框颜色 |
| `block-cursor-foreground` | 块光标前景色 |
| `block-cursor-background` | 块光标背景色 |
| `block-cursor-text-style` | 块光标文字样式 |
| `input-cursor-background` | 输入光标背景色 |
| `input-cursor-foreground` | 输入光标前景色 |
| `input-cursor-text-style` | 输入光标文字样式 |
| `input-selection-background` | 输入选择背景色 |
| `input-selection-foreground` | 输入选择前景色 |
| `scrollbar` | 滚动条颜色 |
| `scrollbar-hover` | 滚动条悬停色 |
| `scrollbar-active` | 滚动条激活色 |
| `scrollbar-background` | 滚动条背景色 |
| `scrollbar-background-hover` | 滚动条背景悬停色 |
| `scrollbar-background-active` | 滚动条背景激活色 |
| `scrollbar-corner-color` | 滚动条角落色 |
| `block-hover-background` | 块悬停背景色 |
| `footer-key-foreground` | 页脚快捷键前景色 |
| `footer-key-background` | 页脚快捷键背景色 |
| `footer-description-foreground` | 页脚描述前景色 |
| `footer-description-background` | 页脚描述背景色 |
| `screen-selection-background` | 屏幕选择背景色 |
| `screen-selection-foreground` | 屏幕选择前景色 |

## 向后兼容

系统自动兼容旧格式（`styles: {...}`）的主题文件，会在加载时自动转换为新格式。
如果需要永久转换旧文件，运行 `python src/themes/convert_themes.py`，旧文件将备份到 `src/themes/data_backup_old/`。

## 使用方法

### 1. 创建新主题

1. 复制一个现有 `.theme` 文件
2. 按照上述格式修改颜色值
3. 保存文件
4. 在应用设置中重新选择该主题

### 2. 在设置中心切换主题

1. 打开设置中心：按 `s` 键
2. 在外观标签页中找到"主题"选项
3. 从下拉列表中选择主题
4. 保存设置

### 3. 快捷键切换主题

按 `t` 键打开主题选择器，上下移动预览，回车确认。
