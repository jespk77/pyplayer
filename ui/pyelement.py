from tkinter import ttk, font
import tkinter

from ui import pyconfiguration

def check_master(master):
	if not isinstance(master, tkinter.Wm) and isinstance(master, PyElement) and not master._supports_children:
		raise TypeError("'{.__name__}' cannot contain additional widgets".format(type(master)))

class PyElement:
	""" Framework for elements that can be parented from other pyelements, should not be created on its own """
	block_action = "break"

	def __init__(self, id="<???>"):
		self._configuration = {}
		self._dirty = False
		self._boundids = {}
		self.id = id
		self.window = None
		self._master_cfg = True

	@property
	def configuration(self):
		""" Get current configuration options (as dictionary) that have been set for this element """
		return self._configuration
	@configuration.setter
	def configuration(self, value):
		""" Takes a dictionary and updates all configuration options for this element, should only be used when loading configuration from file """
		if isinstance(value, dict):
			self._configuration = value
			self._load_configuration()
			self.mark_dirty()
		else: raise TypeError("Can only update configuration with a dictionary, not '{}'".format(type(value).__name__))

	@property
	def has_master_configuration(self):
		""" Returns true if the configuration for this element should be written to file """
		return self._master_cfg
	@has_master_configuration.setter
	def has_master_configuration(self, value):
		""" Set whether or not the configuration should be added to configuration file (when false, element will never be marked as dirty)
		 	This is useful when creating many widgets that have the same configuration options """
		self._master_cfg = value
		self._dirty = False

	@property
	def dirty(self): return self._dirty
	@property
	def _supports_children(self):
		""" Signals whether new elements can be made a parent from this element,
		 	by default they cannot (exceptions being "window manager" like elements) """
		return False

	def mark_dirty(self, event=None):
		""" Mark this element as dirty (configuration options will be written to file next save)
			Has no effect if the configuration is not set to be added to configuration file"""
		if self._master_cfg: self._dirty = True

	def _load_configuration(self): self.configure(**self._configuration)

	def __setitem__(self, key, value):
		""" Update configuration item for this element """
		self._configuration[key] = value
		self.mark_dirty()
		try: super().__setitem__(key, value)
		except AttributeError: print("ERROR", "Cannot find super class 'setitem' method in:", super())
		return self

	def __getitem__(self, key):
		if key in self._configuration: return self._configuration[key]
		try: return self.cget(key)
		except (AttributeError, tkinter.TclError) as e: print("ERROR", "Cannot find key '{}' for element '{}': ".format(key, self.id), e)
		return pyconfiguration.ConfigurationEntry()

	def after(self, s, *args):
		""" Schedule function to be executed (with given parameters) after at least given seconds has passed """
		try: super().after(int(s * 1000), *args)
		except AttributeError: print("ERROR", "Cannot find super class 'after' method in:", super())
		return self

	def bind(self, sequence=None, func=None, add=None):
		""" Bind passed function to specified event, returns binding identifier (used for unbinding)
			Multiple events can be specified by separating events with '&&' """
		sequence = sequence.split("&&")
		for s in sequence: self._try_bind(s, func, add)
		return self
	def _try_bind(self, sequence=None, func=None, add=None):
		try: super().bind(sequence, func, add)
		except AttributeError: print("ERROR", "Cannot find super class 'bind' method in:", super().__name__)

	def unbind(self, sequence, funcid=None):
		""" Remove passed function bound from identifier
		 	Multiple events can be specified by separating events with '&&' """
		sequence = sequence.split("&&")
		for s in sequence: self._try_unbind(s, funcid)
		return self
	def _try_unbind(self, sequence, funcid):
		try: super().unbind(sequence, funcid)
		except AttributeError: print("ERROR", "Cannot find super class 'unbind' method in:", super().__name__)

	def configure(self, cnf=None, **kw):
		""" Update configuration options (are NOT saved to file, set options directly if it should be)
		 	(also note that using direct updating + calling in conbination can cause unwanted effects, only do this if you know what you're doing) """
		try: super()._configure("configure", cnf, kw)
		except AttributeError: print("ERROR", "Cannot find super class 'configure' method in:", super())
		except tkinter.TclError as e: print("ERROR", "Cannot set configuration for item '{}':".format(self.id), e)
		return self

