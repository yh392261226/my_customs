"""
可视化补缺助手 —— 在浏览器中通过拖拽操作完成补缺位置选择
生成 HTML 页面，支持：
  - 目标文件内容预览（带行号，可点击定位）
  - 三个拖放区域：前置 / 中间 / 后置
  - 新爬取书籍的 draggable 区块
  - 点击目标文件任意行设为中间插入点
  - 确认后通过 HTTP POST 将数据返回给 Python 后端
"""

import os
import json
import tempfile
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from src.utils.logger import get_logger
from src.utils.browser_manager import BrowserManager

logger = get_logger(__name__)


class VisualMergeHelper:
    """可视化补缺助手——管理 HTML 生成、HTTP 通信和浏览器打开"""

    _instance: Optional['VisualMergeHelper'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._port: int = 54322  # 独立端口，避免与阅读器冲突
        self._host: str = "localhost"
        self._result_data: Optional[Dict[str, Any]] = None
        self._result_event = threading.Event()
        self._result_callback: Optional[Callable] = None
        self._current_html_content: str = ""  # 存储当前 HTML 内容供 HTTP 服务器使用
        logger.info("可视化补缺助手已初始化")

    # ══════════════════════════════════════════
    #   公开 API
    # ══════════════════════════════════════════

    def open_visual_merge(
        self,
        target_file_path: str,
        target_lines: List[str],
        crawled_books: List[Dict[str, Any]],
        existing_groups: Dict[str, Dict[str, Any]],
        callback: Optional[Callable[[Dict], None]] = None,
        theme: str = "light",
    ) -> bool:
        """
        打开可视化补缺页面。

        Args:
            target_file_path: 目标文件路径
            target_lines: 目标文件按行的内容列表
            crawled_books: 新爬取的书籍列表 [{title, file_path, novel_id, ...}]
            existing_groups: 已有的分组信息 {front/middle/back: {books: [], line: int|None}}
            callback: 用户确认后的回调函数，接收合并结果字典
            theme: UI 主题 (light / dark)

        Returns:
            是否成功打开浏览器
        """
        try:
            # 1. 启动 HTTP 服务器接收结果
            if not self._start_server():
                logger.error("无法启动可视化补缺 HTTP 服务器")
                return False

            # 2. 准备书籍数据
            books_data = []
            for i, book in enumerate(crawled_books):
                books_data.append({
                    "index": i,
                    "title": book.get('title', book.get('novel_title', f'Book #{i+1}')),
                    "novel_id": str(book.get('novel_id', '')),
                    "file_path": book.get('file_path', ''),
                    "exists": os.path.exists(book.get('file_path', ''))
                    if book.get('file_path') else False,
                })

            # 3. 构建分组初始状态
            groups_init = {}
            for gkey in ('front', 'middle', 'back'):
                gdata = existing_groups.get(gkey, {"books": [], "line": None})
                groups_init[gkey] = {
                    "book_indices": gdata.get("books", []),
                    "line": gdata.get("line"),
                }

            # 4. 生成完整 HTML
            submit_url = f"http://{self._host}:{self._port}/submit_merge"
            html = self._create_merge_html(
                target_file_path=target_file_path,
                target_lines=target_lines,
                books_data=books_data,
                groups_init=groups_init,
                submit_url=submit_url,
                theme=theme,
            )

            # 5. 将 HTML 内容存储在实例变量中，供 HTTP 服务器使用
            self._current_html_content = html

            # 6. 注册回调
            self._result_callback = callback
            self._result_data = None
            self._result_event.clear()

            # 7. 打开浏览器访问 HTTP 地址，而不是本地文件
            url = f"http://{self._host}:{self._port}/"
            BrowserManager.open_url(url)

            logger.info(f"可视化补缺页面已打开: {url}")
            return True

        except Exception as e:
            logger.error(f"打开可视化补缺页面失败: {e}", exc_info=True)
            return False

    def wait_for_result(self, timeout: float = 300.0) -> Optional[Dict[str, Any]]:
        """阻塞等待用户在浏览器中确认（超时返回 None）"""
        if self._result_event.wait(timeout=timeout):
            return self._result_data
        return None

    def stop_server(self):
        """停止 HTTP 服务器"""
        try:
            if self._server:
                self._server.shutdown()
                self._server = None
            if self._server_thread and self._server_thread.is_alive():
                self._server_thread.join(timeout=0.5)
                self._server_thread = None
            # 清理 HTML 内容
            self._current_html_content = ""
            logger.info("可视化补缺 HTTP 服务器已停止")
        except Exception as e:
            logger.error(f"停止服务器失败: {e}")

    @classmethod
    def get_instance(cls) -> 'VisualMergeHelper':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ══════════════════════════════════════════
    #   HTTP 服务器
    # ══════════════════════════════════════════

    def _start_server(self) -> bool:
        """启动轻量 HTTP 服务器用于接收合并结果并提供 HTML 页面"""
        if self._server and self._server_thread and self._server_thread.is_alive():
            return True

        class MergeResultHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                # 添加请求日志以便调试
                logger.debug(f"HTTP {self.command} {self.path} - {format % args if args else format}")

            def do_GET(self):
                try:
                    helper = VisualMergeHelper.get_instance()
                    logger.debug(f"GET请求: {self.path}")
                    
                    if self.path == '/':
                        # 提供主 HTML 页面
                        if hasattr(helper, '_current_html_content') and helper._current_html_content:
                            self.send_response(200)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(helper._current_html_content.encode('utf-8'))
                            logger.debug(f"已发送HTML内容，长度: {len(helper._current_html_content)}")
                        else:
                            self.send_response(404)
                            self.end_headers()
                            logger.warning("GET /: 没有HTML内容可用")
                    elif self.path == '/health':
                        self._send_json(200, {"status": "ok"})
                    elif self.path == '/poll_result':
                        helper = VisualMergeHelper.get_instance()
                        if helper._result_data:
                            self._send_json(200, {"has_result": True, "data": helper._result_data})
                        else:
                            self._send_json(200, {"has_result": False})
                    else:
                        self.send_response(404)
                        self.end_headers()
                        logger.debug(f"GET请求路径未找到: {self.path}")
                except Exception as e:
                    logger.error(f"处理GET请求失败: {e}", exc_info=True)
                    self.send_response(500)
                    self.end_headers()

            def do_POST(self):
                try:
                    logger.debug(f"POST请求: {self.path}")
                    
                    if self.path == '/submit_merge':
                        helper = VisualMergeHelper.get_instance()
                        try:
                            content_length = int(self.headers.get('Content-Length', 0))
                            logger.debug(f"POST内容长度: {content_length}")
                            
                            if content_length > 0:
                                body = self.rfile.read(content_length)
                                data = json.loads(body.decode('utf-8'))

                                logger.info(f"收到可视化补缺结果: {json.dumps(data, ensure_ascii=False)}")

                                # 存储结果
                                helper._result_data = data
                                helper._result_event.set()

                                # 调用回调
                                if helper._result_callback:
                                    try:
                                        helper._result_callback(data)
                                    except Exception as cb_err:
                                        logger.error(f"回调执行失败: {cb_err}")

                                self._send_json(200, {"status": "success"})
                                logger.debug("POST请求处理成功")
                            else:
                                logger.warning("POST请求内容为空")
                                self._send_json(400, {"error": "请求内容为空"})
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON解析失败: {e}")
                            self._send_json(400, {"error": f"无效的JSON格式: {str(e)}"})
                        except Exception as e:
                            logger.error(f"处理提交数据失败: {e}", exc_info=True)
                            self._send_json(500, {"error": str(e)})
                    else:
                        self.send_response(404)
                        self.end_headers()
                        logger.debug(f"POST请求路径未找到: {self.path}")
                        
                except Exception as e:
                    logger.error(f"处理POST请求时发生未捕获的异常: {e}", exc_info=True)
                    # 尝试发送错误响应
                    try:
                        self.send_response(500)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(f"服务器内部错误: {str(e)}".encode('utf-8'))
                    except:
                        pass

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            def _send_json(self_self, code: int, data: dict):
                self_self.send_response(code)
                self_self.send_header('Content-Type', 'application/json; charset=utf-8')
                self_self.send_header('Access-Control-Allow-Origin', '*')
                self_self.end_headers()
                self_self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

        # 查找可用端口
        import socket
        port = self._port
        for i in range(20):  # 尝试最多 20 个端口
            try:
                logger.debug(f"尝试在端口 {port} 上启动服务器...")
                server = HTTPServer((self._host, port), MergeResultHandler)
                self._server = server
                self._server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                self._server_thread.start()
                self._port = port
                logger.info(f"可视化补缺服务器已启动: http://{self._host}:{self._port}")
                logger.debug(f"服务器线程已启动: {self._server_thread.is_alive()}")
                return True
            except OSError as e:
                logger.debug(f"端口 {port} 被占用: {e}")
                port += 1
                continue
            except Exception as e:
                logger.error(f"启动服务器失败: {e}", exc_info=True)
                port += 1
                continue

        logger.error("无法找到可用端口启动可视化补缺服务器")
        return False

    # ══════════════════════════════════════════
    #   HTML 生成器
    # ══════════════════════════════════════════

    def _create_merge_html(
        self,
        target_file_path: str,
        target_lines: List[str],
        books_data: List[Dict],
        groups_init: Dict[str, Dict],
        submit_url: str,
        theme: str = "light",
    ) -> str:
        """生成完整的可视化补缺 HTML 页面"""

        # 截断显示行数（避免超大文件导致浏览器卡顿）
        MAX_DISPLAY_LINES = 2000
        display_lines = target_lines[:MAX_DISPLAY_LINES]
        total_lines = len(target_lines)
        truncated = total_lines > MAX_DISPLAY_LINES

        # 行内容 JSON
        lines_json = json.dumps(display_lines, ensure_ascii=False)
        books_json = json.dumps(books_data, ensure_ascii=False)
        groups_json = json.dumps(groups_init, ensure_ascii=False)

        target_filename = os.path.basename(target_file_path) or "target.txt"

        # 主题色配置
        themes = {
            "light": {
                "bg": "#ffffff",
                "bg_secondary": "#f5f7fa",
                "bg_hover": "#e8ecf1",
                "text": "#1a1a2e",
                "text_muted": "#6b7280",
                "border": "#d1d5db",
                "accent": "#3b82f6",
                "accent_light": "#dbeafe",
                "success": "#10b981",
                "success_light": "#d1fae5",
                "warning": "#f59e0b",
                "warning_light": "#fef3c7",
                "error": "#ef4444",
                "drop_active": "#c7d2fe",
                "front_color": "#059669",
                "mid_color": "#d97706",
                "back_color": "#2563eb",
            },
            "dark": {
                "bg": "#1a1a2e",
                "bg_secondary": "#16213e",
                "bg_hover": "#0f3460",
                "text": "#e0e0e0",
                "text_muted": "#9ca3af",
                "border": "#374151",
                "accent": "#60a5fa",
                "accent_light": "#1e3a5f",
                "success": "#34d399",
                "success_light": "#064e3b",
                "warning": "#fbbf24",
                "warning_light": "#451a03",
                "error": "#f87171",
                "drop_active": "#4338ca",
                "front_color": "#34d399",
                "mid_color": "#fbbf24",
                "back_color": "#60a5fa",
            },
        }
        t = themes.get(theme, themes["light"])

        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Visual Merge Helper</title>
<style>
/* ===== Reset & Base ===== */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
    background: {t["bg"]};
    color: {t["text"]};
    line-height: 1.6;
    overflow-x: hidden;
}}

