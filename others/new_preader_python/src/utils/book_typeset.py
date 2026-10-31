"""
书籍固定排版工具（仅针对 .txt 书籍）。

目标：把爬虫抓取的、章节标题五花八门（第N章 / 第一章 / 12 / (12) / [12] /
Chapter N …）的内容，重排为便于阅读器展示与章节识别的固定样式。

重要约定：章节标题**尽量保留原文已有的章节号**，不再额外编造「章节 N」字样。
正文里一般已经带有章节号，程序若识别不到真实编号就去套一个顺序号（章节 1 /
章节 2 …），反而会覆盖原文编号、造成重复与混乱。因此：

    书名

    第 1 章 初见            （原文是「第一章 初见」则原样保留；旧版「章节 1」会还原为「第1章」）
        段落一内容……

        段落二内容……

    第 2 章 相遇
        ……

设计要点：
- 章节标题保留原文（清理首尾空白 / Markdown 符号 / 包裹括号即可）；旧版归一化的
  「章节 N」会被还原为「第N章」，不再出现「章节」二字；
- 正文每段前缩进 4 个空格；
- 章节之间用空行分隔（不再使用任何人工分隔符）；
- 段落归一化：以空行为段落边界，单行内的软换行合并为一段（重排），
  对完全没有换行的长文本做兜底句末切分。
"""

import re

# ─────────────────────────────────────────────────────────────
# 通用章节号识别
#
# 爬取回来的章节名千奇百怪：阿拉伯数字（123）、中文数字（一二三 / 三十一）、
# 罗马数字（I/II/III/XII）、英文数字词（One/Two/Twenty One）、中英文混合，
# 还常被各种符号包裹（（）()【】[]「」『』<>"" 等），前面可能带「第 / Chapter /
# 卷 / 篇 …」前缀，后面可能带「章 / 回 / 节 …」单位。
#
# 下面用一套统一的子模式覆盖上述所有组合，做到「见号识号」，而不是碰到认不出的
# 就退化为顺序号（章节 1 / 章节 2 …），从而避免把文章里已有的章节号覆盖掉。
# ─────────────────────────────────────────────────────────────

# 简体中文数字（含 〇 / 两）
_CN_NUM = {
    '零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
}

# 罗马数字
_ROMAN_MAP = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}

# 英文数字词 -> 数值
_EN_NUM = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
    'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12,
    'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
    'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
    'hundred': 100, 'thousand': 1000, 'million': 1000000,
}
_EN_WORD = '|'.join(sorted(_EN_NUM.keys(), key=len, reverse=True))
_EN_WORD_MULTI = (
    r'(?:' + _EN_WORD +
    r'(?:\s*(?:-|and)?\s*' + _EN_WORD + r')*)'
)

# 数字子模式（非捕获组；同名组不能在同一正则里重复，故不命名，提取时另行捕获）
_ARABIC = r'[0-9０-９]{1,6}'                 # 半角 + 全角数字（全角 ０１２ 常见于部分爬虫书）
_CN = r'[零〇一二两三四五六七八九十百千万亿]{1,12}'
_ROMAN = r'[IVXLCDM]{1,8}'
# 仅含 1 个罗马字母（I/V/X/L/C/D/M）极易与正文里的英文字母/单词混淆（如 "M"、 "Children"），
# 章节罗马数字几乎都是两位以上（II/III/IV/XII…），故裸罗马数字要求至少 2 位。
_ROMAN2 = r'[IVXLCDM]{2,}'
# 数字整体：阿拉伯 / 中文 / 罗马 / 英文词；罗马与英文加字母边界，避免「C」被当作
# 罗马数字从 Chapter 里揪出来，或正文里的 one/ten 被误判。
_NUM = (
    r'(?:' + _ARABIC + r'|' + _CN
    + r'|(?<![A-Za-z])' + _ROMAN + r'(?![A-Za-z])'
    + r'|(?<![A-Za-z])' + _EN_WORD_MULTI + r'(?![A-Za-z])'
    + r')'
)
# 仅用于从已匹配的章节标记里取出「数字部分」
_NUM_RE = re.compile(_NUM, re.IGNORECASE)

