"""
文件选择器对话框，用于选择单个或多个文件
"""

import os
from typing import Optional, List, Set
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static
from textual.validation import Validator, ValidationResult
from textual import events

from src.locales.i18n import I18n
from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.utils.file_utils import FileUtils
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation

class FilePathValidator(Validator):
    """文件路径验证器"""
    
    def __init__(self, file_extensions: Optional[List[str]] = None):
        """
        初始化文件路径验证器
        
        Args:
            file_extensions: 允许的文件扩展名列表
        """
        super().__init__()
        self.file_extensions = file_extensions
        
    def validate(self, value: str) -> ValidationResult:
        """
        验证文件路径
        
        Args:
            value: 文件路径
            
        Returns:
            ValidationResult: 验证结果
        """
        if not value.strip():
            return self.failure(get_global_i18n().t("empty_path"))
            
        if not os.path.exists(value):
            return self.failure(get_global_i18n().t("not_exists"))
            
        if not os.path.isfile(value):
            return self.failure(get_global_i18n().t("path_not_file"))
            
        # 检查文件扩展名
        if self.file_extensions:
            file_ext = FileUtils.get_file_extension(value)
            if file_ext not in self.file_extensions:
                return self.failure(f"{get_global_i18n}: {file_ext}")
                
        return self.success()


class FileChooserDialog(ModalScreen[Optional[List[str]]]):
    """文件选择器对话框"""
    
    def __init__(self, theme_manager: ThemeManager, 
                 title: str, placeholder: str, multiple: bool = False,
                 file_extensions: Optional[List[str]] = None):
        """
        初始化文件选择器对话框
        
        Args:
            theme_manager: 主题管理器
            title: 对话框标题
            placeholder: 输入框占位符
            multiple: 是否允许多选
            file_extensions: 允许的文件扩展名列表
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.title = title
        self.placeholder = placeholder
        self.multiple = multiple
        self.file_extensions = file_extensions
        self.selected_files: Set[str] = set()
        
    def compose(self) -> ComposeResult:
        """组合对话框界面"""
        with Vertical(id="file-chooser-dialog"):
            yield Label(self.title or "", id="file-chooser-title")
            
            # 文件路径输入区域
            with Horizontal(id="file-input-section"):
                yield Input(
                    placeholder=self.placeholder, 
                    id="file-input",
                    validators=[FilePathValidator(self.file_extensions)]
                )
                if self.multiple:
                    yield Button(get_global_i18n().t("common.add"), id="add-file-btn")
            
            # 已选择文件列表（多选模式）
            if self.multiple:
                yield Static("", id="selected-files-list")
            
            # 按钮区域
            with Horizontal(id="file-chooser-buttons"):
                yield Button(get_global_i18n().t("common.select"), id="select-btn")
                yield Button(get_global_i18n().t("common.cancel"), id="cancel-btn")
    
    def on_mount(self) -> None:
        """挂载时应用主题"""
        self.theme_manager.apply_theme_to_screen(self)
        
    def _validate_file_path(self, value: str) -> bool:
        """
        验证文件路径
        
        Args:
            value: 文件路径
            
        Returns:
            bool: 是否有效
        """
        if not value.strip():
            return False
            
        if not os.path.exists(value):
            return False
            
        if not os.path.isfile(value):
            return False
            
        # 检查文件扩展名
        if self.file_extensions:
            file_ext = FileUtils.get_file_extension(value)
            if file_ext not in self.file_extensions:
                return False
                
        return True
        
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击处理"""
        if event.button.id == "select-btn":
            if self.multiple and self.selected_files:
                self.dismiss(list(self.selected_files))
            elif not self.multiple:
                file_input = self.query_one("#file-input", Input)
                file_path = file_input.value.strip()
                if self._validate_file_path(file_path):
                    self.dismiss([file_path])
                else:
                    self.notify(get_global_i18n().t("bookshelf.invalid_file"), severity="error")
            else:
                self.notify(get_global_i18n().t("bookshelf.no_files_selected"), severity="warning")
                
        elif event.button.id == "add-file-btn":
            file_input = self.query_one("#file-input", Input)
            file_path = file_input.value.strip()
            
            if self._validate_file_path(file_path):
                if file_path not in self.selected_files:
                    self.selected_files.add(file_path)
                    self._update_selected_files_list()
                    file_input.value = ""
                else:
                    self.notify(get_global_i18n().t("bookshelf.file_already_selected"), severity="warning")
            else:
                self.notify(get_global_i18n().t("bookshelf.invalid_file"), severity="error")
                
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
            
    def _update_selected_files_list(self) -> None:
        """更新已选择文件列表"""
        if self.multiple:
            files_list = self.query_one("#selected-files-list", Static)
            if self.selected_files:
                files_text = "\n".join([
                    f"• {os.path.basename(file)}" for file in self.selected_files
                ])
                files_list.update(files_text)
            else:
                files_list.update("")

