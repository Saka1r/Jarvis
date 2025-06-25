def run():
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from playsound import playsound
    import random
        # Получаем аудио устройство по умолчанию
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_,
        CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    current_volume = volume.GetMasterVolumeLevelScalar()

    # Увеличиваем громкость на 10%
    new_volume = min(current_volume + 0.2, 1.0)
    volume.SetMasterVolumeLevelScalar(new_volume, None)
    
    speak = ['config_files/jarvis_speech/eat.wav', 'config_files/jarvis_speech/ok.wav', 'config_files/jarvis_speech/ok2.wav']

    random_number = random.randint(0, 2)

    print(random_number)

    playsound(speak[random_number])
    print(f"Громкость увеличена до {new_volume * 100:.1f}%")