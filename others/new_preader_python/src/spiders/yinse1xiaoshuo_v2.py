"""
yinse1xiaoshuo.com 解析器
网站: https://www.yinse1xiaoshuo.com/
特点: 短篇小说，支持内容页内分页
基于配置驱动版本
"""

from src.utils.logger import get_logger
import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class Yinse1xiaoshuoParser(BaseParser):
    """yinse1xiaoshuo.com 解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "yinse1xiaoshuo"
    description = "yinse1xiaoshuo.com 短篇小说解析器"
    base_url = "https://www.yinse1xiaoshuo.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="article-title"[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<article[^>]*class="article"[^>]*>(.*?)</article>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="article-content"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<span[^>]*class="status"[^>]*>(.*?)</span>',
        r'<div[^>]*class="status"[^>]*>(.*?)</div>'
    ]
    
    # 书籍类型配置
    book_type = ["内容页内分页"]
    
    # 分页相关配置
    content_page_link_reg = [
        r'<li><a[^>]*href="([^"]*)"[^>]*>.*?下一页.*?</a></li>',
        r'<a[^>]*class="next"[^>]*href="([^"]*)"[^>]*>下一页</a>',
        r'<a[^>]*href="([^"]*)"[^>]*>下一页</a>',
        r'<a[^>]*class="page-next"[^>]*href="([^"]*)"[^>]*>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配yinse1xiaoshuo.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/article/{novel_id}/"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，yinse1xiaoshuo.com支持分页
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检测是否有分页链接
        if re.search(r'下一页', content) and re.search(r'href="[^"]*"', content):
            return "内容页内分页"
        return "短篇"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - yinse1xiaoshuo.com不需要多章节解析
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # yinse1xiaoshuo.com是短篇小说网站，直接使用单章节解析
        return self._parse_single_chapter_novel(content, novel_url, title)
    
    def _parse_content_pagination_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析内容页内分页模式的小说
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        all_content = []
        current_url = novel_url
        page_count = 1
        
        logger.info(f"开始爬取分页内容: {title}")
        
        while current_url:
            # 获取当前页面内容
            if current_url != novel_url:
                page_content = self._get_url_content(current_url)
                if not page_content:
                    print(f"无法获取页面内容: {current_url}")
                    break
            else:
                page_content = content
            
            # 提取当前页面的文章内容
            page_article_content = self._extract_with_regex(page_content, self.content_reg)
            if page_article_content:
                # 执行后处理函数清理HTML内容
                cleaned_content = self._execute_after_crawler_funcs(page_article_content)
                all_content.append(cleaned_content)
                print(f"已获取第 {page_count} 页内容")
            
            # 查找下一页链接
            next_page_url = self._get_next_page_url(page_content)
            
            # 检查是否到达最后一页
            if not next_page_url or "javascript:Wntheme.Layer.Error('没有下一页啦~');" in next_page_url:
                print("已到达最后一页")
                break
            
            # 构建完整的下一页URL
            if next_page_url.startswith('/'):
                next_page_url = f"{self.base_url}{next_page_url}"
            elif not next_page_url.startswith('http'):
                next_page_url = f"{novel_url.rsplit('/', 1)[0]}/{next_page_url}"
            
            current_url = next_page_url
            page_count += 1
            
            # 添加延迟避免请求过快
            import time
            time.sleep(1)
        
        # 合并所有页面内容
        merged_content = "\n\n".join(all_content)
        
        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': merged_content,
                'url': novel_url
            }]
        }
    
    def _get_next_page_url(self, content: str) -> str:
        """
        获取下一页的URL
        
        Args:
            content: 页面内容
            
        Returns:
            下一页URL或空字符串
        """
        for regex in self.content_page_link_reg:
            matches = re.findall(regex, content, re.IGNORECASE)
            for match in matches:
                if match and match.strip():
                    return match.strip()
        return ""
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - yinse1xiaoshuo.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _clean_html_content(self, content: str) -> str:
        """
        重写HTML内容清理方法，适配yinse1xiaoshuo.com的特殊格式
        
        Args:
            content: 原始HTML内容
            
        Returns:
            清理后的文本内容
        """
        # 先调用父类的清理方法
        content = super()._clean_html_content(content)
        
        # yinse1xiaoshuo.com特有的清理逻辑
        # 移除HTML实体编码
        import html
        content = html.unescape(content)
        
        # 移除多余的空白字符
        content = ' '.join(content.split())
        
        return content.strip()


# 使用示例
if __name__ == "__main__":
    parser = Yinse1xiaoshuoParser()
    
    # 测试单篇小说
    try:
        novel_id = "910"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")