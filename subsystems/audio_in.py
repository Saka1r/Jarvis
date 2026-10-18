# subsystem/audio_in.py
import pyaudio
import threading
import logging

logger = logging.getLogger(__name__)


class AudioOpen:
    def __init__(self, rate=16000, channels=1, frames_per_buffer=8000, format=pyaudio.paInt16):

        self.rate = rate
        self.channels = channels
        self.frames_per_buffer = frames_per_buffer
        self.format = format

        self._pyaudio = None
        self.stream = None
        self.is_streaming = False
        self._lock = threading.Lock()

    def open(self):
        """Открывает аудио поток true/false"""
        with self._lock:
            if self.is_streaming:
                return True

            try:
                self._pyaudio = pyaudio.PyAudio()
                self.stream = self._pyaudio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.frames_per_buffer,
                )
                self.is_streaming = True
                return True

            except Exception:
                logger.exception(
                    "Error: subsystem/audio_in.py [open] -> Failed to open audio stream"
                )
                self.close()
                return False

    def read(self, num_frames=None):
        """Читает данные из аудио потока, возрашает данные"""
        with self._lock:
            if not self.is_streaming or self.stream is None:
                raise RuntimeError("Error: subsystem/audio_in.py [read] -> Stream is not open")
            n = num_frames or self.frames_per_buffer
            return self.stream.read(n, exception_on_overflow=False)

    def close(self) -> None:
        """Закрывает поток"""
        logger.info("Закрытие аудиовыхода...")
        try:
            if self.stream:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
                self.stream = None

            if self._pyaudio:
                self._pyaudio.terminate()
                self._pyaudio = None

            self.is_streaming = False
            logger.info("Аудиовыход освобожден")
        except Exception as e:
            logger.error("Ошибка при закрытие потока: {e}")