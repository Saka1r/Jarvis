# tests/test_registry.py
import pytest
import json
from unittest.mock import patch, MagicMock
from core.registry import Registry


class TestRegistry:
    """Тесты для Registry с моками файловой системы."""
    
    @pytest.fixture
    def mock_plugin_structure(self, tmp_path):
        """
        Создаем фейковую структуру плагинов во временной папке.
        Это реалистичная симуляция того, что есть на диске.
        """
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        
        # Плагин "weather"
        weather_dir = plugins_dir / "weather"
        weather_dir.mkdir()
        (weather_dir / "commands.json").write_text(json.dumps({
            "commands": [
                {"triggers": ["погода", "какая погода"], "priority": "dialog"},
                {"triggers": ["обнови погоду"], "priority": "background"}
            ]
        }))
        
        # Плагин "timer"
        timer_dir = plugins_dir / "timer"
        timer_dir.mkdir()
        (timer_dir / "commands.json").write_text(json.dumps({
            "commands": [
                {"triggers": ["таймер", "засеки время"], "priority": "dialog"}
            ]
        }))
        
        # data/plugins.json
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "plugins.json").write_text(json.dumps({
            "voice": [{"name": "weather"}, {"name": "timer"}]
        }))
        
        return tmp_path
    
    def test_is_command_exists(self, mock_plugin_structure):
        """Команда из плагина должна распознаваться."""
        # Mock файловой системы
        with patch("os.getcwd", return_value=str(mock_plugin_structure)), \
             patch("os.listdir", return_value=["weather", "timer"]), \
             patch("os.path.exists", return_value=True), \
             patch("os.path.isdir", side_effect=lambda p: "weather" in p or "timer" in p), \
             patch("os.path.isfile", side_effect=lambda p: "commands.json" in p or "plugins.json" in p):
            
            # Mock чтения файлов
            def mock_open(path, *args, **kwargs):
                if "weather/commands.json" in str(path):
                    return open(str(mock_plugin_structure / "plugins" / "weather" / "commands.json"))
                if "timer/commands.json" in str(path):
                    return open(str(mock_plugin_structure / "plugins" / "timer" / "commands.json"))
                if "plugins.json" in str(path):
                    return open(str(mock_plugin_structure / "data" / "plugins.json"))
                raise FileNotFoundError(f"Mock: {path}")
            
            with patch("builtins.open", side_effect=mock_open):
                reg = Registry(systems={})
                reg.load_plugins()
                
                # Тесты
                assert reg.is_command("погода") is True
                assert reg.is_command("ПОГОДА") is True  # case insensitive
                assert reg.is_command("таймер") is True
    
    def test_is_command_not_exists(self, mock_plugin_structure):
        """Неизвестный текст — не команда."""
        # ... (аналогичный mock) ...
        # Упрощенный пример:
        reg = Registry(systems={})
        # Мокаем внутренние методы, чтобы не грузить реальные плагины
        reg._commands = {"погода": {"priority": "dialog"}, "таймер": {"priority": "dialog"}}
        
        assert reg.is_command("привет как дела") is False
        assert reg.is_command("random text") is False
    
    def test_get_command_priority(self, mock_plugin_structure):
        """Проверяем приоритеты команд."""
        reg = Registry(systems={})
        reg._commands = {
            "погода": {"priority": "dialog"},
            "обнови погоду": {"priority": "background"}
        }
        
        assert reg.get_command_priority("погода") == "dialog"
        assert reg.get_command_priority("обнови погоду") == "background"
        assert reg.get_command_priority("неизвестная") == "dialog"  # По умолчанию