"""
sis001.com 小说网站解析器 - 基于配置驱动版本
继承自 BaseParser,使用属性配置实现
Discuz论坛系统
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Sis001Parser(BaseParser):
    """sis001.com 小说解析器 - 配置驱动版本"""

    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """初始化解析器"""
        super().__init__(proxy_config, novel_site_name)
        # 禁用SSL验证以解决可能的SSL错误
        self.session.verify = False
        # 添加特定的请求头
        self.session.headers.update({
            'Referer': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def _get_url_content(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        重写获取URL内容方法,针对sis001.com的Cloudflare保护专门处理
        策略: 提示用户手动在浏览器中访问并完成验证,然后使用浏览器cookie

        Args:
            url: 目标URL
            max_retries: 最大重试次数

        Returns:
            页面内容或None
        """
        # sis001.com需要人工交互才能通过Cloudflare验证
        logger.warning("=" * 60)
        logger.warning(f"sis001.com检测到Cloudflare保护")
        logger.warning(f"方案1: 使用Playwright尝试绕过(可能失败)")
        logger.warning(f"方案2: 手动在浏览器中完成验证")
        logger.warning(f"  如果想在现有浏览器中使用,请启动Chrome时添加:")
        logger.warning(f"  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
        logger.warning(f"  然后在浏览器中访问: {url}")
        logger.warning(f"  完成验证后再运行爬虫")
        logger.warning("=" * 60)

        # 尝试从浏览器获取cookies
        cookies = self._try_get_browser_cookies(url)
        if cookies:
            logger.info(f"成功获取到 {len(cookies)} 个cookies")
            # 使用cookies请求
            content = self._fetch_with_cookies(url, cookies)
            if content and self._is_valid_content(content):
                logger.info(f"使用浏览器cookies成功获取内容")
                return content
            else:
                logger.warning(f"使用浏览器cookies获取内容失败")

        # 如果没有获取到cookies或请求失败,尝试Playwright
        try:
            logger.info(f"尝试使用Playwright访问: {url}")
            content = self._get_url_content_with_playwright_sis001(url, timeout=120)
            if content:
                logger.info(f"Playwright成功获取内容: {url}")
                # 检查内容是否有效(不是错误页面)
                if self._is_valid_content(content):
                    return content
                else:
                    logger.warning(f"Playwright获取的内容无效(可能是错误页面): {url}")
        except Exception as e:
            logger.warning(f"Playwright访问失败: {e}")

        # 回退到基类方法
        return super()._get_url_content(url, max_retries)

    def _try_get_browser_cookies(self, url: str) -> list:
        """
        尝试从浏览器获取cookies (已废弃,使用_get_chrome_cookies)

        Args:
            url: 目标URL

        Returns:
            cookies列表
        """
        return self._get_chrome_cookies("www.sis001.com")

    def _get_chrome_cookies(self, domain: str) -> list:
        """
        从Chrome浏览器读取指定域名的cookies

        Args:
            domain: 域名,如 "www.sis001.com"

        Returns:
            cookies列表
        """
        import os
        import sqlite3
        import json
        from pathlib import Path

        try:
            # macOS Chrome cookies 位置
            chrome_profile = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")
            cookies_file = os.path.join(chrome_profile, "Cookies")

            if not os.path.exists(cookies_file):
                logger.warning(f"Chrome cookies文件不存在: {cookies_file}")
                return []

            # 复制cookies文件到临时目录(因为Chrome可能正在使用这个文件)
            import tempfile
            import shutil
            temp_dir = tempfile.mkdtemp()
            temp_cookies = os.path.join(temp_dir, "Cookies")
            shutil.copy2(cookies_file, temp_cookies)

            # 连接到SQLite数据库
            conn = sqlite3.connect(temp_cookies)
            cursor = conn.cursor()

            # 查询指定域名的cookies
            query = """
                SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE host_key = ? OR host_key = ?
            """

            cursor.execute(query, (domain, f".{domain}"))
            rows = cursor.fetchall()

            # 转换为Playwright需要的格式
            cookies = []
            for row in rows:
                name, value, host_key, path, expires_utc, is_secure, is_httponly = row
                # Chrome的expires_utc是WebKit格式的时间戳(1601年1月1日起的秒数)
                # 需要转换为Unix时间戳(1970年1月1日起的秒数)
                # 或者设置为-1表示会话cookie
                import time
                if expires_utc:
                    try:
                        # 转换WebKit时间戳到Unix时间戳
                        # WebKit epoch = 1601-01-01 00:00:00 UTC
                        # Unix epoch = 1970-01-01 00:00:00 UTC
                        # 差异 = 11644473600 秒 (约 369年)
                        expires = expires_utc / 1000000.0 - 11644473600
                        # 确保是未来的时间
                        if expires < time.time():
                            expires = -1
                    except:
                        expires = -1
                else:
                    expires = -1

                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': host_key,
                    'path': path,
                    'expires': expires,
                    'secure': bool(is_secure),
                    'httpOnly': bool(is_httponly)
                })

            conn.close()

            # 清理临时文件
            os.remove(temp_cookies)
            os.rmdir(temp_dir)

            logger.info(f"从Chrome读取到 {len(cookies)} 个cookies for {domain}")
            return cookies

        except Exception as e:
            logger.warning(f"读取Chrome cookies失败: {e}")
            import traceback
            logger.debug(f"错误详情: {traceback.format_exc()}")
            return []

    def _fetch_with_cookies(self, url: str, cookies: list) -> Optional[str]:
        """
        使用cookies获取页面内容

        Args:
            url: 目标URL
            cookies: cookies列表

        Returns:
            页面内容或None
        """
        try:
            # 添加cookies到session
            for cookie in cookies:
                self.session.cookies.set(cookie.get('name'), cookie.get('value'))

            # 请求页面
            response = self.session.get(url, headers=self.session.headers)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"使用cookies请求失败,状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"使用cookies请求失败: {e}")
            return None

    def _is_valid_content(self, content: str) -> bool:
        """
        检查获取的内容是否有效(不是错误页面)

        Args:
            content: 页面内容

        Returns:
            是否为有效内容
        """
        # 记录内容检查的调试信息
        content_length = len(content)
        has_turnstile = 'Cloudflare' in content
        has_error_code = 'error-code' in content
        has_ray_id = 'ray id' in content.lower()
        has_t_msgfont = 't_msgfont' in content
        has_pages = 'class="pages"' in content
        has_thread = 'thread-' in content
        has_post = 'post-' in content

        logger.info(f"内容有效性检查 - "
                   f"长度: {content_length}, "
                   f"Cloudflare: {has_turnstile}, "
                   f"error-code: {has_error_code}, "
                   f"ray id: {has_ray_id}, "
                   f"t_msgfont: {has_t_msgfont}, "
                   f"pages: {has_pages}, "
                   f"thread: {has_thread}, "
                   f"post: {has_post}")

        # 检查是否包含Cloudflare错误页面标记 (严格的错误页面)
        if has_error_code and 'error-code' in content and 'Cloudflare' in content:
            logger.warning(f"内容被识别为Cloudflare错误页面 (包含error-code)")
            return False

        # 检查是否是非常短的错误页面
        if content_length < 5000 and (has_error_code or (has_turnstile and 'Please stand by' in content)):
            logger.warning(f"内容被识别为错误页面 (长度过短: {content_length})")
            return False

        # 优先检查是否包含预期的内容标记
        if has_t_msgfont or has_pages:
            logger.info(f"内容通过验证 (包含预期标记: t_msgfont={has_t_msgfont}, pages={has_pages})")
            return True

        # 检查是否包含Discuz论坛的典型元素
        if has_thread or has_post:
            # 如果内容长度合理(大于10000字符),认为是有效内容
            # 因为某些正常页面可能也会在页脚或某个地方提到Cloudflare
            if content_length > 10000:
                logger.info(f"内容通过验证 (包含论坛标记且长度足够: {content_length})")
                return True
            else:
                logger.warning(f"内容包含论坛标记但长度不足 (长度: {content_length})")
                return False

        # 如果只是提到Cloudflare但没有错误标记,且内容长度很长,可能是正常的页面
        if has_turnstile and content_length > 20000:
            logger.info(f"内容通过验证 (包含Cloudflare但长度较长: {content_length})")
            return True

        logger.warning(f"内容被识别为无效 (缺少预期标记, 长度: {content_length})")
        return False

    def _get_url_content_with_playwright_sis001(self, url: str, timeout: int = 120) -> Optional[str]:
        """
        使用Playwright获取页面内容 - sis001.com专用版本
        增加超时时间,改进Cloudflare Turnstile等待逻辑

        Args:
            url: 目标URL
            timeout: 超时时间(秒)

        Returns:
            页面内容或None
        """
        import asyncio

        async def fetch_content():
            try:
                from playwright.async_api import async_playwright
                import time

                async with async_playwright() as p:
                    # 尝试连接到现有的Chrome浏览器实例(需要用--remote-debugging-port启动)
                    # 如果连接失败,则启动新的浏览器并使用已有的cookie
                    browser = None
                    context = None

                    # 尝试从Chrome读取cookies
                    chrome_cookies = self._get_chrome_cookies("www.sis001.com")

                    try:
                        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                        logger.info("成功连接到现有Chrome实例")
                        context = browser.contexts[0] if browser.contexts else None
                        if not context:
                            context = await browser.new_context()
                    except Exception as e:
                        logger.info(f"无法连接到现有Chrome实例,启动新浏览器: {e}")
                        # 启动浏览器 - 使用非headless模式
                        browser = await p.chromium.launch(
                            headless=False,
                            args=[
                                '--disable-blink-features=AutomationControlled',
                                '--no-sandbox',
                                '--disable-dev-shm-usage',
                                '--disable-gpu',
                                '--disable-infobars',
                                '--disable-extensions',
                                '--window-size=1920,1080',
                                '--ignore-certificate-errors',
                                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                            ]
                        )

                    # 创建或使用上下文
                    if not context:
                        context = await browser.new_context(
                            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            viewport={'width': 1920, 'height': 1080},
                            locale='zh-CN',
                            timezone_id='Asia/Shanghai',
                            color_scheme='light'
                        )

                    # 如果获取到了Chrome的cookies,添加到上下文中
                    if chrome_cookies:
                        logger.info(f"找到 {len(chrome_cookies)} 个Chrome cookies,正在添加...")
                        await context.add_cookies(chrome_cookies)

                    # 添加反检测脚本 - 更完整的反自动化检测
                    await context.add_init_script("""
                        // 修改 navigator.webdriver
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });

                        // 修改 Chrome 对象
                        window.chrome = {
                            runtime: {}
                        };

                        // 修改 permissions
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                            parameters.name === 'notifications' ?
                                Promise.resolve({ state: Notification.permission }) :
                                originalQuery(parameters)
                        );

                        // 修改 plugins
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5]
                        });

                        // 修改 languages
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['zh-CN', 'zh', 'en']
                        });
                    """)

                    page = await context.new_page()

                    # 设置默认超时
                    page.set_default_timeout(timeout * 1000)

                    try:
                        logger.info(f"开始访问页面: {url}")
                        # 访问页面 - 使用较慢的加载策略
                        await page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)

                        # 模拟人类行为:等待几秒
                        import time
                        await page.wait_for_timeout(2000 + int(time.time() * 1000) % 2000)

                        logger.info(f"页面加载完成,开始检测Cloudflare验证")

                        # 保存初始页面HTML用于调试
                        initial_content = await page.content()
                        import tempfile
                        import os
                        temp_dir = tempfile.gettempdir()
                        debug_file = os.path.join(temp_dir, 'sis001_initial.html')
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(initial_content)
                        logger.info(f"初始页面HTML已保存到: {debug_file}")

                        # 检测并处理Cloudflare Turnstile
                        has_turnstile = await self._detect_cloudflare_turnstile_playwright(page)
                        if has_turnstile:
                            logger.info(f"检测到Cloudflare Turnstile验证,开始等待验证完成")
                            await self._wait_cloudflare_turnstile_complete(page, max_wait_seconds=60)
                        else:
                            logger.info(f"未检测到Cloudflare Turnstile验证元素")

                        # 等待页面完全加载
                        logger.info(f"等待页面网络空闲")
                        try:
                            await page.wait_for_load_state('networkidle', timeout=30000)
                        except:
                            # 网络空闲超时,继续执行
                            logger.warning(f"网络空闲等待超时,继续获取内容")

                        # 检查页面是否已经加载了有效内容
                        logger.info(f"检查页面内容有效性")
                        content = await page.content()

                        # 如果内容无效,再等待一段时间
                        if not self._is_valid_content(content):
                            logger.info(f"内容无效,再等待30秒")
                            await page.wait_for_timeout(30000)
                            content = await page.content()

                            # 保存最终HTML用于调试
                            final_debug_file = os.path.join(temp_dir, 'sis001_final.html')
                            with open(final_debug_file, 'w', encoding='utf-8') as f:
                                f.write(content)
                            logger.info(f"最终页面HTML已保存到: {final_debug_file}")

                        logger.info(f"成功获取页面内容,长度: {len(content)}")
                        return content

                    finally:
                        await page.close()
                        await context.close()
                        await browser.close()

            except Exception as e:
                logger.warning(f"Playwright获取页面内容异常: {e}")
                import traceback
                logger.warning(f"异常堆栈: {traceback.format_exc()}")
                return None

        try:
            return asyncio.run(fetch_content())
        except Exception as e:
            logger.warning(f"执行异步Playwright任务失败: {e}")
            return None

    async def _detect_cloudflare_turnstile_playwright(self, page) -> bool:
        """
        检测页面是否存在Cloudflare Turnstile验证

        Args:
            page: Playwright页面对象

        Returns:
            是否存在Turnstile验证
        """
        try:
            # 检测Turnstile相关元素
            turnstile_selectors = [
                '[data-sitekey]',
                '.cf-turnstile',
                '#cf-turnstile',
                '[data-cf-turnstile]',
                'iframe[src*="challenges.cloudflare.com"]',
                'iframe[src*="turnstile"]'
            ]

            for selector in turnstile_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.info(f"检测到Turnstile元素: {selector}")
                    return True

            return False
        except Exception as e:
            logger.warning(f"检测Turnstile时出错: {e}")
            return False

    async def _wait_cloudflare_turnstile_complete(self, page, max_wait_seconds: int = 60):
        """
        等待Cloudflare Turnstile验证完成
        通过检测实际内容出现来判断,而不仅仅是URL

        Args:
            page: Playwright页面对象
            max_wait_seconds: 最大等待时间(秒)
        """
        import time
        logger.info(f"开始等待Cloudflare Turnstile验证,最多等待{max_wait_seconds}秒")

        start_time = time.time()
        check_interval = 2  # 每2秒检查一次

        while time.time() - start_time < max_wait_seconds:
            try:
                # 检查是否已经加载了有效内容
                content = await page.content()

                # 方法1: 检查Turnstile元素是否消失
                turnstile_exists = await self._detect_cloudflare_turnstile_playwright(page)

                # 方法2: 检查是否包含了我们期望的内容元素
                has_expected_content = (
                    't_msgfont' in content or
                    'class="pages"' in content or
                    'thread-' in content
                )

                # 方法3: 检查是否没有错误页面标记
                has_error = (
                    'error-code' in content or
                    ('Cloudflare' in content and 'ray id' in content.lower())
                )

                if not turnstile_exists and has_expected_content and not has_error:
                    logger.info(f"✓ Cloudflare Turnstile验证已完成 (内容已加载)")
                    return

                elapsed = int(time.time() - start_time)
                logger.info(f"等待中... ({elapsed}/{max_wait_seconds}秒) Turnstile存在: {turnstile_exists}, 有效内容: {has_expected_content}, 错误: {has_error}")

            except Exception as e:
                logger.warning(f"检查验证状态时出错: {e}")

            # 等待下一次检查
            await page.wait_for_timeout(check_interval * 1000)

        logger.warning(f"Cloudflare Turnstile验证等待超时 ({max_wait_seconds}秒)")


    # 基本信息
    name = "sis001.com"
    description = "sis001.com 小说解析器"
    base_url = "https://www.sis001.com"

    # 正则表达式配置
    # 标题在<h1></h1>或<h2></h2>标签中的文字部分
    title_reg = [
        r"<h1[^>]*>(.*?)</h1>",
        r"<h2[^>]*>(.*?)</h2>",
        r'<title>(.*?)[\s\-_]+'
    ]

    # 内容在class="t_msgfont noSelect"的div标签中,使用贪婪模式避免内容截断
    # 同时支持多种可能的class写法
    content_reg = [
        r'<div[^>]*class="t_msgfont noSelect"[^>]*>([\s\S]*?)</div>',
        r'<div[^>]*class="t_msgfont"[^>]*>([\s\S]*?)</div>',
        r'<div[^>]*class="[^"]*t_msgfont[^"]*"[^>]*>([\s\S]*?)</div>',
        r'<div[^>]*class="[^"]*noSelect[^"]*"[^>]*>([\s\S]*?)</div>',
        r'<td[^>]*class="t_f"[^>]*>([\s\S]*?)</td>',  # Discuz常见的内容单元格
        r'<div[^>]*id="[^"]*post[^"]*"[^>]*>([\s\S]*?)</div>',  # 通过id查找
    ]

    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]

    # 支持的书籍类型:多章节、单篇都有
    book_type = ["短篇", "多章节", "短篇+多章节"]

    # 分页链接正则表达式
    next_page_link_reg = [
        r'<div[^>]*class="pages"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*class="next"[^>]*>'
    ]

    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content",  # 公共基类提供的HTML清理
        "_clean_content_specific"  # 清理sis001特定内容
    ]

    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        重写基类的正则提取方法,专门处理sis001.com的内容提取

        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表

        Returns:
            提取的内容
        """
        # 检查是否是内容提取(通过比较regex_list与content_reg)
        is_content_extraction = regex_list == self.content_reg

        # 如果是内容提取,使用自定义的多div提取函数
        if is_content_extraction:
            extracted = self._extract_all_content_divs(content)
            if extracted and extracted.strip():
                return extracted

        # 使用原始的正则方法(适用于标题和其他非内容提取)
        for regex in regex_list:
            matches = re.findall(regex, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                extracted = match.strip() if isinstance(match, str) else match[0].strip() if match else ""
                if extracted:  # 确保内容不是空的
                    return extracted
        return ""

    def _extract_all_content_divs(self, html: str) -> str:
        """
        提取所有class="t_msgfont noSelect"的div标签包裹的内容
        使用贪婪模式处理嵌套div,避免内容被截断
        页面中可能存在多个这样的div,每个都包含一段内容

        Args:
            html: HTML内容

        Returns:
            提取的所有内容部分(多个div内容合并,用分隔符分开)
        """
        logger.info(f"_extract_all_content_divs: 开始提取, HTML长度: {len(html)}")

        # 尝试多种模式查找内容div
        patterns = [
            re.compile(r'<div[^>]*class="t_msgfont noSelect"[^>]*>', re.IGNORECASE),
            re.compile(r'<div[^>]*class="t_msgfont"[^>]*>', re.IGNORECASE),
            re.compile(r'<div[^>]*class="[^"]*t_msgfont[^"]*"[^>]*>', re.IGNORECASE),
            re.compile(r'<div[^>]*class="[^"]*noSelect[^"]*"[^>]*>', re.IGNORECASE),
        ]

        all_matches = []
        for pattern in patterns:
            matches = list(pattern.finditer(html))
            if matches:
                logger.info(f"找到 {len(matches)} 个匹配项 (pattern: {pattern.pattern[:50]})")
                all_matches.extend(matches)
                break  # 使用第一个成功匹配的模式

        if not all_matches:
            logger.warning("未找到任何匹配的内容div")
            # 尝试备用方案:查找包含大量文本的div
            logger.info("尝试备用方案:查找包含大量文本的div")
            div_pattern = re.compile(r'<div[^>]*>([\s\S]*?)</div>', re.IGNORECASE)
            long_divs = []
            for match in div_pattern.finditer(html):
                content = match.group(1)
                # 移除HTML标签后检查纯文本长度
                text_content = re.sub(r'<[^>]+>', '', content)
                if len(text_content) > 100:  # 至少100字符
                    long_divs.append((match, len(text_content)))

            if long_divs:
                # 选择最长的div
                long_divs.sort(key=lambda x: x[1], reverse=True)
                best_match = long_divs[0][0]
                all_matches = [best_match]
                logger.info(f"备用方案找到最长的div,文本长度: {long_divs[0][1]}")

        # 存储所有提取的内容
        all_contents: list[str] = []

        # 遍历每个t_msgfont noSelect div
        for start_match in all_matches:
            start_pos = start_match.end()

            # 使用嵌套div深度匹配来正确提取内容
            depth = 1
            pos = start_pos
            content_end = -1

            while pos < len(html) and depth > 0:
                # 查找下一个div开标签和闭标签
                next_open = html.find('<div', pos)
                next_close = html.find('</div>', pos)

                if next_close == -1:
                    break

                if next_open != -1 and next_open < next_close:
                    # 先遇到开标签
                    depth += 1
                    pos = next_open + 4  # 跳过"<div"
                else:
                    # 先遇到闭标签
                    depth -= 1
                    if depth == 0:
                        content_end = next_close
                        break
                    pos = next_close + 6  # 跳过"</div>"

            if content_end != -1:
                content = html[start_pos:content_end]
                # 清理内容
                cleaned_content = self._clean_nested_content(content)
                if cleaned_content and cleaned_content.strip():
                    all_contents.append(cleaned_content)

        # 合并所有内容,使用分隔符
        if all_contents:
            return '\n\n---\n\n'.join(all_contents)

        return ""

    def _clean_nested_content(self, content: str) -> str:
        """
        清理嵌套div中的内容,移除广告和不需要的div,保留主要文本内容

        Args:
            content: 原始嵌套内容

        Returns:
            清理后的内容
        """
        # 移除script和style标签
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)

        # 移除广告相关的div
        ad_patterns = [
            r'<div[^>]*class="cm"[^>]*>.*?</div>\s*',
            r'<form[^>]*>.*?</form>\s*',
            r'<iframe[^>]*>.*?</iframe>\s*',
        ]

        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        # 移除所有HTML标签但保留文本内容
        extracted_text = re.sub(r'<[^>]+>', '', content, flags=re.IGNORECASE)
        # 清理空白字符
        extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()

        # 处理HTML实体
        import html
        extracted_text = html.unescape(extracted_text)
        extracted_text = extracted_text.replace('\xa0', ' ')

        # 处理bbcode标签
        extracted_text = re.sub(r'\[/?[^\]]+\]', '', extracted_text)

        return extracted_text

    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法,适配sis001.com的URL格式
        URL格式: https://www.sis001.com/bbs/thread-11518015-1-1.html
        其中11518015是书籍ID,第一个1是分页,第二个1是楼层

        Args:
            novel_id: 小说ID (可能包含完整URL的格式,如 "11428469-1-1")

        Returns:
            小说URL
        """
        # 清理书籍ID,移除可能已存在的分页和楼层信息
        # 例如: "11428469-1-1" -> "11428469"
        cleaned_id = re.sub(r'-\d+-\d+$', '', novel_id)
        return f"{self.base_url}/bbs/thread-{cleaned_id}-1-1.html"

    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测,sis001.com支持多章节和单篇

        Args:
            content: 页面内容

        Returns:
            书籍类型
        """
        # 检测是否有分页
        if self._has_pagination(content):
            return "多章节"

        # 默认返回短篇
        return "短篇"

    def _has_pagination(self, content: str) -> bool:
        """
        检测是否存在分页

        Args:
            content: 页面内容

        Returns:
            是否有分页
        """
        # 检测分页div
        pagination_pattern = r'<div[^>]*class="pages"[^>]*>'
        if re.search(pagination_pattern, content, re.IGNORECASE):
            return True

        return False

    def _get_next_page_url(self, content: str, current_url: str) -> Optional[str]:
        """
        重写获取下一页URL方法,适配sis001.com的分页格式
        分页格式: <div class="pages"><em>&nbsp;14&nbsp;</em><strong>1</strong><a href="thread-11428469-2-1.html">2</a>...

        Args:
            content: 当前页面内容
            current_url: 当前页面URL

        Returns:
            下一页URL或None
        """
        # 使用配置的正则表达式提取下一页链接
        if self.next_page_link_reg:
            for pattern in self.next_page_link_reg:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    next_url = match.group(1)
                    # 构建完整URL
                    if next_url.startswith('/'):
                        return f"{self.base_url}{next_url}"
                    elif next_url.startswith('http'):
                        return next_url
                    else:
                        # 相对路径处理,需要在bbs目录下
                        base_path = current_url.rsplit('/', 1)[0]
                        return f"{base_path}/{next_url}"

        # 备用方法:查找分页div中的链接
        pagination_pattern = r'<div[^>]*class="pages"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*class="next"[^>]*>'
        match = re.search(pagination_pattern, content, re.IGNORECASE)
        if match:
            next_url = match.group(1)
            if next_url.startswith('/'):
                return f"{self.base_url}{next_url}"
            elif next_url.startswith('http'):
                return next_url
            else:
                base_path = current_url.rsplit('/', 1)[0]
                return f"{base_path}/{next_url}"

        return None

    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写单章节小说解析逻辑,适配sis001.com的特定结构

        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题

        Returns:
            小说详情信息
        """
        # 使用配置的正则提取内容
        chapter_content = self._extract_with_regex(content, self.content_reg)

        if not chapter_content:
            raise Exception("无法提取小说内容")

        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)

        # 检查内容是否有效(至少包含一些中文字符)
        if not processed_content or len(processed_content.strip()) < 50:
            raise Exception("提取的内容为空或过短")

        return {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': [{
                'chapter_number': 1,
                'title': title,
                'content': processed_content,
                'url': novel_url
            }]
        }

    def _parse_multichapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写多章节小说解析逻辑,处理有分页的书籍
        sis001.com的分页是通过thread-ID-页码-楼层.html的形式

        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题

        Returns:
            小说详情信息
        """
        # 创建小说内容
        novel_content: Dict[str, Any] = {
            'title': title,
            'author': self.novel_site_name,
            'novel_id': self._extract_novel_id_from_url(novel_url),
            'url': novel_url,
            'chapters': []
        }

        # 当前页码
        current_page = 1

        # 抓取所有页面内容
        current_url = novel_url
        while current_url:
            logger.info(f"正在爬取第 {current_page} 页: {current_url}")

            # 获取页面内容
            page_content = self._get_url_content(current_url)

            if page_content:
                # 提取当前页的章节内容
                chapter_content = self._extract_with_regex(page_content, self.content_reg)

                if chapter_content:
                    # 执行爬取后处理函数
                    processed_content = self._execute_after_crawler_funcs(chapter_content)

                    self.chapter_count += 1
                    novel_content['chapters'].append({
                        'chapter_number': self.chapter_count,
                        'title': f"第 {self.chapter_count} 页",
                        'content': processed_content,
                        'url': current_url
                    })
                    logger.info(f"✓ 第 {self.chapter_count} 页抓取成功")
                else:
                    logger.warning(f"✗ 第 {current_page} 页内容提取失败: {current_url}")
            else:
                logger.warning(f"✗ 第 {current_page} 页抓取失败: {current_url}")

            # 获取下一页URL
            current_url = self._get_next_page_url(page_content or "", current_url)
            current_page += 1

            # 页面间延迟
            import time
            time.sleep(1)

        return novel_content

    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从URL中提取小说ID
        URL格式: thread-11518015-1-1.html

        Args:
            url: 小说URL

        Returns:
            小说ID
        """
        # 匹配 thread-数字-数字-数字 格式
        match = re.search(r'thread-(\d+)-\d+-\d+', url)
        if match:
            return match.group(1)

        # 备用匹配:提取 thread- 后面的数字
        match = re.search(r'thread-(\d+)', url)
        return match.group(1) if match else "unknown"

    def _clean_content_specific(self, content: str) -> str:
        """
        清理sis001.com特定的内容干扰

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        # 首先移除script和style标签及其内容
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.IGNORECASE | re.DOTALL)

        # 移除常见的导航和广告元素
        ad_patterns = [
            r'上一章.*?下一章',
            r'返回.*?目录',
            r'本章.*?字数',
            r'更新时间.*?\d{4}-\d{2}-\d{2}',
            r'作者.*?更新时间',
            r'<div[^>]*class="[^"]*nav[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*footer[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*ad[^"]*"[^>]*>.*?</div>',
            # 移除引用、签名等特定元素
            r'<div[^>]*class="[^"]*quote[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*sign[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*avatar[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*userinfo[^"]*"[^>]*>.*?</div>',
            r'&quot;',
            r'&nbsp;',
        ]

        for pattern in ad_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        # 清理多余的空白字符
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)

        return content.strip()

    def get_homepage_meta(self, novel_id: str) -> Optional[Dict[str, str]]:
        """
        重写首页元数据获取,适配sis001.com的特定结构

        Args:
            novel_id: 小说ID

        Returns:
            包含标题、简介、状态的字典
        """
        novel_url = self.get_novel_url(novel_id)
        content = self._get_url_content(novel_url)

        if not content:
            return None

        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)

        # 提取状态
        status = self._extract_with_regex(content, self.status_reg)

        return {
            "title": title or "未知标题",
            "tags": "",
            "desc": "小说",
            "status": status or "未知状态"
        }

    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - sis001.com不需要列表页解析

        Args:
            url: 小说列表页URL

        Returns:
            小说信息列表
        """
        return []
