"""
网页阅读器页面

从欢迎页点击「网页阅读器」或按 4 / F4 进入本页。
本页提供：
- 打开浏览器阅读器（打开上次阅读书籍或欢迎页）
- 检测服务状态（端口 + 各数据接口健康检查）
- 启动/停止/重启后端同步服务
- 在浏览器打开本地书籍
"""

from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

import asyncio
import os
import socket
import time

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Label, Header, Footer, Input
from textual.app import ComposeResult

from src.locales.i18n_manager import get_global_i18n, t
from src.themes.theme_manager import ThemeManager
from src.ui.styles.quick_fix_isolation import QuickIsolationMixin
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation

from src.utils.logger import get_logger

logger = get_logger(__name__)


# 待检测的接口定义：(i18n键, 方法, 路径, 是否POST)
_ENDPOINT_DEFS: List[Tuple[str, str, str, bool]] = [
    ("web_reader.endpoint_health", "GET", "/health_check", False),
    ("web_reader.endpoint_save_progress", "POST", "/save_progress", True),
    ("web_reader.endpoint_load_progress", "GET", "/load_progress", False),
    ("web_reader.endpoint_save_annotations", "POST", "/save_annotations", True),
    ("web_reader.endpoint_load_annotations", "GET", "/load_annotations", False),
    ("web_reader.endpoint_save_vocab", "POST", "/save_vocab", True),
    ("web_reader.endpoint_load_vocab", "GET", "/load_vocab", False),
    ("web_reader.endpoint_translate", "POST", "/translate", True),
    ("web_reader.endpoint_scan_directory", "POST", "/scan_directory", True),
]


