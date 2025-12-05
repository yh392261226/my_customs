"""
色色文学网站解析器 - 基于配置驱动版本
继承自 BaseParser，使用属性配置实现
"""

import re
from typing import Dict, Any, List, Optional
from .base_parser_v2 import BaseParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Xn59Parser(BaseParser):
    """色色文学网站解析器 - 配置驱动版本"""
    
    def __init__(self, proxy_config: Optional[Dict[str, Any]] = None, novel_site_name: Optional[str] = None):
        """
        初始化解析器
        
        Args:
            proxy_config: 代理配置
            novel_site_name: 网站名称，如果提供则覆盖默认名称
        """
        super().__init__(proxy_config, novel_site_name)
    
    # 基本信息
    name = "色色文学"
    description = "色色文学网站解析器"
    base_url = "https://www.xn59.cc"
    
    # 正则表达式配置 - 标题提取
    title_reg = [
        r'<h4 class="text-center">(.*?)</h4>',
        r'<h4[^>]*>(.*?)</h4>',
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>',
        r'<h2[^>]*>(.*?)</h2>',
        r'<h3[^>]*>(.*?)</h3>'
    ]
    
    # 正则表达式配置 - 内容提取
    content_reg = [
        r'<div class="art-content">(.*?)</div>',
        r'<div class="article-content">(.*?)</div>',
        r'<div class="content">(.*?)</div>',
        r'<div class="post-content">(.*?)</div>',
        r'<div class="entry-content">(.*?)</div>',
        r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>'
    ]
    
    # 状态正则表达式配置
    status_reg = [
        r'状态[:：]\s*(.*?)[<\s]',
        r'status[:：]\s*(.*?)[<\s]'
    ]
    
    # 支持的书籍类型 - 都是短篇
    book_type = ["短篇"]
    
    # 处理函数配置
    after_crawler_func = [
        "_clean_html_content"  # 公共基类提供的HTML清理
    ]
    
    def _detect_book_type(self, content: str) -> str:
        """
        重写书籍类型检测，确保始终返回"短篇"
        
        Args:
            content: 页面内容
            
        Returns:
            书籍类型 - 始终返回"短篇"
        """
        return "短篇"
    
    def get_novel_url(self, novel_id: str) -> str:
        """
        根据小说ID生成小说URL
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说URL
        """
        return f"{self.base_url}/artdetail/{novel_id}.html"
    
    def extract_content(self, html: str) -> str:
        """
        提取书籍内容，重写基类方法以适应特殊格式
        
        Args:
            html: 页面HTML内容
            
        Returns:
            提取的文本内容
        """
        try:
            # 直接提取从 <div class="art-content"> 开始到 <div class="right"> 之前的所有内容
            content_match = re.search(r'<div class="art-content">(.*?)(?=<div class="right">)', html, re.DOTALL)
            if content_match:
                content = content_match.group(1)
                logger.info(f"提取到内容，长度: {len(content)}")
                
                # 首先提取可见内容（在span标签之前的内容）
                visible_content = ""
                visible_match = re.search(r'^(.*?)(?=<span[^>]*id="xiaoshuo_str")', content, re.DOTALL)
                if visible_match:
                    visible_part = visible_match.group(1)
                    # 移除广告和无关的div
                    visible_part = re.sub(r'<div[^>]*class="download_app"[^>]*>.*?</div>', '', visible_part, flags=re.DOTALL)
                    visible_part = re.sub(r'<div[^>]*id="open_xiaoshuo_str"[^>]*>.*?</div>', '', visible_part, flags=re.DOTALL)
                    # 移除所有a标签及其内容（广告）
                    visible_part = re.sub(r'<a[^>]*>.*?</a>', '', visible_part, flags=re.DOTALL)
                    # 处理嵌套的p标签
                    visible_part = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', visible_part, flags=re.DOTALL)
                    # 移除所有HTML标签，但保留内容
                    visible_content = re.sub(r'<[^>]+>', '\n', visible_part)
                    visible_content = re.sub(r'\n\s*\n\s*\n', '\n\n', visible_content).strip()
                
                # 提取隐藏内容（在span标签内的内容）
                hidden_content = ""
                # 首先尝试更精确的匹配
                hidden_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none;">([^<]*(?:<(?!/?span[^>]*>)[^<]*)*)</span>', content, re.DOTALL)
                if not hidden_match:
                    hidden_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*style="display:none"([^<]*(?:<(?!/?span[^>]*>)[^<]*)*)</span>', content, re.DOTALL)
                if not hidden_match:
                    hidden_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*>([^<]*(?:<(?!/?span[^>]*>)[^<]*)*)</span>', content, re.DOTALL)
                
                if hidden_match:
                    hidden_part = hidden_match.group(1)
                    logger.info(f"提取到隐藏内容原始长度: {len(hidden_part)}")
                    # 移除所有a标签及其内容（广告）
                    hidden_part = re.sub(r'<a[^>]*>.*?</a>', '', hidden_part, flags=re.DOTALL)
                    # 处理嵌套的p标签
                    hidden_part = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', hidden_part, flags=re.DOTALL)
                    # 处理br标签
                    hidden_part = re.sub(r'<br[^>]*>', '\n', hidden_part, flags=re.IGNORECASE)
                    # 移除所有HTML标签，但保留内容
                    hidden_part = re.sub(r'<[^>]+>', '\n', hidden_part)
                    hidden_part = re.sub(r'\n\s*\n\s*\n', '\n\n', hidden_part).strip()
                    hidden_content = hidden_part
                    logger.info(f"处理后隐藏内容长度: {len(hidden_content)}")
                else:
                    logger.warning("未能匹配到隐藏内容，尝试更宽松的模式")
                    # 尝试更宽松的匹配
                    loose_match = re.search(r'<span[^>]*id="xiaoshuo_str"[^>]*>(.*?)</span>', content, re.DOTALL)
                    if loose_match:
                        hidden_part = loose_match.group(1)
                        logger.info(f"宽松模式提取到隐藏内容原始长度: {len(hidden_part)}")
                        # 移除所有a标签及其内容（广告）
                        hidden_part = re.sub(r'<a[^>]*>.*?</a>', '', hidden_part, flags=re.DOTALL)
                        # 处理嵌套的p标签
                        hidden_part = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', hidden_part, flags=re.DOTALL)
                        # 处理br标签
                        hidden_part = re.sub(r'<br[^>]*>', '\n', hidden_part, flags=re.IGNORECASE)
                        # 移除所有HTML标签，但保留内容
                        hidden_part = re.sub(r'<[^>]+>', '\n', hidden_part)
                        hidden_part = re.sub(r'\n\s*\n\s*\n', '\n\n', hidden_part).strip()
                        hidden_content = hidden_part
                        logger.info(f"宽松模式处理后隐藏内容长度: {len(hidden_content)}")
                    else:
                        logger.error("所有模式都无法提取隐藏内容")
                
                # 合并可见内容和隐藏内容
                full_content = visible_content + "\n" + hidden_content
                logger.info(f"可见内容长度: {len(visible_content)}, 隐藏内容长度: {len(hidden_content)}, 总内容长度: {len(full_content)}")
                
                return full_content.strip()
            
            # 如果没有找到，尝试使用默认正则提取
            logger.warning("未找到art-content到right之间的内容，使用默认方法")
            return self._extract_with_regex(html, self.content_reg)
            
        except Exception as e:
            logger.warning(f"内容提取失败: {e}")
            return ""
    
    def _parse_single_chapter_novel(self, content: str, novel_url: str, title: str) -> Dict[str, Any]:
        """
        重写基类的单章节小说解析方法，使用自定义的内容提取逻辑
        
        Args:
            content: 页面内容
            novel_url: 小说URL
            title: 小说标题
            
        Returns:
            小说详情信息
        """
        # 使用自定义的内容提取方法
        chapter_content = self.extract_content(content)
        
        if not chapter_content:
            raise Exception("无法提取小说内容")
        
        # 执行爬取后处理函数
        processed_content = self._execute_after_crawler_funcs(chapter_content)
        
        return {
            'title': title,
            'content': processed_content,
            'type': '短篇',
            'source_url': novel_url,
            'author': self.name,
            'status': '已完结'
        }
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        重写基类的保存方法，适应单章节小说格式
        
        Args:
            novel_content: 小说内容字典
            storage_folder: 存储文件夹
            
        Returns:
            文件路径
        """
        import os
        import re
        
        # 确保存储目录存在
        os.makedirs(storage_folder, exist_ok=True)
        
        # 生成文件名（使用标题，避免特殊字符）
        title = novel_content.get('title', '未知标题')
        filename = re.sub(r'[<>:"/\\|?*]', '_', title)
        file_path = os.path.join(storage_folder, f"{filename}.txt")
        
        # 如果文件已存在，添加序号
        # counter = 1
        original_path = file_path
        # 如果文件已经存在, 则增书籍网站名称.
        if os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{self.novel_site_name}.txt')
        # 如果书籍网站名称的文件也存在, 则返回错误
        if os.path.exists(file_path):
            return 'already_exists'
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write(f"## {title}\n\n")
            
            # 写入内容（单章节格式）
            content = novel_content.get('content', '')
            if content:
                f.write(content)
            
            # 写入元信息
            f.write("\n\n")
            f.write(f"作者: {novel_content.get('author', self.name)}\n")
            f.write(f"来源: {novel_content.get('source_url', '')}\n")
            f.write(f"状态: {novel_content.get('status', '未知')}\n")
        
        logger.info(f"文件已保存: {file_path}")
        return file_path
    
    def save_to_file(self, novel_content: Dict[str, Any], storage_folder: str) -> str:
        """
        重写基类的保存文件方法，适应单章节格式
        
        Args:
            novel_content: 小说内容字典
            storage_folder: 存储文件夹
            
        Returns:
            文件路径
        """
        # 确保存储目录存在
        import os
        import re
        os.makedirs(storage_folder, exist_ok=True)
        
        # 生成文件名（使用标题，避免特殊字符）
        title = novel_content.get('title', '未知标题')
        filename = re.sub(r'[<>:"/\\|?*]', '_', title)
        file_path = os.path.join(storage_folder, f"{filename}.txt")
        
        # 如果文件已存在，添加序号
        original_path = file_path
        if os.path.exists(file_path):
            file_path = original_path.replace('.txt', f'_{self.novel_site_name}.txt')
        if os.path.exists(file_path):
            return 'already_exists'
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write(f"## {title}\n\n")
            
            # 写入内容
            content = novel_content.get('content', '')
            f.write(content)
            f.write("\n")
        
        return file_path