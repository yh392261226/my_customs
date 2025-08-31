import subprocess
import shlex
import tempfile
import os
import curses
import time
import pyttsx3
import threading
from utils import build_pages_from_file
from db import DBManager
from stats import StatsManager
from ui_theme import init_colors, BORDER_CHARS, color_pair_idx
from lang import get_text
from epub_utils import parse_epub

KEYS_HELP = [
    "←/→/PgUp/PgDn/j/k 翻页",
    "a 自动翻页",
    "b 添加书签",
    "B 书签列表",
    "g 跳页",
    "m 书架",
    "s 设置",
    "r 朗读/停止",
    "/ 搜索",
    "? 帮助",
    "q 退出",
    "t 阅读统计",
    "T 全部统计"
]

def input_box(stdscr, prompt, maxlen=50, color_pair=2, y=None, x=None):
    """美化输入框，居中显示"""
    max_y, max_x = stdscr.getmaxyx()
    if y is None:
        y = max_y // 2 - 1
    if x is None:
        x = max_x // 2 - len(prompt) // 2 - 8
    box_width = max(len(prompt) + maxlen + 8, 30)
    stdscr.attron(curses.color_pair(color_pair) | curses.A_BOLD)
    # 边框
    stdscr.addstr(y, x, "╭" + "─" * (box_width-2) + "╮")
    stdscr.addstr(y+1, x, "│" + " " * (box_width-2) + "│")
    stdscr.addstr(y+2, x, "╰" + "─" * (box_width-2) + "╯")
    # 提示
    stdscr.addstr(y+1, x+2, prompt)
    stdscr.attroff(curses.color_pair(color_pair) | curses.A_BOLD)
    stdscr.refresh()
    curses.echo()
    val = stdscr.getstr(y+1, x+2+len(prompt), maxlen).decode().strip()
    curses.noecho()
    return val

