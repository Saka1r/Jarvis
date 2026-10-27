# subsystems/llm/llama_server_provider.py
import aiohttp
import json
import re
import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple

from subsystems.llm.base import BaseLLM, LLMResponse, ToolCall

logger = logging.getLogger(__name__)

JARVIS_SYSTEM_PROMPT = """Ты — jarvis, локальный искусственный интеллект и личный помощник.
Твой стиль: сдержанный, профессиональный. Обращайся к пользователю "сэр". Твой создатель Святослав (Sakair).

ПРАВИЛА ФОРМАТА ОТВЕТА:
Ты ОБЯЗАН структурировать каждый свой ответ, используя два тега:
1. <thought>Здесь ты кратко анализируешь запрос пользователя, проверяешь контекст и решаешь, как лучше ответить. Этот текст НЕ будет озвучен.</thought>
2. <response>Здесь находится твой финальный, краткий (1-3 предложения) ответ пользователю. Только этот текст будет озвучен.</response>

СТРОГИЕ ПРАВИЛА ДЛЯ <response>:
- Только русский язык.
- Никаких шаблонных фраз ("Чем могу помочь?", "Добро пожаловать"). Отвечай сразу по делу.
- Никаких списков или эмодзи.
"""

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

TOOL_JSON_INSTRUCTION = """

ФОРМАТ ВЫЗОВА ИНСТРУМЕНТА:
Если для ответа нужны данные, которые ты не можешь получить сам, ответь СТРОГО одним JSON-блоком:
```json
{"tool": "<имя_инструмента>", "arguments": { ... }}
```
Правила:
    Используй только инструменты из списка ниже. Не выдумывай имена.
    Не более одного инструмента за ответ.
    Аргументы должны строго соответствовать JSON Schema инструмента.
    Если инструмент не нужен — отвечай в обычном формате <thought>/<response>.
"""

