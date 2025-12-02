"""
17short.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Short17Parser(BaseParser):
    """17short.com 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "17short.com"
    description = "17short.com 小说解析器"
    base_url = "https://17short.com"
    
    # 正则表达式配置 - 标题提取
    title_reg = [
        r"<h1[^>]*>(.*?)</h1>",
        r'<title>(.*?)</title>',
        r'<title>(.*?)\s*\|\s*17短篇</title>'
    ]
    
    # 正则表达式配置 - 内容提取（从section标签中提取）
    content_reg = [
        r"<section[^>]*>(.*?)</section>"
    ]
    
    # 状态正则表达式配置
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型 - 17short.com都是短篇
    book_type = ["短篇"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_17short_content"  # 17short.com特定内容清理
    ]
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
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
                    
                    # 17short.com 特殊编码处理
                    response.encoding = 'utf-8'
                    content = response.text
                    
                    # 如果内容仍然有乱码，尝试其他编码
                    if self._has_encoding_issues(content):
                        logger.warning(f"检测到编码问题，尝试备用编码: {url}")
                        content = self._fix_encoding_issues(response.content)
                    
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
                elif attempt == 1:  # 第二次失败：尝试 selenium
                    try:
                        return self._selenium_request(url, proxies)
                    except Exception as selenium_error:
                        logger.warning(f"selenium也失败: {selenium_error}")
                else:  # 第三次及以后：尝试 playwright
                    try:
                        return self._get_url_content_with_playwright(url, proxies)
                    except Exception as playwright_error:
                        logger.warning(f"playwright也失败: {playwright_error}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"所有反爬虫策略都失败: {url}")
        return None
    
    def _has_encoding_issues(self, content: str) -> bool:
        """
        检测内容是否存在编码问题
        
        Args:
            content: 页面内容
            
        Returns:
            是否存在编码问题
        """
        # 检测常见的编码问题标志
        encoding_issue_markers = [
            '�',  # 替换字符
            'â€',  # UTF-8 错误解码的常见模式
            'â€"', 
            'â€™',
            'â€¦',
            'â€"â€',
            'ï¿½',  # 另一种替换字符
            'Â',  # 常见的UTF-8错误
        ]
        
        for marker in encoding_issue_markers:
            if marker in content:
                return True
        
        # 检查中文字符比例，如果中文字符很少但内容很长，可能是编码问题
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        total_chars = len(content)
        
        # 如果内容超过100字符，但中文字符少于10%，可能是编码问题
        if total_chars > 100 and chinese_chars / total_chars < 0.1:
            return True
            
        return False
    
    def _fix_encoding_issues(self, content_bytes: bytes) -> str:
        """
        修复编码问题
        
        Args:
            content_bytes: 原始字节内容
            
        Returns:
            修复后的文本内容
        """
        # 尝试多种编码
        encodings_to_try = [
            'utf-8',
            'utf-8-sig',  # 带BOM的UTF-8
            'gbk',  # 简体中文
            'gb2312',  # 简体中文
            'gb18030',  # 简体中文
            'big5',  # 繁体中文
            'latin1',  # ISO-8859-1
        ]
        
        for encoding in encodings_to_try:
            try:
                decoded_content = content_bytes.decode(encoding)
                # 验证解码质量
                if not self._has_encoding_issues(decoded_content):
                    logger.info(f"成功使用 {encoding} 编码解码内容")
                    return decoded_content
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 如果所有编码都失败，使用错误处理模式
        logger.warning("所有编码尝试都失败，使用错误处理模式")
        return content_bytes.decode('utf-8', errors='replace')
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配17short.com的URL格式
        
        Args:
            novel_id: 小说ID (格式: 2025/10/13/尿道连通的无尽调教-1-4)
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/{novel_id}/"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，17short.com都是短篇
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型 - 固定返回"短篇"
        """
        return "短篇"
    
    def _clean_17short_content(self, content: str) -> str:
        """
        17short.com特定内容清理
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        import re
        
        # 移除17short.com相关的标识文本
        remove_patterns = [
            r'17短篇',
            r'17short\.com',
            r'(17short\.com)',
            r'更多精彩内容请访问.*?17short\.com',
            r'本文来源.*?17short\.com',
            r'转载请注明.*?17short\.com'
        ]
        
        for pattern in remove_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 移除常见的广告或推广文本
        ad_patterns = [
            r'广告.*?内容',
            r'推广.*?链接',
            r'点击.*?查看更多',
            r'更多.*?请点击',
            r'扫码.*?关注'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 17short.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID - 适配17short.com的URL格式
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 17short.com URL格式: https://17short.com/2025/10/13/尿道连通的无尽调教-1-4/
        # 提取域名后的部分作为ID
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        path = parsed_url.path.rstrip('/')
        
        # 移除开头的斜杠
        if path.startswith('/'):
            path = path[1:]
        
        return path or "unknown"