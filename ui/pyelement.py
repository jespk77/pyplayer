from tkinter import ttk, font
import tkinter

class PyElement:
	""" Framework for elements that can be added to 'PyWindow' and 'RootPyWindow' instances, should not be created on its own """
	block_action = "break"

	def __init__(self, id="??"):
		self._configuration = {}
		self._dirty = False
		self._boundids = {}
		self.id = id

	@property
	def configuration(self):
		""" Get current configuration options (as dictionary) that have been set for this element
		 	(only used for writing to file, to get a specific option use 'element[option]' instead """
		self._dirty = False
		return self._configuration
	@configuration.setter
	def configuration(self, value):
		""" Takes a dictionary and updates all configuration options for this element, should only be used when loading configuration from file """
		if isinstance(value, dict):
			self._configuration = value
			self._load_configuration()
		else: raise TypeError("Can only update configuration using dictionary, not whatever you're giving me")

	@property
	def dirty(self):
		""" Returns true if the configuration for this element has been updated since last save to file """
		return self._dirty

	def mark_dirty(self, event=None):
		""" Mark this element as dirty (configuration options will be written to file next save)"""
		self._dirty = True

	def _load_configuration(self):
		self.configure(**self._configuration)

	def __setitem__(self, key, value):
		""" Update configuration item for this element """
		self._configuration[key] = value
		self.mark_dirty()
		try: super().__setitem__(key, value)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'setitem' method in:", super())
		return self

	def after(self, s, *args):
		""" Schedule function to be executed (with given parameters) after at least given seconds has passed """
		try: super().after(int(s * 1000), *args)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'after' method in:", super())
		return self

	def bind(self, sequence=None, func=None, add=None):
		""" Bind passed function to specified event, returns binding identifier (used for unbinding)
			Multiple events can be specified by separating events with '&&' """
		sequence = sequence.split("&&")
		for s in sequence: self._try_bind(s, func, add)
		return self
	def _try_bind(self, sequence=None, func=None, add=None):
		try: super().bind(sequence, func, add)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'bind' method in:", super())

	def unbind(self, sequence, funcid=None):
		""" Remove passed function bound from identifier
		 	Multiple events can be specified by separating events with '&&' """
		sequence = sequence.split("&&")
		for s in sequence: self._try_unbind(s, funcid)
		return self
	def _try_unbind(self, sequence, funcid):
		try: super().unbind(sequence, funcid)
		except AttributeError: print("[PyElement.ERROR] Cannot find super class 'unbind' method in:", super())

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
		try: tkinter.Frame.__init__(self, root.root)
		except AttributeError: tkinter.Frame.__init__(self, root)

class PyTextlabel(PyElement, tkinter.Label):
	""" Element for displaying a line of text """
	def __init__(self, window):
		PyElement.__init__(self)
		try: tkinter.Label.__init__(self, window.root)
		except AttributeError: tkinter.Label.__init__(self, window)
		self._string_var = None

	@property
	def display_text(self):
		return self._string_var.get() if not self._string_var is None else self.cget("text")
	@display_text.setter
	def display_text(self, value):
		if self._string_var is None:
			self._string_var = tkinter.StringVar()
			self.configure(textvariable=self._string_var)
		self._string_var.set(value)

class PyButton(PyElement, tkinter.Button):
	""" Element to create a clickable button  """
	def __init__(self, window):
		PyElement.__init__(self)
		try: tkinter.Button.__init__(self, window.root)
		except AttributeError: tkinter.Button.__init__(window)
		self._string_var = None
		self._callback = None

	@property
	def text(self):
		""" Returns the string that is currently displayed on the element """
		return self._string_var.get() if self._string_var is not None else self.cget("text")
	@text.setter
	def text(self, value):
		""" Set the display string of this element (once this is set, using configure 'text' no longer has effect) """
		if self._string_var is None:
			self._string_var = tkinter.StringVar()
			self.configure(textvariable=self._string_var)
		self._string_var.set(value)

	@property
	def callback(self):
		""" Returns the callback that is currently assigned to when the button is pressed or None if nothing bound (or if it cannot be called) """
		if not callable(self._callback): self._callback = None
		return self._callback
	@callback.setter
	def callback(self, value):
		""" Set the callback that gets called when the button is pressed """
		self._callback = value
		self.configure(command=value)

