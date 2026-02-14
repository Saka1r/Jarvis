#core/registry.py

import json
import os
import sys
import importlib

from subsystems.audio_out import AudioOut

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)


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
        
        with open("data/plugins.json", "r", encoding='utf-8') as f:
            result = json.load(f)

        return result 

    def plug_install(self):
        
        self.plugins = self.get_plugins_list()
        
    def plug_remove(self):
        pass

    def plug_update(self):
        pass

    def voice_plug_start(self, voice_text="non"):
        try: 
            with open("data/setting.json", "r", encoding='utf-8') as f:
                commands = json.load(f)
                print(commands)
            for i in commands:
                if voice_text == i: 
                    try:
                        module = importlib.import_module(f"plugins.{commands.get(i)}.main")
                        if hasattr(module, 'run'):
                            module.run()
                        else:
                            print(f"In plugin {commands.get(i)} not found run()")
                    except ModuleNotFoundError as e:
                        print("Error core/registry.py -> ", e)
                else:
                    audio = AudioOut()
                    audio.play("data/jarvis_wav/what.wav")


        except Exception as e:
            print("Error: core/registry.py voice_plug_start -> ", e)

    def plug_start(self):
        
        self.plugins = self.get_plugins_list()

        #voice_plugs = plugins.get("voice")
        self.nonvoice_plug = self.plugins.get("nonvoice")

         

if __name__ == '__main__':
    start = Registry()
    start.plug_start()
    start.voice_plug_start("джарвис")
