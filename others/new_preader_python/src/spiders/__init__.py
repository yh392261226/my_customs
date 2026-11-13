"""
爬虫解析器模块 - 支持工厂模式和继承基类 v2
"""

import os
import importlib
from typing import Dict, List, Any, Optional, Type
from src.utils.logger import get_logger
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)

def get_available_parsers() -> List[Dict[str, Any]]:
    """
    获取所有可用的解析器
    
    Returns:
        解析器信息列表，包含文件名和描述
    """
    parsers = []
    spiders_dir = os.path.dirname(__file__)
    
    # 检查目录是否存在
    if not os.path.exists(spiders_dir):
        return parsers
    
    for filename in os.listdir(spiders_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            parser_name = filename[:-3]  # 去掉.py后缀
            # 直接使用文件名作为解析器信息
            parsers.append({
                'filename': parser_name,
                'name': parser_name,
                'description': f"{parser_name} 解析器",
                'class': None  # 暂时不加载类
            })
    
    return parsers

def get_parser_options() -> List[tuple[str, str]]:
    """
    获取解析器下拉框选项
    
    Returns:
        选项列表，格式为 [(value, label), ...]，按首字母升序排列
    """
    parsers = get_available_parsers()
    options = []
    
    for parser in parsers:
        # 使用文件名作为值，文件名作为显示标签（不包含"解析器"字样）
        options.append((parser['filename'], parser['filename']))
    
    # 按首字母升序排列
    options.sort(key=lambda x: x[0].lower())
    
    # 如果没有任何解析器，返回空列表
    return options

def create_parser(parser_name: str, proxy_config: Optional[Dict[str, Any]] = None,
                  novel_site_name: Optional[str] = None, site_url: Optional[str] = None,
                  site: Optional[Dict[str, Any]] = None) -> BaseParser:
    """
    创建指定名称的解析器实例
    
    Args:
        parser_name: 解析器文件名（不带.py后缀）
        proxy_config: 代理配置
        novel_site_name: 从数据库获取的网站名称，用于作者信息
        site_url: 网站URL，用于CMS解析器自动配置API地址
        site: 完整的书籍网站配置字典；用于读取「爬取头」设置（normal/mobile）。
              未传时按 site_url 回查数据库，仍查不到则按「普通」处理。
        
    Returns:
        解析器实例
        
    Raises:
        ValueError: 如果解析器不存在或加载失败
    """
    try:
        # 动态导入模块
        module = importlib.import_module(f'src.spiders.{parser_name}')
        
        # 查找解析器类（优先查找继承自BaseParser的类）
        parser_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, BaseParser) and 
                attr != BaseParser):
                parser_class = attr
                break
        
        # 如果没有找到继承BaseParserV2的类，查找继承自BaseParser的类
        if not parser_class:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseParser) and 
                    attr != BaseParser):
                    parser_class = attr
                    break
        
        # 如果没有找到继承BaseParser的类，回退到旧版查找逻辑
        if not parser_class:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    hasattr(attr, 'name') and 
                    hasattr(attr, 'description')):
                    parser_class = attr
                    break
        
        if parser_class:
            # 创建解析器实例并传递代理配置、数据库网站名称和网站URL
            # 检查解析器类是否支持site_url参数
            import inspect
            init_signature = inspect.signature(parser_class.__init__)
            if 'site_url' in init_signature.parameters:
                parser = parser_class(proxy_config=proxy_config, novel_site_name=novel_site_name, site_url=site_url)
            else:
                parser = parser_class(proxy_config=proxy_config, novel_site_name=novel_site_name)

            # 在解析器构造完成后注入「爬取头」：
            # 很多子类（如 cms_t4_v2）会在 __init__ 里二次覆盖 session.headers，
            # 因此必须放在实例化之后做最后一次覆盖。
            try:
                from src.utils.crawl_headers import apply_to_parser, resolve_site_mode_by_url
                effective_site = site
                if effective_site is None:
                    effective_site = {
                        "url": site_url or "",
                        "crawl_header_mode": resolve_site_mode_by_url(site_url),
                    }
                apply_to_parser(parser, effective_site)
            except Exception as e:
                logger.warning(f"应用书籍网站爬取头设置失败，按普通模式继续: {e}")

            return parser
        else:
            raise ValueError(f"解析器 {parser_name} 类不存在")
            
    except ImportError:
        raise ValueError(f"解析器 {parser_name} 不存在")
    except ValueError:
        # 重新抛出ValueError，避免重复拼接错误消息
        raise
    except Exception as e:
        raise ValueError(f"创建解析器 {parser_name} 失败: {e}")