"""
ZXCMS网站解析器 v2
支持 https://www.zxcms.net/ 网站的小说解析
使用统一的crypto_utils解密工具
"""

from src.utils.logger import get_logger
import re
import base64
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from Crypto.Cipher import AES
import time
# 导入可能需要的工具函数
try:
    # 尝试从crypto_utils导入函数
    from src.utils.crypto_utils import extract_encryption_keys
except ImportError:
    # 如果导入失败，定义空实现
    from typing import Tuple
    def extract_encryption_keys(html_content: str) -> Tuple[str, str]:
        return "", ""
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class ZXCMSParser(BaseParser):
    """ZXCMS网站解析器 v2"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 初始化解密配置
        self.key = "encryptedDatastr"
        self.iv_b64 = "5w9sgjdqHHEw0Fjc3C2qHg=="
    
    # 基本信息
    name = "ZXCMS"
    description = "ZXCMS多章节小说解析器"
    base_url = "https://www.zxcms.net"
    
    # 正则表达式配置 - 书籍信息页
    title_reg = [
        r'<h1[^>]*>([^<]+)</h1>'
    ]
    
    # 状态提取 - 从 <div id="info"><p class="visible-xs"> 中提取
    status_reg = [
        r'<div[^>]*id="info"[^>]*>.*?<p[^>]*class="visible-xs"[^>]*>(.*?)</p>'
    ]
    
    # 简介提取 - 从 <div id="intro"> 中提取
    description_reg = [
        r'<div[^>]*id="intro"[^>]*>(.*?)</div>'
    ]
    
    # 开始阅读链接提取 - 从 <div class="readbtn"> 中提取
    read_link_reg = [
        r'<div[^>]*class="readbtn"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>[^<]*开始阅读[^<]*</a>',
        r'<div[^>]*class="readbtn"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>[^<]*开始阅读[^<]*</a>',
        r'<a[^>]*href="([^"]*)"[^>]*>[^<]*开始阅读[^<]*</a>'
    ]
    
    # 章节标题提取 - 从 <div class="bookname"> 中提取
    chapter_title_reg = [
        r'<div[^>]*class="bookname"[^>]*>\s*<h1[^>]*>([^<]+)</h1>'
    ]
    
    # 内容页正则 - 用于提取加密脚本（booktxthtml包含真正的加密内容）
    content_reg = [
        # 精确匹配格式：<script>  $('#booktxthtml').html(x("encrypted_data","key","iv"));</script>
        r"<script>\s*\$\(['\"]*#booktxthtml['\"]*\)\.html\(x\(['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"]\)\);</script>"
    ]
    
    # 下一页链接提取 - 从 <div class="bottem1"> 和 <div class="bottem2"> 中提取
    next_page_reg = [
        r'<div[^>]*class="bottem[12]"[^>]*>.*?<a[^>]*rel="next"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        r'<a[^>]*rel="next"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
    ]
    
    # 书籍类型配置
    book_type = ["多章节"]
    
    def _get_url_content(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        获取URL内容，带重试机制
        
        Args:
            url: 要获取的URL
            max_retries: 最大重试次数，默认为3次
            
        Returns:
            页面内容或None
        """
        import time
        import random
        
        for attempt in range(max_retries):
            try:
                logger.info(f"获取页面内容 (第{attempt + 1}/{max_retries}次): {url}")
                
                # 调用父类方法获取内容
                content = super()._get_url_content(url)
                
                if content and len(content) > 1000:  # 只要内容不为空且有一定长度就认为成功
                    print(f"页面获取成功，内容长度: {len(content)}")
                    return content
                else:
                    logger.warning(f"获取到空内容或内容过短，尝试重试...")
                    time.sleep(random.uniform(1, 2))  # 随机延迟1-2秒
                    continue
                    
            except Exception as e:
                logger.error(f"获取页面内容失败 (第{attempt + 1}/{max_retries}次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 2))  # 随机延迟1-2秒
        
        logger.error(f"获取页面内容失败，已达到最大重试次数: {url}")
        return None

    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配ZXCMS网站的URL格式
        
        Args:
            novel_id: 小说ID，格式为 "26_34976"
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/{novel_id}/"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 空实现，因为ZXCMS主要是通过章节列表访问
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写基类方法，确保使用自己的下一页提取逻辑
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        # 解码HTML实体
        import html
        title = html.unescape(title)
        
        # 繁简转换标题
        title = self._convert_traditional_to_simplified(title)
        
        logger.info(f"开始处理 [ {title} ]")
        
        # 使用自己的多章节解析逻辑
        novel_content = self._parse_multichapter_novel(content, novel_url, title)
        
        logger.info(f'[ {title} ] 完成')
        return novel_content
    
    def _get_next_page_url(self, content: str, current_url: str) -> Optional[str]:
        """
        重写基类的下一页URL获取方法，确保过滤javascript:void(0)链接
        
        Args:
            content: 当前页面内容
            current_url: 当前页面URL
            
        Returns:
            下一页URL或None
        """
        # 首先检查是否是"没有了"或类似的结束标识
        end_patterns = [
            r'<a[^>]*rel="next"[^>]*href="javascript:void\(0\);"[^>]*>没有了</a>',
            r'<a[^>]*href="javascript:void\(0\);"[^>]*>没有了</a>',
            r'>没有了<',
            r'>结束<',
            r'>完结<'
        ]
        
        for pattern in end_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                print("检测到结束标识，停止处理")
                return None
        
        # 使用自己的下一页提取方法
        next_url = self._extract_next_page(content)
        
        if not next_url:
            return None
        
        # 检查是否是javascript:void(0)链接
        if "javascript:void(0)" in next_url:
            print("检测到javascript:void(0)链接，停止处理")
            return None
        
        # 构建完整URL
        if next_url.startswith('/'):
            return f"{self.base_url}{next_url}"
        elif next_url.startswith('http'):
            return next_url
        else:
            # 相对路径处理
            from urllib.parse import urljoin
            return urljoin(current_url, next_url)
    
    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        解析多章节小说
        
        Args:
            content: 章节列表页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说内容字典
        """
        # 提取开始阅读链接
        read_url = self._extract_read_link(content)
        if not read_url:
            raise Exception("无法提取开始阅读链接")
        
        logger.info(f"开始处理 [ {title} ] - 开始阅读链接: {read_url}")
        
        # 获取所有章节内容
        chapters_with_content = []
        current_url = read_url
        chapter_number = 1
        
        while current_url:
            try:
                logger.info(f"正在爬取第 {chapter_number} 章: {current_url}")
                
                # 获取章节页面内容
                chapter_content = self._get_url_content(current_url)
                if not chapter_content:
                    logger.warning(f"无法获取章节页面内容: {current_url}")
                    break
                
                # 提取章节标题
                chapter_title = self._extract_chapter_title(chapter_content)
                if not chapter_title:
                    chapter_title = f"第{chapter_number}章"
                
                # 解码HTML实体
                import html
                chapter_title = html.unescape(chapter_title)
                
                # 繁简转换标题
                chapter_title = self._convert_traditional_to_simplified(chapter_title)
                
                # 提取并解密章节内容
                chapter_text = self._extract_encrypted_content(chapter_content)
                print(f"章节解密结果: {bool(chapter_text)}, 长度: {len(chapter_text) if chapter_text else 0}")
                if not chapter_text:
                    print(f"无法解密章节内容，可能是页面未完全加载或缺少加密密钥: {current_url}")
                    # 重试获取当前章节，最多1次
                    logger.info(f"重试获取章节内容: {current_url}")
                    import time
                    time.sleep(2)  # 等待2秒后重试
                    
                    # 重新获取页面内容
                    retry_content = self._get_url_content(current_url, max_retries=3)
                    if retry_content:
                        # 重新尝试解密
                        chapter_text = self._extract_encrypted_content(retry_content)
                        print(f"重试解密结果: {bool(chapter_text)}, 长度: {len(chapter_text) if chapter_text else 0}")
                    
                    if not chapter_text:
                        print(f"重试后仍无法解密章节内容，跳过: {current_url}")
                        # 不跳出循环，尝试继续处理下一个章节
                        # 不增加章节号，因为当前章节没有成功添加
                        # 获取下一页链接
                        next_url = self._extract_next_page(chapter_content)
                        if not next_url or 'javascript:void(0)' in next_url:
                            print("没有更多章节，结束处理")
                            break
                        
                        # 构建完整的下一页URL
                        if next_url.startswith('/'):
                            current_url = urljoin(self.base_url, next_url)
                        elif next_url.startswith('http'):
                            current_url = next_url
                        else:
                            current_url = urljoin(current_url, next_url)
                        
                        # 检查构建的URL是否是javascript:void(0)链接
                        if current_url == "https://www.zxcms.net/book_34976/javascript:void(0);" or "javascript:void(0)" in current_url:
                            print(f"检测到javascript:void(0)链接，停止处理: {current_url}")
                            break
                        
                        continue  # 跳过当前章节，继续下一个章节
                
                # 繁简转换内容
                chapter_text = self._convert_traditional_to_simplified(chapter_text)
                
                chapters_with_content.append({
                    'chapter_number': chapter_number,
                    'title': chapter_title,
                    'content': chapter_text,
                    'url': current_url
                })
                
                logger.info(f"章节 {chapter_number}: {chapter_title} - 完成")
                
                # 获取下一页链接
                next_url = self._extract_next_page(chapter_content)
                
                # 只有在成功添加章节后才增加章节号
                chapter_number += 1
                if not next_url or 'javascript:void(0)' in next_url:
                    print("没有更多章节，结束处理")
                    break
                
                # 构建完整的下一页URL
                if next_url.startswith('/'):
                    current_url = urljoin(self.base_url, next_url)
                elif next_url.startswith('http'):
                    current_url = next_url
                else:
                    current_url = urljoin(current_url, next_url)
                
                # 检查构建的URL是否是javascript:void(0)链接
                if current_url == "https://www.zxcms.net/book_34976/javascript:void(0);" or "javascript:void(0)" in current_url:
                    print(f"检测到javascript:void(0)链接，停止处理: {current_url}")
                    break
                
                chapter_number += 1
                
                # 章节间延迟
                import time
                time.sleep(1)
                    
            except Exception as e:
                print(f"章节 {chapter_number}: 错误 - {e}")
                break
        
        if not chapters_with_content:
            raise Exception("无法获取任何章节内容")
        
        # 提取简介和状态
        description = self._extract_description(content)
        status = self._extract_status(content)
        
        # 解码HTML实体
        import html
        if description:
            description = html.unescape(description)
        if status:
            status = html.unescape(status)
        
        # 繁简转换简介
        if description:
            description = self._convert_traditional_to_simplified(description)
        
        return {
            'title': title,
            'author': self.novel_site_name or self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'description': description,
            'status': status,
            'chapters': chapters_with_content
        }
    
    def _extract_read_link(self, content: str) -> Optional[str]:
        """
        从书籍页面提取开始阅读链接
        
        Args:
            content: 书籍页面内容
            
        Returns:
            开始阅读链接URL
        """
        for pattern in self.read_link_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                link = match.group(1).strip()
                if link:
                    # 确保URL是完整的
                    if not link.startswith('http'):
                        link = urljoin(self.base_url, link)
                    return link
        return None
    
    def _extract_chapter_title(self, content: str) -> Optional[str]:
        """
        从章节页面提取章节标题
        
        Args:
            content: 章节页面内容
            
        Returns:
            章节标题
        """
        try:
            for pattern in self.chapter_title_reg:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    title = match.group(1).strip()
                    if title:
                        # 清理HTML标签和多余空格
                        title = re.sub(r'<[^>]+>', '', title)
                        title = re.sub(r'\s+', ' ', title)
                        return title.strip()
        except Exception as e:
            logger.warning(f"提取章节标题失败: {e}")
        return None
    
    def _extract_next_page(self, content: str) -> Optional[str]:
        """
        从章节页面提取下一页链接
        
        Args:
            content: 章节页面内容
            
        Returns:
            下一页链接URL
        """
        for pattern in self.next_page_reg:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                if len(match) >= 2:
                    link = match[0].strip()
                    text = match[1].strip()
                    
                    # 首先检查是否是"没有了"或类似的结束标识
                    if "没有了" in text or "结束" in text or "完结" in text:
                        print(f"检测到结束标识: {text}")
                        return None
                    
                    # 直接检查是否是javascript:void(0)链接
                    if link == "javascript:void(0);" or "javascript:void(0)" in link:
                        print(f"检测到javascript:void(0)链接，直接返回None")
                        return None
                    
                    # 检查其他javascript链接
                    if not link or "javascript:" in link:
                        print(f"过滤无效链接: {link}")
                        continue
                    
                    # 只返回有效的页面链接
                    if link and link.startswith('/'):
                        print(f"找到有效的下一页链接: {link}")
                        return link
        print("没有找到下一页链接")
        return None
    
    def _extract_description(self, content: str) -> str:
        """
        提取小说简介
        
        Args:
            content: 书籍页面内容
            
        Returns:
            小说简介
        """
        try:
            for pattern in self.description_reg:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    desc = match.group(1).strip()
                    # 清理HTML标签
                    desc = re.sub(r'<[^>]+>', '', desc)
                    desc = re.sub(r'\s+', ' ', desc)
                    return desc.strip()
        except Exception as e:
            print(f"提取简介失败: {e}")
        return ""
    
    def _extract_status(self, content: str) -> str:
        """
        提取小说状态
        
        Args:
            content: 书籍页面内容
            
        Returns:
            小说状态
        """
        try:
            for pattern in self.status_reg:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    status_html = match.group(1).strip()
                    # 提取所有标签中的文字部分
                    status_texts = re.findall(r'>([^<]+)<', status_html)
                    if status_texts:
                        # 用逗号连接所有文字
                        return ', '.join([text.strip() for text in status_texts if text.strip()])
        except Exception as e:
            print(f"提取状态失败: {e}")
        return "连载中"
    
    def _extract_encrypted_content(self, content: str) -> Optional[str]:
        """
        提取并解密加密内容 - 从页面中提取真实的加密密钥
        
        Args:
            content: 章节页面内容
            
        Returns:
            解密后的内容
        """
        print("开始提取加密内容...")
        print(f"页面内容长度: {len(content)}")
        
        # 检查内容长度，但放宽限制以便在页面部分加载时也能尝试解密
        if len(content) < 2000:
            print(f"页面内容过短 ({len(content)}字节)，可能未完全加载")
            return None  # 直接返回None，而不是提取可见内容，因为页面未加载完成
        
 # 查找booktxthtml相关的x函数调用，这是我们真正的加密内容来源
        booktxthtml_pattern = r"#booktxthtml.*?x\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\s*\)"
        booktxthtml_matches = re.findall(booktxthtml_pattern, content, re.DOTALL)
        
        print(f"查找booktxthtml相关的x函数调用: 找到 {len(booktxthtml_matches)} 个匹配")
        
        # 如果没有找到，尝试更宽松的正则表达式
        if not booktxthtml_matches:
            print("尝试更宽松的正则表达式...")
            booktxthtml_pattern = r"#booktxthtml.*?x\(\s*['\"]([^'\"]+)['\"],.*?['\"]([^'\"]+)['\"],.*?['\"]([^'\"]+)['\"]"
            booktxthtml_matches = re.findall(booktxthtml_pattern, content, re.DOTALL)
            print(f"更宽松的正则表达式找到 {len(booktxthtml_matches)} 个匹配")
        
        # 如果找不到booktxthtml相关的x函数，尝试查找所有x函数作为备选
        if not booktxthtml_matches:
            print("未找到booktxthtml相关的x函数调用，尝试查找所有x函数")
            x_function_pattern = r"x\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\s*\)"
            x_function_matches = re.findall(x_function_pattern, content, re.DOTALL)
            
            if not x_function_matches:
                print("未找到任何x函数调用，页面可能未完全加载")
                return None
        else:
            # 使用booktxthtml相关的x函数
            x_function_matches = booktxthtml_matches
        
        # 检查所有匹配的x函数调用，选择最有可能包含小说内容的
        print(f"检查 {len(x_function_matches)} 个x函数调用，选择最有可能包含小说内容的...")
        
        # 选择数据最长的x函数调用，通常包含更多内容
        best_match = x_function_matches[0]
        for match in x_function_matches:
            encrypted_data, key, iv = match
            print(f"  数据长度={len(encrypted_data)}, key={key}, iv={iv[:20]}...")
            if len(encrypted_data) > len(best_match[0]):
                best_match = match
        
        encrypted_data, key, iv = best_match
        print(f"选择了数据最长的x函数调用: 数据长度={len(encrypted_data)}, key={key}, iv={iv}")
        
        # 加密数据长度检查，但允许较短的加密数据
        if len(encrypted_data) < 20:
            print(f"加密数据过短: {len(encrypted_data)}字节，跳过此段加密数据")
            return None
        
        print(f"找到x函数调用: 数据长度={len(encrypted_data)}, key={key}, iv={iv}")
        
        # 对转义字符进行反转义处理
        try:
            import codecs
            # 处理双重转义的情况：\u002b -> \u002b -> +
            # 第一次解码：将\u002b解码为字符串"\u002b"
            processed_data = codecs.decode(encrypted_data, 'unicode-escape')
            # 第二次解码：将字符串"\u002b"解码为字符"+"
            processed_data = codecs.decode(processed_data, 'unicode-escape')
            
            # 处理HTML实体转义
            processed_data = processed_data.replace('\\/', '/')
            processed_data = processed_data.replace('\\u002b', '+')
            processed_data = processed_data.replace('\\u002f', '/')
            
            print(f"反转义后的加密数据长度: {len(processed_data)}")
            print(f"反转义后的加密数据前50字符: {processed_data[:50]}...")
            
            # 使用提取到的真实密钥进行解密
            decrypted_content = self._decrypt_with_real_key(processed_data, key, iv)
            if decrypted_content and len(decrypted_content) > 50:  # 解密内容应该有一定长度
                print(f"解密成功，内容长度: {len(decrypted_content)}")
                print(f"解密内容前100字符: {decrypted_content[:100]}...")
                
                # 先打印更多解密内容以便调试
                print(f"完整解密内容前300字符: {decrypted_content[:300]}")
                print(f"完整解密内容后300字符: {decrypted_content[-300:]}")
                
                # 清理HTML内容
                cleaned_content = self._clean_html_content(decrypted_content)
                if cleaned_content and len(cleaned_content) > 50:
                    print(f"内容清理成功，最终长度: {len(cleaned_content)}")
                    print(f"清理后内容前200字符: {cleaned_content[:200]}")
                    return cleaned_content
                else:
                    print("内容清理失败或内容过短")
                    # 尝试使用原始解密内容，不清理
                    return decrypted_content if len(decrypted_content) > 100 else None
            else:
                print("初次解密失败，尝试其他解密方式...")
                # 尝试使用备选解密方式
                decrypted_content = self._decrypt_with_alternative_methods(processed_data, key, iv)
                if decrypted_content and len(decrypted_content) > 50:
                    print(f"备选解密方式成功，内容长度: {len(decrypted_content)}")
                    return self._clean_html_content(decrypted_content) or decrypted_content
                else:
                    print("所有解密方式均失败")
                    return None
        except Exception as e:
            print(f"处理加密数据时出错: {e}")
            return None
    
    def _is_valid_decrypted_content(self, content: str) -> bool:
        """
        检查解密后的内容是否有效
        
        Args:
            content: 解密后的内容
            
        Returns:
            是否是有效内容
        """
        if not content or len(content) < 10:
            return False
        
        # 检查是否包含中文字符
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        
        # 检查是否包含常见的小说内容词汇
        novel_keywords = ['的', '了', '是', '在', '我', '你', '他', '她']
        keyword_count = sum(1 for keyword in novel_keywords if keyword in content)
        
        # 检查是否是乱码（包含太多不可读字符）
        readable_chars = len([c for c in content if 32 <= ord(c) <= 126 or ord(c) > 127])
        readable_ratio = readable_chars / len(content)
        
        # 综合判断
        is_valid = (
            chinese_chars > 10 or  # 有足够的中文字符
            keyword_count > 3 or  # 有足够的关键词
            (readable_ratio > 0.7 and len(content) > 100)  # 大部分字符可读且内容足够长
        ) and (
            # 排除明显无效的情况
            not content.startswith('Error') and  # 不是错误信息
            not all(c in '0123456789abcdefABCDEF' for c in content.replace(' ', ''))  # 不是纯十六进制
        )
        
        return is_valid
    
    def _extract_page_keys(self, content: str) -> Optional[Dict[str, str]]:
        """
        从页面提取加密密钥
        
        Args:
            content: 页面内容
            
        Returns:
            包含密钥的字典或None
        """
        keys = {}
        
        # 首先尝试crypto_utils格式
        try:
            from ..utils.crypto_utils import extract_encryption_keys
            aei, aek = extract_encryption_keys(content)
            if aei and aek:
                keys['aei'] = aei
                keys['aek'] = aek
                print(f"crypto_utils提取到密钥: aei={aei}, aek={aek}")
        except Exception as e:
            print(f"crypto_utils密钥提取失败: {e}")
        
        # 尝试查找x函数调用中的密钥
        x_function_pattern = r"x\(\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+)['\"]\s*\)"
        x_function_matches = re.findall(x_function_pattern, content, re.DOTALL)
        
        # 从第一个x函数调用中提取密钥
        if x_function_matches:
            first_match = x_function_matches[0]
            if len(first_match) >= 3:
                # 第一个是加密数据，第二个是key，第三个是iv
                key = first_match[1]
                iv = first_match[2]
                
                # 如果key或iv是默认值，记录它们
                if key == "encryptedDatastr":
                    keys['aek'] = key  # aek是key
                if iv == "5w9sgjdqHHEw0Fjc3C2qHg==" or iv == "3rptdNnUDS4FAypFfpoIpA==":
                    keys['aei'] = iv   # aei是iv
                
                print(f"从x函数提取到密钥: key={key}, iv={iv}")
        
        # 如果还没有提取到密钥，使用默认值
        if not keys:
            keys['aei'] = "5w9sgjdqHHEw0Fjc3C2qHg=="  # 默认IV
            keys['aek'] = "encryptedDatastr"  # 默认Key
            print("使用默认密钥")
        
        return keys if keys else None
    
    def _find_encrypted_data_segments(self, content: str, page_keys: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        查找htmlContenthtml加密数据段
        
        Args:
            content: 章节页面内容
            page_keys: 从页面提取的密钥
            
        Returns:
            解密后的内容
        """
        print("开始查找htmlContenthtml加密数据段...")
        
        # 只查找htmlContenthtml相关的x函数调用
        htmlcontent_pattern = r"#htmlContenthtml.*?x\(['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"]\)"
        htmlcontent_matches = re.findall(htmlcontent_pattern, content, re.DOTALL)
        
        if not htmlcontent_matches:
            print("未找到htmlContenthtml相关的x函数调用")
            return None
        
        print(f"找到 {len(htmlcontent_matches)} 个htmlContenthtml相关的x函数调用")
        
        # 使用第一个匹配的htmlContenthtml x函数调用
        encrypted_data, key, iv = htmlcontent_matches[0]
        print(f"尝试htmlContenthtml x函数: 数据长度={len(encrypted_data)}, key={key}, iv={iv}")
        
        # 对转义字符进行反转义处理
        if encrypted_data:
            import codecs
            # 处理双重转义的情况：\u002b -> \u002b -> +
            # 第一次解码：将\u002b解码为字符串"\u002b"
            encrypted_data = codecs.decode(encrypted_data, 'unicode-escape')
            # 第二次解码：将字符串"\u002b"解码为字符"+"
            encrypted_data = codecs.decode(encrypted_data, 'unicode-escape')
            
            # 处理HTML实体转义
            encrypted_data = encrypted_data.replace('\\/', '/')
            encrypted_data = encrypted_data.replace('\\u002b', '+')
            encrypted_data = encrypted_data.replace('\\u002f', '/')
            
            print(f"反转义后的加密数据长度: {len(encrypted_data)}")
            print(f"反转义后的加密数据前50字符: {encrypted_data[:50]}...")
        
        # 尝试解密
        try:
            decrypted_content = self._decrypt_with_real_key(encrypted_data, key, iv)
            if decrypted_content and len(decrypted_content) > 10:
                print(f"booktxthtml x函数解密成功！内容前100字符: {decrypted_content[:100]}...")
                
                # 检查是否包含中文字符
                chinese_chars = len([c for c in decrypted_content if '\u4e00' <= c <= '\u9fff'])
                print(f"中文字符数量: {chinese_chars}")
                
                # 如果有中文字符，则清理并返回
                if chinese_chars > 10:
                    cleaned_content = self._clean_html_content(decrypted_content)
                    if cleaned_content:
                        print(f"内容清理成功，最终长度: {len(cleaned_content)}")
                        return cleaned_content
            else:
                print("解密结果为空或太短")
                return None
        except Exception as e:
            print(f"booktxthtml x函数解密失败: {e}")
            return None
        
        print("booktxthtml加密数据段解密失败")
        return None
    
    def _decrypt_with_real_key(self, encrypted_data: str, key: str, iv: str) -> Optional[str]:
        """
        使用从页面提取的真实密钥解密内容
        
        Args:
            encrypted_data: 加密数据
            key: 从页面提取的解密密钥
            iv: 从页面提取的初始化向量
            
        Returns:
            解密后的内容
        """
        print(f"使用真实密钥解密: 数据长度={len(encrypted_data)}, key={key}, iv={iv}")
        
        # Base64解析加密数据
        try:
            ciphertext = base64.b64decode(encrypted_data, validate=True)
            print(f"Base64解码成功，密文长度: {len(ciphertext)}")
        except Exception as e:
            print(f"Base64解码失败: {e}")
            # 修复padding
            encrypted_data = encrypted_data.strip()
            encrypted_data = re.sub(r'[^A-Za-z0-9+/=]', '', encrypted_data)
            encrypted_data = encrypted_data.rstrip('=')
            padding_needed = 4 - (len(encrypted_data) % 4)
            if padding_needed and padding_needed != 4:
                encrypted_data += '=' * padding_needed
            try:
                ciphertext = base64.b64decode(encrypted_data)
                print(f"修复padding后Base64解码成功")
            except:
                print("Base64解码彻底失败")
                return None
        
        # Base64解析IV
        try:
            iv_bytes = base64.b64decode(iv)
            print(f"IV解码成功，长度: {len(iv_bytes)}")
        except Exception as e:
            print(f"IV解码失败: {e}")
            return None
        
        # UTF-8解析密钥
        try:
            key_bytes = key.encode('utf-8')
            print(f"密钥编码成功，长度: {len(key_bytes)}")
            
            # 确保密钥长度为16字节
            if len(key_bytes) != 16:
                if len(key_bytes) < 16:
                    key_bytes += b'\x00' * (16 - len(key_bytes))
                    print(f"密钥长度不足，填充至16字节")
                else:
                    key_bytes = key_bytes[:16]
                    print(f"密钥长度过长，截取前16字节")
        except Exception as e:
            print(f"密钥编码失败: {e}")
            return None
        
        # AES解密 - 使用CBC模式
        try:
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
            decrypted_bytes = cipher.decrypt(ciphertext)
            print(f"AES解密成功，解密数据长度: {len(decrypted_bytes)}")
            
            # 尝试不同的padding移除方式
            # 使用函数列表而不是lambda表达式，避免类型错误
            def remove_zero_padding(b):
                return b.rstrip(b'\x00')
            
            def no_removal(b):
                return b
            
            def remove_pkcs7_padding(b):
                if b and len(b) > 0:
                    padding_len = b[-1]
                    if 0 < padding_len <= 16:  # PKCS7 padding长度在1-16之间
                        if b[-padding_len:] == bytes([padding_len] * padding_len):
                            return b[:-padding_len]
                return b
            
            removal_functions = [remove_zero_padding, no_removal, remove_pkcs7_padding]
            
            for removal in removal_functions:
                try:
                    cleaned_bytes = removal(decrypted_bytes)
                    # 转换为UTF-8字符串
                    try:
                        decrypted_text = cleaned_bytes.decode('utf-8')
                        print(f"解密成功，尝试padding移除方法: {removal.__name__}")
                        return decrypted_text
                    except UnicodeDecodeError:
                        try:
                            decrypted_text = cleaned_bytes.decode('utf-8', errors='ignore')
                            print(f"解密成功（忽略错误），尝试padding移除方法: {removal.__name__}")
                            return decrypted_text
                        except:
                            print(f"UTF-8解码失败，尝试下一个padding移除方法")
                            continue
                except Exception as e:
                    print(f"padding移除失败: {e}")
                    continue
            
            print("所有padding移除方法都失败")
            # 最后尝试直接转换为字符串
            try:
                return str(decrypted_bytes)
            except:
                return None
        except Exception as e:
            print(f"AES解密失败: {e}")
            return None
    
    def _decrypt_with_alternative_methods(self, encrypted_data: str, key: str, iv: str) -> Optional[str]:
        """
        使用备选方法解密内容
        
        Args:
            encrypted_data: 加密数据
            key: 从页面提取的解密密钥
            iv: 从页面提取的初始化向量
            
        Returns:
            解密后的内容
        """
        print(f"尝试备选解密方法: 数据长度={len(encrypted_data)}, key={key}, iv={iv}")
        
        try:
            # 备选解密方法1: 尝试不同的密钥/IV组合
            alternative_keys = [
                key,  # 原始密钥
                "encryptedDatastr",  # 默认key
                "3rptdNnUDS4FAypFfpoIpA==",  # 备选iv作为key
                "5w9sgjdqHHEw0Fjc3C2qHg==",  # 默认iv
            ]
            
            alternative_ivs = [
                iv,  # 原始iv
                "5w9sgjdqHHEw0Fjc3C2qHg==",  # 默认iv
                "3rptdNnUDS4FAypFfpoIpA==",  # 备选iv
                "encryptedDatastr",  # key作为iv（不太可能但值得一试）
            ]
            
            for alt_key in alternative_keys:
                for alt_iv in alternative_ivs:
                    # 尝试解密
                    decrypted = self._decrypt_with_real_key(encrypted_data, alt_key, alt_iv)
                    if decrypted and len(decrypted) > 50:
                        # 检查解密内容是否合理
                        chinese_chars = len([c for c in decrypted if '\u4e00' <= c <= '\u9fff'])
                        if chinese_chars > 10:  # 包含足够的中文字符
                            print(f"备选方法成功: key={alt_key}, iv={alt_iv}, 中文字符数={chinese_chars}")
                            return decrypted
            
            # 备选解密方法2: 尝试使用ECB模式
            try:
                print("尝试ECB模式解密...")
                ciphertext = base64.b64decode(encrypted_data, validate=False)
                key_bytes = key.encode('utf-8')
                
                # 确保密钥长度为16字节
                if len(key_bytes) != 16:
                    if len(key_bytes) < 16:
                        key_bytes += b'\x00' * (16 - len(key_bytes))
                    else:
                        key_bytes = key_bytes[:16]
                
                cipher = AES.new(key_bytes, AES.MODE_ECB)
                decrypted_bytes = cipher.decrypt(ciphertext)
                
                # 转换为UTF-8字符串
                try:
                    decrypted_text = decrypted_bytes.rstrip(b'\x00').decode('utf-8')
                    chinese_chars = len([c for c in decrypted_text if '\u4e00' <= c <= '\u9fff'])
                    if chinese_chars > 10:
                        print(f"ECB模式解密成功，中文字符数={chinese_chars}")
                        return decrypted_text
                except UnicodeDecodeError:
                    print("ECB模式解密后UTF-8解码失败")
            except Exception as e:
                print(f"ECB模式解密失败: {e}")
            
            print("所有备选解密方法均失败")
            return None
            
        except Exception as e:
            print(f"备选解密方法出错: {e}")
            return None
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 从URL中提取小说ID，格式为 "26_34976"
        match = re.search(r'/(\d+_\d+)/', url)
        if match:
            return match.group(1)
        return "unknown"
    

    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的文本内容
        """
        content = html_content
        try:
            # 解码HTML实体 - 这是关键步骤
            import html
            content = html.unescape(content)
            
            # 移除所有HTML标签，但保留内容
            cleaned = re.sub(r'<[^>]+>', '', content)
            
            # 处理常见的HTML实体
            cleaned = cleaned.replace('&nbsp;', ' ')
            cleaned = cleaned.replace('&lt;', '<')
            cleaned = cleaned.replace('&gt;', '>')
            cleaned = cleaned.replace('&amp;', '&')
            cleaned = cleaned.replace('&quot;', '"')
            cleaned = cleaned.replace('&#39;', "'")
            cleaned = cleaned.replace('&ldquo;', '"')
            cleaned = cleaned.replace('&rdquo;', '"')
            cleaned = cleaned.replace('&lsquo;', "'")
            cleaned = cleaned.replace('&rsquo;', "'")
            cleaned = cleaned.replace('&mdash;', '—')
            cleaned = cleaned.replace('&ndash;', '–')
            
            # 处理Unicode数字实体
            cleaned = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), cleaned)
            
            # 清理多余的空白字符，但保留段落结构
            # 将多个连续空格替换为单个空格
            cleaned = re.sub(r'[ \t]+', ' ', cleaned)
            
            # 保留换行符，但去掉多余的空行
            cleaned = re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', cleaned)
            
            # 去除首尾空白
            cleaned = cleaned.strip()
            
            # 如果内容看起来像加密数据或乱码，返回空字符串
            if len(cleaned) < 10 or cleaned.count(' ') > len(cleaned) * 0.8:
                print("内容清理后仍然异常，可能解密失败")
                return ""
            
            # 检查是否有中文字符，如果没有则可能解密失败
            chinese_chars = len([c for c in cleaned if '\u4e00' <= c <= '\u9fff'])
            if chinese_chars < 5:
                print(f"清理后内容中文字符太少: {chinese_chars}个，可能解密失败")
                print(f"清理后内容前200字符: {cleaned[:200]}...")
                # 不返回空字符串，继续尝试，因为有些章节可能确实较少
            
            return cleaned
            
        except Exception as e:
            print(f"清理HTML内容失败: {e}")
            return content