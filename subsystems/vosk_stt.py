import json

from vosk import Model, KaldiRecognizer
from subsystems.stt import STT
from core.registry import Registry

class Vosk_STT(STT):
    def __init__(self, model_path: str = "data/models/vosk", sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None
        self.accumulated_text = ""
        #self.commands = Registry().load_commands()

    def open(self) -> bool:
        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate) #,self.commands)
            return True
        except Exception:
            return False

    def close(self) -> None:
        self.recognizer = None
        self.model = None

    def accept_audio(self, audio_bytes: bytes) -> None:
        if self.recognizer is None:
            raise RuntimeError("Error: subsystems/vosk_stt.py [accept_audio] -> Recognizer not opened")

        if self.recognizer.AcceptWaveform(audio_bytes):
            partial_result = json.loads(self.recognizer.Result())
            new_text = partial_result.get("text", "")
            
            # Накапливаем текст с пробелом
            if new_text:
                self.accumulated_text += new_text + " " 
                return self.accumulated_text

    def process(self, audio_bytes: bytes) -> str:
        self.accept_audio(audio_bytes)
        return self.get_result()

    def get_result(self) -> str:
        result = self.accumulated_text.strip() if self.accumulated_text else ""
        self.accumulated_text = ""
        return result

if __name__ == '__main__':
    vosk_ = Vosk_STT()
    pass
