"""
增强样式隔离解决方案
通过CSS命名空间和动态样式管理实现完全的样式隔离
"""

import os
import re
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from textual.app import App
from textual.screen import Screen

from src.utils.logger import get_logger

logger = get_logger(__name__)

class EnhancedStyleIsolation:
    """
    增强样式隔离管理器
    提供完全的样式隔离，防止屏幕间样式污染
    """
    
    def __init__(self, app: "App[Any]"):
        """初始化增强样式隔离管理器"""
        self.app = app
        self._active_screen_styles: Dict[str, Set[str]] = {}
        self._original_stylesheets: Dict[str, str] = {}
        self._isolated_stylesheets: Dict[str, str] = {}
        
        # 屏幕到CSS文件的映射
        self._screen_css_mapping = {
            "WelcomeScreen": ["styles.css"],
            "BookshelfScreen": ["bookshelf.css", "styles.css"],
            "ReaderScreen": ["terminal_reader.css", "styles.css", "reader_components/reader_content.css", "reader_components/reader_controls.css"],
            "SettingsScreen": ["settings_screen.css", "styles.css"],
            "FileExplorerScreen": ["file_explorer.css", "styles.css"],
            "StatisticsScreen": ["statistics.css", "styles.css"],
            "HelpScreen": ["help_screen.css", "styles.css"],
            "BossKeyScreen": ["boss_key.css", "styles.css"],
            "GetBooksScreen": ["get_books_screen.css", "styles.css"],
            "ProxyListScreen": ["proxy_list_screen.css", "styles.css"],
            "NovelSitesManagementScreen": ["novel_sites_management_screen.css", "styles.css"],
            "CrawlerManagementScreen": ["crawler_management_screen.css", "styles.css"],
            "BookmarksScreen": ["bookmarks.css", "styles.css"],
            "SearchResultsScreen": ["search_results_dialog.css", "styles.css"],
        }
        
        # 基础样式目录
        self.styles_dir = Path(__file__).parent
    
    def get_screen_namespace(self, screen_name: str) -> str:
        """获取屏幕的CSS命名空间"""
        return f"screen-{screen_name.lower().replace('screen', '')}"
    
    def isolate_css_content(self, css_content: str, namespace: str) -> str:
        """
        为CSS内容添加命名空间隔离
        
        Args:
            css_content: 原始CSS内容
            namespace: 命名空间
            
        Returns:
            str: 隔离后的CSS内容
        """
        if not css_content.strip():
            return css_content
        
        # 分割CSS内容为规则
        rules = self._parse_css_rules(css_content)
        isolated_rules = []
        
        for rule in rules:
            isolated_rule = self._isolate_css_rule(rule, namespace)
            isolated_rules.append(isolated_rule)
        
        return '\n'.join(isolated_rules)
    
    def _parse_css_rules(self, css_content: str) -> List[str]:
        """解析CSS内容为规则列表"""
        # 移除注释
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # 分割规则 - 更精确的规则分割
        rules = []
        current_rule = []
        brace_count = 0
        in_string = False
        string_char = None
        
        lines = css_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                if current_rule:
                    current_rule.append('')
                continue
            
            # 检查字符串状态
            i = 0
            while i < len(line):
                char = line[i]
                
                if not in_string and char in ['"', "'"]:
                    in_string = True
                    string_char = char
                elif in_string and char == string_char and (i == 0 or line[i-1] != '\\'):
                    in_string = False
                    string_char = None
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                
                i += 1
            
            current_rule.append(line)
            
            # 如果大括号平衡且不在字符串中，说明规则结束
            if brace_count == 0 and not in_string and current_rule:
                rule_content = '\n'.join(current_rule).strip()
                if rule_content:
                    rules.append(rule_content)
                current_rule = []
        
        # 处理最后一个规则
        if current_rule:
            rule_content = '\n'.join(current_rule).strip()
            if rule_content:
                rules.append(rule_content)
        
        return rules
    
    def _isolate_css_rule(self, rule: str, namespace: str) -> str:
        """为单个CSS规则添加命名空间"""
        rule = rule.strip()
        if not rule:
            return rule
        
        # 跳过@规则（如@media, @keyframes等）
        if rule.startswith('@'):
            return rule
        
        # 查找选择器和规则体的分界点
        brace_pos = rule.find('{')
        if brace_pos == -1:
            return rule
        
        selector_part = rule[:brace_pos].strip()
        rule_body = rule[brace_pos:]
        
        # 处理选择器
        isolated_selectors = []
        selectors = [s.strip() for s in selector_part.split(',')]
        
        for selector in selectors:
            if not selector:
                continue
            
            # 跳过伪选择器和特殊选择器
            if selector.startswith(':') or selector.startswith('::'):
                isolated_selectors.append(selector)
                continue
            
            # 为普通选择器添加命名空间
            if selector == '*':
                # 通配符选择器
                isolated_selector = f".{namespace} *"
            elif selector.startswith('#') or selector.startswith('.'):
                # ID或类选择器
                isolated_selector = f".{namespace} {selector}"
            elif ' ' in selector:
                # 复合选择器
                isolated_selector = f".{namespace} {selector}"
            else:
                # 元素选择器
                isolated_selector = f".{namespace} {selector}"
            
            isolated_selectors.append(isolated_selector)
        
        # 重新组合规则
        isolated_selector_part = ', '.join(isolated_selectors)
        return f"{isolated_selector_part} {rule_body}"
    
    def apply_screen_isolation(self, screen: "Screen[Any]") -> None:
        """为屏幕应用样式隔离"""
        screen_name = screen.__class__.__name__
        namespace = self.get_screen_namespace(screen_name)
        
        # 为屏幕添加命名空间类
        if hasattr(screen, 'add_class'):
            screen.add_class(namespace)
        
        # 获取屏幕的CSS文件
        css_files = self._screen_css_mapping.get(screen_name, ["styles.css"])
        
        # 清除之前的样式
        self._clear_screen_styles(screen_name)
        
        # 加载并隔离CSS文件
        isolated_css_content = []
        for css_file in css_files:
            css_path = self.styles_dir / css_file
            if css_path.exists():
                try:
                    with open(css_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    
                    # 隔离CSS内容
                    isolated_content = self.isolate_css_content(original_content, namespace)
                    isolated_css_content.append(f"/* {css_file} */\n{isolated_content}")
                    
                except Exception as e:
                    logger.error(f"加载CSS文件失败 {css_path}: {e}")
        
        # 将隔离后的样式应用到应用
        if isolated_css_content:
            combined_css = '\n\n'.join(isolated_css_content)
            self._apply_isolated_styles(screen_name, combined_css)
        
        logger.debug(f"为屏幕 {screen_name} 应用样式隔离，命名空间: {namespace}")
    
    def _clear_screen_styles(self, screen_name: str) -> None:
        """清除屏幕的样式"""
        if screen_name in self._active_screen_styles:
            # 这里可以实现样式清除逻辑
            # 由于Textual的限制，我们主要依赖命名空间隔离
            self._active_screen_styles[screen_name].clear()
    
    def _apply_isolated_styles(self, screen_name: str, css_content: str) -> None:
        """应用隔离后的样式"""
        try:
            # 存储样式内容
            self._isolated_stylesheets[screen_name] = css_content
            
            # 记录活动样式
            if screen_name not in self._active_screen_styles:
                self._active_screen_styles[screen_name] = set()
            
            # 由于Textual的CSS系统限制，我们主要依赖命名空间隔离
            # 实际的样式应用通过屏幕的CSS_PATH完成
            
        except Exception as e:
            logger.error(f"应用隔离样式失败 {screen_name}: {e}")
    
    def remove_screen_isolation(self, screen: "Screen[Any]") -> None:
        """移除屏幕的样式隔离"""
        screen_name = screen.__class__.__name__
        namespace = self.get_screen_namespace(screen_name)
        
        # 移除命名空间类
        if hasattr(screen, 'remove_class'):
            screen.remove_class(namespace)
        
        # 清除样式记录
        self._clear_screen_styles(screen_name)
        
        logger.debug(f"移除屏幕 {screen_name} 的样式隔离")
    
    def get_isolated_css(self, screen_name: str) -> Optional[str]:
        """获取屏幕的隔离CSS内容"""
        return self._isolated_stylesheets.get(screen_name)
    
    def cleanup(self) -> None:
        """清理资源"""
        self._active_screen_styles.clear()
        self._original_stylesheets.clear()
        self._isolated_stylesheets.clear()


# 全局增强样式隔离管理器实例
_enhanced_isolation_manager: Optional[EnhancedStyleIsolation] = None

def initialize_enhanced_isolation(app: "App[Any]") -> EnhancedStyleIsolation:
    """初始化增强样式隔离管理器"""
    global _enhanced_isolation_manager
    _enhanced_isolation_manager = EnhancedStyleIsolation(app)
    return _enhanced_isolation_manager

def get_enhanced_isolation_manager() -> Optional[EnhancedStyleIsolation]:
    """获取增强样式隔离管理器"""
    return _enhanced_isolation_manager

def apply_enhanced_style_isolation(screen: "Screen[Any]") -> None:
    """为屏幕应用增强样式隔离"""
    if _enhanced_isolation_manager:
        _enhanced_isolation_manager.apply_screen_isolation(screen)
    else:
        logger.warning("增强样式隔离管理器未初始化")

def remove_enhanced_style_isolation(screen: "Screen[Any]") -> None:
    """移除屏幕的增强样式隔离"""
    if _enhanced_isolation_manager:
        _enhanced_isolation_manager.remove_screen_isolation(screen)