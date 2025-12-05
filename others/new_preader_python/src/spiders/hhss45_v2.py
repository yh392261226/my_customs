"""
红尘黄书网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Hhss45Parser(BaseParser):
    """红尘黄书网站解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "红尘黄书"
    description = "红尘黄书网站解析器"
    base_url = "https://www.hhss45.top"
    
    # 正则表达式配置 - 标题提取
    title_reg = [
        r'<title>\【(.*?)\】.*?</title>',  # 从title标签中提取【】内的内容
        r'<h1 class="article-title"><a[^>]*>(.*?)</a></h1>',
        r'<h1[^>]*class="article-title"[^>]*><a[^>]*>(.*?)</a></h1>',
        r'<h1 class="article-title"[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    # 正则表达式配置 - 内容提取
    content_reg = [
        r'<article class="article-content">.*?<div>(.*?)</div></article>',
        r'<div>(.*?)</div>'
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
            # 使用基类的 _extract_with_regex 方法尝试提取标题
            title = self._extract_with_regex(html, self.title_reg)
            if title:
                logger.info(f"通过默认正则提取到标题: {title}")
                return title
            
            logger.warning("无法提取标题")
            return ""
            
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
            # 首先检查是否是权限受限页面
            if "您没有权限访问此数据" in html or "请升级会员" in html:
                logger.warning("页面显示需要会员权限，无法访问内容")
                return "页面访问受限，需要会员权限"
            
            # 检查是否是系统提示页面
            if "系统提示" in html and "亲爱的：" in html:
                logger.warning("页面显示为系统提示页面，不是正常内容页")
                return "页面访问受限，系统提示需要权限"
            
            # 对于红尘黄书网站，内容在<article class="article-content">标签内
            article_match = re.search(r'<article class="article-content">(.*?)</article>', html, re.DOTALL)
            if not article_match:
                logger.warning("未找到article-content标签")
            else:
                logger.info("找到article-content标签")
                article_content = article_match.group(1)
                
                # 直接匹配没有任何class或id属性的div标签
                # 这种模式匹配：<div>内容</div>，确保不匹配任何有class或id的div
                content_div_match = re.search(r'<div(?![^>]*class)(?![^>]*id)[^>]*>(.*?)</div>', article_content, re.DOTALL)
                
                if content_div_match:
                    content_div = content_div_match.group(1)
                    logger.info(f"找到内容div（无class/id属性），长度: {len(content_div)}")
                    logger.info(f"内容div前100字符: {content_div[:100]}")
                    # 直接返回内容，将由after_crawler_func处理清理
                    return content_div
                else:
                    logger.warning("未找到没有class/id属性的div标签")
                    # 如果没有找到，尝试使用默认正则提取
                    content = self._extract_with_regex(html, self.content_reg)
                    if content:
                        logger.info(f"通过默认正则提取到内容，长度: {len(content)}")
                        return content
                    return ""
            
            # 如果没有找到，尝试使用默认正则提取
            content = self._extract_with_regex(html, self.content_reg)
            if content:
                logger.info(f"通过默认正则提取到内容，长度: {len(content)}")
                return content
                
            # 输出HTML的前500个字符用于调试
            logger.warning(f"无法提取内容，HTML内容前500字符: {html[:500]}")
            return ""
            
        except Exception as e:
            logger.warning(f"内容提取失败: {e}")
            return ""