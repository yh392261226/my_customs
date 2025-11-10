"""
xiyule网站解析器
支持 https://xiyule.co/ 网站的短篇小说解析
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser


class XiyuleParser(BaseParser):
    """xiyule网站解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "xiyule"
    description = "xiyule短篇小说解析器"
    base_url = "https://xiyule.co"
    
    # 正则表达式配置 - 标题提取
    title_reg = [
        r'<h1[^>]*class="card-title[^>]*text-center"[^>]*>([^<]+)</h1>',
        r'<h1[^>]*class="card-title"[^>]*>([^<]+)</h1>',
        r'<h1[^>]*>([^<]+)</h1>',
        r'<title[^>]*>([^<]+)</title>'
    ]
    
    # 正则表达式配置 - 内容提取
    content_reg = [
        r'<div[^>]*class="col-auto[^>]*mx-auto[^>]*art-content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="art-content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="col-auto[^>]*mx-auto"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>'
    ]
    
    # 状态正则表达式（短篇小说通常没有状态信息）
    status_reg = [
        r'<span[^>]*class="status"[^>]*>(.*?)</span>',
        r'<div[^>]*class="status"[^>]*>(.*?)</div>',
        r'<span[^>]*class="badge"[^>]*>(.*?)</span>'
    ]
    
    # 简介正则表达式（短篇小说通常没有简介）
    description_reg = [
        r'<div[^>]*class="intro"[^>]*>(.*?)</div>',
        r'<div[^>]*class="description"[^>]*>(.*?)</div>',
        r'<p[^>]*class="intro"[^>]*>(.*?)</p>',
        r'<div[^>]*class="summary"[^>]*>(.*?)</div>'
    ]
    
    # 书籍类型配置 - 短篇
    book_type = ["短篇"]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配xiyule网站的URL格式
        
        Args:
            novel_id: 小说ID（如：396/火车上我把一个帅哥摸射了）
            
        Returns:
            小说URL
        """
        # 如果novel_id包含路径，直接拼接
        if '/' in novel_id:
            return f"{self.base_url}/article/{novel_id}.html#article_title"
        else:
            # 如果只有数字ID，需要构造完整的URL
            return f"{self.base_url}/article/{novel_id}.html#article_title"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测方法，xiyule网站主要是短篇小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # xiyule网站主要是短篇小说，直接返回"短篇"
        return "短篇"
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写单章节小说解析方法，适配xiyule网站
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说内容字典
        """
        # 提取小说内容
        chapter_content = self._extract_chapter_content(content)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 清理内容
        cleaned_content = self._clean_chapter_content(chapter_content)
        
        # 从标题中提取作者信息
        author = self._extract_author_from_title(title)
        
        # 提取简介
        description = self._extract_description(content)
        
        # 提取状态
        status = self._extract_status(content)
        
        # 提取小说ID
        novel_id = self._extract_novel_id_from_url(novel_url)
        
        return {
            'title': title,
            'author': author or self.novel_site_name or self.name,
            'novel_id': novel_id,
            'url': novel_url,
            'description': description,
            'status': status or "已完结",  # 短篇小说通常都是已完结的
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': cleaned_content,
                'url': novel_url
            }]
        }
    
    def _extract_chapter_content(self, content: str) -> Optional[str]:
        """
        从页面内容提取章节内容
        
        Args:
            content: 页面内容
            
        Returns:
            章节内容或None
        """
        # 使用配置的正则表达式提取内容
        for pattern in self.content_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1)
        
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
        
        # 清理多余的空格和换行
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'^\s+', '', cleaned)
        cleaned = re.sub(r'\s+$', '', cleaned)
        
        # 恢复段落格式
        cleaned = re.sub(r'\s*\n\s*', '\n', cleaned)
        
        # 去掉可能存在的广告或干扰文本
        cleaned = re.sub(r'[\s\n]*请收藏本站.*[\s\n]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[\s\n]*.*广告.*[\s\n]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[\s\n]*.*版权.*[\s\n]*', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _extract_author_from_title(self, title: str) -> Optional[str]:
        """
        从标题中提取作者信息
        
        Args:
            title: 小说标题
            
        Returns:
            作者名称或None
        """
        # 尝试从标题中提取作者信息（如：【作者：xxx】）
        author_match = re.search(r'【作者：([^】]+)】', title)
        if author_match:
            return author_match.group(1).strip()
        
        # 尝试其他常见的作者标记格式
        author_patterns = [
            r'作者[:：]\s*([^\s]+)',
            r'by\s+([^\s]+)',
            r'BY\s+([^\s]+)'
        ]
        
        for pattern in author_patterns:
            author_match = re.search(pattern, title)
            if author_match:
                return author_match.group(1).strip()
        
        return None
    
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
                return desc.strip()
        
        # 如果没有找到简介，返回空字符串
        return ""
    
    def _extract_status(self, content: str) -> str:
        """提取小说状态"""
        # 使用配置的正则表达式提取状态
        for pattern in self.status_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                status = match.group(1).strip()
                # 清理HTML标签
                status = re.sub(r'<[^>]+>', '', status)
                status = re.sub(r'\s+', ' ', status)
                return status.strip()
        
        # 短篇小说默认状态为"已完结"
        return "已完结"