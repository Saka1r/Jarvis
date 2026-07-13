# core/context.py

import json
import os
import logging
from typing import List, Dict
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self, storage_path: str = "data/context.json", max_turns: int = 6):
        self.storage_path = storage_path
        self.max_turns = max_turns
        
        self.short_term = deque(maxlen=max_turns * 2)
        self.tool_cache = {}
        self.long_term_facts = []

        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.short_term = deque(data.get("short_term", []), maxlen=self.max_turns * 2)
                    self.tool_cache = data.get("tool_cache", {})
                    self.long_term_facts = data.get("long_term_facts", [])
                logger.info("💾 Контекст успешно загружен с диска.")
            except Exception as e:
                logger.error(f"Ошибка загрузки контекста: {e}")

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "short_term": list(self.short_term),
                    "tool_cache": self.tool_cache,
                    "long_term_facts": self.long_term_facts,
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения контекста: {e}")

    def add_message(self, role: str, content: str):
        if not content.strip():
            return
            
        content = content.strip()

        # ЗАЩИТА 1: Игнорируем точные дубликаты подряд (частая проблема STT)
        if self.short_term and self.short_term[-1]["role"] == role and self.short_term[-1]["content"] == content:
            return

        # ЗАЩИТА 2: Если роль та же самая (например, два 'user' подряд), 
        # мы ЗАМЕНЯЕМ последнее сообщение, а не добавляем новое. 
        # Это сохраняет чередование user/assistant, которое требует Llama 3.
        if self.short_term and self.short_term[-1]["role"] == role:
            logger.warning(f"⚠️ Обнаружено подряд идущее сообщение от {role}. Последнее сообщение обновлено.")
            self.short_term[-1]["content"] = content
        else:
            self.short_term.append({"role": role, "content": content})
            
        self._save()

    def add_tool_result(self, tool_name: str, query: str, result: str):
        import hashlib
        cache_key = hashlib.md5(f"{tool_name}:{query}".encode()).hexdigest()
        
        self.tool_cache[cache_key] = {
            "tool": tool_name,
            "query": query,
            "result": result[:2000],
            "timestamp": datetime.now().isoformat()
        }
        self._save()
        logger.info(f"💾 Кэширован результат инструмента: {tool_name}")

    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """
        Возвращает ТОЛЬКО историю диалога и факты.
        Системный промпт добавляется внутри LlamaLLM.generate().
        """
        messages = []
        
        # Добавляем факты о пользователе (если они есть)
        if self.long_term_facts:
            facts_text = "\n".join([f"- {fact}" for fact in self.long_term_facts])
            messages.append({"role": "system", "content": f"ПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ:\n{facts_text}"})

        # Добавляем историю диалога
        messages.extend(list(self.short_term))
        
        return messages

    def clear_short_term(self):
        self.short_term.clear()
        self._save()
        logger.info("🧹 Кратковременная память очищена.")