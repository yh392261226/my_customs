from ebooklib import epub
from bs4 import BeautifulSoup
from utils import build_pages_from_text
import time

def parse_epub(file_path, width, height, line_spacing):
    # 简单的加载提示
    print("解析EPUB文件...")
    book = epub.read_epub(file_path)
    
    chapters = []
    items = list(book.get_items())
    
    print("解析章节内容...")
    for i, item in enumerate(items):
        if item.get_type() == epub.ITEM_DOCUMENT:
            print(f"处理章节 {len(chapters)+1}")
            soup = BeautifulSoup(item.get_content(), "html.parser")
            title = soup.title.string if soup.title else ""
            text = soup.get_text()
            
            # 使用统一的文本分页函数
            pages = build_pages_from_text(text, width, height, line_spacing)
            chapters.append({"title": title, "pages": pages})
            
    return chapters

def get_epub_metadata(file_path):
    book = epub.read_epub(file_path)
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else ""
    author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else ""
    return title, author