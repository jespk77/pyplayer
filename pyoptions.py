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
        self._index, self._type = 0, self._get_type()
        self._items = []
        pyelement.PyFrame.__init__(self, parent, f"option_{key}", "vertical")
        self.events.EventDestroy(self.on_close)
        self.layout.margins(5)

    def _get_type(self):
        default = self._cfg.default_value
        return type(default) if default is not None else str

    def _create_itemframe(self, index, item):
        frame = self.add_element(f"item_{self._index}", element_class=pyelement.PyFrame, index=self._index)
        frame.current_index = index
        frame.layout.margins(0)

        if self._type is str: el = frame.add_element("value", element_class=pyelement.PyTextInput)
        else: el = frame.add_element(element=pyelement.PyNumberInput(frame, "value", double=self._type is float))
        el.value = item
        el.events.EventInteract(lambda element: self.on_update(element.parent.current_index, element.value))

        btn = frame.add_element("del", element_class=pyelement.PyButton, column=1)
        btn.text, btn.max_width = "X", 20
        btn.events.EventInteract(lambda element: self.on_update(element.parent.current_index))

        self._items.append(frame.element_id)
        self._index += 1

    def create_widgets(self):
        index = 0
        for item in self._cfg.value:
            self._create_itemframe(index, item)
            index += 1

        add_btn = self.add_element("add_btn", element_class=pyelement.PyButton)
        add_btn.new_index, add_btn.text = index, "Add"
        add_btn.events.EventInteract(lambda element: self.on_update(element.new_index, "" if self._type is str else 0))

    def on_update(self, index, value=None):
        if value is None:
            del self._cfg.value[index]
            self.remove_element(self._items[index])
            del self._items[index]

            for index, e in enumerate(self._items): self[e].current_index = index
            self["add_btn"].new_index = index + 1
        elif index >= len(self._cfg.value):
            self._cfg.value.append(value)
            self._create_itemframe(index, value)
            self["add_btn"].new_index = index + 1
        else: self._cfg.value[index] = value
        self._cfg.mark_dirty()

    def on_close(self): self._cfg.value = list(filter(lambda item: item != "", self._cfg.value))

class PyOptionsDictFrame(pyelement.PyFrame):
    def __init__(self, parent, key, cfg):
        self._key, self._cfg = key, cfg
        self._items, self._index = {}, 0
        pyelement.PyFrame.__init__(self, parent, f"option_{key}", "vertical")
        self.events.EventDestroy(self.on_close)
        self.layout.margins(5)

    def _create_item(self, key, value, index=None):
        add_new = self._cfg.can_add_new
        if not add_new and key.startswith("_"): return

        frame = self.add_element(f"item_{self._index}", element_class=pyelement.PyFrame, index=index)
        frame.key = key
        frame.layout.margins(0)

        if add_new:
            inpt = frame.add_element("input", element_class=pyelement.PyTextInput)
            inpt.prev_value = inpt.value = key.lstrip("$#&")
            inpt.events.EventInteract(self._move_key)
        else:
            lbl = frame.add_element("label", element_class=pyelement.PyTextLabel)
            lbl.text = key.lstrip("$#&").replace("_", " ").capitalize()
            lbl.set_alignment("centerV")

        frame.add_element("value", element=create_element(self, key, value), column=1)
        if add_new:
            btn = frame.add_element("delete", element_class=pyelement.PyButton, column=2)
            btn.text, btn.max_width = "X", 20
            btn.events.EventInteract(self._delete_key)

        sep = frame.add_element("sep", element_class=pyelement.PySeparator, row=1, columnspan=3)
        sep.color, sep.thickness = "#111111", 1
        self._items[key] = frame.element_id
        self._index += 1

    def create_widgets(self):
        for key, value in self._cfg.items(): self._create_item(key, value)

        if self._cfg.can_add_new:
            btn = self.add_element("add_new", element_class=pyelement.PyButton)
            btn.new_index, btn.text = self._index, "Add"
            btn.events.EventInteract(self._add_new)

    def _add_new(self):
        if not "" in self._cfg: self._create_item("", self._cfg.get_or_create_configuration(""), index=-1)

    def _move_key(self, element):
        if element.prev_value != element.value:
            key = element.value
            try: self._cfg.rename(element.prev_value, key)
            except KeyError:
                attempts = 0
                while True:
                    key = f"{element.value}_{attempts}"
                    try: self._cfg.rename(element.prev_value, key)
                    except KeyError: attempts += 1
                    else: break
                element.value = key
            self._items[key] = self._items[element.prev_value]
            del self._items[element.prev_value]
            element.prev_value = element.parent.key = key

    def _delete_key(self, element):
        key = element.parent.key
        self.remove_element(self._items[key])
        del self._cfg[key]

    def on_update(self, key, value): self._cfg[key] = value

    def on_close(self):
        if self._cfg.can_add_new:
            try: del self._cfg[""]
            except KeyError: pass

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