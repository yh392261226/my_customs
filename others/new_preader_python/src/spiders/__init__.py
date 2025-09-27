"""
爬虫解析器模块
"""

import os
import importlib
from typing import Dict, List, Any, Optional
from src.utils.logger import get_logger

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

def create_parser(parser_name: str, proxy_config: Optional[Dict[str, Any]] = None) -> Any:
    """
    创建指定名称的解析器实例
    
    Args:
        parser_name: 解析器文件名（不带.py后缀）
        proxy_config: 代理配置
        
    Returns:
        解析器实例
        
    Raises:
        ValueError: 如果解析器不存在或加载失败
    """
    try:
        # 动态导入模块
        module = importlib.import_module(f'src.spiders.{parser_name}')
        
        # 查找解析器类
        parser_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                hasattr(attr, 'name') and 
                hasattr(attr, 'description')):
                parser_class = attr
                break
        
        if parser_class:
            # 创建解析器实例并传递代理配置
            return parser_class(proxy_config=proxy_config)
        else:
            raise ValueError(f"解析器 {parser_name} 类不存在")
            
    except ImportError:
        raise ValueError(f"解析器 {parser_name} 不存在")
    except ValueError:
        # 重新抛出ValueError，避免重复拼接错误消息
        raise
    except Exception as e:
        raise ValueError(f"创建解析器 {parser_name} 失败: {e}")