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
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
        """
        self.session = requests.Session()
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        self.chapter_count = 0
        
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
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        """
        获取URL内容，支持cloudscraper绕过反爬虫限制
        
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
                # 首先尝试普通请求
                response = self.session.get(url, proxies=proxies, timeout=10)
                if response.status_code == 200:
                    response.encoding = 'utf-8'
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
                # 如果普通请求失败，尝试使用cloudscraper
                if attempt == 0:  # 只在第一次失败时尝试cloudscraper
                    try:
                        return self._get_url_content_with_cloudscraper(url, proxies)
                    except Exception as scraper_error:
                        logger.warning(f"cloudscraper也失败: {scraper_error}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"获取URL内容失败: {url}")
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
            
            # 创建cloudscraper会话，使用更强大的配置
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                },
                # 禁用SSL验证以解决可能的SSL错误
                ssl_verify=False,
                # 增加延迟以模拟真实用户行为
                delay=2
            )
            
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
                # 如果备用请求也失败，尝试使用selenium作为最后手段
                return self._selenium_request(url, proxies)
                
        except Exception as e:
            logger.warning(f"备用请求异常: {e}")
            # 如果备用请求异常，也尝试selenium
            return self._selenium_request(url, proxies)
    
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
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        # 替换HTML实体
        clean_text = clean_text.replace('&nbsp;', ' ').replace('\xa0', ' ')
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容
        按顺序尝试每个正则，返回第一个匹配的结果
        
        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        for regex in regex_list:
            match = re.search(regex, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
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
            'author': self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': processed_content,
                'url': novel_url
            }]
        }
    
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
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{counter}.txt')
            counter += 1
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write(f"# {title}\n\n")
            
            # 写入章节内容
            chapters = novel_content.get('chapters', [])
            for chapter in chapters:
                chapter_title = chapter.get('title', '未知章节')
                chapter_content = chapter.get('content', '')
                
                f.write(f"## {chapter_title}\n\n")
                f.write(chapter_content)
                f.write("\n\n")
        
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
            'author': self.name,
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
            'author': self.name,
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