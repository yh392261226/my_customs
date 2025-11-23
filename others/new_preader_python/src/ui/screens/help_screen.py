"""
帮助屏幕
"""


from typing import Dict, Any, Optional, List, ClassVar

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, MarkdownViewer, Header, Footer
from textual.reactive import reactive

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n, t
from src.utils.logger import get_logger
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.core.database_manager import DatabaseManager

logger = get_logger(__name__)

class HelpScreen(Screen[None]):
    """帮助屏幕"""
    CSS_PATH = "../styles/help_screen_overrides.tcss"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("t", "toggle_table_of_contents", get_global_i18n().t('help.toggle_table_of_contents')),
    ]
    
    def __init__(self):
        """
        初始化帮助屏幕
        """
        super().__init__()
        self.title = get_global_i18n().t("help.title")
        # self.db_manager = DatabaseManager()  # 数据库管理器
        
        # 逐行从语言包读取，拼装 Markdown
        self.help_content = (
            f"# {t('help.sub_title')}\n\n"
            f"## {t('help.keyboard_shortcuts')}\n\n"
            # 全局
            f"### {t('help.global')}\n"
            f"- h  : {t('app.bindings.help')}\n"
            f"- k  : {t('app.bindings.bookshelf')}\n"
            f"- s  : {t('app.bindings.settings')}\n"
            f"- c  : {t('app.bindings.statistics')}\n"
            f"- /  : {t('app.bindings.boss_key')}\n"
            f"- t  : {t('settings.theme')}\n"
            f"- ESC: {t('common.back')}\n"
            f"- q  : {t('help.quit')}\n\n"
            # 阅读器
            f"### {t('reader.title')}\n"
            f"- ← p/n → : {t('help.prev_next_page')}\n"
            f"- ↑/↓ : {t('help.scroll_content')}\n"
            f"- g   : {t('reader.go_to_page')}\n"
            f"- a   : {t('reader.auto_page')}\n"
            f"- b   : {t('reader.bookmark')}\n"
            f"- B   : {t('reader.bookmark_list')}\n"
            f"- f   : {t('reader.search')}\n"
            f"- r   : {t('reader.aloud')}\n"
            f"- /   : {t('help.boss_key')}\n"
            f"- s   : {t('reader.settings')}\n"
            f"- o   : {t('bookshelf.view_file')}\n"
            f"- l   : {t('reader.translation')}\n"
            f"- w   : {t('reader.vocabulary')}\n"
            f"- {t('reader.vocabulary_info')}\n\n"
            f"- v   : {t('reader.enter_selection_mode')}\n"
            f"- {t('selection_mode.in_notify_message')}\n\n"
            # 欢迎页
            f"### {t('welcome.title')}\n"
            f"- F1/1 : {t('welcome.open_book')}\n"
            f"- F2/2 : {t('welcome.browse_library')}\n"
            f"- F3/3 : {t('welcome.get_books')}\n"
            f"- F4/4 : {t('welcome.manage')}\n"
            f"- F5/5 : {t('welcome.settings')}\n"
            f"- F6/6 : {t('welcome.statistics')}\n"
            f"- F7/7 : {t('welcome.help')}\n"
            f"- ESC/Q: {t('welcome.exit')}\n\n"
            # 书架
            f"### {t('bookshelf.title')}\n"
            f"- s    : {t('bookshelf.search')}\n"
            f"- r    : {t('bookshelf.sort_name')}\n"
            f"- l    : {t('bookshelf.batch_ops_name')}\n"
            f"- f    : {t('bookshelf.refresh')}\n"
            f"- a    : {t('bookshelf.add_book')}\n"
            f"- d    : {t('bookshelf.scan_directory')}\n"
            f"- g    : {t('bookshelf.get_books')}\n"
            f"- p/n  : {t('bookshelf.prev_page')} / {t('bookshelf.next_page')}\n"
            f"- ↑↓   : {t('bookshelf.choose_book')}\n"
            f"- x    : {t('bookshelf.clear_search_params')}"
            f"- Enter: {t('bookshelf.open_book')}\n"
            f"- ESC  : {t('bookshelf.back')}\n\n"
            # 文件资源管理器
            f"### {t('file_explorer.title')}\n"
            f"- b      : {t('file_explorer.back')}\n"
            f"- g      : {t('file_explorer.go')}\n"
            f"- H      : {t('file_explorer.home')}\n"
            f"- s      : {t('common.select')}\n"
            f"- →      : {t('file_explorer.right')}\n"
            f"- ↑/↓    : {t('file_explorer.updown')}\n"
            f"- Enter/s: {t('common.select')}\n"
            f"- ESC    : {t('common.back')}\n\n"
            # 搜索结果
            f"### {t('search_results_screen.title')}\n"
            f"- n/p  : {t('bookshelf.next_page')} / {t('bookshelf.prev_page')}\n"
            f"- ESC  : {t('common.back')}\n\n"
            # 获取书籍
            f"### {t('get_books.title')}\n"
            f"- N    : {t('get_books.novel_sites')}\n"
            f"- P    : {t('get_books.proxy_settings')}\n"
            f"- Space: {t('get_books.shortcut_space')}\n"
            f"- Enter: {t('get_books.shortcut_enter')}\n"
            f"- p    : {t('crawler.prev_page')}\n"
            f"- n    : {t('crawler.next_page')}\n"
            f"- Enter: {t('get_books.shortcut_enter')}\n"
            f"- ESC  : {t('common.back')}\n\n"
            # 统计
            f"### {t('statistics.title')}\n"
            f"- r    : {t('statistics.refresh')}\n"
            f"- e    : {t('statistics.export')}\n"
            f"- ESC  : {t('common.back')}\n\n"
            # 书籍网站管理
            f"### {t('novel_sites.title')}\n"
            f"- a    : {t('novel_sites.add')}\n"
            f"- e    : {t('novel_sites.edit')}\n"
            f"- d    : {t('novel_sites.delete')}\n"
            f"- b    : {t('novel_sites.batch_delete')}\n"
            f"- p    : {t('crawler.prev_page')}\n"
            f"- n    : {t('crawler.next_page')}\n"
            f"- Enter: {t('novel_sites.shortcut_enter')}\n"
            f"- Space: {t('batch_ops.toggle_rows')}\n"
            f"- ESC  : {t('common.back')}\n\n"
            # 代理列表
            f"### {t('proxy_list.title')}\n"
            f"- a    : {t('proxy_list.add_proxy')}\n"
            f"- t    : {t('proxy_list.test_connection')}\n"
            f"- e    : {t('proxy_list.edit_proxy')}\n"
            f"- d    : {t('proxy_list.delete_proxy')}\n"
            f"- p    : {t('crawler.prev_page')}\n"
            f"- n    : {t('crawler.next_page')}\n"
            f"- ESC  : {t('common.back')}\n\n"
            # 爬取管理
            f"### {t('crawler.title')}\n"
            f"- o    : {t('crawler.open_browser')}\n"
            f"- r    : {t('crawler.view_history')}\n"
            f"- s    : {t('crawler.start_crawl')}\n"
            f"- v    : {t('crawler.stop_crawl')}\n"
            f"- x    : {t('crawler.select_books')}\n"
            f"- b    : {t('note.title')}\n"
            f"- p/n  : {t('crawler.prev_page')} / {t('crawler.next_page')}\n"
            f"- Space: {t('batch_ops.toggle_rows')}\n"
            f"- ESC  : {t('common.back')}\n\n"
            # 选择书籍
            f"### {t('select_books.select_books')}\n"
            f"- s    : {t('common.search')}\n"
            f"- g    : {t('common.ok')}\n"
            f"- ESC  : {t('common.back')}\n\n"
            # 设置
            f"### {t('settings.title')}\n"
            f"- r    : {t('settings.reset')}\n"
            f"- Enter: {t('settings.save')}\n"
            # 关于
            f"## {t('help.about')}\n"
            f"{t('help.about_content')}\n"
        )
    
    def compose(self) -> ComposeResult:
        """
        组合帮助屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Vertical(
                # 顶部标题区域
                # Label(get_global_i18n().t("help.title"), id="help-title", classes="section-title"),
                
                # 中间内容区域 - 目录和预览分栏
                Horizontal(
                    # 左侧目录区域
                    # Vertical(
                    #     Label("目录", id="toc-title"),
                    #     Static(self.toc_content, id="help-toc"),
                    #     id="help-toc-container"
                    # ),
                    # 右侧Markdown预览区域
                    MarkdownViewer(self.help_content, id="help-content", show_table_of_contents=True),
                    id="help-content-area"
                ),
                
                # 底部按钮和快捷键区域
                Horizontal(
                    Button(get_global_i18n().t("help.back"), id="back-btn"),
                    id="help-controls", classes="btn-row"
                ),
                id="help-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        from src.ui.styles.style_manager import apply_style_isolation
        self.query_one("#help-container").focus()
        apply_style_isolation(self)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "back-btn":
            self.app.pop_screen()

    @property
    def markdown_viewer(self) -> MarkdownViewer:
        """Get the Markdown widget."""
        return self.query_one(MarkdownViewer)

    def action_toggle_table_of_contents(self) -> None:
        if self.query_one("MarkdownTableOfContents").styles.display == 'none': 
            self.query_one("MarkdownTableOfContents").styles.display = 'block'
        else:
            self.query_one("MarkdownTableOfContents").styles.display = 'none'

    
    def on_key(self, event) -> None:
        """
        处理键盘事件
        
        Args:
            event: 键盘事件
        """
        if event.key == "escape":
            self.app.pop_screen()
            event.stop()
            event.prevent_default()