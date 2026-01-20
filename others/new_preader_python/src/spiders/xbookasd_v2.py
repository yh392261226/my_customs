"""
xbookasd.top 解析器
网站: https://xbookasd.top/
特点: 多章节小说，需要解析章节列表和每章内容
基于配置驱动版本，遵循多章节解析器格式
"""

from src.utils.logger import get_logger
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class XbookasdParser(BaseParser):
    """xbookasd.top 解析器 - 配置驱动版本"""
    
    # 网站使用GBK编码
    encoding = "gbk"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "xbookasd.top"
    description = "xbookasd.top 多章节小说解析器"
    base_url = "https://xbookasd.top"
    
    # 正则表达式配置 - 章节列表页
    title_reg = [
        r'<h1[^>]*class="dx-title font-semibold mb-1"[^>]*>(.*?)</h1>',
        r'<h1[^>]*class="dx-title[^>]*>(.*?)</h1>',
        r'<h2[^>]*class="dx-title font-semibold mb-1"[^>]*>(.*?)</h2>',
        r'<h2[^>]*class="dx-title[^>]*>(.*?)</h2>',
        r'<title>(.*?)</title>'
    ]
    
    # 章节列表正则
    chapter_link_reg = [
        r'<li><a[^>]*class="block dx-hairline--bottom py-1\.5 mb-1\.5"[^>]*href="([^"]*?)"[^>]*>(.*?)</a></li>',
        r'<a[^>]*href="([^"]*?)"[^>]*rel="external nofollow noopener noreferrer"[^>]*>(.*?)</a>',
        r'<a[^>]*href="([^"]*?)"[^>]*>(.*?)</a>'
    ]
    
    # 状态提取 - 从标签列表中提取
    status_reg = [
        r'<a[^>]*class="flex-1 py-2 px-4 rounded bg-base11 text-primary link"[^>]*href="[^"]*?tag=([^"]*?)"[^>]*>(.*?)</a>',
        r'<a[^>]*href="[^"]*?tag=([^"]*?)"[^>]*>(.*?)</a>'
    ]
    
    # 简介提取
    description_reg = [
        r'<div[^>]*class="bg-base10[^>]*mb-3[^>]*p-2.5[^>]*md:p-5[^>]*rounded-sm[^>]*dx-text">(.*?)</div>',
        r'<meta[^>]*name="description"[^>]*content="([^"]*?)"'
    ]
    
    # 内容页正则 - 章节内容
    content_reg = [
        r'<article[^>]*class="text-xl whitespace-pre-line"[^>]*>(.*?)</article>',
        r'<article[^>]*class="text-xl[^>]*>(.*?)</article>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="novel-content"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    # 书籍类型配置
    book_type = ["多章节"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配xbookasd.top的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        if novel_id.isdigit():
            # 如果书籍ID是整形则返回下面的连接地址 
            return f"{self.base_url}/?novel/detail/{novel_id}"
        else:
            # 如果书籍ID是字符串则返回下面的连接地址
            return f"{self.base_url}/?view_novel/{novel_id}"
    
    def get_chapter_url(self, chapter_url: str) -> str:
        """
        构建完整的章节URL
        
        Args:
            chapter_url: 相对章节URL
            
        Returns:
            完整的章节URL
        """
        if chapter_url.startswith('http'):
            return chapter_url
        
        # 章节链接已经是相对路径格式，可以直接使用
        # 格式: ?view_read/xDbbQjododulv7dg
        return f"{self.base_url}{chapter_url}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，xbookasd.top是多章节小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "多章节"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - xbookasd.top不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        实现多章节小说解析逻辑
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 提取书籍信息
        novel_info = {
            "title": title,
            "url": novel_url,
            "chapters": [],
            "status": "",
            "description": ""
        }
        
        # 提取简介
        description_match = re.search(self.description_reg[0], content, re.DOTALL)
        if description_match:
            novel_info["description"] = description_match.group(1).strip()
        
        # 提取状态标签
        status_tags = []
        for status_pattern in self.status_reg:
            matches = re.finditer(status_pattern, content)
            for match in matches:
                # 提取标签文字
                tag_text = match.group(2).strip() if match.group(2) else match.group(1).strip()
                if tag_text and tag_text not in status_tags:
                    status_tags.append(tag_text)
        
        if status_tags:
            novel_info["status"] = ", ".join(status_tags)
        
        # 提取章节列表
        chapters = self._extract_chapters(content)
        
        # 实际爬取每个章节的内容
        for i, chapter in enumerate(chapters, 1):
            logger.info(f"正在爬取第 {i}/{len(chapters if "chapters_info" in content else chapters_info)} 章: {chapter["title"]}")
            
            # 构建完整的章节URL
            chapter_url = self.get_chapter_url(chapter['url'])
            
            # 爬取章节内容
            chapter_content = self.parse_chapter_content(chapter_url)
            
            if chapter_content and chapter_content != "获取章节内容失败" and chapter_content != "未找到章节内容":
                novel_info["chapters"].append({
                    "title": chapter["title"],
                    "url": chapter_url,
                    "order": chapter["order"],
                    "content": chapter_content
                })
                logger.info(f"✓ 第 {i}/{len(chapters)} 章爬取成功")
            else:
                logger.warning(f"✗ 第 {i}/{len(chapters)} 章爬取失败")
                # 即使失败也添加章节信息，但内容为空
                novel_info["chapters"].append({
                    "title": chapter["title"],
                    "url": chapter_url,
                    "order": chapter["order"],
                    "content": ""
                })
            
            # 章节间延迟
            import time
            time.sleep(1)
        
        return novel_info
    
    def _extract_chapters(self, content: str) -> List[Dict[str, Any]]:
        """
        从章节列表页面提取章节信息
        
        Args:
            content: 章节列表页面内容
            
        Returns:
            章节信息列表
        """
        chapters = []
        
        # 查找章节列表区域
        chapter_list_match = re.search(r'<ul[^>]*class="text-base13 dx-small-title"[^>]*>(.*?)</ul>', content, re.DOTALL)
        if not chapter_list_match:
            return chapters
        
        chapter_list_content = chapter_list_match.group(1)
        
        # 使用集合来避免重复章节
        seen_urls = set()
        
        # 提取章节链接和标题
        for chapter_pattern in self.chapter_link_reg:
            matches = re.finditer(chapter_pattern, chapter_list_content)
            for match in matches:
                chapter_url = match.group(1).strip()
                chapter_title = match.group(2).strip()
                
                # 清理章节标题
                chapter_title = re.sub(r'\s+new\s*$', '', chapter_title)  # 移除new标记
                chapter_title = re.sub(r'\s+', ' ', chapter_title).strip()  # 清理多余空白
                
                # 检查是否已经处理过这个URL，避免重复
                if chapter_url not in seen_urls:
                    seen_urls.add(chapter_url)
                    chapters.append({
                        "title": chapter_title,
                        "url": chapter_url,
                        "order": len(chapters) + 1
                    })
        
        return chapters
    
    def parse_chapter_content(self, chapter_url: str) -> str:
        """
        解析章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容文本
        """
        try:
            # 获取章节页面内容
            content = self._get_url_content(chapter_url)
            if not content:
                return "获取章节内容失败"
            
            # 提取内容
            for content_pattern in self.content_reg:
                match = re.search(content_pattern, content, re.DOTALL)
                if match:
                    chapter_content = match.group(1)
                    # 清理HTML标签
                    chapter_content = re.sub(r'<[^>]+>', '', chapter_content)
                    chapter_content = re.sub(r'\s+', ' ', chapter_content).strip()
                    return chapter_content
            
            return "未找到章节内容"
            
        except Exception as e:
            return f"解析章节内容失败: {str(e)}"
    
    def _clean_html_content(self, content: str) -> str:
        """
        重写HTML内容清理方法，适配xbookasd.top的特殊格式
        
        Args:
            content: 原始HTML内容
            
        Returns:
            清理后的文本内容
        """
        # 先调用父类的清理方法
        content = super()._clean_html_content(content)
        
        # 移除HTML实体编码
        import html
        content = html.unescape(content)
        
        # 移除多余的空白字符
        content = ' '.join(content.split())
        
        return content.strip()


# 使用示例
if __name__ == "__main__":
    parser = XbookasdParser()
    
    # 测试多章节小说
    try:
        novel_id = "ambmwnKgMYHR1Z"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")