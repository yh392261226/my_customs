"""
自动爬取书籍链接

在书籍网站管理中为每个网站配置：
  - auto_crawl_url      : 指定的书籍列表页面/接口地址
  - auto_crawl_rule     : 自定义过滤规则（Python 片段）
  - auto_crawl_pages    : 最大抓取页数（配合下一页规则做分页）
  - auto_crawl_next_rule: 下一页规则，根据当前页数据返回下一页地址

执行流程（由爬取管理页面的「自动爬取书籍」按钮 / G 快捷键触发）：
  1. 抓取指定地址，自动识别返回内容是 JSON 接口还是 HTML 页面
  2. 解析出条目列表（JSON 数组或页面上的 <a> 链接）
  3. 逐条应用规则，判定该条目是否为「真正的书籍」
     —— 规则的职责正是排除广告、评论/跟帖、求助贴（字数少）等噪音
  4. 若配置了下一页规则，则按其返回的地址继续抓下一页，直至达到最大页数
  5. 把符合规则的结果原样返回，交给爬取管理用统一的
     novel_id_extractor 提取书籍ID并爬取

本模块只负责「取回符合规则的结果」，不负责提取书籍ID，
书籍ID的提取统一由 src/utils/novel_id_extractor.py 完成，
与浏览器标签页监听共用同一套逻辑。

规则编写说明：
    可用变量：
        item       当前条目（HTML模式为链接字典，JSON模式为接口返回的对象）
        url        链接地址（JSON模式取条目里的 url/link 字段）
        text       标题文字（已 strip、已去HTML标签）
        text_len   标题文字长度
        title      同 text
        html       HTML模式下该 <a> 标签的完整片段
        page_url   当前页地址
        page       当前页码（从1开始）
        re         Python 正则模块
        extract_id(url)  用统一的提取器从链接取书籍ID，取不到返回 None

    返回值约定：
        返回 True          -> 保留该条目，交由爬取管理提取ID并爬取
        返回 字符串         -> 可以是链接，也可以直接是书籍ID
                              （会自动判定：带 http(s):// 的按链接提取，
                                不带协议的直接当书籍ID使用）
        返回 False/None/空 -> 跳过该条目（广告、评论、求助贴等）

    规则留空则保留所有条目，由爬取管理在提取ID时剔除无效项。
    可写单行表达式，也可写多行（多行时可用 return）。

下一页规则编写说明：
    可用变量：items（本页解析出的原始条目列表）、page_url、page、re
    返回下一页地址字符串；返回 None/空 表示分页结束。

    示例（cool18 禁忌书屋的游标分页）：
        tids = [int(i['tid']) for i in items if i.get('uptid') == '0']
        if not tids:
            return None
        return page_url.split('mtid=')[0] + 'mtid=' + str(min(tids))

典型配置示例（cool18 禁忌书屋）：
    数据格式    : JSON接口   ← 必须指定，否则误填HTML列表页时会去解析页面上的推荐链接
    自动爬取页面: https://www.cool18.com/bbs4/index.php?app=forum&act=ajax&mtid=0&aifilter=1
    最大页数    : 5
    爬取规则    :
        # 只用 size 判定即可。注意：跟帖(uptid!='0')里也有子章节（续章/番外），
        # 若按 uptid 排除会把这些子章节一并误杀
        if int(item.get('size') or 0) <= 1000:
            return False
        return item['tid']
    下一页规则  :
        # 游标必须取「顶层帖」中最小的 tid，与页面 JS 的 _mtid 逻辑保持一致
        tids = [int(i['tid']) for i in items if i.get('uptid') == '0']
        if not tids:
            return None
        return page_url.split('mtid=')[0] + 'mtid=' + str(min(tids))
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

from src.utils.logger import get_logger
from src.utils.novel_id_extractor import extract_novel_id_from_url

logger = get_logger(__name__)

# 规则执行时可用的内建函数（限制 __builtins__，避免规则误用危险操作）
_SAFE_BUILTINS = {
    'abs': abs,
    'all': all,
    'any': any,
    'bool': bool,
    'dict': dict,
    'enumerate': enumerate,
    'filter': filter,
    'float': float,
    'int': int,
    'isinstance': isinstance,
    'len': len,
    'list': list,
    'map': map,
    'max': max,
    'min': min,
    'range': range,
    'reversed': reversed,
    'set': set,
    'sorted': sorted,
    'str': str,
    'sum': sum,
    'tuple': tuple,
    'zip': zip,
    'True': True,
    'False': False,
    'None': None,
}

# 过滤规则与下一页规则各自可用的变量名
ITEM_RULE_PARAMS: Tuple[str, ...] = (
    'url', 'text', 'text_len', 'title', 'html', 'page_url', 'page', 're', 'extract_id', 'item',
)
NEXT_RULE_PARAMS: Tuple[str, ...] = ('items', 'page_url', 'page', 're', 'url')

_REQUEST_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/json,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 被忽略的伪协议前缀
_SKIP_HREF_PREFIXES = ('#', 'javascript:', 'mailto:', 'tel:', 'data:')

# JSON 接口常见的数据字段
_JSON_LIST_KEYS = ('data', 'list', 'items', 'rows', 'result', 'threads', 'topics')

# 数据格式：空表示自动识别
FORMAT_AUTO = ''
FORMAT_JSON = 'json'
FORMAT_HTML = 'html'

_HTML_TAG_RE = re.compile(r'<[^>]+>')


class AutoCrawlError(Exception):
    """自动爬取过程中的可预期错误（配置缺失、抓取失败等）"""


def _to_int(value: Any, default: int) -> int:
    """把配置值转成整数（界面上可能存成字符串）"""
    try:
        result = int(value)
        return result if result > 0 else default
    except (TypeError, ValueError):
        return default


def fetch_page_html(site: Dict[str, Any], page_url: str,
                    proxy_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    抓取自动爬取页面的内容（HTML 或 JSON 接口返回）

    优先复用该网站解析器的 _get_url_content（自带多层反爬策略），
    失败时回退到普通 requests 请求。

    Args:
        site: 书籍网站配置
        page_url: 要抓取的地址
        proxy_config: 代理配置 {'enabled': bool, 'proxy_url': str}

    Returns:
        Optional[str]: 页面内容，失败返回 None
    """
    parser_name = (site.get('parser') or '').strip()
    if parser_name:
        try:
            from src.spiders import create_parser
            parser = create_parser(
                parser_name,
                proxy_config,
                site.get('name'),
                site.get('url'),
            )
            html = parser._get_url_content(page_url)
            if html:
                logger.info(f"通过解析器 {parser_name} 成功获取页面: {page_url}")
                return html
        except Exception as e:
            logger.warning(f"使用解析器 {parser_name} 获取页面失败，回退到 requests: {e}")

    return _fetch_with_requests(page_url, proxy_config)


