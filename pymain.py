from ui.qt import pyelement, pywindow, pylauncher
import sys

resolution = 225, 325
process_command = pylauncher.process_command

class PySplashWindow(pywindow.RootPyWindow):
    def __init__(self):
        pywindow.RootPyWindow.__init__(self)
        self._cfg = None

        self.title = "Initializing PyPlayer"
        self.icon = "assets/icon.png"
        self.layout.row(1, weight=1)

        self.make_borderless()
        self.center_window(*resolution, fit_to_size=True)
        self.schedule_task(sec=1, func=self._load_program)

    def create_widgets(self):
        pywindow.RootPyWindow.create_widgets(self)
        self.add_element("header", element_class=pyelement.PyTextLabel, row=0, column=0)
        btn = self.add_element("close_btn", element_class=pyelement.PyButton, row=0, column=1)
        btn.width, btn.text = 30, "X"
        @btn.events.EventInteract
        def _on_click(): self.destroy()
        logo = self.add_element("logo_img", element_class=pyelement.PyTextLabel, row=1, columnspan=2)
        logo.display_image = "assets/logo.png"
        status_bar = self.add_element("status_bar", element_class=pyelement.PyTextLabel, row=2, columnspan=2)
        status_bar.set_alignment("center")
        status_bar.text, status_bar.wrapping = "Initializing...", True

    def _load_program(self):
        from pyplayerqt import PyPlayer
        client = self.add_window("client", window_class=PyPlayer)

        client.hidden = False
        self.hidden = True
        @client.events.EventWindowDestroy
        def _on_close(): self.schedule_task(sec=1, func=self.destroy)

if __name__ == "__main__":
    PySplashWindow().start()