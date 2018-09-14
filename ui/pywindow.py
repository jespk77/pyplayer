import tkinter, os, sys

from ui import pyelement, pyconfiguration

class BaseWindow:
	""" Framework class for PyWindow and RootPyWindow, should not be created on its own """
	default_title = "PyWindow"
	invalid_cfg_keys = ["geometry"]

	def __init__(self, id, initial_cfg):
		self._windowid = id
		self._elements = {}
		self._children = None
		self._dirty = False

		self.last_position = -1
		self.last_size = -1
		self._configuration = pyconfiguration.Configuration(initial_value=initial_cfg, filepath=self.cfg_filename)
		self.load_configuration()

	@property
	def root(self): return None
	@property
	def window_id(self):
		""" The (unique) identifier for this window, this cannot change once the window is created """
		return self._windowid
	@property
	def cfg_filename(self):
		""" The filepath of the configuration file (created using window identifier)"""
		return ".cfg/" + self.window_id.lower()
	@property
	def widgets(self):
		""" All elements that are present inside this window """
		return self._elements
	@property
	def children(self):
		""" All windows that are active and have this window as parent """
		if self._children is None: self._children = {}
		return self._children
	def load_configuration(self): pass

	@property
	def dirty(self):
		""" Returns true if configuration has changed since last save """
		if self._dirty: return True

		for id, wd in self.widgets.items():
			if wd.dirty: return True
		return False

	@property
	def geometry(self): return None
	@property
	def title(self): return None
	@property
	def icon(self): return None
	@property
	def always_on_top(self): return False

	def mark_dirty(self, event=None):
		""" Mark this window as dirty, event parameter only used for tkinter event handling """
		if event is not None:
			if event.widget is self.root:
				if self.last_position != -1 and self.last_size != -1: self._dirty = self._dirty or self.last_position != (event.x * event.y) or self.last_size != (event.height * event.width)
				self.last_position = event.x * event.y
				self.last_size = event.height * event.width
		else: self._dirty = True

	def write_configuration(self):
		""" Write window configuration to file (if dirty) """
		if self._configuration.error: print("INFO", "Skipping configuration writing since there was an error loading it")
		elif self.dirty:
			for id, wd in self.widgets.items():
				if wd._write: self._configuration[id] = wd.configuration
				wd._dirty = False

			print("INFO", "Window is dirty, writing configuration to '{}'".format(self.cfg_filename))
			try:
				self._configuration["geometry"] = self.geometry
				self._configuration.write_configuration()
				self._dirty = False
			except Exception as e: print("ERROR", "Error writing configuration file for '{}':".format(self.window_id), e)

	def add_widget(self, id, widget, initial_cfg=None, **pack_args):
		""" Add new 'pyelement' widget to this window using passed (unique) identifier, add all needed pack parameters for this widget to the end
		 	(any widget already assigned to this identifier will be destroyed)
		 	Returns the bound widget if successful, False otherwise"""
		id = id.lower()
		if not isinstance(widget, pyelement.PyElement):
			print("ERROR", "Tried to create widget with id '{}' but it is not a valid widget: ".format(id), widget)
			return False

		self.remove_widget(id)
		self.widgets[id] = widget
		widget.id = id
		if initial_cfg is None: initial_cfg = {}

		try:
			cfg = self._configuration.get(id)
			if cfg is not None: initial_cfg.update(cfg.to_dict()); cfg = initial_cfg
			elif initial_cfg is not None: cfg = initial_cfg

			if cfg is not None: self.widgets[id].configuration = cfg
		except (AttributeError, TypeError) as e: print("ERROR", "Cannot assign configuration to created widget '{}':".format(id), e)

		self.widgets[id].pack(pack_args)
		return self.widgets[id]

	def remove_widget(self, id):
		""" Destroy and removes widget that was assigned to the passed identifier (has no effect if identifier was not bound)
		 	Returns true if the identifier was bound and the widget has been removed """
		id = id.lower()
		if id in self.widgets:
			if id != self.window_id:
				self.widgets[id].destroy()
				del self.widgets[id]
				return True
			else: raise NameError("[BaseWindow.ERROR] Cannot remove self from widgets!")
		return False

	def add_window(self, id, window):
		""" Adds new child window to this window using passed (unique) identifier
		 	(any window already assigned to this identifier will be destroyed)
		 	Returns the bound window if successful, False otherwise """
		id = id.lower()
		if not isinstance(window, BaseWindow):
			print("ERROR", "Tried to create window with id '{}' but it is not a valid widget: {}".format(id, window))
			return False

		if self._children is None: self._children = {}
		success = self.remove_window(id)
		if not success: print("ERROR", "Cannot close previously bound window with id '{}'".format(id))

		self._children[id] = window
		return self.children[id]

	def remove_window(self, id):
		""" Destroy and remove window assigned to passed identifier (has no effect if identifier was not bound) """
		id = id.lower()
		if self._children is not None and id in self._children:
			try:
				self._children[id].destroy()
				del self._children[id]
			except AttributeError: return False
			except Exception as e: print("ERROR", "Couldn't destroy window '{}' properly: ".format(id), e); return False
		return True

	def get_or_create(self, item, default=None):
		""" Get configuration option if it is currently set,
				- when this option is not set and a 'default' is given, this will be used as value for this option """
		i = self._configuration.get(item)
		if i is None and default is not None: self._configuration[item] = default
		return self._configuration.get(item)

	def __getitem__(self, item):
		""" Get configuration option for this window/widget in this window or None if no such value was stored
		 	For a nested search in configuration seperate keys with '::' """
		vl = self._configuration[item]
		try: return vl.to_dict()
		except AttributeError: return vl.value

	def __setitem__(self, key, value):
		""" Set configuration option for this window/widget in this window, the change will be updated in the configuration file """
		if not self._configuration.error:
			if key in BaseWindow.invalid_cfg_keys: raise ValueError("Tried to set option '{}' which should not be changed manually".format(key))
			self._configuration[key] = value
			key = key.split("::", maxsplit=1)
			if len(key) > 1 and key[0] in self.widgets:
				try: self.widgets[key[0]][key[1]] = value
				except Exception as e: print("ERROR", "Error configuring option '{}': ".format(key), e)
			self.mark_dirty()
		else: print("WARNING", "Configuration was not loaded properly therefore any configuration updates are ignored")

	def __delitem__(self, key):
		""" Delete the configuration option for this window/widget in this window from the configuration file
		 	(the change will only be visible next time the window is created) """
		self.__setitem__(key, None)

