#subsystem/audio_out.py

import playsound

class AudioOut():

    def __init__(self):
        pass

    def play(self, file): 
        playsound.playsound(file)
