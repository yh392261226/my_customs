"""
书籍ID提取器（共享模块）

从书籍链接中提取书籍ID，供多处复用：
  - 浏览器标签页监听（切换标签时识别小说页面）
  - 自动爬取：按规则取回链接后，统一交由本模块提取书籍ID

书籍ID的形态非常多样，绝不能假定它只是数字。参考 src/spiders 下各解析器，
实际存在以下几类（{id} 即为书籍ID）：
  - 纯数字        ：/book/{12345}.html、?p={789}、artdetail-{12345}.html
  - 十六进制哈希  ：/fiction/id-{68fa7dcff3de0}.html        (crxs / xchina)
  - 字母数字token ：/?view_novel/{ambmwnKgMYHR1Z}           (xbookasd)
  - Base64/编码串 ：/fiction.php?id={MjE0OTc%3D}            (xbookcnorg)
  - 短 slug       ：/n/{umkof}、/read/{cidhld}/
  - 带连字符 slug ：/book/{s3-mingchaonaxieshier}.html      (feiku6)
  - 纯中文标题    ：/{测试小说}/、/book/{中文标题}            (fsnovel / book18)
  - 日期路径      ：/{2025/10/13/尿道连通的无尽调教-1-4}/     (17short)
                    /index.php/archives/{2025/08/67909}/    (alhs)
  - 分类路径      ：/{wife/我的婚紗照}、/{renqishunv/73359}   (youbook / x6wx)
  - 复合形态      ：/{26_34976}/、/thread-{35923-1-1}.html、?v=9082&name=xxx

因此本模块只在「该站点确认为纯数字ID」的分支才做数字校验，其余一律按
url_pattern 原样提取，不做数字限制；匹配时还允许ID包含斜杠（路径型ID）。

原先这段逻辑只作为 BrowserTabMonitor 的方法存在，自动爬取无法复用。
抽成模块级函数并做了以下升级：
  1. 模块级函数，无需实例化监视器即可调用
  2. 容错站点URL的 www / http、https 差异（列表页抓取到的链接写法
     常与配置的站点URL不一致，原实现要求前缀完全一致导致提取失败）
  3. 匹配前剔除 URL 的 #片段，避免把锚点误当成ID的一部分
  4. 降低日志级别，避免批量提取时（自动爬取）刷屏
"""

import re
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import unquote, urljoin, urlparse

from src.utils.logger import get_logger

logger = get_logger(__name__)


def _candidate_base_urls(site_url: str) -> List[str]:
    """
    生成站点基础URL的候选写法（含 www / http / https 变体）

    原实现只按配置里的站点URL做前缀匹配，一旦页面链接写成
    http:// 或带/不带 www 就匹配不上。这里把这些写法都列为候选。

    Args:
        site_url: 数据库中配置的网站地址

    Returns:
        List[str]: 候选基础URL列表（按最贴近配置的顺序排列）
    """
    if not site_url:
        return []

    base = site_url.strip().rstrip('/')
    if base.endswith('.html'):
        # 站点地址直接配置到了某个页面时，去掉文件名部分
        base = base.rsplit('/', 1)[0]

    parsed = urlparse(base)
    netloc = parsed.netloc
    if not netloc:
        return [base]
    path = parsed.path.rstrip('/')

    # www 有无两种写法
    if netloc.startswith('www.'):
        netlocs = [netloc, netloc[4:]]
    else:
        netlocs = [netloc, 'www.' + netloc]

    schemes: List[str] = []
    for scheme in (parsed.scheme, 'https', 'http'):
        if scheme and scheme not in schemes:
            schemes.append(scheme)

    candidates: List[str] = []
    for nl in netlocs:
        for scheme in schemes:
            candidate = f"{scheme}://{nl}{path}"
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def _find_first(bases: List[str], url: str,
                make_pattern: Callable[[str], str]) -> Optional[re.Match]:
    """依次用各候选基础URL构造正则去匹配，返回首个命中结果"""
    for base in bases:
        try:
            match = re.search(make_pattern(base), url)
        except re.error:
            continue
        if match:
            return match
    return None


