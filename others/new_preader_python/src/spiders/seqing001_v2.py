"""
seqing001.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class Seqing001Parser(BaseParser):
    """seqing001.com 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "seqing001.com"
    description = "seqing001.com 小说解析器"
    base_url = "https://seqing001.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1 class="post-title item fn" itemprop="name">\s*(.*?)\s*</h1>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<div class="post-content description " itemprop="articleBody">(.*?)</div>\s*</div>\s*</div>',
        r'<div[^>]*?class=["\']post-content description["\'][^>]*?>(.*?)</div>\s*</div>\s*</div>',
        r'<div[^>]*?class=["\']post-content["\'][^>]*?>(.*?)</div>\s*</div>\s*</div>',
        r'<div class="post-content description " itemprop="articleBody">(.*?)</div>',
        r'<div[^>]*?class=["\']post-content description["\'][^>]*?>(.*?)</div>',
        r'<div[^>]*?class=["\']post-content["\'][^>]*?>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_remove_all_html_tags",  # 移除所有HTML标签
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_ads"  # 广告移除
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配seqing001.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/?p={novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，适配seqing001.com的特定模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # seqing001.com主要是单篇书籍
        return "短篇"
    
    def _remove_all_html_tags(self, content: str) -> str:
        """
        移除所有HTML标签 - seqing001.com特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的纯文本内容
        """
        import re
        
        # 首先移除script和style标签及其内容
        content = re.sub(r'<section[^>]*>.*?.*?</section>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<a[^>]*>.*?.*?</a>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<div[^>]*>.*?.*?</div>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除所有HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 替换HTML实体
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            '&hellip;': '...',
            '&mdash;': '—',
            '&ndash;': '–',
            '&ldquo;': '"',
            '&rdquo;': '"',
            '&lsquo;': "'",
            '&rsquo;': "'"
        }
        
        for entity, replacement in html_entities.items():
            content = content.replace(entity, replacement)
        
        # 清理多余空白字符
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        return content
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - seqing001.com特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除常见的广告模式
        ad_patterns = [
            r'<div class="ad".*?</div>',
            r'<div class="ads".*?</div>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容',
            r'广告.*?内容',
            r'相关推荐',
            r'热门文章',
            r'你可能喜欢'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - seqing001.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # seqing001.com是短篇小说网站，每个小说一个页面，不需要列表解析
        return []


# 使用示例
if __name__ == "__main__":
    parser = Seqing001Parser()
    
    # 测试单篇小说
    try:
        novel_id = "6079"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"单篇小说已保存到: {file_path}")
    except Exception as e:
        print(f"单篇抓取失败: {e}")