"""
aabook.xyz 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
import time
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AabookParser(BaseParser):
    """aabook.xyz 小说解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "aabook.xyz"
    description = "aabook.xyz 小说解析器"
    base_url = "https://aabook.xyz"
    
    # 正则表达式配置
    title_reg = [
        r"<h3 class=\"book_name\"><a[^>]*>(.*?)</a></h3>",
        r'<title>(.*?)[\s\-_]+疯情书库</title>'
    ]
    
    content_reg = [
        r"<div[^>]*class=\"[^\"]*content[^\"]*\"[^>]*>(.*?)</div>",
        r"<div[^>]*id=\"[^\"]*content[^\"]*\"[^>]*>(.*?)</div>",
        r"<article[^>]*>(.*?)</article>"
    ]
    
    status_reg = [
        r'作品状态[：:]\s*(.*?)[<\n\r]',
        r'status[：:]\s*(.*?)[<\n\r]'
    ]
    
    # 支持的书籍类型
    book_type = ["多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_content_specific",  # 特定内容清理
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
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
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配aabook.xyz的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/book-{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，aabook.xyz主要是多章节小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # aabook.xyz主要是多章节小说
        return "多章节"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑
        
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
        
        # 获取章节列表
        chapter_links = self._get_chapter_list(book_id)
        if not chapter_links:
            raise Exception("无法获取章节列表")
        
        print(f"发现 {len(chapter_links)} 个章节")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': book_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _extract_book_id_from_url(self, url: str) -> Optional[str]:
        """
        从书籍URL中提取书籍ID
        
        Args:
            url: 书籍URL
            
        Returns:
            书籍ID或None
        """
        match = re.search(r'book-(\d+)\.html', url)
        return match.group(1) if match else None
    
    def _get_chapter_list(self, book_id: str) -> List[Dict[str, str]]:
        """
        获取章节列表
        
        Args:
            book_id: 书籍ID
            
        Returns:
            章节链接列表
        """
        chapter_list_url = f"{self.base_url}/chapterList-{book_id}.html"
        
        print(f"正在获取章节列表: {chapter_list_url}")
        
        content = self._get_url_content(chapter_list_url)
        if not content:
            logger.error(f"无法获取章节列表页面: {chapter_list_url}")
            return []
        
        logger.debug(f"章节列表页面内容长度: {len(content)}")
        
        chapter_links = []
        
        # 解析章节列表 - aabook.xyz的章节在第二个ul中
        # 首先尝试查找section_list
        section_list_pattern = r'<ul[^>]*class="[^"]*section_list[^"]*"[^>]*>(.*?)</ul>'
        section_match = re.search(section_list_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if section_match:
            section_content = section_match.group(1)
            logger.debug(f"找到section_list，内容长度: {len(section_content)}")
            
            # 提取每个章节链接
            chapter_pattern = r'<li[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>\s*</li>'
            chapter_matches = re.findall(chapter_pattern, section_content, re.IGNORECASE)
            
            logger.debug(f"找到 {len(chapter_matches)} 个章节链接")
            
            for href, title in chapter_matches:
                # 清理标题
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                # 确保URL格式正确
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = f"{self.base_url}/{href}"
                chapter_links.append({
                    'url': full_url,
                    'title': clean_title,
                    'chapter_id': self._extract_chapter_id_from_url(href)
                })
        
        # 如果section_list为空或找不到，使用更通用的方法
        if not chapter_links:
            logger.info("section_list为空，使用通用方法提取章节链接")
            
            # 查找所有ul元素，找到包含章节链接的那个
            ul_pattern = r'<ul[^>]*>(.*?)</ul>'
            ul_matches = re.findall(ul_pattern, content, re.IGNORECASE | re.DOTALL)
            
            for i, ul_content in enumerate(ul_matches):
                # 在每个ul中查找章节链接
                chapter_pattern = r'<li[^>]*>\s*<a[^>]*href="([^"]*read-(\d+)\.html)"[^>]*>(.*?)</a>\s*</li>'
                chapter_matches = re.findall(chapter_pattern, ul_content, re.IGNORECASE)
                
                if chapter_matches:
                    logger.debug(f"在第 {i+1} 个ul中找到 {len(chapter_matches)} 个章节")
                    
                    for href, chapter_id, title in chapter_matches:
                        clean_title = re.sub(r'<[^>]+>', '', title).strip()
                        # 确保URL格式正确
                        if href.startswith('http'):
                            full_url = href
                        elif href.startswith('/'):
                            full_url = f"{self.base_url}{href}"
                        else:
                            full_url = f"{self.base_url}/{href}"
                        chapter_links.append({
                            'url': full_url,
                            'title': clean_title,
                            'chapter_id': chapter_id
                        })
                    break  # 找到章节后就停止搜索其他ul
        
        # 最后的备用方法：直接在整个页面中搜索章节链接
        if not chapter_links:
            logger.warning("使用备用方法搜索章节链接")
            alt_pattern = r'<a[^>]*href="([^"]*read-(\d+)\.html)"[^>]*>(.*?)</a>'
            alt_matches = re.findall(alt_pattern, content, re.IGNORECASE)
            
            for href, chapter_id, title in alt_matches:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                # 确保URL格式正确
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = f"{self.base_url}/{href}"
                chapter_links.append({
                    'url': full_url,
                    'title': clean_title,
                    'chapter_id': chapter_id
                })
        
        logger.info(f"从章节列表页面提取到 {len(chapter_links)} 个章节")
        
        # 使用基类方法按章节编号排序
        self._sort_chapters_by_number(chapter_links)
        
        return chapter_links
    
    def _extract_chapter_id_from_url(self, url: str) -> Optional[str]:
        """
        从章节URL中提取章节ID
        
        Args:
            url: 章节URL
            
        Returns:
            章节ID或None
        """
        match = re.search(r'read-(\d+)\.html', url)
        return match.group(1) if match else None
    
    def _get_all_chapters(self, chapter_links: List[Dict[str, str]], novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
        """
        self.chapter_count = 0
        
        for chapter_info in chapter_links:
            self.chapter_count += 1
            chapter_url = chapter_info['url']
            chapter_title = chapter_info['title']
            chapter_id = chapter_info['chapter_id']
            
            print(f"正在抓取第 {self.chapter_count} 章: {chapter_title}")
            
            # 获取章节内容
            chapter_content = self._get_chapter_content(chapter_url, chapter_id)
            
            if chapter_content:
                novel_content['chapters'].append({
                    'chapter_number': self.chapter_count,
                    'title': chapter_title,
                    'content': chapter_content,
                    'url': chapter_url
                })
                print(f"√ 第 {self.chapter_count} 章抓取成功")
            else:
                print(f"× 第 {self.chapter_count} 章内容抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def _get_chapter_content(self, chapter_url: str, chapter_id: str) -> Optional[str]:
        """
        获取章节内容 - 通过AJAX请求获取
        
        Args:
            chapter_url: 章节URL
            chapter_id: 章节ID
            
        Returns:
            章节内容或None
        """
        # 首先获取章节页面，提取v参数
        page_content = self._get_url_content(chapter_url)
        if not page_content:
            logger.warning(f"无法获取章节页面: {chapter_url}")
            return None
        
        # 从页面中提取v参数
        v_parameter = self._extract_v_parameter(page_content, chapter_id)
        if not v_parameter:
            logger.warning(f"无法从页面提取v参数: {chapter_url}")
            return None
        
        # 构建AJAX请求URL
        ajax_url = f"{self.base_url}/_getcontent.php?id={chapter_id}&v={v_parameter}"
        
        print(f"正在通过AJAX获取内容: {ajax_url}")
        
        # 发送AJAX请求获取内容
        try:
            response = self.session.get(ajax_url, timeout=10)
            if response.status_code == 200:
                content = response.text.strip()
                
                # 检查是否为错误响应
                if content == "readerror":
                    logger.warning(f"服务器返回读取错误: {chapter_id}")
                    return None
                
                # 执行爬取后处理函数
                processed_content = self._execute_after_crawler_funcs(content)
                
                # 检查内容是否有效（至少包含一些中文字符）
                if processed_content and len(processed_content.strip()) > 50 and re.search(r'[\u4e00-\u9fff]', processed_content):
                    return processed_content
                else:
                    logger.warning(f"获取的内容无效或过短: {chapter_id}")
                    return None
            else:
                logger.warning(f"AJAX请求失败，HTTP状态码: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"AJAX请求异常: {e}")
            return None
    
    def _extract_v_parameter(self, page_content: str, chapter_id: str) -> Optional[str]:
        """
        从页面内容中提取v参数
        
        Args:
            page_content: 章节页面的HTML内容
            chapter_id: 章节ID
            
        Returns:
            v参数值或None
        """
        # 查找包含_getcontent.php的JavaScript代码
        patterns = [
            # 直接查找v参数
            r'_getcontent\.php\?id=' + re.escape(chapter_id) + r'&v=([^&\'"\s]+)',
            r'_getcontent\.php\?id=\d+&v=([^&\'"\s]+)',
            # 查找ajaxGetContent函数调用
            r'ajaxGetContent\(\'' + re.escape(chapter_id) + r'\'\)[^}]*?v=([^&\'"\s]+)',
            r'ajaxGetContent\(\'' + re.escape(chapter_id) + r'\'\)[^}]*?["\']v["\']:\s*["\']([^"\']+) ["\']',
            # 更宽泛的模式
            r'\.get\(".*?_getcontent\.php[^"]*v=([^&\'"\s]+)',
            r'_getcontent\.php[^v]*v=([^&\'"\s]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                v_value = match.strip()
                if v_value and len(v_value) > 10:  # v参数通常比较长
                    logger.info(f"成功提取v参数: {v_value[:20]}...")
                    return v_value
        
        # 如果上述方法都失败，尝试查找所有可能的v参数
        logger.warning(f"无法从页面提取v参数，章节ID: {chapter_id}")
        
        # 调试：输出页面内容的一部分以便排查
        content_sample = page_content[:1000] if len(page_content) > 1000 else page_content
        logger.debug(f"页面内容示例: {content_sample}")
        
        return None
    
    def _extract_v_parameter(self, page_content: str, chapter_id: str) -> Optional[str]:
        """
        从页面中提取AJAX请求所需的v参数
        
        Args:
            page_content: 页面HTML内容
            chapter_id: 章节ID
            
        Returns:
            v参数值或None
        """
        # 方法1: 从JavaScript代码中提取v参数
        v_patterns = [
            # 直接匹配ajaxGetContent函数调用中的v参数
            r'ajaxGetContent\(["\']' + re.escape(chapter_id) + r'["\'][^;]*?v=([^&\s\"\"]+)',
            # 匹配_getcontent.php请求中的v参数
            r'_getcontent\.php\?id=' + re.escape(chapter_id) + r'&v=([^&\s\"\"]+)',
            # 通用模式：查找v参数
            r'["\']v["\']?\s*[:=]\s*["\']([^"\'&]+)["\']',
            # 查找$.get请求中的v参数
            r'\$\.get\([^)]*v=([^&\s\"\"]+)[^)]*\)',
        ]
        
        for pattern in v_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            for match in matches:
                v_value = match.strip()
                # v参数通常是一段较长的字符串，包含字母数字和特殊字符
                if len(v_value) > 10 and re.search(r'[a-zA-Z0-9_-]', v_value):
                    logger.info(f"成功提取v参数: {v_value}")
                    return v_value
        
        # 方法2: 如果找不到直接匹配，尝试从页面中查找所有可能的v参数值
        # 查找符合v参数特征的字符串（长度较长，包含字母数字和特殊字符）
        v_candidate_pattern = r'["\']([a-zA-Z0-9_-]{20,})["\']'
        candidates = re.findall(v_candidate_pattern, page_content)
        
        for candidate in candidates:
            # 进一步验证是否可能是v参数
            if re.search(r'[A-Z][a-z0-9_-]*', candidate) and len(candidate) > 30:
                logger.info(f"找到可能的v参数候选: {candidate}")
                return candidate
        
        logger.warning(f"无法从页面提取v参数，章节ID: {chapter_id}")
        return None

    def _clean_content_specific(self, content: str) -> str:
        """
        清理aabook.xyz特定的内容干扰
        
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
            # 移除特定的网站元素
            r'疯情书库.*?正文',
            r'抖阴.*?SOUL',
            r'性福宝排行榜',
            r'aabook_readfile',
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        return content.strip()
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写首页元数据获取，适配aabook.xyz的特定结构
        
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
        
        # 提取标签信息
        tags = self._extract_tags(content)
        
        # 提取简介
        description = self._extract_description(content)
        
        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "tags": tags,
            "desc": description or "暂无简介",
            "status": status or "未知状态"
        }
    
    def _extract_tags(self, content: str) -> str:
        """
        提取书籍标签信息
        
        Args:
            content: 页面内容
            
        Returns:
            标签字符串
        """
        # 查找标签信息
        tags_pattern = r'<ul[^>]*class="[^"]*xinxi_content[^"]*"[^>]*style="display:none"[^>]*>(.*?)</ul>'
        tags_match = re.search(tags_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if tags_match:
            tags_content = tags_match.group(1)
            # 提取文本并用逗号连接
            tags_text = re.sub(r'<[^>]+>', ' ', tags_content)
            tags_text = re.sub(r'\s+', ' ', tags_text).strip()
            
            # 按行分割并清理
            tag_lines = [line.strip() for line in tags_text.split('\n') if line.strip()]
            
            # 过滤出包含标签信息的行
            filtered_tags = []
            for line in tag_lines:
                if any(keyword in line for keyword in ['分类', '状态', '字数', '点击']):
                    # 提取标签值
                    if '：' in line or ':' in line:
                        tag_value = re.split(r'[:：]', line)[-1].strip()
                        if tag_value:
                            filtered_tags.append(tag_value)
            
            return ', '.join(filtered_tags)
        
        return ""
    
    def _extract_description(self, content: str) -> str:
        """
        提取书籍简介
        
        Args:
            content: 页面内容
            
        Returns:
            简介文本
        """
        # 查找简介信息
        desc_pattern = r'<p[^>]*class="[^"]*jianjieneirong[^"]*"[^>]*>(.*?)</p>'
        desc_match = re.search(desc_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if desc_match:
            desc_content = desc_match.group(1)
            # 清理HTML标签
            desc_text = re.sub(r'<[^>]+>', '', desc_content)
            desc_text = re.sub(r'\s+', ' ', desc_text).strip()
            return desc_text
        
        return ""
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - aabook.xyz不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []