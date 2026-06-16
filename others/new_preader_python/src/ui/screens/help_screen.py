"""
帮助屏幕 - 自动扫描所有页面的快捷键绑定并生成分类 Markdown 帮助文档
"""


from typing import Optional, ClassVar
import time

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, MarkdownViewer, Header, Footer

from src.locales.i18n_manager import get_global_i18n, t
from src.utils.logger import get_logger
from src.utils.help_generator import HelpGenerator

logger = get_logger(__name__)

# 模块级缓存：避免每次打开帮助都重新扫描
_help_cache: Optional[str] = None
_help_cache_time: float = 0.0
_help_cache_ttl: float = 300.0  # 5 分钟缓存


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


class HelpScreen(Screen[None]):
    """帮助屏幕"""
    CSS_PATH = "../styles/help_screen_overrides.tcss"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("t", "toggle_table_of_contents", get_global_i18n().t('help.toggle_table_of_contents')),
        ("r", "refresh_help", t('statistics.refresh')),
    ]
    
    def __init__(self):
        """
        初始化帮助屏幕 - 自动扫描所有页面和弹窗的快捷键
        """
        super().__init__()
        self.title = get_global_i18n().t("help.title")
        self.help_content = _get_help_content()
    
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

    def action_refresh_help(self) -> None:
        """刷新帮助内容（强制重新扫描所有页面）"""
        self.help_content = _get_help_content(force_refresh=True)
        try:
            from textual.widgets import Markdown
            markdown = self.query_one(Markdown)
            markdown.update(self.help_content)
        except Exception:
            # 如果无法更新组件，通知用户重新进入帮助
            self.notify(t('statistics.refresh'), timeout=2)
    
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