class PyWindow(BaseWindow):
	""" Separate window that can be created on top of another window
		(it has its own configuration file separate from root configuration) """
	def __init__(self, root, id, initial_cfg=None):
		self.tk = tkinter.Toplevel(root.root)
		BaseWindow.__init__(self, id, initial_cfg)
		self.title = id

	@property
	def root(self):
		""" Get window manager for this window """
		return self.tk

	@property
	def transient(self): return None
	@transient.setter
	def transient(self, value):
		""" Sets this window to be transient, connected to its parent and is minimized when the parent is minimized
		 	(Cannot be set on root window, also cannot be disabled once set) """
		if value:
			if not isinstance(self.tk, tkinter.Toplevel): raise TypeError("Can only set transient on regular window")
			self.root.transient()

	@property
	def hidden(self): return self.root.state() == "withdrawn"
	@hidden.setter
	def hidden(self, value):
		if value: self.root.withdraw()
		else: self.root.deiconify()

	def toggle_hidden(self):
		self.hidden = not self.hidden

	def load_configuration(self):
		""" (Re)load configuration from file """
		self.geometry = self._configuration.get("geometry", "")
		self.autosave_delay = int(self._configuration["autosave_delay"])
		self.root.bind("<Configure>", self.mark_dirty)
		self.root.bind("<Destroy>", self.try_autosave)

	def bind(self, sequence, callback=None, add=None):
		sequence = sequence.split("&&")
		for s in sequence: self.root.bind(s, callback, add)
		return self

	def unbind(self, sequence, funcid=None):
		sequence = sequence.split("&&")
		for s in sequence: self.root.unbind(s, funcid)
		return self

	@property
	def autosave_delay(self):
		""" Time interval (in minutes) between automatic save of window configuration to file, returns 0 if disabled """
		try: return int(self._autosave_delay / 60000)
		except AttributeError: return 0
	@autosave_delay.setter
	def autosave_delay(self, value):
		""" Set time interval (in minutes) between autosaves (if dirty), set to 0 to disable """
		if self.autosave_delay != value:
			self._autosave_delay = max(0, value * 60000)
			try: self.root.after_cancel(self._autosave)
			except (TypeError, AttributeError): pass

			if value > 0: self._autosave = self.root.after(self._autosave_delay, self.try_autosave)
			else: self._autosave = None

	@property
	def geometry(self):
		""" Get window geometry string, returned as '{width}x{height}+{x_pos}+{y_pos}' where {width} and {height} are positive and {x_pos} and {y_pos} may be negative """
		return self.root.geometry()
	@geometry.setter
	def geometry(self, value):
		""" Update geometry for this window (use specified geometry format) """
		self.root.geometry(value)

	@property
	def title(self):
		""" Get current window title """
		return self.root.title()
	@title.setter
	def title(self, value):
		""" Update current window title """
		self.root.title(value)

	@property
	def icon(self):
		""" Get current window icon """
		return self.root.iconbitmap()
	@icon.setter
	def icon(self, value):
		""" Set window icon """
		if "linux" in sys.platform:
			path = os.path.dirname(os.path.realpath(__file__))
			try: self.root.tk.call("wm", "iconphoto", self.root._w, pyelement.PyImage(file=os.path.join(path, os.pardir, value + ".png")))
			except Exception as e: print("ERROR", "Setting icon bitmap {}".format(e))
		elif "win" in sys.platform: self.root.iconbitmap(value + ".ico")

	@property
	def always_on_top(self):
		""" If true this window will always display be displayed above others """
		return bool(self.root.wm_attributes("-topmost"))
	@always_on_top.setter
	def always_on_top(self, value):
		""" Set this window to be always above others """
		self.root.wm_attributes("-topmost", "1" if value else "0")

	def focus_followsmouse(self):
		""" The widget under mouse will get focus, cannot be disabled! """
		self.root.tk_focusFollowsMouse()

	def start(self):
		""" Initialize and start GUI """
		self.root.mainloop()

	def after(self, s, *args):
		self.root.after(int(s * 1000) if s < 1000 else s, *args)

	def try_autosave(self, event=None):
		""" Autosave configuration to file (if dirty) """
		self.write_configuration()
		if event is None:
			self.autosave_delay = int(self._configuration["autosave_delay"])

			if self.autosave_delay > 0: self._autosave = self.root.after(self._autosave_delay, self.try_autosave)
			else: self._autosave = None

class RootPyWindow(PyWindow):
	""" Root window for this application (should be the first created window and should only be created once, for additional windows use 'PyWindow' instead) """
	def __init__(self, id="root", initial_cfg=None):
		self.tk = tkinter.Tk()
		BaseWindow.__init__(self, id, initial_cfg)
		self.title = BaseWindow.default_title