"""
diyizhan.xyz解析器 - 基于配置驱动版本
支持多章节小说和内容页分页类型
"""

import re
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DiyizhanParser(BaseParser):
    """diyizhan.xyz解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "diyizhan.xyz"
    description = "diyizhan.xyz小说爬取解析器（支持多章节和分页类型）"
    base_url = "https://www.diyizhan.xyz"
    
    # 编码配置 - diyizhan.xyz使用gbk编码
    encoding = "gbk"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="booktitle"[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*class="readcontent"[^>]*>(.*?)(?=</?div[^>]*>|$)',
        r'<div[^>]*class="readcontent"[^>]*>(.*?)(?=<div|$)',
        r'<div[^>]*class="readcontent"[^>]*>(.*?)(?=</div>|$)',
        r'<div[^>]*class="readcontent"[^>]*>(.*)'
    ]
    
    status_reg = [
        r'<p[^>]*class="bookintro"[^>]*>(.*?)</p>'
    ]
    
    # 书籍类型配置 - 支持多章节和内容页分页
    book_type = ["多章节", "内容页内分页"]
    
    # 内容页内分页相关配置
    content_page_link_reg = [
        r'<p[^>]*class="text-center"[^>]*>(.*?)</p>'
    ]
    
    next_page_link_reg = [
        r'<a[^>]*id="linkNext"[^>]*href="([^"]*)"[^>]*>下一页</a>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_extract_balanced_content",  # 使用平衡算法提取内容
        "_remove_ads",  # 广告移除
        "_convert_traditional_to_simplified"  # 繁体转简体
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
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/zhan/{novel_id}/"

    def _extract_chapter_list(self, content: str) -> List[Dict[str, str]]:
        """
        提取章节列表
        
        Args:
            content: 页面内容
            
        Returns:
            章节列表，每个元素包含 {'title': 章节标题, 'url': 章节URL}
        """
        chapter_list = []
        seen_urls = set()  # 用于去重
        
        # 首先尝试从全部章节目录区域提取（优先使用更完整的列表）
        chapter_all_pattern = r'<div[^>]*id="list-chapterAll"[^>]*>(.*?)</div>'
        chapter_all_match = re.search(chapter_all_pattern, content, re.DOTALL)
        if chapter_all_match:
            chapter_all_content = chapter_all_match.group(1)
            # 匹配双引号和单引号的href和title
            patterns = [
                r'<dd><a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>([^<]*)</a></dd>',
                r"<dd><a[^>]*href='([^']*)'[^>]*title='([^']*)'[^>]*>([^<]*)</a></dd>",
                r'<dd><a[^>]*href="([^"]*)"[^>]*title=\'([^\']*)\'[^>]*>([^<]*)</a></dd>',
                r"<dd><a[^>]*href='([^']*)'[^>]*title=\"([^\"]*)\"[^>]*>([^<]*)</a></dd>"
            ]
            
            matches = []
            for pattern in patterns:
                found_matches = re.findall(pattern, chapter_all_content, re.DOTALL)
                if found_matches:
                    matches.extend(found_matches)
        else:
            # 如果没有找到全部章节区域，尝试从页面其他区域提取
            patterns = [
                r'<dd><a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>([^<]*)</a></dd>',
                r"<dd><a[^>]*href='([^']*)'[^>]*title='([^']*)'[^>]*>([^<]*)</a></dd>",
                r'<dd><a[^>]*href="([^"]*)"[^>]*title=\'([^\']*)\'[^>]*>([^<]*)</a></dd>',
                r"<dd><a[^>]*href='([^']*)'[^>]*title=\"([^\"]*)\"[^>]*>([^<]*)</a></dd>"
            ]
            
            matches = []
            for pattern in patterns:
                found_matches = re.findall(pattern, content, re.DOTALL)
                if found_matches:
                    matches.extend(found_matches)
        
        novel_id = self._extract_novel_id_from_url(content)
        
        for match in matches:
            url, title, title_text = match
            # 优先使用title属性，如果没有则使用标签内文本
            chapter_title = title.strip() if title.strip() else title_text.strip()
            
            if chapter_title and url:
                # 如果URL是相对路径，转换为绝对路径
                if url.startswith('/'):
                    url = urljoin(self.base_url, url)
                elif not url.startswith('http'):
                    # 相对路径处理，如 "323589.html"
                    url = urljoin(self.base_url, f"/zhan/{novel_id}/{url}")
                
                # 去重：只添加未出现过的URL
                if url not in seen_urls:
                    seen_urls.add(url)
                    chapter_list.append({
                        'title': chapter_title,
                        'url': url
                    })
        
        # 按章节顺序排序（通常序号在URL中的数字越大越新）
        chapter_list.sort(key=lambda x: int(re.search(r'(\d+)\.html', x['url']).group(1)) if re.search(r'(\d+)\.html', x['url']) else 0)
        
        return chapter_list

    def _extract_novel_id_from_url(self, content_or_url: str) -> str:
        """
        从内容或URL中提取小说ID
        
        Args:
            content_or_url: 页面内容或URL
            
        Returns:
            小说ID
        """
        # 如果是URL，直接提取
        if content_or_url.startswith('http'):
            match = re.search(r'/zhan/(\d+)/', content_or_url)
            if match:
                return match.group(1)
        
        # 如果是内容，从页面中提取
        pattern = r'<link[^>]*href="https://www\.diyizhan\.xyz/zhan/(\d+)/"[^>]*/>'
        match = re.search(pattern, content_or_url)
        if match:
            return match.group(1)
        
        # 尝试其他模式
        pattern = r'/zhan/(\d+)/'
        match = re.search(pattern, content_or_url)
        if match:
            return match.group(1)
        
        return ""

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
        
        # 提取状态（从bookintro标签中提取简介内容）
        status_match = re.search(r'<p[^>]*class="bookintro"[^>]*>(.*?)</p>', content, re.DOTALL)
        status = ""
        if status_match:
            # 去除HTML标签
            status = re.sub(r'<[^>]+>', '', status_match.group(1)).strip()
        
        # 构造小说信息
        novel_info = {
            'title': title,
            'url': novel_url,
            'status': status or '未知',
            'intro': status or '暂无简介',
            'author': f'来自 {self.novel_site_name}',
            'novel_id': self._extract_novel_id_from_url(novel_url)
        }
        
        return novel_info



    def _extract_balanced_content(self, content: str) -> str:
        """
        平衡算法提取内容，确保HTML标签配对
        
        Args:
            content: 原始内容
            
        Returns:
            提取后的内容
        """
        # 移除script和style标签及其内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        # 移除常见的广告标签
        ad_patterns = [
            r'<center>.*?点击下载.*?</center>',
            r'<div[^>]*class="kongwen"[^>]*>.*?</div>',
            r'<div[^>]*class="readmiddle"[^>]*>.*?</div>',
            r'本章未完，点击下一页继续阅读',
            r'<p[^>]*class="text-danger[^>]*>.*?</p>',
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # 处理HTML实体
        content = re.sub(r'&nbsp;', ' ', content)
        content = re.sub(r'&lt;', '<', content)
        content = re.sub(r'&gt;', '>', content)
        content = re.sub(r'&amp;', '&', content)
        content = re.sub(r'&quot;', '"', content)
        content = re.sub(r'&#39;', "'", content)
        
        # 去除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除"其他推荐阅读："及其后面的所有内容
        content = re.sub(r'其他推荐阅读：.*$', '', content, flags=re.DOTALL)
        
        # 处理多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # 移除页码相关内容
        content = re.sub(r'\d+/\d+\s*\d+下一页尾页', '', content)
        
        return content

    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容
        
        Args:
            content: 原始内容
            
        Returns:
            移除广告后的内容
        """
        # 广告关键词列表
        ad_keywords = [
            '点击下载',
            '邀请码',
            '积分规则',
            '留言反馈',
            '投票推荐',
            '加入书架',
            '加入书签'
        ]
        
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 如果行中包含广告关键词，则跳过
            if not any(keyword in line for keyword in ad_keywords):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)

    def _get_chapter_content_first_page(self, chapter_url: str) -> Optional[str]:
        """
        获取章节内容（处理分页）
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容或None
        """
        all_content = []
        current_url = chapter_url
        chapter_title = ""
        
        while current_url:
            # 获取当前页内容
            content = self._get_url_content(current_url)
            if not content:
                break
            
            # 提取章节标题（只从第一页提取）
            if not chapter_title:
                title_match = re.search(r'<h1[^>]*class="pt10"[^>]*>(.*?)</h1>', content, re.DOTALL)
                if title_match:
                    # 去除HTML标签
                    chapter_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            
            # 查找readcontent区域
            readcontent_match = re.search(r'<div[^>]*class="readcontent"[^>]*>', content)
            if not readcontent_match:
                break
            
            start_pos = readcontent_match.end()
            
            # 查找结束位置 - 以"其他推荐阅读："或下一部分导航作为结束标志
            end_patterns = [
                r'其他推荐阅读：',
                r'<div[^>]*class="book mt10 pt10 tuijian"[^>]*>',
                r'<p[^>]*class="text-center"[^>]*>'
            ]
            
            end_pos = len(content)  # 默认到页面末尾
            for pattern in end_patterns:
                match = re.search(pattern, content[start_pos:])
                if match:
                    end_pos = start_pos + match.start()
                    break
            
            # 提取内容区域
            content_area = content[start_pos:end_pos]
            
            # 提取所有文本内容
            all_text = re.findall(r'(?<=>)[^<]+(?=<)', content_area)
            cleaned_text = []
            
            for text in all_text:
                # 过滤掉空白、广告和无关内容
                text = text.strip()
                if text and len(text) > 5 and not self._is_ad_content(text):
                    cleaned_text.append(text)
            
            # 合并当前页内容
            page_content = '\n'.join(cleaned_text)
            if page_content:
                all_content.append(page_content)
            
            # 检查下一页链接
            next_match = re.search(r'<a[^>]*id="linkNext"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', content)
            if not next_match:
                break
                
            next_url = next_match.group(1)
            next_text = next_match.group(2)
            
            # 如果是"下一章"，则停止处理
            if "下一章" in next_text:
                break
                
            # 构建下一页的完整URL
            if next_url.startswith('/'):
                next_url = urljoin(self.base_url, next_url)
            elif not next_url.startswith('http'):
                # 获取当前章节的基础URL
                base_url = current_url.rsplit('/', 1)[0]
                next_url = f"{base_url}/{next_url}"
            
            current_url = next_url
            # 添加延迟避免请求过快
            time.sleep(1)
        
        # 合并所有内容
        raw_content = '\n'.join(all_content)
        
        # 处理内容
        processed_content = self._process_content(raw_content)
        
        return processed_content

    def _get_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        获取章节内容，支持分页处理
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容或None
        """
        content = self._get_url_content(chapter_url)
        if not content:
            return None
        
        # 查找readcontent区域
        readcontent_match = re.search(r'<div[^>]*class="readcontent"[^>]*>', content)
        if not readcontent_match:
            return None
        
        start_pos = readcontent_match.end()
        
        # 查找结束位置 - 以"其他推荐阅读："或下一部分导航作为结束标志
        end_patterns = [
            r'其他推荐阅读：',
            r'<div[^>]*class="book mt10 pt10 tuijian"[^>]*>',
            r'<p[^>]*class="text-center"[^>]*>'
        ]
        
        end_pos = len(content)  # 默认到页面末尾
        for pattern in end_patterns:
            match = re.search(pattern, content[start_pos:])
            if match:
                end_pos = start_pos + match.start()
                break
        
        # 提取内容区域
        content_area = content[start_pos:end_pos]
        
        # 提取所有文本内容
        all_text = re.findall(r'(?<=>)[^<]+(?=<)', content_area)
        cleaned_text = []
        
        for text in all_text:
            # 过滤掉空白、广告和无关内容
            text = text.strip()
            if text and len(text) > 5 and not self._is_ad_content(text):
                cleaned_text.append(text)
        
        # 合并所有文本
        raw_content = '\n'.join(cleaned_text)
        
        # 处理当前页内容
        processed_content = self._process_content(raw_content)
        
        # 检查是否有下一页
        next_page_match = re.search(r'<a[^>]*id="linkNext"[^>]*href="([^"]*)"[^>]*>', content)
        if next_page_match:
            next_page_url = next_page_match.group(1)
            # 如果是相对路径，转换为绝对路径
            if next_page_url.startswith('/'):
                next_page_url = urljoin(self.base_url, next_page_url)
            elif not next_page_url.startswith('http'):
                # 获取当前章节的基础URL
                base_url = chapter_url.rsplit('/', 1)[0]
                next_page_url = f"{base_url}/{next_page_url}"
            
            # 递归获取下一页内容
            next_page_content = self._get_chapter_content(next_page_url)
            if next_page_content:
                processed_content += "\n\n" + next_page_content
        
        return processed_content
    
    def _is_ad_content(self, text: str) -> bool:
        """
        判断是否为广告或无关内容
        
        Args:
            text: 文本内容
            
        Returns:
            是否为广告内容
        """
        ad_keywords = [
            '点击下载',
            '邀请码',
            '积分规则',
            '留言反馈',
            '投票推荐',
            '加入书架',
            '加入书签',
            '首页',
            '书库',
            '排行',
            '全本',
            '搜索',
            '淫妻性宴_第',
            '返回书目',
            '上一章',
            '下一页',
            '章节目录',
            '温馨提示',
            '更新时间',
            '最新章节',
            '查看全部章节',
            '其他推荐阅读',
            '更多推荐阅读'
        ]
        
        return any(keyword in text for keyword in ad_keywords)

    def _process_content(self, content: str) -> str:
        """
        处理内容，调用配置的处理函数
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        result = content
        
        # 调用配置的处理函数
        for func_name in self.after_crawler_func:
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                try:
                    result = func(result)
                except Exception as e:
                    logger.warning(f"处理函数 {func_name} 执行失败: {e}")
        
        return result

    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说内容字典
        """
        # 提取小说基本信息
        novel_info = self._parse_novel_info(content, novel_url)
        if not novel_info:
            raise Exception("无法解析小说基本信息")
        
        # 提取小说ID
        novel_id = self._extract_novel_id_from_url(novel_url)
        if not novel_id:
            raise Exception("无法提取小说ID")
        
        # 提取章节列表
        chapter_list = self._extract_chapter_list(content)
        if not chapter_list:
            raise Exception("无法提取章节列表")
        
        print(f"发现 {len(chapter_list)} 个章节，开始爬取...")
        
        chapters = []
        for i, chapter in enumerate(chapter_list, 1):
            chapter_title = chapter['title']
            chapter_url = chapter['url']
            
            print(f"正在爬取第 {i}/{len(chapter_list)} 章: {chapter_title}")
            
            # 获取章节内容（只获取第一页，不进行分页处理）
            chapter_content = self._get_chapter_content_first_page(chapter_url)
            if chapter_content:
                chapters.append({
                    'chapter_number': i,
                    'title': chapter_title,
                    'content': chapter_content,
                    'url': chapter_url
                })
            else:
                print(f"警告: 无法获取章节内容: {chapter_title}")
                # 仍然添加空章节以保持章节顺序
                chapters.append({
                    'chapter_number': i,
                    'title': chapter_title,
                    'content': "无法获取内容",
                    'url': chapter_url
                })
            
            # 添加延迟避免请求过快
            time.sleep(1)
        
        return {
            'title': novel_info['title'],
            'author': novel_info['author'],
            'novel_id': novel_info['novel_id'],
            'url': novel_info['url'],
            'status': novel_info['status'],
            'intro': novel_info['intro'],
            'chapters': chapters
        }

    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检查是否存在章节列表（优先检查多章节）
        if re.search(r'<div[^>]*id="list-chapterAll"[^>]*>', content):
            return "多章节"
        
        # 检查是否存在内容页分页（仅在没有章节列表时检查）
        if re.search(r'<a[^>]*id="linkNext"[^>]*>', content):
            return "内容页内分页"
        
        # 默认为单章节
        return "短篇"