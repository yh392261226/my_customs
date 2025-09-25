"""
阅读器控制组件 - 处理用户交互和控制逻辑
"""

from typing import Dict, Any, Callable

from src.ui.components.base_component import BaseComponent

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ReaderControls(BaseComponent):
    """阅读器控制组件 - 处理翻页、书签、搜索等用户交互"""
    
    def __init__(self, config: Dict[str, Any], component_id: str = "reader_controls"):
        """
        初始化控制组件
        
        Args:
            config: 组件配置
            component_id: 组件ID
        """
        super().__init__(config, component_id)
        self.auto_page_turn: bool = False
        self.auto_turn_interval: int = config.get("auto_page_turn_interval", 30)
        
    def _on_initialize(self) -> None:
        """组件初始化"""
        logger.debug(f"阅读器控制组件 {self.component_id} 初始化完成")
        
    def _on_config_change(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """配置变化处理"""
        if "auto_page_turn_interval" in new_config:
            self.auto_turn_interval = new_config["auto_page_turn_interval"]
            
    def toggle_auto_page_turn(self) -> bool:
        """切换自动翻页状态"""
        self.auto_page_turn = not self.auto_page_turn
        self.emit_event("auto_turn_changed", self.auto_page_turn)
        return self.auto_page_turn
        
    def adjust_font_size(self, delta: int) -> int:
        """调整字体大小"""
        current_size = self.config.get("font_size", 14)
        new_size = max(12, min(24, current_size + delta))
        
        if new_size != current_size:
            old_config = self.config.copy()
            self.config["font_size"] = new_size
            self._on_config_change(old_config, self.config)
            
        return new_size
        
    def set_callbacks(self, 
                     page_change_cb: Callable[[int], None],
                     auto_turn_cb: Callable[[bool], None],
                     config_change_cb: Callable[[Dict[str, Any]], None]) -> None:
        """设置回调函数"""
        self.register_callback("page_changed", page_change_cb)
        self.register_callback("auto_turn_changed", auto_turn_cb)
        self.register_callback("config_changed", config_change_cb)
        
    def render(self) -> str:
        """渲染组件内容"""
        auto_turn_status = "自动翻页: 开启" if self.auto_page_turn else "自动翻页: 关闭"
        font_size = self.config.get("font_size", 14)
        return f"{auto_turn_status} | 字体大小: {font_size}px"