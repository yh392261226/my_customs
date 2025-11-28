"""
爱69小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class Ai69novelParser(BaseParser):
    """爱69小说网站解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "爱69小说"
    description = "爱69小说网站单篇小说爬取解析器"
    base_url = "https://ai69novel.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="title entry-title"[^>]*>([^<]+)</h1>',
        r'<title>([^<]+)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*class="nv-content-wrap entry-content"[^>]*>(.*?)</div>',
        r'<div class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="entry-content"[^>]*>(.*?)</div>',
        r'<main[^>]*class="neve-main"[^>]*>.*?<div[^>]*class="nv-content-wrap entry-content"[^>]*>(.*?)</div>',
        r'<article[^>]*>.*?<div[^>]*class="nv-content-wrap entry-content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<meta[^>]*property="article:section"[^>]*content="([^"]*)"',
        r'状态[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型 - 只有单篇
    book_type = ["短篇"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_special_chars",  # 清理特殊字符
        "_remove_share_buttons"  # 移除分享按钮
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/archives/{novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型 - 爱69小说只有单篇
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _clean_special_chars(self, content: str) -> str:
        """
        清理特殊字符
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        import re
        
        # 替换HTML实体和特殊空白字符
        content = content.replace('&emsp;', ' ')
        content = content.replace('&nbsp;', ' ')
        content = content.replace('\xa0', ' ')
        
        # 清理多余的换行和空格
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'<br\s*/?>', '\n', content)
        
        return content.strip()
    
    def _remove_share_buttons(self, content: str) -> str:
        """
        移除分享按钮等无关内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        import re
        
        # 移除分享按钮相关内容
        patterns_to_remove = [
            r'<div[^>]*class=\'heateorSssClear\'[^>]*>.*?</div>',
            r'<div[^>]*class=\'heateor_sss_sharing_container[^>]*>.*?</div>',
            r'<div[^>]*class=\'heateor_sss_sharing_title[^>]*>.*?</div>',
            r'<div[^>]*class=\'heateor_sss_sharing_ul[^>]*>.*?</div>',
            r'<a[^>]*class=\'heateor_sss_[^>]*>.*?</a>',
            r'<span[^>]*class=\'heateor_sss_svg[^>]*>.*?</span>',
            r'<svg[^>]*>.*?</svg>',
            r'\(ai69novel\.com 爱69小说\)',
            r'独乐乐不如众乐乐 - 分享出去'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content.strip()
    
    def _extract_content_from_full_page(self, content: str) -> str:
        """
        从完整页面中提取小说内容
        
        Args:
            content: 页面内容
            
        Returns:
            提取的小说内容
        """
        import re
        
        # 首先尝试使用现有的正则表达式
        extracted = self._extract_with_regex(content, self.content_reg)
        if extracted and len(extracted) > 100:  # 如果内容长度合理
            return extracted
        
        # 如果现有正则失败，尝试更精确的提取
        # 查找nv-content-wrap entry-content div中的所有段落
        content_div_pattern = r'<div[^>]*class="nv-content-wrap entry-content"[^>]*>(.*?)</div>'
        content_div_match = re.search(content_div_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if content_div_match:
            div_content = content_div_match.group(1)
            
            # 提取所有段落
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', div_content, re.IGNORECASE | re.DOTALL)
            
            # 过滤掉包含分享按钮等无关内容的段落
            clean_paragraphs = []
            for p in paragraphs:
                # 清理HTML标签
                clean_p = re.sub(r'<[^>]+>', '', p).strip()
                
                # 过滤条件：长度大于20，不包含分享相关关键词和脚本代码
                if (len(clean_p) > 20 and 
                    'heateor' not in clean_p and 
                    '分享' not in clean_p and
                    'Facebook' not in clean_p and
                    'Twitter' not in clean_p and
                    'svg' not in clean_p and
                    'button' not in clean_p and
                    'function' not in clean_p and
                    'var ' not in clean_p and
                    'jQuery' not in clean_p and
                    '/* ' not in clean_p and
                    '*/' not in clean_p and
                    'Skip to content' not in clean_p):
                    clean_paragraphs.append(clean_p)
            
            if clean_paragraphs:
                return '\n\n'.join(clean_paragraphs)
        
        # 如果还是没找到，尝试从整个页面提取段落
        all_paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.IGNORECASE | re.DOTALL)
        clean_paragraphs = []
        
        for p in all_paragraphs:
            clean_p = re.sub(r'<[^>]+>', '', p).strip()
            if (len(clean_p) > 50 and  # 增加长度要求确保是正文
                '爱69色情小说' not in clean_p and  # 过滤侧边栏内容
                '每日更新色情小說' not in clean_p and
                'function' not in clean_p and  # 过滤脚本
                'var ' not in clean_p and
                'jQuery' not in clean_p and
                '/* ' not in clean_p and
                '*/' not in clean_p):
                clean_paragraphs.append(clean_p)
        
        if clean_paragraphs:
            return '\n\n'.join(clean_paragraphs)
        
        return ""
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析单章节小说 - 重写以适配爱69小说的结构
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 使用新的内容提取方法
        chapter_content = self._extract_content_from_full_page(content)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 执行其他处理函数（跳过内容提取，因为已经执行过了）
        processed_content = chapter_content
        
        # 执行HTML清理和特殊字符清理
        processed_content = self._clean_html_content(processed_content)
        processed_content = self._clean_special_chars(processed_content)
        processed_content = self._remove_share_buttons(processed_content)
        
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
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        重写以适配爱69小说网站的结构
        
        Args:
            novel_id: 小说ID
            
        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            return None
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        
        # 提取内容作为简介
        content_text = self._extract_with_regex(content, self.content_reg)
        if content_text:
            # 清理内容作为简介
            desc = self._execute_after_crawler_funcs(content_text)
            desc = desc[:200] + "..." if len(desc) > 200 else desc
        else:
            desc = "暂无简介"
        
        # 提取状态/分类
        status = self._extract_with_regex(content, self.status_reg)
        
        # 提取标签
        tags = self._extract_tags(content)
        
        return {
            "title": title or "未知标题",
            "desc": desc or "暂无简介",
            "status": status or "未知状态",
            "tags": tags or ""
        }
    
    def _extract_tags(self, content: str) -> str:
        """
        提取书籍标签
        
        Args:
            content: 页面内容
            
        Returns:
            书籍标签（逗号分隔）
        """
        import re
        
        # 从meta标签提取文章标签
        pattern = r'<meta[^>]*property="article:tag"[^>]*content="([^"]*)"'
        matches = re.findall(pattern, content, re.IGNORECASE)
        
        if matches:
            return ', '.join(matches)
        
        # 如果没有找到，尝试从其他地方提取
        return ""
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        import re
        
        # 从URL中提取archives/后面的数字
        match = re.search(r'/archives/(\d+)', url)
        if match:
            return match.group(1)
        
        # 如果没有找到，使用默认方法
        return super()._extract_novel_id_from_url(url)
