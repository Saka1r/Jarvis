# subsystems/coqui_tts.py
import threading
import os
import queue
import uuid
import torch

from TTS.api import TTS as CoquiTTS
from subsystems.tts import TTS

class TTS_Manager:
    def __init__(self):
        self.tts = Coqui_TTS()
        self.queue = queue.Queue()
        self.is_playing = False
        self._thread = None

    def start(self):
        """Запускает фоновый поток для обработки очереди"""
        self.tts.open()
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()

    def add_to_queue(self, text):
        """Добавляет текст в очередь (вызывается из asyncio)"""
        self.queue.put(text)

    def _process_queue(self):
        """Фоновый поток: берет текст из очереди и говорит"""
        while True:
            text = self.queue.get()
            if text is None:
                break
            file_path = self.tts.generate(text)
            if file_path:
                self._play_audio(file_path)
                self.tts.cleanup(file_path)

    def _play_audio(self, file_path):
        """Воспроизведение"""
        pass

    def stop(self):
        self.queue.put(None)  # Сигнал остановки

class Coqui_TTS(TTS):
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.speaker_wav = "new_reference_jar.wav"
        self.output_dir = "data/output_wav"
        
        os.makedirs(self.output_dir, exist_ok=True)

    def open(self):
        """Ленивая загрузка модели (можно вызвать отдельно)"""
        try:
            print(f"Loading TTS model on {self.device}...")
            self.model = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
            print("TTS model loaded.")
            return True
        except Exception as e:
            print(f"Error loading TTS: {e}")
            return False

    def generate(self, text) -> str:
        """
        Генерирует аудио и возвращает ПУТЬ к файлу.
        """
        if self.model is None:
            raise RuntimeError("TTS model not loaded. Call open() first.")
        
        # Уникальное имя файла, чтобы не было конфликтов
        filename = f"jarvis_{uuid.uuid4().hex}.wav"
        file_path = os.path.join(self.output_dir, filename)
        
        try:
            self.model.tts_to_file(
                text=text, 
                speaker_wav=self.speaker_wav, 
                language="ru", 
                file_path=file_path
            )
            return file_path
        except Exception as e:
            print(f"TTS generation error: {e}")
            return None

    def cleanup(self, file_path):
        """Удаление файла после воспроизведения (чтобы не забивать диск)"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
