"""
集芳阁小说网站解析器 - 基于配置驱动版本
支持多章节和单篇小说
"""

import re
import time
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class JisgeParser(BaseParser):
    """集芳阁小说解析器 - 支持多章节和单篇小说"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        # 禁用SSL验证以解决可能的SSL错误
        self.session.verify = False
        # 添加特定的请求头
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    # 基本信息
    name = "集芳阁"
    description = "集芳阁小说解析器"
    base_url = "https://www.xn--1jqvh729avzfcy2d8ummib.com"
    
    # 正则表达式配置
    title_reg = [
        r'<div[^>]*style="text-align:center;clear:both; padding-top: 20px;"[^>]*>(.*?)</div>',
        r'<title>(.*?)[\s\-_]+'
    ]
    
    content_reg = [
        r'<div[^>]*id="bookcontent"[^>]*class="s-tab-main nomal"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型
    book_type = ["短篇", "多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_content_specific",  # 特定内容清理
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配集芳阁的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/contentlist_{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，根据是否包含ul.ucontent来判断
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检测是否包含多章节列表
        if re.search(r'<ul[^>]*class="ucontent"[^>]*>', content, re.IGNORECASE):
            return "多章节"
        else:
            return "短篇"
    
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
        book_id = self._extract_book_id_from_url(novel_url)
        if not book_id:
            raise Exception("无法提取书籍ID")
        
        # 获取章节列表
        chapter_links = self._get_chapter_list(content)
        if not chapter_links:
            raise Exception("无法获取章节列表")
        
        print(f"发现 {len(chapter_links)} 个章节")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': book_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写单章节小说解析逻辑，适配集芳阁的特定结构
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 使用配置的正则提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)
        
        # 检查内容是否有效（至少包含一些中文字符）
        if not processed_content or len(processed_content.strip()) < 50:
            raise Exception("提取的内容为空或过短")
        
        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_book_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': processed_content,
                'url': novel_url
            }]
        }
    
    def _extract_book_id_from_url(self, url: str) -> str:
        """
        从URL中提取书籍ID
        
        Args:
            url: 小说URL
            
        Returns:
            书籍ID
        """
        # 匹配 contentlist_后面的ID
        match = re.search(r'contentlist_([a-f0-9]+)', url)
        return match.group(1) if match else "unknown"
    
    def _get_chapter_list(self, content: str) -> List[Dict[str, str]]:
        """
        从页面内容中提取章节列表
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        chapter_links = []
        
        # 查找ul.ucontent标签
        ul_pattern = r'<ul[^>]*class="ucontent"[^>]*>(.*?)</ul>'
        ul_match = re.search(ul_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if ul_match:
            ul_content = ul_match.group(1)
            
            # 提取每个章节链接 - 适配集芳阁的HTML结构
            chapter_pattern = r'<li[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>.*?<div[^>]*class="title"[^>]*>(.*?)</div>.*?</a>\s*</li>'
            chapter_matches = re.findall(chapter_pattern, ul_content, re.IGNORECASE | re.DOTALL)
            
            for href, title in chapter_matches:
                # 清理标题
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                
                # 构建完整URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = f"{self.base_url}/{href}"
                
                chapter_links.append({
                    'url': full_url,
                    'title': clean_title
                })
        
        logger.info(f"从页面提取到 {len(chapter_links)} 个章节")
        # 使用基类方法按章节编号排序
        self._sort_chapters_by_number(chapter_links)

        return chapter_links
    
    def _get_all_chapters(self, chapter_links: List[Dict[str, str]], novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
        """
        self.chapter_count = 0
        
        for chapter_info in chapter_links:
            self.chapter_count += 1
            chapter_url = chapter_info['url']
            chapter_title = chapter_info['title']
            
            print(f"正在抓取第 {self.chapter_count} 章: {chapter_title}")
            
            # 获取章节内容
            chapter_content = self._get_chapter_content(chapter_url)
            
            if chapter_content:
                novel_content['chapters'].append({
                    'chapter_number': self.chapter_count,
                    'title': chapter_title,
                    'content': chapter_content,
                    'url': chapter_url
                })
                print(f"√ 第 {self.chapter_count} 章抓取成功")
            else:
                print(f"× 第 {self.chapter_count} 章内容抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
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
        
        # 使用配置的正则提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if chapter_content:
            # 执行爬取后处理函数
            processed_content = self._execute_after_crawler_funcs(chapter_content)
            
            # 检查内容是否有效（至少包含一些中文字符）
            if processed_content and len(processed_content.strip()) > 50 and re.search(r'[\u4e00-\u9fff]', processed_content):
                return processed_content
        
        logger.warning(f"无法从章节页面提取有效内容: {chapter_url}")
        return None
    
    def _clean_content_specific(self, content: str) -> str:
        """
        清理集芳阁特定的内容干扰
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 首先移除script和style标签及其内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<a[^>]*>.*?</a>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除特定的来源链接
        # content = re.sub(r'<a[^>]*href="https://xs\.jisge\.com"[^>]*>来源：集芳阁</a>', '', content, flags=re.IGNORECASE)
        
        # 移除常见的导航和广告元素
        ad_patterns = [
            r'上一章.*?下一章',
            r'返回.*?目录',
            r'本章.*?字数',
            r'更新时间.*?\d{4}-\d{2}-\d{2}',
            r'作者.*?更新时间',
            r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',
            r'来源 集书阁.com',
            r'来源 jishuge.one',
            r'来源 jishuge.vip',
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        return content.strip()
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写首页元数据获取，适配集芳阁的特定结构
        
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
        
        # 自动检测书籍类型
        book_type = self._detect_book_type(content)
        
        return {
            "title": title or "未知标题",
            "tags": "",
            "desc": f"{book_type}小说",
            "status": status or "未知状态"
        }
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 集芳阁不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []