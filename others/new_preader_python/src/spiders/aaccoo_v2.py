"""
aaccoo.com 小说网站解析器
继承自 BaseParser，使用属性配置实现
"""

import re
import time
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AaccooParser(BaseParser):
    """aaccoo.com 小说解析器"""
    
    # 基本信息
    name = "aaccoo.com"
    description = "aaccoo.com 小说解析器"
    base_url = "https://www.aaccoo.com"
    
    # 正则表达式配置
    title_reg = [
        r"<h1[^>]*>(.*?)</h1>",
        r'<title>(.*?)[\s\-_]+.*?</title>'
    ]
    
    desc_reg = [
        r'<div[^>]*class="[^"]*book-desc[^"]*"[^>]*>(.*?)</div>'
    ]
    
    content_reg = [
        r"<div[^>]*class=\"[^\"]*content[^\"]*\"[^>]*id=\"[^\"]*content[^\"]*\"[^>]*>(.*?)</div>",
        r"<div[^>]*class=\"[^\"]*content[^\"]*\"[^>]*>(.*?)</div>",
        r"<div[^>]*id=\"[^\"]*content[^\"]*\"[^>]*>(.*?)</div>"
    ]
    
    status_reg = [
        r'<dl[^>]*class="[^"]*status[^"]*"[^>]*>.*?<dt[^>]*>状态</dt>\s*<dd[^>]*>(.*?)</dd>',
        r'status[：:]\s*(.*?)[<\n\r]'
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
        # 禁用SSL验证以解决可能的SSL错误
        self.session.verify = False
        # 添加特定的请求头
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配aaccoo.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/book/{novel_id}/"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，aaccoo.com主要是多章节小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # aaccoo.com主要是多章节小说
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
        
        # 提取书籍简介
        description = self._extract_description(content)
        
        # 提取书籍状态
        status = self._extract_status(content)
        
        # 获取第一页链接
        first_page_url = self._extract_first_page_url(content)
        if not first_page_url:
            raise Exception("无法获取第一页链接")
        
        print(f"第一页链接: {first_page_url}")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'description': description,
            'status': status,
            'novel_id': book_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 从第一页开始，按顺序获取所有章节内容
        self._get_all_chapters_sequentially(first_page_url, novel_content, book_id)
        
        return novel_content
    
    def _extract_book_id_from_url(self, url: str) -> Optional[str]:
        """
        从书籍URL中提取书籍ID
        
        Args:
            url: 书籍URL
            
        Returns:
            书籍ID或None
        """
        match = re.search(r'/book/(\d+)/?', url)
        return match.group(1) if match else None
    
    def _extract_description(self, content: str) -> str:
        """
        提取书籍简介
        
        Args:
            content: 页面内容
            
        Returns:
            书籍简介
        """
        for pattern in self.desc_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                desc = match.group(1).strip()
                # 去除HTML标签
                desc = re.sub(r'<[^>]+>', '', desc)
                # 清理空白字符
                desc = re.sub(r'\s+', ' ', desc).strip()
                return desc
        return "无简介"
    
    def _extract_status(self, content: str) -> str:
        """
        提取书籍状态
        
        Args:
            content: 页面内容
            
        Returns:
            书籍状态
        """
        for pattern in self.status_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                status = match.group(1).strip()
                return status
        return "未知"
    
    def _extract_first_page_url(self, content: str) -> Optional[str]:
        """
        提取第一页链接
        
        Args:
            content: 页面内容
            
        Returns:
            第一页链接或None
        """
        # 查找 "开始阅读" 按钮
        pattern = r'<a[^>]*class="[^"]*btn-read[^"]*"[^>]*href="([^"]*)"[^>]*>'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            href = match.group(1).strip()
            # 确保URL格式正确
            if href.startswith('http'):
                return href
            elif href.startswith('/'):
                return f"{self.base_url}{href}"
            else:
                return f"{self.base_url}/{href}"
        return None
    
    def _get_all_chapters_sequentially(self, first_page_url: str, novel_content: Dict[str, Any], book_id: str) -> None:
        """
        按顺序获取所有章节内容
        
        Args:
            first_page_url: 第一页链接
            novel_content: 小说内容字典
            book_id: 书籍ID
        """
        self.chapter_count = 0
        current_url = first_page_url
        
        while current_url:
            self.chapter_count += 1
            
            print(f"正在抓取第 {self.chapter_count} 章: {current_url}")
            
            # 获取章节标题和内容
            chapter_title, chapter_content, next_url = self._get_chapter_info(current_url)
            
            if chapter_title and chapter_content:
                novel_content['chapters'].append({
                    'chapter_number': self.chapter_count,
                    'title': chapter_title,
                    'content': chapter_content,
                    'url': current_url
                })
                print(f"√ 第 {self.chapter_count} 章抓取成功: {chapter_title}")
            else:
                print(f"× 第 {self.chapter_count} 章内容抓取失败")
                break  # 如果无法获取内容，停止继续
            
            # 更新下一页URL
            if next_url and next_url != "javascript:alert('没有了');":
                # 确保URL格式正确
                if next_url.startswith('http'):
                    current_url = next_url
                elif next_url.startswith('/'):
                    current_url = f"{self.base_url}{next_url}"
                else:
                    current_url = f"{self.base_url}/{next_url}"
            else:
                current_url = None
            
            # 章节间延迟
            time.sleep(1)
    
    def _get_chapter_info(self, chapter_url: str) -> tuple[str, str, Optional[str]]:
        """
        获取章节信息，包括标题、内容和下一页链接
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节标题、内容和下一页链接的元组
        """
        content = self._get_url_content(chapter_url)
        if not content:
            logger.warning(f"无法获取章节页面: {chapter_url}")
            return None, None, None
        
        # 提取章节标题
        chapter_title = self._extract_chapter_title(content)
        
        # 提取章节内容
        chapter_content = self._extract_chapter_content(content)
        
        # 提取下一页链接
        next_url = self._extract_next_url(content)
        
        return chapter_title, chapter_content, next_url
    
    def _extract_chapter_title(self, content: str) -> str:
        """
        提取章节标题
        
        Args:
            content: 页面内容
            
        Returns:
            章节标题
        """
        pattern = r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h1>'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            # 去除HTML标签
            title = re.sub(r'<[^>]+>', '', title)
            return title
        return f"第{self.chapter_count}章"
    
    def _extract_chapter_content(self, content: str) -> Optional[str]:
        """
        提取章节内容
        
        Args:
            content: 页面内容
            
        Returns:
            章节内容或None
        """
        for pattern in self.content_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                content_text = match.group(1).strip()
                # 去除HTML标签
                content_text = re.sub(r'<[^>]+>', '', content_text)
                # 执行爬取后处理函数
                processed_content = self._execute_after_crawler_funcs(content_text)
                
                # 检查内容是否有效（至少包含一些中文字符）
                if processed_content and len(processed_content.strip()) > 50 and re.search(r'[\u4e00-\u9fff]', processed_content):
                    return processed_content
        return None
    
    def _extract_next_url(self, content: str) -> Optional[str]:
        """
        提取下一页链接
        
        Args:
            content: 页面内容
            
        Returns:
            下一页链接或None
        """
        # 查找 prenext div
        pattern = r'<div[^>]*class="[^"]*prenext[^"]*"[^>]*>.*?</div>'
        prenext_match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if not prenext_match:
            return None
        
        prenext_content = prenext_match.group(0)
        
        # 查找所有链接
        link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>下一章</a>'
        next_match = re.search(link_pattern, prenext_content, re.IGNORECASE)
        if next_match:
            return next_match.group(1).strip()
        
        # 如果找不到"下一章"链接，检查是否是最后一章
        no_more_pattern = r'<a[^>]*href="javascript:alert\(\'没有了\'\);"[^>]*>下一章</a>'
        if re.search(no_more_pattern, prenext_content, re.IGNORECASE):
            return "javascript:alert('没有了');"
        
        return None
    
    def _clean_content_specific(self, content: str) -> str:
        """
        特定内容清理方法，针对aaccoo.com的特点
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return content
            
        # 移除常见的广告和无关内容
        content = re.sub(r'(?i)(最新章节|免费阅读|全文阅读).{0,20}', '', content)
        content = re.sub(r'(?i)(请记住本站域名|网址|书友大本营|收藏本站|加入书签|推荐本书).*', '', content)
        content = re.sub(r'(?i)(天才一秒记住|更新速度快|无弹窗|喜欢).*', '', content)
        
        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # 清理首尾空白
        content = content.strip()
        
        return content