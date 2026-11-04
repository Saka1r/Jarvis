#subsystem/stt/base.py

from abc import ABC, abstractmethod

class BaseSTT(ABC):
    @abstractmethod
    def open(self) -> bool:
        """Иницилизация модели и ресурсов."""
        pass
    
    @abstractmethod
    def process(self, audio_data: bytes) -> str:
        """Распознавание аудио. Возращает текст или пустую строку."""
        pass

    @abstractmethod
    def close(self):
        """Освобождение ресурсов."""
        pass

    @abstractmethod
    def set_grammar(self, grammar_path: str):
        """Опционально: установка грамматики (для Vosk)."""
        pass

    @abstractmethod
    def clear_grammar(self):
        """Опционально: сброс грамматики (для свободного режима)."""
        pass
