"""
www.dpyqxs.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
支持内容页内分页模式
"""

import re
import html
import requests
import concurrent.futures
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DpyqxsParser(BaseParser):
    """www.dpyqxs.com 小说解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "www.dpyqxs.com"
    description = "www.dpyqxs.com 小说解析器"
    base_url = "https://www.dpyqxs.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1 class="title single">\s*<a[^>]*title="[^"]*">(.*?)</a>\s*</h1>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<article class="page-content-single small single">(.*?)</article>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    status_reg = [
        r'状态[：:]\s*(.*?)[<\n\r]',
        r'status[：:]\s*(.*?)[<\n\r]'
    ]
    
    # 支持的书籍类型
    book_type = ["内容页内分页"]
    
    # 内容页内分页相关配置
    content_page_link_reg = [
        r'<div class="single-nav-links">(.*?)</div>'
    ]
    
    next_page_link_reg = [
        r'<a[^>]*href="([^"]*)"[^>]*class="post-page-numbers"[^>]*>[^<]*</a>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_dpyqxs_content",  # 特定内容清理
        "_clean_html_content"     # 公共基类提供的HTML清理
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        # 添加特定的请求头
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配dpyqxs.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/?p={novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，dpyqxs.com主要是内容页内分页模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 检查是否存在分页链接
        if re.search(r'<div[^>]*class="single-nav-links"[^>]*>', content, re.IGNORECASE):
            return "内容页内分页"
        return "内容页内分页"  # 默认返回内容页内分页
    
    def _parse_content_pagination_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析内容页内分页模式的小说
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取书籍ID
        book_id = self._extract_book_id_from_url(novel_url)
        if not book_id:
            raise Exception("无法提取书籍ID")
        
        # 获取所有分页链接
        page_links = self._extract_page_links(content, novel_url)
        if not page_links:
            raise Exception("无法获取分页链接")
        
        print(f"发现 {len(page_links)} 个分页")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': book_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有页面内容
        self._get_all_pages(page_links, novel_content)
        
        return novel_content
    
    def _extract_book_id_from_url(self, url: str) -> Optional[str]:
        """
        从书籍URL中提取书籍ID
        
        Args:
            url: 书籍URL
            
        Returns:
            书籍ID或None
        """
        match = re.search(r'[?&]p=(\d+)', url)
        return match.group(1) if match else None
    
    def _extract_page_links(self, content: str, base_url: str) -> List[str]:
        """
        从页面内容中提取所有分页链接
        
        Args:
            content: 页面内容
            base_url: 基础URL
            
        Returns:
            分页链接列表
        """
        page_links = []
        
        # 首先添加当前页面（第一页）
        page_links.append(base_url)
        
        # 查找分页链接区域
        nav_pattern = r'<div[^>]*class="single-nav-links"[^>]*>(.*?)</div>'
        nav_match = re.search(nav_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if nav_match:
            nav_content = nav_match.group(1)
            
            # 提取所有分页链接
            page_pattern = r'<a[^>]*href="([^"]*)"[^>]*class="post-page-numbers"[^>]*>[^<]*</a>'
            page_matches = re.findall(page_pattern, nav_content, re.IGNORECASE)
            
            for href in page_matches:
                # 解码HTML实体
                decoded_href = html.unescape(href)
                
                # 确保URL格式正确
                if decoded_href.startswith('http'):
                    full_url = decoded_href
                elif decoded_href.startswith('/'):
                    full_url = f"{self.base_url}{decoded_href}"
                else:
                    # 相对路径处理
                    import os
                    base_dir = os.path.dirname(base_url)
                    full_url = f"{base_dir}/{decoded_href}"
                
                # 避免重复添加页面
                if full_url not in page_links:
                    page_links.append(full_url)
        
        # 如果没有找到其他分页，只返回当前页面
        if len(page_links) == 1:
            logger.debug("未找到其他分页，可能为单页小说")
        
        logger.info(f"提取到 {len(page_links)} 个页面链接")
        return page_links
    
    def _fetch_single_page(self, page_info: tuple[int, str]) -> tuple[int, str, str, bool]:
        """
        单页面抓取函数，用于并行处理
        
        Args:
            page_info: (页码, 页面URL)
            
        Returns:
            (页码, 页面内容, 是否成功)
        """
        page_num, page_url = page_info
        
        try:
            page_content = self._get_url_content_optimized(page_url)
            if page_content:
                chapter_content = self._extract_content_optimized(page_content)
                if chapter_content:
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    return (page_num, page_url, processed_content, True)
            return (page_num, page_url, "", False)
        except Exception as e:
            logger.warning(f"抓取第 {page_num} 页失败: {e}")
            return (page_num, page_url, "", False)
    
    def _fetch_single_page_with_retry(self, page_info: tuple[int, str]) -> tuple[int, str, str, bool]:
        """
        带重试的单页面抓取函数，用于重试失败的页面
        
        Args:
            page_info: (页码, 页面URL)
            
        Returns:
            (页码, 页面内容, 是否成功)
        """
        page_num, page_url = page_info
        
        # 重试3次
        for retry_count in range(3):
            try:
                # 重试时使用更长的超时时间
                response = self.session.get(page_url, timeout=(10, 20))
                
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    page_content = response.text
                    
                    if page_content:
                        chapter_content = self._extract_content_optimized(page_content)
                        if chapter_content:
                            processed_content = self._execute_after_crawler_funcs(chapter_content)
                            return (page_num, page_url, processed_content, True)
                
                # 等待一段时间后重试
                import time
                time.sleep(2 * (retry_count + 1))
                
            except Exception as e:
                logger.warning(f"重试第 {page_num} 页失败 (尝试 {retry_count + 1}/3): {e}")
                if retry_count < 2:  # 不是最后一次重试
                    import time
                    time.sleep(2 * (retry_count + 1))
        
        return (page_num, page_url, "", False)
    
    def _get_all_pages_parallel(self, page_links: List[str], novel_content: Dict[str, Any]) -> None:
        """
        并行抓取所有页面内容 - 修复排序和缺失问题版本
        
        Args:
            page_links: 页面链接列表
            novel_content: 小说内容字典
        """
        logger.info(f"开始并行抓取 {len(page_links)} 个页面")
        
        # 准备页面信息
        page_infos = [(i+1, url) for i, url in enumerate(page_links)]
        
        # 使用线程池并行处理
        max_workers = min(8, len(page_links))  # 最大8个线程，避免过多并发
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务并记录页码到future的映射
            future_to_page_num = {}
            for page_info in page_infos:
                page_num, page_url = page_info
                future = executor.submit(self._fetch_single_page, page_info)
                future_to_page_num[future] = page_num
            
            # 等待所有任务完成
            completed_results = {}
            failed_pages = []
            
            for future in concurrent.futures.as_completed(future_to_page_num):
                page_num = future_to_page_num[future]
                
                try:
                    result_page_num, result_url, content, success = future.result()
                    
                    if success and content:
                        completed_results[page_num] = {
                            'chapter_number': page_num,
                            'title': f"第 {page_num} 页",
                            'content': content,
                            'url': result_url
                        }
                    else:
                        failed_pages.append(page_num)
                        logger.warning(f"第 {page_num} 页抓取失败")
                        
                except Exception as e:
                    failed_pages.append(page_num)
                    logger.error(f"处理第 {page_num} 页时出错: {e}")
            
            # 按页码顺序重新排序章节
            sorted_page_nums = sorted(completed_results.keys())
            for page_num in sorted_page_nums:
                novel_content['chapters'].append(completed_results[page_num])
            
            # 处理失败的页面（尝试重新抓取）
            if failed_pages:
                logger.warning(f"有 {len(failed_pages)} 个页面抓取失败，尝试重新抓取: {failed_pages}")
                self._retry_failed_pages(failed_pages, page_links, novel_content)
        
        logger.info(f"并行抓取完成，成功抓取 {len(novel_content['chapters'])}/{len(page_links)} 个页面")
        
        # 检查是否有章节缺失
        if len(novel_content['chapters']) < len(page_links):
            missing_pages = set(range(1, len(page_links) + 1)) - set(ch['chapter_number'] for ch in novel_content['chapters'])
            if missing_pages:
                logger.error(f"章节缺失: {sorted(missing_pages)}")
                
    def _retry_failed_pages(self, failed_pages: List[int], page_links: List[str], novel_content: Dict[str, Any]) -> None:
        """
        重新尝试抓取失败的页面
        
        Args:
            failed_pages: 失败的页码列表
            page_links: 页面链接列表
            novel_content: 小说内容字典
        """
        retry_infos = []
        for page_num in failed_pages:
            if page_num <= len(page_links):
                url = page_links[page_num - 1]
                retry_infos.append((page_num, url))
        
        if not retry_infos:
            return
            
        logger.info(f"开始重新抓取 {len(retry_infos)} 个失败的页面")
        
        # 使用更少的线程和更长的超时时间进行重试
        max_workers = min(3, len(retry_infos))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交重试任务
            future_to_page = {executor.submit(self._fetch_single_page_with_retry, page_info): page_info for page_info in retry_infos}
            
            retry_results = {}
            
            for future in concurrent.futures.as_completed(future_to_page):
                page_info = future_to_page[future]
                page_num, page_url = page_info
                
                try:
                    result_page_num, result_url, content, success = future.result()
                    
                    if success and content:
                        retry_results[page_num] = {
                            'chapter_number': page_num,
                            'title': f"第 {page_num} 页",
                            'content': content,
                            'url': result_url
                        }
                        logger.info(f"重试成功: 第 {page_num} 页")
                    else:
                        logger.error(f"重试失败: 第 {page_num} 页")
                        
                except Exception as e:
                    logger.error(f"重试第 {page_num} 页时出错: {e}")
            
            # 将重试成功的章节按顺序插入到正确位置
            if retry_results:
                # 先移除可能存在的重复章节
                novel_content['chapters'] = [ch for ch in novel_content['chapters'] if ch['chapter_number'] not in retry_results]
                
                # 重新排序所有章节
                all_chapters = novel_content['chapters'] + list(retry_results.values())
                novel_content['chapters'] = sorted(all_chapters, key=lambda x: x['chapter_number'])
    
    def _get_url_content_optimized(self, url: str) -> Optional[str]:
        """
        优化的URL内容获取方法，减少重试次数和延迟
        
        Args:
            url: 目标URL
            
        Returns:
            页面内容或None
        """
        try:
            # 使用更短的超时时间
            response = self.session.get(url, timeout=(5, 10))  # 连接5s，读取10s
            
            if response.status_code == 200:
                response.encoding = 'utf-8'
                return response.text
            elif response.status_code == 404:
                logger.warning(f"页面不存在: {url}")
                return None
            else:
                # 对于其他错误，只重试1次
                logger.warning(f"HTTP {response.status_code} 获取失败，尝试重试: {url}")
                response = self.session.get(url, timeout=(5, 10))
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response.text
                return None
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"请求失败: {url}, 错误: {e}")
            return None
    
    def _extract_content_optimized(self, content: str) -> str:
        """
        优化的内容提取方法，提高正则匹配效率
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容
        """
        # 优先尝试最可能成功的正则表达式
        patterns = [
            r'<article class="page-content-single small single">(.*?)</article>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>'
        ]
        
        for pattern in patterns:
            # 不使用DOTALL，提高性能
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return extracted
        
        # 如果上面的模式失败，再尝试更通用的模式
        patterns_fallback = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*id="content"[^>]*>(.*?)</div>'
        ]
        
        for pattern in patterns_fallback:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return extracted
        
        return ""
    
    def _get_all_pages(self, page_links: List[str], novel_content: Dict[str, Any]) -> None:
        """
        抓取所有页面内容 - 智能选择串行或并行模式
        
        Args:
            page_links: 页面链接列表
            novel_content: 小说内容字典
        """
        # 根据页面数量智能选择处理模式
        if len(page_links) > 3:
            # 页面较多，使用并行处理
            self._get_all_pages_parallel(page_links, novel_content)
        else:
            # 页面较少，使用串行处理
            self._get_all_pages_serial(page_links, novel_content)
    
    def _get_all_pages_serial(self, page_links: List[str], novel_content: Dict[str, Any]) -> None:
        """
        串行抓取所有页面内容 - 优化版本
        
        Args:
            page_links: 页面链接列表
            novel_content: 小说内容字典
        """
        self.chapter_count = 0
        
        # 批量处理页面，减少延迟
        for i, page_url in enumerate(page_links):
            self.chapter_count += 1
            
            # 减少调试信息输出
            if i % 10 == 0:  # 每10页输出一次进度
                logger.info(f"正在抓取第 {self.chapter_count}/{len(page_links)} 页")
            
            # 获取页面内容（使用优化后的请求方法）
            page_content = self._get_url_content_optimized(page_url)
            
            if page_content:
                # 优化内容提取
                chapter_content = self._extract_content_optimized(page_content)
                
                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': f"第 {self.chapter_count} 页",
                        'content': processed_content,
                        'url': page_url
                    })
                    # 减少成功日志
                else:
                    logger.warning(f"第 {self.chapter_count} 页内容提取失败")
            else:
                logger.warning(f"第 {self.chapter_count} 页抓取失败")
            
            # 优化延迟策略：根据页面数量动态调整延迟
            if len(page_links) > 5:
                import time
                time.sleep(0.3)  # 减少到0.3秒，提高速度
    
    def _clean_dpyqxs_content(self, content: str) -> str:
        """
        清理dpyqxs.com特定的内容干扰 - 优化版本
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 第一步：必须先移除script和style标签及其内容（使用DOTALL）
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 第二步：移除其他HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 第三步：清理特定的广告文本
        ad_patterns = [
            r'返回.*?首页',
            r'上一页.*?下一页',
            r'第\s*\d+\s*页',
            r'post-page-numbers',
            r'返回顶部',
            r'上一章.*?下一章',
            r'上一页.*?下一页'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # 第四步：清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 移除开头和结尾的空行
        content = content.strip()
        
        return content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - dpyqxs.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []