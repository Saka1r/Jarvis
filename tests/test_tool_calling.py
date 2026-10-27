# tests/test_tool_calling.py
"""
Тесты Tool Calling. Не требуют запуска реальной LLM:
используется FakeLLM со скриптом ответов.
"""
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.context import ContextManager
from core.jarvis import Jarvis, AgentState, MAX_TOOL_ROUNDS
from core.tools import ToolRegistry, register_builtin_tools, validate_arguments
from subsystems.llm.base import BaseLLM, LLMResponse, ToolCall


# --------------------------------------------------------------------------
# Тестовые двойники
# --------------------------------------------------------------------------
class FakeLLM(BaseLLM):
    """LLM со скриптом заранее заданных ответов."""

    def __init__(self, script=None):
        self.script = list(script or [])
        self.calls = []

    def load(self): return True
    def unload(self): pass

    def _next(self):
        return self.script.pop(0) if self.script else LLMResponse(text="<response>Готово.</response>")

    async def async_generate(self, context_messages):
        self.calls.append({"mode": "plain", "messages": list(context_messages), "tools": None})
        item = self._next()
        return item.text if isinstance(item, LLMResponse) else str(item)

    async def async_generate_with_tools(self, context_messages, tools=None):
        self.calls.append({"mode": "tools", "messages": list(context_messages), "tools": tools})
        item = self._next()
        return item if isinstance(item, LLMResponse) else LLMResponse(text=str(item))


class FakeRegistry:
    """Замена Registry: только tool API, без файлового ввода-вывода."""

    def __init__(self, tool_registry):
        self._tr = tool_registry
        self.executed = []

    def get_tools_schema(self):
        return self._tr.get_schemas()

    def is_tool_allowed(self, name):
        return self._tr.is_allowed(name)

    async def execute_tool(self, name, arguments):
        result = await self._tr.execute(name, arguments)
        self.executed.append((name, arguments, result))
        return result

    # для совместимости с COMMAND-режимом
    def is_command(self, text): return False
    def voice_plug_start(self, text): return None


def make_tool_registry():
    tr = ToolRegistry()
    register_builtin_tools(tr)
    return tr


def tool_call_response(name, args=None, call_id="call_1"):
    return LLMResponse(
        text="",
        tool_calls=[ToolCall(id=call_id, name=name, arguments=args or {})],
        native_payload={"role": "assistant", "content": None,
                        "tool_calls": [{"id": call_id, "type": "function",
                                        "function": {"name": name,
                                                     "arguments": json.dumps(args or {})}}]},
    )


# --------------------------------------------------------------------------
# Фикстура Jarvis
# --------------------------------------------------------------------------
@pytest.fixture
def jarvis(tmp_path):
    cfg = tmp_path / "system.json"
    cfg.write_text('{"llm": {"provider": "llama_server"}}', encoding="utf-8")

    with patch("core.jarvis.create_llm_provider") as mk_llm, \
         patch("core.jarvis.TTS_Manager") as mk_tts, \
         patch("subsystems.audio_out.AudioOut") as mk_ao, \
         patch("core.jarvis.ContextManager") as mk_ctx:
        mk_llm.return_value = MagicMock()
        mk_tts.return_value = MagicMock()
        mk_ao.return_value = MagicMock()
        mk_ctx.return_value = MagicMock()
        j = Jarvis(config_path=str(cfg))

    j.context = ContextManager(storage_path=str(tmp_path / "ctx.json"), max_turns=6)
    j.reg = FakeRegistry(make_tool_registry())
    j.llm = FakeLLM()
    j.vosk = MagicMock()
    j.audio_out = MagicMock()
    j._speak_and_wait = AsyncMock()   # перехватываем то, что попало бы в TTS
    j.state = AgentState.FREE
    return j


# --------------------------------------------------------------------------
# 1. Обычный ответ работает без вызова инструмента
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_plain_answer_no_tool(jarvis):
    jarvis.llm = FakeLLM(["<thought>простое приветствие</thought><response>Здравствуйте, сэр.</response>"])

    await jarvis.handle_input("привет")

    spoken = jarvis._speak_and_wait.call_args[0][0]
    assert spoken == "Здравствуйте, сэр."
    assert jarvis.reg.executed == []
    assert len(jarvis.llm.calls) == 1


# --------------------------------------------------------------------------
# 2. Запрос времени вызывает get_time
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_time_request_calls_get_time(jarvis):
    jarvis.llm = FakeLLM([
        tool_call_response("get_time", {}),
        "<thought>время получено</thought><response>Сейчас 15:30, сэр.</response>",
    ])

    await jarvis.handle_input("который час")

    assert len(jarvis.reg.executed) == 1
    name, args, result = jarvis.reg.executed[0]
    assert name == "get_time"
    assert result["ok"] is True
    assert "time" in result["result"]
    assert "date" in result["result"]

    spoken = jarvis._speak_and_wait.call_args[0][0]
    assert spoken == "Сейчас 15:30, сэр."


# --------------------------------------------------------------------------
# 3. Неизвестный инструмент отклоняется
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unknown_tool_rejected(jarvis):
    await jarvis.handle_input("удали все файлы")   # просто чтобы инициализировать
    result = await jarvis.reg.execute_tool("rm_everything", {})

    assert result["ok"] is False
    assert "не зарегистрирован" in result["error"]


@pytest.mark.asyncio
async def test_unknown_tool_does_not_crash_dialog(jarvis):
    jarvis.llm = FakeLLM([
        tool_call_response("drop_database", {}),
        "<response>Не могу выполнить это, сэр.</response>",
    ])

    await jarvis.handle_input("сделай что-нибудь опасное")

    assert jarvis.reg.executed[0][2]["ok"] is False
    spoken = jarvis._speak_and_wait.call_args[0][0]
    assert spoken == "Не могу выполнить это, сэр."


# --------------------------------------------------------------------------
# 4. Некорректные аргументы отклоняются
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_args_rejected(jarvis):
    # get_time не принимает аргументов (additionalProperties: false)
    r1 = await jarvis.reg.execute_tool("get_time", {"foo": "bar"})
    assert r1["ok"] is False
    assert "неизвестный аргумент" in r1["error"]

    # component вне enum
    r2 = await jarvis.reg.execute_tool("get_system_status", {"component": "gpu"})
    assert r2["ok"] is False
    assert "должен быть одним из" in r2["error"]

    # неверный тип
    r3 = await jarvis.reg.execute_tool("get_system_status", {"component": 123})
    assert r3["ok"] is False
    assert "тип" in r3["error"]

    # аргументы не объект
    r4 = await jarvis.reg.execute_tool("get_time", "не словарь")
    assert r4["ok"] is False


def test_validate_arguments_unit():
    schema = {"type": "object",
              "properties": {"q": {"type": "string"}},
              "required": ["q"], "additionalProperties": False}
    ok, cleaned, err = validate_arguments(schema, {"q": "test"})
    assert ok and cleaned == {"q": "test"}

    ok, _, err = validate_arguments(schema, {})
    assert not ok and "обязательный" in err


# --------------------------------------------------------------------------
# 5. Исключение инструмента не обрушает Jarvis
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tool_exception_is_contained(jarvis):
    def boom():
        raise RuntimeError("внутренний сбой")

    jarvis.reg._tr.register_function("boom_tool", "ломается",
                                     {"type": "object", "properties": {},
                                      "required": [], "additionalProperties": False},
                                     boom, timeout=2.0)

    result = await jarvis.reg.execute_tool("boom_tool", {})
    assert result["ok"] is False
    assert "сбой инструмента" in result["error"]
    assert "внутренний сбой" not in result["error"]   # детали не утекают


@pytest.mark.asyncio
async def test_tool_timeout_is_contained(jarvis):
    def slow():
        import time
        time.sleep(1.0)
        return {"x": 1}

    jarvis.reg._tr.register_function("slow_tool", "медленный",
                                     {"type": "object", "properties": {},
                                      "required": [], "additionalProperties": False},
                                     slow, timeout=0.1)

    result = await jarvis.reg.execute_tool("slow_tool", {})
    assert result["ok"] is False
    assert "тайм-аут" in result["error"]


# --------------------------------------------------------------------------
# 6. После вызова инструмента результат возвращается в LLM
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tool_result_fed_back_to_llm(jarvis):
    jarvis.llm = FakeLLM([
        tool_call_response("get_time", {}, call_id="call_42"),
        "<response>Время получено.</response>",
    ])

    await jarvis.handle_input("который час")

    assert len(jarvis.llm.calls) == 2
    second_messages = jarvis.llm.calls[1]["messages"]

    tool_msgs = [m for m in second_messages if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["tool_call_id"] == "call_42"
    assert tool_msgs[0]["name"] == "get_time"

    payload = json.loads(tool_msgs[0]["content"])
    assert payload["ok"] is True
    assert "time" in payload["result"]

    assistant_msgs = [m for m in second_messages if m.get("role") == "assistant" and m.get("tool_calls")]
    assert len(assistant_msgs) == 1


# --------------------------------------------------------------------------
# 7. В TTS попадает только финальный ответ
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_only_final_answer_reaches_tts(jarvis):
    jarvis.llm = FakeLLM([
        tool_call_response("get_system_status", {"component": "cpu"}),
        "<response>Процессор загружен на 12 процентов.</response>",
    ])

    await jarvis.handle_input("как там процессор")

    assert jarvis._speak_and_wait.call_count == 1
    spoken = jarvis._speak_and_wait.call_args[0][0]

    assert spoken == "Процессор загружен на 12 процентов."
    for forbidden in ("{", "}", "tool_call_id", "call_1", "get_system_status", "Traceback"):
        assert forbidden not in spoken


@pytest.mark.asyncio
async def test_thought_tags_do_not_leak_to_tts(jarvis):
    jarvis.llm = FakeLLM(["<thought>секретные рассуждения</thought>"])
    await jarvis.handle_input("тест")
    spoken = jarvis._speak_and_wait.call_args[0][0]
    assert "<thought>" not in spoken
    assert "секретные рассуждения" not in spoken


# --------------------------------------------------------------------------
# 8. Один запрос не запускает бесконечный цикл
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_infinite_tool_loop(jarvis):
    endless = [tool_call_response("get_time", {}, call_id=f"c{i}") for i in range(20)]
    jarvis.llm = FakeLLM(endless)

    await jarvis.handle_input("который час")

    # MAX_TOOL_ROUNDS итераций + 1 финальный запрос без инструментов
    assert len(jarvis.llm.calls) == MAX_TOOL_ROUNDS + 1
    assert jarvis.llm.calls[-1]["mode"] == "plain"
    assert jarvis._speak_and_wait.call_count == 1


# --------------------------------------------------------------------------
# 9. Старые команды и голосовой сценарий продолжают работать
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_command_mode_dialog_switch(jarvis):
    jarvis.state = AgentState.COMMAND
    await jarvis.handle_input("включи режим диалога")
    assert jarvis.state == AgentState.FREE
    jarvis.vosk.clear_grammar.assert_called_once()


@pytest.mark.asyncio
async def test_command_mode_wait_switch(jarvis):
    jarvis.state = AgentState.COMMAND
    await jarvis.handle_input("режим ожидания")
    assert jarvis.state == AgentState.WAIT


@pytest.mark.asyncio
async def test_wait_mode_wake_word(jarvis):
    jarvis.state = AgentState.WAIT
    await jarvis.handle_input("джарвис")
    assert jarvis.state == AgentState.COMMAND
    jarvis.vosk.set_grammar.assert_called_once()


@pytest.mark.asyncio
async def test_command_mode_plugin_path_untouched(jarvis):
    jarvis.state = AgentState.COMMAND
    jarvis.reg.is_command = MagicMock(return_value=True)
    jarvis.reg.voice_plug_start = MagicMock(return_value=None)

    await jarvis.handle_input("здарова")

    jarvis.reg.voice_plug_start.assert_called_once_with("здарова")
    assert jarvis.llm.calls == []          # LLM не задействована
    assert jarvis._speak_and_wait.call_count == 0


# --------------------------------------------------------------------------
# 10. История не перезаписывается и не дублируется
# --------------------------------------------------------------------------
@pytest.mark.xfail(reason="P1: add_message() перезаписывает подряд идущие user-сообщения. Фикс отложен до Этапа 2.")
def test_context_appends_not_overwrites(tmp_path):
    ctx = ContextManager(storage_path=str(tmp_path / "c.json"), max_turns=6)
    ctx.add_message("user", "первый")
    ctx.add_message("user", "второй")
    ctx.add_message("assistant", "ответ")

    msgs = ctx.get_messages_for_llm()
    contents = [m["content"] for m in msgs]
    assert contents == ["первый", "второй", "ответ"]


def test_context_skips_exact_duplicate(tmp_path):
    ctx = ContextManager(storage_path=str(tmp_path / "c.json"), max_turns=6)
    ctx.add_message("user", "да")
    ctx.add_message("user", "да")
    assert len(ctx.get_messages_for_llm()) == 1


def test_context_rejects_tool_role(tmp_path):
    ctx = ContextManager(storage_path=str(tmp_path / "c.json"), max_turns=6)
    ctx.add_message("user", "который час")
    ctx.add_message("tool", '{"ok": true}')
    ctx.add_message("assistant", "15:30")

    roles = [m["role"] for m in ctx.get_messages_for_llm()]
    assert roles == ["user", "assistant"]
    assert "tool" not in roles


def test_context_truncation_never_keeps_tool_messages(tmp_path):
    """Инструментальные сообщения не попадают в deque -> усечение безопасно."""
    ctx = ContextManager(storage_path=str(tmp_path / "c.json"), max_turns=2)
    for i in range(10):
        ctx.add_message("user", f"вопрос {i}")
        ctx.add_message("assistant", f"ответ {i}")

    msgs = ctx.get_messages_for_llm()
    assert len(msgs) == 4                      # max_turns * 2
    assert all(m["role"] in ("user", "assistant") for m in msgs)


def test_add_tool_result_persists(tmp_path):
    ctx = ContextManager(storage_path=str(tmp_path / "c.json"), max_turns=6)
    ctx.add_tool_result("get_time", "{}", '{"ok": true}')
    assert len(ctx.tool_cache) == 1
    # и при этом НЕ попадает в историю сообщений
    assert ctx.get_messages_for_llm() == []


# --------------------------------------------------------------------------
# Юнит-тесты ToolRegistry
# --------------------------------------------------------------------------
def test_builtin_tools_registered():
    tr = make_tool_registry()
    names = tr.list_names()
    assert "get_time" in names
    assert "get_system_status" in names


def test_schemas_are_openai_format():
    tr = make_tool_registry()
    schemas = tr.get_schemas()
    assert len(schemas) == 2
    for s in schemas:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "parameters" in s["function"]


@pytest.mark.asyncio
async def test_get_time_returns_real_values():
    tr = make_tool_registry()
    res = await tr.execute("get_time", {})
    assert res["ok"] is True
    assert len(res["result"]["time"]) == 8      # HH:MM:SS
    assert len(res["result"]["date"]) == 10     # YYYY-MM-DD


@pytest.mark.asyncio
async def test_get_system_status_components():
    tr = make_tool_registry()
    for comp in ("cpu", "memory", "disk", "all"):
        res = await tr.execute("get_system_status", {"component": comp})
        assert res["ok"] is True, comp
    res = await tr.execute("get_system_status", {})
    assert res["ok"] is True and "platform" in res["result"]


@pytest.mark.asyncio
async def test_result_size_is_limited():
    tr = ToolRegistry()
    tr.register_function(
        "big", "возвращает много данных",
        {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        lambda: {"blob": "x" * 50000},
        timeout=2.0,
    )
    res = await tr.execute("big", {})
    assert res["ok"] is True
    assert res["result"].get("_truncated") is True
    assert len(res["result"]["preview"]) <= 4000


@pytest.mark.asyncio
async def test_async_handler_supported():
    tr = ToolRegistry()

    async def handler():
        await asyncio.sleep(0)
        return {"async": True}

    tr.register_function("atool", "async", 
                         {"type": "object", "properties": {}, "required": [],
                          "additionalProperties": False}, handler, timeout=2.0)
    res = await tr.execute("atool", {})
    assert res["ok"] is True and res["result"] == {"async": True}