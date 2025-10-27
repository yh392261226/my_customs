from typing import Optional, Dict, Any, List, Tuple, Set, ClassVar
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Container, Grid, VerticalScroll
from textual.widgets import Button, Input, Label, DataTable, LoadingIndicator, Static
from textual import events, on
from bs4 import BeautifulSoup
from rich.text import Text
import requests
import textwrap
import threading
import asyncio

from src.locales.i18n_manager import get_global_i18n
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger
from src.spiders import create_parser

logger = get_logger(__name__)

class SelectBooksDialog(ModalScreen[Optional[str]]):
    CSS_PATH = "../styles/select_books_dialog_overrides.tcss"
    """选择书籍对话框：输入开始ID和截止ID，检索并列出可选书籍，返回选中ID（逗号分隔）"""
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("g", "ok_btn", get_global_i18n().t('common.ok')),
        ("escape", "cancel_btn", get_global_i18n().t('common.cancel')),
        ("s", "search_btn", get_global_i18n().t('common.search')),
    ]

    def __init__(self, theme_manager, novel_site: Dict[str, Any]):
        super().__init__()
        self.theme_manager = theme_manager
        self.novel_site = novel_site
        self.db_manager = DatabaseManager()
        # (id, title, status, desc)
        self._results: List[Tuple[str, str, str, str]] = []
        self._selected: Set[str] = set()
        # 初始化解析器以统一站点规则与代理
        try:
            parser_name = self.novel_site.get("parser")
            proxy_config = self._get_proxy_config()
            self.parser_instance = create_parser(parser_name, proxy_config) if parser_name else None
        except Exception:
            self.parser_instance = None
        self.loading_animation = None  # 加载动画组件
        self.loading_indicator = None  # 原生 LoadingIndicator 引用
        self.loading_overlay = None  # 加载覆盖层
        self.is_mounted_flag = False  # 组件挂载标志
        # 搜索任务与取消控制
        self._cancel_event: threading.Event = threading.Event()
        self._search_worker = None
        self._is_searching: bool = False

    def _cancel_search(self) -> None:
        """请求取消当前搜索任务，并尽可能终止后台worker与加载动画。"""
        try:
            self._cancel_event.set()
        except Exception:
            pass
        # 尝试取消后台worker（如果Textual版本支持）
        try:
            if self._search_worker is not None:
                cancel_method = getattr(self._search_worker, "cancel", None)
                if callable(cancel_method):
                    cancel_method()
        except Exception:
            pass
        # 隐藏加载动画
        self._hide_loading_animation()

    def compose(self) -> ComposeResult:
        yield Container(
            Grid(
                Vertical(
                    Label(get_global_i18n().t('select_books.select_books'), id="get-books-title"),
                ),
                # 顶部工具栏（与书架屏幕风格一致）
                Vertical(
                    Horizontal(
                        Input(placeholder=get_global_i18n().t('select_books.start_id'), id="start-id-input"),
                        Label("-", id="seprator"),
                        Input(placeholder=get_global_i18n().t('select_books.end_id'), id="end-id-input"),
                        Button(get_global_i18n().t("common.search"), id="search-btn", classes="btn"),
                        id="id-range-row",
                        classes="btn-row"
                    ),
                    id="select-books-header"
                ),
                # 中间数据表区域
                DataTable(id="books-table"),
                # 统计信息区域（与书架屏幕一致的ID，方便样式复用）
                # Vertical(
                #     Label("", id="books-stats-label"),
                #     id="books-stats-area"
                # ),
                # 加载动画区域 - 确保有足够高度显示
                Static("", id="books-stats-label", classes="loading-animation-container"),
                # 底部按钮栏
                Horizontal(
                    Button(get_global_i18n().t("common.ok"), id="ok-btn", variant="primary", classes="btn"),
                    Button(get_global_i18n().t("common.cancel"), id="cancel-btn", variant="error", classes="btn"),
                    id="buttons-row",
                    classes="btn-row"
                ),
                id="select-books-root"
            ),
            id="select-books-dialog"
        )

    def on_mount(self) -> None:
        # 设置挂载标志
        self.is_mounted_flag = True
        
        # 应用主题（如果可用）
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass
        
        # 初始化加载动画
        self._initialize_loading_animation()
        # 设置Grid布局的行高分配，确保加载动画有足够空间
        try:
            grid = self.query_one("Grid")
            grid.styles.grid_size_rows = 5
            grid.styles.grid_size_columns = 1
            grid.styles.grid_rows = ("5%", "15%", "55%", "15%", "10%")  # 给加载动画分配5%空间
        except Exception:
            pass
        # 创建覆盖层：挂载到屏幕（全屏覆盖），居中显示加载指示器
        try:
            if not hasattr(self, "loading_overlay"):
                overlay_indicator = LoadingIndicator(id="select-books-overlay-indicator")
                self.loading_overlay = Container(
                    overlay_indicator,
                    id="select-books-loading-overlay"
                )
                # 覆盖层样式：全屏覆盖、居中、半透明背景，初始隐藏；置于 overlay 图层并顶端 dock
                try:
                    self.loading_overlay.styles.display = "none"
                    self.loading_overlay.styles.layer = "overlay"
                    self.loading_overlay.styles.dock = "top"
                    self.loading_overlay.styles.width = "100%"
                    self.loading_overlay.styles.height = "100%"
                    self.loading_overlay.styles.align_horizontal = "center"
                    self.loading_overlay.styles.align_vertical = "middle"
                    self.loading_overlay.styles.background = "rgba(0,0,0,0.15)"
                except Exception:
                    pass
            # 挂载覆盖层到屏幕本身，避免受容器布局影响
            try:
                if self.loading_overlay is not None:
                    self.mount(self.loading_overlay)
            except Exception:
                pass
        except Exception:
            pass
        # Label 自动换行，避免长简介不显示
        try:
            stats_label = self.query_one("#books-stats-label", Static)
            stats_label.styles.text_wrap = "wrap"
        except Exception:
            pass
        # 初始化表格
        table = self.query_one("#books-table", DataTable)
        table.clear(columns=True)
        table.add_column(get_global_i18n().t('select_books.selected'), key="selected")
        table.add_column(get_global_i18n().t('select_books.id'), key="id")
        table.add_column(get_global_i18n().t('select_books.title'), key="title")
        table.add_column(get_global_i18n().t('select_books.status'), key="status")
        table.add_column(get_global_i18n().t('select_books.desc'), key="desc")
        table.zebra_stripes = True
        table.show_cursor = True
        table.cursor_type = "cell"
        # 样式启用自动换行
        try:
            table.styles.text_wrap = "wrap"
        except Exception:
            pass
        # 设置列宽，给简介列足够宽度触发自动换行
        try:
            table.set_column_width(0, 6)   # 选中
            table.set_column_width(1, 10)  # ID
            table.set_column_width(2, 24)  # 标题
            table.set_column_width(3, 16)  # 状态
            table.set_column_width(4, 40)  # 简介
        except Exception:
            pass
        # 聚焦开始ID
        self.query_one("#start-id-input", Input).focus()

    def _build_test_urls(self, book_id: str) -> List[str]:
        base = self.novel_site.get("url", "").rstrip("/")
        patterns: List[str] = []
        pattern = self.novel_site.get("detail_url_pattern")
        if isinstance(pattern, str) and "{id}" in pattern:
            patterns.append(pattern.format(id=book_id))
        patterns.extend([
            f"{base}/book/{book_id}.html",
            f"{base}/{book_id}.html",
            f"{base}/book/{book_id}/",
        ])
        # 去重保持顺序
        seen = set()
        uniq: List[str] = []
        for u in patterns:
            if u not in seen:
                uniq.append(u)
                seen.add(u)
        return uniq

    def _get_proxies(self) -> Optional[Dict[str, str]]:
        try:
            enabled_proxy = self.db_manager.get_enabled_proxy()
            if not enabled_proxy:
                return None
            ptype = (enabled_proxy.get("type", "HTTP") or "HTTP").lower()
            host = enabled_proxy.get("host") or ""
            port = enabled_proxy.get("port") or ""
            username = enabled_proxy.get("username") or ""
            password = enabled_proxy.get("password") or ""
            if not host or not port:
                return None
            if username and password:
                url = f"{ptype}://{username}:{password}@{host}:{port}"
            else:
                url = f"{ptype}://{host}:{port}"
            return {"http": url, "https": url}
        except Exception as e:
            logger.debug(f"获取代理失败: {e}")
            return None

    def _get_proxy_config(self) -> Dict[str, Any]:
        try:
            enabled_proxy = self.db_manager.get_enabled_proxy()
            if not enabled_proxy:
                return {"enabled": False, "proxy_url": ""}
            ptype = (enabled_proxy.get("type", "HTTP") or "HTTP").lower()
            host = enabled_proxy.get("host") or ""
            port = enabled_proxy.get("port") or ""
            username = enabled_proxy.get("username") or ""
            password = enabled_proxy.get("password") or ""
            if not host or not port:
                return {"enabled": False, "proxy_url": ""}
            if username and password:
                url = f"{ptype}://{username}:{password}@{host}:{port}"
            else:
                url = f"{ptype}://{host}:{port}"
            return {"enabled": True, "proxy_url": url}
        except Exception:
            return {"enabled": False, "proxy_url": ""}

    def _fetch_one(self, book_id: str) -> Optional[Tuple[str, str, str, str]]:
        """优先使用解析器获取标题/状态/简介，失败时回退到 requests+BeautifulSoup；支持取消"""
        if self._cancel_event.is_set():
            return None
        # 解析器优先
        try:
            if self._cancel_event.is_set():
                return None
            if self.parser_instance and hasattr(self.parser_instance, "get_homepage_meta"):
                meta = self.parser_instance.get_homepage_meta(book_id)  # type: ignore[attr-defined]
                if self._cancel_event.is_set():
                    return None
                if meta and (meta.get("title") or meta.get("desc") or meta.get("status")):
                    return (
                        book_id,
                        meta.get("title", "") or "",
                        meta.get("status", "") or "",
                        meta.get("desc", "") or ""
                    )
        except Exception as e:
            logger.debug(f"解析器获取首页元信息失败: {e}")
        # 回退请求
        proxies = self._get_proxies()
        headers = {"User-Agent": "Mozilla/5.0 TextualReader/6.3"}
        for url in self._build_test_urls(book_id):
            if self._cancel_event.is_set():
                return None
            try:
                resp = requests.get(url, timeout=2, proxies=proxies, headers=headers)
                if self._cancel_event.is_set():
                    return None
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else ""
                desc_div = soup.find("div", class_="decs hangd")
                desc = (desc_div.get_text(strip=True) if desc_div else "")
                # 状态尝试两种站点
                status = ""
                ty_div = soup.find("div", class_="ty")
                if ty_div:
                    status = ty_div.get_text(strip=True).replace("\xa0", " ").replace("&nbsp;", " ").strip()
                else:
                    bookdes = soup.find("div", class_="bookdes")
                    if bookdes:
                        p_list = bookdes.find_all("p")
                        if p_list:
                            status = p_list[0].get_text(separator="", strip=True).replace("\xa0", " ").replace("&nbsp;", " ").strip()
                if title or desc or status:
                    return (book_id, title, status, desc)
            except Exception as e:
                if self._cancel_event.is_set():
                    return None
                logger.debug(f"抓取 {book_id} 失败: {e}")
        return None

    def _should_skip(self, book_id: str) -> bool:
        try:
            site_id = self.novel_site.get("id")
            if not site_id:
                return False
            return self.db_manager.check_novel_exists(site_id, book_id)
        except Exception:
            return False

    def _search_range(self, start_id: int, end_id: int) -> List[Tuple[str, str, str, str]]:
        results: List[Tuple[str, str, str, str]] = []
        if end_id < start_id:
            start_id, end_id = end_id, start_id
        for i in range(start_id, end_id + 1):
            if self._cancel_event.is_set():
                break
            sid = str(i)
            if self._should_skip(sid):
                continue
            item = self._fetch_one(sid)
            if self._cancel_event.is_set():
                break
            if item:
                results.append(item)
        return results

    def _refresh_table(self) -> None:
        table = self.query_one("#books-table", DataTable)
        table.clear()
        # 使用行键为书籍ID；简介列传入 Rich Text 并允许自动换行
        for (bid, title, status, desc) in self._results:
            mark = "✔" if bid in self._selected else "□"
            # 直接传入 Text，no_wrap=False 允许自动折行；不预插入换行，交给 Rich 根据列宽折行
            desc_text = Text(str(desc or ""), no_wrap=False, overflow="fold")
            try:
                table.add_row(mark, bid, title, status, desc_text, key=bid)
            except Exception:
                table.add_row(mark, bid, title, status, desc_text)
        # 默认显示首行的简介到底部标签（如果有结果）
        try:
            if self._results:
                first_desc = self._results[0][3] if len(self._results[0]) > 3 else ""
                stats_label = self.query_one("#books-stats-label", Static)
                stats_label.update(str(first_desc or ""))
                # 自动聚焦到表格中
                table.focus()
        except Exception as e:
            logger.debug(f"默认简介更新失败: {e}")

    def _update_stats_with_desc(self, row_index: int) -> None:
        """将指定行的简介内容更新到统计标签（兼容不同Textual版本的DataTable行访问）"""
        try:
            table = self.query_one("#books-table", DataTable)
            # 通过索引解析真实的行键
            keys = list(table.rows.keys())
            if not keys or row_index is None or row_index < 0 or row_index >= len(keys):
                return
            row_key = keys[row_index]
            # 优先使用 row_key 获取行
            row = None
            try:
                row = table.get_row(row_key)
            except Exception:
                # 兼容方法：某些版本提供 get_row_at(index)
                try:
                    if hasattr(table, "get_row_at"):
                        row = table.get_row_at(row_index)  # type: ignore[attr-defined]
                    else:
                        row = table.get_row(row_index)
                except Exception:
                    row = None
            if row is None:
                return
            desc_val = row[4] if len(row) > 4 else ""
            desc_str = desc_val.plain if isinstance(desc_val, Text) else str(desc_val or "")
            label = self.query_one("#books-stats-label", Static)
            label.update(desc_str)
        except Exception as e:
            logger.debug(f"更新简介到统计标签失败: {e}")

    def _show_loading_animation(self, message: Optional[str] = None) -> None:
        """显示加载动画（Textual LoadingIndicator + textual_animation_manager + 经典 animation_manager）"""
        if message is None:
            message = get_global_i18n().t("common.on_action")
        logger.debug(f"开始显示加载动画: {message}")
        
        # 确保加载动画组件已初始化
        if self.loading_animation is None:
            logger.debug("加载动画组件未初始化，立即初始化")
            self._initialize_loading_animation()
        
        try:
            # 显示自定义加载动画（优先）
            try:
                if self.loading_animation is not None:
                    logger.debug("自定义加载动画组件存在，开始显示")
                    self.loading_animation.show(message)
                    logger.debug("自定义加载动画显示成功")
                else:
                    # 如果加载动画仍然不存在，尝试重新初始化
                    logger.warning("自定义加载动画组件仍然不存在，尝试重新初始化")
                    self._initialize_loading_animation()
                    
                    # 延迟显示加载动画
                    def delayed_show():
                        if self.loading_animation is not None:
                            logger.debug("延迟显示自定义加载动画")
                            self.loading_animation.show(message)
                            logger.debug("延迟自定义加载动画显示成功")
                        else:
                            logger.error("延迟显示时加载动画组件仍为None")
                    
                    self.set_timer(0.1, delayed_show)
            except Exception as e:
                logger.error(f"显示自定义加载动画失败: {e}")

            # 原生 LoadingIndicator：显示
            try:
                if not hasattr(self, "loading_indicator") or self.loading_indicator is None:
                    self.loading_indicator = self.query_one("#select-books-loading-indicator", LoadingIndicator)
            except Exception:
                pass
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    # 显示原生 LoadingIndicator（统计区）
                    self.loading_indicator.styles.display = "block"
            except Exception:
                pass
            # 显示覆盖层居中指示器
            try:
                if hasattr(self, "loading_overlay") and self.loading_overlay:
                    self.loading_overlay.styles.display = "block"
            except Exception:
                pass

            # Textual 集成加载动画
            try:
                from src.ui.components.textual_loading_animation import textual_animation_manager
                textual_animation_manager.show_default(message)
            except Exception:
                pass

            # 回退到经典加载动画
            try:
                from src.ui.components.loading_animation import animation_manager
                animation_manager.show_default(message)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"显示加载动画失败: {e}")

    def _initialize_loading_animation(self) -> None:
        """初始化加载动画"""
        logger.debug("开始初始化加载动画")
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
                loading_container = self.query_one("#books-stats-label", Static)
                logger.debug(f"加载动画容器查询成功: {loading_container}")
                
                # 创建加载动画组件并挂载到容器
                self.loading_animation = TextualLoadingAnimation()
                logger.debug(f"创建加载动画组件: {self.loading_animation}")
                loading_container.mount(self.loading_animation)
                logger.debug("加载动画组件挂载成功")
                
                # 同时创建并挂载原生 LoadingIndicator（初始隐藏）
                try:
                    self.loading_indicator = LoadingIndicator(id="select-books-loading-indicator")
                    self.loading_indicator.styles.display = "none"
                    loading_container.mount(self.loading_indicator)
                    logger.debug("原生 LoadingIndicator 挂载成功")
                except Exception as e:
                    logger.warning(f"原生 LoadingIndicator 挂载失败: {e}")

                # 设置默认动画
                textual_animation_manager.set_default_animation(self.loading_animation)
                logger.debug("默认动画设置成功")
                
                logger.debug("加载动画组件初始化成功")
            except Exception as e:
                logger.error(f"加载动画组件初始化失败: {e}")
                self.loading_animation = None
            
        except Exception as e:
            logger.error(f"加载动画组件初始化过程失败: {e}")
            self.loading_animation = None

    def _hide_loading_animation(self) -> None:
        """隐藏加载动画（Textual LoadingIndicator + textual_animation_manager + 经典 animation_manager）"""
        try:
            # 原生 LoadingIndicator：隐藏
            try:
                if hasattr(self, "loading_indicator") and self.loading_indicator:
                    # 隐藏原生 LoadingIndicator（统计区）
                    self.loading_indicator.styles.display = "none"
            except Exception:
                pass
            # 隐藏覆盖层
            try:
                if hasattr(self, "loading_overlay") and self.loading_overlay:
                    self.loading_overlay.styles.display = "none"
            except Exception:
                pass

            # Textual 集成加载动画隐藏
            try:
                from src.ui.components.textual_loading_animation import textual_animation_manager
                textual_animation_manager.hide_default()
            except Exception:
                pass

            # 经典加载动画隐藏
            try:
                from src.ui.components.loading_animation import animation_manager
                animation_manager.hide_default()
            except Exception:
                pass
            
            # 隐藏自定义加载动画
            try:
                if hasattr(self, 'loading_animation') and self.loading_animation:
                    self.loading_animation.hide()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"隐藏加载动画失败: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-btn":
            # 若已有搜索在进行，避免重复启动
            if getattr(self, "_is_searching", False):
                try:
                    self.app.bell()
                except Exception:
                    pass
                return
            # 先显示加载动画
            self._show_loading_animation(get_global_i18n().t("common.on_action"))
            # 置为搜索中并禁用确认/搜索按钮
            try:
                self._is_searching = True
                self.query_one("#search-btn", Button).disabled = True
                self.query_one("#ok-btn", Button).disabled = True
            except Exception:
                pass
            # 延迟启动搜索，确保动画有足够时间显示
            def delayed_search():
                # 异步执行搜索
                async def async_search():
                    try:
                        start_input = self.query_one("#start-id-input", Input).value.strip()
                        end_input = self.query_one("#end-id-input", Input).value.strip()
                        if not (start_input and end_input) or not start_input.isdigit() or not end_input.isdigit():
                            self.app.bell()
                            return
                        start_id = int(start_input)
                        end_id = int(end_input)
                        
                        # 执行搜索（将阻塞型任务放入线程池，确保UI可响应取消）
                        self._results = await asyncio.to_thread(self._search_range, start_id, end_id)
                        if self._cancel_event.is_set():
                            return
                        self._selected.clear()
                        self._refresh_table()
                    except Exception as e:
                        logger.error(f"搜索失败: {e}")
                    finally:
                        # 隐藏双加载动画
                        self._hide_loading_animation()
                        # 结束搜索状态并恢复按钮
                        try:
                            self._is_searching = False
                            self.query_one("#search-btn", Button).disabled = False
                            self.query_one("#ok-btn", Button).disabled = False
                        except Exception:
                            pass
                        # 若搜索被取消，此处无需特殊返回，函数自然结束
                
                # 启动异步搜索任务（保存句柄，并在启动前清理取消标志）
                try:
                    self._cancel_event.clear()
                except Exception:
                    pass
                self._search_worker = self.app.run_worker(async_search(), name="select-books-search", exclusive=False)
            
            # 延迟100ms启动搜索，确保动画完全显示
            self.set_timer(0.1, delayed_search)
        elif event.button.id == "ok-btn":
            selected_str = ",".join(sorted(self._selected, key=lambda x: int(x) if x.isdigit() else x))
            self.dismiss(selected_str)
        elif event.button.id == "cancel-btn":
            # 触发取消
            self._cancel_search()
            # 关闭对话框
            self.dismiss(None)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """回车选择当前行：切换选中状态并更新底部简介"""
        table = self.query_one("#books-table", DataTable)
        try:
            # 优先使用事件提供的行键定位索引，避免依赖 cursor_row
            row_index = None
            try:
                evt_row_key = getattr(event, "row_key", None)
                if evt_row_key is not None:
                    keys = list(table.rows.keys())
                    row_index = keys.index(evt_row_key)
            except Exception:
                pass
            if row_index is None:
                row_index = getattr(table, "cursor_row", None)
            if row_index is None:
                return
            # 取行键（ID）
            try:
                row_key = list(table.rows.keys())[row_index]
                bid = str(getattr(row_key, "value", row_key))
            except Exception:
                row = table.get_row(row_index)
                bid = str(row[1]) if len(row) > 1 else ""
                row_key = row_index
            if not bid:
                return
            # 切换选中状态
            if bid in self._selected:
                self._selected.remove(bid)
            else:
                self._selected.add(bid)
            # 更新“选中”列标记
            try:
                selected_col_key = table.ordered_columns[0].key
                table.update_cell(row_key, selected_col_key, "✔" if bid in self._selected else "□")
            except Exception:
                table.update_cell(row_index, 0, "✔" if bid in self._selected else "□")
            # 同步当前行的简介到底部统计标签
            try:
                self._update_stats_with_desc(row_index)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"切换选中失败: {e}")

    @on(DataTable.CellSelected, "#books-table")
    def on_books_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """
        单元格选择事件：点击任意列均更新底部简介；仅当点击“选中”列（第一列）时，切换该行的选中状态。
        """
        table = event.data_table if hasattr(event, "data_table") else self.query_one("#books-table", DataTable)
        coord = getattr(event, "coordinate", None)
        row_index = coord.row if coord else None
        if row_index is None:
            return
        # 获取行键（ID）
        try:
            row_key = list(table.rows.keys())[row_index]
            bid = str(getattr(row_key, "value", row_key))
        except Exception:
            row = table.get_row(row_index)
            bid = str(row[1]) if len(row) > 1 else ""
            row_key = row_index
        if not bid:
            return
        # 仅当第一列被点击时，切换选中状态
        if coord and coord.column == 0:
            if bid in self._selected:
                self._selected.remove(bid)
            else:
                self._selected.add(bid)
            # 更新“选中”列显示
            try:
                selected_col_key = table.ordered_columns[0].key
                table.update_cell(row_key, selected_col_key, "✔" if bid in self._selected else "□")
            except Exception:
                table.update_cell(row_index, 0, "✔" if bid in self._selected else "□")
        # 保持光标在当前行
        try:
            table.cursor_row = row_index
        except Exception:
            pass
        # 无论点击哪一列，都更新底部简介
        try:
            self._update_stats_with_desc(row_index)
        except Exception:
            pass
        event.stop()

    @on(DataTable.RowHighlighted, "#books-table")
    def on_books_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """行高亮变化时同步底部简介（支持键盘上下移动焦点）"""
        try:
            table = self.query_one("#books-table", DataTable)
            # 通过 row_key 查找索引，兼容不同 Textual 版本
            row_index = None
            try:
                evt_row_key = getattr(event, "row_key", None)
                if evt_row_key is not None:
                    keys = list(table.rows.keys())
                    row_index = keys.index(evt_row_key)
            except Exception:
                pass
            if row_index is None:
                row_index = getattr(table, "cursor_row", None)
            if row_index is None:
                return
            self._update_stats_with_desc(row_index)
        except Exception as e:
            logger.debug(f"高亮行更新简介失败: {e}")



    @on(DataTable.CellHighlighted, "#books-table")
    def on_books_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """单元格高亮变化时更新底部简介"""
        try:
            coord = getattr(event, "coordinate", None)
            row_index = coord.row if coord else None
            if row_index is None:
                # 回退到当前光标行
                table = self.query_one("#books-table", DataTable)
                row_index = getattr(table, "cursor_row", None)
            if row_index is None:
                return
            self._update_stats_with_desc(row_index)
        except Exception as e:
            logger.debug(f"单元格高亮更新简介失败: {e}")

    def on_key(self, event: events.Key) -> None:
        """空格键切换当前行选中状态"""
        if event.key == "space":
            table = self.query_one("#books-table", DataTable)
            row_index = getattr(table, "cursor_row", None)
            if row_index is None:
                return
            try:
                # 行键与ID
                try:
                    row_key = list(table.rows.keys())[row_index]
                    bid = str(getattr(row_key, "value", row_key))
                except Exception:
                    row = table.get_row(row_index)
                    bid = str(row[1]) if len(row) > 1 else ""
                    row_key = row_index
                if not bid:
                    return
                # 切换选中
                if bid in self._selected:
                    self._selected.remove(bid)
                else:
                    self._selected.add(bid)
                # 更新“选中”列
                try:
                    selected_col_key = table.ordered_columns[0].key
                    table.update_cell(row_key, selected_col_key, "✔" if bid in self._selected else "□")
                except Exception:
                    table.update_cell(row_index, 0, "✔" if bid in self._selected else "□")
                # 同步当前行简介到底部标签
                try:
                    self._update_stats_with_desc(row_index)
                except Exception:
                    pass
                try:
                    event.stop()
                except Exception:
                    pass
            except Exception as e:
                logger.debug(f"空格切换选中失败: {e}")

        if event.key == "escape":
            # 设置取消标志，隐藏加载动画，并安全退出对话
            # 请求取消并隐藏加载（并恢复按钮状态）
            self._cancel_search()
            try:
                self._is_searching = False
                self.query_one("#search-btn", Button).disabled = False
                self.query_one("#ok-btn", Button).disabled = False
            except Exception:
                pass
            # 关闭对话
            # 直接关闭对话框
            try:
                self.dismiss(None)
            except Exception:
                try:
                    self.app.pop_screen()
                except Exception:
                    pass
            event.stop()

    def action_ok_btn(self) -> None:
        """确认按钮点击事件"""
        selected_str = ",".join(sorted(self._selected, key=lambda x: int(x) if x.isdigit() else x))
        self.dismiss(selected_str)
    
    def action_cancel_btn(self) -> None:
        """取消按钮点击事件"""
        try:
            self._cancel_event.set()
        except Exception:
            pass
        self._hide_loading_animation()
        try:
            self._is_searching = False
            self.query_one("#search-btn", Button).disabled = False
            self.query_one("#ok-btn", Button).disabled = False
        except Exception:
            pass
        self.dismiss(None)

    def action_search_btn(self) -> None:
        """搜索按钮点击事件（模拟点击搜索按钮）"""
        try:
            # 启动搜索前清理取消标记
            try:
                self._cancel_event.clear()
            except Exception:
                pass
            btn = self.query_one("#search-btn", Button)
            # 模拟点击触发 Pressed 事件
            btn.press()
        except Exception:
            # 兼容回退：如果 press 不可用，尝试直接发送 Pressed 消息
            try:
                btn = self.query_one("#search-btn", Button)
                from textual.widgets import Button as TButton
                self.post_message(TButton.Pressed(btn))  # type: ignore[attr-defined]
            except Exception:
                pass
        # 保持焦点在搜索按钮（可选）
        try:
            self.query_one("#search-btn", Button).focus()
        except Exception:
            pass