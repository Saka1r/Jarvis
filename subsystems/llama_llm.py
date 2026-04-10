# subsystems/llama_llm.py
import asyncio
import os
from typing import List, Dict, Optional
from llama_cpp import Llama

class LlamaLLM:
    def __init__(
        self, 
        model_path: str = "data/llama-7b-chat.gguf",
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        n_threads: int = 8,
        max_tokens: int = 300
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
                verbose=False
            )
            self._loaded = True
            print("✅ LLM model loaded successfully.")
            return True
        except Exception as e:
            print(f"❌ Failed to load LLM: {e}")
            return False

    def unload(self):
        if self._llm:
            del self._llm
            self._llm = None
            self._loaded = False

    def generate(self, user_input: str, context: Optional[List[Dict]] = None) -> str:
        if not self._loaded or self._llm is None:
            raise RuntimeError("LLM model not loaded. Call load() first.")

        # Формируем сообщения в формате OpenAI Chat
        messages = [
            {
                "role": "system", 
                "content": (
                    "Ты — Джарвис, вежливый и доброжелательный помощник. "
                    "Отвечай ИСКЛЮЧИТЕЛЬНО НА РУССКОМ ЯЗЫКЕ. "
                    "Будь краток (1-3 предложения), отвечай строго по делу. "
                    "Не используй списки, маркировку или форматы типа A:/B:/C:. "
                    "Если не знаешь точного ответа, так и скажи: 'Не уверен, но могу уточнить'."
                )
            }
        ]
        
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": user_input})

        response = self._llm.create_chat_completion(
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=0.2,
            top_p=0.9,
            top_k=40,
            repeat_penalty=1.1,
            # stop_tokens убраны: чат-формат сам корректно останавливает генерацию
        )

        try:
            return response["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            return f"[Ошибка генерации: {str(e)}]"

    async def async_generate(self, user_input: str, context: Optional[List[Dict]] = None) -> str:
        """Асинхронная обёртка. Не блокирует asyncio event loop."""
        return await asyncio.to_thread(self.generate, user_input, context)

if __name__ == "__main__":
    llm = LlamaLLM()
    llm.load()
    print("🔹 Тест:", llm.generate("Привет кто ты?"))