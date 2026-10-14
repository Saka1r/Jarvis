# tests/conftest.py
import sys
from unittest.mock import MagicMock

# Мокаем все тяжелые ML и аудио библиотеки ДО начала импорта тестов
# Это предотвращает ModuleNotFoundError при сборке (collection)

# PyTorch и аудио
sys.modules['torch'] = MagicMock()
sys.modules['torch.cuda'] = MagicMock()
sys.modules['torchaudio'] = MagicMock()
sys.modules['torchaudio.functional'] = MagicMock()

# Трансформеры и TTS
sys.modules['transformers'] = MagicMock()
sys.modules['TTS'] = MagicMock()
sys.modules['TTS.api'] = MagicMock()
sys.modules['TTS.tts'] = MagicMock()
sys.modules['TTS.tts.configs'] = MagicMock()
sys.modules['TTS.tts.models'] = MagicMock()

# STT и системное аудио
sys.modules['vosk'] = MagicMock()
sys.modules['sounddevice'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()

# Векторные БД (на будущее, если вдруг подтянутся)
sys.modules['chromadb'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()