class PyTextfield(PyElement, tkinter.Text):
	""" Element to display multiple lines of text, includes support for user input, images and markers/tags
	 	*Tags are configurable in the options with format 'tag'.'option': 'value' """
	front = "0.0"
	back = "end"

	def __init__(self, window, accept_input=True):
		PyElement.__init__(self)
		try: tkinter.Text.__init__(self, window.root)
		except AttributeError: tkinter.Text.__init__(self, window)
		self.accept_input = accept_input

		self._font = font.Font(family="segoeui", size="11")
		self.configure(font=self._font)
		self._boldfont = None

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

	@property
	def font(self): return self._font
	@property
	def bold_font(self):
		if self._boldfont is None:
			self._boldfont = self._font.copy()
			self._boldfont.configure(weight="bold")
		return self._boldfont

	has_focus = tkinter.Text.focus_get
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

	def delete(self, index1, index2=None):
		self.configure(state="normal")
		tkinter.Text.delete(self, index1, index2)
		if not self.accept_input: self.configure(state="disabled")

	def _load_configuration(self):
		for key, value in self._configuration.items():
			item = key.split(".", maxsplit=1)
			if len(item) == 2: self.tag_configure(item[0], {item[1]: value})
			elif item[0] == "font":
				self._font = font.Font(**value)
				if self._boldfont is not None:
					self._boldfont.configure(**value)
					self._boldfont.configure(weight="bold")
				self.configure(font=self._font)
			else: self.configure({key: value})

	def __setitem__(self, key, value):
		item = key.split(".", maxsplit=1)
		if len(item) == 2:
			self.tag_configure(item[0], {item[1]: value})
			self._configuration[key] = value
			self.mark_dirty()
		else: PyElement.__setitem__(self, key, value)

	def __getitem__(self, key):
		if key in self._configuration: return self._configuration[key]
		try: return self.cget(key)
		except tkinter.TclError as e: print("[PyTextfield.ERROR] Cannot find key '{}' for element '{}': ".format(key, self.id), e)
		return None

class PyProgressbar(PyElement, ttk.Progressbar):
	""" Widget that displays a bar indicating progress made by the application """
	def __init__(self, window, horizontal=True):
		self._progress_var = tkinter.IntVar()
		self._style = ttk.Style()
		PyElement.__init__(self)
		try: ttk.Progressbar.__init__(self, window.root)
		except AttributeError: ttk.Progressbar.__init__(self, window)
		self.configure(mode="determinate", variable=self._progress_var)
		self.horizontal = horizontal

	@property
	def progress(self, actual=True):
		""" Gets the current progress of the bar
			Set 'actual' to false to return progress in relation to maximum (value between 0 and 1), otherwise it returns the absolute progress """
		p = self._progress_var.get()
		return p if actual else p / self.maximum
	@progress.setter
	def progress(self, value): self._progress_var.set(value)

	@property
	def determinate(self):
		""" If determinate is true, the bar is set to the current value
		 	If determinate is false, the bar is moving back and forth """
		return self.cget("mode") == "determinate"
	@determinate.setter
	def determinate(self, value): self.configure(mode="determinate" if value else "indeterminate")

	def _load_configuration(self):
		self._style.theme_use(self._configuration.get("theme", "default"))
		style = "Horizontal.TProgressbar" if self.horizontal else "Vertical.TProgressbar"
		self._style.configure(style, **self._configuration)
		self.configure(style=style)

	@property
	def maximum(self):
		""" Returns the total size of the bar, if the progress is set to this value the bar is full (default is 100) """
		return self.cget("maximum")
	@maximum.setter
	def maximum(self, value): self.configure(maximum=value)

class PyItemlist(PyElement, tkinter.Listbox):
	""" A list of options where the user can select one or more lines """
	def __init__(self, window):
		PyElement.__init__(self)
		try: tkinter.Listbox.__init__(self, window.root)
		except AttributeError: tkinter.Listbox.__init__(self, window)
		self.configure(selectmode="single")
		self.list_var = None
		self._items = None

	@property
	def itemlist(self):
		""" Returns the items displayed in the list """
		return self._items if self.list_var is not None else self.get(0, "end")
	@itemlist.setter
	def itemlist(self, value):
		""" Set the items displayed in this list (after the first call using 'insert' or 'delete' no longer has effect) """
		if self.list_var is None:
			self.list_var = tkinter.StringVar()
			self.configure(listvariable=self.list_var)

		self._items = value
		self.list_var.set(self._items)