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
        bookshelf.add_book(novel_path, width=settings["width"], height=settings["height"], line_spacing=settings["line_spacing"])
        if bookshelf.books:
            reader.load_book(bookshelf.books[-1])
        else:
            stdscr.addstr(0, 0, f"{get_text('cannot_load_novel', settings['lang'])}: {novel_path}")
            stdscr.refresh()
            stdscr.getch()
            return
    # 进入主循环
    reader.run()

if __name__ == '__main__':
    curses.wrapper(main)