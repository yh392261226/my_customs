"""
xhxs2.xyz 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用JSON API接口
"""

from typing import Dict, Any, List, Optional
import json
from .base_parser_v2 import BaseParser

class Xhxs2Parser(BaseParser):
    """xhxs2.xyz 小说解析器 - JSON API版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "泄火小说网"
    description = "xhxs2.xyz 短篇小说解析器"
    base_url = "https://vue.xhxs2.xyz/"
    
    # 正则表达式配置 - 由于是JSON API，不需要HTML正则
    title_reg = []
    content_reg = []
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配xhxs2.xyz的API格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说API URL
        """
        return f"{self.base_url}/vue.php?act=detail&id={novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，xhxs2.xyz是短篇小说网站
        
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
        match = re.search(r'id=(\d+)', url)
        return match.group(1) if match else "unknown"
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，处理JSON格式的API响应
        
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
            
            # 解析JSON响应
            data = json.loads(content)
            
            # 检查detail字段是否存在
            if 'detail' not in data or not isinstance(data['detail'], dict):
                raise ValueError("API响应中没有找到detail字段")
            
            detail = data['detail']
            
            # 获取标题和内容
            title = detail['title'].strip()
            content_html = detail['src'].strip()
            
            if not title:
                raise ValueError("未获取到小说标题")
            
            if not content_html:
                raise ValueError("未获取到小说内容")
            
            # 执行后处理函数清理HTML内容
            content_text = self._clean_html_content(content_html)
            
            # 自动检测书籍类型
            book_type = self._detect_book_type(content_text)
            
            print(f"开始处理 [ {title} ] - 类型: {book_type}")
            
            # 直接返回小说内容（跳过基类的正则提取步骤）
            novel_content = {
                "title": title,
                "author": self.novel_site_name,  # 使用数据库中的网站名称
                "content": content_text,
                "url": novel_url,
                "book_type": book_type,
                "status": "已完成",  # 短篇小说通常已完成
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
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"解析小说详情失败: {e}")
    

    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - xhxs2.xyz不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = Xhxs2Parser()
    
    # 测试单篇小说
    try:
        novel_id = "21234"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")