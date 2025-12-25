"""
aiwenzhang.pics 小说网站解析器
继承自 BaseParser，使用属性配置实现
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AiwenzhangParser(BaseParser):
    """aiwenzhang.pics 小说解析器"""
    
    # 基本信息
    name = "aiwenzhang.pics"
    description = "aiwenzhang.pics 小说解析器"
    base_url = "https://aiwenzhang.pics"
    
    # 正则表达式配置
    title_reg = [
        r'<a[^>]*href="javascript:;">(.*?)</a>'
    ]
    
    # 内容正则表达式 - 使用贪婪模式匹配整个content div
    content_reg = [
        r'<div[^>]*class="content"[^>]*style="text-align: left"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        r'<div[^>]*class="content"[^>]*style="text-align: left"[^>]*>(.*?)(?=</div>\s*</div>\s*</div>|$)'
    ]
    
    # 支持的书籍类型
    book_type = ["短篇"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_content_specific",  # 特定内容清理
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/index.php/art/detail/id/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型
        对于 aiwenzhang.pics 网站，所有内容都是短篇
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _clean_content_specific(self, content: str) -> str:
        """
        针对aiwenzhang.pics网站的内容清理
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return content
            
        # 移除常见的广告和无关内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL)
        content = re.sub(r'<footer[^>]*>.*?</footer>', '', content, flags=re.DOTALL)
        content = re.sub(r'<header[^>]*>.*?</header>', '', content, flags=re.DOTALL)
        
        # 处理多个连续的div标签 - 使用贪婪模式匹配
        # 确保不会因为嵌套div导致内容被截断
        content = re.sub(r'<div[^>]*>', '', content)
        content = re.sub(r'</div>', '', content)
        
        # 处理其他HTML标签，但先保留段落结构
        content = re.sub(r'<p[^>]*>', '\n\n', content)
        content = re.sub(r'</p>', '\n', content)
        content = re.sub(r'<br[^>]*>', '\n', content)
        content = re.sub(r'<li[^>]*>', '\n• ', content)
        content = re.sub(r'</li>', '\n', content)
        
        # 移除剩余的HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 处理HTML实体
        content = re.sub(r'&ldquo;', '"', content)
        content = re.sub(r'&rdquo;', '"', content)
        content = re.sub(r'&lsquo;', "'", content)
        content = re.sub(r'&rsquo;', "'", content)
        content = re.sub(r'&hellip;', '...', content)
        content = re.sub(r'&nbsp;', ' ', content)
        content = re.sub(r'&amp;', '&', content)
        content = re.sub(r'&lt;', '<', content)
        content = re.sub(r'&gt;', '>', content)
        content = re.sub(r'&quot;', '"', content)
        
        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'^[ \t]+', '', content, flags=re.MULTILINE)  # 移除行首空格
        content = content.strip()
        
        return content