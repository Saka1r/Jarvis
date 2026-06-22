# plugins/jarvis/main.py

'''Standart commands for Jarvis'''

import random
import os
import webbrowser
import psutil

from core.base_plugin import BasePlugin

if os.name == 'nt':
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class JarvisPlugin(BasePlugin):
    
    def greet(self) -> None:
        """Просто играет WAV. Озвучки текста нет → возвращаем None."""
        files = [
            "data/jarvis_wav/at_you_service.wav",
            "data/jarvis_wav/at_you_service_2.wav",
            "data/jarvis_wav/yes_sir.wav"
        ]
        self.audio_out.play(random.choice(files))
        return None  # ← ничего озвучивать не нужно

    def browser(self) -> None:
        self.greet()
        webbrowser.open("https://www.google.com")
        return None

    def youtube(self) -> None:
        self.greet()
        webbrowser.open("https://www.youtube.com/?app=desktop&hl=ru")
        return None

    def music(self) -> None:
        self.greet()
        webbrowser.open("https://www.youtube.com/watch?v=pAgnJDJN4VA&list=RDpAgnJDJN4VA&start_radio=1")
        return None

    def goWork(self) -> None:
        self.greet()
        os.startfile(r"D:\VS Code\Microsoft VS Code\Code.exe")
        return None

    def _get_volume_interface(self):
        if os.name != 'nt':
            return None
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))

    def soundDown(self) -> str:
        self.greet()
        volume = self._get_volume_interface()
        if volume:
            current = volume.GetMasterVolumeLevelScalar()
            new_volume = max(current - 0.2, 0.0)
            volume.SetMasterVolumeLevelScalar(new_volume, None)
            return f"Громкость уменьшена до {new_volume * 100:.0f} процентов."
        return None

    def soundUp(self) -> str:
        self.greet()
        volume = self._get_volume_interface()
        if volume:
            current = volume.GetMasterVolumeLevelScalar()
            new_volume = min(current + 0.2, 1.0)
            volume.SetMasterVolumeLevelScalar(new_volume, None)
            return f"Громкость увеличена до {new_volume * 100:.0f} процентов."
        return None

    def soundOff(self) -> str:
        self.greet()
        volume = self._get_volume_interface()
        if volume:
            volume.SetMasterVolumeLevelScalar(0.0, None)
            return "Звук выключен."
        return None

    def get_system_status(self) -> str:
        """Возвращает строку — Jarvis сам её озвучит через TTS."""
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_gb = ram.used / (1024 ** 3)
        self.systems["tts"].queue.put_nowait(f"Процессор загружен на {cpu} процентов. Использовано {ram_gb:.1f} гигабайт оперативной памяти.")
        #return f"Процессор загружен на {cpu} процентов. Использовано {ram_gb:.1f} гигабайт оперативной памяти."