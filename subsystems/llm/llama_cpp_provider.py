# subsystems/llm/llama_cpp_provider.py
import os
from typing import List, Dict, Optional
from llama_cpp import Llama
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

class LlamaCppProvider(BaseLLM):
    def __init__(self, config: dict):
        self.config = config
        self.model_path = config.get("model_path", "data/models/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf")
        self.n_ctx = config.get("n_ctx", 4096)
        self.n_gpu_layers = config.get("n_gpu_layers", -1)
        self.n_threads = config.get("n_threads", 8)
        self.n_batch = config.get("n_batch", 1024)
        self.max_tokens = config.get("max_tokens", 256)
        
        self._llm: Optional[Llama] = None
        self._loaded = False

    def load(self) -> bool:
        if self._loaded:
            return True
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
            
        try:
            print(f"⏳ [LlamaCpp] Loading model ({self.n_gpu_layers} layers on GPU)...")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_threads=self.n_threads,
                n_batch=self.n_batch,
                n_threads_batch=self.n_threads,
                mmap=False,
                verbose=False,
                chat_format="llama-3"
            )
            self._loaded = True
            print("✅ [LlamaCpp] Model loaded successfully.")
            return True
        except Exception as e:
            print(f"❌ [LlamaCpp] Failed to load: {e}")
            return False

    async def async_generate(self, context_messages: List[Dict]) -> str:
        import asyncio
        
        if not self._loaded or self._llm is None:
            raise RuntimeError("LLM model not loaded.")

        messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
        if context_messages:
            messages.extend(context_messages)

        def _generate():
            return self._llm.create_chat_completion(
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.1,
                top_p=0.9,
                repeat_penalty=1.15,
                stream=False
            )

        response = await asyncio.to_thread(_generate)

        try:
            return response["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            return f"[Ошибка генерации: {str(e)}]"

    def unload(self):
        if self._llm:
            del self._llm
            self._llm = None
            self._loaded = False