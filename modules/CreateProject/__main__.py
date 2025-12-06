def run():
    from vosk import Model, KaldiRecognizer
    from playsound import playsound
    import json 
    import pyaudio


    playsound("config_files/jarvis_speech/project.wav")

    model = Model('config_files/vosk_en')

    rec = KaldiRecognizer(model, 16000)
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

            data = stream.read(4000, exception_on_overflow=False)

            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = rec.Result()
                result_json = json.loads(result)
                if result_json.get("text"):  # Проверяем наличие текста
                    yield result_json["text"]

    for text in listen():
        print(text)
        