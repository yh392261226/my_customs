"""
浏览器阅读器服务器管理器
负责在应用启动时自动启动后端服务器，并管理其生命周期
"""

import gzip
import threading
import time
import re
import uuid
from html.parser import HTMLParser
from typing import Optional, Dict, Any, Callable, Tuple
from urllib.parse import quote
from src.utils.logger import get_logger
from src.utils.browser_reader import BrowserReader
from src.utils.book_identity import (
    book_key_for_path,
    is_known_book_path as _identity_is_known_book_path,
    resolve_path_by_book_key,
)

logger = get_logger(__name__)

# 当前进程（=当前阅读器实例）的唯一标识。
# 健康检查会带上它，浏览器阅读页据此确认"对面是不是我这个实例的服务"，
# 避免多实例并存时页面误连到第一个启动的实例。
PROCESS_INSTANCE_ID = uuid.uuid4().hex


def get_process_instance_id() -> str:
    """返回当前进程的实例标识（同一进程内所有服务共用）"""
    return PROCESS_INSTANCE_ID


def _map_translate_lang(code: str) -> str:
    """将常见语言代码映射到 MyMemory 使用的 RFC3066 形式"""
    code = (code or '').lower()
    if code in ('zh', 'zh-cn', 'zh_chs', 'zh-chs', 'zh-cht', 'zh_cht'):
        return 'zh-CN'
    if code in ('zh-tw', 'zh_tw', 'zh-hant', 'zh_hant'):
        return 'zh-TW'
    return code or 'en'


def _verify_request(headers: Any, query: Any, secret: str) -> bool:
    """
    校验请求密钥。与 api/server.py 保持一致：
      - secret 为空时放行（开放模式）
      - 否则要求来源提供的密钥与 secret 完全一致
    密钥可接受来源（优先级从高到低）：
      1. 请求头 X-API-Key
      2. Authorization: Bearer <key>
      3. 查询参数 ?key=<key>（用于 sendBeacon 等无法设置自定义请求头的场景）
    """
    secret = str(secret or '').strip()
    if not secret:
        # 开放模式：忽略浏览器书签里残留的 ?key= 和 localStorage 里的旧密钥
        return True
    provided = (headers.get('X-API-Key') or '').strip()
    if not provided:
        auth = headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            provided = auth[len('Bearer '):].strip()
    if not provided:
        vals = query.get('key')
        provided = str((vals[0] if vals else '') or '').strip()
    return provided == secret


def get_runtime_secret() -> str:
    """返回当前生效的接口密钥；空字符串表示开放模式（不校验密钥）。

    每次请求都重新读取配置，因此设置中心把密钥清空或改掉之后，不用重启
    「浏览器阅读器服务」也会立即生效；手机书签里的旧 ``?key=`` 在开放模式下
    会被 ``_verify_request`` / ``check_auth`` 直接忽略。
    """
    try:
        from src.config.config_manager import ConfigManager
        cfg = ConfigManager.get_instance().get_config() or {}
        return str((cfg.get('browser_server') or {}).get('api_secret', '') or '').strip()
    except Exception as e:
        logger.debug(f"读取接口密钥失败，回退到服务启动时的值: {e}")
        try:
            return str(BrowserReaderServerManager.get_instance()._secret or '').strip()
        except Exception:
            return ''


def get_book_reader_url(book_key: str) -> Optional[str]:
    """供终端书库/爬取管理调用：生成 /reader?book=... 的浏览器阅读地址。"""
    try:
        return BrowserReaderServerManager.get_instance().get_book_reader_url(book_key)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# 局域网 Web 页面支持
# --------------------------------------------------------------------------- #
# 原先统一服务只提供 JSON 接口，阅读器页面是 file:// 单文件，
# 因此局域网设备拿不到页面。这里让同一个服务额外提供书库入口页与阅读页，
# 页面与 file:// 版本共用同一份 HTML 生成逻辑与前端资源。
_WEB_PAGE_PATHS = ("/", "/reader", "/sw.js", "/manifest.webmanifest")
_reader_page_cache: Dict[str, str] = {}
_reader_page_gzip_cache: Dict[str, bytes] = {}
_reader_page_cache_lock = threading.Lock()
# HTTP /reader 页面复用同一套浏览器编辑器；按真实文件路径缓存，避免重复启动服务。
_editor_servers: Dict[str, Tuple[str, Any]] = {}
_editor_servers_lock = threading.Lock()
# 每个编辑器服务独占一个线程且 idle_timeout=0（永不自动关闭），必须限制数量，
# 否则每打开一本书就永久新增一个服务线程，长时间运行后越来越卡。
_EDITOR_SERVERS_MAX = 8
_READER_PAGE_CACHE_MAX = 6
# 阅读页内嵌了整本书正文，体积通常远大于普通网页；大于 1KB 才 gzip，
# 避免把短错误页也压缩得得不偿失。
_GZIP_MIN_BYTES = 1024
_GZIP_LEVEL = 6


def _is_private_ipv4(ip: str) -> bool:
    """判断是否为常见家用/办公局域网地址（排除 VPN 虚拟网段与链路本地地址）。"""
    parts = (ip or "").split(".")
    if len(parts) != 4:
        return False
    try:
        n = [int(p) for p in parts]
    except (TypeError, ValueError):
        return False
    return (n[0] == 10
            or (n[0] == 192 and n[1] == 168)
            or (n[0] == 172 and 16 <= n[1] <= 31))


def get_lan_ip() -> str:
    """探测本机局域网 IPv4（UDP connect 不实际发包，离线环境也可用）。

    有 VPN / 虚拟网卡时默认出口可能是 198.18.x 之类无法从手机访问的地址，
    因此优先在候选地址中挑 RFC1918 私有地址。
    """
    import socket
    candidates = []
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.3)
        sock.connect(("8.8.8.8", 80))
        candidates.append(sock.getsockname()[0])
    except Exception:
        pass
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            candidates.append(info[4][0])
    except Exception:
        pass
    for ip in candidates:
        if _is_private_ipv4(ip):
            return ip
    for ip in candidates:
        if ip and not ip.startswith("127."):
            return ip
    return "127.0.0.1"


def _accepts_gzip(headers: Any) -> bool:
    """解析 Accept-Encoding；显式 gzip;q=0 优先于通配符。"""
    raw = str(headers.get("Accept-Encoding") or "").lower()
    if not raw:
        return False
    saw_gzip = False
    gzip_allowed = False
    wildcard_allowed = False
    for part in raw.split(","):
        pieces = [p.strip() for p in part.split(";")]
        token = pieces[0]
        quality = 1.0
        for param in pieces[1:]:
            if param.startswith("q="):
                try:
                    quality = float(param[2:])
                except ValueError:
                    quality = 0.0
        if token in ("gzip", "x-gzip"):
            saw_gzip = True
            gzip_allowed = quality > 0
        elif token == "*":
            wildcard_allowed = quality > 0
    return gzip_allowed if saw_gzip else wildcard_allowed


