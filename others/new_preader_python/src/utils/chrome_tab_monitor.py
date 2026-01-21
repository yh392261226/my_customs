"""
Chrome浏览器标签页监控工具 - 修复版本
"""

import re
import subprocess
import time
import threading
from typing import Dict, List, Optional, Any
from urllib.parse import unquote
from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager

logger = get_logger(__name__)

class ChromeTabMonitor:
    """Chrome浏览器标签页监控器"""
    
    def __init__(self, novel_sites=None, on_url_detected=None, headless=True):
        """
        初始化Chrome标签页监控器
        
        Args:
            novel_sites: 网站列表，如果为None则从数据库获取
            on_url_detected: URL检测回调函数
            headless: 是否使用无头模式（AppleScript模式忽略此参数）
        """
        self.db_manager = DatabaseManager()
        self.novel_sites = novel_sites if novel_sites is not None else self.db_manager.get_novel_sites()
        self.on_url_detected = on_url_detected
        self.headless = headless
        self.last_urls = {}  # 记录上次检测的URL，避免重复处理
        self._monitoring_thread = None
        self._stop_monitoring = False
        
    def get_chrome_tabs(self) -> List[Dict[str, Any]]:
        """
        获取Chrome浏览器所有标签页
        
        Returns:
            标签页信息列表
        """
        try:
            # 使用AppleScript获取Chrome标签页
            script = '''
            tell application "Google Chrome"
                if it is running then
                    set window_list to every window
                    set tab_list to {}
                    repeat with current_window in window_list
                        repeat with current_tab in every tab of current_window
                            set tab_info to {url:URL of current_tab, title:title of current_tab}
                            set end of tab_list to tab_info
                        end repeat
                    end repeat
                    return tab_list
                else
                    return {}
                end if
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # 解析AppleScript返回的结果
                output = result.stdout.strip()
                if output and output != '{}':
                    # 解析实际的AppleScript输出格式
                    tabs = []
                    lines = output.split('\n')
                    for line in lines:
                        # AppleScript实际返回格式: URL:..., name:..., URL:..., name:...
                        if 'URL:' in line and 'name:' in line:
                            # 使用正则表达式匹配所有URL和name对
                            url_pattern = r'URL:([^,]+),\s*name:([^,]+)(?:,|$)'
                            matches = re.findall(url_pattern, line)
                            for url, title in matches:
                                url = url.strip()
                                title = title.strip()
                                if url and title:
                                    tabs.append({
                                        'url': url,
                                        'title': title
                                    })
                    return tabs
            
            return []
            
        except Exception as e:
            logger.error(f"获取Chrome标签页失败: {e}")
            return []
    
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
            site_url = site_config.get('url', '')
            
            # 初始化base_url
            if site_url.endswith('.html'):
                # 如果URL以.html结尾，去掉文件名部分
                base_url = site_url.rsplit('/', 1)[0]
            else:
                base_url = site_url.rstrip('/')
            
            # 优先使用url_pattern（数据库中的精确配置）
            if url_pattern:
                # 特殊处理69hnovel.com - 需要精确匹配包含斜杠的ID
                if '69hnovel.com' in site_url and url_pattern == '/erotic-novel/{novel_id}.html':
                    # 69hnovel.com精确匹配：只提取包含斜杠的书籍ID
                    pattern = rf"{re.escape(base_url)}/erotic-novel/([^/?]+)/([^/?]+)\.html"
                    match = re.search(pattern, url)
                    if match:
                        category = unquote(match.group(1))
                        article = unquote(match.group(2))
                        # 确保category和article都不为空，且article包含数字
                        if category and article and re.search(r'\d', article):
                            return f"{category}/{article}"
                    else:
                        return None
                
                # 特殊处理photo-gram.com，避免双斜杠问题
                elif 'photo-gram.com' in site_url and url_pattern == '/read/{novel_id}/':
                    pattern = rf"{re.escape(base_url)}/read/([^/?]+)/"
                    match = re.search(pattern, url)
                    if match:
                        return unquote(match.group(1))
                    else:
                        return None
                
                # 特殊处理po18gg.com和po18rr.com - url_pattern不匹配实际URL格式
                elif ('po18gg.com' in site_url or 'po18rr.com' in site_url) and url_pattern == 'novel/{novel_id}.html':
                    # 实际URL格式：/{dir_id}/{novel_id}/
                    # 其中dir_id是novel_id去掉后3位数字的部分
                    pattern = rf"{re.escape(base_url)}/([^/]+)/([^/?]+)/"
                    match = re.search(pattern, url)
                    if match:
                        # 验证第二部分是否为完整ID
                        potential_dir_id = match.group(1)
                        potential_novel_id = match.group(2)
                        # 检查是否满足po18的ID规则：dir_id + 最后3位数字 = novel_id
                        if (len(potential_novel_id) >= 2 and 
                            potential_novel_id[-3:].isdigit() and 
                            potential_novel_id[:-3] == potential_dir_id):
                            return potential_novel_id
                    else:
                        return None
                
                # 特殊处理cms_t1_v2解析器 - url_pattern不匹配实际URL格式
                elif site_config.get('parser') == 'cms_t1_v2':
                    # cms_t1_v2实际URL格式：{base_url}/{category}/{novel_id}.html
                    pattern = rf"{re.escape(base_url)}/([^/]+)/([^/?]+)\.html"
                    match = re.search(pattern, url)
                    if match:
                        category = unquote(match.group(1))
                        novel_id = unquote(match.group(2))
                        # 确保novel_id是数字（cms_t1_v2通常使用数字ID）
                        if novel_id.isdigit():
                            return novel_id
                    else:
                        return None
                
                # 特殊处理cms_t3_v2解析器 - url_pattern不匹配实际URL格式
                elif site_config.get('parser') == 'cms_t3_v2':
                    # cms_t3_v2支持两种URL格式：
                    # 1. {base_url}/artdetail-{novel_id}.html
                    # 2. {base_url}/index.php/art/detail/id/{novel_id}
                    
                    # 格式1：/artdetail-{novel_id}.html
                    pattern1 = rf"{re.escape(base_url)}/artdetail-([^/?]+)\.html"
                    match1 = re.search(pattern1, url)
                    if match1:
                        novel_id = unquote(match1.group(1))
                        if novel_id.isdigit():
                            return novel_id
                    
                    # 格式2：/index.php/art/detail/id/{novel_id}
                    pattern2 = rf"{re.escape(base_url)}/index\.php/art/detail/id/([^/?]+)"
                    match2 = re.search(pattern2, url)
                    if match2:
                        novel_id = unquote(match2.group(1))
                        if novel_id.isdigit():
                            return novel_id
                    else:
                        return None
                
                # 标准处理：使用url_pattern构建正则表达式
                clean_pattern = url_pattern.replace('{novel_id}', '([^/?]+)')
                
                # 特殊处理91porna.com - base_url包含不匹配的路径
                if '91porna.com' in site_url:
                    # 91porna实际URL格式：https://91porna.com/novels/{novel_id}
                    # 但数据库中的base_url包含/novels/new，导致标准处理失败
                    # 需要使用正确的base_url进行匹配
                    correct_base_url = "https://91porna.com"
                    pattern = rf"{re.escape(correct_base_url)}{clean_pattern}(?:\?[^#]*)?(?:#.*)?$"
                else:
                    # 避免双斜杠问题：如果clean_pattern以/开头，不要在base_url后加/
                    if clean_pattern.startswith('/'):
                        pattern = rf"{re.escape(base_url)}{clean_pattern}(?:\?[^#]*)?(?:#.*)?$"
                    else:
                        pattern = rf"{re.escape(base_url)}/{clean_pattern}(?:\?[^#]*)?(?:#.*)?$"
                
                match = re.search(pattern, url)
                if match:
                    novel_id = unquote(match.group(1))
                    # 对于91porna，确保是数字ID
                    if '91porna.com' in site_url and not novel_id.isdigit():
                        return None
                    return novel_id
            
            # 如果没有url_pattern或不匹配，使用特殊处理逻辑
            # 特殊处理crxs.me网站（没有url_pattern）
            elif 'crxs.me' in site_url:
                pattern = rf"{re.escape(base_url)}/fiction/id-([^/?]+)\.html"
                match = re.search(pattern, url)
                if match:
                    return unquote(match.group(1))
            
            # 特殊处理book18.me网站（没有url_pattern，支持两种格式）
            elif 'book18.me' in site_url:
                # book18.me的两种URL格式
                # 1. 数字ID格式：/article/{数字}
                pattern1 = rf"{re.escape(base_url)}/article/(\d+)"
                match1 = re.search(pattern1, url)
                if match1:
                    return match1.group(1)
                
                # 2. 中文标题格式：/book/{编码后的标题}
                pattern2 = rf"{re.escape(base_url)}/book/([^/?]+)"
                match2 = re.search(pattern2, url)
                if match2:
                    # URL解码得到原始标题
                    return unquote(match2.group(1))
            
            # 特殊处理po18gg.com网站（url_pattern不匹配实际URL格式）
            elif 'po18gg.com' in site_url:
                # po18gg.com实际URL格式：/{dir_id}/{novel_id}/
                # 其中dir_id是novel_id去掉后3位数字的部分
                pattern = rf"{re.escape(base_url)}/([^/]+)/([^/?]+)/"
                match = re.search(pattern, url)
                if match:
                    # 验证第二部分是否为完整ID
                    potential_dir_id = match.group(1)
                    potential_novel_id = match.group(2)
                    # 检查是否满足po18gg的ID规则：dir_id + 最后3位数字 = novel_id
                    if (len(potential_novel_id) >= 2 and 
                        potential_novel_id[-3:].isdigit() and 
                        potential_novel_id[:-3] == potential_dir_id):
                        return potential_novel_id
            
            # 特殊处理po18rr.com网站（url_pattern不匹配实际URL格式）
            elif 'po18rr.com' in site_url:
                # po18rr.com实际URL格式：/{dir_id}/{novel_id}/
                # 其中dir_id是novel_id去掉后3位数字的部分
                pattern = rf"{re.escape(base_url)}/([^/]+)/([^/?]+)/"
                match = re.search(pattern, url)
                if match:
                    # 验证第二部分是否为完整ID
                    potential_dir_id = match.group(1)
                    potential_novel_id = match.group(2)
                    # 检查是否满足po18rr的ID规则：dir_id + 最后3位数字 = novel_id
                    # 支持3位以上或2位数字的ID
                    if (len(potential_novel_id) >= 2 and 
                        potential_novel_id[-3:].isdigit() and 
                        potential_novel_id[:-3] == potential_dir_id):
                        return potential_novel_id
            
            # 特殊处理xbookasd网站（XX小说网）
            elif 'xbookasd.top' in site_url:
                # xbookasd支持两种URL格式：
                # 1. /?novel/detail/{novel_id} (数字ID)
                # 2. /?view_novel/{novel_id} (字符串ID)
                pattern1 = rf"{re.escape(base_url)}/\?novel/detail/([^/?&]+)"
                match1 = re.search(pattern1, url)
                if match1:
                    return unquote(match1.group(1))
                
                pattern2 = rf"{re.escape(base_url)}/\?view_novel/([^/?&]+)"
                match2 = re.search(pattern2, url)
                if match2:
                    return unquote(match2.group(1))
            
            # 特殊处理rouwenwu20网站（新御宅屋）
            elif 'rouwenwu20.com' in site_url:
                # rouwenwu20实际URL格式：/{prefix}_{novel_id}/
                # 其中prefix是novel_id去掉后3位，如果不足1则显示为0
                # 例如：novel_id=90692 -> prefix=90 -> URL=/90_90692/
                pattern = rf"{re.escape(base_url)}/([^/_]+)_([^/?]+)/"
                match = re.search(pattern, url)
                if match:
                    prefix = unquote(match.group(1))
                    potential_novel_id = unquote(match.group(2))
                    # 验证prefix是否正确（应该是potential_novel_id去掉后3位）
                    if len(potential_novel_id) >= 3:
                        expected_prefix = potential_novel_id[:-3]
                        if not expected_prefix:
                            expected_prefix = "0"
                        if prefix == expected_prefix:
                            return potential_novel_id
                    elif len(potential_novel_id) > 0:
                                            # 如果novel_id不足3位，期望的prefix应该是"0"
                                            if prefix == "0":
                                                return potential_novel_id
                                

            
            # 使用默认模式：/b/{novel_id}
            else:
                pattern = rf"{re.escape(base_url)}/b/([^/?]+)"
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
                if not site.get('url'):
                    continue
                
                site_url = site.get('url', '')
                base_url = site_url.rstrip('/')
                
# 特殊处理91porna.com - base_url配置包含/novels/new，但实际小说URL不包含这个路径
                if '91porna.com' in site_url:
                    # 91porna的URL规则：
                    # - https://91porna.com/novels/{数字ID} → 小说页面（提取ID）
                    # - https://91porna.com/novels/{字符串} → 列表页面（不提取ID）
                    if '/novels/' in url and url != 'https://91porna.com/novels/new':
                        # 提取路径中的最后部分
                        path_parts = url.split('/novels/')
                        if len(path_parts) > 1:
                            potential_id = path_parts[1]
                            # 只有当ID是纯数字时才返回（书籍页面）
                            if potential_id.isdigit():
                                return site
                            # 否则是列表页面，不返回
                
                # 检查URL是否包含网站的基础URL
                if base_url in url:
                    # 尝试提取小说ID
                    novel_id = self.extract_novel_id_from_url(url, site)
                    if novel_id:
                        return site
            
            return None
            
        except Exception as e:
            logger.error(f"检查URL有效性失败: {url}, 错误: {e}")
            return None
    
    def monitor_tabs(self, callback=None) -> List[Dict[str, Any]]:
        """
        监控Chrome标签页，查找小说URL
        
        Args:
            callback: 发现小说URL时的回调函数
            
        Returns:
            发现的小说URL列表
        """
        try:
            tabs = self.get_chrome_tabs()
            novel_urls = []
            
            for tab in tabs:
                url = tab.get('url', '')
                title = tab.get('title', '')
                
                # 跳过空URL或重复URL
                if not url or url in self.last_urls.values():
                    continue
                
                # 检查是否为小说URL
                site_config = self.is_valid_novel_url(url)
                if site_config:
                    novel_id = self.extract_novel_id_from_url(url, site_config)
                    if novel_id:
                        novel_info = {
                            'url': url,
                            'title': title,
                            'site_name': site_config.get('name', ''),
                            'novel_id': novel_id,
                            'site_config': site_config
                        }
                        novel_urls.append(novel_info)
                        
                        # 记录URL避免重复处理
                        self.last_urls[site_config.get('name', '')] = url
                        
                        # 调用回调函数（优先使用传入的callback，其次使用实例的on_url_detected）
                        if callback:
                            callback(novel_info)
                        elif self.on_url_detected:
                            self.on_url_detected(novel_info)
            
            return novel_urls
            
        except Exception as e:
            logger.error(f"监控标签页失败: {e}")
            return []
    
    def start_monitoring(self, interval=5, callback=None):
        """
        开始持续监控Chrome标签页（非阻塞）
        
        Args:
            interval: 检查间隔（秒）
            callback: 发现小说URL时的回调函数
            
        Returns:
            bool: 是否成功启动监控
        """
        try:
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                logger.warning("监控已经在运行中")
                return False
            
            self._stop_monitoring = False
            self._monitoring_thread = threading.Thread(
                target=self._monitor_loop,
                args=(interval, callback),
                daemon=True
            )
            self._monitoring_thread.start()
            logger.info(f"开始监控Chrome标签页，检查间隔：{interval}秒")
            return True
            
        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            return False
    
    def _monitor_loop(self, interval, callback):
        """监控循环（在后台线程中运行）"""
        try:
            while not self._stop_monitoring:
                novel_urls = self.monitor_tabs(callback)
                
                if novel_urls:
                    for novel_info in novel_urls:
                        logger.info(f"发现小说URL: {novel_info['url']}, "
                                  f"网站: {novel_info['site_name']}, "
                                  f"小说ID: {novel_info['novel_id']}")
                
                # 使用可中断的sleep
                for _ in range(interval * 10):  # 每0.1秒检查一次停止标志
                    if self._stop_monitoring:
                        break
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"监控过程中出错: {e}")
        finally:
            logger.info("监控线程已停止")
    
    def stop_monitoring(self):
        """停止监控Chrome标签页"""
        try:
            self._stop_monitoring = True
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=2)  # 等待最多2秒
            logger.info("已停止监控Chrome标签页")
            return True
        except Exception as e:
            logger.error(f"停止监控失败: {e}")
            return False
    
    def is_monitoring(self):
        """检查是否正在监控"""
        return self._monitoring_thread and self._monitoring_thread.is_alive()
    
    def test_url_extraction(self, test_urls: List[str]) -> Dict[str, Any]:
        """
        测试URL提取功能
        
        Args:
            test_urls: 测试URL列表
            
        Returns:
            测试结果
        """
        results = {}
        
        for url in test_urls:
            site_config = self.is_valid_novel_url(url)
            if site_config:
                novel_id = self.extract_novel_id_from_url(url, site_config)
                results[url] = {
                    'valid': True,
                    'site_name': site_config.get('name', ''),
                    'novel_id': novel_id
                }
            else:
                results[url] = {
                    'valid': False,
                    'site_name': '',
                    'novel_id': None
                }
        
        return results
    
    def close_tab(self, url: str) -> bool:
        """
        关闭指定URL的Chrome标签页
        
        Args:
            url: 要关闭的标签页URL
            
        Returns:
            是否成功关闭
        """
        try:
            # 使用AppleScript关闭指定URL的标签页
            script = f'''
            tell application "Google Chrome"
                if it is running then
                    set window_list to every window
                    repeat with current_window in window_list
                        repeat with current_tab in every tab of current_window
                            if URL of current_tab is "{url}" then
                                close current_tab
                                return "closed"
                            end if
                        end repeat
                    end repeat
                    return "not_found"
                else
                    return "not_running"
                end if
            end tell
            '''
            
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if output == "closed":
                    logger.info(f"成功关闭标签页: {url}")
                    return True
                elif output == "not_found":
                    logger.warning(f"未找到要关闭的标签页: {url}")
                    return False
                elif output == "not_running":
                    logger.warning("Chrome未运行，无法关闭标签页")
                    return False
                else:
                    logger.warning(f"关闭标签页时收到未知响应: {output}")
                    return False
            else:
                logger.error(f"关闭标签页失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("关闭标签页超时")
            return False
        except Exception as e:
            logger.error(f"关闭标签页异常: {e}")
            return False