"""
87NB小说网解析器 - www.87nb.com
基于PHP版本转换而来
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

class Nb87Parser:
    """87NB小说网解析器"""
    
    name = "87NB小说网"
    description = "87NB小说网整本小说爬取解析器"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
        """
        self.base_url = "https://www.87nb.com"
        self.session = requests.Session()
        self.chapter_count = 0
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        
        # 特殊字符替换映射
        self.char_replacements = {
            '<img src="/zi/n1.png" width="30px" height="28px"/>': '奶',
            '<img src="/zi/d2.png" width="30px" height="28px"/>': '屌',
            '<img src="/zi/r5.png" width="30px" height="28px"/>': '日',
            '<img src="/zi/q1.png" width="30px" height="28px"/>': '情',
            '<img src="/zi/k1.png" width="30px" height="28px"/>': '口',
            '<img src="/zi/n2.png" width="30px" height="28px"/>': '女',
            '<img src="/zi/r3.png" width="30px" height="28px"/>': '人',
            '<img src="/zi/s1.png" width="30px" height="28px"/>': '射',
            '<img src="/zi/j1.png" width="30px" height="28px"/>': '精',
            '<img src="/zi/y1.png" width="30px" height="28px"/>': '液',
            '<img src="/zi/r2.png" width="30px" height="28px"/>': '乳',
            '<img src="/zi/j4.png" width="30px" height="28px"/>': '鸡',
            '<img src="/zi/t1.png" width="30px" height="28px"/>': '头',
            '<img src="/zi/r1.png" width="30px" height="28px"/>': '肉',
            '<img src="/zi/b4.png" width="30px" height="28px"/>': '棒',
            '<img src="/zi/g2.png" width="30px" height="28px"/>': '龟',
            '<img src="/zi/c2.png" width="30px" height="28px"/>': '操',
            '<img src="/zi/c4.png" width="30px" height="28px"/>': '肏',
            '<img src="/zi/g1.png" width="30px" height="28px"/>': '肛',
            '<img src="/zi/c3.png" width="30px" height="28px"/>': '插',
            '<img src="/zi/y2.png" width="30px" height="28px"/>': '淫',
            '<img src="/zi/x1.png" width="30px" height="28px"/>': '穴',
            '<img src="/zi/b2.png" width="30px" height="28px"/>': '暴',
            '<img src="/zi/b3.png" width="30px" height="28px"/>': '屄',
            '<img src="/zi/d3.png" width="30px" height="28px"/>': '洞',
            '<img src="/zi/x2.png" width="30px" height="28px"/>': '性',
            '<img src="/zi/l3.png" width="30px" height="28px"/>': '乱',
            '<img src="/zi/a1.png" width="30px" height="28px"/>': '爱',
            '<img src="/zi/j3.png" width="30px" height="28px"/>': '交',
            '<img src="/zi/p1.png" width="30px" height="28px"/>': '喷',
            '<img src="/zi/c5.png" width="30px" height="28px"/>': '潮',
            '<img src="/zi/b1.png" width="30px" height="28px"/>': '爆',
            '<img src="/zi/f1.png" width="30px" height="28px"/>': '妇',
            '<img src="/zi/j2.png" width="30px" height="28px"/>': '奸',
            '<img src="/zi/n3.png" width="30px" height="28px"/>': '嫩',
            '<img src="/zi/l1.png" width="30px" height="28px"/>': '轮',
            '<img src="/zi/d1.png" width="30px" height="28px"/>': '荡',
            '<img src="/zi/l2.png" width="30px" height="28px"/>': '浪',
            '<img src="/zi/c1.png" width="30px" height="28px"/>': '草',
            '<img src="/zi/j5.png" width="30px" height="28px"/>': '妓',
            '<img src="/zi/b5.png" width="30px" height="28px"/>': '逼',
            '<img src="/zi/g3.png" width="30px" height="28px"/>': '干',
            '<img src="/zi/g4.png" width="30px" height="28px"/>': '股',
            '<img src="/zi/s2.png" width="30px" height="28px"/>': '深',
            '<img src="/zi/f2.png" width="30px" height="28px"/>': '粉',
            '<img src="/zi/r4.png" width="30px" height="28px"/>': '入',
            '<img src="/zi/b6.png" width="30px" height="28px"/>': '巴',
            '<img src="/zi/p3.png" width="30px" height="28px"/>': '屁',
            '<img src="/zi/p2.png" width="30px" height="28px"/>': '破',
            '<img src="/zi/l4.png" width="30px" height="28px"/>': '裸',
            '<img src="/zi/t2.png" width="30px" height="28px"/>': '臀',
        }
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（87NB小说网不需要列表页解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # 87NB小说网直接通过小说ID抓取整本，不需要列表解析
        return []
    
    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """获取书籍首页的标题、简介与状态（87NB）
           标题/简介：div.bookintro 的第一个 p
           状态：div.bookdes 的第一个 p（如“小说状态：连载 | 0万字”）"""
        if not novel_id.isdigit():
            return None
        novel_url = f"{self.base_url}/lt/{novel_id}.html"
        content = self._get_url_content(novel_url)
        if not content:
            return None
        title = ""
        desc = ""
        status = ""
        # 优先使用 BeautifulSoup 解析
        try:
            from bs4 import BeautifulSoup  # 解析 HTML
            soup = BeautifulSoup(content, "html.parser")
            intro = soup.find("div", class_="bookintro")
            if intro:
                ps = intro.find_all("p")
                if ps:
                    p0 = ps[0]
                    a0 = p0.find("a")
                    if a0:
                        title = (a0.get_text(strip=True) or a0.get("title") or "").strip()
                    full_text = p0.get_text(separator="", strip=True)
                    if "小说简介：" in full_text:
                        desc = full_text.split("小说简介：", 1)[1].strip()
                    else:
                        a_text = a0.get_text(strip=True) if a0 else ""
                        desc = full_text.replace(a_text, "", 1).strip()
            # 状态：bookdes 第一个 p
            bookdes = soup.find("div", class_="bookdes")
            if bookdes:
                p_list = bookdes.find_all("p")
                if p_list:
                    # 清理不间断空格
                    status = p_list[0].get_text(separator="", strip=True).replace('\xa0', ' ').replace('&nbsp;', ' ').strip()
        except Exception:
            pass
        # 若 Soup 失败，使用正则兜底
        if not (title or desc):
            try:
                title_match = re.search(r'<div class="bookintro">.*?<p>\s*<a[^>]*title="([^"]+)"[^>]*>.*?</a>', content, re.DOTALL)
                if not title_match:
                    title_match = re.search(r'<div class="bookintro">.*?<p>\s*<a[^>]*>([^<]+)</a>', content, re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()
                desc_match = re.search(r'<div class="bookintro">.*?<p>\s*<a.*?</a>\s*(.*?)</p>', content, re.DOTALL)
                if desc_match:
                    raw = desc_match.group(1)
                    raw_text = re.sub(r'<[^>]+>', '', raw)
                    desc = raw_text.split("小说简介：", 1)[-1].strip()
            except Exception:
                pass
        # 状态兜底：从 bookdes 第一个 p 取文本
        if not status:
            try:
                status_match = re.search(r'<div class="bookdes">.*?<p>(.*?)</p>', content, re.DOTALL)
                if status_match:
                    raw_status = status_match.group(1)
                    status = re.sub(r'<[^>]+>', '', raw_status)
                    status = status.replace('&nbsp;', ' ').replace('\xa0', ' ').strip()
            except Exception:
                pass
        if not title and not desc and not status:
            return None
        return {"title": title, "desc": desc, "status": status}
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取整本小说内容
        
        Args:
            novel_id: 小说ID（URL中的数字部分）
            
        Returns:
            小说详情信息
        """
        if not novel_id.isdigit():
            raise ValueError("小说ID必须是数字")
        
        # 构建小说详情页URL
        novel_url = f"{self.base_url}/lt/{novel_id}.html"
        
        # 获取小说详情页内容
        content = self._get_url_content(novel_url)
        if not content:
            raise Exception(f"无法获取小说详情页: {novel_url}")
        
        # 提取小说标题
        title_match = re.search(r'<h1><a href=".*?" title="(.*?)">', content)
        if not title_match:
            raise Exception("无法提取小说标题")
        
        title = title_match.group(1).strip()
        print(f"开始处理 [ {title} ]")

        # 提取小说简介（更健壮：优先用Soup；其次正则；最后允许为空，不抛异常）
        desc = ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            intro = soup.find("div", class_="bookintro")
            if intro:
                p = intro.find("p")
                if p:
                    # 文本为 <p><a ...>标题</a>简介文本</p>
                    a = p.find("a")
                    full_text = p.get_text(separator="", strip=True)
                    a_text = a.get_text(strip=True) if a else ""
                    if full_text:
                        desc = full_text[len(a_text):].strip() if a_text and full_text.startswith(a_text) else full_text
        except Exception:
            pass
        if not desc:
            desc_match = re.search(r'<div class="bookintro"><p><a[^>]*>.*?</a>(.*?)</p>', content, re.DOTALL)
            if desc_match:
                raw = desc_match.group(1)
                desc = re.sub(r'<[^>]+>', '', raw).strip()
        # 允许简介缺失
        
        # 提取第一章URL
        first_chapter_match = re.search(r'<a href="(.*?)">开始阅读', content)
        if not first_chapter_match:
            raise Exception("无法提取第一章URL")
        
        first_chapter_url = first_chapter_match.group(1)
        
        # 创建小说内容
        novel_content = {
            'title': title,
            'author': '未知作者',
            'novel_id': novel_id,
            'url': novel_url,
            'chapters': []
        }
        
        # 抓取所有章节内容
        self._get_all_chapters(first_chapter_url, novel_content)
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _get_all_chapters(self, start_url: str, novel_content: Dict[str, Any]) -> None:
        """
        抓取所有章节内容
        
        Args:
            start_url: 起始章节URL
            novel_content: 小说内容字典
        """
        current_url = start_url
        self.chapter_count = 0
        
        while current_url:
            self.chapter_count += 1
            print(f"正在抓取第 {self.chapter_count} 章: {current_url}")
            
            # 获取章节内容
            chapter_content = self._get_chapter_content(current_url)
            if chapter_content:
                novel_content['chapters'].append(chapter_content)
                print(f"√ 第 {self.chapter_count} 章抓取成功")
            else:
                print(f"× 第 {self.chapter_count} 章抓取失败")
            
            # 获取下一章URL
            next_url = self._get_next_chapter_url(current_url)
            current_url = next_url
            
            # 章节间延迟
            time.sleep(1)
    
    def _get_chapter_content(self, url: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        获取章节内容
        
        Args:
            url: 章节URL
            retry_count: 重试次数
            
        Returns:
            章节内容字典
        """
        max_retries = 5
        
        try:
            content = self._get_url_content(urljoin(self.base_url, url))
            if not content:
                if retry_count < max_retries:
                    wait_time = min(60, 2 ** (retry_count + 1))
                    print(f"网络请求失败，正在重试 [{retry_count + 1}/{max_retries}]，等待{wait_time}秒")
                    time.sleep(wait_time)
                    return self._get_chapter_content(url, retry_count + 1)
                else:
                    print(f"章节抓取失败（已达最大重试）: {url}")
                    return None
            
            # 尝试匹配内容
            content_match = re.search(r'<div id="booktxt">(.*?)(?:<div class="report">|</div>\s*<a id="nextBtn")', content, re.DOTALL)
            if not content_match:
                content_match = re.search(r'<div id="booktxt">(.*)', content, re.DOTALL)
            
            if not content_match:
                if retry_count < max_retries:
                    wait_time = min(60, 2 ** (retry_count + 1))
                    print(f"内容匹配失败，正在重试 [{retry_count + 1}/{max_retries}]，等待{wait_time}秒")
                    time.sleep(wait_time)
                    return self._get_chapter_content(url, retry_count + 1)
                else:
                    print(f"内容匹配失败（已达最大重试）: {url}")
                    return None
            
            # 清理内容
            chapter_text = content_match.group(1)
            
            # 应用特殊字符替换
            for old_char, new_char in self.char_replacements.items():
                chapter_text = chapter_text.replace(old_char, new_char)
            
            # 清理HTML标签和多余空格
            chapter_text = re.sub(r'<p>|</p>|</div>|<div id="booktxt">|<>|</>|\s+', '', chapter_text)
            chapter_text = re.sub(r'<divclass="readpage">.*?</body>', '', chapter_text, flags=re.DOTALL)
            chapter_text = re.sub(r'<divclass="readpage">|</html>|</body>', '', chapter_text)
            
            return {
                'chapter_number': self.chapter_count,
                'title': f"第 {self.chapter_count} 章",
                'content': chapter_text,
                'url': url
            }
            
        except Exception as e:
            print(f"获取章节内容时出错: {e}")
            if retry_count < max_retries:
                wait_time = min(60, 2 ** (retry_count + 1))
                print(f"正在重试 [{retry_count + 1}/{max_retries}]，等待{wait_time}秒")
                time.sleep(wait_time)
                return self._get_chapter_content(url, retry_count + 1)
            return None
    
    def _get_next_chapter_url(self, current_url: str) -> Optional[str]:
        """
        获取下一章URL
        
        Args:
            current_url: 当前章节URL
            
        Returns:
            下一章URL，如果没有则返回None
        """
        try:
            content = self._get_url_content(urljoin(self.base_url, current_url))
            if content:
                next_match = re.search(r'<a rel="next" href="(.*?)">下一', content)
                if next_match and next_match.group(1):
                    return next_match.group(1)
        except Exception as e:
            print(f"获取下一章URL时出错: {e}")
        
        return None
    
    def _get_url_content(self, url: str, max_retries: int = 5) -> Optional[str]:
        """
        获取URL内容
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
            
        Returns:
            页面内容
        """
        retry_count = 0
        
        # 根据代理配置决定是否使用代理
        proxies = None
        if self.proxy_config.get('enabled') and self.proxy_config.get('proxy_url'):
            proxies = {
                'http': self.proxy_config['proxy_url'],
                'https': self.proxy_config['proxy_url']
            }
        
        while retry_count < max_retries:
            try:
                response = self.session.get(url, timeout=60, proxies=proxies)
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    return response.text
                else:
                    print(f"HTTP错误: {response.status_code} - {url}")
            except Exception as e:
                print(f"请求失败: {e} - {url}")
            
            retry_count += 1
            if retry_count < max_retries:
                wait_time = min(60, 2 ** retry_count)
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
        
        print(f"达到最大重试次数({max_retries})，放弃请求: {url}")
        return None
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        将小说内容保存到文件
        
        Args:
            novel_content: 小说内容
            storage_folder: 存储文件夹路径
            
        Returns:
            保存的文件路径
        """
        import os
        
        # 确保存储文件夹存在
        os.makedirs(storage_folder, exist_ok=True)
        
        # 生成文件名：小说标题.txt
        filename = f"{novel_content['title']}.txt"
        file_path = os.path.join(storage_folder, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入小说标题
            f.write(f"{novel_content['title']}\n\n")
            
            # 写入所有章节
            for chapter in novel_content['chapters']:
                f.write(f"第 {chapter['chapter_number']} 章\n")
                f.write(f"\t{chapter['content']}\n\n")
        
        print(f"小说已保存到: {file_path}")
        return file_path


# 使用示例
if __name__ == "__main__":
    parser = Nb87Parser()
    
    # 示例：抓取小说ID为30689的小说
    try:
        novel_content = parser.parse_novel_detail("30689")
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")