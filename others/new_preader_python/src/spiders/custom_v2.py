"""
自定义解析器 v2 - 基于配置驱动的重构版本
用于快速创建新的网站解析器
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class CustomParser(BaseParser):
    """自定义解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    name = "自定义网站"
    description = "自定义网站小说解析器"
    base_url = "https://example.com"  # 默认示例URL
    
    # 默认正则表达式配置（用户需要根据具体网站调整）
    title_reg = [
        r'<h1[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>',
        r'<div[^>]*class=["\']title["\'][^>]*>(.*?)</div>'
    ]
    
    content_reg = [
        r'<div[^>]*id=["\']content["\'][^>]*>(.*?)</div>',
        r'<div[^>]*class=["\']content["\'][^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)<',
        r'<span[^>]*class=["\']status["\'][^>]*>(.*?)</span>'
    ]
    
    # 书籍类型配置
    book_type = ["短篇", "多章节", "短篇+多章节"]
    
    # 章节列表正则
    chapter_list_reg = [
        r'<a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>',
        r'<li[^>]*><a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a></li>'
    ]
    
    # 处理函数链
    after_crawler_func = ["_clean_html_tags", "_remove_ads", "_format_content"]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, custom_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化自定义解析器
        
        Args:
            proxy_config: 代理配置
            custom_config: 自定义配置，可以覆盖默认配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 禁用SSL验证以解决SSL错误
        self.session.verify = False
        # 添加User-Agent以绕过反爬虫
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 应用自定义配置
        if custom_config:
            self._apply_custom_config(custom_config)
    
    def _apply_custom_config(self, config: Dict[str, Any]):
        """应用自定义配置"""
        if 'name' in config:
            self.name = config['name']
        if 'description' in config:
            self.description = config['description']
        if 'base_url' in config:
            self.base_url = config['base_url']
        if 'title_reg' in config:
            self.title_reg = config['title_reg']
        if 'content_reg' in config:
            self.content_reg = config['content_reg']
        if 'status_reg' in config:
            self.status_reg = config['status_reg']
        if 'book_type' in config:
            self.book_type = config['book_type']
        if 'chapter_list_reg' in config:
            self.chapter_list_reg = config['chapter_list_reg']
        if 'after_crawler_func' in config:
            self.after_crawler_func = config['after_crawler_func']
    
    def _remove_ads(self, content: str) -> str:
        """
        移除广告内容（通用实现，用户可重写）
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 通用广告移除逻辑
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<iframe[^>]*>.*?</iframe>', '', content, flags=re.DOTALL)
        
        # 移除常见广告类名
        ad_patterns = [
            r'<div[^>]*class=["\']ad["\'][^>]*>.*?</div>',
            r'<div[^>]*id=["\']ad["\'][^>]*>.*?</div>',
            r'<div[^>]*class=["\']ads["\'][^>]*>.*?</div>',
            r'<div[^>]*id=["\']ads["\'][^>]*>.*?</div>'
        ]
        
        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        return content
    
    def _format_content(self, content: str) -> str:
        """
        格式化内容（通用实现，用户可重写）
        
        Args:
            content: 清理后的内容
            
        Returns:
            格式化后的内容
        """
        # 通用格式化逻辑
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'\s{2,}', ' ', content)
        content = re.sub(r'^', '    ', content, flags=re.MULTILINE)
        
        return content
    
    def _detect_book_type(self, novel_id: str) -> str:
        """
        检测书籍类型（通用实现，用户可重写）
        
        Args:
            novel_id: 书籍ID
            
        Returns:
            书籍类型
        """
        try:
            url = f"{self.base_url}/book/{novel_id}.html"
            content = self._get_url_content(url)
            
            # 通用检测逻辑
            if re.search(r'章节列表|目录|章节目录', content):
                return "多章节"
            
            if re.search(r'正文|内容|小说内容', content):
                return "短篇"
            
            return "短篇+多章节"
            
        except Exception:
            return "短篇"  # 默认类型
    
    def configure_for_site(self, site_config: Dict[str, Any]):
        """
        为特定网站配置解析器
        
        Args:
            site_config: 网站配置字典
        """
        self._apply_custom_config(site_config)
    
    def create_site_template(self, site_name: str, site_url: str) -> Dict[str, Any]:
        """
        创建网站配置模板
        
        Args:
            site_name: 网站名称
            site_url: 网站URL
            
        Returns:
            配置模板字典
        """
        return {
            'name': site_name,
            'description': f"{site_name}小说解析器",
            'base_url': site_url,
            'title_reg': self.title_reg,
            'content_reg': self.content_reg,
            'status_reg': self.status_reg,
            'book_type': self.book_type,
            'chapter_list_reg': self.chapter_list_reg,
            'after_crawler_func': self.after_crawler_func
        }
    
    def test_configuration(self, novel_id: str) -> Dict[str, Any]:
        """
        测试当前配置是否有效
        
        Args:
            novel_id: 测试用的书籍ID
            
        Returns:
            测试结果
        """
        result = {
            'success': False,
            'errors': [],
            'extracted_data': {}
        }
        
        try:
            # 测试URL访问
            url = f"{self.base_url}/book/{novel_id}.html"
            content = self._get_url_content(url)
            
            if not content:
                result['errors'].append("无法获取页面内容")
                return result
            
            # 测试标题提取
            title = self._extract_title(content)
            if title:
                result['extracted_data']['title'] = title
            else:
                result['errors'].append("无法提取标题")
            
            # 测试内容提取
            extracted_content = self._extract_content(content)
            if extracted_content:
                result['extracted_data']['content_length'] = len(extracted_content)
            else:
                result['errors'].append("无法提取内容")
            
            # 测试状态提取
            status = self._extract_status(content)
            if status:
                result['extracted_data']['status'] = status
            
            # 测试书籍类型检测
            book_type = self._detect_book_type(novel_id)
            result['extracted_data']['book_type'] = book_type
            
            result['success'] = len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"测试过程中发生错误: {e}")
        
        return result