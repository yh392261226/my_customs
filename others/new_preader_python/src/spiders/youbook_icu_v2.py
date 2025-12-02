"""
youbook.icu 网站解析器
专门用于解析 youbook.icu 网站的单篇书籍内容
"""

import html
import re
from typing import Dict, Any, List, Optional
from src.spiders.base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class YoubookIcuV2Parser(BaseParser):
    """youbook.icu 网站解析器"""
    
    # 基本配置
    name: str = "youbook.icu解析器"
    description: str = "专门解析youbook.icu网站的单篇书籍内容"
    base_url: str = "https://youbook.icu"
    
    # 支持的书籍类型 - 这个网站只有单篇书籍
    book_type: List[str] = ["短篇"]
    
    # 标题正则表达式
    title_reg: List[str] = [
        r'<title>([^<]+)</title>',
        r'<h3><b><span[^>]*>([^<]+)</span></b></h3>',
        r'<h1[^>]*>([^<]+)</h1>'
    ]
    
    # 内容正则表达式 - 重点匹配指定的div标签
    content_reg: List[str] = [
        r'<div class="art-content pt10 f16 lh200"[^>]*>(.*?)</div>',
        r'<div[^>]*class="art-content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*style="font-size:20px[^"]*"[^>]*>(.*?)</div>'
    ]
    
    # 状态正则表达式（可选）
    status_reg: List[str] = [
        r'状态[：:]\s*([^<\s]+)',
        r'连载状态[：:]\s*([^<\s]+)'
    ]
    
    # 处理函数配置
    after_crawler_func: List[str] = [
        "_clean_html_content",      # 公共基类提供的HTML清理
        "_decode_html_entities",    # HTML实体解码
        "_convert_traditional_to_simplified", # 繁体字转换成简体字
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        youbook.icu的URL格式: https://youbook.icu/wife/书籍ID
        
        Args:
            novel_id: 小说ID（如：wife/我的婚紗照）
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/{novel_id}"
    
    
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容，提取纯文本
        重写父类方法，添加HTML实体解码功能
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        # 先调用父类方法进行基本清理
        clean_text = super()._clean_html_content(html_content)
        
        # HTML实体解码 - 这是关键功能
        clean_text = html.unescape(clean_text)
        
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)
        
        return clean_text.strip()
    
    def _extract_content_from_div(self, content: str) -> str:
        """
        从指定的div标签中提取内容
        处理可能存在的嵌套div标签情况
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容
        """
        # 尝试匹配主要内容区域
        for pattern in self.content_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                div_content = match.group(1)
                logger.info(f"成功匹配到内容区域，长度: {len(div_content)}")
                
                # 检查是否包含嵌套的div标签
                nested_divs = re.findall(r'<div[^>]*>(.*?)</div>', div_content, re.IGNORECASE | re.DOTALL)
                if nested_divs:
                    logger.info(f"发现 {len(nested_divs)} 个嵌套的div标签")
                
                return div_content
        
        # 如果没有匹配到，尝试更宽泛的匹配
        fallback_patterns = [
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*art[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>'
        ]
        
        for pattern in fallback_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                logger.info(f"使用备用模式匹配到内容区域")
                return match.group(1)
        
        logger.warning("无法找到内容区域")
        return ""
    
    def _decode_html_entities(self, text: str) -> str:
        """
        解码HTML实体字符
        重写父类方法，添加youbook.icu特定的解码逻辑
        处理 &#28014;&#22631;&#28415; 这样的实体编码
        
        Args:
            text: 包含HTML实体的文本
            
        Returns:
            解码后的文本
        """
        try:
            # 使用html模块的unescape方法
            decoded_text = html.unescape(text)
            
            # 如果unescape没有完全解码，尝试手动处理
            if '&#' in decoded_text:
                # 使用正则表达式匹配所有HTML实体
                def replace_entity(match):
                    entity = match.group(1)
                    try:
                        if entity.startswith('x') or entity.startswith('X'):
                            # 十六进制实体
                            return chr(int(entity[1:], 16))
                        else:
                            # 十进制实体
                            return chr(int(entity))
                    except (ValueError, OverflowError):
                        return match.group(0)  # 保持原样
                
                decoded_text = re.sub(r'&(\d+|x[0-9a-fA-F]+);', replace_entity, decoded_text)
            
            # 添加youbook.icu特定的处理逻辑
            if decoded_text != text:
                logger.info(f"HTML实体解码成功，处理了 {len(re.findall(r'&\d+;|&x[0-9a-fA-F]+;', text))} 个实体")
            
            return decoded_text
            
        except Exception as e:
            logger.warning(f"HTML实体解码失败: {e}")
            return text
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析单章节小说
        重写父类方法，添加HTML实体解码功能
        
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
        
        # HTML实体解码 - 关键步骤
        decoded_content = self._decode_html_entities(clean_content)
        
        if not decoded_content:
            raise Exception("内容解码后为空")
        
        logger.info(f"成功提取和解码内容，最终长度: {len(decoded_content)}")
        
        # 执行爬取后处理函数（按配置顺序执行）
        processed_content = self._execute_after_crawler_funcs(decoded_content)
        
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
        youbook.icu的ID格式可能包含路径，如 wife/我的婚紗照
        
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
            
            # 移除开头的斜杠
            if path.startswith('/'):
                path = path[1:]
            
            return path or "unknown"
            
        except Exception as e:
            logger.warning(f"从URL提取ID失败: {e}")
            return "unknown"