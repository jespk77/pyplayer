import json

from .codes import KeyCode

class KeyCommands:
    keymap_file = "keymap.json"

    def __init__(self):
        self._keymap = {}
        self._load()

    def _load(self):
        print("VERBOSE", "(Re)loading key map")
        try:
            with open(self.keymap_file, "r") as file:
                self._keymap = json.load(file)
        except FileNotFoundError: pass
        except Exception as e: print("ERROR", f"Loading keymap from '{self.keymap_file}'", e)

    def _save(self):
        print("VERBOSE", "Saving key map to file")
        try:
            with open(self.keymap_file, "w") as file:
                json.dump(self._keymap, file, indent=5)
        except Exception as e: print("ERROR", f"Saving keymap to '{self.keymap_file}'", e)

    def get_command_for_key(self, key):
        code = KeyCode.get_code(key)
        return self.get_command_for_code(code)

    def get_command_for_code(self, code):
        return self._keymap.get(str(code), "")

    def set_command(self, key, command):
        self._keymap[str(key)] = command
        self._save()

    def __getitem__(self, item): return self._keymap[item]
    __setitem__ = set_command

key_commands = KeyCommands()