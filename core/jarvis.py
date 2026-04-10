#core/jarvis

import asyncio

from concurrent.futures import ThreadPoolExecutor

from subsystems import audio_in

from subsystems.vosk_stt import Vosk_STT
from subsystems.coqui_tts import TTS_Manager
from subsystems.llama_llm import LlamaLLM

from core.registry import Registry


class Jarvis:
    def __init__(self):
        self.executor = None
        self.vosk = None
        self.audio = None
        self.reg = None
        self.mode = "command"

        self.tts_manager = TTS_Manager()
        self.llm = LlamaLLM()
        self.llm.load()

        self.commands_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=2)

    @classmethod
    async def start(cls):
        """Точка входа. Запускается из main.py через asyncio.run()"""

        self = cls()

        self.vosk = Vosk_STT()
        self.audio = audio_in.AudioOpen()
        self.reg = Registry()

        self.vosk.open()
        self.audio.open()
       
        self.tts_manager.start()
        
        print("🎤 Jarvis is listening...")
        
        await asyncio.gather(
            self._listen_loop(),
            self._process_loop()
        )

    async def _listen_loop(self):
        """Только слушает и кидает текст в очередь. Никогда не ждет LLM."""
        while True:
            try:
                data = await asyncio.to_thread(self.audio.read)
                if not data: continue
                
                text = await asyncio.to_thread(self.vosk.process, data)
                if text:
                    print(f"👂 Услышал: {text}")
                    await self.commands_queue.put(text)
            except Exception as e:
                print(f"Audio error: {e}")
                await asyncio.sleep(0.5)

    async def _process_loop(self):
        """Берет команды из очереди и обрабатывает. Работает параллельно с listen."""
        while True:
            text = await self.commands_queue.get()
            try:
                # Тяжелые задачи выполняем в executor, но await не блокирует listen_loop
                await self.handle_input(text)
            finally:
                self.commands_queue.task_done()

    async def handle_input(self, text):
        if self.mode == "command":
            if self.is_wake_word(text):
                self.mode = "free"
                await self.speak("Слушаю")
            elif self.reg.is_command(text):
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, self.reg.voice_plug_start, text
                )
            else:
                print("⚠️ Команда не распознана") 
        
        elif self.mode == "free":
            print(f"🤔 Думаю над фразой: {text}")
            
            # to_thread НЕ блокирует event loop. _listen_loop продолжит работу!
            response = await asyncio.to_thread(self.llm.generate, text)
            print(f"💬 Джарвис: {response}")
            await self.speak(response)
            self.mode = "command"

    async def speak(self, text):
        self.tts_manager.add_to_queue(text)

    def is_wake_word(self, text):
        return "джарвис" in text.lower()
