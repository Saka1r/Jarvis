import json

from vosk import Model, KaldiRecognizer
from subsystems.stt import STT

class Vosk_STT(STT):
    def __init__(self, model_path: str = "data/models/vosk", sample_rate: int = 16000):
        with open("data/setting.json", "r", encoding='utf-8') as f:
            commands = json.load(f)

        self.commands = list(commands.keys())
        self.commands = json.dumps(self.commands, ensure_ascii=False)

        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None

        self.accumulated_text = None

    def open(self) -> bool:
        try:
            self.model = Model(self.model_path, lang="ru")
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate, self.commands)
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

    def get_result(self) -> str:
        result = self.accumulated_text.strip() if self.accumulated_text else ""
        self.accumulated_text = ""
        return result
