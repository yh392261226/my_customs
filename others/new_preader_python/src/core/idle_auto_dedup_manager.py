"""
静置自动批量去重管理器
======================

系统静置超过配置的分钟数后，在后台线程执行一次完整的批量去重检测，
并把结果暂存到 dedup_staging，供之后人工打开「继续上次去重」处理。

设计要点：
* 只统计 Python 端（Textual 终端界面）的人为操作，浏览器端不算；
* 使用独立的静置计时，与静置自动爬取完全解耦：自动爬取、网络回调、
  后台任务都不会重置这里的计时，因此自动爬取不会被当成「非静置」；
* 全程不弹窗、不推送通知，只在日志中记录进度与结果；
* 使用独立的检测器状态（取消标志 / 执行器 / 缓存），执行期间不会被用户的
  取消、手动去重等其它操作打断，也不会清掉或改动其它任务的状态；
  只有退出系统的信号可以中止它。
* 多个 App 实例通过独立的文件锁抢占，避免重复执行耗时的全量检测。
"""
from __future__ import annotations

import os
import threading
import time
from typing import Optional

from src.config.default_config import DEFAULT_CONFIG
from src.utils.logger import get_logger
from src.utils.process_lock import NonBlockingFileLock, is_locked_by_other

logger = get_logger(__name__)

_DEFAULTS = DEFAULT_CONFIG.get("idle", {})
# 同一进程内可能同时存在多个 App 实例（如多个 Web 会话），每个实例的静置计时独立。
_ACTIVE_MANAGERS: set["IdleAutoDedupManager"] = set()
_ACTIVE_MANAGERS_LOCK = threading.Lock()


