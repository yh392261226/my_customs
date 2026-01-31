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
    
    def parse_novel_detail(self, novel_id: str, category: str = "") -> Dict[str, Any]:
        """
        重写小说详情解析方法，支持分类参数
        
        Args:
            novel_id: 小说ID
            category: 分类（可选）
            
        Returns:
            小说详情信息
        """
        # 重置章节计数器，防止跨书籍或重试时计数延续
        self.chapter_count = 0
        
        novel_url = self.get_novel_url(novel_id, category)
        content = self._get_url_content(novel_url)
        
        if not content:
            raise Exception(f"无法获取小说页面: {novel_url}")
        
        # 自动检测书籍类型
        book_type = self._detect_book_type(content)
        
        # 提取标题
        title = self._extract_with_regex(content, self.title_reg)
        if not title:
            raise Exception("无法提取小说标题")
        
        logger.info(f"开始处理 [ {title} ] - 类型: {book_type}")
        
        # 根据书籍类型选择处理方式
        if book_type == "多章节":
            novel_content = self._parse_multichapter_novel(content, novel_url, title)
        elif book_type == "内容页内分页":
            novel_content = self._parse_content_pagination_novel(content, novel_url, title)
        else:
            novel_content = self._parse_single_chapter_novel(content, novel_url, title)
        
        logger.info(f'[ {title} ] 完成')
        return novel_content
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写单章节小说解析方法，使用通用内容提取
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 使用通用内容提取方法
        chapter_content = self._extract_content_universal(content)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)
        
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
    
    def _extract_p_tags_intelligent(self, content: str) -> List[str]:
        """
        智能提取P标签，处理多层嵌套问题
        
        Args:
            content: 页面内容
            
        Returns:
            提取的P标签内容列表
        """
        try:
            # 方法1：使用标准的非贪婪模式
            p_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
            
            # 方法2：如果发现可能的嵌套问题，使用手动解析
            if len(p_matches) < 10:  # 如果P标签数量异常少，可能存在嵌套问题
                logger.info(f"P标签数量较少({len(p_matches)})，可能存在嵌套问题，使用智能解析")
                
                # 手动解析P标签
                intelligent_matches = []
                p_start_positions = []
                p_end_positions = []
                
                # 查找所有P标签的开始和结束位置
                for match in re.finditer(r'<p[^>]*>', content, re.IGNORECASE):
                    p_start_positions.append(match.start())
                
                for match in re.finditer(r'</p>', content, re.IGNORECASE):
                    p_end_positions.append(match.end())
                
                # 智能配对P标签
                if p_start_positions and p_end_positions:
                    stack = []
                    i = 0
                    j = 0
                    
                    while i < len(p_start_positions) and j < len(p_end_positions):
                        start_pos = p_start_positions[i]
                        end_pos = p_end_positions[j]
                        
                        if start_pos < end_pos:
                            stack.append(start_pos)
                            i += 1
                        else:
                            if stack:
                                # 找到匹配的P标签
                                matched_start = stack.pop()
                                p_content = content[matched_start:end_pos]
                                intelligent_matches.append(p_content)
                            j += 1
                    
                    # 处理剩余的栈
                    while stack and j < len(p_end_positions):
                        matched_start = stack.pop()
                        end_pos = p_end_positions[j]
                        p_content = content[matched_start:end_pos]
                        intelligent_matches.append(p_content)
                        j += 1
                
                if len(intelligent_matches) > len(p_matches):
                    p_matches = intelligent_matches
                    logger.info(f"智能解析找到 {len(p_matches)} 个P标签")
            
            # 方法3：如果还是有问题，使用最精确的模式
            if len(p_matches) < 5:
                logger.info("使用最精确的模式提取P标签")
                # 使用递归模式匹配，避免嵌套
                precise_pattern = r'<p[^>]*>(?:[^<]|<(?!/?p[^>]*>))*?</p>'
                p_matches = re.findall(precise_pattern, content, re.DOTALL | re.IGNORECASE)
                logger.info(f"精确模式找到 {len(p_matches)} 个P标签")
            
            logger.info(f"最终找到 {len(p_matches)} 个P标签")
            return p_matches
            
        except Exception as e:
            logger.error(f"智能P标签提取失败: {e}")
            # 回退到简单模式
            return re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)

    def _remove_ads(self, content: str) -> str:
        """
        移除广告和无关内容
        
        Args:
            content: 原始内容
            
        Returns:
            清理后的内容
        """
        try:
            # 更保守的广告移除，只移除明确的广告内容
            ad_patterns = [
                r'点此下载.*?成人.*?视频.*?香嫩.*?少女.*?包你射.*?',
                r'更多小说尽在CR小说.*$',
                r'更多小说尽在.*$',
                r'CR小说.*$',
                r'<a[^>]*>.*?下载.*?成人.*?视频.*?</a>',
                r'<a[^>]*>.*?点此.*?下载.*?</a>',
                r'var[^=]*=[^;]*;',
                r'Copyright.*?All Rights Reserved',
            ]
            
            for pattern in ad_patterns:
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 清理多余空白
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content).strip()
            
            return content
            
        except Exception as e:
            logger.error(f"移除广告失败: {e}")
            return content

    def _extract_content_universal(self, content: str) -> str:
        """
        通用内容提取方法，自动检测并处理可见开头和隐藏内容

        Args:
            content: 原始HTML内容

        Returns:
            提取的完整内容
        """
        try:
            # 第一步：提取标题和发布日期
            title = ""
            publish_date = ""
            
            # 提取标题
            title_patterns = [
                r'<h1[^>]*class=["\']title["\'][^>]*>([^<]+)</h1>',
                r'<h1[^>]*>([^<]+)</h1>',
                r'<title[^>]*>([^<]+)</title>',
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    # 移除网站后缀
                    title = re.sub(r'[-—].*?$', '', title)
                    break
            
            # 提取发布日期
            date_patterns = [
                r'发布于[：:]\s*(\d{4}-\d{2}-\d{2})',
                r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, content)
                if match:
                    publish_date = match.group(1)
                    break
            
            # 第二步：提取所有可能的可见开头（P标签或art-content）
            # 但首先构建完整的开头部分
            header_content = ""
            if title and publish_date:
                header_content = f"{title}\n\n发布于：{publish_date}\n\n"
            elif title:
                header_content = f"{title}\n\n"
            
            # 第三步：提取所有可能的可见开头（P标签或art-content）
            visible_starts = []

            # 从P标签中提取可见开头（使用更智能的算法处理嵌套问题）
            p_matches = self._extract_p_tags_intelligent(content)
            logger.info(f"找到 {len(p_matches)} 个P标签")

            # 使用原来的逻辑处理其他网站
            for i, p_match in enumerate(p_matches):
                    cleaned = self._clean_html_tags(p_match)

                    # 过滤掉导航信息和广告
                    skip_keywords = ['当前位置', '首页', 'TikTok', '成人导航', 'APP破解', '点此下载', '包你射', '香嫩少女', '柠檬导航', 'Copyright']
                    is_skip = any(keyword in cleaned for keyword in skip_keywords)

                    if cleaned and not is_skip:
                        # 特殊处理章节标记（如（１）、（2）、①等）
                        chapter_marker_pattern = r'^[（\(][0-9一二三四五六七八九十０-９]+[）\)]$|^第[一二三四五六七八九十]+[章节回]$|^①$|^②$|^③$|^④$|^⑤$|^⑥$|^⑦$|^⑧$|^⑨$|^⑩$'
                        is_chapter_marker = re.match(chapter_marker_pattern, cleaned.strip())
                        
                        if is_chapter_marker:
                            # 如果是章节标记，直接添加
                            visible_starts.append(cleaned)
                            logger.info(f"P标签 #{i+1} 章节标记添加到visible_starts")
                            continue
                        
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

                    # 过滤掉导航信息
                    skip_keywords = ['当前位置', '首页', 'TikTok', '成人导航', 'APP破解', '柠檬导航', 'Copyright', '阅读是一场修行']
                    is_skip = any(keyword in cleaned for keyword in skip_keywords)

                    if cleaned and not is_skip and len(cleaned.strip()) > 50:
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

                    # 过滤掉导航信息
                    skip_keywords = ['当前位置', '首页', 'TikTok', '成人导航', 'APP破解', '柠檬导航']
                    is_skip = any(keyword in cleaned for keyword in skip_keywords)

                    if cleaned and not is_skip and len(cleaned.strip()) > 50:
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned))
                        if chinese_chars > 20:
                            visible_starts.append(cleaned)
                            logger.info(f"Article #{i+1} 添加到visible_starts")
                            break

            # 如果还是没有任何可见开头,尝试从section标签提取
            if not visible_starts:
                section_matches = re.findall(r'<section[^>]*>(.*?)</section>', content, re.DOTALL | re.IGNORECASE)
                logger.info(f"未从article找到有效内容,检查 {len(section_matches)} 个section标签")

                for i, section_match in enumerate(section_matches):
                    cleaned = self._clean_html_tags(section_match)

                    # 过滤掉导航信息
                    skip_keywords = ['当前位置', '首页', 'TikTok', '成人导航', 'APP破解', '柠檬导航', 'Toggle navigation']
                    is_skip = any(keyword in cleaned for keyword in skip_keywords)

                    if cleaned and not is_skip and len(cleaned.strip()) > 50:
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned))
                        if chinese_chars > 20:
                            visible_starts.append(cleaned)
                            logger.info(f"Section #{i+1} 添加到visible_starts")
                            break
            
            # 特殊处理：提取隐藏内容之前的可见文本
            if not visible_starts:
                hidden_pos = content.find('id="xiaoshuo_str"')
                if hidden_pos != -1:
                    # 查找h1标题位置
                    h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content[:hidden_pos], re.IGNORECASE)
                    if h1_match:
                        h1_end = h1_match.end()
                        # 提取h1标题到隐藏内容之间的文本
                        text_before_hidden = content[h1_end:hidden_pos]
                        
                        # 清理HTML标签和广告
                        cleaned_text = self._clean_html_tags(text_before_hidden)
                        cleaned_text = re.sub(r'TikTok成人版.*?幸福每一天', '', cleaned_text)
                        cleaned_text = re.sub(r'点此打开隐藏内容继续看.*$', '', cleaned_text)
                        cleaned_text = cleaned_text.strip()
                        
                        # 检查是否包含有效的故事内容
                        chinese_chars = len(re.findall(r'[一-龯]', cleaned_text))
                        if len(cleaned_text) > 20 and chinese_chars > 10:
                            visible_starts.append(cleaned_text)
                            logger.info(f"从隐藏内容之前提取可见文本，长度: {len(cleaned_text)}")
                            logger.info(f"可见文本开头: {cleaned_text[:100]}...")

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
            
            # 如果有header_content，确保它被包含在最终结果中
            if header_content:
                # 暂时将header_content添加到visible_starts的开头
                visible_starts.insert(0, header_content)

            # 情况1: 有完整可见内容和隐藏内容
            if full_visible_content and hidden_content:
                logger.info(f"情况1: full_visible_content长度={len(full_visible_content)}, hidden_content长度={len(hidden_content)}")
                
                # 检查是否有章节标记在visible_starts中
                has_chapter_marker = False
                chapter_marker_start = None
                for start in visible_starts:
                    chapter_marker_pattern = r'^[（\(][0-9一二三四五六七八九十０-９]+[）\)]$|^第[一二三四五六七八九十]+[章节回]$|^①$|^②$|^③$|^④$|^⑤$|^⑥$|^⑦$|^⑧$|^⑨$|^⑩$'
                    if re.match(chapter_marker_pattern, start.strip()):
                        has_chapter_marker = True
                        chapter_marker_start = start
                        break
                
                # 如果有章节标记，使用章节标记开头，然后合并可见内容和隐藏内容
                if has_chapter_marker and chapter_marker_start:
                    # 从可见内容中找到章节标记后面的内容
                    visible_after_marker = ""
                    for start in visible_starts:
                        if start != chapter_marker_start and len(start.strip()) > 10:
                            visible_after_marker = start
                            break
                    
                    # 如果没有找到章节标记后的可见内容，使用full_visible_content的一部分
                    if not visible_after_marker and full_visible_content:
                        # 从full_visible_content中提取章节标记后的内容
                        marker_pos = full_visible_content.find(chapter_marker_start)
                        if marker_pos != -1:
                            after_marker = full_visible_content[marker_pos + len(chapter_marker_start):].strip()
                            if len(after_marker) > 10:
                                visible_after_marker = after_marker
                    
                    # 智能跳过隐藏内容中的错误开头
                    clean_hidden = self._skip_error_start_in_hidden(chapter_marker_start, hidden_content)
                    
                    # 合并内容：章节标记 + 可见内容（如果有） + 隐藏内容
                    if visible_after_marker:
                        merged_content = f"{chapter_marker_start}\n\n{visible_after_marker}\n\n{clean_hidden}"
                        logger.info(f"使用章节标记开头合并可见内容和隐藏内容，总长度: {len(merged_content)}")
                    else:
                        merged_content = f"{chapter_marker_start}\n\n{clean_hidden}"
                        logger.info(f"使用章节标记开头合并隐藏内容，总长度: {len(merged_content)}")
                    return merged_content
                # 检查可见内容是否包含故事开头但可能不完整
                # 如果隐藏内容明显比可见内容长，说明需要合并
                if len(hidden_content) > len(full_visible_content) * 0.8:
                    logger.info(f"隐藏内容长度({len(hidden_content)})与可见内容长度({len(full_visible_content)})相近，需要合并")
                    
                    # 选择最长的可见开头
                    best_start = max(visible_starts, key=len) if visible_starts else full_visible_content[:200]
                    if best_start:
                        clean_hidden = self._skip_error_start_in_hidden(best_start, hidden_content)
                        merged_content = f"{best_start}\n\n{clean_hidden}"
                        logger.info(f"合并可见开头和隐藏内容，总长度: {len(merged_content)}")
                        return merged_content
                
                # 如果可见内容足够长（>500字）且隐藏内容相对较短，优先使用可见内容
                elif len(full_visible_content) > 500:
                    logger.info(f"可见内容长度足够（{len(full_visible_content)}），优先使用可见内容")
                    return full_visible_content
                # 否则使用可见内容的第一部分和隐藏内容
                # 提取visible_starts中的第一个作为开头
                best_start = visible_starts[0] if visible_starts else full_visible_content[:200]
                if best_start:
                    clean_hidden = self._skip_error_start_in_hidden(best_start, hidden_content)
                    merged_content = f"{best_start}\n\n{clean_hidden}"
                    logger.info(f"合并可见开头和隐藏内容，总长度: {len(merged_content)}")
                    return merged_content
                else:
                    logger.info("使用隐藏内容（无可见开头）")
                    return hidden_content

            # 情况2: 有隐藏内容和可见开头，需要合并
            if hidden_content and visible_starts:
                # 检查是否有章节标记
                chapter_marker_start = None
                other_visible_content = ""
                
                for start in visible_starts:
                    chapter_marker_pattern = r'^[（\(][0-9一二三四五六七八九十０-９]+[）\)]$|^第[一二三四五六七八九十]+[章节回]$|^①$|^②$|^③$|^④$|^⑤$|^⑥$|^⑦$|^⑧$|^⑨$|^⑩$'
                    if re.match(chapter_marker_pattern, start.strip()):
                        chapter_marker_start = start
                    elif len(start.strip()) > 10:
                        other_visible_content = start
                
                # 构建完整的开头部分（标题 + 发布日期 + 章节标记/可见内容）
                header_parts = []
                if title:
                    header_parts.append(title)
                if publish_date:
                    header_parts.append(f"发布于：{publish_date}")
                
                # 如果有章节标记，使用章节标记开头
                if chapter_marker_start:
                    header_parts.append(chapter_marker_start)
                    # 智能跳过隐藏内容中的错误开头
                    clean_hidden = self._skip_error_start_in_hidden(chapter_marker_start, hidden_content)
                    
                    # 合并内容：标题 + 发布日期 + 章节标记 + 其他可见内容（如果有） + 隐藏内容
                    if other_visible_content:
                        merged_content = "\n\n".join(header_parts + [other_visible_content, clean_hidden])
                        logger.info(f"使用章节标记开头合并可见内容和隐藏内容，总长度: {len(merged_content)}")
                    else:
                        merged_content = "\n\n".join(header_parts + [clean_hidden])
                        logger.info(f"使用章节标记开头合并隐藏内容，总长度: {len(merged_content)}")
                    return merged_content
                else:
                    # 没有章节标记，选择最长的可见开头
                    best_start = max(visible_starts, key=len)
                    header_parts.append(best_start)
                    
                    # 智能跳过隐藏内容中的错误开头
                    clean_hidden = self._skip_error_start_in_hidden(best_start, hidden_content)
                    
                    # 合并内容：标题 + 发布日期 + 可见开头 + 隐藏内容
                    merged_content = "\n\n".join(header_parts + [clean_hidden])
                    logger.info(f"合并可见开头和隐藏内容，总长度: {len(merged_content)}")
                    return merged_content

            # 情况3: 只有完整可见内容
            if full_visible_content:
                logger.info("使用完整可见内容")
                return full_visible_content

            # 情况4: 只有可见开头
            if visible_starts:
                # 选择最长的可见开头
                best_start = max(visible_starts, key=len)
                logger.info(f"使用可见开头，长度: {len(best_start)}")
                return best_start

            # 情况5: 只有隐藏内容
            if hidden_content:
                logger.info("只找到隐藏内容")
                return hidden_content

            # 情况6: 都没找到，返回空
            logger.warning("未找到任何有效内容")
            return ""

        except Exception as e:
            logger.error(f"通用内容提取失败: {e}")
            return ""

    def _clean_visible_content(self, raw_content: str) -> str:
        """
        清理可见内容，移除广告和导航信息，处理各种边界情况
        包括嵌套、缺失、多重、多个、半个等情况
        """
        try:
            content = raw_content
            
            # 移除各种广告div - 处理多重和嵌套情况
            ad_div_patterns = [
                r'<div[^>]*class="[^"]*download[^"]*"[^>]*>.*?</div>',
                r'<div[^>]*id="[^"]*open[^"]*xiaoshuo[^"]*"[^>]*>.*?</div>',
                r'<div[^>]*style="text-align:center[^>]*>.*?<a[^>]*>.*?下载.*?</a>.*?</div>',
            ]
            for pattern in ad_div_patterns:
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除导航和发布信息 - 处理各种格式，包括wux3.xyz的特殊格式
            nav_patterns = [
                r'^[\s\S]*?当前位置\s*[:：].*?\n',
                r'^[\s\S]*?发布于\s*[:：][^\n]*?\n',
                r'^[\s\S]*?首页\s*>\s*[^>\n]+(?:\s*>\s*[^>\n]+)*\s*',
                r'当前位置\s*[:：].*?(?=\n|$)',
                r'发布于\s*[:：][^\n]*(?=\n|$)',
                r'首页\s*>\s*[^>\n]+(?:\s*>\s*[^>\n]+)*\s*(?=\n|$)',
            ]
            for pattern in nav_patterns:
                content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            # 移除各种广告链接 - 处理多个和半个标签
            ad_link_patterns = [
                r'<a[^>]*>.*?下载.*?成人.*?视频.*?</a>',
                r'<a[^>]*>.*?点此.*?下载.*?</a>',
                r'<a[^>]*>.*?嫩女.*?视频.*?</a>',
                r'<a[^>]*>.*?香嫩.*?少女.*?</a>',
                r'<a[^>]*>.*?包你射.*?</a>',
                r'<a[^>]*>.*?点此打开.*?隐藏.*?内容.*?</a>',
                r'<a[^>]*>.*?PornHub.*?</a>',
                r'<a[^>]*>.*?51色.*?</a>',
                r'<a[^>]*>.*?高能.*?污漫.*?</a>',
                r'<a[^>]*href="[^"]*"[^>]*>.*?</a>',  # 移除所有外部链接
                r'<a[^>]*>.*?</a>',  # 移除剩余的a标签
            ]
            for pattern in ad_link_patterns:
                content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 移除script和style标签 - 处理嵌套情况
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # 处理HTML标签 - 保留换行，处理各种br变体
            br_patterns = [
                r'<br[^>]*>',
                r'<br/>',
                r'<br />',
                r'<BR[^>]*>',
                r'<BR/>',
                r'<BR />',
            ]
            for br_pattern in br_patterns:
                content = re.sub(br_pattern, '\n', content, flags=re.IGNORECASE)
            
            # 处理嵌套的P标签 - 处理多个和半个标签
            content = re.sub(r'</p>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<p[^>]*>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<P[^>]*>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</P>', '\n', content, flags=re.IGNORECASE)
            
            # 移除剩余的HTML标签 - 处理半个标签
            content = re.sub(r'<[^>]*>', '', content)
            
            # 清理多余空白和换行
            content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
            content = re.sub(r'[ \t]+', ' ', content)
            
            # 过滤掉导航、版权和无关信息 - 处理各种情况
            skip_patterns = [
                r'当前位置\s*[:：].*',
                r'首页\s*>.*',
                r'TikTok.*',
                r'成人导航.*',
                r'APP破解.*',
                r'柠檬导航.*',
                r'Copyright.*',
                r'阅读是一场修行.*',
                r'©.*',
                r'更多小说尽在.*',
                r'CR小说.*',
                r'本帖最后由.*编辑.*',
                r'^\s*[＞>]\s*',
                r'^\s*【.*】\s*$',
                r'^\s*$\s*$',  # 空行
            ]
            
            lines = content.split('\n')
            filtered_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否匹配跳过模式
                should_skip = False
                for pattern in skip_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_skip = True
                        break
                
                if not should_skip:
                    # 检查是否是有意义的中文内容
                    chinese_chars = len(re.findall(r'[一-龯]', line))
                    total_chars = len(line)
                    
                    # 特殊处理章节标记（如（１）、（2）、①等）
                    chapter_marker_pattern = r'^[（\(][0-9一二三四五六七八九十０-９]+[）\)]$|^第[一二三四五六七八九十]+[章节回]$|^①$|^②$|^③$|^④$|^⑤$|^⑥$|^⑦$|^⑧$|^⑨$|^⑩$'
                    is_chapter_marker = re.match(chapter_marker_pattern, line.strip())                    
                    # 如果是章节标记，直接保留
                    if is_chapter_marker:
                        filtered_lines.append(line)
                    # 如果中文字符占比超过30%且至少有5个字符，保留
                    elif total_chars > 0 and chinese_chars / total_chars > 0.3 and chinese_chars >= 5:
                        filtered_lines.append(line)
            
            final_content = '\n\n'.join(filtered_lines).strip()
            return final_content
            
        except Exception as e:
            logger.error(f"清理可见内容失败: {e}")
            return raw_content

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

            # 默认假设没有重叠
            has_overlap = False

            # 策略1: 如果可见开头和隐藏开头明显不同，跳过隐藏内容的第一句
            if visible_start and len(visible_start) > 20 and len(visible_keywords) > 0:
                # 检查隐藏内容开头是否包含可见开头的关键词
                for keyword in visible_keywords[:3]:  # 检查前3个关键词
                    if keyword in hidden_start_text:
                        has_overlap = True
                        break

            # 只有在没有重叠时才考虑跳过
            if not has_overlap:
                # 额外检查：检查可见开头和隐藏内容的前3行是否明显不同
                # 通过比较前100个字符来判断
                visible_prefix = visible_start[:100]
                hidden_prefix = hidden_content[:100]

                # 如果前100个字符相同度很低（小于50%），则跳过第一句
                similarity = sum(1 for a, b in zip(visible_prefix, hidden_prefix) if a == b)
                if len(visible_prefix) > 0 and similarity / len(visible_prefix) < 0.5:
                    # 前100字符相同度很低，可能需要跳过
                    if len(hidden_lines) > 1:
                        # 跳过第一句，从第二句开始
                        skip_count = 1
                        while skip_count < len(hidden_lines):
                            # 跳过太短的句子
                            if len(hidden_lines[skip_count].strip()) > 10:
                                break
                            skip_count += 1

                        if skip_count < len(hidden_lines):
                            clean_hidden = '\n'.join(hidden_lines[skip_count:]).strip()
                            logger.info(f"可见开头和隐藏开头相似度低，跳过前{skip_count}句话")
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

    def _extract_p_tag_split_content(self, content: str) -> str:
        """
        提取P标签分割型网站的内容（sewu3.xyz, xhxs2.xyz等）
        
        策略：
        1. 智能提取可见内容，包括被广告截断的部分和多个P标签
        2. 提取xiaoshuo_str标签中的隐藏内容
        3. 合并两部分内容并去重
        """
        try:
            logger.info("使用P标签分割型内容提取策略")
            
            # 1. 提取可见内容 - 处理多个P标签的情况
            visible_content = ""
            
            # 查找第一个P标签开始到xiaoshuo_str标签之前的所有内容
            p_start_match = re.search(r'<p[^>]*>', content, re.IGNORECASE)
            xiaoshuo_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*>', content, re.IGNORECASE)
            
            if p_start_match and xiaoshuo_match:
                # 提取从第一个P标签开始到xiaoshuo_str标签之前的所有内容
                start_pos = p_start_match.start()
                end_pos = xiaoshuo_match.start()
                raw_visible_section = content[start_pos:end_pos]
                
                # 提取所有P标签的内容，包括嵌套的P标签
                all_p_contents = []
                
                # 特殊处理：对于被广告截断的嵌套P标签，直接手动提取
                # 查找所有开P标签和闭P标签的位置
                p_open_positions = []
                p_close_positions = []
                
                for match in re.finditer(r'<p[^>]*>', raw_visible_section, re.IGNORECASE):
                    p_open_positions.append(match.start())
                
                for match in re.finditer(r'</p>', raw_visible_section, re.IGNORECASE):
                    p_close_positions.append(match.end())
                
                # 如果开P标签比闭P标签多，说明有被截断的P标签
                if len(p_open_positions) > len(p_close_positions):
                    logger.info(f"检测到被截断的P标签：开标签{len(p_open_positions)}个，闭标签{len(p_close_positions)}个")
                    
                    # 手动提取每个P标签的内容
                    for i, open_pos in enumerate(p_open_positions):
                        # 确定这个P标签的结束位置
                        if i < len(p_close_positions):
                            # 有对应的闭标签
                            end_pos = p_close_positions[i]
                            p_content = raw_visible_section[open_pos:end_pos]
                        else:
                            # 没有对应的闭标签，提取到xiaoshuo_str之前
                            p_content = raw_visible_section[open_pos:]
                        
                        # 提取P标签内的文本内容
                        p_text_match = re.search(r'<p[^>]*>(.*)', p_content, re.DOTALL | re.IGNORECASE)
                        if p_text_match:
                            p_text = p_text_match.group(1)
                            # 如果有闭标签，移除它
                            p_text = re.sub(r'</p>.*$', '', p_text, flags=re.DOTALL)
                            
                            # 只保留有实际内容的P标签（长度大于5且包含中文字符）
                            if len(p_text.strip()) > 5 and re.search(r'[一-龯]', p_text):
                                all_p_contents.append(p_text.strip())
                            elif re.match(r'^[（\(][0-9一二三四五六七八九十]+[）\)]$', p_text.strip()) or p_text.strip() == '（１）':
                                # 特殊处理章节标记
                                all_p_contents.append(p_text.strip())
                else:
                    # 正常情况：使用非贪婪匹配按顺序提取
                    temp_content = raw_visible_section
                    extracted_contents = []
                    
                    while True:
                        p_match = re.search(r'<p[^>]*>(.*?)</p>', temp_content, re.DOTALL | re.IGNORECASE)
                        if p_match:
                            p_content = p_match.group(1)
                            extracted_contents.append(p_content)
                            temp_content = temp_content[p_match.end():]
                        else:
                            break
                    
                    p_matches = extracted_contents
                    
                    # 对于每个提取的P标签内容，检查是否还包含嵌套的P标签
                    final_contents = []
                    for p_content in p_matches:
                        # 如果P标签内容中还包含P标签，递归提取
                        if re.search(r'<p[^>]*>', p_content, re.IGNORECASE):
                            # 递归提取嵌套的P标签
                            nested_temp = p_content
                            while True:
                                nested_match = re.search(r'<p[^>]*>(.*?)</p>', nested_temp, re.DOTALL | re.IGNORECASE)
                                if nested_match:
                                    nested_content = nested_match.group(1)
                                    final_contents.append(nested_content)
                                    nested_temp = nested_temp[nested_match.end():]
                                else:
                                    break
                        else:
                            final_contents.append(p_content)
                    
                    for p_content in final_contents:
                        # 清理每个P标签的内容
                        clean_p = self._clean_visible_content(p_content)
                        if clean_p.strip():
                            all_p_contents.append(clean_p.strip())
                
                # 对提取的内容进行最终清理
                cleaned_contents = []
                for p_content in all_p_contents:
                    clean_p = self._clean_visible_content(p_content)
                    if clean_p.strip():
                        cleaned_contents.append(clean_p.strip())
                
                all_p_contents = cleaned_contents
                
                # 合并所有P标签内容
                raw_visible = '\n\n'.join(all_p_contents)
                logger.info(f"提取到{len(all_p_contents)}个P标签内容，总长度: {len(raw_visible)}")
                
                # 进一步清理合并后的内容
                visible_content = self._clean_visible_content(raw_visible)
                logger.info(f"清理后可见内容长度: {len(visible_content)}")
            else:
                # 备用方案：提取第一个P标签
                p_match = re.search(r'<p[^>]*>(.*?)</p>', content, re.DOTALL | re.IGNORECASE)
                if p_match:
                    raw_visible = p_match.group(1)
                    visible_content = self._clean_visible_content(raw_visible)
                    logger.info(f"备用方案提取P标签内容，长度: {len(visible_content)}")
            
            # 2. 提取隐藏内容
            hidden_content = ""
            hidden_patterns = [
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none;"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"[^>]*>(.*?)</span>',
                r'<span[^>]*id="xiaoshuo_str"[^>]*>(.*?)</span>',
            ]
            
            for pattern in hidden_patterns:
                hidden_match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if hidden_match:
                    raw_hidden = hidden_match.group(1)
                    logger.info(f"提取到原始隐藏内容，长度: {len(raw_hidden)}")
                    
                    # 清理隐藏内容
                    hidden_content = self._clean_hidden_content(raw_hidden)
                    logger.info(f"清理后隐藏内容长度: {len(hidden_content)}")
                    break
            
            # 3. 智能合并内容
            if visible_content and hidden_content:
                merged_content = self._merge_visible_and_hidden(visible_content, hidden_content)
                logger.info(f"合并内容总长度: {len(merged_content)}")
                return merged_content
            elif visible_content:
                logger.info("只有可见内容，返回可见内容")
                return visible_content
            elif hidden_content:
                logger.info("只有隐藏内容，返回隐藏内容")
                return hidden_content
            else:
                logger.warning("未找到有效内容，尝试备用方案")
                return self._extract_content_fallback(content)
                
        except Exception as e:
            logger.error(f"P标签分割型内容提取失败: {e}")
            return self._extract_content_fallback(content)

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
            # 检查是否是9个有问题的网站，使用base_url来判断
            problematic_sites = ['sewu3.xyz', 'xhxs2.xyz', 'luseshuba2.xyz', 'th5.xyz',
                               'lrwx.xyz', 'meiseshuba2.xyz', 'sw2.xyz', 'scxs2.xyz', 'sdxs.xyz']
            
            if self.base_url:
                for site in problematic_sites:
                    if site in self.base_url:
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
            r'^[一-龯].*?(?:发布于|20|本帖|我)',
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
        
        logger.info(f"开始处理 [ {title} ] - 分类: {category}")
        
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