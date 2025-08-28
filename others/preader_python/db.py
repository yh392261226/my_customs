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
            tags TEXT
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

    def add_book(self, path, title, author, book_type, tags):
        c = self.conn.cursor()
        c.execute("INSERT OR IGNORE INTO books (path, title, author, type, tags) VALUES (?, ?, ?, ?, ?)",
                  (path, title, author, book_type, tags))
        self.conn.commit()

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