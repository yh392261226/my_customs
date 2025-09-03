import curses
import sys
import os
import signal  # 添加signal导入
from bookshelf import Bookshelf
from settings import Settings
from lang import get_text
from reader import NovelReader

def signal_handler(sig, frame):
    # 清理工作
    sys.exit(0)

def main(stdscr):
    # 初始化 curses
    curses.curs_set(0)  # 隐藏光标
    curses.start_color()  # 启用颜色支持
    curses.use_default_colors()  # 使用默认颜色
    stdscr.keypad(True)  # 启用特殊键
    stdscr.nodelay(0)  # 阻塞模式
    
    # 启用滚动（如果需要）
    stdscr.scrollok(True)
    stdscr.idlok(True)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    settings = Settings()
    bookshelf = Bookshelf(settings["lang"])
    reader = NovelReader(stdscr, bookshelf, settings)

    # 支持命令行直接打开文件
    if len(sys.argv) > 1:
        novel_path = sys.argv[1]
        if not os.path.isfile(novel_path):
            stdscr.addstr(0, 0, f"{get_text('file_not_exists', settings['lang'])}: {novel_path}")
            stdscr.refresh()
            stdscr.getch()
            return
            
        # 添加书籍到书架
        bookshelf.add_book(novel_path, width=settings["width"], height=settings["height"], line_spacing=settings["line_spacing"])
        
        # 尝试加载最后添加的书籍
        if bookshelf.books:
            # 获取最后添加的书籍
            book_to_load = bookshelf.books[-1]
            
            # 检查是否是加密PDF
            if book_to_load["type"] == "pdf" and "加密PDF" in book_to_load.get("author", ""):
                # 这是加密PDF，显示提示信息
                stdscr.addstr(0, 0, f"{get_text('pdf_encrypted_prompt', settings['lang'])}: {novel_path}")
                stdscr.refresh()
                stdscr.getch()
                # 不自动加载加密PDF，让用户从书架中选择并输入密码
            else:
                # 正常加载书籍
                reader.load_book(book_to_load)
        else:
            stdscr.addstr(0, 0, f"{get_text('cannot_load_novel', settings['lang'])}: {novel_path}")
            stdscr.refresh()
            stdscr.getch()
            return
    # 进入主循环
    reader.run()

if __name__ == '__main__':
    curses.wrapper(main)