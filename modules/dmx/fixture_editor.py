from ui.qt import pywindow, pyelement
from .dmx import DMXValueTable
from .fixture_data import FixtureData

class DMXFixtureEditorWindow(pywindow.PyWindow):
    main_window_id = "fixture_editor"

    def __init__(self, parent, name):
        self._fixture = FixtureData(name)
        pywindow.PyWindow.__init__(self, parent, self.main_window_id)
        self.title = f"Fixture editor: {name}" if name else "Add new fixture"
        self.set_geometry(x=parent.x, y=parent.y, width=600)

    def create_widgets(self):
        container = self.add_element("container", element_class=pyelement.PyScrollableFrame, columnspan=2)
        container.add_element(element_class=pyelement.PyTextLabel, row=0).with_text("Name:")
        fixture_name : pyelement.PyTextInput = container.add_element("fixture_name", element_class=pyelement.PyTextInput, row=0, column=1)
        fixture_name.value = self._fixture.display_name
        @fixture_name.events.EventInteract
        def _set_fixture_name(value):
            self._fixture.display_name = value
        container.add_element(element_class=pyelement.PyTextLabel, row=1).with_text("Channel count:")

        channels : pyelement.PyNumberInput = container.add_element(element=pyelement.PyNumberInput(container, "fixture_channels", all_updates=True), row=1, column=1).with_min(1)
        channels.value = self._fixture.channel_count
        @channels.events.EventInteract
        def _on_channel_count_change(value):
            self._fixture.channel_count = value
            for child in container.children:
                if child is channels: continue

                if isinstance(child, pyelement.PyNumberInput):
                    child.max = value
                elif isinstance(child, pyelement.PyLabelFrame):
                    for sub_child in child.children:
                        if isinstance(sub_child, pyelement.PyNumberInput):
                            sub_child.max = value

        movement_frame : pyelement.PyLabelFrame = container.add_element("movement", element_class=pyelement.PyLabelFrame, row=2, columnspan=2)
        @movement_frame.events.EventInteract
        def _clear_movement_channels(checked):
            if checked: return

            if self._fixture.has_pan:
                self._fixture.pan.channel = self._fixture.pan.extended_channel =\
                movement_frame["pan_channel"].value = movement_frame["pan2_channel"].value = 0
            if self._fixture.has_tilt:
                self._fixture.tilt.channel = self._fixture.tilt.extended_channel =\
                movement_frame["tilt_channel"].value = movement_frame["tilt2_channel"].value = 0

        movement_frame.label, movement_frame.checkbox, movement_frame.checked = "Movement", True, False
        movement_frame.add_element(element_class=pyelement.PyTextLabel).with_text("Pan channel:")
        pan : pyelement.PyNumberInput = movement_frame.add_element("pan_channel", element_class=pyelement.PyNumberInput, column=1).with_range(0, channels.value)
        pan.value = self._fixture.pan.channel if self._fixture.has_pan else 0
        @pan.events.EventInteract
        def _set_pan_channel(value):
            self._fixture.pan.channel = value
        movement_frame.add_element(element_class=pyelement.PyTextLabel, row=1).with_text("Extended pan:")
        pan2 : pyelement.PyNumberInput = movement_frame.add_element("pan2_channel", element_class=pyelement.PyNumberInput, row=1, column=1).with_range(0, channels.value)
        pan2.value = self._fixture.pan.extended_channel if self._fixture.has_pan else 0
        @pan2.events.EventInteract
        def _set_pan2_channel(value):
            self._fixture.pan.extended_channel = value
        movement_frame.add_element(element_class=pyelement.PyTextLabel, row=2).with_text("Tilt channel:")
        tilt : pyelement.PyNumberInput = movement_frame.add_element("tilt_channel", element_class=pyelement.PyNumberInput, row=2, column=1).with_range(0, channels.value)
        tilt.value = self._fixture.tilt.channel if self._fixture.has_tilt else 0
        @tilt.events.EventInteract
        def _set_tilt_channel(value):
            self._fixture.tilt.channel = value
        movement_frame.add_element(element_class=pyelement.PyTextLabel, row=3).with_text("Extended tilt:")
        tilt2 : pyelement.PyNumberInput = movement_frame.add_element("tilt2_channel", element_class=pyelement.PyNumberInput, row=3, column=1).with_range(0, channels.value)
        tilt2.value = self._fixture.tilt.extended_channel if self._fixture.has_tilt else 0
        @tilt2.events.EventInteract
        def _set_tilt2_channel(value):
            self._fixture.tilt.extended_channel = value

        color_frame : pyelement.PyLabelFrame = container.add_element("color", element_class=pyelement.PyLabelFrame, row=3, columnspan=2)
        color_frame.label, color_frame.checkbox, color_frame.checked = "Colors", True, self._fixture.has_color
        @color_frame.events.EventInteract
        def _clear_color_channels(checked):
            if checked: return
            if self._fixture.has_color: self._fixture.color.channel = color_frame["channel"].value = 0
        color_frame.add_element(element_class=pyelement.PyTextLabel).with_text("Color channel:")
        color : pyelement.PyNumberInput = color_frame.add_element("channel", element_class=pyelement.PyNumberInput, column=1).with_range(0, channels.value)
        color.value = self._fixture.color.channel if self._fixture.has_color else 0
        @color.events.EventInteract
        def _set_color_channel(value):
            self._fixture.color.channel = value
        color_data : DMXValueTable = color_frame.add_element("items", element_class=DMXValueTable, row=1, columnspan=2)
        if self._fixture.has_color:
            row = 0
            colors = self._fixture.color.items
            color_data.rows = len(colors) + 1
            for data in colors:
                for i, item in enumerate(data): color_data.set(row, i, item)
                row += 1
        @color_data.events.EventFocusLost
        def _set_color_data():
            self._fixture.color.set_values(color_data.get())

        gobo_frame : pyelement.PyLabelFrame = container.add_element("gobo", element_class=pyelement.PyLabelFrame, row=4, columnspan=2)
        gobo_frame.label, gobo_frame.checkbox, gobo_frame.checked = "Gobos", True, self._fixture.has_gobo
        @gobo_frame.events.EventInteract
        def _clear_gobo_channels(checked):
            if checked: return
            if self._fixture.has_gobo: self._fixture.gobo.channel = gobo_frame["channel"].value = 0
        gobo_frame.add_element(element_class=pyelement.PyTextLabel).with_text("Gobo channel:")
        gobo : pyelement.PyNumberInput = gobo_frame.add_element("channel", element_class=pyelement.PyNumberInput, column=1).with_range(0, channels.value)
        gobo.value = self._fixture.gobo.channel if self._fixture.has_gobo else 0
        @gobo.events.EventInteract
        def _set_gobo_channel(value):
            self._fixture.gobo.channel = value
        gobo_data : DMXValueTable = gobo_frame.add_element("items", element_class=DMXValueTable, row=1, columnspan=2)
        if self._fixture.has_gobo:
            row = 0
            gobos = self._fixture.gobo.items
            gobo_data.rows = len(gobos) + 1
            for data in gobos:
                for i, item in enumerate(data): gobo_data.set(row, i, item)
                row += 1
        @gobo_data.events.EventFocusLost
        def _set_gobo_data():
            self._fixture.gobo.set_values(gobo_data.get())

        extra_frame : pyelement.PyLabelFrame = container.add_element("extras", element_class=pyelement.PyLabelFrame, row=5, columnspan=2)
        extra_frame.label = "Extras"
        extra_frame.add_element(element_class=pyelement.PyTextLabel).with_text("Shutter channel:")
        shutter : pyelement.PyNumberInput = extra_frame.add_element("shutter_channel", element_class=pyelement.PyNumberInput, column=1).with_range(0, channels.value)
        shutter.value = self._fixture.shutter.channel if self._fixture.has_shutter else 0
        @shutter.events.EventInteract
        def _set_shutter_channel(value):
            self._fixture.shutter.channel = value
        extra_frame.add_element(element_class=pyelement.PyTextLabel, row=1).with_text("Strobe channel:")
        strobe : pyelement.PyNumberInput = extra_frame.add_element("strobe_channel", element_class=pyelement.PyNumberInput, row=1, column=1).with_range(0, channels.value)
        strobe.value = self._fixture.strobe.channel if self._fixture.has_strobe else 0
        @strobe.events.EventInteract
        def _set_strobe_channel(value):
            self._fixture.strobe.channel = value
        extra_frame.add_element(element_class=pyelement.PyTextLabel, row=2).with_text("Intensity channel:")
        intensity : pyelement.PyNumberInput = extra_frame.add_element("intensity_channel", element_class=pyelement.PyNumberInput, row=2, column=1).with_range(0, channels.value)
        intensity.value = self._fixture.intensity.channel if self._fixture.has_intensity else 0
        @intensity.events.EventInteract
        def _set_intensity_channel(value):
            self._fixture.intensity.channel = value
        self.events.EventWindowClose(self._window_closed)

    def _window_closed(self):
        text = self["container"]["fixture_name"].text
        if not text: return

        # creating a new fixture starts with an empty name so a name has to be filled in manually
        self._fixture.save(text.replace(" ", "_").lower())
        self.parent.reload_fixtures()