"""
文件资源管理器屏幕 - 树形目录结构选择书籍
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, ClassVar, Set
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, Tree, DirectoryTree, Input, ListView, ListItem, Header, Footer, LoadingIndicator, OptionList
from textual.reactive import reactive
from textual import on
from textual import events
from textual.widgets.tree import TreeNode
from textual.widgets.option_list import Option
from textual.message import Message

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.bookshelf import Bookshelf
from src.core.statistics_direct import StatisticsManagerDirect
from src.utils.file_utils import FileUtils
from src.core.bookmark import BookmarkManager
from src.ui.messages import RefreshBookshelfMessage
from src.utils.logger import get_logger
from src.ui.styles.style_manager import ScreenStyleMixin
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

logger = get_logger(__name__)

class FileExplorerScreen(ScreenStyleMixin, Screen[Optional[str]]):
    """文件资源管理器屏幕"""
    
    TITLE: ClassVar[Optional[str]] = None
    CSS_PATH = "../styles/file_explorer_overrides.tcss"
    # 使用 Textual BINDINGS 进行快捷键绑定（不移除 on_key，逐步过渡）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("b", "back_button", get_global_i18n().t('file_explorer.back')),
        ("g", "go_button", get_global_i18n().t('file_explorer.go')),
        ("H", "home_button", get_global_i18n().t('file_explorer.home')),
        ("escape", "back", get_global_i18n().t('common.back')),
        ("enter", "select_button", get_global_i18n().t('common.select')),
        ("s", "select_button", get_global_i18n().t('common.select')),
    ]
    
    # 支持的书籍文件扩展名
    SUPPORTED_EXTENSIONS = {'.txt', '.pdf', '.epub', '.mobi', '.azw', '.azw3', '.md'}
    
    def __init__(self, theme_manager: ThemeManager, bookshelf: Bookshelf, statistics_manager: StatisticsManagerDirect,
                 selection_mode: str = "file", title: Optional[str] = None, direct_open: bool = False):
        """
        初始化文件资源管理器屏幕
        
        Args:
            theme_manager: 主题管理器
            bookshelf: 书架
            statistics_manager: 统计管理器
            selection_mode: 选择模式，"file" 或 "directory"
            title: 自定义标题
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        self.statistics_manager = statistics_manager
        self.selection_mode = selection_mode
        self.direct_open = direct_open  # 使用传入的direct_open参数
        
        # 设置标题
        if title:
            self.title = title
        elif selection_mode == "file":
            self.title = get_global_i18n().t("file_explorer.select_file")
        else:
            self.title = get_global_i18n().t("file_explorer.select_directory")
            
        self.__class__.TITLE = self.title
        self.logger = get_logger(__name__)
        
        # 当前选中的文件路径
        self.selected_file: Optional[str] = None
        # 当前目录路径
        self.current_path = FileUtils.get_home_dir()
        # 文件列表项
        self.file_items: List[Dict[str, str]] = []
        # 选中的文件索引
        self.selected_file_index: Optional[int] = None
        
        # 自动补全相关属性
        self._hide_completion_list
        self.completion_list_visible = False
        self.completion_options: List[str] = []
        self.selected_completion_index = 0
        
    def compose(self) -> ComposeResult:
        """
        组合文件资源管理器界面 - 改进版布局
        """
        yield Header()
        with Container(id="main-container"):
            # 顶部标题区域
            with Container(id="header-container"):
                # yield Label(get_global_i18n().t("file_explorer.title"), id="title", classes="section-title")
                yield Static("", id="current-path")
            
            # 导航栏和补全建议区域
            with Vertical(id="navigation-area"):
                with Horizontal(id="navigation-bar", classes="form-row"):
                    yield Button("←", id="back-btn")
                    yield Input(placeholder=get_global_i18n().t("file_explorer.enter_path"), id="path-input")
                    yield Button(get_global_i18n().t("file_explorer.go"), id="go-btn")
                    yield Button(get_global_i18n().t("file_explorer.home"), id="home-btn")
                
                # 补全建议列表（初始隐藏）
                yield OptionList(id="completion-list")
            
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
                with Horizontal(id="action-buttons", classes="btn-row"):
                    if self.selection_mode == "file":
                        yield Button(get_global_i18n().t("file_explorer.select_file"), id="select-btn")
                    else:
                        yield Button(get_global_i18n().t("file_explorer.select_directory"), id="select-btn")
                    yield Button(get_global_i18n().t("common.cancel"), id="cancel-btn")
            yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 应用样式隔离
        apply_universal_style_isolation(self)
        from src.ui.styles.isolation_manager import apply_style_isolation
        apply_style_isolation(self)
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 原生 LoadingIndicator（初始隐藏），挂载到顶部头部容器
        try:
            self.loading_indicator = LoadingIndicator(id="file-explorer-loading-indicator")
            self.loading_indicator.display = False
            header_container = self.query_one("#header-container")
            header_container.mount(self.loading_indicator)
        except Exception:
            pass

        # 初始化目录树
        self._load_directory_tree()
        
        # 更新当前路径显示
        self._update_current_path()
        
        # 加载当前目录的文件列表
        self._load_file_list()
        
        # 设置焦点到路径输入框
        self.query_one("#path-input").focus()

        # 检查按钮权限并禁用/启用按钮
        self._check_button_permissions()
        
        # 初始化补全列表为隐藏状态
        self._hide_completion_list()
    
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
                self.selected_file_index = None
                
        except (PermissionError, OSError) as e:
            # 访问被拒绝
            error_item = ListItem(Label(get_global_i18n().t("file_explorer.access_denied")))
            file_list.append(error_item)
            logger.warning(f"无法访问目录 {self.current_path}: {e}")
            self.file_items = []
            self.selected_file = None
            self.selected_file_index = None
    
    def _update_current_path(self) -> None:
        """更新当前路径显示"""
        path_display = self.query_one("#current-path", Static)
        path_display.update(f"{get_global_i18n().t("file_explorer.current_path")}: {self.current_path}")
        
        # 更新路径输入框
        path_input = self.query_one("#path-input", Input)
        path_input.value = self.current_path
        
        # 更新状态信息
        status_info = self.query_one("#status-info", Static)
        try:
            file_count = len([f for f in os.listdir(self.current_path) if os.path.isfile(os.path.join(self.current_path, f))])
            dir_count = len([d for d in os.listdir(self.current_path) if os.path.isdir(os.path.join(self.current_path, d))])
            status_info.update(f"{get_global_i18n().t("file_explorer.file")}: {file_count} | {get_global_i18n().t("file_explorer.path")}: {dir_count}")
        except (PermissionError, OSError):
            status_info.update(get_global_i18n().t("file_explorer.cannot_visit"))
    
    def _update_selection_status(self) -> None:
        """更新选择状态显示"""
        status_info = self.query_one("#status-info", Static)
        if self.selected_file:
            if self.selection_mode == "file":
                status_info.update(f"{get_global_i18n().t("file_explorer.selected_files")}: {os.path.basename(self.selected_file)}")
            else:
                status_info.update(f"{get_global_i18n().t("file_explorer.selected_path")}: {os.path.basename(self.selected_file)}")
        else:
            try:
                file_count = len([f for f in os.listdir(self.current_path) if os.path.isfile(os.path.join(self.current_path, f))])
                dir_count = len([d for d in os.listdir(self.current_path) if os.path.isdir(os.path.join(self.current_path, d))])
                status_info.update(f"{get_global_i18n().t("file_explorer.file")}: {file_count} | {get_global_i18n().t("file_explorer.path")}: {dir_count}")
            except (PermissionError, OSError):
                status_info.update(get_global_i18n().t("file_explorer.cannot_visit"))
    
    def _get_path_completions(self, partial_path: str) -> List[str]:
        """
        获取路径自动补全建议
        
        Args:
            partial_path: 部分路径
            
        Returns:
            List[str]: 补全建议列表
        """
        try:
            # 如果路径为空或只有空格，返回空列表
            if not partial_path.strip():
                return []
            
            # 处理绝对路径和相对路径
            if os.path.isabs(partial_path):
                # 绝对路径
                base_dir = os.path.dirname(partial_path)
                search_pattern = os.path.basename(partial_path)
            else:
                # 相对路径，相对于当前目录
                base_dir = self.current_path
                search_pattern = partial_path
            
            # 确保基础目录存在
            if not os.path.isdir(base_dir):
                return []
            
            # 获取匹配的目录和文件
            completions = []
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                
                # 检查是否匹配搜索模式（不区分大小写）
                if search_pattern.lower() in item.lower():
                    if os.path.isdir(item_path):
                        # 如果是目录，添加斜杠
                        completions.append(item + "/")
                    else:
                        completions.append(item)
            
            # 按字母顺序排序
            completions.sort()
            return completions
            
        except (PermissionError, OSError):
            return []
    
    def _update_completion_list(self, partial_path: str) -> None:
        """
        更新补全建议列表
        
        Args:
            partial_path: 部分路径
        """
        try:
            # 如果路径为空或只有空格，隐藏补全列表
            if not partial_path.strip():
                self._hide_completion_list()
                return
            
            # 处理绝对路径和相对路径
            if os.path.isabs(partial_path):
                # 绝对路径
                base_dir = os.path.dirname(partial_path)
                search_pattern = os.path.basename(partial_path)
            else:
                # 相对路径，相对于当前目录
                base_dir = self.current_path
                search_pattern = partial_path
            
            # 确保基础目录存在
            if not os.path.isdir(base_dir):
                self._hide_completion_list()
                return
            
            # 获取匹配的目录和文件
            matches = []
            for item in os.listdir(base_dir):
                if item.lower().startswith(search_pattern.lower()):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isdir(item_path):
                        # 如果是目录，添加斜杠
                        matches.append(item + "/")
                    else:
                        matches.append(item)
            
            # 更新补全选项
            self.completion_options = matches
            
            if matches:
                # 显示补全列表
                self._show_completion_list(matches)
                self.selected_completion_index = 0
            else:
                # 没有匹配项，隐藏补全列表
                self._hide_completion_list()
                
        except (PermissionError, OSError):
            self._hide_completion_list()
    
    def _show_completion_list(self, options: List[str]) -> None:
        """显示补全建议列表"""
        completion_list = self.query_one("#completion-list", OptionList)
        completion_list.clear_options()
        
        # 添加补全选项
        for option in options:
            completion_list.add_option(Option(option))
        
        # 显示补全列表
        completion_list.styles.visibility = "visible"
        self.completion_list_visible = True
        # 显示补全列表的时候把内容区域高度设置为40%
        self.query_one("#content-area", Horizontal).styles.height = "40%"
        
        # 选中第一个选项
        if options:
            completion_list.highlighted = 0
    
    def _hide_completion_list(self) -> None:
        """隐藏补全建议列表"""
        completion_list = self.query_one("#completion-list", OptionList)
        # 使用visibility属性隐藏，而不是display，以保持布局
        completion_list.styles.visibility = "hidden"
        self.completion_list_visible = False
        
        # 恢复目录树和文件列表的高度
        self.query_one("#content-area", Horizontal).styles.height = "70%"
        
        self.completion_options = []
        self.selected_completion_index = 0
    
    def _apply_completion(self) -> None:
        """应用选中的补全项"""
        if not self.completion_list_visible or not self.completion_options:
            return
        
        path_input = self.query_one("#path-input", Input)
        selected_option = self.completion_options[self.selected_completion_index]
        
        # 处理绝对路径和相对路径
        current_value = path_input.value.strip()
        if os.path.isabs(current_value):
            # 绝对路径
            base_dir = os.path.dirname(current_value)
            completed_path = os.path.join(base_dir, selected_option)
        else:
            # 相对路径
            completed_path = selected_option
        
        # 更新输入框值
        path_input.value = completed_path
        path_input.cursor_position = len(completed_path)
        
        # 隐藏补全列表
        # self._hide_completion_list()
    
    def _select_next_completion(self) -> None:
        """选择下一个补全项"""
        if not self.completion_list_visible or not self.completion_options:
            return
        
        completion_list = self.query_one("#completion-list", OptionList)
        self.selected_completion_index = (self.selected_completion_index + 1) % len(self.completion_options)
        completion_list.highlighted = self.selected_completion_index
    
    def _select_prev_completion(self) -> None:
        """选择上一个补全项"""
        if not self.completion_list_visible or not self.completion_options:
            return
        
        completion_list = self.query_one("#completion-list", OptionList)
        self.selected_completion_index = (self.selected_completion_index - 1) % len(self.completion_options)
        completion_list.highlighted = self.selected_completion_index
    
    def _focus_completion_list(self) -> None:
        """将焦点转移到补全列表"""
        if self.completion_list_visible:
            completion_list = self.query_one("#completion-list", OptionList)
            completion_list.focus()
    
    def _focus_path_input(self) -> None:
        """将焦点转移到路径输入框"""
        path_input = self.query_one("#path-input", Input)
        path_input.focus()
    
    @on(OptionList.OptionHighlighted, "#completion-list")
    def on_completion_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """补全列表选项高亮时的处理"""
        if self.completion_list_visible and self.completion_options:
            self.selected_completion_index = event.option_index
    
    @on(OptionList.OptionSelected, "#completion-list")
    def on_completion_selected(self, event: OptionList.OptionSelected) -> None:
        """补全列表选项被选中时的处理"""
        if self.completion_list_visible and self.completion_options:
            self.selected_completion_index = event.option_index
            self._apply_completion()
    
    def _focus_next_component(self) -> None:
        """切换到下一个可聚焦的组件"""
        # 获取所有可聚焦的组件
        focusable_components = [
            self.query_one("#path-input", Input),
            self.query_one("#directory-tree", Tree),
            self.query_one("#file-list", ListView)
        ]
        
        # 找到当前聚焦的组件
        current_focused = None
        for component in focusable_components:
            if component.has_focus:
                current_focused = component
                break
        
        # 切换到下一个组件
        if current_focused:
            current_index = focusable_components.index(current_focused)
            next_index = (current_index + 1) % len(focusable_components)
            focusable_components[next_index].focus()
        else:
            # 如果没有当前聚焦的组件，聚焦到第一个
            focusable_components[0].focus()
    
    def _on_path_input_changed(self, event: Input.Changed) -> None:
        """路径输入框内容改变时的自动补全处理"""
        current_value = event.value.strip()
        
        # 如果输入为空或只有一个字符，不进行补全
        if len(current_value) < 2:
            return
        
        # 检查是否需要自动补全（当输入包含路径分隔符或看起来像路径时）
        if "/" in current_value or "\\" in current_value or os.path.isabs(current_value):
            # 尝试自动补全
            completed_path = self._auto_complete_path(current_value)
            if completed_path and completed_path != current_value:
                # 更新输入框值，但保留光标位置
                event.input.value = completed_path
                # 将光标移动到补全后的位置
                event.input.cursor_position = len(completed_path)
    
    @on(Input.Changed, "#path-input")
    def on_path_input_changed(self, event: Input.Changed) -> None:
        """路径输入框内容改变时的自动补全处理"""
        current_value = event.value.strip()
        
        # 如果输入为空或只有一个字符，隐藏补全列表
        if len(current_value) < 2:
            self._hide_completion_list()
            return
        
        # 更新补全建议列表
        self._update_completion_list(current_value)
    
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
            self.notify(f"{get_global_i18n().t("file_explorer.nav_failed")}: {e}", severity="error")
    
    def _validate_selection(self) -> bool:
        """验证选择是否有效"""
        if not self.selected_file:
            return False
        
        if self.selection_mode == "file":
            return os.path.isfile(self.selected_file)
        else:
            return os.path.isdir(self.selected_file)
    
    def _handle_selection(self) -> None:
        """处理选择操作"""
        if not self._validate_selection():
            if self.selection_mode == "file":
                self.notify(get_global_i18n().t("file_explorer.no_file_selected"), severity="warning")
            else:
                self.notify(get_global_i18n().t("file_explorer.no_directory_selected"), severity="warning")
            return
        
        # 根据模式决定行为
        if self.direct_open and self.selection_mode == "file":
            # 直接打开模式下，打开选中的文件
            self._open_selected_file()
        else:
            # 普通模式下，返回选中的路径
            self.dismiss(self.selected_file)
    
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
            if node_path and node_path != "placeholder":
                if os.path.isdir(node_path):
                    if self.selection_mode == "directory":
                        # 在目录选择模式下，直接选中该目录
                        self.selected_file = node_path
                        self._update_selection_status()
                    else:
                        # 在文件选择模式下，进入该目录
                        self._navigate_to_path(node_path)
                elif os.path.isfile(node_path) and self.selection_mode == "file":
                    # 在文件选择模式下，选中文件
                    self.selected_file = node_path
                    self._update_selection_status()
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
    
    def action_back(self) -> None:
        """ESC 返回上一页"""
        self.app.pop_screen()
    
    def action_back_button(self) -> None:
        """b 键 - 返回上一级目录"""
        if not self._has_permission("file_explorer.back"):
            self.notify(get_global_i18n().t("file_explorer.no_permission"), severity="warning")
            return
        
        # 返回上一级目录
        parent_path = os.path.dirname(self.current_path)
        if parent_path != self.current_path:  # 避免无限循环
            self._navigate_to_path(parent_path)
    
    def action_go_button(self) -> None:
        """g 键 - 导航到输入的路径"""
        if not self._has_permission("file_explorer.navigate"):
            self.notify(get_global_i18n().t("file_explorer.no_permission"), severity="warning")
            return
        
        # 导航到输入的路径
        path_input = self.query_one("#path-input", Input)
        input_path = path_input.value.strip()
        if input_path:
            self._navigate_to_path(input_path)
    
    def action_home_button(self) -> None:
        """h 键 - 返回主目录"""
        if not self._has_permission("file_explorer.home"):
            self.notify(get_global_i18n().t("file_explorer.no_permission"), severity="warning")
            return
        
        # 返回主目录
        self._navigate_to_path(FileUtils.get_home_dir())
    
    def action_select_button(self) -> None:
        """enter/s 键 - 选择操作"""
        if not self._has_permission("file_explorer.select"):
            self.notify(get_global_i18n().t("file_explorer.no_permission"), severity="warning")
            return
        
        # 选择操作
        self._handle_selection()

    def _check_button_permissions(self) -> None:
        """检查按钮权限并禁用/启用按钮"""
        try:
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            
            # 检查各个按钮的权限
            back_btn = self.query_one("#back-btn", Button)
            go_btn = self.query_one("#go-btn", Button)
            home_btn = self.query_one("#home-btn", Button)
            select_btn = self.query_one("#select-btn", Button)
            cancel_btn = self.query_one("#cancel-btn", Button)
            
            # 检查权限并设置按钮状态
            if not db_manager.has_permission("file_explorer.back"):
                back_btn.disabled = True
                back_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                back_btn.disabled = False
                back_btn.tooltip = None
                
            if not db_manager.has_permission("file_explorer.navigate"):
                go_btn.disabled = True
                go_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                go_btn.disabled = False
                go_btn.tooltip = None
                
            if not db_manager.has_permission("file_explorer.home"):
                home_btn.disabled = True
                home_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                home_btn.disabled = False
                home_btn.tooltip = None
                
            if not db_manager.has_permission("file_explorer.select"):
                select_btn.disabled = True
                select_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                select_btn.disabled = False
                select_btn.tooltip = None
                
            if not db_manager.has_permission("file_explorer.cancel"):
                cancel_btn.disabled = True
                cancel_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                cancel_btn.disabled = False
                cancel_btn.tooltip = None
                
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
    
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        # 检查权限
        if event.button.id and not self._has_button_permission(event.button.id):
            self.notify(get_global_i18n().t("file_explorer.np_action"), severity="warning")
            return
            
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
            
        elif event.button.id == "select-btn":
            # 选择操作
            self._handle_selection()
            
        elif event.button.id == "cancel-btn":
            # 取消操作 -> 返回上一页
            self.app.pop_screen()
    
    def on_key(self, event: events.Key) -> None:
        """键盘事件处理"""
        if event.key == "escape":
            # ESC键行为：
            # 1. 如果补全列表可见，隐藏补全列表并返回焦点到输入框
            # 2. 如果补全列表不可见，返回上一页
            if self.completion_list_visible:
                # ESC键隐藏补全列表，焦点回到输入框
                self._hide_completion_list()
                self._focus_path_input()
            else:
                # ESC键返回上一页（并阻止冒泡到 App 层，避免二次返回）
                # 使用应用提供的安全返回方法，避免屏幕栈错误
                if hasattr(self.app, 'action_back'):
                    # 异步调用action_back方法
                    self.app.call_later(self.app.action_back)
                else:
                    # 备用方案：检查屏幕栈长度
                    try:
                        if len(self.app._screen_stack) > 1:
                            self.app.pop_screen()
                    except (AttributeError, Exception):
                        pass  # 如果无法安全返回，则不执行任何操作
            event.stop()
        
        elif event.key == "enter":
            # 回车键处理选中项需要权限
            if self._has_permission("file_explorer.select"):
                self._handle_selected_item()
            else:
                self.notify(get_global_i18n().t("file_explorer.np_choose_file"), severity="warning")
            event.stop()
        
        elif event.key == "up" and not self.completion_list_visible:
            # 上箭头键选择上一个文件（仅在补全列表不可见时）
            self._select_previous_file()
            event.stop()
        
        elif event.key == "down" and not self.completion_list_visible:
            # 下箭头键选择下一个文件（仅在补全列表不可见时）
            self._select_next_file()
            event.stop()
        
        elif event.key == "s":
            # S键选择
            self._handle_selection()
            event.stop()
        
        elif event.key == "ctrl+i":
            # Ctrl+I 显示补全建议
            path_input = self.query_one("#path-input", Input)
            current_value = path_input.value.strip()
            
            if current_value:
                completions = self._get_path_completions(current_value)
                if completions:
                    # 显示补全建议
                    suggestions = ", ".join(completions[:5])  # 最多显示5个建议
                    if len(completions) > 5:
                        suggestions += "..."
                    self.notify(f"补全建议: {suggestions}", severity="information")
                else:
                    self.notify("没有找到匹配的路径", severity="information")
            event.stop()
        
        elif event.key == "down" and self.completion_list_visible:
            # 下方向键选择下一个补全项，并将焦点转移到补全列表
            self._select_next_completion()
            self._focus_completion_list()
            event.stop()
            
        elif event.key == "up" and self.completion_list_visible:
            # 上方向键选择上一个补全项，并将焦点转移到补全列表
            self._select_prev_completion()
            self._focus_completion_list()
            event.stop()
            
        elif event.key == "right" and self.completion_list_visible:
            # 右方向键应用选中的补全项
            self._apply_completion()
            event.stop()

            
        elif event.key == "tab" and self.completion_list_visible:
            # Tab键切换到其他区域（目录和文件列表）
            self._hide_completion_list()
            # 手动切换到下一个可聚焦的组件
            self._focus_next_component()
            event.stop()
    
    def _show_loading_animation(self, message: Optional[str] = None) -> None:
        """显示加载动画"""
        if message is None:
            message = get_global_i18n().t("common.on_action")
        try:
            # 原生 LoadingIndicator：可见即动画
            try:
                if not hasattr(self, "loading_indicator"):
                    self.loading_indicator = self.query_one("#file-explorer-loading-indicator", LoadingIndicator)
            except Exception:
                pass
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    self.loading_indicator.display = True
            except Exception:
                pass

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
            # 原生 LoadingIndicator：隐藏
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    self.loading_indicator.display = False
            except Exception:
                pass

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
        if not self.file_items or self.selected_file_index is None:
            return
        
        if self.selected_file_index > 0:
            self.selected_file_index -= 1
            self._update_file_selection()
    
    def _select_next_file(self) -> None:
        """选择下一个文件"""
        if not self.file_items or self.selected_file_index is None:
            return
        
        if self.selected_file_index < len(self.file_items) - 1:
            self.selected_file_index += 1
            self._update_file_selection()
    
    def _update_file_selection(self) -> None:
        """更新文件选择显示"""
        if not self.file_items or self.selected_file_index is None or self.selected_file_index < 0:
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
    
    def _open_selected_file(self) -> None:
        """打开选中的文件进行阅读"""
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
            
            # 打开阅读器并关闭当前文件资源管理器
            reader_screen = ReaderScreen(
                book=book,
                theme_manager=self.theme_manager,
                statistics_manager=self.statistics_manager,
                bookmark_manager=bookmark_manager,
                bookshelf=self.bookshelf
            )
            # 先关闭当前屏幕，然后打开阅读器
            self.app.pop_screen()  # 关闭文件资源管理器
            self.app.push_screen(reader_screen)  # 打开阅读器
            
        except Exception as e:
            self.logger.error(f"打开文件失败: {e}")
            self.notify(f"{get_global_i18n().t("file_explorer.open_failed")}: {e}", severity="error")
    
    def _has_button_permission(self, button_id: str) -> bool:
        """检查按钮权限"""
        try:
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            
            permission_map = {
                "back-btn": "file_explorer.back",
                "go-btn": "file_explorer.navigate", 
                "home-btn": "file_explorer.home",
                "select-btn": "file_explorer.select",
                "cancel-btn": "file_explorer.cancel"
            }
            
            if button_id in permission_map:
                return db_manager.has_permission(permission_map[button_id])
            
            return True  # 默认允许未知按钮
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
            return True  # 出错时默认允许
    
    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            return db_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def _handle_selected_item(self) -> None:
        """处理选中的项目"""
        if not self.file_items or self.selected_file_index is None or self.selected_file_index < 0:
            return
        
        selected_item = self.file_items[self.selected_file_index]
        
        if self.selection_mode == "directory":
            # 目录选择模式下，只能选择目录
            if selected_item["type"] == "directory":
                self.selected_file = selected_item["path"]
                self._update_selection_status()
            else:
                self.notify(get_global_i18n().t("file_explorer.select_directory_only"), severity="warning")
        else:
            # 文件选择模式下
            if selected_item["type"] == "directory":
                # 如果是目录，进入该目录
                self._navigate_to_path(selected_item["path"])
            elif selected_item["type"] == "book":
                # 如果是书籍文件，根据direct_open参数决定行为
                if self.direct_open:
                    # 直接打开文件进行阅读
                    self._open_selected_file()
                else:
                    # 选中文件但不打开，等待用户确认
                    self.selected_file = selected_item["path"]
                    self._update_selection_status()
            else:
                # 其他文件类型，显示不支持的提示
                self.notify(get_global_i18n().t("file_explorer.unsupported_format"), severity="warning")
    
    @on(ListView.Selected)
    def on_file_list_selected(self, message: ListView.Selected) -> None:
        """文件列表选择事件"""
        try:
            if message.list_view.id == "file-list":
                self.selected_file_index = message.list_view.index
                if self.selected_file_index is not None and 0 <= self.selected_file_index < len(self.file_items):
                    selected_item = self.file_items[self.selected_file_index]
                    
                    if self.selection_mode == "file":
                        # 文件选择模式下，只能选择文件
                        if selected_item["type"] in ["book", "file"]:
                            self.selected_file = selected_item["path"]
                        else:
                            self.selected_file = None
                    else:
                        # 目录选择模式下，只能选择目录
                        if selected_item["type"] == "directory":
                            self.selected_file = selected_item["path"]
                        else:
                            self.selected_file = None
                    
                    self._update_selection_status()
        except Exception as e:
            logger.error(f"处理文件列表选择失败: {e}")
    
    @on(ListView.Highlighted)
    def on_file_list_highlighted(self, message: ListView.Highlighted) -> None:
        """文件列表高亮事件"""
        try:
            if message.list_view.id == "file-list":
                self.selected_file_index = message.list_view.index
                if self.selected_file_index is not None and 0 <= self.selected_file_index < len(self.file_items):
                    selected_item = self.file_items[self.selected_file_index]
                    
                    if self.selection_mode == "file":
                        # 文件选择模式下，只能选择文件
                        if selected_item["type"] in ["book", "file"]:
                            self.selected_file = selected_item["path"]
                        else:
                            self.selected_file = None
                    else:
                        # 目录选择模式下，只能选择目录
                        if selected_item["type"] == "directory":
                            self.selected_file = selected_item["path"]
                        else:
                            self.selected_file = None
                    
                    self._update_selection_status()
        except Exception as e:
            logger.error(f"处理文件列表高亮失败: {e}")