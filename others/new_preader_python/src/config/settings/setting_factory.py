"""
设置项工厂
提供预定义的设置项创建函数
"""

from typing import Any, List, Optional, Callable, Dict
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.config.settings.setting_registry import SettingRegistry

from src.config.settings.setting_types import (
    BooleanSetting, IntegerSetting, FloatSetting,
    StringSetting, SelectSetting, ListSetting
)
from src.config.settings.setting_section import SettingSection
from src.config.default_config import (
    AVAILABLE_THEMES, AVAILABLE_LANGUAGES, BORDER_STYLES
)

def create_appearance_settings() -> SettingSection:
    """创建外观相关设置项"""
    section = SettingSection(
        name="appearance",
        display_name="外观设置",
        description="自定义应用程序的外观和主题",
        icon="🎨",
        order=0
    )
    
    # 主题设置
    section.add_setting(SelectSetting(
        key="appearance.theme",
        default_value="dark",
        display_name="主题",
        description="选择应用程序的主题风格",
        options=AVAILABLE_THEMES,
        option_labels=[theme.capitalize() for theme in AVAILABLE_THEMES],
        category="appearance"
    ))
    
    # UI主题设置（兼容性设置）
    section.add_setting(SelectSetting(
        key="appearance.ui_theme",
        default_value="dark",
        display_name="UI主题",
        description="选择UI界面的主题风格",
        options=AVAILABLE_THEMES,
        option_labels=[theme.capitalize() for theme in AVAILABLE_THEMES],
        category="appearance"
    ))
    
    # 边框样式
    section.add_setting(SelectSetting(
        key="appearance.border_style",
        default_value="rounded",
        display_name="边框样式",
        description="选择界面元素的边框样式",
        options=BORDER_STYLES,
        option_labels=[style.capitalize() for style in BORDER_STYLES],
        category="appearance"
    ))
    
    # 显示图标
    section.add_setting(BooleanSetting(
        key="appearance.show_icons",
        default_value=True,
        display_name="显示图标",
        description="是否在界面中显示图标",
        category="appearance"
    ))
    
    # 启用动画
    section.add_setting(BooleanSetting(
        key="appearance.animation_enabled",
        default_value=True,
        display_name="启用动画",
        description="是否启用界面动画效果",
        category="appearance"
    ))
    
    # 进度条样式
    section.add_setting(SelectSetting(
        key="appearance.progress_bar_style",
        default_value="bar",
        display_name="进度条样式",
        description="选择阅读进度条的显示样式",
        options=["bar", "percentage", "both"],
        option_labels=["进度条", "百分比", "两者都显示"],
        category="appearance"
    ))
    
    return section

def create_reading_settings() -> SettingSection:
    """创建阅读相关设置项"""
    section = SettingSection(
        name="reading",
        display_name="阅读设置",
        description="自定义阅读体验和显示选项",
        icon="📖",
        order=1
    )
    
    # 字体大小
    section.add_setting(IntegerSetting(
        key="reading.font_size",
        default_value=16,
        display_name="字体大小",
        description="设置阅读界面的字体大小",
        min_value=8,
        max_value=32,
        category="reading"
    ))
    
    # 行间距
    section.add_setting(IntegerSetting(
        key="reading.line_spacing",
        default_value=1,
        display_name="行间距",
        description="设置文本的行间距（0-5整数）",
        min_value=0,
        max_value=5,
        category="reading"
    ))
    
    # 段落间距
    section.add_setting(IntegerSetting(
        key="reading.paragraph_spacing",
        default_value=1,
        display_name="段落间距",
        description="设置段落的间距（0-5整数）",
        min_value=0,
        max_value=5,
        category="reading"
    ))
    
    # 自动翻页间隔
    section.add_setting(IntegerSetting(
        key="reading.auto_page_turn_interval",
        default_value=30,
        display_name="自动翻页间隔",
        description="自动翻页的时间间隔（秒）",
        min_value=5,
        max_value=300,
        category="reading"
    ))
    
    # 记住阅读位置
    section.add_setting(BooleanSetting(
        key="reading.remember_position",
        default_value=True,
        display_name="记住阅读位置",
        description="是否自动记住每本书的阅读位置",
        category="reading"
    ))
    
    # 高亮搜索结果
    section.add_setting(BooleanSetting(
        key="reading.highlight_search",
        default_value=True,
        display_name="高亮搜索结果",
        description="是否在文本中高亮显示搜索结果",
        category="reading"
    ))
    
    # 左边距
    section.add_setting(IntegerSetting(
        key="reading.margin_left",
        default_value=2,
        display_name="左边距",
        description="设置文本的左边界距（字符数）",
        min_value=0,
        max_value=10,
        category="reading"
    ))
    
    # 右边距
    section.add_setting(IntegerSetting(
        key="reading.margin_right",
        default_value=2,
        display_name="右边距",
        description="设置文本的右边界距（字符数）",
        min_value=0,
        max_value=10,
        category="reading"
    ))
    
    return section

