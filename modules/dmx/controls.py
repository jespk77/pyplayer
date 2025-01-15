from ui.qt import pyelement, pyevents

class DMXValueEvents(pyevents.PyElementEvents):
    def EventValueChanged(self, cb):
        self.register_event("value", cb)
        return cb

class DMXValueControl(pyelement.PyLabelFrame):
    def __init__(self, parent, element_id):
        if not hasattr(self, "_event_handler"): self._event_handler = DMXValueEvents(parent, self)
        pyelement.PyLabelFrame.__init__(self, parent, element_id)
        self.label = element_id.capitalize()

    @property
    def events(self): return self._event_handler

    @property
    def value(self): return self["value"].value
    @value.setter
    def value(self, value):
        value = min(max(0, int(value)), 255)
        self["value"].value = value
        self.events.call_event("value", value=value)

    def create_widgets(self):
        value : pyelement.PyProgessbar = self.add_element("value", element_class=pyelement.PyProgessbar, column=1)
        value.minimum, value.value, value.maximum = 0, 0, 255
        @value.events.EventInteract
        def _on_value_change(position): self.value = round(value.minimum + (position * value.maximum))

        set_min : pyelement.PyButton = self.add_element("min", element_class=pyelement.PyButton)
        set_min.text = "Min"
        @set_min.events.EventInteract
        def _set_min(): self.value = value.minimum

        set_max : pyelement.PyButton = self.add_element("max", element_class=pyelement.PyButton, column=2)
        set_max.text = "Max"
        @set_max.events.EventInteract
        def _set_max(): self.value = value.maximum

        set_min.width = set_max.width = 35
        self.layout.column(0, weight=0).column(1, weight=1).column(2, weight=0)

    @property
    def value_control(self) -> pyelement.PyProgessbar: return self["value"]

class DMXValueMapControl(DMXValueControl):
    def create_widgets(self):
        self.add_element("value", element_class=pyelement.PyItemlist)

    @property
    def value_control(self) -> pyelement.PyItemlist: return self["value"]

class DMXPanTiltEvents(pyevents.PyElementEvents):
    def EventPanChanged(self, cb):
        self.register_event("pan", cb)
        return cb

    def EventTiltChanged(self, cb):
        self.register_event("tilt", cb)
        return cb

class DMXPanTiltControl(DMXValueControl):
    BUTTON_STEP = 5

    def __init__(self, parent, element_id):
        self._event_handler = DMXPanTiltEvents(parent, self)
        DMXValueControl.__init__(self, parent, element_id)
        self.label = "Pan/Tilt"

    @property
    def events(self): return self._event_handler

    @property
    def pan(self) -> int: return self["pan_value"].value
    @pan.setter
    def pan(self, value: int):
        print("set pan", value)
        value = min(max(0, int(value)), 255)
        self["pan_value"].value = value
        self.events.call_event("pan", value=value)

    @property
    def tilt(self): return self["tilt_value"].value
    @tilt.setter
    def tilt(self, value):
        print("set tilt", value)
        value = min(max(0, value), 255)
        self["tilt_value"].value = value
        self.events.call_event("tilt", value=value)

    def create_widgets(self):
        move_up : pyelement.PyButton = self.add_element("up", element_class=pyelement.PyButton, column=3)
        move_up.text = "\U0001f809"
        @move_up.events.EventInteract
        def _move_up(): self.tilt += self.BUTTON_STEP

        tilt_value : pyelement.PyProgessbar = self.add_element("tilt_value", element_class=pyelement.PyProgessbar, row=1, column=3)
        tilt_value.horizontal = False
        tilt_value.height = 200
        tilt_value.minimum, tilt_value.value, tilt_value.maximum = 0, 0, 255
        @tilt_value.events.EventInteract
        def _set_tilt_value(position): self.tilt = round(tilt_value.minimum + (position * tilt_value.maximum))

        move_down : pyelement.PyButton = self.add_element("down", element_class=pyelement.PyButton, row=2, column=3)
        move_down.text = "\U0001f80b"
        @move_down.events.EventInteract
        def _move_down(): self.tilt -= self.BUTTON_STEP

        move_left : pyelement.PyButton = self.add_element("left", element_class=pyelement.PyButton, row=3)
        move_left.text = "\U0001f808"
        @move_left.events.EventInteract
        def _move_left(): self.pan -= self.BUTTON_STEP

        pan_value : pyelement.PyProgessbar = self.add_element("pan_value", element_class=pyelement.PyProgessbar, row=3, column=1)
        pan_value.width = 200
        pan_value.minimum, pan_value.value, pan_value.maximum = 0, 0, 255
        @pan_value.events.EventInteract
        def _set_pan_value(position): self.pan = round(pan_value.minimum + (position * pan_value.maximum))

        move_right : pyelement.PyButton = self.add_element("right", element_class=pyelement.PyButton, row=3, column=2)
        move_right.text = "\U0001f80a"
        @move_right.events.EventInteract
        def _move_right(): self.pan += self.BUTTON_STEP

        move_left.width = move_right.width = move_up.width = move_down.width = 35
        self.layout.row(0, weight=0).row(1, weight=1).row(2, weight=0).row(3, weight=0)
        self.layout.column(0, weight=0).column(1, weight=1).column(2, weight=0).column(3, weight=0)

    @property
    def value_control(self): raise AttributeError("'DMXPanTiltControl' does not have element 'value_control', use either 'pan_control' or 'tilt_control' instead")

    @property
    def pan_control(self) -> pyelement.PyProgessbar: return self["pan_value"]
    @property
    def tilt_control(self) -> pyelement.PyProgessbar: return self["tilt_value"]