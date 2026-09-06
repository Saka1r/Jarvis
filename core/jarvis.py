# core/jarvis.py
import asyncio
import logging
import json
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from enum import Enum, auto

from core.registry import Registry
from core.context import ContextManager

from subsystems import audio_in
from subsystems import audio_out
from subsystems.vosk_stt import Vosk_STT
from subsystems.coqui_tts import TTS_Manager
from subsystems.llm.factory import create_llm_provider

logger = logging.getLogger(__name__)

class AgentState(Enum):
    COMMAND = auto()  # Ожидание wake-word или команды плагина
    FREE = auto()     # Диалог с LLM
    SPEAKING = auto() # Воспроизведение ответа (STT временно отключен)
    WAIT = auto() # Ожидание wake-word для перехода в режим команд, то есть без реагирования

class Jarvis:
    def __init__(self, config_path: str = "config/system.json"):
        self.state = AgentState.COMMAND
        self._stop_event = asyncio.Event()
        self._tts_done_event = asyncio.Event()

        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="JarvisWorker")
        self.vosk: Optional[Vosk_STT] = None
        self.audio: Optional[audio_in.AudioOpen] = None
        self.audio_out = audio_out.AudioOut()
        
        self.tts_manager = TTS_Manager()

        self.config = self._load_config(config_path)
        self.llm = create_llm_provider(self.config.get("llm", {}))

        self.context = ContextManager(max_turns=6) 
        self.commands_queue = asyncio.Queue(maxsize=10)
        self.reg: Optional[Registry] = None

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Конфиг {config_path} не найден. Генерирую дефолтный...")
            from config import Config
            cfg = Config()
            cfg.start() # Создаст файлы, если их нет
            return cfg.standart_system
    
    @classmethod
    async def start(cls, config_path: str = "config/system.json"):
        """Точка входа. Вызывается через asyncio.run()"""
        self = cls(config_path)
        try:
            self.vosk = Vosk_STT()
            self.audio = audio_in.AudioOpen()
            self.reg = Registry(systems={
                "audio_out": self.audio_out,
                "llm": self.llm,
                "tts": self.tts_manager,
                "vosk": self.vosk,
                "audio_in": self.audio
            })

            self.vosk.open()
            self.audio.open()
            self.llm.load()
            self.tts_manager.start()

            self.vosk.set_grammar()

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

        # ____________________ РЕЖИМ КОМАНД ____________________
        if self.state == AgentState.COMMAND:
            # ___ ПЕРЕХОД В LLM ___
            if "режим диалога" in text_lower:
                self.state = AgentState.FREE
                self.vosk.clear_grammar()
                logger.info("🔓 Режим диалога активирован")
                self.audio_out.play("data/jarvis_wav/yes_sir.wav")
                return
            
            if "режим ожидания" in text_lower:
                self.state = AgentState.WAIT
                self.vosk.clear_grammar()
                logger.info("🔓 Режим ожидания активирован")
                self.audio_out.play("data/jarvis_wav/yes_sir.wav")
                return

            if self.reg.is_command(text):
                await asyncio.to_thread(self.reg.voice_plug_start, text)
            else:
                logger.info("⚠️ Команда не распознана")

        # ____________________ РЕЖИМ ОЖИДАНИЯ ____________________
        if self.state == AgentState.WAIT:
            if "отключить режим ожидания" in text_lower or "джарвис" in text_lower:
                self.state = AgentState.COMMAND
                self.vosk.set_grammar()
                logger.info("🔓 Режим команд активирован")
                self.audio_out.play("data/jarvis_wav/yes_sir.wav")
                return

        # ____________________ РЕЖИМ LLM ____________________
        elif self.state == AgentState.FREE:
            logger.info(f"🤔 Думаю над фразой: {text}")
            self.state = AgentState.SPEAKING
            
            self.context.add_message("user", text)
            
            try:
                messages_for_llm = self.context.get_messages_for_llm()
                raw_response = await self.llm.async_generate(context_messages=messages_for_llm)
                
                thought = ""
                speech = ""
                
                if "<thought>" in raw_response and "</thought>" in raw_response:
                    thought = raw_response.split("<thought>")[1].split("</thought>")[0].strip()
                
                if "<response>" in raw_response and "</response>" in raw_response:
                    speech = raw_response.split("<response>")[1].split("</response>")[0].strip()
                else:
                    speech = raw_response.strip()

                if thought:
                    logger.info(f"🧠 МЫСЛИ ДЖАРВИСА: {thought}")
                
                if speech and speech.strip():
                    logger.info(f"💬 ДЖАРВИС ГОВОРИТ: {speech}")
                    self.context.add_message("assistant", speech)
                    await self._speak_and_wait(speech)
            except Exception as e:
                logger.error(f"LLM/TTS pipeline failed: {e}")
                try:
                    self.tts_manager.queue.put_nowait("Произошла ошибка, сэр. Повторите команду.")
                    await self._tts_done_event.wait()
                except Exception as tts_error:
                    logger.error(f"TTS queue error: {tts_error}")
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