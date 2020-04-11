from ui.qt import pywindow, pyelement

import enum
class PyPlayerCloseReason(enum.Enum):
    NONE = 0,
    RESTART = 1,
    MODULE_CONFIGURE = 2

class PyConsole(pyelement.PyTextField):
    pass

class PyPlayer(pywindow.PyWindow):
    def __init__(self, root):
        pywindow.PyWindow.__init__(self, root)
        self.layout.column(1, minsize=30, weight=1)
        self.layout.row(3, minsize=100, weight=1)

        self.title = "PyPlayer"
        self._title_song = ""
        self.icon = "assets/icon.png"

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        header_left: pyelement.PyTextLabel = self.add_element("header_left", element_class=pyelement.PyTextLabel, row=0, column=0)
        header_center: pyelement.PyTextLabel = self.add_element("header_center", element_class=pyelement.PyTextLabel, row=0, column=1)
        header_right: pyelement.PyTextLabel = self.add_element("header_right", element_class=pyelement.PyTextLabel, row=0, column=2)

        header_left.text = "left"
        header_center.text = "center"
        header_center.set_alignment("center")
        header_right.text = "right"

        progressbar: pyelement.PyProgessbar = self.add_element("progress_bar", element_class=pyelement.PyProgessbar, row=1, columnspan=3)
        progressbar.minimum, progressbar.maximum = 0, 100

        console = self.add_element("console", element_class=PyConsole, row=3, columnspan=3)
        console.accept_input = False
        console.text = "Hello there"
        input: pyelement.PyTextInput = self.add_element("console_input", element_class=pyelement.PyTextInput, row=4, columnspan=3)
        @input.events.EventInteract
        def _on_input_enter():
            console.text += "\n" + input.value
            input.value = ""

    def update_title(self, title, checks=None):
        prefix = " ".join(f"[{c}]" for c in (checks if checks is not None else []))
        self._title_song = title
        self.title = prefix + " " + title

    def update_title_media(self, media_data):
        self.update_title(media_data.display_name)
        self["progress_bar"].progress = 0