def run():
    import os

    from playsound import playsound
    import random
    
    speak = ['config_files/jarvis_speech/eat.wav', 'config_files/jarvis_speech/ok.wav', 'config_files/jarvis_speech/ok2.wav']

    random_number = random.randint(0, 2)

    playsound(speak[random_number])

    os.startfile("D:/VS Code\Microsoft VS Code/Code.exe")