def run():
    import pyautogui
    import time

    time.sleep(1)

    from playsound import playsound
    
    speak = 'config_files/jarvis_speech/eat.wav'

    playsound(speak)

    pyautogui.hotkey('win', 'd')