def _url_pattern_regex(url_pattern: str, id_group: str) -> str:
    """
    把 url_pattern 转换成正则

    url_pattern 是「URL模板」而非正则（如 book/{novel_id}.html、
    fiction.php?id={novel_id}），因此字面部分必须转义，否则其中的 . 和 ?
    会被当成正则元字符，导致含查询参数的模式（?id=xxx）永远匹配不上。

    Args:
        url_pattern: 含 {novel_id} 占位符的URL模板
        id_group: 用于替换占位符的捕获组

    Returns:
        str: 可直接使用的正则片段
    """
    parts = url_pattern.split('{novel_id}')
    return id_group.join(re.escape(part) for part in parts)


def extract_novel_id_from_url(url: str, site_config: Dict[str, Any]) -> Optional[str]:
    """
    从URL中提取书籍ID

    Args:
        url: 书籍链接（完整URL）
        site_config: 网站配置（需含 url，可选 url_pattern / parser）

    Returns:
        Optional[str]: 书籍ID，无法识别时返回 None
    """
    try:
        if not url:
            return None

        url_pattern = (site_config.get('url_pattern') or '')
        site_url = (site_config.get('url') or '')
        parser = (site_config.get('parser') or '')

        bases = _candidate_base_urls(site_url)
        if not bases:
            return None

        # 剔除 #片段，避免锚点被当成ID的一部分
        match_url = url.split('#', 1)[0]

        # ---------- 优先特殊站点 ----------
        # cool18.com：论坛帖 / 书库两种查询参数
        if 'cool18.com' in site_url:
            match = _find_first(bases, match_url,
                                lambda b: rf"{re.escape(b)}\?.*?(?:tid|cid)=(\d+)")
            if match:
                return match.group(1)

        # xx-book.com / seqing001.com：/?p={id}
        if 'xx-book.com' in site_url or 'seqing001.com' in site_url:
            match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/\?p=(\d+)")
            if match:
                return match.group(1)

        # x6wx.com：/{category}/{novel_id}.html，ID需带分类
        if 'x6wx.com' in site_url:
            match = _find_first(bases, match_url,
                                lambda b: rf"{re.escape(b)}/([^/]+)/([^/?]+)\.html")
            if match:
                return f"{unquote(match.group(1))}/{unquote(match.group(2))}"

        if url_pattern:
            # 各站点的特殊URL格式优先匹配；未命中时统一回退到按 url_pattern 的
            # 标准处理，避免「特殊分支不匹配就直接返回None」把有效书籍页漏掉
            special_id: Optional[str] = None

            # 69hnovel.com：ID为 category/article 两段
            if '69hnovel.com' in site_url and url_pattern == '/erotic-novel/{novel_id}.html':
                match = _find_first(bases, match_url, lambda b:
                                    rf"{re.escape(b)}/erotic-novel/([^/?]+)/([^/?]+)\.html")
                if match:
                    category = unquote(match.group(1))
                    article = unquote(match.group(2))
                    if category and article and re.search(r'\d', article):
                        special_id = f"{category}/{article}"

            # photo-gram.com：/read/{novel_id}/
            elif 'photo-gram.com' in site_url and url_pattern == '/read/{novel_id}/':
                match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/read/([^/?]+)/")
                if match:
                    special_id = unquote(match.group(1))

            # po18gg / po18rr：/{dir_id}/{novel_id}/，dir_id 为 novel_id 去后3位
            elif (('po18gg.com' in site_url or 'po18rr.com' in site_url)
                  and url_pattern == 'novel/{novel_id}.html'):
                match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/([^/]+)/([^/?]+)/")
                if match:
                    dir_id = match.group(1)
                    novel_id = match.group(2)
                    if (len(novel_id) >= 2 and novel_id[-3:].isdigit()
                            and novel_id[:-3] == dir_id):
                        special_id = novel_id

            # 以下解析器的实际URL格式为 /{category}/{novel_id}.html
            # 仅当这几类解析器确认使用数字ID时才采用；非数字ID会落到下面的
            # url_pattern 标准处理，不会被误判丢弃
            elif parser in ('cms_t1_v2', 'lulu6_v2', 'cms_t7_v2'):
                match = _find_first(bases, match_url,
                                    lambda b: rf"{re.escape(b)}/([^/]+)/([^/?]+)\.html")
                if match:
                    novel_id = unquote(match.group(2))
                    if novel_id.isdigit():
                        special_id = novel_id

            # cms_t3_v2：artdetail-{id}.html 或 /index.php/art/detail/id/{id}
            elif parser == 'cms_t3_v2':
                match = _find_first(bases, match_url,
                                    lambda b: rf"{re.escape(b)}/artdetail-([^/?]+)\.html")
                if match:
                    novel_id = unquote(match.group(1))
                    if novel_id.isdigit():
                        special_id = novel_id

                if special_id is None:
                    match = _find_first(bases, match_url, lambda b:
                                        rf"{re.escape(b)}/index\.php/art/detail/id/([^/?]+)")
                    if match:
                        novel_id = unquote(match.group(1))
                        if novel_id.isdigit():
                            special_id = novel_id

            if special_id:
                return special_id

            # 标准处理：按 url_pattern 构造正则
            if '91porna.com' in site_url:
                # 配置的 base 含 /novels/new，与实际书籍URL不符，这里用站点根
                pattern = (rf"{re.escape('https://91porna.com')}"
                           rf"{_url_pattern_regex(url_pattern, '([^/?]+)')}(?:\?[^#]*)?(?:#.*)?$")
                match = re.search(pattern, match_url)
            else:
                def _standard(base: str, id_group: str = '([^/?]+)') -> str:
                    # 书籍ID形态多样（数字/哈希/slug/中文标题），占位符统一替换
                    pat = _url_pattern_regex(url_pattern, id_group)
                    if pat.startswith('/'):
                        return rf"{re.escape(base)}{pat}(?:\?[^#]*)?(?:#.*)?$"
                    return rf"{re.escape(base)}/{pat}(?:\?[^#]*)?(?:#.*)?$"

                match = _find_first(bases, match_url, _standard)
                if match is None:
                    # 书籍ID可能是含斜杠的路径型ID（如 2025/10/13/标题、category/slug、
                    # wife/我的婚紗照），严格模式排除了斜杠，这里放宽后重试
                    match = _find_first(bases, match_url, lambda b: _standard(b, '(.+?)'))

            if match:
                novel_id = unquote(match.group(1))
                if '91porna.com' in site_url and not novel_id.isdigit():
                    return None
                return novel_id

        else:
            # ---------- 无 url_pattern，按站点域名特殊处理 ----------
            if 'crxs.me' in site_url:
                match = _find_first(bases, match_url,
                                    lambda b: rf"{re.escape(b)}/fiction/id-([^/?]+)\.html")
                if match:
                    return unquote(match.group(1))

            elif 'book18.me' in site_url:
                # 数字ID：/article/{id}
                match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/article/(\d+)")
                if match:
                    return match.group(1)
                # 中文标题：/book/{标题}
                match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/book/([^/?]+)")
                if match:
                    return unquote(match.group(1))

            elif 'po18gg.com' in site_url or 'po18rr.com' in site_url:
                match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/([^/]+)/([^/?]+)/")
                if match:
                    dir_id = match.group(1)
                    novel_id = match.group(2)
                    if (len(novel_id) >= 2 and novel_id[-3:].isdigit()
                            and novel_id[:-3] == dir_id):
                        return novel_id

            elif 'xbookasd.top' in site_url:
                match = _find_first(bases, match_url,
                                    lambda b: rf"{re.escape(b)}/\?novel/detail/([^/?&]+)")
                if match:
                    return unquote(match.group(1))
                match = _find_first(bases, match_url,
                                    lambda b: rf"{re.escape(b)}/\?view_novel/([^/?&]+)")
                if match:
                    return unquote(match.group(1))

            elif 'rouwenwu20.com' in site_url:
                # /{prefix}_{novel_id}/，prefix 为 novel_id 去后3位（不足则为0）
                match = _find_first(bases, match_url,
                                    lambda b: rf"{re.escape(b)}/([^/_]+)_([^/?]+)/")
                if match:
                    prefix = unquote(match.group(1))
                    novel_id = unquote(match.group(2))
                    if len(novel_id) >= 3:
                        expected_prefix = novel_id[:-3] or '0'
                        if prefix == expected_prefix:
                            return novel_id
                    elif novel_id and prefix == '0':
                        return novel_id

            elif 'aaread.cc' in site_url:
                match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/book/([^/?]+)")
                if match:
                    novel_id = unquote(match.group(1))
                    if novel_id.isdigit():
                        return novel_id

            else:
                # 默认模式：/b/{novel_id}
                match = _find_first(bases, match_url, lambda b: rf"{re.escape(b)}/b/([^/?]+)")
                if match:
                    return unquote(match.group(1))

        logger.debug(f"未能从URL提取书籍ID: {url}")
        return None

    except Exception as e:
        logger.error(f"提取书籍ID失败: {url}, 错误: {e}")
        return None


