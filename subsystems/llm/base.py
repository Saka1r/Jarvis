# subsystems/llm/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """Запрос модели на вызов инструмента."""
    id: str
    name: str
    arguments: Any = field(default_factory=dict)   # Any: не-dict отклоняется валидатором


@dataclass
class LLMResponse:
    """
    Структурированный ответ LLM.

    Позволяет представить три случая:
      1. обычный текст              -> text != "", tool_calls == []
      2. запрос(ы) инструментов     -> tool_calls != []
      3. текст + запрос инструментов -> оба поля заполнены
    """
    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    # исходное сообщение провайдера (native-режим) для корректной записи в историю
    native_payload: Optional[Dict[str, Any]] = None

    @property
    def wants_tool(self) -> bool:
        return len(self.tool_calls) > 0

    def as_assistant_message(self) -> Dict[str, Any]:
        """Сообщение для записи в историю текущего хода диалога."""
        if self.native_payload is not None:
            return dict(self.native_payload)
        return {"role": "assistant", "content": self.text}


class BaseLLM(ABC):
    """Абстрактный интерфейс для всех LLM провайдеров."""

    @abstractmethod
    async def async_generate(self, context_messages: List[Dict]) -> str:
        """Асинхронная генерация ответа."""
        pass

    async def async_generate_with_tools(
        self,
        context_messages: List[Dict],
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        """
        Генерация с поддержкой tool calling.

        Реализация по умолчанию: провайдер НЕ поддерживает нативный
        tool calling — возвращаем обычный текст. Это сохраняет обратную
        совместимость: LlamaCppProvider продолжает работать без изменений.
        """
        text = await self.async_generate(context_messages)
        return LLMResponse(text=text or "")

    @abstractmethod
    def load(self) -> bool:
        """Загрузка модели."""
        pass

    @abstractmethod
    def unload(self):
        """Выгрузка модели."""
        pass