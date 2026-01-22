"""
CMS T7 解析器 - 整合改版后的CMS T1网站
支持多种网站结构和模板，统一解析逻辑
基于base_parser_v2实现
"""

from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse, unquote
from src.utils.logger import get_logger
from .base_parser_v2 import BaseParser
import re

logger = get_logger(__name__)

class CmsT7Parser(BaseParser):
    """CMS T7解析器 - 整合改版后的CMS T1网站"""
    
    # 基本配置
    name: str = "CMS T7通用解析器"
    description: str = "整合改版后的CMS T1网站解析器，支持多种模板结构"
    base_url: str = ""
    
# 正则表达式配置 - 支持多种模板结构
    title_reg: List[str] = [
        # 通用h1/h2/h3标签
        r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>',
        r'<h2[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h2>',
        r'<h3[^>]*>([^<]+)</h3>',
        r'<h1[^>]*>([^<]+)</h1>',
        r'<h2[^>]*>([^<]+)</h2>',
        # 特定模板的标题
        r'<title[^>]*>([^<]+)</title>',
    ]
    
    content_reg: List[str] = [
        # 优先匹配xhxs2.xyz的隐藏内容结构
        r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none;"[^>]*>(.*?)</span>',
        r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"[^>]*>(.*?)</span>',
        # 主要内容区域 - 多种模板结构
        r'<article[^>]*class="post_excerpt[^"]*"[^>]*>(.*?)</article>',
        # 处理嵌套div的art-content - 匹配到下一个顶级div或结束
        r'<div[^>]*class="art-content[^"]*"[^>]*>(.*?)(?=\s*<div[^>]*class=|\s*</div>\s*$)',
        r'<div[^>]*class="tab-panel-item[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="erx-content[^>*"[^>]*>(.*?)</div>',
        # 简化的dd标签匹配 - 适用于buya6.xyz等网站
        r'<dd[^>]*>.*?<h3[^>]*>[^<]+</h3>.*?(.*?)</dd>',
        # 备用：更宽松的dd标签匹配
        r'<dd[^>]*>.*?<h3[^>]*>.*?</h3>.*?(.*?)</dd>',
        r'<section[^>]*>.*?<dl[^>]*>.*?<h3[^>]*>[^<]+</h3>.*?<h5[^>]*>.*?</h5>.*?<p[^>]*>.*?</p>.*?</dl>',
        r'<dl[^>]*>.*?<h3[^>]*>[^<]+</h3>.*?<h5[^>]*>.*?</h5>.*?<p[^>]*>.*?</p>.*?(.*?)</dl>',
        # 通用section和div匹配
        r'<section[^>]*class="[^"]*"[^>]*>(.*?)</section>',
        r'<div[^>]*class="item-box[^>*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="page_content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*id="left"[^>]*>(.*?)</div>',
        # 备用内容区域 - 放在最后
        r'<div[^>]*class="content[^"]*"[^>]*>(.*?)</div>',
        r'<dd[^>]*>(.*?)</dd>',
        # p标签内的隐藏内容
        r'<p[^>]*>.*?<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"[^>]*>(.*?)</span>.*?</p>',
        # 优先匹配所有p标签，然后在提取后选择最长的 - 放在最后作为备选
        r'<p[^>]*>(.*?)</p>',
    ]

    # 处理函数配置
    after_crawler_func = [
        # "_extract_balanced_content",  # 使用平衡算法提取内容
        "_remove_ads",  # 广告移除
        "_convert_traditional_to_simplified" # 繁体转简体
    ]
    
    # 支持的书籍类型
    book_type: List[str] = ["短篇"]
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None, site_url: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称
            site_url: 网站URL，用于自动设置base_url
        """
        super().__init__(proxy_config, novel_site_name)
        
        # 如果提供了site_url，则自动解析并设置base_url
        if site_url:
            try:
                parsed_url = urlparse(site_url)
                self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                logger.info(f"从site_url设置base_url: {self.base_url}")
            except Exception as e:
                logger.error(f"解析site_url失败: {e}")
        
        # 设置网站名称
        if novel_site_name:
            self.novel_site_name = novel_site_name
        
        logger.info(f"初始化CMS T7解析器完成: base_url={self.base_url}, name={self.novel_site_name}")
    
    def get_novel_url(self, novel_id: str, category: str = "") -> str:
        """
        重写URL生成方法，支持多种URL格式
        
        Args:
            novel_id: 小说ID
            category: 分类（可选）
            
        Returns:
            小说URL
        """
        if category:
            # 有分类的URL格式：/{category}/{novel_id}.html
            return f"{self.base_url}/{category}/{novel_id}.html"
        else:
            # 其他网站使用通用格式
            return f"{self.base_url}/{novel_id}.html"
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，这些网站主要是短篇小说
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型
        """
        return "短篇"

    def _extract_content_universal(self, content: str) -> str:
        """
        通用内容提取方法，自动检测并处理可见开头和隐藏内容

        Args:
            content: 原始HTML内容

        Returns:
            提取的完整内容
        """
        try:
            # 第一步：提取所有可能的可见开头（P标签或art-content）
            visible_starts = []

            # 从P标签中提取可见开头
            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
            logger.info(f"找到 {len(p_matches)} 个P标签")

            for i, p_match in enumerate(p_matches):  # 检查所有P标签
                cleaned = self._clean_html_tags(p_match)

                # 过滤掉广告
                ad_keywords = ['TikTok', '成人导航', 'APP破解', '点此下载', '包你射', '香嫩少女']
                is_ad = any(keyword in cleaned for keyword in ad_keywords)

                if cleaned and not is_ad:
                    chinese_chars = len(re.findall(r'[一-龯]', cleaned))
                    if len(cleaned.strip()) > 20 and chinese_chars > 10:
                        # 收集所有可能的P标签
                        visible_starts.append(cleaned)
                        logger.info(f"P标签 #{i+1} 添加到visible_starts")
                        break

            # 如果没有从P标签中找到有效内容,尝试从div中提取
            if not visible_starts:
                div_matches = re.findall(r'<div[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
                logger.info(f"未从P标签找到有效内容,检查 {len(div_matches)} 个div标签")

                for i, div_match in enumerate(div_matches[:15]):
                    cleaned = self._clean_html_tags(div_match)
                    if cleaned and len(cleaned.strip()) > 50:
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned))
                        if chinese_chars > 20:
                            visible_starts.append(cleaned)
                            logger.info(f"DIV #{i+1} 添加到visible_starts")
                            break

            # 如果还是没有,尝试从article标签提取
            if not visible_starts:
                article_matches = re.findall(r'<article[^>]*>(.*?)</article>', content, re.DOTALL | re.IGNORECASE)
                logger.info(f"未从div找到有效内容,检查 {len(article_matches)} 个article标签")

                for i, article_match in enumerate(article_matches):
                    cleaned = self._clean_html_tags(article_match)
                    if cleaned and len(cleaned.strip()) > 50:
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned))
                        if chinese_chars > 20:
                            visible_starts.append(cleaned)
                            logger.info(f"Article #{i+1} 添加到visible_starts")
                            break

            # 如果还是没有任何可见开头,尝试从整个页面提取
            if not visible_starts and not full_visible_content:
                logger.info("无法从任何标签中提取可见内容,尝试从整个页面提取")
                # 移除所有HTML标签
                full_page_cleaned = self._clean_html_tags(content)
                # 检查清理后的内容
                if full_page_cleaned and len(full_page_cleaned.strip()) > 100:
                    chinese_chars = len(re.findall(r'[一-龯]', full_page_cleaned))
                    if chinese_chars > 50:
                        full_visible_content = full_page_cleaned
                        logger.info(f"从整个页面提取内容,长度: {len(full_visible_content)}")

            # 从art-content div中提取完整可见内容
            art_content_matches = re.findall(r'<div[^>]*class="art-content[^"]*"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
            logger.info(f"找到 {len(art_content_matches)} 个art-content div")

            full_visible_content = ""
            for i, art_match in enumerate(art_content_matches):
                cleaned = self._clean_html_tags(art_match)
                if cleaned:
                    # 检查是否包含足够的内容
                    chinese_chars = len(re.findall(r'[一-龯]', cleaned))
                    logger.info(f"art-content #{i+1}: 长度={len(cleaned)}, 中文字符={chinese_chars}, 前80字符={cleaned[:80]}")

                    # 查找编辑信息之后的内容
                    edit_marker = '本帖最后由'
                    if edit_marker in cleaned:
                        marker_pos = cleaned.find(edit_marker)
                        # 从编辑信息后面提取
                        after_marker = cleaned[marker_pos + len(edit_marker):]
                        # 提取编辑信息后的实际内容
                        content_after_edit = re.sub(r'^.*?[编辑编辑修改编辑].*?', '', after_marker, flags=re.DOTALL)
                        content_after_edit = content_after_edit.strip()

                        if len(content_after_edit) > 50:
                            full_visible_content = content_after_edit
                            logger.info(f"使用编辑后的art-content内容, 长度={len(full_visible_content)}, 前100字符={full_visible_content[:100]}")
                            break

                    # 如果没有编辑信息,但内容足够长,直接使用
                    if not full_visible_content and chinese_chars > 100:
                        full_visible_content = cleaned
                        logger.info(f"使用完整art-content内容")
                        break

            # 第二步：提取隐藏内容（在xiaoshuo_str span标签内）
            hidden_content = ""
            hidden_patterns = [
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none;"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*>(.*?)</span>',
            ]

            for i, pattern in enumerate(hidden_patterns):
                hidden_match = re.search(pattern, content, re.DOTALL)
                if hidden_match:
                    hidden_part = hidden_match.group(1)
                    cleaned_hidden = self._clean_html_tags(hidden_part)
                    if cleaned_hidden:
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned_hidden))
                        logger.info(f"隐藏内容 #{i+1}: 长度={len(cleaned_hidden)}, 中文字符={chinese_chars}, 前50字符={cleaned_hidden[:50]}")
                        if chinese_chars > 10:  # 确保有实际内容
                            hidden_content = cleaned_hidden
                            logger.info(f"选择隐藏内容 #{i+1}作为隐藏内容")
                            break

            # 第四步：根据提取的内容情况决定返回内容
            # 情况1: 只有完整可见内容，没有隐藏内容（如buya6.xyz）
            if full_visible_content and not hidden_content:
                logger.info("使用完整可见内容（无隐藏内容）")
                return full_visible_content

            # 情况2: 有完整可见内容和隐藏内容，优先使用可见内容
            if full_visible_content and hidden_content:
                logger.info(f"情况2: full_visible_content长度={len(full_visible_content)}, hidden_content长度={len(hidden_content)}")
                # 如果可见内容足够长（>500字），优先使用可见内容
                if len(full_visible_content) > 500:
                    logger.info(f"可见内容长度足够（{len(full_visible_content)}），优先使用可见内容")
                    return full_visible_content
                # 否则合并
                best_start = visible_starts[0] if visible_starts else ""
                if best_start:
                    clean_hidden = self._skip_error_start_in_hidden(best_start, hidden_content)
                    merged_content = f"{best_start}\n\n{clean_hidden}"
                    logger.info(f"合并可见开头和隐藏内容，总长度: {len(merged_content)}")
                    return merged_content
                else:
                    logger.info("使用隐藏内容（无可见开头）")
                    return hidden_content

            # 情况3: 有隐藏内容和可见开头，需要合并
            if hidden_content and visible_starts:
                # 选择最长的可见开头
                best_start = max(visible_starts, key=len)

                # 智能跳过隐藏内容中的错误开头
                clean_hidden = self._skip_error_start_in_hidden(best_start, hidden_content)

                # 合并内容
                merged_content = f"{best_start}\n\n{clean_hidden}"
                logger.info(f"合并可见开头和隐藏内容，总长度: {len(merged_content)}")
                return merged_content

            # 情况4: 只有隐藏内容
            if hidden_content:
                logger.info("只找到隐藏内容")
                return hidden_content

            # 情况5: 只有完整可见内容
            if full_visible_content:
                logger.info("使用完整可见内容")
                return full_visible_content

            # 情况6: 都没找到，返回空
            logger.warning("未找到任何有效内容")
            return ""

        except Exception as e:
            logger.error(f"通用内容提取失败: {e}")
            return ""

    def _skip_error_start_in_hidden(self, visible_start: str, hidden_content: str) -> str:
        """
        智能跳过隐藏内容中的错误开头

        通过比较可见开头和隐藏内容，判断是否需要跳过隐藏内容的前几句话

        Args:
            visible_start: 可见开头内容
            hidden_content: 隐藏的完整内容

        Returns:
            清理后的隐藏内容
        """
        try:
            # 提取可见开头的关键词（前30个字符）
            visible_keywords = re.findall(r'[一-龯]{2,}', visible_start[:30])

            # 提取隐藏内容的前几句
            hidden_lines = hidden_content.split('\n')
            hidden_start_text = '\n'.join(hidden_lines[:5])  # 前5句话

            # 策略1: 如果可见开头和隐藏开头明显不同，跳过隐藏内容的第一句
            if visible_start and len(visible_start) > 20 and len(visible_keywords) > 0:
                # 检查隐藏内容开头是否包含可见开头的关键词
                has_overlap = False
                for keyword in visible_keywords[:3]:  # 检查前3个关键词
                    if keyword in hidden_start_text:
                        has_overlap = True
                        break

                # 只有在没有重叠且可见开头确实不同时才跳过
                # 使用更严格的条件：可见开头必须在隐藏内容的前200个字符中找不到任何匹配
                if not has_overlap:
                    # 额外检查：可见开头的第一个词是否在隐藏内容的前100字符中
                    first_word = re.findall(r'[一-龯]{2,}', visible_start)
                    if first_word and first_word[0] not in hidden_content[:100]:
                        if len(hidden_lines) > 1:
                            # 跳过第一句，从第二句开始
                            # 但要保留第二句的完整性（不要从中间截断）
                            skip_count = 1
                            while skip_count < len(hidden_lines):
                                # 跳过太短的句子
                                if len(hidden_lines[skip_count].strip()) > 10:
                                    break
                                skip_count += 1

                            if skip_count < len(hidden_lines):
                                clean_hidden = '\n'.join(hidden_lines[skip_count:]).strip()
                                logger.info(f"跳过隐藏内容前{skip_count}句话")
                                return clean_hidden

            # 策略2: 如果可见开头很短（小于100字符），但隐藏内容很长
            # 可能需要跳过隐藏内容的一部分
            if len(visible_start) < 100 and len(hidden_content) > 500:
                # 尝试找到隐藏内容中与可见开头最不相似的部分
                for i in range(min(3, len(hidden_lines))):
                    line = hidden_lines[i].strip()
                    if len(line) > 20:
                        # 检查这行是否明显不同于可见开头
                        if not any(kw in line for kw in visible_keywords):
                            # 找到第一句明显不同的，从这行开始
                            clean_hidden = '\n'.join(hidden_lines[i:]).strip()
                            logger.info(f"从第{i+1}句开始使用隐藏内容")
                            return clean_hidden

            # 默认返回原始隐藏内容
            return hidden_content

        except Exception as e:
            logger.error(f"跳过隐藏内容错误开头失败: {e}")
            return hidden_content

    def _clean_html_tags(self, html_content: str) -> str:
        """
        清理HTML标签，保留纯文本

        Args:
            html_content: HTML内容

        Returns:
            纯文本内容
        """
        try:
            # 移除广告和无关的div
            content = re.sub(r'<div[^>]*class="download_app"[^>]*>.*?</div>', '', html_content, flags=re.DOTALL)
            content = re.sub(r'<div[^>]*id="open_xiaoshuo_str"[^>]*>.*?</div>', '', content, flags=re.DOTALL)
            # 只移除特定广告链接，不删除所有a标签
            content = re.sub(r'<a[^>]*>.*?下载.*?成人.*?视频.*?</a>', '', content, flags=re.DOTALL)
            content = re.sub(r'<a[^>]*>.*?点此.*?下载.*?</a>', '', content, flags=re.DOTALL)
            content = re.sub(r'<a[^>]*>.*?嫩女.*?视频.*?</a>', '', content, flags=re.DOTALL)
            content = re.sub(r'<a[^>]*>.*?香嫩.*?少女.*?</a>', '', content, flags=re.DOTALL)
            content = re.sub(r'<a[^>]*>.*?包你射.*?</a>', '', content, flags=re.DOTALL)
            content = re.sub(r'<a[^>]*>.*?点此打开.*?隐藏.*?内容.*?</a>', '', content, flags=re.DOTALL)
            # 处理br标签
            content = re.sub(r'<br[^>]*>', '\n', content, flags=re.IGNORECASE)
            # 移除JavaScript代码
            content = re.sub(r'function[^{]*\{[^}]*\}', '', content, flags=re.DOTALL)
            content = re.sub(r'var[^=]*=[^;]*;', '', content, flags=re.DOTALL)
            # 移除所有HTML标签，但保留内容
            content = re.sub(r'<[^>]+>', '', content)
            # 清理广告文本
            content = re.sub(r'点此下载.*?成人.*?视频.*?香嫩.*?少女.*?包你射.*?', '', content, flags=re.DOTALL)
            content = re.sub(r'更多小说尽在CR小说.*$', '', content, flags=re.DOTALL)
            content = re.sub(r'更多小说尽在.*$', '', content, flags=re.DOTALL)
            content = re.sub(r'CR小说.*$', '', content, flags=re.DOTALL)
            # 清理多余空白
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content).strip()

            return content

        except Exception as e:
            logger.error(f"清理HTML标签失败: {e}")
            return html_content

    def _extract_sewu3_content(self, content: str) -> str:
        """
        专门针对sewu3.xyz网站的内容提取方法
        从P标签中提取可见内容，再提取隐藏内容
        
        Args:
            content: 原始内容
            
        Returns:
            提取的完整内容
        """
        try:
            # 从P标签中提取可见内容
            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
            if not p_matches:
                logger.warning("未找到P标签，使用通用方法")
                return ""
            
            visible_content = p_matches[0]  # 取第一个P标签
            logger.info(f"找到P标签内容，长度: {len(visible_content)}")
            
            # 清理标题和发布日期等干扰内容，但要保留真正的故事开头
            # 清理发布日期
            visible_content = re.sub(r'^[\s\S]*?发布于[：:][^\n]*?\n', '', visible_content)
            # 清理标题行（如果存在）
            visible_content = re.sub(r'^[\s\S]*?<h3[^>]*>.*?</h3>.*?<Br>', '', visible_content, flags=re.DOTALL | re.IGNORECASE)
            # 清理其他导航信息
            visible_content = re.sub(r'^[\s\S]*?当前位置.*?首页.*?\n', '', visible_content, flags=re.DOTALL | re.IGNORECASE)
            # 移除广告和无关的div
            visible_content = re.sub(r'<div[^>]*class=\"download_app\"[^>]*>.*?</div>', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'<div[^>]*id=\"open_xiaoshuo_str\"[^>]*>.*?</div>', '', visible_content, flags=re.DOTALL)
            # 移除所有a标签及其内容（广告） - 包括下载链接
            visible_content = re.sub(r'<a[^>]*>.*?下载.*?成人.*?视频.*?</a>', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'<a[^>]*>.*?点此.*?下载.*?</a>', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'<a[^>]*>.*?嫩女.*?视频.*?</a>', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'<a[^>]*>.*?香嫩.*?少女.*?</a>', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'<a[^>]*>.*?包你射.*?</a>', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'<a[^>]*>.*?点此打开.*?隐藏.*?内容.*?</a>', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'<a[^>]*>.*?</a>', '', visible_content, flags=re.DOTALL)
            # 处理br标签
            visible_content = re.sub(r'<br[^>]*>', '\n', visible_content, flags=re.IGNORECASE)
            # 移除JavaScript代码
            visible_content = re.sub(r'function[^{]*\{[^}]*\}', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'var[^=]*=[^;]*;', '', visible_content, flags=re.DOTALL)
            # 移除所有HTML标签，但保留内容
            visible_content = re.sub(r'<[^>]+>', '', visible_content)
            # 清理广告文本
            visible_content = re.sub(r'点此下载.*?成人.*?视频.*?香嫩.*?少女.*?包你射.*?', '', visible_content, flags=re.DOTALL)
            # 清理结尾的各种广告
            visible_content = re.sub(r'更多小说尽在CR小说.*$', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'更多小说尽在.*$', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'CR小说.*$', '', visible_content, flags=re.DOTALL)
            visible_content = re.sub(r'更多小说.*$', '', visible_content, flags=re.DOTALL)
            # 最后的保险清理
            if '更多小说尽在CR小说' in visible_content:
                visible_content = visible_content.split('更多小说尽在CR小说')[0].strip()
            elif '更多小说尽在' in visible_content:
                visible_content = visible_content.split('更多小说尽在')[0].strip()
            elif 'CR小说' in visible_content:
                visible_content = visible_content.split('CR小说')[0].strip()
            # 清理多余空白
            visible_content = re.sub(r'\n\s*\n\s*\n', '\n\n', visible_content).strip()
            logger.info(f"提取到可见内容长度: {len(visible_content)}")
            
            # 提取隐藏内容（在span标签内的内容）
            hidden_content = ""
            hidden_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none;">(.*?)</span>', content, re.DOTALL)
            if not hidden_match:
                hidden_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"(.*?)</span>', content, re.DOTALL)
            if not hidden_match:
                hidden_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*>(.*?)</span>', content, re.DOTALL)
            
            if hidden_match:
                hidden_part = hidden_match.group(1)
                logger.info(f"提取到隐藏内容原始长度: {len(hidden_part)}")
                # 处理br标签
                hidden_part = re.sub(r'<br[^>]*>', '\n', hidden_part, flags=re.IGNORECASE)
                # 移除所有HTML标签，但保留内容
                hidden_part = re.sub(r'<[^>]+>', '', hidden_part)
                hidden_part = re.sub(r'\n\s*\n\s*\n', '\n\n', hidden_part).strip()
                hidden_content = hidden_part
                logger.info(f"处理后隐藏内容长度: {len(hidden_content)}")
            
            # 合并可见内容和隐藏内容
            if visible_content and hidden_content:
                full_content = visible_content + "\n\n" + hidden_content
                logger.info(f"合并内容总长度: {len(full_content)}")
                return full_content
            elif visible_content:
                return visible_content
            elif hidden_content:
                return hidden_content
            else:
                return ""
                
        except Exception as e:
            logger.error(f"sewu3.xyz内容提取失败: {e}")
            return ""

    def _clean_content_specific(self, content: str) -> str:
        """
        CMS T7特定的内容清理，处理多种模板结构
        按照用户建议的完整清理流程：先获取整个内容外标签，然后逐步清理
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        try:
            # 第一步：提取隐藏内容 - 在移除标签之前
            hidden_content_patterns = [
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none;"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*>(.*?)</span>',
            ]
            
            for pattern in hidden_content_patterns:
                hidden_matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                if hidden_matches:
                    # 如果找到隐藏内容，优先使用隐藏内容
                    hidden_text = '\n'.join(hidden_matches)
                    logger.info(f"找到隐藏内容，长度: {len(hidden_text)}")
                    # 将隐藏内容替换原始内容
                    content = hidden_text
                    break
            
            # 第二步：移除所有<div ... </div>标签及其内容 - 按照用户建议
            # 但是要保留隐藏内容，所以如果已经提取了隐藏内容，则直接跳过这一步
            if not any(re.search(pattern, content) for pattern in hidden_content_patterns):
                # 如果没有隐藏内容，则尝试从div中提取内容
                div_content_patterns = [
                    r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="[^"]*art-content[^"]*"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="[^"]*tab-panel-item[^"]*"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="[^"]*erx-content[^"]*"[^>]*>(.*?)</div>',
                    r'<div[^>]*id="content"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="content"[^>]*>(.*?)</div>',
                    r'<div[^>]*id="left"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="page_content"[^>]*>(.*?)</div>',
                    r'<article[^>]*class="post_excerpt[^"]*"[^>]*>(.*?)</article>',
                    r'<dd[^>]*>.*?<h3[^>]*>[^<]+</h3>.*?(.*?)</dd>',
                    r'<section[^>]*>.*?<dl[^>]*>.*?<h3[^>]*>[^<]+</h3>.*?<h5[^>]*>.*?</h5>.*?<p[^>]*>.*?</p>.*?</dl>',
                ]
                
                for pattern in div_content_patterns:
                    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                    if matches:
                        # 使用第一个匹配的内容
                        content = matches[0]
                        logger.info(f"从div中提取内容，长度: {len(content)}")
                        break
            
            # 第三步：移除<script ... </script>标签及其内容
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 第四步：移除<style ... </style>标签及其内容
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 第五步：移除所有<p>、<P>、</p>、</P>标签（保留内容）
            content = re.sub(r'<p[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'</p>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'<P[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'</P>', '', content, flags=re.IGNORECASE)
            
            # 第六步：替换<br>、<BR>标签为换行
            br_patterns = ['<br>', '<BR>', '<Br>', '<br/>', '<BR/>', '<Br/>', '<br />', '<BR />']
            for br_tag in br_patterns:
                content = content.replace(br_tag, '\n')
            
            # 第七步：移除其他HTML标签
            content = re.sub(r'<[^>]+>', '', content, flags=re.DOTALL)
            
            # 第八步：HTML实体转换
            import html
            content = html.unescape(content)
            
            # 额外的HTML实体处理
            html_entities = {
                '&nbsp;': ' ',
                '&nbsp': ' ',
                '&lt;': '<',
                '&gt;': '>',
                '&amp;': '&',
                '&quot;': '"',
                '&apos;': "'",
                '&ldquo;': '"',
                '&rdquo;': '"',
                '&lsquo;': ''',
                '&rsquo;': ''',
                '&mdash;': '—',
                '&ndash;': '–',
                '&hellip;': '…',
                '&copy;': '©',
                '&reg;': '®',
                '&trade;': '™',
                '&euro;': '€',
                '&pound;': '£',
                '&yen;': '¥',
                '&cent;': '¢',
                '&sect;': '§',
                '&para;': '¶',
            }
            
            # 转换HTML实体
            for entity, char in html_entities.items():
                content = content.replace(entity, char)
            
            # 处理数字实体（如 &#123; 和 &#x1F;）
            content = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), content)
            content = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), content)
            
            # 第九步：清理多余空白和特殊字符
            content = re.sub(r'\n\s*\n', '\n\n', content)  # 多个换行合并为两个
            content = re.sub(r'\s+', ' ', content)  # 多个空格合并为一个
            content = content.strip()
            
            return content
            
        except Exception as e:
            logger.error(f"内容清理失败: {e}")
            return content
    
    def _extract_title(self, content: str) -> str:
        """
        专门用于提取标题的方法
        
        Args:
            content: 页面内容
            
        Returns:
            提取的标题
        """
        try:
            # 按优先级尝试标题提取
            for pattern in self.title_reg:
                try:
                    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                    if match:
                        if match.groups():
                            title = match.group(1).strip()
                        else:
                            title = match.group(0).strip()
                        
                        # 清理标题中的HTML标签和多余空白
                        title = re.sub(r'<[^>]+>', '', title)
                        title = re.sub(r'\s+', ' ', title).strip()
                        
                        # 过滤掉明显不是标题的内容
                        if (len(title) > 2 and len(title) < 100 and 
                            not any(skip in title.lower() for skip in [
                                '当前位置', '首页', '返回', '上一篇', '下一篇', 
                                '发布于', '字数', '点击', 'www.', 'http', '.com'
                            ])):
                            return title
                except Exception as e:
                    logger.debug(f"标题提取模式 {pattern} 失败: {e}")
                    continue
            
            # 如果所有模式都失败，尝试从内容中提取第一句话作为标题
            content_text = self._extract_with_regex(content, self.content_reg)
            if content_text:
                # 提取第一句话作为标题（最多50字符）
                sentences = re.split(r'[。！？]', content_text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 5 and len(sentence) < 50:
                        return sentence
            
            return ""
        except Exception as e:
            logger.error(f"标题提取失败: {e}")
            return ""

    def _extract_with_regex(self, content: str, regex_list: List[str]) -> str:
        """
        使用正则表达式列表提取内容，按照用户建议的完整清理流程
        智能提取所有内容片段并合并
        
        Args:
            content: 页面内容
            regex_list: 正则表达式列表
            
        Returns:
            提取的内容
        """
        try:
            # 检查是否是8个有问题的网站，如果是则使用通用内容提取方法
            if hasattr(self, 'novel_site_name') and self.novel_site_name:
                problematic_sites = ['sewu3.xyz', 'xhxs2.xyz', 'luseshuba2.xyz', 'th5.xyz',
                                   'lrwx.xyz', 'meiseshuba2.xyz', 'sw2.xyz', 'scxs2.xyz']
                logger.info(f"novel_site_name: {self.novel_site_name}")
                for site in problematic_sites:
                    if site in self.novel_site_name:
                        logger.info(f"检测到{site}网站，使用通用内容提取方法")
                        return self._extract_content_universal(content)
            
            all_fragments = []
            
            # 1. 提取隐藏内容（最高优先级）
            hidden_patterns = [
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none;"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*>(.*?)</span>',
            ]
            
            for pattern in hidden_patterns:
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    cleaned_content = self._clean_content_specific(match)
                    if cleaned_content and len(cleaned_content.strip()) > 10:
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned_content))
                        if chinese_chars >= 5:
                            all_fragments.append({
                                'content': cleaned_content,
                                'source': '隐藏内容',
                                'chinese_chars': chinese_chars,
                                'length': len(cleaned_content),
                                'priority': 0  # 最高优先级
                            })
            
            # 2. 提取P标签内容
            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
            for i, match in enumerate(p_matches):
                cleaned_content = self._clean_content_specific(match)
                if cleaned_content and len(cleaned_content.strip()) > 10:
                    chinese_chars = len(re.findall(r'[一-龯]', cleaned_content))
                    if chinese_chars >= 5:
                        all_fragments.append({
                            'content': cleaned_content,
                            'source': f'P标签-{i+1}',
                            'chinese_chars': chinese_chars,
                            'length': len(cleaned_content),
                            'priority': 2  # 中等优先级
                        })
            
            # 3. 提取其他内容区域
            content_patterns = [
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*art-content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*tab-panel-item[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*erx-content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*id="content"[^>]*>(.*?)</div>',
                r'<div[^>]*class="content"[^>]*>(.*?)</div>',
                r'<div[^>]*id="left"[^>]*>(.*?)</div>',
                r'<div[^>]*class="page_content"[^>]*>(.*?)</div>',
                r'<article[^>]*class="post_excerpt[^"]*"[^>]*>(.*?)</article>',
                r'<dd[^>]*>.*?<h3[^>]*>[^<]+</h3>.*?(.*?)</dd>',
                r'<section[^>]*>.*?<dl[^>]*>.*?<h3[^>]*>[^<]+</h3>.*?<h5[^>]*>.*?</h5>.*?<p[^>]*>.*?</p>.*?</dl>',
            ]
            
            for pattern in content_patterns:
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                for i, match in enumerate(matches):
                    cleaned_content = self._clean_content_specific(match)
                    if cleaned_content and len(cleaned_content.strip()) > 10:
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned_content))
                        if chinese_chars >= 5:
                            all_fragments.append({
                                'content': cleaned_content,
                                'source': f'内容区域-{pattern[:15]}-{i+1}',
                                'chinese_chars': chinese_chars,
                                'length': len(cleaned_content),
                                'priority': 1  # 高优先级
                            })
            
            # 4. 使用正则列表中的模式（备用）
            for pattern in regex_list:
                try:
                    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                    for i, match in enumerate(matches):
                        # re.findall返回的是字符串列表，不是匹配对象
                        if isinstance(match, tuple):
                            # 如果是元组，取第一个非空元素
                            raw_content = next((m.strip() for m in match if m.strip()), "")
                        else:
                            # 如果是字符串，直接使用
                            raw_content = match.strip()
                        
                        cleaned_content = self._clean_content_specific(raw_content)
                        if cleaned_content and len(cleaned_content.strip()) > 10:
                            chinese_chars = len(re.findall(r'[一-龯]', cleaned_content))
                            if chinese_chars >= 5:
                                all_fragments.append({
                                    'content': cleaned_content,
                                    'source': f'正则-{pattern[:15]}-{i+1}',
                                    'chinese_chars': chinese_chars,
                                    'length': len(cleaned_content),
                                    'priority': 3  # 低优先级
                                })
                except Exception as e:
                    logger.error(f"正则匹配失败: {pattern}, 错误: {e}")
                    continue
            
            if not all_fragments:
                # 最后尝试：直接清理整个页面
                logger.info("所有模式都失败，尝试直接清理整个页面")
                cleaned_content = self._clean_content_specific(content)
                if cleaned_content and len(cleaned_content.strip()) > 10:
                    chinese_chars = len(re.findall(r'[一-龯]', cleaned_content))
                    if chinese_chars >= 5:
                        return cleaned_content
                return ""
            
            # 5. 选择最佳内容片段（避免重复）
            # 按优先级和中文字符数排序
            all_fragments.sort(key=lambda x: (x['priority'], -x['chinese_chars'], -x['length']))
            
            logger.info(f"找到 {len(all_fragments)} 个内容片段")
            
            # 选择最佳片段
            best_fragment = all_fragments[0]
            selected_content = best_fragment['content']
            
            logger.info(f"选择最佳片段: {best_fragment['source']} (长度: {best_fragment['length']}, 中文字符: {best_fragment['chinese_chars']})")
            
            # 检查是否有其他更优质的开头片段
            for fragment in all_fragments[1:]:
                if self._is_likely_start(fragment['content']) and not self._is_likely_start(selected_content):
                    # 如果其他片段更像开头，且当前片段不像开头，则替换
                    if fragment['chinese_chars'] > len(selected_content) * 0.7:  # 长度不能差太多
                        selected_content = fragment['content']
                        logger.info(f"选择更合适的开头片段: {fragment['source']}")
                        break
            
            return selected_content
            
        except Exception as e:
            logger.error(f"内容提取失败: {e}")
            return ""
    
    def _is_likely_start(self, content: str) -> bool:
        """
        判断内容是否更像故事开头
        
        Args:
            content: 内容文本
            
        Returns:
            是否像开头
        """
        # 开头常见模式
        start_patterns = [
            r'^[一-龯].*?(?:我是|我叫|今年|刚刚|记得|小时候|一天|从前)',
            r'^[一-龯].*?[一-九][0-9]?岁',
            r'^[一-龯].*?(?:小学|中学|大学|高中)',
            r'^[一-龯].*?字数[：:]\s*\d+字',  # 带字数信息的通常是开头
        ]
        
        for pattern in start_patterns:
            if re.search(pattern, content[:100], re.IGNORECASE):
                return True
        
        # 检查是否包含开头特征词汇
        start_keywords = ['我是', '我叫', '今年', '记得', '小时候', '一天', '从前', '曾经']
        content_start = content[:50]
        for keyword in start_keywords:
            if keyword in content_start:
                return True
        
        return False
    
    def parse_novel_detail(self, novel_id: str, category: str = "") -> Dict[str, Any]:
        """
        重写小说详情解析方法，支持category参数
        
        Args:
            novel_id: 小说ID
            category: 分类
            
        Returns:
            小说详情信息
        """
        # 重置章节计数器
        self.chapter_count = 0
        
        novel_url = self.get_novel_url(novel_id, category)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 提取标题 - 使用专门的标题提取方法
        title = self._extract_title(content)
        if not title:
            raise Exception("无法提取小说标题")
        
        print(f"开始处理 [ {title} ] - 分类: {category}")
        
        # 提取内容
        content_text = self._extract_with_regex(content, self.content_reg)
        if not content_text:
            raise Exception("无法提取小说内容")
        
        # 应用CMS T7特定的内容清理
        content_text = self._clean_content_specific(content_text)

        content_text = self._execute_after_crawler_funcs(content_text)
        
        # 构建返回结果
        result = {
            'title': title,
            'author': self.novel_site_name,  # 使用网站名称作为作者
            'book_type': '短篇',
            'status': '已完结',
            'category': category,
            'content': content_text,
            'url': novel_url,
            'novel_id': novel_id,
            'chapter_count': 1,  # 短篇小说通常只有一章
            'chapters': [
                {
                    'title': title,
                    'content': content_text,
                    'url': novel_url,
                    'chapter_id': '1'
                }
            ]
        }
        
        return result
    
    def parse_novel_list(self, url: str) -> List[Dict[str, Any]]:
        """
        解析小说列表
        
        Args:
            url: 列表页面URL
            
        Returns:
            小说信息列表
        """
        novels = []
        
        try:
            content = self._get_url_content(url)
            if not content:
                return novels
            
            # 查找小说链接 - 支持多种模板结构
            link_patterns = [
                r'<a[^>]*href="(/([^/]+)/([^/?]+)\.html)"[^>]*>([^<]+)</a>',
                r'<h2[^>]*><a[^>]*href="([^"]*)"[^>]*>([^<]+)</a></h2>',
                r'<a[^>]*class="[^"]*"[^>]*href="([^"]*\.html)"[^>]*>([^<]+)</a>',
                r'<dt[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>.*?</dt>',
            ]
            
            for pattern in link_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) >= 2:
                        link_url = match[0] if isinstance(match[0], str) else match[-2]
                        title = match[-1] if isinstance(match[-1], str) else match[-2]
                        
                        # 构建完整的URL
                        if link_url.startswith('/'):
                            full_url = urljoin(self.base_url, link_url)
                        else:
                            full_url = link_url
                        
                        # 提取novel_id和category
                        url_parts = link_url.strip('/').split('/')
                        if len(url_parts) >= 2:
                            category = url_parts[-2]
                            novel_id = url_parts[-1].replace('.html', '')
                        else:
                            category = ""
                            novel_id = url_parts[-1].replace('.html', '')
                        
                        # 确保novel_id不为空
                        if novel_id and title.strip():
                            novels.append({
                                'title': title.strip(),
                                'url': full_url,
                                'novel_id': novel_id,
                                'category': category,
                                'book_type': '短篇'
                            })
            
            return novels
            
        except Exception as e:
            logger.error(f"解析小说列表失败: {url}, 错误: {e}")
            return novels

if __name__ == "__main__":
    # 测试代码
    parser = CmsT7Parser(site_url="https://www.lulu6.xyz/")
    print(f"网站名称: {parser.name}")
    print(f"基础URL: {parser.base_url}")
    print(f"测试URL生成: {parser.get_novel_url('19752', 'luanqing')}")
    print(f'测试URL生成: {parser.get_novel_url("21373", "luanqing")}')
    print(f"书籍类型: {parser._detect_book_type('test')}")