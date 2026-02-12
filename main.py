# main.py

from core.jarvis import Jarvis

from config import Config

from threading import Thread

config_ = Config()

if __name__ == '__main__':
    config_.start() 
    thread_jarvis = Thread(target=Jarvis.start())
       
else:
    print("This is not a module")
