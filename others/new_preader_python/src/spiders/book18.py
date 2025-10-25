"""
book18.me 小说网站解析器 - https://www.book18.me/
支持单篇（数字ID）和多篇（中文标题）小说的自动爬取
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, quote
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Book18Parser:
    """book18.me 小说解析器"""
    
    name = "book18.me"
    description = "book18.me 小说解析器（支持单篇和多篇）"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
        """
        self.base_url = "https://www.book18.me"
        self.session = requests.Session()
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        self.chapter_count = 0
        
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
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（book18.me不需要列表页解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # book18.me是短篇小说网站，每个小说一个页面，不需要列表解析
        return []
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """获取书籍页面的标题、内容与状态"""
        # 根据ID类型构建URL
        novel_url = self._build_novel_url(novel_id)
        
        content = self._get_url_content(novel_url)
        if not content:
            return None
            
        title = self._extract_title(content)
        
        # 判断是单篇还是多篇
        if self._is_multichapter_novel(content):
            desc = "多章节小说"
            status = "连载中"
        else:
            chapter_content = self._extract_content(content)
            desc = "短篇小说（单页面）"
            status = "已完成"
        
        if not title:
            return None
            
        return {
            "title": title or "未知标题",
            "desc": desc,
            "status": status
        }
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
        Args:
            novel_id: 小说ID（数字ID或中文标题）
            
        Returns:
            小说详情信息
        """
        # 构建完整URL
        novel_url = self._build_novel_url(novel_id)
        
        # 获取小说页面内容
        content = self._get_url_content(novel_url)
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取小说标题
        title = self._extract_title(content)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ]")
        
        # 判断是单篇还是多篇，分别处理
        if self._is_multichapter_novel(content):
            # 多篇书籍：有章节列表
            novel_content = self._parse_multichapter_novel(content, novel_url, title)
        else:
            # 单篇书籍：只有一个页面
            novel_content = self._parse_single_chapter_novel(content, novel_url, title)
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _build_novel_url(self, novel_id: str) -> str:
        """根据小说ID构建URL"""
        # 判断ID类型：数字ID还是中文标题
        if novel_id.isdigit():
            # 数字ID：直接内容详情页
            return f"{self.base_url}/article/{novel_id}"
        else:
            # 中文标题：书籍列表页
            # 对中文标题进行URL编码
            encoded_title = quote(novel_id, safe='')
            return f"{self.base_url}/book/{encoded_title}"
    
    def _is_multichapter_novel(self, html_content: str) -> bool:
        """判断是否为多章节小说"""
        # 检查是否存在章节列表（list-group）
        chapter_list_match = re.search(r'<ul class="list-group">', html_content)
        chapter_items_match = re.search(r'<li class="list-group-item px-2">', html_content)
        
        return bool(chapter_list_match or chapter_items_match)
    
    def _parse_single_chapter_novel(self, html_content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """解析单章节小说"""
        # 提取小说内容
        chapter_content = self._extract_content(html_content)
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 创建小说内容（短篇小说只有一章）
        novel_content = {
            'title': title,
            'author': 'book18',
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': chapter_content,
                'url': novel_url
            }]
        }
        
        return novel_content
    
    def _parse_multichapter_novel(self, html_content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """解析多章节小说"""
        # 提取章节列表
        chapter_links = self._extract_chapter_links(html_content)
        if not chapter_links:
            raise Exception("无法提取章节列表")
        
        print(f"发现 {len(chapter_links)} 个章节")
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': 'book18',
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容
        self._get_all_chapters(chapter_links, novel_content)
        
        return novel_content
    
    def _extract_chapter_links(self, html_content: str) -> List[Dict[str, str]]:
        """提取章节链接列表"""
        chapter_links = []
        
        # 匹配章节链接模式 - 从list-group中提取
        # 匹配 <li class="list-group-item px-2"><a href="/208928" target="_blank"><b class="mr-1">我的妈妈是黑帮大佬</b>(1)作者：遇见春水</a></li>
        pattern = r'<li class="list-group-item px-2">\s*<a href="([^"]+)"[^>]*>\s*<b class="mr-1">[^<]*</b>\(([^)]+)\)[^<]*</a>\s*</li>'
        matches = re.findall(pattern, html_content)
        
        for href, chapter_num in matches:
            # 构建章节标题
            chapter_title = f"第{chapter_num}章"
            chapter_links.append({
                'url': href,
                'title': chapter_title
            })
        
        # 如果上面的模式没有匹配到，尝试更宽松的模式
        if not chapter_links:
            # 匹配所有数字链接
            pattern2 = r'<a href="(/(\d+))"[^>]*>'
            matches2 = re.findall(pattern2, html_content)
            
            for href, chapter_num in matches2:
                chapter_title = f"第{chapter_num}章"
                chapter_links.append({
                    'url': href,
                    'title': chapter_title
                })
        
        return chapter_links
    
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
            
            print(f"正在抓取第 {self.chapter_count} 章: {chapter_title}")
            
            # 获取章节内容
            chapter_content = self._get_chapter_content(chapter_url)
            if chapter_content:
                novel_content['chapters'].append({
                    'chapter_number': self.chapter_count,
                    'title': chapter_title,
                    'content': chapter_content,
                    'url': chapter_url
                })
                print(f"√ 第 {self.chapter_count} 章抓取成功")
            else:
                print(f"× 第 {self.chapter_count} 章抓取失败")
            
            # 章节间延迟
            time.sleep(1)
    
    def _get_chapter_content(self, chapter_url: str, retry_count: int = 0) -> Optional[str]:
        """
        获取章节内容
        
        Args:
            chapter_url: 章节URL
            retry_count: 重试次数
            
        Returns:
            章节内容
        """
        max_retries = 5
        
        try:
            full_url = urljoin(self.base_url, chapter_url)
            content = self._get_url_content(full_url)
            if not content:
                if retry_count < max_retries:
                    wait_time = min(60, 2 ** (retry_count + 1))
                    print(f"网络请求失败，正在重试 [{retry_count + 1}/{max_retries}]，等待{wait_time}秒")
                    time.sleep(wait_time)
                    return self._get_chapter_content(chapter_url, retry_count + 1)
                else:
                    print(f"章节抓取失败（已达最大重试）: {chapter_url}")
                    return None
            
            # 提取章节内容
            chapter_text = self._extract_content(content)
            if chapter_text:
                return chapter_text
            else:
                if retry_count < max_retries:
                    wait_time = min(60, 2 ** (retry_count + 1))
                    print(f"内容匹配失败，正在重试 [{retry_count + 1}/{max_retries}]，等待{wait_time}秒")
                    time.sleep(wait_time)
                    return self._get_chapter_content(chapter_url, retry_count + 1)
                else:
                    print(f"内容匹配失败（已达最大重试）: {chapter_url}")
                    return None
            
        except Exception as e:
            print(f"获取章节内容时出错: {e}")
            if retry_count < max_retries:
                wait_time = min(60, 2 ** (retry_count + 1))
                print(f"正在重试 [{retry_count + 1}/{max_retries}]，等待{wait_time}秒")
                time.sleep(wait_time)
                return self._get_chapter_content(chapter_url, retry_count + 1)
            return None
    
    def _extract_title(self, html_content: str) -> str:
        """提取小说标题"""
        # 首先尝试从页面标题中提取
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.DOTALL)
        if title_match:
            raw_title = title_match.group(1).strip()
            # 清理HTML标签
            cleaned_title = re.sub(r'<[^>]+>', '', raw_title)
            # 移除网站名称
            cleaned_title = re.sub(r' - 色情短篇小说', '', cleaned_title)
            cleaned_title = re.sub(r' - 情色成人小说', '', cleaned_title)
            cleaned_title = re.sub(r' - book18.me', '', cleaned_title)
            if cleaned_title and cleaned_title != "相关搜索":
                return cleaned_title.strip()
        
        # 然后尝试短篇书籍的特定标题格式
        title_match = re.search(r'<h1 class="title py-1">\s*(.*?)\s*</h1>', html_content, re.DOTALL)
        if title_match:
            raw_title = title_match.group(1).strip()
            # 清理HTML标签
            cleaned_title = re.sub(r'<[^>]+>', '', raw_title)
            if cleaned_title and cleaned_title != "相关搜索":
                return cleaned_title.strip()
        
        # 最后尝试普通的h1标签，但排除包含"相关搜索"等无关内容
        h1_matches = re.findall(r'<h1[^>]*>\s*(.*?)\s*</h1>', html_content, re.DOTALL)
        for raw_title in h1_matches:
            cleaned_title = re.sub(r'<[^>]+>', '', raw_title).strip()
            # 排除无关的h1内容
            if cleaned_title and cleaned_title != "相关搜索" and len(cleaned_title) > 2:
                return cleaned_title
        
        return ""
    
    def _extract_content(self, html_content: str) -> str:
        """提取小说内容"""
        # 匹配内容模式 - 从id="content"的div中提取
        pattern = r'<div id="content"[^>]*>(.*?)</div>'
        content_match = re.search(pattern, html_content, re.DOTALL)
        
        if content_match:
            raw_content = content_match.group(1).strip()
            if raw_content:
                # 清理HTML标签，保留段落结构
                return self._clean_html_content(raw_content)
        
        # 备用模式：尝试其他可能的内容容器
        patterns = [
            r'<div class="entry-content"[^>]*>(.*?)</div>',
            r'<div class="post-body"[^>]*>(.*?)</div>'
        ]
        
        for pattern in patterns:
            content_match = re.search(pattern, html_content, re.DOTALL)
            if content_match:
                raw_content = content_match.group(1).strip()
                if raw_content:
                    return self._clean_html_content(raw_content)
        
        return ""
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """从URL中提取小说ID"""
        # 从类似 https://www.book18.me/article/60569 的URL中提取ID
        import re
        id_match = re.search(r'/article/(\d+)', url)
        if id_match:
            return id_match.group(1)
        
        # 从书籍列表页URL中提取标题
        title_match = re.search(r'/book/([^/]+)', url)
        if title_match:
            import urllib.parse
            return urllib.parse.unquote(title_match.group(1))
        
        # 备用方法：从URL中提取文件名部分作为ID
        import os
        filename = os.path.basename(url)
        return filename or "unknown"
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容，移除标签并保留文本内容
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            清理后的文本内容
        """
        # 移除HTML标签
        cleaned_content = re.sub(r'<[^>]+>', '', html_content)
        
        # 清理多余的空格和换行
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content)
        
        # 清理特殊字符
        cleaned_content = cleaned_content.replace('&nbsp;', ' ')
        cleaned_content = cleaned_content.replace('&amp;', '&')
        cleaned_content = cleaned_content.replace('&lt;', '<')
        cleaned_content = cleaned_content.replace('&gt;', '>')
        cleaned_content = cleaned_content.replace('&quot;', '"')
        cleaned_content = cleaned_content.replace('&#39;', "'")
        
        # 恢复段落结构：将连续的多个空格替换为换行
        cleaned_content = re.sub(r'\s{2,}', '\n\n', cleaned_content)
        
        return cleaned_content.strip()
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        """
        获取URL内容
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容
        """
        retry_count = 0
        
        # 根据代理配置决定是否使用代理
        proxies = None
        if self.proxy_config.get('enabled') and self.proxy_config.get('proxy_url'):
            proxies = {
                'http': self.proxy_config['proxy_url'],
                'https': self.proxy_config['proxy_url']
            }
        
        while retry_count < max_retries:
            try:
                response = self.session.get(url, timeout=60, proxies=proxies)
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response.text
                else:
                    print(f"HTTP错误: {response.status_code} - {url}")
            except Exception as e:
                print(f"请求失败: {e} - {url}")
            
            retry_count += 1
            if retry_count < max_retries:
                wait_time = min(60, 2 ** retry_count)
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        print(f"达到最大重试次数({max_retries})，放弃请求: {url}")
        return None
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        将小说内容保存到文件
        
        Args:
            novel_content: 小说内容
            storage_folder: 存储文件夹路径
            
        Returns:
            保存的文件路径
        """
        import os
        
        # 确保存储文件夹存在
        os.makedirs(storage_folder, exist_ok=True)
        
        # 生成文件名：小说标题.txt
        filename = f"{novel_content['title']}.txt"
        file_path = os.path.join(storage_folder, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入小说标题
            f.write(f"{novel_content['title']}\n\n")
            
            # 写入所有章节
            for chapter in novel_content['chapters']:
                f.write(f"第 {chapter['chapter_number']} 章: {chapter['title']}\n")
                f.write(f"\t{chapter['content']}\n\n")
        
        print(f"小说已保存到: {file_path}")
        return file_path


# 使用示例
if __name__ == "__main__":
    parser = Book18Parser()
    
    # 示例：抓取单篇小说（数字ID）
    try:
        novel_id = "60569"  # 单篇示例
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"单篇小说已保存到: {file_path}")
    except Exception as e:
        print(f"单篇抓取失败: {e}")
    
    # 示例：抓取多篇小说（中文标题）
    try:
        novel_id = "我的妈妈是黑帮大佬"  # 多篇示例
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"多篇小说已保存到: {file_path}")
    except Exception as e:
        print(f"多篇抓取失败: {e}")