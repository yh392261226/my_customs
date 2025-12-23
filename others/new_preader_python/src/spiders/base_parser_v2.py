"""
书籍网站解析器公共基类 - 配置驱动版本
基于属性配置的灵活解析器架构
"""

import re
import time
import requests
import os
from typing import Dict, Any, List, Optional, Callable
from urllib.parse import urljoin
from src.utils.logger import get_logger
from src.utils.traditional_simplified import convert_traditional_to_simplified

logger = get_logger(__name__)

class BaseParser:
    """书籍网站解析器公共基类 - 配置驱动版本"""
    
    # 子类必须定义的属性
    name: str = "未知解析器"
    description: str = "未知解析器描述"
    base_url: str = ""
    
    # 配置属性 - 子类可以重写这些属性
    title_reg: List[str] = []  # 标题正则表达式列表
    content_reg: List[str] = []  # 内容正则表达式列表
    status_reg: List[str] = []  # 状态正则表达式列表
    book_type: List[str] = ["短篇", "多章节", "短篇+多章节", "内容页内分页"]  # 支持的书籍类型

    # 内容页内分页相关配置
    content_page_link_reg: List[str] = []  # 内容页面链接正则表达式
    next_page_link_reg: List[str] = []  # 下一页链接正则表达式
    
    # 处理函数配置
    after_crawler_func: List[str] = []  # 爬取后处理函数名列表
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
            novel_site_name: 从数据库获取的网站名称，用于作者信息
        """
        self.session = requests.Session()
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        self.chapter_count = 0
        # 保存从数据库获取的网站名称，用于作者信息
        self.novel_site_name = novel_site_name or self.name
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })

    # 繁简转换
    def _convert_traditional_to_simplified(self, text: str) -> str:
        """
        将繁体中文转换为简体中文
        
        Args:
            text: 包含繁体中文的文本
            
        Returns:
            转换为简体中文的文本
        """
        return convert_traditional_to_simplified(text)
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        子类可以重写此方法来自定义URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/b/{novel_id}"
    
    def _get_url_content(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        获取URL内容，支持四层反爬虫绕过策略
        
        策略层级：
        1. 普通请求 (requests)
        2. Cloudscraper 绕过
        3. Selenium 浏览器模拟
        4. Playwright 高级反爬虫处理
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容或None
        """
        proxies = None
        if self.proxy_config.get('enabled', False):
            proxy_url = self.proxy_config.get('proxy_url', '')
            if proxy_url:
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
        
        for attempt in range(max_retries):
            try:
                # 首先尝试普通请求 - 增加超时时间
                response = self.session.get(url, proxies=proxies, timeout=(15, 30))  # 连接15s，读取30s
                if response.status_code == 200:
                    # 检查内容是否为反爬虫页面
                    content = response.text
                    
                    # 检测 Cloudflare Turnstile 等高级反爬虫机制
                    if self._detect_advanced_anti_bot(content):
                        logger.warning(f"检测到高级反爬虫机制，尝试使用 Playwright: {url}")
                        return self._get_url_content_with_playwright(url, proxies)
                    
                    # 优先使用子类指定的编码，如果没有则使用utf-8
                    encoding = getattr(self, 'encoding', 'utf-8')
                    response.encoding = encoding
                    return response.text
                    
                elif response.status_code == 404:
                    logger.warning(f"页面不存在: {url}")
                    return None
                elif response.status_code in [403, 429, 503]:  # 反爬虫相关状态码
                    logger.warning(f"检测到反爬虫限制 (HTTP {response.status_code})，尝试使用cloudscraper: {url}")
                    # 使用cloudscraper绕过反爬虫
                    return self._get_url_content_with_cloudscraper(url, proxies)
                else:
                    logger.warning(f"HTTP {response.status_code} 获取失败: {url}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"第 {attempt + 1} 次请求失败: {url}, 错误: {e}")
                
                # 根据尝试次数选择不同的绕过策略
                if attempt == 0:  # 第一次失败：尝试 cloudscraper
                    try:
                        content = self._get_url_content_with_cloudscraper(url, proxies)
                        if content:
                            return content
                    except Exception as scraper_error:
                        logger.warning(f"cloudscraper也失败: {scraper_error}")
                elif attempt == 1:  # 第二次失败：尝试 playwright
                    try:
                        content = self._get_url_content_with_playwright(url, proxies)
                        if content:
                            return content
                    except Exception as playwright_error:
                        logger.warning(f"playwright也失败: {playwright_error}")
                elif attempt == 2:  # 第三次失败：尝试 selenium
                    try:
                        content = self._selenium_request(url, proxies)
                        if content:
                            return content
                    except Exception as selenium_error:
                        logger.warning(f"selenium也失败: {selenium_error}")
                        # 最后一次尝试，使用普通请求
                        logger.warning(f"尝试普通请求: {url}")
                        try:
                            response = self.session.get(url, proxies=proxies, timeout=(20, 40))
                            if response.status_code == 200:
                                encoding = getattr(self, 'encoding', 'utf-8')
                                response.encoding = encoding
                                return response.text
                        except Exception as final_error:
                            logger.warning(f"最终请求失败: {final_error}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"所有反爬虫策略都失败: {url}")
        return None
    
    def _detect_advanced_anti_bot(self, content: str) -> bool:
        """
        检测是否存在高级反爬虫机制（如 Cloudflare Turnstile）
        
        Args:
            content: 页面内容
            
        Returns:
            是否存在高级反爬虫机制
        """
        try:
            from .playwright_crawler import detect_cloudflare_turnstile_in_content
            return detect_cloudflare_turnstile_in_content(content)
        except ImportError:
            # 如果无法导入 playwright_crawler，使用基本检测
            turnstile_patterns = [
                r'challenges\.cloudflare\.com',
                r'cf-turnstile',
                r'data-sitekey',
                r'turnstile\.cloudflare\.com'
            ]
            
            for pattern in turnstile_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True
            
            return False
    
    def _get_url_content_with_playwright(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        使用 Playwright 获取页面内容，专门处理高级反爬虫机制
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            from .playwright_crawler import get_playwright_content
            
            # 使用 Playwright 获取内容
            return get_playwright_content(url, self.proxy_config, timeout=60, headless=True)
            
        except ImportError:
            logger.warning("playwright 库未安装，无法使用 Playwright 爬虫")
            return None
        except Exception as e:
            logger.warning(f"Playwright 获取页面内容失败: {url}, 错误: {e}")
            return None
    
    def _get_url_content_with_cloudscraper(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        使用cloudscraper绕过反爬虫限制获取URL内容
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            import cloudscraper
            import urllib3
            
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 创建cloudscraper会话，使用更强大的配置
            try:
                # 先创建一个自定义的requests会话，配置好SSL
                import requests
                import ssl
                from requests.adapters import HTTPAdapter
                
                custom_session = requests.Session()
                
                # 创建不验证的SSL上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # 创建自定义适配器，使用我们的SSL上下文
                class SSLAdapter(HTTPAdapter):
                    def init_poolmanager(self, *args, **kwargs):
                        kwargs['ssl_context'] = ssl_context
                        return super().init_poolmanager(*args, **kwargs)
                
                # 应用自定义适配器
                custom_session.mount('https://', SSLAdapter())
                custom_session.verify = False
                
                # 使用自定义会话创建cloudscraper
                scraper = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False
                    },
                    # 增加延迟以模拟真实用户行为
                    delay=2,
                    sess=custom_session  # 使用预配置的会话
                )
                
                # 设置SSL验证 - 先禁用check_hostname再设置verify
                try:
                    # 尝试在scraper对象上设置verify属性
                    scraper.verify = False
                    
                    # 如果有session，需要同时禁用check_hostname
                    if hasattr(scraper, 'session'):
                        session = getattr(scraper, 'session')
                        # 先禁用check_hostname
                        try:
                            if hasattr(session, 'check_hostname'):
                                session.check_hostname = False
                        except Exception as hostname_error:
                            logger.debug(f"无法禁用check_hostname: {hostname_error}")
                        
                        # 尝试在底层SSL上下文中设置
                        try:
                            if hasattr(session, 'ssl_context'):
                                import ssl
                                session.ssl_context.check_hostname = False
                                session.ssl_context.verify_mode = ssl.CERT_NONE
                        except Exception as ssl_context_error:
                            logger.debug(f"无法设置SSL上下文: {ssl_context_error}")
                        
                        # 尝试在底层requests会话上设置
                        try:
                            if hasattr(session, 'requests'):
                                requests_obj = getattr(session, 'requests')
                                if hasattr(requests_obj, 'check_hostname'):
                                    requests_obj.check_hostname = False
                                if hasattr(requests_obj, 'verify'):
                                    requests_obj.verify = False
                        except Exception as requests_error:
                            logger.debug(f"无法在底层requests会话上设置SSL验证: {requests_error}")
                            
                except Exception as verify_error:
                    logger.debug(f"无法设置SSL验证: {verify_error}")
                    # 尝试备用方法：使用urllib3 PoolManager
                    try:
                        import urllib3
                        import ssl
                        from urllib3.util import SSLContext as Urllib3SSLContext
                        
                        # 创建自定义SSL上下文
                        ssl_context = Urllib3SSLContext()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        
                        # 尝试在scraper的session上设置
                        if hasattr(scraper, 'session'):
                            session = getattr(scraper, 'session')
                            if hasattr(session, 'mount'):
                                # 创建自定义PoolManager
                                https_pool = urllib3.PoolManager(
                                    ssl_context=ssl_context,
                                    timeout=urllib3.Timeout(connect=10, read=30)
                                )
                                session.mount('https://', https_pool)
                    except Exception as pool_error:
                        logger.debug(f"无法创建自定义PoolManager: {pool_error}")
                
                # 设置更真实的请求头
                scraper.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Cache-Control': 'max-age=0'
                })
                
                # 设置代理
                if proxies:
                    scraper.proxies = proxies
                
                # 设置更长的超时时间
                response = scraper.get(url, timeout=30)
                
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    logger.info(f"cloudscraper成功绕过反爬虫限制: {url}")
                    return response.text
                else:
                    logger.warning(f"cloudscraper请求失败 (HTTP {response.status_code}): {url}")
                    # 如果cloudscraper也失败，尝试使用requests直接请求但使用不同的User-Agent
                    return self._fallback_request(url, proxies)
                    
            except Exception as scraper_error:
                logger.warning(f"cloudscraper创建失败: {scraper_error}")
                raise  # 重新抛出异常，让外层except处理
        except Exception as e:
            logger.warning(f"cloudscraper创建失败，使用requests: {e}")
            import requests
            import ssl
            import urllib3
            from requests.adapters import HTTPAdapter
            
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            scraper = requests.Session()
            
            # 设置SSL验证 - 确保正确禁用验证
            scraper.verify = False
            
            # 也需要禁用check_hostname
            try:
                # 创建一个不验证的SSL上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # 应用到requests会话
                scraper.mount('https://', HTTPAdapter(
                    max_retries=urllib3.Retry(total=3, backoff_factor=0.1),
                    pool_connections=10,
                    pool_maxsize=10
                ))
                
            except Exception as ssl_error:
                logger.debug(f"无法设置SSL上下文: {ssl_error}")
            
            # 设置更真实的请求头
            scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            })
            
            # 设置代理
            if proxies:
                scraper.proxies = proxies
            
            # 设置更长的超时时间
            response = scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                logger.info(f"cloudscraper成功绕过反爬虫限制: {url}")
                return response.text
            else:
                logger.warning(f"cloudscraper请求失败 (HTTP {response.status_code}): {url}")
                # 如果cloudscraper也失败，尝试使用requests直接请求但使用不同的User-Agent
                return self._fallback_request(url, proxies)
                
        except ImportError:
            logger.warning("cloudscraper库未安装，无法绕过反爬虫限制")
            return self._fallback_request(url, proxies)
        except Exception as e:
            logger.warning(f"cloudscraper请求异常: {e}")
            return self._fallback_request(url, proxies)
    
    def _fallback_request(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        备用请求方法，使用不同的User-Agent和策略
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            # 创建新的会话，使用不同的User-Agent
            fallback_session = requests.Session()
            fallback_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive'
            })
            
            # 禁用SSL验证
            fallback_session.verify = False
            
            # 设置代理
            if proxies:
                fallback_session.proxies = proxies
            
            response = fallback_session.get(url, timeout=15)
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                logger.info(f"备用请求成功: {url}")
                return response.text
            else:
                logger.warning(f"备用请求失败 (HTTP {response.status_code}): {url}")
                return None
                
        except Exception as e:
            logger.warning(f"备用请求异常: {e}")
            return None
    
    def _selenium_request(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        使用selenium + 浏览器指纹伪装作为最后的反爬虫绕过手段
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.common.by import By
            import time
            
            # 配置Chrome选项进行浏览器指纹伪装
            chrome_options = Options()
            
            # 无头模式（可选，根据需求开启）
            # chrome_options.add_argument('--headless')
            
            # 禁用自动化检测
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 浏览器指纹伪装
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # 设置用户代理
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
            
            # 设置窗口大小模拟真实浏览器
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 设置代理
            if proxies:
                proxy_url = proxies.get('http') or proxies.get('https')
                if proxy_url:
                    chrome_options.add_argument(f'--proxy-server={proxy_url}')
            
            # 使用webdriver-manager自动管理ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                # 执行JavaScript脚本进一步伪装
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # 访问目标URL
                driver.get(url)
                
                # 等待页面加载
                time.sleep(10)
                
                # 获取页面源代码
                page_source = driver.page_source
                
                if page_source and len(page_source) > 100:  # 确保有内容
                    logger.info(f"selenium成功获取页面内容: {url}")
                    return page_source
                else:
                    logger.warning(f"selenium获取的页面内容为空或过短: {url}")
                    return None
                    
            except Exception as e:
                logger.warning(f"selenium操作异常: {e}")
                return None
                
            finally:
                # 确保浏览器关闭
                try:
                    driver.quit()
                except:
                    pass
                
        except ImportError:
            logger.warning("selenium库未安装，无法使用浏览器指纹伪装")
            return None
        except Exception as e:
            logger.warning(f"selenium初始化异常: {e}")
            return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容，提取纯文本
        这是公共方法，所有解析器都可以使用
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        import html
        
        # 优先清除所有的<a></a>标签及其内容
        clean_text = re.sub(r'<a[^>]*>.*?</a>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
        # 先移除<style>标签及其内容
        clean_text = re.sub(r'<style[^>]*>.*?</style>', '', clean_text, flags=re.IGNORECASE | re.DOTALL)
        # 移除<script>标签及其内容
        clean_text = re.sub(r'<script[^>]*>.*?</script>', '', clean_text, flags=re.IGNORECASE | re.DOTALL)
        # 移除其他HTML标签
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        # 使用html.unescape解码所有HTML实体
        clean_text = html.unescape(clean_text)
        
        # 替换剩余的特殊空白字符
        clean_text = clean_text.replace('\xa0', ' ')
        
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容
        按顺序尝试每个正则，返回第一个有内容的匹配结果
        
        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        for regex in regex_list:
            matches = re.findall(regex, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted = match.strip() if isinstance(match, str) else match[0].strip() if match else ""
                if extracted:  # 确保内容不是空的
                    return extracted
        return ""
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型（短篇/多章节/内容页内分页）
        子类可以重写此方法来自定义检测逻辑
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检测内容页内分页模式（如87nb网站）
        content_page_patterns = [
            r'开始阅读|开始阅读',
            r'<a[^>]*href="[^"]*ltxs[^"]*"[^>]*>',
            r'<a[^>]*rel="next"[^>]*>下一',
            r'下一章|下一页'
        ]
        
        for pattern in content_page_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "内容页内分页"
        
        # 检测多章节的常见模式
        multi_chapter_patterns = [
            r'章节列表|chapter.*list',
            r'第\s*\d+\s*章',
            r'目录|contents',
            r'<div[^>]*class="[^"]*chapter[^"]*"[^>]*>',
            r'<ul[^>]*class="[^"]*chapters[^"]*"[^>]*>'
        ]
        
        for pattern in multi_chapter_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "多章节"
        
        # 检测短篇的常见模式
        short_story_patterns = [
            r'短篇|short.*story',
            r'单篇|single.*chapter',
            r'全文|full.*text'
        ]
        
        for pattern in short_story_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "短篇"
        
        # 默认返回短篇
        return "短篇"
    
    def _execute_after_crawler_funcs(self, content: str) -> str:
        """
        执行爬取后处理函数
        按照配置顺序执行处理函数
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        processed_content = content
        
        for func_name in self.after_crawler_func:
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                if callable(func):
                    try:
                        processed_content = func(processed_content)
                    except Exception as e:
                        logger.warning(f"执行处理函数 {func_name} 失败: {e}")
        
        return processed_content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页
        子类必须实现此方法
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        raise NotImplementedError("子类必须实现 parse_novel_list 方法")
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        使用配置的正则表达式自动提取
        
        Args:
            novel_id: 小说ID
            
        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            return None
        
        # 自动检测书籍类型
        book_type = self._detect_book_type(content)
        
        # 使用配置的正则提取标题
        title = self._extract_with_regex(content, self.title_reg)
        
        # 使用配置的正则提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "desc": f"{book_type}小说",
            "status": status or "未知状态"
        }
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        根据检测到的书籍类型自动选择处理方式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 自动检测书籍类型
        book_type = self._detect_book_type(content)
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ] - 类型: {book_type}")
        
        # 根据书籍类型选择处理方式
        if book_type == "多章节":
            novel_content = self._parse_multichapter_novel(content, novel_url, title)
        elif book_type == "内容页内分页":
            novel_content = self._parse_content_pagination_novel(content, novel_url, title)
        else:
            novel_content = self._parse_single_chapter_novel(content, novel_url, title)
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """解析单章节小说"""
        # 使用配置的正则提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)
        
        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': processed_content,
                'url': novel_url
            }]
        }
    
    def _extract_chapter_number_from_title(self, title: str) -> int:
        """
        从章节标题中提取章节编号
        
        Args:
            title: 章节标题
            
        Returns:
            章节编号
        """
        # 尝试从标题中提取章节编号
        # 例如: 第1章 美女班長 -> 提取 1
        # 或者: 第一章 美女班長 -> 提取 1
        # 或者: 第3卷 第5章 标题 -> 提取 5
        patterns = [
            r'第(\d+)章',  # 第1章
            r'第(\d+)节',  # 第1节
            r'第(\d+)回',  # 第1回
            r'第(\d+)卷\s*第(\d+)章',  # 第1卷第5章 -> 提取5
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                # 对于"第x卷第y章"模式，我们想要y（章号）
                groups = match.groups()
                return int(groups[-1])  # 取最后一个匹配的数字
        
        # 如果标题中没有明确的章节号，尝试其他方法
        # 例如: "1. 标题" 或 "01 标题"
        general_patterns = [
            r'^(\d+)\.',
            r'^(\d+)\s',
            r'chapter\s*(\d+)',
        ]
        
        for pattern in general_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # 检查特殊章节格式
        # 序章、楔子、前言等通常排在最前面
        special_patterns = [
            (r'序章|序言|引言', 1),
            (r'楔子', 2),
            (r'前言|引子', 3),
            (r'后记|尾声', 99997),
            (r'番外|外传', 99998),
        ]
        
        for pattern, default_num in special_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return default_num
        
        # 如果都找不到，返回一个大数，使其排在最后
        return 99999
    
    def _sort_chapters_by_number(self, chapter_links: List[Dict[str, str]]) -> None:
        """
        按章节编号对章节链接列表进行排序
        
        Args:
            chapter_links: 章节链接列表，会被原地排序
        """
        chapter_links.sort(key=lambda x: self._extract_chapter_number_from_title(x.get('title', '')))
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """解析多章节小说"""
        # 子类必须实现多章节解析逻辑
        raise NotImplementedError("子类必须实现多章节解析逻辑")
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        将小说内容保存到文件
        
        Args:
            novel_content: 小说内容字典
            storage_folder: 存储文件夹
            
        Returns:
            文件路径
        """
        # 确保存储目录存在
        os.makedirs(storage_folder, exist_ok=True)
        
        # 生成文件名（使用标题，避免特殊字符）
        title = novel_content.get('title', '未知标题')
        filename = re.sub(r'[<>:"/\\|?*]', '_', title)
        file_path = os.path.join(storage_folder, f"{filename}.txt")
        
        # 如果文件已存在，添加序号
        # counter = 1
        original_path = file_path
        # 如果文件已经存在, 则增书籍网站名称.
        if os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{self.novel_site_name}.txt')
        # 如果书籍网站名称的文件也存在, 则返回错误
        if os.path.exists(file_path):
            return 'already_exists'
        # while os.path.exists(file_path):
        #     # 文件已经存在的情况, 应该增加的不是序号, 而是网站名称
        #     file_path = original_path.replace('.txt', f'_{counter}.txt')
        #     counter += 1
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write(f"# {title}\n\n")
            
            # 检查小说类型并写入相应内容
            # 1. 多章节小说（包含chapters字段）
            chapters = novel_content.get('chapters', [])
            if chapters:
                for chapter in chapters:
                    chapter_title = chapter.get('title', '未知章节')
                    chapter_content = chapter.get('content', '')
                    
                    f.write(f"## {chapter_title}\n\n")
                    f.write(chapter_content)
                    f.write("\n\n")
            
            # 2. 短篇小说（包含total_content字段）
            elif 'total_content' in novel_content and novel_content['total_content']:
                total_content = novel_content['total_content']
                f.write(f"## {title}\n\n")
                f.write(total_content)
                f.write("\n\n")
            
            # 3. 单页内容（直接使用content字段）
            elif 'content' in novel_content and novel_content['content']:
                content = novel_content['content']
                f.write(f"## {title}\n\n")
                f.write(content)
                f.write("\n\n")
            
            # 4. 如果都没有内容，记录警告
            else:
                logger.warning(f"小说内容为空，仅保存标题: {title}")
        
        logger.info(f"小说已保存到: {file_path}")
        return file_path
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """从URL中提取小说ID"""
        # 默认实现：从URL中提取文件名部分作为ID
        import os
        filename = os.path.basename(url)
        if '.' in filename:
            filename = filename.rsplit('.', 1)[0]
        return filename or "unknown"
    
    def _parse_content_pagination_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析内容页内分页模式的小说（如87nb网站）
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取内容页面链接
        content_page_url = self._extract_content_page_url(content)
        if not content_page_url:
            raise Exception("无法找到内容页面链接")
        
        # 构建完整的内容页面URL
        full_content_url = f"{self.base_url}{content_page_url}"
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容（通过内容页内分页）
        self._get_all_content_pages(full_content_url, novel_content)
        
        return novel_content
    
    def _extract_content_page_url(self, content: str) -> Optional[str]:
        """
        从页面内容中提取内容页面URL
        
        Args:
            content: 页面内容
            
        Returns:
            内容页面URL或None
        """
        # 使用配置的正则表达式提取内容页面链接
        if self.content_page_link_reg:
            for pattern in self.content_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # 默认模式：查找"开始阅读"链接
        patterns = [
            r'<a[^>]*href="([^"]*ltxs[^"]*)"[^>]*>开始阅读</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>开始阅读</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>阅读全文</a>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _get_all_content_pages(self, start_url: str, novel_content: Dict[str, Any]) -> None:
        """
        抓取所有内容页面（通过内容页内分页）
        
        Args:
            start_url: 起始内容页面URL
            novel_content: 小说内容字典
        """
        current_url = start_url
        self.chapter_count = 0
        
        while current_url:
            self.chapter_count += 1
            print(f"正在抓取第 {self.chapter_count} 页: {current_url}")
            
            # 获取页面内容
            page_content = self._get_url_content(current_url)
            
            if page_content:
                # 提取章节内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)
                
                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': f"第 {self.chapter_count} 页",
                        'content': processed_content,
                        'url': current_url
                    })
                    print(f"√ 第 {self.chapter_count} 页抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 页内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 页抓取失败")
            
            # 获取下一页URL
            next_url = self._get_next_page_url(page_content, current_url)
            current_url = next_url
            
            # 页面间延迟
            time.sleep(1)
    
    def _get_next_page_url(self, content: str, current_url: str) -> Optional[str]:
        """
        获取下一页URL
        
        Args:
            content: 当前页面内容
            current_url: 当前页面URL
            
        Returns:
            下一页URL或None
        """
        # 使用配置的正则表达式提取下一页链接
        if self.next_page_link_reg:
            for pattern in self.next_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # 默认模式：查找"下一章"或"下一页"链接
        patterns = [
            r'<a[^>]*rel="next"[^>]*href="([^"]*)"[^>]*>',
            r'<a[^>]*href="([^"]*)"[^>]*>下一[章节页]</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>下一[章节页]</a>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                next_url = match.group(1)
                # 构建完整URL
                if next_url.startswith('/'):
                    return f"{self.base_url}{next_url}"
                elif next_url.startswith('http'):
                    return next_url
                else:
                    # 相对路径处理
                    import os
                    base_dir = os.path.dirname(current_url)
                    return f"{base_dir}/{next_url}"
        
        return None