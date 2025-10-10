"""
书籍模型，定义书籍的数据结构和相关操作
"""

import os
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple

from src.utils.cache_manager import parse_cache, make_key
from src.utils import file_utils as _fu

from src.config.default_config import SUPPORTED_FORMATS
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Book:
    """书籍类，表示一本书籍及其元数据"""
    
    def __init__(self, path: str, title: Optional[str] = None, author: Optional[str] = None, password: Optional[str] = None, pinyin: Optional[str] = None):
        """
        初始化书籍对象
        
        Args:
            path: 书籍文件路径
            title: 书籍标题，如果为None则使用文件名
            author: 书籍作者，如果为None则为"未知作者"
            password: PDF密码，用于加密PDF文件
            pinyin: 书籍标题的拼音，如果为None则自动生成
        """
        self.path = os.path.abspath(path) if path else ""
        self.file_name = os.path.basename(path) if path else "default.txt"
        self.format = os.path.splitext(path)[1].lower() if path else ".txt"
        
        # 检查文件是否存在（允许空路径用于默认书籍）
        if path and not os.path.exists(path):
            logger.warning(f"书籍文件不存在: {path}")
            # 不抛出异常，允许创建书籍对象但标记为文件不存在
        
        # 检查文件格式是否支持（允许空路径用于默认书籍）
        if path and self.format not in SUPPORTED_FORMATS:
            raise ValueError(f"不支持的文件格式: {self.format}")
        
        # 基本信息
        self.title = title if title else os.path.splitext(self.file_name)[0]
        self.author = author if author else "未知作者"
        self.tags: str = ""  # 存储逗号分隔的标签字符串
        self.size = os.path.getsize(path) if path and os.path.exists(path) else 0
        self.add_date = datetime.now().isoformat()
        self.password = password  # 存储PDF密码
        
        # 拼音字段
        if pinyin is not None:
            self.pinyin = pinyin
        else:
            self.pinyin = self._generate_pinyin(self.title)
        
        # 阅读信息
        self.last_read_date: Optional[str] = None
        self.current_position = 0  # 当前阅读位置（字符偏移量）
        self.current_page = 0  # 当前页码
        self.total_pages = 0  # 总页数
        self.reading_progress = 0.0  # 阅读进度（0.0-1.0）
        self.reading_time = 0  # 总阅读时间（秒）
        # 位置锚点（用于跨分页纠偏）
        self.anchor_text: str = ""
        self.anchor_hash: str = ""
        
        # 书签
        self.bookmarks: List[Dict[str, Any]] = []
        
        # 统计信息
        self.word_count = 0  # 字数
        self.open_count = 0  # 打开次数
        
        # 章节信息
        self.chapters: List[Dict[str, Any]] = []
        if not path:  # 如果是默认书籍，添加一个默认章节
            self.chapters = [{
                "title": "默认章节",
                "start": 0,
                "end": 0
            }]
        
        # 内容缓存
        self._content: Optional[str] = None
        self._content_loaded = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将书籍对象转换为字典
        
        Returns:
            Dict[str, Any]: 书籍字典
        """
        return {
            "path": self.path,
            "file_name": self.file_name,
            "format": self.format,
            "title": self.title,
            "author": self.author,
            "pinyin": self.pinyin,
            "tags": self.tags,  # 直接返回字符串
            "size": self.size,
            "add_date": self.add_date,
            "last_read_date": self.last_read_date,
            "current_position": self.current_position,
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "reading_progress": self.reading_progress,
            "reading_time": self.reading_time,
            "anchor_text": getattr(self, "anchor_text", ""),
            "anchor_hash": getattr(self, "anchor_hash", ""),
            "bookmarks": self.bookmarks,
            "word_count": self.word_count,
            "open_count": self.open_count,
            "chapters": self.chapters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Book':
        """
        从字典创建书籍对象
        
        Args:
            data: 书籍字典
            
        Returns:
            Book: 书籍对象
        """
        book = cls(data["path"], data["title"], data["author"], pinyin=data.get("pinyin"))
        book.file_name = data["file_name"]
        book.format = data["format"]
        # 处理tags字段：如果是列表则转换为字符串，如果是字符串则直接使用
        tags_data = data.get("tags", "")
        if isinstance(tags_data, list):
            book.tags = ",".join(tags_data)
        else:
            book.tags = tags_data
        book.size = data["size"]
        book.add_date = data["add_date"]
        book.last_read_date = data.get("last_read_date")
        book.current_position = data.get("current_position", 0)
        book.current_page = data.get("current_page", 0)
        book.total_pages = data.get("total_pages", 0)
        book.reading_progress = data.get("reading_progress", 0.0)
        book.reading_time = data.get("reading_time", 0)
        # 读取锚点字段（向后兼容）
        book.anchor_text = data.get("anchor_text", "")
        book.anchor_hash = data.get("anchor_hash", "")
        book.bookmarks = data.get("bookmarks", [])
        book.word_count = data.get("word_count", 0)
        book.open_count = data.get("open_count", 0)
        book.chapters = data.get("chapters", [])
        return book
    
    def add_tag(self, tag: str) -> None:
        """
        添加标签
        
        Args:
            tag: 标签名称
        """
        if not self.tags:
            self.tags = tag
        elif tag not in self.tags.split(","):
            self.tags += f",{tag}"
    
    def remove_tag(self, tag: str) -> bool:
        """
        移除标签
        
        Args:
            tag: 标签名称
            
        Returns:
            bool: 是否成功移除
        """
        if self.tags:
            tags_list = self.tags.split(",")
            if tag in tags_list:
                tags_list.remove(tag)
                self.tags = ",".join(tags_list)
                return True
        return False
    
    def add_bookmark(self, position: int, page: int, text: str, note: Optional[str] = None) -> Dict[str, Any]:
        """
        添加书签
        
        Args:
            position: 字符位置
            page: 页码
            text: 书签处的文本
            note: 书签备注
            
        Returns:
            Dict[str, Any]: 书签字典
        """
        bookmark = {
            "id": str(int(time.time() * 1000)),  # 使用时间戳作为ID
            "position": position,
            "page": page,
            "text": text,
            "note": note,
            "create_time": datetime.now().isoformat()
        }
        self.bookmarks.append(bookmark)
        return bookmark
    
    def remove_bookmark(self, bookmark_id: str) -> bool:
        """
        移除书签
        
        Args:
            bookmark_id: 书签ID
            
        Returns:
            bool: 是否成功移除
        """
        for i, bookmark in enumerate(self.bookmarks):
            if bookmark["id"] == bookmark_id:
                self.bookmarks.pop(i)
                return True
        return False
    
    def get_bookmarks(self) -> List[Dict[str, Any]]:
        """
        获取所有书签
        
        Returns:
            List[Dict[str, Any]]: 书签列表
        """
        return sorted(self.bookmarks, key=lambda x: x["position"])
    
    def update_reading_progress(self, position: int, page: int, total_pages: int) -> None:
        """
        更新阅读进度
        
        Args:
            position: 当前字符位置
            page: 当前页码
            total_pages: 总页数
        """
        self.current_position = position
        self.current_page = page
        self.total_pages = total_pages
        
        # 计算阅读进度
        if total_pages > 0:
            self.reading_progress = page / total_pages
        else:
            self.reading_progress = 0.0
        
        # 更新最后阅读时间
        self.last_read_date = datetime.now().isoformat()
    
    def add_reading_time(self, seconds: int) -> None:
        """
        添加阅读时间
        
        Args:
            seconds: 阅读时间（秒）
        """
        self.reading_time += seconds
    
    def reset_progress(self) -> None:
        """重置阅读进度"""
        self.current_position = 0
        self.current_page = 0
        self.reading_progress = 0.0
    
    def increment_open_count(self) -> None:
        """增加打开次数"""
        self.open_count += 1
    
    def get_content(self) -> str:
        """
        获取书籍内容，根据文件格式调用相应的解析器
        
        Returns:
            str: 书籍内容（纯文本）
        """
        # 若已加载，直接返回
        if self._content_loaded and self._content is not None:
            return self._content

        # 优先命中解析缓存（避免重复解析）
        try:
            # 以文件哈希 + 格式 + 密码（若有）作为键
            file_hash = ""
            if self.path and os.path.exists(self.path):
                try:
                    file_hash = _fu.calculate_file_sha256(self.path)
                except Exception:
                    # 回退为修改时间+大小
                    stat = os.stat(self.path)
                    file_hash = f"{stat.st_mtime}-{stat.st_size}"
            cache_key = make_key("parse", self.path, self.format, bool(self.password), file_hash)
            cached = parse_cache.get(cache_key)
            if isinstance(cached, dict) and "content" in cached:
                result = cached
                self._content = str(result.get("content", "") or "")
                # 章节（若有）
                if isinstance(result.get("chapters"), list):
                    self.chapters = result["chapters"]
                self._content_loaded = True
                self.word_count = len(self._content or "")
                return self._content
        except Exception:
            pass
        
        # 如果是空路径的默认书籍，返回空内容
        if not self.path:
            self._content = ""
            self._content_loaded = True
            self.word_count = 0
            return self._content
        
        # 根据文件格式选择处理方式
        if self.format in ['.txt', '.md']:
            # 文本文件直接读取（加入缓存）
            text = self._read_text_file()
            self._content = text
            try:
                file_hash = ""
                if self.path and os.path.exists(self.path):
                    try:
                        file_hash = _fu.calculate_file_sha256(self.path)
                    except Exception:
                        stat = os.stat(self.path)
                        file_hash = f"{stat.st_mtime}-{stat.st_size}"
                cache_key = make_key("parse", self.path, self.format, bool(self.password), file_hash)
                parse_cache.set(cache_key, {"content": text, "chapters": []}, ttl_seconds=1800)
            except Exception:
                pass
        else:
            # 其他格式使用解析器
            self._content = self._parse_with_parser()
        
        self._content_loaded = True
        
        # 计算字符数
        if self._content:
            self.word_count = len(self._content)
        
        return self._content
    
    def _read_text_file(self) -> str:
        """读取文本文件，支持多种编码自动检测"""
        # 显示加载动画
        self._show_loading_animation("正在读取文件...")
        
        try:
            # 首先检查文件是否存在
            if not os.path.exists(self.path):
                logger.error(f"书籍文件不存在: {self.path}")
                self._hide_loading_animation()
                return f"书籍文件不存在: {self.path}"
            
            # 尝试多种编码读取文件
            encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'utf-16', 'ascii']
            
            for encoding in encodings:
                try:
                    with open(self.path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.debug(f"成功使用 {encoding} 编码读取文件: {self.path}")
                    
                    # 隐藏加载动画
                    self._hide_loading_animation()
                    return content
                    
                except (UnicodeDecodeError, UnicodeError):
                    logger.debug(f"使用 {encoding} 编码读取文件失败，尝试下一种编码")
                    continue
                except FileNotFoundError:
                    logger.error(f"书籍文件不存在: {self.path}")
                    self._hide_loading_animation()
                    return f"书籍文件不存在: {self.path}"
                except Exception as e:
                    logger.error(f"读取书籍内容时出错 (编码: {encoding}): {e}")
                    continue
            
            # 如果所有编码都失败，尝试二进制读取并使用chardet检测编码
            try:
                import chardet
                with open(self.path, 'rb') as f:
                    raw_data = f.read()
                
                # 检测编码
                detected = chardet.detect(raw_data)
                detected_encoding = detected.get('encoding')
                if detected_encoding:
                    content = raw_data.decode(detected_encoding, errors='ignore')
                    logger.debug(f"使用检测编码 {detected_encoding} 成功读取文件")
                    
                    # 隐藏加载动画
                    self._hide_loading_animation()
                    return content
                
            except FileNotFoundError:
                logger.error(f"书籍文件不存在: {self.path}")
                self._hide_loading_animation()
                return f"书籍文件不存在: {self.path}"
            except ImportError:
                logger.warning("chardet 库未安装，无法进行编码检测")
            except Exception as e:
                logger.error(f"使用编码检测读取文件失败: {e}")
            
            # 最后的备用方案：使用utf-8并忽略错误
            try:
                with open(self.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                logger.warning(f"使用 UTF-8 编码并忽略错误读取文件，可能存在字符丢失")
                
                # 隐藏加载动画
                self._hide_loading_animation()
                return content
                
            except FileNotFoundError:
                logger.error(f"书籍文件不存在: {self.path}")
                self._hide_loading_animation()
                return f"书籍文件不存在: {self.path}"
            except Exception as e:
                logger.error(f"所有编码尝试都失败: {e}")
                return f"无法读取文件 {self.path}，请检查文件是否损坏或编码不支持"
                
        finally:
            # 确保在任何情况下都隐藏加载动画
            self._hide_loading_animation()
    
    def _parse_with_parser(self) -> str:
        """使用相应的解析器解析文件内容"""
        try:
            # 对于PDF文件，先检查是否需要密码
            if self.format == '.pdf':
                return self._handle_pdf_file()
            
            # 其他格式使用标准解析流程
            return self._handle_other_formats()
                
        except Exception as e:
            logger.error(f"使用解析器解析文件失败: {e}")
            # 如果解析器失败，尝试作为文本文件读取
            logger.warning(f"解析器失败，尝试作为文本文件读取: {self.path}")
            return self._read_text_file()
    
    def _safe_async_call(self, async_func, *args, **kwargs):
        """安全地调用异步函数"""
        import asyncio
        import concurrent.futures
        import threading
        
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用线程池执行
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_async_in_thread, async_func, *args, **kwargs)
                return future.result(timeout=60)  # 60秒超时
        except RuntimeError:
            # 如果没有运行的事件循环，直接运行
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(async_func(*args, **kwargs))
                finally:
                    loop.close()
            except Exception as e:
                logger.error(f"异步调用失败: {e}")
                raise
    
    def _run_async_in_thread(self, async_func, *args, **kwargs):
        """在新线程中运行异步函数"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    
    def _ensure_pure_text_content(self, content) -> str:
        """
        确保内容是纯文本，过滤掉任何二进制数据或HTML标签
        
        Args:
            content: 输入内容
            
        Returns:
            str: 纯文本内容
        """
        if not content:
            return ""
        
        # 如果不是字符串，尝试转换
        if not isinstance(content, str):
            try:
                if isinstance(content, bytes):
                    # 检查是否为二进制文件
                    if content.startswith(b'PK') or content.startswith(b'\x89PNG') or content.startswith(b'\xff\xd8\xff'):
                        logger.warning("检测到二进制数据，返回空内容")
                        return ""
                    content = content.decode('utf-8', errors='ignore')
                else:
                    content = str(content)
            except Exception as e:
                logger.warning(f"内容转换失败: {e}")
                return ""
        
        # 检查内容质量
        if len(content) > 100:
            # 计算可打印字符比例
            printable_chars = sum(1 for c in content[:1000] if c.isprintable() or c.isspace())
            printable_ratio = printable_chars / min(len(content), 1000)
            
            if printable_ratio < 0.7:
                logger.warning(f"内容可打印字符比例过低 ({printable_ratio:.2f})，可能包含二进制数据")
                return ""
        
        # 移除HTML标签
        import re
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除HTML实体
        import html
        content = html.unescape(content)
        
        # 过滤掉不可打印的字符（保留常见的空白字符）
        filtered_chars = []
        for char in content:
            if char.isprintable() or char in '\n\r\t ':
                filtered_chars.append(char)
            elif ord(char) < 32 and char not in '\n\r\t':
                # 跳过控制字符
                continue
            else:
                filtered_chars.append(char)
        
        content = ''.join(filtered_chars)
        
        # 规范化空白字符
        content = re.sub(r'[ \t]+', ' ', content)  # 多个空格/制表符合并为一个空格
        content = re.sub(r'\n\s*\n', '\n\n', content)  # 规范化换行
        content = re.sub(r'\n{3,}', '\n\n', content)  # 移除多余的空行
        
        # 移除行首行尾空白
        lines = content.split('\n')
        lines = [line.strip() for line in lines]
        content = '\n'.join(lines)
        
        return content.strip()
    
    def search(self, keyword: str) -> List[Tuple[int, str]]:
        """
        搜索书籍内容
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            List[Tuple[int, str]]: 搜索结果列表，每个元素为(位置, 上下文)
        """
        content = self.get_content()
        results = []
        
        # 简单的搜索实现
        start = 0
        while True:
            pos = content.find(keyword, start)
            if pos == -1:
                break
                
            # 获取上下文（前后各50个字符）
            context_start = max(0, pos - 50)
            context_end = min(len(content), pos + len(keyword) + 50)
            context = content[context_start:context_end]
            
            results.append((pos, context))
            start = pos + len(keyword)
        
        return results
    
    def _show_loading_animation(self, message: str = "处理中...") -> None:
        """显示加载动画（动态导入以断开循环依赖）"""
        try:
            import importlib
            # Textual集成动画
            ta_mod = importlib.import_module("src.ui.components.textual_loading_animation")
            textual_animation_manager = getattr(ta_mod, "textual_animation_manager", None)
            if textual_animation_manager and getattr(textual_animation_manager, "show_default", None):
                if textual_animation_manager.show_default(message):
                    logger.debug(f"显示Textual加载动画: {message}")
                    return
            # 回退动画
            la_mod = importlib.import_module("src.ui.components.loading_animation")
            animation_manager = getattr(la_mod, "animation_manager", None)
            if animation_manager and getattr(animation_manager, "show_default", None):
                animation_manager.show_default(message)
                logger.debug(f"显示传统加载动画: {message}")
        except Exception as e:
            logger.warning(f"显示加载动画失败或组件未找到: {e}")
    
    def _hide_loading_animation(self) -> None:
        """隐藏加载动画（动态导入以断开循环依赖）"""
        try:
            import importlib
            ta_mod = importlib.import_module("src.ui.components.textual_loading_animation")
            textual_animation_manager = getattr(ta_mod, "textual_animation_manager", None)
            if textual_animation_manager and getattr(textual_animation_manager, "hide_default", None):
                if textual_animation_manager.hide_default():
                    logger.debug("隐藏Textual加载动画")
                    return
            la_mod = importlib.import_module("src.ui.components.loading_animation")
            animation_manager = getattr(la_mod, "animation_manager", None)
            if animation_manager and getattr(animation_manager, "hide_default", None):
                animation_manager.hide_default()
                logger.debug("隐藏传统加载动画")
        except Exception as e:
            logger.warning(f"隐藏加载动画失败或组件未找到: {e}")

    def _generate_pinyin(self, text: str) -> str:
        """
        生成中文文本的拼音
        
        Args:
            text: 中文文本
            
        Returns:
            str: 拼音字符串
        """
        try:
            from pypinyin import pinyin, Style
            
            # 将中文转换为拼音，使用不带声调的格式
            pinyin_list = pinyin(text, style=Style.NORMAL)
            # 将拼音列表连接成字符串
            pinyin_str = ''.join([item[0] for item in pinyin_list if item[0]])
            
            # 如果转换失败或为空，返回原始文本的ASCII表示
            if not pinyin_str:
                pinyin_str = text.encode('ascii', 'ignore').decode('ascii')
            
            return pinyin_str
            
        except ImportError:
            logger.warning("pypinyin库未安装，使用简单拼音转换")
            # 简单的拼音转换实现（仅处理基本汉字）
            pinyin_map = {
                '阿': 'a', '啊': 'a', '爱': 'ai', '安': 'an', '昂': 'ang',
                '八': 'ba', '把': 'ba', '白': 'bai', '班': 'ban', '帮': 'bang',
                # 这里可以添加更多基本汉字映射
            }
            
            result = []
            for char in text:
                if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                    result.append(pinyin_map.get(char, char))
                else:
                    result.append(char)
            
            return ''.join(result)
            
        except Exception as e:
            logger.error(f"拼音转换失败: {e}")
            # 如果转换失败，返回原始文本的ASCII表示
            return text.encode('ascii', 'ignore').decode('ascii')

    def _handle_pdf_file(self) -> str:
        """处理PDF文件，区分加密和非加密"""
        # 先检查PDF是否需要密码
        is_encrypted = self._check_pdf_encryption()
        
        if not is_encrypted:
            # 非加密PDF直接使用标准解析器
            return self._parse_pdf_without_password()
        else:
            # 加密PDF需要获取密码
            return self._parse_encrypted_pdf()

    def _check_pdf_encryption(self) -> bool:
        """检查PDF文件是否加密"""
        try:
            from PyPDF2 import PdfReader
            with open(self.path, 'rb') as f:
                reader = PdfReader(f)
                return bool(getattr(reader, "is_encrypted", False))
        except Exception as e:
            logger.debug(f"PDF加密检查失败: {e}")
            return False

    def _parse_pdf_without_password(self) -> str:
        """解析非加密PDF文件"""
        from src.parsers.pdf_parser import PdfParser
        parser = PdfParser()
        
        # 显示加载动画
        self._show_loading_animation("正在解析PDF文件...")
        
        try:
            result = self._safe_async_call(parser.parse, self.path)
            self._hide_loading_animation()

            content = result.get('content', '')
            content = self._ensure_pure_text_content(content)

            # 更新章节信息
            validated_chapters = []
            if 'chapters' in result:
                for chapter in result['chapters']:
                    if isinstance(chapter, dict) and 'content' in chapter:
                        chapter['content'] = self._ensure_pure_text_content(chapter.get('content', ''))
                        validated_chapters.append(chapter)
            self.chapters = validated_chapters

            # 写入解析缓存
            try:
                stat = os.stat(self.path)
                file_hash = ""
                try:
                    file_hash = _fu.calculate_file_sha256(self.path)
                except Exception:
                    file_hash = f"{stat.st_mtime}-{stat.st_size}"
                cache_key = make_key("parse", self.path, self.format, bool(self.password), file_hash)
                parse_cache.set(cache_key, {"content": content, "chapters": validated_chapters}, ttl_seconds=1800)
            except Exception:
                pass

            logger.debug(f"成功解析非加密PDF文件: {self.path}")
            return content
            
        except Exception as e:
            self._hide_loading_animation()
            raise e

    def _parse_encrypted_pdf(self) -> str:
        """解析加密PDF文件"""
        # 如果已经有密码，直接使用
        if hasattr(self, 'password') and self.password is not None:
            password = self.password
            logger.info(f"使用存储的密码解析加密PDF: {self.path}")
        else:
            # 暂停加载动画，显示密码输入框
            self._hide_loading_animation()
            
            # 获取密码
            password = self._get_password_for_pdf()
            
            # 重新开始加载动画
            self._show_loading_animation("正在解析加密PDF文件...")
        
        try:
            # 使用加密PDF解析器
            from src.parsers.pdf_encrypt_parser import PdfEncryptParser
            parser = PdfEncryptParser()
            
            result = self._safe_async_call(parser.parse, self.path, password)
            self._hide_loading_animation()

            content = result.get('content', '')
            content = self._ensure_pure_text_content(content)

            # 更新章节信息
            validated_chapters = []
            if 'chapters' in result:
                for chapter in result['chapters']:
                    if isinstance(chapter, dict) and 'content' in chapter:
                        chapter['content'] = self._ensure_pure_text_content(chapter.get('content', ''))
                        validated_chapters.append(chapter)
            self.chapters = validated_chapters

            # 写入解析缓存（含密码特征）
            try:
                stat = os.stat(self.path)
                file_hash = ""
                try:
                    file_hash = _fu.calculate_file_sha256(self.path)
                except Exception:
                    file_hash = f"{stat.st_mtime}-{stat.st_size}"
                cache_key = make_key("parse", self.path, self.format, True, file_hash)
                parse_cache.set(cache_key, {"content": content, "chapters": validated_chapters}, ttl_seconds=1800)
            except Exception:
                pass
            
            logger.debug(f"成功解析加密PDF文件: {self.path}")
            
            # 发送内容刷新消息（动态导入）
            try:
                import importlib
                app_mod = importlib.import_module("src.ui.app")
                get_app_instance = getattr(app_mod, "get_app_instance", None)
                msg_mod = importlib.import_module("src.ui.messages")
                RefreshContentMessage = getattr(msg_mod, "RefreshContentMessage", None)
                from typing import Any as _Any
                app = get_app_instance() if get_app_instance else None  # type: _Any
                if app and RefreshContentMessage:
                    app.post_message(RefreshContentMessage())
            except Exception as e:
                logger.debug(f"发送内容刷新消息失败: {e}")
            
            return content
            
        except Exception as e:
            self._hide_loading_animation()
            raise e

    def _get_password_for_pdf(self) -> Optional[str]:
        """获取PDF密码，支持GUI和CLI两种模式"""
        try:
            # 尝试通过GUI获取密码（动态导入避免循环依赖）
            import importlib
            app_mod = None
            get_app_instance = None
            try:
                app_mod = importlib.import_module("src.ui.app")
                get_app_instance = getattr(app_mod, "get_app_instance", None)
            except Exception:
                get_app_instance = None
            app = get_app_instance() if get_app_instance else None
            if not app:
                # Textual 应用（动态属性访问）
                try:
                    textual_app_mod = importlib.import_module("textual.app")
                    TextualApp = getattr(textual_app_mod, "App", None)
                    get_app = getattr(TextualApp, "get_app", None) if TextualApp else None
                    app = get_app() if callable(get_app) else None
                except Exception:
                    app = None
                
                if app and hasattr(app, "request_password_async"):
                    from concurrent.futures import Future
                    future = Future()
                    
                    # 在UI线程中获取密码
                    if hasattr(app, "schedule_on_ui"):
                        getattr(app, "schedule_on_ui")(lambda: getattr(app, "request_password_async")(self.path, 3, future))
                    elif hasattr(app, "call_from_thread"):
                        getattr(app, "call_from_thread")(lambda: getattr(app, "request_password_async")(self.path, 3, future))
                    else:
                        getattr(app, "request_password_async")(self.path, 3, future)
                    
                    return future.result(timeout=300)
                
                # 如果GUI模式失败，使用CLI模式
                return self._get_password_cli()
        
        except Exception as e:
            logger.warning(f"GUI密码获取失败，使用CLI模式: {e}")
            return self._get_password_cli()

    def _get_password_cli(self) -> Optional[str]:
        """CLI模式下获取密码"""
        try:
            import getpass
            print(f"\nPDF文件需要密码: {self.path}")
            password = getpass.getpass("请输入PDF密码（留空跳过）: ")
            return password if password else None
        except Exception as e:
            logger.warning(f"CLI密码获取失败: {e}")
            return None

    def _handle_other_formats(self) -> str:
        """处理其他格式的文件"""
        # 动态导入解析器
        if self.format == '.epub':
            from src.parsers.epub_parser import EpubParser
            parser = EpubParser()
        elif self.format == '.mobi':
            from src.parsers.mobi_parser import MobiParser
            parser = MobiParser()
        elif self.format in ['.azw', '.azw3']:
            from src.parsers.azw_parser import AzwParser
            parser = AzwParser()
        else:
            # 不支持的格式，尝试作为文本文件读取
            logger.warning(f"不支持的格式 {self.format}，尝试作为文本文件读取")
            return self._read_text_file()
        
        # 显示加载动画
        self._show_loading_animation("正在解析文件...")
        
        try:
            result = self._safe_async_call(parser.parse, self.path)
            self._hide_loading_animation()

            content = result.get('content', '')
            content = self._ensure_pure_text_content(content)

            # 更新章节信息
            validated_chapters = []
            if 'chapters' in result:
                for chapter in result['chapters']:
                    if isinstance(chapter, dict) and 'content' in chapter:
                        chapter['content'] = self._ensure_pure_text_content(chapter.get('content', ''))
                        validated_chapters.append(chapter)
            self.chapters = validated_chapters

            # 写入解析缓存
            try:
                stat = os.stat(self.path)
                file_hash = ""
                try:
                    file_hash = _fu.calculate_file_sha256(self.path)
                except Exception:
                    file_hash = f"{stat.st_mtime}-{stat.st_size}"
                cache_key = make_key("parse", self.path, self.format, bool(self.password), file_hash)
                parse_cache.set(cache_key, {"content": content, "chapters": validated_chapters}, ttl_seconds=1800)
            except Exception:
                pass

            logger.debug(f"成功使用解析器解析文件: {self.path}")
            return content
            
        except Exception as e:
            self._hide_loading_animation()
            raise e