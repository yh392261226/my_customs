"""
解析进度回调模块，用于在解析过程中提供进度反馈
"""

from typing import Protocol, runtime_checkable, Optional, Any, Dict
import asyncio
import time


@runtime_checkable
class ProgressCallback(Protocol):
    """解析进度回调协议"""
    
    def on_progress(self, current: int, total: int, message: str = "") -> bool:
        """
        进度更新回调
        
        Args:
            current: 当前进度
            total: 总进度
            message: 进度消息
            
        Returns:
            bool: 是否继续解析，False表示取消
        """
        ...


class SimpleProgressCallback:
    """简单的进度回调实现"""
    
    def __init__(self):
        self.last_update_time = 0
        self.min_update_interval = 0.1  # 最小更新间隔0.1秒
    
    def on_progress(self, current: int, total: int, message: str = "") -> bool:
        """
        进度更新回调
        
        Args:
            current: 当前进度
            total: 总进度
            message: 进度消息
            
        Returns:
            bool: 是否继续解析，False表示取消
        """
        current_time = time.time()
        # 限制更新频率
        if current_time - self.last_update_time < self.min_update_interval:
            return True
            
        self.last_update_time = current_time
        
        if total > 0:
            percent = (current / total) * 100
            print(f"\r解析进度: {percent:.1f}% ({current}/{total}) {message}", end='', flush=True)
        else:
            print(f"\r解析中: {message}", end='', flush=True)
        
        return True  # 总是继续解析


class AsyncProgressCallback:
    """异步进度回调实现"""
    
    def __init__(self, callback_func=None):
        self.callback_func = callback_func
        self.last_update_time = 0
        self.min_update_interval = 0.1  # 最小更新间隔0.1秒
    
    async def on_progress(self, current: int, total: int, message: str = "") -> bool:
        """
        异步进度更新回调
        
        Args:
            current: 当前进度
            total: 总进度
            message: 进度消息
            
        Returns:
            bool: 是否继续解析，False表示取消
        """
        current_time = time.time()
        # 限制更新频率
        if current_time - self.last_update_time < self.min_update_interval:
            return True
            
        self.last_update_time = current_time
        
        if self.callback_func:
            # 调用外部提供的回调函数
            try:
                result = self.callback_func(current, total, message)
                if asyncio.iscoroutine(result):
                    result = await result
                return result if result is not None else True
            except Exception as e:
                print(f"进度回调出错: {e}")
                return True
        else:
            # 默认实现
            if total > 0:
                percent = (current / total) * 100
                print(f"\r解析进度: {percent:.1f}% ({current}/{total}) {message}", end='', flush=True)
            else:
                print(f"\r解析中: {message}", end='', flush=True)
            
            return True


class ParsingContext:
    """解析上下文，用于传递进度回调和其他解析参数"""
    
    def __init__(self, progress_callback: Optional[ProgressCallback] = None, 
                 timeout: Optional[float] = 300.0,  # 5分钟超时
                 chunk_size: int = 8192):
        self.progress_callback = progress_callback
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.start_time = time.time()
        self.cancel_requested = False
    
    async def update_progress(self, current: int, total: int, message: str = "") -> bool:
        """更新解析进度"""
        if self.cancel_requested:
            return False
            
        if self.progress_callback:
            if hasattr(self.progress_callback, 'on_progress'):
                if asyncio.iscoroutinefunction(self.progress_callback.on_progress):
                    return await self.progress_callback.on_progress(current, total, message)
                else:
                    return self.progress_callback.on_progress(current, total, message)
        
        return True
    
    def check_timeout(self) -> bool:
        """检查是否超时"""
        if self.timeout and (time.time() - self.start_time) > self.timeout:
            return True
        return False
    
    def cancel(self):
        """取消解析"""
        self.cancel_requested = True