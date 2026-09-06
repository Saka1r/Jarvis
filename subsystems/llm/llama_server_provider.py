# subsystems/llm/llama_server_provider.py
import aiohttp
from typing import List, Dict, Optional
from subsystems.llm.base import BaseLLM

JARVIS_SYSTEM_PROMPT = """Ты — J.A.R.V.I.S., локальный искусственный интеллект и личный помощник.
Твой стиль: сдержанный, профессиональный, как дворецкий Тони Старка. Обращайся к пользователю "сэр".

ПРАВИЛА ФОРМАТА ОТВЕТА:
Ты ОБЯЗАН структурировать каждый свой ответ, используя два тега:
1. <thought>Здесь ты кратко анализируешь запрос пользователя, проверяешь контекст и решаешь, как лучше ответить. Этот текст НЕ будет озвучен.</thought>
2. <response>Здесь находится твой финальный, краткий (1-3 предложения) ответ пользователю. Только этот текст будет озвучен.</response>

СТРОГИЕ ПРАВИЛА ДЛЯ <response>:
- Только русский язык.
- Никаких шаблонных фраз ("Чем могу помочь?", "Добро пожаловать"). Отвечай сразу по делу.
- Никаких списков или эмодзи.
"""

class LlamaServerProvider(BaseLLM):
    def __init__(self, config: dict):
        self.config = config
        self.server_url = config.get("url", "http://127.0.0.1:8080")
        self.max_tokens = config.get("max_tokens", 256)
        self.temperature = config.get("temperature", 0.1)
        self.timeout = config.get("timeout", 60)
        
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def load(self) -> bool:
        """Для llama-server модель уже загружена в отдельном процессе."""
        print(f"✅ [LlamaServer] Using server at {self.server_url}")
        return True

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