# 包裹符号（开 / 闭）
_OPEN = r'[（\(\[【「『<]'
_CLOSE = r'[）\)\]】」』>]'
# 章节单位：明确用于标识「章节」的后缀。
# 含：章 / 回 / 节 / 话 / 幕 / 集 / 页（其中「页」在很多书里是分页标记，等价于章节分隔）；
# 不含：卷（卷号非章节）、篇 / 部（正文常出现「一篇小说 / 一部作品」）、部分（「第N部分」是分卷）。
_UNIT_CH = r'[章回节话幕集页]'
# 真正的「分章」单位（用于 extract_chapter_number 在「卷+章」里挑出分章号而非卷号）
_UNIT_CH_SET = set('章回节话幕集页')
# 「第X…」前缀可用的单位：在第 前缀下，卷 / 篇 / 部 也作为分章（第3卷/第5篇/第2部），
# 但仍不含「部分」；不带 第 前缀的裸数字+单位仍用 _UNIT_CH，避免「一篇小说」误判。
_UNIT_VOL = r'[章回节卷篇部话幕集页]'

# 前缀分两类：
#  - 第：必须后接「章节单位」，否则「第N部分 / 第N页以外」不作章节；
#  - 其它（Chapter / Episode / No / # / 章节 / 序 …）：可后接数字，单位可选。
_PREFIX_CH = r'第\s*'
_PREFIX_OTHER = (r'(?:章节\s*|[Cc]hapter\s*|[Cc]hap\.?\s*|[Ee]p(?:isode)?\.?\s*|'
                 r'[Ss]ection\s*|[Vv]ol(?:ume)?\.?\s*|[Nn]o\.?\s*|#\s*|序\s*)')
# 「第X卷第Y章」/「第X卷的第Y章」：卷+章连写（卷号非章节，真正分章的是后面的第Y章）。
# 末位单位用 _UNIT_CH（不含卷），避免把「第X卷第Y卷」之类误收；中间「的」可有可无。
_VOL_CH = (_PREFIX_CH + _NUM + _UNIT_VOL + r'\s*的?\s*' + _PREFIX_CH + _NUM + _UNIT_CH)

# 包裹数字分两类：
#  - 中文数字包裹（（三十一））：几乎必为章节，始终视为章节标记；
#  - 其它数字包裹（（12）/（XII）/（Three））：需后接「章节单位」或标题文字，
#    避免正文里的脚注 / 序号「（1）」被误判为章节。
_WRAP_CN = _OPEN + _CN + _CLOSE + _UNIT_CH + r'?'
_WRAP_OTHER_HEAD = (_OPEN + r'(?:' + _ARABIC + r'|' + _ROMAN + r'|' + _EN_WORD_MULTI + r')' + _CLOSE
                   + r'(?:' + _UNIT_CH + r'|\s*\S.*)')     # 需后接单位或标题文字
_WRAP_OTHER_LEAD = _OPEN + r'(?:' + _ARABIC + r'|' + _ROMAN + r'|' + _EN_WORD_MULTI + r')' + _CLOSE

# 行级章节标题「核心」：标题行以章节号开头。
# HEAD 版（用于判定是否为章节标题，允许包裹其它数字后接标题文字）；
# LEAD 版（用于从已确认标题里取出开头的章节号标记，不做贪心后接）。
_HEAD_CORE = (
    _WRAP_CN
    + r'|' + _WRAP_OTHER_HEAD
    + r'|' + _VOL_CH                                             # 第X卷第Y章 / 第X卷的第Y章
    + r'|' + _PREFIX_CH + _NUM + _UNIT_VOL                       # 第X章/回/节/页…（必须带章节单位）
    + r'|' + _PREFIX_OTHER + _NUM + _UNIT_CH + r'?'
    + r'|(?:' + _ARABIC + r'|' + _CN + r')' + _UNIT_CH          # 12章 / 三章 / III章
    + r'|(?:' + _ARABIC + r'|' + _CN + r')[\.）\)]'             # 12. / 12) / 12）（去掉枚举逗号、，避免「三、四十岁」误判）
    + r'|(?:' + _ARABIC + r'|' + _CN + r'|' + _ROMAN2 + r')(?:[\s　]|$)'   # 二十 终章 / 12 / XII（后接空白或行尾；罗马需≥2位）
    + r'|' + _ROMAN2 + r'(?:[\.、\)）])?'                       # 罗马数字 XII / III.
)
_LEAD_CORE = (
    _WRAP_CN
    + r'|' + _WRAP_OTHER_LEAD
    + r'|' + _VOL_CH
    + r'|' + _PREFIX_CH + _NUM + _UNIT_VOL
    + r'|' + _PREFIX_OTHER + _NUM + _UNIT_CH + r'?'
    + r'|(?:' + _ARABIC + r'|' + _CN + r')' + _UNIT_CH
    + r'|(?:' + _ARABIC + r'|' + _CN + r')[\.）\)]'
    + r'|(?:' + _ARABIC + r'|' + _CN + r'|' + _ROMAN2 + r')(?:[\s　]|$)'
    + r'|' + _ROMAN2 + r'(?:[\.、\)）])?'
)
# 判定整行是否为章节标题
_CHAPTER_HEAD_RE = re.compile(r'^(?:' + _HEAD_CORE + r')(.*)$', re.IGNORECASE)
# 从章节标题里截取开头的章节号标记（供分离标题与正文用）
_CHAPTER_HEAD_LEAD_RE = re.compile(r'^(?:' + _LEAD_CORE + r')', re.IGNORECASE)

