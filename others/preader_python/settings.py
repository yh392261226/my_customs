import json
import os

class Settings:
    def __init__(self, path="settings.json"):
        self.path = path
        self.defaults = {
            "width": 80,
            "height": 25,
            "font_color": "white",
            "bg_color": "black",
            "bg_transparent": False,
            "margin": 2,
            "padding": 1,
            "line_spacing": 1,
            "status_bar": True,
            "auto_page_interval": 5,
            "theme": "dark",
            "lang": "zh",
            "border_style": "round",
            "border_color": "blue",
            "remind_interval": 30,  # 单位: 分钟
        }
        self.data = self.defaults.copy()
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    self.data.update(json.load(f))
            except:
                pass

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def update(self, **kwargs):
        self.data.update(kwargs)
        self.save()

    def __getitem__(self, key):
        return self.data.get(key, self.defaults.get(key))

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()