"""
夜色书阁 (yssg2.cfd) 小说网站解析器
基于配置驱动版本，遵循txtxi_v2.py格式
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class YssgParser(BaseParser):
    """夜色书阁解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "夜色书阁"
    description = "夜色书阁短篇小说解析器"
    base_url = "http://5l15cquy.yssg2.cfd"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="title animated slideInLeft"[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*class="content"[^>]*id="Content-Box"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配夜色书阁的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/index.php/art/detail/id/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，夜色书阁是短篇小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - 夜色书阁不需要多章节解析
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 夜色书阁是短篇小说网站，直接使用单章节解析
        return self._parse_single_chapter_novel(content, novel_url, title)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 夜色书阁不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = YssgParser()
    
    # 测试单篇小说
    try:
        novel_id = "124230"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")