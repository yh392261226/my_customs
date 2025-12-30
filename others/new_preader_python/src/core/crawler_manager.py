"""
后台爬取管理器
支持异步后台爬取，页面切换时继续爬取，全局状态通知
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import threading
from datetime import datetime

from src.utils.logger import get_logger
from src.locales.i18n_manager import get_global_i18n

logger = get_logger(__name__)

class CrawlStatus(Enum):
    """爬取状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

@dataclass
class CrawlTask:
    """爬取任务"""
    task_id: str
    site_id: int
    novel_ids: List[str]
    proxy_config: Dict[str, Any]
    status: CrawlStatus = CrawlStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: int = 0
    total: int = 0
    current_novel_id: Optional[str] = None
    success_count: int = 0
    failed_count: int = 0
    error_message: Optional[str] = None


class CrawlerManager:
    """后台爬取管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._tasks: Dict[str, CrawlTask] = {}
            self._running_tasks: Dict[str, asyncio.Task] = {}
            self._status_callbacks: List[Callable] = []
            self._notification_callbacks: List[Callable] = []
            self._lock = threading.Lock()
            self._initialized = True
    
    def register_status_callback(self, callback: Callable) -> None:
        """注册状态回调函数"""
        with self._lock:
            if callback not in self._status_callbacks:
                self._status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable) -> None:
        """注销状态回调函数"""
        with self._lock:
            if callback in self._status_callbacks:
                self._status_callbacks.remove(callback)
    
    def register_notification_callback(self, callback: Callable) -> None:
        """注册通知回调函数"""
        with self._lock:
            if callback not in self._notification_callbacks:
                self._notification_callbacks.append(callback)
    
    def unregister_notification_callback(self, callback: Callable) -> None:
        """注销通知回调函数"""
        with self._lock:
            if callback in self._notification_callbacks:
                self._notification_callbacks.remove(callback)
    
    def _notify_status_change(self, task_id: str) -> None:
        """通知状态变化"""
        task = self._tasks.get(task_id)
        if task:
            with self._lock:
                for callback in self._status_callbacks:
                    try:
                        callback(task_id, task)
                    except Exception as e:
                        logger.error(f"状态回调执行失败: {e}")
    
    def _notify_crawl_success(self, task_id: str, novel_id: str, novel_title: str, already_exists: bool = False) -> None:
        """通知爬取成功
        
        Args:
            task_id: 任务ID
            novel_id: 小说ID
            novel_title: 小说标题
            already_exists: 是否文件已存在
        """
        with self._lock:
            for callback in self._notification_callbacks:
                try:
                    callback(task_id, novel_id, novel_title, already_exists)
                except Exception as e:
                    logger.error(f"成功通知回调执行失败: {e}")
    
    def get_active_tasks(self) -> List[CrawlTask]:
        """获取活跃的爬取任务"""
        with self._lock:
            return [task for task in self._tasks.values() if task.status in [CrawlStatus.RUNNING, CrawlStatus.PENDING]]
    
    def get_task_by_id(self, task_id: str) -> Optional[CrawlTask]:
        """根据任务ID获取任务"""
        return self._tasks.get(task_id)
    
    def start_crawl_task(self, site_id: int, novel_ids: List[str], proxy_config: Dict[str, Any]) -> str:
        """开始新的爬取任务"""
        import uuid
        
        task_id = str(uuid.uuid4())
        
        task = CrawlTask(
            task_id=task_id,
            site_id=site_id,
            novel_ids=novel_ids,
            proxy_config=proxy_config,
            status=CrawlStatus.PENDING,
            total=len(novel_ids)
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        # 异步启动爬取任务
        asyncio.create_task(self._run_crawl_task(task_id))
        
        return task_id
    
    async def _run_crawl_task(self, task_id: str) -> None:
        """运行爬取任务"""
        task = self._tasks.get(task_id)
        if not task:
            return
        
        # 检查任务是否已经被停止
        if task.status == CrawlStatus.STOPPED:
            return
        
        # 更新任务状态为运行中
        task.status = CrawlStatus.RUNNING
        task.start_time = datetime.now()
        self._notify_status_change(task_id)
        
        try:
            # 导入相关模块
            from src.core.database_manager import DatabaseManager
            from src.spiders import create_parser
            
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            
            # 获取网站信息
            novel_site = db_manager.get_novel_site_by_id(task.site_id)
            if not novel_site:
                task.status = CrawlStatus.FAILED
                task.error_message = get_global_i18n().t('crawler.site_not_found')
                self._notify_status_change(task_id)
                return
            
            # 获取解析器名称
            parser_name = novel_site.get('parser')
            if not parser_name:
                task.status = CrawlStatus.FAILED
                task.error_message = get_global_i18n().t('crawler.no_parser')
                self._notify_status_change(task_id)
                return
            
            # 创建解析器
            parser = create_parser(parser_name, task.proxy_config, novel_site.get('name'), novel_site.get('url'))
            if not parser:
                task.status = CrawlStatus.FAILED
                task.error_message = f"{get_global_i18n().t('crawler.parser_not_found')}: {parser_name}"
                self._notify_status_change(task_id)
                return
            
            # 爬取每个小说
            for i, novel_id in enumerate(task.novel_ids):
                # 检查是否应该停止
                if task.status == CrawlStatus.STOPPED:
                    break
                
                # 检查连续失败次数，如果超过3次则跳过
                consecutive_failures = db_manager.get_consecutive_failure_count(task.site_id, novel_id)
                if consecutive_failures >= 3:
                    logger.info(f"跳过小说 {novel_id}，连续失败次数已达 {consecutive_failures} 次")
                    task.failed_count += 1
                    
                    # 保存跳过记录，但不增加连续失败计数（使用特殊标记）
                    db_manager.add_crawl_history(
                        site_id=task.site_id,
                        novel_id=novel_id,
                        novel_title=novel_id,
                        status="failed",
                        file_path="",
                        error_message=f"连续失败 {consecutive_failures} 次，已跳过"
                    )
                    # 跳过这个小说，继续下一个
                    continue
                
                # 更新当前爬取状态
                task.current_novel_id = novel_id
                task.progress = i + 1
                self._notify_status_change(task_id)
                
                try:
                    # 重置解析器的章节计数器，防止跨书籍计数延续
                    if hasattr(parser, 'chapter_count'):
                        parser.chapter_count = 0
                    
                    # 执行爬取
                    result = await self._async_parse_novel_detail(parser, novel_id)
                    
                    # 假设解析器成功执行时返回的结果就是成功的
                    # 如果解析器抛出异常，_async_parse_novel_detail 会返回 {'success': False, ...}
                    if 'success' in result and not result['success']:
                        # 解析器明确返回失败
                        task.failed_count += 1
                        
                        # 保存失败记录
                        db_manager.add_crawl_history(
                            site_id=task.site_id,
                            novel_id=novel_id,
                            novel_title=novel_id,
                            status="failed",
                            file_path="",
                            error_message=result.get('error_message', get_global_i18n().t('crawler.unknown_error'))
                        )
                    else:
                        # 解析器成功返回小说内容
                        task.success_count += 1
                        
                        # 获取存储文件夹并保存文件
                        storage_folder = novel_site.get('storage_folder', 'novels')
                        import os
                        storage_folder = os.path.expanduser(storage_folder)
                        
                        # 调用解析器的 save_to_file 方法实际保存文件
                        file_path = parser.save_to_file(result, storage_folder)
                        
                        # 检查文件是否成功保存
                        if file_path == 'already_exists':
                            # 文件已存在，不添加新记录，但显示成功消息
                            logger.info(f"小说文件已存在，跳过保存: {result['title']}")
                            # 发送成功通知（但文件已存在）
                            self._notify_crawl_success(task_id, novel_id, result['title'], already_exists=True)
                        else:
                            # 文件成功保存，保存到数据库
                            db_manager.add_crawl_history(
                                site_id=task.site_id,
                                novel_id=novel_id,
                                novel_title=result['title'],
                                status="success",
                                file_path=file_path,
                                error_message=""
                            )
                            
                            # 将书籍添加到书库
                            try:
                                from src.core.bookshelf import Bookshelf
                                bookshelf = Bookshelf()
                                
                                # 合并网站标签和解析器返回的标签
                                site_tags = novel_site.get('tags', '')
                                result_tags = result.get('tags', '')
                                
                                # 合并标签逻辑：如果有网站标签，则添加到书籍标签中
                                if site_tags:
                                    if result_tags:
                                        combined_tags = f"{result_tags},{site_tags}"
                                    else:
                                        combined_tags = site_tags
                                else:
                                    combined_tags = result_tags
                                
                                # 使用合并后的标签添加书籍
                                book = bookshelf.add_book(file_path, result['title'], result.get('author', ''), combined_tags)
                                
                                logger.info(f"小说已添加到书库: {result['title']}, 作者: {result.get('author', '')}, 标签: {combined_tags}")
                            except Exception as e:
                                logger.error(f"添加到书库失败: {e}")
                            
                            # 发送成功通知
                            self._notify_crawl_success(task_id, novel_id, result['title'])
                        
                except Exception as e:
                    task.failed_count += 1
                    logger.error(f"爬取小说 {novel_id} 时发生异常: {e}")
                    
                    # 保存异常记录
                    db_manager.add_crawl_history(
                        site_id=task.site_id,
                        novel_id=novel_id,
                        novel_title=novel_id,
                        status="failed",
                        file_path="",
                        error_message=str(e)
                    )
            
            # 更新任务状态
            if task.status != CrawlStatus.STOPPED:
                task.status = CrawlStatus.COMPLETED
                task.end_time = datetime.now()
                
        except Exception as e:
            logger.error(f"爬取任务执行失败: {e}")
            task.status = CrawlStatus.FAILED
            task.error_message = str(e)
        
        finally:
            # 清理任务
            with self._lock:
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]
            
            # 发送最终状态通知
            self._notify_status_change(task_id)
    
    async def _async_parse_novel_detail(self, parser, novel_id: str) -> Dict[str, Any]:
        """异步解析小说详情"""
        try:
            # 使用线程池执行同步的解析方法
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, parser.parse_novel_detail, novel_id)
            return result
        except Exception as e:
            logger.error(f"解析小说详情失败: {e}")
            return {
                'success': False,
                'error_message': str(e)
            }
    
    def stop_crawl_task(self, task_id: str) -> bool:
        """停止爬取任务"""
        try:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"停止任务失败: 任务 {task_id} 不存在")
                return False
            
            if task.status in [CrawlStatus.COMPLETED, CrawlStatus.FAILED, CrawlStatus.STOPPED]:
                logger.info(f"停止任务: 任务 {task_id} 已处于最终状态 {task.status}")
                return False
            
            # 更新任务状态
            task.status = CrawlStatus.STOPPED
            task.end_time = datetime.now()
            
            # 取消异步任务
            running_task = self._running_tasks.get(task_id)
            if running_task:
                try:
                    running_task.cancel()
                    logger.info(f"已取消异步任务: {task_id}")
                except Exception as e:
                    logger.error(f"取消异步任务失败: {task_id}, 错误: {e}")
                
                with self._lock:
                    if task_id in self._running_tasks:
                        del self._running_tasks[task_id]
                        logger.info(f"已从运行任务列表中移除: {task_id}")
            else:
                logger.warning(f"停止任务: 任务 {task_id} 不在运行任务列表中")
            
            # 发送状态变更通知
            self._notify_status_change(task_id)
            logger.info(f"成功停止任务: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"停止任务时发生异常: {task_id}, 错误: {e}")
            return False
    
    def get_crawl_summary(self) -> Dict[str, Any]:
        """获取爬取任务摘要"""
        with self._lock:
            active_tasks = self.get_active_tasks()
            completed_tasks = [task for task in self._tasks.values() if task.status == CrawlStatus.COMPLETED]
            
            return {
                'active_count': len(active_tasks),
                'completed_count': len(completed_tasks),
                'total_tasks': len(self._tasks),
                'active_tasks': active_tasks
            }