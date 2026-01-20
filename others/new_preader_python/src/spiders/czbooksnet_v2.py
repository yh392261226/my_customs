"""
czbooks.net 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class CzbooksnetParser(BaseParser):
    """czbooks.net 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 初始化实例变量
        self._current_novel_id = ""
        self._current_chapter_links = []
        self.chapter_count = 0
    
    # 基本信息
    name = "czbooks.net"
    description = "czbooks.net 小说解析器"
    base_url = "https://czbooks.net"
    
    # 正则表达式配置
    title_reg = [
        r'《([^》]+)》',
        r'<title>([^<]+)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*class\s*=\s*"content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'連載狀態\s*([^<\s]+)',
        r'状态[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型
    book_type = ["多章节", "短篇+多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_content_obs",  # 清理内容中的干扰
        "_remove_ads",  # 移除广告
        "_convert_traditional_to_simplified" # 繁体转简体
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/n/{novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        自动检测书籍类型
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # czbooks.net主要是多章节小说
        if "chapter-list" in content and "nav chapter-list" in content:
            return "多章节"
        return "短篇"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取书籍ID并设置到实例变量
        novel_id = self._extract_novel_id_from_url(novel_url)
        self._current_novel_id = novel_id
        
        print(f"开始解析书籍: {title} (ID: {novel_id})")
        
        # 提取章节链接
        chapter_links = self._extract_chapter_links(content)
        
        if not chapter_links:
            raise Exception("无法提取章节列表")
        
        print(f"发现 {len(chapter_links)} 个章节")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 保存章节链接列表供排序使用
        self._current_chapter_links = chapter_links
        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
        """
        提取章节链接列表
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        import re
        chapter_links = []
        
        # 获取当前书籍的ID
        current_novel_id = getattr(self, '_current_novel_id', '')
        if not current_novel_id:
            # 如果没有设置当前书籍ID，尝试从URL中提取
            # 这里可以通过其他方式获取，暂时使用空字符串
            current_novel_id = ''
        
        # 方法1: 首先尝试从章节列表区域提取（适用于JavaScript渲染后的内容）
        chapter_list_match = re.search(r'<ul[^>]*class\s*=\s*"nav chapter-list"[^>]*id\s*=\s*"chapter-list"[^>]*>(.*?)</ul>', content, re.IGNORECASE | re.DOTALL)
        
        if chapter_list_match:
            chapter_list_content = chapter_list_match.group(1)
            
            # czbooks.net新的章节链接模式，不在链接中包含chapterNumber
            # <a href="//czbooks.net/n/umkof/umhp9">第1章 美女班長（修改完成）</a>
            pattern = r'<a[^>]*href="//([^"\"]+/n/[^"\"]+/[^"\"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, chapter_list_content, re.IGNORECASE)
            
            for href, chapter_title in matches:
                # 构建完整的章节URL
                chapter_url = f"https://{href}"
                
                # 验证链接属于当前书籍
                if self._is_valid_chapter_link(chapter_url, current_novel_id):
                    chapter_links.append({
                        'url': chapter_url,
                        'title': chapter_title.strip()
                    })
        
        # 方法2: 如果章节列表区域不存在，从整个页面提取并过滤（适用于静态HTML）
        if not chapter_links and current_novel_id:
            # 查找所有章节链接（新的格式）
            pattern = r'href=["\']([^"\']*//[^"\']*/n/[^"\']+/[^"\']*)["\']'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            # 提取对应的标题
            title_pattern = r'<a[^>]*href=["\'][^"\']*//[^"\']*/n/[^"\']+/[^"\']*["\'][^>]*>([^<]+)</a>'
            title_matches = re.findall(title_pattern, content, re.IGNORECASE)
            
            for i, href in enumerate(matches):
                if i < len(title_matches):
                    chapter_title = title_matches[i]
                    # 构建完整的URL
                    if href.startswith('//'):
                        chapter_url = f"https:{href}"
                    elif href.startswith('/'):
                        chapter_url = f"https://czbooks.net{href}"
                    else:
                        chapter_url = href
                    
                    # 验证链接属于当前书籍
                    if self._is_valid_chapter_link(chapter_url, current_novel_id):
                        chapter_links.append({
                            'url': chapter_url,
                            'title': chapter_title.strip()
                        })
        
        # 使用基类方法按章节编号排序
        self._sort_chapters_by_number(chapter_links)
        
        return chapter_links
    
    def _is_valid_chapter_link(self, url: str, novel_id: str) -> bool:
        """
        验证章节链接是否属于指定的书籍
        
        Args:
            url: 章节URL
            novel_id: 书籍ID
            
        Returns:
            是否为有效链接
        """
        if not novel_id:
            return True  # 如果没有提供书籍ID，接受所有链接
        
        # 从URL中提取书籍ID
        import re
        match = re.search(r'/n/([^/?]+)', url)
        if match:
            url_novel_id = match.group(1)
            return url_novel_id == novel_id
        
        return False
    

    
    def _extract_chapter_number(self, url: str) -> int:
        """
        从URL中提取章节编号
        
        Args:
            url: 章节URL
            
        Returns:
            章节编号
        """
        import re
        
        # 新版本URL不再包含chapterNumber参数，尝试从路径中提取序号
        # 例如: //czbooks.net/n/umkof/umhp9 -> 尝试提取最后的序号部分
        
        # 首先尝试从标题中提取章节编号
        # 例如: 第1章 美女班長 -> 提取 1
        if hasattr(self, '_current_chapter_links'):
            for link_info in self._current_chapter_links:
                if link_info.get('url') == url:
                    title = link_info.get('title', '')
                    return self._extract_chapter_number_from_title(title)
        
        # 如果无法从标题提取，尝试从URL路径中提取
        # 有些URL可能包含序号，如 /umhp9 -> 9
        path_part = url.split('/')[-1]
        number_match = re.search(r'(\d+)', path_part)
        if number_match:
            return int(number_match.group(1))
        
        # 如果都找不到，返回0（会按列表顺序排序）
        return 0
    
    def _get_url_content(self, url: str, max_retries: int = 3) -> str:
        """
        获取页面内容，对于章节页面使用特殊处理
        
        Args:
            url: 页面URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容
        """
        # 新版章节URL格式: //czbooks.net/n/{novel_id}/{chapter_id}
        # 主页格式: //czbooks.net/n/{novel_id}
        # 通过URL路径段数区分章节页面和主页
        url_parts = url.split('/')
        
        # 如果是章节页面，使用特殊处理
        if '/n/' in url and len(url_parts) >= 6:  # 至少有 http:,, czbooks.net, n, {novel_id}, {chapter_id}
            self.logger.info(f"检测到章节页面，使用增强内容获取: {url}")
            return self._get_chapter_content_enhanced(url)
        
        # 对于非章节页面（如主页），使用普通HTTP请求
        return super()._get_url_content(url, max_retries)
    
    def _get_chapter_content_enhanced(self, url: str) -> str:
        """
        增强的章节内容获取方法 - 直接从HTML中提取content div内容
        
        Args:
            url: 章节URL
            
        Returns:
            章节内容
        """
        import re
        
        # 获取章节页面的HTML内容
        html_content = super()._get_url_content(url)
        
        if not html_content:
            self.logger.warning(f"⚠ 无法获取章节页面HTML: {url}")
            return ""
        
        # 直接使用配置的正则表达式提取 <div class="content"> 内容
        # 这是用户明确指出的内容位置，注意czbooks.net使用 class = "content" 格式（有空格）
        content_pattern = r'<div[^>]*class\s*=\s*"content"[^>]*>(.*?)</div>'
        match = re.search(content_pattern, html_content, re.IGNORECASE | re.DOTALL)
        
        if match:
            raw_content = match.group(1)
            print(f"✓ 找到content div，原始内容长度: {len(raw_content)}")
            
            # 基础HTML清理 - 移除HTML标签但保留文本结构
            # 保留段落和换行
            cleaned_content = self._clean_chapter_content(raw_content)
            
            if cleaned_content and len(cleaned_content.strip()) > 10:
                print(f"✓ 内容清理完成，最终长度: {len(cleaned_content)}")
                return cleaned_content
            else:
                print(f"⚠ 内容清理后为空或过短")
                return ""
        else:
            print(f"⚠ 未找到 <div class='content'> 标签")
            
            # 尝试其他可能的内容容器
            fallback_patterns = [
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                r'<article[^>]*>(.*?)</article>',
                r'<section[^>]*>(.*?)</section>',
            ]
            
            for pattern in fallback_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if match:
                    raw_content = match.group(1)
                    cleaned_content = self._clean_chapter_content(raw_content)
                    if cleaned_content and len(cleaned_content.strip()) > 10:
                        print(f"✓ 通过fallback模式找到内容，长度: {len(cleaned_content)}")
                        return cleaned_content
            
            # 如果都找不到，返回明确的错误信息
            return ""
    
    def _get_all_chapters(self, chapter_links: List[Dict[str, str]], novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
        """
        import time
        
        self.chapter_count = 0
        
        for i, chapter_info in enumerate(chapter_links, 1):
            chapter_url = chapter_info['url']
            chapter_title = chapter_info['title']

            self.logger.info(f"正在爬取第 {i}/{len(chapter_links)} 章: {chapter_title}")
            
            # 获取章节内容
            chapter_content = self._get_url_content(chapter_url)
            
            if chapter_content:
                # _get_chapter_content_enhanced 已经提取并清理了内容
                # 不需要再次使用正则表达式提取
                final_content = chapter_content
                
                if final_content and len(final_content.strip()) > 10:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(final_content)
                    final_content = processed_content
                    self.logger.info(f"✓ 第 {i}/{len(chapter_links)} 章抓取成功")
                else:
                    # 内容提取失败，但至少保存章节标题
                    final_content = f"[章节内容暂时无法获取]\n\n章节标题: {chapter_title}\n章节链接: {chapter_url}"
                    self.logger.warning(f"⚠ 第 {i}/{len(chapter_links)} 章内容提取失败，但保存了标题")
                
                novel_content['chapters'].append({
                    'chapter_number': self.chapter_count,
                    'title': chapter_title,
                    'content': final_content,
                    'url': chapter_url
                })
            else:
                self.logger.warning(f"✗ 第 {i}/{len(chapter_links)} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        重写以适配czbooks.net网站的结构
        
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
        
        # 提取简介
        desc = self._extract_description(content)
        
        # 提取作者 (从简介中提取或使用默认值)
        author = self._extract_author(content)
        
        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or "未知标题",
            "desc": desc or "暂无简介",
            "status": status or "未知状态",
            "author": author or "未知作者"
        }
    
    def _extract_description(self, content: str) -> str:
        """
        提取书籍简介
        
        Args:
            content: 页面内容
            
        Returns:
            书籍简介
        """
        import re
        
        pattern = r'<div[^>]*class="description"[^>]*>(.*?)</div>'
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            desc = match.group(1)
            # 清理HTML标签
            desc = re.sub(r'<[^>]+>', '', desc)
            desc = desc.replace('&nbsp;', ' ').replace('\xa0', ' ')
            # 清理多余的空白字符
            desc = re.sub(r'\s+', ' ', desc)
            return desc.strip()
        
        return ""
    
    def _extract_author(self, content: str) -> str:
        """
        提取作者信息
        
        Args:
            content: 页面内容
            
        Returns:
            作者名称
        """
        import re
        
        # czbooks.net可能没有明确的作者信息，返回网站名称作为默认值
        return self.name
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除常见的广告模式
        ad_patterns = [
            r'<div[^>]*class="ad"[^>]*>.*?</div>',
            r'<iframe[^>]*>.*?</iframe>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _clean_chapter_content(self, content: str) -> str:
        """
        专门清理章节内容，移除HTML标签但保留文本结构
        
        Args:
            content: 原始HTML内容
            
        Returns:
            清理后的纯文本内容
        """
        import re
        
        if not content:
            return ""
        
        # 1. 保留段落结构 - 将<p>标签转换为换行
        content = re.sub(r'<p[^>]*>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'</p>', '\n', content, flags=re.IGNORECASE)
        
        # 2. 保留换行 - 将<br>标签转换为换行
        content = re.sub(r'<br[^>]*>', '\n', content, flags=re.IGNORECASE)
        
        # 3. 保留div分隔 - 将</div>转换为换行
        content = re.sub(r'</div>', '\n', content, flags=re.IGNORECASE)
        
        # 4. 移除所有其他HTML标签
        content = re.sub(r'<[^>]+>', '', content, flags=re.IGNORECASE)
        
        # 5. 解码常见的HTML实体
        html_entities = {
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&apos;': "'",
            '&#39;': "'",
            '&#34;': '"',
            '&#38;': '&',
            '&#60;': '<',
            '&#62;': '>'
        }
        
        for entity, char in html_entities.items():
            content = content.replace(entity, char)
        
        # 6. 移除数字HTML实体编码 (如 &#1234;)
        content = re.sub(r'&#\d{1,6};', '', content)
        
        # 7. 清理多余的空白字符
        # 将连续的空白字符替换为单个空格
        content = re.sub(r'[ \t]+', ' ', content)
        
        # 将连续的换行符合并，但保留段落分隔
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # 8. 移除行首行尾空白
        lines = content.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        
        # 9. 重新组合，确保段落间有适当的空行
        result = '\n\n'.join(cleaned_lines)
        
        return result.strip()
    
    def _clean_content_obs(self, content: str) -> str:
        """
        清理内容中的干扰，提取纯文本
        
        Args:
            content: 内容
            
        Returns:
            清理后的纯文本
        """
        import re
        
        # 移除以#&开头、中间有数字、以;结尾的干扰字符串
        clean_text = re.sub(r'&#\d{1,10};', '', content)
        
        # 同时移除其他可能的HTML实体编码干扰
        clean_text = re.sub(r'&#\d{1,5};', '', clean_text)
        
        # 移除多余的空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)

        clean_text = re.sub(r'(快捷键←) [上一章][回目录] [下一章] (快捷键→)书签收藏 投推荐票 打开书架 返回书目 返回书页', '', clean_text)
        
        return clean_text.strip()
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        import re
        
        # 从URL中提取/n/后面的部分
        match = re.search(r'/n/([^/?]+)', url)
        if match:
            return match.group(1)
        
        # 如果没有找到，使用默认方法
        return super()._extract_novel_id_from_url(url)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - czbooks.net不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []