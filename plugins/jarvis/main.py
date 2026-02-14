def run():
    
    from subsystems.audio_out import AudioOut
    import random

    audio = AudioOut()

    file = ["data/jarvis_wav/at_you_service.wav", "data/jarvis_wav/at_you_service_2.wav", "data/jarvis_wav/yes_sir.wav", "data/jarvis_wav/listening.wav"]

    int_ = random.randint(0,3)

    audio.play(file[int_])
