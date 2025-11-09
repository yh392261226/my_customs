"""
aaread.cc 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser，支持多章节小说解析
"""

from typing import Dict, Any, List, Optional
import json
import re
from .base_parser_v2 import BaseParser

class AareadParser(BaseParser):
    """aaread.cc 小说解析器 - 多章节版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "aaread.cc"
    description = "aaread.cc 多章节小说解析器"
    base_url = "https://aaread.cc"
    
    # 正则表达式配置
    title_reg = [
        r'<h1>\s*<em>(.*?)</em>',  # 提取小说标题
        r'<title>(.*?)</title>'  # 备用标题提取
    ]
    
    content_reg = [
        r'<p class="intro">(.*?)</p>',  # 小说简介
    ]
    
    status_reg = [
        r'<span class="tag">\s*<i class="blue">(.*?)</i>',  # 状态信息
        r'<span class="tag">(.*?)</span>',  # 备用状态信息
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配aaread.cc的章节列表格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说章节列表页URL
        """
        return f"{self.base_url}/book/{novel_id}#Catalog"
    
    def get_chapter_url(self, novel_id: str, chapter_id: str) -> str:
        """
        获取章节详情API URL
        
        Args:
            novel_id: 小说ID
            chapter_id: 章节ID
            
        Returns:
            章节详情API URL
        """
        return f"https://aaread.cc/ajax/chapter/chapterContent.php?_csrfToken=&bookId={novel_id}&chapterId={chapter_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，aaread.cc是多章节小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "多章节"
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        import re
        match = re.search(r'/book/(\d+)', url)
        return match.group(1) if match else "unknown"
    
    def _extract_chapter_list(self, content: str) -> List[Dict[str, str]]:
        """
        从HTML内容中提取章节列表
        
        Args:
            content: 章节列表页HTML内容
            
        Returns:
            章节列表信息
        """
        chapters = []
        
        # 使用正则表达式提取章节信息
        # 匹配 <div class="volume"> 下的 <ul class="cf"> 中的 <li> 标签
        volume_pattern = r'<div class="volume">.*?<ul class="cf">(.*?)</ul>'
        volume_match = re.search(volume_pattern, content, re.DOTALL)
        
        if volume_match:
            volume_content = volume_match.group(1)
            
            # 提取每个章节的li标签（注意这里没有闭合的</li>标签）
            li_pattern = r'<li data-rid="(\d+)"><a href="/chapter/(\d+)/(\d+)"[^>]*?title="[^"]*?章节字数：(\d+)">([^<]+)</a>'
            matches = re.findall(li_pattern, volume_content)
            
            for match in matches:
                data_rid, book_id, chapter_id, word_count, chapter_title = match
                chapters.append({
                    'data_rid': data_rid,
                    'book_id': book_id,
                    'chapter_id': chapter_id,
                    'chapter_title': chapter_title.strip(),
                    'word_count': int(word_count),
                    'url': f"/chapter/{book_id}/{chapter_id}"
                })
        
        return chapters
    
    def _parse_chapter_content(self, novel_id: str, chapter_id: str) -> Dict[str, Any]:
        """
        解析单个章节内容
        
        Args:
            novel_id: 小说ID
            chapter_id: 章节ID
            
        Returns:
            章节内容信息
        """
        try:
            chapter_url = self.get_chapter_url(novel_id, chapter_id)
            content = self._get_url_content(chapter_url)
            
            if not content:
                raise Exception(f"无法获取章节内容: {chapter_url}")
            
            # 解析JSON响应
            data = json.loads(content)
            
            # 检查data字段是否存在
            if 'data' not in data or not isinstance(data['data'], dict):
                raise ValueError("API响应中没有找到data字段")
            
            data_info = data['data']
            
            # 检查chapterInfo字段是否存在
            if 'chapterInfo' not in data_info or not isinstance(data_info['chapterInfo'], dict):
                raise ValueError("API响应中没有找到chapterInfo字段")
            
            chapter_info = data_info['chapterInfo']
            
            # 获取章节标题和内容
            chapter_title = chapter_info.get('chapterName', '').strip()
            content_html = chapter_info.get('content', '').strip()
            
            if not chapter_title:
                raise ValueError("未获取到章节标题")
            
            if not content_html:
                raise ValueError("未获取到章节内容")
            
            # 执行后处理函数清理HTML内容
            content_text = self._clean_html_content(content_html)
            
            return {
                'chapter_id': chapter_id,
                'chapter_title': chapter_title,
                'content': content_text,
                'url': f"/chapter/{novel_id}/{chapter_id}",
                'word_count': chapter_info.get('wordsCount', 0)
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"章节JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"解析章节内容失败: {e}")
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，处理多章节小说
        
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
            
            # 提取小说简介
            intro = self._extract_with_regex(content, self.content_reg)
            
            # 提取小说状态
            status = self._extract_with_regex(content, self.status_reg)
            
            # 提取章节列表
            chapters_info = self._extract_chapter_list(content)
            if not chapters_info:
                raise ValueError("未获取到章节列表")
            
            print(f"开始处理 [ {title} ] - 找到 {len(chapters_info)} 个章节")
            
            # 解析每个章节内容
            chapters = []
            for i, chapter_info in enumerate(chapters_info):
                try:
                    chapter_content = self._parse_chapter_content(novel_id, chapter_info['chapter_id'])
                    
                    chapters.append({
                        'chapter_number': i + 1,
                        'title': chapter_content['chapter_title'],
                        'content': chapter_content['content'],
                        'url': f"{self.base_url}{chapter_content['url']}",
                        'word_count': chapter_content['word_count']
                    })
                    
                    print(f"章节 {i+1}/{len(chapters_info)}: {chapter_content['chapter_title']} - 完成")
                    
                except Exception as e:
                    print(f"章节 {i+1}/{len(chapters_info)}: 解析失败 - {e}")
                    # 继续处理其他章节，不中断整个流程
                    continue
            
            if not chapters:
                raise ValueError("所有章节解析失败")
            
            # 自动检测书籍类型
            book_type = self._detect_book_type(content)
            
            # 返回小说内容
            novel_content = {
                "title": title,
                "content": "",  # 多章节小说没有统一的内容
                "url": novel_url,
                "book_type": book_type,
                "status": status if status else "连载中",  # 使用提取的状态，如果没有则默认"连载中"
                "intro": intro if intro else "",  # 小说简介
                "chapters": chapters
            }
            
            print(f'[ {title} ] 完成 - 成功解析 {len(chapters)} 个章节')
            return novel_content
            
        except Exception as e:
            raise ValueError(f"解析小说详情失败: {e}")
    
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
        # 创建小说信息字典
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
        
        # 提取章节列表
        chapters = self._extract_chapters(content)
        
        # 实际爬取每个章节的内容
        for i, chapter in enumerate(chapters):
            print(f"正在爬取第 {i+1}/{len(chapters)} 章: {chapter['title']}")
            
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
                print(f"√ 第 {i+1} 章爬取成功")
            else:
                print(f"× 第 {i+1} 章爬取失败")
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
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        重写HTML内容清理方法，专门处理aaread.cc的特定样式和标识符
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的纯文本
        """
        import re
        
        # 首先清理aaread.cc特有的样式和标识符
        
        # 1. 清理display:none样式
        # 移除 <style> .QS6aBnEXOlIs12AvVW9J3BjuW {display:none;}</style> 等类似样式
        html_content = re.sub(r'<style>\s*\.[A-Za-z0-9]+\s*\{[^}]*display\s*:\s*none[^}]*\}\s*</style>', '', html_content)
        
        # 2. 清理特定的标识符标签
        # 移除 <i class='QS6aBnEXOlIs12AvVW9J3BjuW'>feng情 书库</i> 等类似标签
        html_content = re.sub(r"<i\s+class=['\"][A-Za-z0-9]+['\"]>[^<]*</i>", '', html_content)
        
        # 3. 清理其他可能的样式标签
        # 移除任何包含display:none的样式标签
        html_content = re.sub(r'<style[^>]*>[^<]*display\s*:\s*none[^<]*</style>', '', html_content)
        
        # 4. 清理空段落标签
        html_content = re.sub(r'<p>\s*<\\?/p>', '', html_content)
        html_content = re.sub(r'<p>\\r\\s*</p>', '', html_content)
        
        # 5. 清理转义字符
        html_content = html_content.replace('\\r', '').replace('\\n', ' ')
        
        # 6. 调用基类的通用HTML清理方法
        return super()._clean_html_content(html_content)
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - aaread.cc暂时不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = AareadParser()
    
    # 测试单篇小说
    try:
        novel_id = "14"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
        print(f"共解析 {len(novel_content['chapters'])} 个章节")
    except Exception as e:
        print(f"抓取失败: {e}")