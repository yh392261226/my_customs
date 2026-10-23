"""
书籍固定排版工具（仅针对 .txt 书籍）。

目标：把爬虫抓取的、章节标题五花八门（第N章 / 第一章 / 12 / (12) / [12] /
Chapter N …）的内容，统一排版为固定样式，便于阅读器展示与章节识别：

    书名

    章节 1
        段落一内容……

        段落二内容……

    章节 2
        ……

设计要点：
- 章节标题归一化为「章节 N」前缀（保留原标题中的描述性文字作为后缀）；
- 正文每段前缩进 4 个空格；
- 章节之间用空行分隔（不再使用任何人工分隔符）；
- 段落归一化：以空行为段落边界，单行内的软换行合并为一段（重排），
  对完全没有换行的长文本做兜底句末切分。
"""

import re

# 章节标题中可能出现的简体中文数字
_CN_NUM = {
    '零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
}

# 用于从各式各样的章节标题中提取章节号的模式；
# 每个模式捕获「数字部分」（阿拉伯数字或中文数字），按顺序尝试。
# 注意：章/回/节 优先于 卷/部/篇 匹配，避免「第3卷第5章」被误取为卷号。
# 首条为已归一化的「章节 N」格式，保证对已排版内容再次重排时仍可识别并保留描述。
_CHAPTER_NUM_PATTERNS = [
    r'章节\s*(\d+|[零〇一二两三四五六七八九十百千]+)',            # 已归一化「章节 N」（优先，保证重排幂等）
    r'第\s*(\d+|[零〇一二两三四五六七八九十百千]+)\s*[章回节]',  # 第1章 / 第一章 / 第 12 回（优先）
    r'第\s*(\d+|[零〇一二两三四五六七八九十百千]+)\s*卷',        # 第3卷（卷号，兜底）
    r'[（\(]\s*(\d+|[零〇一二两三四五六七八九十]+)\s*[）\)]',     # (12) / [12]
    r'[Cc]hapter\s*(\d+|[零〇一二两三四五六七八九十]+)',          # Chapter 3
    r'^\s*\[?\s*(\d+|[零〇一二两三四五六七八九十]+)\s*\]?\s*$',   # 纯数字 12 / [12]
    r'^\s*(\d+|[零〇一二两三四五六七八九十]+)\s*[\.、\)）]',     # 12. / 12、 / 12)
]

# 普通段落的缩进宽度
_INDENT = "    "

# 智能分段相关常量
# 句末标点：遇到即视为一个句子的结束（引号外）
_SENT_END = set('。！？!?…')
# 直接引语的开引号 -> 闭引号映射（ASCII 双/单引号开闭同形）
_OPEN_QUOTES = {'“': '”', '「': '」', '『': '』', '"': '"', '‘': '’', "'": "'"}
# 闭引号集合：仅在已处于引号内时才作为结束符，避免把孤立闭引号误判为开引号
_CLOSE_QUOTES = set('”」』’')
# 引导直接引语的提示性结尾（冒号、开引号等）：其后紧跟的引语视为「同位」不另起段
_LEADIN_TAIL = ('：', ':', '“', '「', '『', '"', '‘', "'", '—', '——', '（', '(')
# 单段最大字符数：超过则在该句/片段边界处收束另起一段
_MAX_PARA_LEN = 180


def _normalize_fullwidth(text: str) -> str:
    """
    仅把「全角数字 / 全角字母 / 全角空格」转成半角。

    爬虫抓来的正文常见 ２２岁、１５８公分、３４Ｄ 这类全角 ASCII 残留，
    阅读时既难看又影响排版宽度。但中文正常的全角标点（。！？、：等）属于
    U+FF01~U+FF5E 全角区块，必须原样保留，故此处只处理数字/字母/全角空格。
    """
    if not text:
        return text
    out = []
    for ch in text:
        cp = ord(ch)
        if 0xFF10 <= cp <= 0xFF19:        # ０-９ -> 0-9
            out.append(chr(cp - 0xFF10 + 0x30))
        elif 0xFF21 <= cp <= 0xFF3A:      # Ａ-Ｚ -> A-Z
            out.append(chr(cp - 0xFF21 + 0x41))
        elif 0xFF41 <= cp <= 0xFF5A:      # ａ-ｚ -> a-z
            out.append(chr(cp - 0xFF41 + 0x61))
        elif ch == '\u3000':              # 全角空格 -> 半角空格
            out.append(' ')
        else:
            out.append(ch)
    return ''.join(out)


