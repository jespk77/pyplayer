from core import modules
module = modules.Module(__package__)

from ui.qt import pywindow, pyelement
from .fixture import Fixture
from .fixture_editor import DMXFixtureEditorWindow

class DMXSetupWindow(pywindow.PyWindow):
    main_window_id = "dmx_setup"

    def __init__(self, parent):
        pywindow.PyWindow.__init__(self, parent, self.main_window_id)
        self.title = "DMX Setup"

    def _edit_fixture_type(self, name=""):
        self.schedule_task(func=lambda: self.add_window(window=DMXFixtureEditorWindow(self, module.get_fixture_type_by_name(name))))

    def reload_fixture_types(self):
        self["content"]["fixture_types"]["list"].itemlist = [fixture.name for fixture in module.fixture_types]

    def create_widgets(self):
        content : pyelement.PyScrollableFrame = self.add_element("content", element_class=pyelement.PyScrollableFrame)
        content.show_scrollbar = False

        fixture_type_settings : pyelement.PyLabelFrame = content.add_element("fixture_types", element_class=pyelement.PyLabelFrame)
        fixture_type_settings.layout.column(0, weight=1).column(1, weight=1).column(2, weight=1)
        fixture_type_settings.label = "Fixture Types"

        fixture_types : pyelement.PyItemlist = fixture_type_settings.add_element("list", element_class=pyelement.PyItemlist, columnspan=3)
        self.reload_fixture_types()

        add : pyelement.PyButton = fixture_type_settings.add_element("add", element_class=pyelement.PyButton, row=1)
        add.text = "Add"
        add.events.EventInteract(self._edit_fixture_type)
        edit : pyelement.PyButton = fixture_type_settings.add_element("edit", element_class=pyelement.PyButton, row=1, column=1)
        edit.text = "Edit"
        edit.events.EventInteract(lambda : self._edit_fixture_type(fixture_types.selected_item))
        remove : pyelement.PyButton = fixture_type_settings.add_element("remove", element_class=pyelement.PyButton, row=1, column=2)
        remove.text = "Remove"
        @remove.events.EventInteract
        def _remove_fixture_type():
            module.delete_fixture_type(fixture_types.selected_item)
            self.reload_fixture_types()

        @fixture_types.events.EventInteract
        def _selected_fixture_type_change(current):
            fixture_type_settings["edit"].accept_input = fixture_type_settings["remove"].accept_input = current >= 0

        fixture_list : pyelement.PyLabelFrame = content.add_element("fixture_list", element_class=pyelement.PyLabelFrame, row=1)
        fixture_list.layout.column(0, weight=1).column(1, weight=1).column(2, weight=1)
        fixture_list.label = "Fixtures"

        fixtures : pyelement.PyTable = fixture_list.add_element("fixtures", element_class=pyelement.PyTable, columnspan=3)
        fixtures.column_labels = "Type", "Start channel"
        fixtures.column_width = 200, 100
        fixtures.dynamic_rows = True
        row = 0
        for fixture in module.fixtures:
            if row >= fixtures.rows: fixtures.insert_row(row)
            fixtures.set(row=row, column=0, value=fixture.data.name)
            fixtures.set(row=row, column=1, value=str(fixture.start_channel))
            row += 1

        error_txt : pyelement.PyTextLabel = self.add_element("error_txt", element_class=pyelement.PyTextLabel, row=1)
        save_btn : pyelement.PyButton = self.add_element("save_btn", element_class=pyelement.PyButton, row=2).with_text("Save && Close")
        @save_btn.events.EventInteract
        def _save_changes():
            try:
                module.fixtures = [Fixture(*fixtures.get(row=row)) for row in range(fixtures.rows)]
                module.save_fixtures()
                self.destroy()
            except Exception as e:
                error_txt.text = f"Save failed: {e}"
                print("INFO", "Failed to save fixure data", e)