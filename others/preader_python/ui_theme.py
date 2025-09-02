import curses

COLOR_MAP = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "transparent": -1,  # 新增透明色
}

THEMES = {
    "dark": {
        "font": "white",
        "bg": "black",
        "highlight": "cyan",
        "progress": "green",
        "border": "blue"
    },
    "light": {
        "font": "black",
        "bg": "white",
        "highlight": "red",
        "progress": "magenta",
        "border": "yellow"
    },
    "eye": {
        "font": "green",
        "bg": "black",
        "highlight": "yellow",
        "progress": "green",
        "border": "green"
    },
    # 新增主题
    "midnight": {
        "font": "white",
        "bg": "blue",
        "highlight": "cyan",
        "progress": "green",
        "border": "magenta"
    },
    "sepia": {
        "font": "black",
        "bg": "yellow",
        "highlight": "red",
        "progress": "magenta",
        "border": "black"
    },
    "forest": {
        "font": "white",
        "bg": "green",
        "highlight": "yellow",
        "progress": "cyan",
        "border": "white"
    },
    "amethyst": {
        "font": "white",
        "bg": "magenta",
        "highlight": "cyan",
        "progress": "green",
        "border": "blue"
    },
    "ocean": {
        "font": "white",
        "bg": "cyan",
        "highlight": "blue",
        "progress": "green",
        "border": "white"
    },
    "crimson": {
        "font": "white",
        "bg": "red",
        "highlight": "yellow",
        "progress": "cyan",
        "border": "white"
    },
    "slate": {
        "font": "white",
        "bg": "black",
        "highlight": "blue",
        "progress": "cyan",
        "border": "white"
    },
    "transparent-dark": {
        "font": "white",
        "bg": "transparent",
        "highlight": "cyan",
        "progress": "green",
        "border": "blue"
    },
    "transparent-light": {
        "font": "black",
        "bg": "transparent",
        "highlight": "red",
        "progress": "magenta",
        "border": "yellow"
    },
    "transparent-blue": {
        "font": "white",
        "bg": "transparent",
        "highlight": "cyan",
        "progress": "green",
        "border": "blue"
    }
}

BORDER_CHARS = {
    "single": ('|', '-', '+'),
    "double": ('║', '═', '╬'),
    "bold": ('┃', '━', '╋'),
    "round": ('│', '─', '○'),
    "none": (' ', ' ', ' '),
    # 新增边框样式
    "dotted": ('┆', '┄', '┼'),
    "dashed": ('┊', '┈', '┼'),
    "curved": ('│', '─', '╭╮╰╯'),  # 特殊处理，需要四个角字符
    "thick": ('┃', '━', '┏┓┗┛'),   # 特殊处理，需要四个角字符
    "shadow": ('│', '─', '┌┐└┘'),   # 特殊处理，需要四个角字符
    "fancy": ('║', '═', '╔╗╚╝'),    # 特殊处理，需要四个角字符
    "minimal": ('│', '─', '├┤┬┴'),  # 特殊处理，需要四个角字符
    "classic": ('┃', '━', '┌┐└┘'),  # 特殊处理，需要四个角字符
}

def color_pair_idx(idx, fg, bg):
    fg_c = COLOR_MAP.get(fg, curses.COLOR_WHITE)
    bg_c = COLOR_MAP.get(bg, curses.COLOR_BLACK)
    
    # 处理透明背景
    if bg == "transparent":
        # 使用默认终端背景色
        curses.init_pair(idx, fg_c, -1)
    else:
        curses.init_pair(idx, fg_c, bg_c)
    
    return curses.color_pair(idx)

def init_colors(theme="dark", settings=None):
    # 启用默认颜色支持，这是实现透明效果的关键
    curses.use_default_colors()
    curses.start_color()
    
    t = THEMES[theme]
    font_color = settings["font_color"] if settings else t["font"]
    bg_color = settings["bg_color"] if settings else t["bg"]
    highlight_color = t["highlight"]
    progress_color = t["progress"]
    border_color = settings["border_color"] if settings else t["border"]

    color_pair_idx(1, font_color, bg_color)
    color_pair_idx(2, highlight_color, bg_color)
    color_pair_idx(3, progress_color, bg_color)
    color_pair_idx(4, border_color, bg_color)
    color_pair_idx(10, border_color, bg_color)