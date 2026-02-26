"""
HaijBookx 解析器 - 基于配置驱动版本
网站: https://haijbookx.top/
继承自 BaseParser，使用属性配置实现
"""

import os
import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class HaijBookxParser(BaseParser):
    """HaijBookx 解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "HaijBookx"
    description = "HaijBookx 整本小说爬取解析器"
    base_url = "https://haijbookx.top"
    
    # 编码配置 - HaijBookx 网站使用 GBK 编码
    encoding = "gbk"
    
    # 正则表达式配置
    title_reg = [
        r'<span[^>]*style="font-size:20px;font-weight:bold;color:#f27622;"[^>]*>(.*?)</span>',
        r'<span[^>]*style="font-size:20px;font-weight:bold;color:#f27622;"[^>]*>(.*?)</span>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*id="acontent"[^>]*class="acontent"[^>]*style="font-size: 20px;"[^>]*>(.*?)</div>',
        r'<div[^>]*id="acontent"[^>]*class="acontent"[^>]*>(.*?)</div>',
        r'<div[^>]*class="acontent"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div[^>]*style="line-height:2;"[^>]*>(.*?)</div>',
        r'<div[^>]*class="tags"[^>]*>(.*?)</div>',
        r'<div[^>]*class="tag"[^>]*>(.*?)</div>'
    ]
    
    intro_reg = [
        r'<div[^>]*style="padding:3px;border:0;height:100%;width:100%;overflow-y:scroll;"[^>]*>(.*?)</div>',
        r'<div[^>]*class="intro"[^>]*>(.*?)</div>',
        r'<div[^>]*class="description"[^>]*>(.*?)</div>',
        r'<meta[^>]*name="description"[^>]*content="([^"]*?)"'
    ]
    
    # 章节列表正则
    chapter_link_reg = [
        r'<dd>\s*<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>(.*?)</a>\s*</dd>',
        r'<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>(.*?)</a>',
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
    ]
    
    # 章节标题正则
    chapter_title_reg = [
        r'<div[^>]*class="atitle"[^>]*>(.*?)</div>',
        r'<h1[^>]*>(.*?)</h1>',
        r'<h2[^>]*>(.*?)</h2>',
        r'<title>(.*?)</title>'
    ]
    
    # 书籍类型配置
    book_type = ["多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_replace_br_to_newline"  # 替换<br/>为换行符
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 从数据库获取的网站名称，用于作者信息
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 设置请求头，适配GBK编码
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
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配haijbookx的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/?info/{novel_id}.html"
    
    def get_chapter_url(self, chapter_url: str) -> str:
        """
        构建完整的章节URL
        
        Args:
            chapter_url: 相对章节URL
            
        Returns:
            完整的章节URL
        """
        if chapter_url.startswith('http'):
            return chapter_url
        elif chapter_url.startswith('/'):
            return f"{self.base_url}{chapter_url}"
        else:
            # 相对路径，添加到基础URL后面
            return f"{self.base_url}/{chapter_url}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，haijbookx是多章节小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "多章节"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - haijbookx不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取书籍信息
        novel_info = {
            'title': title,
            'url': novel_url,
            'chapters': [],
            'status': '',
            'description': ''
        }
        
        # 提取简介
        description = self._extract_with_regex(content, self.intro_reg)
        if description:
            novel_info["description"] = description
        
        # 提取状态标签
        status_tags = []
        for status_pattern in self.status_reg:
            matches = re.finditer(status_pattern, content)
            for match in matches:
                # 提取标签文字
                tag_text = match.group(1).strip()
                # 清理HTML标签
                tag_text = re.sub(r'<[^>]+>', '', tag_text)
                # 清理多余空白
                tag_text = re.sub(r'\s+', ' ', tag_text).strip()
                if tag_text and tag_text not in status_tags:
                    status_tags.append(tag_text)
        
        if status_tags:
            novel_info["status"] = ", ".join(status_tags)
        
        # 提取章节列表
        chapters = self._extract_chapters(content)
        
        # 实际爬取每个章节的内容
        for i, chapter in enumerate(chapters, 1):
            logger.info(f"正在爬取第 {i}/{len(chapters if "chapters_info" in content else chapters_info)} 章: {chapter["title"]}")
            
            # 构建完整的章节URL
            chapter_url = self.get_chapter_url(chapter['url'])
            
            # 爬取章节内容
            chapter_content = self.parse_chapter_content(chapter_url)
            
            if chapter_content and chapter_content != "获取章节内容失败" and chapter_content != "未找到章节内容":
                novel_info["chapters"].append({
                    "title": chapter["title"],
                    "url": chapter_url,
                    "order": chapter["order"],
                    "content": chapter_content
                })
                logger.info(f"✓ 第 {i}/{len(chapters)} 章爬取成功")
            else:
                logger.warning(f"✗ 第 {i}/{len(chapters)} 章爬取失败")
                # 即使失败也添加章节信息，但内容为空
                novel_info["chapters"].append({
                    "title": chapter["title"],
                    "url": chapter_url,
                    "order": chapter["order"],
                    "content": ""
                })
            
            # 章节间延迟
            time.sleep(1)
        
        return novel_info
    
    def _extract_chapters(self, content: str) -> List[Dict[str, Any]]:
        """
        从页面内容中提取章节列表
        
        Args:
            content: 页面内容
            
        Returns:
            章节信息列表
        """
        chapters = []
        
        # 查找章节列表区域
        chapter_list_match = re.search(r'<dl[^>]*class="index"[^>]*>(.*?)</dl>', content, re.DOTALL)
        if not chapter_list_match:
            return chapters
        
        chapter_list_content = chapter_list_match.group(1)
        
        # 使用集合来避免重复章节
        seen_urls = set()
        
        # 提取章节链接和标题
        for chapter_pattern in self.chapter_link_reg:
            matches = re.finditer(chapter_pattern, chapter_list_content)
            for match in matches:
                chapter_url = match.group(1).strip()
                chapter_title = match.group(2).strip()
                
                # 清理章节标题中的HTML标签
                chapter_title = re.sub(r'<[^>]+>', '', chapter_title)
                chapter_title = re.sub(r'\s+', ' ', chapter_title).strip()
                
                # 检查是否已经处理过这个URL，避免重复
                if chapter_url not in seen_urls:
                    seen_urls.add(chapter_url)
                    chapters.append({
                        "title": chapter_title,
                        "url": chapter_url,
                        "order": len(chapters) + 1
                    })
        
        return chapters
    
    def parse_chapter_content(self, chapter_url: str) -> str:
        """
        解析章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容文本
        """
        try:
            # 获取章节页面内容
            content = self._get_url_content(chapter_url)
            if not content:
                return "获取章节内容失败"
            
            # 提取内容
            for content_pattern in self.content_reg:
                match = re.search(content_pattern, content, re.DOTALL)
                if match:
                    chapter_content = match.group(1)
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    return processed_content
            
            return "未找到章节内容"
            
        except Exception as e:
            return f"解析章节内容失败: {str(e)}"
    
    def _extract_chapter_title(self, content: str) -> str:
        """
        提取章节标题
        
        Args:
            content: 页面内容
            
        Returns:
            章节标题
        """
        # 使用配置的正则表达式提取章节标题
        for title_pattern in self.chapter_title_reg:
            match = re.search(title_pattern, content)
            if match:
                title = match.group(1).strip()
                # 清理HTML标签
                title = re.sub(r'<[^>]+>', '', title)
                if title:
                    return title
        
        return ""
    
    def _replace_br_to_newline(self, content: str) -> str:
        """
        替换<br/>为换行符
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        # 将<br/>替换为换行符\n
        content = re.sub(r'<br\s*/?>', '\n', content, flags=re.IGNORECASE)
        return content
    
    def _clean_html_content(self, content: str) -> str:
        """
        重写HTML内容清理方法，适配haijbookx的特殊格式
        
        Args:
            content: 原始HTML内容
            
        Returns:
            清理后的文本内容
        """
        # 先调用父类的清理方法
        content = super()._clean_html_content(content)
        
        # 移除HTML实体编码
        import html
        content = html.unescape(content)
        
        # 移除多余的空白字符
        content = ' '.join(content.split())
        
        return content.strip()
    
    def _get_url_content(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        获取URL内容，支持GBK编码处理
        HaijBookx 网站使用GBK编码，需要特殊处理
        
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
                    # HaijBookx 网站使用GBK编码，特殊处理
                    response.encoding = self.encoding
                    content = response.text
                    
                    # 检测 Cloudflare Turnstile 等高级反爬虫机制
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
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"第 {attempt + 1} 次请求失败: {url}, 错误: {e}")
                
                # 根据尝试次数选择不同的绕过策略
                if attempt == 0:  # 第一次失败：尝试 cloudscraper
                    try:
                        return self._get_url_content_with_cloudscraper(url, proxies)
                    except Exception as scraper_error:
                        logger.warning(f"cloudscraper也失败: {scraper_error}")
                elif attempt == 1:  # 第二次失败：尝试 playwright
                    try:
                        return self._get_url_content_with_playwright(url, proxies)
                    except Exception as playwright_error:
                        logger.warning(f"playwright也失败: {playwright_error}")
                elif attempt == 2:  # 第三次失败：尝试 selenium
                    try:
                        return self._selenium_request(url, proxies)
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
        HaijBookx 网站使用GBK编码，需要特殊处理
        
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
            
            # 创建cloudscraper会话
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
            
            except Exception as scraper_error:
                logger.debug(f"cloudscraper创建失败，使用requests: {scraper_error}")
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
                
            # 设置请求头，适配GBK编码
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
                # HaijBookx 网站使用GBK编码，特殊处理
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
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        将小说内容保存到文件，处理GBK编码的文件名
        
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
        
        # 处理GBK编码的标题，转换为UTF-8
        try:
            # 如果标题是GBK编码的字节流，先解码为字符串
            if isinstance(title, bytes):
                title = title.decode('gbk')
            
            # 清理文件名中的特殊字符
            filename = re.sub(r'[<>:"/\\|?*]', '_', title)
            
            # 如果文件名仍然是乱码，尝试GBK到UTF-8转换
            try:
                filename.encode('utf-8')
            except UnicodeEncodeError:
                # 可能是GBK编码的字符串，需要转换
                filename = title.encode('gbk').decode('utf-8', errors='ignore')
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                
        except Exception as e:
            logger.warning(f"文件名编码处理失败: {e}")
            filename = f"haijbookx_novel_{int(time.time())}"
        
        file_path = os.path.join(storage_folder, f"{filename}.txt")
        
        # 如果文件已存在，添加序号
        original_path = file_path
        # 如果文件已经存在, 则增书籍网站名称.
        if os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{self.novel_site_name}.txt')
        # 如果书籍网站名称的文件也存在, 则返回错误
        if os.path.exists(file_path):
            return 'already_exists'
        
        # 写入文件，使用UTF-8编码
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


