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
        选项列表，格式为 [(value, label), ...]
    """
    parsers = get_available_parsers()
    options = []
    
    for parser in parsers:
        # 使用文件名作为值，文件名作为显示标签（不包含"解析器"字样）
        options.append((parser['filename'], parser['filename']))
    
    # 如果没有任何解析器，返回空列表
    return options

def create_parser(parser_name: str, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None) -> BaseParser:
    """
    创建指定名称的解析器实例
    
    Args:
        parser_name: 解析器文件名（不带.py后缀）
        proxy_config: 代理配置
        novel_site_name: 从数据库获取的网站名称，用于作者信息
        
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
            # 创建解析器实例并传递代理配置和数据库网站名称
            return parser_class(proxy_config=proxy_config, novel_site_name=novel_site_name)
        else:
            raise ValueError(f"解析器 {parser_name} 类不存在")
            
    except ImportError:
        raise ValueError(f"解析器 {parser_name} 不存在")
    except ValueError:
        # 重新抛出ValueError，避免重复拼接错误消息
        raise
    except Exception as e:
        raise ValueError(f"创建解析器 {parser_name} 失败: {e}")