def _send_web_response(handler: Any, body: str, content_type: str = "text/html; charset=utf-8",
                       status: int = 200, extra_headers: Optional[Dict[str, str]] = None,
                       precompressed_gzip: Optional[bytes] = None,
                       compress: bool = True) -> None:
    """向浏览器写出 Web 页面资源；支持的客户端自动收到 gzip 压缩正文。"""
    data = body.encode("utf-8")
    response_data = data
    response_headers: Dict[str, str] = {"Vary": "Accept-Encoding"}
    if compress and _accepts_gzip(handler.headers):
        if precompressed_gzip:
            response_data = precompressed_gzip
        elif len(data) >= _GZIP_MIN_BYTES:
            response_data = gzip.compress(data, compresslevel=_GZIP_LEVEL, mtime=0)
        if response_data is not data:
            response_headers["Content-Encoding"] = "gzip"
    handler.send_response(status)
    handler.send_header("Content-type", content_type)
    handler.send_header("Content-Length", str(len(response_data)))
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Access-Control-Allow-Origin", "*")
    for name, value in response_headers.items():
        handler.send_header(name, value)
    for name, value in (extra_headers or {}).items():
        handler.send_header(name, value)
    handler.end_headers()
    try:
        handler.wfile.write(response_data)
    except (BrokenPipeError, ConnectionResetError):
        pass


def _is_known_book_path(file_path: str) -> bool:
    """路径白名单：书库或爬取记录登记过的文件才允许浏览器打开。"""
    return _identity_is_known_book_path(file_path)


def _find_book_path_by_key(book_key: str) -> str:
    """把公开的 book key 反查为白名单内路径。"""
    return resolve_path_by_book_key(book_key)


def _resolve_requested_book_path(query: Dict[str, Any]) -> str:
    """解析 /reader、/download_book 的书目标识，兼容旧的 ?path= 链接。"""
    key = (query.get("book") or [""])[0]
    if key:
        resolved = _find_book_path_by_key(key)
        if resolved:
            return resolved
        # 兼容早期版本或手工请求把真实路径塞进 book 参数的情况
        if _is_known_book_path(key):
            return key
        return ""
    return (query.get("path") or [""])[0]


class _BookTextExtractor(HTMLParser):
    """把阅读器 HTML 还原为适合手机文本阅读器打开的纯文本。"""

    _BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br", "tr", "section", "article"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            if self._skip_depth:
                self._skip_depth -= 1
        elif tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        lines = [line.rstrip() for line in "".join(self._parts).splitlines()]
        out = []
        blank_pending = False
        for line in lines:
            if not line.strip():
                if out and not blank_pending:
                    out.append("")
                blank_pending = True
            else:
                out.append(line)
                blank_pending = False
        return "\n".join(out).strip() + "\n"


def _read_plain_text(file_path: str) -> str:
    """按阅读器相同的编码兜底顺序读取纯文本书籍。"""
    for encoding in ("utf-8", "gbk", "gb18030"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, "无法识别书籍编码")


def _book_to_txt(file_path: str) -> Optional[str]:
    """把书库中的书籍导出为 UTF-8 纯文本；加密且未解锁的书籍返回 None。"""
    import os
    from src.utils.browser_reader import _BROWSER_READER_BINARY_FORMATS

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _BROWSER_READER_BINARY_FORMATS:
        return _read_plain_text(file_path)

    html = BrowserReader.read_file_content(file_path)
    if 'data-needs-password="1"' in html:
        return None
    extractor = _BookTextExtractor()
    extractor.feed(html)
    return extractor.text()


def _txt_content_disposition(filename: str) -> str:
    """生成带中文文件名支持的 Content-Disposition（RFC 5987）。"""
    import re
    from urllib.parse import quote

    fallback = re.sub(r"[^\x20-\x7e]", "_", filename).replace('"', "_").replace("\\", "_").replace("/", "_")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}'


def _ensure_http_editor(file_path: str) -> str:
    """为 HTTP /reader 页面启动并缓存浏览器编辑器服务，返回编辑器 URL。"""
    import os
    key = os.path.realpath(file_path)
    with _editor_servers_lock:
        cached = _editor_servers.get(key)
        if cached and cached[0]:
            # LRU：命中的条目移到末尾，超限时淘汰最久未使用的服务
            _editor_servers.pop(key, None)
            _editor_servers[key] = cached
            return cached[0]
        try:
            from src.utils.browser_editor import BrowserEditorServer
            server = BrowserEditorServer(key, idle_timeout=0)
            url = server.start()
            _editor_servers[key] = (url, server)
            while len(_editor_servers) > _EDITOR_SERVERS_MAX:
                old_key, (_, old_server) = next(iter(_editor_servers.items()))
                del _editor_servers[old_key]
                try:
                    old_server.stop()
                except Exception as e:
                    logger.debug(f"关闭淘汰的编辑器服务失败: {e}")
            return url
        except Exception as e:
            logger.warning(f"为局域网阅读页启动编辑器失败: {e}")
            return ""


def _build_reader_page(file_path: str, req_host: str, req_port: int, secret: str,
                       book_key: str = "") -> Optional[Tuple[str, bytes]]:
    """生成阅读页，返回 (HTML, 预压缩 gzip)；与 file:// 版本共用页面与功能。"""
    import os
    from pathlib import Path
    from src.config.config_manager import ConfigManager

    if not file_path or not os.path.isfile(file_path):
        return None
    if not _is_known_book_path(file_path):
        logger.warning(f"拒绝通过局域网打开非书库文件: {file_path}")
        return None

    try:
        mtime = int(os.path.getmtime(file_path))
    except OSError:
        mtime = 0
    # 开屏密码开关/密码变更后必须让页面缓存失效，否则仍按旧密码校验
    try:
        _sg_cfg = ConfigManager.get_instance().get_config().get("browser_server", {}) or {}
    except Exception:
        _sg_cfg = {}
    _sg_enabled = bool(_sg_cfg.get("startup_password_enabled", False))
    _sg_pwd = str(_sg_cfg.get("startup_password", "") or "")
    # 末尾为前端资源版本号：响应式 CSS / Web JS / Service Worker 有变更时递增，
    # 让进程内缓存的旧 /reader 页面失效，否则局域网版会一直返回修复前的 HTML。
    cache_key = (f"{os.path.realpath(file_path)}|{mtime}|{req_host}|{req_port}|{secret}|"
                 f"{_sg_enabled}|{_sg_pwd}|59")
    with _reader_page_cache_lock:
        cached = _reader_page_cache.get(cache_key)
        cached_gzip = _reader_page_gzip_cache.get(cache_key, b"")
    if cached:
        return cached, cached_gzip

    try:
        cfg = ConfigManager.get_instance().get_config()
        bs = cfg.get("browser_server", {}) or {}
        content = BrowserReader.read_file_content(file_path)
        base = f"http://{req_host}:{req_port}"
        html = BrowserReader.create_reader_html(
            content,
            Path(file_path).stem,
            "light",
            save_progress_url=f"{base}/save_progress",
            load_progress_url=f"{base}/load_progress",
            book_id=Path(file_path).stem,
            book_key=book_key or book_key_for_path(file_path),
            browser_server_host=req_host,
            browser_server_port=req_port,
            browser_server_base_port=req_port,
            file_path=file_path,
            lock_enabled=bool(bs.get("lock_enabled", False)),
            api_base_url=base,
            api_secret=secret,
            progress_sync_enabled=True,
            startup_password_enabled=_sg_enabled,
            startup_password=_sg_pwd,
            download_txt_enabled=True,
        )
    except Exception as e:
        logger.error(f"生成局域网阅读页失败: {e}")
        return None

    # 与桌面端 file:// 阅读页保持一致：为 HTTP /reader 注入浏览器编辑器入口。
    try:
        editor_url = _ensure_http_editor(file_path)
        if editor_url:
            public_key = book_key or book_key_for_path(file_path)
            return_url = f"{base}/reader?book={quote(public_key, safe='')}"
            if secret:
                return_url += "&key=" + quote(secret, safe="")
            html = BrowserReader._inject_editor_button(html, editor_url, return_url)
    except Exception as e:
        logger.warning(f"为局域网阅读页注入编辑器入口失败: {e}")

    # 阅读页内嵌整本书正文，预压缩一次后所有手机/浏览器请求都复用，避免每请求重复 gzip。
    try:
        compressed = gzip.compress(html.encode("utf-8"), compresslevel=_GZIP_LEVEL, mtime=0)
    except Exception as e:
        logger.warning(f"预压缩阅读页失败，将按原文返回: {e}")
        compressed = b""

    with _reader_page_cache_lock:
        if len(_reader_page_cache) >= _READER_PAGE_CACHE_MAX:
            oldest = next(iter(_reader_page_cache))
            _reader_page_cache.pop(oldest, None)
            _reader_page_gzip_cache.pop(oldest, None)
        _reader_page_cache[cache_key] = html
        _reader_page_gzip_cache[cache_key] = compressed
    return html, compressed


