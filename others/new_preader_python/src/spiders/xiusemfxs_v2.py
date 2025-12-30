"""
XiuSeMFXS 书籍网站解析器
网站: https://fhjz.xiusemfxs.xyz/
书籍详情页格式: https://fhjz.xiusemfxs.xyz/{ID}.html
"""

import re
import time
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class XiuSeMFXSParser(BaseParser):
    """XiuSeMFXS 书籍网站解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 添加针对该网站的特定请求头
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://fhjz.xiusemfxs.xyz/',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })

    # 解析器配置属性
    name = "XiuSeMFXS"
    description = "XiuSeMFXS书籍网站解析器，支持短篇小说爬取"
    base_url = "https://fhjz.xiusemfxs.xyz/"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*>([^<]+)</h1>',  # 标题正则
        r'<title>([^<]+)</title>',  # 备用标题正则
    ]
    
    content_reg = [
        r"<div\s+class=['\"]m1938ing['\"][^>]*>([\s\S]*?)</div>",  # 标准class匹配
        r"<div[^>]*class=['\"][^'\"]*m1938ing[^'\"]*['\"][^>]*>([\s\S]*?)</div>",  # 包含class的匹配
        r'<div[^>]*id="content"[^>]*>([\s\S]*?)</div>',  # 备用id匹配
        r'<div[^>]*class="content"[^>]*>([\s\S]*?)</div>',  # 备用内容正则
    ]
    
    status_reg = [
        r'<span[^>]*class="[^"]*status[^"]*"[^>]*>([^<]+)</span>',  # 状态正则
        r'<span[^>]*>状态[：:]([^<]+)</span>',  # 中文状态正则
    ]
    
    book_type = ["短篇"]  # 该网站主要为短篇小说
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}se-{novel_id}.html"

    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（该网站主要为单篇短篇小说，不需要列表解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # 该网站主要为单篇短篇小说，不需要列表解析
        return []

    def _clean_content(self, content: str) -> str:
        """
        清理小说内容，移除不需要的HTML标签和广告
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return ""
        
        # 移除script标签
        content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', content)
        # 移除style标签
        content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', content)
        # 移除注释
        content = re.sub(r'<!--[\s\S]*?-->', '', content)
        
        # 移除广告相关元素
        content = re.sub(r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>[\s\S]*?</div>', '', content)
        content = re.sub(r'<ins[^>]*>[\s\S]*?</ins>', '', content)
        content = re.sub(r'<iframe[^>]*>[\s\S]*?</iframe>', '', content)
        content = re.sub(r'<a[^>]*href="[^"]*javascript[^"]*"[^>]*>[\s\S]*?</a>', '', content)
        
        # 清理HTML标签，保留必要的换行
        content = re.sub(r'<br\s*/?>', '\n', content)
        content = re.sub(r'<p[^>]*>', '\n', content)
        content = re.sub(r'</p>', '\n', content)
        content = re.sub(r'<div[^>]*>', '\n', content)
        content = re.sub(r'</div>', '\n', content)
        content = re.sub(r'<span[^>]*>', '', content)
        content = re.sub(r'</span>', '', content)
        
        # 移除所有HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理空白字符
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'^\s+', '', content)
        content = re.sub(r'\s+$', '', content)
        
        # 替换HTML实体
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        content = content.replace('&#39;', "'")
        content = content.replace('&#x27;', "'")
        
        # 清理特殊字符
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        return content.strip()

    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容
        
        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        for regex in regex_list:
            match = re.search(regex, content, re.IGNORECASE | re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return extracted
        return ""

    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        
        Args:
            novel_id: 小说ID
            
        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            return None
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        
        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "desc": "短篇小说",  # 该网站主要为短篇小说
            "status": status or "未知状态"
        }

    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ] - 类型: 短篇")
        
        # 提取内容
        novel_content = self._parse_single_chapter_novel(content, novel_url, title)
        
        print(f'[ {title} ] 完成')
        return novel_content

    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析单章节小说（该网站主要为短篇小说）
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说内容字典
        """
        # 提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if not chapter_content:
            # 如果标准正则失败，尝试备用方法
            chapter_content = self._fallback_extract_content(content)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 清理内容
        cleaned_content = self._clean_content(chapter_content)
        
        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': cleaned_content,
                'url': novel_url
            }]
        }
    
    def _fallback_extract_content(self, content: str) -> str:
        """
        备用内容提取方法，当标准正则失败时使用
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容
        """
        # 尝试查找包含内容的div
        patterns = [
            r'<div[^>]*>(.*?)</div>',
            r'<p[^>]*>(.*?)</p>',
            r'<article[^>]*>(.*?)</article>',
            r'<section[^>]*>(.*?)</section>'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                # 检查内容长度是否合理
                text_only = re.sub(r'<[^>]+>', '', match)
                if len(text_only.strip()) > 100:  # 假设有效内容至少100字符
                    return match
        
        return ""

    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型（该网站主要为短篇小说）
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 该网站主要为短篇小说
        return "短篇"
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 从URL中提取ID部分
        match = re.search(r'/([^/]+)\.html$', url)
        if match:
            return match.group(1)
        
        return "unknown"