def _parse_arguments(raw: Any) -> Any:
    """Приводит arguments к dict; невалидные данные возвращает как есть (отклонит валидатор)."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return raw
    return raw

def _extract_json_tool_call(text: str) -> Tuple[List[ToolCall], str]:
    """
    Резервный JSON-протокол. Строгий парсинг: только валидный JSON
    с обязательным ключом "tool". eval/exec не используются.
    """
    text = text or ""
    candidates = [m.group(1) for m in _JSON_BLOCK_RE.finditer(text)]
    if not candidates:
        start = text.find("{")
        if start != -1 and '"tool"' in text[start:]:
            candidates.append(text[start:])

    for chunk in candidates:
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or "tool" not in obj:
            continue
        name = obj.get("tool")
        if not isinstance(name, str) or not name.strip():
            continue

        args = obj.get("arguments")
        call = ToolCall(
            id=f"json_{uuid.uuid4().hex[:8]}",
            name=name.strip(),
            arguments=args if args is not None else {},
        )
        cleaned = text.replace(chunk, "").replace("```json", "").replace("```", "").strip()
        return [call], cleaned

    return [], text

class LlamaServerProvider(BaseLLM):
    def __init__(self, config: dict):
        self.config = config
        self.server_url = config.get("url", "http://127.0.0.1:8080")
        self.max_tokens = config.get("max_tokens", 256)
        self.temperature = config.get("temperature", 0.1)
        self.timeout = config.get("timeout", 60)

        self.tool_mode = str(config.get("tool_mode", "native")).lower()
        if self.tool_mode not in ("native", "json", "off"):
            logger.warning("Неизвестный tool_mode '%s', использую 'native'", self.tool_mode)
            self.tool_mode = "native"
        
        self._tool_registry_desc: str = ""
        self._session: Optional[aiohttp.ClientSession] = None

    def set_tools_description(self, description: str) -> None:
        """Устанавливает текстовое описание инструментов для JSON-режима."""
        self._tool_registry_desc = description or ""

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def load(self) -> bool:
        """Для llama-server модель уже загружена в отдельном процессе."""
        print(f"✅ [LlamaServer] Using server at {self.server_url}")
        return True

    # ------------------------------------------------------------------
    # Вспомогательные методы tool calling
    # ------------------------------------------------------------------
    def _build_system_prompt(self, tools: List[Dict]) -> str:
        """Формирует system prompt с учётом режима."""
        if self.tool_mode == "json" and tools and self._tool_registry_desc:
            return (
                JARVIS_SYSTEM_PROMPT
                + TOOL_JSON_INSTRUCTION
                + "\nДОСТУПНЫЕ ИНСТРУМЕНТЫ:\n"
                + self._tool_registry_desc
            )
        
        # В native-режиме с инструментами используем упрощённый промпт,
        # чтобы не конфликтовать с форматом вызова инструментов
        if tools and self.tool_mode == "native":
            return (
                "Ты — Jarvis, локальный ИИ-ассистент. Обращайся к пользователю \"сэр\". "
                "Если тебе нужны данные для ответа — вызови подходящий инструмент. "
                "Отвечай кратко (1-3 предложения) на русском языке."
            )
        
        # Без инструментов — стандартный промпт
        return JARVIS_SYSTEM_PROMPT

    def _normalize_messages(self, messages: List[Dict], has_tools: bool) -> List[Dict]:
        """
        В native-режиме сообщения протокола tool calling передаются как есть.
        В json-режиме llama-server не ожидает role='tool' — преобразуем их
        в понятный текстовый вид.
        """
        if self.tool_mode != "json":
            return list(messages or [])

        out: List[Dict] = []
        for msg in messages or []:
            role = msg.get("role")

            if role == "tool":
                out.append({
                    "role": "user",
                    "content": (
                        f"[СИСТЕМА] Результат инструмента \"{msg.get('name', '?')}\": "
                        f"{msg.get('content', '')}\n"
                        f"Сформируй финальный ответ в формате <thought>/<response>. "
                        f"Не вызывай инструменты повторно."
                    ),
                })
            elif role == "assistant" and msg.get("tool_calls"):
                raw = msg.get("tool_calls")
                out.append({"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)})
            else:
                out.append({"role": role, "content": msg.get("content", "")})
        return out

    # ------------------------------------------------------------------
    # Основной метод
    # ------------------------------------------------------------------
    async def async_generate_with_tools(
        self,
        context_messages: List[Dict],
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        tools = tools or []
        use_native = (self.tool_mode == "native") and bool(tools)
        use_json = (self.tool_mode == "json") and bool(tools)

        if self.tool_mode == "off" or not tools:
            text = await self.async_generate(context_messages)
            return LLMResponse(text=text)

        session = await self._get_session()

        messages = [{"role": "system", "content": self._build_system_prompt(tools)}]
        messages.extend(self._normalize_messages(context_messages, bool(tools)))

        payload: Dict[str, Any] = {
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 0.9,
            "repeat_penalty": 1.15,
            "stream": False,
        }
        if use_native:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with session.post(f"{self.server_url}/v1/chat/completions", json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error("LLM server %s: %s", resp.status, error_text[:300])
                    return LLMResponse(text="")
                data = await resp.json()
        except Exception as e:
            logger.error("Ошибка соединения с LLM сервером: %s", e)
            return LLMResponse(text="")

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            logger.error("Не удалось разобрать ответ LLM: %s", str(data)[:300])
            return LLMResponse(text="")

        content = (message.get("content") or "").strip()

        # --- native tool calls ---
        if use_native:
            raw_calls = message.get("tool_calls") or []
            parsed: List[ToolCall] = []
            for idx, item in enumerate(raw_calls):
                fn = (item or {}).get("function") or {}
                name = fn.get("name")
                if not name:
                    continue
                parsed.append(ToolCall(
                    id=str(item.get("id") or f"call_{idx}"),
                    name=str(name),
                    arguments=_parse_arguments(fn.get("arguments")),
                ))
            if parsed:
                return LLMResponse(
                    text=content,
                    tool_calls=parsed,
                    native_payload={
                        "role": "assistant",
                        "content": message.get("content"),
                        "tool_calls": raw_calls,
                    },
                )

        # --- json fallback ---
        if use_json and content:
            calls, cleaned = _extract_json_tool_call(content)
            if calls:
                return LLMResponse(text=cleaned, tool_calls=calls)

        return LLMResponse(text=content)
 
    async def async_generate(self, context_messages: List[Dict]) -> str:
        session = await self._get_session()
        
        messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
        if context_messages:
            messages.extend(context_messages)

        payload = {
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 0.9,
            "repeat_penalty": 1.15,
            "stream": False
        }

        try:
            async with session.post(f"{self.server_url}/v1/chat/completions", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    error_text = await resp.text()
                    return f"[Ошибка сервера: {resp.status} - {error_text}]"
        except Exception as e:
            return f"[Ошибка соединения с LLM сервером: {str(e)}]"

    def unload(self):
        """Закрываем HTTP сессию."""
        if self._session and not self._session.closed:
            import asyncio
            asyncio.create_task(self._session.close())