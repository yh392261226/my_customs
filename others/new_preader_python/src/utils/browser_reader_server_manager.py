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
    
    def start_server(self) -> bool:
        """启动浏览器阅读器服务器"""
        try:
            if self.is_server_running():
                logger.info("浏览器阅读器服务器已在运行")
                return True
            
            # 创建虚拟文件路径用于服务器初始化
            import tempfile
            import os
            
            temp_dir = tempfile.mkdtemp()
            dummy_file = os.path.join(temp_dir, "browser_reader_server.txt")
            
            with open(dummy_file, 'w', encoding='utf-8') as f:
                f.write("浏览器阅读器服务器占位文件")
            
            # 定义进度保存回调
            def on_progress_save(progress: float, scroll_top: int, scroll_height: int,
                              current_page: Optional[int] = None, total_pages: Optional[int] = None,
                              word_count: Optional[int] = None):
                """保存进度回调"""
                # 从请求中获取书籍ID（通过HTTP头传递）
                # 这里暂时不处理，实际保存会在HTTP处理器中进行
                logger.debug(f"收到进度保存请求: progress={progress:.4f}, scrollTop={scroll_top}")
            
            # 定义进度加载回调
            def on_progress_load() -> Optional[Dict[str, Any]]:
                """加载进度回调"""
                # 这里暂时不处理，实际加载会在HTTP处理器中进行
                return None
            
            # 获取配置的固定端口
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager.get_instance()
            config = config_manager.get_config()
            browser_config = config.get("browser_server", {})
            fixed_port = browser_config.get("port", 54321)
            
            # 强制使用固定端口
            logger.info(f"尝试在固定端口 {fixed_port} 启动浏览器阅读器服务器...")
            
            import socket
            
            # 等待端口释放（如果被占用）
            max_wait = 10  # 最多等待10秒
            wait_interval = 0.5  # 每0.5秒检查一次
            
            for i in range(int(max_wait / wait_interval)):
                # 检查端口是否可用
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex(('localhost', fixed_port))
                sock.close()
                
                if result != 0:  # 端口可用
                    break
                
                if i < int(max_wait / wait_interval) - 1:
                    logger.info(f"端口 {fixed_port} 被占用，等待 {wait_interval} 秒后重试...")
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
                    data = callback()
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