class NovelReader:
    def __init__(self, stdscr, bookshelf, settings):
        self.stdscr = stdscr
        self.bookshelf = bookshelf
        self.settings = settings
        self.db = DBManager()
        self.stats = StatsManager()
        self.engine = pyttsx3.init()
        self.current_book = None
        self.current_pages = []
        self.current_page_idx = 0
        self.start_time = time.time()
        self.auto_page = False
        self.search_keyword = ""
        self.highlight_lines = set()
        self.running = True
        self.lang = self.settings["lang"]
        self.last_remind_time = time.time()
        self.remind_minutes = self.settings["remind_interval"]
        self.is_reading = False  # 添加朗读状态标志
        self.reading_thread = None  # 添加朗读线程
        self.boss_mode = False  # 老板键模式标志
        self.terminal_history = []  # 终端命令历史
        self.terminal_position = 0  # 终端历史位置
        init_colors(theme=self.settings["theme"], settings=self.settings)

    def get_safe_height(self):
        """计算安全的显示高度，考虑边框和边距"""
        max_y, _ = self.stdscr.getmaxyx()
        margin = self.settings["margin"]
        # 预留顶部/底部/状态栏空间（9行）
        return max(1, min(self.settings["height"], max_y - margin - 9))

    def show_loading_screen(self, message, progress=None):
        """显示美观的加载屏幕，支持进度显示"""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 绘制边框
        self.draw_border()
        
        # 显示标题
        title = "📖 小说阅读器 - 加载中"
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(2, max_x // 2 - len(title) // 2, title)
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        # 显示消息
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(max_y // 2 - 2, max_x // 2 - len(message) // 2, message)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
        # 显示动态旋转图标
        spinner_chars = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        spinner = spinner_chars[int(time.time() * 8) % len(spinner_chars)]
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(max_y // 2, max_x // 2 - 1, spinner)
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # 显示进度条（如果有进度信息）
        if progress is not None:
            # 解析进度信息
            if "/" in progress:
                current, total = progress.split("/")
                try:
                    current_val = int(current)
                    total_val = int(total)
                    percent = current_val / total_val if total_val > 0 else 0
                    
                    # 绘制进度条
                    bar_width = min(40, max_x - 10)
                    filled = int(bar_width * percent)
                    bar = "[" + "█" * filled + "░" * (bar_width - filled) + "]"
                    bar_text = f"{bar} {int(percent*100)}%"
                    
                    self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    self.stdscr.addstr(max_y // 2 + 2, max_x // 2 - len(bar_text) // 2, bar_text)
                    self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                    
                    # 显示详细进度
                    detail_text = f"{current_val}/{total_val}"
                    self.stdscr.attron(curses.color_pair(3))
                    self.stdscr.addstr(max_y // 2 + 4, max_x // 2 - len(detail_text) // 2, detail_text)
                    self.stdscr.attroff(curses.color_pair(3))
                except:
                    pass
        
        # 显示提示信息
        tip = "请稍候，正在努力加载..."
        self.stdscr.attron(curses.color_pair(1) | curses.A_DIM)
        self.stdscr.addstr(max_y - 3, max_x // 2 - len(tip) // 2, tip)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_DIM)
        
        self.stdscr.refresh()

    def load_book(self, book):
        # 使用设置的宽度，而不是有效宽度
        width = self.settings["width"]
        height = self.get_safe_height()
        line_spacing = self.settings["line_spacing"]
        
        # 显示加载屏幕
        self.show_loading_screen("初始化书籍加载")
        time.sleep(0.5)  # 短暂延迟让用户看到初始画面
        
        # 进度回调函数
        def progress_callback(message):
            # 解析消息中的进度信息
            progress = None
            if ":" in message and "/" in message:
                parts = message.split(":")
                if len(parts) > 1 and "/" in parts[1]:
                    progress = parts[1].strip()
            
            self.show_loading_screen(message, progress)
        
        if book["type"] == "epub":
            self.show_loading_screen("解析EPUB文件结构")
            chapters = parse_epub(book["path"], width, height, line_spacing)
            
            pages = []
            total_chapters = len(chapters)
            for i, ch in enumerate(chapters):
                # 添加章节标题页
                pages.append([f"《{ch['title']}》"])
                # 添加章节内容页
                pages.extend(ch["pages"])
                
                # 每处理一章更新一次显示
                if i % 2 == 0:  # 每两章更新一次，避免过于频繁
                    self.show_loading_screen(f"处理章节内容: {i+1}/{total_chapters}")
            
            self.current_pages = pages
            self.show_loading_screen("EPUB处理完成")
            time.sleep(0.5)
        else:
            # 使用新版 utils.build_pages_from_file，确保不丢失任何内容
            self.current_pages = build_pages_from_file(
                book["path"], width, height, line_spacing, progress_callback
            )
            self.show_loading_screen("文本处理完成")
            time.sleep(0.5)
        # 在解析完成后检查是否为空
        if not self.current_pages:
            self.current_pages = [["空文件或文件内容为空"]]
        

        self.current_book = book
        self.current_page_idx = self.db.get_progress(book["id"])
        self.highlight_lines = set()

    def show_bookshelf(self):
        books_per_page = max(1, self.get_safe_height() - 8)
        page = 0
        search_keyword = ""
        # 修改排序方式为按标题升序
        filtered_books = sorted(self.bookshelf.books, key=lambda x: x["title"].lower())
        book_selected = False
        
        while not book_selected and self.running:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            total_books = len(filtered_books)
            total_pages = (total_books + books_per_page - 1) // books_per_page if total_books else 1
            start_idx = page * books_per_page
            end_idx = min(start_idx + books_per_page, total_books)
            title_str = "📚 " + get_text("bookshelf", self.lang) + f" [{page+1}/{total_pages}]"
            if search_keyword:
                title_str += f" | 搜索: {search_keyword}"
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title_str) // 2, title_str)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            for idx, book in enumerate(filtered_books[start_idx:end_idx]):
                line = f" {start_idx+idx+1:02d} | {book['title'][:30]:<30} | {get_text('author', self.lang)}:{book['author'][:15]:<15} | 标签:{book['tags']}"
                color = curses.color_pair(2) if idx % 2 else curses.color_pair(1)
                self.stdscr.attron(color | curses.A_BOLD)
                self.stdscr.addstr(idx+2, 2, line[:max_x-3])
                self.stdscr.attroff(color | curses.A_BOLD)
                
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(books_per_page+3, 2,
                f"[a] {get_text('add_book', self.lang)}  [d] {get_text('add_dir', self.lang)}  [n]下一页  [p]上一页  [/]搜索书名  [q]{get_text('exit', self.lang)}")
            self.stdscr.addstr(books_per_page+5, 2, "输入小说序号并回车可选书")
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('a'):
                path = input_box(self.stdscr, get_text("input_path", self.lang), maxlen=120)
                if path:
                    self.bookshelf.add_book(path, width=self.settings["width"], height=self.settings["height"], line_spacing=self.settings["line_spacing"])
                    filtered_books = self.bookshelf.books if not search_keyword else self.bookshelf.search_books(search_keyword)
            elif c == ord('d'):
                dir_path = input_box(self.stdscr, get_text("input_dir", self.lang), maxlen=120)
                if dir_path:
                    self.bookshelf.add_dir(dir_path, width=self.settings["width"], height=self.settings["height"], line_spacing=self.settings["line_spacing"])
                    filtered_books = self.bookshelf.books if not search_keyword else self.bookshelf.search_books(search_keyword)
            elif c == ord('/'):
                kw = input_box(self.stdscr, "请输入书名关键词：", maxlen=30)
                search_keyword = kw
                page = 0
                filtered_books = self.bookshelf.search_books(search_keyword) if search_keyword else self.bookshelf.books
            elif c == ord('q'):
                self.running = False
                break
            elif c == ord('n') and page < total_pages - 1:
                page += 1
            elif c == ord('p') and page > 0:
                page -= 1
            elif c in [10, 13]:  # 回车键
                idx_str = input_box(self.stdscr, "序号: ", maxlen=8)
                try:
                    idx = int(idx_str) - 1
                    if 0 <= idx < total_books:
                        self.load_book(filtered_books[idx])
                        book_selected = True
                    else:
                        self.stdscr.addstr(books_per_page+9, 2, "序号超范围！")
                        self.stdscr.refresh()
                        time.sleep(1)
                except:
                    self.stdscr.addstr(books_per_page+9, 2, "输入无效！")
                    self.stdscr.refresh()
                    time.sleep(1)

    def draw_border(self):
        style = self.settings["border_style"]
        color = self.settings["border_color"]
        max_y, max_x = self.stdscr.getmaxyx()
        v, h, c = BORDER_CHARS.get(style, BORDER_CHARS["round"])
        border_color_pair = color_pair_idx(10, color, self.settings["bg_color"])
        if style != "none":
            for i in range(1, max_y-2):
                self.stdscr.attron(border_color_pair)
                self.stdscr.addstr(i, 0, v)
                self.stdscr.addstr(i, max_x-2, v)
                self.stdscr.attroff(border_color_pair)
            for i in range(1, max_x-2):
                self.stdscr.attron(border_color_pair)
                self.stdscr.addstr(0, i, h)
                self.stdscr.addstr(max_y-2, i, h)
                self.stdscr.attroff(border_color_pair)
            self.stdscr.attron(border_color_pair)
            self.stdscr.addstr(0, 0, c)
            self.stdscr.addstr(0, max_x-2, c)
            self.stdscr.addstr(max_y-2, 0, c)
            self.stdscr.addstr(max_y-2, max_x-2, c)
            self.stdscr.attroff(border_color_pair)

    def display(self):
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        margin = self.settings["margin"]
        padding = self.settings["padding"]
        height = self.get_safe_height()
        self.draw_border()

        # 添加对空页面的检查
        if not self.current_pages:
            empty_msg = "文件为空或无法解析内容"
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(margin + height // 2, max_x // 2 - len(empty_msg) // 2, empty_msg)
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.refresh()
            return
        
        page_lines = self.current_pages[self.current_page_idx] if self.current_pages else []
        if self.current_pages and self.current_book:
            progress = int((self.current_page_idx+1)/len(self.current_pages)*100)
            bar_len = int(progress / 5)
            
            title_str = f"《{self.current_book['title']}》阅读进度:[{'█'*bar_len}{'-'*(20-bar_len)}] {progress:3d}%"
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(margin, max_x // 2 - len(title_str)//2, title_str[:max_x-4])
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
        for idx, line in enumerate(page_lines[:height]):
            y = idx + margin + 2
            x = padding + 2
            if y >= max_y - 7:
                break
            safe_line = line.replace('\r', '').replace('\n', '').replace('\t', ' ')
            # 显示时截断到屏幕宽度
            safe_line = safe_line[:max_x - x - 3] if len(safe_line) > (max_x - x - 3) else safe_line
            try:
                if safe_line.startswith("《") and safe_line.endswith("》"):
                    self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    self.stdscr.addstr(y, x, safe_line.center(self.settings["width"])[:max_x - x - 3])
                    self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                elif idx in self.highlight_lines:
                    self.stdscr.attron(curses.color_pair(2) | curses.A_REVERSE)
                    self.stdscr.addstr(y, x, safe_line)
                    self.stdscr.attroff(curses.color_pair(2) | curses.A_REVERSE)
                else:
                    self.stdscr.attron(curses.color_pair(1))
                    self.stdscr.addstr(y, x, safe_line)
                    self.stdscr.attroff(curses.color_pair(1))
            except curses.error:
                pass
                
        if self.current_pages:
            bar = f""
            self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(margin+height+1, 2, bar[:max_x-4])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
            
        if self.settings["status_bar"] and self.current_book:
            status = f"📖 {self.current_book['title']} | {get_text('author', self.lang)}: {self.current_book['author']} | {get_text('current_page', self.lang)}: {self.current_page_idx+1}/{len(self.current_pages)}"
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(margin+height+2, 2, status[:max_x-4])
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
        # 显示朗读状态
        if self.is_reading:
            reading_status = "🔊 朗读中 - 按r停止"
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(margin+height+3, 2, reading_status[:max_x-4])
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            
        help_str = " | ".join(KEYS_HELP)
        self.stdscr.attron(curses.color_pair(2) | curses.A_DIM)
        self.stdscr.addstr(margin+height+4, 2, help_str[:max_x-4])
        self.stdscr.attroff(curses.color_pair(2) | curses.A_DIM)
        self.stdscr.refresh()

    def handle_input(self):
        c = self.stdscr.getch()
        if self.boss_mode:
            # 老板模式关闭自动翻页、朗读
            if self.is_reading:
                self.stop_reading()
            if self.is_reading:
                self.stop_reading()

            # 在老板键模式下处理输入
            self.handle_terminal_input(c)
            return

        if c == ord(' '):  # 空格键 - 老板键
            self.toggle_boss_mode()
        elif c in (curses.KEY_RIGHT, curses.KEY_NPAGE, ord('j')):
            if self.is_reading:
                self.stop_reading()
            self.next_page()
        elif c in (curses.KEY_LEFT, curses.KEY_PPAGE, ord('k')):
            if self.is_reading:
                self.stop_reading()
            self.prev_page()
        elif c == ord('a'):
            if self.is_reading:
                self.stop_reading()
            self.auto_page = not self.auto_page
        elif c == ord('b'):
            if self.is_reading:
                self.stop_reading()
            self.add_bookmark()
        elif c == ord('B'):
            if self.is_reading:
                self.stop_reading()
            self.show_bookmarks()
        elif c == ord('m'):
            if self.is_reading:
                self.stop_reading()
            self.show_bookshelf()
        elif c == ord('q'):
            self.running = False
        elif c == ord('r'):
            self.toggle_reading()  # 修改为切换朗读状态
        elif c == ord('/'):
            if self.is_reading:
                self.stop_reading()
            self.search()
        elif c == ord('s'):
            if self.is_reading:
                self.stop_reading()
            self.change_settings()
        elif c == ord('?'):
            if self.is_reading:
                self.stop_reading()
            self.show_help()
        elif c == ord('g'):
            if self.is_reading:
                self.stop_reading()
            self.jump_page()
        elif c == ord('t'):
            if self.is_reading:
                self.stop_reading()
            self.show_stats()
        elif c == ord('T'):
            if self.is_reading:
                self.stop_reading()
            self.show_all_books_stats()

    def next_page(self):
        if self.current_page_idx < len(self.current_pages)-1:
            self.current_page_idx += 1

    def prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1

    def save_progress(self):
        if self.current_book:
            self.db.save_progress(self.current_book["id"], self.current_page_idx)

    def show_bookmarks(self):
        bookmarks = self.db.get_bookmarks(self.current_book["id"])
        max_y, max_x = self.stdscr.getmaxyx()
        self.stdscr.clear()
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(0, max_x // 2 - 5, get_text("bookmark_list", self.lang))
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        for i, (page, comment) in enumerate(bookmarks[:max_y-8]):
            self.stdscr.addstr(i+2, 4, f"{i+1:02d}. 第{page+1}页: {comment}"[:max_x-8])
        self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
        self.stdscr.addstr(max_y-4, 4, "输入书签序号并回车跳转，q退出")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
        self.stdscr.refresh()
        c = self.stdscr.getch()
        if c == ord('q'):
            return
        elif c in [10, 13]:
            idx_str = input_box(self.stdscr, "序号: ", maxlen=8)
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(bookmarks):
                    self.current_page_idx = bookmarks[idx][0]
                else:
                    self.stdscr.addstr(max_y-2, 4, "序号超范围！")
                    self.stdscr.refresh()
                    time.sleep(1)
            except:
                self.stdscr.addstr(max_y-2, 4, "输入无效！")
                self.stdscr.refresh()
                time.sleep(1)

    def jump_page(self):
        max_y, max_x = self.stdscr.getmaxyx()
        page_str = input_box(self.stdscr, get_text("input_jump_page", self.lang), maxlen=10)
        try:
            page_num = int(page_str)
            if 1 <= page_num <= len(self.current_pages):
                self.current_page_idx = page_num - 1
            else:
                self.stdscr.addstr(max_y-3, 2, get_text("invalid", self.lang))
                self.stdscr.refresh()
                time.sleep(1)
        except:
            self.stdscr.addstr(max_y-3, 2, get_text("invalid", self.lang))
            self.stdscr.refresh()
            time.sleep(1)

    def add_bookmark(self):
        comment = input_box(self.stdscr, get_text("input_comment", self.lang), maxlen=100)
        if comment:
            self.db.add_bookmark(self.current_book["id"], self.current_page_idx, comment)

    def toggle_reading(self):
        """切换朗读状态"""
        if self.is_reading:
            self.stop_reading()
        else:
            self.start_reading()

    def start_reading(self):
        """开始朗读"""
        if self.is_reading:
            return
            
        # 开始朗读
        self.is_reading = True
        txt = "\n".join(self.current_pages[self.current_page_idx])
        
        # 使用线程来运行朗读，避免阻塞主线程
        def run_reading():
            try:
                self.engine.say(txt)
                self.engine.runAndWait()
            except Exception as e:
                # 忽略所有异常，特别是KeyboardInterrupt
                pass
            finally:
                self.is_reading = False
                
        self.reading_thread = threading.Thread(target=run_reading)
        self.reading_thread.daemon = True
        self.reading_thread.start()

    def stop_reading(self):
        """停止朗读"""
        if self.is_reading:
            try:
                self.engine.stop()
                # 等待一小段时间让引擎停止
                time.sleep(0.1)
                self.is_reading = False
            except Exception:
                self.is_reading = False

    def search(self):
        kw = input_box(self.stdscr, get_text("input_search", self.lang), maxlen=50)
        if kw:
            self.search_keyword = kw
            self.highlight_lines = set()
            page_lines = self.current_pages[self.current_page_idx]
            for idx, line in enumerate(page_lines):
                if kw in line:
                    self.highlight_lines.add(idx)

    def check_remind(self):
        remind_interval = self.settings["remind_interval"]
        if remind_interval and remind_interval > 0:
            now = time.time()
            elapsed = now - self.last_remind_time
            if elapsed > remind_interval * 60:
                self.show_remind(int(elapsed // 60))
                self.last_remind_time = now

    def show_remind(self, minutes):
        max_y, max_x = self.stdscr.getmaxyx()
        msg = get_text("remind_msg", self.lang).format(minutes=minutes)
        box_top = max_y // 2 - 3
        box_left = max_x // 2 - len(msg) // 2 - 2
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(box_top, box_left, "╭" + "─" * (len(msg)+2) + "╮")
        self.stdscr.addstr(box_top+1, box_left, "│" + msg + " │")
        self.stdscr.addstr(box_top+2, box_left, "╰" + "─" * (len(msg)+2) + "╯")
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.refresh()
        time.sleep(3)

    def change_settings(self):
        options = [
            ("width", "宽度", int, 40, 300),
            ("height", "高度", int, 10, 80),
            ("theme", get_text("input_theme", self.lang), str, ["dark", "light", "eye"]),
            ("lang", get_text("input_lang", self.lang), str, ["zh", "en"]),
            ("font_color", get_text("input_font_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("bg_color", get_text("input_bg_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("border_style", get_text("input_border_style", self.lang), str, ["round","double","single","bold","none"]),
            ("border_color", get_text("input_border_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("line_spacing", "行距", int, 1, 5),
            ("auto_page_interval", "自动翻页秒", int, 1, 60),
            ("status_bar", "状态栏显示", bool, [0, 1]),
            ("remind_interval", get_text("input_remind_interval", self.lang), int, 0, 120),
        ]
        curr = 0
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - 6, "⚙️ 设置界面")
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            for idx, (key, desc, typ, *meta) in enumerate(options):
                val = self.settings[key]
                line = f"{desc} [{val}]"
                if idx == curr:
                    self.stdscr.attron(curses.color_pair(2) | curses.A_REVERSE)
                    self.stdscr.addstr(idx+2, 4, line[:max_x-8])
                    self.stdscr.attroff(curses.color_pair(2) | curses.A_REVERSE)
                else:
                    self.stdscr.addstr(idx+2, 4, line[:max_x-8])
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(len(options)+4, 4, "回车修改，q返回")
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c in (curses.KEY_DOWN, ord('j')):
                curr = (curr + 1) % len(options)
            elif c in (curses.KEY_UP, ord('k')):
                curr = (curr - 1) % len(options)
            elif c == ord('q'):
                init_colors(theme=self.settings["theme"], settings=self.settings)
                self.lang = self.settings["lang"]
                self.remind_minutes = self.settings["remind_interval"]
                # 重新加载当前书籍以适应新设置
                if self.current_book:
                    self.load_book(self.current_book)
                break
            elif c in (curses.KEY_ENTER, 10, 13):
                key, desc, typ, *meta = options[curr]
                newval = input_box(self.stdscr, f"{desc}新值: ", maxlen=20)
                valid = False
                if typ == int:
                    try:
                        v = int(newval)
                        if len(meta)==2 and (meta[0] <= v <= meta[1]):
                            self.settings[key] = v
                            valid = True
                    except:
                        pass
                elif typ == bool:
                    if newval.lower() in ['1', 'true', 'yes', 'y', '开', '是']:
                        self.settings[key] = True
                        valid = True
                    elif newval.lower() in ['0', 'false', 'no', 'n', '关', '否']:
                        self.settings[key] = False
                        valid = True
                elif typ == str:
                    if isinstance(meta[0], list) and newval in meta[0]:
                        self.settings[key] = newval
                        valid = True
                if not valid:
                    self.stdscr.addstr(len(options)+7, 4, get_text("invalid", self.lang))
                    self.stdscr.refresh()
                    time.sleep(1)
                else:
                    self.settings.save()
                    if key in ["theme","font_color","bg_color","border_style","border_color"]:
                        init_colors(theme=self.settings["theme"], settings=self.settings)
                    if key == "lang":
                        self.lang = self.settings["lang"]
                    if key == "remind_interval":
                        self.remind_minutes = self.settings["remind_interval"]
                    # 重新加载当前书籍以适应新设置
                    if self.current_book and key in ["width", "height", "line_spacing"]:
                        self.load_book(self.current_book)

    def show_help(self):
        max_y, max_x = self.stdscr.getmaxyx()
        self.stdscr.clear()
        
        # 绘制边框
        self.draw_border()
        
        # 标题
        title = "💡 帮助中心"
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(2, max_x // 2 - len(title) // 2, title)
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        # 分隔线
        sep_line = "─" * (max_x - 6)
        self.stdscr.attron(curses.color_pair(10))
        self.stdscr.addstr(4, 3, sep_line)
        self.stdscr.attroff(curses.color_pair(10))
        
        # 分类显示帮助信息
        categories = [
            {
                "title": "📖 阅读控制",
                "items": [
                    ("←/→/PgUp/PgDn/j/k", "翻页"),
                    ("a", "自动翻页"),
                    ("g", "跳转到指定页"),
                    ("/", "搜索文本")
                ]
            },
            {
                "title": "🔖 书签功能",
                "items": [
                    ("b", "添加书签"),
                    ("B", "查看书签列表")
                ]
            },
            {
                "title": "🎵 朗读功能",
                "items": [
                    ("r", "开始/停止朗读")
                ]
            },
            {
                "title": "📚 书籍管理",
                "items": [
                    ("m", "返回书架"),
                    ("s", "设置选项")
                ]
            },
            {
                "title": "📊 统计信息",
                "items": [
                    ("t", "本书阅读统计"),
                    ("T", "全部书籍统计")
                ]
            },
            {
                "title": "👔 老板键功能",
                "items": [
                    ("空格键", "隐藏/显示阅读器"),
                    ("空格+回车", "从终端返回阅读器"),
                    ("↑↓", "浏览命令历史")
                ]
            },
            {
                "title": "⚙️ 系统操作",
                "items": [
                    ("?", "显示帮助"),
                    ("q", "退出程序")
                ]
            }
        ]
        
        y_pos = 6
        for category in categories:
            # 显示分类标题
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(y_pos, 5, category["title"])
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            
            y_pos += 1
            
            # 显示分类中的项目
            for key, desc in category["items"]:
                key_part = f"[{key}]"
                desc_part = f" {desc}"
                
                self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
                self.stdscr.addstr(y_pos, 7, key_part)
                self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
                
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y_pos, 7 + len(key_part), desc_part)
                self.stdscr.attroff(curses.color_pair(1))
                
                y_pos += 1
            
            y_pos += 1  # 分类之间的间隔
        
        # 底部提示
        tip = "按任意键返回阅读界面"
        self.stdscr.attron(curses.color_pair(1) | curses.A_DIM)
        self.stdscr.addstr(max_y - 3, max_x // 2 - len(tip) // 2, tip)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_DIM)
        
        # 装饰性边框
        self.stdscr.attron(curses.color_pair(10))
        self.stdscr.addstr(max_y - 5, 3, sep_line)
        self.stdscr.attroff(curses.color_pair(10))
        
        self.stdscr.refresh()
        self.stdscr.getch()

    def show_stats(self):
        stats = self.stats.get_book_stats(self.current_book["id"])
        max_y, max_x = self.stdscr.getmaxyx()
        self.stdscr.clear()
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(0, max_x // 2 - 6, "📊 阅读统计")
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(2, 4, f"小说：{self.current_book['title']}")
        self.stdscr.addstr(3, 4, f"累计阅读时间：{stats['total_time']//60} 分钟")
        self.stdscr.addstr(4, 4, f"阅读天数：{stats['days']} 天")
        self.stdscr.addstr(6, 4, f"每日统计：")
        for idx, (date, sec) in enumerate(stats["records"][:max_y-12]):
            self.stdscr.addstr(7+idx, 6, f"{date}: {sec//60} 分钟")
        self.stdscr.addstr(max_y-2, 4, "任意键返回")
        self.stdscr.refresh()
        self.stdscr.getch()

    def show_all_books_stats(self):
        all_stats = self.stats.get_all_books_stats()
        # 修改排序方式为按标题升序
        books = sorted(self.bookshelf.books, key=lambda x: x["title"].lower())
        max_y, max_x = self.stdscr.getmaxyx()
        stats_per_page = max(1, max_y - 7)
        page = 0
        total_books = len(books)
        total_pages = (total_books + stats_per_page - 1) // stats_per_page if total_books else 1
        while True:
            self.stdscr.clear()
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - 7, "📚 全部书籍阅读统计")
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            start_idx = page * stats_per_page
            end_idx = min(start_idx + stats_per_page, total_books)
            y = 2
            for book in books[start_idx:end_idx]:
                book_id = book["id"]
                stat = all_stats.get(book_id, {"total_time":0, "days":0})
                line = f"{book['title'][:20]:<20} | {stat['total_time']//60:>4} 分钟 | {stat['days']} 天"
                self.stdscr.addstr(y, 4, line[:max_x-8])
                y += 1
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            page_info = f"第{page+1}/{total_pages}页 [n]下一页 [p]上一页 [q]返回"
            self.stdscr.addstr(max_y-3, 4, page_info[:max_x-8])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c == ord('n') and page < total_pages - 1:
                page += 1
            elif c == ord('p') and page > 0:
                page -= 1

    def toggle_boss_mode(self):
        """切换老板键模式"""
        self.boss_mode = not self.boss_mode
        if self.boss_mode:
            # 进入老板键模式
            self.terminal_input = ""
            self.terminal_output = ["终端模拟器已启动", "输入命令或按空格+回车返回", "----------------------------------------"]
            self.terminal_cursor = 0
        else:
            # 退出老板键模式
            self.terminal_history = []
            self.terminal_position = 0

    def handle_terminal_input(self, c):
        """处理终端模式下的输入"""
        if c == curses.KEY_ENTER or c == 10 or c == 13:  # 回车键
            self.execute_terminal_command()
        elif c == curses.KEY_BACKSPACE or c == 127:  # 退格键
            if self.terminal_input:
                self.terminal_input = self.terminal_input[:-1]
        elif c == curses.KEY_UP:  # 上箭头 - 历史命令
            if self.terminal_history and self.terminal_position > 0:
                self.terminal_position -= 1
                self.terminal_input = self.terminal_history[self.terminal_position]
        elif c == curses.KEY_DOWN:  # 下箭头 - 历史命令
            if self.terminal_history and self.terminal_position < len(self.terminal_history) - 1:
                self.terminal_position += 1
                self.terminal_input = self.terminal_history[self.terminal_position]
            elif self.terminal_position == len(self.terminal_history) - 1:
                self.terminal_position = len(self.terminal_history)
                self.terminal_input = ""
        elif 32 <= c <= 126:  # 可打印字符
            self.terminal_input += chr(c)
            
        self.display_terminal()

    def execute_terminal_command(self):
        """执行终端命令"""
        command = self.terminal_input.strip()
        
        # 如果命令为空或只有空格，则退出老板键模式
        if not command or command.isspace():
            self.toggle_boss_mode()
            return
            
        # 将命令添加到历史
        if not self.terminal_history or self.terminal_history[-1] != command:
            self.terminal_history.append(command)
        self.terminal_position = len(self.terminal_history)
        
        # 执行命令
        try:
            if command.lower() in ['exit', 'quit']:
                self.terminal_output.append(f"$ {command}")
                self.terminal_output.append("使用空格+回车退出终端模式")
            else:
                self.terminal_output.append(f"$ {command}")
                
                # 使用subprocess执行命令
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                
                if result.stdout:
                    self.terminal_output.extend(result.stdout.splitlines())
                if result.stderr:
                    self.terminal_output.extend(result.stderr.splitlines())
                if result.returncode != 0:
                    self.terminal_output.append(f"命令退出代码: {result.returncode}")
                    
        except subprocess.TimeoutExpired:
            self.terminal_output.append("命令执行超时")
        except Exception as e:
            self.terminal_output.append(f"执行错误: {str(e)}")
        
        # 限制输出行数
        if len(self.terminal_output) > 100:
            self.terminal_output = self.terminal_output[-100:]
        
        self.terminal_input = ""
        self.display_terminal()

    def display_terminal(self):
        """显示终端界面"""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 显示终端标题
        title = "💻 终端模式"
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        # 显示分隔线
        sep_line = "─" * (max_x - 4)
        self.stdscr.attron(curses.color_pair(10))
        self.stdscr.addstr(1, 2, sep_line)
        self.stdscr.attroff(curses.color_pair(10))
        
        # 显示终端输出
        start_line = max(0, len(self.terminal_output) - (max_y - 6))
        for i, line in enumerate(self.terminal_output[start_line:]):
            if i < max_y - 5:
                # 截断过长的行
                display_line = line[:max_x-4] if len(line) > max_x-4 else line
                self.stdscr.addstr(i + 2, 2, display_line)
        
        # 显示分隔线
        self.stdscr.attron(curses.color_pair(10))
        self.stdscr.addstr(max_y - 3, 2, sep_line)
        self.stdscr.attroff(curses.color_pair(10))
        
        # 显示命令输入行
        prompt = "$ "
        input_line = prompt + self.terminal_input
        # 如果输入行太长，截断并显示光标位置
        if len(input_line) > max_x - 4:
            start_pos = max(0, len(self.terminal_input) - (max_x - 6))
            display_input = input_line[start_pos:start_pos + max_x - 4]
            cursor_pos = len(prompt) + len(self.terminal_input) - start_pos
        else:
            display_input = input_line
            cursor_pos = len(display_input)
        
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(max_y - 2, 2, display_input)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
        # 显示光标
        if time.time() % 1 < 0.5:  # 闪烁光标
            try:
                self.stdscr.addstr(max_y - 2, 2 + cursor_pos, "_")
            except:
                pass
        
        # 显示帮助提示
        help_text = "按空格+回车返回 | ↑↓浏览历史命令"
        self.stdscr.attron(curses.color_pair(1) | curses.A_DIM)
        self.stdscr.addstr(max_y - 1, max_x // 2 - len(help_text) // 2, help_text)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_DIM)
        
        self.stdscr.refresh()

    def run(self):
        if self.current_book:
            while self.running:
                if self.boss_mode:
                    self.display_terminal()
                    c = self.stdscr.getch()
                    self.handle_terminal_input(c)
                else:
                    self.display()
                    self.handle_input()
                    self.save_progress()
                    self.stats.record_reading(self.current_book["id"], int(time.time() - self.start_time))
                    self.check_remind()
                    self.start_time = time.time()
                    if self.auto_page:
                        time.sleep(self.settings["auto_page_interval"])
                        self.next_page()
        else:
            self.show_bookshelf()
            while self.running:
                if self.boss_mode:
                    self.display_terminal()
                    c = self.stdscr.getch()
                    self.handle_terminal_input(c)
                else:
                    self.display()
                    self.handle_input()
                    self.save_progress()
                    self.stats.record_reading(self.current_book["id"], int(time.time() - self.start_time))
                    self.check_remind()
                    self.start_time = time.time()
                    if self.auto_page:
                        time.sleep(self.settings["auto_page_interval"])
                        self.next_page()
                        
        # 确保在退出前停止朗读
        self.stop_reading()