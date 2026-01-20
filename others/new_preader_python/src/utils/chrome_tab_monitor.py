"""
Chrome浏览器标签页监听器
用于监听Chrome浏览器打开的标签页，自动检测符合爬取条件的URL
"""

import threading
import time
import json
import platform
import re
from typing import Dict, List, Optional, Set, Callable
from urllib.parse import urlparse, unquote
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchWindowException
from src.utils.logger import get_logger
from src.locales.i18n_manager import get_global_i18n

logger = get_logger(__name__)

class ChromeTabMonitor:
    """Chrome标签页监听器"""
    
    def __init__(self, novel_sites: List[Dict[str, Any]], on_url_detected=None, headless=True):
        """
        初始化Chrome标签页监听器
        
        Args:
            novel_sites: 小说网站配置列表
            on_url_detected: 检测到URL时的回调函数
            headless: 是否使用无头模式（默认True，避免卡死）
        """
        self.novel_sites = novel_sites
        self.on_url_detected = on_url_detected
        self.driver: Optional[webdriver.Chrome] = None
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.processed_urls: Set[str] = set()  # 已处理的URL集合
        self.i18n = get_global_i18n()
        
        # 监听间隔（秒）
        self.monitor_interval = 2.0
        
        # Chrome驱动路径（可选）
        self.chrome_driver_path = None
        
        # 是否使用无头模式
        self.headless = headless
        
        # 是否使用AppleScript模式（macOS优先）
        self.use_applescript = platform.system() == "Darwin"
        if self.use_applescript:
            logger.info("使用AppleScript模式监听Chrome标签页")
        
    def setup_chrome_driver(self) -> bool:
        """
        设置Chrome驱动，尝试连接到现有Chrome实例或创建新实例
        
        Returns:
            是否设置成功
        """
        try:
            # 如果使用AppleScript模式，不需要设置Selenium驱动
            if self.use_applescript:
                logger.info("AppleScript模式，无需设置Chrome驱动")
                return True
            
            # 非AppleScript模式，使用Selenium
            # 首先尝试连接到现有的Chrome实例
            try:
                chrome_options = Options()
                chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                # 设置连接超时
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("成功连接到现有Chrome实例")
                return True
            except Exception as e:
                logger.debug(f"无法连接到现有Chrome实例: {e}")
                
                # 如果无法连接到现有实例，创建新的Chrome实例
                chrome_options = Options()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                if self.headless:
                    chrome_options.add_argument("--headless")  # 使用无头模式避免卡死
                
                # 直接使用自动检测的Chrome驱动
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                except WebDriverException as e:
                    logger.error(f"Chrome驱动启动失败: {e}")
                    return False
                
                # 验证驱动是否正常工作
                try:
                    self.driver.current_url  # 简单测试
                    logger.info("创建新的Chrome实例成功")
                    logger.warning("注意：新Chrome实例无法访问用户现有的标签页")
                    logger.warning("建议启动Chrome时使用远程调试：google-chrome --remote-debugging-port=9222")
                    return True
                except Exception as e:
                    logger.error(f"Chrome驱动创建后无法正常工作: {e}")
                    if self.driver:
                        try:
                            self.driver.quit()
                        except:
                            pass
                        self.driver = None
                    return False
            
        except Exception as e:
            logger.error(f"设置Chrome驱动失败: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            return False
    
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
            
            # 特殊处理crxs.me网站
            if 'crxs.me' in base_url:
                # crxs.me使用 /fiction/id-{novel_id}.html 格式
                pattern = rf"{re.escape(base_url)}/fiction/id-([^/?]+)\.html"
                match = re.search(pattern, url)
                if match:
                    return unquote(match.group(1))
            
            if not url_pattern:
                # 使用默认模式：/b/{novel_id}
                pattern = rf"{re.escape(base_url)}/b/([^/?]+)"
                match = re.search(pattern, url)
                if match:
                    return unquote(match.group(1))
            else:
                # 使用自定义模式
                # 处理包含锚点的情况，如 #Catalog
                clean_pattern = url_pattern.split('#')[0]  # 移除锚点部分
                
                # 特殊处理包含查询参数的模式
                if '?' in clean_pattern:
                    # 分离路径和查询参数部分
                    path_part, query_part = clean_pattern.split('?', 1)
                    path_pattern = path_part.replace('{novel_id}', '([^/?]+)')
                    
                    # 构造正则表达式
                    pattern = rf"{re.escape(base_url)}/{path_pattern}\?{re.escape(query_part.replace('{novel_id}', ''))}([^&=?]+)"
                else:
                    # 标准模式
                    pattern = clean_pattern.replace('{novel_id}', '([^/?]+)')
                    pattern = rf"{re.escape(base_url)}/{pattern}(?:\?[^#]*)?(?:#.*)?$"
                
                match = re.search(pattern, url)
                if match:
                    return unquote(match.group(1))
            
            return None
            
        except Exception as e:
            logger.debug(f"提取小说ID失败: {url}, 错误: {e}")
            return None
    
    def is_valid_novel_url(self, url: str) -> Optional[Dict]:
        """
        检查URL是否为有效的小说URL
        
        Args:
            url: 目标URL
            
        Returns:
            匹配的网站配置或None
        """
        try:
            for site in self.novel_sites:
                # 跳过没有有效URL配置的网站
                if not site.get('base_url') and not site.get('url'):
                    continue
                    
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
    
    def get_open_tabs(self) -> List[str]:
        """
        获取Chrome中打开的所有标签页URL
        
        Returns:
            URL列表
        """
        try:
            # 首先尝试使用AppleScript（macOS）
            if platform.system() == "Darwin":
                return self._get_tabs_via_applescript()
            
            # 如果不是macOS或AppleScript失败，尝试使用Selenium
            if not self.driver:
                return []
            
            urls = []
            try:
                # 获取所有窗口句柄
                all_windows = self.driver.window_handles
                
                for window_handle in all_windows:
                    try:
                        self.driver.switch_to.window(window_handle)
                        current_url = self.driver.current_url
                        if current_url and current_url.startswith('http'):
                            urls.append(current_url)
                    except Exception:
                        continue
                        
            except Exception:
                # 如果无法获取窗口句柄，尝试获取当前窗口
                try:
                    current_url = self.driver.current_url
                    if current_url and current_url.startswith('http'):
                        urls.append(current_url)
                except Exception:
                    pass
            
            logger.debug(f"获取到 {len(urls)} 个有效URL: {urls}")
            return urls
            
        except Exception as e:
            logger.error(f"获取标签页失败: {e}")
            return []
    
    def _get_tabs_via_applescript(self) -> List[str]:
        """
        使用AppleScript获取Chrome标签页（仅macOS）
        
        Returns:
            URL列表
        """
        try:
            import subprocess
            
            # 使用AppleScript获取所有标签页URL
            script = '''
            tell application "Google Chrome"
                set tab_urls to {}
                repeat with w in every window
                    repeat with t in every tab of w
                        set tab_url to URL of t
                        if tab_url starts with "http" then
                            set end of tab_urls to tab_url
                        end if
                    end repeat
                end repeat
                return tab_urls
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # 解析AppleScript返回的结果
                urls = []
                for line in result.stdout.strip().split(', '):
                    line = line.strip()
                    if line and line.startswith('http'):
                        urls.append(line)
                
                logger.debug(f"AppleScript获取到 {len(urls)} 个标签页: {urls}")
                return urls
            else:
                logger.debug(f"AppleScript执行失败: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("AppleScript执行超时")
            return []
        except Exception as e:
            logger.debug(f"AppleScript获取标签页失败: {e}")
            return []
    
    def monitor_tabs(self) -> None:
        """监听标签页变化的主循环"""
        logger.info("开始监听Chrome标签页")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_monitoring:
            try:
                # 在AppleScript模式下，不需要检查driver
                if not self.use_applescript and not self.driver:
                    logger.error("Chrome驱动已断开，停止监听")
                    break
                
                # 获取当前打开的标签页
                current_tabs = self.get_open_tabs()
                
                if current_tabs is None:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"连续{max_consecutive_errors}次获取标签页失败，停止监听")
                        break
                    time.sleep(self.monitor_interval)
                    continue
                
                consecutive_errors = 0  # 重置错误计数
                
                # 检查新的标签页
                for url in current_tabs:
                    if url not in self.processed_urls:
                        # 检查是否为有效的小说URL
                        result = self.is_valid_novel_url(url)
                        
                        if result:
                            logger.info(f"检测到有效的小说URL: {url}")
                            
                            # 调用回调函数
                            if self.on_url_detected:
                                try:
                                    self.on_url_detected(result)
                                except Exception as e:
                                    logger.error(f"回调函数执行失败: {e}")
                            
                            # 标记为已处理
                            self.processed_urls.add(url)
                
                # 清理已关闭的标签页URL（可选）
                # 这里可以添加逻辑来清理已关闭标签页的URL
                
                # 等待下次检查
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"监听过程中发生错误 ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("连续错误次数过多，停止监听")
                    break
                    
                time.sleep(self.monitor_interval)
        
        logger.info("Chrome标签页监听已停止")
    
    def start_monitoring(self) -> bool:
        """
        开始监听
        
        Returns:
            是否成功开始监听
        """
        if self.is_monitoring:
            logger.warning("监听已在运行中")
            return False
        
        # 设置Chrome驱动
        if not self.setup_chrome_driver():
            return False
        
        self.is_monitoring = True
        
        # 启动监听线程
        self.monitor_thread = threading.Thread(target=self.monitor_tabs, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Chrome标签页监听已启动")
        return True
    
    def stop_monitoring(self) -> None:
        """停止监听"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        # 等待线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # 只有在非AppleScript模式下才关闭Chrome驱动
        if not self.use_applescript and self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.debug(f"关闭Chrome驱动失败: {e}")
            finally:
                self.driver = None
        
        # 清理已处理的URL
        self.processed_urls.clear()
        
        logger.info("Chrome标签页监听已停止")
    
    def close_tab(self, url: str) -> bool:
        """
        关闭指定URL的标签页
        
        Args:
            url: 要关闭的标签页URL
            
        Returns:
            是否成功关闭
        """
        try:
            if not self.driver:
                return False
            
            # 查找包含指定URL的标签页
            all_windows = self.driver.window_handles.copy()
            
            for window_handle in all_windows:
                try:
                    self.driver.switch_to.window(window_handle)
                    current_url = self.driver.current_url
                    
                    if current_url == url:
                        # 关闭当前标签页
                        self.driver.close()
                        
                        # 切换到剩余的标签页
                        remaining_windows = self.driver.window_handles
                        if remaining_windows:
                            self.driver.switch_to.window(remaining_windows[0])
                        
                        logger.info(f"已关闭标签页: {url}")
                        return True
                        
                except NoSuchWindowException:
                    continue
                except Exception as e:
                    logger.debug(f"关闭标签页时出错: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"关闭标签页失败: {url}, 错误: {e}")
            return False
    
    def is_monitoring_active(self) -> bool:
        """
        检查监听是否活跃
        
        Returns:
            是否正在监听
        """
        return self.is_monitoring and self.monitor_thread and self.monitor_thread.is_alive()
    
    def get_status(self) -> Dict:
        """
        获取监听器状态
        
        Returns:
            状态信息字典
        """
        return {
            'is_monitoring': self.is_monitoring,
            'is_active': self.is_monitoring_active(),
            'processed_urls_count': len(self.processed_urls),
            'chrome_driver_available': self.driver is not None
        }