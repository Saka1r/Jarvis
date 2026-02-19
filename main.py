# main.py

# author Sakair/Svyatoslav
# """--------------------------------------------------------------------------"""
#        __       ___      .______     ____    ____  __       _______.
#       |  |     /   \     |   _  \    \   \  /   / |  |     /       |
#       |  |    /  ^  \    |  |_)  |    \   \/   /  |  |    |   (----`
# .--.  |  |   /  /_\  \   |      /      \      /   |  |     \   \
# |  `--'  |  /  _____  \  |  |\  \----.  \    /    |  | .----)   |
#  \______/  /__/     \__\ | _| `._____|   \__/     |__| |_______/
#
# """--------------------------------------------------------------------------"""

from core.jarvis import Jarvis

from config import Config

from threading import Thread

config_ = Config()

if __name__ == '__main__':
    config_.start() 
    thread_jarvis = Thread(target=Jarvis.start())
       
else:
    print("This is not a module")