""" Initializer of each 'PyElement' instance must contain a reference to its parent, which must also be a 'PyElement' instance
	For widgets that don't have a parent, use the frame of the window (using the 'frame' attribute on window)
	The window the frame is currently in can be accessed with the 'window' attribute (is None if not placed on a window)
"""
# === ELEMENT CONTAINERS ===
class PyFrame(PyElement, tkinter.Frame):
	""" Use as container for a collection of elements, parameter 'master' must be another pyelement """
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Frame.__init__(self, master)

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Frame.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	@property
	def _supports_children(self): return True

class PyScrollableFrame(PyFrame):
	""" Same as PyFrame but supports scrolling, horizontal and vertical scrollbars can optionally be added """
	def __init__(self, master):
		check_master(master)
		PyFrame.__init__(self, master)
		self._canvas = PyCanvas(self)
		self._content = PyFrame(self._canvas)
		self.grid_rowconfigure(0, weight=1)
		self.grid_columnconfigure(0, weight=1)
		self._content.bind("<Configure>", self._update_scrollregion, add=True)
		self._canvas.bind("<Configure>", self._update_width, add=True)
		self._canvas.grid(row=0, column=0, sticky="news")
		self._canvas.create_window((0,0), window=self._content, anchor="nw", tags="content_frame")
		self._scrollx = self._scrolly = None

	@property
	def frame(self): return self._content
	def _update_width(self, event): self._canvas.itemconfigure("content_frame", width=event.width)
	def _update_scrollregion(self, event): self._canvas.configure(scrollregion=self._canvas.bbox("all"))

	@property
	def horizontal_scrollbar(self): return self._scrollx is not None
	@property
	def vertical_scrollbar(self): return self._scrolly is not None

	@horizontal_scrollbar.setter
	def horizontal_scrollbar(self, vl):
		if vl and not self.horizontal_scrollbar:
			self._scrollx = PyScrollbar(self)
			self._scrollx.configure(orient="horizontal", command=self._canvas.xview)
			self._canvas.configure(xscrollcommand=self._scrollx.set)
			self._scrollx.grid(row=1, column=0, sticky="ew")

	@vertical_scrollbar.setter
	def vertical_scrollbar(self, vl):
		if vl and not self.vertical_scrollbar:
			self._scrolly = PyScrollbar(self)
			self._scrolly.configure(orient="vertical", command=self._canvas.yview)
			self._canvas.configure(yscrollcommand=self._scrolly.set)
			self._scrolly.grid(row=0, column=1, sticky="ns")

class PyLabelframe(PyElement, tkinter.LabelFrame):
	""" Same as PyFrame but has an outline around it and can add label at the top of the frame """
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.LabelFrame.__init__(self, master)

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.LabelFrame.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
	@property
	def _supports_children(self): return True

	@property
	def label(self): return self.cget("text")
	@label.setter
	def label(self, vl): self.configure(text=vl)

class PyCanvas(PyElement, tkinter.Canvas):
	""" Similar to PyFrame, but allows for drawing of geometric shapes, other widgets and images """
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Canvas.__init__(self, master)

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Canvas.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
	@property
	def _supports_children(self): return True

# === ELEMENT ITEMS ===

class PyTextlabel(PyElement, tkinter.Label):
	""" Element for displaying a line of text """
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Label.__init__(self, master)
		self._string_var = None

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Label.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	@property
	def display_text(self):
		return self._string_var.get() if not self._string_var is None else self.cget("text")
	@display_text.setter
	def display_text(self, value):
		if self._string_var is None:
			self._string_var = tkinter.StringVar()
			self.configure(textvariable=self._string_var)
		self._string_var.set(value)

class PyTextInput(PyElement, tkinter.Entry):
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Entry.__init__(self, master)
		self._format_str = None
		self._input_length = 0
		self._strvar = tkinter.StringVar()
		self._input_cmd = self.register(self._on_input_key)
		self.configure(textvariable=self._strvar, validate="key", validatecommand=(self._input_cmd, "%P"))

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Entry.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	@property
	def accept_input(self): return self.cget("state") == "disabled"
	@accept_input.setter
	def accept_input(self, vl): self.configure(state="normal" if vl else "disabled")

	@property
	def format_str(self): return self._format_str if self._format_str else ""
	@format_str.setter
	def format_str(self, fs):
		""" Allows to set specific characters that can be entered into this field, set None to allow everything """
		if fs:
			import re
			self._format_str = re.compile("[^{}]".format(fs))
		else: self._format_str = None

	@property
	def value(self): return self._strvar.get()
	@value.setter
	def value(self, vl):
		if vl and not self._on_input_key(vl): raise ValueError("Cannot set value; contains non-allowed characters")
		self._strvar.set(vl)

	@property
	def max_length(self): return self._input_length
	@max_length.setter
	def max_length(self, ln): self._input_length = ln

	def _on_input_key(self, entry):
		if not self._format_str: return True
		return self._input_length > 0 and len(entry) <= self._input_length and not self._format_str.search(entry)

