"""
书籍网站编辑对话框
"""

from typing import Dict, Any, Optional, List
from urllib.parse import unquote
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label, Input, Select, Switch
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.utils.logger import get_logger
from src.spiders import get_parser_options
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.config.config_manager import ConfigManager

logger = get_logger(__name__)

class NovelSiteDialog(ModalScreen[Optional[Dict[str, Any]]]):

    """书籍网站编辑对话框"""
    
    CSS_PATH = "../styles/novel_site_overrides.tcss"

    # 使用 BINDINGS：Enter 保存，Esc 取消
    BINDINGS = [
        ("enter", "save", get_global_i18n().t('common.save')),
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
    ]
    
    # 解析器到URL模式的映射表
    PARSER_URL_PATTERNS = {
        # CMS类型
        'cms_t1_v2': 'vue.php?act=detail&id={novel_id}',
        'cms_t2_v2': 'index.php/art/detail/id/{novel_id}.html',
        'cms_t3_v2': 'article/{novel_id}.html',
        'cms_t4_v2': 'novel/{novel_id}.html',
        'cms_t5_v2': '{novel_id}/',
        'cms_t6_v2': 'article.php?id={novel_id}',
        
        # 特殊网站
        'feiku6_v2': 'book/{novel_id}.html',
        'kunnu8_v2': '{novel_id}/',
        'luoxiadushu_v2': '{novel_id}/',
        'aaread_v2': 'book/{novel_id}#Catalog',
        'xxread_v2': 'book/{novel_id}.html',
        'migu_v2': 'book/{novel_id}.html',
        'photo_gram_v2': 'html/{novel_id}.html',
        'po18_v2': 'novel/{novel_id}.html',
        'haijbookx_v2': 'book/{novel_id}.html',
        'fsnovel_v2': '{novel_id}/',
        'po18gg_v2': 'novel/{novel_id}.html',
        'po18rr_v2': 'novel/{novel_id}.html',
        'chanjishi_v2': 'index.php/art/detail/id/{novel_id}/page/1.html',
        'zxcms_v2': 'show/{novel_id}.html',
        
        # 默认模式（不需要设置，会使用 /b/{novel_id}）
        'txtxi_v2': '',
        '91porna_v2': '',
        'crxs_v2': '',
    }
    
    def __init__(self, theme_manager: ThemeManager, novel_site: Optional[Dict[str, Any]] = None):
        """
        初始化书籍网站对话框
        
        Args:
            theme_manager: 主题管理器
            novel_site: 书籍网站信息，如果为None则为添加模式
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.novel_site = novel_site or {}
        self.is_edit_mode = novel_site is not None
        
        # 设置标题 - 处理i18n未初始化的情况
        try:
            if self.is_edit_mode:
                self.title = get_global_i18n().t('novel_site_dialog.edit_title')
            else:
                self.title = get_global_i18n().t('novel_site_dialog.add_title')
        except RuntimeError:
            # 如果i18n未初始化，使用默认标题
            if self.is_edit_mode:
                self.title = "编辑书籍网站"
            else:
                self.title = "添加书籍网站"
    
    def compose(self) -> ComposeResult:
        """
        组合书籍网站对话框界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Vertical(
                Label(self.title or "", id="novel-site-dialog-title", classes="section-title"),

                # 可滚动的中部内容
                Vertical(
                    # 网站基本信息
                    Vertical(
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.site_name'), id="site-name-label"),
                            Input(
                                placeholder=get_global_i18n().t('novel_site_dialog.site_name_placeholder'),
                                id="site-name-input"
                            ),
                            id="site-name-container", classes="form-row"
                        ),
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.site_url'), id="site-url-label"),
                            Input(
                                placeholder=get_global_i18n().t('novel_site_dialog.site_url_placeholder'),
                                id="site-url-input"
                            ),
                            id="site-url-container", classes="form-row"
                        ),
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.storage_folder'), id="storage-folder-label"),
                            Input(
                                placeholder=get_global_i18n().t('novel_site_dialog.storage_folder_placeholder'),
                                id="storage-folder-input"
                            ),
                            id="storage-folder-container", classes="form-row"
                        ),
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.tags'), id="tags-label"),
                            Input(
                                placeholder=get_global_i18n().t('novel_site_dialog.tags_placeholder'),
                                id="tags-input"
                            ),
                            id="tags-container", classes="form-row"
                        ),
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.book_id_example'), id="book-id-example-label"),
                            Input(
                                placeholder=get_global_i18n().t('novel_site_dialog.book_id_example_placeholder'),
                                id="book-id-example-input"
                            ),
                            id="book-id-example-container", classes="form-row"
                        ),
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.url_pattern'), id="url-pattern-label"),
                            Input(
                                placeholder=get_global_i18n().t('novel_site_dialog.url_pattern_placeholder'),
                                id="url-pattern-input"
                            ),
                            id="url-pattern-container", classes="form-row"
                        ),
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.rating'), id="rating-label"),
                            Select(
                                [
                                    ("☆☆☆☆☆", 0),
                                    ("★☆☆☆☆", 1),
                                    ("★★☆☆☆", 2),
                                    ("★★★☆☆", 3),
                                    ("★★★★☆", 4),
                                    ("★★★★★", 5)
                                ],
                                id="rating-select",
                                allow_blank=False
                            ),
                            id="rating-container", classes="form-row"
                        ),
                        id="basic-info-container"
                    ),

                    # 解析器设置
                    Vertical(
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.parser'), id="parser-label"),
                            Select(
                                get_parser_options() or [("", get_global_i18n().t('novel_site_dialog.no_parser'))],
                                id="parser-select"
                            ),
                            id="parser-container", classes="form-row"
                        ),
                        id="parser-settings-container"
                    ),

                    # 代理设置
                    Vertical(
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.enable_proxy'), id="enable-proxy-label"),
                            Switch(id="enable-proxy"),
                            id="proxy-enable-container", classes="form-row"
                        ),
                        id="proxy-settings-container"
                    ),

                    # 选择书籍设置
                    Vertical(
                        Horizontal(
                            Label(get_global_i18n().t('novel_site_dialog.enable_selectable'), id="enable-selectable-label"),
                            Switch(id="enable-selectable", value=True),  # 默认开启
                            id="selectable-enable-container", classes="form-row"
                        ),
                        id="selectable-settings-container"
                    ),
                    id="novel-site-dialog-body", classes="scroll-y"
                ),

                # 操作按钮（底部固定）
                Horizontal(
                    Button(get_global_i18n().t('novel_site_dialog.save'), id="save-btn", variant="primary"),
                    Button(get_global_i18n().t('novel_site_dialog.cancel'), id="cancel-btn"),
                    id="novel-site-dialog-buttons", classes="btn-row"
                ),

                # 状态信息
                Label("", id="novel-site-dialog-status"),
                id="novel-site-dialog-container"
            )
        )
    
    def on_mount(self) -> None:
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        
        """对话框挂载时的回调"""
        # 应用主题
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            # 如果应用主题失败（比如在没有应用上下文的情况下），忽略错误
            pass
        
        # 延迟填充现有数据，确保DOM元素已经创建
        # 在所有模式下都调用，确保默认值正确设置
        self.call_after_refresh(self._fill_existing_data)
    
    def _fill_existing_data(self) -> None:
        """填充现有数据"""
        # 网站名称
        name_input = self.query_one("#site-name-input", Input)
        name_input.value = self.novel_site.get("name", "")
        
        # 网站URL
        url_input = self.query_one("#site-url-input", Input)
        url_input.value = self.novel_site.get("url", "")
        
        # 存储文件夹
        folder_input = self.query_one("#storage-folder-input", Input)
        # 如果是编辑模式，使用原有的存储文件夹值
        # 如果是添加模式，从系统配置文件中获取默认值
        if self.is_edit_mode:
            folder_input.value = self.novel_site.get("storage_folder", "")
        else:
            # 从系统配置文件中获取paths.library的值作为默认值
            try:
                config_manager = ConfigManager.get_instance()
                config = config_manager.get_config()
                library_path = config.get("paths", {}).get("library", "")
                folder_input.value = library_path
            except Exception as e:
                logger.error(f"获取配置路径失败: {e}")
                folder_input.value = ""
        
        # 标签
        tags_input = self.query_one("#tags-input", Input)
        tags_input.value = self.novel_site.get("tags", "")
        
        # 书籍ID样例
        book_id_example_input = self.query_one("#book-id-example-input", Input)
        book_id_example = self.novel_site.get("book_id_example", "")
        # 对书籍ID样例进行URL解码，避免显示乱码
        decoded_book_id_example = unquote(book_id_example) if book_id_example else ""
        book_id_example_input.value = decoded_book_id_example
        
        # 解析器 - 使用解析器文件名作为值
        parser_select = self.query_one("#parser-select", Select)
        parser_value = self.novel_site.get("parser", "")  # 默认为空
        
        # 处理Select.BLANK值，将其转换为空字符串
        if parser_value in ["Select.BLANK", "SelectBLANK"]:
            parser_value = ""
        
        # 设置解析器值，空字符串使用clear()方法
        # 先检查值是否在可用选项中，避免无效值导致崩溃
        available_options = [option[0] for option in get_parser_options()]
        if parser_value and parser_value in available_options:
            parser_select.value = parser_value
        else:
            parser_select.clear()  # 清除选择
        
        # 代理设置
        proxy_checkbox = self.query_one("#enable-proxy", Switch)
        proxy_checkbox.value = self.novel_site.get("proxy_enabled", False)
        
        # 选择书籍设置
        selectable_checkbox = self.query_one("#enable-selectable", Switch)
        selectable_checkbox.value = self.novel_site.get("selectable_enabled", True)  # 默认开启
        
        # 星级评分
        rating_select = self.query_one("#rating-select", Select)
        rating_value = self.novel_site.get("rating", 2)  # 默认2星
        if rating_value is not None:
            rating_select.value = rating_value
        else:
            rating_select.value = 2  # 默认2星
        
        # URL模式
        url_pattern_input = self.query_one("#url-pattern-input", Input)
        url_pattern_value = self.novel_site.get("url_pattern", "")
        url_pattern_input.value = url_pattern_value
        
        # 如果没有URL模式且已选择解析器，自动填充
        if not url_pattern_value and parser_value:
            self._auto_fill_url_pattern(parser_value)
    
    # Actions for BINDINGS
    def action_save(self) -> None:
        self._save_novel_site()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "save-btn":
            self._save_novel_site()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """
        选择框变化时的回调
        
        Args:
            event: 选择框变化事件
        """
        if event.select.id == "parser-select":
            parser_value = str(event.value) if event.value else ""
            self._auto_fill_url_pattern(parser_value)
    
    def _auto_fill_url_pattern(self, parser_value: str) -> None:
        """
        根据解析器自动填充URL模式
        
        Args:
            parser_value: 解析器值
        """
        try:
            url_pattern_input = self.query_one("#url-pattern-input", Input)
            
            # 从映射表中获取URL模式
            url_pattern = self.PARSER_URL_PATTERNS.get(parser_value, "")
            
            # 如果找到模式且当前输入框为空，则自动填充
            if url_pattern and not url_pattern_input.value.strip():
                url_pattern_input.value = url_pattern
        except Exception as e:
            logger.error(f"自动填充URL模式失败: {e}")
    
    def _save_novel_site(self) -> None:
        """保存书籍网站信息"""
        # 获取输入值
        name_input = self.query_one("#site-name-input", Input)
        url_input = self.query_one("#site-url-input", Input)
        folder_input = self.query_one("#storage-folder-input", Input)
        tags_input = self.query_one("#tags-input", Input)
        book_id_example_input = self.query_one("#book-id-example-input", Input)
        url_pattern_input = self.query_one("#url-pattern-input", Input)
        parser_select = self.query_one("#parser-select", Select)
        proxy_checkbox = self.query_one("#enable-proxy", Switch)
        selectable_checkbox = self.query_one("#enable-selectable", Switch)
        rating_select = self.query_one("#rating-select", Select)
        
        # 验证必填字段
        if not name_input.value.strip():
            self._update_status(get_global_i18n().t('novel_site_dialog.enter_site_name'))
            return  # 验证失败，停留在当前页面
        
        if not url_input.value.strip():
            self._update_status(get_global_i18n().t('novel_site_dialog.enter_site_url'))
            return  # 验证失败，停留在当前页面
        
        # 存储文件夹现在是可选字段，不需要验证
        
        # 验证URL格式
        # if not self._is_valid_url(url_input.value.strip()):
        #     self._update_status(get_global_i18n().t('novel_site_dialog.invalid_url'))
        #     return  # 验证失败，停留在当前页面
        
        # 获取解析器值 - 使用解析器文件名
        parser_value = ""  # 默认为空
        if parser_select.value is not None and parser_select.value != "Select.BLANK":
            # 获取选中的解析器文件名，并清理"解析器"字样
            parser_value = str(parser_select.value)
            # 清理解析器名称，只保留文件名部分
            parser_value = self._clean_parser_name(parser_value)
        
        # 获取星级评分值
        rating_value = 2  # 默认值
        if rating_select.value is not None:
            try:
                rating_value = int(rating_select.value)
            except (ValueError, TypeError):
                rating_value = 2  # 如果转换失败，使用默认值
        
        # 构建书籍网站信息
        novel_site_info = {
            "name": name_input.value.strip(),
            "url": url_input.value.strip(),
            "storage_folder": folder_input.value.strip(),
            "tags": tags_input.value.strip(),
            "book_id_example": book_id_example_input.value.strip(),
            "url_pattern": url_pattern_input.value.strip(),
            "parser": parser_value,
            "proxy_enabled": proxy_checkbox.value,
            "selectable_enabled": selectable_checkbox.value,
            "rating": rating_value
        }
        
        # 如果是编辑模式，保留原有的ID
        if self.is_edit_mode and "id" in self.novel_site:
            novel_site_info["id"] = self.novel_site["id"]
        
        # 显示保存成功状态
        self._update_status(get_global_i18n().t('novel_site_dialog.save_success'), "success")
        
        # 延迟关闭对话框，让用户看到成功消息
        def delayed_dismiss():
            self.dismiss(novel_site_info)
        
        # 1秒后关闭对话框
        self.set_timer(1.0, delayed_dismiss)
    
    def _is_valid_url(self, url: str) -> bool:
        """验证URL格式"""
        import re
        # 简单的URL验证正则表达式
        url_pattern = re.compile(
            r'^(https?://)?'  # http:// or https://
            r'(([A-Z0-9][A-Z0-9_-]*)(\.[A-Z0-9][A-Z0-9_-]*)+)'  # domain
            r'(:\d+)?'  # optional port
            r'(/.*)?$',  # path
            re.IGNORECASE
        )
        return bool(url_pattern.match(url))
    
    def _clean_parser_name(self, parser_name: str) -> str:
        """
        清理解析器名称，确保只保留文件名部分
        
        Args:
            parser_name: 原始解析器名称
            
        Returns:
            str: 清理后的解析器文件名
        """
        if not parser_name:
            return ""
        
        # 移除"解析器"字样
        cleaned_name = parser_name.replace("解析器", "").strip()
        
        # 如果清理后为空，返回原始值
        if not cleaned_name:
            return parser_name
        
        # 移除可能的空格和特殊字符，只保留字母数字和下划线
        import re
        cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '', cleaned_name)
        
        # 如果清理后为空，返回原始值
        if not cleaned_name:
            return parser_name
        
        return cleaned_name
    
    def _update_status(self, message: str, severity: str = "error") -> None:
        """更新状态信息"""
        status_label = self.query_one("#novel-site-dialog-status", Label)
        status_label.update(message)
        
        # 根据严重程度设置样式
        if severity == "success":
            status_label.styles.color = "green"
        elif severity == "error":
            status_label.styles.color = "red"
        else:
            status_label.styles.color = "blue"
    
    def on_key(self, event: events.Key) -> None:
        """已由 BINDINGS 处理，避免重复触发"""
        pass