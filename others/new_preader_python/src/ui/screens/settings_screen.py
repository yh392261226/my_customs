"""
现代化设置屏幕
使用新的面向对象设置系统
"""


from typing import Any, Dict, Optional, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, Select, Switch, Input, TabbedContent, TabPane
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

class SettingsScreen(Screen[Any]):
    """现代化设置屏幕"""
    
    CSS_PATH = ["../styles/settings_overrides.tcss"]
    # 使用 Textual BINDINGS 进行快捷键绑定（不移除 on_key，逐步过渡）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("enter", "press('#save-btn')", "保存"),
        ("r", "press('#reset-btn')", "重置"),
        ("ctrl+s", "press('#save-btn')", "保存"),
    ]
    

    
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
        
        # 初始化设置系统
        self.setting_registry = SettingRegistry()
        initialize_settings_registry(self.setting_registry)
        self.config_adapter = ConfigAdapter(config_manager, self.setting_registry)
        
        # 从配置加载设置值
        self.config_adapter.load_config_to_settings()
        
        self.screen_title = get_global_i18n().t("settings.title")
    
    def compose(self) -> ComposeResult:
        """
        组合设置屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        with Container(id="settings-container"):
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
                
                # 高级设置标签页
                with TabPane(get_global_i18n().t("settings.advanced"), id="advanced-tab"):
                    yield from self._compose_advanced_settings()
                

            
            # 控制按钮
            with Horizontal(id="settings-controls", classes="btn-row"):
                yield Button(get_global_i18n().t("settings.save"), id="save-btn", variant="primary")
                yield Button(get_global_i18n().t("settings.cancel"), id="cancel-btn")
                yield Button(get_global_i18n().t("settings.reset"), id="reset-btn", variant="warning")
            
            # 快捷键状态栏
            with Horizontal(id="settings-shortcuts-bar", classes="status-bar"):
                yield Label(f"Enter: {get_global_i18n().t("common.save")}", id="shortcut-enter")
                yield Label(f"ESC: {get_global_i18n().t("common.cancel")}", id="shortcut-esc")
                yield Label(f"R: {get_global_i18n().t("common.reset")}", id="shortcut-reset")
    
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
                yield Select(
                    [(label, value) for value, label in zip(progress_setting.options, progress_setting.option_labels)],
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
                        ("0 (紧凑)", 0),
                        ("1 (标准)", 1),
                        ("2 (宽松)", 2),
                        ("3 (较宽松)", 3),
                        ("4 (很宽松)", 4),
                        ("5 (最大间距)", 5)
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
                        ("0 (紧凑)", 0),
                        ("1 (标准)", 1),
                        ("2 (宽松)", 2),
                        ("3 (较宽松)", 3),
                        ("4 (很宽松)", 4),
                        ("5 (最大间距)", 5)
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
                yield Select(
                    [(label, value) for value, label in zip(voice_setting.options, voice_setting.option_labels)],
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
                yield Select(
                    [(label, value) for value, label in zip(service_setting.options, service_setting.option_labels)],
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

            # 启用启动密码
            yield Label("启用启动密码", classes="setting-label")
            pwd_enabled_setting = self.setting_registry.get_setting("advanced.password_enabled")
            if pwd_enabled_setting:
                yield Switch(
                    value=pwd_enabled_setting.value,
                    id="advanced-password-enabled-switch"
                )

            # 设置密码（输入框，明文存储）
            yield Label("设置密码", classes="setting-label")
            yield Input(
                placeholder="输入新密码",
                password=True,
                id="advanced-password-input"
            )
    

    
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
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "reset-btn":
            self._reset_settings()

    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回（仅一次）
            self.app.pop_screen()
            event.stop()
    
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
                new_val = int(val)  # type: ignore[arg-type]
            except Exception:
                return
            old_value = self.setting_registry.get_value("reading.line_spacing", 0)
            self.setting_registry.set_value("reading.line_spacing", new_val)
            notify_setting_change("reading.line_spacing", old_value, new_val, "settings_screen")
            
            # 显示设置已保存的提示
            # self.notify(get_global_i18n().t("settings.saved"), severity="information")
            
        elif event.select.id == "reading-para-select" and event.value is not None:
            # 立即应用段落间距设置（安全转换）
            val = event.value
            try:
                new_val = int(val)  # type: ignore[arg-type]
            except Exception:
                return
            old_value = self.setting_registry.get_value("reading.paragraph_spacing", 0)
            self.setting_registry.set_value("reading.paragraph_spacing", new_val)
            notify_setting_change("reading.paragraph_spacing", old_value, new_val, "settings_screen")
            
            # 显示设置已保存的提示
            # self.notify(get_global_i18n().t("settings.saved"), severity="information")
    

    
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
            self.setting_registry.set_value("reading.font_size", int(font_input.value))
        except ValueError:
            pass

        spacing_select = self.query_one("#reading-spacing-select", Select)
        if spacing_select.value is not None:
            try:
                self.setting_registry.set_value("reading.line_spacing", int(spacing_select.value))
            except Exception:
                pass
        
        para_select = self.query_one("#reading-para-select", Select)
        if para_select.value is not None:
            try:
                self.setting_registry.set_value("reading.paragraph_spacing", int(para_select.value))
            except Exception:
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
        
        # 启动密码开关
        pwd_enabled_switch = self.query_one("#advanced-password-enabled-switch", Switch)
        self.setting_registry.set_value("advanced.password_enabled", pwd_enabled_switch.value)

        # 设置密码输入（如有输入则直接保存明文）
        pwd_input = self.query_one("#advanced-password-input", Input)
        new_pwd = (pwd_input.value or "").strip()
        if new_pwd:
            self.setting_registry.set_value("advanced.password", new_pwd)

    
    def _update_ui_from_settings(self) -> None:
        """从设置项更新UI"""
        # 这个方法会在重置后重新加载UI
        # 由于Textual的限制，我们需要重新加载整个屏幕
        # 在实际应用中，可以逐个更新UI控件
        pass