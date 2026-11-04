# core/services.py
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class ServiceContainer:
    """
    Контейнер сервисов (Dependency Injection Container).
    Хранит и предоставляет доступ к подсистемам Jarvis по имени.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any, override: bool = False) -> None:
        """
        Регистрирует сервис в контейнере.
        
        Args:
            name: Имя сервиса (например, "stt", "llm", "rag")
            service: Экземпляр сервиса
            override: Разрешить перезапись существующего сервиса
        """
        if name in self._services and not override:
            logger.warning(f"Сервис '{name}' уже зарегистрирован. Используйте override=True для перезаписи.")
            return
        
        self._services[name] = service
        logger.debug(f"✅ Зарегистрирован сервис: {name}")
    
    def get(self, name: str, default: Any = None) -> Any:
        """
        Получает сервис по имени.
        
        Args:
            name: Имя сервиса
            default: Значение по умолчанию, если сервис не найден
        
        Returns:
            Экземпляр сервиса или default
        """
        return self._services.get(name, default)
    
    def has(self, name: str) -> bool:
        """Проверяет, зарегистрирован ли сервис."""
        return name in self._services
    
    def list_services(self) -> list:
        """Возвращает список зарегистрированных сервисов."""
        return list(self._services.keys())
