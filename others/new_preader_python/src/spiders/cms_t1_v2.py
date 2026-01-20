"""
CMS T1 小说网站解析器 - 通用JSON API版本
继承自 BaseParser，用于处理使用相同CMS结构的网站
"""

from typing import Dict, Any, List, Optional
import json
import re
from urllib.parse import urlparse
from src.utils.logger import get_logger
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

class CmsT1Parser(BaseParser):
    """CMS T1 小说解析器 - 通用JSON API版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None, site_url: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
            site_url: 网站URL，用于自动生成API地址
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 记录初始化开始
        logger.info(f"初始化CMS T1解析器，site_url: {site_url}, novel_site_name: {novel_site_name}")
        
        # 如果提供了site_url，则自动解析并设置base_url和name
        if site_url:
            logger.info(f"提供site_url，开始设置base_url")
            self._setup_from_site_url(site_url)
            logger.info(f"设置完成，base_url: {self.base_url}")
        else:
            logger.warning("未提供site_url，base_url可能为空")
        
        # 如果base_url仍然为空，设置一个默认值以避免错误
        if not self.base_url or self.base_url.strip() == "":
            logger.error(f"base_url未设置或为空，当前值: '{self.base_url}'")
            # 使用默认值，避免生成错误的URL
            self.base_url = "https://vue.example.com/"
            logger.warning(f"使用默认base_url: {self.base_url}，请在初始化时提供有效的site_url")
        else:
            logger.info(f"base_url已正确设置: {self.base_url}")
    
    def _setup_from_site_url(self, site_url: str) -> None:
        """
        从网站URL自动设置base_url
        
        Args:
            site_url: 网站URL，如 https://www.sdxs.xyz/
        """
        logger.info(f"开始从site_url设置base_url: {site_url}")
        
        # 解析URL获取域名
        parsed_url = urlparse(site_url)
        domain = parsed_url.netloc
        logger.info(f"解析出域名: {domain}")
        
        # 去掉www前缀
        if domain.startswith('www.'):
            domain = domain[4:]
            logger.info(f"去掉www前缀后域名: {domain}")
        
        # 构建API基础URL - 将域名中的第一部分作为API子域名
        # 例如: sdxs.xyz -> vue.sdxs.xyz
        domain_parts = domain.split('.')
        logger.info(f"域名分割结果: {domain_parts}")
        
        if len(domain_parts) >= 2:
            api_domain = f"vue.{domain_parts[0]}.{domain_parts[1]}"
            self.base_url = f"https://{api_domain}/"
            logger.info(f"构建API域名: {api_domain}, base_url: {self.base_url}")
        else:
            # 如果域名格式不标准，使用默认格式
            self.base_url = f"https://vue.{domain}/"
            logger.warning(f"域名格式不标准，使用默认格式: {self.base_url}")
        
        # 如果没有提供novel_site_name，使用域名作为名称
        if not self.novel_site_name or self.novel_site_name == self.name:
            self.novel_site_name = domain
            logger.info(f"设置novel_site_name: {self.novel_site_name}")
        
        logger.info(f"_setup_from_site_url完成，base_url: {self.base_url}, novel_site_name: {self.novel_site_name}")
    
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
        从数据库中获取所有CMS T1网站并创建解析器实例
        
        Args:
            db_path: 数据库路径，如果为None则使用默认路径
            
        Returns:
            List[Dict[str, Any]]: 包含网站信息和对应解析器的列表
        """
        from src.core.database_manager import DatabaseManager
        
        # 创建数据库管理器
        db_manager = DatabaseManager(db_path) if db_path else DatabaseManager()
        
        # 获取所有CMS T1网站并创建解析器
        return db_manager.create_cms_t1_parsers()
    
    # 基本信息 - 会被动态设置
    name = "CMS T1 通用解析器"
    description = "CMS T1 通用JSON API解析器"
    base_url = ""  # 将在初始化时设置
    
    # 正则表达式配置 - 由于是JSON API，不需要HTML正则
    title_reg = []
    content_reg = []
    
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配CMS T1的API格式
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说API URL
        """
        # 确保base_url已设置
        if not self.base_url or self.base_url == "":
            logger.error("base_url未设置或为空，无法生成有效的API URL")
            # 使用默认值，避免生成错误的URL
            self.base_url = "https://vue.example.com/"
            logger.warning(f"使用默认base_url: {self.base_url}，请在初始化时提供有效的site_url")
            
        return f"{self.base_url}vue.php?act=detail&id={novel_id}"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，CMS T1通常是短篇小说网站
        
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
        match = re.search(r'id=(\d+)', url)
        return match.group(1) if match else "unknown"
    
    def parse_novel_detail(self, novel_id: str) -> Dict[str, Any]:
        """
        重写小说详情解析方法，处理JSON格式的API响应
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说详情信息
        """
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        
        try:
            novel_url = self.get_novel_url(novel_id)
            content = self._get_url_content(novel_url)
            
            if not content:
                raise Exception(f"无法获取小说页面: {novel_url}")
            
            # 解析JSON响应
            # 检查是否有SQL错误或其他HTML错误信息
            if '<FONT COLOR="#FF0000">' in content:
                # 尝试从HTML错误信息中提取JSON部分
                # 查找第一个出现的左花括号
                json_start = content.find('{')
                if json_start > 0:
                    content = content[json_start:]
                    logger.warning("检测到SQL错误，尝试从响应中提取JSON部分")
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败，响应内容: {content[:200]}")
                raise ValueError(f"JSON解析失败: {e}")
            
            # 打印JSON数据的结构
            logger.info(f"JSON数据结构: {list(data.keys())}")
            
            # 检查detail字段是否存在
            if 'detail' not in data:
                logger.error(f"API响应中没有detail字段，可用字段: {list(data.keys())}")
                raise ValueError(f"API响应中没有找到detail字段，可用字段: {list(data.keys())}")
            
            detail = data['detail']
            
            # 检查detail是否为None
            if detail is None:
                logger.error("detail字段为None")
                raise ValueError("detail字段为None")
            
            # 获取标题和内容
            title = detail.get('title', '')
            content_html = detail.get('src', '')
            
            logger.info(f"标题: {title}, 内容长度: {len(content_html) if content_html else 0}")
            
            # 检查标题是否为空
            if not title:
                logger.warning(f"标题为空，detail字段内容: {detail}")
                
                # 尝试从newlist字段中获取小说信息
                if 'newlist' in data and data['newlist']:
                    for item in data['newlist']:
                        if isinstance(item, dict) and item.get('id') == novel_id:
                            title = item.get('title', '')
                            content_html = item.get('src', '')
                            logger.info(f"从newlist字段中找到小说信息，标题: {title}")
                            break
                
                # 如果仍然没有标题，尝试使用小说ID作为标题
                if not title:
                    title = f"小说ID-{novel_id}"
                    logger.warning(f"无法获取标题，使用小说ID作为标题: {title}")
            
            # 检查内容是否为空
            if not content_html:
                logger.warning(f"内容为空，detail字段内容: {detail}")
                
                # 尝试从newlist字段中获取小说内容
                if 'newlist' in data and data['newlist']:
                    for item in data['newlist']:
                        if isinstance(item, dict) and item.get('id') == novel_id:
                            content_html = item.get('src', '')
                            logger.info(f"从newlist字段中找到小说内容，长度: {len(content_html) if content_html else 0}")
                            break
                
                # 如果仍然没有内容，使用默认内容
                if not content_html:
                    content_html = "<p>无法获取小说内容</p>"
                    logger.warning("无法获取内容，使用默认内容")
            
            # 最后检查
            if not title:
                raise ValueError("未获取到小说标题")
            
            if not content_html or content_html == "<p>无法获取小说内容</p>":
                logger.warning("无法获取小说内容，生成默认内容")
                content_html = f"<p>无法获取小说 {title} 的内容，可能是因为API错误或数据库问题。</p>"
            
            # 执行后处理函数清理HTML内容
            content_text = super()._clean_html_content(content_html)
            
            # 自动检测书籍类型
            book_type = self._detect_book_type(content_text)
            
            print(f"开始处理 [ {title} ] - 类型: {book_type}")
            
            # 直接返回小说内容（跳过基类的正则提取步骤）
            novel_content = {
                "title": title,
                "author": self.novel_site_name,  # 使用数据库中的网站名称
                "content": content_text,
                "url": novel_url,
                "book_type": book_type,
                "status": "已完成",  # 短篇小说通常已完成
                "chapters": [
                    {
                        "title": title,
                        "content": content_text,
                        "url": novel_url
                    }
                ]
            }
            
            print(f'[ {title} ] 完成')
            return novel_content
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"解析小说详情失败: {e}")
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - CMS T1通常不需要列表页解析
        
        Args:
            url: 小说列表页URL
            
        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    # 示例1: 使用site_url自动配置
    parser = CmsT1Parser(site_url="https://www.sdxs.xyz/")
    
    # 测试单篇小说
    try:
        novel_id = "21234"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
    
    # 示例2: 从数据库创建所有CMS T1解析器
    print("\n=== 从数据库创建所有CMS T1解析器 ===")
    try:
        parser_sites = CmsT1Parser.create_all_parsers_from_db()
        print(f"已创建 {len(parser_sites)} 个CMS T1解析器")
        
        for site_info in parser_sites:
            site_data = site_info['site_data']
            print(f"- 网站: {site_data.get('name')} ({site_data.get('url')})")
            print(f"  存储文件夹: {site_data.get('storage_folder')}")
            print(f"  代理启用: {site_data.get('proxy_enabled', False)}")
    except Exception as e:
        print(f"从数据库创建解析器失败: {e}")
    
    # 示例3: 使用BaseParser工厂方法创建CMS T1解析器
    print("\n=== 使用BaseParser工厂方法创建CMS T1解析器 ===")
    try:
        from src.core.database_manager import DatabaseManager
        db_manager = DatabaseManager()
        cms_sites = db_manager.get_cms_t1_sites()
        
        if cms_sites:
            site_data = cms_sites[0]  # 使用第一个网站作为示例
            parser = BaseParser.create_cms_t1_parser(site_data)
            print(f"使用工厂方法创建了解析器: {parser.novel_site_name}")
        else:
            print("数据库中没有CMS T1网站")
    except Exception as e:
        print(f"使用工厂方法创建解析器失败: {e}")