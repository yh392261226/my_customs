"""
狐狸小说网解析器
网站: https://a.huli1.cfd
特点: 短篇小说，单章节，无需分页
基于配置驱动版本，遵循txtxi_v2.py格式
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class HuliParser(BaseParser):
    """狐狸小说网解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "狐狸小说网"
    description = "狐狸小说网短篇小说解析器"
    base_url = "https://kkk.huli1.lat" #"https://a.huli1.cfd"
    
    # 正则表达式配置
    title_reg = [
        r'<title>(.*?)</title>',
        r'<h1[^>]*class="title font-weight-bold mb-3"[^>]*>\s*<a[^>]*>(.*?)</a>',
        r'<h1[^>]*class="title[^>]*>\s*<a[^>]*>(.*?)</a>'
    ]
    
    content_reg = [
        r'<div[^>]*class="thread-content message break-all"[^>]*>(.*?)</div>',
        r'<div[^>]*class="thread-content[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    status_reg = [
        r'<span[^>]*class="mr-2"[^>]*><i[^>]*class="icon-book"[^>]*></i><a[^>]*class="comment_a"[^>]*>(.*?)</a>',
        r'<span[^>]*><i[^>]*class="icon-book"[^>]*></i><a[^>]*class="comment_a"[^>]*>(.*?)</a>'
    ]
    
    # 书籍类型配置
    book_type = ["短篇"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配狐狸小说网的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/xs/{novel_id}.htm"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，狐狸小说网是短篇小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - 狐狸小说网不需要多章节解析
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 狐狸小说网是短篇小说网站，直接使用单章节解析
        return self._parse_single_chapter_novel(content, novel_url, title)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 狐狸小说网不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _clean_html_content(self, content: str) -> str:
        """
        重写HTML内容清理方法，适配狐狸小说网的特殊格式
        
        Args:
            content: 原始HTML内容
            
        Returns:
            清理后的文本内容
        """
        # 先调用父类的清理方法
        content = super()._clean_html_content(content)
        
        # 狐狸小说网特有的清理逻辑
        # 移除HTML实体编码
        import html
        content = html.unescape(content)
        
        # 移除多余的空白字符
        content = ' '.join(content.split())
        
        return content.strip()


# 使用示例
if __name__ == "__main__":
    parser = HuliParser()
    
    # 测试单篇小说
    try:
        novel_id = "199130"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        self.logger.error(f"抓取失败: {e}")