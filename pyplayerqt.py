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
        pywindow.PyWindow.__init__(self, root, window_id, "vertical")

        self.title = "PyPlayer"
        self.title_song = ""
        self.icon = "assets/icon.png"
        self.flags = PyPlayerCloseReason.NONE
        self.configuration.set_defaults(initial_cfg)

        self._command_history = History()
        self._interp = self._cmd = None
        self._left_head_update = self._right_head_update = None
        self._autocomplete = {
            "options": [], "index": 0
        }

        self.schedule_task(sec=1, loop=True, func=self._window_tick, task_id="window_tick")
        self.schedule_task(func=self._insert_reply, task_id="reply_task", reply="= Hello there =\nEnter a command below, the resulting output will show up here")
        self.add_task(task_id="notification_task", func=self._insert_notification)
        self.add_task(task_id="shutdown", func=self.destroy)
        self.add_task(task_id=self.autocomplete_task, func=self._update_suggestions)

        import pylogging
        pylogging.get_logger().log_level = self.configuration["loglevel"]
        self._window_tick()
        self._interp = Interpreter(self)

        @self.events.EventWindowOpen
        def _on_open():
            self.parent.hidden = True
            self._interp.start()
        @self.events.EventWindowDestroy
        def _on_close():
            self.stop_interpreter()
            self.parent.on_close(self)

    def create_widgets(self):
        pywindow.PyWindow.create_widgets(self)
        header = self.add_element("header", element_class=pyelement.PyFrame)
        header.add_element("left", element_class=pyelement.PyTextLabel, row=0, column=0)
        header_center = header.add_element("center", element_class=pyelement.PyTextLabel, row=0, column=1)
        header.add_element("right", element_class=pyelement.PyTextLabel, row=0, column=2)
        header.layout.column(1, minsize=30, weight=1).margins(0)
        header_center.text = "PyPlayer"
        header_center.set_alignment("centerH")

        console = self.add_element("console", element_class=pyelement.PyLabelFrame)
        console.layout.margins(5)
        console.label = " \u2692 Commands"
        command_output = console.add_element("output", element_class=pyelement.PyTextField, columnspan=2)
        command_output.accept_input = False
        console.add_element("prefix", element_class=pyelement.PyTextLabel, row=1).set_alignment("center")
        inpt: pyelement.PyTextInput = console.add_element(element=pyelement.PyTextInput(console, "input", True), row=1, column=1)

        @inpt.events.EventKeyDown("all")
        def _on_any_key(): self._autocomplete["options"].clear()

        @inpt.events.EventInteract
        def _on_input_enter():
            self._on_command_enter(inpt.value)
            inpt.value = ""
            _on_any_key()

        @inpt.events.EventHistory
        def _set_history(direction):
            if direction > 0: inpt.value = self._command_history.get_next("")
            elif direction < 0:
                hist = self._command_history.get_previous()
                if hist is not None: inpt.value = hist

            _on_any_key()
            return inpt.events.block_action

        @inpt.events.EventKeyDown("Escape")
        def _clear_input():
            inpt.value = ""
            _on_any_key()
            return inpt.events.block_action

        @inpt.events.EventKeyDown("Tab")
        def _try_autocomplete():
            txt = inpt.value
            if txt:
                if len(self._autocomplete["options"]) <= 1:
                    inpt.accept_input = False
                    self._interp.request_autocomplete(inpt.value)
                else: self._insert_autocomplete()
                return inpt.events.block_action

        @command_output.events.EventFocusGet
        def _on_focus(): inpt.get_focus()

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
            self._command_history.add(cmd)
            self["console"]["input"].accept_input = False
            self._interp.put_command(cmd, self._cmd)

    def _insert_reply(self, reply, tags=None, prefix=None, text=None):
        if not prefix: prefix = "> "
        self["console"]["output"].text = reply
        self["console"]["prefix"].text = prefix

        console_input = self["console"]["input"]
        console_input.accept_input = True
        if text: console_input.text = text
        console_input.get_focus()

    def _insert_notification(self, message, tags=None):
        console = self["console"]["output"]
        console.text = message + "\n" + console.text

    def _update_suggestions(self, suggestions):
        for s in suggestions:
            if s.options is not None:
                self._autocomplete["options"].extend([s.command + " " + option + " " + s.remainder for option in s.options])
            else: self._autocomplete["options"].append(s.command + " " + s.remainder)
            self._autocomplete["index"] = 0
        self._insert_autocomplete()

    def _insert_autocomplete(self):
        inpt = self["console"]["input"]
        inpt.accept_input = True
        try:
            index = self._autocomplete["index"]
            inpt.value = self._autocomplete["options"][index]
            self._autocomplete["index"] = (index + 1) % len(self._autocomplete["options"])
        except IndexError: pass
        inpt.get_focus()

    def _window_tick(self):
        date = datetime.datetime.today()
        self["header"]["center"].text = date.strftime(self.configuration["header_format"])
        if self._left_head_update: self._left_head_update(date)
        if self._right_head_update: self._right_head_update(date)

    def update_left_header(self, cb): self._left_head_update = cb
    def update_right_header(self, cb): self._right_head_update = cb

    def on_reply(self, reply, tags=None, cmd=None, prefix='', text=''):
        self._cmd = cmd
        if not self["console"]["input"].accept_input:
            self.schedule_task(task_id="reply_task", reply=reply, tags=tags, prefix=prefix, text=text)

    def on_notification(self, message, tags=None):
        self.schedule_task(task_id="notification_task", message=message, tags=tags)

    def update_title(self, title):
        if not title: title = self.title
        self.title_song = title
        self.title = self._interp.arguments + " " + title