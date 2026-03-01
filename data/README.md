## Здесь хранятся файлы нужные файлы для Джарвиса

plugins.json
```json
{
    "voice": [
        {
            "name": "jarvis",
            "version": "1.0",
            "enabled": true
        }
    ],
    "utility": []
}
```
Это минимальный plugins.json. В этом файле хранятся все имена плагинов и их характеристики.

setting.json 
```json
{
    "engine": "vosk",
    "language": "ru"
}
```
В этом файле хранятся пользовательские настройки, например язык и речевой движок

models - это файлы vosk

в jarvis_wav хранятся семплы Джарвиса