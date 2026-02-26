"""
book18.me 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""
from src.utils.logger import get_logger
import re
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

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
        import time
        
        self.chapter_count = 0
        
        for i, chapter_info in enumerate(chapter_links, 1):
            self.chapter_count += 1
            chapter_url = chapter_info['url']
            chapter_title = chapter_info['title']
            
            logger.info(f"正在爬取第 {i}/{len(chapter_links)} 章: {chapter_title}")
            
            # 获取章节内容
            full_url = f"{self.base_url}{chapter_url}"
            chapter_content = self._get_url_content(full_url)
            
            if chapter_content:
                # 使用基类提供的正则表达式提取方法
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    self.chapter_count += 1  # 只在成功添加章节后才增加计数
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': full_url
                    })
                    logger.info(f"✓ 第 {i}/{len(chapter_links)} 章抓取成功")
                else:
                    logger.warning(f"✗ 第 {self.chapter_count} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {i}/{len(chapter_links)} 章抓取失败")
            
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
        logger.error(f"抓取失败: {e}")
    def parse_novel_detail_incremental(self, novel_id: str, start_url: str, title: str = None, author: str = None, start_index: int = 0) -> Dict[str, Any]:
        """
        增量爬取：从指定章节URL开始继续爬取
        
        Args:
            novel_id: 小说ID
            start_url: 起始章节URL（最后一章的URL）
            title: 小说标题（可选）
            author: 作者（可选）
            start_index: 起始章节索引
            
        Returns:
            小说详情信息
        """
        # 获取小说页面，提取章节列表
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取章节列表（子类需要实现 _extract_chapter_links 方法）
        chapter_links = self._extract_chapter_links(content)
        if not chapter_links:
            raise Exception("无法获取章节列表")
        
        # 通过比对URL找到起始位置
        start_pos = 0
        for i, chapter in enumerate(chapter_links):
            chapter_full_url = chapter.get('url', '')
            if chapter_full_url == start_url or (not chapter_full_url.startswith('http') and f"{self.base_url}{chapter_full_url}" == start_url):
                start_pos = i + 1  # 从下一章开始
                break
        
        if start_pos >= len(chapter_links):
            # 没有新章节
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        logger.info(f"从第 {start_pos + 1} 章开始爬取，共 {len(chapter_links) - start_pos} 个新章节")
        
        # 创建小说内容
        novel_content = {
            'title': title or f'书籍-{novel_id}',
            'author': author or self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 从起始位置开始爬取
        self._get_all_chapters_incremental(chapter_links[start_pos:], novel_content, start_index)
        
        return novel_content
    
    def _get_all_chapters_incremental(self, chapter_links, novel_content, start_index=0):
        """
        增量爬取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
            start_index: 起始章节索引
        """
        import time
        
        self.chapter_count = start_index
        
        for i, chapter_info in enumerate(chapter_links, 1):
            chapter_url = chapter_info.get('url', '')
            chapter_title = chapter_info.get('title', f'第{start_index + i}章')
            
            logger.info(f"正在爬取第 {start_index + i} 章: {chapter_title}")
            
            # 获取章节内容
            full_url = f"{self.base_url}{chapter_url}" if chapter_url and not chapter_url.startswith('http') else chapter_url
            chapter_content = self._get_url_content(full_url)
            
            if chapter_content:
                # 使用配置的正则提取内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    self.chapter_count += 1
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': full_url
                    })
                    logger.info(f"✓ 第 {start_index + i} 章抓取成功")
                else:
                    logger.warning(f"✗ 第 {start_index + i} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {start_index + i} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
