"""
hxtxt38.lol 小说网站解析器 - 支持AES解密
继承自 BaseParser，使用统一的crypto_utils解密工具
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from ..utils.crypto_utils import AESCipher, extract_encryption_keys, is_encrypted_content
from .base_parser_v2 import BaseParser


class HXtxt38Parser(BaseParser):
    """hxtxt38.lol 小说解析器 - 支持AES解密"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 加密密钥（从页面动态获取）
        self.aei = None  # aes iv
        self.aek = None  # aes key
        self.enc = True  # 是否加密
    
    # 基本信息
    name = "799415.hxtxt38.lol"
    description = "799415.hxtxt38.lol 小说解析器 - 支持AES解密"
    base_url = "https://799415.hxtxt38.lol"
    
    # 正则表达式配置
    title_reg = [
        r'<h1 class="bookname d">([^<]+)</h1>',
        r'<title>([^<]+)</title>'
    ]
    
    content_reg = [
        r'<div[^>]*?id="chaptercontent"[^>]*?class="d"[^>]*?>([\s\S]*?)</div>',
        r'<div[^>]*?class="d"[^>]*?id="chaptercontent"[^>]*?>([\s\S]*?)</div>'
    ]
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_remove_external_links",  # 先移除外部链接
        "_clean_html_tags",  # 再去除HTML标签
        "_clean_text_content"  # 最后清理文本内容
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配hxtxt38.lol的URL格式
        根据分析，书籍详情页URL格式为：https://799415.hxtxt38.lol/show.php?itemid=17621
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/show.php?itemid={novel_id}"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 空实现，因为hxtxt38主要是单篇阅读
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _extract_encryption_keys(self, content: str) -> Dict[str, str]:
        """
        从页面内容中提取加密密钥
        
        Args:
            content: 页面内容
            
        Returns:
            加密密钥字典 {aei: iv, aek: key}
        """
        # 使用统一的密钥提取工具
        aei, aek = extract_encryption_keys(content)
        
        keys = {
            'aei': aei,
            'aek': aek,
            'enc': 'true'  # 字符串类型，与返回值类型一致
        }
        
        print(f"提取到加密密钥: aei={keys['aei']}, aek={keys['aek']}, enc={keys['enc']}")
        
        return keys
    
    def _extract_encrypted_content(self, content: str) -> Optional[str]:
        """
        提取并解密加密内容
        
        Args:
            content: 章节页面内容
            
        Returns:
            解密后的内容
        """
        # 首先提取加密密钥
        keys = self._extract_encryption_keys(content)
        if not keys or 'aei' not in keys or 'aek' not in keys:
            print("无法提取加密密钥")
            return None
        
        # 提取内容加密内容
        content_match = re.search(r'<div[^>]*?id="chaptercontent"[^>]*?class="d"[^>]*?>([\s\S]*?)</div>', content)
        if not content_match:
            print("无法提取加密内容")
            return None
        
        encrypted_content = content_match.group(1).strip()
        print(f"提取到加密内容，长度: {len(encrypted_content)}")
        
        # 解密内容
        decrypted_content = self._decrypt_content(encrypted_content, keys['aek'], keys['aei'])
        if decrypted_content:
            print("内容解密成功")
            return decrypted_content
        else:
            print("内容解密失败")
            return None
    
    def _extract_encrypted_title(self, content: str) -> Optional[str]:
        """
        提取并解密加密标题
        
        Args:
            content: 章节页面内容
            
        Returns:
            解密后的标题
        """
        # 首先提取加密密钥
        keys = self._extract_encryption_keys(content)
        if not keys or 'aei' not in keys or 'aek' not in keys:
            print("无法提取加密密钥")
            return None
        
        # 提取标题加密内容 - 从<title>标签中提取
        title_match = re.search(r'<title>([^<]+)</title>', content)
        if title_match:
            encrypted_title = title_match.group(1).strip()
            print(f"提取到加密标题: {encrypted_title}")
            decrypted_title = self._decrypt_content(encrypted_title, keys['aek'], keys['aei'])
            if decrypted_title:
                print(f"解密标题成功: {decrypted_title}")
                return decrypted_title
            else:
                print("标题解密失败")
        
        # 如果<title>标签解密失败，尝试从<h1>标签提取
        title_match = re.search(r'<h1 class="bookname d">([^<]+)</h1>', content)
        if title_match:
            encrypted_title = title_match.group(1).strip()
            print(f"从h1标签提取到加密标题: {encrypted_title}")
            decrypted_title = self._decrypt_content(encrypted_title, keys['aek'], keys['aei'])
            if decrypted_title:
                print(f"h1标签解密标题成功: {decrypted_title}")
                return decrypted_title
            else:
                print("h1标签标题解密失败")
        
        return None
    

    
    def _decrypt_content(self, encrypted_data: str, key: str, iv: str) -> Optional[str]:
        """
        解密内容 - 使用统一的AESCipher工具
        
        Args:
            encrypted_data: 加密数据
            key: 密钥
            iv: 初始化向量
            
        Returns:
            解密后的内容
        """
        try:
            # 使用统一的AES解密工具
            cipher = AESCipher(key, iv)
            decrypted_text = cipher.decrypt(encrypted_data)
            
            # 检查解密结果是否有效
            if decrypted_text and decrypted_text != encrypted_data:
                print(f"解密成功，长度: {len(decrypted_text)} 字符")
                return decrypted_text
            else:
                print("解密失败或内容未加密")
                return None
                
        except Exception as e:
            print(f"解密失败: {e}")
            return None
    
    def _contains_chinese_text(self, text: str) -> bool:
        """检查文本是否包含中文"""
        import re
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return len(chinese_chars) > 10  # 至少有10个中文字符
    
    def _remove_external_links(self, content: str) -> str:
        """
        移除外部链接，特别是成人网址导航等广告链接
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return ""
        
        # 移除特定格式的外部链接
        patterns_to_remove = [
            # 移除 <a href="https://manage.izfp6.buzz/go/" data-id="9032" target="_blank">更多免费小说请前往：成人网址导航</a>
            r'<a[^>]*?href="[^"]*?manage\.izfp6\.buzz/go/[^"]*?"[^>]*?>[^<]*?更多免费小说请前往：成人网址导航[^<]*?</a>',
            # 移除类似的成人网址导航链接
            r'<a[^>]*?href="[^"]*?成人网址导航[^"]*?"[^>]*?>[^<]*?</a>',
            # 移除所有包含"成人网址导航"的链接
            r'<a[^>]*?>[^<]*?成人网址导航[^<]*?</a>',
            # 移除常见的广告链接
            r'<a[^>]*?href="[^"]*?(buzz|ad|ads|promo|promotion)[^"]*?"[^>]*?>[^<]*?</a>',
            # 移除包含"更多免费小说请前往"的文本
            r'更多免费小说请前往：成人网址导航',
            # 移除所有外部链接（保留相对链接）
            r'<a[^>]*?href="https?://[^"]*?"[^>]*?>[^<]*?</a>',
        ]
        
        cleaned_content = content
        for pattern in patterns_to_remove:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE)
        
        # 移除空的段落标签
        cleaned_content = re.sub(r'<p[^>]*?>\s*</p>', '', cleaned_content)
        cleaned_content = re.sub(r'<div[^>]*?>\s*</div>', '', cleaned_content)
        
        print(f"外部链接清理完成，原始长度: {len(content)}, 清理后长度: {len(cleaned_content)}")
        
        return cleaned_content
    
    def _clean_html_tags(self, content: str) -> str:
        """
        清理HTML标签，提取纯文本内容
        
        Args:
            content: 原始HTML内容
            
        Returns:
            清理后的纯文本内容
        """
        if not content:
            return ""
        
        # 移除所有HTML标签（包括<p>、<div>等）
        clean_text = re.sub(r'<[^>]+>', '', content)
        
        # 替换HTML实体
        clean_text = clean_text.replace('&nbsp;', ' ').replace('\xa0', ' ')
        
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # 移除首尾空白
        clean_text = clean_text.strip()
        
        print(f"HTML标签清理完成，原始长度: {len(content)}, 清理后长度: {len(clean_text)}")
        
        return clean_text
    
    def _clean_text_content(self, content: str) -> str:
        """
        清理文本内容，移除多余空白和特殊字符
        
        Args:
            content: 原始文本内容
            
        Returns:
            清理后的文本内容
        """
        if not content:
            return ""
        
        # 清理多余空白字符
        clean_text = re.sub(r'\s+', ' ', content)
        
        # 移除首尾空白
        clean_text = clean_text.strip()
        
        # 清理特殊字符和不可见字符
        clean_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_text)
        
        print(f"文本内容清理完成，原始长度: {len(content)}, 清理后长度: {len(clean_text)}")
        
        return clean_text
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，确保解密功能被自动调用
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说内容字典
        """
        # 生成小说URL
        novel_url = self.get_novel_url(novel_id)
        
        print(f"=== 开始解析 hxtxt38.lol 小说 ===")
        print(f"目标URL: {novel_url}")
        
        try:
            # 获取小说页面内容
            content = self._get_url_content(novel_url)
            if not content:
                raise Exception("无法获取页面内容")
            
            print(f"页面获取成功，长度: {len(content)} 字符")
            
            # 提取标题（先尝试解密）
            title = ""
            # 首先尝试解密标题
            decrypted_title = self._extract_encrypted_title(content)
            if decrypted_title:
                title = decrypted_title
            
            # 如果解密标题失败，尝试直接提取
            if not title:
                title = self._extract_with_regex(content, self.title_reg)
                if title:
                    print(f"直接提取标题: {title}")
                else:
                    # 尝试从<title>标签提取
                    title_match = re.search(r'<title>([^<]+)</title>', content)
                    if title_match:
                        title = title_match.group(1).strip()
                    else:
                        # 从URL提取小说ID作为标题
                        title = f"小说_{novel_id}"
            
            print(f"小说标题: {title}")
            
            if not title:
                raise Exception("无法提取小说标题")
            
            # 提取并解密内容
            novel_content = self._extract_encrypted_content(content)
            if not novel_content:
                raise Exception("无法获取小说内容")
            
            # 执行爬取后处理函数
            processed_content = self._execute_after_crawler_funcs(novel_content)
            
            return {
                'title': title,
                'author': self.novel_site_name or self.name,
                'novel_id': novel_id,
                'url': novel_url,
                'description': "",  # 单篇小说可能没有简介
                'status': "连载中",
                'chapters': [{
                    'chapter_number': 1,
                    'title': title,
                    'content': processed_content,
                    'url': novel_url
                }]
            }
                
        except Exception as e:
            print(f"解析失败: {e}")
            raise Exception(f"解析小说失败: {e}")
    
    def parse_single_novel(self, novel_url: str) -> Dict[str, Any]:
        """
        解析单篇小说的完整流程（用于测试和独立调用）
        
        Args:
            novel_url: 小说URL
            
        Returns:
            小说内容字典
        """
        # 从URL中提取小说ID
        novel_id_match = re.search(r'itemid=(\d+)', novel_url)
        if novel_id_match:
            novel_id = novel_id_match.group(1)
            return self.parse_novel_detail(novel_id)
        else:
            raise Exception(f"无法从URL中提取小说ID: {novel_url}")
    
    def test_parser(self, novel_url: str) -> Dict[str, Any]:
        """
        测试解析器功能
        
        Args:
            novel_url: 测试小说URL
            
        Returns:
            解析结果
        """
        return self.parse_single_novel(novel_url)
    
    def run_test(self, test_url: Optional[str] = None):
        """
        运行测试
        
        Args:
            test_url: 测试URL，如果为None则使用默认测试URL
        """
        if test_url is None:
            # 使用提供的测试URL
            test_url = "https://799415.hxtxt38.lol/show.php?itemid=17621"
        
        result = self.test_parser(test_url)
        
        if "error" in result:
            print(f"测试失败: {result['error']}")
        else:
            print(f"测试成功!")
            print(f"小说标题: {result['title']}")
            print(f"作者: {result['author']}")
            print(f"小说ID: {result['novel_id']}")
            print(f"章节数量: {len(result['chapters'])}")
            print(f"状态: {result['status']}")
            
            # 显示章节内容预览
            if result['chapters']:
                chapter = result['chapters'][0]
                print(f"章节标题: {chapter['title']}")
                if chapter['content']:
                    print(f"内容预览: {chapter['content'][:200]}...")


# 测试代码
if __name__ == "__main__":
    # 创建解析器实例
    parser = HXtxt38Parser()
    
    # 运行测试
    parser.run_test()