# NewReader - 现代化终端小说阅读器

NewReader 是一个功能丰富的现代化终端小说阅读器，基于 Textual 框架构建，支持多种文件格式和丰富的阅读功能，拥有美观的用户界面和强大的功能特性。

## ✨ 核心特性

### 📖 多格式支持
- **文本格式**: TXT, MD
- **电子书格式**: EPUB, PDF, MOBI, AZW/AZW3
- **智能解析**: 自动识别章节结构，支持复杂电子书格式
- **加密PDF支持**: 支持加密PDF文件的密码输入和解密

### 🎨 现代化界面
- **多主题支持**: 内置 15+ 精美主题 (dark, light, nord, dracula, material, github-dark, github-light, solarized-dark, solarized-light, amethyst, forest-green, crimson, slate, transparent-dark, transparent-light)
- **多语言界面**: 支持中文和英文界面切换
- **响应式设计**: 自适应终端尺寸，支持全屏模式
- **动画效果**: 平滑的过渡动画和加载效果

### 🔧 丰富的阅读功能
- **智能分页**: 自动根据终端尺寸和字体设置进行分页
- **书签管理**: 添加、删除、管理书签，支持书签备注
- **全文搜索**: 支持内容搜索和书库搜索，支持文件类型筛选
- **阅读统计**: 详细的阅读时间和进度统计，支持单本和全局统计
- **自动翻页**: 可配置的自动翻页功能
- **文本朗读**: TTS 文本朗读支持
- **阅读进度**: 自动保存和恢复阅读位置

### 📚 书库管理
- **智能扫描**: 自动扫描目录添加书籍
- **批量操作**: 支持批量删除、导出、标签管理操作
- **批量标签管理**: 支持批量设置、清空标签，包含全选、反选、取消全选功能
- **分类管理**: 按作者、格式、阅读时间、标签分类
- **搜索筛选**: 强大的搜索和筛选功能，支持按文件类型筛选
- **实时统计**: 书架页面显示总书籍数和各格式分布统计

### ⚙️ 高度可定制
- **字体设置**: 可调整字体大小、行间距、段落间距
- **边距设置**: 自定义左右边距
- **主题定制**: 丰富的主题选择和自定义选项
- **快捷键**: 完全可定制的键盘快捷键

### 🔒 隐私保护
- **老板键功能**: 快速切换到终端模拟界面 (Ctrl+B)
- **安全退出**: 支持快速隐藏阅读界面
- **命令模拟**: 支持基本的终端命令执行

### 🌐 网络小说爬虫
- **多站点支持**: 内置 87NB小说网、任奇小说网等爬虫
- **整本下载**: 支持整本小说章节爬取
- **代理支持**: 可配置网络代理
- **智能解析**: 自动识别章节结构和内容

## 🚀 快速开始

### 系统要求
- Python 3.8+
- 支持终端模拟器 (iTerm2, Terminal, Windows Terminal 等)

### 安装方法

```bash
# 克隆仓库
git clone https://github.com/yourusername/newreader.git
cd newreader

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

### 命令行参数
```bash
python main.py [选项] [书籍文件]

选项:
  --config CONFIG    指定配置文件路径
  --debug            启用调试模式
  --help             显示帮助信息

