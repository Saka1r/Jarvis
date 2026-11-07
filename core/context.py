"""
Context Manager для Jarvis
Управляет кратковременной и долговременной памятью ассистента.
"""
from typing import List, Dict, Optional, Any
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Модель сообщения в диалоге"""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=10000)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ToolCall(BaseModel):
    """Модель вызова инструмента"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    success: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: int = Field(ge=0)


class ContextManager:
    """
    Менеджер контекста с поддержкой кратковременной и долговременной памяти.
    
    Features:
    - Автоматическое ограничение размера истории
    - Lazy save (сохранение не на каждом сообщении)
    - Очистка старых записей в кэше
    - Валидация через Pydantic
    """
    
    # Константы
    MAX_MESSAGE_LENGTH = 10000
    DEFAULT_MAX_TURNS = 6
    DEFAULT_MAX_FACTS = 100
    DEFAULT_CACHE_MAX_AGE_HOURS = 24
    SAVE_INTERVAL = 5  # Сохранять каждые N сообщений
    
    def __init__(
        self,
        storage_path: str = "data/context.json",
        max_turns: int = DEFAULT_MAX_TURNS,
        max_facts: int = DEFAULT_MAX_FACTS
    ):
        """
        Инициализация менеджера контекста.
        
        Args:
            storage_path: Путь к файлу сохранения контекста
            max_turns: Максимальное количество пар сообщений (user+assistant)
            max_facts: Максимальное количество долгосрочных фактов
        """
        self.storage_path = Path(storage_path)
        self.max_turns = max_turns
        self.max_facts = max_facts
        
        # Кратковременная память (история диалога)
        self.short_term: deque[Message] = deque(maxlen=max_turns * 2)
        
        # Кэш результатов инструментов
        self.tool_cache: Dict[str, ToolCall] = {}
        
        # Долговременная память (факты о пользователе)
        self.long_term_facts: List[str] = []
        
        # Счётчик для lazy save
        self._save_counter = 0
        
        # Загружаем сохранённый контекст
        self._load()
    
    def _load(self) -> None:
        """Загрузка контекста с диска"""
        if not self.storage_path.exists():
            logger.info(f"📝 Файл контекста не найден: {self.storage_path}")
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Загружаем кратковременную память
            if "short_term" in data:
                self.short_term = deque(
                    [Message(**msg) for msg in data["short_term"]],
                    maxlen=self.max_turns * 2
                )
            
            # Загружаем кэш инструментов
            if "tool_cache" in data:
                self.tool_cache = {
                    k: ToolCall(**v) 
                    for k, v in data["tool_cache"].items()
                }
            
            # Загружаем долгосрочные факты
            if "long_term_facts" in data:
                self.long_term_facts = data["long_term_facts"][:self.max_facts]
            
            logger.info(f"💾 Контекст загружен: {len(self.short_term)} сообщений, {len(self.long_term_facts)} фактов")
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            self._backup_corrupted_file()
        except Exception as e:
            logger.error(f"Ошибка загрузки контекста: {e}", exc_info=True)
    
    def _save(self) -> None:
        """Сохранение контекста на диск"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "short_term": [msg.dict() for msg in self.short_term],
                "tool_cache": {k: v.dict() for k, v in self.tool_cache.items()},
                "long_term_facts": self.long_term_facts,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.debug("💾 Контекст сохранён")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения контекста: {e}", exc_info=True)
    
    def _backup_corrupted_file(self) -> None:
        """Создание бэкапа повреждённого файла"""
        backup_path = self.storage_path.with_suffix('.corrupted.json')
        try:
            self.storage_path.rename(backup_path)
            logger.warning(f"⚠️ Повреждённый файл перемещён: {backup_path}")
        except Exception as e:
            logger.error(f"Не удалось создать бэкап: {e}")
    
    def add_message(self, role: str, content: str) -> bool:
        """
        Добавление сообщения в историю.
        
        Args:
            role: Роль (user/assistant/system)
            content: Текст сообщения
        
        Returns:
            True если сообщение добавлено, False если пропущено
        """
        try:
            # Валидация через Pydantic
            message = Message(role=role, content=content)
        except Exception as e:
            logger.warning(f"Невалидное сообщение: {e}")
            return False
        
        # Проверка на дубликаты (последние 3 сообщения)
        if len(self.short_term) >= 3:
            last_three = list(self.short_term)[-3:]
            if all(msg.content == message.content for msg in last_three):
                logger.debug(f"Дубль сообщения пропущен: {content[:50]}")
                return False
        
        # Добавляем сообщение
        self.short_term.append(message)
        
        # Lazy save
        self._save_counter += 1
        if self._save_counter >= self.SAVE_INTERVAL:
            self._save()
            self._save_counter = 0
        
        return True
    
    def add_fact(self, fact: str) -> bool:
        """
        Добавление долгосрочного факта.
        
        Args:
            fact: Текст факта
        
        Returns:
            True если факт добавлен
        """
        if not fact or not fact.strip():
            return False
        
        # Ограничиваем размер
        if len(self.long_term_facts) >= self.max_facts:
            removed = self.long_term_facts.pop(0)
            logger.debug(f"Удалён старый факт: {removed[:50]}")
        
        self.long_term_facts.append(fact.strip())
        self._save()
        
        logger.info(f"💭 Добавлен факт: {fact[:50]}...")
        return True
    
    def add_tool_call(self, tool_name: str, arguments: Dict[str, Any], 
                      result: Any, success: bool, duration_ms: int) -> None:
        """
        Добавление результата вызова инструмента в кэш.
        
        Args:
            tool_name: Название инструмента
            arguments: Аргументы вызова
            result: Результат выполнения
            success: Успешность выполнения
            duration_ms: Время выполнения в мс
        """
        try:
            tool_call = ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=success,
                duration_ms=duration_ms
            )
            
            # Ключ кэша: tool_name + хеш аргументов
            cache_key = f"{tool_name}:{hash(str(sorted(arguments.items())))}"
            self.tool_cache[cache_key] = tool_call
            
            logger.debug(f"🔧 Tool call cached: {tool_name}")
            
        except Exception as e:
            logger.error(f"Ошибка добавления tool call: {e}", exc_info=True)
    
    def get_cached_tool_result(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[ToolCall]:
        """
        Получение кэшированного результата вызова инструмента.
        
        Args:
            tool_name: Название инструмента
            arguments: Аргументы вызова
        
        Returns:
            ToolCall если найден в кэше, иначе None
        """
        cache_key = f"{tool_name}:{hash(str(sorted(arguments.items())))}"
        return self.tool_cache.get(cache_key)
    
    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """
        Получение сообщений для отправки в LLM.
        
        Returns:
            Список сообщений в формате OpenAI API
        """
        messages = []
        
        # Добавляем долгосрочные факты как system prompt
        if self.long_term_facts:
            facts_text = "\n".join([f"- {fact}" for fact in self.long_term_facts])
            messages.append({
                "role": "system",
                "content": f"ПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ:\n{facts_text}"
            })
        
        # Добавляем историю диалога
        for msg in self.short_term:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def clear_short_term(self) -> None:
        """Очистка кратковременной памяти"""
        self.short_term.clear()
        self._save()
        logger.info("🧹 Кратковременная память очищена")
    
    def clear_tool_cache(self, max_age_hours: int = DEFAULT_CACHE_MAX_AGE_HOURS) -> int:
        """
        Очистка старых записей в кэше инструментов.
        
        Args:
            max_age_hours: Максимальный возраст записей в часах
        
        Returns:
            Количество удалённых записей
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        old_count = len(self.tool_cache)
        
        self.tool_cache = {
            k: v for k, v in self.tool_cache.items()
            if v.timestamp > cutoff
        }
        
        removed_count = old_count - len(self.tool_cache)
        
        if removed_count > 0:
            logger.info(f"🧹 Удалено {removed_count} старых записей из кэша инструментов")
            self._save()
        
        return removed_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики контекста.
        
        Returns:
            Словарь со статистикой
        """
        return {
            "short_term_count": len(self.short_term),
            "long_term_facts_count": len(self.long_term_facts),
            "tool_cache_count": len(self.tool_cache),
            "storage_path": str(self.storage_path),
            "storage_exists": self.storage_path.exists(),
            "max_turns": self.max_turns,
            "max_facts": self.max_facts
        }
