"""
白胖次小说网解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class BaipangciParser(BaseParser):
    """白胖次小说网解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "白胖次小说网"
    description = "白胖次小说网整本小说爬取解析器"
    base_url = "https://book.baipangci.com"
    
    # 正则表达式配置
    title_reg = [
        r'<li class="active">([^<]+)</li>',
        r'<h1[^>]*class="booktitle"[^>]*>([^<]+)</h1>',
        r'<title>([^_]+)_</title>'
    ]
    
    content_reg = [
        r'<div[^>]*class="readcontent"[^>]*>(.*?)</div>',
        r'<div class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<span class="red">([^<]+)</span>',
        r'状态[:：]\s*(.*?)[<\s]'
    ]
    
    # 内容页内分页相关配置
    content_page_link_reg = [
        r'<a[^>]*class="btn btn-info"[^>]*href="([^"]*)"[^>]*>开始阅读</a>'
    ]
    
    next_page_link_reg = [
        r'<a[^>]*id="linkNext"[^>]*class="btn btn-default"[^>]*href="([^"]*)"[^>]*>下一章</a>'
    ]
    
    # 支持的书籍类型
    book_type = ["多章节", "短篇+多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_special_chars"  # 清理特殊字符
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/index/{novel_id}/"
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 白胖次网站主要是多章节小说
        if "开始阅读" in content and "章节目录" in content:
            return "多章节"
        return "短篇"
    
    def _clean_special_chars(self, content: str) -> str:
        """
        清理特殊字符
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 替换HTML实体和特殊空白字符
        content = content.replace('&emsp;', ' ')
        content = content.replace('&nbsp;', ' ')
        content = content.replace('\xa0', ' ')
        
        # 清理多余的换行和空格
        import re
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'<br\s*/?>', '\n', content)
        
        return content.strip()
    
    def _get_next_page_url(self, content: str, current_url: str) -> Optional[str]:
        """
        获取下一页URL，重写以处理最后一页的特殊情况
        
        Args:
            content: 当前页面内容
            current_url: 当前页面URL
            
        Returns:
            下一页URL或None
        """
        import re
        
        # 使用配置的正则表达式提取下一页链接
        if self.next_page_link_reg:
            for pattern in self.next_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    next_url = match.group(1)
                    
                    # 检查是否是最后一页的特殊链接
                    if "lastchapter.php" in next_url:
                        return None
                    
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
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说
        
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
        if content_page_url.startswith('http'):
            full_content_url = content_page_url
        else:
            full_content_url = f"{self.base_url}{content_page_url}"
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 检查是否有章节列表，如果没有则认为是单章节小说
        chapter_links = self._extract_chapter_links(content)
        if chapter_links:
            # 使用基类方法按章节编号排序
            self._sort_chapters_by_number(chapter_links)
            
            # 抓取所有章节内容
            self._get_all_chapters_from_links(chapter_links, novel_content)
        else:
            # 没有章节列表，使用单一内容页URL
            self._get_all_chapters(full_content_url, novel_content)
        
        return novel_content
    
    def _get_all_chapters(self, start_url: str, novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容
        
        Args:
            start_url: 起始章节URL
            novel_content: 小说内容字典
        """
        import re
        import time
        
        current_url = start_url
        chapter_count = 0
        
        while current_url:
            chapter_count += 1
            logger.info(f"正在爬取第 {chapter_count} 章: {current_url}")
            
            # 获取页面内容
            page_content = self._get_url_content(current_url)
            
            if page_content:
                # 提取章节标题
                chapter_title = self._extract_chapter_title(page_content)
                if not chapter_title:
                    chapter_title = f"第 {chapter_count} 章"
                
                # 提取章节内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)
                
                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': chapter_count,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': current_url
                    })
                    logger.info(f"✓ 第 {chapter_count} 章 [{chapter_title}] 抓取成功")
                else:
                    logger.warning(f"✗ 第 {chapter_count} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {chapter_count} 章页面抓取失败")
            
            # 获取下一章URL
            next_url = self._get_next_page_url(page_content, current_url)
            current_url = next_url
            
            # 章节间延迟
            time.sleep(1)
    
    def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
        """
        提取章节列表链接
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表，每个链接包含title和url
        """
        import re
        
        chapter_links = []
        seen_urls = set()  # 用于去重
        
        # 查找章节链接模式
        patterns = [
            r'<dd><a href="([^"]+)">([^<]+)</a></dd>',
            r'<a[^>]*class="bookchapter"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>(第\d+\s*章[^<]*)</a>',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    url, title = match
                    # 清理标题
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    
                    # 确保URL是完整的
                    if url.startswith('/'):
                        url = f"{self.base_url}{url}"
                    elif not url.startswith('http'):
                        url = f"{self.base_url}/{url.lstrip('/')}"
                    
                    # 跳过非章节链接
                    if 'javascript:' in url or '查看全部章节' in title:
                        continue
                    
                    # 去重：如果URL已经见过，则跳过
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                        
                    # 从URL中提取章节编号
                    chapter_number = self._extract_chapter_number_from_url(url)
                    
                    chapter_links.append({
                        'title': title,
                        'url': url,
                        'chapter_number': chapter_number  # 添加章节编号字段
                    })
        
        # 按URL中的章节编号排序，确保顺序正确
        chapter_links.sort(key=lambda x: x.get('chapter_number', 99999))
        
        return chapter_links
    
    def _extract_chapter_number_from_url(self, url: str) -> int:
        """
        从URL中提取章节编号
        
        Args:
            url: 章节URL
            
        Returns:
            章节编号
        """
        import re
        
        # 尝试从URL中提取章节ID
        # URL格式通常是: https://book.baipangci.com/read/102/16459.html
        # 最后一个数字段可能是章节ID
        id_patterns = [
            r'/(\d+)\.html$',  # 末尾的数字ID
            r'/read/[^/]+/(\d+)\.html',  # read路径中的数字ID
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        # 如果无法从URL提取，尝试从标题提取
        title = ""
        if isinstance(url, dict) and 'title' in url:
            title = url.get('title', '')
        
        return self._extract_chapter_number_from_title(title)
    
    def _get_all_chapters_from_links(self, chapter_links: List[Dict[str, str]], novel_content: Dict[str, Any]) -> None:
        """
        从章节链接列表中抓取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
        """
        import time
        
        # 为了保持章节顺序的连续性，我们使用索引作为章节编号
        # 但实际排序是基于URL中的章节ID
        for i, chapter in enumerate(chapter_links, 1):
            # 优先使用URL中提取的章节编号，否则使用索引+1
            chapter_number = chapter.get('chapter_number', i)
            title = chapter.get('title', f"第 {chapter_number} 章")
            url = chapter.get('url')

            logger.info(f"正在爬取第 {i}/{len(chapter_links)} 章: {title}")
            
            # 获取页面内容
            page_content = self._get_url_content(url)
            
            if page_content:
                # 提取章节内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)
                
                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': chapter_number,
                        'title': title,
                        'content': processed_content,
                        'url': url
                    })
                    logger.info(f"✓ 第 {i}/{len(chapter_links)} 章抓取成功")
                else:
                    logger.warning(f"✗ 第 {i}/{len(chapter_links)} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {i}/{len(chapter_links)} 章页面抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def _extract_chapter_title(self, content: str) -> str:
        """
        提取章节标题
        
        Args:
            content: 页面内容
            
        Returns:
            章节标题
        """
        import re
        
        # 从面包屑导航中提取章节标题
        patterns = [
            r'<li class="active">([^<]+)</li>',
            r'<h1[^>]*class="pt10"[^>]*>([^<]+)</h1>',
            r'<title>[^_]*_([^_]*)_</title>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if title and title not in ["首页", "书库", "排行", "全本", "搜索"]:
                    return title
        
        return ""
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        重写以适配白胖次网站的结构
        
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
        
        # 提取简介
        desc = self._extract_description(content)
        
        # 提取标签
        tags = self._extract_tags(content)
        
        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "desc": desc or "暂无简介",
            "status": status or "未知状态",
            "tags": tags or ""
        }
    
    def _extract_description(self, content: str) -> str:
        """
        提取书籍简介
        
        Args:
            content: 页面内容
            
        Returns:
            书籍简介
        """
        import re
        
        pattern = r'<p[^>]*class="bookintro"[^>]*>(.*?)</p>'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            desc = match.group(1)
            # 清理HTML标签
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.replace('&nbsp;', ' ').replace('\xa0', ' ')
            return desc.strip()
        
        return ""
    
    def _extract_tags(self, content: str) -> str:
        """
        提取书籍标签
        
        Args:
            content: 页面内容
            
        Returns:
            书籍标签（逗号分隔）
        """
        import re
        
        pattern = r'<p[^>]*class="booktag"[^>]*>(.*?)</p>'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            tag_content = match.group(1)
            # 提取所有文本内容，用逗号连接
            tags = []
            text_parts = re.findall(r'>([^<]+)<', tag_content)
            for text in text_parts:
                text = text.strip()
                if text and not text.isdigit() and '万字' not in text and '人读过' not in text:
                    tags.append(text)
            return ', '.join(tags)
        
        return ""
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
        
        # 提取章节列表（子类需要实现 _extract_chapter_links 方法）
        chapter_links = self._extract_chapter_links(content)
        if not chapter_links:
            raise Exception("无法获取章节列表")
        
        # 通过比对URL找到起始位置
        start_pos = 0
        for i, chapter in enumerate(chapter_links):
            chapter_full_url = chapter.get('url', '')
            if chapter_full_url == start_url or (not chapter_full_url.startswith('http') and f"{self.base_url}{chapter_full_url}" == start_url):
                start_pos = i + 1  # 从下一章开始
                break
        
        if start_pos >= len(chapter_links):
            # 没有新章节
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        logger.info(f"从第 {start_pos + 1} 章开始爬取，共 {len(chapter_links) - start_pos} 个新章节")
        
        # 创建小说内容
        novel_content = {
            'title': title or f'书籍-{novel_id}',
            'author': author or self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 从起始位置开始爬取
        self._get_all_chapters_incremental(chapter_links[start_pos:], novel_content, start_index)
        
        return novel_content
    
    def _get_all_chapters_incremental(self, chapter_links, novel_content, start_index=0):
        """
        增量爬取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
            start_index: 起始章节索引
        """
        import time
        
        self.chapter_count = start_index
        
        for i, chapter_info in enumerate(chapter_links, 1):
            chapter_url = chapter_info.get('url', '')
            chapter_title = chapter_info.get('title', f'第{start_index + i}章')
            
            logger.info(f"正在爬取第 {start_index + i} 章: {chapter_title}")
            
            # 获取章节内容
            full_url = f"{self.base_url}{chapter_url}" if chapter_url and not chapter_url.startswith('http') else chapter_url
            chapter_content = self._get_url_content(full_url)
            
            if chapter_content:
                # 使用配置的正则提取内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    self.chapter_count += 1
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': full_url
                    })
                    logger.info(f"✓ 第 {start_index + i} 章抓取成功")
                else:
                    logger.warning(f"✗ 第 {start_index + i} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {start_index + i} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
