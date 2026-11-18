"""全局日志查看器弹窗（内存模式 / 文件模式）。

统一日志弹窗的界面与刷新逻辑，供批量操作、爬取管理界面及全局快捷键复用。
"""
import asyncio
import os

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, Log

from src.locales.i18n_manager import get_global_i18n
from src.utils.logger import get_logger, get_recent_memory_logs

logger = get_logger(__name__)


class LogViewerPopup(ModalScreen[None]):
    """日志查看器弹窗"""

    BINDINGS = [
        ("escape", "close", get_global_i18n().t('crawler.close_popup')),
        ("q", "force_close", get_global_i18n().t('crawler.force_close')),
        ("e", "scroll_to_bottom", get_global_i18n().t('crawler.scroll_to_bottom')),
        ("c", "sync_close", get_global_i18n().t('crawler.sync_close')),
    ]

    DEFAULT_CSS = """
    LogViewerPopup {
        height: 80%;
        width: 80%;
        align: center middle;
    }

    LogViewerPopup > Container {
        width: 90%;
        height: 90%;
        align: center middle;
        background: $surface;
        border: solid $accent;
    }

    .log-popup-container {
        width: 85%;
        height: 85%;
        align: center middle;
        layout: vertical;
    }

    .log-popup-header {
        height: 1;
        background: $accent;
        color: $text;
        content-align: center middle;
    }

    .log-popup-controls {
        height: 4;
        margin: 0 0 1 0;
    }

    #close-log-btn, #toggle-scroll-btn, #clear-log-btn, #refresh-log-btn {
        margin: 0;
        padding: 0;
        border: none;
        height: 3;
    }

    .log-popup-content {
        height: 55%;
        background: $background;
    }

    #log-viewer {
        width: 100%;
        height: 40%;
        background: $background;
        padding: 5 1 5 1;
        border: solid $border;
        overflow: auto;
    }
    """

    def __init__(self, log_file_path: str, memory_mode: bool = False):
        super().__init__()
        self.log_file_path = log_file_path
        self.memory_mode = memory_mode
        self.auto_scroll = True
        self.last_position = 0
        self.file_watcher_task = None
        self.stop_watching = False
        self._memory_last_line = None  # 内存模式增量同步游标：已显示的最后一条日志

    def compose(self) -> ComposeResult:
        """组合日志查看器界面"""
        yield Header()
        yield Container(
            Vertical(
                # 标题栏
                Horizontal(
                    Label(
                        f"📋 {get_global_i18n().t('crawler.viewing_logs')}: "
                        f"{'内存日志' if self.memory_mode else os.path.basename(self.log_file_path)}",
                        classes="log-popup-title",
                    ),
                    classes="log-popup-header",
                ),
                # 控制按钮
                Horizontal(
                    Button(get_global_i18n().t('common.close'), id="close-log-btn", variant="primary"),
                    Button(get_global_i18n().t('crawler.toggle_auto_scroll'), id="toggle-scroll-btn", variant="default"),
                    Button(get_global_i18n().t('crawler.clear_display'), id="clear-log-btn", variant="warning"),
                    Button(get_global_i18n().t('crawler.refresh_log'), id="refresh-log-btn", variant="success"),
                    classes="log-popup-controls",
                ),
                # 日志内容区域
                Log(id="log-viewer", auto_scroll=True, max_lines=1000, classes="log-popup-content"),
                classes="log-popup-container",
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """弹窗挂载时的回调"""
        if self.memory_mode:
            self._load_memory_content()
            self.set_interval(1.0, self._refresh_memory_content)
        else:
            self._load_initial_log_content()
            self._start_file_watching()

        try:
            self.query_one("#close-log-btn", Button).focus()
        except Exception:
            pass

        self.set_timer(0.05, self._ensure_scroll_to_bottom)

    async def on_unmount(self) -> None:
        """弹窗卸载时的回调"""
        await self._stop_file_watching()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下事件处理"""
        if event.button.id == "close-log-btn":
            asyncio.create_task(self._async_close())
        elif event.button.id == "toggle-scroll-btn":
            self._toggle_auto_scroll()
        elif event.button.id == "clear-log-btn":
            self._clear_log_content()
        elif event.button.id == "refresh-log-btn":
            self._refresh_log_content()

    async def _async_close(self) -> None:
        """异步关闭弹窗"""
        try:
            await self._stop_file_watching()
            self.dismiss()
        except Exception as e:
            logger.error(f"关闭日志查看器失败: {e}")
            await self._force_close()

    def _load_initial_log_content(self) -> None:
        """加载初始日志内容"""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    log_viewer = self.query_one("#log-viewer", Log)
                    log_viewer.clear()
                    # 只显示最后1000行
                    lines = content.split('\n')
                    if len(lines) > 1000:
                        lines = lines[-1000:]
                    log_viewer.write('\n'.join(lines))
                    self.last_position = len(content.encode('utf-8'))

                    if self.auto_scroll:
                        self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
                        self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
            else:
                log_viewer = self.query_one("#log-viewer", Log)
                log_viewer.write(f"📁 {get_global_i18n().t('crawler.log_file_not_found')}: {self.log_file_path}")
        except Exception as e:
            logger.error(f"加载日志内容失败: {e}")
            log_viewer = self.query_one("#log-viewer", Log)
            log_viewer.write(f"❌ {get_global_i18n().t('crawler.load_log_failed')}: {e}")

    def _load_memory_content(self) -> None:
        """全量加载内存日志（首次打开/手动刷新时使用）"""
        try:
            log_viewer = self.query_one("#log-viewer", Log)
            log_viewer.clear()
            lines = get_recent_memory_logs(1000)
            if lines:
                log_viewer.write('\n'.join(lines))
                self._memory_last_line = lines[-1]
            else:
                self._memory_last_line = None
                log_viewer.write("💡 内存中暂无日志记录（当前未写入文件日志）")
            if self.auto_scroll:
                self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
        except Exception as e:
            logger.error(f"加载内存日志失败: {e}")

    def _refresh_memory_content(self) -> None:
        """增量同步内存日志：只追加新日志，不清空/重写历史，保留用户滚动位置。"""
        try:
            lines = get_recent_memory_logs(1000)
            if not lines:
                return

            if self._memory_last_line is None:
                new_lines = lines
            else:
                # 从后往前定位上次同步的最后一条，避免内容相同的日志行导致定位偏差
                idx = None
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i] == self._memory_last_line:
                        idx = i
                        break
                new_lines = lines[idx + 1:] if idx is not None else lines

            if not new_lines:
                return

            log_viewer = self.query_one("#log-viewer", Log)
            if self._memory_last_line is None:
                # 清掉此前的「暂无日志」占位提示
                log_viewer.clear()
            log_viewer.write('\n'.join(new_lines))
            self._memory_last_line = lines[-1]

            if self.auto_scroll:
                self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
        except Exception:
            pass

    def _start_file_watching(self) -> None:
        """启动文件监控任务"""
        self.stop_watching = False
        self.file_watcher_task = asyncio.create_task(self._watch_file_changes())

    async def _stop_file_watching(self) -> None:
        """停止文件监控"""
        try:
            self.stop_watching = True
            if self.file_watcher_task and not self.file_watcher_task.done():
                self.file_watcher_task.cancel()
                try:
                    await asyncio.wait_for(self.file_watcher_task, timeout=0.1)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        except Exception as e:
            logger.error(f"停止文件监控失败: {e}")

    async def _watch_file_changes(self) -> None:
        """异步监控文件变化"""
        while not self.stop_watching:
            try:
                if os.path.exists(self.log_file_path):
                    current_size = os.path.getsize(self.log_file_path)
                    if current_size > self.last_position:
                        with open(self.log_file_path, 'r', encoding='utf-8') as f:
                            f.seek(self.last_position)
                            new_content = f.read()

                        try:
                            log_viewer = self.query_one("#log-viewer", Log)
                            log_viewer.write(new_content)
                            if self.auto_scroll:
                                self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
                                self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
                        except Exception:
                            self.stop_watching = True
                            break

                        self.last_position = current_size
                else:
                    self.last_position = 0
            except Exception as e:
                logger.error(f"监控日志文件变化失败: {e}")
                self.stop_watching = True
                break

            try:
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                break

    def _toggle_auto_scroll(self) -> None:
        """切换自动滚动"""
        self.auto_scroll = not self.auto_scroll
        log_viewer = self.query_one("#log-viewer", Log)
        log_viewer.auto_scroll = self.auto_scroll

        toggle_btn = self.query_one("#toggle-scroll-btn", Button)
        toggle_btn.label = f"{get_global_i18n().t('common.auto_scroll')}: {'开' if self.auto_scroll else '关'}"

        if self.auto_scroll:
            self.app.notify(get_global_i18n().t('crawler.auto_scroll_enabled'))
            self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
            self.set_timer(0.05, lambda: log_viewer.scroll_end(animate=False))
        else:
            self.app.notify(get_global_i18n().t('crawler.auto_scroll_disabled'))

    def _clear_log_content(self) -> None:
        """清空日志视图显示（不影响日志源）"""
        log_viewer = self.query_one("#log-viewer", Log)
        log_viewer.clear()
        log_viewer.write(f"📝 {get_global_i18n().t('crawler.log_cleared_message')}")
        if self.memory_mode:
            # 把游标推到当前末尾，避免定时刷新把已清空的历史日志重新写回
            lines = get_recent_memory_logs(1000)
            self._memory_last_line = lines[-1] if lines else None

    def _refresh_log_content(self) -> None:
        """刷新日志内容：从日志源全量重新加载当前快照"""
        if self.memory_mode:
            self._load_memory_content()
        else:
            self.last_position = 0
            self._load_initial_log_content()
        self.app.notify(f"📋 {get_global_i18n().t('crawler.log_refreshed')}")

    async def action_close(self) -> None:
        """关闭弹窗"""
        try:
            await self._stop_file_watching()
            self.dismiss()
            self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
        except Exception as e:
            logger.error(f"关闭日志查看器失败: {e}")
            await self._force_close()

    async def action_force_close(self) -> None:
        """强制关闭弹窗"""
        await self._force_close()

    async def _force_close(self) -> None:
        """强制关闭弹窗的内部方法"""
        try:
            self.stop_watching = True
            if self.file_watcher_task and not self.file_watcher_task.done():
                self.file_watcher_task.cancel()
                try:
                    await asyncio.wait_for(self.file_watcher_task, timeout=0.1)
                except asyncio.TimeoutError:
                    pass
            self.dismiss()
            self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
        except Exception as e:
            logger.error(f"{get_global_i18n().t('crawler.force_close_failed')}: {e}")
            try:
                self.remove()
                self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
            except Exception:
                pass

    def action_sync_close(self) -> None:
        """同步关闭弹窗（备用方法）"""
        try:
            self.stop_watching = True
            self.dismiss()
            self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
        except Exception as e:
            logger.error(f"{get_global_i18n().t('crawler.sync_close_failed')}: {e}")
            try:
                self.remove()
                self.app.notify(f"📋 {get_global_i18n().t('crawler.log_viewer_closed')}")
            except Exception:
                pass

    def _ensure_scroll_to_bottom(self) -> None:
        """确保滚动到底部的内部方法"""
        try:
            log_viewer = self.query_one("#log-viewer", Log)
            log_viewer.scroll_end(animate=False)
        except Exception:
            pass

    def action_scroll_to_bottom(self) -> None:
        """手动滚动到底部"""
        try:
            log_viewer = self.query_one("#log-viewer", Log)
            log_viewer.scroll_end(animate=False)
            self.set_timer(0.02, lambda: log_viewer.scroll_end(animate=False))
            self.app.notify(get_global_i18n().t('crawler.scrolled_to_bottom'))
        except Exception as e:
            logger.error(f"{get_global_i18n().t('crawler.scroll_to_bottom_failed')}: {e}")
