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
    <!-- 进度条 -->
    <div class="progress-bar">
        <div class="progress-fill" id="progressFill"></div>
    </div>
    
    <!-- 进度信息 -->
    <div class="progress-info" id="progressInfo">进度: 0%</div>
    
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
            </select>
        </label>
        
        <label>
            行高：
            <input type="range" min="1.2" max="2.5" step="0.1" value="{settings['line_height']}" onchange="changeLineHeight(this.value)">
        </label>
        
        <button onclick="scrollToTop()">顶部</button>
        <button onclick="scrollToBottom()">底部</button>
        <button onclick="printContent()">打印</button>
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
        
        // 修改字体大小
        function changeFontSize(delta) {{
            const body = document.body;
            const currentSize = parseInt(getComputedStyle(body).fontSize);
            body.style.fontSize = (currentSize + delta) + 'px';
            currentSettings['font_size'] = String(currentSize + delta);
            saveSettings();
        }}
        
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
            document.getElementById('progressInfo').textContent = '进度: ' + progress.toFixed(1) + '%';

            // 触发自动保存进度
            triggerProgressSave(progress);
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
        function saveProgress(progress) {{
            console.log('开始保存进度，SAVE_PROGRESS_URL:', SAVE_PROGRESS_URL);
            if (!SAVE_PROGRESS_URL) {{
                console.log('SAVE_PROGRESS_URL 为空，跳过保存进度');
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

            const data = {{
                progress: progressDecimalString,
                scrollTop: scrollTop,
                scrollHeight: scrollHeight,
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
            }}).catch(err => {{
                console.log('保存进度失败:', err);
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
            }}
        }}
        
        // 应用设置
        function applySettings(settings) {{
            document.body.style.backgroundColor = settings.background;
            document.body.style.color = settings.text;
            document.body.style.fontSize = settings.font_size + 'px';
            document.body.style.lineHeight = settings.line_height;
            document.body.style.fontFamily = settings.font_family;
            
            // 更新控件状态
            document.getElementById('themeSelect').value = getThemeName(settings);
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
                    break;
                case '-':
                    changeFontSize(-2);
                    break;
            }}
        }});
        
        // 监听滚动事件，更新进度
        window.addEventListener('scroll', () => {{
            updateProgress();
        }});
        
        // 页面加载时恢复设置和进度
        window.onload = function() {{
            loadSettings();

            console.log('页面加载完成，开始初始化');
            console.log('文档高度:', document.documentElement.scrollHeight, '视口高度:', window.innerHeight);

            // 延迟加载进度，等待内容完全渲染
            setTimeout(() => {{
                console.log('延迟加载进度开始，文档高度:', document.documentElement.scrollHeight);
                loadProgress();

                // 延迟取消冷却标记,允许正常自动保存
                setTimeout(() => {{
                    isPageLoading = false;
                    console.log('页面加载冷却结束,允许自动保存');
                }}, pageLoadCooldown);
            }}, 1000);
        }};
        
        // 页面关闭前保存进度
        window.addEventListener('beforeunload', function() {{
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
                const data = {{
                    progress: progressDecimal.toFixed(15),
                    scrollTop: scrollTop,
                    scrollHeight: scrollHeight,
                    timestamp: Date.now()
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
                    # TXT文件：将段落转换为HTML
                    paragraphs = content.split('\n')
                    html_content = ''
                    for para in paragraphs:
                        para = para.strip()
                        if para:
                            html_content += f'<p>{para}</p>'
                    return html_content
                    
                elif ext == '.md':
                    # Markdown文件：简单处理（可以使用markdown库增强）
                    import markdown
                    return markdown.markdown(content)
                    
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
                    else:
                        self.send_response(404)
                        self.end_headers()
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

                        if on_progress_save:
                            on_progress_save(progress, scroll_top, scroll_height)

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

