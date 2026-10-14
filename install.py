#!/usr/bin/env python3
"""
Умный установщик зависимостей для J.A.R.V.I.S. (v4.0 - Bulletproof)
Обходит конфликт chromadb/transformers и предотвращает обновление huggingface-hub до 1.x
"""

import subprocess
import sys
import platform

def get_os_type():
    system = platform.system().lower()
    if system == "windows": return "windows"
    elif system == "linux": return "linux"
    return "unknown"

def check_cuda_available():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version,name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None

def run_pip(args):
    """Вспомогательная функция для вызова pip"""
    cmd = [sys.executable, "-m", "pip"] + args
    print(f"🔄 Выполняю: pip install {' '.join(args[-3:])}...")
    subprocess.check_call(cmd)

def main():
    print("=" * 70)
    print("🤖 J.A.R.V.I.S. Installation")
    print("=" * 70)
    
    os_type = get_os_type()
    print(f"\n🖥️  ОС: {os_type.capitalize()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    
    cuda_available, gpu_info = check_cuda_available()
    use_cuda = False
    
    if cuda_available:
        print(f"\n✅ Обнаружена NVIDIA GPU:\n   {gpu_info}")
        choice = input("\nИспользовать CUDA-версию PyTorch? [Y/n]: ").strip().lower()
        use_cuda = choice != 'n'
    else:
        print("\n⚠️  NVIDIA GPU не обнаружена. Будет установлена CPU-версия.")
    
    confirm = input("\nПродолжить установку? [Y/n]: ").strip().lower()
    if confirm == 'n':
        sys.exit(0)
    
    # ШАГ 1: Обновляем pip и ставим PyTorch
    print("\n" + "=" * 70)
    print("📦 Шаг 1/3: Обновление pip и установка PyTorch")
    print("=" * 70)
    run_pip(["install", "--upgrade", "pip"])
    
    if use_cuda:
        run_pip(["install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu124"])
    else:
        run_pip(["install", "torch", "torchvision", "torchaudio"])

    # ШАГ 2: Ставим основные пакеты
    print("\n" + "=" * 70)
    print("📦 Шаг 2/3: Установка ML-стека")
    print("=" * 70)
    
    ml_packages = [
        "transformers>=4.44.0,<4.58.0",
        "sentence-transformers>=3.0.0,<4.0.0",
        "coqui-tts>=0.24.0,<0.28.0",
        "vosk==0.3.45",
        "sounddevice==0.5.5",
        "PyAudio==0.2.14",
        "httpx>=0.27.0,<0.29.0",
        "numpy>=1.24.0,<2.0.0",
        "scipy>=1.10.0,<1.16.0",
        "librosa>=0.10.0,<0.12.0",
        "aiohttp>=3.9.0,<4.0.0",
        "anyio>=4.0.0,<5.0.0",
        "pydub"
    ]
    
    if os_type == "windows":
        ml_packages.extend(["comtypes>=1.4.0", "pycaw"])
        
    run_pip(["install"] + ml_packages)

    # ШАГ 3: ChromaDB + хак для предотвращения поломки huggingface-hub
    print("\n" + "=" * 70)
    print("📦 Шаг 3/3: Установка ChromaDB и фиксация tokenizers")
    print("=" * 70)
    print("💡 Примечание: pip может ворчать на конфликты версий tokenizers.")
    print("   Мы используем хак (--no-deps), чтобы предотвратить это.")
    
    # 1. Ставим chromadb (он попытается стянуть старый tokenizers)
    run_pip(["install", "chromadb>=0.5.0,<0.6.0"])
    
    # 2. Жёстко ставим нужный tokenizers БЕЗ обновления его зависимостей
    # Это предотвращает скачивание huggingface-hub 1.x, который ломает transformers
    run_pip(["install", "--no-deps", "tokenizers>=0.22.0,<0.23.0"])
    
    # 3. На всякий случай фиксируем huggingface-hub в безопасной зоне
    run_pip(["install", "huggingface-hub>=0.34.0,<1.0"])

    # ПРОВЕРКА
    print("\n" + "=" * 70)
    print("✅ Финальная проверка")
    print("=" * 70)
    
    check_script = """
import torch
import transformers
import tokenizers
import chromadb
import numpy as np
import scipy

print(f"✅ PyTorch: {torch.__version__} (CUDA: {torch.cuda.is_available()})")
print(f"✅ Numpy: {np.__version__} (должно быть 1.26.x)")
print(f"✅ Scipy: {scipy.__version__}")
print(f"✅ Transformers: {transformers.__version__}")
print(f"✅ Tokenizers: {tokenizers.__version__} (должно быть 0.22.x)")
print(f"✅ ChromaDB: {chromadb.__version__}")
print("\\n🎉 Все зависимости установлены и совместимы!")
"""
    subprocess.check_call([sys.executable, "-c", check_script])
    
    print("\n" + "=" * 70)
    print("🚀 Установка завершена! Можешь запускать python main.py")
    print("=" * 70)

if __name__ == "__main__":
    main()