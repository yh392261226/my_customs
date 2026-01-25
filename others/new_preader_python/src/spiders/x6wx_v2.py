"""
x6wx.com 小说网站解析器
继承自 BaseParser，使用属性配置实现
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class X6wxParser(BaseParser):
    """x6wx.com 小说解析器"""

    # 基本信息
    name = "x6wx.com"
    description = "x6wx.com 小说解析器（短篇）"
    base_url = "https://x6wx.com"

    # 正则表达式配置
    title_reg = [
        r'<div[^>]*class="detail_title"[^>]*>\s*(.*?)\s*</div>'
    ]

    # 内容正则表达式 - 使用贪婪模式匹配整个article-content div
    # 需要匹配到最后的</div>闭合标签，避免因为子div导致内容截断
    content_reg = [
        r'<div[^>]*class="article-content"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>',
        r'<div[^>]*class="article-content"[^>]*>(.*?)(?=</div>\s*</div>\s*</div>\s*</div>|$)'
    ]

    # 支持的书籍类型
    book_type = ["短篇"]

    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]

    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        格式: https://x6wx.com/{category}/{id}.html

        Args:
            novel_id: 小说ID，格式为 category/id (例如: renqishunv/73359)

        Returns:
            小说URL
        """
        return f"{self.base_url}/{novel_id}.html"

    def _detect_book_type(self, content: str) -> str:
        """
        检测书籍类型
        对于 x6wx.com 网站，所有内容都是短篇

        Args:
            content: 页面内容

        Returns:
            书籍类型
        """
        return "短篇"

    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        重写正则提取方法，针对x6wx.com使用特殊处理
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
    parser = X6wxParser()

    # 测试单篇小说
    try:
        novel_id = "renqishunv/73359"  # 示例ID
        novel_content = parser.parse_novel_detail(novel_id)
        file_path = parser.save_to_file(novel_content, "novels")
        print(f"小说已保存到: {file_path}")
    except Exception as e:
        logger.error(f"抓取失败: {e}")
