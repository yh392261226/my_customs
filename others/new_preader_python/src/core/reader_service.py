"""
阅读器服务 - 提供统一的阅读器配置和管理
"""

from typing import Dict, Any
from dataclasses import dataclass


from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ReaderConfig:
    """阅读器配置类"""
    font_size: int = 14
    line_spacing: float = 1.5
    paragraph_spacing: float = 1.2
    remember_position: bool = True
    auto_page_turn: bool = False
    auto_page_turn_interval: int = 30
    theme: str = "default"
    highlight_search: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "paragraph_spacing": self.paragraph_spacing,
            "remember_position": self.remember_position,
            "auto_page_turn": self.auto_page_turn,
            "auto_page_turn_interval": self.auto_page_turn_interval,
            "theme": self.theme,
            "highlight_search": self.highlight_search
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ReaderConfig':
        """从字典创建配置"""
        return cls(
            font_size=config_dict.get("font_size", 14),
            line_spacing=config_dict.get("line_spacing", 1.5),
            paragraph_spacing=config_dict.get("paragraph_spacing", 1.2),
            remember_position=config_dict.get("remember_position", True),
            auto_page_turn=config_dict.get("auto_page_turn", False),
            auto_page_turn_interval=config_dict.get("auto_page_turn_interval", 30),
            theme=config_dict.get("theme", "default"),
            highlight_search=config_dict.get("highlight_search", True)
        )

class ReaderService:
    """阅读器服务 - 管理阅读器配置和状态"""
    
    def __init__(self):
        self.config = ReaderConfig()
        self.current_book = None
        self.reading_session = None
        
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新阅读器配置"""
        self.config = ReaderConfig.from_dict(new_config)
        logger.info(f"阅读器配置已更新: {self.config}")
        
    def get_config(self) -> ReaderConfig:
        """获取当前配置"""
        return self.config
        
    def start_reading_session(self, book) -> None:
        """开始阅读会话"""
        self.current_book = book
        self.reading_session = {
            "start_time": None,
            "pages_read": 0,
            "words_read": 0,
            "current_page": book.current_page
        }
        logger.info(f"开始阅读会话: {book.title}")
        
    def end_reading_session(self) -> Dict[str, Any]:
        """结束阅读会话并返回统计信息"""
        if not self.reading_session:
            return {}
            
        stats = self.reading_session.copy()
        self.reading_session = None
        logger.info(f"结束阅读会话，统计: {stats}")
        return stats
        
    def update_reading_progress(self, page_num: int, words_read: int = 0) -> None:
        """更新阅读进度"""
        if self.reading_session:
            self.reading_session["current_page"] = page_num
            start_page = self.reading_session.get("start_page", page_num)
            if start_page is None:
                start_page = page_num
            self.reading_session["pages_read"] = page_num - start_page
            self.reading_session["words_read"] += words_read
            
    def get_reading_stats(self) -> Dict[str, Any]:
        """获取阅读统计信息"""
        if not self.reading_session:
            return {}
            
        return {
            "current_page": self.reading_session["current_page"],
            "pages_read": self.reading_session["pages_read"],
            "words_read": self.reading_session["words_read"]
        }