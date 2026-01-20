"""
小爽文网站解析器
支持 https://chanji-shi.shop/ 网站的小说解析
"""

from src.utils.logger import get_logger
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class ChanjishiParser(BaseParser):

    """小爽文网站解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "小爽文"
    description = "小爽文网站解析器，支持短篇和长篇分页小说"
    base_url = "https://chanji-shi.shop"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*>([^<]+)</h1>',
        r'<title[^>]*>([^<]+)</title>'
    ]
    
    # 内容页正则 - 从<article>标签中提取
    content_reg = [
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>'
    ]
    
    # 分页信息正则
    page_info_reg = [
        r'<div[^>]*class="page_tip"[^>]*>(.*?)</div>',
        r'共(\d+)条数据,当前(\d+)/(\d+)页'
    ]
    
    # 下一页链接正则
    next_page_link_reg = [
        r'<a[^>]*class="page_link"[^>]*href="([^"]*)"[^>]*title="下一页"[^>]*>下一页</a>',
        r'<a[^>]*href="([^"]*)"[^>]*>下一页</a>'
    ]

    # 处理函数配置
    after_crawler_func = [
        "_clean_chapter_content",
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    # 书籍类型配置
    book_type = ["短篇", "多章节", "内容页内分页"]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配小爽文网站的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/index.php/art/detail/id/{novel_id}/page/1.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测方法，专门针对小爽文网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检测分页信息
        page_tip_patterns = [
            r'<div[^>]*class="page_tip"[^>]*>',
            r'共(\d+)条数据,当前(\d+)/(\d+)页'
        ]
        
        for pattern in page_tip_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # 检查页数是否大于1
                page_match = re.search(r'共(\d+)条数据,当前(\d+)/(\d+)页', content)
                if page_match:
                    total_pages = int(page_match.group(3))
                    if total_pages > 1:
                        return "内容页内分页"
                return "短篇"
        
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
        
        # 默认返回短篇
        return "短篇"
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写单章节小说解析方法，支持分页处理
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说内容字典
        """
        # 检测书籍类型
        book_type = self._detect_book_type(content)
        
        if book_type == "内容页内分页":
            # 处理分页小说
            return self._parse_content_pagination_novel(content, novel_url, title)
        else:
            # 处理单页短篇小说
            return super()._parse_single_chapter_novel(content, novel_url, title)
    
    def _parse_content_pagination_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析内容页内分页模式的小说
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,  # 使用数据库中的网站名称
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有页面内容
        self._get_all_content_pages(novel_url, novel_content)
        
        return novel_content
    
    def _get_all_content_pages(self, start_url: str, novel_content: Dict[str, Any]) -> None:
        """
        抓取所有内容页面（通过内容页内分页）
        
        Args:
            start_url: 起始内容页面URL
            novel_content: 小说内容字典
        """
        current_url = start_url
        self.chapter_count = 0
        
        # 记录已经处理过的URL，避免无限循环
        processed_urls = set()
        
        while current_url and current_url not in processed_urls:
            processed_urls.add(current_url)
            self.chapter_count += 1
            logger.info(f"正在爬取第 {self.chapter_count} 页: {current_url}")
            
            # 获取页面内容
            page_content = self._get_url_content(current_url)
            
            if page_content:
                # 提取章节内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)
                
                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    
                    # 清理内容
                    cleaned_content = self._clean_chapter_content(processed_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': f"第 {self.chapter_count} 页",
                        'content': cleaned_content,
                        'url': current_url
                    })
                    logger.info(f"✓ 第 {self.chapter_count} 页抓取成功")
                else:
                    logger.warning(f"✗ 第 {self.chapter_count} 页内容提取失败")
                    
                # 获取下一页URL
                next_url = self._get_next_page_url(page_content, current_url)
                
                # 如果下一页URL与当前页相同，则停止
                if next_url == current_url:
                    logger.info("下一页URL与当前页相同，停止抓取")
                    break
                    
                current_url = next_url
            else:
                logger.warning(f"✗ 第 {self.chapter_count} 页抓取失败")
                break
            
            # 页面间延迟
            import time
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
                    next_url = match.group(1).strip()
                    
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
        
        # 检查分页信息，如果没有下一页链接但有多个页面，尝试构造下一页URL
        page_info_match = re.search(r'共(\d+)条数据,当前(\d+)/(\d+)页', content)
        if page_info_match:
            current_page = int(page_info_match.group(2))
            total_pages = int(page_info_match.group(3))
            
            if current_page < total_pages:
                # 尝试构造下一页URL
                next_page = current_page + 1
                # 从当前URL中提取基础路径并构造下一页URL
                base_pattern = r'(/index\.php/art/detail/id/\d+/)(?:page/\d+\.html)?'
                match = re.search(base_pattern, current_url)
                if match:
                    base_path = match.group(1)
                    return f"{self.base_url}{base_path}page/{next_page}.html"
        
        return None
    
    def _clean_chapter_content(self, content: str) -> str:
        """
        清理章节内容，专门针对小爽文网站
        
        Args:
            content: 原始章节内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return ""
        
        # 首先移除所有HTML标签，包括自闭合标签
        cleaned = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余的空格和换行
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 恢复段落格式 - 将连续的换行合并为单个换行
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        
        # 清理开头和结尾的空格
        cleaned = cleaned.strip()
        
        # 去掉可能的广告文字
        cleaned = re.sub(r'(本站|小爽文|最新精品小说).*?(版权所有|Power by)', '', cleaned)
        
        # 去除特殊字符和多余的空行
        cleaned = re.sub(r'^\s*[\r\n]+', '', cleaned)  # 去除开头的空行
        cleaned = re.sub(r'[\r\n]+\s*$', '', cleaned)  # 去除结尾的空行
        
        return cleaned
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题
        
        Args:
            content: 页面内容
            
        Returns:
            提取的标题
        """
        # 使用配置的正则表达式列表提取标题
        for pattern in self.title_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # 清理标题中的HTML标签
                title = re.sub(r'<[^>]+>', '', title)
                return title
        
        # 如果正则表达式匹配失败，尝试默认的h1标签提取
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            title = re.sub(r'<[^>]+>', '', title)
            return title
        
        return ""
    
    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容
        
        Args:
            content: 页面内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        for pattern in regex_list:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        重写从URL中提取小说ID的方法
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 从小爽文网站的URL中提取ID
        # 格式: /index.php/art/detail/id/17777/page/1.html
        match = re.search(r'/index\.php/art/detail/id/(\d+)/', url)
        if match:
            return match.group(1)
        
        # 如果无法提取，使用默认方法
        return super()._extract_novel_id_from_url(url)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（暂未实现）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # 待实现
        return []