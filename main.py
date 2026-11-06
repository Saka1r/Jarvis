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

logger = logging.getLogger(__name__)

import asyncio

from core.jarvis import Jarvis

from config import Config

async def main():
    config = Config() 
    config.start()

    max_retries = 3
    for attempt in range(max_retries):
        try:
            await Jarvis.start()
            break
        except FileNotFoundError as e:
            logger.error(f"Missing file {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 5 seconds...")
                await asyncio.sleep(5)
            else:
                raise
        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break

if __name__ == "__main__":
    asyncio.run(main())
else:
    print("This is not a module")
