"""
共享类型定义和接口，用于解决循环依赖问题
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass

@dataclass
class BookData:
    """书籍数据结构，用于模块间数据传递"""
    path: str
    title: str
    author: str
    format: str
    size: int
    file_size: int
    add_date: str
    pinyin: str
    tags: str
    file_not_found: bool = False

@dataclass  
class ReadingInfo:
    """阅读信息数据结构"""
    current_position: int = 0
    current_page: int = 0
    total_pages: int = 0
    reading_progress: float = 0.0
    last_read_date: Optional[str] = None
    word_count: int = 0
    open_count: int = 0
    anchor_text: str = ""
    anchor_hash: str = ""

# 书籍操作接口类（用于解耦）
class BookOperations:
    """书籍操作接口，避免直接导入Book类"""
    
    @staticmethod
    def create_book_from_dict(data: Dict[str, Any]) -> Any:
    """从字典创建书籍对象"""
    from src.core.book import Book
    return Book.from_dict(data)

    @staticmethod
    def convert_book_to_dict(book: Any) -> Dict[str, Any]:
        """将书籍对象转换为字典"""
    return book.to_dict()

# 解析器接口
def get_parser_factory() -> Any:
    """延迟导入解析器工厂"""
    from src.parsers.parser_factory import parser_factory
    return parser_factory