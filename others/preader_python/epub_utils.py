from ebooklib import epub
from bs4 import BeautifulSoup

def parse_epub(file_path, width, height, line_spacing):
    book = epub.read_epub(file_path)
    chapters = []
    for item in book.get_items():
        if item.get_type() == epub.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            title = soup.title.string if soup.title else ""
            text = soup.get_text()
            lines = text.splitlines()
            # 分页
            pages = []
            page = []
            for line in lines:
                while len(line) > width:
                    page.append(line[:width])
                    line = line[width:]
                    if len(page) >= height:
                        pages.append(page)
                        page = []
                page.append(line)
                for _ in range(line_spacing-1):
                    page.append("")
                if len(page) >= height:
                    pages.append(page)
                    page = []
            if page:
                pages.append(page)
            chapters.append({"title": title, "pages": pages})
    return chapters

def get_epub_metadata(file_path):
    book = epub.read_epub(file_path)
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else ""
    author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else ""
    return title, author