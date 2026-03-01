from subsystems import audio_in

from subsystems.vosk_stt import Vosk_STT

from core.registry import Registry

class Jarvis():
    def __init__(self):
        pass 

    @classmethod    
    def start(cls):
        vosk = Vosk_STT()
        audio = audio_in.AudioOpen()
        reg = Registry()

        reg.plug_start()
        vosk.open()
        audio.open()

        def listen():
            while True:
                data = audio.read()
                vosk.accept_audio(data)
               
                print(data)

                # Получаем текст только если есть значимое содержимое
                answer = vosk.get_result()
                if answer:
                    print(answer)
                    #reg.voice_plug_start(answer)
                    #answer = vosk.get_result()
            
        listen()