def _segment_with_quotes(text: str) -> list:
    """
    把正文切成片段序列，每项为 (kind, content)，kind ∈ {'quote', 'text'}。

    规则：
    - 引号内的完整内容（含其中的句号/感叹号/问号）作为一个 quote 片段，
      不会被拆成多句——这保证了「配文："……。"」「"媛媛别委屈！……！"」
      这类直接引语整体不被切断。
    - 引号外的文本按句末标点切分为 text 片段（每片段通常是一句话）。
    - 未被闭合的引号在超过安全长度后强制收尾，避免吞噬整段。
    """
    segs = []
    buf = ''
    kind = 'text'
    quote_open = None      # 当前打开的引号开字符
    quote_close = None     # 对应的闭引号字符
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote_open:
            buf += ch
            # 命中闭引号，或引号过长（防失衡），结束该引语片段
            if ch == quote_close or len(buf) > 500:
                segs.append(('quote', buf))
                buf = ''
                quote_open = None
                quote_close = None
            i += 1
            continue
        # 不在引号内
        if ch in _OPEN_QUOTES:
            if buf:
                segs.append(('text', buf))
                buf = ''
            quote_open = ch
            quote_close = _OPEN_QUOTES[ch]
            buf = ch
            i += 1
            continue
        if ch in _CLOSE_QUOTES:
            # 落单的闭引号：当作普通字符，不开启引号
            buf += ch
            i += 1
            continue
        if ch in _SENT_END:
            buf += ch
            segs.append(('text', buf))
            buf = ''
            i += 1
            continue
        buf += ch
        i += 1
    if buf:
        segs.append(('text', buf))
    return segs


def _smart_paragraphs(text: str, max_len: int = _MAX_PARA_LEN) -> list:
    """
    把一段「无换行」的正文智能聚合为多个自然段落（不含缩进）。

    分段信号：
    - 直接引语（quote 片段）通常独立成段；但若它紧跟在引语提示
      （「配文：」「说：」等以 _LEADIN_TAIL 结尾的文本）之后，则视为同位，
      与提示合并为一段。
    - 引语结束回到叙述（quote -> text）时另起一段。
    - 连续叙述按长度聚合，超过 max_len 后在片段边界收束，避免一整面“文字墙”。
    """
    segs = _segment_with_quotes(text)
    paras = []
    cur = []
    cur_len = 0
    last_kind = None
    last_tail = ''     # 上一个 text 片段的结尾字符（用于判断是否为引语提示）
    for kind, txt in segs:
        t = txt.strip()
        if not t:
            continue
        break_before = False
        if cur:
            if kind == 'quote':
                # 引语：若前文也是引语（连续多说话人），或前文不是引语提示
                # （不以 ：/开引号 等结尾），则另起一段
                if last_kind == 'quote' or \
                        (last_kind == 'text' and last_tail not in _LEADIN_TAIL):
                    break_before = True
            else:  # text：引语结束后的叙述另起一段
                if last_kind == 'quote':
                    break_before = True
        if break_before:
            paras.append(''.join(cur))
            cur = []
            cur_len = 0
            last_kind = None
            last_tail = ''
        cur.append(txt)
        cur_len += len(txt)
        last_kind = kind
        last_tail = t[-1] if t else ''
        # 段落过长则强制在下一片段前断开
        if cur_len >= max_len:
            paras.append(''.join(cur))
            cur = []
            cur_len = 0
            last_kind = None
            last_tail = ''
    if cur:
        paras.append(''.join(cur))
    return [p for p in paras if p.strip()]


def reflow_paragraphs(text: str, indent: str = _INDENT,
                      max_para_len: int = _MAX_PARA_LEN) -> list:
    """
    把章节正文重排为统一段落：以空行为段落边界，段内软换行合并为一行，
    对完全没有换行/结构的长文本做智能分段（引号成句、对话独立、按长度收束）；
    每个段落统一缩进。

    返回缩进后的段落字符串列表（不含空段）。
    """
    if not text:
        return []

    # 以一个或多个空行作为段落边界切分
    blocks = re.split(r'\n\s*\n', text)

    paragraphs = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # 跳过残留的 Markdown 标题行（# 书名 / ## 章节）：否则会作为正文段落出现
        if re.match(r'^#{1,6}\s+\S', block):
            continue

        # 段落内有换行：合并软换行为一段（去掉每行首尾空白）
        if '\n' in block:
            lines = [ln.strip() for ln in block.split('\n')]
            lines = [ln for ln in lines if ln]
            if lines:
                merged = _normalize_fullwidth(''.join(lines))
                paragraphs.append(indent + merged)
            continue

        # 单行长文本：智能分段（引号成句、对话独立、按长度收束），
        # 替代原先「见句末标点就换行」的生硬切分。
        for p in _smart_paragraphs(block, max_para_len):
            paragraphs.append(indent + _normalize_fullwidth(p))

    return paragraphs


