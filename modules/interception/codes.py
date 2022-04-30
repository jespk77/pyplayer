class _KeyCodes:
    undefined_key = "Undefined"
    undefined_code = 0

    _codes =\
        "Esc|1|2|3|4|5|6|7|8|9|0|-|=|Backspace|Tab|" +\
        "Q|W|E|R|T|Y|U|I|O|P|[|]|Enter|LCtrl|A|S|" +\
        "D|F|G|H|J|K|L|;|'|`|LShift|\\|Z|X|C|V|" +\
        "B|N|M|,|.|/|RShift|Num *|LAlt|Space|CapsLock|F1|F2|F3|F4|F5|" +\
        "F6|F7|F8|F9|F10|NumLock|ScrollLock|Num 7|Num 8|Num 9|Num -|Num 4|Num 5|Num 6|Num +|Num 1|" +\
        "Num 2|Num 3|Num 0|Num .||||F11|F12|"

    _extra_codes = {
        "PrintScreen": 0x37 * 4,
        "Pause": 0x1d * 6,
        "Insert": 0x52 * 4,
        "Home": 0x47 * 4,
        "PageUp": 0x49 * 4,
        "Num /": 0x35 * 4,
        "Del": 0x53 * 4,
        "End": 0x4f * 4,
        "PageDown": 0x51 * 4,
        "Up": 0x48 * 4,
        "Num Enter": 0x1c * 4,
        "Win": 0x5b * 4,
        "RAlt": 0x38 * 4,
        "RCtrl": 0x1d * 4,
        "Left": 0x4b * 4,
        "Down": 0x50 * 4,
        "Right": 0x4d * 4
    }

    _name_to_code = _code_to_name = None

    def _load_name_to_code(self):
        self._name_to_code = { char: index+1 for index, char in enumerate(self._codes.split("|")) if char }
        self._name_to_code.update(self._extra_codes)

    def _load_code_to_name(self):
        self._code_to_name = { index+1: char for index, char in enumerate(self._codes.split("|")) if char }
        for key, code in self._extra_codes.items(): self._code_to_name[code] = key

    def get_name(self, char):
        """ Get the key name from its scancode """
        if self._code_to_name is None: self._load_code_to_name()
        return self._code_to_name.get(char, self.undefined_key)

    def get_code(self, name):
        """ Get the key scancode from its name """
        if self._name_to_code is None: self._load_name_to_code()
        return self._name_to_code.get(name, self.undefined_code)

    def __getattribute__(self, item):
        if item.startswith("Key_"): return self.get_code(item[4:])
        else: return object.__getattribute__(self, item)

    def __setattr__(self, key, value):
        if key.startswith("Key_"): raise TypeError("Key codes are read-only")
        else: object.__setattr__(self, key, value)

    def __getitem__(self, item):
        try: return self.get_name(int(item))
        except ValueError: pass
        raise KeyError(item)

KeyCode = _KeyCodes()