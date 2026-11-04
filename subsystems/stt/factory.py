#subsystems/stt/factory.py
from subsystems.stt.base import BaseSTT

def create_stt_provider(config: dict) -> BaseSTT:
    provider_name = config.get("provider", "vosk")
    provider_config = config.get(provider_name, {})

    if provider_name == "vosk":
        from subsystems.stt.vosk_stt import Vosk_STT 
        return Vosk_STT(provider_config)
    elif provider_name == "whisper":
        from subsystems.stt.whisper_provider import WhisperProvider 
        return WhisperProvider(provider_config)
    else:
        raise ValueError(f"Неизвестный STT провайдер: {provider_name}")
