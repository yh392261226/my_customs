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
import logging

logger = logging.getLogger(__name__)
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
from src.ui.dialogs.translation_dialog import TranslationDialog
from src.ui.dialogs.vocabulary_dialog import VocabularyDialog
from src.ui.screens.bookmarks_screen import BookmarksScreen
from src.ui.screens.search_results_screen import SearchResultsScreen
from src.utils.text_to_speech import TextToSpeech as TTSManager
from src.core.translation_manager import TranslationManager
from src.core.vocabulary_manager import VocabularyManager
from src.config.settings.setting_registry import SettingRegistry
from src.ui.messages import RefreshBookshelfMessage, RefreshContentMessage
from src.ui.styles.style_manager import ScreenStyleMixin
from src.ui.styles.comprehensive_style_isolation import apply_comprehensive_style_isolation, remove_comprehensive_style_isolation

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderScreen(ScreenStyleMixin, Screen[None]):
    """终端阅读器屏幕 - 简化版本"""
    CSS_PATH = "../styles/reader_overrides.tcss"

    def _ensure_page_sync(self, target_page_0: int) -> None:
        """最终强制对齐渲染页与显示内容，消除首次打开时落后一页的问题"""
        try:
            tp = int(getattr(self.renderer, "total_pages", 0) or 0)
            if tp <= 0:
                return
            t = max(0, min(int(target_page_0 or 0), tp - 1))
            # 若当前不是目标页，优先用 force_set_page(0基) 硬对齐；兜底使用 1基 goto_page
            rc = int(getattr(self.renderer, "current_page", -1))
            if rc != t:
                if hasattr(self.renderer, "force_set_page"):
                    ok = bool(self.renderer.force_set_page(t))
                    if not ok and hasattr(self.renderer, "goto_page"):
                        try:
                            self.renderer.goto_page(t + 1)
                        except Exception:
                            pass
                elif hasattr(self.renderer, "goto_page"):
                    try:
                        self.renderer.goto_page(t + 1)
                    except Exception:
                        pass
            # 显式刷新可见内容
            try:
                if hasattr(self.renderer, "_update_visible_content"):
                    self.renderer._update_visible_content()
                elif hasattr(self.renderer, "update_content"):
                    self.renderer.update_content()
            except Exception:
                pass
            # 同步状态
            try:
                self.current_page = int(getattr(self.renderer, "current_page", t))
                self.total_pages = int(getattr(self.renderer, "total_pages", tp))
            except Exception:
                pass
        except Exception:
            pass
    
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
        
        # 创建内容渲染器 - ID已在ContentRenderer构造函数中设置为"content"
        self.renderer = ContentRenderer(
            container_width=80,
            container_height=20,
            config=self.render_config,
            theme_manager=self.theme_manager
        )
        # 尺寸变化防抖与异步分页状态
        self._resize_timer = None
        self._pending_size = None
        self._pagination_in_progress = False
        # 异步分页恢复轮询定时器
        self._restore_timer = None
        # 首次恢复标记：确保不论发生几次分页，首次显示都恢复到上次阅读页
        self._initial_restore_done = False
        
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
        # 页偏移缓存（用于将字符偏移映射到当前分页的页码）
        self._page_offsets: List[int] = []
        # 每页每行的绝对偏移列表（用于页内精准定位滚动行）
        self._line_offsets_per_page: List[List[int]] = []
        # 锚点（片段+hash）用于偏移纠偏
        self._anchor_window: int = 32
        
        # 行级滚动状态
        self.can_scroll_up = False
        self.can_scroll_down = False
        
        # TTS管理器
        self.tts_manager = TTSManager()
        self.tts_enabled = False
        
        # 翻译和单词本管理器
        self.translation_manager = TranslationManager()
        # 配置翻译管理器
        try:
            self.translation_manager.configure_from_config_manager()
        except Exception as e:
            logger.error(f"配置翻译管理器失败: {e}")
            # 如果配置失败，使用默认管理器（无服务配置）
        
        self.vocabulary_manager = VocabularyManager()
        
        # 选词状态
        self.selected_text = ""
        self.selection_start = None
        self.selection_end = None

        # 划词模式状态（键盘选择，扩展列级）
        self.selection_mode = False
        self._cursor_line = 0  # 当前页内的光标行索引
        self._cursor_col = 0   # 当前行内的列索引（字符级）
        self._selection_anchor_line = None  # 锚点行
        self._selection_anchor_col = None   # 锚点列
        
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
        
        # 内容区域 - 使用已设置的ID
        yield self.renderer
        
        # 按钮区域 - 使用HorizontalScroll实现水平滚动
        from textual.containers import HorizontalScroll
        with HorizontalScroll(id="reader-buttons-container"):
            with Horizontal(id="reader-buttons", classes="btn-row"):
                yield Button(f"{get_global_i18n().t('reader.prev_chapter')}【←】", classes="btn", id="prev-btn")
                yield Button(f"{get_global_i18n().t('reader.next_chapter')}【→】", classes="btn", id="next-btn")
                yield Button(f"{get_global_i18n().t('reader.goto_page')}【g】", classes="btn", id="goto-btn")
                yield Button(f"{get_global_i18n().t('reader.search')}【f】", classes="btn", id="search-btn")
                yield Button(f"{get_global_i18n().t('reader.add_remove_bookmark')}【b】", classes="btn", id="bookmark-btn")
                yield Button(f"{get_global_i18n().t('reader.bookmark_list')}【B】", classes="btn", id="bookmark-list-btn")
                yield Button(f"{get_global_i18n().t('reader.translation')}【l】", classes="btn", id="translation-btn")
                yield Button(f"{get_global_i18n().t('reader.vocabulary')}【w】", classes="btn", id="vocabulary-btn")
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
        
        # 应用主题样式到CSS
        self._apply_theme_styles_to_css()
        
        # 强制应用ContentRenderer的主题样式
        if hasattr(self, 'renderer') and hasattr(self.renderer, '_apply_theme_styles'):
            self.renderer._apply_theme_styles()
        
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
        # 不要在 on_mount 提前持久化，待分页与位置恢复完成后再写入
        self.last_progress_update = time.time()
        
        # 更新界面
        self._update_ui()
    
    def _normalize_text(self, s: str) -> str:
        """规范化文本：换行/制表/空白压缩/Unicode归一，提升匹配稳定性"""
        try:
            import unicodedata, re
            s = s.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
            s = unicodedata.normalize("NFC", s)
            # 压缩多空白为单空格，但保留换行以避免跨段过度粘连
            s = re.sub(r"[ \t\f\v]+", " ", s)
            return s
        except Exception:
            return s

    def _calc_anchor(self, original: str, offset: int) -> tuple[str, str]:
        """从原文offset附近提取锚点片段与hash"""
        try:
            import hashlib
            n = len(original)
            off = max(0, min(int(offset or 0), n))
            win = int(getattr(self, "_anchor_window", 32) or 32)
            start = max(0, off - win)
            end = min(n, off + win)
            raw = original[start:end]
            norm = self._normalize_text(raw)
            h = hashlib.sha1(norm.encode("utf-8", errors="ignore")).hexdigest()
            return norm, h
        except Exception:
            return "", ""

    def _rehydrate_offset_from_anchor(self, anchor_text: str, anchor_hash: str, original: str, approx_offset: int = 0) -> int | None:
        """基于锚点在原文中重新定位offset；先在近邻窗口找，找不到再全局兜底"""
        try:
            if not anchor_text:
                return None
            norm_original = self._normalize_text(original)
            norm_anchor = self._normalize_text(anchor_text)
            # 近邻窗口搜索：以approx_offset为中心
            n = len(original)
            if approx_offset and n > 0:
                win = max(2048, self._anchor_window * 64)
                left = max(0, approx_offset - win)
                right = min(n, approx_offset + win)
                sub = norm_original[left:right]
                idx = sub.find(norm_anchor)
                if idx != -1:
                    return left + idx
            # 全局兜底
            idx = norm_original.find(norm_anchor)
            if idx != -1:
                return idx
            return None
        except Exception:
            return None

    def _build_page_offsets(self) -> None:
        """更稳健的页偏移构建：近邻窗口多级匹配，降低偏移漂移"""
        try:
            pages = getattr(self.renderer, "all_pages", None)
            if not pages:
                self._page_offsets = []
                self._line_offsets_per_page = []
                return
            # 获取原文内容
            try:
                original = getattr(self.renderer, "_original_content", "") or ""
                if not original and hasattr(self.book, "get_content"):
                    original = self.book.get_content() or ""
            except Exception:
                original = getattr(self.renderer, "_original_content", "") or ""
            n = len(original)

            import re

            def _collapse_ws(s: str) -> str:
                return re.sub(r"[ \t\f\v]+", " ", s.strip()) if s else s

            def _search_line_near(original_s: str, ptr: int, line_s: str) -> int:
                """在原文 ptr 附近的窗口内搜索 line，返回匹配到的原文起始索引，找不到返回 -1"""
                if not line_s:
                    return ptr
                # 近邻窗口范围（左右不对称，右侧更大以顺序前进）
                left = max(0, ptr - 256)
                right = min(n, ptr + 8192)
                window = original_s[left:right]

                # 1) exact 寻找
                idx = window.find(line_s)
                if idx != -1:
                    return left + idx

                # 2) 空白不敏感：将 line 中连续空白收敛为 \s+ 构造正则
                ln = _collapse_ws(line_s)
                if ln:
                    # 将连续空白替换为 \s+，转义其他字符
                    pattern = re.escape(ln)
                    pattern = re.sub(r"\\\s+", r"\\s+", pattern)
                    try:
                        m = re.search(pattern, window, flags=re.IGNORECASE)
                        if m:
                            return left + m.start()
                    except Exception:
                        pass

                # 3) 指纹匹配：取去空白后的中段指纹
                core = re.sub(r"\s+", "", line_s)
                if core:
                    L = len(core)
                    seg = core[max(0, L // 2 - 12): min(L, L // 2 + 12)]
                    if seg:
                        pos = window.find(seg)
                        if pos != -1:
                            # 近似对齐：按指纹定位后回退一小段，避免跳太远
                            return left + max(0, pos - 8)

                return -1

            offsets: List[int] = []
            line_offsets_per_page: List[List[int]] = []
            pointer = 0
            for page_lines in pages:
                offsets.append(max(0, min(pointer, n)))
                page_line_offsets: List[int] = []
                if not page_lines:
                    line_offsets_per_page.append(page_line_offsets)
                    continue
                for line in page_lines:
                    # 记录该行开始偏移（先用当前指针，命中后会被“下一行开始”校正）
                    page_line_offsets.append(max(0, min(pointer, n)))
                    if not line:
                        # 空行：仅当当前是换行推进一格
                        if pointer < n and original[pointer:pointer + 1] == "\n":
                            pointer += 1
                        continue

                    hit = _search_line_near(original, pointer, line)
                    if hit != -1:
                        pointer = hit + len(line)
                    else:
                        # 找不到时，小步前进，避免一次性大漂移
                        step = max(1, min(8, len(line) // 4))
                        pointer = min(n, pointer + step)
                        logger.debug(f"_build_page_offsets: 未在原文匹配到行，容错小步推进 step={step}, ptr={pointer}")

                # 规范化行起始偏移
                page_line_offsets = [max(0, min(off, n)) for off in page_line_offsets]
                line_offsets_per_page.append(page_line_offsets)

            # 页起始偏移
            self._page_offsets = [max(0, min(off, n)) for off in offsets]
            self._line_offsets_per_page = line_offsets_per_page
        except Exception as e:
            logger.error(f"构建页偏移失败: {e}")
            self._page_offsets = []
            self._line_offsets_per_page = []
    
    def _find_page_for_offset(self, offset: int) -> int:
        """根据字符偏移在当前分页中定位页码（0-based），找不到时返回0"""
        if not self._page_offsets:
            return 0
        import bisect
        idx = bisect.bisect_right(self._page_offsets, max(0, int(offset))) - 1
        idx = max(0, idx)
        if self.renderer and hasattr(self.renderer, "total_pages"):
            idx = min(idx, max(0, self.renderer.total_pages - 1))
        return idx
    
    def _current_page_offset(self) -> int:
        """获取当前可见顶行在原文中的绝对偏移（页内精准）"""
        if not self._page_offsets:
            return 0
        cp = int(getattr(self.renderer, "current_page", 0) or 0)
        if not (0 <= cp < len(self._page_offsets)):
            return 0
        # 如有页内行偏移，使用当前滚动偏移定位到行
        try:
            scroll = int(getattr(self.renderer, "_scroll_offset", 0) or 0)
            line_offsets = self._line_offsets_per_page[cp] if 0 <= cp < len(self._line_offsets_per_page) else None
            if line_offsets and 0 <= scroll < len(line_offsets):
                return line_offsets[scroll]
        except Exception:
            pass
        return self._page_offsets[cp]
    
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
        
        # 重建页偏移缓存（尺寸变化已触发重新分页）
        self._build_page_offsets()
        
        # 同步状态
        self.current_page = self.renderer.current_page
        self.total_pages = self.renderer.total_pages
        
        # 若尚未进行首次恢复，且启用了记忆位置与分页就绪，则优先恢复到上次页码
        try:
            if (not getattr(self, "_initial_restore_done", False)) and self.render_config.get("remember_position", True) and int(getattr(self.renderer, "total_pages", 0)) > 0:
                # 1) 优先使用保存的页码（0-based）
                try:
                    legacy_saved_page_0 = max(int(getattr(self.book, "current_page", 0) or 0) - 1, 0)
                except Exception:
                    legacy_saved_page_0 = 0
                restored = False
                if 0 <= legacy_saved_page_0 < int(getattr(self.renderer, "total_pages", 0)):
                    display = min(legacy_saved_page_0, self.renderer.total_pages - 1)
                    ok = bool(self.renderer.goto_page(display + 1))
                    if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(display):
                        try:
                            self.renderer.goto_page(display + 1)
                        except Exception:
                            pass
                        if hasattr(self.renderer, "force_set_page"):
                            try:
                                self.renderer.force_set_page(display)
                            except Exception:
                                pass
                    # 确保内容刷新与页码一致
                    try:
                        if hasattr(self.renderer, "_update_visible_content"):
                            self.renderer._update_visible_content()
                    except Exception:
                        pass
                    self.current_page = int(getattr(self.renderer, "current_page", display))
                    # 最终强制对齐（0基）
                    try:
                        self._ensure_page_sync(display)
                    except Exception:
                        pass
                    restored = True
                # 2) 其次使用绝对偏移映射到页码
                if not restored:
                    saved_offset = int(getattr(self.book, "current_position", 0) or 0)
                    if saved_offset > 0:
                        target_page_0 = min(self._find_page_for_offset(saved_offset), self.renderer.total_pages - 1)
                        ok = bool(self.renderer.goto_page(target_page_0 + 1))
                        if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(target_page_0):
                            try:
                                self.renderer.goto_page(target_page_0 + 1)
                            except Exception:
                                pass
                            if hasattr(self.renderer, "force_set_page"):
                                try:
                                    self.renderer.force_set_page(target_page_0)
                                except Exception:
                                    pass
                        # 确保内容刷新与页码一致
                        try:
                            if hasattr(self.renderer, "_update_visible_content"):
                                self.renderer._update_visible_content()
                        except Exception:
                            pass
                        self.current_page = int(getattr(self.renderer, "current_page", target_page_0))
                        # 最终强制对齐（0基）
                        try:
                            self._ensure_page_sync(target_page_0)
                        except Exception:
                            pass
                # 置位首次恢复标记
                self._initial_restore_done = True
        except Exception:
            pass
        
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
                
                # 优先使用异步分页，避免阻塞UI
                triggered_async = False
                if hasattr(self.renderer, "async_paginate_and_render"):
                    try:
                        # 显示加载动画以指示后台分页
                        self._show_loading_animation(get_global_i18n().t('reader.pagenation_async'))
                        import asyncio as _aio
                        triggered_async = True
                        coro = self.renderer.async_paginate_and_render(content)
                        if hasattr(self.app, "run_worker"):
                            self.app.run_worker(coro, exclusive=False)
                        else:
                            loop = getattr(self.app, "_main_loop", None)
                            if loop and hasattr(loop, "call_soon_threadsafe"):
                                loop.call_soon_threadsafe(lambda: _aio.create_task(coro))
                            else:
                                import threading, asyncio as _aio2
                                threading.Thread(target=lambda: _aio2.run(coro), daemon=True).start()
                    except Exception:
                        # 回退同步
                        self.renderer.set_content(content)
                else:
                    self.renderer.set_content(content)
                # 如果已启动异步分页，先结束回到等待刷新消息或轮询恢复
                if triggered_async:
                    # 开启轮询：分页就绪后自动恢复位置并持久化
                    try:
                        if getattr(self, "_restore_timer", None):
                            self._restore_timer.stop()
                        self._restore_timer = self.set_interval(0.2, self._poll_restore_ready)
                    except Exception:
                        pass
                    self._update_ui()
                    return
                self.current_page = self.renderer.current_page
                self.total_pages = self.renderer.total_pages
                logger.debug(f"{get_global_i18n().t('reader.pagenation_result', current_page=self.current_page, total_pages=self.total_pages)}")
                
                # 构建页偏移缓存（用于offset到页码映射）
                self._build_page_offsets()
                
                # 恢复阅读位置：优先按锚点纠偏后的字符偏移，其次回退页码
                if self.render_config.get("remember_position", True):
                    saved_offset = int(getattr(self.book, "current_position", 0) or 0)
                    saved_anchor_text = getattr(self.book, "anchor_text", "") or ""
                    saved_anchor_hash = getattr(self.book, "anchor_hash", "") or ""
                    # 优先使用保存的页码（0-based）
                    try:
                        legacy_saved_page_0 = max(int(getattr(self.book, "current_page", 0) or 0) - 1, 0)
                    except Exception:
                        legacy_saved_page_0 = 0
                    if 0 <= legacy_saved_page_0 < self.renderer.total_pages:
                        display = min(legacy_saved_page_0, self.renderer.total_pages - 1)
                        ok = bool(self.renderer.goto_page(display + 1))
                        if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(display):
                            try:
                                self.renderer.goto_page(display + 1)
                            except Exception:
                                pass
                            if hasattr(self.renderer, "force_set_page"):
                                try:
                                    self.renderer.force_set_page(display)
                                except Exception:
                                    pass
                        # 确保内容刷新与页码一致
                        try:
                            if hasattr(self.renderer, "_update_visible_content"):
                                self.renderer._update_visible_content()
                        except Exception:
                            pass
                        self.current_page = int(getattr(self.renderer, "current_page", display))
                        # 最终强制对齐（0基）
                        try:
                            self._ensure_page_sync(display)
                        except Exception:
                            pass
                        # 页码优先恢复完成，更新UI后直接返回
                        try:
                            self._update_ui()
                        except Exception:
                            pass
                        return
                    # 优先使用保存的页码（0-based），可直接恢复并提前返回
                    try:
                        legacy_saved_page_0 = max(int(getattr(self.book, "current_page", 0) or 0) - 1, 0)
                    except Exception:
                        legacy_saved_page_0 = 0
                    if 0 <= legacy_saved_page_0 < getattr(self.renderer, "total_pages", 0):
                        display = min(legacy_saved_page_0, self.renderer.total_pages - 1)
                        ok = bool(self.renderer.goto_page(display + 1))
                        if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(display):
                            try:
                                self.renderer.goto_page(display + 1)
                            except Exception:
                                pass
                            if hasattr(self.renderer, "force_set_page"):
                                try:
                                    self.renderer.force_set_page(display)
                                except Exception:
                                    pass
                        # 确保内容刷新与页码一致
                        try:
                            if hasattr(self.renderer, "_update_visible_content"):
                                self.renderer._update_visible_content()
                        except Exception:
                            pass
                        self.current_page = int(getattr(self.renderer, "current_page", display))
                        # 最终强制对齐（0基）
                        try:
                            self._ensure_page_sync(display)
                        except Exception:
                            pass
                        # 页码优先恢复完成，更新UI并返回
                        try:
                            self._update_ui()
                        except Exception:
                            pass
                        return
                    corrected = None
                    try:
                        original = getattr(self.renderer, "_original_content", "") or (self.book.get_content() if hasattr(self.book, "get_content") else "")
                        if original:
                            # 先用锚点重建；若无锚点则用approx直接映射
                            if saved_anchor_text:
                                corrected = self._rehydrate_offset_from_anchor(saved_anchor_text, saved_anchor_hash, original, approx_offset=saved_offset or 0)
                    except Exception as _e:
                        logger.debug(f"获取原文用于锚点重建失败: {_e}")
                        corrected = None

                    use_offset = corrected if (isinstance(corrected, int) and corrected >= 0) else saved_offset
                    if use_offset > 0 and self.renderer.total_pages > 0:
                        target_page_0 = self._find_page_for_offset(use_offset)
                        # 再打开同一本书时，按需求跳到“上次页面的下一页”（不超过最后一页）
                        # 直接按 0 基页码跳转
                        if self.renderer.total_pages > 0:
                            target_page_0 = min(target_page_0, self.renderer.total_pages - 1)
                        # 先尝试 0-based
                    ok = bool(self.renderer.goto_page(target_page_0 + 1))
                    if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(target_page_0):
                        # 兜底尝试 1-based
                        try:
                            self.renderer.goto_page(target_page_0 + 1)
                        except Exception:
                            pass
                        # 强制设置页索引，确保状态同步
                        if hasattr(self.renderer, "force_set_page"):
                            try:
                                self.renderer.force_set_page(target_page_0)
                            except Exception:
                                pass
                        self.current_page = int(getattr(self.renderer, "current_page", 0))
                        # 最终强制对齐（0基）
                        try:
                            self._ensure_page_sync(target_page_0)
                        except Exception:
                            pass
                        # 页内行定位
                        try:
                            import bisect
                            line_offsets = self._line_offsets_per_page[target_page_0] if 0 <= target_page_0 < len(self._line_offsets_per_page) else None
                            if line_offsets:
                                line_idx = bisect.bisect_right(line_offsets, use_offset) - 1
                                line_idx = max(0, min(line_idx, len(line_offsets) - 1))
                                setattr(self.renderer, "_scroll_offset", line_idx)
                                if hasattr(self.renderer, "_update_visible_content"):
                                    self.renderer._update_visible_content()
                        except Exception as _e:
                            logger.debug(f"页内行定位失败，退化为页级定位: {_e}")
                        logger.info(f"恢复阅读: offset={use_offset} (纠偏={'Yes' if corrected is not None else 'No'}), page={self.current_page+1}/{self.renderer.total_pages}")
                    else:
                        # 兼容旧数据：使用已保存页码（0-based）回退
                        legacy_saved_page_0 = int(getattr(self.book, "current_page", 0) or 0)
                        if 0 <= legacy_saved_page_0 < self.renderer.total_pages:
                            # 旧数据回退：按 0 基页码直接跳转
                            display = min(legacy_saved_page_0, self.renderer.total_pages - 1)
                            # 先尝试 0-based
                            ok = bool(self.renderer.goto_page(display))
                            if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(display):
                                # 兜底尝试 1-based
                                try:
                                    self.renderer.goto_page(display + 1)
                                except Exception:
                                    pass
                                # 强制设置页索引，确保状态同步
                                if hasattr(self.renderer, "force_set_page"):
                                    try:
                                        self.renderer.force_set_page(display)
                                    except Exception:
                                        pass
                            self.current_page = int(getattr(self.renderer, "current_page", 0))
                            # 最终强制对齐（0基）
                            try:
                                self._ensure_page_sync(display)
                            except Exception:
                                pass
                            logger.info(f"按旧页码恢复阅读(下一页): page={self.current_page+1}/{self.renderer.total_pages}")
                        else:
                            # 默认跳到第一页（0 基页码）
                            self.renderer.goto_page(1)
                            self.current_page = self.renderer.current_page
                            logger.info("无有效恢复信息，从第一页开始")

                else:
                    # 记忆位置关闭：默认跳到第一页（0 基页码）
                    self.renderer.goto_page(0)
                    self.current_page = self.renderer.current_page
                    logger.info("记忆位置关闭，从第一页开始")
                
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
                    # 优先异步分页，失败则回退同步
                    if hasattr(self.renderer, "async_paginate_and_render"):
                        try:
                            self._show_loading_animation(get_global_i18n().t('reader.pagenation_async'))
                            import asyncio as _aio
                            coro = self.renderer.async_paginate_and_render(content)
                            if hasattr(self.app, "run_worker"):
                                self.app.run_worker(coro, exclusive=False)
                            else:
                                loop = getattr(self.app, "_main_loop", None)
                                if loop and hasattr(loop, "call_soon_threadsafe"):
                                    loop.call_soon_threadsafe(lambda: _aio.create_task(coro))
                                else:
                                    import threading, asyncio as _aio2
                                    threading.Thread(target=lambda: _aio2.run(coro), daemon=True).start()
                        except Exception:
                            self.renderer.set_content(content)
                    else:
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
        # 防抖：记录最新尺寸，短延时后提交
        self._pending_size = (self.size.width, self.size.height)
        try:
            if self._resize_timer:
                self._resize_timer.stop()
        except Exception:
            pass
        self._resize_timer = self.set_timer(0.2, self._commit_resize)

    def _commit_resize(self) -> None:
        """提交窗口尺寸变化，并触发异步分页（如可用）"""
        # 应用当前尺寸计算
        try:
            self._set_container_size()
        except Exception:
            pass
        # 触发异步分页（若渲染器支持且已有内容）
        try:
            content = None
            if hasattr(self.renderer, "get_full_content"):
                content = self.renderer.get_full_content()
            if not content and hasattr(self.book, "get_content"):
                content = self.book.get_content()
            if content and hasattr(self.renderer, "async_paginate_and_render"):
                # 避免并发重复任务
                if not self._pagination_in_progress:
                    self._pagination_in_progress = True
                    self._show_loading_animation(get_global_i18n().t('reader.pagenation_async'))
                    import asyncio as _aio
                    coro = self.renderer.async_paginate_and_render(content)
                    def _done_reset():
                        self._pagination_in_progress = False
                        try:
                            self._hide_loading_animation()
                        except Exception:
                            pass
                        self._build_page_offsets()
                        self._update_ui()
                    try:
                        if hasattr(self.app, "run_worker"):
                            self.app.run_worker(coro, exclusive=False)
                            self.set_timer(0.1, _done_reset)
                        else:
                            loop = getattr(self.app, "_main_loop", None)
                            if loop and hasattr(loop, "call_soon_threadsafe"):
                                loop.call_soon_threadsafe(lambda: _aio.create_task(coro))
                                self.set_timer(0.1, _done_reset)
                            else:
                                import threading, asyncio as _aio2
                                threading.Thread(target=lambda: _aio2.run(coro), daemon=True).start()
                                self.set_timer(0.2, _done_reset)
                    except Exception:
                        # 回退：同步设置内容
                        try:
                            self.renderer.set_content(content)
                        except Exception:
                            pass
                        self._pagination_in_progress = False
                        self._hide_loading_animation()
                        self._build_page_offsets()
                        self._update_ui()
        except Exception:
            # 即使异步失败也确保界面可用
            try:
                self._hide_loading_animation()
            except Exception:
                pass
            self._build_page_offsets()
            self._update_ui()
        finally:
            self._resize_timer = None
            self._pending_size = None
    
    def on_key(self, event: events.Key) -> None:
        # 添加调试信息
        logger.debug(f"键盘事件: {event.key}")

        # 划词模式：屏蔽原有方向键行为，改为光标/选择控制
        if getattr(self, "selection_mode", False):
            # Enter：结束划词并打开翻译
            if event.key in ("enter", "return"):
                self._exit_selection_mode(open_translation=True)
                event.stop()
                return
            # ESC/Q：取消划词模式，恢复原行为
            if event.key in ("escape", "q"):
                self._exit_selection_mode(open_translation=False)
                event.stop()
                return
            # 处理方向键与Shift选择
            handled = self._handle_selection_key(event)
            if handled:
                event.stop()
                return
            # 其他按键在划词模式下默认不处理为导航
            event.stop()
            return

        # 非划词模式：新增 v 进入划词模式
        if event.key == "v":
            self._enter_selection_mode()
            event.stop()
            return

        # 原有快捷键行为
        if event.key == "left":
            self._prev_page()
        elif event.key == "right":
            self._next_page()
        elif event.key == "up":
            self._scroll_up()
        elif event.key == "down":
            self._scroll_down()
        elif event.key == "g":
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
        elif event.key == "l":
            self._translate_selected_text()
        elif event.key == "w":
            self._open_vocabulary()
        elif event.key == "q" or event.key == "escape":
            self._back_to_library()
            event.stop()
        elif event.key == "slash":
            logger.info("检测到老板键 (slash)，调用 _activate_boss_key()")
            self._activate_boss_key()
        elif event.key == "h":
            logger.info("检测到帮助键 (h)，调用 _show_help()")
            self._show_help()
        elif event.key == "ctrl+c":
            # 复制选中的文本
            self._copy_selected_text()
        event.stop()
    
    def on_mouse_down(self, event: events.MouseDown) -> None:
        """鼠标按下事件 - 开始文本选择"""
        try:
            # 检查是否点击在内容渲染器上
            if event.widget == self.renderer:
                # 计算点击位置对应的行索引
                line_index = self._get_line_index_from_mouse_position(event.x, event.y)
                if line_index is not None:
                    # 开始文本选择
                    self.renderer.start_selection(self.renderer.current_page, line_index)
                    logger.debug(f"开始文本选择: 页面={self.renderer.current_page}, 行={line_index}")
        except Exception as e:
            logger.error(f"鼠标按下事件处理失败: {e}")
    
    def on_mouse_move(self, event: events.MouseMove) -> None:
        """鼠标移动事件 - 更新文本选择"""
        try:
            if hasattr(self.renderer, '_is_selecting') and self.renderer._is_selecting:
                # 计算鼠标位置对应的行索引
                line_index = self._get_line_index_from_mouse_position(event.x, event.y)
                if line_index is not None:
                    # 更新文本选择
                    self.renderer.update_selection(self.renderer.current_page, line_index)
        except Exception as e:
            logger.error(f"鼠标移动事件处理失败: {e}")
    
    def on_mouse_up(self, event: events.MouseUp) -> None:
        """鼠标释放事件 - 结束文本选择"""
        try:
            if hasattr(self.renderer, '_is_selecting') and self.renderer._is_selecting:
                # 结束文本选择
                selected_text = self.renderer.end_selection()
                self.selected_text = selected_text
                logger.debug(f"结束文本选择: 选中文本长度={len(selected_text)}")
                
                # 如果选中了文本，显示提示
                if selected_text.strip():
                    self.notify(f"已选中文本: {selected_text[:50]}...", severity="information")
        except Exception as e:
            logger.error(f"鼠标释放事件处理失败: {e}")

    # —— 划词模式：键盘选择逻辑 ——
    def _enter_selection_mode(self) -> None:
        """进入划词模式：初始化光标行列并高亮当前字符，屏蔽原方向键行为"""
        try:
            self.selection_mode = True
            # 初始光标：当前滚动顶行 + 列为0
            try:
                self._cursor_line = int(getattr(self.renderer, "_scroll_offset", 0) or 0)
            except Exception:
                self._cursor_line = 0
            lines = getattr(self.renderer, "current_page_lines", None) or []
            self._cursor_line = max(0, min(self._cursor_line, max(0, len(lines) - 1)))
            # 初始列夹取到该行长度范围
            line_text = lines[self._cursor_line] if 0 <= self._cursor_line < len(lines) else ""
            self._cursor_col = 0
            if line_text:
                self._cursor_col = min(self._cursor_col, max(0, len(line_text) - 1))
            else:
                self._cursor_col = 0

            # 单点高亮（插入符）：锚点=当前行列
            page = int(getattr(self.renderer, "current_page", 0) or 0)
            self._selection_anchor_line = self._cursor_line
            self._selection_anchor_col = self._cursor_col
            if hasattr(self.renderer, "start_selection"):
                try:
                    self.renderer.start_selection(page, self._selection_anchor_line, self._selection_anchor_col)
                except Exception:
                    pass
            if hasattr(self.renderer, "update_selection"):
                try:
                    self.renderer.update_selection(page, self._cursor_line, self._cursor_col)
                except Exception:
                    pass

            self.notify(get_global_i18n().t("selection_mode.in_notify_message"), severity="information")
        except Exception as e:
            logger.error(f"进入划词模式失败: {e}")
            self.selection_mode = False

    def _exit_selection_mode(self, open_translation: bool) -> None:
        """退出划词模式；可选直接打开翻译对话框"""
        try:
            # 获取选中文本：优先以 end_selection() 结束并返回完整选区
            selected_text = ""
            try:
                if hasattr(self.renderer, "end_selection"):
                    selected_text = self.renderer.end_selection() or ""
                elif hasattr(self.renderer, "get_selected_text"):
                    selected_text = self.renderer.get_selected_text() or ""
            except Exception:
                selected_text = ""

            # 复位模式状态
            self.selection_mode = False
            self._selection_anchor_line = None
            self._selection_anchor_col = None

            # 若需要打开翻译，且确有选中文本则执行
            if open_translation and selected_text.strip():
                self.selected_text = selected_text
                self._translate_selected_text()
            else:
                # 无选区或不翻译时，确保清理选择高亮（若尚未清理）
                try:
                    if hasattr(self.renderer, "cancel_selection"):
                        self.renderer.cancel_selection()
                except Exception:
                    pass
                if open_translation:
                    # 没有选择内容也尝试打开翻译对话框（允许输入）
                    self.selected_text = ""
                    self._translate_selected_text()
            self.notify(get_global_i18n().t("selection_mode.out_notify_message"), severity="information")
        except Exception as e:
            logger.error(f"退出划词模式失败: {e}")

    def _handle_selection_key(self, event: events.Key) -> bool:
        """在划词模式下处理方向键与Shift选择（禁止跨页，字符级选择），返回是否已处理"""
        try:
            lines = getattr(self.renderer, "current_page_lines", None) or []
            page = int(getattr(self.renderer, "current_page", 0) or 0)
            last_line_idx = max(0, len(lines) - 1)

            # 强化 Shift 检测与按键规范化
            key_raw = str(getattr(event, "key", "")) or ""
            mods = set(getattr(event, "modifiers", []) or [])
            shift_held = bool(getattr(event, "shift", False)) or ("shift" in mods) or ("Shift" in mods) or key_raw.startswith("shift+")
            # 归一化方向键名（例如 "shift+right" -> "right"）
            key = key_raw.split("+")[-1] if "+" in key_raw else key_raw

            if key not in ("up", "down", "left", "right"):
                return False

            prev_line = self._cursor_line
            prev_col = self._cursor_col

            if key == "up":
                self._cursor_line = max(0, self._cursor_line - 1)
                new_line_text = lines[self._cursor_line] if 0 <= self._cursor_line < len(lines) else ""
                self._cursor_col = min(self._cursor_col, max(0, len(new_line_text) - 1)) if new_line_text else 0
            elif key == "down":
                self._cursor_line = min(last_line_idx, self._cursor_line + 1)
                new_line_text = lines[self._cursor_line] if 0 <= self._cursor_line < len(lines) else ""
                self._cursor_col = min(self._cursor_col, max(0, len(new_line_text) - 1)) if new_line_text else 0
            elif key == "left":
                self._cursor_col = max(0, self._cursor_col - 1)
            elif key == "right":
                curr_text = lines[self._cursor_line] if 0 <= self._cursor_line < len(lines) else ""
                self._cursor_col = min(self._cursor_col + 1, max(0, len(curr_text) - 1)) if curr_text else 0

            # 滚动以保持光标行可见
            try:
                top = int(getattr(self.renderer, "_scroll_offset", 0) or 0)
                height = int(getattr(self.renderer, "container_height", 0) or 0)
                if self._cursor_line < top:
                    self.renderer.content_scroll_up(top - self._cursor_line)
                elif height > 0 and self._cursor_line >= top + height:
                    delta = self._cursor_line - (top + height) + 1
                    self.renderer.content_scroll_down(max(1, delta))
            except Exception:
                pass

            # 选择与高亮（字符级，仅当前页）
            if shift_held:
                if self._selection_anchor_line is None or self._selection_anchor_col is None:
                    self._selection_anchor_line = prev_line
                    self._selection_anchor_col = prev_col
                    if hasattr(self.renderer, "start_selection"):
                        try:
                            self.renderer.start_selection(page, self._selection_anchor_line, self._selection_anchor_col)
                        except Exception:
                            pass
                if hasattr(self.renderer, "update_selection"):
                    try:
                        self.renderer.update_selection(page, self._cursor_line, self._cursor_col)
                    except Exception:
                        pass
            else:
                self._selection_anchor_line = self._cursor_line
                self._selection_anchor_col = self._cursor_col
                if hasattr(self.renderer, "start_selection"):
                    try:
                        self.renderer.start_selection(page, self._selection_anchor_line, self._selection_anchor_col)
                    except Exception:
                        pass
                if hasattr(self.renderer, "update_selection"):
                    try:
                        self.renderer.update_selection(page, self._cursor_line, self._cursor_col)
                    except Exception:
                        pass

            return True
        except Exception as e:
            logger.error(f"划词模式方向键处理失败: {e}")
            return False
    
    def _get_line_index_from_mouse_position(self, x: int, y: int) -> Optional[int]:
        """根据鼠标位置计算对应的行索引"""
        try:
            # 获取内容渲染器的位置和尺寸
            renderer_widget = self.renderer
            renderer_x = renderer_widget.region.x
            renderer_y = renderer_widget.region.y
            renderer_height = renderer_widget.region.height
            
            # 计算相对于内容渲染器的y坐标
            relative_y = y - renderer_y
            
            # 计算行高（假设每行高度为1）
            line_height = 1
            
            # 计算行索引（考虑滚动偏移）
            line_index = int(relative_y / line_height) + self.renderer._scroll_offset
            
            # 确保行索引在有效范围内
            if 0 <= line_index < len(self.renderer.current_page_lines):
                return line_index
            else:
                return None
                
        except Exception as e:
            logger.error(f"计算鼠标位置对应的行索引失败: {e}")
            return None
    
    def _copy_selected_text(self) -> None:
        """复制选中的文本到剪贴板"""
        try:
            if hasattr(self.renderer, 'get_selected_text') and self.renderer.has_selection():
                selected_text = self.renderer.get_selected_text()
                if selected_text.strip():
                    # 尝试复制到系统剪贴板
                    import pyperclip
                    pyperclip.copy(selected_text)
                    self.notify(get_global_i18n().t("selection_mode.copied_selection"), severity="information")
                else:
                    self.notify(get_global_i18n().t("selection_mode.no_selection"), severity="warning")
            else:
                self.notify(get_global_i18n().t("selection_mode.no_selection"), severity="warning")
        except ImportError:
            self.notify(get_global_i18n().t("selection_mode.cannot_copy"), severity="error")
        except Exception as e:
            self.notify(f"{get_global_i18n().t("selection_mode.copied_failed")}: {e}", severity="error")
    
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
        elif button_id == "translation-btn":
            self._translate_selected_text()
        elif button_id == "vocabulary-btn":
            self._open_vocabulary()
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
                # result 是 0-based 索引，ContentRenderer 接受 1-based，需要 +1
                target_page_1 = result + 1
                if self.renderer.goto_page(target_page_1):
                    # 与渲染器同步（0-based）
                    self.current_page = self.renderer.current_page
                    self._on_page_change(self.current_page)
                    self._update_ui()
        
        self.app.push_screen(PageDialog(self.renderer.total_pages, self.renderer.current_page), on_result)
    
    def _toggle_bookmark(self) -> None:
        try:
            # 使用绝对偏移 + 锚点作为书签位置
            current_offset = self._current_page_offset()
            # 计算锚点
            try:
                original = getattr(self.renderer, "_original_content", "") or (self.book.get_content() if hasattr(self.book, "get_content") else "")
            except Exception:
                original = getattr(self.renderer, "_original_content", "") or ""
            anchor_text, anchor_hash = ("", "")
            try:
                anchor_text, anchor_hash = self._calc_anchor(original, current_offset)
            except Exception:
                pass
            
            # 获取当前书籍的所有书签
            bookmarks = self.bookmark_manager.get_bookmarks(self.book_id)
            
            # 检查是否已存在同位置的书签（按偏移近似）
            existing_bookmark = None
            for bookmark in bookmarks:
                try:
                    # 兼容数据库中旧结构（position 可能是字符串）
                    bm_pos = int(getattr(bookmark, "position", getattr(bookmark, "position", 0)) or 0)
                except Exception:
                    bm_pos = 0
                if abs(bm_pos - current_offset) <= 2:
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
                    "position": current_offset,
                    "anchor_text": anchor_text,
                    "anchor_hash": anchor_hash,
                    "note": bookmark_text
                }
                
                def on_bookmark_dialog_result(result: Optional[Dict[str, Any]]) -> None:
                    if result:
                        try:
                            new_bookmark = Bookmark(
                                book_id=result.get("book_id", self.book_id),
                                position=int(result.get("position", current_offset) or 0),
                                note=result.get("note", bookmark_text),
                                anchor_text=result.get("anchor_text", anchor_text),
                                anchor_hash=result.get("anchor_hash", anchor_hash)
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
            # 设置变更会触发重分页，需重建页偏移缓存
            self._build_page_offsets()
            
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
            # self.notify(f"{get_global_i18n().t('reader.setting_effected')}", severity="information")
            
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
        # 分页配置变化后重建偏移缓存，确保偏移->页码映射正确
        self._build_page_offsets()
    
    def _update_book_progress(self) -> None:
        # 只有在启用了记住阅读位置功能且分页就绪时才更新进度
        if self.render_config.get("remember_position", True) and getattr(self.renderer, "total_pages", 0) > 0:
            # 计算锚点并更新
            try:
                original = getattr(self.renderer, "_original_content", "") or (self.book.get_content() if hasattr(self.book, "get_content") else "")
                anchor_text, anchor_hash = self._calc_anchor(original, self._current_page_offset())
            except Exception:
                anchor_text, anchor_hash = "", ""
            self.book.update_reading_progress(
                position=self._current_page_offset(),
                page=int(self.renderer.current_page) + 1,
                total_pages=int(self.renderer.total_pages)
            )
            # 扩展字段：动态记录锚点
            try:
                setattr(self.book, "anchor_text", anchor_text)
                setattr(self.book, "anchor_hash", anchor_hash)
            except Exception:
                pass
        
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
        # 防御性同步：若屏幕状态与渲染器不一致，优先以渲染器为准
        try:
            if int(getattr(self, "current_page", -1)) != int(getattr(self.renderer, "current_page", -1)):
                self.current_page = int(getattr(self.renderer, "current_page", 0))
                self.total_pages = int(getattr(self.renderer, "total_pages", 0))
        except Exception:
            pass
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
    
    def _translate_selected_text(self) -> None:
        """翻译选中的文本，如果没有选择文本则允许用户输入"""
        try:
            # 检查是否有选中的文本
            if hasattr(self.renderer, 'get_selected_text') and self.renderer.has_selection():
                self.selected_text = self.renderer.get_selected_text()
            
            # 获取当前上下文（当前页面的内容）
            context = self.renderer.get_current_page() if hasattr(self.renderer, 'get_current_page') else ""
            
            def on_translation_result(result: Optional[Dict[str, Any]]) -> None:
                if result:
                    # 处理翻译结果
                    action = result.get('action', '')
                    translation_result = result.get('translation_result', {})
                    
                    if action == 'close' and translation_result:
                        word = result.get('original_text', self.selected_text)
                        translation = translation_result.get('translated_text', '')
                        if word and translation:
                            logger.info(f"翻译结果: {word} -> {translation}")
            
            # 如果没有选中的文本，允许用户输入要翻译的内容
            if not self.selected_text or not self.selected_text.strip():
                # 打开翻译对话框，允许用户输入文本
                self.app.push_screen(
                    TranslationDialog(
                        original_text="",  # 空文本，让用户输入
                        context=context,
                        translation_manager=self.translation_manager,
                        vocabulary_manager=self.vocabulary_manager,
                        allow_input=True,  # 允许用户输入
                        book_path=self.book.path if hasattr(self.book, 'path') else ""  # 传递书籍路径
                    ),
                    on_translation_result
                )
            else:
                # 有选中的文本，直接翻译
                self.app.push_screen(
                    TranslationDialog(
                        original_text=self.selected_text,
                        context=context,
                        translation_manager=self.translation_manager,
                        vocabulary_manager=self.vocabulary_manager,
                        book_path=self.book.path if hasattr(self.book, 'path') else ""  # 传递书籍路径
                    ),
                    on_translation_result
                )
            
        except Exception as e:
            logger.error(f"翻译选中的文本失败: {e}")
            self.notify(f"{get_global_i18n().t('selection_mode.trans_failed')}: {e}", severity="error")
    
    def _open_vocabulary(self) -> None:
        """打开单词本对话框"""
        try:
            def on_vocabulary_result(result: Optional[Dict[str, Any]]) -> None:
                if result:
                    # 处理单词本操作结果
                    action = result.get('action', '')
                    if action == 'review':
                        logger.info("开始复习单词")
            
            # 打开单词本对话框
            self.app.push_screen(
                VocabularyDialog(
                    vocabulary_manager=self.vocabulary_manager,
                    book_path=self.book.path if hasattr(self.book, 'path') else None
                ),
                on_vocabulary_result
            )
            
        except Exception as e:
            logger.error(f"打开单词本失败: {e}")
            self.notify(f"{get_global_i18n().t('selection_mode.open_failed')}: {e}", severity="error")
    
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
            # 计算锚点并更新
            try:
                original = getattr(self.renderer, "_original_content", "") or (self.book.get_content() if hasattr(self.book, "get_content") else "")
                anchor_text, anchor_hash = self._calc_anchor(original, self._current_page_offset())
            except Exception:
                anchor_text, anchor_hash = "", ""
            self.book.update_reading_progress(
                position=self._current_page_offset(),
                page=int(self.current_page) + 1,
                total_pages=int(getattr(self.renderer, 'total_pages', 1))
            )
            try:
                setattr(self.book, "anchor_text", anchor_text)
                setattr(self.book, "anchor_hash", anchor_hash)
            except Exception:
                pass
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
    
    def _get_color_string(self, color_obj) -> str:
        """
        将Rich库的Color对象转换为十六进制颜色字符串
        
        Args:
            color_obj: Rich库的Color对象或字符串
            
        Returns:
            str: 十六进制颜色字符串，如 "#FFFFFF"
        """
        if color_obj is None:
            return ""
        
        # 如果已经是字符串，直接返回
        if isinstance(color_obj, str):
            return color_obj
        
        # 如果是Rich库的Color对象，调用其get_truecolor方法
        try:
            from rich.color import Color
            if isinstance(color_obj, Color):
                # 获取RGB值并转换为十六进制
                rgb = color_obj.get_truecolor()
                if rgb:
                    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}".upper()
        except (ImportError, AttributeError):
            pass
        
        # 尝试调用str方法
        try:
            color_str = str(color_obj)
            if color_str.startswith("#") and len(color_str) in [4, 7, 9]:
                return color_str
        except:
            pass
        
        return ""
    
    def _apply_theme_styles_to_css(self) -> None:
        """根据当前主题注入阅读内容的多色位规则，让正文不再只有黑白"""
        try:
            tm = self.theme_manager

            # 基础文本与背景
            text_style = tm.get_style("reader.text") or tm.get_style("content.text")
            text_color = self._get_color_string(getattr(text_style, "color", None)) if text_style else ""

            bg_style = tm.get_style("ui.background")
            bg_color = self._get_color_string(getattr(bg_style, "bgcolor", None)) if bg_style else ""

            # 标题
            heading_style = tm.get_style("reader.chapter") or tm.get_style("content.heading") or tm.get_style("app.title")
            heading_color = self._get_color_string(getattr(heading_style, "color", None)) if heading_style else ""

            # 链接
            link_style = tm.get_style("content.link") or tm.get_style("app.accent")
            link_color = self._get_color_string(getattr(link_style, "color", None)) if link_style else ""

            # 引用
            quote_style = tm.get_style("content.quote")
            quote_color = self._get_color_string(getattr(quote_style, "color", None)) if quote_style else ""

            # 代码块（前景/背景）
            code_style = tm.get_style("content.code")
            code_fg = self._get_color_string(getattr(code_style, "color", None)) if code_style else ""
            code_bg = self._get_color_string(getattr(code_style, "bgcolor", None)) if code_style else ""
            # 兜底：若没有 code 背景，用面板/表面色
            surface_style = tm.get_style("ui.panel")
            surface_color = self._get_color_string(getattr(surface_style, "bgcolor", None)) if surface_style else ""
            if not code_bg:
                code_bg = surface_color

            # 高亮（前景/背景），优先 reader.search_result，其次 content.highlight
            hl_style = tm.get_style("reader.search_result") or tm.get_style("content.highlight")
            hl_fg = self._get_color_string(getattr(hl_style, "color", None)) if hl_style else ""
            hl_bg = self._get_color_string(getattr(hl_style, "bgcolor", None)) if hl_style else ""

            # 合理兜底（根据 app.dark 判断）
            is_dark = bool(getattr(self.app, "dark", False))
            text_fallback = "#FFFFFF" if is_dark else "#000000"
            bg_fallback = "#000000" if is_dark else "#FFFFFF"

            def pick(val: str, default: str) -> str:
                return val if val else default

            # 仅保留可用的部件/ID级规则，避免使用 HTML 标签选择器
            css = f"""
/* 基础正文与背景（作用于内容 Static 部件本身） */
.reader-screen #content {{
  color: {pick(text_color, text_fallback)} !important;
  background: {pick(bg_color, bg_fallback)};
}}

/* 作为兜底，所有 Static 默认文本色 */
.reader-screen Static {{
  color: {pick(text_color, text_fallback)};
}}
"""
            # 注入到样式表
            if hasattr(self.app, "stylesheet") and hasattr(self.app.stylesheet, "add_source"):
                self.app.stylesheet.add_source(css)
                if hasattr(self.app, "screen_stack") and self.app.screen_stack:
                    self.app.stylesheet.update(self.app.screen_stack[-1])
        except Exception as e:
            logger.error(f"注入阅读内容多色位CSS失败: {e}")
    
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
                        
                        # 处理主题变更：同步 ThemeManager、Textual 主题与样式
                        if event.setting_key == "appearance.theme":
                            new_theme = str(event.new_value) if event.new_value is not None else ""
                            tm = self.reader_screen.theme_manager
                            if new_theme:
                                try:
                                    tm.set_theme(new_theme)
                                    tm.apply_theme_to_screen(self.reader_screen)
                                    # 注入 CSS 变量，保证文本/背景颜色立即生效
                                    self.reader_screen._apply_theme_styles_to_css()
                                    # 强制内容渲染器刷新其内部样式映射
                                    if hasattr(self.reader_screen, 'renderer') and hasattr(self.reader_screen.renderer, '_apply_theme_styles'):
                                        self.reader_screen.renderer._apply_theme_styles()
                                    self.reader_screen._update_ui()
                                except Exception as e:
                                    logger.error(f"应用主题变更失败: {e}")
                            return
                        
                        # 更新渲染配置 - 对于影响分页的设置，调用完整的重载方法
                        if event.setting_key in ["reading.line_spacing", "reading.paragraph_spacing", "reading.font_size"]:
                            # 调用完整的设置重载方法，确保状态同步
                            self.reader_screen._reload_settings()
                            
                    except Exception as e:
                        logger.error(f"ReaderScreen: {get_global_i18n().t('reader.apply_change_failed')}: {e}")
            
            # 创建并注册观察者
            self._setting_observer = ReaderScreenObserver(self)
            
            # 注册监听阅读/外观相关设置
            reading_settings = [
                "reading.line_spacing",
                "reading.paragraph_spacing", 
                "reading.font_size",
                "appearance.theme",
                "appearance.progress_bar_style"
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
                    "reading.font_size",
                    "appearance.theme",
                    "appearance.progress_bar_style"
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

    def _poll_restore_ready(self) -> None:
        """异步分页就绪后尝试恢复阅读位置并停止轮询"""
        try:
            if getattr(self.renderer, "total_pages", 0) > 0:
                self._try_restore_position()
                # 置位首次恢复标记，避免重复恢复
                try:
                    self._initial_restore_done = True
                except Exception:
                    pass
                # 恢复后若状态仍不同步，强制与屏幕期望对齐
                try:
                    cp = int(getattr(self, "current_page", 0))
                    rc = int(getattr(self.renderer, "current_page", -1))
                    tp = int(getattr(self.renderer, "total_pages", 0))
                    if tp > 0 and rc != cp and hasattr(self.renderer, "force_set_page"):
                        self.renderer.force_set_page(max(0, min(cp, tp - 1)))
                        # 统一同步
                        self.current_page = int(getattr(self.renderer, "current_page", cp))
                        self.total_pages = int(getattr(self.renderer, "total_pages", tp))
                except Exception:
                    pass
                # 恢复后停止轮询
                if getattr(self, "_restore_timer", None):
                    try:
                        self._restore_timer.stop()
                    except Exception:
                        pass
                    self._restore_timer = None
                # 刷新界面
                self._update_ui()
                # 最终强制对齐（确保首次异步分页恢复后内容与页码一致）
                try:
                    tp = int(getattr(self.renderer, "total_pages", 0) or 0)
                    if tp > 0:
                        _tp1 = int(getattr(self.book, "current_page", 0) or 0)
                        target_page_0 = max(0, min(max(_tp1 - 1, 0), tp - 1))
                        self._ensure_page_sync(target_page_0)
                except Exception:
                    pass
                # 恢复完成后持久化正确进度
                try:
                    self._update_book_progress()
                    if self.bookshelf and hasattr(self.bookshelf, "db_manager"):
                        self.bookshelf.db_manager.update_book(self.book)
                except Exception as e:
                    logger.debug(f"轮询后持久化阅读进度失败: {e}")
        except Exception as e:
            logger.debug(f"轮询恢复失败: {e}")

    def _try_restore_position(self) -> None:
        """统一恢复到上次阅读位置（锚点优先，页码兜底），支持 0/1 基页码双重尝试"""
        try:
            if not self.render_config.get("remember_position", True):
                # 记忆位置关闭：默认跳到第一页（0 基）
                self.renderer.goto_page(0)
                self.current_page = self.renderer.current_page
                return

            # 构建页偏移缓存（如尚未构建）
            if not getattr(self, "_page_offsets", None):
                self._build_page_offsets()

            saved_offset = int(getattr(self.book, "current_position", 0) or 0)
            saved_anchor_text = getattr(self.book, "anchor_text", "") or ""
            saved_anchor_hash = getattr(self.book, "anchor_hash", "") or ""

            corrected = None
            try:
                original = getattr(self.renderer, "_original_content", "") or (self.book.get_content() if hasattr(self.book, "get_content") else "")
                if original and saved_anchor_text:
                    corrected = self._rehydrate_offset_from_anchor(saved_anchor_text, saved_anchor_hash, original, approx_offset=saved_offset or 0)
            except Exception as _e:
                logger.debug(f"恢复时锚点重建失败: {_e}")
                corrected = None

            use_offset = corrected if (isinstance(corrected, int) and corrected >= 0) else saved_offset

            if use_offset > 0 and getattr(self.renderer, "total_pages", 0) > 0:
                target_page_0 = self._find_page_for_offset(use_offset)
                target_page_0 = min(target_page_0, self.renderer.total_pages - 1)
                # 先尝试 0-based，再兜底 1-based
                ok = bool(self.renderer.goto_page(target_page_0 + 1))
                if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(target_page_0):
                    try:
                        self.renderer.goto_page(target_page_0 + 1)
                    except Exception:
                        pass
                    # 强制设置页索引，确保状态同步
                    if hasattr(self.renderer, "force_set_page"):
                        try:
                            self.renderer.force_set_page(target_page_0)
                        except Exception:
                            pass
                self.current_page = int(getattr(self.renderer, "current_page", 0))

                # 页内行定位（尽量定位到原偏移附近）
                try:
                    import bisect
                    line_offsets = self._line_offsets_per_page[target_page_0] if 0 <= target_page_0 < len(self._line_offsets_per_page) else None
                    if line_offsets:
                        line_idx = bisect.bisect_right(line_offsets, use_offset) - 1
                        line_idx = max(0, min(line_idx, len(line_offsets) - 1))
                        setattr(self.renderer, "_scroll_offset", line_idx)
                        if hasattr(self.renderer, "_update_visible_content"):
                            self.renderer._update_visible_content()
                except Exception as _e:
                    logger.debug(f"恢复时页内行定位失败: {_e}")
            else:
                # 兼容旧页码存储：按旧页码跳转
                legacy_saved_page_0 = int(getattr(self.book, "current_page", 0) or 0)
                if 0 <= legacy_saved_page_0 < getattr(self.renderer, "total_pages", 0):
                    display = min(legacy_saved_page_0, self.renderer.total_pages - 1)
                    ok = bool(self.renderer.goto_page(display))
                    if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(display):
                        try:
                            self.renderer.goto_page(display + 1)
                        except Exception:
                            pass
                        # 强制设置页索引，确保状态同步
                        if hasattr(self.renderer, "force_set_page"):
                            try:
                                self.renderer.force_set_page(display)
                            except Exception:
                                pass
                    self.current_page = int(getattr(self.renderer, "current_page", 0))
                    # 最终强制对齐（0基）
                    try:
                        self._ensure_page_sync(target_page_0)
                    except Exception:
                        pass
                else:
                    # 默认跳到第一页（0 基）
                    self.renderer.goto_page(1)
                    self.current_page = self.renderer.current_page

        except Exception as e:
            logger.debug(f"统一恢复位置失败: {e}")

    def on_refresh_content_message(self, message: RefreshContentMessage) -> None:
        """处理刷新内容消息：异步分页完成后恢复到上次阅读位置并刷新UI"""
        logger.info(get_global_i18n().t('common.refresh_content'))
        # 使用统一的恢复逻辑（即使未收到消息也可由轮询触发）
        # 构建偏移与同步状态在方法内部完成
        try:
            self._try_restore_position()
        except Exception as _e:
            logger.debug(f"刷新消息恢复失败: {_e}")
        try:
            # 重建页偏移
            self._build_page_offsets()
            # 同步页状态
            self.current_page = getattr(self.renderer, "current_page", self.current_page)
            self.total_pages = getattr(self.renderer, "total_pages", self.total_pages)

            # 恢复阅读位置（基于保存的绝对偏移与锚点）
            if self.render_config.get("remember_position", True):
                saved_offset = int(getattr(self.book, "current_position", 0) or 0)
                saved_anchor_text = getattr(self.book, "anchor_text", "") or ""
                saved_anchor_hash = getattr(self.book, "anchor_hash", "") or ""
                # 优先使用保存的页码（0-based）
                try:
                    legacy_saved_page_0 = max(int(getattr(self.book, "current_page", 0) or 0) - 1, 0)
                except Exception:
                    legacy_saved_page_0 = 0
                if 0 <= legacy_saved_page_0 < self.renderer.total_pages:
                    display = min(legacy_saved_page_0, self.renderer.total_pages - 1)
                    ok = bool(self.renderer.goto_page(display))
                    if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(display):
                        try:
                            self.renderer.goto_page(display + 1)
                        except Exception:
                            pass
                        if hasattr(self.renderer, "force_set_page"):
                            try:
                                self.renderer.force_set_page(display)
                            except Exception:
                                pass
                    self.current_page = int(getattr(self.renderer, "current_page", display))
                    # 页码优先恢复完成，更新UI后直接返回
                    try:
                        self._update_ui()
                    except Exception:
                        pass
                    return
                corrected = None
                try:
                    original = getattr(self.renderer, "_original_content", "") or (self.book.get_content() if hasattr(self.book, "get_content") else "")
                    if original and saved_anchor_text:
                        corrected = self._rehydrate_offset_from_anchor(saved_anchor_text, saved_anchor_hash, original, approx_offset=saved_offset or 0)
                except Exception as _e:
                    logger.debug(f"刷新时锚点重建失败: {_e}")
                    corrected = None

                use_offset = corrected if (isinstance(corrected, int) and corrected >= 0) else saved_offset
                if use_offset > 0 and self.renderer.total_pages > 0:
                    target_page_0 = self._find_page_for_offset(use_offset)
                    # 规则：跳到“上次页面的下一页”，不超过最后一页
                    # 直接按 0 基页码跳转
                    target_page_0 = min(target_page_0, self.renderer.total_pages - 1)
                    # 先尝试 0-based
                    ok = bool(self.renderer.goto_page(target_page_0))
                    if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(target_page_0):
                        # 兜底尝试 1-based
                        try:
                            self.renderer.goto_page(target_page_0 + 1)
                        except Exception:
                            pass
                        # 强制设置页索引，确保状态同步
                        if hasattr(self.renderer, "force_set_page"):
                            try:
                                self.renderer.force_set_page(target_page_0)
                            except Exception:
                                pass
                    self.current_page = int(getattr(self.renderer, "current_page", 0))
                    # 最终强制对齐（0基）
                    try:
                        self._ensure_page_sync(display)
                    except Exception:
                        pass
                    # 页内行定位（尽量定位到原偏移附近）
                    try:
                        import bisect
                        line_offsets = self._line_offsets_per_page[target_page_0] if 0 <= target_page_0 < len(self._line_offsets_per_page) else None
                        if line_offsets:
                            line_idx = bisect.bisect_right(line_offsets, use_offset) - 1
                            line_idx = max(0, min(line_idx, len(line_offsets) - 1))
                            setattr(self.renderer, "_scroll_offset", line_idx)
                            if hasattr(self.renderer, "_update_visible_content"):
                                self.renderer._update_visible_content()
                    except Exception as _e:
                        logger.debug(f"刷新时页内行定位失败: {_e}")
                else:
                    # 兼容旧页码存储：按旧页码跳转
                    legacy_saved_page_0 = int(getattr(self.book, "current_page", 0) or 0)
                    if 0 <= legacy_saved_page_0 < self.renderer.total_pages:
                        # 直接按 0 基页码跳转
                        display = min(legacy_saved_page_0, self.renderer.total_pages - 1)
                        # 先尝试 0-based
                        ok = bool(self.renderer.goto_page(display))
                        if (not ok) or int(getattr(self.renderer, "current_page", -1)) != int(display):
                            # 兜底尝试 1-based
                            try:
                                self.renderer.goto_page(display + 1)
                            except Exception:
                                pass
                            # 强制设置页索引，确保状态同步
                            if hasattr(self.renderer, "force_set_page"):
                                try:
                                    self.renderer.force_set_page(display)
                                except Exception:
                                    pass
                        self.current_page = int(getattr(self.renderer, "current_page", 0))

            # 置位首次恢复标记，避免重复恢复
            try:
                self._initial_restore_done = True
            except Exception:
                pass
            # 刷新界面
            self._update_ui()
            # 最终强制对齐（确保首次异步分页恢复后内容与页码一致）
            try:
                tp = int(getattr(self.renderer, "total_pages", 0) or 0)
                if tp > 0:
                    _tp1 = int(getattr(self.book, "current_page", 0) or 0)
                    target_page_0 = max(0, min(max(_tp1 - 1, 0), tp - 1))
                    self._ensure_page_sync(target_page_0)
            except Exception:
                pass
            # 恢复完成后再持久化正确进度
            try:
                self._update_book_progress()
                if self.bookshelf and hasattr(self.bookshelf, "db_manager"):
                    self.bookshelf.db_manager.update_book(self.book)
            except Exception as e:
                logger.debug(f"刷新后持久化阅读进度失败: {e}")
        finally:
            try:
                self._hide_loading_animation()
            except Exception:
                pass