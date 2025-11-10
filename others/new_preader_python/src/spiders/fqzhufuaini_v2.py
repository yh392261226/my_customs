"""
FQZhufuaini网站解析器
支持 https://fq.zhufuaini.top/ 网站的短篇小说解析
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser


class FQZhufuainiParser(BaseParser):
    """FQZhufuaini网站解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "FQZhufuaini"
    description = "FQZhufuaini短篇小说解析器"
    base_url = "https://fq.zhufuaini.top"
    
    # 正则表达式配置
    title_reg = [
        r'<h2[^>]*>([^<]+)</h2>',  # 标题在h2标签中
        r'<title[^>]*>([^<]+)</title>'  # 备用：从title标签提取
    ]
    
    # 状态提取 - 来源信息
    status_reg = [
        r"<span[^>]*class=['\"]tags['\"][^>]*>([^<]+)</span>",  # 来源信息
        r"来源[：:]([^<]+)"  # 备用模式
    ]
    
    # 内容提取 - 小说内容在div class="entry"中的第一个div标签内
    content_reg = [
        r'<div[^>]*class="entry"[^>]*>\s*<div[^>]*>([\s\S]*?)</div>\s*</div>',  # 主内容提取
        r'<div[^>]*class="entry"[^>]*>([\s\S]*?)</div>',  # 备用：整个entry内容
        r'<div[^>]*id="post-[^>]*>\s*<div[^>]*class="entry"[^>]*>([\s\S]*?)</div>',  # 包含post-id的提取
    ]
    
    # 书籍类型配置 - 这个网站主要是短篇小说
    book_type = ["短篇"]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配FQZhufuaini网站的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/index.php/art/detail/id/{novel_id}.html"
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取标题
        title = self._extract_title(content)
        if not title:
            raise Exception("无法提取小说标题")
        
        # 提取状态（来源信息）
        status = self._extract_status(content)
        
        # 提取内容
        novel_content = self._extract_content(content)
        if not novel_content:
            raise Exception("无法提取小说内容")
        
        print(f"开始处理 [ {title} ] - 状态: {status}")
        
        # 清理和格式化内容
        cleaned_content = self._clean_and_format_content(novel_content)
        
        return {
            'title': title,
            'author': self.novel_site_name or self.name,
            'novel_id': novel_id,
            'url': novel_url,
            'description': f"短篇小说 - {status}",
            'status': status,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': cleaned_content,
                'url': novel_url
            }]
        }
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题
        
        Args:
            content: 页面内容
            
        Returns:
            小说标题
        """
        # 优先从h2标签提取
        for pattern in self.title_reg:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # 清理标题中的特殊字符和多余空格
                title = re.sub(r'[『』]', '', title).strip()
                if title:
                    return title
        
        # 如果从h2标签提取失败，尝试从title标签提取
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            # 清理标题中的网站名称
            title = re.sub(r'\s*-\s*风情小说.*$', '', title).strip()
            if title:
                return title
        
        return ""
    
    def _extract_status(self, content: str) -> str:
        """
        提取小说状态（来源信息）
        
        Args:
            content: 页面内容
            
        Returns:
            状态信息
        """
        for pattern in self.status_reg:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                status = match.group(1).strip()
                # 清理HTML标签
                status = re.sub(r'<[^>]+>', '', status)
                status = re.sub(r'\s+', ' ', status)
                return status.strip()
        
        return "未知来源"
    
    def _extract_content(self, content: str) -> str:
        """
        提取小说内容
        
        Args:
            content: 页面内容
            
        Returns:
            小说内容
        """
        for pattern in self.content_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_content = match.group(1).strip()
                # 清理掉版权信息
                cleaned_content = self._remove_copyright_info(extracted_content)
                return cleaned_content
        
        # 如果标准提取失败，尝试更宽松的提取
        # 查找包含p标签的内容区域
        p_content_match = re.search(
            r'<div[^>]*class="entry"[^>]*>(.*?)(?:<div[^>]*class="copyright"|<div[^>]*class="relatedpost")',
            content, re.IGNORECASE | re.DOTALL
        )
        if p_content_match:
            extracted_content = p_content_match.group(1).strip()
            # 清理掉版权信息
            cleaned_content = self._remove_copyright_info(extracted_content)
            return cleaned_content
        
        return ""
    
    def _remove_copyright_info(self, content: str) -> str:
        """
        清理掉<div class="copyright"></div>标签中的全部内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 移除整个copyright div标签及其内容
        content = re.sub(r'<div[^>]*class="copyright"[^>]*>[\s\S]*?</div>', '', content, flags=re.IGNORECASE)
        
        # 移除可能存在的其他版权信息标签
        content = re.sub(r'<div[^>]*class="copyright-info"[^>]*>[\s\S]*?</div>', '', content, flags=re.IGNORECASE)
        
        # 移除可能存在的版权文本
        content = re.sub(r'版权声明[\s\S]*?(?:<\/div>|$)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'版权信息[\s\S]*?(?:<\/div>|$)', '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _clean_and_format_content(self, content: str) -> str:
        """
        清理和格式化小说内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 1. 清理HTML标签，保留p标签用于段落分隔
        # 首先将p标签转换为换行符
        content = re.sub(r'</p>', '\n\n', content)
        # 然后移除所有其他HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 2. 替换HTML实体
        content = content.replace('&nbsp;', ' ').replace('\xa0', ' ')
        
        # 3. 清理多余的空格和换行
        # 合并多个连续空格
        content = re.sub(r' +', ' ', content)
        # 合并多个连续换行符
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'\n+', '\n', content)
        
        # 4. 清理开头和结尾的空格
        content = content.strip()
        
        # 5. 确保每段开头没有空格
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:  # 只保留非空行
                cleaned_lines.append(cleaned_line)
        
        return '\n\n'.join(cleaned_lines)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（如果需要支持列表解析）
        
        Args:
            url: 列表页URL
            
        Returns:
            小说信息列表
        """
        # 这个网站主要是详情页，列表解析不是主要功能
        # 可以根据需要实现
        return []
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说（这个网站主要是短篇，但保留接口）
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说内容字典
        """
        # 对于短篇小说网站，默认使用单章节处理
        return self._parse_single_chapter_novel(content, novel_url, title)
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析单章节小说
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取状态
        status = self._extract_status(content)
        
        # 提取内容
        novel_content = self._extract_content(content)
        if not novel_content:
            raise Exception("无法提取小说内容")
        
        # 清理和格式化内容
        cleaned_content = self._clean_and_format_content(novel_content)
        
        return {
            'title': title,
            'author': self.novel_site_name or self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'description': f"短篇小说 - {status}",
            'status': status,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': cleaned_content,
                'url': novel_url
            }]
        }