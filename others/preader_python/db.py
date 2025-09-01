import os
import sqlite3

def get_db_path():
    home = os.environ.get("HOME")
    config_dir = os.path.join(home, ".config", "preader")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "novel_reader.db")

class DBManager:
    def __init__(self):
        self.db_path = get_db_path()
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            title TEXT,
            author TEXT,
            type TEXT,
            tags TEXT,
            last_read_time INTEGER  -- 添加最后阅读时间字段
        )""")
        # 添加标签表
        c.execute("""CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS book_tags (
            book_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY(book_id, tag_id),
            FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS progress (
            book_id INTEGER,
            page_idx INTEGER,
            PRIMARY KEY(book_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS bookmarks (
            book_id INTEGER,
            page_idx INTEGER,
            comment TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS stats (
            book_id INTEGER,
            date TEXT,
            seconds INTEGER,
            PRIMARY KEY(book_id, date)
        )""")
        self.conn.commit()
    
    # 添加标签相关方法
    def get_all_tags(self):
        """获取所有标签"""
        c = self.conn.cursor()
        c.execute("SELECT id, name FROM tags ORDER BY name")
        return c.fetchall()

    def add_tag(self, tag_name):
        """添加标签，如果已存在则返回现有标签的ID"""
        c = self.conn.cursor()
        
        # 首先尝试插入标签
        c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
        
        # 然后获取标签ID（无论是否是新插入的还是已存在的）
        c.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        result = c.fetchone()
        
        self.conn.commit()
        
        if result:
            return result[0]
        else:
            # 如果插入失败且无法获取ID，返回None
            return None
    
    def get_book_tags(self, book_id):
        """获取书籍的标签"""
        c = self.conn.cursor()
        c.execute("""SELECT t.id, t.name FROM tags t 
                    JOIN book_tags bt ON t.id = bt.tag_id 
                    WHERE bt.book_id = ?""", (book_id,))
        return c.fetchall()

    def add_book_tag(self, book_id, tag_id):
        """为书籍添加标签"""
        c = self.conn.cursor()
        try:
            c.execute("INSERT OR IGNORE INTO book_tags (book_id, tag_id) VALUES (?, ?)", (book_id, tag_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # 标签已存在，忽略错误
            return False

    def remove_book_tag(self, book_id, tag_id):
        """移除书籍的标签"""
        c = self.conn.cursor()
        c.execute("DELETE FROM book_tags WHERE book_id=? AND tag_id=?", (book_id, tag_id))
        self.conn.commit()
        return c.rowcount > 0
    
    def update_book_metadata(self, book_id, title, author, tags):
        """更新书籍元数据（标题、作者、标签）"""
        c = self.conn.cursor()
        # 更新标题和作者
        c.execute("UPDATE books SET title=?, author=? WHERE id=?", (title, author, book_id))
        
        # 清空现有标签
        c.execute("DELETE FROM book_tags WHERE book_id=?", (book_id,))
        
        # 添加新标签
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            for tag_name in tag_list:
                # 确保标签存在
                tag_id = self.add_tag(tag_name)
                # 关联标签和书籍
                self.add_book_tag(book_id, tag_id)
        
        self.conn.commit()

    def add_book(self, path, title, author, book_type, tags):
        c = self.conn.cursor()
        c.execute("INSERT OR IGNORE INTO books (path, title, author, type, tags) VALUES (?, ?, ?, ?, ?)",
                  (path, title, author, book_type, tags))
        book_id = c.lastrowid
        
        # 处理标签
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            for tag_name in tag_list:
                tag_id = self.add_tag(tag_name)
                self.add_book_tag(book_id, tag_id)
        
        self.conn.commit()
        return book_id

    def get_books(self):
        c = self.conn.cursor()
        c.execute("SELECT id, path, title, author, type, tags FROM books ORDER BY id DESC")
        return c.fetchall()

    def save_progress(self, book_id, page_idx):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO progress (book_id, page_idx) VALUES (?, ?)", (book_id, page_idx))
        self.conn.commit()

    def get_progress(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT page_idx FROM progress WHERE book_id=?", (book_id,))
        r = c.fetchone()
        return r[0] if r else 0

    def add_bookmark(self, book_id, page_idx, comment):
        c = self.conn.cursor()
        c.execute("INSERT INTO bookmarks (book_id, page_idx, comment) VALUES (?, ?, ?)", (book_id, page_idx, comment))
        self.conn.commit()

    def get_bookmarks(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT page_idx, comment FROM bookmarks WHERE book_id=? ORDER BY page_idx", (book_id,))
        return c.fetchall()

    def record_stat(self, book_id, date, seconds):
        c = self.conn.cursor()
        c.execute("SELECT seconds FROM stats WHERE book_id=? AND date=?", (book_id, date))
        r = c.fetchone()
        if r:
            c.execute("UPDATE stats SET seconds=seconds+? WHERE book_id=? AND date=?", (seconds, book_id, date))
        else:
            c.execute("INSERT INTO stats (book_id, date, seconds) VALUES (?, ?, ?)", (book_id, date, seconds))
        self.conn.commit()

    def get_stats(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT date, seconds FROM stats WHERE book_id=? ORDER BY date", (book_id,))
        return c.fetchall()

    def delete_book(self, book_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM books WHERE id=?", (book_id,))
        c.execute("DELETE FROM progress WHERE book_id=?", (book_id,))
        c.execute("DELETE FROM bookmarks WHERE book_id=?", (book_id,))
        c.execute("DELETE FROM stats WHERE book_id=?", (book_id,))
        self.conn.commit()

    def update_book_path(self, book_id, new_path):
        """更新书籍路径"""
        c = self.conn.cursor()
        c.execute("UPDATE books SET path=? WHERE id=?", (new_path, book_id))
        self.conn.commit()

    def delete_book(self, book_id):
        """删除书籍及其所有相关数据"""
        c = self.conn.cursor()
        # 删除书籍
        c.execute("DELETE FROM books WHERE id=?", (book_id,))
        # 删除阅读进度
        c.execute("DELETE FROM progress WHERE book_id=?", (book_id,))
        # 删除书签
        c.execute("DELETE FROM bookmarks WHERE book_id=?", (book_id,))
        # 删除阅读统计
        c.execute("DELETE FROM stats WHERE book_id=?", (book_id,))
        self.conn.commit()

    def delete_tag(self, tag_id):
        """删除标签及其所有关联"""
        c = self.conn.cursor()
        # 先删除书籍标签关联
        c.execute("DELETE FROM book_tags WHERE tag_id=?", (tag_id,))
        # 再删除标签本身
        c.execute("DELETE FROM tags WHERE id=?", (tag_id,))
        self.conn.commit()
        return True
    
    def get_tag_id(self, tag_name):
        """根据标签名称获取标签ID"""
        c = self.conn.cursor()
        c.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
        result = c.fetchone()
        return result[0] if result else None
    
    def update_bookmark(self, bookmark_id, page_idx, comment):
        """更新书签"""
        c = self.conn.cursor()
        c.execute("UPDATE bookmarks SET page_idx=?, comment=? WHERE rowid=?", 
                (page_idx, comment, bookmark_id))
        self.conn.commit()

    def delete_bookmark(self, bookmark_id):
        """删除书签"""
        c = self.conn.cursor()
        c.execute("DELETE FROM bookmarks WHERE rowid=?", (bookmark_id,))
        self.conn.commit()

    def get_bookmark_by_id(self, bookmark_id):
        """根据ID获取书签"""
        c = self.conn.cursor()
        c.execute("SELECT rowid, book_id, page_idx, comment FROM bookmarks WHERE rowid=?", (bookmark_id,))
        return c.fetchone()