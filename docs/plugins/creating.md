# Создание плагина

## 0. `data/plugins.json`

```json
{
    "voice": [
        {
            "name": "my_plugin",
            "version": "1.0",
            "enabled": true
        }
    ],
    "utility": []
}
```
Добавить свой плагин в data/plugins.json. В данном случаи наш плагин является голосовым (активация с помощью команды), плагин включен (enabled: true).

## 1. `plugin.json`

```json
{
  "name": "my_plugin",
  "version": "1.0.0",
  "entry": "MyPlugin"
}
```
entry - точка входа плагина это имя класса.


## 2. `commands.json`

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

## 3. `main.py`

```python
class MyPlugin:
    def __init__(self, systems: dict):
        self.systems = systems
    
    def greet(self) -> str:
        return "Привет, сэр!"
```

### Готово!
Плагин автоматически подхватится Registry.