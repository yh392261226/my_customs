"""
87NB小说网解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class Nb87Parser(BaseParser):
    """87NB小说网解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "87NB小说网"
    description = "87NB小说网整本小说爬取解析器"
    base_url = "https://www.87nb.com"
    
    # 正则表达式配置 - 与原始版本保持一致
    title_reg = [
        r'<div class="bookintro">\s*<p[^>]*>\s*<a[^>]*title="([^"]*)"[^>]*>',
        r'<div class="bookintro">\s*<p[^>]*>\s*<a[^>]*>([^<]*)</a>',
        r'<h1[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*id="booktxt"[^>]*>(.*?)</div>',
        r'<div class="booktxt"[^>]*>(.*?)</div>',
        r'<div class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div class="bookdes">\s*<p[^>]*>(.*?)</p>',
        r'小说状态[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_replace_special_chars",  # 87NB特有的字符替换
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
        
        # 87NB特殊字符替换映射
        self.char_replacements = {
            '<img src="/zi/n1.png" width="30px" height="28px"/>': '奶',
            '<img src="/zi/d2.png" width="30px" height="28px"/>': '屌',
            '<img src="/zi/r5.png" width="30px" height="28px"/>': '日',
            '<img src="/zi/q1.png" width="30px" height="28px"/>': '情',
            '<img src="/zi/k1.png" width="30px" height="28px"/>': '口',
            '<img src="/zi/n2.png" width="30px" height="28px"/>': '女',
            '<img src="/zi/r3.png" width="30px" height="28px"/>': '人',
            '<img src="/zi/s1.png" width="30px" height="28px"/>': '射',
            '<img src="/zi/j1.png" width="30px" height="28px"/>': '精',
            '<img src="/zi/y1.png" width="30px" height="28px"/>': '液',
            '<img src="/zi/r2.png" width="30px" height="28px"/>': '乳',
            '<img src="/zi/j4.png" width="30px" height="28px"/>': '鸡',
            '<img src="/zi/t1.png" width="30px" height="28px"/>': '头',
            '<img src="/zi/r1.png" width="30px" height="28px"/>': '肉',
            '<img src="/zi/b4.png" width="30px" height="28px"/>': '棒',
            '<img src="/zi/g2.png" width="30px" height="28px"/>': '龟',
            '<img src="/zi/c2.png" width="30px" height="28px"/>': '操',
            '<img src="/zi/c4.png" width="30px" height="28px"/>': '肏',
            '<img src="/zi/g1.png" width="30px" height="28px"/>': '肛',
            '<img src="/zi/c3.png" width="30px" height="28px"/>': '插',
            '<img src="/zi/y2.png" width="30px" height="28px"/>': '淫',
            '<img src="/zi/x1.png" width="30px" height="28px"/>': '穴',
            '<img src="/zi/b2.png" width="30px" height="28px"/>': '暴',
            '<img src="/zi/b3.png" width="30px" height="28px"/>': '屄',
            '<img src="/zi/d3.png" width="30px" height="28px"/>': '洞',
            '<img src="/zi/x2.png" width="30px" height="28px"/>': '性',
            '<img src="/zi/l3.png" width="30px" height="28px"/>': '乱',
            '<img src="/zi/a1.png" width="30px" height="28px"/>': '爱',
            '<img src="/zi/j3.png" width="30px" height="28px"/>': '交',
            '<img src="/zi/p1.png" width="30px" height="28px"/>': '喷',
            '<img src="/zi/c5.png" width="30px" height="28px"/>': '潮',
            '<img src="/zi/b1.png" width="30px" height="28px"/>': '爆',
            '<img src="/zi/f1.png" width="30px" height="28px"/>': '妇',
            '<img src="/zi/j2.png" width="30px" height="28px"/>': '奸',
            '<img src="/zi/n3.png" width="30px" height="28px"/>': '嫩',
            '<img src="/zi/l1.png" width="30px" height="28px"/>': '轮',
            '<img src="/zi/d1.png" width="30px" height="28px"/>': '荡',
            '<img src="/zi/l2.png" width="30px" height="28px"/>': '浪',
            '<img src="/zi/c1.png" width="30px" height="28px"/>': '草',
            '<img src="/zi/j5.png" width="30px" height="28px"/>': '妓',
            '<img src="/zi/b5.png" width="30px" height="28px"/>': '逼',
            '<img src="/zi/g3.png" width="30px" height="28px"/>': '干',
            '<img src="/zi/g4.png" width="30px" height="28px"/>': '股',
            '<img src="/zi/s2.png" width="30px" height="28px"/>': '深',
            '<img src="/zi/f2.png" width="30px" height="28px"/>': '粉',
            '<img src="/zi/r4.png" width="30px" height="28px"/>': '入',
            '<img src="/zi/b6.png" width="30px" height="28px"/>': '巴',
            '<img src="/zi/p3.png" width="30px" height="28px"/>': '屁',
            '<img src="/zi/p2.png" width="30px" height="28px"/>': '破',
            '<img src="/zi/l4.png" width="30px" height="28px"/>': '裸',
            '<img src="/zi/t2.png" width="30px" height="28px"/>': '臀',
        }
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配87NB的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/lt/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，适配87NB的特定模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 87NB网站使用内容页内分页模式
        return "内容页内分页"
    
    def _get_content_url(self, content: str) -> Optional[str]:
        """
        从页面内容中提取小说内容页面的URL
        
        Args:
            content: 页面内容
            
        Returns:
            内容页面URL或None
        """
        import re
        
        # 查找"开始阅读"链接
        pattern = r'<a href="(/ltxs/\d+/\d+\.html)"[^>]*>开始阅读</a>'
        match = re.search(pattern, content)
        
        if match:
            return match.group(1)
        
        return None
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现单章节小说解析逻辑 - 87NB特定实现
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 87NB特殊处理：需要从"开始阅读"链接获取内容
        content_url = self._get_content_url(content)
        
        if not content_url:
            raise Exception("无法找到内容页面链接")
        
        # 构建完整的内容页面URL
        full_content_url = f"{self.base_url}{content_url}"
        
        # 获取内容页面
        content_page = self._get_url_content(full_content_url)
        
        if not content_page:
            raise Exception("无法获取内容页面")
        
        # 从内容页面提取小说内容
        extracted_content = self._extract_with_regex(content_page, self.content_reg)
        
        if not extracted_content:
            # 尝试备用内容提取模式
            extracted_content = self._extract_content_fallback(content_page)
        
        if not extracted_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(extracted_content)
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [
                {
                    'chapter_number': 1,
                    'title': title,
                    'content': processed_content,
                    'url': full_content_url
                }
            ]
        }
        
        return novel_content
    
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
        # 提取章节链接
        chapter_links = self._extract_chapter_links(content)
        if not chapter_links:
            raise Exception("无法提取章节列表")
        
        print(f"发现 {len(chapter_links)} 个章节")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _extract_chapter_links(self, content: str) -> List[Dict[str, str]]:
        """
        提取章节链接列表 - 87NB特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            章节链接列表
        """
        # 87NB是短篇小说网站，没有章节列表
        return []
    
    def _get_all_chapters(self, chapter_links: List[Dict[str, str]], novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容
        
        Args:
            chapter_links: 章节链接列表
            novel_content: 小说内容字典
        """
        import time
        
        self.chapter_count = 0
        
        for chapter_info in chapter_links:
            self.chapter_count += 1
            chapter_url = chapter_info['url']
            chapter_title = chapter_info['title']
            
            print(f"正在抓取第 {self.chapter_count} 章: {chapter_title}")
            
            # 获取章节内容
            full_url = f"{self.base_url}{chapter_url}"
            chapter_content = self._get_url_content(full_url)
            
            if chapter_content:
                # 使用配置的正则提取内容
                extracted_content = self._extract_with_regex(chapter_content, self.content_reg)
                
                if extracted_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(extracted_content)
                    
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': chapter_title,
                        'content': processed_content,
                        'url': full_url
                    })
                    print(f"√ 第 {self.chapter_count} 章抓取成功")
                else:
                    print(f"× 第 {self.chapter_count} 章内容提取失败")
            else:
                print(f"× 第 {self.chapter_count} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def _replace_special_chars(self, content: str) -> str:
        """
        替换特殊字符 - 87NB特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        # 替换87NB的特殊图片字符
        for old_char, new_char in self.char_replacements.items():
            content = content.replace(old_char, new_char)
        
        return content
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - 87NB特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除87NB常见的广告模式
        ad_patterns = [
            r'<div class="ad".*?</div>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题 - 87NB特定实现
        
        Args:
            content: 页面内容
            
        Returns:
            小说标题
        """
        import re
        
        # 使用配置的正则表达式提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if title:
            return title
        
        # 备用方法：从页面标题中提取
        title_match = re.search(r'<title>(.*?)</title>', content)
        if title_match:
            return title_match.group(1).strip()
        
        return "未知标题"
    
    def _extract_content_fallback(self, content: str) -> Optional[str]:
        """
        备用内容提取方法 - 当主要正则表达式失败时使用
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容或None
        """
        import re
        
        # 备用模式1：查找包含小说内容的div
        patterns = [
            r'<div[^>]*class="content"[^>]*>(.*?)</div>',
            r'<div[^>]*id="content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="article-content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="text"[^>]*>(.*?)</div>',
            r'<div[^>]*class="txt"[^>]*>(.*?)</div>'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)
        
        # 备用模式2：查找包含大量文本的段落
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        if paragraphs:
            # 选择最长的段落作为内容
            longest_paragraph = max(paragraphs, key=len)
            if len(longest_paragraph.strip()) > 100:  # 确保有足够的内容
                return longest_paragraph
        
        return None
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 87NB不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = Nb87Parser()
    
    # 测试单篇小说
    try:
        novel_id = "12345"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")