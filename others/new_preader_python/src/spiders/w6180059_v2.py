"""
6180059.xyz 小说网站解析器
基于配置驱动版本，继承自 BaseParser
"""

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
import re
from urllib.parse import unquote
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class W6180059Parser(BaseParser):
    """6180059.xyz 小说解析器"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "6180059.xyz"
    description = "6180059.xyz 短篇小说解析器"
    base_url = "https://6180059.xyz"
    
    # 正则表达式配置
    title_reg = [
        r'<title>([^<]+)</title>',
        r'<h1[^>]*>([^<]+)</h1>',
        r'<meta property="og:title" content="([^"]+)"'
    ]
    
    content_reg = [
        r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'<meta property="og:novel:status" content="([^"]+)"'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配6180059.xyz的URL格式
        
        Args:
            novel_id: 小说ID，格式为 "v=9082&name=我和姐姐疯狂的做爱"
            
        Returns:
            小说URL
        """
        # 从novel_id中提取书籍ID
        id_match = re.search(r'v=(\d+)', novel_id)
        if id_match:
            book_id = id_match.group(1)
            return f"{self.base_url}/ys/6k-d.html?{novel_id}"
        return f"{self.base_url}/ys/6k-d.html?{novel_id}"
    
    def get_content_url(self, novel_id: str) -> str:
        """
        获取书籍内容txt文件的URL
        
        Args:
            novel_id: 小说ID，格式为 "v=9082&name=我和姐姐疯狂的做爱"
            
        Returns:
            内容txt文件URL
        """
        # 从novel_id中提取书籍ID
        id_match = re.search(r'v=(\d+)', novel_id)
        if id_match:
            book_id = id_match.group(1)
            return f"{self.base_url}/ys/cb/{book_id}.txt"
        # 如果没有找到ID，尝试从novel_id中提取数字
        id_match = re.search(r'(\d+)', novel_id)
        if id_match:
            book_id = id_match.group(1)
            return f"{self.base_url}/ys/cb/{book_id}.txt"
        raise ValueError(f"无法从novel_id中提取书籍ID: {novel_id}")
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID，格式为 "v=9082&name=我和姐姐疯狂的做爱"
        """
        import re
        # 匹配查询参数部分
        match = re.search(r'6k-d\.html\?(.+)', url)
        if match:
            return match.group(1)
        return "unknown"
    
    def _extract_book_title_from_id(self, novel_id: str) -> str:
        """
        从小说ID中提取书籍标题
        
        Args:
            novel_id: 小说ID，格式为 "v=9082&name=我和姐姐疯狂的做爱"
            
        Returns:
            书籍标题
        """
        # 匹配name参数
        match = re.search(r'name=([^&]+)', novel_id)
        if match:
            title = match.group(1)
            # URL解码
            try:
                title = unquote(title)
            except:
                pass
            return title
        
        # 如果没有name参数，尝试从URL中提取
        id_match = re.search(r'v=(\d+)', novel_id)
        if id_match:
            return f"书籍_{id_match.group(1)}"
        
        return "未知标题"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，6180059.xyz是短篇小说网站
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _get_txt_content(self, url: str) -> Optional[str]:
        """
        获取txt文件内容，处理编码问题
        
        Args:
            url: txt文件URL
            
        Returns:
            文本内容或None
        """
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                # 首先尝试使用UTF-8编码
                response.encoding = 'utf-8'
                utf8_content = response.text
                
                # 检查UTF-8编码是否正常
                if self._is_valid_chinese_content(utf8_content):
                    return utf8_content
                
                # 如果UTF-8有问题，尝试GBK编码
                response.encoding = 'gbk'
                gbk_content = response.text
                if self._is_valid_chinese_content(gbk_content):
                    return gbk_content
                
                # 尝试GB2312编码
                response.encoding = 'gb2312'
                gb2312_content = response.text
                if self._is_valid_chinese_content(gb2312_content):
                    return gb2312_content
                
                # 尝试BIG5编码
                response.encoding = 'big5'
                big5_content = response.text
                if self._is_valid_chinese_content(big5_content):
                    return big5_content
                
                # 如果所有编码都失败，使用原始字节并尝试解码
                raw_content = response.content
                
                # 尝试检测常见的中文编码模式
                for encoding in ['utf-8', 'gbk', 'gb2312', 'big5']:
                    try:
                        decoded_content = raw_content.decode(encoding)
                        if self._is_valid_chinese_content(decoded_content):
                            return decoded_content
                    except UnicodeDecodeError:
                        continue
                
                # 最后使用utf-8并忽略错误
                return raw_content.decode('utf-8', errors='ignore')
            
            return None
            
        except Exception as e:
            logger.error(f"获取txt内容失败: {url}, 错误: {e}")
            return None
    
    def _is_valid_chinese_content(self, content: str) -> bool:
        """
        检查内容是否为有效的中文内容
        
        Args:
            content: 要检查的内容
            
        Returns:
            是否为有效的中文内容
        """
        if not content:
            return False
        
        # 检查是否有中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', content)
        
        # 如果有足够的中文字符，认为是有效内容
        if len(chinese_chars) >= 10:  # 至少有10个中文字符
            return True
        
        # 检查是否包含乱码字符
        garbled_patterns = [
            r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]',  # 控制字符
            r'â€|Ã|Â|Å|â|ä|å|æ|ç|è|é|ê|ë|ì|í|î|ï|ð|ñ|ò|ó|ô|õ|ö|÷|ø|ù|ú|û|ü|ý|þ|ÿ',  # 常见的乱码字符
        ]
        
        for pattern in garbled_patterns:
            if re.search(pattern, content):
                return False
        
        # 如果内容较短但包含中文字符，也认为是有效的
        if len(content) < 100 and len(chinese_chars) > 0:
            return True
        
        return False
    
    def _clean_txt_content(self, content: str) -> str:
        """
        清理txt文件内容
        
        Args:
            content: 原始txt内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return ""
        
        # 首先彻底清理HTML标签，特别是<p>和</p>标签
        content = self._clean_html_tags_completely(content)
        
        # 移除多余的空行和空格
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # 只保留非空行
                cleaned_lines.append(line)
        
        # 重新组合，每段之间用换行分隔
        cleaned_content = '\n\n'.join(cleaned_lines)
        
        # 移除特殊字符和乱码
        cleaned_content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', cleaned_content)
        
        return cleaned_content
    
    def _clean_html_tags_completely(self, content: str) -> str:
        """
        彻底清理HTML标签，特别是处理不完整的<p>和</p>标签
        
        Args:
            content: 包含HTML标签的内容
            
        Returns:
            完全清理后的纯文本
        """
        if not content:
            return ""
        
        # 第一步：移除所有完整的HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 第二步：处理可能残留的不完整标签
        # 处理不完整的<p>标签（可能只有<p没有>）
        content = re.sub(r'<p\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<\s*/\s*p\s*', '', content, flags=re.IGNORECASE)
        
        # 第三步：处理其他常见的不完整标签
        html_tags = [
            'div', 'span', 'br', 'strong', 'b', 'em', 'i', 'u', 'font', 'table',
            'tr', 'td', 'th', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
        ]
        
        for tag in html_tags:
            # 处理开始标签不完整
            content = re.sub(r'<\s*' + tag + r'\s*', '', content, flags=re.IGNORECASE)
            # 处理结束标签不完整
            content = re.sub(r'<\s*/\s*' + tag + r'\s*', '', content, flags=re.IGNORECASE)
        
        # 第四步：处理HTML实体
        html_entities = {
            '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>', 
            '&quot;': '"', '&apos;': "'", '&copy;': '(c)', '&reg;': '(r)'
        }
        
        for entity, replacement in html_entities.items():
            content = content.replace(entity, replacement)
        
        # 第五步：清理可能剩余的<和>字符
        content = re.sub(r'<+', '', content)
        content = re.sub(r'>+', '', content)
        
        # 第六步：清理多余的空格和换行
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        return content
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，处理6180059.xyz的单篇txt格式
        
        Args:
            novel_id: 小说ID，格式为 "v=9082&name=我和姐姐疯狂的做爱"
            
        Returns:
            小说详情信息
        """
        
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        try:
            # 从ID中提取标题
            title = self._extract_book_title_from_id(novel_id)
            
            if not title or title == "未知标题":
                # 尝试从详情页获取标题
                novel_url = self.get_novel_url(novel_id)
                novel_content = self._get_url_content(novel_url)
                
                if novel_content:
                    # 尝试从HTML中提取标题
                    for pattern in self.title_reg:
                        match = re.search(pattern, novel_content)
                        if match:
                            extracted_title = match.group(1).strip()
                            if extracted_title:
                                title = extracted_title
                                break
            
            if not title:
                raise ValueError("无法获取小说标题")
            
            # 获取txt内容
            content_url = self.get_content_url(novel_id)
            txt_content = self._get_txt_content(content_url)
            
            if not txt_content:
                raise Exception(f"无法获取小说内容: {content_url}")
            
            # 清理txt内容
            clean_content = self._clean_txt_content(txt_content)
            
            if not clean_content:
                raise ValueError("清理后的内容为空")
            
            # 获取详情页URL
            novel_url = self.get_novel_url(novel_id)
            
            print(f"开始处理 [ {title} ]")
            
            # 构建小说信息
            novel_content = {
                "title": title,
                "author": self.novel_site_name,  # 使用数据库中的网站名称
                "content": clean_content,
                "url": novel_url,
                "book_type": "短篇",
                "status": "已完成",  # 单篇短篇小说通常已完成
                "chapters": [
                    {
                        "title": title,
                        "content": clean_content,
                        "url": novel_url,
                        "order": 1
                    }
                ]
            }
            
            print(f'[ {title} ] 完成')
            return novel_content
            
        except Exception as e:
            raise ValueError(f"解析小说详情失败: {e}")
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 6180059.xyz暂不支持列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = W6180059Parser()
    
    # 测试单篇小说
    try:
        novel_id = "v=9082&name=我和姐姐疯狂的做爱"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")