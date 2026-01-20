"""
剪贴板监听器 - 通过剪贴板获取URL的替代方案
"""

import re
import time
import threading
from urllib.parse import unquote
from typing import Dict, Any, List, Optional, Set, Callable
from src.locales.i18n_manager import get_global_i18n
from src.utils.logger import get_logger

logger = get_logger(__name__)

class ClipboardMonitor:
    """剪贴板监听器"""
    
    def __init__(self, novel_sites: List[Dict[str, Any]], on_url_detected: Optional[Callable] = None):
        """
        初始化剪贴板监听器
        
        Args:
            novel_sites: 小说网站配置列表
            on_url_detected: 检测到URL时的回调函数
        """
        self.novel_sites = novel_sites
        self.on_url_detected = on_url_detected
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.processed_urls: Set[str] = set()
        self.i18n = get_global_i18n()
        
        # 监听间隔（秒）
        self.monitor_interval = 1.0
        
        # 上次剪贴板内容
        self.last_clipboard_content = ""
        
        # 尝试导入剪贴板库
        self.clipboard_available = self._init_clipboard()
    
    def _init_clipboard(self) -> bool:
        """初始化剪贴板功能"""
        try:
            # 尝试导入不同的剪贴板库
            try:
                import pyperclip
                self.clipboard_lib = pyperclip
                logger.info("使用pyperclip进行剪贴板操作")
                return True
            except ImportError:
                pass
            
            try:
                import clipboard
                self.clipboard_lib = clipboard
                logger.info("使用clipboard进行剪贴板操作")
                return True
            except ImportError:
                pass
            
            # macOS专用
            try:
                import subprocess
                result = subprocess.run(['pbpaste'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.clipboard_lib = 'macos_pbpaste'
                    logger.info("使用macOS pbpaste进行剪贴板操作")
                    return True
            except Exception:
                pass
            
            logger.warning("无法导入剪贴板库，剪贴板监听功能不可用")
            return False
            
        except Exception as e:
            logger.error(f"初始化剪贴板功能失败: {e}")
            return False
    
    def get_clipboard_content(self) -> str:
        """获取剪贴板内容"""
        try:
            if hasattr(self.clipboard_lib, 'paste'):
                return self.clipboard_lib.paste()
            elif self.clipboard_lib == 'macos_pbpaste':
                import subprocess
                result = subprocess.run(['pbpaste'], capture_output=True, text=True)
                return result.stdout.strip()
            else:
                return ""
        except Exception as e:
            logger.debug(f"获取剪贴板内容失败: {e}")
            return ""
    
    def is_valid_novel_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        验证URL是否为有效的小说页面
        
        Args:
            url: 要验证的URL
            
        Returns:
            如果有效，返回包含网站信息和小说ID的字典；否则返回None
        """
        try:
            # 去除前后空格
            url = url.strip()
            
            # 检查是否为HTTP/HTTPS URL
            if not (url.startswith('http://') or url.startswith('https://')):
                return None
            
            # 检查URL是否匹配任何小说网站
            for site in self.novel_sites:
                if not site.get('url'):
                    continue
                    
                site_url = site['url'].rstrip('/')
                if url.startswith(site_url):
                    # 尝试提取小说ID
                    novel_id = self.extract_novel_id_from_url(url, site)
                    if novel_id:
                        return {
                            'site': site,
                            'novel_id': novel_id,
                            'url': url
                        }
            return None
            
        except Exception as e:
            logger.debug(f"验证URL失败: {url}, 错误: {e}")
            return None
    
    def extract_novel_id_from_url(self, url: str, site_config: Dict[str, Any]) -> Optional[str]:
        """
        从URL中提取小说ID
        
        Args:
            url: 页面URL
            site_config: 网站配置
            
        Returns:
            小说ID或None
        """
        try:
            # 获取URL模式
            url_pattern = site_config.get('url_pattern', '')
            base_url = site_config.get('url', '').rstrip('/')
            
            if not url_pattern:
                # 使用默认模式：/b/{novel_id}
                pattern = rf"{re.escape(base_url)}/b/([^/?]+)"
                match = re.search(pattern, url)
                if match:
                    return unquote(match.group(1))
            else:
                # 使用自定义模式
                pattern = url_pattern.replace('{novel_id}', '([^/?]+)')
                pattern = rf"{re.escape(base_url)}/{pattern}"
                match = re.search(pattern, url)
                if match:
                    return unquote(match.group(1))
            
            return None
            
        except Exception as e:
            logger.debug(f"提取小说ID失败: {url}, 错误: {e}")
            return None
    
    def monitor_clipboard(self) -> None:
        """监听剪贴板变化的主循环"""
        logger.info("开始监听剪贴板变化")
        
        while self.is_monitoring:
            try:
                # 获取当前剪贴板内容
                current_content = self.get_clipboard_content()
                
                # 检查是否有新内容
                if current_content and current_content != self.last_clipboard_content:
                    self.last_clipboard_content = current_content
                    
                    # 检查是否为URL
                    if current_content.startswith(('http://', 'https://')):
                        # 检查是否已处理过
                        if current_content not in self.processed_urls:
                            # 验证是否为有效的小说URL
                            result = self.is_valid_novel_url(current_content)
                            
                            if result:
                                logger.info(f"检测到有效的小说URL: {current_content}")
                                
                                # 调用回调函数
                                if self.on_url_detected:
                                    try:
                                        self.on_url_detected(result)
                                    except Exception as e:
                                        logger.error(f"回调函数执行失败: {e}")
                                
                                # 标记为已处理
                                self.processed_urls.add(current_content)
                
                # 等待下次检查
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"监听过程中发生错误: {e}")
                time.sleep(self.monitor_interval)
        
        logger.info("剪贴板监听已停止")
    
    def start_monitoring(self) -> bool:
        """
        开始监听剪贴板
        
        Returns:
            是否成功开始监听
        """
        if not self.clipboard_available:
            logger.error("剪贴板功能不可用，无法开始监听")
            return False
        
        if self.is_monitoring:
            logger.warning("剪贴板监听已在运行")
            return True
        
        try:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
            self.monitor_thread.start()
            
            logger.info("剪贴板监听已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动剪贴板监听失败: {e}")
            self.is_monitoring = False
            return False
    
    def stop_monitoring(self) -> None:
        """停止监听剪贴板"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        logger.info("剪贴板监听已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取监听器状态
        
        Returns:
            状态信息字典
        """
        return {
            'is_monitoring': self.is_monitoring,
            'is_active': self.is_monitoring and (self.monitor_thread is not None and self.monitor_thread.is_alive()),
            'processed_urls_count': len(self.processed_urls),
            'clipboard_available': self.clipboard_available
        }