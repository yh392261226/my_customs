"""
API 服务器：基于标准库 http.server 的线程化 JSON 接口服务。

路由：
  GET  /api/health
  GET  /api/{books|websites|crawls}?page=&page_size=&q=
  GET  /api/{books|websites|crawls}/{pk}
  POST /api/{books|websites|crawls}
  PUT  /api/{books|websites|crawls}/{pk}
  DELETE /api/{books|websites|crawls}/{pk}
  POST /api/{books|websites|crawls}/batch
  POST /api/fill-missing
  POST /api/merge
  POST /api/batch
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from . import routes
from .http_utils import send_json, send_error, read_json_body, parse_query

COLLECTIONS = ("books", "websites", "crawls")

# 服务端密钥：由 start_api_server 注入；为空表示开放模式（不校验）
_API_SECRET = ""
# 打开书籍回调：由上层（管理器）注入，签名为 open_cb(path) -> (success, message) 或 bool
_OPEN_BOOK_CB = None


def set_open_book_callback(cb) -> None:
    """注册“打开书籍”回调，使浏览器端可请求服务端打开某本书用于阅读。"""
    global _OPEN_BOOK_CB
    _OPEN_BOOK_CB = cb


class ApiHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # 禁用访问日志
        pass

    def _raw_path(self) -> str:
        """从原始请求行解析路径，避免 %2F 等被 HTTP 服务器提前解码为 / 而破坏路由。"""
        line = self.raw_requestline
        if isinstance(line, bytes):
            line = line.decode("iso-8859-1")
        parts = line.split()
        if len(parts) >= 2:
            return parts[1]
        return self.path

    def _check_auth(self) -> bool:
        """校验请求密钥。服务端未配置密钥时放行（开放模式）。"""
        secret = _API_SECRET
        if not secret:
            return True
        provided = self.headers.get("X-API-Key") or ""
        if not provided:
            auth = self.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                provided = auth[len("Bearer "):]
        if not provided:
            q = parse_query(self._raw_path())
            vals = q.get("key")
            provided = (vals[0] if vals else "") or ""
        return provided == secret

    def _dispatch(self):
        if not self._check_auth():
            send_error(self, 401, "拒绝访问：密钥无效或未提供")
            return
        method = self.command
        rp = self._raw_path()
        raw_path = rp.split("?")[0]
        query = parse_query(rp)

        body = {}
        if method in ("POST", "PUT"):
            ok, data = read_json_body(self)
            if not ok:
                send_error(self, 400, data.get("error", "无效的请求体"))
                return
            body = data

        if raw_path == "/api/health":
            if method == "GET":
                send_json(self, 200, routes.route_health())
            else:
                send_error(self, 405, "Method Not Allowed")
            return

        parts = [p for p in raw_path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "api":
            seg = parts[1]

            if seg in COLLECTIONS:
                collection = seg
                if len(parts) == 2:
                    if method == "GET":
                        send_json(self, 200, routes.route_list(collection, query))
                    elif method == "POST":
                        res = routes.route_create(collection, body, self)
                        if res is not None:
                            send_json(self, 200, res)
                    else:
                        send_error(self, 405, "Method Not Allowed")
                    return

                if len(parts) == 3 and parts[2] == "batch":
                    if method == "POST":
                        res = routes.route_batch_collection(collection, body, self)
                        if res is not None:
                            send_json(self, 200, res)
                    else:
                        send_error(self, 405, "Method Not Allowed")
                    return

                if len(parts) == 3:
                    pk = routes._coerce_pk(collection, unquote(parts[2]))
                    if method == "GET":
                        item = routes.route_get(collection, pk)
                        if item is None:
                            send_error(self, 404, "记录不存在")
                        else:
                            send_json(self, 200, item)
                    elif method == "PUT":
                        res = routes.route_update(collection, pk, body, self)
                        if res is not None:
                            send_json(self, 200, res)
                    elif method == "DELETE":
                        res = routes.route_delete(collection, pk, self)
                        if res is not None:
                            send_json(self, 200, res)
                    else:
                        send_error(self, 405, "Method Not Allowed")
                    return

            if seg == "fill-missing" and len(parts) == 2:
                if method == "POST":
                    res = routes.route_fill_missing(body, self)
                    if res is not None:
                        send_json(self, 200, res)
                else:
                    send_error(self, 405, "Method Not Allowed")
                return

            if seg == "merge" and len(parts) == 2:
                if method == "POST":
                    res = routes.route_merge(body, self)
                    if res is not None:
                        send_json(self, 200, res)
                else:
                    send_error(self, 405, "Method Not Allowed")
                return

            if seg == "batch" and len(parts) == 2:
                if method == "POST":
                    coll = (body.get("collection") or "")
                    if coll not in COLLECTIONS:
                        send_error(self, 400, "无效的 collection")
                        return
                    res = routes.route_batch_collection(coll, body, self)
                    if res is not None:
                        send_json(self, 200, res)
                else:
                    send_error(self, 405, "Method Not Allowed")
                return

            if seg == "open_book" and len(parts) == 2:
                if method == "POST":
                    res = routes.route_open_book(body, _OPEN_BOOK_CB)
                    send_json(self, 200, res)
                else:
                    send_error(self, 405, "Method Not Allowed")
                return

        send_error(self, 404, "Not Found")

    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()

    def do_PUT(self):
        self._dispatch()

    def do_DELETE(self):
        self._dispatch()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Book-ID, X-API-Key")
        self.end_headers()


def start_api_server(host: str = "localhost", port: int = 54322, secret: str = None):
    """启动 API 服务器，返回 (server, thread)。secret 非空时要求客户端密钥一致。"""
    global _API_SECRET
    _API_SECRET = secret or ""
    server = ThreadingHTTPServer((host, port), ApiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def get_api_base_url() -> str:
    """根据配置计算浏览器阅读器应连接的后端接口地址。"""
    try:
        from src.config.config_manager import ConfigManager
        cfg = ConfigManager.get_instance().get_config()
        bc = cfg.get("browser_server", {})
        base = (bc.get("api_base_url") or "").strip()
        if base:
            return base.rstrip("/")
        host = bc.get("host", "localhost")
        port = int(bc.get("api_port", 54322))
        return f"http://{host}:{port}"
    except Exception:  # noqa: BLE001
        return "http://localhost:54322"
