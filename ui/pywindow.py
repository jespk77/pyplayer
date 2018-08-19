import json, tkinter, ast

from ui import pyelement

class BaseWindow:
	""" Framework class for PyWindow and RootPyWindow, should not be created on its own """
	default_title = "PyWindow"
	invalid_cfg_keys = ["geometry"]

	def __init__(self, id):
		self._windowid = id
		self._elements = {}
		self._children = None
		self._dirty = False

		self.last_position = -1
		self.last_size = -1
		self._configuration_cache = {}
		self._configuration_error = False
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

	@property
	def dirty(self):
		""" Returns true if configuration has changed since last save """
		if self._dirty: return True

		for id, wd in self.widgets.items():
			if wd.dirty:
				print(self.window_id, "-> found dirty widget:", id)
				return True
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

	def load_configuration(self):
		""" (Re)load window configuration from file """
		try:
			file = open(self.cfg_filename, "r")
			try:
				self._configuration_cache = json.load(file)
				self._configuration_error = False
			except json.JSONDecodeError as e:
				self._configuration_error = True
				print("[BaseWindow.ERROR] Error parsing configuration json '{}':".format(self.cfg_filename), e)
			file.close()
			self._dirty = False
		except FileNotFoundError: print("[BaseWindow.ERROR] Cannot find configuration file:", self.cfg_filename)

		for id, wd in self.widgets.items():
			cfg = self._configuration_cache.get(id)
			if cfg is not None: wd.configuration = cfg

	def write_configuration(self):
		""" Write window configuration to file (if dirty) """
		if self._configuration_error: print("[BaseWindow.INFO] Skipping configuration writing since there was an error loading it")
		elif self.dirty:
			for id, wd in self.widgets.items():
				self._configuration_cache[id] = wd.configuration

			print("[PyWindow.INFO] Window is dirty, writing configuration to '{}'".format(self.cfg_filename))
			try:
				self._configuration_cache["geometry"] = self.geometry
				file = open(self.cfg_filename, "w+")
				json.dump(self._configuration_cache, file, indent=5, sort_keys=True)
				file.close()
				self._dirty = False
			except Exception as e: print("[BaseWindow.ERROR] error writing configuration file for '{}':".format(self.window_id), e)

	def add_widget(self, id, widget, **pack_args):
		""" Add new 'pyelement' widget to this window using passed (unique) identifier, add all needed pack parameters for this widget to the end
		 	(any widget already assigned to this identifier will be destroyed)
		 	Returns the bound widget if successful, False otherwise"""
		id = id.lower()
		if not isinstance(widget, pyelement.PyElement):
			print("[BaseWindow.ERROR] tried to create widget with id '{}' but it is not a valid widget: ".format(id), widget)
			return False

		self.remove_widget(id)
		self.widgets[id] = widget
		widget.id = id
		if self._configuration_cache is not None and id in self._configuration_cache:
			self.widgets[id].configuration = self._configuration_cache[id]
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
			print("[BaseWindow.ERROR] tried to create window with id '{}' but it is not a valid widget: {}".format(id, window))
			return False

		if self._children is None: self._children = {}
		success = self.remove_window(id)
		if not success: print("[BaseWindow.ERROR] Cannot close previously bound window with id '{}'".format(id))

		self._children[id] = window
		return self.children[id]

	def remove_window(self, id):
		""" Destroy and remove window assigned to passed identifier (has no effect if identifier was not bound) """
		id = id.lower()
		if self._children is not None and id in self._children:
			try:
				self._children[id].destroy()
				del self._children[id]
			except: return False
		return True

	def _cfg_lookup(self, key, value=""):
		if self._configuration_error: return ""

		k = key.split("::")
		if k[0] in self.widgets:
			d = self.widgets[k[0]]
			k = k[1:]
		else: d = self._configuration_cache

		while len(k) > 1:
			item = k.pop(0)
			if item in d: d = d[item]
			else: break

		key = k[0]
		if value is None:
			if key in d and not isinstance(d[key], str): return False
			del d[key]
			self.mark_dirty()
			return None
		elif value != "":
			if key in d and not isinstance(d[key], str): return False
			d[key] = value
			self.mark_dirty()
		try: return d.cget(key)
		except AttributeError: return d.get(key, "")

	def __getitem__(self, item):
		""" Get configuration option for this window/widget in this window or empty string if no such value was stored
		 	For a nested search in configuration seperate keys with '::' """
		value = self._cfg_lookup(item)
		try: return ast.literal_eval(value)
		except: return value

	def __setitem__(self, key, value):
		""" Set configuration option for this window/widget in this window, the change will be updated in the configuration file """
		if not self._configuration_error:
			if key in BaseWindow.invalid_cfg_keys: raise ValueError("Tried to set option '{}' which should not be changed manually".format(key))
			self._cfg_lookup(key, value)
		else: print("[BaseWindow.WARNING] Configuration was not loaded properly therefore any configuration updates are ignored")

	def __delitem__(self, key):
		""" Delete the configuration option for this window/widget in this window from the configuration file
		 	(the change will only be visible next time the window is created) """
		self.__setitem__(key, None)

class PyWindow(BaseWindow):
	""" Separate window that can be created on top of another window
		(it has its own configuration file separate from root configuration) """
	def __init__(self, root, id):
		self.tk = tkinter.Toplevel(root.root)
		BaseWindow.__init__(self, id)
		self.title = id

	@property
	def root(self):
		""" Get window manager for this window """
		return self.tk

	def load_configuration(self):
		""" (Re)load configuration from file """
		BaseWindow.load_configuration(self)
		self.geometry = self._configuration_cache.get("geometry")
		try: self.autosave_delay = int(self._configuration_cache.get("autosave_delay", "5"))
		except ValueError: self.autosave_delay = 5
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
		try: self.root.iconbitmap(value)
		except Exception as e: print("[PyWindow.ERROR] setting bitmap '{}': {}".format(value, e))

	@property
	def always_on_top(self):
		""" If true this window will always display be displayed above others """
		return self.root.wm_attributes("--topmost")
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
			try: self.autosave_delay = int(self._configuration_cache.get("autosave_delay", ""))
			except ValueError: pass

			if self.autosave_delay > 0: self._autosave = self.root.after(self._autosave_delay, self.try_autosave)
			else: self._autosave = None

class RootPyWindow(PyWindow):
	""" Root window for this application (should be the first created window and should only be created once, for additional windows use 'PyWindow' instead) """
	def __init__(self, id="root"):
		self.tk = tkinter.Tk()
		BaseWindow.__init__(self, id)
		self.title = BaseWindow.default_title