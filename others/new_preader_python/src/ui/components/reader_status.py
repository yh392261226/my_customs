"""
阅读器状态组件 - 负责管理阅读状态和统计信息
采用面向对象设计，提供统一的状态管理接口
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime

class ReaderStatus:
    """阅读器状态管理组件"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化阅读器状态组件
        
        Args:
            config: 状态配置
        """
        self.config = config
        
        # 阅读状态
        self.reading_start_time: Optional[float] = None
        self.current_page = 0
        self.total_pages = 0
        self.word_count = 0
        
        # 统计信息
        self.pages_read = 0
        self.words_read = 0
        self.reading_time = 0
    
    def start_reading(self, current_page: int, total_pages: int, word_count: int) -> None:
        """开始阅读"""
        self.reading_start_time = time.time()
        self.current_page = current_page
        self.total_pages = total_pages
        self.word_count = word_count
        self.pages_read = current_page
        # 不再使用基于字数的计算，仅记录页面进度
        self.words_read = 0
    
    def update_reading_position(self, current_page: int) -> None:
        """更新阅读位置"""
        # 确保页码在有效范围内
        current_page = max(0, min(current_page, self.total_pages - 1))
        
        old_page = self.current_page
        self.current_page = current_page
        
        # 更新已读页数（仅当向前翻页时增加）
        if current_page > old_page:
            self.pages_read += (current_page - old_page)
        
        # 基于页面进度估算已读字数
        if self.total_pages > 0:
            self.words_read = int(self.word_count * (current_page / self.total_pages))
    
    def stop_reading(self) -> Dict[str, Any]:
        """停止阅读并返回统计信息"""
        if self.reading_start_time is None:
            return {}
        
        session_time = int(time.time() - self.reading_start_time)
        self.reading_time += session_time
        
        stats = self.get_statistics()
        self.reading_start_time = None
        
        return stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取当前统计信息"""
        current_time = time.time() if self.reading_start_time else 0
        session_time = int(current_time - self.reading_start_time) if self.reading_start_time else 0
        total_reading_time = self.reading_time + session_time
        
        # 计算阅读速度（页/分钟）
        reading_speed = 0
        if total_reading_time > 0 and self.pages_read > 0:
            reading_speed = int(self.pages_read / (total_reading_time / 60))
        
        # 估计剩余时间（基于页面而非字数）
        remaining_pages = max(0, self.total_pages - self.current_page)
        estimated_time_left = 0
        if reading_speed > 0:
            estimated_time_left = int(remaining_pages / reading_speed * 60)
        
        return {
            "current_page": self.current_page + 1,  # 始终显示1-based页码
            "total_pages": self.total_pages,
            "progress": self.current_page / self.total_pages if self.total_pages > 0 else 0,
            "pages_read": self.pages_read,
            "words_read": self.words_read,
            "total_words": self.word_count,
            "session_time": session_time,
            "total_reading_time": total_reading_time,
            "reading_speed": reading_speed,
            "estimated_time_left": estimated_time_left,
            "page_progress": f"{self.current_page + 1}/{self.total_pages}"  # 添加页面进度显示
        }
    
    def get_progress(self) -> float:
        """获取阅读进度"""
        if self.total_pages == 0:
            return 0.0
        return self.current_page / self.total_pages
    
    def reset(self) -> None:
        """重置状态"""
        self.reading_start_time = None
        self.current_page = 0
        self.total_pages = 0
        self.word_count = 0
        self.pages_read = 0
        self.words_read = 0
        self.reading_time = 0

    def get_reading_time(self) -> int:
        """获取阅读时间（秒）"""
        if self.reading_start_time is None:
            return self.reading_time
        return self.reading_time + int(time.time() - self.reading_start_time)

    def get_reading_speed(self) -> int:
        """获取阅读速度（字/分钟）"""
        total_time = self.get_reading_time()
        if total_time <= 0 or self.words_read <= 0:
            return 0
        return int(self.words_read / (total_time / 60))

    def get_words_read(self) -> int:
        """获取已读字数"""
        return self.words_read

# 工厂函数
def create_status_manager(config: Dict[str, Any]) -> ReaderStatus:
    """创建阅读器状态管理组件实例"""
    return ReaderStatus(config)