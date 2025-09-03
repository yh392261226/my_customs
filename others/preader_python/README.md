# Preader 📖

> 一个功能丰富的终端小说阅读器，支持多种电子书格式，提供舒适的阅读体验和强大的书籍管理功能。

---

## ✨ 功能特点

### 📚 多格式支持
- **文本文件**: `.txt`, `.md`
- **电子书格式**: `.epub`, `.pdf`, `.mobi`, `.azw`, `.azw3`

### 🎨 个性化阅读体验
- **主题系统**: 支持多种主题（dark、light、eye、midnight 等）
- **字体设置**: 可调整字体大小、行距和段落间距
- **自动翻页**: 可设置自动翻页间隔
- **朗读功能**: 支持文本朗读，可调节语速

### 🔍 强大的书籍管理
- **书架系统**: 分类管理所有书籍
- **标签系统**: 为书籍添加标签，支持批量编辑
- **搜索功能**: 快速查找书籍
- **阅读统计**: 记录阅读时间和进度
- **书签功能**: 添加和管理书签

### ⚡ 便捷操作
- **老板键**: 一键隐藏/显示阅读界面
- **终端模式**: 内置终端模拟器，不退出程序即可执行命令
- **多语言支持**: 支持中文和英文界面
- **快捷键**: 丰富的快捷键操作

---

## 🛠️ 安装步骤

### 前提条件
- Python 3.7+
- 终端支持 256 色和 Unicode

### 安装依赖
```bash
pip install -r requirements.txt
```

### 获取 KindleUnpack
- 项目需要 KindleUnpack 来处理 AZW/AZW3 格式，请从官方仓库获取并放置在项目目录下：
```bash
git clone https://github.com/kevinhendricks/KindleUnpack.git ./KindleUnpack
```

## 🚀 使用方法

### 启动阅读器
```bash
python main.py
```

### 直接打开书籍
```bash
python main.py /path/to/your/book.epub
```

### 基本操作
```text
preader/
├── main.py              # 程序入口
├── reader.py            # 主阅读器类
├── bookshelf.py         # 书架管理
├── db.py                # 数据库管理
├── settings.py          # 设置管理
├── stats.py             # 阅读统计
├── lang.py              # 多语言支持
├── ui_theme.py          # 界面主题
├── chart_utils.py       # 统计图表
├── requirements.txt     # 依赖列表
├── epub_utils.py        # EPUB解析
├── pdf_utils.py         # PDF解析
├── mobi_utils.py        # MOBI解析
└── azw_utils.py         # AZW/AZW3解析
```

## ⚙️ 配置说明

#### 程序首次运行时会创建配置文件 ~/.config/preader/settings.json，包含以下可配置项：
- 显示设置: 宽度、高度、边距、字体颜色、背景颜色
- ​阅读设置: 行距、段落间距、自动翻页间隔
- ​朗读设置: 语速
- ​提醒设置: 阅读提醒间隔
​- 界面主题: 多种预定义主题

## ❓ 常见问题
Q: 无法打开 EPUB 文件​
​A:​​ 确保已安装所有依赖库，特别是 ebooklib 和 beautifulsoup4。

​Q: 朗读功能无法工作​
​A:​​ 在 macOS 上可能需要安装额外的语音引擎：
```bash
# 安装 pyobjc
pip install pyobjc
```

Q: 显示乱码​
​A:​​ 确保终端支持 UTF-8 编码，并设置了正确的 locale：
```bash
export LANG=en_US.UTF-8
```

Q: 无法解析 AZW/AZW3 文件​
​A:​​ 确保 KindleUnpack 已正确放置在项目目录下。

## 📄 许可证
- 本项目采用 MIT 许可证，详见 LICENSE 文件。

## 🙏 致谢
- 感谢 KindleUnpack 项目提供 AZW/AZW3 解析支持
- 感谢所有贡献者和 Deepseek 的支持
-------


享受阅读的乐趣吧！📖