import chardet
import cjkwrap
from lang import get_text

def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        raw = f.read(10000)
    res = chardet.detect(raw)
    encoding = res["encoding"] if res and res["encoding"] else "utf-8"
    return encoding

def stream_file_as_text(file_path):
    encoding = detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="ignore") as f:
        return f.read()

def build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, progress_callback=None, lang="zh"):
    """
    将文本内容分页，考虑行间距和段落间距
    确保不会丢失任何内容
    """
    # 检查文本是否为空
    if not text or not text.strip():
        return [[f"{get_text('empty_directory_or_file', lang)}"]]

    display_lines = []
    # 合并所有文本为显示行列表
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    
    total_lines = len(lines)
    for i, rawline in enumerate(lines):
        # 处理空行（段落间距）
        if not rawline.strip():
            for _ in range(max(0, paragraph_spacing)):
                display_lines.append("")
            continue
            
        # 确保宽度至少为1
        wrap_width = max(1, width)
        wrapped_lines = cjkwrap.wrap(rawline, wrap_width)
        
        for j, sub_line in enumerate(wrapped_lines):
            display_lines.append(sub_line)
            # 添加行间距（除了最后一行的行间距）
            if j < len(wrapped_lines) - 1 or line_spacing > 0:
                for _ in range(max(0, line_spacing)):
                    display_lines.append("")
        
        # 每100行报告一次进度
        if progress_callback and i % 100 == 0:
            progress_callback(f"{get_text('action_document_line', lang)}: {i}/{total_lines}")
            
    # 逐页切分，不丢任何内容
    pages = []
    idx = 0
    total_display_lines = len(display_lines)
    
    # 确保高度至少为1
    page_height = max(1, height)
    
    while idx < total_display_lines:
        page = display_lines[idx:idx+page_height]
        pages.append(page)
        idx += page_height
        
        # 每10页报告一次进度
        if progress_callback and idx % (page_height * 10) == 0:
            progress_callback(f"{get_text('action_pages', lang)}: {idx}/{total_display_lines}")
            
    return pages


def build_pages_from_file(file_path, width, height, line_spacing, paragraph_spacing, progress_callback=None, lang="zh"):
    """
    完全不丢失内容的分页算法
    """
    if progress_callback:
        progress_callback(f"{get_text('reading_from_file', lang)}")
    
    text = stream_file_as_text(file_path)
    
    if progress_callback:
        progress_callback(f"{get_text('action_document_file', lang)}")
    
    pages = build_pages_from_text(text, width, height, line_spacing, paragraph_spacing, progress_callback, lang)
    
    return pages