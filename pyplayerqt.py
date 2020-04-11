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
        self.layout.row(2, minsize=100, weight=1)

        self.title = "PyPlayer"
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

        console: PyConsole = self.add_element("console", element_class=PyConsole, row=2, columnspan=3)
        console.text = "bummer"

    def update_title(self, title): self.title = title
    def update_title_media(self, title): self.update_title(title)