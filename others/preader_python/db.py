import sqlite3
import os

class DBManager:
    def __init__(self, db_path='novel_reader.db'):
        create = not os.path.exists(db_path)
        self.conn = sqlite3.connect(db_path)
        if create:
            self.init_db()

    def init_db(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            title TEXT,
            author TEXT,
            type TEXT,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            tags TEXT
        )''')
        c.execute('''CREATE TABLE bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            page INTEGER,
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE progress (
            book_id INTEGER PRIMARY KEY,
            page INTEGER,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            date TEXT,
            read_time INTEGER DEFAULT 0
        )''')
        self.conn.commit()

    def add_book(self, path, title, author, book_type, tags=''):
        c = self.conn.cursor()
        c.execute("INSERT INTO books (path, title, author, type, tags) VALUES (?, ?, ?, ?, ?)", (path, title, author, book_type, tags))
        self.conn.commit()

    def get_books(self):
        c = self.conn.cursor()
        c.execute("SELECT id, path, title, author, type, tags FROM books")
        return c.fetchall()

    def add_bookmark(self, book_id, page, comment=''):
        c = self.conn.cursor()
        c.execute("INSERT INTO bookmarks (book_id, page, comment) VALUES (?, ?, ?)", (book_id, page, comment))
        self.conn.commit()

    def get_bookmarks(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT page, comment FROM bookmarks WHERE book_id=? ORDER BY created_at DESC", (book_id,))
        return c.fetchall()

    def save_progress(self, book_id, page):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO progress (book_id, page) VALUES (?, ?)", (book_id, page))
        self.conn.commit()

    def get_progress(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT page FROM progress WHERE book_id=?", (book_id,))
        r = c.fetchone()
        return r[0] if r else 0

    def record_stat(self, book_id, date, seconds):
        c = self.conn.cursor()
        c.execute("SELECT id, read_time FROM stats WHERE book_id=? AND date=?", (book_id, date))
        r = c.fetchone()
        if r:
            c.execute("UPDATE stats SET read_time=? WHERE id=?", (r[1] + seconds, r[0]))
        else:
            c.execute("INSERT INTO stats (book_id, date, read_time) VALUES (?, ?, ?)", (book_id, date, seconds))
        self.conn.commit()

    def get_stats(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT date, read_time FROM stats WHERE book_id=? ORDER BY date DESC", (book_id,))
        return c.fetchall()