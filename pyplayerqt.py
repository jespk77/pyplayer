from ui.qt import pywindow, pyelement
from core.history import History
from core.interpreter import Interpreter

import enum, datetime
class PyPlayerCloseReason(enum.Enum):
    NONE = 0,
    RESTART = 1,
    MODULE_CONFIGURE = 2

initial_cfg = { "header_format": "PyPlayer - %a %b %d, %Y %I:%M %p -", "loglevel": "info" }
class PyPlayer(pywindow.PyWindow):
    autocomplete_task = "autocomplete_task"

    def __init__(self, root, window_id):
        pywindow.PyWindow.__init__(self, root, window_id)
        self.layout.column(1, minsize=30, weight=1).row(3, minsize=100, weight=1)

        self.title = "PyPlayer"
        self.title_song = ""
        self.icon = "assets/icon.png"
        self.flags = PyPlayerCloseReason.NONE
        self.configuration.set_defaults(initial_cfg)

        self._command_history = History()
        self._interp = self._cmd = None
        self._left_head_update = self._right_head_update = None

        self.schedule_task(func=self._insert_reply, task_id="reply_task", reply="= Hello there =")
        self.schedule_task(sec=1, loop=True, func=self._window_tick, task_id="window_tick")
        self.add_task(task_id="shutdown", func=self.destroy)
        self.add_task(task_id=self.autocomplete_task, func=self._insert_autocomplete)

        import pylogging
        pylogging.get_logger().log_level = self.configuration["loglevel"]
        self._window_tick()

        @self.events.EventWindowOpen
        def _on_open(): self.parent.hidden = True
        @self.events.EventWindowDestroy
        def _on_close():
            self.stop_interpreter()
            self.parent.on_close(self)

        self.start_interpreter()

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        self.add_element("header_left", element_class=pyelement.PyTextLabel, row=0, column=0)
        header_center = self.add_element("header_center", element_class=pyelement.PyTextLabel, row=0, column=1)
        self.add_element("header_right", element_class=pyelement.PyTextLabel, row=0, column=2)
        header_center.text = "PyPlayer"
        header_center.set_alignment("centerH")

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

        @inpt.events.EventKeyDown("Escape")
        def _clear_input():
            inpt.value = ""
            return inpt.events.block_action

        @inpt.events.EventKeyDown("Tab")
        def _try_autocomplete():
            txt = inpt.value
            if txt:
                print("trying to autocomplete:", txt)
                inpt.accept_input = False
                self._interp.request_autocomplete(inpt.value)
                return inpt.events.block_action

        @console.events.EventFocusGet
        def _on_focus(): inpt.get_focus()

    def start_interpreter(self):
        self._interp = Interpreter(self)
        self._interp.start()

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
            self._interp.put_command(cmd, self._cmd)

    def _insert_reply(self, reply, tags=None, prefix=None, text=None):
        if not prefix: prefix = "> "
        console = self["console"]
        console.insert(console.end, f"{reply}\n{prefix}")
        console.show(console.end)

        console_input = self["console_input"]
        console_input.accept_input = True
        if text: console_input.text = text
        console_input.get_focus()

    def _insert_autocomplete(self, suggestions):
        inpt = self["console_input"]
        inpt.accept_input = True

        if len(suggestions) > 0:
            cmd = suggestions[0]
            inpt.value = cmd.command + " "
            if cmd.remainder: inpt.value += cmd.remainder
        inpt.get_focus()

    def _window_tick(self):
        date = datetime.datetime.today()
        self["header_center"].text = date.strftime(self.configuration["header_format"])
        if self._left_head_update: self._left_head_update(date)
        if self._right_head_update: self._right_head_update(date)

    def update_left_header(self, cb): self._left_head_update = cb
    def update_right_header(self, cb): self._right_head_update = cb

    def on_reply(self, reply, tags=None, cmd=None, prefix='', text=''):
        self._cmd = cmd
        if not self["console_input"].accept_input:
            self.schedule_task(task_id="reply_task", reply=reply, tags=tags, prefix=prefix, text=text)

    def on_notification(self, message, tags=None):
        self.schedule_task(task_id="reply_task", reply=message, tags=tags)

    def update_title(self, title):
        if not title: title = self.title
        self.title_song = title
        self.title = self._interp.arguments + " " + title