def cn_to_int(text: str):
    """把中文数字（支持 零~万 量级）转换为整数；纯阿拉伯数字直接转。"""
    if text is None:
        return None
    s = text.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)

    num = 0
    cur = 0
    for ch in s:
        if ch in _CN_NUM:
            cur = _CN_NUM[ch]
        elif ch == '十':
            cur = (cur * 10 + 10) if cur else 10
            num += cur
            cur = 0
        elif ch == '百':
            num += (cur if cur else 1) * 100
            cur = 0
        elif ch == '千':
            num += (cur if cur else 1) * 1000
            cur = 0
        elif ch == '万':
            num = (num + cur) * 10000
            cur = 0
        else:
            # 遇到无法识别的字符（如「第」「章」等）直接忽略
            continue
    num += cur
    return num if num > 0 else None


def extract_chapter_number(raw_title: str):
    """从章节标题中提取章节号（整数），无法提取时返回 None。"""
    if not raw_title:
        return None
    for pattern in _CHAPTER_NUM_PATTERNS:
        m = re.search(pattern, raw_title)
        if m:
            value = cn_to_int(m.group(1))
            if value is not None:
                return value, m
    return None


def normalize_chapter_title(raw_title: str, position_index: int) -> str:
    """
    把任意章节标题归一化为「章节 N [描述]」。

    - 能提取到章节号则用提取到的号（保留真实编号，如 (12) -> 12）；
    - 提取不到则用位置序号作为兜底；
    - 保留原标题中章节号之后的描述性文字（如「美女班长」）。
    """
    fallback_num = position_index if position_index and position_index > 0 else 1
    num = fallback_num
    remainder = ""

    result = extract_chapter_number(raw_title)
    if result:
        num, m = result
        # 取匹配位置之后的文字作为描述性后缀
        after = raw_title[m.end():]
        after = after.strip()
        # 去掉开头常见的分隔/标点
        after = re.sub(r'^[\s：:、\-—·|~]+', '', after)
        if after and not re.fullmatch(r'[\s\d（）\(\)\[\]【】]+', after):
            remainder = after

    label = f"章节 {num}"
    if remainder:
        label = f"{label} {remainder}"
    return label


def strip_leading_title(content: str, title: str) -> str:
    """
    去掉正文开头可能存在的书名行，避免与 typeset_body 写入的书名重复。

    兼容「书名」「# 书名」两种写法，并跳过紧随其后的空行。
    """
    if not content or not title:
        return content
    lines = content.split('\n')
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        cand = lines[i].strip().lstrip('#').strip()
        if cand and cand == title.strip():
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
    return '\n'.join(lines[i:])


def split_chapters(content: str) -> list:
    """
    把正文切分为章节列表 [{'title': ..., 'content': ...}]，
    章节识别规则与阅读器保持一致（第N章/回/节、(12)、[12]、12.、Chapter N、章节 N）。

    兼容爬虫常见的 Markdown 风格标题：
    - `# 书名` / `# 书名`：仅作书名标记，不作为章节，且不写入正文；
    - `## 章节` / `### 章节`：视为章节标题，开始新章节。

    用于把整本原始内容送入 typeset_body 做统一重排。
    """
    chapters = []
    if not content:
        return chapters
    # 预处理：把粘连到上一行末尾的章节标记拆到新行，便于后续按行识别。
    # 仅当标记前有空白或右引号/右括号等「边界」时才拆，避免误拆正文里的「第3章」提及。
    content = re.sub(
        r'([\s”’」』）)】\]>])(第[零一二三四五六七八九十百千万两\d]+\s*[章节回篇部页])',
        r'\1\n\2', content)
    content = re.sub(
        r'([\s”’」』）)】\]>])(章节\s*\d+)',
        r'\1\n\2', content)
    lines = content.split('\n')
    current = {"title": "未命名章节", "content": ""}
    # Markdown 标题正则：二级及以上为章节，一级为书名（跳过）
    md_chapter_re = re.compile(r'^#{2,6}\s+(.+)$')
    md_title_re = re.compile(r'^#\s+(.+)$')
    for line in lines:
        stripped = line.strip()
        # —— Markdown 标题优先于传统规则处理 ——
        md_chap = md_chapter_re.match(stripped)
        if md_chap:
            if current["content"].strip():
                chapters.append(current.copy())
            current = {"title": _normalize_fullwidth(md_chap.group(1).strip()),
                       "content": ""}
            continue
        if md_title_re.match(stripped):
            # 一级标题是书名标记：跳过，不写入正文
            continue
        is_chapter = (
            # 第N章/回/节/篇/部/页（允许前面有引号、空格、括号等前缀，
            # 兼容「” 第6章」「（第3章」这类被粘连到上一行的标题）
            re.match(r'^[\s"\'”’」』「『（([【<]*第[零一二三四五六七八九十百千万两\d]+\s*[章节回篇部页]', stripped) is not None
            or stripped.startswith("章节")  # 已归一化的「章节 N」
            or stripped.lower().startswith("chapter")
            or re.match(r'^[（\(]\s*\d+\s*[）\)\]]', stripped) is not None   # (12) / （12） / [12]
            or re.match(r'^\d+\s*[\.、\)）]\s*\S', stripped) is not None      # 12. 描述 / 12、番外 / 12) 续集
            or re.match(r'^\d+\s*[\.、\)）]?$', stripped) is not None        # 纯 12 / 12. / 12)
        )
        if is_chapter:
            # 当前块若有内容则保留（避免丢失章节前的正文/序言），再开新章节
            if current["content"].strip():
                chapters.append(current.copy())
            current = {"title": stripped, "content": ""}
        else:
            current["content"] += line + "\n"
    if current["content"].strip():
        chapters.append(current)
    if not chapters:
        chapters = [{"title": "全文", "content": content}]
    return chapters


