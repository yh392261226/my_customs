"""带自动补全的网站搜索框。

参考 Textual 官方 Widgets 中 Input 的 Country 自动补全交互：在用户键入时，
于输入框下方弹出匹配项下拉列表，支持键盘 ↓/↑ 选择、Enter 选中、Esc 关闭。

匹配维度（不区分大小写）：
    * 网站名称子串
    * 网站网址子串
    * 网站名称的拼音全拼（如 “笔趣阁” -> “biquge”）
    * 网站名称的拼音首字母（如 “笔趣阁” -> “bqg”）

选中候选项后，会把输入框的值设为该网站名称，从而触发屏幕已有的“实时搜索”
（两个目标屏都会在 ``Input.Changed`` 时调用 ``_perform_search``）。

由于当前项目依赖的 Textual 版本未内置 autocomplete，这里自行实现下拉组件。
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from rich.text import Text
from textual import events
from textual.containers import Container
from textual.message import Message
from textual.widgets import Input, Label, ListItem, ListView

from pypinyin import Style, pinyin as _pinyin

# 最多展示的候选数，避免下拉过长
_MAX_SUGGESTIONS = 12
# 候选项显示宽度（字符列），略宽于输入框本身以便完整展示网址
_DROPDOWN_WIDTH = 50


class SiteSearchBox(Container):
    """搜索框 + 自动补全下拉（网站名称 / 拼音 / 网址）。

    用法::

        SiteSearchBox(
            placeholder=...,
            sites_provider=lambda: self.database_manager.get_novel_sites(),
        )

    内部 Input 的 id 固定为 ``novel-sites-search-input``，外部屏幕可直接
    ``query_one("#novel-sites-search-input", Input)`` 读取其值。
    """

    class SiteSelected(Message):
        """选中某候选项后发出（携带网站名称）。"""

        def __init__(self, site_name: str) -> None:
            self.site_name = site_name
            super().__init__()

    DEFAULT_CSS = """
    SiteSearchBox {
        width: 50;
        height: auto;
        position: relative;
    }
    SiteSearchBox > Input {
        width: 100%;
    }
    SiteSearchBox > .site-autocomplete {
        position: absolute;
        overlay: screen;
        offset: 0 3;
        width: 100%;
        min-width: 30;
        max-height: 16;
        height: auto;
        background: $panel;
        border: round $accent;
        display: none;
        overflow-y: auto;
    }
    SiteSearchBox > .site-autocomplete.-visible {
        display: block;
    }
    SiteSearchBox > .site-autocomplete ListItem.-highlight {
        background: $accent 30%;
    }
    SiteSearchBox > .site-autocomplete ListItem:hover {
        background: $accent 20%;
    }
    """

    def __init__(
        self,
        placeholder: str = "",
        sites_provider: Optional[Callable[[], List[Dict]]] = None,
        id: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(id=id, **kwargs)
        self._placeholder = placeholder
        self._sites_provider = sites_provider
        self._sites: List[Dict] = []
        self._py_cache: Dict[int, tuple] = {}
        self._matches: List[Dict] = []
        self._items: List[ListItem] = []
        self._selected = 0
        self._open = False
        self._accepted_value: Optional[str] = None
        self._hide_timer = None

    def compose(self):
        yield Input(
            placeholder=self._placeholder,
            id="novel-sites-search-input",
            classes="novel-sites-search-input",
        )
        yield ListView(
            id="novel-sites-search-suggestions",
            classes="site-autocomplete",
        )

    def on_mount(self) -> None:
        self._input = self.query_one("#novel-sites-search-input", Input)
        self._list = self.query_one("#novel-sites-search-suggestions", ListView)
        # 下拉列表绝不作为焦点目标：避免其出现（overlay:screen）时抢走
        # Input 焦点，导致 Input 失焦触发 on_descendant_blur 而误关下拉；
        # 也避免它自身的 up/down 绑定与容器层导航冲突。
        self._list.can_focus = False
        self._list.can_focus_children = False
        self._hide_timer = None
        self._load_sites()

    # ------------------------------------------------------------------ #
    # 数据
    # ------------------------------------------------------------------ #
    def _load_sites(self) -> None:
        try:
            if self._sites_provider is not None:
                self._sites = list(self._sites_provider()) or []
        except Exception:
            self._sites = []

    def refresh_sites(self) -> None:
        """网站数据变化（增删改）后调用，重新加载候选源（不主动弹出下拉）。"""
        self._py_cache.clear()
        self._load_sites()

    def set_sites(self, sites: List[Dict]) -> None:
        """直接设置候选源（避免重复查询数据库）。"""
        self._py_cache.clear()
        self._sites = list(sites) or []

    def _pinyin(self, site: Dict) -> tuple:
        key = id(site)
        cached = self._py_cache.get(key)
        if cached is not None:
            return cached
        name = site.get("name", "") or ""
        try:
            full = (
                "".join(
                    p[0]
                    for p in _pinyin(name, style=Style.NORMAL, errors="ignore", heteronym=False)
                )
                if name
                else ""
            )
            init = (
                "".join(
                    p[0][0]
                    for p in _pinyin(name, style=Style.FIRST_LETTER, errors="ignore", heteronym=False)
                )
                if name
                else ""
            )
        except Exception:
            full = init = ""
        cached = (full.lower(), init.lower())
        self._py_cache[key] = cached
        return cached

    @staticmethod
    def _match(site: Dict, q: str) -> tuple:
        """返回 (是否匹配, 排序分数)。分数越小越靠前。"""
        name = (site.get("name", "") or "").lower()
        url = (site.get("url", "") or "").lower()
        if name.startswith(q):
            return True, 0
        if url.startswith(q):
            return True, 1
        if q in name:
            return True, 2
        if q in url:
            return True, 3
        py_full, py_init = site.get("_py", ("", ""))
        if q in py_full or q in py_init:
            return True, 4
        return False, 99

    def _search(self, q: str) -> List[Dict]:
        results = []
        for site in self._sites:
            py = self._pinyin(site)
            site["_py"] = py  # 临时挂上拼音，供 _match 使用
            ok, score = self._match(site, q)
            if ok:
                results.append((score, site.get("name", "").lower(), site))
        results.sort(key=lambda x: (x[0], x[1]))
        return [r[2] for r in results[:_MAX_SUGGESTIONS]]

    # ------------------------------------------------------------------ #
    # 下拉渲染与显隐
    # ------------------------------------------------------------------ #
    def _populate_list(self) -> None:
        self._list.clear()
        self._items = []
        for site in self._matches:
            name = site.get("name", "") or ""
            url = site.get("url", "") or ""
            text = Text()
            text.append(name, style="bold")
            if url:
                text.append("  ")
                text.append(url, style="dim")
            item = ListItem(Label(text))
            self._items.append(item)
        for it in self._items:
            self._list.append(it)
        self._highlight()

    def _highlight(self) -> None:
        for i, item in enumerate(self._items):
            if i == self._selected:
                item.add_class("-highlight")
            else:
                item.remove_class("-highlight")
        # 候选数已被 _MAX_SUGGESTIONS(12) 截断且容器 max-height:16，正常不滚动；
        # 仍保留 scroll_visible 以便极端长列表时把高亮项滚入可见区。
        if self._items and 0 <= self._selected < len(self._items):
            try:
                self._items[self._selected].scroll_visible()
            except Exception:
                pass

    def _show(self) -> None:
        # 取消任何待执行的延时隐藏，避免“输入/展开”与“失焦隐藏”竞态
        t = getattr(self, "_hide_timer", None)
        if t is not None:
            try:
                t.stop()
            except Exception:
                pass
            self._hide_timer = None
        self._open = True
        self._list.add_class("-visible")

    def _hide(self) -> None:
        self._open = False
        self._matches = []
        self._selected = 0
        try:
            self._list.remove_class("-visible")
        except Exception:
            pass

    def schedule_hide(self) -> None:
        """失焦后延时关闭（给候选项点击留出时间）。"""
        try:
            self._hide_timer = self.set_timer(0.25, self._hide)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # 交互
    # ------------------------------------------------------------------ #
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "novel-sites-search-input":
            return
        # 正在输入说明焦点仍在输入框，取消任何待执行的延时隐藏
        t = getattr(self, "_hide_timer", None)
        if t is not None:
            try:
                t.stop()
            except Exception:
                pass
            self._hide_timer = None
        value = event.value or ""
        # 选中后程序化赋值会再次触发本事件，用标记跳过下拉重开
        if self._accepted_value is not None and value == self._accepted_value:
            self._accepted_value = None
            return
        self._update(value)

    def _update(self, query: str) -> None:
        q = (query or "").strip().lower()
        if not q:
            self._hide()
            return
        matches = self._search(q)
        self._matches = matches
        self._selected = 0
        self._populate_list()
        if matches:
            self._show()
        else:
            self._hide()

    def on_key(self, event: events.Key) -> None:
        """容器层拦截按键：Key 事件从内部 Input 冒泡上来。

        仅在下拉打开时消费 ↓/↑/Enter/Esc；其余按键（含可打印字符）放行，
        由 Input 自行处理。此写法与官方 Country 示例一致，且不会再覆盖
        ``Widget.handle_key``（async，被默认 ``on_key`` await）而触发崩溃。
        """
        if not self._open or not self._matches:
            return
        # 拦截导航键时，取消任何待执行的延时隐藏，避免“按箭头后 0.25s 被关掉”
        t = getattr(self, "_hide_timer", None)
        if t is not None:
            try:
                t.stop()
            except Exception:
                pass
            self._hide_timer = None
        key = getattr(event, "key", None) or getattr(event, "name", None)
        if key == "down":
            self._selected = min(self._selected + 1, len(self._matches) - 1)
            self._highlight()
            event.prevent_default()
            event.stop()
        elif key == "up":
            self._selected = max(self._selected - 1, 0)
            self._highlight()
            event.prevent_default()
            event.stop()
        elif key == "enter":
            self._accept(self._selected)
            event.prevent_default()
            event.stop()
        elif key == "escape":
            self._hide()
            event.prevent_default()
            event.stop()

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        """内部 Input 失焦时延时关闭下拉（给点击候选项留出时间）。

        ``Blur`` 事件本身不冒泡，但 ``DescendantBlur`` 会冒泡到祖先，
        故在容器层即可感知 Input 失焦。
        """
        if event.widget is self._input:
            self.schedule_hide()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # 点击候选项即选中
        try:
            idx = self._items.index(event.item)
        except ValueError:
            return
        self._accept(idx)

    def _accept(self, index: int) -> None:
        if not self._matches or index < 0 or index >= len(self._matches):
            self._hide()
            return
        site = self._matches[index]
        name = site.get("name", "") or ""
        self._hide()
        # 标记本次程序化赋值，避免 on_input_changed 再次弹出下拉
        self._accepted_value = name
        self._input.value = name
        try:
            self._input.focus()
        except Exception:
            pass
        self.post_message(self.SiteSelected(name))
