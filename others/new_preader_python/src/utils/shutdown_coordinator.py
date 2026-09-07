"""
全局优雅退出协调器
==================

解决的问题
----------
在批量去重等后台任务运行期间按 Ctrl+C，会出现如下现象：

    KeyboardInterrupt
      File ".../asyncio/runners.py", line 74, in close
        loop.run_until_complete(loop.shutdown_default_executor(THREAD_JOIN_TIMEOUT))
      ...
    Exception ignored on threading shutdown:
      File ".../concurrent/futures/thread.py", line 31, in _python_exit
        t.join()

原因：
1. 主线程被 Ctrl+C 中断，但后台检测线程及其线程池仍在执行；
2. 解释器退出阶段会 join 这些工作线程（asyncio 默认执行器最长等待 300 秒），
   `concurrent.futures.thread._python_exit` 也会 join 所有池线程；
3. 用户只能反复按 Ctrl+C，最终打印出上面的堆栈。

本模块提供统一收口：
- 安装 SIGINT / SIGTERM 处理器；
- 首次中断：置全局退出标志 → 调用已注册的取消回调（去重检测器等）→
  请求 UI 优雅退出 → 摘除 daemon 工作线程（退出时不再 join）→
  启动看门狗线程；
- 超过宽限期（默认 3 秒）仍未退出：恢复终端后 `os._exit(130)` 强制退出；
- 再次按下 Ctrl+C：立即强制退出。

使用方式
--------
程序入口（main.py）安装一次：

    from src.utils.shutdown_coordinator import shutdown
    shutdown.install(app_exit_callback=lambda: app.call_from_thread(app.exit))
    ...
    app.run()
    shutdown.finish()

后台任务中周期性检查：

    from src.utils.shutdown_coordinator import is_shutdown_requested
    if is_shutdown_requested():
        return
"""

from __future__ import annotations

import importlib
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Ctrl+C 的常规退出码
DEFAULT_EXIT_CODE = 130
# 优雅退出的宽限时间（秒），超时后强制退出
DEFAULT_GRACE_PERIOD = 3.0

# 恢复终端的转义序列（退出备用屏幕、关闭鼠标跟踪、显示光标等）
_TERMINAL_RESTORE_SEQUENCE = (
    "\x1b[?1049l"                    # 退出 alternate screen
    "\x1b[?1003l\x1b[?1002l\x1b[?1000l"  # 关闭鼠标跟踪
    "\x1b[?2004l"                    # 关闭 bracketed paste
    "\x1b[0m"                        # 重置字符属性
    "\x1b[?25h"                      # 显示光标
)

# 默认需要通知取消的后台任务类（延迟导入，避免循环依赖）
_DEFAULT_CANCEL_TARGETS = (
    ("src.utils.book_duplicate_detector_v2", "SmartDuplicateDetectorV3"),
    ("src.utils.book_duplicate_detector_ultra", "UltraBookDuplicateDetector"),
    ("src.utils.book_duplicate_detector_optimized", "OptimizedBookDuplicateDetector"),
)


class DaemonThreadPoolExecutor(ThreadPoolExecutor):
    """工作线程全部为 daemon，且 `shutdown()` 永不阻塞调用线程。

    asyncio 在事件循环关闭时会调用 `shutdown(wait=True)`，若池中线程仍在
    运行会一直等待（Python 3.14 下最长 THREAD_JOIN_TIMEOUT=300 秒）。
    这里强制忽略 wait，保证退出流程不被拖住。
    """

    def submit(self, fn, *args, **kwargs):
        future = super().submit(fn, *args, **kwargs)
        self._mark_threads_daemon()
        return future

    def _mark_threads_daemon(self) -> None:
        for t in tuple(getattr(self, "_threads", ()) or ()):
            if not t.daemon:
                try:
                    t.daemon = True
                except (RuntimeError, ValueError):
                    # 线程已启动，无法再修改 daemon 属性
                    pass

    def shutdown(self, wait=True, *args, **kwargs):  # noqa: D102
        self._mark_threads_daemon()
        try:
            super().shutdown(wait=False, cancel_futures=True)
        except TypeError:  # Python < 3.9 不支持 cancel_futures
            super().shutdown(wait=False)


