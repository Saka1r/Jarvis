# subsystems/llm/factory.py
from subsystems.llm.base import BaseLLM
from subsystems.llm.llama_cpp_provider import LlamaCppProvider
from subsystems.llm.llama_server_provider import LlamaServerProvider

def create_llm_provider(config: dict) -> BaseLLM:
    """Создает LLM провайдер на основе конфига."""
    provider_name = config.get("provider", "llama_cpp")
    provider_config = config.get(provider_name, {})
    
    if provider_name == "llama_cpp":
        return LlamaCppProvider(provider_config)
    elif provider_name == "llama_server":
        return LlamaServerProvider(provider_config)
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")