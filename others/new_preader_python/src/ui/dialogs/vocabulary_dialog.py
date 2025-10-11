"""
单词本对话框 - 查看和管理已保存的单词
"""

from typing import List, Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static, Input, DataTable
from textual import events, on
from src.locales.i18n_manager import get_global_i18n, t
from src.core.vocabulary_manager import VocabularyManager, VocabularyItem
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class VocabularyDialog(ModalScreen[Dict[str, Any]]):
    """单词本对话框"""
    
    CSS_PATH = "../styles/vocabulary_dialog_overrides.tcss"
    
    def __init__(self, vocabulary_manager: Optional[VocabularyManager] = None, book_path: Optional[str] = None):
        super().__init__()
        self.vocabulary_manager = vocabulary_manager if vocabulary_manager is not None else VocabularyManager()
        self.book_path = book_path
        self.current_words: List[VocabularyItem] = []
        self.filtered_words: List[VocabularyItem] = []
        self.selected_row_index: Optional[int] = None
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Container(id="vocabulary-dialog-container", classes="panel"):
            yield Label(
                get_global_i18n().t("vocabulary_dialog.title"),
                id="dialog-title",
                classes="section-title"
            )
            
            # 搜索和统计区域
            with Vertical(id="search-section", classes="vocabulary-section"):
                with Horizontal():
                    yield Input(
                        placeholder=get_global_i18n().t("vocabulary_dialog.search_placeholder"),
                        id="search-input",
                        classes="vocabulary-input-std"
                    )
                    yield Button(
                        get_global_i18n().t("common.search"),
                        id="search-button",
                        classes="vocabulary-search-button",
                        variant="primary"
                    )
                    yield Button(
                        get_global_i18n().t("vocabulary_dialog.show_statistics"),
                        id="stats-button",
                        classes="vocabulary-stats-button",
                        variant="primary"
                    )
            
            # 统计信息显示区域
            with Vertical(id="stats-section", classes="vocabulary_section") as stats_section:
                yield Static("", id="stats-display", classes="text-display")
            
            # 单词列表区域
            with Vertical(id="words-section", classes="vocabulary_section"):
                yield Label(
                    get_global_i18n().t("vocabulary_dialog.word_list"),
                    classes="field-label"
                )
                yield DataTable(
                    id="words-table",
                    cursor_type="row"
                )
            
            # 单词详情区域
            with Vertical(id="detail-section", classes="vocabulary_section"):
                yield Label(
                    get_global_i18n().t("vocabulary_dialog.word_details"),
                    classes="field-label"
                )
                yield Static("", id="word-details", classes="text-display")
            
            # 操作按钮区域
            with Container(id="dialog-buttons", classes="btn-row"):
                yield Button(
                    get_global_i18n().t("vocabulary_dialog.review_words"),
                    id="review-button",
                    variant="success"
                )
                yield Button(
                    get_global_i18n().t("vocabulary_dialog.delete_word"),
                    id="delete-button",
                    variant="error",
                    disabled=True
                )
                yield Button(
                    get_global_i18n().t("common.close"),
                    id="close-button",
                    variant="primary"
                )
    
    def on_mount(self) -> None:
        """对话框挂载时的回调"""
        # 应用样式隔离
        apply_universal_style_isolation(self)
        # 初始化数据表格
        self.initialize_table()
        # 加载单词数据
        self.load_words()
        # 聚焦搜索输入框
        self.query_one("#search-input", Input).focus()
    
    def initialize_table(self) -> None:
        """初始化数据表格"""
        table = self.query_one("#words-table", DataTable)
        table.add_columns(
            get_global_i18n().t("vocabulary_dialog.column_word"),
            get_global_i18n().t("vocabulary_dialog.column_translation"),
            get_global_i18n().t("vocabulary_dialog.column_language"),
            get_global_i18n().t("vocabulary_dialog.column_mastery"),
            get_global_i18n().t("vocabulary_dialog.column_reviews")
        )
        table.zebra_stripes = True
        # 启用行选择功能
        table.cursor_type = "row"
    
    def load_words(self) -> None:
        """加载单词数据"""
        # 根据书籍路径过滤单词
        if self.book_path:
            # 只加载当前书籍的单词
            self.current_words = self.vocabulary_manager.get_words_by_book(self.book_path)
        else:
            # 加载所有单词
            self.current_words = self.vocabulary_manager.get_all_words()
        self.filtered_words = self.current_words.copy()
        self.update_table()
    
    def update_table(self) -> None:
        """更新表格显示"""
        table = self.query_one("#words-table", DataTable)
        table.clear()
        
        for word_item in self.filtered_words:
            mastery_level = word_item.mastery_level or 0
            mastery_display = "★" * mastery_level + "☆" * (5 - mastery_level)
            
            table.add_row(
                word_item.word,
                word_item.translation,
                word_item.language,
                mastery_display,
                str(word_item.review_count or 0)
            )
    
    def search_words(self, keyword: str) -> None:
        """搜索单词"""
        if not keyword.strip():
            self.filtered_words = self.current_words.copy()
        else:
            # 搜索所有单词，然后根据书籍路径过滤
            all_results = self.vocabulary_manager.search_words(keyword)
            if self.book_path:
                # 只保留当前书籍的搜索结果
                self.filtered_words = [word for word in all_results if word.book_id == self.book_path]
            else:
                self.filtered_words = all_results
        
        self.update_table()
    
    def show_statistics(self) -> None:
        """显示统计信息"""
        stats = self.vocabulary_manager.get_statistics()
        
        stats_text = f"""
{get_global_i18n().t('vocabulary_dialog.total_words')}: {stats.get('total_words', 0)}
{get_global_i18n().t('vocabulary_dialog.today_new')}: {stats.get('today_new', 0)}

{get_global_i18n().t('vocabulary_dialog.mastery_levels')}:
"""
        
        mastery_stats = stats.get('mastery_stats', {})
        for level in range(6):
            count = mastery_stats.get(level, 0)
            stars = "★" * level + "☆" * (5 - level)
            stats_text += f"  {stars}: {count}\n"
        
        stats_text += f"\n{get_global_i18n().t('vocabulary_dialog.languages')}:\n"
        language_stats = stats.get('language_stats', {})
        for lang, count in language_stats.items():
            stats_text += f"  {lang}: {count}\n"
        
        stats_display = self.query_one("#stats-display", Static)
        stats_display.update(stats_text)
        
        # 显示统计区域 - 使用CSS类控制显示
        stats_section = self.query_one("#stats-section", Vertical)
        stats_section.add_class("visible")
    
    def hide_statistics(self) -> None:
        """隐藏统计信息"""
        stats_section = self.query_one("#stats-section", Vertical)
        stats_section.remove_class("visible")
    
    def _resolve_row_index(self, row_key: Any) -> Optional[int]:
        """将 DataTable 的 row_key 解析为当前可见行索引"""
        table = self.query_one("#words-table", DataTable)
        # 优先使用 DataTable 的 API（Textual 新版提供）
        try:
            idx = table.get_row_index(row_key)  # type: ignore[attr-defined]
            if isinstance(idx, int):
                return idx
        except Exception:
            pass
        # 回退尝试直接转为 int
        try:
            return int(row_key)  # 兼容旧实现/整数索引
        except (ValueError, TypeError):
            return None

    def show_word_details(self, row_key: Any) -> None:
        """显示单词详情"""
        if row_key is None:
            # 清除选中状态
            self.selected_row_index = None
            details_display = self.query_one("#word-details", Static)
            details_display.update("请选择一个单词查看详情")
            delete_button = self.query_one("#delete-button", Button)
            delete_button.disabled = True
            return

        row_index = self._resolve_row_index(row_key)
        if row_index is None or row_index < 0 or row_index >= len(self.filtered_words):
            return
        
        word_item = self.filtered_words[row_index]
        
        details_text = f"""
单词: {word_item.word}
翻译: {word_item.translation}
语言: {word_item.language}
掌握程度: {"★" * word_item.mastery_level + "☆" * (5 - word_item.mastery_level)}
复习次数: {word_item.review_count}
上下文: {word_item.context or '无'}
添加时间: {word_item.created_at.strftime('%Y-%m-%d %H:%M') if word_item.created_at else 'N/A'}
最后复习: {word_item.last_reviewed.strftime('%Y-%m-%d %H:%M') if word_item.last_reviewed else '未复习'}
"""
        
        details_display = self.query_one("#word-details", Static)
        details_display.update(details_text)
        
        # 启用删除按钮
        delete_button = self.query_one("#delete-button", Button)
        delete_button.disabled = False
        # 存储当前选中的行索引，供删除按钮使用
        self.selected_row_index = row_index
    
    def delete_selected_word(self, row_key: Any) -> bool:
        """删除选中的单词"""
        if row_key is None:
            return False

        row_index = self._resolve_row_index(row_key)
        if row_index is None or row_index < 0 or row_index >= len(self.filtered_words):
            return False
        
        word_item = self.filtered_words[row_index]
        
        # 检查word_id是否为None
        if word_item.id is None:
            return False
        
        try:
            success = self.vocabulary_manager.delete_word(word_item.id)
            if success:
                # 重新加载数据
                self.load_words()
                # 清空详情显示
                self.query_one("#word-details", Static).update("")
                # 禁用删除按钮
                self.query_one("#delete-button", Button).disabled = True
                return True
            return False
        except Exception:
            return False
    
    def start_review(self) -> None:
        """开始单词复习"""
        review_words = self.vocabulary_manager.get_words_for_review(limit=20)
        if not review_words:
            # 显示无单词可复习的消息
            details_display = self.query_one("#word-details", Static)
            details_display.update(get_global_i18n().t("vocabulary_dialog.no_words_to_review"))
            return
        
        # 创建复习会话
        self.dismiss({
            'action': 'start_review',
            'review_words': [word.to_dict() for word in review_words]
        })
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "search-button":
            # 搜索按钮
            search_input = self.query_one("#search-input", Input)
            self.search_words(search_input.value.strip())
            
        elif event.button.id == "stats-button":
            # 统计按钮
            stats_section = self.query_one("#stats-section", Vertical)
            if stats_section.has_class("visible"):
                self.hide_statistics()
            else:
                self.show_statistics()
                
        elif event.button.id == "review-button":
            # 复习按钮
            self.start_review()
            
        elif event.button.id == "delete-button":
            # 删除按钮
            if self.selected_row_index is not None:
                self.delete_selected_word(self.selected_row_index)
                
        elif event.button.id == "close-button":
            # 关闭按钮
            self.dismiss({
                'action': 'close',
                'word_count': len(self.current_words)
            })
    
    @on(DataTable.RowSelected)
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """表格行选中时的回调"""
        if event.row_key is not None:
            # 解析索引并记录
            idx = self._resolve_row_index(event.row_key)
            if idx is None:
                return
            self.selected_row_index = idx
            self.show_word_details(event.row_key)
            # 确保删除按钮启用
            delete_button = self.query_one("#delete-button", Button)
            delete_button.disabled = False
        else:
            # 清除选中状态
            self.selected_row_index = None
            details_display = self.query_one("#word-details", Static)
            details_display.update("请选择一个单词查看详情")
            delete_button = self.query_one("#delete-button", Button)
            delete_button.disabled = True
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """输入框内容改变时的回调"""
        if event.input.id == "search-input":
            self.search_words(event.input.value.strip())
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """输入框提交时的回调"""
        if event.input.id == "search-input":
            self.search_words(event.input.value.strip())
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键关闭对话框
            self.dismiss({
                'action': 'close',
                'word_count': len(self.current_words)
            })
            event.prevent_default()
            event.stop()
        elif event.key == "delete":
            # Delete键删除选中的单词
            table = self.query_one("#words-table", DataTable)
            row_key = table.cursor_row
            if row_key is not None:
                if self.delete_selected_word(row_key):
                    event.prevent_default()
                    event.stop()

# 工厂函数
def create_vocabulary_dialog(vocabulary_manager: Optional[VocabularyManager] = None, book_path: Optional[str] = None) -> VocabularyDialog:
    """创建单词本对话框实例"""
    return VocabularyDialog(vocabulary_manager, book_path)