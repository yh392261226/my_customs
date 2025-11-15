"""
统一异常处理模块，提供标准化的异常处理机制
"""

import traceback
import time
import asyncio
from typing import Callable, Any, Optional, Type, Tuple, Dict, Union
from functools import wraps
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ExceptionHandler:
    """异常处理类"""
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        operation: str,
        user_message: Optional[str] = None,
        log_level: str = "error",
        reraise: bool = False,
        show_traceback: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        统一处理异常
        
        Args:
            exception: 捕获的异常
            operation: 操作描述
            user_message: 用户友好的错误消息
            log_level: 日志级别 (debug, info, warning, error)
            reraise: 是否重新抛出异常
            show_traceback: 是否显示完整堆栈跟踪
            
        Returns:
            Tuple[bool, Optional[str]]: (是否处理成功, 错误消息)
        """
        error_msg = user_message or f"{operation}时发生错误"
        
        # 记录异常详细信息
        if log_level == "debug":
            logger.debug(f"{error_msg}: {str(exception)}")
            if show_traceback:
                logger.debug(f"异常堆栈:\n{traceback.format_exc()}")
        elif log_level == "info":
            logger.info(f"{error_msg}: {str(exception)}")
        elif log_level == "warning":
            logger.warning(f"{error_msg}: {str(exception)}")
        else:
            logger.error(f"{error_msg}: {str(exception)}")
            if show_traceback:
                logger.debug(f"异常堆栈:\n{traceback.format_exc()}")
        
        # 重新抛出异常
        if reraise:
            raise exception
            
        return False, error_msg
    
    @staticmethod
    def safe_execute(
        func: Callable,
        operation: str,
        default_return: Any = None,
        user_message: Optional[str] = None,
        log_level: str = "error",
        ignore_exceptions: Tuple[Type[Exception], ...] = ()
    ) -> Any:
        """
        安全执行函数，捕获并处理异常
        
        Args:
            func: 要执行的函数
            operation: 操作描述
            default_return: 异常时的默认返回值
            user_message: 用户友好的错误消息
            log_level: 日志级别
            ignore_exceptions: 要忽略的异常类型
        
        Returns:
            函数执行结果或默认返回值
        """
        try:
            return func()
        except ignore_exceptions:
            # 忽略指定的异常类型
            raise
        except Exception as e:
            ExceptionHandler.handle_exception(e, operation, user_message, log_level, reraise=False)
            return default_return


def exception_handler(
    operation: str,
    default_return: Any = None,
    user_message: Optional[str] = None,
    log_level: str = "error",
    ignore_exceptions: Tuple[Type[Exception], ...] = ()
):
    """
    异常处理装饰器
    
    Args:
        operation: 操作描述
        default_return: 异常时的默认返回值
        user_message: 用户友好的错误消息
    log_level: 日志级别
    ignore_exceptions: 要忽略的异常类型
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return ExceptionHandler.safe_execute(
                lambda: func(*args, **kwargs),
                operation,
                default_return,
                user_message,
                log_level,
                ignore_exceptions
            )
        return wrapper
    return decorator


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    operation: str = "操作",
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: str = "warning"
):
    """
    重试装饰器，在发生异常时自动重试
    
    Args:
        max_retries: 最大重试次数
        delay: 初始重试延迟（秒）
        backoff_factor: 指数退避因子
        operation: 操作描述
        exceptions: 触发重试的异常类型
        log_level: 重试日志级别
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        current_delay = delay * (backoff_factor ** attempt)
                        if log_level == "debug":
                            logger.debug(f"{operation}失败，第{attempt + 1}次重试 (等待{current_delay:.1f}秒): {str(e)}")
                        elif log_level == "info":
                            logger.info(f"{operation}失败，第{attempt + 1}次重试 (等待{current_delay:.1f}秒): {str(e)}")
                        else:
                            logger.warning(f"{operation}失败，第{attempt + 1}次重试 (等待{current_delay:.1f}秒): {str(e)}")
                        time.sleep(current_delay)
                    else:
                        logger.error(f"{operation}失败，已达到最大重试次数: {str(e)}")
                        raise last_exception
            return None
        return wrapper
    return decorator


def async_retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    operation: str = "操作",
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_level: str = "warning"
):
    """
    异步重试装饰器，在发生异常时自动重试
    
    Args:
        max_retries: 最大重试次数
        delay: 初始重试延迟（秒）
        backoff_factor: 指数退避因子
        operation: 操作描述
        exceptions: 触发重试的异常类型
        log_level: 重试日志级别
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        current_delay = delay * (backoff_factor ** attempt)
                        if log_level == "debug":
                            logger.debug(f"{operation}失败，第{attempt + 1}次重试 (等待{current_delay:.1f}秒): {str(e)}")
                        elif log_level == "info":
                            logger.info(f"{operation}失败，第{attempt + 1}次重试 (等待{current_delay:.1f}秒): {str(e)}")
                        else:
                            logger.warning(f"{operation}失败，第{attempt + 1}次重试 (等待{current_delay:.1f}秒): {str(e)}")
                        await asyncio.sleep(current_delay)
                    else:
                        logger.error(f"{operation}失败，已达到最大重试次数: {str(e)}")
                        raise last_exception
            return None
        return wrapper
    return decorator


# 常用的异常处理函数
def handle_file_operation(func: Callable) -> Callable:
    """文件操作异常处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return ExceptionHandler.safe_execute(
            lambda: func(*args, **kwargs),
            "文件操作",
            None,
            "文件操作失败，请检查文件路径和权限"
        )
    return wrapper


def handle_database_operation(func: Callable) -> Callable:
    """数据库操作异常处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return ExceptionHandler.safe_execute(
            lambda: func(*args, **kwargs),
            "数据库操作",
            None,
            "数据库操作失败，请检查数据库连接"
        )
    return wrapper


def handle_network_operation(func: Callable) -> Callable:
    """网络操作异常处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return ExceptionHandler.safe_execute(
            lambda: func(*args, **kwargs),
            "网络操作",
            None,
            "网络连接失败，请检查网络设置"
        )
    return wrapper