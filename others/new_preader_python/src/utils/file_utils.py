"""
文件操作工具类，提供文件和目录操作功能
"""

import os

import shutil
import hashlib
from typing import List, Dict, Any, Set, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

class FileUtils:
    """文件操作工具类"""
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """
        获取文件扩展名
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件扩展名（小写）
        """
        return os.path.splitext(file_path)[1].lower()
    
    @staticmethod
    def get_file_name(file_path: str) -> str:
        """
        获取文件名（不含扩展名）
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件名
        """
        return os.path.splitext(os.path.basename(file_path))[0]
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        获取文件大小（字节）
        
        Args:
            file_path: 文件路径
            
        Returns:
            int: 文件大小
        """
        return os.path.getsize(file_path)
    
    @staticmethod
    def get_file_size_formatted(file_path: str) -> str:
        """
        获取格式化的文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 格式化的文件大小
        """
        size = FileUtils.get_file_size(file_path)
        return FileUtils.format_file_size(size)
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        格式化文件大小（不足1M用KB，大于等于1M用M）
        
        Args:
            size_bytes: 文件大小（字节）
            
        Returns:
            str: 格式化的文件大小
        """
        if size_bytes < 1024 * 1024:  # 小于1MB
            # 使用KB显示
            size_kb = size_bytes / 1024.0
            return f"{size_kb:.1f} KB"
        else:
            # 使用MB显示
            size_mb = size_bytes / (1024.0 * 1024.0)
            return f"{size_mb:.1f} M"
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = 'md5') -> str:
        """
        计算文件哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法（md5, sha1, sha256）
            
        Returns:
            str: 文件哈希值
        """
        hash_algorithms = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha256': hashlib.sha256
        }
        
        if algorithm not in hash_algorithms:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
        
        hash_obj = hash_algorithms[algorithm]()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    @staticmethod
    def ensure_dir_exists(dir_path: str) -> bool:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            dir_path: 目录路径
            
        Returns:
            bool: 是否成功创建或已存在
        """
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return False
    
    @staticmethod
    def list_files(dir_path: str, recursive: bool = False, 
                  file_extensions: Optional[List[str]] = None) -> List[str]:
        """
        列出目录中的文件
        
        Args:
            dir_path: 目录路径
            recursive: 是否递归查找
            file_extensions: 文件扩展名过滤列表
            
        Returns:
            List[str]: 文件路径列表
        """
        result = []
        
        if not os.path.exists(dir_path):
            logger.warning(f"目录不存在: {dir_path}")
            return result
        
        if file_extensions:
            file_extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                              for ext in file_extensions]
        
        if recursive:
            for root, _, files in os.walk(dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_extensions:
                        ext = os.path.splitext(file)[1].lower()
                        if ext in file_extensions:
                            result.append(file_path)
                    else:
                        result.append(file_path)
        else:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    if file_extensions:
                        ext = os.path.splitext(item)[1].lower()
                        if ext in file_extensions:
                            result.append(item_path)
                    else:
                        result.append(item_path)
        
        return result
    
    @staticmethod
    def copy_file(src_path: str, dst_path: str, overwrite: bool = False) -> bool:
        """
        复制文件
        
        Args:
            src_path: 源文件路径
            dst_path: 目标文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            bool: 是否成功复制
        """
        try:
            if os.path.exists(dst_path) and not overwrite:
                logger.warning(f"目标文件已存在: {dst_path}")
                return False
            
            # 确保目标目录存在
            dst_dir = os.path.dirname(dst_path)
            FileUtils.ensure_dir_exists(dst_dir)
            
            shutil.copy2(src_path, dst_path)
            return True
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return False
    
    @staticmethod
    def move_file(src_path: str, dst_path: str, overwrite: bool = False) -> bool:
        """
        移动文件
        
        Args:
            src_path: 源文件路径
            dst_path: 目标文件路径
            overwrite: 是否覆盖已存在的文件
            
        Returns:
            bool: 是否成功移动
        """
        try:
            if os.path.exists(dst_path) and not overwrite:
                logger.warning(f"目标文件已存在: {dst_path}")
                return False
            
            # 确保目标目录存在
            dst_dir = os.path.dirname(dst_path)
            FileUtils.ensure_dir_exists(dst_dir)
            
            shutil.move(src_path, dst_path)
            return True
        except Exception as e:
            logger.error(f"移动文件失败: {e}")
            return False
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否成功删除
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {file_path}")
                return False
            
            os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False
    
    @staticmethod
    def get_home_dir() -> str:
        """
        获取用户主目录
        
        Returns:
            str: 用户主目录路径
        """
        return str(Path.home())
    
    @staticmethod
    def get_app_data_dir(app_name: str) -> str:
        """
        获取应用数据目录
        
        Args:
            app_name: 应用名称
            
        Returns:
            str: 应用数据目录路径
        """
        home = FileUtils.get_home_dir()
        
        if os.name == 'nt':  # Windows
            app_data = os.path.join(os.environ.get('APPDATA', os.path.join(home, 'AppData', 'Roaming')))
            return os.path.join(app_data, app_name)
        elif os.name == 'posix':  # macOS, Linux
            if os.path.exists(os.path.join(home, 'Library')):  # macOS
                return os.path.join(home, 'Library', 'Application Support', app_name)
            else:  # Linux
                return os.path.join(home, '.config', app_name)
        else:
            return os.path.join(home, f'.{app_name.lower()}')
    
    @staticmethod
    def get_documents_dir() -> str:
        """
        获取用户文档目录
        
        Returns:
            str: 用户文档目录路径
        """
        home = FileUtils.get_home_dir()
        
        if os.name == 'nt':  # Windows
            return os.path.join(home, 'Documents')
        elif os.name == 'posix':  # macOS, Linux
            if os.path.exists(os.path.join(home, 'Documents')):
                return os.path.join(home, 'Documents')
            else:
                return home
        else:
            return home