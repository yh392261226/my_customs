"""支持边界方向键自动翻页的 DataTable。

在表格最后一行按 ↓ 自动翻到下一页并把光标置于新页首行；
在第一行按 ↑ 自动翻到上一页并把光标置于新页末行。

通过重写 ``action_cursor_down`` / ``action_cursor_up`` 实现，使翻页逻辑
与 Textual 原生的光标移动绑定到同一个动作上，避免屏幕 ``on_key`` 与
DataTable 原生绑定重复处理导致的不一致（三个页面行为各异）问题。

宿主屏幕需提供：
    * ``_go_to_next_page()`` / ``_go_to_prev_page()`` 方法
    * ``_current_page`` / ``_total_pages``（或 ``current_page`` / ``total_pages``）属性
"""

from __future__ import annotations

from typing import Optional

from textual.app import App
from textual.widgets import DataTable


class PagingDataTable(DataTable):
    """带边界自动翻页的 DataTable。"""

    def _screen_page(self, screen) -> object:
        """读取宿主屏幕的当前页码（兼容下划线/无下划线命名）。"""
        for attr in ("_current_page", "current_page"):
            if hasattr(screen, attr):
                return getattr(screen, attr)
        return None

    @staticmethod
    def _page_size(screen) -> Optional[int]:
        """读取宿主屏幕的每页行数（兼容多种命名）。"""
        for attr in ("_books_per_page", "_sites_per_page", "items_per_page",
                     "page_size", "pageSize"):
            val = getattr(screen, attr, None)
            if isinstance(val, int) and val > 0:
                return val
        return None

    @staticmethod
    def move_pending(
        tbl: "DataTable",
        pending: Optional[str],
        page_n: int = 0,
        app: Optional[App] = None,
    ) -> None:
        """将光标移动到新页首/末行，兼容行坐标异步刷新与焦点重置。

        两个真实环境的坑：
        1. 宿主在重填表格后通常会 ``table.focus()``，焦点回调会在随后的
           refresh 周期内把光标重置回 ``(0, 0)``。若我们先于该刷新同步地
           ``move_cursor``，会被覆盖回首行。因此首次尝试延后到下一帧
           （优先 ``app.call_later``，其次 ``call_after_refresh``）执行。
        2. 末行目标用“表格实际最后一行” ``rows - 1``，而非依赖 ``page_n``，
           这样不满页的最后一页也能正确落在真正末行。
        """
        if pending is None:
            return

        def _try() -> bool:
            try:
                rows = len(tbl.rows)
                if pending == "first":
                    target = 0
                else:
                    target = max(0, rows - 1)
                if rows > 0 and 0 <= target < rows:
                    tbl.move_cursor(row=target, column=0)
                    return True
            except Exception:
                pass
            return False

        def _attempt(remaining: int) -> None:
            if _try() or remaining <= 0:
                return
            try:
                if hasattr(tbl, "call_after_refresh"):
                    tbl.call_after_refresh(lambda: _attempt(remaining - 1))
                    return
            except Exception:
                pass
            try:
                if app is not None:
                    app.call_later(lambda: _attempt(remaining - 1))
            except Exception:
                pass

        # 延后首次尝试，确保发生在 table.focus() 触发的光标重置之后。
        try:
            if app is not None:
                app.call_later(lambda: _attempt(20))
            elif hasattr(tbl, "call_after_refresh"):
                tbl.call_after_refresh(lambda: _attempt(20))
            else:
                _attempt(20)
        except Exception:
            _attempt(20)

    def action_cursor_down(self) -> None:
        """下键：在末行边界自动翻到下一页，否则按原生方式下移。

        边界判定使用宿主屏幕的“每页行数”，而非 ``len(self.rows)`` ——因为
        真实环境里表格可能加载了超过一页的行（虚拟滚动/累加），此时
        ``cursor_row == len(self.rows) - 1`` 在页内末行永远不成立，导致
        无法翻页（卡在第一页末行）。用页大小取模判定可稳定命中页边界。
        """
        screen = self.screen
        cr = self.cursor_row
        if cr is not None and hasattr(screen, "_go_to_next_page"):
            ps = self._page_size(screen)
            if ps is not None:
                if (cr + 1) % ps == 0:
                    screen._go_to_next_page()
                    return
            elif cr == len(self.rows) - 1:
                screen._go_to_next_page()
                return
        super().action_cursor_down()

    def action_cursor_up(self) -> None:
        """上键：在首行边界自动翻到上一页，否则按原生方式上移。"""
        screen = self.screen
        cr = self.cursor_row
        if cr is not None and hasattr(screen, "_go_to_prev_page"):
            ps = self._page_size(screen)
            if ps is not None:
                if cr % ps == 0:
                    screen._go_to_prev_page()
                    return
            elif cr == 0:
                screen._go_to_prev_page()
                return
        super().action_cursor_up()
