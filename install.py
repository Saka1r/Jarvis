#!/usr/bin/env python3
"""
Умный установщик зависимостей для J.A.R.V.I.S.
Автоматически определяет ОС, CUDA и устанавливает правильные версии.
"""

import subprocess
import sys
import platform
import os

def get_os_type():
    """Определяет тип операционной системы."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    else:
        return "unknown"

def check_cuda_available():
    """Проверяет наличие CUDA в системе."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version,name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            gpu_info = result.stdout.strip()
            return True, gpu_info
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None

def install_with_pip(packages, extra_args=None):
    """Устанавливает пакеты через pip."""
    cmd = [sys.executable, "-m", "pip", "install"]
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend(packages)
    
    print(f"\n📦 Устанавливаю: {', '.join(packages[:3])}...")
    subprocess.check_call(cmd)

def main():
    print("=" * 70)
    print("🤖 J.A.R.V.I.S. Installation Wizard")
    print("=" * 70)
    
    # 1. Определение ОС
    os_type = get_os_type()
    print(f"\n🖥️  Операционная система: {os_type.capitalize()}")
    
    if os_type == "unknown":
        print("❌ Неподдерживаемая операционная система")
        sys.exit(1)
    
    # 2. Проверка CUDA
    cuda_available, gpu_info = check_cuda_available()
    
    if cuda_available:
        print(f"\n✅ Обнаружена NVIDIA GPU:")
        print(f"   {gpu_info}")
        choice = input("\nИспользовать CUDA-версию PyTorch? [Y/n]: ").strip().lower()
        use_cuda = choice != 'n'
    else:
        print("\n⚠️  NVIDIA GPU не обнаружена или драйвер CUDA не установлен")
        print("💡 Если у тебя есть GPU, установи драйвер NVIDIA и перезапусти скрипт")
        use_cuda = False
    
    # 3. Подтверждение
    print(f"\n📋 Конфигурация установки:")
    print(f"   ОС: {os_type.capitalize()}")
    print(f"   PyTorch: {'CUDA 12.4' if use_cuda else 'CPU'}")
    
    confirm = input("\nПродолжить установку? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("❌ Установка отменена")
        sys.exit(0)
    
    # 4. Установка PyTorch (самый большой пакет)
    print("\n" + "=" * 70)
    print("📦 Шаг 1/2: Установка PyTorch")
    print("=" * 70)
    
    if use_cuda:
        # CUDA версия
        torch_packages = [
            "torch==2.5.1",
            "torchvision==0.20.1",
            "torchaudio==2.5.1"
        ]
        install_with_pip(
            torch_packages,
            extra_args=["--index-url", "https://download.pytorch.org/whl/cu124"]
        )
    else:
        # CPU версия
        torch_packages = [
            "torch==2.5.1",
            "torchvision==0.20.1",
            "torchaudio==2.5.1"
        ]
        install_with_pip(torch_packages)
    
    # 5. Установка остальных зависимостей
    print("\n" + "=" * 70)
    print("📦 Шаг 2/2: Установка остальных зависимостей")
    print("=" * 70)
    
    # Общие зависимости для всех платформ
    base_packages = [
        "transformers==4.57.6",
        "sentence-transformers==3.0.1",
        "coqui-tts==0.27.5",
        "vosk==0.3.45",
        "sounddevice==0.5.5",
        "PyAudio==0.2.14",
        "httpx==0.28.1",
        "numpy<2.0.0",
        "scipy==1.17.1",
        "librosa==0.11.0",
        "pydub",
        "aiohttp==3.14.1",
        "anyio==4.14.0",
        "llama_cpp_python==0.3.30"
    ]
    
    # Специфичные для Windows
    if os_type == "windows":
        base_packages.extend([
            "comtypes==1.4.16",
            "pycaw==20251023"
        ])
    
    # Специфичные для Linux
    if os_type == "linux" and use_cuda:
        # NVIDIA библиотеки для Linux
        base_packages.extend([
            "nvidia-cublas-cu12==12.4.5.8",
            "nvidia-cuda-cupti-cu12==12.4.127",
            "nvidia-cuda-nvrtc-cu12==12.4.127",
            "nvidia-cuda-runtime-cu12==12.4.127",
            "nvidia-cudnn-cu12==9.1.0.70",
            "nvidia-cufft-cu12==11.2.1.3",
            "nvidia-curand-cu12==10.3.5.147",
            "nvidia-cusolver-cu12==11.6.1.9",
            "nvidia-cusparse-cu12==12.3.1.170",
            "nvidia-nccl-cu12==2.21.5",
            "nvidia-nvjitlink-cu12==12.4.127",
            "nvidia-nvtx-cu12==12.4.127",
            "triton==3.1.0"
        ])
    
    install_with_pip(base_packages)
    
    # 6. Проверка установки
    print("\n" + "=" * 70)
    print("✅ Проверка установки")
    print("=" * 70)
    
    check_script = """
import torch
import transformers
import TTS
import vosk

print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
print(f"✅ Transformers: {transformers.__version__}")
print(f"✅ Coqui TTS: {TTS.__version__}")
print(f"✅ Vosk: {vosk.__version__}")
print("\\n🎉 Все зависимости установлены успешно!")
"""
    
    subprocess.check_call([sys.executable, "-c", check_script])
    
    print("\n" + "=" * 70)
    print("🚀 Установка завершена!")
    print("=" * 70)
    print("\nСледующие шаги:")
    print("1. Скачай модели в data/models/")
    print("2. Запусти: python main.py")
    print("\nДокументация: https://github.com/Saka1r/Jarvis")

if __name__ == "__main__":
    main()