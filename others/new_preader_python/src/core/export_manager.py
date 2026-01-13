"""
导出管理器
用于将书签、笔记等内容导出为多种格式
"""

import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.utils.logger import get_logger
from src.core.bookmark import BookmarkManager
from src.core.book import Book

logger = get_logger(__name__)

class ExportManager:
    """导出管理器"""
    
    def __init__(self, bookmark_manager: BookmarkManager):
        """
        初始化导出管理器
        
        Args:
            bookmark_manager: 书签管理器实例
        """
        self.bookmark_manager = bookmark_manager
    
    def export_bookmarks_to_markdown(self, book: Book, output_path: str) -> bool:
        """
        将书籍的书签导出为Markdown格式
        
        Args:
            book: 书籍对象
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            bookmarks = self.bookmark_manager.get_bookmarks(book.path)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {book.title} - 书签导出\n\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                if bookmarks:
                    f.write("## 书签列表\n\n")
                    for bookmark in bookmarks:
                        f.write(f"### 页码 {bookmark['page']} (位置 {bookmark['position']})\n\n")
                        f.write(f"> {bookmark['text']}\n\n")
                        if bookmark.get('note'):
                            f.write(f"**备注**: {bookmark['note']}\n\n")
                        f.write("---\n\n")
                else:
                    f.write("暂无书签。\n\n")
            
            logger.info(f"书签已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出书签到Markdown失败: {e}")
            return False
    
    def export_bookmarks_to_csv(self, book: Book, output_path: str) -> bool:
        """
        将书籍的书签导出为CSV格式
        
        Args:
            book: 书籍对象
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            bookmarks = self.bookmark_manager.get_bookmarks(book.path)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'position', 'page', 'text', 'note', 'timestamp', 'create_time']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for bookmark in bookmarks:
                    writer.writerow({
                        'id': bookmark.get('id', ''),
                        'position': bookmark.get('position', ''),
                        'page': bookmark.get('page', ''),
                        'text': bookmark.get('text', '').replace('\n', '\\n'),
                        'note': bookmark.get('note', '').replace('\n', '\\n') if bookmark.get('note') else '',
                        'timestamp': bookmark.get('timestamp', ''),
                        'create_time': bookmark.get('create_time', '')
                    })
            
            logger.info(f"书签已导出到CSV: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出书签到CSV失败: {e}")
            return False
    
    def export_bookmarks_to_json(self, book: Book, output_path: str) -> bool:
        """
        将书籍的书签导出为JSON格式
        
        Args:
            book: 书籍对象
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            bookmarks = self.bookmark_manager.get_bookmarks(book.path)
            
            export_data = {
                "book_info": {
                    "title": book.title,
                    "author": book.author,
                    "path": book.path,
                    "format": book.format
                },
                "export_time": datetime.now().isoformat(),
                "bookmarks": bookmarks
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"书签已导出到JSON: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出书签到JSON失败: {e}")
            return False
    
    def export_bookmarks_to_txt(self, book: Book, output_path: str) -> bool:
        """
        将书籍的书签导出为TXT格式
        
        Args:
            book: 书籍对象
            output_path: 输出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            bookmarks = self.bookmark_manager.get_bookmarks(book.path)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"书籍: {book.title}\n")
                f.write(f"作者: {book.author}\n")
                f.write(f"路径: {book.path}\n")
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                
                if bookmarks:
                    for i, bookmark in enumerate(bookmarks, 1):
                        f.write(f"书签 {i}:\n")
                        f.write(f"  页码: {bookmark['page']}\n")
                        f.write(f"  位置: {bookmark['position']}\n")
                        f.write(f"  内容: {bookmark['text']}\n")
                        if bookmark.get('note'):
                            f.write(f"  备注: {bookmark['note']}\n")
                        f.write(f"  时间: {bookmark.get('create_time', '')}\n")
                        f.write("-" * 30 + "\n\n")
                else:
                    f.write("暂无书签。\n")
            
            logger.info(f"书签已导出到TXT: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出书签到TXT失败: {e}")
            return False
    
    def export_all_bookmarks(self, output_dir: str, format: str = "json") -> bool:
        """
        导出所有书签
        
        Args:
            output_dir: 输出目录
            format: 导出格式 (json, csv, markdown, txt)
            
        Returns:
            是否导出成功
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取所有书籍的路径（从书签数据中推断）
            all_bookmarks = self.bookmark_manager.get_all_bookmarks()
            book_paths = set(bm['book_path'] for bm in all_bookmarks)
            
            for book_path in book_paths:
                # 创建虚拟书籍对象用于导出
                book = Book(book_path)
                filename = f"bookmarks_{os.path.basename(book_path).replace('.', '_')}.{format}"
                output_path = os.path.join(output_dir, filename)
                
                if format.lower() == "json":
                    self.export_bookmarks_to_json(book, output_path)
                elif format.lower() == "csv":
                    self.export_bookmarks_to_csv(book, output_path)
                elif format.lower() == "markdown":
                    self.export_bookmarks_to_markdown(book, output_path)
                elif format.lower() == "txt":
                    self.export_bookmarks_to_txt(book, output_path)
                else:
                    logger.error(f"不支持的导出格式: {format}")
                    return False
            
            logger.info(f"所有书签已导出到: {output_dir}")
            return True
        except Exception as e:
            logger.error(f"导出所有书签失败: {e}")
            return False
    
    def export_reading_notes(self, book: Book, output_path: str, format: str = "markdown") -> bool:
        """
        导出阅读笔记（目前主要导出书签作为笔记）
        
        Args:
            book: 书籍对象
            output_path: 输出路径
            format: 导出格式
            
        Returns:
            是否导出成功
        """
        if format.lower() == "json":
            return self.export_bookmarks_to_json(book, output_path)
        elif format.lower() == "csv":
            return self.export_bookmarks_to_csv(book, output_path)
        elif format.lower() == "txt":
            return self.export_bookmarks_to_txt(book, output_path)
        else:  # 默认markdown
            return self.export_bookmarks_to_markdown(book, output_path)
    
    def get_export_formats(self) -> List[str]:
        """获取支持的导出格式"""
        return ["json", "csv", "markdown", "txt"]
    
    def validate_export_path(self, path: str) -> bool:
        """
        验证导出路径是否有效
        
        Args:
            path: 导出路径
            
        Returns:
            路径是否有效
        """
        try:
            path_obj = Path(path)
            parent_dir = path_obj.parent
            
            # 检查父目录是否存在且可写
            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
            
            if not os.access(parent_dir, os.W_OK):
                logger.error(f"导出目录不可写: {parent_dir}")
                return False
            
            # 检查文件扩展名是否支持
            suffix = path_obj.suffix.lower()[1:]  # 移除点号
            if suffix not in self.get_export_formats():
                logger.warning(f"文件扩展名 '{suffix}' 可能不受支持，但仍可导出")
            
            return True
        except Exception as e:
            logger.error(f"验证导出路径失败: {e}")
            return False