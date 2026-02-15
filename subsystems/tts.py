#subsystems/tts.py

from abc import ABC, abstractmethod

class TTS(ABC):
    '''Абстрактный класс'''
    def __init__(self):
        pass

    @abstractmethod
    def generate(self, text) -> str:
        '''Тут генерируется голос на основе текста'''
        pass
