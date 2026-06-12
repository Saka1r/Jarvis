<p align="center">
   <img src="https://img.shields.io/badge/build-XD-brightgreen?style=flat&logo=logo&logoColor=%237516a1&label=J.A.R.V.I.S&labelColor=%23c20232&color=%234202c2" alt="Jarvis">
</p>

<p align="center">
   <a href="#-подсистемы">🇷🇺 Русский</a> | <a href="#-subsystems">🇬🇧 English</a>
</p>

---

# 🇷🇺 Подсистемы

Каталог `subsystems/` содержит модули ввода-вывода и ML-движки. Все подсистемы следуют принципу единого интерфейса: абстрактные базовые классы `STT` и `TTS` определяют контракт, конкретные реализации (`Vosk_STT`, `Coqui_TTS`) его реализуют.

## 🧩 Список подсистем

| Файл | Класс | Назначение |
|------|-------|-----------|
| `audio_in.py` | `AudioOpen` | Захват аудио с микрофона (PyAudio) |
| `audio_out.py` | `AudioOut` | Воспроизведение WAV (sounddevice) |
| `stt.py` | `STT` | Абстрактный базовый класс для распознавания речи |
| `vosk_stt.py` | `Vosk_STT` | Реализация STT на базе Vosk/Kaldi |
| `tts.py` | `TTS` | Абстрактный базовый класс для синтеза речи |
| `coqui_tts.py` | `TTS_Manager`, `Coqui_TTS` | Менеджер очереди + реализация TTS на XTTS v2 |
| `llama_llm.py` | `LlamaLLM` | Локальная LLM через llama.cpp |

---

## 🎤 `audio_in.py` — `AudioOpen`

Захват сырого PCM-потока с микрофона.

```python
audio = AudioOpen(rate=16000, channels=1, frames_per_buffer=8000)
audio.open()                     # открыть поток
data = audio.read()              # прочитать chunk байт
audio.close()                    # закрыть поток
```

| Метод | Описание |
|-------|----------|
| `open()` → `bool` | Инициализирует PyAudio-стрим |
| `read(num_frames=None)` → `bytes` | Читает очередной chunk |
| `close()` | Освобождает устройство |

Потокобезопасность обеспечивается через `threading.Lock`.

---

## 🔊 `audio_out.py` — `AudioOut`

Воспроизведение WAV-файлов.

```python
out = AudioOut()
out.play("data/jarvis_wav/yes_sir.wav")   # блокирующее воспроизведение
out.stop()                                 # экстренная остановка
```

Под капотом: `torchaudio.load()` → конвертация в mono float32 → `sounddevice.play()` + `sd.wait()`.

---

## 📝 `stt.py` — абстрактный `STT`

Базовый контракт для всех STT-реализаций:

```python
class STT(ABC):
    def open(self) -> bool: ...
    def close(self) -> None: ...
    def accept_audio(self, audio_bytes: bytes) -> None: ...
    def get_result(self) -> str: ...
```

---

## 👂 `vosk_stt.py` — `Vosk_STT`

Реализация STT на Vosk с поддержкой **грамматики** (список разрешённых фраз) и **свободного распознавания**.

```python
stt = Vosk_STT(model_path="data/models/vosk")
stt.open()
stt.set_grammar()              # включить режим команд (быстро, точно)
stt.clear_grammar()            # включить режим диалога (свободно)
text = stt.process(audio_chunk)
```

| Метод | Описание |
|-------|----------|
| `open()` | Загружает модель Vosk, инициализирует `KaldiRecognizer` |
| `close()` | Выгружает модель |
| `accept_audio(bytes)` | Скармливает chunk в recognizer |
| `get_result()` | Возвращает накопленный текст и сбрасывает буфер |
| `process(bytes)` | `accept_audio` + `get_result` в одном вызове |
| `set_grammar()` | Активирует грамматику (триггеры плагинов + системные) |
| `clear_grammar()` | Снимает ограничения → свободный словарь |

**Системные триггеры** (всегда активны в режиме `COMMAND`):
```python
["джарвис", "режим ожидания", "режим диалога", "отключить режим ожидания"]
```

---

## 🗣️ `coqui_tts.py` — `TTS_Manager` + `Coqui_TTS`

Двухуровневая архитектура:

- **`Coqui_TTS`** — обёртка над XTTS v2. Методы: `open()`, `generate(text) → path`, `cleanup(path)`.
- **`TTS_Manager`** — фоновый поток с очередью. Принимает текст, синтезирует, воспроизводит, удаляет временный WAV.

