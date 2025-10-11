"""
翻译对话框 - 显示翻译结果并提供添加到单词本的功能
"""

from typing import Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Input, Static, Select
from textual import events
from src.locales.i18n_manager import get_global_i18n, t
from src.core.translation_manager import TranslationManager
from src.core.vocabulary_manager import VocabularyManager
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TranslationDialog(ModalScreen[Dict[str, Any]]):
    """翻译对话框"""
    
    # CSS文件路径
    CSS_PATH = "../styles/translation_dialog_overrides.tcss"
    
    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        apply_universal_style_isolation(self)
    
    def __init__(self, original_text: str, context: str = "", translation_manager: Optional[TranslationManager] = None, vocabulary_manager: Optional[VocabularyManager] = None, allow_input: bool = False, book_path: str = ""):
        super().__init__()
        self.selected_text = original_text.strip()
        self.context = context
        self.translation_result = None
        self.book_path = book_path  # 书籍的绝对路径
        
        # 初始化翻译服务
        if translation_manager is not None:
            self.translation_service = translation_manager
        else:
            # 创建新的翻译管理器并配置
            self.translation_service = TranslationManager()
            try:
                # 尝试从配置管理器配置翻译服务
                self.translation_service.configure_from_config_manager()
            except Exception as e:
                logger.error(f"配置翻译管理器失败: {e}")
                # 如果配置失败，使用默认管理器（无服务配置）
                pass
        
        self.vocabulary_manager = vocabulary_manager if vocabulary_manager is not None else VocabularyManager()
        self.allow_input = allow_input  # 是否允许用户输入文本
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Container(id="translation-dialog-container", classes="panel"):
            yield Label(
                get_global_i18n().t("translation_dialog.title"),
                id="translation-dialog-title",
                classes="section-title"
            )
            
            with Vertical(id="translation-dialog-body", classes="section-body"):
                # 原文显示区域
                with Horizontal(id="original-text-section", classes="trans_section"):
                    yield Label(
                        get_global_i18n().t("translation_dialog.original_text"),
                        classes="field-label"
                    )
                    
                    if self.allow_input and not self.selected_text:
                        # 允许用户输入要翻译的文本
                        yield Input(
                            placeholder=get_global_i18n().t("translation_dialog.enter_text_to_translate"),
                            id="original-text-input",
                            classes="input-std"
                        )
                    else:
                        # 显示选中的文本
                        yield Static(
                            self.selected_text,
                            id="original-text",
                            classes="text-display"
                        )
                
                # 翻译输入区域
                with Horizontal(id="translation-input-section", classes="trans_section"):
                    yield Label(
                        get_global_i18n().t("translation_dialog.target_language"),
                        classes="field-label"
                    )
                    with Horizontal():
                        yield Select(self._build_language_options(), id="target-language-select", allow_blank=False)
                        yield Button(
                            get_global_i18n().t("translation_dialog.translate"),
                            id="translate-button",
                            variant="primary"
                        )
            
            # 翻译结果显示区域
            with Vertical(id="translation-result-section", classes="section"):
                yield Label(
                    get_global_i18n().t("translation_dialog.translation_result"),
                    classes="field-label"
                )
                yield Static(
                    get_global_i18n().t("translation_dialog.waiting_for_translation"),
                    id="translation-result",
                    classes="text-display"
                )
            
            # 添加到单词本区域
            with Vertical(id="vocabulary-section", classes="section"):
                yield Label(
                    get_global_i18n().t("translation_dialog.add_to_vocabulary"),
                    classes="field-label"
                )
                with Horizontal():
                    yield Input(
                        placeholder=get_global_i18n().t("translation_dialog.enter_context_optional"),
                        id="context-input",
                        classes="input-std"
                    )
                    yield Button(
                        get_global_i18n().t("translation_dialog.add_to_vocabulary"),
                        id="add-vocabulary-button",
                        variant="error",
                        disabled=True
                    )
            
            # 按钮区域
            with Container(id="dialog-buttons", classes="btn-row"):
                yield Button(
                    get_global_i18n().t("common.close"),
                    id="close-button",
                    variant="primary"
                )
    
    def _build_language_options(self):
        """根据当前翻译服务构建下拉选项"""
        service = (getattr(self.translation_service, "default_service", None) or getattr(self.translation_service, "service", None) or "").lower()
        baidu = [
            ("中文 zh", "zh"),
            ("繁体中文 cht", "cht"),
            ("英语 en", "en"),
            ("粤语 yue", "yue"),
            ("文言文 wyw", "wyw"),
            ("日语 jp", "jp"),
            ("韩语 kor", "kor"),
            ("泰语 th", "th"),
            ("俄语 ru", "ru"),
        ]
        youdao = [
            ("简体中文 zh-CHS", "zh-CHS"),
            ("繁体中文 zh-CHT", "zh-CHT"),
            ("英语 en", "en"),
            ("粤语 yue", "yue"),
            ("日语 ja", "ja"),
            ("韩语 ko", "ko"),
            ("泰语 th", "th"),
            ("俄语 ru", "ru"),
        ]
        google = [
            ("中文 zh-CN", "zh-CN"),
            ("繁体中文 zh-TW", "zh-TW"),
            ("英语 en", "en"),
            ("粤语 yue", "yue"),
            ("日语 ja", "ja"),
            ("韩语 ko", "ko"),
            ("泰语 th", "th"),
            ("俄语 ru", "ru"),
        ]
        microsoft = [
            ("中文 zh-Hans", "zh-Hans"),
            ("繁体中文 zh-Hant", "zh-Hant"),
            ("英语 en", "en"),
            ("粤语 yue", "yue"),
            ("日语 ja", "ja"),
            ("韩语 ko", "ko"),
            ("泰语 th", "th"),
            ("俄语 ru", "ru"),
        ]
        if "baidu" in service:
            return baidu
        if "youdao" in service:
            return youdao
        if "google" in service:
            return google
        if "microsoft" in service or "azure" in service:
            return microsoft
        return [
            ("中文 zh", "zh"),
            ("繁体中文 zh-TW", "zh-TW"),
            ("英语 en", "en"),
            ("粤语 yue", "yue"),
            ("日语 ja", "ja"),
            ("韩语 ko", "ko"),
            ("泰语 th", "th"),
            ("俄语 ru", "ru"),
        ]

    def _refresh_language_options(self) -> None:
        """刷新下拉选择的选项（根据当前翻译服务）"""
        try:
            select = self.query_one("#target-language-select", Select)
            options = self._build_language_options()
            select.set_options(options)
            # 默认选择第一项的值
            if options and options[0][1]:
                select.value = options[0][1]
        except Exception:
            pass

    def on_mount(self) -> None:
        """对话框挂载时的回调"""
        # 聚焦到合适的输入框
        if self.allow_input and not self.selected_text:
            # 在输入模式下，聚焦到原文输入框
            self.query_one("#original-text-input", Input).focus()
        else:
            # 在有选中文本的模式下，先刷新语言选项，聚焦到下拉框并自动翻译
            self._refresh_language_options()
            self.query_one("#target-language-select", Select).focus()
            self.app.call_later(self.translate_text)
    
    async def translate_text(self) -> None:
        """执行翻译"""
        select = self.query_one("#target-language-select", Select)
        target_lang = (select.value or "zh").strip()
        
        # 获取要翻译的文本
        if self.allow_input and not self.selected_text:
            # 从输入框获取文本
            original_input = self.query_one("#original-text-input", Input)
            text_to_translate = original_input.value.strip()
            if not text_to_translate:
                # 如果没有输入文本，显示提示
                result_display = self.query_one("#translation-result", Static)
                result_display.update(get_global_i18n().t("translation_dialog.enter_text_first"))
                return
            self.selected_text = text_to_translate
        else:
            text_to_translate = self.selected_text
        
        # 显示翻译中状态
        result_display = self.query_one("#translation-result", Static)
        result_display.update(get_global_i18n().t("translation_dialog.translating"))
        
        # 执行翻译
        try:
            self.translation_result = self.translation_service.translate(
                text_to_translate,
                target_lang=target_lang,
                source_lang="auto"
            )
            
            if self.translation_result.get('success'):
                # 显示翻译结果
                translated_text = self.translation_result.get('translated_text', '')
                source_lang = self.translation_result.get('source_lang', 'auto')
                target_lang = self.translation_result.get('target_lang', target_lang)
                
                result_text = f"{translated_text}\n\n({source_lang} → {target_lang})"
                result_display.update(result_text)
                
                # 启用添加到单词本按钮
                self.query_one("#add-vocabulary-button", Button).disabled = False
            else:
                # 显示错误信息
                error_msg = self.translation_result.get('error', get_global_i18n().t("translation_dialog.translation_failed"))
                result_display.update(f"{get_global_i18n().t('translation_dialog.error')}: {error_msg}")
                self.query_one("#add-vocabulary-button", Button).disabled = True
                
        except Exception as e:
            result_display.update(f"{get_global_i18n().t('translation_dialog.error')}: {str(e)}")
            self.query_one("#add-vocabulary-button", Button).disabled = True
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "translate-button":
            # 翻译按钮
            self.app.call_later(self.translate_text)
            
        elif event.button.id == "add-vocabulary-button":
            # 添加到单词本按钮
            self.add_to_vocabulary()
            
        elif event.button.id == "close-button":
            # 关闭按钮
            self.dismiss({
                'action': 'close',
                'translation_result': self.translation_result
            })
    
    def add_to_vocabulary(self) -> None:
        """添加到单词本"""
        if not self.translation_result or not self.translation_result.get('success'):
            return
            
        context = self.query_one("#context-input", Input).value.strip()
        translated_text = self.translation_result.get('translated_text', '')
        
        try:
            # 添加到单词本，使用书籍路径作为book_id
            vocabulary_item = self.vocabulary_manager.add_word(
                word=self.selected_text,
                translation=translated_text,
                language=self.translation_result.get('source_lang', 'en'),
                context=context,
                book_id=self.book_path  # 使用书籍的绝对路径作为book_id
            )
            
            if vocabulary_item:
                # 显示成功消息
                result_display = self.query_one("#translation-result", Static)
                success_msg = f"{get_global_i18n().t('translation_dialog.added_to_vocabulary')}"
                result_display.update(success_msg)
                
                # 禁用添加到单词本按钮，避免重复添加
                self.query_one("#add-vocabulary-button", Button).disabled = True
            else:
                # 显示错误消息
                result_display = self.query_one("#translation-result", Static)
                error_msg = f"{get_global_i18n().t('translation_dialog.add_to_vocabulary_failed')}"
                result_display.update(error_msg)
                
        except Exception as e:
            # 显示异常消息
            result_display = self.query_one("#translation-result", Static)
            error_msg = f"{get_global_i18n().t('translation_dialog.error')}: {str(e)}"
            result_display.update(error_msg)
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """输入框提交时的回调"""
        if event.input.id == "original-text-input":
            # 原文输入框提交时聚焦到目标语言输入框
            self.query_one("#target-language-input", Input).focus()
        elif event.input.id == "target-language-input":
            # 目标语言输入框提交时执行翻译
            self.app.call_later(self.translate_text)
        elif event.input.id == "context-input":
            # 上下文输入框提交时添加到单词本
            if not self.query_one("#add-vocabulary-button", Button).disabled:
                self.add_to_vocabulary()
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键关闭对话框
            self.dismiss({
                'action': 'close',
                'translation_result': self.translation_result
            })
            event.prevent_default()
            event.stop()
        elif event.key == "l":
            # L键重新翻译（刷新）
            self.app.call_later(self.translate_text)
            event.prevent_default()
            event.stop()

# 工厂函数
def create_translation_dialog(original_text: str, context: str = "", translation_manager: Optional[TranslationManager] = None, vocabulary_manager: Optional[VocabularyManager] = None, allow_input: bool = False, book_path: str = "") -> TranslationDialog:
    """创建翻译对话框实例"""
    return TranslationDialog(original_text, context, translation_manager, vocabulary_manager, allow_input, book_path)