def create_audio_settings() -> SettingSection:
    """创建音频相关设置项"""
    section = SettingSection(
        name="audio",
        display_name="音频设置",
        description="配置文本朗读和音频选项",
        icon="🔊",
        order=2
    )
    
    # 启用文本朗读
    section.add_setting(BooleanSetting(
        key="audio.tts_enabled",
        default_value=True,
        display_name="启用文本朗读",
        description="是否启用文本转语音功能",
        category="audio"
    ))
    
    # 朗读速度
    section.add_setting(IntegerSetting(
        key="audio.tts_speed",
        default_value=150,
        display_name="朗读速度",
        description="设置朗读速度（每分钟字数）",
        min_value=50,
        max_value=300,
        category="audio"
    ))
    
    # 朗读声音
    section.add_setting(SelectSetting(
        key="audio.tts_voice",
        default_value="female",
        display_name="朗读声音",
        description="设置朗读声音类型",
        options=["child", "female", "male"],
        option_labels=["儿童", "女声", "男声"],
        category="audio"
    ))
    
    # 朗读音量
    section.add_setting(FloatSetting(
        key="audio.tts_volume",
        default_value=1.0,
        display_name="朗读音量",
        description="设置朗读音量大小",
        min_value=0.0,
        max_value=1.0,
        category="audio"
    ))
    
    return section

def create_advanced_settings() -> SettingSection:
    """创建高级设置项"""
    section = SettingSection(
        name="advanced",
        display_name="高级设置",
        description="高级功能和系统配置选项",
        icon="⚙️",
        order=3
    )
    
    # 界面语言
    section.add_setting(SelectSetting(
        key="advanced.language",
        default_value="zh_CN",
        display_name="界面语言",
        description="选择应用程序的界面语言",
        options=AVAILABLE_LANGUAGES,
        option_labels=["简体中文", "English"],
        category="advanced"
    ))
    
    # 缓存大小
    section.add_setting(IntegerSetting(
        key="advanced.cache_size",
        default_value=100,
        display_name="缓存大小",
        description="设置缓存大小（MB）",
        min_value=10,
        max_value=1000,
        category="advanced"
    ))
    
    # 启用统计
    section.add_setting(BooleanSetting(
        key="advanced.statistics_enabled",
        default_value=True,
        display_name="启用阅读统计",
        description="是否记录和显示阅读统计信息",
        category="advanced"
    ))
    
    # 启用备份
    section.add_setting(BooleanSetting(
        key="advanced.backup_enabled",
        default_value=True,
        display_name="启用自动备份",
        description="是否自动备份阅读进度和书签",
        category="advanced"
    ))
    
    # 备份间隔
    section.add_setting(IntegerSetting(
        key="advanced.backup_interval",
        default_value=7,
        display_name="备份间隔",
        description="自动备份的时间间隔（天）",
        min_value=1,
        max_value=30,
        category="advanced"
    ))
    
    # 调试模式
    section.add_setting(BooleanSetting(
        key="advanced.debug_mode",
        default_value=False,
        display_name="调试模式",
        description="启用调试模式，显示更多日志信息",
        category="advanced"
    ))
    
    return section

def create_path_settings() -> SettingSection:
    """创建路径相关设置项"""
    section = SettingSection(
        name="paths",
        display_name="路径设置",
        description="配置文件和目录路径设置",
        icon="📁",
        order=4
    )
    
    # 配置目录
    section.add_setting(StringSetting(
        key="paths.config_dir",
        default_value="~/.config/new_preader",
        display_name="配置目录",
        description="配置文件存储目录",
        category="paths"
    ))
    
    # 数据库路径
    section.add_setting(StringSetting(
        key="paths.database",
        default_value="~/.config/new_preader/database.sqlite",
        display_name="数据库文件",
        description="SQLite数据库文件路径",
        category="paths"
    ))
    
    # 书籍库路径
    section.add_setting(StringSetting(
        key="paths.library",
        default_value="~/Documents/NewReader/books",
        display_name="书籍库目录",
        description="默认书籍存储目录",
        category="paths"
    ))
    
    return section

def create_all_settings() -> List[SettingSection]:
    """
    创建所有预定义设置项分组
    
    Returns:
        List[SettingSection]: 所有设置项分组列表
    """
    return [
        create_appearance_settings(),
        create_reading_settings(),
        create_audio_settings(),
        create_advanced_settings(),
        create_path_settings()
    ]

def initialize_settings_registry(registry: 'SettingRegistry') -> None:
    """
    初始化设置项注册表
    
    Args:
        registry: SettingRegistry实例
    """
    sections = create_all_settings()
    for section in sections:
        registry.register_section(section)