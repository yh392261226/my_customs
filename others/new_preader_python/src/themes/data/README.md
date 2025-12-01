# 动态主题系统使用指南

## 概述

NewReader 现在支持动态主题系统，允许在不重启应用的情况下添加、修改和删除主题文件。所有主题文件都存放在 `src/themes/data/` 目录下，以 `.theme` 为扩展名。

## 主题文件格式

主题文件是 JSON 格式，包含以下结构：

```json
{
    "name": "theme_name",
    "display_name": "显示名称",
    "description": "主题描述",
    "styles": {
        "style_key": {
            "color": "#颜色代码",
            "bgcolor": "#背景色代码",
            "bold": true,
            "italic": true,
            "underline": true
        }
    }
}
```

### 必填字段

- `name`: 主题的唯一标识符，必须与文件名（不含扩展名）一致
- `styles`: 样式配置对象

### 可选字段

- `display_name`: 主题的显示名称
- `description`: 主题的描述信息

## 样式配置

每个样式可以包含以下属性：

- `color`: 文字颜色（支持颜色名称或十六进制代码）
- `bgcolor`: 背景颜色
- `bold`: 是否粗体（true/false）
- `italic`: 是否斜体（true/false）
- `underline`: 是否下划线（true/false）
- `blink`: 是否闪烁（true/false）
- `reverse`: 是否反色（true/false）
- `strike`: 是否删除线（true/false）

## 常用样式键

### 应用级样式
- `app.title`: 应用标题
- `app.subtitle`: 应用副标题
- `app.accent`: 强调色
- `app.highlight`: 高亮色
- `app.warning`: 警告色
- `app.success`: 成功色
- `app.info`: 信息色
- `app.muted`: 静音色

### 界面样式
- `ui.border`: 边框颜色
- `ui.background`: 背景色
- `ui.panel`: 面板背景色
- `ui.panel.title`: 面板标题
- `ui.label`: 标签文字
- `ui.button`: 按钮样式
- `ui.button.primary`: 主要按钮
- `ui.button.success`: 成功按钮
- `ui.button.warning`: 警告按钮
- `ui.button.danger`: 危险按钮
- `ui.input`: 输入框
- `ui.input.focus`: 输入框焦点状态
- `ui.selection`: 选择项背景

### 内容样式
- `content.text`: 正文文字
- `content.heading`: 标题
- `content.subheading`: 副标题
- `content.link`: 链接
- `content.quote`: 引用
- `content.code`: 代码
- `content.highlight`: 高亮文本

### 进度条样式
- `progress.bar`: 进度条
- `progress.text`: 进度文字
- `progress.percentage`: 百分比文字

### 书架样式
- `bookshelf.title`: 书架标题
- `bookshelf.author`: 作者名
- `bookshelf.progress`: 进度条
- `bookshelf.tag`: 标签
- `bookshelf.selected`: 选中项

### 阅读器样式
- `reader.text`: 阅读器正文
- `reader.chapter`: 章节标题
- `reader.page_number`: 页码
- `reader.bookmark`: 书签
- `reader.search_result`: 搜索结果

## 使用方法

### 1. 创建新主题

1. 在 `src/themes/data/` 目录下创建新的 `.theme` 文件
2. 按照上述格式配置主题
3. 保存文件

### 2. 修改现有主题

1. 直接编辑对应的 `.theme` 文件
2. 保存修改
3. 在应用中重新选择该主题即可生效

### 3. 删除主题

1. 删除对应的 `.theme` 文件
2. 如果当前使用的是被删除的主题，系统会自动切换到默认主题

## 动态加载特性

- **自动检测**: 系统会在每次获取主题列表或切换主题时自动检测文件变化
- **热更新**: 修改主题文件后无需重启应用，下次切换主题时自动生效
- **错误处理**: 如果主题文件格式错误，系统会记录错误并跳过该文件
- **向后兼容**: 保持对原有内置主题的完全兼容

## 示例主题

系统已包含以下示例主题文件：

- `dark.theme`: 深色主题
- `light.theme`: 浅色主题
- `nord.theme`: Nord 配色主题
- `custom_blue.theme`: 自定义蓝色主题

## 注意事项

1. 主题文件必须使用 UTF-8 编码
2. 颜色代码支持标准颜色名称和十六进制格式
3. 主题名称必须唯一，建议使用英文和下划线
4. 修改系统内置主题时，建议先备份原文件
5. 如果主题文件有语法错误，系统会在日志中显示详细错误信息

## 故障排除

### 主题未显示在列表中
- 检查文件是否在正确的目录下
- 确认文件扩展名是 `.theme`
- 检查 JSON 格式是否正确
- 查看应用日志中的错误信息

### 主题样式未生效
- 确认样式键名是否正确
- 检查颜色值格式是否有效
- 尝试重新切换主题

### 应用报错
- 检查主题文件 JSON 格式
- 确认所有必填字段都已填写
- 查看详细错误日志