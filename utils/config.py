import json
import os

class ConfigManager:
    DEFAULT_CONFIG = {
        "last_devices": ["camera"],
        "arduino_port": "COM3",
        "camera_index": 0
    }
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return self.DEFAULT_CONFIG
        return self.DEFAULT_CONFIG

    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
