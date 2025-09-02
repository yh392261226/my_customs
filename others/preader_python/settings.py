import os
import json

def get_config_path():
    home = os.environ.get("HOME")
    config_dir = os.path.join(home, ".config", "preader")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "settings.json")

DEFAULT_SETTINGS = {
    "width": 200,
    "height": 50,
    "theme": "dark",
    "lang": "zh",
    "font_color": "white",
    "bg_color": "black",
    "border_style": "round",
    "border_color": "blue",
    "margin": 1,
    "padding": 2,
    "line_spacing": 1,
    "paragraph_spacing": 1,  # 添加段落间距
    "status_bar": True,
    "auto_page_interval": 5,
    "speech_rate": 200,  # 添加语速设置，默认200（pyttsx3的默认值）
    "remind_interval": 0,
    # 添加字体相关设置
    "font_scale": 1.0,  # 字体缩放因子
    "paragraph_spacing": 0,  # 段落间距
}

class Settings:
    def __init__(self):
        self.path = get_config_path()
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

        # 确保所有设置都有有效值
        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in self.settings:
                self.settings[key] = default_value
                
        # 确保数值设置的最小值
        self.settings["width"] = max(10, self.settings["width"])
        self.settings["height"] = max(5, self.settings["height"])
        self.settings["line_spacing"] = max(0, self.settings["line_spacing"])
        self.settings["paragraph_spacing"] = max(0, self.settings.get("paragraph_spacing", 1))
        self.settings["font_scale"] = max(0.1, self.settings["font_scale"])
        self.settings["margin"] = max(0, self.settings["margin"])
        self.settings["padding"] = max(0, self.settings["padding"])
        
        self.save()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.settings.update(data)
            except Exception:
                pass

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def __getitem__(self, key):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))

    def __setitem__(self, key, value):
        # 确保设置的值有效
        if key in ["width", "height"]:
            value = max(10, value)
        elif key in ["line_spacing", "paragraph_spacing", "margin", "padding"]:
            value = max(0, value)
        elif key == "font_scale":
            value = max(0.1, value)
            
        self.settings[key] = value