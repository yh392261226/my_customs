import os
import sys
import tempfile
import shutil
import subprocess
from utils import build_pages_from_text
from lang import get_text

# 添加KindleUnpack到Python路径
KINDLEUNPACK_PATH = os.path.join(os.path.dirname(__file__), 'KindleUnpack')
sys.path.insert(0, KINDLEUNPACK_PATH)

def parse_azw(file_path, width, height, line_spacing, paragraph_spacing, lang="zh"):
    """解析AZW/AZW3文件"""
    try:
        # 创建临时输出目录
        temp_output_dir = tempfile.mkdtemp()
        
        # 使用KindleUnpack命令行工具
        cmd = [
            sys.executable, 
            os.path.join(KINDLEUNPACK_PATH, 'lib/kindleunpack.py'), 
            '-s',  # 安静模式
            '-r',  # 生成EPUB
            file_path, 
            temp_output_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            raise Exception(f"KindleUnpack failed: {result.stderr}")
        
        # 在输出目录中查找HTML内容
        html_content = extract_html_from_unpacked(temp_output_dir)
        
        if not html_content:
            raise Exception("No HTML content found after unpacking")
        
        # 使用统一的文本分页函数
        pages = build_pages_from_text(html_content, width, height, line_spacing, paragraph_spacing, lang=lang)
        
        # 清理临时目录
        shutil.rmtree(temp_output_dir)
        
        return pages
        
    except subprocess.TimeoutExpired:
        return [[f"{get_text('cannot_load_novel', lang)}: {get_text('parsing_data_outtime', lang)}"]]
    except Exception as e:
        # 确保临时目录被清理
        try:
            shutil.rmtree(temp_output_dir)
        except:
            pass
        return [[f"{get_text('cannot_load_novel', lang)}: {str(e)}"]]

def extract_html_from_unpacked(unpacked_dir):
    """从解包目录中提取HTML内容，按照正确的章节顺序"""
    html_content = ""
    
    # 优先查找OPF文件来确定阅读顺序
    opf_files = []
    for root, dirs, files in os.walk(unpacked_dir):
        for file in files:
            if file.endswith('.opf'):
                opf_files.append(os.path.join(root, file))
    
    if opf_files:
        # 解析OPF文件获取阅读顺序
        reading_order = parse_reading_order_from_opf(opf_files[0])
        
        # 按照阅读顺序提取HTML内容
        for item in reading_order:
            html_file_path = find_html_file(unpacked_dir, item)
            if html_file_path and os.path.exists(html_file_path):
                try:
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 使用BeautifulSoup提取纯文本
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # 提取章节标题
                    title = extract_chapter_title(soup)
                    if title:
                        html_content += f"\n\n{title}\n\n"
                    
                    html_content += soup.get_text() + "\n\n"
                except Exception as e:
                    print(f"Error reading {html_file_path}: {str(e)}")
                    continue
    else:
        # 如果没有OPF文件，回退到原始方法
        html_content = extract_html_fallback(unpacked_dir)
    
    return html_content

def parse_reading_order_from_opf(opf_path):
    """从OPF文件中解析阅读顺序"""
    reading_order = []
    
    try:
        import xml.etree.ElementTree as ET
        
        # 解析OPF文件
        tree = ET.parse(opf_path)
        root = tree.getroot()
        
        # 定义命名空间
        ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # 获取manifest中的项目映射
        manifest_items = {}
        for item in root.findall('.//opf:manifest/opf:item', ns):
            item_id = item.get('id')
            item_href = item.get('href')
            manifest_items[item_id] = item_href
        
        # 获取spine中的阅读顺序
        for itemref in root.findall('.//opf:spine/opf:itemref', ns):
            item_id = itemref.get('idref')
            if item_id in manifest_items:
                reading_order.append(manifest_items[item_id])
    
    except Exception as e:
        print(f"Error parsing OPF file: {str(e)}")
    
    return reading_order

def find_html_file(base_dir, href):
    """根据OPF中的href查找实际的HTML文件"""
    # 处理相对路径
    html_path = os.path.normpath(os.path.join(base_dir, href))
    
    # 如果文件存在，直接返回
    if os.path.exists(html_path):
        return html_path
    
    # 如果文件不存在，尝试在base_dir的子目录中查找
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == os.path.basename(href):
                return os.path.join(root, file)
    
    # 如果还是找不到，尝试使用不同的扩展名
    base_name = os.path.splitext(href)[0]
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if os.path.splitext(file)[0] == base_name and (file.endswith('.html') or file.endswith('.xhtml')):
                return os.path.join(root, file)
    
    return None

def extract_chapter_title(soup):
    """从HTML中提取章节标题"""
    # 尝试多种可能的标题选择器
    title_selectors = [
        'h1', 'h2', 'h3', 
        '.chapter-title', '.title', '[class*="title"]',
        '#chapter-title', '#title'
    ]
    
    for selector in title_selectors:
        title_elem = soup.select_one(selector)
        if title_elem and title_elem.get_text().strip():
            return title_elem.get_text().strip()
    
    return None

def extract_html_fallback(unpacked_dir):
    """备用的HTML提取方法（当没有OPF文件时使用）"""
    html_content = ""
    
    # 收集所有HTML文件
    html_files = []
    for root, dirs, files in os.walk(unpacked_dir):
        for file in files:
            if file.endswith('.html') or file.endswith('.xhtml'):
                html_files.append(os.path.join(root, file))
    
    # 尝试按照数字顺序排序（假设文件名包含章节号）
    def extract_number(filename):
        import re
        match = re.search(r'(\d+)', os.path.basename(filename))
        return int(match.group(1)) if match else 0
    
    html_files.sort(key=extract_number)
    
    # 按顺序提取内容
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # 提取章节标题
            title = extract_chapter_title(soup)
            if title:
                html_content += f"\n\n{title}\n\n"
            
            html_content += soup.get_text() + "\n\n"
        except Exception as e:
            print(f"Error reading {html_file}: {str(e)}")
            continue
    
    return html_content


def get_azw_metadata(file_path):
    """获取AZW/AZW3元数据"""
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 使用KindleUnpack提取元数据
        cmd = [
            sys.executable, 
            os.path.join(KINDLEUNPACK_PATH, 'KindleUnpack.py'), 
            '-s',  # 安静模式
            '-r',  # 生成EPUB
            file_path, 
            temp_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # 尝试从OPF文件中提取元数据
        opf_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.opf'):
                    opf_files.append(os.path.join(root, file))
        
        title, author = None, None
        if opf_files:
            import xml.etree.ElementTree as ET
            try:
                tree = ET.parse(opf_files[0])
                root = tree.getroot()
                
                # 查找命名空间
                ns = {'opf': 'http://www.idpf.org/2007/opf', 
                      'dc': 'http://purl.org/dc/elements/1.1/'}
                
                title_elem = root.find('.//dc:title', ns)
                if title_elem is not None:
                    title = title_elem.text
                
                creator_elem = root.find('.//dc:creator', ns)
                if creator_elem is not None:
                    author = creator_elem.text
            except:
                pass
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        return title, author
        
    except Exception:
        # 确保临时目录被清理
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        return None, None