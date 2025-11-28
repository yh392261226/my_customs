"""
xbookcn.org 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class XbookcnorgParser(BaseParser):
    """xbookcn.org 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "xbookcn.org"
    description = "xbookcn.org 小说网站解析器"
    base_url = "https://xbookcn.org"
    
    # 正则表达式配置
    title_reg = [
        r'<div[^>]*class="title"[^>]*>([^<]+)</div>',
        r'<title>([^<]+)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*class="content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型
    book_type = ["多章节", "短篇+多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_content_obs",  # 清理内容中的干扰
        "_remove_ads"  # 移除广告
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/fiction.php?id={novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # xbookcn.org主要是多章节小说
        if "chapters" in content and "page=" in content:
            return "多章节"
        return "短篇"
    
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
        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
        """
        提取章节链接列表
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        import re
        chapter_links = []
        
        # 直接从完整HTML内容中提取章节链接，不限制在chapters区域内
        # xbookcn.org特定的章节链接模式
        # <a href="/fiction.php?id=MjE0OTc%3D&page=1"><div>第一章 踏入的第一步</div></a>
        pattern = r'<a[^>]*href="(/fiction\.php\?id=([^&]+)&page=(\d+))"[^>]*><div>([^<]+)</div></a>'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        # 如果没有找到普通&符号的链接，尝试&amp;编码
        if not matches:
            pattern = r'<a[^>]*href="(/fiction\.php\?id=([^&]+)&amp;page=(\d+))"[^>]*><div>([^<]+)</div></a>'
            matches = re.findall(pattern, content, re.IGNORECASE)
        
        for href, novel_id, page_num, chapter_title in matches:
            # 构建完整的章节URL
            chapter_url = f"{self.base_url}{href}"
            chapter_links.append({
                'url': chapter_url,
                'title': chapter_title.strip()
            })
        
        # 如果上面的方法没有找到章节，尝试更简单的模式
        if not chapter_links:
            # 尝试匹配任何包含page参数的链接
            pattern = r'<a[^>]*href="([^"]*page=\d+[^"]*)"[^>]*><div>([^<]+)</div></a>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            for href, chapter_title in matches:
                if href.startswith('/'):
                    chapter_url = f"{self.base_url}{href}"
                else:
                    chapter_url = href
                chapter_links.append({
                    'url': chapter_url,
                    'title': chapter_title.strip()
                })
        
        return chapter_links
    
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
            chapter_content = self._get_url_content(chapter_url)
            
            if chapter_content:
                # 使用配置的正则提取内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': chapter_url
                    })
                    print(f"√ 第 {self.chapter_count} 章抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 章内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        重写以适配xbookcn.org网站的结构
        
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
        
        # 提取作者
        author = self._extract_author(content)
        
        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "desc": desc or "暂无简介",
            "status": status or "未知状态",
            "author": author or "未知作者"
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
        
        pattern = r'<div[^>]*class="brief"[^>]*>(.*?)</div>'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            desc = match.group(1)
            # 清理HTML标签
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.replace('&nbsp;', ' ').replace('\xa0', ' ')
            # 移除"导读："前缀
            desc = re.sub(r'^导读：', '', desc)
            return desc.strip()
        
        return ""
    
    def _extract_author(self, content: str) -> str:
        """
        提取作者信息
        
        Args:
            content: 页面内容
            
        Returns:
            作者名称
        """
        import re
        
        pattern = r'<div[^>]*class="author"[^>]*>作者：<a[^>]*>([^<]+)</a></div>'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return ""
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除常见的广告模式
        ad_patterns = [
            r'<div[^>]*class="fiction-banner"[^>]*>.*?</div>',
            r'<iframe[^>]*>.*?</iframe>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _clean_content_obs(self, content: str) -> str:
        """
        清理内容中的干扰，提取纯文本
        
        Args:
            content: 内容
            
        Returns:
            清理后的纯文本
        """
        import re
        
        # 移除以#&开头、中间有数字、以;结尾的干扰字符串
        clean_text = re.sub(r'&#\d{1,10};', '', content)
        
        # 同时移除其他可能的HTML实体编码干扰
        clean_text = re.sub(r'&#\d{1,5};', '', clean_text)
        
        # 移除多余的空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text.strip()
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        import re
        
        # 从URL中提取id参数
        match = re.search(r'id=([^&]+)', url)
        if match:
            return match.group(1)
        
        # 如果没有找到，使用默认方法
        return super()._extract_novel_id_from_url(url)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - xbookcn.org不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []