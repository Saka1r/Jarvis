def run():
    import webbrowser
    from playsound import playsound
    import random
    url = 'https://www.youtube.com/watch?v=pAgnJDJN4VA&list=PLpZaq7kciiNIscD5bMLUIyesR_EHTSvxu&ab_channel=acdcVEVO'

    speak = ['config_files/jarvis_speech/eat.wav', 'config_files/jarvis_speech/ok.wav', 'config_files/jarvis_speech/ok2.wav']

    random_number = random.randint(0, 2)

    #print(random_number)

    playsound(speak[random_number])
    webbrowser.open_new_tab(url)