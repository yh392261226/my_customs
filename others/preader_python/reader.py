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
    "T 全部统计",
    "x 删除书籍",
    "空格 老板键"
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
    
    # 使用更安全的方法处理输入
    curses.echo()
    try:
        # 使用getstr但捕获可能的解码错误
        val_bytes = stdscr.getstr(y+1, x+2+len(prompt), maxlen)
        
        # 尝试UTF-8解码，如果失败则使用替代方法
        try:
            val = val_bytes.decode('utf-8').strip()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试使用latin-1编码
            val = val_bytes.decode('latin-1').strip()
    except Exception as e:
        # 如果出现任何异常，返回空字符串
        val = ""
    
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
        # 老板键模式相关属性
        self.boss_mode = False
        self.terminal_input = ""
        self.terminal_output = []
        self.terminal_cursor = 0
        self.terminal_history = []
        self.terminal_position = 0
        self.terminal_cursor_pos = 0  # 光标在输入行中的位置
        self.terminal_scroll_offset = 0  # 输出滚动偏移
        self.terminal_suggestions = []  # 自动补全建议
        self.terminal_suggestion_index = 0  # 当前选中的建议索引
        self.selected_tags = set() # 存储选中的标签
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
        title = f"📖 {get_text('novel_reader', self.lang)} - {get_text('loading', self.lang)}"
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
        tip = f"{get_text('wait_for_loading', self.lang)}..."
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
        self.show_loading_screen(get_text("loading_books", self.lang))
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
            self.show_loading_screen(get_text("parsing_epub_data", self.lang))
            chapters = parse_epub(book["path"], width, height, line_spacing, self.lang)
            
            pages = []
            total_chapters = len(chapters)
            for i, ch in enumerate(chapters):
                # 添加章节标题页
                pages.append([f"《{ch['title']}》"])
                # 添加章节内容页
                pages.extend(ch["pages"])
                
                # 每处理一章更新一次显示
                if i % 2 == 0:  # 每两章更新一次，避免过于频繁
                    self.show_loading_screen(f"{get_text('action_document_line', self.lang)}: {i+1}/{total_chapters}")
            
            self.current_pages = pages
            self.show_loading_screen(get_text("action_pages", self.lang))
            time.sleep(0.5)
        else:
            # 使用新版 utils.build_pages_from_file，确保不丢失任何内容
            self.current_pages = build_pages_from_file(
                book["path"], width, height, line_spacing, progress_callback, self.lang
            )
            self.show_loading_screen(get_text("action_pages", self.lang))
            time.sleep(0.5)
        # 在解析完成后检查是否为空
        if not self.current_pages:
            self.current_pages = [[get_text("empty_file_or_cannot_read", self.lang)]]
        

        self.current_book = book
        self.current_page_idx = self.db.get_progress(book["id"])
        self.highlight_lines = set()

    def show_bookshelf(self):
        """显示书架界面，支持标签过滤和批量编辑"""
        books_per_page = max(1, self.get_safe_height() - 8)
        page = 0
        search_keyword = ""
        
        # 初始过滤书籍列表
        filtered_books = self.bookshelf.books
        
        # 如果有选中的标签，按标签过滤
        if self.selected_tags:
            filtered_books = [
                book for book in filtered_books 
                if any(tag in book["tags"] for tag in self.selected_tags)
            ]
        
        # 如果有搜索关键词，进一步过滤
        if search_keyword:
            filtered_books = [
                book for book in filtered_books 
                if search_keyword.lower() in book["title"].lower()
            ]
        
        # 按标题排序
        filtered_books.sort(key=lambda x: x["title"].lower())
        
        current_selection = 0
        book_selected = False
        tag_mode = False  # 标签模式标志
        selected_book_ids = set()  # 存储选中的书籍ID
        
        while not book_selected and self.running:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            total_books = len(filtered_books)
            total_pages = (total_books + books_per_page - 1) // books_per_page if total_books else 1
            start_idx = page * books_per_page
            end_idx = min(start_idx + books_per_page, total_books)
            current_page_books = filtered_books[start_idx:end_idx]
            
            # 显示标题和标签信息
            title_str = "📚 " + get_text("bookshelf", self.lang) + f" [{page+1}/{total_pages}]"
            if search_keyword:
                title_str += f" | {get_text('search', self.lang)}: {search_keyword}"
            if self.selected_tags:
                title_str += f" | {get_text('tag', self.lang)}: {', '.join(self.selected_tags)}"
            if tag_mode:
                title_str += f" | {get_text('multype_mode', self.lang)}: {get_text('already_selected_books', self.lang).format(books=f'{len(selected_book_ids)}')}"
                
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title_str) // 2, title_str)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示书籍列表
            for idx, book in enumerate(current_page_books):
                exists = "" if book["exists"] else "❌"
                selected = "[✓]" if book["id"] in selected_book_ids else ""
                tags_str = ",".join(book["tags"]) if book["tags"] else get_text('no_tags', self.lang)
                line = f" {selected} {start_idx+idx+1:02d} | {exists} {book['title'][:25]:<25} | {get_text('author', self.lang)}:{book['author'][:15]:<15} | {get_text('tag', self.lang)}:{tags_str}"
                
                # 根据文件是否存在设置颜色
                if not book["exists"]:
                    color = curses.color_pair(3)  # 红色，表示文件不存在
                else:
                    color = curses.color_pair(2) if idx % 2 else curses.color_pair(1)
                
                # 如果是当前选中的行，添加反色效果
                if idx == current_selection:
                    color |= curses.A_REVERSE
                    
                self.stdscr.attron(color | curses.A_BOLD)
                self.stdscr.addstr(idx+2, 2, line[:max_x-3])
                self.stdscr.attroff(color | curses.A_BOLD)
                    
            # 显示操作提示
            help_lines = [
                f"[a] {get_text('add_book', self.lang)}  [d] {get_text('add_dir', self.lang)} [/] {get_text('search', self.lang)} [p] {get_text('pre_page', self.lang)} [n] {get_text('next_page', self.lang)}",
                f"[t] {get_text('tag_management', self.lang)} [e] {get_text('edit_book', self.lang)} [x] {get_text('delete', self.lang)}  [q] {get_text('exit', self.lang)}",
            ]
            
            if tag_mode:
                help_lines.append(f"[l] {get_text('out_multype_mode', self.lang)} [{get_text('space', self.lang)}] {get_text('select_or_unselect', self.lang)} [b] {get_text('multype_tags_edit', self.lang)} [a] {get_text('select_all', self.lang)} [c] {get_text('unselect_all', self.lang)}")
            else:
                help_lines.append(f"[l] {get_text('in_multype_mode', self.lang)} [Enter] {get_text('select', self.lang)}")
            
            for i, line in enumerate(help_lines):
                self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
                self.stdscr.addstr(books_per_page+3+i, 2, line[:max_x-3])
                self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
                
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('a'):
                if tag_mode:
                    # 在多选模式下，全选当前页
                    for book in current_page_books:
                        selected_book_ids.add(book["id"])
                else:
                    # 正常模式下添加书籍
                    path = input_box(self.stdscr, get_text("input_path", self.lang), maxlen=120)
                    if path:
                        self.bookshelf.add_book(path, width=self.settings["width"], height=self.settings["height"], line_spacing=self.settings["line_spacing"])
                        # 刷新书籍列表
                        self.bookshelf.books = self.bookshelf.load_books()
                        # 重新应用过滤
                        filtered_books = self.bookshelf.books
                        if search_keyword:
                            filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                        if self.selected_tags:
                            filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
            elif c == ord('d'):
                dir_path = input_box(self.stdscr, get_text("input_dir", self.lang), maxlen=120)
                if dir_path:
                    self.bookshelf.add_dir(dir_path, width=self.settings["width"], height=self.settings["height"], line_spacing=self.settings["line_spacing"])
                    # 刷新书籍列表
                    self.bookshelf.books = self.bookshelf.load_books()
                    # 重新应用过滤
                    filtered_books = self.bookshelf.books
                    if search_keyword:
                        filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                    if self.selected_tags:
                        filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
            elif c == ord('/'):
                kw = input_box(self.stdscr, get_text("input_search", self.lang), maxlen=30)
                search_keyword = kw
                page = 0
                current_selection = 0
                # 重新应用过滤
                filtered_books = self.bookshelf.books
                if search_keyword:
                    filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                if self.selected_tags:
                    filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
            elif c == ord('x'):
                if tag_mode and selected_book_ids:
                    # 在多选模式下删除选中的书籍
                    confirm = input_box(self.stdscr, f"{get_text('book_deletion_confirm', self.lang).format(books=f'{len(selected_book_ids)}')} (y/N): ", maxlen=1)
                    if confirm.lower() == 'y':
                        self.bookshelf.delete_books(list(selected_book_ids))
                        selected_book_ids.clear()
                        # 刷新书籍列表
                        self.bookshelf.books = self.bookshelf.load_books()
                        # 重新应用过滤
                        filtered_books = self.bookshelf.books
                        if search_keyword:
                            filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                        if self.selected_tags:
                            filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
                else:
                    self.show_book_deletion()
                    # 刷新书籍列表
                    self.bookshelf.books = self.bookshelf.load_books()
                    # 重新应用过滤
                    filtered_books = self.bookshelf.books
                    if search_keyword:
                        filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                    if self.selected_tags:
                        filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
            elif c == ord('t'):
                self.show_tag_management()
                # 刷新书籍列表
                self.bookshelf.books = self.bookshelf.load_books()
                # 重新应用过滤
                filtered_books = self.bookshelf.books
                if search_keyword:
                    filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                if self.selected_tags:
                    filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
            elif c == ord('e'):
                if current_page_books:
                    book = current_page_books[current_selection]
                    self.edit_book_metadata(book["id"])
                    # 刷新书籍列表
                    self.bookshelf.books = self.bookshelf.load_books()
                    # 重新应用过滤
                    filtered_books = self.bookshelf.books
                    if search_keyword:
                        filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                    if self.selected_tags:
                        filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
            elif c == ord('l'):
                # 切换多选模式
                tag_mode = not tag_mode
                if not tag_mode:
                    # 退出多选模式时清空选择
                    selected_book_ids.clear()
                else:
                    # 进入多选模式时，可以选择当前页的所有书籍
                    for book in current_page_books:
                        selected_book_ids.add(book["id"])
            elif c == ord('b') and tag_mode and selected_book_ids:
                # 批量编辑标签
                self.show_batch_tag_edit(list(selected_book_ids))
                # 刷新书籍列表
                self.bookshelf.books = self.bookshelf.load_books()
                # 重新应用过滤
                filtered_books = self.bookshelf.books
                if search_keyword:
                    filtered_books = [book for book in filtered_books if search_keyword.lower() in book["title"].lower()]
                if self.selected_tags:
                    filtered_books = [book for book in filtered_books if any(tag in book["tags"] for tag in self.selected_tags)]
            elif c == ord('c') and tag_mode:
                # 取消全选
                selected_book_ids.clear()
            elif c == ord('q'):
                self.running = False
                break
            elif c == curses.KEY_UP:
                if current_selection > 0:
                    current_selection -= 1
                elif current_selection == 0 and page > 0:
                    page -= 1
                    current_selection = books_per_page - 1
            elif c == curses.KEY_DOWN:
                if current_selection < len(current_page_books) - 1:
                    current_selection += 1
                elif current_selection == len(current_page_books) - 1 and page < total_pages - 1:
                    page += 1
                    current_selection = 0
            elif c == curses.KEY_NPAGE or c == ord('n'):
                if page < total_pages - 1:
                    page += 1
                    current_selection = 0
            elif c == curses.KEY_PPAGE or c == ord('p'):
                if page > 0:
                    page -= 1
                    current_selection = 0
            elif c == ord(' ') and tag_mode:
                # 在多选模式下，空格键选择/取消选择当前书籍
                if current_page_books:
                    book = current_page_books[current_selection]
                    if book["id"] in selected_book_ids:
                        selected_book_ids.remove(book["id"])
                    else:
                        selected_book_ids.add(book["id"])
            elif c in (10, 13) and not tag_mode:  # 回车键选择当前书籍（非多选模式）
                if current_page_books:
                    book = current_page_books[current_selection]
                    if not book["exists"]:
                        # 文件不存在，提示更新路径
                        self.update_missing_book_path(book["id"])
                    else:
                        self.load_book(book)
                        book_selected = True
            elif c in range(48, 58):  # 数字键0-9，支持快速跳转
                # 保存当前按键
                key_char = chr(c)
                # 显示输入的数字
                self.stdscr.addstr(books_per_page+7, 2, f"{get_text('input_no', self.lang)}: {key_char}")
                self.stdscr.refresh()
                
                # 等待可能的第二个数字（两位数）
                second_c = self.stdscr.getch()
                if second_c in range(48, 58):  # 第二个数字
                    key_char += chr(second_c)
                    self.stdscr.addstr(books_per_page+7, 2, f"{get_text('input_no', self.lang)}: {key_char}")
                    self.stdscr.refresh()
                    
                try:
                    idx = int(key_char) - 1
                    if 0 <= idx < total_books:
                        book = filtered_books[idx]
                        if not book["exists"]:
                            # 文件不存在，提示更新路径
                            self.update_missing_book_path(book["id"])
                        else:
                            self.load_book(book)
                            book_selected = True
                    else:
                        self.stdscr.addstr(books_per_page+7, 2, get_text('no_limited', self.lang))
                        self.stdscr.refresh()
                        time.sleep(1)
                except:
                    self.stdscr.addstr(books_per_page+7, 2, get_text('invalid', self.lang))
                    self.stdscr.refresh()
                    time.sleep(1)

    def show_tag_management(self):
        """显示标签管理界面 - 修复删除功能"""
        all_tags = self.bookshelf.get_all_tags()
        selected_tags = self.selected_tags.copy()
        current_selection = 0
        
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            
            # 显示标题
            title = f"🏷️ {get_text('tag_management', self.lang)}"
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示分隔线
            sep_line = "─" * (max_x - 4)
            self.stdscr.attron(curses.color_pair(10))
            self.stdscr.addstr(1, 2, sep_line)
            self.stdscr.attroff(curses.color_pair(10))
            
            # 显示标签列表
            for idx, tag in enumerate(all_tags):
                selected = "[✓]" if tag in selected_tags else "[ ]"
                line = f" {selected} {tag}"
                
                color = curses.color_pair(2) if idx % 2 else curses.color_pair(1)
                if idx == current_selection:
                    color |= curses.A_REVERSE
                    
                self.stdscr.attron(color)
                self.stdscr.addstr(idx+3, 4, line[:max_x-8])
                self.stdscr.attroff(color)
            
            # 显示操作提示
            help_text = f"[{get_text('space', self.lang)}] {get_text('select_or_unselect', self.lang)} [a] {get_text('add_tag', self.lang)} [d] {get_text('remove_tag', self.lang)} [Enter] {get_text('use_filter', self.lang)} [q] {get_text('back', self.lang)}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(max_y-3, 4, help_text[:max_x-8])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            # 显示分隔线
            self.stdscr.attron(curses.color_pair(10))
            self.stdscr.addstr(max_y-4, 2, sep_line)
            self.stdscr.attroff(curses.color_pair(10))
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c == curses.KEY_UP:
                if current_selection > 0:
                    current_selection -= 1
            elif c == curses.KEY_DOWN:
                if current_selection < len(all_tags) - 1:
                    current_selection += 1
            elif c == ord(' '):  # 空格键选择/取消选择标签
                if all_tags:
                    tag = all_tags[current_selection]
                    if tag in selected_tags:
                        selected_tags.remove(tag)
                    else:
                        selected_tags.add(tag)
            elif c == ord('a'):  # 添加新标签
                new_tag = input_box(self.stdscr, f"{get_text('type_new_tag_name', self.lang)}: ", maxlen=20)
                if new_tag:
                    # 检查标签是否已存在
                    if new_tag not in all_tags:
                        self.bookshelf.db.add_tag(new_tag)
                        all_tags = self.bookshelf.get_all_tags()  # 刷新标签列表
                    else:
                        # 显示错误消息
                        self.stdscr.addstr(max_y-2, 4, f"{get_text('tag_already_exists', self.lang)}!")
                        self.stdscr.refresh()
                        time.sleep(1)
            elif c == ord('d'):  # 删除标签
                if all_tags:
                    tag = all_tags[current_selection]
                    confirm = input_box(self.stdscr, f"{get_text('confirm_remove_tags', self.lang)} '{tag}'? (y/N): ", maxlen=1)
                    if confirm.lower() == 'y':
                        if self.bookshelf.delete_tag(tag):
                            # 从所有标签列表中移除
                            all_tags = self.bookshelf.get_all_tags()
                            # 从选中标签中移除
                            if tag in selected_tags:
                                selected_tags.remove(tag)
                            # 显示成功消息
                            self.stdscr.addstr(max_y-2, 4, f"{get_text('already_deleted_tag', self.lang)}: {tag}")
                            self.stdscr.refresh()
                            time.sleep(1)
                        else:
                            # 显示错误消息
                            self.stdscr.addstr(max_y-2, 4, f"{get_text('remove_tag_failed', self.lang)}!")
                            self.stdscr.refresh()
                            time.sleep(1)
            elif c in (10, 13):  # 回车键应用筛选
                self.selected_tags = selected_tags
                break
        
        # 返回书架主界面
        self.show_bookshelf()

    def edit_book_metadata(self, book_id):
        """编辑书籍元数据"""
        book = self.bookshelf.get_book_by_id(book_id)
        if not book:
            return
            
        # 获取当前信息
        current_title = book["title"]
        current_author = book["author"]
        current_tags = ",".join(book["tags"])
        
        # 显示编辑界面
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        title = f"📝 {get_text('edit_book_info', self.lang)}"
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        # 显示当前信息
        self.stdscr.addstr(2, 4, f"{get_text('book_name', self.lang)}: {current_title}")
        self.stdscr.addstr(3, 4, f"{get_text('book_author', self.lang)}: {current_author}")
        self.stdscr.addstr(4, 4, f"{get_text('tag', self.lang)}: {current_tags}")
        
        # 显示操作提示
        help_text = f"[t] {get_text('edit_title', self.lang)} [a] {get_text('edit_author', self.lang)} [g] {get_text('edit_tags', self.lang)} [Enter] {get_text('save_changes', self.lang)} [q] {get_text('back', self.lang)}"
        self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
        self.stdscr.addstr(6, 4, help_text[:max_x-8])
        self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
        
        self.stdscr.refresh()
        
        while True:
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c == ord('t'):  # 编辑标题
                new_title = input_box(self.stdscr, f"{get_text('new_book_name', self.lang)}: ", maxlen=100, y=2, x=10)
                if new_title:
                    current_title = new_title
                    self.stdscr.addstr(2, 10, " " * (max_x-20))
                    self.stdscr.addstr(2, 10, current_title)
                    self.stdscr.refresh()
            elif c == ord('a'):  # 编辑作者
                new_author = input_box(self.stdscr, f"{get_text('new_book_author', self.lang)}: ", maxlen=50, y=3, x=10)
                if new_author:
                    current_author = new_author
                    self.stdscr.addstr(3, 10, " " * (max_x-20))
                    self.stdscr.addstr(3, 10, current_author)
                    self.stdscr.refresh()
            elif c == ord('g'):  # 编辑标签
                new_tags = input_box(self.stdscr, f"{get_text('new_book_tags', self.lang)}: ", maxlen=100, y=4, x=10)
                if new_tags is not None:
                    current_tags = new_tags
                    self.stdscr.addstr(4, 10, " " * (max_x-20))
                    self.stdscr.addstr(4, 10, current_tags)
                    self.stdscr.refresh()
            elif c in (10, 13):  # 回车键保存
                # 确保即使只修改了标签也能保存
                self.bookshelf.update_book_metadata(book_id, current_title, current_author, current_tags)
                break

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
            empty_msg = f"{get_text('empty_file_or_cannot_read', self.lang)}"
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(margin + height // 2, max_x // 2 - len(empty_msg) // 2, empty_msg)
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.refresh()
            return
        
        page_lines = self.current_pages[self.current_page_idx] if self.current_pages else []
        if self.current_pages and self.current_book:
            progress = int((self.current_page_idx+1)/len(self.current_pages)*100)
            bar_len = int(progress / 5)
            
            title_str = f"《{self.current_book['title']}》{get_text('reading_progress', self.lang)}:[{'█'*bar_len}{'-'*(20-bar_len)}] {progress:3d}%"
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
            reading_status = f"🔊 {get_text('aloud_r2_stop', self.lang)}"
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
            self.stdscr.addstr(i+2, 4, f"{i+1:02d}. {get_text('page_no', self.lang).format(page=page+1)}: {comment}"[:max_x-8])
        self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
        self.stdscr.addstr(max_y-4, 4, get_text('input_jump_page_quit', self.lang))
        self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
        self.stdscr.refresh()
        c = self.stdscr.getch()
        if c == ord('q'):
            return
        elif c in [10, 13]:
            idx_str = input_box(self.stdscr, f"{get_text('number', self.lang)}: ", maxlen=8)
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < len(bookmarks):
                    self.current_page_idx = bookmarks[idx][0]
                else:
                    self.stdscr.addstr(max_y-2, 4, get_text('no_unlimited', self.lang))
                    self.stdscr.refresh()
                    time.sleep(1)
            except:
                self.stdscr.addstr(max_y-2, 4, get_text('invalid', self.lang))
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
            self.stdscr.addstr(0, max_x // 2 - 7, f"📚 {get_text('stats_all', self.lang)}")
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            start_idx = page * stats_per_page
            end_idx = min(start_idx + stats_per_page, total_books)
            y = 2
            for book in books[start_idx:end_idx]:
                book_id = book["id"]
                stat = all_stats.get(book_id, {"total_time":0, "days":0})
                line = f"{book['title'][:20]:<20} | {stat['total_time']//60:>4} {get_text('minutes', self.lang)} | {stat['days']} {get_text('day', self.lang)}"
                self.stdscr.addstr(y, 4, line[:max_x-8])
                y += 1
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            page_info = f"{get_text('page_no', self.lang).format(page=f'{page+1}/{total_pages}')} [n] {get_text('next_page', self.lang)} [p] {get_text('pre_page', self.lang)} [q] {get_text('back', self.lang)}"
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
        """切换老板键模式 - 增强版"""
        self.boss_mode = not self.boss_mode
        if self.boss_mode:
            # 进入老板键模式
            self.terminal_input = ""
            self.terminal_output = [
                f"{get_text('terminal_mode_started', self.lang)}", 
                f"当前目录: {os.getcwd()}",
                f"{get_text('terminal_help_text2', self.lang)}", 
                "----------------------------------------"
            ]
            self.terminal_cursor_pos = 0
            self.terminal_scroll_offset = 0
            self.terminal_suggestions = []
            self.terminal_suggestion_index = 0
        else:
            # 退出老板键模式
            self.terminal_history = []
            self.terminal_position = 0

    def handle_terminal_input(self, c):
        """处理终端模式下的输入 - 增强版"""
        if c == curses.KEY_ENTER or c == 10 or c == 13:  # 回车键
            self.execute_terminal_command()
        elif c == curses.KEY_BACKSPACE or c == 127:  # 退格键
            if self.terminal_input and self.terminal_cursor_pos > 0:
                # 删除光标前的一个字符
                self.terminal_input = self.terminal_input[:self.terminal_cursor_pos-1] + self.terminal_input[self.terminal_cursor_pos:]
                self.terminal_cursor_pos -= 1
                self.update_terminal_suggestions()
        elif c == curses.KEY_LEFT:  # 左箭头
            if self.terminal_cursor_pos > 0:
                self.terminal_cursor_pos -= 1
        elif c == curses.KEY_RIGHT:  # 右箭头
            if self.terminal_cursor_pos < len(self.terminal_input):
                self.terminal_cursor_pos += 1
        elif c == curses.KEY_UP:  # 上箭头 - 历史命令或输出滚动
            if self.terminal_suggestions:
                # 在自动补全模式下，上箭头选择上一个建议
                self.terminal_suggestion_index = max(0, self.terminal_suggestion_index - 1)
            elif self.terminal_history and self.terminal_position > 0:
                # 浏览历史命令
                self.terminal_position -= 1
                self.terminal_input = self.terminal_history[self.terminal_position]
                self.terminal_cursor_pos = len(self.terminal_input)
            else:
                # 滚动输出
                self.terminal_scroll_offset = max(0, self.terminal_scroll_offset - 1)
        elif c == curses.KEY_DOWN:  # 下箭头 - 历史命令或输出滚动
            if self.terminal_suggestions:
                # 在自动补全模式下，下箭头选择下一个建议
                self.terminal_suggestion_index = min(len(self.terminal_suggestions) - 1, self.terminal_suggestion_index + 1)
            elif self.terminal_history and self.terminal_position < len(self.terminal_history) - 1:
                # 浏览历史命令
                self.terminal_position += 1
                self.terminal_input = self.terminal_history[self.terminal_position]
                self.terminal_cursor_pos = len(self.terminal_input)
            elif self.terminal_position == len(self.terminal_history) - 1:
                # 回到空白输入
                self.terminal_position = len(self.terminal_history)
                self.terminal_input = ""
                self.terminal_cursor_pos = 0
            else:
                # 滚动输出
                self.terminal_scroll_offset = min(len(self.terminal_output) - self.get_terminal_output_height(), 
                                                self.terminal_scroll_offset + 1)
        elif c == ord('\t'):  # Tab键 - 自动补全
            self.auto_complete()
        elif c == curses.KEY_PPAGE:  # Page Up - 向上滚动输出
            self.terminal_scroll_offset = max(0, self.terminal_scroll_offset - self.get_terminal_output_height() // 2)
        elif c == curses.KEY_NPAGE:  # Page Down - 向下滚动输出
            max_scroll = max(0, len(self.terminal_output) - self.get_terminal_output_height())
            self.terminal_scroll_offset = min(max_scroll, 
                                            self.terminal_scroll_offset + self.get_terminal_output_height() // 2)
        elif c == 12:  # Ctrl+L - 清屏
            self.terminal_output = []
            self.terminal_scroll_offset = 0
        elif 32 <= c <= 126:  # 可打印字符
            # 在光标处插入字符
            self.terminal_input = (self.terminal_input[:self.terminal_cursor_pos] + 
                                chr(c) + 
                                self.terminal_input[self.terminal_cursor_pos:])
            self.terminal_cursor_pos += 1
            self.update_terminal_suggestions()
        
        self.display_terminal()

    def update_terminal_suggestions(self):
        """更新自动补全建议"""
        if not self.terminal_input:
            self.terminal_suggestions = []
            self.terminal_suggestion_index = 0
            return
        
        # 简单的命令自动补全
        common_commands = [
            "ls", "cd", "pwd", "cat", "echo", "grep", "find", 
            "ps", "top", "kill", "mkdir", "rm", "cp", "mv",
            "python", "pip", "git", "ssh", "scp", "curl", "wget"
        ]
        
        # 过滤匹配的命令
        self.terminal_suggestions = [cmd for cmd in common_commands 
                                    if cmd.startswith(self.terminal_input)]
        self.terminal_suggestion_index = 0

    def auto_complete(self):
        """执行自动补全"""
        if self.terminal_suggestions:
            # 使用当前选中的建议
            self.terminal_input = self.terminal_suggestions[self.terminal_suggestion_index]
            self.terminal_cursor_pos = len(self.terminal_input)
            self.terminal_suggestions = []  # 清空建议列表
            self.terminal_suggestion_index = 0

    def execute_terminal_command(self):
        """执行终端命令 - 增强版"""
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
            self.terminal_output.append(f"$ {command}")
            
            # 特殊处理cd命令
            if command.startswith("cd "):
                try:
                    new_dir = command[3:].strip()
                    if new_dir:
                        os.chdir(new_dir)
                        self.terminal_output.append(f"Changed directory to {os.getcwd()}")
                    else:
                        os.chdir(os.path.expanduser("~"))
                        self.terminal_output.append(f"Changed directory to home")
                except Exception as e:
                    self.terminal_output.append(f"cd: {str(e)}")
            else:
                # 使用subprocess执行命令
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    cwd=os.getcwd()  # 使用当前工作目录
                )
                
                if result.stdout:
                    for line in result.stdout.splitlines():
                        self.terminal_output.append(line)
                if result.stderr:
                    for line in result.stderr.splitlines():
                        self.terminal_output.append(f"\033[91m{line}\033[0m")  # 红色错误信息
                if result.returncode != 0:
                    self.terminal_output.append(f"{get_text('command_exists_code', self.lang)}: {result.returncode}")
                    
        except subprocess.TimeoutExpired:
            self.terminal_output.append(f"{get_text('command_time_unlimit', self.lang)}")
        except Exception as e:
            self.terminal_output.append(f"{get_text('execute_fail', self.lang)}: {str(e)}")
        
        # 限制输出行数
        if len(self.terminal_output) > 1000:
            self.terminal_output = self.terminal_output[-1000:]
        
        # 自动滚动到最底部
        self.terminal_scroll_offset = max(0, len(self.terminal_output) - self.get_terminal_output_height())
        
        self.terminal_input = ""
        self.terminal_cursor_pos = 0
        self.terminal_suggestions = []
        self.terminal_suggestion_index = 0
        self.display_terminal()

    def get_terminal_output_height(self):
        """获取终端输出区域的高度"""
        max_y, _ = self.stdscr.getmaxyx()
        return max_y - 5  # 预留顶部标题、分隔线和底部输入行空间

    def display_terminal(self):
        """显示终端界面 - 增强版"""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 显示终端标题
        title = f"💻 {get_text('terminal_title', self.lang)} - {os.getcwd()}"
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        # 显示分隔线
        sep_line = "─" * (max_x - 4)
        self.stdscr.attron(curses.color_pair(10))
        self.stdscr.addstr(1, 2, sep_line)
        self.stdscr.attroff(curses.color_pair(10))
        
        # 显示终端输出
        output_height = self.get_terminal_output_height()
        start_line = max(0, min(self.terminal_scroll_offset, len(self.terminal_output) - output_height))
        
        for i, line in enumerate(self.terminal_output[start_line:start_line + output_height]):
            if i < output_height:
                # 处理ANSI颜色代码（简化版）
                if '\033[91m' in line:  # 红色错误信息
                    parts = line.split('\033[91m')
                    self.stdscr.attron(curses.color_pair(3))  # 红色
                    self.stdscr.addstr(i + 2, 2, parts[1].replace('\033[0m', '')[:max_x-4])
                    self.stdscr.attroff(curses.color_pair(3))
                else:
                    # 截断过长的行
                    display_line = line[:max_x-4] if len(line) > max_x-4 else line
                    self.stdscr.addstr(i + 2, 2, display_line)
        
        # 显示分隔线
        self.stdscr.attron(curses.color_pair(10))
        self.stdscr.addstr(max_y - 3, 2, sep_line)
        self.stdscr.attroff(curses.color_pair(10))
        
        # 显示命令输入行
        prompt = f"{os.getcwd()}$ "
        input_line = prompt + self.terminal_input
        
        # 计算光标在屏幕上的位置
        cursor_screen_pos = len(prompt) + self.terminal_cursor_pos
        
        # 如果输入行太长，截断并显示光标位置
        if len(input_line) > max_x - 4:
            if cursor_screen_pos >= max_x - 4:
                start_pos = cursor_screen_pos - (max_x - 4) + 1
                display_input = input_line[start_pos:start_pos + max_x - 4]
                cursor_screen_pos = max_x - 5  # 光标在显示区域的最右边
            else:
                display_input = input_line[:max_x-4]
        else:
            display_input = input_line
        
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(max_y - 2, 2, display_input)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
        # 显示自动补全建议
        if self.terminal_suggestions:
            suggestions_text = " | ".join(self.terminal_suggestions)
            # 高亮当前选中的建议
            if self.terminal_suggestion_index < len(self.terminal_suggestions):
                selected = self.terminal_suggestions[self.terminal_suggestion_index]
                suggestions_text = suggestions_text.replace(selected, f"[{selected}]")
            
            # 显示在底部
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(max_y - 1, 2, suggestions_text[:max_x-4])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
        else:
            # 显示帮助提示
            help_text = f"{get_text('terminal_help_text', self.lang)} | Tab: {get_text('auto_complete', self.lang)} | Ctrl+L: {get_text('clear_screen', self.lang)}"
            self.stdscr.attron(curses.color_pair(1) | curses.A_DIM)
            self.stdscr.addstr(max_y - 1, max_x // 2 - len(help_text) // 2, help_text)
            self.stdscr.attroff(curses.color_pair(1) | curses.A_DIM)
        
        # 显示光标
        if time.time() % 1 < 0.5:  # 闪烁光标
            try:
                self.stdscr.addstr(max_y - 2, 2 + cursor_screen_pos, "_")
            except:
                pass
        
        self.stdscr.refresh()

    def show_book_deletion(self):
        """显示书籍删除界面"""
        max_y, max_x = self.stdscr.getmaxyx()
        books_per_page = max(1, self.get_safe_height() - 8)
        page = 0
        selected_books = set()  # 存储选中的书籍ID
        current_selection = 0   # 当前选中的行在当前页的索引
        
        while True:
            self.stdscr.clear()
            
            # 检查书籍存在状态
            self.bookshelf.check_books_existence()
            
            # 显示标题
            title = f"🗑️ {get_text('book_deletion_title', self.lang)}"
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示书籍列表
            total_books = len(self.bookshelf.books)
            total_pages = (total_books + books_per_page - 1) // books_per_page if total_books else 1
            start_idx = page * books_per_page
            end_idx = min(start_idx + books_per_page, total_books)
            current_page_books = self.bookshelf.books[start_idx:end_idx]
            
            for idx, book in enumerate(current_page_books):
                line_num = start_idx + idx + 1
                selected = "[✓]" if book["id"] in selected_books else "[ ]"
                exists = "" if book["exists"] else "❌"
                line = f" {selected} {line_num:02d} | {exists} {book['title'][:25]:<25} | {book['author'][:15]:<15}"
                
                # 根据选择状态和存在状态设置颜色
                if not book["exists"]:
                    color = curses.color_pair(3)  # 红色，表示文件不存在
                elif book["id"] in selected_books:
                    color = curses.color_pair(2) | curses.A_BOLD  # 高亮，表示已选择
                else:
                    color = curses.color_pair(1)  # 普通颜色
                    
                # 如果是当前选中的行，添加反色效果
                if idx == current_selection:
                    color |= curses.A_REVERSE
                    
                self.stdscr.attron(color)
                self.stdscr.addstr(idx + 2, 2, line[:max_x-4])
                self.stdscr.attroff(color)
            
            # 显示页码和帮助信息
            page_info = f"{get_text('page_no', self.lang).format(page=f'{page+1}/{total_pages}')}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(books_per_page + 3, 2, page_info)
            help_text = f"{get_text('book_deletion_help', self.lang)}"
            self.stdscr.addstr(books_per_page + 4, 2, help_text[:max_x-4])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            # 处理输入
            c = self.stdscr.getch()
            if c == ord('q'):  # 退出
                break
            elif c == curses.KEY_UP:  # 上箭头
                if current_selection > 0:
                    current_selection -= 1
                # 如果当前在第一行，且不是第一页，可以翻到上一页并选中最后一本书
                elif current_selection == 0 and page > 0:
                    page -= 1
                    current_selection = books_per_page - 1
            elif c == curses.KEY_DOWN:  # 下箭头
                if current_selection < len(current_page_books) - 1:
                    current_selection += 1
                # 如果当前在最后一行的下一页还有书，则翻到下一页并选中第一本书
                elif current_selection == len(current_page_books) - 1 and page < total_pages - 1:
                    page += 1
                    current_selection = 0
            elif c == ord('n') and page < total_pages - 1:  # 下一页
                page += 1
                current_selection = 0  # 翻页后重置选中行为第一行
            elif c == ord('p') and page > 0:  # 上一页
                page -= 1
                current_selection = 0  # 翻页后重置选中行为第一行
            elif c == ord('a'):  # 全选
                selected_books = set(book["id"] for book in self.bookshelf.books)
            elif c == ord('c'):  # 取消全选
                selected_books.clear()
            elif c == ord(' '):  # 选择/取消选择当前行
                if current_page_books:
                    book_id = current_page_books[current_selection]["id"]
                    if book_id in selected_books:
                        selected_books.remove(book_id)
                    else:
                        selected_books.add(book_id)
            elif c in (10, 13):  # 回车键，确认删除
                if selected_books:
                    selected_books_len=len(selected_books)
                    # 确认删除
                    confirm = input_box(self.stdscr, f"{get_text('book_deletion_confirm', self.lang).format(books=selected_books_len)} (y/N): ", maxlen=1)
                    if confirm.lower() == 'y':
                        self.bookshelf.delete_books(selected_books)
                        selected_books.clear()
                        # 显示删除成功消息
                        msg = f"{get_text('book_deletion_success', self.lang).format(books=selected_books_len)}"
                        self.stdscr.addstr(books_per_page + 6, 2, msg)
                        self.stdscr.refresh()
                        time.sleep(1)
                        # 删除后重新加载书籍列表
                        self.bookshelf.books = self.bookshelf.load_books()
                        # 如果当前页没有书籍了，且不是第一页，则回到上一页
                        if not self.bookshelf.books and page > 0:
                            page -= 1
                        # 调整当前选中行，确保不越界
                        if current_selection >= len(current_page_books):
                            current_selection = max(0, len(current_page_books) - 1)
        
        # 返回书架主界面
        self.show_bookshelf()

    def update_missing_book_path(self, book_id):
        """更新丢失书籍的路径"""
        max_y, max_x = self.stdscr.getmaxyx()
        book = self.bookshelf.get_book_by_id(book_id)
        if not book:
            return
            
        new_path = input_box(self.stdscr, f"{get_text('books', self.lang)} '{book['title']}' {get_text('unfind_type_new', self.lang)}: ", maxlen=200)
        if new_path and os.path.exists(new_path):
            if self.bookshelf.update_book_path(book_id, new_path):
                msg = f"{get_text('update_path_success', self.lang)}"
                self.stdscr.addstr(max_y-2, 2, msg)
                self.stdscr.refresh()
                time.sleep(1)
            else:
                msg = f"{get_text('update_path_fail', self.lang)}"
                self.stdscr.addstr(max_y-2, 2, msg)
                self.stdscr.refresh()
                time.sleep(1)
        else:
            msg = f"{get_text('path_not_exists', self.lang)}"
            self.stdscr.addstr(max_y-2, 2, msg)
            self.stdscr.refresh()
            time.sleep(1)

    def show_batch_tag_edit(self, book_ids):
        """显示批量标签编辑界面 - 修复输入问题"""
        if not book_ids:
            return
            
        current_action = 0  # 0: 添加标签, 1: 移除标签
        tag_input = ""
        continue_editing = True
        
        while continue_editing:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            
            # 显示标题
            title = f"🏷️ {get_text('multype_tags_edit_books', self.lang).format(books=f'({len(book_ids)})')}"
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示分隔线
            sep_line = "─" * (max_x - 4)
            self.stdscr.attron(curses.color_pair(10))
            self.stdscr.addstr(1, 2, sep_line)
            self.stdscr.attroff(curses.color_pair(10))
            
            # 显示操作选项
            actions = [f"{get_text('add_tag', self.lang)}", f"{get_text('remove_tag', self.lang)}"]
            for idx, action in enumerate(actions):
                line = f"{'→' if idx == current_action else ' '} {action}"
                color = curses.color_pair(2) if idx == current_action else curses.color_pair(1)
                self.stdscr.attron(color)
                self.stdscr.addstr(3 + idx, 4, line)
                self.stdscr.attroff(color)
            
            # 显示标签输入框
            self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(6, 4, f"{get_text('type_tag_name', self.lang)}:")
            self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
            
            # 绘制输入框
            input_width = min(40, max_x - 10)
            self.stdscr.attron(curses.color_pair(2))
            self.stdscr.addstr(7, 4, "╭" + "─" * input_width + "╮")
            self.stdscr.addstr(8, 4, "│" + " " * input_width + "│")
            self.stdscr.addstr(9, 4, "╰" + "─" * input_width + "╯")
            
            # 显示输入内容
            display_input = tag_input[:input_width]
            if len(tag_input) > input_width:
                display_input = "..." + tag_input[-input_width+3:]
                
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(8, 6, display_input)
            
            # 显示光标
            if time.time() % 1 < 0.5:  # 闪烁光标
                cursor_pos = min(len(display_input), input_width - 2)
                try:
                    self.stdscr.addstr(8, 6 + cursor_pos, "_")
                except:
                    pass
                    
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            
            # 显示操作提示
            help_text = f"[↑↓] {get_text('select', self.lang)} [Enter] {get_text('confirm', self.lang)} [q] {get_text('back', self.lang)} [c] {get_text('clear_input', self.lang)}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(11, 4, help_text[:max_x-8])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            # 显示分隔线
            self.stdscr.attron(curses.color_pair(10))
            self.stdscr.addstr(12, 2, sep_line)
            self.stdscr.attroff(curses.color_pair(10))
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            
            # 处理字符输入
            if 32 <= c <= 126:  # 可打印字符
                tag_input += chr(c)
                continue  # 继续循环以更新显示
            
            # 处理特殊按键
            if c == ord('q'):
                continue_editing = False
            elif c == ord('c'):
                # 清除输入
                tag_input = ""
            elif c == curses.KEY_UP:
                if current_action > 0:
                    current_action -= 1
            elif c == curses.KEY_DOWN:
                if current_action < len(actions) - 1:
                    current_action += 1
            elif c == curses.KEY_BACKSPACE or c == 127:  # 退格键
                if tag_input:
                    tag_input = tag_input[:-1]
            elif c in (10, 13):  # 回车键
                if tag_input:
                    action = "add" if current_action == 0 else "remove"
                    success_count = self.bookshelf.batch_update_tags(book_ids, action, tag_input)
                    
                    # 显示操作结果
                    result_msg = f"{get_text('already_success_books', self.lang).format(books=success_count)}{actions[current_action]} '{tag_input}'"
                    self.stdscr.addstr(14, 4, result_msg)
                    
                    # 询问是否继续
                    continue_msg = f"{get_text('type_anykey_or_quit', self.lang)}"
                    self.stdscr.addstr(15, 4, continue_msg)
                    self.stdscr.refresh()
                    
                    # 等待用户响应
                    key = self.stdscr.getch()
                    if key == ord('q'):
                        continue_editing = False
                    else:
                        # 清空输入以便输入下一个标签
                        tag_input = ""

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