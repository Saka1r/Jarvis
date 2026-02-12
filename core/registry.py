#core/registry.py

import json
import os

class Registry():
    def __init__(self):

        self.plugins = None
        self.nonvoice_plug = None
        self.voice_plug = None

        self.check_plugins()

    def check_plugins(self):

        self.plugins = self.get_plugins_list() 

        self.voice_plug = self.plugins.get("voice")
        self.nonvoice_plug = self.plugins.get("nonvoice")

        for i in self.voice_plug:

            path = "plugins/" + i.get("name")

            if not os.path.exists(path):
                print(f"Plugin {path} not found") 
        #TODO добавить еще для nonvoice, т.к пока нету плагинов для nonvoice я не могу проверять их наличие

    def get_plugins_list(self):
        
        with open("data/plugins.json", "r") as f:
            result = json.load(f)

        return result 

    def plug_install(self):
        
        self.plugins = self.get_plugins_list()
        
    def plug_remove(self):
        pass

    def plug_update(self):
        pass

    def voice_plug_start(self, voice_text):
        pass

    def plug_start(self):
        
        self.plugins = self.get_plugins_list()

        #voice_plugs = plugins.get("voice")
        self.nonvoice_plug = self.plugins.get("nonvoice")

         

if __name__ == '__main__':
    start = Registry()
    start.plug_start()
