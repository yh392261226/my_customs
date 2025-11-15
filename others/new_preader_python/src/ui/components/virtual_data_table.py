"""
虚拟滚动数据表组件，优化大量数据的渲染性能
"""

from typing import Dict, List, Any, Optional, Tuple
from textual.widgets import DataTable
from textual.reactive import reactive
from textual import events

class VirtualDataTable(DataTable):
    """虚拟滚动数据表，支持大量数据的高效渲染"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._virtual_data: List[Dict[str, Any]] = []
        self._total_rows = 0
        self._buffer_size = 100  # 缓冲区大小，渲染前后各100行
        self._scroll_offset = 0  # 当前滚动偏移
        self._last_rendered_range = (0, 0)  # 上次渲染的范围
        self._render_throttle_ms = 50  # 渲染节流时间（毫秒）
        self._last_render_time = 0  # 上次渲染时间
        
    def set_virtual_data(self, data: List[Dict[str, Any]]) -> None:
        """设置虚拟数据并重新渲染"""
        self._virtual_data = data
        self._total_rows = len(data)
        
        print(f"DEBUG set_virtual_data: 接收到 {len(data)} 行数据")
        if data:
            print(f"DEBUG set_virtual_data: 第一行数据键: {list(data[0].keys())}")
        
        # 清除现有行数据，保留列定义
        self.clear()
        
        # 调试：检查列信息
        if hasattr(self, 'columns') and self.columns:
            print(f"DEBUG set_virtual_data: VirtualDataTable 列数量: {len(self.columns)}")
            for i, col in enumerate(self.columns):
                if hasattr(col, 'key'):
                    key_val = col.key.value if hasattr(col.key, 'value') else col.key
                    print(f"DEBUG set_virtual_data: 列 {i}: key={key_val}")
                else:
                    print(f"DEBUG set_virtual_data: 列 {i}: 没有 key 属性, 列对象: {col}")
        else:
            print("DEBUG set_virtual_data: VirtualDataTable 没有列信息")
        
        self._render_current_view()
        
    def _render_current_view(self) -> None:
        """渲染当前可见范围内的数据"""
        # 计算可见范围
        visible_start = max(0, self._scroll_offset)
        visible_end = min(self._total_rows, self._scroll_offset + self._buffer_size)
        
        # 性能优化：避免不必要的重渲染
        if self._last_rendered_range == (visible_start, visible_end):
            # 即使范围相同，也强制重新渲染以确保数据显示
            print(f"DEBUG _render_current_view: 范围相同但强制重渲染 {self._last_rendered_range} -> ({visible_start}, {visible_end})")
        
        # 清除现有行（但保留列）
        self.clear()
        
        # 渲染可见行
        visible_rows = self._virtual_data[visible_start:visible_end]
        for i, row_data in enumerate(visible_rows):
            row_idx = visible_start + i
            # 使用行极键（如果存在），否则使用索引
            row_key = row_data.get('_row_key', str(row_idx))
            row_values = self._format_row_data(row_data, row_idx)
            self.add_row(*row_values, key=row_key)
        
        # 更新上次渲染范围
        self._last_rendered_range = (visible_start, visible_end)
        
        print(f"DEBUG _render_current_view: 渲染了 {len(visible_rows)} 行，范围 {visible_start}-{visible_end}")
    
    def _format_row_data(self, row_data: Dict[str, Any], row_index: int) -> List[Any]:
        """格式化行数据"""
        # 使用全局索引而不是当前页的索引
        display_index = row_data.get('_global_index', row_index + 1)
        
        # 简化列键获取逻辑，直接使用硬编码的列键顺序
        # 这样可以避免 Textual DataTable 内部列结构的问题
        column_keys = ['id', 'title', 'author', 'format', 'size_display', 'last_read', 
                      'progress', 'tags', 'read_action', 'view_action', 'rename_action', 'delete_action']
        
        # 根据固定的列键顺序构建数据
        row_values = []
        for col_key in column_keys:
            if col_key == 'id':
                row_values.append(str(display_index))
            elif col_key in row_data:
                row_values.append(row_data[col_key])
            else:
                # 如果数据中没有对应的键，使用空字符串
                row_values.append('')
        
        return row_values

    def scroll_to_row(self, row_index: int) -> None:
        """滚动到指定行"""
        if 0 <= row_index < self._total_rows:
            self._scroll_offset = row_index
            self._render_current_view()
        else:
            # 边界检查：确保滚动偏移在有效范围内
            self._scroll_offset = max(0, min(row_index, self._total_rows - 1))
            self._render_current_view()

    def scroll_by(self, amount: int) -> None:
        """按指定行数滚动"""
        self.scroll_to_row(self._scroll_offset + amount)

    def get_current_view(self) -> Tuple[int, int]:
        """获取当前可见范围"""
        visible_start = self._scroll_offset
        visible_end = min(self._total_rows, visible_start + self._buffer_size)
        return (visible_start, visible_end)

    def on_scroll(self, event: events.Scroll) -> None:
        """处理滚动事件"""
        super().on_scroll(event)
        
        # 获取滚动事件信息
        scroll_delta_y = getattr(event, 'delta_y', 0) or 0
        scroll_delta_x = getattr(event, 'delta_x', 0) or 0
        
        # 计算滚动方向和距离
        scroll_rows = abs(scroll_delta_y)
        if scroll_delta_y != 0:
            # 处理垂直滚动
            direction = -1 if scroll_delta_y > 0 else 1
            new_offset = self._scroll_offset + direction * int(scroll_rows * 3)  # 加速滚动
            
            # 边界检查
            new_offset = max(0, min(new_offset, self._total_rows - 1))
            
            # 只有偏移改变时才重新渲染
            if new_offset != self._scroll_offset:
                self._scroll_offset = new_offset
                self._render_current_view()
            
            event.prevent_default()
    
    def on_mount(self) -> None:
        """组件挂载时的回调"""
        # 确保组件能够接收焦点和事件
        self.can_focus = True
        self.focus()
    
    def on_key(self, event) -> None:
        """处理键盘事件"""
        if event.key == "up":
            self.scroll_by(-1)
            event.prevent_default()
        elif event.key == "down":
            self.scroll_by(1)
            event.prevent_default()
        elif event.key == "pageup":
            self.scroll_by(-self._buffer_size // 2)
            event.prevent_default()
        elif event.key == "pagedown":
            self.scroll_by(self._buffer_size // 2)
            event.prevent_default()
        elif event.key == "home":
            self.scroll_to_row(0)
            event.prevent_default()
        elif event.key == "end":
            self.scroll_to_row(self._total_rows - 1)
            event.prevent_default()
        else:
            # 其他按键交给父类处理
            pass
    
    def set_buffer_size(self, size: int) -> None:
        """设置缓冲区大小"""
        self._buffer_size = max(10, min(size, 500))  # 限制缓冲区大小范围
        self._render_current_view()
    
    def get_total_rows(self) -> int:
        """获取总行数"""
        return self._total_rows
    
    def get_current_offset(self) -> int:
        """获取当前滚动偏移"""
        return self._scroll_offset
    
    def get_visible_range(self) -> Tuple[int, int]:
        """获取当前可见范围"""
        return self._last_rendered_range
    
    def scroll_to_top(self) -> None:
        """滚动到顶部"""
        self.scroll_to_row(0)
    
    def scroll_to_bottom(self) -> None:
        """滚动到底部"""
        self.scroll_to_row(self._total_rows - 1)
    
    def get_scroll_progress(self) -> float:
        """获取滚动进度 (0.0 到 1.0)"""
        if self._total_rows <= 1:
            return 0.0
        return self._scroll_offset / (self._total_rows - 1)
    
    def set_scroll_progress(self, progress: float) -> None:
        """设置滚动进度 (0.0 到 1.0)"""
        if self._total_rows > 1:
            target_row = int(progress * (self._total_rows - 1))
            self.scroll_to_row(target_row)
    
    def get_current_visible_data(self) -> List[Dict[str, Any]]:
        """获取当前可见的数据"""
        visible_start, visible_end = self._last_rendered_range
        return self._virtual_data[visible_start:visible_end]
    
    def get_row_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """通过索引获取行数据"""
        if 0 <= index < self._total_rows:
            return self._virtual_data[index]
        return None