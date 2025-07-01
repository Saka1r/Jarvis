def run():
    import webbrowser
    from playsound import playsound
    import random
    url = 'https://web.telegram.org/k/'

    speak = ['config_files/jarvis_speech/eat.wav', 'config_files/jarvis_speech/ok.wav', 'config_files/jarvis_speech/ok2.wav']

    random_number = random.randint(0, 2)

    print(random_number)

    playsound(speak[random_number])
    webbrowser.open_new_tab(url)