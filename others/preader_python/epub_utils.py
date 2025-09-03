from ebooklib import epub
from bs4 import BeautifulSoup
from utils import build_pages_from_text
from lang import get_text

def parse_epub(file_path, width, height, line_spacing, paragraph_spacing, lang="zh"):
    book = epub.read_epub(file_path)
    
    chapters = []
    items = list(book.get_items())
    
    for item in items:
        # 使用正确的常量
        if item.get_type() == epub.ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            title = soup.title.string if soup.title else ""
            text = soup.get_text()
            
            # 添加缺少的 paragraph_spacing 参数
            pages = build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, lang=lang)
            chapters.append({"title": title, "pages": pages})
            
    return chapters

def get_epub_metadata(file_path):
    book = epub.read_epub(file_path)
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else ""
    author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else ""
    return title, author