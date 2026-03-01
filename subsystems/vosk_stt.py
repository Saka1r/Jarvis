import json
import os

from vosk import Model, KaldiRecognizer
from subsystems.stt import STT

class Vosk_STT(STT):
    def __init__(self, model_path: str = "data/models/vosk", sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None

        self.accumulated_text = None

        self.commands = self.load_commands()

    def load_commands(self):
        commands = []
        
        plugins_dir = "plugins"
        
        # Проходимся по всем плагинам
        for plugin_name in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            
            if os.path.isdir(plugin_path):
                commands_file_path = os.path.join(plugin_path, "commands.json")
                
                # Если файл commands.json существует, загружаем его
                if os.path.isfile(commands_file_path):
                    with open(commands_file_path, "r", encoding='utf-8') as f:
                        plugin_commands = json.load(f)
                        # Собираем команды в общий список
                        for command in plugin_commands.get("commands", []):
                            commands.extend(command['triggers'])

        # Удаляем дубликаты, если нужно, преобразуя в множество
        commands = list(set(commands))
        
        return json.dumps(commands, ensure_ascii=False)


    def open(self) -> bool:
        try:
            self.model = Model(self.model_path)
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

if __name__ == '__main__':
    vosk_ = Vosk_STT()
    print(vosk_.load_commands())
