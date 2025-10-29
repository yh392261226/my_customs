"""
TXT文件解析器
"""

import os

from typing import Dict, Any, List

from src.parsers.base_parser import BaseParser

from src.utils.logger import get_logger

logger = get_logger(__name__)

class TxtParser(BaseParser):
    """TXT文件解析器"""
    
    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析TXT文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        logger.info(f"解析TXT文件: {file_path}")
        
        try:
            # 尝试不同的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                logger.error(f"无法解码文件: {file_path}")
                raise ValueError(f"无法解码文件: {file_path}")
            
            # 预处理内容：清理常见格式标记和乱码
            content = self._preprocess_content(content)
            
            # 提取元数据
            metadata = self.extract_metadata(content)
            
            # 如果没有从内容中提取到标题，使用文件名作为标题
            if "title" not in metadata or not metadata["title"]:
                metadata["title"] = os.path.splitext(os.path.basename(file_path))[0]
            
            # 提取章节
            chapters = self.extract_chapters(content)
            
            return {
                "content": content,
                "title": metadata.get("title", ""),
                "author": metadata.get("author", "未知作者"),
                "chapters": chapters,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"解析TXT文件时出错: {e}")
            raise
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".txt"]
    
    def _preprocess_content(self, content: str) -> str:
        """
        预处理文本内容，清理常见格式标记和乱码
        
        Args:
            content: 原始文本内容
            
        Returns:
            str: 清理后的文本内容
        """
        if not content:
            return content
        
        import re
        
        # 常见格式标记清理规则
        # 1. 清理连续的 ** 标记（可能是格式标记）
        content = re.sub(r'\*\*+', ' ', content)
        
        # 2. 清理其他常见乱码模式
        # 连续的特殊字符组合
        content = re.sub(r'[\*#@$%&_]{2,}', ' ', content)
        
        # 3. 清理过长的空格序列
        content = re.sub(r'\s{5,}', '    ', content)
        
        # 4. 清理无效的控制字符（保留空格、换行等）
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
        # 5. 确保文本有基本的段落分隔
        # 如果整个文本没有换行符，尝试按句子分割（更加保守的方式）
        if '\n' not in content and len(content) > 500:
            # 非常保守的段落分割：只处理明显的句子结束
            # 避免在数字、缩写等位置错误分割
            # 只在句号后面跟非数字、非标点的字符时添加换行
            content = re.sub(r'([。！？])([^\d\s。！？，；：""])', r'\1\n\2', content)
        
        # 6. 清理行首和行尾的多余空格
        lines = content.split('\n')
        cleaned_lines = [line.strip() for line in lines]
        content = '\n'.join(cleaned_lines)
        
        return content.strip()