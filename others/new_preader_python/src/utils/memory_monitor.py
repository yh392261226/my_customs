"""
内存监控器：周期性采样进程内存使用，超阈值时触发缓存清理与渲染释放
"""

import asyncio
from typing import Optional, Callable

def _get_process_memory_bytes() -> int:
    try:
        import psutil
        proc = psutil.Process()
        # RSS 常驻集
        return int(proc.memory_info().rss)
    except Exception:
        try:
            import resource
            # ru_maxrss: macOS 返回字节？Linux 返回KB；统一转换为字节
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # macOS ru_maxrss 单位为字节，Linux 为KB。做个尽量安全的估计：
            return int(rss if rss > (1 << 20) else rss * 1024)
        except Exception:
            return 0

class MemoryMonitor:
    def __init__(self, 
                 high_water_bytes: int,
                 target_bytes: int,
                 on_pressure: Optional[Callable[[], None]] = None):
        """
        Args:
            high_water_bytes: 触发清理的上限
            target_bytes: 收缩目标（清理后尽量不超过该值）
            on_pressure: 当超阈值时调用的回调（执行缓存收缩与渲染释放）
        """
        self.high_water_bytes = high_water_bytes
        self.target_bytes = target_bytes
        self.on_pressure = on_pressure
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def _run(self, interval_sec: float):
        self._running = True
        try:
            while self._running:
                mem = _get_process_memory_bytes()
                if mem and mem >= self.high_water_bytes:
                    try:
                        if callable(self.on_pressure):
                            self.on_pressure()
                    except Exception:
                        pass
                await asyncio.sleep(interval_sec)
        finally:
            self._running = False

    def start(self, interval_sec: float = 2.0):
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run(interval_sec))
        except RuntimeError:
            # 无事件循环，忽略
            self._task = None

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None