def _handle_web_get(handler: Any, path: str, query: Dict[str, Any], secret: str) -> bool:
    """处理局域网 Web 页面 GET 请求；返回 False 表示交由原有接口逻辑处理。"""
    import json

    # 局域网离线阅读：把书库中的书籍导出为 TXT 下载到本机/手机。
    # 必须在通用路径判断之前处理（它不属于 _WEB_PAGE_PATHS）。
    if path == "/download_book":
        if not _verify_request(handler.headers, query, secret):
            _send_web_response(handler, "接口密钥无效", "text/plain; charset=utf-8", status=401)
            return True
        file_path = _resolve_requested_book_path(query)
        if not file_path or not _is_known_book_path(file_path):
            _send_web_response(handler, "书籍不在书库中", "text/plain; charset=utf-8", status=404)
            return True
        try:
            text = _book_to_txt(file_path)
            if text is None:
                _send_web_response(handler, "加密书籍需先在阅读页解锁后再下载", "text/plain; charset=utf-8", status=409)
                return True
            import os
            stem = os.path.splitext(os.path.basename(file_path))[0] or "book"
            _send_web_response(
                handler, text, "text/plain; charset=utf-8",
                extra_headers={
                    "Content-Disposition": _txt_content_disposition(stem + ".txt"),
                    "X-Content-Type-Options": "nosniff",
                },
                compress=False,
            )
        except Exception as e:
            logger.error(f"导出书籍 TXT 失败: {e}", exc_info=True)
            _send_web_response(handler, f"导出失败: {e}", "text/plain; charset=utf-8", status=500)
        return True

    if path not in _WEB_PAGE_PATHS:
        return False
    from src.utils.reader_web import SERVICE_WORKER_JS, build_portal_html

    # Service Worker 与 manifest 必须免鉴权：浏览器注册 SW 时无法携带自定义头或密钥
    if path == "/sw.js":
        _send_web_response(
            handler, SERVICE_WORKER_JS, "application/javascript; charset=utf-8",
            extra_headers={"Service-Worker-Allowed": "/"},
        )
        return True
    if path == "/manifest.webmanifest":
        manifest = json.dumps({
            "name": "NewReader 浏览器阅读器", "short_name": "NewReader",
            "start_url": "/", "display": "standalone", "background_color": "#f5f6f8",
            "theme_color": "#2f7cf6",
            "icons": [],
        }, ensure_ascii=False)
        _send_web_response(handler, manifest, "application/manifest+json; charset=utf-8")
        return True

    if not _verify_request(handler.headers, query, secret):
        _send_web_response(
            handler,
            "<!doctype html><meta charset='utf-8'><p style='font:16px/1.8 sans-serif;padding:24px'>"
            "接口密钥无效，请在访问地址后追加 ?key=&lt;密钥&gt;</p>",
            status=401,
        )
        return True

    if path == "/":
        # 局域网书库入口页同样受开屏密码保护（与离线版 /reader 页共用门禁）
        try:
            from src.config.config_manager import ConfigManager
            _sg_cfg = ConfigManager.get_instance().get_config().get("browser_server", {}) or {}
            _sg_enabled = bool(_sg_cfg.get("startup_password_enabled", False))
            _sg_pwd = str(_sg_cfg.get("startup_password", "") or "")
        except Exception:
            _sg_enabled, _sg_pwd = False, ""
        _send_web_response(handler, build_portal_html(
            secret=secret,
            startup_password_enabled=_sg_enabled,
            startup_password=_sg_pwd,
        ))
        return True

    # /reader?book=<书籍公开标识>；旧链接 ?path=<已登记路径> 继续兼容。
    file_path = _resolve_requested_book_path(query)
    book_key = book_key_for_path(file_path) if file_path else ""
    host_header = (handler.headers.get("Host") or "").split(":")[0] or "localhost"
    try:
        req_port = int(handler.server.server_address[1])
    except Exception:
        req_port = 54321

    # ★ 局域网版阅读页：为该书注册进度落库回调。
    # 桌面端“在浏览器打开”流程（browser_reader.py:13795）会注册，但 /reader 直链访问不会，
    # 导致 POST /save_progress 找不到回调、manager.save_progress 返回 False、HTTP 404，
    # 进度无法同步到服务器。这里用 BookmarkManager 按 book_path 直接落库，与桌面端一致。
    if file_path:
        try:
            from pathlib import Path as _P
            from src.core.bookmark import BookmarkManager
            from src.utils.multi_user_manager import MultiUserManager
            _bm = BookmarkManager()
            _bid = _P(file_path).stem

            # 与桌面书架保持一致：以当前登录用户的 id 作为落库 user_id，
            # 这样局域网版保存的进度在桌面书架也能正确读取（避免“同步成功但书架进度不变”）。
            # get_current_user() 是 MultiUserManager 的静态方法（单用户/超级管理员模式返回 id=1，
            # 多用户模式返回真实登录用户 id），与书架设置 current_user_id 的来源完全相同。
            def _get_uid() -> int:
                try:
                    _cu = MultiUserManager.get_current_user()
                    if isinstance(_cu, dict) and _cu.get('id') is not None:
                        return int(_cu['id'])
                except Exception:
                    pass
                return 0

            def _on_progress_save(progress, scroll_top=0, scroll_height=0,
                                  current_page=None, total_pages=None, word_count=0):
                try:
                    _uid = _get_uid()
                    _tp = int(total_pages) if total_pages and total_pages > 0 else max(1, int((scroll_height or 0) / 1000))
                    _cp = int(current_page) if current_page and current_page > 0 else int(progress * _tp)
                    _bm.save_reading_info(
                        file_path, current_page=_cp, total_pages=_tp,
                        reading_progress=float(progress), scroll_top=int(scroll_top or 0),
                        scroll_height=int(scroll_height or 0), word_count=int(word_count or 0),
                        user_id=_uid)
                except Exception as _e:
                    logger.error(f"局域网版保存阅读进度失败: {_e}", exc_info=True)

            def _on_progress_load(book_id=""):
                try:
                    _uid = _get_uid()
                    _info = _bm.get_reading_info(file_path, user_id=_uid)
                    if _info and _info.get('progress', 0) > 0:
                        return {
                            'progress': _info.get('progress', 0),
                            'scrollTop': _info.get('scrollTop', 0),
                            'scrollHeight': _info.get('scrollHeight', 0) or 10000,
                        }
                except Exception as _e:
                    logger.error(f"局域网版加载阅读进度失败: {_e}", exc_info=True)
                return None

            BrowserReaderServerManager.get_instance().register_callbacks(
                _bid, on_progress_save=_on_progress_save, on_progress_load=_on_progress_load)
        except Exception as _e:
            logger.warning(f"为局域网阅读页注册进度回调失败: {_e}")

    page = _build_reader_page(file_path, host_header, req_port, secret, book_key=book_key)
    if page is None:
        _send_web_response(
            handler,
            "<!doctype html><meta charset='utf-8'><p style='font:16px/1.8 sans-serif;padding:24px'>"
            "无法打开该书籍：文件不存在或不在书库中。</p>",
            status=404,
        )
    else:
        html, compressed = page
        _send_web_response(handler, html, precompressed_gzip=compressed)
    return True


