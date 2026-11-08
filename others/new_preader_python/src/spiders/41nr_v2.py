"""
狠男人小说解析器 (m.41nr.com)
继承自 BaseParser，使用属性配置实现

网站结构特点：
- 书籍详情页：https://m.41nr.com/book/{书籍ID}/ 例如 https://m.41nr.com/book/30396/
- 书籍标题在 <h2></h2> 标签中的 <a ...></a> 包裹的文本
- 书籍简介在 <div class="book-summary"></div> 标签中（需去除其中 html 标签及标签包裹的内容）
- 第一个章节链接在 <ul class="chapter"></ul> 中第一个 <li></li> 的 <a href="..."> 的 href 属性
- 内容页章节标题在 <div class="nr_title" id="nr_title"></div> 标签中的文本
- 内容页章节内容在 <div id="nr" class="nr_nr"></div> 标签中的文本（需去除其中的 html 标签）
- 内容页下一章链接在 <td class="next"><a href="...">下一页</a> 中的 href 属性，
  如果该值与书籍网址相同则为最后一章，否则继续抓取下一章
"""

import re
import html
import time
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Nr41Parser(BaseParser):
    """狠男人小说 (m.41nr.com) 解析器 - 配置驱动版本"""

    # 基本信息
    name = "狠男人小说"
    description = "狠男人小说 (m.41nr.com) 解析器"
    base_url = "https://m.41nr.com"

    # 编码配置 - m.41nr.com 使用 UTF-8 编码
    encoding = "utf-8"

    # 正则表达式配置 - 书籍标题（<h2></h2> 中 <a></a> 包裹的文本）
    title_reg = [
        r'<h2[^>]*>\s*<a[^>]*>([^<]+)</a>',
        r'<h2[^>]*>([^<]+)</h2>'
    ]

    # 正则表达式配置 - 书籍简介（<div class="book-summary">）
    intro_reg = [
        r'<div[^>]*class="book-summary"[^>]*>([\s\S]*?)</div>'
    ]

    # 正则表达式配置 - 章节内容页（<div id="nr" class="nr_nr">）
    content_reg = [
        r'<div[^>]*id="nr"[^>]*class="nr_nr[^"]*"[^>]*>([\s\S]*?)</div>',
        r'<div[^>]*class="nr_nr[^"]*"[^>]*id="nr"[^>]*>([\s\S]*?)</div>',
        r'<div[^>]*id="nr"[^>]*>([\s\S]*?)</div>'
    ]

    # 正则表达式配置 - 状态信息（书籍详情页，可选项）
    status_reg = [
        r'状态[:：]\s*([^<\s]+)',
        r'(连载中|已完结|完本)'
    ]

    # 正则表达式配置 - 内容页章节标题（<div class="nr_title" id="nr_title">）
    chapter_title_reg = [
        r'<div[^>]*class="nr_title[^"]*"[^>]*id="nr_title"[^>]*>([\s\S]*?)</div>',
        r'<div[^>]*id="nr_title"[^>]*class="nr_title[^"]*"[^>]*>([\s\S]*?)</div>',
        r'<div[^>]*id="nr_title"[^>]*>([\s\S]*?)</div>'
    ]

    # 正则表达式配置 - 下一章链接（<td class="next"><a href="...">下一页</a>，兼容单双引号）
    next_page_link_reg = [
        r'<td[^>]*class="next"[^>]*>\s*<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>',
        r'<td[^>]*class="next"[^>]*>[\s\S]*?<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>'
    ]

    # 处理函数配置
    after_crawler_func = [
        "_clean_chapter_text"  # 本解析器提供的正文清理（去除html标签，保留段落）
    ]

    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器

        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)

        # 移动端站点，使用移动端 User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': f'{self.base_url}/'
        })

    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配 m.41nr.com 的URL格式

        Args:
            novel_id: 书籍ID；也兼容传入完整书籍链接
                     （如 https://m.41nr.com/book/30396、https://m.41nr.com/txt/30396.html），
                     会自动提取其中的数字ID

        Returns:
            书籍URL
        """
        # 兼容传入完整链接的情况：从中提取书籍ID
        if not str(novel_id).isdigit():
            extracted = self._extract_novel_id_from_url(str(novel_id))
            if extracted != "unknown":
                novel_id = extracted

        return f"{self.base_url}/book/{novel_id}/"

    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，m.41nr.com 都是多章节书籍

        Args:
            content: 页面内容

        Returns:
            书籍类型
        """
        return "多章节"

    def _extract_intro(self, content: str) -> Optional[str]:
        """
        提取书籍简介，去除其中的 html 标签及标签中包裹的内容

        Args:
            content: 页面内容

        Returns:
            书籍简介或None
        """
        intro_html = self._extract_with_regex(content, self.intro_reg)
        if not intro_html:
            return None

        intro = self._strip_html_tags_with_content(intro_html)
        return intro or None

    def _extract_first_chapter_url(self, content: str, novel_url: str) -> Optional[str]:
        """
        从书籍详情页提取第一个章节的URL
        取 <ul class="chapter"> 中第一个 <li> 内的 <a href="..."> 的 href 属性

        Args:
            content: 书籍详情页内容
            novel_url: 书籍URL（用于解析相对路径）

        Returns:
            第一章内容页URL或None
        """
        patterns = [
            r'<ul[^>]*class="chapter"[^>]*>[\s\S]*?<li[^>]*>\s*<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>',
            r'<ul[^>]*class="chapter"[^>]*>[\s\S]*?<a[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>'
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                href = match.group(1).strip()
                if href:
                    return self._build_absolute_url(href, novel_url)

        return None

    def _extract_chapter_title(self, content: str, chapter_number: int) -> str:
        """
        从内容页提取章节标题（<div class="nr_title" id="nr_title">）

        Args:
            content: 内容页HTML
            chapter_number: 章节编号（提取失败时的备用标题）

        Returns:
            章节标题
        """
        raw_title = self._extract_with_regex(content, self.chapter_title_reg)
        if raw_title:
            # 去除标题中可能存在的标签
            title = self._strip_html_tags_with_content(raw_title)
            if title:
                return self._normalize_chapter_title(title)

        return f"第{chapter_number}章"

    def _normalize_chapter_title(self, title: str) -> str:
        """
        规范化章节标题，去除同章节分页的分页序号后缀
        如 "第1部分（2/2）" -> "第1部分"

        Args:
            title: 原始章节标题

        Returns:
            规范化后的章节标题
        """
        return re.sub(r'[（(]\s*\d+\s*/\s*\d+\s*[)）]\s*$', '', title).strip()

    def _extract_next_page_url(self, content: str, current_url: str) -> Optional[str]:
        """
        提取内容页中的下一章链接（<td class="next"><a href="...">下一页</a>）

        Args:
            content: 当前内容页HTML
            current_url: 当前页面URL（用于解析相对路径）

        Returns:
            下一章URL或None
        """
        if not content:
            return None

        for pattern in self.next_page_link_reg:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                href = match.group(1).strip()
                if href:
                    return self._build_absolute_url(href, current_url)

        return None

    def _build_absolute_url(self, href: str, current_url: str) -> str:
        """
        将相对路径构建为完整的URL

        Args:
            href: 页面中的链接地址
            current_url: 当前页面URL

        Returns:
            完整URL
        """
        from urllib.parse import urljoin

        if href.startswith('http'):
            return href

        if href.startswith('/'):
            return f"{self.base_url}{href}"

        # 相对路径相对于当前页面目录
        return urljoin(current_url, href)

    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        重写从URL中提取书籍ID的方法
        支持以下URL格式（/book/ 后的末尾斜杠可有可无）：
        - https://m.41nr.com/book/30396/
        - https://m.41nr.com/book/30396
        - https://m.41nr.com/txt/30396.html
        - https://m.41nr.com/chapter/30396/6503609.html （章节URL中同样包含书籍ID）

        Args:
            url: 书籍URL或章节URL

        Returns:
            书籍ID
        """
        patterns = [
            r'/book/(\d+)',
            r'/txt/(\d+)\.html',
            r'/chapter/(\d+)/'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return "unknown"

    def _is_last_page(self, next_url: str, novel_url: str, current_url: str) -> bool:
        """
        判断是否为最后一章
        下一章链接与书籍网址相同（或与当前页相同）时为最后一章

        Args:
            next_url: 下一章URL
            novel_url: 书籍URL
            current_url: 当前页URL

        Returns:
            是否为最后一章
        """
        next_normalized = self._normalize_url(next_url)
        return (next_normalized == self._normalize_url(novel_url) or
                next_normalized == self._normalize_url(current_url))

    def _normalize_url(self, url: str) -> str:
        """
        规范化URL用于比较（去除末尾斜杠、查询参数和锚点）

        Args:
            url: 原始URL

        Returns:
            规范化后的URL
        """
        from urllib.parse import urlsplit

        if not url:
            return ""
        parts = urlsplit(url)
        path = parts.path.rstrip('/')
        return f"{parts.netloc.lower()}{path}"

    def _strip_html_tags_with_content(self, html_content: str) -> str:
        """
        去除 html 标签及标签中包裹的内容
        适用于简介等场景（如 <strong>内容简介：</strong>、<a>[详情]</a> 整体移除）

        Args:
            html_content: 原始HTML内容

        Returns:
            纯文本（仅保留未包裹在标签中的文本）
        """
        clean_text = re.sub(r'<(script|style)[^>]*>[\s\S]*?</\1>', '', html_content, flags=re.IGNORECASE)
        # 由内向外逐层移除带内容的标签，避免外层标签把未处理的内层内容一并带走
        while True:
            stripped = re.sub(r'<([a-zA-Z][^\s>/]*)[^>]*>([^<]*)</\1>', '', clean_text, flags=re.IGNORECASE)
            if stripped == clean_text:
                break
            clean_text = stripped
        # 移除剩余的孤立标签
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        clean_text = html.unescape(clean_text)
        clean_text = clean_text.replace('\xa0', ' ')
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()

    def _clean_chapter_text(self, content: str) -> str:
        """
        清理章节正文：去除 html 标签，保留段落结构

        Args:
            content: 内容页正文原始HTML

        Returns:
            清理后的纯文本正文
        """
        text = re.sub(r'<(script|style)[^>]*>[\s\S]*?</\1>', '', content, flags=re.IGNORECASE)
        # 将 <br> 和段落标签（开/闭）转换为换行，保留段落结构
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</?(p|div|li)[^>]*>', '\n', text, flags=re.IGNORECASE)
        # 移除剩余的 html 标签（含标签包裹的内容，如 <a>...</a>）
        text = re.sub(r'<a[^>]*>[\s\S]*?</a>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        text = text.replace('\xa0', ' ')
        # 移除站内分页提示文字（如"本章未完，请点击下方 下一页 继续阅读"、"本章已完，请点击下方 下一章 翻阅新篇"）
        text = re.sub(r'本章[未已]?(?:完)?.{0,40}?(?:继续阅读|翻阅新篇)', '', text)
        # 清理多余空白行
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n', text)
        return text.strip()

    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - m.41nr.com 特定实现

        Args:
            content: 书籍详情页内容
            novel_url: 书籍URL
            title: 书籍标题

        Returns:
            小说详情信息
        """
        # 提取简介
        intro = self._extract_intro(content)

        # 提取第一章URL
        first_chapter_url = self._extract_first_chapter_url(content, novel_url)
        if not first_chapter_url:
            raise Exception("无法提取第一个章节链接")

        logger.info(f"找到第一章链接: {first_chapter_url}")

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
        self._crawl_all_chapters(first_chapter_url, novel_content)

        return novel_content

    def _crawl_all_chapters(self, first_chapter_url: str, novel_content: Dict[str, Any],
                            start_index: int = 0) -> None:
        """
        从第一章开始沿着"下一章"链接爬取所有章节内容
        同一章节分页（章节标题相同）的内容会合并到同一章节

        Args:
            first_chapter_url: 第一章URL
            novel_content: 小说内容字典
            start_index: 起始章节索引（用于增量爬取时的章节编号偏移）
        """
        current_url = first_chapter_url
        novel_url = novel_content.get('url', '')
        seen_urls = set()
        chapter_number = start_index

        while current_url:
            # 防止循环引用导致死循环
            normalized = self._normalize_url(current_url)
            if normalized in seen_urls:
                logger.warning(f"检测到重复链接，停止抓取: {current_url}")
                break
            seen_urls.add(normalized)

            page_number = chapter_number + 1
            logger.info(f"正在爬取第 {page_number} 章: {current_url}")

            page_content = self._get_url_content(current_url)
            if not page_content:
                logger.warning(f"✗ 第 {page_number} 页抓取失败")
                break

            # 提取章节标题
            chapter_title = self._extract_chapter_title(page_content, page_number)

            # 提取章节内容
            chapter_content = self._extract_with_regex(page_content, self.content_reg)
            if chapter_content:
                processed_content = self._execute_after_crawler_funcs(chapter_content)

                if processed_content:
                    # 同一章节标题的分页内容合并到上一章（标题已归一化，分页后缀已去除）
                    last_chapter = novel_content['chapters'][-1] if novel_content['chapters'] else None
                    if (last_chapter and chapter_title and
                            last_chapter.get('title') == chapter_title and
                            chapter_number == start_index + len(novel_content['chapters'])):
                        last_chapter['content'] = f"{last_chapter['content']}\n{processed_content}".strip()
                        logger.info(f"✓ 第 {chapter_number} 章分页内容合并成功")
                    else:
                        chapter_number += 1
                        novel_content['chapters'].append({
                            'chapter_number': chapter_number,
                            'title': chapter_title,
                            'content': processed_content,
                            'url': current_url
                        })
                        logger.info(f"✓ 第 {chapter_number} 章抓取成功，内容长度: {len(processed_content)}")
                else:
                    logger.warning(f"✗ 第 {page_number} 页内容处理后为空")
            else:
                logger.warning(f"✗ 第 {page_number} 页内容提取失败")

            # 提取下一章链接
            next_url = self._extract_next_page_url(page_content, current_url)

            # 下一章链接与书籍网址相同（或当前页相同）时为最后一章
            if next_url and self._is_last_page(next_url, novel_url, current_url):
                logger.info("已到达最后一章")
                break

            current_url = next_url

            # 章节间延迟
            time.sleep(1)

    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写获取书籍首页元数据方法，提取标题、简介与状态

        Args:
            novel_id: 书籍ID

        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)

        if not content:
            return None

        title = self._extract_with_regex(content, self.title_reg)
        intro = self._extract_intro(content)
        status = self._extract_with_regex(content, self.status_reg)

        return {
            "title": title or "未知标题",
            "desc": intro or "多章节小说",
            "status": status or "未知状态"
        }

    def parse_novel_detail_incremental(self, novel_id: str, start_url: str, title: str = None,
                                       author: str = None, start_index: int = 0) -> Dict[str, Any]:
        """
        增量爬取：从指定章节URL开始继续爬取新章节

        Args:
            novel_id: 书籍ID
            start_url: 起始章节URL（最后一章的URL）
            title: 书籍标题（可选）
            author: 作者（可选）
            start_index: 起始章节索引（从0开始）

        Returns:
            小说详情信息（只包含新章节）
        """
        novel_url = self.get_novel_url(novel_id)

        # 如果未提供标题，从书籍详情页提取
        if not title:
            content = self._get_url_content(novel_url)
            if content:
                title = self._extract_with_regex(content, self.title_reg)
            title = title or f"书籍-{novel_id}"

        logger.info(f"增量爬取 [ {title} ] 从 {start_url} 开始")

        novel_content = {
            'title': title,
            'author': author or self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }

        self._crawl_all_chapters(start_url, novel_content, start_index=start_index)

        return novel_content

    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - m.41nr.com 不需要列表页解析

        Args:
            url: 小说列表页URL

        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = Nr41Parser()

    # 测试多章节书籍
    try:
        novel_id = "30396"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
