from tkinter import ttk, font
import tkinter

from ui import pycontainer, pyevents, pyimage

def scroll_event():
	import sys
	return "<MouseWheel>" if "win" in sys.platform else "<Button-4>&&<Button-5>"

# PREDEFINED DEFAULT COLORS USED IN ELEMENT CONFIGURATIONS
background_color = "gray15"
foreground_color = "white"
disabled_color = "gray75"
highlight_color = "cyan"
sel_background_color = "gray"
sel_foreground_color = "white"

# === ELEMENT CONTAINERS ===
class PyElement:
	def __init__(self, id, container, tk, initial_cfg=None):
		if not isinstance(container, pycontainer.BaseWidgetContainer): raise ValueError("'{.__name__}' is not a valid widget container!".format(type(container)))
		if not initial_cfg: initial_cfg = {}

		self._id = id
		self._container = container
		self._tk = tk
		self._cfg = self._container.configuration.get_or_create(self.widget_id.lower(), initial_cfg)
		self.load_configuration()
		self._event_handler = pyevents.PyElementEvents(self)

	@property
	def widget_id(self): return self._id
	@property
	def configuration(self): return self._cfg
	@property
	def event_handler(self): return self._event_handler

	@property
	def width(self): return self._tk.winfo_width()
	@width.setter
	def width(self, value): self._tk.configure(width=value)

	@property
	def height(self): return self._tk.winfo_height()
	@height.setter
	def height(self, value): self._tk.configure(height=value)

	def set_focus(self): self._tk.focus_set()
	def move_focus_up(self): self._tk.tk_focusPrev()
	def move_focus_down(self): self._tk.tk_focusNext()

	def load_configuration(self):
		""" Set configuration options stored in configuration file """
		try: self._tk.configure(**self._cfg.value)
		except Exception as e: print("ERROR", "Loading configuration for widget '{}':".format(self.widget_id), e)

	def __getitem__(self, item):
		return self._tk.cget(item)


element_cfg = { "background": background_color, "foreground": foreground_color }
# === ELEMENT ITEMS ===
class PyTextlabel(PyElement):
	""" Element for displaying a line of text """
	def __init__(self, container, id, initial_cfg=None):
		PyElement.__init__(self, id, container, tkinter.Label(container._tk, **element_cfg), initial_cfg)
		self._string_var = tkinter.StringVar()
		self._tk.configure(textvariable=self._string_var)
		self._img = None

	@property
	def text(self):
		""" Get the text that is currently displayed on this label (or empty string if no text set)
		 	* update: renamed from 'display_text' """
		return self._string_var.get()
	@text.setter
	def text(self, value):
		""" Configure the text displayed on this label """
		self._string_var.set(value)
	display_text = text

	@property
	def image(self):
		""" Get the image currently displayed on this label (or None if not set) """
		return self._img
	@image.setter
	def image(self, img):
		""" Set the image that should be displayed, it should either be set to an instance of 'PyImage' or None to remove it """
		if img and not isinstance(img, pyimage.PyImage): raise ValueError("Image can only be set to 'PyImage' or None, not '{.__name__}'".format(type(img)))
		self._img = img
		self._tk.configure(image=img)


