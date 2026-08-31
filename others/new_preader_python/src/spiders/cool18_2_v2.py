"""
cool18.com 书库(book)解析器 - 基于配置驱动版本
继承自 BaseParser，专门解析 cool18.com 的「书库」页面：

    https://www.cool18.com/bbs4/index.php?app=book&act=bookview&cid=6482

与 cool18_v2.py（论坛帖 threadview）的区别：
  - 标题在 <font size=6><b>标题</b></font> 或 <title> 中
  - 正文位于 <!--bodybegin--> 与 <!--bodyend--> 之间的 <pre> 内
  - 正文用 <br> / <p> 作换行，并夹带与背景同色的隐形水印 <font color=#E6E6DD>cool18.com</font>
  - 需要保留段落换行、剔除水印
"""

import re

from src.utils.logger import get_logger
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser

logger = get_logger(__name__)


class Cool18BookParser(BaseParser):

    """cool18.com 书库(book)解析器 - 配置驱动版本"""

    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器

        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)

    # 基本信息
    name = "cool18_2.com"
    description = "cool18.com 书库(book)解析器"
    base_url = "https://www.cool18.com"

    # 标题正则：优先取 <font size=6><b>标题</b></font>，
    # 其次去掉 <title> 中 " - cool18.com 书库" 后缀，最后兜底取 <title>
    title_reg = [
        r'<font[^>]*size=6[^>]*>\s*<b>(.*?)</b>',
        r'<title>(.*?)\s*-\s*cool18\.com\s*书库</title>',
        r'<title>(.*?)</title>'
    ]

    # 内容正则：书库正文在 <!--bodybegin--> 与 <!--bodyend--> 之间
    content_reg = [
        r'<!--bodybegin-->(.*?)<!--bodyend-->',
        r'<pre[^>]*>(.*?)</pre>'
    ]

    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]

    # 处理函数配置：仅使用书库专用清洗
    after_crawler_func = [
        "_clean_book_content"
    ]

    def get_novel_url(self, novel_id: str) -> str:
        """
        重写URL生成方法，适配 cool18.com 书库(book)的URL格式

        支持以下输入：
          - 完整 URL：原样返回
          - 含 cid= 的查询串：提取 cid 构造书库 URL
          - 前缀形式：book:6482
          - 纯数字：视为书库 cid

        Args:
            novel_id: 小说ID或URL

        Returns:
            小说URL
        """
        if not novel_id:
            return self.base_url

        s = str(novel_id).strip()

        # 完整 URL 直接返回（兼容粘贴完整书库链接）
        if s.startswith("http://") or s.startswith("https://"):
            return s

        # 含 cid= 的查询串
        if "cid=" in s:
            m = re.search(r"cid=(\d+)", s)
            if m:
                return f"{self.base_url}/bbs4/index.php?app=book&act=bookview&cid={m.group(1)}"

        # 前缀形式 book:6482
        if s.lower().startswith("book:"):
            cid = s.split(":", 1)[1].strip()
            if cid:
                return f"{self.base_url}/bbs4/index.php?app=book&act=bookview&cid={cid}"

        # 纯数字默认按书库 cid 处理
        return f"{self.base_url}/bbs4/index.php?app=book&act=bookview&cid={s}"

    def _extract_novel_id_from_url(self, url: str) -> str:
        """
        从书库URL中提取 cid 作为小说ID

        Args:
            url: 页面URL

        Returns:
            小说ID（cid）
        """
        m = re.search(r"cid=(\d+)", url)
        if m:
            return m.group(1)
        m = re.search(r"tid=(\d+)", url)
        if m:
            return m.group(1)
        return super()._extract_novel_id_from_url(url)

    def _detect_book_type(self, content: str) -> str:
        """
        书库内容均为单篇，返回短篇

        Args:
            content: 页面内容

        Returns:
            书籍类型
        """
        return "短篇"

    def _clean_book_content(self, content: str) -> str:
        """
        书库正文清洗：
          1. 移除与背景同色的隐形水印 <font ...>cool18.com</font>
          2. 将 <br> / <p> 转换为换行，保留段落结构
          3. 移除其余 HTML 标签
          4. 解码 HTML 实体
          5. 收敛多余空行

        Args:
            content: 原始内容（bodybegin/bodyend 之间的 HTML）

        Returns:
            清洗后的纯文本
        """
        import html

        if not content:
            return ""

        # 1. 移除隐形水印（背景色 #E6E6DD 的同色小字）
        content = re.sub(r"<font[^>]*>cool18\.com</font>", "", content, flags=re.IGNORECASE)

        # 2. 换行处理
        content = re.sub(r"<br\s*/?>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"</?p[^>]*>", "\n", content, flags=re.IGNORECASE)

        # 3. 移除其余 HTML 标签
        content = re.sub(r"<[^>]+>", "", content)

        # 4. 解码 HTML 实体
        content = html.unescape(content)

        # 5. 收敛多余空行（保留段落间单个空行），并去除行尾空白
        content = re.sub(r"[ \t]+\n", "\n", content)
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip()

    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表页 - 书库不需要列表页解析

        Args:
            url: 小说列表页URL

        Returns:
            小说信息列表
        """
        return []


# 使用示例
if __name__ == "__main__":
    parser = Cool18BookParser()

    try:
        novel_id = "6482"  # 书库 cid
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"书库小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"书库抓取失败: {e}")
