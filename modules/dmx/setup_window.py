from ui.qt import pywindow, pyelement
from .fixture_data import FixtureData
from .fixture_editor import DMXFixtureEditorWindow

class DMXSetupWindow(pywindow.PyWindow):
    main_window_id = "dmx_setup"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, self.main_window_id)
        self.title = "DMX Setup"

    def _edit_fixture(self, name=""):
        self.schedule_task(func=lambda: self.add_window(window=DMXFixtureEditorWindow(self, name)))

    def reload_fixtures(self):
        self["fixtures"]["list"].itemlist = sorted([fixture.name for fixture in FixtureData.get_fixtures()])
        self["fixtures"]["list"].selected_index = -1

    def create_widgets(self):
        fixture_settings : pyelement.PyLabelFrame = self.add_element("fixtures", element_class=pyelement.PyLabelFrame, row=1)
        fixture_settings.layout.column(0, weight=1).column(1, weight=1).column(2, weight=1)
        fixture_settings.label = "Fixture Types"

        fixtures : pyelement.PyItemlist = fixture_settings.add_element("list", element_class=pyelement.PyItemlist, columnspan=3)
        self.reload_fixtures()
        @fixtures.events.EventInteract
        def _selected_fixture_change(current): fixture_settings["edit"].accept_input = fixture_settings["remove"].accept_input = current >= 0

        add : pyelement.PyButton = fixture_settings.add_element("add", element_class=pyelement.PyButton, row=1)
        add.text = "Add"
        add.events.EventInteract(self._edit_fixture)
        edit : pyelement.PyButton = fixture_settings.add_element("edit", element_class=pyelement.PyButton, row=1, column=1)
        edit.text = "Edit"
        edit.events.EventInteract(lambda : self._edit_fixture(fixtures.selected_item))
        remove : pyelement.PyButton = fixture_settings.add_element("remove", element_class=pyelement.PyButton, row=1, column=2)
        remove.text = "Remove"
        @remove.events.EventInteract
        def _remove_fixture():
            FixtureData.remove_fixture(fixtures.selected_item)
            self.reload_fixtures()