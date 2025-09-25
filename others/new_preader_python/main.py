"""
NewReader 主程序入口
"""

import argparse
import logging
import sys
import traceback
from typing import NoReturn

def handle_error(message: str, exit_code: int = 1) -> NoReturn:
    """处理致命错误并退出"""
    logging.error(message)
    print(f"错误: {message}", file=sys.stderr)
    sys.exit(exit_code)

from src.ui.app import NewReaderApp
from src.utils.logger import setup_logging_from_config
from src.config.config_manager import ConfigManager

def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="NewReader - 现代化终端小说阅读器")
    parser.add_argument("--config", help="指定配置文件路径")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
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
        config["app.debug"] = True
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
    
    # 创建并运行应用程序
    try:
        app = NewReaderApp(config_manager, args.book_file)
        app.run()
    except ImportError as e:
        handle_error(f"缺少依赖: {e}\n请运行: pip install -r requirements.txt", 2)
    except PermissionError as e:
        handle_error(f"文件权限问题: {e}\n请检查文件和目录权限", 3)
    except Exception as e:
        handle_error(f"未处理的异常: {e}\n{traceback.format_exc()}", 99)

if __name__ == "__main__":
    main()