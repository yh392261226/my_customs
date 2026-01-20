"""
po18rr.com解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Po18rrParser(BaseParser):
    """po18rr.com解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "po18rr.com"
    description = "po18rr.com整本小说爬取解析器"
    base_url = "https://www.po18rr.com"
    
    # 编码配置 - po18rr.com使用GBK编码
    encoding = "gbk"
    
    # 正则表达式配置
    title_reg = [
        r'<div class="p1">\s*<h1[^>]*>(.*?)</h1>',
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*id="content"[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div class="content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div class="p2">\s*<p[^>]*>(.*?)</p>',
        r'ÀàÐÍ[:：]\s*(.*?)[<\s]'
    ]
    
    # 书籍类型配置
    book_type = ["多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_extract_balanced_content",  # 使用平衡括号匹配算法
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_ads"  # 广告移除
    ]

    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 从数据库获取的网站名称，用于作者信息
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })

    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID，格式为"127032"，去除后3位数字后剩余的数字作为目录ID
            
        Returns:
            小说URL
        """
        # 提取目录ID：去除后3位数字后剩余的数字
        if len(novel_id) > 3:
            dir_id = novel_id[:-3]
            # 如果剩余的小于1则取0
            if not dir_id or int(dir_id) < 1:
                dir_id = "0"
        else:
            # 如果小说ID长度小于等于3，则目录ID为0
            dir_id = "0"
        
        return f"{self.base_url}/{dir_id}/{novel_id}/"

    def _parse_book_intro(self, content: str) -> str:
        """
        解析书籍简介
        
        Args:
            content: 页面内容
            
        Returns:
            书籍简介
        """
        # 查找<p class="p3">标签内的简介内容
        intro_pattern = r'<p[^>]*class="p3"[^>]*>(.*?)</p>'
        intro_match = re.search(intro_pattern, content, re.DOTALL)
        
        if intro_match:
            intro_text = intro_match.group(1)
            # 清理HTML标签
            intro_text = re.sub(r'<[^>]+>', '', intro_text)
            intro_text = re.sub(r'\s+', ' ', intro_text).strip()
            return intro_text
        
        return ""

    def _parse_chapter_list(self, content: str, base_url: str) -> List[Dict[str, str]]:
        """
        解析章节列表
        
        Args:
            content: 页面内容
            base_url: 基础URL用于拼接相对链接
            
        Returns:
            章节列表，每个章节包含标题和URL
        """
        chapters = []
        
        # 直接在整个页面内容中查找章节链接
        # 查找所有包含章节链接的li标签
        li_pattern = r'<li>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        li_matches = re.findall(li_pattern, content, re.DOTALL)
        
        # 过滤掉非章节链接（如导航链接等）
        for href, title in li_matches:
            # 只处理相对链接（章节链接通常是相对路径）
            if not href.startswith('http') and not href.startswith('#') and not href.startswith('javascript'):
                # 清理标题
                title = re.sub(r'<[^>]+>', '', title).strip()
                
                # 拼接完整URL
                full_url = urljoin(base_url, href)
                
                chapters.append({
                    'title': title,
                    'url': full_url
                })
        
        return chapters

    def _extract_balanced_content(self, content: str) -> str:
        """
        使用平衡括号匹配算法提取内容，处理嵌套div标签
        针对po18rr.com的特殊结构进行优化
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容
        """
        # 查找可能的内容容器标签
        container_patterns = [
            r'<div[^>]*id="content"[^>]*class="content"[^>]*>',
            r'<div[^>]*class="content"[^>]*id="content"[^>]*>',
            r'<div[^>]*class="content"[^>]*>',
            r'<div[^>]*id="content"[^>]*>'
        ]
        
        for pattern in container_patterns:
            start_match = re.search(pattern, content, re.IGNORECASE)
            if start_match:
                start_pos = start_match.end()
                container_tag_match = re.search(r'<(\w+)', pattern)
                if container_tag_match:
                    container_tag = container_tag_match.group(1)
                    
                    # 使用平衡匹配算法找到对应的结束标签
                    stack = 1
                    pos = start_pos
                    
                    while stack > 0 and pos < len(content):
                        # 查找下一个开始或结束标签
                        tag_match = re.search(r'</?\w+[^>]*>', content[pos:])
                        if not tag_match:
                            break
                        
                        tag = tag_match.group(0)
                        tag_pos = pos + tag_match.start()
                        
                        # 检查是否是相同类型的标签
                        if re.match(r'<\s*/?\s*' + container_tag + r'\b', tag, re.IGNORECASE):
                            if tag.startswith('</'):
                                stack -= 1
                            else:
                                stack += 1
                        
                        pos = tag_pos + len(tag)
                        
                        if stack == 0:
                            # 找到匹配的结束标签
                            extracted_content = content[start_pos:tag_pos]
                            
                            # 清理HTML标签和实体编码
                            extracted_content = self._clean_html_content(extracted_content)
                            
                            return extracted_content
        
        return ""

    def _clean_html_content(self, content: str) -> str:
        """
        清理HTML内容，去除HTML标签和实体编码
        
        Args:
            content: HTML内容
            
        Returns:
            清理后的纯文本内容
        """
        # 移除脚本和样式标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        # 移除注释
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # 保留br标签用于换行
        content = re.sub(r'<br[^>]*>', '\n', content)
        
        # 移除其他HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 处理HTML实体编码
        import html
        content = html.unescape(content)
        
        # 清理空白字符
        content = re.sub(r'&nbsp;', ' ', content)
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content

    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容
        
        Args:
            content: 文本内容
            
        Returns:
            移除广告后的内容
        """
        # 移除常见的广告词
        ad_patterns = [
            r'请收藏本站.*?最新最快无防盗免费阅读',
            r'天才一秒.*?记住本站地址',
            r'新.*?最快.*?手机版',
            r'无广告.*?免费阅读',
            r'首发.*?请勿转载'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content)
        
        return content.strip()

    def crawl_novel(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """
        爬取整本小说
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说信息字典或None
        """
        novel_url = self.get_novel_url(novel_id)
        logger.info(f"开始爬取小说: {novel_url}")
        
        # 获取书籍页面内容
        content = self._get_url_content(novel_url)
        if not content:
            logger.error(f"无法获取书籍页面: {novel_url}")
            return None
        
        # 解析书籍信息
        novel_info = self._parse_novel_info(content, novel_url)
        if not novel_info:
            logger.error(f"无法解析书籍信息: {novel_url}")
            return None
        
        # 解析章节列表
        chapters = self._parse_chapter_list(content, novel_url)
        if not chapters:
            logger.error(f"无法解析章节列表: {novel_url}")
            return None
        
        novel_info['chapters'] = chapters
        novel_info['chapter_count'] = len(chapters)
        
        logger.info(f"成功解析书籍信息: {novel_info['title']}, 章节数: {len(chapters)}")
        
        return novel_info

    def crawl_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        爬取章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容或None
        """
        logger.info(f"开始爬取章节内容: {chapter_url}")
        
        # 获取章节页面内容
        content = self._get_url_content(chapter_url)
        if not content:
            logger.error(f"无法获取章节页面: {chapter_url}")
            return None
        
        # 使用配置的处理函数链提取内容
        processed_content = self._execute_after_crawler_funcs(content)
        
        if processed_content and len(processed_content.strip()) > 0:
            logger.info(f"成功提取章节内容，长度: {len(processed_content)}")
            return processed_content
        else:
            logger.error(f"章节内容提取失败: {chapter_url}")
            return None

    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - po18rr.com特定实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取简介
        intro = self._parse_book_intro(content)
        
        # 解析章节列表
        chapters = self._parse_chapter_list(content, novel_url)
        if not chapters:
            raise Exception("无法解析章节列表")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': f'来自 {self.novel_site_name}',
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'intro': intro,
            'chapters': []
        }
        
        # 爬取所有章节内容
        self._crawl_all_chapters(chapters, novel_content)
        
        return novel_content
    
    def _crawl_all_chapters(self, chapters: List[Dict[str, str]], novel_content: Dict[str, Any]) -> None:
        """
        爬取所有章节内容
        
        Args:
            chapters: 章节列表
            novel_content: 小说内容字典
        """
        for i, chapter in enumerate(chapters, 1):
            chapter_number = i + 1
            chapter_url = chapter['url']
            chapter_title = chapter['title']
            
            logger.info(f"正在抓取第 {chapter_number} 章: {chapter_title}")
            
            # 获取章节页面内容
            chapter_content = self._get_url_content(chapter_url)
            
            if not chapter_content:
                logger.warning(f"第 {chapter_number} 章抓取失败: {chapter_url}")
                continue
            
            # 使用配置的处理函数链提取内容
            processed_content = self._execute_after_crawler_funcs(chapter_content)
            
            if processed_content and len(processed_content.strip()) > 0:
                novel_content['chapters'].append({
                    'chapter_number': chapter_number,
                    'title': chapter_title,
                    'content': processed_content,
                    'url': chapter_url
                })
                logger.info(f"第 {chapter_number} 章抓取成功，内容长度: {len(processed_content)}")
            else:
                logger.warning(f"第 {chapter_number} 章内容提取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def _parse_novel_info(self, content: str, novel_url: str) -> Optional[Dict[str, Any]]:
        """
        解析小说基本信息
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            
        Returns:
            小说信息字典或None
        """
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            logger.error("无法提取小说标题")
            return None
        
        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        # 提取简介
        intro = self._parse_book_intro(content)
        
        # 构造小说信息
        novel_info = {
            'title': title,
            'url': novel_url,
            'status': status or '未知',
            'intro': intro,
            'author': f'来自 {self.novel_site_name}',
            'source': self.name,
            'chapters': []
        }
        
        return novel_info

    def _execute_after_crawler_funcs(self, content: str) -> str:
        """
        执行爬取后处理函数链
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        processed_content = content
        
        for func_name in self.after_crawler_func:
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                processed_content = func(processed_content)
            else:
                logger.warning(f"处理函数不存在: {func_name}")
        
        return processed_content