/* ===== Header ===== */
.header {{
    background: linear-gradient(135deg, {t["accent"]} 0%, #7c3aed 100%);
    color: white;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    position: sticky;
    top: 0;
    z-index: 100;
}}
.header h1 {{
    font-size: 20px;
    font-weight: 700;
}}
.header .target-info {{
    font-size: 13px;
    opacity: 0.9;
    margin-top: 4px;
}}
.header-actions button {{
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s ease;
    margin-left: 8px;
}}
.btn-confirm {{
    background: {t["success"]};
    color: white;
}}
.btn-confirm:hover {{ background: #059669; transform: translateY(-1px); }}
.btn-cancel {{
    background: rgba(255,255,255,0.2);
    color: white;
    border: 1px solid rgba(255,255,255,0.3) !important;
}}
.btn-cancel:hover {{ background: rgba(255,255,255,0.3); }}

/* ===== Main Layout ===== */
.main-layout {{
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 0;
    height: calc(100vh - 72px);
}}

/* ===== Left Panel: Target Content ===== */
.target-panel {{
    border-right: 2px solid {t["border"]};
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}
.target-header {{
    padding: 12px 16px;
    background: {t["bg_secondary"]};
    border-bottom: 1px solid {t["border"]};
    display: flex;
    align-items: center;
    gap: 12px;
}}
.target-header h2 {{ font-size: 14px; color: {t["text_muted"]}; }}
.target-header .hint {{
    font-size: 12px;
    color: {t["accent"]};
    background: {t["accent_light"]};
    padding: 4px 10px;
    border-radius: 12px;
}}
.target-content {{
    flex: 1;
    overflow-y: auto;
    padding: 0;
    font-family: "SF Mono", "Fira Code", "Cascadia Code", "Consolas", monospace;
    font-size: 13px;
}}
.target-line {{
    display: flex;
    min-height: 22px;
    border-bottom: 1px solid {t["bg_secondary"]};
    cursor: pointer;
    transition: background 0.1s ease;
}}
.target-line:hover {{ background: {t["bg_hover"]}; }}
.target-line.selected {{
    background: {t["warning_light"]};
    border-left: 3px solid {t["warning"]};
}}
.target-line.middle-insert-point {{
    background: {t["accent_light"]};
    border-top: 2px dashed {t["accent"]};
    border-bottom: 2px dashed {t["accent"]};
}}
.line-num {{
    width: 58px;
    min-width: 58px;
    text-align: right;
    padding: 0 10px;
    color: {t["text_muted"]};
    user-select: none;
    background: {t["bg_secondary"]};
    border-right: 1px solid {t["border"]};
    font-size: 11.5px;
}}
.line-text {{
    flex: 1;
    padding: 0 12px;
    white-space: pre-wrap;
    word-break: break-all;
    overflow-x: auto;
}}
.insert-indicator {{
    display: inline-block;
    background: {t["warning"]};
    color: white;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    margin-right: 6px;
    font-weight: 600;
    vertical-align: middle;
}}

/* ===== Right Panel: Drop Zones ===== */
.right-panel {{
    background: {t["bg_secondary"]};
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}
.zone-container {{
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 12px;
    gap: 10px;
    overflow-y: auto;
}}

/* Draggable Book Items */
.books-pool {{
    background: {t["bg"]};
    border: 1px solid {t["border"]};
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 8px;
}}
.books-pool-title {{
    font-size: 12px;
    color: {t["text_muted"]};
    margin-bottom: 8px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.book-item {{
    background: {t["bg"]};
    border: 2px solid {t["border"]};
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 6px;
    cursor: grab;
    transition: all 0.2s ease;
    user-select: none;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
}}
.book-item:hover {{
    border-color: {t["accent"]};
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transform: translateX(2px);
}}
.book-item:active {{ cursor: grabbing; }}
.book-item.dragging {{ opacity: 0.5; }}
.book-icon {{
    width: 28px;
    height: 28px;
    border-radius: 6px;
    background: {t["accent_light"]};
    color: {t["accent"]};
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: bold;
    flex-shrink: 0;
}}
.book-title {{
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.book-status {{
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
}}
.book-status.ok {{ background: {t["success_light"]}; color: {t["success"]}; }}
.book-status.err {{ background: #fef2f2; color: {t["error"]}; }}

/* Drop Zones */
.drop-zone {{
    border: 2px dashed {t["border"]};
    border-radius: 12px;
    padding: 12px;
    min-height: 80px;
    transition: all 0.25s ease;
    position: relative;
    background: {t["bg"]};
}}
.drop-zone.drag-over {{
    border-color: {t["accent"]};
    background: {t["drop_active"]};
    transform: scale(1.02);
    box-shadow: 0 0 16px rgba(59,130,246,0.25);
}}
.drop-zone-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
}}
.drop-zone-label {{
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.drop-zone-label .dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}}
.dot-front {{ background: {t["front_color"]}; }}
.dot-mid {{ background: {t["mid_color"]}; }}
.dot-back {{ background: {t["back_color"]}; }}
.drop-zone-count {{
    font-size: 11px;
    color: {t["text_muted"]};
    background: {t["bg_secondary"]};
    padding: 2px 8px;
    border-radius: 10px;
}}
.zone-books {{
    min-height: 30px;
}}
.dropped-book {{
    background: {t["bg_secondary"]};
    border: 1px solid {t["border"]};
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 4px;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    animation: slideIn 0.2s ease;
}}
.dropped-book .remove-btn {{
    background: none;
    border: none;
    color: {t["text_muted"]};
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0 2px;
}}
.dropped-book .remove-btn:hover {{ color: {t["error"]}; }}

@keyframes slideIn {{
    from {{ opacity: 0; transform: translateY(-4px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

/* Middle Line Input in Zone */
.middle-line-input-area {{
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed {t["border"]};
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
}}
.middle-line-input-area label {{ color: {t["text_muted"]}; }}
.middle-line-input-area input {{
    width: 70px;
    padding: 4px 8px;
    border: 1px solid {t["border"]};
    border-radius: 4px;
    background: {t["bg"]};
    color: {t["text"]};
    font-size: 12px;
}}
.middle-line-input-area .set-btn {{
    padding: 4px 10px;
    background: {t["accent"]};
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
}}

/* Status Bar */
.status-bar {{
    padding: 8px 16px;
    background: {t["bg"]};
    border-top: 1px solid {t["border"]};
    font-size: 12px;
    color: {t["text_muted"]};
    display: flex;
    align-items: center;
    gap: 16px;
}}

/* Empty state */
.empty-hint {{
    color: {t["text_muted"]};
    font-size: 12px;
    font-style: italic;
    text-align: center;
    padding: 12px;
}}

/* Scrollbar styling */
::-webkit-scrollbar {{ width: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: {t["border"]}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {t["text_muted"]}; }}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <div>
        <h1>📖 Visual Merge — 补缺可视化工具</h1>
        <div class="target-info">目标文件: <strong>{target_filename}</strong> ({total_lines} 行)</div>
        <div class="title-edit-area" style="margin-top: 8px;">
            <label style="font-size: 13px; color: rgba(255,255,255,0.9);">新书籍标题: </label>
            <input type="text" id="newBookTitle" placeholder="请输入新标题..." style="padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.3); background: rgba(255,255,255,0.1); color: white; width: 300px; font-size: 13px; margin-left: 8px;">
        </div>
    </div>
    <div class="header-actions">
        <button class="btn-cancel" onclick="window.close()">取消</button>
        <button class="btn-confirm" onclick="submitMerge()">✓ 确认合并</button>
    </div>
</div>

<!-- Main Layout -->
<div class="main-layout">
    <!-- 左侧：目标文件内容 -->
    <div class="target-panel">
        <div class="target-header">
            <h2>📄 目标文件内容</h2>
            <span class="hint">💡 点击任意行 → 设为中间组插入位置</span>
        </div>
        <div class="target-content" id="targetContent"></div>
    </div>

    <!-- 右侧：拖放区域 -->
    <div class="right-panel">
        <div class="zone-container">
            <!-- 待分配书籍池 -->
            <div class="books-pool" id="booksPool">
                <div class="books-pool-title">📚 待分配的新书籍（拖拽到下方区域）</div>
                <div id="poolBooks"></div>
            </div>

            <!-- 前置区 -->
            <div class="drop-zone" data-zone="front"
                 ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
                <div class="drop-zone-header">
                    <span class="drop-zone-label"><span class="dot dot-front"></span> 前置区 (Front)</span>
                    <span class="drop-zone-count" id="frontCount">0 本</span>
                </div>
                <div class="zone-books" id="zoneFrontBooks"></div>
                <div class="empty-hint" id="frontEmpty">拖拽书籍到这里 → 插入到文件开头</div>
            </div>

            <!-- 中间区 -->
            <div class="drop-zone" data-zone="middle"
                 ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
                <div class="drop-zone-header">
                    <span class="drop-zone-label"><span class="dot dot-mid"></span> 中间区 (Middle)</span>
                    <span class="drop-zone-count" id="middleCount">0 本</span>
                </div>
                <div class="zone-books" id="zoneMiddleBooks"></div>
                <div class="empty-hint" id="middleEmpty">拖拽书籍 + 点击左侧行号设置插入位置</div>
                <div class="middle-line-input-area" id="middleLineArea" style="display:none;">
                    <label>插入位置:</label>
                    <input type="number" id="middleLineInput" min="1" max="{total_lines}" placeholder="行号">
                    <button class="set-btn" onclick="applyMiddleLine()">设置</button>
                </div>
            </div>

            <!-- 后置区 -->
            <div class="drop-zone" data-zone="back"
                 ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDrop(event)">
                <div class="drop-zone-header">
                    <span class="drop-zone-label"><span class="dot dot-back"></span> 后置区 (Back)</span>
                    <span class="drop-zone-count" id="backCount">0 本</span>
                </div>
                <div class="zone-books" id="zoneBackBooks"></div>
                <div class="empty-hint" id="backEmpty">拖拽书籍到这里 → 追加到文件末尾</div>
            </div>
        </div>
        <div class="status-bar">
            <span id="statusText">就绪</span>
            <span id="selectedLineInfo"></span>
        </div>
    </div>
</div>

<script>
// ===== Data =====
const TARGET_LINES = {lines_json};
const TOTAL_LINES = {total_lines};
const BOOKS_DATA = {books_json};
const SUBMIT_URL = "{submit_url}";

let zones = {{ front: [], middle: [], back: [] }};
let middleLine = null;
let selectedLineEl = null;

// ===== Init =====
document.addEventListener("DOMContentLoaded", function() {{
    renderTargetContent();
    renderPoolBooks();
    // 初始分组状态
    const initGroups = {groups_json};
    if (initGroups) {{
        Object.keys(initGroups).forEach(zone => {{
            const g = initGroups[zone];
            if (g && g.book_indices) {{
                g.book_indices.forEach(idx => {{
                    const book = BOOKS_DATA.find(b => b.index === idx);
                    if (book) addToZone(zone, book, false);
                }});
            }}
            if (g && g.line && zone === "middle") {{
                middleLine = g.line;
                document.getElementById("middleLineInput").value = middleLine;
                showMiddleLineArea();
                highlightMiddleLine();
            }}
        }});
    }}
    updateAllZones();
}});

// ===== Target Content Rendering =====
function renderTargetContent() {{
    const container = document.getElementById("targetContent");
    let html = "";
    TARGET_LINES.forEach((line, idx) => {{
        const lineNum = idx + 1;
        const escaped = escapeHtml(line).replace(/\\n$/, "") || "\\u00A0";
        // 注意：使用 data-line 属性 + 事件委托，避免 f-string 嵌套变量问题
        html += '<div class="target-line" data-line="' + lineNum + '" onclick="onLineClick(this,' + lineNum + ')">' +
            '<div class="line-num">' + lineNum + '</div>' +
            '<div class="line-text">' + escaped + '</div>' +
            '</div>';
    }});
    container.innerHTML = html;

    // 使用事件委托替代 inline onclick（更可靠）
    container.onclick = function(e) {{
        const row = e.target.closest(".target-line");
        if (row && !e.target.closest(".remove-btn")) {{
            const ln = parseInt(row.dataset.line);
            if (!isNaN(ln)) onLineClick(row, ln);
        }}
    }};
}}

function escapeHtml(text) {{
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}}

// ===== Line Click → Set Middle Insert Point =====
function onLineClick(el, lineNum) {{
    // 取消之前选中
    if (selectedLineEl) {{
        selectedLineEl.classList.remove("selected", "middle-insert-point");
    }}
    // 选中当前行
    el.classList.add("selected", "middle-insert-point");
    selectedLineEl = el;

    middleLine = lineNum;
    document.getElementById("middleLineInput").value = lineNum;
    showMiddleLineArea();
    updateStatus(`已选中第 ${{lineNum}} 行作为中间插入点`);
    updateSelectedLineInfo(lineNum);

    // 自动将焦点切换到中间区
    document.querySelector('[data-zone="middle"]').scrollIntoView({{ behavior: "smooth", block: "nearest" }});
}}

function showMiddleLineArea() {{
    document.getElementById("middleLineArea").style.display = "flex";
}}

function applyMiddleLine() {{
    const val = parseInt(document.getElementById("middleLineInput").value);
    if (val && val >= 1 && val <= TOTAL_LINES) {{
        middleLine = val;
        highlightMiddleLine();
        updateStatus(`中间插入点已设置为第 ${{val}} 行`);
        // 也更新选中行视觉
        if (selectedLineEl) selectedLineEl.classList.remove("middle-insert-point");
        const lineEl = document.querySelector(`.target-line[data-line="${{val}}"]`);
        if (lineEl) {{
            if (selectedLineEl) selectedLineEl.classList.remove("selected");
            lineEl.classList.add("selected", "middle-insert-point");
            selectedLineEl = lineEl;
            lineEl.scrollIntoView({{ behavior: "smooth", block: "center" }});
        }}
        updateSelectedLineInfo(val);
    }} else {{
        alert("请输入有效的行号 (1-" + TOTAL_LINES + ")");
    }}
}}

function highlightMiddleLine() {{
    document.querySelectorAll(".target-line.middle-insert-point").forEach(el => {{
        el.classList.remove("middle-insert-point");
    }});
    if (middleLine) {{
        const el = document.querySelector(`.target-line[data-line="${{middleLine}}"]`);
        if (el) el.classList.add("middle-insert-point");
    }}
}}

// ===== Pool Books Rendering =====
function renderPoolBooks() {{
    const container = document.getElementById("poolBooks");
    let html = "";
    const assignedIndices = new Set([...zones.front, ...zones.middle, ...zones.back]);
    BOOKS_DATA.filter(book => !assignedIndices.has(book.index)).forEach(book => {{
        html += createBookItemHtml(book);
    }});
    container.innerHTML = html || '<div class="empty-hint">暂无待分配书籍</div>';
}}

function createBookItemHtml(book, showRemove = false) {{
    const statusClass = book.exists ? "ok" : "err";
    const statusText = book.exists ? "存在" : "缺失";
    const removeBtn = showRemove
        ? `<button class="remove-btn" onclick="event.stopPropagation(); removeBookFromZone(this, ${{book.index}})">×</button>`
        : "";
    return `<div class="book-item" draggable="true" data-index="${{book.index}}"
              ondragstart="handleDragStart(event)" ondragend="handleDragEnd(event)">
        <div class="book-icon">${{book.index + 1}}</div>
        <div class="book-title" title="${{escapeHtml(book.title)}}">${{escapeHtml(book.title)}}</div>
        <div class="book-status ${{statusClass}}">${{statusText}}</div>
        ${{removeBtn}}
    </div>`;
}}

// ===== Drag & Drop =====
let draggedIndex = null;

function handleDragStart(e) {{
    draggedIndex = parseInt(e.target.dataset.index);
    e.target.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", draggedIndex);
}}

function handleDragEnd(e) {{
    e.target.classList.remove("dragging");
    draggedIndex = null;
}}

function handleDragOver(e) {{
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    e.currentTarget.classList.add("drag-over");
}}

function handleDragLeave(e) {{
    e.currentTarget.classList.remove("drag-over");
}}

function handleDrop(e) {{
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");
    const zone = e.currentTarget.dataset.zone;
    if (draggedIndex !== null) {{
        const book = BOOKS_DATA.find(b => b.index === draggedIndex);
        if (book) addToZone(zone, book);
    }}
}}

function addToZone(zone, book, animate = true) {{
    // 从其他 zone 中移除（如果已在别的 zone）
    ["front", "middle", "back"].forEach(z => {{
        const idx = zones[z].indexOf(book.index);
        if (idx !== -1) zones[z].splice(idx, 1);
    }});
    // 加入新 zone
    zones[zone].push(book.index);
    updateAllZones();
}}

function removeBookFromZone(btnEl, bookIndex) {{
    const zoneEl = btnEl.closest(".drop-zone");
    const zone = zoneEl.dataset.zone;
    const idx = zones[zone].indexOf(bookIndex);
    if (idx !== -1) zones[zone].splice(idx, 1);
    updateAllZones();
}}

function updateAllZones() {{
    ["front", "middle", "back"].forEach(zone => {{
        const cap = zone.charAt(0).toUpperCase() + zone.slice(1);
        const container = document.getElementById("zone" + cap + "Books");
        const countEl = document.getElementById(zone + "Count");
        const emptyEl = document.getElementById(zone + "Empty");

        if (!container || !countEl) return;  // 安全检查

        const booksInZone = zones[zone].map(idx => BOOKS_DATA.find(b => b.index === idx)).filter(Boolean);

        countEl.textContent = booksInZone.length + " 本";

        if (emptyEl) {{
            if (booksInZone.length === 0) {{
                container.innerHTML = "";
                emptyEl.style.display = "block";
            }} else {{
                emptyEl.style.display = "none";
                let html = "";
                booksInZone.forEach(book => {{
                    html += '<div class="dropped-book">' +
                        '<span>' + escapeHtml(book.title) + '</span>' +
                        '<button class="remove-btn" onclick="removeBookFromZone(this,' + book.index + ')">×</button>' +
                        '</div>';
                }});
                container.innerHTML = html;
            }}
        }}
    }});
    renderPoolBooks();  // 更新书池
}}

// ===== Submit =====
async function submitMerge() {{
    const newTitle = document.getElementById("newBookTitle").value.trim();
    
    const result = {{
        action: "merge",
        front_books: zones.front.map(idx => BOOKS_DATA.find(b => b.index === idx)),
        middle_books: zones.middle.map(idx => BOOKS_DATA.find(b => b.index === idx)),
        back_books: zones.back.map(idx => BOOKS_DATA.find(b => b.index === idx)),
        middle_line: middleLine,
        new_title: newTitle || null,
        timestamp: Date.now(),
    }};

    // 验证
    const hasAny = zones.front.length > 0 || zones.middle.length > 0 || zones.back.length > 0;
    if (!hasAny) {{
        alert("请至少将一本书分配到一个区域！");
        return;
    }}
    if (zones.middle.length > 0 && !middleLine) {{
        alert("中间区有书籍但未设置插入位置！请点击左侧内容的某一行来设置。");
        return;
    }}

    try {{
        updateStatus("正在提交...");
        const resp = await fetch(SUBMIT_URL, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify(result),
        }});
        const data = await resp.json();
        if (data.status === "success") {{
            updateStatus("✅ 已提交！3秒后自动关闭...");
            document.body.style.pointerEvents = "none";
            document.body.style.opacity = "0.85";
            // 显示成功提示覆盖层
            const overlay = document.createElement("div");
            overlay.style.cssText = `
                position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(16,185,129,0.95);
                color:white;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:9999;font-size:24px;
            `;
            overlay.innerHTML = `✅<br><br>合并方案已成功提交！<br><br><span style="font-size:14px;opacity:0.8;">页面将在3秒后自动关闭</span>`;
            document.body.appendChild(overlay);
            
            // 3秒后自动关闭页面
            setTimeout(() => {{
                window.close();
            }}, 3000);
        }} else {{
            alert("提交失败: " + (data.error || "未知错误"));
        }}
    }} catch(err) {{
        console.error("Submit error:", err);
        alert("网络错误: " + err.message);
        updateStatus("❌ 提交失败");
    }}
}}

// ===== Status =====
function updateStatus(msg) {{
    document.getElementById("statusText").textContent = msg;
}}

function updateSelectedLineInfo(lineNum) {{
    const el = document.getElementById("selectedLineInfo");
    el.innerHTML = `📍 中间插入点: <strong>第 ${{lineNum}} 行</strong>`;
}}
</script>
</body>
</html>'''


def get_visual_merge_helper() -> VisualMergeHelper:
    """获取可视化补缺助手单例实例"""
    return VisualMergeHelper.get_instance()
