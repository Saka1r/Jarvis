from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Line
from kivy.utils import get_color_from_hex

class Error_win():
    def open(message):
        box = BoxLayout(orientation="vertical")
        error_text = Label(text=message)
        box.add_widget(error_text)

        win = Popup(title="Ошибка", size_hint=(0.8, 0.7), auto_dismiss=True, content=box)
        win.open()

class Custom_button(Button):
    """Class for custom button"""
    def __init__(self, **kwargs):
        super(Custom_button, self).__init__(**kwargs)
        """draws a rectangle near the button"""
        with self.canvas.before:
            color = get_color_from_hex('#007bff')
            Color(*color)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=2)

        self.bind(pos=self.update_rect, size=self.update_rect)
    def update_rect(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

class Custom_textinput(TextInput):
    """draws a rectangle near the textinput"""
    def __init__(self, **kwargs):
        super(Custom_textinput, self).__init__(**kwargs)
        with self.canvas.before:
            color = get_color_from_hex('#007bff')
            Color(*color)
            self.border_line = Line(rectangle=(self.x, self.y, self.width, self.height), width=2)

        self.bind(pos=self.update_rect, size=self.update_rect)
    def update_rect(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)