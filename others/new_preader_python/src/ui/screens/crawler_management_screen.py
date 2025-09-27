"""
爬取管理屏幕
"""

from typing import Dict, Any, Optional, List, ClassVar
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Label, DataTable, Input, Select
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import events

from src.locales.i18n_manager import get_global_i18n, t, init_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CrawlerManagementScreen(Screen[None]):
    """爬取管理屏幕"""
    
    CSS_PATH = "../styles/crawler_management_screen.css"
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
        self.loading_animation = None  # 加载动画组件
        self.is_mounted_flag = False  # 组件挂载标志
        
        # 确保i18n已初始化
        try:
            get_global_i18n()
        except RuntimeError:
            # 如果未初始化，则初始化
            init_global_i18n('src/locales', 'zh_CN')
        
        # 设置屏幕标题
        CrawlerManagementScreen.TITLE = f"{get_global_i18n().t('crawler.title')} - {novel_site['name']}"
    
    def compose(self) -> ComposeResult:
        """
        组合爬取管理屏幕界面
        
        Returns:
            ComposeResult: 组合结果
        """
        yield Container(
            Vertical(
                Label(f"{get_global_i18n().t('crawler.title')} - {self.novel_site['name']}", id="crawler-title"),
                Label(self.novel_site['url'], id="crawler-url"),
                
                # 操作按钮区域
                Horizontal(
                    Button(get_global_i18n().t('crawler.open_browser'), id="open-browser-btn"),
                    Button(get_global_i18n().t('crawler.view_history'), id="view-history-btn"),
                    Button(get_global_i18n().t('crawler.back'), id="back-btn"),
                    id="crawler-buttons"
                ),
                
                # 小说ID输入区域
                Vertical(
                    # Label(get_global_i18n().t('crawler.novel_id'), id="novel-id-label"),
                    Horizontal(
                        Input(placeholder=get_global_i18n().t('crawler.novel_id_placeholder'), id="novel-id-input"),
                        Button(get_global_i18n().t('crawler.start_crawl'), id="start-crawl-btn", variant="primary"),
                        Button(get_global_i18n().t('crawler.stop_crawl'), id="stop-crawl-btn", variant="error", disabled=True),
                        id="novel-id-container"
                    ),
                    id="novel-id-section"
                ),
                
                # 爬取历史区域
                Vertical(
                    Label(get_global_i18n().t('crawler.crawl_history'), id="crawl-history-title"),
                    DataTable(id="crawl-history-table"),
                    
                    # 分页控制
                    Horizontal(
                        Button(get_global_i18n().t('crawler.prev_page'), id="prev-page-btn"),
                        Label("", id="page-info"),
                        Button(get_global_i18n().t('crawler.next_page'), id="next-page-btn"),
                        id="pagination-controls"
                    ),
                    id="crawl-history-section"
                ),
                
                # 状态信息
                Label("", id="crawler-status"),
                
                # 加载动画区域
                Static("", id="loading-animation"),
                
                # 快捷键状态栏
                Horizontal(
                    Label(get_global_i18n().t('crawler.shortcut_o'), id="shortcut-o"),
                    Label(get_global_i18n().t('crawler.shortcut_v'), id="shortcut-v"),
                    Label(get_global_i18n().t('crawler.shortcut_s'), id="shortcut-s"),
                    Label(get_global_i18n().t('crawler.shortcut_p'), id="shortcut-p"),
                    Label(get_global_i18n().t('crawler.shortcut_n'), id="shortcut-n"),
                    Label(get_global_i18n().t('crawler.shortcut_esc'), id="shortcut-esc"),
                    id="shortcuts-bar"
                ),
                id="crawler-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        # 设置挂载标志
        self.is_mounted_flag = True
        
        # 应用主题
        self.theme_manager.apply_theme_to_screen(self)
        
        # 初始化数据表
        table = self.query_one("#crawl-history-table", DataTable)
        table.add_columns(
            get_global_i18n().t('crawler.novel_id'),
            get_global_i18n().t('crawler.novel_title'),
            get_global_i18n().t('crawler.crawl_time'),
            get_global_i18n().t('crawler.status'),
            get_global_i18n().t('crawler.file_path'),
            get_global_i18n().t('crawler.view_file'),
            get_global_i18n().t('crawler.delete_file'),
            get_global_i18n().t('crawler.delete_record')
        )
        
        # 初始化加载动画
        self._initialize_loading_animation()
        
        # 加载爬取历史
        self._load_crawl_history()
    
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
                        "file_path": item['file_path'] or ""
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
                
                # 为成功的数据添加三个独立的操作按钮，为失败的数据添加删除记录按钮
                if item["status"] == get_global_i18n().t('crawler.status_success') and item["file_path"]:
                    view_file_text = get_global_i18n().t('crawler.view_file')
                    delete_file_text = get_global_i18n().t('crawler.delete_file')
                    delete_record_text = get_global_i18n().t('crawler.delete_record')
                elif item["status"] == get_global_i18n().t('crawler.status_failed'):
                    view_file_text = ""
                    delete_file_text = ""
                    delete_record_text = get_global_i18n().t('crawler.delete_record')
                else:
                    view_file_text = ""
                    delete_file_text = ""
                    delete_record_text = ""
                    
                table.add_row(
                    item["novel_id"],
                    item["novel_title"],
                    item["crawl_time"],
                    item["status"],
                    item["file_path"],
                    view_file_text,
                    delete_file_text,
                    delete_record_text,
                    key=row_key
                )
            
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
        elif event.button.id == "start-crawl-btn":
            self._start_crawl()
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
        
        # 只处理操作列（第6、7、8列）
        if column_index not in [5, 6, 7]:  # 查看文件、删除文件、删除记录列
            return
            
        # 直接使用行索引访问数据（参考get_books_screen.py的实现）
        if row_index < 0 or row_index >= len(self.crawler_history):
            return
            
        history_item = self.crawler_history[row_index]
        
        if not history_item:
            return
            
        # 根据列索引执行不同的操作
        if column_index == 5:  # 查看文件列
            self._view_file(history_item)
        elif column_index == 6:  # 删除文件列
            self._delete_file_only(history_item)
        elif column_index == 7:  # 删除记录列
            self._delete_record_only(history_item)
    
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
        if self.is_crawling:
            return  # 如果正在爬取，忽略新的爬取请求
        
        novel_id_input = self.query_one("#novel-id-input", Input)
        novel_id = novel_id_input.value.strip()
        
        if not novel_id:
            self._update_status(get_global_i18n().t('crawler.enter_novel_id'))
            return
        
        # 验证小说ID格式
        if not novel_id.isdigit():
            self._update_status(get_global_i18n().t('crawler.invalid_novel_id'))
            return
        
        # 检查是否已经下载过且文件存在
        site_id = self.novel_site.get('id')
        if site_id and self.db_manager.check_novel_exists(site_id, novel_id):
            self._update_status(get_global_i18n().t('crawler.novel_already_exists'))
            return
        
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
        self.app.run_worker(self._actual_crawl(novel_id), name="crawl-worker")
    
    async def _actual_crawl(self, novel_id: str) -> None:
        """实际爬取小说（异步执行）"""
        import asyncio
        import os
        import time
        
        # 开始爬取 - 使用app.call_later来安全地更新UI
        self.app.call_later(self._update_status, get_global_i18n().t('crawler.crawling'))
        
        try:
            # 获取解析器名称
            parser_name = self.novel_site.get('parser')
            if not parser_name:
                self.app.call_later(self._update_status, "未配置解析器", "error")
                return
            
            # 导入解析器
            from src.spiders import create_parser
            
            # 设置代理配置
            proxy_config = {
                'enabled': self.novel_site.get('proxy_enabled', False),
                'proxy_url': ''  # 这里需要从代理设置中获取实际的代理URL
            }
            
            # 创建解析器实例
            parser_instance = create_parser(parser_name, proxy_config)
            
            # 使用异步方式执行网络请求，避免阻塞UI
            # 这里需要将同步的网络请求改为异步实现
            # 暂时使用异步睡眠模拟网络延迟
            await asyncio.sleep(2)  # 模拟网络延迟
            
            # 解析小说详情 - 这里需要改为异步实现
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
                from src.core.book import Book
                book = Book(file_path, novel_title, self.novel_site.get('name', '未知来源'))
                if self.db_manager.add_book(book):
                    # 发送刷新书架消息
                    try:
                        from src.ui.messages import RefreshBookshelfMessage
                        self.app.post_message(RefreshBookshelfMessage())
                    except Exception as msg_error:
                        logger.debug(f"发送刷新书架消息失败: {msg_error}")
                    
                    self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_added_to_shelf')}", "success")
                else:
                    self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_add_failed')}", "warning")
            except Exception as e:
                logger.error(f"添加书籍到书架失败: {e}")
                self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_success')}: {novel_title} - {get_global_i18n().t('crawler.book_add_failed')}", "warning")
            
            self.app.call_later(self._update_history_table)
            
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
            self.app.call_later(self._update_status, f"{get_global_i18n().t('crawler.crawl_failed')}: {str(e)}", "error")
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
            # 如果解析失败，抛出异常
            raise e
            try:
                from src.ui.messages import CrawlCompleteNotification
                self.app.post_message(CrawlCompleteNotification(
                    success=False,
                    novel_title="",
                    message=f"{get_global_i18n().t('crawler.crawl_failed')}: {error_message}"
                ))
            except Exception as msg_error:
                logger.debug(f"发送爬取失败通知失败: {msg_error}")
        finally:
            # 重置爬取状态
            self.app.call_later(self._reset_crawl_state)
    
    async def _simulate_crawl(self, novel_id: str) -> None:
        """模拟爬取过程（异步执行）"""
        import asyncio
        import random
        import os
        import time
        
        # 模拟爬取过程
        self._update_status(get_global_i18n().t('crawler.crawling'))
        
        # 使用异步睡眠模拟网络延迟，避免阻塞UI
        await asyncio.sleep(2)
        
        # 随机返回成功或失败
        if random.random() > 0.2:  # 80%成功率
            # 模拟成功爬取
            novel_title = f"小说_{novel_id}"
            
            # 正确的文件路径格式：用户输入的存储路径 + 小说标题.txt
            storage_folder = self.novel_site.get('storage_folder', 'novels')
            file_name = f"{novel_title}.txt"
            file_path = os.path.join(storage_folder, file_name)
            
            # 确保存储目录存在
            os.makedirs(storage_folder, exist_ok=True)
            
            # 创建模拟文件内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {novel_title}\\n\\n")
                f.write("这是模拟爬取的小说内容。\\n")
                f.write(f"小说ID: {novel_id}\\n")
                f.write(f"爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\\n")
            
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
                from src.core.book import Book
                book = Book(file_path, novel_title, self.novel_site.get('name', '未知来源'))
                if self.db_manager.add_book(book):
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
        else:
            # 模拟爬取失败
            error_message = "网络连接失败"
            
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
            if hasattr(self, 'loading_animation') and self.loading_animation:
                self.loading_animation.hide()
        except Exception as e:
            logger.error(f"隐藏加载动画失败: {e}")
    
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
        except Exception as e:
            logger.debug(f"重置爬取状态失败: {e}")
            # 延迟重试
            self.set_timer(0.1, self._reset_crawl_state)
    
    def key_o(self) -> None:
        """O键 - 打开浏览器"""
        self._open_browser()
    
    def key_v(self) -> None:
        """V键 - 查看历史"""
        self._view_history()
    
    def key_s(self) -> None:
        """S键 - 开始爬取"""
        self._start_crawl()
    
    def key_p(self) -> None:
        """P键 - 上一页"""
        self._prev_page()
    
    def key_n(self) -> None:
        """N键 - 下一页"""
        self._next_page()
    
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
        """只删除文件，不删除数据库记录"""
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
            def handle_delete_confirmation(confirmed: bool) -> None:
                if confirmed:
                    try:
                        # 只删除文件，不删除数据库记录
                        os.remove(file_path)
                        
                        # 刷新历史记录
                        self._load_crawl_history()
                        self._update_status(get_global_i18n().t('crawler.file_deleted'))
                    except Exception as e:
                        self._update_status(f"{get_global_i18n().t('crawler.delete_file_failed')}: {str(e)}", "error")
                else:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（只删除文件）",
                    f"{get_global_i18n().t('crawler.confirm_delete_message')}"
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
            def handle_delete_confirmation(confirmed: bool) -> None:
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
                else:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（只删除数据库记录）",
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
            def handle_delete_confirmation(confirmed: bool) -> None:
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
                else:
                    self._update_status(get_global_i18n().t('crawler.delete_cancelled'))
            
            # 显示确认对话框
            self.app.push_screen(
                ConfirmDialog(
                    self.theme_manager,
                    f"{get_global_i18n().t('crawler.confirm_delete')}（同时删除文件和记录）",
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
            event.prevent_default()