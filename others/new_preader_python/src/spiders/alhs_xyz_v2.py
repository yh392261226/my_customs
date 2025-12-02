"""
alhs.xyz 网站解析器
专门用于解析 alhs.xyz 网站的书籍内容（支持单篇和多章节）
"""

import html
import re
from typing import Dict, Any, List, Optional
from src.spiders.base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AlhsXyzV2Parser(BaseParser):
    """alhs.xyz 网站解析器"""
    
    # 基本配置
    name: str = "alhs.xyz解析器"
    description: "专门解析alhs.xyz网站的书籍内容"
    base_url: str = "https://alhs.xyz"
    
    # 支持的书籍类型 - 这个网站有单篇和多章节
    book_type: List[str] = ["短篇", "多章节"]
    
    # 标题正则表达式
    title_reg: List[str] = [
        r'<title>([^<]+)</title>',
        r'<meta property="og:title" content="([^"]+)">',
        r'<h1[^>]*>([^<]+)</h1>'
    ]
    
    # 章节列表正则表达式
    series_list_reg: List[str] = [
        r'<ul class="post-series-list">(.*?)</ul>'
    ]
    
    # 章节项正则表达式
    series_item_reg: List[str] = [
        r'<li[^>]*class="post-series-item[^"]*">.*?<span class="post-series-item-title">(.*?)</span>.*?</li>'
    ]
    
    # 章节标题和链接正则表达式
    chapter_title_link_reg: List[str] = [
        r'<span class="post-series-item-title"><a href="([^"]+)">([^<]+)</a></span>',
        r'<span class="post-series-item-title">([^<]+)</span>'
    ]
    
    # 内容正则表达式
    content_reg: List[str] = [
        r'<div class="post-content" id="post_content">(.*?)</div>'
    ]
    
    # 状态正则表达式（可选）
    status_reg: List[str] = [
        r'状态[：:]\s*([^<\s]+)',
        r'连载状态[：:]\s*([^<\s]+)'
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        alhs.xyz的URL格式: https://alhs.xyz/index.php/archives/2025/08/67909/
        
        Args:
            novel_id: 小说ID（如：2025/08/67909）
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/index.php/archives/{novel_id}/"
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型（短篇/多章节/内容页内分页）
        重写父类方法，添加alhs.xyz特定的检测逻辑
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 优先检测alhs.xyz的多章节标识，但要验证章节列表确实存在
        if '<ul class="post-series-list">' in content:
            # 直接调用章节列表提取方法来验证
            test_chapters = self._extract_series_list(content)
            if test_chapters:
                logger.info(f"检测到多章节标识，并成功提取到 {len(test_chapters)} 个章节")
                return "多章节"
            else:
                logger.info("检测到多章节标识但无法提取到有效章节，作为单篇处理")
        
        # 检测内容页内分页模式
        content_page_patterns = [
            r'开始阅读|开始阅读',
            r'<a[^>]*href="[^"]*ltxs[^"]*"[^>]*>',
            r'<a[^>]*rel="next"[^>]*>下一',
            r'下一章|下一页'
        ]
        
        for pattern in content_page_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "内容页内分页"
        
        # 检测多章节的常见模式
        multi_chapter_patterns = [
            r'章节列表|chapter.*list',
            r'第\s*\d+\s*章',
            r'目录|contents',
            r'<div[^>]*class="[^"]*chapter[^"]*"[^>]*>',
            r'<ul[^>]*class="[^"]*chapters[^"]*"[^>]*>'
        ]
        
        for pattern in multi_chapter_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "多章节"
        
        # 检测短篇的常见模式
        short_story_patterns = [
            r'短篇|short.*story',
            r'单篇|single.*chapter',
            r'全文|full.*text'
        ]
        
        for pattern in short_story_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "短篇"
        
        # 默认返回短篇
        logger.info("未检测到明确的书籍类型标识，默认为短篇")
        return "短篇"
    
    def _extract_series_list(self, content: str) -> List[Dict[str, str]]:
        """
        从页面内容中提取章节列表
        
        Args:
            content: 页面内容
            
        Returns:
            章节列表，每个元素包含 title 和 url
        """
        chapters = []
        
        # 尝试匹配章节列表
        for pattern in self.series_list_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                series_list_html = match.group(1)
                
                # 检查是否为空列表
                if not series_list_html.strip():
                    logger.info("章节列表为空")
                    return []
                
                # 提取每个章节项
                series_items = re.findall(r'<li[^>]*class="post-series-item[^"]*">(.*?)</li>', series_list_html, re.IGNORECASE | re.DOTALL)
                
                for item in series_items:
                    # 尝试提取章节标题和链接
                    if '<a href=' in item:
                        # 有链接的章节
                        title_link_match = re.search(r'<span class="post-series-item-title"><a href="([^"]+)">([^<]+)</a></span>', item, re.IGNORECASE)
                        if title_link_match:
                            chapters.append({
                                'title': title_link_match.group(2).strip(),
                                'url': title_link_match.group(1).strip()
                            })
                    else:
                        # 当前章节（没有链接）
                        current_title_match = re.search(r'<span class="post-series-item-title">([^<]+)</span>', item, re.IGNORECASE)
                        if current_title_match:
                            chapters.append({
                                'title': current_title_match.group(1).strip(),
                                'url': ''  # 当前章节没有链接
                            })
                
                if chapters:
                    logger.info(f"成功提取到 {len(chapters)} 个章节")
                else:
                    logger.info("章节列表存在但未找到有效章节项")
                return chapters
        
        logger.warning("无法找到章节列表")
        return []
    
    def _extract_content_from_div(self, content: str) -> str:
        """
        从指定的div标签中提取内容
        修复版本：使用正确的边界提取内容
        """
        # 使用正确的边界提取内容
        start_pattern = r'<div class="post-content" id="post_content">'
        end_pattern = r'<div style="font-size: 0px; height: 0px; line-height: 0px; margin: 0; padding: 0; clear: both;">'
        
        start_match = re.search(start_pattern, content, re.IGNORECASE)
        if not start_match:
            logger.warning("未找到内容开始标记")
            return ""
        
        end_match = re.search(end_pattern, content, re.IGNORECASE)
        if end_match:
            start_pos = start_match.end()
            end_pos = end_match.start()
            content_div = content[start_pos:end_pos]
        else:
            start_pos = start_match.end()
            content_div = content[start_pos:]
        
        logger.info(f"成功提取内容区域，长度: {len(content_div)}")
        
        # 去除section标签
        content_div = re.sub(r'<section class="post-series">.*?</section>', '', content_div, flags=re.IGNORECASE | re.DOTALL)
        
        # 解码HTML实体
        content_div = html.unescape(content_div)
        
        # 提取所有文本内容
        all_text_parts = []
        
        # 提取所有标签间的文本
        text_matches = re.findall(r'>([^<]+)<', content_div)
        for text in text_matches:
            clean_text = text.strip()
            if clean_text and len(clean_text) > 2:
                all_text_parts.append(clean_text)
        
        # 去重并过滤
        unique_texts = []
        seen_texts = set()
        filter_keywords = ['qq群', '推荐', '收藏', '评论', '分享', '点赞', '打赏', '广告', '联系方式', '网址', 'http', 'www', '.com', '.cn']
        
        for text in all_text_parts:
            if text not in seen_texts:
                if not any(keyword in text.lower() for keyword in filter_keywords):
                    unique_texts.append(text)
                    seen_texts.add(text)
        
        # 合并所有文本
        final_content = "\n".join(unique_texts)
        
        # 传统转简体
        # final_content = self.traditional_to_simplified(final_content)
        
        # 最后清理
        final_content = re.sub(r'\n{3,}', '\n', final_content)
        final_content = final_content.strip()
        
        logger.info(f"最终提取内容长度: {len(final_content)}")
        return final_content

    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说
        重写父类方法，实现alhs.xyz的多章节解析逻辑
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取章节列表
        chapters_info = self._extract_series_list(content)
        
        if not chapters_info:
            logger.warning("无法提取章节列表，尝试作为单篇处理")
            # 如果无法提取章节列表，回退到单篇处理
            return self._parse_single_chapter_novel(content, novel_url, title)
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取每个章节的内容
        for i, chapter_info in enumerate(chapters_info, 1):
            chapter_url = chapter_info.get('url', '')
            chapter_title = chapter_info.get('title', f'第{i}章')
            
            if chapter_url:
                # 有链接的章节，需要获取内容
                try:
                    chapter_content = self._get_url_content(chapter_url)
                    if chapter_content:
                        chapter_text = self._extract_content_from_div(chapter_content)
                        processed_content = self._execute_after_crawler_funcs(chapter_text)
                        
                        novel_content['chapters'].append({
                            'chapter_number': i,
                            'title': chapter_title,
                            'content': processed_content,
                            'url': chapter_url
                        })
                        logger.info(f"成功获取第 {i} 章: {chapter_title}")
                    else:
                        logger.warning(f"无法获取第 {i} 章内容: {chapter_title}")
                except Exception as e:
                    logger.error(f"获取第 {i} 章时出错: {e}")
                    continue
            else:
                # 当前章节（没有链接），直接从当前页面提取
                chapter_text = self._extract_content_from_div(content)
                processed_content = self._execute_after_crawler_funcs(chapter_text)
                
                novel_content['chapters'].append({
                    'chapter_number': i,
                    'title': chapter_title,
                    'content': processed_content,
                    'url': novel_url
                })
                logger.info(f"成功提取当前章节: {chapter_title}")
        
        return novel_content
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析单章节小说
        重写父类方法，添加alhs.xyz的内容处理逻辑
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 使用专门的方法提取内容
        raw_content = self._extract_content_from_div(content)
        
        if not raw_content:
            raise Exception("无法提取小说内容")
        
        # 清理HTML标签
        clean_content = self._clean_html_content(raw_content)
        
        if not clean_content:
            raise Exception("内容清理后为空")
        
        logger.info(f"成功提取内容，最终长度: {len(clean_content)}")
        
        # 执行爬取后处理函数（如果有）
        processed_content = self._execute_after_crawler_funcs(clean_content)
        
        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': processed_content,
                'url': novel_url
            }]
        }
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        alhs.xyz的ID格式: 2025/08/67909
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        try:
            # 从URL中提取路径部分
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            path = parsed.path.lstrip('/')
            
            # 移除 index.php/archives/ 前缀
            if path.startswith('index.php/archives/'):
                path = path.replace('index.php/archives/', '', 1)
            
            # 移除末尾的斜杠
            if path.endswith('/'):
                path = path[:-1]
            
            return path or "unknown"
            
        except Exception as e:
            logger.warning(f"从URL提取ID失败: {e}")
            return "unknown"