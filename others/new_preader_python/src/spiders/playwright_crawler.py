"""
Playwright 爬虫工具类
专门用于处理 Cloudflare Turnstile 等高级反爬虫机制
"""

import re
import time
import asyncio
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PlaywrightCrawler:
    """Playwright 爬虫工具类"""
    
    def __init__(self, proxy_config: Optional[dict] = None, headless: bool = True):
        """
        初始化 Playwright 爬虫
        
        Args:
            proxy_config: 代理配置
            headless: 是否无头模式
        """
        self.proxy_config = proxy_config or {'enabled': False, 'proxy_url': ''}
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    async def init_browser(self):
        """初始化浏览器"""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            
            # 配置浏览器选项
            browser_options = {
                'headless': self.headless,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-images',
                    '--window-size=1920,1080',
                    '--ignore-certificate-errors'
                ]
            }
            
            # 设置代理
            if self.proxy_config.get('enabled', False):
                proxy_url = self.proxy_config.get('proxy_url', '')
                if proxy_url:
                    # 正确的代理配置格式
                    browser_options['proxy'] = {
                        'server': proxy_url
                    }
            
            self.browser = await self.playwright.chromium.launch(**browser_options)
            
            # 创建上下文
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            # 设置额外的请求头
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            self.page = await self.context.new_page()
            
            logger.info("Playwright 浏览器初始化成功")
            
        except ImportError:
            logger.warning("playwright 库未安装，无法使用 Playwright 爬虫")
            raise
        except Exception as e:
            logger.error(f"Playwright 浏览器初始化失败: {e}")
            raise
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            logger.info("Playwright 浏览器已关闭")
        except Exception as e:
            logger.warning(f"关闭 Playwright 浏览器时出错: {e}")
    
    async def get_page_content(self, url: str, timeout: int = 60) -> Optional[str]:
        """
        使用 Playwright 获取页面内容
        
        Args:
            url: 目标URL
            timeout: 超时时间（秒）
            
        Returns:
            页面内容或None
        """
        if not self.page:
            await self.init_browser()
        
        try:
            # 设置超时
            self.page.set_default_timeout(timeout * 1000)  # 转换为毫秒
            
            # 访问页面
            await self.page.goto(url, wait_until='domcontentloaded')
            
            # 检查是否有 Cloudflare Turnstile 验证
            if await self._detect_cloudflare_turnstile():
                logger.info(f"检测到 Cloudflare Turnstile 验证，尝试绕过: {url}")
                await self._bypass_cloudflare_turnstile()
            
            # 检查是否有其他反爬虫机制
            if await self._detect_anti_bot():
                logger.info(f"检测到反爬虫机制，尝试模拟人类行为: {url}")
                await self._simulate_human_behavior()
            
            # 等待页面完全加载
            await self.page.wait_for_load_state('networkidle')
            
            # 获取页面内容
            content = await self.page.content()
            
            logger.info(f"Playwright 成功获取页面内容: {url}")
            return content
            
        except Exception as e:
            logger.warning(f"Playwright 获取页面内容失败: {url}, 错误: {e}")
            return None
    
    async def _detect_cloudflare_turnstile(self) -> bool:
        """
        检测是否存在 Cloudflare Turnstile 验证
        
        Returns:
            是否存在 Turnstile 验证
        """
        try:
            # 检测 Turnstile 相关的元素
            turnstile_selectors = [
                '[data-sitekey]',
                '.cf-turnstile',
                '#cf-turnstile',
                '[data-cf-turnstile]',
                'iframe[src*="challenges.cloudflare.com"]',
                'iframe[src*="turnstile"]'
            ]
            
            for selector in turnstile_selectors:
                if await self.page.query_selector(selector):
                    return True
            
            # 检测 Turnstile JavaScript
            turnstile_scripts = await self.page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    return scripts.some(script => 
                        script.src.includes('turnstile') || 
                        script.textContent.includes('turnstile') ||
                        script.textContent.includes('challenges.cloudflare.com')
                    );
                }
            """)
            
            return turnstile_scripts
            
        except Exception as e:
            logger.warning(f"检测 Cloudflare Turnstile 时出错: {e}")
            return False
    
    async def _bypass_cloudflare_turnstile(self) -> bool:
        """
        尝试绕过 Cloudflare Turnstile 验证
        
        Returns:
            是否成功绕过
        """
        try:
            # 等待 Turnstile iframe 加载
            await self.page.wait_for_timeout(5000)
            
            # 尝试点击 "I'm human" 或类似按钮
            human_selectors = [
                '[aria-label*="human"]',
                '[title*="human"]',
                'button:has-text("Verify")',
                'button:has-text("Human")',
                'button:has-text("I\'m human")',
                'button:has-text("Verify you are human")'
            ]
            
            for selector in human_selectors:
                try:
                    await self.page.click(selector, timeout=5000)
                    logger.info("点击了验证按钮")
                    await self.page.wait_for_timeout(3000)
                    return True
                except:
                    continue
            
            # 如果无法点击按钮，尝试等待自动验证完成
            logger.info("等待 Cloudflare Turnstile 自动验证...")
            
            # 最多等待 30 秒
            for _ in range(30):
                current_url = self.page.url
                if 'challenges.cloudflare.com' not in current_url:
                    logger.info("Cloudflare Turnstile 验证可能已完成")
                    return True
                await self.page.wait_for_timeout(1000)
            
            logger.warning("Cloudflare Turnstile 验证超时")
            return False
            
        except Exception as e:
            logger.warning(f"绕过 Cloudflare Turnstile 时出错: {e}")
            return False
    
    async def _detect_anti_bot(self) -> bool:
        """
        检测是否存在其他反爬虫机制
        
        Returns:
            是否存在反爬虫机制
        """
        try:
            # 检测常见的反爬虫标志
            anti_bot_indicators = [
                # JavaScript 检测
                await self.page.evaluate("""
                    () => {
                        return navigator.webdriver === true ||
                               window.__webdriver_evaluate ||
                               window.__selenium_evaluate ||
                               window.__webdriver_script_fn ||
                               window.__webdriver_script_func ||
                               window.__webdriver_script_function;
                    }
                """),
                
                # 检查是否有验证码
                await self.page.evaluate("""
                    () => {
                        const captchaSelectors = [
                            '.g-recaptcha',
                            '#recaptcha',
                            '.h-captcha',
                            '.cf-captcha',
                            '[data-sitekey]'
                        ];
                        return captchaSelectors.some(selector => document.querySelector(selector));
                    }
                """)
            ]
            
            return any(anti_bot_indicators)
            
        except Exception as e:
            logger.warning(f"检测反爬虫机制时出错: {e}")
            return False
    
    async def _simulate_human_behavior(self):
        """模拟人类浏览行为"""
        try:
            # 随机移动鼠标
            await self._random_mouse_movements()
            
            # 随机滚动页面
            await self._random_scrolling()
            
            # 随机等待时间
            await self.page.wait_for_timeout(2000 + int(time.time() * 1000) % 3000)
            
        except Exception as e:
            logger.warning(f"模拟人类行为时出错: {e}")
    
    async def _random_mouse_movements(self):
        """随机移动鼠标"""
        try:
            # 获取页面尺寸
            viewport = await self.page.evaluate("""
                () => {
                    return {
                        width: window.innerWidth,
                        height: window.innerHeight
                    };
                }
            """)
            
            # 随机移动鼠标几次
            for _ in range(3):
                x = int(time.time() * 1000) % viewport['width']
                y = int(time.time() * 1000) % viewport['height']
                await self.page.mouse.move(x, y)
                await self.page.wait_for_timeout(500 + int(time.time() * 1000) % 1000)
                
        except Exception as e:
            logger.warning(f"随机移动鼠标时出错: {e}")
    
    async def _random_scrolling(self):
        """随机滚动页面"""
        try:
            # 随机滚动几次
            for _ in range(2):
                scroll_amount = 100 + (int(time.time() * 1000) % 500)
                await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await self.page.wait_for_timeout(1000 + int(time.time() * 1000) % 2000)
                
        except Exception as e:
            logger.warning(f"随机滚动页面时出错: {e}")
    
    def get_content_sync(self, url: str, timeout: int = 60) -> Optional[str]:
        """
        同步版本的获取页面内容方法
        
        Args:
            url: 目标URL
            timeout: 超时时间（秒）
            
        Returns:
            页面内容或None
        """
        try:
            return asyncio.run(self.get_page_content(url, timeout))
        except Exception as e:
            logger.warning(f"同步获取页面内容失败: {url}, 错误: {e}")
            return None


class PlaywrightManager:
    """Playwright 管理器，用于管理多个爬虫实例"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'crawlers'):
            self.crawlers = {}
    
    def get_crawler(self, proxy_config: Optional[Dict[str, Any]] = None, headless: bool = True) -> PlaywrightCrawler:
        """
        获取或创建 Playwright 爬虫实例
        
        Args:
            proxy_config: 代理配置
            headless: 是否无头模式
            
        Returns:
            PlaywrightCrawler 实例
        """
        key = f"{str(proxy_config)}_{headless}"
        
        if key not in self.crawlers:
            self.crawlers[key] = PlaywrightCrawler(proxy_config, headless)
        
        return self.crawlers[key]
    
    async def cleanup(self):
        """清理所有爬虫实例"""
        for crawler in self.crawlers.values():
            try:
                await crawler.close()
            except Exception as e:
                logger.warning(f"清理爬虫实例时出错: {e}")
        
        self.crawlers.clear()


# 工具函数
def detect_cloudflare_turnstile_in_content(content: str) -> bool:
    """
    在页面内容中检测 Cloudflare Turnstile
    
    Args:
        content: 页面内容
        
    Returns:
        是否存在 Turnstile 验证
    """
    turnstile_patterns = [
        r'challenges\.cloudflare\.com',
        r'cf-turnstile',
        r'data-sitekey',
        r'turnstile\.cloudflare\.com'
    ]
    
    for pattern in turnstile_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    return False


def get_playwright_content(url: str, proxy_config: Optional[Dict[str, Any]] = None, 
                          timeout: int = 60, headless: bool = True) -> Optional[str]:
    """
    便捷函数：使用 Playwright 获取页面内容
    
        Args:
            url: 目标URL
            proxy_config: 代理配置
            timeout: 超时时间
            headless: 是否无头模式
            
        Returns:
            页面内容或None
        """
    manager = PlaywrightManager()
    crawler = manager.get_crawler(proxy_config, headless)
    
    try:
        return crawler.get_content_sync(url, timeout)
    except Exception as e:
        logger.error(f"获取页面内容失败: {url}, 错误: {e}")
        return None