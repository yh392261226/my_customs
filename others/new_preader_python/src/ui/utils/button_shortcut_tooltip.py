"""
按钮「快捷键提示」自动注入模块
================================

目标
----
系统内所有 ``Button``（含各 Screen 与 ModalScreen 对话框，以及运行时动态挂载的按钮），
只要能在「当前屏幕 BINDINGS」或「App 全局 BINDINGS」中找到语义对应的 action，
就自动附加一个 tooltip，内容为对应的快捷键（如 ``打开书籍 (F1)``）；
找不到对应快捷键的按钮保持原样，不做提示。

实现要点
--------
1. 读取 BINDINGS：沿 MRO 收集类属性 BINDINGS，兼容 ``(key, action, desc)`` 元组与
   ``Binding`` 实例，并用 Textual 官方 ``Binding.make_bindings`` 展开复合键，
   同一 action 的多个按键会合并展示（如 ``"f1,1"`` → ``f1/1``）。
2. 按钮 → action 匹配：按按钮 id 归一化后与 action 名称打分匹配，
   优先级顺序为：显式映射表 > 按钮自带 action > 语义匹配；
   多个 action 同分并列时直接放弃（宁缺勿错）。显式映射的值为空串表示「明确不提示」。
3. 注入时机：对 ``Widget.mount`` 打一层薄补丁，在每次挂载（含 compose 与动态挂载）
   之后的下一帧对所在屏幕统一刷新 tooltip。

用法
----
在应用启动时调用一次 ``install_button_shortcut_tooltips()`` 即可（``src/ui/app.py`` 中已调用）。
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Button, DataTable

# --------------------------------------------------------------------------- #
# 配置区
# --------------------------------------------------------------------------- #

#: 显式映射：{屏幕/对话框类名: {按钮 id: action 名}}
#: 当语义匹配不准或匹配不到时使用（优先级最高）
BUTTON_ACTION_OVERRIDES: Dict[str, Dict[str, str]] = {
    # 欢迎页：「管理」按钮对应 F5 打开用户管理
    "WelcomeScreen": {
        "manage-btn": "open_user_management",
    },
    # 阅读器：上一页/下一页/朗读/翻译/浏览器阅读
    "ReaderScreen": {
        "prev-btn": "left",
        "next-btn": "right",
        "aloud-btn": "toggle_tts",
        "translation-btn": "translate",
        "view-browser-btn": "browser_read",
        "reader-back-btn": "back",
    },
    # 设置中心：外观-主题按钮对应全局 t
    "SettingsScreen": {
        "appearance-theme-btn": "pick_theme",
    },
    # 爬取管理：全选=全选本页(a)；合并=合并选中(C)；搜索按钮无独立快捷键，明确不提示
    "CrawlerManagementScreen": {
        "select-all-btn": "select_all_rows",
        "merge-btn": "merge_selected",
        "search-btn": "",
    },
    # 批量操作：合并=合并选中(C)；查重=去重(u)；删除=删除选中(r)
    #           复制书名=当前行书名(y)；查看文件=当前行书籍文件(F)
    "BatchOpsDialog": {
        "merge-btn": "merge_selected",
        "find-duplicates-btn": "deduplicate",
        "delete-btn": "delete_selected",
        "copy-title-btn": "copy_title",
        "view-file-btn": "view_current_file",
    },
    # 网页阅读器：检查状态(c)、浏览书籍文件(f)、手机模拟器(m)；返回按钮(esc)
    "WebReaderScreen": {
        "wr-check-btn": "check_status",
        "wr-browse-btn": "browse_book_file",
        "wr-open-mobile-btn": "open_mobile_simulator",
        "wr-back-btn": "back",
    },
    # 日志查看弹窗（爬取管理与批量操作里同名）：关闭(esc)
    "LogViewerPopup": {
        "close-log-btn": "close",
    },
    # 统一书籍视图（详情 / 预览 / 查看文件三合一）
    "BookViewDialog": {
        "bv-details-btn": "show_details",
        "bv-preview-btn": "show_preview",
        "bv-full-btn": "toggle_preview",
        "bv-view-file-btn": "view_file",
        "bv-close-btn": "close",
    },
    # 兼容类名（BookDetailsDialog / BookPreviewDialog 继承自 BookViewDialog）
    "BookDetailsDialog": {
        "bv-details-btn": "show_details",
        "bv-preview-btn": "show_preview",
        "bv-full-btn": "toggle_preview",
        "bv-view-file-btn": "view_file",
        "bv-close-btn": "close",
    },
    "BookPreviewDialog": {
        "bv-details-btn": "show_details",
        "bv-preview-btn": "show_preview",
        "bv-full-btn": "toggle_preview",
        "bv-view-file-btn": "view_file",
        "bv-close-btn": "close",
    },
    # 回收站
    "RecycleBinDialog": {
        "rb-restore-btn": "restore_selected",
        "rb-undo-btn": "undo_batch",
        "rb-purge-btn": "purge_selected",
        "rb-empty-btn": "empty_bin",
        "rb-refresh-btn": "reload",
        "rb-close-btn": "close",
    },
    "LibraryFilterDialog": {
        "lf-apply-btn": "apply",
        "lf-clear-btn": "clear",
        "lf-cancel-btn": "cancel",
    },
    # 文本编辑器：保存、自动换行、关闭
    "TextEditorModal": {
        "editor-save-btn": "save",
        "editor-wrap-btn": "toggle_wrap",
        "editor-close-btn": "close",
    },
    # 补足缺失章节：预览当前光标行书籍(v)、可视化补足(V)
    "FillMissingDialog": {
        "fm-preview-book-btn": "preview_current_book",
        "fm-visual-merge-btn": "visual_merge",
    },
    # 书籍详情弹窗：查看文件(F)、预览(v)、关闭(i/q/esc)
    "BookDetailsDialog": {
        "book-details-view-file-btn": "view_file",
        "book-details-preview-btn": "preview",
        "book-details-close-btn": "close",
    },
    # 获取书籍：代理设置(P)
    "GetBooksScreen": {
        "proxy-settings-btn": "open_proxy_list",
    },
    # 解锁屏：回车提交
    "LockScreen": {
        "lock-submit-btn": "on_submit",
    },
}

#: 表格列级显式映射：{屏幕/对话框类名: {列 key: action 名}}
#: 用于「快捷键作用于当前光标行、但表格里没有真实 Button」的场景。
#: 例如批量操作页按 y 复制书名、按 F 打开书籍文件：悬停到对应列时，
#: 把快捷键写进 DataTable 的 tooltip（列 key 与语言无关，比按中文标签匹配更稳）。
TABLE_COLUMN_ACTION_OVERRIDES: Dict[str, Dict[str, str]] = {
    "BatchOpsDialog": {
        "title": "copy_title",
        "view_action": "view_current_file",
    },
}

#: 明确不做提示的按钮 id（语义匹配会产生误导，且无对应快捷键）
SKIP_BUTTON_IDS = {
    "ok-btn",
}

#: 不做提示的 action（多为导航/焦点类，挂到按钮上容易误导）
SKIP_ACTIONS = {
    "toggle_focus",
    "focus_next",
    "focus_previous",
    "toggle_view",
}

#: 语义匹配的最低可用分（低于该分视为不可信）
MIN_SCORE = 50

#: 按钮标识别名：归一化后的按钮 id → 额外尝试的 action 名
#: 用于「按钮叫 jump_page、快捷键 action 叫 jump_to」这类命名不一致的情况
NORM_ALIASES: Dict[str, Tuple[str, ...]] = {
    "jump_page": ("jump_to", "goto_page"),
    "jump": ("jump_to",),
    "goto": ("jump_to", "goto_page"),
    "page_jump": ("jump_to",),
    "goto_page": ("jump_to",),
}

#: 同义词归一（仅用于语义匹配，尽量保守）
SYNONYMS = {
    "choose": "select",
    "pick": "select",
    "del": "delete",
    "remove": "delete",
    "esc": "escape",
}

_BTN_SUFFIX_RE = re.compile(r"[_\-](btn|button)$", re.IGNORECASE)
_MULTI_UNDERSCORE_RE = re.compile(r"_+")
# 单元格里的「文字型按钮」： [删除] / [预览]
_CELL_LABEL_RE = re.compile(r"\[([^\[\]]{1,16})\]")
# 方括号片段（含 rich 标记如 [bold]）
_BRACKET_SEG_RE = re.compile(r"\[[^\[\]]*\]")
# 非文字符号（emoji / 箭头 / 标点等）
_SYMBOL_RE = re.compile(r"[^\w一-鿿\s]")
# 只保留文字与数字
_CLEAN_RE = re.compile(r"[^\w一-鿿]+")
# 用于区分「未记录」与「记录为 None」的哨兵值
_UNSET = object()


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
def normalize_button_key(raw: Optional[str]) -> str:
    """把按钮 id / name 归一化成可与 action 比较的形式。

    例：``"Open-Book-btn"`` → ``"open_book"``；``"confirm_btn"`` → ``"confirm"``
    """
    text = (raw or "").strip().lower()
    text = _BTN_SUFFIX_RE.sub("", text)
    text = text.replace("-", "_").replace(" ", "_")
    text = _MULTI_UNDERSCORE_RE.sub("_", text).strip("_")
    return text


def score_action(action: str, norm: str) -> int:
    """给「action 名」与「归一化后的按钮标识」的语义相关度打分（0 表示无关）。

    只认可「结构化」的相似：完全一致、仅差一个动词/后缀、或至少两个词重合。
    单词重合（如 ``search`` ↔ ``clear_search_params``）一律判为无关，避免错标。
    """
    if not action or not norm:
        return 0
    action = action.strip().lower()
    if action == norm:
        return 100

    a_tokens = [t for t in action.split("_") if t]
    n_tokens = [SYNONYMS.get(t, t) for t in norm.split("_") if t]
    if not a_tokens or not n_tokens:
        return 0
    if a_tokens == n_tokens:
        return 100

    diff = len(a_tokens) - len(n_tokens)
    if diff == 1:
        # action = 动词 + 按钮标识（open_settings / settings）
        if a_tokens[1:] == n_tokens:
            return 90
        # action = 按钮标识 + 限定词（merge_mode / merge）
        if a_tokens[:-1] == n_tokens:
            return 86
    elif diff <= -1 and len(a_tokens) >= 2:
        # 按钮标识更长，但尾部/头部与 action 完全一致（wr_open_reader / open_reader）
        # 要求 action 至少两个词，避免 fm_assign_back 之类误配到 back
        length = len(a_tokens)
        if n_tokens[-length:] == a_tokens:
            return 82
        if n_tokens[:length] == a_tokens:
            return 80

    # 乱序但词全部覆盖（要求至少两个词，单词覆盖太容易误伤）
    if len(n_tokens) >= 2 and set(n_tokens).issubset(set(a_tokens)):
        return 76

    # 至少两个词重合
    inter = set(n_tokens) & set(a_tokens)
    if len(inter) >= 2:
        return 60 + 10 * (len(inter) - 2)
    return 0


def _collect_bindings(owner) -> List[Binding]:
    """收集某个对象（Screen / App）沿 MRO 声明的所有 Binding。"""
    result: List[Binding] = []
    if owner is None:
        return result
    sources = []
    # 实例属性优先（个别屏幕会在实例上覆盖 BINDINGS）
    inst_bindings = getattr(owner, "__dict__", {}).get("BINDINGS")
    if inst_bindings:
        sources.append(inst_bindings)
    for klass in type(owner).__mro__:
        raw = klass.__dict__.get("BINDINGS")
        if raw:
            sources.append(raw)
    for raw in sources:
        try:
            result.extend(Binding.make_bindings(raw))
        except Exception:
            continue
    return result


def _key_display(app, binding: Binding) -> str:
    """获取按键的展示文本（优先 key_display，其次 App.get_key_display）。"""
    try:
        if binding.key_display:
            return str(binding.key_display)
    except Exception:
        pass
    try:
        if app is not None and hasattr(app, "get_key_display"):
            return str(app.get_key_display(binding))
    except Exception:
        pass
    return str(getattr(binding, "key", "") or "")


def build_action_index(screen) -> Dict[str, Tuple[str, str, int]]:
    """构建 ``action -> (按键显示, 描述, 来源优先级)`` 索引。

    屏幕自身绑定优先于 App 全局绑定（优先级 2 > 1）。
    """
    index: Dict[str, Tuple[str, str, int]] = {}
    app = None
    try:
        app = screen.app
    except Exception:
        app = None

    for priority, owner in ((2, screen), (1, app)):
        for binding in _collect_bindings(owner):
            try:
                action = binding.action
                if not action or action in SKIP_ACTIONS:
                    continue
                # 不在 footer 展示的（系统级/隐藏）绑定不用于按钮提示
                if getattr(binding, "system", False) or not getattr(binding, "show", True):
                    continue
                key = _key_display(app, binding)
                if not key:
                    continue
            except Exception:
                continue
            description = getattr(binding, "description", "") or ""
            existing = index.get(action)
            if existing is not None:
                if existing[2] > priority:
                    continue
                if existing[2] == priority:
                    # 同一 action 绑定了多个键（如 "f1,1" / "escape,q"）→ 合并展示
                    keys = existing[0].split("/")
                    if key not in keys and len(keys) < 3:
                        index[action] = ("/".join(keys + [key]), existing[1] or description, priority)
                    continue
            index[action] = (key, description, priority)
    return index


def match_action(norm: str, index: Dict[str, Tuple[str, str, int]]) -> Optional[str]:
    """在 action 索引中为归一化按钮标识找到最可能的 action。

    除按钮标识本身外，还会尝试 :data:`NORM_ALIASES` 中登记的同义 action 名
    （例如分页条的 ``jump-page-btn`` → ``jump_to``）。
    """
    candidates: List[Tuple[int, int, str]] = []
    # 按钮标识本身优先，其后按 NORM_ALIASES 中的顺序依次降级
    for rank, try_norm in enumerate((norm, *NORM_ALIASES.get(norm, ()))):
        for action, (_key, _desc, priority) in index.items():
            s = score_action(action, try_norm)
            if s < MIN_SCORE:
                continue
            # 屏幕绑定（priority=2）在同分时胜出；别名命中按 rank 轻微降权
            candidates.append((s + priority - 6 * rank, s, action))
    if not candidates:
        return None
    # 同一个 action 可能被多个别名命中，去重后按分数排序
    deduped: Dict[str, Tuple[int, int]] = {}
    for total, score, action in candidates:
        if action not in deduped or total > deduped[action][0]:
            deduped[action] = (total, score)
    ranked = sorted(
        ((total, score, action) for action, (total, score) in deduped.items()),
        key=lambda item: (-item[0], -item[1], item[2]),
    )
    top_total = ranked[0][0]
    if sum(1 for c in ranked if c[0] == top_total) > 1:
        # 并列第一 → 无法确定是哪一个，直接放弃（宁缺勿错）
        return None
    return ranked[0][2]


def build_tooltip_text(key: str, description: str) -> str:
    """组装 tooltip 文本。"""
    key = (key or "").strip()
    description = (description or "").strip()
    if description and key:
        return f"{description} ({key})"
    return key or description


def get_action_index(screen) -> Dict[str, Tuple[str, str, int]]:
    """获取（并缓存）屏幕的 action 索引，供按钮与表格单元格提示复用。"""
    cached = getattr(screen, "_shortcut_action_index", None)
    if isinstance(cached, dict) and cached:
        return cached
    index = build_action_index(screen)
    try:
        setattr(screen, "_shortcut_action_index", index)
    except Exception:
        pass
    return index


def match_binding_by_label(
    label: str,
    index: Dict[str, Tuple[str, str, int]],
    min_score: int = 70,
) -> Optional[str]:
    """按「中文标签」匹配绑定：用于表格里的文字型按钮。

    匹配强度：完全一致(100) > 描述以标签开头(90) > 标签包含在描述中(80) >
    描述包含在标签中(70)。``min_score`` 用于抑制弱匹配带来的误报：
    带方括号/图标的单元格可信度高，可用 70/80；普通文本单元格要求 90 以上。
    """
    label = (label or "").strip()
    if not label:
        return None
    best: Optional[Tuple[int, str, int]] = None
    for action, (_key, desc, priority) in index.items():
        text = (desc or "").strip()
        if not text:
            continue
        if text == label:
            score = 100
        elif text.startswith(label):
            score = 90
        elif label in text:
            score = 80
        elif text in label:
            score = 70
        else:
            continue
        if score < min_score:
            continue
        score += priority  # 屏幕绑定优先
        if best is None or score > best[0] or (score == best[0] and len(text) < best[2]):
            best = (score, action, len(text))
    return best[1] if best else None


def extract_cell_labels(text: str) -> List[Tuple[str, int]]:
    """从单元格文本中提取「可点击项」的候选标签及其最低匹配置信度。

    系统里有三种文字型按钮写法：
      * ``[删除]``        —— 方括号包裹
      * ``🔍 检测``       —— 图标 + 文字
      * ``查看文件``      —— 纯文字（如爬取管理的操作列）
    """
    labels: List[Tuple[str, int]] = []
    for label in _CELL_LABEL_RE.findall(text or ""):
        label = label.strip()
        if label:
            labels.append((label, 70))
    plain = _plain_label(text)
    if len(plain) >= 2:
        # 带图标的单元格（🔍 检测 / ➤ 进入）可信度高一些；纯文字要求更严格
        has_symbol = bool(_SYMBOL_RE.search(_BRACKET_SEG_RE.sub("", text or "")))
        labels.append((plain, 80 if has_symbol else 90))
    return labels


def _plain_label(text: str) -> str:
    """去掉方括号片段（含 rich 标记）与符号后的纯文字标签。"""
    stripped = _BRACKET_SEG_RE.sub("", text or "")
    return _CLEAN_RE.sub("", stripped).strip()


def _cell_text(value) -> str:
    """把单元格内容转成纯文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    plain = getattr(value, "plain", None)
    if isinstance(plain, str):
        return plain
    try:
        return str(value)
    except Exception:
        return ""


def _column_key_at(table, column_index: Optional[int]) -> Optional[str]:
    """取 DataTable 第 N 列的 key（即 add_column(key=...) 传入的值）。"""
    if column_index is None or column_index < 0:
        return None
    try:
        columns = list(getattr(table, "ordered_columns", None) or [])
        if not columns:
            columns = list(getattr(table, "columns", {}).values())
        col = columns[column_index]
        key = getattr(col, "key", None)
        value = getattr(key, "value", None) or key
        return str(value) if value else None
    except Exception:
        return None


def update_hovered_cell_tooltip(table, coordinate) -> None:
    """根据鼠标所在单元格更新表格自身的 tooltip。

    表格里的操作项（``[删除]`` / ``[预览]`` …）是单元格文本而非真按钮，
    Textual 没有「单元格级 tooltip」，因此借用表格自身的 tooltip：
    悬停到这类单元格时把对应快捷键写上去，离开后清除。
    """
    try:
        screen = table.screen
    except Exception:
        return
    if screen is None:
        return
    index = get_action_index(screen)
    if not index:
        return
    try:
        value = table.get_cell_at(coordinate)
    except Exception:
        return

    tips: List[str] = []
    used_labels: set[str] = set()
    for label, min_score in extract_cell_labels(_cell_text(value)):
        if label in used_labels:
            continue
        used_labels.add(label)
        action = match_binding_by_label(label, index, min_score=min_score)
        if not action:
            continue
        key, description, _priority = index[action]
        tip = build_tooltip_text(key, description)
        if tip and tip not in tips:
            tips.append(tip)

    # 列级显式映射：作用于「当前光标行」的快捷键没有真实按钮，
    # 借表格 tooltip 在悬停对应列时给出提示（与文字按钮提示合并、去重）。
    column_actions = TABLE_COLUMN_ACTION_OVERRIDES.get(type(screen).__name__, {})
    if column_actions:
        col_key = _column_key_at(table, getattr(coordinate, "column", -1))
        action = column_actions.get(col_key or "")
        if action:
            entry = index.get(action)
            if entry:
                tip = build_tooltip_text(entry[0], entry[1])
                if tip and tip not in tips:
                    tips.append(tip)

    new_tip = " · ".join(tips) if tips else None

    # 记录应用自身给表格设过的 tooltip，离开「文字按钮」单元格时还原
    if getattr(table, "_shortcut_tip_original", _UNSET) is _UNSET:
        try:
            table._shortcut_tip_original = getattr(table, "tooltip", None)
        except Exception:
            table._shortcut_tip_original = None
    target = new_tip if new_tip else table._shortcut_tip_original

    try:
        if getattr(table, "tooltip", None) != target:
            table.tooltip = target
        table._shortcut_tip_value = new_tip
    except Exception:
        return

    # 关键：Textual 在「同一控件内移动鼠标」时会把 tooltip 隐藏，
    # 且 _update_tooltip 只在 tooltip 已显示时才会刷新内容。
    # 因此这里主动调用屏幕的 tooltip 处理函数，保证提示能随单元格即时更新/消失。
    refresh = getattr(screen, "_handle_tooltip_timer", None)
    if callable(refresh):
        try:
            refresh(table)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 应用逻辑
