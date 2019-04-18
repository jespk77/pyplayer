from tkinter import ttk, font
import tkinter

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
	def __init__(self, parent, id):
		self._id = id
		self.parent = parent
		self._cfg = None
		self.load_configuration()

	@property
	def widget_id(self): return self._id
	@property
	def configuration(self): return self._cfg

	def load_configuration(self):
		self._cfg = self.parent.configuration.get_or_create(self.widget_id, {})
		self.configure(**self._cfg.value)

	# --- Forward declarations for tkinter operations, should not get called in a proper setup ---
	def grid(self, *args, **kwargs): raise RuntimeError("This element is invalid")
	def configure(self, *args, **kwargs): self.grid(*args, **kwargs)


element_cfg = { "background": background_color, "foreground": foreground_color }
# === ELEMENT ITEMS ===
class PyTextlabel(tkinter.Label, PyElement):
	""" Element for displaying a line of text """
	def __init__(self, master, id):
		tkinter.Label.__init__(self, master, **element_cfg)
		PyElement.__init__(self, master, id)
		self._string_var = self._img = None

	@property
	def text(self):
		""" Get the text that is currently displayed on this label (or empty string if no text set)
		 	* update: renamed from 'display_text' in previous versions """
		return self._string_var.get() if not self._string_var is None else ""
	@text.setter
	def text(self, value):
		""" Configure the text displayed on this label """
		if self._string_var is None:
			self._string_var = tkinter.StringVar()
			self.configure(textvariable=self._string_var)
		self._string_var.set(value)

	@property
	def image(self):
		""" Get the image currently displayed on this label (or None if not set) """
		return self._img
	@image.setter
	def image(self, img):
		""" Set the image that should be displayed, it should either be set to an instance of 'PyImage' or None to remove it """
		if img is not None and not isinstance(img, PyImage): raise ValueError("Image can only be set to 'PyImage' or None, not '{.__name__}'".format(type(img)))
		self._img = img
		self.configure(image=img)

input_cfg = { "insertbackground": foreground_color, "selectforeground": sel_foreground_color, "selectbackground": sel_background_color }
input_cfg.update(element_cfg)
class PyTextInput(tkinter.Entry, PyElement):
	def __init__(self, master, id):
		tkinter.Entry.__init__(self, master, disabledbackground=background_color, **input_cfg)
		PyElement.__init__(self, master, id)
		self._format_str = self._cmd = None
		self._input_length = 0
		self._strvar = tkinter.StringVar()
		self._input_cmd = self.register(self._on_input_key)
		self.bind("<Escape>", self._clear_input)
		self.configure(textvariable=self._strvar, validate="key", validatecommand=(self._input_cmd, "%P"))

	@property
	def accept_input(self): return self.cget("state") == "disabled"
	@accept_input.setter
	def accept_input(self, vl):
		""" Control whether the current input value can be adjusted """
		self.configure(state="normal" if vl else "disabled")

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

	def _clear_input(self, event=None): self.value = ""
	def _on_input_key(self, entry): return self._input_length == 0 or (len(entry) <= self._input_length and (not self._format_str or not self._format_str.search(entry)))

checkbox_cfg = { "activebackground": background_color, "activeforeground": foreground_color, "selectcolor": background_color }
checkbox_cfg.update(element_cfg)
class PyCheckbox(tkinter.Checkbutton, PyElement):
	def __init__(self, master, id):
		tkinter.Checkbutton.__init__(self, master, **checkbox_cfg)
		PyElement.__init__(self, master, id)
		self._value = tkinter.IntVar()
		self._desc = tkinter.StringVar()
		self.configure(variable=self._value, textvariable=self._desc)

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

