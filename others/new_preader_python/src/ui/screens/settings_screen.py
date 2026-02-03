"""
现代化设置屏幕
使用新的面向对象设置系统
"""


import os
from typing import Any, Dict, Optional, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, Select, Switch, Input, TabbedContent, TabPane, Header, Footer, Pretty
from src.ui.components.slider import Slider
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from textual.reactive import reactive
from textual import on, events
from textual.app import ComposeResult

from src.locales.i18n import I18n
from src.locales.i18n_manager import set_global_locale, get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.config.config_manager import ConfigManager
from src.config.settings import SettingRegistry, ConfigAdapter, initialize_settings_registry
from src.config.settings.setting_observer import notify_setting_change
from src.config.settings.setting_types import SelectSetting

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 公共函数：判断当前语言是否为中文
def is_chinese_locale() -> bool:
    try:
        i18n = get_global_i18n()
        locale = getattr(i18n, "current_locale", None)
        if not locale and hasattr(i18n, "get_current_locale"):
            try:
                locale = i18n.get_current_locale()
            except Exception:
                locale = None
        if isinstance(locale, str):
            low = locale.lower()
            return ("zh" in low) or (low in ("zh_cn", "zh-cn", "zh_hans", "zh-hans"))
        return False
    except Exception:
        return False

# 公共函数：根据当前语言返回 (label, value) 列表
def options_by_locale(options, labels):
    try:
        if is_chinese_locale():
            # 中文显示 labels，值用 options
            return [(label, value) for value, label in zip(options, labels)]
        # 非中文显示 options 作为文本，值仍用 options
        return [(label, value) for value, label in zip(options, options)]
    except Exception:
        # 兜底：用 options
        return [(str(v), v) for v in (options or [])]

