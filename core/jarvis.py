# core/jarvis.py
import asyncio
import logging
import json
import time
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List, Dict, Any

from core.registry import Registry
from core.context import ContextManager
from core.services import ServiceContainer
from core.llm_wrapper import LLMWrapper, CircuitBreakerConfig
from subsystems.stt.factory import create_stt_provider  # <-- ВАЖНО: добавлен импорт
from subsystems import audio_in
from subsystems import audio_out
from subsystems.coqui_tts import TTS_Manager
from subsystems.llm.factory import create_llm_provider

logger = logging.getLogger(__name__)

# Константы для Tool Calling
MAX_TOOL_ROUNDS = 2
MAX_TOOLS_PER_ROUND = 2
LLM_TIMEOUT_SECONDS = 30

class AgentState(Enum):
    COMMAND = auto()  # Ожидание wake-word или команды плагина (Vosk + grammar)
    FREE = auto()     # Диалог с LLM (Whisper)
    SPEAKING = auto() # Воспроизведение ответа (STT временно отключен)
    WAIT = auto()     # Глубокий сон, ждём "джарвис"

class Jarvis:
    def __init__(self, config_path: str = "config/system.json"):
        self.state = AgentState.COMMAND
        self._stop_event = asyncio.Event()
        self._tts_done_event = asyncio.Event()
        
        self.config = self._load_config(config_path)
        
        self.context = ContextManager(
                storage_path="data/context.json",
                max_turns=6,
                max_facts=100
        )
        raw_llm = create_llm_provider(self.config.get("llm", {}))
        self.llm = LLMWrapper(
                llm_instance=raw_llm,
                timeout=30,
                fallback_message="Прошу прощения сэр. Не могу подключиться к модели.",
                circuit_breaker_config=CircuitBreakerConfig(
                    failure_threshold=5,
                    recovery_timeout=60,
                    success_threshold=2
                )
        )
        self.tts_manager = TTS_Manager()
        
        stt_config = self.config.get("stt", {})
        self.stt_command = create_stt_provider({
            "provider": stt_config.get("command_provider", "vosk"),
            "vosk": stt_config.get("vosk", {})
        })
        self.stt_dialog = create_stt_provider({
            "provider": stt_config.get("dialog_provider", "whisper"),
            "whisper": stt_config.get("whisper", {})
        })
        
        self.current_stt = self.stt_command
        
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="JarvisWorker")
        self.audio: Optional[audio_in.AudioOpen] = None
        self.audio_out = audio_out.AudioOut()
        self.commands_queue = asyncio.Queue(maxsize=10)
        
        # ServiceContainer будет создан в start(), но объявим тип для IDE
        self.services: Optional[ServiceContainer] = None
        self.reg: Optional[Registry] = None

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Конфиг {config_path} не найден. Генерирую дефолтный...")
            from config import Config
            cfg = Config()
            cfg.start()
            return cfg.standart_system
    
    @classmethod
    async def start(cls, config_path: str = "config/system.json"):
        """Точка входа. Вызывается через asyncio.run()"""
        self = cls(config_path)
        try:
            self.audio = audio_in.AudioOpen()
            
            # Создаём и наполняем ServiceContainer
            self.services = ServiceContainer()
            self.services.register("audio_out", self.audio_out)
            self.services.register("audio_in", self.audio)
            self.services.register("llm", self.llm)
            self.services.register("tts", self.tts_manager)
            self.services.register("stt_command", self.stt_command)
            self.services.register("stt_dialog", self.stt_dialog)
            self.services.register("stt", self.current_stt)
            
            self.reg = Registry(services=self.services)
            if hasattr(self.stt_command, "set_commands"):
                self.stt_command.set_commands(self.reg.commands)
                logger.info(f"📜 Передано {len(self.reg.commands)} команд в STT")

            # Затем открывай STT и ставь грамматику
            if not self.stt_command.open():
                raise RuntimeError("Failed to initialize command STT")

            # Запускаем подсистемы
            self.audio.open()
            self.llm.load()
            self.tts_manager.start()
            
            # ✅ ИСПРАВЛЕНО: Инициализируем STT с проверкой и логированием
            logger.info("🎙️ Инициализация STT провайдеров...")
            
            # Инициализируем командный STT (Vosk)
            if not self.stt_command.open():
                logger.error("❌ Не удалось инициализировать командный STT (Vosk)")
                raise RuntimeError("Failed to initialize command STT")
            logger.info(f"✅ Командный STT инициализирован: {self.stt_command.__class__.__name__}")
            
            # Инициализируем диалоговый STT (Whisper)
            if not self.stt_dialog.open():
                logger.error("❌ Не удалось инициализировать диалоговый STT (Whisper)")
                raise RuntimeError("Failed to initialize dialog STT")
            logger.info(f"✅ Диалоговый STT инициализирован: {self.stt_dialog.__class__.__name__}")
            
            # Устанавливаем грамматику для командного режима
            self.stt_command.set_grammar()
            logger.info("📜 Грамматика командного режима установлена")

            logger.info("🎤 Jarvis запущен. Ожидание команд...")
            await asyncio.gather(
                self._listen_loop(),
                self._process_loop()
            )
        except asyncio.CancelledError:
            logger.info("⚠️ Задачи отменены (нормальное завершение)")
        except KeyboardInterrupt:
            logger.info("⚠️ Получен сигнал остановки")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при запуске: {e}", exc_info=True)
            raise
        finally:
            await self._cleanup()
    async def _listen_loop(self):
        """Производитель: читает аудио → STT → очередь."""
        while not self._stop_event.is_set():
            if self.state == AgentState.SPEAKING:
                await asyncio.sleep(0.15)
                continue

            try:
                data = await asyncio.to_thread(self.audio.read)
                if not data:
                    await asyncio.sleep(0.01)
                    continue

                # ИСПРАВЛЕНО: используем current_stt вместо захардкоженного self.vosk
                text = await asyncio.to_thread(self.current_stt.process, data)
                if text:
                    logger.debug(f"👂 STT ({self.current_stt.__class__.__name__}): {text}")
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
                logger.error(f"Ошибка обработки команды: {e}", exc_info=True)
                # Fallback в безопасное состояние при любой ошибке
                await self._force_command_mode()
            finally:
                self.commands_queue.task_done()

    async def handle_input(self, text: str):
        text_lower = text.lower()

        # ____________________ РЕЖИМ КОМАНД ____________________
        if self.state == AgentState.COMMAND:
            if "режим диалога" in text_lower:
                await self._switch_to_dialog_mode()
                return
            
            if "режим ожидания" in text_lower:
                self.state = AgentState.WAIT
                self.current_stt.clear_grammar()
                logger.info("💤 Режим ожидания активирован")
                await asyncio.to_thread(self.audio_out.play, "data/jarvis_wav/yes_sir.wav")
                return

            if self.reg.is_command(text):
                await asyncio.to_thread(self.reg.voice_plug_start, text)
            else:
                logger.info("⚠️ Команда не распознана")

        # ____________________ РЕЖИМ ОЖИДАНИЯ ____________________
        elif self.state == AgentState.WAIT:
            if "отключить режим ожидания" in text_lower or "джарвис" in text_lower:
                await self._force_command_mode()
                return

        # ____________________ РЕЖИМ LLM ____________________
        elif self.state == AgentState.FREE:
            logger.info(f"🤔 Думаю над фразой: {text}")
            self.state = AgentState.SPEAKING
            self.context.add_message("user", text)

            try:
                messages_for_llm = self.context.get_messages_for_llm()
                speech = await self._dialog_turn(messages_for_llm)

                if speech and speech.strip():
                    logger.info(f"💬 ДЖАРВИС ГОВОРИТ: {speech}")
                    self.context.add_message("assistant", speech)
                    await self._speak_and_wait(speech)
                else:
                    logger.warning("LLM вернула пустой ответ")
                    await self._speak_and_wait("Я не расслышал, сэр. Повторите, пожалуйста.")
            except Exception as e:
                logger.error(f"LLM/TTS pipeline failed: {e}", exc_info=True)
                await self._speak_and_wait("Произошла ошибка, сэр. Повторите команду.")
            finally:
                # Гарантированный возврат в командный режим после диалога
                await self._force_command_mode()

    async def _switch_to_dialog_mode(self):
        """Безопасное переключение в режим диалога (Whisper)."""
        self.state = AgentState.FREE
        self.current_stt = self.stt_dialog
        # Обновляем сервис для плагинов, чтобы они брали правильный STT
        self.services.register("stt", self.current_stt, override=True)
        
        self.stt_command.clear_grammar() # Выключаем грамматику Vosk
        logger.info("🔓 Режим диалога активирован (Whisper)")
        await asyncio.to_thread(self.audio_out.play, "data/jarvis_wav/yes_sir.wav")

    async def _force_command_mode(self):
        """Жёсткий сброс в командный режим (Vosk)."""
        self.state = AgentState.COMMAND
        self.current_stt = self.stt_command
        self.services.register("stt", self.current_stt, override=True)
        
        self.current_stt.set_grammar()
        logger.info("🔒 Режим команд активирован (Vosk)")

    async def _dialog_turn(self, messages_for_llm: list) -> str:
        """
        Ограниченный цикл Tool Calling с защитой от сбоев.
        
        Features:
        - Таймауты для предотвращения зависаний
        - Обработка ошибок LLM
        - Логирование производительности
        """
        messages = list(messages_for_llm)
        tools_schema = self.reg.get_tools_schema() if self.reg else []
        
        start_time = time.time()
        total_rounds = 0
        
        for round_index in range(MAX_TOOL_ROUNDS):
            total_rounds += 1
            round_start = time.time()
            
            try:
                # Таймаут для защиты от зависаний LLM
                async with asyncio.timeout(LLM_TIMEOUT_SECONDS):
                    response = await self.llm.async_generate_with_tools(messages, tools_schema)
                
                round_time = (time.time() - round_start) * 1000
                logger.debug(f"⏱️ Round {round_index + 1} completed in {round_time:.0f}ms")
                
            except asyncio.TimeoutError:
                logger.error(f"⏱️ LLM timeout после {LLM_TIMEOUT_SECONDS}с в раунде {round_index + 1}")
                return "Прошу прощения, сэр, я задумался. Повторите, пожалуйста."
            
            except Exception as e:
                logger.error(f"❌ Ошибка LLM в раунде {round_index + 1}: {e}", exc_info=True)
                return "Произошла ошибка, сэр. Попробуйте ещё раз."
            
            # --- обычный текстовый ответ: завершаем ---
            if not response.wants_tool:
                thought, speech = self._parse_llm_text(response.text)
                if thought:
                    logger.info(f"🧠 МЫСЛИ ДЖАРВИСА: {thought}")
                
                total_time = (time.time() - start_time) * 1000
                logger.info(f"✅ Диалог завершён за {total_time:.0f}ms, {total_rounds} раундов")
                return speech
            
            # --- модель запросила инструменты ---
            messages.append(response.as_assistant_message())
            
            tool_round_start = time.time()
            tools_executed = 0
            
            for call in response.tool_calls[:MAX_TOOLS_PER_ROUND]:
                logger.info(f"🛠️ LLM вызывает: {call.name} args={call.arguments}")
                
                try:
                    result = await self.reg.execute_tool(call.name, call.arguments)
                    tools_executed += 1
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(result, ensure_ascii=False, default=str)[:4000],
                    })
                    
                    # Кэшируем результат инструмента
                    try:
                        self.context.add_tool_result(
                            call.name,
                            json.dumps(call.arguments, ensure_ascii=False, default=str),
                            json.dumps(result, ensure_ascii=False, default=str),
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Не удалось закэшировать результат инструмента: {e}")
                
                except Exception as e:
                    logger.error(f"❌ Ошибка выполнения инструмента {call.name}: {e}", exc_info=True)
                    
                    # Передаём ошибку обратно в LLM как результат инструмента
                    error_result = {
                        "error": str(e),
                        "tool_name": call.name
                    }
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(error_result, ensure_ascii=False, default=str),
                    })
            
            tool_round_time = (time.time() - tool_round_start) * 1000
            logger.debug(f"🔧 Executed {tools_executed} tools in {tool_round_time:.0f}ms")
        
        # Если лимит исчерпан, просим обычный текст
        logger.warning(f"⚠️ Достигнут лимит раундов ({MAX_TOOL_ROUNDS}), запрашиваю финальный ответ")
        
        try:
            async with asyncio.timeout(LLM_TIMEOUT_SECONDS):
                final_text = await self.llm.async_generate(messages)
            
            thought, speech = self._parse_llm_text(final_text)
            if thought:
                logger.info(f"🧠 МЫСЛИ ДЖАРВИСА: {thought}")
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Диалог завершён (fallback) за {total_time:.0f}ms, {total_rounds} раундов")
            return speech or "Мне не удалось завершить запрос, сэр."
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ LLM timeout при финальном ответе")
            return "Я слишком долго думаю, сэр. Попробуйте упростить запрос."
        
        except Exception as e:
            logger.error(f"❌ Ошибка при финальном ответе: {e}", exc_info=True)
            return "Произошла ошибка, сэр. Не удалось завершить запрос."

    @staticmethod
    def _parse_llm_text(raw_response: str) -> tuple:
        """Разделяет <thought> и <response>. Защита от утечки тегов в TTS."""
        raw = raw_response or ""
        thought = ""
        speech = ""

        if "<thought>" in raw and "</thought>" in raw:
            thought = raw.split("<thought>")[1].split("</thought>")[0].strip()

        if "<response>" in raw and "</response>" in raw:
            speech = raw.split("<response>")[1].split("</response>")[0].strip()
        else:
            body = raw
            if "</thought>" in body:
                body = body.split("</thought>", 1)[1]
            speech = body.strip()

        return thought, speech

    async def _speak_and_wait(self, text: str):
        """Асинхронно ждет завершения синтеза и воспроизведения."""
        self.state = AgentState.SPEAKING
        self._tts_done_event.clear()
        try:
            self.tts_manager.queue.put_nowait(text)
            await asyncio.to_thread(self.tts_manager.queue.join)
        except asyncio.QueueFull:
            logger.error("TTS queue full. Dropping speech.")
        except Exception as e:
            logger.error(f"Speech pipeline failed: {e}")
        finally:
            self._tts_done_event.set()

    async def _cleanup(self):
        """Гарантированное освобождение ресурсов."""
        logger.info("🛑 Остановка конвейера...")
        self._stop_event.set()
        
        self.tts_manager.stop()
        self.executor.shutdown(wait=True)
        
        if self.audio:
            self.audio.close()
        
        # ИСПРАВЛЕНО: закрываем оба STT провайдера, а не несуществующий self.vosk
        self.stt_command.close()
        self.stt_dialog.close()
            
        logger.info("✅ Jarvis корректно остановлен.")
