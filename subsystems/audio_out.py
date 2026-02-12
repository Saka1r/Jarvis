#subsystem/audio_out.py

import playsound

class AudioOut():

    def __init__(self):
        pass

    def play(self, text):
       if text == 'джарвис':
            print("yes sir")
            playsound.playsound("data/jarvis_wav/yes_sir.wav")
