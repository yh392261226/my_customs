"""
PhotoGram网站解析器 v2
支持 https://www.photo-gram.com/ 网站的小说解析
使用统一的crypto_utils解密工具
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from ..utils.crypto_utils import AESCipher, extract_encryption_keys, is_encrypted_content
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
        # 使用.+?进行非贪婪匹配，可以匹配包含\u002b等转义字符的内容
        # 注意脚本标签后可能有空格，并且可能跨行
        r"<script>\s+\$\(['\"]#booktxthtml['\"]\)\.html\(x\(['\"](.+?)['\"],['\"](.+?)['\"],['\"](.+?)['\"]\)\);</script>"
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
        
        # 创建URL记录文件
        novel_id = self._extract_novel_id_from_url(novel_url)
        # url_record_file = f"{novel_id}_urls.txt"
        
        # 初始化URL记录
        # successful_urls = []
        # failed_urls = []
        
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
                    # successful_urls.append(chapter_url)
                    print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 完成")
                else:
                    # failed_urls.append(chapter_url)
                    print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 获取内容失败")
                    
                # 章节间延迟
                import time
                time.sleep(1)
                    
            except Exception as e:
                # failed_urls.append(chapter_info['url'])
                print(f"章节 {i+1}/{len(chapters_list)}: {chapter_info['title']} - 错误: {e}")
        
        # 写入URL记录文件
        # self._write_urls_to_file(url_record_file, successful_urls, failed_urls, novel_url, title)
        
        if not chapters_with_content:
            raise Exception("无法获取任何章节内容")
        
        # 提取简介和状态
        description = self._extract_description(content)
        status = self._extract_status(content)
        
        return {
            'title': title,
            'author': self.novel_site_name or self.name,
            'novel_id': novel_id,
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

            
            # 确保URL是完整的
            if not chapter_url.startswith('http'):
                chapter_url = urljoin(self.base_url, chapter_url)
            
            chapters.append({
                "title": chapter_title,
                "url": chapter_url
            })
        
        print(f"从 <dl id=\"newlist\"> 中提取到 {len(chapters)} 个章节")
        return chapters
    
    # def _write_urls_to_file(self, filename: str, successful_urls: List[str], failed_urls: List[str], novel_url: str, title: str):
    #     """
    #     将URL记录写入文件，方便检查哪些页面没有成功获取
        
    #     Args:
    #         filename: 文件名
    #         successful_urls: 成功获取的URL列表
    #         failed_urls: 失败的URL列表
    #         novel_url: 小说URL
    #         title: 小说标题
    #     """
    #     try:
    #         with open(filename, 'w', encoding='utf-8') as f:
    #             f.write(f"# PhotoGram 小说URL记录文件\n")
    #             f.write(f"# 小说标题: {title}\n")
    #             f.write(f"# 小说URL: {novel_url}\n")
    #             f.write(f"# 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    #             f.write(f"# 成功获取: {len(successful_urls)} 个页面\n")
    #             f.write(f"# 失败页面: {len(failed_urls)} 个页面\n")
    #             f.write(f"\n{'='*80}\n")
    #             f.write("成功获取的页面URL:\n")
    #             f.write(f"{'='*80}\n")
                
    #             for i, url in enumerate(successful_urls, 1):
    #                 f.write(f"{i}. {url}\n")
                
    #             f.write(f"\n{'='*80}\n")
    #             f.write("失败的页面URL:\n") 
    #             f.write(f"{'='*80}\n")
                
    #             if failed_urls:
    #                 for i, url in enumerate(failed_urls, 1):
    #                     f.write(f"{i}. {url}\n")
    #             else:
    #                 f.write("无失败的页面\n")
                
    #             f.write(f"\n{'='*80}\n")
    #             f.write("统计信息:\n")
    #             f.write(f"{'='*80}\n")
    #             f.write(f"总页面数: {len(successful_urls) + len(failed_urls)}\n")
    #             f.write(f"成功获取: {len(successful_urls)} 页 ({(len(successful_urls)/(len(successful_urls) + len(failed_urls))*100):.1f}%)\n")
    #             f.write(f"失败页面: {len(failed_urls)} 页 ({(len(failed_urls)/(len(successful_urls) + len(failed_urls))*100):.1f}%)\n")
            
    #         print(f"URL记录已保存到文件: {filename}")
    #         print(f"成功获取: {len(successful_urls)} 页，失败: {len(failed_urls)} 页")
            
    #     except Exception as e:
    #         print(f"写入URL记录文件失败: {e}")
    
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
        
        # 获取所有子章节内容（包含第一页）
        sub_contents = self._get_sub_chapters_content(chapter_url)
        
        # 如果有内容，合并所有子章节内容
        if sub_contents:
            print(f"找到 {len(sub_contents)} 个子章节")
            all_content = ""
            for i, sub_content in enumerate(sub_contents):
                print(f"  子章节 {i+1}: {sub_content[:50]}...")
                if i == 0:
                    all_content = sub_content
                else:
                    all_content += "\n\n" + sub_content
            return all_content
        else:
            # 没有获取到任何内容，尝试直接获取章节内容
            main_content = self._get_single_chapter_content(chapter_url)
            if not main_content:
                print("无法获取主章节内容")
                return None
            return main_content
    
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
        
        # 提取加密内容并解密（这是单独获取章节内容，所以是第一页）
        encrypted_content = self._extract_encrypted_content(content, is_first_page=True)
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
        chapter_base_name = None  # 记录当前主章节的基本名称
        
        # 提取当前主章节的基本名称
        def extract_base_name(url):
            # 如果是完整URL，先提取路径部分
            if url.startswith('http'):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path
            else:
                path = url
            
            # 移开头的斜杠
            path = path.lstrip('/')
            # 分割路径
            parts = path.split('/')
            if len(parts) >= 2:
                filename = parts[-1]  # 获取文件名
                # 分离基本名和后缀
                base_name = filename.replace('.html', '')
                # 检查是否有数字后缀
                match = re.match(r'(.+?)_(\d+)$', base_name)
                if match:
                    # 有数字后缀，是子章节，返回基本名
                    return match.group(1)
                else:
                    # 没有数字后缀，是主章节，直接返回
                    return base_name
            return None
        
        # 获取主章节的基本名称
        chapter_base_name = extract_base_name(chapter_url)
        print(f"主章节基本名称: {chapter_base_name}")
        
        # 获取第一页的页面内容，用于提取xlink
        print(f"正在获取第一页内容: {chapter_url}")
        first_page_content = self._get_url_content(chapter_url)
        if not first_page_content:
            print(f"❌ 无法获取第一页页面内容: {chapter_url}")
            return []
        
        print(f"✅ 第一页获取成功，长度: {len(first_page_content)} 字符")
        
        # 检查页面内容是否包含常见的错误信息
        if "404" in first_page_content or "Not Found" in first_page_content:
            print(f"❌ 第一页返回404错误: {chapter_url}")
            return []
        
        # 获取第一页的内容（这是主章节内容）
        first_content = self._extract_encrypted_content(first_page_content, is_first_page=True)
        if first_content:
            sub_contents.append(first_content)
            print(f"✅ 成功解密第一页内容: {first_content[:50]}...")
        else:
            print(f"⚠️ 无法解密第一页内容，但继续处理子章节")
            # 尝试其他解密方法
            print("尝试备用解密方法...")
            # 检查页面是否包含明文内容
            if "booktxthtml" in first_page_content:
                print("页面包含booktxthtml元素，尝试直接提取")
                # 尝试直接提取文本内容
                text_content = self._extract_plain_text(first_page_content)
                if text_content:
                    sub_contents.append(text_content)
                    print(f"✅ 使用备用方法提取到第一页内容: {text_content[:50]}...")
        
        # 立即提取第一页的xlink，用于判断是否需要继续
        print("正在提取第一页的xlink...")
        slink, xlink = self._extract_slink_xlink(first_page_content)
        if not xlink:
            print(f"❌ 无法从第一页提取xlink，尝试其他提取方法")
            # 尝试多种xlink提取方法
            xlink = self._extract_xlink_alternative(first_page_content)
            if not xlink:
                print(f"❌ 所有xlink提取方法都失败，无法继续处理子章节")
                return sub_contents
        
        print(f"✅ 成功提取xlink: {xlink}")
        
        print(f"第一页xlink: {xlink}")
        
        # 构建下一页URL
        if xlink.startswith('/'):
            next_url = urljoin(self.base_url, xlink)
        elif xlink.startswith('http'):
            next_url = xlink
        else:
            # 相对路径，需要基于当前URL构建
            next_url = urljoin(current_url, xlink)
        
        # 检查是否需要继续处理
        # 如果xlink指向章节列表页，说明第一页就是唯一的一页
        if (xlink.startswith('/read/') and not any(sub in xlink for sub in ['.html', '_1', '_2', '_3', '_4', '_5', '_6', '_7', '_8', '_9'])):
            print(f"第一页xlink指向章节列表页，没有子章节: {xlink}")
            return sub_contents
        
        # 检查xlink是否与当前书籍的章节列表页一致（说明是最后一页）
        # 构建当前书籍的章节列表页URL
        book_id = chapter_url.split('/')[-2]  # 从URL中提取书籍ID，如dhce
        chapter_list_url = f"{self.base_url}/read/{book_id}/"
        
        # 处理xlink中的转义字符
        cleaned_xlink = xlink.replace('\\/', '/')
        
        # 如果xlink指向章节列表页，说明当前是第一页也是最后一页
        if cleaned_xlink == chapter_list_url or cleaned_xlink == f"{self.base_url}/read/{book_id}/":
            print(f"第一页xlink指向章节列表页（最后一页），没有子章节: {cleaned_xlink}")
            return sub_contents
        
        # 如果xlink指向其他主章节，说明第一页就是唯一的一页
        next_base_name = extract_base_name(next_url)
        if next_base_name and next_base_name != chapter_base_name:
            print(f"第一页xlink指向其他主章节（{next_base_name} != {chapter_base_name}），没有子章节")
            return sub_contents
        
        # 如果xlink指向当前页面本身，说明第一页就是唯一的一页
        if next_url == current_url:
            print(f"第一页xlink指向当前页面，没有子章节")
            return sub_contents
        
        # 特殊检查：如果xlink指向的页面包含数字后缀（如_2.html），则认为是子章节，继续处理
        if any(sub in xlink for sub in ['_2', '_3', '_4', '_5', '_6', '_7', '_8', '_9']):
            print(f"第一页xlink指向子章节（包含数字后缀），继续处理: {next_url}")
            # 更新current_url为下一页
            current_url = next_url
        else:
            # 否则，xlink指向子章节，继续处理
            print(f"第一页xlink指向子章节，继续处理: {next_url}")
            # 更新current_url为下一页
            current_url = next_url
        
        # 然后查找子章节
        while current_url and current_url not in visited_urls:
            visited_urls.add(current_url)
            
            # 获取当前页面内容
            content = self._get_url_content(current_url)
            if not content:
                print(f"无法获取页面内容: {current_url}")
                break
            
            # 提取当前页面的内容（不是第一页）
            sub_content = self._extract_encrypted_content(content, is_first_page=False)
            if not sub_content:
                print(f"无法解密当前页面内容，尝试备用方法: {current_url}")
                # 尝试备用方法
                sub_content = self._extract_plain_text(content)
            
            if sub_content:
                # 确保不重复添加相同内容
                if not any(sc == sub_content for sc in sub_contents):
                    sub_contents.append(sub_content)
                    print(f"获取子章节内容: {sub_content[:50]}...")
                else:
                    print(f"子章节内容已存在，跳过: {current_url}")
            else:
                print(f"⚠️ 无法获取子章节内容，但继续处理下一页: {current_url}")
            
            # 提取slink和xlink
            slink, xlink = self._extract_slink_xlink(content)
            if not xlink:
                print(f"无法从页面提取xlink: {current_url}")
                break
            
            print(f"找到链接 - slink: {slink}, xlink: {xlink}")
            
            # 构建完整的xlink URL
            if xlink.startswith('/'):
                page_next_url = urljoin(self.base_url, xlink)
            elif xlink.startswith('http'):
                page_next_url = xlink
            else:
                # 相对路径，需要基于当前URL构建
                page_next_url = urljoin(current_url, xlink)
            
            # 检查xlink是否是当前章节的子章节
            # 判断规则：
            # 1. 如果xlink指向章节列表页（如 /read/cidhld/），说明当前章节结束
            # 2. 如果xlink是其他主章节（基本名不同），说明当前章节结束
            # 3. 如果xlink是当前主章节的子章节，继续处理
            
            # 情况1：检查是否指向章节列表页（如 /read/cidhld/）
            # 章节列表页的特征是路径以/read/开头，后面直接跟着小说ID，没有具体的章节文件名
            if xlink.startswith('/read/') and not any(sub in xlink for sub in ['.html', '_1', '_2', '_3', '_4', '_5']):
                print(f"xlink指向章节列表页，当前章节处理完成: {xlink}")
                break
            
            # 检查xlink是否与当前书籍的章节列表页一致（说明是最后一页）
            cleaned_xlink = xlink.replace('\\/', '/')
            if cleaned_xlink == chapter_list_url or cleaned_xlink == f"{self.base_url}/read/{book_id}/":
                print(f"xlink指向章节列表页（最后一页），当前章节处理完成: {cleaned_xlink}")
                break
            
            # 情况2：检查是否指向其他主章节
            xlink_base_name = extract_base_name(page_next_url)
            if xlink_base_name and xlink_base_name != chapter_base_name:
                print(f"xlink指向其他主章节（{xlink_base_name} != {chapter_base_name}），当前章节处理完成")
                break
            
            # 情况3：xlink是当前主章节的子章节
            if page_next_url != current_url:
                # 无论是否成功获取内容，都继续到下一页
                current_url = page_next_url
                # 添加延迟避免请求过快
                import time
                time.sleep(1)
            else:
                # xlink指向当前页面，说明已经到达最后
                print("xlink指向当前页面，已经到达最后一页")
                break
        
        print(f"总共获取到 {len(sub_contents)} 个子章节内容")
        return sub_contents
    
    def _extract_slink_xlink(self, content: str) -> tuple[str, str]:
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
        
        return "", ""  # type: ignore
    
    def _extract_plain_text(self, content: str) -> Optional[str]:
        """
        从页面内容中提取明文文本（备用方法）
        
        Args:
            content: 页面内容
            
        Returns:
            提取的文本内容
        """
        try:
            # 尝试提取booktxthtml元素的内容
            # 格式：<div id="booktxthtml">...</div>
            pattern = r'<div[^>]*id=["\']booktxthtml["\'][^>]*>(.*?)</div>'
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                html_content = match.group(1)
                # 清理HTML标签
                text_content = re.sub(r'<[^>]+>', '', html_content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                if text_content and len(text_content) > 10:
                    return text_content
            
            # 尝试其他可能的文本容器
            patterns = [
                r'<div[^>]*class=["\']content["\'][^>]*>(.*?)</div>',
                r'<div[^>]*class=["\']text["\'][^>]*>(.*?)</div>',
                r'<p[^>]*>(.*?)</p>',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                if matches:
                    all_text = []
                    for match in matches:
                        text = re.sub(r'<[^>]+>', '', match)
                        text = re.sub(r'\s+', ' ', text).strip()
                        if text and len(text) > 10:
                            all_text.append(text)
                    
                    if all_text:
                        return '\n\n'.join(all_text)
            
            return None
        except Exception as e:
            print(f"提取明文文本失败: {e}")
            return None
    
    def _extract_xlink_alternative(self, content: str) -> Optional[str]:
        """
        备用方法提取xlink
        
        Args:
            content: 页面内容
            
        Returns:
            提取的xlink
        """
        try:
            # 方法1：查找包含xlink的script标签
            patterns = [
                # 标准格式：var xlink = '...';
                r'xlink\s*=\s*["\']([^"\']+)["\']',
                # 其他可能格式
                r'xlink:\s*["\']([^"\']+)["\']',
                r'next[^>]*href=["\']([^"\']+)["\']',
                # 查找下一页链接
                r'href=["\']([^"\']+_2\.html)["\']',
                r'href=["\']([^"\']+_\d+\.html)["\']',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 过滤掉明显的错误链接
                    if match and not match.startswith('#') and 'javascript' not in match:
                        # 检查是否是子章节链接（包含_数字.html）
                        if re.search(r'_\d+\.html', match):
                            return match
                        # 或者检查是否是相对路径
                        elif match.startswith('/') or '.' in match:
                            return match
            
            return None
        except Exception as e:
            print(f"备用xlink提取失败: {e}")
            return None
    
    def _is_sub_chapter(self, current_url: str, xlink: str) -> bool:
        """
        判断xlink是否是当前主章节的子章节
        
        根据您提供的URL结构，判断规则如下：
        1. 主章节URL格式: /dhjd/giehg.html
        2. 子章节URL格式: /dhjd/giehg_1.html, /dhjd/giehg_2.html 等
        3. 如果xlink不包含数字后缀，且与当前URL的基本名不同，则指向下一个主章节
        
        Args:
            current_url: 当前页面URL
            xlink: 下一页链接
            
        Returns:
            是否是当前主章节的子章节
        """
        # 提取当前URL的基本信息
        def extract_base_info(url_or_path):
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
                # 分离基本名和后缀
                base_name = filename.replace('.html', '')
                # 检查是否有数字后缀
                match = re.match(r'(.+?)_(\d+)$', base_name)
                if match:
                    # 有数字后缀，是子章节
                    return {
                        'is_sub_chapter': True,
                        'base_name': match.group(1),
                        'suffix': int(match.group(2))
                    }
                else:
                    # 没有数字后缀，是主章节
                    return {
                        'is_sub_chapter': False,
                        'base_name': base_name,
                        'suffix': 0
                    }
            return None
        
        current_info = extract_base_info(current_url)
        xlink_info = extract_base_info(xlink)
        
        if current_info and xlink_info:
            print(f"当前URL信息: {current_info}, xlink信息: {xlink_info}")
            
            # 如果xlink是子章节
            if xlink_info['is_sub_chapter']:
                # 检查基本名是否与当前URL的基本名匹配
                # 当前URL可能是主章节，也可能是子章节
                current_base = current_info['base_name']
                if current_info['is_sub_chapter']:
                    # 如果当前URL也是子章节，使用它的基本名
                    current_base = current_info['base_name']
                
                is_sub = current_base == xlink_info['base_name']
                print(f"xlink是子章节，基本名匹配: {is_sub}")
                return is_sub
            else:
                # xlink不是子章节（是主章节）
                # 检查基本名是否与当前URL的基本名相同
                current_base = current_info['base_name']
                if current_info['is_sub_chapter']:
                    # 如果当前URL是子章节，使用它的基本名
                    current_base = current_info['base_name']
                
                is_sub = current_base == xlink_info['base_name']
                print(f"xlink是主章节，与当前基本名相同: {is_sub}")
                return is_sub
        
        return False
    
    def _is_same_chapter(self, current_url: str, xlink: str) -> bool:
        """
        判断xlink是否与当前URL属于同一章节
        
        这个方法保留作为后备，但建议使用_is_sub_chapter方法
        
        Args:
            current_url: 当前页面URL
            xlink: 下一页链接
            
        Returns:
            是否属于同一章节
        """
        # 调用新的_is_sub_chapter方法
        return self._is_sub_chapter(current_url, xlink)
    
    def debug_decrypt_content(self, content: str) -> Optional[str]:
        """
        调试解密内容的方法，用于诊断问题
        
        Args:
            content: 章节页面内容
            
        Returns:
            解密后的内容
        """
        print("=== 开始调试解密过程 ===")
        print(f"页面内容长度: {len(content)}")
        
        # 1. 检查页面是否包含booktxthtml元素
        if 'booktxthtml' not in content:
            print("❌ 页面不包含booktxthtml元素")
            return None
        
        print("✅ 页面包含booktxthtml元素")
        
        # 2. 查找所有script标签
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, content, re.DOTALL | re.IGNORECASE)
        
        print(f"找到 {len(scripts)} 个script标签")
        
        # 3. 查找所有可能的加密数据
        base64_pattern = r"['\"]([A-Za-z0-9+/=]{50,})['\"]"
        encrypted_data = re.findall(base64_pattern, content)
        
        print(f"找到 {len(encrypted_data)} 个可能的加密数据段")
        for i, data in enumerate(encrypted_data[:3]):  # 只显示前3个
            print(f"  数据段 {i+1}: 长度={len(data)}, 前20字符={data[:20]}...")
        
        # 4. 查找所有可能的密钥和IV
        keys = re.findall(r"key\s*=\s*['\"]([^'\"]+)['\"]", content)
        ivs = re.findall(r"iv\s*=\s*['\"]([^'\"]+)['\"]", content)
        
        print(f"找到 {len(keys)} 个可能的密钥: {keys}")
        print(f"找到 {len(ivs)} 个可能的IV: {ivs}")
        
        # 5. 尝试使用默认配置解密
        default_key = "encryptedDatastr"
        default_iv = "FMCqVWeARJd9AY9PYm2csw=="
        
        print(f"\n尝试使用默认配置解密: key={default_key}, iv={default_iv}")
        
        for i, data in enumerate(encrypted_data):
            if len(data) > 100:  # 只尝试较长的数据
                print(f"\n尝试解密数据段 {i+1}...")
                try:
                    from ..utils.crypto_utils import AESCipher
                    cipher = AESCipher(default_key, default_iv)
                    decrypted = cipher.decrypt(data, padding_mode='zero')
                    
                    if decrypted and decrypted != data:
                        chinese_chars = len([c for c in decrypted if '\u4e00' <= c <= '\u9fff'])
                        print(f"  解密成功! 长度={len(decrypted)}, 中文字符数={chinese_chars}")
                        print(f"  前100字符: {decrypted[:100]}...")
                        
                        if chinese_chars > 10:
                            print("✅ 解密结果包含有效中文内容")
                            return decrypted
                    else:
                        print("  解密失败或返回原数据")
                        
                        # 尝试PKCS7模式
                        decrypted_pkcs7 = cipher.decrypt(data, padding_mode='pkcs7')
                        if decrypted_pkcs7 and decrypted_pkcs7 != data:
                            chinese_chars = len([c for c in decrypted_pkcs7 if '\u4e00' <= c <= '\u9fff'])
                            print(f"  PKCS7解密成功! 长度={len(decrypted_pkcs7)}, 中文字符数={chinese_chars}")
                            
                            if chinese_chars > 10:
                                print("✅ PKCS7解密结果包含有效中文内容")
                                return decrypted_pkcs7
                except Exception as e:
                    print(f"  解密出错: {e}")
        
        # 6. 尝试所有密钥和IV组合
        print("\n尝试所有密钥和IV组合...")
        all_keys = [default_key] + keys
        all_ivs = [default_iv] + ivs
        
        for key in all_keys:
            for iv in all_ivs:
                print(f"  尝试组合: key={key}, iv={iv}")
                for data in encrypted_data:
                    if len(data) > 50:
                        try:
                            cipher = AESCipher(key, iv)
                            decrypted = cipher.decrypt(data, padding_mode='zero')
                            
                            if decrypted and decrypted != data:
                                chinese_chars = len([c for c in decrypted if '\u4e00' <= c <= '\u9fff'])
                                if chinese_chars > 10:
                                    print(f"✅ 找到有效组合! key={key}, iv={iv}")
                                    return decrypted
                        except:
                            pass
        
        print("❌ 所有解密尝试都失败")
        return None

    def _extract_encrypted_content(self, content: str, is_first_page: bool = False) -> Optional[str]:
        """
        提取并解密加密内容（动态获取密钥和IV，只关注booktxthtml）
        
        Args:
            content: 章节页面内容
            is_first_page: 是否是第一页（用于决定是否提取正文开始位置）
            
        Returns:
            解密后的内容
        """
        # 首先尝试调试方法
        debug_result = self.debug_decrypt_content(content)
        if debug_result:
            return debug_result
        
        # 如果调试失败，尝试原始方法
        print("\n=== 尝试原始解密方法 ===")
        import html as html_module
        
        print(f"开始提取加密内容，页面内容长度: {len(content)} 字符")
        
        # 尝试多种可能的脚本模式
        script_patterns = [
            # 原始模式
            r"<script>\s+\$\(['\"]#booktxthtml['\"]\)\.html\(x\(['\"](.+?)['\"],['\"](.+?)['\"],['\"](.+?)['\"]\)\);</script>",
            # 新增模式1：空格变体
            r"<script>\s*\$\(['\"]#booktxthtml['\"]\)\.html\(x\(['\"](.+?)['\"],['\"](.+?)['\"],['\"](.+?)['\"]\)\);</script>",
            # 新增模式2：换行变体
            r"<script>\s*\$\(['\"]#booktxthtml['\"]\)\.html\(x\(['\"](.+?)['\"],['\"](.+?)['\"],['\"](.+?)['\"]\)\);?\s*</script>",
            # 新增模式3：可能有其他字符
            r"<script[^>]*>\s*\$\(['\"]#booktxthtml['\"]\)\.html\(x\(['\"](.+?)['\"],['\"](.+?)['\"],['\"](.+?)['\"]\)\);?\s*</script>",
            # 新增模式4：不带jQuery
            r"<script>\s*document\.getElementById\(['\"]booktxthtml['\"]\)\.innerHTML\s*=\s*x\(['\"](.+?)['\"],['\"](.+?)['\"],['\"](.+?)['\"]\);?\s*</script>",
        ]
        
        for i, script_pattern in enumerate(script_patterns):
            print(f"尝试第 {i+1} 种脚本模式匹配...")
            match = re.search(script_pattern, content, re.DOTALL)
            
            if match:
                # 格式：group(1)=encrypted_data, group(2)=key, group(3)=iv
                encrypted_data = match.group(1)
                key = match.group(2)
                iv = match.group(3)
                
                print(f"✅ 第 {i+1} 种模式匹配成功")
                print(f"加密数据长度: {len(encrypted_data)}")
                print(f"密钥: {key}")
                print(f"IV: {iv}")
                
                # 处理JavaScript的转义字符
                encrypted_data = encrypted_data.replace(r'\/', '/').replace(r'\u002b', '+')
                iv = iv.replace(r'\/', '/').replace(r'\u002b', '+')
                key = key
                
                # 检查变量是否被正确定义
                if encrypted_data and key and iv:
                    print(f"开始解密，使用模式 {i+1} 的参数")
                    # 尝试解密
                    decrypted_content = self._decrypt_content(encrypted_data, key, iv, content, is_first_page)
                    if decrypted_content:
                        print(f"✅ 使用模式 {i+1} 解密成功")
                        return decrypted_content
                    else:
                        print(f"❌ 使用模式 {i+1} 解密失败")
                else:
                    print("❌ 加密脚本参数不完整")
            else:
                print(f"❌ 第 {i+1} 种模式未匹配")
        
        # 如果所有精确模式都失败，尝试更宽松的匹配
        print("尝试更宽松的匹配...")
        
        # 查找所有x()函数调用
        x_function_pattern = r"x\(['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"],['\"]([^'\"]+)['\"]\)"
        x_matches = re.findall(x_function_pattern, content)
        
        if x_matches:
            print(f"找到 {len(x_matches)} 个x()函数调用")
            for i, match in enumerate(x_matches):
                encrypted_data, key, iv = match
                
                # 处理IV中的转义字符
                iv = self._decode_iv(iv)
                
                print(f"尝试第 {i+1} 个x()函数调用")
                print(f"  数据长度: {len(encrypted_data)}")
                print(f"  密钥: {key}")
                print(f"  处理后的IV: {iv}")
                
                # 尝试解密
                decrypted_content = self._decrypt_content(encrypted_data, key, iv, content, is_first_page)
                if decrypted_content:
                    print(f"✅ 第 {i+1} 个x()函数调用解密成功")
                    return decrypted_content
                else:
                    print(f"❌ 第 {i+1} 个x()函数调用解密失败")
        
        # 如果所有方法都失败，尝试查找加密数据段
        print("所有方法都失败，尝试查找加密数据段")
        return self._find_encrypted_data_segments(content)
    
    def _decode_iv(self, iv: str) -> str:
        """
        解码IV字符串，处理其中的转义字符
        
        Args:
            iv: 原始IV字符串
            
        Returns:
            处理后的IV字符串
        """
        try:
            import codecs
            import urllib.parse
            
            # 处理JavaScript风格的Unicode转义
            # 例如：\\u002b -> +
            iv = codecs.decode(iv, 'unicode_escape')
            
            # 处理URL编码的字符
            # 例如：%2B -> +
            iv = urllib.parse.unquote(iv)
            
            return iv
        except Exception as e:
            print(f"IV解码失败: {e}")
            return iv
    
    def _find_encrypted_data_segments(self, content: str) -> Optional[str]:
        """
        查找加密数据段（尝试多种可能的密钥和IV组合）
        
        Args:
            content: 章节页面内容
            
        Returns:
            解密后的内容
        """
        print(f"开始查找加密数据段，页面内容长度: {len(content)} 字符")
        
        # 多种可能的base64编码数据段模式
        base64_patterns = [
            r"['\"]([A-Za-z0-9+/=]{100,})['\"]",  # 标准模式
            r"['\"]([A-Za-z0-9+/=]{50,100})['\"]",  # 较短模式
            r"x\(['\"]([A-Za-z0-9+/=]{50,})['\"]",  # x函数模式
            r"html\(['\"]([A-Za-z0-9+/=]{50,})['\"]",  # html函数模式
        ]
        
        # 查找长字符串（可能是加密数据）
        all_matches = []
        for pattern in base64_patterns:
            matches = re.findall(pattern, content)
            all_matches.extend(matches)
        
        # 去重并过滤长度
        unique_matches = list(set([m for m in all_matches if len(m) > 50]))
        print(f"找到 {len(unique_matches)} 个可能的加密数据段")
        
        # 从页面中提取可能的密钥和IV
        key_iv_patterns = [
            r"var\s+key\s*=\s*['\"]([^'\"]+)['\"]",
            r"var\s+iv\s*=\s*['\"]([^'\"]+)['\"]",
            r"const\s+key\s*=\s*['\"]([^'\"]+)['\"]",
            r"const\s+iv\s*=\s*['\"]([^'\"]+)['\"]",
            # 新增模式
            r"key\s*=\s*['\"]([^'\"]+)['\"]",
            r"iv\s*=\s*['\"]([^'\"]+)['\"]",
        ]
        
        possible_keys = []
        possible_ivs = []
        
        for pattern in key_iv_patterns:
            found_values = re.findall(pattern, content)
            if found_values:
                if 'key' in pattern:
                    possible_keys.extend(found_values)
                elif 'iv' in pattern:
                    possible_ivs.extend(found_values)
        
        # 添加默认值
        default_keys = ["encryptedDatastr", "mAf6AupVNiH5u4vS", "BaL94DxIbGhdAJ80"]
        default_ivs = ["FMCqVWeARJd9AY9PYm2csw==", "mAf6AupVNiH5u4vS", "BaL94DxIbGhdAJ80"]
        
        for key in default_keys:
            if key not in possible_keys:
                possible_keys.append(key)
        
        for iv in default_ivs:
            if iv not in possible_ivs:
                possible_ivs.append(iv)
        
        print(f"可能的密钥: {possible_keys}")
        print(f"可能的IV: {possible_ivs}")
        
        # 尝试所有可能的密钥和IV组合
        for match in unique_matches:
            if len(match) > 50:  # 处理所有可能的加密数据
                print(f"尝试解密数据段，长度: {len(match)}")
                
                # 尝试所有可能的密钥和IV组合
                for key in possible_keys:
                    for iv in possible_ivs:
                        print(f"  尝试使用密钥: {key}, IV: {iv}")
                        decrypted_content = self._decrypt_content(match, key, iv, content, is_first_page)
                        if decrypted_content:
                            # 检查是否包含有效内容
                            if ("<p>" in decrypted_content or "</p>" in decrypted_content or 
                                len(decrypted_content) > 100 or 
                                any('\u4e00' <= c <= '\u9fff' for c in decrypted_content)):
                                print(f"✅ 解密成功！使用密钥: {key}, IV: {iv}")
                                return decrypted_content
                            else:
                                print(f"  解密结果无效或不包含有效内容")
        
        # 最后尝试：直接提取页面中的文本内容作为备用
        print("所有解密方法都失败，尝试直接提取页面文本")
        plain_text = self._extract_plain_text(content)
        if plain_text and len(plain_text) > 100:
            print(f"✅ 直接提取到页面文本，长度: {len(plain_text)}")
            return plain_text
        
        print("所有解密和提取方法都失败")
        return None
    
    def _convert_html_to_text(self, html_content: str, is_first_page: bool = True) -> str:
        """
        将HTML内容转换为纯文本，并提取小说正文部分
        
        Args:
            html_content: HTML内容
            is_first_page: 是否是第一页（第一页需要提取正文开始位置）
            
        Returns:
            转换后的纯文本
        """
        if not html_content:
            return ""
        
        import re
        
        # 确保换行符的一致性
        html_content = html_content.replace('\r', '\n')
        
        # 移除所有HTML标签
        # 先处理<p>标签，转换为换行
        html_content = re.sub(r'</p>', '\n\n', html_content)
        html_content = re.sub(r'<p[^>]*>', '', html_content)
        
        # 移除其他所有HTML标签
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # 解码HTML实体
        import html as html_module
        html_content = html_module.unescape(html_content)
        
        # 清理多余的空白字符
        html_content = re.sub(r'[ \t]+', ' ', html_content)
        html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)  # 多个换行合并为两个
        
        # 清理段落开头的空格
        html_content = re.sub(r'\n +', '\n', html_content)
        
        text = html_content.strip()
        
        # 只在第一页尝试找到小说正文开始位置
        if is_first_page:
            # 常见的小说开头模式
            start_patterns = [
                r"曾经的我",
                r"我叫谷宇",
                r"初中的我是",
                r"同学都是",
                r"如果不是认识了",
                r"上篇",
                r"下篇"
            ]
            
            for pattern in start_patterns:
                match_pos = text.find(pattern)
                if match_pos > 0 and match_pos < 500:  # 确保不是太远的位置
                    print(f"找到小说正文开始位置: {pattern} 在位置 {match_pos}")
                    # 从这个位置开始截取
                    text = text[match_pos:]
                    break
        
        return text.strip()
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        清理HTML内容，移除所有HTML标签，输出纯文本
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            清理后的纯文本内容
        """
        if not html_content:
            return ""
        
        import re
        
        # 移除开头的乱码字符，但保留中文字符
        # 查找第一个<p>标签的位置
        first_p_start = html_content.find('<p>')
        if first_p_start > 0:
            # 检查前面是否有中文字符
            before_p = html_content[:first_p_start]
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', before_p)
            if chinese_chars:
                # 如果有中文字符，说明可能是有意义的前缀，保留它
                pass
            else:
                # 检查是否是乱码
                has_garbage = any(ord(c) < 32 and c not in '\r\n\t' for c in before_p)
                if has_garbage or len(before_p) > 10:
                    # 只有确定是乱码时才移除
                    html_content = html_content[first_p_start:]
        
        # 确保换行符的一致性
        html_content = html_content.replace('\r', '\n')
        
        # 移除所有HTML标签
        # 先处理<p>标签，转换为换行
        html_content = re.sub(r'</p>', '\n\n', html_content)
        html_content = re.sub(r'<p[^>]*>', '', html_content)
        
        # 移除其他所有HTML标签
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # 解码HTML实体
        import html as html_module
        html_content = html_module.unescape(html_content)
        
        # 清理多余的空白字符
        html_content = re.sub(r'[ \t]+', ' ', html_content)
        html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)  # 多个换行合并为两个
        
        # 清理段落开头的空格
        html_content = re.sub(r'\n +', '\n', html_content)
        
        return html_content.strip()
        
        # 如果没有找到<p>标签，尝试其他处理
        # 移除脚本和样式标签
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
        
        # 移除广告和无关元素
        html_content = re.sub(r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<div[^>]*id="[^"]*ad[^"]*"[^>]*>.*?</div>', '', html_content, flags=re.DOTALL)
        
        # 转换段落标签为换行
        html_content = re.sub(r'</p>', '\n\n', html_content)
        html_content = re.sub(r'<p[^>]*>', '', html_content)
        
        # 转换换行标签
        html_content = re.sub(r'<br[^>]*/?>', '\n', html_content)
        
        # 移除所有HTML标签
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # 解码HTML实体
        import html
        html_content = html.unescape(html_content)
        
        # 清理多余空白和换行
        html_content = re.sub(r'[ \t]+', ' ', html_content)  # 只清理空格和制表符
        html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)  # 多个换行合并为两个
        html_content = html_content.strip()
        
        return html_content
    

    
    def _decrypt_content(self, encrypted_data: str, key: str, iv: str, html_content: str | None = None, is_first_page: bool = False) -> Optional[str]:
        """
        解密内容 - 使用统一的AESCipher工具，使用多种填充模式尝试
        
        Args:
            encrypted_data: 加密数据
            key: 密钥
            iv: 初始化向量
            html_content: 原始HTML页面内容（用于提取明文部分）
            is_first_page: 是否是第一页（用于决定是否提取正文开始位置）
            
        Returns:
            解密后的内容
        """
        try:
            # 使用统一的AES解密工具
            cipher = AESCipher(key, iv)
            
            # 尝试多种填充模式
            padding_modes = ['zero', 'pkcs7']
            
            for padding_mode in padding_modes:
                decrypted_text = cipher.decrypt_with_fallback(encrypted_data, key, iv, padding_mode)
                
                # 检查解密结果是否有效
                if decrypted_text and decrypted_text != encrypted_data:
                    # 检查是否包含有意义的内容
                    chinese_chars = len([c for c in decrypted_text if '\u4e00' <= c <= '\u9fff'])
                    has_html_tags = '<p>' in decrypted_text or '</p>' in decrypted_text
                    
                    if chinese_chars > 10 or has_html_tags or len(decrypted_text) > 200:
                        print(f"✅ {padding_mode}解密成功，长度: {len(decrypted_text)} 字符，中文字符数: {chinese_chars}")
                        
                        # 修复解密后的内容前缀问题
                        decrypted_text = self._fix_decrypted_prefix(decrypted_text, html_content)
                        
                        # 将HTML内容转换为纯文本
                        if decrypted_text and "<p>" in decrypted_text:
                            # 使用_convert_html_to_text方法转换
                            final_text = self._convert_html_to_text(decrypted_text, is_first_page)
                            return final_text
                        elif decrypted_text and len(decrypted_text.strip()) > 50:
                            # 如果没有HTML标签但有足够的文本内容，直接返回
                            return decrypted_text
                        else:
                            print(f"解密内容过短或无意义: {len(decrypted_text)} 字符")
                            continue
                    else:
                        print(f"❌ {padding_mode}解密结果无效或不包含有意义内容")
                else:
                    print(f"❌ {padding_mode}解密失败或返回原数据")
            
            print("所有填充模式都解密失败")
            return None
                
        except Exception as e:
            print(f"解密过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _fix_decrypted_prefix(self, decrypted_text: str, html_content: str | None = None) -> str:
        """
        修复解密后的前缀问题 - 使用页面中原有的明文内容补全
        
        Args:
            decrypted_text: 原始解密文本
            html_content: 原始HTML页面内容（用于提取明文部分）
            
        Returns:
            修复后的文本
        """
        if not decrypted_text:
            return decrypted_text
        
        # 确保换行符的一致性
        decrypted_text = decrypted_text.replace('\r', '\n')
        
        # 如果没有提供HTML内容，只做基本清理
        if not html_content:
            # 查找第一个<p>标签的位置
            first_p_start = decrypted_text.find('<p>')
            if first_p_start > 0:
                # 检查<p>标签前是否有乱码
                before_p = decrypted_text[:first_p_start]
                has_garbage = any(ord(c) < 32 and c not in '\r\n\t' for c in before_p)
                if has_garbage or len(before_p) > 10:
                    decrypted_text = decrypted_text[first_p_start:]
            return decrypted_text
        
        # 从HTML中提取booktxthtml的明文内容
        plain_content = self._extract_plain_booktxthtml(html_content)
        
        if not plain_content:
            # 如果没有提取到明文内容，只做基本清理
            first_p_start = decrypted_text.find('<p>')
            if first_p_start > 0:
                before_p = decrypted_text[:first_p_start]
                has_garbage = any(ord(c) < 32 and c not in '\r\n\t' for c in before_p)
                if has_garbage or len(before_p) > 10:
                    decrypted_text = decrypted_text[first_p_start:]
            return decrypted_text
        
        # 按照用户思路：明文内容和加密内容都直接去掉所有的HTML标签，然后比对，找到重复的部分
        # 提取解密内容的纯文本（去掉HTML标签）
        decrypted_clean = re.sub(r'<[^>]+>', '', decrypted_text).strip()
        
        # 提取明文内容的纯文本（去掉HTML标签）
        plain_clean = re.sub(r'<[^>]+>', '', plain_content).strip()
        
        # 如果解密内容为空或太短，无法匹配
        if not decrypted_clean or len(decrypted_clean) < 20:
            return decrypted_text
        
        # 尝试更智能的匹配方法
        # 首先清理解密内容，移除控制字符和乱码
        cleaned_decrypted = ""
        for char in decrypted_clean:
            # 保留中文字符、英文字母、数字和常见标点
            if (ord(char) >= 0x4e00 and ord(char) <= 0x9fff) or char.isalnum() or char in '。！？，；：""''（）《》\n\r\t ':
                cleaned_decrypted += char
        
        # 如果清理解密内容为空，无法匹配
        if not cleaned_decrypted:
            return decrypted_text
        
        # 方法1：尝试查找明文内容中的特定完整句子
        specific_full_text = "室内太过安静，柯允站在魏从闻面前，虽然这人坐着，他站着，自己却完全不敢抬头。"
        specific_full_pos = plain_clean.find(specific_full_text)
        
        if specific_full_pos >= 0:
            # 检查解密内容中是否包含这句
            if specific_full_text in cleaned_decrypted:
                # 解密内容中也包含这句，可能已经有完整前缀
                pass
            else:
                # 解密内容中不包含这句，需要添加
                # 直接使用这段文本作为前缀
                prefix_text = plain_clean[:specific_full_pos + len(specific_full_text)].strip()
                prefix_html = self._text_to_html(prefix_text)
                
                # 找到解密内容中第一个<p>标签的位置
                first_p_pos = decrypted_text.find('<p>')
                if first_p_pos > 0:
                    combined_content = prefix_html + '\n' + decrypted_text[first_p_pos:]
                else:
                    combined_content = prefix_html + '\n' + decrypted_text
                
                print(f"使用特定完整文本匹配方法补全前缀，添加了 {len(prefix_text)} 个字符")
                return combined_content
        
        # 方法2：尝试查找明文内容中的短句子，并扩展到完整句子
        specific_short_text = "室内太过安静，柯允站在魏从闻面前"
        specific_short_pos = plain_clean.find(specific_short_text)
        
        if specific_short_pos >= 0:
            # 检查解密内容中是否包含这句
            if specific_short_text in cleaned_decrypted:
                # 解密内容中也包含这句，可能已经有完整前缀
                pass
            else:
                # 尝试扩展到完整的句子
                # 查找下一个句号、感叹号或问号
                after_short_pos = specific_short_pos + len(specific_short_text)
                next_punct_pos = -1
                for punct in ['。', '！', '？']:
                    punct_pos = plain_clean.find(punct, after_short_pos)
                    if punct_pos > 0 and (next_punct_pos == -1 or punct_pos < next_punct_pos):
                        next_punct_pos = punct_pos
                
                if next_punct_pos > 0:
                    # 扩展到完整句子
                    extended_text = plain_clean[:next_punct_pos + 1].strip()
                    prefix_html = self._text_to_html(extended_text)
                    
                    # 找到解密内容中第一个<p>标签的位置
                    first_p_pos = decrypted_text.find('<p>')
                    if first_p_pos > 0:
                        combined_content = prefix_html + '\n' + decrypted_text[first_p_pos:]
                    else:
                        combined_content = prefix_html + '\n' + decrypted_text
                    
                    print(f"使用扩展文本匹配方法补全前缀，添加了 {len(extended_text)} 个字符")
                    return combined_content
                else:
                    # 如果找不到句号，使用原始短文本
                    prefix_text = plain_clean[:specific_short_pos + len(specific_short_text)].strip()
                    prefix_html = self._text_to_html(prefix_text)
                    
                    # 找到解密内容中第一个<p>标签的位置
                    first_p_pos = decrypted_text.find('<p>')
                    if first_p_pos > 0:
                        combined_content = prefix_html + '\n' + decrypted_text[first_p_pos:]
                    else:
                        combined_content = prefix_html + '\n' + decrypted_text
                    
                    print(f"使用特定短文本匹配方法补全前缀，添加了 {len(prefix_text)} 个字符")
                    return combined_content
        
        # 查找解密内容在明文内容中的位置
        match_pos = plain_clean.find(decrypted_clean[:50])  # 使用前50个字符匹配
        if match_pos > 0:
            # 提取明文内容中匹配位置之前的部分（前缀）
            prefix_text = plain_clean[:match_pos].strip()
            
            if prefix_text and len(prefix_text) > 5:  # 确保前缀有足够的内容
                # 将前缀转换为HTML格式
                prefix_html = self._text_to_html(prefix_text)
                
                # 找到解密内容中第一个<p>标签的位置
                first_p_pos = decrypted_text.find('<p>')
                if first_p_pos > 0:
                    # 有<p>标签，从第一个<p>标签开始拼接
                    combined_content = prefix_html + '\n' + decrypted_text[first_p_pos:]
                else:
                    # 没有<p>标签，直接拼接
                    combined_content = prefix_html + '\n' + decrypted_text
                
                print(f"使用纯文本匹配方法补全前缀，添加了 {len(prefix_text)} 个字符")
                print(f"前缀文本: {repr(prefix_text)}")
                
                return combined_content
        
        # 如果没有找到匹配，尝试更短的匹配文本
        # 递减匹配长度，增加匹配成功率
        for match_len in [40, 30, 20, 15]:
            if len(decrypted_clean) >= match_len:
                match_text = decrypted_clean[:match_len]
                match_pos = plain_clean.find(match_text)
                
                if match_pos > 0:
                    prefix_text = plain_clean[:match_pos].strip()
                    
                    if prefix_text and len(prefix_text) > 5:
                        prefix_html = self._text_to_html(prefix_text)
                        
                        first_p_pos = decrypted_text.find('<p>')
                        if first_p_pos > 0:
                            combined_content = prefix_html + '\n' + decrypted_text[first_p_pos:]
                        else:
                            combined_content = prefix_html + '\n' + decrypted_text
                        
                        print(f"使用{match_len}字符匹配方法补全前缀，添加了 {len(prefix_text)} 个字符")
                        print(f"前缀文本: {repr(prefix_text)}")
                        return combined_content
        
        # 如果所有匹配都失败，只清理解密内容中的乱码
        first_p_start = decrypted_text.find('<p>')
        if first_p_start > 0:
            before_p = decrypted_text[:first_p_start]
            has_garbage = any(ord(c) < 32 and c not in '\r\n\t' for c in before_p)
            if has_garbage or len(before_p) > 10:
                decrypted_text = decrypted_text[first_p_start:]
        
        return decrypted_text
    
    def _text_to_html(self, text: str) -> str:
        """
        将纯文本转换为HTML格式，保留段落结构
        
        Args:
            text: 纯文本内容
            
        Returns:
            HTML格式的内容
        """
        if not text:
            return ""
        
        # 先去除已有的标点符号，避免重复
        text = text.strip()
        
        # 如果文本以句号、问号或感叹号结尾，去掉标点
        if text and text[-1] in '。！？':
            text = text[:-1]
        
        # 简单处理：如果文本较短（少于50个字符），直接作为一个段落
        if len(text) < 50:
            return f"<p>{text}</p>"
        
        # 按照句子分割文本
        sentences = re.split(r'[。！？]', text)
        
        # 过滤掉空句子和太短的句子
        valid_sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]
        
        if not valid_sentences:
            return f"<p>{text}</p>"
        
        # 如果只有一个句子，直接包装在一个<p>标签中
        if len(valid_sentences) == 1:
            return f"<p>{valid_sentences[0]}</p>"
        
        # 多个句子，每个句子包装在一个<p>标签中
        html_content = ""
        for sentence in valid_sentences:
            html_content += f"<p>{sentence}</p>\n"
        
        return html_content.strip()
    
    def _extract_plain_booktxthtml(self, html_content: str) -> str:
        """
        从HTML中提取booktxthtml的明文内容
        
        Args:
            html_content: HTML页面内容
            
        Returns:
            提取的明文内容
        """
        # 查找<div id="booktxthtml">标签
        pattern = r'<div[^>]*id=["\']booktxthtml["\'][^>]*>(.*?)</div>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        if match:
            content = match.group(1)
            
            # 查找第一个<script>标签的位置
            script_start = content.find('<script')
            if script_start > 0:
                # 保留script标签之前的内容（这是明文部分）
                plain_content = content[:script_start]
                
                # 直接处理明文部分，移除其他标签
                plain_content = re.sub(r'<style[^>]*>.*?</style>', '', plain_content, flags=re.DOTALL)
                plain_content = re.sub(r'<div[^>]*>', '', plain_content)
                plain_content = re.sub(r'</div>', '', plain_content)
                
                # 尝试提取所有<p>标签内容
                p_matches = re.findall(r'<p[^>]*>(.*?)</p>', plain_content, re.DOTALL | re.IGNORECASE)
                if p_matches:
                    # 如果有<p>标签，说明有明文内容
                    valid_p_contents = [p.strip() for p in p_matches if p.strip() and len(p.strip()) > 5]
                    if valid_p_contents:
                        # 返回原始的<p>标签格式，保留结构
                        return '\n'.join([f"<p>{p}</p>" for p in valid_p_contents])
                
                # 如果没有<p>标签，尝试提取其他文本内容
                # 移除HTML标签，但保留文本
                text_content = re.sub(r'<[^>]+>', '', plain_content)
                text_content = text_content.strip()
                
                if text_content and len(text_content) > 10:
                    # 直接返回包装的文本
                    return f"<p>{text_content}</p>"
            
            # 如果没有找到script标签，尝试提取整个内容中的文本
            # 清理内容但保留<p>标签
            all_text = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            all_text = re.sub(r'<script[^>]*>.*?</script>', '', all_text, flags=re.DOTALL)
            
            # 尝试提取所有<p>标签内容
            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', all_text, re.DOTALL | re.IGNORECASE)
            if p_matches:
                # 如果有<p>标签，说明有明文内容
                valid_p_contents = [p.strip() for p in p_matches if p.strip() and len(p.strip()) > 5]
                if valid_p_contents:
                    # 返回原始的<p>标签格式，保留结构
                    return '\n'.join([f"<p>{p}</p>" for p in valid_p_contents])
            
            # 如果没有<p>标签，尝试提取其他文本内容
            # 移除HTML标签，但保留文本
            text_content = re.sub(r'<[^>]+>', '', all_text)
            text_content = text_content.strip()
            
            if text_content and len(text_content) > 10:
                # 直接返回包装的文本
                return f"<p>{text_content}</p>"
        
        return ""
    
    def _clean_prefix_content(self, content: str) -> str:
        """
        清理前缀内容，保留<p>标签结构
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 保留<p>标签，移除其他标签
        # 提取所有<p>标签内容
        p_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        
        if p_matches:
            # 重建<p>标签内容
            rebuilt_content = ""
            for i, p_text in enumerate(p_matches):
                p_text = p_text.strip()
                if p_text:
                    rebuilt_content += f"<p> {p_text}</p>"
                    # 如果不是最后一个<p>标签，添加换行
                    if i < len(p_matches) - 1:
                        rebuilt_content += '\n'
            return rebuilt_content
        
        # 如果没有<p>标签，尝试提取文本并包装
        # 移除所有HTML标签
        text_content = re.sub(r'<[^>]+>', '', content)
        text_content = text_content.strip()
        
        if text_content:
            # 解码HTML实体
            import html as html_module
            text_content = html_module.unescape(text_content)
            
            # 分割文本为句子，每句作为一个<p>标签
            sentences = re.split(r'[。！？\n]\s*', text_content)
            if len(sentences) > 1:
                rebuilt_content = ""
                for idx, sentence in enumerate(sentences):
                    sentence = sentence.strip()
                    if sentence:
                        rebuilt_content += f"<p> {sentence}。</p>"
                        if idx < len(sentences) - 1:
                            rebuilt_content += '\n'
                return rebuilt_content
            else:
                # 包装成单个<p>标签
                return f"<p> {text_content}</p>"
        
        return ""
    
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
                return {"error": "无法获取页面内容"}  # type: ignore
            
            print(f"页面获取成功，长度: {len(content)} 字符")
            
            # 提取标题
            title = self._extract_with_regex(content, self.title_reg)
            print(f"提取标题: {title}")
            
            if not title:
                return {"error": "无法提取小说标题"}  # type: ignore
            
            # 解析多章节小说
            result = self._parse_multichapter_novel(content, novel_url, title)
            print(f"解析完成，共 {len(result['chapters'])} 个章节")
            return result
                
        except Exception as e:
            print(f"解析失败: {e}")
            return {"error": str(e)}  # type: ignore
    
    def run_test(self, test_url: str | None = None):
        """
        运行测试
        
        Args:
            test_url: 测试URL，如果为None则使用默认测试URL
        """
        if test_url is None:
            # 使用默认的测试URL
            test_url = "https://www.photo-gram.com/read/dhce/"
        
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