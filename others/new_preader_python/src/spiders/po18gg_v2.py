"""
po18gg.com解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import os
import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Po18ggParser(BaseParser):
    """po18gg.com解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "po18gg.com"
    description = "po18gg.com整本小说爬取解析器"
    base_url = "https://www.po18gg.com"
    
    # 编码配置 - po18gg.com网站使用GBK编码
    encoding = "gbk"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*>(?!.*logo)(.*?)</h1>',  # 排除包含logo的h1标签
        r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h1>',
        r'<h1[^>]*class="[^"]*book[^"]*"[^>]*>(.*?)</h1>',
        r'<h1[^>]*id="[^"]*title[^"]*"[^>]*>(.*?)</h1>',
        r'<h1[^>]*id="[^"]*book[^"]*"[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*id="content"[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*id="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="read-content"[^>]*>(.*?)</div>',
        r'<div[^>]*id="chaptercontent"[^>]*>(.*?)</div>',
        r'<div[^>]*class="chaptercontent"[^>]*>(.*?)</div>',
        r'<div[^>]*class="article-content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<p[^>]*class="fullfalg"[^>]*>状态[:：]\s*(.*?)[<\s]',
        r'状态[:：]\s*(.*?)[<\s]'
    ]
    
    intro_reg = [
        r'<p[^>]*class="intro"[^>]*>(.*?)</p>',
        r'简介[:：]\s*(.*?)[<\s]'
    ]
    
    # 内容页内分页相关配置
    content_page_link_reg = [
        r'阅读第一章.*?href="([^"]*\.html)"',
        r'href="([^"]*\.html)"[^>]*>阅读第一章</a>',
        r'<a[^>]*href="([^"]*\.html)"[^>]*>阅读第一章</a>',
        r'<a[^>]*href="([^"]*)"[^>]*>阅读第一章</a>'
    ]
    
    next_page_link_reg = [
        r'<div[^>]*class="chapterpage"[^>]*>.*?<a[^>]*href="([^"]*\.html)"[^>]*>下一章</a>',
        r'<a[^>]*href="([^"]*\.html)"[^>]*>下一章</a>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_ads",  # 广告移除
        "_fix_content_divs"  # 修复内容中的div标签问题
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 从数据库获取的网站名称，用于作者信息
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 设置请求头，适配GBK编码
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Charset': 'GBK,utf-8;q=0.7,*;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        
        # 跟踪当前处理的小说URL
        self.current_novel_url = ""
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配po18gg的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        # 根据提供的格式：https://www.po18gg.com/193/193144/
        # 193是书籍ID的去除后3位数字后剩余的数字
        if len(novel_id) > 3:
            dir_id = novel_id[:-3]
            # 如果剩余的小于1则取0
            if not dir_id or int(dir_id) < 1:
                dir_id = "0"
        else:
            # 如果小说ID长度小于等于3，则目录ID为0
            dir_id = "0"
        
        return f"{self.base_url}/{dir_id}/{novel_id}/"
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型，po18gg.com都是多章节书籍
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "多章节"
    
    def _extract_content_page_url(self, content: str) -> Optional[str]:
        """
        从页面内容中提取小说第一章的URL
        
        Args:
            content: 页面内容
            
        Returns:
            第一章内容页面URL或None
        """
        # 查找"阅读第一章"链接
        patterns = self.content_page_link_reg
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                href = match.group(1)
                print(f"找到链接: {href}")
                
                # 确保href是相对路径时转换为正确的绝对路径
                if not href.startswith('http'):
                    # 如果href是相对路径，构建完整的URL
                    if href.startswith('/'):
                        href = f"{self.base_url}{href}"
                    else:
                        # 对于po18gg.com，相对路径相对于当前页面的目录
                        # 例如：当前页面是 https://www.po18gg.com/193/193144/
                        # 链接是 55556544.html，应该构建为 https://www.po18gg.com/193/193144/55556544.html
                        # 获取当前页面的基础路径
                        if self.current_novel_url:
                            # 确保当前小说URL以/结尾
                            base_url = self.current_novel_url.rstrip('/') + '/'
                            href = urljoin(base_url, href)
                        else:
                            # 如果没有设置当前小说URL，使用基础URL
                            href = f"{self.base_url}/{href}"
                
                print(f"转换后链接: {href}")
                return href
        
        print("未找到匹配的链接")
        return None
    
    def _extract_intro(self, content: str) -> Optional[str]:
        """
        提取小说简介
        
        Args:
            content: 页面内容
            
        Returns:
            小说简介或None
        """
        intro = self._extract_with_regex(content, self.intro_reg)
        if intro:
            # 清理简介内容
            intro = re.sub(r'\s+', ' ', intro).strip()
            return intro
        
        return None
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - po18gg.com特定实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 设置当前小说URL
        self.current_novel_url = novel_url
        
        # 提取简介
        intro = self._extract_intro(content)
        
        # 提取第一章节URL
        first_chapter_url = self._extract_content_page_url(content)
        if not first_chapter_url:
            raise Exception("无法找到第一章内容链接")
        
        print(f"找到第一章链接: {first_chapter_url}")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'intro': intro,
            'chapters': []
        }
        
        # 从第一章开始爬取所有章节
        self._crawl_all_chapters_from_first(first_chapter_url, novel_content)
        
        return novel_content
    
    def _crawl_all_chapters_from_first(self, first_chapter_url: str, novel_content: Dict[str, Any]) -> None:
        """
        从第一章开始爬取所有章节内容
        
        Args:
            first_chapter_url: 第一章URL
            novel_content: 小说内容字典
        """
        current_url = first_chapter_url
        chapter_number = 1
        
        while current_url:
            print(f"正在抓取第 {chapter_number} 章: {current_url}")
            
            # 获取章节页面内容
            chapter_content = self._get_url_content(current_url)
            
            if not chapter_content:
                print(f"× 第 {chapter_number} 章抓取失败")
                break
            
            # 提取章节标题
            chapter_title = self._extract_chapter_title(chapter_content, chapter_number)
            
            # 提取章节内容 - 优先使用平衡括号匹配算法
            extracted_content = self._extract_content_alternative(chapter_content)
            
            if extracted_content:
                print(f"提取到内容，长度: {len(extracted_content)}")
                print(f"内容预览: {extracted_content[:300]}...")
                
                # 执行爬取后处理函数
                processed_content = self._execute_after_crawler_funcs(extracted_content)
                
                # 检查处理后的内容是否有效
                if processed_content and len(processed_content.strip()) > 0:
                    novel_content['chapters'].append({
                        'chapter_number': chapter_number,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': current_url
                    })
                    print(f"√ 第 {chapter_number} 章抓取成功，内容长度: {len(processed_content)}")
                    print(f"处理后内容预览: {processed_content[:200]}...")
                else:
                    print(f"× 第 {chapter_number} 章内容处理后为空")
                    # 尝试正则表达式方法作为备选
                    regex_content = self._extract_with_regex(chapter_content, self.content_reg)
                    if regex_content:
                        processed_content = self._execute_after_crawler_funcs(regex_content)
                        novel_content['chapters'].append({
                            'chapter_number': chapter_number,
                            'title': chapter_title,
                            'content': processed_content,
                            'url': current_url
                        })
                        print(f"√ 第 {chapter_number} 章使用正则表达式方法抓取成功，内容长度: {len(processed_content)}")
                    else:
                        print(f"× 第 {chapter_number} 章所有内容提取方法都失败")
                        break
            else:
                # 添加调试信息，查看为什么内容提取失败
                print(f"× 第 {chapter_number} 章内容提取失败")
                print(f"页面内容预览: {chapter_content[:500]}...")
                
                # 尝试正则表达式方法作为备选
                regex_content = self._extract_with_regex(chapter_content, self.content_reg)
                if regex_content:
                    processed_content = self._execute_after_crawler_funcs(regex_content)
                    novel_content['chapters'].append({
                        'chapter_number': chapter_number,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': current_url
                    })
                    print(f"√ 第 {chapter_number} 章使用正则表达式方法抓取成功，内容长度: {len(processed_content)}")
                else:
                    print(f"× 第 {chapter_number} 章所有内容提取方法都失败")
                    break
            
            # 提取下一页链接
            next_url = self._extract_next_chapter_url(chapter_content, current_url)
            
            # 检查是否到达最后一章（下一页URL等于小说主页URL）
            if next_url and self._is_last_chapter(next_url, novel_content['url']):
                print("已到达最后一章")
                break
            
            current_url = next_url
            chapter_number += 1
            
            # 章节间延迟
            time.sleep(1)
    
    def _extract_chapter_title(self, content: str, chapter_number: int) -> str:
        """
        提取章节标题
        
        Args:
            content: 章节内容
            chapter_number: 章节编号
            
        Returns:
            章节标题
        """
        # 尝试从页面标题中提取章节标题
        title_match = re.search(r'<title>(.*?)</title>', content)
        if title_match:
            title = title_match.group(1).strip()
            # 移除网站名称部分
            title = re.sub(r'[-_]*po18gg\.com.*', '', title).strip()
            if title:
                return title
        
        # 备用：使用章节编号
        return f"第{chapter_number}章"
    
    def _extract_next_chapter_url(self, content: str, current_url: str) -> Optional[str]:
        """
        提取下一章节URL
        
        Args:
            content: 当前章节内容
            current_url: 当前章节URL
            
        Returns:
            下一章节URL或None
        """
        # 查找下一页链接，只取第一个匹配（避免重复）
        patterns = self.next_page_link_reg
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                # 只取第一个匹配的链接
                href = matches[0]
                
                # 构建完整的URL
                if not href.startswith('http'):
                    # 如果href是相对路径，构建完整的URL
                    if href.startswith('/'):
                        href = f"{self.base_url}{href}"
                    else:
                        # 假设相对路径相对于当前页面的目录
                        base_dir = '/'.join(current_url.split('/')[:-1]) + '/'
                        href = urljoin(base_dir, href)
                
                return href
        
        return None
    
    def _is_last_chapter(self, next_url: str, novel_base_url: str) -> bool:
        """
        检查是否是最后一章
        
        Args:
            next_url: 下一章URL
            novel_base_url: 小说主页URL
            
        Returns:
            是否是最后一章
        """
        # 如果下一章URL等于小说主页URL，说明是最后一章
        return next_url == novel_base_url or next_url == novel_base_url.rstrip('/') + '/'
    
    def _fix_content_divs(self, content: str) -> str:
        """
        修复内容中的div标签问题 - po18gg.com特有处理
        避免抓取的内容被嵌套的div标签截断
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 首先移除所有div标签，但保留其内容
        # 使用非贪婪匹配，确保不会截断内容
        content = re.sub(r'<div[^>]*>', '', content)
        content = re.sub(r'</div>', '', content)
        
        # 移除其他可能的嵌套标签
        content = re.sub(r'<span[^>]*>', '', content)
        content = re.sub(r'</span>', '', content)
        
        # 保留p标签但转换为换行
        content = re.sub(r'<p[^>]*>', '\\n', content)
        content = re.sub(r'</p>', '\\n', content)
        
        # 移除br标签，转换为换行
        content = re.sub(r'<br[^>]*>', '\\n', content)
        
        # 清理多余的空格和换行
        content = re.sub(r'\\s+', ' ', content)
        content = re.sub(r'\\n\\s*\\n', '\\n\\n', content)
        content = re.sub(r'^\\s+|\\s+$', '', content)
        
        return content.strip()
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - po18gg.com特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除常见的广告模式
        ad_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<style[^>]*>.*?</style>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容',
            r'请收藏本站',
            r'请记住本站',
            r'po18gg\.com',
            r'www\.po18gg\.com'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题 - po18gg.com特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            小说标题
        """
        # 首先尝试从页面标题中提取（最可靠的方法）
        title_match = re.search(r'<title>(.*?)</title>', content)
        if title_match:
            title_text = title_match.group(1).strip()
            # 移除网站名称部分
            title_text = re.sub(r'[-_]*po18gg\.com.*', '', title_text).strip()
            # 进一步清理HTML标签和特殊字符
            title_text = re.sub(r'<[^>]+>', '', title_text).strip()
            title_text = re.sub(r'[<>]', '', title_text).strip()
            # 检查是否是有效的标题（不是HTML标签或链接）
            if title_text and len(title_text) > 1 and not title_text.startswith('<a') and not re.search(r'href=|src=', title_text):
                return title_text
        
        # 尝试从页面内容中寻找更具体的标题
        # 寻找不包含logo的h1标签
        novel_title_patterns = [
            r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h1>',
            r'<h1[^>]*class="[^"]*book[^"]*"[^>]*>(.*?)</h1>',
            r'<h1[^>]*id="[^"]*title[^"]*"[^>]*>(.*?)</h1>',
            r'<h1[^>]*id="[^"]*book[^"]*"[^>]*>(.*?)</h1>',
            # 排除包含logo的h1标签
            r'<h1[^>]*>(?!.*logo)(.*?)</h1>'
        ]
        
        for pattern in novel_title_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                title_text = match.group(1).strip()
                title_text = re.sub(r'<[^>]+>', '', title_text).strip()
                # 检查是否是有效的标题（不是HTML标签或链接）
                if title_text and len(title_text) > 1 and not title_text.startswith('<a') and not re.search(r'href=|src=', title_text):
                    return title_text
        
        # 最后尝试使用配置的正则表达式提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if title:
            # 清理标题，移除HTML标签和多余空格
            title = re.sub(r'<[^>]+>', '', title).strip()
            # 进一步清理，移除网站名称和特殊字符
            title = re.sub(r'[-_]*po18gg\.com.*', '', title).strip()
            title = re.sub(r'[<>]', '', title).strip()
            # 检查是否是有效的标题
            if title and len(title) > 1 and not title.startswith('<a') and not re.search(r'href=|src=', title):
                return title
        
        return "未知标题"
    
    def _extract_status(self, content: str) -> Optional[str]:
        """
        提取小说状态
        
        Args:
            content: 页面内容
            
        Returns:
            小说状态或None
        """
        status = self._extract_with_regex(content, self.status_reg)
        return status
    
    def _extract_content_alternative(self, content: str) -> Optional[str]:
        """
        备用的内容提取方法
        优先使用平衡括号匹配算法处理嵌套div标签
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容或None
        """
        # 首先尝试平衡括号匹配算法，处理嵌套div标签
        balanced_content = self._extract_balanced_content(content)
        if balanced_content and len(balanced_content) > 100:
            return balanced_content
        
        # 如果平衡算法失败，尝试其他常见的内容区域模式
        alternative_patterns = [
            r'<div[^>]*class="content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*text[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*novel[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*chapter[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<section[^>]*>(.*?)</section>'
        ]
        
        for pattern in alternative_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                extracted = match.group(1)
                # 检查提取的内容是否合理（有一定长度且包含中文）
                if len(extracted) > 100 and re.search(r'[\u4e00-\u9fff]', extracted):
                    return extracted
        
        # 如果常规方法都失败，尝试智能内容提取
        return self._extract_content_smart(content)
    
    def _extract_content_smart(self, content: str) -> Optional[str]:
        """
        智能内容提取方法，处理嵌套div标签
        使用平衡括号匹配算法，参考shiyimng_v2.py的实现
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容或None
        """
        # 使用平衡括号匹配算法提取内容，处理嵌套div标签
        return self._extract_balanced_content(content)
    
    def _extract_balanced_content(self, content: str) -> str:
        """
        使用平衡括号匹配算法提取内容，处理嵌套div标签
        针对po18gg.com的特殊结构进行优化
        
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
            r'<div[^>]*id="content"[^>]*>',
            r'<div[^>]*class="read-content"[^>]*>',
            r'<div[^>]*id="chaptercontent"[^>]*>',
            r'<div[^>]*class="chaptercontent"[^>]*>',
            r'<div[^>]*class="article-content"[^>]*>',
            r'<div[^>]*class="novel-content"[^>]*>',
            r'<article[^>]*>',
            r'<section[^>]*>'
        ]
        
        best_candidate = ""
        best_score = 0
        
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
                            
                            # po18gg.com特殊处理：内容可能包含导航div，需要进一步提取
                            # 查找包含实际小说文本的部分（通常包含&nbsp;和<br>标签）
                            novel_content = self._extract_novel_text_from_container(extracted_content)
                            if novel_content:
                                return novel_content
                            
                            # 改进的内容验证逻辑
                            score = self._score_content_quality(extracted_content)
                            
                            # 如果内容质量很高，直接返回
                            if score >= 0.8:
                                return extracted_content
                            
                            # 否则保存最佳候选内容
                            if score > best_score:
                                best_score = score
                                best_candidate = extracted_content
                            break
        
        # 如果有质量尚可的内容，返回最佳候选
        if best_score >= 0.3:
            return best_candidate
        
        return ""
    
    def _extract_novel_text_from_container(self, container_content: str) -> str:
        """
        从内容容器中提取实际的小说文本
        针对po18gg.com的特殊结构：内容在导航div之后
        
        Args:
            container_content: 容器内容
            
        Returns:
            提取的小说文本
        """
        # 查找导航div的结束位置
        nav_end_patterns = [
            r'<div[^>]*class="chapterpage"[^>]*>.*?</div>',
            r'<div[^>]*class="nav"[^>]*>.*?</div>',
            r'<div[^>]*class="page"[^>]*>.*?</div>'
        ]
        
        nav_end_pos = 0
        for pattern in nav_end_patterns:
            nav_match = re.search(pattern, container_content, re.DOTALL | re.IGNORECASE)
            if nav_match:
                nav_end_pos = nav_match.end()
                break
        
        # 如果找到导航，从导航之后开始提取内容
        if nav_end_pos > 0:
            novel_text = container_content[nav_end_pos:]
            
            # 清理HTML标签，保留文本和必要的换行
            novel_text = re.sub(r'<script[^>]*>.*?</script>', '', novel_text, flags=re.DOTALL)
            novel_text = re.sub(r'<style[^>]*>.*?</style>', '', novel_text, flags=re.DOTALL)
            novel_text = re.sub(r'<!--.*?-->', '', novel_text, flags=re.DOTALL)
            
            # 保留br标签用于换行
            novel_text = re.sub(r'<br[^>]*>', '\n', novel_text)
            
            # 移除其他HTML标签但保留文本内容
            novel_text = re.sub(r'<[^>]+>', '', novel_text)
            
            # 清理空白字符
            novel_text = re.sub(r'&nbsp;', ' ', novel_text)
            novel_text = re.sub(r'\s+', ' ', novel_text)
            novel_text = re.sub(r'\n\s*\n', '\n\n', novel_text)
            novel_text = novel_text.strip()
            
            # 检查是否包含实际的小说内容
            if len(novel_text) > 100 and re.search(r'[一-鿿]', novel_text):
                return novel_text
        
        return ""
    
    def _score_content_quality(self, content: str) -> float:
        """
        评估内容质量，返回0-1之间的分数
        
        Args:
            content: 要评估的内容
            
        Returns:
            质量分数 (0-1)
        """
        if not content or len(content) < 50:
            return 0.0
        
        score = 0.0
        
        # 1. 中文文本比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(content)
        if total_chars > 0:
            chinese_ratio = chinese_chars / total_chars
            score += min(chinese_ratio * 0.4, 0.4)  # 中文比例最高占40%
        
        # 2. 内容长度
        if total_chars > 500:
            score += 0.3  # 长度足够
        elif total_chars > 200:
            score += 0.2  # 长度适中
        elif total_chars > 100:
            score += 0.1  # 长度较短
        
        # 3. 段落结构（检查是否有多个段落）
        paragraphs = re.split(r'<p>|<br>|\n\s*\n', content)
        if len(paragraphs) > 3:
            score += 0.2  # 有良好的段落结构
        elif len(paragraphs) > 1:
            score += 0.1  # 有基本段落结构
        
        # 4. 排除广告和导航内容
        # 检查是否包含明显的广告关键词
        ad_patterns = [
            r'广告', r'赞助', r'收藏', r'记住', r'po18gg\.com', 
            r'上一章', r'下一章', r'目录', r'返回'
        ]
        
        ad_count = 0
        for pattern in ad_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                ad_count += 1
        
        # 广告关键词过多会降低分数
        if ad_count > 3:
            score *= 0.5
        elif ad_count > 1:
            score *= 0.7
        
        return min(score, 1.0)
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        """
        重写获取URL内容方法，支持GBK编码处理
        po18gg.com网站使用GBK编码，需要特殊处理
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容或None
        """
        proxies = None
        if self.proxy_config.get('enabled', False):
            proxy_url = self.proxy_config.get('proxy_url', '')
            if proxy_url:
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
        
        for attempt in range(max_retries):
            try:
                # 首先尝试普通请求
                response = self.session.get(url, proxies=proxies, timeout=10)
                if response.status_code == 200:
                    # po18gg.com网站使用GBK编码，特殊处理
                    response.encoding = self.encoding
                    content = response.text
                    
                    # 检测 Cloudflare Turnstile 等高级反爬虫机制
                    if self._detect_advanced_anti_bot(content):
                        logger.warning(f"检测到高级反爬虫机制，尝试使用 Playwright: {url}")
                        return self._get_url_content_with_playwright(url, proxies)
                    
                    return content
                    
                elif response.status_code == 404:
                    logger.warning(f"页面不存在: {url}")
                    return None
                elif response.status_code in [403, 429, 503]:  # 反爬虫相关状态码
                    logger.warning(f"检测到反爬虫限制 (HTTP {response.status_code})，尝试使用cloudscraper: {url}")
                    # 使用cloudscraper绕过反爬虫
                    return self._get_url_content_with_cloudscraper(url, proxies)
                else:
                    logger.warning(f"HTTP {response.status_code} 获取失败: {url}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"第 {attempt + 1} 次请求失败: {url}, 错误: {e}")
                
                # 根据尝试次数选择不同的绕过策略
                if attempt == 0:  # 第一次失败：尝试 cloudscraper
                    try:
                        content = self._get_url_content_with_cloudscraper(url, proxies)
                        if content:
                            return content
                    except Exception as scraper_error:
                        logger.warning(f"cloudscraper也失败: {scraper_error}")
                elif attempt == 1:  # 第二次失败：尝试 playwright
                    try:
                        content = self._get_url_content_with_playwright(url, proxies)
                        if content:
                            return content
                    except Exception as playwright_error:
                        logger.warning(f"playwright也失败: {playwright_error}")
                else:  # 第三次及以后：再次尝试普通请求
                    logger.warning(f"尝试普通请求: {url}")
                    try:
                        response = self.session.get(url, proxies=proxies, timeout=20)
                        if response.status_code == 200:
                            response.encoding = self.encoding
                            return response.text
                    except Exception as final_error:
                        logger.warning(f"最终请求失败: {final_error}")
                else:  # 第三次及以后：尝试 playwright
                    try:
                        return self._get_url_content_with_playwright(url, proxies)
                    except Exception as playwright_error:
                        logger.warning(f"playwright也失败: {playwright_error}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"所有反爬虫策略都失败: {url}")
        return None
    
    def _get_url_content_with_cloudscraper(self, url: str, proxies: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        使用cloudscraper绕过反爬虫限制获取URL内容
        po18gg.com网站使用GBK编码，需要特殊处理
        
        Args:
            url: 目标URL
            proxies: 代理配置
            
        Returns:
            页面内容或None
        """
        try:
            import cloudscraper
            import urllib3
            
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 创建cloudscraper会话
            try:
                # 先创建一个自定义的requests会话，配置好SSL
                import requests
                import ssl
                from requests.adapters import HTTPAdapter
                
                custom_session = requests.Session()
                
                # 创建不验证的SSL上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # 创建自定义适配器，使用我们的SSL上下文
                class SSLAdapter(HTTPAdapter):
                    def init_poolmanager(self, *args, **kwargs):
                        kwargs['ssl_context'] = ssl_context
                        return super().init_poolmanager(*args, **kwargs)
                
                # 应用自定义适配器
                custom_session.mount('https://', SSLAdapter())
                custom_session.verify = False
                
                # 使用自定义会话创建cloudscraper
                scraper = cloudscraper.create_scraper(
                    browser={
                        'browser': 'chrome',
                        'platform': 'windows',
                        'mobile': False
                    },
                    delay=2,
                    sess=custom_session  # 使用预配置的会话
                )
                
                # 设置SSL验证 - 先禁用check_hostname再设置verify
                try:
                    # 尝试在scraper对象上设置verify属性
                    scraper.verify = False
                    
                    # 如果有session，需要同时禁用check_hostname
                    if hasattr(scraper, 'session'):
                        session = getattr(scraper, 'session')
                        # 先禁用check_hostname
                        try:
                            if hasattr(session, 'check_hostname'):
                                session.check_hostname = False
                        except Exception as hostname_error:
                            logger.debug(f"无法禁用check_hostname: {hostname_error}")
                        
                        # 尝试在底层SSL上下文中设置
                        try:
                            if hasattr(session, 'ssl_context'):
                                import ssl
                                session.ssl_context.check_hostname = False
                                session.ssl_context.verify_mode = ssl.CERT_NONE
                        except Exception as ssl_context_error:
                            logger.debug(f"无法设置SSL上下文: {ssl_context_error}")
                        
                        # 尝试在底层requests会话上设置
                        try:
                            if hasattr(session, 'requests'):
                                requests_obj = getattr(session, 'requests')
                                if hasattr(requests_obj, 'check_hostname'):
                                    requests_obj.check_hostname = False
                                if hasattr(requests_obj, 'verify'):
                                    requests_obj.verify = False
                        except Exception as requests_error:
                            logger.debug(f"无法在底层requests会话上设置SSL验证: {requests_error}")
                            
                except Exception as verify_error:
                    logger.debug(f"无法设置SSL验证: {verify_error}")
                    # 尝试备用方法：使用urllib3 PoolManager
                    try:
                        import urllib3
                        import ssl
                        from urllib3.util import SSLContext as Urllib3SSLContext
                        
                        # 创建自定义SSL上下文
                        ssl_context = Urllib3SSLContext()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        
                        # 尝试在scraper的session上设置
                        if hasattr(scraper, 'session'):
                            session = getattr(scraper, 'session')
                            if hasattr(session, 'mount'):
                                # 创建自定义PoolManager
                                https_pool = urllib3.PoolManager(
                                    ssl_context=ssl_context,
                                    timeout=urllib3.Timeout(connect=10, read=30)
                                )
                                session.mount('https://', https_pool)
                    except Exception as pool_error:
                        logger.debug(f"无法创建自定义PoolManager: {pool_error}")
                
        except Exception as e:
            logger.warning(f"cloudscraper创建失败，使用requests: {e}")
            import requests
            import ssl
            import urllib3
            from requests.adapters import HTTPAdapter
            
            # 禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            scraper = requests.Session()
            
            # 设置SSL验证 - 确保正确禁用验证
            scraper.verify = False
            
            # 也需要禁用check_hostname
            try:
                # 创建一个不验证的SSL上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # 应用到requests会话
                scraper.mount('https://', HTTPAdapter(
                    max_retries=urllib3.Retry(total=3, backoff_factor=0.1),
                    pool_connections=10,
                    pool_maxsize=10
                ))
                
            except Exception as ssl_error:
                logger.debug(f"无法设置SSL上下文: {ssl_error}")
            
            # 设置请求头，适配GBK编码
            scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Charset': 'GBK,utf-8;q=0.7,*;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            })
            
            # 设置代理
            if proxies:
                scraper.proxies = proxies
            
            response = scraper.get(url, timeout=30)
            
            if response.status_code == 200:
                # po18gg.com网站使用GBK编码，特殊处理
                response.encoding = self.encoding
                logger.info(f"cloudscraper成功绕过反爬虫限制: {url}")
                return response.text
            else:
                logger.warning(f"cloudscraper请求失败 (HTTP {response.status_code}): {url}")
                return None
                
        except ImportError:
            logger.warning("cloudscraper库未安装，无法绕过反爬虫限制")
            return None
        except Exception as e:
            logger.warning(f"cloudscraper请求异常: {e}")
            return None

# 使用示例
if __name__ == "__main__":
    parser = Po18ggParser()
    
    # 测试小说
    try:
        novel_id = "193144"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")