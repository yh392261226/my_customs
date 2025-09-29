"""
样式隔离解决方案 - 通过CSS命名空间实现样式隔离
"""

import os
from pathlib import Path
from typing import Dict, Set, List, Optional
import re

from src.utils.logger import get_logger

logger = get_logger(__name__)

class StyleIsolationManager:
    """
    样式隔离管理器
    通过为每个屏幕创建CSS命名空间来隔离样式
    """
    
    def __init__(self, styles_dir: str):
        """
        初始化样式隔离管理器
        
        Args:
            styles_dir: 样式文件目录
        """
        self.styles_dir = Path(styles_dir)
        self._processed_files: Set[str] = set()
        self._screen_namespaces: Dict[str, str] = {}
        
        # 屏幕到CSS文件的映射
        self._screen_css_mapping = {
            "WelcomeScreen": ["styles.css"],
            "BookshelfScreen": ["bookshelf.css", "styles.css"],
            "ReaderScreen": ["terminal_reader.css", "styles.css"],
            "SettingsScreen": ["settings_screen.css", "styles.css"],
            "FileExplorerScreen": ["file_explorer.css", "styles.css"],
            "StatisticsScreen": ["statistics.css", "styles.css"],
            "HelpScreen": ["help_screen.css", "styles.css"],
            "BossKeyScreen": ["boss_key.css", "styles.css"],
            "GetBooksScreen": ["styles.css"],
            "ProxyListScreen": ["proxy_list_screen.css", "styles.css"],
            "NovelSitesManagementScreen": ["novel_sites_management_screen.css", "styles.css"],
            "CrawlerManagementScreen": ["crawler_management_screen.css", "styles.css"],
        }
    
    def create_isolated_css(self, screen_name: str) -> Optional[str]:
        """
        为指定屏幕创建隔离的CSS文件
        
        Args:
            screen_name: 屏幕名称
            
        Returns:
            Optional[str]: 生成的CSS内容，如果失败返回None
        """
        if screen_name not in self._screen_css_mapping:
            logger.warning(f"未找到屏幕 {screen_name} 的CSS映射")
            return None
        
        css_files = self._screen_css_mapping[screen_name]
        namespace = f"screen-{screen_name.lower()}"
        self._screen_namespaces[screen_name] = namespace
        
        css_content = []
        
        for css_file in css_files:
            file_path = self.styles_dir / css_file
            
            if not file_path.exists():
                logger.warning(f"CSS文件不存在: {file_path}")
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 为CSS内容添加命名空间
                isolated_content = self._add_namespace(content, namespace)
                css_content.append(f"/* {css_file} */\n{isolated_content}\n")
                
            except Exception as e:
                logger.error(f"处理CSS文件失败 {file_path}: {e}")
                continue
        
        if css_content:
            return "\n".join(css_content)
        
        return None
    
    def _add_namespace(self, css_content: str, namespace: str) -> str:
        """
        为CSS内容添加命名空间
        
        Args:
            css_content: 原始CSS内容
            namespace: 命名空间
            
        Returns:
            str: 添加命名空间后的CSS内容
        """
        # 处理CSS规则，为选择器添加命名空间
        lines = css_content.split('\n')
        processed_lines = []
        
        in_comment = False
        in_rule = False
        current_rule = []
        
        for line in lines:
            line = line.strip()
            
            # 处理注释
            if line.startswith('/*'):
                in_comment = True
                processed_lines.append(line)
                continue
            
            if in_comment and '*/' in line:
                in_comment = False
                processed_lines.append(line)
                continue
            
            if in_comment:
                processed_lines.append(line)
                continue
            
            # 空行
            if not line:
                processed_lines.append(line)
                continue
            
            # CSS规则开始
            if line.endswith('{'):
                # 处理当前规则
                if current_rule:
                    processed_rule = self._process_rule(current_rule, namespace)
                    processed_lines.extend(processed_rule)
                    current_rule = []
                
                current_rule.append(line)
                in_rule = True
            
            # CSS规则内容
            elif in_rule:
                if line == '}':
                    # 规则结束
                    current_rule.append(line)
                    processed_rule = self._process_rule(current_rule, namespace)
                    processed_lines.extend(processed_rule)
                    current_rule = []
                    in_rule = False
                else:
                    current_rule.append(line)
            
            # 其他情况（如@规则）
            else:
                processed_lines.append(line)
        
        # 处理最后一个规则
        if current_rule:
            processed_rule = self._process_rule(current_rule, namespace)
            processed_lines.extend(processed_rule)
        
        return '\n'.join(processed_lines)
    
    def _process_rule(self, rule_lines: List[str], namespace: str) -> List[str]:
        """
        处理单个CSS规则，为其添加命名空间
        
        Args:
            rule_lines: 规则行列表
            namespace: 命名空间
            
        Returns:
            List[str]: 处理后的规则行列表
        """
        if not rule_lines:
            return []
        
        # 提取选择器
        selector_line = rule_lines[0]
        
        # 跳过@规则和特殊规则
        if selector_line.startswith('@'):
            return rule_lines
        
        # 处理选择器
        if '{' in selector_line:
            selector_part = selector_line.split('{')[0].strip()
            brace_part = selector_line.split('{')[1]
            
            # 为选择器添加命名空间
            processed_selectors = []
            selectors = selector_part.split(',')
            
            for selector in selectors:
                selector = selector.strip()
                
                # 跳过特殊选择器（如:hover, :focus等）
                if selector.startswith(':') or selector.startswith('@'):
                    processed_selectors.append(selector)
                else:
                    # 为普通选择器添加命名空间
                    processed_selectors.append(f".{namespace} {selector}")
            
            processed_selector = ', '.join(processed_selectors)
            processed_line = f"{processed_selector} {{ {brace_part}"
        else:
            # 规则跨越多行的情况
            processed_selectors = []
            selectors = selector_line.split(',')
            
            for selector in selectors:
                selector = selector.strip()
                
                if selector.startswith(':') or selector.startswith('@'):
                    processed_selectors.append(selector)
                else:
                    processed_selectors.append(f".{namespace} {selector}")
            
            processed_selector = ', '.join(processed_selectors)
            processed_line = processed_selector
        
        result = [processed_line]
        result.extend(rule_lines[1:])
        
        return result
    
    def get_screen_namespace(self, screen_name: str) -> str:
        """
        获取屏幕的CSS命名空间
        
        Args:
            screen_name: 屏幕名称
            
        Returns:
            str: CSS命名空间类名
        """
        return self._screen_namespaces.get(screen_name, f"screen-{screen_name.lower()}")
    
    def cleanup(self) -> None:
        """清理资源"""
        self._processed_files.clear()
        self._screen_namespaces.clear()


def apply_style_isolation(screen_instance) -> None:
    """
    为屏幕实例应用样式隔离
    
    Args:
        screen_instance: 屏幕实例
    """
    screen_name = screen_instance.__class__.__name__
    
    # 获取样式目录
    styles_dir = Path(__file__).parent
    
    # 创建样式隔离管理器
    isolation_manager = StyleIsolationManager(str(styles_dir))
    
    # 生成隔离的CSS
    isolated_css = isolation_manager.create_isolated_css(screen_name)
    
    if isolated_css:
        # 获取命名空间
        namespace = isolation_manager.get_screen_namespace(screen_name)
        
        # 为屏幕容器添加命名空间类
        if hasattr(screen_instance, 'add_class'):
            # 添加命名空间类
            screen_instance.add_class(namespace)
        
        logger.debug(f"为屏幕 {screen_name} 应用样式隔离，命名空间: {namespace}")
    
    isolation_manager.cleanup()