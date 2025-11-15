"""
进度管理器 - 统一管理应用中的进度指示和加载状态
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProgressManager:
    """进度管理器类"""
    
    def __init__(self):
        self._progress_tasks: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, Callable] = {}
    
    def start_task(self, task_id: str, task_name: str, total_steps: int = 100) -> None:
        """
        开始一个新任务
        
        Args:
            task_id: 任务ID
            task_name: 任务名称
            total_steps: 总步骤数
        """
        self._progress_tasks[task_id] = {
            'name': task_name,
            'total_steps': total_steps,
            'current_step': 0,
            'start_time': datetime.now(),
            'status': 'running',
            'message': '',
            'progress': 0.0
        }
        logger.info(f"开始任务: {task_name} (ID: {task_id})")
    
    def update_progress(self, task_id: str, current_step: int, message: str = "") -> None:
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            current_step: 当前步骤
            message: 进度消息
        """
        if task_id not in self._progress_tasks:
            logger.warning(f"任务不存在: {task_id}")
            return
        
        task = self._progress_tasks[task_id]
        task['current_step'] = current_step
        task['message'] = message
        
        if task['total_steps'] > 0:
            progress = (current_step / task['total_steps']) * 100
            task['progress'] = min(progress, 100.0)
        
        # 触发回调
        if task_id in self._callbacks:
            try:
                self._callbacks[task_id](task)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")
        
        logger.debug(f"任务进度更新: {task['name']} - {current_step}/{task['total_steps']} ({task['progress']:.1f}%) - {message}")
    
    def complete_task(self, task_id: str, message: str = "完成") -> None:
        """
        完成任务
        
        Args:
            task_id: 任务ID
            message: 完成消息
        """
        if task_id not in self._progress_tasks:
            logger.warning(f"任务不存在: {task_id}")
            return
        
        task = self._progress_tasks[task_id]
        task['status'] = 'completed'
        task['message'] = message
        task['progress'] = 100.0
        task['end_time'] = datetime.now()
        
        # 计算耗时
        duration = (task['end_time'] - task['start_time']).total_seconds()
        task['duration'] = duration
        
        # 触发回调
        if task_id in self._callbacks:
            try:
                self._callbacks[task_id](task)
            except Exception as e:
                logger.error(f"完成回调执行失败: {e}")
        
        logger.info(f"任务完成: {task['name']} - 耗时: {duration:.2f}秒")
    
    def fail_task(self, task_id: str, error_message: str = "失败") -> None:
        """
        标记任务失败
        
        Args:
            task_id: 任务ID
            error_message: 错误消息
        """
        if task_id not in self._progress_tasks:
            logger.warning(f"任务不存在: {task_id}")
            return
        
        task = self._progress_tasks[task_id]
        task['status'] = 'failed'
        task['message'] = error_message
        task['end_time'] = datetime.now()
        
        # 计算耗时
        duration = (task['end_time'] - task['start_time']).total_seconds()
        task['duration'] = duration
        
        # 触发回调
        if task_id in self._callbacks:
            try:
                self._callbacks[task_id](task)
            except Exception as e:
                logger.error(f"失败回调执行失败: {e}")
        
        logger.error(f"任务失败: {task['name']} - {error_message}")
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务进度信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务进度信息字典
        """
        return self._progress_tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有任务
        
        Returns:
            所有任务字典
        """
        return self._progress_tasks.copy()
    
    def register_callback(self, task_id: str, callback: Callable) -> None:
        """
        注册进度回调函数
        
        Args:
            task_id: 任务ID
            callback: 回调函数
        """
        self._callbacks[task_id] = callback
    
    def unregister_callback(self, task_id: str) -> None:
        """
        取消注册进度回调函数
        
        Args:
            task_id: 任务ID
        """
        if task_id in self._callbacks:
            del self._callbacks[task_id]
    
    def clear_completed_tasks(self) -> None:
        """清除已完成的任务"""
        completed_tasks = []
        for task_id, task in self._progress_tasks.items():
            if task['status'] in ['completed', 'failed']:
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            del self._progress_tasks[task_id]
            if task_id in self._callbacks:
                del self._callbacks[task_id]
        
        logger.debug(f"已清除 {len(completed_tasks)} 个已完成任务")
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Returns:
            统计信息字典
        """
        total_tasks = len(self._progress_tasks)
        running_tasks = sum(1 for task in self._progress_tasks.values() if task['status'] == 'running')
        completed_tasks = sum(1 for task in self._progress_tasks.values() if task['status'] == 'completed')
        failed_tasks = sum(1 for task in self._progress_tasks.values() if task['status'] == 'failed')
        
        return {
            'total_tasks': total_tasks,
            'running_tasks': running_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks
        }


# 全局进度管理器实例
progress_manager = ProgressManager()