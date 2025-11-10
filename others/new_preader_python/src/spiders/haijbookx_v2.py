"""
海角文爱网站解析器
支持 https://haijbookx.top/ 网站的小说解析
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser


class HaijbookxParser(BaseParser):
    """海角文爱网站解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "海角文爱"
    description = "海角文爱多章节小说解析器"
    base_url = "https://haijbookx.top"
    
    # 正则表达式配置 - 章节列表页
    title_reg = [
        r'<h1[^>]*>([^<]+)</h1>',
        r'<title[^>]*>([^<]+)</title>'
    ]
    
    # 章节列表正则 - 从<ul id="ul_all_chapters">中提取
    chapter_link_reg = [
        r'<ul[^>]*id="ul_all_chapters"[^>]*>(.*?)</ul>',
        r'<li[^>]*><a[^>]*href="([^"]*?)"[^>]*title="[^"]*?([^"]*?)[^"]*?"[^>]*>([^<]+)</a></li>',
        r'<li[^>]*><a[^>]*href="([^"]*?)"[^>]*>([^<]+)</a></li>'
    ]
    
    # 状态提取 - 从<div class="novel_info_title">下的<p>标签中提取
    status_reg = [
        r'<div[^>]*class="novel_info_title"[^>]*>(.*?)</div>',
        r'<p[^>]*>(.*?)</p>'
    ]
    
    # 简介提取 - 从<div class="intro">中提取
    description_reg = [
        r'<div[^>]*class="intro"[^>]*>(.*?)</div>',
        r'<p[^>]*>(.*?)</p>'
    ]
    
    # 内容页正则 - 章节内容
    content_reg = [
        r'<article[^>]*id="article"[^>]*class="content"[^>]*>(.*?)</article>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>'
    ]
    
    # 书籍类型配置
    book_type = ["多章节"]
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测方法，专门针对海角文爱网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检测海角文爱特有的多章节模式
        haijbookx_patterns = [
            r'<ul[^>]*id="ul_all_chapters"[^>]*>',
            r'第\s*\d+\s*章',
            r'章节列表',
            r'目录'
        ]
        
        for pattern in haijbookx_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "多章节"
        
        # 检测通用的多章节模式
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
        
        # 默认返回多章节（海角文爱主要是多章节小说）
        return "多章节"
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配海角文爱网站的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/?book/{novel_id}/"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说
        
        Args:
            content: 章节列表页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说内容字典
        """
        # 提取章节列表
        chapters_list = self._extract_chapters(content, novel_url)
        
        if not chapters_list:
            raise Exception("无法提取章节列表")
        
        print(f"开始处理 [ {title} ] - 找到 {len(chapters_list)} 个章节")
        
        # 解析每个章节内容
        chapters_with_content = []
        for i, chapter_info in enumerate(chapters_list):
            try:
                chapter_url = chapter_info['url']
                chapter_content = self.parse_chapter_content(chapter_url)
                
                if chapter_content:
                    chapters_with_content.append({
                        'chapter_number': i + 1,
                        'title': chapter_info['title'],
                        'content': chapter_content,
                        'url': chapter_url
                    })
                    print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 完成")
                else:
                    print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 获取内容失败")
                    
            except Exception as e:
                print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 错误: {e}")
        
        if not chapters_with_content:
            raise Exception("无法获取任何章节内容")
        
        # 提取简介和状态
        description = self._extract_description(content)
        status = self._extract_status(content)
        
        return {
            'title': title,
            'author': self.novel_site_name or self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'description': description,
            'status': status,
            'chapters': chapters_with_content
        }
    
    def _extract_chapters(self, content: str, novel_url: str) -> List[Dict[str, Any]]:
        """
        从章节列表页面提取章节信息
        
        Args:
            content: 章节列表页面内容
            novel_url: 小说URL
            
        Returns:
            章节信息列表
        """
        chapters = []
        
        # 首先尝试从ul_all_chapters中提取
        ul_pattern = r'<ul[^>]*id="ul_all_chapters"[^>]*>(.*?)</ul>'
        ul_match = re.search(ul_pattern, content, re.DOTALL)
        
        if ul_match:
            ul_content = ul_match.group(1)
            # 从ul中提取li链接
            li_pattern = r'<li[^>]*><a[^>]*href="([^"]*?)"[^>]*title="[^"]*?([^"]*?)[^"]*?"[^>]*>([^<]+)</a></li>'
            li_matches = re.finditer(li_pattern, ul_content, re.DOTALL)
            
            for match in li_matches:
                chapter_url = match.group(1).strip()
                chapter_title = match.group(3).strip()  # 优先使用链接文本
                
                # 清理章节标题
                chapter_title = re.sub(r'\s+', ' ', chapter_title).strip()
                
                # 确保URL是完整的
                if not chapter_url.startswith('http'):
                    if chapter_url.startswith('/'):
                        chapter_url = self.base_url + chapter_url
                    else:
                        chapter_url = urljoin(self.base_url, chapter_url)
                
                chapters.append({
                    "title": chapter_title,
                    "url": chapter_url
                })
        
        # 如果没有找到，尝试通用方法
        if not chapters:
            # 提取章节链接和标题
            for chapter_pattern in self.chapter_link_reg:
                matches = re.finditer(chapter_pattern, content, re.DOTALL)
                for match in matches:
                    if len(match.groups()) >= 2:
                        chapter_url = match.group(1).strip()
                        chapter_title = match.group(2).strip() if len(match.groups()) >= 2 else "未知章节"
                        
                        # 清理章节标题
                        chapter_title = re.sub(r'\s+', ' ', chapter_title).strip()
                        
                        # 确保URL是完整的
                        if not chapter_url.startswith('http'):
                            if chapter_url.startswith('/'):
                                chapter_url = self.base_url + chapter_url
                            else:
                                chapter_url = urljoin(self.base_url, chapter_url)
                        
                        chapters.append({
                            "title": chapter_title,
                            "url": chapter_url
                        })
        
        return chapters
    
    def _extract_description(self, content: str) -> str:
        """提取小说简介"""
        # 使用配置的正则表达式提取简介
        for pattern in self.description_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                desc = match.group(1).strip()
                # 清理HTML标签
                desc = re.sub(r'<[^>]+>', '', desc)
                desc = re.sub(r'\s+', ' ', desc)
                # 去掉"本站永久域名"等字样
                desc = re.sub(r'本站永久域名[^，。]*[，。]', '', desc)
                return desc.strip()
        return ""
    
    def _extract_status(self, content: str) -> str:
        """提取小说状态"""
        # 使用配置的正则表达式提取状态
        status_info = []
        
        for pattern in self.status_reg:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                status_text = match.group(1).strip()
                # 清理HTML标签
                status_text = re.sub(r'<[^>]+>', '', status_text)
                status_text = re.sub(r'\s+', ' ', status_text)
                if status_text and status_text not in status_info:
                    status_info.append(status_text)
        
        # 将状态信息用逗号连接
        if status_info:
            return ', '.join(status_info)
        
        return "连载中"
    
    def parse_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        解析章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容文本
        """
        print(f"正在获取章节内容: {chapter_url}")
        content = self._fetch_url(chapter_url)
        
        if not content:
            print("无法获取章节页面内容")
            return None
        
        print(f"获取到章节页面，长度: {len(content)}")
        
        # 提取章节内容
        chapter_content = self._extract_chapter_content(content)
        
        if chapter_content:
            print(f"章节内容提取成功，长度: {len(chapter_content)}")
            return chapter_content
        
        print("章节内容提取失败")
        return None
    
    def _extract_chapter_content(self, content: str) -> Optional[str]:
        """
        从章节页面提取内容
        
        Args:
            content: 章节页面内容
            
        Returns:
            清理后的章节内容
        """
        # 尝试从article标签中提取
        for pattern in self.content_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                article_content = match.group(1)
                
                # 清理内容
                cleaned_content = self._clean_chapter_content(article_content)
                
                if cleaned_content:
                    return cleaned_content
        
        return None
    
    def _clean_chapter_content(self, content: str) -> str:
        """
        清理章节内容
        
        Args:
            content: 原始章节内容
            
        Returns:
            清理后的内容
        """
        # 去掉HTML标签
        cleaned = re.sub(r'<[^>]+>', '', content)
        
        # 去掉"本站永久域名"等字样
        cleaned = re.sub(r'本站永久域名[^，。]*[，。]', '', cleaned)
        
        # 清理多余的空格和换行
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'^\s+', '', cleaned)
        cleaned = re.sub(r'\s+$', '', cleaned)
        
        # 恢复段落格式
        cleaned = re.sub(r'\s*\n\s*', '\n', cleaned)
        
        return cleaned.strip()
    
    def _fetch_url(self, url: str) -> Optional[str]:
        """
        获取URL内容
        
        Args:
            url: 目标URL
            
        Returns:
            页面内容或None
        """
        try:
            # 使用session获取页面内容
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                # 设置正确的编码（根据网站使用gbk编码）
                response.encoding = 'gbk'
                return response.text
            else:
                print(f"请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None