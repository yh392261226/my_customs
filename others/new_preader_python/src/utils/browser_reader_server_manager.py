"""
浏览器阅读器服务器管理器
负责在应用启动时自动启动后端服务器，并管理其生命周期
"""

import threading
import time
from typing import Optional, Dict, Any, Callable
from src.utils.logger import get_logger
from src.utils.browser_reader import BrowserReader

logger = get_logger(__name__)


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
        self._callbacks: Dict[str, Dict[str, Any]] = {}
        self._book_progress_data: Dict[str, Dict] = {}
        
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

    def start_server(self) -> bool:
        """启动浏览器阅读器服务器"""
        try:
            if self.is_server_running():
                logger.info("浏览器阅读器服务器已在运行")
                return True
            
            # 获取配置
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager.get_instance()
            config = config_manager.get_config()
            browser_config = config.get("browser_server", {})
            fixed_port = browser_config.get("port", 54321)
            host = browser_config.get("host", "localhost")

            # ★ 快速检测：端口是否已被其他实例占用
            # 如果是本程序的服务器，直接复用URL，无需等待或重复启动
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2)
            port_in_use = sock.connect_ex((host, fixed_port)) == 0
            sock.close()

            if port_in_use and self._check_existing_server(host, fixed_port):
                logger.info(f"检测到端口 {fixed_port} 已有服务在运行，直接复用")
                self._save_url = f"http://{host}:{fixed_port}/save_progress"
                self._load_url = f"http://{host}:{fixed_port}/load_progress"
                self._server = None  # 不持有服务器对象，因为不是我们启动的
                self._server_thread = None
                return True

            # 端口未被占用或非本程序服务，等待后启动（缩短等待时间）
            if port_in_use:
                max_wait = 2  # 减少到最多等2秒
                wait_interval = 0.2
                
                for i in range(int(max_wait / wait_interval)):
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.1)
                    result = sock.connect_ex((host, fixed_port))
                    sock.close()
                    
                    if result != 0:  # 端口释放了
                        break
                    
                    time.sleep(wait_interval)
            
            # 获取配置中的host设置
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager.get_instance()
            config = config_manager.get_config()
            browser_config = config.get("browser_server", {})
            host = browser_config.get("host", "localhost")
            
            # 启动服务器（使用自定义方法）
            logger.info(f"尝试启动服务器 - host: {host}, port: {fixed_port}")
            self._save_url, self._load_url, self._server, self._server_thread = \
                self._start_custom_server(fixed_port, host)
            
            logger.info(f"服务器启动结果 - save_url: {self._save_url}, load_url: {self._load_url}")
            if self._save_url and self._load_url:
                # 验证端口
                from urllib.parse import urlparse
                parsed_url = urlparse(self._save_url)
                actual_port = parsed_url.port
                
                if actual_port == fixed_port:
                    logger.info(f"浏览器阅读器服务器已在固定端口 {fixed_port} 启动: {self._save_url}")
                else:
                    logger.error(f"服务器启动在错误端口 {actual_port}，期望 {fixed_port}")
                    # 停止服务器
                    if self._server:
                        self._server.shutdown()
                    if self._server_thread:
                        self._server_thread.join(timeout=1)
                    self._server = None
                    self._server_thread = None
                    self._save_url = None
                    self._load_url = None
            else:
                logger.error("浏览器阅读器服务器启动失败")
            
            if self._save_url and self._load_url:
                logger.info(f"浏览器阅读器服务器已启动: {self._save_url}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"启动浏览器阅读器服务器时出错: {e}", exc_info=True)
            return False
    
    def _start_custom_server(self, port: int, host: str = "localhost") -> tuple:
        """启动自定义服务器"""
        from http.server import BaseHTTPRequestHandler
        import json
        import threading
        from urllib.parse import parse_qs, urlparse
        
        class CustomProgressHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # 禁用日志输出
            
            def do_GET(self):
                if self.path == '/load_progress':
                    # 从查询参数获取书籍ID
                    parsed = urlparse(self.path)
                    query = parse_qs(parsed.query)
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
                elif self.path == '/health_check':
                    # 健康检查
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_POST(self):
                if self.path == '/save_progress':
                    # 从请求头获取书籍ID
                    book_id_header = self.headers.get('X-Book-ID', '')
                    # URL解码书籍ID
                    from urllib.parse import unquote
                    book_id = unquote(book_id_header)
                    
                    # 读取请求数据
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        
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
                            self.send_response(500)
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
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
                elif self.path == '/scan_directory':
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
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_OPTIONS(self):
                # CORS预检请求
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Book-ID')
                self.end_headers()
        
        try:
            from http.server import HTTPServer
            server = HTTPServer((host, port), CustomProgressHandler)
            # 使用守护线程，这样Python退出时不会等待
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            
            save_url = f"http://{host}:{port}/save_progress"
            load_url = f"http://{host}:{port}/load_progress"
            
            return save_url, load_url, server, server_thread
        except Exception as e:
            logger.error(f"启动自定义服务器失败: {e}")
            return None, None, None, None
    
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
    
    def register_callbacks(self, book_id: str, 
                          on_progress_save: Optional[Callable] = None,
                          on_progress_load: Optional[Callable] = None):
        """注册书籍特定的回调函数"""
        if book_id not in self._callbacks:
            self._callbacks[book_id] = {}
        
        if on_progress_save:
            self._callbacks[book_id]['save'] = on_progress_save
        if on_progress_load:
            self._callbacks[book_id]['load'] = on_progress_load
        
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
            
            # 如果有注册的回调，也调用它
            if book_id in self._callbacks and 'save' in self._callbacks[book_id]:
                callback = self._callbacks[book_id]['save']
                if callback:
                    callback(progress, scroll_top, scroll_height, current_page, total_pages, word_count)
            
            logger.debug(f"已保存书籍 {book_id} 的进度: {progress:.4f}")
            return True
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