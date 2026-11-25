"""
接口路由处理：书库 / 书籍网站 / 爬取管理 的 分页+搜索 CRUD，
以及 补缺 / 合并 / 批量操作 / 健康检查。

约定：
- 列表/详情 GET；集合级 POST 创建；实例级 PUT 更新、DELETE 删除。
- 每个处理器返回 dict（响应 200）；若已自行发送错误响应则返回 None。
We 
"""

import json
import os
from urllib.parse import unquote
from typing import Any, Dict, List, Optional

from . import db
from .http_utils import send_error, get_str, parse_pagination
from src.utils.book_identity import book_id_for_path, book_key_for_path, resolve_path_by_book_key


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def _coerce_pk(collection: str, raw: str) -> Any:
    spec = db.COLLECTIONS[collection]
    if spec["pk_type"] == "int":
        try:
            return int(raw)
        except (ValueError, TypeError):
            return raw
    return raw


def _parse_meta(raw) -> Dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _with_public_ids(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """为书籍记录附加公开标识 book_key，以及供离线缓存兼容的 book_id。"""
    for item in items:
        path = item.get("path") or ""
        if not path:
            continue
        item["book_key"] = book_key_for_path(str(path))
        item["book_id"] = book_id_for_path(str(path))
    return items


# 浏览器书库只拿这些字段；尤其不能把物理路径 path 下发给浏览器。
_PORTAL_BOOK_FIELDS = (
    "book_key", "book_id", "title", "novel_title", "name", "author",
    "format", "status", "pinyin", "tags", "categories", "add_date", "file_size",
)


def _portal_book(item: Dict[str, Any]) -> Dict[str, Any]:
    return {field: item[field] for field in _PORTAL_BOOK_FIELDS if field in item}


# ---------------------------------------------------------------------------
# 健康检查：检测各接口可用情况
# ---------------------------------------------------------------------------
def route_health() -> Dict[str, Any]:
    interfaces: Dict[str, Any] = {}
    for c in ["books", "websites", "crawls"]:
        try:
            n = db.count_all(c)
            interfaces[c] = {"available": True, "count": n}
        except Exception as e:  # noqa: BLE001
            interfaces[c] = {"available": False, "error": str(e)}
    interfaces["fill_missing"] = {"available": True, "description": "分析书籍缺失章节"}
    interfaces["merge"] = {"available": True, "description": "合并多本书籍章节"}
    interfaces["batch"] = {"available": True, "description": "批量操作"}
    return {
        "success": True,
        "status": "ok",
        "server": "newreader-api",
        "version": "1.0",
        "interfaces": interfaces,
    }


# ---------------------------------------------------------------------------
# 通用集合处理
# ---------------------------------------------------------------------------
def _enrich_crawls_with_sites(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """为爬取记录补全所属书籍网站的名称与链接（site_id -> novel_sites）。"""
    if not items:
        return items
    site_ids = sorted({it.get("site_id") for it in items if it.get("site_id") is not None})
    site_map = {}
    if site_ids:
        conn = db.get_conn()
        try:
            placeholders = ",".join("?" * len(site_ids))
            rows = conn.execute(
                "SELECT id, name, url FROM novel_sites WHERE id IN (%s)" % placeholders, site_ids
            ).fetchall()
        finally:
            conn.close()
        site_map = {r["id"]: {"site_name": r["name"] or "", "site_url": r["url"] or ""} for r in rows}
    for it in items:
        sid = it.get("site_id")
        if sid in site_map:
            it["site_name"] = site_map[sid]["site_name"]
            it["site_url"] = site_map[sid]["site_url"]
        # 爬取记录也带公开标识，离线版打开书籍时无需下发真实路径
        book_path = it.get("file_path") or it.get("path") or ""
        if book_path:
            it["book_key"] = book_key_for_path(str(book_path))
    return items


# 每个集合允许排序的列（白名单，避免 SQL 注入）
ALLOWED_SORT: Dict[str, List[str]] = {
    "books": ["title", "author", "add_date", "file_size", "pinyin", "format"],
    "crawls": ["crawl_time", "last_update_time", "novel_title", "novel_id", "status", "chapter_count", "id"],
    "websites": ["id", "name", "url", "created_at", "rating"],
}
# 每个集合允许的等值筛选字段（白名单）
ALLOWED_FILTER: Dict[str, List[str]] = {
    "books": ["format", "author", "tags"],
    "crawls": ["status", "book_type", "site_id"],
    "websites": ["parser", "tags", "selectable_enabled", "one_click_crawl_enabled", "format_enabled"],
}


def _build_filters(collection: str, query: Dict[str, List[str]]) -> tuple:
    """根据白名单构造等值筛选条件。"""
    if collection not in ALLOWED_FILTER:
        return None, []
    clauses = []
    params = []
    for f in ALLOWED_FILTER[collection]:
        v = get_str(query, f)
        if v:
            clauses.append(f"{f} = ?")
            params.append(v)
    if not clauses:
        return None, []
    return " AND ".join(clauses), params


def _flag(query: Dict[str, List[str]], name: str) -> bool:
    return get_str(query, name).lower() in ("1", "true", "yes", "on")


def _build_library_filter_conditions(query: Dict[str, List[str]]) -> tuple:
    """把书库高级筛选（有/无、大小、入库时间）转成 SQL 条件。"""
    from src.core.library_filter import UNKNOWN_AUTHORS

    clauses: List[str] = []
    params: List[Any] = []

    unknown = sorted({str(a).lower() for a in UNKNOWN_AUTHORS if str(a)})
    placeholders = ",".join("?" for _ in unknown) or "''"
    if _flag(query, "no_author"):
        clauses.append(f"LOWER(COALESCE(author, '')) IN ({placeholders})")
        params.extend(unknown)
    if _flag(query, "has_author"):
        clauses.append(f"LOWER(COALESCE(author, '')) NOT IN ({placeholders})")
        params.extend(unknown)

    if _flag(query, "no_tags"):
        clauses.append("COALESCE(tags, '') = ''")
    if _flag(query, "has_tags"):
        clauses.append("COALESCE(tags, '') != ''")
    if _flag(query, "no_pinyin"):
        clauses.append("COALESCE(pinyin, '') = ''")
    if _flag(query, "has_pinyin"):
        clauses.append("COALESCE(pinyin, '') != ''")
    if _flag(query, "no_file"):
        clauses.append("COALESCE(file_size, 0) = 0")
    if _flag(query, "file_exists"):
        clauses.append("COALESCE(file_size, 0) > 0")

    size_min = get_str(query, "size_min")
    size_max = get_str(query, "size_max")
    try:
        if size_min:
            clauses.append("COALESCE(file_size, 0) >= ?")
            params.append(float(size_min) * 1024 * 1024)
        if size_max:
            clauses.append("COALESCE(file_size, 0) <= ?")
            params.append(float(size_max) * 1024 * 1024)
    except ValueError:
        pass

    added_after = get_str(query, "added_after")
    added_before = get_str(query, "added_before")
    if added_after:
        clauses.append("add_date >= ?")
        params.append(added_after + "T00:00:00")
    if added_before:
        clauses.append("substr(add_date, 1, 10) <= ?")
        params.append(added_before)

    if not clauses:
        return None, []
    return " AND ".join(clauses), params


def _build_category_filter(query: Dict[str, List[str]]) -> tuple:
    """构造多分类筛选（OR：命中任一分类即可，可含「无分类」哨兵）。"""
    from src.core.book_categories import NO_CATEGORY
    from src.utils.string_utils import normalize_match_text

    values: List[str] = []
    for raw in query.get("categories", []) or []:
        for part in str(raw).split(","):
            name = part.strip()
            if name and name not in values:
                values.append(name)
    if not values:
        return None, []

    want_no_category = NO_CATEGORY in values
    values = [name for name in values if name != NO_CATEGORY]

    clauses: List[str] = []
    params: List[str] = []
    if want_no_category:
        clauses.append("(categories IS NULL OR categories = '')")
    for name in values:
        escaped = normalize_match_text(name)
        escaped = escaped.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        clauses.append("(',' || COALESCE(categories, '') || ',') LIKE ? ESCAPE '\\'")
        params.append(f"%,{escaped},%")
    return "(" + " OR ".join(clauses) + ")", params


def _build_order_by(collection: str, query: Dict[str, List[str]]) -> Optional[str]:
    sort = get_str(query, "sort")
    if sort and sort in ALLOWED_SORT.get(collection, []):
        order = get_str(query, "order")
        if order not in ("asc", "desc"):
            order = "desc"
        return f"{sort} {order}"
    return None


def route_distinct(collection: str, query: Dict[str, List[str]]) -> Dict[str, Any]:
    field = get_str(query, "field")
    allowed = ALLOWED_FILTER.get(collection, []) + ["author", "format", "status", "book_type", "site_id", "parser", "tags", "categories"]
    if field not in allowed:
        return {"success": False, "error": "不允许的字段: %s" % field}
    values = db.distinct(collection, field)
    if field == "categories":
        split_values: List[str] = []
        for raw in values:
            for name in str(raw or "").split(","):
                name = name.strip()
                if name and name not in split_values:
                    split_values.append(name)
        values = split_values
        from src.core.book_categories import NO_CATEGORY
        if NO_CATEGORY not in values:
            values.append(NO_CATEGORY)
    return {"success": True, "field": field, "values": values}


def route_list(collection: str, query: Dict[str, List[str]]) -> Dict[str, Any]:
    q = get_str(query, "q")
    page, page_size, offset, _ = parse_pagination(query)
    extra_where, extra_params = _build_filters(collection, query)
    if collection == "books":
        category_where, category_params = _build_category_filter(query)
        library_where, library_params = _build_library_filter_conditions(query)
        clauses = [c for c in (extra_where, category_where, library_where) if c]
        extra_where = " AND ".join(f"({c})" for c in clauses) if clauses else None
        extra_params = (
            list(extra_params or []) + list(category_params or []) + list(library_params or [])
        )
    order_by = _build_order_by(collection, query)
    items, total = db.query_paginated(
        collection, q, page, page_size, offset,
        extra_where=extra_where, extra_params=extra_params, order_by=order_by,
    )
    if collection == "crawls":
        items = _enrich_crawls_with_sites(items)
    if collection == "books":
        items = _with_public_ids(items)
    return {
        "success": True,
        "collection": collection,
        "page": page,
        "page_size": page_size,
        "total": total,
        "count": len(items),
        "items": items,
    }


def route_book_index() -> Dict[str, Any]:
    """全量精简书单（不分页）：浏览器阅读器用它做离线书库与离线搜索。

    主列表走 :func:`route_list` 的服务端分页；这里只提供轻量索引，
    不含 metadata/章节正文，避免为离线缓存反复翻页请求。
    """
    items = _with_public_ids(db.list_book_index())
    return {"success": True, "collection": "books", "items": items, "total": len(items)}


def route_portal_book_list(query: Dict[str, List[str]]) -> Dict[str, Any]:
    """浏览器书库分页列表：只返回公开字段，彻底不下发真实路径。"""
    result = route_list("books", query)
    result["items"] = [_portal_book(item) for item in result["items"] if item.get("book_key")]
    return result


def route_portal_book_index() -> Dict[str, Any]:
    """浏览器离线书单：只返回公开字段，彻底不下发真实路径。"""
    result = route_book_index()
    result["items"] = [_portal_book(item) for item in result["items"] if item.get("book_key")]
    result["total"] = len(result["items"])
    return result


def route_get(collection: str, pk: Any) -> Optional[Dict[str, Any]]:
    item = db.get_one(collection, pk)
    if item is None:
        return None
    if collection == "books":
        item = _with_public_ids([item])[0]
    return {"success": True, "item": item}


def route_create(collection: str, body: Dict[str, Any], handler) -> Optional[Dict[str, Any]]:
    if collection == "books":
        return _create_book(body, handler)
    if collection == "websites":
        return _create_website(body, handler)
    # crawls：直接插入一条爬取记录
    row = {k: v for k, v in body.items() if k not in ("id",)}
    now = _now()
    row.setdefault("crawl_time", now)
    row.setdefault("first_crawl_time", now)
    row.setdefault("last_update_time", now)
    if "book_type" not in row:
        row["book_type"] = "小说"
    if "status" not in row:
        row["status"] = "完成"
    try:
        new_id = db.insert_row("crawls", row)
        return {"success": True, "existed": False, "id": new_id, "item": db.get_one("crawls", new_id)}
    except Exception as e:  # noqa: BLE001
        send_error(handler, 400, "创建爬取记录失败: %s" % str(e))
        return None


def _create_book(body: Dict[str, Any], handler) -> Optional[Dict[str, Any]]:
    path = (body.get("path") or "").strip()
    if not path:
        send_error(handler, 400, "book path 不能为空")
        return None
    existing = db.get_one("books", path)
    if existing:
        # 选择性入库：已存在则不重复写入，明确提示「本书已存在」
        return {"success": True, "existed": True, "message": "本书已存在", "item": existing}
    raw_meta = body.get("metadata")
    if isinstance(raw_meta, str):
        meta_str = raw_meta
    else:
        meta_str = json.dumps(raw_meta or {}, ensure_ascii=False)
    # 书名与拼音：优先使用前端传入，未传则由标题转换拼音（用于首字母/拼音排序）
    title = body.get("title") or os.path.basename(path)
    pinyin = body.get("pinyin", "") or ""
    if not pinyin and title:
        try:
            from src.core.database_manager import convert_to_pinyin
            pinyin = convert_to_pinyin(title)
        except Exception:
            pinyin = ""
    tags = body.get("tags", "") or ""
    row = {
        "path": path,
        "title": title,
        "pinyin": pinyin,
        "author": body.get("author", "未知"),
        "format": body.get("format") or (os.path.splitext(path)[1].lstrip(".").lower() or "txt"),
        "add_date": body.get("add_date") or _now(),
        "tags": tags,
        "file_size": int(body.get("file_size", 0) or 0),
        "metadata": meta_str,
    }
    # API 直接建书同样要做分类，并写入预归一化检索文本
    from src.core.database_manager import DatabaseManager
    try:
        from src.core.book_categories import classify_book_file
        detected = classify_book_file(path, title=title, tags=tags)
        categories = ",".join(detected)
        row["categories"] = categories
        row["search_text"] = DatabaseManager._build_search_text(
            title, row["author"], pinyin, tags, categories
        )
    except Exception:
        row["categories"] = ""
        row["search_text"] = DatabaseManager._build_search_text(
            title, row["author"], pinyin, tags, ""
        )
    try:
        db.insert_row("books", row)
    except Exception as e:  # noqa: BLE001
        send_error(handler, 400, "创建书籍失败: %s" % str(e))
        return None
    return {"success": True, "existed": False, "item": db.get_one("books", path)}


def _create_website(body: Dict[str, Any], handler) -> Optional[Dict[str, Any]]:
    name = (body.get("name") or "").strip()
    if not name:
        send_error(handler, 400, "website name 不能为空")
        return None
    # 按唯一名去重
    conn = db.get_conn()
    try:
        row = conn.execute("SELECT * FROM novel_sites WHERE name = ?", (name,)).fetchone()
    finally:
        conn.close()
    if row:
        return {"success": True, "existed": True, "item": dict(row)}
    now = _now()
    from src.utils.crawl_headers import normalize_mode
    data = {
        "name": name,
        "crawl_header_mode": normalize_mode(body.get("crawl_header_mode")),
        "url": body.get("url", ""),
        "storage_folder": body.get("storage_folder", ""),
        "proxy_enabled": int(bool(body.get("proxy_enabled", 0))),
        "selectable_enabled": int(body.get("selectable_enabled", 1)),
        "one_click_crawl_enabled": int(bool(body.get("one_click_crawl_enabled", body.get("daily_crawl_enabled", 0)))),
        "format_enabled": int(bool(body.get("format_enabled", 1))),
        "parser": body.get("parser", ""),
        "tags": body.get("tags", "") or "",
        "rating": int(body.get("rating", 2) or 2),
        "created_at": body.get("created_at", now),
        "updated_at": body.get("updated_at", now),
        "book_id_example": body.get("book_id_example", "") or "",
        "search_url": body.get("search_url", "") or "",
        "status": body.get("status", "正常"),
    }
    try:
        new_id = db.insert_row("websites", data)
        return {"success": True, "existed": False, "id": new_id, "item": db.get_one("websites", new_id)}
    except Exception as e:  # noqa: BLE001
        send_error(handler, 400, "创建书籍网站失败: %s" % str(e))
        return None


def route_update(collection: str, pk: Any, body: Dict[str, Any], handler) -> Optional[Dict[str, Any]]:
    if not db.collection_exists(collection):
        send_error(handler, 404, "未知集合")
        return None
    if not db.exists_row(collection, pk):
        send_error(handler, 404, "记录不存在")
        return None
    ok = db.update_row(collection, pk, body)
    return {"success": True, "updated": ok, "item": db.get_one(collection, pk)}


def route_delete(collection: str, pk: Any, handler) -> Optional[Dict[str, Any]]:
    if not db.exists_row(collection, pk):
        send_error(handler, 404, "记录不存在")
        return None
    ok = db.delete_row(collection, pk)
    return {"success": True, "deleted": ok}


# ---------------------------------------------------------------------------
# 批量操作
# ---------------------------------------------------------------------------
def route_batch_collection(collection: str, body: Dict[str, Any], handler) -> Optional[Dict[str, Any]]:
    op = (body.get("op") or "").strip()
    ids = body.get("ids") or body.get("paths") or []
    if not isinstance(ids, list):
        ids = [ids]
    if op == "delete":
        n = 0
        for raw in ids:
            if db.delete_row(collection, _coerce_pk(collection, str(raw))):
                n += 1
        return {"success": True, "op": "delete", "affected": n}
    if op == "update_tags":
        tags = body.get("tags", "")
        n = 0
        for raw in ids:
            if db.update_row(collection, _coerce_pk(collection, str(raw)), {"tags": tags}):
                n += 1
        return {"success": True, "op": "update_tags", "affected": n}
    send_error(handler, 400, "不支持的批量操作: %s" % op)
    return None


# ---------------------------------------------------------------------------
# 补缺：分析书籍缺失章节
# ---------------------------------------------------------------------------
def _detect_missing(chapters: List[Dict[str, Any]]) -> List[int]:
    if not chapters:
        return []
    indices = []
    for ch in chapters:
        idx = ch.get("index")
        if idx is None and "chapter_index" in ch:
            idx = ch["chapter_index"]
        if isinstance(idx, int):
            indices.append(idx)
    if not indices:
        return []
    lo, hi = min(indices), max(indices)
    present = set(indices)
    return [i for i in range(lo, hi + 1) if i not in present]


def route_fill_missing(body: Dict[str, Any], handler) -> Optional[Dict[str, Any]]:
    paths = body.get("book_paths")
    if not paths and body.get("book_path"):
        paths = [body["book_path"]]
    if not isinstance(paths, list) or not paths:
        send_error(handler, 400, "请提供 book_path 或 book_paths")
        return None
    results = []
    for p in paths:
        p = str(p)
        b = db.get_one("books", p)
        if not b:
            results.append({"book_path": p, "status": "not_found"})
            continue
        meta = _parse_meta(b.get("metadata"))
        chapters = meta.get("chapters") or []
        missing = _detect_missing(chapters)
        results.append({
            "book_path": p,
            "title": b.get("title"),
            "total_chapters": len(chapters),
            "missing": missing,
            "status": "ok" if missing else "complete",
        })
    _log_task("fill_missing", body, {"results": results})
    return {"success": True, "results": results}


# ---------------------------------------------------------------------------
# 合并：汇总多本书籍章节
# ---------------------------------------------------------------------------
def route_merge(body: Dict[str, Any], handler) -> Optional[Dict[str, Any]]:
    paths = body.get("book_paths") or []
    if not isinstance(paths, list) or not paths:
        send_error(handler, 400, "请提供 book_paths")
        return None
    sources = []
    total = 0
    for p in paths:
        p = str(p)
        b = db.get_one("books", p)
        if not b:
            continue
        meta = _parse_meta(b.get("metadata"))
        ch = meta.get("chapters") or []
        sources.append({"book_path": p, "title": b.get("title"), "chapter_count": len(ch)})
        total += len(ch)
    title = body.get("title") or (sources[0]["title"] if sources else "")
    result = {
        "title": title,
        "source_count": len(sources),
        "total_chapters": total,
        "sources": sources,
    }
    _log_task("merge", body, result)
    return {"success": True, **result}


# ---------------------------------------------------------------------------
# 打开书籍：经回调让服务端在浏览器中打开一本书用于阅读
# ---------------------------------------------------------------------------
def _book_path_for_key(book_key: str) -> str:
    """把公开 book key 反查为白名单路径，避免在客户端与网络上传递真实目录。"""
    return resolve_path_by_book_key(book_key)


def route_open_book(body: Dict[str, Any], open_cb) -> Dict[str, Any]:
    """通过上层注入的 open_cb(path) 打开书籍；优先使用公开 book 标识。"""
    if not open_cb:
        return {"success": False, "error": "服务端未启用打开书籍能力"}
    path = (body.get("path") or "").strip()
    if not path and body.get("book"):
        path = _book_path_for_key(body["book"])
    if not path and body.get("book_id"):
        path = str(body["book_id"]).strip()
    if not path:
        return {"success": False, "error": "缺少 book / path / book_id"}
    try:
        res = open_cb(path)
        if isinstance(res, tuple):
            ok = bool(res[0]) if len(res) > 0 else False
            msg = res[1] if len(res) > 1 else ""
        else:
            ok = bool(res)
            msg = ""
        return {"success": ok, "message": msg or ""}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 网页上传书籍：浏览器书库（网络/离线统一 UI）把文件直接 POST 到这里
# ---------------------------------------------------------------------------
def route_upload_book(handler) -> Dict[str, Any]:
    """接收原始文件体，保存到书库目录并登记；只返回公开字段，不回传真实路径。"""
    try:
        length = int(handler.headers.get("Content-Length", 0) or 0)
    except Exception:
        length = 0
    max_bytes = 100 * 1024 * 1024
    if length <= 0 or length > max_bytes:
        return {"success": False, "error": "文件大小无效或超过 100MB"}

    name = unquote(handler.headers.get("X-File-Name") or "").replace("\\", "/")
    name = os.path.basename(name).strip().lstrip(".")
    ext = os.path.splitext(name)[1].lower()
    allowed = {".txt", ".md", ".epub", ".pdf", ".mobi", ".azw", ".azw3"}
    if not name or ext not in allowed:
        return {"success": False, "error": "不支持的文件格式"}

    data = handler.rfile.read(length)
    if len(data) != length:
        return {"success": False, "error": "文件内容不完整"}

    try:
        from src.core.bookshelf import Bookshelf
        from datetime import datetime

        shelf = Bookshelf()
        os.makedirs(shelf.data_dir, exist_ok=True)
        target = os.path.join(shelf.data_dir, name)
        if os.path.exists(target):
            stem, suffix = os.path.splitext(name)
            name = f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
            target = os.path.join(shelf.data_dir, name)
        with open(target, "wb") as f:
            f.write(data)

        title = unquote(handler.headers.get("X-File-Title") or "").strip() or os.path.splitext(name)[0]
        book = shelf.add_book(target, title=title, tags="网页上传")
        if book is None:
            return {"success": False, "error": "书籍已存在或入库失败"}
        return {"success": True, "book": _portal_book(_with_public_ids([book.to_dict()])[0])}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 任务记录（补缺 / 合并 的操作留痕）
# ---------------------------------------------------------------------------
def _ensure_api_tasks() -> None:
    conn = db.get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                payload TEXT,
                result TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _log_task(kind: str, payload: Dict[str, Any], result: Dict[str, Any]) -> None:
    try:
        _ensure_api_tasks()
        conn = db.get_conn()
        try:
            conn.execute(
                "INSERT INTO api_tasks (kind, payload, result, created_at) VALUES (?, ?, ?, ?)",
                (kind, json.dumps(payload, ensure_ascii=False), json.dumps(result, ensure_ascii=False), _now()),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass
