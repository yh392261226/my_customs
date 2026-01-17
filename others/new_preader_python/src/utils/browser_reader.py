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
                        load_progress_url: Optional[str] = None) -> str:
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
        
        # 生成HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 浏览器阅读器</title>
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
        }}

        .settings-panel:hover {{
            background: rgba(255, 255, 255, 1);
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 2000;
            width: 90%;
            max-width: 500px;
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
            left: 80px;
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
        
        /* 书页翻页效果 - 更逼真的实现 */
        .page-content.book-flip {{
            position: relative;
            transform-style: preserve-3d;
            perspective: 2000px;
            backface-visibility: hidden;
            will-change: transform;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        .page-content.book-flip-next {{
            animation: bookFlipNext 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}
        
        .page-content.book-flip-prev {{
            animation: bookFlipPrev 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }}
        
        /* 书页翻页动画 */
        @keyframes bookFlipNext {{
            0% {{
                transform: rotateY(0deg) rotateX(0deg);
                transform-origin: right bottom;
            }}
            25% {{
                transform: rotateY(30deg) rotateX(-5deg);
                transform-origin: right bottom;
            }}
            50% {{
                transform: rotateY(90deg) rotateX(-10deg);
                transform-origin: right bottom;
            }}
            75% {{
                transform: rotateY(150deg) rotateX(-5deg);
                transform-origin: right bottom;
            }}
            100% {{
                transform: rotateY(180deg) rotateX(0deg);
                transform-origin: right bottom;
            }}
        }}
        
        @keyframes bookFlipPrev {{
            0% {{
                transform: rotateY(0deg) rotateX(0deg);
                transform-origin: left bottom;
            }}
            25% {{
                transform: rotateY(-30deg) rotateX(-5deg);
                transform-origin: left bottom;
            }}
            50% {{
                transform: rotateY(-90deg) rotateX(-10deg);
                transform-origin: left bottom;
            }}
            75% {{
                transform: rotateY(-150deg) rotateX(-5deg);
                transform-origin: left bottom;
            }}
            100% {{
                transform: rotateY(-180deg) rotateX(0deg);
                transform-origin: left bottom;
            }}
        }}
        
        /* 书页弯曲效果 */
        .page-curve {{
            position: absolute;
            top: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, 
                transparent 0%, 
                rgba(0,0,0,0.1) 45%, 
                rgba(0,0,0,0.2) 50%, 
                rgba(0,0,0,0.1) 55%, 
                transparent 100%);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .page-curve.active {{
            opacity: 1;
        }}
        
        /* 书页阴影效果 */
        .page-book-shadow {{
            position: absolute;
            top: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 10;
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
    </style>
</head>
<body>
    <!-- 全屏状态指示器 -->
    <div class="fullscreen-indicator" id="fullscreenIndicator">
        全屏模式 (按 ESC 退出)
    </div>
    
    <!-- 进度条 -->
    <div class="progress-bar">
        <div class="progress-fill" id="progressFill"></div>
    </div>
    
    <!-- 进度信息 -->
    <div class="progress-info" id="progressInfo">进度: 0%</div>

    <!-- 缩略图导航 -->
    <div class="minimap-container" id="minimapContainer">
        <div class="minimap-content" id="minimapContent">
            <div class="minimap-viewport" id="minimapViewport"></div>
        </div>
    </div>

    <!-- 缩略图切换按钮 -->
    <div class="minimap-toggle" id="minimapToggle" onclick="toggleMinimap()" title="缩略图导航">
        📍
    </div>

    <!-- 快捷键提示 -->
    <div class="keyboard-hint" id="keyboardHint">
        <h4>快捷键</h4>
        <ul>
            <li><kbd>+</kbd>/<kbd>-</kbd> 字体大小</li>
            <li><kbd>↑</kbd>/<kbd>↓</kbd> 翻页</li>
            <li><kbd>PageUp</kbd>/<kbd>PageDown</kbd> 上下翻页</li>
            <li><kbd>Home</kbd>/<kbd>End</kbd> 首尾</li>
            <li><kbd>c</kbd> 章节目录</li>
            <li><kbd>s</kbd> 搜索</li>
            <li><kbd>b</kbd> 书签</li>
            <li><kbd>f</kbd> 全屏</li>
            <li><kbd>F</kbd> 专注模式</li>
            <li><kbd>a</kbd> 自动滚动</li>
            <li><kbd>Space</kbd> 朗读选中内容</li>
            <li><kbd>h</kbd> 隐藏提示</li>
            <li><kbd>g</kbd> 字体设置</li>
            <li><kbd>n</kbd> 笔记/高亮</li>
            <li><kbd>m</kbd> 缩略图导航</li>
            <li><kbd>ESC</kbd> 退出全屏/专注模式</li>
        </ul>
    </div>

    <!-- 阅读统计 -->
    <div class="reading-stats" id="readingStats">
        <p>阅读时间: <span id="readingTime">0:00</span></p>
        <p>已读字数: <span id="wordCount">0</span></p>
        <p>阅读速度: <span id="readingSpeed">0</span> 字/分</p>
    </div>
    
    <!-- 增强的阅读统计面板 -->
    <div class="reading-stats-enhanced" id="readingStatsEnhanced">
        <h4>阅读统计</h4>
        <p>总阅读时间: <span class="stat-value" id="totalReadingTime">0:00</span></p>
        <p>本次阅读时间: <span class="stat-value" id="sessionReadingTime">0:00</span></p>
        <p>已读字数: <span class="stat-value" id="totalWordCount">0</span></p>
        <p>阅读进度: <span class="stat-value" id="readingProgress">0%</span></p>
        <p>平均阅读速度: <span class="stat-value" id="avgReadingSpeed">0</span> 字/分</p>
        <p>预计剩余时间: <span class="stat-value" id="estimatedTimeLeft">--</span></p>
    </div>
    
    <!-- 夜间模式切换 -->
    <div class="night-mode-toggle" id="nightModeToggle" onclick="toggleNightMode()">
        <span id="nightModeIcon">🌙</span>
        <span id="nightModeText">夜间模式</span>
    </div>
    
    <!-- 翻页模式切换 -->
    <div class="pagination-mode-toggle" id="paginationModeToggle" onclick="togglePaginationMode()">
        <span id="paginationModeIcon">📖</span>
        <span id="paginationModeText">翻页模式</span>
    </div>
    
    <!-- 工具栏 -->
    <div class="toolbar" id="toolbar">
        <button onclick="changeFontSize(-2)">A-</button>
        <button onclick="changeFontSize(2)">A+</button>

        <label>
            主题：
            <select id="themeSelect" onchange="changeTheme(this.value)">
                <option value="light">浅色</option>
                <option value="dark">深色</option>
                <option value="sepia">羊皮纸</option>
                <option value="matrix">黑客绿</option>
                <option value="ocean">海洋蓝</option>
                <option value="forest">森林绿</option>
                <option value="warm">暖色调</option>
                <option value="purple">紫罗兰</option>
                <option value="custom">自定义</option>
            </select>
            <button onclick="showThemeManager()" style="margin-left: 5px; padding: 4px 8px; font-size: 12px;">主题管理</button>
        </label>

        <label>
            行高：
            <input type="range" min="1.2" max="2.5" step="0.1" value="{settings['line_height']}" onchange="changeLineHeight(this.value)">
        </label>

        <button onclick="toggleFontSettings()">字体</button>
        <button onclick="toggleHighlightMode()">高亮</button>
        <button onclick="toggleNotesMode()">笔记</button>
        <button onclick="toggleSearch()">搜索</button>
        <button onclick="toggleAutoScrollPanel()">自动滚动</button>
        <button onclick="toggleSpeech()">朗读设置</button>
        <button onclick="toggleReadingStats()">统计</button>
        <button onclick="togglePaginationSettings()">翻页设置</button>
        <button onclick="toggleFocusMode()">专注模式</button>
        <button onclick="toggleFullscreen()">全屏</button>
        <button onclick="scrollToTop()">顶部</button>
        <button onclick="scrollToBottom()">底部</button>
        <button onclick="printContent()">打印</button>
        <button onclick="toggleMinimap()" id="minimapToolbarBtn">缩略图</button>
        <button onclick="toggleTOC()">目录</button>
    </div>

    <!-- 工具栏收缩/展开按钮 -->
    <div class="toolbar-toggle-container" id="toolbarToggleContainer">
        <button class="toolbar-toggle-btn" onclick="toggleToolbar()" title="收缩/展开工具栏">
            <span id="toolbarToggleIcon">︽</span>
        </button>
    </div>

    <!-- 字体设置面板 -->
    <div class="settings-panel" id="fontSettingsPanel" style="display: none;">
        <div class="settings-content">
            <h3>字体设置</h3>
            <button class="settings-close" onclick="toggleFontSettings()">×</button>

            <div class="setting-item">
                <label>字体：</label>
                <select id="fontFamilySelect" onchange="changeFontFamily(this.value)">
                    <option value="system">系统默认</option>
                    <option value="serif">宋体/衬线</option>
                    <option value="sans-serif">黑体/无衬线</option>
                    <option value="georgia">Georgia</option>
                    <option value="kai">楷体</option>
                    <option value="fangsong">仿宋</option>
                    <option value="monospace">等宽字体</option>
                </select>
            </div>

            <div class="setting-item">
                <label>加粗：</label>
                <button class="toggle-btn" id="boldBtn" onclick="toggleBold()">B</button>
            </div>

            <div class="setting-item">
                <label>倾斜：</label>
                <button class="toggle-btn" id="italicBtn" onclick="toggleItalic()">I</button>
            </div>

            <div class="setting-item">
                <label>下划线：</label>
                <button class="toggle-btn" id="underlineBtn" onclick="toggleUnderline()">U</button>
            </div>

            <div class="setting-item">
                <label>字体颜色：</label>
                <input type="color" id="fontColorInput" value="{settings['text']}" onchange="changeFontColor(this.value)">
            </div>

            <div class="setting-item">
                <label>背景颜色：</label>
                <input type="color" id="bgColorInput" value="{settings['background']}" onchange="changeBackgroundColor(this.value)">
            </div>

            <div class="setting-item">
                <label>字间距：</label>
                <input type="range" min="-2" max="5" step="0.5" value="{settings['letter_spacing']}" onchange="changeLetterSpacing(this.value)">
                <span id="letterSpacingValue">{settings['letter_spacing']}</span>
            </div>

            <div class="setting-item">
                <label>词间距：</label>
                <input type="range" min="-2" max="10" step="1" value="{settings['word_spacing']}" onchange="changeWordSpacing(this.value)">
                <span id="wordSpacingValue">{settings['word_spacing']}</span>
            </div>

            <div class="setting-item">
                <label>对齐方式：</label>
                <select id="textAlignSelect" onchange="changeTextAlign(this.value)">
                    <option value="left">左对齐</option>
                    <option value="center">居中</option>
                    <option value="right">右对齐</option>
                    <option value="justify">两端对齐</option>
                </select>
            </div>

            <div class="setting-actions">
                <button onclick="resetFontSettings()">重置</button>
                <button onclick="toggleFontSettings()">关闭</button>
            </div>
        </div>
    </div>

    <!-- 高亮和笔记面板 -->
    <div class="settings-panel" id="notesPanel" style="display: none;">
        <div class="settings-content">
            <h3 id="notesTitle">阅读助手</h3>
            <button class="settings-close" onclick="closeNotesPanel()">×</button>

            <div class="notes-tabs">
                <button class="tab-btn active" onclick="switchNotesTab('highlights')">高亮</button>
                <button class="tab-btn" onclick="switchNotesTab('bookmarks')">书签</button>
                <button class="tab-btn" onclick="switchNotesTab('notes')">笔记</button>
            </div>

            <div class="notes-content" id="highlightsTab">
                <div class="notes-list" id="highlightsList"></div>
                <div class="notes-hint">选中文字后点击高亮按钮添加高亮</div>
            </div>

            <div class="notes-content" id="bookmarksTab" style="display: none;">
                <div class="notes-list" id="bookmarksList"></div>
                <button onclick="addBookmark()" class="add-btn">添加当前书签</button>
            </div>

            <div class="notes-content" id="notesTab" style="display: none;">
                <textarea id="noteInput" placeholder="输入笔记内容..." rows="3"></textarea>
                <button onclick="addNote()" class="add-btn">添加笔记</button>
                <div class="notes-list" id="notesList"></div>
            </div>
        </div>
    </div>

    <!-- 搜索框 -->
    <div class="search-container" id="searchContainer">
        <input type="text" id="searchInput" placeholder="搜索内容..." onkeypress="handleSearchKeypress(event)">
        <button onclick="searchText()">搜索</button>
        <button onclick="searchNext()">下一个</button>
        <span class="search-count" id="searchCount"></span>
    </div>

    <!-- 目录切换按钮 -->
    <button class="toc-toggle-btn" onclick="toggleTOC()" title="目录">☰</button>

    <!-- 书签按钮 -->
    <button class="bookmark-btn" id="bookmarkBtn" onclick="toggleBookmark()" title="书签">🔖</button>

    <!-- 章节目录 -->
    <div class="toc-container" id="tocContainer">
        <div class="toc-header">
            <h3>章节目录</h3>
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
        <button onclick="toggleAutoScroll()" id="autoScrollToggleBtn">开始滚动</button>
        <button onclick="resetAutoScroll()">重置</button>
    </div>
    
    <!-- 朗读控制面板 -->
    <div class="speech-controls" id="speechControls">
        <button onclick="toggleSpeechPlayback()" id="speechPlaybackBtn">开始朗读</button>
        <select id="voiceSelect" onchange="changeVoice(this.value)">
            <option value="">选择语音</option>
        </select>
        <label>速度: <input type="range" id="speechRate" min="0.5" max="2" step="0.1" value="1" onchange="changeSpeechRate(this.value)"></label>
        <label>音调: <input type="range" id="speechPitch" min="0.5" max="2" step="0.1" value="1" onchange="changeSpeechPitch(this.value)"></label>
        <button onclick="stopSpeech()">停止</button>
        <span class="speech-status" id="speechStatus">未朗读</span>
    </div>
    
    <!-- 翻页容器 -->
    <div class="pagination-container" id="paginationContainer" style="display: none;">
        <div class="page-content" id="pageContent"></div>
    </div>
    
    <!-- 翻页控制按钮 -->
    <div class="pagination-controls" id="paginationControls" style="display: none;">
        <button onclick="previousPage()" id="prevPageBtn">上一页</button>
        <div class="page-info">
            <span id="currentPage">1</span> / <span id="totalPages">1</span>
        </div>
        <div class="page-jump">
            <input type="number" id="pageJumpInput" min="1" value="1" onchange="jumpToPage()">
            <button onclick="jumpToPage()">跳转</button>
        </div>
        <button onclick="nextPage()" id="nextPageBtn">下一页</button>
    </div>
    
    <!-- 翻页设置面板 -->
    <div class="pagination-settings" id="paginationSettings">
        <div class="pagination-settings-content">
            <h3>翻页设置</h3>
            <button class="pagination-settings-close" onclick="togglePaginationSettings()">×</button>
            
            <div class="setting-item">
                <label>翻页效果：</label>
                <select id="pageEffectSelect" onchange="changePageEffect(this.value)">
                    <option value="none">无效果</option>
                    <option value="slide">滑动效果</option>
                    <option value="fade">淡入淡出</option>
                    <option value="flip">翻转效果</option>
                    <option value="realistic">仿真翻页</option>
                    <option value="book">书页翻页</option>
                </select>
            </div>
            
            <div class="setting-item">
                <label>自动翻页：</label>
                <select id="autoPageTurnSelect" onchange="changeAutoPageTurn(this.value)">
                    <option value="off">关闭</option>
                    <option value="10">10秒</option>
                    <option value="15">15秒</option>
                    <option value="30">30秒</option>
                    <option value="60">60秒</option>
                </select>
            </div>
            
            <div class="setting-actions">
                <button onclick="resetPaginationSettings()">重置</button>
                <button onclick="togglePaginationSettings()">关闭</button>
            </div>
        </div>
    </div>
    
    <!-- 内容区域 -->
    <div class="content" id="content">
        {content}
    </div>
    
    <script>
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
        let saveProgressInterval = 3000; // 3秒保存一次

        // 标记:页面加载后短时间内禁用自动保存,避免恢复进度时触发错误保存
        let isPageLoading = true;
        let pageLoadStartTime = Date.now();
        const pageLoadCooldown = 3000; // 页面加载冷却时间3秒

        // 缓存上一次保存的进度值
        let cachedProgress = null;
        let cachedScrollTop = 0;
        let cachedScrollHeight = 0;
        
        // 进度API地址
        const SAVE_PROGRESS_URL = {f'"{save_progress_url}"' if save_progress_url else 'null'};
        const LOAD_PROGRESS_URL = {f'"{load_progress_url}"' if load_progress_url else 'null'};

        // 后端在线状态
        let isBackendOnline = true;

        // 检测后端是否在线
        async function checkBackendStatus() {{
            if (!SAVE_PROGRESS_URL && !LOAD_PROGRESS_URL) {{
                isBackendOnline = false;
                return false;
            }}

            try {{
                const checkUrl = SAVE_PROGRESS_URL || LOAD_PROGRESS_URL;
                const response = await fetch(checkUrl.replace(/save_progress|load_progress/, 'health_check'), {{
                    method: 'GET',
                    cache: 'no-cache',
                    timeout: 3000
                }}).catch(() => null);

                if (response && response.ok) {{
                    isBackendOnline = true;
                    return true;
                }} else {{
                    // 尝试HEAD请求作为备用检测
                    const headResponse = await fetch(checkUrl, {{
                        method: 'HEAD',
                        mode: 'no-cors',
                        cache: 'no-cache'
                    }}).catch(() => null);

                    isBackendOnline = headResponse !== null;
                    return isBackendOnline;
                }}
            }} catch (error) {{
                console.log('后端检测失败:', error);
                isBackendOnline = false;
                return false;
            }}
        }}

        // 获取后端状态提示
        function getBackendStatusText() {{
            return isBackendOnline ? '' : '（后端离线）';
        }}
        
        // 切换工具栏收缩/展开
        function toggleToolbar() {{
            const toolbar = document.getElementById('toolbar');
            const icon = document.getElementById('toolbarToggleIcon');
            
            toolbar.classList.toggle('collapsed');
            
            if (toolbar.classList.contains('collapsed')) {{
                icon.textContent = '︾';
                showNotification('工具栏已隐藏');
            }} else {{
                icon.textContent = '︽';
                showNotification('工具栏已展开');
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
                showNotification('已进入高亮模式，选中文字后点击添加高亮');
            }} else {{
                document.body.style.cursor = 'default';
                showNotification('已退出高亮模式');
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
                    showNotification('高亮已添加');
                }} catch (e) {{
                    console.error('添加高亮失败:', e);
                    showNotification('无法在此位置添加高亮');
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
                item.innerHTML = `
                    <div class="note-text">${{h.text.substring(0, 50)}}...</div>
                    <div class="note-time">位置: ${{h.position}}px</div>
                    <span class="note-delete" onclick="deleteHighlight(${{h.id}})">×</span>
                `;
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
                showNotification('请输入笔记内容');
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
            showNotification('笔记已添加');
        }}

        function updateNotesList() {{
            const list = document.getElementById('notesList');
            if (!list) return;

            list.innerHTML = '';
            notes.forEach(note => {{
                const item = document.createElement('div');
                item.className = 'note-item';
                item.innerHTML = `
                    <span class="note-delete" onclick="deleteNote(${{note.id}})">×</span>
                    <div class="note-text">${{note.text}}</div>
                    <div class="note-time">${{note.time}}</div>
                `;
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
            showNotification('笔记已删除');
        }}

        function updateBookmarksList() {{
            const list = document.getElementById('bookmarksList');
            if (!list) return;

            const savedBookmarks = JSON.parse(localStorage.getItem('reader_bookmarks') || '[]');
            list.innerHTML = '';

            savedBookmarks.forEach((bm, index) => {{
                const item = document.createElement('div');
                item.className = 'note-item';
                item.innerHTML = `
                    <span class="note-delete" onclick="deleteBookmark(${{bm.id}})">×</span>
                    <div class="note-text">书签 ${{index + 1}}</div>
                    <div class="note-time">${{new Date(bm.time).toLocaleString()}}</div>
                `;
                item.onclick = (e) => {{
                    if (e.target.className !== 'note-delete') {{
                        window.scrollTo({{ top: bm.position, behavior: 'smooth' }});
                    }}
                }};
                list.appendChild(item);
            }});
        }}

        function addBookmark() {{
            const savedBookmarks = JSON.parse(localStorage.getItem('reader_bookmarks') || '[]');

            const bookmark = {{
                id: Date.now(),
                position: Math.floor(window.scrollY),
                time: Date.now()
            }};

            savedBookmarks.push(bookmark);
            localStorage.setItem('reader_bookmarks', JSON.stringify(savedBookmarks));

            updateBookmarksList();
            showNotification('书签已添加');
        }}

        function deleteBookmark(id) {{
            const savedBookmarks = JSON.parse(localStorage.getItem('reader_bookmarks') || '[]');
            const filtered = savedBookmarks.filter(b => b.id !== id);
            localStorage.setItem('reader_bookmarks', JSON.stringify(filtered));
            updateBookmarksList();
            showNotification('书签已删除');
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
                    btn.style.cssText = `
                        position: fixed;
                        top: ${{rect.top - 40}}px;
                        left: ${{rect.left}}px;
                        background: rgba(100, 149, 237, 0.9);
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 4px;
                        cursor: pointer;
                        z-index: 2000;
                    `;
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
                themesHtml += `
                    <div class="theme-item" data-theme="${{name}}">
                        <div class="theme-name">${{name}}</div>
                        <div class="theme-preview" style="background: ${{customThemes[name].background}}; color: ${{customThemes[name].text}};">预览</div>
                        <div class="theme-actions">
                            <button onclick="loadCustomThemeByName('${{name}}')">加载</button>
                            <button onclick="deleteCustomTheme('${{name}}')">删除</button>
                        </div>
                    </div>
                `;
            }});
            
            if (themeNames.length === 0) {{
                themesHtml = '<div class="no-themes">暂无自定义主题</div>';
            }}
            
            const panel = document.createElement('div');
            panel.className = 'settings-panel theme-manager-panel';
            panel.innerHTML = `
                <div class="settings-content">
                    <h3>主题管理</h3>
                    <button class="settings-close" onclick="closeThemeManager()">×</button>
                    
                    <div class="theme-manager-content">
                        <div class="current-theme-info">
                            <h4>当前主题设置</h4>
                            <p>背景色: <span style="display: inline-block; width: 20px; height: 20px; background: ${{currentSettings.background}}; vertical-align: middle;"></span> ${{currentSettings.background}}</p>
                            <p>文字色: <span style="display: inline-block; width: 20px; height: 20px; background: ${{currentSettings.text}}; vertical-align: middle;"></span> ${{currentSettings.text}}</p>
                            <p>字体大小: ${{currentSettings.font_size}}px</p>
                            <p>行高: ${{currentSettings.line_height}}</p>
                        </div>
                        
                        <div class="theme-actions-top">
                            <button onclick="saveCustomThemeFromManager()">保存当前主题</button>
                        </div>
                        
                        <div class="themes-list">
                            <h4>已保存的主题</h4>
                            ${{themesHtml}}
                        </div>
                    </div>
                </div>
            `;
            
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
            const themeName = prompt('请输入自定义主题名称:', '我的主题');
            if (!themeName) {{
                showNotification('主题名称不能为空');
                return;
            }}

            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            customThemes[themeName] = {{...currentSettings}};
            localStorage.setItem('reader_custom_themes', JSON.stringify(customThemes));
            showNotification('主题已保存: ' + themeName);
        }}
        
        // 从主题管理器保存主题
        function saveCustomThemeFromManager() {{
            const themeName = prompt('请输入自定义主题名称:', '我的主题');
            if (!themeName) {{
                showNotification('主题名称不能为空');
                return;
            }}

            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            customThemes[themeName] = {{...currentSettings}};
            localStorage.setItem('reader_custom_themes', JSON.stringify(customThemes));
            showNotification('主题已保存: ' + themeName);
            
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
                showNotification('主题不存在');
                return;
            }}

            applySettings(customThemes[themeName]);
            showNotification('已加载主题: ' + themeName);
        }}
        
        // 通过名称加载自定义主题
        function loadCustomThemeByName(themeName) {{
            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            if (!customThemes[themeName]) {{
                showNotification('主题不存在');
                return;
            }}

            applySettings(customThemes[themeName]);
            showNotification('已加载主题: ' + themeName);
        }}
        
        // 删除自定义主题
        function deleteCustomTheme(themeName) {{
            if (!confirm('确定要删除主题 "' + themeName + '" 吗？')) {{
                return;
            }}
            
            const customThemes = JSON.parse(localStorage.getItem('reader_custom_themes') || '{{}}');
            delete customThemes[themeName];
            localStorage.setItem('reader_custom_themes', JSON.stringify(customThemes));
            showNotification('主题已删除: ' + themeName);
            
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
            if (!LOAD_PROGRESS_URL) {{
                console.log('LOAD_PROGRESS_URL 为空，跳过加载进度');
                return;
            }}

            fetch(LOAD_PROGRESS_URL)
                .then(response => {{
                    console.log('服务器响应状态:', response.status);
                    return response.json();
                }})
                .then(data => {{
                    console.log('加载到的翻页进度数据:', data);
                    if (data && data.progress !== undefined && pages.length > 0) {{
                        // 从数据库加载的是小数(0-1),转换为百分比(0-100)
                        const progressDecimal = parseFloat(data.progress);
                        const loadedProgress = progressDecimal * 100;  // 转换为百分比
                        
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
                            console.log('进度为0，从第一页开始');
                        }}
                    }} else {{
                        console.log('进度数据不完整或无效:', data);
                    }}
                }})
                .catch(err => {{
                    console.log('加载翻页进度失败:', err);
                }});
        }}
        
        // 保存翻页模式下的进度
        function savePaginationProgress(progress) {{
            console.log('开始保存翻页模式进度，SAVE_PROGRESS_URL:', SAVE_PROGRESS_URL);
            if (!SAVE_PROGRESS_URL) {{
                console.log('SAVE_PROGRESS_URL 为空，跳过保存进度');
                return;
            }}

            // 检测后端是否在线
            const backendOnline = checkBackendStatus();
            if (!backendOnline) {{
                console.log('后端离线，跳过保存进度');
                updateBackendStatusDisplay();
                return;
            }}

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
                    totalWordCount += page.textContent.replace(/\s+/g, '').length;
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

            fetch(SAVE_PROGRESS_URL, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify(data)
            }}).then(response => {{
                console.log('保存翻页进度响应状态:', response.status);
                if (response.ok) {{
                    isBackendOnline = true;
                    updateBackendStatusDisplay();
                }}
            }}).catch(err => {{
                console.log('保存翻页进度失败:', err);
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
                
                showNotification('已切换到夜间模式');
            }} else {{
                // 恢复之前的主题
                changeTheme(previousTheme);
                
                // 更新UI
                toggle.classList.remove('active');
                icon.textContent = '🌙';
                text.textContent = '夜间模式';
                
                showNotification('已切换到日间模式');
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
                
                showNotification('已进入专注模式，按 ESC 退出');
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
                showNotification('已退出专注模式');
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
                    option.textContent = `${{voice.name}} (${{voice.lang}})`;
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
                playbackBtn.textContent = '开始朗读';
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
            statusDisplay.textContent = `段落 ${{currentParagraphIndex + 1}}/${{paragraphs.length}}`;
            
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
                    playbackBtn.textContent = '开始朗读';
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
                    playbackBtn.textContent = '开始朗读';
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
            statsPanelVisible = !statsPanelVisible;
            
            if (statsPanelVisible) {{
                panel.classList.add('show');
                updateEnhancedReadingStats();
            }} else {{
                panel.classList.remove('show');
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
                    return `${{hours}}:${{minutes.toString().padStart(2, '0')}}:${{secs.toString().padStart(2, '0')}}`;
                }} else {{
                    return `${{minutes}}:${{secs.toString().padStart(2, '0')}}`;
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
            if (!SAVE_PROGRESS_URL) {{
                console.log('SAVE_PROGRESS_URL 为空，跳过保存进度');
                return;
            }}

            // 检测后端是否在线
            const backendOnline = await checkBackendStatus();
            if (!backendOnline) {{
                console.log('后端离线，跳过保存进度');
                updateBackendStatusDisplay();
                return;
            }}

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

            fetch(SAVE_PROGRESS_URL, {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
                body: JSON.stringify(data)
            }}).then(response => {{
                console.log('保存进度响应状态:', response.status);
                if (response.ok) {{
                    isBackendOnline = true;
                    updateBackendStatusDisplay();
                }}
            }}).catch(err => {{
                console.log('保存进度失败:', err);
                isBackendOnline = false;
                updateBackendStatusDisplay();
            }});
        }}
        
        // 从服务器加载进度
        function loadProgress() {{
            console.log('开始加载进度，LOAD_PROGRESS_URL:', LOAD_PROGRESS_URL);
            if (!LOAD_PROGRESS_URL) {{
                console.log('LOAD_PROGRESS_URL 为空，跳过加载进度');
                return;
            }}

            fetch(LOAD_PROGRESS_URL)
                .then(response => {{
                    console.log('服务器响应状态:', response.status);
                    return response.json();
                }})
                .then(data => {{
                    console.log('加载到的进度数据(小数):', data);
                    if (data && data.progress !== undefined) {{
                        // 从数据库加载的是小数(0-1),转换为百分比(0-100)
                        const progressDecimal = parseFloat(data.progress);
                        const progress = progressDecimal * 100;  // 转换为百分比

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
                    }} else {{
                        console.log('进度数据不完整或无效:', data);
                    }}
                }})
                .catch(err => {{
                    console.log('加载进度失败:', err);
                }});
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
                    toggleFontSettings();
                    e.preventDefault();
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
                console.log('标题', index + 1, ':', header.tagName, header.textContent.substring(0, 50));
            }});

            if (headers.length === 0) {{
                tocList.innerHTML = '<li class="toc-item">暂无章节目录</li>';
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
                    header.id = 'section-' + index;
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
        
        // 内容分页函数
        function paginateContent() {{
            const content = document.getElementById('content');
            const pageContainer = document.getElementById('paginationContainer');
            const pageContent = document.getElementById('pageContent');
            
            if (!content || !pageContainer || !pageContent) return;
            
            // 获取可用高度
            const containerHeight = pageContainer.offsetHeight;
            const containerWidth = pageContainer.offsetWidth;
            const pageContentEl = document.getElementById('pageContent');
            const pageContentStyle = window.getComputedStyle(pageContentEl);
            const paddingTop = parseInt(pageContentStyle.paddingTop) || 0;
            const paddingBottom = parseInt(pageContentStyle.paddingBottom) || 0;
            const totalPadding = paddingTop + paddingBottom;
            const availableHeight = containerHeight - totalPadding;
            
            console.log('=== 分页调试信息 ===');
            console.log('  容器尺寸:', containerWidth, 'x', containerHeight);
            console.log('  可用高度:', availableHeight);
            console.log('  内容元素总数:', content.children.length);
            console.log('  容器计算样式:', window.getComputedStyle(pageContainer).height);
            console.log('  容器实际高度:', pageContainer.getBoundingClientRect().height);
            
            // 克隆内容以避免修改原始内容
            const contentClone = content.cloneNode(true);
            contentClone.style.display = 'block';
            contentClone.style.height = 'auto';
            contentClone.style.overflow = 'visible';
            contentClone.style.padding = '0';
            contentClone.style.margin = '0';
            
            // 临时添加到DOM以计算高度
            document.body.appendChild(contentClone);
            
            // 获取所有内容元素
            const elements = Array.from(contentClone.children);
            pages = [];
            let currentPage = document.createElement('div');
            currentPage.className = 'page';
            let currentHeight = 0;
            
            // 简化的分页逻辑 - 强制按段落分页
            let elementCount = 0;
            elements.forEach((element, index) => {{
                elementCount++;
                console.log('处理元素 ' + index + ': ' + element.tagName + ' - ' + (element.textContent || '').substring(0, 30) + '...');
                
                // 强制分页策略：每2个段落分一页
                if (elementCount > 2 && currentPage.children.length > 0) {{
                    console.log('  -> 强制创建新页 (元素计数: ' + elementCount + ')');
                    // 当前页已满，创建新页
                    pages.push(currentPage);
                    currentPage = document.createElement('div');
                    currentPage.className = 'page';
                    currentHeight = 0;
                    elementCount = 1; // 重置计数，当前元素算作新页的第一个
                }}
                
                // 正式添加元素到当前页
                currentPage.appendChild(element);
                currentHeight = currentPage.offsetHeight;
                
                console.log('  -> 已添加，当前页元素数: ' + currentPage.children.length + ', 高度: ' + currentHeight);
            }});
            
            // 添加最后一页
            if (currentPage.children.length > 0) {{
                pages.push(currentPage);
            }}
            
            // 移除临时元素
            document.body.removeChild(contentClone);
            
            // 更新总页数
            document.getElementById('totalPages').textContent = pages.length;
            
            // 注意：不再自动显示第一页，由调用者决定显示哪一页
        }}
        
        // 显示指定页面
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
            
            // 根据不同的翻页效果应用不同的动画
            if (pageEffect === 'none') {{
                // 无效果，直接更新内容
                pageContent.innerHTML = '';
                pageContent.appendChild(pages[pageIndex].cloneNode(true));
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
                }});
            }} else {{
                requestAnimationFrame(() => {{
                    newContent.classList.add('book-flip-prev');
                    bookShadowPrev.classList.add('active');
                    pageCurve.classList.add('active');
                    thicknessLeft.classList.add('active');
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
        
        // 应用书页翻页效果
        function applyBookFlipEffect(element, direction) {{
            element.classList.add('book-flip');
            
            // 添加书页阴影效果
            const bookShadowNext = document.createElement('div');
            bookShadowNext.className = 'page-book-shadow page-book-shadow-next';
            
            const bookShadowPrev = document.createElement('div');
            bookShadowPrev.className = 'page-book-shadow page-book-shadow-prev';
            
            // 添加页面弯曲效果
            const pageCurve = document.createElement('div');
            pageCurve.className = 'page-curve';
            
            // 添加页面厚度效果
            const thicknessRight = document.createElement('div');
            thicknessRight.className = 'page-thickness page-thickness-right';
            
            const thicknessLeft = document.createElement('div');
            thicknessLeft.className = 'page-thickness page-thickness-left';
            
            element.appendChild(bookShadowNext);
            element.appendChild(bookShadowPrev);
            element.appendChild(pageCurve);
            element.appendChild(thicknessRight);
            element.appendChild(thicknessLeft);
            
            // 根据方向应用不同的翻页效果
            if (direction === 'next') {{
                element.classList.add('book-flip-next');
                bookShadowNext.classList.add('active');
                pageCurve.classList.add('active');
                thicknessRight.classList.add('active');
            }} else {{
                element.classList.add('book-flip-prev');
                bookShadowPrev.classList.add('active');
                pageCurve.classList.add('active');
                thicknessLeft.classList.add('active');
            }}
            
            // 动画结束后移除效果
            setTimeout(() => {{
                const effects = element.querySelectorAll('.page-book-shadow, .page-curve, .page-thickness');
                effects.forEach(effect => effect.remove());
            }}, 800);
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
                
                showNotification(`自动翻页已开启，每${{autoPageTurnInterval}}秒翻页`);
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
                    loadProgress();
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
                progress = cachedProgress;
            }} else {{
                // 否则重新计算
                const scrollableHeight = Math.max(scrollHeight - clientHeight, 1);
                progress = (scrollTop / scrollableHeight) * 100;
                progress = Math.min(100, Math.max(0, progress));
                console.log('beforeunload - 重新计算进度:', progress);
            }}

            console.log('beforeunload - 最终使用的进度(百分比):', progress.toFixed(2) + '%');

            if (SAVE_PROGRESS_URL) {{
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
                console.log('beforeunload - 发送数据(小数):', data);
                console.log('beforeunload - 发送JSON:', JSON.stringify(data));
                navigator.sendBeacon(SAVE_PROGRESS_URL, JSON.stringify(data));
            }}
        }});
    </script>
</body>
</html>"""
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
                # 保存服务器对象到全局字典，防止被垃圾回收
                server_id = str(uuid.uuid4())
                _active_servers[server_id] = {
                    'server': server,
                    'server_thread': server_thread,
                    'file_path': file_path,
                    'created_at': time.time()
                }
                logger.info(f"已保存服务器对象到全局字典，server_id={server_id}")
            
            # 创建HTML
            html = BrowserReader.create_reader_html(
                content, title, theme, custom_settings, save_url, load_url
            )
            
            # 创建临时HTML文件
            temp_dir = tempfile.gettempdir()
            html_filename = f"{title}_reader.html"
            html_path = os.path.join(temp_dir, html_filename)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)

            # 使用 Chrome 浏览器打开
            chrome_path = None
            if platform.system() == 'Darwin':  # macOS
                chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
            elif platform.system() == 'Windows':
                chrome_paths = [
                    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe')
                ]
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_path = path
                        break
            elif platform.system() == 'Linux':
                chrome_path = '/usr/bin/google-chrome'

            if chrome_path and os.path.exists(chrome_path):
                # 使用 Chrome 打开
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                webbrowser.get('chrome').open(f'file://{html_path}')
                logger.info(f"使用 Chrome 浏览器打开书籍: {html_path}")
            else:
                # 回退到默认浏览器
                webbrowser.open(f'file://{html_path}')
                logger.warning(f"未找到 Chrome 浏览器,使用默认浏览器打开: {html_path}")

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
        
        # 生成随机端口
        port = random.randint(10000, 60000)
        
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
                    self.wfile.write(json.dumps({{"status": "ok"}}).encode())
                else:
                    self.send_response(404)
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
        try:
            server = HTTPServer(('localhost', port), ProgressHandler)
            server_thread = Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            
            save_url = f"http://localhost:{port}/save_progress"
            load_url = f"http://localhost:{port}/load_progress"
            
            return save_url, load_url, server, server_thread
        except OSError:
            # 端口被占用，尝试其他端口
            for _ in range(10):
                port = random.randint(10000, 60000)
                try:
                    server = HTTPServer(('localhost', port), ProgressHandler)
                    server_thread = Thread(target=server.serve_forever, daemon=True)
                    server_thread.start()
                    
                    save_url = f"http://localhost:{port}/save_progress"
                    load_url = f"http://localhost:{port}/load_progress"
                    
                    return save_url, load_url, server, server_thread
                except OSError:
                    continue
            
            # 所有端口都被占用，不启用进度同步
            return None, None, None, None

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

