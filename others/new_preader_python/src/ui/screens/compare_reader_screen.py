"""
对比阅读屏幕 - 最终稳定版 v4.0
使用最简单的架构确保100%可靠
"""

import os
import asyncio
from typing import List, Dict, ClassVar
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Label, Static, RichLog
from textual import events

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.core.book import Book
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CompareReaderScreen(ModalScreen[None]):
    """
    对比阅读屏幕 - 极简架构
    
    设计原则：
    - 不使用自定义组件类
    - 直接使用Static + 手动更新
    - 所有状态集中管理
    """

    CSS_PATH = "../styles/compare_reader_overrides.tcss"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("up", "scroll", get_global_i18n().t('compare_reader.scroll_up')),
        ("down", "scroll", get_global_i18n().t('compare_reader.scroll_down')),
        ("escape", "exit_compare", get_global_i18n().t('common.exit')),
        ("q", "exit_compare", get_global_i18n().t('common.exit')),
    ]

    def __init__(
        self,
        book_paths: List[str],
        theme_manager: ThemeManager,
        bookshelf: Bookshelf,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.i18n = get_global_i18n()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        
        # 限制最多4个文件
        self.book_paths = book_paths[:min(4, len(book_paths))]
        
        # 核心状态 - 全部集中管理
        self._scroll_pos: int = 0  # 全局滚动位置（行号）
        self._books_data: List[Dict] = []  # 存储所有书籍的内容数据

    def compose(self) -> ComposeResult:
        """构建界面 - 每次都是全新的组件"""
        yield Header()
        
        # 标题 - 使用时间戳避免ID冲突
        import time
        ts = int(time.time() * 1000)
        
        yield Label(
            f"📖 对比阅读 ({len(self.book_paths)} 个文件)",
            id=f"title-{ts}"
        )
        
        # 主容器
        with Horizontal(id=f"main-{ts}"):
            for i in range(len(self.book_paths)):
                # 每个面板容器
                panel_class = f"panel-col panel-{len(self.book_paths)}col"
                with Container(classes=panel_class):
                    # 内容显示区域 - 使用唯一的ID
                    yield Static(
                        "加载中...",
                        id=f"content-{ts}-{i}",
                        classes="viewer"
                    )
        
        # 底部提示
        yield Footer()

    async def on_mount(self) -> None:
        """挂载后立即加载内容"""
        self.theme_manager.apply_theme_to_screen(self)
        
        # 异步加载所有书籍
        await self._load_all_content()

    async def _load_all_content(self) -> None:
        """异步加载所有书籍内容"""
        self._books_data.clear()
        
        # 获取当前屏幕上的所有内容组件ID
        content_widgets = self.query(".viewer")
        widget_list = list(content_widgets)
        
        for i, path in enumerate(self.book_paths):
            data = {
                'title': os.path.basename(path),
                'lines': [],
                'loaded': False
            }
            
            try:
                # 获取书籍对象
                book = self.bookshelf.get_book(path)
                
                if book:
                    # 在线程中读取大文件，避免卡顿UI
                    content = await asyncio.to_thread(book.get_content)
                    
                    if content and len(content.strip()) > 0:
                        data['lines'] = content.split('\n')
                        data['title'] = book.title or data['title']
                    else:
                        data['lines'] = ['[空内容]']
                        logger.warning(f"文件 {path} 为空")
                else:
                    data['lines'] = [f"[未找到: {os.path.basename(path)}]"]
                    
            except Exception as e:
                logger.error(f"加载失败 [{i}] {path}: {e}")
                data['lines'] = [f'[错误: {str(e)[:50]}]']
            
            finally:
                data['loaded'] = True
                self._books_data.append(data)
                
                # 更新对应的显示组件
                if i < len(widget_list):
                    try:
                        widget = widget_list[i]
                        self._update_widget_display(widget, i)
                    except Exception as e:
                        logger.error(f"更新显示失败: {e}")
        
        # 初始化显示第一页
        self._refresh_all_views()

    def _update_widget_display(self, widget: Static, index: int) -> None:
        """更新单个widget的显示内容"""
        if index >= len(self._books_data):
            return
            
        data = self._books_data[index]
        
        if not data['loaded'] or not data['lines']:
            widget.update("⏳ 加载中...")
            return
            
        # 计算可见范围
        lines = data['lines']
        start = max(0, min(self._scroll_pos, len(lines) - 20))
        end = min(start + 20, len(lines))
        
        visible_text = '\n'.join(lines[start:end])
        
        # 格式化显示 - 使用简单的纯文本格式（避免Rich标记语法问题）
        separator = '─' * 30
        header = f"【{data['title']}】"
        footer = f"{start+1}-{end}/{len(lines)}行"
        
        display = f"{header}\n{separator}\n{visible_text}\n{separator}\n{footer}"
        
        widget.update(display)

    def _refresh_all_views(self) -> None:
        """刷新所有视图 - 唯一入口"""
        widgets = self.query(".viewer")
        widget_list = list(widgets)
        
        for i, widget in enumerate(widget_list):
            try:
                self._update_widget_display(widget, i)
            except Exception as e:
                logger.debug(f"刷新视图{i}异常: {e}")

    # ==================== 滚动控制 ====================

    def action_scroll(self) -> None:
        """处理方向键滚动（通过event.key判断方向）"""
        pass  # 实际逻辑在on_key中

    def _do_scroll(self, delta_lines: int) -> None:
        """
        执行滚动操作 - 统一入口
        
        Args:
            delta_lines: 滚动的行数（正数向下，负数向上）
        """
        new_pos = self._scroll_pos + delta_lines
        self._scroll_pos = max(0, new_pos)
        
        logger.debug(f"滚动: delta={delta_lines}, pos={self._scroll_pos}")
        self._refresh_all_views()

    def action_exit_compare(self) -> None:
        """退出对比阅读"""
        self.dismiss(None)

    # ==================== 事件处理器 ====================

    def on_key(self, event: events.Key) -> None:
        """键盘输入 - 屏幕级别统一拦截"""
        key = event.character or event.key
        
        # 方向键控制滚动
        if event.key == "up":
            event.stop()  # 阻止传播给子组件
            self._do_scroll(-5)
            return
            
        elif event.key == "down":
            event.stop()
            self._do_scroll(5)
            return
        
        # 退出快捷键
        elif key.lower() == 'q':
            event.stop()
            self.action_exit_compare()
            return
        else:
            # 其他按键不干预
            pass

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """鼠标滚轮向上"""
        event.stop()
        self._do_scroll(-3)

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """鼠标滚轮向下"""
        event.stop()
        self._do_scroll(3)

    # ==================== 辅助方法 ====================
