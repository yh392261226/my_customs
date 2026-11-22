"""
静置自动一键爬取管理器
======================

只统计 Python 端（Textual 终端界面）的人为操作：
* 按键、鼠标点击/滚动、粘贴等终端输入会重置静置计时；
* 浏览器端访问/操作不会调用本模块，因此不会重置计时；
* 后台爬取、网络回调等非人为事件也不会重置计时。

当开关开启且系统持续静置超过本次随机间隔时，在 UI 线程触发一次
``OneClickCrawlManager.start()``，随后重新计时。每次新的静置周期都会在
配置的间隔区间内重新随机取值，降低被书籍网站识别为固定频率爬虫的概率。

多个 NewReader 实例之间通过跨进程文件锁抢占自动爬取权：同一时刻只允许
一个实例持有锁并触发一键爬取，其它静置实例会等待下一轮随机间隔。
"""

from __future__ import annotations

import os
import random
import threading
import time
from typing import Optional

from src.config.default_config import DEFAULT_CONFIG
from src.utils.logger import get_logger
from src.utils.process_lock import NonBlockingFileLock, is_locked_by_other

logger = get_logger(__name__)

_DEFAULTS = DEFAULT_CONFIG.get("idle", {})
# 同一进程内可能同时存在多个 App 实例（如多个 Web 会话），
# 每个实例的静置计时必须独立，不能被其它实例的操作重置。
_ACTIVE_MANAGERS: set["IdleAutoCrawlManager"] = set()
_ACTIVE_MANAGERS_LOCK = threading.Lock()