class IdleAutoDedupManager:
    """绑定在 App 实例上的静置自动去重检测器。"""

    CHECK_INTERVAL = 3.0

    def __init__(self, app) -> None:
        self.app = app
        self._lock = threading.Lock()
        self._last_activity = time.monotonic()
        self._dedup_active = False
        self._dedup_lock: Optional[NonBlockingFileLock] = None
        self._timer = None
        self._started = False
        self._config_cache = None
        self._config_cached_at = 0.0

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self) -> None:
        """启动静置检测（应从 App 主线程调用）。"""
        with _ACTIVE_MANAGERS_LOCK:
            _ACTIVE_MANAGERS.add(self)

        if self._started:
            return

        self.notify_activity("start")
        try:
            self._timer = self.app.set_interval(self.CHECK_INTERVAL, self._tick)
            self._started = True
        except Exception as e:
            logger.error(f"启动静置自动去重检测失败: {e}")

    def stop(self) -> None:
        """停止静置检测（App 退出时调用）。"""
        self._started = False
        self._release_dedup_lock()
        timer, self._timer = self._timer, None
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
        with _ACTIVE_MANAGERS_LOCK:
            _ACTIVE_MANAGERS.discard(self)

    # ------------------------------------------------------------------
    # 外部活动通知
    # ------------------------------------------------------------------
    def notify_activity(self, source: str = "tui") -> None:
        """记录一次 Python 端人为操作，重新计算静置时间。"""
        with self._lock:
            self._last_activity = time.monotonic()

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------
    def _get_config(self):
        config_manager = getattr(self.app, "config_manager", None)
        if config_manager is None:
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager.get_instance()
        return config_manager.get_config() or {}

    def _read_config(self):
        now = time.monotonic()
        if self._config_cache is not None and now - self._config_cached_at < 10.0:
            return self._config_cache
        cfg = self._get_config()
        idle_cfg = cfg.get("idle", {}) or {}
        enabled = bool(idle_cfg.get(
            "auto_dedup_enabled",
            _DEFAULTS.get("auto_dedup_enabled", False),
        ))
        try:
            minutes = int(idle_cfg.get(
                "auto_dedup_interval_minutes",
                _DEFAULTS.get("auto_dedup_interval_minutes", 30),
            ))
        except (TypeError, ValueError):
            minutes = int(_DEFAULTS.get("auto_dedup_interval_minutes", 30))
        minutes = max(1, minutes)
        self._config_cache = (enabled, minutes)
        self._config_cached_at = now
        return self._config_cache

    # ------------------------------------------------------------------
    # 跨实例抢占锁（与静置爬取的锁相互独立）
    # ------------------------------------------------------------------
    def _get_dedup_lock(self) -> NonBlockingFileLock:
        cfg = self._get_config()
        config_dir = (cfg.get("paths", {}) or {}).get(
            "config_dir",
            DEFAULT_CONFIG.get("paths", {}).get("config_dir", "~/.config/new_preader"),
        )
        path = os.path.abspath(os.path.expanduser(
            os.path.join(str(config_dir), "idle_auto_dedup.lock")
        ))
        if self._dedup_lock is None or self._dedup_lock.path != path:
            self._release_dedup_lock()
            self._dedup_lock = NonBlockingFileLock(path)
        return self._dedup_lock

    def _release_dedup_lock(self) -> None:
        lock, self._dedup_lock = self._dedup_lock, None
        if lock is not None:
            lock.release()

    def _is_dedup_lock_held(self) -> bool:
        return self._dedup_lock is not None and self._dedup_lock.is_held

    def _acquire_dedup_lock(self) -> bool:
        lock = self._get_dedup_lock()
        try:
            return lock.acquire()
        except Exception as e:
            logger.error(f"抢占静置自动去重锁失败: {e}")
            self._release_dedup_lock()
            return False

    def _is_dedup_lock_held_by_other(self) -> bool:
        lock = self._get_dedup_lock()
        try:
            return is_locked_by_other(lock.path)
        except Exception as e:
            logger.debug(f"检测静置自动去重锁失败: {e}")
            return False

    def _is_active(self) -> bool:
        with self._lock:
            return self._dedup_active

    def _finish(self) -> None:
        """一次自动去重结束：释放锁并从完成时刻重新计时。"""
        logger.info("静置自动批量去重结束，释放跨实例锁")
        with self._lock:
            self._dedup_active = False
            self._last_activity = time.monotonic()
        self._release_dedup_lock()

    # ------------------------------------------------------------------
    # 定时检测
    # ------------------------------------------------------------------
    def _tick(self) -> None:
        if not self._started:
            return

        enabled, minutes = self._read_config()
        now = time.monotonic()

        # 开关关闭时持续推进静置起点，避免用户稍后开启时立刻触发历史静置。
        if not enabled:
            self._release_dedup_lock()
            with self._lock:
                self._last_activity = now
                self._dedup_active = False
            return

        # 本实例持有锁：检测线程仍在运行时不续期静置起点（后台任务不是人为活动）。
        if self._is_dedup_lock_held():
            if self._is_active():
                return
            self._finish()
            return

        # 其它实例正在执行自动去重，本实例等待下一个完整静置周期。
        if self._is_dedup_lock_held_by_other():
            with self._lock:
                self._last_activity = now
            return

        with self._lock:
            elapsed = now - self._last_activity

        if elapsed < minutes * 60:
            return

        if not self._acquire_dedup_lock():
            with self._lock:
                self._last_activity = now
            return

        logger.info(f"系统静置已超过 {minutes} 分钟，自动执行批量去重（后台、无弹窗）")
        with self._lock:
            self._last_activity = now
            self._dedup_active = True
        self.app.call_later(self._run_auto_dedup)

    # ------------------------------------------------------------------
    # 执行：后台线程检测 + 静默暂存
    # ------------------------------------------------------------------
    def _run_auto_dedup(self) -> None:
        """在 UI 线程取书籍快照，随后把重活交给后台线程。"""
        try:
            books = list(self.app.bookshelf.get_all_books())
        except Exception as e:
            logger.error(f"静置自动去重读取书库失败: {e}")
            self._finish()
            return

        if len(books) < 2:
            logger.info("书籍不足 2 本，跳过静置自动去重")
            self._finish()
            return

        try:
            from src.utils import dedup_staging

            # 已有人工处理进度的暂存绝不覆盖，否则会丢失人工选择。
            existing = dedup_staging.load_staging()
            if existing:
                state = existing.get("state", {}) or {}
                if (state.get("selected_books") or state.get("skipped_groups")
                        or state.get("viewed_groups")):
                    logger.info("已有人工处理进度的去重暂存，跳过本次静置自动去重")
                    self._finish()
                    return
            existing_saved_at = existing.get("saved_at") if existing else None

            def worker() -> None:
                try:
                    from src.utils.book_duplicate_detector_v2 import SmartDuplicateDetectorV3
                    from src.utils import dedup_staging as staging

                    # 独立的检测器状态：手动去重的取消、缓存清理、执行器关闭
                    # 都不会打断本任务，本任务也不会改动其它操作使用的状态。
                    class _IdleDedupDetector(SmartDuplicateDetectorV3):
                        _cancelled = False
                        _active_executors = []
                        _executors_lock = threading.Lock()
                        _hash_cache = {}
                        _content_cache = {}
                        _fingerprint_cache = {}
                        _cache_lock = threading.Lock()
                        # 后台执行期间限制并发，避免拖慢用户正在进行的操作
                        MAX_WORKERS = 2

                    def progress_callback(current, total, message="") -> None:
                        # 用户回到终端操作时主动让出 CPU：只降速，不取消任务，
                        # 既保证自动去重不被打断，也避免抢占前台操作的资源。
                        try:
                            with self._lock:
                                last = self._last_activity
                            if time.monotonic() - last < 3.0:
                                time.sleep(0.02)
                        except Exception:
                            pass

                    started = time.monotonic()
                    detector = _IdleDedupDetector()
                    groups = detector._find_duplicates_impl(
                        books, progress_callback=progress_callback
                    ) or []
                    snapshot = staging.build_snapshot(
                        groups=groups,
                        selected_books=set(),
                        recommended_selected_books=set(),
                        skipped_groups=set(),
                        viewed_groups=set(),
                        current_group_index=0,
                        current_batch=0,
                        total_batches=1,
                        processing_remaining=False,
                        elapsed_seconds=time.monotonic() - started,
                    )
                    # 标记为自动任务生成，便于后续人工处理区分来源。
                    snapshot["source"] = "idle_auto_dedup"

                    # 执行期间若暂存被用户改动（清除/另存），不覆盖用户的结果。
                    current = staging.load_staging()
                    current_saved_at = current.get("saved_at") if current else None
                    if current_saved_at != existing_saved_at:
                        logger.info("暂存文件在执行期间被其他操作修改，跳过自动写入")
                        return

                    if staging.save_staging(snapshot):
                        logger.info(f"静置自动去重结果已暂存: {len(groups)} 组")
                    else:
                        logger.error("静置自动去重结果暂存失败")
                except Exception as e:
                    logger.error(f"静置自动去重执行失败: {e}", exc_info=True)
                finally:
                    self._finish()

            threading.Thread(
                target=worker, daemon=True, name="idle-auto-dedup"
            ).start()
        except Exception as e:
            logger.error(f"启动静置自动去重任务失败: {e}")
            self._finish()


