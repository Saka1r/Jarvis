# tests/test_context.py
import pytest
import tempfile
from pathlib import Path
from core.context import ContextManager


class TestContextManager:
    """Тесты для ContextManager."""
    
    @pytest.fixture
    def context(self, tmp_path):
        """
        Фикстура — это функция, которая создает объект для тестов.
        tmp_path — встроенная фикстура pytest, дает временную папку.
        Каждый тест получает свою изолированную папку.
        """
        storage = str(tmp_path / "test_context.json")
        return ContextManager(storage_path=storage, max_turns=3)
    
    def test_add_message_user_then_assistant(self, context):
        """Проверяем нормальный диалог: user -> assistant."""
        # Arrange (подготовка)
        # Act (действие)
        context.add_message("user", "Привет")
        context.add_message("assistant", "Здравствуйте")
        
        # Assert (проверка)
        messages = list(context.short_term)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Привет"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Здравствуйте"
    
    def test_add_message_duplicate_ignored(self, context):
        """
        Твоя защита от дубликатов STT: 
        если одно и то же сообщение приходит дважды подряд, второе игнорируется.
        """
        context.add_message("user", "Привет")
        context.add_message("user", "Привет")  # Должно игнорироваться
        
        messages = list(context.short_term)
        assert len(messages) == 1, "Дубликат должен быть проигнорирован"
        assert messages[0]["content"] == "Привет"
    
    def test_add_message_consecutive_same_role_replaces(self, context):
        """
        Твоя защита от двух user подряд: 
        второе сообщение заменяет первое (не добавляется).
        """
        context.add_message("user", "Привет")
        context.add_message("user", "Как дела?")  # Должно ЗАМЕНИТЬ "Привет"
        
        messages = list(context.short_term)
        assert len(messages) == 1, "Второе сообщение должно заменить первое"
        assert messages[0]["content"] == "Как дела?"
    
    def test_add_message_empty_ignored(self, context):
        """Пустые строки и пробелы не добавляются."""
        context.add_message("user", "")
        context.add_message("user", "   ")
        context.add_message("user", "\n\t")
        
        assert len(list(context.short_term)) == 0, "Пустые сообщения не должны добавляться"
    
    def test_max_turns_overflow(self, context):
        """Проверяем, что deque обрезает старые сообщения при переполнении."""
        # Добавляем 10 сообщений (больше чем max_turns * 2 = 6)
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            context.add_message(role, f"Сообщение {i}")
        
        messages = list(context.short_term)
        assert len(messages) == 6, f"Ожидалось 6 сообщений, получено {len(messages)}"
        
        # Проверяем, что остались последние сообщения
        assert messages[0]["content"] == "Сообщение 4"
        assert messages[-1]["content"] == "Сообщение 9"
    
    def test_get_messages_for_llm_with_facts(self, context):
        """Проверяем форматирование для LLM с долгосрочными фактами."""
        # Arrange
        context.long_term_facts = ["Меня зовут Слава", "Я готовлюсь к ЕГЭ"]
        context.add_message("user", "Привет")
        
        # Act
        messages = context.get_messages_for_llm()
        
        # Assert
        assert len(messages) == 2, "Должно быть system + user"
        assert messages[0]["role"] == "system"
        assert "Меня зовут Слава" in messages[0]["content"]
        assert "Я готовлюсь к ЕГЭ" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Привет"
    
    def test_add_fact(self, context):
        """Проверяем добавление долгосрочных фактов."""
        context.add_fact("Любимый цвет — синий")
        context.add_fact("Любимая еда — пицца")
        
        assert len(context.long_term_facts) == 2
        assert "Любимый цвет — синий" in context.long_term_facts