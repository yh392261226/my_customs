"""
现代化阅读器基础组件 - 采用面向对象和面向切片架构
提供可扩展的组件基类和接口定义
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

import time
from src.core.reader_service import ReaderConfig as CoreReaderConfig

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderConfig(CoreReaderConfig):
    """阅读器配置数据类 - 兼容UI组件"""
    
    def __init__(self, **kwargs):
        # 调用父类初始化
        super().__init__(**kwargs)
        
        # 添加UI特定的默认值
        self.show_progress = kwargs.get('show_progress', True)
        self.show_stats = kwargs.get('show_stats', True)
        self.show_shortcuts = kwargs.get('show_shortcuts', True)
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，包含UI特定字段"""
        result = super().to_dict()
        result.update({
            'show_progress': self.show_progress,
            'show_stats': self.show_stats,
            'show_shortcuts': self.show_shortcuts
        })
        return result
        
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """从字典更新配置，包含UI特定字段"""
        super().update_from_dict(config_dict)
        
        if 'show_progress' in config_dict:
            self.show_progress = config_dict['show_progress']
        if 'show_stats' in config_dict:
            self.show_stats = config_dict['show_stats']
        if 'show_shortcuts' in config_dict:
            self.show_shortcuts = config_dict['show_shortcuts']

class ReaderComponent(ABC):
    """阅读器组件抽象基类"""
    
    def __init__(self, config: ReaderConfig):
        self.config = config
        self._callbacks: Dict[str, List[Callable[..., None]]] = {}
    
    @abstractmethod
    def initialize(self) -> None:
        """初始化组件"""
        pass
    
    @abstractmethod
    def update(self, data: Dict[str, Any]) -> None:
        """更新组件状态"""
        pass
    
    @abstractmethod
    def render(self) -> Dict[str, Any]:
        """渲染组件内容"""
        pass
    
    def register_callback(self, event: str, callback: Callable[..., None]) -> None:
        """注册事件回调"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def emit_event(self, event: str, *args, **kwargs) -> None:
        """触发事件"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Callback error for event {event}: {e}")
    
    def update_config(self, new_config: ReaderConfig) -> None:
        """更新配置"""
        self.config = new_config
        self.on_config_change()
    
    def on_config_change(self) -> None:
        """配置变化时的回调"""
        pass

class ContentRendererComponent(ReaderComponent):
    """内容渲染组件"""
    
    def __init__(self, config: ReaderConfig):
        super().__init__(config)
        self.content: Optional[str] = None
        self.pages: List[str] = []
        self.current_page: int = 0
        self.total_pages: int = 0
    
    def initialize(self) -> None:
        """初始化渲染器"""
        self.pages = []
        self.current_page = 0
        self.total_pages = 0
    
    def set_content(self, content: str) -> None:
        """设置内容并分页"""
        self.content = content
        self._paginate()
    
    def _paginate(self) -> None:
        """分页逻辑 - 使用动态分页，由DynamicContentRenderer处理"""
        if not self.content:
            self.pages = []
            self.total_pages = 0
            return
        
        # 动态分页由专门的DynamicContentRenderer组件处理
        # 这里保持简单的单页显示，避免重复分页逻辑
        self.pages = [self.content]
        self.total_pages = 1
    
    def _get_intelligent_page(self, content: str, target_length: int) -> str:
        """智能获取页面内容 - 已由DynamicContentRenderer处理"""
        # 动态分页由专门的DynamicContentRenderer组件处理
        return content
    
    def get_current_page(self) -> str:
        """获取当前页内容"""
        if not self.pages or self.current_page >= len(self.pages):
            return ""
        return self.pages[self.current_page]
    
    def next_page(self) -> bool:
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            return True
        return False
    
    def prev_page(self) -> bool:
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            return True
        return False
    
    def goto_page(self, page_num: int) -> bool:
        """跳转到指定页"""
        if 0 <= page_num < self.total_pages:
            self.current_page = page_num
            return True
        return False
    
    def update(self, data: Dict[str, Any]) -> None:
        """更新组件状态"""
        if "current_page" in data:
            self.goto_page(data["current_page"])
    
    def render(self) -> Dict[str, Any]:
        """渲染组件数据"""
        return {
            "current_content": self.get_current_page(),
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "progress": self.get_progress()
        }
    
    def get_progress(self) -> float:
        """获取阅读进度"""
        if self.total_pages == 0:
            return 0.0
        return self.current_page / self.total_pages