class WebReaderScreen(QuickIsolationMixin, Screen[None]):
    """网页阅读器页面"""

    TITLE: Optional[str] = None
    CSS_PATH = '../styles/web_reader_screen.tcss'

    BINDINGS: ClassVar = [
        ("escape,q", "back", get_global_i18n().t('web_reader.back')),
        ("c", "check_status", get_global_i18n().t('web_reader.check_status')),
        ("o", "open_reader", get_global_i18n().t('web_reader.open_reader')),
        ("f", "browse_book_file", get_global_i18n().t('web_reader.browse_file')),
    ]

    def __init__(self, theme_manager: ThemeManager):
        super().__init__()
        self.title = t("web_reader.title")
        self.sub_title = t("app.description")
        self.theme_manager = theme_manager

    # ------------------------------------------------------------------ #
    # 组合界面
    # ------------------------------------------------------------------ #
    def compose(self) -> ComposeResult:
        i18n = get_global_i18n()
        yield Header(time_format=None, show_clock=True, id="web-reader-header", name="web-reader-header")
        yield Container(
            # Label(i18n.t('web_reader.title'), id="wr-title"),
            Label(i18n.t('web_reader.description'), id="wr-title"),
            # 顶部按钮行（参考欢迎页）
            Horizontal(
                Button(i18n.t('web_reader.open_reader'), id="wr-open-reader-btn", variant="primary"),
                Button(i18n.t('web_reader.check_status'), id="wr-check-btn", variant="success"),
                Button(i18n.t('web_reader.toggle_server'), id="wr-toggle-btn"),
                Button(i18n.t('web_reader.restart_server'), id="wr-restart-btn"),
                Button(i18n.t('web_reader.back'), id="wr-back-btn"),
                id="wr-buttons", classes="btn-row",
            ),
            # 服务信息 + 诊断结果
            Horizontal(
                Vertical(
                    Label(i18n.t('web_reader.service_info'), classes="wr-section-title"),
                    Label("", id="wr-status-label", classes="wr-info-line"),
                    Label("", id="wr-host-label", classes="wr-info-line"),
                    Label("", id="wr-port-label", classes="wr-info-line"),
                    Label("", id="wr-addr-label", classes="wr-info-line"),
                    classes="wr-panel",
                    id="wr-info-panel",
                ),
                Vertical(
                    Label(i18n.t('web_reader.diagnosis'), classes="wr-section-title"),
                    ScrollableContainer(
                        Static(i18n.t('web_reader.diag_not_run'), id="wr-diag", classes="wr-diag"),
                        id="wr-diag-scroll",
                    ),
                    classes="wr-panel",
                    id="wr-diag-panel",
                ),
                classes="wr-panels",
            ),
            # 底部：路径输入框 + 浏览文件 + 打开本地书籍
            Horizontal(
                Input(placeholder=i18n.t('web_reader.path_placeholder'), id="wr-path-input"),
                Button(i18n.t('web_reader.browse_file'), id="wr-browse-btn"),
                Button(i18n.t('web_reader.open_local'), id="wr-open-local-btn", variant="success"),
                id="wr-local-row", classes="btn-row",
            ),
            id="wr-main",
        )
        yield Footer()

    def on_mount(self) -> None:
        apply_universal_style_isolation(self)
        self.theme_manager.apply_theme_to_screen(self)
        try:
            i18n = get_global_i18n()
            type(self).BINDINGS = [
                ("escape,q", "back", i18n.t('web_reader.back')),
                ("c", "check_status", i18n.t('web_reader.check_status')),
                ("o", "open_reader", i18n.t('web_reader.open_reader')),
            ]
        except Exception:
            pass
        self._refresh_service_info()

    # ------------------------------------------------------------------ #
    # 事件处理
    # ------------------------------------------------------------------ #
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "wr-open-reader-btn":
            self.run_worker(self._open_reader)
        elif btn_id == "wr-check-btn":
            self._start_diagnosis()
        elif btn_id == "wr-toggle-btn":
            self.run_worker(self._toggle_server)
        elif btn_id == "wr-restart-btn":
            self.run_worker(self._restart_server)
        elif btn_id == "wr-open-local-btn":
            self.run_worker(self._open_local_book)
        elif btn_id == "wr-browse-btn":
            self._browse_local_book()
        elif btn_id == "wr-back-btn":
            self._back()

    def action_back(self) -> None:
        self._back()

    def action_open_reader(self) -> None:
        self.run_worker(self._open_reader)

    def action_check_status(self) -> None:
        self._start_diagnosis()

    def action_browse_book_file(self) -> None:
        self._browse_local_book()

    # ------------------------------------------------------------------ #
    # 辅助
    # ------------------------------------------------------------------ #
    def _back(self) -> None:
        try:
            self.app.pop_screen()
        except Exception:
            self.dismiss()

    @staticmethod
    async def _run_blocking(func, *args):
        """在后台线程执行阻塞操作，避免卡住 UI 事件循环"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _get_server_manager(self):
        from src.utils.browser_reader_server_manager import get_browser_reader_server_manager
        return get_browser_reader_server_manager()

    def _get_host_port(self) -> Tuple[str, int]:
        try:
            from src.config.config_manager import ConfigManager
            config = ConfigManager.get_instance().get_config()
            bs = config.get("browser_server", {})
            return bs.get("host", "localhost"), int(bs.get("port", 54321))
        except Exception:
            return "localhost", 54321

    def _refresh_service_info(self) -> None:
        i18n = get_global_i18n()
        try:
            host, port = self._get_host_port()
            running = self._get_server_manager().is_server_running()
            status_text = i18n.t('web_reader.status_running') if running else i18n.t('web_reader.status_stopped')
            status_color = "green" if running else "red"
            self.query_one("#wr-status-label", Label).update(
                f"● {status_text}"
            )
            self.query_one("#wr-status-label", Label).styles.color = (
                "green" if running else "red"
            )
            self.query_one("#wr-host-label", Label).update(f"{i18n.t('web_reader.host')}: {host}")
            self.query_one("#wr-port-label", Label).update(f"{i18n.t('web_reader.port')}: {port}")
            self.query_one("#wr-addr-label", Label).update(f"{i18n.t('web_reader.address')}: http://{host}:{port}")
            toggle_btn = self.query_one("#wr-toggle-btn", Button)
            toggle_btn.label = i18n.t('web_reader.toggle_server_stop') if running else i18n.t('web_reader.toggle_server')
        except Exception as e:
            logger.warning(f"刷新服务信息失败: {e}")

    # ------------------------------------------------------------------ #
    # 打开浏览器阅读器
    # ------------------------------------------------------------------ #
    async def _open_reader(self) -> None:
        i18n = get_global_i18n()
        try:
            from src.config.config_manager import ConfigManager
            config = ConfigManager.get_instance().get_config()
            start_page = config.get("browser", {}).get("start_page", "last_book")
            success, message = await self._run_blocking(self._open_reader_sync, start_page)
            if success:
                self.notify(i18n.t('welcome.browser_reader_opened', title="浏览器阅读器"), severity="information")
                self._refresh_service_info()
            else:
                self.notify(i18n.t('web_reader.open_reader_failed', message=message), severity="error")
        except Exception as e:
            logger.error(f"打开浏览器阅读器失败: {e}")
            self.notify(i18n.t('web_reader.open_reader_failed', message=str(e)), severity="error")

    def _open_reader_sync(self, start_page: str) -> Tuple[bool, str]:
        from src.utils.browser_reader import BrowserReader
        from src.core.bookmark import BookmarkManager

        if start_page == "last_book":
            last_book_path = None
            try:
                last_book = BookmarkManager().get_last_read_book()
                if last_book:
                    last_book_path = last_book.get('book_path')
            except Exception as e:
                logger.warning(f"获取上一次阅读书籍失败: {e}")
            if last_book_path and os.path.exists(last_book_path):
                return BrowserReader.open_book_in_browser(
                    last_book_path, theme=self.theme_manager.get_current_theme_name()
                )
            return self._create_welcome_temp_file()
        return self._create_welcome_temp_file()

    def _create_welcome_temp_file(self) -> Tuple[bool, str]:
        from src.utils.browser_reader import BrowserReader
        import tempfile

        try:
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, "welcome.txt")
            library_content = """🌐 浏览器阅读器

