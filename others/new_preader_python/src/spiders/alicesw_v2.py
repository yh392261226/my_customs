"""
alicesw.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
import time
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AliceswParser(BaseParser):
    """alicesw.com 小说解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "alicesw.com"
    description = "alicesw.com 小说解析器"
    base_url = "https://www.alicesw.com"
    
    # 正则表达式配置
    title_reg = [
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*class="read-content j_readContent user_ad_content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="read-content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div[^>]*class="tLJ"[^>]*>(.*?)</div>'
    ]
    
    # 支持的书籍类型
    book_type = ["多章节"]
    
    # 内容页内分页相关配置
    content_page_link_reg = [
        r'<a[^>]*class="btn_yuedu"[^>]*href="([^"]*)"[^>]*>开始阅读</a>'
    ]
    
    next_page_link_reg = [
        r'<a[^>]*id="j_chapterNext"[^>]*href="([^"]*)"[^>]*>下一章</a>'
    ]
    
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
        重写URL生成方法，适配alicesw.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/novel/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，alicesw.com主要是多章节小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # alicesw.com主要是多章节小说
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
        book_id = self._extract_book_id_from_url(novel_url)
        if not book_id:
            raise Exception("无法提取书籍ID")
        
        # 获取第一章节链接
        first_chapter_url = self._extract_first_chapter_url(content)
        if not first_chapter_url:
            raise Exception("无法找到第一章节链接")
        
        # 构建完整的第一章节URL
        full_first_chapter_url = f"{self.base_url}{first_chapter_url}"
        
        print(f"第一章节链接: {full_first_chapter_url}")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': book_id,
            'url': novel_url,
            'chapters': []
        }
        
        
        # 抓取所有章节内容（通过章节分页）
        self._get_all_chapters(full_first_chapter_url, novel_content)
        
        return novel_content
    
    def _extract_book_id_from_url(self, url: str) -> Optional[str]:
        """
        从书籍URL中提取书籍ID
        
        Args:
            url: 书籍URL
            
        Returns:
            书籍ID或None
        """
        match = re.search(r'/novel/(\d+)\.html', url)
        return match.group(1) if match else None
    
    def _extract_first_chapter_url(self, content: str) -> Optional[str]:
        """
        从页面内容中提取第一章节链接
        
        Args:
            content: 页面内容
            
        Returns:
            第一章节链接或None
        """
        # 使用配置的正则表达式提取第一章节链接
        if self.content_page_link_reg:
            for pattern in self.content_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # 默认模式：查找"开始阅读"链接
        patterns = [
            r'<a[^>]*class="btn_yuedu"[^>]*href="([^"]*)"[^>]*>开始阅读</a>',
            r'<a[^>]*href="([^"]*)"[^>]*title="[^"]*"[^>]*>开始阅读</a>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _get_all_chapters(self, start_url: str, novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容（通过章节分页）
        
        Args:
            start_url: 起始章节URL
            novel_content: 小说内容字典
        """
        current_url = start_url
        self.chapter_count = 0
        
        while current_url:
            self.chapter_count += 1
            print(f"正在抓取第 {self.chapter_count} 章: {current_url}")
            
            # 获取章节页面内容
            page_content = self._get_url_content(current_url)
            
            if page_content:
                # 提取章节标题
                chapter_title = self._extract_chapter_title(page_content)
                
                # 提取章节内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)
                
                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': chapter_title or f"第 {self.chapter_count} 章",
                        'content': processed_content,
                        'url': current_url
                    })
                    print(f"√ 第 {self.chapter_count} 章抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 章内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 章抓取失败")
            
            # 获取下一页URL
            next_url = self._get_next_chapter_url(page_content, current_url) if page_content else None
            
            # 检查是否是最后一章
            if next_url and "/novel/" in next_url:
                print("检测到最后一章，停止抓取")
                break
            
            current_url = next_url
            
            # 章节间延迟
            time.sleep(1)
    
    def _extract_chapter_title(self, content: str) -> Optional[str]:
        """
        提取章节标题
        
        Args:
            content: 页面内容
            
        Returns:
            章节标题或None
        """
        patterns = [
            r'<h3[^>]*class="j_chapterName"[^>]*>(.*?)</h3>',
            r'<h3[^>]*class="j_chapterName"[^>]*>(.*?)</h3>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # 清理HTML标签
                title = re.sub(r'<[^>]+>', '', title)
                return title
        
        return None
    
    def _get_next_chapter_url(self, content: str, current_url: str) -> Optional[str]:
        """
        获取下一章节URL
        
        Args:
            content: 当前页面内容
            current_url: 当前页面URL
            
        Returns:
            下一章节URL或None
        """
        # 使用配置的正则表达式提取下一章节链接
        if self.next_page_link_reg:
            for pattern in self.next_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    next_url = match.group(1)
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
        
        # 默认模式：查找"下一章"链接
        patterns = [
            r'<a[^>]*id="j_chapterNext"[^>]*href="([^"]*)"[^>]*>下一章</a>',
            r'<a[^>]*href="([^"]*)"[^>]*>下一章</a>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                next_url = match.group(1)
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
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写首页元数据获取，适配alicesw.com的特定结构
        
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
        description = self._extract_description(content)
        
        # 提取状态
        status = self._extract_status(content)
        
        return {
            "title": title or "未知标题",
            "desc": description or "暂无简介",
            "status": status or "未知状态"
        }
    
    def _extract_description(self, content: str) -> str:
        """
        提取书籍简介
        
        Args:
            content: 页面内容
            
        Returns:
            简介文本
        """
        # 查找简介信息 - 使用更灵活的正则表达式匹配style属性
        desc_patterns = [
            r'<div[^>]*class="intro"[^>]*style="[^"]*margin-top[^"]*margin-left[^"]*font-size[^"]*font-weight[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="intro"[^>]*>(.*?)</div>',
            r'<div[^>]*class="intro"[^>]*style="[^"]*"[^>]*>(.*?)</div>'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                desc_content = match.group(1)
                # 清理HTML标签
                desc_text = re.sub(r'<[^>]+>', '', desc_content)
                desc_text = re.sub(r'\s+', ' ', desc_text).strip()
                return desc_text
        
        return ""
    
    def _extract_status(self, content: str) -> str:
        """
        提取书籍状态信息
        
        Args:
            content: 页面内容
            
        Returns:
            状态信息
        """
        # 查找所有tLJ类的div标签
        status_pattern = r'<div[^>]*class="tLJ"[^>]*>(.*?)</div>'
        status_matches = re.findall(status_pattern, content, re.IGNORECASE)
        
        if status_matches:
            # 将所有状态信息用逗号连接
            status_text = ', '.join([match.strip() for match in status_matches if match.strip()])
            return status_text
        
        return ""
    
    def _clean_content_specific(self, content: str) -> str:
        """
        清理alicesw.com特定的内容干扰
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 首先移除script和style标签及其内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除可能包含的嵌套div标签
        # 注意：根据用户描述，内容中可能还会有多个<div></div>标签
        # 我们保留最外层的div内容，移除内部的嵌套div
        
        # 移除导航和广告元素
        ad_patterns = [
            r'上一章.*?下一章',
            r'返回.*?目录',
            r'本章.*?字数',
            r'更新时间.*?\d{4}-\d{2}-\d{2}',
            r'作者.*?更新时间',
            r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        return content.strip()
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - alicesw.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []