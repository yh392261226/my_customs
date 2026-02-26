"""
咪咕文学网站解析器
网站: https://74qyavudmbzu1.migu1.top/
特点: 短篇小说，单章节，无需分页
基于配置驱动版本，遵循txtxi_v2.py格式
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class MiguParser(BaseParser):
    """咪咕文学网站解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "咪咕文学"
    description = "咪咕文学短篇小说解析器"
    base_url = "https://74qyavudmbzu1.migu1.top"
    
    # 正则表达式配置
    title_reg = [
        r'<h2[^>]*class="chapter-title"[^>]*>(.*?)</h2>'
    ]
    
    content_reg = [
        r'<div[^>]*class="reading-content"[^>]*id="readingContent"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配咪咕文学的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/index.php/art/detail/id/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，咪咕文学是短篇小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - 咪咕文学不需要多章节解析
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 咪咕文学是短篇小说网站，直接使用单章节解析
        return self._parse_single_chapter_novel(content, novel_url, title)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 咪咕文学不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = MiguParser()
    
    # 测试单篇小说
    try:
        novel_id = "435"  # 示例ID
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
        
        # 提取章节列表（子类需要实现提取方法）
        # 这里尝试提取章节，如果没有则返回空列表
        chapters = []
        
        # 尝试使用正则表达式提取章节
        import re
        chapter_patterns = [
            r'<a[^>]*href=["']([^"']*)["'][^>]*>([^<]+)</a>',
            r'<li[^>]*><a[^>]*href=["']([^"']*)["'][^>]*>([^<]+)</a></li>',
        ]
        
        for pattern in chapter_patterns:
            matches = re.findall(pattern, content)
            if matches:
                chapters = [
                    {'url': match[0], 'title': match[1]}
                    for match in matches
                ]
                break
        
        if not chapters:
            # 无法获取章节列表，返回空结果
            logger.warning("无法获取章节列表，无法进行增量爬取")
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        # 通过比对URL找到起始位置
        start_pos = 0
        for i, chapter in enumerate(chapters):
            chapter_full_url = chapter.get('url', '')
            if chapter_full_url == start_url:
                start_pos = i + 1  # 从下一章开始
                break
        
        if start_pos >= len(chapters):
            # 没有新章节
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        logger.info(f"从第 {start_pos + 1} 章开始爬取，共 {len(chapters) - start_pos} 个新章节")
        
        # 创建小说内容
        novel_content = {
            'title': title or f'书籍-{novel_id}',
            'author': author or self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 从起始位置开始爬取
        for i in range(start_pos, len(chapters)):
            chapter = chapters[i]
            chapter_url = chapter.get('url', '')
            chapter_title = chapter.get('title', f'第{i+1}章')
            
            if not chapter_url:
                continue
            
            # 构建完整URL
            if not chapter_url.startswith('http'):
                chapter_url = f"{self.base_url}{chapter_url}"
            
            logger.info(f"正在爬取第 {i+1} 章: {chapter_title}")
            
            # 获取章节内容
            chapter_content = self._get_url_content(chapter_url)
            
            if chapter_content:
                # 提取章节内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    if processed_content and len(processed_content.strip()) > 0:
                        novel_content['chapters'].append({
                            'chapter_number': start_index + (i - start_pos) + 1,
                            'title': chapter_title,
                            'content': processed_content,
                            'url': chapter_url
                        })
                        logger.info(f"✓ 第 {i+1} 章抓取成功")
                    else:
                        logger.warning(f"✗ 第 {i+1} 章内容处理后为空")
                else:
                    logger.warning(f"✗ 第 {i+1} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {i+1} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
        
        return novel_content
