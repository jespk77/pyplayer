from ui.qt import pywindow, pyelement
from utilities.history import History
from interpreter import Interpreter

import enum
class PyPlayerCloseReason(enum.Enum):
    NONE = 0,
    RESTART = 1,
    MODULE_CONFIGURE = 2

class PyPlayer(pywindow.PyWindow):
    def __init__(self, root, window_id):
        pywindow.PyWindow.__init__(self, root, window_id)
        self.layout.column(1, minsize=30, weight=1).row(3, minsize=100, weight=1)

        self.title = "PyPlayerQt"
        self._title_song = ""
        self.icon = "assets/icon.png"
        self.flags = PyPlayerCloseReason.NONE

        self._command_history = History()
        self._interp = None
        self._cmd = None
        self.schedule_task(func=self._insert_reply, task_id="reply_task", reply="= Hello there =")
        self.add_task(task_id="shutdown", func=self.destroy)
        @self.events.EventWindowClose
        def _on_close(): self.stop_interpreter()

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        header_left = self.add_element("header_left", element_class=pyelement.PyTextLabel, row=0, column=0)
        header_center = self.add_element("header_center", element_class=pyelement.PyTextLabel, row=0, column=1)
        header_right = self.add_element("header_right", element_class=pyelement.PyTextLabel, row=0, column=2)

        header_left.text = "left"
        header_center.text = "center"
        header_center.set_alignment("centerH")
        header_right.text = "right"

        console = self.add_element("console", element_class=pyelement.PyTextField, row=3, columnspan=3)
        console.accept_input = False


        inpt: pyelement.PyTextInput = pyelement.PyTextInput(self, "console_input", True)
        self.add_element(element=inpt, row=4, columnspan=3)
        @inpt.events.EventInteract
        def _on_input_enter():
            self._on_command_enter(inpt.value)
            inpt.value = ""

        @inpt.events.EventHistory
        def _set_history(direction):
            if direction > 0: inpt.value = self._command_history.get_next("")
            elif direction < 0:
                hist = self._command_history.get_previous()
                if hist is not None: inpt.value = hist
            return inpt.events.block_action

        @console.events.EventKeyDown("all")
        def _on_key_down(key, modifiers):
            try:
                key = chr(key)
                if "shift" not in modifiers: key = key.lower()
                inpt.get_focus()
                inpt.text += key
            except ValueError: pass

    def start_interpreter(self, module_cfg):
        self._interp = Interpreter(self, module_cfg)

    def stop_interpreter(self):
        if self._interp:
            self._interp.stop()
            self._interp = None

    def close_with_reason(self, reason):
        try:
            self.flags = PyPlayerCloseReason[reason.upper()]
            print("INFO", "Closing application with reason", self.flags)
            return self.schedule_task(sec=1, task_id="shutdown")
        except KeyError: pass
        raise ValueError(f"Unknown reason '{reason}'")

    def _on_command_enter(self, cmd):
        if cmd:
            self["console"].text += f"{cmd}\n"
            self._command_history.add(cmd)
            self["console_input"].accept_input = False
            self._interp.put_command(cmd)

    def _insert_reply(self, reply, tags=None, prefix=None, text=None):
        if not prefix: prefix = "> "
        self["console"].text += f"{reply}\n{prefix}"
        self["console_input"].accept_input = True

    def on_reply(self, reply, tags=None, cmd=None, prefix='', text=''):
        self._cmd = cmd
        if not self["console_input"].accept_input:
            self.schedule_task(task_id="reply_task", reply=reply, tags=tags, prefix=prefix, text=text)

    def on_notification(self, message, tags=None):
        self.schedule_task(task_id="reply_task", reply=message, tags=tags)

    def update_title(self, title, checks=None):
        if not title: title = self.title
        prefix = " ".join(f"[{c}]" for c in (checks if checks is not None else []))
        self._title_song = title
        self.title = prefix + " " + title

    def update_title_media(self, media_data):
        self.update_title(media_data.display_name)
        self["progress_bar"].progress = 0