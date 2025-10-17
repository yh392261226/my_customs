"""
NewReader 主程序入口
"""

import argparse
import logging
import sys
import traceback
from typing import NoReturn
from textual_serve.server import Server

def handle_error(message: str, exit_code: int = 1) -> NoReturn:
    """处理致命错误并退出"""
    logging.error(message)
    print(f"错误: {message}", file=sys.stderr)
    sys.exit(exit_code)

# 在导入应用之前初始化全局 i18n，避免导入阶段调用 i18n 崩溃
try:
    from src.locales.i18n_manager import init_global_i18n, set_global_locale, get_global_i18n
    from src.config.config_manager import ConfigManager
    init_global_i18n()
    try:
        cfg = ConfigManager().get_config()
        lang = (cfg.get("advanced", {}) or {}).get("language", "zh_CN")
        if isinstance(lang, str):
            set_global_locale(lang)
    except Exception:
        # 保持默认语言
        pass
except Exception:
    # 如果初始化失败，继续启动，后续模块内有兜底逻辑
    pass

from src.ui.app import NewReaderApp
from src.utils.logger import setup_logging_from_config
from src.config.config_manager import ConfigManager

def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="NewReader - 现代化终端小说阅读器")
    parser.add_argument("--config", help="指定配置文件路径")
    parser.add_argument("--web", action="store_true", help="启用浏览器模式")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--host", default="localhost", help="Web 服务绑定地址，默认 localhost")
    parser.add_argument("--port", type=int, default=8000, help="Web 服务端口，默认 8000，若被占用将自动顺延")
    parser.add_argument("book_file", nargs="?", help="直接打开指定的小说文件")
    args = parser.parse_args()
    
    # 如果指定了小说文件，验证文件是否存在
    if args.book_file:
        import os
        if not os.path.exists(args.book_file):
            handle_error(f"文件不存在: {args.book_file}", 4)
        if not os.path.isfile(args.book_file):
            handle_error(f"不是有效的文件: {args.book_file}", 5)
        
        # 检查书籍是否在书架中，如果不在则添加到数据库
        try:
            from src.core.bookshelf import Bookshelf
            from src.core.database_manager import DatabaseManager
            
            # 创建书架实例
            bookshelf = Bookshelf()
            
            # 检查书籍是否已存在
            abs_path = os.path.abspath(args.book_file)
            existing_book = bookshelf.get_book(abs_path)
            
            if not existing_book:
                # 书籍不存在，添加到数据库
                book = bookshelf.add_book(abs_path)
                if not book:
                    print(f"添加书籍到书架失败: {abs_path}")
            # else:
            #     print(f"书籍已在书架中: {existing_book.title}")
                
        except Exception as e:
            print(f"检查书籍状态时出错: {e}")
    
    # 创建配置管理器
    config_manager = ConfigManager(args.config)
    
    # 如果命令行指定了debug，覆盖配置
    if args.debug:
        config = config_manager.get_config()
        config["advanced"] = config.get("advanced", {})
        config["advanced"]["debug_mode"] = True
        config_manager.save_config(config)

    # 设置日志
    try:
        setup_logging_from_config(config_manager)
        
        # 如果命令行指定了debug，覆盖配置
        if args.debug:
            from src.utils.logger import set_debug_mode
            set_debug_mode(True)
            print("调试模式已启用")
            
    except Exception as e:
        handle_error(f"日志初始化失败: {e}", 1)
        
    if args.web:
        # 使用 textual-serve 启动 Web 模式
        import os, asyncio, socket
        # Python 3.14 不会为主线程默认创建事件循环，这里显式创建以兼容 textual-serve
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        # 端口检测与自动顺延
        host = args.host or "localhost"
        start_port = int(args.port or 8000)
        port = start_port

        def _is_busy(h: str, p: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.settimeout(0.2)
                    return s.connect_ex((h, p)) == 0
            except Exception:
                # 如果检测异常，保守认为被占用，避免冲突
                return True

        tries = 10
        while _is_busy(host, port) and tries > 0:
            print(f"Port on used: {port}，Try next port: {port + 1}")
            port += 1
            tries -= 1

        if _is_busy(host, port):
            handle_error(f"No port to use（From {start_port} to last 10 ports were all on used）", 6)
            return

        main_file = os.path.dirname(__file__)
        # 使用当前解释器，避免不同 Python 版本导致问题
        python_cmd = f'"{sys.executable}"' if getattr(sys, "executable", None) else "python"
        server = Server(f'{python_cmd} {main_file}/main.py "$@"', host=host, port=port, title="NewReader")
        server.serve()
        return

    # 创建并运行应用程序
    try:
        # 创建应用实例
        app = NewReaderApp(config_manager, args.book_file)
        
        # 应用内部已经集成了多用户设置检查逻辑
        # 在NewReaderApp的on_mount方法中会自动处理登录流程
        app.run()
    except ImportError as e:
        handle_error(f"缺少依赖: {e}\n请运行: pip install -r requirements.txt", 2)
    except PermissionError as e:
        handle_error(f"文件权限问题: {e}\n请检查文件和目录权限", 3)
    except Exception as e:
        handle_error(f"未处理的异常: {e}\n{traceback.format_exc()}", 99)

if __name__ == "__main__":
    main()