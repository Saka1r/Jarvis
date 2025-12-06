# Основной модуль для распознование голоса 

from picovoice import Picovoice
from picovoice import PicovoiceError

from vosk import Model, KaldiRecognizer
from playsound import playsound

import json
import pyaudio
import numpy as np
import random
import time
import threading
import importlib
from module import read_module

stream = None
p = None
is_stream_open = False
word_detect = False
lock = threading.Lock()
model = Model('config_files/small_model')

def kill_stream():
    global stream, is_stream_open
    with lock:
        if is_stream_open and stream is not None:
            stream.stop_stream()
            stream.close()
            is_stream_open = False
            print("Stream stopped.")

def get_commmands():
    with open("config_files/config.json", 'r', encoding="utf-8") as f:
        config_content = json.load(f)
    return config_content["Commands"]

def wake_word_vosk():
    global word_detect, is_stream_open
    # timed1 = time.time()

    #Раскоментировать если нужно что бы был отсчет до разпознания команды

    commands = get_commmands()

    commands = sorted(commands.keys())
    #print(type(commands))

    dop_com = ["пока пока", "пока", "запрос", "запрос на английском"]

    for i in dop_com:
        commands.append(i)

    commands = json.dumps(commands,  ensure_ascii=False)

    rec = KaldiRecognizer(model, 16000, commands)
    p = pyaudio.PyAudio()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=8000)
    stream.start_stream()
    is_stream_open = True

    def listen():
        while True:
            with lock:  # Защита доступа к потоку
                if not is_stream_open:
                    break  

            # timed2 = time.time()
            data = stream.read(4000, exception_on_overflow=False)

            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = rec.Result()
                result_json = json.loads(result)
                if result_json.get("text"):  # Проверяем наличие текста
                    yield result_json["text"]
            # if word_detect == False:
            #     print(timed2 - timed1)
            #     if timed2 - timed1 >= 10:
            #         kill_stream() 

    for text in listen():
        #print(text)
        word_detect = True
        config = read_module()
        if text in config["Commands"]:
            folder_name = config["Commands"][text]
            try:
                module = importlib.import_module(f"modules.{folder_name}.__main__")
                if hasattr(module, 'run'):
                    stream.stop_stream()
                    module.run()
                    start()
                else:
                    print(f"В модуле {folder_name} не найдена функция run()")
            except ModuleNotFoundError as e:
                print(f"Ошибка при импорте модуля: {e}")

        elif text == 'пока пока' or text == 'пока':
            kill_stream()
            speak = 'config_files/jarvis_speech/bye.wav'
            playsound(speak)
        elif text == 'запрос':
            stream.stop_stream()
            print('Начинаю запрос')
            playsound('config_files/jarvis_speech/ok.wav')
            rec = KaldiRecognizer(model, 16000)
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
            for text in listen():
                module = importlib.import_module(f"modules.Search.__main__")
                if hasattr(module, 'run'):
                    stream.stop_stream()
                    print(text)
                    module.run(text)
                    kill_stream()
                    start()
        elif text == 'запрос на английском':
            stream.stop_stream()
            print('Начинаю запрос')
            playsound('config_files/jarvis_speech/ok.wav')
            rec = KaldiRecognizer(model, 16000)
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
            stream.start_stream()
            for text in listen():
                module = importlib.import_module(f"modules.Search.__main__")
                if hasattr(module, 'run'):
                    stream.stop_stream()
                    print(text)
                    module.run(text)
                    kill_stream()
                    start()
        else:
            playsound("config_files/jarvis_speech/what.wav")
            stream.stop_stream()
            start()

def wake_word_callback():
    #print("Wake word detected!")
    print("Команда распознана")
    global stream, p
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    speak = ['config_files/jarvis_speech/eat.wav', 'config_files/jarvis_speech/ok.wav', 'config_files/jarvis_speech/ok2.wav']

    random_number = random.randint(0, 2)

    playsound(speak[random_number])

    wake_word_vosk()

#Обязательная функция не удалять
def inference_callback(inference):
    pass

def start():
    global stream, p

    with open("key.txt", "r") as f:
        key = f.read()

    try:
        picovoice = Picovoice(
            access_key=key,
            keyword_path="config_files/jarvis_w.ppn",
            wake_word_callback=wake_word_callback,
            context_path="config_files/cont.rhn",
            inference_callback=inference_callback,
        )
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)

        print("Слушаю...")

        while True:
            # Чтение следующего аудиофрейма из микрофона
            audio_frame = stream.read(512)
            audio_frame = np.frombuffer(audio_frame, dtype=np.int16) 
            picovoice.process(audio_frame)

    except PicovoiceError as e:
        print(f"Picovoice Error: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'stream' in globals() and stream is not None:
            stream.stop_stream()
            stream.close()
        if 'p' in globals() and p is not None:
            p.terminate()

if __name__ == '__main__':
    start()
