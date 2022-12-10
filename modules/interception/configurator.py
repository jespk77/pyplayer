from ui.qt import pywindow, pyelement

from .codes import KeyCode
from .commands import key_commands

class ConfiguratorWindow(pywindow.PyWindow):
    window_name = "input_configurator"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, self.window_name)
        self.title = "Input configurator"
        self.layout.row(2, weight=1).column(1, weight=1)

    def create_widgets(self):
        self.add_element("keyboard", element_class=pyelement.PyLabelFrame).layout.margins(0)
        self._create_keyboard()

        controls = self.add_element("controls", element_class=pyelement.PyFrame, row=1)
        controls.layout.margins(0)
        controls.add_element("status", element_class=pyelement.PyTextLabel).text = "Press a key to configure it..."
        controls.add_element("command", element_class=pyelement.PyTextInput, row=1).accept_input = False
        controls["command"].events.EventInteract(self._on_command_change)

    def _create_keyboard(self):
        # base keys
        self._add_keys("Esc||F1|F2|F3|F4|F5|F6|F7|F8|F9|F10|F11|F12||Print|ScrollLock|Pause", 0)
        self._add_keys("`|1|2|3|4|5|6|7|8|9|0|-|=|Backspace||Insert|Home|PageUp||NumLock|Num /|Num *|Num -", 2)
        self._add_keys("Tab|Q|W|E|R|T|Y|U|I|O|P|[|]|\\||Del|End|PageDown||Num 7|Num 8|Num 9", 3)
        self._add_keys("CapsLock|A|S|D|F|G|H|J|K|L|;|'||||||||Num 4|Num 5|Num 6", 4)
        self._add_keys("||Z|X|C|V|B|N|M|,|.|/|||||Up|||Num 1|Num 2|Num 3", 5)
        self._add_keys("LCtrl|Win|LAlt|||||||||RAlt|RClick|RCtrl||Left|Down|Right||||Num .", 6)

        # keys with special formatting
        self._add_button("Enter", row=4, column=12, columnspan=2)
        self._add_button("LShift", row=5, columnspan=2)
        self._add_button("RShift", row=5, column=12, columnspan=2)
        self._add_button("Space", row=6, column=3, columnspan=8)
        self._add_button("Num +", row=3, rowspan=2, column=22).height = 50
        self._add_button("Num Enter", row=5, rowspan=2, column=22).height = 50
        self._add_button("Num 0", row=6, column=19, columnspan=2)

        # spacers to improve visuals
        frame = self["keyboard"]
        frame.add_element(element=pyelement.PySeparator(self, "spacer"), row=1, columnspan=23)
        frame.add_element(element=pyelement.PySeparator(self, "spacer1", horizontal=False), column=14, row=2, rowspan=5)
        frame.add_element(element=pyelement.PySeparator(self, "spacer2", horizontal=False), column=18, row=2, rowspan=5)

    def _add_keys(self, keys, row):
        for i, char in enumerate(keys.split("|")): self._add_button(char, row=row, column=i)

    def _add_button(self, key_name, **layout_kwargs):
        if key_name:
            command = key_commands.get_command_for_key(key_name)
            button = self["keyboard"].add_element(f"key_{key_name}", element_class=pyelement.PyButton, **layout_kwargs)
            button.text = f"|{key_name}|" if command else key_name
            if "columnspan" not in layout_kwargs: button.width = 60
            button.events.EventInteract(self._on_button_press)
            return button

    def _on_button_press(self, element):
        key = element.text.replace("|", "")
        code = KeyCode.get_code(key)
        print("VERBOSE", f"Key pressed: key={key}, code={code}")

        controls = self["controls"]
        controls["status"].text = f"Pressed key {key} (code={hex(code)})"
        controls["command"].code = code
        controls["command"].text = key_commands.get_command_for_code(code)
        controls["command"].accept_input = True

    def _on_command_change(self, element):
        command = element.value
        print("VERBOSE", f"Key code {hex(element.code)} changed to \"{command}\"")
        key_name = KeyCode.get_name(element.code)
        self["keyboard"][f"key_{key_name}"].text = f"|{key_name}|" if command else key_name
        key_commands[element.code] = element.value