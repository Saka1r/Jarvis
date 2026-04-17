import random
import os
import webbrowser

from subsystems.audio_out import AudioOut

if os.name == 'nt':
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class JarvisPlugin:
    def greet(self):
        audio_out_ = AudioOut()

        file = [
            "data/jarvis_wav/at_you_service.wav",
            "data/jarvis_wav/at_you_service_2.wav",
            "data/jarvis_wav/yes_sir.wav"
        ]

        int_ = random.randint(0, 2)

        audio_out_.play(file[int_])
        
    def browser(self):
        self.greet()
        webbrowser.open("www.google.com")
    
    def youtube(self):
        self.greet()
        webbrowser.open("https://www.youtube.com/?app=desktop&hl=ru")

    def music(self):
        self.greet()
        webbrowser.open("https://www.youtube.com/watch?v=pAgnJDJN4VA&list=RDpAgnJDJN4VA&start_radio=1")

    def goWork(self):
        self.greet()
        os.startfile("D:/VS Code\Microsoft VS Code/Code.exe")

    def soundDown(self):
        if os.name == 'nt':
            self.greet()
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_,
                CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))

            current_volume = volume.GetMasterVolumeLevelScalar()

            # Увеличиваем громкость на 10%
            new_volume = max(current_volume - 0.2, 0.0)
            volume.SetMasterVolumeLevelScalar(new_volume, None)

            print(f"Громкость уменьшена до {new_volume * 100:.1f}%")

    def soundOff(self):
        if os.name == 'nt':
            self.greet()
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_,
                CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))

            current_volume = volume.GetMasterVolumeLevelScalar()

            # выключить звук
            new_volume = volume.SetMasterVolumeLevelScalar(0.0, None)

            print(f"Громкость увеличена до {new_volume * 100:.1f}%")


    def soundUp(self):
        if os.name == 'nt':
            self.greet()
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_,
                CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))

            current_volume = volume.GetMasterVolumeLevelScalar()

            # Увеличиваем громкость на 10%
            new_volume = min(current_volume + 0.2, 1.0)
            volume.SetMasterVolumeLevelScalar(new_volume, None)
            
            print(f"Громкость увеличена до {new_volume * 100:.1f}%")