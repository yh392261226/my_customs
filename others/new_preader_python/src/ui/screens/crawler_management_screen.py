"""
爬取管理屏幕
"""

from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Label, DataTable, Input, Select, Link, Header, Footer, LoadingIndicator
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n, t, init_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger
from src.ui.dialogs.note_dialog import NoteDialog
from src.ui.dialogs.select_books_dialog import SelectBooksDialog

logger = get_logger(__name__)

class CrawlerManagementScreen(Screen[None]):
    """爬取管理屏幕"""
    
    CSS_PATH = ["../styles/utilities.tcss", "../styles/crawler_management_overrides.tcss"]
    TITLE: ClassVar[Optional[str]] = None
    
    def __init__(self, theme_manager: ThemeManager, novel_site: Dict[str, Any]):
        """
        初始化爬取管理屏幕
        
        Args:
            theme_manager: 主题管理器
            novel_site: 书籍网站信息
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.novel_site = novel_site
        self.crawler_history = []  # 爬取历史记录
        self.current_page = 1
        self.items_per_page = 10
        self.db_manager = DatabaseManager()  # 数据库管理器
        self.is_crawling = False  # 爬取状态标志
        # 当前正在爬取的ID（用于状态显示）
        self.current_crawling_id: Optional[str] = None
        self.loading_animation = None  # 加载动画组件
        self.loading_indicator = None  # 原生 LoadingIndicator 引用
        self.is_mounted_flag = False  # 组件挂载标志
        self.title = get_global_i18n().t('crawler.title')

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限（兼容单/多用户）"""
        try:
            db_manager = self.db_manager if hasattr(self, "db_manager") else DatabaseManager()
            # 获取当前用户ID
            current_user_id = getattr(self.app, 'current_user_id', None)
            if current_user_id is None:
                # 如果没有当前用户，检查是否是多用户模式
                if not getattr(self.app, 'multi_user_enabled', False):
                    # 单用户模式默认允许所有权限
                    return True
                else:
                    # 多用户模式但没有当前用户，默认拒绝
                    return False
            # 传入用户ID与权限键
            return db_manager.has_permission(current_user_id, permission_key)  # type: ignore[misc]
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def compose(self) -> ComposeResult:
        """
        组合爬取管理屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Header()
        yield Container(
            Vertical(
                # Label(f"{get_global_i18n().t('crawler.title')} - {self.novel_site['name']}", id="crawler-title", classes="section-title"),
                Link(f"{self.novel_site['url']}", url=f"{self.novel_site['url']}", id="crawler-url", tooltip=f"{get_global_i18n().t('crawler.click_me')}"),
                Label(f"{get_global_i18n().t('crawler.book_id_example')}: {self.novel_site.get('book_id_example', '')}", id="book-id-example-label"),

                # 顶部操作按钮（固定）
                Horizontal(
                    Button(get_global_i18n().t('crawler.open_browser'), id="open-browser-btn"),
                    Button(get_global_i18n().t('crawler.view_history'), id="view-history-btn"),
                    Button(get_global_i18n().t('crawler.note'), id="note-btn"),
                    Button(get_global_i18n().t('crawler.back'), id="back-btn"),
                    id="crawler-buttons", classes="btn-row"
                ),

                # 中部可滚动区域：输入区 + 历史表格
                Vertical(
                    # 小说ID输入区域
                    Vertical(
                        Horizontal(
                            # 根据书籍网站的"是否支持选择书籍"设置显示选择书籍按钮
                            *([Button(get_global_i18n().t('crawler.select_books'), id="choose-books-btn")] if self.novel_site.get("selectable_enabled", True) else []),
                            Input(placeholder=get_global_i18n().t('crawler.novel_id_placeholder_multi'), id="novel-id-input"),
                            Button(get_global_i18n().t('crawler.start_crawl'), id="start-crawl-btn", variant="primary"),
                            Button(get_global_i18n().t('crawler.stop_crawl'), id="stop-crawl-btn", variant="error", disabled=True),
                            id="novel-id-container", classes="form-row"
                        ),
                        id="novel-id-section"
                    ),

                    # 爬取历史区域（不包含分页控件）
                    Vertical(
                        Label(get_global_i18n().t('crawler.crawl_history'), id="crawl-history-title"),
                        DataTable(id="crawl-history-table"),
                        id="crawl-history-section"
                    ),
                    id="crawler-scroll", classes="scroll-y"
                ),

                # 分页控件（底部固定，始终可见）
                Horizontal(
                    Button(get_global_i18n().t('crawler.prev_page'), id="prev-page-btn"),
                    Label("", id="page-info"),
                    Button(get_global_i18n().t('crawler.next_page'), id="next-page-btn"),
                    id="pagination-controls", classes="form-row"
                ),

                # 状态信息
                Label("", id="crawler-status"),

                # 加载动画区域
                Static("", id="loading-animation"),

                # 快捷键状态栏
                # Horizontal(
                #     Label(get_global_i18n().t('crawler.shortcut_o'), id="shortcut-o"),
                #     Label(get_global_i18n().t('crawler.shortcut_r'), id="shortcut-r"),
                #     Label(get_global_i18n().t('crawler.shortcut_s'), id="shortcut-s"),
                #     Label(get_global_i18n().t('crawler.shortcut_v'), id="shortcut-v"),
                #     Label(get_global_i18n().t('crawler.shortcut_b'), id="shortcut-b"),
                #     Label(get_global_i18n().t('crawler.shortcut_p'), id="shortcut-p"),
                #     Label(get_global_i18n().t('crawler.shortcut_n'), id="shortcut-n"),
                #     Label(get_global_i18n().t('crawler.shortcut_esc'), id="shortcut-esc"),
                #     id="shortcuts-bar", classes="status-bar"
                # ),
                id="crawler-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 设置挂载标志
        self.is_mounted_flag = True
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 权限提示与按钮状态
        try:
            start_btn = self.query_one("#start-crawl-btn", Button)
            if not getattr(self.app, "has_permission", lambda k: True)("crawler.run"):
                start_btn.disabled = True
                self._update_status(get_global_i18n().t('crawler.np_crawler'), "warning")
        except Exception:
            pass
        
        # 初始化数据表
        table = self.query_one("#crawl-history-table", DataTable)
        table.add_columns(
            get_global_i18n().t('crawler.sequence'),  # 序号列
            get_global_i18n().t('crawler.novel_id'),
            get_global_i18n().t('crawler.novel_title'),
            get_global_i18n().t('crawler.crawl_time'),
            get_global_i18n().t('crawler.status'),
            get_global_i18n().t('crawler.file_path'),
            get_global_i18n().t('crawler.view_file'),
            get_global_i18n().t('crawler.read_book'),
            get_global_i18n().t('crawler.delete_file'),
            get_global_i18n().t('crawler.delete_record'),
            get_global_i18n().t('crawler.view_reason')  # 新增查看原因列
        )
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        # 初始化加载动画
        self._initialize_loading_animation()
        
        # 加载爬取历史
        self._load_crawl_history()

        # 自动聚焦小说ID输入框
        self.query_one("#novel-id-input", Input).focus()
    
    def _load_crawl_history(self) -> None:
        """加载爬取历史记录"""
        try:
            # 从数据库加载爬取历史
            site_id = self.novel_site.get('id')
            if site_id:
                db_history = self.db_manager.get_crawl_history_by_site(site_id, limit=100)
                
                # 转换数据库格式为显示格式
                self.crawler_history = []
                for item in db_history:
                    # 转换状态显示文本
                    status_text = get_global_i18n().t('crawler.status_success') if item['status'] == 'success' else get_global_i18n().t('crawler.status_failed')
                    
                    # 转换时间格式
                    try:
                        from datetime import datetime
                        crawl_time = datetime.fromisoformat(item['crawl_time']).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        crawl_time = item['crawl_time']
                    
                    self.crawler_history.append({
                        "id": item['id'],  # 保存数据库记录ID
                        "novel_id": item['novel_id'],
                        "novel_title": item['novel_title'],
                        "crawl_time": crawl_time,
                        "status": status_text,
                        "file_path": item['file_path'] or "",
                        "error_message": item.get('error_message', '')  # 保存错误信息
                    })
            else:
                self.crawler_history = []
        except Exception as e:
            logger.error(f"加载爬取历史记录失败: {e}")
            self.crawler_history = []
        
        # 更新数据表
        self._update_history_table()
    
    def _update_history_table(self) -> None:
        """更新历史记录表格"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟更新历史记录表格")
                # 延迟100ms后重试
                self.set_timer(0.1, self._update_history_table)
                return

            table = self.query_one("#crawl-history-table", DataTable)
            table.clear()
            
            # 计算分页
            start_index = (self.current_page - 1) * self.items_per_page
            end_index = min(start_index + self.items_per_page, len(self.crawler_history))
            current_page_items = self.crawler_history[start_index:end_index]
            
            for i, item in enumerate(current_page_items):
                # 使用唯一标识符作为行键，避免重复
                row_key = f"{item['novel_id']}_{item['crawl_time']}_{i}"
                
                # 为成功的数据添加四个独立的操作按钮，为失败的数据添加删除记录按钮和查看原因按钮
                if item["status"] == get_global_i18n().t('crawler.status_success') and item["file_path"]:
                    view_file_text = get_global_i18n().t('crawler.view_file')
                    read_book_text = get_global_i18n().t('crawler.read_book')
                    delete_file_text = get_global_i18n().t('crawler.delete_file')
                    delete_record_text = get_global_i18n().t('crawler.delete_record')
                    view_reason_text = ""  # 成功时不显示查看原因按钮
                elif item["status"] == get_global_i18n().t('crawler.status_failed'):
                    view_file_text = ""
                    read_book_text = ""
                    delete_file_text = ""
                    delete_record_text = get_global_i18n().t('crawler.delete_record')
                    view_reason_text = get_global_i18n().t('crawler.view_reason')  # 失败时显示查看原因按钮
                else:
                    view_file_text = ""
                    read_book_text = ""
                    delete_file_text = ""
                    delete_record_text = ""
                    view_reason_text = ""
                    
                table.add_row(
                    str(start_index + i + 1),  # 序号，从当前页面的起始序号开始计算
                    item["novel_id"],
                    item["novel_title"],
                    item["crawl_time"],
                    item["status"],
                    item["file_path"],
                    view_file_text,
                    read_book_text,
                    delete_file_text,
                    delete_record_text,
                    view_reason_text,  # 新增查看原因列
                    key=row_key
                )

                # 启用隔行变色效果
                table.zebra_stripes = True
            
            # 更新分页信息
            self._update_pagination_info()
            
        except Exception as e:
            logger.debug(f"更新历史记录表格失败: {e}")
            # 延迟重试
            self.set_timer(0.1, self._update_history_table)
    
    def _update_pagination_info(self) -> None:
        """更新分页信息"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟更新分页信息")
                # 延迟100ms后重试
                self.set_timer(0.1, self._update_pagination_info)
                return

            total_pages = max(1, (len(self.crawler_history) + self.items_per_page - 1) // self.items_per_page)
            page_label = self.query_one("#page-info", Label)
            page_label.update(f"{get_global_i18n().t('crawler.page')} {self.current_page}/{total_pages}")
        except Exception as e:
            logger.debug(f"更新分页信息失败: {e}")
            # 延迟重试
            self.set_timer(0.1, self._update_pagination_info)
    
    # 统一快捷键绑定（含 ESC 返回）
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("o", "open_browser", get_global_i18n().t('crawler.shortcut_o')),
        ("r", "view_history", get_global_i18n().t('crawler.shortcut_r')),
        ("b", "note", get_global_i18n().t('crawler.shortcut_b')),
        ("escape", "back", get_global_i18n().t('common.back')),
        ("x", "select_books", get_global_i18n().t('crawler.select_books')),
        ("s", "start_crawl", get_global_i18n().t('crawler.shortcut_s')),
        ("v", "stop_crawl", get_global_i18n().t('crawler.shortcut_v')),
        ("p", "prev_page", get_global_i18n().t('crawler.shortcut_p')),
        ("n", "next_page", get_global_i18n().t('crawler.shortcut_n')),
    ]

    def action_open_browser(self) -> None:
        self._open_browser()

    def action_view_history(self) -> None:
        self._view_history()

    def action_start_crawl(self) -> None:
        self._start_crawl()

    def action_stop_crawl(self) -> None:
        self._stop_crawl()

    def action_note(self) -> None:
        self._open_note_dialog()

    def action_prev_page(self) -> None:
        self._prev_page()

    def action_next_page(self) -> None:
        self._next_page()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_select_books(self) -> None:
        # 如果未开启支持选择书籍，则不做任何处理
        if self.novel_site.get("selectable_enabled", True):
            self._open_select_books_dialog()
        else:
            # 弹窗提示未开启支持选择书籍
            self._update_status(get_global_i18n().t('crawler.disabled_selectable'), "error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        按钮按下时的回调
        
        Args:
            event: 按钮按下事件
        """
        if event.button.id == "open-browser-btn":
            self._open_browser()
        elif event.button.id == "view-history-btn":
            self._view_history()
        elif event.button.id == "note-btn":
            self._open_note_dialog()
        elif event.button.id == "start-crawl-btn":
            self._start_crawl()
        elif event.button.id == "choose-books-btn":
            self._open_select_books_dialog()
        elif event.button.id == "stop-crawl-btn":
            self._stop_crawl()
        elif event.button.id == "prev-page-btn":
            self._prev_page()
        elif event.button.id == "next-page-btn":
            self._next_page()
        elif event.button.id == "back-btn":
            self.app.pop_screen()  # 返回上一页
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """
        数据表格单元格选择时的回调
        
        Args:
            event: 单元格选择事件
        """
        # 获取选中的单元格坐标
        row_index = event.coordinate.row
        column_index = event.coordinate.column
        
        # 只处理操作列（第7、8、9、10、11列）
        if column_index not in [6, 7, 8, 9, 10]:  # 查看文件、阅读书籍、删除文件、删除记录、查看原因列
            return
            
        # 根据分页计算真实索引，避免跨页错位
        start_index = (self.current_page - 1) * self.items_per_page
        real_index = start_index + row_index
        if real_index < 0 or real_index >= len(self.crawler_history):
            return

        history_item = self.crawler_history[real_index]
        
        if not history_item:
            return
            
        # 根据列索引执行不同的操作
        if column_index == 6:  # 查看文件列
            self._view_file(history_item)
        elif column_index == 7:  # 阅读书籍列
            self._read_book(history_item)
        elif column_index == 8:  # 删除文件列
            self._delete_file_only(history_item)
        elif column_index == 9:  # 删除记录列
            self._delete_record_only(history_item)
        elif column_index == 10:  # 查看原因列
            self._view_reason(history_item)
    
    def _open_browser(self) -> None:
        """在浏览器中打开网站"""
        import webbrowser
        try:
            webbrowser.open(self.novel_site['url'])
            self._update_status(get_global_i18n().t('crawler.browser_opened'))
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.open_browser_failed')}: {str(e)}", "error")
    
    def _view_history(self) -> None:
        """查看爬取历史"""
        # 刷新历史记录
        self._load_crawl_history()
        self._update_status(get_global_i18n().t('crawler.history_loaded'))
    
    def _open_note_dialog(self) -> None:
        """打开备注对话框"""
        try:
            # 获取当前网站的备注内容
            site_id = self.novel_site.get('id')
            if not site_id:
                self._update_status(get_global_i18n().t('crawler.no_site_id'), "error")
                return
            
            # 从数据库加载现有备注
            current_note = self.db_manager.get_novel_site_note(site_id) or ""
            
            # 打开备注对话框
            def handle_note_dialog_result(result: Optional[str]) -> None:
                if result is not None:
                    # 保存备注到数据库
                    if self.db_manager.save_novel_site_note(site_id, result):
                        self._update_status(get_global_i18n().t('crawler.note_saved'), "success")
                    else:
                        self._update_status(get_global_i18n().t('crawler.note_save_failed'), "error")
                # 如果result为None，表示用户取消了操作
            
            self.app.push_screen(
                NoteDialog(
                    self.theme_manager,
                    self.novel_site['name'],
                    current_note
                ),
                handle_note_dialog_result
            )
            
        except Exception as e:
            logger.error(f"打开备注对话框失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.open_note_dialog_failed')}: {str(e)}", "error")

    def _open_select_books_dialog(self) -> None:
        """打开选择书籍对话框，回填选中ID到输入框"""
        try:
            def handle_selected_ids(result: Optional[str]) -> None:
                if result:
                    try:
                        novel_id_input = self.query_one("#novel-id-input", Input)
                        novel_id_input.value = result
                        novel_id_input.focus()
                        self._update_status(get_global_i18n().t('crawler.filled_ids'))
                    except Exception as e:
                        logger.debug(f"回填选中ID失败: {e}")
            self.app.push_screen(
                SelectBooksDialog(self.theme_manager, self.novel_site),
                handle_selected_ids
            )
        except Exception as e:
            logger.error(f"打开选择书籍对话框失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.open_dialog_failed')}: {str(e)}", "error")

    def _stop_crawl(self) -> None:
        """停止爬取"""
        if not self.is_crawling:
            self._update_status(get_global_i18n().t('crawler.no_crawl_in_progress'))
            return
        
        # 设置停止标志
        self.is_crawling = False
        self._update_crawl_button_state()
        self._hide_loading_animation()
        self._update_status(get_global_i18n().t('crawler.crawl_stopped'))
    
    def _start_crawl(self) -> None:
        """开始爬取小说"""
        # 权限校验：执行爬取任务需 crawler.run
        if not getattr(self.app, "has_permission", lambda k: True)("crawler.run"):
            self._update_status(get_global_i18n().t('crawler.np_crawler'), "error")
            return
        if self.is_crawling:
            return  # 如果正在爬取，忽略新的爬取请求
        
        novel_id_input = self.query_one("#novel-id-input", Input)
        novel_ids_input = novel_id_input.value.strip()
        
        if not novel_ids_input:
            self._update_status(get_global_i18n().t('crawler.enter_novel_id'))
            return
        
        # 分割多个小说ID
        novel_ids = [id.strip() for id in novel_ids_input.split(',') if id.strip()]
        
        if not novel_ids:
            self._update_status(get_global_i18n().t('crawler.enter_novel_id'))
            return
        
        # 验证每个小说ID格式（支持多种格式：数字、字母、中文、日期路径等）
        invalid_ids = []
        for novel_id in novel_ids:
            # 支持以下格式：
            # 1. 2022/02/blog-post_70 (日期路径格式)
            # 2. 中文标题名 (纯中文)
            # 3. 2025/06/09/中文标题 (混合格式)
            # 4. 数字字母组合 (如68fa7dcff3de0)
            if not novel_id:
                invalid_ids.append(novel_id)
                continue
            
            # 检查是否包含非法字符（简化验证，主要排除英文逗号作为分隔符）
            # 允许的字符：字母、数字、中文、常见标点符号、空格等
            # 注意：英文逗号(,)用于分隔多个ID，所以不能在单个ID中使用
            if ',' in novel_id:
                invalid_ids.append(novel_id)
        
        if invalid_ids:
            self._update_status(f"{get_global_i18n().t('crawler.invalid_novel_id')}: {', '.join(invalid_ids)}")
            return
        
        # 检查是否已经下载过且文件存在
        site_id = self.novel_site.get('id')
        existing_novels = []
        if site_id:
            for novel_id in novel_ids:
                if self.db_manager.check_novel_exists(site_id, novel_id):
                    existing_novels.append(novel_id)
        
        if existing_novels:
            # 自动跳过并清理已存在的ID
            try:
                for _eid in existing_novels:
                    # 清理输入框中的已存在ID
                    self.app.call_later(self._remove_id_from_input, _eid)
                    # 单独提示每个被跳过的ID
                    try:
                        self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.skipped')}: {_eid}", "information")
                    except Exception:
                        pass
            except Exception:
                pass
            # 过滤掉已存在的ID，继续爬取剩余的
            novel_ids = [nid for nid in novel_ids if nid not in existing_novels]
            if not novel_ids:
                self._update_status(f"{get_global_i18n().t('crawler.novel_already_exists')}: {', '.join(existing_novels)}")
                return
            else:
                # 汇总提示，继续爬取剩余ID
                self._update_status(f"{get_global_i18n().t('crawler.novel_already_exists')}: {', '.join(existing_novels)}，{get_global_i18n().t('crawler.skip')}", "information")
        
        # 检查代理要求
        proxy_check_result = self._check_proxy_requirements_sync()
        if not proxy_check_result['can_proceed']:
            self._update_status(proxy_check_result['message'], "error")
            return
        
        proxy_config = proxy_check_result['proxy_config']
        
        # 清空之前的提示信息
        self._update_status("")
        
        # 设置爬取状态
        self.is_crawling = True
        
        # 立即更新按钮状态和显示加载动画
        # 使用call_after_refresh确保在UI刷新后执行
        self.call_after_refresh(self._update_crawl_button_state)
        self.call_after_refresh(self._show_loading_animation)
        
        # 开始爬取
        self._update_status(get_global_i18n().t('crawler.starting_crawl'))
        
        # 实现实际的爬取逻辑
        # 使用异步执行爬取任务，避免阻塞UI更新
        # 调用实际爬取方法 - 使用app级别的run_worker，确保页面卸载时爬取继续
        self.app.run_worker(self._actual_crawl_multiple(novel_ids, proxy_config), name="crawl-worker")
    
    def _check_proxy_requirements_sync(self) -> Dict[str, Any]:
        """
        同步检查代理要求
        
        Returns:
            包含检查结果的字典
        """
        try:
            # 检查网站是否启用了代理
            proxy_enabled = self.novel_site.get('proxy_enabled', False)
            
            if not proxy_enabled:
                # 网站未启用代理，返回空代理配置
                return {
                    'can_proceed': True,
                    'proxy_config': {
                        'enabled': False,
                        'proxy_url': ''
                    },
                    'message': get_global_i18n().t('crawler.not_enabled_proxy')
                }
            
            # 网站启用了代理，获取可用的代理设置
            enabled_proxy = self.db_manager.get_enabled_proxy()
            
            if not enabled_proxy:
                # 没有启用的代理，提示用户
                return {
                    'can_proceed': False,
                    'proxy_config': None,
                    'message': get_global_i18n().t('crawler.need_proxy')
                }
            
            # 构建代理URL
            proxy_type = enabled_proxy.get('type', 'HTTP').lower()
            host = enabled_proxy.get('host', '')
            port = enabled_proxy.get('port', '')
            username = enabled_proxy.get('username', '')
            password = enabled_proxy.get('password', '')
            
            if not host or not port:
                return {
                    'can_proceed': False,
                    'proxy_config': None,
                    'message': get_global_i18n().t('crawler.proxy_error')
                }
            
            # 构建代理URL
            if username and password:
                proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"{proxy_type}://{host}:{port}"
            
            # 测试代理连接
            proxy_test_result = self._test_proxy_connection(proxy_url)
            if not proxy_test_result:
                return {
                    'can_proceed': False,
                    'proxy_config': None,
                    'message': get_global_i18n().t("crawler.proxy_error_url", proxy_url=proxy_url)
                }
            
            return {
                'can_proceed': True,
                'proxy_config': {
                    'enabled': True,
                    'proxy_url': proxy_url,
                    'name': enabled_proxy.get('name', get_global_i18n().t("crawler.unnamed_proxy"))
                },
                'message': f"{get_global_i18n().t("crawler.use_proxy")}: {enabled_proxy.get('name', get_global_i18n().t("crawler.unnamed_proxy"))} ({host}:{port})"
            }
            
        except Exception as e:
            logger.error(f"检查代理要求失败: {e}")
            return {
                'can_proceed': False,
                'proxy_config': None,
                'message': f'{get_global_i18n().t("crawler.check_proxy_failed")}: {str(e)}'
            }

    def _test_proxy_connection(self, proxy_url: str) -> bool:
        """
        测试代理连接是否可用
        
        Args:
            proxy_url: 代理URL
            
        Returns:
            bool: 代理是否可用
        """
        import requests
        import time
        
        try:
            # 设置代理
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 测试连接 - 使用目标网站进行测试
            test_url = "https://www.renqixiaoshuo.net"
            
            # 设置超时时间
            timeout = 10
            
            start_time = time.time()
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            end_time = time.time()
            
            if response.status_code == 200:
                logger.info(f"{get_global_i18n().t('crawler.test_success')}: {proxy_url} ({get_global_i18n().t('crawler.response_time')}: {end_time - start_time:.2f}s)")
                return True
            else:
                logger.error(f"{get_global_i18n().t('crawler.test_failed')}: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectTimeout:
            logger.error(f"代理连接超时: {proxy_url}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error(f"代理连接错误: {proxy_url}")
            return False
        except Exception as e:
            logger.error(f"代理测试异常: {e}")
            return False

    async def _check_proxy_requirements(self, website: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查代理要求
        
        Args:
            website: 网站信息
            
        Returns:
            包含检查结果的字典
        """
        try:
            # 检查网站是否启用了代理
            proxy_enabled = website.get('proxy_enabled', False)
            
            if not proxy_enabled:
                # 网站未启用代理，返回空代理配置
                return {
                    'can_proceed': True,
                    'proxy_config': {
                        'enabled': False,
                        'proxy_url': ''
                    },
                    'message': get_global_i18n().t("crawler.not_enabled_proxy")
                }
            
            # 网站启用了代理，获取可用的代理设置
            enabled_proxy = self.db_manager.get_enabled_proxy()
            
            if not enabled_proxy:
                # 没有启用的代理，但允许用户选择是否继续不使用代理
                return {
                    'can_proceed': True,
                    'proxy_config': {
                        'enabled': False,
                        'proxy_url': ''
                    },
                    'message': get_global_i18n().t("crawler.need_proxy_try")
                }
            
            # 构建代理URL
            proxy_type = enabled_proxy.get('type', 'HTTP').lower()
            host = enabled_proxy.get('host', '')
            port = enabled_proxy.get('port', '')
            username = enabled_proxy.get('username', '')
            password = enabled_proxy.get('password', '')
            
            if not host or not port:
                return {
                    'can_proceed': False,
                    'proxy_config': None,
                    'message': get_global_i18n().t("crawler.proxy_error")
                }
            
            # 构建代理URL
            if username and password:
                proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"{proxy_type}://{host}:{port}"
            
            return {
                'can_proceed': True,
                'proxy_config': {
                    'enabled': True,
                    'proxy_url': proxy_url,
                    'name': enabled_proxy.get('name', get_global_i18n().t("crawler.unnamed_proxy"))
                },
                'message': f"{get_global_i18n().t("crawler.use_proxy")}: {enabled_proxy.get('name', get_global_i18n().t("crawler.unnamed_proxy"))} ({host}:{port})"
            }
            
        except Exception as e:
            logger.error(f"检查代理要求失败: {e}")
            return {
                'can_proceed': False,
                'proxy_config': None,
                'message': f'{get_global_i18n().t("crawler.check_proxy_failed")}: {str(e)}'
            }

    async def _actual_crawl_multiple(self, novel_ids: List[str], proxy_config: Dict[str, Any]) -> None:
        """实际爬取多个小说（异步执行）"""
        import asyncio
        import time
        
        # 开始爬取 - 使用app.call_later来安全地更新UI
        self.app.call_later(self._update_status, get_global_i18n().t("crawler.start_to_crawler_books", counts=len(novel_ids)))
        
        try:
            # 获取解析器名称
            parser_name = self.novel_site.get('parser')
            if not parser_name:
                self.app.call_later(self._update_status, get_global_i18n().t("crawler.no_parser"), "error")
                return
            
            # 导入解析器
            from src.spiders import create_parser
            
            # 创建解析器实例，传递数据库中的网站名称作为作者信息
            parser_instance = create_parser(parser_name, proxy_config, self.novel_site.get('name'))
            
            # 使用异步方式同时爬取多个小说
            tasks = []
            for novel_id in novel_ids:
                task = self._crawl_single_novel(parser_instance, novel_id, proxy_config)
                tasks.append(task)
            
            # 同时执行所有爬取任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            success_count = 0
            failed_count = 0
            
            for i, result in enumerate(results):
                novel_id = novel_ids[i]
                if isinstance(result, Exception):
                    logger.error(f"爬取小说 {novel_id} 失败: {result}")
                    failed_count += 1
                    
                    # 记录失败到数据库
                    site_id = self.novel_site.get('id')
                    if site_id:
                        self.db_manager.add_crawl_history(
                            site_id=site_id,
                            novel_id=novel_id,
                            novel_title="",
                            status='failed',
                            file_path="",
                            error_message=str(result)
                        )
                    
                    # 添加到历史记录
                    new_history = {
                        "novel_id": novel_id,
                        "novel_title": "",
                        "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": get_global_i18n().t('crawler.status_failed'),
                        "file_path": ""
                    }
                    self.crawler_history.insert(0, new_history)
                    # 移除已完成ID（失败）
                    try:
                        self.app.call_later(self._remove_id_from_input, novel_id)
                    except Exception:
                        pass
                else:
                    success_count += 1
                    # 移除已完成ID（成功）
                    try:
                        self.app.call_later(self._remove_id_from_input, novel_id)
                    except Exception:
                        pass
            
            # 更新历史记录表格
            self.app.call_later(self._update_history_table)
            
            # 显示最终结果
            if success_count > 0 and failed_count == 0:
                self.app.call_later(self._update_status, get_global_i18n().t("crawler.crawler_success_count_books", counts=success_count), "success")
            elif success_count > 0 and failed_count > 0:
                self.app.call_later(self._update_status, get_global_i18n().t("crawler.crawler_result", success=success_count, failed=failed_count), "warning")
            else:
                self.app.call_later(self._update_status, get_global_i18n().t("crawler.crawler_all_failed", counts=failed_count), "error")
            
            # 发送全局爬取完成通知
            try:
                from src.ui.messages import CrawlCompleteNotification
                self.app.post_message(CrawlCompleteNotification(
                    success=success_count > 0,
                    novel_title=get_global_i18n().t("crawler.novel_title_count", counts=success_count),
                    message=get_global_i18n().t("crawler.crawler_result", success=success_count, failed=failed_count)
                ))
            except Exception as msg_error:
                logger.debug(f"发送爬取完成通知失败: {msg_error}")
            
            # 重置爬取状态
            self.app.call_later(self._reset_crawl_state)
            
        except Exception as e:
            logger.error(f"多小说爬取过程中发生错误: {e}")
            import traceback
            logger.error(f"详细错误堆栈: {traceback.format_exc()}")
            error_message = f"{get_global_i18n().t("crawler.many_books_failed")}: {str(e)}"
            self.app.call_later(self._update_status, error_message, "error")
            self.app.call_later(self._reset_crawl_state)
    
    async def _crawl_single_novel(self, parser_instance, novel_id: str, proxy_config: Dict[str, Any]) -> Dict[str, Any]:
        """爬取单个小说"""
        import asyncio
        import time
        # 标记当前正在爬取的ID并更新状态
        try:
            self.current_crawling_id = novel_id
            self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawling')} ID: {novel_id}")
        except Exception:
            pass
        
        try:
            # 使用异步方式执行网络请求
            await asyncio.sleep(0.5)  # 添加小延迟避免同时请求过多
            
            # 解析小说详情
            novel_content = await self._async_parse_novel_detail(parser_instance, novel_id)
            novel_title = novel_content['title']
            
            # 获取存储文件夹
            storage_folder = self.novel_site.get('storage_folder', 'novels')
            
            # 保存小说到文件
            file_path = parser_instance.save_to_file(novel_content, storage_folder)
            
            # 记录到数据库
            site_id = self.novel_site.get('id')
            if site_id:
                self.db_manager.add_crawl_history(
                    site_id=site_id,
                    novel_id=novel_id,
                    novel_title=novel_title,
                    status='success',
                    file_path=file_path
                )
            
            # 添加到历史记录
            new_history = {
                "novel_id": novel_id,
                "novel_title": novel_title,
                "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": get_global_i18n().t('crawler.status_success'),
                "file_path": file_path
            }
            self.crawler_history.insert(0, new_history)
            # 移除已完成ID
            try:
                self.app.call_later(self._remove_id_from_input, novel_id)
            except Exception:
                pass
            
            # 自动将书籍加入书架
            try:
                # 将新书加入书架（优先使用内存书架以便立刻可读，失败时退回直接写DB）
                try:
                    bs = getattr(self.app, "bookshelf", None)
                    book = None
                    if bs and hasattr(bs, "add_book"):
                        # 强制使用数据库中的书籍网站名称作为作者
                        author = self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source'))
                        # 获取网站标签
                        site_tags = self.novel_site.get('tags', '')
                        book = bs.add_book(file_path, author=author, tags=site_tags)
                    if not book:
                        from src.core.book import Book
                        # 强制使用数据库中的书籍网站名称作为作者
                        author = self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source'))
                        # 获取网站标签
                        site_tags = self.novel_site.get('tags', '')
                        book = Book(file_path, novel_title, author, tags=site_tags)
                        self.db_manager.add_book(book)
                except Exception as add_err:
                    logger.error(f"添加书籍到书架失败: {add_err}")
                # 发送全局刷新书架消息
                try:
                    from src.ui.messages import RefreshBookshelfMessage
                    self.app.post_message(RefreshBookshelfMessage())
                    logger.info(f"已发送书架刷新消息，书籍已添加到书架: {novel_title}")
                except Exception as msg_error:
                    logger.debug(f"发送刷新书架消息失败: {msg_error}")
                else:
                    logger.warning(f"添加书籍到书架失败: {novel_title}")
            except Exception as e:
                logger.error(f"添加书籍到书架失败: {e}")
            
            # 若当前ID与本任务一致，清空当前ID
            try:
                if self.current_crawling_id == novel_id:
                    self.current_crawling_id = None
            except Exception:
                pass
            return novel_content
            
        except Exception as e:
            logger.error(f"爬取小说 {novel_id} 失败: {e}")
            # 失败也清理当前ID（若仍匹配）
            try:
                if self.current_crawling_id == novel_id:
                    self.current_crawling_id = None
            except Exception:
                pass
            raise e
    
    async def _actual_crawl(self, novel_id: str, proxy_config: Dict[str, Any]) -> None:
        """实际爬取小说（异步执行）- 保留单本爬取方法"""
        import asyncio
        import os
        import time
        
        # 标记当前正在爬取的ID并更新状态
        try:
            self.current_crawling_id = novel_id
        except Exception:
            pass
        # 开始爬取 - 使用app.call_later来安全地更新UI
        self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawling')} ID: {novel_id}")
        
        try:
            # 获取解析器名称
            parser_name = self.novel_site.get('parser')
            if not parser_name:
                self.app.call_later(self._update_status, get_global_i18n().t('crawler.no_parser'), "error")
                return
            
            # 导入解析器
            from src.spiders import create_parser
            
            # 创建解析器实例，传递数据库中的网站名称作为作者信息
            parser_instance = create_parser(parser_name, proxy_config, self.novel_site.get('name'))
            
            # 使用异步方式执行网络请求，避免阻塞UI
            await asyncio.sleep(2)  # 模拟网络延迟
            
            # 解析小说详情
            novel_content = await self._async_parse_novel_detail(parser_instance, novel_id)
            novel_title = novel_content['title']
            
            # 获取存储文件夹
            storage_folder = self.novel_site.get('storage_folder', 'novels')
            
            # 保存小说到文件
            file_path = parser_instance.save_to_file(novel_content, storage_folder)
            
            # 记录到数据库
            site_id = self.novel_site.get('id')
            if site_id:
                self.db_manager.add_crawl_history(
                    site_id=site_id,
                    novel_id=novel_id,
                    novel_title=novel_title,
                    status='success',
                    file_path=file_path
                )
            
            # 添加到历史记录
            new_history = {
                "novel_id": novel_id,
                "novel_title": novel_title,
                "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": get_global_i18n().t('crawler.status_success'),
                "file_path": file_path
            }
            self.crawler_history.insert(0, new_history)
            
            # 自动将书籍加入书架
            try:
                # 将新书加入书架（优先内存书架，确保立即可读）
                try:
                    bs = getattr(self.app, "bookshelf", None)
                    added_book = None
                    if bs and hasattr(bs, "add_book"):
                        # 使用解析器返回的作者信息，如果没有则使用数据库中的书籍网站名称
                        author = novel_content.get('author', self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source')))
                        # 获取网站标签
                        site_tags = self.novel_site.get('tags', '')
                        added_book = bs.add_book(file_path, author=author, tags=site_tags)
                    if not added_book:
                        from src.core.book import Book
                        # 使用解析器返回的作者信息，如果没有则使用数据库中的书籍网站名称
                        author = novel_content.get('author', self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source')))
                        # 获取网站标签
                        site_tags = self.novel_site.get('tags', '')
                        added_book = Book(file_path, novel_title, author, tags=site_tags)
                        self.db_manager.add_book(added_book)
                except Exception as add_err:
                    logger.error(f"添加书籍到书架失败: {add_err}")
                # 发送全局刷新书架消息，确保书架屏幕能够接收
                try:
                    from src.ui.messages import RefreshBookshelfMessage
                    self.app.post_message(RefreshBookshelfMessage())
                    logger.info(f"已发送书架刷新消息，书籍已添加到书架: {novel_title}")
                except Exception as msg_error:
                    logger.debug(f"发送刷新书架消息失败: {msg_error}")
                    
                    self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_added_to_shelf')}", "success")
                else:
                    self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_add_failed')}", "warning")
            except Exception as e:
                logger.error(f"添加书籍到书架失败: {e}")
                self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_add_failed')}", "warning")
            
            self.app.call_later(self._update_history_table)
            
            # 移除已完成ID
            try:
                self.app.call_later(self._remove_id_from_input, novel_id)
            except Exception:
                pass
            
            # 发送全局爬取完成通知
            try:
                from src.ui.messages import CrawlCompleteNotification
                self.app.post_message(CrawlCompleteNotification(
                    success=True,
                    novel_title=novel_title,
                    message=f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title}"
                ))
            except Exception as msg_error:
                logger.debug(f"发送爬取完成通知失败: {msg_error}")
            
            # 重置爬取状态
            self.app.call_later(self._reset_crawl_state)
        except Exception as e:
            logger.error(f"爬取过程中发生错误: {e}")
            logger.error(f"代理配置信息: {proxy_config}")
            import traceback
            logger.error(f"详细错误堆栈: {traceback.format_exc()}")
            # 显示更详细的错误信息
            error_message = f"{get_global_i18n().t('crawler.crawl_failed')}: {str(e)}"
            if hasattr(e, '__cause__') and e.__cause__:
                error_message += f"\n{get_global_i18n().t('crawler.reason')}: {str(e.__cause__)}"
            self.app.call_later(self._update_status, error_message, "error")
            
            # 移除已完成ID（失败）
            try:
                self.app.call_later(self._remove_id_from_input, novel_id)
            except Exception:
                pass
            self.app.call_later(self._reset_crawl_state)
    
    async def _async_parse_novel_detail(self, parser_instance, novel_id: str) -> Dict[str, Any]:
        """异步解析小说详情"""
        import asyncio
        
        # 将同步的解析方法包装为异步
        # 在实际实现中，这里应该使用异步HTTP客户端
        # 暂时使用run_in_executor来避免阻塞事件循环
        loop = asyncio.get_event_loop()
        try:
            # 在线程池中执行同步的网络请求
            novel_content = await loop.run_in_executor(
                None, parser_instance.parse_novel_detail, novel_id
            )
            return novel_content
        except Exception as e:
            # 记录详细的错误信息
            logger.error(f"解析小说详情失败: {e}")
            import traceback
            logger.error(f"详细错误堆栈: {traceback.format_exc()}")
            # 如果解析失败，抛出异常
            raise e
    
    async def _simulate_crawl(self, novel_id: str) -> None:
        """模拟爬取过程（异步执行）"""
        import asyncio
        import random
        import os
        import time
        
        # 标记当前正在爬取的ID并更新状态
        try:
            self.current_crawling_id = novel_id
        except Exception:
            pass
        # 模拟爬取过程
        self._update_status(f"{get_global_i18n().t('crawler.crawling')} ID: {novel_id}")
        
        # 使用异步睡眠模拟网络延迟，避免阻塞UI
        await asyncio.sleep(2)
        
        # 随机返回成功或失败
        if random.random() > 0.2:  # 80%成功率
            # 模拟成功爬取
            novel_title = f"{get_global_i18n().t('search_book')}_{novel_id}"
            
            # 正确的文件路径格式：用户输入的存储路径 + 小说标题.txt
            storage_folder = self.novel_site.get('storage_folder', 'novels')
            file_name = f"{novel_title}.txt"
            file_path = os.path.join(storage_folder, file_name)
            
            # 确保存储目录存在
            os.makedirs(storage_folder, exist_ok=True)
            
            # 创建模拟文件内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {novel_title}\\n\\n")
                f.write(f"{get_global_i18n().t('crawler.simulate')}\\n")
                f.write(f"{get_global_i18n().t('search_book')}ID: {novel_id}\\n")
                f.write(f"{get_global_i18n().t('crawler.crawl_time')}: {time.strftime('%Y-%m-%d %H:%M:%S')}\\n")
            
            # 记录到数据库
            site_id = self.novel_site.get('id')
            if site_id:
                self.db_manager.add_crawl_history(
                    site_id=site_id,
                    novel_id=novel_id,
                    novel_title=novel_title,
                    status='success',
                    file_path=file_path
                )
            
            # 添加到历史记录
            new_history = {
                "novel_id": novel_id,
                "novel_title": novel_title,
                "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": get_global_i18n().t('crawler.status_success'),
                "file_path": file_path
            }
            self.crawler_history.insert(0, new_history)
            
            # 移除已完成ID（模拟成功）
            try:
                self.app.call_later(self._remove_id_from_input, novel_id)
            except Exception:
                pass
            
            # 自动将书籍加入书架（优先内存书架，立即可读）
            try:
                bs = getattr(self.app, "bookshelf", None)
                added_book = None
                if bs and hasattr(bs, "add_book"):
                    # 使用解析器名称作为作者（模拟爬取时使用解析器名称）
                    author = self.novel_site.get('name', '未知来源')
                    # 获取网站标签
                    site_tags = self.novel_site.get('tags', '')
                    added_book = bs.add_book(file_path, author=author, tags=site_tags)
                if not added_book:
                    from src.core.book import Book
                    # 使用解析器名称作为作者（模拟爬取时使用解析器名称）
                    author = self.novel_site.get('name', '未知来源')
                    # 获取网站标签
                    site_tags = self.novel_site.get('tags', '')
                    added_book = Book(file_path, novel_title, author, tags=site_tags)
                    self.db_manager.add_book(added_book)
                # 发送刷新书架消息
                try:
                    from src.ui.messages import RefreshBookshelfMessage
                    self.app.post_message(RefreshBookshelfMessage())
                except Exception as msg_error:
                    logger.debug(f"发送刷新书架消息失败: {msg_error}")
            
                    self._update_status(f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_added_to_shelf')}", "success")
                else:
                    self._update_status(f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_add_failed')}", "warning")
            except Exception as e:
                logger.error(f"添加书籍到书架失败: {e}")
                self._update_status(f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_add_failed')}", "warning")
            
            # 发送全局爬取完成通知
            try:
                from src.ui.messages import CrawlCompleteNotification
                self.app.post_message(CrawlCompleteNotification(
                    success=True,
                    novel_title=novel_title,
                    message=f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title}"
                ))
            except Exception as msg_error:
                logger.debug(f"发送爬取完成通知失败: {msg_error}")
            
            self._update_history_table()
            # 若当前ID与本任务一致，清空当前ID
            try:
                if self.current_crawling_id == novel_id:
                    self.current_crawling_id = None
            except Exception:
                pass
        else:
            # 模拟爬取失败
            error_message = get_global_i18n().t('crawler.connected_failed')
            
            # 记录到数据库
            site_id = self.novel_site.get('id')
            if site_id:
                self.db_manager.add_crawl_history(
                    site_id=site_id,
                    novel_id=novel_id,
                    novel_title="",
                    status='failed',
                    file_path="",
                    error_message=error_message
                )
            
            # 添加到历史记录
            new_history = {
                "novel_id": novel_id,
                "novel_title": "",
                "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": get_global_i18n().t('crawler.status_failed'),
                "file_path": ""
            }
            self.crawler_history.insert(0, new_history)
            
            self._update_history_table()
            self._update_status(f"{get_global_i18n().t('crawler.crawl_failed')}: {error_message}", "error")
            
            # 移除已完成ID（模拟失败）
            try:
                self.app.call_later(self._remove_id_from_input, novel_id)
            except Exception:
                pass
            
            # 发送全局爬取失败通知
            try:
                from src.ui.messages import CrawlCompleteNotification
                self.app.post_message(CrawlCompleteNotification(
                    success=False,
                    novel_title="",
                    message=f"{get_global_i18n().t('crawler.crawl_failed')}: {error_message}"
                ))
            except Exception as msg_error:
                logger.debug(f"发送爬取失败通知失败: {msg_error}")
            # 失败也清理当前ID（若仍匹配）
            try:
                if self.current_crawling_id == novel_id:
                    self.current_crawling_id = None
            except Exception:
                pass
    
    def _prev_page(self) -> None:
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self._update_history_table()
    
    def _next_page(self) -> None:
        """下一页"""
        total_pages = max(1, (len(self.crawler_history) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self._update_history_table()
    
    def _update_status(self, message: str, severity: str = "information") -> None:
        """更新状态信息"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟更新状态信息")
                # 延迟100ms后重试
                self.set_timer(0.1, lambda: self._update_status(message, severity))
                return

            # 在爬取进行中且消息为空或为通用“正在爬取”时，附加当前ID
            base_crawling = get_global_i18n().t('crawler.crawling')
            if self.is_crawling and self.current_crawling_id:
                if not message or message.strip() == base_crawling:
                    message = f"{base_crawling} ID: {self.current_crawling_id}"
                # 附加剩余未爬取数量
                try:
                    novel_id_input = self.query_one("#novel-id-input", Input)
                    raw = (novel_id_input.value or "").strip()
                    remaining_ids = [i.strip() for i in raw.split(",") if i.strip()]
                    rem = len(remaining_ids) - 1
                    message = f"{message}（{get_global_i18n().t('crawler.remaining')}: {rem}）"
                    
                except Exception:
                    pass
            # 使用正确的CSS选择器语法，需要#号
            status_label = self.query_one("#crawler-status", Label)
            status_label.update(message)
            
            # 根据严重程度设置样式
            if severity == "success":
                status_label.styles.color = "green"
            elif severity == "error":
                status_label.styles.color = "red"
            else:
                status_label.styles.color = "blue"
            
            logger.debug(f"状态信息更新成功: {message}")
        except Exception as e:
            # 如果状态标签不存在，记录错误但不中断程序
            logger.debug(f"更新状态信息失败: {e}")
            # 延迟重试
            self.set_timer(0.1, lambda: self._update_status(message, severity))
    
    def _remove_id_from_input(self, finished_id: str) -> None:
        """爬取完成后，从输入框中移除已完成的ID（支持多个ID，英文逗号分隔）"""
        try:
            novel_id_input = self.query_one("#novel-id-input", Input)
            raw = (novel_id_input.value or "").strip()
            if not raw:
                return
            # 分割并标准化
            ids = [i.strip() for i in raw.split(",") if i.strip()]
            # 如果没有该ID则跳过
            if finished_id not in ids:
                return
            # 移除匹配ID
            ids = [i for i in ids if i != finished_id]
            # 更新输入框
            novel_id_input.value = ",".join(ids)
            # 将焦点放回输入框，便于继续输入
            try:
                novel_id_input.focus()
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"移除输入ID失败: {e}")

    def _initialize_loading_animation(self) -> None:
        """初始化加载动画"""
        try:
            from src.ui.components.textual_loading_animation import TextualLoadingAnimation, textual_animation_manager

            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟初始化加载动画")
                # 延迟100ms后重试
                self.set_timer(0.1, self._initialize_loading_animation)
                return

            try:
                # 获取加载动画容器
                loading_container = self.query_one("#loading-animation", Static)
                logger.debug("加载动画容器查询成功")
                
                # 创建加载动画组件并挂载到容器
                self.loading_animation = TextualLoadingAnimation()
                loading_container.mount(self.loading_animation)
                logger.debug("加载动画组件挂载成功")
                
                # 同时创建并挂载原生 LoadingIndicator（初始隐藏）
                try:
                    self.loading_indicator = LoadingIndicator(id="crawler-loading-indicator")
                    self.loading_indicator.display = False
                    loading_container.mount(self.loading_indicator)
                    logger.debug("原生 LoadingIndicator 挂载成功")
                except Exception:
                    pass

                # 设置默认动画
                textual_animation_manager.set_default_animation(self.loading_animation)
                logger.debug("默认动画设置成功")
                
                logger.debug("加载动画组件初始化成功")
            except Exception as e:
                logger.warning(f"加载动画组件初始化失败: {e}")
                self.loading_animation = None
            
        except Exception as e:
            logger.warning(f"加载动画组件初始化过程失败: {e}")
            self.loading_animation = None
    
    def _update_crawl_button_state(self) -> None:
        """更新爬取按钮状态"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟更新按钮状态")
                # 延迟100ms后重试
                self.set_timer(0.1, self._update_crawl_button_state)
                return

            # 使用正确的CSS选择器语法，需要#号
            start_crawl_button = self.query_one("#start-crawl-btn", Button)
            stop_crawl_button = self.query_one("#stop-crawl-btn", Button)
            
            if self.is_crawling:
                start_crawl_button.label = get_global_i18n().t('crawler.crawling_in_progress')
                start_crawl_button.disabled = True
                stop_crawl_button.disabled = False
            else:
                start_crawl_button.label = get_global_i18n().t('crawler.start_crawl')
                start_crawl_button.disabled = False
                stop_crawl_button.disabled = True
            
            logger.debug("爬取按钮状态更新成功")
        except Exception as e:
            # 如果按钮不存在，记录错误但不中断程序
            logger.debug(f"更新爬取按钮状态失败: {e}")
            # 延迟重试
            self.set_timer(0.1, self._update_crawl_button_state)
    
    def _show_loading_animation(self) -> None:
        """显示加载动画"""
        try:
            # 原生 LoadingIndicator：可见即动画
            try:
                if not hasattr(self, "loading_indicator"):
                    self.loading_indicator = self.query_one("#crawler-loading-indicator", LoadingIndicator)
            except Exception:
                pass
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    self.loading_indicator.display = True
            except Exception:
                pass

            # 检查加载动画组件是否存在且已初始化
            if self.loading_animation is not None:
                self.loading_animation.show(get_global_i18n().t('crawler.crawling'))
                logger.debug("加载动画显示成功")
            else:
                # 如果加载动画不存在，尝试重新初始化
                logger.warning("加载动画组件不存在，尝试重新初始化")
                self._initialize_loading_animation()
                
                # 延迟显示加载动画
                def delayed_show():
                    if self.loading_animation is not None:
                        self.loading_animation.show(get_global_i18n().t('crawler.crawling'))
                        logger.debug("延迟加载动画显示成功")
                    else:
                        # 回退到状态更新
                        logger.warning("加载动画组件初始化失败，使用状态更新替代")
                        self._update_status(get_global_i18n().t('crawler.crawling'))
                
                self.set_timer(0.1, delayed_show)
        except Exception as e:
            logger.error(f"显示加载动画失败: {e}")
            # 回退到状态更新
            self._update_status(get_global_i18n().t('crawler.crawling'))
    
    def _hide_loading_animation(self) -> None:
        """隐藏加载动画"""
        try:
            # 原生 LoadingIndicator：隐藏
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    self.loading_indicator.display = False
            except Exception:
                pass

            if hasattr(self, 'loading_animation') and self.loading_animation:
                self.loading_animation.hide()
        except Exception as e:
            logger.error(f"隐藏加载动画失败: {e}")
    
    def _check_proxy_settings(self) -> Optional[Dict[str, Any]]:
        """
        检查代理设置
        
        Returns:
            代理配置字典，如果检查失败返回None
        """
        try:
            # 检查网站是否启用了代理
            proxy_enabled = self.novel_site.get('proxy_enabled', False)
            
            if not proxy_enabled:
                # 网站未启用代理，返回空代理配置
                return {
                    'enabled': False,
                    'proxy_url': ''
                }
            
            # 网站启用了代理，获取可用的代理设置
            enabled_proxy = self.db_manager.get_enabled_proxy()
            
            if not enabled_proxy:
                # 没有启用的代理，提示用户
                self._update_status(get_global_i18n().t('crawler.need_proxy'), "error")
                return None
            
            # 构建代理URL
            proxy_type = enabled_proxy.get('type', 'HTTP').lower()
            host = enabled_proxy.get('host', '')
            port = enabled_proxy.get('port', '')
            username = enabled_proxy.get('username', '')
            password = enabled_proxy.get('password', '')
            
            if not host or not port:
                self._update_status(get_global_i18n().t('crawler.proxy_error'), "error")
                return None
            
            # 构建代理URL
            if username and password:
                proxy_url = f"{proxy_type}://{username}:{password}@{host}:{port}"
            else:
                proxy_url = f"{proxy_type}://{host}:{port}"
            
            self._update_status(f"{get_global_i18n().t('crawler.use_proxy')}: {enabled_proxy.get('name', get_global_i18n().t('crawler.unnamed_proxy'))} ({host}:{port})", "success")
            
            return {
                'enabled': True,
                'proxy_url': proxy_url,
                'name': enabled_proxy.get('name', get_global_i18n().t('crawler.unnamed_proxy'))
            }
            
        except Exception as e:
            logger.error(f"检查代理设置失败: {e}")
            self._update_status(f"{get_global_i18n().t('crawler.check_proxy_failed')}: {str(e)}", "error")
            return None
    
    def _reset_crawl_state(self) -> None:
        """重置爬取状态"""
        try:
            # 确保组件已经挂载
            if not self.is_mounted_flag:
                logger.debug("组件尚未挂载，延迟重置爬取状态")
                # 延迟100ms后重试
                self.set_timer(0.1, self._reset_crawl_state)
                return

            self.is_crawling = False
            self._update_crawl_button_state()
            self._hide_loading_animation()
            
            # 自动继续爬取剩余ID（如果输入框中还有）
            try:
                novel_id_input = self.query_one("#novel-id-input", Input)
                raw = (novel_id_input.value or "").strip()
                remaining_ids = [i.strip() for i in raw.split(",") if i.strip()]
                if remaining_ids and not self.is_crawling:
                    # 在UI刷新后触发下一轮爬取
                    self.call_after_refresh(self._start_crawl)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"重置爬取状态失败: {e}")
            # 延迟重试
            self.set_timer(0.1, self._reset_crawl_state)
    
    def key_o(self) -> None:
        """O键 - 打开浏览器"""
        if self._has_permission("crawler.open_browser"):
            self._open_browser()
        else:
            self._update_status(get_global_i18n().t('crawler.np_open_browser'), "warning")
    
    def key_v(self) -> None:
        """V键 - 查看历史"""
        if self._has_permission("crawler.view_history"):
            self._view_history()
        else:
            self._update_status(get_global_i18n().t('crawler.np_view_history'), "warning")
    
    def key_s(self) -> None:
        """S键 - 开始爬取"""
        if self._has_permission("crawler.start_crawl"):
            self._start_crawl()
        else:
            self._update_status(get_global_i18n().t('crawler.np_crawl'), "warning")
    
    def key_p(self) -> None:
        """P键 - 上一页"""
        if self._has_permission("crawler.navigate"):
            self._prev_page()
        else:
            self._update_status(get_global_i18n().t('crawler.np_nav'), "warning")
    
    def key_n(self) -> None:
        """N键 - 下一页"""
        if self._has_permission("crawler.navigate"):
            self._next_page()
        else:
            self._update_status(get_global_i18n().t('crawler.np_nav'), "warning")
    
    def _view_file(self, history_item: Dict[str, Any]) -> None:
        """查看文件"""
        try:
            file_path = history_item.get('file_path')
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
                
            # 在文件管理器中显示文件
            import platform
            system = platform.system()
            
            if system == "Darwin":  # macOS
                os.system(f'open -R "{file_path}"')
            elif system == "Windows":
                os.system(f'explorer /select,"{file_path}"')
            elif system == "Linux":
                os.system(f'xdg-open "{os.path.dirname(file_path)}"')
                
            self._update_status(get_global_i18n().t('crawler.file_opened'))
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.open_file_failed')}: {str(e)}", "error")
    
    def _delete_file_only(self, history_item: Dict[str, Any]) -> None:
        """只删除文件，不删除数据库记录（同时删除书架中的对应书籍）"""
        try:
            file_path = history_item.get('file_path')
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
                
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        # 只删除文件，不删除数据库记录
                        os.remove(file_path)
                        
                        # 同时删除书架中的对应书籍
                        try:
                            # 直接使用文件路径删除书架中的书籍
                            if self.db_manager.delete_book(file_path):
                                # 发送全局刷新书架消息，确保书架屏幕能够接收
                                try:
                                    from src.ui.messages import RefreshBookshelfMessage
                                    self.app.post_message(RefreshBookshelfMessage())
                                    logger.info("已发送书架刷新消息，书籍已从书架删除")
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，书架中的书籍已删除")
                                except Exception as msg_error:
                                    logger.debug(f"发送刷新书架消息失败: {msg_error}")
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，书架书籍删除但刷新失败")
                            else:
                                # 如果删除失败，检查书籍是否存在于书架中
                                books = self.db_manager.get_all_books()
                                book_exists = any(book.path == file_path for book in books)
                                if book_exists:
                                    self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，但删除书架书籍失败")
                                else:
                                    self._update_status(get_global_i18n().t('crawler.file_deleted'))
                        except Exception as shelf_error:
                            logger.error(f"删除书架书籍失败: {shelf_error}")
                            self._update_status(f"{get_global_i18n().t('crawler.file_deleted')}，但删除书架书籍时出错")
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                    except Exception as e:
                        self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（删除文件及书架书籍）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')}\n\n注意：此操作将同时删除书架中的对应书籍。"
                ),
                handle_delete_confirmation
            )
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
    
    def _delete_record_only(self, history_item: Dict[str, Any]) -> None:
        """只删除数据库记录，不删除文件"""
        try:
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        # 只删除数据库记录，不删除文件
                        history_id = history_item.get('id')
                        if history_id:
                            self.db_manager.delete_crawl_history(history_id)
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                        self._update_status(get_global_i18n().t('crawler.file_deleted'))
                    except Exception as e:
                        self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（{get_global_i18n().t('crawler.only_delete')}）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')}"
                ),
                handle_delete_confirmation
            )
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
    
    def _delete_file(self, history_item: Dict[str, Any]) -> None:
        """删除文件（同时删除文件和记录）"""
        try:
            file_path = history_item.get('file_path')
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
                
            # 确认删除
            from src.ui.dialogs.confirm_dialog import ConfirmDialog
            def handle_delete_confirmation(confirmed: bool | None) -> None:
                if confirmed:
                    try:
                        # 先删除文件
                        os.remove(file_path)
                        
                        # 从数据库中删除对应的记录
                        history_id = history_item.get('id')
                        if history_id:
                            self.db_manager.delete_crawl_history(history_id)
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                        self._update_status(get_global_i18n().t('crawler.file_deleted'))
                    except Exception as e:
                        self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
                elif confirmed is False:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（{get_global_i18n().t('crawler.both_file_data')}）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')}"
                ),
                handle_delete_confirmation
            )
            
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
    
    def on_unmount(self) -> None:
        """页面卸载时的回调"""
        # 设置挂载标志为False，防止后续的UI更新操作
        self.is_mounted_flag = False
        
        # 注意：这里不停止爬取工作线程，让爬取继续在后台运行
        # 爬取工作线程会通过app.call_later和app.post_message来更新UI
        # 即使页面卸载，这些消息也会被正确处理
        logger.debug("爬取管理页面卸载，爬取工作线程继续在后台运行")
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "escape":
            # ESC键返回 - 爬取继续在后台运行
            self.app.pop_screen()
            event.stop()
    
    def _view_reason(self, history_item: Dict[str, Any]) -> None:
        """查看失败原因"""
        try:
            # 检查是否为失败状态
            if history_item.get("status") != get_global_i18n().t('crawler.status_failed'):
                self._update_status(get_global_i18n().t('crawler.no_reason_to_view'), "warning")
                return
                
            # 获取错误信息
            error_message = history_item.get('error_message', '')
            
            if not error_message:
                self._update_status(get_global_i18n().t('crawler.no_error_message'), "information")
                return
                
            # 在状态信息区域显示错误信息
            self._update_status(f"{get_global_i18n().t('crawler.failure_reason')}: {error_message}", "error")
                
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.view_reason_failed')}: {str(e)}", "error")

    def _read_book(self, history_item: Dict[str, Any]) -> None:
        """阅读书籍"""
        try:
            file_path = history_item.get('file_path')
            if not file_path:
                self._update_status(get_global_i18n().t('crawler.no_file_path'))
                return
                
            import os
            if not os.path.exists(file_path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
            
            # 从文件路径创建书籍对象
            from src.core.book import Book
            book_title = history_item.get('novel_title', get_global_i18n().t('crawler.unknown_book'))
            book_source = self.novel_site.get('name', get_global_i18n().t('crawler.unknown_source'))
            book = Book(file_path, book_title, book_source)
            
            # 检查书籍是否有效
            if not book.path or not os.path.exists(book.path):
                self._update_status(get_global_i18n().t('crawler.file_not_exists'))
                return
            
            # 使用 app 的 open_book 方法打开书籍（运行时安全检查，避免类型检查告警）
            open_book = getattr(self.app, "open_book", None)
            if callable(open_book):
                open_book(file_path)  # type: ignore[misc]
                self._update_status(f"{get_global_i18n().t('crawler.on_reading')}: {book_title}", "success")
            else:
                self._update_status(get_global_i18n().t('crawler.cannot_open_book'), "error")
                
        except Exception as e:
            self._update_status(f"{get_global_i18n().t('crawler.open_failed')}: {str(e)}", "error")