```python
manager = TTS_Manager()
manager.start()                             # запустить worker-поток
manager.queue.put_nowait("Привет, сэр.")    # неблокирующая постановка
await asyncio.to_thread(manager.queue.join) # ждать завершения
manager.stop()
```

### Параметры синтеза (XTTS v2)

| Параметр | Значение |
|----------|----------|
| Модель | `tts_models/multilingual/multi-dataset/xtts_v2` |
| Язык | `ru` |
| `temperature` | 0.8 |
| `repetition_penalty` | 1.15 |
| `top_k` / `top_p` | 50 / 0.9 |
| `speed` | 1.08 |
| Референс голоса | `data/new_reference_jar_micro_22050.wav` |

`cleanup()` корректно обрабатывает `WinError 32` (файл занят) на Windows с retry-логикой.

---

## 🧠 `llama_llm.py` — `LlamaLLM`

Локальная LLM через `llama-cpp-python`.

```python
llm = LlamaLLM(model_path="data/models/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf")
llm.load()
answer = llm.generate("Как дела?")
# или асинхронно:
answer = await llm.async_generate("Как дела?")
```

| Параметр | Значение |
|----------|----------|
| `n_ctx` | 4096 |
| `n_gpu_layers` | -1 (все на GPU) |
| `n_threads` | 8 |
| `max_tokens` | 300 |
| `temperature` | 0.2 |
| `top_p` / `top_k` | 0.9 / 40 |
| `repeat_penalty` | 1.1 |

**System prompt** жёстко зашит: Джарвис отвечает только по-русски, кратко (1–3 предложения), без списков.

---

## 🔗 Взаимодействие подсистем

Все подсистемы передаются в `Registry` через словарь `systems` при инициализации `Jarvis`:

```python
self.reg = Registry(systems={
    "audio_out": self.audio_out,
    "llm": self.llm,
    "tts": self.tts_manager,
    "vosk": self.vosk,
    "audio_in": self.audio
})
```

Плагины получают этот словарь в конструктор и могут использовать любую подсистему (например, `systems["audio_out"].play(...)` для воспроизведения своих звуков).

---

# 🇬🇧 Subsystems

The `subsystems/` directory contains I/O modules and ML engines. All subsystems follow a single-interface principle: abstract base classes `STT` and `TTS` define the contract, concrete implementations (`Vosk_STT`, `Coqui_TTS`) implement it.

## 🧩 Subsystem list

| File | Class | Purpose |
|------|-------|---------|
| `audio_in.py` | `AudioOpen` | Microphone capture (PyAudio) |
| `audio_out.py` | `AudioOut` | WAV playback (sounddevice) |
| `stt.py` | `STT` | Abstract base class for speech recognition |
| `vosk_stt.py` | `Vosk_STT` | Vosk/Kaldi-based STT implementation |
| `tts.py` | `TTS` | Abstract base class for speech synthesis |
| `coqui_tts.py` | `TTS_Manager`, `Coqui_TTS` | Queue manager + XTTS v2 TTS implementation |
| `llama_llm.py` | `LlamaLLM` | Local LLM via llama.cpp |

## 🎤 `audio_in.py` — `AudioOpen`
Captures raw PCM stream from microphone. Methods: `open()`, `read()`, `close()`. Thread-safe via `threading.Lock`.

## 🔊 `audio_out.py` — `AudioOut`
Plays WAV files. Methods: `play(path)` (blocking), `stop()` (emergency). Uses `torchaudio.load()` → `sounddevice.play()`.

## 👂 `vosk_stt.py` — `Vosk_STT`
Vosk-based STT with grammar mode (commands) and free recognition (dialog). Key methods: `open()`, `close()`, `accept_audio()`, `get_result()`, `process()`, `set_grammar()`, `clear_grammar()`.

## 🗣️ `coqui_tts.py` — `TTS_Manager` + `Coqui_TTS`
Two-layer architecture: `Coqui_TTS` wraps XTTS v2, `TTS_Manager` runs a background worker thread with a queue. Handles Windows `WinError 32` with retry logic.

## 🧠 `llama_llm.py` — `LlamaLLM`
Local LLM via `llama-cpp-python`. Loads Meta-Llama-3.1-8B-Instruct-Q6_K. Provides sync `generate()` and async `async_generate()`.

## 🔗 Interaction
All subsystems are passed to `Registry` via the `systems` dict during `Jarvis` initialization. Plugins receive this dict in their constructor and can use any subsystem.