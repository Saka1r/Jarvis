# subsystems/llama_llm.py
import asyncio
import os
from typing import List, Dict, Optional
from llama_cpp import Llama

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

ПРИМЕР:
User: Что такое аниме?
Assistant: 
<thought>Пользователь спрашивает определение аниме. Нужно дать краткое, точное определение, обратившись к нему "сэр", без лишней воды.</thought>
<response>Аниме — это японская мультипликация, сэр, отличающаяся уникальным визуаль стилем и разнообразием жанров.</response>
"""

class LlamaLLM:
    def __init__(
        self, 
        model_path: str = "data/models/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf",
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        n_threads: int = 8,
        max_tokens: int = 256
    ):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.n_threads = n_threads
        self.max_tokens = max_tokens
        self._llm: Optional[Llama] = None
        self._loaded = False

    def load(self) -> bool:
        if self._loaded:
            return True
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
            
        try:
            print(f"⏳ Loading LLM model ({self.n_gpu_layers} layers on GPU)...")
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                n_threads=self.n_threads,
                n_batch=512,
                verbose=False,
                chat_format="llama-3" 
            )
            self._loaded = True
            print("✅ LLM model loaded successfully.")
            return True
        except Exception as e:
            print(f"❌ Failed to load LLM: {e}")
            return False

    def generate(self, context_messages: List[Dict]) -> str:
        """
        Принимает ТОЛЬКО контекст (историю диалога).
        user_input уже добавлен в context_messages через context.add_message("user", text)
        """
        if not self._loaded or self._llm is None:
            raise RuntimeError("LLM model not loaded.")

        messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
        
        if context_messages:
            messages.extend(context_messages)

        # 🔍 ДЕБАГ:
        print("\n" + "="*80)
        print("📤 ОТПРАВЛЯЮ В LLM:")
        for i, msg in enumerate(messages):
            print(f"[{i}] {msg['role'].upper()}: {msg['content'][:80]}...")
        print("="*80 + "\n")

        response = self._llm.create_chat_completion(
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=0.1,  # холоднее для предсказуемости
            top_p=0.9,
            repeat_penalty=1.15,
        )

        try:
            return response["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            return f"[Ошибка генерации: {str(e)}]"

    async def async_generate(self, context_messages: List[Dict]) -> str:
        """Асинхронная обёртка. Сигнатура должна совпадать с generate()."""
        return await asyncio.to_thread(self.generate, context_messages)

    def unload(self):
        if self._llm:
            del self._llm
            self._llm = None
            self._loaded = False

if __name__ == "__main__":
    llm = LlamaLLM()
    llm.load()
    #print("🔹 Тест:", llm.generate("Привет кто ты?"))
    
