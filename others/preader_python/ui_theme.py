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
    }
}

BORDER_CHARS = {
    "single": ('|', '-', '+'),
    "double": ('║', '═', '╬'),
    "bold": ('┃', '━', '╋'),
    "round": ('│', '─', '○'),
    "none": (' ', ' ', ' '),
}

def color_pair_idx(idx, fg, bg):
    fg_c = COLOR_MAP.get(fg, curses.COLOR_WHITE)
    bg_c = COLOR_MAP.get(bg, curses.COLOR_BLACK)
    curses.init_pair(idx, fg_c, bg_c)
    return curses.color_pair(idx)

def init_colors(theme="dark", settings=None):
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