# 内联切分：在正文中找出「章节号标记」的位置（不要求位于行首），用于把粘连在段落
# 里的章节标记拆出来。阿拉伯 / 中文数字要求带 单位 / 分隔符 / 包裹 / 前缀 之一；
# 「第X卷」是卷号而非章节，不作为内联切分点（避免把「第3卷第5章」误拆）。
_INLINE_SPLIT_RE = re.compile(
    _OPEN + _NUM + _CLOSE + _UNIT_CH + r'?'
    + r'|' + _VOL_CH                                        # 第X卷第Y章 / 第X卷的第Y章
    + r'|' + _PREFIX_CH + _NUM + _UNIT_VOL                   # 第X章/回/节/页…（不含卷/篇/部/部分）
    + r'|' + _PREFIX_OTHER + _NUM                           # Chapter/EP/No/#… + 数字
    + r'|(?:' + _ARABIC + r'|' + _CN + r')' + _UNIT_CH      # 12章 / 三章 / III章
    + r'|(?:' + _ARABIC + r'|' + _CN + r')[\.）\)]'         # 12. / 12) （不含枚举逗号、）
    + r'|(?:' + _ARABIC + r'|' + _CN + r'|' + _ROMAN2 + r'|' + _EN_WORD_MULTI + r')' + _UNIT_CH
    + r'|' + _ROMAN2 + r'(?:[\.、\)）])?',
    re.IGNORECASE,
)

# 提取章节号时用：在任意字符串里找到第一个「带语境」的章节号标记并捕获其数字部分。
# 数字必须带 包裹 / 前缀 / 单位 / 分隔符 之一，避免「一段」「详见第5章的说明」被误抓。
_CHAPTER_NUMBER_RE = re.compile(
    _OPEN + _NUM + _CLOSE                                   # 包裹：（三十一） / (12)
    + r'|' + _PREFIX_CH + _NUM + _UNIT_VOL                   # 第5章 / 第一章
    + r'|' + _PREFIX_OTHER + _NUM + _UNIT_CH + r'?'         # Chapter 3 / 章节 7
    + r'|' + _NUM + _UNIT_CH                               # 单位：12章 / 三章 / III章
    + r'|' + _NUM + r'[\.）\)]',                           # 分隔符：12. / 12)
    re.IGNORECASE,
)

# 内联切分前允许作为「断点」的前导字符（句末标点 / 引号 / 括号 / 空白 / 行首）
_BREAK_BEFORE = set('。！？!?…"，’」』）)】【>—')
# 中文数字连写常表示约数/范围（两三回 = 两三次），并非章节号，识别时排除。
_RANGE_PAIRS = ('一两', '三两', '二三', '三四', '四五', '五六', '六七', '七八', '八九')

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


def roman_to_int(s: str):
    """罗马数字 -> 整数；无法识别返回 None。"""
    s = (s or '').strip().upper()
    if not s or any(c not in _ROMAN_MAP for c in s):
        return None
    total, prev = 0, 0
    for ch in reversed(s):
        v = _ROMAN_MAP[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total or None


def english_number_to_int(s: str):
    """英文数字词（支持 twenty one / one hundred twenty three 等）-> 整数。"""
    words = re.split(r'[\s\-]+', (s or '').strip().lower())
    words = [w for w in words if w]
    if not words or any(w not in _EN_NUM for w in words):
        return None
    total, current = 0, 0
    for w in words:
        v = _EN_NUM[w]
        if v in (100, 1000, 1000000):
            total += (current or 1) * v
            current = 0
        else:
            current += v
    total += current
    return total or None


def cn_to_int(text: str):
    """把中文数字（支持 零~亿 量级）转换为整数；纯阿拉伯数字直接转。"""
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
        elif ch == '亿':
            num = (num + cur) * 100000000
            cur = 0
        else:
            # 遇到无法识别的字符（如「第」「章」等）直接忽略
            continue
    num += cur
    return num if num > 0 else None


def _parse_number(token: str):
    """把捕获到的「数字部分」统一转为整数，支持四种写法。"""
    if not token:
        return None
    token = _normalize_fullwidth(token).strip()
    if token.isdigit():
        return int(token)
    # 中文数字：全部字符都在中文数字集合内
    if all(c in _CN_NUM or c in '十百千万亿' for c in token):
        return cn_to_int(token)
    # 罗马数字：全部为大写罗马字符
    if token.upper().isalpha() and all(c in _ROMAN_MAP for c in token.upper()):
        return roman_to_int(token)
    # 英文数字词
    if any(c.isalpha() for c in token):
        return english_number_to_int(token)
    return None


def is_chapter_heading(stripped_line: str) -> bool:
    """判断一行（已 strip）是否为章节标题。"""
    if not stripped_line:
        return False
    # 中文数字连写常表示约数/范围（两三回 = 两三次、三两回），并非章节号，排除。
    if any(pair in stripped_line[:12] for pair in _RANGE_PAIRS):
        return False
    return _CHAPTER_HEAD_RE.match(stripped_line) is not None


def extract_chapter_number(raw_title: str):
    """从章节标题中提取章节号（整数），无法提取时返回 None。

    对「第X卷第Y章」这类卷章连写，优先取以分章单位（章/回/节…）结尾的那个
    编号（即分章号 Y），而非卷号 X，避免阅读器按卷号排序导致章节错乱。
    """
    if not raw_title:
        return None
    matches = list(_CHAPTER_NUMBER_RE.finditer(raw_title))
    if not matches:
        return None
    best = None
    for m in matches:
        if m.group(0)[-1] in _UNIT_CH_SET:      # 以真正的分章单位结尾
            best = m
    if best is None:
        best = matches[-1]                       # 否则取最后一个编号
    inner = _NUM_RE.search(best.group(0))
    if not inner:
        return None
    value = _parse_number(inner.group(0))
    return (value, best) if value is not None else None


def normalize_chapter_title(raw_title: str, position_index: int) -> str:
    """
    处理章节标题：尽量保留原文已有的章节号，不再额外编造「章节 N」字样。

    规则：
    1. 若标题已是本程序旧版归一化的「章节 N」格式，则还原为更自然的「第N章」
       （去掉「章节」二字）并保留其后的描述——既清理了多余的「章节」前缀，
       又不丢失真实编号；
    2. 若标题本身已包含可识别的章节号（第N章 / 第一章 / 第一篇 / (12) /
       [12] / Chapter N / 纯数字 …），直接保留原文（仅清理首尾空白、Markdown
       标题符号与包裹括号），不改写为「章节 N」；
    3. 若标题完全识别不出任何章节语义（如「序」「番外」或纯描述性文字），
       同样保留原文，不再强行套用「章节 N」前缀，避免画蛇添足、重复编号。

    position_index 仅保留参数兼容性，不再用于生成章节号。
    """
    if not raw_title:
        return raw_title
    cleaned = raw_title.strip()
    # 去掉 Markdown 标题符号（# 书名 / ## 章节）
    cleaned = re.sub(r'^#{1,6}\s*', '', cleaned).strip()
    # 去掉包裹整行的成对括号/方括号，避免「（第十二章）」这类被阅读器忽略
    cleaned = re.sub(r'^[（\(\[【]\s*(.+?)\s*[）\)\]】]$', r'\1', cleaned).strip()
    # 折叠多余空白
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if not cleaned:
        return cleaned

    # 规则 1：旧版「章节 N」归一化格式 -> 还原为「第N章 [描述]」
    m = re.match(
        r'^章节\s*(\d+|[零〇一二两三四五六七八九十百千]+)\s*(.*)$', cleaned)
    if m:
        num = cn_to_int(m.group(1))
        rest = m.group(2).strip()
        if num is not None:
            return f"第{num}章 {rest}".strip() if rest else f"第{num}章"

    # 规则 2/3：保留原文，不添加任何「章节 N」前缀
    return cleaned


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

    # 预处理：很多爬虫书籍把章节标记「粘连」在段落末尾（甚至整本书只有一行），
    # 例如本测试书《…》整本仅 12 个换行却有 31 个「（三十一）见面礼」式标记。
    # 这里在「章节号标记」前插入换行，使其成为独立的一行，便于后续按行识别。
    # 仅当标记前是「边界」（行首 / 空白 / 句末标点 / 引号 / 括号）时才拆，
    # 避免误拆正文里对章节号的提及。
    content = _insert_chapter_breaks(content)

    lines = content.split('\n')
    current = {"title": "未命名章节", "content": ""}
    # Markdown 标题正则：二级及以上为章节候选（再按层级/是否含章节号判定），一级为书名（跳过）
    md_chapter_re = re.compile(r'^(#{2,6})\s+(.+)$')
    md_title_re = re.compile(r'^#\s+(.+)$')
    for line in lines:
        stripped = line.strip()
        # —— Markdown 标题优先于传统规则处理 ——
        md_chap = md_chapter_re.match(stripped)
        md_title = md_title_re.match(stripped)
        if md_chap:
            level = len(md_chap.group(1))          # # 的个数（h2 / h3 …）
            heading_text = _normalize_fullwidth(md_chap.group(2).strip())
            # 仅当层级较深（h3+）或标题本身像个章节（含章节号）时才视为章节；
            # 否则（如「## 书名（作者）」这类重复书名）当作书名标记跳过，避免误吞正文。
            if level >= 3 or is_chapter_heading(heading_text):
                if current["content"].strip():
                    chapters.append(current.copy())
                current = {"title": heading_text, "content": ""}
                continue
            else:
                # 非章节的 Markdown 标题：当作书名/卷名，不写入正文
                continue
        if md_title:
            # 一级标题是书名标记：跳过，不写入正文
            continue
        if is_chapter_heading(stripped):
            # 章节号标记（仅取开头的章节号，保留文章原有编号，不编造「章节 N」）
            lm = _CHAPTER_HEAD_LEAD_RE.match(stripped)
            if lm:
                marker = lm.group(0)
                rest = stripped[lm.end():]
            else:
                marker, rest = stripped, ''
            # 标题行若在章节号之后还拖着大段正文（多见于整本无换行的爬虫书），
            # 则只把章节号作为标题、其余内容并入本章正文；否则保留完整标题（含章节名），
            # 避免把整段正文误吞进标题里导致正文丢失。
            if rest.strip() and (len(rest.strip()) > 25 or any(p in rest for p in _SENT_END)):
                title = marker
                first_body = rest.strip()
            else:
                title = stripped
                first_body = ''
            chapters.append(current)
            current = {"title": title,
                       "content": (first_body + "\n") if first_body else ""}
        else:
            current["content"] += line + "\n"
    chapters.append(current)
    # 去掉「未命名章节 / 全文」且正文为空的占位章节（正文最前面那段无内容的占位）
    chapters = [c for c in chapters
                if not (c["title"] in ("未命名章节", "全文") and not c["content"].strip())]
    if not chapters:
        chapters = [{"title": "全文", "content": content}]
    return chapters


def _insert_chapter_breaks(content: str) -> str:
    """
    在内联的章节号标记前插入换行，把粘连在段落里的章节标记拆成独立行。

    - 包裹型「（数字）/(数字)/【数字】」：正文里几乎只会出现为章节标记，故无条件拆；
    - 其它形式（第X章 / 12. / Chapter …）：仅当标记前是「边界」（行首 / 空白 /
      句末标点 / 引号 / 括号）时才拆，且卷号（第X卷）不作为切分点。
    """
    if not content:
        return content
    open_chars = set('（([【「『<')
    close_chars = set('）)]】」』>')
    out = []
    last = 0
    for m in _INLINE_SPLIT_RE.finditer(content):
        token = m.group(0)
        if any(pair in token for pair in _RANGE_PAIRS):
            continue
        p = m.start()
        q = m.end()
        before = content[p - 1] if p > 0 else ''
        # 包裹型（内容仅数字）无条件拆；其余需前导为边界（空白/句末标点/引号/括号）
        wrapped = token and token[0] in open_chars and token[-1] in close_chars
        # 中文数字包裹（（三十一））：几乎只作章节标记，且其后紧跟标题/正文需断开
        inner = token[1:-1] if wrapped else ''
        cn_wrapped = wrapped and bool(inner) and any(
            ch in _CN_NUM or ch in '十百千万亿' for ch in inner)
        do_split = p > 0 and (wrapped or before in _BREAK_BEFORE or before.isspace())
        out.append(content[last:p])   # 始终保存上一个拆分点到本标记之间的正文（避免丢字）
        if do_split:
            out.append('\n')
        out.append(content[p:q])      # 章节号标记本身
        nxt = content[q] if q < len(content) else ''
        # 中文数字包裹（（三十一））：正文里几乎只作章节标记，且其后常紧跟标题/正文，
        # 断开让其独占一行、其后内容作为本章正文开头，避免正文被吞进标题里。
        # 阿拉伯/罗马/英文数字包裹（（12）/（XII））可能是脚注/序号，不在此断开。
        if cn_wrapped and nxt and not nxt.isspace():
            out.append('\n')
        last = q
    out.append(content[last:])            # 末尾剩余正文
    return ''.join(out)


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
