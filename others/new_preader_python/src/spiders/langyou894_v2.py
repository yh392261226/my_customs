"""
狼人小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Langyou894Parser(BaseParser):
    """狼人小说网站解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "狼人小说"
    description = "狼人小说网站解析器"
    base_url = "https://www.langyou894.cc"
    
    # 正则表达式配置 - 标题提取
    title_reg = [
        r'<div class="media">.*?<div style="text-align: center;">(.*?)</div>.*?</div>',
        r'<div style="text-align: center;">(.*?)</div>',
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>',
        r'<h2[^>]*>(.*?)</h2>',
        r'<h3[^>]*>(.*?)</h3>',
        r'<h4[^>]*>(.*?)</h4>'
    ]
    
    # 正则表达式配置 - 内容提取
    content_reg = [
        r'<div class="media">.*?<div class="artcontent">(.*?)</div>.*?</div>',
        r'<div class="artcontent">(.*?)</div>',
        r'<div class="article-content">(.*?)</div>',
        r'<div class="content">(.*?)</div>',
        r'<div class="post-content">(.*?)</div>',
        r'<div class="entry-content">(.*?)</div>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    # 状态正则表达式配置
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型 - 都是短篇
    book_type = ["短篇"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，确保始终返回"短篇"
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型 - 始终返回"短篇"
        """
        return "短篇"
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/artdetail-{novel_id}.html"
    
    def extract_title(self, html: str) -> str:
        """
        提取书籍标题，重写基类方法以适应特殊格式
        
        Args:
            html: 页面HTML内容
            
        Returns:
            提取的标题文本
        """
        try:
            # 对于狼人小说网站，标题在<div class="media"></div>标签下的<div style="text-align: center;"></div>标签内
            media_match = re.search(r'<div class="media">(.*?)</div>', html, re.DOTALL)
            if media_match:
                media_content = media_match.group(1)
                # 查找居中的div标签
                title_div_match = re.search(r'<div style="text-align: center;">(.*?)</div>', media_content, re.DOTALL)
                if title_div_match:
                    title = title_div_match.group(1)
                    # 直接返回标题，将由after_crawler_func处理清理
                    return title
            
            # 如果没有找到，尝试使用默认正则提取
            return self._extract_with_regex(html, self.title_reg)
            
        except Exception as e:
            logger.warning(f"标题提取失败: {e}")
            return ""
    
    def extract_content(self, html: str) -> str:
        """
        提取书籍内容，重写基类方法以适应特殊格式
        
        Args:
            html: 页面HTML内容
            
        Returns:
            提取的文本内容
        """
        try:
            # 对于狼人小说网站，内容在<div class="media"></div>标签下的<div class="artcontent"></div>标签内
            media_match = re.search(r'<div class="media">(.*?)</div>', html, re.DOTALL)
            if media_match:
                media_content = media_match.group(1)
                # 查找artcontent div标签
                content_div_match = re.search(r'<div class="artcontent">(.*?)</div>', media_content, re.DOTALL)
                if content_div_match:
                    content = content_div_match.group(1)
                    # 直接返回内容，将由after_crawler_func处理清理
                    return content
            
            # 如果没有找到，尝试使用默认正则提取
            return self._extract_with_regex(html, self.content_reg)
            
        except Exception as e:
            logger.warning(f"内容提取失败: {e}")
            return ""