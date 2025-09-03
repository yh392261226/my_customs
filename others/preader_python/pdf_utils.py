import PyPDF2
import pdfplumber
from utils import build_pages_from_text
from lang import get_text

class EncryptedPDFError(Exception):
    """PDF文件已加密异常"""
    pass

def parse_pdf(file_path, width, height, line_spacing, paragraph_spacing, lang="zh", password=None):
    """解析PDF文件，支持加密PDF"""
    pages = []
    
    try:
        # 使用PyPDF2提取文本
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # 检查PDF是否加密
            if pdf_reader.is_encrypted:
                if password is None:
                    raise EncryptedPDFError("PDF is encrypted")
                
                # 尝试使用提供的密码解密
                if not pdf_reader.decrypt(password):
                    raise EncryptedPDFError("Incorrect password")
            
            num_pages = len(pdf_reader.pages)
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # 使用统一的文本分页函数
                page_content = build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, lang=lang)
                pages.extend(page_content)
                
    except EncryptedPDFError:
        # 重新抛出加密异常，让调用者处理
        raise
    except Exception as e:
        # 如果PyPDF2失败，尝试使用pdfplumber
        try:
            with pdfplumber.open(file_path, password=password) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        page_content = build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, lang=lang)
                        pages.extend(page_content)
        except Exception as e2:
            # 检查是否是密码错误
            if "password" in str(e2).lower() or "encrypted" in str(e2).lower():
                raise EncryptedPDFError("PDF is encrypted")
            else:
                error_msg = f"{get_text('cannot_load_novel', lang)}: {str(e2)}"
                pages = [[error_msg]]
    
    return pages

def get_pdf_metadata(file_path, password=None):
    """获取PDF元数据，支持加密PDF"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # 检查PDF是否加密
            if pdf_reader.is_encrypted:
                if password is None:
                    # 返回None表示需要密码，但不抛出异常
                    return None, None
                
                # 尝试使用提供的密码解密
                if not pdf_reader.decrypt(password):
                    # 密码不正确，返回None
                    return None, None
            
            info = pdf_reader.metadata
            
            title = info.get('/Title', '') if info else ''
            author = info.get('/Author', '') if info else ''
            
            return title, author
    # 发生任何异常都返回None
    except Exception:
        return None, None

def is_pdf_encrypted(file_path):
    """检查PDF是否加密"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return pdf_reader.is_encrypted
    except Exception:
        return False