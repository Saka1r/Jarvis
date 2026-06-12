<p align="center">
      <img src="https://i.ibb.co/27gG72vV/kandinsky-download-1742490236209.png" width="726">
</p>
  
<p align="center">
   <img src="https://img.shields.io/badge/build-XD-brightgreen?style=flat&logo=logo&logoColor=%237516a1&label=J.A.R.V.I.S&labelColor=%23c20232&color=%234202c2" alt="Jarvis">
</p>

<p align="center">
   <a href="#-о-проекте">🇷🇺 Русский</a> | <a href="#-about">🇬🇧 English</a>
</p>

---

# 🇷🇺 О проекте

**J.A.R.V.I.S.** (*Just A Rather Very Intelligent System*) — моя интерпретация голосового ассистента Тони Старка. Локальный, приватный, офлайн-ориентированный помощник, работающий на открытом стеке: **Vosk** (STT), **Coqui XTTS v2** (TTS), **llama.cpp** (LLM) и системе плагинов.

Никаких облаков. Никаких API-ключей. Только твой GPU и твой голос.

## ✨ Возможности

- 🎤 **Голосовое управление** через Vosk с поддержкой грамматики (командный режим) и свободного распознавания (диалоговый режим)
- 🗣️ **Синтез речи** на базе XTTS v2 с клонированием голоса по референс-аудио
- 🧠 **Локальная LLM** (Meta-Llama-3.1-8B-Instruct-Q6_K) для диалогов
- 🔌 **Система плагинов** — команды загружаются из `plugins/*/commands.json`, установка из `.zip`
- ⚡ **Асинхронное ядро** на `asyncio` с `ThreadPoolExecutor` для блокирующих операций
- 🎛️ **Конечный автомат состояний**: `COMMAND` → `FREE` → `SPEAKING` → `WAIT`
- 🛡️ **Эхо-подавление**: микрофон игнорируется, пока Джарвис говорит

## 🏗️ Архитектура

```
main.py
  ├── config.py          — инициализация конфигов
  └── core/jarvis.py     — ядро (конечный автомат)
        ├── core/registry.py       — менеджер плагинов
        ├── subsystems/audio_in    — PyAudio (микрофон)
        ├── subsystems/audio_out   — sounddevice (вывод)
        ├── subsystems/vosk_stt    — распознавание речи
        ├── subsystems/coqui_tts   — синтез речи
        └── subsystems/llama_llm   — генерация ответов
```

                        ┌─────────────────────────────────────┐
                        │          A G E N T   F S M          │
                        └─────────────────────────────────────┘

                                  ┌──────────────┐
                       ┌─────────▶│   COMMAND    │◀────────────┐
                       │          │  (grammar)   │             │
                       │          └──────┬───────┘             │
                       │                 │                     │
         "джарвис" /                     │ "режим диалога"     │ "режим диалога"
    "отключить режим ожидания"           │                     │ завершён
                       │                 ▼                     │
                       │          ┌──────────────┐             │
                       │          │     FREE     │             │
                       │          │  (LLM chat)  │             │
                       │          └──────┬───────┘             │
                       │                 │                     │
                       │                 │ user spoke          │
                       │                 ▼                     │
                       │          ┌──────────────┐             │
                       │          │   SPEAKING   │             │
                       │          │ (TTS + echo  │─────────────┘
                       │          │  suppression)│
                       │          └──────────────┘
                       │
                       │  "режим ожидания"
                       │
                       ▼
                ┌──────────────┐
                │     WAIT     │
                │  (standby)   │
                └──────────────┘

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/sakair/jarvis.git
cd jarvis

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Положить модели в data/models/
#    - vosk/              (модель Vosk)
#    - Meta-Llama-3.1-8B-Instruct-Q6_K.gguf

