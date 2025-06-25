def run():
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        # Получаем аудио устройство по умолчанию
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_,
        CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    current_volume = volume.GetMasterVolumeLevelScalar()

    # выключить звук
    new_volume = volume.SetMasterVolumeLevelScalar(0.0, None)

    print(f"Громкость увеличена до {new_volume * 100:.1f}%")