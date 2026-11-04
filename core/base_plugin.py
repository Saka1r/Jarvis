# core/base_plugin.py
import json
import logging
from typing import Any, Optional
from core.services import ServiceContainer

logger = logging.getLogger(__name__)

class BasePlugin:
    """
    Базовый класс для всех плагинов.
    Предоставляет доступ к подсистемам Jarvis через ServiceContainer.
    """
    
    def __init__(self, services: ServiceContainer = None, config: dict = None):
        self.services = services or ServiceContainer()
        self.config = config or self._load_default_config()
    
    # === Универсальный доступ к сервисам ===
    
    def get_service(self, name: str, default: Any = None) -> Any:
        """
        Получает сервис по имени.
        
        Примеры:
            stt = self.get_service("stt")
            rag = self.get_service("rag")
            memory = self.get_service("memory")
        """
        return self.services.get(name, default)
    
    def has_service(self, name: str) -> bool:
        """Проверяет, доступен ли сервис."""
        return self.services.has(name)
    
    # === Обратная совместимость (deprecated, но работает) ===
    
    @property
    def audio_out(self):
        """@deprecated: Используйте get_service('audio_out')"""
        return self.get_service("audio_out")
    
    @property
    def audio_in(self):
        """@deprecated: Используйте get_service('audio_in')"""
        return self.get_service("audio_in")
    
    @property
    def llm(self):
        """@deprecated: Используйте get_service('llm')"""
        return self.get_service("llm")
    
    @property
    def tts(self):
        """@deprecated: Используйте get_service('tts')"""
        return self.get_service("tts")
    
    @property
    def stt(self):
        """
        Возвращает текущий активный STT.
        @deprecated: Используйте get_service('stt') или get_service('stt_command')/get_service('stt_dialog')
        """
        return self.get_service("stt")
    
    # === Вспомогательные методы ===
    
    def _load_default_config(self) -> dict:
        """Загружает стандартную конфигурацию."""
        try:
            with open("config/system.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Конфиг config/system.json не найден")
            return {}
