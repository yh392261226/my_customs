"""
CMS T3 小说网站解析器 - 通用HTML解析版本
适用于使用相同CMS结构的网站，内容在div class="entry"中
支持两种URL格式: /index.php/art/detail/id/ 和 /artdetail-
"""

import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from src.utils.logger import get_logger
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class CmsT3Parser(BaseParser):
    """CMS T3 小说解析器 - 通用HTML解析版本"""
    
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
        
        # 默认URL格式，可以通过detect_url_format方法自动检测
        self.url_format = "index"  # 可选值: "index" 或 "artdetail"
    
    def _setup_from_site_url(self, site_url: str) -> None:
        """
        从网站URL自动设置base_url
        
        Args:
            site_url: 网站URL，如 https://www.example.com/
        """
        logger.info(f"开始从site_url设置base_url: {site_url}")
        
        # 解析URL获取域名
        parsed_url = urlparse(site_url)
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
        parser = cls(
            proxy_config=proxy_config,
            novel_site_name=site_data.get('name'),
            site_url=site_data.get('url')
        )
        
        # 根据网站域名自动检测URL格式
        domain = site_data.get('url', '').lower()
        parser_name = site_data.get('parser', '').lower()
        
        # 特定网站使用特定格式
        if 'auate' in domain or parser_name == 'auate_v2' or 'wenzigouhun' in domain:
            parser.url_format = 'artdetail'
        else:
            parser.url_format = 'index'
        
        logger.info(f"网站 {site_data.get('name')} 使用URL格式: {parser.url_format}")
        
        return parser
    
    @classmethod
    def create_all_parsers_from_db(cls, db_path: Optional[str] = None):
        """
        从数据库中获取所有CMS T3网站并创建解析器实例
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            
        Returns:
            List[Dict[str, Any]]: 包含网站信息和对应解析器的列表
        """
        from src.core.database_manager import DatabaseManager
        
        # 创建数据库管理器
        db_manager = DatabaseManager(db_path) if db_path else DatabaseManager()
        
        # 获取所有CMS T3网站并创建解析器
        return db_manager.create_cms_t3_parsers()
    
    # 基本信息 - 会被动态设置
    name = "CMS T3 通用解析器"
    description = "CMS T3 通用HTML解析器，适用于内容在div class=\"entry\"中的网站"
    base_url = ""  # 将在初始化时设置
    
    # 正则表达式配置
    title_reg = [
        r'<h2[^>]*>([^<]+)</h2>',  # 标准标题
        r'<title[^>]*>([^<]+)</title>',  # 备用标题
        r'<h1[^>]*>([^<]+)</h1>',  # 通用h1标题
    ]
    
    content_reg = [
        r'<div[^>]*class="entry"[^>]*>\s*<div[^>]*>([\s\S]*?)</div>\s*</div>',  # 主内容提取
        r'<div[^>]*class="entry"[^>]*>([\s\S]*?)</div>',  # 备用：整个entry内容
        r'<div[^>]*id="post-[^>]*>\s*<div[^>]*class="entry"[^>]*>([\s\S]*?)</div>',  # 包含post-id的提取
    ]
    
    status_reg = [
        r"<span[^>]*class=['\"]tags['\"][^>]*>([^<]+)</span>",  # 来源信息
        r"来源[：:]([^<]+)"  # 备用模式
    ]
    
    book_type = ["短篇"]  # 这类网站主要为短篇小说
    
    def detect_url_format(self, test_id: str = "1") -> str:
        """
        自动检测网站使用的URL格式
        
        Args:
            test_id: 用于测试的小说ID
            
        Returns:
            URL格式: "index" 或 "artdetail"
        """
        # 测试两种URL格式，看哪个能正常访问
        index_url = f"{self.base_url}/index.php/art/detail/id/{test_id}.html"
        artdetail_url = f"{self.base_url}/artdetail-{test_id}.html"
        
        # 先尝试index格式
        try:
            response = self._get_url_content(index_url, check_content=False)
            if response and '<div class="entry"' in response:
                self.url_format = "index"
                logger.info(f"检测到URL格式: index ({index_url})")
                # 保存检测到的格式到实例属性，供后续使用
                self._url_format_detected = True
                return "index"
        except Exception as e:
            logger.debug(f"index格式URL测试失败: {e}")
        
        # 再尝试artdetail格式
        try:
            response = self._get_url_content(artdetail_url, check_content=False)
            if response and '<div class="entry"' in response:
                self.url_format = "artdetail"
                logger.info(f"检测到URL格式: artdetail ({artdetail_url})")
                # 保存检测到的格式到实例属性，供后续使用
                self._url_format_detected = True
                return "artdetail"
        except Exception as e:
            logger.debug(f"artdetail格式URL测试失败: {e}")
        
        # 默认使用index格式
        logger.warning("无法确定URL格式，使用默认的index格式")
        self.url_format = "index"
        # 保存检测到的格式到实例属性，供后续使用
        self._url_format_detected = True
        return "index"
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL，适配CMS T3格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        if not self.base_url:
            logger.error("base_url未设置，无法生成有效的URL")
            raise ValueError("base_url未设置，请在初始化时提供有效的site_url")
        
        # 根据URL格式生成不同格式的URL
        if self.url_format == "artdetail":
            return f"{self.base_url}/artdetail-{novel_id}.html"
        else:  # 默认为index格式
            return f"{self.base_url}/index.php/art/detail/id/{novel_id}.html"
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页（CMS T3网站主要为单篇短篇小说，不需要列表解析）
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []
    
    def _extract_title(self, content: str) -> str:
        """
        提取小说标题
        
        Args:
            content: 页面内容
            
        Returns:
            小说标题
        """
        # 优先从h2标签提取
        for pattern in self.title_reg:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                # 清理标题中的特殊字符和多余空格
                title = re.sub(r'[『』]', '', title).strip()
                if title:
                    return title
        
        # 如果从h2标签提取失败，尝试从title标签提取
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            # 清理标题中的网站名称
            title = re.sub(r'\s*-\s*风情小说.*$', '', title).strip()
            title = re.sub(r'\s*-\s*Auate.*$', '', title).strip()
            if title:
                return title
        
        return ""
    
    def _extract_status(self, content: str) -> str:
        """
        提取小说状态（来源信息）
        
        Args:
            content: 页面内容
            
        Returns:
            状态信息
        """
        for pattern in self.status_reg:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                status = match.group(1).strip()
                # 清理HTML标签
                status = re.sub(r'<[^>]+>', '', status)
                status = re.sub(r'\s+', ' ', status)
                return status.strip()
        
        return "未知来源"
    
    def _extract_content(self, content: str) -> str:
        """
        提取小说内容
        
        Args:
            content: 页面内容
            
        Returns:
            小说内容
        """
        for pattern in self.content_reg:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_content = match.group(1).strip()
                # 清理掉版权信息
                cleaned_content = self._remove_copyright_info(extracted_content)
                return cleaned_content
        
        # 如果标准提取失败，尝试更宽松的提取
        # 查找包含p标签的内容区域
        p_content_match = re.search(
            r'<div[^>]*class="entry"[^>]*>(.*?)(?:<div[^>]*class="copyright"|<div[^>]*class="relatedpost")',
            content, re.IGNORECASE | re.DOTALL
        )
        if p_content_match:
            extracted_content = p_content_match.group(1).strip()
            # 清理掉版权信息
            cleaned_content = self._remove_copyright_info(extracted_content)
            return cleaned_content
        
        return ""
    
    def _remove_copyright_info(self, content: str) -> str:
        """
        清理掉<div class="copyright"></div>标签中的全部内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 移除整个copyright div标签及其内容
        content = re.sub(r'<div[^>]*class="copyright"[^>]*>[\s\S]*?</div>', '', content, flags=re.IGNORECASE)
        
        # 移除可能存在的其他版权信息标签
        content = re.sub(r'<div[^>]*class="copyright-info"[^>]*>[\s\S]*?</div>', '', content, flags=re.IGNORECASE)
        
        # 移除可能存在的版权文本
        content = re.sub(r'版权声明[\s\S]*?(?:<\/div>|$)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'版权信息[\s\S]*?(?:<\/div>|$)', '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _clean_and_format_content(self, content: str) -> str:
        """
        清理和格式化小说内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        # 1. 清理HTML标签，保留p标签用于段落分隔
        # 首先将p标签转换为换行符
        content = re.sub(r'</p>', '\n\n', content)
        # 然后移除所有其他HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 2. 替换HTML实体
        content = content.replace('&nbsp;', ' ').replace('\xa0', ' ')
        
        # 3. 清理多余的空格和换行
        # 合并多个连续空格
        content = re.sub(r' +', ' ', content)
        # 合并多个连续换行符
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = re.sub(r'\n+', '\n', content)
        
        # 4. 清理开头和结尾的空格
        content = content.strip()
        
        # 5. 确保每段开头没有空格
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:  # 只保留非空行
                cleaned_lines.append(cleaned_line)
        
        return '\n\n'.join(cleaned_lines)
    
    def test_url_format_with_content(self, novel_id: str) -> tuple:
        """
        测试URL格式并返回有效的内容和URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            tuple: (success, content, novel_url, url_format)
        """
        # 如果URL格式未确定，先自动检测（只在第一次请求时执行）
        if not hasattr(self, '_url_format_detected') or not self._url_format_detected:
            logger.info("首次使用，检测URL格式...")
            
            # 根据网站域名预设初始格式
            domain = self.base_url.lower()
            if 'auate' in domain:
                self.url_format = "artdetail"  # Auate网站通常使用artdetail格式
            else:
                self.url_format = "index"     # 默认使用index格式
                
            logger.info(f"预设URL格式: {self.url_format}")
        
        # 测试当前格式
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if content and '<div class="entry"' in content:
            logger.info(f"URL格式 {self.url_format} 有效")
            self._url_format_detected = True
            return True, content, novel_url, self.url_format
        
        # 如果当前格式无效，尝试切换格式
        logger.warning(f"当前URL格式({self.url_format})无法获取有效内容，尝试切换格式")
        old_format = self.url_format
        self.url_format = "artdetail" if self.url_format == "index" else "index"
        
        # 使用新格式重新获取URL和内容
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)
        
        if content and '<div class="entry"' in content:
            logger.info(f"切换到URL格式 {self.url_format} 成功")
            self._url_format_detected = True
            return True, content, novel_url, self.url_format
        else:
            logger.error(f"两种URL格式都无法获取有效内容，恢复原格式: {old_format}")
            self.url_format = old_format
            self._url_format_detected = True
            return False, "", "", old_format
    
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
        # 测试URL格式并获取内容
        if hasattr(self, '_url_format_detected') and self._url_format_detected:
            logger.info(f"使用已检测的URL格式: {self.url_format}")
        else:
            logger.info(f"检测URL格式...")
        
        success, content, novel_url, url_format = self.test_url_format_with_content(novel_id)
        
        if not success:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取标题
        title = self._extract_title(content)
        if not title:
            raise Exception("无法提取小说标题")
        
        # 提取状态（来源信息）
        status = self._extract_status(content)
        
        # 提取内容
        novel_content = self._extract_content(content)
        if not novel_content:
            raise Exception("无法提取小说内容")
        
        print(f"开始处理 [ {title} ] - 状态: {status}")
        
        # 清理和格式化内容
        cleaned_content = self._clean_and_format_content(novel_content)
        
        return {
            'title': title,
            'author': self.novel_site_name or self.name,
            'novel_id': novel_id,
            'url': novel_url,
            'description': f"短篇小说 - {status}",
            'status': status,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': cleaned_content,
                'url': novel_url
            }]
        }
    
    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型（CMS T3网站主要为短篇小说）
        
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
        # 尝试从index格式URL中提取ID
        match = re.search(r'/id/(\d+)\.html', url)
        if match:
            return match.group(1)
        
        # 尝试从artdetail格式URL中提取ID
        match = re.search(r'/artdetail-(\d+)\.html', url)
        if match:
            return match.group(1)
        
        # 备用方法：从URL路径中提取
        parts = url.split('/')
        for part in parts:
            if part.endswith('.html'):
                # 移除可能的前缀
                part = re.sub(r'^(artdetail-|id)', '', part)
                return part.replace('.html', '')
        
        return "unknown"


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用site_url自动配置
    parser = CmsT3Parser(site_url="https://www.example.com/")
    
    # 测试单篇小说
    try:
        novel_id = "12345"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
    
    # 示例2: 从数据库创建所有CMS T3解析器
    print("\n=== 从数据库创建所有CMS T3解析器 ===")
    try:
        parser_sites = CmsT3Parser.create_all_parsers_from_db()
        print(f"已创建 {len(parser_sites)} 个CMS T3解析器")
        
        for site_info in parser_sites:
            site_data = site_info['site_data']
            print(f"- 网站: {site_data.get('name')} ({site_data.get('url')})")
            print(f"  存储文件夹: {site_data.get('storage_folder')}")
            print(f"  代理启用: {site_data.get('proxy_enabled', False)}")
    except Exception as e:
        print(f"从数据库创建解析器失败: {e}")
    
    # 示例3: 使用BaseParser工厂方法创建CMS T3解析器
    print("\n=== 使用BaseParser工厂方法创建CMS T3解析器 ===")
    try:
        from src.core.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        cms_sites = db_manager.get_cms_t3_sites()
        
        if cms_sites:
            site_data = cms_sites[0]  # 使用第一个网站作为示例
            parser = BaseParser.create_cms_t3_parser(site_data)
            print(f"使用工厂方法创建了解析器: {parser.novel_site_name}")
        else:
            print("数据库中没有CMS T3网站")
    except Exception as e:
        print(f"使用工厂方法创建解析器失败: {e}")