"""
crxs.me 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class CrxsParser(BaseParser):

    """crxs.me 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "crxs.me"
    description = "crxs.me 小说解析器（配置驱动版本）"
    base_url = "https://crxs.me"
    
    # 正则表达式配置
    title_reg = [
        r'<meta name="twitter:title" content="\s*(.*?)\s*" />',
        r'<div class="title">\s*(.*?)\s*</div>',
        r'<div class="fiction-overview-info-item title">\s*(.*?)\s*</div>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*?class=["\']fiction-body["\'][^>]*?>(.*?)</div>',
        r'<div class="fiction-content">(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_replace_images_with_text",  # 子类特有的图片替换
        "_remove_ads"  # 子类特有的广告移除
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配crxs.me的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/fiction/id-{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，适配crxs.me的特定模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # crxs.me特定的多章节检测模式
        if 'fiction-overview-chapters' in content or 'chapter-item' in content:
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
        提取章节链接列表 - crxs.me特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        import re
        chapter_links = []
        
        # crxs.me特定的章节链接模式
        pattern = r'<a href="(/fiction/id-[^"]+)"[^>]*>\s*<div class="chapter-item">([^<]+)</div>\s*</a>'
        matches = re.findall(pattern, content)
        
        for href, title in matches:
            chapter_links.append({
                'url': href,
                'title': title.strip()
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
            chapter_url = chapter_info['url']
            chapter_title = chapter_info['title']

            logger.info(f"正在爬取第 {i}/{len(chapter_links)} 章: {chapter_title}")
            
            # 获取章节内容
            full_url = f"{self.base_url}{chapter_url}"
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
                    logger.info(f"✓ 第 {i}/{len(chapter_links)} 章抓取成功")
                else:
                    logger.warning(f"✗ 第 {i}/{len(chapter_links)} 章内容提取失败: {chapter_title}")
            else:
                logger.warning(f"✗ 第 {i}/{len(chapter_links)} 章抓取失败: {chapter_title}")
            
            # 章节间延迟
            time.sleep(1)
    
    def _replace_images_with_text(self, content: str) -> str:
        """
        替换图片为文字描述 - crxs.me特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 将图片标签替换为文字描述
        content = re.sub(r'<img[^>]*alt="([^"]*)"[^>]*>', r'[图片: \1]', content)
        content = re.sub(r'<img[^>]*>', '[图片]', content)
        
        return content
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - crxs.me特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除常见的广告模式
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
        解析小说列表页 - crxs.me不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # crxs.me是短篇小说网站，每个小说一个页面，不需要列表解析
        return []


# 使用示例
if __name__ == "__main__":
    parser = CrxsParser()
    
    # 测试单篇小说
    try:
        novel_id = "68fa7dcff3de0"  # 单篇示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"单篇小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"单篇抓取失败: {e}")
    
    # 测试多篇小说
    try:
        novel_id = "6286950598ecd"  # 多篇示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"多篇小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"多篇抓取失败: {e}")
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
