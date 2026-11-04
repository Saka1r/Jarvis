# download_silero_vad.py
import torch
import os

print("⏳ Загрузка Silero VAD через официальный PyTorch Hub (нужен интернет)...")

try:
    # Официальный способ загрузки, который автоматически обходит изменения в структуре репозитория
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        trust_repo=True
    )
    
    # Сохраняем модель в формате JIT для полностью офлайн использования в будущем
    save_dir = "data/models/silero_vad"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "silero_vad.jit")
    
    torch.jit.save(model, save_path)
    
    file_size = os.path.getsize(save_path) / (1024 * 1024)
    print(f"✅ Модель успешно сохранена в {save_path} ({file_size:.2f} МБ)")
    print("🎉 Теперь ты можешь отключить интернет, она будет работать полностью локально!")
    
except Exception as e:
    print(f"❌ Ошибка загрузки: {e}")
    print("Проверь подключение к интернету и попробуй снова.")
