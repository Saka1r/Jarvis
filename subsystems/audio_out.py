#subsystem/audio_out.py
import logging
from pathlib import Path
import numpy as np
import sounddevice as sd
import torchaudio

logger = logging.getLogger(__name__)

class AudioOut:
    """Аудиовывод на базе sounddevice."""

    def __init__(self, device: int | None = None):
        self.device = device
        # sounddevice автоматически использует устройство по умолчанию, если device=None

    def play(self, file_path: str) -> None:
        """Блокирующее воспроизведение WAV-файла."""
        path = Path(file_path)
        if not path.exists():
            logger.error(f"❌ Аудиофайл не найден: {file_path}")
            return

        try:
            # 1. Загрузка в RAM. Файловый дескриптор закрывается СРАЗУ после этой строки.
            waveform, sr = torchaudio.load(str(path))

            # 2. Приведение к формату sounddevice (float32, mono)
            if waveform.dim() > 1:
                waveform = waveform.mean(dim=0, keepdim=True)  # Stereo → Mono
            audio_data = waveform.squeeze().numpy().astype(np.float32)

            # 3. Воспроизведение
            logger.debug(f"🔊 Play: {path.name} | SR: {sr} Гц | Длительность: {len(audio_data)/sr:.2f}с")
            sd.play(audio_data, samplerate=sr, device=self.device)
            sd.wait()  # ← ЖЁСТКАЯ БЛОКИРОВКА до конца звука

        except Exception as e:
            logger.error(f"💥 Ошибка воспроизведения {file_path}: {e}")

    def stop(self) -> None:
        """Экстренная остановка воспроизведения."""
        sd.stop()
        logger.info("⏹️ Воспроизведение прервано вручную")

