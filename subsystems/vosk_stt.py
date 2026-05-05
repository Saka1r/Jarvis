import json

from vosk import Model, KaldiRecognizer
from subsystems.stt import STT
from core.registry import Registry

# Системные триггеры
SYSTEM_TRIGGERS = [
    "джарвис", 
    "режим ожидания", 
    "режим диалога",
    "отключить режим ожидания",
]


class Vosk_STT(STT):
    def __init__(self, model_path: str = "data/models/vosk", sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None
        self.accumulated_text = ""
        self.commands = Registry().load_commands()

    def open(self) -> bool:
        try:
            self.model = Model(self.model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate) #,self.commands)
            #self.recognizer.SetGrammar()
            return True
        except Exception as e:
            print(f"❌ Vosk init error: {e}")
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

    def set_grammar(self):
        """Объединяет команды плагинов с системными триггерами и включает грамматику"""
        if self.recognizer is None:
            raise RuntimeError("Recognizer not opened")
            
        # Слияние + удаление дубликатов + сохранение порядка
        merged = list(dict.fromkeys(list(self.commands) + SYSTEM_TRIGGERS))
        grammar_json = json.dumps(merged, ensure_ascii=False)

        self.recognizer.SetGrammar(grammar_json)

        print(f"🔧 Grammar ON: {len(merged)} triggers loaded ({len(self.commands)} plugins + {len(SYSTEM_TRIGGERS)} system)")

    def clear_grammar(self):
        """Отключает словарь → полный режим свободного распознавания"""
        if self.recognizer is None:
            raise RuntimeError("Recognizer not opened")
        self.recognizer.SetGrammar("[]")  # Пустой список = снимаем ограничения
        print("🔓 Grammar OFF: free dialog mode")

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
