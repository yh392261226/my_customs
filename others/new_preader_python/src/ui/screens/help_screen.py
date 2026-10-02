"""
帮助屏幕 - 自动扫描所有页面的快捷键绑定并生成分类 Markdown 帮助文档
布局采用 TabbedContent（标签页）形式，替代原先 MarkdownViewer 的左侧目录菜单。
"""


from typing import Optional, ClassVar
import time

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Header, Footer, Static, TabbedContent, TabPane, Collapsible

from src.locales.i18n_manager import get_global_i18n, t
from src.utils.logger import get_logger
from src.utils.help_generator import HelpGenerator

logger = get_logger(__name__)

# 模块级缓存：避免每次打开帮助都重新扫描
_help_cache: Optional[str] = None
_help_cache_time: float = 0.0
_help_cache_ttl: float = 300.0  # 5 分钟缓存

# 标签内容缓存
_help_tabs_cache: Optional[list[tuple[str, str]]] = None
_help_tabs_cache_time: float = 0.0


def _get_help_content(force_refresh: bool = False) -> str:
    """获取帮助内容（带缓存）"""
    global _help_cache, _help_cache_time
    now = time.time()
    if not force_refresh and _help_cache is not None and (now - _help_cache_time) < _help_cache_ttl:
        return _help_cache
    try:
        generator = HelpGenerator()
        content = generator.generate_markdown()
        _help_cache = content
        _help_cache_time = now
        return content
    except Exception as e:
        logger.error(f"自动生成帮助文档失败: {e}")
        import traceback as _tb
        logger.error(_tb.format_exc())
        # 降级：完全不依赖 i18n，确保无论如何都能显示
        return (
            "# 帮助中心\n\n"
            "## 快捷键\n\n"
            "> ⚠ 自动扫描失败，以下为基础快捷键。\n\n"
            "- **H** : 打开帮助\n"
            "- **K** : 打开书架\n"
            "- **S** : 打开设置\n"
            "- **C** : 打开统计\n"
            "- **Q** : 退出\n"
            "- **ESC** : 返回\n\n"
            "## 关于\n\n"
            "NewReader - 终端阅读器\n"
        )


def _get_help_structured(force_refresh: bool = False) -> list[tuple[str, list[tuple[str, str]]]]:
    """获取「标签 → 可折叠分组」嵌套帮助内容（带缓存）"""
    global _help_tabs_cache, _help_tabs_cache_time
    now = time.time()
    if not force_refresh and _help_tabs_cache is not None and (now - _help_tabs_cache_time) < _help_cache_ttl:
        return _help_tabs_cache
    try:
        generator = HelpGenerator()
        tabs = generator.generate_structured()
    except Exception as e:
        logger.error(f"自动生成分页签帮助失败: {e}")
        tabs = [(_get_help_fallback_title(), [(_get_help_fallback_title(), _get_help_content(force_refresh))])]
    _help_tabs_cache = tabs
    _help_tabs_cache_time = now
    return tabs


def _get_help_fallback_title() -> str:
    try:
        return get_global_i18n().t("help.keyboard_shortcuts")
    except Exception:
        return "帮助"


class HelpScreen(Screen[None]):
    """帮助屏幕（标签式布局）"""
    CSS_PATH = "../styles/help_screen_overrides.tcss"
    # 专注（最大化）模式下只保留被最大化的控件，隐藏 Header/Footer/横幅/操作栏
    ALLOW_IN_MAXIMIZED_VIEW: ClassVar[str | None] = ""
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("t", "next_tab", get_global_i18n().t('help.next_tab')),
        ("r", "refresh_help", t('statistics.refresh')),
        ("ctrl+a", "toggle_focus", get_global_i18n().t('help.focus_mode')),
    ]

    def __init__(self):
        """
        初始化帮助屏幕 - 自动扫描所有页面和弹窗的快捷键，按分类生成标签页
        """
        super().__init__()
        self.title = get_global_i18n().t("help.title")
        self.banner_text = f"📖 {get_global_i18n().t('help.title')}  ·  {get_global_i18n().t('help.sub_title')}"
        self._tabs = _get_help_structured()

    def compose(self) -> ComposeResult:
        """
        组合帮助屏幕界面：清爽顶部标题栏 + 标签页主内容（每个分组可折叠）+ 底部操作栏，
        并支持 Ctrl+A 专注/最大化效果。

        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        # 顶部标题栏（专注模式下隐藏）
        yield Static(self.banner_text, id="help-banner", classes="help-banner")
        # 主内容：标签式（TabbedContent），每个标签内按分组用 Collapsible 折叠展示
        with TabbedContent(id="help-content"):
            for ti, (tab_title, sections) in enumerate(self._tabs):
                with TabPane(tab_title, id=f"help-tab-{ti}"):
                    with VerticalScroll(classes="help-sections"):
                        for si, (sec_title, sec_md) in enumerate(sections):
                            with Collapsible(
                                title=sec_title,
                                id=f"help-sec-{ti}-{si}",
                                classes="help-collapsible",
                            ):
                                yield Static(sec_md, markup=True, classes="help-sec-body")
        # 底部操作栏（专注模式下隐藏）
        yield Horizontal(
            Button(get_global_i18n().t("help.back"), id="back-btn"),
            id="help-controls", classes="btn-row"
        )
        yield Footer()

    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        from src.ui.styles.style_manager import apply_style_isolation
        apply_style_isolation(self)
        try:
            self.query_one("#help-content", TabbedContent).focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调

        Args:
            event: 按钮按下事件
        """
        if event.button.id == "back-btn":
            self.app.pop_screen()

    def action_next_tab(self) -> None:
        """t 键 - 在标签之间循环切换"""
        try:
            tc = self.query_one("#help-content", TabbedContent)
            panes = list(tc.query(TabPane))
            if not panes:
                return
            current = tc.active
            idx = next((i for i, p in enumerate(panes) if p.id == current), -1)
            nxt = panes[(idx + 1) % len(panes)]
            tc.active = nxt.id
        except Exception:
            pass

    def action_refresh_help(self) -> None:
        """刷新帮助内容（强制重新扫描所有页面）"""
        self._tabs = _get_help_structured(force_refresh=True)
        try:
            md_widgets = list(self.query("#help-content Static"))
            idx = 0
            for _tab_title, sections in self._tabs:
                for _sec_title, sec_md in sections:
                    if idx < len(md_widgets):
                        md_widgets[idx].update(sec_md)
                    idx += 1
            self.notify(t('statistics.refresh'), timeout=2)
        except Exception as e:
            logger.error(f"刷新帮助内容失败: {e}")
            self.notify(t('statistics.refresh'), timeout=2)

    def action_toggle_focus(self) -> None:
        """
        按 Ctrl+A：最大化 / 还原「当前光标所在控件」（Textual 原生专注模式）。

        依赖 Textual 的 Screen.maximize/minimize：会把当前聚焦控件占满全屏、
        自动隐藏其它控件，再次按 Ctrl+A 或 Esc 还原。
        """
        focused = self.focused
        if focused is None:
            return
        if self.screen.maximized is not None:
            self.screen.minimize()
        else:
            self.screen.maximize(focused)

    def on_key(self, event) -> None:
        """
        处理键盘事件

        Args:
            event: 键盘事件
        """
        if event.key == "escape":
            # 专注模式下先还原最大化控件，否则关闭帮助
            if self.screen.maximized is not None:
                self.screen.minimize()
            else:
                self.app.pop_screen()
            event.stop()
            event.prevent_default()
