def run():
    import os

    from playsound import playsound
    
    speak = 'config_files/jarvis_speech/ok2.wav'
    
    playsound(speak)
    
    os.startfile("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")