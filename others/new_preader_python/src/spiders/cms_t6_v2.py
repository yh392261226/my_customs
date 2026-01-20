"""
CMS T6 小说网站解析器 - 短篇article.php解析版本
适用于使用相同CMS结构的网站，特征为 /article.php?id={id} 格式
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from src.utils.logger import get_logger
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class CmsT6Parser(BaseParser):
    """CMS T6 小说解析器 - 短篇article.php解析版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None, site_url: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
            site_url: 网站URL，用于自动生成base_url
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 如果提供了site_url，则自动解析并设置base_url
        if site_url:
            self._setup_from_site_url(site_url)
        
        # 添加通用的请求头
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'DNT': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # 如果base_url已设置，更新Referer头
        if self.base_url:
            self.session.headers.update({'Referer': self.base_url})
    
    def _setup_from_site_url(self, site_url: str) -> None:
        """
        从网站URL自动设置base_url
        
        Args:
            site_url: 网站URL，如 https://www.example.com/
        """
        logger.info(f"开始从site_url设置base_url: {site_url}")
        
        # 解析URL获取域名
        parsed_url = urlparse(site_url)
        # CMS T6 不需要修改域名，直接使用原始URL
        self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        logger.info(f"设置base_url: {self.base_url}")
        
        # 如果没有提供novel_site_name，使用域名作为名称
        if not self.novel_site_name or self.novel_site_name == self.name:
            # 使用完整域名作为名称，包括www前缀
            self.novel_site_name = parsed_url.netloc
            logger.info(f"设置novel_site_name: {self.novel_site_name}")
    
    @classmethod
    def create_from_site_data(cls, site_data: Dict[str, Any], proxy_config: Optional[Dict[str, Any]] = None):
        """
        从数据库中的网站数据创建解析器实例
        
        Args:
            site_data: 数据库中的网站数据
            proxy_config: 代理配置
            
        Returns:
            解析器实例
        """
        return cls(
            proxy_config=proxy_config,
            novel_site_name=site_data.get('name'),
            site_url=site_data.get('url')
        )
    
    @classmethod
    def create_all_parsers_from_db(cls, db_path: Optional[str] = None):
        """
        从数据库中获取所有CMS T6网站并创建解析器实例
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            
        Returns:
            List[Dict[str, Any]]: 包含网站信息和对应解析器的列表
        """
        from src.core.database_manager import DatabaseManager
        
        # 创建数据库管理器
        db_manager = DatabaseManager(db_path) if db_path else DatabaseManager()
        
        # 获取所有CMS T6网站并创建解析器
        return db_manager.create_cms_t6_parsers()
    
    # 基本信息 - 会被动态设置
    name = "CMS T6 通用解析器"
    description = "CMS T6 通用article.php解析器，适用于 /article.php?id= 格式的短篇网站"
    base_url = ""  # 将在初始化时设置
    
    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*>([^<]+)</h1>',  # 标准h1标题
        r'<title>([^<]+)</title>',  # 备用标题
    ]
    
    # 简介（文章描述）正则表达式
    desc_reg = [
        r'<div\s+class="article-desc"[^>]*>([^<]+)</div>',  # 标准文章描述
        r'<div[^>]*class="[^"]*article-desc[^"]*"[^>]*>([^<]+)</div>',  # 备用文章描述
        r'<div[^>]*class="[^"]*desc[^"]*"[^>]*>([^<]+)</div>',  # 通用描述
    ]
    
    # 内容正则表达式 - 根据要求，是空的class属性
    content_reg = [
        r'<div\s+class="">([\s\S]*?)</div>',  # 空class属性的内容
        r'<div[^>]*class=""[^>]*>([\s\S]*?)</div>',  # 空class属性的内容（带其他属性）
        r'<div[^>]*>([\s\S]*?)</div>',  # 通用div内容
    ]
    
    book_type = ["短篇"]  # 这类网站主要为短篇小说
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL，适配CMS T6格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        if not self.base_url:
            logger.error("base_url未设置，无法生成有效的URL")
            raise ValueError("base_url未设置，请在初始化时提供有效的site_url")
            
        return f"{self.base_url}/article.php?id={novel_id}"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（CMS T6网站主要为单篇短篇小说，不需要列表解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容
        
        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        for regex in regex_list:
            match = re.search(regex, content, re.IGNORECASE | re.DOTALL)
            if match:
                extracted = match.group(1).strip()
                if extracted:
                    return extracted
        return ""
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        解析小说详情并抓取小说内容
        
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
            # 尝试从title标签中提取并移除后缀
            title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # 移除常见的后缀
                title = re.sub(r'[-_].*$', '', title).strip()
        
        if not title:
            raise Exception("无法提取小说标题")
        
        # 提取简介
        description = self._extract_with_regex(content, self.desc_reg)
        if not description:
            description = "无简介"
        
        print(f"开始处理 [ {title} ] - 类型: 短篇")
        
        # 提取内容
        novel_content = self._parse_single_chapter_novel(content, novel_url, title, description)
        
        print(f'[ {title} ] 完成')
        return novel_content
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str, description: str) -> Dict[str, Any]:
        """
        解析单章节小说（CMS T6网站主要为短篇小说）
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            description: 小说简介
            
        Returns:
            小说内容字典
        """
        # 提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)
        
        if not chapter_content:
            # 如果标准正则失败，尝试备用方法
            chapter_content = self._fallback_extract_content(content)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 清理内容 - 移除HTML标签
        cleaned_content = self._clean_content(chapter_content)
        
        return {
            'title': title,
            'description': description,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': cleaned_content,
                'url': novel_url
            }]
        }
    
    def _clean_content(self, content: str) -> str:
        """
        清理小说内容，移除HTML标签和不需要的元素
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        if not content:
            return ""
        
        # 移除script标签
        content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', content)
        # 移除style标签
        content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', content)
        # 移除注释
        content = re.sub(r'<!--[\s\S]*?-->', '', content)
        
        # 移除广告相关元素
        content = re.sub(r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>[\s\S]*?</div>', '', content)
        content = re.sub(r'<ins[^>]*>[\s\S]*?</ins>', '', content)
        content = re.sub(r'<iframe[^>]*>[\s\S]*?</iframe>', '', content)
        content = re.sub(r'<a[^>]*href="[^"]*javascript[^"]*"[^>]*>[\s\S]*?</a>', '', content)
        
        # 清理HTML标签，保留必要的换行
        content = re.sub(r'<br\s*/?>', '\n', content)
        content = re.sub(r'<p[^>]*>', '\n', content)
        content = re.sub(r'</p>', '\n', content)
        content = re.sub(r'<div[^>]*>', '\n', content)
        content = re.sub(r'</div>', '\n', content)
        content = re.sub(r'<span[^>]*>', '', content)
        content = re.sub(r'</span>', '', content)
        
        # 移除所有HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理空白字符
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'^\s+', '', content)
        content = re.sub(r'\s+$', '', content)
        
        # 替换HTML实体
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&quot;', '"')
        content = content.replace('&#39;', "'")
        content = content.replace('&#x27;', "'")
        
        # 清理特殊字符
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        return content.strip()
    
    def _fallback_extract_content(self, content: str) -> str:
        """
        备用内容提取方法，当标准正则失败时使用
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容
        """
        # 方法1: 使用平衡括号匹配算法
        result = self._extract_balanced_content(content)
        if result:
            return result
        
        # 方法2: 查找最长的文本块
        result = self._find_longest_text_block(content)
        if result:
            return result
        
        # 方法3: 尝试查找包含中文内容的区域
        result = self._find_chinese_content(content)
        if result:
            return result
        
        return ""
    
    def _extract_balanced_content(self, content: str) -> str:
        """
        使用平衡括号匹配算法提取内容
        
        Args:
            content: 页面内容
            
        Returns:
            提取的内容
        """
        # 查找可能的内容容器标签
        container_patterns = [
            r'<div[^>]*class=""[^>]*>',
            r'<div[^>]*>',
            r'<article[^>]*>',
            r'<section[^>]*>'
        ]
        
        for pattern in container_patterns:
            start_match = re.search(pattern, content, re.IGNORECASE)
            if start_match:
                start_pos = start_match.end()
                container_tag = re.search(r'<(\w+)', pattern).group(1)
                
                # 使用平衡匹配算法找到对应的结束标签
                stack = 1
                pos = start_pos
                
                while stack > 0 and pos < len(content):
                    # 查找下一个开始或结束标签
                    tag_match = re.search(r'</?\w+[^>]*>', content[pos:])
                    if not tag_match:
                        break
                    
                    tag = tag_match.group(0)
                    tag_pos = pos + tag_match.start()
                    
                    # 检查是否是相同类型的标签
                    if re.match(r'<\s*/?\s*' + container_tag + r'\b', tag, re.IGNORECASE):
                        if tag.startswith('</'):
                            stack -= 1
                        else:
                            stack += 1
                    
                    pos = tag_pos + len(tag)
                    
                    if stack == 0:
                        # 找到匹配的结束标签
                        return content[start_pos:tag_pos]
        
        return ""
    
    def _find_longest_text_block(self, content: str) -> str:
        """
        查找最长的文本块
        
        Args:
            content: 页面内容
            
        Returns:
            最长的文本块
        """
        # 移除脚本和样式
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        
        # 查找所有可能的内容块
        blocks = re.findall(r'>([^><]{100,})<', cleaned)
        
        if blocks:
            # 返回最长的块
            return max(blocks, key=len)
        
        return ""
    
    def _find_chinese_content(self, content: str) -> str:
        """
        查找包含中文内容的区域
        
        Args:
            content: 页面内容
            
        Returns:
            包含中文的内容
        """
        # 查找包含连续中文文本的区域
        chinese_pattern = r'[\u4e00-\u9fff]{10,}'
        
        # 查找包含中文的标签块
        matches = re.findall(r'<[^>]*>([^<]*' + chinese_pattern + r'[^<]*)</[^>]*>', content)
        
        if matches:
            # 合并所有匹配的内容
            combined = ' '.join(matches)
            if len(combined) > 100:
                return combined
        
        return ""
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型（CMS T6网站主要为短篇小说）
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"
    
    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        
        Args:
            url: 小说URL
            
        Returns:
            小说ID
        """
        # 从URL中提取ID部分
        match = re.search(r'article\.php\?id=(\d+)', url)
        if match:
            return match.group(1)
        
        # 备用方法：从URL路径中提取
        parts = url.split('=')
        if len(parts) > 1:
            return parts[1]
        
        return "unknown"


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用site_url自动配置
    parser = CmsT6Parser(site_url="https://234516.xyz/")
    
    # 测试单篇小说
    try:
        novel_id = "109956"  # 测试ID
        novel_content = parser.parse_novel_detail(novel_id)
        
        # 打印小说信息
        print(f"标题: {novel_content['title']}")
        if 'description' in novel_content:
            print(f"简介: {novel_content['description']}")
        print(f"内容长度: {len(novel_content['chapters'][0]['content'])}")
        print(f"内容前100字符: {novel_content['chapters'][0]['content'][:100]}")
        
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
    
    # 示例2: 从数据库创建所有CMS T6解析器
    print("\n=== 从数据库创建所有CMS T6解析器 ===")
    try:
        parser_sites = CmsT6Parser.create_all_parsers_from_db()
        print(f"已创建 {len(parser_sites)} 个CMS T6解析器")
        
        for site_info in parser_sites:
            site_data = site_info['site_data']
            print(f"- 网站: {site_data.get('name')} ({site_data.get('url')})")
            print(f"  存储文件夹: {site_data.get('storage_folder')}")
            print(f"  代理启用: {site_data.get('proxy_enabled', False)}")
    except Exception as e:
        print(f"从数据库创建解析器失败: {e}")