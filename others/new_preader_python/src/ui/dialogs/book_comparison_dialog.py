"""
书籍对比对话框，用于详细比较两本书籍的内容
"""

import os
import difflib
from typing import Optional, List, Tuple
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Static, Button, Label, ProgressBar, Tabs, TabPane, RichLog
from textual import on

# 注释掉样式隔离系统
# from src.ui.styles.universal_style_isolation import apply_universal_style_isolation
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.book import Book
from src.utils.book_duplicate_detector import BookDuplicateDetector
from src.utils.file_utils import FileUtils
from src.utils.string_utils import StringUtils
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BookComparisonDialog(ModalScreen[None]):
    """书籍对比对话框"""
    
    # 完全不使用CSS，确保没有样式干扰UI构建
    CSS_PATH = None
    
    BINDINGS = [
        ("escape", "close", get_global_i18n().t('common.close')),
    ]
    
    def __init__(self, theme_manager: ThemeManager, book1: Book, book2: Book):
        """
        初始化书籍对比对话框
        
        Args:
            theme_manager: 主题管理器
            book1: 书籍1
            book2: 书籍2
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.book1 = book1
        self.book2 = book2
        self.comparison_data = None
        
        # 组件ID列表，用于查询
        self.book1_ids = ["book1-title", "book1-author", "book1-size", "book1-format", "book1-path"]
        self.book2_ids = ["book2-title", "book2-author", "book2-size", "book2-format", "book2-path"]
    
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        yield Header()
        with Container():
            with Vertical():
                # 标题
                Label(get_global_i18n().t("book_comparison.title"))
                
                # 书籍基本信息对比
                with Horizontal():
                    # 书籍1信息
                    with Vertical():
                        Label(get_global_i18n().t("book_comparison.book_info", num=1))
                        yield Label("加载中...", id="book1-title")
                        yield Label("加载中...", id="book1-author")
                        yield Label("加载中...", id="book1-size")
                        yield Label("加载中...", id="book1-format")
                        yield Label("加载中...", id="book1-path")
                    
                    # 书籍2信息
                    with Vertical():
                        Label(get_global_i18n().t("book_comparison.book_info", num=2))
                        yield Label("加载中...", id="book2-title")
                        yield Label("加载中...", id="book2-author")
                        yield Label("加载中...", id="book2-size")
                        yield Label("加载中...", id="book2-format")
                        yield Label("加载中...", id="book2-path")
                
                # 相似度信息
                Label(get_global_i18n().t("book_comparison.similarity_title"))
                yield Label("计算中...", id="similarity-info")
                yield ProgressBar(total=100, show_eta=False, id="similarity-bar")
                
                # 内容对比选项卡
                with Tabs():
                    with TabPane(get_global_i18n().t("book_comparison.tab_samples")):
                        # 内容采样对比
                        with Horizontal():
                            # 书籍1内容
                            with ScrollableContainer():
                                Label(get_global_i18n().t("book_comparison.book_content", num=1))
                                yield Vertical(id="book1-samples")
                            
                            # 书籍2内容
                            with ScrollableContainer():
                                Label(get_global_i18n().t("book_comparison.book_content", num=2))
                                yield Vertical(id="book2-samples")
                    
                    with TabPane(get_global_i18n().t("book_comparison.tab_diff")):
                        # 差异对比（类似git diff）
                        with ScrollableContainer():
                            yield RichLog(id="diff-view", wrap=True, markup=True)
                
                # 操作按钮
                with Horizontal():
                    Button(get_global_i18n().t("book_comparison.refresh"), id="refresh-btn", variant="primary")
                    Button(get_global_i18n().t("common.close"), id="close-btn")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 延迟开始比较，确保组件完全加载
        self.set_timer(0.2, self._compare_books)
    
    def action_close(self) -> None:
        """关闭对话框"""
        self.dismiss()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下时的回调"""
        if event.button.id == "close-btn":
            self.action_close()
        elif event.button.id == "refresh-btn":
            # 刷新比较数据
            self._load_comparison_data()
    
    def _compare_books(self) -> None:
        """比较两本书籍"""
        # 显示基本信息
        self._display_basic_info()
        
        # 异步加载比较数据
        self._load_comparison_data()
    
    def _display_basic_info(self) -> None:
        """显示书籍基本信息"""
        def update_info():
            try:
                # 书籍1信息
                self.query_one("#book1-title").update(
                    f"{get_global_i18n().t('bookshelf.title')}: {self.book1.title}"
                )
                self.query_one("#book1-author").update(
                    f"{get_global_i18n().t('bookshelf.author')}: {self.book1.author}"
                )
                
                # 格式化文件大小
                size1_str = ""
                try:
                    if hasattr(self.book1, 'size') and self.book1.size:
                        if self.book1.size < 1024 * 1024:  # 小于1MB
                            size_kb = self.book1.size / 1024.0
                            size1_str = f"{size_kb:.1f} KB"
                        else:
                            size_mb = self.book1.size / (1024.0 * 1024.0)
                            size1_str = f"{size_mb:.1f} MB"
                except:
                    size1_str = "未知"
                
                self.query_one("#book1-size").update(
                    f"{get_global_i18n().t('bookshelf.size')}: {size1_str}"
                )
                self.query_one("#book1-format").update(
                    f"{get_global_i18n().t('bookshelf.format')}: {self.book1.format.upper() if self.book1.format else ''}"
                )
                self.query_one("#book1-path").update(
                    f"{get_global_i18n().t('bookshelf.path')}: {self.book1.path}"
                )
                
                # 书籍2信息
                self.query_one("#book2-title").update(
                    f"{get_global_i18n().t('bookshelf.title')}: {self.book2.title}"
                )
                self.query_one("#book2-author").update(
                    f"{get_global_i18n().t('bookshelf.author')}: {self.book2.author}"
                )
                
                # 格式化文件大小
                size2_str = ""
                try:
                    if hasattr(self.book2, 'size') and self.book2.size:
                        if self.book2.size < 1024 * 1024:  # 小于1MB
                            size_kb = self.book2.size / 1024.0
                            size2_str = f"{size_kb:.1f} KB"
                        else:
                            size_mb = self.book2.size / (1024.0 * 1024.0)
                            size2_str = f"{size_mb:.1f} MB"
                except:
                    size2_str = "未知"
                
                self.query_one("#book2-size").update(
                    f"{get_global_i18n().t('bookshelf.size')}: {size2_str}"
                )
                self.query_one("#book2-format").update(
                    f"{get_global_i18n().t('bookshelf.format')}: {self.book2.format.upper() if self.book2.format else ''}"
                )
                self.query_one("#book2-path").update(
                    f"{get_global_i18n().t('bookshelf.path')}: {self.book2.path}"
                )
                
            except Exception as e:
                logger.error(f"更新书籍基本信息失败: {e}")
                # 如果失败，重试一次
                self.set_timer(0.1, update_info)
        
        # 延迟执行更新，确保组件已挂载
        self.set_timer(0.1, update_info)
    
    def _load_comparison_data(self) -> None:
        """加载比较数据"""
        def perform_comparison():
            """执行比较操作"""
            try:
                # 比较书籍内容
                comparison = BookDuplicateDetector.compare_books(self.book1, self.book2)
                
                # 获取详细内容比较
                detailed_comparison = BookDuplicateDetector.compare_books_content(
                    self.book1, 
                    self.book2
                )
                
                # 合并比较结果
                comparison_data = {
                    "basic_comparison": comparison,
                    "detailed_comparison": detailed_comparison
                }
                
                # 更新UI
                self.call_after_refresh(self._display_comparison_results, comparison_data)
                
            except Exception as e:
                logger.error(f"比较书籍内容时出错: {e}")
                self.call_after_refresh(self._display_error)
        
        # 在后台线程中执行比较
        from threading import Thread
        thread = Thread(target=perform_comparison)
        thread.daemon = True
        thread.start()
    
    def _display_comparison_results(self, comparison_data: dict) -> None:
        """显示比较结果"""
        self.comparison_data = comparison_data
        
        # 显示相似度信息
        basic_comparison = comparison_data["basic_comparison"]
        similarity = basic_comparison.similarity
        
        # 更新相似度信息
        similarity_text = get_global_i18n().t(
            "book_comparison.similarity_value",
            similarity=f"{similarity:.1%}"
        )
        
        # 添加重复类型信息
        duplicate_types = []
        if basic_comparison.file_name_match:
            duplicate_types.append(get_global_i18n().t("duplicate_books.type_file_name"))
        if basic_comparison.hash_match:
            duplicate_types.append(get_global_i18n().t("duplicate_books.type_hash_identical"))
        if similarity >= 0.2:
            duplicate_types.append(get_global_i18n().t("duplicate_books.type_content_similar", similarity=f"{similarity:.1%}"))
        
        if duplicate_types:
            similarity_text += f"\n{get_global_i18n().t('duplicate_books.types')}: {', '.join(duplicate_types)}"
        
        try:
            self.query_one("#similarity-info").update(similarity_text)
            
            # 更新相似度进度条
            similarity_bar = self.query_one("#similarity-bar", ProgressBar)
            similarity_bar.advance(int(similarity * 100))
        except Exception as e:
            logger.error(f"更新相似度信息失败: {e}")
        
        # 显示内容对比
        self._display_content_comparison(comparison_data["detailed_comparison"])
        
        # 生成并显示差异对比
        self._generate_diff_view()
    
    def _display_content_comparison(self, detailed_comparison: dict) -> None:
        """显示内容对比"""
        def update_content():
            try:
                # 获取内容容器
                book1_samples = self.query_one("#book1-samples", Vertical)
                book2_samples = self.query_one("#book2-samples", Vertical)
                
                # 清除加载文本
                book1_samples.remove_children()
                book2_samples.remove_children()
                
                # 显示书籍1的内容采样
                samples1 = detailed_comparison["samples"]["book1"]
                if samples1.get("start"):
                    book1_samples.mount(Label(get_global_i18n().t("book_comparison.content_start")))
                    book1_samples.mount(Label(samples1["start"][:500] + ("..." if len(samples1["start"]) > 500 else "")))
                
                if samples1.get("middle"):
                    book1_samples.mount(Label(get_global_i18n().t("book_comparison.content_middle")))
                    book1_samples.mount(Label(samples1["middle"][:500] + ("..." if len(samples1["middle"]) > 500 else "")))
                
                if samples1.get("end"):
                    book1_samples.mount(Label(get_global_i18n().t("book_comparison.content_end")))
                    book1_samples.mount(Label(samples1["end"][:500] + ("..." if len(samples1["end"]) > 500 else "")))
                
                # 显示书籍2的内容采样
                samples2 = detailed_comparison["samples"]["book2"]
                if samples2.get("start"):
                    book2_samples.mount(Label(get_global_i18n().t("book_comparison.content_start")))
                    book2_samples.mount(Label(samples2["start"][:500] + ("..." if len(samples2["start"]) > 500 else "")))
                
                if samples2.get("middle"):
                    book2_samples.mount(Label(get_global_i18n().t("book_comparison.content_middle")))
                    book2_samples.mount(Label(samples2["middle"][:500] + ("..." if len(samples2["middle"]) > 500 else "")))
                
                if samples2.get("end"):
                    book2_samples.mount(Label(get_global_i18n().t("book_comparison.content_end")))
                    book2_samples.mount(Label(samples2["end"][:500] + ("..." if len(samples2["end"]) > 500 else "")))
                
            except Exception as e:
                logger.error(f"更新内容比较失败: {e}")
                # 如果失败，重试一次
                self.set_timer(0.1, update_content)
        
        # 延迟执行更新，确保组件已挂载
        self.set_timer(0.1, update_content)
    
    def _generate_diff_view(self) -> None:
        """生成类似git diff的差异视图"""
        try:
            # 获取书籍内容
            content1 = self._get_book_content(self.book1)
            content2 = self._get_book_content(self.book2)
            
            if not content1 or not content2:
                self._show_error_in_diff()
                return
            
            # 分割为行
            lines1 = content1.splitlines(keepends=True)
            lines2 = content2.splitlines(keepends=True)
            
            # 生成差异
            diff_lines = list(difflib.unified_diff(
                lines1, lines2,
                fromfile=f"{self.book1.title} ({self.book1.format})",
                tofile=f"{self.book2.title} ({self.book2.format})",
                lineterm=''
            ))
            
            # 显示差异
            diff_view = self.query_one("#diff-view", RichLog)
            diff_view.clear()
            
            # 添加文件头信息
            diff_view.write(f"[bold]{get_global_i18n().t('book_comparison.diff_header')}[/bold]")
            diff_view.write(f"[dim]{get_global_i18n().t('book_comparison.diff_book1')}: {self.book1.title} ({self.book1.format})[/dim]")
            diff_view.write(f"[dim]{get_global_i18n().t('book_comparison.diff_book2')}: {self.book2.title} ({self.book2.format})[/dim]")
            diff_view.write("")
            
            # 如果没有差异
            if not diff_lines:
                diff_view.write(f"[green]{get_global_i18n().t('book_comparison.no_diff')}[/green]")
                return
            
            # 显示差异行
            for line in diff_lines:
                if line.startswith('---') or line.startswith('+++'):
                    # 文件信息行
                    diff_view.write(f"[cyan]{line}[/cyan]")
                elif line.startswith('@@'):
                    # 位置信息行
                    diff_view.write(f"[magenta]{line}[/magenta]")
                elif line.startswith('-'):
                    # 删除行
                    diff_view.write(f"[red]{line}[/red]")
                elif line.startswith('+'):
                    # 添加行
                    diff_view.write(f"[green]{line}[/green]")
                else:
                    # 上下文行
                    diff_view.write(line)
                    
        except Exception as e:
            logger.error(f"生成差异视图失败: {e}")
            self._show_error_in_diff()
    
    def _get_book_content(self, book: Book) -> Optional[str]:
        """获取书籍内容"""
        try:
            if not book or not book.path:
                return None
                
            if not os.path.exists(book.path):
                return None
                
            # 读取文件内容，限制大小
            file_size = os.path.getsize(book.path)
            max_size = 100 * 1024  # 100KB，适合diff比较
                
            if file_size > max_size:
                with open(book.path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 读取开头和结尾部分
                    start_content = f.read(max_size // 2)
                    f.seek(-max_size // 2, os.SEEK_END)
                    end_content = f.read()
                    return start_content + "\n...\n" + end_content
            else:
                with open(book.path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
                    
        except Exception as e:
            logger.error(f"读取书籍内容失败: {e}")
            return None
    
    def _show_error_in_diff(self) -> None:
        """在差异视图中显示错误"""
        try:
            diff_view = self.query_one("#diff-view", RichLog)
            diff_view.clear()
            diff_view.write(f"[red]{get_global_i18n().t('book_comparison.comparison_failed')}[/red]")
        except Exception as e:
            logger.error(f"显示差异视图错误失败: {e}")
    
    def _display_error(self) -> None:
        """显示错误信息"""
        def show_error():
            try:
                self.query_one("#similarity-info").update(
                    get_global_i18n().t("book_comparison.comparison_failed")
                )
                
                # 清除加载文本
                book1_samples = self.query_one("#book1-samples", Vertical)
                book2_samples = self.query_one("#book2-samples", Vertical)
                
                book1_samples.remove_children()
                book2_samples.remove_children()
                
                book1_samples.mount(
                    Label(get_global_i18n().t("book_comparison.comparison_failed"))
                )
                book2_samples.mount(
                    Label(get_global_i18n().t("book_comparison.comparison_failed"))
                )
            except Exception as e:
                logger.error(f"显示错误信息失败: {e}")
                # 如果失败，重试一次
                self.set_timer(0.1, show_error)
        
        # 延迟执行，确保组件已挂载
        self.set_timer(0.1, show_error)