def translate_text_via_manager(text: str, target_lang: str = 'zh', source_lang: str = 'auto') -> Dict[str, Any]:
    """翻译文本：优先复用系统已配置的翻译 API；未配置时回退到免费无密钥翻译（MyMemory）。"""
    # 1. 优先使用系统中已配置的翻译服务（与 translation_dialog.py 共用 TranslationManager）
    try:
        from src.core.translation_manager import get_translation_manager, init_translation_manager_from_config
        tm = get_translation_manager()
        if not tm.get_available_services():
            init_translation_manager_from_config()
            tm = get_translation_manager()
        if tm.get_available_services():
            return tm.translate(text, target_lang, source_lang)
    except Exception as e:
        logger.warning(f"系统翻译服务不可用，尝试免费兜底翻译: {e}")

    # 2. 未配置任何 API 时，使用免费无密钥翻译（MyMemory）兜底
    return _fallback_translate(text, target_lang, source_lang)


def _fallback_translate(text: str, target_lang: str, source_lang: str) -> Dict[str, Any]:
    """免费无密钥翻译兜底，仅用于未配置翻译 API 时的应急。依次尝试多个公共接口。"""
    # 粗略检测源语言
    src = source_lang
    if not src or src == 'auto':
        if re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', text):
            src = 'zh-CN'
        else:
            src = 'en'
    tl = _map_translate_lang(target_lang)

    # 1) MyMemory 公共接口
    try:
        import requests
        resp = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{_map_translate_lang(src)}|{tl}"},
            timeout=8
        )
        resp.raise_for_status()
        j = resp.json()
        translated = (j.get("responseData") or {}).get("translatedText")
        if translated:
            return {
                "success": True,
                "original_text": text,
                "translated_text": translated,
                "source_lang": src,
                "target_lang": target_lang,
                "service": "mymemory(free)"
            }
    except Exception as e:
        logger.debug(f"MyMemory 兜底翻译失败: {e}")

    # 2) Google 免费 gtx 接口
    try:
        import requests
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": _map_translate_lang(src), "tl": tl, "dt": "t", "q": text},
            timeout=8
        )
        resp.raise_for_status()
        j = resp.json()
        # 返回结构: [[["译文","原文",...],...], ...]
        parts = []
        for seg in (j[0] or []):
            if seg and seg[0]:
                parts.append(seg[0])
        translated = "".join(parts)
        if translated:
            return {
                "success": True,
                "original_text": text,
                "translated_text": translated,
                "source_lang": src,
                "target_lang": target_lang,
                "service": "google(free)"
            }
    except Exception as e:
        logger.debug(f"Google gtx 兜底翻译失败: {e}")

    return {"success": False, "error": "未配置翻译 API，且免费翻译接口暂不可用（可能受网络限制）"}


