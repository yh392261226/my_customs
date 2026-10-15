"""
数据访问层：直接读取 newreader 的 SQLite 数据库（与 DatabaseManager 共用同一文件）。

为保证对表结构变动的兼容性，列表/详情统一使用 SELECT *，
由调用方按需取用字段。
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from src.core.database_manager import DatabaseManager

_dm_instance = None


def _get_dm() -> "DatabaseManager":
    global _dm_instance
    if _dm_instance is None:
        _dm_instance = DatabaseManager()
    return _dm_instance


def get_db_path() -> str:
    return _get_dm().get_db_path()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    return conn


def rows_to_dicts(rows) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


# 集合 -> 表/主键/可搜索列 的映射
COLLECTIONS: Dict[str, Dict[str, Any]] = {
    "books": {
        "table": "books",
        "pk": "path",
        "pk_type": "text",
        "search": ["title", "author", "pinyin", "tags", "format", "metadata"],
        "order_by": "add_date DESC",
    },
    "websites": {
        "table": "novel_sites",
        "pk": "id",
        "pk_type": "int",
        "search": ["name", "url", "tags", "parser", "status", "pinyin"],
        "order_by": "id DESC",
    },
    "crawls": {
        "table": "crawl_history",
        "pk": "id",
        "pk_type": "int",
        "search": ["novel_title", "novel_id", "status", "book_type", "error_message", "pinyin"],
        "order_by": "id DESC",
    },
}


def collection_exists(name: str) -> bool:
    return name in COLLECTIONS


_COLUMN_CACHE: Dict[str, List[str]] = {}


def get_columns(table: str) -> List[str]:
    """返回表真实存在的列名（带缓存），用于过滤不存在的搜索/写入列。"""
    if table in _COLUMN_CACHE:
        return _COLUMN_CACHE[table]
    conn = get_conn()
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        cols = [r["name"] for r in rows]
    finally:
        conn.close()
    _COLUMN_CACHE[table] = cols
    return cols


def query_paginated(collection: str, q: str, page: int, page_size: int, offset: int,
                    extra_where: Optional[str] = None,
                    extra_params: Optional[list] = None) -> Tuple[List[Dict[str, Any]], int]:
    spec = COLLECTIONS[collection]
    table = spec["table"]
    search_cols = spec["search"]
    order_by = spec["order_by"]

    params: List[Any] = []
    where_clauses: List[str] = []
    actual_cols = set(get_columns(table))
    search_cols = [c for c in search_cols if c in actual_cols]
    if q:
        for col in search_cols:
            where_clauses.append(f"{col} LIKE ?")
            params.append("%" + q + "%")
    if extra_where:
        where_clauses.append("(" + extra_where + ")")
        if extra_params:
            params.extend(extra_params)

    where_sql = ("WHERE " + " OR ".join(where_clauses)) if where_clauses else ""

    conn = get_conn()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM {table} {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM {table} {where_sql} ORDER BY {order_by} LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        return rows_to_dicts(rows), total
    finally:
        conn.close()


def get_one(collection: str, pk_value: Any) -> Optional[Dict[str, Any]]:
    spec = COLLECTIONS[collection]
    table = spec["table"]
    pk = spec["pk"]
    conn = get_conn()
    try:
        row = conn.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (pk_value,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def count_all(collection: str) -> int:
    spec = COLLECTIONS[collection]
    conn = get_conn()
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {spec['table']}").fetchone()[0]
    finally:
        conn.close()


def insert_row(collection: str, data: Dict[str, Any]) -> Any:
    """插入一行，返回生成的主键（自增 id 由数据库生成）。"""
    spec = COLLECTIONS[collection]
    table = spec["table"]
    pk = spec["pk"]

    actual_cols = set(get_columns(table))
    cols = [k for k in data.keys() if k in actual_cols]
    if not cols:
        raise ValueError("无可写入字段")
    placeholders = ", ".join("?" for _ in cols)
    col_sql = ", ".join(cols)
    values = [data[c] for c in cols]

    conn = get_conn()
    try:
        cur = conn.execute(f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})", values)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_row(collection: str, pk_value: Any, data: Dict[str, Any]) -> bool:
    spec = COLLECTIONS[collection]
    table = spec["table"]
    pk = spec["pk"]

    actual_cols = set(get_columns(table))
    cols = [k for k in data.keys() if k in actual_cols and k != pk and data.get(k) is not None]
    if not cols:
        return True
    set_sql = ", ".join(f"{c} = ?" for c in cols)
    values = [data[c] for c in cols] + [pk_value]

    conn = get_conn()
    try:
        cur = conn.execute(f"UPDATE {table} SET {set_sql} WHERE {pk} = ?", values)
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_row(collection: str, pk_value: Any) -> bool:
    spec = COLLECTIONS[collection]
    table = spec["table"]
    pk = spec["pk"]
    conn = get_conn()
    try:
        cur = conn.execute(f"DELETE FROM {table} WHERE {pk} = ?", (pk_value,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def exists_row(collection: str, pk_value: Any) -> bool:
    return get_one(collection, pk_value) is not None
