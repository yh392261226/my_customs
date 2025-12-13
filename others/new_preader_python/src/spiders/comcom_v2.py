"""
comcom.cyou 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用HTML解析
"""

from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class ComcomParser(BaseParser):
    """comcom.cyou 小说解析器 - HTML解析版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "都市小说网"
    description = "comcom.cyou 短篇小说解析器"
    base_url = "https://comcom.cyou"
    
    # 正则表达式配置
    title_reg = [
        r'<h2>([^<]*)</h2>'
    ]
    
    content_reg = [
        r'<div class="entry">\s*<div>([\s\S]*?)</div>'
    ]
    
    status_reg = [
        r'<span class=\'tags\'>来源：([^<]*)</span>',
        r'<span class="tags">来源：([^<]*)</span>'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配comcom.cyou的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/artdetail-{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，comcom.cyou是短篇小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        import re
        match = re.search(r'artdetail-(\d+)\.html', url)
        return match.group(1) if match else "unknown"
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        重写HTML内容清理方法，专门处理comcom.cyou的特定内容
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        import re
        
        # 清理comcom.cyou特有的内容
        
        # 1. 清理HTML标签
        html_content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html_content)  # 移除script标签
        html_content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html_content)    # 移除style标签
        html_content = re.sub(r'<!--[\s\S]*?-->', '', html_content)                 # 移除注释
        
        # 2. 清理特定的广告和无关内容
        html_content = re.sub(r'<div class="copyright">[\s\S]*?</div>', '', html_content)  # 移除版权信息
        html_content = re.sub(r'<div class="relatedpost">[\s\S]*?</div>', '', html_content)  # 移除相关推荐
        
        # 3. 清理段落标签，保留内容
        html_content = re.sub(r'<p>', '\n', html_content)     # 将<p>标签替换为换行
        html_content = re.sub(r'</p>', '\n', html_content)   # 将</p>标签替换为换行
        
        # 4. 清理其他HTML标签
        html_content = re.sub(r'<[^>]+>', '', html_content)   # 移除所有HTML标签
        
        # 5. 清理空白字符
        html_content = re.sub(r'\s+', ' ', html_content)      # 将多个空白字符合并为一个空格
        html_content = html_content.strip()                   # 去除首尾空白
        
        # 6. 处理章节分隔符
        html_content = re.sub(r'=+', '\n\n', html_content)   # 将多个等号替换为双换行
        
        # 7. 调用基类的通用HTML清理方法
        return super()._clean_html_content(html_content)
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，适配comcom.cyou的HTML结构
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        try:
            novel_url = self.get_novel_url(novel_id)
            content = self._get_url_content(novel_url)
            
            if not content:
                raise Exception(f"无法获取小说页面: {novel_url}")
            
            # 提取小说基本信息
            title = self._extract_with_regex(content, self.title_reg)
            if not title:
                raise ValueError("未获取到小说标题")
            
            # 提取小说内容
            content_html = self._extract_with_regex(content, self.content_reg)
            if not content_html:
                raise ValueError("未获取到小说内容")
            
            # 提取小说状态
            status = self._extract_with_regex(content, self.status_reg)
            
            # 执行后处理函数清理HTML内容
            content_text = self._clean_html_content(content_html)
            
            # 自动检测书籍类型
            book_type = self._detect_book_type(content_text)
            
            print(f"开始处理 [ {title} ] - 类型: {book_type}")
            
            # 返回小说内容
            novel_content = {
                "title": title,
                "author": self.novel_site_name,  # 使用数据库中的网站名称
                "content": content_text,
                "url": novel_url,
                "book_type": book_type,
                "status": status if status else "已完成",  # 短篇小说通常已完成
                "chapters": [
                    {
                        "title": title,
                        "content": content_text,
                        "url": novel_url
                    }
                ]
            }
            
            print(f'[ {title} ] 完成')
            return novel_content
            
        except Exception as e:
            raise ValueError(f"解析小说详情失败: {e}")
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - comcom.cyou不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = ComcomParser()
    
    # 测试单篇小说
    try:
        novel_id = "25437"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")