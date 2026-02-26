"""
roushuwo.com 小说网站解析器
继承自 BaseParser，使用属性配置实现
"""

import re
import time
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class RoushuwoParser(BaseParser):
    """roushuwo.com 小说解析器"""
    # 网站使用GBK编码
    encoding = "gbk"
    # 基本信息
    name = "roushuwo.com"
    description = "roushuwo.com 小说解析器"
    base_url = "https://www.roushuwo.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="bookTitle"[^>]*>(.*?)</h1>'
    ]
    
    desc_reg = [
        r'<p[^>]*class="text-muted"[^>]*id="bookIntro"[^>]*>(.*?)</p>'
    ]
    
    tags_reg = [
        r'<p[^>]*class="booktag"[^>]*>(.*?)</p>'
    ]
    
    # 支持的书籍类型
    book_type = ["多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_content_specific",  # 特定内容清理
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        # 添加特定的请求头
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        格式: https://www.roushuwo.com/book/{novel_id}.html
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/book/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型
        roushuwo.com 主要是多章节小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "多章节"
    
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
        # 提取书籍ID
        book_id = self._extract_novel_id_from_url(novel_url)
        if not book_id:
            raise Exception("无法提取书籍ID")
        
        # 提取书籍简介
        description = self._extract_with_regex(content, self.desc_reg)
        if description:
            description = self._clean_html_text(description)
        
        # 提取书籍标签
        tags = []
        tags_match = self._extract_with_regex(content, self.tags_reg)
        if tags_match:
            # 从booktag p标签中提取所有子标签内容
            # 使用贪婪模式匹配以确保获取完整内容
            sub_tags = re.findall(r'<[^>]+>(.*?)</[^>]+>', tags_match)
            if sub_tags:
                # 清理每个标签内容并用逗号连接
                tags = [self._clean_html_text(tag).strip() for tag in sub_tags if self._clean_html_text(tag).strip()]
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': book_id,
            'url': novel_url,
            'description': description,
            'tags': ','.join(tags),
            'chapters': []
        }
        
        # 提取章节列表
        chapter_links = self._extract_chapter_links(content)
        
        if not chapter_links:
            logger.warning(f"未找到章节列表，书籍ID: {book_id}")
            return novel_content
        
        # 抓取所有章节内容
        for i, chapter in enumerate(chapter_links):
            try:
                logger.info(f"正在爬取第 {i}/{len(chapter_links)} 章: {chapter['title']}")
                
                # 获取章节内容
                chapter_content = self._get_chapter_content(chapter['url'])
                
                if chapter_content:
                    novel_content['chapters'].append({
                        'title': chapter['title'],
                        'url': chapter['url'],
                        'content': chapter_content
                    })
                    
                    # 添加延迟避免请求过快
                    time.sleep(0.5)
                else:
                    logger.warning(f"无法获取章节内容: {chapter['title']}")
                    
            except Exception as e:
                logger.error(f"抓取章节 {chapter['title']} 时出错: {str(e)}")
                continue
        
        return novel_content
    
    def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
        """
        从内容中提取章节链接
        使用贪婪模式确保获取完整的章节列表
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表，包含标题和URL
        """
        chapters = []
        
        # 使用贪婪模式查找章节列表区域，避免被子div标签截断
        chapter_list_match = re.search(r'<div[^>]*class="panel panel-default"[^>]*id="list-chapterAll"[^>]*>(.*?)</div>\s*(?:<div|</article>|$)', content, re.DOTALL)
        if not chapter_list_match:
            logger.warning("未找到章节列表区域")
            return chapters
        
        chapter_list_html = chapter_list_match.group()
        
        # 提取所有章节链接 - 匹配<dd>标签内的<a>标签
        chapter_matches = re.findall(r'<dd[^>]*class="col-md-3"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>\s*</dd>', chapter_list_html, re.DOTALL)
        
        for href, title, text in chapter_matches:
            # 确保URL是完整的
            if not href.startswith('http'):
                if href.startswith('/'):
                    href = f"{self.base_url}{href}"
                else:
                    href = f"{self.base_url}/{href}"
            
            # 优先使用title属性作为章节标题，如果没有则使用文本内容
            chapter_title = title if title else text
            
            chapters.append({
                'title': chapter_title,
                'url': href
            })
        
        return chapters
    
    def _get_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        获取章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容
        """
        try:
            # 获取章节页面内容
            chapter_html = self._get_url_content(chapter_url)
            if not chapter_html:
                return None
            
            # 提取章节内容 - 使用class="panel-body"和id="htmlContent"的div
            content_match = re.search(r'<div[^>]*class="panel-body"[^>]*id="htmlContent"[^>]*>(.*?)</div>', chapter_html, re.DOTALL)
            if not content_match:
                logger.warning(f"未找到章节内容区域: {chapter_url}")
                return None
            
            chapter_content = content_match.group()
            
            # 执行内容清理
            processed_content = self._execute_after_crawler_funcs(chapter_content)
            
            return processed_content
            
        except Exception as e:
            logger.error(f"获取章节内容时出错: {str(e)}")
            return None
    
    def _clean_html_text(self, html_text: str) -> str:
        """
        清理HTML文本，去除标签和实体
        
        Args:
            html_text: HTML文本
            
        Returns:
            清理后的文本
        """
        if not html_text:
            return ""
        
        # 移除所有HTML标签
        text = re.sub(r'<[^>]+>', '', html_text)
        
        # 处理HTML实体
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'&#39;', "'", text)
        text = re.sub(r'&ldquo;', '"', text)
        text = re.sub(r'&rdquo;', '"', text)
        text = re.sub(r'&lsquo;', "'", text)
        text = re.sub(r'&rsquo;', "'", text)
        text = re.sub(r'&hellip;', '...', text)
        
        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _clean_content_specific(self, content: str) -> str:
        """
        针对roushuwo.com网站的内容清理
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return content
        
        # 移除常见的广告和无关内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<iframe[^>]*>.*?</iframe>', '', content, flags=re.DOTALL)
        
        # 移除所有HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 处理HTML实体
        content = self._clean_html_text(content)
        
        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n+', '\n\n', content)
        content = content.strip()
        
        return content
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
