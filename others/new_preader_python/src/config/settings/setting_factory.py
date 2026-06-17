"""
设置项工厂
提供预定义的设置项创建函数
"""

from typing import Any, List, Optional, Callable, Dict
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.config.settings.setting_registry import SettingRegistry

from src.config.settings.setting_types import (

    BooleanSetting,

    IntegerSetting,

    FloatSetting,

    StringSetting,

    SelectSetting,

    ListSetting,

    SeparatorSetting

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
    
    # 阅读提醒时间间隔
    section.add_setting(IntegerSetting(
        key="reading.reminder_interval",
        default_value=1800,
        display_name="阅读提醒时间间隔",
        description="阅读提醒的时间间隔（秒），设置为0表示禁用提醒",
        min_value=0,
        max_value=7200,
        category="reading"
    ))
    
    # 启用阅读提醒
    section.add_setting(BooleanSetting(
        key="reading.reminder_enabled",
        default_value=True,
        display_name="启用阅读提醒",
        description="是否启用阅读提醒功能",
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

def create_translation_settings() -> SettingSection:
    """创建翻译相关设置项"""
    section = SettingSection(
        name="translation",
        display_name="翻译设置",
        description="配置第三方翻译API和翻译选项",
        icon="🌐",
        order=3
    )
    
    # 默认翻译服务
    section.add_setting(SelectSetting(
        key="translation.default_service",
        default_value="baidu",
        display_name="默认翻译服务",
        description="选择默认使用的翻译服务",
        options=["baidu", "youdao", "google", "microsoft"],
        option_labels=["百度翻译", "有道翻译", "Google翻译", "微软翻译"],
        category="translation"
    ))
    
    # 源语言
    section.add_setting(StringSetting(
        key="translation.source_language",
        default_value="auto",
        display_name="源语言",
        description="设置源语言（auto为自动检测）",
        category="translation"
    ))
    
    # 目标语言
    section.add_setting(StringSetting(
        key="translation.target_language",
        default_value="zh",
        display_name="目标语言",
        description="设置目标语言",
        category="translation"
    ))
    
    # 启用缓存
    section.add_setting(BooleanSetting(
        key="translation.cache_enabled",
        default_value=True,
        display_name="启用翻译缓存",
        description="是否启用翻译结果缓存",
        category="translation"
    ))
    
    # 缓存时长
    section.add_setting(IntegerSetting(
        key="translation.cache_duration",
        default_value=3600,
        display_name="缓存时长",
        description="翻译结果缓存时间（秒）",
        min_value=300,
        max_value=86400,
        category="translation"
    ))
    
    # 请求超时
    section.add_setting(IntegerSetting(
        key="translation.timeout",
        default_value=10,
        display_name="请求超时",
        description="翻译API请求超时时间（秒）",
        min_value=5,
        max_value=60,
        category="translation"
    ))
    
    # 重试次数
    section.add_setting(IntegerSetting(
        key="translation.retry_count",
        default_value=3,
        display_name="重试次数",
        description="翻译失败时的重试次数",
        min_value=0,
        max_value=10,
        category="translation"
    ))
    
    # 百度翻译配置
    section.add_setting(BooleanSetting(
        key="translation.translation_services.baidu.enabled",
        default_value=False,
        display_name="启用百度翻译",
        description="是否启用百度翻译服务",
        category="translation"
    ))
    
    section.add_setting(StringSetting(
        key="translation.translation_services.baidu.app_id",
        default_value="",
        display_name="百度翻译 App ID",
        description="百度翻译API的应用ID",
        category="translation"
    ))
    
    section.add_setting(StringSetting(
        key="translation.translation_services.baidu.app_key",
        default_value="",
        display_name="百度翻译 App Key",
        description="百度翻译API的应用密钥",
        category="translation"
    ))
    
    # 有道翻译配置
    section.add_setting(BooleanSetting(
        key="translation.translation_services.youdao.enabled",
        default_value=False,
        display_name="启用有道翻译",
        description="是否启用有道翻译服务",
        category="translation"
    ))
    
    section.add_setting(StringSetting(
        key="translation.translation_services.youdao.app_key",
        default_value="",
        display_name="有道翻译 App Key",
        description="有道翻译API的应用密钥",
        category="translation"
    ))
    
    section.add_setting(StringSetting(
        key="translation.translation_services.youdao.app_secret",
        default_value="",
        display_name="有道翻译 App Secret",
        description="有道翻译API的应用密钥",
        category="translation"
    ))
    
    # Google翻译配置
    section.add_setting(BooleanSetting(
        key="translation.translation_services.google.enabled",
        default_value=False,
        display_name="启用Google翻译",
        description="是否启用Google翻译服务",
        category="translation"
    ))
    
    section.add_setting(StringSetting(
        key="translation.translation_services.google.api_key",
        default_value="",
        display_name="Google翻译 API Key",
        description="Google翻译API的密钥",
        category="translation"
    ))
    
    # 微软翻译配置
    section.add_setting(BooleanSetting(
        key="translation.translation_services.microsoft.enabled",
        default_value=False,
        display_name="启用微软翻译",
        description="是否启用微软翻译服务",
        category="translation"
    ))
    
    section.add_setting(StringSetting(
        key="translation.translation_services.microsoft.subscription_key",
        default_value="",
        display_name="微软翻译订阅密钥",
        description="微软翻译API的订阅密钥",
        category="translation"
    ))
    
    section.add_setting(StringSetting(
        key="translation.translation_services.microsoft.region",
        default_value="global",
        display_name="微软翻译区域",
        description="微软翻译API的服务区域",
        category="translation"
    ))
    
    return section

def create_advanced_settings() -> SettingSection:
    """创建高级设置项"""
    section = SettingSection(
        name="advanced",
        display_name="高级设置",
        description="高级功能和系统配置选项",
        icon="⚙️",
        order=4
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

    # 启用多用户
    section.add_setting(BooleanSetting(
        key="advanced.multi_user_enabled",
        default_value=False,
        display_name="启用多用户",
        description="启用后，系统将使用用户登录和权限管理功能；禁用时，默认使用超级管理员权限",
        category="advanced"
    ))

    # 启用启动密码
    section.add_setting(BooleanSetting(
        key="advanced.password_enabled",
        default_value=False,
        display_name="启用启动密码",
        description="启用后，启动阅读器时需要输入密码",
        category="advanced"
    ))

    # 启动密码（明文）
    section.add_setting(StringSetting(
        key="advanced.password",
        default_value="",
        display_name="启动密码",
        description="设置启动时需要输入的密码（明文保存，便于忘记后修改）",
        category="advanced",
        is_hidden=False
    ))

    # 启用数据库自动清理
    section.add_setting(BooleanSetting(
        key="advanced.auto_vacuum_enabled",
        default_value=True,
        display_name="启用数据库自动清理",
        description="自动清理数据库中的空闲空间，避免数据库文件变得臃肿",
        category="advanced"
    ))
    
    return section

def create_browser_settings() -> SettingSection:
    """创建浏览器相关设置项"""
    section = SettingSection(
        name="browser",
        display_name="Browser",  # 将在UI中通过国际化显示
        description="Configure default browser and browser paths",  # 将在UI中通过国际化显示
        icon="🌐",
        order=5
    )
    
    # 默认浏览器
    section.add_setting(SelectSetting(
        key="browser.default_browser",
        default_value="chrome",
        display_name="Default Browser",  # 将在UI中通过国际化显示
        description="Select the default browser for opening web pages and browser reading",  # 将在UI中通过国际化显示
        options=["chrome", "safari", "brave"],
        option_labels=["Chrome", "Safari", "Brave"],  # 这些是浏览器名称，不需要国际化
        category="browser"
    ))
    
    # Chrome路径
    section.add_setting(StringSetting(
        key="browser.chrome_path",
        default_value="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        display_name="Chrome Path",  # 将在UI中通过国际化显示
        description="Chrome browser executable file path",  # 将在UI中通过国际化显示
        category="browser"
    ))
    
    # Safari路径
    section.add_setting(StringSetting(
        key="browser.safari_path",
        default_value="/Applications/Safari.app/Contents/MacOS/Safari",
        display_name="Safari Path",  # 将在UI中通过国际化显示
        description="Safari browser executable file path",  # 将在UI中通过国际化显示
        category="browser"
    ))
    
    # Brave路径
    section.add_setting(StringSetting(
        key="browser.brave_path",
        default_value="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        display_name="Brave Path",  # 将在UI中通过国际化显示
        description="Brave browser executable file path",  # 将在UI中通过国际化显示
        category="browser"
    ))

    # 起始页设置
    section.add_setting(SelectSetting(
        key="browser.start_page",
        default_value="last_book",
        display_name="Start Page",  # 将在UI中通过国际化显示
        description="Select the starting page for browser reader",  # 将在UI中通过国际化显示
        options=["last_book", "welcome"],
        option_labels=["Start Page: Last Read Book", "Start Page: Welcome Page"],
        category="browser"
    ))

    # 分隔线
    section.add_setting(SeparatorSetting(
        key="browser.server_separator",
        display_name="Browser Reader Server",  # 将在UI中通过国际化显示
        category="browser"
    ))
    
    # 服务器主机地址
    section.add_setting(StringSetting(
        key="browser_server.host",
        default_value="localhost",
        display_name="Server Host",  # 将在UI中通过国际化显示
        description="Host address for browser reader server (supports any address like 0.0.0.0, 192.168.1.100, etc.)",  # 将在UI中通过国际化显示
        category="browser"
    ))
    
    # 服务器端口
    section.add_setting(IntegerSetting(
        key="browser_server.port",
        default_value=54321,
        display_name="Server Port",  # 将在UI中通过国际化显示
        description="Port number for browser reader server (set to 0 for random port assignment)",  # 将在UI中通过国际化显示
        min_value=0,
        max_value=65535,
        category="browser"
    ))
    
    # 随机端口范围最小值
    section.add_setting(IntegerSetting(
        key="browser_server.port_range_min",
        default_value=10000,
        display_name="Random Port Range Min",  # 将在UI中通过国际化显示
        description="Minimum port for random port assignment (when port is 0)",  # 将在UI中通过国际化显示
        min_value=1024,
        max_value=60000,
        category="browser"
    ))
    
    # 随机端口范围最大值
    section.add_setting(IntegerSetting(
        key="browser_server.port_range_max",
        default_value=60000,
        display_name="Random Port Range Max",  # 将在UI中通过国际化显示
        description="Maximum port for random port assignment (when port is 0)",  # 将在UI中通过国际化显示
        min_value=1025,
        max_value=65535,
        category="browser"
    ))
    
    # 端口冲突最大重试次数
    section.add_setting(IntegerSetting(
        key="browser_server.max_retry_attempts",
        default_value=10,
        display_name="Max Retry Attempts",  # 将在UI中通过国际化显示
        description="Maximum retry attempts when port conflict occurs",  # 将在UI中通过国际化显示
        min_value=1,
        max_value=50,
        category="browser"
    ))
    
    return section

def create_path_settings() -> SettingSection:
    """创建路径相关设置项"""
    section = SettingSection(
        name="paths",
        display_name="路径设置",
        description="配置文件和目录路径设置",
        icon="📁",
        order=6
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
        create_translation_settings(),
        create_advanced_settings(),
        create_browser_settings(),
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