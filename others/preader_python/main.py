import curses
import sys
import os
from bookshelf import Bookshelf
from settings import Settings
from reader import NovelReader

def main(stdscr):
    curses.curs_set(0)
    settings = Settings()
    bookshelf = Bookshelf()
    reader = NovelReader(stdscr, bookshelf, settings)

    # 支持命令行直接打开文件
    if len(sys.argv) > 1:
        novel_path = sys.argv[1]
        if not os.path.isfile(novel_path):
            stdscr.addstr(0, 0, f"文件不存在: {novel_path}")
            stdscr.refresh()
            stdscr.getch()
            return
        bookshelf.add_book(novel_path, width=settings["width"], height=settings["height"], line_spacing=settings["line_spacing"])
        if bookshelf.books:
            reader.load_book(bookshelf.books[-1])
        else:
            stdscr.addstr(0, 0, f"无法加载小说: {novel_path}")
            stdscr.refresh()
            stdscr.getch()
            return
    # 进入主循环
    reader.run()

if __name__ == '__main__':
    curses.wrapper(main)