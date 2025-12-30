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
    
    def _is_multi_chapter(self, content: str) -> bool:
        """
        检查是否为多章节书籍
        
        Args:
            content: 页面内容
            
        Returns:
            是否为多章节书籍
        """
        # 检查是否存在<div id="list">标签
        has_list_div = bool(re.search(r'<div[^>]*?id="list"[^>]*?>', content))
        
        if has_list_div:
            print("检测到<div id='list'>标签，判断为多章节书籍")
            return True
        else:
            print("未检测到<div id='list'>标签，判断为单章节书籍")
            return False
    
    def _extract_chapter_list(self, content: str) -> List[Dict[str, Any]]:
        """
        提取章节列表信息
        
        Args:
            content: 页面内容
            
        Returns:
            章节信息列表
        """
        chapters = []
        
        # 查找<div id="list">标签
        list_match = re.search(r'<div[^>]*?id="list"[^>]*?>([\s\S]*?)</div>', content)
        if not list_match:
            print("未找到<div id='list'>标签，可能为单章节书籍")
            return chapters
        
        list_content = list_match.group(1)
        print("找到<div id='list'>标签，开始解析多章节书籍")
        
        # 提取加密密钥
        keys = self._extract_encryption_keys(content)
        if not keys or 'aei' not in keys or 'aek' not in keys:
            print("无法提取加密密钥")
            return chapters
        
        # 查找所有<span class="d">标签 - 专门针对章节列表的解密
        span_pattern = r'<span[^>]*?class="d"[^>]*?>(.*?)</span>'
        span_matches = re.findall(span_pattern, list_content)
        
        print(f"找到 {len(span_matches)} 个加密的span标签")
        
        chapter_number = 1
        for span_content in span_matches:
            encrypted_content = span_content.strip()
            if not encrypted_content:
                continue
                
            print(f"处理第 {chapter_number} 个加密内容: {encrypted_content[:50]}...")
            
            # 尝试解密span内容
            decrypted_content = self._decrypt_content(encrypted_content, keys['aek'], keys['aei'])
            
            if decrypted_content:
                print(f"解密成功: {decrypted_content[:100]}...")
                
                # 根据您的描述，解密后应该包含<a>标签
                # <a>标签中的href是章节URL，文字是章节标题
                a_match = re.search(r'<a[^>]*?href="([^"]*?)"[^>]*?>([\s\S]*?)</a>', decrypted_content)
                if a_match:
                    chapter_url = urljoin(self.base_url, a_match.group(1))
                    a_content = a_match.group(2).strip()
                    
                    # 从<dd>标签中提取章节标题
                    dd_match = re.search(r'<dd[^>]*?>([^<]*?)</dd>', a_content)
                    if dd_match:
                        chapter_title = dd_match.group(1).strip()
                    else:
                        # 如果没有<dd>标签，直接使用<a>标签内容
                        chapter_title = re.sub(r'<[^>]+>', '', a_content).strip()
                    
                    # 清理标题中的HTML实体
                    chapter_title = chapter_title.replace('&nbsp;', ' ').replace('\xa0', ' ')
                    chapter_title = re.sub(r'\s+', ' ', chapter_title).strip()
                    
                    if chapter_title:
                        chapters.append({
                            'chapter_number': chapter_number,
                            'title': chapter_title,
                            'url': chapter_url,
                            'content': ''  # 稍后获取内容
                        })
                        chapter_number += 1
                        print(f"提取章节 {chapter_number-1}: {chapter_title} -> {chapter_url}")
                    else:
                        print("章节标题为空，跳过")
                else:
                    # 如果没有找到标准的<a>标签，尝试其他格式
                    print(f"未找到标准的<a>标签，尝试其他格式解析...")
                    
                    # 简化处理：直接提取文本作为章节标题，生成默认URL
                    chapter_title = re.sub(r'<[^>]+>', '', decrypted_content).strip()
                    chapter_title = chapter_title.replace('&nbsp;', ' ').replace('\xa0', ' ')
                    chapter_title = re.sub(r'\s+', ' ', chapter_title).strip()
                    
                    if chapter_title:
                        # 使用小说详情页URL加上章节编号作为章节URL
                        chapter_url = f"{self.base_url}/chapter_{chapter_number}.html"
                        
                        chapters.append({
                            'chapter_number': chapter_number,
                            'title': chapter_title,
                            'url': chapter_url,
                            'content': ''
                        })
                        chapter_number += 1
                        print(f"提取章节 {chapter_number-1}: {chapter_title} -> {chapter_url}")
                    else:
                        print("无法提取章节标题，跳过")
            else:
                print(f"解密失败，跳过此内容")
        
        print(f"总共提取到 {len(chapters)} 个章节")
        return chapters
    
    def _get_chapter_content(self, chapter_url: str, keys: Dict[str, str]) -> Optional[str]:
        """
        获取章节内容
        
        Args:
            chapter_url: 章节URL
            keys: 解密密钥
            
        Returns:
            解密后的章节内容
        """
        try:
            # 获取章节页面内容
            chapter_content = self._get_url_content(chapter_url)
            if not chapter_content:
                print(f"无法获取章节页面内容: {chapter_url}")
                return None
            
            # 提取并解密内容
            content_match = re.search(r'<div[^>]*?id="chaptercontent"[^>]*?class="d"[^>]*?>([\s\S]*?)</div>', chapter_content)
            if not content_match:
                print("无法提取章节内容")
                return None
            
            encrypted_content = content_match.group(1).strip()
            print(f"提取到章节加密内容，长度: {len(encrypted_content)}")
            
            # 解密内容
            decrypted_content = self._decrypt_content(encrypted_content, keys['aek'], keys['aei'])
            if decrypted_content:
                print("章节内容解密成功")
                # 执行爬取后处理函数
                processed_content = self._execute_after_crawler_funcs(decrypted_content)
                return processed_content
            else:
                print("章节内容解密失败")
                return None
                
        except Exception as e:
            print(f"获取章节内容失败: {e}")
            return None
    
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
        重写小说详情解析方法，支持单章节和多章节书籍
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说内容字典
        """
        
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
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
            
            # 检查是否为多章节书籍
            is_multi_chapter = self._is_multi_chapter(content)
            print(f"是否为多章节书籍: {is_multi_chapter}")
            
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
            
            # 提取加密密钥
            keys = self._extract_encryption_keys(content)
            if not keys or 'aei' not in keys or 'aek' not in keys:
                raise Exception("无法提取加密密钥")
            
            chapters = []
            
            if is_multi_chapter:
                # 多章节处理
                print("=== 处理多章节书籍 ===")
                
                # 提取章节列表
                chapter_list = self._extract_chapter_list(content)
                if not chapter_list:
                    print("无法提取章节列表，尝试作为单章节处理")
                    # 如果无法提取章节列表，可能是判断错误，尝试作为单章节处理
                    novel_content = self._extract_encrypted_content(content)
                    if novel_content:
                        processed_content = self._execute_after_crawler_funcs(novel_content)
                        chapters.append({
                            'chapter_number': 1,
                            'title': title,
                            'content': processed_content,
                            'url': novel_url
                        })
                    else:
                        raise Exception("无法提取章节列表且无法获取单章节内容")
                else:
                    print(f"找到 {len(chapter_list)} 个章节")
                    
                    # 获取每个章节的内容
                    for chapter in chapter_list:
                        print(f"正在获取章节内容: {chapter['title']}")
                        chapter_content = self._get_chapter_content(chapter['url'], keys)
                        if chapter_content:
                            chapter['content'] = chapter_content
                            chapters.append(chapter)
                        else:
                            print(f"获取章节内容失败: {chapter['title']}")
                            # 即使获取内容失败，也保留章节信息
                            chapter['content'] = "内容获取失败"
                            chapters.append(chapter)
                
            else:
                # 单章节处理
                print("=== 处理单章节书籍 ===")
                
                # 提取并解密内容
                novel_content = self._extract_encrypted_content(content)
                if not novel_content:
                    raise Exception("无法获取小说内容")
                
                # 执行爬取后处理函数
                processed_content = self._execute_after_crawler_funcs(novel_content)
                
                chapters.append({
                    'chapter_number': 1,
                    'title': title,
                    'content': processed_content,
                    'url': novel_url
                })
            
            return {
                'title': title,
                'author': self.novel_site_name or self.name,
                'novel_id': novel_id,
                'url': novel_url,
                'description': "",  # 可能没有简介
                'status': "连载中",
                'chapters': chapters
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