class BrowserReaderServerManager:
    """浏览器阅读器服务器管理器"""
    
    _instance: Optional['BrowserReaderServerManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化服务器管理器"""
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._initialized = True
        self._server = None
        self._server_thread = None
        self._save_url: Optional[str] = None
        self._load_url: Optional[str] = None
        self._api_url: Optional[str] = None
        self._api_server = None
        self._api_thread = None
        # 统一服务是否挂载 /api/* 数据接口（由 start_server 按 browser_server.api_enabled 设置）
        self._serve_api: bool = True
        # 是否允许局域网访问（开启时统一服务绑定 0.0.0.0）
        self._lan_enabled: bool = False
        self._callbacks: Dict[str, Dict[str, Any]] = {}
        self._book_progress_data: Dict[str, Dict] = {}
        self._book_annotations: Dict[str, Dict[str, Any]] = {}
        self._annotation_callbacks: Dict[str, Dict[str, Any]] = {}
        # 本地阅读器服务使用的密钥：由 start_server 从 browser_server.api_secret 注入；
        # 为空表示开放模式（不校验），与 api/server.py 保持一致
        self._secret: str = ""
        
        logger.info("浏览器阅读器服务器管理器已初始化")
    
    def _check_existing_server(self, host: str, port: int) -> bool:
        """快速检测端口上是否已有本程序的服务器在运行"""
        try:
            import json
            import urllib.request
            url = f"http://{host}:{port}/health_check"
            req = urllib.request.Request(url, method='GET')
            req.add_header('Connection', 'close')
            with urllib.request.urlopen(req, timeout=0.3) as response:
                data = response.read().decode('utf-8')
                result = json.loads(data)
                return result.get("status") == "ok"
        except Exception:
            return False

    @staticmethod
    def _is_port_free(host: str, port: int) -> bool:
        """用 bind 探测端口是否可用（与真正启动语义一致，比 connect_ex 可靠）。

        connect_ex 对"已监听但未 accept 且 backlog 满"的端口会误判为空闲。
        """
        import socket
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((host, int(port)))
            return True
        except OSError:
            return False
        finally:
            probe.close()

    def _find_available_port(self, host: str, base_port: int, max_tries: int = 100,
                             max_port: Optional[int] = None) -> int:
        """从 base_port 开始找一个可用端口，供当前实例独占使用。

        多实例场景下必须各自独立端口：复用别人的端口会让页面连到别人的后端。
        max_port（设置中心 port_range_max）用于限定顺延上限，超出后交由系统随机分配。
        """
        base_port = int(base_port or 54321)
        for offset in range(max_tries):
            candidate = base_port + offset
            if max_port and candidate > max_port:
                break
            if self._is_port_free(host, candidate):
                return candidate
        logger.warning(f"端口 {base_port} 起的 {max_tries} 个端口都不可用，走随机端口范围兜底")
        return 0

    def _find_random_available_port(self, host: str, min_port: int, max_port: int,
                                    tries: int = 10) -> int:
        """在设置中心的随机端口范围 [min_port, max_port] 内随机找一个可用端口。

        用于：browser_server.port=0 时的初始分配，以及顺延窗口耗尽后的兜底。
        范围内全部失败时返回 0（最终兜底：系统随机分配）。
        """
        import random
        min_port, max_port = int(min_port), int(max_port)
        if min_port > max_port:
            min_port, max_port = max_port, min_port
        tried = set()
        for _ in range(max(tries, 1)):
            candidate = random.randint(min_port, max_port)
            if candidate in tried:
                continue
            tried.add(candidate)
            if self._is_port_free(host, candidate):
                return candidate
        logger.warning(f"随机端口范围 [{min_port}, {max_port}] 内 {tries} 次尝试均失败，交由系统分配")
        return 0

    def start_server(self) -> bool:
        """启动浏览器阅读器服务器"""
        try:
            # 获取配置
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager.get_instance()
            config = config_manager.get_config()
            browser_config = config.get("browser_server", {})
            host = browser_config.get("host", "localhost")
            # 局域网访问：对外绑定 0.0.0.0，但注入页面的地址仍用配置的 host（本机可用），
            # HTTP 页面会在浏览器端用 location.origin 自动改用实际访问地址
            self._lan_enabled = bool(browser_config.get("lan_enabled", False))
            bind_host = "0.0.0.0" if self._lan_enabled else host
            # 本地统一服务使用的密钥（进度接口与 /api/* 数据接口共用 browser_server.api_secret）
            # 运行期每个请求都会重新读配置（get_runtime_secret），此处只是启动时的快照
            self._secret = get_runtime_secret()
            # 是否在同一服务上提供 /api/* 数据接口（api_enabled=false 时仅提供进度接口）
            self._serve_api = bool(browser_config.get("api_enabled", True))
            # 密钥注入到 /api/* 分发器（开放模式下为空）；同时注册动态提供者，
            # 让设置中心清空/修改密钥后无需重启服务即刻生效
            try:
                from src.api import set_api_secret, set_api_secret_provider
                set_api_secret_provider(get_runtime_secret)
                set_api_secret(self._secret)
            except Exception as e:
                logger.warning(f"注入 API 密钥失败: {e}")

            if self.is_server_running():
                logger.info("浏览器阅读器服务器已在运行")
                self._configure_api()
                return True
            
            fixed_port = int(browser_config.get("port", 54321) or 0)
            # 设置中心的端口规则：port=0 时在 [port_range_min, port_range_max] 内随机分配；
            # port 非 0 时用指定端口，被占用则向上顺延（上限 port_range_max），
            # 顺延窗口耗尽后同样按随机端口范围兜底
            _range_min = int(browser_config.get("port_range_min", 10000) or 10000)
            _range_max = int(browser_config.get("port_range_max", 60000) or 60000)
            _max_retry = int(browser_config.get("max_retry_attempts", 10) or 10)
            if _range_min > _range_max:
                _range_min, _range_max = _range_max, _range_min

            # 初始化翻译管理器（复用系统中的翻译配置）
            try:
                from src.core.translation_manager import init_translation_manager_from_config
                init_translation_manager_from_config()
            except Exception as _e:
                logger.warning(f"初始化翻译管理器失败（翻译功能将不可用）: {_e}")

            chosen_port = fixed_port
            if fixed_port == 0:
                # port=0：按设置中心的随机端口范围分配
                logger.info(f"端口设置为0，将按设置中心随机端口范围 [{_range_min}, {_range_max}] 分配")
                chosen_port = self._find_random_available_port(host, _range_min, _range_max, _max_retry)
            else:
                # ★ 多实例隔离：端口被占用时"换端口"，绝不"复用"别人的服务。
                # 复用会让浏览器页面连到另一个实例的后端（数据回调/书库都在别人进程里），
                # 表现为页面连错后端、保存 404、状态显示混乱。
                if not self._is_port_free(host, fixed_port):
                    if self._check_existing_server(host, fixed_port):
                        logger.info(f"端口 {fixed_port} 已被其它阅读器实例占用，本实例将使用独立端口（不复用）")
                    else:
                        logger.info(f"端口 {fixed_port} 被其它程序占用，本实例将使用独立端口")
                    chosen_port = self._find_available_port(host, fixed_port, max_port=_range_max)

            # 顺延窗口耗尽仍无端口：按设置中心随机端口范围兜底（最终仍失败则系统随机分配）
            if chosen_port == 0 and fixed_port != 0:
                logger.info(f"顺延窗口内无可用端口，按设置中心随机端口范围 [{_range_min}, {_range_max}] 兜底")
                chosen_port = self._find_random_available_port(host, _range_min, _range_max, _max_retry)

            # 启动统一服务器（进度接口 + 可选的 /api/* 数据接口 + 局域网 Web 页面）
            logger.info(f"尝试启动统一服务 - bind: {bind_host}, url_host: {host}, port: {chosen_port}, serve_api: {self._serve_api}")
            self._save_url, self._load_url, self._server, self._server_thread = \
                self._start_custom_server(chosen_port, host, serve_api=self._serve_api, bind_host=bind_host)
            if self._lan_enabled:
                if not self._secret:
                    logger.warning("局域网访问已开启但未设置接口密钥，同网段设备可直接访问数据接口，建议配置 browser_server.api_secret")
                logger.info(f"局域网书库入口: http://{get_lan_ip()}:{chosen_port}/")
            
            logger.info(f"服务器启动结果 - save_url: {self._save_url}, load_url: {self._load_url}")
            if not (self._save_url and self._load_url):
                logger.error("浏览器阅读器服务器启动失败")
            
            if self._save_url and self._load_url:
                logger.info(f"浏览器阅读器服务器已启动: {self._save_url}")
                self._configure_api()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"启动浏览器阅读器服务器时出错: {e}", exc_info=True)
            return False
    
    def _start_custom_server(self, port: int, host: str = "localhost", serve_api: bool = True,
                             bind_host: Optional[str] = None) -> tuple:
        """启动自定义服务器"""
        from http.server import BaseHTTPRequestHandler
        import json
        import threading
        from urllib.parse import parse_qs, urlparse
        
        class CustomProgressHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # 禁用日志输出
            
            def do_GET(self):
                parsed = urlparse(self.path)
                path = parsed.path
                query = parse_qs(parsed.query)
                # 每次请求读当前配置：设置中心清空密钥后立即进入开放模式，无需重启服务
                secret = get_runtime_secret()

                # 健康检查：仅返回状态与实例标识，且需被无密钥的本地/远程健康探测访问，故保持开放
                if path == '/health_check':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok", "instance": PROCESS_INSTANCE_ID}).encode())
                    return

                # 局域网 Web 页面：书库入口页 / 阅读页 / Service Worker / manifest
                # （内部自行处理鉴权；不匹配的路径返回 False 继续走原接口逻辑）
                if _handle_web_get(self, path, query, secret):
                    return

                # 其余读取接口（进度/标注/单词本）均需密钥匹配；开放模式下 secret 为空则放行
                if not _verify_request(self.headers, query, secret):
                    self.send_response(401)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "密钥无效或未提供"}).encode())
                    return

                if path == '/load_progress':
                    # 从查询参数获取书籍ID
                    book_id = query.get('book_id', [''])[0]

                    # 使用管理器加载进度
                    manager = BrowserReaderServerManager.get_instance()
                    data = manager.load_progress(book_id)

                    if data:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(data).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                elif path == '/load_annotations':
                    # 加载书籍标注（高亮/笔记/书签）
                    book_id = query.get('book_id', [''])[0]
                    manager = BrowserReaderServerManager.get_instance()
                    data = manager.load_annotations(book_id)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": True,
                        "highlights": data.get("highlights", []),
                        "notes": data.get("notes", []),
                        "bookmarks": data.get("bookmarks", [])
                        }, ensure_ascii=False).encode('utf-8'))
                elif path == '/load_vocab':
                    # 加载书籍单词本（与终端阅读器共用 VocabularyManager，按 book_id 过滤）
                    book_id = query.get('book_id', [''])[0]
                    try:
                        from src.core.vocabulary_manager import get_vocabulary_manager
                        manager = get_vocabulary_manager()
                        words = manager.get_words_by_book(book_id)
                        data = [w.to_dict() for w in words]
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True, "words": data}, ensure_ascii=False).encode('utf-8'))
                    except Exception as e:
                        import traceback
                        logger.error(f"加载单词本出错: {e}", exc_info=True)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8'))
                else:
                    # 统一服务：/api/* 数据接口分发（api_enabled 时挂载在同一端口）
                    if serve_api and (path == '/api' or path.startswith('/api/')):
                        from src.api import dispatch_api
                        dispatch_api(self)
                        return
                    self.send_response(404)
                    self.end_headers()
            
            def do_POST(self):
                # 所有写/读接口均需密钥匹配（开放模式下 secret 为空则放行）
                _parsed = urlparse(self.path)
                _req_path = _parsed.path
                _query = parse_qs(_parsed.query)
                _secret = get_runtime_secret()
                if not _verify_request(self.headers, _query, _secret):
                    self.send_response(401)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "密钥无效或未提供"}).encode())
                    return
                if _req_path == '/save_progress':
                    # 读取请求数据
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        
                        # 优先从 X-Book-ID 请求头获取书籍ID；
                        # sendBeacon 无法设置自定义请求头，因此退化到从 body 的 book_id 字段读取
                        from urllib.parse import unquote
                        book_id_header = self.headers.get('X-Book-ID', '')
                        if book_id_header:
                            book_id = unquote(book_id_header)
                        else:
                            book_id = data.get('book_id', '')
                        
                        # 使用管理器保存进度
                        manager = BrowserReaderServerManager.get_instance()
                        # 确保progress是float类型
                        progress_value = data.get('progress', 0)
                        if isinstance(progress_value, str):
                            progress_value = float(progress_value)
                        
                        success = manager.save_progress(
                            book_id, 
                            progress_value,
                            int(data.get('scrollTop', 0)),
                            int(data.get('scrollHeight', 0)),
                            int(data.get('current_page', 0)),
                            int(data.get('total_pages', 0)),
                            int(data.get('word_count', 0))
                        )
                        
                        if success:
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "success"}).encode())
                        else:
                            # 未找到对应书籍的回调（book_id 不匹配），进度实际未落库
                            self.send_response(404)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({
                                "status": "error",
                                "message": "未找到该书进度回调，进度未保存"
                            }).encode())
                    except Exception as e:
                        import traceback
                        error_msg = f"保存进度出错: {e}"
                        logger.error(error_msg, exc_info=True)
                        logger.error(f"接收到的数据: {post_data}")
                        logger.error(f"错误堆栈:\n{traceback.format_exc()}")
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e), "traceback": traceback.format_exc()}).encode())
                elif _req_path == '/scan_directory':
                    # 扫描目录并导入书籍
                    import os
                    from src.config.default_config import SUPPORTED_FORMATS
                    
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        directory = data.get('directory', '')
                        recursive = data.get('recursive', True)
                        
                        if not directory or not os.path.isdir(directory):
                            self.send_response(400)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({"success": False, "error": "无效的目录路径"}).encode())
                            return
                        
                        # 支持的书籍文件扩展名
                        supported_extensions = set(SUPPORTED_FORMATS)
                        
                        books = []
                        scan_count = 0
                        
                        if recursive:
                            # 递归扫描
                            for root, dirs, files in os.walk(directory):
                                for file in files:
                                    file_lower = file.lower()
                                    if any(file_lower.endswith(ext) for ext in supported_extensions):
                                        file_path = os.path.join(root, file)
                                        books.append({
                                            "file_name": file,
                                            "file_path": file_path,
                                            "title": os.path.splitext(file)[0]
                                        })
                                        scan_count += 1
                        else:
                            # 只扫描当前目录
                            for file in os.listdir(directory):
                                file_lower = file.lower()
                                if any(file_lower.endswith(ext) for ext in supported_extensions):
                                    file_path = os.path.join(directory, file)
                                    books.append({
                                        "file_name": file,
                                        "file_path": file_path,
                                        "title": os.path.splitext(file)[0]
                                    })
                                    scan_count += 1
                        
                        logger.info(f"扫描目录 {directory} 完成，找到 {scan_count} 本书籍")
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": True,
                            "books": books,
                            "count": scan_count
                        }).encode())
                        
                    except Exception as e:
                        import traceback
                        logger.error(f"扫描目录出错: {e}", exc_info=True)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": False,
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        }).encode())
                elif _req_path == '/translate':
                    # 翻译文本（复用系统翻译服务）
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        text = data.get('text', '')
                        target_lang = data.get('target_lang', 'zh')
                        source_lang = data.get('source_lang', 'auto')

                        from src.utils.browser_reader_server_manager import translate_text_via_manager
                        result = translate_text_via_manager(text, target_lang, source_lang)
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                    except Exception as e:
                        import traceback
                        logger.error(f"翻译出错: {e}", exc_info=True)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": False,
                            "error": str(e)
                        }, ensure_ascii=False).encode('utf-8'))
                elif _req_path == '/save_annotations':
                    # 保存书籍标注（高亮/笔记/书签）
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        book_id = data.get('book_id', '')
                        manager = BrowserReaderServerManager.get_instance()
                        ok = manager.save_annotations(book_id, data)
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": ok}, ensure_ascii=False).encode('utf-8'))
                    except Exception as e:
                        import traceback
                        logger.error(f"保存标注出错: {e}", exc_info=True)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({
                            "success": False,
                            "error": str(e)
                        }, ensure_ascii=False).encode('utf-8'))
                elif _req_path == '/save_vocab':
                    # 保存单词到单词本（与终端阅读器共用 VocabularyManager）
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        word = (data.get('word') or '').strip()
                        translation = data.get('translation', '') or ''
                        context = data.get('context', '') or ''
                        book_id = data.get('book_id', '') or ''
                        position = int(data.get('position', 0) or 0)
                        if not word:
                            self.send_response(400)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({"success": False, "error": "word 不能为空"}, ensure_ascii=False).encode('utf-8'))
                        else:
                            from src.core.vocabulary_manager import get_vocabulary_manager
                            manager = get_vocabulary_manager()
                            item = manager.add_word(
                                word=word, translation=translation, language='en',
                                context=context, book_id=book_id, position=position
                            )
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps(
                                {"success": item is not None, "word": item.to_dict() if item else None},
                                ensure_ascii=False).encode('utf-8'))
                    except Exception as e:
                        import traceback
                        logger.error(f"保存单词出错: {e}", exc_info=True)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8'))
                elif _req_path == '/open_book_content':
                    # 浏览器阅读器：后端解析二进制书籍（epub/mobi/azw/azw3/pdf），
                    # 加密 PDF 可带 password 二次请求解密。返回 JSON。
                    try:
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode('utf-8'))
                        path = (data.get('path') or '').strip()
                        if not path and data.get('book'):
                            path = _find_book_path_by_key(data['book'])
                        password = data.get('password') or None
                        from src.utils.browser_reader import BrowserReader
                        result = BrowserReader.open_book_content_json(path, password)
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                    except Exception as e:
                        import traceback
                        logger.error(f"打开书籍内容失败: {e}", exc_info=True)
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8'))
                else:
                    # 统一服务：/api/* 数据接口分发（api_enabled 时挂载在同一端口）
                    if serve_api and (_req_path == '/api' or _req_path.startswith('/api/')):
                        from src.api import dispatch_api
                        dispatch_api(self)
                        return
                    self.send_response(404)
                    self.end_headers()
            
            def do_OPTIONS(self):
                # CORS预检请求：允许携带 X-Book-ID / X-API-Key 自定义头（否则浏览器会拦截实际请求）
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Book-ID, X-API-Key')
                self.end_headers()
        
        try:
            # 使用多线程服务器：避免慢请求（如 /translate 调用外部翻译API）
            # 占满单线程，把 /save_vocab 等普通写入请求堵住
            from http.server import ThreadingHTTPServer
            server = ThreadingHTTPServer((bind_host or host, port), CustomProgressHandler)
            # 使用守护线程，这样Python退出时不会等待
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            
            # 实际绑定的端口（port=0 时由系统随机分配，取真实端口回填 URL）
            actual_port = server.server_address[1] or port
            save_url = f"http://{host}:{actual_port}/save_progress"
            load_url = f"http://{host}:{actual_port}/load_progress"
            
            return save_url, load_url, server, server_thread
        except Exception as e:
            logger.error(f"启动自定义服务器失败: {e}")
            return None, None, None, None
    
    def _configure_api(self) -> None:
        """配置后端数据接口地址。

        /api/* 已并入统一服务（与进度接口同端口），无需单独启动服务：
        - api_enabled=false 时页面进入仅本地模式（_api_url=None）；
        - api_base_url 有值时优先使用（如远程后端）；
        - 否则使用统一服务实际绑定的地址。
        """
        try:
            from src.config.config_manager import ConfigManager
            cfg = ConfigManager.get_instance().get_config()
            bc = cfg.get("browser_server", {})
            if not bc.get("api_enabled", True):
                self._api_url = None
                logger.info("后端数据接口已按配置禁用（浏览器将仅本地模式）")
                return
            try:
                from src.api import set_open_book_callback
                set_open_book_callback(self._open_book_by_path)
            except Exception as e:
                logger.warning(f"注册打开书籍回调失败: {e}")
            base = (bc.get("api_base_url") or "").strip()
            if base:
                self._api_url = base.rstrip("/")
            elif self._save_url:
                from urllib.parse import urlparse
                parsed = urlparse(self._save_url)
                self._api_url = f"http://{parsed.hostname or 'localhost'}:{parsed.port or 54321}"
            else:
                self._api_url = None
            if self._api_url:
                logger.info(f"后端数据接口已并入统一服务: {self._api_url}"
                            + ("" if self._secret else "（开放模式）"))
        except Exception as e:
            logger.warning(f"配置后端数据接口失败（浏览器将仅本地模式）: {e}")
            self._api_url = None

    def get_api_url(self) -> Optional[str]:
        """获取后端数据接口地址（供浏览器阅读器连接）。"""
        return self._api_url

    def _open_book_by_path(self, path: str):
        """供浏览器端 /api/open_book 调用：在服务端用浏览器打开指定书籍。"""
        try:
            from src.utils.browser_reader import BrowserReader
            return BrowserReader.open_book_in_browser(path)
        except Exception as e:
            logger.error(f"通过 API 打开书籍失败: {path} - {e}")
            return (False, str(e))

    def stop_server(self):
        """停止浏览器阅读器服务器"""
        try:
            if self._server:
                self._server.shutdown()
                self._server = None
            if self._server_thread and self._server_thread.is_alive():
                # 设置超时，避免阻塞
                self._server_thread.join(timeout=0.5)
                self._server_thread = None
            self._save_url = None
            self._load_url = None
            if self._api_server:
                try:
                    self._api_server.shutdown()
                except Exception:
                    pass
                self._api_server = None
            if self._api_thread and self._api_thread.is_alive():
                self._api_thread.join(timeout=0.5)
                self._api_thread = None
            self._api_url = None
            logger.info("浏览器阅读器服务器已停止")
        except Exception as e:
            logger.error(f"停止服务器时出错: {e}")
    
    def __del__(self):
        """析构函数，确保服务器被正确关闭"""
        try:
            self.stop_server()
        except:
            pass
    
    def is_server_running(self) -> bool:
        """检查服务器是否正在运行"""
        running = (self._server is not None and 
                self._server_thread is not None and 
                self._server_thread.is_alive())
        
        # 如果看起来在运行，验证端口是否真的在监听
        if running and self._save_url:
            import socket
            try:
                from urllib.parse import urlparse
                parsed = urlparse(self._save_url)
                host = parsed.hostname or 'localhost'
                port = parsed.port or 54321
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result != 0:
                    logger.warning(f"端口 {port} 未在监听，标记服务器为未运行")
                    running = False
            except Exception as e:
                logger.warning(f"检查端口时出错: {e}")
                running = False
        
        return running
    
    def get_server_urls(self) -> tuple[Optional[str], Optional[str]]:
        """获取服务器URL"""
        return self._save_url, self._load_url

    def sync_runtime_config(self, secret: Optional[str] = None) -> None:
        """设置中心保存后热更新接口密钥，无需重启浏览器阅读器服务。

        Args:
            secret: 设置中心里填写的密钥（留空即开放模式）。传入时同时刷新配置管理器
                的内存视图，避免 ``save_config(显式 config)`` 只落盘导致 ``get_config()``
                仍返回旧值；不传则直接沿用当前配置。

        注意：host / port / lan_enabled 决定监听地址，变更仍需重启服务。
        """
        try:
            from src.config.config_manager import ConfigManager
            cfg = ConfigManager.get_instance().get_config()
            browser_cfg = cfg.setdefault("browser_server", {})
            if secret is not None:
                browser_cfg["api_secret"] = str(secret or "").strip()
            self._secret = get_runtime_secret()
            from src.api import set_api_secret, set_api_secret_provider
            set_api_secret_provider(get_runtime_secret)
            set_api_secret(self._secret)
            self._configure_api()
            logger.info("接口密钥已热更新：" + ("开放模式（不校验密钥）" if not self._secret else "需要密钥"))
        except Exception as e:
            logger.warning(f"同步浏览器阅读器运行配置失败: {e}")

    def get_lan_access_url(self) -> Optional[str]:
        """返回可直接复制到手机/平板的局域网访问地址。

        未开启局域网访问或服务未启动时返回 None；配置了接口密钥时地址会带上 ``?key=``，
        便于移动设备首次打开即可通过鉴权，之后密钥由浏览器 localStorage 保存。
        """
        if not getattr(self, "_lan_enabled", False) or not self._save_url:
            return None
        try:
            from urllib.parse import quote, urlparse
            port = urlparse(self._save_url).port
        except Exception:
            port = None
        if not port:
            return None
        # 密钥可能刚在设置中心被清空/修改，展示的地址也要同步更新
        secret = get_runtime_secret()
        self._secret = secret
        url = f"http://{get_lan_ip()}:{port}/"
        if secret:
            url += "?key=" + quote(secret, safe="")
        return url

    def get_book_reader_url(self, book_key: str) -> Optional[str]:
        """返回桌面端“浏览器阅读”应打开的 URL：只含公开 book 标识，不含物理路径。"""
        if not book_key or not self._save_url:
            return None
        from urllib.parse import quote, urlparse
        try:
            port = urlparse(self._save_url).port
        except Exception:
            port = None
        if not port:
            return None
        host = get_lan_ip() if getattr(self, "_lan_enabled", False) else "127.0.0.1"
        url = f"http://{host}:{port}/reader?book={quote(str(book_key), safe='')}"
        secret = get_runtime_secret()
        self._secret = secret
        if secret:
            url += "&key=" + quote(secret, safe="")
        return url

    def register_callbacks(self, book_id: str, 
                          on_progress_save: Optional[Callable] = None,
                          on_progress_load: Optional[Callable] = None,
                          on_annotations_save: Optional[Callable] = None,
                          on_annotations_load: Optional[Callable] = None):
        """注册书籍特定的回调函数"""
        if book_id not in self._callbacks:
            self._callbacks[book_id] = {}
            # 按书累积的状态（回调/进度/标注）原本只增不减，限制为最近若干本，
            # 防止长时间运行后内存与字典遍历成本持续上升。
            max_books = 200
            for cache in (self._callbacks, self._book_progress_data,
                          self._book_annotations, self._annotation_callbacks):
                while len(cache) > max_books:
                    cache.pop(next(iter(cache)), None)
        
        if on_progress_save:
            self._callbacks[book_id]['save'] = on_progress_save
        if on_progress_load:
            self._callbacks[book_id]['load'] = on_progress_load
        
        if on_annotations_save or on_annotations_load:
            self._annotation_callbacks[book_id] = {
                'save': on_annotations_save,
                'load': on_annotations_load
            }
        
        logger.debug(f"已注册书籍 {book_id} 的回调函数")
    
    def save_progress(self, book_id: str, progress: float, scroll_top: int, 
                     scroll_height: int, current_page: int = 0, 
                     total_pages: int = 0, word_count: int = 0) -> bool:
        """保存书籍进度"""
        try:
            # 保存到内存
            self._book_progress_data[book_id] = {
                'progress': progress,
                'scroll_top': scroll_top,
                'scroll_height': scroll_height,
                'current_page': current_page,
                'total_pages': total_pages,
                'word_count': word_count,
                'timestamp': time.time()
            }
            
            # 如果有注册的回调，也调用它（真正写入数据库）
            callback_invoked = False
            if book_id in self._callbacks and 'save' in self._callbacks[book_id]:
                callback = self._callbacks[book_id]['save']
                if callback:
                    callback(progress, scroll_top, scroll_height, current_page, total_pages, word_count)
                    callback_invoked = True
            else:
                logger.warning(f"书籍 {book_id} 没有注册进度保存回调，进度仅存内存、未落库")
            
            logger.debug(f"已保存书籍 {book_id} 的进度: {progress:.4f}")
            # 只有真正调用了落库回调才算成功，否则返回 False 让服务端返回 404
            return callback_invoked
        except Exception as e:
            logger.error(f"保存进度失败: {e}")
            return False
    
    def load_progress(self, book_id: str) -> Optional[Dict[str, Any]]:
        """加载书籍进度"""
        try:
            # 从内存加载
            if book_id in self._book_progress_data:
                return self._book_progress_data[book_id]
            
            # 如果有注册的回调，也调用它
            if book_id in self._callbacks and 'load' in self._callbacks[book_id]:
                callback = self._callbacks[book_id]['load']
                if callback:
                    data = callback(book_id)
                    if data:
                        # 保存到内存
                        self._book_progress_data[book_id] = data
                        return data
            
            return None
        except Exception as e:
            logger.error(f"加载进度失败: {e}")
            return None
    
    def save_annotations(self, book_id: str, data: Dict[str, Any]) -> bool:
        """保存书籍标注（高亮/笔记/书签）

        data 结构: {{"highlights": [...], "notes": [...], "bookmarks": [...]}}
        """
        try:
            clean = {
                'highlights': data.get('highlights', []),
                'notes': data.get('notes', []),
                'bookmarks': data.get('bookmarks', [])
            }
            self._book_annotations[book_id] = clean

            if book_id in self._annotation_callbacks:
                cb = self._annotation_callbacks[book_id].get('save')
                if cb:
                    cb(book_id, clean)
            return True
        except Exception as e:
            logger.error(f"保存标注失败: {e}")
            return False

    def load_annotations(self, book_id: str) -> Dict[str, Any]:
        """加载书籍标注"""
        try:
            if book_id in self._book_annotations:
                return self._book_annotations[book_id]

            if book_id in self._annotation_callbacks:
                cb = self._annotation_callbacks[book_id].get('load')
                if cb:
                    data = cb(book_id)
                    if data:
                        self._book_annotations[book_id] = data
                        return data
            return {'highlights': [], 'notes': [], 'bookmarks': []}
        except Exception as e:
            logger.error(f"加载标注失败: {e}")
            return {'highlights': [], 'notes': [], 'bookmarks': []}

    @classmethod
    def get_instance(cls) -> 'BrowserReaderServerManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_browser_reader_server_manager() -> BrowserReaderServerManager:
    """获取浏览器阅读器服务器管理器实例"""
    return BrowserReaderServerManager.get_instance()


def start_browser_reader_server() -> bool:
    """启动浏览器阅读器服务器"""
    manager = get_browser_reader_server_manager()
    return manager.start_server()


def stop_browser_reader_server():
    """停止浏览器阅读器服务器"""
    manager = get_browser_reader_server_manager()
    manager.stop_server()