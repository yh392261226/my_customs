"""
示例解析器 - 展示如何使用BaseParser基类
"""

from typing import Dict, Any, List, Optional
from .base_parser import BaseParser

class ExampleParser(BaseParser):
    """示例解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    name = "示例解析器"
    description = "示例解析器，展示如何使用BaseParser基类"
    
    def _get_base_url(self) -> str:
        """返回基础URL"""
        return "https://example.com"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # 示例实现：返回空列表，因为大多数网站不需要列表解析
        return []
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        获取书籍首页的标题、简介与状态
        
        Args:
            novel_id: 小说ID
            
        Returns:
            包含标题、简介、状态的字典
        """
        # 构建小说详情页URL
        novel_url = f"{self.base_url}/book/{novel_id}"
        content = self._get_url_content(novel_url)
        if not content:
            return None
        
        # 使用基类提供的默认方法提取标题
        title = self._extract_title(content)
        
        # 自定义内容提取逻辑
        desc = self._extract_description(content)
        status = self._extract_status(content)
        
        if not title and not desc:
            return None
            
        return {
            "title": title or "未知标题",
            "desc": desc or "",
            "status": status or "未知状态"
        }
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        if not novel_id:
            raise ValueError("小说ID不能为空")
        
        # 构建小说详情页URL
        novel_url = f"{self.base_url}/book/{novel_id}"
        content = self._get_url_content(novel_url)
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取小说标题
        title = self._extract_title(content)
        if not title:
            raise Exception("无法提取小说标题")
        
        # 提取章节内容
        chapters = self._extract_chapters(content)
        
        return {
            "title": title,
            "chapters": chapters,
            "chapter_count": len(chapters)
        }
    
    # 自定义提取方法
    def _extract_description(self, content: str) -> str:
        """提取小说简介"""
        # 自定义实现：查找简介相关的HTML元素
        import re
        desc_match = re.search(r'<div[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</div>', content, re.IGNORECASE | re.DOTALL)
        if desc_match:
            return self._clean_content(desc_match.group(1))
        return ""
    
    def _extract_status(self, content: str) -> str:
        """提取小说状态"""
        # 自定义实现：查找状态相关的HTML元素
        import re
        status_match = re.search(r'<span[^>]*class="[^"]*status[^"]*"[^>]*>(.*?)</span>', content, re.IGNORECASE | re.DOTALL)
        if status_match:
            return self._clean_content(status_match.group(1))
        return "连载中"
    
    def _extract_chapters(self, content: str) -> List[Dict[str, str]]:
        """提取章节列表"""
        # 自定义实现：根据网站结构提取章节
        chapters = []
        
        # 示例：假设网站只有一个章节
        chapter_content = self._extract_content(content)
        if chapter_content:
            chapters.append({
                "title": "正文",
                "content": chapter_content
            })
        
        return chapters