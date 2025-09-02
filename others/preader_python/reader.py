try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.text import Text
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
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
from chart_utils import display_rich_chart_in_terminal

def input_box(stdscr, prompt, maxlen=50, color_pair=2, y=None, x=None, default=""):
    """美化输入框，居中显示，支持默认值"""
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
    
    # 显示默认值
    if default:
        stdscr.addstr(y+1, x+2+len(prompt), default)
    
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
    
    # 如果用户没有输入任何内容，返回默认值
    if not val and default:
        return default
        
    return val

class NovelReader:
    def __init__(self, stdscr, bookshelf, settings):
        self.stdscr = stdscr
        self.bookshelf = bookshelf
        self.settings = settings
        self.db = DBManager()
        self.stats = StatsManager()
        self.engine = pyttsx3.init()
        # 设置初始语速
        self.engine.setProperty('rate', self.settings["speech_rate"])
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
        # 添加这些属性来跟踪显示状态
        self.display_start_line = 0  # 当前显示起始行
        self.display_start_col = 0   # 当前显示起始列
        self.max_display_lines = 0   # 最大可显示行数
        self.max_display_cols = 0    # 最大可显示列数

    def get_safe_height(self):
        """计算安全的显示高度，考虑边框、边距和缩放因子"""
        max_y, _ = self.stdscr.getmaxyx()
        margin = self.settings["margin"]
        
        # 考虑缩放因子
        zoom_factor = max(0.1, self.get_setting("font_scale", 1.0))  # 确保最小缩放因子为0.1
        
        # 预留顶部/底部/状态栏空间（9行），并考虑缩放因子
        return max(1, min(self.settings["height"], int((max_y - margin - 9) / zoom_factor)))

    def show_loading_screen(self, message, progress=None):
        """显示美观的加载屏幕，支持进度显示"""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 考虑缩放因子
        zoom_factor = self.get_setting("font_scale", 1.0)
        
        # 绘制边框
        self.draw_border()
        
        # 显示标题
        title = f"📖 {get_text('novel_reader', self.lang)} - {get_text('loading', self.lang)}"
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(2, max_x // 2 - len(title) // 2, title)
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        # 显示消息
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(int(max_y * 0.5 / zoom_factor) - 2, max_x // 2 - len(message) // 2, message)
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
        """加载书籍，基于固定字符数进行分页（不考虑缩放因子）"""
        # 使用固定的字符数进行分页（不考虑缩放）
        base_width = max(10, self.settings["width"])  # 每行字符数，最小10
        base_height = max(5, self.settings["height"])  # 每页行数，最小5
        line_spacing = max(0, self.settings["line_spacing"])
        paragraph_spacing = max(0, self.get_setting("paragraph_spacing", 0))
        
        # 显示加载屏幕
        self.show_loading_screen(get_text("loading_books", self.lang))
        time.sleep(0.5)
        
        # 进度回调函数
        def progress_callback(message):
            progress = None
            if ":" in message and "/" in message:
                parts = message.split(":")
                if len(parts) > 1 and "/" in parts[1]:
                    progress = parts[1].strip()
            self.show_loading_screen(message, progress)
        
        if book["type"] == "epub":
            self.show_loading_screen(get_text("parsing_epub_data", self.lang))
            # EPUB解析需要传递字符宽度和高度
            chapters = parse_epub(book["path"], base_width, base_height, line_spacing, self.lang)
            
            pages = []
            total_chapters = len(chapters)
            for i, ch in enumerate(chapters):
                pages.append([f"《{ch['title']}》"])
                pages.extend(ch["pages"])
                
                if i % 2 == 0:
                    self.show_loading_screen(f"{get_text('action_document_line', self.lang)}: {i+1}/{total_chapters}")
            
            self.current_pages = pages
            self.show_loading_screen(get_text("action_pages", self.lang))
            time.sleep(0.5)
        else:
            # 文本文件使用改进的分页函数
            self.current_pages = build_pages_from_file(
                book["path"], base_width, base_height, line_spacing, paragraph_spacing, progress_callback, self.lang
            )
            self.show_loading_screen(get_text("action_pages", self.lang))
            time.sleep(0.5)
        
        if not self.current_pages:
            self.current_pages = [[get_text("empty_file_or_cannot_read", self.lang)]]
        
        self.current_book = book
        self.current_page_idx = self.db.get_progress(book["id"])
        self.highlight_lines = set()
        self.display_start_line = 0
        self.display_start_col = 0
        self.record_last_read_time(book["id"])
        
        # 计算最大可显示行数和列数
        self.calculate_display_limits()

    def show_bookshelf(self):
        """显示书架界面，支持标签过滤和批量编辑"""
        max_y, max_x = self.stdscr.getmaxyx()
        # 考虑缩放因子计算可用空间
        zoom_factor = self.get_setting("font_scale", 1.0)
        books_per_page = max(1, int((max_y - 15) / zoom_factor))  # 为最近阅读区域和帮助信息留出空间
        page = 0
        search_keyword = ""
        
        # 获取最近阅读的书籍
        recent_books = self.get_recent_books(limit=3)
        
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
            
            y_offset = 2
            
            # 显示最近阅读的书籍区域
            if recent_books:
                # 计算最近阅读区域的高度
                recent_height = 4 + len(recent_books)  # 标题+分隔线+书籍列表+底部间距
                
                # 确保有足够的空间显示最近阅读区域
                if y_offset + recent_height < max_y - 10:  # 预留10行给帮助信息
                    # 绘制最近阅读区域的边框
                    self.draw_section_border(y_offset, 1, recent_height, max_x - 2, get_text("recent_books", self.lang))
                    
                    # 显示最近阅读的书籍列表
                    for i, book in enumerate(recent_books):
                        exists = "" if book["exists"] else "❌"
                        line = f" [{i+1}] {exists} {book['title'][:25]:<25} | {get_text('author', self.lang)}:{book['author'][:15]:<15}"
                        
                        # 根据文件是否存在设置颜色
                        if not book["exists"]:
                            color = curses.color_pair(3)  # 红色，表示文件不存在
                        else:
                            color = curses.color_pair(2)  # 高亮显示最近阅读的书籍
                            
                        self.stdscr.attron(color | curses.A_BOLD)
                        self.stdscr.addstr(y_offset + 2 + i, 4, line[:max_x-8])
                        self.stdscr.attroff(color | curses.A_BOLD)
                    
                    y_offset += recent_height + 1
            
            # 计算书架区域的高度
            bookshelf_height = min(books_per_page + 4, max_y - y_offset - 7)  # 预留7行给帮助信息
            
            # 绘制书架区域的边框
            self.draw_section_border(y_offset, 1, bookshelf_height, max_x - 2, get_text("bookshelf", self.lang))
            
            # 显示书架列表标题
            bookshelf_title = "📖 " + get_text("bookshelf", self.lang)
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(y_offset + 1, 4, bookshelf_title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示分隔线
            sep_line = "─" * (max_x - 6)
            self.stdscr.attron(curses.color_pair(10))
            self.stdscr.addstr(y_offset + 2, 3, sep_line)
            self.stdscr.attroff(curses.color_pair(10))
            
            # 显示书籍列表
            actual_books_per_page = min(books_per_page, bookshelf_height - 4)  # 调整实际显示的书籍数量
            current_page_books = filtered_books[start_idx:start_idx + actual_books_per_page]
            
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
                self.stdscr.addstr(y_offset + 3 + idx, 4, line[:max_x-8])
                self.stdscr.attroff(color | curses.A_BOLD)
            
            # 计算帮助信息的位置
            help_y = y_offset + bookshelf_height + 1
            
            # 确保帮助信息不会超出屏幕
            if help_y < max_y - 4:
                # 显示操作提示
                help_lines = [
                    f"[1-3] {get_text('recent_books_short', self.lang)}  [a] {get_text('add_book', self.lang)}  [d] {get_text('add_dir', self.lang)} [/] {get_text('search', self.lang)} [p] {get_text('pre_page', self.lang)} [n] {get_text('next_page', self.lang)} [t] {get_text('tag_management', self.lang)} [e] {get_text('edit_book', self.lang)} [x] {get_text('delete', self.lang)} [q] {get_text('exit', self.lang)} [Enter] {get_text('select', self.lang)}"
                ]
                
                if tag_mode:
                    help_lines.append(f"[l] {get_text('out_multype_mode', self.lang)} [{get_text('space', self.lang)}] {get_text('select_or_unselect', self.lang)} [b] {get_text('multype_tags_edit', self.lang)} [a] {get_text('select_all', self.lang)} [c] {get_text('unselect_all', self.lang)}")
                else:
                    help_lines.append(f"[l] {get_text('in_multype_mode', self.lang)}")
                
                # 确保帮助信息不会超出屏幕
                max_help_lines = max_y - help_y - 1
                help_lines_to_show = help_lines[:max_help_lines]
                
                for i, line in enumerate(help_lines_to_show):
                    self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
                    self.stdscr.addstr(help_y + i, 2, line[:max_x-4])
                    self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            # 处理数字键1-3选择最近阅读的书籍
            if c in [ord('1'), ord('2'), ord('3')] and recent_books:
                idx = c - ord('1')
                if idx < len(recent_books):
                    book = recent_books[idx]
                    if not book["exists"]:
                        # 文件不存在，提示更新路径
                        self.update_missing_book_path(book["id"])
                    else:
                        self.load_book(book)
                        book_selected = True
                        continue
            elif c == ord('a'):
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

        # 获取边框字符
        if style in ["curved", "thick", "shadow", "fancy", "minimal", "classic"]:
            # 特殊边框样式，需要四个不同的角字符
            v, h, corners = BORDER_CHARS.get(style, BORDER_CHARS["round"])
            if len(corners) >= 4:
                tl, tr, bl, br = corners[0], corners[1], corners[2], corners[3]
            else:
                tl, tr, bl, br = corners, corners, corners, corners
        else:
            v, h, c = BORDER_CHARS.get(style, BORDER_CHARS["round"])
            tl, tr, bl, br = c, c, c, c
        
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
            self.stdscr.addstr(0, 0, tl)
            self.stdscr.addstr(0, max_x-2, tr)
            self.stdscr.addstr(max_y-2, 0, bl)
            self.stdscr.addstr(max_y-2, max_x-2, br)
            self.stdscr.attroff(border_color_pair)

    def display(self):
        """显示当前页面，考虑缩放因子但保持内容完整"""
        self.stdscr.clear()
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 重新计算显示限制
        self.calculate_display_limits()
        
        # 获取缩放因子
        zoom_factor = max(0.1, self.get_setting("font_scale", 1.0))
        
        # 计算边距和填充
        margin = max(0, self.settings["margin"])
        padding = max(0, self.settings["padding"])
        
        self.draw_border()

        if not self.current_pages:
            empty_msg = f"{get_text('empty_file_or_cannot_read', self.lang)}"
            y_pos = max(0, min(max_y // 2, max_y - 1))
            x_pos = max(0, min(max_x // 2 - len(empty_msg) // 2, max_x - len(empty_msg) - 1))
            
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(y_pos, x_pos, empty_msg)
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.refresh()
            return
        
        # 获取当前页的内容（基于原始分页）
        page_lines = self.current_pages[self.current_page_idx] if self.current_pages else []
        
        # 显示标题和进度
        if self.current_pages and self.current_book:
            progress = int((self.current_page_idx+1)/len(self.current_pages)*100)
            bar_len = int(progress / 5)
            
            title_str = f"《{self.current_book['title']}》{get_text('reading_progress', self.lang)}:[{'█'*bar_len}{'-'*(20-bar_len)}] {progress:3d}%"
            y_pos = max(0, min(margin, max_y - 1))
            x_pos = max(0, min(max_x // 2 - len(title_str)//2, max_x - len(title_str) - 1))
            
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(y_pos, x_pos, title_str)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        
        # 计算可以显示的行范围
        start_line = self.display_start_line
        end_line = min(start_line + self.max_display_lines, len(page_lines))
        
        # 显示内容行
        for idx in range(start_line, end_line):
            line = page_lines[idx]
            
            # 计算实际显示位置（考虑缩放）
            y = max(0, min(margin + 2 + int((idx - start_line) * zoom_factor), max_y - 1))
            
            # 处理行内容
            safe_line = line
            
            # 处理列偏移
            if self.display_start_col > 0 and self.display_start_col < len(safe_line):
                safe_line = safe_line[self.display_start_col:]
            
            # 计算可以显示的字符数
            max_chars = min(len(safe_line), self.max_display_cols)
            safe_line = safe_line[:max_chars]
            
            # 如果需要，添加省略号
            if len(safe_line) < len(line) - self.display_start_col:
                safe_line = safe_line[:-3] + "..." if len(safe_line) > 3 else "..."
            
            # 计算列位置
            x = max(0, min(padding + 2, max_x - 1))
            
            try:
                if safe_line.startswith("《") and safe_line.endswith("》"):
                    self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    self.stdscr.addstr(y, x, safe_line)
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
                pass  # 忽略绘制错误
        
        # 显示导航提示
        self.show_navigation_hints(page_lines, max_y, max_x)
                
        # 显示状态栏
        self.show_status_bar(max_y, max_x)
        
        self.stdscr.refresh()

    def handle_input(self):
        c = self.stdscr.getch()
        # 处理终端尺寸变化
        if c == curses.KEY_RESIZE:
            self.handle_resize()
            return

        # 处理导航键
        if self.handle_navigation_keys(c):
            return
        
        # 然后处理字体快捷键
        if self.handle_font_shortcuts(c):
            return

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
        elif c == ord('f'):  # 添加字体设置快捷键
            self.show_font_settings()
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
        elif c == ord('x'):
            if self.is_reading:
                self.stop_reading()
            self.show_book_deletion()
        elif c == ord('R'):  # 大写R键 - 显示Rich统计图表
            if self.is_reading:
                self.stop_reading()
            if self.current_book:
                self.show_rich_statistics(self.current_book["id"])
            else:
                self.show_rich_statistics()

    def handle_resize(self):
        """处理终端尺寸变化"""
        self.stdscr.clear()
        curses.update_lines_cols()  # 更新行数和列数
        self.calculate_display_limits()  # 重新计算显示限制
        
        # 重绘界面
        if self.current_book:
            self.display()
        else:
            self.show_bookshelf()

    def next_page(self):
        if self.current_page_idx < len(self.current_pages)-1:
            self.current_page_idx += 1
            # 翻页后重置显示位置到顶部
            self.display_start_line = 0
            self.display_start_col = 0

    def prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            # 翻页后重置显示位置到顶部
            self.display_start_line = 0
            self.display_start_col = 0

    def save_progress(self):
        if self.current_book:
            self.db.save_progress(self.current_book["id"], self.current_page_idx)

    def show_bookmarks(self):
        """显示书签列表，支持编辑和删除"""
        bookmarks = self.db.get_bookmarks(self.current_book["id"])
        max_y, max_x = self.stdscr.getmaxyx()
        
        if not bookmarks:
            self.stdscr.clear()
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - 10, f"📑 {get_text('bookmark_list', self.lang)}")
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(2, 4, f"{get_text('none_bookmark', self.lang)}")
            self.stdscr.addstr(4, 4, f"{get_text('press_anykey_back', self.lang)}")
            self.stdscr.refresh()
            self.stdscr.getch()
            return
            
        current_selection = 0
        bookmarks_per_page = max(1, max_y - 8)
        page = 0
        
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            
            # 显示标题
            title = f"📑 {get_text('bookmark_list', self.lang)} ({page+1}/{(len(bookmarks) + bookmarks_per_page - 1) // bookmarks_per_page})"
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示书签列表
            start_idx = page * bookmarks_per_page
            end_idx = min(start_idx + bookmarks_per_page, len(bookmarks))
            
            for idx, (page_idx, comment) in enumerate(bookmarks[start_idx:end_idx]):
                line = f"{start_idx+idx+1:02d}. {get_text('page_no', self.lang).format(page=f'{page_idx+1}')}: {comment}"
                if idx == current_selection:
                    self.stdscr.attron(curses.color_pair(2) | curses.A_REVERSE)
                    self.stdscr.addstr(idx+2, 4, line[:max_x-8])
                    self.stdscr.attroff(curses.color_pair(2) | curses.A_REVERSE)
                else:
                    self.stdscr.addstr(idx+2, 4, line[:max_x-8])
            
            # 显示操作提示
            help_text = f"[Enter] {get_text('Jump', self.lang)} [e] {get_text('edit', self.lang)} [d] {get_text('delete', self.lang)} [q] {get_text('back', self.lang)} [n] {get_text('next_page', self.lang)} [p] {get_text('pre_page', self.lang)}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(max_y-3, 4, help_text[:max_x-8])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c == curses.KEY_UP:
                if current_selection > 0:
                    current_selection -= 1
                elif page > 0:
                    page -= 1
                    current_selection = bookmarks_per_page - 1
            elif c == curses.KEY_DOWN:
                if current_selection < min(bookmarks_per_page, len(bookmarks) - page * bookmarks_per_page) - 1:
                    current_selection += 1
                elif page < (len(bookmarks) - 1) // bookmarks_per_page:
                    page += 1
                    current_selection = 0
            elif c == ord('n') and page < (len(bookmarks) - 1) // bookmarks_per_page:
                page += 1
                current_selection = 0
            elif c == ord('p') and page > 0:
                page -= 1
                current_selection = 0
            elif c in (10, 13):  # 回车键 - 跳转到书签
                selected_bookmark = bookmarks[start_idx + current_selection]
                self.current_page_idx = selected_bookmark[0]
                # 跳转到书签后重置显示位置到顶部
                self.display_start_line = 0
                self.display_start_col = 0
                break
            elif c == ord('e'):  # 编辑书签
                selected_bookmark = bookmarks[start_idx + current_selection]
                self.edit_bookmark(selected_bookmark)
                # 刷新书签列表
                bookmarks = self.db.get_bookmarks(self.current_book["id"])
            elif c == ord('d'):  # 删除书签
                selected_bookmark = bookmarks[start_idx + current_selection]
                self.delete_bookmark(selected_bookmark)
                # 刷新书签列表
                bookmarks = self.db.get_bookmarks(self.current_book["id"])
                # 如果当前页没有书签了，且不是第一页，则回到上一页
                if not bookmarks and page > 0:
                    page -= 1
                # 调整当前选中行，确保不越界
                if current_selection >= len(bookmarks) - page * bookmarks_per_page:
                    current_selection = max(0, len(bookmarks) - page * bookmarks_per_page - 1)

    def edit_bookmark(self, bookmark):
        """编辑书签"""
        page_idx, comment = bookmark
        new_comment = input_box(self.stdscr, f"{get_text('edit_bookmark_comment', self.lang)}: ", maxlen=100, default=comment)
        if new_comment is not None:
            # 获取书签ID
            all_bookmarks = self.db.get_bookmarks(self.current_book["id"])
            bookmark_id = None
            for i, (bm_page, bm_comment) in enumerate(all_bookmarks):
                if bm_page == page_idx and bm_comment == comment:
                    # 假设书签ID是行号+1（因为书签列表从1开始）
                    bookmark_id = i + 1
                    break
            
            if bookmark_id:
                # 更新书签
                self.db.update_bookmark(bookmark_id, page_idx, new_comment)

    def delete_bookmark(self, bookmark):
        """删除书签"""
        page_idx, comment = bookmark
        
        # 确认删除
        confirm = input_box(self.stdscr, f"{get_text('confirm_delete_bookmark', self.lang)} '{comment}'? (y/N): ", maxlen=1)
        if confirm and confirm.lower() == 'y':
            # 获取书签ID
            all_bookmarks = self.db.get_bookmarks(self.current_book["id"])
            bookmark_id = None
            for i, (bm_page, bm_comment) in enumerate(all_bookmarks):
                if bm_page == page_idx and bm_comment == comment:
                    # 假设书签ID是行号+1（因为书签列表从1开始）
                    bookmark_id = i + 1
                    break
            
            if bookmark_id:
                # 删除书签
                self.db.delete_bookmark(bookmark_id)

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
            
            # 如果有匹配项，滚动到第一个匹配项
            if self.highlight_lines:
                first_match = min(self.highlight_lines)
                if first_match > self.max_display_lines:
                    self.display_start_line = first_match - self.max_display_lines // 2
                else:
                    self.display_start_line = 0

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
            ("width", f"{get_text('width', self.lang)}", int, 40, 300),
            ("height", f"{get_text('height', self.lang)}", int, 10, 80),
            ("theme", get_text("input_theme", self.lang), str, ["dark", "light", "eye", "midnight", "sepia", "forest", "amethyst", "ocean", "crimson", "slate", "transparent-dark", "transparent-light", "transparent-blue"]),
            ("lang", get_text("input_lang", self.lang), str, ["zh", "en"]),
            ("font_color", get_text("input_font_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("bg_color", get_text("input_bg_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white", "transparent"]),
            ("border_style", get_text("input_border_style", self.lang), str, ["round","double","single","bold","dotted","dashed","curved","thick","shadow","fancy","minimal","classic","none"]),
            ("border_color", get_text("input_border_color", self.lang), str, ["black","red","green","yellow","blue","magenta","cyan","white"]),
            ("line_spacing", f"{get_text('line_spacing', self.lang)}", int, 1, 5),
            ("auto_page_interval", f"{get_text('auto_pager_sec', self.lang)}", int, 1, 60),
            ("speech_rate", f"{get_text('speech_rate', self.lang)}", int, 50, 400),  # 添加语速设置
            ("status_bar", f"{get_text('statusbar_switch', self.lang)}", bool, [0, 1]),
            ("remind_interval", get_text("input_remind_interval", self.lang), int, 0, 120),
            ("font_settings", get_text("font_settings", self.lang), "menu", []),  # 添加字体设置菜单选项
        ]
        curr = 0
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - 6, f"⚙️ {get_text('setting_page', self.lang)}")
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
            self.stdscr.addstr(len(options)+4, 4, f"{get_text('enter_confirm_q_back', self.lang)}")
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
                if key == "font_settings":
                    self.show_font_settings()
                    continue
                newval = input_box(self.stdscr, f"{desc}{get_text('new_val', self.lang)}: ", maxlen=20)
                valid = False
                if typ == int:
                    try:
                        v = int(newval)
                        if len(meta)==2 and (meta[0] <= v <= meta[1]):
                            self.settings[key] = v
                            valid = True
                            # 如果是语速设置，立即应用
                            if key == "speech_rate":
                                self.set_speech_rate(v)
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
        # 构建帮助内容的所有行
        categories = [
            {
                "title": f"📖 {get_text('help_t1', self.lang)}",
                "items": [
                    ("←/→/PgUp/PgDn/j/k", f"{get_text('turn_page', self.lang)}"),
                    ("a", f"{get_text('help_t1_a', self.lang)}"),
                    ("g", f"{get_text('help_t1_g', self.lang)}"),
                    ("/", f"{get_text('help_t1_line', self.lang)}")
                ]
            },
            {
                "title": f"🔖 {get_text('help_t2', self.lang)}",
                "items": [
                    ("b", f"{get_text('help_t2_b', self.lang)}"),
                    ("B", f"{get_text('help_t2_bigb', self.lang)}")
                ]
            },
            {
                "title": f"🎵 {get_text('help_t3', self.lang)}",
                "items": [
                    ("r", f"{get_text('help_t3_r', self.lang)}")
                ]
            },
            {
                "title": f"📚 {get_text('help_t4', self.lang)}",
                "items": [
                    ("m", f"{get_text('help_t4_m', self.lang)}"),
                    ("s", f"{get_text('help_t4_s', self.lang)}")
                ]
            },
            {
                "title": f"📊 {get_text('help_t5', self.lang)}",
                "items": [
                    ("t", f"{get_text('help_t5_t', self.lang)}"),
                    ("T", f"{get_text('help_t5_bigt', self.lang)}"),
                    ("R", f"{get_text('help_t5_bigr', self.lang)}")
                ]
            },
            {
                "title": f"👔 {get_text('help_t6', self.lang)}",
                "items": [
                    (f"{get_text('help_t6_key_space', self.lang)}", f"{get_text('help_t6_key_space_desc', self.lang)}"),
                    (f"{get_text('help_t6_key_space_enter', self.lang)}", f"{get_text('help_t6_key_space_enter_desc', self.lang)}"),
                    ("↑↓", f"{get_text('help_t6_key_move_desc', self.lang)}")
                ]
            },
            {
                "title": f"⚙️ {get_text('help_t7', self.lang)}",
                "items": [
                    ("?", f"{get_text('help_t7_ask', self.lang)}"),
                    ("q", f"{get_text('help_t7_q', self.lang)}")
                ]
            },
            {
                "title": f"🎨 {get_text('font_settings', self.lang)}",
                "items": [
                    ("f", get_text('font_settings', self.lang)),
                    ("+/-", f"{get_text('increase', self.lang)}/{get_text('decrease', self.lang)} {get_text('font_scale', self.lang)}"),
                    ("[/]", f"{get_text('increase', self.lang)}/{get_text('decrease', self.lang)} {get_text('line_spacing_setting', self.lang)}")
                ]
            }
        ]
        
        # 计算总行数
        total_lines = 0
        for category in categories:
            total_lines += 1  # 分类标题
            total_lines += len(category["items"])  # 分类项目
            total_lines += 1  # 分类之间的间隔
        
        # 初始化滚动位置
        scroll_offset = 0
        max_y, max_x = self.stdscr.getmaxyx()
        available_lines = max_y - 6  # 预留顶部和底部空间
        
        while True:
            max_y, max_x = self.stdscr.getmaxyx()
            available_lines = max_y - 6  # 重新计算可用行数
            
            self.stdscr.clear()
            
            # 绘制边框
            self.draw_border()
            
            # 标题
            title = f"💡 {get_text('help_center', self.lang)}"
            if total_lines > available_lines:
                title += f" ({scroll_offset//available_lines + 1}/{(total_lines + available_lines - 1) // available_lines})"
            
            title_y = 2
            title_x = max(0, min(max_x // 2 - len(title) // 2, max_x - len(title) - 1))
            
            self.safe_addstr(self.stdscr, title_y, title_x, title, curses.color_pair(4) | curses.A_BOLD)
            
            # 显示当前可见的帮助内容
            y_pos = 4
            current_line = 0
            
            for category in categories:
                # 检查是否在当前可见范围内
                if current_line >= scroll_offset and current_line < scroll_offset + available_lines:
                    self.safe_addstr(self.stdscr, y_pos, 5, category["title"], curses.color_pair(2) | curses.A_BOLD)
                    y_pos += 1
                
                current_line += 1
                
                # 显示分类中的项目
                for key, desc in category["items"]:
                    # 检查是否在当前可见范围内
                    if current_line >= scroll_offset and current_line < scroll_offset + available_lines:
                        key_part = f"[{key}]"
                        desc_part = f" {desc}"
                        
                        self.safe_addstr(self.stdscr, y_pos, 7, key_part, curses.color_pair(3) | curses.A_BOLD)
                        self.safe_addstr(self.stdscr, y_pos, 7 + len(key_part), desc_part, curses.color_pair(1))
                        
                        y_pos += 1
                    
                    current_line += 1
                
                # 检查分类之间的间隔是否在当前可见范围内
                if current_line >= scroll_offset and current_line < scroll_offset + available_lines:
                    y_pos += 1
                
                current_line += 1
            
            # 底部提示
            tip = f"{get_text('press_anykey_back_reading', self.lang)}"
            if total_lines > available_lines:
                tip = f"↑↓: {get_text('turn_page', self.lang)} | Q: {get_text('back', self.lang)}"
            
            tip_y = max(0, min(max_y - 3, max_y - 1))
            tip_x = max(0, min(max_x // 2 - len(tip) // 2, max_x - len(tip) - 1))
            
            self.safe_addstr(self.stdscr, tip_y, tip_x, tip, curses.color_pair(1) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            # 处理输入
            c = self.stdscr.getch()
            
            # 上下键滚动
            if c == curses.KEY_UP:
                scroll_offset = max(0, scroll_offset - 1)
            elif c == curses.KEY_DOWN:
                scroll_offset = min(total_lines - available_lines, scroll_offset + 1)
            elif c == curses.KEY_PPAGE:  # Page Up
                scroll_offset = max(0, scroll_offset - available_lines)
            elif c == curses.KEY_NPAGE:  # Page Down
                scroll_offset = min(total_lines - available_lines, scroll_offset + available_lines)
            elif c == curses.KEY_HOME:  # Home键回到顶部
                scroll_offset = 0
            elif c == curses.KEY_END:  # End键到底部
                scroll_offset = max(0, total_lines - available_lines)
            elif c == ord('q') or c == ord('Q'):
                break
            elif c == curses.KEY_RESIZE:
                # 终端尺寸变化，重新计算
                continue

    def show_stats(self):
        """显示书籍阅读统计，增加查看Rich图表的选项"""
        stats = self.stats.get_book_stats(self.current_book["id"])
        max_y, max_x = self.stdscr.getmaxyx()
        self.stdscr.clear()
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(0, max_x // 2 - 6, f"📊 {get_text('stats', self.lang)}")
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.addstr(2, 4, f"{get_text('novel', self.lang)}：{self.current_book['title']}")
        self.stdscr.addstr(3, 4, f"{get_text('stats_time', self.lang)}：{stats['total_time']//60} {get_text('minutes', self.lang)}")
        self.stdscr.addstr(4, 4, f"{get_text('stats_days', self.lang)}：{stats['days']} {get_text('day', self.lang)}")
        self.stdscr.addstr(6, 4, f"{get_text('stats_daily', self.lang)}：")
        for idx, (date, sec) in enumerate(stats["records"][:max(max_y-12, 0)]):
            if idx + 7 < max_y:
                try:
                    self.stdscr.addstr(7+idx, 6, f"{date}: {sec//60} {get_text('minutes', self.lang)}")
                except curses.error:
                    pass
        
        # 添加查看Rich图表的提示（仅在Rich可用时显示）
        if RICH_AVAILABLE:
            prompt = get_text('press_anykey_back_r_rich', self.lang)
        else:
            prompt = get_text('press_anykey_back', self.lang)
        
        if max_y - 4 >= 0:
            try:
                self.stdscr.addstr(max_y-4, 4, prompt[:max_x-8])
            except curses.error:
                pass
        
        self.stdscr.refresh()
        
        c = self.stdscr.getch()
        if c == ord('R') and RICH_AVAILABLE:
            self.show_rich_statistics(self.current_book["id"])

    def show_all_books_stats(self):
        """显示所有书籍统计，增加查看Rich图表的选项"""
        all_stats = self.stats.get_all_books_stats()
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
                if y < max_y:
                    book_id = book["id"]
                    stat = all_stats.get(book_id, {"total_time":0, "days":0})
                    line = f"{book['title'][:20]:<20} | {stat['total_time']//60:>4} {get_text('minutes', self.lang)} | {stat['days']} {get_text('day', self.lang)}"
                    try:
                        self.stdscr.addstr(y, 4, line[:max_x-8])
                    except curses.error:
                        pass
                    y += 1
            
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            page_info = f"{get_text('page_no', self.lang).format(page=f'{page+1}/{total_pages}')} [n] {get_text('next_page', self.lang)} [p] {get_text('pre_page', self.lang)} [q] {get_text('back', self.lang)}"
            
            if max_y - 4 >= 0:
                try:
                    self.stdscr.addstr(max_y-4, 4, page_info[:max_x-8])
                except curses.error:
                    pass
            
            # 添加查看Rich图表的提示（仅在Rich可用时显示）
            if RICH_AVAILABLE and max_y - 3 >= 0:
                try:
                    self.stdscr.addstr(max_y-3, 4, get_text('r_view_all_charts', self.lang))
                except curses.error:
                    pass
            
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c == ord('n') and page < total_pages - 1:
                page += 1
            elif c == ord('p') and page > 0:
                page -= 1
            elif c == ord('R') and RICH_AVAILABLE:
                self.show_rich_statistics()

    def toggle_boss_mode(self):
        """切换老板键模式 - 增强版"""
        self.boss_mode = not self.boss_mode
        if self.boss_mode:
            # 进入老板键模式
            self.terminal_input = ""
            self.terminal_output = [
                f"{get_text('terminal_mode_started', self.lang)}", 
                f"{get_text('current_dir', self.lang)}: {os.getcwd()}",
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

    def set_speech_rate(self, rate):
        """设置朗读语速"""
        self.engine.setProperty('rate', rate)
        self.settings["speech_rate"] = rate
        self.settings.save()

    def show_detailed_stats(self, book_id=None):
        """显示详细的阅读统计图表"""
        max_y, max_x = self.stdscr.getmaxyx()
        current_view = "daily"  # daily, weekly, monthly
        time_unit = 0  # 0: 分钟, 1: 小时
        
        # 获取书籍标题
        if book_id:
            book = self.bookshelf.get_book_by_id(book_id)
            title = f"📊 {book['title']} - {get_text('stats', self.lang)}"
        else:
            title = f"📊 {get_text('stats_all', self.lang)}"
        
        while True:
            self.stdscr.clear()
            
            # 显示标题
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 获取统计数据
            if current_view == "daily":
                stats = self.stats.get_daily_stats(book_id)
                view_title = get_text('daily_stats', self.lang)
            elif current_view == "weekly":
                stats = self.stats.get_weekly_stats(book_id)
                view_title = get_text('weekly_stats', self.lang)
            else:  # monthly
                stats = self.stats.get_monthly_stats(book_id)
                view_title = get_text('monthly_stats', self.lang)
            
            # 转换时间单位
            if time_unit == 0:  # 分钟
                stats_display = [(period, seconds // 60) for period, seconds in stats]
                unit = get_text('minutes', self.lang)
            else:  # 小时
                stats_display = [(period, seconds // 3600) for period, seconds in stats]
                unit = get_text('hours', self.lang)
            
            # 显示图表
            self.display_stats_chart(stats_display, view_title, unit, max_y, max_x)
            
            # 显示操作提示
            help_text = f"[d] {get_text('day_view', self.lang)} [w] {get_text('week_view', self.lang)} [m] {get_text('month_view', self.lang)} [u] {get_text('switch_unit', self.lang)}({unit}) [q] {get_text('back', self.lang)}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(max_y-2, 4, help_text[:max_x-8])
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c == ord('d'):
                current_view = "daily"
            elif c == ord('w'):
                current_view = "weekly"
            elif c == ord('m'):
                current_view = "monthly"
            elif c == ord('u'):
                time_unit = 1 - time_unit  # 切换单位

    def display_stats_chart(self, stats, title, unit, max_y, max_x):
        """显示统计图表 - 修复位置计算错误"""
        if not stats:
            # 没有数据时显示提示
            no_data_msg = get_text('none_stats', self.lang)
            try:
                self.stdscr.addstr(max_y // 2, max_x // 2 - len(no_data_msg) // 2, no_data_msg)
            except curses.error:
                pass  # 忽略绘制错误
            return
        
        # 计算图表区域大小，确保不超出屏幕范围
        chart_height = min(max(5, max_y - 10), max_y - 6)  # 图表高度
        chart_width = min(max(20, max_x - 20), max_x - 8)  # 图表宽度
        
        # 找出最大值用于缩放
        max_value = max(value for _, value in stats) if stats else 1
        if max_value == 0:
            max_value = 1  # 避免除以零
        
        # 显示标题
        try:
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(2, max(0, min(max_x // 2 - len(title) // 2, max_x - len(title) - 1)), title)
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass
        
        # 显示图表
        chart_top = 4
        chart_left = 4
        
        # 确保不超出屏幕范围
        if chart_top + chart_height >= max_y or chart_left + chart_width >= max_x:
            return  # 屏幕太小，无法显示图表
        
        # 绘制Y轴和刻度
        y_axis_width = 8
        for i in range(chart_height):
            y_pos = chart_top + chart_height - i - 1
            if y_pos >= max_y:
                continue  # 跳过超出屏幕的行
                
            if i % max(1, chart_height // 5) == 0:  # 每1/5高度显示一个刻度
                value = int(max_value * i / chart_height)
                value_str = f"{value:4d} {unit}"
                try:
                    x_pos = max(0, min(chart_left - len(value_str) - 1, max_x - len(value_str) - 1))
                    self.stdscr.addstr(y_pos, x_pos, value_str)
                    self.stdscr.addstr(y_pos, chart_left, "┤")
                except curses.error:
                    pass
            else:
                try:
                    self.stdscr.addstr(y_pos, chart_left, "│")
                except curses.error:
                    pass
        
        # 绘制X轴
        try:
            x_axis_y = chart_top + chart_height
            if x_axis_y < max_y:
                self.stdscr.addstr(x_axis_y, chart_left, "└")
                for i in range(min(chart_width, max_x - chart_left - 1)):
                    self.stdscr.addstr(x_axis_y, chart_left + i + 1, "─")
        except curses.error:
            pass
        
        # 绘制数据条
        bar_width = max(1, min(3, chart_width // max(1, len(stats)) - 1))
        for i, (period, value) in enumerate(stats):
            if i * (bar_width + 1) >= chart_width:
                break  # 超出图表宽度
            
            # 计算条形高度
            bar_height = int(value * chart_height / max_value)
            
            # 绘制条形
            bar_left = chart_left + 1 + i * (bar_width + 1)
            for j in range(bar_height):
                y_pos = chart_top + chart_height - j - 1
                if y_pos >= max_y:
                    continue  # 跳过超出屏幕的行
                    
                for k in range(bar_width):
                    try:
                        x_pos = bar_left + k
                        if x_pos < max_x:
                            self.stdscr.addstr(y_pos, x_pos, "█")
                    except curses.error:
                        pass
            
            # 显示周期标签（每隔几个显示一个，避免重叠）
            if i % max(1, len(stats) // 10) == 0 or i == len(stats) - 1:
                label_y = chart_top + chart_height + 1
                if label_y >= max_y:
                    continue  # 跳过超出屏幕的行
                    
                label = period
                if len(label) > bar_width + 2:
                    label = label[:bar_width + 2] + ".."
                try:
                    x_pos = bar_left + bar_width // 2 - len(label) // 2
                    if x_pos >= 0 and x_pos + len(label) < max_x:
                        self.stdscr.addstr(label_y, x_pos, label)
                except curses.error:
                    pass
        
        # 显示统计摘要
        total_value = sum(value for _, value in stats) if stats else 0
        avg_value = total_value / len(stats) if stats else 0
        
        summary_y = chart_top + chart_height + 3
        if summary_y < max_y:
            summary = f"{get_text('total', self.lang)}: {total_value} {unit} | {get_text('avg', self.lang)}: {avg_value:.1f} {unit}/{get_text('cycle', self.lang)} | {get_text('cycle_count', self.lang)}: {len(stats)}"
            try:
                x_pos = max(0, min(max_x // 2 - len(summary) // 2, max_x - len(summary) - 1))
                self.stdscr.addstr(summary_y, x_pos, summary)
            except curses.error:
                pass

    def show_rich_statistics(self, book_id=None):
        """显示Rich统计图表"""
        if not RICH_AVAILABLE:
            # 如果Rich不可用，显示错误信息
            max_y, max_x = self.stdscr.getmaxyx()
            error_msg = "No module named Rich, Install it run : pip install rich"
            try:
                self.stdscr.addstr(max_y // 2, max_x // 2 - len(error_msg) // 2, error_msg)
                self.stdscr.refresh()
                self.stdscr.getch()
            except curses.error:
                pass
            return
        
        # 退出curses模式
        curses.endwin()
        
        try:
            # 获取统计数据 - 添加错误处理
            try:
                daily_stats = self.stats.get_daily_stats_for_chart(book_id)
            except AttributeError:
                daily_stats = []
                # print("警告: get_daily_stats_for_chart 方法不存在")
            
            try:
                weekly_stats = self.stats.get_weekly_stats_for_chart(book_id)
            except AttributeError:
                weekly_stats = []
                # print("警告: get_weekly_stats_for_chart 方法不存在")
            
            try:
                monthly_stats = self.stats.get_monthly_stats_for_chart(book_id)
            except AttributeError:
                monthly_stats = []
                # print("警告: get_monthly_stats_for_chart 方法不存在")
            
            # 获取书籍标题
            book_title = None
            if book_id:
                book = self.bookshelf.get_book_by_id(book_id)
                if book:
                    book_title = book["title"]
            
            # 使用Rich显示图表
            self.display_rich_chart(daily_stats, weekly_stats, monthly_stats, book_title)
            
        except Exception as e:
            # print(f"显示统计图表时出错: {e}")
            import traceback
            traceback.print_exc()  # 打印完整的错误堆栈
            input(f"{get_text('press_enter_to_back', self.lang)}...")
        
        # 重新初始化curses
        self.stdscr = curses.initscr()
        curses.cbreak()
        curses.noecho()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        
        # 重新初始化颜色
        init_colors(theme=self.settings["theme"], settings=self.settings)

    def display_rich_chart(self, daily_stats, weekly_stats, monthly_stats, book_title=None):
        """使用Rich显示统计图表"""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        from rich.text import Text
        from rich.layout import Layout
        
        console = Console()
        
        # 创建布局
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=7)
        )
        
        layout["main"].split_row(
            Layout(name="daily", ratio=1),
            Layout(name="weekly", ratio=1),
            Layout(name="monthly", ratio=1)
        )
        
        # 头部标题
        title = f"📊 {get_text('stats', self.lang)}"
        if book_title:
            title += f" - {book_title}"
        
        layout["header"].update(
            Panel(Text(title, justify="center", style="bold yellow"), style="on blue")
        )
        
        # 每日统计
        daily_table = Table(title=get_text('nearly_ten_days', self.lang), box=box.ROUNDED, show_header=True, header_style="bold magenta")
        daily_table.add_column(get_text('date', self.lang), style="dim", width=12)
        daily_table.add_column(get_text('reading_time_minutes', self.lang), justify="right")
        daily_table.add_column(get_text('chart', self.lang), width=30)
        
        if daily_stats and len(daily_stats) > 0:
            max_daily = max(minutes for _, minutes in daily_stats[-10:]) if daily_stats[-10:] else 1
            for date, minutes in daily_stats[-10:]:
                bar_length = int(minutes * 30 / max_daily)
                bar = "█" * bar_length + "░" * (30 - bar_length)
                daily_table.add_row(date, f"{minutes}", f"{bar} {minutes}{get_text('minutes', self.lang)}")
        else:
            daily_table.add_row(get_text('none_data', self.lang), "0", get_text('none_data', self.lang))
        
        layout["daily"].update(daily_table)
        
        # 每周统计
        weekly_table = Table(title=get_text('nearly_eight_weeks', self.lang), box=box.ROUNDED, show_header=True, header_style="bold magenta")
        weekly_table.add_column(get_text('week', self.lang), style="dim", width=12)
        weekly_table.add_column(get_text('reading_time_minutes', self.lang), justify="right")
        weekly_table.add_column(get_text('chart', self.lang), width=30)
        
        if weekly_stats and len(weekly_stats) > 0:
            max_weekly = max(minutes for _, minutes in weekly_stats[-8:]) if weekly_stats[-8:] else 1
            for week, minutes in weekly_stats[-8:]:
                bar_length = int(minutes * 30 / max_weekly)
                bar = "█" * bar_length + "░" * (30 - bar_length)
                weekly_table.add_row(week, f"{minutes}", f"{bar} {minutes}{get_text('minutes', self.lang)}")
        else:
            weekly_table.add_row(get_text('none_data', self.lang), "0", get_text('none_data', self.lang))
        
        layout["weekly"].update(weekly_table)
        
        # 每月统计
        monthly_table = Table(title=get_text('nearly_tweleve_month', self.lang), box=box.ROUNDED, show_header=True, header_style="bold magenta")
        monthly_table.add_column(get_text('month', self.lang), style="dim", width=12)
        monthly_table.add_column(get_text('reading_time_minutes', self.lang), justify="right")
        monthly_table.add_column(get_text('chart', self.lang), width=30)
        
        if monthly_stats and len(monthly_stats) > 0:
            max_monthly = max(minutes for _, minutes in monthly_stats[-12:]) if monthly_stats[-12:] else 1
            for month, minutes in monthly_stats[-12:]:
                bar_length = int(minutes * 30 / max_monthly)
                bar = "█" * bar_length + "░" * (30 - bar_length)
                monthly_table.add_row(month, f"{minutes}", f"{bar} {minutes}{get_text('minutes', self.lang)}")
        else:
            monthly_table.add_row(get_text('none_data', self.lang), "0", get_text('none_data', self.lang))
        
        layout["monthly"].update(monthly_table)
        
        # 底部摘要
        if daily_stats and len(daily_stats) > 0:
            total_minutes = sum(minutes for _, minutes in daily_stats)
            avg_minutes = total_minutes / len(daily_stats) if daily_stats else 0
            max_minutes = max(minutes for _, minutes in daily_stats) if daily_stats else 0
            min_minutes = min(minutes for _, minutes in daily_stats) if daily_stats else 0
            
            summary_text = Text()
            summary_text.append(f"{get_text('total', self.lang)}: {total_minutes} {get_text('minutes', self.lang)}\n", style="bold")
            summary_text.append(f"{get_text('avg', self.lang)}: {avg_minutes:.1f} {get_text('minutes', self.lang)}/天\n")
            summary_text.append(f"{get_text('highest', self.lang)}: {max_minutes} {get_text('minutes', self.lang)}\n")
            summary_text.append(f"{get_text('lowest', self.lang)}: {min_minutes} {get_text('minutes', self.lang)}\n")
            summary_text.append(f"{get_text('days', self.lang)}: {len(daily_stats)}")
            
            summary_panel = Panel(summary_text, title=get_text('every_day_stats', self.lang))
        else:
            summary_panel = Panel(get_text('none_data', self.lang), title=get_text('every_day_stats', self.lang))
        
        layout["footer"].update(summary_panel)
        
        # 显示所有内容
        console.print(layout)
        
        # 显示操作提示
        console.print(f"\n{get_text('press_anykey_back_reading', self.lang)}...", style="bold dim")
        input()

    def get_help_list(self):
        """返回当前语言的帮助键列表"""
        help_items = [
            get_text("help_key_page", self.lang),
            get_text("help_key_auto_page", self.lang),
            get_text("help_key_add_bookmark", self.lang),
            get_text("help_key_bookmark_list", self.lang),
            get_text("help_key_jump_page", self.lang),
            get_text("help_key_bookshelf", self.lang),
            get_text("help_key_settings", self.lang),
            get_text("help_key_read_aloud", self.lang),
            get_text("help_key_search", self.lang),
            get_text("help_key_help", self.lang),
            get_text("help_key_exit", self.lang),
            get_text("help_key_stats", self.lang),
            get_text("help_key_all_stats", self.lang),
            get_text("help_key_delete_book", self.lang),
            get_text("help_key_boss_key", self.lang),
            f"r:{get_text('reset_position', self.lang)}"  # 添加重置功能的说明
        ]
        return help_items

    def record_last_read_time(self, book_id):
        """记录书籍的最后阅读时间"""
        if book_id:
            # 获取当前时间戳
            current_time = int(time.time())
            # 更新数据库中的最后阅读时间
            c = self.db.conn.cursor()
            c.execute("UPDATE books SET last_read_time=? WHERE id=?", (current_time, book_id))
            self.db.conn.commit()

    def get_recent_books(self, limit=3):
        """获取最近阅读的书籍"""
        c = self.db.conn.cursor()
        c.execute("SELECT id, path, title, author, type, tags FROM books WHERE last_read_time IS NOT NULL ORDER BY last_read_time DESC LIMIT ?", (limit,))
        books = c.fetchall()
        
        result = []
        for id_, path, title, author, book_type, tags in books:
            exists = os.path.exists(path)
            # 获取书籍的标签列表
            book_tags = self.db.get_book_tags(id_)
            tag_names = [tag[1] for tag in book_tags]
            
            result.append({
                "id": id_,
                "path": path,
                "title": title,
                "author": author,
                "type": book_type,
                "tags": tag_names,
                "exists": exists,
                "recent": True  # 标记为最近阅读的书籍
            })
        return result

    def draw_section_border(self, top, left, height, width, title=None):
        """绘制一个区域的边框"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 确保不超出屏幕范围
        if top + height >= max_y or left + width >= max_x:
            return
        
        # 绘制边框
        v, h, c = BORDER_CHARS.get("round", BORDER_CHARS["round"])
        border_color_pair = color_pair_idx(10, self.settings["border_color"], self.settings["bg_color"])
        
        # 绘制垂直边框
        for i in range(top + 1, top + height - 1):
            self.stdscr.attron(border_color_pair)
            try:
                self.stdscr.addstr(i, left, v)
                self.stdscr.addstr(i, left + width - 1, v)
            except curses.error:
                pass
            self.stdscr.attroff(border_color_pair)
        
        # 绘制水平边框
        for i in range(left + 1, left + width - 1):
            self.stdscr.attron(border_color_pair)
            try:
                self.stdscr.addstr(top, i, h)
                self.stdscr.addstr(top + height - 1, i, h)
            except curses.error:
                pass
            self.stdscr.attroff(border_color_pair)
        
        # 绘制角落
        self.stdscr.attron(border_color_pair)
        try:
            self.stdscr.addstr(top, left, c)
            self.stdscr.addstr(top, left + width - 1, c)
            self.stdscr.addstr(top + height - 1, left, c)
            self.stdscr.addstr(top + height - 1, left + width - 1, c)
        except curses.error:
            pass
        self.stdscr.attroff(border_color_pair)
        
        # 绘制标题（如果有）
        if title:
            title_str = f" {title} "
            try:
                self.stdscr.attron(border_color_pair | curses.A_BOLD)
                self.stdscr.addstr(top, left + 2, title_str)
                self.stdscr.attroff(border_color_pair | curses.A_BOLD)
            except curses.error:
                pass

    def get_effective_width(self):
        """获取有效的显示宽度，考虑缩放因子"""
        base_width = self.get_setting("width", 200)
        zoom_factor = self.get_setting("font_scale", 1.0)
        return max(10, int(base_width * zoom_factor))

    def get_effective_height(self):
        """获取有效的显示高度，考虑缩放因子"""
        base_height = self.get_setting("height", 50)
        zoom_factor = self.get_setting("font_scale", 1.0)
        return max(5, int(base_height * zoom_factor))

    def show_font_settings(self):
        """显示字体设置主界面"""
        options = [
            ("presets", get_text("font_presets", self.lang)),
            ("scale", get_text("font_scale", self.lang)),
            ("line_spacing", get_text("line_spacing_setting", self.lang)),
            ("paragraph_spacing", get_text("paragraph_spacing_setting", self.lang)),
            ("auto_adjust", get_text("auto_adjust", self.lang)),
        ]
        
        current_selection = 0
        
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            
            title = get_text("font_settings", self.lang)
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示当前设置值
            scale = getattr(self.settings, "font_scale", 1.0)
            line_spacing = getattr(self.settings, "line_spacing", 1)
            paragraph_spacing = getattr(self.settings, "paragraph_spacing", 1)
            
            current_settings = f"{get_text('font_scale', self.lang)}: {scale:.1f}x | {get_text('line_spacing_setting', self.lang)}: {line_spacing} | {get_text('paragraph_spacing_setting', self.lang)}: {paragraph_spacing}"
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(1, max_x // 2 - len(current_settings) // 2, current_settings)
            self.stdscr.attroff(curses.color_pair(3))
            
            # 显示选项
            for idx, (key, desc) in enumerate(options):
                line = f"{'→' if idx == current_selection else ' '} {desc}"
                color = curses.color_pair(2) if idx == current_selection else curses.color_pair(1)
                self.stdscr.attron(color)
                self.stdscr.addstr(idx + 3, 4, line)
                self.stdscr.attroff(color)
            
            help_text = f"[↑↓]{get_text('select', self.lang)} [Enter]{get_text('confirm', self.lang)} [q]{get_text('back', self.lang)}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(len(options) + 5, 4, help_text)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c in (curses.KEY_UP, ord('k')):
                current_selection = (current_selection - 1) % len(options)
            elif c in (curses.KEY_DOWN, ord('j')):
                current_selection = (current_selection + 1) % len(options)
            elif c in (curses.KEY_ENTER, 10, 13):
                selected_option = options[current_selection][0]
                
                if selected_option == "presets":
                    self.show_font_presets()
                elif selected_option == "scale":
                    self.adjust_font_scale()
                elif selected_option == "line_spacing":
                    self.adjust_line_spacing()
                elif selected_option == "paragraph_spacing":
                    self.adjust_paragraph_spacing()
                elif selected_option == "auto_adjust":
                    self.auto_adjust_font_settings()

    def show_font_presets(self):
        """显示字体预设方案界面"""
        presets = [
            {
                "name": get_text("font_preset_small", self.lang),
                "scale": 0.8,
                "line_spacing": 0,
                "paragraph_spacing": 0
            },
            {
                "name": get_text("font_preset_standard", self.lang),
                "scale": 1.0,
                "line_spacing": 1,
                "paragraph_spacing": 1
            },
            {
                "name": get_text("font_preset_large", self.lang),
                "scale": 1.3,
                "line_spacing": 1,
                "paragraph_spacing": 1
            },
            {
                "name": get_text("font_preset_comfort", self.lang),
                "scale": 1.1,
                "line_spacing": 2,
                "paragraph_spacing": 2
            },
            {
                "name": get_text("font_preset_compact", self.lang),
                "scale": 0.9,
                "line_spacing": 0,
                "paragraph_spacing": 0
            }
        ]
        
        current_selection = 0
        
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            
            title = get_text("font_presets", self.lang)
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示预设选项
            for idx, preset in enumerate(presets):
                line = f"{'→' if idx == current_selection else ' '} {preset['name']}"
                color = curses.color_pair(2) if idx == current_selection else curses.color_pair(1)
                self.stdscr.attron(color)
                self.stdscr.addstr(idx + 2, 4, line)
                self.stdscr.attroff(color)
                
                # 显示预设的详细参数
                details = f"  {get_text('font_scale', self.lang)}: {preset['scale']}x, {get_text('line_spacing_setting', self.lang)}: {preset['line_spacing']}, {get_text('paragraph_spacing_setting', self.lang)}: {preset['paragraph_spacing']}"
                self.stdscr.addstr(idx + 2, 4 + len(line) + 2, details[:max_x - len(line) - 6])
            
            help_text = f"[↑↓]{get_text('select', self.lang)} [Enter]{get_text('apply', self.lang)} [q]{get_text('back', self.lang)}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(len(presets) + 4, 4, help_text)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('q'):
                break
            elif c in (curses.KEY_UP, ord('k')):
                current_selection = (current_selection - 1) % len(presets)
            elif c in (curses.KEY_DOWN, ord('j')):
                current_selection = (current_selection + 1) % len(presets)
            elif c in (curses.KEY_ENTER, 10, 13):
                # 应用选中的预设
                preset = presets[current_selection]
                self.settings["font_scale"] = preset["scale"]
                self.settings["line_spacing"] = preset["line_spacing"]
                self.settings["paragraph_spacing"] = preset["paragraph_spacing"]
                self.settings.save()
                
                # 重新加载当前书籍
                if self.current_book:
                    self.load_book(self.current_book)
                
                # 显示应用成功消息
                self.show_message(get_text("settings_applied", self.lang), 
                                get_text("font_settings_applied", self.lang))
                break

    def adjust_font_scale(self):
        """调整字体缩放因子"""
        current_scale = self.get_setting("font_scale", 1.0)
        new_scale = self.show_slider_setting(
            get_text("font_scale", self.lang),
            current_scale,
            0.5,  # 最小值
            2.0,  # 最大值
            0.1,  # 步长
            get_text("font_scale_desc", self.lang)
        )
        
        if new_scale is not None:
            # 检查缩放因子是否会导致界面问题
            max_y, max_x = self.stdscr.getmaxyx()
            min_scale = max(0.5, 10 / max_x, 5 / max_y)  # 确保至少能显示10个字符和5行
            max_scale = min(2.0, max_x / 10, max_y / 5)  # 确保不会超出屏幕
            
            if new_scale < min_scale:
                self.show_message(get_text("invalid", self.lang), 
                                f"{get_text('font_scale', self.lang)} {get_text('cannot_be_less_than', self.lang)} {min_scale:.1f}")
                return
            elif new_scale > max_scale:
                self.show_message(get_text("invalid", self.lang), 
                                f"{get_text('font_scale', self.lang)} {get_text('cannot_be_greater_than', self.lang)} {max_scale:.1f}")
                return
            
            self.settings["font_scale"] = new_scale
            self.settings.save()
            
            # 重新加载当前书籍
            if self.current_book:
                self.load_book(self.current_book)
            
            self.show_message(get_text("settings_applied", self.lang), 
                            f"{get_text('font_scale', self.lang)}: {new_scale:.1f}x")

    def adjust_line_spacing(self):
        """调整行距"""
        current_spacing = getattr(self.settings, "line_spacing", 1)
        new_spacing = self.show_slider_setting(
            get_text("line_spacing_setting", self.lang),
            current_spacing,
            0,  # 最小值
            3,  # 最大值
            1,  # 步长
            get_text("line_spacing_desc", self.lang)
        )
        
        if new_spacing is not None:
            self.settings["line_spacing"] = new_spacing
            self.settings.save()
            
            # 重新加载当前书籍
            if self.current_book:
                self.load_book(self.current_book)
            
            self.show_message(get_text("settings_applied", self.lang), 
                            f"{get_text('line_spacing_setting', self.lang)}: {new_spacing}")

    def adjust_paragraph_spacing(self):
        """调整段落间距"""
        current_spacing = getattr(self.settings, "paragraph_spacing", 1)
        new_spacing = self.show_slider_setting(
            get_text("paragraph_spacing_setting", self.lang),
            current_spacing,
            0,  # 最小值
            3,  # 最大值
            1,  # 步长
            get_text("paragraph_spacing_desc", self.lang)
        )
        
        if new_spacing is not None:
            self.settings["paragraph_spacing"] = new_spacing
            self.settings.save()
            
            # 重新加载当前书籍
            if self.current_book:
                self.load_book(self.current_book)
            
            self.show_message(get_text("settings_applied", self.lang), 
                            f"{get_text('paragraph_spacing_setting', self.lang)}: {new_spacing}")

    def show_slider_setting(self, title, current_value, min_value, max_value, step, description):
        """显示滑块设置界面"""
        value = current_value
        
        while True:
            self.stdscr.clear()
            max_y, max_x = self.stdscr.getmaxyx()
            
            # 显示标题
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(0, max_x // 2 - len(title) // 2, title)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
            # 显示描述
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(2, 4, description[:max_x-8])
            self.stdscr.attroff(curses.color_pair(3))
            
            # 显示当前值
            value_str = f"{get_text('current_value', self.lang)}: {value}"
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(4, 4, value_str)
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            
            # 显示滑块
            slider_width = min(40, max_x - 10)
            slider_pos = int((value - min_value) / (max_value - min_value) * slider_width)
            
            slider = "[" + "=" * slider_pos + "○" + "=" * (slider_width - slider_pos - 1) + "]"
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(6, 4, slider)
            self.stdscr.attroff(curses.color_pair(1))
            
            # 显示最小值、最大值和步长
            range_info = f"{min_value} ← {step} → {max_value}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(7, 4 + (slider_width - len(range_info)) // 2, range_info)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            # 显示操作提示
            help_text = f"[←→]{get_text('adjust', self.lang)} [Enter]{get_text('apply', self.lang)} [q]{get_text('cancel', self.lang)}"
            self.stdscr.attron(curses.color_pair(3) | curses.A_DIM)
            self.stdscr.addstr(9, 4, help_text)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_DIM)
            
            self.stdscr.refresh()
            
            c = self.stdscr.getch()
            if c == ord('q'):
                return None
            elif c in (curses.KEY_ENTER, 10, 13):
                return value
            elif c == curses.KEY_RIGHT:
                value = min(max_value, value + step)
            elif c == curses.KEY_LEFT:
                value = max(min_value, value - step)

    def auto_adjust_font_settings(self):
        """根据屏幕大小自动调整字体设置"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 根据屏幕大小推荐设置
        if max_y < 25 or max_x < 80:  # 小屏幕
            recommended_scale = 0.8
            recommended_spacing = 0
        elif max_y < 35 or max_x < 100:  # 中等屏幕
            recommended_scale = 1.0
            recommended_spacing = 1
        else:  # 大屏幕
            recommended_scale = 1.2
            recommended_spacing = 1
        
        # 询问用户是否应用推荐设置
        message = f"{get_text('get_screen_size', self.lang)}: {max_x}x{max_y}, {get_text('recommend_use', self.lang)}: {get_text('font_scale', self.lang)}{recommended_scale}x, {get_text('line_spacing_setting', self.lang)}{recommended_spacing}"
        choice = self.show_confirm_dialog(get_text("auto_adjust", self.lang), message)
        
        if choice:
            self.settings["font_scale"] = recommended_scale
            self.settings["line_spacing"] = recommended_spacing
            self.settings.save()
            
            # 重新加载当前书籍
            if self.current_book:
                self.load_book(self.current_book)
            
            self.show_message(get_text("settings_applied", self.lang), 
                            get_text("font_settings_auto_adjusted", self.lang))

    def show_confirm_dialog(self, title, message):
        """显示确认对话框"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 计算对话框大小
        dialog_width = min(max_x - 4, len(message) + 4)
        dialog_height = 6
        
        # 计算对话框位置
        dialog_x = (max_x - dialog_width) // 2
        dialog_y = (max_y - dialog_height) // 2
        
        # 绘制对话框
        self.draw_section_border(dialog_y, dialog_x, dialog_height, dialog_width, title)
        
        # 显示消息
        self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(dialog_y + 2, dialog_x + 2, message[:dialog_width-4])
        self.stdscr.attroff(curses.color_pair(1))
        
        # 显示选项
        yes_option = f"[Y] {get_text('apply', self.lang)}"
        no_option = f"[N] {get_text('cancel', self.lang)}"
        
        options_line = f"{yes_option}   {no_option}"
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(dialog_y + 4, dialog_x + (dialog_width - len(options_line)) // 2, options_line)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
        self.stdscr.refresh()
        
        # 等待用户选择
        while True:
            c = self.stdscr.getch()
            if c in (ord('y'), ord('Y')):
                return True
            elif c in (ord('n'), ord('N'), ord('q')):
                return False

    def show_message(self, title, message, duration=2):
        """显示消息对话框"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 计算对话框大小
        dialog_width = min(max_x - 4, len(message) + 4)
        dialog_height = 5
        
        # 计算对话框位置
        dialog_x = (max_x - dialog_width) // 2
        dialog_y = (max_y - dialog_height) // 2
        
        # 绘制对话框
        self.draw_section_border(dialog_y, dialog_x, dialog_height, dialog_width, title)
        
        # 显示消息
        self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(dialog_y + 2, dialog_x + 2, message[:dialog_width-4])
        self.stdscr.attroff(curses.color_pair(1))
        
        self.stdscr.refresh()
        time.sleep(duration)

    def handle_font_shortcuts(self, c):
        """处理字体大小调整快捷键"""
        if c == ord('+') or c == ord('='):  # 增大字体
            current_scale = getattr(self.settings, "font_scale", 1.0)
            new_scale = min(2.0, current_scale + 0.1)
            self.settings["font_scale"] = new_scale
            self.apply_font_settings()
            return True
        elif c == ord('-'):  # 减小字体
            current_scale = getattr(self.settings, "font_scale", 1.0)
            new_scale = max(0.5, current_scale - 0.1)
            self.settings["font_scale"] = new_scale
            self.apply_font_settings()
            return True
        elif c == ord('['):  # 减小行距
            current_spacing = getattr(self.settings, "line_spacing", 1)
            new_spacing = max(0, current_spacing - 1)
            self.settings["line_spacing"] = new_spacing
            self.apply_font_settings()
            return True
        elif c == ord(']'):  # 增加行距
            current_spacing = getattr(self.settings, "line_spacing", 1)
            new_spacing = min(3, current_spacing + 1)
            self.settings["line_spacing"] = new_spacing
            self.apply_font_settings()
            return True
        return False

    def apply_font_settings(self):
        """应用字体设置并重新加载当前书籍"""
        self.settings.save()
        if self.current_book:
            self.load_book(self.current_book)
        
        # 显示临时提示
        max_y, max_x = self.stdscr.getmaxyx()
        scale = getattr(self.settings, "font_scale", 1.0)
        spacing = getattr(self.settings, "line_spacing", 1)
        message = f"{get_text('font_scale', self.lang)}: {scale:.1f}x, {get_text('line_spacing_setting', self.lang)}: {spacing}"
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(max_y - 2, max_x // 2 - len(message) // 2, message)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.refresh()
        time.sleep(1)  # 显示1秒后消失

    def get_setting(self, key, default=None):
        """安全地获取设置值"""
        try:
            return self.settings[key]
        except (KeyError, AttributeError):
            return default

    def get_display_width(self):
        """获取考虑缩放因子的显示宽度"""
        max_y, max_x = self.stdscr.getmaxyx()
        zoom_factor = self.get_setting("font_scale", 1.0)
        return max(10, min(self.settings["width"], int(max_x * 0.9 / zoom_factor)))

    def get_display_height(self):
        """获取考虑缩放因子的显示高度"""
        max_y, max_x = self.stdscr.getmaxyx()
        zoom_factor = self.get_setting("font_scale", 1.0)
        return max(5, min(self.settings["height"], int(max_y * 0.8 / zoom_factor)))

    def get_scaled_coordinates(self, y, x):
        """将逻辑坐标转换为考虑缩放因子的实际屏幕坐标"""
        zoom_factor = self.get_setting("font_scale", 1.0)
        return int(y * zoom_factor), int(x * zoom_factor)

    def get_safe_content_area(self):
        """计算安全的内容显示区域"""
        max_y, max_x = self.stdscr.getmaxyx()
        margin = self.settings["margin"]
        padding = self.settings["padding"]
        
        # 获取缩放因子
        zoom_factor = max(0.1, self.get_setting("font_scale", 1.0))
        
        # 计算有效的内容区域
        content_height = max(1, int((max_y - margin * 2) / zoom_factor))
        content_width = max(1, int((max_x - padding * 2) / zoom_factor))
        
        return content_height, content_width

    def get_display_coordinates(self, logical_y, logical_x):
        """将逻辑坐标转换为实际显示坐标"""
        margin = self.settings["margin"]
        padding = self.settings["padding"]
        
        # 获取缩放因子
        zoom_factor = max(0.1, self.get_setting("font_scale", 1.0))
        
        # 计算实际坐标
        actual_y = margin + int(logical_y * zoom_factor)
        actual_x = padding + int(logical_x * zoom_factor)
        
        # 确保坐标在屏幕范围内
        max_y, max_x = self.stdscr.getmaxyx()
        actual_y = max(0, min(actual_y, max_y - 1))
        actual_x = max(0, min(actual_x, max_x - 1))
        
        return actual_y, actual_x

    def get_display_info(self):
        """获取显示信息，包括可显示的行数和列数"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 获取缩放因子
        zoom_factor = max(0.1, self.get_setting("font_scale", 1.0))
        
        # 计算可用的显示区域（考虑边距）
        margin = self.settings["margin"]
        padding = self.settings["padding"]
        
        # 可显示的行数和列数
        display_height = max(1, int((max_y - margin * 2 - 6) / zoom_factor))  # 6行用于标题和状态栏
        display_width = max(1, int((max_x - padding * 2) / zoom_factor))
        
        return display_height, display_width

    def show_content_warning(self):
        """显示内容警告（如果内容超出屏幕）"""
        if not self.current_pages:
            return
            
        page_lines = self.current_pages[self.current_page_idx]
        display_height, display_width = self.get_display_info()
        
        # 检查是否有内容超出屏幕
        lines_outside = max(0, len(page_lines) - display_height)
        chars_outside = 0
        
        for line in page_lines:
            chars_outside += max(0, len(line) - display_width)
        
        # 如果有内容超出屏幕，显示警告
        if lines_outside > 0 or chars_outside > 0:
            max_y, max_x = self.stdscr.getmaxyx()
            warning = f"⚠️ {get_text('content_outside_warning', self.lang)}"
            
            if lines_outside > 0:
                warning += f" {lines_outside} {get_text('lines', self.lang)}"
            if chars_outside > 0:
                warning += f" {chars_outside} {get_text('chars', self.lang)}"
            
            y_pos = max(0, min(max_y - 1, max_y - 1))
            x_pos = max(0, min(2, max_x - len(warning) - 1))
            
            self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(y_pos, x_pos, warning)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

    def calculate_display_limits(self):
        """计算最大可显示行数和列数"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # 获取缩放因子
        zoom_factor = max(0.1, self.get_setting("font_scale", 1.0))
        
        # 计算边距和填充
        margin = max(0, self.settings["margin"])
        padding = max(0, self.settings["padding"])
        
        # 计算可用的显示区域
        self.max_display_lines = max(1, int((max_y - margin * 2 - 6) / zoom_factor))  # 6行用于标题和状态栏
        self.max_display_cols = max(1, int((max_x - padding * 2) / zoom_factor))

    def show_navigation_hints(self, page_lines, max_y, max_x):
        """显示导航提示"""
        # 如果有内容超出屏幕，显示导航提示
        hints = []
        
        # 行导航提示
        if self.display_start_line > 0:
            hints.append("↑")
        if self.display_start_line + self.max_display_lines < len(page_lines):
            hints.append("↓")
        
        # 列导航提示
        if self.display_start_col > 0:
            hints.append("←")
        
        max_line_length = max([len(line) for line in page_lines]) if page_lines else 0
        if self.display_start_col + self.max_display_cols < max_line_length:
            hints.append("→")
        
        # 添加重置提示
        if self.display_start_line > 0 or self.display_start_col > 0:
            hints.append(f"r:{get_text('reset', self.lang)}")
        
        if hints:
            hint_text = " ".join(hints)
            y_pos = max(0, min(max_y - 5, max_y - 1))
            x_pos = max(0, min(max_x - len(hint_text) - 2, max_x - 1))
            
            self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(y_pos, x_pos, hint_text)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

    def show_status_bar(self, max_y, max_x):
        """显示状态栏"""
        if self.settings["status_bar"] and self.current_book:
            status = f"📖 {self.current_book['title']} | {get_text('author', self.lang)}: {self.current_book['author']} | {get_text('current_page', self.lang)}: {self.current_page_idx+1}/{len(self.current_pages)}"
            y_pos = max(0, min(max_y - 4, max_y - 1))
            x_pos = max(0, min(2, max_x - len(status) - 1))
            
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(y_pos, x_pos, status)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            
        # 显示朗读状态
        if self.is_reading:
            reading_status = f"🔊 {get_text('aloud_r2_stop', self.lang)}"
            y_pos = max(0, min(max_y - 3, max_y - 1))
            x_pos = max(0, min(2, max_x - len(reading_status) - 1))
            
            self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(y_pos, x_pos, reading_status)
            self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            
        # 显示帮助信息
        help_str = " | ".join(self.get_help_list())
        y_pos = max(0, min(max_y - 2, max_y - 1))
        x_pos = max(0, min(2, max_x - len(help_str) - 1))
        
        self.stdscr.attron(curses.color_pair(2) | curses.A_DIM)
        self.stdscr.addstr(y_pos, x_pos, help_str)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_DIM)

    def handle_navigation_keys(self, c):
        """处理导航键"""
        if not self.current_pages:
            return False
            
        page_lines = self.current_pages[self.current_page_idx]
        
        # 重置键 - 回到顶部和左侧
        if c == ord('r') or c == ord('R'):  # 重置显示位置
            self.display_start_line = 0
            self.display_start_col = 0
            return True
            
        # 行导航
        if c == curses.KEY_UP:
            if self.display_start_line > 0:
                self.display_start_line -= 1
                return True
        elif c == curses.KEY_DOWN:
            if self.display_start_line + self.max_display_lines < len(page_lines):
                self.display_start_line += 1
                return True
        elif c == curses.KEY_PPAGE:  # Page Up
            if self.display_start_line > 0:
                self.display_start_line = max(0, self.display_start_line - self.max_display_lines)
                return True
        elif c == curses.KEY_NPAGE:  # Page Down
            if self.display_start_line + self.max_display_lines < len(page_lines):
                self.display_start_line = min(len(page_lines) - self.max_display_lines, 
                                            self.display_start_line + self.max_display_lines)
                return True
                
        # 列导航
        max_line_length = max([len(line) for line in page_lines]) if page_lines else 0
        if c == curses.KEY_LEFT:
            if self.display_start_col > 0:
                self.display_start_col -= 1
                return True
        elif c == curses.KEY_RIGHT:
            if self.display_start_col + self.max_display_cols < max_line_length:
                self.display_start_col += 1
                return True
                
        # Home 键 - 回到行首
        elif c == curses.KEY_HOME:
            if self.display_start_col > 0:
                self.display_start_col = 0
                return True
                
        # End 键 - 到行尾
        elif c == curses.KEY_END:
            if self.display_start_col + self.max_display_cols < max_line_length:
                self.display_start_col = max(0, max_line_length - self.max_display_cols)
                return True
                
        return False

    def safe_addstr(self, win, y, x, text, attr=None):
        """安全地添加字符串到窗口，避免边界错误"""
        max_y, max_x = win.getmaxyx()
        
        # 检查 y 坐标是否有效
        if y < 0 or y >= max_y:
            return False
        
        # 检查 x 坐标是否有效
        if x < 0 or x >= max_x:
            return False
        
        # 截断文本以适应屏幕
        max_length = max_x - x
        if max_length <= 0:
            return False
        
        safe_text = text[:max_length]
        
        try:
            if attr:
                win.addstr(y, x, safe_text, attr)
            else:
                win.addstr(y, x, safe_text)
            return True
        except curses.error:
            return False

    def safe_addstr_simple(self, y, x, text, attr=None):
        """简化版本的安全添加字符串方法，直接使用 self.stdscr"""
        return self.safe_addstr(self.stdscr, y, x, text, attr)

    def safe_addstr_centered(self, y, text, attr=None):
        """在指定行居中显示文本"""
        max_y, max_x = self.stdscr.getmaxyx()
        x = max(0, min(max_x // 2 - len(text) // 2, max_x - len(text) - 1))
        return self.safe_addstr(self.stdscr, y, x, text, attr)

    def run(self):
        try:
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
            
        except Exception as e:
            # 记录错误并尝试恢复
            import traceback
            error_msg = f"错误: {str(e)}"
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, error_msg)
            self.stdscr.addstr(1, 0, "按任意键继续...")
            self.stdscr.refresh()
            self.stdscr.getch()
            
            # 尝试恢复界面
            if self.current_book:
                self.display()
            else:
                self.show_bookshelf()