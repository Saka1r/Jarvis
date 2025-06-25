from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label

from custom_widget import Custom_button
from custom_widget import Error_win

from functools import partial
import os

BUTTON_COLOR = (0, 0.031, 0.514, 1)

class File_Manager(BoxLayout):
    def __init__(self, on_select=None, **kwargs):
        super().__init__(**kwargs)

        self.on_select = on_select

        self.current_path = os.getcwd()

        self.path_to_file = None
        self.list_files = None
        self.button_widget = None
        self.button_back = None
        self.button_dot = None
        self.button_list = []

        self.list_widget_scroll = ScrollView()
        self.list_widget_grid = GridLayout(cols=1, size_hint_y=None)
        self.list_widget_scroll.add_widget(self.list_widget_grid)

        # Высота для GridLayout в зависимости от количества файлов
        self.list_widget_grid.bind(minimum_height=self.list_widget_grid.setter('height'))

        self.file_manager_screen = ModalView(auto_dismiss=True, size_hint=(0.9, 0.9), background_color=(0, 0, 0, 0))
        self.file_manager_screen.open()

        self.box_file = BoxLayout(orientation='vertical')
        self.box_file.add_widget(self.list_widget_scroll)
        self.file_manager_screen.add_widget(self.box_file)

        self.button_back = Custom_button(text="Выйти", background_color=BUTTON_COLOR, size_hint_y=None, height=50)
        self.button_back.bind(on_release=lambda x: self.close_FileManager())
        self.list_widget_grid.add_widget(self.button_back)

        self.button_dot = Custom_button(text="..", background_color=BUTTON_COLOR, size_hint_y=None, height=50)
        self.button_dot.bind(on_release=lambda x: self.go_up())
        self.list_widget_grid.add_widget(self.button_dot)

        self.list()

    def close_FileManager(self):
        self.file_manager_screen.dismiss()

    @staticmethod
    def error_win(message):
        Error_win.open(message)

    def update_file_view(self):
        self.clear_widgets_list()
        self.list()

    def clear_widgets_list(self):
        for widget in list(self.list_widget_grid.children):
            if widget not in [self.button_back, self.button_dot]:
                self.list_widget_grid.remove_widget(widget)
    def go_up(self):
        print("go up:\n", self.current_path)
        try:
            os.chdir("..")
            self.current_path = os.getcwd()
            print(self.current_path)
            self.update_file_view()
        except Exception as e:
            self.error_win(f"ошибка перехода {self.current_path}")

    def open_file(self, Path_to_file):
        print(f"Open {Path_to_file}")
        self.path_to_file = Path_to_file
        self.close_FileManager()
        if self.on_select:
            self.on_select(self.path_to_file)
        
    def widget_open(self, name, *args):
        current_path_new = os.path.join(self.current_path, name)
        print("widget_open: \n", current_path_new)
        if os.path.isdir(current_path_new):
            self.current_path = current_path_new
            os.chdir(self.current_path)
            print(self.current_path)
            self.update_file_view()
        else:
            print(f"Path {current_path_new} is not a directory")
            self.open_file(current_path_new)

    def list(self):
        self.clear_widgets_list()
        self.list_files = os.listdir(self.current_path)
        try:
            for i in self.list_files:
                self.button_widget = Custom_button(text=f'{i}', background_color=BUTTON_COLOR, size_hint_y=None, height=50)
                self.button_widget.bind(on_release=partial(self.widget_open, i))
                self.list_widget_grid.add_widget(self.button_widget)
                self.button_list.append(self.button_widget)
            # print(self.button_list)
        except Exception as e:
            print(f"Error file list: {e}")
            self.error_win("Ошибка при списке файлов")

if __name__ == '__main__':
    class MyApp(App):
        def build(self):
            file_managet = File_Manager()
            return file_managet
    MyApp().run()