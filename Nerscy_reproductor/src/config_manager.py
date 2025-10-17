import json
import os
class ConfigManager:
    def __init__(self, filename="config.json"):
        self.filename = filename
        self.config = {}

    def load_config(self):
        if os.path.exists(self.filename):
            with open(self.filename, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            # configuracion inicial por defecto
            self.config = {
                "window_size": "800x600",
                "last_folder": "",
                "recent_tracks": [],
                "music_folder": [],
                "background_image": "",
                "volume": 0.5
            }
            self.save_config()
    
    def save_config(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value