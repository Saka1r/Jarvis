from subsystems import audio_in
from subsystems import audio_out
from subsystems.audio_in import AudioOpen
from subsystems.vosk_stt import Vosk_STT

class Jarvis():
    def __init__(self):
        pass 
    @classmethod    
    def start(cls):
        vosk = Vosk_STT()
        audio = AudioOpen()
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
                    audio_o.play(answer) 
        listen()
