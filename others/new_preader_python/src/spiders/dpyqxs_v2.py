"""
www.dpyqxs.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
支持内容页内分页模式
"""

import re
import html
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DpyqxsParser(BaseParser):
    """www.dpyqxs.com 小说解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "www.dpyqxs.com"
    description = "www.dpyqxs.com 小说解析器"
    base_url = "https://www.dpyqxs.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1 class="title single">\s*<a[^>]*title="[^"]*">(.*?)</a>\s*</h1>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<article class="page-content-single small single">(.*?)</article>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    status_reg = [
        r'状态[：:]\s*(.*?)[<\n\r]',
        r'status[：:]\s*(.*?)[<\n\r]'
    ]
    
    # 支持的书籍类型
    book_type = ["内容页内分页"]
    
    # 内容页内分页相关配置
    content_page_link_reg = [
        r'<div class="single-nav-links">(.*?)</div>'
    ]
    
    next_page_link_reg = [
        r'<a[^>]*href="([^"]*)"[^>]*class="post-page-numbers"[^>]*>[^<]*</a>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_dpyqxs_content",  # 特定内容清理
        "_clean_html_content"     # 公共基类提供的HTML清理
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        self.novel_site_name = novel_site_name or self.name
        # 添加特定的请求头
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配dpyqxs.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/?p={novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，dpyqxs.com主要是内容页内分页模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检查是否存在分页链接
        if re.search(r'<div[^>]*class="single-nav-links"[^>]*>', content, re.IGNORECASE):
            return "内容页内分页"
        return "内容页内分页"  # 默认返回内容页内分页
    
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
        # 提取书籍ID
        book_id = self._extract_book_id_from_url(novel_url)
        if not book_id:
            raise Exception("无法提取书籍ID")
        
        # 获取所有分页链接
        page_links = self._extract_page_links(content, novel_url)
        if not page_links:
            raise Exception("无法获取分页链接")
        
        print(f"发现 {len(page_links)} 个分页")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': book_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有页面内容
        self._get_all_pages(page_links, novel_content)
        
        return novel_content
    
    def _extract_book_id_from_url(self, url: str) -> Optional[str]:
        """
        从书籍URL中提取书籍ID
        
        Args:
            url: 书籍URL
            
        Returns:
            书籍ID或None
        """
        match = re.search(r'[?&]p=(\d+)', url)
        return match.group(1) if match else None
    
    def _extract_page_links(self, content: str, base_url: str) -> List[str]:
        """
        从页面内容中提取所有分页链接
        
        Args:
            content: 页面内容
            base_url: 基础URL
            
        Returns:
            分页链接列表
        """
        page_links = []
        
        # 首先添加当前页面（第一页）
        page_links.append(base_url)
        
        # 查找分页链接区域
        nav_pattern = r'<div[^>]*class="single-nav-links"[^>]*>(.*?)</div>'
        nav_match = re.search(nav_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if nav_match:
            nav_content = nav_match.group(1)
            logger.debug(f"找到分页导航区域，内容长度: {len(nav_content)}")
            
            # 提取所有分页链接
            page_pattern = r'<a[^>]*href="([^"]*)"[^>]*class="post-page-numbers"[^>]*>[^<]*</a>'
            page_matches = re.findall(page_pattern, nav_content, re.IGNORECASE)
            
            logger.debug(f"找到 {len(page_matches)} 个分页链接")
            
            for href in page_matches:
                # 解码HTML实体
                decoded_href = html.unescape(href)
                
                # 确保URL格式正确
                if decoded_href.startswith('http'):
                    full_url = decoded_href
                elif decoded_href.startswith('/'):
                    full_url = f"{self.base_url}{decoded_href}"
                else:
                    # 相对路径处理
                    import os
                    base_dir = os.path.dirname(base_url)
                    full_url = f"{base_dir}/{decoded_href}"
                
                # 避免重复添加当前页面
                if full_url != base_url and full_url not in page_links:
                    page_links.append(full_url)
        else:
            logger.warning("未找到分页导航区域")
        
        # 如果没有找到其他分页，只返回当前页面
        if len(page_links) == 1:
            logger.info("未找到其他分页，可能为单页小说")
        
        logger.info(f"提取到 {len(page_links)} 个页面链接")
        return page_links
    
    def _get_all_pages(self, page_links: List[str], novel_content: Dict[str, Any]) -> None:
        """
        抓取所有页面内容
        
        Args:
            page_links: 页面链接列表
            novel_content: 小说内容字典
        """
        self.chapter_count = 0
        
        for page_url in page_links:
            self.chapter_count += 1
            
            print(f"正在抓取第 {self.chapter_count} 页: {page_url}")
            
            # 获取页面内容
            page_content = self._get_url_content(page_url)
            
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
                        'url': page_url
                    })
                    print(f"√ 第 {self.chapter_count} 页抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 页内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 页抓取失败")
            
            # 页面间延迟
            import time
            time.sleep(1)
    
    def _clean_dpyqxs_content(self, content: str) -> str:
        """
        清理dpyqxs.com特定的内容干扰
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 首先移除script和style标签及其内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除常见的导航和广告元素
        ad_patterns = [
            r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*single-nav-links[^"]*"[^>]*>.*?</div>',
            # 移除分页数字
            r'<span[^>]*class="[^"]*post-page-numbers[^"]*"[^>]*>.*?</span>',
            r'<a[^>]*class="[^"]*post-page-numbers[^"]*"[^>]*>.*?</a>',
            # 移除可能的广告文本
            r'返回.*?首页',
            r'上一页.*?下一页',
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 清理HTML标签，保留纯文本
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 移除开头和结尾的空行
        content = content.strip()
        
        return content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - dpyqxs.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []