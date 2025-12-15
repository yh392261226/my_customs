"""
canovel.com解析器 - 基于配置驱动版本
支持内容页内分页类型小说
"""

import re
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CanovelParser(BaseParser):
    """canovel.com解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "canovel.com"
    description = "canovel.com小说爬取解析器（支持内容页分页类型）"
    base_url = "https://canovel.com"
    
    # 编码配置 - canovel.com使用UTF-8编码
    encoding = "utf-8"
    
    # 正则表达式配置 - 标题提取
    title_reg = [
        r'<h1[^>]*class="post-title entry-title"[^>]*>(.*?)</h1>',
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    # 正则表达式配置 - 内容提取（使用贪婪模式匹配嵌套div）
    content_reg = [
        r'<div[^>]*class="entry-inner"[^>]*>(.*?)</div>\s*<div[^>]*class="'
    ]
    
    status_reg = [
        r'<span[^>]*class="posted-on"[^>]*>(.*?)</span>',
        r'<time[^>]*class="entry-date"[^>]*>(.*?)</time>'
    ]
    
    # 书籍类型配置 - 支持内容页分页
    book_type = ["内容页内分页"]
    
    # 内容页内分页相关配置 - 下一页链接提取
    next_page_link_reg = [
        r'<a[^>]*class="nextpostslink"[^>]*href="([^"]*)"[^>]*>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 先清理HTML
        "_extract_balanced_content",  # 使用平衡算法提取内容
        "_remove_ads",  # 广告移除
        "_convert_traditional_to_simplified" # 繁体转简体
    ]

    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型
        对于canovel.com网站，固定返回"内容页内分页"
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "内容页内分页"
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写解析小说详情方法，直接处理内容页内分页
        对于canovel.com网站，书籍URL直接是内容页
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        # 构建小说URL，例如：https://canovel.com/article/1384
        novel_url = f"{self.base_url}/article/{novel_id}"
        
        # 直接从内容页开始抓取
        return self._parse_content_pagination_novel_direct(novel_url, novel_id)
    
    def _parse_content_pagination_novel_direct(self, start_url: str, novel_id: str) -> Dict[str, Any]:
        """
        直接解析内容页内分页模式的小说
        不需要先获取首页，直接从第一页内容开始
        
        Args:
            start_url: 起始内容页面URL
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        # 获取第一页内容
        content = self._get_url_content(start_url)
        if not content:
            raise Exception(f"无法获取小说页面: {start_url}")
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ] - 类型: 内容页内分页")
        
        # 创建小说内容结构
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': novel_id,
            'url': start_url,
            'chapters': []
        }
        
        # 抓取所有内容页
        self._get_all_content_pages_direct(start_url, novel_content)
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _get_all_content_pages_direct(self, start_url: str, novel_content: Dict[str, Any]) -> None:
        """
        直接抓取所有内容页面（从第一页开始）
        
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
                # 提取内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)
                
                if chapter_content:
                    # 直接使用我们的内容清理方法处理内容
                    processed_content = self._extract_balanced_content(chapter_content)
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(processed_content)
                    
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
            next_url = self._get_next_page_url_direct(page_content, current_url)
            current_url = next_url
            
            # 页面间延迟
            time.sleep(1)
    
    def _get_next_page_url_direct(self, content: str, current_url: str) -> Optional[str]:
        """
        获取下一页URL - 适配canovel.com网站结构
        
        Args:
            content: 当前页面内容
            current_url: 当前页面URL
            
        Returns:
            下一页URL或None
        """
        if not content:
            return None
            
        # 使用配置的正则表达式提取下一页链接
        if self.next_page_link_reg:
            for pattern in self.next_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    next_url = match.group(1)
                    # 构建完整URL
                    if next_url.startswith('http'):
                        return next_url
                    else:
                        return next_url
        
        return None
    
    def _extract_balanced_content(self, content: str) -> str:
        """
        提取平衡的内容，处理嵌套div标签
        使用贪婪模式匹配，确保内容抓取完整
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        # 清理HTML内容
        content = self._clean_html_content(content)
        
        # 找到"🌱 汤米仔优选好站"的位置，截断之后的所有内容
        emoji_pattern = r'🌱 汤米仔优选好站'
        if emoji_pattern in content:
            content = content.split(emoji_pattern)[0]
            content = content.strip()
        
        # 找到"汤米仔优选好站"的位置，截断之后的所有内容
        pattern = r'汤米仔优选好站'
        if pattern in content:
            content = content.split(pattern)[0]
            content = content.strip()
        
        # 移除"🌱"之后的所有内容
        emoji_single_pattern = r'🌱'
        if emoji_single_pattern in content:
            content = content.split(emoji_single_pattern)[0]
            content = content.strip()
        
        # 移除页码和导航信息
        content = re.sub(r'第\s*\d+\s*页\s*/\s*共\s*\d+\s*页', '', content)
        
        # 移除"You may also like"相关内容
        content = re.sub(r'You may also like.*$', '', content, flags=re.MULTILINE | re.DOTALL)
        
        # 移除警告信息
        content = re.sub(r'警告：本网只供18岁以上人士浏览.*$', '', content, flags=re.MULTILINE | re.DOTALL)
        
        # 移除版权信息和友站链接
        content = re.sub(r'© 2025.*?$', '', content, flags=re.MULTILINE | re.DOTALL)
        content = re.sub(r'友站连结.*?$', '', content, flags=re.MULTILINE | re.DOTALL)
        content = re.sub(r'标籤云.*?$', '', content, flags=re.MULTILINE | re.DOTALL)
        
        # 移除"Tags:"之后的内容
        content = re.sub(r'Tags:.*$', '', content, flags=re.MULTILINE | re.DOTALL)
        
        # 移除"Previous story"之后的内容
        content = re.sub(r'Previous story.*$', '', content, flags=re.MULTILINE | re.DOTALL)
        
        # 移除末尾的空格和换行
        content = content.strip()
        
        return content