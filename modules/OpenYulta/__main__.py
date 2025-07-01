def run():
    import os
    import random
    from playsound import playsound

    speak = ['config_files/jarvis_speech/eat.wav', 'config_files/jarvis_speech/ok.wav', 'config_files/jarvis_speech/ok2.wav']

    random_number = random.randint(0, 2)

    print(random_number)

    playsound(speak[random_number])
    os.startfile(r'C:\Users\Sakair\AppData\Roaming\ulta-loader\ulta-loader.exe')