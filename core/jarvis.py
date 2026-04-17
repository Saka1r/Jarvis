# core/jarvis.py
import asyncio
import logging
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from enum import Enum, auto

from subsystems import audio_in
from subsystems.vosk_stt import Vosk_STT
from subsystems.coqui_tts import TTS_Manager
from subsystems.llama_llm import LlamaLLM
from core.registry import Registry

logger = logging.getLogger(__name__)

class AgentState(Enum):
    COMMAND = auto()  # Ожидание wake-word или команды плагина
    FREE = auto()     # Диалог с LLM
    SPEAKING = auto() # Воспроизведение ответа (STT временно отключен)

class Jarvis:
    def __init__(self):
        self.state = AgentState.COMMAND
        self._stop_event = asyncio.Event()
        self._tts_done_event = asyncio.Event()

        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="JarvisWorker")
        self.vosk: Optional[Vosk_STT] = None
        self.audio: Optional[audio_in.AudioOpen] = None
        self.reg: Optional[Registry] = None
        
        self.tts_manager = TTS_Manager()
        self.llm = LlamaLLM()
        self.commands_queue = asyncio.Queue(maxsize=10)

    @classmethod
    async def start(cls):
        """Точка входа. Вызывается через asyncio.run()"""
        self = cls()
        try:
            self.vosk = Vosk_STT()
            self.audio = audio_in.AudioOpen()
            self.reg = Registry()

            self.vosk.open()
            self.audio.open()
            self.llm.load()
            self.tts_manager.start()

            logger.info("🎤 Jarvis запущен. Ожидание команд...")
            await asyncio.gather(
                self._listen_loop(),
                self._process_loop()
            )
        finally:
            await self._cleanup()

    async def _listen_loop(self):
        """Производитель: читает аудио → STT → очередь. Пауза во время речи."""
        while not self._stop_event.is_set():
            # 🛡️ ЭХО-ПОДАВЛЕНИЕ: игнорируем микрофон, пока Джарвис говорит
            if self.state == AgentState.SPEAKING:
                await asyncio.sleep(0.15)
                continue

            try:
                data = await asyncio.to_thread(self.audio.read)
                if not data:
                    await asyncio.sleep(0.01)
                    continue

                text = await asyncio.to_thread(self.vosk.process, data)
                if text:
                    logger.debug(f"👂 STT: {text}")
                    try:
                        self.commands_queue.put_nowait(text)
                    except asyncio.QueueFull:
                        logger.warning("Очередь команд переполнена. Пропуск.")
            except Exception as e:
                logger.error(f"Audio/STT error: {e}")
                await asyncio.sleep(0.5)

    async def _process_loop(self):
        """Потребитель: берет команды, обрабатывает, управляет состоянием."""
        while not self._stop_event.is_set():
            try:
                text = await asyncio.wait_for(self.commands_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            try:
                await self.handle_input(text)
            except Exception as e:
                logger.error(f"Ошибка обработки команды: {e}")
                if self.state == AgentState.FREE:
                    self.state = AgentState.COMMAND
            finally:
                self.commands_queue.task_done()

    async def handle_input(self, text: str):
        text_lower = text.lower()

        if self.state == AgentState.COMMAND:
            if "джарвис" in text_lower:
                self.state = AgentState.FREE
                logger.info("🔓 Режим диалога активирован")
                return

            if self.reg.is_command(text):
                await asyncio.to_thread(self.reg.voice_plug_start, text)
            else:
                logger.info("⚠️ Команда не распознана")

        elif self.state == AgentState.FREE:
            logger.info(f"🤔 Думаю над фразой: {text}")
            self.state = AgentState.SPEAKING  # Блокируем STT до конца ответа
            try:
                response = await asyncio.to_thread(self.llm.generate, text)
                if response and response.strip():
                    logger.info(f"💬 Джарвис: {response}")
                    await self._speak_and_wait(response)
            except Exception as e:
                logger.error(f"LLM/TTS pipeline failed: {e}")
                self.tts_manager.add_to_queue("Произошла ошибка. Повторите команду.")
                await self._tts_done_event.wait()
            finally:
                self.state = AgentState.COMMAND
                logger.info("🔒 Режим диалога завершён")

    async def _speak_and_wait(self, text: str):
        """Асинхронно ждет завершения синтеза и воспроизведения."""
        self.state = AgentState.SPEAKING
        try:
            # 1. Кладем в синхронную очередь (не блокирует asyncio)
            self.tts_manager.queue.put_nowait(text)
            # 2. Ждем в отдельном потоке, пока _worker не вызовет task_done()
            await asyncio.to_thread(self.tts_manager.queue.join)
        except asyncio.QueueFull:
            logger.error("TTS queue full. Dropping speech.")
        except Exception as e:
            logger.error(f"Speech pipeline failed: {e}")
        finally:
            self.state = AgentState.COMMAND
            logger.info("🔒 Режим диалога завершён")

    async def _cleanup(self):
        """Гарантированное освобождение ресурсов"""
        logger.info("🛑 Остановка конвейера...")
        self._stop_event.set()
        
        self.tts_manager.stop()
        self.executor.shutdown(wait=True)
        
        if self.audio:
            self.audio.close()
        if self.vosk:
            self.vosk.close()
            
        logger.info("✅ Jarvis корректно остановлен.")