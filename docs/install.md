# Установка

## Требования

- Python 3.10+
- CUDA (опционально, для ускорения TTS/LLM)
- Микрофон и аудиовыход
- ~8 ГБ VRAM для Llama-3.1-8B-Q6_K

## Шаги

```bash
git clone https://github.com/Saka1r/jarvis.git
cd jarvis
pip install -r requirements.txt
```

## Модели 

Положи в models vosk и LLM.

```bash
data/models/:
    vosk/ — модель Vosk для русского языка
    Meta-Llama-3.1-8B-Instruct-Q6_K.gguf — LLM
```

## Запуск

```bash
python main.py
```