input_cfg = { "insertbackground": foreground_color, "selectforeground": sel_foreground_color, "selectbackground": sel_background_color }
input_cfg.update(element_cfg)
class PyTextInput(PyElement):
	def __init__(self, container, id, initial_cfg=None):
		PyElement.__init__(self, id, container, tkinter.Entry(container._tk, disabledbackground=background_color, **input_cfg), initial_cfg)
		self._format_str = self._cmd = None
		self._input_length = 0
		self._strvar = tkinter.StringVar()
		self._input_cmd = self._tk.register(self._on_input_key)
		self._tk.configure(textvariable=self._strvar, validate="key", validatecommand=(self._input_cmd, "%P"))
		@self.event_handler.KeyEvent("escape")
		def _clear_input(): self.value = ""

	@property
	def accept_input(self): return self._tk.cget("state") == "disabled"
	@accept_input.setter
	def accept_input(self, vl):
		""" Control whether the current input value can be adjusted """
		self._tk.configure(state="normal" if vl else "disabled")

	@property
	def format_str(self): return self._format_str if self._format_str else ""
	@format_str.setter
	def format_str(self, fs):
		""" Allows to set a regular expression for characters that can be entered into this field, or None to allow everything """
		if fs:
			import re
			self._format_str = re.compile("[^{}]".format(fs))
			self.value = self._format_str.sub(self.value, "")
		else: self._format_str = None

	@property
	def command(self): return self._cmd
	@command.setter
	def command(self, vl):
		""" Gets called whenever the input value is updated by the user """
		if vl:
			if not callable(vl): raise TypeError("Command callback for 'PyTextInput' must be callable or None!")
			self._cmd = self._strvar.trace_add("write", lambda *args: vl())
		else:
			self._strvar.trace_remove("write", self._cmd)
			self._cmd = None

	@property
	def value(self): return self._strvar.get()
	@value.setter
	def value(self, vl):
		""" Current value currently set for this input field """
		vl = str(vl)
		if vl and not self._on_input_key(vl): raise ValueError("Cannot set value {}; contains non-allowed characters".format(vl))
		self._strvar.set(vl)

	@property
	def max_length(self): return self._input_length
	@max_length.setter
	def max_length(self, ln):
		""" Character limit for this input field, when this limit is reached, no more characters can be entered; set to 0 to disable limit """
		self._input_length = ln

	def _on_input_key(self, entry): return self._input_length == 0 or (len(entry) <= self._input_length and (not self._format_str or not self._format_str.search(entry)))


checkbox_cfg = { "activebackground": background_color, "activeforeground": foreground_color, "selectcolor": background_color }
checkbox_cfg.update(element_cfg)
class PyCheckbox(PyElement):
	def __init__(self, container, id, initial_cfg=None):
		PyElement.__init__(self, id, container, tkinter.Checkbutton(container._tk, **checkbox_cfg), initial_cfg)
		self._value = tkinter.IntVar()
		self._desc = tkinter.StringVar()
		self._img = None
		self._tk.configure(variable=self._value, textvariable=self._desc)

	@property
	def text(self):
		""" The text that is displayed to the side of this checkbox, returns empty string if nothing set
		 	* update: renamed from 'description' property """
		return self._desc.get()
	@text.setter
	def text(self, vl): self._desc.set(vl)
	description = text

	@property
	def image(self):
		""" The image that is displayed to the side of this checkbox, returns None if not set """
		return self._img
	@image.setter
	def image(self, ig):
		if ig and not isinstance(ig, pyimage.PyImage): raise TypeError("Image must be a PyImage, not {.__name__}".format(type(ig)))
		self._tk.configure(image=ig)
		self._img = ig

	@property
	def checked(self):
		""" Whether the checkbox is currently set or not """
		return self._value.get()
	@checked.setter
	def checked(self, check): self._value.set(check)

	@property
	def accept_input(self):
		""" Whether the user can interact with the checkbox """
		return self._tk.cget("state") != "disabled"
	@accept_input.setter
	def accept_input(self, vl): self._tk.configure(state="normal" if vl else "disabled")

	@property
	def command(self):
		""" The handler that gets called whenever the checkbox gets toggled """
		return self._tk.cget("command")
	@command.setter
	def command(self, cb):
		if not callable(cb): raise TypeError("Callback must be callable!")
		self._tk.configure(command=cb)


button_cfg = { "activebackground": background_color, "activeforeground": foreground_color }
button_cfg.update(element_cfg)
class PyButton(PyElement):
	def __init__(self, container, id, initial_cfg=None):
		PyElement.__init__(self, id, container, tkinter.Button(container._tk, **button_cfg), initial_cfg)
		self._string_var = tkinter.StringVar()
		self._tk.configure(textvariable=self._string_var)
		self._callback = self._image = None

	@property
	def accept_input(self): return self._tk.cget("state") == "normal"
	@accept_input.setter
	def accept_input(self, vl): self._tk.configure(state="normal" if vl else "disabled")

	@property
	def text(self):
		""" Returns the string that is currently displayed on the button """
		return self._string_var.get()
	@text.setter
	def text(self, value):
		""" Set the display string of this element (once this is set, using configure 'text' no longer has effect) """
		self._string_var.set(value)

	@property
	def image(self):
		""" Return the image that is displayed on the button """
		return self._tk.cget("image")
	@image.setter
	def image(self, vl):
		""" Set the image displayed on this button """
		self._tk.configure(image=vl)
		self._image = vl

	@property
	def command(self):
		""" Returns the callback that is currently assigned to when the button is pressed or None if nothing bound """
		if not callable(self._callback): self._callback = None
		return self._callback
	@command.setter
	def command(self, value):
		""" Set the callback that gets called when the button is pressed """
		self._callback = value
		self._tk.configure(command=value)


