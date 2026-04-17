# core/registry.py

import json
import os
import sys
import importlib
import zipfile

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

class Registry:
    def __init__(self):
        self.plugins = None
        self.utility_plug = None
        self.voice_plug = None
        self.plug_config_file = None

        self.check_plugins()
        self.commands = self.load_commands()

    def get_command_priority(self, text: str) -> str:
        """
        Возвращает приоритет команды: 'background' или 'dialog'.
        Если команда не найдена — 'dialog' (консервативно).
        """
        text_lower = text.lower()
        plugins_dir = "plugins"
        
        for plugin_name in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            if os.path.isdir(plugin_path):
                commands_file_path = os.path.join(plugin_path, "commands.json")
                if os.path.isfile(commands_file_path):
                    with open(commands_file_path, "r", encoding='utf-8') as f:
                        plugin_commands = json.load(f)
                        for command in plugin_commands.get("commands", []):
                            if text_lower in command.get('triggers', []):
                                return command.get('priority', 'dialog')
        
        # Команда не найдена в реестре → считаем диалоговой
        return 'dialog'

    def load_commands(self):
        commands = [] 
        plugins_dir = "plugins"
        
        for plugin_name in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            if os.path.isdir(plugin_path):
                commands_file_path = os.path.join(plugin_path, "commands.json")
                if os.path.isfile(commands_file_path):
                    with open(commands_file_path, "r", encoding='utf-8') as f:
                        plugin_commands = json.load(f)
                        for command in plugin_commands.get("commands", []):
                            commands.extend(command.get('triggers', []))
        
        return set(commands)

    def is_command(self, text):
        return text.lower() in self.commands

    def check_plugins(self):
        self.plugins = self.get_plugins_list()

        self.voice_plug = self.plugins.get("voice")
        self.utility_plug = self.plugins.get("utility")

        for i in self.voice_plug:
            path = "plugins/" + i.get("name")

            if not os.path.exists(path):
                print(f"Error: core/registry.py [check_plugins] -> Plugin {path} not found")

        # TODO добавить еще для utility

    def get_plugins_list(self):
        with open("data/plugins.json", "r", encoding="utf-8") as f:
            result = json.load(f)

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
                print(
                    "Error: core/registry.py [plug_install] -> File is not a zip archive or is heavily corrupted."
                )

    def plug_remove(self):
        pass

    def plug_update(self):
        pass

    def voice_plug_start(self, voice_text):
        try:
            self.voice_plug = self.get_plugins_list().get("voice")
            for i in self.voice_plug:
                path = "plugins/" + i.get("name")

                with open(f"{path}/commands.json", "r", encoding="utf-8") as f:
                    file_config = json.load(f)

                with open(f"{path}/plugin.json", "r", encoding="utf-8") as f:
                    file_plug = json.load(f)

                # Импортируем плагины
                plugin_module = importlib.import_module(f"plugins.{i.get('name')}.main")
                plugin_class = getattr(plugin_module, file_plug["entry"])
                plugin_instance = plugin_class()

                # Проверка триггеров
                for command in file_config.get("commands", []):
                    if voice_text in command["triggers"]:
                        action = command.get("action")
                        # Вызов соответствующего метода
                        if hasattr(plugin_instance, action):
                            method = getattr(plugin_instance, action)
                            if callable(method):
                                method()
                        else:
                            print(
                                f"Error: core/registry.py [voice_plug_start] -> Action {action} not found in {i.get('name')} plugin."
                            )

        except Exception as e:
            print("Error: core/registry.py [voice_plug_start] -> ", e)

    def plug_start(self, flag, voice_text="None"):
        if flag == "voice":
            if voice_text == "None":
                print(
                    "Error: core/registry.py [plug_install] -> voice_text for voice commands: None"
                )
            else:
                self.voice_plug_start(voice_text)
        elif flag == "utility":
            pass


if __name__ == "__main__":
    start = Registry()
    start.get_plugins_list()

    start.voice_plug_start("здарова")

    # start.voice_plug_start("джарвис")
    # start.plug_install("test.zip")
