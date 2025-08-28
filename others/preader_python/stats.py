from db import DBManager
import datetime

class StatsManager:
    def __init__(self):
        self.db = DBManager()

    def record_reading(self, book_id, seconds):
        date = datetime.date.today().isoformat()
        self.db.record_stat(book_id, date, seconds)

    def get_book_stats(self, book_id):
        records = self.db.get_stats(book_id)
        total_time = sum(v for _, v in records)
        days = len(records)
        return {
            "total_time": total_time,
            "days": days,
            "records": records
        }