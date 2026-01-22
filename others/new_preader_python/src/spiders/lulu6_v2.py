"""
撸撸色书 (www.lulu6.xyz) 解析器
网站: https://www.lulu6.xyz/
特点: 短篇小说网站，使用URL格式: /{category}/{novel_id}.html
基于base_parser_v2进行实现
"""

from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse, unquote
from src.utils.logger import get_logger
from .base_parser_v2 import BaseParser
import re

logger = get_logger(__name__)

class Lulu6Parser(BaseParser):
    """撸撸色书解析器 - 基于base_parser_v2实现"""
    
    # 基本配置
    name: str = "撸撸色书解析器"
    description: str = "撸撸色书网站解析器，支持多种分类的短篇小说"
    base_url: str = "https://www.lulu6.xyz"
    
    # 正则表达式配置
    title_reg: List[str] = [
        r'<h3[^>]*>([^<]+)</h3>',  # 标题在h3标签中
        r'<title[^>]*>([^<]+)</title>',  # 备用：页面标题
    ]
    
    content_reg: List[str] = [
        r'<article[^>]*class="post_excerpt[^"]*"[^>]*>(.*?)</article>',  # 主要内容区域
        r'<div[^>]*class="content[^"]*"[^>]*>(.*?)</div>',  # 备用内容区域
    ]
    
    # 支持的书籍类型
    book_type: List[str] = ["短篇"]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None, site_url: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
            site_url: 网站URL，用于自动设置base_url
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 如果提供了site_url，则自动解析并设置base_url
        if site_url:
            try:
                parsed_url = urlparse(site_url)
                self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                logger.info(f"从site_url设置base_url: {self.base_url}")
            except Exception as e:
                logger.error(f"解析site_url失败: {e}")
                self.base_url = "https://www.lulu6.xyz"
        
        # 设置网站名称
        if novel_site_name:
            self.novel_site_name = novel_site_name
        
        logger.info(f"初始化撸撸色书解析器完成: base_url={self.base_url}, name={self.novel_site_name}")
    
    def get_novel_url(self, novel_id: str, category: str = "luanqing") -> str:
        """
        重写URL生成方法，适配撸撸色书的URL格式
        
        Args:
            novel_id: 小说ID
            category: 分类，默认为luanqing
            
        Returns:
            小说URL
        """
        # 撸撸色书的URL格式：/{category}/{novel_id}.html
        # 其中category可以是luanqing、dushi、xiaoshuo等各种分类
        return f"{self.base_url}/{category}/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，撸撸色书主要是短篇小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _clean_content_specific(self, content: str) -> str:
        """
        撸撸色书特定的内容清理
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        try:
            # 先移除脚本标签，避免干扰其他清理
            script_pattern = r'<script[^>]*>.*?</script>'
            content = re.sub(script_pattern, '', content, flags=re.DOTALL)
            
            # 移除当前位置 : <a href="/">首页</a> &gt; <a href="/luanqing/">父女文学</a> 部分
            nav_pattern = r'当前位置\s*:\s*<a[^>]*>首页</a>\s*&gt;\s*<a[^>]*>[^<]*</a>'
            content = re.sub(nav_pattern, '', content)
            
            # 移除h3标题标签（因为标题已经单独提取）
            h3_pattern = r'<h3[^>]*>.*?</h3>'
            content = re.sub(h3_pattern, '', content)
            
            # 移除h5发布时间标签
            h5_pattern = r'<h5[^>]*>.*?</h5>'
            content = re.sub(h5_pattern, '', content)
            
            # 移除<p></p>标签但保留内容
            p_patterns = [
                r'<p[^>]*>(.*?)</p>',  # 标准p标签
                r'<P[^>]*>(.*?)</P>',  # 大写P标签
                r'<p[^>]*/>',          # 自闭合p标签
                r'<P[^>]*/>',          # 大写自闭合p标签
            ]
            
            for p_pattern in p_patterns:
                def p_replacer(match):
                    return match.group(1) if match.group(1) else ''  # 只保留内容部分
                content = re.sub(p_pattern, p_replacer, content, flags=re.DOTALL)
            
            # 将<BR>替换为换行
            content = content.replace('<br>', '\n')
            content = content.replace('<BR>', '\n')
            content = content.replace('<Br>', '\n')
            
            # 移除其他常见的行内标签但保留内容
            inline_patterns = [
                r'<span[^>]*>(.*?)</span>',
                r'<SPAN[^>]*>(.*?)</SPAN>',
                r'<strong[^>]*>(.*?)</strong>',
                r'<b[^>]*>(.*?)</b>',
                r'<B[^>]*>(.*?)</B>',
                r'<i[^>]*>(.*?)</i>',
                r'<I[^>]*>(.*?)</I>',
                r'<em[^>]*>(.*?)</em>',
                r'<EM[^>]*>(.*?)</EM>',
            ]
            
            for pattern in inline_patterns:
                content = re.sub(pattern, r'\1', content, flags=re.DOTALL)
            
            # 最后清理所有剩余的HTML标签（不匹配的标签）
            content = re.sub(r'<[^>]+>', '', content)
            
            # 清理多余的空白行
            content = re.sub(r'\n\s*\n', '\n\n', content)
            content = content.strip()
            
            return content
            
        except Exception as e:
            logger.error(f"内容清理失败: {e}")
            return content
    
    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容
        
        Args:
            content: 页面内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        for pattern in regex_list:
            try:
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
                    # 清理HTML实体和多余空格
                    result = re.sub(r'&nbsp;?', ' ', result)
                    result = re.sub(r'\s+', ' ', result)
                    return result
            except Exception as e:
                logger.error(f"正则匹配失败: {pattern}, 错误: {e}")
                continue
        
        return ""
    
    def parse_novel_detail(self, novel_id: str, category: str = "luanqing") -> Dict[str, Any]:
        """
        重写小说详情解析方法，支持category参数
        
        Args:
            novel_id: 小说ID
            category: 分类
            
        Returns:
            小说详情信息
        """
        # 重置章节计数器
        self.chapter_count = 0
        
        novel_url = self.get_novel_url(novel_id, category)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ] - 分类: {category}")
        
        # 提取内容
        content_text = self._extract_with_regex(content, self.content_reg)
        if not content_text:
            raise Exception("无法提取小说内容")
        
        # 应用撸撸色书特定的内容清理
        content_text = self._clean_content_specific(content_text)
        
        # 构建返回结果
        result = {
            'title': title,
            'author': self.novel_site_name,  # 使用网站名称作为作者
            'book_type': '短篇',
            'status': '已完结',
            'category': category,
            'content': content_text,
            'url': novel_url,
            'novel_id': novel_id,
            'chapter_count': 1,  # 短篇小说通常只有一章
            'chapters': [
                {
                    'title': title,
                    'content': content_text,
                    'url': novel_url,
                    'chapter_id': '1'
                }
            ]
        }
        
        return result
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表
        
        Args:
            url: 列表页面URL
            
        Returns:
            小说信息列表
        """
        novels = []
        
        try:
            content = self._get_url_content(url)
            if not content:
                return novels
            
            # 查找小说链接
            # 撸撸色书的小说链接格式：/{category}/{novel_id}.html
            link_pattern = r'<a[^>]*href="(/([^/]+)/([^/?]+)\.html)"[^>]*>([^<]+)</a>'
            matches = re.findall(link_pattern, content)
            
            for match in matches:
                link_url, category, novel_id, title = match
                full_url = urljoin(self.base_url, link_url)
                
                # 确保novel_id是数字
                if novel_id.isdigit():
                    novels.append({
                        'title': title.strip(),
                        'url': full_url,
                        'novel_id': novel_id,
                        'category': category,
                        'book_type': '短篇'
                    })
            
            return novels
            
        except Exception as e:
            logger.error(f"解析小说列表失败: {url}, 错误: {e}")
            return novels

if __name__ == "__main__":
    # 测试代码
    parser = Lulu6Parser(site_url="https://www.lulu6.xyz/")
    print(f"网站名称: {parser.name}")
    print(f"基础URL: {parser.base_url}")
    print(f"测试URL生成: {parser.get_novel_url('19752', 'luanqing')}")
    print(f"测试URL生成: {parser.get_novel_url('12345', 'dushi')}")
    print(f"书籍类型: {parser._detect_book_type('test')}")
