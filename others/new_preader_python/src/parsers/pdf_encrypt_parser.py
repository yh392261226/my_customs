"""
加密PDF文件解析器 - 专门处理需要密码的PDF文件
"""

import os
import re
from typing import Dict, Any, List, Optional
import PyPDF2

from src.parsers.base_parser import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PdfEncryptParser(BaseParser):
    """加密PDF文件解析器"""
    
    def __init__(self, app=None):
        """初始化加密PDF解析器"""
        super().__init__()
        self.app = app
        self.max_password_attempts = 3
    
    @staticmethod
    def is_encrypted_pdf(file_path: str) -> bool:
        """
        检查PDF文件是否加密
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            bool: 如果文件加密返回True，否则返回False
        """
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return bool(getattr(reader, "is_encrypted", False))
        except Exception as e:
            logger.debug(f"PDF加密检查失败: {e}")
            return False

    async def parse(self, file_path: str, provided_password: Optional[str] = None) -> Dict[str, Any]:
        """
        解析加密PDF文件
        
        Args:
            file_path: 文件路径
            provided_password: 外部提供的密码（可选）
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        logger.info(f"解析加密PDF文件: {file_path}")
        # 抑制 pypdf 提示信息与特定 warnings
        try:
            import logging as _logging, warnings as _warnings
            _logging.getLogger("pypdf").setLevel(_logging.ERROR)
            # 使用字符串正则，避免类型检查错误
            _warnings.filterwarnings("ignore", message=".*should not allow text extraction.*", module="pypdf|PyPDF2")
        except Exception:
            pass
        
        # 验证文件确实需要密码
        if not self._is_pdf_encrypted(file_path):
            logger.warning(f"文件 {file_path} 不需要密码，但被传递到加密解析器")
            # 回退到普通PDF解析器
            from src.parsers.pdf_parser import PdfParser
            pdf_parser = PdfParser(app=self.app)
            return await pdf_parser.parse(file_path)
        
        # 获取密码（优先使用外部提供的密码）
        password = provided_password
        if password is None:
            password = await self._get_password_from_user(file_path)
            if password is None:
                raise ValueError("用户取消输入密码")
        
        # 使用密码解析PDF
        return await self._parse_with_password(file_path, password)
    
    def _is_pdf_encrypted(self, file_path: str) -> bool:
        """
        检查PDF文件是否加密
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否加密
        """
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file, strict=False)
                return reader.is_encrypted
        except Exception as e:
            logger.error(f"检查PDF加密状态时出错: {e}")
            return False
    
    async def _get_password_from_user(self, file_path: str) -> Optional[str]:
        """
        显示密码输入对话框并获取用户输入的密码
        
        Args:
            file_path: 需要密码的PDF文件路径
            
        Returns:
            Optional[str]: 用户输入的密码，如果取消则为None
        """
        # 检查当前线程是否是主线程
        import threading
        is_main_thread = threading.current_thread() is threading.main_thread()
        
        # 尝试使用GUI对话框（只有在主线程中才能显示GUI）
        try:
            from src.ui.app import get_app_instance
            app = get_app_instance()
            if not app:
                try:
                    from textual.app import App as _TextualApp  # type: ignore
                    app = _TextualApp.get_app()
                except Exception:
                    app = None

            logger.debug(f"Password dialog app check: has_app={bool(app)}, is_main_thread={is_main_thread}")

            if app:
                from src.ui.dialogs.password_dialog import PasswordDialog
                try:
                    # 主线程且支持 push_screen_wait 时优先使用
                    
                    # 移除主线程同步等待，统一走消息/回调桥接，避免阻塞UI
                    
                    # 使用 App 消息桥接到主线程
                    logger.info("PasswordDialog: requesting via App message bridge")
                    import asyncio as _asyncio
                    loop = _asyncio.get_running_loop()
                    future: _asyncio.Future[Optional[str]] = loop.create_future()
                    
                    try:
                        # 优先使用 App 的主线程桥接方法
                        if hasattr(app, "request_password_async") and hasattr(app, "schedule_on_ui"):
                            logger.info("PasswordDialog.bridge via app.request_password_async using schedule_on_ui")
                            app.schedule_on_ui(lambda: app.request_password_async(file_path, self.max_password_attempts, future))
                            return await future
                        elif hasattr(app, "request_password_async") and hasattr(app, "call_from_thread"):
                            logger.info("PasswordDialog.bridge via app.request_password_async using call_from_thread")
                            app.call_from_thread(lambda: app.request_password_async(file_path, self.max_password_attempts, future))
                            return await future
                        
                        # 次优先：消息桥接
                        try:
                            from src.ui.messages import RequestPasswordMessage
                            msg = RequestPasswordMessage(file_path, self.max_password_attempts, future)
                            if hasattr(app, "post_message_from_thread"):
                                app.post_message_from_thread(msg)
                                logger.info("PasswordDialog.request posted via post_message_from_thread")
                            elif hasattr(app, "call_from_thread") and hasattr(app, "post_message"):
                                app.call_from_thread(lambda: app.post_message(msg))
                            else:
                                logger.warning("No message bridge API available; fallback to direct push")
                                def _on_result(result: Optional[str]) -> None:
                                    if not future.done():
                                        future.set_result(result)
                                PasswordDialog.show(app, file_path, callback=_on_result)
                            return await future
                        except Exception as e:
                            logger.error(f"Message bridge failed: {e}")
                            # 回退到CLI
                            import asyncio as _asyncio
                            return await _asyncio.to_thread(self._get_password_from_cli, file_path)
                    except Exception as e:
                        logger.error(f"发送密码请求消息失败: {e}")
                        return await _asyncio.to_thread(self._get_password_from_cli, file_path)
                except Exception as e:
                    logger.error(f"显示GUI密码对话框时出错: {e}")
                    import asyncio as _asyncio
                    return await _asyncio.to_thread(self._get_password_from_cli, file_path)
            else:
                # 没有 GUI 应用实例，回退到命令行输入
                import asyncio as _asyncio
                return await _asyncio.to_thread(self._get_password_from_cli, file_path)
        except (ImportError, RuntimeError):
            # 回退到命令行输入
            import asyncio as _asyncio
            return await _asyncio.to_thread(self._get_password_from_cli, file_path)
    
    def _get_password_from_cli(self, file_path: str) -> Optional[str]:
        """
        从命令行获取密码输入
        
        Args:
            file_path: 需要密码的PDF文件路径
            
        Returns:
            Optional[str]: 用户输入的密码，如果取消则为None
        """
        try:
            # 直接使用input而不是getpass，确保在CLI模式下能显示提示
            print(f"\nPDF文件需要密码: {os.path.basename(file_path)}")
            password = input("请输入PDF密码（留空跳过）: ")
            return password if password else None
        except KeyboardInterrupt:
            print("\n用户取消输入密码")
            return None
        except Exception as e:
            logger.error(f"CLI密码输入失败: {e}")
            return None

    async def _parse_with_password(self, file_path: str, password: str) -> Dict[str, Any]:
        """
        使用密码解析PDF文件
        
        Args:
            file_path: 文件路径
            password: 密码
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # 验证密码
                if not reader.is_encrypted:
                    logger.warning("文件不需要密码，但被传递到加密解析器")
                    # 回退到普通PDF解析
                    from src.parsers.pdf_parser import PdfParser
                    pdf_parser = PdfParser(app=self.app)
                    return await pdf_parser.parse(file_path)
                
                # 尝试解密
                decrypt_result = reader.decrypt(password)
                if decrypt_result == 0:
                    raise ValueError("密码不正确")
                
                logger.info(f"使用密码解密成功，解密结果: {decrypt_result}")
                
                # 提取元数据
                metadata = self._extract_pdf_metadata(reader)
                
                # 如果没有从内容中提取到标题，使用文件名作为标题
                if "title" not in metadata or not metadata["title"]:
                    metadata["title"] = os.path.splitext(os.path.basename(file_path))[0]
                
                # 优先使用pdfminer提取内容（质量更好）
                content = self._extract_pdf_content_pdfminer(file_path, password)
                if not content or not content.strip():
                    # 如果pdfminer失败，回退到pypdf
                    logger.info("pdfminer提取失败，回退到PyPDF2")
                    # 使用解密后的reader提取内容 - 解密后reader已经可以访问内容
                    content = self._extract_pdf_content(reader)
                
                # 清理提取的文本内容
                content = self._clean_text_content(content)
                content = self._clean_pdf_specific_content(content)
                
                # 检查内容质量，如果内容质量太差，尝试重新提取
                if self._needs_pdfminer_fallback(content):
                    logger.info("内容质量较差，尝试重新提取")
                    content = self._extract_pdf_content(reader)
                    content = self._clean_text_content(content)
                    content = self._clean_pdf_specific_content(content)
                    
                # 最终内容质量检查
                if not content or not content.strip():
                    logger.warning("无法提取有效文本内容")
                    content = "无法提取有效文本内容，请尝试其他PDF文件"
                
                # 提取章节
                chapters = self._extract_pdf_chapters(content)
                
                return {
                    "content": content,
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", "未知作者"),
                    "chapters": chapters,
                    "metadata": metadata
                }
        except Exception as e:
            logger.error(f"解析加密PDF文件时出错: {e}")
            raise
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".pdf"]
    
    def _extract_pdf_metadata(self, reader: PyPDF2.PdfReader) -> Dict[str, Any]:
        """从PDF文件中提取元数据"""
        metadata = {}
        
        info = reader.metadata
        if info:
            if info.get('/Title'):
                metadata["title"] = info.get('/Title')
            if info.get('/Author'):
                metadata["author"] = info.get('/Author')
            if info.get('/Subject'):
                metadata["subject"] = info.get('/Subject')
            if info.get('/Keywords'):
                metadata["keywords"] = info.get('/Keywords')
            if info.get('/Creator'):
                metadata["creator"] = info.get('/Creator')
            if info.get('/Producer'):
                metadata["producer"] = info.get('/Producer')
        
        return metadata
    
    def _extract_pdf_content(self, reader: PyPDF2.PdfReader) -> str:
        """从PDF文件中提取文本内容"""
        content = ""
        
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            try:
                text = page.extract_text()
                if text:
                    content += text + "\n\n"
            except Exception as e:
                logger.warning(f"提取PDF第{page_num+1}页文本时出错: {e}")
                continue
        
        content = self._clean_text_content(content)
        content = self._clean_pdf_specific_content(content)
        
        return content
    
    def _needs_pdfminer_fallback(self, content: str) -> bool:
        """判断内容是否需要回退解析"""
        if not content or len(content.strip()) < 50:
            return True
        text = content.strip()
        import re as _re
        valid_chars = _re.findall(r"[A-Za-z0-9\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text)
        ratio = (len(valid_chars) / max(len(text), 1))
        return ratio < 0.25

    def _extract_pdf_content_pdfminer(self, file_path: str, password: str) -> str:
        """使用 pdfminer.six 提取文本"""
        try:
            from pdfminer.high_level import extract_text  # type: ignore
        except Exception:
            logger.warning("未安装 pdfminer.six，使用PyPDF2")
            return ""
        try:
            text = extract_text(file_path, password=password)
            return text or ""
        except Exception as e:
            logger.warning(f"pdfminer 提取文本失败: {e}")
            return ""

    def _extract_pdf_chapters(self, content: str) -> List[Dict[str, Any]]:
        """从PDF内容中提取章节"""
        chapters = []
        
        chapter_patterns = [
            r"第\s*(\d+)\s*章\s*([^\n]+)",
            r"Chapter\s*(\d+)\s*[:\.\s]*([^\n]+)",
            r"CHAPTER\s*(\d+)\s*[:\.\s]*([^\n]+)"
        ]
        
        chapter_positions = []
        
        for pattern in chapter_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                chapter_num = match.group(1)
                chapter_title = match.group(2).strip()
                position = match.start()
                chapter_positions.append((position, f"第{chapter_num}章 {chapter_title}"))
        
        chapter_positions.sort()
        
        if chapter_positions:
            for i in range(len(chapter_positions)):
                start_pos = chapter_positions[i][0]
                title = chapter_positions[i][1]
                
                if i < len(chapter_positions) - 1:
                    end_pos = chapter_positions[i+1][0]
                else:
                    end_pos = len(content)
                
                chapter_content = content[start_pos:end_pos].strip()
                
                chapters.append({
                    "title": title,
                    "content": chapter_content
                })
        else:
            parts = content.split("\n\n\n")
            if len(parts) > 1:
                for i, part in enumerate(parts):
                    if part.strip():
                        chapters.append({
                            "title": f"部分 {i+1}",
                            "content": part.strip()
                        })
            else:
                chapters = [{"title": "全文", "content": content}]
        
        return chapters
    
    def _clean_text_content(self, content: str) -> str:
        """彻底清理文本内容，确保返回纯文本"""
        if not content:
            return ""
        
        content = re.sub(r'<[^>]+>', '', content)
        
        import html
        content = html.unescape(content)
        
        content = re.sub(r'[\x00-\x1f\x7f-\xa0\u2000-\u200f\u2028-\u202f\u2060-\u206f\ufeff]', '', content)
        content = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', content)
        content = content.replace('\ufeff', '')
        content = re.sub(r'[\xad\u00ad\u2011]', '', content)
        
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        lines = content.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        content = '\n'.join(lines)
        
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        if not content.strip():
            return "无法提取有效文本内容"
        
        return content.strip()
    
    def _clean_pdf_specific_content(self, content: str) -> str:
        """专门清理PDF提取的内容"""
        if not content:
            return ""
        
        content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
        content = re.sub(r'[\u2000-\u200f\u2028-\u202f\u2060-\u206f\ufeff]', '', content)
        content = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', content)
        content = re.sub(r'[\xad\u00ad]', '', content)
        
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        lines = content.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        content = '\n'.join(lines)
        
        return content.strip()