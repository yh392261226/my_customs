import chardet
import cjkwrap

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

def build_pages_from_text(text, width, height, line_spacing, progress_callback=None):
    """
    将文本内容分页，考虑行间距和页面高度
    """
    display_lines = []
    # 合并所有文本为显示行列表
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    
    total_lines = len(lines)
    for i, rawline in enumerate(lines):
        # cjkwrap.wrap 返回每行不超过 width 的字符串列表
        for sub_line in cjkwrap.wrap(rawline, width):
            display_lines.append(sub_line)
            for _ in range(line_spacing - 1):
                display_lines.append("")
        
        # 每100行报告一次进度
        if progress_callback and i % 100 == 0:
            progress_callback(f"处理文本行: {i}/{total_lines}")
            
    # 逐页切分，不丢任何内容
    pages = []
    idx = 0
    total_display_lines = len(display_lines)
    
    while idx < total_display_lines:
        page = display_lines[idx:idx+height]
        pages.append(page)
        idx += height
        
        # 每10页报告一次进度
        if progress_callback and idx % (height * 10) == 0:
            progress_callback(f"分页处理: {idx}/{total_display_lines}")
            
    return pages

def build_pages_from_file(file_path, width, height, line_spacing, progress_callback=None):
    """
    完全不丢失内容的分页算法（逐显示行流式分页，支持中英文混合宽度）。
    width: 每行显示宽度
    height: 每页最大行数
    line_spacing: 行间距
    """
    if progress_callback:
        progress_callback("读取文件...")
    text = stream_file_as_text(file_path)
    
    if progress_callback:
        progress_callback("处理文本内容...")
    pages = build_pages_from_text(text, width, height, line_spacing, progress_callback)
    
    return pages