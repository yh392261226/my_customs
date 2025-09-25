"""
解析器工厂，用于根据文件类型选择合适的解析器
"""

import os

from typing import Dict, Type, Optional, Any, List

from src.parsers.base_parser import BaseParser
from src.parsers.txt_parser import TxtParser
from src.parsers.markdown_parser import MarkdownParser
from src.parsers.epub_parser import EpubParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.pdf_encrypt_parser import PdfEncryptParser
from src.parsers.mobi_parser import MobiParser
from src.parsers.azw_parser import AzwParser

from src.utils.logger import get_logger

logger = get_logger(__name__)

class ParserFactory:
    """解析器工厂类"""
    
    def __init__(self):
        """初始化解析器工厂"""
        self._parsers: Dict[str, Type[BaseParser]] = {}
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """注册默认解析器"""
        self.register_parser(TxtParser())
        self.register_parser(MarkdownParser())
        self.register_parser(EpubParser())
        # 注入 App 实例，确保解析期可显示 GUI 弹窗
        try:
            from src.ui.app import get_app_instance
            _app_instance = get_app_instance()
        except Exception:
            _app_instance = None
        if not _app_instance:
            try:
                from textual.app import App as _TextualApp  # type: ignore
                _app_instance = _TextualApp.get_app()
            except Exception:
                _app_instance = None
        self.register_parser(PdfParser(app=_app_instance))
        self.register_parser(MobiParser())
        self.register_parser(AzwParser())
    
    def register_parser(self, parser: BaseParser):
        """
        注册解析器
        
        Args:
            parser: 解析器实例
        """
        for format_ext in parser.get_supported_formats():
            self._parsers[format_ext.lower()] = parser.__class__
        
        logger.debug(f"已注册解析器 {parser.__class__.__name__} 支持格式: {parser.get_supported_formats()}")
    
    async def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        解析文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        parser = self.get_parser(file_path)
        if parser is None:
            raise ValueError(f"不支持的文件格式: {os.path.splitext(file_path)[1]}")
            
        return await parser.parse(file_path)

    def get_parser(self, file_path: str) -> Optional[BaseParser]:
        """
        根据文件路径获取合适的解析器
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[BaseParser]: 解析器实例，如果没有找到合适的解析器则返回None
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext in self._parsers:
            parser_class = self._parsers[ext]
            
            # 对于PDF文件，需要检查是否加密
            if ext == '.pdf':
                return self._get_pdf_parser(file_path, parser_class)
            
            # 其他格式直接实例化
            return parser_class()
        
        logger.warning(f"未找到支持格式 {ext} 的解析器")
        return None
    
    def _get_pdf_parser(self, file_path: str, parser_class: Type[BaseParser]) -> BaseParser:
        """
        获取PDF解析器，根据文件是否加密选择不同的解析器
        
        Args:
            file_path: PDF文件路径
            parser_class: 解析器类
            
        Returns:
            BaseParser: PDF解析器实例
        """
        # 检查PDF是否加密
        is_encrypted = self._check_pdf_encryption(file_path)
        
        # 获取App实例
        try:
            from src.ui.app import get_app_instance
            app_instance = get_app_instance()
        except Exception:
            app_instance = None
        
        if not app_instance:
            try:
                from textual.app import App
                app_instance = App.get_app() if hasattr(App, 'get_app') else None
            except Exception:
                app_instance = None
        
        if is_encrypted:
            # 使用加密PDF解析器
            from src.parsers.pdf_encrypt_parser import PdfEncryptParser
            return PdfEncryptParser(app=app_instance)
        else:
            # 使用普通PDF解析器
            from src.parsers.pdf_parser import PdfParser
            return PdfParser(app=app_instance)
    
    def _check_pdf_encryption(self, file_path: str) -> bool:
        """
        检查PDF文件是否加密
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 是否加密
        """
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return reader.is_encrypted
        except Exception as e:
            logger.debug(f"检查PDF加密状态时出错: {e}")
            return False
    
    def get_supported_formats(self) -> List[str]:
        """
        获取所有支持的文件格式
        
        Returns:
            list: 支持的文件格式列表
        """
        return list(self._parsers.keys())


# 创建全局解析器工厂实例
parser_factory = ParserFactory()