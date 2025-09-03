import PyPDF2
import pdfplumber
from utils import build_pages_from_text
from lang import get_text

def parse_pdf(file_path, width, height, line_spacing, paragraph_spacing, lang="zh"):
    """解析PDF文件"""
    pages = []
    
    try:
        # 使用PyPDF2提取文本
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                
                # 使用统一的文本分页函数
                page_content = build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, lang=lang)
                pages.extend(page_content)
                
    except Exception as e:
        # 如果PyPDF2失败，尝试使用pdfplumber
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        page_content = build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, lang=lang)
                        pages.extend(page_content)
        except Exception as e2:
            error_msg = f"{get_text('cannot_load_novel', lang)}: {str(e2)}"
            pages = [[error_msg]]
    
    return pages

def get_pdf_metadata(file_path):
    """获取PDF元数据"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            info = pdf_reader.metadata
            
            title = info.get('/Title', '') if info else ''
            author = info.get('/Author', '') if info else ''
            
            return title, author
    except:
        return None, None