"""
18文学网解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import os
import re
import time
import requests
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Po18Parser(BaseParser):
    """18文学网解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "18文学网"
    description = "18文学网整本小说爬取解析器"
    base_url = "https://www.po18.in"
    
    # 编码配置 - PO18网站使用GBK编码
    encoding = "gbk"
    
    # 正则表达式配置 - 与原始版本保持一致
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
        "_replace_special_chars",  # po18特有的字符替换
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_ads"  # 广告移除
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
        
        # po18特殊字符替换映射
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
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配po18的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/info/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，适配po18的特定模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # po18网站使用内容页内分页模式
        return "内容页内分页"
    
    def _extract_content_page_url(self, content: str) -> Optional[str]:
        """
        从页面内容中提取小说内容页面的URL
        
        Args:
            content: 页面内容
            
        Returns:
            内容页面URL或None
        """
        import re
        
        # 查找"开始阅读"链接 - 修复正则表达式匹配
        patterns = [
            r'<a href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>',
            r'href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>',
            r'<a href="(/info/\d+/\d+\.html)"[^>]*>开始阅读</a>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        # 备用方法：查找章节列表中的第一个章节链接
        first_chapter_pattern = r'<a href="(/info/\d+/\d+\.html)"[^>]*rel="chapter"[^>]*>'
        first_chapter_match = re.search(first_chapter_pattern, content)
        if first_chapter_match:
            return first_chapter_match.group(1)
        
        return None
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现单章节小说解析逻辑 - po18特定实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # po18特殊处理：需要从"开始阅读"链接获取内容
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
        # 提取章节链接
        chapter_links = self._extract_chapter_links(content)
        if not chapter_links:
            raise Exception("无法提取章节列表")
        
        print(f"发现 {len(chapter_links)} 个章节")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 使用基类方法按章节编号排序
        self._sort_chapters_by_number(chapter_links)

        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
        """
        提取章节链接列表 - po18特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        # po18是短篇小说网站，没有章节列表
        return []
    
    def _get_all_chapters(self, chapter_links: List[Dict[str, str]], novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
        """
        import time
        
        self.chapter_count = 0
        
        for chapter_info in chapter_links:
            self.chapter_count += 1
            chapter_url = chapter_info['url']
            chapter_title = chapter_info['title']
            
            print(f"正在抓取第 {self.chapter_count} 章: {chapter_title}")
            
            # 获取章节内容
            full_url = f"{self.base_url}{chapter_url}"
            chapter_content = self._get_url_content(full_url)
            
            if chapter_content:
                # 从章节页面提取章节标题
                page_chapter_title = self._extract_chapter_title(chapter_content)
                
                # 使用配置的正则提取内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    # 优先使用从页面提取的标题，如果不存在则使用链接中的标题
                    final_title = page_chapter_title if page_chapter_title else chapter_title
                    
                    # 如果标题是"第1页"或类似页码标记，则使用默认标题
                    if final_title and re.search(r'第\d+页', final_title):
                        final_title = f"第{self.chapter_count}章"
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': final_title,
                        'content': processed_content,
                        'url': full_url
                    })
                    print(f"√ 第 {self.chapter_count} 章抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 章内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def _replace_special_chars(self, content: str) -> str:
        """
        替换特殊字符 - po18特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        # 替换po18的特殊图片字符
        for old_char, new_char in self.char_replacements.items():
            content = content.replace(old_char, new_char)
        
        return content
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - po18特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除po18常见的广告模式
        ad_patterns = [
            r'<div class="ad".*?</div>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题 - po18特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            小说标题
        """
        import re
        
        # 使用配置的正则表达式提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if title:
            return title
        
        # 备用方法：从页面标题中提取
        title_match = re.search(r'<title>(.*?)</title>', content)
        if title_match:
            return title_match.group(1).strip()
        
        return "未知标题"
    
    def _extract_chapter_title(self, content: str) -> str:
        """
        从内容页面提取章节标题
        
        Args:
            content: 页面内容
            
        Returns:
            章节标题
        """
        import re
        
        # 尝试从title标签中提取章节标题 - 先从标题中分离出小说名和章节名
        title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        if title_match:
            full_title = title_match.group(1).strip()
            # 常见的标题格式: "小说名 - 章节名 - 18文学网" 或 "章节名_小说名_18文学网" 等
            # 尝试分离出章节名
            chapter_title_patterns = [
                r'^(.+?)\s*[-_]\s*[^-_\s]+(?:小说|正文)?\s*[-_]\s*18文学网',  # 章节名在前
                r'^[^-_\s]+(?:小说|正文)?\s*[-_]\s*(.+?)\s*[-_]\s*18文学网',  # 章节名在中间
                r'^(.+?)\s*[-_]\s*18文学网',  # 只有章节名和网站名
                r'^(.+?)\s*[-_]\s*[^-_]*$',  # 只有章节名和小说名
            ]
            
            for pattern in chapter_title_patterns:
                match = re.match(pattern, full_title)
                if match:
                    chapter_title = match.group(1).strip()
                    # 清理可能的页码标记
                    chapter_title = re.sub(r'第\d+页$', '', chapter_title).strip()
                    if chapter_title and chapter_title not in ['首页', '小说', '正文', '目录', '18文学网', 'po18']:
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
                if title and title not in ['首页', '小说', '正文', '目录', '下一页', '上一页', '18文学网', 'po18']:
                    # 如果标题太短或者太通用，尝试其他模式
                    if len(title) > 1 and not re.match(r'^[0-9]+$', title):
                        return title
        
        # 其他可能的标题标签
        other_patterns = [
            r'<h2[^>]*>(.*?)</h2>',
            r'<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="[^"]*title[^"]*"[^>]*>(.*?)</div>',
            # 可能包含章节信息的特定结构
            r'<div[^>]*class="[^"]*chapter[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*page[^"]*"[^>]*>(.*?)</div>',
            # 从面包屑导航中提取
            r'<div[^>]*class="[^"]*breadcrumb[^"]*"[^>]*>([^<]+)</div>',
            # 从页面中的特定文本提取
            r'正文\s*([^\s<>]+)',
            r'章节\s*([^\s<>]+)',
        ]
        
        for pattern in other_patterns:
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
                if title and title not in ['首页', '小说', '正文', '目录', '下一页', '上一页', '18文学网', 'po18']:
                    if len(title) > 1 and not re.match(r'^[0-9]+$', title):
                        return title
        
        # 如果所有模式都失败，尝试从页面中查找包含"第"和"章"的文本
        chapter_patterns = [
            r'第[0-9一二三四五六七八九十百千万]+[章回节][^<\s]*',
            r'第[0-9一二三四五六七八九十百千万]+[章回节]\s*[^<]*',
            r'第[0-9一二三四五六七八九十百千万]+页[^<\s]*',
            r'第[0-9一二三四五六七八九十百千万]+话[^<\s]*'
        ]
        
        for pattern in chapter_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                title = match.strip()
                # 清理可能的页码标记
                title = re.sub(r'第\d+页$', '', title).strip()
                if len(title) > 3 and not '第1页' in title:  # 避免返回"第1页"这样的标题
                    return title
        
        return ""
    
    def _extract_content_fallback(self, content: str) -> Optional[str]:
        """
        备用内容提取方法 - 当主要正则表达式失败时使用
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容或None
        """
        import re
        
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
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - po18不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _get_url_content(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        获取URL内容，支持GBK编码处理
        PO18网站使用GBK编码，需要特殊处理
        
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
                    # PO18网站使用GBK编码，特殊处理
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
        PO18网站使用GBK编码，需要特殊处理
        
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
                # PO18网站使用GBK编码，特殊处理
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
            filename = f"po18_novel_{int(time.time())}"
        
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
    parser = Po18Parser()
    
    # 测试单篇小说
    try:
        novel_id = "12345"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")