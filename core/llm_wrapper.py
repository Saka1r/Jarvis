"""
LLM Wrapper с Circuit Breaker, таймаутами и делегированием методов.
"""
from typing import List, Dict, Optional, Any
import asyncio
import time
import logging
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 2


class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
    
    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("🔌 Circuit Breaker: переход в HALF_OPEN")
                    return True
            return False
        
        return True
    
    def record_success(self) -> None:
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info("✅ Circuit Breaker: восстановлен")
    
    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("🔌 Circuit Breaker: разомкнут")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"🔌 Circuit Breaker: разомкнут после {self.failure_count} ошибок")


class LLMWrapper:
    """
    Обёртка над LLM с защитой от сбоев.
    
    Делегирует все методы оригинальному объекту через __getattr__,
    добавляя при этом:
    - Таймауты для всех async вызовов
    - Circuit Breaker для защиты от каскадных сбоев
    - Метрики производительности
    - Логирование
    """
    
    def __init__(
        self,
        llm_instance: Any,
        timeout: int = 30,
        fallback_message: str = "Извините, сэр, я сейчас не могу ответить.",
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Инициализация обёртки.
        
        Args:
            llm_instance: Оригинальный объект LLM (LlamaLLM)
            timeout: Таймаут для async вызовов в секундах
            fallback_message: Сообщение при сбое
            circuit_breaker_config: Конфигурация Circuit Breaker
        """
        # Сохраняем оригинальный объект как приватный атрибут
        self._llm = llm_instance
        self._timeout = timeout
        self._fallback_message = fallback_message
        self._circuit_breaker = CircuitBreaker(
            circuit_breaker_config or CircuitBreakerConfig()
        )
        
        # Метрики
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency_ms": 0.0,
            "max_latency_ms": 0.0
        }
    
    def __getattr__(self, name: str) -> Any:
        """
        Делегирование всех неизвестных атрибутов оригинальному объекту.
        
        Это позволяет вызывать:
        - self.llm.load()
        - self.llm.generate()
        - self.llm.async_generate_with_tools()
        - любые другие методы оригинального объекта
        """
        # Делегируем оригинальному объекту
        return getattr(self._llm, name)
    
    async def async_generate(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Генерация ответа с защитой от сбоев.
        
        Оборачивает оригинальный метод с таймаутом и метриками.
        """
        self._metrics["total_requests"] += 1
        
        if not self._circuit_breaker.can_execute():
            logger.warning("🔌 Circuit Breaker OPEN - используется fallback")
            self._metrics["failed_requests"] += 1
            return self._fallback_message
        
        start_time = time.time()
        
        try:
            async with asyncio.timeout(self._timeout):
                response = await self._llm.async_generate(messages, **kwargs)
            
            if not response or not response.strip():
                raise ValueError("Пустой ответ от LLM")
            
            # Успех
            self._circuit_breaker.record_success()
            self._metrics["successful_requests"] += 1
            
            latency_ms = (time.time() - start_time) * 1000
            self._metrics["total_latency_ms"] += latency_ms
            self._metrics["max_latency_ms"] = max(
                self._metrics["max_latency_ms"], latency_ms
            )
            
            logger.debug(f"✅ LLM response ({latency_ms:.0f}ms)")
            return response
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ LLM timeout после {self._timeout}с")
            self._record_failure()
            return self._fallback_message
        
        except Exception as e:
            logger.error(f"❌ Ошибка LLM: {e}", exc_info=True)
            self._record_failure()
            return self._fallback_message
    
    async def async_generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools_schema: List[Dict[str, Any]],
        **kwargs
    ) -> Any:
        """
        Генерация с инструментами с защитой от сбоев.
        
        Возвращает оригинальный response объект от _llm.
        """
        self._metrics["total_requests"] += 1
        
        if not self._circuit_breaker.can_execute():
            logger.warning("🔌 Circuit Breaker OPEN - пропускаем tool call")
            self._metrics["failed_requests"] += 1
            
            # Возвращаем объект с wants_tool = False
            # чтобы _dialog_turn завершил цикл
            return self._create_fallback_response()
        
        start_time = time.time()
        
        try:
            async with asyncio.timeout(self._timeout):
                response = await self._llm.async_generate_with_tools(
                    messages, tools_schema, **kwargs
                )
            
            self._circuit_breaker.record_success()
            self._metrics["successful_requests"] += 1
            
            latency_ms = (time.time() - start_time) * 1000
            self._metrics["total_latency_ms"] += latency_ms
            self._metrics["max_latency_ms"] = max(
                self._metrics["max_latency_ms"], latency_ms
            )
            
            logger.debug(f"✅ Tool call response ({latency_ms:.0f}ms)")
            return response
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Tool call timeout после {self._timeout}с")
            self._record_failure()
            return self._create_fallback_response()
        
        except Exception as e:
            logger.error(f"❌ Ошибка tool call: {e}", exc_info=True)
            self._record_failure()
            return self._create_fallback_response()
    
    def _record_failure(self) -> None:
        self._circuit_breaker.record_failure()
        self._metrics["failed_requests"] += 1
    
    def _create_fallback_response(self) -> Any:
        """Создаёт объект ответа с wants_tool = False."""
        # Если у оригинального LLM есть класс для ответов, используй его
        # Иначе создаём простой объект с нужными атрибутами
        class FallbackResponse:
            def __init__(self):
                self.wants_tool = False
                self.text = self._fallback_message
                self.tool_calls = []
            
            def as_assistant_message(self):
                return {"role": "assistant", "content": self.text}
        
        return FallbackResponse()
    
    def get_metrics(self) -> Dict[str, Any]:
        success_rate = (
            self._metrics["successful_requests"] / self._metrics["total_requests"] * 100
            if self._metrics["total_requests"] > 0 else 0
        )
        
        avg_latency = (
            self._metrics["total_latency_ms"] / self._metrics["successful_requests"]
            if self._metrics["successful_requests"] > 0 else 0
        )
        
        return {
            "total_requests": self._metrics["total_requests"],
            "success_rate_percent": round(success_rate, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "max_latency_ms": round(self._metrics["max_latency_ms"], 1),
            "circuit_breaker_state": self._circuit_breaker.state.value
        }
    
    def reset_circuit_breaker(self) -> None:
        self._circuit_breaker.state = CircuitState.CLOSED
        self._circuit_breaker.failure_count = 0
        self._circuit_breaker.success_count = 0
        logger.info("🔄 Circuit Breaker сброшен")
