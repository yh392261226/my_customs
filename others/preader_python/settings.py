import os
import json

def get_config_path():
    home = os.environ.get("HOME")
    config_dir = os.path.join(home, ".config", "preader")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "settings.json")

DEFAULT_SETTINGS = {
    "width": 80,
    "height": 25,
    "theme": "dark",
    "lang": "zh",
    "font_color": "white",
    "bg_color": "black",
    "border_style": "round",
    "border_color": "blue",
    "margin": 1,
    "padding": 2,
    "line_spacing": 1,
    "status_bar": True,
    "auto_page_interval": 5,
    "remind_interval": 0
}

class Settings:
    def __init__(self):
        self.path = get_config_path()
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

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
        self.settings[key] = value