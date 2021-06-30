import json
from ui.qt import pywindow, pyelement

trigger_file = ""

class KeyConfigurationWindow(pywindow.PyWindow):
    window_id = "interception_key_window"

    def __init__(self, parent):
        with open(trigger_file, "r") as file: self._data = json.load(file)
        pywindow.PyWindow.__init__(self, parent, self.window_id)
        self.title = "Interception Key Configuration"
        self.icon = "assets/blank"

        self._dirty = False
        self.events.EventWindowDestroy(self.save)

    def create_widgets(self):
        content = self.add_element("content", element_class=pyelement.PyScrollableFrame)
        header = content.add_element("header", element_class=pyelement.PyFrame)
        header.layout.column(0, minsize=100, weight=0).column(1, weight=1)
        header.add_element("headerL", element_class=pyelement.PyTextLabel).text = "Key"
        header.add_element("headerR", element_class=pyelement.PyTextLabel, column=1).text = "Command"

        row = 1
        for key, value in self._data.items():
            item = content.add_element(f"item_{key}", element_class=pyelement.PyFrame, row=row)
            item.layout.column(0, minsize=100)
            name = item.add_element("name", element_class=pyelement.PyTextLabel)
            name.set_alignment("centerV")
            name.text = value["description"]

            element = item.add_element("value", element_class=pyelement.PyTextInput, column=1)
            element.value = value.get("command", "")
            element.key = key
            element.events.EventInteract(self._update)
            row += 1

    def _update(self, element):
        key = element.key
        data = self._data[key]

        if data.get("command", "") != element.value:
            print("VERBOSE", f"Updating '{data['description']}' to '{element.value}'")
            self._dirty = True
            self._data[key]["command"] = element.value

    def save(self):
       if self._dirty:
           print("VERBOSE", "Key trigger file dirty, writing to file...")
           with open(trigger_file, "w") as file: json.dump(self._data, file, indent=5, sort_keys=True)