"""
HTTP 工具：JSON 响应、CORS、请求体解析、分页与查询参数辅助。
"""

import json
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Tuple, Optional


def send_json(handler, status: int, obj: Any, cors: bool = True) -> None:
    """向客户端发送 JSON 响应。"""
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    if cors:
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-Book-ID, X-API-Key")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def send_error(handler, status: int, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    body: Dict[str, Any] = {"success": False, "error": message}
    if extra:
        body.update(extra)
    send_json(handler, status, body)


def read_json_body(handler) -> Tuple[bool, Any]:
    """读取并解析请求体为 JSON。返回 (ok, data)。"""
    try:
        length = int(handler.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return True, {}
        raw = handler.rfile.read(length)
        if not raw:
            return True, {}
        data = json.loads(raw.decode("utf-8"))
        return True, data
    except Exception as e:  # noqa: BLE001
        return False, {"error": "无效的 JSON 请求体: %s" % str(e)}


def parse_query(path: str) -> Dict[str, list]:
    """从 path 中解析查询参数。"""
    return parse_qs(urlparse(path).query)


def parse_pagination(query: Dict[str, list]) -> Tuple[int, int, int, int]:
    """
    解析分页参数。
    返回 (page, page_size, offset, limit)
    """
    try:
        page = max(1, int(query.get("page", ["1"])[0]))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = int(query.get("page_size", query.get("limit", ["20"]))[0])
    except (ValueError, TypeError):
        page_size = 20
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size
    return page, page_size, offset, page_size


def get_str(query: Dict[str, list], key: str, default: str = "") -> str:
    val = query.get(key, [default])[0]
    return (val or default).strip()
