import json
import os
from termcolor import colored

CONFIG_NAME = "config.json"

JSON_STANDART = {"OS": os.name, "Path": os.getcwd(), "Commands": ["HelloSir"], "NonVoiceCommands": ["simple_write"]}
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
    else:
        flag_dir = False
        return flag_dir

def create_config():
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
            json.dump(JSON_STANDART, f, indent=4)
        print(colored("Config file created", "yellow"))

def parser_json():
    with open("config_files/config.json", "r") as f:
        list = json.load(f)
        print(list)
