# subsystems/stt/whisper_provider.py
import logging
import numpy as np
import torch
import os
from typing import Optional
from faster_whisper import WhisperModel
from subsystems.stt.base import BaseSTT

logger = logging.getLogger(__name__)


class WhisperProvider(BaseSTT):
    """
    Whisper STT с локальным VAD-детектором (Silero).
    Работает полностью офлайн после первоначальной загрузки модели.
    """
    
    def __init__(self, config: dict):
        self.model_size = config.get("model_size", "small")
        # Определяем устройство, но с проверкой доступности CUDA
        self.device = "cuda" if (config.get("device", "cuda") == "cuda" and torch.cuda.is_available()) else "cpu"
        self.compute_type = config.get("compute_type", "float16")
        
        # Настройки VAD
        self.silence_threshold = config.get("silence_threshold", 0.5)
        self.silence_duration_ms = config.get("silence_duration_ms", 1000)
        self.max_speech_duration_s = config.get("max_speech_duration_s", 30)
        
        # Параметры аудио
        self.sample_rate = 16000
        self.chunk_size = 512  # Silero VAD требует 512 сэмплов
        
        # Состояние
        self.audio_buffer = []
        self.buffer_samples = 0
        self.silence_samples = 0
        self.is_speaking = False
        
        # Модели
        self.whisper_model = None
        self.vad_model = None
        self.is_open = False

    def open(self) -> bool:
        if self.is_open:
            return True
        
        try:
            # 1. Загружаем Whisper
            logger.info(f"⏳ Загрузка Whisper ({self.model_size}) на {self.device}...")
            self.whisper_model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root="data/models/whisper"
            )
            
            # 2. Загружаем Silero VAD ЛОКАЛЬНО (TorchScript)
            vad_model_path = "data/models/silero_vad/silero_vad.jit"
            
            if not os.path.exists(vad_model_path):
                logger.error(f"❌ Silero VAD модель не найдена: {vad_model_path}")
                logger.error("Запусти 'python download_silero_vad.py' для её загрузки (нужен интернет один раз).")
                return False
            
            logger.info(f"⏳ Загрузка Silero VAD из локального файла на {self.device}...")
            self.vad_model = torch.jit.load(vad_model_path)
            self.vad_model.eval()
            
            # Явно перемещаем модель на нужное устройство
            self.vad_model = self.vad_model.to(self.device)
            
            self.is_open = True
            logger.info(f"✅ Whisper + Silero VAD загружены локально (устройство: {self.device})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}", exc_info=True)
            return False

    def process(self, audio_data: bytes) -> str:
        """
        Обрабатывает аудио chunk за chunk.
        Возвращает распознанный текст ТОЛЬКО когда пользователь замолчал.
        """
        if not self.is_open:
            return ""
        
        try:
            # Преобразуем байты в numpy int16
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Silero VAD требует ровно 512 сэмплов
            for i in range(0, len(audio_array), self.chunk_size):
                chunk = audio_array[i:i + self.chunk_size]
                
                # Если последний чанк меньше 512 — дополняем нулями
                if len(chunk) < self.chunk_size:
                    chunk = np.pad(chunk, (0, self.chunk_size - len(chunk)))
                
                # Создаём тензор
                audio_tensor = torch.FloatTensor(chunk) / 32768.0
                
                audio_tensor = audio_tensor.to(self.device)
                
                # Определяем вероятность голоса
                confidence = self.vad_model(audio_tensor, self.sample_rate).item()
                is_voice = confidence > self.silence_threshold
                
                if is_voice:
                    # Голос detected — добавляем в буфер
                    self.audio_buffer.append(chunk)
                    self.buffer_samples += len(chunk)
                    self.silence_samples = 0
                    self.is_speaking = True
                    
                else:
                    # Тишина
                    if self.is_speaking:
                        # Всё ещё добавляем тишину в буфер (она часть фразы)
                        self.audio_buffer.append(chunk)
                        self.buffer_samples += len(chunk)
                        self.silence_samples += len(chunk)
                        
                        # Проверяем, не закончил ли пользователь говорить
                        silence_ms = (self.silence_samples / self.sample_rate) * 1000
                        speech_duration_s = self.buffer_samples / self.sample_rate
                        
                        # Конец фразы: пауза >= silence_duration_ms ИЛИ достигнут максимум
                        if silence_ms >= self.silence_duration_ms or speech_duration_s >= self.max_speech_duration_s:
                            return self._transcribe_buffer()
            
            return ""
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки аудио: {e}", exc_info=True)
            self._reset_buffer()
            return ""

    def _transcribe_buffer(self) -> str:
        """Транскрибирует накопленный буфер через Whisper."""
        if not self.audio_buffer:
            self._reset_buffer()
            return ""
        
        try:
            # Объединяем все чанки
            full_audio = np.concatenate(self.audio_buffer)
            audio_float = full_audio.astype(np.float32) / 32768.0
            
            # Очищаем буфер ПЕРЕД транскрипцией
            self._reset_buffer()
            
            # Транскрибируем
            segments, info = self.whisper_model.transcribe(
                audio_float,
                beam_size=5,
                language="ru",
                vad_filter=False,  # Мы уже используем свой VAD
                condition_on_previous_text=True
            )
            
            text = " ".join([segment.text.strip() for segment in segments]).strip()
            
            if text:
                logger.debug(f"🎙️ Whisper распознал: {text}")
            
            return text
            
        except Exception as e:
            logger.error(f"❌ Ошибка транскрипции: {e}", exc_info=True)
            return ""

    def _reset_buffer(self):
        """Очищает буфер и сбрасывает состояние."""
        self.audio_buffer = []
        self.buffer_samples = 0
        self.silence_samples = 0
        self.is_speaking = False

    def force_transcribe(self) -> str:
        """Принудительно транскрибирует текущий буфер."""
        if self.audio_buffer:
            return self._transcribe_buffer()
        return ""

    def close(self):
        if self.audio_buffer:
            self.force_transcribe()
        
        self.whisper_model = None
        self.vad_model = None
        self.is_open = False
        self._reset_buffer()
        logger.info("🛑 Whisper + VAD ресурсы освобождены")

    def set_grammar(self, grammar_path: str = None):
        pass

    def clear_grammar(self):
        pass
