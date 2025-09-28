"""
文件资源管理器屏幕 - 树形目录结构选择书籍
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, ClassVar, Set
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, Tree, DirectoryTree, Input, ListView, ListItem
from textual.reactive import reactive
from textual import on
from textual import events
from textual.widgets.tree import TreeNode
from textual.message import Message

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.core.statistics_direct import StatisticsManagerDirect
from src.utils.file_utils import FileUtils
from src.core.bookmark import BookmarkManager
from src.ui.messages import RefreshBookshelfMessage
from src.utils.logger import get_logger

logger = get_logger(__name__)

class FileExplorerScreen(Screen[None]):
    """文件资源管理器屏幕"""
    
    TITLE: ClassVar[Optional[str]] = None
    CSS_PATH = "../styles/file_explorer.css"
    
    # 支持的书籍文件扩展名
    SUPPORTED_EXTENSIONS = {'.txt', '.pdf', '.epub', '.mobi', '.azw', '.azw3', '.md'}
    
    def __init__(self, theme_manager: ThemeManager, bookshelf: Bookshelf, statistics_manager: StatisticsManagerDirect):
        """
        初始化文件资源管理器屏幕
        
        Args:
            theme_manager: 主题管理器
            bookshelf: 书架
            statistics_manager: 统计管理器
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        self.statistics_manager = statistics_manager
        self.title = get_global_i18n().t("file_explorer.title")
        self.__class__.TITLE = self.title
        self.logger = get_logger(__name__)
        
        # 当前选中的文件路径
        self.selected_file: Optional[str] = None
        # 当前目录路径
        self.current_path = FileUtils.get_home_dir()
        # 文件列表项
        self.file_items: List[Dict[str, str]] = []
        # 选中的文件索引
        self.selected_file_index: int = -1
        
    def compose(self) -> ComposeResult:
        """
        组合文件资源管理器界面 - 改进版布局
        """
        with Container(id="main-container"):
            # 顶部标题区域
            with Container(id="header-container"):
                yield Label(get_global_i18n().t("file_explorer.title"), id="title")
                yield Static("", id="current-path")
            
            # 导航栏
            with Horizontal(id="navigation-bar"):
                yield Button("←", id="back-btn")
                yield Input(placeholder=get_global_i18n().t("file_explorer.enter_path"), id="path-input")
                yield Button(get_global_i18n().t("file_explorer.go"), id="go-btn")
                yield Button(get_global_i18n().t("file_explorer.home"), id="home-btn")
            
            # 主内容区域
            with Horizontal(id="content-area"):
                # 左侧目录树
                with Vertical(id="tree-panel"):
                    yield Label(get_global_i18n().t("file_explorer.directory_tree"), id="tree-label")
                    yield Tree(get_global_i18n().t("file_explorer.root"), id="directory-tree")
                
                # 右侧文件列表
                with Vertical(id="file-panel"):
                    yield Label(get_global_i18n().t("file_explorer.file_list"), id="file-label")
                    yield ListView(id="file-list")
            
            # 底部状态和操作区域
            with Container(id="footer-container"):
                yield Static("", id="status-info")
                with Horizontal(id="action-buttons"):
                    yield Button(get_global_i18n().t("file_explorer.open_book"), id="open-btn")
                    yield Button(get_global_i18n().t("file_explorer.add_to_bookshelf"), id="add-btn")
                    yield Button(get_global_i18n().t("common.back"), id="back-to-bookshelf-btn")
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 初始化目录树
        self._load_directory_tree()
        
        # 更新当前路径显示
        self._update_current_path()
        
        # 加载当前目录的文件列表
        self._load_file_list()
    
    def _load_directory_tree(self) -> None:
        """加载目录树"""
        tree = self.query_one("#directory-tree", Tree)
        tree.clear()
        
        # 设置根节点标签和数据
        root_node = tree.root
        root_node.set_label(os.path.basename(self.current_path) or self.current_path)
        root_node.data = self.current_path
        root_node.expand()
        
        # 从当前路径开始构建树
        self._build_tree_node(root_node, self.current_path)
    
    def _build_tree_node(self, parent_node: TreeNode[str], path: str) -> None:
        """构建目录树节点"""
        try:
            # 获取目录下的子目录
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    # 创建目录节点，存储完整路径作为数据
                    dir_node = parent_node.add(item, data=item_path)
                    dir_node.allow_expand = True
                    
                    # 检查是否有子目录，如果有则添加一个占位符节点
                    try:
                        sub_items = os.listdir(item_path)
                        has_subdirs = any(os.path.isdir(os.path.join(item_path, sub_item)) for sub_item in sub_items)
                        if has_subdirs:
                            # 添加一个占位符节点，用于延迟加载
                            placeholder_node = dir_node.add("...", data="placeholder")
                            placeholder_node.allow_expand = False  # 占位符节点不允许展开
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError) as e:
            logger.warning(f"无法访问目录 {path}: {e}")
    
    def _load_file_list(self) -> None:
        """加载当前目录的文件列表"""
        file_list = self.query_one("#file-list", ListView)
        
        try:
            # 清空现有列表
            file_list.clear()
            self.file_items = []  # 存储文件项信息
            
            # 获取当前目录下的文件和目录
            items = []
            for item in sorted(os.listdir(self.current_path)):
                item_path = os.path.join(self.current_path, item)
                
                if os.path.isdir(item_path):
                    # 目录项
                    items.append({"name": item, "path": item_path, "type": "directory", "display": f"📁 {item}/"})
                elif os.path.isfile(item_path):
                    # 文件项，检查是否为支持的书籍格式
                    ext = FileUtils.get_file_extension(item_path)
                    if ext in self.SUPPORTED_EXTENSIONS:
                        items.append({"name": item, "path": item_path, "type": "book", "display": f"📖 {item}"})
                    else:
                        items.append({"name": item, "path": item_path, "type": "file", "display": f"📄 {item}"})
            
            if items:
                # 添加到ListView
                for item in items:
                    list_item = ListItem(Label(item["display"]))
                    list_item.data = item  # 存储项目数据
                    file_list.append(list_item)
                    self.file_items.append(item)
                
                # 默认选中第一项
                if len(items) > 0:
                    self.selected_file_index = 0
                    if items[0]["type"] in ["book", "file"]:
                        self.selected_file = items[0]["path"]
                    else:
                        self.selected_file = None
            else:
                # 空目录
                empty_item = ListItem(Label(get_global_i18n().t("file_explorer.empty_directory")))
                file_list.append(empty_item)
                self.file_items = []
                self.selected_file = None
                self.selected_file_index = -1
                
        except (PermissionError, OSError) as e:
            # 访问被拒绝
            error_item = ListItem(Label(get_global_i18n().t("file_explorer.access_denied")))
            file_list.append(error_item)
            logger.warning(f"无法访问目录 {self.current_path}: {e}")
            self.file_items = []
            self.selected_file = None
            self.selected_file_index = -1
    
    def _update_current_path(self) -> None:
        """更新当前路径显示"""
        path_display = self.query_one("#current-path", Static)
        path_display.update(f"当前路径: {self.current_path}")
        
        # 更新路径输入框
        path_input = self.query_one("#path-input", Input)
        path_input.value = self.current_path
        
        # 更新状态信息
        status_info = self.query_one("#status-info", Static)
        try:
            file_count = len([f for f in os.listdir(self.current_path) if os.path.isfile(os.path.join(self.current_path, f))])
            dir_count = len([d for d in os.listdir(self.current_path) if os.path.isdir(os.path.join(self.current_path, d))])
            status_info.update(f"文件: {file_count} | 目录: {dir_count}")
        except (PermissionError, OSError):
            status_info.update("无法访问")
    
    def _navigate_to_path(self, path: str) -> None:
        """导航到指定路径"""
        try:
            if os.path.isdir(path):
                self.current_path = path
                self._update_current_path()
                self._load_file_list()
                self._load_directory_tree()
            else:
                self.notify(get_global_i18n().t("file_explorer.invalid_directory"), severity="error")
        except Exception as e:
            self.notify(f"导航失败: {e}", severity="error")
    
    def _open_selected_file(self) -> None:
        """打开选中的文件"""
        if not self.selected_file:
            self.notify(get_global_i18n().t("file_explorer.no_file_selected"), severity="warning")
            return
        
        try:
            # 检查文件是否为支持的格式
            ext = FileUtils.get_file_extension(self.selected_file)
            if ext not in self.SUPPORTED_EXTENSIONS:
                self.notify(get_global_i18n().t("file_explorer.unsupported_format"), severity="error")
                return
            
            # 创建书籍对象并打开
            from src.core.book import Book
            from src.ui.screens.reader_screen import ReaderScreen
            
            file_name = os.path.basename(self.selected_file)
            book_name = FileUtils.get_file_name(self.selected_file)
            
            book = Book(self.selected_file, book_name, get_global_i18n().t("app.unknown_author"))
            bookmark_manager = BookmarkManager()
            
            # 打开阅读器
            reader_screen = ReaderScreen(
                book=book,
                theme_manager=self.theme_manager,
                statistics_manager=self.statistics_manager,
                bookmark_manager=bookmark_manager,
                bookshelf=self.bookshelf
            )
            self.app.push_screen(reader_screen)
            
        except Exception as e:
            self.logger.error(f"打开文件失败: {e}")
            self.notify(f"打开文件失败: {e}", severity="error")
    
    def _add_to_bookshelf(self) -> None:
        """将选中的文件添加到书架"""
        if not self.selected_file:
            self.notify(get_global_i18n().t("file_explorer.no_file_selected"), severity="warning")
            return
        
        try:
            # 检查文件是否为支持的格式
            ext = FileUtils.get_file_extension(self.selected_file)
            if ext not in self.SUPPORTED_EXTENSIONS:
                self.notify(get_global_i18n().t("file_explorer.unsupported_format"), severity="error")
                return
            
            # 添加到书架
            book = self.bookshelf.add_book(self.selected_file)
            if book:
                self.notify(
                    get_global_i18n().t("file_explorer.book_added", title=book.title),
                    severity="information"
                )
            else:
                self.notify(get_global_i18n().t("file_explorer.add_failed"), severity="error")
                
        except Exception as e:
            self.logger.error(f"添加到书架失败: {e}")
            self.notify(f"添加到书架失败: {e}", severity="error")
    
    @on(Tree.NodeExpanded)
    def on_tree_node_expanded(self, message: Tree.NodeExpanded) -> None:
        """目录树节点展开事件 - 延迟加载子目录"""
        try:
            # 使用节点存储的数据获取路径
            node_path = message.node.data
            
            if node_path and node_path != "placeholder" and os.path.isdir(node_path):
                # 检查是否已经有子节点（占位符节点）
                if (message.node.children and 
                    len(message.node.children) > 0 and 
                    message.node.children[0].data == "placeholder"):
                    
                    # 清除占位符节点并加载实际子目录
                    message.node.remove_children()
                    self._build_tree_node(message.node, node_path)
                    
                    # 重新检查是否有子目录，如果没有则禁用展开
                    if not message.node.children:
                        message.node.allow_expand = False
                    else:
                        message.node.allow_expand = True
                        
        except Exception as e:
            logger.error(f"处理树节点展开失败: {e}")
    
    @on(Tree.NodeSelected)
    def on_tree_node_selected(self, message: Tree.NodeSelected) -> None:
        """目录树节点选择事件"""
        try:
            # 使用节点存储的数据获取路径
            node_path = message.node.data
            if node_path and node_path != "placeholder" and os.path.isdir(node_path):
                self._navigate_to_path(node_path)
        except Exception as e:
            logger.error(f"处理树节点选择失败: {e}")
    
    def _get_node_path(self, node: TreeNode[str]) -> Optional[str]:
        """获取树节点的完整路径"""
        try:
            path_parts = []
            current_node = node
            
            # 从当前节点向上遍历构建路径
            while current_node and current_node != current_node.tree.root:
                # 跳过占位符节点
                if current_node.label != "...":
                    path_parts.insert(0, current_node.label)
                current_node = current_node.parent
            
            # 从根目录开始构建完整路径
            if path_parts:
                full_path = os.path.join(self.current_path, *path_parts)
                return full_path
            
            return self.current_path
        except Exception as e:
            logger.error(f"获取节点路径失败: {e}")
            return None
    
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "back-btn":
            # 返回上一级目录
            parent_path = os.path.dirname(self.current_path)
            if parent_path != self.current_path:  # 避免无限循环
                self._navigate_to_path(parent_path)
                
        elif event.button.id == "go-btn":
            # 导航到输入的路径
            path_input = self.query_one("#path-input", Input)
            input_path = path_input.value.strip()
            if input_path:
                self._navigate_to_path(input_path)
                
        elif event.button.id == "home-btn":
            # 返回主目录
            self._navigate_to_path(FileUtils.get_home_dir())
            
        elif event.button.id == "open-btn":
            # 打开选中的文件
            self._open_selected_file()
            
        elif event.button.id == "add-btn":
            # 添加到书架
            self._add_to_bookshelf()
            
        elif event.button.id == "back-to-bookshelf-btn":
            # 返回书架
            self.app.pop_screen()
    
    def on_key(self, event: events.Key) -> None:
        """键盘事件处理"""
        if event.key == "escape":
            # ESC键返回书架
            self.app.pop_screen()
            event.prevent_default()
        
        elif event.key == "enter":
            # 回车键处理选中项
            self._handle_selected_item()
            event.prevent_default()
        
        elif event.key == "up":
            # 上箭头键选择上一个文件
            self._select_previous_file()
            event.prevent_default()
        
        elif event.key == "down":
            # 下箭头键选择下一个文件
            self._select_next_file()
            event.prevent_default()
        
        elif event.key == "a":
            # A键添加到书架
            self._add_to_bookshelf()
            event.prevent_default()
        
        elif event.key == "o":
            # O键打开文件
            self._open_selected_file()
            event.prevent_default()
    
    def _show_loading_animation(self, message: Optional[str] = None) -> None:
        """显示加载动画"""
        if message is None:
            message = get_global_i18n().t("common.on_action")
        try:
            from src.ui.components.textual_loading_animation import textual_animation_manager
            if textual_animation_manager.show_default(message):
                return
            from src.ui.components.loading_animation import animation_manager
            animation_manager.show_default(message)
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"显示加载动画失败: {e}")
    
    def _hide_loading_animation(self) -> None:
        """隐藏加载动画"""
        try:
            from src.ui.components.textual_loading_animation import textual_animation_manager
            if textual_animation_manager.hide_default():
                return
            from src.ui.components.loading_animation import animation_manager
            animation_manager.hide_default()
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"隐藏加载动画失败: {e}")
    
    def _select_previous_file(self) -> None:
        """选择上一个文件"""
        if not self.file_items:
            return
        
        if self.selected_file_index > 0:
            self.selected_file_index -= 1
            self._update_file_selection()
    
    def _select_next_file(self) -> None:
        """选择下一个文件"""
        if not self.file_items:
            return
        
        if self.selected_file_index < len(self.file_items) - 1:
            self.selected_file_index += 1
            self._update_file_selection()
    
    def _update_file_selection(self) -> None:
        """更新文件选择显示"""
        if not self.file_items or self.selected_file_index < 0:
            return
        
        file_list = self.query_one("#file-list", ListView)
        
        # 设置选中项
        if 0 <= self.selected_file_index < len(file_list.children):
            file_list.index = self.selected_file_index
            
            # 更新选中的文件路径
            selected_item = self.file_items[self.selected_file_index]
            if selected_item["type"] in ["book", "file"]:
                self.selected_file = selected_item["path"]
            else:
                self.selected_file = None
    
    def _handle_selected_item(self) -> None:
        """处理选中的项目"""
        if not self.file_items or self.selected_file_index < 0:
            return
        
        selected_item = self.file_items[self.selected_file_index]
        
        if selected_item["type"] == "directory":
            # 如果是目录，进入该目录
            self._navigate_to_path(selected_item["path"])
        elif selected_item["type"] == "book":
            # 如果是书籍文件，打开它
            self._open_selected_file()
        else:
            # 其他文件类型，显示不支持的提示
            self.notify(get_global_i18n().t("file_explorer.unsupported_format"), severity="warning")
    
    @on(ListView.Selected)
    def on_file_list_selected(self, message: ListView.Selected) -> None:
        """文件列表选择事件"""
        try:
            if message.list_view.id == "file-list":
                self.selected_file_index = message.list_view.index
                if 0 <= self.selected_file_index < len(self.file_items):
                    selected_item = self.file_items[self.selected_file_index]
                    if selected_item["type"] in ["book", "file"]:
                        self.selected_file = selected_item["path"]
                    else:
                        self.selected_file = None
        except Exception as e:
            logger.error(f"处理文件列表选择失败: {e}")
    
    @on(ListView.Highlighted)
    def on_file_list_highlighted(self, message: ListView.Highlighted) -> None:
        """文件列表高亮事件"""
        try:
            if message.list_view.id == "file-list":
                self.selected_file_index = message.list_view.index
                if 0 <= self.selected_file_index < len(self.file_items):
                    selected_item = self.file_items[self.selected_file_index]
                    if selected_item["type"] in ["book", "file"]:
                        self.selected_file = selected_item["path"]
                    else:
                        self.selected_file = None
        except Exception as e:
            logger.error(f"处理文件列表高亮失败: {e}")