class PyTextfield(PyElement):
	front = "0.0"
	back = "end"
	def __init__(self, container, id, initial_cfg=None):
		self._font = font.Font(family="segoeui", size="11")
		PyElement.__init__(self, id, container, tkinter.Text(container._tk, **input_cfg), initial_cfg)
		self.accept_input = True
		self._tk.configure(font=self._font)
		self._cmd = None

	@property
	def accept_input(self): return self._accept_input
	@accept_input.setter
	def accept_input(self, value):
		self._tk.configure(state="normal" if value else "disabled")
		self._accept_input = value is True

	@property
	def current_pos(self): return "current"
	@current_pos.setter
	def current_pos(self, value): self._tk.mark_set("current", value)

	@property
	def text(self): return self._tk.get(self.front, self.back).rstrip("\n")
	@text.setter
	def text(self, value):
		self.delete(self.front, self.back)
		self.insert(self.back, value)

	@property
	def cursor(self):
		""" Get the textfield coordinate currently set to the insert cursor """
		return self.position("insert")
	@cursor.setter
	def cursor(self, value):
		try: self._tk.mark_set("insert", value)
		except tkinter.TclError as e: print("ERROR", "While setting insert mark:", e)

	@property
	def command(self):
		""" Get the callback that is registered when any character is entered, returns None if not set """
		return self._cmd
	@command.setter
	def command(self, vl):
		if vl and not callable(vl): raise ValueError("Callback must be callable!")
		self._cmd = vl
		if vl:
			@self.event_handler.KeyEvent("all")
			def _on_key_press(char):
				if self._cmd:
					try: self._cmd(char)
					except Exception as e: print("ERROR", "Processing callback for textfield:", e)

	def can_interact(self): return self._tk.cget("state") == "normal"
	def insert(self, index, chars, *args):
		""" Insert text into the given position (ignores 'accept_input' property) """
		if not self.accept_input: self._tk.configure(state="normal")
		self._tk.insert(index, chars, *args)
		if not self.accept_input: self._tk.configure(state="disabled")

	def delete(self, index1, index2=None):
		""" Delete text between the given positions (ignores 'accept_input' property) """
		self._tk.configure(state="normal")
		self._tk.delete(index1, index2)
		if not self.accept_input: self._tk.configure(state="disabled")

	def position(self, tag):
		""" Get the exact coordinates in this text field, or emtpy string if nothing found """
		pos = self._tk.index(tag)
		return pos if pos else ""

	def show(self, position):
		""" Make sure that the given line is visible on screen """
		self._tk.see(position)

	def get_text(self, from_pos, to_pos=None):
		""" Get the text that was set between given positions """
		return self._tk.get(from_pos, to_pos)

	def place_mark(self, mark, position, gravity="right"):
		self._tk.mark_set(mark, position)
		self._tk.mark_gravity(mark, gravity)

	def clear_selection(self):
		""" Remove selection in this text field (has no effect if nothing was selected) """
		try: self._tk.tag_remove("sel", self.front, self.back)
		except: pass

	def load_configuration(self):
		dt = self._cfg.value
		ft = dt.get("font")
		if ft:
			del dt["font"]
			try:
				self._font.configure(**ft)
				self._tk.configure(font=self._font)
			except tkinter.TclError as e: print("ERROR", "While setting font properties for text field '{}':".format(self.widget_id), e)

		for key, value in dt.items():
			key = key.split(".", maxsplit=1)
			if len(key) == 2:
				try: self._tk.tag_configure(key[0], **{key[1]: value})
				except Exception as e: print("ERROR", "Setting tag configuration for element '{}':".format(self.widget_id), e)
			else:
				try: self._tk.configure(**{key[0]:value})
				except Exception as e: print("ERROR", "Setting configuration value for element '{}':".format(self.widget_id), e)


