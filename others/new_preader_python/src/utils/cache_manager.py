"""
通用缓存管理器：支持 LRU + TTL + 近似容量控制（以字节估算）
用于解析结果与分页渲染缓存，集中清理入口
"""

import time
import threading
from typing import Any, Optional, Tuple, Callable, Dict

class CacheItem:
    __slots__ = ("value", "expires_at", "size")
    def __init__(self, value: Any, ttl_seconds: Optional[int] = None, size: int = 0):
        self.value = value
        self.expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
        self.size = size

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

class LRUCache:
    """
    简化的线程安全 LRU + TTL 缓存。
    - max_items: 项数量上限（保底）
    - max_bytes: 近似容量上限（字节），用于触发收缩
    """
    def __init__(self, max_items: int = 1024, max_bytes: int = 64 * 1024 * 1024):
        self._lock = threading.RLock()
        self._store: Dict[Any, CacheItem] = {}
        self._order: Dict[Any, float] = {}
        self._max_items = max_items
        self._max_bytes = max_bytes

    def _estimate_size(self, value: Any) -> int:
        # 近似估算：字符串按长度，列表按累加，字典按键值长度；其余给一个常数
        try:
            if isinstance(value, str):
                return len(value.encode("utf-8", errors="ignore"))
            if isinstance(value, (bytes, bytearray)):
                return len(value)
            if isinstance(value, list):
                return sum(self._estimate_size(v) for v in value)
            if isinstance(value, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in value.items())
        except Exception:
            pass
        return 1024  # 默认

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item.is_expired():
                self._pop(key)
                return None
            self._order[key] = time.time()
            return item.value

    def set(self, key: Any, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            size = self._estimate_size(value)
            self._store[key] = CacheItem(value, ttl_seconds, size)
            self._order[key] = time.time()
            self._shrink_if_needed()

    def _shrink_if_needed(self) -> None:
        # 清掉过期
        expired_keys = [k for k, it in self._store.items() if it.is_expired()]
        for k in expired_keys:
            self._pop(k)
        # 数量限制
        while len(self._store) > self._max_items:
            self._evict_oldest()
        # 容量限制
        while self.total_bytes() > self._max_bytes and len(self._store) > 0:
            self._evict_oldest()

    def _evict_oldest(self) -> None:
        if not self._order:
            return
        # 取最久未使用
        oldest_key = min(self._order.items(), key=lambda kv: kv[1])[0]
        self._pop(oldest_key)

    def _pop(self, key: Any) -> None:
        self._store.pop(key, None)
        self._order.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._order.clear()

    def total_bytes(self) -> int:
        return sum(it.size for it in self._store.values())

    def shrink_to_target(self, target_bytes: int) -> None:
        with self._lock:
            # 逐出直到容量低于目标
            while self.total_bytes() > target_bytes and len(self._store) > 0:
                self._evict_oldest()

# 全局缓存实例：解析缓存与分页缓存分离
parse_cache = LRUCache(max_items=256, max_bytes=128 * 1024 * 1024)
paginate_cache = LRUCache(max_items=512, max_bytes=256 * 1024 * 1024)

def make_key(*parts: Any) -> Tuple[Any, ...]:
    # 将复杂对象转为可哈希的元组键
    normalized = []
    for p in parts:
        try:
            if isinstance(p, dict):
                normalized.append(tuple(sorted(p.items())))
            elif isinstance(p, list):
                normalized.append(tuple(p))
            else:
                normalized.append(p)
        except Exception:
            normalized.append(str(p))
    return tuple(normalized)