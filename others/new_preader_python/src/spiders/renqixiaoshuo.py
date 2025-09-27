"""
热奇小说网解析器 - www.renqixiaoshuo.net
基于PHP版本转换而来
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

class RenqixiaoshuoParser:
    """热奇小说网解析器"""
    
    name = "热奇小说网"
    description = "热奇小说网整本小说爬取解析器"
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置，格式为 {'enabled': bool, 'proxy_url': str}
        """
        self.base_url = "https://www.renqixiaoshuo.net"
        self.session = requests.Session()
        self.chapter_count = 0
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        
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
        解析小说列表页（热奇小说网不需要列表页解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        # 热奇小说网直接通过小说ID抓取整本，不需要列表解析
        return []
    
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
        novel_url = f"{self.base_url}/b/{novel_id}"
        
        # 获取小说详情页内容
        content = self._get_url_content(novel_url)
        if not content:
            raise Exception(f"无法获取小说详情页: {novel_url}")
        
        # 提取小说标题
        title_match = re.search(r'<div class="name hang1"><h1>(.*?)</h1>', content)
        if not title_match:
            raise Exception("无法提取小说标题")
        
        title = title_match.group(1).strip()
        print(f"开始处理 [ {title} ]")
        
        # 提取第一章URL
        first_chapter_match = re.search(r'<a id="btnread" href="(.*?)" class="stayd">开始阅读', content)
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
            
            # 提取章节内容
            content_match = re.search(r'<div class="tjc-cot">(.*?)</div>', content, re.DOTALL)
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
            chapter_text = re.sub(r'<p>|</p>|\s+', '', chapter_text)
            
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
                next_match = re.search(r'<a href="(.*?)">下一章 >', content)
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
    parser = RenqixiaoshuoParser()
    
    # 示例：抓取小说ID为123的小说
    try:
        novel_content = parser.parse_novel_detail("123")
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        print(f"抓取失败: {e}")