# 使用示例
if __name__ == "__main__":
    parser = HaijBookxParser()
    
    # 测试单篇小说
    try:
        novel_id = "2820"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
    def parse_novel_detail_incremental(self, novel_id: str, start_url: str, title: str = None, author: str = None, start_index: int = 0) -> Dict[str, Any]:
        """
        增量爬取：从指定章节URL开始继续爬取
        
        Args:
            novel_id: 小说ID
            start_url: 起始章节URL（最后一章的URL）
            title: 小说标题（可选）
            author: 作者（可选）
            start_index: 起始章节索引
            
        Returns:
            小说详情信息
        """
        # 获取小说页面，提取章节列表
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取章节列表（子类需要实现提取方法）
        # 这里尝试提取章节，如果没有则返回空列表
        chapters = []
        
        # 尝试使用正则表达式提取章节
        import re
        chapter_patterns = [
            r'<a[^>]*href=["']([^"']*)["'][^>]*>([^<]+)</a>',
            r'<li[^>]*><a[^>]*href=["']([^"']*)["'][^>]*>([^<]+)</a></li>',
        ]
        
        for pattern in chapter_patterns:
            matches = re.findall(pattern, content)
            if matches:
                chapters = [
                    {'url': match[0], 'title': match[1]}
                    for match in matches
                ]
                break
        
        if not chapters:
            # 无法获取章节列表，返回空结果
            logger.warning("无法获取章节列表，无法进行增量爬取")
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        # 通过比对URL找到起始位置
        start_pos = 0
        for i, chapter in enumerate(chapters):
            chapter_full_url = chapter.get('url', '')
            if chapter_full_url == start_url:
                start_pos = i + 1  # 从下一章开始
                break
        
        if start_pos >= len(chapters):
            # 没有新章节
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        logger.info(f"从第 {start_pos + 1} 章开始爬取，共 {len(chapters) - start_pos} 个新章节")
        
        # 创建小说内容
        novel_content = {
            'title': title or f'书籍-{novel_id}',
            'author': author or self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 从起始位置开始爬取
        for i in range(start_pos, len(chapters)):
            chapter = chapters[i]
            chapter_url = chapter.get('url', '')
            chapter_title = chapter.get('title', f'第{i+1}章')
            
            if not chapter_url:
                continue
            
            # 构建完整URL
            if not chapter_url.startswith('http'):
                chapter_url = f"{self.base_url}{chapter_url}"
            
            logger.info(f"正在爬取第 {i+1} 章: {chapter_title}")
            
            # 获取章节内容
            chapter_content = self._get_url_content(chapter_url)
            
            if chapter_content:
                # 提取章节内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    if processed_content and len(processed_content.strip()) > 0:
                        novel_content['chapters'].append({
                            'chapter_number': start_index + (i - start_pos) + 1,
                            'title': chapter_title,
                            'content': processed_content,
                            'url': chapter_url
                        })
                        logger.info(f"✓ 第 {i+1} 章抓取成功")
                    else:
                        logger.warning(f"✗ 第 {i+1} 章内容处理后为空")
                else:
                    logger.warning(f"✗ 第 {i+1} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {i+1} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
        
        return novel_content
