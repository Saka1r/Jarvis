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

def stop_stream():
    global stream, is_stream_open
    with lock:
        if is_stream_open and stream is not None:
            stream.stop_stream()
            stream.close()
            is_stream_open = False
            print("Stream stopped.")

def wake_word_vosk():
    global word_detect, is_stream_open
    timed1 = time.time()

    model = Model('config_files/small_model')
    rec = KaldiRecognizer(model, 16000)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
    stream.start_stream()
    is_stream_open = True

    def listen():
        while True:
            with lock:  # Защита доступа к потоку
                if not is_stream_open:
                    break  

            timed2 = time.time()
            data = stream.read(4000, exception_on_overflow=False)

            if (rec.AcceptWaveform(data)) and (len(data) > 0):
                answer = json.loads(rec.Result())
                if answer['text']:
                    yield answer['text']
            if word_detect == False:
                print(timed2 - timed1)
                if timed2 - timed1 >= 10:
                    stop_stream()

    for text in listen():
        print(text)
        word_detect = True
        config = read_module()
        if text in config["Commands"]:
            folder_name = config["Commands"][text]
            try:
                module = importlib.import_module(f"modules.{folder_name}.__main__")
                if hasattr(module, 'run'):
                    module.run()
                else:
                    print(f"В модуле {folder_name} не найдена функция run()")
            except ModuleNotFoundError as e:
                print(f"Ошибка при импорте модуля: {e}")

        elif text == 'пока пока':
            stop_stream()
            speak = 'config_files/jarvis_speech/bye.wav'
            playsound(speak)

def wake_word_callback():
    print("Wake word detected!")
    global stream, p
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    speak = ['config_files/jarvis_speech/eat.wav', 'config_files/jarvis_speech/ok.wav', 'config_files/jarvis_speech/ok2.wav']

    random_number = random.randint(0, 2)

    print(random_number)

    playsound(speak[random_number])

    wake_word_vosk()

#Обязательная функция не удалять
def inference_callback(inference):
    pass

def start():
    global stream, p
    try:
        picovoice = Picovoice(
            access_key="YOUR_KEY",
            keyword_path="config_files/jarvis_w.ppn",
            wake_word_callback=wake_word_callback,
            context_path="config_files/cont.rhn",
            inference_callback=inference_callback,
        )
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)
        
        print("Listening...")

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