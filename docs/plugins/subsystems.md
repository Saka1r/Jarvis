# Использование подсистем Джарвиса

## Что такое подсистемы?

Подсистемы — это независимые модули, которые выполняют конкретную задачу: захватывают аудио, распознают речь, синтезируют голос, генерируют ответы LLM. Ядро (`Jarvis`) создаёт их при старте и передаёт в `Registry`, а тот — в каждый плагин.

Такая архитектура позволяет плагинам использовать любые возможности Джарвиса, не зная деталей реализации.

## Как подсистемы попадают в плагины?

### Шаг 1. Jarvis создаёт подсистемы и передаёт их в Registry

```python
# core/jarvis.py

self.reg = Registry(systems={
    "audio_out": self.audio_out,
    "llm": self.llm,
    "tts": self.tts_manager,
    "vosk": self.vosk,
    "audio_in": self.audio
})
```

### Шаг 2. Registry передаёт их в каждый плагин
```python
# core/registry.py

plugin_class = getattr(plugin_module, file_plug["entry"])
instance = plugin_class(self.systems)  # ← словарь подсистем
```
### Шаг 3. BasePlugin выносит подсистемы в атрибуты
```python
# core/base_plugin.py

class BasePlugin:
    """
    Базовый класс для всех плагинов.
    
    Принимает словарь подсистем и выносит их в атрибуты для удобства:
    - self.audio_out  → воспроизведение звука
    - self.audio_in   → захват аудио
    - self.llm        → локальная языковая модель
    - self.tts        → синтез речи
    - self.vosk       → распознавание речи
    """
    
    def __init__(self, systems=None):
        self.systems = systems or {}
        
        # Выносим подсистемы в атрибуты для удобства
        self.audio_out = self.systems.get("audio_out")
        self.audio_in = self.systems.get("audio_in")
        self.llm = self.systems.get("llm")
        self.tts = self.systems.get("tts")
        self.vosk = self.systems.get("vosk")
```
Благодаря BasePlugin в плагинах можно писать self.audio_out.play(...) вместо self.systems["audio_out"].play(...).

## Справочник подсистем
### audio_out — воспроизведение звука

|Метод|Описание|
|-----|--------|
|play(file_path: str)|воспроизведение WAV-файла|
|stop()|Экстренная остановка воспроизведения|


Пример:
```python
def greet(self):
    self.audio_out.play("data/jarvis_wav/yes_sir.wav")
```
### audio_in — захват аудио
|Метод|Описание|
|-----|--------|
|open() -> bool|Открыть аудиопоток с микрофона|
|read(num_frames=None) -> bytes|Прочитать chunk аудио|
|close()|Закрыть поток|


Пример:
```python
def record_sample(self) -> bytes:
    """Записать короткий сэмпл с микрофона."""
    return self.audio_in.read(8000)
```

### vosk — распознавание речи

Класс: Vosk_STT (subsystems/vosk_stt.py)

|Метод|Описание|
|------|-------|
|open()|Загрузить модель Vosk|
|close()|Выгрузить модель|
|accept_audio(audio_bytes)|Передать аудио в recognizer|
|get_result() -> str|Получить накопленный текст|
|process(audio_bytes) -> str|accept_audio + get_result|
|set_grammar()|Включить режим команд (грамматика)|
|clear_grammar()|Включить режим свободного распознавания|

Пример:
```python
def custom_listen(self) -> str:
    """Временно переключить в свободный режим и послушать."""
    self.vosk.clear_grammar()
    # ... слушаем ...
    self.vosk.set_grammar()
```

### tts - синтез речи

Класс: TTS_Manager (subsystems/coqui_tts.py)

|Метод/Атрибут|Описание|
|------|-------|
|queue: Queue|Очередь текстов для озвучки|
|start()|Запуск worker-потока|
|stop()|Остановка worker-потока|

Пример:

```python
def notify(self, text: str):
    """Отправить текст в TTS-очередь."""
    self.tts.queue.put_nowait(text)
```
### llm — локальная языковая модель

Класс: LlamaLLM (subsystems/llama_llm.py)

|Метод|Описание|
|------|-------|
|generate(user_input: str, context=None) -> str|Синхронная генерация ответа|
|async_generate(user_input: str, context=None) -> str|Асинхронная генерация|
|load() -> bool|Загрузка модели в память|
|unload()|Выгрузка модели|

Пример:

```python
def ask_llm(self, question: str) -> str:
    """Спросить LLM и вернуть ответ."""
    return self.llm.generate(question)
```
### Пример плагина

```python
# plugins/smart_assistant/main.py

from core.base_plugin import BasePlugin


class SmartAssistantPlugin(BasePlugin):
    
    def analyze_and_report(self) -> str:
        """Комплексный пример: использует сразу несколько подсистем."""
        
        # 1. Воспроизводим звук приветствия
        self.audio_out.play("data/jarvis_wav/yes_sir.wav")
        
        # 2. Спрашиваем LLM
        answer = self.llm.generate("Что такое Москва?")
        
        # 3. Возвращаем ответ
        self.tts.queue.put_nowait(answer)
        #or self.systems["tts"].queue.put_nowait(
    
    def play_notification(self) -> None:
        """Просто играет звук, без озвучки текста."""
        self.audio_out.play("data/jarvis_wav/notification.wav")
        
```
## Лучшие практики

### Делай

-    Наследуй от BasePlugin — это даёт доступ к self.audio_out, self.llm и т.д.
-    Используй self.audio_out.play() только для коротких WAV-файлов (приветствия, звуки).

### Не делай

-    Не создавай свои инстансы подсистем — они уже созданы в Jarvis.
-    Не вызывай llm.load() повторно — модель уже в памяти.
-    Не блокируй asyncio-цикл — используй asyncio.to_thread() для долгих операций.

## Как добавить свою подсистему

Если тебе нужна новая подсистема (например, camera для работы с веб-камерой)

### 1. Создай файл подсистемы
```python
# subsystems/camera.py

class Camera:
    def capture(self) -> bytes:
        """Сделать снимок."""
        # ... реализация ...
        pass
```
### 2. Добавь её в Jarvis
```python
# core/jarvis.py

from subsystems.camera import Camera

class Jarvis:
    async def start(cls):
        self = cls()
        self.camera = Camera()  # ← создаём подсистему
        
        self.reg = Registry(systems={
            "audio_out": self.audio_out,
            "llm": self.llm,
            "tts": self.tts_manager,
            "vosk": self.vosk,
            "audio_in": self.audio,
            "camera": self.camera  # ← добавляем в словарь
        })
```

### 3. Добавь ее в BasePlugin

# core/base_plugin.py

```python
class BasePlugin:
    def __init__(self, systems=None):
        self.systems = systems or {}
        self.audio_out = self.systems.get("audio_out")
        self.audio_in = self.systems.get("audio_in")
        self.llm = self.systems.get("llm")
        self.tts = self.systems.get("tts")
        self.vosk = self.systems.get("vosk")
        self.camera = self.systems.get("camera")  # ← добавляем атрибут
```

### 4. Используй в плагинах

```python
class PhotoPlugin(BasePlugin):
    def take_photo(self) -> str:
        self.camera.capture()
        self.tts.queue.put_nowait("Фото сделано, сэр.")
```