button_cfg = { "activebackground": background_color, "activeforeground": foreground_color }
button_cfg.update(element_cfg)
class PyButton(tkinter.Button, PyElement):
	""" Element to create a clickable button  """
	def __init__(self, master, id):
		tkinter.Button.__init__(self, master, **button_cfg)
		PyElement.__init__(self, master, id)
		self._string_var = self._callback = self._image = None

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
	def command(self):
		""" Returns the callback that is currently assigned to when the button is pressed or None if nothing bound (or if it cannot be called) """
		if not callable(self._callback): self._callback = None
		return self._callback
	@command.setter
	def command(self, value):
		""" Set the callback that gets called when the button is pressed """
		self._callback = value
		self.configure(command=value)
	callback = command

class PyTextfield(tkinter.Text, PyElement):
	""" Element to display multiple lines of text, includes support for user input, images and markers/tags
	 	*Tags are configurable in the options with format 'tag'.'option': 'value' """
	front = "0.0"
	back = "end"
	def __init__(self, master, id):
		tkinter.Text.__init__(self, master, **input_cfg)
		PyElement.__init__(self, master, id)

		self._font = font.Font(family="segoeui", size="11")
		self.configure(font=self._font)
		self._accept_input = True
		self._boldfont = self._cmd = self._bd = None

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

	@property
	def command(self):
		""" Get the callback that is registered when any character is entered, returns None if not set """
		return self._cmd
	@command.setter
	def command(self, vl):
		if vl:
			if not callable(vl): raise ValueError("Callback must be callable!")
			self._bd = self.bind("<Key>", self._on_key_press)
		elif self._bd:
			self.unbind("<Key>", self._bd)
			self._bd = None
		self._cmd = vl

	def _on_key_press(self, event=None):
		if self._cmd:
			try: self._cmd()
			except Exception as e: print("ERROR", "Processing callback for textfield:", e)

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
		self._on_key_press()
		if not self.accept_input: self.configure(state="disabled")

	def delete(self, index1, index2=None):
		self.configure(state="normal")
		try: tkinter.Text.delete(self, index1, index2)
		except: raise
		finally: 
			self._on_key_press()
			if not self.accept_input: self.configure(state="disabled")

	#todo: add custom configuration loader/setter (tag style + font customization)

progress_cfg = { "background": "green", "troughcolor": background_color }
class PyProgressbar(ttk.Progressbar, PyElement):
	""" Widget that displays a bar indicating progress made by the application """
	def __init__(self, master, id):
		ttk.Progressbar.__init__(self, master)
		self._progress_var = tkinter.IntVar()
		self._style = ttk.Style()
		self._horizontal = True
		PyElement.__init__(self, master, id)
		self.configure(mode="determinate", variable=self._progress_var)

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
	@property
	def maximum(self):
		""" Returns the total size of the bar, if the progress is set to this value the bar is full (default is 100) """
		return self.cget("maximum")
	@maximum.setter
	def maximum(self, value): self.configure(maximum=value)

	#todo: add custom configuration loader/setter (style customization)

class PyScrollbar(tkinter.Scrollbar, PyElement):
	def __init__(self, master, id):
		tkinter.Scrollbar.__init__(self, master)
		PyElement.__init__(self, master, id)

	@property
	def scrollcommand(self): return
	@scrollcommand.setter
	def scrollcommand(self, value): self.configure(command=value)

list_cfg = { "selectbackground": background_color, "selectforeground": highlight_color }
list_cfg.update(element_cfg)
class PyItemlist(tkinter.Listbox, PyElement):
	""" A list of options where the user can select one or more lines """
	def __init__(self, master, id):
		tkinter.Listbox.__init__(self, master, selectmode="single", **list_cfg)
		PyElement.__init__(self, master, id)
		self.list_var = self._items = self._font = None

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

	def get_item_from_event(self, event):
		""" Get the element at the mouse pointer when processing event from bound callback """
		return self._items[self.nearest(event.y)]

	#todo: add custom customization loader/setter (style + font customization)

class PyImage:
	""" Placeholder to avoid type errors in the rest of the program """
	#todo: add improved version in separate module
	def __init__(self, file=None, url=None, bin_file=None): pass
	def write(self, filename, format=None, from_coords=None): pass