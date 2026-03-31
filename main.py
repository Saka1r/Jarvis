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
