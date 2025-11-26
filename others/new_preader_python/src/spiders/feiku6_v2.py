"""
飞库中文网 (feiku6.com) 小说网站解析器
基于配置驱动版本，继承自 BaseParser
"""

from typing import Dict, Any, List, Optional
import json
import re
import time
from datetime import datetime
from .base_parser_v2 import BaseParser

class Feiku6Parser(BaseParser):
    """飞库中文网 (feiku6.com) 小说解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 飞库中文网使用UTF-8编码
        self.encoding = 'utf-8'
    
    # 基本信息
    name = "飞库中文网"
    description = "feiku6.com 小说解析器，支持多章节多部小说"
    base_url = "https://www.feiku6.com/"
    
    # 正则表达式配置
    title_reg = [
        r'<h1 class="mb15 lh1d2 oh">([^<]+)</h1>',
        r'<title>([^<]+)_[^<]+</title>',
        r'<meta property="og:novel:book_name" content="([^"]+)"',
        r'<h1[^>]*>([^<]+)</h1>'
    ]
    
    content_reg = [
        r'<div id="TextContent"[^>]*>(.*?)<script src="/scripts/ads/book\.bottom\.js"',
        r'<div id="artWrap"[^>]*>(.*?)</div>',
        r'<div class="read-content[^"]*"[^>]*>(.*?)</div>'
    ]
    
    status_reg = [
        r'<div class="g_col_8 pr">(.*?)</div>',
        r'状态[:：]\s*(.*?)[<\s]',
        r'<meta property="og:novel:status" content="([^"]+)"'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配feiku6.com的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}book/{novel_id}.html"
    
    def get_chapter_list_url(self, novel_id: str) -> str:
        """
        获取章节列表JSON URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            章节列表JSON URL
        """
        current_date = datetime.now().strftime("%Y%m%d")
        return f"{self.base_url}files/book/scripts/{novel_id}/catalog.js?time={current_date}"
    
    def get_chapter_url(self, novel_id: str, chapter_id: str) -> str:
        """
        获取章节详情页URL
        
        Args:
            novel_id: 小说ID
            chapter_id: 章节ID
            
        Returns:
            章节详情页URL
        """
        return f"{self.base_url}read/{novel_id}/{chapter_id}.html"
    

    

    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        import re
        # 匹配 book/小说ID.html 格式
        match = re.search(r'/book/([^/.]+)\.html', url)
        if match:
            return match.group(1)
        
        # 匹配 read/小说ID/章节ID.html 格式
        match = re.search(r'/read/([^/]+)/', url)
        if match:
            return match.group(1)
        
        return "unknown"
    
    def _extract_book_status(self, content: str) -> str:
        """
        从HTML内容中提取书籍状态信息
        
        Args:
            content: 页面HTML内容
            
        Returns:
            书籍状态信息，多个标签用逗号连接
        """
        status_parts = []
        
        # 使用正则表达式提取状态信息
        for pattern in self.status_reg:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                if match and match.strip():
                    # 清理HTML标签和多余空格
                    clean_text = re.sub(r'<[^>]+>', '', match).strip()
                    if clean_text and clean_text not in status_parts:
                        status_parts.append(clean_text)
        
        # 从meta标签获取状态
        meta_match = re.search(r'<meta property="og:novel:status" content="([^"]+)"', content)
        if meta_match and meta_match.group(1):
            status_value = meta_match.group(1)
            if status_value not in status_parts:
                status_parts.append(status_value)
        
        return ", ".join(status_parts) if status_parts else "未知"
    
    def _extract_book_introduction(self, content: str) -> str:
        """
        从HTML内容中提取书籍简介
        
        Args:
            content: 页面HTML内容
            
        Returns:
            书籍简介
        """
        # 匹配简介标签
        intro_pattern = r'<div class="h112 mb15 det-abt lh1d8 c_strong fs16 hm-scroll"[^>]*>(.*?)</div>'
        match = re.search(intro_pattern, content, re.DOTALL)
        
        if match:
            intro_html = match.group(1)
            # 清理HTML标签
            intro_text = re.sub(r'<[^>]+>', '', intro_html).strip()
            return intro_text
        
        # 从meta标签获取描述
        meta_match = re.search(r'<meta name="description" content="([^"]+)"', content)
        if meta_match:
            return meta_match.group(1)
        
        return ""
    
    def _parse_chapter_list_json(self, json_content: str) -> List[Dict[str, Any]]:
        """
        解析章节列表JSON数据
        
        Args:
            json_content: JSON格式的章节列表内容
            
        Returns:
            章节列表信息
        """
        try:
            # 清理JSON内容，去除JavaScript变量声明
            clean_json = re.sub(r'^var chapterList\s*=\s*', '', json_content.strip())
            
            data = json.loads(clean_json)
            
            chapters_info = []
            
            if 'bookVolumeList' in data:
                for volume in data['bookVolumeList']:
                    volume_name = volume.get('volume_name', '')
                    
                    if 'bookChapterList' in volume:
                        for chapter in volume['bookChapterList']:
                            chapter_info = {
                                'volume_name': volume_name,
                                'chapter_name': chapter.get('chapter_name', ''),
                                'chapter_id': str(chapter.get('id', '')),
                                'order': len(chapters_info) + 1
                            }
                            chapters_info.append(chapter_info)
            
            return chapters_info
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"解析章节列表失败: {e}")
    
    def _clean_chapter_content(self, content: str) -> str:
        """
        清理章节内容，去除HTML标签和多余内容
        
        Args:
            content: 原始章节内容
            
        Returns:
            清理后的纯文本内容
        """
        # 首先移除script标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        
        # 移除广告相关div
        content = re.sub(r'<div[^>]*ads[^>]*>.*?</div>', '', content, flags=re.DOTALL)
        
        # 特别处理空div标签
        content = re.sub(r'<div>\s*</div>', '', content)
        
        # 清理HTML标签，保留文本内容
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余的空格和换行
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'^\s+|\s+$', '', content)
        
        return content
    
    def _fix_encoding(self, content: str) -> str:
        """
        修复编码问题，处理乱码内容
        
        Args:
            content: 可能包含乱码的内容
            
        Returns:
            修复后的正确编码内容
        """
        if not content:
            return content
        
        # 检查是否已经是正确的UTF-8编码
        try:
            # 尝试UTF-8解码再编码，检查是否正常
            content.encode('utf-8').decode('utf-8')
            return content
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，说明可能存在编码问题
            pass
        
        # 检查内容中是否包含中文字符
        chinese_pattern = r'[\u4e00-\u9fff]'
        chinese_matches = re.findall(chinese_pattern, content)
        
        if len(chinese_matches) < 10:  # 如果中文字符很少，可能存在编码问题
            # 尝试GBK编码
            try:
                # 先尝试GBK解码
                gbk_content = content.encode('latin1').decode('gbk')
                # 检查是否包含更多中文字符
                gbk_chinese_matches = re.findall(chinese_pattern, gbk_content)
                if len(gbk_chinese_matches) > len(chinese_matches):
                    return gbk_content
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            
            # 尝试GB2312编码
            try:
                gb2312_content = content.encode('latin1').decode('gb2312')
                gb2312_chinese_matches = re.findall(chinese_pattern, gb2312_content)
                if len(gb2312_chinese_matches) > len(chinese_matches):
                    return gb2312_content
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
        
        return content
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        """
        获取URL内容，重写基类方法以处理飞库中文网的编码问题
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容或None
        """
        import requests
        
        proxies = None
        if self.proxy_config and self.proxy_config.get('enabled', False):
            proxy_url = self.proxy_config.get('proxy_url', '')
            if proxy_url:
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
        
        for attempt in range(max_retries):
            try:
                # 使用requests手动处理，确保编码正确
                response = self.session.get(url, proxies=proxies, timeout=10)
                if response.status_code == 200:
                    # 首先尝试使用UTF-8编码
                    response.encoding = 'utf-8'
                    content = response.text
                    
                    # 检查是否有乱码，如果有则尝试其他编码
                    if self._has_garbled_text(content):
                        # 尝试GBK编码
                        response.encoding = 'gbk'
                        gbk_content = response.text
                        if not self._has_garbled_text(gbk_content):
                            return gbk_content
                        
                        # 尝试GB2312编码
                        response.encoding = 'gb2312'
                        gb2312_content = response.text
                        if not self._has_garbled_text(gb2312_content):
                            return gb2312_content
                    
                    return content
                
                elif response.status_code == 404:
                    print(f"页面不存在: {url}")
                    return None
                else:
                    print(f"HTTP {response.status_code} 获取失败: {url}")
                    
            except requests.exceptions.RequestException as e:
                print(f"第 {attempt + 1} 次请求失败: {url}, 错误: {e}")
                
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        return None
    
    def _has_garbled_text(self, text: str) -> bool:
        """
        检查文本是否包含乱码
        
        Args:
            text: 要检查的文本
            
        Returns:
            是否包含乱码
        """
        # 检查常见的乱码字符
        garbled_patterns = [
            r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]',  # 控制字符
            r'â€|Ã|Â|Å|â|ä|å|æ|ç|è|é|ê|ë|ì|í|î|ï|ð|ñ|ò|ó|ô|õ|ö|÷|ø|ù|ú|û|ü|ý|þ|ÿ',  # 常见的乱码字符
        ]
        
        for pattern in garbled_patterns:
            if re.search(pattern, text):
                return True
        
        # 检查中文字符比例，如果很少可能有问题
        chinese_pattern = r'[\u4e00-\u9fff]'
        chinese_chars = re.findall(chinese_pattern, text)
        total_chars = len(text)
        
        if total_chars > 100 and len(chinese_chars) / total_chars < 0.01:  # 中文字符比例小于1%
            return True
        
        return False
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，处理飞库中文网的多章节多部小说
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        try:
            # 获取小说基本信息页
            novel_url = self.get_novel_url(novel_id)
            novel_content = self._get_url_content(novel_url)
            
            if not novel_content:
                raise Exception(f"无法获取小说页面: {novel_url}")
            
            # 提取小说标题
            title = self._extract_title(novel_content)
            if not title:
                raise ValueError("未获取到小说标题")
            
            # 提取书籍状态
            status = self._extract_book_status(novel_content)
            
            # 提取书籍简介
            introduction = self._extract_book_introduction(novel_content)
            
            # 获取章节列表
            chapter_list_url = self.get_chapter_list_url(novel_id)
            chapter_list_content = self._get_url_content(chapter_list_url)
            
            if not chapter_list_content:
                raise Exception(f"无法获取章节列表: {chapter_list_url}")
            
            # 解析章节列表
            chapters_info = self._parse_chapter_list_json(chapter_list_content)
            
            if not chapters_info:
                raise ValueError("未获取到章节列表")
            
            print(f"开始处理 [ {title} ] - 章节数: {len(chapters_info)}")
            
            # 逐章获取内容
            chapters = []
            for i, chapter_info in enumerate(chapters_info):
                chapter_name = chapter_info['chapter_name']
                chapter_id = chapter_info['chapter_id']
                volume_name = chapter_info['volume_name']
                
                print(f"正在处理第 {i+1}/{len(chapters_info)} 章: {chapter_name}")
                
                # 获取章节详情页
                chapter_url = self.get_chapter_url(novel_id, chapter_id)
                chapter_content = self._get_url_content(chapter_url)
                
                if not chapter_content:
                    print(f"警告: 无法获取章节内容: {chapter_url}")
                    continue
                
                # 提取章节内容
                content_match = None
                for pattern in self.content_reg:
                    match = re.search(pattern, chapter_content, re.DOTALL)
                    if match:
                        content_match = match.group(1)
                        break
                
                if not content_match:
                    print(f"警告: 未找到章节内容: {chapter_url}")
                    continue
                
                # 清理章节内容
                clean_content = self._clean_chapter_content(content_match)
                
                # 构建章节标题（包含部名）
                full_chapter_title = f"{volume_name} {chapter_name}" if volume_name else chapter_name
                
                chapter_data = {
                    "title": full_chapter_title,
                    "content": clean_content,
                    "url": chapter_url,
                    "order": i + 1
                }
                chapters.append(chapter_data)
                
                # 添加延迟，避免请求过快
                time.sleep(0.5)
            
            if not chapters:
                raise ValueError("未获取到任何有效的章节内容")
            
            # 构建小说信息
            novel_content = {
                "title": title,
                "content": "",  # 多章节小说，不在详情中存储内容
                "url": novel_url,
                "book_type": "多章节",
                "status": status,
                "introduction": introduction,
                "chapters": chapters
            }
            
            print(f'[ {title} ] 完成，共处理 {len(chapters)} 章')
            return novel_content
            
        except Exception as e:
            raise ValueError(f"解析小说详情失败: {e}")
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题
        
        Args:
            content: 页面内容
            
        Returns:
            小说标题
        """
        # 尝试多个正则表达式
        for pattern in self.title_reg:
            match = re.search(pattern, content)
            if match:
                title = match.group(1).strip()
                if title:
                    return title
        
        # 从meta标签获取
        meta_match = re.search(r'<meta property="og:novel:book_name" content="([^"]+)"', content)
        if meta_match:
            return meta_match.group(1)
        
        return ""
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 飞库中文网暂不支持列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = Feiku6Parser()
    
    # 测试单篇小说
    try:
        novel_id = "s3-mingchaonaxieshier"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")