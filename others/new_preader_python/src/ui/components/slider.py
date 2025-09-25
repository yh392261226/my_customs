"""
自定义滑动条组件
实现0-5整数值的滑动设置
"""

from textual.widget import Widget
from textual.reactive import reactive
from textual import events
from textual.geometry import Region

class Slider(Widget):
    """
    自定义滑动条组件
    用于设置0-5的整数值
    """
    
    value = reactive(1)
    
    def __init__(
        self,
        min_value: int = 0,
        max_value: int = 5,
        value: int = 1,
        id: str | None = None,
        classes: str | None = None
    ):
        super().__init__(id=id, classes=classes)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self._dragging = False
    
    def on_mount(self) -> None:
        """组件挂载时的初始化"""
        self.styles.width = "100%"
        self.styles.height = 3
        self.styles.background = "gray"
    
    def render(self) -> str:
        """渲染滑动条"""
        # 获取宽度值
        width = int(self.styles.width.value or 20)
        
        # 计算滑块位置
        total_range = self.max_value - self.min_value
        position = int((self.value - self.min_value) / total_range * (width - 3))
        
        # 创建滑动条显示
        track = "─" * (width - 1)
        slider = track[:position] + "●" + track[position + 1:]
        
        # 添加数值标签
        values = " ".join(str(i) for i in range(self.min_value, self.max_value + 1))
        return f"{slider}\n{values}"
    
    def on_click(self, event: events.Click) -> None:
        """点击事件处理"""
        width = self.styles.width.value or 20
        if not width:
            return
            
        # 计算点击位置对应的值
        click_x = event.x - self.region.x
        new_value = int((click_x / width) * (self.max_value - self.min_value)) + self.min_value
        
        # 限制在有效范围内
        new_value = max(self.min_value, min(self.max_value, new_value))
        
        # 更新值并触发事件
        old_value = self.value
        self.value = new_value
        self.emit_changed_event(old_value, new_value)
    
    def on_mouse_down(self, event: events.MouseDown) -> None:
        """鼠标按下事件"""
        self._dragging = True
        self.capture_mouse()
    
    def on_mouse_up(self, event: events.MouseUp) -> None:
        """鼠标释放事件"""
        self._dragging = False
        self.release_mouse()
    
    def on_mouse_move(self, event: events.MouseMove) -> None:
        """鼠标移动事件"""
        width = self.styles.width.value or 20
        if self._dragging and width:
            # 计算拖动位置对应的值
            move_x = event.x - self.region.x
            new_value = int((move_x / width) * (self.max_value - self.min_value)) + self.min_value
            
            # 限制在有效范围内
            new_value = max(self.min_value, min(self.max_value, new_value))
            
            # 更新值并触发事件
            if new_value != self.value:
                old_value = self.value
                self.value = new_value
                self.emit_changed_event(old_value, new_value)
    
    def emit_changed_event(self, old_value: int, new_value: int) -> None:
        """触发值变化事件"""
        self.post_message(self.Changed(self, new_value, old_value))
    
    class Changed(events.Event):
        """滑动条值变化事件"""
        
        def __init__(self, slider: "Slider", value: int, old_value: int):
            super().__init__()
            self.slider = slider
            self.value = value
            self.old_value = old_value