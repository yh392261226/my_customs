from typing import List, Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Label, Static
from textual.screen import ModalScreen
from textual import events
from src.locales.i18n_manager import get_global_i18n
from src.core.vocabulary_manager import VocabularyManager, VocabularyItem
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation

class ReviewDialog(ModalScreen[Dict[str, Any]]):
    """单词复习对话框：按序呈现待复习单词，记录复习结果"""

    # 可选：如需专用样式，可添加对应 tcss 并指向；为最小改动先不绑定专用 tcss
    # CSS_PATH = "../styles/review_dialog_overrides.tcss"

    def __init__(self, review_words: List[Dict[str, Any]], vocabulary_manager: Optional[VocabularyManager] = None) -> None:
        super().__init__()
        self.vocabulary_manager = vocabulary_manager if vocabulary_manager is not None else VocabularyManager()
        # 将 dict 恢复为 VocabularyItem，确保有 mastery_level/review_count 等
        self.words: List[VocabularyItem] = [VocabularyItem.from_dict(w) if not isinstance(w, VocabularyItem) else w for w in review_words]  # type: ignore
        self.index: int = 0
        self.total: int = len(self.words)

    def on_mount(self) -> None:
        apply_universal_style_isolation(self)
        # 首次渲染
        self._render_current()

    def compose(self) -> ComposeResult:
        with Container(id="review-dialog-container", classes="panel"):
            yield Label(get_global_i18n().t("vocabulary_dialog.review_session_title"), id="review-title", classes="section-title")
            with Vertical(id="review-body"):
                yield Static("", id="word-display", classes="text-display")
                yield Static("", id="meta-display", classes="text-display")
            with Container(id="review-buttons", classes="btn-row"):
                yield Button(get_global_i18n().t("vocabulary_dialog.known"), id="btn-known", variant="success")
                yield Button(get_global_i18n().t("vocabulary_dialog.unknown"), id="btn-unknown", variant="error")
                yield Button(get_global_i18n().t("vocabulary_dialog.skip"), id="btn-skip", variant="primary")
                yield Button(get_global_i18n().t("common.close"), id="btn-finish", variant="primary")

    def _render_current(self) -> None:
        word_display = self.query_one("#word-display", Static)
        meta_display = self.query_one("#meta-display", Static)
        if self.index >= self.total or self.total == 0:
            word_display.update(get_global_i18n().t("vocabulary_dialog.review_finished"))
            meta_display.update(get_global_i18n().t("vocabulary_dialog.review_summary").format(total=self.total, reviewed=sum(1 for w in self.words if (w.review_count or 0) > 0)))
            return
        item = self.words[self.index]
        # 展示当前单词和简单信息
        word_display.update(f"{item.word}  ({item.language})")
        mastery = max(0, min(5, item.mastery_level or 0))
        reviews = item.review_count or 0
        meta_display.update(f"掌握度: {'★'*mastery + '☆'*(5-mastery)}  复习次数: {reviews}\n翻译: {item.translation or ''}\n上下文: {item.context or ''}")

    def _apply_result(self, known: bool) -> None:
        """根据答题结果更新数据库与内存，并跳到下一个"""
        if self.index >= self.total:
            return
        item = self.words[self.index]
        # 计算新掌握度（答对+1，答错-1），限制在 0..5
        current_level = item.mastery_level or 0
        new_level = current_level + (1 if known else -1)
        new_level = max(0, min(5, new_level))
        # 写入数据库：自增复习次数、更新时间，并设置 mastery_level
        if item.id is not None:
            try:
                self.vocabulary_manager.record_review(word_id=item.id, mastery_level=new_level)
                # 同步更新内存对象，便于后续显示
                item.mastery_level = new_level
                item.review_count = (item.review_count or 0) + 1
            except Exception:
                pass
        # 下一个
        self.index += 1
        self._render_current()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-known":
            self._apply_result(True)
        elif event.button.id == "btn-unknown":
            self._apply_result(False)
        elif event.button.id == "btn-skip":
            # 跳过不更新，直接下一个
            if self.index < self.total:
                self.index += 1
                self._render_current()
        elif event.button.id == "btn-finish":
            # 结束并返回复习统计
            reviewed = sum(1 for w in self.words if (w.review_count or 0) > 0)
            self.dismiss({"action": "finish", "reviewed": reviewed, "total": self.total})

    def on_key(self, event: events.Key) -> None:
        # 快捷键：j/k 或 左右方向键控制认识/不认识，space 跳过，esc 结束
        if event.key in ("j", "right"):
            self._apply_result(True)
            event.prevent_default(); event.stop()
        elif event.key in ("k", "left"):
            self._apply_result(False)
            event.prevent_default(); event.stop()
        elif event.key in ("space",):
            if self.index < self.total:
                self.index += 1
                self._render_current()
            event.prevent_default(); event.stop()
        elif event.key == "escape":
            reviewed = sum(1 for w in self.words if (w.review_count or 0) > 0)
            self.dismiss({"action": "finish", "reviewed": reviewed, "total": self.total})
            event.prevent_default(); event.stop()