"""
可复用文本编辑器对话框

这是一个高度可复用的纯文本编辑器，基于 Textual 的 TextArea 实现，支持：
- 复制 / 粘贴 / 撤销 / 重做（工具栏按钮 + 内置快捷键）
- 多行文本编辑（换行）
- 字符数 / 行数实时统计
- 自动换行开关
- 只读模式
- 保存回调（可将内容写回文件或交给调用方处理）
- 未保存修改时关闭提示

可在项目任意位置复用，例如：
    self.app.push_screen(TextEditorModal(
        theme_manager=self.theme_manager,
        title="编辑书籍",
        file_path="/path/to/book.md",
        language="markdown",
    ))
"""

from typing import Optional, Callable, Any, ClassVar
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Label, TextArea
from textual.app import ComposeResult
from textual import events

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.ui.dialogs.confirm_dialog import ConfirmDialog

logger = get_logger(__name__)


class TextEditorModal(ModalScreen[Optional[str]]):
    """可复用文本编辑器对话框

    返回值：
        - 保存成功：返回编辑后的文本内容（str）
        - 取消 / 未保存关闭：返回 None
    """

    CSS_PATH = ["../styles/utilities.tcss", "../styles/text_editor_overrides.tcss"]

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("ctrl+s", "save", get_global_i18n().t('editor.save')),
        ("ctrl+w", "toggle_wrap", get_global_i18n().t('editor.word_wrap')),
        ("escape", "close", get_global_i18n().t('editor.close')),
    ]

    def __init__(
        self,
        theme_manager: ThemeManager,
        title: str = "",
        initial_text: str = "",
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        on_save: Optional[Callable[[str], Any]] = None,
        read_only: bool = False,
        show_line_numbers: bool = True,
        word_wrap: bool = True,
        placeholder: str = "",
    ) -> None:
        """
        初始化文本编辑器

        Args:
            theme_manager: 主题管理器
            title: 编辑器标题（默认使用国际化 "文本编辑器"）
            initial_text: 初始文本内容（当未提供 file_path 时使用）
            file_path: 关联的文件路径；提供时自动读取内容，保存时写回该文件
            language: 语法高亮语言（如 "markdown"、"python"），None 表示纯文本
            on_save: 保存回调，签名为 (text: str) -> None；保存文件后调用，可抛异常中断保存
            read_only: 只读模式（禁用编辑与保存）
            show_line_numbers: 是否显示行号
            word_wrap: 是否自动换行
            placeholder: 空内容时的占位提示
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.title = title or get_global_i18n().t('editor.title')
        self.initial_text = initial_text or ""
        self.file_path = file_path
        self.language = language
        self.on_save = on_save
        self.read_only = read_only
        self.show_line_numbers = show_line_numbers
        self.word_wrap = word_wrap
        self.placeholder = placeholder

        self._original_text: str = ""
        self._is_dirty: bool = False

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        with Container(id="editor-screen-container"):
            with Vertical(id="editor-root"):
                yield Label(self.title, id="editor-title", classes="section-title")

                with Horizontal(id="editor-toolbar"):
                    yield Button(get_global_i18n().t('editor.save'), id="editor-save-btn", variant="primary")
                    yield Button(get_global_i18n().t('editor.copy'), id="editor-copy-btn")
                    yield Button(get_global_i18n().t('editor.paste'), id="editor-paste-btn")
                    yield Button(get_global_i18n().t('editor.undo'), id="editor-undo-btn")
                    yield Button(get_global_i18n().t('editor.redo'), id="editor-redo-btn")
                    yield Button(get_global_i18n().t('editor.clear'), id="editor-clear-btn")
                    yield Button(get_global_i18n().t('editor.word_wrap'), id="editor-wrap-btn")
                    yield Button(get_global_i18n().t('editor.edit_in_browser'), id="editor-browser-btn", variant="success")
                    yield Button(get_global_i18n().t('editor.close'), id="editor-close-btn", variant="error")

                yield TextArea(
                    self._original_text,
                    id="editor-textarea",
                    language=self.language,
                    show_line_numbers=self.show_line_numbers,
                    read_only=self.read_only,
                    soft_wrap=self.word_wrap,
                    placeholder=self.placeholder,
                    classes="textarea-std",
                )

                with Horizontal(id="editor-statusbar"):
                    yield Label("", id="editor-stats")
                    yield Label("", id="editor-modified")

    def on_mount(self) -> None:
        # 读取关联文件内容
        if self.file_path:
            self._original_text = self._read_file(self.file_path)
        else:
            self._original_text = self.initial_text

        # 将内容写入 TextArea（compose 时 _original_text 可能尚未就绪，这里重新填充）
        textarea = self.query_one("#editor-textarea", TextArea)
        if textarea.text != self._original_text:
            textarea.text = self._original_text

        # 只读模式：禁用编辑相关按钮
        if self.read_only:
            for btn_id in ("editor-save-btn", "editor-paste-btn", "editor-undo-btn",
                           "editor-redo-btn", "editor-clear-btn", "editor-wrap-btn"):
                try:
                    self.query_one(f"#{btn_id}", Button).disabled = True
                except Exception:
                    pass

        # 未关联文件时，禁用「浏览器编辑」按钮
        if not self.file_path:
            try:
                self.query_one("#editor-browser-btn", Button).disabled = True
            except Exception:
                pass

        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)

        # 聚焦编辑器
        self.set_focus(textarea)
        self._update_status()

    # ------------------------------------------------------------------
    # 文件读写
    # ------------------------------------------------------------------
    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {path}: {e}")
            self.notify(
                get_global_i18n().t('editor.load_failed', error=str(e)),
                severity="error",
            )
            return ""

    def _write_file(self, path: str, text: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    # ------------------------------------------------------------------
    # 工具栏 / 按钮
    # ------------------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "editor-save-btn":
            self.action_save()
        elif btn_id == "editor-copy-btn":
            self._copy()
        elif btn_id == "editor-paste-btn":
            self._paste()
        elif btn_id == "editor-undo-btn":
            self._undo()
        elif btn_id == "editor-redo-btn":
            self._redo()
        elif btn_id == "editor-clear-btn":
            self._clear()
        elif btn_id == "editor-wrap-btn":
            self.action_toggle_wrap()
        elif btn_id == "editor-browser-btn":
            self._edit_in_browser()
        elif btn_id == "editor-close-btn":
            self.action_close()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """文本变化 -> 标记脏状态并更新统计"""
        self._is_dirty = event.text_area.text != self._original_text
        self._update_status()

    # ------------------------------------------------------------------
    # 编辑操作
    # ------------------------------------------------------------------
    def _copy(self) -> None:
        textarea = self.query_one("#editor-textarea", TextArea)
        selected = textarea.selected_text
        text = selected if selected else textarea.text
        if not text:
            return
        # 优先写入系统剪贴板，同时写入内置剪贴板作为回退
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception as e:
            logger.debug(f"复制到系统剪贴板失败，使用内置剪贴板: {e}")
        self.app.copy_to_clipboard(text)
        self.notify(get_global_i18n().t('editor.copy') + " ✓", timeout=1.5)

    def _paste(self) -> None:
        if self.read_only:
            return
        textarea = self.query_one("#editor-textarea", TextArea)
        text = ""
        try:
            import pyperclip
            text = pyperclip.paste()
        except Exception as e:
            logger.debug(f"读取系统剪贴板失败: {e}")
        if text:
            textarea.insert(text)
        else:
            # 退回到 TextArea 内置剪贴板（如 Ctrl+C 复制的内容）
            textarea.action_paste()

    def _undo(self) -> None:
        self.query_one("#editor-textarea", TextArea).action_undo()

    def _redo(self) -> None:
        self.query_one("#editor-textarea", TextArea).action_redo()

    def _clear(self) -> None:
        if self.read_only:
            return
        textarea = self.query_one("#editor-textarea", TextArea)
        textarea.text = ""

    def _edit_in_browser(self) -> None:
        """在浏览器中打开功能更强大的网页编辑器编辑同一文件"""
        if not self.file_path:
            self.notify(
                get_global_i18n().t('editor.browser_edit_requires_file'),
                severity="warning",
            )
            return
        try:
            from src.utils.browser_editor import BrowserEditorServer, open_in_browser
            url = BrowserEditorServer(self.file_path).start()
            open_in_browser(url)
            self.notify(
                get_global_i18n().t('editor.open_in_browser_ok', title=self.title, url=url),
                severity="information",
            )
        except Exception as e:
            logger.error(f"打开浏览器编辑器失败: {e}")
            self.notify(
                get_global_i18n().t('editor.open_in_browser_fail'),
                severity="error",
            )

    # ------------------------------------------------------------------
    # 保存 / 关闭
    # ------------------------------------------------------------------
    def action_save(self) -> None:
        if self.read_only:
            self.notify(get_global_i18n().t('editor.read_only_hint'), severity="warning")
            return
        textarea = self.query_one("#editor-textarea", TextArea)
        text = textarea.text
        try:
            if self.file_path:
                self._write_file(self.file_path, text)
            if self.on_save is not None:
                self.on_save(text)
            self._original_text = text
            self._is_dirty = False
            self._update_status()
            self.notify(get_global_i18n().t('editor.saved_success'), severity="information")
            # 保存成功后返回编辑后的内容，便于调用方刷新
            self.dismiss(text)
        except Exception as e:
            logger.error(f"保存失败: {e}")
            self.notify(
                get_global_i18n().t('editor.save_failed', error=str(e)),
                severity="error",
            )

    def action_toggle_wrap(self) -> None:
        textarea = self.query_one("#editor-textarea", TextArea)
        textarea.soft_wrap = not textarea.soft_wrap
        self.word_wrap = textarea.soft_wrap
        self._update_status()

    def action_close(self) -> None:
        if self._is_dirty and not self.read_only:
            def _on_confirm(confirmed: Optional[bool]) -> None:
                if confirmed:
                    self.dismiss(None)
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    get_global_i18n().t('editor.confirm_close_title'),
                    get_global_i18n().t('editor.confirm_close_msg'),
                ),
                _on_confirm,
            )
        else:
            self.dismiss(None)

    # ------------------------------------------------------------------
    # 状态栏
    # ------------------------------------------------------------------
    def _update_status(self) -> None:
        try:
            textarea = self.query_one("#editor-textarea", TextArea)
        except Exception:
            return
        text = textarea.text
        char_count = len(text)
        line_count = text.count("\n") + 1 if text else 0

        stats = f"{get_global_i18n().t('editor.char_count')}: {char_count}   " \
                f"{get_global_i18n().t('editor.line_count')}: {line_count}"
        if self.word_wrap:
            stats += f"   [✓{get_global_i18n().t('editor.word_wrap')}]"
        stats_label = self.query_one("#editor-stats", Label)
        if stats_label:
            stats_label.update(stats)

        modified = self.query_one("#editor-modified", Label)
        if modified:
            if self.read_only:
                modified.update(f"[{get_global_i18n().t('editor.read_only')}]")
            elif self._is_dirty:
                modified.update(f"● {get_global_i18n().t('editor.edited_label')}")
            else:
                modified.update("")
