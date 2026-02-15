#config.py

import json
import os

class Config():
    def __init__(self):
       self.standart_plugins = {
        "voice": [
            {
                "name": "jarvis",
                "version": "1.0",
                "description": "Voice assistant plugin",
                "author": "Sakair"
            }
        ],
        "nonvoice": []
        }
 
    def generate_system_config(self):
        with open("config/system.json", "w", encoding='utf-8') as f:
            json.dump(self.standart_plugins, f, indent=4, ensure_ascii=False)

    def generate_setting_config(self):
        with open("data/setting.json", "w", encoding='utf-8') as f:
            json.dump(self.standart_plugins, f, indent=4, ensure_ascii=False)

    def generate_plugins_config(self):
        with open("data/plugins.json", "w", encoding='utf-8') as f:
            json.dump(self.standart_plugins, f, indent=4, ensure_ascii=False)
    
    def check_status(self):

        '''проверяет файлы конфигурации, системы, плагинов'''

        if not os.path.exists("config/system.json"):
            print("Error: config/system.json not found -> create config/system.json")
            self.generate_system_config()

        if not os.path.exists("data/setting.json"):
            print("Error: data/setting.json not found -> create data/setting.json")
            self.generate_setting_config()

        if not os.path.exists("data/plugins.json"):
            print("Error: data/plugins.json not found -> create plugins.json")
            self.generate_plugins_config()

    def start(self):
        self.check_status()