class ShutdownCoordinator:
    """进程级退出协调器（单例使用：模块底部的 `shutdown`）。"""

    def __init__(self, grace_period: float = DEFAULT_GRACE_PERIOD) -> None:
        self._grace_period = grace_period
        self._lock = threading.RLock()
        self._requested = False
        self._finished = threading.Event()
        self._watchdog: Optional[threading.Thread] = None
        self._cancel_callbacks: List[Callable[[], None]] = []
        self._exit_callback: Optional[Callable[[], None]] = None
        self._installed = False
        self._executor_installed = False

    # ------------------------------------------------------------------
    # 安装
    # ------------------------------------------------------------------
    def install(
        self,
        app_exit_callback: Optional[Callable[[], None]] = None,
        grace_period: Optional[float] = None,
    ) -> "ShutdownCoordinator":
        """安装信号处理器与默认取消回调（可重复调用，只有首次生效）。"""
        if app_exit_callback is not None:
            self._exit_callback = app_exit_callback
        if grace_period is not None:
            self._grace_period = grace_period

        if self._installed:
            return self

        self.register_cancel_callback(self._cancel_background_tasks)

        for sig_name in ("SIGINT", "SIGTERM"):
            sig = getattr(signal, sig_name, None)
            if sig is None:
                continue
            try:
                signal.signal(sig, self._handle_signal)
            except (ValueError, OSError, RuntimeError) as exc:
                # 非主线程等场景无法安装信号处理器，忽略即可
                logger.debug(f"注册 {sig_name} 处理器失败（可忽略）: {exc}")

        self._installed = True
        return self

    # ------------------------------------------------------------------
    # 注册接口
    # ------------------------------------------------------------------
    def register_cancel_callback(self, callback: Callable[[], None]) -> None:
        """注册退出时需要执行的取消逻辑（会被 try/except 包裹）。"""
        with self._lock:
            self._cancel_callbacks.append(callback)

    def set_app_exit_callback(self, callback: Optional[Callable[[], None]]) -> None:
        """设置优雅退出 UI 的回调，例如 `lambda: app.call_from_thread(app.exit)`。"""
        self._exit_callback = callback

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------
    def is_requested(self) -> bool:
        """是否已收到退出请求（后台任务应周期性检查并尽快返回）。"""
        return self._requested

    def finish(self) -> None:
        """正常退出完成，停止看门狗（不会触发强制退出）。"""
        self._finished.set()

    # ------------------------------------------------------------------
    # 触发退出
    # ------------------------------------------------------------------
    def request_shutdown(self, reason: str = "") -> None:
        """请求优雅退出（重复调用安全）。"""
        with self._lock:
            first = not self._requested
            self._requested = True

        if not first:
            return

        logger.info(f"收到退出请求（{reason or 'unknown'}），正在取消后台任务…")

        self.cancel_background_tasks()
        self._request_app_exit()
        self._start_watchdog()

    def cancel_background_tasks(self) -> None:
        """仅取消后台任务并摘除其工作线程（不触发退出、不启动看门狗）。

        适用于程序正常退出路径：让仍在运行的去重等任务尽快停止，
        并避免解释器在退出阶段 join 这些线程。
        """
        self._run_cancel_callbacks()
        self._detach_daemon_threads()

    def force_exit(self, code: int = DEFAULT_EXIT_CODE) -> None:
        """立即终止进程（不等待后台线程、不执行 atexit 钩子）。"""
        self._finished.set()
        self._restore_terminal()
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(code)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _handle_signal(self, signum, frame) -> None:  # noqa: ARG002
        try:
            name = signal.Signals(signum).name
        except Exception:
            name = str(signum)

        if self._requested:
            # 二次中断：不再等待，直接退出
            try:
                print(f"\n⚠️  再次收到 {name}，强制退出…", file=sys.stderr, flush=True)
            except Exception:
                pass
            self.force_exit()
            return

        try:
            print(
                f"\n收到 {name}，正在停止后台任务并退出（再次按 Ctrl+C 强制退出）…",
                file=sys.stderr,
                flush=True,
            )
        except Exception:
            pass
        self.request_shutdown(reason=name)

    def _run_cancel_callbacks(self) -> None:
        with self._lock:
            callbacks = list(self._cancel_callbacks)
        for callback in callbacks:
            try:
                callback()
            except Exception as exc:
                logger.debug(f"退出取消回调执行失败（可忽略）: {exc}")

    def _request_app_exit(self) -> None:
        if self._exit_callback is None:
            return
        try:
            self._exit_callback()
        except Exception as exc:
            logger.debug(f"请求 UI 退出失败（可忽略）: {exc}")
            self.force_exit()

    def _start_watchdog(self) -> None:
        with self._lock:
            if self._watchdog is not None and self._watchdog.is_alive():
                return
            self._watchdog = threading.Thread(
                target=self._watchdog_loop,
                name="shutdown-watchdog",
                daemon=True,
            )
            self._watchdog.start()

    def _watchdog_loop(self) -> None:
        deadline = time.monotonic() + self._grace_period
        while not self._finished.wait(0.1):
            if time.monotonic() >= deadline:
                logger.warning(
                    f"退出超时（{self._grace_period}s）：后台任务未及时结束，强制终止进程"
                )
                self.force_exit()
                return

    @staticmethod
    def _detach_daemon_threads() -> None:
        """把 daemon 工作线程从 concurrent.futures 的全局集合中摘除。

        解释器退出时 `concurrent.futures.thread._python_exit` 会 join 所有在册
        的工作线程（daemon 线程同样会被 join），线程不结束就会卡住退出流程。
        摘除后进程即可立即退出，daemon 线程由操作系统回收。
        """
        try:
            import concurrent.futures.thread as _cf_thread

            threads_queues = getattr(_cf_thread, "_threads_queues", None)
            threads = getattr(_cf_thread, "_threads", None)
            detached = 0
            for t in tuple(threads or ()):
                if not getattr(t, "daemon", False):
                    continue
                if threads_queues is not None:
                    try:
                        threads_queues.pop(t, None)
                    except Exception:
                        pass
                if threads is not None:
                    try:
                        threads.discard(t)
                    except Exception:
                        pass
                detached += 1
            if detached:
                logger.debug(f"已摘除 {detached} 个后台工作线程，退出时不再等待它们")
        except Exception as exc:
            logger.debug(f"摘除后台线程失败（可忽略）: {exc}")

    @staticmethod
    def _restore_terminal() -> None:
        """强制退出前尽量恢复终端，避免停留在备用屏幕/隐藏光标状态。"""
        try:
            stream = sys.stderr
            if stream is None or not stream.isatty():
                return
            stream.write(_TERMINAL_RESTORE_SEQUENCE)
            stream.flush()
        except Exception:
            pass

    @staticmethod
    def _cancel_background_tasks() -> None:
        """通知已知的后台任务（去重检测器等）立即取消。"""
        for module_path, class_name in _DEFAULT_CANCEL_TARGETS:
            try:
                module = importlib.import_module(module_path)
                target = getattr(module, class_name, None)
                if target is not None and hasattr(target, "request_cancel"):
                    target.request_cancel()
            except Exception as exc:
                logger.debug(f"取消 {class_name} 失败（可忽略）: {exc}")

    # ------------------------------------------------------------------
    # asyncio 默认执行器
    # ------------------------------------------------------------------
    def install_daemon_default_executor(self) -> bool:
        """把当前事件循环的 asyncio 默认执行器替换为 daemon 版本。

        必须在事件循环内调用（例如 App 的 `on_mount`）。
        """
        if self._executor_installed:
            return True
        try:
            import asyncio

            loop = asyncio.get_running_loop()
        except Exception as exc:
            logger.debug(f"获取事件循环失败，跳过替换默认执行器: {exc}")
            return False

        try:
            old_executor = getattr(loop, "_default_executor", None)
            executor = DaemonThreadPoolExecutor(
                max_workers=min(32, (os.cpu_count() or 1) + 4),
                thread_name_prefix="asyncio-daemon",
            )
            loop.set_default_executor(executor)
            if old_executor is not None:
                try:
                    old_executor.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
            self._executor_installed = True
            return True
        except Exception as exc:
            logger.debug(f"替换 asyncio 默认执行器失败（可忽略）: {exc}")
            return False


# ----------------------------------------------------------------------
# 模块级单例与便捷函数
# ----------------------------------------------------------------------

shutdown = ShutdownCoordinator()


def install(
    app_exit_callback: Optional[Callable[[], None]] = None,
    grace_period: Optional[float] = None,
) -> ShutdownCoordinator:
    return shutdown.install(app_exit_callback=app_exit_callback, grace_period=grace_period)


def register_cancel_callback(callback: Callable[[], None]) -> None:
    shutdown.register_cancel_callback(callback)


def is_shutdown_requested() -> bool:
    return shutdown.is_requested()


def request_shutdown(reason: str = "") -> None:
    shutdown.request_shutdown(reason=reason)


def force_exit(code: int = DEFAULT_EXIT_CODE) -> None:
    shutdown.force_exit(code)


def finish() -> None:
    shutdown.finish()


def cancel_background_tasks() -> None:
    shutdown.cancel_background_tasks()


def install_daemon_default_executor() -> bool:
    return shutdown.install_daemon_default_executor()
