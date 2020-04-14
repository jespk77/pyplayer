from ui.qt import pywindow, pyelement
import os, json, sys

class ModuleConfiguration(pyelement.PyLabelFrame):
    def __init__(self, parent, module_id, module_data, update_cb):
        pyelement.PyLabelFrame.__init__(self, parent, f"module.{module_id}")
        self.label = f"Module: {module_id}"
        self._id, self._data = module_id, module_data

        required = self._data.get("required", False)
        if required: self.add_element("req_label", element_class=pyelement.PyTextLabel, columnspan=2).text = "Required module"
        platform = self._data.get("platform")
        invalid_platform = platform is not None and sys.platform not in platform
        platform_label = self.add_element("platform_label", element_class=pyelement.PyTextLabel, row=1, columnspan=2)
        platform_label.text = "Platform: " + (",".join(platform) if isinstance(platform, list) else platform if platform else "any")

        check_enabled = self.add_element("check_enabled", element_class=pyelement.PyCheckbox, row=2, columnspan=2)
        check_enabled.checked = self._data.get("enabled", False) if not required else True if not invalid_platform else False
        check_enabled.text = "Enabled" if check_enabled.checked else "Disabled"
        if required or invalid_platform: check_enabled.accept_input = False
        @check_enabled.events.EventInteract
        def _on_toggle():
            check_enabled.text = "Enabled" if check_enabled.checked else "Disabled"
            self._data["enabled"] = check_enabled.checked
            if callable(update_cb): update_cb(self._id, self._data)

        priority_label = self.add_element("priority_label", element_class=pyelement.PyTextLabel, row=3)
        priority_label.text = "Priority:"
        priority_label.set_alignment("center")

        priority: pyelement.PyTextInput = self.add_element("priority_value", element_class=pyelement.PyTextInput, row=3, column=1)
        priority.max_length = 2
        priority.format_str = "90"
        priority.value = self._data.get("priority", 99)
        priority.accept_input = check_enabled.accept_input
        @priority.events.EventInteract
        def _on_update():
            self._data["priority"] = priority.value
            if callable(update_cb): update_cb(self._id, self._data)


class PyModuleConfigurator(pywindow.PyWindow):
    def __init__(self, root, module_list=None):
        self._root = root
        self._modules = module_list if module_list else [(md.name, md.path) for md in os.scandir("modules") if md.is_dir()]
        self._module_data = {}
        pywindow.PyWindow.__init__(self, root, "module_select")

        self.title = "PyPlayer Module Configuration"
        self.icon = "assets/icon.png"

    def _load_module_data(self):
        for module_id, module_path in self._modules:
            try:
                with open(os.path.join(module_path, "package.json")) as file:
                    print("INFO", f"Loading module '{module_id}'")
                    module_data = json.load(file)
                    self._module_data[module_id] = module_data
            except FileNotFoundError:
                print("WARNING", f"Skipping invalid module '{module_id}': package.json not found")
                continue
            except Exception as e:
                print("ERROR", "Loading module", module_id, "->", e)
                continue

    def create_widgets(self):
        modules = self.add_element("module_list", element_class=pyelement.PyScrollableFrame, columnspan=2)
        self._load_module_data()
        row=0
        for module_id, module_data in self._module_data.items():
            modules.add_element(element=ModuleConfiguration(modules, module_id, module_data, self._module_update), row=row)
            row += 1

        b_enable_all = self.add_element("button_all", element_class=pyelement.PyButton, row=1, column=0)
        b_enable_all.text = "Enable all"
        @b_enable_all.events.EventInteract
        def _enable_all():
            print("VERBOSE", "Enabling all modules")

        b_enable_none = self.add_element("button_none", element_class=pyelement.PyButton, row=1, column=1)
        b_enable_none.text = "Disable all"
        @b_enable_none.events.EventInteract
        def _disable_all():
            print("VERBOSE", "Disabling all modules")

        b_cancel = self.add_element("button_cancel", element_class=pyelement.PyButton, row=2, column=0)
        b_cancel.text = "Cancel"
        @b_cancel.events.EventInteract
        def _cancel():
            print("VERBOSE", "Module configuration canceled")
            self.destroy()

        b_confirm = self.add_element("button_confirm", element_class=pyelement.PyButton, row=2, column=1)
        b_confirm.text = "Confirm"
        @b_confirm.events.EventInteract
        def _confirm():
            print("VERBOSE", "Module configuration complete")
            self._root.set_module_data(self._module_data)
            self.destroy()

    def _module_update(self, module_id, module_data):
        print("VERBOSE", "Module data for", module_id, "updated")
        self._module_data[module_id] = module_data