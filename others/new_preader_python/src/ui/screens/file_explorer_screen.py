"""
文件资源管理器屏幕 - 树形目录结构选择书籍
"""

import os
import time
import stat
from pathlib import Path
from typing import Dict, Any, Optional, List, ClassVar, Set, Union
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Center
from textual.widgets import Select, Static, Button, Label, Switch, Tree, DirectoryTree, Input, ListView, ListItem, Header, Footer, LoadingIndicator, OptionList
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
from src.config.default_config import SUPPORTED_FORMATS

logger = get_logger(__name__)

class FileExplorerScreen(ScreenStyleMixin, Screen[Optional[Union[str, List[str]]]]):
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
    
    # 支持的书籍文件扩展名（从配置文件读取）
    SUPPORTED_EXTENSIONS = set(SUPPORTED_FORMATS)
    
    def __init__(self, theme_manager: ThemeManager, bookshelf: Bookshelf, statistics_manager: StatisticsManagerDirect,
                 selection_mode: str = "file", title: Optional[str] = None, direct_open: bool = False,
                 multiple: bool = False, file_extensions: Optional[Set[str]] = None):
        """
        初始化文件资源管理器屏幕
        
        Args:
            theme_manager: 主题管理器
            bookshelf: 书架
            statistics_manager: 统计管理器
            selection_mode: 选择模式，"file" 或 "directory"
            title: 自定义标题
            multiple: 是否允许多选
            file_extensions: 自定义文件扩展名集合（如 {".zip", ".tar"}），如果为None则使用默认的书籍格式
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.bookshelf = bookshelf
        self.statistics_manager = statistics_manager
        self.selection_mode = selection_mode
        self.direct_open = direct_open  # 使用传入的direct_open参数
        self.multiple = multiple  # 多选模式
        
        # 使用自定义文件扩展名或默认的书籍格式
        if file_extensions is not None:
            self.file_extensions = file_extensions
        else:
            self.file_extensions = self.SUPPORTED_EXTENSIONS
        
        # 设置标题
        if title:
            self.title = title
        elif selection_mode == "file":
            if multiple:
                self.title = get_global_i18n().t("file_explorer.select_files")
            else:
                self.title = get_global_i18n().t("file_explorer.select_file")
        else:
            self.title = get_global_i18n().t("file_explorer.select_directory")
            
        self.__class__.TITLE = self.title
        self.logger = get_logger(__name__)
        
        # 当前选中的文件路径（单选模式）
        self.selected_file: Optional[str] = None
        # 多选模式下选中的文件路径集合
        self.selected_files: Set[str] = set()
        # 当前目录路径
        self.current_path = FileUtils.get_home_dir()
        # 文件列表项
        self.file_items: List[Dict[str, str]] = []
        # 选中的文件索引（单选模式）
        self.selected_file_index: Optional[int] = None
        # 多选模式下选中的文件索引集合
        self.selected_file_indices: Set[int] = set()
        
        # 自动补全相关属性
        self.completion_list_visible = False
        self.completion_options: List[str] = []
        self.selected_completion_index = 0
        
        # 性能优化相关缓存
        self._directory_cache = {}  # 目录内容缓存
        self._bookshelf_cache = None  # 书库文件缓存
        
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
                    with Vertical(id="navigation-bar-left"):
                        yield Button("←", id="back-btn")
                        yield Input(placeholder=get_global_i18n().t("file_explorer.enter_path"), id="path-input")
                        yield Button(get_global_i18n().t("file_explorer.go"), id="go-btn")
                        yield Button(get_global_i18n().t("file_explorer.home"), id="home-btn")
                    with Vertical(id="navigation-bar-right"):
                        if self.selection_mode == "file":
                            # 如果是文件选择模式，则显示搜索框和按钮 start
                            yield Label(get_global_i18n().t("file_explorer.diff_mode"), id="file-explorer-diff-mode-label")
                            yield Switch(value=False, id="file-explorer-diff-mode-switch")
                            yield Input(placeholder=get_global_i18n().t("file_explorer.search_placeholder"), id="file-explorer-search-input")
                            # 动态生成搜索选择框选项
                            search_options = [(get_global_i18n().t("search.all_formats"), "all")]
                            # 根据self.file_extensions生成格式选项
                            for ext in self.file_extensions:
                                # 去掉点号，转换为大写作为显示名称
                                display_name = ext.upper().lstrip('.')
                                search_options.append((display_name, ext))
                            
                            yield Select(id="file-explorer-search-select", options=search_options, prompt=get_global_i18n().t("common.select_ext_prompt"))
                            yield Button(get_global_i18n().t("common.search"), id="file-explorer-search-btn")
                            # 如果是文件选择模式，则显示搜索框和按钮 end
                            yield Button(get_global_i18n().t("file_explorer.select_file"), id="select-btn")
                        else:
                            yield Button(get_global_i18n().t("file_explorer.select_directory"), id="select-btn")
                        yield Button(get_global_i18n().t("common.cancel"), id="cancel-btn")
                
                # 补全建议列表（初始隐藏）
                with Center():
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
        """加载当前目录的文件列表（优化版本 - 减少系统调用）"""
        file_list = self.query_one("#file-list", ListView)
        
        try:
            # 清空现有列表
            file_list.clear()
            self.file_items = []  # 存储文件项信息
            
            # 只调用一次os.listdir,避免重复I/O
            try:
                all_items = os.listdir(self.current_path)
            except (PermissionError, OSError) as e:
                logger.warning(f"无法访问目录 {self.current_path}: {e}")
                return
            
            # 一次性处理所有项目,减少系统调用
            items = []
            book_count = 0
            dir_count = 0
            
            for item in sorted(all_items):
                item_path = os.path.join(self.current_path, item)
                
                # 使用try-except避免stat调用失败
                try:
                    is_dir = os.path.isdir(item_path)
                    
                    if is_dir:
                        # 目录项
                        dir_count += 1
                        items.append({"name": item, "path": item_path, "type": "directory", "display": f"📁 {item}/"})
                    else:
                        # 文件项，只显示支持的书籍格式
                        ext = FileUtils.get_file_extension(item_path)
                        if ext in self.file_extensions:
                            book_count += 1
                            items.append({"name": item, "path": item_path, "type": "book", "display": f"📖 {item}"})
                except (PermissionError, OSError):
                    # 跳过无法访问的文件
                    continue
            
            # 缓存统计信息
            self._current_file_count = book_count
            self._current_dir_count = dir_count
            
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
                
                # 更新文件列表的视觉状态
                self._update_file_list_visual_state()
                
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
        """更新当前路径显示（优化版本 - 使用缓存）"""
        path_display = self.query_one("#current-path", Static)
        path_display.update(f"{get_global_i18n().t("file_explorer.current_path")}: {self.current_path}")
        
        # 更新路径输入框
        path_input = self.query_one("#path-input", Input)
        path_input.value = self.current_path
        
        # 更新状态信息（使用缓存值，避免重复调用os.listdir）
        status_info = self.query_one("#status-info", Static)
        try:
            # 优先使用缓存值
            if hasattr(self, '_current_file_count') and hasattr(self, '_current_dir_count'):
                file_count = self._current_file_count
                dir_count = self._current_dir_count
            else:
                # 如果缓存不存在，才调用os.listdir
                file_count = len([f for f in os.listdir(self.current_path) if os.path.isfile(os.path.join(self.current_path, f))])
                dir_count = len([d for d in os.listdir(self.current_path) if os.path.isdir(os.path.join(self.current_path, d))])
            status_info.update(f"{get_global_i18n().t("file_explorer.file")}: {file_count} | {get_global_i18n().t("file_explorer.path")}: {dir_count}")
        except (PermissionError, OSError):
            status_info.update(get_global_i18n().t("file_explorer.cannot_visit"))
    
    def _update_selection_status(self) -> None:
        """更新选择状态显示"""
        status_info = self.query_one("#status-info", Static)
        
        # 动态检测多选模式
        is_multiple_mode = self.multiple
        
        logger.debug(f"更新选择状态: 多选模式={is_multiple_mode}, 选中文件数={len(self.selected_files)}, 当前文件={self.selected_file}")
        
        if is_multiple_mode and self.selected_files:
            # 多选模式
            count = len(self.selected_files)
            if count == 1:
                file_name = os.path.basename(next(iter(self.selected_files)))
                status_info.update(f"{get_global_i18n().t("file_explorer.selected_files")}: {file_name} ({get_global_i18n().t("file_explorer.multype_mode")})")
            else:
                status_info.update(f"{get_global_i18n().t("file_explorer.selected_files")}: {count} {get_global_i18n().t("file_explorer.files")} ({get_global_i18n().t("file_explorer.multype_mode")})")
        elif self.selected_file:
            # 单选模式
            if self.selection_mode == "file":
                status_info.update(f"{get_global_i18n().t("file_explorer.selected_files")}: {os.path.basename(self.selected_file)} ({get_global_i18n().t("file_explorer.single_mode")})")
            else:
                status_info.update(f"{get_global_i18n().t("file_explorer.selected_path")}: {os.path.basename(self.selected_file)} ({get_global_i18n().t("file_explorer.single_mode")})")
        else:
            # 无选择（使用缓存避免重复I/O）
            try:
                # 优先使用缓存值
                if hasattr(self, '_current_file_count') and hasattr(self, '_current_dir_count'):
                    file_count = self._current_file_count
                    dir_count = self._current_dir_count
                else:
                    # 如果缓存不存在，才调用os.listdir
                    file_count = len([f for f in os.listdir(self.current_path) if os.path.isfile(os.path.join(self.current_path, f))])
                    dir_count = len([d for d in os.listdir(self.current_path) if os.path.isdir(os.path.join(self.current_path, d))])
                mode_text = get_global_i18n().t("file_explorer.multype_mode") if is_multiple_mode else get_global_i18n().t("file_explorer.single_mode")
                status_info.update(f"{get_global_i18n().t("file_explorer.file")}: {file_count} | {get_global_i18n().t("file_explorer.path")}: {dir_count} ({mode_text})")
            except (PermissionError, OSError):
                mode_text = get_global_i18n().t("file_explorer.multype_mode") if is_multiple_mode else get_global_i18n().t("file_explorer.single_mode")
                status_info.update(f"{get_global_i18n().t("file_explorer.cannot_visit")} ({mode_text})")
    
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
            
            # 获取匹配的目录（只补全目录，不补全文件名）
            matches = []
            for item in os.listdir(base_dir):
                if item.lower().startswith(search_pattern.lower()):
                    item_path = os.path.join(base_dir, item)
                    if os.path.isdir(item_path):
                        # 只添加目录，添加斜杠
                        matches.append(item + "/")
            
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
            completed_path = os.path.join(self.current_path, selected_option)
        
        # 检查补全后的路径是否为目录
        if os.path.isdir(completed_path):
            # 如果是目录，直接导航到该目录
            self._navigate_to_path(completed_path)
            # 导航后更新输入框值并设置焦点到内容结尾
            path_input.value = completed_path
            path_input.cursor_position = len(completed_path)
            path_input.focus()
        else:
            # 如果不是目录，只更新输入框值
            path_input.value = completed_path
            path_input.cursor_position = len(completed_path)
            path_input.focus()
        
        # 隐藏补全列表
        self._hide_completion_list()
    
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
        """导航到指定路径（优化版本 - 清理缓存）"""
        try:
            if os.path.isdir(path):
                self.current_path = path
                # 清理缓存，因为目录改变了
                if hasattr(self, '_directory_cache'):
                    self._directory_cache.clear()
                self._update_current_path()
                self._load_file_list()
                self._load_directory_tree()
            else:
                self.notify(get_global_i18n().t("file_explorer.invalid_directory"), severity="error")
        except Exception as e:
            self.notify(f"{get_global_i18n().t("file_explorer.nav_failed")}: {e}", severity="error")
    
    def _validate_selection(self) -> bool:
        """验证选择是否有效"""
        if self.multiple:
            # 多选模式
            if not self.selected_files:
                return False
            
            if self.selection_mode == "file":
                # 验证所有选中的文件都存在
                for file_path in self.selected_files:
                    if not os.path.isfile(file_path):
                        return False
                return True
            else:
                # 目录选择模式不支持多选
                return False
        else:
            # 单选模式
            if not self.selected_file:
                return False
            
            if self.selection_mode == "file":
                return os.path.isfile(self.selected_file)
            else:
                return os.path.isdir(self.selected_file)
    
    def _handle_selection(self) -> None:
        """处理选择操作"""
        if not self._validate_selection():
            # 动态检测多选模式
            is_multiple_mode = self.multiple
            
            if is_multiple_mode:
                if self.selection_mode == "file":
                    self.notify(get_global_i18n().t("file_explorer.no_files_selected"), severity="warning")
                else:
                    self.notify(get_global_i18n().t("file_explorer.no_directory_selected"), severity="warning")
            else:
                if self.selection_mode == "file":
                    self.notify(get_global_i18n().t("file_explorer.no_file_selected"), severity="warning")
                else:
                    self.notify(get_global_i18n().t("file_explorer.no_directory_selected"), severity="warning")
            return
        
        # 根据模式决定行为
        if self.direct_open and self.selection_mode == "file":
            # 直接打开模式下，打开选中的文件
            if self.multiple:
                # 多选模式下不支持直接打开多个文件
                self.notify(get_global_i18n().t("file_explorer.cannot_open_multiple"), severity="warning")
            else:
                self._open_selected_file()
        else:
            # 普通模式下，返回选中的路径
            # 动态检测多选模式
            is_multiple_mode = self.multiple
            
            if is_multiple_mode:
                # 返回多选的文件列表
                self.dismiss(list(self.selected_files))
            else:
                # 返回单选的文件路径
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
        if not self._has_permission("file_explorer.go"):
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
            from src.utils.multi_user_manager import multi_user_manager
            db_manager = DatabaseManager()
            
            # 获取当前用户ID - 使用与应用实例一致的方式
            current_user = getattr(self.app, 'current_user', None)
            if current_user:
                current_user_id = current_user.get('id')

            # 如果没有从应用实例获取到用户信息，回退到多用户管理器
            if current_user_id is None:
                from src.utils.multi_user_manager import multi_user_manager
                current_user = multi_user_manager.get_current_user()
                current_user_id = current_user.get('id') if current_user else None
            
            # 如果多用户模式关闭，user_id应该为None（查询所有数据）
            if current_user_id is not None:
                from src.utils.multi_user_manager import multi_user_manager
                if not multi_user_manager.is_multi_user_enabled():
                    user_id = None
                else:
                    user_id = current_user_id
            else:
                user_id = None
            
            user_id = current_user.get("id", 0)
            role = current_user.get("role", "user")
            logger.info(f"_check_button_permissions:当前用户: {user_id}, 角色: {role}")
            # 检查各个按钮的权限
            back_btn = self.query_one("#back-btn", Button)
            go_btn = self.query_one("#go-btn", Button)
            home_btn = self.query_one("#home-btn", Button)
            select_btn = self.query_one("#select-btn", Button)
            cancel_btn = self.query_one("#cancel-btn", Button)
            
            # 检查权限并设置按钮状态
            if not db_manager.has_permission(user_id, "file_explorer.back") and role != "super_admin" and role != "superadmin":
                back_btn.disabled = True
                back_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                back_btn.disabled = False
                back_btn.tooltip = None
                
            if not db_manager.has_permission(user_id, "file_explorer.go") and role != "super_admin" and role != "superadmin":
                go_btn.disabled = True
                go_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                go_btn.disabled = False
                go_btn.tooltip = None
                
            if not db_manager.has_permission(user_id, "file_explorer.home") and role != "super_admin" and role != "superadmin":
                home_btn.disabled = True
                home_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                home_btn.disabled = False
                home_btn.tooltip = None
                
            if not db_manager.has_permission(user_id, "file_explorer.select") and role != "super_admin" and role != "superadmin":
                select_btn.disabled = True
                select_btn.tooltip = get_global_i18n().t("file_explorer.no_permission")
            else:
                select_btn.disabled = False
                select_btn.tooltip = None
                
            if not db_manager.has_permission(user_id, "file_explorer.cancel") and role != "super_admin" and role != "superadmin":
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
        
        # 更新选择状态显示
        self._update_selection_status()
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
            if ext not in self.file_extensions:
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
            from src.utils.multi_user_manager import multi_user_manager
            db_manager = DatabaseManager()
            
            # 获取当前用户ID - 使用与应用实例一致的方式
            current_user = getattr(self.app, 'current_user', None)
            if current_user:
                current_user_id = current_user.get('id')

            # 如果没有从应用实例获取到用户信息，回退到多用户管理器
            if current_user_id is None:
                from src.utils.multi_user_manager import multi_user_manager
                current_user = multi_user_manager.get_current_user()
                current_user_id = current_user.get('id') if current_user else None
            
            # 如果多用户模式关闭，user_id应该为None（查询所有数据）
            if current_user_id is not None:
                from src.utils.multi_user_manager import multi_user_manager
                if not multi_user_manager.is_multi_user_enabled():
                    user_id = None
                else:
                    user_id = current_user_id
            else:
                user_id = None
            
            role = current_user.get("role")

            logger.info(f"_has_button_permission: 当前用户ID: {user_id}, 角色: {role}")
            
            # 超级管理员拥有所有权限
            if role == "super_admin" or role == "superadmin": 
                return True
            
            permission_map = {
                "back-btn": "file_explorer.back",
                "go-btn": "file_explorer.go", 
                "home-btn": "file_explorer.home",
                "select-btn": "file_explorer.select",
                "cancel-btn": "file_explorer.cancel"
            }
            
            if button_id in permission_map:
                return db_manager.has_permission(user_id, permission_map[button_id], role)
            
            return True  # 默认允许未知按钮
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
            return True  # 出错时默认允许
    
    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            from src.core.database_manager import DatabaseManager
            from src.utils.multi_user_manager import multi_user_manager
            db_manager = DatabaseManager()
            
            # 获取当前用户ID - 使用与应用实例一致的方式
            current_user = getattr(self.app, 'current_user', None)
            if current_user:
                current_user_id = current_user.get('id')

            # 如果没有从应用实例获取到用户信息，回退到多用户管理器
            if current_user_id is None:
                from src.utils.multi_user_manager import multi_user_manager
                current_user = multi_user_manager.get_current_user()
                current_user_id = current_user.get('id') if current_user else None
            
            # 如果多用户模式关闭，user_id应该为None（查询所有数据）
            if current_user_id is not None:
                from src.utils.multi_user_manager import multi_user_manager
                if not multi_user_manager.is_multi_user_enabled():
                    user_id = None
                else:
                    user_id = current_user_id
            else:
                user_id = None
            
            role = current_user.get("role")

            logger.info(f"_has_permission: 当前用户ID: {user_id}, 角色: {role}")

            # 超级管理员拥有所有权限
            if role == "super_admin" or role == "superadmin": 
                return True
            
            return db_manager.has_permission(user_id, permission_key, role)
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
    
    def _get_bookshelf_files(self) -> Set[str]:
        """获取书库中所有书籍文件的文件名集合"""
        try:
            bookshelf_files = set()
            # 直接使用self.bookshelf.books,避免重复查询数据库
            logger.debug(f"开始获取书库文件列表，书架中书籍数量: {len(self.bookshelf.books)}")
            for book_path, book in self.bookshelf.books.items():
                # 获取书籍的文件名（不包含路径）
                if hasattr(book, 'path') and book.path:
                    filename = os.path.basename(book.path)
                    bookshelf_files.add(filename)
                    # logger.debug(f"书架中的书籍: {filename} (完整路径: {book.path})")
                else:
                    logger.warning(f"书籍对象没有path属性或path为空: {book_path}")
            logger.info(f"获取到的书库文件列表 ({len(bookshelf_files)} 个): {bookshelf_files}")
            return bookshelf_files
        except Exception as e:
            logger.error(f"获取书库文件列表失败: {e}")
            return set()
    
    def _get_all_files_in_current_directory(self) -> List[Dict[str, str]]:
        """获取当前目录下的所有文件（优化版本 - 使用缓存）"""
        # 使用缓存避免重复I/O
        cache_key = (self.current_path, tuple(sorted(self.file_extensions)))

        # 检查缓存是否存在且有效
        # 注意：缓存有效期改为1秒，确保每次切换目录都重新扫描
        if hasattr(self, '_directory_cache'):
            cached_data = self._directory_cache.get(cache_key)
            if cached_data:
                cache_time, cached_files = cached_data
                # 缓存有效期1秒（从5秒缩短，确保刷新及时）
                if time.time() - cache_time < 1:
                    logger.debug(f"使用缓存的文件列表: {len(cached_files)} 个文件")
                    return cached_files
                else:
                    logger.debug(f"缓存已过期（{time.time() - cache_time:.2f}秒），重新扫描")

        all_files = []
        try:
            # 只调用一次os.listdir
            items = os.listdir(self.current_path)

            logger.info(f"📁 当前目录: {self.current_path}")
            logger.info(f"📊 目录项目数量: {len(items)}, 支持的文件扩展名: {self.file_extensions}")

            # 优化：预先扩展名集合用于快速查找
            supported_extensions = self.file_extensions

            # 对于大量文件，使用进度提示和定时日志
            start_time = time.time()
            total_items = len(items)

            for idx, item in enumerate(items):
                # 每500个文件输出一次进度，对于14000个文件会输出28次
                if idx % 500 == 0 and idx > 0:
                    elapsed = time.time() - start_time
                    remaining_pct = (idx / total_items) * 100
                    logger.info(f"⏳ 已处理 {idx}/{total_items} 个项目 ({remaining_pct:.1f}%) - 用时: {elapsed:.1f}秒")

                # 快速检查扩展名，避免不必要的系统调用
                if '.' in item:
                    ext = item.rsplit('.', 1)[-1].lower()
                    if ext.startswith('.'):
                        ext = ext[1:]
                    ext_with_dot = '.' + ext
                else:
                    continue  # 没有扩展名，跳过

                # 只处理支持的书籍格式
                if ext_with_dot in supported_extensions:
                    item_path = os.path.join(self.current_path, item)
                    try:
                        # 使用os.lstat而不是os.path.isfile，更快且不跟随符号链接
                        stat_info = os.lstat(item_path)
                        if stat.S_ISREG(stat_info.st_mode):  # 是普通文件
                            all_files.append({
                                "name": item,
                                "path": item_path,
                                "type": "book",
                                "display": f"📖 {item}",
                                "directory": "."
                            })
                    except (OSError, AttributeError):
                        # 跳过无法访问的文件
                        continue

        except (PermissionError, OSError) as e:
            logger.warning(f"⚠️  获取当前目录文件失败: {e}")

        logger.info(f"最终获取到的文件数量: {len(all_files)}")
        logger.debug(f"文件列表: {[f['name'] for f in all_files]}")

        # 缓存结果
        if not hasattr(self, '_directory_cache'):
            self._directory_cache = {}

        self._directory_cache[cache_key] = (time.time(), all_files)

        return all_files

    def _filter_files_not_in_bookshelf(self, files: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """过滤掉书库中已存在的文件（优化版本 - 使用缓存）"""
        try:
            # 缓存书库文件列表,避免重复查询
            # 检查缓存是否存在
            cache_valid = False
            current_time = 0
            bookshelf_files = set()
            bookshelf_files_lower = set()

            if hasattr(self, '_bookshelf_cache'):
                cache_data = self._bookshelf_cache
                if isinstance(cache_data, dict) and 'time' in cache_data:
                    current_time = time.time()
                    # 缓存有效期30秒
                    if current_time - cache_data['time'] < 30:
                        cache_valid = True
                        bookshelf_files = cache_data.get('files', set())
                        bookshelf_files_lower = cache_data.get('files_lower', set())
                        logger.debug(f"使用书库文件缓存: {len(bookshelf_files)} 个文件")

            if not cache_valid:
                # 缓存过期或不存在，重新获取
                bookshelf_files = self._get_bookshelf_files()
                bookshelf_files_lower = {filename.lower() for filename in bookshelf_files}

                # 更新缓存
                self._bookshelf_cache = {
                    'time': current_time if current_time > 0 else time.time(),
                    'files': bookshelf_files,
                    'files_lower': bookshelf_files_lower
                }
                logger.debug(f"刷新书库文件缓存: {len(bookshelf_files)} 个文件")

            filtered_files = []

            # 调试信息：显示书库文件数量和当前目录文件数量
            logger.info(f"书库文件数量: {len(bookshelf_files)}, 当前目录文件数量: {len(files)}")
            logger.info(f"书库文件列表: {bookshelf_files}")

            for file_info in files:
                filename = file_info["name"]
                filename_lower = filename.lower()
                # 如果文件不在书库中，则保留（不区分大小写）
                if filename_lower not in bookshelf_files_lower:
                    filtered_files.append(file_info)
                    logger.info(f"✅ 文件 '{filename}' 不在书库中，保留")
                # else:
                #     logger.info(f"❌ 文件 '{filename}' 已在书库中，被过滤")

            logger.info(f"过滤后文件数量: {len(filtered_files)}")
            # logger.info(f"过滤后文件列表: {[f['name'] for f in filtered_files]}")
            return filtered_files
        except Exception as e:
            logger.error(f"过滤书库文件时出错: {e}", exc_info=True)
            return files
    
    def _search_files(self) -> None:
        """搜索文件"""
        try:
            # 获取搜索关键词和文件类型
            search_input = self.query_one("#file-explorer-search-input", Input)
            search_select = self.query_one("#file-explorer-search-select", Select)
            diff_switch = self.query_one("#file-explorer-diff-mode-switch", Switch)

            search_keyword = search_input.value.strip()

            # 处理下拉框值，确保正确处理NoSelection对象
            file_type_value = search_select.value
            if file_type_value is None or (hasattr(file_type_value, 'is_blank') and file_type_value.is_blank) or str(file_type_value) == 'Select.BLANK':
                file_type = "all"
            else:
                # 确保file_type_value是字符串类型
                file_type = str(file_type_value) if file_type_value else "all"

            diff_mode_enabled = diff_switch.value

            # 调试信息：显示搜索条件
            logger.info(f"🔍 搜索条件 - 关键词: '{search_keyword}', 文件类型: '{file_type}', 对比模式: {diff_mode_enabled}")
            
            # 如果既没有搜索关键词也没有选择特定文件类型，恢复显示所有文件
            if not search_keyword and file_type == "all" and not diff_mode_enabled:
                logger.debug("无搜索条件且对比模式关闭，恢复显示所有文件")
                self._load_file_list()
                return
            
            # 显示加载状态
            self._show_loading_animation(get_global_i18n().t("file_explorer.searching"))

            # 如果对比模式开启，优先处理对比模式
            if diff_mode_enabled:
                # 差异模式：获取当前目录所有文件，然后过滤掉已添加的书籍
                # 无论是否有搜索关键词或文件类型选择，差异模式都应该显示所有未添加的书籍
                logger.info("🔄 差异模式已开启，获取当前目录所有文件...")

                # 获取所有支持的文件
                all_files = self._get_all_files_in_current_directory()
                logger.info(f"📁 当前目录文件数量: {len(all_files)}")

                # 如果有搜索条件，先过滤搜索条件
                # 差异模式下只按关键词搜索，不按文件类型过滤
                if search_keyword:
                    logger.info(f"🔍 应用搜索条件 - 关键词: '{search_keyword}' (差异模式忽略文件类型)")
                    filtered_by_search = []
                    for file_info in all_files:
                        if self._match_search_criteria(file_info["name"], search_keyword, "all"):
                            filtered_by_search.append(file_info)
                    logger.info(f"搜索后文件数量: {len(filtered_by_search)}")
                    files_to_filter = filtered_by_search
                else:
                    # 差异模式无搜索条件，显示所有文件
                    logger.info(f"📁 差异模式无搜索条件，显示所有文件")
                    files_to_filter = all_files

                # 过滤掉书库中已存在的文件
                search_results = self._filter_files_not_in_bookshelf(files_to_filter)
                logger.info(f"✅ 过滤后文件数量（不在书架中）: {len(search_results)}")
            else:
                # 非对比模式，正常搜索
                search_results = self._perform_search(search_keyword, file_type)
                logger.debug(f"非对比模式：搜索后文件数量: {len(search_results)}")
            
            # 更新文件列表显示搜索结果
            self._update_file_list_with_search_results(search_results)
            
            # 隐藏加载状态
            self._hide_loading_animation()
            
            # 显示搜索结果统计
            if search_results:
                if diff_mode_enabled:
                    self.notify(f"找到 {len(search_results)} 个书库中不存在的文件", severity="information")
                else:
                    self.notify(f"找到 {len(search_results)} 个匹配的文件", severity="information")
            else:
                if diff_mode_enabled:
                    self.notify("没有找到书库中不存在的文件", severity="information")
                else:
                    self.notify("没有找到匹配的文件", severity="information")
                
        except Exception as e:
            logger.error(f"搜索文件失败: {e}")
            self._hide_loading_animation()
            self.notify(f"搜索失败: {e}", severity="error")
    
    def _perform_search(self, keyword: str, file_type: str) -> List[Dict[str, str]]:
        """
        执行文件搜索（基于当前文件列表）
        
        Args:
            keyword: 搜索关键词
            file_type: 文件类型筛选
            
        Returns:
            List[Dict[str, str]]: 搜索结果列表
        """
        search_results = []
        
        try:
            # 获取当前目录下的所有文件和目录
            items = os.listdir(self.current_path)
            
            for item in items:
                item_path = os.path.join(self.current_path, item)
                
                # 只处理文件，不处理目录
                if os.path.isfile(item_path):
                    # 检查文件是否匹配搜索条件
                    if self._match_search_criteria(item, keyword, file_type):
                        # 获取文件信息
                        ext = FileUtils.get_file_extension(item_path)
                        file_type_display = "book" if ext in self.file_extensions else "file"
                        
                        search_results.append({
                            "name": item,
                            "path": item_path,
                            "type": file_type_display,
                            "display": f"📖 {item}" if file_type_display == "book" else f"📄 {item}",
                            "directory": "."
                        })
                        
        except (PermissionError, OSError) as e:
            logger.warning(f"搜索过程中无法访问目录: {e}")
        
        return search_results
    
    def _match_search_criteria(self, filename: str, keyword: str, file_type: str) -> bool:
        """
        检查文件是否匹配搜索条件
        
        Args:
            filename: 文件名
            keyword: 搜索关键词
            file_type: 文件类型筛选
            
        Returns:
            bool: 是否匹配
        """
        # 检查文件类型筛选
        if file_type != "all":
            ext = FileUtils.get_file_extension(filename).lower()
            if ext != file_type.lower():
                return False
        
        # 检查文件名是否包含关键词（不区分大小写）
        if keyword and keyword.lower() not in filename.lower():
            return False
        
        return True
    
    def _update_file_list_with_search_results(self, search_results: List[Dict[str, str]]) -> None:
        """
        使用搜索结果更新文件列表
        
        Args:
            search_results: 搜索结果列表
        """
        file_list = self.query_one("#file-list", ListView)
        file_list.clear()
        self.file_items = []
        
        if search_results:
            # 添加搜索结果到列表
            for result in search_results:
                list_item = ListItem(Label(result["display"]))
                list_item.data = result
                file_list.append(list_item)
                self.file_items.append(result)
            
            # 默认选中第一项
            if len(search_results) > 0:
                self.selected_file_index = 0
                if search_results[0]["type"] in ["book", "file"]:
                    self.selected_file = search_results[0]["path"]
                else:
                    self.selected_file = None
        else:
            # 没有搜索结果
            empty_item = ListItem(Label(get_global_i18n().t("file_explorer.no_search_results")))
            file_list.append(empty_item)
            self.file_items = []
            self.selected_file = None
            self.selected_file_index = None
        
        # 更新状态信息
        self._update_search_status(len(search_results))
    
    def _update_search_status(self, result_count: int) -> None:
        """更新搜索状态显示"""
        status_info = self.query_one("#status-info", Static)
        search_input = self.query_one("#file-explorer-search-input", Input)
        search_select = self.query_one("#file-explorer-search-select", Select)
        
        search_keyword = search_input.value.strip()
        
        # 处理下拉框值，确保正确处理NoSelection对象
        file_type_value = search_select.value
        if file_type_value is None or (hasattr(file_type_value, 'is_blank') and file_type_value.is_blank):
            file_type = "all"
        else:
            # 确保file_type_value是字符串类型
            file_type = str(file_type_value) if file_type_value else "all"
        
        diff_switch = self.query_one("#file-explorer-diff-mode-switch", Switch)
        diff_mode_enabled = diff_switch.value
        
        # 如果正在进行搜索（有搜索关键词或选择了特定文件类型）
        if search_keyword or file_type != "all":
            status_info.update(f"{get_global_i18n().t("file_explorer.search_results")}: {result_count}")
        else:
            # 如果没有搜索条件，显示正常状态
            try:
                file_count = len([f for f in os.listdir(self.current_path) if os.path.isfile(os.path.join(self.current_path, f))])
                dir_count = len([d for d in os.listdir(self.current_path) if os.path.isdir(os.path.join(self.current_path, d))])
                status_info.update(f"{get_global_i18n().t("file_explorer.file")}: {file_count} | {get_global_i18n().t("file_explorer.path")}: {dir_count}")
            except (PermissionError, OSError):
                status_info.update(get_global_i18n().t("file_explorer.cannot_visit"))
    
    @on(Button.Pressed, "#file-explorer-search-btn")
    def on_search_button_pressed(self, event: Button.Pressed) -> None:
        """搜索按钮点击事件"""
        self._search_files()
    
    @on(Input.Submitted, "#file-explorer-search-input")
    def on_search_input_submitted(self, event: Input.Submitted) -> None:
        """搜索输入框回车事件"""
        self._search_files()
    
    @on(Select.Changed, "#file-explorer-search-select")
    def on_search_select_changed(self, event: Select.Changed) -> None:
        """搜索选择框改变事件"""
        # 当文件类型选择改变时，立即执行搜索（支持独立使用）
        self._search_files()
    
    @on(Switch.Changed, "#file-explorer-diff-mode-switch")
    def on_diff_mode_switch_changed(self, event: Switch.Changed) -> None:
        """对比模式开关改变事件"""
        # 当对比模式开关改变时，清除缓存并执行搜索
        if event.value:
            # 开启差异模式：强制清除缓存
            self._bookshelf_cache = None
            self._directory_cache.clear()
            self.logger.info("🔄 差异模式已开启，已清除所有缓存")
        self._search_files()

    @on(RefreshBookshelfMessage)
    def handle_refresh_message(self, message: RefreshBookshelfMessage) -> None:
        """接收书架刷新消息"""
        self.logger.info("🔄 接收到书架刷新消息，正在重新加载书籍数据...")
        try:
            # 1. 清除书库文件缓存 - 强制设置为None确保缓存失效
            self._bookshelf_cache = None
            self.logger.info("✅ 已清除书库文件缓存")

            # 2. 重新加载书架数据
            self.bookshelf._load_books()
            bookshelf_files = self._get_bookshelf_files()
            self.logger.info(f"✅ 书架数据已重新加载，当前书籍数量: {len(self.bookshelf.books)}")
            self.logger.info(f"📚 书架文件列表 ({len(bookshelf_files)} 个): {bookshelf_files}")

            # 3. 如果差异模式开启，重新搜索文件列表
            try:
                diff_switch = self.query_one("#file-explorer-diff-mode-switch", Switch)
                diff_mode_enabled = diff_switch.value
                if diff_mode_enabled:
                    self.logger.info("🔄 差异模式已开启，正在重新搜索文件列表...")
                    self._search_files()
            except Exception as e:
                self.logger.warning(f"⚠️  重新搜索文件列表失败: {e}")
        except Exception as e:
            self.logger.error(f"❌ 处理书架刷新消息时出错: {e}", exc_info=True)

    @on(ListView.Selected)
    def on_file_list_selected(self, message: ListView.Selected) -> None:
        """文件列表选择事件 - 多选处理"""
        try:
            if message.list_view.id == "file-list":
                if not self.file_items:
                    logger.debug("文件列表为空，无法选择")
                    return
                
                # 获取选中的项索引
                file_list = self.query_one("#file-list", ListView)
                selected_index = file_list.index
                
                if selected_index is None or selected_index < 0 or selected_index >= len(self.file_items):
                    logger.debug(f"无效的选中索引: {selected_index}")
                    return
                
                selected_item = self.file_items[selected_index]
                
                # 检查是否多选
                if self.multiple:
                    # 多选模式
                    if selected_index in self.selected_file_indices:
                        # 如果已经选中，取消选中
                        self.selected_file_indices.remove(selected_index)
                        if selected_item["path"] in self.selected_files:
                            self.selected_files.remove(selected_item["path"])
                        logger.debug(f"取消选中文件: {selected_item['name']}")
                    else:
                        # 如果未选中，添加到选中集合
                        self.selected_file_indices.add(selected_index)
                        self.selected_files.add(selected_item["path"])
                        logger.debug(f"选中文件: {selected_item['name']}")
                    
                    # 多选模式下不进入目录
                    logger.debug(f"多选模式: 当前选中 {len(self.selected_files)} 个文件")
                    
                    # 更新文件列表的视觉状态
                    self._update_file_list_visual_state()
                    
                else:
                    # 单选模式
                    self.selected_file_index = selected_index
                    if selected_item["type"] in ["book", "file"]:
                        self.selected_file = selected_item["path"]
                        logger.debug(f"单选模式选中文件: {selected_item['name']}")
                    else:
                        self.selected_file = None
                        logger.debug(f"选中了非文件类型: {selected_item['type']}")
                    
                    # 清空多选集合
                    self.selected_file_indices.clear()
                    self.selected_files.clear()
                    logger.debug("清空多选集合，进入单选模式")
                    
                    # 更新文件列表的视觉状态
                    self._update_file_list_visual_state()
                    
                    # 如果选中的是目录，直接进入该目录
                    if selected_item["type"] == "directory":
                        logger.debug(f"进入目录: {selected_item['path']}")
                        self._navigate_to_path(selected_item["path"])
                        return
                
                # 更新选择状态显示
                self._update_selection_status()
                
        except Exception as e:
            logger.error(f"处理文件列表选择事件失败: {e}")
    
    def _update_file_list_visual_state(self) -> None:
        """更新文件列表的视觉状态，显示选中状态"""
        try:
            file_list = self.query_one("#file-list", ListView)
            
            # 遍历所有文件项，更新显示
            for i, list_item in enumerate(file_list.children):
                if i < len(self.file_items):
                    item = self.file_items[i]
                    
                    # 检查是否在多选集合中
                    if i in self.selected_file_indices:
                        # 选中状态：添加选中标记
                        new_display = f"✅ {item['display']}"
                    elif i == self.selected_file_index:
                        # 单选选中状态
                        new_display = f"▶️ {item['display']}"
                    else:
                        # 未选中状态
                        new_display = item['display']
                    
                    # 更新显示文本
                    label = list_item.query_one(Label)
                    if label:
                        label.update(new_display)
                        
        except Exception as e:
            logger.error(f"更新文件列表视觉状态失败: {e}")

    def on_key(self, event: events.Key) -> None:       
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

# 文件资源管理器屏幕类定义结束