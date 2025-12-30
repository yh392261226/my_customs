"""
热奇小说网解析器 v2 - 基于配置驱动的重构版本
www.renqixiaoshuo.net
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class RenqixiaoshuoParser(BaseParser):
    """热奇小说网解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    name = "热奇小说网"
    description = "热奇小说网整本小说爬取解析器"
    base_url = "https://www.renqixiaoshuo.net"
    
    # 正则表达式配置 - 参考renqixiaoshuo.py
    title_reg = [
        r'<div class="name hang1"><h1>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div class="tjc-cot">(.*?)</div>'
    ]
    
    status_reg = [
        r'<div class="ty">(.*?)</div>'
    ]
    
    # 书籍类型配置 - 热奇小说网使用多章节模式
    book_type = ["多章节"]
    
    # 章节链接正则 - 从章节列表中提取
    chapter_link_reg = [
        r'<a href="(/d/\d+/\d+)"[^>]*>(.*?)</a>'
    ]
    
    # 内容页面链接正则 - 用于检测内容页内分页模式
    content_page_link_reg = [
        r'<a id="btnread" href="(.*?)" class="stayd">开始阅读'
    ]
    
    # 下一页链接正则 - 参考renqixiaoshuo.py
    next_page_link_reg = [
        r'<a href="(.*?)">下一章 >'  # 下一章链接
    ]
    
    # 书籍ID提取正则 - 参考renqixiaoshuo.py
    book_id_reg = [
        r'/b/(\d+)',  # 从URL中提取书籍ID
        r'/d/(\d+)/\d+'  # 从章节链接中提取书籍ID
    ]
    
    # 处理函数链
    after_crawler_func = ["_clean_html_tags", "_remove_ads", "_format_content"]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        super().__init__(proxy_config, novel_site_name)
        self.chapter_count = 0
        # 添加User-Agent和Referer以绕过反爬虫
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.renqixiaoshuo.net/'
        })
    
    def _clean_html_tags(self, content: str) -> str:
        """
        清理HTML标签，提取纯文本内容
        
        Args:
            content: 原始HTML内容
            
        Returns:
            清理后的纯文本内容
        """
        # 移除所有HTML标签
        clean_text = re.sub(r'<[^>]+>', '', content)
        
        # 替换HTML实体
        clean_text = clean_text.replace('&nbsp;', ' ').replace('\xa0', ' ')
        
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # 移除首尾空白
        clean_text = clean_text.strip()
        
        return clean_text
    
    def _remove_ads(self, content: str) -> str:
        """
        移除热奇小说网特有的广告内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 移除script标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        
        # 移除style标签
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        # 移除特定广告div
        content = re.sub(r'<div[^>]*class=["\']ad["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL)
        content = re.sub(r'<div[^>]*id=["\']ad["\'][^>]*>.*?</div>', '', content, flags=re.DOTALL)
        
        # 移除iframe
        content = re.sub(r'<iframe[^>]*>.*?</iframe>', '', content, flags=re.DOTALL)
        
        return content
    
    def _format_content(self, content: str) -> str:
        """
        格式化内容，热奇小说网特有格式
        
        Args:
            content: 清理后的内容
            
        Returns:
            格式化后的内容
        """
        # 替换多个换行为单个换行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 移除多余空格
        content = re.sub(r'\s{2,}', ' ', content)
        
        # 确保每段开头有缩进
        content = re.sub(r'^', '    ', content, flags=re.MULTILINE)
        
        return content
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型（热奇小说网特有逻辑）
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 热奇小说网采用多章节模式
        return "多章节"
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情（重写基类方法，添加热奇小说网特有逻辑）
        
        Args:
            novel_id: 书籍ID
            
        Returns:
            小说详细信息
        """
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        
        # 首先验证novel_id参数的有效性
        if not novel_id or novel_id.strip() == "":
            raise ValueError("小说ID不能为空")
        
        # 检查是否是HTML内容（包含HTML标签）
        import re
        if re.search(r'<[^>]+>', novel_id):
            # 如果是HTML内容，说明传入的是页面内容而不是ID
            # 这种情况下，我们需要专注于当前页面的内容，而不是提取其他书籍的ID
            
            # 首先检查是否是书籍列表页面（包含章节列表）
            if '章节目录' in novel_id or '章节列表' in novel_id:
                # 如果是书籍列表页面，提取当前页面的书籍ID
                # 优先从明确的标识提取，避免匹配推荐书籍的链接
                patterns = [
                    r'data-bookid="(\d+)"',  # 从data-bookid属性提取
                    r'/b/(\d+)(?!.*/b/\d+)'  # 当前页面的URL，避免匹配多个
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, novel_id)
                    if match:
                        novel_id = match.group(1)
                        print(f"从书籍列表页面提取到当前书籍ID: {novel_id}")
                        break
                else:
                    # 如果无法提取，尝试更宽松的模式
                    match = re.search(r'/b/(\d+)', novel_id)
                    if match:
                        novel_id = match.group(1)
                        print(f"使用宽松模式提取书籍ID: {novel_id}")
                    else:
                        raise ValueError(f"无法从书籍列表页面提取有效的书籍ID")
            else:
                # 如果是内容页面或其他页面，直接抛出错误
                raise ValueError("parse_novel_detail方法应该接收书籍ID或书籍列表页面内容，而不是内容页面")
        
        # 最终验证ID是否为纯数字
        if not re.match(r'^\d+$', novel_id):
            raise ValueError(f"小说ID必须是纯数字: {novel_id}")
        
        # 直接调用基类方法，传入正确的书籍ID
        novel_info = super().parse_novel_detail(novel_id)
        
        # 添加热奇小说网特有信息
        novel_info['source'] = 'renqixiaoshuo'
        novel_info['site_name'] = self.name
        
        return novel_info
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID - 热奇小说网特定实现
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        import re
        
        # 首先检查是否是HTML内容（包含HTML标签）
        if re.search(r'<[^>]+>', url):
            # 如果是HTML内容，说明传入的是页面内容而不是ID
            # 这种情况下，我们需要专注于当前页面的内容，而不是提取其他书籍的ID
            
            # 首先检查是否是书籍列表页面（包含章节列表）
            if '章节目录' in url or '章节列表' in url:
                # 如果是书籍列表页面，提取当前页面的书籍ID
                # 优先从明确的标识提取，避免匹配推荐书籍的链接
                patterns = [
                    r'data-bookid="(\d+)"',  # 从data-bookid属性提取
                    r'/b/(\d+)(?!.*/b/\d+)'  # 当前页面的URL，避免匹配多个
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, url)
                    if match:
                        novel_id = match.group(1)
                        # 验证提取的ID是否为纯数字
                        if re.match(r'^\d+$', novel_id):
                            print(f"从书籍列表页面提取到当前书籍ID: {novel_id}")
                            return novel_id
                
                # 如果无法提取，尝试更宽松的模式
                match = re.search(r'/b/(\d+)', url)
                if match:
                    novel_id = match.group(1)
                    print(f"使用宽松模式提取书籍ID: {novel_id}")
                    return novel_id
                else:
                    raise ValueError(f"无法从书籍列表页面提取有效的书籍ID")
            else:
                # 如果是内容页面或其他页面，直接抛出错误
                raise ValueError("_extract_novel_id_from_url方法应该接收书籍ID或书籍列表页面内容，而不是内容页面")
        
        # 如果是正常的URL，尝试从URL中提取数字ID
        # 热奇小说网URL格式：https://www.renqixiaoshuo.net/b/1100
        
        # 更精确的模式匹配，确保匹配完整的URL路径
        patterns = [
            r'/b/(\d+)(?!.*/b/\d+)',  # 避免匹配多个书籍ID
            r'/b/(\d+)'  # 宽松模式
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                extracted_id = match.group(1)
                print(f"从URL中提取到书籍ID: {extracted_id}")
                return extracted_id
        
        # 如果无法提取数字ID，使用基类的默认实现
        return super()._extract_novel_id_from_url(url)
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说 - 热奇小说网实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        import re
        import time
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 从章节列表中提取所有章节链接
        chapter_links = self._extract_chapter_links(content)
        
        if not chapter_links:
            raise Exception("无法提取章节列表")
        
        print(f"找到 {len(chapter_links)} 个章节")
        
        # 抓取每个章节的内容
        for i, chapter_url in enumerate(chapter_links, 1):
            print(f"正在抓取第 {i} 章: {chapter_url}")
            
            # 获取章节内容
            chapter_content = self._get_url_content(chapter_url)
            
            if chapter_content:
                # 提取章节正文内容
                content_text = self._extract_with_regex(chapter_content, self.content_reg)
                
                if content_text:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(content_text)
                    
                    # 提取章节标题
                    chapter_title = self._extract_chapter_title(chapter_content, chapter_url)
                    
                    # 添加到章节列表
                    novel_content['chapters'].append({
                        'chapter_number': i,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': chapter_url
                    })
                    print(f"√ 第 {i} 章抓取成功")
                else:
                    print(f"× 第 {i} 章内容提取失败")
            else:
                print(f"× 第 {i} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
        
        print(f"总共抓取 {len(novel_content['chapters'])} 章内容")
        return novel_content
    
    def _extract_chapter_links(self, content: str) -> List[str]:
        """
        从书籍列表页面提取章节链接
        
        Args:
            content: 书籍列表页面内容
            
        Returns:
            章节链接列表
        """
        import re
        
        # 查找章节列表容器
        chapter_container_match = re.search(r'<ul[^>]*class="tjzl"[^>]*id="chapterlsit"[^>]*>(.*?)</ul>', content, re.DOTALL)
        if not chapter_container_match:
            return []
        
        chapter_container = chapter_container_match.group(1)
        
        # 提取所有章节链接 - 使用更宽松的正则表达式匹配各种章节标题格式
        chapter_links = []
        
        # 查找所有章节链接，匹配各种章节标题格式
        # 支持：第01章、第一章、第1章、第一章 标题、特殊章节标题等
        chapter_matches = re.findall(r'<a href="(/d/\d+/\d+)"[^>]*>(.*?)</a>', chapter_container)
        
        for chapter_url, chapter_title in chapter_matches:
            # 过滤掉非章节链接（如网站导航、推荐小说等）
            # 只保留有效的章节链接
            if chapter_url and chapter_url.startswith('/d/'):
                full_url = f"{self.base_url}{chapter_url}"
                chapter_links.append(full_url)
        
        # 使用基类方法按章节编号排序
        self._sort_chapters_by_number(chapter_links)

        return chapter_links
    
    def _extract_chapter_title(self, content: str, current_url: str) -> str:
        """
        从内容页面提取章节标题
        
        Args:
            content: 页面内容
            current_url: 当前页面URL
            
        Returns:
            章节标题
        """
        import re
        
        # 多种方式提取章节标题
        title_patterns = [
            # 从页面标题中提取
            (r'<title>(.*?)</title>', True),
            # 从h1标签中提取
            (r'<h1[^>]*>(.*?)</h1>', True),
            # 从h2标签中提取
            (r'<h2[^>]*>(.*?)</h2>', True),
            # 从章节导航中提取（热奇小说网特定）
            (r'<div[^>]*class="tjbreak"[^>]*>.*?<h2>(.*?)</h2>', True),
            # 从章节标题div中提取
            (r'<div[^>]*class="rtj-title"[^>]*>.*?<h1>(.*?)</h1>', True)
        ]
        
        for pattern, needs_cleaning in title_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                title = match.group(1).strip()
                
                if needs_cleaning:
                    # 清理标题 - 移除网站名称和多余的符号
                    title = re.sub(r'[-_\|].*', '', title).strip()
                    title = re.sub(r'小说.*全文阅读', '', title).strip()
                    title = re.sub(r'我的狗老公\s*-?\s*', '', title).strip()
                    
                if title:
                    return title
        
        # 从URL中提取章节编号作为备用方案
        chapter_match = re.search(r'/d/\d+/(\d+)', current_url)
        if chapter_match:
            chapter_num = chapter_match.group(1)
            return f"第{chapter_num}章"
        
        # 如果都无法提取，使用默认标题
        return f"第 {self.chapter_count} 章"
    
    def _parse_content_pagination_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析内容页内分页模式的小说 - 热奇小说网实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 热奇小说网实际上是多章节模式，不是内容页内分页
        # 所以这里应该重定向到多章节解析逻辑
        print(f"检测到热奇小说网采用多章节模式，切换到多章节解析")
        return self._parse_multichapter_novel(content, novel_url, title)
    
    def _get_next_page_url(self, content: str, current_url: str) -> Optional[str]:
        """
        从内容页面获取下一页链接
        
        Args:
            content: 当前页面内容
            current_url: 当前页面URL
            
        Returns:
            下一页URL或None（如果没有下一页）
        """
        import re
        
        # 使用配置的正则表达式提取下一页链接
        for pattern in self.next_page_link_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                next_url = match.group(1)
                # 构建完整URL
                if next_url.startswith('/'):
                    return f"{self.base_url}{next_url}"
                elif next_url.startswith('http'):
                    return next_url
                else:
                    # 相对路径处理
                    import os
                    base_dir = os.path.dirname(current_url)
                    return f"{base_dir}/{next_url}"
        
        # 如果没有找到下一页链接，返回None表示结束
        return None