# --------------------------------------------------------------------------- #
def apply_button_shortcut_tooltips(screen) -> int:
    """给指定屏幕内所有 Button 附加快捷键 tooltip，返回实际写入的按钮数量。"""
    if screen is None:
        return 0
    try:
        buttons = list(screen.query(Button))
    except Exception:
        return 0
    if not buttons:
        return 0

    index = build_action_index(screen)
    if not index:
        return 0
    # 缓存索引，供表格单元格悬停提示复用
    try:
        setattr(screen, "_shortcut_action_index", index)
    except Exception:
        pass

    overrides = BUTTON_ACTION_OVERRIDES.get(type(screen).__name__, {})
    changed = 0
    for button in buttons:
        try:
            button_id = button.id or ""
            if button_id in SKIP_BUTTON_IDS:
                continue
            # 显式映射：值为空表示「明确不提示」
            if button_id in overrides:
                action = overrides[button_id] or None
            else:
                action = None
            norm = normalize_button_key(button_id or button.name or "")
            if not norm:
                continue
            if action is None:
                action = getattr(button, "action", None) or match_action(norm, index)
            if not action:
                continue

            entry = index.get(action)
            if not entry:
                continue
            key, description, _priority = entry
            if not key:
                continue

            text = build_tooltip_text(key, description)
            current = getattr(button, "tooltip", None)
            if current:
                current_text = str(current)
                if key in current_text:
                    continue
                button.tooltip = f"{current_text} · {key}"
            else:
                button.tooltip = text
            changed += 1
        except Exception:
            continue
    return changed


