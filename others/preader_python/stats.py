from db import DBManager
import datetime
from collections import defaultdict

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

    def get_all_books_stats(self):
        # Returns stats for all books as {book_id: {total_time, days, records}}
        all_books = self.db.get_books()
        result = {}
        for book in all_books:
            book_id = book[0]
            result[book_id] = self.get_book_stats(book_id)
        return result

    def get_daily_stats_for_chart(self, book_id=None):
        """获取每日阅读统计，适合图表显示"""
        daily_stats = self.get_daily_stats(book_id)
        # 转换为(日期, 分钟数)格式
        return [(date, seconds // 60) for date, seconds in daily_stats]

    def get_weekly_stats_for_chart(self, book_id=None):
        """获取每周阅读统计，适合图表显示"""
        weekly_stats = self.get_weekly_stats(book_id)
        # 转换为(周次, 分钟数)格式
        return [(week, seconds // 60) for week, seconds in weekly_stats]

    def get_monthly_stats_for_chart(self, book_id=None):
        """获取每月阅读统计，适合图表显示"""
        monthly_stats = self.get_monthly_stats(book_id)
        # 转换为(月份, 分钟数)格式
        return [(month, seconds // 60) for month, seconds in monthly_stats]

    def get_daily_stats(self, book_id=None):
        """获取每日阅读统计"""
        if book_id:
            records = self.db.get_stats(book_id)
        else:
            # 获取所有书籍的统计
            all_stats = self.get_all_books_stats()
            daily_stats = defaultdict(int)
            for book_id, stats in all_stats.items():
                for date, seconds in stats["records"]:
                    daily_stats[date] += seconds
            records = list(daily_stats.items())
        
        # 按日期排序
        records.sort(key=lambda x: x[0])
        return records

    def get_weekly_stats(self, book_id=None):
        """获取每周阅读统计"""
        daily_stats = self.get_daily_stats(book_id)
        weekly_stats = defaultdict(int)
        
        for date, seconds in daily_stats:
            # 将日期转换为周数
            year, week, _ = datetime.datetime.strptime(date, "%Y-%m-%d").isocalendar()
            week_key = f"{year}-W{week:02d}"
            weekly_stats[week_key] += seconds
        
        return list(weekly_stats.items())

    def get_monthly_stats(self, book_id=None):
        """获取每月阅读统计"""
        daily_stats = self.get_daily_stats(book_id)
        monthly_stats = defaultdict(int)
        
        for date, seconds in daily_stats:
            # 提取年月
            year_month = date[:7]  # YYYY-MM
            monthly_stats[year_month] += seconds
        
        return list(monthly_stats.items())