class IdleAutoCrawlManager:
    """绑定在 App 实例上的静置检测器（每个 App 实例一份）。"""

    # 静置间隔以分钟为量级，3 秒的轮询精度足够；原先每秒在主线程做配置读取、
    # 文件锁探测与运行状态查询，书库/配置变大后会形成持续的背景卡顿。
    CHECK_INTERVAL = 3.0

    def __init__(self, app) -> None:
        self.app = app
        self._lock = threading.Lock()
        self._last_activity = time.monotonic()
        self._auto_crawl_active = False
        self._next_interval: Optional[int] = None
        self._crawl_lock: Optional[NonBlockingFileLock] = None
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
            logger.error(f"启动静置自动爬取检测失败: {e}")

    def stop(self) -> None:
        """停止静置检测（App 退出时调用）。"""
        self._started = False
        self._release_crawl_lock()
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
            # 新的静置周期使用新的随机间隔
            self._next_interval = None

    # ------------------------------------------------------------------
    # 定时检测
    # ------------------------------------------------------------------
    def _get_config(self):
        config_manager = getattr(self.app, "config_manager", None)
        if config_manager is None:
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager.get_instance()
        return config_manager.get_config() or {}

    def _read_config(self):
        # get_config 可能涉及文件 IO 且在 UI 主线程执行，缓存 10 秒；
        # 设置变更最多延迟一个缓存周期生效，对静置触发场景无感。
        now = time.monotonic()
        if self._config_cache is not None and now - self._config_cached_at < 10.0:
            return self._config_cache
        cfg = self._get_config()
        idle_cfg = cfg.get("idle", {}) or {}
        enabled = bool(idle_cfg.get(
            "auto_one_click_crawl_enabled",
            _DEFAULTS.get("auto_one_click_crawl_enabled", False),
        ))
        def read_interval(key: str, default_key: str) -> int:
            try:
                return int(idle_cfg.get(key, _DEFAULTS.get(default_key, 1800)))
            except (TypeError, ValueError):
                return int(_DEFAULTS.get(default_key, 1800))

        interval_min = read_interval(
            "auto_one_click_crawl_interval_min", "auto_one_click_crawl_interval_min"
        )
        interval_max = read_interval(
            "auto_one_click_crawl_interval_max", "auto_one_click_crawl_interval_max"
        )
        if interval_min > interval_max:
            interval_min, interval_max = interval_max, interval_min
        interval_min = max(1, interval_min)
        interval_max = max(interval_min, interval_max)
        self._config_cache = (enabled, interval_min, interval_max)
        self._config_cached_at = now
        return self._config_cache

    def _is_one_click_running(self) -> bool:
        try:
            from src.core.one_click_crawl_manager import get_one_click_crawl_manager
            return bool(get_one_click_crawl_manager(self.app).is_running)
        except Exception as e:
            logger.debug(f"查询一键爬取运行状态失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 跨实例抢占锁
    # ------------------------------------------------------------------
    def _get_crawl_lock(self) -> NonBlockingFileLock:
        cfg = self._get_config()
        config_dir = (cfg.get("paths", {}) or {}).get(
            "config_dir",
            DEFAULT_CONFIG.get("paths", {}).get("config_dir", "~/.config/new_preader"),
        )
        path = os.path.abspath(os.path.expanduser(
            os.path.join(str(config_dir), "idle_auto_crawl.lock")
        ))
        if self._crawl_lock is None or self._crawl_lock.path != path:
            self._release_crawl_lock()
            self._crawl_lock = NonBlockingFileLock(path)
        return self._crawl_lock

    def _release_crawl_lock(self) -> None:
        lock, self._crawl_lock = self._crawl_lock, None
        if lock is not None:
            lock.release()

    def _is_crawl_lock_held(self) -> bool:
        return self._crawl_lock is not None and self._crawl_lock.is_held

    def _acquire_crawl_lock(self) -> bool:
        lock = self._get_crawl_lock()
        try:
            return lock.acquire()
        except Exception as e:
            logger.error(f"抢占静置自动爬取锁失败: {e}")
            self._release_crawl_lock()
            return False

    def _is_crawl_lock_held_by_other(self) -> bool:
        lock = self._get_crawl_lock()
        try:
            return is_locked_by_other(lock.path)
        except Exception as e:
            logger.debug(f"检测静置自动爬取锁失败: {e}")
            return False

    def _tick(self) -> None:
        if not self._started:
            return

        enabled, interval_min, interval_max = self._read_config()
        now = time.monotonic()

        # 开关关闭时持续把静置起点推进到当前时间，
        # 这样用户稍后开启开关时不会立刻触发一轮历史静置。
        if not enabled:
            self._release_crawl_lock()
            with self._lock:
                self._last_activity = now
                self._auto_crawl_active = False
                self._next_interval = None
            return

        # 本实例持有锁：爬取期间持续续期静置起点，爬取结束后释放锁并重新计时。
        if self._is_crawl_lock_held():
            if self._is_one_click_running():
                with self._lock:
                    self._auto_crawl_active = True
                    self._last_activity = now
                    self._next_interval = None
                return
            logger.info("静置自动一键爬取结束，释放跨实例锁")
            self._release_crawl_lock()
            with self._lock:
                self._auto_crawl_active = False
                self._last_activity = now
                self._next_interval = None
            return

        # 其它实例持有锁时，本实例不触发，并等待一个全新的静置周期。
        if self._is_crawl_lock_held_by_other():
            with self._lock:
                self._last_activity = now
                self._auto_crawl_active = False
                self._next_interval = None
            return

        # 本实例正在手动/其它来源的一键爬取，视为系统活动。
        if self._is_one_click_running():
            with self._lock:
                self._auto_crawl_active = True
                self._last_activity = now
                self._next_interval = None
            return

        with self._lock:
            if self._auto_crawl_active:
                self._auto_crawl_active = False
                self._last_activity = now
                self._next_interval = None
                return
            if (
                self._next_interval is None
                or not (interval_min <= self._next_interval <= interval_max)
            ):
                self._next_interval = random.randint(interval_min, interval_max)
            interval = self._next_interval
            elapsed = now - self._last_activity

        if elapsed < interval:
            return

        # 抢占跨实例锁：抢占失败说明另一个实例刚拿到自动爬取权。
        if not self._acquire_crawl_lock():
            with self._lock:
                self._last_activity = now
                self._next_interval = None
            return

        logger.info(
            f"系统静置已超过本次随机间隔 {interval} 秒"
            f"（区间 {interval_min}-{interval_max} 秒），自动执行一键爬取"
        )
        with self._lock:
            self._last_activity = now
            self._auto_crawl_active = True
            self._next_interval = None
        self.app.call_later(self._run_auto_crawl)

    def _run_auto_crawl(self) -> None:
        """在 UI 线程启动一键爬取。"""
        try:
            from src.core.one_click_crawl_manager import get_one_click_crawl_manager
            manager = get_one_click_crawl_manager(self.app)
            started = manager.start()
            if not started and not manager.is_running:
                # 未真正启动（如无站点/无权限）时立即让出跨实例爬取权
                self._release_crawl_lock()
        except Exception as e:
            logger.error(f"静置自动一键爬取执行失败: {e}")
            self._release_crawl_lock()


def get_idle_auto_crawl_manager(app) -> IdleAutoCrawlManager:
    """获取（并惰性创建）绑定在 App 上的静置自动爬取管理器。"""
    manager = getattr(app, "_idle_auto_crawl_manager", None)
    if manager is None or manager.app is not app:
        manager = IdleAutoCrawlManager(app)
        setattr(app, "_idle_auto_crawl_manager", manager)
    return manager


def notify_user_activity(source: str = "tui") -> None:
    """广播一次 Python 端人为操作给所有已启动的 App 实例。

    App 自身的终端事件会走 :meth:`IdleAutoCrawlManager.notify_activity`
    精确重置当前实例；此函数供需要广播的场景使用，浏览器端不会调用。
    """
    with _ACTIVE_MANAGERS_LOCK:
        managers = tuple(_ACTIVE_MANAGERS)
    for manager in managers:
        manager.notify_activity(source)


def stop_idle_auto_crawl_manager(app=None) -> None:
    """停止静置检测器；显式传入 app 时只停止该 App 上的实例。"""
    if app is not None:
        manager = getattr(app, "_idle_auto_crawl_manager", None)
        if manager is not None:
            manager.stop()
        return
    with _ACTIVE_MANAGERS_LOCK:
        managers = tuple(_ACTIVE_MANAGERS)
    for manager in managers:
        manager.stop()
