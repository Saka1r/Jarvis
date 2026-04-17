# subsystems/coqui_tts.py
import threading
import os
import queue
import uuid
import logging
import time  # Для retry-логики на Windows
import asyncio
from pathlib import Path
from typing import Optional

import torch
from TTS.api import TTS as CoquiAPI

from subsystems.tts import TTS
from subsystems.audio_out import AudioOut

logger = logging.getLogger(__name__)

class TTS_Manager:
    def __init__(self, audio_out=None):
        self.tts = Coqui_TTS()  # Ваш класс TTS
        self.queue = queue.Queue(maxsize=50)
        self.audio_out = audio_out or AudioOut()
        self._thread = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive(): return
        self.tts.open()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True, name="TTS-Worker")
        self._thread.start()

    def _worker(self) -> None:
        """Фоновый поток: берет текст → синтезирует → играет → освобождает файл."""
        while not self._stop_event.is_set():
            try:
                text = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None: break

            try:
                file_path = self.tts.generate(text)
                if file_path and Path(file_path).exists():
                    self.audio_out.play(file_path)  # sd.wait() блокирует ЗДЕСЬ
            except Exception as e:
                logger.error(f"TTS error: {e}")
            finally:
                self.tts.cleanup(file_path)
                self.queue.task_done()  # ← Сигнализирует queue.join(), что задача завершена

    def stop(self) -> None:
        self._stop_event.set()
        self.queue.put(None)
        if self._thread: self._thread.join(timeout=5.0)
        
class Coqui_TTS(TTS):
    """Обёртка над Coqui XTTS v2."""
    
    def __init__(self, 
                 speaker_wav: str = "data/new_reference_jar_micro_22050.wav", 
                 device: Optional[str] = None):
        # Принудительно используем CUDA, если доступно 
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.raw_speaker_wav = speaker_wav
        self.processed_speaker_wav: Optional[str] = None
        self.output_dir = "data/output_wav/"
        os.makedirs(self.output_dir, exist_ok=True)

    def open(self) -> bool:
        if self.model is not None:
            return True
        try:
            logger.info(f"Loading XTTS v2 on {self.device}...")
            self.model = CoquiAPI("tts_models/multilingual/multi-dataset/xtts_v2", 
                                  gpu=(self.device == "cuda"))
            logger.info("TTS model loaded successfully.")
            self.processed_speaker_wav = self.raw_speaker_wav
            return True
        except Exception as e:
            logger.error(f"Error loading TTS model: {e}")
            return False

    def generate(self, text: str) -> Optional[str]:
        if self.model is None:
            raise RuntimeError("TTS model not loaded. Call open() first.")

        filename = f"jarvis_{uuid.uuid4().hex[:12]}.wav"
        file_path = os.path.join(self.output_dir, filename)

        try:
            # ✅ Убран length_penalty — не поддерживается в tts_to_file()
            self.model.tts_to_file(
                text=text,
                speaker_wav=self.processed_speaker_wav,
                language="ru",
                file_path=file_path,
                temperature=0.8,
                repetition_penalty=1.15,
                top_k=50,
                top_p=0.9,
                speed=1.08,
                enable_text_splitting=True
            )
            logger.info(f"Generated: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None

    def cleanup(self, file_path: Optional[str]) -> None:
        """Удаление файла с обработкой WinError 32 (файл занят)."""
        if not file_path or not os.path.exists(file_path):
            return
        try:
            os.remove(file_path)
        except PermissionError as e:
            # Windows: файл может быть занят аудиоплеером
            logger.warning(f"File busy, retrying: {file_path}")
            for attempt in range(3):
                time.sleep(0.3)
                try:
                    os.remove(file_path)
                    return
                except:
                    continue
            logger.error(f"Failed to cleanup after retries: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path}: {e}")

if __name__ == "__main__":
    import sys
    import signal
    
    logging.basicConfig(
        level=logging.INFO, 
        format='%(levelname)s:%(name)s:%(message)s',
        stream=sys.stdout
    )
    
    # Обработка Ctrl+C для чистого выхода
    def signal_handler(sig, frame):
        logger.info("Interrupt received, shutting down...")
        if 'manager' in globals():
            manager.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    manager = TTS_Manager()
    manager.start()
    
    manager.ge("Голосовой интерфейс инициализирован.")
    manager.add_to_queue("Я готов к работе, сэр.")
    
    # Ждём завершения ВСЕХ задач в очереди
    manager.queue.join()
    print("✅ Все задачи выполнены.")
    
    manager.stop()
    
    print("👋 Джарвис завершил работу.")