class SettingsScreen(Screen[Any]):
    """现代化设置屏幕"""
    
    CSS_PATH = "../styles/settings_overrides.tcss"
    

    
    def __init__(
        self, 
        theme_manager: ThemeManager, 
        config_manager: ConfigManager
    ):
        """
        初始化现代化设置屏幕
        
        Args:
            theme_manager: 主题管理器
            config_manager: 配置管理器
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.config_manager = config_manager
        
        # 设置快捷键绑定
        self.BINDINGS = [
            ("enter", "press('#save-btn')", get_global_i18n().t("settings.save")),
            ("r", "press('#reset-btn')", get_global_i18n().t("settings.reset")),
        ]
        
        # 初始化设置系统
        self.setting_registry = SettingRegistry()
        initialize_settings_registry(self.setting_registry)
        self.config_adapter = ConfigAdapter(config_manager, self.setting_registry)
        
        # 从配置加载设置值
        self.config_adapter.load_config_to_settings()
        
        self.title = get_global_i18n().t("settings.title")
    
    def compose(self) -> ComposeResult:
        """
        组合设置屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        with Container(id="settings-container"):
            # yield Horizontal(
            #     Label(get_global_i18n().t("settings.title"), id="settings-title", classes="settings-title"), 
            #     id="settings-title-container"
            #     )

            with TabbedContent():
                # 外观设置标签页
                with TabPane(get_global_i18n().t("settings.appearance"), id="appearance-tab"):
                    yield from self._compose_appearance_settings()
                
                # 阅读设置标签页
                with TabPane(get_global_i18n().t("settings.reading"), id="reading-tab"):
                    yield from self._compose_reading_settings()
                
                # 音频设置标签页
                with TabPane(get_global_i18n().t("settings.audio"), id="audio-tab"):
                    yield from self._compose_audio_settings()
                
                # 翻译设置标签页
                with TabPane(get_global_i18n().t("settings.translation"), id="translation-tab"):
                    yield from self._compose_translation_settings()
                
                # 数据库管理标签页
                with TabPane(get_global_i18n().t("settings.database_management"), id="database-tab"):
                    yield from self._compose_database_settings()
                
                # 浏览器设置标签页
                with TabPane(get_global_i18n().t("settings.browser"), id="browser-tab"):
                    yield from self._compose_browser_settings()
                
                # 高级设置标签页
                with TabPane(get_global_i18n().t("settings.advanced"), id="advanced-tab"):
                    yield from self._compose_advanced_settings()

                # 预览配置文件标签页
                with TabPane(get_global_i18n().t("settings.view-config"), id="preview-config-tab"):
                    yield from self._compose_preview_config_settings()
                

            
            # 控制按钮
            with Horizontal(id="settings-controls", classes="btn-row"):
                yield Button(get_global_i18n().t("settings.save"), id="save-btn", variant="primary")
                yield Button(get_global_i18n().t("settings.cancel"), id="cancel-btn")
                yield Button(get_global_i18n().t("settings.reset"), id="reset-btn", variant="warning")
            
            # 快捷键状态栏
            # with Horizontal(id="settings-shortcuts-bar", classes="status-bar"):
            #     yield Label(f"Enter: {get_global_i18n().t("common.save")}", id="shortcut-enter")
            #     yield Label(f"ESC: {get_global_i18n().t("common.cancel")}", id="shortcut-esc")
            #     yield Label(f"R: {get_global_i18n().t("common.reset")}", id="shortcut-reset")
        yield Footer()
    
    def _compose_appearance_settings(self) -> ComposeResult:
        """组合外观设置"""
        with ScrollableContainer(id="appearance-settings", classes="settings-scrollable"):
            # 主题设置
            yield Label(get_global_i18n().t("settings.theme"), classes="setting-label")
            theme_setting = self.setting_registry.get_setting("appearance.theme")
            if theme_setting and isinstance(theme_setting, SelectSetting):
                yield Select(
                    [(label, value) for value, label in zip(theme_setting.options, theme_setting.option_labels)],
                    value=theme_setting.value,
                    id="appearance-theme-select"
                )
            
            # 边框样式
            yield Label(get_global_i18n().t("settings.border_style"), classes="setting-label hidden")
            border_setting = self.setting_registry.get_setting("appearance.border_style")
            if border_setting and isinstance(border_setting, SelectSetting):
                yield Select(
                    [(label, value) for value, label in zip(border_setting.options, border_setting.option_labels)],
                    value=border_setting.value,
                    id="appearance-border-select",
                    classes="hidden"
                )
            
            # 显示图标
            yield Label(get_global_i18n().t("settings.show_icons"), classes="setting-label")
            icons_setting = self.setting_registry.get_setting("appearance.show_icons")
            if icons_setting:
                yield Switch(
                    value=icons_setting.value,
                    id="appearance-icons-switch"
                )
            
            # 启用动画
            yield Label(get_global_i18n().t("settings.animation_enabled"), classes="setting-label")
            animation_setting = self.setting_registry.get_setting("appearance.animation_enabled")
            if animation_setting:
                yield Switch(
                    value=animation_setting.value,
                    id="appearance-animation-switch"
                )
            
            # 进度条样式
            yield Label(get_global_i18n().t("settings.progress_bar_style"), classes="setting-label")
            progress_setting = self.setting_registry.get_setting("appearance.progress_bar_style")
            if progress_setting and isinstance(progress_setting, SelectSetting):
                options_text = options_by_locale(progress_setting.options, progress_setting.option_labels)
                yield Select(
                    options_text,
                    value=progress_setting.value,
                    id="appearance-progress-select"
                )
    
    def _compose_reading_settings(self) -> ComposeResult:
        """组合阅读设置"""
        with ScrollableContainer(id="reading-settings"):
            # 字体大小
            yield Label(get_global_i18n().t("settings.font_size"), classes="setting-label")
            font_setting = self.setting_registry.get_setting("reading.font_size")
            if font_setting:
                yield Input(
                    str(font_setting.value),
                    id="reading-font-size-input",
                    type="number"
                )
            

            # 行间距
            yield Label(get_global_i18n().t("settings.line_spacing"), classes="setting-label")
            spacing_setting = self.setting_registry.get_setting("reading.line_spacing")
            if spacing_setting:
                yield Select(
                    [
                        (f"0 ({get_global_i18n().t("settings.compact")})", 0),
                        (f"1 ({get_global_i18n().t("settings.standard")})", 1),
                        (f"2 ({get_global_i18n().t("settings.loose")})", 2),
                        (f"3 ({get_global_i18n().t("settings.looser")})", 3),
                        (f"4 ({get_global_i18n().t("settings.loosest")})", 4),
                        (f"5 ({get_global_i18n().t("settings.max")})", 5)
                    ],
                    value=spacing_setting.value,
                    id="reading-spacing-select"
                )
            
            # 段落间距
            yield Label(get_global_i18n().t("settings.paragraph_spacing"), classes="setting-label")
            para_setting = self.setting_registry.get_setting("reading.paragraph_spacing")
            if para_setting:
                yield Select(
                    [
                        (f"0 ({get_global_i18n().t("settings.compact")})", 0),
                        (f"1 ({get_global_i18n().t("settings.standard")})", 1),
                        (f"2 ({get_global_i18n().t("settings.loose")})", 2),
                        (f"3 ({get_global_i18n().t("settings.looser")})", 3),
                        (f"4 ({get_global_i18n().t("settings.loosest")})", 4),
                        (f"5 ({get_global_i18n().t("settings.max")})", 5)
                    ],
                    value=para_setting.value,
                    id="reading-para-select"
                )
            
            # 自动翻页间隔
            yield Label(get_global_i18n().t("settings.auto_page_turn_interval"), classes="setting-label")
            auto_setting = self.setting_registry.get_setting("reading.auto_page_turn_interval")
            if auto_setting:
                yield Input(
                    str(auto_setting.value),
                    id="reading-auto-input",
                    type="number"
                )
            
            # 记住阅读位置
            yield Label(get_global_i18n().t("settings.remember_position"), classes="setting-label")
            remember_setting = self.setting_registry.get_setting("reading.remember_position")
            if remember_setting:
                yield Switch(
                    value=remember_setting.value,
                    id="reading-remember-switch"
                )
            
            # 高亮搜索结果
            yield Label(get_global_i18n().t("settings.highlight_search"), classes="setting-label")
            highlight_setting = self.setting_registry.get_setting("reading.highlight_search")
            if highlight_setting:
                yield Switch(
                    value=highlight_setting.value,
                    id="reading-highlight-switch"
                )
            
            # 启用阅读提醒
            yield Label(get_global_i18n().t("settings.reminder_enabled"), classes="setting-label")
            reminder_enabled_setting = self.setting_registry.get_setting("reading.reminder_enabled")
            if reminder_enabled_setting:
                yield Switch(
                    value=reminder_enabled_setting.value,
                    id="reading-reminder-enabled-switch"
                )
            
            # 阅读提醒时间间隔
            yield Label(get_global_i18n().t("settings.reminder_interval"), classes="setting-label")
            reminder_interval_setting = self.setting_registry.get_setting("reading.reminder_interval")
            if reminder_interval_setting:
                yield Input(
                    str(reminder_interval_setting.value),
                    id="reading-reminder-interval-input",
                    type="number"
                )
    
    def _compose_audio_settings(self) -> ComposeResult:
        """组合音频设置"""
        with ScrollableContainer(id="audio-settings"):
            # 启用文本朗读
            yield Label(get_global_i18n().t("settings.tts_enabled"), classes="setting-label")
            tts_setting = self.setting_registry.get_setting("audio.tts_enabled")
            if tts_setting:
                yield Switch(
                    value=tts_setting.value,
                    id="audio-tts-switch"
                )
            
            # 朗读速度
            yield Label(get_global_i18n().t("settings.tts_speed"), classes="setting-label")
            speed_setting = self.setting_registry.get_setting("audio.tts_speed")
            if speed_setting:
                yield Input(
                    str(speed_setting.value),
                    id="audio-speed-input",
                    type="number"
                )
            
            # 朗读声音
            yield Label(get_global_i18n().t("settings.tts_voice"), classes="setting-label")
            voice_setting = self.setting_registry.get_setting("audio.tts_voice")
            if voice_setting and isinstance(voice_setting, SelectSetting):
                options_text = options_by_locale(voice_setting.options, voice_setting.option_labels)
                yield Select(
                    options=options_text,
                    value=voice_setting.value,
                    id="audio-voice-select"
                )
            
            # 朗读音量
            yield Label(get_global_i18n().t("settings.tts_volume"), classes="setting-label")
            volume_setting = self.setting_registry.get_setting("audio.tts_volume")
            if volume_setting:
                yield Input(
                    str(volume_setting.value),
                    id="audio-volume-input",
                    type="number"
                )
    
    def _compose_translation_settings(self) -> ComposeResult:
        """组合翻译设置"""
        with ScrollableContainer(id="translation-settings"):
            # 默认翻译服务
            yield Label(get_global_i18n().t("settings.default_translation_service"), classes="setting-label")
            service_setting = self.setting_registry.get_setting("translation.default_service")
            if service_setting and isinstance(service_setting, SelectSetting):
                options_text = options_by_locale(service_setting.options, service_setting.option_labels)
                yield Select(
                    options_text,
                    value=service_setting.value,
                    id="translation-service-select"
                )
            
            # 源语言
            yield Label(get_global_i18n().t("settings.source_language"), classes="setting-label")
            source_setting = self.setting_registry.get_setting("translation.source_language")
            if source_setting:
                yield Input(
                    str(source_setting.value),
                    id="translation-source-input"
                )
            
            # 目标语言
            yield Label(get_global_i18n().t("settings.target_language"), classes="setting-label")
            target_setting = self.setting_registry.get_setting("translation.target_language")
            if target_setting:
                yield Input(
                    str(target_setting.value),
                    id="translation-target-input"
                )
            
            # 启用缓存
            yield Label(get_global_i18n().t("settings.translation_cache_enabled"), classes="setting-label")
            cache_setting = self.setting_registry.get_setting("translation.cache_enabled")
            if cache_setting:
                yield Switch(
                    value=cache_setting.value,
                    id="translation-cache-switch"
                )
            
            # 缓存时长
            yield Label(get_global_i18n().t("settings.cache_duration"), classes="setting-label")
            duration_setting = self.setting_registry.get_setting("translation.cache_duration")
            if duration_setting:
                yield Input(
                    str(duration_setting.value),
                    id="translation-duration-input",
                    type="number"
                )
            
            # 请求超时
            yield Label(get_global_i18n().t("settings.request_timeout"), classes="setting-label")
            timeout_setting = self.setting_registry.get_setting("translation.timeout")
            if timeout_setting:
                yield Input(
                    str(timeout_setting.value),
                    id="translation-timeout-input",
                    type="number"
                )
            
            # 重试次数
            yield Label(get_global_i18n().t("settings.retry_count"), classes="setting-label")
            retry_setting = self.setting_registry.get_setting("translation.retry_count")
            if retry_setting:
                yield Input(
                    str(retry_setting.value),
                    id="translation-retry-input",
                    type="number"
                )
            
            # 翻译服务API配置
            yield Label(get_global_i18n().t("settings.translation_services"), classes="setting-section-title")
            
            # 百度翻译配置
            yield Label(get_global_i18n().t("settings.baidu_translation"), classes="setting-subtitle")
            baidu_enabled = self.setting_registry.get_setting("translation.translation_services.baidu.enabled")
            if baidu_enabled:
                yield Switch(
                    value=baidu_enabled.value,
                    id="baidu-enabled-switch"
                )
                yield Label(get_global_i18n().t("settings.baidu_app_id"), classes="setting-label")
                baidu_app_id = self.setting_registry.get_setting("translation.translation_services.baidu.app_id")
                if baidu_app_id:
                    yield Input(
                        value=baidu_app_id.value,
                        placeholder=baidu_app_id.default_value,
                        id="baidu-app-id-input",
                        password=True
                    )
                yield Label(get_global_i18n().t("settings.baidu_app_key"), classes="setting-label")
                baidu_app_key = self.setting_registry.get_setting("translation.translation_services.baidu.app_key")
                if baidu_app_key:
                    yield Input(
                        value=baidu_app_key.value,
                        placeholder=baidu_app_key.default_value,
                        id="baidu-app-key-input",
                        password=True
                    )
            
            # 有道翻译配置
            yield Label(get_global_i18n().t("settings.youdao_translation"), classes="setting-subtitle")
            youdao_enabled = self.setting_registry.get_setting("translation.translation_services.youdao.enabled")
            if youdao_enabled:
                yield Switch(
                    value=youdao_enabled.value,
                    id="youdao-enabled-switch"
                )
                yield Label(get_global_i18n().t("settings.youdao_app_key"), classes="setting-label")
                youdao_app_key = self.setting_registry.get_setting("translation.translation_services.youdao.app_key")
                if youdao_app_key:
                    yield Input(
                        value=youdao_app_key.value,
                        placeholder=youdao_app_key.default_value,
                        id="youdao-app-key-input",
                        password=True
                    )
                yield Label(get_global_i18n().t("settings.youdao_app_secret"), classes="setting-label")
                youdao_app_secret = self.setting_registry.get_setting("translation.translation_services.youdao.app_secret")
                if youdao_app_secret:
                    yield Input(
                        value=youdao_app_secret.value,
                        placeholder=youdao_app_secret.default_value,
                        id="youdao-app-secret-input",
                        password=True
                    )
            
            # Google翻译配置
            yield Label(get_global_i18n().t("settings.google_translation"), classes="setting-subtitle")
            google_enabled = self.setting_registry.get_setting("translation.translation_services.google.enabled")
            if google_enabled:
                yield Switch(
                    value=google_enabled.value,
                    id="google-enabled-switch"
                )
                yield Label(get_global_i18n().t("settings.google_api_key"), classes="setting-label")
                google_api_key = self.setting_registry.get_setting("translation.translation_services.google.api_key")
                if google_api_key:
                    yield Input(
                        value=google_api_key.value,
                        placeholder=google_api_key.default_value,
                        id="google-api-key-input",
                        password=True
                    )
            
            # 微软翻译配置
            yield Label(get_global_i18n().t("settings.microsoft_translation"), classes="setting-subtitle")
            microsoft_enabled = self.setting_registry.get_setting("translation.translation_services.microsoft.enabled")
            if microsoft_enabled:
                yield Switch(
                    value=microsoft_enabled.value,
                    id="microsoft-enabled-switch"
                )
                yield Label(get_global_i18n().t("settings.microsoft_subscription_key"), classes="setting-label")
                microsoft_key = self.setting_registry.get_setting("translation.translation_services.microsoft.subscription_key")
                if microsoft_key:
                    yield Input(
                        value=microsoft_key.value,
                        placeholder=microsoft_key.default_value,
                        id="microsoft-key-input",
                        password=True
                    )
                yield Label(get_global_i18n().t("settings.microsoft_region"), classes="setting-label")
                microsoft_region = self.setting_registry.get_setting("translation.translation_services.microsoft.region")
                if microsoft_region:
                    yield Input(
                        value=microsoft_region.value,
                        placeholder=microsoft_region.default_value,
                        id="microsoft-region-input"
                    )

    def _compose_browser_settings(self) -> ComposeResult:
        """组合浏览器设置"""
        with ScrollableContainer(id="browser-settings"):
            # 默认浏览器
            yield Label(get_global_i18n().t("settings.default_browser"), classes="setting-label")
            browser_setting = self.setting_registry.get_setting("browser.default_browser")
            if browser_setting and isinstance(browser_setting, SelectSetting):
                options_text = options_by_locale(browser_setting.options, browser_setting.option_labels)
                yield Select(
                    options_text,
                    value=browser_setting.value,
                    id="browser-default-select"
                )
            
            # Chrome路径
            yield Label(get_global_i18n().t("settings.chrome_path"), classes="setting-label")
            chrome_setting = self.setting_registry.get_setting("browser.chrome_path")
            if chrome_setting:
                yield Input(
                    value=chrome_setting.value,
                    id="browser-chrome-input",
                    placeholder=chrome_setting.default_value
                )
            
            # Safari路径
            yield Label(get_global_i18n().t("settings.safari_path"), classes="setting-label")
            safari_setting = self.setting_registry.get_setting("browser.safari_path")
            if safari_setting:
                yield Input(
                    value=safari_setting.value,
                    id="browser-safari-input",
                    placeholder=safari_setting.default_value
                )
            
            # Brave路径
            yield Label(get_global_i18n().t("settings.brave_path"), classes="setting-label")
            brave_setting = self.setting_registry.get_setting("browser.brave_path")
            if brave_setting:
                yield Input(
                    value=brave_setting.value,
                    id="browser-brave-input",
                    placeholder=brave_setting.default_value
                )
            
            # 分隔线
            yield Static("─", classes="setting-separator")
            yield Label(get_global_i18n().t("settings.browser_server"), classes="setting-section-title")
            
            # 服务器主机地址
            host_setting = self.setting_registry.get_setting("browser_server.host")
            if host_setting:
                yield Label(get_global_i18n().t("settings.server_host"), classes="setting-label")
                yield Input(
                    value=host_setting.value,
                    id="browser-server-host-input",
                    placeholder=host_setting.default_value
                )
            
            # 服务器端口
            port_setting = self.setting_registry.get_setting("browser_server.port")
            if port_setting:
                yield Label(get_global_i18n().t("settings.server_port"), classes="setting-label")
                yield Input(
                    value=str(port_setting.value),
                    id="browser-server-port-input",
                    placeholder=str(port_setting.default_value)
                )
            
            # 随机端口范围最小值
            port_range_min_setting = self.setting_registry.get_setting("browser_server.port_range_min")
            if port_range_min_setting:
                yield Label(get_global_i18n().t("settings.port_range_min"), classes="setting-label")
                yield Input(
                    value=str(port_range_min_setting.value),
                    id="browser-server-port-range-min-input",
                    placeholder=str(port_range_min_setting.default_value)
                )
            
            # 随机端口范围最大值
            port_range_max_setting = self.setting_registry.get_setting("browser_server.port_range_max")
            if port_range_max_setting:
                yield Label(get_global_i18n().t("settings.port_range_max"), classes="setting-label")
                yield Input(
                    value=str(port_range_max_setting.value),
                    id="browser-server-port-range-max-input",
                    placeholder=str(port_range_max_setting.default_value)
                )
            
            # 最大重试次数
            max_retry_setting = self.setting_registry.get_setting("browser_server.max_retry_attempts")
            if max_retry_setting:
                yield Label(get_global_i18n().t("settings.max_retry_attempts"), classes="setting-label")
                yield Input(
                    value=str(max_retry_setting.value),
                    id="browser-server-max-retry-input",
                    placeholder=str(max_retry_setting.default_value)
                )
            
            # 端口检测按钮和状态
            yield Label(get_global_i18n().t("settings.check_port"), classes="setting-label")
            with Horizontal(id="browser-server-check-area"):
                yield Button(
                    get_global_i18n().t('settings.check_port'),
                    id="browser-server-check-port-btn",
                    variant="primary"
                )
                yield Static(
                    get_global_i18n().t("settings.port_not_checked", default="Not checked"),
                    id="browser-server-port-status",
                    classes="port-status"
                )

    def _compose_advanced_settings(self) -> ComposeResult:
        """组合高级设置"""
        with ScrollableContainer(id="advanced-settings"):
            # 界面语言
            yield Label(get_global_i18n().t("settings.language"), classes="setting-label")
            lang_setting = self.setting_registry.get_setting("advanced.language")
            if lang_setting and isinstance(lang_setting, SelectSetting):
                yield Select(
                    [(label, value) for value, label in zip(lang_setting.options, lang_setting.option_labels)],
                    value=lang_setting.value,
                    id="advanced-language-select"
                )
            
            # 启用统计
            yield Label(get_global_i18n().t("settings.statistics_enabled"), classes="setting-label")
            stats_setting = self.setting_registry.get_setting("advanced.statistics_enabled")
            if stats_setting:
                yield Switch(
                    value=stats_setting.value,
                    id="advanced-stats-switch"
                )
            
            # 调试模式
            yield Label(get_global_i18n().t("settings.debug_mode"), classes="setting-label")
            debug_setting = self.setting_registry.get_setting("advanced.debug_mode")
            if debug_setting:
                yield Switch(
                    value=debug_setting.value,
                    id="advanced-debug-switch"
                )

            # 启用多用户
            yield Label(get_global_i18n().t("settings.multi_user_enabled"), classes="setting-label")
            multi_user_setting = self.setting_registry.get_setting("advanced.multi_user_enabled")
            if multi_user_setting:
                yield Switch(
                    value=multi_user_setting.value,
                    id="advanced-multi-user-switch"
                )

            # 启用启动密码
            yield Label(get_global_i18n().t("settings.password_enabled"), classes="setting-label")
            pwd_enabled_setting = self.setting_registry.get_setting("advanced.password_enabled")
            if pwd_enabled_setting:
                yield Switch(
                    value=pwd_enabled_setting.value,
                    id="advanced-password-enabled-switch"
                )

            # 设置密码（输入框，明文存储）
            yield Label(get_global_i18n().t("settings.password"), classes="setting-label")
            yield Input(
                placeholder=get_global_i18n().t("settings.password_placeholder"),
                password=True,
                id="advanced-password-input"
            )

            # 启用数据库自动清理
            yield Label(get_global_i18n().t("settings.auto_vacuum_enabled"), classes="setting-label")
            auto_vacuum_setting = self.setting_registry.get_setting("advanced.auto_vacuum_enabled")
            if auto_vacuum_setting:
                yield Switch(
                    value=auto_vacuum_setting.value,
                    id="advanced-auto-vacuum-switch"
                )
    
    def _compose_database_settings(self) -> ComposeResult:
        """组合数据库管理设置"""
        with ScrollableContainer(id="database-settings"):
            # 数据库信息标题
            yield Label(get_global_i18n().t("settings.database"), classes="setting-section-title")
            
            # 数据库路径信息
            yield Label(get_global_i18n().t("settings.database_path_label"), classes="setting-label")
            config = self.config_manager.get_config()
            db_path = os.path.expanduser(config["paths"]["database"])
            yield Label(db_path, classes="setting-value")
            
            # 数据库文件大小
            try:
                if os.path.exists(db_path):
                    file_size = os.path.getsize(db_path) / 1024 / 1024  # MB
                    yield Label(get_global_i18n().t("settings.file_size_label", size=file_size), classes="setting-value")
                else:
                    yield Label(get_global_i18n().t("settings.file_size_not_exists"), classes="setting-value error")
            except Exception:
                yield Label(get_global_i18n().t("settings.file_size_error"), classes="setting-value error")
            
            # 分隔线
            yield Horizontal(id="database-separator", classes="setting-separator")
            
            # 数据库备份
            yield Label(get_global_i18n().t("settings.backup_database"), classes="setting-section-title")
            yield Label(get_global_i18n().t("settings.backup_database_desc"), classes="setting-description")
            yield Button(
                get_global_i18n().t("settings.backup_database"),
                id="database-backup-btn",
                variant="primary"
            )
            
            # 数据库还原
            yield Label(get_global_i18n().t("settings.restore_database"), classes="setting-section-title")
            yield Label(get_global_i18n().t("settings.restore_database_desc"), classes="setting-description")
            yield Button(
                get_global_i18n().t("settings.restore_database"),
                id="database-restore-btn",
                variant="error"
            )
            
            # 数据库维护说明
            yield Horizontal(id="database-maintenance-separator", classes="setting-separator")
            yield Label(get_global_i18n().t("settings.maintenance_tips_title"), classes="setting-section-title")
            yield Label(get_global_i18n().t("settings.maintenance_tip_vacuum"), classes="setting-description")
            yield Label(get_global_i18n().t("settings.maintenance_tip_backup"), classes="setting-description")
            yield Label(get_global_i18n().t("settings.maintenance_tip_location"), classes="setting-description")
    
    def _compose_preview_config_settings(self) -> ComposeResult:
        """组合预览配置设置"""
        with ScrollableContainer(id="preview-config-settings"):
            # 获取当前配置信息
            config_data = self.config_manager.get_config()
            
            # 格式化配置数据，移除敏感信息
            safe_config = self._sanitize_config_data(config_data)
            
            # 使用Pretty组件显示配置预览
            yield Label(f"{get_global_i18n().t('settings.current_config')}:", classes="setting-section-title")
            yield Pretty(safe_config, id="config-preview")
            
            # 添加刷新按钮
            yield Button(get_global_i18n().t("settings.refresh_config"), id="refresh-config-btn", variant="primary")
    
    def _sanitize_config_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤敏感配置信息
        
        Args:
            config_data: 原始配置数据
            
        Returns:
            Dict[str, Any]: 过滤后的安全配置数据
        """
        import copy
        
        # 深拷贝配置数据以避免修改原始数据
        safe_config = copy.deepcopy(config_data)
        
        # 定义需要过滤的敏感字段
        sensitive_fields = [
            # 翻译服务API密钥
            "app_id", "app_key", "api_key", "subscription_key", "app_secret",
            # 其他敏感信息
            "secret", "token"
        ]
        
        def sanitize_dict(d):
            """递归过滤字典中的敏感信息"""
            if not isinstance(d, dict):
                return d
                
            result = {}
            for key, value in d.items():
                # 检查是否为敏感字段
                if any(sensitive in str(key).lower() for sensitive in sensitive_fields):
                    result[key] = get_global_i18n().t("settings.hiddens")
                elif isinstance(value, dict):
                    result[key] = sanitize_dict(value)
                elif isinstance(value, list):
                    result[key] = [sanitize_dict(item) if isinstance(item, dict) else item for item in value]
                else:
                    result[key] = value
            return result
        
        return sanitize_dict(safe_config)
    
    def _refresh_config_preview(self) -> None:
        """刷新配置预览"""
        try:
            # 获取最新的配置数据
            config_data = self.config_manager.get_config()
            safe_config = self._sanitize_config_data(config_data)
            
            # 更新Pretty组件的内容
            config_preview = self.query_one("#config-preview", Pretty)
            config_preview.update(safe_config)
            
            self.notify(get_global_i18n().t("settings.config_refreshed"), severity="information")
            
        except Exception as e:
            logger.error(f"刷新配置预览失败: {e}")
            self.notify(get_global_i18n().t("settings.config_refresh_failed"), severity="error")
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        from src.ui.styles.isolation_manager import apply_style_isolation
        apply_style_isolation(self)
        
        # 调试信息：检查设置项是否被正确加载
        all_settings = self.setting_registry.get_all_settings()
        logger.debug(f"{get_global_i18n().t('settings.settings_count')}: {len(all_settings)}")
        for key, setting in all_settings.items():
            logger.debug(f"{get_global_i18n().t('settings.settings_key')} {key}: {setting.value} ({get_global_i18n().t('settings.settings_type')}: {type(setting).__name__})")
        
        # 应用当前主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 调试：检查ScrollableContainer是否正常工作
        scroll_containers = self.query("ScrollableContainer")
        logger.debug(f"{get_global_i18n().t('settings.found_unit', count=len(scroll_containers))}ScrollableContainer")
        for i, container in enumerate(scroll_containers):
            logger.debug(f"Container {i}: {container.id} - {get_global_i18n().t('common.height')}: {container.styles.height}")
        
        # 初始化多用户和启动密码的联动状态
        self._init_multi_user_password_linkage()
        
        # 检查按钮权限并禁用/启用按钮
        self._check_button_permissions()
    
    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            
            # 获取当前用户ID
            current_user_id = getattr(self.app, 'current_user_id', None)
            if current_user_id is None:
                # 如果没有当前用户，检查是否是多用户模式
                if not getattr(self.app, 'multi_user_enabled', False):
                    # 单用户模式默认允许所有权限
                    return True
                else:
                    # 多用户模式但没有当前用户，默认拒绝
                    return False
            
            return db_manager.has_permission(current_user_id, permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def _check_button_permissions(self) -> None:
        """检查按钮权限并禁用/启用按钮"""
        try:
            save_btn = self.query_one("#save-btn", Button)
            reset_btn = self.query_one("#reset-btn", Button)
            
            # 检查权限并设置按钮状态
            if not self._has_permission("settings.save"):
                save_btn.disabled = True
                save_btn.tooltip = get_global_i18n().t('settings.no_permission')
            else:
                save_btn.disabled = False
                save_btn.tooltip = None
                
            if not self._has_permission("settings.reset"):
                reset_btn.disabled = True
                reset_btn.tooltip = get_global_i18n().t('settings.no_permission')
            else:
                reset_btn.disabled = False
                reset_btn.tooltip = None
                
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        # 检查权限
        if not self._has_button_permission(event.button.id):
            self.notify(get_global_i18n().t("settings.np_action"), severity="warning")
            return
            
        if event.button.id == "save-btn":
            if self._has_permission("settings.save"):
                self._save_settings()
            else:
                self.notify(get_global_i18n().t("settings.np_save"), severity="warning")
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "reset-btn":
            if self._has_permission("settings.reset"):
                self._reset_settings()
            else:
                self.notify(get_global_i18n().t("settings.np_reset"), severity="warning")
        elif event.button.id == "refresh-config-btn":
            self._refresh_config_preview()
        elif event.button.id == "database-backup-btn":
            self._backup_database()
        elif event.button.id == "database-restore-btn":
            self._restore_database()

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回（仅一次）
            self.app.pop_screen()
            event.stop()
        elif event.key == "enter" or event.key == "ctrl+s":
            # 保存设置需要权限
            if self._has_permission("settings.save"):
                self._save_settings()
                self.notify(get_global_i18n().t("settings.saved"), severity="information")
            else:
                self.notify(get_global_i18n().t("settings.np_save"), severity="warning")
            event.stop()
        elif event.key == "r":
            # 重置设置需要权限
            if self._has_permission("settings.reset"):
                self._reset_settings()
                self.notify(get_global_i18n().t("settings.np_save"), severity="information")
            else:
                self.notify(get_global_i18n().t("settings.reseted"), severity="warning")
            event.prevent_default()
    
    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        """
        下拉选择框值变化时的回调
        
        Args:
            event: 下拉选择框变化事件
        """
        if event.select.id == "reading-spacing-select" and event.value is not None:
            # 立即应用行间距设置（安全转换）
            val = event.value
            try:
                # 确保值可以被转换为int
                if isinstance(val, (int, str)):
                    new_val = int(val)
                else:
                    return
            except (ValueError, TypeError):
                return
            old_value = self.setting_registry.get_value("reading.line_spacing", 0)
            self.setting_registry.set_value("reading.line_spacing", new_val)
            notify_setting_change("reading.line_spacing", old_value, new_val, "settings_screen")
            
        elif event.select.id == "reading-para-select" and event.value is not None:
            # 立即应用段落间距设置（安全转换）
            val = event.value
            try:
                # 确保值可以被转换为int
                if isinstance(val, (int, str)):
                    new_val = int(val)
                else:
                    return
            except (ValueError, TypeError):
                return
            old_value = self.setting_registry.get_value("reading.paragraph_spacing", 0)
            self.setting_registry.set_value("reading.paragraph_spacing", new_val)
            notify_setting_change("reading.paragraph_spacing", old_value, new_val, "settings_screen")
    
    

    @on(Button.Pressed)
    def on_port_check_pressed(self, event: Button.Pressed) -> None:
        """端口检测按钮按下时的回调"""
        if event.button.id == "browser-server-check-port-btn":
            self._check_current_port_availability()
    
    def _check_current_port_availability(self) -> None:
        """检测当前端口配置的可用性"""
        try:
            from src.utils.browser_reader import BrowserReader
            
            # 获取当前配置
            host_input = self.query_one("#browser-server-host-input", Input)
            port_input = self.query_one("#browser-server-port-input", Input)
            status_text = self.query_one("#browser-server-port-status", Static)
            
            # 解析主机地址
            host = host_input.value.strip() or "localhost"
            
            # 解析端口
            try:
                port = int(port_input.value or "0")
            except ValueError:
                port = 0
            
            # 检测端口
            if port == 0:
                status_text.update(get_global_i18n().t("settings.port_status_random"))
                status_text.styles.color = "blue"
            elif BrowserReader._is_port_available(host, port):
                status_text.update(get_global_i18n().t("settings.port_status_available").format(host=host, port=port))
                status_text.styles.color = "green"
            else:
                status_text.update(get_global_i18n().t("settings.port_status_occupied").format(host=host, port=port))
                status_text.styles.color = "red"
                
        except Exception as e:
            status_text = self.query_one("#browser-server-port-status", Static)
            status_text.update(get_global_i18n().t("settings.port_check_failed").format(error=str(e)))
            status_text.styles.color = "red"

    @on(Switch.Changed)
    def on_switch_changed(self, event: Switch.Changed) -> None:
        """
        Switch组件值变化时的回调
        
        Args:
            event: Switch变化事件
        """
        if event.switch.id == "advanced-multi-user-switch":
            # 多用户开关状态改变，更新启动密码控件的状态
            self._update_password_controls_state(event.value)
    
    def _update_password_controls_state(self, multi_user_enabled: bool) -> None:
        """根据多用户状态更新启动密码控件的状态"""
        try:
            # 获取启动密码相关控件
            pwd_enabled_switch = self.query_one("#advanced-password-enabled-switch", Switch)
            pwd_input = self.query_one("#advanced-password-input", Input)
            
            if multi_user_enabled:
                # 多用户开启时，禁用启动密码功能
                pwd_enabled_switch.value = False
                pwd_enabled_switch.disabled = True
                pwd_input.disabled = True
            else:
                # 多用户关闭时，启用启动密码功能
                pwd_enabled_switch.disabled = False
                pwd_input.disabled = False
                
        except Exception as e:
            logger.debug(f"更新启动密码控件状态失败: {e}")
    

    
    def _has_button_permission(self, button_id: str) -> bool:
        """检查按钮权限"""
        permission_map = {
            "save-btn": "settings.save",
            "reset-btn": "settings.reset"
        }
        
        if button_id in permission_map:
            return self._has_permission(permission_map[button_id])
        
        return True  # 默认允许未知按钮
    
    def _save_settings(self) -> None:
        """保存设置"""
        try:
            # 更新所有设置项的值
            self._update_settings_from_ui()
            
            # 保存到配置
            if self.config_adapter.save_settings_to_config():
                # 通知所有设置变更
                self._notify_setting_changes()
                # 设置中心保存后：强同步 app.theme 到 appearance.theme，并立即应用刷新与持久化
                try:
                    desired = self.setting_registry.get_value("appearance.theme", None)
                    if desired and isinstance(desired, str):
                        # 写入并应用到App与所有屏幕
                        if self.theme_manager.set_theme(desired):
                            # 应用到当前App
                            try:
                                self.theme_manager.apply_theme_to_screen(self.app)
                            except Exception:
                                pass
                            # 应用到已安装的屏幕
                            try:
                                installed = getattr(self.app, "installed_screens", {})
                                for scr in list(installed.values()):
                                    self.theme_manager.apply_theme_to_screen(scr)
                            except Exception:
                                pass
                            # 持久化 app.theme
                            try:
                                cfg = self.config_manager.get_config()
                                app_cfg = cfg.get("app", {})
                                app_cfg["theme"] = desired
                                cfg["app"] = app_cfg
                                if hasattr(self.config_manager, "save_config"):
                                    self.config_manager.save_config(cfg)  # type: ignore[attr-defined]
                            except Exception:
                                pass
                            # 刷新UI
                            try:
                                self.app.refresh(layout=True)
                            except Exception:
                                pass
                except Exception as e:
                    logger.debug(f"设置中心保存后同步主题失败（可忽略）：{e}")

                self.notify(get_global_i18n().t("settings.saved"), severity="information")
                self.app.pop_screen()
            else:
                self.notify(get_global_i18n().t("settings.save_failed"), severity="error")
                
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.notify(get_global_i18n().t("settings.save_error"), severity="error")
    
    def _notify_setting_changes(self) -> None:
        """通知设置变更"""
        try:
            from src.config.settings.setting_observer import notify_setting_change
            
            # 获取所有设置项并通知变更
            all_settings = self.setting_registry.get_all_settings()
            for key, setting in all_settings.items():
                # 直接通知所有设置项变更
                notify_setting_change(key, None, setting.value, "settings_screen")
                    
        except Exception as e:
            logger.error(f"Failed to notify setting changes: {e}")
    
    def _reset_settings(self) -> None:
        """重置设置为默认值"""
        try:
            # 重置当前标签页的设置
            current_tab = self.query_one(TabbedContent).active
            category = current_tab.replace("-tab", "")
            
            count = self.config_adapter.reset_settings_to_defaults(category)
            
            if count > 0:
                # 重新加载UI
                self._update_ui_from_settings()
                self.notify(
                    get_global_i18n().t("settings.reset_success", count=count),
                    severity="information"
                )
            else:
                self.notify(get_global_i18n().t("settings.reset_failed"), severity="warning")
                
        except Exception as e:
            logger.error(f"Failed to reset settings: {e}")
            self.notify(get_global_i18n().t("settings.reset_error"), severity="error")
    
    def _update_settings_from_ui(self) -> None:
        """从UI更新设置项的值"""
        # 外观设置
        theme_select = self.query_one("#appearance-theme-select", Select)
        if theme_select.value is not None:
            self.setting_registry.set_value("appearance.theme", theme_select.value)
        
        border_select = self.query_one("#appearance-border-select", Select)
        if border_select.value is not None:
            self.setting_registry.set_value("appearance.border_style", border_select.value)
        
        icons_switch = self.query_one("#appearance-icons-switch", Switch)
        self.setting_registry.set_value("appearance.show_icons", icons_switch.value)
        
        animation_switch = self.query_one("#appearance-animation-switch", Switch)
        self.setting_registry.set_value("appearance.animation_enabled", animation_switch.value)
        
        progress_select = self.query_one("#appearance-progress-select", Select)
        if progress_select.value is not None:
            self.setting_registry.set_value("appearance.progress_bar_style", progress_select.value)
        
        # 阅读设置
        font_input = self.query_one("#reading-font-size-input", Input)
        try:
            if font_input.value:
                self.setting_registry.set_value("reading.font_size", int(font_input.value))
        except ValueError:
            pass

        spacing_select = self.query_one("#reading-spacing-select", Select)
        if spacing_select.value is not None:
            try:
                # 确保值可以被安全转换为int
                val = spacing_select.value
                if isinstance(val, (int, str)):
                    self.setting_registry.set_value("reading.line_spacing", int(val))
            except (ValueError, TypeError):
                pass
        
        para_select = self.query_one("#reading-para-select", Select)
        if para_select.value is not None:
            try:
                # 确保值可以被安全转换为int
                val = para_select.value
                if isinstance(val, (int, str)):
                    self.setting_registry.set_value("reading.paragraph_spacing", int(val))
            except (ValueError, TypeError):
                pass
        
        auto_input = self.query_one("#reading-auto-input", Input)
        try:
            self.setting_registry.set_value("reading.auto_page_turn_interval", int(auto_input.value))
        except ValueError:
            pass
        
        remember_switch = self.query_one("#reading-remember-switch", Switch)
        self.setting_registry.set_value("reading.remember_position", remember_switch.value)
        
        highlight_switch = self.query_one("#reading-highlight-switch", Switch)
        self.setting_registry.set_value("reading.highlight_search", highlight_switch.value)
        
        # 阅读提醒设置
        reminder_enabled_switch = self.query_one("#reading-reminder-enabled-switch", Switch)
        self.setting_registry.set_value("reading.reminder_enabled", reminder_enabled_switch.value)
        
        reminder_interval_input = self.query_one("#reading-reminder-interval-input", Input)
        try:
            if reminder_interval_input.value:
                self.setting_registry.set_value("reading.reminder_interval", int(reminder_interval_input.value))
        except ValueError:
            pass
        
        # 音频设置
        tts_switch = self.query_one("#audio-tts-switch", Switch)
        self.setting_registry.set_value("audio.tts_enabled", tts_switch.value)
        
        speed_input = self.query_one("#audio-speed-input", Input)
        try:
            self.setting_registry.set_value("audio.tts_speed", int(speed_input.value))
        except ValueError:
            pass
        
        voice_select = self.query_one("#audio-voice-select", Select)
        if voice_select.value is not None:
            self.setting_registry.set_value("audio.tts_voice", voice_select.value)
        
        volume_input = self.query_one("#audio-volume-input", Input)
        try:
            self.setting_registry.set_value("audio.tts_volume", float(volume_input.value))
        except ValueError:
            pass
        
        # 翻译设置
        service_select = self.query_one("#translation-service-select", Select)
        if service_select.value is not None:
            self.setting_registry.set_value("translation.default_service", service_select.value)
        
        source_input = self.query_one("#translation-source-input", Input)
        self.setting_registry.set_value("translation.source_language", source_input.value)
        
        target_input = self.query_one("#translation-target-input", Input)
        self.setting_registry.set_value("translation.target_language", target_input.value)
        
        cache_switch = self.query_one("#translation-cache-switch", Switch)
        self.setting_registry.set_value("translation.cache_enabled", cache_switch.value)
        
        duration_input = self.query_one("#translation-duration-input", Input)
        try:
            self.setting_registry.set_value("translation.cache_duration", int(duration_input.value))
        except ValueError:
            pass
        
        timeout_input = self.query_one("#translation-timeout-input", Input)
        try:
            self.setting_registry.set_value("translation.timeout", int(timeout_input.value))
        except ValueError:
            pass
        
        retry_input = self.query_one("#translation-retry-input", Input)
        try:
            self.setting_registry.set_value("translation.retry_count", int(retry_input.value))
        except ValueError:
            pass
        
        # 翻译服务API配置
        # 百度翻译
        baidu_enabled = self.query_one("#baidu-enabled-switch", Switch)
        self.setting_registry.set_value("translation.translation_services.baidu.enabled", baidu_enabled.value)
        
        baidu_app_id = self.query_one("#baidu-app-id-input", Input)
        self.setting_registry.set_value("translation.translation_services.baidu.app_id", baidu_app_id.value)
        
        baidu_app_key = self.query_one("#baidu-app-key-input", Input)
        self.setting_registry.set_value("translation.translation_services.baidu.app_key", baidu_app_key.value)
        
        # 有道翻译
        youdao_enabled = self.query_one("#youdao-enabled-switch", Switch)
        self.setting_registry.set_value("translation.translation_services.youdao.enabled", youdao_enabled.value)
        
        youdao_app_key = self.query_one("#youdao-app-key-input", Input)
        self.setting_registry.set_value("translation.translation_services.youdao.app_key", youdao_app_key.value)
        
        youdao_app_secret = self.query_one("#youdao-app-secret-input", Input)
        self.setting_registry.set_value("translation.translation_services.youdao.app_secret", youdao_app_secret.value)
        
        # Google翻译
        google_enabled = self.query_one("#google-enabled-switch", Switch)
        self.setting_registry.set_value("translation.translation_services.google.enabled", google_enabled.value)
        
        google_api_key = self.query_one("#google-api-key-input", Input)
        self.setting_registry.set_value("translation.translation_services.google.api_key", google_api_key.value)
        
        # 微软翻译
        microsoft_enabled = self.query_one("#microsoft-enabled-switch", Switch)
        self.setting_registry.set_value("translation.translation_services.microsoft.enabled", microsoft_enabled.value)
        
        microsoft_key = self.query_one("#microsoft-key-input", Input)
        self.setting_registry.set_value("translation.translation_services.microsoft.subscription_key", microsoft_key.value)
        
        microsoft_region = self.query_one("#microsoft-region-input", Input)
        self.setting_registry.set_value("translation.translation_services.microsoft.region", microsoft_region.value)
        
        # 浏览器设置
        browser_select = self.query_one("#browser-default-select", Select)
        if browser_select.value is not None:
            self.setting_registry.set_value("browser.default_browser", browser_select.value)
        
        chrome_input = self.query_one("#browser-chrome-input", Input)
        self.setting_registry.set_value("browser.chrome_path", chrome_input.value)
        
        safari_input = self.query_one("#browser-safari-input", Input)
        self.setting_registry.set_value("browser.safari_path", safari_input.value)
        
        brave_input = self.query_one("#browser-brave-input", Input)
        self.setting_registry.set_value("browser.brave_path", brave_input.value)
        
        # 浏览器服务器设置
        host_input = self.query_one("#browser-server-host-input", Input)
        self.setting_registry.set_value("browser_server.host", host_input.value)
        
        port_input = self.query_one("#browser-server-port-input", Input)
        try:
            self.setting_registry.set_value("browser_server.port", int(port_input.value))
        except ValueError:
            pass
        
        port_range_min_input = self.query_one("#browser-server-port-range-min-input", Input)
        try:
            self.setting_registry.set_value("browser_server.port_range_min", int(port_range_min_input.value))
        except ValueError:
            pass
        
        port_range_max_input = self.query_one("#browser-server-port-range-max-input", Input)
        try:
            self.setting_registry.set_value("browser_server.port_range_max", int(port_range_max_input.value))
        except ValueError:
            pass
        
        max_retry_input = self.query_one("#browser-server-max-retry-input", Input)
        try:
            self.setting_registry.set_value("browser_server.max_retry_attempts", int(max_retry_input.value))
        except ValueError:
            pass
        
        # 高级设置
        lang_select = self.query_one("#advanced-language-select", Select)
        if lang_select.value is not None:
            self.setting_registry.set_value("advanced.language", lang_select.value)
        
        # 更新全局i18n语言设置（确保类型为字符串）
        if isinstance(lang_select.value, str):
            set_global_locale(lang_select.value)
        
        stats_switch = self.query_one("#advanced-stats-switch", Switch)
        self.setting_registry.set_value("advanced.statistics_enabled", stats_switch.value)
        
        debug_switch = self.query_one("#advanced-debug-switch", Switch)
        self.setting_registry.set_value("advanced.debug_mode", debug_switch.value)
        
        # 多用户开关
        multi_user_switch = self.query_one("#advanced-multi-user-switch", Switch)
        multi_user_enabled = multi_user_switch.value
        self.setting_registry.set_value("advanced.multi_user_enabled", multi_user_enabled)
        
        # 启动密码开关
        pwd_enabled_switch = self.query_one("#advanced-password-enabled-switch", Switch)
        pwd_enabled = pwd_enabled_switch.value
        
        # 多用户和启动密码联动逻辑
        if multi_user_enabled:
            # 多用户开启时，自动关闭启动密码模式
            pwd_enabled = False
            self.setting_registry.set_value("advanced.password_enabled", False)
            # 同时禁用启动密码相关的UI控件
            try:
                pwd_enabled_switch.value = False
                pwd_enabled_switch.disabled = True
                pwd_input = self.query_one("#advanced-password-input", Input)
                pwd_input.disabled = True
            except Exception:
                pass
        else:
            # 多用户关闭时，启用启动密码相关的UI控件
            try:
                pwd_enabled_switch.disabled = False
                pwd_input = self.query_one("#advanced-password-input", Input)
                pwd_input.disabled = False
            except Exception:
                pass
            self.setting_registry.set_value("advanced.password_enabled", pwd_enabled)
        
        # 设置密码输入（如有输入则直接保存明文）
        pwd_input = self.query_one("#advanced-password-input", Input)
        new_pwd = (pwd_input.value or "").strip()
        if new_pwd:
            self.setting_registry.set_value("advanced.password", new_pwd)

    
    def _init_multi_user_password_linkage(self) -> None:
        """初始化多用户和启动密码的联动状态"""
        try:
            # 获取当前多用户设置状态
            multi_user_enabled = self.setting_registry.get_value("advanced.multi_user_enabled", False)
            
            # 获取启动密码相关控件
            multi_user_switch = self.query_one("#advanced-multi-user-switch", Switch)
            pwd_enabled_switch = self.query_one("#advanced-password-enabled-switch", Switch)
            pwd_input = self.query_one("#advanced-password-input", Input)
            
            # 根据多用户状态设置启动密码控件的状态
            if multi_user_enabled:
                # 多用户开启时，禁用启动密码功能
                pwd_enabled_switch.value = False
                pwd_enabled_switch.disabled = True
                pwd_input.disabled = True
            else:
                # 多用户关闭时，启用启动密码功能
                pwd_enabled_switch.disabled = False
                pwd_input.disabled = False
                
        except Exception as e:
            logger.debug(f"初始化多用户密码联动状态失败: {e}")
    
    def _update_ui_from_settings(self) -> None:
        """从设置项更新UI"""
        # 这个方法会在重置后重新加载UI
        # 由于Textual的限制，我们需要重新加载整个屏幕
        # 在实际应用中，可以逐个更新UI控件

    def _backup_database(self) -> None:
        """备份数据库到下载文件夹"""
        import os
        import shutil
        import datetime
        from pathlib import Path
        from src.core.database_manager import DatabaseManager
        
        try:
            # 显示备份进度提示
            self.notify(get_global_i18n().t("settings.backup_in_progress"), severity="information")
            
            # 获取数据库路径
            db_manager = DatabaseManager()
            db_path = db_manager.get_db_path()
            
            # 检查数据库文件是否存在
            if not os.path.exists(db_path):
                self.notify(get_global_i18n().t("settings.backup_failed"), severity="error")
                return
            
            # 创建下载目录
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(exist_ok=True)
            
            # 生成备份文件名（包含时间戳）
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"newreader_database_backup_{timestamp}.zip"
            backup_path = downloads_dir / backup_filename
            
            # 创建临时目录
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_db_path = os.path.join(temp_dir, "database.sqlite")
                
                # 复制数据库文件到临时目录
                shutil.copy2(db_path, temp_db_path)
                
                # 创建ZIP压缩包
                import zipfile
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(temp_db_path, "database.sqlite")
                
                # 验证备份文件
                if backup_path.exists() and backup_path.stat().st_size > 0:
                    self.notify(
                        f"{get_global_i18n().t('settings.backup_success')}: {backup_filename}", 
                        severity="success"
                    )
                    logger.info(f"数据库备份成功: {backup_path}")
                else:
                    self.notify(get_global_i18n().t("settings.backup_failed"), severity="error")
                    
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            self.notify(get_global_i18n().t("settings.backup_failed"), severity="error")

    def _restore_database(self) -> None:
        """从备份恢复数据库"""
        try:
            from src.ui.screens.file_explorer_screen import FileExplorerScreen
            
            def on_file_selected(file_path: Optional[str]) -> None:
                if file_path:
                    # 如果返回的是列表（多选模式），取第一个
                    if isinstance(file_path, list):
                        if not file_path:
                            return
                        file_path = file_path[0]
                    self._perform_database_restore(file_path)
            
            self.app.push_screen(
                FileExplorerScreen(
                    theme_manager=self.theme_manager,
                    bookshelf=self.app.bookshelf,
                    statistics_manager=self.app.statistics_manager,
                    selection_mode="file",
                    title=get_global_i18n().t("settings.select_backup_file"),
                    file_extensions={".zip"}
                ),
                on_file_selected
            )
        except Exception as e:
            logger.error(f"打开文件选择器失败: {e}")
            self.notify(get_global_i18n().t("error.error") + f": {e}", severity="error")

    def _perform_database_restore(self, backup_path: str) -> None:
        """执行数据库恢复"""
        import shutil
        import zipfile
        import tempfile
        from src.core.database_manager import DatabaseManager
        
        try:
            self.notify(get_global_i18n().t("common.on_action"), severity="information")
            
            # 验证zip文件
            if not zipfile.is_zipfile(backup_path):
                 self.notify(get_global_i18n().t("settings.restore_failed") + ": Invalid Zip File", severity="error")
                 return

            # 获取数据库路径
            db_manager = DatabaseManager()
            db_path = db_manager.get_db_path()
            
            # 创建临时目录解压
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                    # 检查是否存在 database.sqlite
                    file_to_restore = None
                    if "database.sqlite" in zip_ref.namelist():
                        file_to_restore = "database.sqlite"
                    
                    # 简单支持 SQL 文件恢复（如果 zip 中包含 .sql）
                    # 注意：这需要解析 SQL 并执行，比较复杂。
                    # 如果用户坚持 "restore .sql file"，我们先只支持替换 database.sqlite
                    # 如果没有 sqlite 但有 sql，提示用户。
                    
                    if not file_to_restore:
                        sql_files = [f for f in zip_ref.namelist() if f.endswith(".sql")]
                        if sql_files:
                             self.notify(get_global_i18n().t("settings.restore_failed") + ": SQL dump restore not supported yet, only binary backup.", severity="error")
                             return
                        
                        self.notify(get_global_i18n().t("settings.restore_failed") + ": No database.sqlite found in zip", severity="error")
                        return
                        
                    zip_ref.extract(file_to_restore, temp_dir)
                    extracted_db_path = os.path.join(temp_dir, file_to_restore)
                    
                    # 备份当前数据库 (.bak)
                    if os.path.exists(db_path):
                        try:
                            shutil.copy2(db_path, db_path + ".bak")
                        except Exception as e:
                            logger.warning(f"自动备份当前数据库失败: {e}")
                            # 继续尝试还原
                        
                    # 覆盖数据库
                    shutil.copy2(extracted_db_path, db_path)
                    
            self.notify(get_global_i18n().t("settings.restore_success"), severity="success")
            
            # 刷新 UI 或提示重启
            # 重新加载配置可能不够，因为数据库连接可能需要重置。
            # 最好的方式是让用户重启，或者尝试重新初始化 app 状态。
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            self.notify(get_global_i18n().t("settings.restore_failed") + f": {e}", severity="error")