"""
TXT文件保存工具
提供将小说内容保存为TXT文件的功能
"""

import os
import re
from typing import Dict, Any, List
from datetime import datetime
from send2trash import send2trash

from src.utils.logger import get_logger

logger = get_logger(__name__)

class TxtSaver:
    """TXT文件保存器"""
    
    def __init__(self, output_dir: str = "saved_novels"):
        """
        初始化保存器
        
        Args:
            output_dir: 输出目录，默认为当前目录下的saved_novels文件夹
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def save_novel(self, novel_data: Dict[str, Any], filename: str = None) -> str:
        """
        保存小说为TXT文件
        
        Args:
            novel_data: 小说数据，包含title, author, chapters等字段
            filename: 自定义文件名，如果为None则自动生成
            
        Returns:
            str: 保存的文件路径
        """
        try:
            # 获取小说基本信息
            title = novel_data.get("title", "未知标题")
            author = novel_data.get("author", "未知作者")
            chapters = novel_data.get("chapters", [])
            
            # 生成文件名
            if not filename:
                filename = self._generate_filename(title, author)
            
            file_path = os.path.join(self.output_dir, filename)
            
            # 如果文件已存在，添加序号
            counter = 1
            original_path = file_path
            while os.path.exists(file_path):
                name, ext = os.path.splitext(original_path)
                file_path = f"{name}_{counter}{ext}"
                counter += 1
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入文件头信息
                self._write_header(f, title, author)
                
                # 写入章节内容
                self._write_chapters(f, chapters)
                
                # 写入文件尾信息
                self._write_footer(f)
            
            logger.info(f"小说保存成功: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存小说失败: {e}")
            raise
    
    def save_chapter(self, chapter_data: Dict[str, Any], filename: str = None) -> str:
        """
        保存单个章节为TXT文件
        
        Args:
            chapter_data: 章节数据，包含title, content等字段
            filename: 自定义文件名
            
        Returns:
            str: 保存的文件路径
        """
        try:
            title = chapter_data.get("title", "未知章节")
            content = chapter_data.get("content", "")
            
            if not filename:
                filename = self._generate_chapter_filename(title)
            
            file_path = os.path.join(self.output_dir, filename)
            
            # 如果文件已存在，添加序号
            counter = 1
            original_path = file_path
            while os.path.exists(file_path):
                name, ext = os.path.splitext(original_path)
                file_path = f"{name}_{counter}{ext}"
                counter += 1
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n")
                f.write("=" * 50 + "\n\n")
                f.write(content)
                f.write("\n\n")
                f.write("=" * 50 + "\n")
                f.write(f"保存时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            logger.info(f"章节保存成功: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"保存章节失败: {e}")
            raise
    
    def _generate_filename(self, title: str, author: str) -> str:
        """
        生成文件名
        
        Args:
            title: 小说标题
            author: 作者
            
        Returns:
            str: 文件名
        """
        # 清理文件名中的非法字符
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_author = re.sub(r'[<>:"/\\|?*]', '_', author)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_title}_by_{safe_author}_{timestamp}.txt"
    
    def _generate_chapter_filename(self, title: str) -> str:
        """
        生成章节文件名
        
        Args:
            title: 章节标题
            
        Returns:
            str: 文件名
        """
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_title}_{timestamp}.txt"
    
    def _write_header(self, file_handle, title: str, author: str):
        """
        写入文件头信息
        
        Args:
            file_handle: 文件句柄
            title: 小说标题
            author: 作者
        """
        file_handle.write(f"{title}\n")
        file_handle.write(f"作者：{author}\n")
        file_handle.write("=" * 60 + "\n\n")
        file_handle.write(f"保存时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file_handle.write("=" * 60 + "\n\n")
    
    def _write_chapters(self, file_handle, chapters: List[Dict[str, Any]]):
        """
        写入章节内容
        
        Args:
            file_handle: 文件句柄
            chapters: 章节列表
        """
        for i, chapter in enumerate(chapters, 1):
            chapter_title = chapter.get("title", f"第{i}章")
            chapter_content = chapter.get("content", "")
            
            file_handle.write(f"{chapter_title}\n")
            file_handle.write("-" * 40 + "\n\n")
            
            # 清理和格式化内容
            cleaned_content = self._clean_content(chapter_content)
            file_handle.write(cleaned_content)
            
            file_handle.write("\n\n")
            file_handle.write("-" * 40 + "\n\n")
    
    def _write_footer(self, file_handle):
        """
        写入文件尾信息
        
        Args:
            file_handle: 文件句柄
        """
        file_handle.write("\n" + "=" * 60 + "\n")
        file_handle.write("小说保存完成\n")
        file_handle.write("=" * 60 + "\n")
    
    def _clean_content(self, content: str) -> str:
        """
        清理和格式化内容
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清理后的内容
        """
        if not content:
            return ""
        
        # 清理常见的HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理过多的空格和换行
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # 确保段落之间有适当的间距
        content = re.sub(r'([。！？])([^\n])', r'\1\n\2', content)
        
        return content.strip()
    
    def get_saved_files(self) -> List[str]:
        """
        获取已保存的文件列表
        
        Returns:
            List[str]: 文件路径列表
        """
        if not os.path.exists(self.output_dir):
            return []
        
        files = []
        for filename in os.listdir(self.output_dir):
            if filename.endswith('.txt'):
                files.append(os.path.join(self.output_dir, filename))
        
        return sorted(files)
    
    def delete_saved_file(self, file_path: str) -> bool:
        """
        删除保存的文件（移动到回收站）
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if os.path.exists(file_path):
                send2trash(file_path)
                logger.info(f"文件已移至回收站: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False