# 4. Запустить
python main.py
```

## 📁 Структура проекта

```
jarvis/
├── main.py              # точка входа
├── config.py            # генерация конфигов
├── core/                # ядро ассистента
│   ├── jarvis.py        # главный класс
│   ├── registry.py      # менеджер плагинов
│   └── context.py       # контекст диалога (WIP)
├── subsystems/          # подсистемы ввода/вывода/ML
├── plugins/             # пользовательские плагины
├── config/              # system.json
├── data/                # модели, аудио, плагины.json, setting.json
└── plan.txt             # дорожная карта
```

📖 **Подробная документация по модулям:**
- [`core/README.md`](core/README.md) — ядро (Jarvis, Registry)
- [`config/README.md`](config/README.md) — конфигурация
- [`subsystems/README.md`](subsystems/README.md) — подсистемы

## ⚙️ Требования

- Python 3.10+
- CUDA (опционально, для ускорения TTS/LLM)
- Микрофон и аудиовыход
- ~8 ГБ VRAM для Llama-3.1-8B-Q6_K (или CPU — будет медленнее)

## 📜 Лицензия

MIT © sakair / Svyatoslav

---

# 🇬🇧 About

**J.A.R.V.I.S.** (*Just A Rather Very Intelligent System*) — my interpretation of Tony Stark's voice assistant. A local, private, offline-first assistant built on an open stack: **Vosk** (STT), **Coqui XTTS v2** (TTS), **llama.cpp** (LLM), and a plugin system.

No clouds. No API keys. Just your GPU and your voice.

## ✨ Features

- 🎤 **Voice control** via Vosk with grammar mode (commands) and free recognition (dialog)
- 🗣️ **Speech synthesis** using XTTS v2 with voice cloning from reference audio
- 🧠 **Local LLM** (Meta-Llama-3.1-8B-Instruct-Q6_K) for conversations
- 🔌 **Plugin system** — commands loaded from `plugins/*/commands.json`, installable from `.zip`
- ⚡ **Async core** on `asyncio` with `ThreadPoolExecutor` for blocking ops
- 🎛️ **Finite state machine**: `COMMAND` → `FREE` → `SPEAKING` → `WAIT`
- 🛡️ **Echo suppression**: microphone ignored while Jarvis is speaking

## 🚀 Quick start

```bash
git clone https://github.com/sakair/jarvis.git
cd jarvis
pip install -r requirements.txt
# Place models into data/models/
python main.py
```

## 🏗️ Architecture
```
main.py
  ├── config.py          — config initialization
  └── core/jarvis.py     — core (state machine)
        ├── core/registry.py       — plugin manager
        ├── subsystems/audio_in    — PyAudio (microphone)
        ├── subsystems/audio_out   — sounddevice (output)
        ├── subsystems/vosk_stt    — speech recognition
        ├── subsystems/coqui_tts   — speech synthesis
        └── subsystems/llama_llm   — response generation
```

                        ┌─────────────────────────────────────┐
                        │          A G E N T   F S M          │
                        └─────────────────────────────────────┘

                                  ┌──────────────┐
                       ┌─────────▶│   COMMAND    │◀────────────┐
                       │          │  (grammar)   │             │
                       │          └──────┬───────┘             │
                       │                 │                     │
         "джарвис" /                     │ "режим диалога"     │ "режим диалога"
    "отключить режим ожидания"           │                     │ завершён
                       │                 ▼                     │
                       │          ┌──────────────┐             │
                       │          │     FREE     │             │
                       │          │  (LLM chat)  │             │
                       │          └──────┬───────┘             │
                       │                 │                     │
                       │                 │ user spoke          │
                       │                 ▼                     │
                       │          ┌──────────────┐             │
                       │          │   SPEAKING   │             │
                       │          │ (TTS + echo  │─────────────┘
                       │          │  suppression)│
                       │          └──────────────┘
                       │
                       │  "режим ожидания"
                       │
                       ▼
                ┌──────────────┐
                │     WAIT     │
                │  (standby)   │
                └──────────────┘

📁 Project structure
```
jarvis/
├── main.py              # entry point
├── config.py            # config generation
├── core/                # assistant core
│   ├── jarvis.py        # main class
│   ├── registry.py      # plugin manager
│   └── context.py       # dialogue context (WIP)
├── subsystems/          # I/O and ML subsystems
├── plugins/             # user plugins
├── config/              # system.json
├── data/                # models, audio, plugins.json, setting.json
└── plan.txt             # roadmap
```


📖 **Module docs:**
- [`core/README.md`](core/README.md) — core (Jarvis, Registry)
- [`config/README.md`](config/README.md) — configuration
- [`subsystems/README.md`](subsystems/README.md) — subsystems


## ⚙️ Requirements
Python 3.10+
CUDA (optional, for accelerating TTS/LLM)
Microphone and audio output
~8 GB VRAM for Llama-3.1-8B-Q6_K (or CPU — slower)

## 📜 License
MIT © sakair / Svyatoslav*