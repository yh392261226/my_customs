"""
性能监控和错误追踪系统
用于监控系统性能和追踪错误
"""

import time
import psutil
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import json
import os

from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_usage_percent: float
    disk_free: int
    disk_total: int
    process_count: int
    thread_count: int
    uptime: float
    custom_metrics: Dict[str, Any] = None


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    timestamp: float
    error_type: str
    error_message: str
    traceback: str
    context: Dict[str, Any]
    severity: str  # 'low', 'medium', 'high', 'critical'


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, interval: float = 5.0):
        """
        初始化性能监控器
        
        Args:
            interval: 监控间隔（秒）
        """
        self.interval = interval
        self.running = False
        self.monitor_thread = None
        self.metrics_history: List[PerformanceMetrics] = []
        self.custom_collectors: List[Callable[[], Dict[str, Any]]] = []
        self.start_time = time.time()
        
        # 限制历史记录数量
        self.max_history = 1000
    
    def start(self):
        """启动性能监控"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("性能监控已启动")
    
    def stop(self):
        """停止性能监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info("性能监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                metrics = self.collect_metrics()
                self.metrics_history.append(metrics)
                
                # 限制历史记录数量
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"性能监控循环出错: {e}")
                time.sleep(self.interval)
    
    def collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = memory.used
        memory_total = memory.total
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        disk_free = disk.free
        disk_total = disk.total
        
        # 进程和线程数量
        process_count = len(psutil.pids())
        thread_count = threading.active_count()
        
        # 运行时间
        uptime = time.time() - self.start_time
        
        # 自定义指标
        custom_metrics = {}
        for collector in self.custom_collectors:
            try:
                custom_metrics.update(collector())
            except Exception as e:
                logger.error(f"收集自定义指标失败: {e}")
        
        return PerformanceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used=memory_used,
            memory_total=memory_total,
            disk_usage_percent=disk_usage_percent,
            disk_free=disk_free,
            disk_total=disk_total,
            process_count=process_count,
            thread_count=thread_count,
            uptime=uptime,
            custom_metrics=custom_metrics
        )
    
    def add_custom_collector(self, collector: Callable[[], Dict[str, Any]]):
        """添加自定义指标收集器"""
        self.custom_collectors.append(collector)
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        return self.collect_metrics()
    
    def get_metrics_history(self, limit: int = None) -> List[PerformanceMetrics]:
        """获取性能指标历史"""
        if limit:
            return self.metrics_history[-limit:]
        return self.metrics_history.copy()
    
    def get_average_metrics(self, minutes: int = 5) -> Optional[PerformanceMetrics]:
        """获取指定时间内的平均性能指标"""
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return None
        
        # 计算平均值
        count = len(recent_metrics)
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / count
        avg_memory = sum(m.memory_percent for m in recent_metrics) / count
        avg_disk = sum(m.disk_usage_percent for m in recent_metrics) / count
        
        # 返回最近的指标，但使用平均值
        latest = recent_metrics[-1]
        return PerformanceMetrics(
            timestamp=latest.timestamp,
            cpu_percent=avg_cpu,
            memory_percent=avg_memory,
            memory_used=latest.memory_used,
            memory_total=latest.memory_total,
            disk_usage_percent=avg_disk,
            disk_free=latest.disk_free,
            disk_total=latest.disk_total,
            process_count=latest.process_count,
            thread_count=latest.thread_count,
            uptime=latest.uptime,
            custom_metrics=latest.custom_metrics
        )
    
    def is_system_overloaded(self, cpu_threshold: float = 80.0, 
                           memory_threshold: float = 85.0) -> bool:
        """检查系统是否过载"""
        current = self.get_current_metrics()
        return (current.cpu_percent > cpu_threshold or 
                current.memory_percent > memory_threshold)