def _looks_like_url(value: str) -> bool:
    """判断是否为完整URL（而非已经提取好的书籍ID）"""
    return '://' in value or value.startswith('//')


def resolve_novel_id(value: str, site_config: Dict[str, Any]) -> Optional[str]:
    """
    把自动爬取取回的一条结果解析为书籍ID

    自动爬取的结果有两种形态，这里统一判定：
      - 完整链接（http(s)://... 或 //...）-> 走统一的链接提取逻辑
      - 已经是书籍ID（规则里用 re 直接取出的纯ID）-> 直接作为书籍ID
      - 站点内相对路径（/xxx）-> 补全为绝对地址后提取，取不到则原样使用

    Args:
        value: 链接或书籍ID
        site_config: 网站配置

    Returns:
        Optional[str]: 书籍ID，无法解析时返回 None
    """
    value = (value or '').strip()
    if not value:
        return None

    if _looks_like_url(value):
        # 协议相对地址（//host/path）补全协议后再提取
        if value.startswith('//'):
            value = 'https:' + value
        return extract_novel_id_from_url(value, site_config)

    if value.startswith('/'):
        # 站点内相对路径：补全后按链接提取，仍取不到则原样当作书籍ID
        site_url = (site_config.get('url') or '').strip()
        if site_url:
            extracted = extract_novel_id_from_url(urljoin(site_url, value), site_config)
            if extracted:
                return extracted
        return value.rstrip('/')

    # 无协议、非路径：视为规则已经直接给出的书籍ID
    return value.rstrip('/')


def extract_novel_ids(urls: List[str], site_config: Dict[str, Any]) -> List[str]:
    """
    批量把「书籍链接」转成书籍ID（保持顺序、去重、跳过无法识别的链接）

    自动爬取取回的结果有时是完整链接、有时规则已直接返回书籍ID，
    这里逐条判定后统一转ID，详见 resolve_novel_id()。

    Args:
        urls: 书籍链接列表（元素也可能已是不含协议的书籍ID）
        site_config: 网站配置

    Returns:
        List[str]: 去重后的书籍ID列表
    """
    novel_ids: List[str] = []
    seen = set()

    for url in urls:
        novel_id = resolve_novel_id(url, site_config)
        if not novel_id:
            continue
        # 书籍ID会被拼成逗号分隔串交给爬取管理，含逗号会导致拆分错误
        if ',' in novel_id:
            logger.warning(f"跳过含逗号的书籍ID: {novel_id}")
            continue
        if novel_id in seen:
            continue
        seen.add(novel_id)
        novel_ids.append(novel_id)

    return novel_ids
