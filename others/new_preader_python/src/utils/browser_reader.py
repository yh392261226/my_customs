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
            background: {settings['background']};
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            min-width: 100px;
        }}

        /* 快捷键提示 */
        .keyboard-hint {{
            position: fixed;
            bottom: 45px;
            right: 10px;
            background: {settings['background']};
            padding: 10px;
            border-radius: 4px;
            font-size: 11px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 998;
            max-width: 200px;
            border: 1px solid rgba(128, 128, 128, 0.3);
        }}

        .keyboard-hint h4 {{
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
        }}

        /* 章节目录 */
        .toc-container {{
            position: fixed;
            right: 20px;
            top: 80px;
            width: 250px;
            max-height: 70vh;
            background: {settings['background']};
            border: 1px solid rgba(128, 128, 128, 0.3);
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 998;
            overflow-y: auto;
            display: none;
            transition: all 0.3s ease;
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
            background: rgba(128, 128, 128, 0.1);
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
            background: {settings['background']};
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
            background: rgba(128, 128, 128, 0.1);
            transform: scale(1.05);
        }}

        /* 搜索框 */
        .search-container {{
            position: fixed;
            top: 70px;
            left: 20px;
            background: {settings['background']};
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            display: none;
            border: 1px solid rgba(128, 128, 128, 0.3);
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
            background: rgba(100, 149, 237, 0.6);
            border: none;
            color: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}

        .search-container button:hover {{
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
            background: {settings['background']};
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
            background: rgba(128, 128, 128, 0.1);
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
            background: {settings['background']};
            padding: 10px;
            border-radius: 4px;
            font-size: 11px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            min-width: 120px;
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
            gap: 20px;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            flex-wrap: wrap;
        }}
        
        .toolbar button {{
            padding: 6px 12px;
            background: rgba(128, 128, 128, 0.1);
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
            transition: all 0.2s;
        }}
        
        .toolbar button:hover {{
            background: rgba(128, 128, 128, 0.2);
        }}
        
        .toolbar button:active {{
            transform: scale(0.98);
        }}
        
        .toolbar select {{
            padding: 6px 12px;
            background: rgba(128, 128, 128, 0.1);
            border: 1px solid rgba(128, 128, 128, 0.3);
            color: {settings['text']};
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
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
            background: {settings['background']};
            border: 1px solid rgba(128, 128, 128, 0.3);
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
            background: rgba(128, 128, 128, 0.1);
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
            background: {settings['background']};
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.2s;
        }}

        .toggle-btn:hover {{
            background: rgba(128, 128, 128, 0.1);
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
            background: {settings['background']};
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
        }}

        .setting-actions button:hover {{
            background: rgba(128, 128, 128, 0.1);
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
            background: rgba(100, 149, 237, 0.3);
            border: 1px solid rgba(100, 149, 237, 0.6);
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}

        .add-btn:hover {{
            background: rgba(100, 149, 237, 0.5);
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
            background: {settings['background']};
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
        }}
        
        .theme-actions button:hover {{
            background: rgba(128, 128, 128, 0.1);
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
            top: 70px;
            left: 50%;
            transform: translateX(-50%);
            background: {settings['background']};
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
            background: rgba(128, 128, 128, 0.1);
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
            background: {settings['background']};
            padding: 15px;
            border-radius: 8px;
            font-size: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            min-width: 180px;
            display: none;
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
            background: {settings['background']};
            padding: 10px 20px;
            border-radius: 25px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            display: none;
            align-items: center;
            gap: 15px;
        }}
        
        .auto-scroll-controls.show {{
            display: flex;
        }}
        
        .auto-scroll-controls button {{
            padding: 6px 12px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: {settings['background']};
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .auto-scroll-controls button:hover {{
            background: rgba(128, 128, 128, 0.1);
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
            background: {settings['background']};
            padding: 10px 20px;
            border-radius: 25px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 997;
            border: 1px solid rgba(128, 128, 128, 0.3);
            display: none;
            align-items: center;
            gap: 15px;
        }}
        
        .speech-controls.show {{
            display: flex;
        }}
        
        .speech-controls button {{
            padding: 6px 12px;
            border: 1px solid rgba(128, 128, 128, 0.3);
            background: {settings['background']};
            color: {settings['text']};
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        .speech-controls button:hover {{
            background: rgba(128, 128, 128, 0.1);
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
    
    <!-- 工具栏 -->
    <div class="toolbar">
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
        <button onclick="toggleFocusMode()">专注模式</button>
        <button onclick="toggleFullscreen()">全屏</button>
        <button onclick="scrollToTop()">顶部</button>
        <button onclick="scrollToBottom()">底部</button>
        <button onclick="printContent()">打印</button>
        <button onclick="toggleTOC()">目录</button>
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
    
    <!-- 内容区域 -->
    <div class="content" id="content">
        {content}
    </div>
    
    <script>
        // 当前设置
        let currentSettings = {str(settings)};

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
        
        // 修改字体大小
        function changeFontSize(delta) {{
            const body = document.body;
            const currentSize = parseInt(getComputedStyle(body).fontSize);
            body.style.fontSize = (currentSize + delta) + 'px';
            currentSettings['font_size'] = String(currentSize + delta);
            saveSettings();
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
        }}

        // 修改背景颜色
        function changeBackgroundColor(color) {{
            document.body.style.backgroundColor = color;
            currentSettings['background'] = color;
            saveSettings();
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
            const themes = {str(BrowserReader.THEMES)};
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
            const themes = {str(BrowserReader.THEMES)};
            const selectedTheme = themes[theme];
            
            document.body.style.backgroundColor = selectedTheme.background;
            document.body.style.color = selectedTheme.text;
            document.body.style.fontSize = selectedTheme.font_size + 'px';
            document.body.style.lineHeight = selectedTheme.line_height;
            document.body.style.fontFamily = selectedTheme.font_family;
            
            currentSettings = selectedTheme;
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
            saveSettings();
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
        
        // 加载设置
        function loadSettings() {{
            const saved = localStorage.getItem('readerSettings');
            if (saved) {{
                currentSettings = JSON.parse(saved);
                applySettings(currentSettings);
            }} else {{
                // 首次加载，检测系统主题
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (prefersDark) {{
                    changeTheme('dark');
                }}
            }}
        }}
        
        
        
        // 获取主题名称
        function getThemeName(settings) {{
            const themes = {str(BrowserReader.THEMES)};
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
                    window.scrollBy({{ top: -window.innerHeight * 0.8, behavior: 'smooth' }});
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                    window.scrollBy({{ top: window.innerHeight * 0.8, behavior: 'smooth' }});
                    e.preventDefault();
                    break;
                case 'PageUp':
                    window.scrollBy({{ top: -window.innerHeight * 0.9, behavior: 'smooth' }});
                    e.preventDefault();
                    break;
                case 'PageDown':
                    window.scrollBy({{ top: window.innerHeight * 0.9, behavior: 'smooth' }});
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
        
        // 监听滚动事件，更新进度和当前章节
        window.addEventListener('scroll', () => {{
            updateProgress();
            highlightCurrentChapter();
        }});
        
        // 页面加载时恢复设置和进度
        window.onload = function() {{
            loadSettings();

            console.log('页面加载完成，开始初始化');
            console.log('文档高度:', document.documentElement.scrollHeight, '视口高度:', window.innerHeight);

            // 生成章节目录
            setTimeout(() => {{
                generateTOC();
            }}, 500);

            // 加载书签状态
            loadBookmark();
            
            // 初始化语音功能
            initSpeech();

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
            if (prefersDark && !isNightMode) {{
                toggleNightMode();
            }}

            // 延迟加载进度，等待内容完全渲染
            setTimeout(() => {{
                console.log('延迟加载进度开始，文档高度:', document.documentElement.scrollHeight);
                loadProgress();

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

