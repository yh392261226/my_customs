"""
爬取历史合并模式对话框

功能：
1. 按全部爬取记录，搜索同一书籍网站下的相似书籍
2. 自动识别同一本书的不同章节并归为一组
3. 支持人工勾选后批量合并
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple

from rich import style
from textual.screen import ModalScreen, Screen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Label, DataTable, Static
from textual import on
from textual.css.query import NoMatches
from textual.widget import events

from textual_datepicker import DateSelect, DatePicker
import pendulum

from src.locales.i18n_manager import get_global_i18n
from src.themes.theme_manager import ThemeManager
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─── 章节模式正则（按优先级排序） ───
CHAPTER_PATTERNS = [
    # （序-数字）如（序-21）、（序-6）
    re.compile(r'[（(]\s*序\s*[-–—－]\s*(\d+)\s*[）)]'),
    # （数字.数字-数字.数字）如（1.1-2.155）— 子章节范围
    re.compile(r'[（(]\s*(\d+\.\d+)\s*[-–—－]\s*(\d+\.\d+)[^）)]*[）)]'),
    # （数字-数字+附加内容）如（1-14+番外 欣然篇之迷奸表哥）、（1-47）、(1－28)
    re.compile(r'[（(]\s*(\d+)\s*[-–—－]\s*(\d+)[^）)]*[）)]'),
    # （数字）单独
    re.compile(r'[（(]\s*(\d+)\s*[）)]'),
    # 第X章 / 第X卷 / 第X节
    re.compile(r'\s*第\s*[\d一二三四五六七八九十百千万]+\s*[章节卷部篇集回]\s*'),
    # 第X卷 / 第X部
    re.compile(r'\s*第\s*[\d一二三四五六七八九十百千万]+\s*[卷部篇集回]\s*'),
    # 上/中/下/全
    re.compile(r'\s*[（(]?\s*(?:上|中|下|全|完结|完)\s*[）)]?\s*$'),
    # 罗马数字 ⅠⅡⅢⅣⅤ
    re.compile(r'\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\s*$'),
    # 末尾空格+数字范围 如 " 3-4"、" 1-46"
    re.compile(r'\s+\d+\s*[-–—－]\s*\d+\s*$'),
    # 末尾纯数字或数字范围
    re.compile(r'\s*[-–—－]?\s*\d+\s*$'),
    # 末尾空格+数字
    re.compile(r'\s+\d{1,3}\s*$'),
]


@dataclass
class BookGroup:
    """书籍分组"""
    group_id: int
    base_title: str                        # 规范化后的基准标题
    books: List[Dict[str, Any]] = field(default_factory=list)
    is_auto_same_book: bool = False        # 是否自动识别为同一本书的不同章节
    is_selected: bool = True               # 默认全选

    @property
    def book_count(self) -> int:
        return len(self.books)

    @property
    def display_title(self) -> str:
        """显示使用第一个书籍的原始标题（截断）"""
        if self.books:
            title = self.books[0].get('novel_title', self.base_title)
            return title if len(title) <= 40 else title[:37] + '...'
        return self.base_title if len(self.base_title) <= 40 else self.base_title[:37] + '...'

    @property
    def date_range(self) -> str:
        """日期范围"""
        dates = sorted(set(
            b.get('crawl_time', '')[:10] for b in self.books if b.get('crawl_time')
        ))
        if not dates:
            return '-'
        if len(dates) == 1:
            return dates[0]
        return f"{dates[0]} ~ {dates[-1]}"


def normalize_book_title(title: str) -> str:
    """
    提取核心书名作为分组键。

    处理流程（按顺序）：
    1. 剥离章节信息（括号内数字、尾部数字范围、第X章等）
    2. 去除"作者"及之后的所有内容
    3. 在第一个分隔符处截断（逗号、顿号、问号、感叹号、句号、冒号、分号等），只保留主标题
    4. 在破折号处截断（跳过数字范围如 1-46）
    5. 去除包裹符号 《 》 【 】 「 」 [ ]
    6. 去除尾部省略号
    7. 移除所有剩余特殊字符，只保留中英文和数字

    示例:
        我都三十五了，系统怎么才来           →  我都三十五了
        《我都三十五了，系统怎么才来》3-4    →  我都三十五了
        【我都三十五了，系统怎么才来】（5-6） →  我都三十五了
        《我都三十五了...》（7-8）           →  我都三十五了
        【半缘-陌上花开】（序-21）作者：修道  →  半缘
        【与老妈的(其他)故事】(1－28)作者:xxx →  与老妈的
        【女主播？我的女友！】               →  女主播
        【蛆虫之歌】11-19完 译者：sunson -> 蛆虫之歌
        【蛆虫之歌】(11-19完) 译者：sunson -> 蛆虫之歌
        【蛆虫之歌】（11-19完） 译者：sunson -> 蛆虫之歌
    """
    if not title:
        return ""

    result = title.strip()

    # Step 1: 剥离章节信息
    result = remove_chapter_info(result)

    # Step 2: 去除"作者"及之后的所有内容
    for sep in ('译者', '作者', '作', '译'):
        author_idx = result.find(sep)
        if author_idx > 0:
            result = result[:author_idx]
            break

    # Step 3: 在第一个分隔符处截断，只保留主标题
    # 分隔符包括：tab、空格、逗号、顿号、问号、感叹号、句号、冒号、分号、括号、省略号、书名号闭合等
    # 注意：省略号必须在书名号闭合之前，否则 】 会先匹配导致截断位置错误
    for sep in ('   ', ' ', '，', ',', '、', '？', '?', '！', '!', '。', '.', '；', ';', '：', ':', '(', '（', '…', '...', '】', '」', '》', ')', '）'):
        idx = result.find(sep)
        if idx >= 2:
            result = result[:idx].strip()
            break

    # Step 4: 在破折号处截断（跳过数字范围）
    for sep in ('-', '—', '－', '~'):
        idx = result.find(sep)
        if idx < 2:
            continue
        before = result[:idx].rstrip()
        after = result[idx + 1:].lstrip()
        # 跳过数字范围（如 "1-46"、"3-4" 已在章节剥离中处理）
        if before and after and before[-1].isdigit() and after[0].isdigit():
            continue
        if before and len(before) >= 2:
            result = before.strip()
            break

    # Step 5: 去除包裹符号
    for ch in ('【', '】', '《', '》', '「', '」', '[', ']', '（', '）', '(', ')'):
        result = result.replace(ch, '')

    # Step 6: 去除尾部省略号/句号
    result = result.rstrip('·…。.~～ ')

    # Step 7: 移除所有剩余特殊字符，只保留中英文字母
    result = re.sub(
        r'[^\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6dfa-zA-Z]',
        '', result,
    )

    return result.strip()


def remove_chapter_info(title: str) -> str:
    """
    移除章节信息，用于判断两本书是否为同一本书的不同章节。

    去除括号中的数字、第X章、上中下等章节标记。
    """
    if not title:
        return ""

    result = title.strip()

    for pattern in CHAPTER_PATTERNS:
        result = pattern.sub('', result).strip()

    # 清理多余空白和标点
    result = re.sub(r'\s+', ' ', result).strip()
    result = result.rstrip('。-—（）()[]{}\u3010\u3011')

    return result


def is_same_book_chapters(title1: str, title2: str) -> bool:
    """
    判断两个标题是否为同一本书的不同章节。

    移除章节信息后对比规范化标题。
    """
    n1 = remove_chapter_info(normalize_book_title(title1))
    n2 = remove_chapter_info(normalize_book_title(title2))

    if not n1 or not n2:
        return False

    # 精确匹配
    if n1 == n2:
        return True

    # 一个包含另一个（如 "小红的一天" 包含在 "小红的一天续" 中）
    if len(n1) >= 3 and len(n2) >= 3:
        if n1 in n2 or n2 in n1:
            return True

    # 编辑距离（简单版：共同前缀比例）
    min_len = min(len(n1), len(n2))
    if min_len >= 4:
        common = 0
        for i in range(min_len):
            if n1[i] == n2[i]:
                common += 1
            else:
                break
        if common >= min_len * 0.7 and common >= 4:
            return True

    return False


def group_books_for_merge(
    all_history: List[Dict[str, Any]],
    db_manager: DatabaseManager,
    site_id: int,
) -> List[BookGroup]:
    """
    对爬取历史记录进行分组，用于合并模式。

    流程：
    1. 以指定日期范围内的爬取记录为种子
    2. 对每条记录先规范化书名，再剥离章节信息，用得到的核心书名
       去数据库 LIKE 搜索（含已合并的、往期各章节的全部历史记录）
    3. 自动检测不同搜索关键词对应的分组是否实际是同一本书，
       若是则合并为一组
    4. 返回分组结果

    Args:
        all_history: 日期范围内的爬取历史记录（去重后）
        db_manager: 数据库管理器
        site_id: 网站ID

    Returns:
        List[BookGroup]: 分组列表
    """
    if not all_history:
        return []

    # Step 1: 对每条记录，先规范化再剥离章节信息，用核心书名搜索全部历史
    seen_search_keys: Set[str] = set()
    raw_groups: List[BookGroup] = []
    group_id = 0

    for item in all_history:
        title = item.get('novel_title', '').strip()
        if not title:
            continue

        # 先按用户规则规范化（去作者、去标点等）
        normalized = normalize_book_title(title)
        if not normalized:
            continue

        # 再剥离章节信息（去括号数字、第X章等），得到核心书名用于搜索
        search_key = remove_chapter_info(normalized)
        if not search_key or len(search_key) < 2:
            # 核心书名太短则用规范化结果兜底
            search_key = normalized

        if search_key in seen_search_keys:
            continue
        seen_search_keys.add(search_key)

        # 用核心书名 LIKE 搜索全部历史（包括已合并的、往期章节）
        similar_books = db_manager.search_crawl_history_by_title(site_id, search_key)

        if similar_books:
            group_id += 1
            raw_groups.append(BookGroup(
                group_id=group_id,
                base_title=search_key,       # 核心书名作为基准
                books=similar_books,
            ))

    # Step 2: 跨所有分组检测是否为同一本书的不同章节/命名变体
    merged_groups, _ = _auto_merge_chapter_groups(raw_groups)

    return merged_groups


def _auto_merge_chapter_groups(
    groups: List[BookGroup],
) -> Tuple[List[BookGroup], Set[int]]:
    """
    跨所有分组检测同一本书的不同命名变体，合并为一组。

    检测逻辑：
    - 对任意两组，取各自第一条记录的原始标题
    - 用 is_same_book_chapters 判断是否为同一本书
    - 若是则合并，不在主列表中单独展示
    """
    if not groups:
        return [], set()
    merged_group_ids: Set[int] = set()
    auto_merged_count = 0

    for i, group_a in enumerate(groups):
        if group_a.group_id in merged_group_ids:
            continue

        for j, group_b in enumerate(groups):
            if j <= i:
                continue
            if group_b.group_id in merged_group_ids:
                continue

            # 检查两组的代表书名是否为同一本书
            title_a = group_a.books[0].get('novel_title', '') if group_a.books else group_a.base_title
            title_b = group_b.books[0].get('novel_title', '') if group_b.books else group_b.base_title

            if is_same_book_chapters(title_a, title_b):
                # 合并书籍列表（按 ID 去重）
                existing_ids = {b.get('id') for b in group_a.books}
                for book in group_b.books:
                    if book.get('id') not in existing_ids:
                        group_a.books.append(book)
                        existing_ids.add(book.get('id'))

                group_a.is_auto_same_book = True
                auto_merged_count += 1
                merged_group_ids.add(group_b.group_id)

                n_a = remove_chapter_info(normalize_book_title(title_a))
                n_b = remove_chapter_info(normalize_book_title(title_b))
                logger.debug(
                    f"自动合并: [{n_a[:40]}] ← [{n_b[:40]}]"
                    f" (组{group_a.group_id}+{group_b.group_id}，"
                    f"共{len(group_a.books)}本)"
                )

    # 过滤掉已合并的组
    result = [g for g in groups if g.group_id not in merged_group_ids]

    # 对合并后的组按书名排序
    result.sort(key=lambda g: g.base_title)

    # 重新编号
    for idx, g in enumerate(result, 1):
        g.group_id = idx

    logger.info(
        f"合并模式分组完成：原始 {len(groups)} 组 → {len(result)} 组"
        f"（自动合并 {auto_merged_count} 组章节）"
    )

    return result, merged_group_ids


class CrawlerMergeModeDialog(ModalScreen[Dict[str, Any]]):
    """爬取历史合并模式弹窗 —— 内置日期筛选"""

    CSS_PATH = "../styles/crawler_merge_mode_dialog.tcss"

    BINDINGS = [
        ("escape", "cancel", get_global_i18n().t('common.cancel')),
        ("g", "confirm_merge", get_global_i18n().t('merge_mode.confirm_merge')),
        ("space", "toggle_row", get_global_i18n().t('batch_ops.toggle_row')),
        ("a", "toggle_select_all", get_global_i18n().t('batch_ops.select_all')),
        ("r", "invert_selection", get_global_i18n().t('merge_mode.invert_selection')),
        ("y", "copy_title", get_global_i18n().t('merge_detail.copy_title')),
    ]

    def __init__(
        self,
        theme_manager: ThemeManager,
        all_history: List[Dict[str, Any]],
        db_manager: DatabaseManager,
        site_id: int,
        site_name: str = "",
        min_date: str = "",
        max_date: str = "",
        novel_site: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        # DatePickerDialog 原生 CSS 有 layer: dialog + display:none。
        # 在 ModalScreen 里 display:none 会导致 size 无法计算（(0,0)），
        # layer 问题用 CSS 覆盖解决。
        # 策略：dialog 挂载在 ModalScreen 直属下，display 始终为 True，
        # 用 offset=(-999,-999) 离屏隐藏。_patched_show 中动态计算 Screen 内
        # 绝对坐标，通过 reflow 让 compositor 感知位置变更。
        self._orig_dateselect_on_mount = DateSelect.on_mount
        DateSelect.on_mount = lambda self: None  # 阻止 compose 阶段创建 dialog

        from textual_datepicker._date_select import DatePickerDialog
        self._orig_dlg_on_selected = DatePickerDialog.on_date_picker_selected
        self._orig_dlg_on_blur = DatePickerDialog.on_descendant_blur

        # flow_position 缓存（按 dialog id），避免每次 show 都做两阶段 reflow
        _flow_cache = {}  # type: dict[int, tuple[int,int,int,int]]

        def _dlg_is_visible(dlg):
            off = dlg.offset
            return off is not None and not (str(off.x) == '-999' and str(off.y) == '-999')

        def _patched_dlg_on_selected(self, event):  # type: ignore[override]
            logger.debug(f"DLG_SELECTED: hiding dialog")
            self.styles.offset = (-999, -999)
            if self.target is not None:  # type: ignore[attr-defined]
                self.target.focus()  # type: ignore[attr-defined]

        def _patched_dlg_on_blur(self, event):  # type: ignore[override]
            pass

        DatePickerDialog.on_date_picker_selected = _patched_dlg_on_selected
        DatePickerDialog.on_descendant_blur = _patched_dlg_on_blur

        def _patched_show(self):
            """show/hide dialog via offset (display stays True, layout always computed)"""
            dlg = self.dialog
            app = self.app

            # toggle：已在屏幕上则隐藏
            if _dlg_is_visible(dlg):
                logger.debug(f"_patched_show: toggle hide")
                dlg.styles.offset = (-999, -999)
                return

            screen = self.screen
            comp = screen._compositor

            # Step 1: 计算 DateSelect 在 Screen 内的绝对坐标
            off_x, off_y = self.region.offset
            node = self.parent
            while node is not None and node is not screen:
                off_x += node.region.offset.x
                off_y += node.region.offset.y
                node = node.parent  # type: ignore[assignment]

            # Step 2: 获取 flow position（首次测量后缓存）
            dlg_id = id(dlg)
            if dlg_id in _flow_cache:
                flow_x, flow_y, dlg_height, dlg_width = _flow_cache[dlg_id]
            else:
                # 首次测量：把 offset 临时设为 (0,0) 让 dialog 进入 Screen 的
                # CSS 流布局，reflow 后从 full_map 读出其自然流位置。
                # batch_update 抑制 offset 变更的中间帧渲染。
                with app.batch_update():
                    dlg.styles.offset = (0, 0)
                comp.reflow(screen, screen.size)
                full_map = comp.full_map
                if dlg in full_map:
                    region = full_map[dlg].region
                    flow_x, flow_y = region.offset
                    dlg_height, dlg_width = region.height, region.width
                else:
                    rw = getattr(dlg, '_render_widget', dlg)
                    region = full_map[rw] if rw in full_map else None
                    flow_x, flow_y = region.offset if region else (0, 0)
                    dlg_height = region.height if region else 17
                    dlg_width = region.width if region else 30
                _flow_cache[dlg_id] = (flow_x, flow_y, dlg_height, dlg_width)

            # Step 3: 扣除 flow position，得到纯 CSS offset，
            # 并确保不超出屏幕右边界和底部
            final_off_x = off_x - flow_x
            final_off_y = off_y + 3 - flow_y
            screen_w, screen_h = screen.size.width, screen.size.height
            # 水平方向：右侧不超出屏幕
            effective_x = flow_x + final_off_x
            if effective_x + dlg_width > screen_w:
                final_off_x = max(0, screen_w - dlg_width - flow_x - 1)
            # 垂直方向：底部不超出屏幕
            effective_y = flow_y + final_off_y
            if effective_y + dlg_height > screen_h:
                final_off_y = max(0, screen_h - dlg_height - flow_y - 1)

            # 隐藏其他 dialog + 设置最终位置，合并所有样式变更到同一个 batch_update，
            # 只触发一次布局+重绘，dialog 直接出现在最终位置，不闪屏
            final_offset = (final_off_x, final_off_y)
            with app.batch_update():
                # 先隐藏其他可见的 dialog（如果还亮着）
                for picker in screen.query(DateSelect):
                    other = picker.dialog
                    if other is not None and other is not dlg and _dlg_is_visible(other):
                        other.styles.offset = (-999, -999)
                # 再设置当前 dialog 到目标位置
                dlg.styles.offset = final_offset

            # 设置日期并聚焦
            if self.date is not None:
                dlg.date_picker.date = self.date
                for day in dlg.query("DayLabel.--day"):
                    if day.day == self.date.day:
                        day.focus()
                        break
            else:
                try:
                    dlg.query_one("DayLabel.--today").focus()
                except NoMatches:
                    dlg.query("DayLabel.--day").first().focus()

            # --- 诊断日志 ---
            full_map = comp.full_map
            screen_region = screen.size.region
            vig = comp.visible_widgets

            if dlg in full_map:
                mg = full_map[dlg]
                dlg_region, dlg_clip = mg.region, mg.clip
                in_screen = dlg_region.overlaps(screen_region)
                clip_ok = dlg_clip.overlaps(dlg_region)
            else:
                alt_key = dlg._render_widget if hasattr(dlg, '_render_widget') else None
                if alt_key and alt_key != dlg and alt_key in full_map:
                    mg = full_map[alt_key]
                    dlg_region, dlg_clip = mg.region, mg.clip
                    in_screen = dlg_region.overlaps(screen_region)
                    clip_ok = dlg_clip.overlaps(dlg_region)
                else:
                    dlg_region = dlg_clip = "N/A"
                    in_screen = clip_ok = "N/A"

            in_compositor = dlg in vig
            logger.debug(
                f"_patched_show: final_offset={final_offset}, "
                f"flow_position=({flow_x},{flow_y}) cached={dlg_id in _flow_cache}, "
                f"in_compositor={in_compositor}, "
                f"in_full_map={dlg in full_map}, "
                f"dlg_region={dlg_region}, "
                f"dlg_clip={dlg_clip}, "
                f"screen_region={screen_region}, "
                f"in_screen={in_screen}, clip_ok={clip_ok}, "
                f"visible_widgets_count={len(vig)}, "
                f"display={dlg.display}, "
                f"visible={dlg.visible}, "
                f"size=({dlg.size.width},{dlg.size.height})"
            )

        DateSelect._show_date_picker = _patched_show
        super().__init__(id="merge-mode-dialog", **kwargs)
        self.theme_manager = theme_manager
        self.db_manager = db_manager
        self.site_id = site_id
        self.site_name = site_name
        self.i18n = get_global_i18n()
        self.novel_site = novel_site or {}

        # 全量缓存
        self.all_history = all_history
        self.min_date = min_date
        self.max_date = max_date

        # 默认日期范围：最近一周 ~ 今天（避免遗漏近期下载的书籍）
        from datetime import datetime, timedelta
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        self._start_date = week_ago if week_ago >= min_date else min_date
        self._start_date = today #只取今天即可 不用一周前
        self._end_date = today if today <= max_date else max_date

        # 分组结果（初始为空，on_mount 时加载）
        self.groups: List[BookGroup] = []
        self._selected_group_ids: Set[int] = set()
        self._total_books: int = 0

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                # 标题
                Label(
                    f"📑 {self.i18n.t('merge_mode.title')} — {self.site_name}",
                    id="merge-mode-title",
                ),
                # 日期筛选行
                Horizontal(
                    Label(self.i18n.t('merge_mode.date_filter'), classes="date-filter-label"),
                    Label(self.i18n.t('merge_mode.date_start'), classes="date-sub-label"),
                    DateSelect(date=pendulum.parse(self._start_date), format="YYYY-MM-DD", picker_mount="#merge-mode-dialog", id="filter-start-date"),
                    Label(self.i18n.t('merge_mode.date_end'), classes="date-sub-label"),
                    DateSelect(date=pendulum.parse(self._end_date), format="YYYY-MM-DD", picker_mount="#merge-mode-dialog", id="filter-end-date"),
                    Button(self.i18n.t('merge_mode.date_query'), id="date-query-btn", variant="primary"),
                    id="merge-mode-filter",
                ),
                # 统计摘要
                Label("", id="merge-mode-summary"),
                # 自动合并提示
                Static("", id="merge-mode-auto-hint"),
                # 分组列表表格
                DataTable(id="merge-group-table"),
                # 底部按钮
                Horizontal(
                    Button(self.i18n.t('merge_mode.select_all'), id="select-all-btn"),
                    Button(self.i18n.t('merge_mode.deselect_all'), id="deselect-all-btn"),
                    Button(self.i18n.t('merge_mode.invert_selection'), id="invert-btn"),
                    Button(self.i18n.t('merge_mode.merge_selected'), id="confirm-merge-btn", variant="primary"),
                    Button(self.i18n.t('common.cancel'), id="cancel-btn"),
                    id="merge-mode-buttons",
                ),
                # 状态提示
                Label("", id="merge-mode-status"),
                id="merge-mode-container",
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """初始化：添加表格列，加载默认日期范围的分组"""
        self.theme_manager.apply_theme_to_screen(self)

        # DateSelect.on_mount 保持 no-op，避免 recompose 时失效
        from textual_datepicker._date_select import DatePickerDialog

        # dialog 挂在 Screen 直属下，display=True 保证 layout 计算，
        # offset=(-999,-999) 离屏隐藏。_patched_show 中动态获取 Screen
        # 布局的 flow position 并计算正确的 CSS offset。
        for picker_id in ("filter-start-date", "filter-end-date"):
            try:
                picker = self.query_one(f"#{picker_id}", DateSelect)
                if picker.dialog is None:
                    dlg = DatePickerDialog()
                    dlg.target = picker  # type: ignore
                    dlg.display = True
                    dlg.offset = (-999, -999)  # 离屏隐藏
                    picker.dialog = dlg
                    self.mount(dlg)
                    logger.debug(
                        f"Mounted dialog for {picker_id} on Screen, "
                        f"children={len(dlg.children)}, "
                        f"date_picker={dlg.date_picker is not None}"
                    )
            except Exception as e:
                logger.warning(f"Failed to init date picker {picker_id}: {e}")
        self.screen._compositor.reflow(self.screen, self.screen.size)
        self.refresh(layout=True)

        table = self.query_one("#merge-group-table", DataTable)
        table.cursor_type = "row"
        table.add_column("✓", width=3)
        table.add_column(self.i18n.t('merge_mode.col_group_name'), width=40)
        table.add_column(self.i18n.t('merge_mode.col_book_count'), width=10)
        table.add_column(self.i18n.t('merge_mode.col_date'), width=22)
        table.add_column(self.i18n.t('merge_mode.col_type'), width=12)

        # 默认加载昨天~今天的分组
        self._do_grouping(self._start_date, self._end_date)
        table.focus()

    # ─── 分组逻辑 ───────────────────────────────────────────

    def _do_grouping(self, start_date: str, end_date: str) -> None:
        """根据日期范围重新分组并刷新显示（用 crawl_time 精确比较）"""
        self._start_date = start_date
        self._end_date = end_date

        from datetime import datetime, timedelta

        # 解析日期边界
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)
        except ValueError:
            # 日期格式错误时回退到简单字符串过滤
            filtered = [
                item for item in self.all_history
                if start_date <= (item.get('crawl_time', '')[:10]) <= end_date
            ]
        else:
            # 用 crawl_time 精确比较（覆盖整天 00:00:00 ~ 23:59:59.999999）
            filtered = []
            for item in self.all_history:
                crawl_time = item.get('crawl_time', '')
                if not crawl_time:
                    continue
                try:
                    # ISO 格式: 2026-06-19T11:30:00.123456
                    ct = datetime.strptime(crawl_time.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    # 尝试其他格式
                    try:
                        ct = datetime.strptime(crawl_time[:19], "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        # 最终回退：用前10位比较
                        if start_date <= crawl_time[:10] <= end_date:
                            filtered.append(item)
                        continue
                if start_dt <= ct <= end_dt:
                    filtered.append(item)

        logger.debug(
            f"日期过滤: {start_date}~{end_date}, "
            f"全部记录={len(self.all_history)}, 过滤后={len(filtered)}"
        )
        if filtered:
            sample_dates = sorted(set(
                item.get('crawl_time', '')[:10] for item in filtered
            ))
            sample_titles = [item.get('novel_title', '') for item in filtered[:5]]
            logger.debug(
                f"结果日期: {sample_dates[:3]}..." if len(sample_dates) > 3
                else f"结果日期: {sample_dates}"
            )
            logger.debug(f"结果前5本书名: {sample_titles}")

        if not filtered:
            self.groups = []
            self._selected_group_ids = set()
            self._total_books = 0
            self._refresh_display()
            self.notify(
                self.i18n.t('merge_mode.no_range_history', start=start_date, end=end_date),
                severity="warning",
            )
            return

        # ── 分组策略 ──
        # 1. 对 filtered 中的每条记录，用 normalize_book_title 提取核心书名
        # 2. 用核心书名 LIKE %xxx% 搜索数据库中该书的全部历史（跨日期）
        # 3. 去重建组，自动合并章节组

        # Step 1: 提取唯一核心书名
        seen_cores: Set[str] = set()
        core_list: List[str] = []
        for item in filtered:
            title = item.get('novel_title', '').strip()
            if not title:
                continue
            core = normalize_book_title(title)
            if not core or len(core) < 2:
                continue
            if core not in seen_cores:
                seen_cores.add(core)
                core_list.append(core)

        logger.debug(
            f"核心书名提取: {len(filtered)}条 → {len(core_list)}个唯一核心书名"
        )
        for cn in core_list[:10]:
            logger.debug(f"  '{cn}'")
        if len(core_list) > 10:
            logger.debug(f"  ... 共 {len(core_list)} 个（仅展示前10）")

        # Step 2: 用每个核心书名 LIKE 搜索数据库全部历史记录
        all_seen_ids: Set[Any] = set()
        raw_groups: List[BookGroup] = []
        group_id = 0

        for core in core_list:
            books = self.db_manager.search_crawl_history_by_title(
                self.site_id, core
            )
            if not books:
                # 兜底：DB 搜不到时用 filtered 中匹配的记录
                books = [
                    item for item in filtered
                    if normalize_book_title(item.get('novel_title', '')) == core
                ]

            # 去重（不同核心书名可能搜到同一本书）
            deduped: List[Dict[str, Any]] = []
            for b in books:
                bid = b.get('id')
                if bid not in all_seen_ids:
                    all_seen_ids.add(bid)
                    deduped.append(b)

            if deduped:
                group_id += 1
                raw_groups.append(BookGroup(
                    group_id=group_id,
                    base_title=core,
                    books=deduped,
                ))
                logger.debug(
                    f"  '{core}' → DB搜到{len(books)}条，去重后{len(deduped)}条"
                )

        logger.debug(
            f"DB搜索分组: {len(core_list)}核心 → {len(raw_groups)}组"
        )

        # Step 3: 跨组合并在同一本书的不同章节/命名变体
        self.groups, merged_ids = _auto_merge_chapter_groups(raw_groups)
        if merged_ids:
            logger.debug(
                f"自动合并(第二步): {len(raw_groups)} → {len(self.groups)}组"
                f"（合并了 {len(merged_ids)} 组）"
            )

        # 过滤：只显示记录数 > 1 的组（只有1条不需要合并）
        if self.groups:
            before = len(self.groups)
            self.groups = [g for g in self.groups if g.book_count > 1]
            logger.debug(
                f"过滤单本组: {before}组 → {len(self.groups)}组"
                f"（移除 {before - len(self.groups)} 组）"
            )

        if not self.groups:
            self._selected_group_ids = set()
            self._total_books = 0
            self._refresh_display()
            self.notify(self.i18n.t('merge_mode.no_groups'), severity="information")
            return

        # 默认全选
        self._selected_group_ids = set(g.group_id for g in self.groups if g.is_selected)
        self._total_books = sum(g.book_count for g in self.groups)
        self._refresh_display()

    def _refresh_display(self) -> None:
        """刷新摘要、表格、提示和状态"""
        # 统计摘要
        summary = self.query_one("#merge-mode-summary", Label)
        if self.groups:
            summary.update(
                self.i18n.t(
                    'merge_mode.group_summary',
                    group_count=len(self.groups),
                    start=self._start_date,
                    end=self._end_date,
                )
            )
        else:
            summary.update("")

        # 自动合并提示
        hint = self.query_one("#merge-mode-auto-hint", Static)
        auto_count = sum(1 for g in self.groups if g.is_auto_same_book)
        if auto_count > 0:
            hint.update(f"🔗 {self.i18n.t('merge_mode.auto_merged_hint', count=auto_count)}")
        else:
            hint.update("")

        # 表格
        self._refresh_table()
        self._update_status()

    # ─── 查询按钮 ───────────────────────────────────────────

    @on(Button.Pressed, "#date-query-btn")
    def on_date_query(self) -> None:
        """点击查询按钮重新分组"""
        start_picker = self.query_one("#filter-start-date", DateSelect)
        end_picker = self.query_one("#filter-end-date", DateSelect)
        start_dt = start_picker.date
        end_dt = end_picker.date
        if start_dt is None or end_dt is None:
            self.notify(self.i18n.t('merge_mode.no_date'), severity="warning")
            return
        start = start_dt.format("YYYY-MM-DD")
        end = end_dt.format("YYYY-MM-DD")
        if start > end:
            start, end = end, start
        self._do_grouping(start, end)

    def _update_status(self) -> None:
        """更新状态栏"""
        selected = len(self._selected_group_ids)
        total_books = sum(
            g.book_count for g in self.groups
            if g.group_id in self._selected_group_ids
        )
        status = self.query_one("#merge-mode-status", Label)
        status.update(
            self.i18n.t(
                'merge_mode.status',
                selected_groups=selected,
                total_groups=len(self.groups),
                selected_books=total_books,
            )
        )

    def _refresh_table(self) -> None:
        """刷新表格显示"""
        table = self.query_one("#merge-group-table", DataTable)
        table.clear()

        for group in self.groups:
            is_sel = group.group_id in self._selected_group_ids
            check_mark = "☑" if is_sel else "☐"
            type_label = "章节合集" if group.is_auto_same_book else "相似书籍"

            table.add_row(
                check_mark,
                group.display_title,
                str(group.book_count),
                group.date_range,
                type_label,
                key=str(group.group_id),
            )

    def _toggle_current_row(self) -> None:
        """切换当前行的选中状态"""
        table = self.query_one("#merge-group-table", DataTable)
        if table.row_count == 0:
            return

        try:
            cursor_row = getattr(table, 'cursor_row', None)
            if cursor_row is None or not (0 <= cursor_row < len(table.rows)):
                return

            row_keys = list(table.rows.keys())
            row_key = row_keys[cursor_row]
            if row_key is None:
                return
            group_id = int(str(row_key.value if hasattr(row_key, 'value') else row_key))
            if group_id in self._selected_group_ids:
                self._selected_group_ids.discard(group_id)
            else:
                self._selected_group_ids.add(group_id)

            self._refresh_table()

            # 恢复光标到原位
            if cursor_row < len(table.rows):
                if hasattr(table, 'move_cursor'):
                    table.move_cursor(row=cursor_row)
                else:
                    while table.cursor_row > 0:
                        table.action_cursor_up()
                    for _ in range(cursor_row):
                        table.action_cursor_down()
                table.focus()

            self._update_status()
        except (ValueError, IndexError) as e:
            logger.debug(f"切换行失败: {e}")

    def _copy_focused_group_title(self) -> None:
        """复制当前光标所在行的书籍名称到剪贴板"""
        table = self.query_one("#merge-group-table", DataTable)
        if table.row_count == 0:
            return

        try:
            cursor_row = getattr(table, 'cursor_row', None)
            if cursor_row is None or not (0 <= cursor_row < len(table.rows)):
                return

            row_keys = list(table.rows.keys())
            row_key = row_keys[cursor_row]
            if row_key is None:
                return
            group_id = int(str(row_key.value if hasattr(row_key, 'value') else row_key))

            group = next((g for g in self.groups if g.group_id == group_id), None)
            if not group:
                return

            display_title = group.display_title
            if not display_title:
                return

            try:
                import pyperclip
                pyperclip.copy(display_title)
            except ImportError:
                import subprocess
                import platform
                system = platform.system()
                try:
                    if system == 'Darwin':
                        subprocess.run(['pbcopy'], input=display_title, text=True, check=True)
                    elif system == 'Windows':
                        subprocess.run(['clip'], input=display_title, text=True, check=True, shell=True)
                    else:
                        try:
                            subprocess.run(['xclip', '-selection', 'clipboard'], input=display_title, text=True, check=True)
                        except (subprocess.SubprocessError, FileNotFoundError):
                            subprocess.run(['xsel', '--clipboard', '--input'], input=display_title, text=True, check=True)
                except Exception as copy_error:
                    logger.error(f"复制书名到剪贴板失败: {copy_error}")
                    self.notify(self.i18n.t('cannot_copy'), severity="error", timeout=2)
                    return

            self.notify(
                self.i18n.t('crawler.title_copied', title=display_title),
                timeout=2,
            )
        except (ValueError, IndexError) as e:
            logger.debug(f"复制书名失败: {e}")

    @on(Button.Pressed, "#select-all-btn")
    def on_select_all(self) -> None:
        """全选"""
        self._selected_group_ids = set(g.group_id for g in self.groups)
        self._refresh_table()
        self._update_status()

    @on(Button.Pressed, "#deselect-all-btn")
    def on_deselect_all(self) -> None:
        """取消全选"""
        self._selected_group_ids.clear()
        self._refresh_table()
        self._update_status()

    @on(Button.Pressed, "#invert-btn")
    def on_invert_selection(self) -> None:
        """反选"""
        all_ids = set(g.group_id for g in self.groups)
        self._selected_group_ids = all_ids - self._selected_group_ids
        self._refresh_table()
        self._update_status()

    @on(Button.Pressed, "#confirm-merge-btn")
    def on_confirm_merge(self) -> None:
        """确认合并选中组 —— 推入详情弹窗，完成后传回结果再 dismiss"""
        if not self._selected_group_ids:
            self.notify(self.i18n.t('merge_mode.no_selection'), severity="warning")
            return

        selected_groups = [
            g for g in self.groups
            if g.group_id in self._selected_group_ids
        ]

        if not selected_groups:
            return

        # 组装数据
        group_data = []
        for group in selected_groups:
            group_data.append({
                "group_id": group.group_id,
                "base_title": group.base_title,
                "display_title": group.display_title,
                "books": group.books,
                "is_auto_same_book": group.is_auto_same_book,
            })

        from src.ui.dialogs.crawler_merge_detail_dialog import CrawlerMergeDetailDialog

        def handle_detail_result(detail_result: Optional[Dict[str, Any]]) -> None:
            """详情弹窗完成后，把结果传给主页面的回调"""
            if detail_result and detail_result.get('success'):
                self.dismiss({
                    "success": True,
                    "action": "merge_mode",
                    "merged_groups": detail_result.get('merged_groups', []),
                    "skipped_groups": detail_result.get('skipped_groups', []),
                })
            else:
                self.dismiss({
                    "success": False,
                    "action": "merge_mode",
                    "message": detail_result.get('message', '') if detail_result else '',
                })

        self.app.push_screen(
            CrawlerMergeDetailDialog(self.theme_manager, group_data, self.db_manager, novel_site=self.novel_site),
            handle_detail_result,
        )

    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self) -> None:
        """取消"""
        self.dismiss({
            "success": False,
            "action": "merge_mode",
            "message": self.i18n.t('batch_ops.cancel_merge'),
        })

    def action_toggle_row(self) -> None:
        """空格键：切换行选中"""
        self._toggle_current_row()

    def action_toggle_select_all(self) -> None:
        """a键：全选/取消全选切换（与爬取管理一致）"""
        if self._selected_group_ids:
            # 已有选中项 -> 取消全选
            self.on_deselect_all()
        else:
            # 无选中项 -> 全选
            self.on_select_all()

    def action_confirm_merge(self) -> None:
        """回车键：合并选中组"""
        self.on_confirm_merge()

    def action_invert_selection(self) -> None:
        """r键：反选"""
        self.on_invert_selection()

    def action_copy_title(self) -> None:
        """y键：复制当前行书名"""
        self._copy_focused_group_title()

    def action_cancel(self) -> None:
        """ESC键：取消"""
        self.on_cancel()

    def on_key(self, event) -> None:
        """按键事件"""
        if event.key == "escape":
            self.on_cancel()
            event.stop()
        elif event.key == "space":
            self._toggle_current_row()
            event.stop()


