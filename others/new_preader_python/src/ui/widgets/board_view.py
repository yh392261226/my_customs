"""只读“看板 / 项目视图”组件。

设计原则：完全不触碰任何现有 ``DataTable`` 的用法（其 ``id``、类型、
方法、事件、CSS 一律保留）。``BoardView`` 是一个**独立的只读组件**，仅在
用户切换视图时，读取目标 ``DataTable`` 的公开数据
（``columns`` / ``rows`` / ``get_row_at``）生成卡片式浏览界面。

自动同步：源 ``DataTable``（如翻页、刷新）重新填充数据时，本组件会监听
其行 key 集合的变化并自动重建卡片，因此翻页在看板模式下同样有效。

单元格可点击：卡片中每个字段都是一个可点击单元，点击会向源 ``DataTable``
转发一条 ``DataTable.CellSelected`` 消息（携带正确的 row/column 坐标），
从而**原样复用**屏幕里已有的单元格点击处理逻辑（如阅读/查看文件/删除等
按钮列，以及标题复制、列筛选等），无需在屏幕中添加任何新代码。

视觉：值为 ``[xxx]`` 形式的字段被识别为“操作按钮”，单独排成卡片底部的
自适应按钮条（去掉方括号、紧凑样式，按卡片宽度动态决定每行按钮数并自动
分行），其余字段仍按 ``标签: 值`` 展示。
"""
from __future__ import annotations

import logging
import re
from typing import Iterator, List, Optional, Tuple

logger = logging.getLogger(__name__)

from textual.coordinate import Coordinate
from textual.containers import Container, Horizontal, ItemGrid, Vertical, VerticalScroll
from textual.widgets import DataTable, Input, Static
from rich.cells import cell_len
from rich.text import Text

# 形如 `[阅读]` / `[删除]` 的单元格值，识别为“操作按钮”
_ACTION_RE = re.compile(r"^\[[^\]]+\]$")


def _is_action_value(value: object) -> bool:
    return bool(_ACTION_RE.match(str(value).strip()))