class StatisticsComponent(ReaderComponent):
    """统计组件"""
    
    def __init__(self, config: ReaderConfig):
        super().__init__(config)
        self.start_time: Optional[float] = None
        self.pages_read: int = 0
        self.words_read: int = 0
        self.reading_speed: float = 0.0
    
    def initialize(self) -> None:
        """初始化统计"""
        self.start_time = None
        self.pages_read = 0
        self.words_read = 0
        self.reading_speed = 0.0
    
    def start_reading(self) -> None:
        """开始阅读会话"""
        self.start_time = time.time()
        self.pages_read = 0
        self.words_read = 0
    
    def update_reading(self, page_content: str, page_num: int) -> None:
        """更新阅读统计"""
        if self.start_time is None:
            self.start_reading()
        
        self.pages_read += 1
        self.words_read += len(page_content.split())
        
        # 计算阅读速度（字/分钟）
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.reading_speed = (self.words_read / elapsed_time) * 60
    
    def update(self, data: Dict[str, Any]) -> None:
        """更新统计信息"""
        if "page_content" in data and "page_num" in data:
            self.update_reading(data["page_content"], data["page_num"])
    
    def render(self) -> Dict[str, Any]:
        """渲染统计信息"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        return {
            "pages_read": self.pages_read,
            "words_read": self.words_read,
            "reading_speed": round(self.reading_speed, 1),
            "reading_time": self._format_time(elapsed_time)
        }
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

class BookmarkComponent(ReaderComponent):
    """书签组件"""
    
    def __init__(self, config: ReaderConfig):
        super().__init__(config)
        self.bookmarks: Dict[int, Dict[str, Any]] = {}
    
    def initialize(self) -> None:
        """初始化书签"""
        self.bookmarks = {}
    
    def add_bookmark(self, page_num: int, note: str = "") -> bool:
        """添加书签"""
        if page_num in self.bookmarks:
            return False
        
        self.bookmarks[page_num] = {
            "page": page_num,
            "note": note,
            "timestamp": time.time(),
            "content_preview": self._get_content_preview(page_num)
        }
        
        return True
    
    def remove_bookmark(self, page_num: int) -> bool:
        """移除书签"""
        if page_num in self.bookmarks:
            del self.bookmarks[page_num]
            return True
        return False
    
    def has_bookmark(self, page_num: int) -> bool:
        """检查是否有书签"""
        return page_num in self.bookmarks
    
    def get_bookmarks(self) -> List[Dict[str, Any]]:
        """获取所有书签"""
        return list(self.bookmarks.values())
    
    def _get_content_preview(self, page_num: int) -> str:
        """获取内容预览"""
        # 这里需要访问渲染器组件获取页面内容
        # 在实际实现中，需要通过组件间通信获取
        return f"Page {page_num} content preview"
    
    def update(self, data: Dict[str, Any]) -> None:
        """更新书签状态"""
        if "add_bookmark" in data:
            page_num = data["page_num"]
            note = data.get("note", "")
            self.add_bookmark(page_num, note)
        elif "remove_bookmark" in data:
            self.remove_bookmark(data["page_num"])
    
    def render(self) -> Dict[str, Any]:
        """渲染书签信息"""
        return {
            "total_bookmarks": len(self.bookmarks),
            "has_current_bookmark": self.has_bookmark(self._get_current_page()),
            "bookmarks": self.get_bookmarks()
        }
    
    def _get_current_page(self) -> int:
        """获取当前页码"""
        # 需要通过组件间通信获取当前页码
        return 0

# 组件工厂
class ComponentFactory:
    """组件工厂 - 创建和管理阅读器组件"""
    
    @staticmethod
    def create_component(component_type: str, config: ReaderConfig) -> Optional[ReaderComponent]:
        """创建指定类型的组件"""
        components = {
            "content_renderer": ContentRendererComponent,
            "statistics": StatisticsComponent,
            "bookmark": BookmarkComponent
        }
        
        if component_type in components:
            return components[component_type](config)
        return None
    
    @staticmethod
    def create_all_components(config: ReaderConfig) -> Dict[str, ReaderComponent]:
        """创建所有组件"""
        return {
            "content_renderer": ContentRendererComponent(config),
            "statistics": StatisticsComponent(config),
            "bookmark": BookmarkComponent(config)
        }