示例:
python main.py ~/Documents/books/novel.txt
python main.py --config ~/.config/newreader/custom_config.json
```

## 🎮 使用指南

### 主界面导航
- **欢迎屏幕**: 应用启动时的主界面，提供快速访问功能
- **书库管理**: 浏览和管理所有书籍，显示实时统计信息
- **阅读界面**: 沉浸式阅读体验，支持多种阅读模式
- **设置界面**: 个性化配置应用程序
- **统计界面**: 查看详细的阅读数据和趋势分析
- **老板键界面**: 快速切换到终端模拟环境

### 键盘快捷键

#### 📖 阅读操作
- `←`/`→` 或 `h`/`l`: 上一页/下一页
- `↑`/`↓` 或 `k`/`j`: 滚动内容
- `g`: 跳转到指定页码
- `空格`: 自动翻页开关
- `b`: 添加/管理书签
- `s`: 全文搜索
- `r`: 朗读功能开关

#### 🎨 界面设置
- `t`: 切换主题风格
- `l`: 切换语言
- `S`: 打开设置菜单
- `f`: 全屏切换
- `h`: 显示帮助信息
- `q`: 退出程序

#### 📚 书库管理
- `k`: 打开书库
- `a`: 添加新书籍
- `d`: 添加新书籍源目录
- `l`: 批量操作（支持标签管理、删除、导出）
- `E`: 导出阅读数据
- `c`: 查看阅读统计
- `C`: 查看全局统计
- `/`: 搜索书籍（支持文件类型筛选）

#### ⚡ 高级功能
- `Ctrl+B`: 老板键(切换到终端模式)
- `R`: 重置阅读进度
- `F`: 字体大小调整
- `W`: 每页字数设置
- `L`: 行间距调整
- `P`: 段落间距调整

## ⚙️ 配置说明

### 配置文件位置
默认配置文件位于: `~/.config/newreader/config.json`

### 主要配置选项

#### 外观设置
```json
{
  "appearance": {
    "theme": "dark",
    "border_style": "rounded",
    "show_icons": true,
    "animation_enabled": true,
    "progress_bar_style": "bar"
  }
}
```

#### 阅读设置
```json
{
  "reading": {
    "font_size": 16,
    "line_spacing": 1.2,
    "paragraph_spacing": 1.0,
    "auto_page_turn_interval": 30,
    "remember_position": true,
    "highlight_search": true,
    "margin_left": 2,
    "margin_right": 2
  }
}
```

#### 音频设置
```json
{
  "audio": {
    "tts_enabled": true,
    "tts_speed": 150,
    "tts_voice": "default",
    "tts_volume": 1.0
  }
}
```

#### 高级设置
```json
{
  "advanced": {
    "cache_size": 100,
    "language": "zh_CN",
    "book_directories": [],
    "statistics_enabled": true,
    "backup_enabled": true,
    "backup_interval": 7,
    "debug_mode": false
  }
}
```

## 🏗️ 架构设计

### 组件化架构
NewReader 采用完全组件化的统一架构，具有以下特点：

- **面向对象设计**: 每个组件都是独立的类，具有清晰的接口和生命周期
- **低耦合**: 组件之间通过事件和回调进行通信，减少直接依赖
- **高可扩展**: 通过组件工厂注册新组件，易于添加新功能
- **高可维护**: 每个组件独立维护，样式和逻辑分离

### 核心组件
- **BaseComponent**: 所有组件的抽象基类
- **ContentRenderer**: 内容渲染器组件，负责书籍内容的显示和分页
- **ReaderHeader**: 头部信息组件，显示书籍标题和阅读统计
- **ReaderControls**: 控制组件，处理用户交互逻辑
- **ComponentFactory**: 组件创建和管理工厂

### 解析器系统
- **PDF解析器**: 支持加密PDF，完善的密码输入功能
- **MOBI解析器**: 使用BeautifulSoup4提取HTML中的纯文本内容
- **AZW解析器**: 集成KindleUnpack库专门处理AZW文件
- **EPUB解析器**: 修复API兼容性问题，优化章节提取
- **TXT解析器**: 智能识别章节结构
- **MD解析器**: 支持Markdown格式解析

### 爬虫系统
- **87NB小说网**: 完整的小说爬取功能
- **任奇小说网**: 支持章节批量下载
- **自定义爬虫**: 可扩展的爬虫框架
- **代理支持**: 网络请求代理配置

## 🗂️ 项目结构

```
newreader/
├── src/
│   ├── config/          # 配置管理
│   │   ├── config_manager.py
│   │   ├── default_config.py
│   │   └── settings/    # 设置系统
│   │       ├── base_setting.py
│   │       ├── config_adapter.py
│   │       ├── setting_factory.py
│   │       ├── setting_observer.py
│   │       ├── setting_registry.py
│   │       ├── setting_section.py
│   │       └── setting_types.py
│   ├── core/           # 核心功能
│   │   ├── book.py     # 书籍模型
│   │   ├── reader.py   # 阅读器核心
│   │   ├── bookshelf.py # 书库管理
│   │   ├── statistics.py # 统计功能
│   │   ├── database_manager.py # 数据库管理
│   │   ├── pagination/ # 分页系统
│   │   └── reader_context.py # 阅读上下文
│   ├── ui/             # 用户界面
│   │   ├── app.py      # 主应用
│   │   ├── screens/    # 各个界面
│   │   ├── components/ # UI组件
│   │   ├── dialogs/   # 对话框
│   │   └── styles/     # 样式文件
│   ├── parsers/        # 文件解析器
│   │   ├── txt_parser.py
│   │   ├── epub_parser.py
│   │   ├── pdf_parser.py
│   │   ├── pdf_encrypt_parser.py
│   │   ├── mobi_parser.py
│   │   ├── azw_parser.py
│   │   ├── kindle_unpack_wrapper.py
│   │   ├── markdown_parser.py
│   │   ├── parser_factory.py
│   │   └── base_parser.py
│   ├── locales/        # 国际化
│   │   ├── i18n.py
│   │   ├── i18n_manager.py
│   │   ├── zh_CN/      # 中文语言包
│   │   └── en_US/      # 英文语言包
│   ├── themes/         # 主题管理
│   │   ├── theme_manager.py
│   │   └── modern_theme_manager.py
│   ├── spiders/        # 网络爬虫
│   │   ├── 87nb.py     # 87NB小说网爬虫
│   │   ├── renqixiaoshuo.py # 任奇小说网爬虫
│   │   ├── custom.py   # 自定义爬虫
│   │   └── library/    # 爬虫库文件
│   └── utils/          # 工具类
│       ├── logger.py
│       ├── file_utils.py
│       ├── string_utils.py
│       └── text_to_speech.py
├── main.py             # 程序入口
├── requirements.txt    # 依赖列表
├── README.md          # 项目说明
├── readme_iflow.md    # 详细说明文档
├── run.sh            # 运行脚本
├── reader.sh         # 快速启动脚本
└── library/          # 示例书籍库
```

## 🆕 最新功能

### 🔖 批量标签管理
- **批量设置标签**: 支持为多本书籍同时设置标签
- **批量清空标签**: 一键清空选中书籍的标签
- **智能选择**: 支持全选、反选、取消全选操作
- **实时预览**: 操作前显示选中书籍数量和预览
- **错误处理**: 完善的错误处理和用户反馈机制

### 🔍 增强搜索功能
- **文件类型筛选**: 支持按 TXT、EPUB、MOBI、PDF 等格式筛选搜索结果
- **下拉菜单**: 直观的文件类型选择界面
- **实时搜索**: 输入时实时更新搜索结果
- **格式感知**: 搜索结果显示书籍格式信息

### 📊 统计系统增强
- **全局统计**: 总阅读时间、书籍数量、作者排行
- **单本统计**: 每本书的阅读时间、页数、进度
- **趋势分析**: 7天、30天阅读趋势
- **数据导出**: 支持统计报告导出功能
- **实时刷新**: 书架页面自动显示统计信息

### 🔒 老板键功能
- **终端模拟**: 真实的命令行环境模拟
- **命令支持**: 支持基本终端命令 (ls, pwd, cd, cat, echo, date, whoami, clear, help, exit)
- **快速切换**: Ctrl+B 快速激活老板键
- **安全退出**: 支持多种退出方式

## 🔧 开发指南

### 依赖项
主要依赖库:
- `textual>=0.40.0`: 终端UI框架
- `rich>=13.5.0`: 富文本显示
- `ebooklib>=0.18`: EPUB解析
- `PyPDF2>=3.0.0`: PDF解析
- `mobi>=0.3.3`: MOBI解析
- `beautifulsoup4>=4.12.0`: HTML解析
- `pyttsx3>=2.90`: 文本朗读
- `lxml>=4.9.0`: XML/HTML解析
- `requests>=2.28.0`: 网络请求
- `pyfiglet>=0.8.post1`: ASCII艺术字体
- `pypinyin>=0.55.0`: 中文拼音转换

### 扩展开发
#### 添加新文件格式解析器
1. 在 `src/parsers/` 创建新的解析器类
2. 继承 `BaseParser` 类并实现必要方法
3. 在 `parser_factory.py` 中注册新解析器

#### 添加新主题
1. 在 `src/themes/` 中添加主题配置
2. 在 `theme_manager.py` 中注册新主题
3. 更新 `AVAILABLE_THEMES` 列表

#### 添加新语言
1. 在 `src/locales/` 创建新的语言目录
2. 创建 `translation.json` 翻译文件
3. 在 `i18n.py` 中注册新语言

#### 添加新组件
1. 继承 `BaseComponent` 基类
2. 实现必要的抽象方法
3. 在 `ComponentFactory` 中注册组件
4. 创建对应的样式定义

#### 添加新爬虫
1. 在 `src/spiders/` 创建新的爬虫类
2. 实现爬虫接口和解析逻辑
3. 在爬虫模块中注册新爬虫

## 🐛 故障排除

### 常见问题
1. **文件无法打开**: 检查文件格式是否支持，文件权限是否正确
2. **显示异常**: 尝试调整终端尺寸或字体设置
3. **性能问题**: 减少缓存大小或关闭动画效果
4. **解析失败**: 确保依赖库正确安装，特别是KindleUnpack库位置

### KindleUnpack库配置
确保KindleUnpack库位于正确位置：
```
other_project/KindleUnpack/
```

### 调试模式
启用调试模式获取详细日志:
```bash
python main.py --debug
```

日志文件位置: `~/.config/newreader/logs/`

## 📊 功能对比

| 功能 | NewReader | 其他终端阅读器 |
|------|-----------|----------------|
| 多格式支持 | ✅ 全面支持 | ⚠️ 有限支持 |
| 图形界面 | ✅ 现代化UI | ❌ 文本界面 |
| 多主题 | ✅ 15+主题 | ⚠️ 少量主题 |
| 多语言 | ✅ 中英文 | ❌ 仅英文 |
| 阅读统计 | ✅ 详细统计 | ⚠️ 基础统计 |
| 文本朗读 | ✅ TTS支持 | ❌ 不支持 |
| 书签管理 | ✅ 完整功能 | ⚠️ 基础功能 |
| 批量操作 | ✅ 支持 | ❌ 不支持 |
| 老板键 | ✅ 终端模拟 | ❌ 不支持 |
| 网络爬虫 | ✅ 内置支持 | ❌ 不支持 |

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Textual](https://textual.textualize.io/) - 优秀的终端UI框架
- [Rich](https://github.com/Textualize/rich) - 富文本显示库
- [KindleUnpack](https://github.com/kevinhendricks/KindleUnpack) - AZW文件解包工具
- 所有贡献者和用户的支持！

---

**享受阅读的乐趣！** 📚✨

如有问题或建议，请提交 Issue 或联系开发团队。