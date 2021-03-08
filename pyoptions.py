from ui.qt import pywindow, pyelement

def create_element(parent, key, value):
    if isinstance(value, dict): return PyOptionsDictFrame(parent, key, value)
    elif isinstance(value, list): return PyOptionsListFrame(parent, key, value)

    if isinstance(value, int): el = pyelement.PyNumberInput(parent, f"option_{key}")
    elif isinstance(value, float): el = pyelement.PyNumberInput(parent, f"option_{key}", True)
    else: el = pyelement.PyTextInput(parent, f"option_{key}")
    el.events.EventInteract(lambda : parent.on_update(key, el.value))
    el.value = value
    return el

class PyOptionsListFrame(pyelement.PyFrame):
    def __init__(self, parent, key, value):
        if not isinstance(value, list): raise TypeError("value must be a list")
        self._key, self._value = key, value
        pyelement.PyFrame.__init__(self, parent, f"option_{key}")
        self.layout.margins(5)

    def create_widgets(self):
        row = 0
        for item in self._value:
            if isinstance(item, str): el = self.add_element(f"item_{row}", element_class=pyelement.PyTextInput, row=row)
            else: el = self.add_element(f"item_{row}", element_class=pyelement.PyNumberInput, double=isinstance(item, float), row=row)
            el.index, el.value = row, item
            el.events.EventInteract(lambda element: self.on_update(element.index, element.value))

            btn = self.add_element(f"del_{row}", element_class=pyelement.PyButton, row=row, column=1)
            btn.index, btn.text = row, "X"
            btn.events.EventInteract(lambda element: self.on_update(element.index))
            row += 1

        add_btn = self.add_element("add_btn", element_class=pyelement.PyButton, row=row, columnspan=2)
        add_btn.index, add_btn.text = row, "Add"
        add_btn.events.EventInteract(lambda element: self.on_update(element.index, ""))

    def on_update(self, index, value=None):
        if value is None:
            del self._value[index]
            change = 1
        elif index >= len(self._value):
            self._value.append(value)
            change = 2
        else:
            self._value[index] = value
            change = 0
        self.parent.on_update(self._key, self._value)

        if change > 0:
            for c in self.children: self.remove_element(c.element_id)
            self.create_widgets()
            if change == 2: self.get_element(f"item_{len(self._value) - 1}").get_focus()

class PyOptionsDictFrame(pyelement.PyFrame):
    def __init__(self, parent, key, value):
        if not isinstance(value, dict): raise TypeError("value must be a dictionary")
        self._key, self._value = key, value
        pyelement.PyFrame.__init__(self, parent, f"option_{key}")
        self.layout.margins(5)

    def create_widgets(self):
        row = 0
        for key, value in self._value.items():
            if not key.startswith("_"):
                lbl = self.add_element(f"lbl_{key}", element_class=pyelement.PyTextLabel, row=row)
                lbl.text = key.replace("_", " ").capitalize()
                lbl.set_alignment("centerV")

                self.add_element(f"val_{key}", element=create_element(self, key, value), row=row, column=1)
                sep = self.add_element(f"sep_{row}", element_class=pyelement.PySeparator, row=row+1, columnspan=2)
                sep.color, sep.thickness = "#111111", 1
                row += 2
        self.remove_element(f"sep_{row-2}")

    def on_update(self, key, value): self.parent.on_update(f"{self._key}::{key}" if self._key else key, value)

class PyOptionsFrame(pyelement.PyScrollableFrame):
    def __init__(self, parent, element_id, module_cfg):
        self._cfg = module_cfg
        pyelement.PyScrollableFrame.__init__(self, parent, element_id)
        self.show_scrollbar = False
        self.layout.row(0, weight=0).margins(0)
        self.events.EventDestroy(lambda : self._cfg.save())

    def create_widgets(self):
        cfg = self._cfg.value
        if len(cfg) > 0: self.add_element(element=PyOptionsDictFrame(self, "", cfg), column=1)
        else: self.add_element("lbl_empty", element_class=pyelement.PyTextLabel).text = "No configurable options"

    def on_update(self, key, value):
        print("key", key, "updated to", value)
        self._cfg[key] = value

class PyOptionsWindow(pywindow.PyWindow):
    def __init__(self, parent, modules):
        self._modules = modules
        pywindow.PyWindow.__init__(self, parent, "options")
        self.title = "PyPlayer Options"
        self.icon = "assets/icon"
        self.layout.row(1, weight=1).column(0, weight=0, minsize=50).column(1, weight=1)

    def create_widgets(self):
        self.add_element("lbl1", element_class=pyelement.PyTextLabel).text = "Modules:"
        modlist: pyelement.PyItemlist = self.add_element("module_list", element_class=pyelement.PyItemlist, row=1)
        modlist.itemlist = [m[0].upper() + m[1:] for m in self._modules.keys()]
        modlist.max_width = 100
        @modlist.events.EventInteract
        def _on_module_select(current): self["module_options"].current_index = current

        self.add_element("lbl2", element_class=pyelement.PyTextLabel, column=1).text = "Options:"
        options: pyelement.PyFrameList = self.add_element("module_options", element_class=pyelement.PyFrameList, row=1, column=1)
        for name, mod in self._modules.items(): options.add_frame(frame_class=PyOptionsFrame, module_cfg=mod.configuration)