def _resolve_screen(widget) -> Optional[object]:
    """尽量解析出挂载操作所属的屏幕。"""
    try:
        screen = widget.screen
        if screen is not None:
            return screen
    except Exception:
        pass
    try:
        from textual.screen import Screen

        if isinstance(widget, Screen):
            return widget
    except Exception:
        pass
    try:
        return widget.app.screen
    except Exception:
        return None


def _run_apply(screen) -> None:
    try:
        setattr(screen, "_shortcut_tips_scheduled", False)
    except Exception:
        pass
    try:
        apply_button_shortcut_tooltips(screen)
    except Exception:
        pass


def _schedule_apply(screen) -> None:
    """在下一帧统一处理，避免同一次 compose 反复计算。"""
    if screen is None:
        return
    try:
        if getattr(screen, "_shortcut_tips_scheduled", False):
            return
        setattr(screen, "_shortcut_tips_scheduled", True)
    except Exception:
        pass
    try:
        app = screen.app
        app.call_after_refresh(lambda: _run_apply(screen))
        return
    except Exception:
        pass
    _run_apply(screen)


_installed = False
_table_installed = False


def install_data_table_cell_tooltips() -> None:
    """让 DataTable 单元格里的「文字型按钮」（``[删除]`` 等）也能提示快捷键。

    Textual 没有单元格级 tooltip，这里借用 DataTable 自身的 tooltip：
    随 ``hover_coordinate`` 变化更新内容，离开这类单元格后清除。
    """
    global _table_installed
    if _table_installed:
        return
    original_watch = getattr(DataTable, "watch_hover_coordinate", None)
    if original_watch is None or getattr(original_watch, "_shortcut_tips_patched", False):
        _table_installed = True
        return

    def watch_hover_coordinate(self, old, value):
        original_watch(self, old, value)
        try:
            update_hovered_cell_tooltip(self, value)
        except Exception:
            pass

    watch_hover_coordinate._shortcut_tips_patched = True  # type: ignore[attr-defined]
    DataTable.watch_hover_coordinate = watch_hover_coordinate  # type: ignore[assignment]
    _table_installed = True


def install_button_shortcut_tooltips() -> None:
    """安装全局钩子：任何按钮挂载后自动补齐快捷键 tooltip。

    同时为 DataTable 单元格内的文字型按钮启用悬停提示。幂等；可安全重复调用。
    """
    global _installed
    original_mount = Widget.mount
    if getattr(original_mount, "_shortcut_tips_patched", False):
        _installed = True
    else:
        def mount(self, *args, **kwargs):
            result = original_mount(self, *args, **kwargs)
            try:
                _schedule_apply(_resolve_screen(self))
            except Exception:
                pass
            return result

        mount._shortcut_tips_patched = True  # type: ignore[attr-defined]
        Widget.mount = mount  # type: ignore[assignment]
        _installed = True

    try:
        install_data_table_cell_tooltips()
    except Exception:
        pass
