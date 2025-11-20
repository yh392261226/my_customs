"""
fsnovel.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现

网站结构特点：
- 书籍详情页：https://fsnovel.com/中文名称/
- 中文名称既是书籍ID也是书籍标题
- 文章内容在：<div class="tdb-block-inner td-fix-index"></div>标签中
- 书籍是短篇的，不需要考虑分页
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class FsnovelParser(BaseParser):
    """fsnovel.com 小说解析器 - 配置驱动版本"""
    
    # 基本信息
    name = "fsnovel.com"
    description = "fsnovel.com 小说解析器（短篇）"
    base_url = "https://fsnovel.com"
    
    # 正则表达式配置
    title_reg = [
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>'
    ]
    
    content_reg = [
        r'<div[^>]*class="td_block_wrap tdb_single_content[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div[^>]*class="post-meta"[^>]*>(.*?)</div>',
        r'<span[^>]*class="post-date"[^>]*>(.*?)</span>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_remove_ads"  # 广告移除
    ]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        # 禁用SSL验证以解决SSL错误
        self.session.verify = False
        # 添加User-Agent以绕过反爬虫
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配fsnovel.com的URL格式
        
        Args:
            novel_id: 小说ID（中文名称）
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/{novel_id}/"
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写获取书籍首页元数据方法
        
        Args:
            novel_id: 小说ID（中文名称）
            
        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            return None
        
        # 使用配置的正则提取标题
        title = self._extract_with_regex(content, self.title_reg)
        
        # 使用配置的正则提取状态
        status = self._extract_with_regex(content, self.status_reg)
        
        return {
            "title": title or novel_id,  # 如果提取不到标题，使用中文名称作为标题
            "desc": "短篇小说",
            "status": status or "未知状态"
        }
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，fsnovel.com都是短篇
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容 - fsnovel.com特有处理
        
        Args:
            content: 原始内容
            
        Returns:
            处理后的内容
        """
        import re
        
        # 移除fsnovel.com常见的广告模式
        ad_patterns = [
            r'<div class="ads".*?</div>',
            r'<div class="td-a-rec".*?</div>',
            r'<!--.*?广告.*?-->',
            r'赞助.*?内容'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - fsnovel.com不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = FsnovelParser()
    
    # 测试短篇小说
    try:
        # 中文名称作为小说ID
        novel_id = "测试小说"
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")