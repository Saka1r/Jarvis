#subsystems/llm/base.py

from abc import ABC, abstractmethod
from typing import List, Dict

class BaseLLM(ABC):
    """Абстрактный интерфейс для всех LLM провайдеров."""

    @abstractmethod
    async def async_generate(self, context_messages: List[Dict]) -> str:
        """Асинхронная генерация ответа."""
        pass
    
    @abstractmethod
    def load(self) -> bool:
        """Загрузка модели."""
        pass
    
    @abstractmethod
    def unload(self):
        """Выгрузка модели."""
        pass