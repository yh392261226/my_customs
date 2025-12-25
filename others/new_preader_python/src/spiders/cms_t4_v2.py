"""
CMS T4 小说网站解析器 - 通用成人内容解析版本
适用于使用相同CMS结构的成人内容网站，特征为特殊图片字符替换和GBK编码
"""

import re
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from src.utils.logger import get_logger
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class CmsT4Parser(BaseParser):
    """CMS T4 小说解析器 - 通用成人内容解析版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None, site_url: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
            site_url: 网站URL，用于自动生成base_url
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 初始化实例变量
        self._detected_url_format = None
        self.encoding = "utf-8"  # 默认UTF-8，可在检测后调整为GBK
        
        # 如果提供了site_url，则自动解析并设置base_url
        if site_url:
            self._setup_from_site_url(site_url)
        
        # 添加通用的请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Charset': 'GBK,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        
        # 如果base_url已设置，更新Referer头
        if self.base_url:
            self.session.headers.update({'Referer': self.base_url})
        
        # CMS T4 特有的特殊字符替换映射
        self.char_replacements = {
            '<img src="/zi/n1.png" width="30px" height="28px"/>': '奶',
            '<img src="/zi/d2.png" width="30px" height="28px"/>': '屌',
            '<img src="/zi/r5.png" width="30px" height="28px"/>': '日',
            '<img src="/zi/q1.png" width="30px" height="28px"/>': '情',
            '<img src="/zi/k1.png" width="30px" height="28px"/>': '口',
            '<img src="/zi/n2.png" width="30px" height="28px"/>': '女',
            '<img src="/zi/r3.png" width="30px" height="28px"/>': '人',
            '<img src="/zi/s1.png" width="30px" height="28px"/>': '射',
            '<img src="/zi/j1.png" width="30px" height="28px"/>': '精',
            '<img src="/zi/y1.png" width="30px" height="28px"/>': '液',
            '<img src="/zi/r2.png" width="30px" height="28px"/>': '乳',
            '<img src="/zi/j4.png" width="30px" height="28px"/>': '鸡',
            '<img src="/zi/t1.png" width="30px" height="28px"/>': '头',
            '<img src="/zi/r1.png" width="30px" height="28px"/>': '肉',
            '<img src="/zi/b4.png" width="30px" height="28px"/>': '棒',
            '<img src="/zi/g2.png" width="30px" height="28px"/>': '龟',
            '<img src="/zi/c2.png" width="30px" height="28px"/>': '操',
            '<img src="/zi/c4.png" width="30px" height="28px"/>': '肏',
            '<img src="/zi/g1.png" width="30px" height="28px"/>': '肛',
            '<img src="/zi/c3.png" width="30px" height="28px"/>': '插',
            '<img src="/zi/y2.png" width="30px" height="28px"/>': '淫',
            '<img src="/zi/x1.png" width="30px" height="28px"/>': '穴',
            '<img src="/zi/b2.png" width="30px" height="28px"/>': '暴',
            '<img src="/zi/b3.png" width="30px" height="28px"/>': '屄',
            '<img src="/zi/d3.png" width="30px" height="28px"/>': '洞',
            '<img src="/zi/x2.png" width="30px" height="28px"/>': '性',
            '<img src="/zi/l3.png" width="30px" height="28px"/>': '乱',
            '<img src="/zi/a1.png" width="30px" height="28px"/>': '爱',
            '<img src="/zi/j3.png" width="30px" height="28px"/>': '交',
            '<img src="/zi/p1.png" width="30px" height="28px"/>': '喷',
            '<img src="/zi/c5.png" width="30px" height="28px"/>': '潮',
            '<img src="/zi/b1.png" width="30px" height="28px"/>': '爆',
            '<img src="/zi/f1.png" width="30px" height="28px"/>': '妇',
            '<img src="/zi/j2.png" width="30px" height="28px"/>': '奸',
            '<img src="/zi/n3.png" width="30px" height="28px"/>': '嫩',
            '<img src="/zi/l1.png" width="30px" height="28px"/>': '轮',
            '<img src="/zi/d1.png" width="30px" height="28px"/>': '荡',
            '<img src="/zi/l2.png" width="30px" height="28px"/>': '浪',
            '<img src="/zi/c1.png" width="30px" height="28px"/>': '草',
            '<img src="/zi/j5.png" width="30px" height="28px"/>': '妓',
            '<img src="/zi/b5.png" width="30px" height="28px"/>': '逼',
            '<img src="/zi/g3.png" width="30px" height="28px"/>': '干',
            '<img src="/zi/g4.png" width="30px" height="28px"/>': '股',
            '<img src="/zi/s2.png" width="30px" height="28px"/>': '深',
            '<img src="/zi/f2.png" width="30px" height="28px"/>': '粉',
            '<img src="/zi/r4.png" width="30px" height="28px"/>': '入',
            '<img src="/zi/b6.png" width="30px" height="28px"/>': '巴',
            '<img src="/zi/p3.png" width="30px" height="28px"/>': '屁',
            '<img src="/zi/p2.png" width="30px" height="28px"/>': '破',
            '<img src="/zi/l4.png" width="30px" height="28px"/>': '裸',
            '<img src="/zi/t2.png" width="30px" height="28px"/>': '臀',
        }
        
        # URL格式模式 - 支持多种格式
        self.url_patterns = {
            'po18': {
                'info': '/info/{id}.html',
                'content': '/info/{id}/{page}.html'
            },
            '87nb': {
                'info': '/lt/{id}.html',
                'content': '/ltxs/{id}/{page}.html'
            }
        }
    

    
    def _setup_from_site_url(self, site_url: str) -> None:
        """
        从网站URL自动设置base_url并检测URL格式
        
        Args:
            site_url: 网站URL，如 https://www.example.com/
        """
        logger.info(f"开始从site_url设置base_url: {site_url}")
        
        # 解析URL获取域名
        parsed_url = urlparse(site_url)
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        logger.info(f"设置base_url: {self.base_url}")
        
        # 检测URL格式类型
        domain = parsed_url.netloc.lower()
        if 'po18' in domain:
            self._detected_url_format = 'po18'
            self.encoding = "gbk"  # po18使用GBK编码
            logger.info("检测到po18格式URL，使用GBK编码")
        elif '87nb' in domain:
            self._detected_url_format = '87nb'
            self.encoding = "utf-8"  # 87nb使用UTF-8编码
            logger.info("检测到87nb格式URL，使用UTF-8编码")
        else:
            # 默认使用po18格式
            self._detected_url_format = 'po18'
            self.encoding = "gbk"
            logger.info("使用默认po18格式URL和GBK编码")
        
        # 如果没有提供novel_site_name，使用域名作为名称
        if not self.novel_site_name or self.novel_site_name == self.name:
            self.novel_site_name = parsed_url.netloc
            logger.info(f"设置novel_site_name: {self.novel_site_name}")
    
    @classmethod
    def create_from_site_data(cls, site_data: Dict[str, Any], proxy_config: Optional[Dict[str, Any]] = None):
        """
        从数据库中的网站数据创建解析器实例
        
        Args:
            site_data: 数据库中的网站数据
            proxy_config: 代理配置
            
        Returns:
            解析器实例
        """
        return cls(
            proxy_config=proxy_config,
            novel_site_name=site_data.get('name'),
            site_url=site_data.get('url')
        )
    
    @classmethod
    def create_all_parsers_from_db(cls, db_path: Optional[str] = None):
        """
        从数据库中获取所有CMS T4网站并创建解析器实例
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            
        Returns:
            List[Dict[str, Any]]: 包含网站信息和对应解析器的列表
        """
        from src.core.database_manager import DatabaseManager
        
        # 创建数据库管理器
        db_manager = DatabaseManager(db_path) if db_path else DatabaseManager()
        
        # 获取所有CMS T4网站并创建解析器
        return db_manager.create_cms_t4_parsers()
    
    # 基本信息 - 会被动态设置
    name = "CMS T4 通用解析器"
    description = "CMS T4 通用成人内容解析器，适用于特殊图片字符替换的网站"
    base_url = ""  # 将在初始化时设置
    
    # 正则表达式配置
    title_reg = [
        r'<div class="bookintro">\s*<p[^>]*>\s*<a[^>]*title="([^"]*)"[^>]*>',
        r'<div class="bookintro">\s*<p[^>]*>\s*<a[^>]*>([^<]*)</a>',
        r'<h1[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*id="booktxt"[^>]*>(.*?)</div>',
        r'<div class="booktxt"[^>]*>(.*?)</div>',
        r'<div class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div class="bookdes">\s*<p[^>]*>(.*?)</p>',
        r'小说状态[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_replace_special_chars",  # CMS T4特有的字符替换
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_ads"  # 广告移除
    ]
    
    book_type = ["短篇"]  # 这类网站主要为短篇小说
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL，适配检测到的格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        if not self.base_url:
            logger.error("base_url未设置，无法生成有效的URL")
            raise ValueError("base_url未设置，请在初始化时提供有效的site_url")
        
        if not self._detected_url_format:
            logger.error("未检测到URL格式，无法生成有效的URL")
            raise ValueError("未检测到URL格式，请在初始化时提供有效的site_url")
        
        format_config = self.url_patterns.get(self._detected_url_format, self.url_patterns['po18'])
        info_template = format_config['info']
        
        return f"{self.base_url}{info_template.format(id=novel_id)}"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（CMS T4网站主要为单篇短篇小说，不需要列表解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型（CMS T4网站主要为短篇小说）
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "内容页内分页"
    
    def _extract_content_page_url(self, content: str) -> Optional[str]:
        """
        从页面内容中提取小说内容页面的URL
        
        Args:
            content: 页面内容
            
        Returns:
            内容页面URL或None
        """
        # 根据检测到的格式使用不同的正则表达式
        if self._detected_url_format == 'po18':
            patterns = [
                r'<a href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>',
                r'href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>',
                r'<a href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>'
            ]
        elif self._detected_url_format == '87nb':
            patterns = [
                r'<a href="(/ltxs/\d+/\d+\.html)"[^>]*>开始阅读</a>',
                r'href="(/ltxs/\d+/\d+\.html)"[^>]*>开始阅读</a>'
            ]

        else:
            # 默认使用po18格式
            patterns = [
                r'<a href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>',
                r'href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>'
            ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                logger.info(f"使用模式 '{pattern}' 匹配到内容页URL: {match.group(1)}")
                return match.group(1)
        
        # 备用方法：查找章节列表中的第一个章节链接
        if self._detected_url_format == 'po18':
            first_chapter_pattern = r'<a href="(/info/\d+/\d+\.html)"[^>]*rel="chapter"[^>]*>'
        elif self._detected_url_format == '87nb':
            first_chapter_pattern = r'<a href="(/ltxs/\d+/\d+\.html)"[^>]*rel="chapter"[^>]*>'

        else:
            first_chapter_pattern = r'<a href="(/info/\d+/\d+\.html)"[^>]*rel="chapter"[^>]*>'
        
        first_chapter_match = re.search(first_chapter_pattern, content)
        if first_chapter_match:
            logger.info(f"使用备用模式 '{first_chapter_pattern}' 匹配到内容页URL: {first_chapter_match.group(1)}")
            return first_chapter_match.group(1)
        
        # 如果仍然找不到，打印网页内容的部分信息用于调试
        logger.info(f"无法找到内容页面链接，网页内容预览: {content[:500]}")
        
        # 查找所有可能的链接
        all_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>[^<]*</a>', content)
        html_links = [link for link in all_links if 'html' in link]
        if html_links:
            logger.info(f"找到的包含'html'的链接: {html_links[:5]}")  # 只显示前5个
        
        return None
    
    def _extract_chapter_title(self, content: str) -> str:
        """
        从内容页面提取章节标题
        
        Args:
            content: 页面内容
            
        Returns:
            章节标题
        """
        # 尝试从title标签中提取章节标题 - 先从标题中分离出小说名和章节名
        title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        if title_match:
            full_title = title_match.group(1).strip()
            # 常见的标题格式: "小说名 - 章节名 - 网站" 或 "章节名_小说名_网站" 等
            # 尝试分离出章节名
            chapter_title_patterns = [
                r'^(.+?)\s*[-_]\s*[^-_\s]+(?:小说|正文)?\s*[-_]\s*[^-_\s]+',  # 章节名在前
                r'^[^-\s]+(?:小说|正文)?\s*[-_]\s*(.+?)\s*[-_]\s*[^-_\s]+',  # 章节名在中间
                r'^(.+?)\s*[-_]\s*[^-_\s]+',  # 只有章节名和网站名
                r'^(.+?)\s*[-_]\s*[^-_]*$',  # 只有章节名和小说名
            ]
            
            for pattern in chapter_title_patterns:
                match = re.match(pattern, full_title)
                if match:
                    chapter_title = match.group(1).strip()
                    # 清理可能的页码标记
                    chapter_title = re.sub(r'第\d+页$', '', chapter_title).strip()
                    if chapter_title and chapter_title not in ['首页', '小说', '正文', '目录']:
                        return chapter_title
        
        # h1标签的各种可能形式
        h1_patterns = [
            r'<h1[^>]*>(.*?)</h1>',
            r'<h1[^>]*class="[^"]*"[^>]*>(.*?)</h1>',
            r'<h1[^>]*id="[^"]*"[^>]*>(.*?)</h1>'
        ]
        
        for pattern in h1_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # 清理标题中的HTML标签
                title = re.sub(r'<[^>]+>', '', title)
                # 清理多余的空白字符
                title = re.sub(r'\s+', ' ', title).strip()
                # 清理可能的页码标记
                title = re.sub(r'第\d+页$', '', title).strip()
                
                # 过滤掉一些明显不是标题的内容
                if title and title not in ['首页', '小说', '正文', '目录', '下一页', '上一页']:
                    # 如果标题太短或者太通用，尝试其他模式
                    if len(title) > 1 and not re.match(r'^[0-9]+$', title):
                        return title
        
        return ""
    
    def _replace_special_chars(self, content: str) -> str:
        """
        替换特殊字符 - CMS T4特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        # 替换CMS T4的特殊图片字符
        for old_char, new_char in self.char_replacements.items():
            content = content.replace(old_char, new_char)
        
        return content
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - CMS T4特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        # 移除常见的广告模式
        ad_patterns = [
            r'<div class="ad".*?</div>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _get_url_content(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        获取URL内容，支持多种编码和反爬虫处理
        
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
                    # 根据检测到的编码设置响应编码
                    response.encoding = self.encoding
                    content = response.text
                    
                    # 检测高级反爬虫机制
                    if self._detect_advanced_anti_bot(content):
                        logger.warning(f"检测到高级反爬虫机制，尝试使用 Playwright: {url}")
                        return self._get_url_content_with_playwright(url, proxies)
                    
                    return content
                    
                elif response.status_code == 404:
                    logger.warning(f"页面不存在: {url}")
                    return None
                elif response.status_code in [403, 429, 503]:  # 反爬虫相关状态码
                    logger.warning(f"检测到反爬虫限制 (HTTP {response.status_code})，尝试使用cloudscraper: {url}")
                    # 使用cloudscraper绕过反爬虫
                    return self._get_url_content_with_cloudscraper(url, proxies)
                else:
                    logger.warning(f"HTTP {response.status_code} 获取失败: {url}")
                    
            except Exception as e:
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
                            response = self.session.get(url, proxies=proxies, timeout=20)
                            if response.status_code == 200:
                                response.encoding = self.encoding
                                return response.text
                        except Exception as final_error:
                            logger.warning(f"最终请求失败: {final_error}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"所有反爬虫策略都失败: {url}")
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
            
            # 创建cloudscraper会话，直接使用requests作为fallback
            try:
                # 先创建一个自定义的requests会话，配置好SSL
                import requests
                import ssl
                import urllib3
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
            
            # 设置请求头
            scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Charset': 'GBK,utf-8;q=0.7,*;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            })
            
            # 设置代理
            if proxies:
                scraper.proxies = proxies
            
            response = scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                # 根据检测到的编码设置响应编码
                response.encoding = self.encoding
                logger.info(f"cloudscraper成功绕过反爬虫限制: {url}")
                return response.text
            else:
                logger.warning(f"cloudscraper请求失败 (HTTP {response.status_code}): {url}")
                return None
                
        except ImportError:
            logger.warning("cloudscraper库未安装，无法绕过反爬虫限制")
            return None
        except Exception as e:
            logger.warning(f"cloudscraper请求异常: {e}")
            return None
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现单章节小说解析逻辑 - CMS T4特定实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # CMS T4特殊处理：需要从"开始阅读"链接获取内容
        content_url = self._extract_content_page_url(content)
        
        if not content_url:
            raise Exception("无法找到内容页面链接")
        
        # 构建完整的内容页面URL
        full_content_url = f"{self.base_url}{content_url}"
        
        # 获取内容页面
        content_page = self._get_url_content(full_content_url)
        
        if not content_page:
            raise Exception("无法获取内容页面")
        
        # 从内容页面提取章节标题
        chapter_title = self._extract_chapter_title(content_page)
        
        # 从内容页面提取小说内容
        extracted_content = self._extract_with_regex(content_page, self.content_reg)
        
        if not extracted_content:
            # 尝试备用内容提取模式
            extracted_content = self._extract_content_fallback(content_page)
        
        if not extracted_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(extracted_content)
        
        # 处理章节标题，确保不使用"第1页"这样的标题
        final_chapter_title = chapter_title if chapter_title else title
        # 如果提取的标题是"第1页"或类似页码标记，则使用小说标题
        if final_chapter_title and re.search(r'第\d+页', final_chapter_title):
            final_chapter_title = title
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [
                {
                    'chapter_number': 1,
                    'title': final_chapter_title,
                    'content': processed_content,
                    'url': full_content_url
                }
            ]
        }
        
        return novel_content
    
    def _extract_content_fallback(self, content: str) -> Optional[str]:
        """
        备用内容提取方法 - 当主要正则表达式失败时使用
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容或None
        """
        # 备用模式1：查找包含小说内容的div
        patterns = [
            r'<div[^>]*class="content"[^>]*>(.*?)</div>',
            r'<div[^>]*id="content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="article-content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="text"[^>]*>(.*?)</div>',
            r'<div[^>]*class="txt"[^>]*>(.*?)</div>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        
        # 备用模式2：查找包含大量文本的段落
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        if paragraphs:
            # 选择最长的段落作为内容
            longest_paragraph = max(paragraphs, key=len)
            if len(longest_paragraph.strip()) > 100:  # 确保有足够的内容
                return longest_paragraph
        
        return None
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 根据检测到的URL格式使用不同的正则表达式
        if self._detected_url_format == 'po18':
            match = re.search(r'/info/(\d+)\.html', url)
        elif self._detected_url_format == '87nb':
            match = re.search(r'/lt/(\d+)\.html', url)
        else:
            # 默认使用po18格式
            match = re.search(r'/info/(\d+)\.html', url)
        
        if match:
            return match.group(1)
        
        # 备用方法：从URL路径中提取
        parts = url.split('/')
        for part in parts:
            if part.endswith('.html'):
                return part.replace('.html', '')
        

        
        return "unknown"


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用site_url自动配置
    parser = CmsT4Parser(site_url="https://www.po18.in/")
    
    # 测试单篇小说
    try:
        novel_id = "12345"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")
    
    # 示例2: 从数据库创建所有CMS T4解析器
    print("\n=== 从数据库创建所有CMS T4解析器 ===")
    try:
        parser_sites = CmsT4Parser.create_all_parsers_from_db()
        print(f"已创建 {len(parser_sites)} 个CMS T4解析器")
        
        for site_info in parser_sites:
            site_data = site_info['site_data']
            print(f"- 网站: {site_data.get('name')} ({site_data.get('url')})")
            print(f"  存储文件夹: {site_data.get('storage_folder')}")
            print(f"  代理启用: {site_data.get('proxy_enabled', False)}")
    except Exception as e:
        print(f"从数据库创建解析器失败: {e}")
    
    # 示例3: 使用BaseParser工厂方法创建CMS T4解析器
    print("\n=== 使用BaseParser工厂方法创建CMS T4解析器 ===")
    try:
        from src.core.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        cms_sites = db_manager.get_cms_t4_sites()
        
        if cms_sites:
            site_data = cms_sites[0]  # 使用第一个网站作为示例
            parser = BaseParser.create_cms_t4_parser(site_data)
            print(f"使用工厂方法创建了解析器: {parser.novel_site_name}")
        else:
            print("数据库中没有CMS T4网站")
    except Exception as e:
        print(f"使用工厂方法创建解析器失败: {e}")