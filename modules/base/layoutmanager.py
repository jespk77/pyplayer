from collections import namedtuple
LayoutData = namedtuple("LayoutData", ["x", "y", "width", "height", "state"], defaults=[0])

from core import modules
module = modules.Module(__package__)

from ui.qt import pywindow

class LayoutManager:
    @staticmethod
    def from_string(value : str): return LayoutData(*value.split(","))
    @staticmethod
    def to_string(layout : LayoutData): return f"{layout.x},{layout.y},{layout.width},{layout.height},{layout.state}"

    def __init__(self):
        try: self._layouts = {key : LayoutManager.from_string(value) for key, value in module.configuration.get_or_create("layout", {}).items()}
        except Exception as ex:
            print("ERROR", "Failed to load layouts:", ex)
            self._layouts = {}

    def save(self):
        module.configuration["layout"] = {key: LayoutManager.to_string(value) for key, value in self._layouts.items()}
        module.configuration.save()

    @property
    def layouts(self): return self._layouts.keys()

    def has_layout(self, layout_name : str):
        return layout_name in self._layouts

    def get_layout(self, layout_name : str, default_value=None):
        return self._layouts.get(layout_name, default_value)

    def set_layout(self, layout_name : str, layout : LayoutData, autosave=True):
        self._layouts[layout_name] = layout
        if autosave: self.save()

    def delete_layout(self, layout_name : str, autosave=True):
        try:
            del self._layouts[layout_name]
            if autosave: self.save()
        except KeyError: pass

    def set_layout_on_window(self, layout_name : str, window : pywindow.PyWindow):
        layout = self.get_layout(layout_name)
        if layout is None:
            print("INFO", f"No layout stored with name '{layout_name}': skipping layout update")
            return False

        window.set_geometry(int(layout.x), int(layout.y), int(layout.width), int(layout.height))
        try: state = int(layout.state)
        except ValueError: state = 0
        if state == 2: window.maximized = True
        elif state == 1: window.minimized = True
        else: window.maximized = window.minimized = False
        return True

    def save_layout_from_window(self, layout_name : str, window : pywindow.PyWindow, autosave=True):
        window_state = 2 if window.maximized else 1 if window.minimized else 0
        self.set_layout(layout_name, LayoutData(window.x, window.y, window.width, window.height, window_state), autosave)
