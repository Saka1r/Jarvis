# core/base_plugin.py
import json

class BasePlugin:
    """Базовый класс для всех плагинов. Принимает и хранит ссылки на подсистемы Джарвиса."""
    def __init__(self, systems=None, config=None):
        self.systems = systems or {}
        self.config = config or self._load_default_config()
        
        # Для удобства выносим подсистемы в атрибуты
        self.audio_out = self.systems.get("audio_out")
        self.audio_in = self.systems.get("audio_in")
        self.llm = self.systems.get("llm")
        self.tts = self.systems.get("tts")
        self.vosk = self.systems.get("vosk")
    
    def _load_default_config(self) -> dict:
        """Загружает конфиг по умолчанию."""
        try:
            with open("config/system.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}