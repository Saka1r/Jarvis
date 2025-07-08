import json
import os
from termcolor import colored

CONFIG_NAME = "config.json"

flag_dir = False

def check_files():
    global flag_dir
    list_dir = os.listdir()
    print(list_dir)
    if 'config_files' in list_dir:
        if 'config.json' in os.listdir('config_files'):
            print(colored("The config already exists", "green"))
            flag_dir = True
        else:
            print(colored("config_files exist but config.json not found", "red"))
            flag_dir = False
            return flag_dir
    else:
        flag_dir = False
        return flag_dir

def create_config(key_pico):

    standart_modules = {
        "я вернулся": "HelloSir",
        "увеличить звук": "SoundUp",
        "уменьшить звук": "SoundDown",
        "выключить звук": "SoundOff",
        "открой ютуб": "OpenYoutube",
        "открой телегу": "OpenTelegram"
    }

    JSON_STANDART = {"OS": os.name, "Path": os.getcwd(), "Key_Picovoice": key_pico, "Commands": standart_modules, "NonVoiceCommands": [None]}
    
    out = check_files()
    if out:
        return
    else:
        if not os.path.exists("config_files"):
            os.mkdir("config_files")
            print(colored("Modules directory created", "green"))
        else:
            print(colored("config_files directory already created.", "green"))
        with open(os.path.join("config_files", CONFIG_NAME), "w") as f:
            json.dump(JSON_STANDART, f, indent=4, ensure_ascii=False)
        print(colored("Config file created", "yellow"))

def parser_json():
    with open("config_files/config.json", "r", encoding='utf-8') as f:
        list = json.load(f)
        print(list)
    return list
if __name__ == '__main__':
    create_config("21376156das")
    parser_json()
