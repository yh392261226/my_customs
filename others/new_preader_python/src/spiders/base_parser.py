"""
书籍网站解析器公共基类
提供所有解析器共用的基础功能
"""

import re
import time
import requests
import os
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from src.utils.logger import get_logger

logger = get_logger(__name__)

class BaseParser:
    """书籍网站解析器公共基类"""
    
    # 子类必须定义的属性
    name: str = "未知解析器"
    description: str = "未知解析器描述"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
        """
        self.base_url = self._get_base_url()
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
    
    def _get_base_url(self) -> str:
        """获取基础URL，子类可以重写此方法"""
        return ""
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        """
        获取URL内容
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容或None
        """
        proxies = None
        if self.proxy_config.get('enabled', False):
            proxy_url = self.proxy_config.get('proxy_url', '')
            if proxy_url:
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, proxies=proxies, timeout=10)
                if response.status_code == 200:
                    # 检测编码
                    response.encoding = response.apparent_encoding
                    return response.text
                elif response.status_code == 404:
                    logger.warning(f"页面不存在: {url}")
                    return None
                else:
                    logger.warning(f"HTTP {response.status_code} 获取失败: {url}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"第 {attempt + 1} 次请求失败: {url}, 错误: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        logger.error(f"获取URL内容失败: {url}")
        return None
    
    def _clean_content(self, html_content: str) -> str:
        """
        清理HTML内容，提取纯文本
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        # 替换HTML实体
        clean_text = clean_text.replace('&nbsp;', ' ').replace('\xa0', ' ')
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        将小说内容保存到文件
        
        Args:
            novel_content: 小说内容字典
            storage_folder: 存储文件夹
            
        Returns:
            文件路径
        """
        # 确保存储目录存在
        os.makedirs(storage_folder, exist_ok=True)
        
        # 生成文件名（使用标题，避免特殊字符）
        title = novel_content.get('title', '未知标题')
        # 清理文件名中的非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', title)
        file_path = os.path.join(storage_folder, f"{filename}.txt")
        
        # 如果文件已存在，添加序号
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{counter}.txt')
            counter += 1
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write(f"# {title}\n\n")
            
            # 写入章节内容
            chapters = novel_content.get('chapters', [])
            for chapter in chapters:
                chapter_title = chapter.get('title', '未知章节')
                chapter_content = chapter.get('content', '')
                
                f.write(f"## {chapter_title}\n\n")
                f.write(chapter_content)
                f.write("\n\n")
        
        logger.info(f"小说已保存到: {file_path}")
        return file_path
    
    # 抽象方法，子类必须实现
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        raise NotImplementedError("子类必须实现 parse_novel_list 方法")
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        
        Args:
            novel_id: 小说ID
            
        Returns:
            包含标题、简介、状态的字典
        """
        raise NotImplementedError("子类必须实现 get_homepage_meta 方法")
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        raise NotImplementedError("子类必须实现 parse_novel_detail 方法")
    
    # 可选的重写方法
    def _extract_title(self, content: str) -> str:
        """提取小说标题，子类可以重写此方法"""
        # 默认实现：查找h1标签
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
        if title_match:
            return self._clean_content(title_match.group(1))
        return ""
    
    def _extract_content(self, content: str) -> str:
        """提取小说内容，子类可以重写此方法"""
        # 默认实现：查找常见的内容容器
        content_patterns = [
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*entry[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                return self._clean_content(match.group(1))
        
        return ""