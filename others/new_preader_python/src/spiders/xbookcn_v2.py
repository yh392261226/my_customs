"""
xbookcn.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class XbookcnParser(BaseParser):
    """xbookcn.com 小说解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "xbookcn.com"
    description = "xbookcn.com 小说解析器"
    base_url = "https://blog.xbookcn.com"
    
    # 正则表达式配置
    title_reg = [
        r"<h3 class='post-title entry-title' itemprop='name'>(.*?)</h3>",
        r'<title>(.*?)-[^-]+</title>'
    ]
    
    content_reg = [
        r"<div class='post-body entry-content'[^>]*>(.*?)</div>"
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_content_obs",
        "_remove_ads"  # 广告移除
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """初始化解析器"""
        super().__init__(proxy_config)
        # 禁用SSL验证以解决SSL错误
        self.session.verify = False
        # 添加User-Agent以绕过反爬虫
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配xbookcn.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，适配xbookcn.com的特定模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # xbookcn.com特定的多章节检测模式
        if '章节列表' in content or 'chapter-list' in content:
            return "多章节"
        
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
        # 提取章节链接
        chapter_links = self._extract_chapter_links(content)
        if not chapter_links:
            raise Exception("无法提取章节列表")
        
        print(f"发现 {len(chapter_links)} 个章节")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
        """
        提取章节链接列表 - xbookcn.com特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        import re
        chapter_links = []
        
        # xbookcn.com特定的章节链接模式
        pattern = r'<a href="(/book/\d+/\d+\.html)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, content)
        
        for href, title in matches:
            chapter_links.append({
                'url': href,
                'title': title.strip()
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
            full_url = f"{self.base_url}{chapter_url}"
            chapter_content = self._get_url_content(full_url)
            
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
                        'url': full_url
                    })
                    print(f"√ 第 {self.chapter_count} 章抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 章内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - xbookcn.com特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除xbookcn.com常见的广告模式
        ad_patterns = [
            r'<div class="ad".*?</div>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - xbookcn.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []

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
        # 更精确的正则表达式，匹配 &#123; 或 &#12345; 等格式
        clean_text = re.sub(r'&#\d{1,10};', '', content)
        
        # 同时移除其他可能的HTML实体编码干扰
        clean_text = re.sub(r'&#\d{1,5};', '', clean_text)
        
        # 移除多余的空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text.strip()