progress_cfg = { "background": "green", "troughcolor": background_color }
class PyProgressbar(PyElement):
	def __init__(self, container, id, initial_cfg=None):
		self._style = ttk.Style()
		self._style.theme_use("default")
		self._style.configure(style="default", **progress_cfg)
		self.horizontal = True
		PyElement.__init__(self, id, container, ttk.Progressbar(container._tk), initial_cfg)
		self._progress_var = tkinter.IntVar()
		self._tk.configure(mode="determinate", variable=self._progress_var)

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
	def background_color(self): return self._tk.cget("background")
	@background_color.setter
	def background_color(self, c):
		try: self._style.configure(style="default", background=c)
		except tkinter.TclError as e: print("ERROR", "Setting background color for progressbar '{}':".format(self.widget_id), e)

	@property
	def determinate(self):
		""" If determinate is true, the bar is set to the current value
		 	If determinate is false, the bar is moving back and forth """
		return self._tk.cget("mode") == "determinate"
	@determinate.setter
	def determinate(self, value): self._tk.configure(mode="determinate" if value else "indeterminate")
	@property
	def maximum(self):
		""" Returns the total size of the bar, if the progress is set to this value the bar is full (default is 100) """
		return self._tk.cget("maximum")
	@maximum.setter
	def maximum(self, value):
		try: self._tk.configure(maximum=value)
		except tkinter.TclError as e: print("ERROR", "Setting maximum value for progressbar '{}':".format(self.widget_id), e)

	def load_configuration(self):
		try: self._style.configure(style="Horizontal.TProgressbar" if self.horizontal else "Vertical.TProgressbar", **self._cfg.value)
		except tkinter.TclError as e: print("ERROR", "Loading configuration for '{}':".format(self.widget_id), e)

class PyScrollbar(PyElement):
	def __init__(self, container, id, initial_cfg=None):
		PyElement.__init__(self, id, container, tkinter.Scrollbar(container._tk), initial_cfg)

	@property
	def set_command(self): return self._tk.set

	@property
	def scrollcommand(self): return self._tk.cget("command")
	@scrollcommand.setter
	def scrollcommand(self, value): self._tk.configure(command=value)

	@property
	def orientation(self): return self._tk.cget("orient")
	@orientation.setter
	def orientation(self, ort): self._tk.configure(orient=ort)

list_cfg = { "selectbackground": background_color, "selectforeground": highlight_color }
list_cfg.update(element_cfg)
class PyItemlist(PyElement):
	""" A list of options where the user can select one or more lines """
	def __init__(self, container, id, initial_cfg=None):
		PyElement.__init__(self, id, container, tkinter.Listbox(container._tk, selectmode="single", **list_cfg), initial_cfg)
		self._list_var = tkinter.StringVar()
		self._tk.configure(listvariable=self._list_var)
		self._items = self._font = None

	@property
	def itemlist(self):
		""" Returns the items displayed in the list """
		return self._items if self._list_var is not None else self._tk.get(0, "end")
	@itemlist.setter
	def itemlist(self, value):
		""" Set the items displayed in this list (after the first call using 'insert' or 'delete' no longer has effect) """
		self._items = value
		self._list_var.set(self._items)

	def get_nearest_item(self, y):
		""" Get the element at the mouse pointer when processing event from bound callback """
		return self._items[self._tk.nearest(y)]
	def move_to(self, position):
		""" Scroll up/down so that the given position is visible """
		self._tk.see(position)

	def clear_selection(self):
		""" Clear any previously selected items """
		self._tk.selection_clear(0, "end")
	def set_selection(self, start, end=None, clear=True):
		""" Set selection to provided range (if start and end are given, when only start is given only one item gets selected), also clears any previous selection(s), unless 'clear' keyword is set to false """
		if clear: self.clear_selection()
		self._tk.selection_set(start, end)

	#todo: add custom customization loader/setter (style + font customization)