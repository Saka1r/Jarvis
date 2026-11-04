# subsystems/vosk_stt.py
import json
import logging
import threading
from typing import Iterable, Optional, Any

from vosk import Model, KaldiRecognizer

from subsystems.stt.base import BaseSTT

logger = logging.getLogger(__name__)

SYSTEM_TRIGGERS = [
    "джарвис",
    "режим ожидания",
    "режим диалога",
    "отключить режим ожидания",
]


class Vosk_STT(BaseSTT):
    """
    Vosk STT provider.

    Совместим с двумя вариантами инициализации:

    Старый:
        Vosk_STT("data/models/vosk", 16000)

    Новый через factory:
        Vosk_STT({
            "model_path": "data/models/vosk-model-small-ru-0.22",
            "sample_rate": 16000
        })
    """

    def __init__(
        self,
        config: Optional[dict[str, Any] | str] = None,
        sample_rate: int = 16000,
    ):
        # Поддержка старого вызова Vosk_STT("path/to/model")
        if isinstance(config, str):
            self.model_path = config
            self.sample_rate = sample_rate
        else:
            config = config or {}
            self.model_path = config.get("model_path", "data/models/vosk")
            self.sample_rate = int(config.get("sample_rate", sample_rate))

        self.model = None
        self.recognizer = None

        self.accumulated_text = ""
        self.commands: list[str] = []

        self._grammar_enabled = False
        self._lock = threading.RLock()

    def open(self) -> bool:
        """Загружает Vosk model и создаёт recognizer без грамматики."""
        with self._lock:
            if self.recognizer is not None:
                return True

            try:
                logger.info(f"⏳ Загрузка Vosk модели: {self.model_path}")
                self.model = Model(self.model_path)
                self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
                self.accumulated_text = ""
                self._grammar_enabled = False

                logger.info("✅ Vosk модель загружена успешно")
                return True

            except Exception as e:
                logger.error(f"❌ Vosk init error: {e}", exc_info=True)
                self.model = None
                self.recognizer = None
                return False

    def close(self) -> None:
        """Освобождает ресурсы Vosk."""
        with self._lock:
            self.recognizer = None
            self.model = None
            self.accumulated_text = ""
            self._grammar_enabled = False
            logger.info("🛑 Vosk ресурсы освобождены")

    def set_commands(self, commands: Iterable[str]) -> None:
        """
        Core/Jarvis передаёт сюда команды плагинов.
        STT сам НЕ должен создавать Registry.
        """
        normalized = []
        for command in commands:
            if not isinstance(command, str):
                continue
            command = command.strip().lower()
            if command:
                normalized.append(command)

        self.commands = list(dict.fromkeys(normalized))
        logger.debug(f"📥 Vosk получил {len(self.commands)} команд для грамматики")

    def _rebuild_recognizer(self, grammar: Optional[list[str]] = None) -> None:
        """
        Пересоздаёт recognizer.

        Важно:
        В Vosk надёжнее менять грамматику через создание нового KaldiRecognizer,
        чем пытаться динамически вызывать SetGrammar.
        """
        if self.model is None:
            raise RuntimeError("Vosk model not opened")

        self.accumulated_text = ""

        if grammar:
            grammar_json = json.dumps(grammar, ensure_ascii=False)
            self.recognizer = KaldiRecognizer(
                self.model,
                self.sample_rate,
                grammar_json,
            )
            self._grammar_enabled = True
        else:
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self._grammar_enabled = False

    def set_grammar(self, commands: Optional[Iterable[str]] = None) -> None:
        """
        Включает грамматику командного режима.

        Если commands переданы — использует их.
        Если нет — использует ранее загруженные self.commands + SYSTEM_TRIGGERS.
        """
        with self._lock:
            if self.recognizer is None:
                raise RuntimeError("Recognizer not opened")

            if commands is not None:
                self.set_commands(commands)

            merged = list(dict.fromkeys(
                [cmd.lower().strip() for cmd in self.commands if cmd.strip()]
                + SYSTEM_TRIGGERS
            ))

            if not merged:
                logger.warning("⚠️ Grammar ON запрошен, но список команд пуст")
                merged = SYSTEM_TRIGGERS

            self._rebuild_recognizer(grammar=merged)

            logger.info(
                f"🔧 Grammar ON: {len(merged)} triggers loaded "
                f"({len(self.commands)} plugins + {len(SYSTEM_TRIGGERS)} system)"
            )

    def clear_grammar(self) -> None:
        """
        Отключает грамматику и возвращает свободное распознавание.

        Важно:
        SetGrammar("[]") может означать "запретить всё".
        Поэтому для свободного режима пересоздаём recognizer БЕЗ grammar.
        """
        with self._lock:
            if self.recognizer is None:
                raise RuntimeError("Recognizer not opened")

            self._rebuild_recognizer(grammar=None)
            logger.info("🔓 Grammar OFF: free dialog mode")

    def accept_audio(self, audio_bytes: bytes) -> None:
        """Принимает аудио chunk и накапливает финальные результаты Vosk."""
        with self._lock:
            if self.recognizer is None:
                raise RuntimeError("Recognizer not opened")

            if self.recognizer.AcceptWaveform(audio_bytes):
                result = json.loads(self.recognizer.Result())
                new_text = result.get("text", "").strip()

                if new_text:
                    self.accumulated_text += new_text + " "

    def process(self, audio_bytes: bytes) -> str:
        """
        Основной метод BaseSTT.
        Возвращает финальный текст, если Vosk завершил фразу.
        Иначе возвращает пустую строку.
        """
        try:
            self.accept_audio(audio_bytes)
            return self.get_result()
        except Exception as e:
            logger.error(f"❌ Vosk process error: {e}", exc_info=True)
            return ""

    def get_result(self) -> str:
        """Возвращает накопленный текст и очищает буфер."""
        with self._lock:
            result = self.accumulated_text.strip()
            self.accumulated_text = ""
            return result
