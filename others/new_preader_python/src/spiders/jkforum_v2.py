"""
jkforum.net 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class JkforumParser(BaseParser):
    """jkforum.net 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        # 禁用SSL验证以解决可能的SSL错误
        self.session.verify = False
        # 添加特定的请求头
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    # 基本信息
    name = "jkforum.net"
    description = "jkforum.net 小说解析器"
    base_url = "https://www.jkforum.net"
    
    # 正则表达式配置
    title_reg = [
        r"<h1[^>]*>(.*?)</h1>",
        r'<title>(.*?)[\s\-_]+'
    ]
    
    content_reg = [
        r'<div[^>]*class="t_fsz"[^>]*>([\s\S]*?)</div>\s*(?:</div>|$)',
        r'<div[^>]*class="t_fsz"[^>]*>([\s\S]*?)</div>',
        r"<div[^>]*class=\"nv-content-wrap entry-content\"[^>]*>(.*?)</div>"
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型
    book_type = ["短篇"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_content_obs",  # 清理内容中的干扰
        "_remove_ads"  # 移除广告
    ]

    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        重写基类的正则提取方法，专门处理jkforum.net的嵌套div结构
        
        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        # 检查是否是内容提取（通过比较regex_list与content_reg）
        is_content_extraction = regex_list == self.content_reg
        
        # 如果是内容提取，首先尝试使用自定义的嵌套div提取函数
        if is_content_extraction:
            extracted = self._extract_content_div(content)
            if extracted and extracted.strip():
                return extracted
        
        # 使用原始的正则方法（适用于标题和其他非内容提取）
        for regex in regex_list:
            matches = re.findall(regex, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted = match.strip() if isinstance(match, str) else match[0].strip() if match else ""
                if extracted:  # 确保内容不是空的
                    return extracted
        return ""

    def _extract_content_div(self, html: str) -> str:
        """
        专门处理嵌套div的内容提取函数
        能够正确提取所有<div class="t_fsz">及其所有嵌套内容
        页面中可能存在多个t_fsz div，每个都包含一个书籍内容
        
        Args:
            html: HTML内容
            
        Returns:
            提取的所有内容部分（多个div内容合并，用分隔符分开）
        """
        import re
        
        # 找到所有t_fsz div的开始位置
        start_pattern = re.compile(r'<div[^>]*class="t_fsz"[^>]*>', re.IGNORECASE)
        all_matches = list(start_pattern.finditer(html))
        
        if not all_matches:
            return ""
        
        # 存储所有提取的内容
        all_contents = []
        
        # 遍历每个t_fsz div
        for match_idx, start_match in enumerate(all_matches):
            start_pos = start_match.end()
            
            # 使用更精确的方法来匹配嵌套div
            depth = 1
            pos = start_pos
            content_end = -1
            
            while pos < len(html) and depth > 0:
                # 查找下一个div开标签和闭标签
                next_open = html.find('<div', pos)
                next_close = html.find('</div>', pos)
                
                if next_close == -1:
                    break
                    
                if next_open != -1 and next_open < next_close:
                    # 先遇到开标签
                    depth += 1
                    pos = next_open + 4  # 跳过"<div"
                else:
                    # 先遇到闭标签
                    depth -= 1
                    if depth == 0:
                        content_end = next_close
                        break
                    pos = next_close + 6  # 跳过"</div>"
            
            if content_end != -1:
                content = html[start_pos:content_end]
                # 清理广告和不需要的div内容
                cleaned_content = self._clean_nested_content(content)
                if cleaned_content and cleaned_content.strip():
                    all_contents.append(cleaned_content)
        
        # 合并所有内容，使用分隔符
        if all_contents:
            return '\n\n---\n\n'.join(all_contents)
        
        return ""

    def _clean_nested_content(self, content: str) -> str:
        """
        清理嵌套div中的内容，移除广告和不需要的div，保留主要文本内容
        
        Args:
            content: 原始嵌套内容
            
        Returns:
            清理后的内容
        """
        import re
        
        # 移除table标签但保留内容
        content = re.sub(r'<table[^>]*>.*?</table>', lambda m: re.sub(r'<[^>]+>', '', m.group(0)), content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除td/tr标签但保留内容
        content = re.sub(r'<t[d|h][^>]*>(.*?)</t[d|h]>', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除广告相关的div
        ad_patterns = [
            r'<div[^>]*class="cm"[^>]*>.*?</div>\s*',
            r'<div[^>]*id="[^"]*"[^>]*>.*?</div>\s*',
            r'<form[^>]*>.*?</form>\s*',
            r'<script[^>]*>.*?</script>\s*',
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 提取所有font标签的内容
        font_content = re.findall(r'<font[^>]*>(.*?)</font>', content, re.IGNORECASE | re.DOTALL)
        
        # 合并所有font标签内容
        if font_content:
            extracted_text = '\n'.join([f.strip() for f in font_content if f.strip()])
        else:
            # 如果没有找到font标签，移除所有HTML标签但保留文本内容
            extracted_text = re.sub(r'<[^>]+>', '', content, flags=re.IGNORECASE)
            # 清理空白字符
            extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
        
        # 处理特殊的bbcode标签
        extracted_text = re.sub(r'\[/?[^\]]+\]', '', extracted_text)
        
        return extracted_text
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配jkforum.net的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/p/thread-{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，jkforum.net主要是短篇小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # jkforum.net主要是短篇小说
        return "短篇"
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写单章节小说解析逻辑，适配jkforum.net的特定结构
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 使用配置的正则提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)
        
        # 检查内容是否有效（至少包含一些中文字符）
        if not processed_content or len(processed_content.strip()) < 50:
            raise Exception("提取的内容为空或过短")
        
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
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 匹配 thread-数字-1-1 格式
        match = re.search(r'thread-(\d+)-\d+-\d+', url)
        if match:
            return match.group(1)
        
        # 备用匹配：提取 thread- 后面的数字
        match = re.search(r'thread-(\d+)', url)
        return match.group(1) if match else "unknown"
    
    def _clean_content_specific(self, content: str) -> str:
        """
        清理jkforum.net特定的内容干扰
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 首先移除script和style标签及其内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除常见的导航和广告元素
        ad_patterns = [
            r'上一章.*?下一章',
            r'返回.*?目录',
            r'本章.*?字数',
            r'更新时间.*?\d{4}-\d{2}-\d{2}',
            r'作者.*?更新时间',
            r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',
            # 移除引用、签名等特定元素
            r'<div[^>]*class="[^"]*quote[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*sign[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*avatar[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*userinfo[^"]*"[^>]*>.*?</div>',
            r'&quot;',
            r'&nbsp;',
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        return content.strip()
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写首页元数据获取，适配jkforum.net的特定结构
        
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
        
        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "tags": "",
            "desc": "短篇小说",
            "status": status or "未知状态"
        }
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - jkforum.net不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []