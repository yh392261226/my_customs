"""
xx-book.com 小说网站解析器
继承自 BaseParser，使用属性配置实现
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class XxbookParser(BaseParser):
    """xx-book.com 小说解析器"""

    # 基本信息
    name = "xx-book.com"
    description = "xx-book.com 小说解析器（短篇）"
    base_url = "https://xx-book.com"

    # 正则表达式配置
    title_reg = [
        r'<h1[^>]*class="entry-title"[^>]*>\s*(.*?)\s*</h1>'
    ]

    # 内容正则表达式 - 使用贪婪模式匹配整个entry-content div
    # 需要匹配到最后的</div>闭合标签，避免因为子div导致内容截断
    content_reg = [
        r'<div[^>]*class="entry-content"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>',
        r'<div[^>]*class="entry-content"[^>]*>(.*?)(?=</div>\s*</div>\s*</div>\s*</div>|$)'
    ]

    # 支持的书籍类型
    book_type = ["短篇"]

    # 处理函数配置
    after_crawler_func = [
        "_clean_specific_content",  # 清理特定内容
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]

    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        格式: https://xx-book.com/?p={id}

        Args:
            novel_id: 小说ID（纯数字）

        Returns:
            小说URL
        """
        return f"{self.base_url}/?p={novel_id}"

    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型
        对于 xx-book.com 网站，所有内容都是短篇

        Args:
            content: 页面内容

        Returns:
            书籍类型
        """
        return "短篇"

    def _clean_specific_content(self, content: str) -> str:
        """
        清理特定的内容
        先清理掉内容中的 <span class="d-none">book18.org</span>

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        if not content:
            return content

        # 清理掉 <span class="d-none">book18.org</span> 标签
        content = re.sub(r'<span[^>]*class="d-none"[^>]*>book18\.org</span>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'book18\.org', '', content, flags=re.IGNORECASE)

        return content

    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        重写正则提取方法，针对xx-book.com使用特殊处理
        确保能正确提取包含嵌套div的内容

        Args:
            content: 要提取的内容
            regex_list: 正则表达式列表

        Returns:
            提取的内容
        """
        for regex in regex_list:
            try:
                match = re.search(regex, content, re.IGNORECASE | re.DOTALL)
                if match:
                    extracted = match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip()
                    if extracted:  # 确保内容不是空的
                        return extracted
            except Exception as e:
                logger.warning(f"正则匹配失败: {regex}, 错误: {e}")
                continue
        return ""


# 使用示例
if __name__ == "__main__":
    parser = XxbookParser()

    # 测试单篇小说
    try:
        novel_id = "21743"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
