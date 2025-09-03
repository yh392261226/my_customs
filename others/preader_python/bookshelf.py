import os
import time
from db import DBManager
from utils import build_pages_from_file
from epub_utils import parse_epub, get_epub_metadata
from lang import get_text
from epub_utils import parse_epub, get_epub_metadata
from pdf_utils import parse_pdf, get_pdf_metadata
from mobi_utils import parse_mobi, get_mobi_metadata

class Bookshelf:
    def __init__(self, lang="zh"):
        self.db = DBManager()
        self.lang = lang
        self.books = self.load_books()

    def load_books(self):
        books = self.db.get_books()
        result = []
        for id_, path, title, author, book_type, old_tags in books:  # 注意这里改为old_tags
            exists = os.path.exists(path)
            # 获取书籍的标签列表 - 从数据库实时获取
            book_tags = self.db.get_book_tags(id_)
            tag_names = [tag[1] for tag in book_tags]  # 获取标签名称列表
            
            result.append({
                "id": id_,
                "path": path,
                "title": title,
                "author": author,
                "type": book_type,
                "tags": tag_names,  # 使用实时获取的标签列表
                "exists": exists
            })
        # 按照标题升序排序
        result.sort(key=lambda x: x["title"].lower())
        return result

    # 添加标签相关方法
    def get_all_tags(self):
        """获取所有标签"""
        tags = self.db.get_all_tags()
        return [tag[1] for tag in tags]

    def filter_books_by_tag(self, tag_name):
        """按标签过滤书籍 - 修复筛选逻辑"""
        if not tag_name:  # 如果标签为空，返回所有书籍
            return self.books
            
        return [book for book in self.books if tag_name in book["tags"]]

    def update_book_metadata(self, book_id, title, author, tags):
        """更新书籍元数据（标题、作者、标签）"""
        # 使用 self.db.conn 而不是 self.conn
        c = self.db.conn.cursor()
        
        # 使用事务确保所有操作要么全部成功，要么全部失败
        try:
            # 更新标题和作者
            c.execute("UPDATE books SET title=?, author=? WHERE id=?", (title, author, book_id))
            
            # 清空现有标签
            c.execute("DELETE FROM book_tags WHERE book_id=?", (book_id,))
            
            # 添加新标签
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                for tag_name in tag_list:
                    # 确保标签存在
                    tag_id = self.db.add_tag(tag_name)
                    # 关联标签和书籍
                    c.execute("INSERT OR IGNORE INTO book_tags (book_id, tag_id) VALUES (?, ?)", (book_id, tag_id))
            
            # 提交事务
            self.db.conn.commit()
            return True
            
        except Exception as e:
            # 发生错误时回滚
            self.db.conn.rollback()
            print(f"{get_text('update_books_source_failed', self.lang)}: {str(e)}")
            return False

    def batch_update_tags(self, book_ids, action, tag_name):
        """批量更新标签 - 修复已存在标签无法添加的问题"""
        success_count = 0
        
        # 首先处理标签
        if action == "add":
            # 确保标签存在并获取标签ID
            tag_id = self.db.add_tag(tag_name)
            if tag_id is None:
                print(f"{get_text('cannot_create_tag', self.lang).format(tag=tag_name)}")
                return 0
        elif action == "remove":
            # 获取标签ID
            all_tags = self.db.get_all_tags()
            tag_id = None
            for tag in all_tags:
                if tag[1] == tag_name:
                    tag_id = tag[0]
                    break
            if not tag_id:
                # 标签不存在，无需继续
                print(f"{get_text('tag', self.lang)} '{tag_name}' {get_text('not_exists', self,lang)}")
                return 0
        
        # 使用事务处理批量操作
        conn = self.db.conn
        c = conn.cursor()
        
        try:
            for book_id in book_ids:
                try:
                    if action == "add":
                        # 检查是否已经存在该标签关联
                        c.execute("SELECT COUNT(*) FROM book_tags WHERE book_id=? AND tag_id=?", (book_id, tag_id))
                        exists = c.fetchone()[0] > 0
                        
                        if not exists:
                            c.execute("INSERT INTO book_tags (book_id, tag_id) VALUES (?, ?)", (book_id, tag_id))
                            # print(f"添加标签成功: 书籍ID={book_id}, 标签ID={tag_id}")
                            success_count += 1
                        else:
                            # print(f"标签已存在: 书籍ID={book_id}, 标签ID={tag_id}")
                            # 即使标签已存在，我们也认为操作成功
                            success_count += 1
                    elif action == "remove":
                        c.execute("DELETE FROM book_tags WHERE book_id=? AND tag_id=?", (book_id, tag_id))
                        if c.rowcount > 0:
                            # print(f"移除标签成功: 书籍ID={book_id}, 标签ID={tag_id}")
                            success_count += 1
                        # else:
                            # print(f"标签不存在: 书籍ID={book_id}, 标签ID={tag_id}")
                except Exception as e:
                    print(f"{get_text('deal_book_id_error', self.lang).format(id=book_id)}: {str(e)}")
            
            # 提交事务
            conn.commit()
            print(f"{get_text('multype_update_success', self.lang)}: {get_text('update_success_books', self.lang).format(count=success_count)}")
            
        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"{get_text('multype_update_failed', self.lang)}: {str(e)}")
        
        # 重新加载书籍列表
        self.books = self.load_books()
        return success_count

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
        
        # 根据文件类型处理
        if ext == ".epub":
            print(f"{get_text('parsing_epub_data', self.lang)}...")
            title, author = get_epub_metadata(file_path)
            print(f"{get_text('save_to_db', self.lang)}...")
            self.db.add_book(file_path, title or os.path.basename(file_path), author, "epub", tags)
        elif ext == ".pdf":
            print(f"{get_text('parsing_epub_data', self.lang)}...")  # 复用提示文本
            title, author = get_pdf_metadata(file_path)
            print(f"{get_text('save_to_db', self.lang)}...")
            self.db.add_book(file_path, title or os.path.basename(file_path), author, "pdf", tags)
        elif ext == ".mobi":
            print(f"{get_text('parsing_epub_data', self.lang)}...")  # 复用提示文本
            title, author = get_mobi_metadata(file_path)
            print(f"{get_text('save_to_db', self.lang)}...")
            self.db.add_book(file_path, title or os.path.basename(file_path), author, "mobi", tags)
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
            if os.path.isfile(fpath) and fname.lower().endswith(('.txt', '.epub', '.pdf', '.mobi', '.md')):
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

    def get_books_by_ids(self, book_ids):
        """根据ID列表获取书籍信息"""
        return [book for book in self.books if book["id"] in book_ids]
    
    def get_all_books(self):
        """获取所有书籍"""
        return self.books
    
    def delete_tag(self, tag_name):
        """删除标签"""
        # 获取标签ID
        tag_id = self.db.get_tag_id(tag_name)
        if tag_id:
            return self.db.delete_tag(tag_id)
        return False

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