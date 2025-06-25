import json
import os
import importlib
import zipfile
from tqdm import tqdm

def check_dir_modules():
    list_dir = os.listdir()
    print(list_dir)
    if not os.path.exists("modules"):
        # Создаем папку
        os.makedirs("modules")
        print("directory created")
    else:
        print("the directory has already been created")
                

def check_dir(file_path):
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    else:
        print(f"the directory {file_path} already exists")

def install_module(path_to_zip):
    print(f"install module -> {path_to_zip}")
    
    extract_to = 'modules'

    check_dir(extract_to)

    with zipfile.ZipFile(path_to_zip, 'r') as zip_ref:
        file_list = zip_ref.infolist()
        total_files = len(file_list)
        
        # Progress bar
        with tqdm(total=total_files, desc='Распаковка') as pbar:
            for file_info in file_list:
                zip_ref.extract(file_info, path=extract_to)
                pbar.update(1)
                
def remove_module():
    pass

def init_module(config):

    NoVoiceCommands = config.get('NonVoiceCommands', [])
    
    imported_modules = {}

    for name in NoVoiceCommands:
        try:
            print(name)
            
            module_name = f"modules.{name}.__main__"

            module = importlib.import_module(module_name)
            imported_modules[name] = module
            print(f"Module {module_name} successfully imported")
        except ImportError:
            print(f"Failed to import module {module_name}")

    for name, module in imported_modules.items():
        if hasattr(module, 'run'):
            print(f"Start module {name}")
            module.run()
        else:
            print("Non run function")


def read_module():
    
    with open("config_files/config.json", "r", encoding='utf-8') as f:
        config = json.load(f)

    return config


def create_module():
    pass

if __name__ == '__main__':
    read_module()