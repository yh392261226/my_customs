"""
69hnovel.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class H69NovelParser(BaseParser):
    """69hnovel.com 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "69hnovel.com"
    description = "69hnovel.com 小说解析器"
    base_url = "https://www.69hnovel.com"
    
    # 正则表达式配置
    title_reg = [
        r'<h1 class="title">\s*(.*?)\s*</h1>',
        r'<title>(.*?)</title>'
    ]
    
    content_reg = [
        r'<article class="novel-content">(.*?)</article>',
        r'<div[^>]*?class=["\']novel-content["\'][^>]*?>(.*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_editor_special_chars",  # 移除编辑器特殊字符
        "_remove_table_content",  # 移除表格内容
        "_remove_ads"  # 广告移除
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配69hnovel.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/erotic-novel/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，适配69hnovel.com的特定模式
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        # 69hnovel.com主要是单篇书籍
        return "短篇"
    
    def _remove_editor_special_chars(self, content: str) -> str:
        """
        移除编辑器特殊字符 - 69hnovel.com特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除编辑器转换的特殊字符
        special_chars = {
            '&hellip;': '...',
            '&rdquo;': '"',
            '&nbsp;': ' ',
            '&ldquo;': '"',
            '&mdash;': '—',
            '&ndash;': '–',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            "&rsquo;": "’",
            "&lsquo;": "‘"
        }
        
        # 替换特殊字符
        for char, replacement in special_chars.items():
            content = content.replace(char, replacement)
        
        return content
    
    def _remove_table_content(self, content: str) -> str:
        """
        移除表格内容 - 69hnovel.com特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除所有<table>到</table>之间的内容
        content = re.sub(r'<table[^>]*>.*?</table>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除可能遗漏的表格相关标签
        table_patterns = [
            r'<thead>.*?</thead>',
            r'<tbody>.*?</tbody>',
            r'<tfoot>.*?</tfoot>',
            r'<tr>.*?</tr>',
            r'<th>.*?</th>',
            r'<td>.*?</td>'
        ]
        
        for pattern in table_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - 69hnovel.com特有处理
        
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
            r'广告.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 69hnovel.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # 69hnovel.com是短篇小说网站，每个小说一个页面，不需要列表解析
        return []


# 使用示例
if __name__ == "__main__":
    parser = H69NovelParser()
    
    # 测试单篇小说
    try:
        novel_id = "13900"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"单篇小说已保存到: {file_path}")
    except Exception as e:
        print(f"单篇抓取失败: {e}")