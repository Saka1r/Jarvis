<p align="center">
   <img src="https://img.shields.io/badge/build-XD-brightgreen?style=flat&logo=logo&logoColor=%237516a1&label=J.A.R.V.I.S&labelColor=%23c20232&color=%234202c2" alt="Jarvis">
</p>

<p align="center">
   <a href="#-конфигурация">🇷🇺 Русский</a> | <a href="#-configuration">🇬🇧 English</a>
</p>

---

# 🇷🇺 Конфигурация

Модуль `config.py` отвечает за инициализацию и проверку конфигурационных файлов ассистента. При первом запуске автоматически создаёт недостающие файлы со значениями по умолчанию.

## 🧬 Класс `Config`

### Методы

```python
start()                    # главная точка входа — запускает check_status()
check_status()             # проверяет наличие конфигов, создаёт недостающие
generate_system_config()   # создаёт config/system.json
generate_setting_config()  # создаёт data/setting.json
generate_plugins_config()  # создаёт data/plugins.json
```

## 📂 Генерируемые файлы

### `config/system.json`
Системные параметры (зарезервировано под будущие настройки хоста, GPIO, умного дома).

```json
{}
```

### `data/setting.json`
Общие настройки ассистента.

```json
{
    "engine": "vosk",
    "language": "ru"
}
```

| Поле | Описание |
|------|----------|
| `engine` | Движок STT (сейчас поддерживается только `vosk`) |
| `language` | Язык распознавания и синтеза |

### `data/plugins.json`
Манифест активных плагинов.

```json
{
    "voice": [
        {"name": "jarvis", "version": "1.0", "enabled": true}
    ],
    "utility": []
}
```

| Поле | Описание |
|------|----------|
| `voice` | Список голосовых плагинов (реагируют на триггеры) |
| `utility` | Список утилитных плагинов (фоновые задачи, интеграции) |

## 🔄 Жизненный цикл

```
main.py
   │
   ▼
Config().start()
   │
   ├─▶ существует ли config/system.json?  ──нет──▶ создать
   ├─▶ существует ли data/setting.json?   ──нет──▶ создать
   └─▶ существует ли data/plugins.json?   ──нет──▶ создать
   │
   ▼
Jarvis.start()  ← использует уже готовые конфиги
```

---

# 🇬🇧 Configuration

The `config.py` module handles initialization and validation of the assistant's configuration files. On first launch, it automatically creates missing files with default values.

## 🧬 `Config` class

Methods: `start()`, `check_status()`, `generate_system_config()`, `generate_setting_config()`, `generate_plugins_config()`.

## 📂 Generated files

- **`config/system.json`** — system-level parameters (reserved for host/GPIO/smart-home settings)
- **`data/setting.json`** — general assistant settings (`engine`, `language`)
- **`data/plugins.json`** — active plugin manifest (`voice` and `utility` lists)

See the Russian section above for file schemas.