def _fetch_with_requests(page_url: str,
                         proxy_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """使用 requests 抓取页面（解析器不可用时的回退方案）"""
    try:
        import requests
    except ImportError:
        logger.error("requests 未安装，无法抓取页面")
        return None

    proxies = None
    if proxy_config and proxy_config.get('enabled'):
        proxy_url = proxy_config.get('proxy_url') or ''
        if proxy_url:
            proxies = {'http': proxy_url, 'https': proxy_url}

    try:
        response = requests.get(
            page_url,
            headers=_REQUEST_HEADERS,
            timeout=(15, 30),
            proxies=proxies,
        )
        if response.status_code != 200:
            logger.warning(f"抓取页面返回状态码 {response.status_code}: {page_url}")
            return None
        # 修正编码，避免中文乱码
        try:
            response.encoding = response.apparent_encoding or response.encoding or 'utf-8'
        except Exception:
            response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        logger.error(f"抓取页面失败 {page_url}: {e}")
        return None


def _parse_json_items(content: str) -> Optional[List[Any]]:
    """
    尝试把内容按 JSON 接口解析出条目列表

    支持顶层为数组，或对象里 data/list/items 等常见字段为数组的情况。

    Args:
        content: 抓取到的内容

    Returns:
        Optional[List[Any]]: 条目列表；不是 JSON 时返回 None
    """
    stripped = (content or '').lstrip()
    # 仅当内容以 [ 或 { 开头时才尝试按 JSON 解析
    if not stripped or stripped[0] not in '[{' :  # noqa: E203
        return None
    try:
        data = json.loads(stripped)
    except (ValueError, TypeError):
        return None

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in _JSON_LIST_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                return value
        # 退而求其次，取第一个数组型字段
        for value in data.values():
            if isinstance(value, list):
                return value
    return None


def extract_links(html: str, base_url: str, selector: str = '') -> List[Dict[str, str]]:
    """
    从页面 HTML 中提取链接

    指定了 selector 时只在该区域内取链接：
      - 若选择器命中的元素本身就是 <a>，直接取它
      - 否则取该元素内「第一个」<a>（如 ul.update li 中首个a才是书籍链接，
        后面的a通常是作者/分类/章节）
    未指定 selector 时取页面上所有 <a>。

    Args:
        html: 页面 HTML
        base_url: 用于把相对地址补全为绝对地址的基准 URL
        selector: 可选的 CSS 选择器，用于限定抓取区域

    Returns:
        List[Dict[str, str]]: 每条含 url / text / title / html，已按 url 去重
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.error("beautifulsoup4 未安装，无法解析页面链接")
        return []

    soup = BeautifulSoup(html, 'html.parser')

    if selector.strip():
        try:
            matched = soup.select(selector.strip())
        except Exception as e:
            raise AutoCrawlError(f"CSS选择器无法解析 ({selector}): {e}") from e

        targets: List[Any] = []
        for element in matched:
            if element.name == 'a':
                targets.append(element)
            else:
                # 容器内取第一个 <a>
                first_a = element.find('a')
                if first_a is not None:
                    targets.append(first_a)
        logger.debug(f"选择器 {selector} 命中 {len(matched)} 个元素，取到 {len(targets)} 个链接")
    else:
        targets = soup.find_all('a', href=True)

    links: List[Dict[str, str]] = []
    seen = set()

    for tag in targets:
        href = str(tag.get('href') or '').strip()
        if not href:
            continue
        if href.lower().startswith(_SKIP_HREF_PREFIXES):
            continue

        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)

        links.append({
            'url': url,
            'text': str(tag.get_text(strip=True) or ''),
            'title': str(tag.get('title') or '').strip(),
            'html': str(tag)[:2000],
        })

    return links


def _json_item_to_ctx(item: Any, page_url: str) -> Optional[Dict[str, Any]]:
    """把 JSON 接口的一个条目转换成规则可用的上下文"""
    if not isinstance(item, dict):
        return None

    # 标题：优先常见字段名，并去掉其中可能夹带的 HTML 标签
    raw_text = ''
    for key in ('subject', 'title', 'name', 'bookname', 'novelname'):
        if item.get(key) is not None:
            raw_text = str(item[key])
            break
    text = _HTML_TAG_RE.sub('', raw_text).strip()

    url = ''
    for key in ('url', 'link', 'href'):
        if item.get(key):
            url = str(item[key])
            break

    return {
        'item': item,
        'url': url,
        'text': text,
        'text_len': len(text),
        'title': text,
        'html': '',
    }


def _compile_rule(rule: str,
                  params: Sequence[str] = ITEM_RULE_PARAMS) -> Optional[Callable[[Dict[str, Any]], Any]]:
    """
    把规则文本编译为可调用对象

    优先按「单行表达式」编译；若语法不通，则按「多行函数体」编译
    （此时规则内部可使用 return）。

    Args:
        rule: 规则文本
        params: 多行模式下函数可用的参数名

    Returns:
        Optional[Callable]: 接收上下文并返回判定结果的函数；规则为空返回 None

    Raises:
        AutoCrawlError: 规则语法错误
    """
    stripped = (rule or '').strip()
    if not stripped:
        return None

    # 1) 单行表达式
    try:
        code = compile(stripped, '<auto_crawl_rule>', 'eval')

        def run_expr(ctx: Dict[str, Any]) -> Any:
            return eval(code, {'__builtins__': _SAFE_BUILTINS}, ctx)  # noqa: S307

        return run_expr
    except SyntaxError:
        pass

    # 2) 多行函数体（允许使用 return）
    body = "\n".join("    " + line for line in stripped.splitlines())
    signature = ", ".join(params)
    source = f"def __rule({signature}):\n{body}\n"
    namespace: Dict[str, Any] = {}
    try:
        exec(compile(source, '<auto_crawl_rule>', 'exec'),  # noqa: S102
             {'__builtins__': _SAFE_BUILTINS}, namespace)
    except SyntaxError as e:
        raise AutoCrawlError(f"规则语法错误: {e}") from e

    func = namespace.get('__rule')
    if func is None:
        return None

    def run_func(ctx: Dict[str, Any]) -> Any:
        kwargs = {name: ctx.get(name) for name in params}
        return func(**kwargs)

    return run_func


def collect_book_urls(site: Dict[str, Any],
                      proxy_config: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    自动爬取的核心入口：抓取页面/接口 -> 按规则过滤 -> 返回符合规则的结果

    自动识别返回内容是 JSON 接口还是 HTML 页面；若配置了下一页规则，
    则按最大页数逐页抓取。只返回结果，不提取书籍ID；书籍ID由爬取管理调用
    novel_id_extractor.extract_novel_ids() 统一提取。

    Args:
        site: 书籍网站配置（需含 auto_crawl_url，可选 auto_crawl_rule /
              auto_crawl_pages / auto_crawl_next_rule）
        proxy_config: 代理配置

    Returns:
        List[str]: 去重后的结果列表（链接或书籍ID），保持抓取顺序

    Raises:
        AutoCrawlError: 未配置页面地址、首页抓取失败或规则语法错误
    """
    page_url = (site.get('auto_crawl_url') or '').strip()
    rule = (site.get('auto_crawl_rule') or '').strip()
    next_rule = (site.get('auto_crawl_next_rule') or '').strip()
    max_pages = _to_int(site.get('auto_crawl_pages'), 1)
    content_format = (site.get('auto_crawl_format') or FORMAT_AUTO).strip().lower()
    selector = (site.get('auto_crawl_selector') or '').strip()

    if not page_url:
        raise AutoCrawlError('未配置自动爬取页面地址')

    rule_func = _compile_rule(rule)
    next_func = _compile_rule(next_rule, NEXT_RULE_PARAMS) if next_rule else None

    def extract_id(url: str) -> Optional[str]:
        """规则可用：用统一提取器尝试取书籍ID（取不到通常意味着不是书籍页）"""
        return extract_novel_id_from_url(url, site)

    results: List[str] = []
    seen = set()
    current_url = page_url

    pages_done = 0
    for page in range(1, max_pages + 1):
        pages_done = page
        content = fetch_page_html(site, current_url, proxy_config)
        if not content:
            if page == 1:
                raise AutoCrawlError('获取自动爬取页面失败')
            logger.warning(f"第 {page} 页抓取失败，提前结束分页: {current_url}")
            break

        # 按配置的数据格式解析；未指定时自动识别（先 JSON 后 HTML）
        json_items = None if content_format == FORMAT_HTML else _parse_json_items(content)
        if json_items is not None:
            is_json = True
            raw_items = [i for i in json_items if isinstance(i, dict)]
        else:
            is_json = False
            if content_format == FORMAT_JSON:
                # 明确要求JSON接口却拿到非JSON内容（如误填了HTML页面、或接口返回错误页），
                # 此时若回退解析HTML会把页面上的推荐链接当成书籍，必须直接报错
                raise AutoCrawlError(
                    '已指定数据格式为 JSON 接口，但返回内容不是 JSON。'
                    '请检查「自动爬取页面」是否为接口地址（而非书籍列表HTML页面）'
                )
            raw_items = extract_links(content, current_url, selector)

        logger.info(
            f"第 {page}/{max_pages} 页 {current_url} 解析到 {len(raw_items)} 个条目"
            f"（{'JSON接口' if is_json else 'HTML链接'}）"
        )

        for raw in raw_items:
            try:
                if is_json:
                    ctx = _json_item_to_ctx(raw, current_url)
                    if ctx is None:
                        continue
                else:
                    ctx = {
                        'item': raw,
                        'url': raw['url'],
                        'text': raw['text'],
                        'text_len': len(raw['text']),
                        'title': raw['title'],
                        'html': raw['html'],
                    }
                ctx['page_url'] = current_url
                ctx['page'] = page
                ctx['re'] = re
                ctx['extract_id'] = extract_id

                if rule_func is None:
                    # 无规则：HTML模式保留链接；JSON模式仅在条目自带链接时保留
                    target = str(ctx['url'] or '')
                else:
                    result = rule_func(ctx)
                    if result is None or result is False:
                        continue
                    if result is True:
                        target = str(ctx['url'] or '')
                    else:
                        # 规则返回字符串：链接或书籍ID，交由爬取管理判定
                        target = str(result).strip()
            except AutoCrawlError:
                raise
            except Exception as e:
                # 单条目的规则异常不影响其余条目
                logger.warning(f"规则执行异常，跳过条目: {e}")
                continue

            if not target or target in seen:
                continue
            seen.add(target)
            results.append(target)

        # 计算下一页
        if next_func is None or page >= max_pages:
            break
        try:
            next_url = next_func({
                'items': raw_items,
                'page_url': current_url,
                'page': page,
                're': re,
                'url': current_url,
            })
        except Exception as e:
            logger.warning(f"下一页规则执行异常，提前结束分页: {e}")
            break

        if not next_url or not isinstance(next_url, str):
            break
        next_url = next_url.strip()
        if not next_url or next_url == current_url:
            break
        current_url = next_url

    logger.info(f"自动爬取共抓取 {pages_done} 页，规则保留 {len(results)} 个结果")
    return results
