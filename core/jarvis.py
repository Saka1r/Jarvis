from subsystems import audio_in
from subsystems import audio_out

from subsystems.audio_in import AudioOpen
from subsystems.vosk_stt import Vosk_STT

from core.registry import Registry

class Jarvis():
    def __init__(self):
        pass 

    @classmethod    
    def start(cls):
        vosk = Vosk_STT()
        audio = AudioOpen()
        reg = Registry()

        reg.plug_start()
        audio_o = audio_out.AudioOut()
        vosk.open()
        audio.open()

        def listen():
            while True:
                data = audio.read()
                vosk.accept_audio(data)
                
                # Получаем текст только если есть значимое содержимое
                answer = vosk.get_result()
                if answer:
                    print(answer)
                    reg.voice_plug_start(answer)
        listen()
