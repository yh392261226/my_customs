import mobi
import os
import tempfile
from utils import build_pages_from_text
from lang import get_text

def parse_mobi(file_path, width, height, line_spacing, paragraph_spacing, lang="zh"):
    """解析MOBI文件"""
    try:
        # 使用mobi库提取文本
        temp_dir, filepath = mobi.extract(file_path)
        
        # 读取提取的HTML内容
        html_file = None
        for file in os.listdir(temp_dir):
            if file.endswith('.html'):
                html_file = os.path.join(temp_dir, file)
                break
        
        if html_file:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用BeautifulSoup提取纯文本
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text()
            
            # 使用统一的文本分页函数
            pages = build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, lang=lang)
            
            # 清理临时文件
            import shutil
            shutil.rmtree(temp_dir)
            
            return pages
        else:
            return [[f"{get_text('cannot_load_novel', lang)}: No HTML content found"]]
            
    except Exception as e:
        return [[f"{get_text('cannot_load_novel', lang)}: {str(e)}"]]

def get_mobi_metadata(file_path):
    """获取MOBI元数据"""
    try:
        # mobi库可以获取元数据
        metadata = mobi.read_metadata(file_path)
        title = metadata.get('title', '')
        author = metadata.get('author', '')
        return title, author
    except:
        return None, None