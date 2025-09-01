import os
from db import DBManager
from utils import build_pages_from_file
from epub_utils import parse_epub, get_epub_metadata
from lang import get_text
import time

class Bookshelf:
    def __init__(self, lang="zh"):
        self.db = DBManager()
        self.lang = lang
        self.books = self.load_books()

    def load_books(self):
        books = self.db.get_books()
        result = []
        for id_, path, title, author, book_type, tags in books:
            exists = os.path.exists(path)
            result.append({
                "id": id_,
                "path": path,
                "title": title,
                "author": author,
                "type": book_type,
                "tags": tags,
                "exists": exists  # 添加存在状态标记
            })
        # 按照标题升序排序
        result.sort(key=lambda x: x["title"].lower())
        return result

    def check_books_existence(self):
        """检查所有书籍文件是否存在"""
        for book in self.books:
            book["exists"] = os.path.exists(book["path"])
        return self.books

    def update_book_path(self, book_id, new_path):
        """更新书籍路径"""
        if not os.path.exists(new_path):
            return False
            
        # 更新数据库
        self.db.update_book_path(book_id, new_path)
        
        # 更新内存中的书籍列表
        for book in self.books:
            if book["id"] == book_id:
                book["path"] = new_path
                book["exists"] = True
                break
                
        return True

    def delete_book(self, book_id):
        """从书架删除书籍"""
        # 从数据库删除
        self.db.delete_book(book_id)
        
        # 从内存中的书籍列表删除
        self.books = [book for book in self.books if book["id"] != book_id]
        
    def delete_books(self, book_ids):
        """批量删除书籍"""
        for book_id in book_ids:
            self.db.delete_book(book_id)
        
        # 从内存中的书籍列表删除
        self.books = [book for book in self.books if book["id"] not in book_ids]

    def add_book(self, file_path, tags="", width=80, height=25, line_spacing=1):
        ext = os.path.splitext(file_path)[-1].lower()
        if not os.path.exists(file_path):
            return None
            
        # 简单的加载提示
        print(f"{get_text('loading_books', self.lang)}...")
        if ext == ".epub":
            print(f"{get_text('parsing_epub_data', self.lang)}...")
            title, author = get_epub_metadata(file_path)
            print(f"{get_text('save_to_db', self.lang)}...")
            self.db.add_book(file_path, title or os.path.basename(file_path), author, "epub", tags)
        else:
            print(f"{get_text('save_to_db', self.lang)}...")
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
        print(f"{get_text('total_add_books', self.lang).format(books=len(files))}...")
        for i, fpath in enumerate(files):
            print(f"{get_text('parsing_books', self.lang).format(books=f'{i+1}/{len(files)}')}: {os.path.basename(fpath)}")
            self.add_book(fpath, tags=tags, width=width, height=height, line_spacing=line_spacing)

    def get_book_by_id(self, book_id):
        for b in self.books:
            if b["id"] == book_id:
                return b
        return None

    def search_books(self, keyword):
        keyword = keyword.strip().lower()
        result = [book for book in self.books if keyword in book["title"].lower()]
        # 搜索结果也按照标题升序排序
        result.sort(key=lambda x: x["title"].lower())
        return result
    
    def delete_book(self, book_id):
        self.db.delete_book(book_id)
        self.books = self.load_books()