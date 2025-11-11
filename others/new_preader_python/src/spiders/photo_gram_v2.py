"""
PhotoGram网站解析器 v2
支持 https://www.photo-gram.com/ 网站的小说解析
整合了test.py中的成功解密逻辑
"""

import re
import base64
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import zlib
import gzip
from .base_parser_v2 import BaseParser


class PhotoGramParser(BaseParser):
    """PhotoGram网站解析器 v2"""
    
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
        self.iv_b64 = "FMCqVWeARJd9AY9PYm2csw=="
    
    # 基本信息
    name = "PhotoGram"
    description = "PhotoGram多章节小说解析器"
    base_url = "https://www.photo-gram.com"
    
    # 正则表达式配置 - 章节列表页
    title_reg = [
        r'<h1[^>]*class="bookTitle"[^>]*>([^<]+)</h1>'
    ]
    
    # 章节列表正则 - 通用匹配
    chapter_link_reg = [
        r'<dl[^>]*class="panel-body panel-chapterlist"[^>]*id="newlist"[^>]*>.*?<dd[^>]*class="col-sm-4"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>\s*</dd>'
    ]
    status_reg = [
        r'<p[^>]*class="booktag"[^>]*>(.*?)</p>'
    ]
    
    # 简介提取
    description_reg = [
        r'<p[^>]*id="bookIntro"[^>]*class="text-justify"[^>]*>(.*?)</p>'
    ]
    
    # 内容页正则 - 用于提取加密脚本（booktxthtml包含真正的加密内容）
    content_reg = [
        # 精确匹配格式：<script>  $('#booktxthtml').html(x("encrypted_data","key","iv"));</script>
        r"<script>\s*\$\(['\"]*#booktxthtml['\"]*\)\.html\(x\(['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"]\)\);</script>"
    ]
    
    # 书籍类型配置
    book_type = ["多章节"]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配PhotoGram网站的URL格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/read/{novel_id}/"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 空实现，因为PhotoGram主要是通过章节列表访问
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
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
        # 提取章节列表
        chapters_list = self._extract_chapters(content, novel_url)
        
        if not chapters_list:
            raise Exception("无法提取章节列表")
        
        print(f"开始处理 [ {title} ] - 找到 {len(chapters_list)} 个章节")
        
        # 解析每个章节内容
        chapters_with_content = []
        for i, chapter_info in enumerate(chapters_list):
            try:
                chapter_url = chapter_info['url']
                chapter_content = self.parse_chapter_content(chapter_url)
                
                if chapter_content:
                    chapters_with_content.append({
                        'chapter_number': i + 1,
                        'title': chapter_info['title'],
                        'content': chapter_content,
                        'url': chapter_url
                    })
                    print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 完成")
                else:
                    print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 获取内容失败")
                    
                # 章节间延迟
                import time
                time.sleep(1)
                    
            except Exception as e:
                print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 错误: {e}")
        
        if not chapters_with_content:
            raise Exception("无法获取任何章节内容")
        
        # 提取简介和状态
        description = self._extract_description(content)
        status = self._extract_status(content)
        
        return {
            'title': title,
            'author': self.novel_site_name or self.name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'description': description,
            'status': status,
            'chapters': chapters_with_content
        }
    
    def _extract_chapters(self, content: str, novel_url: str) -> List[Dict[str, Any]]:
        """
        从章节列表页面提取章节信息
        
        Args:
            content: 章节列表页面内容
            novel_url: 小说URL
            
        Returns:
            章节信息列表
        """
        chapters = []
        
        # 精确匹配 <dl class="panel-body panel-chapterlist" id="newlist"> 容器
        # 提取这个容器内的所有内容
        newlist_pattern = r'<dl[^>]*class="panel-body panel-chapterlist"[^>]*id="newlist"[^>]*>(.*?)</dl>'
        newlist_match = re.search(newlist_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not newlist_match:
            print("未找到 <dl class=\"panel-body panel-chapterlist\" id=\"newlist\"> 容器")
            return chapters
        
        newlist_content = newlist_match.group(1)
        
        # 在容器内查找 <dd class="col-sm-4"><a> 标签
        chapter_pattern = r'<dd[^>]*class="col-sm-4"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>\s*</dd>'
        matches = re.finditer(chapter_pattern, newlist_content, re.DOTALL)
        
        for match in matches:
            chapter_url = match.group(1).strip()
            chapter_title = match.group(2).strip()
            
            # 清理章节标题
            chapter_title = re.sub(r'<[^>]+>', '', chapter_title)
            chapter_title = re.sub(r'\\s+', ' ', chapter_title).strip()
            
            # 确保URL是完整的
            if not chapter_url.startswith('http'):
                chapter_url = urljoin(self.base_url, chapter_url)
            
            chapters.append({
                "title": chapter_title,
                "url": chapter_url
            })
        
        print(f"从 <dl id=\"newlist\"> 中提取到 {len(chapters)} 个章节")
        return chapters
        
        # 提取章节链接和标题
        for chapter_pattern in self.chapter_link_reg:
            matches = re.finditer(chapter_pattern, content, re.DOTALL)
            for match in matches:
                chapter_url = match.group(1).strip()
                chapter_title = match.group(2).strip()
                
                # 清理章节标题
                chapter_title = re.sub(r'<[^>]+>', '', chapter_title)
                chapter_title = re.sub(r'\s+', ' ', chapter_title).strip()
                
                # 确保URL是完整的
                if not chapter_url.startswith('http'):
                    chapter_url = urljoin(self.base_url, chapter_url)
                
                chapters.append({
                    "title": chapter_title,
                    "url": chapter_url
                })
        
        return chapters
    
    def _extract_description(self, content: str) -> str:
        """提取小说简介"""
        # 使用配置的正则表达式提取简介
        for pattern in self.description_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                desc = match.group(1).strip()
                # 清理HTML标签
                desc = re.sub(r'<[^>]+>', '', desc)
                desc = re.sub(r'\s+', ' ', desc)
                return desc.strip()
        return ""
    
    def _extract_status(self, content: str) -> str:
        """提取小说状态"""
        # 使用配置的正则表达式提取状态
        for pattern in self.status_reg:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                status_html = match.group(1).strip()
                # 提取所有标签中的文字部分
                status_texts = re.findall(r'>([^<]+)<', status_html)
                if status_texts:
                    # 用逗号连接所有文字
                    return ', '.join([text.strip() for text in status_texts if text.strip()])
        return "连载中"
    
    def parse_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        解析章节内容（包含子章节处理）
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容文本（包含所有子章节内容）
        """
        print(f"正在获取章节内容: {chapter_url}")
        
        # 获取主章节内容
        main_content = self._get_single_chapter_content(chapter_url)
        if not main_content:
            print("无法获取主章节内容")
            return None
        
        # 检查是否有子章节
        sub_contents = self._get_sub_chapters_content(chapter_url)
        
        # 合并所有内容
        all_content = main_content
        if sub_contents:
            print(f"找到 {len(sub_contents)} 个子章节")
            for i, sub_content in enumerate(sub_contents):
                print(f"  子章节 {i+1}: {sub_content[:50]}...")
                all_content += "\n\n" + sub_content
        
        return all_content
    
    def _get_single_chapter_content(self, chapter_url: str) -> Optional[str]:
        """
        获取单个页面的章节内容（不包含子章节）
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            章节内容文本
        """
        content = self._get_url_content(chapter_url)
        
        if not content:
            print("无法获取章节页面内容")
            return None
        
        print(f"获取到章节页面，长度: {len(content)} 字符")
        
        # 提取加密内容并解密
        encrypted_content = self._extract_encrypted_content(content)
        if encrypted_content:
            print("成功解密内容")
            return encrypted_content
        
        print("加密内容提取失败")
        return None
    
    def _get_sub_chapters_content(self, chapter_url: str) -> List[str]:
        """
        获取章节的所有子章节内容
        
        Args:
            chapter_url: 章节URL
            
        Returns:
            子章节内容列表
        """
        sub_contents = []
        current_url = chapter_url
        visited_urls = set()  # 避免循环
        
        while current_url and current_url not in visited_urls:
            visited_urls.add(current_url)
            
            # 获取当前页面内容
            content = self._get_url_content(current_url)
            if not content:
                break
            
            # 提取slink和xlink
            slink, xlink = self._extract_slink_xlink(content)
            if not xlink:
                print(f"无法从页面提取xlink: {current_url}")
                break
            
            print(f"找到链接 - slink: {slink}, xlink: {xlink}")
            
            # 检查xlink是否是当前章节的子章节
            if not self._is_same_chapter(current_url, xlink):
                print(f"xlink指向其他章节，停止子章节爬取: {xlink}")
                break
            
            # 构建完整的xlink URL
            if xlink.startswith('/'):
                next_url = urljoin(self.base_url, xlink)
            else:
                next_url = xlink
            
            # 如果是下一个页面，获取内容
            if next_url != current_url:
                sub_content = self._get_single_chapter_content(next_url)
                if sub_content:
                    sub_contents.append(sub_content)
                    current_url = next_url
                    # 添加延迟避免请求过快
                    import time
                    time.sleep(1)
                else:
                    print(f"无法获取子章节内容: {next_url}")
                    break
            else:
                break
        
        return sub_contents
    
    def _extract_slink_xlink(self, content: str) -> tuple:
        """
        从页面内容中提取slink和xlink
        
        Args:
            content: 页面内容
            
        Returns:
            (slink, xlink) 元组
        """
        # 匹配 <script>var slink = '...', xlink = '...';</script> 格式
        pattern = r"<script>\s*var\s+slink\s*=\s*['\"]([^'\"]+)['\"],\s*xlink\s*=\s*['\"]([^'\"]+)['\"]\s*;</script>"
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        
        if match:
            slink = match.group(1)
            xlink = match.group(2)
            
            # 去除转义字符，如 \/ -> /
            if slink:
                slink = slink.replace('\\/', '/')
            if xlink:
                xlink = xlink.replace('\\/', '/')
            
            return slink, xlink
        
        return None, None
    
    def _is_same_chapter(self, current_url: str, xlink: str) -> bool:
        """
        判断xlink是否与当前URL属于同一章节
        
        Args:
            current_url: 当前页面URL
            xlink: 下一页链接
            
        Returns:
            是否属于同一章节
        """
        # 从路径中提取章节标识
        # 例如: /eddli/iglk.html -> iglk
        #       /eddli/iglk_1.html -> iglk
        #       /eddli/igcl.html -> igcl
        
        def extract_chapter_id(url_or_path):
            # 如果是完整URL，先提取路径部分
            if url_or_path.startswith('http'):
                from urllib.parse import urlparse
                parsed = urlparse(url_or_path)
                path = parsed.path
            else:
                path = url_or_path
            
            # 移开头的斜杠
            path = path.lstrip('/')
            # 分割路径
            parts = path.split('/')
            if len(parts) >= 2:
                filename = parts[-1]  # 获取文件名
                # 移除扩展名
                name_without_ext = filename.replace('.html', '')
                # 移除数字后缀（如 _1, _2 等）
                name_without_ext = re.sub(r'_\d+$', '', name_without_ext)
                return name_without_ext
            return None
        
        current_id = extract_chapter_id(current_url)
        xlink_id = extract_chapter_id(xlink)
        
        if current_id and xlink_id:
            is_same = current_id == xlink_id
            print(f"章节ID比较 - 当前URL: {current_id}, xlink: {xlink_id}, 相同: {is_same}")
            return is_same
        
        return False
    
    def _extract_encrypted_content(self, content: str) -> Optional[str]:
        """
        提取并解密加密内容（只关注booktxthtml，忽略booktxthtml广告）
        
        Args:
            content: 章节页面内容
            
        Returns:
            解密后的内容
        """
        # 尝试精确匹配加密脚本
        script_patterns = [
            # 精确格式：<script>  $('#booktxthtml').html(x("encrypted_data","key","iv"));</script>
            r"<script>\s*\$\(['\"]*#booktxthtml['\"]*\)\.html\(x\(['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"]\)\);</script>"
        ]
        
        for pattern in script_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                # 根据正则表达式分组情况获取参数
                if pattern == script_patterns[0] or pattern == script_patterns[1]:
                    # 格式1和2：group(1)=encrypted_data, group(2)=key, group(3)=iv
                    encrypted_data = match.group(1)
                    key = match.group(2)
                    iv = match.group(3)
                
                print(f"使用正则模式找到加密内容，数据长度: {len(encrypted_data)}")
                print(f"提取的密钥: {key}")
                print(f"提取的IV: {iv}")
                
                # 尝试解密
                decrypted_content = self._decrypt_content(encrypted_data, key, iv)
                if decrypted_content:
                    # 清理HTML内容
                    cleaned_content = self._clean_html_content(decrypted_content)
                    return cleaned_content
        
        # 如果所有正则模式都失败，尝试查找加密数据段
        print("正则表达式匹配失败，尝试查找加密数据段")
        return self._find_encrypted_data_segments(content)
    
    def _find_encrypted_data_segments(self, content: str) -> Optional[str]:
        """
        查找加密数据段
        
        Args:
            content: 章节页面内容
            
        Returns:
            解密后的内容
        """
        # 查找可能的base64编码数据段
        base64_pattern = r"['\"]([A-Za-z0-9+/=]{100,})['\"]"
        
        # 查找长字符串（可能是加密数据）
        matches = re.findall(base64_pattern, content)
        
        for match in matches:
            if len(match) > 100:  # 只处理较长的字符串
                print(f"找到可能的加密数据段，长度: {len(match)}")
                
                # 尝试使用默认密钥和IV解密
                decrypted_content = self._decrypt_content(match, self.key, self.iv_b64)
                if decrypted_content:
                    # 检查是否包含有效内容
                    if "<p>" in decrypted_content or "</p>" in decrypted_content or len(decrypted_content) > 100:
                        cleaned_content = self._clean_html_content(decrypted_content)
                        return cleaned_content
        
        return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            清理后的纯文本内容
        """
        if not html_content:
            return ""
        
        # 移除脚本和样式标签
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        
        # 移除广告和无关元素
        html_content = re.sub(r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<div[^>]*id="[^"]*ad[^"]*"[^>]*>.*?</div>', '', html_content, flags=re.DOTALL)
        
        # 转换段落标签为换行
        html_content = re.sub(r'</?p[^>]*>', '\n', html_content)
        
        # 转换换行标签
        html_content = re.sub(r'<br[^>]*/?>', '\n', html_content)
        
        # 移除所有HTML标签
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # 清理多余空白和换行
        html_content = re.sub(r'\s+', ' ', html_content)
        html_content = re.sub(r'\n\s*\n', '\n\n', html_content)
        
        # 清理首尾空白
        html_content = html_content.strip()
        
        return html_content
    
    def _fix_escapes(self, s: str) -> str:
        """修复转义字符"""
        return s.replace("\\u002b", "+").replace("\\/", "/").replace("\\n", "")
    
    def _try_zero_unpad(self, b: bytes) -> bytes:
        """尝试零填充去除"""
        return b.rstrip(b'\x00')
    
    def _is_printable_text(self, s: bytes, threshold=0.7) -> bool:
        """检查是否为可打印文本"""
        if not s:
            return False
        printable = sum(1 for ch in s if 32 <= ch <= 126 or ch in (9,10,13))
        return printable / len(s) >= threshold
    
    def _detect_openssl_salt(self, data: bytes):
        """检测OpenSSL盐值"""
        if data.startswith(b"Salted__"):
            salt = data[8:16]
            return True, salt, data[16:]
        return False, None, data
    
    def _try_decompress(self, decoded_bytes: bytes) -> dict:
        """尝试解压缩"""
        results = {}
        # try zlib
        try:
            out = zlib.decompress(decoded_bytes)
            results['zlib'] = out
        except Exception:
            pass
        # try gzip
        try:
            out = gzip.decompress(decoded_bytes)
            results['gzip'] = out
        except Exception:
            pass
        return results
    
    def _aes_decrypt_raw(self, ciphertext: bytes, key_bytes: bytes, iv_bytes: bytes) -> bytes:
        """AES解密原始数据"""
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        return cipher.decrypt(ciphertext)
    
    def _decrypt_content(self, encrypted_data: str, key: str, iv: str) -> Optional[str]:
        """
        解密内容
        
        Args:
            encrypted_data: 加密数据
            key: 密钥
            iv: 初始化向量
            
        Returns:
            解密后的内容
        """
        try:
            # 1. 修复转义字符
            s = self._fix_escapes(encrypted_data)
            
            # 2. 如果字符串看起来像JSON数组段，尝试解析
            possible_segments = None
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                    possible_segments = parsed
                    print(f"[info] 检测到JSON数组的base64段 (长度 {len(parsed)})")
            except Exception:
                pass
            
            candidates = []
            if possible_segments:
                # 尝试连接段（无分隔符）
                concat = "".join(possible_segments)
                candidates.append(("concatenated_segments", concat))
                # 也尝试解密每个段
                for i, seg in enumerate(possible_segments):
                    candidates.append((f"segment_{i}", seg))
            
            # 将原始完整字符串作为候选
            candidates.append(("original", s))
            
            # 解码IV
            iv_bytes = base64.b64decode(iv)
            key_bytes = key.encode('utf-8')
            
            for name, b64text in candidates:
                print(f"\n--- 尝试解密: {name} ---")
                try:
                    ciphertext = base64.b64decode(b64text)
                except Exception as e:
                    print(f" base64解码失败: {e}")
                    continue
                
                # 检测OpenSSL盐头
                has_salt, salt, raw_cipher = self._detect_openssl_salt(ciphertext)
                if has_salt and salt:
                    print(f"  [info] 检测到OpenSSL 'Salted__' 头，salt = {salt.hex()}")
                    ciphertext_to_try = raw_cipher
                else:
                    ciphertext_to_try = ciphertext
                
                # 原始解密
                dec = self._aes_decrypt_raw(ciphertext_to_try, key_bytes, iv_bytes)
                
                # 尝试零填充去除
                z_unpadded = self._try_zero_unpad(dec)
                try:
                    z_text = z_unpadded.decode('utf-8', errors='replace')
                except Exception:
                    z_text = None
                
                print(f"  解密长度: {len(dec)} 字节")
                if z_text is not None:
                    printable = self._is_printable_text(z_unpadded)
                    print(f"  零填充去除 -> 前200字符 (可打印={printable}):\n{repr(z_text[:200])}")
                    
                    # 检查是否包含HTML标签或中文文本，如果是则返回
                    if ("<p>" in z_text and "</p>" in z_text) or self._contains_chinese_text(z_text):
                        return z_text
                    
                    # 尝试解压缩
                    decomp = self._try_decompress(z_unpadded)
                    if decomp:
                        for method, out in decomp.items():
                            try:
                                decomp_text = out.decode('utf-8', errors='replace')
                                if ("<p>" in decomp_text and "</p>" in decomp_text) or self._contains_chinese_text(decomp_text):
                                    return decomp_text
                            except Exception:
                                pass
                
                # 尝试PKCS7填充去除
                try:
                    pk = unpad(dec, AES.block_size)
                    try:
                        pk_text = pk.decode('utf-8', errors='replace')
                        if ("<p>" in pk_text and "</p>" in pk_text) or self._contains_chinese_text(pk_text):
                            return pk_text
                    except Exception:
                        pass
                except Exception:
                    pass
            
            return None
            
        except Exception as e:
            print(f"解密失败: {e}")
            return None
    
    def _contains_chinese_text(self, text: str) -> bool:
        """检查文本是否包含中文"""
        import re
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return len(chinese_chars) > 10  # 至少有10个中文字符
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 提取URL中的read/后面的部分作为小说ID
        match = re.search(r'/read/([^/]+)/', url)
        if match:
            return match.group(1)
        # 如果无法提取，使用URL的路径部分
        return url.replace('/', '_').replace(':', '_')
    
    def test_parser(self, novel_url: str) -> Dict[str, Any]:
        """
        测试解析器功能
        
        Args:
            novel_url: 测试小说URL
            
        Returns:
            解析结果
        """
        print(f"=== 开始测试 PhotoGram 解析器 ===")
        print(f"目标URL: {novel_url}")
        
        try:
            # 获取小说页面内容
            content = self._get_url_content(novel_url)
            if not content:
                return {"error": "无法获取页面内容"}
            
            print(f"页面获取成功，长度: {len(content)} 字符")
            
            # 提取标题
            title = self._extract_with_regex(content, self.title_reg)
            print(f"提取标题: {title}")
            
            if not title:
                return {"error": "无法提取小说标题"}
            
            # 解析多章节小说
            result = self._parse_multichapter_novel(content, novel_url, title)
            print(f"解析完成，共 {len(result['chapters'])} 个章节")
            return result
                
        except Exception as e:
            print(f"解析失败: {e}")
            return {"error": str(e)}
    
    def run_test(self, test_url: str = None):
        """
        运行测试
        
        Args:
            test_url: 测试URL，如果为None则使用默认测试URL
        """
        if test_url is None:
            # 使用默认的测试URL
            test_url = "https://www.photo-gram.com/read/eddli/"
        
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
            
            # 显示前3个章节的标题
            for i, chapter in enumerate(result['chapters'][:3]):
                print(f"章节 {i+1}: {chapter['title']}")
                if chapter['content']:
                    print(f"  内容预览: {chapter['content'][:100]}...")
            
            if len(result['chapters']) > 3:
                print(f"... 还有 {len(result['chapters']) - 3} 个章节")


# 测试代码
if __name__ == "__main__":
    # 创建解析器实例
    parser = PhotoGramParser()
    
    # 运行测试
    parser.run_test()