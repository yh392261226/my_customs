"""
ylwx74.xyz 书籍网站解析器
支持短篇和多章节书籍解析
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Ylwx74V2Parser(BaseParser):
    """ylwx74.xyz 书籍网站解析器"""
    
    # 基本信息
    name = "ylwx74解析器"
    description = "ylwx74.xyz 书籍网站解析器"
    base_url = "https://www.ylwx74.xyz"
    
    # 支持的书籍类型
    book_type = ["短篇", "多章节", "短篇+多章节"]
    
    # 标题正则表达式
    title_reg = [
        r'<h1[^>]*>([^<]+)</h1>',
        r'<title[^>]*>([^<]+)</title>'
    ]
    
    # 状态正则表达式
    status_reg = [
        r'<div[^>]*class="fix"[^>]*>([^<]+)</div>',
        r'<div[^>]*class="status"[^>]*>([^<]+)</div>'
    ]
    
    # 简介正则表达式
    desc_reg = [
        r'<div[^>]*class="desc[^"]*"[^>]*>([^<]+)</div>',
        r'<div[^>]*class="description"[^>]*>([^<]+)</div>'
    ]
    
    # 章节列表正则表达式
    chapter_list_reg = [
        r'<ul[^>]*id="section-list"[^>]*class="section-list[^"]*"[^>]*>(.*?)</ul>',
        r'<ul[^>]*class="section-list[^"]*"[^>]*>(.*?)</ul>'
    ]
    
    # 章节链接正则表达式
    chapter_link_reg = [
        r'<li[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>.*?</li>',
        r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>'
    ]
    
    # 内容正则表达式
    content_reg = [
        r'<div[^>]*class="content"[^>]*id="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>'
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/artshow-{novel_id}.html"
    
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
        if status:
            # 清理状态文本，去除多余空格和换行
            status = re.sub(r'\s+', ' ', status).strip()
            # 如果状态包含多个标签，用逗号连接
            if ',' in status:
                status = status.replace(',', '、')
        
        # 提取简介
        desc = self._extract_with_regex(content, self.desc_reg)
        if desc:
            # 清理简介文本
            desc = re.sub(r'\s+', ' ', desc).strip()
        
        return {
            "title": title or "未知标题",
            "desc": desc or "暂无简介",
            "status": status or "未知状态"
        }
    
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
        # 提取章节列表
        chapter_list_html = self._extract_chapter_list(content)
        if not chapter_list_html:
            raise Exception("无法找到章节列表")
        
        # 解析章节信息
        chapters = self._parse_chapter_list(chapter_list_html, novel_url)
        if not chapters:
            raise Exception("无法解析章节列表")
        
        # 抓取每个章节的内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        logger.info(f"开始抓取章节内容，共 {len(chapters)} 章")
        
        for i, chapter in enumerate(chapters, 1):
            logger.info(f"正在爬取第 {i}/{len(chapters)} 章: {chapter['title']}")
            
            # 获取章节内容
            chapter_content = self._get_chapter_content(chapter['url'])
            
            if chapter_content:
                novel_content['chapters'].append({
                    'chapter_number': i,
                    'title': chapter['title'],
                    'content': chapter_content,
                    'url': chapter['url']
                })
                logger.info(f"✓ 第 {i} 章抓取成功")
            else:
                logger.warning(f"✗ 第 {i} 章抓取失败")
            
            # 章节间延迟
            import time
            time.sleep(1)
        
        return novel_content
    
    def _extract_chapter_list(self, content: str) -> Optional[str]:
        """
        从页面内容中提取章节列表HTML
        
        Args:
            content: 页面内容
            
        Returns:
            章节列表HTML或None
        """
        for pattern in self.chapter_list_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        return None
    
    def _parse_chapter_list(self, chapter_list_html: str, base_url: str) -> List[Dict[str, str]]:
        """
        解析章节列表HTML，提取章节信息
        
        Args:
            chapter_list_html: 章节列表HTML
            base_url: 基础URL
            
        Returns:
            章节信息列表
        """
        chapters = []
        
        # 查找所有<li>标签
        li_pattern = r'<li[^>]*>(.*?)</li>'
        li_matches = re.findall(li_pattern, chapter_list_html, re.IGNORECASE | re.DOTALL)
        
        for li_content in li_matches:
            # 在每个<li>中查找<a>标签
            for pattern in self.chapter_link_reg:
                match = re.search(pattern, li_content, re.IGNORECASE)
                if match:
                    href = match.group(1)
                    title = match.group(2)
                    
                    # 清理标题
                    title = re.sub(r'\s+', ' ', title).strip()
                    
                    # 构建完整URL
                    full_url = urljoin(base_url, href)
                    
                    chapters.append({
                        'title': title,
                        'url': full_url
                    })
                    break
        
        return chapters
    
    def _get_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        获取章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容或None
        """
        content = self._get_url_content(chapter_url)
        if not content:
            return None
        
        # 提取章节内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if not chapter_content:
            return None
        
        # 清理内容
        chapter_content = self._clean_chapter_content(chapter_content)
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)
        
        return processed_content
    
    def _clean_chapter_content(self, content: str) -> str:
        """
        清理章节内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 去除&nbsp;等字符
        content = content.replace('&nbsp;', ' ').replace('\xa0', ' ')
        
        # 去除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 清理特殊字符
        content = content.replace('""', '"')
        content = content.replace("''", "'")
        
        return content.strip()
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        content = self._get_url_content(url)
        if not content:
            return []
        
        # 这里可以根据网站的实际列表页结构来实现
        # 由于需求中没有指定列表页结构，这里返回空列表
        return []
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
