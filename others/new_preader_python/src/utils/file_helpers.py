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


def _strict_decode_tolerant(raw: bytes, encoding: str) -> Optional[str]:
    """
    以严格方式解码字节，但对「末尾多字节序列被截断」这种错误做容错

    读取预览时只读取了文件前缀字节，可能恰好把 UTF-8/GBK 等多字节字符从
    中间截断，导致严格解码抛 ``UnicodeDecodeError``（如 "unexpected end of
    data"）。这种情况不应视为编码不匹配，而是忽略末尾不完整的字节后再试。

    Args:
        raw: 文件前缀字节
        encoding: 尝试的编码

    Returns:
        解码后的文本；若确实不是该编码则返回 ``None``
    """
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError as e:
        msg = str(e)
        # 仅当错误发生在末尾、且属于“多字节序列被截断”时才容错重试
        truncated = ("unexpected end of data" in msg) or ("incomplete" in msg)
        at_tail = (getattr(e, "end", 0) or 0) >= len(raw) - 4
        if truncated and at_tail:
            try:
                return raw.decode(encoding, errors="ignore")
            except UnicodeDecodeError:
                return None
        return None


def read_file_preview(file_path: str, max_chars: int = 2000) -> str:
    """
    读取文件前 max_chars 个字符用于预览，自动检测编码

    依次尝试常见中文编码（utf-8 / gbk / gb2312 / big5 / utf-16 等），并对
    “读到的字节恰好截断多字节字符”的情况做容错，避免把合法的 UTF-8 文件
    误判成宽松编码（如 utf-16）而显示乱码。charset-normalizer 作为罕见编码
    的补充检测。

    Args:
        file_path: 文件路径
        max_chars: 最大字符数（默认 2000）

    Returns:
        解码后的文本（截断到 max_chars 个字符）；失败返回空字符串
    """
    try:
        # 读取足够的前缀字节：多字节编码下 max_chars 字符最多约 4 倍字节数，
        # 额外多读一些字节以覆盖边界情况（避免多字节字符被截断）
        with open(file_path, 'rb') as f:
            raw = f.read(max_chars * 4 + 64)

        text: Optional[str] = None

        # 1) 依次尝试常见编码；utf-8 优先，且对末尾截断做容错
        encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'utf-16']
        for encoding in encodings:
            decoded = _strict_decode_tolerant(raw, encoding)
            if decoded is not None:
                text = decoded
                break

        # 2) 补充：charset-normalizer 检测更罕见编码（若已安装且上面未命中）
        if not text:
            try:
                from charset_normalizer import from_bytes
                result = from_bytes(raw).best()
                if result is not None and result.encoding:
                    text = str(result)
            except Exception:
                pass

        # 3) 最终回退：忽略无法解码的字节，避免预览直接失败
        if not text:
            text = raw.decode('utf-8', errors='ignore')

        # 去掉可能导致渲染异常的 NUL 字符
        text = text.replace('\x00', '')
        return text[:max_chars]
    except Exception as e:
        logger.error(f"读取文件预览失败: {file_path}, 错误: {e}")
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