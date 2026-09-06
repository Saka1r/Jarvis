# config.py
import json
import os

class Config:
    def __init__(self):
        self.standart_plugins = {
            "voice": [{"name": "jarvis", "version": "1.0", "enabled": True}],
            "utility": [],
        }

        self.standart_setting = {"engine": "vosk", "language": "ru"}

        self.standart_system = {
            "llm": {
                "provider": "llama_server",  # "llama_cpp" или "llama_server"
                "llama_cpp": {
                    "model_path": "data/models/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf",
                    "n_ctx": 4096,
                    "n_gpu_layers": -1,
                    "n_threads": 8,
                    "n_batch": 1024,
                    "max_tokens": 256
                },
                "llama_server": {
                    "url": "http://127.0.0.1:8080",
                    "max_tokens": 256,
                    "temperature": 0.1,
                    "timeout": 60
                }
            },
            "tts": {
                "provider": "coqui",  # "coqui" или "piper" (в будущем)
                "coqui": {
                    "model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
                    "speaker_wav": "data/voices/jarvis_reference.wav",
                    "language": "ru"
                },
                "piper": {
                    "model_path": "data/models/piper/ru-RU-irina-medium.onnx"
                }
            },
            "stt": {
                "provider": "vosk",
                "vosk": {
                    "model_path": "data/models/vosk-model-small-ru-0.22",
                    "sample_rate": 16000
                }
            }
        }

    def generate_system_config(self):
        with open("config/system.json", "w", encoding="utf-8") as f:
            json.dump(self.standart_system, f, indent=4, ensure_ascii=False)

    def generate_setting_config(self):
        with open("data/setting.json", "w", encoding="utf-8") as f:
            json.dump(self.standart_setting, f, indent=4, ensure_ascii=False)

    def generate_plugins_config(self):
        with open("data/plugins.json", "w", encoding="utf-8") as f:
            json.dump(self.standart_plugins, f, indent=4, ensure_ascii=False)

    def check_status(self):
        """проверяет файлы конфигурации, системы, плагинов"""

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
