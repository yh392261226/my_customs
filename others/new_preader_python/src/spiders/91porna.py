"""
91porna.com 小说网站解析器 - https://91porna.com
短篇小说解析器，每个小说一个页面，无章节列表
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Porna91Parser:
    """91porna.com 小说解析器"""
    
    name = "91porna"
    description = "91porna.com 短篇小说解析器"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
        """
        self.base_url = "https://91porna.com/novels/"
        self.session = requests.Session()
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        
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
        解析小说列表页（91porna.com不需要列表页解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # 91porna.com是短篇小说网站，每个小说一个页面，不需要列表解析
        return []
    
    def get_homepage_meta(self, novel_url: str) -> Optional[Dict[str, str]]:
        """获取书籍页面的标题、内容与状态"""
        if not novel_url.startswith(self.base_url):
            novel_url = urljoin(self.base_url, novel_url)
            
        content = self._get_url_content(novel_url)
        if not content:
            return None
            
        title = self._extract_title(content)
        chapter_content = self._extract_content(content)
        
        if not title and not chapter_content:
            return None
            
        return {
            "title": title or "未知标题",
            "desc": "短篇小说（单页面）",
            "status": "已完成"
        }
    
    def parse_novel_detail(self, novel_url: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
        Args:
            novel_url: 小说页面URL或路径
            
        Returns:
            小说详情信息
        """
        # 构建完整URL
        if not novel_url.startswith('http'):
            novel_url = urljoin(self.base_url, novel_url)
        
        # 获取小说页面内容
        content = self._get_url_content(novel_url)
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取小说标题
        title = self._extract_title(content)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ]")
        
        # 提取小说内容
        chapter_content = self._extract_content(content)
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 创建小说内容（短篇小说只有一章）
        novel_content = {
            'title': title,
            'author': '91porna',
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': chapter_content,
                'url': novel_url
            }]
        }
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _extract_title(self, html_content: str) -> str:
        """提取小说标题"""
        # 匹配 <h1 class="mt-5 mb-4 text-2xl">标题</h1>
        # 考虑多行的情况
        title_match = re.search(r'<h1 class="mt-5 mb-4 text-2xl">\s*(.*?)\s*</h1>', html_content, re.DOTALL)
        if title_match:
            raw_title = title_match.group(1).strip()
            # 清理HTML标签
            return re.sub(r'<[^>]+>', '', raw_title)
        return ""
    
    def _extract_content(self, html_content: str) -> str:
        """提取小说内容"""
        # 匹配 <article style="line-height: 2;" class="markdown-body">内容</article>
        # 支持单引号和双引号
        patterns = [
            r'<article[^>]*?class=["\']markdown-body["\'][^>]*?>(.*?)</article>',
            r'<article[^>]*?class=["\']markdown-body["\'][^>]*?>'
        ]
        
        for pattern in patterns:
            content_match = re.search(pattern, html_content, re.DOTALL)
            if content_match:
                raw_content = content_match.group(1).strip() if content_match.groups() else ""
                if raw_content:
                    # 清理HTML标签，保留段落结构
                    return self._clean_html_content(raw_content)
        return ""
    
    def _extract_novel_id(self, url: str) -> str:
        """从URL中提取小说ID"""
        # 从URL中提取文件名部分作为ID
        import os
        filename = os.path.basename(url)
        if '.' in filename:
            filename = filename.rsplit('.', 1)[0]
        return filename or "unknown"
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """从URL中提取小说ID"""
        # 从类似 https://91porna.com/novels/1891774072 的URL中提取ID
        import re
        id_match = re.search(r'/novels/(\d+)', url)
        if id_match:
            return id_match.group(1)
        return self._extract_novel_id(url)
    
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
            
            # 写入章节内容（短篇小说只有一章）
            for chapter in novel_content['chapters']:
                f.write(f"{chapter['content']}\n\n")
        
        print(f"小说已保存到: {file_path}")
        return file_path


# 使用示例
if __name__ == "__main__":
    parser = Porna91Parser()
    
    # 示例：抓取指定URL的小说
    try:
        novel_url = "https://91porna.com/novels/1891774072"  # 示例URL，使用用户提供的小说ID
        novel_content = parser.parse_novel_detail(novel_url)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")
