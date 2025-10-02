"""
终端阅读器屏幕 - 简化版本，解决渲染问题
"""


import os
from typing import Dict, Any, Optional, List, ClassVar
from datetime import datetime
import time
from webbrowser import get
from textual import events
from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, ProgressBar
from textual.reactive import reactive

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.book import Book
from src.core.statistics_direct import StatisticsManagerDirect
from src.ui.components.content_renderer import ContentRenderer
from src.core.bookmark import BookmarkManager, Bookmark
from src.core.search import SearchResult
from src.ui.components.reader_controls import ReaderControls
from src.ui.components.reader_status import ReaderStatus
from src.ui.components.textual_loading_animation import TextualLoadingAnimation, textual_animation_manager
from src.ui.dialogs.page_dialog import PageDialog
from src.ui.dialogs.content_search_dialog import ContentSearchDialog
from src.ui.dialogs.bookmark_dialog import BookmarkDialog
from src.ui.screens.bookmarks_screen import BookmarksScreen
from src.ui.screens.search_results_screen import SearchResultsScreen
from src.utils.text_to_speech import TextToSpeech as TTSManager
from src.config.settings.setting_registry import SettingRegistry
from src.ui.messages import RefreshBookshelfMessage, RefreshContentMessage
from src.ui.styles.style_manager import ScreenStyleMixin
from src.ui.styles.comprehensive_style_isolation import apply_comprehensive_style_isolation, remove_comprehensive_style_isolation

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderScreen(ScreenStyleMixin, Screen[None]):
    """终端阅读器屏幕 - 简化版本"""
    CSS_PATH = "../styles/isolated_reader.css"
    
    TITLE: ClassVar[Optional[str]] = None
    
    def __init__(self, book: Book, theme_manager: ThemeManager, 
                 statistics_manager: StatisticsManagerDirect, bookmark_manager: BookmarkManager,
                 bookshelf: Optional[Any] = None):
        """初始化阅读器屏幕"""
        super().__init__()
        # 使用实例变量而不是类变量来避免重新定义常量
        self._title = get_global_i18n().t('reader.title')
        self.book = book
        self.theme_manager = theme_manager
        self.statistics_manager = statistics_manager
        self.bookmark_manager = bookmark_manager
        self.bookshelf = bookshelf
        self.book_id = book.path if hasattr(book, 'path') else str(id(book))
        
        # 获取设置注册表
        self.settings_registry = SettingRegistry()
        
        # 从设置系统获取渲染配置
        self.render_config = self._load_render_config_from_settings()
        
        # 创建内容渲染器
        self.renderer = ContentRenderer(
            container_width=80,
            container_height=20,
            config=self.render_config
        )
        
        # 注册设置观察者
        self._register_setting_observers()
        
        # 创建其他组件
        self.controls = ReaderControls(self.render_config)
        self.status_manager = ReaderStatus(self.render_config)
        
        # 阅读状态
        self.current_page = 0
        self.total_pages = 0
        self.auto_turn_enabled = False
        self.auto_turn_timer = None
        # 避免未初始化告警
        self.reading_start_time = 0.0
        self.last_progress_update = 0.0
        
        # 行级滚动状态
        self.can_scroll_up = False
        self.can_scroll_down = False
        
        # TTS管理器
        self.tts_manager = TTSManager()
        self.tts_enabled = False
        
        # 设置组件回调
        self._setup_component_callbacks()
        
        # 初始化加载动画
        self.loading_animation = TextualLoadingAnimation(id="loading-animation")
        textual_animation_manager.set_default_animation(self.loading_animation)
    
    def _load_render_config_from_settings(self) -> Dict[str, Any]:
        """从设置系统加载渲染配置"""
        config = {
            # 从设置系统获取阅读相关配置
            "font_size": self.settings_registry.get_value("reading.font_size", 16),
            "line_spacing": self.settings_registry.get_value("reading.line_spacing", 0),
            "paragraph_spacing": self.settings_registry.get_value("reading.paragraph_spacing", 0),
            "remember_position": self.settings_registry.get_value("reading.remember_position", True),
            "auto_page_turn_interval": self.settings_registry.get_value("reading.auto_page_turn_interval", 30),
            "pagination_strategy": self.settings_registry.get_value("reading.pagination_strategy", "smart"),
            "highlight_search": self.settings_registry.get_value("reading.highlight_search", True),
            
            # 从设置系统获取外观相关配置
            "theme": self.settings_registry.get_value("appearance.theme", "dark"),
            "show_icons": self.settings_registry.get_value("appearance.show_icons", True),
            "animation_enabled": self.settings_registry.get_value("appearance.animation_enabled", True),
            
            # 边距设置
            "margin_left": 1,
            "margin_right": 1,
            "margin_top": 1,
            "margin_bottom": 1
        }
        
        logger.debug(f"从设置系统加载的配置: {config}")
        return config
    
    def _setup_component_callbacks(self) -> None:
        """设置组件回调"""
        self.controls.register_callback("page_changed", self._on_page_change)
        self.controls.register_callback("auto_turn_changed", self._on_auto_turn_change)
        self.controls.register_callback("config_changed", self._on_config_change)
    
    def compose(self) -> ComposeResult:
        """组合阅读器屏幕界面"""
        # 标题栏
        yield Static(f"📖 {get_global_i18n().t('reader.title')}", id="header")
        
        # 加载动画 - 放在内容区域之前
        yield self.loading_animation
        
        # 内容区域 - 设置ID为content以便CSS定位
        self.renderer.id = "content"
        yield self.renderer
        
        # 按钮区域 - 使用HorizontalScroll实现水平滚动
        from textual.containers import HorizontalScroll
        with HorizontalScroll(id="reader-buttons-container"):
            with Horizontal(id="reader-buttons"):
                yield Button(f"{get_global_i18n().t('reader.prev_chapter')}【←】", classes="btn", id="prev-btn")
                yield Button(f"{get_global_i18n().t('reader.next_chapter')}【→】", classes="btn", id="next-btn")
                yield Button(f"{get_global_i18n().t('reader.goto_page')}【g】", classes="btn", id="goto-btn")
                yield Button(f"{get_global_i18n().t('reader.search')}【f】", classes="btn", id="search-btn")
                yield Button(f"{get_global_i18n().t('reader.add_remove_bookmark')}【b】", classes="btn", id="bookmark-btn")
                yield Button(f"{get_global_i18n().t('reader.bookmark_list')}【B】", classes="btn", id="bookmark-list-btn")
                yield Button(f"{get_global_i18n().t('reader.aloud')}【R】", classes="btn", id="aloud-btn")
                yield Button(f"{get_global_i18n().t('reader.auto_page')}【a】", classes="btn", id="auto-page-btn")
                yield Button(f"{get_global_i18n().t('reader.settings')}【s】", classes="btn", id="settings-btn")
                yield Button(f"{get_global_i18n().t('common.back')}【q】", classes="btn", id="back-btn")
        
        # 状态栏
        yield Static("", id="reader-status")
    
    def on_mount(self) -> None:
        # 应用全面的样式隔离
        apply_comprehensive_style_isolation(self)
        
        # 调用父类的on_mount方法
        super().on_mount()
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 异步加载书籍内容（避免阻塞 UI 主线程）
        self._load_book_content_async()
        
        # 设置容器尺寸
        self._set_container_size()
        
        # 阅读位置恢复现在在内容加载完成后进行
        # 参见 _load_book_content_async 方法中的 _on_ok 回调
        
        # 开始阅读会话
        self.status_manager.start_reading(
            current_page=self.renderer.current_page,
            total_pages=self.renderer.total_pages,
            word_count=self.book.word_count
        )
        
        # 同步页面状态
        self.current_page = self.renderer.current_page
        self.total_pages = self.renderer.total_pages
        
        # 初始化阅读时间记录
        self.reading_start_time = time.time()
        self.last_progress_update = time.time()
        
        # 更新界面
        self._update_ui()
    
    def _set_container_size(self) -> None:
        # 获取屏幕尺寸
        screen_width = self.size.width
        screen_height = self.size.height
        
        if screen_width <= 0 or screen_height <= 0:
            self.set_timer(0.1, self._set_container_size)
            return
        
        # 计算内容区域可用尺寸
        # 标题栏(1行) + 按钮区域(1行) + 状态栏(1行) = 3行
        available_width = screen_width - 2  # 减去左右边距
        available_height = screen_height - 3  # 减去固定区域
        
        # 确保最小尺寸
        width = max(60, available_width)
        height = max(15, available_height)
        
        # 临时调试信息
        # print(f"DEBUG: 屏幕尺寸: {screen_width}x{screen_height}, 计算的内容尺寸: {width}x{height}")
        # logger.debug(f"屏幕尺寸: {screen_width}x{screen_height}, 内容尺寸: {width}x{height}")
        
        # 设置渲染器容器尺寸
        self.renderer.set_container_size(width, height)
        
        # 同步状态
        self.current_page = self.renderer.current_page
        self.total_pages = self.renderer.total_pages
        
        # print(f"DEBUG: 分页后总页数: {self.total_pages}")
        
        # 更新界面
        self._update_ui()
    
    def _load_book_content_async(self) -> None:
        # 直接在 UI 线程中显示加载动画（因为我们在 on_mount 中调用）
        self._show_loading_animation("正在加载书籍内容...")
        
        async def _worker():
            import asyncio
            try:
                # 在后台线程执行潜在的重计算/IO，避免阻塞 UI 主循环
                content = await asyncio.to_thread(self.book.get_content)
            except Exception as e:
                def _on_err():
                    # 回到 UI 线程处理错误并隐藏动画
                    self._hide_loading_animation()
                    self.notify(f"{get_global_i18n().t('reader.load_error')}: {e}", severity="error")
                    logger.error(f"{get_global_i18n().t('reader.load_error')}: {str(e)}", exc_info=True)
                # 安全地回到 UI 线程
                if hasattr(self.app, "call_from_thread"):
                    self.app.call_from_thread(_on_err)
                else:
                    _on_err()
                return
            
            def _on_ok():
                # 回到 UI 线程设置内容与分页
                if not content:
                    self.notify(f"{get_global_i18n().t('reader.empty_book_content')}", severity="error")
                    self._hide_loading_animation()
                    return
                
                # 检查内容是否是错误信息（文件不存在）
                if isinstance(content, str) and content.startswith("书籍文件不存在:"):
                    self.notify(f"{get_global_i18n().t('reader.file_not_found')}: {content}", severity="error")
                    self._hide_loading_animation()
                    # 关闭阅读器屏幕，返回书架
                    self.app.pop_screen()
                    return
                
                content_len = len(content)
                logger.debug(f"{get_global_i18n().t('reader.load_book_content_len', len=content_len)}")
                
                self.renderer.set_content(content)
                self.current_page = self.renderer.current_page
                self.total_pages = self.renderer.total_pages
                logger.debug(f"{get_global_i18n().t('reader.pagenation_result', current_page=self.current_page, total_pages=self.total_pages)}")
                
                # 恢复阅读位置（如果启用了记住位置功能）
                if self.render_config.get("remember_position", True):
                    saved_page = getattr(self.book, 'current_page', 0) + 1
                    # saved_page是0-based的，如果大于0说明有保存的位置
                    if saved_page > 0 and saved_page < self.renderer.total_pages:
                        # goto_page接受1-based参数，需要转换为1-based页码
                        if saved_page <= 1:
                            saved_page = 1
                        self.renderer.goto_page(saved_page)
                        self.current_page = self.renderer.current_page  # 这是0-based的
                        logger.info(get_global_i18n().t("reader.restore_page", page=saved_page + 1, saved=saved_page, current=self.current_page))
                    else:
                        # 如果没有保存的位置或位置无效，从第一页开始
                        self.renderer.goto_page(1)  # 1-based，1表示第1页
                        self.current_page = self.renderer.current_page  # 应该是0
                        logger.info(get_global_i18n().t("reader.read_from_first", current=self.current_page))
                else:
                    # 如果不记住位置，总是从第一页开始
                    self.renderer.goto_page(1)  # 1-based，1表示第1页
                    self.current_page = self.renderer.current_page  # 应该是0
                    logger.info(get_global_i18n().t("reader.unknown_read_from_first", current=self.current_page))
                
                self._update_ui()
                self._hide_loading_animation()
            
            # 安全地回到 UI 线程
            import threading
            if hasattr(self.app, "call_from_thread") and threading.get_ident() != getattr(self.app, "_thread_id", None):
                self.app.call_from_thread(_on_ok)
            else:
                # 如果在同一个线程，直接调用
                _on_ok()
        
        # 在 UI 事件循环中启动 worker
        try:
            if hasattr(self.app, "run_worker"):
                self.app.run_worker(_worker(), exclusive=True)
            else:
                # 次优：直接在主循环创建任务
                import asyncio as _aio
                loop = getattr(self.app, "_main_loop", None)
                if loop and hasattr(loop, "call_soon_threadsafe"):
                    loop.call_soon_threadsafe(lambda: _aio.create_task(_worker()))
                else:
                    # 最后兜底：新线程启动一个事件循环来运行该协程
                    import threading, asyncio as _aio2
                    threading.Thread(target=lambda: _aio2.run(_worker()), daemon=True).start()
        except Exception as e:
            # 启动失败则回退为同步路径（尽量避免）
            logger.error(get_global_i18n().t('reader.boot_failed', error=str(e)))
            try:
                # 保持与旧实现一致
                content = self.book.get_content()
                if content:
                    self.renderer.set_content(content)
                    self.current_page = self.renderer.current_page
                    self.total_pages = self.renderer.total_pages
                    self._update_ui()
                else:
                    self.notify(f"{get_global_i18n().t('reader.empty_book_content')}", severity="error")
            except Exception as e2:
                self.notify(f"{get_global_i18n().t('reader.load_error')}: {e2}", severity="error")
                logger.error(f"{get_global_i18n().t('reader.load_error')}: {str(e2)}", exc_info=True)
            finally:
                self._hide_loading_animation()
    
    def on_resize(self, event: events.Resize) -> None:
        self._set_container_size()
    
    def on_key(self, event: events.Key) -> None:
        # 添加调试信息
        logger.debug(f"键盘事件: {event.key}")
        
        if event.key == "left":
            self._prev_page()
        elif event.key == "right":
            self._next_page()
        elif event.key == "up":
            self._scroll_up()
        elif event.key == "down":
            self._scroll_down()
        elif event.key == "g":
            # logger.info("检测到g键，调用_goto_page")
            self._goto_page()
        elif event.key == "b":
            self._toggle_bookmark()
        elif event.key == "B":
            self._open_bookmark_list()
        elif event.key == "s":
            self._open_settings()
        elif event.key == "f":
            self._search_text()
        elif event.key == "a":
            self._toggle_auto_page()
        elif event.key == "r":
            self._toggle_tts()
        elif event.key == "q" or event.key == "escape":
            self._back_to_library()
        elif event.key == "slash":
            logger.info("检测到老板键 (slash)，调用 _activate_boss_key()")
            self._activate_boss_key()
        elif event.key == "h":
            logger.info("检测到帮助键 (h)，调用 _show_help()")
            self._show_help()
        event.stop()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        # 添加调试信息
        logger.debug(get_global_i18n().t("reader.button_event", button_id=button_id))
        
        if button_id == "prev-btn":
            self._prev_page()
        elif button_id == "next-btn":
            self._next_page()
        elif button_id == "goto-btn":
            # logger.info("检测到goto-btn点击，调用_goto_page")
            self._goto_page()
        elif button_id == "search-btn":
            self._search_text()
        elif button_id == "bookmark-btn":
            self._toggle_bookmark()
        elif button_id == "bookmark-list-btn":
            self._open_bookmark_list()
        elif button_id == "settings-btn":
            self._open_settings()
        elif button_id == "aloud-btn":
            self._toggle_tts()
        elif button_id == "auto-page-btn":
            self._toggle_auto_page()
        elif button_id == "back-btn":
            self._back_to_library()
    
    def _activate_boss_key(self) -> None:
        logger.info("执行 _activate_boss_key() 方法")
        try:
            from src.ui.screens.boss_key_screen import BossKeyScreen
            logger.info("导入 BossKeyScreen 成功")
            boss_screen = BossKeyScreen(self.theme_manager)
            logger.info("创建 BossKeyScreen 实例成功")
            self.app.push_screen(boss_screen)
            logger.info("推入 BossKeyScreen 成功")
        except Exception as e:
            logger.error(f"打开老板键屏幕失败: {e}")
            self.notify(f"打开老板键屏幕失败: {e}", severity="error")

    def _show_help(self) -> None:
        """显示帮助中心"""
        try:
            from src.ui.screens.help_screen import HelpScreen
            self.app.push_screen(HelpScreen())
        except Exception as e:
            self.notify(f"打开帮助中心失败: {e}", severity="error")
    
    def _prev_page(self) -> None:
        if self.renderer.prev_page():
            # 同步页码状态
            self.current_page = self.renderer.current_page
            self.total_pages = self.renderer.total_pages
            self._on_page_change(self.current_page)
    
    def _next_page(self) -> None:
        if self.renderer.next_page():
            # 同步页码状态
            self.current_page = self.renderer.current_page
            self.total_pages = self.renderer.total_pages
            self._on_page_change(self.current_page)
    
    def _scroll_up(self, lines: int = 1) -> None:
        self.renderer.content_scroll_up(lines)
    
    def _scroll_down(self, lines: int = 1) -> None:
        self.renderer.content_scroll_down(lines)
    
    def _goto_page(self) -> None:
        # 添加调试信息
        logger.info(f"_goto_page{get_global_i18n().t('reader.on_use')}: total_pages={self.renderer.total_pages}, current_page={self.renderer.current_page}")
        
        # 检查是否有有效的页面数据
        if self.renderer.total_pages <= 1:
            # self.notify("当前书籍只有一页，无需跳转", severity="information")
            return
            
        def on_result(result: Optional[int]) -> None:
            if result is not None:
                # result 是 0-based 索引，直接传给 renderer.goto_page（它接受 1-based 参数）
                target_page = result + 1  # 转换为 1-based 页码
                if self.renderer.goto_page(target_page):
                    self.current_page = result  # 保存 0-based 页码
                    self._on_page_change(self.current_page)
                    self._update_ui()
        
        self.app.push_screen(PageDialog(self.renderer.total_pages, self.renderer.current_page), on_result)
    
    def _toggle_bookmark(self) -> None:
        try:
            current_position = str(self.renderer.current_page)
            
            # 获取当前书籍的所有书签
            bookmarks = self.bookmark_manager.get_bookmarks(self.book_id)
            
            # 检查是否已存在书签
            existing_bookmark = None
            for bookmark in bookmarks:
                if bookmark.position == current_position:
                    existing_bookmark = bookmark
                    break
            
            if existing_bookmark:
                # 删除书签
                bookmark_id = getattr(existing_bookmark, 'id', None)
                if bookmark_id and self.bookmark_manager.remove_bookmark(bookmark_id):
                    self.notify(f"{get_global_i18n().t('reader.bookmark_deleted')}", severity="information")
                else:
                    self.notify(f"{get_global_i18n().t('reader.bookmark_delete_failed')}", severity="error")
            else:
                # 添加书签
                bookmark_text = self._get_current_position_text()
                bookmark_data = {
                    "book_id": self.book_id,
                    "position": current_position,
                    "note": bookmark_text
                }
                
                def on_bookmark_dialog_result(result: Optional[Dict[str, Any]]) -> None:
                    if result:
                        try:
                            new_bookmark = Bookmark(
                                book_id=result["book_id"],
                                position=result["position"],
                                note=result.get("note", bookmark_text)
                            )
                            if self.bookmark_manager.add_bookmark(new_bookmark):
                                self.notify(f"{get_global_i18n().t('reader.bookmark_added')}", severity="information")
                            else:
                                self.notify(f"{get_global_i18n().t('reader.bookmark_add_failed')}", severity="error")
                        except Exception as e:
                            self.notify(f"{get_global_i18n().t('reader.bookmark_add_failed')}: {e}", severity="error")
                
                self.app.push_screen(BookmarkDialog(bookmark_data), on_bookmark_dialog_result)
        except Exception as e:
            self.notify(get_global_i18n().t('reader.bookmark_action_failed', error=str(e)), severity="error")
    
    def _open_bookmark_list(self) -> None:
        try:
            self.app.push_screen(BookmarksScreen(self.book_id))
        except Exception as e:
            self.notify(f"{get_global_i18n().t('reader.open_bookmark_failed')}: {e}", severity="error")
    
    def _get_current_position_text(self) -> str:
        content = self.renderer.get_current_page()
        if content:
            return content[:50].replace('\n', ' ') + "..."
        return f"{get_global_i18n().t('reader.page_current', page=self.renderer.current_page + 1)}"
    
    def _open_settings(self) -> None:
        try:
            # 保存当前页面位置
            current_page = self.current_page
            
            # 打开设置屏幕（兼容不同 App 类型，避免类型检查报错）
            try:
                _action = getattr(self.app, "action_show_settings", None)
                if callable(_action):
                    _action()
                else:
                    self.app.push_screen("settings")
            except Exception:
                self.app.push_screen("settings")
            
            # 设置一个定时器来检查设置是否已关闭
            self.set_timer(0.5, self._check_settings_closed)
        except Exception as e:
            self.notify(f"{get_global_i18n().t('reader.open_setting_failed')}: {e}", severity="error")
    
    def _check_settings_closed(self) -> None:
        # 简单的检查方法：如果当前屏幕是阅读器屏幕，说明设置已关闭
        if self.app.screen is self:
            self._reload_settings()
    
    def _reload_settings(self) -> None:
        try:
            # 重新加载配置
            new_config = self._load_render_config_from_settings()
            
            # 保存当前页面位置
            current_page = self.current_page
            
            # 更新渲染器配置
            self.renderer.update_config(new_config)
            self.render_config = new_config
            
            # 同步状态到屏幕组件
            self.current_page = self.renderer.current_page
            self.total_pages = self.renderer.total_pages
            
            # 更新状态管理器
            if hasattr(self, 'status_manager') and self.status_manager:
                self.status_manager.total_pages = self.total_pages
                self.status_manager.update_reading_position(self.current_page)
            
            # 更新其他组件配置
            if hasattr(self.controls, 'update_config'):
                self.controls.update_config(new_config)
            # status_manager 可能没有 update_config 方法，跳过
            
            # 更新界面
            self._update_ui()
            
            logger.info(get_global_i18n().t("reader.setting_reloaded"))
            logger.debug(f"设置重载后: 当前页={self.current_page}, 总页数={self.total_pages}")
            self.notify(f"{get_global_i18n().t('reader.setting_effected')}", severity="information")
            
        except Exception as e:
            logger.error(f"{get_global_i18n().t('reader.setting_reload_failed')}: {e}")
            self.notify(f"{get_global_i18n().t('reader.setting_effect_failed')}: {e}", severity="error")
    
    def _search_text(self) -> None:
        def on_search(search_keyword: Optional[str]) -> None:
            if search_keyword and search_keyword.strip():
                try:
                    # 直接在 UI 线程显示加载动画
                    self._show_loading_animation(get_global_i18n().t("reader.searching"))
                    
                    # 获取当前小说的完整内容进行搜索
                    full_content = self.book.get_content()
                    if not full_content:
                        self.notify(f"{get_global_i18n().t('reader.cannot_get_content')}", severity="error")
                        self._hide_loading_animation()
                        return
                    
                    # 在当前内容中搜索
                    search_results = []
                    import re
                    pattern = re.compile(re.escape(search_keyword), re.IGNORECASE)
                    
                    for match in pattern.finditer(full_content):
                        start_pos = max(0, match.start() - 50)
                        end_pos = min(len(full_content), match.end() + 50)
                        context = full_content[start_pos:end_pos]
                        
                        # 估算页码
                        avg_page_length = len(full_content) / self.renderer.total_pages if self.renderer.total_pages > 0 else 1000
                        estimated_page = min(self.renderer.total_pages, max(1, int(match.start() / avg_page_length) + 1))
                        
                        search_results.append({
                            'page': estimated_page,
                            'position': match.start(),
                            'preview': context,
                            'match_text': match.group()
                        })
                    
                    # 隐藏加载动画
                    self._hide_loading_animation()
                    
                    if search_results:
                        self.app.push_screen(SearchResultsScreen(search_keyword, search_results, self.theme_manager, self.renderer))
                    else:
                        self.notify(f"{get_global_i18n().t('reader.no_match')}", severity="warning")
                except Exception as e:
                    # 隐藏加载动画
                    self._hide_loading_animation()
                    self.notify(f"{get_global_i18n().t('reader.search_failed')}: {e}", severity="error")
        
        self.app.push_screen(ContentSearchDialog(self.theme_manager), on_search)
    
    def _toggle_auto_page(self) -> None:
        self.auto_turn_enabled = not self.auto_turn_enabled
        
        if self.auto_turn_enabled:
            self._start_auto_turn()
            self.notify(f"{get_global_i18n().t('reader.auto_page_enabled')}", severity="information")
        else:
            self._stop_auto_turn()
            self.notify(f"{get_global_i18n().t('reader.auto_page_disabled')}", severity="information")
    
    def _start_auto_turn(self) -> None:
        if self.auto_turn_timer:
            self.auto_turn_timer.stop()
        
        interval = self.render_config.get("auto_page_turn_interval", 30)
        interval_float = float(interval) if isinstance(interval, (int, float, str)) else 30.0
        self.auto_turn_timer = self.set_interval(interval_float, self._auto_turn_page)
    
    def _stop_auto_turn(self) -> None:
        if self.auto_turn_timer:
            self.auto_turn_timer.stop()
            self.auto_turn_timer = None
    
    def _auto_turn_page(self) -> None:
        if not self.renderer.next_page():
            self.auto_turn_enabled = False
            self._stop_auto_turn()
            self.notify(f"{get_global_i18n().t('reader.already_last_auto_stop')}", severity="information")
        else:
            self.current_page = self.renderer.current_page
            self._on_page_change(self.current_page)
    
    def _toggle_tts(self) -> None:
        self.tts_enabled = not self.tts_enabled
        
        if self.tts_enabled:
            self._start_tts()
            self.notify(f"{get_global_i18n().t('reader.aloud_enabled')}", severity="information")
        else:
            self._stop_tts()
            self.notify(f"{get_global_i18n().t('reader.aloud_disabled')}", severity="information")
    
    def _start_tts(self) -> None:
        try:
            # 获取朗读音量设置
            from src.config.settings.setting_registry import SettingRegistry
            setting_registry = SettingRegistry()
            tts_volume = setting_registry.get_value("reader.tts_volume", 50)
            
            content = self.renderer.get_current_page()
            if content:
                # 将音量设置转换为语速（0.5-2.0范围）
                rate = 0.5 + (tts_volume / 100) * 1.5
                self.tts_manager.speak(content, rate=rate)
        except Exception as e:
            self.notify(f"{get_global_i18n().t('reader.aloud_start_failed')}: {e}", severity="error")
            self.tts_enabled = False
    
    def _stop_tts(self) -> None:
        try:
            self.tts_manager.stop()
        except Exception as e:
            logger.error(f"{get_global_i18n().t('reader.aloud_stop_failed')}: {e}")
    
    def _on_page_change(self, new_page: int) -> None:
        # 更新状态，确保与renderer同步
        self.current_page = self.renderer.current_page
        self.total_pages = self.renderer.total_pages
        
        # 更新状态管理器
        if hasattr(self, 'status_manager') and self.status_manager:
            self.status_manager.update_reading_position(self.current_page)
            
        # 更新界面
        self._update_ui()
        self._update_book_progress()
    
    def _on_auto_turn_change(self, auto_turn: bool) -> None:
        self.auto_turn_enabled = auto_turn
    
    def _on_config_change(self, new_config: Dict[str, Any]) -> None:
        self.render_config = new_config
        self.renderer.config = self.render_config
        self.renderer._paginate()
        self.renderer.update_content()
    
    def _update_book_progress(self) -> None:
        # 只有在启用了记住阅读位置功能时才更新进度
        if self.render_config.get("remember_position", True):
            self.book.update_reading_progress(
                position=self.renderer.current_page,
                page=self.renderer.current_page,
                total_pages=self.renderer.total_pages
            )
        
        # 记录阅读时间（每次更新进度时记录）
        if hasattr(self, 'last_progress_update'):
            current_time = time.time()
            reading_duration = int(current_time - self.last_progress_update)
            if reading_duration > 0:
                # 添加阅读记录到书架（显式命名参数，避免类型检查报错）
                if self.bookshelf:
                    try:
                        self.bookshelf.add_reading_record(
                            book=self.book,
                            duration=reading_duration,
                            pages_read=1
                        )
                        logger.debug(f"记录翻页阅读: {reading_duration}秒")
                    except Exception as e:
                        logger.error(f"记录翻页阅读失败: {e}")
                else:
                    logger.debug("bookshelf对象为None，跳过翻页阅读记录")
        
        self.last_progress_update = time.time()
    
    def _update_ui(self) -> None:
        # 更新标题栏
        try:
            header = self.query_one("#header", Static)
            book_title = getattr(self.book, 'title', get_global_i18n().t('reader.unknow_book'))
            progress = 0
            if self.renderer.total_pages > 0:
                # 修复进度计算：renderer.current_page是从0开始的，所以需要+1
                # 当在最后一页时，进度应该是100%
                progress = ((self.renderer.current_page + 1) / self.renderer.total_pages) * 100
                # 确保进度不超过100%
                progress = min(progress, 100.0)
            
            # 根据进度条样式设置显示不同格式
            progress_display = self._format_progress_display(progress)
            header.update(f"📖 {book_title} - {progress_display}")
        except Exception:
            pass
        
        # 更新状态栏 - 添加更安全的查询方式
        try:
            # 先检查状态栏是否存在
            status_widgets = self.query("#reader-status")
            if not status_widgets:
                logger.warning("状态栏元素未找到，可能尚未渲染完成")
                return
                
            status = self.query_one("#reader-status", Static)
            
            # 调试信息：检查分页值
            logger.debug(f"状态栏更新: current_page={self.current_page}, total_pages={self.total_pages}, renderer.current_page={self.renderer.current_page}, renderer.total_pages={self.renderer.total_pages}")
            
            # 检查是否启用统计功能
            from src.config.settings.setting_registry import SettingRegistry
            setting_registry = SettingRegistry()
            statistics_enabled = setting_registry.get_value("advanced.statistics_enabled", True)
            
            if statistics_enabled:
                # 显示统计信息
                stats = self.status_manager.get_statistics()
                status_text = f"第{self.renderer.current_page + 1}/{self.renderer.total_pages}页 "
                status.update(status_text)
            else:
                # 统计功能关闭，只显示基本页面信息
                status_text = f"第{self.renderer.current_page + 1}/{self.renderer.total_pages}页 (统计已关闭)"
                status.update(status_text)
        except Exception as e:
            logger.error(f"更新状态栏失败: {e}")
            pass
        
        # 更新按钮状态
        try:
            prev_btn = self.query_one("#prev-btn", Button)
            prev_btn.disabled = self.renderer.current_page <= 0
            
            next_btn = self.query_one("#next-btn", Button)
            next_btn.disabled = self.renderer.current_page >= self.renderer.total_pages - 1
        except Exception:
            pass
    
    def _format_progress_display(self, progress: float) -> str:
        try:
            # 获取进度条样式设置
            from src.config.settings.setting_registry import SettingRegistry
            setting_registry = SettingRegistry()
            progress_style = setting_registry.get_value("appearance.progress_bar_style", "bar")
            
            if progress_style == "percentage":
                # 仅显示百分比
                return f"{progress:.1f}%"
            elif progress_style == "bar":
                # 显示进度条
                bar_width = 20
                filled = int((progress / 100) * bar_width)
                empty = bar_width - filled
                bar = "█" * filled + "░" * empty
                return f"[{bar}]"
            elif progress_style == "both":
                # 显示进度条和百分比
                bar_width = 15
                filled = int((progress / 100) * bar_width)
                empty = bar_width - filled
                bar = "█" * filled + "░" * empty
                return f"[{bar}] {progress:.1f}%"
            else:
                # 默认显示百分比
                return f"{progress:.1f}%"
                
        except Exception as e:
            logger.error(f"{get_global_i18n().t('reader.format_progress_failed')}: {e}")
            # 出错时返回默认格式
            return f"{progress:.1f}%"
    
    def _back_to_library(self) -> None:
        # 停止阅读会话
        stats = self.status_manager.stop_reading()
        
        # 记录阅读统计和进度
        if stats:
            reading_duration = stats.get("session_time", 0)
            logger.info(get_global_i18n().t('reader.reading_seconds').format(duration=reading_duration))
            
            # 记录阅读数据到数据库
            if self.book and reading_duration > 0:  # 记录所有阅读会话，即使很短
                try:
                    pages_read = max(1, self.current_page - getattr(self, 'initial_page', 1))
                    if self.bookshelf:
                        self.bookshelf.add_reading_record(
                            book=self.book,
                            duration=reading_duration,
                            pages_read=pages_read
                        )
                        logger.info(get_global_i18n().t('reader.record_session', title=self.book.title, pages=pages_read, duration=reading_duration))
                    else:
                        logger.warning("bookshelf对象为None，无法记录阅读统计")
                except Exception as e:
                    logger.error(f"{get_global_i18n().t('reader.record_data_failed')}: {e}")
        
        # 保存当前阅读进度
        if self.book:
            self.book.update_reading_progress(
                position=self.current_page * 1000,  # 估算字符位置
                page=self.current_page,
                total_pages=getattr(self.renderer, 'total_pages', 1)
            )
            # 保存到数据库
            try:
                if self.bookshelf:
                    self.bookshelf.save()
                    
                logger.info(get_global_i18n().t('reader.record_progress', title=self.book.title, page=self.current_page, total=getattr(self.renderer, 'total_pages', 1), progress=f"{self.book.reading_progress:.1%}"))
            except Exception as e:
                logger.error(f"{get_global_i18n().t('reader.record_progress_failed')}: {e}")
        
        # 取消注册设置观察者
        self._unregister_setting_observers()
        
        # 移除全面的样式隔离
        remove_comprehensive_style_isolation(self)
        
        # 发送刷新书架消息
        from src.ui.messages import RefreshBookshelfMessage
        self.app.post_message(RefreshBookshelfMessage())
        
        # 返回书架
        self.app.pop_screen()
    
    def _apply_theme_styles_to_css(self) -> None:
        """根据当前主题注入CSS变量与强制规则，确保内容字体颜色生效"""
        try:
            tm = self.theme_manager
            # 获取文字颜色（优先 reader.text，其次 content.text）
            text_style = tm.get_style("reader.text") or tm.get_style("content.text")
            text_color = str(getattr(text_style, "color", "")) if text_style else ""
            # 背景与面板
            bg_style = tm.get_style("ui.background")
            bg_color = str(getattr(bg_style, "bgcolor", "")) if bg_style else ""
            surface_style = tm.get_style("ui.panel")
            surface_color = str(getattr(surface_style, "bgcolor", "")) if surface_style else ""
            # 主色与强调色
            primary_style = tm.get_style("app.accent")
            primary_color = str(getattr(primary_style, "color", "")) if primary_style else ""
            accent_style = tm.get_style("app.highlight")
            accent_color = str(getattr(accent_style, "color", "")) if accent_style else ""
            
            # 合理兜底（根据 app.dark 判断）
            is_dark = bool(getattr(self.app, "dark", False))
            text_fallback = "#ffffff" if is_dark else "#000000"
            bg_fallback = "#000000" if is_dark else "#ffffff"
            
            def pick(val: str, default: str) -> str:
                return val if val else default
            
            css = f"""
:root {{
  --text: {pick(text_color, text_fallback)};
  --background: {pick(bg_color, bg_fallback)};
  --surface: {pick(surface_color, "transparent")};
  --primary: {pick(primary_color, "#3b82f6")};
  --accent: {pick(accent_color, "#f59e0b")};
}}
/* 强制阅读内容区采用主题文字颜色，避免被其他样式覆盖 */
.reader-screen #content {{
  color: var(--text) !important;
  background: var(--background);
}}
.reader-screen Static {{
  color: var(--text);
}}
"""
            if hasattr(self.app, "stylesheet") and hasattr(self.app.stylesheet, "add_source"):
                self.app.stylesheet.add_source(css)
                if hasattr(self.app, "screen_stack") and self.app.screen_stack:
                    self.app.stylesheet.update(self.app.screen_stack[-1])
        except Exception as e:
            logger.error(f"注入主题CSS变量失败: {e}")
    
    def _register_setting_observers(self) -> None:
        try:
            from src.config.settings.setting_observer import global_observer_manager, SettingObserver, SettingChangeEvent
            

            class ReaderScreenObserver(SettingObserver):
                def __init__(self, reader_screen):
                    self.reader_screen = reader_screen
                
                def on_setting_changed(self, event: SettingChangeEvent) -> None:
                    """设置变更时的回调"""
                    try:
                        logger.debug(f"ReaderScreen: {get_global_i18n().t('reader.receive_setting_change')}: {event.setting_key} = {event.new_value}")
                        
                        # 处理进度条样式变更
                        if event.setting_key == "appearance.progress_bar_style":
                            self.reader_screen._update_ui()
                            return
                        
                        # 更新渲染配置 - 对于影响分页的设置，调用完整的重载方法
                        if event.setting_key in ["reading.line_spacing", "reading.paragraph_spacing", "reading.font_size"]:
                            # 调用完整的设置重载方法，确保状态同步
                            self.reader_screen._reload_settings()
                            
                    except Exception as e:
                        logger.error(f"ReaderScreen: {get_global_i18n().t('reader.apply_change_failed')}: {e}")
            
            # 创建并注册观察者
            self._setting_observer = ReaderScreenObserver(self)
            
            # 注册监听阅读相关设置
            reading_settings = [
                "reading.line_spacing",
                "reading.paragraph_spacing", 
                "reading.font_size"
            ]
            
            for setting_key in reading_settings:
                global_observer_manager.register_observer(self._setting_observer, setting_key)
                
            logger.debug(f"ReaderScreen: {get_global_i18n().t('reader.regedited_watcher')}")
            
        except Exception as e:
            logger.error(f"{get_global_i18n().t('reader.regedite_watcher_failed')}: {e}")
    
    def _unregister_setting_observers(self) -> None:
        """取消注册设置观察者"""
        try:
            if hasattr(self, '_setting_observer'):
                from src.config.settings.setting_observer import global_observer_manager
                
                reading_settings = [
                    "reading.line_spacing",
                    "reading.paragraph_spacing", 
                    "reading.font_size"
                ]
                
                for setting_key in reading_settings:
                    global_observer_manager.unregister_observer(self._setting_observer, setting_key)
                
                logger.debug(f"ReaderScreen: {get_global_i18n().t('reader.regedite_watcher_cancel')}")
                
        except Exception as e:
            logger.error(f"{get_global_i18n().t('reader.regedite_watcher_cancel_failed')}: {e}")
    
    def _show_loading_animation(self, message: Optional[str] = None) -> None:
        """显示加载动画"""
        if message is None:
            message = get_global_i18n().t('common.on_action')
        # 确保message是字符串类型
        if message is None:
            message = "正在处理..."
        try:
            # 使用Textual集成的加载动画
            if hasattr(self, 'loading_animation') and self.loading_animation:
                self.loading_animation.show(message)
                logger.debug(f"{get_global_i18n().t('common.show_loading_animation')}: {message}")
            else:
                # 回退到全局动画管理器
                textual_animation_manager.show_default(message)
                logger.debug(f"{get_global_i18n().t('common.use_global_animation')}: {message}")
            
        except Exception as e:
            logger.error(f"{get_global_i18n().t('common.animation_failed')}: {e}")
    
    def _hide_loading_animation(self) -> None:
        """隐藏加载动画"""
        try:
            # 使用Textual集成的加载动画
            if hasattr(self, 'loading_animation') and self.loading_animation:
                self.loading_animation.hide()
                logger.debug(get_global_i18n().t('common.hide_animation'))
            else:
                # 回退到全局动画管理器
                textual_animation_manager.hide_default()
                logger.debug(get_global_i18n().t('common.hide_global_animation'))
            
        except Exception as e:
            logger.error(f"{get_global_i18n().t('common.hide_failed')}: {e}")

    def on_refresh_content_message(self, message: RefreshContentMessage) -> None:
        """处理刷新内容消息"""
        logger.info(get_global_i18n().t('common.refresh_content'))
        # 清除Book对象的缓存，强制重新解析
        self.book._content_loaded = False
        self.book._content = None
        # 重新加载内容
        self._load_book_content_async()