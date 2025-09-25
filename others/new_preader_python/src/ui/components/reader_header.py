"""
阅读器头部组件 - 显示书籍信息和阅读状态
"""

from typing import Dict, Any

from src.ui.components.base_component import BaseComponent

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderHeader(BaseComponent):
    """阅读器头部组件 - 显示书籍标题、作者和阅读统计"""
    
    def __init__(self, config: Dict[str, Any], component_id: str = "reader_header"):
        """
        初始化头部组件
        
        Args:
            config: 组件配置
            component_id: 组件ID
        """
        super().__init__(config, component_id)
        self.book_title: str = ""
        self.book_author: str = ""
        self.reading_stats: str = ""
        
    def _on_initialize(self) -> None:
        """组件初始化"""
        logger.debug(f"阅读器头部组件 {self.component_id} 初始化完成")
        
    def _on_config_change(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """配置变化处理"""
        # 头部组件配置变化通常不需要特殊处理
        pass
        
    def set_book_info(self, title: str, author: str) -> None:
        """设置书籍信息"""
        self.book_title = title
        self.book_author = author
        
    def update_stats(self, stats: Dict[str, Any]) -> None:
        """更新阅读统计"""
        pages_read = stats.get("pages_read", 0)
        total_pages = stats.get("total_pages", 0)
        reading_time = stats.get("reading_time", 0)
        
        if total_pages > 0:
            progress = f"{pages_read}/{total_pages}页"
            time_str = self._format_time(reading_time)
            self.reading_stats = f"{progress} | {time_str}"
        else:
            self.reading_stats = "阅读中..."
            
    def _format_time(self, seconds: int) -> str:
        """格式化时间显示"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}时{minutes}分"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"
            
    def render(self) -> str:
        """渲染组件内容"""
        header_info = f"{self.book_title} 作者: {self.book_author}"
        if self.reading_stats:
            header_info += f" | {self.reading_stats}"
        return header_info