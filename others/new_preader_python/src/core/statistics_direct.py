"""
统计模块 - 直接数据库版本
直接操作数据库进行统计计算，不使用JSON文件缓存
"""

import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class StatisticsDirect:
    """直接数据库统计类，负责收集和分析阅读数据"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化统计模块
        
        Args:
            db_manager: 数据库管理器对象
        """
        self.db_manager = db_manager
        self.db_path = db_manager.db_path
    
    def get_total_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取总体统计数据（直接从数据库查询）
        
        Args:
            user_id: 用户ID，如果为None则获取所有用户数据
            
        Returns:
            Dict[str, Any]: 总体统计数据
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询条件
                where_clause = ""
                params = []
                if user_id is not None:
                    where_clause = "WHERE user_id = ?"
                    params = [user_id]
                
                # 获取阅读历史记录总数
                cursor.execute(f"SELECT COUNT(*) as total_records FROM reading_history {where_clause}", params)
                total_records = cursor.fetchone()["total_records"]
                
                # 获取总阅读时间
                cursor.execute(f"SELECT SUM(duration) as total_reading_time FROM reading_history {where_clause}", params)
                total_reading_time = cursor.fetchone()["total_reading_time"] or 0
                
                # 获取阅读过的书籍数量
                cursor.execute(f"SELECT COUNT(DISTINCT book_path) as books_read FROM reading_history {where_clause}", params)
                books_read = cursor.fetchone()["books_read"] or 0
                
                # 获取总阅读页数
                cursor.execute(f"SELECT SUM(pages_read) as total_pages_read FROM reading_history {where_clause}", params)
                total_pages_read = cursor.fetchone()["total_pages_read"] or 0
                
                # 获取最长阅读时段
                cursor.execute(f"SELECT MAX(duration) as longest_session FROM reading_history {where_clause}", params)
                longest_session = cursor.fetchone()["longest_session"] or 0
                
                # 获取首次和最后阅读日期
                cursor.execute(f"SELECT MIN(read_date) as first_read_date, MAX(read_date) as last_read_date FROM reading_history {where_clause}", params)
                date_result = cursor.fetchone()
                first_read_date = date_result["first_read_date"]
                last_read_date = date_result["last_read_date"]
                
                # 获取完成的书籍数量（如果表中有reading_progress字段）
                books_finished = 0
                try:
                    # 检查表是否有reading_progress字段
                    cursor.execute("PRAGMA table_info(reading_history)")
                    columns = [row[1] for row in cursor.fetchall()]
                    
                    if 'reading_progress' in columns:
                        if user_id is not None:
                            cursor.execute("""
                                SELECT COUNT(DISTINCT rh.book_path) as books_finished
                                FROM reading_history rh
                                JOIN books b ON rh.book_path = b.path
                                WHERE rh.user_id = ? AND rh.reading_progress >= 0.98
                            """, [user_id])
                        else:
                            cursor.execute("""
                                SELECT COUNT(DISTINCT rh.book_path) as books_finished
                                FROM reading_history rh
                                JOIN books b ON rh.book_path = b.path
                                WHERE rh.reading_progress >= 0.98
                            """)
                        books_finished = cursor.fetchone()["books_finished"] or 0
                except:
                    # 如果无法检查字段或查询失败，默认为0
                    books_finished = 0
                
                return {
                    "reading_time": total_reading_time,
                    "books_read": books_read,
                    "pages_read": total_pages_read,
                    "words_read": 0,  # 不再使用基于字数的计算
                    "books_finished": books_finished,
                    "longest_session": longest_session,
                    "first_read_date": first_read_date,
                    "last_read_date": last_read_date,
                    "total_records": total_records
                }
                
        except sqlite3.Error as e:
            logger.error(f"获取总体统计数据失败: {e}")
            return {
                "reading_time": 0,
                "books_read": 0,
                "pages_read": 0,
                "words_read": 0,
                "books_finished": 0,
                "longest_session": 0,
                "first_read_date": None,
                "last_read_date": None,
                "total_records": 0
            }
    
    def get_daily_stats(self, date_str: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取指定日期的统计数据
        
        Args:
            date_str: 日期字符串（YYYY-MM-DD格式），如果为None则使用今天
            user_id: 用户ID，如果为None则获取所有用户数据
            
        Returns:
            Dict[str, Any]: 日期统计数据
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询条件
                where_clause = "WHERE read_date LIKE ?"
                params = [f"{date_str}%"]
                
                if user_id is not None:
                    where_clause = "WHERE read_date LIKE ? AND user_id = ?"
                    params.append(user_id)
                
                # 获取当天的阅读记录
                cursor.execute(f"""
                    SELECT SUM(duration) as reading_time, 
                           COUNT(DISTINCT book_path) as books_read,
                           SUM(pages_read) as pages_read
                    FROM reading_history 
                    {where_clause}
                """, params)
                
                result = cursor.fetchone()
                
                return {
                    "reading_time": result["reading_time"] or 0,
                    "books_read": result["books_read"] or 0,
                    "pages_read": result["pages_read"] or 0,
                    "words_read": 0,
                    "books": []
                }
                
        except sqlite3.Error as e:
            logger.error(f"获取每日统计数据失败: {e}")
            return {
                "reading_time": 0,
                "books_read": 0,
                "pages_read": 0,
                "words_read": 0,
                "books": []
            }
    
    def get_period_stats(self, start_date: str, end_date: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取指定时间段的统计数据
        
        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            user_id: 用户ID，如果为None则获取所有用户数据
            
        Returns:
            Dict[str, Any]: 时间段统计数据
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询条件
                where_clause = "WHERE read_date BETWEEN ? AND ?"
                params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
                
                if user_id is not None:
                    where_clause = "WHERE read_date BETWEEN ? AND ? AND user_id = ?"
                    params.append(user_id)
                
                cursor.execute(f"""
                    SELECT SUM(duration) as reading_time, 
                           COUNT(DISTINCT book_path) as books_read,
                           SUM(pages_read) as pages_read,
                           GROUP_CONCAT(DISTINCT book_path) as book_paths
                    FROM reading_history 
                    {where_clause}
                """, params)
                
                result = cursor.fetchone()
                book_paths = result["book_paths"].split(",") if result["book_paths"] else []
                
                return {
                    "reading_time": result["reading_time"] or 0,
                    "books_read": result["books_read"] or 0,
                    "pages_read": result["pages_read"] or 0,
                    "words_read": 0,
                    "books": book_paths
                }
                
        except sqlite3.Error as e:
            logger.error(f"获取时间段统计数据失败: {e}")
            return {
                "reading_time": 0,
                "books_read": 0,
                "pages_read": 0,
                "words_read": 0,
                "books": []
            }
    
    def get_most_read_books(self, limit: int = 5, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取最常阅读的书籍
        
        Args:
            limit: 返回的书籍数量
            user_id: 用户ID，如果为None则获取所有用户数据
            
        Returns:
            List[Dict[str, Any]]: 书籍统计列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询条件
                where_clause = ""
                params = [limit]
                
                if user_id is not None:
                    where_clause = "WHERE user_id = ?"
                    params = [user_id, limit]
                
                cursor.execute(f"""
                    SELECT book_path, 
                           SUM(duration) as total_reading_time,
                           COUNT(*) as open_count
                    FROM reading_history 
                    {where_clause}
                    GROUP BY book_path 
                    ORDER BY total_reading_time DESC 
                    LIMIT ?
                """, params)
                
                books = []
                for row in cursor.fetchall():
                    # 获取书籍详细信息
                    book = self.db_manager.get_book(row["book_path"])
                    if book:
                        books.append({
                            "path": row["book_path"],
                            "title": book.title,
                            "author": book.author,
                            "reading_time": row["total_reading_time"],
                            "open_count": row["open_count"],
                            "progress": row["total_reading_time"]  # 使用阅读时间作为进度参考
                        })
                
                return books
                
        except sqlite3.Error as e:
            logger.error(f"获取最常阅读书籍失败: {e}")
            return []
    
    def get_most_read_authors(self, limit: int = 5, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取最常阅读的作者
        
        Args:
            limit: 返回的作者数量
            user_id: 用户ID，如果为None则获取所有用户数据
            
        Returns:
            List[Dict[str, Any]]: 作者统计列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询条件
                where_clause = "WHERE b.author IS NOT NULL AND b.author != ''"
                params = [limit]
                
                if user_id is not None:
                    where_clause = "WHERE b.author IS NOT NULL AND b.author != '' AND rh.user_id = ?"
                    params = [user_id, limit]
                
                cursor.execute(f"""
                    SELECT b.author,
                           SUM(rh.duration) as total_reading_time,
                           COUNT(DISTINCT rh.book_path) as book_count,
                           GROUP_CONCAT(DISTINCT rh.book_path) as book_paths
                    FROM reading_history rh
                    JOIN books b ON rh.book_path = b.path
                    {where_clause}
                    GROUP BY b.author
                    ORDER BY total_reading_time DESC 
                    LIMIT ?
                """, params)
                
                authors = []
                for row in cursor.fetchall():
                    book_paths = row["book_paths"].split(",") if row["book_paths"] else []
                    authors.append({
                        "author": row["author"],
                        "reading_time": row["total_reading_time"],
                        "book_count": row["book_count"],
                        "books": book_paths
                    })
                
                return authors
                
        except sqlite3.Error as e:
            logger.error(f"获取最常阅读作者失败: {e}")
            return []
    
    def get_reading_heatmap(self, year: Optional[int] = None, user_id: Optional[int] = None) -> Dict[str, int]:
        """
        获取阅读热图数据
        
        Args:
            year: 年份，如果为None则使用当前年份
            user_id: 用户ID，如果为None则获取所有用户数据
            
        Returns:
            Dict[str, int]: 日期到阅读时间（分钟）的映射
        """
        if year is None:
            year = datetime.now().year
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 构建查询条件
                where_clause = "WHERE strftime('%Y', read_date) = ?"
                params = [str(year)]
                
                if user_id is not None:
                    where_clause = "WHERE strftime('%Y', read_date) = ? AND user_id = ?"
                    params.append(user_id)
                
                cursor.execute(f"""
                    SELECT DATE(read_date) as read_date, 
                           SUM(duration) as daily_reading_time
                    FROM reading_history 
                    {where_clause}
                    GROUP BY DATE(read_date)
                """, params)
                
                heatmap = {}
                for row in cursor.fetchall():
                    # 将阅读时间从秒转换为分钟
                    reading_time_minutes = (row["daily_reading_time"] or 0) // 60
                    heatmap[row["read_date"]] = reading_time_minutes
                
                return heatmap
                
        except sqlite3.Error as e:
            logger.error(f"获取阅读热图数据失败: {e}")
            return {}
    
    def get_reading_trend(self, days: int = 30, user_id: Optional[int] = None) -> List[Tuple[str, int]]:
        """
        获取阅读趋势数据
        
        Args:
            days: 天数
            user_id: 用户ID，如果为None则获取所有用户数据
            
        Returns:
            List[Tuple[str, int]]: 日期和阅读时间（分钟）的列表
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        
        trend = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_stats = self.get_daily_stats(date_str, user_id=user_id)
            reading_time_minutes = daily_stats.get("reading_time", 0) // 60
            trend.append((date_str, reading_time_minutes))
            current_date += timedelta(days=1)
        
        return trend
    
    def reset_statistics(self, user_id: Optional[int] = None) -> bool:
        """
        重置统计数据
        
        Args:
            user_id: 用户ID，如果为None则重置所有用户数据
            
        Returns:
            bool: 重置是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建删除条件
                where_clause = ""
                params = []
                
                if user_id is not None:
                    where_clause = "WHERE user_id = ?"
                    params = [user_id]
                
                # 删除阅读历史记录
                cursor.execute(f"DELETE FROM reading_history {where_clause}", params)
                
                # 删除书籍统计相关的元数据
                if user_id is not None:
                    # 对于特定用户，只删除该用户的元数据
                    cursor.execute("""
                        DELETE FROM book_metadata 
                        WHERE book_path IN (
                            SELECT DISTINCT book_path FROM reading_history WHERE user_id = ?
                        )
                    """, [user_id])
                else:
                    # 对于所有用户，清空整个表
                    cursor.execute("DELETE FROM book_metadata")
                
                conn.commit()
                
                logger.info(f"统计数据重置成功 - 用户ID: {user_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"重置统计数据失败: {e}")
            return False

# 为保持向后兼容性，添加别名
StatisticsManagerDirect = StatisticsDirect