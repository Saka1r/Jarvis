<p align="center">
   <img src="https://img.shields.io/badge/build-XD-brightgreen?style=flat&logo=logo&logoColor=%237516a1&label=J.A.R.V.I.S&labelColor=%23c20232&color=%234202c2" alt="Jarvis">
</p>

## Subsytems

## Подсистемы

Каталог в subsystems лежат подсистемы Джарвиса. Например подсистема audio_in.py служит для чтения данных с устройством ввода. Разберем подсистемы.

В audio.py всего 3 метода: open(), read(), close().

```python 
def open(self):
        '''Открывает аудио поток true/false'''
        with self._lock:
            if self.is_streaming:
                return True

            try:
                self._pyaudio = pyaudio.PyAudio()
                self.stream = self._pyaudio.open(format=self.format, channels=self.channels, rate=self.rate, input=True, frames_per_buffer=self.frames_per_buffer)
                self.is_streaming = True
                return True

            except Exception:
                logger.exception("Error: subsystem/audio_in.py [open] -> Failed to open audio stream")
                self.close()
                return False
```


```python
def read(self, num_frames=None):
        '''Читает данные из аудио потока, возрашает данные'''
        with self._lock:
            if not self.is_streaming or self.stream is None:
                raise RuntimeError("Error: subsystem/audio_in.py [read] -> Stream is not open")
            n = num_frames or self.frames_per_buffer
            return self.stream.read(n, exception_on_overflow=False)
```

```python
def close(self):
        '''Закрывает поток'''
        with self._lock:
            if self.stream is not None:
                try:
                    self.stream.stop_stream()
                    self.stream.close()

                except Exception:
                    logger.exception("Error: subsystem/audio_in.py [close] -> Failed to close audio stream")

                finally:
                    self.stream = None
```

В audio_out подсистемы всего один метод play(), который принимает аргумент в виде пути до файлы, который следует воспроизвести.

sst.py формально является подсистемой, но он играет в роли абстрактного класса для дочерних подсистем. Например vost_stt.py - дочерняя подсистема

В vosk_stt.py есть 5 методов, из названия можно понять, что они делают. load_commands(), open(), close(), accept_audio(), get_result()

load_commands() - загружает trigers (голосовые команды) из всех плагинов в self.commands

open() - загружает vosk модель 
```python
self.model = Model(self.model_path)
```
Иницилизирует KaldiRecognizer

close() - выгружает модель

accept_audio
```python
def accept_audio(self, audio_bytes: bytes) -> None:
        if self.recognizer is None:
            raise RuntimeError("Error: subsystems/vosk_stt.py [accept_audio] -> Recognizer not opened")

        if self.recognizer.AcceptWaveform(audio_bytes):
            partial_result = json.loads(self.recognizer.Result())
            new_text = partial_result.get("text", "")
            
            # Накапливаем текст с пробелом
            if new_text:
                self.accumulated_text += new_text + " " 
                return self.accumulated_text
```

