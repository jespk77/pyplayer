from ui.qt import pywindow, pyelement

from .codes import KeyCode

class ConfiguratorWindow(pywindow.PyWindow):
    window_name = "input_configurator"

    def __init__(self, parent, keyboard_listener):
        pywindow.PyWindow.__init__(self, parent, self.window_name)
        self.title = "Input configurator"
        self.layout.row(2, weight=1).column(1, weight=1)

        self._keyboard_listener = keyboard_listener
        self._keyboard_listener.event_callback = self._on_key_press
        self._keyboard_listener_active = keyboard_listener.active
        self._keyboard_listener.start()

        @self.events.EventWindowDestroy
        def _on_destroy():
            self._keyboard_listener.event_callback = None
            if not self._keyboard_listener_active:
                print("VERBOSE", "Listener was not active before, stop it again")
                self._keyboard_listener.stop()

    def create_widgets(self):
        self.add_element("keyboard", element_class=pyelement.PyLabelFrame).layout.margins(0)
        self._create_keyboard()

        controls = self.add_element("controls", element_class=pyelement.PyFrame, row=1)
        controls.layout.margins(0)
        controls.add_element("status", element_class=pyelement.PyTextLabel, columnspan=2).text = "Press a key to configure it..."
        controls.add_element("command", element_class=pyelement.PyTextInput, row=1).accept_input = False
        btn = controls.add_element("test", element_class=pyelement.PyButton, row=1, column=1)
        btn.text, btn.accept_input = "Test \u25b6", False
        btn.events.EventInteract(self._on_test_action)

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
            button = self["keyboard"].add_element(f"key_{key_name}", element_class=pyelement.PyButton, **layout_kwargs)
            button.text = key_name
            if "columnspan" not in layout_kwargs: button.width = 60
            button.events.EventInteract(self._on_button_press)
            return button

    def _on_button_press(self, element):
        print("key pressed:", element.text)
        self["controls"]["status"].text = f"Pressed key {element.text} (code={hex(KeyCode.get_code(element.text))})"

    def _on_key_press(self, device, key):
        if self.is_active:
            print("VERBOSE", f"Received key down event from on code {hex(key.code)}")
            self["controls"]["status"].text = f"Pressed key {KeyCode.get_name(key.code)} (code={hex(key.code)}) on device {device}"
            return True
        return False

    def _on_test_action(self):
        pass