class ErrorTracker:
    """错误追踪器"""
    
    def __init__(self, max_errors: int = 1000):
        """
        初始化错误追踪器
        
        Args:
            max_errors: 最大错误记录数量
        """
        self.errors: List[ErrorInfo] = []
        self.max_errors = max_errors
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        self.severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None, 
                   severity: str = "medium") -> ErrorInfo:
        """
        追踪错误
        
        Args:
            error: 错误对象
            context: 错误上下文
            severity: 错误严重程度
            
        Returns:
            错误信息对象
        """
        import traceback
        
        error_info = ErrorInfo(
            timestamp=time.time(),
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=traceback.format_exc(),
            context=context or {},
            severity=severity
        )
        
        self.errors.append(error_info)
        self.severity_counts[severity] += 1
        
        # 限制错误记录数量
        if len(self.errors) > self.max_errors:
            removed = self.errors.pop(0)
            self.severity_counts[removed.severity] -= 1
        
        # 调用回调函数
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}")
        
        # 记录错误
        logger.error(f"错误追踪: {error_info.error_type} - {error_info.error_message}")
        
        return error_info
    
    def add_error_callback(self, callback: Callable[[ErrorInfo], None]):
        """添加错误回调函数"""
        self.error_callbacks.append(callback)
    
    def get_errors(self, limit: int = None, severity: str = None) -> List[ErrorInfo]:
        """获取错误列表"""
        errors = self.errors.copy()
        
        if severity:
            errors = [e for e in errors if e.severity == severity]
        
        if limit:
            errors = errors[-limit:]
        
        return errors
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        total_errors = len(self.errors)
        recent_errors = len([e for e in self.errors if time.time() - e.timestamp < 3600])  # 1小时内
        
        return {
            "total_errors": total_errors,
            "recent_errors": recent_errors,
            "severity_counts": self.severity_counts.copy(),
            "error_types": self._get_error_types_distribution()
        }
    
    def _get_error_types_distribution(self) -> Dict[str, int]:
        """获取错误类型分布"""
        type_counts = {}
        for error in self.errors:
            error_type = error.error_type
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
        return type_counts
    
    def clear_errors(self):
        """清空错误记录"""
        self.errors.clear()
        self.severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}


class SystemMonitor:
    """系统监控器 - 组合性能监控和错误追踪"""
    
    def __init__(self, perf_interval: float = 5.0):
        """
        初始化系统监控器
        
        Args:
            perf_interval: 性能监控间隔（秒）
        """
        self.performance_monitor = PerformanceMonitor(perf_interval)
        self.error_tracker = ErrorTracker()
        self.alert_callbacks: List[Callable[[str, Any], None]] = []
    
    def start(self):
        """启动监控"""
        self.performance_monitor.start()
        logger.info("系统监控已启动")
    
    def stop(self):
        """停止监控"""
        self.performance_monitor.stop()
        logger.info("系统监控已停止")
    
    def add_alert_callback(self, callback: Callable[[str, Any], None]):
        """添加警报回调函数"""
        self.alert_callbacks.append(callback)
    
    def check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状况"""
        perf_metrics = self.performance_monitor.get_current_metrics()
        error_stats = self.error_tracker.get_error_stats()
        
        # 检查是否过载
        is_overloaded = self.performance_monitor.is_system_overloaded()
        
        # 检查错误率
        recent_errors = error_stats["recent_errors"]
        high_severity_errors = sum(
            error_stats["severity_counts"].get(sev, 0) 
            for sev in ["high", "critical"]
        )
        
        health_status = "healthy"
        if is_overloaded or recent_errors > 10 or high_severity_errors > 0:
            health_status = "warning"
        if is_overloaded and high_severity_errors > 5:
            health_status = "critical"
        
        return {
            "health_status": health_status,
            "performance_metrics": perf_metrics,
            "error_stats": error_stats,
            "is_overloaded": is_overloaded,
            "timestamp": time.time()
        }
    
    def get_system_report(self) -> Dict[str, Any]:
        """获取系统报告"""
        health = self.check_system_health()
        
        return {
            "report_time": datetime.now().isoformat(),
            "health_status": health["health_status"],
            "performance": {
                "cpu_percent": health["performance_metrics"].cpu_percent,
                "memory_percent": health["performance_metrics"].memory_percent,
                "disk_usage_percent": health["performance_metrics"].disk_usage_percent,
                "uptime_hours": health["performance_metrics"].uptime / 3600
            },
            "errors": health["error_stats"],
            "alerts": self._get_pending_alerts()
        }
    
    def _get_pending_alerts(self) -> List[Dict[str, Any]]:
        """获取待处理的警报"""
        alerts = []
        health = self.check_system_health()
        
        if health["is_overloaded"]:
            alerts.append({
                "type": "system_overload",
                "message": "系统资源使用过高",
                "severity": "high",
                "data": {
                    "cpu_percent": health["performance_metrics"].cpu_percent,
                    "memory_percent": health["performance_metrics"].memory_percent
                }
            })
        
        if health["error_stats"]["recent_errors"] > 10:
            alerts.append({
                "type": "high_error_rate",
                "message": "近期错误率较高",
                "severity": "medium",
                "data": {
                    "recent_error_count": health["error_stats"]["recent_errors"]
                }
            })
        
        return alerts


# 全局监控实例
_system_monitor = None


def get_system_monitor() -> SystemMonitor:
    """获取系统监控器实例"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def start_system_monitor():
    """启动系统监控"""
    monitor = get_system_monitor()
    monitor.start()


def stop_system_monitor():
    """停止系统监控"""
    monitor = get_system_monitor()
    monitor.stop()