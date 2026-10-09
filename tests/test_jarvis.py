# tests/test_jarvis.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from core.jarvis import Jarvis, AgentState


class TestJarvisFSM:
    """Тесты конечного автомата состояний."""
    
    @pytest.fixture
    def jarvis(self):
        """Создаем Джарвиса со всеми заглушками."""
        j = Jarvis()
        
        # Заменяем реальные подсистемы на заглушки
        j.vosk = MagicMock()
        j.audio_out = MagicMock()
        j.reg = MagicMock()
        j.llm = AsyncMock()
        j.context = MagicMock()
        
        # Мок для LLM ответа
        j.llm.async_generate.return_value = "<thought>думаю</thought><response>Ответ</response>"
        
        return j
    
    @pytest.mark.asyncio
    async def test_command_mode_to_dialog_mode(self, jarvis):
        """Фраза 'режим диалога' должна переключить состояние в FREE."""
        jarvis.state = AgentState.COMMAND
        
        await jarvis.handle_input("включи режим диалога")
        
        assert jarvis.state == AgentState.FREE
        jarvis.vosk.clear_grammar.assert_called_once()
        jarvis.audio_out.play.assert_called_once_with("data/jarvis_wav/yes_sir.wav")
    
    @pytest.mark.asyncio
    async def test_command_mode_unknown_command(self, jarvis):
        """Неизвестная команда не меняет состояние."""
        jarvis.state = AgentState.COMMAND
        jarvis.reg.is_command.return_value = False
        
        await jarvis.handle_input("что-то непонятное")
        
        assert jarvis.state == AgentState.COMMAND
    
    @pytest.mark.asyncio
    async def test_wait_mode_to_command_with_jarvis_keyword(self, jarvis):
        """Слово 'джарвис' должно вывести из режима ожидания."""
        jarvis.state = AgentState.WAIT
        
        await jarvis.handle_input("джарвис")
        
        assert jarvis.state == AgentState.COMMAND
        jarvis.vosk.set_grammar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_free_mode_calls_llm(self, jarvis):
        """В режиме FREE должна вызываться LLM."""
        jarvis.state = AgentState.FREE
        jarvis.context.get_messages_for_llm.return_value = [
            {"role": "user", "content": "hi"}
        ]
        
        await jarvis.handle_input("привет")
        
        jarvis.llm.async_generate.assert_called_once()
        jarvis.context.add_message.assert_any_call("user", "привет")
        jarvis.context.add_message.assert_any_call("assistant", "Ответ")