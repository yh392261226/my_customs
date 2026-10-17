"""
合并模式「手动处理进度」暂存工具

合并模式下一次可能要人工处理上千个分组，工作量无法短期完成。
本模块把合并详情弹窗中：
  - 已被人工处理过的分组（合并/跳过的结果）
  - 尚未处理的分组（默认状态）
的当前进度序列化到磁盘。下次重新打开合并模式并进入详情后，
可据 book id 集合把匹配的分组结果恢复出来，避免重复劳动。

匹配方式：以每个分组的 book id 集合（frozenset）作为稳定指纹，
跨会话只要书籍未被合并/删除，id 集合就一致，即可精确恢复人工结果。
"""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from src.utils.logger import get_logger
from src.utils.file_utils import FileUtils

logger = get_logger(__name__)

_STAGING_DIR = os.path.join(FileUtils.get_app_data_dir("newreader"), "merge_staging")
_STAGING_VERSION = 1


def _staging_file_path(staging_key: str) -> str:
    """把任意 staging_key 规整为安全的文件名"""
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', str(staging_key))
    if not safe:
        safe = "default"
    return os.path.join(_STAGING_DIR, f"{safe}.json")


def save_staging(staging_key: str, entries: List[Dict[str, Any]]) -> bool:
    """
    保存暂存数据。

    entries: 每组的快照，形如
        {
            "book_ids": [书本 id 列表（用于跨会话匹配）],
            "base_title": "...",
            "display_title": "...",
            "state": {selected_ids, pending_delete_ids, merged_title, skipped, auto_sorted, processed},
        }
    """
    try:
        os.makedirs(_STAGING_DIR, exist_ok=True)
        data = {
            "version": _STAGING_VERSION,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "groups": entries,
        }
        with open(_staging_file_path(staging_key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"合并暂存已保存: key={staging_key}, 分组数={len(entries)}")
        return True
    except Exception as e:
        logger.error(f"保存合并暂存失败: {e}")
        return False


def load_staging(staging_key: str) -> Optional[Dict[str, Any]]:
    """读取暂存数据；不存在或损坏时返回 None"""
    path = _staging_file_path(staging_key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "groups" not in data:
            return None
        return data
    except Exception as e:
        logger.error(f"读取合并暂存失败: {e}")
        return None


def clear_staging(staging_key: str) -> None:
    """删除指定 staging_key 的暂存文件"""
    path = _staging_file_path(staging_key)
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"合并暂存已清除: key={staging_key}")
    except Exception as e:
        logger.debug(f"清除合并暂存失败: {e}")


def has_staging(staging_key: str) -> bool:
    return os.path.exists(_staging_file_path(staging_key))


def apply_staging_to_groups(
    groups: List[Dict[str, Any]],
    group_state: Dict[int, Dict[str, Any]],
    staging: Dict[str, Any],
) -> int:
    """
    把暂存中匹配的分组结果应用到当前 group_state，返回成功恢复的分组数。

    匹配规则：用每个分组的 book id 集合（frozenset）做精确匹配。
    """
    # 建立「当前分组书籍 id 集合 -> 下标」索引
    current_index: Dict[frozenset, int] = {}
    for i, g in enumerate(groups):
        ids = frozenset(b.get('id') for b in g.get('books', []))
        if ids:
            current_index[ids] = i

    restored = 0
    for entry in staging.get("groups", []):
        try:
            ids = frozenset(entry.get("book_ids", []))
            i = current_index.get(ids)
            if i is None:
                # 该分组在本会话已不存在（可能被合并/删除），跳过
                continue
            st = group_state[i]
            s = entry.get("state", {})
            # 只恢复当前仍存在的 book id，避免脏数据污染
            live_ids = {b.get('id') for b in groups[i].get('books', [])}
            st['selected_ids'] = set(
                bid for bid in s.get('selected_ids', []) if bid in live_ids
            )
            st['pending_delete_ids'] = set(
                bid for bid in s.get('pending_delete_ids', []) if bid in live_ids
            )
            st['merged_title'] = s.get('merged_title', groups[i].get('base_title', ''))
            st['skipped'] = bool(s.get('skipped', False))
            st['auto_sorted'] = bool(s.get('auto_sorted', False))
            st['processed'] = bool(s.get('processed', False))
            restored += 1
        except Exception as e:
            logger.debug(f"恢复暂存分组失败: {e}")

    return restored
