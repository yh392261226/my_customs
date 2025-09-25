"""
设置变更观察者系统
提供实时设置变更通知和响应机制
"""


import time
from typing import Dict, Any, List, Callable, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger(__name__)

class SettingChangeEvent:
    """设置变更事件"""
    
    def __init__(self, setting_key: str, old_value: Any, new_value: Any, source: str = "user"):
        self.setting_key = setting_key
        self.old_value = old_value
        self.new_value = new_value
        self.source = source
        self.timestamp = time.time()
    
    def __str__(self) -> str:
        return f"SettingChangeEvent({self.setting_key}: {self.old_value} -> {self.new_value})"

class SettingObserver(ABC):
    """设置观察者抽象基类"""
    
    @abstractmethod
    def on_setting_changed(self, event: SettingChangeEvent) -> None:
        """设置变更时的回调"""
        pass

class SettingObserverManager:
    """设置观察者管理器"""
    
    def __init__(self):
        self._observers: Dict[str, List[SettingObserver]] = {}
        self._global_observers: List[SettingObserver] = []
    
    def register_observer(self, observer: SettingObserver, setting_key: Optional[str] = None) -> None:
        """注册观察者"""
        if setting_key:
            if setting_key not in self._observers:
                self._observers[setting_key] = []
            self._observers[setting_key].append(observer)
        else:
            self._global_observers.append(observer)
    
    def unregister_observer(self, observer: SettingObserver, setting_key: Optional[str] = None) -> None:
        """取消注册观察者"""
        if setting_key:
            if setting_key in self._observers:
                if observer in self._observers[setting_key]:
                    self._observers[setting_key].remove(observer)
        else:
            if observer in self._global_observers:
                self._global_observers.remove(observer)
    
    def notify_setting_changed(self, event: SettingChangeEvent) -> None:
        """通知设置变更"""
        # 通知特定设置的观察者
        if event.setting_key in self._observers:
            for observer in self._observers[event.setting_key]:
                try:
                    observer.on_setting_changed(event)
                except Exception as e:
                    logger.error(f"Observer error for {event.setting_key}: {e}")
        
        # 通知全局观察者
        for observer in self._global_observers:
            try:
                observer.on_setting_changed(event)
            except Exception as e:
                logger.error(f"Global observer error: {e}")
    
    def clear_observers(self) -> None:
        """清除所有观察者"""
        self._observers.clear()
        self._global_observers.clear()

# 全局观察者管理器实例
global_observer_manager = SettingObserverManager()

class UIComponentObserver(SettingObserver):
    """UI组件观察者"""
    
    def __init__(self, component):
        self.component = component
    
    def on_setting_changed(self, event: SettingChangeEvent) -> None:
        """UI组件设置变更响应"""
        try:
            # 根据设置键处理不同的变更
            if event.setting_key == "appearance.theme":
                self._handle_theme_change(event.new_value)
            elif event.setting_key == "reading.font_size":
                self._handle_font_size_change(event.new_value)
            elif event.setting_key == "reading.line_spacing":
                self._handle_line_spacing_change(event.new_value)
            elif event.setting_key.startswith("reading."):
                self._handle_reading_setting_change(event.setting_key, event.new_value)
            elif event.setting_key.startswith("appearance."):
                self._handle_appearance_setting_change(event.setting_key, event.new_value)
            
            # 触发组件重新渲染
            if hasattr(self.component, 'refresh'):
                self.component.refresh()
                
        except Exception as e:
            logger.error(f"UI component observer error: {e}")
    
    def _handle_theme_change(self, new_theme: str) -> None:
        """处理主题变更"""
        if hasattr(self.component, 'apply_theme'):
            self.component.apply_theme(new_theme)
    
    def _handle_font_size_change(self, new_size: int) -> None:
        """处理字体大小变更"""
        if hasattr(self.component, 'update_font_size'):
            self.component.update_font_size(new_size)
    
    def _handle_line_spacing_change(self, new_spacing: float) -> None:
        """处理行间距变更"""
        if hasattr(self.component, 'update_line_spacing'):
            self.component.update_line_spacing(new_spacing)
    
    def _handle_reading_setting_change(self, setting_key: str, new_value: Any) -> None:
        """处理阅读设置变更"""
        # 通用的阅读设置变更处理
        if hasattr(self.component, 'update_reading_config'):
            self.component.update_reading_config({setting_key: new_value})
    
    def _handle_appearance_setting_change(self, setting_key: str, new_value: Any) -> None:
        """处理外观设置变更"""
        # 通用的外观设置变更处理
        if hasattr(self.component, 'update_appearance_config'):
            self.component.update_appearance_config({setting_key: new_value})

class ContentRendererObserver(SettingObserver):
    """内容渲染器观察者"""
    
    def __init__(self, renderer):
        self.renderer = renderer
    
    def on_setting_changed(self, event: SettingChangeEvent) -> None:
        """内容渲染器设置变更响应"""
        try:
            if event.setting_key in ["reading.font_size", "reading.line_spacing", 
                                   "appearance.theme"]:
                # 这些设置变更需要重新分页和渲染
                if hasattr(self.renderer, '_paginate'):
                    self.renderer._paginate()
                if hasattr(self.renderer, 'refresh'):
                    self.renderer.refresh()
                    
        except Exception as e:
            logger.error(f"Content renderer observer error: {e}")

class StatisticsObserver(SettingObserver):
    """统计组件观察者"""
    
    def __init__(self, statistics_component):
        self.statistics = statistics_component
    
    def on_setting_changed(self, event: SettingChangeEvent) -> None:
        """统计组件设置变更响应"""
        try:
            if event.setting_key == "reading.show_stats":
                # 显示/隐藏统计信息
                if hasattr(self.statistics, 'set_visible'):
                    self.statistics.set_visible(event.new_value)
                    
        except Exception as e:
            logger.error(f"Statistics observer error: {e}")

# 工具函数
def register_component_observers(component, setting_keys: Optional[List[str]] = None) -> None:
    """注册组件观察者"""
    observer = UIComponentObserver(component)
    if setting_keys:
        for key in setting_keys:
            global_observer_manager.register_observer(observer, key)
    else:
        global_observer_manager.register_observer(observer)

def notify_setting_change(setting_key: str, old_value: Any, new_value: Any, source: str = "user") -> None:
    """通知设置变更"""
    event = SettingChangeEvent(setting_key, old_value, new_value, source)
    global_observer_manager.notify_setting_changed(event)

def register_global_observer(observer: SettingObserver) -> None:
    """注册全局观察者"""
    global_observer_manager.register_observer(observer)

def unregister_global_observer(observer: SettingObserver) -> None:
    """取消注册全局观察者"""
    global_observer_manager.unregister_observer(observer)