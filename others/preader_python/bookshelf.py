import os
from db import DBManager
from utils import build_pages_from_file
from epub_utils import parse_epub, get_epub_metadata
import time

class Bookshelf:
    def __init__(self):
        self.db = DBManager()
        self.books = self.load_books()

    def load_books(self):
        books = self.db.get_books()
        result = []
        for id_, path, title, author, book_type, tags in books:
            if not os.path.exists(path):
                continue
            result.append({
                "id": id_,
                "path": path,
                "title": title,
                "author": author,
                "type": book_type,
                "tags": tags
            })
        return result

    def add_book(self, file_path, tags="", width=80, height=25, line_spacing=1):
        ext = os.path.splitext(file_path)[-1].lower()
        if not os.path.exists(file_path):
            return None
            
        # 简单的加载提示
        print("加载书籍中...")
        if ext == ".epub":
            print("解析EPUB元数据...")
            title, author = get_epub_metadata(file_path)
            print("保存到数据库...")
            self.db.add_book(file_path, title or os.path.basename(file_path), author, "epub", tags)
        else:
            print("保存到数据库...")
            self.db.add_book(file_path, os.path.basename(file_path), "", "txt", tags)
            
        self.books = self.load_books()

    def add_dir(self, dir_path, tags="", width=80, height=25, line_spacing=1):
        if not os.path.isdir(dir_path):
            return
            
        # 获取目录中所有支持的书籍文件
        files = []
        for fname in os.listdir(dir_path):
            fpath = os.path.join(dir_path, fname)
            if os.path.isfile(fpath) and fname.lower().endswith(('.txt', '.epub', '.md')):
                files.append(fpath)
                
        # 简单的加载提示
        print(f"添加目录中的书籍，共 {len(files)} 本...")
        for i, fpath in enumerate(files):
            print(f"处理第 {i+1}/{len(files)} 本: {os.path.basename(fpath)}")
            self.add_book(fpath, tags=tags, width=width, height=height, line_spacing=line_spacing)

    def get_book_by_id(self, book_id):
        for b in self.books:
            if b["id"] == book_id:
                return b
        return None

    def search_books(self, keyword):
        keyword = keyword.strip().lower()
        return [book for book in self.books if keyword in book["title"].lower()]