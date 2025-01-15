from core import modules
module = modules.Module(__package__)

from ui.qt import pyelement, pywindow

from .controls import DMXValueControl, DMXValueMapControl, DMXPanTiltControl
from .fixture import Fixture

class DMXControlWindow(pywindow.PyWindow):
    main_window_id = "dmx_control"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, self.main_window_id)
        self.title = "DMX Controls"
        self._fixtures = []
        self._dirty = False

    def _on_selection_changed(self, element: pyelement.PyItemlist, selected):
        if self._dirty: return

        indices = element.selected_index
        if selected:
            new_index = selected[-1]
            new_fixture = module.fixtures[new_index]

            updated_indices = [index for index in indices if module.fixtures[index].data.name == new_fixture.data.name]
            if indices != updated_indices:
                self._dirty = True
                element.selected_index = indices = updated_indices
                self._dirty = False

        self._fixtures = [module.fixtures[index] for index in indices if 0 <= index < len(module.fixtures)]
        self._update_elements(self._fixtures[-1] if len(self._fixtures) > 0 else None)

    def _update_elements(self, fixture : Fixture|None):
        controls : pyelement.PyScrollableFrame = self["controls"]
        pantilt : DMXPanTiltControl = controls["pantilt"]
        if fixture and (fixture.data.has_pan or fixture.data.has_tilt):
            pantilt.hidden = False
            pantilt.pan_control.hidden = not fixture.data.has_pan
            pantilt.pan_control.value = fixture.pan
            pantilt.tilt_control.hidden = not fixture.data.has_tilt
            pantilt.tilt_control.value = fixture.tilt
        else: pantilt.hidden = True

        color : DMXValueMapControl = controls["color"]
        if fixture and fixture.data.has_color:
            color.hidden = False
            color.value_control.itemlist = fixture.data.color.names
            color.value_control.selected_item = fixture.color
        else: color.hidden = True

        gobo : DMXValueMapControl = controls["gobo"]
        if fixture and fixture.data.has_gobo:
            gobo.hidden = False
            gobo.value_control.itemlist = fixture.data.gobo.names
            gobo.value_control.selected_item = fixture.gobo
        else: gobo.hidden = True

        shutter : DMXValueControl = controls["shutter"]
        if fixture and fixture.data.has_shutter:
            shutter.hidden = False
            shutter.value_control.value = fixture.shutter
        else: shutter.hidden = True

        strobe : DMXValueControl = controls["strobe"]
        if fixture and fixture.data.has_strobe:
            strobe.hidden = False
            strobe.value_control.value = fixture.strobe
        else: strobe.hidden = True

        intensity : DMXValueControl = controls["intensity"]
        if fixture and fixture.data.has_intensity:
            intensity.hidden = False
            intensity.value_control.value = fixture.intensity
        else: intensity.hidden = True

    def _set_pan(self, value):
        for fixture in self._fixtures: fixture.pan = value / 255

    def _set_tilt(self, value):
        for fixture in self._fixtures: fixture.tilt = value / 255

    def _set_color(self, element):
        for fixture in self._fixtures: fixture.color = element.selected_item

    def _set_gobo(self, element):
        for fixture in self._fixtures: fixture.gobo = element.selected_item

    def _set_shutter(self, value):
        for fixture in self._fixtures: fixture.shutter = value

    def _set_strobe(self, value):
        for fixture in self._fixtures: fixture.strobe = value

    def _set_intensity(self, value):
        for fixture in self._fixtures: fixture.intensity = value

    def create_widgets(self):
        self.add_element(element_class=pyelement.PyTextLabel).with_text("Fixtures")
        fixtures : pyelement.PyItemlist = self.add_element("fixtures", element_class=pyelement.PyItemlist, row=1)
        fixtures.itemlist = [fixture.name for fixture in module.fixtures] if module.fixtures else ["No fixtures configured"]
        fixtures.selection_mode = "multi"
        fixtures.events.EventInteract(self._on_selection_changed)
        fixtures.height = 100
        @fixtures.events.EventRightClick
        def _on_selection_rightclicked():
            fixtures.clear_selection()

        controls : pyelement.PyScrollableFrame = self.add_element("controls", element_class=pyelement.PyScrollableFrame, row=2)
        pantilt : DMXPanTiltControl = controls.add_element("pantilt", element_class=DMXPanTiltControl).with_hidden(True)
        pantilt.events.EventPanChanged(self._set_pan)
        pantilt.events.EventTiltChanged(self._set_tilt)
        color : DMXValueControl = controls.add_element("color", element_class=DMXValueMapControl, row=1).with_hidden(True)
        color.value_control.events.EventInteract(self._set_color)
        gobo : DMXValueMapControl = controls.add_element("gobo", element_class=DMXValueMapControl, row=2).with_hidden(True)
        gobo.value_control.events.EventInteract(self._set_gobo)
        shutter : DMXValueControl = controls.add_element("shutter", element_class=DMXValueControl, row=3).with_hidden(True)
        shutter.events.EventValueChanged(self._set_shutter)
        strobe : DMXValueControl = controls.add_element("strobe", element_class=DMXValueControl, row=4).with_hidden(True)
        strobe.events.EventValueChanged(self._set_strobe)
        intensity : DMXValueControl = controls.add_element("intensity", element_class=DMXValueControl, row=5).with_hidden(True)
        intensity.events.EventValueChanged(self._set_intensity)
        self.layout.row(0, weight=0).row(1, weight=0).row(2, weight=1)