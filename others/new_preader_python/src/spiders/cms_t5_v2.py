"""
CMS T5 WordPress小说网站解析器 - 通用WordPress主题解析版本
适用于使用相同WordPress主题结构的网站，特征为entry-title、entry-content结构
支持短篇小说和内容页分页类型
"""

import re
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CmsT5Parser(BaseParser):
    """CMS T5 WordPress主题小说解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None, site_url: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
            site_url: 网站URL，用于自动生成base_url
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 如果提供了site_url，则自动解析并设置base_url
        if site_url:
            self._setup_from_site_url(site_url)
        
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
        
        # 如果base_url已设置，更新Referer头
        if self.base_url:
            self.session.headers.update({'Referer': self.base_url})
    
    def _setup_from_site_url(self, site_url: str) -> None:
        """
        从网站URL自动设置base_url
        
        Args:
            site_url: 网站URL，如 https://www.example.com/
        """
        logger.info(f"开始从site_url设置base_url: {site_url}")
        
        # 解析URL获取域名
        parsed_url = urlparse(site_url)
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        logger.info(f"设置base_url: {self.base_url}")
        
        # 如果没有提供novel_site_name，使用域名作为名称
        if not self.novel_site_name or self.novel_site_name == self.name:
            self.novel_site_name = parsed_url.netloc
            logger.info(f"设置novel_site_name: {self.novel_site_name}")
    
    @classmethod
    def create_from_site_data(cls, site_data: Dict[str, Any], proxy_config: Optional[Dict[str, Any]] = None):
        """
        从数据库中的网站数据创建解析器实例
        
        Args:
            site_data: 数据库中的网站数据
            proxy_config: 代理配置
            
        Returns:
            解析器实例
        """
        return cls(
            proxy_config=proxy_config,
            novel_site_name=site_data.get('name'),
            site_url=site_data.get('url')
        )
    
    @classmethod
    def create_all_parsers_from_db(cls, db_path: Optional[str] = None):
        """
        从数据库中获取所有CMS T5网站并创建解析器实例
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            
        Returns:
            List[Dict[str, Any]]: 包含网站信息和对应解析器的列表
        """
        from src.core.database_manager import DatabaseManager
        
        # 创建数据库管理器
        db_manager = DatabaseManager(db_path) if db_path else DatabaseManager()
        
        # 获取所有CMS T5网站并创建解析器
        return db_manager.create_cms_t5_parsers()
    
    # 基本信息 - 会被动态设置
    name = "CMS T5 WordPress主题通用解析器"
    description = "CMS T5 WordPress主题通用解析器，适用于entry-title、entry-content结构的网站"
    base_url = ""  # 将在初始化时设置
    
    # 编码配置 - 使用UTF-8编码
    encoding = "utf-8"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="entry-title"[^>]*>(.*?)</h1>',
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*class="entry-content"[^>]*>(.*)</div>'
    ]
    
    status_reg = [
        r'<span[^>]*class="posted-on"[^>]*>(.*?)</span>',
        r'<time[^>]*class="entry-date"[^>]*>(.*?)</time>'
    ]
    
    # 书籍类型配置 - 支持短篇和内容页分页
    book_type = ["短篇", "内容页内分页"]
    
    # 内容页内分页相关配置
    content_page_link_reg = [
        r'<p[^>]*class="pages"[^>]*>(.*?)</p>'
    ]
    
    next_page_link_reg = [
        r'<a[^>]*class="post-page-numbers"[^>]*href="([^"]*)"[^>]*>[^<]*</a>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_extract_balanced_content",  # 使用平衡算法提取内容
        "_remove_ads",  # 广告移除
        "_convert_traditional_to_simplified" # 繁体转简体
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID，格式为"2025/12/14/一個出軌女人的自述"
            
        Returns:
            小说URL
        """
        if not self.base_url:
            logger.error("base_url未设置，无法生成有效的URL")
            raise ValueError("base_url未设置，请在初始化时提供有效的site_url")
            
        return f"{self.base_url}/{novel_id}/"
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        适配应用程序的标准接口
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        # 调用现有的crawl_novel方法
        novel_info = self.crawl_novel(novel_id)
        
        if not novel_info:
            raise Exception(f"无法解析小说详情: {novel_id}")
        
        # 将novel_info转换为标准的parse_novel_detail格式
        novel_content = {
            'title': novel_info.get('title', ''),
            'author': novel_info.get('author', ''),
            'novel_id': novel_info.get('novel_id', ''),
            'url': novel_info.get('url', ''),
            'intro': novel_info.get('intro', ''),
            'status': novel_info.get('status', '未知')
        }
        
        # 添加内容字段
        if 'total_content' in novel_info:
            novel_content['total_content'] = novel_info['total_content']
            novel_content['content'] = novel_info['total_content']
        
        # 如果有多页内容，添加pages字段
        if 'pages' in novel_info:
            novel_content['pages'] = novel_info['pages']
            # 确保章节有正确的名称，如果没有则使用顺序值
            chapters = []
            for i, page in enumerate(novel_info['pages']):
                chapter_data = page.copy()
                # 如果章节没有标题，使用顺序值
                if 'title' not in chapter_data or not chapter_data['title']:
                    chapter_data['title'] = f"第{i+1}页"
                chapters.append(chapter_data)
            novel_content['chapters'] = chapters
        
        return novel_content
    
    def crawl_novel(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """
        爬取小说信息
        
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
        
        # 检查是否有多页内容
        page_links = self._parse_content_page_links(content, novel_url)
        if page_links:
            novel_info['page_links'] = page_links
            novel_info['page_count'] = len(page_links) + 1  # 包括当前页面
            logger.info(f"检测到分页内容，共 {novel_info['page_count']} 页")
            
            # 对于分页小说，使用多页爬取
            multipage_novel = self.crawl_multipage_novel(novel_id)
            if multipage_novel:
                novel_info.update(multipage_novel)
            else:
                # 如果多页爬取失败，回退到单页爬取
                logger.warning("多页爬取失败，回退到单页爬取")
                novel_content = self.crawl_chapter_content(novel_url)
                if novel_content:
                    novel_info['total_content'] = novel_content
                    novel_info['content'] = novel_content
        else:
            # 对于短篇小说，提取并保存内容
            novel_content = self.crawl_chapter_content(novel_url)
            if novel_content:
                novel_info['total_content'] = novel_content
                novel_info['content'] = novel_content
        
        logger.info(f"成功解析书籍信息: {novel_info['title']}")
        
        return novel_info
    
    def crawl_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        爬取章节内容（对于内容页分页类型，爬取当前页面的内容）
        
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
        
        # 使用处理函数链提取内容
        processed_content = self._execute_after_crawler_funcs(content)
        
        if processed_content and len(processed_content.strip()) > 0:
            logger.info(f"成功提取章节内容，长度: {len(processed_content)}")
            return processed_content
        else:
            logger.error(f"章节内容提取失败: {chapter_url}")
            return None
    
    def crawl_multipage_novel(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """
        爬取多页小说内容（适用于内容页分页类型）
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说内容字典或None
        """
        novel_url = self.get_novel_url(novel_id)
        logger.info(f"开始爬取多页小说: {novel_url}")
        
        # 获取主页面内容
        main_content = self._get_url_content(novel_url)
        if not main_content:
            logger.error(f"无法获取主页面: {novel_url}")
            return None
        
        # 解析基本信息
        title = self._extract_with_regex(main_content, self.title_reg)
        if not title:
            logger.error("无法提取小说标题")
            return None
        
        # 提取标签作为简介
        intro = self._parse_book_intro(main_content)
        
        # 解析分页链接
        page_links = self._parse_content_page_links(main_content, novel_url)
        
        # 创建小说内容字典
        novel_content = {
            'title': title,
            'author': f'来自 {self.novel_site_name}',
            'novel_id': novel_id,
            'url': novel_url,
            'intro': intro,
            'pages': [],
            'total_content': ''
        }
        
        # 爬取所有页面内容
        all_pages = [novel_url] + page_links
        total_content = []
        
        for i, page_url in enumerate(all_pages):
            logger.info(f"正在爬取第 {i+1}/{len(all_pages)} 页: {page_url}")
            
            page_content = self._get_url_content(page_url)
            if not page_content:
                logger.warning(f"无法获取页面内容: {page_url}")
                continue
            
            # 提取页面内容
            processed_content = self._execute_after_crawler_funcs(page_content)
            
            if processed_content and len(processed_content.strip()) > 0:
                novel_content['pages'].append({
                    'page_number': i + 1,
                    'url': page_url,
                    'content': processed_content,
                    'title': f"第{i+1}页"  # 添加章节名称
                })
                total_content.append(processed_content)
                logger.info(f"第 {i+1} 页爬取成功，内容长度: {len(processed_content)}")
            else:
                logger.warning(f"第 {i+1} 页内容提取失败")
            
            # 页面间延迟
            time.sleep(1)
        
        # 合并所有页面内容
        novel_content['total_content'] = '\n\n'.join(total_content)
        novel_content['total_length'] = len(novel_content['total_content'])
        
        logger.info(f"多页小说爬取完成，总内容长度: {novel_content['total_length']}")
        
        return novel_content
    
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
            'novel_id': self._extract_novel_id_from_url(novel_url)
        }
        
        return novel_info
    
    def _parse_book_intro(self, content: str) -> str:
        """
        解析书籍简介（使用标签作为简介）
        
        Args:
            content: 页面内容
            
        Returns:
            书籍简介（使用标签信息）
        """
        # 提取标签信息作为简介
        tags = self._extract_tags(content)
        if tags:
            return f"标签: {', '.join(tags)}"
        
        # 如果无法提取标签，返回默认简介
        return f"{self.novel_site_name}优质小说"
    
    def _extract_tags(self, content: str) -> List[str]:
        """
        提取书籍标签
        
        Args:
            content: 页面内容
            
        Returns:
            标签列表
        """
        tags = []
        
        # 查找<span class="tags">标签内的所有<a>标签
        tags_pattern = r'<span[^>]*class="tags"[^>]*>(.*?)</span>'
        tags_match = re.search(tags_pattern, content, re.DOTALL)
        
        if tags_match:
            tags_content = tags_match.group(1)
            # 提取所有<a>标签内的文字
            tag_pattern = r'<a[^>]*>(.*?)</a>'
            tag_matches = re.findall(tag_pattern, tags_content)
            
            for tag in tag_matches:
                # 清理HTML标签和空白字符
                clean_tag = re.sub(r'<[^>]+>', '', tag).strip()
                if clean_tag:
                    tags.append(clean_tag)
        
        return tags
    
    def _parse_content_page_links(self, content: str, base_url: str) -> List[str]:
        """
        解析内容页分页链接
        修正版本：正确匹配WordPress主题的分页格式
        
        Args:
            content: 页面内容
            base_url: 基础URL
            
        Returns:
            分页链接列表
        """
        page_links = []
        
        # 查找分页区域 - WordPress主题使用class="pages"的p标签
        pagination_pattern = r'<p[^>]*class="pages"[^>]*>(.*?)</p>'
        pagination_match = re.search(pagination_pattern, content, re.DOTALL)
        
        if pagination_match:
            pagination_content = pagination_match.group(1)
            
            # 提取所有带有post-page-numbers类的链接（排除当前页）
            link_pattern = r'<a[^>]*class="post-page-numbers"[^>]*href="([^"]*)"[^>]*>[^<]*</a>'
            link_matches = re.findall(link_pattern, pagination_content, re.DOTALL)
            
            # 提取所有分页链接
            for href in link_matches:
                if not href.startswith('#'):
                    # 拼接完整URL
                    full_url = urljoin(base_url, href)
                    
                    # 避免重复添加当前页面
                    if full_url not in page_links and full_url != base_url:
                        page_links.append(full_url)
        
        # 如果没有找到分页区域，尝试查找所有包含数字的链接
        if not page_links:
            # 查找所有包含数字的分页链接
            page_links_pattern = r'<a[^>]*href="([^"]*)"[^>]*>\s*(\d+)\s*</a>'
            all_link_matches = re.findall(page_links_pattern, content, re.DOTALL)
            
            for href, number in all_link_matches:
                if not href.startswith('#') and number != '1':  # 排除第1页（当前页）
                    full_url = urljoin(base_url, href)
                    if full_url not in page_links and full_url != base_url:
                        page_links.append(full_url)
        
        # 按页码排序分页链接（根据URL中的数字）
        def get_page_number(url):
            # 从URL中提取页码
            match = re.search(r'/(\d+)/?$', url)
            return int(match.group(1)) if match else 0
        
        if page_links:
            page_links.sort(key=get_page_number)
        
        return page_links
    
    def _extract_balanced_content(self, content: str) -> str:
        """
        使用平衡括号匹配算法提取内容，专门针对<div class="entry-content">
        改进版本：更好地处理嵌套div，避免内容截断
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容
        """
        # 查找<div class="entry-content">标签
        start_pattern = r'<div[^>]*class="entry-content"[^>]*>'
        start_match = re.search(start_pattern, content, re.IGNORECASE)
        
        if start_match:
            start_pos = start_match.end()
            
            # 使用平衡匹配算法找到对应的结束标签
            stack = 1
            pos = start_pos
            
            while stack > 0 and pos < len(content):
                # 查找下一个开始或结束标签
                tag_match = re.search(r'</?div[^>]*>', content[pos:])
                if not tag_match:
                    break
                
                tag = tag_match.group(0)
                tag_pos = pos + tag_match.start()
                
                # 检查是否是开始或结束标签
                if tag.startswith('</div'):
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
        
        # 如果平衡算法失败，尝试使用正则表达式（带DOTALL标志）
        for pattern in self.content_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                extracted_content = match.group(1)
                extracted_content = self._clean_html_content(extracted_content)
                return extracted_content
        
        return ""
    
    def _clean_html_content(self, content: str) -> str:
        """
        清理HTML内容，去除HTML标签和实体编码
        改进版本：更好地清理WordPress主题特有的广告和导航内容
        
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
        
        # 移除广告和导航内容（WordPress主题特有）
        content = re.sub(r'<div[^>]*class="zFXsv8Os"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
        content = re.sub(r'<div[^>]*class="post-navigation"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
        content = re.sub(r'<div[^>]*class="widget-area"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
        content = re.sub(r'<div[^>]*class="entry-meta"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
        content = re.sub(r'<span[^>]*class="posted-on"[^>]*>.*?</span>', '', content, flags=re.DOTALL)
        content = re.sub(r'<span[^>]*class="tags-links"[^>]*>.*?</span>', '', content, flags=re.DOTALL)
        content = re.sub(r'<span[^>]*class="cat-links"[^>]*>.*?</span>', '', content, flags=re.DOTALL)
        
        # 保留br标签用于换行
        content = re.sub(r'<br[^>]*>', '\n', content)
        
        # 保留p标签用于段落分隔
        content = re.sub(r'</p>', '\n\n', content)
        
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
            r'首发.*?请勿转载',
            r'本文首发.*?转载',
            r'本站所有小说.*?转载',
            r'版权声明.*?保留所有权利'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content)
        
        return content.strip()
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - WordPress主题特定实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取简介
        intro = self._parse_book_intro(content)
        
        # 检查是否有多页内容
        page_links = self._parse_content_page_links(content, novel_url)
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': f'来自 {self.novel_site_name}',
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'intro': intro,
            'pages': []
        }
        
        # 爬取所有页面内容
        all_pages = [novel_url] + page_links
        
        for i, page_url in enumerate(all_pages):
            logger.info(f"正在爬取第 {i+1} 页: {page_url}")
            
            page_content = self._get_url_content(page_url)
            if not page_content:
                logger.warning(f"第 {i+1} 页抓取失败: {page_url}")
                continue
            
            # 使用处理函数链提取内容
            processed_content = self._execute_after_crawler_funcs(page_content)
            
            if processed_content and len(processed_content.strip()) > 0:
                novel_content['pages'].append({
                    'page_number': i + 1,
                    'url': page_url,
                    'content': processed_content
                })
                logger.info(f"第 {i+1} 页抓取成功，内容长度: {len(processed_content)}")
            else:
                logger.warning(f"第 {i+1} 页内容提取失败")
            
            # 页面间延迟
            time.sleep(1)
        
        return novel_content
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型（WordPress主题网站主要为短篇小说）
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 对于WordPress主题，使用URL路径作为ID
        # 例如: https://aaanovel.com/2025/12/14/一個出軌女人的自述/
        parsed_url = urlparse(url)
        # 移除开头的/和结尾的/
        path = parsed_url.path.strip('/')
        return path if path else "unknown"


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用site_url自动配置
    parser = CmsT5Parser(site_url="https://aaanovel.com/")
    
    # 测试单篇小说
    try:
        novel_id = "2025/12/14/一個出軌女人的自述"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
    
    # 示例2: 从数据库创建所有CMS T5解析器
    print("\n=== 从数据库创建所有CMS T5解析器 ===")
    try:
        parser_sites = CmsT5Parser.create_all_parsers_from_db()
        print(f"已创建 {len(parser_sites)} 个CMS T5解析器")
        
        for site_info in parser_sites:
            site_data = site_info['site_data']
            print(f"- 网站: {site_data.get('name')} ({site_data.get('url')})")
            print(f"  存储文件夹: {site_data.get('storage_folder')}")
            print(f"  代理启用: {site_data.get('proxy_enabled', False)}")
    except Exception as e:
        print(f"从数据库创建解析器失败: {e}")
    
    # 示例3: 使用BaseParser工厂方法创建CMS T5解析器
    print("\n=== 使用BaseParser工厂方法创建CMS T5解析器 ===")
    try:
        from src.core.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        cms_sites = db_manager.get_cms_t5_sites()
        
        if cms_sites:
            site_data = cms_sites[0]  # 使用第一个网站作为示例
            parser = BaseParser.create_cms_t5_parser(site_data)
            print(f"使用工厂方法创建了解析器: {parser.novel_site_name}")
        else:
            print("数据库中没有CMS T5网站")
    except Exception as e:
        print(f"使用工厂方法创建解析器失败: {e}")
    def parse_novel_detail_incremental(self, novel_id: str, start_url: str, title: str = None, author: str = None, start_index: int = 0) -> Dict[str, Any]:
        """
        增量爬取：从指定章节URL开始继续爬取
        
        Args:
            novel_id: 小说ID
            start_url: 起始章节URL（最后一章的URL）
            title: 小说标题（可选）
            author: 作者（可选）
            start_index: 起始章节索引
            
        Returns:
            小说详情信息
        """
        # 获取小说页面，提取章节列表
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取章节列表（子类需要实现提取方法）
        # 这里尝试提取章节，如果没有则返回空列表
        chapters = []
        
        # 尝试使用正则表达式提取章节
        import re
        chapter_patterns = [
            r'<a[^>]*href=["']([^"']*)["'][^>]*>([^<]+)</a>',
            r'<li[^>]*><a[^>]*href=["']([^"']*)["'][^>]*>([^<]+)</a></li>',
        ]
        
        for pattern in chapter_patterns:
            matches = re.findall(pattern, content)
            if matches:
                chapters = [
                    {'url': match[0], 'title': match[1]}
                    for match in matches
                ]
                break
        
        if not chapters:
            # 无法获取章节列表，返回空结果
            logger.warning("无法获取章节列表，无法进行增量爬取")
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        # 通过比对URL找到起始位置
        start_pos = 0
        for i, chapter in enumerate(chapters):
            chapter_full_url = chapter.get('url', '')
            if chapter_full_url == start_url:
                start_pos = i + 1  # 从下一章开始
                break
        
        if start_pos >= len(chapters):
            # 没有新章节
            return {
                'title': title or f'书籍-{novel_id}',
                'chapters': []
            }
        
        logger.info(f"从第 {start_pos + 1} 章开始爬取，共 {len(chapters) - start_pos} 个新章节")
        
        # 创建小说内容
        novel_content = {
            'title': title or f'书籍-{novel_id}',
            'author': author or self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 从起始位置开始爬取
        for i in range(start_pos, len(chapters)):
            chapter = chapters[i]
            chapter_url = chapter.get('url', '')
            chapter_title = chapter.get('title', f'第{i+1}章')
            
            if not chapter_url:
                continue
            
            # 构建完整URL
            if not chapter_url.startswith('http'):
                chapter_url = f"{self.base_url}{chapter_url}"
            
            logger.info(f"正在爬取第 {i+1} 章: {chapter_title}")
            
            # 获取章节内容
            chapter_content = self._get_url_content(chapter_url)
            
            if chapter_content:
                # 提取章节内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    if processed_content and len(processed_content.strip()) > 0:
                        novel_content['chapters'].append({
                            'chapter_number': start_index + (i - start_pos) + 1,
                            'title': chapter_title,
                            'content': processed_content,
                            'url': chapter_url
                        })
                        logger.info(f"✓ 第 {i+1} 章抓取成功")
                    else:
                        logger.warning(f"✗ 第 {i+1} 章内容处理后为空")
                else:
                    logger.warning(f"✗ 第 {i+1} 章内容提取失败")
            else:
                logger.warning(f"✗ 第 {i+1} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
        
        return novel_content
