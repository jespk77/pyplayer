from tkinter import ttk
import tkinter

class PyElement:
	""" Framework for elements that can be added to 'PyWindow' and 'RootPyWindow' instances, should not be created on its own """
	block_action = "break"

	def __init__(self, id="??"):
		self._configuration = {}
		self._dirty = False
		self.id = id

	@property
	def configuration(self):
		""" Get current configuration options (as dictionary: {key}:{value}) that have been set for this element """
		self._dirty = False
		return self._configuration
	@configuration.setter
	def configuration(self, value):
		""" Takes a dictionary and updates all configuration options for this element, should only be used when loading configuration from file """
		if isinstance(value, dict):
			self._configuration = value
			self._load_configuration(value)

	@property
	def dirty(self):
		""" Returns true if the configuration for this element has been updated since last save to file """
		return self._dirty

	def mark_dirty(self, event=None):
		""" Mark this element as dirty (configuration options will be written to file next save)"""
		self._dirty = True

	def _load_configuration(self, cfg):
		self.configure(**cfg)

	def __setitem__(self, key, value):
		""" Update configuration item for this element """
		self._configuration[key] = value
		self.mark_dirty()
		try: super().__setitem__(key, value)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'setitem' method in:", super())
		return self

	def after(self, s, *args):
		""" Schedule function to be executed (with given parameters) after at least given seconds has passed """
		try: super().after(s * 1000, *args)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'after' method in:", super())
		return self

	def bind(self, sequence=None, func=None, add=None):
		""" Bind passed function to specified event, returns binding identifier (used for unbinding) """
		try: super().bind(sequence, func, add)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'bind' method in:", super())
		return self

	def unbind(self, sequence, funcid=None):
		""" Remove passed function bound from identifier """
		try: super().unbind(sequence, funcid)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'unbind' method in:", super())
		return self

	def configure(self, cnf=None, **kw):
		""" Update configuration options (are NOT saved to file, set options directly if it should be)
		 	(also note that using direct updating + calling in conbination can cause unwanted effects, only do this if you know what you're doing) """
		try: super()._configure("configure", cnf, kw)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'configure' method in:", super())
		except tkinter.TclError as e: print("[PyElement.ERROR] Cannot set configuration for item '{}':".format(self.id), e)
		return self

class PyFrame(PyElement, tkinter.Frame):
	""" Use as container for a collection of elements """
	def __init__(self, root):
		PyElement.__init__(self)
		tkinter.Frame.__init__(self, root.root)

class PyTextlabel(PyElement, tkinter.Label):
	""" Element for displaying a line of text
		*Use 'display_text' attribute to change label text (all other common options can be set with 'configure') """
	def __init__(self, window):
		PyElement.__init__(self)
		self._string_var = tkinter.StringVar()
		tkinter.Label.__init__(self, window.root, textvariable=self._string_var)

	@property
	def display_text(self): return self._string_var.get()
	@display_text.setter
	def display_text(self, value): self._string_var.set(value)

class PyButton(PyElement, tkinter.Button):
	""" Element to create a clickable button
		*Configurable with 'callback' and 'text' options (in addition to all common options) """
	def __init__(self, window):
		PyElement.__init__(self)
		tkinter.Button.__init__(self, window.root)

class PyTextfield(PyElement, tkinter.Text):
	""" Element to display multiple lines of text, includes support for user input, images and markers/tags
	 	*Tags are configurable in the options with format 'tag'.'option': 'value' """
	front = "0.0"
	back = "end"

	def __init__(self, window):
		PyElement.__init__(self)
		tkinter.Text.__init__(self, window.root)
		self.accept_input = True

	@property
	def accept_input(self): return self._accept_input
	@accept_input.setter
	def accept_input(self, value):
		self.configure(state="normal" if value else "disabled")
		self._accept_input = value is True

	@property
	def current_pos(self): return "current"
	@current_pos.setter
	def current_pos(self, value): self.mark_set("current", value)

	def has_focus(self):
		""" Return true if the widget is focused """
		return tkinter.Text.focus_get
	current_focus = tkinter.Text.focus_displayof
	previous_focus = tkinter.Text.focus_lastfor
	def focus(self, force=False):
		""" Request widget focus if the window has focus
		pass true to force focus (don't really do this), otherwise this widget will get focus next time the window has focus """
		if force: return self.focus_force()
		else: return self.focus_set()

	def can_user_interact(self):
		return self["state"] == "normal"

	def insert(self, index, chars, *args):
		self.configure(state="normal")
		tkinter.Text.insert(self, index, chars, *args)
		if not self.accept_input: self.configure(state="disabled")

	def _load_configuration(self, cfg):
		for key, value in cfg.items():
			item = key.split(".", maxsplit=1)
			if len(item) == 2: tkinter.Text.tag_configure(self, item[0], {item[1]: value})
			else: self.configure({key: value})

	def __setitem__(self, key, value):
		item = key.split(".", maxsplit=1)
		if len(item) == 2:
			self.tag_configure(item[0], {item[1]: value})
			self._configuration[key] = value
			self.mark_dirty()
		else: PyElement.__setitem__(self, key, value)

class PyProgressbar(PyElement, ttk.Progressbar):
	def __init__(self, window, horizontal=True):
		PyElement.__init__(self)
		self._progress_var = tkinter.IntVar()
		self._style = ttk.Style()
		ttk.Progressbar.__init__(self, window.root, mode="determinate", variable=self._progress_var)
		self.horizontal = horizontal

	@property
	def progress(self): return self._progress_var.get()
	@progress.setter
	def progress(self, value): self._progress_var.set(value)

	@property
	def determinate(self):
		""" If determinate is true, the bar is set to the current value
		 	If determinate is false, the bar is moving back and forth """
		return self.cget("mode") == "determinate"
	@determinate.setter
	def determinate(self, value): self.configure(mode="determinate" if value else "indeterminate")

	def _load_configuration(self, cfg):
		super()._load_configuration(cfg)
		self._style.theme_use(cfg.get("theme", "default"))

	@property
	def maximum(self):
		""" Returns the total size of the bar, if the progress is set to this value the bar is full (default is 100) """
		return self.cget("maximum")
	@maximum.setter
	def maximum(self, value): self.configure(maximum=value)

	@property
	def horizontal(self):
		""" Returns whether the orientation is horizontal or vertical """
		return self.cget("horizontal")
	@horizontal.setter
	def horizontal(self, value):
		style = "Horizontal.TProgressbar" if value else "Vertical.TProgressbar"
		self._style.configure(style=style)
		self.configure(orient="horizontal" if value else "vertical", style=style)