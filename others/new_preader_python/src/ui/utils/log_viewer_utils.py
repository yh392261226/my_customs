"""
日志查看器公用逻辑。

把「内存模式 / 文件模式」两种日志查看器的打开入口收敛到这里，
供书库批量操作、爬取管理等界面以及 App 全局快捷键复用，
避免各界面重复实现相同的打开与去重逻辑。
"""
import os
from datetime import date
from typing import Optional

from src.utils.logger import get_logger, is_file_logging_enabled

logger = get_logger(__name__)


def get_log_file_path() -> str:
    """返回当前应用日志文件路径（兼容调试/生产模式与回退）。"""
    try:
        from src.config.config_manager import ConfigManager

        config_manager = ConfigManager.get_instance()
        log_dir = os.path.join(os.path.expanduser("~"), ".config", "new_preader", "logs")

        if config_manager.get_debug_mode():
            log_file = os.path.join(log_dir, f"application_{date.today()}.log")
        else:
            log_file = os.path.join(log_dir, "application.log")

        # 主日志文件不存在时，回退到目录下最新的 .log 文件
        if not os.path.exists(log_file) and os.path.exists(log_dir):
            log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
            if log_files:
                log_files.sort(
                    key=lambda x: os.path.getmtime(os.path.join(log_dir, x)),
                    reverse=True,
                )
                log_file = os.path.join(log_dir, log_files[0])

        return log_file
    except Exception as e:
        logger.error(f"获取日志文件路径失败: {e}")
        return os.path.join(
            os.path.expanduser("~"), ".config", "new_preader", "logs", "application.log"
        )


def open_log_viewer(app) -> str:
    """打开日志查看器（全局复用）。

    Returns:
        str: 打开状态，取值为
            "memory"   已打开内存日志
            "file"     已打开文件日志
            "noop"     日志查看器已在栈中，未重复打开
            "missing"  日志文件不存在
            "error"    打开失败
    """
    from src.ui.dialogs.batch_ops_dialog import LogViewerPopup

    try:
        # 去重：已有日志查看器则不重复打开
        if any(isinstance(s, LogViewerPopup) for s in app.screen_stack):
            return "noop"

        # 非文件日志模式（内存模式）：直接展示内存中的日志
        if not is_file_logging_enabled():
            app.push_screen(LogViewerPopup("内存日志", memory_mode=True))
            return "memory"

        log_file_path = get_log_file_path()
        if not os.path.exists(log_file_path):
            return "missing"

        app.push_screen(LogViewerPopup(log_file_path))
        return "file"
    except Exception as e:
        logger.error(f"打开日志查看器失败: {e}")
        return "error"
