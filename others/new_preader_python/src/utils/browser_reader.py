"""
自定义浏览器阅读器模块

提供在浏览器中打开书籍的功能，支持自定义样式（背景、字体、颜色等）
支持阅读进度同步到数据库
"""

import os
import platform
import tempfile
import webbrowser
import json
import time
import uuid
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import parse_qs, urlparse

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 全局字典，保存服务器对象以防止被垃圾回收
_active_servers: Dict[str, Dict[str, Any]] = {}


class BrowserReader:
    """浏览器阅读器类"""

    @staticmethod
    def get_permission_script():
        """生成权限检查JavaScript代码"""
        try:
            from src.utils.multi_user_manager import MultiUserManager
            user_permissions = MultiUserManager.get_current_user_permissions()
            is_multi_user = MultiUserManager.is_multi_user_enabled()
            current_user = MultiUserManager.get_current_user()
            
            # 确保包含浏览器阅读器需要的细粒度权限
            required_permissions = [
                "book.read", "book.write", "book.add", "book.delete",
                "bookmark.read", "bookmark.write", "bookmark.delete",
                "settings.read", "settings.write",
                "search.read", "stats.read"
            ]
            
            # 添加缺失的权限
            for perm in required_permissions:
                if perm not in user_permissions:
                    user_permissions.append(perm)
                    
        except:
            user_permissions = [
                "read", "write", "delete", "manage_users", "manage_books", "manage_settings",
                "book.read", "book.write", "book.add", "book.delete",
                "bookmark.read", "bookmark.write", "bookmark.delete",
                "settings.read", "settings.write",
                "search.read", "stats.read"
            ]
            is_multi_user = False
            current_user = {"id": 1, "role": "super_admin"}
        
        permissions_json = json.dumps(user_permissions)
        user_json = json.dumps(current_user)
        
        return f"""
        // 权限管理
        window.userPermissions = {permissions_json};
        window.isMultiUser = {str(is_multi_user).lower()};
        window.currentUser = {user_json};
        
        function hasPermission(permission) {{
            return window.userPermissions.includes(permission);
        }}
        
        function checkPermission(operation) {{
            if (!hasPermission(operation)) {{
                alert(t('browser_reader.permission_denied', {{operation: operation}}));
                return false;
            }}
            return true;
        }}
        """

    @staticmethod
    def get_translations():
        """获取浏览器阅读器的翻译"""
        try:
            from src.locales.i18n_manager import get_global_i18n, init_global_i18n
            try:
                i18n = get_global_i18n()
            except RuntimeError:
                init_global_i18n()
                i18n = get_global_i18n()
            
            # 获取当前语言
            current_lang = getattr(i18n, 'current_language', 'zh_CN')
            
            # 直接从文件加载翻译数据
            import json
            import os
            translation_file = f'/Users/yanghao/data/app/python/newreader/src/locales/{current_lang}/translation.json'
            
            if os.path.exists(translation_file):
                with open(translation_file, 'r', encoding='utf-8') as f:
                    file_translations = json.load(f)
                    browser_translations = file_translations.get('browser_reader', {})
            else:
                # 如果文件不存在，使用默认翻译
                browser_translations = {
                    "title": "浏览器阅读器",
                    "permission_denied": "无权限执行此操作: {{operation}}",
                    "font_button": "字体",
                    "font_settings_title": "字体设置",
                    "highlight_button": "高亮",
                    "notes_button": "笔记",
                    "search_button": "搜索",
                    "stats_button": "统计",
                    "pagination_settings": "翻页设置",
                    "print_button": "打印",
                    "progress_sync": "进度同步",
                    "import_file": "导入文件",
                    "bottom": "底部",
                    "toc_toggle_title": "目录",
                    "bookmark_title": "书签",
                    "auto_scroll_start": "开始滚动",
                    "reset_button": "重置",
                    "preview": "预览",
                    "load": "加载",
                    "delete": "删除",
                    "no_custom_themes": "暂无自定义主题",
                    "theme_manager": "主题管理",
                    "note_placeholder": "输入笔记内容...",
                    "search_placeholder": "搜索内容...",
                    "auto_extract_title": "自动从文件名提取",
                    "add_directory": "添加目录",
                    "add_directory_title": "添加目录",
                    "select_directory_label": "选择目录",
                    "select_directory_hint": "将目录拖放到此处",
                    "or_click_select_directory": "或点击选择目录",
                    "selected_directory": "已选择的目录",
                    "no_directory_selected": "未选择目录",
                    "directory_path": "目录路径",
                    "directory_path_placeholder": "请输入书籍所在目录的路径",
                    "recursive_scan": "递归扫描子目录",
                    "confirm_add_directory": "确认添加",
                    "scan_in_progress": "正在扫描目录...",
                    "scan_success": "成功添加 {count} 本书籍",
                    "scan_failed": "扫描目录失败",
                    "no_books_found": "目录中没有找到支持的书籍文件",
                    "position_jump": {
                        "title": "位置跳转",
                        "input_label": "输入位置百分比 (0-100):",
                        "input_placeholder": "0.00",
                        "jump_button": "跳转",
                        "jump_button_title": "跳转到指定位置",
                        "quick_jump_label": "快速跳转:",
                        "jump_25": "25%",
                        "jump_50": "50%",
                        "jump_75": "75%",
                        "input_error": "请输入0-100之间的数值（支持小数点后两位）",
                        "jump_success": "已跳转到 {percentage}% 位置",
                        "jump_25_success": "已跳转到 25% 位置",
                        "jump_50_success": "跳转到 50% 位置",
                        "jump_75_success": "跳转到 75% 位置"
                    }
                }
            
            # 返回带有browser_reader命名空间的翻译
            return {'browser_reader': browser_translations}
        except:
            # 如果无法加载翻译，直接从文件加载
            import json
            import os
            
            try:
                translation_file = '/Users/yanghao/data/app/python/newreader/src/locales/zh_CN/translation.json'
                if os.path.exists(translation_file):
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        file_translations = json.load(f)
                        browser_translations = file_translations.get('browser_reader', {})
                        return {'browser_reader': browser_translations}
            except:
                pass
            
            # 如果文件也加载失败，返回基本的键值对
            return {
                "browser_reader": {
                    "title": "浏览器阅读器",
                    "permission_denied": "无权限执行此操作: {operation}",
                    "font_button": "字体",
                    "font_settings_title": "字体设置",
                    "highlight_button": "高亮",
                    "notes_button": "笔记",
                    "search_button": "搜索",
                    "stats_button": "统计",
                    "pagination_settings": "翻页设置",
                    "print_button": "打印",
                    "progress_sync": "进度同步",
                    "import_file": "导入文件",
                    "bottom": "底部",
                    "toc_toggle_title": "目录",
                    "bookmark_title": "书签",
                    "auto_scroll_start": "开始滚动",
                    "reset_button": "重置",
                    "preview": "预览",
                    "load": "加载",
                    "delete": "删除",
                    "no_custom_themes": "暂无自定义主题",
                    "theme_manager": "主题管理",
                    "add_directory": "添加目录",
                    "add_directory_title": "添加目录",
                    "select_directory_label": "选择目录",
                    "select_directory_hint": "将目录拖放到此处",
                    "or_click_select_directory": "或点击选择目录",
                    "selected_directory": "已选择的目录",
                    "no_directory_selected": "未选择目录",
                    "directory_path": "目录路径",
                    "directory_path_placeholder": "请输入书籍所在目录的路径",
                    "recursive_scan": "递归扫描子目录",
                    "confirm_add_directory": "确认添加",
                    "scan_in_progress": "正在扫描目录...",
                    "scan_success": "成功添加 {count} 本书籍",
                    "scan_failed": "扫描目录失败",
                    "no_books_found": "目录中没有找到支持的书籍文件",
                    "position_jump": {
                        "title": "位置跳转",
                        "input_label": "输入位置百分比 (0-100):",
                        "input_placeholder": "0.00",
                        "jump_button": "跳转",
                        "jump_button_title": "跳转到指定位置",
                        "quick_jump_label": "快速跳转:",
                        "jump_25": "25%",
                        "jump_50": "50%",
                        "jump_75": "75%",
                        "input_error": "请输入0-100之间的数值（支持小数点后两位）",
                        "jump_success": "已跳转到 {percentage}% 位置",
                        "jump_25_success": "已跳转到 25% 位置",
                        "jump_50_success": "已跳转到 50% 位置",
                        "jump_75_success": "跳转到 75% 位置"
                    }
                }
            }

    # 可用字体列表
    FONT_FAMILIES = {
        "system": {
            "name": "系统默认",
            "value": "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif"
        },
        "serif": {
            "name": "宋体/衬线",
            "value": "'SimSun', 'Songti SC', 'Times New Roman', serif"
        },
        "sans-serif": {
            "name": "黑体/无衬线",
            "value": "'SimHei', 'Microsoft YaHei', 'Arial', sans-serif"
        },
        "georgia": {
            "name": "Georgia",
            "value": "'Georgia', 'Times New Roman', serif"
        },
        "kai": {
            "name": "楷体",
            "value": "'KaiTi', 'STKaiti', '楷体', serif"
        },
        "fangsong": {
            "name": "仿宋",
            "value": "'FangSong', 'STFangsong', '仿宋', serif"
        },
        "monospace": {
            "name": "等宽字体",
            "value": "'Courier New', 'Consolas', monospace"
        }
    }

    # 默认阅读主题
    THEMES = {
        "light": {
            "name": "浅色主题",
            "background": "#ffffff",
            "text": "#333333",
            "title": "#000000",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Georgia", "Microsoft YaHei", serif',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "justify",
            "width": "800px",
            "padding": "40px"
        },
        "dark": {
            "name": "深色主题",
            "background": "#1a1a1a",
            "text": "#e0e0e0",
            "title": "#ffffff",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Georgia", "Microsoft YaHei", serif',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "justify",
            "width": "800px",
            "padding": "40px"
        },
        "sepia": {
            "name": "羊皮纸主题",
            "background": "#f4ecd8",
            "text": "#5b4636",
            "title": "#3b3129",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Georgia", "Microsoft YaHei", serif',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "justify",
            "width": "800px",
            "padding": "40px"
        },
        "matrix": {
            "name": "黑客绿主题",
            "background": "#000000",
            "text": "#00ff00",
            "title": "#00ff00",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Courier New", monospace',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "left",
            "width": "800px",
            "padding": "40px"
        },
        "ocean": {
            "name": "海洋蓝主题",
            "background": "#0a1628",
            "text": "#7dd3fc",
            "title": "#38bdf8",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Georgia", "Microsoft YaHei", serif',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "justify",
            "width": "800px",
            "padding": "40px"
        },
        "forest": {
            "name": "森林绿主题",
            "background": "#0d1f0d",
            "text": "#90EE90",
            "title": "#98FB98",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Georgia", "Microsoft YaHei", serif',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "justify",
            "width": "800px",
            "padding": "40px"
        },
        "warm": {
            "name": "暖色调主题",
            "background": "#fef3c7",
            "text": "#78350f",
            "title": "#451a03",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Georgia", "Microsoft YaHei", serif',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "justify",
            "width": "800px",
            "padding": "40px"
        },
        "purple": {
            "name": "紫罗兰主题",
            "background": "#2d1b4e",
            "text": "#e9d5ff",
            "title": "#d8b4fe",
            "line_height": "1.8",
            "font_size": "18",
            "font_family": '"Georgia", "Microsoft YaHei", serif',
            "font_weight": "normal",
            "font_style": "normal",
            "text_decoration": "none",
            "letter_spacing": "0",
            "word_spacing": "0",
            "text_align": "justify",
            "width": "800px",
            "padding": "40px"
        }
    }
    
    @staticmethod
    def create_reader_html(content: str, title: str = "书籍阅读", theme: str = "light", 
                        custom_settings: Optional[Dict[str, str]] = None,
                        save_progress_url: Optional[str] = None,
                        load_progress_url: Optional[str] = None,
                        book_id: Optional[str] = None,
                        initial_progress: Optional[float] = None,
                        browser_server_host: str = "localhost",
                        browser_server_port: int = 54321) -> str:
        """
        创建浏览器阅读器HTML
        
        Args:
            content: 书籍内容
            title: 书籍标题
            theme: 主题名称（light/dark/sepia）
            custom_settings: 自定义设置，可覆盖主题设置
            save_progress_url: 保存进度的API端点
            load_progress_url: 加载进度的API端点
            
        Returns:
            HTML字符串
        """
        # 页面加载完成后执行的全局初始化
        global_init_code = """
        // 页面加载完成后执行
        document.addEventListener('DOMContentLoaded', function() {
            // 初始化主题
            applyTheme(currentSettings);
            
            // 更新跳转弹窗的语言文本
            updatePositionJumpTranslations();
            
            // 加载保存的进度
            loadBookProgress();
            
            // 检查后端状态
            checkBackendStatus();
            
            // 启动自动保存进度
            startAutoSaveProgress();
            
            // 初始化工具栏位置
            updateToolbarTogglePosition();
            
            // 添加键盘快捷键监听
            document.addEventListener('keydown', handleKeyboardShortcuts);
            
            // 初始化老板键模式
            initBossMode();
            
            // 初始化缩略图导航
            initMinimap();
            
            // 监听窗口大小变化
            window.addEventListener('resize', handleWindowResize);
            
            // 监听滚动事件
            window.addEventListener('scroll', handleScroll);
            
            // 初始化阅读统计
            initReadingStats();
            
            // 延迟初始化拖放区域（即使面板未打开也预先初始化）
            setTimeout(() => {
                const dropZone = document.getElementById('dropZone');
                if (dropZone) {
                    console.log('找到拖放区域，开始初始化');
                    console.log('拖放区域类名:', dropZone.className);
                    console.log('拖放区域样式:', window.getComputedStyle(dropZone));
                    initDropZone();
                } else {
                    console.log('未找到拖放区域');
                }
                
                // 初始化书籍状态检查
                initBookStatusCheck();
            }, 500);
        });
        """
        """
        创建浏览器阅读器HTML
        
        Args:
            content: 书籍内容
            title: 书籍标题
            theme: 主题名称（light/dark/sepia）
            custom_settings: 自定义设置，可覆盖主题设置
            save_progress_url: 保存进度的API端点
            load_progress_url: 加载进度的API端点
            
        Returns:
            HTML字符串
        """
        # 获取主题设置
        settings = BrowserReader.THEMES.get(theme, BrowserReader.THEMES["light"]).copy()
        
        # 应用自定义设置
        if custom_settings:
            settings.update(custom_settings)
        
        # 获取翻译文本
        browser_reader_translations = BrowserReader.get_translations()
        browser_reader_title = browser_reader_translations.get('browser_reader', {}).get('title', '浏览器阅读器')
        
        # 生成HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title id="pageTitle" data-original-title="{title} - {browser_reader_title}">{title} - {browser_reader_title}</title>
    
    
    
    <style>
        /* 基础样式重置 */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background-color: {settings['background']};
            color: {settings['text']};
            font-family: {settings['font_family']};
            font-size: {settings['font_size']}px;
            line-height: {settings['line_height']};
            font-weight: {settings['font_weight']};
            font-style: {settings['font_style']};
            text-decoration: {settings['text_decoration']};
            letter-spacing: {settings['letter_spacing']}px;
            word-spacing: {settings['word_spacing']}px;
            text-align: {settings['text_align']};
            padding: {settings['padding']};
            margin: 0 auto;
            max-width: {settings['width']};
            min-height: 100vh;
            transition: all 0.3s ease;
        }}
        
        /* 标题样式 */
        h1 {{
            color: {settings['title']};
            font-size: 2em;
            margin: 1em 0 0.5em 0;
            font-weight: bold;
        }}
        
        h2 {{
            color: {settings['title']};
            font-size: 1.5em;
            margin: 0.8em 0 0.4em 0;
            font-weight: bold;
        }}
        
        h3 {{
            color: {settings['title']};
            font-size: 1.2em;
            margin: 0.6em 0 0.3em 0;
            font-weight: bold;
        }}
        
        /* 段落样式 */
        p {{
            margin: 0.8em 0;
            text-align: justify;
            text-indent: 2em;
        }}
        
        /* 进度条样式 */
        .progress-bar {{
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: rgba(128, 128, 128, 0.2);
            z-index: 1001;
        }}
        
        .progress-fill {{
            height: 100%;
            background: rgba(100, 149, 237, 0.6);
            width: 0%;
            transition: width 0.3s ease;
        }}
        
        .progress-info {{
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: transparent;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            min-width: 100px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            transition: background 0.3s ease;
        }}

        .progress-info:hover {{
            background: rgba(255, 255, 255, 0.95);
        }}

        /* 快捷键提示 */
        .keyboard-hint, #keyboardHint {{
            position: fixed !important;
            bottom: 45px !important;
            right: 10px !important;
            top: auto !important;
            left: auto !important;
            background: transparent;
            padding: 10px;
            border-radius: 4px;
            font-size: 11px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 9999 !important;
            max-width: 200px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            transition: background 0.3s ease;
        }}

        .keyboard-hint:hover, #keyboardHint:hover {{
            background: rgba(255, 255, 255, 0.95);
        }}

        .keyboard-hint h4, #keyboardHint h4 {{
            margin: 0 0 5px 0;
            font-size: 12px;
            color: {settings['title']};
        }}

        .keyboard-hint ul {{
            margin: 0;
            padding-left: 15px;
        }}

        .keyboard-hint li {{
            margin: 2px 0;
        }}

        .keyboard-hint kbd {{
            background: rgba(128, 128, 128, 0.1);
            padding: 1px 4px;
            border-radius: 3px;
            font-family: monospace;
            transition: all 0.2s ease;
            border: 1px solid rgba(128, 128, 128, 0.2);
        }}

        .keyboard-hint kbd:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            border-color: rgba(0, 0, 0, 0.3);
        }}

        /* 章节目录 */
        .toc-container {{
            position: fixed;
            right: 20px;
            top: 80px;
            width: 250px;
            max-height: 70vh;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 998;
            overflow-y: auto;
            display: none;
            transition: all 0.3s ease;
        }}

        .toc-container:hover {{
            background: rgba(255, 255, 255, 0.95);
        }}

        .toc-container.show {{
            display: block;
        }}
        
        .show {{
            display: block;
        }}

        .hide {{
            display: none;
        }}

        .toc-header {{
            padding: 12px 16px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            background: {settings['background']};
            z-index: 1;
        }}

        .toc-header h3 {{
            margin: 0;
            font-size: 16px;
            color: {settings['title']};
        }}

        .toc-close {{
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: {settings['text']};
            padding: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }}

        .toc-close:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            border-radius: 4px;
        }}

        .toc-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}

        .toc-item {{
            padding: 8px 16px;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 14px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.1);
        }}

        .toc-item:hover {{
            background: rgba(128, 128, 128, 0.1);
        }}

        .toc-item.h1 {{
            font-weight: bold;
            padding-left: 16px;
        }}

        .toc-item.h2 {{
            padding-left: 32px;
        }}

        .toc-item.h3 {{
            padding-left: 48px;
        }}

        .toc-item.active {{
            background: rgba(100, 149, 237, 0.15);
            border-left: 3px solid rgba(100, 149, 237, 0.6);
        }}

        /* 目录切换按钮 */
        .toc-toggle-btn {{
            position: fixed;
            right: 20px;
            top: 70px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 997;
            transition: all 0.2s;
        }}

        .toc-toggle-btn:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            transform: scale(1.05);
        }}

        /* 搜索框 */
        .search-container {{
            position: fixed;
            top: 70px;
            left: 20px;
            background: transparent;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            display: none;
            border: 1px solid rgba(128, 128, 128, 0.3);
            transition: background 0.3s ease;
        }}

        .search-container:hover {{
            background: rgba(255, 255, 255, 0.95);
        }}

        .search-container.show {{
            display: block;
        }}

        .search-container input {{
            width: 200px;
            padding: 6px 10px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 4px;
            background: rgba(128, 128, 128, 0.05);
            color: {settings['text']};
            font-size: 14px;
            margin-right: 5px;
        }}

        .library-search input {{
            width: 200px;
            padding: 6px 10px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 4px;
            background: rgba(128, 128, 128, 0.05);
            color: {settings['text']};
            font-size: 14px;
            margin-right: 5px;
        }}

        .search-container button {{
            padding: 6px 12px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}

        .search-container button:hover {{
            color: #000;
            background: rgba(100, 149, 237, 0.8);
        }}

        .search-count {{
            font-size: 12px;
            margin-left: 10px;
            color: {settings['text']};
        }}

        /* 书签按钮 */
        .bookmark-btn {{
            position: fixed;
            right: 70px;
            top: 70px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 997;
            transition: all 0.2s;
        }}

        .bookmark-btn:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            transform: scale(1.05);
        }}

        .bookmark-btn.bookmarked {{
            color: #ffd700;
            border-color: #ffd700;
        }}

        /* 阅读统计 */
        .reading-stats {{
            position: fixed;
            bottom: 140px;
            right: 10px;
            background: transparent;
            padding: 10px;
            border-radius: 4px;
            font-size: 11px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            min-width: 120px;
            transition: background 0.3s ease;
        }}

        .reading-stats:hover {{
            background: rgba(255, 255, 255, 0.95);
        }}

        .reading-stats p {{
            margin: 3px 0;
        }}

        /* 高亮搜索结果 */
        ::-webkit-input-placeholder {{
            color: rgba(128, 128, 128, 0.5);
        }}
        
        /* 工具栏样式 */
        .toolbar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: {settings['background']};
            border-bottom: 1px solid rgba(128, 128, 128, 0.3);
            padding: 10px 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            flex-wrap: wrap;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }}

        /* 缩略图导航样式 */
        .minimap-container {{
            position: fixed;
            left: 0;
            top: 210px;
            width: 120px;
            height: 60vh;
            max-height: 600px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-left: none;
            border-radius: 0 8px 8px 0;
            z-index: 996;
            overflow: hidden;
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
        }}

        .minimap-container:hover {{
            background: rgba(255, 255, 255, 0.1);
            width: 140px;
        }}

        .minimap-content {{
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            bottom: 0;
            overflow: hidden;
            background: rgba(0, 0, 0, 0.15);
            border-radius: 0 0 6px 0;
        }}
        
        .minimap-content-inner {{
            position: relative;
            width: 100%;
            height: 100%;
            transform-origin: top left;
            transform: scale(0.15);
            margin-left: 8px;
            margin-top: 8px;
            pointer-events: none;
            overflow: hidden;
        }}
        
        .minimap-content::-webkit-scrollbar {{
            width: 2px;
        }}
        
        .minimap-content::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        .minimap-content::-webkit-scrollbar-thumb {{
            background: rgba(128, 128, 128, 0.3);
            border-radius: 1px;
        }}

        .minimap-viewport {{
            position: absolute;
            left: -2px;
            right: -2px;
            width: calc(100% + 4px);
            background: rgba(100, 149, 237, 0.3);
            border: 3px solid rgba(100, 149, 237, 1);
            pointer-events: none;
            transition: top 0.05s ease, height 0.05s ease;
            box-shadow: 0 0 8px rgba(100, 149, 237, 0.8);
            min-height: 15px;
            border-radius: 2px;
        }}
        
        .minimap-viewport::before {{
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            pointer-events: none;
            border-radius: 3px;
        }}
        
        .minimap-viewport::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(180deg, 
                rgba(100, 149, 237, 0.2) 0%, 
                rgba(100, 149, 237, 0.1) 50%, 
                rgba(100, 149, 237, 0.2) 100%);
            pointer-events: none;
            border-radius: 1px;
        }}

        .minimap-toggle {{
            position: fixed;
            left: 10px;
            top: 170px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            width: 32px;
            height: 32px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 997;
            transition: all 0.2s;
        }}

        .minimap-toggle:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            transform: scale(1.05);
        }}

        .minimap-toggle.active {{
            background: rgba(100, 149, 237, 0.3);
            border-color: rgba(100, 149, 237, 0.6);
        }}

        .minimap-container.hidden {{
            transform: translateX(-100%);
        }}

        .minimap-container.collapsed {{
            width: 40px;
        }}

        .minimap-container.collapsed .minimap-content {{
            transform: scale(0.05);
            margin-left: 5px;
            margin-top: 5px;
        }}

        /* 章节标记 */
        .minimap-chapter-marker {{
            position: absolute;
            left: 0;
            width: 100%;
            height: 2px;
            background: rgba(255, 165, 0, 0.6);
            pointer-events: none;
        }}

        /* 搜索结果标记 */
        .minimap-search-marker {{
            position: absolute;
            left: 0;
            width: 100%;
            height: 2px;
            background: rgba(255, 255, 0, 0.8);
            pointer-events: none;
        }}

        .toolbar.collapsed {{
            transform: translateY(-100%);
            opacity: 0;
        }}

        /* 工具栏收缩按钮容器 */
        .toolbar-toggle-container {{
            position: fixed;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1001;
            transition: top 0.3s ease;
        }}

        /* 工具栏收缩按钮 */
        .toolbar-toggle-btn {{
            width: 80px;
            height: 24px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            cursor: pointer;
            border-radius: 0 0 12px 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            transition: all 0.3s ease;
            padding: 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}

        .toolbar-toggle-btn:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            transform: scale(1.05);
        }}

        #toolbarToggleIcon {{
            transition: transform 0.3s ease;
            user-select: none;
        }}
        
        .toolbar button {{
            padding: 6px 12px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
            transition: all 0.2s;
        }}
        
        .toolbar button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}
        
        .toolbar button:active {{
            transform: scale(0.98);
        }}
        
        .toolbar select {{
            padding: 6px 12px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .toolbar select:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}
        
        .toolbar label {{
            color: {settings['text']};
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .toolbar input[type="range"] {{
            width: 100px;
            cursor: pointer;
        }}
        
        
        
        /* 内容区域 */
        .content {{
            margin-top: 60px;
            padding-bottom: 40px;
        }}
        
        /* 选择文本样式 */
        ::selection {{
            background: rgba(100, 149, 237, 0.3);
        }}

        /* 设置面板 */
        .settings-panel {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(128, 128, 128, 0.3);
            transition: background 0.3s ease;
            width: 90%;
            max-width: 500px;
            max-height: 80vh;
            overflow-y: auto;
        }}

        .settings-panel:hover {{
            background: rgba(255, 255, 255, 1);
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 2000;
            max-height: 80vh;
            overflow-y: auto;
        }}

        .settings-content {{
            padding: 20px;
        }}

        .settings-content h3 {{
            margin: 0 0 20px 0;
            color: {settings['title']};
            font-size: 18px;
            border-bottom: 2px solid rgba(128, 128, 128, 0.2);
            padding-bottom: 10px;
        }}

        .settings-close {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: {settings['text']};
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }}

        .settings-close:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            border-radius: 4px;
        }}

        .setting-item {{
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .setting-item label {{
            font-size: 14px;
            color: {settings['text']};
            min-width: 80px;
        }}

        .setting-item select,
        .setting-item input[type="range"],
        .setting-item input[type="color"] {{
            flex: 1;
            margin-left: 10px;
        }}

        .toggle-btn {{
            width: 40px;
            height: 40px;
            border: 2px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.2s;
        }}

        .toggle-btn:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}

        .toggle-btn.active {{
            background: rgba(100, 149, 237, 0.3);
            border-color: rgba(100, 149, 237, 0.6);
        }}

        .setting-actions {{
            display: flex;
            gap: 10px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid rgba(128, 128, 128, 0.2);
        }}

        .setting-actions button {{
            flex: 1;
            padding: 8px 16px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
        }}

        .setting-actions button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}

        /* 笔记和高亮 */
        .notes-tabs {{
            display: flex;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
            margin-bottom: 15px;
        }}

        .tab-btn {{
            flex: 1;
            padding: 10px;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            color: {settings['text']};
            cursor: pointer;
            font-size: 14px;
        }}

        .tab-btn:hover {{
            background: rgba(128, 128, 128, 0.05);
        }}

        .tab-btn.active {{
            border-bottom-color: rgba(100, 149, 237, 0.6);
            color: rgba(100, 149, 237, 1);
        }}

        .notes-content {{
            min-height: 200px;
        }}

        .notes-list {{
            max-height: 300px;
            overflow-y: auto;
            margin-top: 10px;
        }}

        .notes-hint {{
            text-align: center;
            color: rgba(128, 128, 128, 0.7);
            font-size: 12px;
            margin-top: 20px;
        }}

        .note-item {{
            padding: 10px;
            background: rgba(128, 128, 128, 0.05);
            border-radius: 4px;
            margin-bottom: 8px;
            font-size: 13px;
        }}

        .note-item:hover {{
            background: rgba(128, 128, 128, 0.1);
        }}

        .note-text {{
            margin-bottom: 5px;
        }}

        .note-time {{
            font-size: 11px;
            color: rgba(128, 128, 128, 0.7);
        }}

        .note-delete {{
            float: right;
            cursor: pointer;
            color: rgba(255, 0, 0, 0.6);
            font-size: 14px;
        }}

        .note-delete:hover {{
            color: rgba(255, 0, 0, 1);
        }}

        #noteInput {{
            width: 100%;
            padding: 10px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 4px;
            background: {settings['background']};
            color: {settings['text']};
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
        }}

        .add-btn {{
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}

        .add-btn:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}

        /* 位置跳转弹窗专用样式 */
        .position-input {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: #fff;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
            width: 100px;
            transition: all 0.2s ease;
            outline: none;
        }}

        .position-input:focus {{
            background: rgba(255, 255, 255, 0.15);
            border-color: rgba(66, 153, 225, 0.8);
            box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.2);
        }}

        .position-input::placeholder {{
            color: rgba(255, 255, 255, 0.6);
        }}

        .jump-btn {{
            background: rgba(66, 153, 225, 0.8);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s ease;
            margin-left: 8px;
        }}

        .jump-btn:hover {{
            background: rgba(66, 153, 225, 1);
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(66, 153, 225, 0.3);
        }}

        .quick-jump-buttons {{
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }}

        .quick-jump-btn {{
            background: rgba(72, 187, 120, 0.8);
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            min-width: 40px;
            transition: all 0.2s ease;
        }}

        .quick-jump-btn:hover {{
            background: rgba(72, 187, 120, 1);
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(72, 187, 120, 0.3);
        }}

        /* 拖放区域样式 */
        .drop-zone {{
            border: 2px dashed rgba(128, 128, 128, 0.3) !important;
            border-radius: 8px !important;
            padding: 10px 10px !important;
            text-align: center !important;
            background: rgba(128, 128, 128, 0.05) !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            position: relative !important;
            min-height: 120px !important;
            width: 100% !important;
            box-sizing: border-box !important;
            display: block !important;
            margin: 10px 0 !important;
        }}

        .drop-zone:hover {{
            border-color: rgba(100, 149, 237, 0.6);
            background: rgba(100, 149, 237, 0.1);
        }}

        .drop-zone.dragover {{
            border-color: rgba(100, 149, 237, 1);
            background: rgba(100, 149, 237, 0.2);
            transform: scale(1.02);
        }}

        .drop-zone-content {{
            pointer-events: none !important;
            position: relative !important;
            z-index: 1 !important;
        }}

        .drop-icon {{
            font-size: 48px !important;
            margin-bottom: 10px !important;
            opacity: 0.6 !important;
            display: block !important;
        }}

        .drop-hint {{
            font-size: 12px !important;
            color: rgba(128, 128, 128, 0.7) !important;
            margin-top: 5px !important;
            display: block !important;
        }}

        .drop-zone input[type="file"] {{
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            opacity: 0 !important;
            cursor: pointer !important;
            pointer-events: all !important;
            z-index: 2 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            background: transparent !important;
        }}

        /* 高亮样式 */
        .highlight {{
            background-color: rgba(255, 255, 0, 0.4);
            cursor: pointer;
        }}

        .highlight.active {{
            background-color: rgba(255, 255, 0, 0.7);
        }}

        /* 动画 */
        @keyframes fadeInOut {{
            0% {{
                opacity: 0;
                transform: translateX(-50%) translateY(-20px);
            }}
            15% {{
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }}
            85% {{
                opacity: 1;
            }}
            100% {{
                opacity: 0;
            }}
        }}
        
        /* 主题管理面板样式 */
        .theme-manager-panel {{
            max-width: 600px;
        }}
        
        .theme-manager-content {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .current-theme-info {{
            background: rgba(128, 128, 128, 0.05);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(128, 128, 128, 0.2);
        }}
        
        .current-theme-info h4 {{
            margin: 0 0 10px 0;
            color: {settings['title']};
        }}
        
        .current-theme-info p {{
            margin: 5px 0;
            font-size: 14px;
        }}
        
        .theme-actions-top {{
            display: flex;
            justify-content: center;
        }}
        
        .themes-list h4 {{
            margin: 0 0 15px 0;
            color: {settings['title']};
        }}
        
        .theme-item {{
            display: flex;
            align-items: center;
            padding: 10px;
            margin-bottom: 10px;
            background: rgba(128, 128, 128, 0.05);
            border-radius: 8px;
            border: 1px solid rgba(128, 128, 128, 0.2);
        }}
        
        .theme-name {{
            flex: 1;
            font-weight: bold;
            margin-right: 10px;
        }}
        
        .theme-preview {{
            width: 60px;
            height: 30px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            margin-right: 10px;
            border: 1px solid rgba(128, 128, 128, 0.3);
        }}
        
        .theme-actions {{
            display: flex;
            gap: 5px;
        }}
        
        .theme-actions button {{
            padding: 4px 8px;
            font-size: 12px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
        }}

        .theme-actions button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}

        .no-themes {{
            text-align: center;
            color: rgba(128, 128, 128, 0.7);
            padding: 20px;
            font-style: italic;
        }}
        
        /* 夜间模式切换按钮 */
        .night-mode-toggle {{
            position: fixed;
            top: 120px;
            left: 76px;
            transform: translateX(-50%);
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 997;
            transition: all 0.2s;
        }}
        
        .night-mode-toggle:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            transform: translateX(-50%) scale(1.05);
        }}
        
        .night-mode-toggle.active {{
            background: #1a1a1a;
            color: #ffd700;
            border-color: #ffd700;
        }}
        
        /* 全屏状态指示器 */
        .fullscreen-indicator {{
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 3000;
            display: none;
        }}
        
        .fullscreen-indicator.show {{
            display: block;
        }}
        
        /* 增强的阅读统计面板 */
        .reading-stats-enhanced {{
            position: fixed;
            bottom: 140px;
            right: 10px;
            background: transparent;
            padding: 15px;
            border-radius: 8px;
            font-size: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            min-width: 180px;
            transition: background 0.3s ease;
            display:none;
        }}

        .reading-stats-enhanced:hover {{
            background: rgba(255, 255, 255, 0.95);
        }}
        
        .reading-stats-enhanced.show {{
            display: block;
        }}
        
        .reading-stats-enhanced h4 {{
            margin: 0 0 10px 0;
            color: {settings['title']};
            font-size: 14px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
            padding-bottom: 5px;
        }}
        
        .reading-stats-enhanced p {{
            margin: 5px 0;
            display: flex;
            justify-content: space-between;
        }}
        
        .reading-stats-enhanced .stat-value {{
            font-weight: bold;
            color: {settings['title']};
        }}
        
        /* 自动滚动控制面板 */
        .auto-scroll-controls {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: transparent;
            padding: 10px 20px;
            border-radius: 25px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            display: none;
            transition: background 0.3s ease;
        }}

        .auto-scroll-controls:hover {{
            background: rgba(255, 255, 255, 0.95);
            align-items: center;
            gap: 15px;
        }}
        
        .auto-scroll-controls.show {{
            display: flex;
        }}
        
        .auto-scroll-controls button {{
            padding: 6px 12px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}

        .auto-scroll-controls button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}

        .auto-scroll-controls button.active {{
            background: rgba(100, 149, 237, 0.3);
            border-color: rgba(100, 149, 237, 0.6);
        }}
        
        .auto-scroll-controls input[type="range"] {{
            width: 100px;
        }}
        
        .scroll-speed-display {{
            font-size: 14px;
            font-weight: bold;
            color: {settings['title']};
            min-width: 30px;
            text-align: center;
        }}
        
        /* 朗读控制面板 */
        .speech-controls {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: transparent;
            padding: 10px 20px;
            border-radius: 25px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            display: none;
            transition: background 0.3s ease;
        }}

        .speech-controls:hover {{
            background: rgba(255, 255, 255, 0.95);
            align-items: center;
            gap: 15px;
        }}
        
        .speech-controls.show {{
            display: flex;
        }}
        
        .speech-controls button {{
            padding: 6px 12px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}

        .speech-controls button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}

        .speech-controls button.active {{
            background: rgba(100, 149, 237, 0.3);
            border-color: rgba(100, 149, 237, 0.6);
        }}
        
        .speech-controls select {{
            padding: 6px 10px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: {settings['background']};
            color: {settings['text']};
            border-radius: 4px;
            font-size: 14px;
        }}
        
        .speech-controls input[type="range"] {{
            width: 100px;
        }}
        
        .speech-status {{
            font-size: 14px;
            font-weight: bold;
            color: {settings['title']};
            min-width: 80px;
            text-align: center;
        }}

        /* 滚动条样式 */
        ::-webkit-scrollbar {{
            width: 10px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: rgba(128, 128, 128, 0.1);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: rgba(128, 128, 128, 0.3);
            border-radius: 5px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: rgba(128, 128, 128, 0.5);
        }}
        
        /* 翻页功能样式 */
        .pagination-container {{
            position: relative;
            width: 100%;
            height: calc(100vh - 160px); /* 减去工具栏和其他元素的高度 */
            overflow: hidden;
            margin-top: 60px;
            background-color: {settings['background']};
            color: {settings['text']};
            font-family: {settings['font_family']};
            font-size: {settings['font_size']}px;
            line-height: {settings['line_height']};
            font-weight: {settings['font_weight']};
            font-style: {settings['font_style']};
            text-decoration: {settings['text_decoration']};
            letter-spacing: {settings['letter_spacing']}px;
            word-spacing: {settings['word_spacing']}px;
            text-align: {settings['text_align']};
        }}
        
        .page-content {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            padding: 40px;
            box-sizing: border-box;
            background-color: {settings['background']};
            color: {settings['text']};
            font-family: {settings['font_family']};
            font-size: {settings['font_size']}px;
            line-height: {settings['line_height']};
            font-weight: {settings['font_weight']};
            font-style: {settings['font_style']};
            text-decoration: {settings['text_decoration']};
            letter-spacing: {settings['letter_spacing']}px;
            word-spacing: {settings['word_spacing']}px;
            text-align: {settings['text_align']};
            overflow: hidden;
        }}
        
        .page {{
            width: 100%;
            height: 100%;
            box-sizing: border-box;
            overflow: hidden;
        }}
        
        .page h1 {{
            color: {settings['title']};
            font-size: 2em;
            margin: 1em 0 0.5em 0;
            font-weight: bold;
        }}
        
        .page h2 {{
            color: {settings['title']};
            font-size: 1.5em;
            margin: 0.8em 0 0.4em 0;
            font-weight: bold;
        }}
        
        .page h3 {{
            color: {settings['title']};
            font-size: 1.2em;
            margin: 0.6em 0 0.3em 0;
            font-weight: bold;
        }}
        
        .page p {{
            margin: 0.8em 0;
            text-align: justify;
            text-indent: 2em;
            overflow-y: auto;
            background: {settings['background']};
            color: {settings['text']};
            font-family: {settings['font_family']};
            font-size: {settings['font_size']}px;
            line-height: {settings['line_height']};
        }}
        
        /* 翻页效果 - 滑动 */
        .page-content.slide-effect {{
            animation: slideEffect 0.3s ease-in-out;
        }}
        
        @keyframes slideEffect {{
            0% {{
                transform: translateX(100%);
                opacity: 0;
            }}
            100% {{
                transform: translateX(0);
                opacity: 1;
            }}
        }}
        
        /* 翻页效果 - 淡入淡出 */
        .page-content.fade-effect {{
            animation: fadeEffect 0.3s ease-in-out;
        }}
        
        @keyframes fadeEffect {{
            0% {{
                opacity: 0;
            }}
            100% {{
                opacity: 1;
            }}
        }}
        
        /* 翻页效果 - 翻转 */
        .page-content.flip-effect {{
            animation: flipEffect 0.6s ease-in-out;
            transform-style: preserve-3d;
        }}
        
        @keyframes flipEffect {{
            0% {{
                transform: rotateY(180deg);
            }}
            100% {{
                transform: rotateY(0deg);
            }}
        }}
        
        /* 翻页效果 - 仿真翻页 */
        .page-content.realistic-flip {{
            position: relative;
            transform-style: preserve-3d;
            transition: transform 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}
        
        .page-content.realistic-flip-left {{
            transform-origin: right bottom;
            transform: rotateY(0deg);
            animation: realisticFlipLeft 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}
        
        .page-content.realistic-flip-right {{
            transform-origin: left bottom;
            transform: rotateY(0deg);
            animation: realisticFlipRight 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}
        
        /* 3D书籍翻页效果 - 融合test.html的优秀设计 */
        .page-content.book-flip {{
            position: relative;
            width: 100%;
            height: 100%;
            transform-style: preserve-3d;
            transform-origin: left center;
            transition: transform 1s ease;
            cursor: pointer;
            backface-visibility: hidden;
        }}
        
        .page-content.book-flip-next {{
            transform: rotateY(-180deg);
        }}
        
        .page-content.book-flip-prev {{
            transform: rotateY(0deg);
        }}
        
        /* 书页容器 */
        .book-container {{
            position: relative;
            width: 100%;
            height: 100%;
            perspective: 2000px;
        }}
        
        /* 页面样式 */
        .book-page {{
            position: absolute;
            width: 100%;
            height: 100%;
            background: inherit;
            color: inherit;
            padding: 40px;
            backface-visibility: hidden;
            box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.12);
            overflow-y: auto;
        }}
        
        .book-page.front {{
            background: linear-gradient(to right, 
                {settings['background']} 95%, 
                rgba(0,0,0,0.05) 100%);
        }}
        
        .book-page.back {{
            transform: rotateY(180deg);
            background: linear-gradient(to left, 
                {settings['background']} 95%, 
                rgba(0,0,0,0.05) 100%);
        }}
        
        /* 3D书页容器 */
        .book-3d-container {{
            position: relative;
            width: 100%;
            height: 100%;
            transform-style: preserve-3d;
            perspective: 1500px;
        }}
        
        /* 书页背面 */
        .page-back {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            transform: rotateY(180deg);
            backface-visibility: hidden;
            background: inherit;
            color: inherit;
        }}
        
        
        
        /* 自然的3D书页弯曲效果 */
        .page-curve {{
            position: absolute;
            top: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(ellipse at right center, 
                    rgba(0,0,0,0.3) 0%, 
                    rgba(0,0,0,0.15) 30%, 
                    rgba(0,0,0,0.08) 60%, 
                    transparent 100%),
                linear-gradient(90deg, 
                    transparent 0%, 
                    rgba(0,0,0,0.02) 30%, 
                    rgba(0,0,0,0.08) 50%, 
                    rgba(0,0,0,0.15) 70%,
                    rgba(0,0,0,0.08) 85%,
                    transparent 100%);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.6s cubic-bezier(0.4, 0.0, 0.2, 1);
            border-radius: 0 2px 2px 0;
            mix-blend-mode: multiply;
        }}
        
        .page-curve.active {{
            opacity: 1;
            animation: pageCurveNaturalAnimation 1.6s cubic-bezier(0.4, 0.0, 0.2, 1);
        }}
        
        @keyframes pageCurveNaturalAnimation {{
            0% {{ opacity: 0; transform: scaleX(1); }}
            10% {{ opacity: 0.3; transform: scaleX(1.01); }}
            30% {{ opacity: 0.8; transform: scaleX(1.02); }}
            50% {{ opacity: 1; transform: scaleX(1.03); }}
            70% {{ opacity: 0.8; transform: scaleX(1.02); }}
            90% {{ opacity: 0.3; transform: scaleX(1.01); }}
            100% {{ opacity: 0; transform: scaleX(1); }}
        }}
        
        /* 3D书页阴影效果 */
        .page-book-shadow {{
            position: absolute;
            top: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 10;
            transition: all 0.4s ease;
        }}
        
        .page-book-shadow-next {{
            background: 
                radial-gradient(ellipse at right bottom, 
                    rgba(0,0,0,0.6) 0%, 
                    rgba(0,0,0,0.4) 30%, 
                    rgba(0,0,0,0.2) 60%, 
                    rgba(0,0,0,0.1) 80%, 
                    transparent 100%),
                linear-gradient(to left, 
                    rgba(0,0,0,0.3) 0%, 
                    rgba(0,0,0,0.2) 20%, 
                    rgba(0,0,0,0.15) 40%, 
                    rgba(0,0,0,0.1) 60%, 
                    rgba(0,0,0,0.05) 80%, 
                    transparent 100%);
            opacity: 0;
            transition: opacity 0.4s ease;
            mix-blend-mode: multiply;
        }}
        
        .page-book-shadow-prev {{
            background: 
                radial-gradient(ellipse at left bottom, 
                    rgba(0,0,0,0.6) 0%, 
                    rgba(0,0,0,0.4) 30%, 
                    rgba(0,0,0,0.2) 60%, 
                    rgba(0,0,0,0.1) 80%, 
                    transparent 100%),
                linear-gradient(to right, 
                    rgba(0,0,0,0.3) 0%, 
                    rgba(0,0,0,0.2) 20%, 
                    rgba(0,0,0,0.15) 40%, 
                    rgba(0,0,0,0.1) 60%, 
                    rgba(0,0,0,0.05) 80%, 
                    transparent 100%);
            opacity: 0;
            transition: opacity 0.4s ease;
            mix-blend-mode: multiply;
        }}
        
        /* 自然的页面光泽效果 */
        .page-gloss {{
            position: absolute;
            top: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(ellipse at 30% 30%, 
                    rgba(255,255,255,0.3) 0%, 
                    rgba(255,255,255,0.15) 40%, 
                    rgba(255,255,255,0.05) 70%, 
                    transparent 100%),
                linear-gradient(135deg, 
                    transparent 0%, 
                    rgba(255,255,255,0.08) 20%, 
                    rgba(255,255,255,0.15) 40%, 
                    rgba(255,255,255,0.08) 60%, 
                    rgba(255,255,255,0.03) 80%,
                    transparent 100%);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.8s cubic-bezier(0.4, 0.0, 0.2, 1);
            mix-blend-mode: overlay;
            filter: blur(0.5px);
        }}
        
        .page-gloss.active {{
            opacity: 1;
            animation: pageGlossNaturalAnimation 1.6s cubic-bezier(0.4, 0.0, 0.2, 1);
        }}
        
        @keyframes pageGlossNaturalAnimation {{
            0% {{ opacity: 0; transform: translateY(0); }}
            15% {{ opacity: 0.2; transform: translateY(-2px); }}
            35% {{ opacity: 0.6; transform: translateY(-4px); }}
            50% {{ opacity: 0.8; transform: translateY(-5px); }}
            65% {{ opacity: 0.6; transform: translateY(-4px); }}
            85% {{ opacity: 0.2; transform: translateY(-2px); }}
            100% {{ opacity: 0; transform: translateY(0); }}
        }}
        
        .page-book-shadow-next.active {{
            opacity: 1;
        }}
        
        .page-book-shadow-prev.active {{
            opacity: 1;
        }}
        
        /* 书页厚度效果 */
        .page-thickness {{
            position: absolute;
            top: 0;
            width: 3px;
            height: 100%;
            background: linear-gradient(to right, 
                rgba(0,0,0,0.3) 0%, 
                rgba(0,0,0,0.1) 50%, 
                transparent 100%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .page-thickness-right {{
            right: 0;
        }}
        
        .page-thickness-left {{
            left: 0;
        }}
        
        .page-thickness.active {{
            opacity: 1;
        }}
        
        /* 仿真翻页阴影效果 */
        .page-shadow {{
            position: absolute;
            top: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 10;
        }}
        
        .page-shadow-left {{
            left: 0;
            background: linear-gradient(to right, 
                rgba(0,0,0,0.3) 0%, 
                rgba(0,0,0,0.15) 20%, 
                rgba(0,0,0,0.05) 40%, 
                rgba(0,0,0,0) 100%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .page-shadow-right {{
            right: 0;
            background: linear-gradient(to left, 
                rgba(0,0,0,0.3) 0%, 
                rgba(0,0,0,0.15) 20%, 
                rgba(0,0,0,0.05) 40%, 
                rgba(0,0,0,0) 100%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .page-shadow-left.active {{
            opacity: 1;
        }}
        
        .page-shadow-right.active {{
            opacity: 1;
        }}
        
        /* 翻页时的页面背面 */
        .page-back {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            backface-visibility: hidden;
            transform: rotateY(180deg);
            background: {settings['background']};
            border: 1px solid rgba(128, 128, 128, 0.2);
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }}
        
        /* 仿真翻页动画 */
        @keyframes realisticFlipLeft {{
            0% {{
                transform: rotateY(0deg);
            }}
            100% {{
                transform: rotateY(-180deg);
            }}
        }}
        
        @keyframes realisticFlipRight {{
            0% {{
                transform: rotateY(0deg);
            }}
            100% {{
                transform: rotateY(180deg);
            }}
        }}
        
        .page-content.realistic-flip-left-animation {{
            animation: realisticFlipLeft 0.6s cubic-bezier(0.645, 0.045, 0.355, 1);
        }}
        
        .page-content.realistic-flip-right-animation {{
            animation: realisticFlipRight 0.6s cubic-bezier(0.645, 0.045, 0.355, 1);
        }}
        
        /* 翻页控制按钮 */
        .pagination-controls {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 15px;
            background: transparent;
            padding: 10px 20px;
            border-radius: 25px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: background 0.3s ease;
        }}

        .pagination-controls:hover {{
            background: rgba(255, 255, 255, 0.95);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
        }}
        
        .pagination-controls button {{
            padding: 8px 16px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }}

        .pagination-controls button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}
        
        .pagination-controls button:hover {{
            background: rgba(128, 128, 128, 0.1);
        }}
        
        .pagination-controls button:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .pagination-controls button:disabled:hover {{
            background: {settings['background']};
        }}
        
        .page-info {{
            font-size: 14px;
            color: {settings['text']};
            min-width: 80px;
            text-align: center;
        }}
        
        .page-jump {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .page-jump input {{
            width: 50px;
            padding: 4px 8px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: {settings['background']};
            color: {settings['text']};
            border-radius: 4px;
            font-size: 14px;
            text-align: center;
        }}
        
        /* 翻页设置面板 */
        .pagination-settings {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 2000;
            transition: background 0.3s ease;
            display: none;
        }}

        .pagination-settings:hover {{
            background: rgba(255, 255, 255, 1);
        }}

        .pagination-settings.show {{
            display: block;
            width: 90%;
            max-width: 400px;
        }}
        
        .pagination-settings.show {{
            display: block;
        }}
        
        .pagination-settings-content {{
            padding: 20px;
        }}
        
        .pagination-settings h3 {{
            margin: 0 0 20px 0;
            color: {settings['title']};
            font-size: 18px;
            border-bottom: 2px solid rgba(128, 128, 128, 0.2);
            padding-bottom: 10px;
        }}
        
        .pagination-settings-close {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: {settings['text']};
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }}
        
        .pagination-settings-close:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            border-radius: 4px;
        }}
        
        .setting-item {{
            margin-bottom: 15px;
        }}
        
        .setting-item label {{
            display: block;
            margin-bottom: 5px;
            font-size: 14px;
            color: {settings['text']};
        }}
        
        .setting-item select {{
            width: 100%;
            padding: 8px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            font-size: 14px;
        }}

        .setting-item select:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}
        
        .setting-actions {{
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }}
        
        .setting-actions button {{
            flex: 1;
            padding: 8px 16px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: transparent;
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
        }}

        .setting-actions button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}
        
        /* 翻页模式切换按钮 */
        .pagination-mode-toggle {{
            position: fixed;
            top: 70px;
            left: 20px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 997;
            transition: all 0.2s;
        }}
        
        .pagination-mode-toggle:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
            transform: scale(1.05);
        }}
        
        .pagination-mode-toggle.active {{
            background: rgba(100, 149, 237, 0.3);
            border-color: rgba(100, 149, 237, 0.6);
        }}
        
        /* 隐藏滚动条（翻页模式） */
        .pagination-mode .page-content::-webkit-scrollbar {{
            display: none;
        }}
        
        .pagination-mode .page-content {{
            -ms-overflow-style: none;
            scrollbar-width: none;
        }}
        
        /* 书库面板样式 */
        .book-library-panel {{
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }}
        
        /* 书库面板悬停样式 - 只保留视觉效果 */
        .book-library-panel:hover {{
            background: rgba(255, 255, 255, 1);
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 2000;
        }}
        
        /* 文件导入面板悬停样式 - 只保留视觉效果 */
        #fileImportPanel:hover {{
            background: rgba(255, 255, 255, 1);
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 2000;
        }}
        
        /* 进度同步面板悬停样式 - 只保留视觉效果 */
        #progressSyncPanel:hover {{
            background: rgba(255, 255, 255, 1);
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 2000;
        }}
        
        .library-tabs {{
            display: flex;
            border-bottom: 1px solid rgba(128, 128, 128, 0.3);
            margin-bottom: 20px;
        }}
        
        .library-tabs .tab-btn {{
            flex: 1;
            padding: 10px;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            color: {settings['text']};
            cursor: pointer;
            font-size: 14px;
        }}
        
        .library-tabs .tab-btn:hover {{
            background: rgba(128, 128, 128, 0.05);
        }}
        
        .library-tabs .tab-btn.active {{
            border-bottom-color: rgba(100, 149, 237, 0.6);
            color: rgba(100, 149, 237, 1);
        }}
        
        .library-content {{
            min-height: 300px;
        }}
        
        .library-actions {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        }}
        
        .library-actions button {{
            padding: 6px 2px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            height: 30px;
            width: 90px;
            margin: 12px;
        }}
        
        .library-actions button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}
        
        .book-list {{
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .book-item {{
            display: flex;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.1);
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .book-item:hover {{
            background: rgba(128, 128, 128, 0.05);
        }}
        
        .book-item:last-child {{
            border-bottom: none;
        }}
        
        .book-cover {{
            width: 40px;
            height: 60px;
            background: rgba(100, 149, 237, 0.2);
            border: 1px solid rgba(100, 149, 237, 0.4);
            border-radius: 4px;
            margin-right: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            color: {settings['text']};
        }}
        
        .book-info {{
            flex: 1;
        }}
        
        .book-title {{
            font-weight: bold;
            margin-bottom: 4px;
            color: {settings['text']};
        }}
        
        .book-meta {{
            font-size: 12px;
            color: rgba(128, 128, 128, 0.8);
        }}
        
        .book-actions {{
            display: flex;
            gap: 8px;
        }}
        
        .book-actions button {{
            padding: 4px 8px;
            background: transparent;
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        
        .book-actions button:hover {{
            background: rgba(255, 255, 255, 0.9);
            color: #000;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: rgba(128, 128, 128, 0.6);
        }}
    </style>
</head>
<body>
    <!-- 老板键 - 百度首页 -->
    <div id="bossModeBaidu" style="display:none;">
        <style>
            #bossModeBaidu {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: #fff;
                z-index: 999999;
                font-family: Arial, sans-serif;
            }}
            #bossModeBaidu .baidu-header {{
                background: #fff;
                padding: 10px 20px;
                display: flex;
                align-items: center;
                border-bottom: 1px solid #e8e8e8;
            }}
            #bossModeBaidu .baidu-logo {{
                font-size: 24px;
                font-weight: bold;
                color: #3385ff;
                margin-right: 10px;
            }}
            #bossModeBaidu .baidu-logo span {{
                color: #ff4d4f;
            }}
            #bossModeBaidu .baidu-nav {{
                display: flex;
                gap: 20px;
                margin-left: auto;
                font-size: 14px;
                color: #333;
            }}
            #bossModeBaidu .baidu-nav a {{
                color: #333;
                text-decoration: none;
            }}
            #bossModeBaidu .baidu-nav a:hover {{
                color: #3385ff;
            }}
            #bossModeBaidu .baidu-main {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: calc(100% - 60px);
                padding-top: 80px;
            }}
            #bossModeBaidu .baidu-main-logo {{
                font-size: 48px;
                font-weight: bold;
                margin-bottom: 30px;
            }}
            #bossModeBaidu .baidu-main-logo span:first-child {{
                color: #3385ff;
            }}
            #bossModeBaidu .baidu-main-logo span:last-child {{
                color: #ff4d4f;
            }}
            #bossModeBaidu .baidu-search-box {{
                width: 600px;
                max-width: 90%;
                display: flex;
                gap: 10px;
            }}
            #bossModeBaidu .baidu-search-box input {{
                flex: 1;
                padding: 12px 16px;
                border: 2px solid #3385ff;
                border-radius: 4px 0 0 4px;
                font-size: 16px;
                outline: none;
            }}
            #bossModeBaidu .baidu-search-box input:focus {{
                border-color: #3385ff;
            }}
            #bossModeBaidu .baidu-search-box button {{
                padding: 12px 30px;
                background: #3385ff;
                color: #fff;
                border: none;
                border-radius: 0 4px 4px 0;
                font-size: 16px;
                cursor: pointer;
                font-weight: bold;
            }}
            #bossModeBaidu .baidu-search-box button:hover {{
                background: #2d7aff;
            }}
            #bossModeBaidu .baidu-footer {{
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                background: #fff;
                padding: 10px 20px;
                text-align: center;
                font-size: 12px;
                color: #999;
                border-top: 1px solid #e8e8e8;
            }}
        </style>
        <div class="baidu-header">
            <div class="baidu-logo"><span></span></div>
            <div class="baidu-nav">
                <a href="https://news.baidu.com" target="_blank">新闻</a>
                <a href="https://www.hao123.com" target="_blank">hao123</a>
                <a href="https://map.baidu.com" target="_blank">地图</a>
                <a href="https://tieba.baidu.com" target="_blank">贴吧</a>
                <a href="https://video.baidu.com" target="_blank">视频</a>
                <a href="https://image.baidu.com" target="_blank">图片</a>
                <a href="https://pan.baidu.com" target="_blank">网盘</a>
            </div>
        </div>
        <div class="baidu-main">
            <div class="baidu-main-logo">
                <img hidefocus="true" id="s_lg_img" class="index-logo-src" src="https://www.baidu.com/img/PCtm_d9c8750bed0b3c7d089fa7d55720d6cf.png" width="270" height="129" onerror="this.src='//www.baidu.com/img/flexible/logo/pc/index.png';this.onerror=null;" usemap="#mp">
            </div>
            <div class="baidu-search-box">
                <input type="text" id="baiduSearchInput" placeholder="请输入搜索内容" />
                <button onclick="performBaiduSearch()">百度一下</button>
            </div>
        </div>
        <div class="baidu-footer">
            © 2026 Baidu <a href="https://www.baidu.com/duty/" target="_blank" style="color:#999;">使用百度前必读</a> <a href="https://www.baidu.com/licence/" target="_blank" style="color:#999;">意见反馈</a> 京ICP证030173号
        </div>
    </div>

    <!-- 全屏状态指示器 -->
    <div class="fullscreen-indicator" id="fullscreenIndicator">
        <script>document.write(t('browser_reader.fullscreen_indicator'));</script>
    </div>
    
    <!-- 进度条 -->
    <div class="progress-bar">
        <div class="progress-fill" id="progressFill"></div>
    </div>
    
    <!-- 进度信息 -->
    <div class="progress-info" id="progressInfo" onclick="togglePositionJump()" title="{{t('browser_reader.progress_click_title')}}"><script>document.write(t('browser_reader.progress_info'));</script></div>

    <!-- 缩略图导航 -->
    <div class="minimap-container" id="minimapContainer">
        <div class="minimap-content" id="minimapContent">
            <div class="minimap-viewport" id="minimapViewport"></div>
        </div>
    </div>

    <!-- 缩略图切换按钮 -->
    <div class="minimap-toggle" id="minimapToggle" onclick="toggleMinimap()" title="{{t('browser_reader.minimap')}}">
        📍
    </div>

    <!-- 快捷键提示 -->
    <div class="keyboard-hint" id="keyboardHint">
        <h4><script>document.write(t('browser_reader.shortcuts_title'));</script></h4>
        <ul>
            <li><kbd>+</kbd>/<kbd>-</kbd> <script>document.write(t('browser_reader.shortcut_font_size'));</script></li>
            <li><kbd>↑</kbd>/<kbd>↓</kbd> <script>document.write(t('browser_reader.shortcut_page_up_down'));</script></li>
            <li><kbd>PageUp</kbd>/<kbd>PageDown</kbd> <script>document.write(t('browser_reader.shortcut_page_up_down_keys'));</script></li>
            <li><kbd>Home</kbd>/<kbd>End</kbd> <script>document.write(t('browser_reader.shortcut_home_end'));</script></li>
            <li><kbd>c</kbd> <script>document.write(t('browser_reader.shortcut_chapter'));</script></li>
            <li><kbd>s</kbd> <script>document.write(t('browser_reader.shortcut_search'));</script></li>
            <li><kbd>b</kbd> <script>document.write(t('browser_reader.shortcut_bookmark'));</script></li>
            <li><kbd>f</kbd> <script>document.write(t('browser_reader.shortcut_fullscreen'));</script></li>
            <li><kbd>F</kbd> <script>document.write(t('browser_reader.shortcut_focus'));</script></li>
            <li><kbd>a</kbd> <script>document.write(t('browser_reader.shortcut_auto_scroll'));</script></li>
            <li><kbd>Space</kbd> <script>document.write(t('browser_reader.shortcut_speech'));</script></li>
            <li><kbd>h</kbd> <script>document.write(t('browser_reader.shortcut_hide'));</script></li>
            <li><kbd>Ctrl+G</kbd> <script>document.write(t('browser_reader.shortcut_position_jump'));</script></li>
            <li><kbd>g</kbd> <script>document.write(t('browser_reader.shortcut_font_settings'));</script></li>
            <li><kbd>n</kbd> <script>document.write(t('browser_reader.shortcut_notes'));</script></li>
            <li><kbd>m</kbd> <script>document.write(t('browser_reader.shortcut_minimap'));</script></li>
            <li><kbd>/</kbd> 老板键</li>
            <li><kbd>ESC</kbd> <script>document.write(t('browser_reader.shortcut_escape'));</script></li>
        </ul>
    </div>

    <!-- 阅读统计 -->
    <div class="reading-stats" id="readingStats" onclick="toggleReadingStats()">
        <p><script>document.write(t('browser_reader.reading_time'));</script> <span id="readingTime">0:00</span></p>
        <p><script>document.write(t('browser_reader.word_count'));</script> <span id="wordCount">0</span></p>
        <p><script>document.write(t('browser_reader.reading_speed'));</script> <span id="readingSpeed">0</span> 字/分</p>
    </div>
    
    <!-- 增强的阅读统计面板 -->
    <div class="reading-stats-enhanced" id="readingStatsEnhanced" onclick="toggleReadingStats()">
        <h4><script>document.write(t('browser_reader.stats_title'));</script></h4>
        <p><script>document.write(t('browser_reader.stats_total_time'));</script> <span class="stat-value" id="totalReadingTime">0:00</span></p>
        <p><script>document.write(t('browser_reader.stats_session_time'));</script> <span class="stat-value" id="sessionReadingTime">0:00</span></p>
        <p><script>document.write(t('browser_reader.stats_total_words'));</script> <span class="stat-value" id="totalWordCount">0</span></p>
        <p><script>document.write(t('browser_reader.stats_progress'));</script> <span class="stat-value" id="readingProgress">0%</span></p>
        <p><script>document.write(t('browser_reader.stats_avg_speed'));</script> <span class="stat-value" id="avgReadingSpeed">0</span> 字/分</p>
        <p><script>document.write(t('browser_reader.stats_estimated_time'));</script> <span class="stat-value" id="estimatedTimeLeft">--</span></p>
    </div>
    
    <!-- 夜间模式切换 -->
    <div class="night-mode-toggle" id="nightModeToggle" onclick="toggleNightMode()">
        <span id="nightModeIcon">🌙</span>
        <span id="nightModeText"><script>document.write(t('browser_reader.night_mode'));</script></span>
    </div>
    
    <!-- 翻页模式切换 -->
    <div class="pagination-mode-toggle" id="paginationModeToggle" onclick="togglePaginationMode()">
        <span id="paginationModeIcon">📖</span>
        <span id="paginationModeText"><script>document.write(t('browser_reader.pagination_mode'));</script></span>
    </div>
    
    <!-- 位置跳转弹窗 -->
    <div class="settings-panel" id="positionJumpModal" style="display: none;">
        <div class="settings-content">
            <h3 id="positionJumpTitle"><script>document.write(t('browser_reader.position_jump.title'));</script></h3>
            <button class="settings-close" onclick="closePositionJumpModal()">×</button>
            
            <div class="setting-item">
                <label id="positionJumpInputLabel"><script>document.write(t('browser_reader.position_jump.input_label'));</script></label>
                <input type="number" id="positionJumpInputModal" class="position-input" min="0" max="100" step="0.01" placeholder="{{t('browser_reader.position_jump.input_placeholder')}}">
                <button onclick="jumpToPositionFromModal()" id="positionJumpButton" class="jump-btn" title="{{t('browser_reader.position_jump.jump_button_title')}}"><script>document.write(t('browser_reader.position_jump.jump_button'));</script></button>
            </div>
            
            <div class="setting-item">
                <label id="positionJumpQuickLabel"><script>document.write(t('browser_reader.position_jump.quick_jump_label'));</script></label>
                <div class="quick-jump-buttons">
                    <button onclick="quickJumpToFromModal(25)" id="positionJump25" class="quick-jump-btn" title="{{t('browser_reader.position_jump.jump_25')}}"><script>document.write(t('browser_reader.position_jump.jump_25'));</script></button>
                    <button onclick="quickJumpToFromModal(50)" id="positionJump50" class="quick-jump-btn" title="{{t('browser_reader.position_jump.jump_50')}}"><script>document.write(t('browser_reader.position_jump.jump_50'));</script></button>
                    <button onclick="quickJumpToFromModal(75)" id="positionJump75" class="quick-jump-btn" title="{{t('browser_reader.position_jump.jump_75')}}"><script>document.write(t('browser_reader.position_jump.jump_75'));</script></button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 工具栏 -->
    <div class="toolbar" id="toolbar">
        <button onclick="changeFontSize(-2)">A-</button>
        <button onclick="changeFontSize(2)">A+</button>

        <label>
            <script>document.write(t('browser_reader.theme_label'));</script>
            <select id="themeSelect" onchange="changeTheme(this.value)">
                <option value="light"><script>document.write(t('browser_reader.theme_light'));</script></option>
                <option value="dark"><script>document.write(t('browser_reader.theme_dark'));</script></option>
                <option value="sepia"><script>document.write(t('browser_reader.theme_sepia'));</script></option>
                <option value="matrix"><script>document.write(t('browser_reader.theme_matrix'));</script></option>
                <option value="ocean"><script>document.write(t('browser_reader.theme_ocean'));</script></option>
                <option value="forest"><script>document.write(t('browser_reader.theme_forest'));</script></option>
                <option value="warm"><script>document.write(t('browser_reader.theme_warm'));</script></option>
                <option value="purple"><script>document.write(t('browser_reader.theme_purple'));</script></option>
                <option value="custom"><script>document.write(t('browser_reader.theme_custom'));</script></option>
            </select>
            <button onclick="showThemeManager()" style="margin-left: 5px; padding: 4px 8px; font-size: 12px;"><script>document.write(t('browser_reader.theme_manager'));</script></button>
        </label>

        <label>
            <script>document.write(t('browser_reader.line_height_label'));</script>
            <input type="range" min="1.2" max="2.5" step="0.1" value="{settings['line_height']}" onchange="changeLineHeight(this.value)">
        </label>

        <button onclick="if(checkPermission('settings.write')) toggleFontSettings()"><script>document.write(t('browser_reader.font_button'));</script></button>
        <button onclick="if(checkPermission('bookmark.write')) toggleHighlightMode()"><script>document.write(t('browser_reader.highlight_button'));</script></button>
        <button onclick="if(checkPermission('bookmark.write')) toggleNotesMode()"><script>document.write(t('browser_reader.notes_button'));</script></button>
        <button onclick="if(checkPermission('search.read')) toggleSearch()"><script>document.write(t('browser_reader.search_button'));</script></button>
        <button onclick="toggleAutoScrollPanel()"><script>document.write(t('browser_reader.auto_scroll_button'));</script></button>
        <button onclick="toggleSpeech()"><script>document.write(t('browser_reader.speech_settings'));</script></button>
        <button onclick="if(checkPermission('stats.read')) toggleReadingStats()"><script>document.write(t('browser_reader.stats_button'));</script></button>
        <button onclick="if(checkPermission('settings.write')) togglePaginationSettings()"><script>document.write(t('browser_reader.pagination_settings'));</script></button>
        <button onclick="toggleFocusMode()"><script>document.write(t('browser_reader.focus_mode'));</script></button>
        <button onclick="toggleFullscreen()"><script>document.write(t('browser_reader.fullscreen'));</script></button>
        <button onclick="scrollToTop()"><script>document.write(t('browser_reader.scroll_to_top'));</script></button>
        <button onclick="scrollToBottom()"><script>document.write(t('browser_reader.bottom'));</script></button>
        
        <button onclick="togglePositionJump()" id="positionJumpBtn" title="{{t('browser_reader.position_jump.title')}}"><script>document.write(t('browser_reader.position_jump.title'));</script></button>
        <button onclick="if(checkPermission('book.write')) printContent()"><script>document.write(t('browser_reader.print_button'));</script></button>
        <button onclick="toggleMinimap()" id="minimapToolbarBtn"><script>document.write(t('browser_reader.minimap'));</script></button>
        <button onclick="toggleTOC()"><script>document.write(t('browser_reader.toc'));</script></button>
        <button onclick="if(checkPermission('book.write')) toggleProgressSync()" id="progressSyncBtn"><script>document.write(t('browser_reader.progress_sync'));</script></button>
        <button onclick="if(checkPermission('book.add')) toggleFileImport()" id="fileImportBtn"><script>document.write(t('browser_reader.import_file'));</script></button>
        <button onclick="toggleBookLibrary()" id="bookLibraryBtn"><script>document.write(t('browser_reader.book_library'));</script></button>
    </div>

    <!-- 工具栏收缩/展开按钮 -->
    <div class="toolbar-toggle-container" id="toolbarToggleContainer">
        <button class="toolbar-toggle-btn" onclick="toggleToolbar()" title="{{t('browser_reader.toolbar_toggle_title')}}">
            <span id="toolbarToggleIcon">︽</span>
        </button>
    </div>

    <!-- 字体设置面板 -->
    <div class="settings-panel" id="fontSettingsPanel" style="display: none;">
        <div class="settings-content">
            <h3><script>document.write(t('browser_reader.font_settings_title'));</script></h3>
            <button class="settings-close" onclick="toggleFontSettings()">×</button>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.font_label'));</script></label>
                <select id="fontFamilySelect" onchange="changeFontFamily(this.value)">
                    <option value="system"><script>document.write(t('browser_reader.font_system'));</script></option>
                    <option value="serif"><script>document.write(t('browser_reader.font_serif'));</script></option>
                    <option value="sans-serif"><script>document.write(t('browser_reader.font_sans_serif'));</script></option>
                    <option value="georgia">Georgia</option>
                    <option value="kai"><script>document.write(t('browser_reader.font_kai'));</script></option>
                    <option value="fangsong"><script>document.write(t('browser_reader.font_fangsong'));</script></option>
                    <option value="monospace"><script>document.write(t('browser_reader.font_monospace'));</script></option>
                </select>
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.bold_label'));</script></label>
                <button class="toggle-btn" id="boldBtn" onclick="toggleBold()">B</button>
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.italic_label'));</script></label>
                <button class="toggle-btn" id="italicBtn" onclick="toggleItalic()">I</button>
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.underline_label'));</script></label>
                <button class="toggle-btn" id="underlineBtn" onclick="toggleUnderline()">U</button>
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.font_color_label'));</script></label>
                <input type="color" id="fontColorInput" value="{settings['text']}" onchange="changeFontColor(this.value)">
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.bg_color_label'));</script></label>
                <input type="color" id="bgColorInput" value="{settings['background']}" onchange="changeBackgroundColor(this.value)">
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.letter_spacing_label'));</script></label>
                <input type="range" min="-2" max="5" step="0.5" value="{settings['letter_spacing']}" onchange="changeLetterSpacing(this.value)">
                <span id="letterSpacingValue">{settings['letter_spacing']}</span> <script>document.write(t('browser_reader.pixel_unit'));</script>
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.word_spacing_label'));</script></label>
                <input type="range" min="-2" max="10" step="1" value="{settings['word_spacing']}" onchange="changeWordSpacing(this.value)">
                <span id="wordSpacingValue">{settings['word_spacing']}</span> <script>document.write(t('browser_reader.pixel_unit'));</script>
            </div>

            <div class="setting-item">
                <label><script>document.write(t('browser_reader.alignment_label'));</script></label>
                <select id="textAlignSelect" onchange="changeTextAlign(this.value)">
                    <option value="left"><script>document.write(t('browser_reader.align_left'));</script></option>
                    <option value="center"><script>document.write(t('browser_reader.align_center'));</script></option>
                    <option value="right"><script>document.write(t('browser_reader.align_right'));</script></option>
                    <option value="justify"><script>document.write(t('browser_reader.align_justify'));</script></option>
                </select>
            </div>

            <div class="setting-actions">
                <button onclick="resetFontSettings()"><script>document.write(t('browser_reader.reset_button'));</script></button>
                <button onclick="toggleFontSettings()"><script>document.write(t('browser_reader.close_button'));</script></button>
            </div>
        </div>
    </div>

    <!-- 高亮和笔记面板 -->
    <div class="settings-panel" id="notesPanel" style="display: none;">
        <div class="settings-content">
            <h3 id="notesTitle"><script>document.write(t('browser_reader.notes_title'));</script></h3>
            <button class="settings-close" onclick="closeNotesPanel()">×</button>

            <div class="notes-tabs">
                <button class="tab-btn active" onclick="switchNotesTab('highlights')"><script>document.write(t('browser_reader.highlights_tab'));</script></button>
                <button class="tab-btn" onclick="switchNotesTab('bookmarks')"><script>document.write(t('browser_reader.bookmarks_tab'));</script></button>
                <button class="tab-btn" onclick="switchNotesTab('notes')"><script>document.write(t('browser_reader.notes_tab'));</script></button>
            </div>

            <div class="notes-content" id="highlightsTab">
                <div class="notes-list" id="highlightsList"></div>
                <div class="notes-hint"><script>document.write(t('browser_reader.highlights_hint'));</script></div>
            </div>

            <div class="notes-content" id="bookmarksTab" style="display: none;">
                <div class="notes-list" id="bookmarksList"></div>
                <button onclick="addBookmark()" class="add-btn"><script>document.write(t('browser_reader.add_bookmark'));</script></button>
            </div>

            <div class="notes-content" id="notesTab" style="display: none;">
                <textarea id="noteInput" placeholder="{{t('browser_reader.note_placeholder')}}" rows="3"></textarea>
                <button onclick="addNote()" class="add-btn"><script>document.write(t('browser_reader.add_note'));</script></button>
                <div class="notes-list" id="notesList"></div>
            </div>
        </div>
    </div>

    <!-- 搜索框 -->
    <div class="search-container" id="searchContainer">
        <input type="text" id="searchInput" placeholder="{{t('browser_reader.search_placeholder')}}" onkeypress="handleSearchKeypress(event)">
        <button onclick="searchText()"><script>document.write(t('browser_reader.search_button_text'));</script></button>
        <button onclick="searchNext()"><script>document.write(t('browser_reader.search_next'));</script></button>
        <span class="search-count" id="searchCount"></span>
    </div>

    <!-- 目录切换按钮 -->
    <button class="toc-toggle-btn" onclick="toggleTOC()" title="{{t('browser_reader.toc_toggle_title')}}">☰</button>

    <!-- 书签按钮 -->
    <button class="bookmark-btn" id="bookmarkBtn" onclick="toggleBookmark()" title="{{t('browser_reader.bookmark_title')}}">🔖</button>

    <!-- 章节目录 -->
    <div class="toc-container" id="tocContainer">
        <div class="toc-header">
            <h3><script>document.write(t('browser_reader.toc_title'));</script></h3>
            <button class="toc-close" onclick="toggleTOC()">×</button>
        </div>
        <ul class="toc-list" id="tocList"></ul>
    </div>
    
    <!-- 自动滚动控制面板 -->
    <div class="auto-scroll-controls" id="autoScrollControls">
        <button onclick="decreaseScrollSpeed()">−</button>
        <span class="scroll-speed-display" id="scrollSpeedDisplay">1</span>
        <button onclick="increaseScrollSpeed()">+</button>
        <input type="range" id="scrollSpeedSlider" min="0.5" max="10" step="0.5" value="1" onchange="setScrollSpeed(this.value)">
        <button onclick="toggleAutoScroll()" id="autoScrollToggleBtn"><script>document.write(t('browser_reader.auto_scroll_start'));</script></button>
        <button onclick="resetAutoScroll()"><script>document.write(t('browser_reader.reset_button'));</script></button>
    </div>
    
    <!-- 朗读控制面板 -->
    <div class="speech-controls" id="speechControls">
        <button onclick="toggleSpeechPlayback()" id="speechPlaybackBtn"><script>document.write(t('browser_reader.speech_start'));</script></button>
        <select id="voiceSelect" onchange="changeVoice(this.value)">
            <option value=""><script>document.write(t('browser_reader.speech_select_voice'));</script></option>
        </select>
        <label><script>document.write(t('browser_reader.speech_speed'));</script> <input type="range" id="speechRate" min="0.5" max="2" step="0.1" value="1" onchange="changeSpeechRate(this.value)"></label>
        <label><script>document.write(t('browser_reader.speech_pitch'));</script> <input type="range" id="speechPitch" min="0.5" max="2" step="0.1" value="1" onchange="changeSpeechPitch(this.value)"></label>
        <button onclick="stopSpeech()"><script>document.write(t('browser_reader.speech_stop'));</script></button>
        <span class="speech-status" id="speechStatus"><script>document.write(t('browser_reader.speech_not_started'));</script></span>
    </div>
    
    <!-- 翻页容器 -->
    <div class="pagination-container" id="paginationContainer" style="display: none;">
        <div class="page-content" id="pageContent"></div>
    </div>
    
    <!-- 翻页控制按钮 -->
    <div class="pagination-controls" id="paginationControls" style="display: none;">
        <button onclick="previousPage()" id="prevPageBtn"><script>document.write(t('browser_reader.prev_page'));</script></button>
        <div class="page-info">
            <span id="currentPage">1</span> / <span id="totalPages">1</span>
        </div>
        <div class="page-jump">
            <input type="number" id="pageJumpInput" min="1" value="1" onchange="jumpToPage()">
            <button onclick="jumpToPage()"><script>document.write(t('browser_reader.page_jump'));</script></button>
        </div>
        <button onclick="nextPage()" id="nextPageBtn"><script>document.write(t('browser_reader.next_page'));</script></button>
    </div>
    
    <!-- 翻页设置面板 -->
    <div class="pagination-settings" id="paginationSettings">
        <div class="pagination-settings-content">
            <h3><script>document.write(t('browser_reader.pagination_settings'));</script></h3>
            <button class="pagination-settings-close" onclick="togglePaginationSettings()">×</button>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.page_effect'));</script></label>
                <select id="pageEffectSelect" onchange="changePageEffect(this.value)">
                    <option value="none"><script>document.write(t('browser_reader.effect_none'));</script></option>
                    <option value="slide"><script>document.write(t('browser_reader.effect_slide'));</script></option>
                    <option value="fade"><script>document.write(t('browser_reader.effect_fade'));</script></option>
                    <option value="flip"><script>document.write(t('browser_reader.effect_flip'));</script></option>
                    <option value="realistic"><script>document.write(t('browser_reader.effect_realistic'));</script></option>
                    <option value="book"><script>document.write(t('browser_reader.effect_book'));</script></option>
                </select>
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.auto_page_turn'));</script></label>
                <select id="autoPageTurnSelect" onchange="changeAutoPageTurn(this.value)">
                    <option value="off"><script>document.write(t('browser_reader.pagination_off'));</script></option>
                    <option value="10"><script>document.write(t('browser_reader.pagination_10s'));</script></option>
                    <option value="15"><script>document.write(t('browser_reader.pagination_15s'));</script></option>
                    <option value="30"><script>document.write(t('browser_reader.pagination_30s'));</script></option>
                    <option value="60"><script>document.write(t('browser_reader.pagination_60s'));</script></option>
                </select>
            </div>
            
            <div class="setting-actions">
                <button onclick="resetPaginationSettings()"><script>document.write(t('browser_reader.reset_button'));</script></button>
                <button onclick="togglePaginationSettings()"><script>document.write(t('browser_reader.close_button'));</script></button>
            </div>
        </div>
    </div>
    
    <!-- 进度同步设置面板 -->
    <div class="settings-panel" id="progressSyncPanel" style="display: none;">
        <div class="settings-content">
            <h3><script>document.write(t('browser_reader.progress_sync_settings'));</script></h3>
            <button class="settings-close" onclick="toggleProgressSync()">×</button>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.enable_progress_sync'));</script></label>
                <button class="toggle-btn" id="progressSyncToggle" onclick="toggleProgressSyncEnabled()"><script>document.write(t('browser_reader.enable'));</script></button>
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.sync_status'));</script></label>
                <span id="syncStatusText"><script>document.write(t('browser_reader.not_connected'));</script></span>
            </div>
            
            <div class="setting-item">
                <label>服务器地址</label>
                <span id="serverAddressText" style="font-family: monospace; font-size: 12px; color: #666;">检测中...</span>
            </div>
            
            <div class="setting-item">
                <label>连接模式</label>
                <span id="connectionModeText" style="color: #666;">检测中...</span>
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.last_sync_time'));</script></label>
                <span id="lastSyncTime"><script>document.write(t('browser_reader.never_synced'));</script></span>
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.auto_sync_interval'));</script></label>
                <select id="syncIntervalSelect" onchange="changeSyncInterval(this.value)">
                    <option value="300000"><script>document.write(t('browser_reader.sync_5min'));</script></option>
                    <option value="600000"><script>document.write(t('browser_reader.sync_10min'));</script></option>
                    <option value="1800000"><script>document.write(t('browser_reader.sync_30min'));</script></option>
                    <option value="3600000"><script>document.write(t('browser_reader.sync_1hour'));</script></option>
                    <option value="7200000"><script>document.write(t('browser_reader.sync_2hours'));</script></option>
                </select>
            </div>
            
            <div class="setting-actions">
                <button onclick="manualSync()"><script>document.write(t('browser_reader.sync_now'));</script></button>
                <button onclick="toggleProgressSync()"><script>document.write(t('browser_reader.close_button'));</script></button>
            </div>
        </div>
    </div>
    
    <!-- 文件导入面板 -->
    <div class="settings-panel" id="fileImportPanel" style="display: none;">
        <div class="settings-content">
            <h3><script>document.write(t('browser_reader.import_file'));</script></h3>
            <button class="settings-close" onclick="toggleFileImport()">×</button>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.drag_drop_file'));</script></label>
                <div id="dropZone" class="drop-zone">
                    <div class="drop-zone-content">
                        <div class="drop-icon">📁</div>
                        <p><script>document.write(t('browser_reader.drop_file_here'));</script></p>
                        <p class="drop-hint"><script>document.write(t('browser_reader.or_click_select'));</script></p>
                        <input type="file" id="fileInput" accept=".txt,.html,.htm,.md,.pdf,.epub,.mobi,.azw,.azw3" onchange="handleFileSelect(event)">
                    </div>
                </div>
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.file_preview'));</script></label>
                <div id="filePreview" style="max-height: 200px; overflow-y: auto; border: 1px solid rgba(128, 128, 128, 0.3); padding: 10px; background: rgba(128, 128, 128, 0.05);">
                    <p style="color: #666;"><script>document.write(t('browser_reader.select_file_preview'));</script></p>
                </div>
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.file_title'));</script></label>
                <input type="text" id="fileTitle" placeholder="{{t('browser_reader.auto_extract_title')}}">
            </div>
            
            <div class="setting-actions">
                <button onclick="importFile()"><script>document.write(t('browser_reader.import_and_open'));</script></button>
                <button onclick="toggleFileImport()"><script>document.write(t('browser_reader.cancel'));</script></button>
            </div>
        </div>
    </div>
    
    <!-- 书库面板 -->
    <div class="settings-panel book-library-panel" id="bookLibraryPanel" style="display: none;">
        <div class="settings-content">
            <h3><script>document.write(t('browser_reader.my_library'));</script></h3>
            <button class="settings-close" onclick="toggleBookLibrary()">×</button>
            
            <div class="library-tabs">
                <button class="tab-btn active" onclick="switchLibraryTab('history')"><script>document.write(t('browser_reader.reading_history'));</script></button>
                <button class="tab-btn" onclick="switchLibraryTab('imported')"><script>document.write(t('browser_reader.imported_books'));</script></button>
            </div>
            
            <!-- 阅读历史 -->
            <div class="library-content" id="historyTab">
                <div class="library-actions">
                    <div class="library-search">
                        <input type="text" id="librarySearchInput" placeholder="搜索书籍标题..." onkeyup="searchLibraryBooks()">
                        <button onclick="clearLibrarySearch()" id="clearSearchBtn" style="display: none;">×</button>
                    </div>
                    <button onclick="clearHistory()"><script>document.write(t('browser_reader.clear_history'));</script></button>
                    <button onclick="refreshHistory()"><script>document.write(t('browser_reader.refresh'));</script></button>
                </div>
                <div class="book-list" id="historyBookList">
                    <p style="color: #666; text-align: center; padding: 20px;"><script>document.write(t('browser_reader.no_reading_history'));</script></p>
                </div>
            </div>
            
            <!-- 导入书籍 -->
            <div class="library-content" id="importedTab" style="display: none;">
                <div class="library-actions">
                    <div class="library-search">
                        <input type="text" id="importedSearchInput" placeholder="搜索书籍标题..." onkeyup="searchImportedBooks()">
                        <button onclick="clearImportedSearch()" id="clearImportedSearchBtn" style="display: none;">×</button>
                    </div>
                    <button onclick="addBookFromLibrary()"><script>document.write(t('browser_reader.add_book'));</script></button>
                    <button onclick="showAddDirectoryModal()"><script>document.write(t('browser_reader.add_directory'));</script></button>
                    <button onclick="exportLibrary()"><script>document.write(t('browser_reader.export_library'));</script></button>
                    <button onclick="showStorageInfo()" title="存储使用情况">📊</button>
                    <button onclick="clearAllImportedBooks()" style="background-color: #ff6b6b;" title="清空所有导入书籍"><script>document.write(t('browser_reader.clear_all_books'));</script></button>
                </div>
                <div class="book-list" id="importedBookList">
                    <p style="color: #666; text-align: center; padding: 20px;"><script>document.write(t('browser_reader.no_imported_books'));</script></p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 添加目录弹窗 -->
    <div class="settings-panel" id="addDirectoryModal" style="display: none;">
        <div class="settings-content">
            <h3><script>document.write(t('browser_reader.add_directory_title'));</script></h3>
            <button class="settings-close" onclick="closeAddDirectoryModal()">×</button>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.select_directory_label'));</script></label>
                <div id="directoryDropZone" class="drop-zone">
                    <div class="drop-zone-content">
                        <div class="drop-icon">📁</div>
                        <p><script>document.write(t('browser_reader.select_directory_hint'));</script></p>
                        <p class="drop-hint"><script>document.write(t('browser_reader.or_click_select_directory'));</script></p>
                        <input type="file" id="directoryInput" webkitdirectory directory multiple style="display: none;" onchange="handleDirectorySelect(event)">
                    </div>
                </div>
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.selected_directory'));</script></label>
                <input type="text" id="directoryPath" placeholder="{{t('browser_reader.no_directory_selected')}}" readonly style="background: rgba(128, 128, 128, 0.1);">
            </div>
            
            <div class="setting-item">
                <label><script>document.write(t('browser_reader.recursive_scan'));</script></label>
                <input type="checkbox" id="recursiveScan" checked>
            </div>
            
            <div class="setting-actions">
                <button onclick="confirmAddDirectory()"><script>document.write(t('browser_reader.confirm_add_directory'));</script></button>
                <button onclick="closeAddDirectoryModal()"><script>document.write(t('browser_reader.cancel'));</script></button>
            </div>
        </div>
    </div>
    
    <!-- 内容区域 -->
    <div class="content" id="content">
        {content}
    </div>
    
    <script>
        // 语言包支持 - 直接嵌入翻译数据
        const translations = {str(BrowserReader.get_translations())};
        
        
        // 替换所有翻译占位符
        function replaceAllPlaceholders() {{
            // 替换所有包含翻译占位符的文本节点
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            const textNodes = [];
            let node;
            while (node = walker.nextNode()) {{
                if (node.textContent.includes('{{t(') && node.textContent.includes(')}}')) {{
                    textNodes.push(node);
                }}
            }}
            
            textNodes.forEach(textNode => {{
                const text = textNode.textContent;
                const newText = text.replace(/{{t\('([^']+)'\)}}/g, function(match, key) {{
                    const value = key.split('.').reduce((obj, k) => obj && obj[k], translations);
                    return value || match;
                        }});
                textNode.textContent = newText;
            }});

            // 替换所有元素的placeholder属性中的翻译占位符
            const allElements = document.querySelectorAll('*');
            allElements.forEach(element => {{
                const placeholder = element.getAttribute('placeholder');
                if (placeholder && placeholder.includes('{{t(')) {{
                    const newPlaceholder = placeholder.replace(/{{t\('([^']+)'\)}}/g, function(match, key) {{
                        const value = key.split('.').reduce((obj, k) => obj && obj[k], translations);
                        return value || match;
                    }});
                    element.setAttribute('placeholder', newPlaceholder);
                }}
                
                const title = element.getAttribute('title');
                if (title && title.includes('{{t(')) {{
                    const newTitle = title.replace(/{{t\('([^']+)'\)}}/g, function(match, key) {{
                        const value = key.split('.').reduce((obj, k) => obj && obj[k], translations);
                        return value || match;
                    }});
                    element.setAttribute('title', newTitle);
                }}
            }});
        }}
        
        // 翻译函数
        function t(key, params = {{}}) {{
            let value = key.split('.').reduce((obj, k) => obj && obj[k], translations);
            if (!value) return key;
            
            // 替换参数
            for (const [param, val] of Object.entries(params)) {{
                value = value.replace(new RegExp(`{{${{param}}}}`, 'g'), val);
            }}
            return value;
        }}
        
        // 页面加载完成后替换翻译占位符
        document.addEventListener('DOMContentLoaded', function() {{
            replaceAllPlaceholders();
            
            // 确保进度同步UI正确初始化
            updateProgressSyncUI();
        }});
        
        {BrowserReader.get_permission_script()}
        
        // 当前设置
        let currentSettings = {str(settings)};
        
        
        
        // 全局主题变量
        const themes = {str(BrowserReader.THEMES)};
        
        // 翻页功能变量
        let isPaginationMode = false;
        let currentPageIndex = 0;
        let pages = [];
        let pageEffect = 'none';
        let autoPageTurnTimer = null;
        let autoPageTurnInterval = 0;

        // 自动保存进度定时器
        let saveProgressTimer = null;
        let saveProgressInterval = 7200000; // 2 小时保存一次

        // 标记:页面加载后短时间内禁用自动保存,避免恢复进度时触发错误保存
        let isPageLoading = true;
        let pageLoadStartTime = Date.now();
        const pageLoadCooldown = 3000; // 页面加载冷却时间3秒

        // 缓存上一次保存的进度值
        let cachedProgress = null;
        let cachedScrollTop = 0;
        let cachedScrollHeight = 0;
        
        // 进度API地址 - 使用let而不是const，以便可以动态更新
        let SAVE_PROGRESS_URL = {f'"{save_progress_url}"' if save_progress_url else 'null'};
        let LOAD_PROGRESS_URL = {f'"{load_progress_url}"' if load_progress_url else 'null'};
        
        // 暴露到window对象，以便可以动态更新
        window.SAVE_PROGRESS_URL = SAVE_PROGRESS_URL;
        window.LOAD_PROGRESS_URL = LOAD_PROGRESS_URL;
        
        // 调试：输出URL设置情况
        console.log('=== 浏览器阅读器初始化 ===');
        console.log('SAVE_PROGRESS_URL:', SAVE_PROGRESS_URL);
        console.log('LOAD_PROGRESS_URL:', LOAD_PROGRESS_URL);
        console.log('Python传入的save_progress_url:', {f'"{save_progress_url}"' if save_progress_url else 'null'});
        console.log('Python传入的load_progress_url:', {f'"{load_progress_url}"' if load_progress_url else 'null'});

        // 后端在线状态
        let isBackendOnline = SAVE_PROGRESS_URL ? true : false;
        
        // 进度同步设置
        let progressSyncEnabled = localStorage.getItem('progressSyncEnabled') === 'true';
        let syncInterval = parseInt(localStorage.getItem('syncInterval') || '7200000'); // 默认2小时
        let lastSyncTime = localStorage.getItem('lastSyncTime') || null;
        
        // 书籍ID（用于区分不同书籍的进度）
        let BOOK_ID = '{book_id or title}';
        
        // 初始进度（从Python端传递）
        const INITIAL_PROGRESS = {initial_progress if initial_progress is not None else 'null'};
        
        // 获取书籍特定的本地进度键名
        function getLocalProgressKey(bookId = BOOK_ID) {{
            return 'localReadingProgress_' + bookId;
        }}
        
        // 获取书籍特定的本地进度数据
        function getLocalProgressData(bookId = BOOK_ID) {{
            const key = getLocalProgressKey(bookId);
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        }}
        
        // 保存书籍特定的本地进度数据
        function setLocalProgressData(data, bookId = BOOK_ID) {{
            const key = getLocalProgressKey(bookId);
            localStorage.setItem(key, JSON.stringify(data));
            console.log('进度已保存到本地存储 [' + bookId + ']');
        }}
        
        // 更新当前书籍ID并重新加载进度
        function updateCurrentBook(newBookId) {{
            if (newBookId !== BOOK_ID) {{
                console.log('切换书籍：从 [' + BOOK_ID + '] 到 [' + newBookId + ']');
                
                // 保存当前书籍的进度（如果有的话）
                const currentScrollTop = window.scrollY;
                const currentScrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
                const currentClientHeight = window.innerHeight;
                const currentProgress = currentScrollHeight > currentClientHeight ? 
                    (currentScrollTop / (currentScrollHeight - currentClientHeight)) * 100 : 0;
                
                if (currentProgress > 0) {{
                    const currentData = {{
                        progress: (currentProgress / 100).toFixed(15),
                        scrollTop: currentScrollTop,
                        scrollHeight: currentScrollHeight,
                        current_page: Math.floor(currentProgress / 100 * 100),
                        total_pages: 100,
                        word_count: 0,
                        timestamp: Date.now()
                    }};
                    setLocalProgressData(currentData, BOOK_ID);
                    console.log('已保存书籍 [' + BOOK_ID + '] 的当前进度: ' + currentProgress.toFixed(2) + '%');
                }}
                
                // 更新书籍ID
                BOOK_ID = newBookId;
                console.log('当前书籍ID已更新为: [' + BOOK_ID + ']');
                
                // 重新加载新书籍的进度
                loadBookProgress();
            }}
        }}
        
        // 加载当前书籍的进度
        function loadBookProgress() {{
            console.log('开始加载当前书籍的进度 [书籍ID:', BOOK_ID + ']');
            
            // 确保DOM已经完全渲染后再加载进度
            if (document.readyState === 'loading') {{
                console.log('文档还在加载中，等待DOMContentLoaded事件');
                document.addEventListener('DOMContentLoaded', () => {{
                    setTimeout(() => loadBookProgressInternal(), 100);
                }});
                return;
            }}
            
            loadBookProgressInternal();
        }}
        
        function loadBookProgressInternal() {{
            console.log('加载进度内部逻辑 [书籍ID:', BOOK_ID + ']');
            
            // 优先使用Python端传递的初始进度（仅在首次加载时）
            if (INITIAL_PROGRESS !== null && INITIAL_PROGRESS > 0 && !window.hasLoadedInitialProgress) {{
                console.log('应用Python端传递的初始进度:', (INITIAL_PROGRESS * 100).toFixed(2) + '%');
                
                const initialData = {{
                    progress: INITIAL_PROGRESS.toFixed(15),
                    scrollTop: 0,
                    scrollHeight: document.documentElement.scrollHeight || 10000,
                    current_page: Math.floor(INITIAL_PROGRESS * 100),
                    total_pages: 100,
                    word_count: 0,
                    timestamp: Date.now(),
                    isInitial: true
                }};
                
                applyServerProgress(initialData, INITIAL_PROGRESS, INITIAL_PROGRESS * 100);
                setLocalProgressData(initialData);
                window.hasLoadedInitialProgress = true;
                return;
            }}
            
            // 尝试加载本地进度
            loadLocalProgress();
        }}
        
        
        
        // 文件导入相关
        let selectedFile = null;
        let fileContent = null;
        let selectedDirectoryFiles = null; // 存储选择的目录文件列表
        
        // 书库相关
        let readingHistory = JSON.parse(localStorage.getItem('readingHistory') || '[]');
        let importedBooks = JSON.parse(localStorage.getItem('importedBooks') || '[]');

        // IndexedDB 数据库配置
        const DB_NAME = 'BookReaderDB';
        const DB_VERSION = 1;
        const BOOK_CONTENT_STORE = 'bookContents';

        // IndexedDB 工具函数
        const IndexedDBUtils = {{
            // 打开数据库
            openDB: function() {{
                return new Promise((resolve, reject) => {{
                    const request = indexedDB.open(DB_NAME, DB_VERSION);

                    request.onerror = function(event) {{
                        console.error('IndexedDB 打开失败:', event);
                        reject(event.target.error);
                    }};

                    request.onsuccess = function(event) {{
                        resolve(event.target.result);
                    }};

                    request.onupgradeneeded = function(event) {{
                        const db = event.target.result;
                        if (!db.objectStoreNames.contains(BOOK_CONTENT_STORE)) {{
                            db.createObjectStore(BOOK_CONTENT_STORE, {{ keyPath: 'bookId' }});
                            console.log('IndexedDB 对象存储创建成功');
                        }}
                    }};
                }});
            }},

            // 保存书籍内容到 IndexedDB
            saveBookContent: async function(bookId, content, retryCount = 0) {{
                try {{
                    const db = await this.openDB();
                    const transaction = db.transaction([BOOK_CONTENT_STORE], 'readwrite');
                    const store = transaction.objectStore(BOOK_CONTENT_STORE);

                    const request = store.put({{ bookId: bookId, content: content }});

                    return new Promise((resolve, reject) => {{
                        // 设置超时机制 - Safari 需要更长的超时时间
                        const timeout = setTimeout(() => {{
                            console.warn('IndexedDB 保存超时:', bookId);
                            reject(new Error('保存超时'));
                        }}, 30000); // 增加到 30 秒超时

                        request.onsuccess = function() {{
                            clearTimeout(timeout);
                            console.log('书籍内容已保存到 IndexedDB:', bookId);
                            resolve(true);
                        }};
                        request.onerror = function() {{
                            clearTimeout(timeout);
                            console.error('保存书籍内容到 IndexedDB 失败:', request.error);
                            reject(request.error);
                        }};
                    }});
                }} catch (error) {{
                    console.error('IndexedDB 保存失败:', error);
                    throw error;
                }}
            }},

            // 带重试机制的保存书籍内容
            saveBookContentWithRetry: async function(bookId, content, maxRetries = 3) {{
                for (let i = 0; i < maxRetries; i++) {{
                    try {{
                        await this.saveBookContent(bookId, content);
                        return true;
                    }} catch (error) {{
                        console.error(`保存书籍内容失败 (尝试 ${{i + 1}}/${{maxRetries}}):`, error);
                        if (i < maxRetries - 1) {{
                            // 指数退避重试
                            const delay = Math.pow(2, i) * 1000;
                            console.log(`等待 ${{delay}}ms 后重试...`);
                            await new Promise(resolve => setTimeout(resolve, delay));
                        }} else {{
                            throw error;
                        }}
                    }}
                }}
            }},

            // 保存队列 - 用于批量保存，避免并发过多导致 Safari 崩溃或超时
            saveQueue: [],
            isProcessing: false,

            // 添加到保存队列
            addToQueue: async function(bookId, content) {{
                return new Promise((resolve, reject) => {{
                    this.saveQueue.push({{
                        bookId,
                        content,
                        resolve,
                        reject
                    }});
                    this.processQueue();
                }});
            }},

            // 处理保存队列
            processQueue: async function() {{
                if (this.isProcessing || this.saveQueue.length === 0) {{
                    return;
                }}

                this.isProcessing = true;
                console.log(`开始处理保存队列，队列长度: ${{this.saveQueue.length}}`);

                while (this.saveQueue.length > 0) {{
                    const item = this.saveQueue.shift();
                    try {{
                        await this.saveBookContentWithRetry(item.bookId, item.content);
                        item.resolve(true);
                    }} catch (error) {{
                        console.error(`队列保存失败:`, item.bookId, error);
                        item.reject(error);
                    }}
                    // 添加小延迟，避免 Safari 压力过大
                    if (this.saveQueue.length > 0) {{
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }}
                }}

                this.isProcessing = false;
                console.log('保存队列处理完成');
            }},

            // 从 IndexedDB 获取书籍内容
            getBookContent: async function(bookId) {{
                try {{
                    const db = await this.openDB();
                    const transaction = db.transaction([BOOK_CONTENT_STORE], 'readonly');
                    const store = transaction.objectStore(BOOK_CONTENT_STORE);
                    const request = store.get(bookId);

                    return new Promise((resolve, reject) => {{
                        // 设置超时机制 - Safari 需要更长的超时时间
                        const timeout = setTimeout(() => {{
                            console.warn('IndexedDB 读取超时:', bookId);
                            resolve(null);
                        }}, 30000); // 增加到 30 秒超时

                        request.onsuccess = function() {{
                            clearTimeout(timeout);
                            const result = request.result;
                            if (result) {{
                                console.log('从 IndexedDB 获取书籍内容成功:', bookId);
                                resolve(result.content);
                            }} else {{
                                console.log('IndexedDB 中未找到书籍内容:', bookId);
                                resolve(null);
                            }}
                        }};
                        request.onerror = function() {{
                            clearTimeout(timeout);
                            console.error('从 IndexedDB 获取书籍内容失败:', request.error);
                            reject(request.error);
                        }};
                    }});
                }} catch (error) {{
                    console.error('IndexedDB 读取失败:', error);
                    return null;
                }}
            }},

            // 删除书籍内容
            deleteBookContent: async function(bookId) {{
                try {{
                    const db = await this.openDB();
                    const transaction = db.transaction([BOOK_CONTENT_STORE], 'readwrite');
                    const store = transaction.objectStore(BOOK_CONTENT_STORE);
                    const request = store.delete(bookId);

                    return new Promise((resolve, reject) => {{
                        request.onsuccess = function() {{
                            console.log('书籍内容已从 IndexedDB 删除:', bookId);
                            resolve(true);
                        }};
                        request.onerror = function() {{
                            console.error('从 IndexedDB 删除书籍内容失败:', request.error);
                            reject(request.error);
                        }};
                    }});
                }} catch (error) {{
                    console.error('IndexedDB 删除失败:', error);
                    throw error;
                }}
            }},

            // 获取队列长度
            getQueueLength: function() {{
                return this.saveQueue.length;
            }},

            // 获取所有书籍内容的 ID
            getAllBookIds: async function() {{
                try {{
                    const db = await this.openDB();
                    const transaction = db.transaction([BOOK_CONTENT_STORE], 'readonly');
                    const store = transaction.objectStore(BOOK_CONTENT_STORE);
                    const request = store.getAllKeys();

                    return new Promise((resolve, reject) => {{
                        request.onsuccess = function() {{
                            resolve(request.result);
                        }};
                        request.onerror = function() {{
                            console.error('获取书籍 ID 列表失败:', request.error);
                            reject(request.error);
                        }};
                    }});
                }} catch (error) {{
                    console.error('获取书籍 ID 列表失败:', error);
                    return [];
                }}
            }}
        }};

        // 数据迁移：将旧版本 localStorage 中的书籍内容迁移到 IndexedDB
        (async function migrateOldData() {{
            try {{
                // 检查是否已迁移过
                if (localStorage.getItem('dataMigratedToIndexedDB') === 'true') {{
                    return;
                }}
                
                // 检查是否有旧数据需要迁移（书籍对象中包含 content 字段）
                const hasOldContent = importedBooks.some(book => book.content && typeof book.content === 'string');
                if (!hasOldContent) {{
                    localStorage.setItem('dataMigratedToIndexedDB', 'true');
                    return;
                }}
                
                console.log('开始迁移旧数据到 IndexedDB...');
                
                // 迁移每本书的内容到 IndexedDB
                for (const book of importedBooks) {{
                    if (book.content && typeof book.content === 'string') {{
                        try {{
                            await IndexedDBUtils.saveBookContentWithRetry(book.id, book.content);
                            // 移除本地存储中的 content，只保留元数据
                            book.content = undefined;
                            book.isLoaded = true;
                        }} catch (e) {{
                            console.error('迁移书籍失败:', book.id, e);
                        }}
                    }}
                }}
                
                // 保存迁移后的元数据
                await saveImportedBooksToStorage();
                localStorage.setItem('dataMigratedToIndexedDB', 'true');
                console.log('旧数据迁移完成');
                
            }} catch (error) {{
                console.error('数据迁移失败:', error);
            }}
        }})();

        // LocalStorage存储管理（只存储元数据，内容存储在 IndexedDB）
        async function saveImportedBooksToStorage() {{
            try {{
                // 只保存书籍元数据（不含 content），content 存储在 IndexedDB 中
                const booksMetadata = importedBooks.map(book => ({{
                    id: book.id,
                    title: book.title,
                    fileName: book.fileName,
                    importTime: book.importTime,
                    filePath: book.filePath,
                    lastReadTime: book.lastReadTime
                }}));
                localStorage.setItem('importedBooks', JSON.stringify(booksMetadata));
                return true;
            }} catch (error) {{
                console.error('保存导入书籍到LocalStorage失败:', error);
                if (error.name === 'QuotaExceededError') {{
                    showNotification('存储空间已满，正在清理数据...');
                    // 清理所有导入书籍
                    try {{
                        localStorage.removeItem('importedBooks');
                        importedBooks = [];
                        showNotification('已清理所有导入书籍，请重新导入');
                    }} catch (clearError) {{
                        showNotification('清理数据失败，请检查浏览器设置');
                    }}
                }} else {{
                    showNotification('保存数据失败: ' + error.message);
                }}
                return false;
            }}
        }}
        

        // 检测后端是否在线
        async function checkBackendStatus() {{
            if (!SAVE_PROGRESS_URL && !LOAD_PROGRESS_URL) {{
                isBackendOnline = false;
                return false;
            }}

            try {{
                let checkUrl = SAVE_PROGRESS_URL || LOAD_PROGRESS_URL;
                
                // 创建带超时的Promise
                const fetchWithTimeout = (url, options, timeout = 3000) => {{
                    return Promise.race([
                        fetch(url, options),
                        new Promise((_, reject) =>
                            setTimeout(() => reject(new Error('Timeout')), timeout)
                        )
                    ]);
                }};
                
                // 首先尝试health_check端点
                try {{
                    const healthCheckUrl = checkUrl.replace(new RegExp("save_progress|load_progress"), "health_check");
                    console.log('尝试健康检查URL:', healthCheckUrl);
                    const response = await fetchWithTimeout(healthCheckUrl, {{
                        method: 'GET',
                        cache: 'no-cache'
                    }});
                    
                    if (response.ok) {{
                        isBackendOnline = true;
                        updateServerConnectionInfo();
                        return true;
                    }}
                }} catch (e) {{
                    console.log('Health check failed, trying to discover server:', e);
                    
                    // 尝试发现新的服务器
                    const serverInfo = await discoverServer();
                    if (serverInfo && (serverInfo.host !== 'localhost' || serverInfo.port !== getCurrentPort())) {{
                        console.log(`发现服务器: ${{serverInfo.host}}:${{serverInfo.port}}`);
                        // 更新URL
                        const baseUrl = checkUrl.split('/').slice(0, 3).join('/');
                        const newPath = checkUrl.split('/').slice(3).join('/');
                        checkUrl = `http://${{serverInfo.host}}:${{serverInfo.port}}/${{newPath}}`;
                        
                        // 更新全局变量和本地变量
                        if (SAVE_PROGRESS_URL) {{
                            window.SAVE_PROGRESS_URL = checkUrl;
                            SAVE_PROGRESS_URL = checkUrl;
                        }}
                        if (LOAD_PROGRESS_URL) {{
                            const newLoadUrl = checkUrl.replace('save_progress', 'load_progress');
                            window.LOAD_PROGRESS_URL = newLoadUrl;
                            LOAD_PROGRESS_URL = newLoadUrl;
                        }}
                        
                        // 重新尝试连接
                        const response = await fetchWithTimeout(checkUrl.replace(/save_progress|load_progress/, 'health_check'), {{
                            method: 'GET',
                            cache: 'no-cache'
                        }});
                        
                        if (response.ok) {{
                            isBackendOnline = true;
                            updateServerConnectionInfo();
                            return true;
                        }}
                    }}
                }}
                
                // 如果health_check失败，尝试原端点的HEAD请求
                try {{
                    const headResponse = await fetchWithTimeout(checkUrl, {{
                        method: 'HEAD',
                        mode: 'no-cors',
                        cache: 'no-cache'
                    }});
                    
                    // no-cors模式下，即使失败也会返回opaque response
                    isBackendOnline = true;
                    updateServerConnectionInfo();
                    return true;
                }} catch (e) {{
                    console.log('HEAD request failed:', e);
                    isBackendOnline = false;
                    updateServerConnectionInfo();
                    return false;
                }}
            }} catch (error) {{
                console.log(t('browser_reader.backend_check_failed'), error);
                isBackendOnline = false;
                updateServerConnectionInfo();
                return false;
            }}
        }}
        
        // 发现服务器
        async function discoverServer() {{
            // 从配置获取期望的host和port
            const expectedHost = '{browser_server_host}'; // 从配置获取
            const expectedPort = {browser_server_port}; // 从配置获取
            
            // 尝试连接期望的地址
            try {{
                const response = await fetch("http://" + expectedHost + ":" + expectedPort + "/health_check", {{
                    method: 'GET',
                    cache: 'no-cache',
                    timeout: 500
                }});
                if (response.ok) {{
                    return {{host: expectedHost, port: expectedPort}};
                }}
            }} catch (e) {{
                // 继续尝试其他端口
            }}
            
            // 扫描端口范围
            for (let port = expectedPort; port < expectedPort + 100; port++) {{
                try {{
                    const response = await fetch("http://" + expectedHost + ":" + port + "/health_check", {{
                        method: 'GET',
                        cache: 'no-cache',
                        timeout: 200
                    }});
                    if (response.ok) {{
                        return {{host: expectedHost, port: port}};
                    }}
                }} catch (e) {{
                    // 继续尝试
                }}
            }}
            
            return null;
        }}
        
        // 获取当前端口号
        function getCurrentPort() {{
            const url = SAVE_PROGRESS_URL || LOAD_PROGRESS_URL;
            if (!url) return {browser_server_port};
            
            try {{
                const parsed = new URL(url);
                return parseInt(parsed.port) || {browser_server_port};
            }} catch (e) {{
                return {browser_server_port};
            }}
        }}
        
        // 获取当前服务器信息
        function getCurrentServerInfo() {{
            const url = SAVE_PROGRESS_URL || LOAD_PROGRESS_URL;
            // 使用配置的默认端口而不是硬编码的80
            const defaultPort = {browser_server_port};
            const defaultHost = '{browser_server_host}';
            
            if (!url) return {{host: defaultHost, port: defaultPort}};
            
            try {{
                const parsed = new URL(url);
                return {{
                    host: parsed.hostname || defaultHost,
                    port: parseInt(parsed.port) || defaultPort
                }};
            }} catch (e) {{
                return {{host: defaultHost, port: defaultPort}};
            }}
        }}

        // 获取后端状态提示
        function getBackendStatusText() {{
            return isBackendOnline ? '' : t('browser_reader.backend_offline');
        }}
        
        // 更新服务器连接信息显示
        function updateServerConnectionInfo() {{
            const serverAddressElement = document.getElementById('serverAddressText');
            const connectionModeElement = document.getElementById('connectionModeText');
            
            if (serverAddressElement && connectionModeElement) {{
                try {{
                    // 使用配置的默认值而不是硬编码
                    let serverAddress = '{browser_server_host}:{browser_server_port}'; // 默认值
                    let connectionMode = '离线模式';
                    let modeColor = '#9E9E9E'; // 灰色
                    
                    // 如果有配置的服务器URL，使用配置的地址
                    if (typeof SAVE_PROGRESS_URL !== 'undefined' && SAVE_PROGRESS_URL) {{
                        try {{
                            console.log('更新服务器信息 - SAVE_PROGRESS_URL:', SAVE_PROGRESS_URL);
                            const serverUrl = new URL(SAVE_PROGRESS_URL);
                            const host = serverUrl.hostname || 'localhost';
                            // 处理端口：serverUrl.port在没有指定端口时返回空字符串
                            let port = serverUrl.port;
                            console.log('更新服务器信息 - 原始端口值:', port, typeof port);
                            if (!port || port === '') {{
                                // 使用配置的默认端口而不是硬编码
                                port = '{browser_server_port}';
                                console.log('更新服务器信息 - 使用配置端口:', port);
                            }}
                            serverAddress = host + ':' + port;
                            console.log('更新服务器信息 - 最终服务器地址:', serverAddress);
                            
                            // 根据端口设置连接模式
                            if (port === '54321') {{
                                connectionMode = '固定端口模式';
                                modeColor = '#4CAF50'; // 绿色
                            }} else if (port >= 10000 && port <= 60000) {{
                                connectionMode = '随机端口模式';
                                modeColor = '#FF9800'; // 橙色
                            }} else {{
                                connectionMode = '端口 ' + port;
                                modeColor = '#2196F3'; // 蓝色
                            }}
                        }} catch (e) {{
                            console.warn('解析SAVE_PROGRESS_URL失败:', e);
                            connectionMode = '配置解析错误';
                            modeColor = '#F44336'; // 红色
                        }}
                    }} else {{
                        // 没有配置URL，尝试从当前页面获取
                        try {{
                            const currentUrl = window.location.href;
                            const url = new URL(currentUrl);
                            const host = url.hostname || 'localhost';
                            const port = url.port || '{browser_server_port}';
                            serverAddress = host + ':' + port;
                        }} catch (e) {{
                            console.warn('解析当前URL失败:', e);
                        }}
                    }}
                    
                    // 更新显示
                    serverAddressElement.textContent = serverAddress;
                    serverAddressElement.style.color = isBackendOnline ? '#4CAF50' : '#F44336';
                    connectionModeElement.textContent = connectionMode;
                    connectionModeElement.style.color = modeColor;
                }} catch (error) {{
                    console.error('更新服务器连接信息失败:', error);
                    serverAddressElement.textContent = '连接信息获取失败';
                    connectionModeElement.textContent = '未知';
                    connectionModeElement.style.color = '#F44336';
                }}
            }}
        }}
        
        // 在页面加载完成后更新服务器信息
        document.addEventListener('DOMContentLoaded', function() {{
            updateServerConnectionInfo();
            
            // 立即检查后端状态
            checkBackendStatus().then(isOnline => {{
                if (!isOnline) {{
                    console.log('后端离线，将在用户操作时尝试重连');
                }}
            }});
            
            // 每隔一段时间更新连接状态
            setInterval(function() {{
                updateServerConnectionInfo();
            }}, 5000);
            
            // 每30秒检查一次后端状态
            setInterval(function() {{
                checkBackendStatus();
            }}, 30000);
        }});
        
        // 切换工具栏收缩/展开
        function toggleToolbar() {{
            const toolbar = document.getElementById('toolbar');
            const icon = document.getElementById('toolbarToggleIcon');
            
            toolbar.classList.toggle('collapsed');
            
            if (toolbar.classList.contains('collapsed')) {{
                icon.textContent = '︾';
                showNotification(t('browser_reader.toolbar_hidden'));
            }} else {{
                icon.textContent = '︽';
                showNotification(t('browser_reader.toolbar_expanded'));
            }}
            
            // 更新 toolbar-toggle-container 的位置
            updateToolbarTogglePosition();
        }}
        
        // 动态更新 toolbar-toggle-container 的位置，使其始终跟随在 toolbar 底部
        function updateToolbarTogglePosition() {{
            const toolbar = document.getElementById('toolbar');
            const toggleContainer = document.getElementById('toolbarToggleContainer');
            
            if (toolbar && toggleContainer) {{
                if (toolbar.classList.contains('collapsed')) {{
                    // 如果工具栏收缩，将按钮容器定位到屏幕顶部
                    toggleContainer.style.top = '0px';
                }} else {{
                    // 如果工具栏展开，将按钮容器定位到工具栏底部
                    const toolbarHeight = toolbar.offsetHeight;
                    toggleContainer.style.top = toolbarHeight + 'px';
                }}
            }}
        }}
        
        // 修改字体大小
        function changeFontSize(delta) {{
            const body = document.body;
            const currentSize = parseInt(getComputedStyle(body).fontSize);
            body.style.fontSize = (currentSize + delta) + 'px';
            currentSettings['font_size'] = String(currentSize + delta);
            saveSettings();
            
            // 如果在翻页模式，更新翻页样式
            if (isPaginationMode) {{
                updatePaginationStyles(currentSettings);
            }}
        }}

        // 切换字体设置面板
        function toggleFontSettings() {{
            const panel = document.getElementById('fontSettingsPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }}

        // 修改字体
        function changeFontFamily(fontKey) {{
            const fontFamilies = {str(BrowserReader.FONT_FAMILIES)};
            const font = fontFamilies[fontKey];
            if (font) {{
                document.body.style.fontFamily = font.value;
                currentSettings['font_family'] = font.value;
                saveSettings();
                
                // 如果在翻页模式，更新翻页样式
                if (isPaginationMode) {{
                    updatePaginationStyles(currentSettings);
                }}
            }}
        }}

        // 切换加粗
        function toggleBold() {{
            const btn = document.getElementById('boldBtn');
            const isBold = document.body.style.fontWeight === 'bold';
            document.body.style.fontWeight = isBold ? 'normal' : 'bold';
            currentSettings['font_weight'] = isBold ? 'normal' : 'bold';
            btn.classList.toggle('active', !isBold);
            saveSettings();
        }}

        // 切换倾斜
        function toggleItalic() {{
            const btn = document.getElementById('italicBtn');
            const isItalic = document.body.style.fontStyle === 'italic';
            document.body.style.fontStyle = isItalic ? 'normal' : 'italic';
            currentSettings['font_style'] = isItalic ? 'normal' : 'italic';
            btn.classList.toggle('active', !isItalic);
            saveSettings();
        }}

        // 切换下划线
        function toggleUnderline() {{
            const btn = document.getElementById('underlineBtn');
            const isUnderline = document.body.style.textDecoration === 'underline';
            document.body.style.textDecoration = isUnderline ? 'none' : 'underline';
            currentSettings['text_decoration'] = isUnderline ? 'none' : 'underline';
            btn.classList.toggle('active', !isUnderline);
            saveSettings();
        }}

        // 修改字体颜色
        function changeFontColor(color) {{
            document.body.style.color = color;
            currentSettings['text'] = color;
            saveSettings();
            
            // 如果在翻页模式，更新翻页样式
            if (isPaginationMode) {{
                updatePaginationStyles(currentSettings);
            }}
        }}

        // 修改背景颜色
        function changeBackgroundColor(color) {{
            document.body.style.backgroundColor = color;
            currentSettings['background'] = color;
            saveSettings();
            
            // 如果在翻页模式，更新翻页样式
            if (isPaginationMode) {{
                updatePaginationStyles(currentSettings);
            }}
        }}

        // 修改字间距
        function changeLetterSpacing(value) {{
            document.body.style.letterSpacing = value + 'px';
            currentSettings['letter_spacing'] = value;
            document.getElementById('letterSpacingValue').textContent = value;
            saveSettings();
        }}

        // 修改词间距
        function changeWordSpacing(value) {{
            document.body.style.wordSpacing = value + 'px';
            currentSettings['word_spacing'] = value;
            document.getElementById('wordSpacingValue').textContent = value;
            saveSettings();
        }}

        // 修改对齐方式
        function changeTextAlign(align) {{
            document.body.style.textAlign = align;
            currentSettings['text_align'] = align;
            saveSettings();
        }}

        // 重置字体设置
        function resetFontSettings() {{
            const defaultSettings = themes['light'];

            document.body.style.fontWeight = 'normal';
            document.body.style.fontStyle = 'normal';
            document.body.style.textDecoration = 'none';
            document.body.style.letterSpacing = '0px';
            document.body.style.wordSpacing = '0px';
            document.body.style.textAlign = 'justify';

            currentSettings['font_weight'] = 'normal';
            currentSettings['font_style'] = 'normal';
            currentSettings['text_decoration'] = 'none';
            currentSettings['letter_spacing'] = '0';
            currentSettings['word_spacing'] = '0';
            currentSettings['text_align'] = 'justify';

            document.getElementById('boldBtn').classList.remove('active');
            document.getElementById('italicBtn').classList.remove('active');
            document.getElementById('underlineBtn').classList.remove('active');
            document.getElementById('letterSpacingValue').textContent = '0';
            document.getElementById('wordSpacingValue').textContent = '0';

            saveSettings();
            showNotification(t('browser_reader.font_settings_reset'));
        }}

        // 高亮模式
        let isHighlightMode = false;
        let highlights = JSON.parse(localStorage.getItem('reader_highlights') || '[]');

        function toggleHighlightMode() {{
            isHighlightMode = !isHighlightMode;
            const btn = event.target;
            btn.classList.toggle('active', isHighlightMode);

            if (isHighlightMode) {{
                document.body.style.cursor = 'text';
                showNotification(t('browser_reader.highlight_mode_entered'));
            }} else {{
                document.body.style.cursor = 'default';
                showNotification(t('browser_reader.highlight_mode_exited'));
            }}
        }}

        function addHighlight() {{
            const selection = window.getSelection();
            if (selection.rangeCount > 0 && !selection.isCollapsed) {{
                const range = selection.getRangeAt(0);
                const text = selection.toString();
                const highlight = document.createElement('span');
                highlight.className = 'highlight';
                highlight.textContent = text;

                try {{
                    range.surroundContents(highlight);
                    selection.removeAllRanges();

                    const highlightData = {{
                        id: Date.now(),
                        text: text,
                        position: Math.floor(window.scrollY)
                    }};

                    highlights.push(highlightData);
                    localStorage.setItem('reader_highlights', JSON.stringify(highlights));

                    updateHighlightsList();
                    showNotification(t('browser_reader.highlight_added'));
                }} catch (e) {{
                    console.error('添加高亮失败:', e);
                    showNotification(t('browser_reader.highlight_add_failed'));
                }}
            }}
        }}

        function updateHighlightsList() {{
            const list = document.getElementById('highlightsList');
            if (!list) return;

            list.innerHTML = '';
            highlights.forEach((h, index) => {{
                const item = document.createElement('div');
                item.className = 'note-item';
                item.innerHTML = '<div class="note-text">' + h.text.substring(0, 50) + '...</div>' +
                                    '<div class="note-time">位置: ' + h.position + 'px</div>' +
                                    '<span class="note-delete" onclick="deleteHighlight(' + h.id + ')">×</span>';
                item.onclick = (e) => {{
                    if (e.target.className !== 'note-delete') {{
                        window.scrollTo({{ top: h.position, behavior: 'smooth' }});
                    }}
                }};
                list.appendChild(item);
            }});
        }}

        function deleteHighlight(id) {{
            highlights = highlights.filter(h => h.id !== id);
            localStorage.setItem('reader_highlights', JSON.stringify(highlights));
            showNotification(t('browser_reader.highlight_deleted'));

            const highlightElements = document.querySelectorAll('.highlight');
            highlightElements.forEach(el => {{
                const text = el.textContent;
                if (highlights.find(h => h.text === text) === undefined) {{
                    el.outerHTML = text;
                }}
            }});

            updateHighlightsList();
            showNotification('高亮已删除');
        }}

        // 笔记功能
        let notes = JSON.parse(localStorage.getItem('reader_notes') || '[]');
        let currentNoteTab = 'highlights';

        function toggleNotesMode() {{
            const panel = document.getElementById('notesPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
            updateHighlightsList();
            updateBookmarksList();
            updateNotesList();
        }}

        function closeNotesPanel() {{
            document.getElementById('notesPanel').style.display = 'none';
        }}

        function switchNotesTab(tab) {{
            currentNoteTab = tab;

            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            document.querySelectorAll('.notes-content').forEach(content => content.style.display = 'none');
            document.getElementById(tab + 'Tab').style.display = 'block';

            if (tab === 'highlights') {{
                updateHighlightsList();
            }} else if (tab === 'bookmarks') {{
                updateBookmarksList();
            }} else if (tab === 'notes') {{
                updateNotesList();
            }}
        }}

        function addNote() {{
            const input = document.getElementById('noteInput');
            const text = input.value.trim();

            if (!text) {{
                showNotification(t('browser_reader.note_empty'));
                return;
            }}

            const note = {{
                id: Date.now(),
                text: text,
                position: Math.floor(window.scrollY),
                time: new Date().toLocaleString()
            }};

            notes.push(note);
            localStorage.setItem('reader_notes', JSON.stringify(notes));

            input.value = '';
            updateNotesList();
            showNotification(t('browser_reader.note_added'));
        }}

        function updateNotesList() {{
            const list = document.getElementById('notesList');
            if (!list) return;

            list.innerHTML = '';
            notes.forEach(note => {{
                const item = document.createElement('div');
                item.className = 'note-item';
                item.innerHTML = '<span class="note-delete" onclick="deleteNote(' + note.id + ')">×</span>' +
                                    '<div class="note-text">' + note.text + '</div>' +
                                    '<div class="note-time">' + note.time + '</div>';
                item.onclick = (e) => {{
                    if (e.target.className !== 'note-delete') {{
                        window.scrollTo({{ top: note.position, behavior: 'smooth' }});
                    }}
                }};
                list.appendChild(item);
            }});
        }}

        function deleteNote(id) {{
            notes = notes.filter(n => n.id !== id);
            localStorage.setItem('reader_notes', JSON.stringify(notes));
            updateNotesList();
            showNotification(t('browser_reader.note_deleted'));
        }}

        function updateBookmarksList() {{
            const list = document.getElementById('bookmarksList');
            if (!list) return;

            const savedBookmarks = JSON.parse(localStorage.getItem('reader_bookmarks') || '[]');
            list.innerHTML = '';

            savedBookmarks.forEach((bm, index) => {{
                const item = document.createElement('div');
                item.className = 'note-item';
                const bookmarkText = typeof t === 'function' ? t('browser_reader.bookmark_item', {{number: index + 1}}) : ('书签 ' + (index + 1));
                const bookmarkTime = new Date(bm.time).toLocaleString();
                item.innerHTML = '<span class="note-delete" onclick="deleteBookmark(' + bm.id + ')">×</span>' +
                                    '<div class="note-text">' + bookmarkText + '</div>' +
                                    '<div class="note-time">' + bookmarkTime + '</div>';
                item.onclick = (e) => {{
                    if (e.target.className !== 'note-delete') {{
                        window.scrollTo({{ top: bm.position, behavior: 'smooth' }});
                    }}
                }};
                list.appendChild(item);
            }});
        }}

        function addBookmark() {{
            if (!checkPermission('bookmark.write')) {{
                return;
            }}
            
            const savedBookmarks = JSON.parse(localStorage.getItem('reader_bookmarks') || '[]');

            const bookmark = {{
                id: Date.now(),
                position: Math.floor(window.scrollY),
                time: Date.now()
            }};

            savedBookmarks.push(bookmark);
            localStorage.setItem('reader_bookmarks', JSON.stringify(savedBookmarks));

            updateBookmarksList();
            showNotification(t('browser_reader.bookmark_added'));
        }}

        function deleteBookmark(id) {{
            if (!checkPermission('bookmark.delete')) {{
                return;
            }}
            
            const savedBookmarks = JSON.parse(localStorage.getItem('reader_bookmarks') || '[]');
            const filtered = savedBookmarks.filter(b => b.id !== id);
            localStorage.setItem('reader_bookmarks', JSON.stringify(filtered));
            updateBookmarksList();
            showNotification(t('browser_reader.bookmark_deleted'));
        }}

        // 显示通知
        function showNotification(message) {{
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 12px 24px;
                border-radius: 4px;
                z-index: 3000;
                animation: fadeInOut 2s ease-in-out;
            `;
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {{
                notification.remove();
            }}, 2000);
        }}

        // 监听文本选择事件，在高亮模式下自动添加高亮
        document.addEventListener('mouseup', function(e) {{
            if (isHighlightMode && e.target.id !== 'highlight' && !e.target.classList.contains('highlight')) {{
                const selection = window.getSelection();
                if (selection.rangeCount > 0 && !selection.isCollapsed) {{
                    const rect = selection.getRangeAt(0).getBoundingClientRect();
                    const btn = document.createElement('button');
                    btn.textContent = '高亮';
                    btn.style.cssText = 'position: fixed;' +
                        'top: ' + (rect.top - 40) + 'px;' +
                        'left: ' + rect.left + 'px;' +
                        'background: rgba(100, 149, 237, 0.9);' +
                        'color: white;' +
                        'border: none;' +
                        'padding: 5px 10px;' +
                        'border-radius: 4px;' +
                        'cursor: pointer;' +
                        'z-index: 2000;';
                    btn.onclick = function() {{
                        addHighlight();
                        btn.remove();
                    }};
                    document.body.appendChild(btn);

                    setTimeout(() => {{
                        if (document.body.contains(btn)) {{
                            btn.remove();
                        }}
                    }}, 3000);
                }}
            }}
        }});

        // 切换主题
        function changeTheme(theme) {{
            const selectedTheme = themes[theme];
            
            document.body.style.backgroundColor = selectedTheme.background;
            document.body.style.color = selectedTheme.text;
            document.body.style.fontSize = selectedTheme.font_size + 'px';
            document.body.style.lineHeight = selectedTheme.line_height;
            document.body.style.fontFamily = selectedTheme.font_family;
            
            currentSettings = {{...selectedTheme}};
            
            // 更新UI控件
            const themeSelect = document.getElementById('themeSelect');
            if (themeSelect) {{
                themeSelect.value = getThemeName(selectedTheme);
            }}
            
            // 如果在翻页模式，更新翻页样式
            if (isPaginationMode) {{
                updatePaginationStyles(currentSettings);
            }}
            
            saveSettings();
        }}
        
        // 修改行高
        function changeLineHeight(value) {{
            document.body.style.lineHeight = value;
            currentSettings['line_height'] = value;
            saveSettings();
        }}
        
        // 滚动到顶部
        function scrollToTop() {{
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
            updateProgress();
        }}
        
        // 滚动到底部
        function scrollToBottom() {{
            window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
            updateProgress();
        }}
        
        // 切换位置跳转弹窗显示/隐藏
        function togglePositionJump() {{
            const modal = document.getElementById('positionJumpModal');
            const input = document.getElementById('positionJumpInputModal');
            
            if (modal.style.display === 'none' || modal.style.display === '') {{
                modal.style.display = 'block';
                
                // 获取当前滚动位置并设置为百分比
                const scrollTop = window.scrollY;
                const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
                const currentPercentage = Math.round((scrollTop / scrollHeight) * 100 * 100) / 100; // 保留两位小数
                input.value = currentPercentage.toFixed(2);
                
                // 自动聚焦输入框
                setTimeout(() => {{
                    input.focus();
                    input.select();
                }}, 100);
            }} else {{
                modal.style.display = 'none';
            }}
        }}
        
        // 更新跳转弹窗的语言文本
        function updatePositionJumpTranslations() {{
            if (typeof t === 'function') {{
                document.getElementById('positionJumpTitle').textContent = t('browser_reader.position_jump.title');
                document.getElementById('positionJumpInputLabel').textContent = t('browser_reader.position_jump.input_label');
                document.getElementById('positionJumpInputModal').placeholder = t('browser_reader.position_jump.input_placeholder');
                document.getElementById('positionJumpButton').textContent = t('browser_reader.position_jump.jump_button');
                document.getElementById('positionJumpButton').title = t('browser_reader.position_jump.jump_button_title');
                document.getElementById('positionJumpQuickLabel').textContent = t('browser_reader.position_jump.quick_jump_label');
                document.getElementById('positionJump25').textContent = t('browser_reader.position_jump.jump_25');
                document.getElementById('positionJump25').title = t('browser_reader.position_jump.jump_25');
                document.getElementById('positionJump50').textContent = t('browser_reader.position_jump.jump_50');
                document.getElementById('positionJump50').title = t('browser_reader.position_jump.jump_50');
                document.getElementById('positionJump75').textContent = t('browser_reader.position_jump.jump_75');
                document.getElementById('positionJump75').title = t('browser_reader.position_jump.jump_75');
            }}
        }}
        
        // 关闭位置跳转弹窗
        function closePositionJumpModal() {{
            const modal = document.getElementById('positionJumpModal');
            modal.style.display = 'none';
        }}
        
        // 从弹窗跳转到指定位置
        function jumpToPositionFromModal() {{
            const input = document.getElementById('positionJumpInputModal');
            const targetPercentage = parseFloat(input.value);
            
            // 验证输入值
            if (isNaN(targetPercentage) || targetPercentage < 0 || targetPercentage > 100) {{
                const errorMsg = typeof t === 'function' ? t('browser_reader.position_jump.input_error') : '请输入0-100之间的数值（支持小数点后两位）';
                showNotification(errorMsg);
                return;
            }}
            
            // 计算目标滚动位置
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            const targetScrollTop = Math.round((targetPercentage / 100) * scrollHeight);
            
            // 执行跳转
            window.scrollTo({{ 
                top: targetScrollTop, 
                behavior: 'smooth' 
            }});
            
            // 更新进度
            updateProgress();
            
            // 显示跳转成功提示
            const successMsg = typeof t === 'function' ? t('browser_reader.position_jump.jump_success', {{percentage: targetPercentage.toFixed(2)}}) : '已跳转到 ' + targetPercentage.toFixed(2) + '% 位置';
            showNotification(successMsg);
            
            // 关闭弹窗
            closePositionJumpModal();
        }}
        
        // 从弹窗快速跳转到指定位置
        function quickJumpToFromModal(percentage) {{
            // 计算目标滚动位置
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            const targetScrollTop = Math.round((percentage / 100) * scrollHeight);
            
            // 执行跳转
            window.scrollTo({{ 
                top: targetScrollTop, 
                behavior: 'smooth' 
            }});
            
            // 更新进度
            updateProgress();
            
            // 显示跳转成功提示
            let successMsg;
            if (typeof t === 'function') {{
                const key = 'browser_reader.position_jump.jump_' + percentage + '_success';
                successMsg = t(key);
            }} else {{
                successMsg = '已跳转到 ' + percentage + '% 位置';
            }}
            showNotification(successMsg);
            
            // 关闭弹窗
            closePositionJumpModal();
        }}
        
        // 跳转到指定位置
        function jumpToPosition() {{
            const input = document.getElementById('positionJumpInput');
            const targetPercentage = parseFloat(input.value);
            
            // 验证输入值
            if (isNaN(targetPercentage) || targetPercentage < 0 || targetPercentage > 100) {{
                showNotification(t('browser_reader.position_input_error'));
                // 恢复当前滚动位置的百分比
                const scrollTop = window.scrollY;
                const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
                const currentPercentage = Math.round((scrollTop / scrollHeight) * 100 * 100) / 100; // 保留两位小数
                input.value = currentPercentage.toFixed(2);
                return;
            }}
            
            performJump(targetPercentage);
        }}
        
        // 执行跳转的通用函数
        function performJump(targetPercentage) {{
            // 计算目标滚动位置
            const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
            const targetScrollTop = Math.round((targetPercentage / 100) * scrollHeight);
            
            // 执行跳转
            window.scrollTo({{ 
                top: targetScrollTop, 
                behavior: 'smooth' 
            }});
            
            // 更新进度
            updateProgress();
            
            // 显示跳转成功提示
            showNotification(t('browser_reader.position_jump_success', {{percentage: targetPercentage.toFixed(2)}}));
            
            // 更新输入框的值
            const input = document.getElementById('positionJumpInput');
            input.value = targetPercentage.toFixed(2);
        }}
        
        // 快速跳转到指定位置
        function quickJumpTo(percentage) {{
            performJump(percentage);
        }}
        
        // 处理位置跳转输入框的回车键
        document.addEventListener('DOMContentLoaded', function() {{
            const positionJumpInput = document.getElementById('positionJumpInput');
            if (positionJumpInput) {{
                positionJumpInput.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        jumpToPosition();
                    }}
                }});
                
                // 限制输入范围
                positionJumpInput.addEventListener('input', function(e) {{
                    let value = parseFloat(e.target.value);
                    if (value > 100) {{
                        e.target.value = 100;
                    }} else if (value < 0) {{
                        e.target.value = 0;
                    }}
                }});
            }}
            
            // 弹窗输入框事件监听
            const positionJumpInputModal = document.getElementById('positionJumpInputModal');
            if (positionJumpInputModal) {{
                positionJumpInputModal.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        jumpToPositionFromModal();
                    }}
                }});
                
                // 限制输入范围
                positionJumpInputModal.addEventListener('input', function(e) {{
                    let value = parseFloat(e.target.value);
                    if (value > 100) {{
                        e.target.value = 100;
                    }} else if (value < 0) {{
                        e.target.value = 0;
                    }}
                }});
                
                // ESC键关闭弹窗
                positionJumpInputModal.addEventListener('keydown', function(e) {{
                    if (e.key === 'Escape') {{
                        closePositionJumpModal();
                    }}
                }});
            }}
            
            // 添加滚动监听，实时更新位置跳转输入框
            let scrollUpdateTimeout;
            window.addEventListener('scroll', function() {{
                clearTimeout(scrollUpdateTimeout);
                scrollUpdateTimeout = setTimeout(function() {{
                    const positionJump = document.getElementById('positionJump');
                    const positionJumpInput = document.getElementById('positionJumpInput');
                    
                    // 只有在位置跳转面板显示时才更新输入框
                    if (positionJump && positionJump.style.display !== 'none' && positionJumpInput) {{
                        const scrollTop = window.scrollY;
                        const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
                        const currentPercentage = Math.round((scrollTop / scrollHeight) * 100 * 100) / 100; // 保留两位小数
                        positionJumpInput.value = currentPercentage.toFixed(2);
                    }}
                }}, 100); // 防抖处理，避免频繁更新
            }});
        }});
        
        // 打印内容
        function printContent() {{
            window.print();
        }}

        // 主题管理面板
        function showThemeManager() {{
            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            const themeNames = Object.keys(customThemes);
            
            let themesHtml = '';
            themeNames.forEach(name => {{
                themesHtml += '<div class="theme-item" data-theme="' + name + '">' +
                                        '<div class="theme-name">' + name + '</div>' +
                                        '<div class="theme-preview" style="background: ' + customThemes[name].background + '; color: ' + customThemes[name].text + ';">' + (typeof t === 'function' ? t('browser_reader.preview') : '预览') + '</div>' +
                                        '<div class="theme-actions">' +
                                            '<button onclick="loadCustomThemeByName(\\'' + name + '\\')">' + (typeof t === 'function' ? t('browser_reader.load') : '加载') + '</button>' +
                                            '<button onclick="deleteCustomTheme(\\'' + name + '\\')">' + (typeof t === 'function' ? t('browser_reader.delete') : '删除') + '</button>' +
                                        '</div>' +
                                    '</div>';
            }});
            
            if (themeNames.length === 0) {{
                themesHtml = '<div class="no-themes">' + (typeof t === 'function' ? t('browser_reader.no_custom_themes') : '暂无自定义主题') + '</div>';
            }}
            
            const panel = document.createElement('div');
            panel.className = 'settings-panel theme-manager-panel';
            panel.innerHTML = '<div class="settings-content">' +
                    '<h3>' + (typeof t === 'function' ? t('browser_reader.theme_manager') : '主题管理') + '</h3>' +
                    '<button class="settings-close" onclick="closeThemeManager()">×</button>' +
                    
                    '<div class="theme-manager-content">' +
                        '<div class="current-theme-info">' +
                            '<h4>当前主题设置</h4>' +
                            '<p>背景色: <span style="display: inline-block; width: 20px; height: 20px; background: ' + currentSettings.background + '; vertical-align: middle;"></span> ' + currentSettings.background + '</p>' +
                            '<p>文字色: <span style="display: inline-block; width: 20px; height: 20px; background: ' + currentSettings.text + '; vertical-align: middle;"></span> ' + currentSettings.text + '</p>' +
                            '<p>字体大小: ' + currentSettings.font_size + 'px</p>' +
                            '<p>行高: ' + currentSettings.line_height + '</p>' +
                        '</div>' +
                        
                        '<div class="theme-actions-top">' +
                            '<button onclick="saveCustomThemeFromManager()">保存当前主题</button>' +
                        '</div>' +
                        
                        '<div class="themes-list">' +
                            '<h4>已保存的主题</h4>' +
                            themesHtml +
                        '</div>' +
                    '</div>' +
                '</div>';
            
            document.body.appendChild(panel);
        }}
        
        function closeThemeManager() {{
            const panel = document.querySelector('.theme-manager-panel');
            if (panel) {{
                panel.remove();
            }}
        }}
        
        // 保存自定义主题
        function saveCustomTheme() {{
            const themeName = prompt(t('browser_reader.theme_name_prompt'), t('browser_reader.default_theme_name'));
            if (!themeName) {{
                showNotification(t('browser_reader.theme_name_empty'));
                return;
            }}

            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            customThemes[themeName] = {{...currentSettings}};
            localStorage.setItem('reader_custom_themes', JSON.stringify(customThemes));
            showNotification(t('browser_reader.theme_saved', {{name: themeName}}));
        }}
        
        // 从主题管理器保存主题
        function saveCustomThemeFromManager() {{
            const themeName = prompt(t('browser_reader.theme_name_prompt'), t('browser_reader.default_theme_name'));
            if (!themeName) {{
                showNotification(t('browser_reader.theme_name_empty'));
                return;
            }}

            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            customThemes[themeName] = {{...currentSettings}};
            localStorage.setItem('reader_custom_themes', JSON.stringify(customThemes));
            showNotification(t('browser_reader.theme_saved', {{name: themeName}}));
            
            // 刷新主题管理面板
            closeThemeManager();
            showThemeManager();
        }}

        // 加载自定义主题
        function loadCustomTheme() {{
            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            const themeNames = Object.keys(customThemes);

            if (themeNames.length === 0) {{
                showNotification('没有已保存的自定义主题');
                return;
            }}

            const themeName = prompt('请选择要加载的主题（输入名称）：\\n' + themeNames.join('\\n'), themeNames[0]);
            if (!themeName || !customThemes[themeName]) {{
                showNotification(t('browser_reader.theme_not_exist'));
                return;
            }}

            applySettings(customThemes[themeName]);
            showNotification(t('browser_reader.theme_loaded', {{name: themeName}}));
        }}
        
        // 通过名称加载自定义主题
        function loadCustomThemeByName(themeName) {{
            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            if (!customThemes[themeName]) {{
                showNotification(t('browser_reader.theme_not_exist'));
                return;
            }}

            applySettings(customThemes[themeName]);
            showNotification(t('browser_reader.theme_loaded', {{name: themeName}}));
        }}
        
        // 删除自定义主题
        function deleteCustomTheme(themeName) {{
            if (!confirm('确定要删除主题 "' + themeName + '" 吗？')) {{
                return;
            }}
            
            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            delete customThemes[themeName];
            localStorage.setItem('reader_custom_themes', JSON.stringify(customThemes));
            showNotification(t('browser_reader.theme_deleted', {{name: themeName}}));
            
            // 刷新主题管理面板
            closeThemeManager();
            showThemeManager();
        }}

        // 应用设置
        function applySettings(settings) {{
            document.body.style.backgroundColor = settings.background;
            document.body.style.color = settings.text;
            document.body.style.fontSize = settings.font_size + 'px';
            document.body.style.lineHeight = settings.line_height;
            document.body.style.fontFamily = settings.font_family;
            document.body.style.fontWeight = settings.font_weight;
            document.body.style.fontStyle = settings.font_style;
            document.body.style.textDecoration = settings.text_decoration;
            document.body.style.letterSpacing = settings.letter_spacing + 'px';
            document.body.style.wordSpacing = settings.word_spacing + 'px';
            document.body.style.textAlign = settings.text_align;

            // 更新翻页模式的样式
            updatePaginationStyles(settings);

            // 更新UI控件
            const fontColorInput = document.getElementById('fontColorInput');
            const bgColorInput = document.getElementById('bgColorInput');
            const letterSpacingValue = document.getElementById('letterSpacingValue');
            const wordSpacingValue = document.getElementById('wordSpacingValue');
            const themeSelect = document.getElementById('themeSelect');
            
            if (fontColorInput) fontColorInput.value = settings.text;
            if (bgColorInput) bgColorInput.value = settings.background;
            if (letterSpacingValue) letterSpacingValue.textContent = settings.letter_spacing;
            if (wordSpacingValue) wordSpacingValue.textContent = settings.word_spacing;
            if (themeSelect) themeSelect.value = getThemeName(settings);

            currentSettings = {{...settings}};
            
            // 只在设置真正改变时才保存
            const currentSettingsStr = JSON.stringify(currentSettings);
            const savedSettingsStr = localStorage.getItem('readerSettings');
            if (currentSettingsStr !== savedSettingsStr) {{
                saveSettings();
            }}
        }}
        
        // 更新翻页模式的进度
        function updatePaginationProgress() {{
            if (!isPaginationMode || pages.length === 0) return;
            
            // 计算进度百分比
            const pageProgress = ((currentPageIndex + 1) / pages.length) * 100;
            
            // 更新进度条
            const progressFill = document.getElementById('progressFill');
            if (progressFill) {{
                progressFill.style.width = pageProgress + '%';
            }}
            
            // 更新进度信息
            const progressInfo = document.getElementById('progressInfo');
            if (progressInfo) {{
                progressInfo.textContent = '进度: ' + pageProgress.toFixed(1) + '% (第' + (currentPageIndex + 1) + '页/共' + pages.length + '页)' + getBackendStatusText();
            }}
            
            // 触发进度保存
            triggerPaginationProgressSave(pageProgress);
        }}
        
        // 触发翻页模式下的进度保存
        function triggerPaginationProgressSave(progress) {{
            // 页面加载冷却期间不保存
            const elapsedTime = Date.now() - pageLoadStartTime;
            if (elapsedTime < pageLoadCooldown) {{
                console.log('页面加载冷却期间,跳过自动保存:', Math.round(elapsedTime / 1000), 's/', Math.round(pageLoadCooldown / 1000), 's');
                return;
            }}

            if (saveProgressTimer) {{
                clearTimeout(saveProgressTimer);
            }}

            saveProgressTimer = setTimeout(() => {{
                savePaginationProgress(progress);
            }}, saveProgressInterval);
        }}
        
        // 加载翻页模式下的进度
        function loadPaginationProgress() {{
            console.log('开始加载翻页模式进度，LOAD_PROGRESS_URL:', LOAD_PROGRESS_URL);
            
            // 优先使用Python端传递的初始进度（仅在首次加载时）
            if (INITIAL_PROGRESS !== null && INITIAL_PROGRESS > 0 && !window.hasLoadedInitialProgress) {{
                console.log('应用Python端传递的初始进度（翻页模式）:', (INITIAL_PROGRESS * 100).toFixed(2) + '%');
                
                const initialData = {{
                    progress: INITIAL_PROGRESS.toFixed(15),
                    scrollTop: 0,
                    scrollHeight: 10000,
                    current_page: Math.floor(INITIAL_PROGRESS * 100),
                    total_pages: 100,
                    word_count: 0,
                    timestamp: Date.now(),
                    isInitial: true
                }};
                
                applyPaginationProgress(initialData, INITIAL_PROGRESS, INITIAL_PROGRESS * 100);
                setLocalProgressData(initialData);
                window.hasLoadedInitialProgress = true;
                return;
            }}
            
            if (!LOAD_PROGRESS_URL) {{
                console.log('LOAD_PROGRESS_URL 为空，尝试加载本地翻页进度');
                loadLocalPaginationProgress();
                return;
            }}

            // 设置超时，如果服务器响应太慢则使用本地进度
            const serverTimeout = setTimeout(() => {{
                console.log('服务器响应超时，尝试加载本地翻页进度');
                loadLocalPaginationProgress();
            }}, 3000); // 3秒超时

            fetch(`${{LOAD_PROGRESS_URL}}?book_id=${{BOOK_ID}}`)
                .then(response => {{
                    clearTimeout(serverTimeout);
                    console.log('服务器响应状态:', response.status);
                    if (!response.ok) {{
                        throw new Error('服务器响应错误: ' + response.status);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    console.log('加载到的翻页进度数据:', data);
                    if (data && data.progress !== undefined && pages.length > 0) {{
                        // 从数据库加载的是小数(0-1),转换为百分比(0-100)
                        const progressDecimal = parseFloat(data.progress);
                        const loadedProgress = progressDecimal * 100;  // 转换为百分比

                        // 验证进度是否有效
                        if (isNaN(progressDecimal) || progressDecimal < 0 || progressDecimal > 1) {{
                            console.log('服务器翻页进度数据无效，尝试加载本地翻页进度');
                            loadLocalPaginationProgress();
                            return;
                        }}

                        // 如果进度为0，也尝试加载本地进度
                        if (loadedProgress <= 0) {{
                            console.log('服务器翻页进度为0%，尝试加载本地翻页进度');
                            loadLocalPaginationProgress();
                            return;
                        }}
                        
                        // 服务器进度有效，应用进度
                        applyPaginationProgress(data, progressDecimal, loadedProgress);
                    }} else {{
                        console.log('翻页进度数据不完整或无效，尝试加载本地翻页进度');
                        loadLocalPaginationProgress();
                    }}
                }})
                .catch(err => {{
                    clearTimeout(serverTimeout);
                    console.log('加载翻页进度失败:', err);
                    console.log('尝试加载本地翻页进度');
                    loadLocalPaginationProgress();
                }});
        }}
        
        // 加载本地翻页进度
        function loadLocalPaginationProgress() {{
            console.log('开始加载本地翻页进度 [书籍ID:', BOOK_ID + ']');
            try {{
                // 从localStorage获取本地保存的进度
                const localProgressData = getLocalProgressData();
                if (localProgressData) {{
                    console.log('加载到本地翻页进度数据:', localProgressData);
                    
                    if (localProgressData && localProgressData.progress !== undefined && pages.length > 0) {{
                        const progressDecimal = parseFloat(localProgressData.progress);
                        const loadedProgress = progressDecimal * 100;
                        
                        // 验证本地进度是否有效
                        if (!isNaN(progressDecimal) && progressDecimal >= 0 && progressDecimal <= 1 && loadedProgress > 0) {{
                            // 使用本地进度
                            applyPaginationProgress(localProgressData, progressDecimal, loadedProgress);
                            console.log('已应用本地保存的翻页进度:', loadedProgress + '%', '[书籍ID:', BOOK_ID + ']');
                            return;
                        }}
                    }}
                }}
                console.log('没有找到本地翻页进度数据 [书籍ID:', BOOK_ID + ']');
            }} catch (e) {{
                console.log('加载本地翻页进度失败:', e);
            }}
        }}
        
        // 应用翻页进度（服务器或本地）
        function applyPaginationProgress(data, progressDecimal, loadedProgress) {{
            // 根据进度计算目标页码
            const targetPage = Math.min(Math.floor(progressDecimal * pages.length), pages.length - 1);
            
            console.log('解析翻页进度 - progressDecimal:', progressDecimal, 'loadedProgress:', loadedProgress + '%', 'targetPage:', targetPage);
            
            // 如果进度大于0，跳转到对应页面
            if (loadedProgress > 0 && targetPage > 0) {{
                // 延迟跳转，确保DOM完全渲染
                setTimeout(() => {{
                    showPage(targetPage);
                    console.log('已恢复翻页进度:', loadedProgress + '%', '跳转到第', targetPage + 1, '页');
                }}, 300);
            }} else {{
                console.log('翻页进度为0，从第一页开始');
            }}
        }}
        
        // 保存翻页模式下的进度
        function savePaginationProgress(progress) {{
            console.log('开始保存翻页模式进度，SAVE_PROGRESS_URL:', SAVE_PROGRESS_URL);
            
            // 计算页面相关的进度信息
            const totalPages = pages.length;
            const currentPage = currentPageIndex + 1;
            
            // 估算总字数
            let totalWordCount = 0;
            if (window.cachedWordCount) {{
                totalWordCount = window.cachedWordCount;
            }} else {{
                // 从所有页面计算字数
                pages.forEach(page => {{
                    totalWordCount += page.textContent.replace(/\\s+/g, '').length;
                }});
                window.cachedWordCount = totalWordCount;
            }}
            
            // 估算已读字数（基于页数比例）
            const readWordCount = Math.floor(totalWordCount * (currentPage / totalPages));
            
            // 估算滚动位置（用于兼容）
            const estimatedScrollTop = (currentPageIndex / totalPages) * 10000; // 假设每10000px代表全书
            
            const data = {{
                progress: (progress / 100).toFixed(15), // 转换为小数(0-1)
                scrollTop: estimatedScrollTop,
                scrollHeight: 10000, // 固定高度用于兼容
                current_page: currentPage,
                total_pages: totalPages,
                word_count: readWordCount,
                timestamp: Date.now()
            }};
            
            console.log('翻页模式保存数据:', data);

            // 保存进度到本地localStorage作为备份（始终保存，不管是否启用同步）
            try {{
                setLocalProgressData(data);
                console.log('翻页进度已保存到本地存储 [书籍ID:', BOOK_ID + ']');
            }} catch (e) {{
                console.log('保存翻页进度到本地存储失败:', e);
            }}

            // 如果没有SAVE_PROGRESS_URL或进度同步已禁用，只保存到本地
            if (!SAVE_PROGRESS_URL) {{
                console.log('SAVE_PROGRESS_URL 为空，仅保存翻页进度到本地');
                return;
            }}
            
            // 检查进度同步设置
            if (!progressSyncEnabled) {{
                console.log('进度同步已禁用，仅保存翻页进度到本地');
                return;
            }}

            // 检测后端是否在线
            const backendOnline = checkBackendStatus();
            if (!backendOnline) {{
                console.log('后端离线，仅保存翻页进度到本地');
                updateBackendStatusDisplay();
                return;
            }}

            // 尝试保存到服务器
            console.log('发送翻页进度数据到服务器:', data);
            // 对BOOK_ID进行URL编码，避免非ASCII字符
            const encodedBookId = encodeURIComponent(BOOK_ID);
            fetch(SAVE_PROGRESS_URL, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-Book-ID': encodedBookId
                }},
                body: JSON.stringify(data)
            }}).then(response => {{
                console.log('保存翻页进度响应状态:', response.status);
                if (response.ok) {{
                    isBackendOnline = true;
                    updateBackendStatusDisplay();
                    console.log('翻页进度已成功保存到服务器');
                }} else {{
                    console.log('服务器保存翻页进度失败，状态码:', response.status);
                    isBackendOnline = false;
                    updateBackendStatusDisplay();
                }}
            }}).catch(err => {{
                console.log('保存翻页进度到服务器失败:', err);
                isBackendOnline = false;
                updateBackendStatusDisplay();
            }});
        }}
        
        // 更新翻页模式的样式
        function updatePaginationStyles(settings) {{
            const paginationContainer = document.getElementById('paginationContainer');
            const pageContentEl = document.getElementById('pageContent');
            
            if (paginationContainer) {{
                paginationContainer.style.backgroundColor = settings.background;
                paginationContainer.style.color = settings.text;
                paginationContainer.style.fontFamily = settings.font_family;
                paginationContainer.style.fontSize = settings.font_size + 'px';
                paginationContainer.style.lineHeight = settings.line_height;
                paginationContainer.style.fontWeight = settings.font_weight;
                paginationContainer.style.fontStyle = settings.font_style;
                paginationContainer.style.textDecoration = settings.text_decoration;
                paginationContainer.style.letterSpacing = settings.letter_spacing + 'px';
                paginationContainer.style.wordSpacing = settings.word_spacing + 'px';
                paginationContainer.style.textAlign = settings.text_align;
            }}
            
            if (pageContent) {{
                pageContent.style.backgroundColor = settings.background;
                pageContent.style.color = settings.text;
                pageContent.style.fontFamily = settings.font_family;
                pageContent.style.fontSize = settings.font_size + 'px';
                pageContent.style.lineHeight = settings.line_height;
                pageContent.style.fontWeight = settings.font_weight;
                pageContent.style.fontStyle = settings.font_style;
                pageContent.style.textDecoration = settings.text_decoration;
                pageContent.style.letterSpacing = settings.letter_spacing + 'px';
                pageContent.style.wordSpacing = settings.word_spacing + 'px';
                pageContent.style.textAlign = settings.text_align;
                
                // 更新页面内容内部的所有元素样式
                updatePageContentElements(pageContent, settings);
            }}
        }}
        
        // 更新页面内容内部元素的样式
        function updatePageContentElements(pageContent, settings) {{
            // 更新标题样式
            const headers = pageContent.querySelectorAll('h1, h2, h3');
            headers.forEach(header => {{
                header.style.color = settings.title;
            }});
            
            // 更新段落样式
            const paragraphs = pageContent.querySelectorAll('p');
            paragraphs.forEach(p => {{
                p.style.color = settings.text;
                p.style.fontFamily = settings.font_family;
                p.style.fontSize = settings.font_size + 'px';
                p.style.lineHeight = settings.line_height;
                p.style.fontWeight = settings.font_weight;
                p.style.fontStyle = settings.font_style;
                p.style.textDecoration = settings.text_decoration;
                p.style.letterSpacing = settings.letter_spacing + 'px';
                p.style.wordSpacing = settings.word_spacing + 'px';
                p.style.textAlign = settings.text_align;
            }});
            
            // 更新所有文本元素
            const textElements = pageContent.querySelectorAll('div, span, article, section');
            textElements.forEach(element => {{
                if (!element.classList.contains('page-book-shadow') && 
                    !element.classList.contains('page-curve') && 
                    !element.classList.contains('page-thickness')) {{
                    element.style.color = settings.text;
                    element.style.fontFamily = settings.font_family;
                    element.style.fontSize = settings.font_size + 'px';
                    element.style.lineHeight = settings.line_height;
                    element.style.fontWeight = settings.font_weight;
                    element.style.fontStyle = settings.font_style;
                    element.style.textDecoration = settings.text_decoration;
                    element.style.letterSpacing = settings.letter_spacing + 'px';
                    element.style.wordSpacing = settings.word_spacing + 'px';
                    element.style.textAlign = settings.text_align;
                }}
            }});
        }}

        // 夜间模式切换
        let isNightMode = false;
        let previousTheme = 'light';
        
        function toggleNightMode() {{
            const toggle = document.getElementById('nightModeToggle');
            const icon = document.getElementById('nightModeIcon');
            const text = document.getElementById('nightModeText');
            
            isNightMode = !isNightMode;
            
            if (isNightMode) {{
                // 保存当前主题
                previousTheme = document.getElementById('themeSelect').value;
                
                // 切换到深色主题
                changeTheme('dark');
                
                // 更新UI
                toggle.classList.add('active');
                icon.textContent = '☀️';
                text.textContent = '日间模式';
                
                showNotification(t('browser_reader.night_mode_on'));
            }} else {{
                // 恢复之前的主题
                changeTheme(previousTheme);
                
                // 更新UI
                toggle.classList.remove('active');
                icon.textContent = '🌙';
                text.textContent = '夜间模式';
                
                showNotification(t('browser_reader.night_mode_off'));
            }}
        }}
        
        // 全屏模式
        function toggleFullscreen() {{
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen().then(() => {{
                    document.getElementById('fullscreenIndicator').classList.add('show');
                }}).catch(err => {{
                    showNotification('全屏模式不可用');
                }});
            }} else {{
                document.exitFullscreen();
            }}
        }}
        
        // 监听全屏变化事件
        document.addEventListener('fullscreenchange', () => {{
            const indicator = document.getElementById('fullscreenIndicator');
            if (document.fullscreenElement) {{
                indicator.classList.add('show');
            }} else {{
                indicator.classList.remove('show');
            }}
        }});

        // 专注模式
        let isFocusMode = false;
        let focusModeHiddenElements = [];
        
        function toggleFocusMode() {{
            isFocusMode = !isFocusMode;
            const toolbar = document.querySelector('.toolbar');
            const stats = document.querySelector('.reading-stats');
            const statsEnhanced = document.querySelector('.reading-stats-enhanced');
            const progress = document.querySelector('.progress-bar');
            const nightModeToggle = document.querySelector('.night-mode-toggle');
            const tocToggle = document.querySelector('.toc-toggle-btn');
            const bookmarkBtn = document.querySelector('.bookmark-btn');
            const autoScrollControls = document.querySelector('.auto-scroll-controls');
            const speechControls = document.querySelector('.speech-controls');
            const keyboardHint = document.querySelector('.keyboard-hint');
            const searchContainer = document.querySelector('.search-container');
            const tocContainer = document.querySelector('.toc-container');
            const fontSettingsPanel = document.querySelector('#fontSettingsPanel');
            const notesPanel = document.querySelector('#notesPanel');

            if (isFocusMode) {{
                // 记录当前显示状态并隐藏元素
                focusModeHiddenElements = [];
                
                const elementsToHide = [
                    toolbar, stats, statsEnhanced, progress, nightModeToggle, 
                    tocToggle, bookmarkBtn, autoScrollControls, speechControls, 
                    keyboardHint, searchContainer, tocContainer
                ];
                
                elementsToHide.forEach(element => {{
                    if (element && element.style.display !== 'none') {{
                        focusModeHiddenElements.push(element);
                        element.style.display = 'none';
                    }}
                }});
                
                // 隐藏面板
                if (fontSettingsPanel && fontSettingsPanel.style.display !== 'none') {{
                    focusModeHiddenElements.push(fontSettingsPanel);
                    fontSettingsPanel.style.display = 'none';
                }}
                
                if (notesPanel && notesPanel.style.display !== 'none') {{
                    focusModeHiddenElements.push(notesPanel);
                    notesPanel.style.display = 'none';
                }}
                
                // 退出高亮模式
                if (isHighlightMode) {{
                    toggleHighlightMode();
                }}
                
                // 停止自动滚动
                if (autoScrollInterval) {{
                    toggleAutoScroll();
                }}
                
                // 停止朗读
                if (isSpeaking) {{
                    stopSpeech();
                }}
                
                showNotification(t('browser_reader.focus_mode_on'));
            }} else {{
                // 恢复隐藏的元素
                focusModeHiddenElements.forEach(element => {{
                    if (element === toolbar) {{
                        element.style.display = 'flex';
                    }} else if (element === stats || element === statsEnhanced) {{
                        element.style.display = 'block';
                    }} else {{
                        element.style.display = '';
                    }}
                }});
                
                focusModeHiddenElements = [];
                showNotification(t('browser_reader.focus_mode_off'));
            }}
        }}

        // 增强的自动滚动
        let autoScrollInterval = null;
        let autoScrollSpeed = 1;
        let autoScrollPanelVisible = false;
        
        function toggleAutoScroll() {{
            const controls = document.getElementById('autoScrollControls');
            const toggleBtn = document.getElementById('autoScrollToggleBtn');
            
            if (autoScrollInterval) {{
                // 停止自动滚动
                clearInterval(autoScrollInterval);
                autoScrollInterval = null;
                toggleBtn.textContent = '开始滚动';
                toggleBtn.classList.remove('active');
                showNotification('自动滚动已停止');
            }} else {{
                // 开始自动滚动
                autoScrollPanelVisible = true;
                controls.classList.add('show');
                
                autoScrollInterval = setInterval(() => {{
                    window.scrollBy(0, autoScrollSpeed);
                    updateProgress();
                    updateEnhancedReadingStats();
                }}, 100);
                
                toggleBtn.textContent = '停止滚动';
                toggleBtn.classList.add('active');
                showNotification('自动滚动已开启，速度: ' + autoScrollSpeed);
            }}
        }}
        
        function increaseScrollSpeed() {{
            if (autoScrollSpeed < 10) {{
                autoScrollSpeed += 0.5;
                updateScrollSpeedDisplay();
            }}
        }}
        
        function decreaseScrollSpeed() {{
            if (autoScrollSpeed > 0.5) {{
                autoScrollSpeed -= 0.5;
                updateScrollSpeedDisplay();
            }}
        }}
        
        function setScrollSpeed(value) {{
            autoScrollSpeed = parseFloat(value);
            updateScrollSpeedDisplay();
        }}
        
        function updateScrollSpeedDisplay() {{
            document.getElementById('scrollSpeedDisplay').textContent = autoScrollSpeed;
            document.getElementById('scrollSpeedSlider').value = autoScrollSpeed;
        }}
        
        function resetAutoScroll() {{
            autoScrollSpeed = 1;
            updateScrollSpeedDisplay();
            
            if (autoScrollInterval) {{
                toggleAutoScroll();
            }}
            
            showNotification('自动滚动已重置');
        }}
        
        function toggleAutoScrollPanel() {{
            const controls = document.getElementById('autoScrollControls');
            autoScrollPanelVisible = !autoScrollPanelVisible;
            
            if (autoScrollPanelVisible) {{
                controls.classList.add('show');
            }} else {{
                controls.classList.remove('show');
            }}
        }}

        // 增强的文字朗读
        let isSpeaking = false;
        let speechSynthesis = window.speechSynthesis;
        let currentUtterance = null;
        let speechPanelVisible = false;
        let voices = [];
        let selectedVoice = null;
        let speechRate = 1.0;
        let speechPitch = 1.0;
        let currentParagraphIndex = 0;
        let paragraphs = [];
        
        // 初始化语音
        function initSpeech() {{
            // 加载语音列表
            function loadVoices() {{
                voices = speechSynthesis.getVoices();
                const voiceSelect = document.getElementById('voiceSelect');
                voiceSelect.innerHTML = '<option value="">选择语音</option>';
                
                // 优先显示中文语音
                const chineseVoices = voices.filter(voice => voice.lang.includes('zh'));
                const otherVoices = voices.filter(voice => !voice.lang.includes('zh'));
                
                [...chineseVoices, ...otherVoices].forEach((voice, index) => {{
                    const option = document.createElement('option');
                    option.value = index;
                    option.textContent = voice.name + ' (' + voice.lang + ')';
                    if (voice.default) {{
                        option.textContent += ' [默认]';
                    }}
                    voiceSelect.appendChild(option);
                }});
                
                // 默认选择第一个中文语音
                if (chineseVoices.length > 0) {{
                    const firstChineseIndex = voices.indexOf(chineseVoices[0]);
                    voiceSelect.value = firstChineseIndex;
                    selectedVoice = chineseVoices[0];
                }}
            }}
            
            loadVoices();
            if (speechSynthesis.onvoiceschanged !== undefined) {{
                speechSynthesis.onvoiceschanged = loadVoices;
            }}
        }}
        
        function toggleSpeech() {{
            const controls = document.getElementById('speechControls');
            
            // 切换控制面板显示状态
            speechPanelVisible = !speechPanelVisible;
            
            if (speechPanelVisible) {{
                controls.classList.add('show');
                if (voices.length === 0) {{
                    initSpeech();
                }}
            }} else {{
                controls.classList.remove('show');
            }}
        }}
        
        function toggleSpeechPlayback() {{
            const playbackBtn = document.getElementById('speechPlaybackBtn');
            const statusDisplay = document.getElementById('speechStatus');
            
            if (isSpeaking) {{
                stopSpeech();
            }} else {{
                startSpeech();
            }}
        }}
        
        function startSpeech() {{
            const selectedText = window.getSelection().toString();
            const playbackBtn = document.getElementById('speechPlaybackBtn');
            const statusDisplay = document.getElementById('speechStatus');
            
            if (selectedText) {{
                // 朗读选中文本
                speakText(selectedText);
            }} else {{
                // 朗读书籍内容
                paragraphs = Array.from(document.querySelectorAll('#content p, #content div, #content h1, #content h2, #content h3'));
                if (paragraphs.length === 0) {{
                    showNotification('没有可朗读的内容');
                    return;
                }}
                
                // 找到当前可见的段落
                const scrollPos = window.scrollY + 100;
                currentParagraphIndex = 0;
                
                for (let i = 0; i < paragraphs.length; i++) {{
                    if (paragraphs[i].offsetTop >= scrollPos) {{
                        currentParagraphIndex = i;
                        break;
                    }}
                }}
                
                speakCurrentParagraph();
            }}
            
            if (playbackBtn) {{
                playbackBtn.textContent = '停止朗读';
                playbackBtn.classList.add('active');
            }}
            
            if (statusDisplay) {{
                statusDisplay.textContent = '正在朗读';
            }}
        }}
        
        function stopSpeech() {{
            speechSynthesis.cancel();
            isSpeaking = false;
            
            const playbackBtn = document.getElementById('speechPlaybackBtn');
            const statusDisplay = document.getElementById('speechStatus');
            
            if (playbackBtn) {{
                playbackBtn.textContent = typeof t === 'function' ? t('browser_reader.speech_start') : '开始朗读';
                playbackBtn.classList.remove('active');
            }}
            
            if (statusDisplay) {{
                statusDisplay.textContent = '已停止';
            }}
            
            showNotification('朗读已停止');
        }}
        
        function speakCurrentParagraph() {{
            if (currentParagraphIndex >= paragraphs.length) {{
                stopSpeech();
                showNotification('朗读完成');
                return;
            }}
            
            const paragraph = paragraphs[currentParagraphIndex];
            const text = paragraph.textContent.trim();
            
            if (!text) {{
                currentParagraphIndex++;
                speakCurrentParagraph();
                return;
            }}
            
            // 滚动到当前段落
            paragraph.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            
            // 更新状态
            const statusDisplay = document.getElementById('speechStatus');
            statusDisplay.textContent = '段落 ' + (currentParagraphIndex + 1) + '/' + paragraphs.length;
            
            speakText(text, () => {{
                currentParagraphIndex++;
                setTimeout(speakCurrentParagraph, 500);
            }});
        }}
        
        function speakText(text, onEnd) {{
            speechSynthesis.cancel();
            currentUtterance = new SpeechSynthesisUtterance(text);
            
            // 设置语音参数
            if (selectedVoice) {{
                currentUtterance.voice = selectedVoice;
            }}
            currentUtterance.rate = speechRate;
            currentUtterance.pitch = speechPitch;
            currentUtterance.lang = 'zh-CN';
            currentUtterance.volume = 1.0;

            currentUtterance.onend = () => {{
                isSpeaking = false;
                const playbackBtn = document.getElementById('speechPlaybackBtn');
                const statusDisplay = document.getElementById('speechStatus');
                
                if (playbackBtn) {{
                    playbackBtn.textContent = typeof t === 'function' ? t('browser_reader.speech_start') : '开始朗读';
                    playbackBtn.classList.remove('active');
                }}
                
                if (statusDisplay) {{
                    statusDisplay.textContent = '已停止';
                }}
                
                if (onEnd) {{
                    onEnd();
                }}
            }};

            currentUtterance.onerror = (event) => {{
                isSpeaking = false;
                const playbackBtn = document.getElementById('speechPlaybackBtn');
                const statusDisplay = document.getElementById('speechStatus');
                
                if (playbackBtn) {{
                    playbackBtn.textContent = typeof t === 'function' ? t('browser_reader.speech_start') : '开始朗读';
                    playbackBtn.classList.remove('active');
                }}
                
                if (statusDisplay) {{
                    statusDisplay.textContent = '朗读出错';
                }}
                
                showNotification('朗读出错: ' + event.error);
            }};

            speechSynthesis.speak(currentUtterance);
            isSpeaking = true;
        }}
        
        function changeVoice(voiceIndex) {{
            if (voiceIndex === '') {{
                selectedVoice = null;
            }} else {{
                selectedVoice = voices[parseInt(voiceIndex)];
            }}
        }}
        
        function changeSpeechRate(rate) {{
            speechRate = parseFloat(rate);
        }}
        
        function changeSpeechPitch(pitch) {{
            speechPitch = parseFloat(pitch);
        }}

        // 增强的阅读统计
        let readingStartTime = Date.now();
        let sessionStartTime = Date.now();
        let totalReadingTime = parseInt(localStorage.getItem('totalReadingTime') || '0');
        let lastWordCount = 0;
        let statsPanelVisible = false;
        
        function toggleReadingStats() {{
            const panel = document.getElementById('readingStatsEnhanced');
            const small_panel = document.getElementById('readingStats');
            statsPanelVisible = !statsPanelVisible;
            
            if (statsPanelVisible) {{
                panel.classList.add('show');
                small_panel.classList.remove('show');
                small_panel.classList.add('hide');
                updateEnhancedReadingStats();
            }} else {{
                panel.classList.remove('show');
                small_panel.classList.remove('hide');
                small_panel.classList.add('show');
            }}
        }}
        
        function updateEnhancedReadingStats() {{
            if (!statsPanelVisible) return;
            
            const currentTime = Date.now();
            const sessionElapsed = Math.floor((currentTime - sessionStartTime) / 1000);
            const totalElapsed = totalReadingTime + sessionElapsed;
            
            // 格式化时间显示
            const formatTime = (seconds) => {{
                const hours = Math.floor(seconds / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                const secs = seconds % 60;
                
                if (hours > 0) {{
                    return hours + ':' + minutes.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');
                }} else {{
                    return minutes + ':' + secs.toString().padStart(2, '0');
                }}
            }};
            
            // 更新时间显示
            document.getElementById('totalReadingTime').textContent = formatTime(totalElapsed);
            document.getElementById('sessionReadingTime').textContent = formatTime(sessionElapsed);
            
            // 计算进度
            const scrollTop = window.scrollY;
            const scrollHeight = document.documentElement.scrollHeight;
            const clientHeight = window.innerHeight;
            const progress = Math.min(100, Math.max(0, (scrollTop / (scrollHeight - clientHeight)) * 100));
            
            document.getElementById('readingProgress').textContent = progress.toFixed(1) + '%';
            
            // 计算总字数和已读字数
            const content = document.getElementById('content');
            if (content) {{
                const totalWords = content.textContent.replace(/\\s+/g, '').length;
                const readWords = Math.floor(totalWords * (progress / 100));
                
                document.getElementById('totalWordCount').textContent = readWords.toLocaleString();
                
                // 计算平均阅读速度
                if (sessionElapsed > 0) {{
                    const avgSpeed = Math.round(readWords / (sessionElapsed / 60));
                    document.getElementById('avgReadingSpeed').textContent = avgSpeed;
                }}
                
                // 估算剩余时间
                if (avgSpeed > 0) {{
                    const remainingWords = totalWords - readWords;
                    const estimatedMinutes = Math.ceil(remainingWords / avgSpeed);
                    document.getElementById('estimatedTimeLeft').textContent = formatTime(estimatedMinutes * 60);
                }}
            }}
        }}
        
        // 阅读时间统计
        function updateReadingStats() {{
            const elapsed = Math.floor((Date.now() - readingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            document.getElementById('readingTime').textContent = minutes + '分' + seconds + '秒';

            // 计算阅读速度（字/分）
            const wordCountElement = document.getElementById('wordCount');
            const currentWordCount = parseInt(wordCountElement.textContent) || 0;
            if (minutes > 0 && currentWordCount > lastWordCount) {{
                const wordsRead = currentWordCount - lastWordCount;
                const speed = Math.round(wordsRead / minutes);
                document.getElementById('readingSpeed').textContent = speed;
            }}
        }}

        // 每10秒更新一次阅读统计
        setInterval(updateReadingStats, 10000);

        
        // 更新进度条
        function updateProgress() {{
            const scrollTop = window.scrollY;
            // 使用 document.documentElement.scrollHeight 更准确
            const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
            const clientHeight = window.innerHeight;

            // 修复进度计算，确保分母不为零且进度不超过100%
            const scrollableHeight = Math.max(scrollHeight - clientHeight, 1);
            let progress = (scrollTop / scrollableHeight) * 100;
            progress = Math.min(100, Math.max(0, progress));

            // 详细日志
            console.log('updateProgress - scrollTop:', scrollTop, 'scrollHeight:', scrollHeight, 'clientHeight:', clientHeight, 'scrollableHeight:', scrollableHeight, 'calculated progress:', progress);

            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressInfo').textContent = '进度: ' + progress.toFixed(1) + '%' + getBackendStatusText();

            // 触发自动保存进度
            triggerProgressSave(progress);
        }}

        // 更新后端状态显示
        function updateBackendStatusDisplay() {{
            const progressInfo = document.getElementById('progressInfo');
            if (progressInfo) {{
                const currentText = progressInfo.textContent.replace(/（后端离线）|（后端在线）/, '').trim();
                progressInfo.textContent = currentText + getBackendStatusText();
            }}
        }}
        
        // 触发进度保存（防抖）
        function triggerProgressSave(progress) {{
            // 页面加载冷却期间不保存,避免恢复进度时触发错误保存
            const elapsedTime = Date.now() - pageLoadStartTime;
            if (elapsedTime < pageLoadCooldown) {{
                console.log('页面加载冷却期间,跳过自动保存:', Math.round(elapsedTime / 1000), 's/', Math.round(pageLoadCooldown / 1000), 's');
                return;
            }}

            if (saveProgressTimer) {{
                clearTimeout(saveProgressTimer);
            }}

            saveProgressTimer = setTimeout(() => {{
                saveProgress(progress);
            }}, saveProgressInterval);
        }}
        
        // 保存进度到服务器
        async function saveProgress(progress) {{
            console.log('开始保存进度，SAVE_PROGRESS_URL:', SAVE_PROGRESS_URL);
            
            const scrollTop = window.scrollY;
            // 使用 document.documentElement.scrollHeight 更准确
            const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
            const clientHeight = window.innerHeight;
            const scrollableHeight = Math.max(scrollHeight - clientHeight, 1);

            // 验证进度值
            const progressString = progress.toFixed(2);
            const progressNumber = parseFloat(progressString);
            console.log('保存进度验证:');
            console.log('  - 原始 progress(百分比):', progress, typeof progress);
            console.log('  - 字符串化 progress:', progressString, typeof progressString);
            console.log('  - 数值化 progress:', progressNumber, typeof progressNumber);
            console.log('  - scrollTop:', scrollTop, 'px');
            console.log('  - scrollHeight:', scrollHeight, 'px');
            console.log('  - clientHeight:', clientHeight, 'px');
            console.log('  - scrollableHeight:', scrollableHeight, 'px');
            console.log('  - 重新计算的 progress:', ((scrollTop / scrollableHeight) * 100).toFixed(2));

            // 将百分比(0-100)转换为小数(0-1)保存到数据库
            // 使用高精度(15位小数)以匹配终端阅读器的精度
            const progressDecimal = progress / 100;
            const progressDecimalString = progressDecimal.toFixed(15);

            // 计算页数（假设每页1000px）
            const estimatedPageHeight = 1000;
            const total_pages = Math.max(1, Math.floor(scrollHeight / estimatedPageHeight));
            const current_page = Math.min(total_pages, Math.floor(progressDecimal * total_pages));

            // 计算字数（缓存，避免每次都计算）
            if (!window.cachedWordCount) {{
                const content = document.getElementById('content');
                if (content) {{
                    window.cachedWordCount = content.textContent.replace(/\\s+/g, '').length;
                }}
            }}
            const word_count = window.cachedWordCount || 0;

            const data = {{
                progress: progressDecimalString,
                scrollTop: scrollTop,
                scrollHeight: scrollHeight,
                current_page: current_page,
                total_pages: total_pages,
                word_count: word_count,
                timestamp: Date.now()
            }};
            console.log('最终保存数据(小数):', data);

            // 缓存保存的值(使用小数)
            cachedProgress = progressDecimal;
            cachedScrollTop = scrollTop;
            cachedScrollHeight = scrollHeight;
            console.log('缓存进度值(小数):', cachedProgress);

            // 保存进度到本地localStorage作为备份（始终保存，不管是否启用同步）
            try {{
                setLocalProgressData(data);
                console.log('进度已保存到本地存储 [书籍ID:', BOOK_ID + ']');
            }} catch (e) {{
                console.log('保存进度到本地存储失败:', e);
            }}

            // 如果没有SAVE_PROGRESS_URL或进度同步已禁用，只保存到本地
            if (!SAVE_PROGRESS_URL) {{
                console.log('SAVE_PROGRESS_URL 为空，仅保存到本地');
                return;
            }}
            
            // 检查进度同步设置
            if (!progressSyncEnabled) {{
                console.log('进度同步已禁用，仅保存到本地');
                return;
            }}

            // 检测后端是否在线
            const backendOnline = await checkBackendStatus();
            if (!backendOnline) {{
                console.log('后端离线，仅保存到本地');
                updateBackendStatusDisplay();
                return;
            }}

            // 尝试保存到服务器
            console.log('发送进度数据到服务器:', data);
            // 对BOOK_ID进行URL编码，避免非ASCII字符
            const encodedBookId = encodeURIComponent(BOOK_ID);
            fetch(SAVE_PROGRESS_URL, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-Book-ID': encodedBookId
                }},
                body: JSON.stringify(data)
            }}).then(response => {{
                console.log('保存进度响应状态:', response.status);
                if (response.ok) {{
                    isBackendOnline = true;
                    updateBackendStatusDisplay();
                    console.log('进度已成功保存到服务器');
                }} else {{
                    console.log('服务器保存进度失败，状态码:', response.status);
                    isBackendOnline = false;
                    updateBackendStatusDisplay();
                }}
            }}).catch(err => {{
                console.error('保存进度到服务器失败:', err);
                console.error('错误详情:', err.message, err.stack);
                isBackendOnline = false;
                updateBackendStatusDisplay();
                // 显示错误通知
                if (typeof showNotification === 'function') {{
                    showNotification('保存进度失败: ' + err.message);
                }}
            }});
        }}
        
        // 从服务器加载进度
        function loadProgress() {{
            console.log('开始加载进度，LOAD_PROGRESS_URL:', LOAD_PROGRESS_URL);
            
            // 使用新的进度加载函数
            if (INITIAL_PROGRESS !== null && INITIAL_PROGRESS > 0 && !window.hasLoadedInitialProgress) {{
                loadBookProgress();
                return;
            }}
            
            if (!LOAD_PROGRESS_URL) {{
                console.log('LOAD_PROGRESS_URL 为空，尝试加载本地进度');
                loadLocalProgress();
                return;
            }}

            // 设置超时，如果服务器响应太慢则使用本地进度
            const serverTimeout = setTimeout(() => {{
                console.log('服务器响应超时，尝试加载本地进度');
                loadLocalProgress();
            }}, 3000); // 3秒超时

            fetch(`${{LOAD_PROGRESS_URL}}?book_id=${{BOOK_ID}}`)
                .then(response => {{
                    clearTimeout(serverTimeout);
                    console.log('服务器响应状态:', response.status);
                    if (!response.ok) {{
                        throw new Error('服务器响应错误: ' + response.status);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    console.log('加载到的进度数据(小数):', data);
                    if (data && data.progress !== undefined) {{
                        // 从数据库加载的是小数(0-1),转换为百分比(0-100)
                        const progressDecimal = parseFloat(data.progress);
                        const progress = progressDecimal * 100;  // 转换为百分比

                        // 验证进度是否有效
                        if (isNaN(progressDecimal) || progressDecimal < 0 || progressDecimal > 1) {{
                            console.log('服务器进度数据无效，尝试加载本地进度');
                            loadLocalProgress();
                            return;
                        }}

                        // 如果进度为0，也尝试加载本地进度
                        if (progress <= 0) {{
                            console.log('服务器进度为0%，尝试加载本地进度');
                            loadLocalProgress();
                            return;
                        }}

                        // 服务器进度有效，使用服务器进度
                        applyServerProgress(data, progressDecimal, progress);
                    }} else {{
                        console.log('进度数据不完整或无效，尝试加载本地进度');
                        loadLocalProgress();
                    }}
                }})
                .catch(err => {{
                    clearTimeout(serverTimeout);
                    console.log('加载进度失败:', err);
                    console.log('尝试加载本地进度');
                    loadLocalProgress();
                }});
        }}
        
        // 加载本地进度
        function loadLocalProgress() {{
            console.log('开始加载本地进度 [书籍ID:', BOOK_ID + ']');
            try {{
                // 从localStorage获取本地保存的进度
                const localProgressData = getLocalProgressData();
                if (localProgressData) {{
                    console.log('加载到本地进度数据:', localProgressData);
                    
                    if (localProgressData && localProgressData.progress !== undefined) {{
                        const progressDecimal = parseFloat(localProgressData.progress);
                        const progress = progressDecimal * 100;
                        
                        console.log('解析本地进度 - progressDecimal:', progressDecimal, 'progress:', progress + '%');
                        
                        // 验证本地进度是否有效
                        if (!isNaN(progressDecimal) && progressDecimal >= 0 && progressDecimal <= 1 && progress > 0) {{
                            // 使用本地进度
                            applyServerProgress(localProgressData, progressDecimal, progress);
                            console.log('✅ 已应用本地保存的阅读进度:', progress.toFixed(2) + '%', '[书籍ID:', BOOK_ID + ']');
                            showNotification('已恢复上次阅读位置: ' + progress.toFixed(1) + '%');
                            return;
                        }} else if (progress <= 0) {{
                            console.log('📍 阅读进度为 0%，滚动到顶部 [书籍ID:', BOOK_ID + ']');
                            // 进度为0，滚动到顶部
                            window.scrollTo({{ top: 0, behavior: 'smooth' }});
                            return;
                        }}
                    }}
                }}
                console.log('❌ 没有找到本地进度数据 [书籍ID:', BOOK_ID + ']');
                console.log('📍 滚动到顶部 [书籍ID:', BOOK_ID + ']');
                // 没有进度数据，滚动到顶部
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }} catch (e) {{
                console.log('❌ 加载本地进度失败:', e);
                console.log('📍 滚动到顶部 [书籍ID:', BOOK_ID + ']');
                // 出错时滚动到顶部
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }}
        }}
        
        // 应用进度（服务器或本地）
        function applyServerProgress(data, progressDecimal, progress) {{
            // 尝试获取保存的滚动位置
            let scrollTop = parseInt(data.scrollTop || 0);
            let savedScrollHeight = parseInt(data.scrollHeight || 0);

            // 如果没有保存的滚动位置但有进度,根据进度计算滚动位置
            if (scrollTop === 0 && progress > 0) {{
                const actualScrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
                const clientHeight = window.innerHeight;
                const scrollableHeight = Math.max(actualScrollHeight - clientHeight, 1);
                scrollTop = Math.round((progressDecimal) * scrollableHeight);
                console.log('根据进度计算滚动位置:', scrollTop + 'px', '可滚动高度:', scrollableHeight + 'px');
            }}

            console.log('解析进度 - progressDecimal:', progressDecimal, 'progress:', progress + '%', 'scrollTop:', scrollTop + 'px', 'savedScrollHeight:', savedScrollHeight + 'px');
            console.log('当前文档实际高度:', (document.documentElement.scrollHeight || document.body.scrollHeight) + 'px');

            // 检查 scrollTop 是否合理（不应超过文档实际高度太多）
            const actualScrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
            const maxScrollTop = Math.max(actualScrollHeight - window.innerHeight, 0);
            const safeScrollTop = Math.min(scrollTop, maxScrollTop);

            console.log('安全滚动位置 - maxScrollTop:', maxScrollTop + 'px', 'safeScrollTop:', safeScrollTop + 'px');

            // 只有当进度大于 0 且滚动位置大于 0 时才滚动
            if (progress > 0 && safeScrollTop > 0) {{
                // 延迟滚动，确保 DOM 完全渲染
                setTimeout(() => {{
                    window.scrollTo({{ top: safeScrollTop, behavior: 'smooth' }});

                    // 验证滚动是否成功
                    setTimeout(() => {{
                        const currentScroll = window.scrollY;
                        console.log('当前滚动位置:', currentScroll + 'px, 期望位置:', safeScrollTop + 'px');

                        // 如果滚动位置差异很大，尝试直接设置
                        if (Math.abs(currentScroll - safeScrollTop) > 100) {{
                            console.log('平滑滚动可能失败，尝试直接设置滚动位置');
                            window.scrollTo(0, safeScrollTop);
                        }}
                    }}, 100);
                }}, 300);

                console.log('已恢复阅读进度:', progress + '%');
            }} else {{
                console.log('进度为 0 或滚动位置为 0，不恢复阅读位置');
            }}
        }}
        
        // 保存设置到localStorage
        function saveSettings() {{
            localStorage.setItem('readerSettings', JSON.stringify(currentSettings));
        }}
        
        // 缩略图导航功能
        let isMinimapVisible = true;
        let minimapScale = 0.15;
        let minimapContent = null;
        let minimapViewport = null;
        let minimapContainer = null;
        let isDragging = false;
        let dragStartY = 0;
        let dragStartScrollTop = 0;
        let minimapUpdateTimer = null;
        let viewportUpdateTimer = null;
        let lastContentUpdate = 0;
        let isUpdating = false;

        // 防抖函数
        function debounce(func, wait) {{
            let timeout;
            return function executedFunction(...args) {{
                const later = () => {{
                    clearTimeout(timeout);
                    func(...args);
                }};
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            }};
        }}

        // 节流函数
        function throttle(func, limit) {{
            let inThrottle;
            return function() {{
                const args = arguments;
                const context = this;
                if (!inThrottle) {{
                    func.apply(context, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }}
            }}
        }}

        // 初始化缩略图导航
        function initMinimap() {{
            minimapContainer = document.getElementById('minimapContainer');
            minimapContent = document.getElementById('minimapContent');
            minimapViewport = document.getElementById('minimapViewport');
            
            if (!minimapContainer || !minimapContent || !minimapViewport) {{
                console.error('缩略图导航元素未找到');
                return;
            }}

            // 设置初始状态
            const savedState = localStorage.getItem('minimapVisible');
            const toolbarBtn = document.getElementById('minimapToolbarBtn');
            
            if (savedState === 'false') {{
                isMinimapVisible = false;
                minimapContainer.classList.add('hidden');
                document.getElementById('minimapToggle').classList.remove('active');
                if (toolbarBtn) {{
                    toolbarBtn.classList.remove('active');
                    toolbarBtn.textContent = '缩略图';
                }}
            }} else {{
                document.getElementById('minimapToggle').classList.add('active');
                if (toolbarBtn) {{
                    toolbarBtn.classList.add('active');
                    toolbarBtn.textContent = '隐藏缩略图';
                }}
            }}

            // 使用节流的滚动事件监听
            window.addEventListener('scroll', throttle(updateMinimapViewport, 50));
            
            // 使用防抖的窗口大小变化监听
            window.addEventListener('resize', debounce(updateMinimap, 300));
            
            // 只监听内容区域的变化，而不是整个文档
            const content = document.getElementById('content');
            if (content) {{
                const observer = new MutationObserver(debounce(() => {{
                    const now = Date.now();
                    // 限制更新频率，至少间隔1秒
                    if (now - lastContentUpdate > 1000 && !isUpdating) {{
                        lastContentUpdate = now;
                        updateMinimap();
                    }}
                }}, 500));
                
                observer.observe(content, {{
                    childList: true,
                    subtree: false,  // 不监听子树，减少事件
                    attributes: false,  // 不监听属性变化
                    characterData: false  // 不监听文本变化
                }});
            }}

            // 添加拖拽功能
            minimapContainer.addEventListener('mousedown', startMinimapDrag);
            document.addEventListener('mousemove', handleMinimapDrag);
            document.addEventListener('mouseup', endMinimapDrag);

            // 初始化缩略图
            setTimeout(updateMinimap, 1000);
        }}

        // 更新缩略图内容
        function updateMinimap() {{
            if (!minimapContent || !minimapContainer || isUpdating) return;

            const content = document.getElementById('content');
            if (!content) return;

            isUpdating = true;
            
            try {{
                // 限制内容长度，避免内存问题
                const contentText = content.textContent || '';
                if (contentText.length > 100000) {{
                    console.warn('内容过长，缩略图功能可能受到影响');
                    minimapContent.innerHTML = '<div class="minimap-content-inner"><div style="color: #666; font-size: 10px; padding: 10px;">内容过长，缩略图已禁用</div></div>';
                    return;
                }}

                // 克隆内容到缩略图
                const clonedContent = content.cloneNode(false);  // 只克隆节点，不克隆子节点
                
                // 清除之前的缩略图内容
                minimapContent.innerHTML = '';
                
                // 重新添加视口元素
                const viewport = document.createElement('div');
                viewport.className = 'minimap-viewport';
                viewport.id = 'minimapViewport';
                minimapContent.appendChild(viewport);
                minimapViewport = viewport;

                // 创建内容容器
                const contentContainer = document.createElement('div');
                contentContainer.className = 'minimap-content-inner';

                // 创建简化的内容表示
                const simplifiedContent = document.createElement('div');
                simplifiedContent.style.width = '800px';
                simplifiedContent.style.transform = 'scale(0.15)';
                simplifiedContent.style.transformOrigin = 'top left';
                simplifiedContent.style.pointerEvents = 'none';
                simplifiedContent.style.opacity = '0.9';
                simplifiedContent.style.fontSize = '2px';
                simplifiedContent.style.lineHeight = '1.2';
                simplifiedContent.style.color = '#333';
                simplifiedContent.style.background = 'rgba(255, 255, 255, 0.8)';
                simplifiedContent.style.borderRadius = '2px';

                // 只复制主要结构（标题）
                const headers = content.querySelectorAll('h1, h2, h3');
                headers.forEach(header => {{
                    const headerClone = document.createElement('div');
                    const fontSize = header.tagName === 'H1' ? '3' : header.tagName === 'H2' ? '2.5' : '2';
                    headerClone.style.margin = '2px 0';
                    headerClone.style.fontSize = fontSize + 'px';
                    headerClone.style.fontWeight = 'bold';
                    headerClone.style.color = 'inherit';
                    headerClone.textContent = header.textContent.substring(0, 50) + (header.textContent.length > 50 ? '...' : '');
                    simplifiedContent.appendChild(headerClone);
                }});

                // 添加内容块指示器
                const paragraphs = content.querySelectorAll('p');
                const totalParagraphs = Math.min(paragraphs.length, 20);  // 限制段落数量
                for (let i = 0; i < totalParagraphs; i += 5) {{
                    const block = document.createElement('div');
                    block.style.height = '2px';
                    block.style.background = 'rgba(128, 128, 128, 0.3)';
                    block.style.margin = '1px 0';
                    simplifiedContent.appendChild(block);
                }}

                contentContainer.appendChild(simplifiedContent);
                minimapContent.appendChild(contentContainer);

                // 添加章节标记
                addMinimapChapterMarkers(simplifiedContent);
                
                // 更新视口位置
                updateMinimapViewport();
            }} catch (error) {{
                console.error('更新缩略图时出错:', error);
                minimapContent.innerHTML = '<div style="color: red; font-size: 10px; padding: 10px;">缩略图更新失败</div>';
            }} finally {{
                isUpdating = false;
            }}
        }}

        // 添加章节标记
        function addMinimapChapterMarkers(clonedContent) {{
            const headers = clonedContent.querySelectorAll('h1, h2, h3');
            const contentContainer = document.querySelector('.minimap-content-inner');
            
            headers.forEach(header => {{
                const marker = document.createElement('div');
                marker.className = 'minimap-chapter-marker';
                marker.style.position = 'absolute';
                marker.style.left = '0';
                marker.style.width = '100%';
                marker.style.height = '3px';
                marker.style.background = '#ff8c00';
                marker.style.top = (header.offsetTop * 0.15) + 8 + 'px';
                marker.style.pointerEvents = 'none';
                marker.style.zIndex = '1';
                if (contentContainer) {{
                    contentContainer.appendChild(marker);
                }}
            }});
        }}

        // 更新视口位置
        function updateMinimapViewport() {{
            if (!minimapViewport || !minimapContent || isDragging) return;

            try {{
                const scrollTop = window.scrollY;
                const documentHeight = document.documentElement.scrollHeight;
                const viewportHeight = window.innerHeight;
                
                // 避免除零错误
                if (documentHeight <= viewportHeight) {{
                    // 如果文档高度小于视口，显示整个文档
                    minimapViewport.style.top = '0px';
                    minimapViewport.style.height = '100%';
                    return;
                }}
                
                // 计算视口在文档中的位置比例
                const scrollProgress = scrollTop / (documentHeight - viewportHeight);
                const viewportHeightRatio = viewportHeight / documentHeight;
                
                // 获取缩略图内容的实际高度
                const contentElement = document.getElementById('content');
                const actualContentHeight = contentElement ? contentElement.offsetHeight : documentHeight;
                
                // 缩略图显示区域的高度（容器高度减去内边距）
                const minimapDisplayHeight = minimapContainer.offsetHeight - 16;
                
                // 计算内容在缩略图中的显示高度
                const scaledContentHeight = Math.min(actualContentHeight * minimapScale, minimapDisplayHeight);
                
                // 调整缩放比例，使视口更加明显
                const adjustedScale = 0.15; // 稍微增大缩放比例
                const adjustedHeight = actualContentHeight * adjustedScale;
                
                // 计算视口在缩略图中的位置（使用调整后的高度）
                const availableHeight = Math.min(adjustedHeight, minimapDisplayHeight);
                const viewportTop = scrollProgress * (availableHeight - viewportHeightRatio * availableHeight);
                const viewportHeightPx = Math.max(30, viewportHeightRatio * availableHeight); // 增加最小高度
                
                // 确保视口不超出缩略图范围
                const maxTop = availableHeight - viewportHeightPx;
                const finalTop = Math.max(0, Math.min(viewportTop, maxTop));
                
                // 批量更新样式，减少重排
                minimapViewport.style.top = finalTop + 'px';
                minimapViewport.style.height = viewportHeightPx + 'px';
                minimapViewport.style.background = 'rgba(100, 149, 237, 0.3)';
                minimapViewport.style.border = '3px solid rgba(100, 149, 237, 1)';
                minimapViewport.style.boxShadow = '0 0 8px rgba(100, 149, 237, 0.8)';
                minimapViewport.style.minHeight = '30px';
                minimapViewport.style.borderRadius = '2px';
                
                // 添加调试信息
                if (window.console && window.console.debug) {{
                    console.debug('视口更新:', {{
                        scrollProgress: (scrollProgress * 100).toFixed(1) + '%',
                        viewportHeightRatio: (viewportHeightRatio * 100).toFixed(1) + '%',
                        finalTop: finalTop.toFixed(1) + 'px',
                        viewportHeightPx: viewportHeightPx.toFixed(1) + 'px'
                    }});
                }}
            }} catch (error) {{
                console.error('更新视口位置时出错:', error);
            }}
        }}

        // 切换缩略图显示
        function toggleMinimap() {{
            isMinimapVisible = !isMinimapVisible;
            const toggle = document.getElementById('minimapToggle');
            const toolbarBtn = document.getElementById('minimapToolbarBtn');
            
            if (isMinimapVisible) {{
                minimapContainer.classList.remove('hidden');
                toggle.classList.add('active');
                if (toolbarBtn) {{
                    toolbarBtn.classList.add('active');
                    toolbarBtn.textContent = '隐藏缩略图';
                }}
                updateMinimap();
            }} else {{
                minimapContainer.classList.add('hidden');
                toggle.classList.remove('active');
                if (toolbarBtn) {{
                    toolbarBtn.classList.remove('active');
                    toolbarBtn.textContent = '缩略图';
                }}
            }}
            
            localStorage.setItem('minimapVisible', isMinimapVisible.toString());
        }}

        // 老板键模式
        let isBossMode = false;

        function initBossMode() {{
            // 获取原始标题
            const titleEl = document.getElementById('pageTitle');
            if (titleEl) {{
                originalTitle = titleEl.getAttribute('data-original-title') || document.title;
            }}
            
            // 监听页面可见性变化
            document.addEventListener('visibilitychange', function() {{
                handleVisibilityChange();
            }});

            // 监听窗口焦点变化（补充监听，确保在标签切换时也能触发）
            window.addEventListener('focus', function() {{
                handleVisibilityChange();
            }});
            
            window.addEventListener('blur', function() {{
                handleVisibilityChange();
            }});

            // 监听百度搜索框的回车键
            const searchInput = document.getElementById('baiduSearchInput');
            if (searchInput) {{
                searchInput.addEventListener('keypress', function(e) {{
                    if (e.key === 'Enter') {{
                        performBaiduSearch();
                    }}
                }});
            }}
        }}

        function handleVisibilityChange() {{
            // 检查页面是否隐藏
            if (document.hidden || !document.hasFocus()) {{
                // 页面不可见或失去焦点时，修改标题
                document.title = '百度一下,你就知道';
            }} else {{
                // 页面可见且有焦点时，恢复原始标题
                if (!isBossMode) {{
                    document.title = originalTitle;
                }}
            }}
        }}

        function toggleBossMode() {{
            isBossMode = !isBossMode;
            const bossModeDiv = document.getElementById('bossModeBaidu');
            const body = document.body;
            
            if (isBossMode) {{
                // 进入老板键模式
                bossModeDiv.style.display = 'block';
                document.title = '百度一下,你就知道';
                // 隐藏页面滚动
                body.style.overflow = 'hidden';
            }} else {{
                // 退出老板键模式
                bossModeDiv.style.display = 'none';
                document.title = originalTitle;
                body.style.overflow = '';
            }}
        }}

        function performBaiduSearch() {{
            const searchInput = document.getElementById('baiduSearchInput');
            if (!searchInput) return;
            
            const keyword = searchInput.value.trim();
            if (keyword) {{
                // 在新标签页打开百度搜索
                const searchUrl = 'https://www.baidu.com/s?ie=utf-8&tn=baidu&wd=' + encodeURIComponent(keyword);
                window.open(searchUrl, '_blank');
            }}
        }}

        // 开始拖拽
        function startMinimapDrag(e) {{
            if (e.target === minimapViewport) return; // 不允许直接拖拽视口
            
            isDragging = true;
            dragStartY = e.clientY;
            dragStartScrollTop = window.scrollY;
            
            // 禁用过渡动画，提高响应性
            if (minimapViewport) {{
                minimapViewport.style.transition = 'none';
            }}
            
            e.preventDefault();
        }}

        // 处理拖拽
        function handleMinimapDrag(e) {{
            if (!isDragging) return;
            
            try {{
                const deltaY = e.clientY - dragStartY;
                const documentHeight = document.documentElement.scrollHeight;
                const viewportHeight = window.innerHeight;
                const scrollableHeight = documentHeight - viewportHeight;
                
                // 避免除零错误
                if (scrollableHeight <= 0) return;
                
                // 计算新的滚动位置
                const scrollRatio = deltaY / (minimapContainer.offsetHeight * minimapScale);
                const newScrollTop = dragStartScrollTop + (scrollRatio * scrollableHeight);
                
                // 限制滚动范围
                const clampedScrollTop = Math.max(0, Math.min(newScrollTop, scrollableHeight));
                
                // 使用 requestAnimationFrame 优化性能
                requestAnimationFrame(() => {{
                    window.scrollTo(0, clampedScrollTop);
                }});
            }} catch (error) {{
                console.error('拖拽处理时出错:', error);
            }}
        }}

        // 结束拖拽
        function endMinimapDrag() {{
            isDragging = false;
            
            // 恢复过渡动画
            if (minimapViewport) {{
                minimapViewport.style.transition = 'top 0.1s ease';
            }}
        }}

        // 加载设置
        function loadSettings() {{
            const saved = localStorage.getItem('readerSettings');
            if (saved) {{
                try {{
                    currentSettings = JSON.parse(saved);
                    applySettings(currentSettings);
                }} catch (e) {{
                    console.error('加载设置失败:', e);
                    // 使用默认设置
                    currentSettings = {str(BrowserReader.THEMES['light'])};
                    applySettings(currentSettings);
                }}
            }} else {{
                // 首次加载，检测系统主题
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (prefersDark) {{
                    currentSettings = themes['dark'];
                    applySettings(currentSettings);
                }} else {{
                    currentSettings = themes['light'];
                    applySettings(currentSettings);
                }}
            }}
            
            // 更新 toolbar-toggle-container 的位置
            setTimeout(updateToolbarTogglePosition, 100);
            
            // 恢复翻页模式状态
            const savedPaginationMode = localStorage.getItem('paginationMode');
            if (savedPaginationMode === 'true') {{
                console.log('恢复翻页模式状态');
                // 延迟切换到翻页模式，确保DOM完全加载
                setTimeout(() => {{
                    togglePaginationMode();
                }}, 500);
            }}
        }}
        
        
        
        // 获取主题名称
        function getThemeName(settings) {{
            for (const [name, theme] of Object.entries(themes)) {{
                if (theme.background === settings.background) {{
                    return name;
                }}
            }}
            return 'light';
        }}
        
        // 键盘快捷键
        document.addEventListener('keydown', function(e) {{
            // 防止输入框触发
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

            switch(e.key) {{
                case 'ArrowUp':
                    if (isPaginationMode) {{
                        previousPage();
                    }} else {{
                        window.scrollBy({{ top: -window.innerHeight * 0.8, behavior: 'smooth' }});
                    }}
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                    if (isPaginationMode) {{
                        nextPage();
                    }} else {{
                        window.scrollBy({{ top: window.innerHeight * 0.8, behavior: 'smooth' }});
                    }}
                    e.preventDefault();
                    break;
                case 'PageUp':
                    if (isPaginationMode) {{
                        previousPage();
                    }} else {{
                        window.scrollBy({{ top: -window.innerHeight * 0.9, behavior: 'smooth' }});
                    }}
                    e.preventDefault();
                    break;
                case 'PageDown':
                    if (isPaginationMode) {{
                        nextPage();
                    }} else {{
                        window.scrollBy({{ top: window.innerHeight * 0.9, behavior: 'smooth' }});
                    }}
                    e.preventDefault();
                    break;
                case 'Home':
                    scrollToTop();
                    e.preventDefault();
                    break;
                case 'End':
                    scrollToBottom();
                    e.preventDefault();
                    break;
                case '+':
                case '=':
                    changeFontSize(2);
                    e.preventDefault();
                    break;
                case '-':
                case '_':
                    changeFontSize(-2);
                    e.preventDefault();
                    break;
                case 'c':
                case 'C':
                    toggleTOC();
                    e.preventDefault();
                    break;
                case 's':
                case 'S':
                    toggleSearch();
                    e.preventDefault();
                    break;
                case 'b':
                case 'B':
                    toggleBookmark();
                    e.preventDefault();
                    break;
                case 'f':
                case 'F':
                    if (e.shiftKey || e.key === 'F') {{
                        toggleFocusMode();
                    }} else {{
                        toggleFullscreen();
                    }}
                    e.preventDefault();
                    break;
                case 'a':
                case 'A':
                    toggleAutoScroll();
                    e.preventDefault();
                    break;
                case ' ':
                    // 空格键朗读选中的文本
                    const selection = window.getSelection().toString();
                    if (selection) {{
                        toggleSpeech();
                        e.preventDefault();
                    }}
                    break;
                case 'h':
                case 'H':
                    toggleKeyboardHint();
                    e.preventDefault();
                    break;
                case 'g':
                case 'G':
                    if (e.ctrlKey || e.metaKey) {{
                        // Ctrl+G 或 Cmd+G 激活位置跳转
                        togglePositionJump();
                        e.preventDefault();
                    }} else {{
                        toggleFontSettings();
                        e.preventDefault();
                    }}
                    break;
                case 'n':
                case 'N':
                    toggleNotesMode();
                    e.preventDefault();
                    break;
                case 'p':
                case 'P':
                    togglePaginationMode();
                    e.preventDefault();
                    break;
                case 'm':
                case 'M':
                    toggleMinimap();
                    e.preventDefault();
                    break;
                case '/':
                    toggleBossMode();
                    e.preventDefault();
                    break;
                case 'Escape':
                    if (document.fullscreenElement) {{
                        document.exitFullscreen();
                    }}
                    // 退出专注模式
                    if (isFocusMode) {{
                        toggleFocusMode();
                    }}
                    // 停止自动滚动
                    if (autoScrollInterval) {{
                        clearInterval(autoScrollInterval);
                        autoScrollInterval = null;
                        const btn = document.querySelector('button[onclick="toggleAutoScroll()"]');
                        if (btn) btn.classList.remove('active');
                        showNotification('自动滚动已停止');
                    }}
                    // 关闭搜索框
                    const searchContainer = document.getElementById('searchContainer');
                    if (searchContainer && searchContainer.classList.contains('show')) {{
                        toggleSearch();
                    }}
                    // 关闭目录
                    const toc = document.getElementById('tocContainer');
                    if (toc && toc.classList.contains('show')) {{
                        toggleTOC();
                    }}
                    // 关闭字体设置面板
                    const fontPanel = document.getElementById('fontSettingsPanel');
                    if (fontPanel && fontPanel.style.display !== 'none') {{
                        toggleFontSettings();
                    }}
                    // 关闭笔记面板
                    const notesPanel = document.getElementById('notesPanel');
                    if (notesPanel && notesPanel.style.display !== 'none') {{
                        closeNotesPanel();
                    }}
                    // 退出高亮模式
                    if (isHighlightMode) {{
                        toggleHighlightMode();
                    }}
                    break;
            }}
        }});

        // 切换全屏
        function toggleFullscreen() {{
            if (!document.fullscreenElement) {{
                document.documentElement.requestFullscreen();
            }} else {{
                document.exitFullscreen();
            }}
        }}

        // 切换快捷键提示显示
        function toggleKeyboardHint() {{
            const hint = document.getElementById('keyboardHint');
            if (hint) {{
                hint.style.display = hint.style.display === 'none' ? 'block' : 'none';
            }}
        }}

        // 生成章节目录
        function generateTOC() {{
            const content = document.getElementById('content');
            const tocList = document.getElementById('tocList');

            if (!content || !tocList) return;

            tocList.innerHTML = '';

            // 获取所有标题
            const headers = content.querySelectorAll('h1, h2, h3');

            console.log('正在生成章节目录，找到的标题数量:', headers.length);
            headers.forEach((header, index) => {{
                const titleNumber = index + 1;
                const titleText = header.tagName + ' ' + header.textContent.substring(0, 50);
                console.log('标题', titleNumber + ':', titleText);
            }});

            if (headers.length === 0) {{
                tocList.innerHTML = '<li class="toc-item">' + (typeof t === 'function' ? t('browser_reader.no_chapters') : '暂无章节目录') + '</li>';
                console.log('未找到任何标题，请在文件内容中使用章节标题格式，如：');
                console.log('  - 第X章、第X节、第X回');
                console.log('  - Chapter X');
                console.log('  - Markdown格式：# 标题');
                console.log('  - 一、二、三、');
                return;
            }}

            // 为每个标题添加唯一ID
            headers.forEach((header, index) => {{
                if (!header.id) {{
                    const sectionId = 'section-' + index;
                    header.id = sectionId;
                }}
            }});

            // 生成目录项，添加章节序号
            let h1Count = 0;
            let h2Count = 0;

            headers.forEach((header, index) => {{
                const li = document.createElement('li');
                li.className = 'toc-item ' + header.tagName.toLowerCase();

                let chapterNumber = '';
                if (header.tagName.toLowerCase() === 'h1') {{
                    h1Count++;
                    h2Count = 0;
                    chapterNumber = h1Count + '. ';
                }} else if (header.tagName.toLowerCase() === 'h2') {{
                    h2Count++;
                    chapterNumber = h1Count + '.' + h2Count + ' ';
                }}

                // 截断过长的标题（超过30个字符）
                let titleText = header.textContent;
                if (titleText.length > 30) {{
                    titleText = titleText.substring(0, 30) + '...';
                }}

                li.textContent = chapterNumber + titleText;
                li.setAttribute('data-full-title', header.textContent); // 保存完整标题
                li.onclick = () => {{
                    // 滚动到对应位置
                    header.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    // 高亮当前章节
                    document.querySelectorAll('.toc-item').forEach(item => item.classList.remove('active'));
                    li.classList.add('active');

                    // 关闭目录面板（可选）
                    // toggleTOC();
                }};
                tocList.appendChild(li);
            }});

            console.log('已生成章节目录，共', headers.length, '个章节');

            // 在目录面板添加搜索框
            addTOCSearch();
        }}

        // 为目录添加搜索功能
        function addTOCSearch() {{
            const tocContainer = document.getElementById('tocContainer');
            if (!tocContainer || tocContainer.querySelector('.toc-search')) return;

            // 在标题后面添加搜索框
            const tocHeader = tocContainer.querySelector('.toc-header');
            if (!tocHeader) return;

            const searchDiv = document.createElement('div');
            searchDiv.className = 'toc-search';
            searchDiv.style.cssText = 'padding: 8px 16px; border-bottom: 1px solid rgba(128, 128, 128, 0.3);';

            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.placeholder = '搜索章节...';
            searchInput.style.cssText = 'width: 100%; padding: 6px 10px; border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 4px; background: rgba(128, 128, 128, 0.05); color: inherit; font-size: 14px; box-sizing: border-box;';

            searchInput.addEventListener('input', function(e) {{
                const searchText = e.target.value.toLowerCase();
                const tocItems = document.querySelectorAll('.toc-item');

                tocItems.forEach(item => {{
                    const fullTitle = item.getAttribute('data-full-title') || item.textContent;
                    if (fullTitle.toLowerCase().includes(searchText)) {{
                        item.style.display = 'block';
                    }} else {{
                        item.style.display = 'none';
                    }}
                }});
            }});

            searchDiv.appendChild(searchInput);
            tocContainer.insertBefore(searchDiv, tocContainer.querySelector('.toc-list'));
        }}

        // 切换目录显示
        function toggleTOC() {{
            const toc = document.getElementById('tocContainer');
            if (toc) {{
                toc.classList.toggle('show');
            }}
        }}

        // 监听滚动，高亮当前章节
        function highlightCurrentChapter() {{
            const headers = document.querySelectorAll('#content h1, #content h2, #content h3');
            const tocItems = document.querySelectorAll('.toc-item');

            if (headers.length === 0) return;

            let currentHeaderIndex = -1;
            const scrollPosition = window.scrollY + 100;

            for (let i = 0; i < headers.length; i++) {{
                const header = headers[i];
                if (header.offsetTop <= scrollPosition) {{
                    currentHeaderIndex = i;
                }} else {{
                    break;
                }}
            }}

            tocItems.forEach((item, index) => {{
                if (index === currentHeaderIndex) {{
                    item.classList.add('active');
                }} else {{
                    item.classList.remove('active');
                }}
            }});
        }}

        // 搜索功能
        let searchResults = [];
        let currentSearchIndex = 0;

        function toggleSearch() {{
            const searchContainer = document.getElementById('searchContainer');
            if (searchContainer) {{
                searchContainer.classList.toggle('show');
                if (searchContainer.classList.contains('show')) {{
                    document.getElementById('searchInput').focus();
                }}
            }}
        }}

        function handleSearchKeypress(event) {{
            if (event.key === 'Enter') {{
                searchText();
            }}
        }}

        function searchText() {{
            const searchQuery = document.getElementById('searchInput').value.trim();
            if (!searchQuery) return;

            const content = document.getElementById('content');
            if (!content) return;

            // 清除之前的搜索结果高亮
            clearSearchHighlights();

            // 查找所有文本节点
            const walker = document.createTreeWalker(
                content,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );

            const nodes = [];
            let node;
            while ((node = walker.nextNode())) {{
                if (node.textContent.toLowerCase().includes(searchQuery.toLowerCase())) {{
                    nodes.push(node);
                }}
            }}

            // 高亮搜索结果
            searchResults = [];
            const regex = new RegExp('(' + searchQuery + ')', 'gi');

            nodes.forEach((node, index) => {{
                const span = document.createElement('span');
                span.innerHTML = node.textContent.replace(regex, '<mark style="background: yellow; padding: 0 2px;">$1</mark>');
                node.parentNode.replaceChild(span, node);
                searchResults.push(span);
            }});

            document.getElementById('searchCount').textContent = '找到 ' + searchResults.length + ' 个结果';
            currentSearchIndex = 0;

            if (searchResults.length > 0) {{
                highlightSearchResult(0);
            }}
        }}

        function searchNext() {{
            if (searchResults.length === 0) return;

            // 清除当前高亮
            if (searchResults[currentSearchIndex]) {{
                searchResults[currentSearchIndex].querySelectorAll('mark').forEach(mark => {{
                    mark.style.background = 'yellow';
                }});
            }}

            // 移动到下一个结果
            currentSearchIndex = (currentSearchIndex + 1) % searchResults.length;
            highlightSearchResult(currentSearchIndex);
        }}

        function highlightSearchResult(index) {{
            const result = searchResults[index];
            if (!result) return;

            const marks = result.querySelectorAll('mark');
            marks.forEach(mark => {{
                mark.style.background = 'orange';
            }});

            // 滚动到搜索结果
            result.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}

        function clearSearchHighlights() {{
            const content = document.getElementById('content');
            if (!content) return;

            const marks = content.querySelectorAll('mark');
            marks.forEach(mark => {{
                const parent = mark.parentNode;
                parent.replaceChild(document.createTextNode(mark.textContent), mark);
                parent.normalize();
            }});
        }}

        // 书签功能
        function toggleBookmark() {{
            const bookmarkBtn = document.getElementById('bookmarkBtn');
            const scrollTop = window.scrollY;
            const progress = (scrollTop / (document.documentElement.scrollHeight - window.innerHeight)) * 100;

            if (bookmarkBtn.classList.contains('bookmarked')) {{
                // 移除书签
                bookmarkBtn.classList.remove('bookmarked');
                localStorage.removeItem('bookmark');
                console.log('书签已移除');
            }} else {{
                // 添加书签
                bookmarkBtn.classList.add('bookmarked');
                localStorage.setItem('bookmark', JSON.stringify({{
                    scrollTop: scrollTop,
                    progress: progress,
                    timestamp: Date.now()
                }}));
                console.log('书签已添加:', scrollTop, progress.toFixed(2) + '%');
            }}
        }}

        function loadBookmark() {{
            const bookmarkData = localStorage.getItem('bookmark');
            if (bookmarkData) {{
                try {{
                    const bookmark = JSON.parse(bookmarkData);
                    const bookmarkBtn = document.getElementById('bookmarkBtn');
                    if (bookmarkBtn) {{
                        bookmarkBtn.classList.add('bookmarked');
                    }}
                    console.log('已加载书签:', bookmark);
                }} catch (e) {{
                    console.error('加载书签失败:', e);
                }}
            }}
        }}

        function jumpToBookmark() {{
            const bookmarkData = localStorage.getItem('bookmark');
            if (bookmarkData) {{
                try {{
                    const bookmark = JSON.parse(bookmarkData);
                    window.scrollTo({{ top: bookmark.scrollTop, behavior: 'smooth' }});
                    console.log('已跳转到书签位置');
                }} catch (e) {{
                    console.error('跳转到书签失败:', e);
                }}
            }}
        }}

        // 阅读统计
        let readingTimer = null;

        function updateReadingStats() {{
            const elapsedTime = Math.floor((Date.now() - readingStartTime) / 1000);
            const minutes = Math.floor(elapsedTime / 60);
            const seconds = elapsedTime % 60;

            document.getElementById('readingTime').textContent =
                minutes + ':' + seconds.toString().padStart(2, '0');

            // 计算已读字数（基于滚动位置）
            const scrollTop = window.scrollY;
            const scrollHeight = document.documentElement.scrollHeight;
            const clientHeight = window.innerHeight;
            const progress = scrollTop / (scrollHeight - clientHeight);

            // 估算总字数
            const content = document.getElementById('content');
            if (content) {{
                const totalWords = content.textContent.replace(/\\s+/g, '').length;
                const readWords = Math.floor(totalWords * progress);
                document.getElementById('wordCount').textContent = readWords;
            }}
        }}
        
// 尝试分割元素
        function trySplitElement(element, remainingHeight, lineHeight) {{
            // 只对段落和文本元素进行分割
            const tagName = element.tagName.toLowerCase();
            if (tagName === 'p' || tagName === 'div' || tagName === 'span') {{
                const text = element.textContent.trim();
                if (text.length > 0) {{
                    return true; // 文本元素可以分割
                }}
            }}
            return false; // 其他元素不分割
        }}
        
        // 分割元素内容
        function splitElementContent(element, remainingHeight, lineHeight) {{
            const clone = element.cloneNode(true);
            document.body.appendChild(clone);
            clone.style.position = 'absolute';
            clone.style.visibility = 'hidden';
            clone.style.height = 'auto';
            
            const originalHeight = clone.offsetHeight;
            document.body.removeChild(clone);
            
            // 如果元素高度小于剩余高度，不需要分割
            if (originalHeight <= remainingHeight) {{
                return {{
                    firstPart: element,
                    secondPart: null
                }};
            }}
            
            // 计算可以显示的行数
            const availableLines = Math.floor(remainingHeight / lineHeight);
            if (availableLines <= 0) {{
                return {{
                    firstPart: null,
                    secondPart: element
                }};
            }}
            
            // 分割文本内容
            const text = element.textContent.trim();
            const words = text.split('');
            const wordsPerLine = Math.ceil(text.length / (originalHeight / lineHeight));
            const wordsToFit = availableLines * wordsPerLine;
            
            if (wordsToFit >= words.length) {{
                return {{
                    firstPart: element,
                    secondPart: null
                }};
            }}
            
            // 创建两个新元素
            const firstPart = element.cloneNode(false);
            const secondPart = element.cloneNode(false);
            
            // 分割文本
            const firstText = words.slice(0, wordsToFit).join('');
            const secondText = words.slice(wordsToFit).join('');
            
            firstPart.textContent = firstText;
            secondPart.textContent = secondText;
            
            return {{
                firstPart: firstPart,
                secondPart: secondPart
            }};
        }}
        
        // 智能内容分页函数 - 确保内容完整显示
        function paginateContent() {{
            const content = document.getElementById('content');
            const pageContainer = document.getElementById('paginationContainer');
            const pageContent = document.getElementById('pageContent');
            
            if (!content || !pageContainer || !pageContent) {{
                console.error('分页失败：缺少必要的DOM元素');
                return;
            }}
            
            // 确保容器有正确的尺寸
            if (pageContainer.offsetHeight === 0 || pageContainer.offsetWidth === 0) {{
                console.error('分页失败：容器尺寸为0');
                return;
            }}
            
            // 获取容器和样式信息
            const containerHeight = pageContainer.offsetHeight;
            const containerWidth = pageContainer.offsetWidth;
            const pageContentStyle = window.getComputedStyle(pageContent);
            const paddingTop = parseInt(pageContentStyle.paddingTop) || 40;
            const paddingBottom = parseInt(pageContentStyle.paddingBottom) || 40;
            const availableHeight = containerHeight - paddingTop - paddingBottom;
            
            console.log('=== 智能分页调试信息 ===');
            console.log('  容器尺寸:', containerWidth, 'x', containerHeight);
            console.log('  可用高度:', availableHeight);
            console.log('  内容元素总数:', content.children.length);
            
            // 验证容器尺寸
            if (containerWidth <= 0 || availableHeight <= 0) {{
                console.error('容器尺寸无效，无法进行分页');
                return;
            }}
            
            // 创建测试容器来测量元素高度
            const testContainer = document.createElement('div');
            const testWidth = containerWidth - 80;
            testContainer.style.position = 'absolute';
            testContainer.style.top = '-9999px';
            testContainer.style.left = '-9999px';
            testContainer.style.width = testWidth + 'px';
            testContainer.style.padding = paddingTop + 'px ' + paddingBottom + 'px';
            testContainer.style.fontFamily = pageContentStyle.fontFamily;
            testContainer.style.fontSize = pageContentStyle.fontSize;
            testContainer.style.lineHeight = pageContentStyle.lineHeight;
            testContainer.style.visibility = 'hidden';
            document.body.appendChild(testContainer);
            
            // 克隆内容并分析每个元素
            const contentClone = content.cloneNode(true);
            const elements = Array.from(contentClone.children);
            pages = [];
            
            let currentPage = document.createElement('div');
            currentPage.className = 'page';
            let currentHeight = 0;
            let currentPageText = '';
            
            elements.forEach((element, index) => {{
                // 测试当前元素的高度
                testContainer.innerHTML = '';
                const elementClone = element.cloneNode(true);
                testContainer.appendChild(elementClone);
                const elementHeight = testContainer.offsetHeight;
                
                // 获取元素文本（用于检查是否在句子中间）
                const elementText = element.textContent || '';
                
                const logMessage = '元素 ' + index + ': ' + element.tagName + ', 高度: ' + elementHeight + ', 文本长度: ' + elementText.length;
                console.log(logMessage);
                
                // 检查添加这个元素是否会超出页面高度
                if (currentHeight + elementHeight > availableHeight && currentPage.children.length > 0) {{
                    const exceedMessage = '  -> 高度超出 (' + (currentHeight + elementHeight) + ' > ' + availableHeight + ')，创建新页';
                    console.log(exceedMessage);
                    
                    // 保存当前页
                    pages.push(currentPage);
                    
                    // 创建新页
                    currentPage = document.createElement('div');
                    currentPage.className = 'page';
                    currentHeight = 0;
                    currentPageText = '';
                }}
                
                // 添加元素到当前页
                currentPage.appendChild(element.cloneNode(true));
                currentHeight += elementHeight;
                currentPageText += elementText;
                
                console.log('  -> 已添加，当前页高度: ' + currentHeight);
            }});
            
            // 添加最后一页
            if (currentPage.children.length > 0) {{
                pages.push(currentPage);
            }}
            
            // 清理测试容器
            document.body.removeChild(testContainer);
            
            // 更新总页数
            document.getElementById('totalPages').textContent = pages.length;
            
            console.log('分页完成，共 ' + pages.length + ' 页');
            
            // 注意：不再自动显示第一页，由调用者决定显示哪一页
        }}
        
        // 显示指定页面 - 确保内容完整显示
        function showPage(pageIndex, direction = 'next') {{
            if (pageIndex < 0 || pageIndex >= pages.length) return;
            
            const pageContent = document.getElementById('pageContent');
            if (!pageContent) return;
            
            currentPageIndex = pageIndex;
            
            // 更新页码显示和按钮状态
            document.getElementById('currentPage').textContent = pageIndex + 1;
            document.getElementById('pageJumpInput').value = pageIndex + 1;
            document.getElementById('pageJumpInput').max = pages.length;
            document.getElementById('prevPageBtn').disabled = pageIndex === 0;
            document.getElementById('nextPageBtn').disabled = pageIndex === pages.length - 1;
            
            // 计算并更新阅读进度
            updatePaginationProgress();
            
            // 确保页面内容完整
            const pageData = pages[pageIndex];
            if (!pageData) {{
                console.error('页面数据不存在:', pageIndex);
                return;
            }}
            
            console.log('显示页面 ' + (pageIndex + 1) + '/' + pages.length + '，包含 ' + pageData.children.length + ' 个元素');
            
            // 根据不同的翻页效果应用不同的动画
            if (pageEffect === 'none') {{
                // 无效果，直接更新内容
                pageContent.innerHTML = '';
                pageContent.appendChild(pageData.cloneNode(true));
            }} else if (pageEffect === 'realistic') {{
                // 仿真翻页效果
                applyRealisticFlipWithContent(pageContent, pageIndex, direction);
            }} else if (pageEffect === 'book') {{
                // 书页翻页效果
                applyBookFlipWithContent(pageContent, pageIndex, direction);
            }} else {{
                // 其他效果
                applyOtherEffectWithContent(pageContent, pageIndex, direction);
            }}
            
            // 延迟更新样式，确保内容已经加载
            setTimeout(() => {{
                updatePaginationStyles(currentSettings);
                // 验证内容是否完整显示
                const displayedContent = pageContent.querySelector('.page, .book-page');
                if (displayedContent) {{
                    console.log('页面内容验证: ' + displayedContent.children.length + ' 个元素已显示');
                }}
            }}, 100);
        }}
        
        // 应用仿真翻页效果并更新内容
        function applyRealisticFlipWithContent(element, pageIndex, direction) {{
            // 创建新内容容器
            const newContent = document.createElement('div');
            newContent.className = 'page-content realistic-flip';
            newContent.innerHTML = '';
            newContent.appendChild(pages[pageIndex].cloneNode(true));
            
            // 添加阴影效果
            const shadowLeft = document.createElement('div');
            shadowLeft.className = 'page-shadow page-shadow-left';
            
            const shadowRight = document.createElement('div');
            shadowRight.className = 'page-shadow page-shadow-right';
            
            newContent.appendChild(shadowLeft);
            newContent.appendChild(shadowRight);
            
            // 根据方向应用不同的翻页效果
            if (direction === 'next') {{
                newContent.classList.add('realistic-flip-left');
                shadowLeft.classList.add('active');
            }} else {{
                newContent.classList.add('realistic-flip-right');
                shadowRight.classList.add('active');
            }}
            
            // 替换内容
            element.parentNode.replaceChild(newContent, element);
            newContent.id = 'pageContent';
            
            // 动画结束后移除效果类
            setTimeout(() => {{
                newContent.className = 'page-content';
                // 移除阴影元素
                const shadows = newContent.querySelectorAll('.page-shadow');
                shadows.forEach(shadow => shadow.remove());
            }}, 800);
        }}
        
        // 应用书页翻页效果并更新内容
        function applyBookFlipWithContent(element, pageIndex, direction) {{
            // 使用DocumentFragment优化性能
            const fragment = document.createDocumentFragment();
            
            // 创建新内容容器
            const newContent = document.createElement('div');
            newContent.className = 'page-content book-flip';
            newContent.innerHTML = '';
            newContent.appendChild(pages[pageIndex].cloneNode(true));
            
            // 创建效果元素
            const effects = [];
            
            // 添加书页阴影效果
            const bookShadowNext = document.createElement('div');
            bookShadowNext.className = 'page-book-shadow page-book-shadow-next';
            effects.push(bookShadowNext);
            
            const bookShadowPrev = document.createElement('div');
            bookShadowPrev.className = 'page-book-shadow page-book-shadow-prev';
            effects.push(bookShadowPrev);
            
            // 添加页面弯曲效果
            const pageCurve = document.createElement('div');
            pageCurve.className = 'page-curve';
            effects.push(pageCurve);
            
            // 添加页面厚度效果
            const thicknessRight = document.createElement('div');
            thicknessRight.className = 'page-thickness page-thickness-right';
            effects.push(thicknessRight);
            
            const thicknessLeft = document.createElement('div');
            thicknessLeft.className = 'page-thickness page-thickness-left';
            effects.push(thicknessLeft);
            
            // 批量添加效果元素
            effects.forEach(effect => newContent.appendChild(effect));
            
            // 根据方向应用不同的翻页效果
            if (direction === 'next') {{
                requestAnimationFrame(() => {{
                    newContent.classList.add('book-flip-next');
                    bookShadowNext.classList.add('active');
                    pageCurve.classList.add('active');
                    thicknessRight.classList.add('active');
                    pageGloss.classList.add('active');
                    
                    // 添加动态阴影效果
                    setTimeout(() => {{
                        bookShadowNext.style.opacity = '0.8';
                    }}, 200);
                }});
            }} else {{
                requestAnimationFrame(() => {{
                    newContent.classList.add('book-flip-prev');
                    bookShadowPrev.classList.add('active');
                    pageCurve.classList.add('active');
                    thicknessLeft.classList.add('active');
                    pageGloss.classList.add('active');
                    
                    // 添加动态阴影效果
                    setTimeout(() => {{
                        bookShadowPrev.style.opacity = '0.8';
                    }}, 200);
                }});
            }}
            
            // 替换内容
            element.parentNode.replaceChild(newContent, element);
            newContent.id = 'pageContent';
            
            // 使用更精确的动画结束检测
            const handleAnimationEnd = () => {{
                newContent.className = 'page-content';
                // 移除所有效果元素
                const effectsToRemove = newContent.querySelectorAll('.page-book-shadow, .page-curve, .page-thickness');
                effectsToRemove.forEach(effect => effect.remove());
            }};
            
            // 使用setTimeout确保动画完成
            setTimeout(handleAnimationEnd, 800);
        }}
        
        // 应用其他翻页效果并更新内容
        function applyOtherEffectWithContent(element, pageIndex, direction) {{
            // 创建新内容容器
            const newContent = document.createElement('div');
            newContent.className = 'page-content';
            newContent.innerHTML = '';
            newContent.appendChild(pages[pageIndex].cloneNode(true));
            
            // 应用效果
            switch(pageEffect) {{
                case 'slide':
                    newContent.classList.add('slide-effect');
                    break;
                case 'fade':
                    newContent.classList.add('fade-effect');
                    break;
                case 'flip':
                    newContent.classList.add('flip-effect');
                    break;
            }}
            
            // 替换内容
            element.parentNode.replaceChild(newContent, element);
            newContent.id = 'pageContent';
            
            // 动画结束后移除效果类
            setTimeout(() => {{
                newContent.className = 'page-content';
            }}, 300);
        }}
        
        
        
        // 应用翻页效果
        function applyPageEffect(element, effect, direction = 'next') {{
            element.className = 'page-content';
            
            switch(effect) {{
                case 'slide':
                    element.classList.add('slide-effect');
                    break;
                case 'fade':
                    element.classList.add('fade-effect');
                    break;
                case 'flip':
                    element.classList.add('flip-effect');
                    break;
                case 'realistic':
                    applyRealisticFlipEffect(element, direction);
                    break;
                case 'book':
                    applyBookFlipEffect(element, direction);
                    break;
            }}
        }}
        
        // 应用简洁的3D书页翻页效果 (参考test.html)
        function applyBookFlipEffect(element, direction) {{
            // 创建书页容器
            const bookContainer = document.createElement('div');
            bookContainer.className = 'book-container';
            
            // 创建页面内容
            const pageContent = element.innerHTML;
            const pageStyles = window.getComputedStyle(element);
            
            // 创建正面页面
            const frontPage = document.createElement('div');
            frontPage.className = 'book-page front';
            frontPage.innerHTML = pageContent;
            frontPage.style.cssText = 
                'font-family: ' + pageStyles.fontFamily + ';' +
                'font-size: ' + pageStyles.fontSize + ';' +
                'line-height: ' + pageStyles.lineHeight + ';' +
                'color: ' + pageStyles.color + ';' +
                'background: ' + pageStyles.backgroundColor + ';';
            
            // 创建背面页面
            const backPage = document.createElement('div');
            backPage.className = 'book-page back';
            backPage.innerHTML = pageContent;
            backPage.style.cssText = frontPage.style.cssText;
            
            // 创建书页
            const sheet = document.createElement('div');
            sheet.className = 'page-content book-flip';
            if (direction === 'next') {{
                sheet.classList.add('book-flip-next');
            }} else {{
                sheet.classList.add('book-flip-prev');
            }}
            
            sheet.appendChild(frontPage);
            sheet.appendChild(backPage);
            bookContainer.appendChild(sheet);
            
            // 替换原元素
            element.parentNode.replaceChild(bookContainer, element);
            bookContainer.id = 'pageContent';
            
            // 动画结束后清理
            setTimeout(() => {{
                if (direction === 'next') {{
                    sheet.classList.remove('book-flip-next');
                }} else {{
                    sheet.classList.remove('book-flip-prev');
                }}
            }}, 1000);
        }}
        
        // 应用仿真翻页效果
        function applyRealisticFlipEffect(element, direction) {{
            element.classList.add('realistic-flip');
            
            // 添加阴影效果
            const shadowLeft = document.createElement('div');
            shadowLeft.className = 'page-shadow page-shadow-left';
            
            const shadowRight = document.createElement('div');
            shadowRight.className = 'page-shadow page-shadow-right';
            
            element.appendChild(shadowLeft);
            element.appendChild(shadowRight);
            
            // 根据方向应用不同的翻页效果
            if (direction === 'next') {{
                element.classList.add('realistic-flip-left');
                shadowLeft.classList.add('active');
            }} else {{
                element.classList.add('realistic-flip-right');
                shadowRight.classList.add('active');
            }}
            
            // 动画结束后移除阴影
            setTimeout(() => {{
                if (shadowLeft.parentNode) shadowLeft.remove();
                if (shadowRight.parentNode) shadowRight.remove();
            }}, 600);
        }}
        
        // 上一页
        function previousPage() {{
            if (currentPageIndex > 0) {{
                showPage(currentPageIndex - 1, 'prev');
            }}
        }}
        
        // 下一页
        function nextPage() {{
            if (currentPageIndex < pages.length - 1) {{
                showPage(currentPageIndex + 1, 'next');
            }}
        }}
        
        // 跳转到指定页
        function jumpToPage() {{
            const input = document.getElementById('pageJumpInput');
            const targetPage = parseInt(input.value) - 1;
            
            if (targetPage >= 0 && targetPage < pages.length) {{
                // 确定翻页方向
                const direction = targetPage > currentPageIndex ? 'next' : 'prev';
                showPage(targetPage, direction);
            }} else {{
                input.value = currentPageIndex + 1;
                showNotification('页码超出范围');
            }}
        }}
        
        // 执行分页和导航的辅助函数
        function performPaginationAndNavigation() {{
            // 获取当前滚动位置（在分页前获取）
            const scrollTop = window.scrollY;
            const documentHeight = document.documentElement.scrollHeight;
            const clientHeight = window.innerHeight;
            const scrollProgress = scrollTop / (documentHeight - clientHeight);
            
            // 分页
            paginateContent();
            
            // 根据当前滚动位置计算应该显示的页码
            if (scrollProgress > 0 && pages.length > 0) {{
                const targetPage = Math.min(Math.floor(scrollProgress * pages.length), pages.length - 1);
                console.log('根据滚动位置计算目标页码:', targetPage + 1, '/', pages.length, '进度:', (scrollProgress * 100).toFixed(1) + '%');
                showPage(targetPage);
            }} else {{
                showPage(0);
            }}
            
            // 更新翻页模式的样式
            updatePaginationStyles(currentSettings);
        }}
        
        // 切换翻页模式
        function togglePaginationMode() {{
            const toggle = document.getElementById('paginationModeToggle');
            const icon = document.getElementById('paginationModeIcon');
            const text = document.getElementById('paginationModeText');
            const content = document.getElementById('content');
            const paginationContainer = document.getElementById('paginationContainer');
            const paginationControls = document.getElementById('paginationControls');
            const toolbar = document.querySelector('.toolbar');
            
            isPaginationMode = !isPaginationMode;
            
            // 保存翻页模式状态到localStorage
            localStorage.setItem('paginationMode', isPaginationMode.toString());
            console.log('保存翻页模式状态:', isPaginationMode);
            
            if (isPaginationMode) {{
                // 进入翻页模式
                toggle.classList.add('active');
                icon.textContent = '📄';
                text.textContent = '滚动模式';
                
                // 隐藏原始内容，显示翻页容器
                content.style.display = 'none';
                paginationContainer.style.display = 'block';
                paginationControls.style.display = 'flex';
                
                // 显示进度条和进度信息
                const progressBar = document.querySelector('.progress-bar');
                const progressInfo = document.getElementById('progressInfo');
                if (progressBar) progressBar.style.display = 'block';
                if (progressInfo) progressInfo.style.display = 'block';
                
                // 延迟分页，确保翻页容器完全渲染
                setTimeout(() => {{
                    // 检查容器是否有有效尺寸
                    const containerHeight = paginationContainer.offsetHeight;
                    const containerWidth = paginationContainer.offsetWidth;
                    
                    console.log('翻页容器初始尺寸:', containerWidth, 'x', containerHeight);
                    
                    // 如果容器尺寸太小，说明还没有完全渲染，需要等待更长时间
                    if (containerHeight < 200) {{
                        console.log('容器高度不足，等待更长时间...');
                        setTimeout(() => {{
                            const newHeight = paginationContainer.offsetHeight;
                            const newWidth = paginationContainer.offsetWidth;
                            console.log('翻页容器最终尺寸:', newWidth, 'x', newHeight);
                            
                            performPaginationAndNavigation();
                        }}, 500);
                    }} else {{
                        performPaginationAndNavigation();
                    }}
                }}, 300); // 延迟300ms确保容器完全渲染
                
                // 隐藏滚动相关功能
                if (toolbar) {{
                    const scrollBtn = toolbar.querySelector('button[onclick*="AutoScroll"]');
                    if (scrollBtn) scrollBtn.style.display = 'none';
                }}
                
                showNotification('已进入翻页模式');
            }} else {{
                // 退出翻页模式
                toggle.classList.remove('active');
                icon.textContent = '📖';
                text.textContent = '翻页模式';
                
                // 显示原始内容，隐藏翻页容器
                content.style.display = 'block';
                paginationContainer.style.display = 'none';
                paginationControls.style.display = 'none';
                
                // 隐藏进度条和进度信息（如果是在专注模式下）
                if (isFocusMode) {{
                    const progressBar = document.querySelector('.progress-bar');
                    const progressInfo = document.getElementById('progressInfo');
                    if (progressBar) progressBar.style.display = 'none';
                    if (progressInfo) progressInfo.style.display = 'none';
                }}
                
                // 显示滚动相关功能
                if (toolbar) {{
                    const scrollBtn = toolbar.querySelector('button[onclick*="AutoScroll"]');
                    if (scrollBtn) scrollBtn.style.display = '';
                }}
                
                // 根据当前页码计算滚动位置
                if (pages.length > 0 && currentPageIndex > 0) {{
                    const pageProgress = currentPageIndex / pages.length;
                    const documentHeight = document.documentElement.scrollHeight;
                    const clientHeight = window.innerHeight;
                    const scrollableHeight = documentHeight - clientHeight;
                    const targetScrollTop = Math.round(pageProgress * scrollableHeight);
                    
                    console.log('根据页码计算滚动位置:', targetScrollTop + 'px', '页码:', currentPageIndex + 1, '/', pages.length, '进度:', (pageProgress * 100).toFixed(1) + '%');
                    
                    // 延迟滚动，确保DOM完全渲染
                    setTimeout(() => {{
                        window.scrollTo({{ top: targetScrollTop, behavior: 'smooth' }});
                    }}, 100);
                }}
                
                // 停止自动翻页
                if (autoPageTurnTimer) {{
                    clearInterval(autoPageTurnTimer);
                    autoPageTurnTimer = null;
                }}
                
                showNotification('已退出翻页模式');
            }}
        }}
        
        // 切换翻页设置面板
        function togglePaginationSettings() {{
            const panel = document.getElementById('paginationSettings');
            panel.classList.toggle('show');
        }}
        
        // 改变翻页效果
        function changePageEffect(effect) {{
            pageEffect = effect;
            localStorage.setItem('pageEffect', effect);
            showNotification('翻页效果已更改');
        }}
        
        // 改变自动翻页
        function changeAutoPageTurn(interval) {{
            autoPageTurnInterval = parseInt(interval);
            
            // 清除现有定时器
            if (autoPageTurnTimer) {{
                clearInterval(autoPageTurnTimer);
                autoPageTurnTimer = null;
            }}
            
            // 设置新的定时器
            if (autoPageTurnInterval > 0 && isPaginationMode) {{
                autoPageTurnTimer = setInterval(() => {{
                    if (currentPageIndex < pages.length - 1) {{
                        nextPage();
                    }} else {{
                        // 到达最后一页，停止自动翻页
                        clearInterval(autoPageTurnTimer);
                        autoPageTurnTimer = null;
                        showNotification('已到达最后一页，自动翻页已停止');
                    }}
                }}, autoPageTurnInterval * 1000);
                
                showNotification('自动翻页已开启，每' + autoPageTurnInterval + '秒翻页');
            }} else {{
                showNotification('自动翻页已关闭');
            }}
            
            localStorage.setItem('autoPageTurnInterval', interval);
        }}
        
        // 重置翻页设置
        function resetPaginationSettings() {{
            document.getElementById('pageEffectSelect').value = 'none';
            document.getElementById('autoPageTurnSelect').value = 'off';
            
            changePageEffect('none');
            changeAutoPageTurn(0);
            
            showNotification('翻页设置已重置');
        }}
        
        // 监听滚动事件，更新进度和当前章节
        window.addEventListener('scroll', () => {{
            if (!isPaginationMode) {{
                updateProgress();
                highlightCurrentChapter();
            }}
        }});
        
        // 监听窗口大小改变，重新计算分页
        window.addEventListener('resize', () => {{
            if (isPaginationMode) {{
                paginateContent();
            }}
            // 更新 toolbar-toggle-container 的位置
            updateToolbarTogglePosition();
        }});
        
        // 页面加载时恢复设置和进度
        window.onload = function() {{
            loadSettings();

            console.log('页面加载完成，开始初始化');
            console.log('文档高度:', document.documentElement.scrollHeight, '视口高度:', window.innerHeight);

            // 初始化缩略图导航
            setTimeout(() => {{
                initMinimap();
            }}, 300);

            // 生成章节目录
            setTimeout(() => {{
                generateTOC();
            }}, 500);

            // 加载书签状态
            loadBookmark();
            
            // 初始化语音功能
            initSpeech();
            
            // 初始化进度同步设置
            updateProgressSyncUI();
            
            // 3秒后自动隐藏帮助看板和工具栏
            setTimeout(() => {{
                // 隐藏帮助看板
                toggleKeyboardHint()
                
                // 隐藏工具栏
                toggleToolbar();
            }}, 3000);
            
            // 初始化 toolbar-toggle-container 的位置
            updateToolbarTogglePosition();

            // 初始化字体设置状态
            if (currentSettings['font_weight'] === 'bold') {{
                document.getElementById('boldBtn').classList.add('active');
            }}
            if (currentSettings['font_style'] === 'italic') {{
                document.getElementById('italicBtn').classList.add('active');
            }}
            if (currentSettings['text_decoration'] === 'underline') {{
                document.getElementById('underlineBtn').classList.add('active');
            }}
            
            // 初始化夜间模式状态
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            // 注意：不要在这里自动切换主题，因为loadSettings()已经处理了主题加载
            // 只有在没有保存设置的情况下才使用系统主题偏好
            if (!localStorage.getItem('readerSettings') && prefersDark && !isNightMode) {{
                // 检查当前设置是否已经是深色主题，如果不是才切换
                if (currentSettings.background !== themes['dark'].background) {{
                    toggleNightMode();
                }}
            }}
            
            // 加载翻页设置
            const savedPageEffect = localStorage.getItem('pageEffect') || 'none';
            const savedAutoPageTurn = localStorage.getItem('autoPageTurnInterval') || '0';
            
            document.getElementById('pageEffectSelect').value = savedPageEffect;
            document.getElementById('autoPageTurnSelect').value = savedAutoPageTurn;
            
            pageEffect = savedPageEffect;
            autoPageTurnInterval = parseInt(savedAutoPageTurn);

            // 延迟加载进度，等待内容完全渲染
            setTimeout(() => {{
                console.log('延迟加载进度开始，文档高度:', document.documentElement.scrollHeight);
                
                // 检查是否需要恢复翻页模式
                const savedPaginationMode = localStorage.getItem('paginationMode');
                
                if (savedPaginationMode === 'true') {{
                    // 先切换到翻页模式，然后加载进度
                    setTimeout(() => {{
                        if (isPaginationMode) {{
                            // 确保页面已经分页完成后再加载进度
                            if (pages && pages.length > 0) {{
                                // 翻页模式下，从后端加载进度并跳转到对应页面
                                loadPaginationProgress();
                            }} else {{
                                // 如果页面还未分页，等待分页完成后再加载进度
                                setTimeout(() => {{
                                    if (pages && pages.length > 0) {{
                                        loadPaginationProgress();
                                    }} else {{
                                        console.log('页面分页失败，使用滚动模式加载进度');
                                        loadProgress();
                                    }}
                                }}, 1000);
                            }}
                        }} else {{
                            console.log('翻页模式未正确激活，使用滚动模式加载进度');
                            loadProgress();
                        }}
                    }}, 500);
                }} else {{
                    // 滚动模式下，正常加载进度
                    loadBookProgress();
                }}

                // 延迟取消冷却标记,允许正常自动保存
                setTimeout(() => {{
                    isPageLoading = false;
                    console.log('页面加载冷却结束,允许正常自动保存');
                }}, pageLoadCooldown);
            }}, 1000);

            // 启动阅读统计定时器
            readingTimer = setInterval(updateReadingStats, 1000);
            
            // 启动增强阅读统计定时器
            setInterval(updateEnhancedReadingStats, 5000);
        }};
        
        // 进度同步相关函数
        function toggleProgressSync() {{
            const panel = document.getElementById('progressSyncPanel');
            if (panel.style.display === 'none') {{
                panel.style.display = 'block';
                updateProgressSyncUI();
            }} else {{
                panel.style.display = 'none';
            }}
        }}
        
        function toggleProgressSyncEnabled() {{
            progressSyncEnabled = !progressSyncEnabled;
            localStorage.setItem('progressSyncEnabled', progressSyncEnabled.toString());
            updateProgressSyncUI();
            showNotification(progressSyncEnabled ? '已启用进度同步' : '已禁用进度同步');
        }}
        
        function updateProgressSyncUI() {{
            // 确保变量已初始化
            if (typeof progressSyncEnabled === 'undefined') {{
                progressSyncEnabled = localStorage.getItem('progressSyncEnabled') === 'true';
            }}
            if (typeof isBackendOnline === 'undefined') {{
                isBackendOnline = SAVE_PROGRESS_URL ? true : false;
            }}
            if (typeof syncInterval === 'undefined') {{
                syncInterval = parseInt(localStorage.getItem('syncInterval') || '7200000');
            }}
            if (typeof lastSyncTime === 'undefined') {{
                lastSyncTime = localStorage.getItem('lastSyncTime') || null;
            }}
            
            const toggle = document.getElementById('progressSyncToggle');
            const statusText = document.getElementById('syncStatusText');
            const lastSyncTimeEl = document.getElementById('lastSyncTime');
            const syncIntervalSelect = document.getElementById('syncIntervalSelect');
            
            if (toggle) {{
                toggle.textContent = progressSyncEnabled ? '禁用' : '启用';
                toggle.classList.toggle('active', progressSyncEnabled);
            }}
            
            if (statusText) {{
                statusText.textContent = isBackendOnline ? '已连接' : '未连接';
            }}
            
            if (lastSyncTimeEl) {{
                if (lastSyncTime) {{
                    const date = new Date(parseInt(lastSyncTime));
                    lastSyncTimeEl.textContent = date.toLocaleString();
                }} else {{
                    lastSyncTimeEl.textContent = '从未同步';
                }}
            }}
            
            if (syncIntervalSelect) {{
                syncIntervalSelect.value = syncInterval.toString();
            }}
        }}
        
        function changeSyncInterval(value) {{
            syncInterval = parseInt(value);
            localStorage.setItem('syncInterval', syncInterval.toString());
            showNotification('同步间隔已更新');
        }}
        
        function manualSync() {{
            console.log('手动同步进度');
            console.log('进度同步启用状态:', progressSyncEnabled);
            console.log('后端连接状态:', isBackendOnline);
            console.log('SAVE_PROGRESS_URL:', SAVE_PROGRESS_URL);
            console.log('BOOK_ID:', BOOK_ID);
            
            if (!progressSyncEnabled) {{
                console.log('进度同步未启用');
                showNotification('请先启用进度同步');
                return;
            }}
            
            // 检查后端是否在线
            if (!isBackendOnline) {{
                showNotification('后端未连接，正在尝试重新连接...');
                // 尝试重新检查后端状态
                checkBackendStatus().then(async isOnline => {{
                    if (isOnline) {{
                        showNotification('后端已重新连接，正在同步...');
                        // 如果重新检查后发现在线，自动执行同步
                        setTimeout(() => manualSync(), 500);
                    }} else {{
                        showNotification('无法连接到后端服务器');
                    }}
                }});
                return;
            }}
            
            if (SAVE_PROGRESS_URL) {{
                const scrollTop = window.scrollY;
                const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
                const clientHeight = window.innerHeight;
                const scrollableHeight = Math.max(scrollHeight - clientHeight, 1);
                const progress = (scrollTop / scrollableHeight) * 100;
                const progressDecimal = progress / 100;
                
                const content = document.getElementById('content');
                let word_count = 0;
                if (content) {{
                    word_count = content.textContent.replace(/\\s+/g, '').length;
                }}
                
                const data = {{
                    progress: progressDecimal.toFixed(15),
                    scrollTop: scrollTop,
                    scrollHeight: scrollHeight,
                    current_page: Math.floor(progressDecimal * 100),
                    total_pages: 100,
                    word_count: word_count,
                    timestamp: Date.now()
                }};
                
                console.log('手动同步 - 发送数据:', data);
                // 对BOOK_ID进行URL编码，避免非ASCII字符
                const encodedBookId = encodeURIComponent(BOOK_ID);
                fetch(SAVE_PROGRESS_URL, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-Book-ID': encodedBookId
                    }},
                    body: JSON.stringify(data)
                }}).then(response => {{
                    if (response.ok) {{
                        lastSyncTime = Date.now().toString();
                        localStorage.setItem('lastSyncTime', lastSyncTime);
                        updateProgressSyncUI();
                        showNotification('同步成功');
                    }} else {{
                        showNotification('同步失败');
                    }}
                }}).catch(err => {{
                    showNotification('同步失败: ' + err.message);
                }});
            }} else {{
                showNotification('后端未连接，无法同步');
            }}
        }}
        
        // 文件导入相关函数
        function toggleFileImport() {{
            const panel = document.getElementById('fileImportPanel');
            if (panel.style.display === 'none') {{
                panel.style.display = 'block';
                // 延迟初始化拖放区域，确保DOM完全渲染
                setTimeout(() => {{
                    initDropZone();
                }}, 100);
            }} else {{
                panel.style.display = 'none';
            }}
        }}
        
        // 初始化拖放区域
        function initDropZone() {{
            const dropZone = document.getElementById('dropZone');
            if (!dropZone) return;
            
            // 移除可能存在的事件监听器
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                dropZone.removeEventListener(eventName, preventDefaults);
                document.body.removeEventListener(eventName, preventDefaults);
                dropZone.removeEventListener(eventName, highlight);
                dropZone.removeEventListener(eventName, unhighlight);
                dropZone.removeEventListener(eventName, handleDrop);
            }});
            
            // 防止默认的拖放行为
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                dropZone.addEventListener(eventName, preventDefaults, false);
                document.body.addEventListener(eventName, preventDefaults, false);
            }});
            
            // 添加拖放事件监听器
            ['dragenter', 'dragover'].forEach(eventName => {{
                dropZone.addEventListener(eventName, highlight, false);
            }});
            
            ['dragleave', 'drop'].forEach(eventName => {{
                dropZone.addEventListener(eventName, unhighlight, false);
            }});
            
            // 处理文件拖放
            dropZone.addEventListener('drop', handleDrop, false);
            
            console.log('拖放区域已初始化');
        }}
        
        // 防止默认行为
        function preventDefaults(e) {{
            e.preventDefault();
            e.stopPropagation();
        }}
        
        // 高亮拖放区域
        function highlight(e) {{
            console.log('拖放区域高亮');
            const dropZone = document.getElementById('dropZone');
            if (dropZone) {{
                dropZone.classList.add('dragover');
            }}
        }}
        
        // 取消高亮
        function unhighlight(e) {{
            console.log('拖放区域取消高亮');
            const dropZone = document.getElementById('dropZone');
            if (dropZone) {{
                dropZone.classList.remove('dragover');
            }}
        }}
        
        // 处理文件拖放
        function handleDrop(e) {{
            console.log('拖放事件触发');
            const dt = e.dataTransfer;
            const files = dt.files;
            
            console.log('拖放了 ' + files.length + ' 个文件');
            
            if (files.length > 0) {{
                // 处理第一个文件
                console.log('处理文件: ' + files[0].name);
                handleDroppedFile(files[0]);
            }} else {{
                console.log('没有检测到文件');
            }}
        }}
        
        
        
        // 处理拖放的文件
        function handleDroppedFile(file) {{
            // 检查文件类型
            const fileName = file.name.toLowerCase();
            const allowedTypes = ['.txt', '.html', '.htm', '.md', '.pdf', '.epub', '.mobi', '.azw', '.azw3'];
            
            const isValidType = allowedTypes.some(type => fileName.endsWith(type));
            
            if (!isValidType) {{
                showNotification('不支持的文件类型，请选择 .txt, .html, .htm, .md, .pdf, .epub, .mobi, .azw 或 .azw3 文件');
                return;
            }}
            
            // 设置选中的文件
            selectedFile = file;
            const fileTitle = document.getElementById('fileTitle');
            const filePreview = document.getElementById('filePreview');
            
            // 自动填充标题
            if (fileTitle && !fileTitle.value) {{
                fileTitle.value = file.name.replace(/\\.[^/.]+$/, '');
            }}
            
            // 检查是否为二进制电子书格式
            const isBinaryFormat = ['.pdf', '.epub', '.mobi', '.azw', '.azw3'].some(type => fileName.endsWith(type));
            
            // 读取并预览文件
            const reader = new FileReader();
            reader.onload = function(e) {{
                fileContent = e.target.result;
                
                if (isBinaryFormat) {{
                    // 对于二进制格式，只显示文件信息
                    if (filePreview) {{
                                                filePreview.innerHTML = '<div style="padding: 10px; background: rgba(100, 149, 237, 0.1); border-radius: 4px; border-left: 4px solid rgba(100, 149, 237, 0.6);">' +
                                    '<h4 style="margin: 0 0 10px 0; color: ' + currentSettings.title + ';">电子书文件</h4>' +
                                    '<p style="margin: 5px 0;"><strong>文件名：</strong>' + file.name + '</p>' +
                                    '<p style="margin: 5px 0;"><strong>文件大小：</strong>' + (file.size / 1024 / 1024).toFixed(2) + ' MB</p>' +
                                    '<p style="margin: 5px 0;"><strong>文件类型：</strong>' + fileName.substring(fileName.lastIndexOf('.')) + '</p>' +
                                    '<p style="margin: 10px 0; color: #666; font-size: 12px;">此文件将在后端进行解析处理</p>' +
                                '</div>';
                    }}
                }} else {{
                    // 对于文本格式，显示内容预览
                    let preview = fileContent;
                    if (preview.length > 1000) {{
                        preview = preview.substring(0, 1000) + '...';
                    }}
                    
                    // 转换HTML特殊字符
                    preview = preview.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    
                    if (filePreview) {{
                        filePreview.innerHTML = '<pre style="white-space: pre-wrap; font-family: monospace; font-size: 12px;">' + preview + '</pre>';
                    }}
                }}
                
                showNotification('已加载文件：' + file.name);
            }};
            
            reader.onerror = function() {{
                showNotification('文件读取失败');
                if (filePreview) {{
                    filePreview.innerHTML = '<p style="color: red;">文件读取失败</p>';
                }}
            }};
            
            reader.readAsText(file, 'utf-8');
        }}
        
        // 从书库添加书籍（关闭书库面板，打开文件导入面板）
        function addBookFromLibrary() {{
            // 关闭书库面板
            const libraryPanel = document.getElementById('bookLibraryPanel');
            if (libraryPanel) {{
                libraryPanel.style.display = 'none';
            }}
            
            // 打开文件导入面板
            const importPanel = document.getElementById('fileImportPanel');
            if (importPanel) {{
                importPanel.style.display = 'block';
            }}
        }}
        
        function handleFileSelect(event) {{
            const file = event.target.files[0];
            if (!file) return;
            
            selectedFile = file;
            const fileTitle = document.getElementById('fileTitle');
            const filePreview = document.getElementById('filePreview');
            
            // 自动填充标题
            if (fileTitle && !fileTitle.value) {{
                fileTitle.value = file.name.replace(/\\.[^/.]+$/, '');
            }}
            
            // 读取并预览文件
            const reader = new FileReader();
            reader.onload = function(e) {{
                fileContent = e.target.result;
                
                // 限制预览长度
                let preview = fileContent;
                if (preview.length > 1000) {{
                    preview = preview.substring(0, 1000) + '...';
                }}
                
                // 转换HTML特殊字符
                preview = preview.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                
                if (filePreview) {{
                    filePreview.innerHTML = '<pre style="white-space: pre-wrap; font-family: monospace; font-size: 12px;">' + preview + '</pre>';
                }}
            }};
            
            reader.onerror = function() {{
                showNotification('文件读取失败');
                if (filePreview) {{
                    filePreview.innerHTML = '<p style="color: red;">文件读取失败</p>';
                }}
            }};
            
            reader.readAsText(file, 'utf-8');
        }}
        
        function importFile() {{
            if (!selectedFile || !fileContent) {{
                showNotification('请先选择文件');
                return;
            }}
            
            const titleInput = document.getElementById('fileTitle');
            const title = titleInput && titleInput.value ? titleInput.value : selectedFile.name;
            
            // 处理文件内容
            let processedContent = fileContent;
            
            // 根据文件类型处理
            const fileName = selectedFile.name.toLowerCase();
            const isBinaryFormat = ['.pdf', '.epub', '.mobi', '.azw', '.azw3'].some(type => fileName.endsWith(type));
            
            if (isBinaryFormat) {{
                // 对于二进制电子书格式，显示等待处理的提示
                processedContent = '<div style="text-align: center; padding: 50px 20px; color: ' + currentSettings.text + ';">' +
                        '<div style="font-size: 48px; margin-bottom: 20px;">📚</div>' +
                        '<h2 style="color: ' + currentSettings.title + '; margin-bottom: 15px;">' + title + '</h2>' +
                        '<p style="margin-bottom: 10px;">正在处理电子书文件...</p>' +
                        '<p style="font-size: 14px; color: rgba(128, 128, 128, 0.7);">' +
                            '文件类型：' + fileName.substring(fileName.lastIndexOf('.')) + '<br>' +
                            '文件大小：' + (selectedFile.size / 1024 / 1024).toFixed(2) + ' MB' +
                        '</p>' +
                        '<div style="margin-top: 30px; padding: 15px; background: rgba(128, 128, 128, 0.1); border-radius: 8px; text-align: left; max-width: 400px; margin-left: auto; margin-right: auto;">' +
                            '<p style="margin: 5px 0; font-size: 12px;">💡 此电子书文件需要后端解析服务进行处理</p>' +
                            '<p style="margin: 5px 0; font-size: 12px;">📖 支持的格式：PDF、EPUB、MOBI、AZW、AZW3</p>' +
                        '</div>' +
                    '</div>';
            }} else if (fileName.endsWith('.txt')) {{
                // TXT文件：转换为HTML段落
                const paragraphs = fileContent.split('\\n');
                processedContent = '';
                paragraphs.forEach(para => {{
                    para = para.trim();
                    if (para) {{
                        processedContent += '<p>' + para + '</p>';
                    }}
                }});
            }} else if (fileName.endsWith('.html') || fileName.endsWith('.htm')) {{
                // HTML文件：直接使用
                processedContent = fileContent;
            }} else if (fileName.endsWith('.md')) {{
                // 简单的Markdown处理
                const lines = fileContent.split('\\n');
                processedContent = '';
                lines.forEach(line => {{
                    line = line.trim();
                    if (!line) return;
                    
                    if (line.startsWith('# ')) {{
                        processedContent += '<h1>' + line.substring(2) + '</h1>';
                    }} else if (line.startsWith('## ')) {{
                        processedContent += '<h2>' + line.substring(3) + '</h2>';
                    }} else if (line.startsWith('### ')) {{
                        processedContent += '<h3>' + line.substring(4) + '</h3>';
                    }} else {{
                        processedContent += '<p>' + line + '</p>';
                    }}
                }});
            }}
            
            // 添加到导入书籍列表
            const bookInfo = {{
                id: Date.now().toString(),
                title: title,
                fileName: selectedFile.name,
                content: processedContent,
                importTime: Date.now(),
                lastReadTime: null,
                progress: 0,
                isBinary: isBinaryFormat,
                fileSize: selectedFile.size,
                fileType: fileName.substring(fileName.lastIndexOf('.'))
            }};
            
            importedBooks.unshift(bookInfo);
            saveImportedBooksToStorage();
            
            // 添加到阅读历史
            addToReadingHistory(title, 'imported', bookInfo.id);
            
            // 更新内容显示
            const contentEl = document.getElementById('content');
            if (contentEl) {{
                contentEl.innerHTML = processedContent;
            }}
            
            // 更新页面标题
            document.title = title + ' - 浏览器阅读器';
            
            // 关闭面板并重置
            toggleFileImport();
            document.getElementById('fileInput').value = '';
            document.getElementById('fileTitle').value = '';
            document.getElementById('filePreview').innerHTML = '<p style="color: #666;">请选择文件进行预览</p>';
            selectedFile = null;
            fileContent = null;
            
            showNotification(typeof t === 'function' ? t('browser_reader.file_imported', {{title: title}}) : ('已导入文件：' + title));
            
            // 如果书库面板当前是打开的，更新书库显示
            const libraryPanel = document.getElementById('bookLibraryPanel');
            if (libraryPanel && libraryPanel.style.display !== 'none') {{
                loadBookLibrary();
            }}
        }}
        
        // 书库相关函数
        function toggleBookLibrary() {{
            const panel = document.getElementById('bookLibraryPanel');
            if (panel.style.display === 'none') {{
                panel.style.display = 'block';
                loadBookLibrary();
            }} else {{
                panel.style.display = 'none';
                stopImportRefresh();
            }}
        }}
        
        function switchLibraryTab(tab) {{
            const historyTab = document.getElementById('historyTab');
            const importedTab = document.getElementById('importedTab');
            const tabBtns = document.querySelectorAll('.library-tabs .tab-btn');
            
            tabBtns.forEach(btn => btn.classList.remove('active'));
            
            if (tab === 'history') {{
                historyTab.style.display = 'block';
                importedTab.style.display = 'none';
                tabBtns[0].classList.add('active');
                loadReadingHistory();
            }} else {{
                historyTab.style.display = 'none';
                importedTab.style.display = 'block';
                tabBtns[1].classList.add('active');
                loadImportedBooks();
            }}
        }}
        
        // 搜索阅读历史
        function searchLibraryBooks() {{
            const searchInput = document.getElementById('librarySearchInput');
            const clearBtn = document.getElementById('clearSearchBtn');
            const bookList = document.getElementById('historyBookList');
            const searchTerm = searchInput.value.toLowerCase().trim();
            
            // 显示/隐藏清除按钮
            clearBtn.style.display = searchTerm ? 'block' : 'none';
            
            // 获取所有书籍项
            const bookItems = bookList.querySelectorAll('.book-item');
            let visibleCount = 0;
            
            bookItems.forEach(item => {{
                const title = item.querySelector('.book-title');
                if (title) {{
                    const titleText = title.textContent.toLowerCase();
                    if (titleText.includes(searchTerm)) {{
                        item.style.display = 'block';
                        visibleCount++;
                    }} else {{
                        item.style.display = 'none';
                    }}
                }}
            }});
            
            // 显示搜索结果状态
            if (searchTerm && visibleCount === 0) {{
                if (!bookList.querySelector('.search-no-results')) {{
                    const noResults = document.createElement('p');
                    noResults.className = 'search-no-results';
                    noResults.style.cssText = 'color: #666; text-align: center; padding: 20px;';
                    noResults.textContent = t('browser_reader.library_search_no_results');
                    bookList.appendChild(noResults);
                }}
            }} else {{
                const noResults = bookList.querySelector('.search-no-results');
                if (noResults) {{
                    noResults.remove();
                }}
            }}
        }}
        
        // 清除阅读历史搜索
        function clearLibrarySearch() {{
            const searchInput = document.getElementById('librarySearchInput');
            const clearBtn = document.getElementById('clearSearchBtn');
            const bookList = document.getElementById('historyBookList');
            
            searchInput.value = '';
            clearBtn.style.display = 'none';
            
            // 显示所有书籍项
            const bookItems = bookList.querySelectorAll('.book-item');
            bookItems.forEach(item => {{
                item.style.display = 'block';
            }});
            
            // 移除搜索结果状态
            const noResults = bookList.querySelector('.search-no-results');
            if (noResults) {{
                noResults.remove();
            }}
        }}
        
        // 搜索导入书籍
        function searchImportedBooks() {{
            const searchInput = document.getElementById('importedSearchInput');
            const clearBtn = document.getElementById('clearImportedSearchBtn');
            const bookList = document.getElementById('importedBookList');
            const searchTerm = searchInput.value.toLowerCase().trim();
            
            // 显示/隐藏清除按钮
            clearBtn.style.display = searchTerm ? 'block' : 'none';
            
            // 获取所有书籍项
            const bookItems = bookList.querySelectorAll('.book-item');
            let visibleCount = 0;
            
            bookItems.forEach(item => {{
                const title = item.querySelector('.book-title');
                if (title) {{
                    const titleText = title.textContent.toLowerCase();
                    if (titleText.includes(searchTerm)) {{
                        item.style.display = 'block';
                        visibleCount++;
                    }} else {{
                        item.style.display = 'none';
                    }}
                }}
            }});
            
            // 显示搜索结果状态
            if (searchTerm && visibleCount === 0) {{
                if (!bookList.querySelector('.search-no-results')) {{
                    const noResults = document.createElement('p');
                    noResults.className = 'search-no-results';
                    noResults.style.cssText = 'color: #666; text-align: center; padding: 20px;';
                    noResults.textContent = t('browser_reader.library_search_no_results');
                    bookList.appendChild(noResults);
                }}
            }} else {{
                const noResults = bookList.querySelector('.search-no-results');
                if (noResults) {{
                    noResults.remove();
                }}
            }}
        }}
        
        // 清除导入书籍搜索
        function clearImportedSearch() {{
            const searchInput = document.getElementById('importedSearchInput');
            const clearBtn = document.getElementById('clearImportedSearchBtn');
            const bookList = document.getElementById('importedBookList');
            
            searchInput.value = '';
            clearBtn.style.display = 'none';
            
            // 显示所有书籍项
            const bookItems = bookList.querySelectorAll('.book-item');
            bookItems.forEach(item => {{
                item.style.display = 'block';
            }});
            
            // 移除搜索结果状态
            const noResults = bookList.querySelector('.search-no-results');
            if (noResults) {{
                noResults.remove();
            }}
        }}
        
        function addToReadingHistory(title, type, bookId) {{
            const historyItem = {{
                id: Date.now().toString(),
                title: title,
                type: type, // 'file' or 'imported'
                bookId: bookId,
                readTime: Date.now(),
                progress: 0
            }};
            
            // 移除重复项（如果存在）
            readingHistory = readingHistory.filter(item => item.bookId !== bookId);
            
            // 添加到开头
            readingHistory.unshift(historyItem);
            
            // 限制历史记录数量
            if (readingHistory.length > 50) {{
                readingHistory = readingHistory.slice(0, 50);
            }}
            
            localStorage.setItem('readingHistory', JSON.stringify(readingHistory));
        }}
        
        function loadReadingHistory() {{
            const historyList = document.getElementById('historyBookList');
            if (!historyList) return;
            
            if (readingHistory.length === 0) {{
                historyList.innerHTML = '<div class="empty-state">暂无阅读历史</div>';
                return;
            }}
            
            let html = '';
            readingHistory.forEach(item => {{
                const date = new Date(item.readTime);
                const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                
                html += '<div class="book-item" onclick="openHistoryBook(\\'' + item.bookId + '\\', \\'' + item.type + '\\')">' +
                    '<div class="book-cover">' + (item.type === 'imported' ? '导入' : '文件') + '</div>' +
                    '<div class="book-info">' +
                        '<div class="book-title">' + item.title + '</div>' +
                        '<div class="book-meta">' + dateStr + ' · 进度 ' + Math.round(item.progress || 0) + '%</div>' +
                    '</div>' +
                    '<div class="book-actions">' +
                        '<button onclick="event.stopPropagation(); removeHistoryItem(\\'' + item.id + '\\')">删除</button>' +
                    '</div>' +
                '</div>';
            }});
            
            historyList.innerHTML = html;
        }}
        
        async function loadImportedBooks() {{
            const bookList = document.getElementById('importedBookList');
            if (!bookList) return;

            // 检查是否有正在导入的书籍
            const isImporting = IndexedDBUtils.isProcessing || IndexedDBUtils.saveQueue.length > 0;

            // 检查 importedBooks 中是否有正在导入的书籍（isLoaded === undefined）
            const hasLoadingBooks = importedBooks.some(book => book.isLoaded === undefined);

            if (importedBooks.length === 0) {{
                // 没有任何书籍记录，检查 IndexedDB 中是否有数据
                let idbBookCount = 0;
                try {{
                    const bookIds = await IndexedDBUtils.getAllBookIds();
                    idbBookCount = bookIds.length;
                }} catch (e) {{
                    console.error('获取 IndexedDB 信息失败:', e);
                }}

                if (idbBookCount > 0 || isImporting) {{
                    // IndexedDB 中有数据或正在导入
                    bookList.innerHTML = '<div class="empty-state" style="text-align: center; padding: 40px 20px;">' +
                        '<div style="font-size: 48px; margin-bottom: 20px;">⏳</div>' +
                        '<p style="color: #666; font-size: 16px;">正在导入书籍,请稍后</p>' +
                        '</div>';
                }} else {{
                    // 完全没有任何书籍数据
                    bookList.innerHTML = '<div class="empty-state" style="text-align: center; padding: 40px 20px;">' +
                        '<div style="font-size: 48px; margin-bottom: 20px;">📚</div>' +
                        '<p style="color: #666; font-size: 16px;">请添加书籍或目录</p>' +
                        '</div>';
                }}
                return;
            }}

            // 如果有正在导入的书籍或队列中有数据，立即显示导入提示，然后后台检查状态
            if (hasLoadingBooks || isImporting) {{
                bookList.innerHTML = '<div class="empty-state" style="text-align: center; padding: 40px 20px;">' +
                    '<div style="font-size: 48px; margin-bottom: 20px;">⏳</div>' +
                    '<p style="color: #666; font-size: 16px;">正在导入书籍,请稍后</p>' +
                    '<p style="color: #999; font-size: 12px; margin-top: 10px;">已找到 ' + importedBooks.length + ' 本书籍，正在加载内容...</p>' +
                    '</div>';

                // 后台检查书籍状态，完成后自动刷新
                for (const book of importedBooks) {{
                    if (book.isLoaded === undefined) {{
                        try {{
                            const content = await IndexedDBUtils.getBookContent(book.id);
                            book.isLoaded = content !== null;
                        }} catch (error) {{
                            console.warn('检查书籍状态失败:', book.id, error);
                            book.isLoaded = false;
                        }}
                    }}
                }}

                // 所有检查完成后，重新加载显示
                loadImportedBooks();
                return;
            }}

            // 所有书籍都加载完成，直接显示书籍列表
            let html = '';
            importedBooks.forEach(book => {{
                const date = new Date(book.importTime);
                const dateStr = date.toLocaleDateString();
                const statusIcon = book.isLoaded === false ? '❌' : '✅';

                html += '<div class="book-item" onclick="openImportedBook(\\'' + book.id + '\\')">' +
                    '<div class="book-cover">' + statusIcon + '</div>' +
                    '<div class="book-info">' +
                        '<div class="book-title">' + book.title + '</div>' +
                        '<div class="book-meta">' + dateStr + ' · ' + book.fileName + '</div>' +
                    '</div>' +
                    '<div class="book-actions">' +
                        '<button onclick="event.stopPropagation(); deleteImportedBook(\\'' + book.id + '\\')">删除</button>' +
                    '</div>' +
                    '</div>';
            }});

            bookList.innerHTML = html;
        }}
        
        function loadBookLibrary() {{
            loadReadingHistory();
            loadImportedBooks();

            // 设置定时刷新，当有正在导入的书籍时自动刷新
            if (!window.importRefreshInterval) {{
                window.importRefreshInterval = setInterval(async () => {{
                    // 检查是否有正在导入的书籍（队列中有数据或正在处理）
                    const queueLength = IndexedDBUtils.getQueueLength();
                    const isProcessing = IndexedDBUtils.isProcessing;

                    // 如果有正在导入的书籍，刷新显示
                    if (queueLength > 0 || isProcessing) {{
                        console.log('自动刷新导入状态...');
                        await loadImportedBooks();
                    }}
                }}, 2000); // 每2秒检查一次
            }}
        }}

        // 停止定时刷新
        function stopImportRefresh() {{
            if (window.importRefreshInterval) {{
                clearInterval(window.importRefreshInterval);
                window.importRefreshInterval = null;
            }}
        }}
        
        // 初始化书籍状态检查
        async function initBookStatusCheck() {{
            console.log('开始检查书籍状态...');
            let needsUpdate = false;
            
            for (const book of importedBooks) {{
                if (book.isLoaded === undefined) {{
                    // 检查 IndexedDB 中是否有内容
                    try {{
                        const content = await IndexedDBUtils.getBookContent(book.id);
                        book.isLoaded = content !== null;
                        needsUpdate = true;
                        console.log(`书籍 ${{book.title}} 状态更新为:`, book.isLoaded ? '已加载' : '未加载');
                    }} catch (error) {{
                        console.warn('检查书籍状态失败:', book.id, error);
                        book.isLoaded = false;
                        needsUpdate = true;
                    }}
                }}
            }}
            
            if (needsUpdate) {{
                await saveImportedBooksToStorage();
                // 刷新书籍列表显示
                const bookList = document.getElementById('importedBookList');
                if (bookList && bookList.children.length > 0) {{
                    loadImportedBooks();
                }}
            }}
        }}
        
        function openHistoryBook(bookId, type) {{
            if (type === 'imported') {{
                openImportedBook(bookId);
            }} else {{
                showNotification('文件类型暂不支持重新打开');
            }}
        }}
        
        async function openImportedBook(bookId) {{
            const book = importedBooks.find(b => b.id === bookId);
            if (!book) {{
                showNotification('书籍不存在');
                return;
            }}
            
            // 更新当前书籍ID并重新加载进度
            updateCurrentBook(bookId);
            
            // 更新内容
            const contentEl = document.getElementById('content');
            if (contentEl) {{
                // 首先尝试直接从 IndexedDB 获取内容
                try {{
                    const content = await IndexedDBUtils.getBookContent(bookId);
                    if (content) {{
                        // 内容存在，直接显示
                        contentEl.innerHTML = content;
                        // 更新书籍状态为已加载
                        if (book.isLoaded === undefined) {{
                            book.isLoaded = true;
                            await saveImportedBooksToStorage();
                        }}
                    }} else {{
                        // 内容不存在，可能是还在加载中
                        if (book.isLoaded === undefined) {{
                            // 显示加载状态并开始轮询
                            contentEl.innerHTML = '<div style="text-align: center; padding: 50px 20px;">' +
                                                 '<div style="font-size: 48px; margin-bottom: 20px;">⏳</div>' +
                                                 '<h2>' + book.title + '</h2>' +
                                                 '<p style="color: #666; margin: 20px 0;">正在加载书籍内容...</p>' +
                                                 '<p style="color: #666;">请稍候，正在处理大量书籍</p>' +
                                                 '<div id="loadingProgress" style="margin-top: 20px;">' +
                                                 '<div style="width: 200px; height: 4px; background: #eee; border-radius: 2px; margin: 0 auto;">' +
                                                 '<div id="progressBar" style="width: 0%; height: 100%; background: #4CAF50; border-radius: 2px; transition: width 0.3s;"></div>' +
                                                 '</div>' +
                                                 '</div>' +
                                                 '</div>';
                            
                            // 开始轮询检查内容是否加载完成
                            let attempts = 0;
                            const maxAttempts = 60; // 最多检查60次（约30秒）
                            const checkInterval = setInterval(async () => {{
                                attempts++;
                                
                                // 更新进度条
                                const progressBar = document.getElementById('progressBar');
                                if (progressBar) {{
                                    const progress = Math.min((attempts / maxAttempts) * 100, 90);
                                    progressBar.style.width = progress + '%';
                                }}
                                
                                try {{
                                    const updatedContent = await IndexedDBUtils.getBookContent(bookId);
                                    if (updatedContent) {{
                                        clearInterval(checkInterval);
                                        contentEl.innerHTML = updatedContent;
                                        book.isLoaded = true;
                                        await saveImportedBooksToStorage();
                                        showNotification('书籍加载完成：' + book.title);
                                    }} else if (attempts >= maxAttempts) {{
                                        // 超时
                                        clearInterval(checkInterval);
                                        contentEl.innerHTML = '<div style="text-align: center; padding: 50px 20px;">' +
                                                             '<div style="font-size: 48px; margin-bottom: 20px;">⏱️</div>' +
                                                             '<h2>' + book.title + '</h2>' +
                                                             '<p style="color: #ff666;">加载超时</p>' +
                                                             '<p style="color: #666;">书籍可能仍在处理中，请稍后再试</p>' +
                                                             '</div>';
                                    }}
                                }} catch (error) {{
                                    console.error('检查书籍状态失败:', error);
                                }}
                            }}, 500); // 每500ms检查一次
                        }} else {{
                            // 内容确实不存在
                            contentEl.innerHTML = '<div style="text-align: center; padding: 50px 20px;">' +
                                                 '<div style="font-size: 48px; margin-bottom: 20px;">📖</div>' +
                                                 '<h2>' + book.title + '</h2>' +
                                                 '<p style="color: #666; margin: 20px 0;">书籍内容未找到</p>' +
                                                 '<p style="color: #666;">请重新导入此文件</p>' +
                                                 '</div>';
                        }}
                    }}
                }} catch (error) {{
                    console.error('从 IndexedDB 读取内容失败:', error);
                    // IndexedDB 读取失败，显示错误但不设置超时
                    contentEl.innerHTML = '<div style="text-align: center; padding: 50px 20px;">' +
                                         '<div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>' +
                                         '<h2>' + book.title + '</h2>' +
                                         '<p style="color: #ff666;">读取书籍失败</p>' +
                                         '<p style="color: #666;">请尝试重新导入此文件</p>' +
                                         '</div>';
                }}
            }}
            
            // 更新页面标题
            document.title = book.title + ' - 浏览器阅读器';
            
            // 更新阅读历史
            addToReadingHistory(book.title, 'imported', bookId);
            
            // 更新最后阅读时间
            book.lastReadTime = Date.now();
            await saveImportedBooksToStorage();
            
            // 关闭书库面板
            toggleBookLibrary();
            
            // 延迟加载进度，等待内容完全渲染
            setTimeout(() => {{
                loadBookProgress();
            }}, 100);
            
            showNotification('已打开书籍：' + book.title);
        }}
        
        function removeHistoryItem(itemId) {{
            if (!confirm('确定要删除这条历史记录吗？')) {{
                return;
            }}
            
            readingHistory = readingHistory.filter(item => item.id !== itemId);
            localStorage.setItem('readingHistory', JSON.stringify(readingHistory));
            loadReadingHistory();
            showNotification('历史记录已删除');
        }}
        
        async function deleteImportedBook(bookId) {{
            if (!confirm('确定要删除这本书吗？删除后无法恢复。')) {{
                return;
            }}
            
            importedBooks = importedBooks.filter(book => book.id !== bookId);
            await saveImportedBooksToStorage();
            
            // 从 IndexedDB 中删除书籍内容
            try {{
                await IndexedDBUtils.deleteBookContent(bookId);
            }} catch (error) {{
                console.error('从 IndexedDB 删除书籍内容失败:', error);
            }}
            
            // 同时删除相关的历史记录
            readingHistory = readingHistory.filter(item => item.bookId !== bookId);
            localStorage.setItem('readingHistory', JSON.stringify(readingHistory));
            
            loadImportedBooks();
            showNotification('书籍已删除');
        }}
        
        function clearHistory() {{
            if (!confirm('确定要清空所有阅读历史吗？')) {{
                return;
            }}
            
            readingHistory = [];
            localStorage.setItem('readingHistory', JSON.stringify(readingHistory));
            loadReadingHistory();
            showNotification('阅读历史已清空');
        }}
        
        async function clearAllImportedBooks() {{
            const bookCount = importedBooks.length;
            if (bookCount === 0) {{
                showNotification('没有需要清空的书籍');
                return;
            }}
            
            if (!confirm('确定要清空所有 ' + bookCount + ' 本导入书籍吗？此操作将删除所有书籍内容和阅读进度，且无法恢复！')) {{
                return;
            }}
            
            // 二次确认
            if (!confirm('此操作不可逆！确定要继续吗？')) {{
                return;
            }}
            
            try {{
                // 从 IndexedDB 中删除所有书籍内容
                for (const book of importedBooks) {{
                    try {{
                        await IndexedDBUtils.deleteBookContent(book.id);
                    }} catch (error) {{
                        console.error('删除 IndexedDB 内容失败:', book.id, error);
                    }}
                }}
                
                // 清空导入书籍列表
                importedBooks = [];
                await saveImportedBooksToStorage();
                
                // 清空所有相关的阅读历史
                readingHistory = readingHistory.filter(item => item.type !== 'imported');
                localStorage.setItem('readingHistory', JSON.stringify(readingHistory));
                
                // 清空所有书籍的阅读进度
                const allKeys = Object.keys(localStorage);
                allKeys.forEach(key => {{
                    if (key.startsWith('localReadingProgress_imported_')) {{
                        localStorage.removeItem(key);
                    }}
                }});
                
                // 刷新显示
                loadImportedBooks();
                loadReadingHistory();
                
                showNotification('已清空所有 ' + bookCount + ' 本导入书籍');
                
            }} catch (error) {{
                console.error('清空所有书籍失败:', error);
                showNotification('清空书籍失败: ' + error.message);
            }}
        }}
        
        function refreshHistory() {{
            loadReadingHistory();
            showNotification('历史记录已刷新');
        }}
        
        function exportLibrary() {{
            const libraryData = {{
                importedBooks: importedBooks,
                readingHistory: readingHistory,
                exportTime: Date.now()
            }};
            
            const dataStr = JSON.stringify(libraryData, null, 2);
            const dataBlob = new Blob([dataStr], {{type: 'application/json'}});
            const url = URL.createObjectURL(dataBlob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = 'book_library_' + new Date().toISOString().split('T')[0] + '.json';
            link.click();
            
            URL.revokeObjectURL(url);
            showNotification('书库已导出');
        }}
        
        // 显示添加目录弹窗
        function showAddDirectoryModal() {{
            const modal = document.getElementById('addDirectoryModal');
            const directoryDropZone = document.getElementById('directoryDropZone');
            const directoryInput = document.getElementById('directoryInput');
            
            if (modal) {{
                modal.style.display = 'block';
            }}
            
            // 设置目录选择区域的点击事件
            if (directoryDropZone && directoryInput) {{
                directoryDropZone.onclick = function() {{
                    directoryInput.click();
                }};
            }}

            // 关闭书库面板
            toggleBookLibrary();
        }}
        
        // 处理目录选择
        function handleDirectorySelect(event) {{
            const files = event.target.files;
            
            if (files && files.length > 0) {{
                // 保存文件列表到全局变量
                selectedDirectoryFiles = Array.from(files);
                
                // 获取第一个文件的路径（所有文件都在同一目录）
                const firstFile = files[0];
                const directoryPath = firstFile.webkitRelativePath.split('/')[0];
                
                const directoryPathInput = document.getElementById('directoryPath');
                if (directoryPathInput) {{
                    directoryPathInput.value = directoryPath;
                }}
                
                showNotification('已选择目录: ' + directoryPath + '，共 ' + files.length + ' 个文件');
            }} else {{
                showNotification('未选择目录');
                selectedDirectoryFiles = null;
            }}
        }}
        
        // 关闭添加目录弹窗
        function closeAddDirectoryModal() {{
            const modal = document.getElementById('addDirectoryModal');
            const directoryPathInput = document.getElementById('directoryPath');
            
            if (modal) {{
                modal.style.display = 'none';
            }}
            
            // 清空目录路径和文件列表
            if (directoryPathInput) {{
                directoryPathInput.value = '';
            }}
            selectedDirectoryFiles = null;
        }}
        
        // 确认添加目录
        async function confirmAddDirectory() {{
            const directoryPathInput = document.getElementById('directoryPath');
            
            if (!directoryPathInput) {{
                showNotification('无法获取输入框');
                return;
            }}
            
            const directoryPath = directoryPathInput.value.trim();
            
            // 检查是否已选择目录文件
            if (!selectedDirectoryFiles || selectedDirectoryFiles.length === 0) {{
                showNotification('请选择目录');
                return;
            }}
            
            // 支持的书籍文件扩展名
            const supportedExtensions = ['.txt', '.html', '.htm', '.md', '.pdf', '.epub', '.mobi', '.azw', '.azw3'];
            
            // 创建右下角悬浮指示器
            const floatingIndicator = document.createElement('div');
            floatingIndicator.id = 'importFloatingIndicator';
            floatingIndicator.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 20px;
                border-radius: 50px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                cursor: pointer;
                z-index: 9999;
                font-size: 14px;
                font-weight: 500;
                display: none;
                align-items: center;
                gap: 10px;
                transition: all 0.3s ease;
                user-select: none;
            `;
            floatingIndicator.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 6v6l4 2"></path>
                </svg>
                <span>正在导入 <strong id="indicatorCount">0</strong> / <strong id="indicatorTotal">0</strong></span>
            `;
            document.body.appendChild(floatingIndicator);

            // 悬浮指示器悬停效果
            floatingIndicator.onmouseenter = function() {{
                this.style.transform = 'scale(1.05)';
                this.style.boxShadow = '0 6px 20px rgba(0,0,0,0.4)';
            }};
            floatingIndicator.onmouseleave = function() {{
                this.style.transform = 'scale(1)';
                this.style.boxShadow = '0 4px 15px rgba(0,0,0,0.3)';
            }};

            // 点击悬浮指示器打开进度窗口
            floatingIndicator.onclick = function() {{
                if (progressModal) {{
                    // 恢复到完整进度窗口
                    progressModal.style.position = 'fixed';
                    progressModal.style.top = '50%';
                    progressModal.style.left = '50%';
                    progressModal.style.transform = 'translate(-50%, -50%)';
                    progressModal.style.width = '300px';
                    progressModal.style.bottom = 'auto';
                    progressModal.style.right = 'auto';

                    // 恢复按钮
                    const btnContainer = progressModal.querySelector('div[style*="margin-top: 15px"]');
                    if (btnContainer) {{
                        btnContainer.innerHTML = `
                            <button id="bgImportBtn" style="padding: 5px 15px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">后台导入</button>
                            <button id="viewLibraryBtn" style="padding: 5px 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">查看书库</button>
                            <button id="cancelAddBtn" style="padding: 5px 15px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                        `;

                        // 重新绑定按钮事件
                        document.getElementById('bgImportBtn').onclick = function() {{
                            convertToMiniModal();
                        }};
                        document.getElementById('viewLibraryBtn').onclick = function() {{
                            saveImportedBooksToStorage();
                            loadImportedBooks();
                            toggleBookLibrary();
                            showNotification(`已刷新书库，已导入 ${{addedCount}} 本书籍`);
                        }};
                        document.getElementById('cancelAddBtn').onclick = function() {{
                            progressModal.style.display = 'none';
                            floatingIndicator.style.display = 'flex';
                            showNotification('导入在后台继续进行，点击右下角指示器查看进度');
                        }};
                    }}

                    // 恢复标题
                    const titleEl = progressModal.querySelector('h3');
                    if (titleEl) {{
                        titleEl.textContent = '正在添加书籍...';
                    }}

                    progressModal.style.display = 'block';
                    floatingIndicator.style.display = 'none';
                }}
            }};

            // 转换为迷你进度窗口
            function convertToMiniModal() {{
                if (progressModal) {{
                    progressModal.style.position = 'fixed';
                    progressModal.style.bottom = '20px';
                    progressModal.style.right = '20px';
                    progressModal.style.top = 'auto';
                    progressModal.style.left = 'auto';
                    progressModal.style.width = '300px';
                    progressModal.style.zIndex = '10000';
                    progressModal.style.minHeight = 'auto';

                    // 隐藏取消和查看书库按钮，只保留关闭按钮
                    const btnContainer = progressModal.querySelector('div[style*="margin-top: 15px"]');
                    if (btnContainer) {{
                        btnContainer.innerHTML = '<button id="closeBgImportBtn" style="padding: 5px 15px; background: #999; color: white; border: none; border-radius: 4px; cursor: pointer;">关闭</button>';
                        document.getElementById('closeBgImportBtn').onclick = function() {{
                            progressModal.style.display = 'none';
                            floatingIndicator.style.display = 'flex';
                            showNotification('导入在后台继续进行，点击右下角指示器查看进度');
                        }};
                    }}

                    // 简化进度显示
                    const titleEl = progressModal.querySelector('h3');
                    if (titleEl) {{
                        titleEl.textContent = '后台导入中...';
                    }}
                }}
            }}

            // 显示进度提示
                const progressModal = document.createElement('div');
                progressModal.style.cssText = `
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    z-index: 10000;
                    text-align: center;
                    min-width: 300px;
                `;
                progressModal.innerHTML = `
                    <h3 style="margin: 0 0 15px 0;">正在添加书籍...</h3>
                    <div style="margin-bottom: 10px;">
                        <span id="progressText">准备处理文件...</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden;">
                        <div id="progressBar" style="width: 0%; height: 100%; background: #4CAF50; transition: width 0.3s;"></div>
                    </div>
                    <div style="margin-top: 10px; font-size: 12px; color: #666;">
                        <span id="progressCount">0 / 0</span>
                    </div>
                    <div style="margin-top: 15px; display: flex; gap: 10px; justify-content: center;">
                        <button id="bgImportBtn" style="padding: 5px 15px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer;">后台导入</button>
                        <button id="viewLibraryBtn" style="padding: 5px 15px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">查看书库</button>
                        <button id="cancelAddBtn" style="padding: 5px 15px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">取消</button>
                    </div>
                `;
                document.body.appendChild(progressModal);

                // 添加取消按钮事件
                const cancelBtn = document.getElementById('cancelAddBtn');
                if (cancelBtn) {{
                    cancelBtn.onclick = function() {{
                        if (progressModal && progressModal.parentElement) {{
                            progressModal.remove();
                        }}
                        // 显示悬浮指示器
                        floatingIndicator.style.display = 'flex';
                        // 设置指示器总数
                        const indicatorTotal = document.getElementById('indicatorTotal');
                        if (indicatorTotal) {{
                            indicatorTotal.textContent = bookFiles.length;
                        }}
                        showNotification('导入在后台继续进行，点击右下角指示器查看进度');
                    }};
                }}
                
            // 先过滤出支持的书籍文件（在try外部定义，确保在catch中也能访问）
            const bookFiles = selectedDirectoryFiles.filter(file => {{
                const fileName = file.name.toLowerCase();
                return supportedExtensions.some(ext => fileName.endsWith(ext));
            }});
            
            try {{
                const progressBar = document.getElementById('progressBar');
                const progressText = document.getElementById('progressText');
                const progressCount = document.getElementById('progressCount');
                
                if (bookFiles.length === 0) {{
                    progressModal.remove();
                    showNotification('目录中没有找到支持的书籍文件');
                    return;
                }}
                
                progressCount.textContent = `0 / ${{bookFiles.length}}`;

                // 初始化悬浮指示器
                const indicatorTotal = document.getElementById('indicatorTotal');
                const indicatorCount = document.getElementById('indicatorCount');
                if (indicatorTotal) {{
                    indicatorTotal.textContent = bookFiles.length;
                }}
                if (indicatorCount) {{
                    indicatorCount.textContent = '0';
                }}

                // 将扫描到的书籍添加到导入书籍列表
                let addedCount = 0;
                let processedCount = 0;
                let isBackgroundImport = false; // 是否切换到后台导入
                let refreshCounter = 0; // 刷新计数器

                // 添加后台导入按钮事件
                const bgImportBtn = document.getElementById('bgImportBtn');
                const viewLibraryBtn = document.getElementById('viewLibraryBtn');

                if (bgImportBtn) {{
                    bgImportBtn.onclick = function() {{
                        isBackgroundImport = true;
                        convertToMiniModal();
                        showNotification('已切换到后台导入，您可以查看已导入的书籍');
                    }};
                }}

                if (viewLibraryBtn) {{
                    viewLibraryBtn.onclick = function() {{
                        // 先保存当前进度
                        saveImportedBooksToStorage();
                        loadImportedBooks();
                        showNotification(`已刷新书库，已导入 ${{addedCount}} 本书籍`);
                    }};
                }}

                // 使用队列逐个处理书籍文件，避免 Safari 并发压力过大
                const processFileQueue = async function(files) {{
                    // 在开始导入前立即刷新书库，显示"正在导入"状态
                    await loadImportedBooks();

                    for (let i = 0; i < files.length; i++) {{
                        const file = files[i];
                        processedCount++;

                        // 更新进度
                        if (progressBar) {{
                            const progress = (processedCount / files.length) * 100;
                            progressBar.style.width = progress + '%';
                        }}
                        if (progressText) {{
                            progressText.textContent = `正在处理: ${{file.name}}`;
                        }}
                        if (progressCount) {{
                            progressCount.textContent = `${{processedCount}} / ${{files.length}}`;
                        }}

                        // 更新悬浮指示器
                        if (indicatorCount) {{
                            indicatorCount.textContent = processedCount;
                        }}

                        // 检查是否已存在
                        const exists = importedBooks.find(b => b.fileName === file.name);
                        if (!exists) {{
                            // 检查文件类型
                            const fileName = file.name.toLowerCase();
                            let content = '';

                            if (fileName.endsWith('.txt') || fileName.endsWith('.md')) {{
                                // 对于文本文件，读取内容
                                const bookId = 'imported_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

                                // 先添加元数据到列表，标记为正在加载
                                importedBooks.push({{
                                    id: bookId,
                                    title: file.name.replace(/\.[^/.]+$/, ""),
                                    fileName: file.name,
                                    importTime: Date.now(),
                                    filePath: file.webkitRelativePath,
                                    isLoaded: undefined // 正在加载
                                }});
                                addedCount++;

                                // 读取文件内容并保存到 IndexedDB
                                try {{
                                    const textContent = await new Promise((resolve, reject) => {{
                                        const reader = new FileReader();
                                        reader.onload = (e) => resolve(e.target.result);
                                        reader.onerror = (e) => reject(reader.error);
                                        reader.readAsText(file);
                                    }});

                                    const bookData = importedBooks.find(b => b.fileName === file.name);
                                    if (bookData) {{
                                        const formattedContent = '<div style="padding: 20px; line-height: 1.8; white-space: pre-wrap;">' +
                                                              textContent.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>';

                                        // 使用队列保存，避免并发压力
                                        await IndexedDBUtils.addToQueue(bookId, formattedContent);
                                        bookData.isLoaded = true;
                                        console.log('书籍内容已保存到 IndexedDB:', file.name);

                                        // 每处理完 5 本书（或在后台导入模式下每处理完 1 本）就保存并刷新
                                        refreshCounter++;
                                        if (refreshCounter >= (isBackgroundImport ? 1 : 5)) {{
                                            saveImportedBooksToStorage();
                                            loadImportedBooks();
                                            refreshCounter = 0;
                                            if (isBackgroundImport) {{
                                                console.log('后台导入：已刷新书库，已导入', addedCount, '本书籍');
                                            }}
                                        }}
                                    }}
                                }} catch (error) {{
                                    console.error('处理文件失败:', file.name, error);
                                    const bookData = importedBooks.find(b => b.fileName === file.name);
                                    if (bookData) {{
                                        bookData.isLoaded = false;
                                    }}
                                }}
                            }} else {{
                                // 其他文件类型显示提示，保存到 IndexedDB
                                content = '<div style="text-align: center; padding: 50px 20px;">' +
                                         '<div style="font-size: 48px; margin-bottom: 20px;">📚</div>' +
                                         '<h2>' + file.name + '</h2>' +
                                         '<p style="color: #666; margin: 20px 0;">路径: ' + file.webkitRelativePath + '</p>' +
                                         '<p style="color: #666;">大小: ' + (file.size / 1024 / 1024).toFixed(2) + ' MB</p>' +
                                         '<p style="color: #666;">此文件类型需要后端解析</p>' +
                                         '</div>';

                                const bookId = 'imported_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                                importedBooks.push({{
                                    id: bookId,
                                    title: file.name.replace(/\.[^/.]+$/, ""),
                                    fileName: file.name,
                                    importTime: Date.now(),
                                    filePath: file.webkitRelativePath,
                                    isLoaded: true
                                }});
                                addedCount++;

                                // 使用队列保存
                                await IndexedDBUtils.addToQueue(bookId, content).catch(err => {{
                                    console.error('保存提示内容失败:', err);
                                }});
                            }}
                        }}

                        // 每处理完一个文件后短暂延迟，让 IndexedDB 有时间处理
                        if (i < files.length - 1) {{
                            await new Promise(resolve => setTimeout(resolve, 150));
                        }}
                    }}
                }};

                // 开始处理文件队列
                await processFileQueue(bookFiles);

                // 保存到本地存储
                saveImportedBooksToStorage();

                // 刷新列表
                loadImportedBooks();

                // 关闭进度模态框
                if (progressModal && progressModal.parentElement) {{
                    progressModal.remove();
                }}

                // 移除悬浮指示器
                if (floatingIndicator && floatingIndicator.parentElement) {{
                    floatingIndicator.remove();
                }}

                // 关闭弹窗
                closeAddDirectoryModal();

                showNotification(`成功添加 ${{addedCount}} 本书籍（总共处理 ${{bookFiles.length}} 个文件）`);

            }} catch (error) {{
                console.error('添加目录出错:', error);

                // 关闭进度模态框
                if (progressModal && progressModal.parentElement) {{
                    progressModal.remove();
                }}

                // 移除悬浮指示器
                if (floatingIndicator && floatingIndicator.parentElement) {{
                    floatingIndicator.remove();
                }}

                showNotification('添加目录时出错: ' + error.message);
            }}
        }}
        
        // 页面关闭前保存进度和统计
        window.addEventListener('beforeunload', function() {{
            // 保存阅读统计
            const sessionElapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
            const newTotalTime = totalReadingTime + sessionElapsed;
            localStorage.setItem('totalReadingTime', newTotalTime.toString());
            
            const scrollTop = window.scrollY;
            // 使用 document.documentElement.scrollHeight 更准确
            const scrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
            const clientHeight = window.innerHeight;

            console.log('beforeunload - scrollTop:', scrollTop, 'scrollHeight:', scrollHeight, 'clientHeight:', clientHeight);
            console.log('beforeunload - 页面加载冷却状态:', isPageLoading, '冷却剩余时间:', Math.max(0, pageLoadCooldown - (Date.now() - pageLoadStartTime)) / 1000, 's');

            let progress;
            // 如果还在页面加载冷却期间且有缓存的进度,使用缓存的值
            const elapsedTime = Date.now() - pageLoadStartTime;
            if (elapsedTime < pageLoadCooldown && cachedProgress !== null) {{
                console.log('beforeunload - 使用缓存的进度值:', cachedProgress);
                progress = cachedProgress * 100; // 转换为百分比
            }} else {{
                // 否则重新计算
                const scrollableHeight = Math.max(scrollHeight - clientHeight, 1);
                progress = (scrollTop / scrollableHeight) * 100;
                progress = Math.min(100, Math.max(0, progress));
                console.log('beforeunload - 重新计算进度:', progress);
            }}

            console.log('beforeunload - 最终使用的进度(百分比):', progress.toFixed(2) + '%');

            // 将百分比(0-100)转换为小数(0-1)保存到数据库
            // 使用高精度(15位小数)以匹配终端阅读器的精度
            const progressDecimal = progress / 100;

            // 计算页数（假设每页1000px）
            const estimatedPageHeight = 1000;
            const total_pages = Math.max(1, Math.floor(scrollHeight / estimatedPageHeight));
            const current_page = Math.min(total_pages, Math.floor(progressDecimal * total_pages));

            // 计算字数（估算）
            const content = document.getElementById('content');
            let word_count = 0;
            if (content) {{
                word_count = content.textContent.replace(/\\s+/g, '').length;
            }}

            const data = {{
                progress: progressDecimal.toFixed(15),
                scrollTop: scrollTop,
                scrollHeight: scrollHeight,
                current_page: current_page,
                total_pages: total_pages,
                word_count: word_count,
                timestamp: Date.now(),
                reading_time: newTotalTime
            }};

            // 总是保存到本地localStorage作为备份（始终保存，不管是否启用同步）
            try {{
                setLocalProgressData(data);
                console.log('beforeunload - 进度已保存到本地存储 [书籍ID:', BOOK_ID + ']');
            }} catch (e) {{
                console.log('beforeunload - 保存进度到本地存储失败:', e);
            }}

            // 如果有SAVE_PROGRESS_URL且启用进度同步，也发送到服务器
            if (SAVE_PROGRESS_URL && progressSyncEnabled) {{
                console.log('beforeunload - 发送数据(小数):', data);
                console.log('beforeunload - 发送JSON:', JSON.stringify(data));
                navigator.sendBeacon(SAVE_PROGRESS_URL, JSON.stringify(data));
            }} else {{
                if (!SAVE_PROGRESS_URL) {{
                    console.log('beforeunload - SAVE_PROGRESS_URL 为空，仅保存到本地');
                    console.log('beforeunload - SAVE_PROGRESS_URL类型:', typeof SAVE_PROGRESS_URL);
                    console.log('beforeunload - SAVE_PROGRESS_URL值:', SAVE_PROGRESS_URL);
                }} else if (!progressSyncEnabled) {{
                    console.log('beforeunload - 进度同步已禁用，仅保存到本地');
                    console.log('beforeunload - 但SAVE_PROGRESS_URL存在:', SAVE_PROGRESS_URL);
                }}
            }}
        }});

        // 显示存储使用情况
        async function showStorageInfo() {{
            try {{
                let totalSize = 0;
                let itemCount = 0;
                
                for (let key in localStorage) {{
                    if (localStorage.hasOwnProperty(key)) {{
                        totalSize += localStorage[key].length;
                        itemCount++;
                    }}
                }}
                
                const usedMB = (totalSize / 1024 / 1024).toFixed(2);
                const quotaMB = 5;
                const usagePercent = ((usedMB / quotaMB) * 100).toFixed(1);
                
                let status = usagePercent > 80 ? '存储空间不足' : '正常';
                
                // 获取 IndexedDB 中的书籍数量
                let idbBookCount = 0;
                try {{
                    const bookIds = await IndexedDBUtils.getAllBookIds();
                    idbBookCount = bookIds.length;
                }} catch (e) {{
                    console.error('获取 IndexedDB 信息失败:', e);
                }}
                
                const message = 'LocalStorage使用: ' + usedMB + 'MB / ' + quotaMB + 'MB (' + usagePercent + '%)\\n' +
                               'IndexedDB书籍数: ' + idbBookCount + ' 本\\n' +
                               '状态: ' + status;
                
                showNotification(message, 5000);
                
                if (usagePercent > 80) {{
                    setTimeout(async () => {{
                        if (confirm('存储空间即将用尽，是否清理旧书籍？')) {{
                            importedBooks.sort((a, b) => a.importTime - b.importTime);
                            const removeCount = Math.floor(importedBooks.length / 2);
                            
                            // 同时从 IndexedDB 中删除
                            for (let i = 0; i < removeCount; i++) {{
                                if (importedBooks[i]) {{
                                    IndexedDBUtils.deleteBookContent(importedBooks[i].id).catch(e => {{
                                        console.error('删除 IndexedDB 内容失败:', e);
                                    }});
                                }}
                            }}
                            
                            importedBooks.splice(0, removeCount);
                            await saveImportedBooksToStorage();
                            loadImportedBooks();
                            showNotification('已清理 ' + removeCount + ' 本旧书籍');
                        }}
                    }}, 1000);
                }}
                
            }} catch (error) {{
                showNotification('获取存储信息失败: ' + error.message);
            }}
        }}
    </script>

    
</body>
</html>"""
        
        # 替换所有document.write调用为直接文本
        import re
        
        def replace_document_write(match):
            key = match.group(1)
            return f"{{t('browser_reader.{key}')}}"
        
        # 替换 <script>document.write(t('key'));</script> 为 {t('key')}
        html = re.sub(r"<script>document\.write\(t\('browser_reader\.([^']+)'\)\);</script>", 
                     lambda m: f"{{t('browser_reader.{m.group(1)}')}}", html)
        
        # 然后在JavaScript中添加一个函数来处理这些占位符
        placeholder_script = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // 替换所有翻译占位符
            function replacePlaceholders() {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );

                let node;
                while (node = walker.nextNode()) {
                    const text = node.textContent;
                    if (text.includes('{t(') && text.includes(')}')) {
                        // 替换翻译占位符
                        const newText = text.replace(/{t\('([^']+)'\)}/g, function(match, key) {
                            return t(key);
                        });
                        node.textContent = newText;
                    }
                }
            }

            replacePlaceholders();
        });
        </script>
        """

        # 标题切换脚本
        title_change_script = """
        <script>
        // 保存原始标题
        let originalTitle = document.title;

        // 设置离开时的标题
        const hiddenTitle = "百度一下，你就知道";

        // 监听可见性变化
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                // 页面隐藏时修改标题
                document.title = hiddenTitle;
            } else {
                // 页面恢复可见时还原标题
                document.title = originalTitle;
            }
        });

        // 监听页面关闭/刷新，避免标题被缓存导致还原异常
        window.addEventListener('beforeunload', function() {
            document.title = originalTitle;
        });
        </script>
        """

        # 在</body>前插入脚本
        html = html.replace('</body>', placeholder_script + title_change_script + '</body>')
        

        # Python端翻译处理 - 替换所有{t('browser_reader.xxx')}占位符
        def get_translation(key):
            keys = key.split('.')
            value = BrowserReader.get_translations()
            for k in keys:
                value = value.get(k) if isinstance(value, dict) else None
                if value is None:
                    break
            return value or key
        
        # 使用正则表达式替换所有翻译占位符
        html = re.sub(r"\{t\('([^']+)'\)\}", lambda m: get_translation(m.group(1)), html)
        
        return html

    
    @staticmethod
    def read_file_content(file_path: str) -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 根据文件扩展名处理内容
                ext = Path(file_path).suffix.lower()
                
                if ext == '.txt':
                    # TXT文件：智能识别章节标题并转换为HTML
                    paragraphs = content.split('\n')
                    html_content = ''

                    # 常见的章节标题模式
                    chapter_patterns = [
                        r'^第[零一二三四五六七八九十百千万\d]+\\s*[章节回篇部页]',  # 添加了 \\s* 以匹配可能存在的空格
                        r'^Chapter\\s*\\d+',
                        r'^Part\\s*\\d+',
                        r'^第\\d+\\s*[章节回篇部页]',  # 添加了 \\s* 以匹配可能存在的空格
                        r'^[零一二三四五六七八九十百千万]+、',
                        r'^[一二三四五六七八九十]+、',
                        r'^\\d+[\\.、\\s]+[^\\s]+',
                        r'^卷[一二三四五六七八九十百千万\\d]+',
                        r'^篇[一二三四五六七八九十百千万\\d]+',
                        r'^序\\s*[言章篇页]',
                        r'^前\\s*言',
                        r'^引\\s*言',
                        r'^楔\\s*子',
                        r'^尾声',
                        r'^后记',
                        r'^【.*】',
                        r'^\\[.*\\]',
                        r'^<.*>',
                        r'^=+\\s*.*\\s*=+',  # Markdown风格的h1
                        r'^-+\\s*.*\\s*-',   # Markdown风格的h2
                    ]

                    import re

                    for para in paragraphs:
                        para = para.strip()
                        if not para:
                            continue

                        # 检查是否是章节标题
                        is_chapter = False
                        for pattern in chapter_patterns:
                            if re.match(pattern, para, re.IGNORECASE):
                                # 判断标题级别
                                if re.match(r'^第[零一二三四五六七八九十百千万\d]+\\s*[章节回篇部页]', para) or re.match(r'^Chapter\\s*\\d+', para, re.IGNORECASE) or re.match(r'^卷[一二三四五六七八九十百千万\\d]+', para):
                                    html_content += f'<h1>{para}</h1>'
                                elif re.match(r'^第\\d+\\s*[章节回篇部页]', para) or re.match(r'^Part\\s*\\d+', para, re.IGNORECASE) or re.match(r'^篇[一二三四五六七八九十百千万\\d]+', para):
                                    html_content += f'<h2>{para}</h2>'
                                elif re.match(r'^[零一二三四五六七八九十]+、', para) or re.match(r'^[一二三四五六七八九十]+、', para):
                                    html_content += f'<h3>{para}</h3>'
                                else:
                                    html_content += f'<h3>{para}</h3>'
                                is_chapter = True
                                break

                        if not is_chapter:
                            html_content += f'<p>{para}</p>'

                    # 如果没有识别到任何章节标题，尝试自动分段
                    if '<h1>' not in html_content and '<h2>' not in html_content and '<h3>' not in html_content:
                        # 统计段落数量
                        paragraph_count = html_content.count('<p>')
                        logger.info(f'未识别到章节标题，共有 {paragraph_count} 个段落')

                        # 如果段落数量大于20，尝试按照固定间隔添加章节标记
                        if paragraph_count > 20:
                            logger.info('段落数量较多，尝试自动分段')
                            paragraphs_with_chapters = html_content.split('<p>')
                            html_content_new = ''

                            # 每10个段落添加一个章节标题
                            chapter_num = 1
                            for i, para in enumerate(paragraphs_with_chapters):
                                if i == 0:
                                    continue  # 跳过第一个空段落

                                # 每10个段落添加章节标记
                                if (i - 1) % 10 == 0 and i > 1:
                                    html_content_new += f'<h3>章节 {chapter_num}</h3>'
                                    chapter_num += 1

                                if para:
                                    html_content_new += f'<p>{para}'

                            html_content = html_content_new

                    return html_content
                    
                elif ext == '.md':
                    # Markdown文件：智能识别章节标题并转换为HTML
                    paragraphs = content.split('\n')
                    html_content = ''

                    # 常见的章节标题模式
                    chapter_patterns = [
                        r'^第[零一二三四五六七八九十百千万\d]+[章节回篇部页]',
                        r'^Chapter\\s*\\d+',
                        r'^Part\\s*\\d+',
                        r'^第\\d+[章节回篇部页]',
                        r'^[零一二三四五六七八九十]+、',
                        r'^[一二三四五六七八九十]+、',
                        r'^\\d+[\\.、\\s]+[^\\s]+',
                        r'^卷[一二三四五六七八九十百千万\\d]+',
                        r'^篇[一二三四五六七八九十百千万\\d]+',
                        r'^序\\s*[言章篇页]',
                        r'^前\\s*言',
                        r'^引\\s*言',
                        r'^楔\\s*子',
                        r'^尾声',
                        r'^后记',
                        r'^【.*】',
                        r'^\\[.*\\]',
                        r'^<.*>',
                    ]

                    import re

                    for line in paragraphs:
                        line = line.strip()
                        if not line:
                            continue

                        # 检查是否是Markdown标准标题
                        if line.startswith('###'):
                            # 三级标题
                            title = line.lstrip('#').strip()
                            html_content += f'<h3>{title}</h3>'
                        elif line.startswith('##'):
                            # 二级标题
                            title = line.lstrip('#').strip()
                            html_content += f'<h2>{title}</h2>'
                        elif line.startswith('#'):
                            # 一级标题
                            title = line.lstrip('#').strip()
                            html_content += f'<h1>{title}</h1>'
                        else:
                            # 检查是否是章节标题
                            is_chapter = False
                            for pattern in chapter_patterns:
                                if re.match(pattern, line, re.IGNORECASE):
                                    # 判断标题级别
                                    if re.match(r'^第[零一二三四五六七八九十百千万\d]+[章节回篇部页]', line) or re.match(r'^Chapter\\s*\\d+', line, re.IGNORECASE) or re.match(r'^卷[一二三四五六七八九十百千万\\d]+', line):
                                        html_content += f'<h1>{line}</h1>'
                                    elif re.match(r'^第\\d+[章节回篇部页]', line) or re.match(r'^Part\\s*\\d+', line, re.IGNORECASE) or re.match(r'^篇[一二三四五六七八九十百千万\\d]+', line):
                                        html_content += f'<h2>{line}</h2>'
                                    elif re.match(r'^[零一二三四五六七八九十]+、', line) or re.match(r'^[一二三四五六七八九十]+、', line):
                                        html_content += f'<h3>{line}</h3>'
                                    else:
                                        html_content += f'<h3>{line}</h3>'
                                    is_chapter = True
                                    break

                            if not is_chapter:
                                html_content += f'<p>{line}</p>'

                    # 如果没有识别到任何章节标题，尝试自动分段
                    if '<h1>' not in html_content and '<h2>' not in html_content and '<h3>' not in html_content:
                        # 统计段落数量
                        paragraph_count = html_content.count('<p>')
                        logger.info(f'未识别到章节标题，共有 {paragraph_count} 个段落')

                        # 如果段落数量大于20，尝试按照固定间隔添加章节标记
                        if paragraph_count > 20:
                            logger.info('段落数量较多，尝试自动分段')
                            paragraphs_with_chapters = html_content.split('<p>')
                            html_content_new = ''

                            # 每10个段落添加一个章节标题
                            chapter_num = 1
                            for i, para in enumerate(paragraphs_with_chapters):
                                if i == 0:
                                    continue  # 跳过第一个空段落

                                # 每10个段落添加章节标记
                                if (i - 1) % 10 == 0 and i > 1:
                                    html_content_new += f'<h3>章节 {chapter_num}</h3>'
                                    chapter_num += 1

                                if para:
                                    html_content_new += f'<p>{para}'

                            html_content = html_content_new

                    return html_content
                    
                else:
                    # 其他格式：直接返回，将换行转换为段落
                    lines = content.split('\n')
                    html_content = ''
                    for line in lines:
                        line = line.strip()
                        if line:
                            html_content += f'<p>{line}</p>'
                    return html_content
                    
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                    paragraphs = content.split('\n')
                    html_content = ''
                    for para in paragraphs:
                        para = para.strip()
                        if para:
                            html_content += f'<p>{para}</p>'
                    return html_content
            except Exception:
                return f'<p>无法读取文件：{file_path}</p>'
        except Exception as e:
            return f'<p>读取文件时出错：{str(e)}</p>'
    
    @staticmethod
    def open_book_in_browser(file_path: str, theme: str = "light",
                          custom_settings: Optional[Dict[str, str]] = None,
                          on_progress_save: Optional[Callable[[float, int, int], None]] = None,
                          on_progress_load: Optional[Callable[[], Optional[Dict[str, Any]]]] = None):
        """
        在浏览器中打开书籍，支持进度同步
        
        Args:
            file_path: 书籍文件路径
            theme: 主题名称
            custom_settings: 自定义设置
            on_progress_save: 进度保存回调函数(progress, scrollTop, scrollHeight)
            on_progress_load: 进度加载回调函数，返回进度数据字典
            
        Returns:
            (success: bool, message: str)
        """
        try:
            # 清理旧的服务器
            BrowserReader._cleanup_old_servers()

            # 检查文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在：{file_path}")

            # 获取书籍标题
            title = Path(file_path).stem
            
            # 读取文件内容
            content = BrowserReader.read_file_content(file_path)
            
            # 获取browser_server配置
            browser_server_host = "localhost"
            browser_server_port = 54321
            try:
                from src.config.config_manager import ConfigManager
                config_manager = ConfigManager.get_instance()
                config = config_manager.get_config()
                browser_server_config = config.get("browser_server", {})
                browser_server_host = browser_server_config.get("host", "localhost")
                browser_server_port = browser_server_config.get("port", 54321)
            except Exception as e:
                logger.warning(f"无法获取browser_server配置，使用默认值: {e}")
            
            # 如果需要进度同步，启动HTTP服务器
            save_url = None
            load_url = None
            server = None
            server_thread = None
            server_id = None

            if on_progress_save or on_progress_load:
                save_url, load_url, server, server_thread = BrowserReader._start_progress_server(
                    file_path, on_progress_save, on_progress_load
                )
            # 使用全局浏览器阅读器服务器
            save_url = None
            load_url = None
            
            try:
                from src.utils.browser_reader_server_manager import get_browser_reader_server_manager
                server_manager = get_browser_reader_server_manager()
                
                # 确保服务器正在运行
                if not server_manager.is_server_running():
                    logger.info("全局服务器未运行，尝试启动...")
                    server_started = server_manager.start_server()
                    if server_started:
                        logger.info("全局服务器启动成功")
                        # 等待一下确保服务器完全启动
                        time.sleep(0.5)
                    else:
                        logger.error("全局服务器启动失败")
                        # 启动失败，继续尝试启动独立服务器
                        pass
                else:
                    logger.info("全局服务器已在运行")
                
                # 获取服务器URL
                save_url, load_url = server_manager.get_server_urls()
                logger.info(f"获取到的服务器URL - save_url: {save_url}, load_url: {load_url}")
                logger.info(f"服务器状态 - running: {server_manager.is_server_running()}, server: {server_manager._server}")
                
                if save_url and load_url:
                    # 注册书籍特定的回调
                    if on_progress_save or on_progress_load:
                        # 使用文件路径作为书籍ID
                        book_id = Path(file_path).stem
                        server_manager.register_callbacks(book_id, on_progress_save, on_progress_load)
                    
                    logger.info(f"使用全局浏览器阅读器服务器: {save_url}")
                else:
                    logger.warning("无法获取服务器URL，尝试启动独立服务器")
                    # 如果全局服务器不可用，启动独立服务器
                    save_url, load_url, server, server_thread = BrowserReader._start_progress_server(
                        file_path, on_progress_save, on_progress_load
                    )
                    if save_url and load_url:
                        # 保存服务器对象到全局字典，防止被垃圾回收
                        server_id = str(uuid.uuid4())
                        _active_servers[server_id] = {
                            'server': server,
                            'server_thread': server_thread,
                            'file_path': file_path,
                            'created_at': time.time()
                        }
                        logger.info(f"已启动独立服务器: {save_url}")
                
            except Exception as e:
                logger.error(f"获取或启动浏览器阅读器服务器失败: {e}", exc_info=True)
                # 最后的回退：尝试启动独立服务器
                try:
                    save_url, load_url, server, server_thread = BrowserReader._start_progress_server(
                        file_path, on_progress_save, on_progress_load
                    )
                    if save_url and load_url:
                        server_id = str(uuid.uuid4())
                        _active_servers[server_id] = {
                            'server': server,
                            'server_thread': server_thread,
                            'file_path': file_path,
                            'created_at': time.time()
                        }
                        logger.info(f"已启动备用服务器: {save_url}")
                except Exception as e2:
                    logger.error(f"启动备用服务器也失败: {e2}")
                    save_url = None
                    load_url = None
                # 保存服务器对象到全局字典，防止被垃圾回收
                server_id = str(uuid.uuid4())
                _active_servers[server_id] = {
                    'server': server,
                    'server_thread': server_thread,
                    'file_path': file_path,
                    'created_at': time.time()
                }
                logger.info(f"已保存服务器对象到全局字典，server_id={server_id}")
            
            # 获取书籍ID和初始进度
            book_id = Path(file_path).stem
            initial_progress = None
            
            # 如果有进度加载回调，尝试获取初始进度
            if on_progress_load:
                try:
                    progress_data = on_progress_load()
                    if progress_data and progress_data.get('progress') is not None:
                        initial_progress = float(progress_data['progress'])
                        logger.info(f"从Python端获取到初始进度: {initial_progress * 100:.2f}%")
                except Exception as e:
                    logger.warning(f"获取初始进度失败: {e}")
            
            # 创建HTML
            html = BrowserReader.create_reader_html(
                content, title, theme, custom_settings, save_url, load_url,
                book_id, initial_progress, browser_server_host, browser_server_port
            )
            
            # 创建临时HTML文件
            temp_dir = tempfile.gettempdir()
            html_filename = f"{title}_reader.html"
            html_path = os.path.join(temp_dir, html_filename)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)

            # 使用BrowserManager打开浏览器
            try:
                from src.utils.browser_manager import BrowserManager
                
                # 使用默认浏览器打开HTML文件
                success = BrowserManager.open_file(html_path)
                if success:
                    browser_name = BrowserManager.get_default_browser()
                    logger.info(f"使用 {browser_name} 浏览器打开书籍: {html_path}")
                else:
                    # 回退到默认浏览器
                    webbrowser.open(f'file://{html_path}')
                    logger.warning(f"使用系统默认浏览器打开: {html_path}")
            except Exception as e:
                # 如果BrowserManager失败，回退到默认浏览器
                webbrowser.open(f'file://{html_path}')
                logger.warning(f"BrowserManager失败，使用系统默认浏览器打开: {e}")

            return True, f"已在浏览器中打开：{title}"

        except Exception as e:
            return False, f"打开书籍失败：{str(e)}"
    
    @staticmethod
    def _start_progress_server(file_path: str,
                           on_progress_save: Optional[Callable[[float, int, int], None]],
                           on_progress_load: Optional[Callable[[], Optional[Dict[str, Any]]]]):
        """
        启动进度同步服务器
        
        Args:
            file_path: 文件路径（用于标识书籍）
            on_progress_save: 进度保存回调
            on_progress_load: 进度加载回调
            
        Returns:
            (save_url, load_url, server, server_thread)
        """
        import random
        from src.config.config_manager import ConfigManager
        
        # 获取配置管理器
        config_manager = ConfigManager.get_instance()
        config = config_manager.get_config()
        browser_server_config = config.get("browser_server", {})
        
        # 获取配置
        host = browser_server_config.get("host", "localhost")
        port = browser_server_config.get("port", 54321)
        port_range_min = browser_server_config.get("port_range_min", 10000)
        port_range_max = browser_server_config.get("port_range_max", 60000)
        max_retry = browser_server_config.get("max_retry_attempts", 10)
        enable_fixed_port = browser_server_config.get("enable_fixed_port", True)
        fixed_port = browser_server_config.get("fixed_port", 54321)
        
        # 确定最终端口
        if port == 0:
            # 端口为0时，随机分配端口
            final_port = random.randint(port_range_min, port_range_max)
            logger.info(f"端口设置为0，使用随机端口: {final_port}")
        else:
            final_port = port
            logger.info(f"使用指定端口: {final_port}")
        
        # 检测端口是否可用
        if enable_fixed_port and final_port == fixed_port:
            # 固定端口模式：如果端口被占用，直接失败（让上层处理）
            if not BrowserReader._is_port_available(host, final_port):
                logger.error(f"固定端口 {host}:{final_port} 被占用")
                return None, None, None, None
            else:
                logger.info(f"固定端口 {host}:{final_port} 可用")
                port = final_port
        else:
            # 非固定端口模式：检测端口是否可用，如果不可用则重试
            for attempt in range(max_retry):
                if BrowserReader._is_port_available(host, final_port):
                    logger.info(f"端口 {host}:{final_port} 可用")
                    port = final_port
                    break
                else:
                    logger.warning(f"端口 {host}:{final_port} 被占用，尝试其他端口")
                    if port == 0:
                        # 原本就是随机端口，继续随机
                        final_port = random.randint(port_range_min, port_range_max)
                    else:
                        # 指定端口被占用，也使用随机端口
                        final_port = random.randint(port_range_min, port_range_max)
            else:
                logger.error(f"经过 {max_retry} 次重试仍找不到可用端口")
                return None, None, None, None
        
        # 存储进度数据
        progress_data = {}
        
        # 创建请求处理器
        class ProgressHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # 禁用日志输出
            
            def do_GET(self):
                if self.path == '/load_progress':
                    # 加载进度
                    if on_progress_load:
                        data = on_progress_load()
                        logger.info(f"从数据库加载进度数据: {data}")
                        if data:
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps(data).encode())
                        else:
                            self.send_response(404)
                            self.end_headers()
                elif self.path == '/health_check':
                    # 健康检查
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode())
                elif self.path.startswith('/src/locales/'):
                    # 提供静态文件访问（翻译文件）
                    self.serve_static_file(self.path[1:])  # 移除开头的 /
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def serve_static_file(self, relative_path):
                """提供静态文件访问"""
                try:
                    # 构建绝对路径
                    base_path = Path(__file__).parent.parent
                    file_path = base_path / relative_path
                    
                    if file_path.exists() and file_path.is_file():
                        # 读取文件内容
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # 设置正确的Content-Type
                        if file_path.suffix == '.json':
                            content_type = 'application/json; charset=utf-8'
                        else:
                            content_type = 'text/plain; charset=utf-8'
                        
                        self.send_response(200)
                        self.send_header('Content-Type', content_type)
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(content.encode('utf-8'))
                    else:
                        self.send_response(404)
                        self.end_headers()
                except Exception as e:
                    logger.error(f"静态文件访问错误: {e}")
                    self.send_response(500)
                    self.end_headers()
            
            def do_POST(self):
                if self.path == '/save_progress':
                    # 保存进度
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)

                    try:
                        raw_json = post_data.decode('utf-8')
                        data = json.loads(raw_json)

                        progress_raw = data.get('progress', 0)
                        scroll_top = int(data.get('scrollTop', 0))
                        scroll_height = int(data.get('scrollHeight', 0))

                        logger.info(f"接收到保存进度请求:")
                        logger.info(f"  - 原始JSON字符串: {raw_json}")
                        logger.info(f"  - 解析后的data: {data}")
                        logger.info(f"  - progress原始值: {progress_raw}, 类型: {type(progress_raw)}")

                        # 转换为float
                        progress = float(progress_raw)
                        logger.info(f"  - progress转换后: {progress}, 类型: {type(progress)}")
                        logger.info(f"  - scrollTop: {scroll_top}px")
                        logger.info(f"  - scrollHeight: {scroll_height}px")

                        # 获取额外信息
                        current_page = int(data.get('current_page', 0))
                        total_pages = int(data.get('total_pages', 0))
                        word_count = int(data.get('word_count', 0))

                        logger.info(f"  - current_page: {current_page}, total_pages: {total_pages}, word_count: {word_count}")

                        if on_progress_save:
                            on_progress_save(progress, scroll_top, scroll_height,
                                              current_page, total_pages, word_count)

                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success"}).encode())
                    except Exception as e:
                        logger.error(f"保存进度出错: {e}")
                        self.send_response(500)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_OPTIONS(self):
                # CORS预检请求
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
        
        # 启动服务器
        def try_start_server(port_to_try, server_host):
            """尝试在指定端口启动服务器"""
            try:
                server = HTTPServer((server_host, port_to_try), ProgressHandler)
                server_thread = Thread(target=server.serve_forever, daemon=True)
                server_thread.start()
                
                save_url = f"http://{server_host}:{port_to_try}/save_progress"
                load_url = f"http://{server_host}:{port_to_try}/load_progress"
                
                logger.info(f"浏览器阅读器服务器已启动: {server_host}:{port_to_try}")
                return save_url, load_url, server, server_thread
            except OSError as e:
                logger.warning(f"端口 {port_to_try} 启动失败: {e}")
                return None
        
        # 首先尝试初始端口
        result = try_start_server(port, host)
        if result:
            # 如果是固定端口且成功启动，保存配置
            if enable_fixed_port and fixed_port > 0 and port == fixed_port:
                logger.info(f"固定端口 {fixed_port} 启动成功")
            return result[0], result[1], result[2], result[3]
        
        # 如果固定端口启动失败，尝试其他端口
        if enable_fixed_port and fixed_port > 0 and port == fixed_port:
            logger.warning(f"固定端口 {fixed_port} 被占用，尝试其他端口")
            
            # 尝试端口范围内的随机端口
            for attempt in range(max_retry):
                fallback_port = random.randint(port_range_min, port_range_max)
                result = try_start_server(fallback_port, host)
                if result:
                    logger.info(f"使用备用端口 {fallback_port} 启动服务器")
                    return result[0], result[1], result[2], result[3]
            
            # 如果指定范围内都失败，扩大范围再尝试
            logger.warning("指定端口范围内都无可用的端口，扩大范围尝试")
            for attempt in range(5):
                fallback_port = random.randint(8000, 65000)
                result = try_start_server(fallback_port, host)
                if result:
                    logger.info(f"使用扩展范围端口 {fallback_port} 启动服务器")
                    return result[0], result[1], result[2], result[3]
        else:
            # 随机端口失败，继续尝试其他随机端口
            for attempt in range(max_retry - 1):
                fallback_port = random.randint(port_range_min, port_range_max)
                result = try_start_server(fallback_port, host)
                if result:
                    return result[0], result[1], result[2], result[3]
        
        # 所有尝试都失败
        logger.error("无法启动浏览器阅读器服务器，所有端口都被占用")
        return None, None, None, None

    @staticmethod
    def _is_port_available(host: str, port: int) -> bool:
        """
        检测端口是否可用
        
        Args:
            host: 主机地址
            port: 端口号
            
        Returns:
            bool: 端口是否可用
        """
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # 连接失败表示端口可用
        except Exception:
            return False
    
    @staticmethod
    def _resolve_host_address(host_config: str, custom_host: str) -> str:
        """
        解析主机地址
        
        Args:
            host_config: 主机配置值
            custom_host: 自定义主机地址
            
        Returns:
            str: 解析后的主机地址
        """
        if host_config == "custom" and custom_host:
            return custom_host.strip()
        elif host_config == "0.0.0.0":
            return "0.0.0.0"
        elif host_config == "127.0.0.1":
            return "127.0.0.1"
        else:
            return "localhost"
    
    @staticmethod
    def get_server_info() -> Dict[str, Any]:
        """
        获取浏览器阅读器服务器配置信息
        
        Returns:
            Dict[str, Any]: 服务器配置信息
        """
        from src.config.config_manager import ConfigManager
        
        config_manager = ConfigManager.get_instance()
        config = config_manager.get_config()
        browser_server_config = config.get("browser_server", {})
        
        return {
            "host": browser_server_config.get("host", "localhost"),
            "port": browser_server_config.get("port", 54321),
            "port_range_min": browser_server_config.get("port_range_min", 10000),
            "port_range_max": browser_server_config.get("port_range_max", 60000),
            "max_retry_attempts": browser_server_config.get("max_retry_attempts", 10),
        }
    
    @staticmethod
    def update_server_config(config: Dict[str, Any]) -> bool:
        """
        更新浏览器阅读器服务器配置
        
        Args:
            config: 新的配置字典
            
        Returns:
            bool: 更新是否成功
        """
        from src.config.config_manager import ConfigManager
        
        try:
            config_manager = ConfigManager.get_instance()
            full_config = config_manager.get_config()
            current_config = full_config.get("browser_server", {})
            
            # 合并配置
            current_config.update(config)
            full_config["browser_server"] = current_config
            config_manager.save_config(full_config)
            
            logger.info(f"浏览器服务器配置已更新: {config}")
            return True
        except Exception as e:
            logger.error(f"更新浏览器服务器配置失败: {e}")
            return False

    @staticmethod
    def _cleanup_old_servers(max_age_hours: int = 24) -> None:
        """
        清理旧的服务器对象，释放资源

        Args:
            max_age_hours: 服务器最大存活时间（小时）
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600

            # 找出所有过期的服务器
            expired_servers = [
                server_id for server_id, server_info in _active_servers.items()
                if current_time - server_info['created_at'] > max_age_seconds
            ]

            # 关闭并删除过期的服务器
            for server_id in expired_servers:
                try:
                    server_info = _active_servers[server_id]
                    server_info['server'].shutdown()
                    server_info['server'].server_close()
                    del _active_servers[server_id]
                    logger.info(f"已清理过期服务器: server_id={server_id}, file_path={server_info['file_path']}")
                except Exception as e:
                    logger.error(f"清理服务器失败: server_id={server_id}, error={e}")
                    del _active_servers[server_id]

            if expired_servers:
                logger.info(f"已清理 {len(expired_servers)} 个过期服务器，当前活跃服务器数: {len(_active_servers)}")
        except Exception as e:
            logger.error(f"清理服务器失败: {e}")