def get_idle_auto_dedup_manager(app) -> IdleAutoDedupManager:
    """获取（并惰性创建）绑定在 App 上的静置自动去重管理器。"""
    manager = getattr(app, "_idle_auto_dedup_manager", None)
    if manager is None or manager.app is not app:
        manager = IdleAutoDedupManager(app)
        setattr(app, "_idle_auto_dedup_manager", manager)
    return manager


def is_idle_auto_dedup_running(app=None) -> bool:
    """查询是否有静置自动批量去重正在执行（含已触发、尚未启动线程的任务）。

    供手动批量去重入口判断是否应该跳过，避免重复发起耗时的全量检测。
    """
    if app is not None:
        manager = getattr(app, "_idle_auto_dedup_manager", None)
        return bool(manager is not None and manager._is_active())
    with _ACTIVE_MANAGERS_LOCK:
        managers = tuple(_ACTIVE_MANAGERS)
    return any(manager._is_active() for manager in managers)


def stop_idle_auto_dedup_manager(app=None) -> None:
    """停止静置自动去重检测器；显式传入 app 时只停止该 App 上的实例。"""
    if app is not None:
        manager = getattr(app, "_idle_auto_dedup_manager", None)
        if manager is not None:
            manager.stop()
        return
    with _ACTIVE_MANAGERS_LOCK:
        managers = tuple(_ACTIVE_MANAGERS)
    for manager in managers:
        manager.stop()
