"""
xchina.co 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现

网站结构特点：
- 书籍详情页和章节列表页都是同一个URL：https://xchina.co/fiction/id-{id}.html
- 多章节书籍：包含 <div class="fiction-overview-chapters"> 章节列表
- 单篇书籍：包含 <div class="fiction-body"> 内容
- 书名：<h1 class="hero-title-item">标题</h1>
- 简介：<div class="fiction-overview-brief">导读内容</div>
- 状态：<div class="fiction-overview-info-item tags">标签内容</div>
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class XchinaParser(BaseParser):
    """xchina.co 小说解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "xchina.co"
    description = "xchina.co 小说解析器（支持单篇和多篇）"
    base_url = "https://xchina.co"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="hero-title-item"[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*class="fiction-body"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div[^>]*class="fiction-overview-info-item tags"[^>]*>(.*?)</div>',
        r'<div[^>]*class="tags"[^>]*>(.*?)</div>'
    ]
    
    # 章节链接正则
    chapter_link_reg = [
        r'<div[^>]*class="fiction-overview-chapters"[^>]*>.*?<a href="(/fiction/id-[^"]+\.html)"[^>]*>\s*<div[^>]*class="chapter-item"[^>]*>(.*?)</div>\s*</a>',
        r'<div[^>]*class="fiction-overview-chapters"[^>]*>.*?<a href="(/fiction/id-[^"]+\.html)"[^>]*>(.*?)</a>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_ads"  # 广告移除
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        # 禁用SSL验证以解决SSL错误
        self.session.verify = False
        # 添加User-Agent以绕过反爬虫
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配xchina.co的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/fiction/id-{novel_id}.html"
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写获取书籍首页元数据方法，专门处理xchina.co的标签提取
        
        Args:
            novel_id: 小说ID
            
        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            return None
        
        # 自动检测书籍类型
        book_type = self._detect_book_type(content)
        
        # 使用配置的正则提取标题
        title = self._extract_with_regex(content, self.title_reg)
        
        # 提取简介
        desc = self._extract_brief_content(content)
        
        # 专门处理标签提取
        status = self._extract_tags_content(content)
        
        return {
            "title": title or "未知标题",
            "desc": desc or f"{book_type}小说",
            "status": status or "未知状态"
        }
    
    def _extract_brief_content(self, content: str) -> str:
        """
        提取简介内容
        
        Args:
            content: 页面内容
            
        Returns:
            简介内容
        """
        import re
        
        # 提取brief div的内容
        brief_match = re.search(r'<div[^>]*class="fiction-overview-brief"[^>]*>\s*<span>导读：</span>\s*(.*?)\s*</div>', 
                              content, re.IGNORECASE | re.DOTALL)
        if brief_match:
            return brief_match.group(1).strip()
        
        return ""
    
    def _extract_tags_content(self, content: str) -> str:
        """
        提取标签内容，多个标签用逗号连接
        
        Args:
            content: 页面内容
            
        Returns:
            标签内容字符串，多个标签用逗号连接
        """
        import re
        
        # 提取整个tags div的内容
        tags_div_match = re.search(r'<div[^>]*class="fiction-overview-info-item tags"[^>]*>(.*?)</div>', 
                                 content, re.IGNORECASE | re.DOTALL)
        if not tags_div_match:
            return ""
        
        tags_div_content = tags_div_match.group(1)
        
        # 提取所有标签内容
        tag_matches = re.findall(r'<div[^>]*class="tag"[^>]*>(.*?)</div>', tags_div_content)
        
        if tag_matches:
            # 清理标签内容并去除空白字符
            cleaned_tags = [tag.strip() for tag in tag_matches if tag.strip()]
            # 用逗号连接所有标签
            return ", ".join(cleaned_tags)
        
        return ""
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，通过章节列表检测
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检测是否包含章节列表
        if 'fiction-overview-chapters' in content:
            return "多章节"
        
        # 检测是否包含内容
        if 'fiction-body' in content:
            return "短篇"
        
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
        提取章节链接列表 - xchina.co特定实现
        只在<div class="fiction-overview-chapters">标签内查找
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        import re
        chapter_links = []
        
        # 首先提取fiction-overview-chapters div的内容
        chapters_div_match = re.search(r'<div[^>]*class="fiction-overview-chapters"[^>]*>(.*?)</div>', 
                                      content, re.IGNORECASE | re.DOTALL)
        
        if not chapters_div_match:
            return []
        
        chapters_div_content = chapters_div_match.group(1)
        
        # 使用配置的章节链接正则表达式，只在chapters div内查找
        for pattern in self.chapter_link_reg:
            matches = re.findall(pattern, chapters_div_content, re.IGNORECASE | re.DOTALL)
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
            
            # 构建完整URL
            if chapter_url.startswith('/'):
                full_url = f"{self.base_url}{chapter_url}"
            else:
                full_url = chapter_url
            
            # 获取章节内容
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
        移除广告内容 - xchina.co特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除xchina.co常见的广告模式
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
        解析小说列表页 - xchina.co不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = XchinaParser()
    
    # 测试多章节小说
    try:
        novel_id = "62aec8e51f719"  # 多章节示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"多章节抓取失败: {e}")
    
    # 测试单篇小说
    try:
        novel_id = "67ef0807c9659"  # 单篇示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"单篇抓取失败: {e}")