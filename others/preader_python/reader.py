import curses
import time
import pyttsx3
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
    "m 书架",
    "s 设置",
    "r 朗读",
    "/ 搜索",
    "q 退出",
    "? 帮助",
    "g 跳页",
    "B 书签列表"
]

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
        init_colors(theme=self.settings["theme"], settings=self.settings)

    def load_book(self, book):
        width = self.settings["width"]
        height = self.settings["height"]
        line_spacing = self.settings["line_spacing"]
        if book["type"] == "epub":
            chapters = parse_epub(book["path"], width, height, line_spacing)
            pages = []
            for ch in chapters:
                pages.append([f"《{ch['title']}》"])
                pages.extend(ch["pages"])
            self.current_pages = pages
        else:
            self.current_pages = build_pages_from_file(book["path"], width, height, line_spacing)
        self.current_book = book
        self.current_page_idx = self.db.get_progress(book["id"])
        self.highlight_lines = set()

    def show_bookshelf(self):
        books_per_page = max(1, self.settings["height"] - 10)
        page = 0
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            total_books = len(self.bookshelf.books)
            total_pages = (total_books + books_per_page - 1) // books_per_page
            start_idx = page * books_per_page
            end_idx = min(start_idx + books_per_page, total_books)
            self.stdscr.addstr(0, 0, get_text("bookshelf", self.lang) + f": [{page+1}/{total_pages}]")
            for idx, book in enumerate(self.bookshelf.books[start_idx:end_idx]):
                line = f"[{start_idx+idx+1}] {book['title']}   {get_text('author', self.lang)}:{book['author']}   {book['tags']}"
                self.stdscr.addstr(idx+1, 2, line[:max_x-3])
            self.stdscr.addstr(books_per_page+2, 2,
                f"[a] {get_text('add_book', self.lang)} [d] {get_text('add_dir', self.lang)} [n]下一页 [p]上一页 [q]{get_text('exit', self.lang)}")
            self.stdscr.addstr(books_per_page+4, 2, "输入小说序号并回车可选书")
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c == ord('a'):
                self.stdscr.addstr(books_per_page+5, 2, get_text("input_path", self.lang)[:max_x-3])
                curses.echo()
                path = self.stdscr.getstr(books_per_page+5, 10, 100).decode()
                curses.noecho()
                self.bookshelf.add_book(path, width=self.settings["width"], height=self.settings["height"], line_spacing=self.settings["line_spacing"])
                total_books = len(self.bookshelf.books)
                total_pages = (total_books + books_per_page - 1) // books_per_page
                end_idx = min(start_idx + books_per_page, total_books)
            elif c == ord('d'):
                self.stdscr.addstr(books_per_page+6, 2, get_text("input_dir", self.lang)[:max_x-3])
                curses.echo()
                dir_path = self.stdscr.getstr(books_per_page+6, 10, 100).decode()
                curses.noecho()
                self.bookshelf.add_dir(dir_path, width=self.settings["width"], height=self.settings["height"], line_spacing=self.settings["line_spacing"])
                total_books = len(self.bookshelf.books)
                total_pages = (total_books + books_per_page - 1) // books_per_page
                end_idx = min(start_idx + books_per_page, total_books)
            elif c == ord('q'):
                self.running = False
                break
            elif c == ord('n') and page < total_pages - 1:
                page += 1
            elif c == ord('p') and page > 0:
                page -= 1
            elif c == 10 or c == 13:
                self.stdscr.addstr(books_per_page+7, 2, "序号: ")
                curses.echo()
                idx_str = self.stdscr.getstr(books_per_page+7, 8, 8).decode().strip()
                curses.noecho()
                try:
                    idx = int(idx_str) - 1
                    if 0 <= idx < total_books:
                        self.load_book(self.bookshelf.books[idx])
                        break
                    else:
                        self.stdscr.addstr(books_per_page+8, 2, "序号超范围！")
                        self.stdscr.refresh()
                        time.sleep(1)
                except:
                    self.stdscr.addstr(books_per_page+8, 2, "输入无效！")
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
        page_lines = self.current_pages[self.current_page_idx] if self.current_pages else []
        self.draw_border()
        for idx, line in enumerate(page_lines):
            y = idx + margin + 1
            x = padding + 1
            if y >= max_y - 7:
                break
            safe_line = line.replace('\r', '').replace('\n', '').replace('\t', ' ')
            safe_line = safe_line[:max_x - x - 3] if len(safe_line) > (max_x - x - 3) else safe_line
            try:
                if safe_line.startswith("《") and safe_line.endswith("》"):
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(y, x, safe_line.center(self.settings["width"])[:max_x - x - 3])
                    self.stdscr.attroff(curses.color_pair(2))
                elif idx in self.highlight_lines:
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(y, x, safe_line)
                    self.stdscr.attroff(curses.color_pair(2))
                else:
                    self.stdscr.attron(curses.color_pair(1))
                    self.stdscr.addstr(y, x, safe_line)
                    self.stdscr.attroff(curses.color_pair(1))
            except curses.error:
                pass

        if self.current_pages:
            progress = int((self.current_page_idx+1)/len(self.current_pages)*100)
            bar_len = int(progress / 5)
            bar = "[" + "#" * bar_len + "-" * (20-bar_len) + f"] {progress}%"
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(self.settings["height"]+margin, 2, bar[:max_x-4])
            self.stdscr.attroff(curses.color_pair(3))
        if self.settings["status_bar"]:
            status = f"{self.current_book['title']} | {get_text('author', self.lang)}: {self.current_book['author']} | {get_text('current_page', self.lang)}: {self.current_page_idx+1}/{len(self.current_pages)}"
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(self.settings["height"]+margin+1, 2, status[:max_x-4], curses.A_BOLD)
            self.stdscr.attroff(curses.color_pair(4))
            help_str = " ".join(KEYS_HELP)
            self.stdscr.addstr(self.settings["height"]+margin+2, 2, help_str[:max_x-4], curses.A_DIM)
        self.stdscr.refresh()

    def handle_input(self):
        c = self.stdscr.getch()
        if c in (curses.KEY_RIGHT, curses.KEY_NPAGE, ord('j')):
            self.next_page()
        elif c in (curses.KEY_LEFT, curses.KEY_PPAGE, ord('k')):
            self.prev_page()
        elif c == ord('a'):
            self.auto_page = not self.auto_page
        elif c == ord('b'):
            self.add_bookmark()
        elif c == ord('m'):
            self.show_bookshelf()
        elif c == ord('q'):
            self.running = False
        elif c == ord('r'):
            self.read_aloud()
        elif c == ord('/'):
            self.search()
        elif c == ord('s'):
            self.change_settings()
        elif c == ord('?'):
            self.show_help()
        elif c == ord('g'):
            self.jump_page()
        elif c == ord('B'):
            self.show_bookmarks()

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
        self.stdscr.attron(curses.color_pair(2))
        self.stdscr.addstr(0, 0, get_text("bookmark_list", self.lang))
        self.stdscr.attroff(curses.color_pair(2))
        for i, (page, comment) in enumerate(bookmarks[:max_y-5]):
            self.stdscr.addstr(i+1, 2, f"{i+1}. 第{page+1}页: {comment}"[:max_x-4])
        self.stdscr.addstr(max_y-3, 2, "输入书签序号并回车跳转，q退出")
        self.stdscr.refresh()
        c = self.stdscr.getch()
        if c == ord('q'):
            return
        elif c == 10 or c == 13:
            self.stdscr.addstr(max_y-2, 2, "序号: ")
            curses.echo()
            idx_str = self.stdscr.getstr(max_y-2, 8, 8).decode().strip()
            curses.noecho()
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(bookmarks):
                    self.current_page_idx = bookmarks[idx][0]
                else:
                    self.stdscr.addstr(max_y-1, 2, "序号超范围！")
                    self.stdscr.refresh()
                    time.sleep(1)
            except:
                self.stdscr.addstr(max_y-1, 2, "输入无效！")
                self.stdscr.refresh()
                time.sleep(1)

    def jump_page(self):
        max_y, max_x = self.stdscr.getmaxyx()
        self.stdscr.addstr(max_y-3, 2, get_text("input_jump_page", self.lang))
        curses.echo()
        page_str = self.stdscr.getstr(max_y-3, 22, 10).decode().strip()
        curses.noecho()
        try:
            page_num = int(page_str)
            if 1 <= page_num <= len(self.current_pages):
                self.current_page_idx = page_num - 1
            else:
                self.stdscr.addstr(max_y-2, 2, get_text("invalid", self.lang))
                self.stdscr.refresh()
                time.sleep(1)
        except:
            self.stdscr.addstr(max_y-2, 2, get_text("invalid", self.lang))
            self.stdscr.refresh()
            time.sleep(1)

    def add_bookmark(self):
        self.stdscr.addstr(self.settings["height"]+self.settings["margin"]+3, 0, get_text("input_comment", self.lang))
        curses.echo()
        comment = self.stdscr.getstr(self.settings["height"]+self.settings["margin"]+3, 10, 100).decode()
        curses.noecho()
        self.db.add_bookmark(self.current_book["id"], self.current_page_idx, comment)

    def read_aloud(self):
        txt = "\n".join(self.current_pages[self.current_page_idx])
        self.engine.say(txt)
        self.engine.runAndWait()

    def search(self):
        self.stdscr.addstr(self.settings["height"]+self.settings["margin"]+2, 0, get_text("input_search", self.lang))
        curses.echo()
        kw = self.stdscr.getstr(self.settings["height"]+self.settings["margin"]+2, 10, 50).decode()
        curses.noecho()
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
        box_top = max_y // 2 - 2
        box_left = max_x // 2 - len(msg) // 2 - 2
        self.stdscr.attron(curses.color_pair(2))
        self.stdscr.addstr(box_top, box_left, " " * (len(msg)+4))
        self.stdscr.addstr(box_top+1, box_left, f"  {msg}  ")
        self.stdscr.addstr(box_top+2, box_left, " " * (len(msg)+4))
        self.stdscr.attroff(curses.color_pair(2))
        self.stdscr.refresh()
        time.sleep(3)

    def change_settings(self):
        options = [
            ("width", "宽度", int, 40, 200),
            ("height", "高度", int, 10, 80),
            ("theme", get_text("input_theme", self.lang), str, ["dark", "light", "eye"]),
            ("lang", get_text("input_lang", self.lang), str, ["zh", "en"]),
            ("font_color", get_text("input_font_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("bg_color", get_text("input_bg_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("border_style", get_text("input_border_style", self.lang), str, ["round","double","single","bold","none"]),
            ("border_color", get_text("input_border_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("line_spacing", "行距", int, 1, 5),
            ("auto_page_interval", "自动翻页秒", int, 1, 60),
            ("remind_interval", get_text("input_remind_interval", self.lang), int, 0, 120),
        ]
        curr = 0
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(0, 0, "设置界面：↑↓选择，回车修改，q返回")
            self.stdscr.attroff(curses.color_pair(4))
            for idx, (key, desc, typ, *meta) in enumerate(options):
                val = self.settings[key]
                line = f"{desc} [{val}]"
                if idx == curr:
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(idx+2, 2, line[:max_x-4])
                    self.stdscr.attroff(curses.color_pair(2))
                else:
                    self.stdscr.addstr(idx+2, 2, line[:max_x-4])
            self.stdscr.addstr(len(options)+3, 2, "回车修改，q返回")
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
                break
            elif c in (curses.KEY_ENTER, 10, 13):
                key, desc, typ, *meta = options[curr]
                self.stdscr.addstr(len(options)+5, 2, f"请输入新值：")
                curses.echo()
                newval = self.stdscr.getstr(len(options)+5, 10, 20).decode().strip()
                curses.noecho()
                valid = False
                if typ == int:
                    try:
                        v = int(newval)
                        if len(meta)==2 and (meta[0] <= v <= meta[1]):
                            self.settings[key] = v
                            valid = True
                    except:
                        pass
                elif typ == str:
                    if isinstance(meta[0], list) and newval in meta[0]:
                        self.settings[key] = newval
                        valid = True
                if not valid:
                    self.stdscr.addstr(len(options)+6, 2, get_text("invalid", self.lang))
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

    def show_help(self):
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, get_text("help", self.lang)+":")
        for idx, h in enumerate(KEYS_HELP):
            self.stdscr.addstr(idx+1, 2, h)
        self.stdscr.addstr(len(KEYS_HELP)+2, 2, get_text("exit", self.lang))
        self.stdscr.refresh()
        self.stdscr.getch()

    def run(self):
        if self.current_book:
            while self.running:
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
                self.display()
                self.handle_input()
                self.save_progress()
                self.stats.record_reading(self.current_book["id"], int(time.time() - self.start_time))
                self.check_remind()
                self.start_time = time.time()
                if self.auto_page:
                    time.sleep(self.settings["auto_page_interval"])
                    self.next_page()