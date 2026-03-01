#core/registry.py

import json
import os
import sys
import importlib
import zipfile

from subsystems.audio_out import AudioOut
from threading import Thread

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
                print(f"Error: core/registry.py [check_plugins] -> Plugin {path} not found") 
        #TODO добавить еще для nonvoice, т.к пока нету плагинов для nonvoice я не могу проверять их наличие

    def get_plugins_list(self):
        with open("data/plugins.json", "r", encoding='utf-8') as f:
            result = json.load(f)
        
        result.get("voice")

        print(result)

        return result 

    def plug_install(self, path_to_zip):
        self.plugins = self.get_plugins_list()

        if not os.path.exists(path_to_zip):
            print("Error: core/registry.py [plug_install] -> path not found")
        else:
            try:
                extract_to_dir = path_to_zip.split("/")[-1].replace(".zip", "")
                extract_to_dir = "plugins/" + extract_to_dir
                print(extract_to_dir)

                with zipfile.ZipFile(path_to_zip, "r") as zip_ref:
                    bad_file = zip_ref.testzip()
                    if bad_file:
                        print("Error: core/registry.py [plug_install] -> The file is damaged")
                    else:
                        zip_ref.extractall(extract_to_dir)
                        print("core/registry.py [plug_install] -> plugins installed")
            except zipfile.BadZipFile:
                print("Error: core/registry.py [plug_install] -> File is not a zip archive or is heavily corrupted.")

    def plug_remove(self):
        pass

    def plug_update(self):
        pass

    def voice_plug_start(self, voice_text="non"):
        try: 
            with open("data/setting.json", "r", encoding='utf-8') as f:
                commands = json.load(f)
                commands_keys = list(commands.keys())
                commands_flag = False

            for i in commands_keys:
                if voice_text == i: 
                    try:
                        module = importlib.import_module(f"plugins.{commands.get(i)}.main")
                        if hasattr(module, 'run'):
                            tread = Thread(target=module.run())
                            commands_flag = True
                            break
                        else:
                            print(f"In plugin {commands.get(i)} not found run()")
                    except ModuleNotFoundError as e:
                        print("Error core/registry.py [voice_plug_start] -> ", e)

            if not commands_flag:
                audio = AudioOut()
                audio.play("data/jarvis_wav/what.wav")

        except Exception as e:
            print("Error: core/registry.py [voice_plug_start] -> ", e)

    def plug_start(self):
        self.plugins = self.get_plugins_list()


         

if __name__ == '__main__':
    start = Registry()
    start.get_plugins_list()
    #start.voice_plug_start("джарвис")
    #start.plug_install("test.zip")
