import chardet

def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        raw = f.read(10000)
    res = chardet.detect(raw)
    encoding = res["encoding"] if res and res["encoding"] else "utf-8"
    return encoding

def stream_lines_utf8(file_path):
    encoding = detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="ignore") as f:
        for line in f:
            yield line.rstrip("\r\n")

def build_pages_from_file(file_path, width, height, line_spacing):
    page = []
    pages = []
    for line in stream_lines_utf8(file_path):
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
    return pages