欢迎使用浏览器阅读器！

请使用书库功能添加书籍，或者使用文件导入功能打开本地书籍文件。

提示：
- 支持TXT、EPUB等多种格式
- 自动保存阅读进度
- 可自定义主题和字体
"""
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(library_content)
            return BrowserReader.open_book_in_browser(temp_file, theme="light")
        except Exception as e:
            logger.error(f"创建欢迎页临时文件失败: {e}")
            return False, str(e)

    def _browse_local_book(self) -> None:
        """打开文件浏览器（文件资源管理器），选择本地书籍并在浏览器中打开"""
        i18n = get_global_i18n()

        def _handle_result(result: Optional[Union[str, List[str]]]) -> None:
            if not result:
                return
            path = result[0] if isinstance(result, list) else result
            self.run_worker(self._open_book_path(path))

        try:
            from src.ui.screens.file_explorer_screen import FileExplorerScreen
            # 通过 getattr 获取，避免类型检查器对 App 基类的静态属性报错（运行时必有这两个属性）
            app = self.app
            bookshelf = getattr(app, "bookshelf", None)
            statistics_manager = getattr(app, "statistics_manager", None)
            file_explorer_screen = FileExplorerScreen(
                theme_manager=self.theme_manager,
                bookshelf=bookshelf,
                statistics_manager=statistics_manager,
                selection_mode="file",
                title=i18n.t('web_reader.browse_file_title'),
                show_all_files=True,
                default_diff_mode=False,
            )
            self.app.push_screen(file_explorer_screen, _handle_result)
        except Exception as e:
            logger.error(f"打开文件浏览器失败: {e}")
            self.notify(i18n.t('web_reader.browse_failed', message=str(e)), severity="error")

    async def _open_local_book(self) -> None:
        path = self.query_one("#wr-path-input", Input).value.strip()
        await self._open_book_path(path)

    async def _open_book_path(self, path: str) -> None:
        """在浏览器中打开指定路径的本地书籍"""
        i18n = get_global_i18n()
        if not path or not os.path.exists(path):
            self.notify(i18n.t('web_reader.invalid_path'), severity="warning")
            return
        ext = os.path.splitext(path)[1].lower()
        try:
            from src.config.default_config import SUPPORTED_FORMATS
            supported = set(SUPPORTED_FORMATS)
        except Exception:
            supported = {'.txt', '.epub', '.pdf', '.mobi', '.azw', '.azw3', '.md'}
        if ext not in supported:
            self.notify(i18n.t('web_reader.unsupported_format', ext=ext), severity="warning")
            return
        try:
            from src.utils.browser_reader import BrowserReader
            success, message = await self._run_blocking(
                BrowserReader.open_book_in_browser, path,
                self.theme_manager.get_current_theme_name()
            )
            if success:
                self.notify(i18n.t('web_reader.open_local_success', path=path), severity="information")
                self._refresh_service_info()
            else:
                self.notify(i18n.t('web_reader.open_reader_failed', message=message), severity="error")
        except Exception as e:
            logger.error(f"在浏览器打开本地书籍失败: {e}")
            self.notify(i18n.t('web_reader.open_reader_failed', message=str(e)), severity="error")

    # ------------------------------------------------------------------ #
    # 服务启停
    # ------------------------------------------------------------------ #
    async def _toggle_server(self) -> None:
        i18n = get_global_i18n()
        try:
            mgr = self._get_server_manager()
            if mgr.is_server_running():
                await self._run_blocking(mgr.stop_server)
                self.notify(i18n.t('web_reader.server_stopped'), severity="information")
            else:
                ok = await self._run_blocking(mgr.start_server)
                if ok:
                    self.notify(i18n.t('web_reader.server_started'), severity="information")
                else:
                    self.notify(i18n.t('web_reader.server_start_failed', message="未知错误"), severity="error")
        except Exception as e:
            logger.error(f"切换服务状态失败: {e}")
            self.notify(i18n.t('web_reader.server_start_failed', message=str(e)), severity="error")
        self._refresh_service_info()

    async def _restart_server(self) -> None:
        i18n = get_global_i18n()
        try:
            mgr = self._get_server_manager()
            await self._run_blocking(mgr.stop_server)
            time.sleep(0.3)
            ok = await self._run_blocking(mgr.start_server)
            if ok:
                self.notify(i18n.t('web_reader.server_restarted'), severity="information")
            else:
                self.notify(i18n.t('web_reader.server_start_failed', message="未知错误"), severity="error")
        except Exception as e:
            logger.error(f"重启服务失败: {e}")
            self.notify(i18n.t('web_reader.server_start_failed', message=str(e)), severity="error")
        self._refresh_service_info()

    # ------------------------------------------------------------------ #
    # 服务状态诊断
    # ------------------------------------------------------------------ #
    def _start_diagnosis(self) -> None:
        self.query_one("#wr-diag", Static).update(get_global_i18n().t('web_reader.diag_running'))
        self.run_worker(self._diagnosis_worker, exclusive=True, group="wr-diag")

    async def _diagnosis_worker(self) -> None:
        result = await self._run_blocking(self._diagnose)
        self._render_diagnosis(result)

    def _diagnose(self) -> Dict[str, Any]:
        i18n = get_global_i18n()
        host, port = self._get_host_port()
        base = f"http://{host}:{port}"

        port_open = False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            port_open = sock.connect_ex((host, port)) == 0
            sock.close()
        except Exception:
            port_open = False

        endpoints: List[Dict[str, Any]] = []
        if not port_open:
            for key, _m, _p, _post in _ENDPOINT_DEFS:
                endpoints.append({"name_key": key, "status": "fail", "detail": i18n.t('web_reader.not_reachable')})
            return {"port_open": False, "base": base, "endpoints": endpoints,
                    "overall": "fail", "timestamp": time.strftime("%H:%M:%S")}

        import json
        import urllib.request
        import urllib.error

        for name_key, method, path, is_post in _ENDPOINT_DEFS:
            detail = ""
            ok = False
            try:
                if method == "GET":
                    req = urllib.request.Request(f"{base}{path}", method="GET")
                else:
                    if path == "/save_progress":
                        payload = json.dumps({
                            "progress": 0.0, "scrollTop": 0, "scrollHeight": 0,
                            "current_page": 0, "total_pages": 0, "word_count": 0
                        }).encode()
                        req = urllib.request.Request(f"{base}{path}", data=payload, method="POST")
                        req.add_header("Content-Type", "application/json")
                        req.add_header("X-Book-ID", "__diag__")
                    elif path == "/save_annotations":
                        payload = json.dumps({"book_id": "__diag__", "highlights": [], "notes": [], "bookmarks": []}).encode()
                        req = urllib.request.Request(f"{base}{path}", data=payload, method="POST")
                        req.add_header("Content-Type", "application/json")
                    elif path == "/save_vocab":
                        # OPTIONS 探测，避免写入用户单词本
                        req = urllib.request.Request(f"{base}{path}", method="OPTIONS")
                    elif path == "/translate":
                        payload = json.dumps({"text": "hello", "target_lang": "zh", "source_lang": "auto"}).encode()
                        req = urllib.request.Request(f"{base}{path}", data=payload, method="POST")
                        req.add_header("Content-Type", "application/json")
                    else:  # /scan_directory
                        payload = json.dumps({"directory": "", "recursive": True}).encode()
                        req = urllib.request.Request(f"{base}{path}", data=payload, method="POST")
                        req.add_header("Content-Type", "application/json")
                req.add_header("Connection", "close")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    code = resp.status
                    if 200 <= code < 300:
                        status = "ok"
                        detail = f"HTTP {code}"
                    elif 400 <= code < 500:
                        status = "warn"
                        detail = f"HTTP {code}（接口可达，多为无数据或参数问题）"
                    else:
                        status = "fail"
                        detail = f"HTTP {code}"
            except urllib.error.HTTPError as e:
                code = e.code
                if 200 <= code < 300:
                    status = "ok"
                    detail = f"HTTP {code}"
                elif 400 <= code < 500:
                    status = "warn"
                    detail = f"HTTP {code}（接口可达，多为无数据或参数问题）"
                else:
                    status = "fail"
                    detail = f"HTTP {code}"
            except Exception:
                status = "fail"
                detail = i18n.t('web_reader.not_reachable')

            endpoints.append({"name_key": name_key, "status": status, "detail": detail})

        fail_count = sum(1 for e in endpoints if e["status"] == "fail")
        warn_count = sum(1 for e in endpoints if e["status"] == "warn")
        overall = "fail" if fail_count > 0 else ("partial" if warn_count > 0 else "ok")
        return {"port_open": True, "base": base, "endpoints": endpoints,
                "overall": overall, "timestamp": time.strftime("%H:%M:%S")}

    def _render_diagnosis(self, result: Dict[str, Any]) -> None:
        i18n = get_global_i18n()
        lines: List[str] = []
        if result.get("port_open"):
            lines.append(f"[b]{i18n.t('web_reader.address')}:[/b] {result['base']}  [green]● {i18n.t('web_reader.status_running')}[/green]")
        else:
            lines.append(f"[b]{result.get('base')}[/b]  [red]● {i18n.t('web_reader.status_stopped')}[/red]")

        for ep in result.get("endpoints", []):
            name = i18n.t(ep["name_key"])
            status = ep.get("status", "fail")
            if status == "ok":
                lines.append(f"  [green]✓[/green] {name}  [dim]{ep['detail']}[/dim]")
            elif status == "warn":
                lines.append(f"  [yellow]⚠[/yellow] {name}  [yellow]{ep['detail']}[/yellow]")
            else:
                lines.append(f"  [red]✗[/red] {name}  [red]{ep['detail']}[/red]")

        overall = result.get("overall")
        if overall == "ok":
            lines.append(f"\n[green]{i18n.t('web_reader.diag_overall_ok')}[/green]")
        elif overall == "partial":
            lines.append(f"\n[yellow]{i18n.t('web_reader.diag_overall_partial')}[/yellow]")
        else:
            lines.append(f"\n[red]{i18n.t('web_reader.diag_overall_fail')}[/red]")

        lines.append(f"[dim]{i18n.t('web_reader.last_check')}: {result.get('timestamp')}[/dim]")
        self.query_one("#wr-diag", Static).update("\n".join(lines))
        self._refresh_service_info()
