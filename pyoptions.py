from ui.qt import pywindow, pyelement

def create_element(parent, key, cfg):
    value = cfg.value
    if isinstance(value, dict): return PyOptionsDictFrame(parent, key, cfg)
    elif isinstance(value, list): return PyOptionsListFrame(parent, key, cfg)

    element_id = f"option_{key}"
    if isinstance(value, int): el = pyelement.PyNumberInput(parent, element_id)
    elif isinstance(value, float): el = pyelement.PyNumberInput(parent, element_id, True)
    elif isinstance(value, str):
        if key.startswith("&"): el = pyelement.PyPathInput(parent, element_id, path=value)
        elif key.startswith("#"): el = pyelement.PyColorInput(parent, element_id, color=value)
        elif key.startswith("$"):
            el = pyelement.PyPathInput(parent, element_id)
            el.dialog.set_mode("directory")
        else: el = pyelement.PyTextInput(parent, element_id)
    else: raise ValueError("Unsupported type")
    el.events.EventInteract(lambda element: parent.on_update(key, element.value))
    el.value = value
    return el

class PyOptionsListFrame(pyelement.PyFrame):
    def __init__(self, parent, key, cfg):
        self._key, self._cfg = key, cfg
        pyelement.PyFrame.__init__(self, parent, f"option_{key}")
        self.layout.margins(5)

    def create_widgets(self):
        row = 0
        for item in self._cfg.value:
            if isinstance(item, str): el = self.add_element(f"item_{row}", element_class=pyelement.PyTextInput, row=row)
            else: el = self.add_element(f"item_{row}", element_class=pyelement.PyNumberInput, double=isinstance(item, float), row=row)
            el.index, el.value = row, item
            el.events.EventInteract(lambda element: self.on_update(element.index, element.value))

            btn = self.add_element(f"del_{row}", element_class=pyelement.PyButton, row=row, column=1)
            btn.index, btn.text, btn.max_width = row, "X", 20
            btn.events.EventInteract(lambda element: self.on_update(element.index))
            row += 1

        add_btn = self.add_element("add_btn", element_class=pyelement.PyButton, row=row, columnspan=2)
        add_btn.index, add_btn.text = row, "Add"
        add_btn.events.EventInteract(lambda element: self.on_update(element.index, ""))

    def on_update(self, index, value=None):
        if value is None:
            del self._cfg.value[index]
            change = 1
        elif index >= len(self._cfg.value):
            self._cfg.value.append(value)
            change = 2
        else:
            self._cfg.value[index] = value
            change = 0

        self._cfg.mark_dirty()
        if change > 0:
            for c in self.children: self.remove_element(c.element_id)
            self.create_widgets()
            if change == 2: self.get_element(f"item_{len(self._cfg.value) - 1}").get_focus()

class PyOptionsDictFrame(pyelement.PyFrame):
    def __init__(self, parent, key, cfg):
        self._key, self._cfg = key, cfg
        pyelement.PyFrame.__init__(self, parent, f"option_{key}")
        self.layout.column(1, weight=1).margins(5)

    def create_widgets(self):
        row = 0
        add_new = self._cfg.can_add_new

        for key, value in self._cfg.items():
            if not key.startswith("_"):
                if add_new:
                    inpt = self.add_element(f"inpt_{key}", element_class=pyelement.PyTextInput, row=row)
                    inpt.prev_value = inpt.value = key.lstrip("$#&")
                    inpt.events.EventInteract(self._move_key)

                else:
                    lbl = self.add_element(f"lbl_{key}", element_class=pyelement.PyTextLabel, row=row)
                    lbl.text = key.lstrip("$#&").replace("_", " ").capitalize()
                    lbl.set_alignment("centerV")

                self.add_element(f"val_{key}", element=create_element(self, key, value), row=row, column=1)

                if add_new:
                    btn = self.add_element(f"del_{key}", element_class=pyelement.PyButton, row=row, column=2)
                    btn.text, btn.max_width = "X", 20
                    btn.key = key
                    btn.events.EventInteract(self._delete_key)

                sep = self.add_element(f"sep_{row}", element_class=pyelement.PySeparator, row=row+1, columnspan=3)
                sep.color, sep.thickness = "#111111", 1
                row += 2

        if add_new:
            btn = self.add_element("add_new", element_class=pyelement.PyButton, row=row, columnspan=3)
            btn.text = "Add"
            btn.events.EventInteract(self._add_new)

    def _add_new(self):
        self._cfg[""] = self._cfg.new_value
        self._recreate_widgets()

    def _move_key(self, element):
        if element.prev_value != element.value:
            self._cfg[element.value] = self._cfg[element.prev_value]
            del self._cfg[element.prev_value]
            element.prev_value = element.value
            self._recreate_widgets()

    def _delete_key(self, element):
        del self._cfg[element.key]
        self._recreate_widgets()

    def _recreate_widgets(self):
        for c in self.children: self.remove_element(c.element_id)
        self.create_widgets()

    def on_update(self, key, value): self._cfg[key] = value

class PyOptionsFrame(pyelement.PyScrollableFrame):
    def __init__(self, parent, element_id, module_cfg):
        self._cfg = module_cfg
        pyelement.PyScrollableFrame.__init__(self, parent, element_id)
        self.show_scrollbar = False
        self.layout.row(0, weight=0).row(1, weight=1).margins(0)
        self.events.EventDestroy(lambda : self._cfg.save())

    def create_widgets(self):
        if len(self._cfg) > 0: self.add_element(element=PyOptionsDictFrame(self, "", self._cfg))
        else: self.add_element("lbl_empty", element_class=pyelement.PyTextLabel).text = "No configurable options"
        self.add_element("spacer", element_class=pyelement.PyFrame, row=1)

    def on_update(self, key, value): self._cfg[key] = value

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