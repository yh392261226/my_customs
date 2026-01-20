"""
txtxi.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class TxtxiParser(BaseParser):
    """txtxi.com 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "txtxi.com"
    description = "txtxi.com 短篇小说解析器"
    base_url = "https://www.txtxi.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*class="text"[^>]*style="font-size:22px"[^>]*>(.*?)</div>\s*<div[^>]*vid="[^"]*"[^>]*class="font"[^>]*>',
        r'<div[^>]*class="text"[^>]*style="font-size:22px"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_remove_ads",  # 广告移除
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配txtxi.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，txtxi.com是短篇小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑 - txtxi.com不需要多章节解析
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # txtxi.com是短篇小说网站，直接使用单章节解析
        return self._parse_single_chapter_novel(content, novel_url, title)
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - txtxi.com特有处理
        特别处理嵌入在内容中的广告代码
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 首先移除嵌入在内容中的广告代码
        # 这个广告代码会插入在内容中间导致内容被截断
        ad_patterns = [
            r'<div class="b300"><div id="txtxi_b1" class="h100"></div><div id="txtxi_b2" class="h100"></div><div id="txtxi_b3" class="h100"></div></div>',
            r'<div class="b300">.*?</div>',
            r'<div class="ad".*?</div>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容',
            r'<script.*?</script>',
            r'<style.*?</style>'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - txtxi.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = TxtxiParser()
    
    # 测试单篇小说
    try:
        novel_id = "12345"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")