"""
book18.me 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""
import re
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from .base_parser_v2 import BaseParser

class Book18Parser(BaseParser):
    """book18.me 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "book18.me"
    description = "book18.me 小说解析器（支持单篇和多篇）"
    base_url = "https://www.book18.me"
    
    # 正则表达式配置
    title_reg = [
        r'<h1 class="title py-1">\s*(.*?)\s*</h1>',
        r'<h1[^>]*>\s*(.*?)\s*</h1>'
    ]
    
    content_reg = [
        r'<div id="content"[^>]*>(.*?)</div>',
        r'<div class="entry-content"[^>]*>(.*?)</div>',
        r'<div class="post-body"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_url_content",
        "_remove_ads"  # 广告移除
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配book18.me的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        # book18.me支持数字ID和中文标题
        if novel_id.isdigit():
            return f"{self.base_url}/article/{novel_id}"
        else:
            # 中文标题需要URL编码
            encoded_title = quote(novel_id)
            return f"{self.base_url}/book/{encoded_title}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，适配book18.me的特定模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        import re
        
        # 检查是否存在章节列表（list-group）
        chapter_list_match = re.search(r'<ul class="list-group">', content)
        chapter_items_match = re.search(r'<li class="list-group-item px-2">', content)
        
        if chapter_list_match or chapter_items_match:
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
        提取章节链接列表 - book18.me特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        import re
        chapter_links = []
        
        # 模式1：从list-group中提取章节链接
        # 匹配 <li class="list-group-item px-2"><a href="/208928" target="_blank"><b class="mr-1">我的妈妈是黑帮大佬</b>(1)作者：遇见春水</a></li>
        pattern1 = r'<li class="list-group-item px-2">\s*<a href="([^"]+)"[^>]*>\s*<b class="mr-1">[^<]*</b>\(([^)]+)\)[^<]*</a>\s*</li>'
        matches1 = re.findall(pattern1, content)
        
        for href, chapter_num in matches1:
            chapter_title = f"第{chapter_num}章"
            chapter_links.append({
                'url': href,
                'title': chapter_title
            })
        
        # 模式2：如果上面的模式没有匹配到，尝试更宽松的模式
        if not chapter_links:
            # 匹配所有数字链接
            pattern2 = r'<a href="(/(\d+))"[^>]*>'
            matches2 = re.findall(pattern2, content)
            
            for href, chapter_num in matches2:
                chapter_title = f"第{chapter_num}章"
                chapter_links.append({
                    'url': href,
                    'title': chapter_title
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
                # 使用基类提供的正则表达式提取方法
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
        移除广告内容 - book18.me特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除book18.me常见的广告模式
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
        解析小说列表页 - book18.me不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _clean_url_content(self, html_content: str) -> str:
        """
        清理HTML内容，提取纯文本
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        clean_text = re.sub(r'', '', html_content)
        # 替换HTML实体
        clean_text = clean_text.replace('book18.org', '')
        return clean_text.strip()


# 使用示例
if __name__ == "__main__":
    parser = Book18Parser()
    
    # 测试单篇小说
    try:
        novel_id = "12345"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")