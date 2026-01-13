"""
API服务模块 - 提供RESTful API接口
（简化版本，不依赖FastAPI以避免依赖问题）
"""

import json
import threading
from typing import Dict, Any, Optional
from datetime import datetime
import time

class APIService:
    """API服务 - 提供RESTful API接口的简化实现"""
    
    def __init__(self):
        """初始化API服务"""
        self._routes: Dict[str, callable] = {}
        self._running = False
        self._server_thread = None
        
        # 注册默认路由
        self._register_default_routes()
    
    def _register_default_routes(self):
        """注册默认路由"""
        self.add_route("GET", "/", self._root_handler)
        self.add_route("GET", "/health", self._health_handler)
        self.add_route("GET", "/status", self._status_handler)
    
    def add_route(self, method: str, path: str, handler: callable):
        """添加路由"""
        route_key = f"{method.upper()}:{path}"
        self._routes[route_key] = handler
    
    def _root_handler(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """根路径处理器"""
        return {
            "message": "Welcome to NewReader API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
    
    def _health_handler(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """健康检查处理器"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "newreader-api"
        }
    
    def _status_handler(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """状态检查处理器"""
        import psutil
        
        # 获取系统状态信息
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        return {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_info.percent,
                "memory_available": memory_info.available,
                "disk_percent": (disk_info.used / disk_info.total) * 100,
                "disk_free": disk_info.free
            },
            "service": "newreader-api"
        }
    
    def handle_request(self, method: str, path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理API请求"""
        route_key = f"{method.upper()}:{path}"
        
        if route_key in self._routes:
            try:
                handler = self._routes[route_key]
                result = handler(params or {})
                return {
                    "success": True,
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "success": False,
                "error": "Route not found",
                "timestamp": datetime.now().isoformat()
            }
    
    def start_server(self, host: str = "127.0.0.1", port: int = 8000):
        """启动API服务器（简化实现，仅作演示）"""
        print(f"API服务器将在 {host}:{port} 上启动")
        print("注意：这是简化版本，实际部署需要使用真正的Web框架")
        
        # 在实际实现中，这里会启动一个HTTP服务器
        # 但现在我们只是模拟启动
        self._running = True
        print("API服务已启动")
    
    def stop_server(self):
        """停止API服务器"""
        self._running = False
        print("API服务已停止")
    
    def is_running(self) -> bool:
        """检查服务是否运行"""
        return self._running


# 全局API服务实例
_api_service = None


def get_api_service() -> APIService:
    """获取API服务实例"""
    global _api_service
    if _api_service is None:
        _api_service = APIService()
    return _api_service


def handle_api_request(method: str, path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """处理API请求的便捷函数"""
    api_service = get_api_service()
    return api_service.handle_request(method, path, params)


# 为向后兼容定义app对象（空实现）
class DummyApp:
    """模拟FastAPI应用对象"""
    pass


app = DummyApp()


if __name__ == "__main__":
    # 简单测试
    api = get_api_service()
    result = api.handle_request("GET", "/")
    print("API测试结果:", result)