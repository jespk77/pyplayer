import sys

from ui import pywindow, pyelement

frame_width = 100
class ModuleSelector(pywindow.PyWindow):
	def __init__(self, root, modules):
		pywindow.PyWindow.__init__(self, root, "module_select")
		self._modules = modules
		self.title = "Pyplayer Modules"
		moptions = pyelement.PyScrollableFrame(self.frame)
		moptions.vertical_scrollbar = True
		moptions.frame.grid_columnconfigure(0, weight=1, minsize=100)
		self.set_widget("module_options", moptions, columnspan=2)

		b_cancel = pyelement.PyButton(self.frame)
		b_cancel.text = "Cancel & close"
		b_cancel.command = self._on_cancel
		self.set_widget("button_cancel", b_cancel, row=1)

		b_enable = pyelement.PyButton(self.frame)
		b_enable.text = "Enable all"
		b_enable.command = self._on_enable_all
		self.set_widget("button_enable", b_enable, row=1, column=1)

		self.confirm = True
		self.column_options(0, weight=1)
		self.column_options(1, weight=1)
		self.row_options(0, weight=1)

		index = 0
		self._module_inputs = {}
		for module_id, module_options in self._modules.items():
			pt = module_options.get("platform")
			invalid_platform = pt is not None and pt != sys.platform
			moptions.frame.grid_rowconfigure(index, weight=1, minsize=85)

			mod_frame = pyelement.PyLabelframe(moptions.frame)
			mod_frame.set_configuration()
			mod_frame.label = "Module: {}".format(module_id)
			if module_options.get("new"):
				del module_options["new"]
				mod_frame.label = "NEW " + mod_frame.label
			mod_frame.grid_columnconfigure(0, weight=1)
			mod_frame.grid(row=index, sticky="news")

			mod_enable = pyelement.PyCheckbox(mod_frame)
			mod_enable.set_configuration()
			mod_enable.module = module_id
			mod_enable.checked = not invalid_platform and module_options.get("enabled", False)
			mod_enable.accept_input = not invalid_platform and not module_options.get("required", False)
			mod_enable.command = lambda check=mod_enable: self._module_enable(check)
			mod_enable.grid(row=index, columnspan=2)
			self._update_checkbox(mod_enable)

			mod_platform = pyelement.PyTextlabel(mod_frame)
			mod_platform.set_configuration()
			mod_platform.display_text = "Supported platform: " + (pt if pt else "any")
			if invalid_platform:
				mod_platform.configure(foreground="red")
				module_options["enabled"] = False
			mod_platform.grid(row=index+1, columnspan=2)

			mod_priority_text = pyelement.PyTextlabel(mod_frame)
			mod_priority_text.set_configuration()
			mod_priority_text.display_text = "Command priority:"
			mod_priority_text.grid(row=index+2)

			mod_priority = pyelement.PyTextInput(mod_frame)
			mod_priority.set_configuration()
			mod_priority.module = module_id
			mod_priority.format_str = "0-9"
			mod_priority.max_length = 2
			mod_priority.accept_input = mod_enable.accept_input
			mod_priority.value = module_options.get("priority", "")
			mod_priority.command = lambda field=mod_priority: self._module_priority(field)
			mod_priority.grid(row=index+2, column=1)

			index += 1
			self._module_inputs[module_id] = mod_enable, mod_priority
		self.frame.focus_set()

	def _on_cancel(self):
		self.confirm = False
		self.destroy()

	def _on_enable_all(self):
		for check, py in self._module_inputs.values():
			if check.accept_input:
				check.checked = True
				try: self._module_enable(check)
				except AttributeError: pass

	@property
	def modules(self):
		return self._modules.copy()

	def _update_checkbox(self, checkbox):
		if checkbox.accept_input: checkbox.description = "Enabled" if checkbox.checked else "Disabled"
		else: checkbox.description = "Module required" if checkbox.checked else "Module incompatible"

	def _module_enable(self, checkbox):
		print("INFO", "Module '{}' was".format(checkbox.module), "enabled" if checkbox.checked else "disbled")
		try:
			self._modules[checkbox.module]["enabled"] = checkbox.checked
			self._update_checkbox(checkbox)
		except KeyError: print("WARNING", "Module '{}' was not found in the module list!".format(checkbox.module))

	def _module_priority(self, field):
		try: self._modules[field.module]["priority"] = int(field.value)
		except ValueError: pass
		except KeyError: print("WARNING", "Module '{}' was not found in the module list!".format(field.module))