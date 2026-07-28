"""
日志工具类，提供日志记录功能
"""

import os
import logging
import logging.handlers
from collections import deque
from typing import Optional, Any
from datetime import date

class LoggerSetup:
    """日志设置类"""
    
    @staticmethod
    def setup_logger(app_name: str, config_manager: Any, 
                    console_output: bool = True, file_output: bool = True,
                    log_file: Optional[str] = None) -> logging.Logger:
        """
        设置日志记录器
        
        Args:
            app_name: 应用名称
            config_manager: 配置管理器
            console_output: 是否输出到控制台
            file_output: 是否输出到文件
            log_file: 日志文件路径，如果为None则使用默认路径
            
        Returns:
            logging.Logger: 日志记录器
        """
        # 创建日志记录器
        logger = logging.getLogger(app_name)
        
        # 根据debug开关设置日志级别，支持开发模式
        debug_mode = config_manager.get_debug_mode()
        log_level = logging.DEBUG if debug_mode else logging.WARNING
        logger.setLevel(log_level)
        
        # 清除现有的处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        handlers = []
        # 添加控制台处理器
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            handlers.append(console_handler)
            logger.addHandler(console_handler)
        
        # 添加文件处理器
        if file_output:
            if log_file is None:
                # 使用默认日志文件路径
                log_dir = os.path.join(os.path.expanduser("~"), ".config", "new_preader", "logs")
                # 确保目录存在
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, f'{app_name}.log')
            
            # 确保日志文件目录存在
            log_dir = os.path.dirname(log_file)
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建文件处理器，使用RotatingFileHandler进行日志轮转
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, 
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
            logger.addHandler(file_handler)
        
        # 确保根 logger 也有相同的输出（项目内各模块 logger 默认冒泡到根 logger）
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        # 避免重复添加同类型同配置的 handler，做一个简单的去重判断
        existing_types = {type(h) for h in root_logger.handlers}
        for h in handlers:
            if type(h) not in existing_types:
                root_logger.addHandler(h)
        
        return logger
    
    @staticmethod
    def debug_log(func):
        """
        调试日志装饰器，当debug模式开启时记录函数调用和返回
        
        Args:
            func: 被装饰的函数
            
        Returns:
            装饰后的函数
        """
        def wrapper(*args, **kwargs):
            # 获取logger实例
            logger = logging.getLogger(func.__module__)
            
            # 检查debug模式
            if logger.isEnabledFor(logging.DEBUG):
                # 记录函数调用
                logger.debug(f"Use function {func.__name__}")
                logger.debug(f"Args: args={args}")
                logger.debug(f"Args: kwargs={kwargs}")
                
                try:
                    result = func(*args, **kwargs)
                    # 记录函数返回
                    logger.debug(f"Function {func.__name__} completed")
                    logger.debug(f"Return: {result}")
                    return result
                except Exception as e:
                    # 记录异常
                    logger.error(f"Function {func.__name__} raised an exception: {e}", exc_info=True)
                    raise
            else:
                return func(*args, **kwargs)
        return wrapper


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 日志记录器
    """
    logger = logging.getLogger(name)
    
    # 设置logger的propagate为True，确保子logger继承根logger的配置
    logger.propagate = True
    
    # 不再设置固定级别，由set_debug_mode统一管理级别
    # 这样可以确保debug模式控制正常工作
    
    return logger


# ---------------------------------------------------------------------------
# 内存日志（环形缓冲）：不落盘时自动启用，用于在界面上查看处理进度与步骤
# ---------------------------------------------------------------------------
_MEMORY_HANDLER = None
_FILE_LOGGING_ENABLED = False


class MemoryLogHandler(logging.Handler):
    """将日志记录保存在内存中的环形缓冲，避免写入文件带来的 IO 开销。"""

    def __init__(self, capacity: int = 1000):
        super().__init__()
        self.buffer = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(self.format(record))
        except Exception:
            pass

    def recent(self, n: int = None):
        items = list(self.buffer)
        return items if n is None else items[-n:]


def get_memory_handler() -> MemoryLogHandler:
    """获取（惰性创建）全局内存日志处理器。"""
    global _MEMORY_HANDLER
    if _MEMORY_HANDLER is None:
        _MEMORY_HANDLER = MemoryLogHandler()
        _MEMORY_HANDLER.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
    return _MEMORY_HANDLER


def get_recent_memory_logs(n: int = None):
    """返回内存中保留的最近日志（不落盘时用于界面展示）。"""
    return get_memory_handler().recent(n)


def is_file_logging_enabled() -> bool:
    """当前是否处于文件日志模式（用于 UI 判断是否展示内存日志）。"""
    return _FILE_LOGGING_ENABLED


def set_debug_mode(debug_mode: bool) -> None:
    """
    设置调试模式，控制所有logger的级别与输出方式。
    
    - debug_mode=True  -> 文件日志模式（开发模式或用户开启调试时）
    - debug_mode=False -> 内存模式（自动开启，不写文件，用于在界面查看进度）
    
    Args:
        debug_mode: 是否启用文件日志/调试模式
    """
    global _FILE_LOGGING_ENABLED

    # 内存模式同样以 DEBUG 级别采集，确保处理进度与步骤可见
    log_level = logging.DEBUG

    # 完全重置logging配置
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.root.handlers = []

    # 设置根logger的级别
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 设置所有已存在的logger的级别
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)

    if debug_mode:
        # 文件日志模式：写入磁盘
        _FILE_LOGGING_ENABLED = True
        log_dir = os.path.join(os.path.expanduser("~"), ".config", "new_preader", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'application_{date.today()}.log')

        # 创建文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

        # 只在文件记录调试模式启用信息
        root_logger.info(f"Debug mode enabled, log level set to: {logging.getLevelName(log_level)}")
    else:
        # 内存模式：不写文件，自动在内存中保留日志供界面展示
        _FILE_LOGGING_ENABLED = False
        mem_handler = get_memory_handler()
        mem_handler.setLevel(log_level)
        root_logger.addHandler(mem_handler)





def setup_logging_from_config(config_manager) -> None:
    """
    根据配置管理器设置日志级别和文件输出
    
    Args:
        config_manager: 配置管理器实例
    """
    try:
        config = config_manager.get_config()
        advanced_config = config.get("advanced", {})
        
        # 统一使用debug_mode控制日志，支持开发模式
        debug_mode = config_manager.get_debug_mode()
        
        if debug_mode:
            # 启用调试模式
            set_debug_mode(True)
        else:
            # 禁用调试模式（静默模式）
            set_debug_mode(False)
            
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f" Setting log level from config failed: {e}")
        # 出错时默认使用INFO级别
        set_debug_mode(False)