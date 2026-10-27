# subsystems/llm/factory.py
from subsystems.llm.base import BaseLLM


def create_llm_provider(config: dict) -> BaseLLM:
    """
    Создаёт LLM-провайдер на основе конфига.

    Импорты провайдеров — ленивые (внутри веток), чтобы зависимости
    неиспользуемого провайдера (например, тяжёлый llama_cpp) не
    загружались и не могли уронить импорт всего ядра.
    """
    provider_name = config.get("provider", "llama_cpp")
    provider_config = config.get(provider_name, {})

    if provider_name == "llama_cpp":
        from subsystems.llm.llama_cpp_provider import LlamaCppProvider
        return LlamaCppProvider(provider_config)

    elif provider_name == "llama_server":
        from subsystems.llm.llama_server_provider import LlamaServerProvider
        return LlamaServerProvider(provider_config)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")