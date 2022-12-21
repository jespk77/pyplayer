from ui.qt import pywindow, pyelement

class FixtureListFrame(pyelement.PyLabelFrame):
    def __init__(self, parent, element_id):
        pyelement.PyLabelFrame.__init__(self, parent, element_id)
        self.label = "Fixtures"

    def create_widgets(self):
        self.add_element("fixture_list", element_class=pyelement.PyItemlist, columnspan=2)

        btn1 = self.add_element("fixture_add", element_class=pyelement.PyButton, row=1)
        btn1.text = "Add"
        btn1.events.EventInteract(self._add_fixture)

        btn2 = self.add_element("fixture_remove", element_class=pyelement.PyButton, row=1, column=1)
        btn2.text = "Remove"
        btn2.events.EventInteract(self._remove_fixture)

    def _add_fixture(self):
        pass

    def _remove_fixture(self):
        pass

class FixtureControlFrame(pyelement.PyLabelFrame):
    def __init__(self, parent, element_id):
        pyelement.PyLabelFrame.__init__(self, parent, element_id)
        self.label = "DMX Control"
        self._fixture = None

    def create_widgets(self):
        self.add_element("name", element_class=pyelement.PyTextLabel)
        self.add_element("controller", element_class=pyelement.PyFrame, row=1)

    def set_fixture(self, fixture):
        self._fixture = fixture
        controller = self["controller"]
        for c in controller.children: controller.remove_element(c.element_id)

class FixtureControlWindow(pywindow.PyWindow):
    fixture_window_id = "fixture_window"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, self.fixture_window_id)
        self.title = "Fixture Control"
        self.layout.row(0, weight=0).row(1, weight=1).row(2, weight=0)

    def create_widgets(self):
        content = self.add_element("saveloadsetup", element_class=pyelement.PyLabelFrame)
        content.label = "Environment"
        filename = content.add_element("filename", element_class=pyelement.PyPathInput)
        filename.events.EventInteract(self._filename_changed)
        filename.value = self.configuration.get("filename", "")

        btn1 = content.add_element("savefile", element_class=pyelement.PyButton, column=1)
        btn1.text = "Save"
        btn1.events.EventInteract(self._save)

        btn2 = content.add_element("loadfile", element_class=pyelement.PyButton, column=2)
        btn2.text = "Load"
        btn2.events.EventInteract(self._load)

        self.add_element("list", element_class=FixtureListFrame, row=1)
        self.add_element("control", element_class=FixtureControlFrame, row=2)

    def _filename_changed(self):
        value = self["saveloadsetup"]["filename"].value
        if not value.endswith(".env"): self["saveloadsetup"]["filename"].value = value = f"{value}.env"
        self.configuration["filename"] = value

    def _load(self):
        filename = self["saveloadsetup"]["filename"].value
        if filename:
            try:
                with open(filename, "r") as file:
                    pass
            except FileNotFoundError: pass
            except Exception as e: print("ERROR", f"Loading setup from '{filename}':", e)

    def _save(self):
        filename = self["saveloadsetup"]["filename"].value
        if filename:
            try:
                with open(filename, "w") as file:
                    pass
            except Exception as e: print("ERROR", f"Saving setup to '{filename}':", e)