class BoardField(Static):
    """卡片中的单个可点击字段（对应源表的一列）。"""

    DEFAULT_CSS = """
    BoardField {
        width: 1fr;
        /* 关键：很多屏幕的隔离 CSS 含有 “#xxx-preview Static { height: 100%;
           min-height: 0 }” 之类规则（经 universal_style_isolation 加前缀后
           优先级很高），会把看板里的 BoardField（Static 子类）高度压成 0、
           文字被裁掉，表现为“有边框、没文字”。这里用 !important 强制自然
           高度，盖过这些宿主屏幕的样式。 */
        height: auto !important;
        min-height: 1 !important;
    }
    BoardField:hover {
        background: $accent 25%;
        text-style: bold;
    }
    /* 操作按钮样式：单行紧凑“药丸”，避免方框把卡片撑高 */
    BoardField.board-action {
        width: auto;
        height: 1 !important;
        min-height: 1 !important;
        border: none;
        background: $primary 30%;
        text-style: bold;
        text-align: center;
        padding: 0 1;
        margin-right: 1;
    }
    BoardField.board-action:hover {
        background: $primary 55%;
    }
    """

    def __init__(
        self,
        label: str,
        value: object,
        row: int,
        col: int,
        source: DataTable,
        is_action: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._value = value
        self._row = row
        self._col = col
        self._source = source
        self._is_action = is_action
        if is_action:
            self.add_class("board-action")
        # 用 inline style 锁定高度，确保盖过宿主屏幕隔离 CSS 对 Static 的
        # “height: 100%; min-height: 0” 覆盖（该规则会把字段高度压成 0，
        # 表现为有边框、没文字）。inline style 优先级高于所有 stylesheet，
        # 包括 !important 与注入的隔离样式，因此对所有屏幕都生效。
        self.styles.height = "1" if is_action else "auto"
        self.styles.min_height = "1"

    def render(self) -> Text:
        if self._is_action:
            # 去掉方括号，只显示按钮文字，更像按钮
            text = Text(BoardField._action_label(self._value), style="bold")
            return text
        text = Text()
        text.append(self._label + ": ", style="bold")
        text.append(str(self._value))
        return text

    @staticmethod
    def _action_label(value: object) -> str:
        """操作按钮的展示文字：去掉首尾方括号。"""
        txt = str(value).strip()
        if txt.startswith("[") and txt.endswith("]"):
            txt = txt[1:-1]
        return txt

    def on_mouse_down(self, event) -> None:
        """点击字段 → 向源表转发 CellSelected，复用其单元格处理逻辑。"""
        event.stop()
        # 必须带上正确的 cell_key（含 column_key / row_key）：依赖
        # ``event.cell_key`` 的屏幕（如爬取管理页）用它定位操作列与行，
        # 若传 None 会因访问 .column_key 抛异常而被静默吞掉，按钮失效。
        cell_key = self._source.coordinate_to_cell_key(
            Coordinate(self._row, self._col)
        )
        self._source.post_message(
            DataTable.CellSelected(
                self._source,
                self._value,
                Coordinate(self._row, self._col),
                cell_key,
            )
        )


class BoardCard(Container):
    """单张卡片，展示一行数据的各个字段（每个字段可点击）。"""

    can_focus = True  # 允许方向键聚焦卡片，支持键盘选择/选中

    # 自适应按钮条：每行最多列数（太宽反而难看），至少为 1
    MAX_ACTION_COLS = 4
    # 按钮药丸的固定开销（左右内边距各 1）= 2 字符宽
    ACTION_BTN_OVERHEAD = 2

    DEFAULT_CSS = """
    BoardCard {
        height: auto;
        width: 1fr;
        border: round $panel;
        padding: 0 1;
        background: $boost;
    }
    BoardCard:hover {
        border: round $accent;
    }
    BoardCard:focus {
        border: thick $accent;
        background-tint: $accent 30%;
    }
    BoardCard:focus:hover {
        border: thick $accent;
        background-tint: $accent 45%;
    }
    BoardCard .board-actions {
        height: auto;
        width: 1fr;
        margin-top: 0;
    }
    """

    def __init__(
        self,
        fields: List[Tuple[str, object]],
        row: int,
        source: DataTable,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._fields = fields
        self._row = row
        self._source = source
        self._action_fields: List[Tuple[str, object, int]] = []
        self._action_container: Optional[Vertical] = None

    def compose(self):
        for col, (label, value) in enumerate(self._fields):
            if _is_action_value(value):
                self._action_fields.append((label, value, col))
            else:
                yield BoardField(label, value, self._row, col, self._source, is_action=False)
        # 操作按钮单独排在卡片底部的“按钮条”，按卡片宽度自动分行（用 Horizontal
        # 行而非 Grid，避免本版本 Grid 在嵌套布局下不生效导致按钮整体消失）。
        if self._action_fields:
            self._action_container = Vertical(classes="board-actions")
            yield self._action_container

    def on_mount(self) -> None:
        # 等布局完成后拿到真实卡片宽度再决定每行按钮数
        self.call_after_refresh(self._relayout_actions)

    def on_resize(self, event) -> None:
        self._relayout_actions()

    def _relayout_actions(self) -> None:
        """按卡片实际宽度与最长按钮文字，动态决定每行按钮数并分行。

        放得下就尽量多排（紧凑），放不下就减少每行列数乃至每行一个，确保
        **任何长度的按钮、任何数量的按钮都不会被裁切**，且都能渲染出来。
        """
        container = self._action_container
        if container is None or not self._action_fields:
            return
        card_w = self.content_size.width
        if card_w <= 0:
            return
        gutter = 1
        labels = [BoardField._action_label(v) for _, v, _ in self._action_fields]
        max_need = max(cell_len(t) for t in labels) + self.ACTION_BTN_OVERHEAD
        # 能容纳的最大每行列数： cols*(need+gutter) - gutter <= card_w
        best = (card_w + gutter) // (max_need + gutter)
        best = max(1, min(len(self._action_fields), best, self.MAX_ACTION_COLS))
        # 重建分行：每 best 个按钮排成一行 Horizontal
        container.remove_children()
        for i in range(0, len(self._action_fields), best):
            chunk = self._action_fields[i:i + best]
            buttons = []
            for label, value, col in chunk:
                bf = BoardField(label, value, self._row, col, self._source, is_action=True)
                bf.styles.width = str(
                    cell_len(BoardField._action_label(value)) + self.ACTION_BTN_OVERHEAD
                )
                buttons.append(bf)
            # 用构造参数把按钮作为子节点传入，整行一起挂载（子树挂载更可靠）
            row = Horizontal(*buttons)
            # 关键：Container 默认 height:1fr 会把每一行按钮条拉伸到整卡高度，
            # 导致卡片被撑到上百行、按钮之间“隔很远”、末位按钮被挤出可视区。
            # 显式限定为 1 行，按钮条才会按内容紧凑排列。
            row.styles.height = 1
            container.mount(row)


class BoardView(Container):
    """``DataTable`` 的只读看板镜像。切换时挂载，切回时卸载。"""

    DEFAULT_CSS = """
    BoardView {
        width: 1fr;
        height: 1fr;
    }
    BoardView > VerticalScroll {
        width: 1fr;
        height: 1fr;
    }
    """

    # 轮询间隔（秒）：检测源表数据变化并重建看板
    SYNC_INTERVAL = 0.3

    def __init__(
        self,
        source: DataTable,
        min_column_width: int = 30,
        on_reach_next: Optional[callable] = None,
        on_reach_prev: Optional[callable] = None,
        **kwargs,
    ) -> None:
        """
        Args:
            source: 要镜像的 ``DataTable``（其 ``id`` 会被用于派生看板 id）。
            min_column_width: 看板每列最小字符宽度，控制自适应列数。
            on_reach_next: 在当前页最后一张按 ``down`` 时调用（翻下一页）；
                传 None 则停在末张不翻页。
            on_reach_prev: 在当前页第一张按 ``up`` 时调用（翻上一页）；
                传 None 则停在第一张不翻页。
        """
        super().__init__(**kwargs)
        self._source = source
        self._min_column_width = min_column_width
        self._grid: Optional[ItemGrid] = None
        self._last_sig: Optional[int] = None
        self._timer = None
        self._on_reach_next = on_reach_next
        self._on_reach_prev = on_reach_prev
        # 翻页后期望聚焦的位置（'first'/'last'/'None'），由 on_key 越界时设置，
        # 在 _rebuild 末尾消费并复位，确保翻页后焦点落在正确的卡片上。
        self._post_rebuild_focus: Optional[str] = None
        # 最近一次聚焦卡片的“页内行号”，用于在翻页时焦点被转移到隐藏源表
        # （屏幕 _update_history_table 会 move_cursor 源表）后仍能保持原行位置，
        # 而不是盲目兜底回到首张。
        self._last_focused_row: Optional[int] = None

    @staticmethod
    def board_id_for(table: DataTable) -> Optional[str]:
        """给定表格，返回其对应看板组件的 id（无表 id 时返回 None）。"""
        return f"{table.id}-board" if table.id else None

    @property
    def source(self) -> DataTable:
        """本看板镜像的源 ``DataTable``（用于切回表格模式）。"""
        return self._source

    # ------------------------------------------------------------------ #
    # 数据读取
    # ------------------------------------------------------------------ #
    def _signature(self) -> int:
        """源表行 key 集合的哈希；翻页/刷新会改变它（行数可能不变）。"""
        try:
            return hash(tuple(self._source.rows.keys()))
        except Exception:
            return -1

    def _selected_column_index(self) -> Optional[int]:
        """返回源表中 key 为 'selected' 的列索引（用于键盘选中）；无则 None。"""
        try:
            for j, col in enumerate(self._source.columns.values()):
                key = getattr(col.key, "value", col.key)
                if key == "selected":
                    return j
        except Exception:
            return None
        return None

    def _selected_sig(self) -> int:
        """``selected`` 列内容的指纹；切换选中状态会改变它，从而触发看板刷新。"""
        idx = self._selected_column_index()
        if idx is None:
            return 0
        try:
            vals = []
            for i in range(self._source.row_count):
                cells = self._source.get_row_at(i)
                vals.append(cells[idx] if idx < len(cells) else "")
            return hash(tuple(vals))
        except Exception:
            return 0

    def _col_labels(self) -> List[str]:
        labels: List[str] = []
        for col in self._source.columns.values():
            label = col.label
            labels.append(label.plain if hasattr(label, "plain") else str(label))
        return labels

    def _card_widgets(self) -> Iterator[BoardCard]:
        """根据源表当前行生成卡片。

        健壮性要点：单行 ``get_row_at`` 失败**只跳过该行**（continue），不会让整页
        看板变空白；本版本 ``Row`` 无 ``.cells`` 属性，故仅依赖公开的 ``get_row_at``。
        """
        col_labels = self._col_labels()
        card_count = 0
        for i, _row_meta in enumerate(self._source.rows.values()):
            try:
                cells = self._source.get_row_at(i)
            except Exception as exc:
                logger.warning("[BoardView] 第 %d 行 get_row_at 异常: %r", i, exc)
                continue
            fields = [
                (col_labels[j], cells[j])
                for j in range(min(len(col_labels), len(cells)))
            ]
            card_count += 1
            yield BoardCard(fields, row=i, source=self._source)
        logger.debug("[BoardView] 构建完成, 产出卡片数=%d", card_count)

    # ------------------------------------------------------------------ #
    # 生命周期
    # ------------------------------------------------------------------ #
    def compose(self):
        with VerticalScroll():
            with ItemGrid(
                min_column_width=self._min_column_width,
                stretch_height=False,
            ) as grid:
                self._grid = grid
                yield from self._card_widgets()

    def on_mount(self) -> None:
        self._last_sig = (self._signature(), self._selected_sig())
        self._timer = self.set_interval(self.SYNC_INTERVAL, self._check_changes)
        # 首次立即渲染看板（不等 _check_changes 的“无变化”判定），保证一进看板就有卡片
        self.run_worker(self._rebuild(), name="board-rebuild", exclusive=True)
        # 兜底重建：若 compose 时刻源表行尚未就绪（为空），首帧拿不到数据会出空白
        # 看板；稍后延时再重建一次，等源表数据就绪后即可正常出卡。真实运行环境里
        # run_worker 正常工作（仅 headless 测试退出时会因 worker 等待而看起来卡住）。
        self.set_timer(0.6, lambda: self.call_after_refresh(self._check_changes))
        # 布局稳定后用真实卡片宽度重排按钮。初次 on_mount 时 ItemGrid 可能还没把
        # 卡片收窄，导致各卡片按偏大的宽度算出行数、其余按钮被横向裁切；延时一次
        # 用正确窄宽度重新分行即可彻底解决。
        self.set_timer(0.2, self._relayout_all_cards)

    def on_resize(self, event) -> None:
        self._relayout_all_cards()

    def _relayout_all_cards(self) -> None:
        for card in self.query(BoardCard):
            card._relayout_actions()

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    # ------------------------------------------------------------------ #
    # 自动同步
    # ------------------------------------------------------------------ #
    def _check_changes(self) -> None:
        sig = (self._signature(), self._selected_sig())
        if sig == self._last_sig:
            return
        self._last_sig = sig
        self.run_worker(self._rebuild(), name="board-rebuild", exclusive=True)

    async def _rebuild(self) -> None:
        grid = self._grid
        if grid is None:
            return
        # 记录当前焦点所在的行，便于重建后恢复“光标行”，避免键盘焦点丢失
        focused_row: Optional[int] = None
        cur_focus = self.screen.focused
        focus_in_input = isinstance(cur_focus, Input)
        if isinstance(cur_focus, BoardCard):
            focused_row = cur_focus._row
        grid.remove_children()
        cards = list(self._card_widgets())
        if cards:
            await grid.mount_all(cards)
        if self._post_rebuild_focus == "first":
            # 翻到下一页后：对焦新页首张
            if cards:
                cards[0].focus()
                self._last_focused_row = cards[0]._row
            self._post_rebuild_focus = None
        elif self._post_rebuild_focus == "last":
            # 翻到上一页后：对焦新页末张
            if cards:
                cards[-1].focus()
                self._last_focused_row = cards[-1]._row
            self._post_rebuild_focus = None
        elif isinstance(cur_focus, BoardCard):
            # 焦点仍在卡片上：保持所在行（页内行号相同即同一张卡片）
            for c in cards:
                if c._row == focused_row:
                    c.focus()
                    self._last_focused_row = c._row
                    break
        elif self._last_focused_row is not None:
            # 焦点被转移到隐藏源表/其它控件（翻页时屏幕会 move_cursor 源表），
            # 保持上一次的卡片行位置，而不是盲目回退到首张。
            for c in cards:
                if c._row == self._last_focused_row:
                    c.focus()
                    break
            else:
                if cards:
                    cards[0].focus()
                    self._last_focused_row = cards[0]._row
        elif not focus_in_input and cards:
            # 无卡片焦点（如刚进入看板）时自动聚焦首张，便于方向键导航
            cards[0].focus()
            self._last_focused_row = cards[0]._row

    # ------------------------------------------------------------------ #
    # 键盘交互：方向键移动焦点 + 空格/回车切换选中
    # ------------------------------------------------------------------ #
    def _toggle_selected_for_card(self, card: "BoardCard") -> None:
        """切换某卡片对应行的选中状态（转发 selected 列的 CellSelected）。"""
        sel_idx = self._selected_column_index()
        if sel_idx is None:
            return
        src = self._source
        try:
            cells = src.get_row_at(card._row)
            value = cells[sel_idx]
        except Exception:
            return
        cell_key = src.coordinate_to_cell_key(Coordinate(card._row, sel_idx))
        src.post_message(
            DataTable.CellSelected(
                src, value, Coordinate(card._row, sel_idx), cell_key
            )
        )

    def on_key(self, event) -> None:
        cards = list(self.query(BoardCard))
        if not cards:
            return
        cur_focus = self.screen.focused
        # 输入框聚焦时不拦截（交给输入框处理方向键/空格）
        if isinstance(cur_focus, Input):
            return
        if not isinstance(cur_focus, BoardCard):
            # 焦点在其它控件（按钮等）或为空：仅上下键进入卡片行序导航
            # （左右方向键已被屏蔽，不用于进入导航）
            if event.key in ("up", "down"):
                cards[0].focus()
                event.prevent_default()
            return
        try:
            idx = cards.index(cur_focus)
        except ValueError:
            idx = 0
        if event.key == "down":
            # 当前页最后一张再按 down：翻下一页并对焦新页首张（若有翻页回调且真翻了）
            if idx == len(cards) - 1 and self._on_reach_next is not None:
                if self._on_reach_next():
                    self._post_rebuild_focus = "first"
                    self.run_worker(self._rebuild(), name="board-rebuild", exclusive=True)
                    event.prevent_default()
                    return
                # 已是最后一页：停在原地，不环绕到第一张
                event.prevent_default()
                return
            idx = min(idx + 1, len(cards) - 1)
        elif event.key == "up":
            # 当前页第一张再按 up：翻上一页并对焦新页末张（若有翻页回调且真翻了）
            if idx == 0 and self._on_reach_prev is not None:
                if self._on_reach_prev():
                    self._post_rebuild_focus = "last"
                    self.run_worker(self._rebuild(), name="board-rebuild", exclusive=True)
                    event.prevent_default()
                    return
                # 已是第一页：停在原地，不环绕到最后一张
                event.prevent_default()
                return
            idx = max(idx - 1, 0)
        elif event.key in ("left", "right"):
            # 看板卡片即整行数据，无列概念，屏蔽左右方向键
            event.prevent_default()
            return
        elif event.key in ("space", "enter"):
            # 仅当存在 selected 列时接管空格/回车，否则交还屏幕原有快捷键
            if self._selected_column_index() is not None:
                self._toggle_selected_for_card(cur_focus)
                event.prevent_default()
            return
        else:
            return
        cards[idx].focus()
        event.prevent_default()
