"""
批量去重「进度暂存」工具

批量去重的检测（哈希 + SimHash + 深度内容比对）非常耗时，而重复书籍对话框
关闭后，检测出来的分组与人工选择此前全部丢失。本模块把：
  - 已检测出的重复分组（只存书籍路径，不存书籍对象与正文）
  - 每组的推荐保留 / 推荐删除项
  - 人工选择、已跳过组、已查看组、当前停留位置
序列化到应用数据目录的 JSON 文件。下次点「继续上次去重」时用书籍路径从
当前书库重建 DuplicateGroup，直接跳过耗时的全量检测。

与 merge_staging.py 的区别：合并暂存的分组可由爬取历史实时重建，所以只保存
每组的处理结果；去重的分组来自昂贵的全量检测，必须连分组一起保存。
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Set

from src.utils.file_utils import FileUtils
from src.utils.logger import get_logger

logger = get_logger(__name__)

STAGING_DIR = os.path.join(FileUtils.get_app_data_dir("newreader"), "dedup_staging")
STAGING_FILE = os.path.join(STAGING_DIR, "library.json")
_VERSION = 1


def has_staging() -> bool:
    """是否存在去重暂存"""
    return os.path.exists(STAGING_FILE)


def load_staging() -> Optional[Dict[str, Any]]:
    """读取暂存；不存在、版本不匹配或损坏时返回 None"""
    try:
        with open(STAGING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("version") != _VERSION:
            return None
        if not isinstance(data.get("groups"), list):
            return None
        return data
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.error(f"读取去重暂存失败: {e}")
        return None


def save_staging(snapshot: Dict[str, Any]) -> bool:
    """原子写入暂存文件（先写 .tmp 再替换，避免写一半导致文件损坏）"""
    try:
        os.makedirs(STAGING_DIR, exist_ok=True)
        data = {
            "version": _VERSION,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "batch_dedupe",
            **{k: v for k, v in snapshot.items() if k not in ("version", "saved_at")},
        }
        tmp_path = STAGING_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, STAGING_FILE)
        logger.info(f"去重进度已暂存: 分组数={len(data.get('groups', []))}")
        return True
    except Exception as e:
        logger.error(f"保存去重暂存失败: {e}")
        return False


def clear_staging() -> None:
    """删除暂存文件"""
    for path in (STAGING_FILE, STAGING_FILE + ".tmp"):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.debug(f"清除去重暂存失败: {e}")


def staging_summary() -> Optional[Dict[str, Any]]:
    """返回暂存摘要（用于弹窗提示）；无有效暂存时返回 None"""
    data = load_staging()
    if not data or not data.get("groups"):
        return None
    return {
        "count": len(data["groups"]),
        "saved_at": data.get("saved_at", ""),
        "complete": bool(data.get("complete", True)),
    }


def build_snapshot(
    groups: List[Any],
    selected_books: Set[str],
    recommended_selected_books: Set[str],
    skipped_groups: Set[frozenset],
    viewed_groups: Set[frozenset],
    current_group_index: int,
    current_batch: int,
    total_batches: int,
    processing_remaining: bool,
    elapsed_seconds: Optional[float],
) -> Dict[str, Any]:
    """把检测结果与人工处理进度收集成可序列化的快照"""
    entries: List[Dict[str, Any]] = []
    for group in groups:
        dtype = group.duplicate_type
        entries.append({
            "duplicate_type": getattr(dtype, "name", str(dtype)),
            "duplicate_type_value": getattr(dtype, "value", ""),
            "similarity": float(getattr(group, "similarity", 0) or 0),
            "book_paths": [b.path for b in group.books],
            "recommended_to_keep": [b.path for b in (group.recommended_to_keep or [])],
            "recommended_to_delete": [b.path for b in (group.recommended_to_delete or [])],
        })

    return {
        "groups": entries,
        "state": {
            "selected_books": sorted(selected_books),
            "recommended_selected_books": sorted(recommended_selected_books),
            "skipped_groups": [sorted(k) for k in skipped_groups],
            "viewed_groups": [sorted(k) for k in viewed_groups],
            "current_group_index": int(current_group_index),
            "current_batch": int(current_batch),
            "total_batches": int(total_batches),
            "elapsed_seconds": elapsed_seconds,
        },
        # 检测是否全部完成；未完成的暂存只含已发现的分组，恢复时给出提示
        "complete": not bool(processing_remaining),
    }


def _restore_duplicate_type(entry: Dict[str, Any]):
    """恢复重复类型枚举。

    检测器 V1 / V2 定义了两个不同的 DuplicateType（V2 多一个 SIMHASH_SIMILAR），
    这里按 name -> value -> V2.name 的顺序回退，保证任何版本写入的暂存都能恢复。
    """
    from src.utils.book_duplicate_detector import DuplicateType as DisplayType

    name = str(entry.get("duplicate_type") or "")
    value = str(entry.get("duplicate_type_value") or "")
    try:
        return DisplayType[name]
    except (KeyError, TypeError):
        pass
    for t in DisplayType:
        if t.value == value or t.value == name:
            return t
    try:
        from src.utils.book_duplicate_detector_v2 import DuplicateType as V2Type
        return V2Type[name]
    except (KeyError, TypeError, ImportError):
        return DisplayType.HASH_IDENTICAL


def restore_snapshot(snapshot: Dict[str, Any], books: List[Any]):
    """用当前书库的书籍对象重建重复分组与处理进度。

    Returns:
        (groups, state)：groups 为重建后的 DuplicateGroup 列表；
        state 可直接传给 DuplicateBooksDialog 恢复界面状态。
    """
    from src.utils.book_duplicate_detector import DuplicateGroup

    book_map = {b.path: b for b in books if getattr(b, "path", None)}
    groups: List[Any] = []
    seen_keys = set()
    for entry in snapshot.get("groups", []):
        try:
            paths = [p for p in entry.get("book_paths", []) if p in book_map]
            key = frozenset(paths)
            # 书已被删除 / 书库记录已不存在的分组不再恢复
            if len(paths) < 2 or key in seen_keys:
                continue
            seen_keys.add(key)
            groups.append(DuplicateGroup(
                duplicate_type=_restore_duplicate_type(entry),
                books=[book_map[p] for p in paths],
                similarity=float(entry.get("similarity", 0) or 0),
                recommended_to_keep=[
                    book_map[p] for p in entry.get("recommended_to_keep", [])
                    if p in book_map
                ],
                recommended_to_delete=[
                    book_map[p] for p in entry.get("recommended_to_delete", [])
                    if p in book_map
                ],
            ))
        except Exception as e:
            logger.debug(f"恢复去重分组失败: {e}")

    valid_keys = {frozenset(b.path for b in g.books) for g in groups}
    live_paths = {p for key in valid_keys for p in key}
    raw = snapshot.get("state", {}) or {}

    def _keys(field: str) -> Set[frozenset]:
        result = set()
        for item in raw.get(field, []):
            try:
                key = frozenset(item)
                if key in valid_keys:
                    result.add(key)
            except TypeError:
                continue
        return result

    state = {
        "selected_books": {p for p in raw.get("selected_books", []) if p in live_paths},
        "recommended_selected_books": {
            p for p in raw.get("recommended_selected_books", []) if p in live_paths
        },
        "skipped_groups": _keys("skipped_groups"),
        "viewed_groups": _keys("viewed_groups"),
        "current_group_index": int(raw.get("current_group_index", 0) or 0),
        "current_batch": int(raw.get("current_batch", 0) or 0),
        "total_batches": int(raw.get("total_batches", 1) or 1),
        "elapsed_seconds": raw.get("elapsed_seconds"),
        "restored_count": len(groups),
        "complete": bool(snapshot.get("complete", True)),
        "saved_at": snapshot.get("saved_at", ""),
    }
    return groups, state
