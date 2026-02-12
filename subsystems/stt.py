#subsystem/stt.py

from abc import ABC, abstractmethod

class STT(ABC):

    """Абстрактный интерфейс"""

    @abstractmethod
    def open(self) -> bool:
        """Иницилизация движка, при успехе - True"""
        pass

    @abstractmethod
    def close(self) -> None:
        """Освободить ресурсы"""
        pass

    @abstractmethod
    def accept_audio(self, audio_bytes: bytes) -> None:
        """Передать сырые аудиоданные (например PCM16)."""
        pass

    @abstractmethod
    def get_result(self) -> str:
        """Вернуть финальный текст (или пустую строку)."""
        pass

