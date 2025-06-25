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

from kivy.app import App

from kivy.lang.builder import Builder
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

from kivy.animation import Animation
from kivy.clock import Clock
from FileManager import File_Manager
from custom_widget import Custom_button
from custom_widget import Custom_textinput
from custom_widget import Error_win

import speech
import threading
import module

Window.size = (1080/3, 1920/3)

class Jarvis(App):
    """Main class for kivy app"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.heart_active = None
        self.speech_thread = None

    def build(self):
        self.title = "J.A.R.V.I.S"
        Window.clearcolor = get_color_from_hex('#04060f')
        return Builder.load_file('style.kv')

    def on_start(self):
        self.create_to_list("Обратно", self.screen, "main")
        self.create_to_list("Модули", self.screen, "config")

    def screen(self, screen_name):
        """Function of moving between a screens"""
        self.root.current = screen_name
        print(screen_name)
    def run_speech(self):

        speech.stop_stream()

        speech.start()

        self.stop_animation()

    def jarvis_start(self):

        speech.stop_stream()

        if self.heart_active is None:
            animation = Animation(size=(600, 600), duration=0.5) + Animation(size=(500, 500), duration=0.8)
            animation.repeat = True  # Повторять анимацию
            animation.start(self.root.ids.jarvis_heart)
            print(self.root.ids.jarvis_heart)
            self.heart_active = animation

            thread = threading.Thread(target=self.run_speech)
            thread.start()
        else:
            print(self.heart_active)
            self.heart_active.stop(self.root.ids.jarvis_heart)
            self.root.ids.jarvis_heart.size = (500, 500)
            print("Good ;3")
            self.heart_active = None

    def module_install(self):
        def on_file_selected(path_to_file):
            file = path_to_file.split("\\")
            file = file[-1].split(".")
            if file[-1] == "zip":
                module.install_module(path_to_zip=path_to_file)
            else:
                Error_win.open("Файл не является zip")


        file_manager = File_Manager(on_select=on_file_selected)

    def stop_animation(self):
        # для выполнение в основном потоке
        Clock.schedule_once(self.end_animation)

    def end_animation(self, dt):
        if self.heart_active is not None:
            self.heart_active.stop(self.root.ids.jarvis_heart)
            self.root.ids.jarvis_heart.size = (500, 500)
            print("Animation stopped ;3")
            self.heart_active = None
    def create_to_list(self, text, function, arg):
        button = Custom_button(text=text, size_hint_y=None, height=150)
        button.bind(on_release=lambda x: function(arg))
        self.root.ids.list_button.add_widget(button)

if __name__ == '__main__':
    Jarvis().run()
