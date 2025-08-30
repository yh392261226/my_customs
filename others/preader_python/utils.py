import chardet
import cjkwrap
import time

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

def build_pages_from_text(text, width, height, line_spacing):
    """
    将文本内容分页，考虑行间距和页面高度
    """
    display_lines = []
    # 合并所有文本为显示行列表
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    
    # 简单的进度提示
    print("处理文本行...")
    for i, rawline in enumerate(lines):
        # cjkwrap.wrap 返回每行不超过 width 的字符串列表
        for sub_line in cjkwrap.wrap(rawline, width):
            display_lines.append(sub_line)
            for _ in range(line_spacing - 1):
                display_lines.append("")
        if i % 100 == 0:  # 每100行显示一次进度
            print(f"已处理 {i}/{len(lines)} 行")
            
    # 逐页切分，不丢任何内容
    pages = []
    idx = 0
    print("分页处理...")
    while idx < len(display_lines):
        page = display_lines[idx:idx+height]
        pages.append(page)
        idx += height
        if idx % (height * 10) == 0:  # 每10页显示一次进度
            print(f"已处理 {idx}/{len(display_lines)} 行")
            
    return pages

def build_pages_from_file(file_path, width, height, line_spacing):
    """
    完全不丢失内容的分页算法（逐显示行流式分页，支持中英文混合宽度）。
    width: 每行显示宽度
    height: 每页最大行数
    line_spacing: 行间距
    """
    # 简单的加载提示
    print("读取文件...")
    text = stream_file_as_text(file_path)
    
    print("处理文本内容...")
    pages = build_pages_from_text(text, width, height, line_spacing)
    
    return pages