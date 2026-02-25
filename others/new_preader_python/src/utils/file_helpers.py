"""
文件操作辅助函数 - 支持增量爬取
"""

import hashlib
import os
from typing import List, Dict, Any, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

def calculate_file_hash(file_path: str) -> str:
    """
    计算文件MD5哈希值
    
    Args:
        file_path: 文件路径
    
    Returns:
        MD5哈希值（十六进制字符串）
    """
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败: {file_path}, 错误: {e}")
        return ""

def calculate_content_hash(content: str) -> str:
    """
    计算内容MD5哈希值
    
    Args:
        content: 文本内容
    
    Returns:
        MD5哈希值（十六进制字符串）
    """
    try:
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    except Exception as e:
        logger.error(f"计算内容哈希失败: {e}")
        return ""

def read_text_file(file_path: str) -> str:
    """
    读取文本文件，自动检测编码
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件内容
    """
    try:
        # 尝试多种编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # 所有编码都失败，使用utf-8并忽略错误
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取文件失败: {file_path}, 错误: {e}")
        return ""

def write_text_file(file_path: str, content: str) -> bool:
    """
    写入文本文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
    
    Returns:
        是否成功
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文件失败: {file_path}, 错误: {e}")
        return False

def append_chapters_to_file(old_content: str, new_chapters: List[Dict[str, Any]]) -> str:
    """
    将新章节追加到已有内容
    
    Args:
        old_content: 已有内容
        new_chapters: 新章节列表，每个章节包含 title 和 content
    
    Returns:
        合并后的内容
    """
    try:
        lines = old_content.split('\n')
        
        # 简单策略：直接追加新章节
        for chapter in new_chapters:
            chapter_title = chapter.get('title', '')
            chapter_content = chapter.get('content', '')
            
            if chapter_title:
                lines.append(f"\n\n{'#'*30}")
                lines.append(f"# {chapter_title}")
                lines.append(f"{'#'*30}")
            
            if chapter_content:
                lines.append(chapter_content)
        
        return '\n'.join(lines)
    except Exception as e:
        logger.error(f"追加章节失败: {e}")
        return old_content

def detect_chapter_duplicates(
    new_chapters: List[Dict[str, Any]], 
    saved_chapters: Dict[int, Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], int]:
    """
    检测重复章节
    
    Args:
        new_chapters: 新章节列表
        saved_chapters: 已保存的章节字典 {index: {title, hash, crawl_time}}
    
    Returns:
        (去重后的新章节列表, 重复数量)
    """
    try:
        unique_chapters = []
        duplicate_count = 0
        
        for chapter in new_chapters:
            chapter_title = chapter.get('title', '')
            chapter_content = chapter.get('content', '')
            chapter_hash = calculate_content_hash(chapter_content)
            
            is_duplicate = False
            for saved_idx, saved_chapter in saved_chapters.items():
                # 检查标题或内容哈希是否匹配
                if (saved_chapter['title'] == chapter_title or 
                    saved_chapter['hash'] == chapter_hash):
                    is_duplicate = True
                    duplicate_count += 1
                    logger.debug(f"章节已存在，跳过: {chapter_title}")
                    break
            
            if not is_duplicate:
                chapter['hash'] = chapter_hash
                unique_chapters.append(chapter)
        
        return unique_chapters, duplicate_count
    except Exception as e:
        logger.error(f"检测章节重复失败: {e}")
        return new_chapters, 0

def format_chapter_info(record: Dict[str, Any]) -> str:
    """
    格式化章节信息用于显示
    
    Args:
        record: 爬取记录字典
    
    Returns:
        格式化的章节信息字符串
    """
    book_type = record.get('book_type', '短篇')
    
    if book_type == '短篇':
        return "短篇"
    elif record.get('chapter_count', 0) > 0:
        current = record.get('last_chapter_index', -1) + 1
        total = record['chapter_count']
        return f"{current}/{total}章"
    else:
        return "-"