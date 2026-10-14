# tests/test_jarvis.py
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from core.jarvis import Jarvis, AgentState


class TestJarvisFSM:
    """Тесты конечного автомата состояний."""
    
    @pytest.fixture
    def jarvis(self, tmp_path):
        """Создаем Джарвиса со всеми заглушками и безопасным конфигом."""
        # Создаем фейковый конфиг, чтобы Jarvis не пытался генерировать реальный
        config_file = tmp_path / "system.json"
        config_file.write_text('{"llm": {"provider": "mock"}}', encoding="utf-8")
        
        # Патчим создание тяжелых объектов внутри __init__
        with patch('core.jarvis.create_llm_provider') as mock_llm_factory, \
             patch('core.jarvis.TTS_Manager') as mock_tts_cls, \
             patch('core.jarvis.Vosk_STT') as mock_vosk_cls, \
             patch('core.jarvis.audio_in.AudioOpen') as mock_audio_in_cls, \
             patch('core.jarvis.audio_out.AudioOut') as mock_audio_out_cls:
            
            # Настраиваем возврат моков
            mock_llm = MagicMock()
            mock_llm.async_generate = AsyncMock(return_value="<thought>думаю</thought><response>Ответ</response>")
            mock_llm_factory.return_value = mock_llm
            
            mock_tts = MagicMock()
            mock_tts.queue = MagicMock()
            mock_tts.queue.put_nowait = MagicMock()
            mock_tts.queue.join = AsyncMock()
            mock_tts_cls.return_value = mock_tts
            
            # Создаем экземпляр (он использует наши моки благодаря patch)
            j = Jarvis(config_path=str(config_file))
            
            # Явно подменяем зависимости для чистоты тестов FSM
            j.vosk = MagicMock()
            j.audio_out = MagicMock()
            j.reg = MagicMock()
            j.llm = mock_llm
            j.context = MagicMock()
            j.context.get_messages_for_llm.return_value = [{"role": "user", "content": "hi"}]
            
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
        
        await jarvis.handle_input("привет")
        
        jarvis.llm.async_generate.assert_called_once()
        jarvis.context.add_message.assert_any_call("user", "привет")
        jarvis.context.add_message.assert_any_call("assistant", "Ответ")