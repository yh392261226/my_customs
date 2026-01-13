"""
通用缓存管理器：支持 LRU + LFU + TTL + 近似容量控制（以字节估算）
用于解析结果与分页渲染缓存，集中清理入口
"""

import time
import threading
from typing import Any, Optional, Tuple, Dict, Union

class CacheItem:
    __slots__ = ("value", "expires_at", "size", "access_count", "last_access_time")
    def __init__(self, value: Any, ttl_seconds: Optional[int] = None, size: int = 0):
        self.value = value
        self.expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
        self.size = size
        self.access_count = 1  # 访问次数，用于LFU算法
        self.last_access_time = time.time()  # 最后访问时间，用于LRU算法

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

class BaseCache:
    """
    基础缓存类，提供通用功能
    """
    def __init__(self, max_items: int = 1024, max_bytes: int = 64 * 1024 * 1024):
        self._lock = threading.RLock()
        self._store: Dict[Any, CacheItem] = {}
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

    def _shrink_if_needed(self) -> None:
        # 清掉过期
        expired_keys = [k for k, it in self._store.items() if it.is_expired()]
        for k in expired_keys:
            self._pop(k)
        # 数量限制
        while len(self._store) > self._max_items:
            self._evict_item()
        # 容量限制
        while self.total_bytes() > self._max_bytes and len(self._store) > 0:
            self._evict_item()

    def _pop(self, key: Any) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def total_bytes(self) -> int:
        return sum(it.size for it in self._store.values())

    def shrink_to_target(self, target_bytes: int) -> None:
        with self._lock:
            # 逐出直到容量低于目标
            while self.total_bytes() > target_bytes and len(self._store) > 0:
                self._evict_item()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                "item_count": len(self._store),
                "total_bytes": self.total_bytes(),
                "max_items": self._max_items,
                "max_bytes": self._max_bytes
            }

class LRUCache(BaseCache):
    """
    线程安全 LRU + TTL 缓存。
    - max_items: 项数量上限（保底）
    - max_bytes: 近似容量上限（字节），用于触发收缩
    """
    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item.is_expired():
                self._pop(key)
                return None
            # 更新访问时间和访问次数
            item.last_access_time = time.time()
            item.access_count += 1
            return item.value

    def set(self, key: Any, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            size = self._estimate_size(value)
            # 如果键已存在，更新访问次数
            if key in self._store:
                existing_item = self._store[key]
                existing_item.value = value
                existing_item.expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
                existing_item.size = size
                existing_item.access_count += 1
            else:
                self._store[key] = CacheItem(value, ttl_seconds, size)
            self._shrink_if_needed()

    def _evict_item(self) -> None:
        if not self._store:
            return
        # 取最久未使用
        oldest_key = min(self._store.items(), key=lambda kv: kv[1].last_access_time)[0]
        self._pop(oldest_key)

class LFUCache(BaseCache):
    """
    线程安全 LFU + TTL 缓存。
    - max_items: 项数量上限（保底）
    - max_bytes: 近似容量上限（字节），用于触发收缩
    """
    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item.is_expired():
                self._pop(key)
                return None
            # 更新访问时间和访问次数
            item.last_access_time = time.time()
            item.access_count += 1
            return item.value

    def set(self, key: Any, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            size = self._estimate_size(value)
            # 如果键已存在，更新访问次数
            if key in self._store:
                existing_item = self._store[key]
                existing_item.value = value
                existing_item.expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
                existing_item.size = size
                existing_item.access_count += 1
            else:
                self._store[key] = CacheItem(value, ttl_seconds, size)
            self._shrink_if_needed()

    def _evict_item(self) -> None:
        if not self._store:
            return
        # 取访问次数最少的，如果访问次数相同则取最久未使用的
        least_frequent_key = min(
            self._store.items(),
            key=lambda kv: (kv[1].access_count, kv[1].last_access_time)
        )[0]
        self._pop(least_frequent_key)

class AdaptiveCache(BaseCache):
    """
    自适应缓存：根据访问模式动态调整LRU/LFU策略
    - max_items: 项数量上限（保底）
    - max_bytes: 近似容量上限（字节），用于触发收缩
    - adaptation_window: 适应窗口大小（访问次数）
    """
    def __init__(self, max_items: int = 1024, max_bytes: int = 64 * 1024 * 1024, adaptation_window: int = 1000):
        super().__init__(max_items, max_bytes)
        self._access_count = 0
        self._adaptation_window = adaptation_window
        self._strategy = "lru"  # 默认使用LRU策略
        self._last_strategy_check = time.time()

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item.is_expired():
                self._pop(key)
                return None
            # 更新访问时间和访问次数
            item.last_access_time = time.time()
            item.access_count += 1
            self._access_count += 1
            return item.value

    def set(self, key: Any, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            size = self._estimate_size(value)
            # 如果键已存在，更新访问次数
            if key in self._store:
                existing_item = self._store[key]
                existing_item.value = value
                existing_item.expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
                existing_item.size = size
                existing_item.access_count += 1
            else:
                self._store[key] = CacheItem(value, ttl_seconds, size)
            self._access_count += 1
            self._shrink_if_needed()

    def _evict_item(self) -> None:
        if not self._store:
            return
        # 根据当前策略选择淘汰算法
        if self._strategy == "lru":
            # LRU: 取最久未使用的
            oldest_key = min(self._store.items(), key=lambda kv: kv[1].last_access_time)[0]
            self._pop(oldest_key)
        else:  # LFU
            # LFU: 取访问次数最少的，如果访问次数相同则取最久未使用的
            least_frequent_key = min(
                self._store.items(),
                key=lambda kv: (kv[1].access_count, kv[1].last_access_time)
            )[0]
            self._pop(least_frequent_key)

    def _should_adapt_strategy(self) -> bool:
        """判断是否需要调整策略"""
        current_time = time.time()
        # 每隔一段时间或达到一定访问次数后检查策略
        return (self._access_count % self._adaptation_window == 0 or
                current_time - self._last_strategy_check > 300)  # 5分钟

    def adapt_strategy(self) -> str:
        """根据访问模式自适应调整策略"""
        with self._lock:
            if not self._should_adapt_strategy():
                return self._strategy

            self._last_strategy_check = time.time()

            # 分析访问模式
            if len(self._store) < 10:  # 缓存项太少，使用默认策略
                return self._strategy

            # 计算访问频率分布
            access_counts = [item.access_count for item in self._store.values()]
            if not access_counts:
                return self._strategy

            avg_access = sum(access_counts) / len(access_counts)
            max_access = max(access_counts)

            # 如果访问频率差异很大，更适合LFU
            if max_access > avg_access * 2:
                self._strategy = "lfu"
            else:
                self._strategy = "lru"

            return self._strategy

# 全局缓存实例：解析缓存与分页缓存分离
parse_cache = AdaptiveCache(max_items=256, max_bytes=128 * 1024 * 1024)
paginate_cache = AdaptiveCache(max_items=512, max_bytes=256 * 1024 * 1024)

# 解析结果缓存专用实例，支持更细粒度的缓存控制
parsing_result_cache = AdaptiveCache(max_items=128, max_bytes=64 * 1024 * 1024)

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