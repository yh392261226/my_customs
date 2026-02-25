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
                    
                    # 获取存储文件夹
                    storage_folder = novel_site.get('storage_folder', 'novels')
                    
                    # 先解析小说详情获取标题
                    parse_result = await self._async_parse_novel_detail(parser, novel_id)
                    if 'success' in parse_result and not parse_result['success']:
                        # 解析失败
                        task.failed_count += 1
                        db_manager.add_crawl_history(
                            site_id=task.site_id,
                            novel_id=novel_id,
                            novel_title=f"书籍ID: {novel_id}",
                            status="failed",
                            file_path="",
                            error_message=parse_result.get('error_message', get_global_i18n().t('crawler.unknown_error'))
                        )
                        continue
                    
                    # 使用解析后的标题
                    actual_novel_title = parse_result.get('title', f"书籍ID: {novel_id}")
                    
                    # 使用增量爬取方法，传入已解析的结果
                    result = await self._incremental_crawl(
                        parser=parser,
                        novel_id=novel_id,
                        site_id=task.site_id,
                        novel_title=actual_novel_title,
                        storage_folder=storage_folder,
                        parse_result=parse_result
                    )
                    
                    # 假设解析器成功执行时返回的结果就是成功的
                    # 如果解析器抛出异常，_incremental_crawl 会返回 {'success': False, ...}
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
                        
                        # 检查是否是新爬取或更新
                        already_exists = result.get('already_exists', False)
                        file_path = result.get('file_path', '')
                        
                        if file_path and not already_exists and result.get('new_chapters', 0) > 0:
                            # 新爬取或有新章节更新，将书籍添加到书库
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
                        new_chapters = result.get('new_chapters', 0)
                        duplicate_count = result.get('duplicate_count', 0)
                        message = result.get('message', '')
                        
                        if new_chapters > 0:
                            logger.info(f"爬取成功: {result['title']}, 新增 {new_chapters} 章, 跳过 {duplicate_count} 章")
                        elif duplicate_count > 0:
                            logger.info(f"爬取成功: {result['title']}, 跳过 {duplicate_count} 个重复章节")
                        
                        self._notify_crawl_success(task_id, novel_id, result['title'], already_exists=already_exists)
                        
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
    
    async def _incremental_crawl(self, parser, novel_id: str, site_id: int, novel_title: str, storage_folder: str, parse_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        增量爬取：只爬取新章节，追加到已有文件
        
        Args:
            parser: 解析器实例
            novel_id: 小说ID
            site_id: 网站ID
            novel_title: 小说标题
            storage_folder: 存储文件夹
            parse_result: 可选，已解析的结果（避免重复解析）
        
        Returns:
            爬取结果
        """
        from src.core.database_manager import DatabaseManager
        from src.utils.file_helpers import (
            read_text_file, write_text_file, append_chapters_to_file,
            calculate_file_hash, calculate_content_hash, detect_chapter_duplicates
        )
        import os
        
        db_manager = DatabaseManager()
        
        # 1. 检查历史记录
        last_successful = db_manager.get_last_successful_crawl(site_id, novel_id)
        
        # 2. 获取已有的章节信息
        saved_chapters = {}
        if last_successful and last_successful.get('serial_mode'):
            saved_chapters = db_manager.get_saved_chapters(
                site_id, 
                novel_id, 
                record_id=last_successful['id']
            )
            
            # 如果没有追踪记录，尝试自动修复
            if not saved_chapters:
                logger.info(f"没有找到章节追踪记录，尝试自动修复...")
                repair_result = db_manager.repair_chapter_tracking(site_id, novel_id)
                if repair_result['success']:
                    logger.info(f"自动修复成功: {repair_result['message']}")
                    # 重新获取章节信息
                    saved_chapters = db_manager.get_saved_chapters(
                        site_id, 
                        novel_id, 
                        record_id=last_successful['id']
                    )
            
            logger.info(f"已有 {len(saved_chapters)} 个章节，从第 {len(saved_chapters)+1} 章开始爬取")
        
        # 3. 爬取所有章节（如果提供了parse_result则使用，否则重新解析）
        if parse_result is None:
            result = await self._async_parse_novel_detail(parser, novel_id)
            if 'success' in result and not result['success']:
                return result
        else:
            result = parse_result
        
        # 更新标题（从解析结果中获取）
        actual_title = result.get('title', novel_title)
        
        all_chapters = result.get('chapters', [])
        
        # 4. 章节去重
        new_chapters, duplicate_count = detect_chapter_duplicates(all_chapters, saved_chapters)
        
        # 5. 保存策略
        if new_chapters:
            if last_successful and os.path.exists(last_successful['file_path']):
                # 检查是否是真正的增量更新（有章节追踪记录）
                if saved_chapters and len(saved_chapters) > 0:
                    # 追加模式：读取已有文件，追加新章节
                    old_content = read_text_file(last_successful['file_path'])
                    new_content = append_chapters_to_file(old_content, new_chapters)
                    
                    # 保存文件
                    file_path = last_successful['file_path']
                    write_text_file(file_path, new_content)
                    
                    logger.info(f"追加模式：追加 {len(new_chapters)} 个新章节，跳过 {duplicate_count} 个重复章节")
                else:
                    # 覆盖模式：没有章节追踪记录，直接覆盖整个文件
                    storage_folder = os.path.expanduser(storage_folder)
                    file_path = parser.save_to_file(result, storage_folder)
                    
                    logger.info(f"覆盖模式：没有章节追踪记录，直接覆盖文件（共 {len(all_chapters)} 章）")
                
                # 更新数据库记录
                # 检查是否需要修复标题（如果标题等于ID，说明是旧数据）
                update_data = {
                    'file_path': file_path,
                    'chapter_count': len(all_chapters),
                    'last_chapter_index': len(all_chapters) - 1,
                    'last_chapter_title': all_chapters[-1].get('title', '') if all_chapters else '',
                    'content_hash': calculate_file_hash(file_path) if file_path else '',
                    'last_update_time': datetime.now().isoformat()
                }
                
                # 如果标题等于ID，修复为正确的标题
                if last_successful.get('novel_title') == novel_id:
                    logger.info(f"检测到错误标题（等于ID），自动修复: {novel_id} -> {actual_title}")
                    update_data['novel_title'] = actual_title
                
                db_manager.update_crawl_history_full(
                    last_successful['id'],
                    **update_data
                )
            else:
                # 首次爬取：保存完整文件
                storage_folder = os.path.expanduser(storage_folder)
                file_path = parser.save_to_file(result, storage_folder)
                
                # 创建爬取历史记录
                db_manager.add_crawl_history(
                    site_id=site_id,
                    novel_id=novel_id,
                    novel_title=actual_title,
                    status='success',
                    file_path=file_path,
                    error_message='',
                    book_type='多章节' if len(all_chapters) > 1 else '短篇',
                    chapter_count=len(all_chapters),
                    last_chapter_index=len(all_chapters) - 1 if all_chapters else -1,
                    last_chapter_title=all_chapters[-1].get('title', '') if all_chapters else '',
                    content_hash=calculate_file_hash(file_path) if file_path else '',
                    serial_mode=len(all_chapters) > 1  # 多章节自动启用连载模式
                )
                
                logger.info(f"首次爬取，保存 {len(all_chapters)} 个章节")
        else:
            # 没有新章节
            logger.info(f"没有新章节，跳过爬取（已跳过 {duplicate_count} 个重复章节）")
            return {
                'success': True,
                'title': novel_title,
                'message': '没有新章节需要更新',
                'new_chapters': 0,
                'duplicate_count': duplicate_count,
                'already_exists': True
            }
        
        # 6. 记录章节追踪信息
        chapter_tracking_data = []
        
        # 判断是否需要记录所有章节
        should_record_all = False
        
        # 如果是首次爬取（没有last_successful），记录所有章节
        if not last_successful:
            should_record_all = True
            logger.info(f"首次爬取，记录所有章节追踪信息")
        # 如果没有章节追踪记录（saved_chapters为空），说明是旧数据，也记录所有章节
        elif not saved_chapters:
            should_record_all = True
            logger.info(f"旧数据（无追踪记录），记录所有章节追踪信息")
        
        if should_record_all:
            # 记录所有章节
            for idx, chapter in enumerate(all_chapters):
                chapter_hash = calculate_content_hash(chapter.get('content', ''))
                chapter_tracking_data.append({
                    'chapter_index': idx,
                    'chapter_title': chapter.get('title', ''),
                    'chapter_hash': chapter_hash,
                    'crawl_time': datetime.now().isoformat()
                })
            logger.info(f"记录 {len(chapter_tracking_data)} 个章节追踪信息")
        else:
            # 如果是真正的增量更新，只记录新章节
            for idx, chapter in enumerate(new_chapters):
                # 找到该章节在所有章节中的实际索引
                actual_index = -1
                for i, ch in enumerate(all_chapters):
                    if ch.get('title') == chapter.get('title') or calculate_content_hash(ch.get('content', '')) == chapter.get('hash'):
                        actual_index = i
                        break
                
                if actual_index >= 0:
                    chapter_tracking_data.append({
                        'chapter_index': actual_index,
                        'chapter_title': chapter.get('title', ''),
                        'chapter_hash': chapter.get('hash', ''),
                        'crawl_time': datetime.now().isoformat()
                    })
            logger.info(f"增量更新，记录 {len(chapter_tracking_data)} 个新章节追踪信息")
        
        if chapter_tracking_data:
            db_manager.batch_add_chapter_tracking(
                site_id=site_id,
                novel_id=novel_id,
                chapters=chapter_tracking_data
            )
        
        # 反爬虫优化：添加延迟
        if len(new_chapters) > 5:
            import time
            delay = min(len(new_chapters) * 0.5, 10)  # 最多延迟10秒
            logger.info(f"爬取了 {len(new_chapters)} 个新章节，延迟 {delay} 秒")
            await asyncio.sleep(delay)
        
        return {
            'success': True,
            'title': result['title'],
            'file_path': file_path if 'file_path' in locals() else last_successful.get('file_path') if last_successful else '',
            'total_chapters': len(all_chapters),
            'new_chapters': len(new_chapters),
            'duplicate_count': duplicate_count,
            'already_exists': bool(last_successful)
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