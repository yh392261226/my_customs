"""
虚拟滚动数据表组件，优化大量数据的渲染性能
"""

from typing import Dict, List, Any, Optional, Tuple
from textual.widgets import DataTable
from textual.reactive import reactive
from textual import events

class VirtualDataTable(DataTable):
    """虚拟滚动数据表，支持大量数据的高效渲染"""
    
    # 事件类定义
    class CellSelected(events.Event):
        """单元格选中事件"""
        def __init__(self, cell_key, value, coordinate, control=None) -> None:
            self.cell_key = cell_key
            self.value = value
            self.coordinate = coordinate
            self.control = control
            super().__init__()
    
    class RowSelected(events.Event):
        """行选中事件"""
        def __init__(self, row_key, control=None) -> None:
            self.row_key = row_key
            self.control = control
            super().__init__()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._virtual_data: List[Dict[str, Any]] = []
        self._total_rows = 0
        self._buffer_size = 100  # 缓冲区大小，渲染前后各100行
        self._scroll_offset = 0  # 当前滚动偏移
        self._last_rendered_range = (0, 0)  # 上次渲染的范围
        self._render_throttle_ms = 50  # 渲染节流时间（毫秒）
        self._last_render_time = 0  # 上次渲染时间
        self._current_data: Dict[str, Dict[str, Any]] = {}  # 存储当前显示的数据，键为row_key
        
    def set_virtual_data(self, data: List[Dict[str, Any]]) -> None:
        """设置虚拟数据并重新渲染"""
        self._virtual_data = data
        self._total_rows = len(data)
        
        # 清除现有行数据，但保留列定义
        # 只清除行，不清除列
        for row_key in list(self.rows.keys()):
            self.remove_row(row_key)
        
        # 清空当前数据
        self._current_data.clear()
        
        self._render_current_view()
        
    def _render_current_view(self) -> None:
        """渲染当前可见范围内的数据"""
        # 计算可见范围
        visible_start = max(0, self._scroll_offset)
        visible_end = min(self._total_rows, self._scroll_offset + self._buffer_size)
        
        # 渲染可见行
        visible_rows = self._virtual_data[visible_start:visible_end]
        for i, row_data in enumerate(visible_rows):
            row_idx = visible_start + i
            # 使用行极键（如果存在），否则使用索引
            row_key = row_data.get('_row_key', str(row_idx))
            row_values = self._format_row_data(row_data, row_idx)
            
            # 存储到当前数据字典
            self._current_data[row_key] = row_data
            
            try:
                self.add_row(*row_values, key=row_key)
            except Exception as e:
                # 尝试不使用key
                try:
                    self.add_row(*row_values)
                except Exception as e2:
                    pass
        
        # 更新上次渲染范围
        self._last_rendered_range = (visible_start, visible_end)
    
    def _format_row_data(self, row_data: Dict[str, Any], row_index: int) -> List[Any]:
        """格式化行数据"""
        # 直接返回所有值，除了内部字段
        excluded_keys = {'_row_key', '_global_index'}
        row_values = []
        
        # 按照添加列的顺序获取数据
        if hasattr(self, 'columns') and self.columns:
            for col in self.columns:
                # col本身就是ColumnKey对象，需要使用.value属性获取实际的键值
                if hasattr(col, 'value'):
                    col_key = str(col.value)
                    if col_key in row_data:
                        row_values.append(row_data[col_key])
                    else:
                        row_values.append('')
                else:
                    # 如果没有value属性，使用空字符串
                    row_values.append('')
        else:
            # 如果没有列信息，按数据顺序返回
            for key, value in row_data.items():
                if key not in excluded_keys:
                    row_values.append(value)
        
        return row_values