def typeset_body(title: str, chapters: list = None, single_content: str = None) -> str:
    """
    生成固定样式的书籍正文（不含元信息行）。

    格式：
        书名

        章节 1
            <缩进段落>

        章节 2
            ...

    参数：
        title: 书名
        chapters: 章节列表，每项为 {'title':..., 'content':...}
        single_content: 单章节/短篇的正文（与 chapters 二选一）
    """
    parts = []
    if title:
        parts.append(title.strip())
        parts.append("")

    if chapters:
        for i, ch in enumerate(chapters):
            raw_title = ch.get('title', '')
            # 无章节语义的引子/正文块（未命名章节 / 全文）直接作为正文排版，
            # 避免给书籍开头的书名/作者/章节范围说明等凭空生成「章节 1」标题
            if raw_title in ("未命名章节", "全文"):
                paras = reflow_paragraphs(ch.get('content', ''))
                parts.extend(paras)
                parts.append("")
                continue
            label = normalize_chapter_title(raw_title, i + 1)
            paras = reflow_paragraphs(ch.get('content', ''))
            parts.append(label)
            parts.append("")
            parts.extend(paras)
            parts.append("")  # 章节之间空行分隔
    elif single_content:
        paras = reflow_paragraphs(single_content)
        parts.extend(paras)
        parts.append("")

    # 合并并去掉尾部多余空行，最后补一个换行
    text = "\n".join(parts).rstrip()
    return text + "\n"


def build_body(title: str, novel_content: dict) -> str:
    """
    根据 novel_content 生成排版后的正文（写入文件前统一按内容自动切分章节）。

    规则：
    - spider 已正确分章（≥2 个带语义标题的章节）-> 直接排版；
    - 否则（整本塞进单章节 / 未分章）-> 对正文按内容自动切分后再排版；
      若切不出章节，则整本作为单章（正文）排版，与纯散文一致。

    这是落盘的唯一排版入口，save_to_file 与批量重排工具共用，保证行为一致。
    """
    novel_content = novel_content or {}
    chapters = novel_content.get('chapters') or []

    real_spider_chapters = [
        c for c in chapters
        if str(c.get('title', '')).strip() not in ('', '未命名章节', '全文')
    ]
    if len(real_spider_chapters) > 1:
        return typeset_body(title, chapters=chapters)

    # spider 未分章或仅单章：按正文内容自动切分
    if chapters:
        full_text = "\n".join(str(ch.get('content', '')) for ch in chapters)
    elif novel_content.get('total_content'):
        full_text = str(novel_content['total_content'])
    elif novel_content.get('content'):
        full_text = str(novel_content['content'])
    else:
        full_text = None

    if full_text:
        detected = split_chapters(full_text)
        if any(str(c.get('title', '')).strip() not in ('全文', '未命名章节')
               for c in detected):
            return typeset_body(title, chapters=detected)
        return typeset_body(title, single_content=full_text)

    return (title.strip() + "\n") if title else ""


def typeset_novel_content(
    title: str,
    chapters: list = None,
    single_content: str = None,
    author: str = None,
    source: str = None,
    status: str = None,
) -> str:
    """
    生成可直接写入文件的完整 .txt 内容（正文 + 可选元信息）。

    元信息放在正文之后，保持与阅读器元信息提取兼容（作者/来源/状态）。
    """
    body = typeset_body(title, chapters=chapters, single_content=single_content)

    meta_lines = []
    if author:
        meta_lines.append(f"作者: {author}")
    if source:
        meta_lines.append(f"来源: {source}")
    if status:
        meta_lines.append(f"状态: {status}")

    if meta_lines:
        return body.rstrip() + "\n\n" + "\n".join(meta_lines) + "\n"
    return body
