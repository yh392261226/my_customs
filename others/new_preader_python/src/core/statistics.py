"""
统计模块，负责收集和分析阅读数据
"""

import os
import json

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from src.core.bookshelf import Bookshelf

from src.utils.logger import get_logger

logger = get_logger(__name__)

class Statistics:
    """统计类，负责收集和分析阅读数据"""
    
    def __init__(self, bookshelf: Bookshelf, data_dir: Optional[str] = None):
        """
        初始化统计模块
        
        Args:
            bookshelf: 书架对象
            data_dir: 数据目录，如果为None则使用默认目录
        """
        self.bookshelf = bookshelf
        
        if data_dir is None:
            # 使用与书架相同的数据目录
            self.data_dir = bookshelf.data_dir
        else:
            self.data_dir = data_dir
            
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 统计数据文件路径
        self.stats_file = os.path.join(self.data_dir, "statistics.json")
        
        # 加载统计数据
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict[str, Any]:
        """
        加载统计数据
        
        Returns:
            Dict[str, Any]: 统计数据字典
        """
        if not os.path.exists(self.stats_file):
            logger.info("统计数据文件不存在，将创建新文件")
            return {
                "daily_stats": {},
                "total_stats": {
                    "reading_time": 0,
                    "books_read": 0,
                    "pages_read": 0,
                    "words_read": 0,
                    "books_finished": 0,
                    "longest_session": 0,
                    "first_read_date": None,
                    "last_read_date": None
                }
            }
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            logger.info("已加载统计数据")
            return stats
        except Exception as e:
            logger.error(f"加载统计数据时出错: {e}")
            return {
                "daily_stats": {},
                "total_stats": {
                    "reading_time": 0,
                    "books_read": 0,
                    "pages_read": 0,
                    "words_read": 0,
                    "books_finished": 0,
                    "longest_session": 0,
                    "first_read_date": None,
                    "last_read_date": None
                }
            }
    
    def save(self) -> bool:
        """
        保存统计数据
        
        Returns:
            bool: 保存是否成功
        """
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=4, ensure_ascii=False)
            logger.info("统计数据已保存")
            return True
        except Exception as e:
            logger.error(f"保存统计数据时出错: {e}")
            return False
    
    def update_statistics(self) -> None:
        """更新统计数据"""
        # 获取阅读历史记录
        reading_history = self.bookshelf.get_reading_history()
        
        # 重置统计数据
        self.stats = {
            "daily_stats": {},
            "total_stats": {
                "reading_time": 0,
                "books_read": 0,
                "pages_read": 0,
                "words_read": 0,
                "books_finished": 0,
                "longest_session": 0,
                "first_read_date": None,
                "last_read_date": None
            }
        }
        
        # 处理阅读历史记录
        books_read = set()
        books_finished = set()
        longest_session = 0
        first_read_date = None
        last_read_date = None
        
        for record in reading_history:
            # 提取日期
            date_str = record["read_date"].split(" ")[0]
            
            # 更新每日统计
            if date_str not in self.stats["daily_stats"]:
                self.stats["daily_stats"][date_str] = {
                    "reading_time": 0,
                    "books_read": 0,
                    "pages_read": 0,
                    "words_read": 0,
                    "books": set()
                }
            
            # 更新阅读时间
            duration = record.get("duration", 0)
            self.stats["daily_stats"][date_str]["reading_time"] += duration
            self.stats["total_stats"]["reading_time"] += duration
            
            # 更新最长阅读时段
            longest_session = max(longest_session, duration)
            
            # 更新阅读书籍
            book_path = record["book_path"]
            books_read.add(book_path)
            self.stats["daily_stats"][date_str]["books"].add(book_path)
            
            # 更新首次和最后阅读日期
            if first_read_date is None or date_str < first_read_date:
                first_read_date = date_str
            if last_read_date is None or date_str > last_read_date:
                last_read_date = date_str
            
            # 检查是否完成阅读
            if record.get("progress", 0) >= 0.98:  # 认为阅读进度达到98%即为完成
                books_finished.add(book_path)
        
        # 更新总体统计
        self.stats["total_stats"]["books_read"] = len(books_read)
        self.stats["total_stats"]["books_finished"] = len(books_finished)
        self.stats["total_stats"]["longest_session"] = longest_session
        self.stats["total_stats"]["first_read_date"] = first_read_date
        self.stats["total_stats"]["last_read_date"] = last_read_date
        
        # 更新每日统计中的书籍数量
        for date_str, daily_stat in self.stats["daily_stats"].items():
            daily_stat["books_read"] = len(daily_stat["books"])
            # 将集合转换为列表以便JSON序列化
            daily_stat["books"] = list(daily_stat["books"])
        
        # 计算页数（不再使用基于字数的计算）
        for book in self.bookshelf.get_all_books():
            if book.path in books_read:
                # 估算已读页数
                progress = book.reading_progress
                pages_read = int(book.total_pages * progress)
                
                # 确保类型正确
                self.stats["total_stats"]["pages_read"] = int(self.stats["total_stats"]["pages_read"]) + pages_read
                # 不再使用基于字数的计算
                self.stats["total_stats"]["words_read"] = 0
        
        # 保存更新后的统计数据
        self.save()
    
    def get_daily_stats(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        获取指定日期的统计数据
        
        Args:
            date_str: 日期字符串（YYYY-MM-DD格式），如果为None则使用今天
            
        Returns:
            Dict[str, Any]: 日期统计数据
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        return self.stats["daily_stats"].get(date_str, {
            "reading_time": 0,
            "books_read": 0,
            "pages_read": 0,
            "words_read": 0,
            "books": []
        })
    
    def get_period_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        获取指定时间段的统计数据
        
        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            
        Returns:
            Dict[str, Any]: 时间段统计数据
        """
        period_stats = {
            "reading_time": 0,
            "books_read": 0,
            "pages_read": 0,
            "words_read": 0,
            "books": set(),
            "daily_breakdown": {}
        }
        
        # 遍历日期范围
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_stats = self.get_daily_stats(date_str)
            
            period_stats["reading_time"] += daily_stats.get("reading_time", 0)
            period_stats["pages_read"] += daily_stats.get("pages_read", 0)
            period_stats["words_read"] += daily_stats.get("words_read", 0)
            
            for book in daily_stats.get("books", []):
                period_stats["books"].add(book)
            
            period_stats["daily_breakdown"][date_str] = daily_stats
            
            current_date += timedelta(days=1)
        
        period_stats["books_read"] = len(period_stats["books"])
        period_stats["books"] = list(period_stats["books"])
        
        return period_stats
    
    def get_weekly_stats(self) -> Dict[str, Any]:
        """
        获取本周统计数据
        
        Returns:
            Dict[str, Any]: 本周统计数据
        """
        today = datetime.now()
        start_of_week = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_of_week = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
        
        return self.get_period_stats(start_of_week, end_of_week)
    
    def get_monthly_stats(self) -> Dict[str, Any]:
        """
        获取本月统计数据
        
        Returns:
            Dict[str, Any]: 本月统计数据
        """
        today = datetime.now()
        start_of_month = today.replace(day=1).strftime("%Y-%m-%d")
        
        # 计算月末
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            
        end_of_month = end_of_month.strftime("%Y-%m-%d")
        
        return self.get_period_stats(start_of_month, end_of_month)
    
    def get_total_stats(self) -> Dict[str, Any]:
        """
        获取总体统计数据
        
        Returns:
            Dict[str, Any]: 总体统计数据
        """
        return self.stats["total_stats"]
    
    def get_reading_heatmap(self, year: Optional[int] = None) -> Dict[str, int]:
        """
        获取阅读热图数据
        
        Args:
            year: 年份，如果为None则使用当前年份
            
        Returns:
            Dict[str, int]: 日期到阅读时间（分钟）的映射
        """
        if year is None:
            year = datetime.now().year
            
        heatmap = {}
        
        for date_str, daily_stat in self.stats["daily_stats"].items():
            if date_str.startswith(str(year)):
                # 将阅读时间从秒转换为分钟
                reading_time_minutes = daily_stat["reading_time"] // 60
                heatmap[date_str] = reading_time_minutes
        
        return heatmap
    
    def get_reading_trend(self, days: int = 30) -> List[Tuple[str, int]]:
        """
        获取阅读趋势数据
        
        Args:
            days: 天数
            
        Returns:
            List[Tuple[str, int]]: 日期和阅读时间（分钟）的列表
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        
        trend = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_stats = self.get_daily_stats(date_str)
            reading_time_minutes = daily_stats.get("reading_time", 0) // 60
            trend.append((date_str, reading_time_minutes))
            current_date += timedelta(days=1)
        
        return trend
    
    def get_most_read_books(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取最常阅读的书籍
        
        Args:
            limit: 返回的书籍数量
            
        Returns:
            List[Dict[str, Any]]: 书籍统计列表
        """
        book_stats = defaultdict(lambda: {"reading_time": 0, "open_count": 0})
        
        # 统计每本书的阅读时间
        for record in self.bookshelf.get_reading_history():
            book_path = record["book_path"]
            duration = record.get("duration", 0)
            book_stats[book_path]["reading_time"] += duration
            book_stats[book_path]["open_count"] += 1
        
        # 转换为列表并排序
        books = []
        for path, stats in book_stats.items():
            book = self.bookshelf.get_book(path)
            if book:
                books.append({
                    "path": path,
                    "title": book.title,
                    "author": book.author,
                    "reading_time": stats["reading_time"],
                    "open_count": stats["open_count"],
                    "progress": book.reading_progress
                })
        
        # 按阅读时间排序
        books.sort(key=lambda x: x["reading_time"], reverse=True)
        
        return books[:limit]
    
    def get_most_read_authors(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取最常阅读的作者
        
        Args:
            limit: 返回的作者数量
            
        Returns:
            List[Dict[str, Any]]: 作者统计列表
        """
        author_stats = defaultdict(lambda: {"reading_time": 0, "book_count": 0, "books": set()})
        
        # 统计每个作者的阅读时间和书籍数量
        for record in self.bookshelf.get_reading_history():
            book_path = record["book_path"]
            book = self.bookshelf.get_book(book_path)
            if book:
                author = book.author
                duration = record.get("duration", 0)
                author_stats[author]["reading_time"] += duration
                author_stats[author]["books"].add(book_path)
        
        # 计算每个作者的书籍数量
        for author, stats in author_stats.items():
            stats["book_count"] = len(stats["books"])
            stats["books"] = list(stats["books"])
        
        # 转换为列表并排序
        authors = []
        for author, stats in author_stats.items():
            authors.append({
                "author": author,
                "reading_time": stats["reading_time"],
                "book_count": stats["book_count"],
                "books": stats["books"]
            })
        
        # 按阅读时间排序
        authors.sort(key=lambda x: x["reading_time"], reverse=True)
        
        return authors[:limit]
    
    def get_average_reading_speed(self) -> int:
        """
        获取平均阅读速度（字/分钟）
        
        Returns:
            int: 平均阅读速度
        """
        total_words = self.stats["total_stats"]["words_read"]
        total_time_minutes = self.stats["total_stats"]["reading_time"] / 60
        
        if total_time_minutes > 0:
            return int(total_words / total_time_minutes)
        return 0
    
    def reset_statistics(self) -> bool:
        """
        重置统计数据
        
        Returns:
            bool: 重置是否成功
        """
        try:
            self.stats = {
                "daily_stats": {},
                "total_stats": {
                    "reading_time": 0,
                    "books_read": 0,
                    "pages_read": 0,
                    "words_read": 0,
                    "books_finished": 0,
                    "longest_session": 0,
                    "first_read_date": None,
                    "last_read_date": None
                }
            }
            
            return self.save()
        except Exception as e:
            logger.error(f"重置统计数据时出错: {e}")
            return False
    
    def export_statistics(self, export_path: str) -> bool:
        """
        导出统计数据
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            export_data = {
                "statistics": self.stats,
                "export_time": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            
            logger.info(f"统计数据已导出到: {export_path}")
            return True
        except Exception as e:
            logger.error(f"导出统计数据时出错: {e}")
            return False

# 为保持向后兼容性，添加别名
StatisticsManager = Statistics