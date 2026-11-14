"""
一键爬取管理器
==============

App 级后台服务：一次点击，为所有开启「一键爬取」的书籍网站并发执行
爬取管理页面的「自动爬取书籍」流程：

    抓取列表页 -> 按规则过滤 -> 提取书籍ID -> 增量去重 -> 启动异步爬取任务

设计要点
--------
* 管理器挂在 App 实例上，不持有任何 Screen 引用，因此返回上一层、切换页面、
  打开弹窗等「非退出系统」的操作都不会中断或影响后台任务；
* 每个站点一个 daemon 线程做网络抓取，抓取完成后切回主线程为该站点调用
  ``CrawlerManager.start_crawl_task``（内部 ``asyncio.create_task``），
  多个站点真正并发执行；
* 所有 UI 反馈只走 ``App.notify``（App 级通知），不触碰具体页面控件；
* 爬取任务标记为 ``CRAWL_SOURCE_ONE_CLICK``，其状态/成功通知只发给专用回调，
  不会广播到爬取管理页、合并弹窗等页面的回调，避免串改「正在爬取」状态、
  输入框 ID 或表格数据。
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from src.core.database_manager import DatabaseManager
from src.locales.i18n_manager import get_global_i18n
from src.utils.auto_crawl import AutoCrawlError, collect_book_urls
from src.utils.logger import get_logger
from src.utils.novel_id_extractor import extract_novel_ids

logger = get_logger(__name__)

ONE_CLICK_CRAWL_FIELD = "one_click_crawl_enabled"


def _is_enabled(value: Any) -> bool:
    """兼容 SQLite 的 0/1、bool 与字符串值。"""
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


class OneClickCrawlManager:
    """App 级一键爬取调度器（每个 App 实例一份）。"""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.db = DatabaseManager()
        self._lock = threading.Lock()
        self._running = False
        self._run_seq = 0
        self._pending = 0
        # task_id -> (轮次, 站点名称)
        self._task_sites: Dict[str, Tuple[int, str]] = {}
        self._callbacks_registered = False
        self._register_callbacks()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def start(self) -> bool:
        """启动一轮一键爬取（必须从 UI 主线程调用）。

        Returns:
            bool: 是否成功启动
        """
        if not getattr(self.app, "has_permission", lambda _key: True)("crawler.run"):
            self._notify("one_click_crawl.no_permission", severity="error")
            return False

        with self._lock:
            already_running = self._running
        if already_running:
            self._notify("one_click_crawl.already_running", severity="warning")
            return False

        try:
            sites = [
                dict(site) for site in self.db.get_novel_sites()
                if site.get("id") and _is_enabled(site.get(ONE_CLICK_CRAWL_FIELD))
            ]
        except Exception as e:
            logger.error(f"读取一键爬取网站失败: {e}")
            self._notify("one_click_crawl.load_failed", severity="error", error=str(e))
            return False

        if not sites:
            self._notify("one_click_crawl.no_sites", severity="warning")
            return False

        with self._lock:
            if self._running:
                self._notify("one_click_crawl.already_running", severity="warning")
                return False
            self._running = True
            self._run_seq += 1
            self._pending = len(sites)
            seq = self._run_seq

        logger.info(f"一键爬取启动: {len(sites)} 个网站")
        self._notify("one_click_crawl.started", count=len(sites))

        for index, site in enumerate(sites):
            threading.Thread(
                target=self._site_worker,
                args=(seq, site),
                daemon=True,
                name=f"one-click-crawl-site-{site.get('id') or index}",
            ).start()
        return True

    # ------------------------------------------------------------------
    # 站点抓取线程
    # ------------------------------------------------------------------
    def _site_worker(self, seq: int, site: Dict[str, Any]) -> None:
        """后台线程：复刻爬取管理页「自动爬取书籍」的取书流程。"""
        name = str(site.get("name") or site.get("id") or "?")
        site_id = int(site.get("id") or 0)
        handed_off = False

        try:
            if not (site.get("auto_crawl_url") or "").strip():
                self._notify("one_click_crawl.site_no_url", name=name, severity="warning")
                return

            proxy_config = self._build_proxy_config(site)
            urls = collect_book_urls(site, proxy_config)
            book_ids = extract_novel_ids(urls, site)
            book_ids = self._filter_new_ids(site_id, book_ids)

            if not book_ids:
                self._notify("one_click_crawl.site_no_new_books", name=name)
                return

            # start_crawl_task 必须在 App 事件循环所在线程调用（内部 asyncio.create_task）
            handed_off = self._schedule(
                self._launch_crawl_task, seq, site_id, name, book_ids, proxy_config
            )
            if not handed_off:
                self._notify(
                    "one_click_crawl.site_failed", name=name,
                    error="无法调度到主线程", severity="error",
                )
        except AutoCrawlError as e:
            logger.warning(f"一键爬取 [{name}] 自动爬取失败: {e}")
            self._notify("one_click_crawl.site_failed", name=name, error=str(e), severity="warning")
        except Exception as e:
            logger.error(f"一键爬取 [{name}] 异常: {e}")
            self._notify("one_click_crawl.site_failed", name=name, error=str(e), severity="error")
        finally:
            if not handed_off:
                self._site_finished(seq)

    def _build_proxy_config(self, site: Dict[str, Any]) -> Dict[str, Any]:
        """构造该站点的代理配置（与爬取管理页的代理检查逻辑一致）。"""
        if not _is_enabled(site.get("proxy_enabled")):
            return {"enabled": False, "proxy_url": ""}
        try:
            proxy = self.db.get_enabled_proxy()
        except Exception as e:
            logger.error(f"读取代理设置失败: {e}")
            proxy = None
        if not proxy:
            logger.warning("站点已启用代理但没有可用代理设置，本次不使用代理")
            return {"enabled": False, "proxy_url": ""}

        proxy_url = str(proxy.get("proxy_url") or "").strip()
        if not proxy_url:
            proxy_type = str(proxy.get("type") or "http").strip().lower()
            host = str(proxy.get("host") or "").strip()
            port = str(proxy.get("port") or "").strip()
            username = str(proxy.get("username") or "").strip()
            password = str(proxy.get("password") or "").strip()
            if not host or not port:
                logger.warning("代理配置缺少 host/port，本次不使用代理")
                return {"enabled": False, "proxy_url": ""}
            auth = f"{username}:{password}@" if username and password else ""
            proxy_url = f"{proxy_type}://{auth}{host}:{port}"
        return {"enabled": True, "proxy_url": proxy_url, "name": proxy.get("name", "")}

    def _filter_new_ids(self, site_id: int, book_ids: List[str]) -> List[str]:
        """剔除已爬取过的短篇书籍；连载书籍保留以便增量更新。"""
        if not book_ids:
            return []
        try:
            crawled = self.db.filter_crawled_novel_ids(site_id, book_ids) or []
            serial_ids = [
                nid for nid in crawled
                if (self.db.get_last_successful_crawl(site_id, nid) or {}).get("serial_mode")
            ]
            skip = set(crawled) - set(serial_ids)
            return [nid for nid in book_ids if nid not in skip]
        except Exception as e:
            logger.error(f"查询已爬取书籍ID失败，改为全量处理: {e}")
            return book_ids

    # ------------------------------------------------------------------
    # 主线程：启动异步爬取任务 / 收尾
    # ------------------------------------------------------------------
    def _launch_crawl_task(
        self,
        seq: int,
        site_id: int,
        name: str,
        book_ids: List[str],
        proxy_config: Dict[str, Any],
    ) -> None:
        from src.core.crawler_manager import CRAWL_SOURCE_ONE_CLICK, CrawlerManager

        manager = CrawlerManager()
        self._register_callbacks(manager)
        try:
            task_id = manager.start_crawl_task(
                site_id, book_ids, proxy_config, source=CRAWL_SOURCE_ONE_CLICK
            )
        except Exception as e:
            logger.error(f"一键爬取 [{name}] 启动爬取任务失败: {e}")
            self._notify("one_click_crawl.site_failed", name=name, error=str(e), severity="error")
            self._site_finished(seq)
            return

        with self._lock:
            self._task_sites[task_id] = (seq, name)
        logger.info(f"一键爬取 [{name}] 已启动异步任务: {len(book_ids)} 本")
        self._notify("one_click_crawl.site_started", name=name, count=len(book_ids))

    def _on_task_status(self, task_id: str, task: Any) -> None:
        """一键爬取任务状态回调（仅接收 one_click 来源的任务）。"""
        from src.core.crawler_manager import CrawlStatus

        if task.status not in (CrawlStatus.COMPLETED, CrawlStatus.FAILED, CrawlStatus.STOPPED):
            return
        with self._lock:
            info = self._task_sites.pop(task_id, None)
        if not info:
            return
        seq, name = info
        self._notify(
            "one_click_crawl.site_done",
            name=name,
            success=task.success_count,
            failed=task.failed_count,
            severity="information" if task.status == CrawlStatus.COMPLETED else "warning",
        )
        self._site_finished(seq)

    def _site_finished(self, seq: int) -> None:
        finished = False
        with self._lock:
            if seq != self._run_seq:
                return
            self._pending = max(0, self._pending - 1)
            if self._pending == 0:
                self._running = False
                finished = True
        if finished:
            logger.info("一键爬取全部完成")
            self._notify("one_click_crawl.finished")

    # ------------------------------------------------------------------
    # 基础设施
    # ------------------------------------------------------------------
    def _register_callbacks(self, manager: Optional[Any] = None) -> None:
        if self._callbacks_registered:
            return
        try:
            if manager is None:
                from src.core.crawler_manager import CrawlerManager
                manager = CrawlerManager()
            manager.register_one_click_status_callback(self._on_task_status)
            self._callbacks_registered = True
        except Exception as e:
            logger.error(f"注册一键爬取状态回调失败: {e}")

    def _schedule(self, callback: Any, *args: Any, **kwargs: Any) -> bool:
        """把回调安全地切回 UI 主线程（可从后台线程调用）。"""
        try:
            return bool(self.app.call_later(callback, *args, **kwargs))
        except Exception as e:
            logger.debug(f"调度 UI 回调失败: {e}")
            return False

    def _notify(self, key: str, *, severity: str = "information", **kwargs: Any) -> None:
        """App 级通知：与当前所在页面无关，页面切换时依然可见。"""
        try:
            message = get_global_i18n().t(key, **kwargs)
        except Exception:
            message = key
        self._schedule(self.app.notify, message, severity=severity, timeout=5)


def get_one_click_crawl_manager(app: Any) -> OneClickCrawlManager:
    """获取（并惰性创建）绑定在 App 上的一键爬取管理器。"""
    manager = getattr(app, "_one_click_crawl_manager", None)
    if manager is None or manager.app is not app:
        manager = OneClickCrawlManager(app)
        setattr(app, "_one_click_crawl_manager", manager)
    return manager
