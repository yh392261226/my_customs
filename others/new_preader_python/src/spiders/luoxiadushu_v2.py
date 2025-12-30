"""
落霞读书 (luoxiadushu.com) 小说网站解析器
基于配置驱动版本，继承自 BaseParser
"""

from typing import Dict, Any, List, Optional
import re
import time
from urllib.parse import urljoin, urlparse
from .base_parser_v2 import BaseParser

class Kunnu8Parser(BaseParser):
    """落霞读书 (luoxiadushu.com) 小说解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 落霞读书使用UTF-8编码
        self.encoding = 'utf-8'
    
    # 基本信息
    name = "落霞读书"
    description = "luoxiadushu.com 小说解析器，支持多章节多部小说"
    base_url = "https://luoxiadushu.com/"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*>([^<]+)</h1>',
        r'<title>([^<]+)_[^<]+</title>',
        r'<meta property="og:title" content="([^"]+)"'
    ]
    
    content_reg = [
        r'<div id="nr1"[^>]*>(.*?)</div>',
        r'<div class="content"[^>]*>(.*?)</div>',
        r'<div id="content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'<div class="status"[^>]*>(.*?)</div>',
        r'<meta property="og:novel:status" content="([^"]+)"'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        生成小说详情页URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情页URL
        """
        return f"{self.base_url}{novel_id}/"
    
    def _extract_volume_list(self, content: str) -> List[Dict[str, Any]]:
        """
        从HTML内容中提取分部信息
        
        Args:
            content: 页面HTML内容
            
        Returns:
            分部信息列表
        """
        volumes = []
        
        # 查找所有分部标题
        volume_pattern = r'<div class="title clearfix">\s*<h3[^>]*class="acin"[^>]*>\s*<a[^>]*title="([^"]+)"[^>]*href="([^"]+)">([^<]+)</a>\s*</h3>\s*</div>'
        volume_matches = re.findall(volume_pattern, content, re.DOTALL)
        
        for i, (title, url, text) in enumerate(volume_matches):
            volume_info = {
                'title': title,
                'url': urljoin(self.base_url, url),
                'text': text,
                'order': i + 1
            }
            volumes.append(volume_info)
        
        return volumes
    
    def _extract_chapter_list(self, content: str) -> List[Dict[str, Any]]:
        """
        从HTML内容中提取章节列表
        
        Args:
            content: 页面HTML内容
            
        Returns:
            章节信息列表
        """
        chapters = []
        chapter_order = 0
        
        # 首先尝试提取有分部的章节列表
        # 查找所有分部及其对应的章节列表
        volume_sections = re.finditer(r'<div class="title clearfix">.*?</h3>.*?</div>\s*(<div class="book-list clearfix">.*?</div>)', content, re.DOTALL)
        has_volume_sections = False
        
        for volume_match in volume_sections:
            has_volume_sections = True
            chapter_list_html = volume_match.group(1)
            
            # 提取当前分部的标题
            volume_section = volume_match.group(0)
            volume_title_match = re.search(r'<h3[^>]*class="acin"[^>]*>\s*<a[^>]*title="([^"]+)"', volume_section)
            volume_title = volume_title_match.group(1) if volume_title_match else ""
            
            # 提取章节链接
            chapter_pattern = r'<a[^>]*target="_blank"[^>]*title="([^"]+)"[^>]*href="([^"]+)">([^<]+)</a>'
            chapter_matches = re.findall(chapter_pattern, chapter_list_html)
            
            for title, href, text in chapter_matches:
                chapter_order += 1
                chapter_info = {
                    'chapter_title': title,
                    'chapter_url': urljoin(self.base_url, href),
                    'chapter_text': text,
                    'volume_title': volume_title,
                    'order': chapter_order
                }
                chapters.append(chapter_info)
        
        # 如果没有分部结构，直接提取所有章节链接
        if not has_volume_sections:
            # 查找所有章节列表容器
            chapter_lists = re.finditer(r'<div class="book-list clearfix">(.*?)</div>', content, re.DOTALL)
            
            for chapter_list_match in chapter_lists:
                chapter_list_html = chapter_list_match.group(1)
                
                # 提取章节链接
                chapter_pattern = r'<a[^>]*target="_blank"[^>]*title="([^"]+)"[^>]*href="([^"]+)">([^<]+)</a>'
                chapter_matches = re.findall(chapter_pattern, chapter_list_html)
                
                for title, href, text in chapter_matches:
                    chapter_order += 1
                    chapter_info = {
                        'chapter_title': title,
                        'chapter_url': urljoin(self.base_url, href),
                        'chapter_text': text,
                        'volume_title': "",  # 没有分部信息
                        'order': chapter_order
                    }
                    chapters.append(chapter_info)
        
        # 如果仍然没有找到章节，尝试更宽泛的匹配
        if not chapters:
            # 尝试匹配所有可能的章节链接
            chapter_pattern = r'<a[^>]*href="([^"]*(?:\.htm|\.html))"[^>]*title="([^"]+)"[^>]*>([^<]+)</a>'
            chapter_matches = re.findall(chapter_pattern, content)
            
            for href, title, text in chapter_matches:
                # 过滤掉非章节链接
                if '/novel/' in href or '/book/' in href or '/chapter/' in href or re.search(r'/\d+\.htm', href):
                    chapter_order += 1
                    chapter_info = {
                        'chapter_title': title,
                        'chapter_url': urljoin(self.base_url, href),
                        'chapter_text': text,
                        'volume_title': "",
                        'order': chapter_order
                    }
                    chapters.append(chapter_info)
        
        return chapters
    
    def _extract_book_introduction(self, content: str) -> str:
        """
        从HTML内容中提取书籍简介
        
        Args:
            content: 页面HTML内容
            
        Returns:
            书籍简介
        """
        # 匹配简介标签
        intro_pattern = r'<div class="describe-html"[^>]*>(.*?)</div>'
        match = re.search(intro_pattern, content, re.DOTALL)
        
        if match:
            intro_html = match.group(1)
            # 清理HTML标签
            intro_text = re.sub(r'<[^>]+>', '', intro_html).strip()
            return intro_text
        
        # 从meta标签获取描述
        meta_match = re.search(r'<meta name="description" content="([^"]+)"', content)
        if meta_match:
            return meta_match.group(1)
        
        return ""
    
    def _clean_chapter_content(self, content: str) -> str:
        """
        清理章节内容，去除HTML标签和多余内容
        
        Args:
            content: 原始章节内容
            
        Returns:
            清理后的纯文本内容
        """
        # 首先移除script标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        
        # 移除广告相关div
        content = re.sub(r'<div[^>]*ads[^>]*>.*?</div>', '', content, flags=re.DOTALL)
        
        # 特别处理空div标签
        content = re.sub(r'<div>\s*</div>', '', content)
        
        # 清理HTML标签，保留文本内容
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余的空格和换行
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'^\s+|\s+$', '', content)
        
        return content
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，处理落霞读书的多章节多部小说
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        try:
            # 获取小说基本信息页
            novel_url = self.get_novel_url(novel_id)
            novel_content = self._get_url_content(novel_url)
            
            if not novel_content:
                raise Exception(f"无法获取小说页面: {novel_url}")
            
            # 提取小说标题
            title = self._extract_title(novel_content)
            if not title:
                raise ValueError("未获取到小说标题")
            
            # 提取书籍状态
            status = self._extract_book_status(novel_content)
            
            # 提取书籍简介
            introduction = self._extract_book_introduction(novel_content)
            
            # 提取章节列表
            chapters_info = self._extract_chapter_list(novel_content)
            
            if not chapters_info:
                raise ValueError("未获取到章节列表")
            
            print(f"开始处理 [ {title} ] - 章节数: {len(chapters_info)}")
            
            # 逐章获取内容
            chapters = []
            for i, chapter_info in enumerate(chapters_info):
                chapter_title = chapter_info['chapter_title']
                chapter_url = chapter_info['chapter_url']
                volume_title = chapter_info['volume_title']
                
                print(f"正在处理第 {i+1}/{len(chapters_info)} 章: {chapter_title}")
                
                # 获取章节详情页
                chapter_content = self._get_url_content(chapter_url)
                
                if not chapter_content:
                    print(f"警告: 无法获取章节内容: {chapter_url}")
                    continue
                
                # 提取章节内容
                content_match = None
                for pattern in self.content_reg:
                    match = re.search(pattern, chapter_content, re.DOTALL)
                    if match:
                        content_match = match.group(1)
                        break
                
                if not content_match:
                    print(f"警告: 未找到章节内容: {chapter_url}")
                    continue
                
                # 清理章节内容
                clean_content = self._clean_chapter_content(content_match)
                
                # 构建章节标题（包含部名）
                full_chapter_title = f"{volume_title} {chapter_title}" if volume_title else chapter_title
                
                chapter_data = {
                    "title": full_chapter_title,
                    "content": clean_content,
                    "url": chapter_url,
                    "order": i + 1
                }
                chapters.append(chapter_data)
                
                # 添加延迟，避免请求过快
                time.sleep(0.5)
            
            if not chapters:
                raise ValueError("未获取到任何有效的章节内容")
            
            # 构建小说信息
            novel_content = {
                "title": title,
                "author": self.novel_site_name,  # 使用数据库中的网站名称
                "content": "",  # 多章节小说，不在详情中存储内容
                "url": novel_url,
                "book_type": "多章节",
                "status": status,
                "introduction": introduction,
                "chapters": chapters
            }
            
            print(f'[ {title} ] 完成，共处理 {len(chapters)} 章')
            return novel_content
            
        except Exception as e:
            raise ValueError(f"解析小说详情失败: {e}")
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题
        
        Args:
            content: 页面内容
            
        Returns:
            小说标题
        """
        # 尝试多个正则表达式
        for pattern in self.title_reg:
            match = re.search(pattern, content)
            if match:
                title = match.group(1).strip()
                if title:
                    return title
        
        # 从h1标签获取
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
        if h1_match:
            return h1_match.group(1).strip()
        
        return ""
    
    def _extract_book_status(self, content: str) -> str:
        """
        从HTML内容中提取书籍状态信息
        
        Args:
            content: 页面HTML内容
            
        Returns:
            书籍状态信息，多个标签用逗号连接
        """
        status_parts = []
        
        # 使用正则表达式提取状态信息
        for pattern in self.status_reg:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                if match and match.strip():
                    # 清理HTML标签和多余空格
                    clean_text = re.sub(r'<[^>]+>', '', match).strip()
                    if clean_text and clean_text not in status_parts:
                        status_parts.append(clean_text)
        
        return ", ".join(status_parts) if status_parts else "未知"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 落霞读书暂不支持列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = Kunnu8Parser()
    
    # 测试单篇小说
    try:
        novel_id = "guichui"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")