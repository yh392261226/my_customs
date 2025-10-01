"""
默认配置文件，包含应用程序的默认设置
"""

DEFAULT_CONFIG = {
    # 路径设置
    "paths": {
        "config_dir": "~/.config/new_preader",
        "database": "~/.config/new_preader/database.sqlite",
        "config_file": "~/.config/new_preader/config.json",
        "library": "~/Documents/NewReader/books"
    },
    
    # 外观设置
    "appearance": {
        "theme": "dark",  # 默认主题
        "border_style": "rounded",  # 边框样式: rounded, single, double, minimal
        "show_icons": True,  # 是否显示图标
        "animation_enabled": True,  # 是否启用动画
        "progress_bar_style": "bar",  # 进度条样式: bar, percentage, both
    },
    
    # 阅读设置
    "reading": {
        "font_size": 16,  # 字体大小
        "line_spacing": 1.2,  # 行间距
        "paragraph_spacing": 1.0,  # 段落间距
        "auto_page_turn_interval": 30,  # 自动翻页间隔(秒)
        "remember_position": True,  # 记住阅读位置
        "highlight_search": True,  # 高亮搜索结果
        "margin_left": 2,  # 左边距
        "margin_right": 2,  # 右边距
    },
    
    # 音频设置
    "audio": {
        "tts_enabled": True,  # 是否启用文本朗读
        "tts_speed": 150,  # 朗读速度 (words per minute)
        "tts_voice": "default",  # 朗读声音
        "tts_volume": 1.0,  # 朗读音量 (0.0-1.0)
    },
    
    # 高级设置
    "advanced": {
        "cache_size": 100,  # 缓存大小(MB)
        "language": "zh_CN",  # 界面语言
        "book_directories": [],  # 书籍目录列表
        "statistics_enabled": True,  # 是否启用阅读统计
        "backup_enabled": True,  # 是否启用备份
        "backup_interval": 7,  # 备份间隔(天)
        "debug_mode": False,  # 调试模式
    },
    
    # 快捷键设置
    "keybindings": {
        # 阅读操作
        "prev_page": ["left", "h"],
        "next_page": ["right", "l"],
        "scroll_up": ["up", "k"],
        "scroll_down": ["down", "j"],
        "goto_page": ["g"],
        "toggle_auto_page": ["space"],
        "bookmark": ["b"],
        "bookmark_list": ["B"],
        "search": ["s"],
        "toggle_tts": ["r"],
        
        # 界面设置
        "toggle_theme": ["t"],
        "change_language": ["alt+l"],
        "open_settings": ["S"],
        "toggle_fullscreen": ["f"],
        "show_help": ["h"],
        "quit": ["q", "ctrl+c"],
        
        # 书架管理
        "open_bookshelf": ["k"],
        "add_book": ["a"],
        "add_book_directory": ["d"],
        "batch_operations": ["l"],
        "export_data": ["E"],
        "view_statistics": ["c"],
        "view_global_statistics": ["C"],
        
        # 高级功能
        "boss_key": ["/"],
        "reset_progress": ["R"],
        "adjust_font_size": ["F"],
        "adjust_line_spacing": ["L"],
        "adjust_paragraph_spacing": ["P"],
    }
}

# 支持的主题列表
AVAILABLE_THEMES = [
    "dark", "light", "nord", "dracula", "material", 
    "github-dark", "github-light", "solarized-dark", 
    "solarized-light", "amethyst", "forest-green",
    "crimson", "slate", "transparent-dark", "transparent-light",
    "paper-white", "cream", "sky-blue", "mint-green", "lavender"
]

# 支持的边框样式
BORDER_STYLES = ["rounded", "single", "double", "minimal", "none"]

# 支持的语言
AVAILABLE_LANGUAGES = ["zh_CN", "en_US"]

# 支持的文件格式
SUPPORTED_FORMATS = [".txt", ".md", ".epub", ".pdf", ".mobi", ".azw", ".azw3"]