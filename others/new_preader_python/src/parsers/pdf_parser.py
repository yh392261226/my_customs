"""
PDF文件解析器
"""

import os

import re
from typing import Dict, Any, List, Optional
import PyPDF2

from src.parsers.base_parser import BaseParser

from src.utils.logger import get_logger

logger = get_logger(__name__)

class PdfParser(BaseParser):
    """PDF文件解析器"""
    
    def __init__(self, app=None):
        """初始化PDF解析器"""
        super().__init__()
        self.app = app
        self.max_password_attempts = 3

    async def parse(self, file_path: str, parsing_context: Optional[ParsingContext] = None) -> Dict[str, Any]:
        """
        解析PDF文件

        Args:
            file_path: 文件路径
            parsing_context: 解析上下文，包含进度回调等信息

        Returns:
            Dict[str, Any]: 解析结果
        """
        # 为了保持向后兼容，如果parsing_context为None，创建一个默认的
        if parsing_context is None:
            from .progress_callback import ParsingContext
            parsing_context = ParsingContext()

        # 从parsing_context中获取可能提供的密码
        provided_password = getattr(parsing_context, 'provided_password', None)
        logger.info(f"解析PDF文件: {file_path}")
        # 抑制 pypdf 提示信息与特定 warnings
        try:
            import logging as _logging, warnings as _warnings
            _logging.getLogger("pypdf").setLevel(_logging.ERROR)
            # 使用字符串正则，避免类型检查错误
            _warnings.filterwarnings("ignore", message=".*should not allow text extraction.*", module="pypdf|PyPDF2")
        except Exception:
            pass
        
        # UI 动画控制仅用于“加密PDF”流程
        ui_app = None
        anim_hidden_for_password = False
        anim_shown_after_password = False

        # 获取 App 实例以便调度到 UI 线程控制动画
        try:
            from src.ui.app import get_app_instance
            ui_app = get_app_instance()
            if not ui_app:
                try:
                    from textual.app import App as _TextualApp  # type: ignore
                    ui_app = _TextualApp.get_app()
                except Exception:
                    ui_app = None
        except Exception:
            ui_app = None

        def _ui_hide_loading():
            try:
                if ui_app and hasattr(ui_app, "schedule_on_ui"):
                    ui_app.schedule_on_ui(lambda: getattr(getattr(ui_app, "animation_manager", None), "hide_default", lambda: None)())
                elif ui_app and hasattr(ui_app, "animation_manager"):
                    # 退化处理：直接调用（通常也在主线程）
                    ui_app.animation_manager.hide_default()
            except Exception:
                pass

        def _ui_show_loading():
            try:
                if ui_app and hasattr(ui_app, "schedule_on_ui"):
                    # 若 AnimationManager 有 show_default 则调用，否则忽略
                    ui_app.schedule_on_ui(lambda: getattr(getattr(ui_app, "animation_manager", None), "show_default", lambda *a, **k: None)())
                elif ui_app and hasattr(ui_app, "animation_manager") and hasattr(ui_app.animation_manager, "show_default"):
                    ui_app.animation_manager.show_default()
            except Exception:
                pass

        try:
            password_used: Optional[str] = None
            # 打开PDF文件
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file, strict=False)
                
                # 检查文件是否加密
                if reader.is_encrypted:
                    logger.info("检测到加密PDF文件")
                    try:
                        # 若外部已提供密码，优先使用；否则先尝试空密码，再走交互获取
                        if provided_password is not None:
                            # 先试空密码，有些“加密标记”其实无需密码
                            decrypt_empty = reader.decrypt("")
                            decrypt_provided = reader.decrypt(provided_password)
                            if decrypt_empty != 0 or decrypt_provided != 0:
                                password_used = "" if decrypt_empty != 0 else provided_password
                                logger.info(f"使用提供的密码/空密码解密成功，空密码结果: {decrypt_empty}, 提供密码结果: {decrypt_provided}")
                            else:
                                raise ValueError("提供的密码不正确")
                        else:
                            # 未提供密码：先试空密码
                            decrypt_empty = reader.decrypt("")
                            if decrypt_empty != 0:
                                password_used = ""
                                logger.info(f"使用空密码解密成功，解密结果: {decrypt_empty}")
                            else:
                                # 回退到内部获取（可能为 CLI），注意这里不再做任何 UI 弹窗尝试
                                password = await self._get_password_from_user(file_path)
                                if password is None:
                                    raise ValueError("用户取消输入密码")
                                # 尝试解密，注意：PyPDF2的decrypt方法返回0表示失败，非0表示成功
                                decrypt_result = reader.decrypt(password)
                                if decrypt_result == 0:
                                    raise ValueError("密码不正确")
                                password_used = password
                                logger.info(f"使用用户输入密码解密成功，解密结果: {decrypt_result}")
                    except Exception as e:
                        logger.error(f"解密PDF文件时出错: {e}")
                        raise ValueError(f"解密失败: {str(e)}")
                
                # 提取元数据
                metadata = self._extract_pdf_metadata(reader)
                
                # 如果没有从内容中提取到标题，使用文件名作为标题
                if "title" not in metadata or not metadata["title"]:
                    metadata["title"] = os.path.splitext(os.path.basename(file_path))[0]
                
                # 优先使用 PyMuPDF（fitz）提取内容，对 CJK 支持更好
                content = self._extract_pdf_content_pymupdf(file_path, password_used)
                if not content or not content.strip():
                    # 次优：使用 pdfminer.six
                    content = self._extract_pdf_content_pdfminer(file_path, password_used)
                    if not content or not content.strip():
                        # 回退到 PyPDF2
                        logger.info("PyMuPDF/pdfminer 提取失败，回退到 PyPDF2")
                        content = self._extract_pdf_content(reader)
                
                # 清理提取的文本内容 - 更彻底的清理
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
                
                # 在加密流程中，若曾显示过动画则确保再次隐藏（当 parse 在内部控制动画时）
                try:
                    if anim_shown_after_password:
                        _ui_hide_loading()
                        anim_shown_after_password = False
                except Exception:
                    pass

                # 密码验证成功后，通知UI刷新内容显示
                try:
                    from textual.app import App
                    app = App.get_app()
                    # 尝试调用终端阅读器屏幕的刷新方法
                    if hasattr(app, 'screen') and hasattr(app.screen, '_load_book_content_async'):
                        # 使用正确的方式在UI线程中调用异步方法
                        if hasattr(app, 'run_worker'):
                            app.run_worker(app.screen._load_book_content_async(), exclusive=True)
                        else:
                            # 备用方案：直接调用
                            app.screen._load_book_content_async()
                except Exception as e:
                    logger.warning(f"刷新UI失败: {e}")
                
                return {
                    "content": content,
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", "未知作者"),
                    "chapters": chapters,
                    "metadata": metadata
                }
        except Exception as e:
            logger.error(f"解析PDF文件时出错: {e}")
            raise
    
    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文件格式
        
        Returns:
            List[str]: 支持的文件格式列表
        """
        return [".pdf"]
    
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

            logger.debug(f"Password dialog app check: has_app={bool(app)}, is_main_thread={is_main_thread}, has_push_screen_wait={(hasattr(app, 'push_screen_wait') if app else False)}, has_push_screen={(hasattr(app, 'push_screen') if app else False)}, has_call_from_thread={(hasattr(app, 'call_from_thread') if app else False)}")

            if app:
                from src.ui.dialogs.password_dialog import PasswordDialog
                try:
                    # 主线程且支持 push_screen_wait 时优先使用
                    # 移除主线程同步等待，统一走消息/回调桥接，避免阻塞UI
                    # 使用 App 消息桥接到主线程，避免跨线程直接 push_screen
                    logger.info("PasswordDialog: requesting via App message bridge")
                    import asyncio as _asyncio
                    loop = _asyncio.get_running_loop()
                    future: _asyncio.Future[Optional[str]] = loop.create_future()
                    try:
                        # 弹窗前尽量隐藏加载动画，避免遮挡
                        try:
                            if hasattr(app, "animation_manager") and getattr(app, "animation_manager"):
                                app.animation_manager.hide_default()
                        except Exception:
                            pass
                        # 优先使用 App 的主线程桥接方法 + 通用调度（最稳妥）
                        if hasattr(app, "request_password_async") and hasattr(app, "schedule_on_ui"):
                            logger.info("PasswordDialog.bridge via app.request_password_async using schedule_on_ui")
                            try:
                                app.schedule_on_ui(lambda: app.request_password_async(file_path, self.max_password_attempts, future))  # type: ignore[attr-defined]
                                return await future
                            except Exception as be:
                                logger.error(f"PasswordDialog.request_password_async scheduling via schedule_on_ui failed: {be}")
                        elif hasattr(app, "request_password_async") and hasattr(app, "call_from_thread"):
                            logger.info("PasswordDialog.bridge via app.request_password_async using call_from_thread")
                            try:
                                app.call_from_thread(lambda: app.request_password_async(file_path, self.max_password_attempts, future))  # type: ignore[attr-defined]
                                return await future
                            except Exception as be:
                                logger.error(f"PasswordDialog.request_password_async failed to schedule: {be}")
                        # 次优先：消息桥接
                        try:
                            from src.ui.messages import RequestPasswordMessage
                            msg = RequestPasswordMessage(file_path, self.max_password_attempts, future)
                            if hasattr(app, "post_message_from_thread"):
                                app.post_message_from_thread(msg)
                                logger.info("PasswordDialog.request posted via post_message_from_thread")
                            elif hasattr(app, "call_from_thread") and hasattr(app, "post_message"):
                                logger.info("PasswordDialog.post via call_from_thread(app.post_message)")
                                app.call_from_thread(lambda: app.post_message(msg))
                            else:
                                logger.warning("No message bridge API available; fallback to direct push")
                                def _on_result(result: Optional[str]) -> None:
                                    if not future.done():
                                        future.set_result(result)
                                logger.info("PasswordDialog._push executing (fallback)")
                                PasswordDialog.show(app, file_path, callback=_on_result)
                            return await future
                        except Exception as e:
                            logger.error(f"Message bridge failed: {e}")
                            # 最后兜底：CLI
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
                # 没有 GUI 应用实例，回退到命令行输入（避免阻塞）
                import asyncio as _asyncio
                return await _asyncio.to_thread(self._get_password_from_cli, file_path)
        except (ImportError, RuntimeError):
            # 回退到命令行输入（避免阻塞）
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
            print(f"请输入PDF文件密码 ({os.path.basename(file_path)})（留空跳过，输入'cancel'取消）: ", end="", flush=True)
            password = input().strip()
            if not password or password.lower() == 'cancel':
                return None
            return password
        except KeyboardInterrupt:
            return None

    def _extract_pdf_metadata(self, reader: PyPDF2.PdfReader) -> Dict[str, Any]:
        """
        从PDF文件中提取元数据
        
        Args:
            reader: PDF读取器对象
            
        Returns:
            Dict[str, Any]: 元数据字典
        """
        metadata = {}
        
        # 提取文档信息
        info = reader.metadata
        if info:
            # 提取标题
            if info.get('/Title'):
                metadata["title"] = info.get('/Title')
            
            # 提取作者
            if info.get('/Author'):
                metadata["author"] = info.get('/Author')
            
            # 提取主题
            if info.get('/Subject'):
                metadata["subject"] = info.get('/Subject')
            
            # 提取关键词
            if info.get('/Keywords'):
                metadata["keywords"] = info.get('/Keywords')
            
            # 提取创建者
            if info.get('/Creator'):
                metadata["creator"] = info.get('/Creator')
            
            # 提取生产者
            if info.get('/Producer'):
                metadata["producer"] = info.get('/Producer')
        
        return metadata
    
    def _extract_pdf_content(self, reader: PyPDF2.PdfReader) -> str:
        """
        从PDF文件中提取文本内容
        
        Args:
            reader: PDF读取器对象
            
        Returns:
            str: 文本内容
        """
        content = ""
        
        # 首先尝试使用pypdf提取
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            try:
                text = page.extract_text()
                if text:
                    content += text + "\n\n"
            except Exception as e:
                logger.warning(f"提取PDF第{page_num+1}页文本时出错: {e}")
                continue
        
        # 清理提取的文本内容
        content = self._clean_text_content(content)
        
        # 对PDF内容进行额外清理
        content = self._clean_pdf_specific_content(content)
        
        return content

    def _extract_pdf_content_pymupdf(self, file_path: str, password: Optional[str]) -> str:
        """
        使用 PyMuPDF 提取文本（优先用于未加密/CJK）
        """
        try:
            import fitz  # PyMuPDF
        except Exception:
            logger.debug("未安装 PyMuPDF，跳过该提取方式")
            return ""
        try:
            # 打开文档（自动识别是否需要密码）
            if password:
                doc = fitz.open(file_path, filetype="pdf", password=password)
            else:
                doc = fitz.open(file_path)
            texts: List[str] = []
            for page in doc:
                try:
                    # "text" 保留换行；若密集，改为 "text-with-spaces"
                    txt = page.get_text("text")
                    if not txt or len(txt.strip()) == 0:
                        txt = page.get_text("text-with-spaces")
                    if txt:
                        texts.append(txt)
                except Exception as e:
                    logger.debug(f"PyMuPDF 提取第{page.number+1}页失败: {e}")
                    continue
            try:
                doc.close()
            except Exception:
                pass
            content = "\n\n".join(texts)
            # 轻度清理，避免过度压缩中文空格；后续仍会经过 _clean_text_content/_clean_pdf_specific_content
            return content.strip()
        except Exception as e:
            logger.debug(f"PyMuPDF 提取失败: {e}")
            return ""
    
    def _needs_pdfminer_fallback(self, content: str) -> bool:
        """
        简单判断内容是否需要回退解析：
        - 内容过短
        - 有效字符比例过低（字母、数字、常见中日韩字符比例）
        """
        if not content or len(content.strip()) < 50:
            return True
        text = content.strip()
        import re as _re
        valid_chars = _re.findall(r"[A-Za-z0-9\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text)
        ratio = (len(valid_chars) / max(len(text), 1))
        return ratio < 0.25

    def _extract_pdf_content_pdfminer(self, file_path: str, password: Optional[str]) -> str:
        """
        使用 pdfminer.six 提取文本（优先使用）
        """
        try:
            from pdfminer.high_level import extract_text  # type: ignore
        except Exception:
            logger.warning("未安装 pdfminer.six，使用PyPDF2")
            return ""
        try:
            text = extract_text(file_path, password=password or "")
            return text or ""
        except Exception as e:
            logger.warning(f"pdfminer 提取文本失败: {e}")
            return ""

    def _extract_pdf_chapters(self, content: str) -> List[Dict[str, Any]]:
        """
        从PDF内容中提取章节
        
        Args:
            content: PDF内容
            
        Returns:
            List[Dict[str, Any]]: 章节列表
        """
        # 尝试根据内容分析章节
        # 这里使用简单的启发式方法，可能需要根据实际PDF文件结构进行调整
        chapters = []
        
        # 使用正则表达式查找可能的章节标题
        # 匹配"第X章"、"Chapter X"等常见章节标记
        chapter_patterns = [
            r"第\s*(\d+)\s*章\s*([^\n]+)",  # 中文章节标题
            r"Chapter\s*(\d+)\s*[:\.\s]*([^\n]+)",  # 英文章节标题
            r"CHAPTER\s*(\d+)\s*[:\.\s]*([^\n]+)"   # 大写英文章节标题
        ]
        
        # 存储所有匹配到的章节位置
        chapter_positions = []
        
        for pattern in chapter_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                chapter_num = match.group(1)
                chapter_title = match.group(2).strip()
                position = match.start()
                chapter_positions.append((position, f"第{chapter_num}章 {chapter_title}"))
        
        # 按位置排序章节
        chapter_positions.sort()
        
        # 如果找到章节，根据章节位置分割内容
        if chapter_positions:
            for i in range(len(chapter_positions)):
                start_pos = chapter_positions[i][0]
                title = chapter_positions[i][1]
                
                # 确定章节结束位置
                if i < len(chapter_positions) - 1:
                    end_pos = chapter_positions[i+1][0]
                else:
                    end_pos = len(content)
                
                # 提取章节内容
                chapter_content = content[start_pos:end_pos].strip()
                
                chapters.append({
                    "title": title,
                    "content": chapter_content
                })
        else:
            # 如果没有找到章节，尝试按页分割
            # 这里简单地按照双换行符分割，可能需要更复杂的逻辑
            parts = content.split("\n\n\n")
            if len(parts) > 1:
                for i, part in enumerate(parts):
                    if part.strip():
                        chapters.append({
                            "title": f"部分 {i+1}",
                            "content": part.strip()
                        })
            else:
                # 如果无法分割，将整个内容作为一个章节
                chapters = [{"title": "全文", "content": content}]
        
        return chapters
    
    def _clean_text_content(self, content: str) -> str:
        """
        彻底清理文本内容，确保返回纯文本
        
        Args:
            content: 原始内容
            
        Returns:
            str: 清理后的纯文本内容
        """
        if not content:
            return ""
        
        # 移除残留的HTML标签（如果有）
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除HTML实体
        import html
        content = html.unescape(content)
        
        # 移除控制字符和非打印字符（保留空格、换行、制表符等）
        # 更彻底地清理控制字符，包括一些特殊的Unicode控制字符
        content = re.sub(r'[\x00-\x1f\x7f-\xa0\u2000-\u200f\u2028-\u202f\u2060-\u206f\ufeff]', '', content)
        
        # 移除零宽空格和其他不可见字符
        content = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', content)
        
        # 移除BOM标记
        content = content.replace('\ufeff', '')
        
        # 移除PDF特有的格式字符
        content = re.sub(r'[\xad\u00ad\u2011]', '', content)  # 软连字符和不可断连字符
        
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 规范化换行
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # 移除行首行尾空白
        lines = content.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        content = '\n'.join(lines)
        
        # 移除多余的空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 确保内容不为空
        if not content.strip():
            return "无法提取有效文本内容"
        
        return content.strip()
    
    def _clean_pdf_specific_content(self, content: str) -> str:
        """
        专门清理PDF提取的内容，处理PDF特有的格式问题
        
        Args:
            content: PDF提取的原始内容
            
        Returns:
            str: 清理后的内容
        """
        if not content:
            return ""
        
        # 移除PDF特有的格式字符和不可见字符
        # 移除所有ASCII控制字符（0-31，127-159）
        content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
        
        # 移除Unicode控制字符和格式字符
        content = re.sub(r'[\u2000-\u200f\u2028-\u202f\u2060-\u206f\ufeff]', '', content)
        
        # 移除零宽空格和其他不可见字符
        content = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', content)
        
        # 移除PDF中常见的格式标记
        content = re.sub(r'[\xad\u00ad]', '', content)  # 软连字符
        
        # 规范化空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 规范化换行
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # 移除行首行尾空白
        lines = content.split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        content = '\n'.join(lines)
        
        return content.strip()