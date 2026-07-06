"""
智能标题生成工具模块

提供书籍合并时的智能标题生成功能，支持：
- 多种数字格式：阿拉伯数字、中文小写/大写、罗马数字
- 章节标记识别：序、卷、部、册、集、前传/后传、外传、番外
- 智能范围合并：自动识别章节号范围并合并
"""

import os
import re
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

    @staticmethod
    def extract_chapter_info(title: str) -> Optional[Tuple[int, int, str, str, str, bool]]:
        """
        从标题中提取章节信息。

        支持的数字格式：
        - 阿拉伯数字: 1, 23, 456
        - 中文小写: 一, 二, 十二, 一百二十三
        - 中文大写: 壹, 贰, 叁, 拾贰
        - 罗马数字: I, II, III, IV, V, X, XII, XLIX
        - 大小写混合: II-IV, 三-五, 1-VIII

        支持的章节标记：
        - 序, 卷, 部, 册, 集, 前/后传, 外传, 番外
        - 第X卷/部等组合标记
        - 括号内标记: (序), （序）

        Returns:
            元组 (start, end, prefix, suffix, chapter_prefix, has_parens) 或 None
            - start: 起始章节数字
            - end: 结束章节数字
            - prefix: 书名前缀（不含章节信息）
            - suffix: 后缀（作者/补充信息）
            - chapter_prefix: 章节文字标记（如"序"、"第一卷"等）
            - has_parens: 原始格式是否使用括号包裹章节信息
        """
        any_num, all_markers = SmartTitleUtils._get_regex_patterns()

        # 括号内任意非数字前缀（如 "重置版"、"序"、"第一卷" 等）
        # 匹配不含数字、括号的任意中文/英文文字
        arbitrary_prefix = r'(?:[^\d\(\)（）\s]+(?:\s+[^\d\(\)（）\s]+)*?)?'

        # 数字后的常见后缀（如 上、下、中、前、后、外、终、完 等）
        num_suffix = r'([上下中前后内外终完正续附增补篇回章集卷册部]*)'

        # 匹配模式列表（按优先级排序）
        patterns = [
            # 0. 括号内包含数字范围（支持任意前缀+后缀）: （ 1-11 ）, (重置版 1-38), （1-2上）
            rf'[\(（]\s*({arbitrary_prefix})\s*({any_num})\s*[-–—~－]\s*({any_num}){num_suffix}[^\)]*?[\)）]',

            # 0.5. 括号内只有单数字（支持后缀）: （4）, (4), （ 4 ）, （2下）, 单章节
            rf'[\(（]\s*({arbitrary_prefix})\s*({any_num}){num_suffix}[^\)]*?[\)）]',

            # 1. 带括号的章节标记后跟数字: (序)3, (第一卷)1-5, (外传)II-IV
            rf'[\(（]({all_markers}?[^\)]*?)[\)）]\s*[-–—]?\s*({any_num})(?:\s*[-–—~]\s*({any_num}))?',

            # 2. 直接跟章节标记: 序3, 序III, 第一卷1-3, 外传II-V, 卷十二
            rf'({all_markers})\s*[-–—]?\s*({any_num})(?:\s*[-–—~]\s*({any_num}))?',

            # 3. 纯数字范围（无标记）: 3, 3-5, III-XII, 二-六, 1-VIII
            rf'^.*?(?:[^章卷部册集])?\s*[-–—]?\s*({any_num})(?:\s*[-–—~]\s*({any_num}))(?:\s*[完全]|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                groups = match.groups()

                # 根据匹配到的组数判断是哪种模式
                non_empty = [g for g in groups if g is not None]
                if not non_empty:
                    continue

                # 提取数字后缀（Pattern 0 和 0.5 有额外的后缀捕获组）
                captured_suffix = ''  # 数字后的后缀如 "上"、"下"

                if len(groups) >= 4 and groups[3] is not None:
                    # Pattern 0: 4个捕获组（prefix, start, end, suffix）
                    chapter_prefix = groups[0].strip() if groups[0] else ''
                    start_str = groups[1].strip()
                    end_str = groups[2].strip()
                    captured_suffix = groups[3].strip() if groups[3] else ''
                elif len(groups) == 3:
                    # 可能是 Pattern 0.5（3组：prefix, num, suffix）或 Pattern 1/2（3组：prefix, start, end）
                    match_text = match.group()
                    if match_text and match_text[0] in '（(':
                        # Pattern 0.5: 括号内单数字 + 后缀
                        chapter_prefix = groups[0].strip() if groups[0] else ''
                        num_str = groups[1].strip()
                        # groups[2] 可能是后缀（如果是 Pattern 0.5）
                        if groups[2] and not SmartTitleUtils._looks_like_number(groups[2]):
                            captured_suffix = groups[2].strip()
                            start_str = num_str
                            end_str = num_str
                        else:
                            start_str = num_str
                            end_str = groups[2].strip() if groups[2] else num_str
                    else:
                        # Pattern 1 或 2: 有章节标记的模式
                        chapter_prefix = groups[0].strip() if groups[0] else ''
                        start_str = groups[1].strip()
                        end_str = groups[2].strip() if len(groups) > 2 and groups[2] else start_str
                elif len(groups) == 2:
                    # 判断依据：match 是否以括号开头
                    match_text = match.group()
                    if match_text and match_text[0] in '（(':
                        # Pattern 0.5 无后缀: 括号内单数字
                        chapter_prefix = groups[0].strip() if groups[0] else ''
                        num_str = groups[1].strip() if groups[1] is not None else ''
                        start_str = num_str
                        end_str = num_str  # 单数字，start=end
                    else:
                        # Pattern 3: 无括号范围格式
                        chapter_prefix = ''
                        start_str = groups[0].strip() if groups[0] else ''
                        end_str = groups[1].strip() if groups[1] is not None else start_str
                elif len(groups) >= 3 and groups[0] is not None:
                    # Pattern 1 或 2: 有章节标记的模式（3个捕获组，end可能为空）
                    chapter_prefix = groups[0].strip() if groups[0] else ''
                    start_str = groups[1].strip()
                    end_str = groups[2].strip() if len(groups) > 2 and groups[2] else start_str
                else:
                    # 其他情况：用非空组
                    chapter_prefix = ''
                    if len(non_empty) >= 2:
                        start_str = non_empty[0].strip()
                        end_str = non_empty[-1].strip()
                    elif len(non_empty) == 1:
                        start_str = end_str = non_empty[0].strip()
                    else:
                        continue

                # 将各种格式转为 int
                start = SmartTitleUtils.extract_number_from_string(start_str)
                end = SmartTitleUtils.extract_number_from_string(end_str)

                if start is None or end is None:
                    continue

                # 提取前后缀
                prefix = title[:match.start()].rstrip()
                suffix = title[match.end():].lstrip()

                # 检测原始格式是否包含括号包裹的章节信息
                has_parens = bool(re.match(r'^.*[\(（]', match.group()))

                return (start, end, prefix, suffix, chapter_prefix, has_parens, captured_suffix)

        return None

    @staticmethod
    def _looks_like_number(s: str) -> bool:
        """判断字符串是否看起来像数字（阿拉伯/中文/罗马/全角）"""
        if not s:
            return False
        s = s.strip()
        # 阿拉伯数字
        if s.isdigit():
            return True
        # 全角数字
        fullwidth_map = str.maketrans('０１２３４５６７８９', '0123456789')
        if s.translate(fullwidth_map).isdigit():
            return True
        # 中文数字
        chinese_chars = set('零一二三四五六七八九十百千万〇壹贰叁肆伍陆柒捌玖拾佰仟萬')
        if all(c in chinese_chars for c in s):
            return True
        # 罗马数字
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
    def _generate_title_with_chapter_info(chapter_infos: list) -> Optional[str]:
        """
        基于已提取的章节信息生成完整智能标题。

        包含：公共前缀 + 章节标记 + 范围 + 完成标记 + 后缀
        """
        # 按章节起始号排序
        chapter_infos.sort(key=lambda x: x[0])

        min_start = chapter_infos[0][0]
        max_end = max(ci[1] for ci in chapter_infos)

        # 找公共前缀（书名部分）
        prefixes = [ci[2] for ci in chapter_infos if ci[2]]
        common_prefix = ""
        if prefixes:
            common_prefix = os.path.commonprefix(prefixes)
            if not common_prefix:
                common_prefix = prefixes[0]

        # 识别章节文字标记（优先级：序 > 前/后传 > 外传 > 番外 > 卷部册集）
        chapter_markers_priority = ['序', '前传', '后传', '外传', '番外', '卷', '部', '册', '集']
        detected_chapter_prefix = ''

        all_chapter_prefixes = [ci[4] for ci in chapter_infos if ci[4]]
        if all_chapter_prefixes:
            for marker in chapter_markers_priority:
                for prefix in all_chapter_prefixes:
                    if marker in prefix:
                        detected_chapter_prefix = prefix
                        break
                if detected_chapter_prefix:
                    break
            if not detected_chapter_prefix:
                detected_chapter_prefix = all_chapter_prefixes[0]

        # 取后缀
        first_suffix = chapter_infos[0][3] if chapter_infos[0][3] else ""
        last_suffix = chapter_infos[-1][3] if chapter_infos[-1][3] else ""

        # 检查完成标记
        completion_marker = ""
        completion_keywords = ['完结', '完', '全', '全集', '全本', '终']
        for kw in completion_keywords:
            if kw in last_suffix:
                completion_marker = kw
                break

        # 构建章节范围
        # 提取数字后缀（如 "上"、"下"）- 取最大 end 对应的后缀（多个时取最后出现的）
        end_num_suffix = ''
        for ci in reversed(chapter_infos):  # 从后往前遍历，优先取后面的
            if len(ci) > 6 and ci[6]:  # ci[6] = captured_suffix
                if ci[1] == max_end:
                    end_num_suffix = ci[6]
                    break
        # 如果没找到精确匹配 max_end 的，用任意一个非空后缀
        if not end_num_suffix:
            for ci in reversed(chapter_infos):
                if len(ci) > 6 and ci[6]:
                    end_num_suffix = ci[6]
                    break

        raw_range = str(min_start) if min_start == max_end else f"{min_start}-{max_end}{end_num_suffix}"

        # 检测是否有书名使用括号格式，若有则保留括号
        has_any_parens = any(len(ci) > 5 and ci[5] for ci in chapter_infos)

        # 组合标题
        parts = []
        if common_prefix:
            parts.append(common_prefix)

        # 根据是否有括号格式决定章节信息的组合方式
        if detected_chapter_prefix and has_any_parens:
            # 括号内格式：（标记 数字范围）如 （重置版 1-40）
            chapter_range = f"（{detected_chapter_prefix} {raw_range}）"
            parts.append(chapter_range)
        elif detected_chapter_prefix:
            # 无括号：标记+数字范围 如 重置版 1-40
            chapter_range = f"{detected_chapter_prefix} {raw_range}"
            parts.append(chapter_range)
        elif has_any_parens:
            # 有括号但无标记：（数字范围）如 （1-40）
            chapter_range = f"（{raw_range}）"
            parts.append(chapter_range)
        else:
            # 无括号无标记：纯数字 如 1-40
            parts.append(raw_range)

        if completion_marker:
            parts.append(completion_marker)
        if first_suffix:
            clean_suffix = first_suffix
            for kw in completion_keywords:
                clean_suffix = clean_suffix.replace(kw, '').strip()
            if clean_suffix:
                parts.append(clean_suffix)

        smart_title = ' '.join(parts)
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

        Args:
            books: 书籍列表（每个元素需包含 title_key 对应的字段）
            title_key: 书名字段名，默认为 'novel_title'

        Returns:
            (sorted_books, success) 元组
            - sorted_books: 排序后的书籍列表（原列表未修改则返回原列表）
            - success: True 表示成功排序，False 表示无法提取章节号
        """
        # 为每本书提取章节信息，保留原始索引
        indexed = []
        all_extracted = True
        for idx, book in enumerate(books):
            title = book.get(title_key, '') if isinstance(book, dict) else getattr(book, title_key, '')
            info = SmartTitleUtils.extract_chapter_info(title)
            if info:
                indexed.append((idx, book, info))
            else:
                all_extracted = False
                break

        if not all_extracted or len(indexed) < 2:
            return books, False

        # 按章节起始号排序，起始号相同则按结束号
        indexed.sort(key=lambda x: (x[2][0], x[2][1]))

        # 返回排序后的书籍列表
        sorted_books = [item[1] for item in indexed]
        return sorted_books, True
