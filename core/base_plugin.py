# core/base_plugin.py

class BasePlugin:
    """Базовый класс для всех плагинов. Принимает и хранит ссылки на подсистемы Джарвиса."""
    def __init__(self, systems=None):
        self.systems = systems or {}
        
        # Для удобства выносим подсистемы в атрибуты, 
        # чтобы в плагинах писать self.llm, а не self.systems['llm']
        self.audio_out = self.systems.get("audio_out")
        self.audio_in = self.systems.get("audio_in")
        self.llm = self.systems.get("llm")
        self.tts = self.systems.get("tts")
        self.vosk = self.systems.get("vosk")