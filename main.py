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

import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,  # Показываем всё, включая отладку аудио
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
# Для отладки Vosk включим логи самой библиотеки
logging.getLogger("vosk").setLevel(logging.DEBUG)

import asyncio

from core.jarvis import Jarvis

from config import Config

async def main():
    config_ = Config()
    
    config_.start() 
    
    try:
        await Jarvis.start()
    except KeyboardInterrupt:
        print("\nJarvis stopped by user.")

if __name__ == "__main__":
    asyncio.run(main())
else:
    print("This is not a module")
