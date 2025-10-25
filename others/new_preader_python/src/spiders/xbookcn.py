"""
xbookcn.com 小说网站解析器 - https://blog.xbookcn.com
支持单篇小说的自动爬取
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

class XBookCnParser:
    """xbookcn.com 小说网站解析器"""
    
    name = "xbookcn.com"
    description = "xbookcn.com 小说网站解析器"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
        """
        self.base_url = "https://blog.xbookcn.com"
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
        解析小说列表页（xbookcn.com 不需要列表页解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # xbookcn.com 直接通过书籍ID抓取单篇，不需要列表解析
        return []
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """获取书籍首页的标题、简介与状态"""
        if not novel_id:
            return None
        
        # 构建书籍详情页URL
        novel_url = f"{self.base_url}/{novel_id}.html"
        content = self._get_url_content(novel_url)
        if not content:
            return None
        
        # 提取小说标题
        title_match = re.search(r"<h3 class='post-title entry-title' itemprop='name'>\\s*(.*?)\\s*</h3>", content)
        title = title_match.group(1).strip() if title_match else ""
        
        # 提取小说内容（作为简介）
        content_match = re.search(r"<div class='post-body entry-content'[^>]*>(.*?)</div>", content, re.DOTALL)
        desc = ""
        if content_match:
            raw_content = content_match.group(1)
            # 清理HTML标签
            desc = self._clean_content(raw_content)
            # 取前200字符作为简介
            desc = desc[:200] + "..." if len(desc) > 200 else desc
        
        # 获取分类信息作为状态
        status = "短篇小说"  # xbookcn.com 主要是短篇小说
        
        if not title and not desc:
            return None
        return {"title": title, "desc": desc, "status": status}
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
        Args:
            novel_id: 书籍ID（URL中的路径部分，如2022/02/blog-post_70）
            
        Returns:
            小说详情信息
        """
        if not novel_id:
            raise ValueError("书籍ID不能为空")
        
        # 构建书籍详情页URL
        novel_url = f"{self.base_url}/{novel_id}.html"
        
        # 获取书籍详情页内容
        content = self._get_url_content(novel_url)
        if not content:
            raise Exception(f"无法获取书籍详情页: {novel_url}")
        
        # 提取小说标题
        title_match = re.search(r"<h3 class='post-title entry-title' itemprop='name'>(.*?)</h3>", content)
        if not title_match:
            # 尝试从title标签提取
            title_match = re.search(r"<title>(.*?)-[^-]+</title>", content)
        
        if not title_match:
            raise Exception("无法提取小说标题")
        
        title = title_match.group(1).strip()
        print(f"开始处理 [ {title} ]")

        # 提取小说内容
        content_match = re.search(r"<div class='post-body entry-content'[^>]*>(.*?)</div>", content, re.DOTALL)
        if not content_match:
            raise Exception("无法提取小说内容")
        
        # 清理内容
        novel_text = self._clean_content(content_match.group(1))
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': '未知作者',
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': novel_text,
                'url': novel_url
            }]
        }
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _clean_content(self, raw_content: str) -> str:
        """
        清理小说内容
        
        Args:
            raw_content: 原始HTML内容
            
        Returns:
            清理后的纯文本内容
        """
        # 去除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', raw_content)
        # 去除\n \t 等标签
        clean_text = re.sub(r'\\n', '', clean_text)
        clean_text = re.sub(r'\\t', '', clean_text)
        
        # 处理HTML实体（如&#65306;等）
        import html
        clean_text = html.unescape(clean_text)
        
        # 去除多余的空格和换行
        clean_text = re.sub(r'\\s+', ' ', clean_text)
        
        # 去除开头和结尾的空格
        clean_text = clean_text.strip()
        
        return clean_text
    
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
            f.write(f"{novel_content['title']}\\n\\n")
            
            # 写入所有章节
            for chapter in novel_content['chapters']:
                f.write(f"{chapter['title']}\\n")
                f.write(f"\\t{chapter['content']}\\n\\n")
        
        print(f"小说已保存到: {file_path}")
        return file_path


# 使用示例
if __name__ == "__main__":
    parser = XBookCnParser()
    
    # 示例：抓取书籍ID为2022/02/blog-post_70的小说
    try:
        novel_content = parser.parse_novel_detail("2022/02/blog-post_70")
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")