"""
书籍存储目录布局工具。

新的目录结构（解决单一目录文件过多的问题）：

    书籍库根目录 / 来源网站 / 书名首字母(或首字符) / 书籍文件

导入（无来源网站）的书籍：

    书籍库根目录 / _imported / 书名首字母(或首字符) / 书籍文件

其中「书名首字母」的归类规则（目录名只为 ASCII，避免中文目录乱码）：
    - 先把整本书名转成拼音串；
    - 从拼音串中从左到右取第一个出现的字母（大写 A-Z）或数字（0-9）；
    - 拼音转换失败/为空时回退到原标题中的 ASCII 字母/数字；
    - 仍无法取得时回退为 "#"。
"""
import os
import re

# 导入书籍（无来源网站）统一放置的子目录名
IMPORT_DIR_NAME = "_imported"


def sanitize_dirname(name: str) -> str:
    """把任意字符串转换为安全的目录名（去除路径分隔符等特殊字符）。"""
    name = (name or "").strip()
    # 去除 Windows / 类 Unix 下不允许出现在文件名中的字符
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(". ")
    return name or "unknown"


def safe_site_dirname(site_name: str) -> str:
    """把站点名转换为 ASCII 安全的目录名，避免中文目录在部分文件系统/工具下出现乱码。

    - 中文转为拼音（复用项目已有的 convert_to_pinyin，无声调）；
    - 非中文部分（字母、数字等）原样保留；
    - 其余特殊字符清洗；若拼音结果为空则回退到清洗后的原名。
    """
    name = (site_name or "").strip()
    if not name:
        return "unknown"
    try:
        from src.core.database_manager import convert_to_pinyin
        pinyin_name = convert_to_pinyin(name)
    except Exception:
        pinyin_name = ""
    candidate = pinyin_name if pinyin_name else name
    return sanitize_dirname(candidate)


def get_title_first_letter(title: str) -> str:
    """根据书名返回分组目录名（首字母 / 首个数字），目录名只为 ASCII。

    规则：
    - 先把整本书名转成拼音串；
    - 从拼音串中从左到右取第一个出现的「字母」(转为大写) 或「数字」；
    - 拼音转换失败/为空时，回退到原标题中的 ASCII 字母/数字；
    - 仍无法取得时回退为 "#"。
    """
    title = (title or "").strip()
    if not title:
        return "#"
    pinyin_text = ""
    try:
        from src.core.database_manager import convert_to_pinyin
        pinyin_text = convert_to_pinyin(title)
    except Exception:
        pass
    # 优先扫描拼音串；拼音为空（如纯符号或拼音库不可用）时回退原标题
    source = pinyin_text if pinyin_text else title
    for ch in source:
        if ch.isascii() and ch.isalpha():
            return ch.upper()
        if ch.isdigit():
            return ch
    return "#"


def get_crawl_storage_dir(base_dir: str, site_name: str, title: str) -> str:
    """爬取书籍的存储目录： base_dir / 来源网站 / 书名首字母 """
    site_dir = safe_site_dirname(site_name)
    letter = get_title_first_letter(title)
    return os.path.join(base_dir, site_dir, letter)


def get_import_storage_dir(library_root: str, title: str) -> str:
    """导入书籍（无来源网站）的存储目录： library_root / _imported / 书名首字母 """
    letter = get_title_first_letter(title)
    return os.path.join(library_root, IMPORT_DIR_NAME, letter)


def make_unique_path(target_path: str) -> str:
    """若目标路径已存在，则返回带自增序号的唯一路径，避免覆盖。"""
    if not os.path.exists(target_path):
        return target_path
    base, ext = os.path.splitext(target_path)
    n = 1
    while True:
        candidate = f"{base}_{n}{ext}"
        if not os.path.exists(candidate):
            return candidate
        n += 1
