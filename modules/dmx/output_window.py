from core.modules import Module
module = Module(__package__)

from ui.qt import pywindow, pyelement

class DMXOutputWindow(pywindow.PyWindow):
    main_window_id = "dmx_output"

    def __init__(self, parent):
        self._error = False
        pywindow.PyWindow.__init__(self, parent, self.main_window_id)
        self.title = "DMX Output"
        self._update_data(module.dmx.frame)

        @self.events.EventWindowOpen
        def _open():
            module.dmx.EventConnected(lambda : self._set_status_text(connected=True))
            module.dmx.EventDisconnected(lambda : self._set_status_text(connected=False))
            module.dmx.EventError(lambda e: self._on_error(e))
            module.dmx.EventDataTransmit(self._update_data)
        @self.events.EventWindowClose
        def _close(): module.dmx.clear_events()

    def create_widgets(self):
        status : pyelement.PyLabelFrame = self.add_element("status", element_class=pyelement.PyLabelFrame)
        status.label = "Status"
        status.add_element("text", element_class=pyelement.PyTextLabel, columnspan=2)
        self._set_status_text(connected=module.dmx.connected)
        start : pyelement.PyButton = status.add_element("start", element_class=pyelement.PyButton, row=1)
        start.text = "Start"
        @start.events.EventInteract
        def _start(): module.interpreter.put_command("dmx start")
        stop : pyelement.PyButton = status.add_element("stop", element_class=pyelement.PyButton, row=1, column=1)
        stop.text = "Stop"
        @stop.events.EventInteract
        def _stop(): module.interpreter.put_command("dmx stop")

        output : pyelement.PyLabelFrame = self.add_element("output", element_class=pyelement.PyLabelFrame, row=1)
        output.label = "Output"
        data : pyelement.PyTextField = output.add_element("data", element_class=pyelement.PyTextField)
        data.accept_input = False

    def _set_status_text(self, connected=False):
        if connected: self._error = False
        # an error message overrides the stopped message
        elif self._error: return
        self.schedule_task(func=lambda : self["status"]["text"].with_text("Controller connected" if connected else "Controller disconnected"))

    def _on_error(self, e):
        self._error = True
        self.schedule_task(func=lambda : self["status"]["text"].with_text(f"Controller error: {e}"))

    def _update_data(self, frame):
        self.schedule_task(func=lambda : self["output"]["data"].with_text(" ".join([str(value) for value in frame])))