class PyCheckbox(PyElement, tkinter.Checkbutton):
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Checkbutton.__init__(self, master)
		self._value = tkinter.IntVar()
		self._desc = tkinter.StringVar()
		self.configure(variable=self._value, textvariable=self._desc)

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Checkbutton.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	@property
	def description(self): return self._desc.get()
	@description.setter
	def description(self, vl): self._desc.set(vl)

	@property
	def image(self): return self.cget("image")
	@image.setter
	def image(self, ig):
		if not isinstance(ig, PyImage): raise TypeError("Image must be a PyImage, not {.__name__}".format(type(ig)))
		self.configure(image=ig)

	@property
	def checked(self): return self._value.get()
	@checked.setter
	def checked(self, check): self._value.set(check)

	@property
	def accept_input(self): return self.cget("state") != "disabled"
	@accept_input.setter
	def accept_input(self, vl): self.configure(state="normal" if vl else "disabled")

	@property
	def command(self): return self.cget("command")
	@command.setter
	def command(self, cb):
		if not callable(cb): raise TypeError("Callback must be callable!")
		self.configure(command=cb)

class PyButton(PyElement, tkinter.Button):
	""" Element to create a clickable button  """
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Button.__init__(self, master)
		self._string_var = None
		self._callback = None
		self._image = None

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Button.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	@property
	def accept_input(self): return self.cget("state") == "normal"
	@accept_input.setter
	def accept_input(self, vl): self.configure(state="normal" if vl else "disabled")

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
	def image(self):
		""" Return the image that is displayed on the button """
		return self.cget("image")
	@image.setter
	def image(self, vl):
		""" Set the image displayed on this button """
		self.configure(image=vl)
		self._image = vl

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

	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Text.__init__(self, master)

		self._font = font.Font(family="segoeui", size="11")
		self.configure(font=self._font)
		self._accept_input = True
		self._boldfont = None

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Text.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

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

	@property
	def text(self): return self.get(self.front, self.back).rstrip("\n")
	@text.setter
	def text(self, value):
		self.delete(self.front, self.back)
		self.insert(self.back, value)

	has_focus = tkinter.Text.focus_get
	current_focus = tkinter.Text.focus_displayof
	previous_focus = tkinter.Text.focus_lastfor
	def focus(self, force=False):
		""" Request widget focus if the window has focus
		pass true to force focus (don't really do this), otherwise this widget will get focus next time the window has focus """
		if force: return self.focus_force()
		else: return self.focus_set()

	def can_user_interact(self): return self.cget("state") == "normal"

	def insert(self, index, chars, *args):
		self.configure(state="normal")
		tkinter.Text.insert(self, index, chars, *args)
		if not self.accept_input: self.configure(state="disabled")

	def delete(self, index1, index2=None):
		self.configure(state="normal")
		tkinter.Text.delete(self, index1, index2)
		if not self.accept_input: self.configure(state="disabled")

	def _load_configuration(self):
		for key, value in self.configuration.items():
			item = key.split(".", maxsplit=1)
			if len(item) == 2: self.tag_configure(item[0], {item[1]: value})
			elif item[0] == "font":
				self._font = font.Font(**value)
				if self._boldfont is not None:
					self._boldfont.configure(**value)
					self._boldfont.configure(weight="bold")
				self.configure(font=self._font)
			else: self.configure({key: value})

	def __setitem__(self, key, value, dirty=True):
		item = key.split(".", maxsplit=1)
		if len(item) == 2:
			self.tag_configure(item[0], {item[1]: value})
			self._configuration[key] = value
		elif item[0].startswith("font"):
			item = key.split("::", maxsplit=1)
			if len(item) == 2:
				if self._font is None: self._font = font.Font()
				self._font.configure(**{item[1]: value})
				self.configure(font=self._font)
			else: print("ERROR", "Missing subkey in key argument '{}'".format(key))
		else: PyElement.__setitem__(self, key, value)
		if dirty: self.mark_dirty()

class PyProgressbar(PyElement, ttk.Progressbar):
	""" Widget that displays a bar indicating progress made by the application """
	def __init__(self, master):
		check_master(master)
		self._progress_var = tkinter.IntVar()
		self._style = ttk.Style()
		self._horizontal = True
		PyElement.__init__(self)
		ttk.Progressbar.__init__(self, master)
		self.configure(mode="determinate", variable=self._progress_var)

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		ttk.Progressbar.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	@property
	def progress(self, actual=True):
		""" Gets the current progress of the bar
			Set 'actual' to false to return progress in relation to maximum (value between 0 and 1), otherwise it returns the absolute progress """
		p = self._progress_var.get()
		return p if actual else p / self.maximum
	@progress.setter
	def progress(self, value): self._progress_var.set(value)

	@property
	def horizontal(self): return self._horizontal
	@horizontal.setter
	def horizontal(self, vl): self._horizontal = vl is True

	@property
	def determinate(self):
		""" If determinate is true, the bar is set to the current value
		 	If determinate is false, the bar is moving back and forth """
		return self.cget("mode") == "determinate"
	@determinate.setter
	def determinate(self, value): self.configure(mode="determinate" if value else "indeterminate")

	def _load_configuration(self):
		self._style.theme_use(self._configuration.get("theme", "default"))
		style = "Horizontal.TProgressbar" if self._horizontal else "Vertical.TProgressbar"
		try: self._style.configure(style, **self.configuration)
		except: pass
		self.configure(style=style)

	@property
	def maximum(self):
		""" Returns the total size of the bar, if the progress is set to this value the bar is full (default is 100) """
		return self.cget("maximum")
	@maximum.setter
	def maximum(self, value): self.configure(maximum=value)

class PyScrollbar(PyElement, tkinter.Scrollbar):
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Scrollbar.__init__(self, master)

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Scrollbar.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	@property
	def scrollcommand(self): return
	@scrollcommand.setter
	def scrollcommand(self, value): self.configure(command=value)

class PyItemlist(PyElement, tkinter.Listbox):
	""" A list of options where the user can select one or more lines """
	def __init__(self, master):
		check_master(master)
		PyElement.__init__(self)
		tkinter.Listbox.__init__(self, master, selectmode="single")
		self.list_var = None
		self._items = None
		self._font = None

	def grid(self, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		tkinter.Listbox.grid(self, row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)

	def _load_configuration(self):
		PyElement._load_configuration(self)
		if "font" in self.configuration:
			if self._font is None: self._font = font.Font()
			self._font.configure(**self.configuration["font"])
			self.configure(font=self._font)

	def __setitem__(self, key, value):
		k = key.split("::", maxsplit=1)
		if len(k) > 1 and k[0] == "font":
			if self._font is None: self._font = font.Font()
			if k[1] == "family": self._font.configure(family=value)
			elif k[1] == "size": self._font.configure(size=value)
			self.configure(font=self._font)
			self.event_generate("<Configure>")
		else: PyElement.__setitem__(self, key, value)

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


try:
	from PIL import Image, ImageTk
	class PyImage(ImageTk.PhotoImage):
		def __init__(self, file=None, url=None, bin_file=None):
			self._success = False
			if url:
				from urllib.request import urlopen
				import io
				u = urlopen(url)
				self._bytes = io.BytesIO(u.read())
				u.close()
				self._img = Image.open(self._bytes)
				ImageTk.PhotoImage.__init__(self, self._img)
				self._success = True

			elif bin_file:
				import io
				self._bytes = io.BytesIO()
				with open(bin_file, "rb") as file:
					self._img = Image.open(file, self._bytes)
				ImageTk.PhotoImage.__init__(self, self._img)
				self._success = True

			elif file:
				import os
				img, ext = os.path.splitext(file)
				if not ext: file = "{}.png".format(file)

				try: ImageTk.PhotoImage.__init__(self, file=file)
				except FileNotFoundError as e:
					print("ERROR", "Loading image:", e)
					ImageTk.PhotoImage.__init__(self, file="assets/blank.png")

				self._bytes = None
				self._success = True
			else: raise ValueError("Must specify either file, bin_file or url argument")

		def write(self, filename, format=None, from_coords=None):
			if self._bytes is not None:
				with open(filename, "wb") as file:
					file.write(self._bytes.getvalue())

		def __del__(self):
			if self._success: ImageTk.PhotoImage.__del__(self)
			else: print("INFO", "Skipped image cleanup since there was an error loading image")
except ImportError:
	print("ERROR", "'Pillow' module not found, images will not be visible!")
	class PyImage:
		""" Placeholder to avoid type errors in the rest of the program """
		def __init__(self, file=None, url=None, bin_file=None): pass
		def write(self, filename, format=None, from_coords=None): pass
		def __del__(self): pass