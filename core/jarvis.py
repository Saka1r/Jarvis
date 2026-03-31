#core/jarvis

import asyncio

from concurrent.futures import ProcessPoolExecutor

from subsystems import audio_in

from subsystems.vosk_stt import Vosk_STT
from subsystems.coqui_tts import TTS_Manager

from core.registry import Registry


class Jarvis:
    def __init__(self):
        self.executor = None
        self.vosk = None
        self.audio = None
        self.reg = None
        self.mode = "command"

        self.tts_manager = TTS_Manager()

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
        print("Jarvis is listening...")
        
        await self.listen_loop()

    async def speak(self, text):
        """Просто добавляем в очередь, не ждем завершения"""
        self.tts_manager.add_to_queue(text)

    async def listen_loop(self):
        """Главный цикл слушания"""
        while True:
            try:
                data = await asyncio.to_thread(self.audio.read) 
                if not data:
                    continue

                text = await asyncio.to_thread(self.vosk.process, data)
                if text:
                    print(f"Услышал: {text}")
                    await self.handle_input(text)

            except KeyboardInterrupt:
                print("\nОстановка...")
                break
            except Exception as e:
                print(f"Ошибка: {e}")
                await asyncio.sleep(1) # Пауза, чтобы не спамить ошибками

    async def handle_input(self, text):
        """Обработка распознанного текста"""
        if self.mode == "command":
            if self.is_wake_word(text):
                self.mode = "free"
                print(">>> Режим диалога")
            if self.reg.is_command(text): 
                print(f"Выполняю команду: {text}")
                await asyncio.to_thread(self.reg.voice_plug_start, text)
            else:
                print("Команда не распознана") 
        
        elif self.mode == "free":
            print(f"Думаю над фразой: {text}")
            self.mode = "command"

    def is_wake_word(self, text):
        if text == "джарвис":
            return True
