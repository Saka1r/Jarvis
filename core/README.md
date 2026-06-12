<p align="center">
   <img src="https://img.shields.io/badge/build-XD-brightgreen?style=flat&logo=logo&logoColor=%237516a1&label=J.A.R.V.I.S&labelColor=%23c20232&color=%234202c2" alt="Jarvis">
</p>

<p align="center">
   <a href="#-ядро">🇷🇺 Русский</a> | <a href="#-core">🇬🇧 English</a>
</p>

---

# 🇷🇺 Ядро

Каталог `core/` содержит центральные компоненты ассистента: конечный автомат, менеджер плагинов и (в перспективе) менеджер контекста диалога.

## 🧩 Модули

| Файл | Назначение |
|------|-----------|
| `jarvis.py` | Главный класс `Jarvis` — оркестратор подсистем и конечный автомат |
| `registry.py` | `Registry` — менеджер плагинов: загрузка, установка, вызов команд |
| `context.py` | `Context` — управление контекстом диалога (WIP) |

---

## 🤖 `jarvis.py` — класс `Jarvis`

Точка входа: `await Jarvis.start()`.

### Состояния (`AgentState`)

| Состояние | Описание |
|-----------|----------|
| `COMMAND` | Ожидание команд. Активна грамматика Vosk. Реагирует на триггеры плагинов и системные команды |
| `FREE` | Режим диалога с LLM. Грамматика отключена, свободное распознавание |
| `SPEAKING` | Воспроизведение ответа. Микрофон игнорируется (эхо-подавление) |
| `WAIT` | Режим ожидания. Джарвис спит, реагирует только на wake-word |

### Системные команды

| Фраза | Переход |
|-------|---------|
| `"режим диалога"` | `COMMAND` → `FREE` |
| `"режим ожидания"` | `COMMAND` → `WAIT` |
| `"джарвис"` / `"отключить режим ожидания"` | `WAIT` → `COMMAND` |

### Основные методы

```python
@classmethod
async def start(cls)            # точка входа, инициализация подсистем
async def _listen_loop()        # producer: аудио → STT → очередь
async def _process_loop()       # consumer: очередь → handle_input
async def handle_input(text)    # маршрутизация по состоянию
async def _speak_and_wait(text) # TTS + ожидание завершения
async def _cleanup()            # освобождение ресурсов
```

### Архитектура цикла

```
┌──────────────┐   audio bytes   ┌────────────┐   text   ┌─────────────────┐
│  AudioOpen   │ ───────────────▶│  Vosk_STT  │ ───────▶ │ commands_queue  │
└──────────────┘                 └────────────┘          └────────┬────────┘
                                                                  │
                                                                  ▼
                                                         ┌─────────────────┐
                                                         │  handle_input   │
                                                         │  (state-based)  │
                                                         └────────┬────────┘
                                                                  │
                                              ┌───────────────────┼───────────────────┐
                                              ▼                   ▼                   ▼
                                        Registry            LlamaLLM           TTS_Manager
                                      (plugins)            (FREE mode)          (SPEAKING)
```

---

## 🔌 `registry.py` — класс `Registry`

Менеджер плагинов. Читает манифесты из `data/plugins.json` и команды из `plugins/<name>/commands.json`.

### Основные методы

```python
load_commands() -> set          # собрать все триггеры из всех плагинов
is_command(text) -> bool        # проверка, является ли текст командой
get_command_priority(text)      # 'background' или 'dialog'
voice_plug_start(voice_text)    # найти плагин по триггеру и вызвать action
plug_install(path_to_zip)       # установить плагин из ZIP-архива
check_plugins()                 # проверить наличие путей плагинов
```

### Формат `commands.json` плагина

```json
{
  "commands": [
    {
      "triggers": ["привет", "здарова"],
      "action": "greet",
      "priority": "dialog"
    }
  ]
}
```

### Формат `plugin.json` плагина

```json
{
  "name": "jarvis",
  "version": "1.0",
  "entry": "JarvisPlugin"
}
```

Поле `entry` — имя класса в `plugins/<name>/main.py`, который будет инстанцирован с передачей `systems` (словарь подсистем).

---

# 🇬🇧 Core

The `core/` directory contains the central components of the assistant: the finite state machine, the plugin manager, and (in the future) the dialog context manager.

## 🧩 Modules

| File | Purpose |
|------|---------|
| `jarvis.py` | Main `Jarvis` class — orchestrator of subsystems and FSM |
| `registry.py` | `Registry` — plugin manager: loading, installation, command dispatch |
| `context.py` | `Context` — dialog context manager (WIP) |

## 🤖 `jarvis.py` — `Jarvis` class

Entry point: `await Jarvis.start()`.

### States (`AgentState`)

| State | Description |
|-------|-------------|
| `COMMAND` | Awaiting commands. Vosk grammar active. Responds to plugin triggers and system commands |
| `FREE` | LLM dialog mode. Grammar disabled, free recognition |
| `SPEAKING` | Playing response. Microphone ignored (echo suppression) |
| `WAIT` | Standby. Jarvis sleeps, reacts only to wake-word |

### System commands

| Phrase | Transition |
|--------|------------|
| `"режим диалога"` | `COMMAND` → `FREE` |
| `"режим ожидания"` | `COMMAND` → `WAIT` |
| `"джарвис"` / `"отключить режим ожидания"` | `WAIT` → `COMMAND` |

## 🔌 `registry.py` — `Registry` class

Plugin manager. Reads manifests from `data/plugins.json` and commands from `plugins/<name>/commands.json`.

Key methods: `load_commands()`, `is_command()`, `voice_plug_start()`, `plug_install()`.

See plugin format in the Russian section above.