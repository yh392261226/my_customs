"""
ms01.top 小说解析器 - 配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
import base64
import urllib.parse
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

class Ms01Parser(BaseParser):
    """ms01.top 小说解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "ms01.top"
    description = "ms01.top 小说解析器"
    base_url = "https://ms01.top"
    
    # 正则表达式配置
    title_reg = [
        r'<h3 style="background-color:#ffdab9;">([^<]+)</h3>',
        r'<title>([^<]+)</title>'
    ]
    
    content_reg = [
        r'<div class="content">[\s\S]*?var decodedContent = decodeURIComponent\(escape\(atob\("([^"]+)"\)\)\);',
        r'var decodedContent = decodeURIComponent\(escape\(atob\("([^"]+)"\)\)\);'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_decrypt_content",  # 解密内容
        "_clean_html_content",  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配ms01.top的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/article.php?id={novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，ms01.top都是单篇小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _decrypt_content(self, content: str) -> str:
        """
        解密内容 - ms01.top特有处理
        使用 decodeURIComponent(escape(atob(...))) 解密
        
        Args:
            content: 加密的内容
            
        Returns:
            解密后的内容
        """
        # 如果内容已经是解密后的文本，直接返回
        if not content.startswith("PHA+"):
            return content
        
        try:
            # 模拟 JavaScript 的 decodeURIComponent(escape(atob(...))) 解密过程
            # 正确的顺序是：atob -> escape -> decodeURIComponent
            
            # 1. 首先进行 base64 解码
            # 确保base64字符串长度是4的倍数，否则添加填充
            padding = 4 - (len(content) % 4)
            if padding != 4:
                content += "=" * padding
            
            decoded_bytes = base64.b64decode(content)
            
            # 2. 将字节转换为Latin-1编码的字符串（模拟JavaScript的二进制字符串）
            latin1_str = decoded_bytes.decode('latin-1')
            
            # 3. 模拟 JavaScript 的 escape 函数
            # escape会将非ASCII字符转换为%XX格式
            escaped_str = ''
            for char in latin1_str:
                code = ord(char)
                if code > 127:
                    # 对于非ASCII字符，转换为%XX格式
                    escaped_str += f'%{code:02X}'
                elif char == "%":
                    # 转义百分号
                    escaped_str += "%25"
                else:
                    escaped_str += char
            
            # 4. 模拟 decodeURIComponent 解码
            # 使用Python的urllib.parse.unquote来解码%XX格式
            final_content = urllib.parse.unquote(escaped_str)
            
            return final_content
            
        except Exception as e:
            print(f"解密失败: {e}")
            # 如果解密失败，尝试直接base64解码
            try:
                # 确保base64字符串长度是4的倍数
                padding = 4 - (len(content) % 4)
                if padding != 4:
                    content += "=" * padding
                decoded_bytes = base64.b64decode(content)
                return decoded_bytes.decode('utf-8', errors='ignore')
            except Exception as e2:
                print(f"直接base64解码也失败: {e2}")
                # 如果还是失败，返回原始内容
                return content
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写解析小说详情方法，适配ms01.top的特殊结构
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ]")
        
        # 提取加密内容
        encrypted_content = self._extract_with_regex(content, self.content_reg)
        
        if not encrypted_content:
            raise Exception("无法提取小说加密内容")
        
        # 执行解密和处理函数
        processed_content = self._execute_after_crawler_funcs(encrypted_content)
        
        print(f'[ {title} ] 完成')
        
        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': processed_content,
                'url': novel_url
            }]
        }
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - ms01.top不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []