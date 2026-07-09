"""
智能标题生成工具模块

提供书籍合并时的智能标题生成功能，支持：
- 多种数字格式：阿拉伯数字、中文小写/大写、罗马数字
- 章节标记识别：序、卷、部、册、集、前传/后传、外传、番外
- 智能范围合并：自动识别章节号范围并合并
"""

import os
import re
from collections import Counter
from typing import Any, Optional, List, Tuple


class SmartTitleUtils:
    """智能标题工具类 - 提供静态方法供各对话框复用"""

    # ─── 数字转换方法 ──────────────────────────────────────

    @staticmethod
    def chinese_num_to_int(chinese_num: str) -> Optional[int]:
        """
        将中文数字转换为整数

        支持：
        - 中文小写: 零一二三四五六七八九十百千万
        - 中文大写: 〇壹贰叁肆伍陆柒捌玖拾佰仟萬
        - 复合: 十二, 一百二十三, 拾贰, 仟贰佰等
        """
        chinese_lower = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '百': 100, '千': 1000, '万': 10000
        }
        chinese_upper = {
            '〇': 0, '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
            '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10,
            '佰': 100, '仟': 1000, '萬': 10000
        }

        merged_dict = {**chinese_lower, **chinese_upper}

        result = 0
        temp = 0
        i = 0
        chars = list(chinese_num)

        while i < len(chars):
            char = chars[i]
            if char in merged_dict:
                value = merged_dict[char]
                if value == 10 and temp == 0:
                    # "十" 在开头表示 10-19
                    temp = 10
                elif value in [10, 100, 1000]:
                    temp = (temp or 1) * value
                elif value == 10000:
                    result += temp * 10000
                    temp = 0
                else:  # 数字 0-9
                    temp = temp + value if temp > 9 or temp == 0 else temp * 10 + value
                i += 1
            else:
                return None

        return result + temp

    @staticmethod
    def roman_to_int(roman: str) -> Optional[int]:
        """
        将罗马数字转换为整数

        支持：
        - 标准罗马数字: I, II, III, IV, V, X, XII, XLIX 等
        - 大小写均可: i, ii, iii, iv 等
        """
        roman_values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000,
            'i': 1, 'v': 5, 'x': 10, 'l': 50,
            'c': 100, 'd': 500, 'm': 1000
        }

        total = 0
        prev_value = 0
        for char in reversed(roman.upper()):
            if char not in roman_values:
                return None
            value = roman_values[char]
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        return total

    @staticmethod
    def extract_number_from_string(num_str: str) -> Optional[int]:
        """
        从字符串中提取数字（自动检测格式）

        支持格式（按优先级）：
        1. 阿拉伯数字: 123, 456
        2. 全角数字: ０１２, １００
        3. 中文小写: 一, 二, 十二, 一百二十三
        4. 中文大写: 壹, 贰, 叁, 拾贰
        5. 罗马数字: I, II, III, XII, XLIX
        """
        num_str = num_str.strip()
        if not num_str:
            return None

        # 尝试阿拉伯数字
        try:
            return int(num_str)
        except ValueError:
            pass

        # 尝试全角数字：转半角后再解析
        fullwidth_map = str.maketrans('０１２３４５６７８９', '0123456789')
        converted = num_str.translate(fullwidth_map)
        if converted != num_str and converted.isdigit():
            try:
                return int(converted)
            except ValueError:
                pass

        # 尝试中文数字（大小写）
        chinese_result = SmartTitleUtils.chinese_num_to_int(num_str)
        if chinese_result is not None:
            return chinese_result

        # 尝试罗马数字
        roman_result = SmartTitleUtils.roman_to_int(num_str)
        if roman_result is not None:
            return roman_result

        return None

    # ─── 章节信息提取 ──────────────────────────────────────

    @staticmethod
    def _get_regex_patterns():
        """获取正则表达式模式组件（内部使用）"""
        arabic_num = r'\d+'  # 阿拉伯数字: 123
        fullwidth_num = r'[０-９]+'  # 全角数字: ０１２３
        chinese_lower_num = r'[零一二三四五六七八九十百千万]+'
        chinese_upper_num = r'[〇壹贰叁肆伍陆柒捌玖拾佰仟萬]+'
        chinese_num = f'(?:{chinese_lower_num}|{chinese_upper_num})'  # 中文数字
        roman_num = (
            r'(?:X{0,3}(?:IX|IV|V?I{0,3})|'
            r'L?X{0,3}(?:IX|IV|V?I{0,3})|'
            r'C(?:M|CD|D?C{0,3})|(?:CM|CD)?D?C{0,3})'
            r'(?:M{0,3})?'
        )  # 罗马数字
        any_num = f'(?:{arabic_num}|{fullwidth_num}|{chinese_num}|{roman_num})'  # 任意数字格式

        chapter_markers = r'(?:序|前传|后传|外传|番外)'
        volume_markers = r'(?:第' + any_num + r'[卷部册集]|[卷部册集])'
        all_markers = f'(?:{chapter_markers}|{volume_markers})'

        return any_num, all_markers

    # 数字后缀字符（数字后的 上/下/中 等标记）
    _NUM_SUFFIX_CHARS = set('上下中前后内外终完正续附增补篇回章集卷册部')

    @staticmethod
    def _parse_numeric(s: str):
        """解析数字字符串为整数或浮点（支持阿拉伯、全角、小数）"""
        if not s:
            return None
        fullwidth_map = str.maketrans('０１２３４５６７８９', '0123456789')
        s2 = s.translate(fullwidth_map).replace('．', '.')
        try:
            if '.' in s2:
                return float(s2)
            return int(s2)
        except ValueError:
            # 退化处理 7.5.2 这类多余小数点的编号：取首个可解析前缀（如 7.5）
            m = re.match(r'\d+(?:\.\d+)?', s2)
            if m:
                try:
                    return float(m.group(0))
                except ValueError:
                    return None
            return None

    @staticmethod
    def _parse_inner_chapter(inner: str):
        """
        解析括号内的内容。

        Returns:
            (start, end, marker, start_suffix, end_suffix, is_text_marker) 或 None
            - marker: 数字前的文字标记（如 序、重置版、第二卷第三章）
            - start_suffix/end_suffix: 数字后的后缀（上/下/中）
            - is_text_marker: True 表示纯标记模式（上/下/中篇等，无数字）
        """
        inner = inner.strip()
        if not inner:
            return None

        # 1. 纯标记模式：整串都是标记字符（上/下/中篇/完结篇）
        if inner and all(c in SmartTitleUtils._NUM_SUFFIX_CHARS for c in inner):
            return (0, 0, inner, '', '', True)

        # 2. 阿拉伯/全角数字（含小数）
        digit_re = r'(\d+(?:\.\d+|．\d+)*|[０-９]+(?:\.[０-９]+|．[０-９]+)*)'
        digits = list(re.finditer(digit_re, inner))
        if digits:
            first = digits[0]
            last = digits[-1]
            marker = inner[:first.start()].strip()
            num_strs = [d.group(0) for d in digits]
            nums = [SmartTitleUtils._parse_numeric(s) for s in num_strs]
            nums = [n if n is not None else 0 for n in nums]
            if len(num_strs) >= 2:
                end_suffix = inner[last.end():].strip()
                end_suffix = ''.join(c for c in end_suffix if c in SmartTitleUtils._NUM_SUFFIX_CHARS)
                start_suffix = inner[first.end():digits[1].start()].strip() if len(digits) >= 2 else ''
                start_suffix = ''.join(c for c in start_suffix if c in SmartTitleUtils._NUM_SUFFIX_CHARS)
                res = (nums[0], nums[-1], marker, start_suffix, end_suffix, False)
            else:
                end_suffix = inner[first.end():].strip()
                end_suffix = ''.join(c for c in end_suffix if c in SmartTitleUtils._NUM_SUFFIX_CHARS)
                res = (nums[0], nums[0], marker, '', end_suffix, False)
            # 清理 "第X章/回/节" 这类纯章节框定（仅保留数字）
            if res[2] == '第' and res[4] in ('章', '回', '节', '集', '篇', '部', '册'):
                res = (res[0], res[1], '', res[3], '', res[5])
            return res

        # 3. 中文数字（第六章、十二 等）
        cn_re = r'([零一二三四五六七八九十百千万〇壹贰叁肆伍陆柒捌玖拾佰仟萬]+)'
        cn = list(re.finditer(cn_re, inner))
        if cn:
            first = cn[0]
            last = cn[-1]
            marker = inner[:first.start()].strip()
            nums = [SmartTitleUtils.chinese_num_to_int(c.group(0)) for c in cn]
            nums = [n if n is not None else 0 for n in nums]
            end_suffix = inner[last.end():].strip()
            end_suffix = ''.join(c for c in end_suffix if c in SmartTitleUtils._NUM_SUFFIX_CHARS)
            if len(cn) >= 2:
                start_suffix = inner[first.end():cn[1].start()].strip()
                start_suffix = ''.join(c for c in start_suffix if c in SmartTitleUtils._NUM_SUFFIX_CHARS)
                res = (nums[0], nums[-1], marker, start_suffix, end_suffix, False)
            else:
                res = (nums[0], nums[0], marker, '', end_suffix, False)
            if res[2] == '第' and res[4] in ('章', '回', '节', '集', '篇', '部', '册'):
                res = (res[0], res[1], '', res[3], '', res[5])
            return res

        # 4. 纯罗马数字
        rm = list(re.finditer(r'([IVXLCDMivxlcdm]+)', inner))
        if rm and all(c in 'IVXLCDMivxlcdm' for c in inner.replace(' ', '')):
            nums = [SmartTitleUtils.roman_to_int(c.group(0)) for c in rm]
            nums = [n if n is not None else 0 for n in nums]
            if len(nums) >= 2:
                return (nums[0], nums[-1], '', '', '', False)
            return (nums[0], nums[0], '', '', '', False)

        return None

    @staticmethod
    def extract_chapter_info(title: str) -> Optional[Tuple]:
        """
        从标题中提取章节信息。

        Returns 9 元组 或 None:
            (start, end, prefix, suffix, chapter_prefix, has_parens, end_suffix, start_suffix, inner_text)
            - start/end: 数字（整数或浮点）；纯标记模式时为 -1
            - prefix: 书名前缀（不含章节信息）
            - suffix: 后缀（作者/补充信息）
            - chapter_prefix: 章节文字标记（如"序"、"重置版"）
            - has_parens: 是否括号包裹
            - end_suffix/start_suffix: 数字后/前的后缀（上/下/中）
            - inner_text: 括号内原文（用于小数合并）
        """
        if not title or not title.strip():
            return None
        title = title.strip()

        # ── 1. 有括号格式 ──
        # 支持全部常见括号：() （） [] 【】 《》 「」 『』
        # 【】《》「」『』 视为"包裹型书名括号"，（）[] 视为"内容括号"。
        # 章节信息只从"内容括号"或"内部含明确数字范围"的包裹括号中提取，
        # 避免把 【2012年9月21日枪挑日本女孩】 这类书名/日期误判为章节。
        OPEN_WRAP = '【《「『'
        CLOSE_WRAP = '】》」』'
        bracket_re = r'[\(（\[【《「『]([^\(\)（）\[\]【】》《「」『]*)[\)）\]】》」』]'
        bracket_matches = list(re.finditer(bracket_re, title))
        if bracket_matches:
            def _bracket_is_chapter(inner: str, is_wrap: bool) -> bool:
                # 任意可解析数字（阿拉伯/全角/中文/罗马）或纯标记（上/下/章…）即视为潜在章节
                any_digit = re.search(
                    r'[0-9０-９零一二三四五六七八九十百千万〇壹贰叁肆伍陆柒捌玖拾佰仟萬'
                    r'IVXLCDMivxlcdm]', inner)
                is_pure_marker = bool(inner) and all(
                    c in SmartTitleUtils._NUM_SUFFIX_CHARS for c in inner)
                if not any_digit and not is_pure_marker:
                    return False
                if is_wrap:
                    # 包裹型书名括号：纯标记直接接受；含数字时须为"明确范围/小数"，
                    # 且去掉数字/分隔符/章节标记后不得残留书名中文字
                    # （排除 【书名1-5】、【2012年9月21日…】 等）。
                    if not is_pure_marker:
                        if not re.search(r'[0-9０-９][\d.０-９.]*\s*[-–—~－]\s*[0-9０-９]', inner) \
                                and not re.search(r'[0-9０-９]+\.[0-9０-９]+', inner):
                            leftover = re.sub(
                                r'[0-9０-９.\-–—~－\s第序卷部册章回集上下中前后内外终完]', '', inner)
                            if re.search(r'[\u4e00-\u9fff]', leftover):
                                return False
                    return True
                return True

            cand = None
            for bm in bracket_matches:
                g = bm.group(1)
                is_wrap = bm.group(0)[0] in OPEN_WRAP
                if _bracket_is_chapter(g, is_wrap):
                    cand = bm
                    break
            if cand is not None:
                bracket_match = cand
                inner_raw = bracket_match.group(1)
                # 以 +/＋ 分段，取"含数字"的片段作为章节范围：
                # - 避免 "1-209章+番外" 把番外当范围末端；
                # - "前传+0-9" 应选 0-9 而非前置标签。
                # 保留首尾空白，供后续（ 1-4 ）样式空格还原使用。
                segs = re.split(r'[+＋]', inner_raw)
                inner = next((s for s in segs if re.search(r'[0-9０-９]', s)), segs[0])
                prefix = title[:bracket_match.start()].rstrip()
                suffix = title[bracket_match.end():].lstrip()
                parsed = SmartTitleUtils._parse_inner_chapter(inner.strip())
                if parsed is not None:
                    start, end, marker, start_suffix, end_suffix, is_text_marker = parsed
                    if is_text_marker:
                        # 用 -1 标记纯标记模式（与数字 0 区分）
                        return (-1, -1, prefix, suffix, marker, True, '', '', inner)
                    return (start, end, prefix, suffix, marker, True, end_suffix, start_suffix, inner)
            # 无章节括号时，交给下面的无括号分支处理

        # ── 2. 无括号格式（如 书名 1-20 / 书名1~8 / 【书名】１-１４）──
        # 锚点：中文、闭合包裹符、空白，或前缀连字符（-1-8 形式）；
        # 数字支持半角/全角；分隔符支持 - – — ~ －。
        num_re = r'[0-9０-９]+(?:\.[0-9０-９]+|．[0-9０-９]+)*'
        # 使用反向预查，使锚点字符不被"吃掉"，从而保留完整前缀（如 【安全词】1-10 的 】）。
        # 锚点：中文、各闭合包裹符（】」』》）、内容括号闭合（）)]）、空白，
        # 以及前缀连字符/波浪号/破折号（- － ~ ～ — –，兼容 "X——1-8"、"X~1-6" 等）。
        anchor = r'(?<=[\u4e00-\u9fff】」』》\]）)\s\-－~～—–])'
        for pat in (
            anchor + r'\s*(' + num_re + r')\s*[-–—~－]\s*(' + num_re + r')',
            anchor + r'\s*(' + num_re + r')',
        ):
            m = re.search(pat, title)
            if m:
                # 仅取首个 "数字-数字" 片段（忽略后续 +番外 等附加章节）
                raw = m.group(0)
                rng = re.split(r'[+＋]', raw, maxsplit=1)[0]
                rm = re.search(r'(' + num_re + r')(?:\s*[-–—~－]\s*(' + num_re + r'))?', rng)
                if not rm:
                    continue
                prefix = title[:m.start()].rstrip()
                suffix = title[m.end():].lstrip()
                if rm.group(2):
                    s = SmartTitleUtils._parse_numeric(rm.group(1))
                    e = SmartTitleUtils._parse_numeric(rm.group(2))
                    return (s, e, prefix, suffix, '', False, '', '', f"{rm.group(1)}-{rm.group(2)}")
                else:
                    # 单数字：避免把 2012年9月21日 中的"年9月/月21日"误判为章节
                    after = title[m.end():m.end() + 1]
                    if after in '年月日号':
                        continue
                    s = SmartTitleUtils._parse_numeric(rm.group(1))
                    return (s, s, prefix, suffix, '', False, '', '', rm.group(1))

        return None

    @staticmethod
    def _looks_like_number(s: str) -> bool:
        """判断字符串是否看起来像数字（阿拉伯/中文/罗马/全角）"""
        if not s:
            return False
        s = s.strip()
        if s.isdigit():
            return True
        fullwidth_map = str.maketrans('０１２３４５６７８９', '0123456789')
        if s.translate(fullwidth_map).isdigit():
            return True
        chinese_chars = set('零一二三四五六七八九十百千万〇壹贰叁肆伍陆柒捌玖拾佰仟萬')
        if all(c in chinese_chars for c in s):
            return True
        roman_chars = set('IVXLCDMivxlcdm')
        if all(c in roman_chars for c in s):
            return True
        return False

    # ─── 智能标题生成 ──────────────────────────────────────

    @staticmethod
    def generate_smart_title(titles: List[str]) -> Optional[str]:
        """
        从多个书籍标题智能生成合并标题。

        分层策略：
        - 最佳：能提取章节信息 → 生成带范围的智能标题（如 "ABC 1-6"）
        - 中等：无法提取章节号但有公共前缀 → 用公共前缀作为标题
        - 兜底：完全无规律 → 返回 None

        示例：
        - ABC（序-3）+ ABC（4-6）→ ABC（序-6）
        - A 第1卷1-3 + A 第1卷4-6 → A 第1卷1-6
        - 书名A + 书名A + 书名A → 书名A

        Args:
            titles: 书籍标题列表（至少2个）

        Returns:
            生成的智能标题字符串，或 None（完全无法生成时）
        """
        if len(titles) < 2:
            return None

        # ── 第一层尝试：提取章节信息生成带范围的标题 ──
        chapter_infos = []
        for title in titles:
            info = SmartTitleUtils.extract_chapter_info(title)
            if info:
                chapter_infos.append(info)

        # 至少2个能提取到章节信息时，使用完整的智能标题逻辑
        if len(chapter_infos) >= 2:
            return SmartTitleUtils._generate_title_with_chapter_info(chapter_infos)

        # ── 第二层尝试：找公共前缀（无需章节信息） ──
        return SmartTitleUtils._generate_title_from_common_prefix(titles)

    @staticmethod
    def _num_to_str(v):
        """数值转显示字符串（浮点去掉多余的 .0）"""
        if isinstance(v, float):
            if v == int(v):
                return str(int(v))
            return str(v)
        return str(v)

    @staticmethod
    def _generate_title_with_chapter_info(chapter_infos: list) -> Optional[str]:
        """
        基于已提取的章节信息生成完整智能标题。

        包含：公共前缀 + 章节标记 + 范围 + 完成标记 + 后缀
        chapter_infos 元素为 9 元组（见 extract_chapter_info）。
        """
        # 区分纯标记模式（start == -1）和数字模式
        text_marker_books = [ci for ci in chapter_infos if ci[0] == -1]
        num_books = [ci for ci in chapter_infos if ci[0] != -1]

        # ── 全部是纯标记模式（如 （上）+（下））──
        if not num_books and text_marker_books:
            markers = [ci[4] for ci in chapter_infos if ci[4]]
            combined = ''.join(markers)
            prefix = chapter_infos[0][2]
            suffix = chapter_infos[0][3]
            has_parens = chapter_infos[0][5]
            if has_parens:
                title = f"{prefix}（{combined}）"
            else:
                title = f"{prefix}{combined}"
            if suffix:
                title = f"{title} {suffix}"
            return title.strip()

        if not num_books:
            return None

        # 数字模式：按 start, end 排序
        num_books.sort(key=lambda x: (x[0] if x[0] != -1 else 0, x[1] if x[1] != -1 else 0))
        min_start = num_books[0][0]
        max_end = max(ci[1] for ci in num_books)

        # 公共前缀（书名部分）
        # 若各书前缀因包裹符号不同（如【】与《》）而无法字符对齐，
        # commonprefix 会得到空串；此时回退到「出现最多的前缀」，
        # 平局则取最小章节号那本（num_books[0]）的前缀，避免书名被整体截断。
        prefixes = [ci[2] for ci in num_books if ci[2]]
        if prefixes:
            common_prefix = os.path.commonprefix(prefixes)
            if not common_prefix:
                common_prefix = Counter(prefixes).most_common(1)[0][0]
        else:
            common_prefix = ''

        # 章节标记：只取"最小编号那本书"的 marker。
        # 只有当 marker 出现在范围起点的书（如 "序-"、"重置版"）才保留；
        # 若 marker 只出现在后续的书（如 "第二卷第三章"），视为不连续的额外描述，丢弃。
        detected_marker = num_books[0][4]
        if detected_marker == '第':
            # "第" 为纯章节框定词，合并时去除
            detected_marker = ''

        # 后缀处理（提取完成标记，剩余作为后缀）
        completion_keywords = ['完结', '完本', '完整', '完', '全本', '全集', '全', '终']
        first_suffix = num_books[0][3].strip() if num_books[0][3] else ''
        # 清理尾部进度标记，如 " (13/15)"、"(2/3)"，避免污染合并标题
        first_suffix = re.sub(r'\(\s*\d+\s*/\s*\d+\s*\)', '', first_suffix).strip()
        completion_marker = ''
        clean_suffix = first_suffix
        for kw in completion_keywords:
            if kw in clean_suffix:
                completion_marker = kw
                clean_suffix = clean_suffix.replace(kw, '').strip()
                break

        has_parens = any(ci[5] for ci in num_books)
        first_inner = num_books[0][8] if num_books[0][8] else ''

        # 小数/带点编号检测：任意 inner 含小数点
        has_decimal = any('.' in str(ci[8]) for ci in num_books)

        if has_decimal:
            # 带点编号合并：保留第一本书中的"点号前缀"（如 2.3.），
            # 把末尾数字替换为合并后的最大编号。
            first_inner_str = str(first_inner)
            dot_nums = re.findall(r'\d+(?:\.\d+)*', first_inner_str)
            if dot_nums:
                first_num_text = dot_nums[0]
                last_num_text = dot_nums[-1]
                if '.' in last_num_text:
                    pfx, _, _ = last_num_text.rpartition('.')
                    dotted_prefix = pfx + '.'
                else:
                    dotted_prefix = ''
                # 仅当后续书也沿用该点号前缀（或无点号）时才借用前缀
                last_inner_str = str(num_books[-1][8])
                last_has_dot = '.' in last_inner_str
                if dotted_prefix and (
                    not last_has_dot
                    or str(SmartTitleUtils._num_to_str(max_end)).startswith(dotted_prefix)
                ):
                    # 借用前缀时，需去掉 max_end 自身已带的前缀段，避免重复
                    max_end_str = SmartTitleUtils._num_to_str(max_end)
                    if max_end_str.startswith(dotted_prefix):
                        tail = max_end_str[len(dotted_prefix):]
                    else:
                        tail = max_end_str
                    new_tail = dotted_prefix + tail
                else:
                    new_tail = SmartTitleUtils._num_to_str(max_end)
                if len(dot_nums) >= 2:
                    sep_match = re.search(r'(?<=\d)\s*([\-–—~－])\s*(?=\d)', first_inner_str)
                    sep = sep_match.group(1) if sep_match else '-'
                    range_text = first_num_text + sep + new_tail
                else:
                    range_text = first_num_text + '-' + new_tail
            else:
                range_text = f"{SmartTitleUtils._num_to_str(min_start)}-{SmartTitleUtils._num_to_str(max_end)}"
        else:
            first_book = num_books[0]
            if first_book[0] == first_book[1]:
                # 起点书为单个编号：其编号后的后缀即为起点后缀（如 "15上"）
                start_suffix = first_book[7] or first_book[6]
            else:
                # 起点书为范围：后缀属于范围末端，起点后缀取其自身的（如有）
                start_suffix = first_book[7]
            end_suffix = num_books[-1][6]
            if detected_marker and detected_marker[-1] in '-–—~－':
                # marker 以分隔符结尾（如 "序-"），范围只显示 end
                range_text = f"{SmartTitleUtils._num_to_str(max_end)}{end_suffix}"
            else:
                range_text = f"{SmartTitleUtils._num_to_str(min_start)}{start_suffix}-{SmartTitleUtils._num_to_str(max_end)}{end_suffix}"

        # 组装书名：书名前缀 + 章节范围 + 后缀。
        # 前缀与章节范围之间：若前缀以中文闭合包裹符结尾、且章节以中文开放包裹符开头，
        # 则不插入空格（如 【猎妻】（1-9））；否则（如英文书名）加空格。
        # 后缀（完成标记 / 作者等）前始终加空格。
        CLOSE_WRAP = '】》」』'
        OPEN_WRAP = '（《【'

        range_part = ''
        if detected_marker:
            # marker 分支：不保留括号内首尾空格，marker 以分隔符结尾时不加空格
            sep = '' if detected_marker[-1] in '-–—~－' else ' '
            if has_parens:
                range_part = f"（{detected_marker}{sep}{range_text}）"
            else:
                range_part = f"{detected_marker}{sep}{range_text}"
        elif has_parens:
            # 无 marker：保留第一本书括号内原始首尾空格（如 " 1-41 " → "（ 1-42 ）"）
            ls = ' ' if str(first_inner).startswith(' ') else ''
            rs = ' ' if str(first_inner).endswith(' ') else ''
            range_part = f"（{ls}{range_text}{rs}）"
        else:
            range_part = range_text

        parts = []
        if common_prefix:
            parts.append(common_prefix)
            if range_part:
                no_space = common_prefix[-1:] in CLOSE_WRAP or range_part[:1] in OPEN_WRAP
                parts.append(range_part if no_space else ' ' + range_part)
        elif range_part:
            parts.append(range_part)

        if completion_marker:
            parts.append(' ' + completion_marker)
        elif clean_suffix:
            parts.append(' ' + clean_suffix)

        smart_title = ''.join(parts)
        smart_title = re.sub(r'\s+', ' ', smart_title).strip()
        return smart_title if smart_title else None

    @staticmethod
    def _generate_title_from_common_prefix(titles: List[str]) -> Optional[str]:
        """
        当无法从标题中提取章节信息时，通过找公共前缀来生成简单合并标题。
        
        适用场景：
        - 所有书名完全相同或高度相似
        - 标题中不含可识别的数字格式
        
        不适用场景（返回None）：
        - 书名完全不同（如不同的书被误归为一组）
        - 公共前缀太短（如只有【等符号）
        
        Returns:
            公共前缀作为标题，或 None（书名不相似时）
        """
        if not titles or len(titles) < 2:
            return None

        # 清理标题
        cleaned_titles = [title.strip() for title in titles if title.strip()]
        if len(cleaned_titles) < 2:
            return None

        # 找最长公共前缀
        common_prefix = os.path.commonprefix(cleaned_titles)
        if not common_prefix:
            return None

        common_prefix = common_prefix.strip()

        # ── 过滤无意义的公共前缀 ──
        
        # 1. 公共前缀太短（少于3个字符），说明书名不相似
        if len(common_prefix) < 3:
            return None
        
        # 2. 公共前缀只是标点符号（如【、[、( 等）
        if all(c in '【】[]()（）《》<>「」『』""''—-~～' for c in common_prefix):
            return None
        
        # 3. 如果公共前缀截断了中文字符，检查是否值得保留
        if len(common_prefix) < len(cleaned_titles[0]):
            next_char_pos = len(common_prefix)
            original = cleaned_titles[0]
            if next_char_pos < len(original):
                char = original[next_char_pos]
                # 截断了中文，且前缀本身不够有意义的长度
                if '\u4e00' <= char <= '\u9fff' and len(common_prefix) < 5:
                    return None

        # 4. 检查书名相似度：如果公共前缀占比太小，说明书名不相似
        avg_len = sum(len(t) for t in cleaned_titles) / len(cleaned_titles)
        if avg_len > 0 and len(common_prefix) / avg_len < 0.3:
            # 公共前缀不足平均长度的30%，认为不相似
            return None

        return common_prefix

    @staticmethod
    def sort_books_by_chapter(books: List[Any], title_key: str = 'novel_title') -> tuple:
        """
        按书名中的章节号对书籍列表进行升序排序。

        策略（非全有或全无）：
        - 能提取到数字章节号的书籍，按 (start, end) 升序排在前部；
        - 无法提取（或无数字，如「番外」「（上）」「（下）」）的书籍，
          按书名正序排到末尾，避免因为个别书籍解析失败而整体不排序。

        Args:
            books: 书籍列表（每个元素需包含 title_key 对应的字段）
            title_key: 书名字段名，默认为 'novel_title'

        Returns:
            (sorted_books, success) 元组
            - sorted_books: 排序后的书籍列表
            - success: 始终为 True（本方法总会给出一个有序列表）
        """
        if len(books) < 2:
            return books, True

        indexed = []
        for idx, book in enumerate(books):
            title = book.get(title_key, '') if isinstance(book, dict) else getattr(book, title_key, '')
            info = SmartTitleUtils.extract_chapter_info(title)
            if info and info[0] != -1:
                # 数字章节号：按 (start, end) 排序
                start = info[0] if isinstance(info[0], (int, float)) else float('inf')
                end = info[1] if isinstance(info[1], (int, float)) else float('inf')
                indexed.append((start, end, idx, book, title))
            else:
                # 无法提取章节号 / 纯标记：放到末尾，按书名排序
                indexed.append((float('inf'), float('inf'), idx, book, title))

        # 排序键：章节号 → 书名（正序，忽略大小写）→ 原始顺序
        indexed.sort(key=lambda x: (x[0], x[1], (x[4] or '').lower(), x[2]))

        sorted_books = [item[3] for item in indexed]
        return sorted_books, True
