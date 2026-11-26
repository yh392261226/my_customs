"""书籍题材分类：按书名、标签与正文摘要识别可筛选的分类标签。

分类规则默认内置，并支持在配置目录下用 ``book_categories.json`` 覆盖或扩展：

    {
      "NTR": ["ntr", "牛头人", "绿帽"],
      "SM": ["sm", "ＳＭ"]
    }

规则里的别名统一走项目现有的归一化逻辑（繁简、全半角、大小写），因此书名里的
全角/繁体写法也能命中。分类结果以逗号分隔字符串写入 ``books.categories``，
供书架筛选、全文搜索与浏览器 API 复用。
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from src.utils.logger import get_logger
from src.utils.string_utils import normalize_match_text

logger = get_logger(__name__)

# 依据当前书库文件名分布整理的默认题材标签。别名只用于元数据归类，不参与正文生成。
DEFAULT_CATEGORY_RULES: Dict[str, List[str]] = {
    "NTR": ["ntr", "牛头人", "绿帽"],
    "SM": ["sm", "ｓｍ"],
    "NP": ["np", "多女"],
    "后宫": ["后宫", "後宮"],
    "百合": ["百合"],
    "人妻": ["人妻"],
    "御姐": ["御姐"],
    "少女": ["少女"],
    "同人": ["同人"],
    "穿越": ["穿越"],
    "重生": ["重生"],
    "系统": ["系统"],
    "都市": ["都市", "男人", "女人", "朋友", "邻居", "同事", "老板", "员工"],
    "校园": ["校园", "学院", "同学", "校花", "大学生", "女大学生", "大学"],
    "奇幻": ["奇幻", "魔法"],
    "科幻": ["科幻", "未来", "星际"],
    "末世": ["末世", "丧尸"],
    "修真": ["修真", "仙侠"],
    "玄幻": ["玄幻", "修仙", "妖魔", "神仙"],
    "武侠": ["武侠"],
    "灵异": ["灵异", "恐怖"],
    "悬疑": ["悬疑", "推理"],
    "历史": ["历史"],
    "军事": ["军事"],
    "游戏": ["游戏", "网游", "电竞"],
    "体育": ["篮球", "足球"],
    "职场": ["职场", "商战", "金融", "法律", "医学", "老板", "员工", "医生", "护士", "警察"],
    "豪门": ["豪门", "总裁", "千金", "少爷"],
    "权贵": ["公主", "皇帝", "皇后", "王爷"],
    "娱乐圈": ["娱乐圈"],
    "美食": ["美食"],
    "快穿": ["快穿", "穿书", "无限流"],
    "种田": ["种田", "基建", "领主"],
    "恋爱": ["女友", "老婆", "妻子", "娇妻", "少妇", "恋人"],
    "亲情": ["妈妈", "母亲", "姐姐", "小姨子"],
    "师生": ["老师", "女教师", "学生"],
    "日常": ["生活", "日记", "幸福", "秘密", "日常", "轻松", "回忆"],
    "青春": ["青梅竹马", "校花", "少年", "青年", "同学"],
    "情感": ["爱情", "情侣", "夫妻", "婚姻", "情感", "关系"],
    "家庭": ["家庭", "夫妻", "婚姻"],
}

_CATEGORY_FILENAME = "book_categories.json"
# 筛选专用哨兵：表示「没有任何分类」，不会写入分类规则或数据库
NO_CATEGORY = "__no_category__"
_MAX_CLASSIFY_CHARS = 8000
_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "big5", "utf-16")
_COMMON_CN = set(
    "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动"
    "同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自"
    "二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日"
    "那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变"
    "条只没结解问意建月公无系军很情者最立代想已通并提直题"
)


def _override_path() -> str:
    """返回分类规则覆盖文件路径。"""
    try:
        from src.config.config_manager import ConfigManager
        return os.path.join(ConfigManager.get_instance().config_dir, _CATEGORY_FILENAME)
    except Exception:
        return os.path.join(str(Path.home()), ".config", "new_preader", _CATEGORY_FILENAME)


@lru_cache(maxsize=1)
def load_category_rules() -> Dict[str, List[str]]:
    """加载分类规则：内置规则 + 用户覆盖（同名分类整体替换）。"""
    rules: Dict[str, List[str]] = {
        name: list(aliases) for name, aliases in DEFAULT_CATEGORY_RULES.items()
    }
    path = _override_path()
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if isinstance(data.get("categories"), dict):
                    data = data["categories"]
                for name, aliases in data.items():
                    if not isinstance(name, str) or not name.strip():
                        continue
                    if isinstance(aliases, str):
                        aliases = [aliases]
                    if isinstance(aliases, (list, tuple, set)):
                        rules[name.strip()] = [str(a) for a in aliases if str(a).strip()]
    except Exception as exc:
        logger.warning(f"读取分类规则覆盖文件失败: {path}, 错误: {exc}")
    return rules


def reload_category_rules() -> Dict[str, List[str]]:
    """强制重新加载分类规则（修改覆盖文件后调用）。"""
    load_category_rules.cache_clear()
    _alias_pattern.cache_clear()
    return load_category_rules()


def save_category_rules(rules: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """把当前分类规则写入配置目录，并刷新内存缓存。"""
    path = _override_path()
    normalized: Dict[str, List[str]] = {}
    for name, aliases in (rules or {}).items():
        clean_name = str(name or "").strip()
        if not clean_name:
            continue
        if isinstance(aliases, str):
            aliases = [aliases]
        normalized[clean_name] = [
            str(alias).strip() for alias in (aliases or []) if str(alias).strip()
        ]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"categories": normalized}, f, ensure_ascii=False, indent=2)
    return reload_category_rules()


def add_category(name: str, aliases: Any) -> Dict[str, List[str]]:
    """新增或覆盖一个分类规则。"""
    rules = dict(load_category_rules())
    alias_list = [aliases] if isinstance(aliases, str) else list(aliases or [])
    rules[str(name).strip()] = [
        str(a).strip() for a in alias_list if str(a).strip()
    ]
    return save_category_rules(rules)


def update_category(old_name: str, new_name: str, aliases: Any,
                    rename_in_library: bool = True) -> Dict[str, List[str]]:
    """修改分类名称/别名；改名时同步更新已分类的书籍。"""
    rules = dict(load_category_rules())
    rules.pop(old_name, None)
    rules[str(new_name).strip()] = [
        str(a).strip() for a in (aliases or []) if str(a).strip()
    ]
    saved = save_category_rules(rules)
    if rename_in_library and old_name != new_name:
        rename_category_in_library(old_name, new_name)
    return saved


def delete_category(name: str, remove_from_books: bool = True) -> Dict[str, List[str]]:
    """删除分类规则；默认同时从已有书籍中移除该分类。"""
    rules = dict(load_category_rules())
    rules.pop(name, None)
    saved = save_category_rules(rules)
    if remove_from_books:
        remove_category_from_library(name)
    return saved


def _rewrite_book_categories(old_names: set, new_names: set) -> int:
    """按映射重写书籍分类与检索文本，返回更新数量。"""
    import sqlite3

    from src.core.database_manager import DatabaseManager

    dm = DatabaseManager()
    updated = 0
    with sqlite3.connect(dm.get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT path, title, author, pinyin, tags, categories FROM books"
        ).fetchall()
        pending: List[tuple] = []
        for row in rows:
            current = categories_from_storage(row["categories"])
            if not old_names.intersection(current):
                continue
            rewritten: List[str] = []
            for name in current:
                if name in old_names:
                    rewritten.extend(sorted(new_names))
                elif name not in rewritten:
                    rewritten.append(name)
            rewritten = [n for n in rewritten if n]
            stored = categories_to_storage(rewritten)
            search_text = DatabaseManager._build_search_text(
                row["title"] or "", row["author"] or "", row["pinyin"] or "",
                row["tags"] or "", stored,
            )
            pending.append((stored, search_text, row["path"]))
            if len(pending) >= 500:
                conn.executemany(
                    "UPDATE books SET categories = ?, search_text = ? WHERE path = ?", pending
                )
                updated += len(pending)
                pending.clear()
        if pending:
            conn.executemany(
                "UPDATE books SET categories = ?, search_text = ? WHERE path = ?", pending
            )
            updated += len(pending)
        conn.commit()
    return updated


def rename_category_in_library(old_name: str, new_name: str) -> int:
    """把已有书籍上的旧分类名替换为新分类名。"""
    return _rewrite_book_categories({old_name}, {new_name})


def remove_category_from_library(name: str) -> int:
    """从已有书籍上移除指定分类。"""
    return _rewrite_book_categories({name}, set())


@lru_cache(maxsize=256)
def _alias_pattern(alias: str) -> Optional[re.Pattern]:
    """把别名编译为正则；短英文别名加词边界，避免 sm 命中词内片段。"""
    normalized = normalize_match_text(alias)
    if not normalized:
        return None
    escaped = re.escape(normalized)
    if re.fullmatch(r"[a-z0-9]{1,5}", normalized):
        escaped = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return re.compile(escaped)


def normalize_categories(values: Any) -> List[str]:
    """把列表/逗号串/单值统一为去重后的分类名列表。"""
    if not values:
        return []
    if isinstance(values, str):
        raw_items: Iterable[Any] = values.split(",")
    elif isinstance(values, (list, tuple, set)):
        raw_items = values
    else:
        raw_items = [values]
    result: List[str] = []
    seen: Set[str] = set()
    for item in raw_items:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def categories_to_storage(categories: Any) -> str:
    """序列化为数据库存储格式（逗号分隔，便于 LIKE 筛选）。"""
    return ",".join(normalize_categories(categories))


def categories_from_storage(raw: Any) -> List[str]:
    """从数据库字段恢复分类列表。"""
    return normalize_categories(raw)


def _decode_quality(text: str) -> int:
    """给解码结果打分：常用中文多、乱码/私用区/控制字符少则更高。"""
    sample = text[:3000]
    common_cn = sum(1 for ch in sample if ch in _COMMON_CN)
    cjk = sum(1 for ch in sample if "\u4e00" <= ch <= "\u9fff")
    pua = sum(1 for ch in sample if "\ue000" <= ch <= "\uf8ff" or "\uf900" <= ch <= "\ufaff")
    rare = sum(1 for ch in sample if "\u3400" <= ch <= "\u4dbf")
    controls = sum(1 for ch in sample if ord(ch) < 32 and ch not in "\n\r\t")
    return common_cn * 5 + cjk - pua * 8 - rare * 3 - controls * 10


def read_content_sample(path: str, max_bytes: int = 128 * 1024,
                        max_chars: int = _MAX_CLASSIFY_CHARS) -> str:
    """读取文件开头作为分类样本；只覆盖文本类文件，失败时返回空串。"""
    if not path or not os.path.isfile(path):
        return ""
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".txt", ".md", ".text"):
        return ""
    try:
        with open(path, "rb") as f:
            raw = f.read(max_bytes)
    except OSError:
        return ""
    candidates: List[tuple] = []
    for encoding in _ENCODINGS:
        for errors in ("strict", "ignore"):
            try:
                text = raw.decode(encoding, errors=errors)
            except Exception:
                continue
            candidates.append((_decode_quality(text), text))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1][:max_chars]
    return raw.decode("utf-8", errors="ignore")[:max_chars]


def classify_book(title: str = "", tags: Any = None, content: Optional[str] = None,
                  categories: Any = None) -> List[str]:
    """按书名、标签、正文摘要和显式分类推断书籍的分类列表。

    多分类可同时命中；结果顺序遵循规则定义顺序，保证写入稳定。
    """
    explicit = normalize_categories(categories)
    parts: List[str] = [str(title or ""), ",".join(normalize_categories(tags))]
    if content:
        parts.append(str(content)[:_MAX_CLASSIFY_CHARS])
    source = normalize_match_text(" ".join(parts))

    matched: List[str] = []
    for name, aliases in load_category_rules().items():
        if name in explicit:
            if name not in matched:
                matched.append(name)
            continue
        for alias in aliases:
            pattern = _alias_pattern(alias)
            if pattern is not None and pattern.search(source):
                matched.append(name)
                break
    for name in explicit:
        if name not in matched:
            matched.append(name)
    return matched


def classify_book_file(path: str, title: str = "", tags: Any = None,
                       include_content: bool = True) -> List[str]:
    """读取文件摘要后调用 :func:`classify_book`。"""
    content = read_content_sample(path) if include_content else ""
    return classify_book(title=title, tags=tags, content=content)


def get_known_categories() -> List[str]:
    """返回 UI 可选分类：内置/自定义规则 + 数据库中已出现的分类。"""
    categories = list(load_category_rules().keys())
    try:
        from src.core.database_manager import DatabaseManager
        db_path = DatabaseManager().get_db_path()
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT categories FROM books WHERE categories IS NOT NULL AND categories != '' LIMIT 2000"
            ).fetchall()
    except Exception as exc:
        logger.debug(f"读取已存分类失败，仅使用规则分类: {exc}")
        return categories
    for row in rows:
        for name in categories_from_storage(row[0]):
            if name not in categories:
                categories.append(name)
    return categories


def get_filter_category_options() -> List[str]:
    """筛选弹窗使用的分类选项：已有分类 + 「无分类」哨兵。"""
    options = get_known_categories()
    if NO_CATEGORY not in options:
        options.append(NO_CATEGORY)
    return options


def book_has_categories(values: Any) -> bool:
    """判断书籍是否至少有一个分类。"""
    return bool(categories_from_storage(values))


def backfill_library_categories(batch_size: int = 500, include_content: bool = True) -> int:
    """为已有书籍补写分类，返回更新数量。可通过 ``--classify-books`` 调用。"""
    import sqlite3

    from src.core.database_manager import DatabaseManager

    dm = DatabaseManager()
    updated = 0
    with sqlite3.connect(dm.get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT path, title, author, pinyin, tags FROM books").fetchall()
        pending: List[tuple] = []
        for row in rows:
            cats = classify_book_file(row["path"], title=row["title"] or "",
                                      tags=row["tags"] or "", include_content=include_content)
            stored = categories_to_storage(cats)
            search_text = DatabaseManager._build_search_text(
                row["title"] or "", row["author"] or "", row["pinyin"] or "",
                row["tags"] or "", stored
            )
            pending.append((stored, search_text, row["path"]))
            if len(pending) >= batch_size:
                conn.executemany(
                    "UPDATE books SET categories = ?, search_text = ? WHERE path = ?", pending
                )
                updated += len(pending)
                pending.clear()
        if pending:
            conn.executemany(
                "UPDATE books SET categories = ?, search_text = ? WHERE path = ?", pending
            )
            updated += len(pending)
        conn.commit()
    logger.info(f"书籍分类回填完成，更新 {updated} 本")
    return updated
