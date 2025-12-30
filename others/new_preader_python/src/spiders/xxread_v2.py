"""
xxread.net 小说网站解析器
基于配置驱动版本，遵循txtxi_v2.py格式
特殊说明：xxread.net使用JSON API接口，需要特殊处理
"""

import json
import base64
from typing import Dict, List, Optional, Any
from .base_parser_v2 import BaseParser


class XxreadParser(BaseParser):
    """xxread.net 小说网站解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, str]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        # 设置JSON请求头
        self.session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest'
        })
    
    # 基本信息
    name: str = "xxread.net"
    description: str = "xxread.net 小说解析器"
    base_url: str = "https://xxread.net"
    
    # 正则表达式配置（用于HTML页面解析）
    title_reg: List[str] = [
        r'<title[^>]*>(.*?)</title>'
    ]
    
    content_reg: List[str] = [
        r'<div[^>]*class="content"[^>]*>(.*?)</div>'
    ]
    
    status_reg: List[str] = [
        r'<span[^>]*class="chapters"[^>]*>(.*?)</span>',
        r'<span[^>]*class="words"[^>]*>(.*?)</span>'
    ]
    
    description_reg: List[str] = [
        r'<meta[^>]*name="description"[^>]*content="([^"]*)"[^>]*>'
    ]
    
    # 处理函数配置
    after_crawler_func: List[str] = [
        "_clean_css_and_hidden_content"  # 自定义CSS和隐藏内容清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配xxread.net的章节列表API
        
        Args:
            novel_id: 小说ID
            
        Returns:
            章节列表API URL
        """
        return f"{self.base_url}/newBookReader.php?operation=info&sourceUuid={novel_id}"
    
    def _get_chapter_content(self, novel_id: str, chapter_id: str) -> str:
        """
        获取章节内容
        
        Args:
            novel_id: 小说ID
            chapter_id: 章节ID
            
        Returns:
            章节内容文本
        """
        content_url = f"{self.base_url}/getArticleContent.php?sourceUuid={novel_id}&articleUuid={chapter_id}"
        
        try:
            response = self.session.get(content_url)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('content'):
                # base64 解码
                encoded_content = data['content']
                try:
                    # 尝试base64解码
                    decoded_bytes = base64.b64decode(encoded_content)
                    html_content = decoded_bytes.decode('utf-8')
                    
                    # 清理HTML内容
                    clean_content = self._clean_html_content(html_content)
                    return clean_content
                    
                except Exception as decode_error:
                    # 如果解码失败，尝试直接清理
                    return self._clean_html_content(encoded_content)
            
            return ""
            
        except Exception as e:
            return ""
    
    def _get_novel_info_from_html(self, novel_id: str) -> Dict[str, str]:
        """
        从HTML页面获取小说信息（标题、状态、简介等）
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说信息字典
        """
        catalog_url = f"{self.base_url}/newBookReader.php?operation=catalog&sourceUuid={novel_id}"
        
        try:
            response = self.session.get(catalog_url)
            response.raise_for_status()
            html_content = response.text
            
            # 提取标题（从<h2 class="title">标签）
            title = self._extract_with_regex(html_content, [r'<h2[^>]*class="title"[^>]*>(.*?)</h2>'])
            
            # 提取状态信息
            chapters_status = self._extract_with_regex(html_content, [r'<span[^>]*class="chapters"[^>]*>(.*?)</span>'])
            words_status = self._extract_with_regex(html_content, [r'<span[^>]*class="words"[^>]*>(.*?)</span>'])
            
            # 提取简介
            description = self._extract_with_regex(html_content, self.description_reg)
            
            # 构建状态信息
            status = ""
            if chapters_status:
                status += chapters_status + " "
            if words_status:
                status += words_status
            
            return {
                'title': title or "",
                'status': status.strip(),
                'description': description or ""
            }
            
        except Exception as e:
            return {'title': '', 'status': '', 'description': ''}
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，适配xxread.net的特殊结构
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        # 获取章节列表JSON
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        try:
            # 解析JSON响应
            data = json.loads(content)
            catalog = data.get('catalog', [])
            
            if not catalog:
                raise Exception("未获取到章节列表")
            
            # 从HTML页面获取标题和额外信息
            novel_info = self._get_novel_info_from_html(novel_id)
            
            # 优先使用HTML页面中的标题，如果为空则使用JSON中的标题
            title = novel_info.get('title', '')
            if not title:
                if len(catalog) > 0:
                    title = catalog[0].get('title', '未知标题')
                else:
                    title = data.get('title', '未知标题')
            
            # 解析章节内容
            novel_content = []
            
            # catalog[0]是书籍信息，从catalog[1]开始是章节
            for i, chapter in enumerate(catalog[1:], 1):
                if not isinstance(chapter, dict):
                    continue
                    
                chapter_id = chapter.get('uuid', '')
                chapter_title = chapter.get('title', f'第{i}章')
                
                if chapter_id:
                    # 获取章节内容
                    chapter_content = self._get_chapter_content(novel_id, chapter_id)
                    
                    novel_content.append({
                        'chapter_number': i,
                        'title': chapter_title,
                        'content': chapter_content,
                        'url': f"{self.base_url}/getArticleContent.php?sourceUuid={novel_id}&articleUuid={chapter_id}"
                    })
            
            # 返回标准格式的小说详情
            return {
                'title': title,
                'author': self.novel_site_name or self.name,
                'status': novel_info.get('status', ''),
                'description': novel_info.get('description', ''),
                'novel_id': novel_id,
                'url': novel_url,
                'chapters': novel_content,
                'total_chapters': len(novel_content)
            }
            
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {e}")
        except Exception as e:
            raise Exception(f"解析小说详情失败: {e}")
    
    def _clean_css_and_hidden_content(self, content: str) -> str:
        """
        清理CSS样式和隐藏内容
        处理如 out_cache.aba7eb2504890cc08d {position:absolute;opacity:0;height:0;width:0;overflow:hidden;} 
        和 {diaplay: none;} 这类内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        import re
        
        # 1. 移除CSS样式块（包括out_cache.xxx样式）
        # 匹配类似 out_cache.aba7eb2504890cc08d {position:absolute;opacity:0;height:0;width:0;overflow:hidden;}
        css_patterns = [
            r'out_cache\.[a-zA-Z0-9]+\s*\{[^}]*\}',  # out_cache.xxx样式
            r'\.[a-zA-Z0-9_-]+\s*\{[^}]*display\s*:\s*none[^}]*\}',  # display:none样式
            r'\{[^}]*display\s*:\s*none[^}]*\}',  # {display: none;}
            r'\{[^}]*visibility\s*:\s*hidden[^}]*\}',  # {visibility: hidden;}
            r'\{[^}]*opacity\s*:\s*0[^}]*\}',  # {opacity: 0;}
            r'\{[^}]*position\s*:\s*absolute[^}]*\}',  # {position: absolute;}
            r'\{[^}]*height\s*:\s*0[^}]*\}',  # {height: 0;}
            r'\{[^}]*width\s*:\s*0[^}]*\}',  # {width: 0;}
            r'\{[^}]*overflow\s*:\s*hidden[^}]*\}',  # {overflow: hidden;}
        ]
        
        for pattern in css_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 2. 移除包含特定样式类的标签
        hidden_class_patterns = [
            r'<[^>]*class\s*=\s*"[^"]*out_cache[^"]*"[^>]*>.*?</[^>]*>',  # class包含out_cache的标签
            r'<[^>]*style\s*=\s*"[^"]*display\s*:\s*none[^"]*"[^>]*>.*?</[^>]*>',  # style包含display:none的标签
            r'<[^>]*style\s*=\s*"[^"]*visibility\s*:\s*hidden[^"]*"[^>]*>.*?</[^>]*>',  # style包含visibility:hidden的标签
            r'<[^>]*style\s*=\s*"[^"]*opacity\s*:\s*0[^"]*"[^>]*>.*?</[^>]*>',  # style包含opacity:0的标签
        ]
        
        for pattern in hidden_class_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 3. 移除空标签和多余空白
        content = re.sub(r'<[^>]*>\s*</[^>]*>', '', content)  # 空标签
        content = re.sub(r'\s+', ' ', content)  # 多个空白合并为一个空格
        content = content.strip()
        
        # 4. 最后使用基类的HTML清理方法
        return super()._clean_html_content(content)

    def parse_novel_list(self, url: str) -> List[Dict[str, str]]:
        """
        解析小说列表页 - xxread.net不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = XxreadParser()
    
    # 测试单篇小说
    try:
        novel_id = "3981"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
        print(f"小说标题: {novel_content.get('title')}")
        print(f"章节数量: {len(novel_content.get('chapters', []))}")
    except Exception as e:
        print(f"抓取失败: {e}")