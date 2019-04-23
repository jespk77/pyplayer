import os
import sys
import tkinter
import weakref

from ui import pyimage, pyconfiguration, pycontainer, pyevents

class PyWindow:
	""" Framework class for windows, they have to be created with a valid root """
	def __init__(self, parent, id, initial_cfg=None, cfg_file=None):
		if parent is not None:
			if not isinstance(parent, PyWindow): raise ValueError("Parent window must be a PyWindow, not '{.__name__}'".format(type(parent)))
			self._tk = tkinter.Toplevel(parent._tk)
		else: self._tk = tkinter.Tk()

		self._event_handler = pyevents.PyWindowEvents(self)
		self.hidden = True
		self._windowid = id
		self.title = "PyWindow: " + self._windowid
		self.icon = ""

		self._children = weakref.WeakValueDictionary()
		self._tick_operations = {}
		self._autosave, self._autosave_delay = None, 0

		if cfg_file is None: cfg_file = ".cfg/" + self._windowid.lower()
		elif not cfg_file.startswith(".cfg/"): cfg_file = ".cfg/" + cfg_file
		self._configuration = pyconfiguration.ConfigurationFile(filepath=cfg_file, cfg_values=initial_cfg)
		self._content = pycontainer.PyFrame(self, self._configuration.get_or_create("content", {}))
		self.create_widgets()
		self._content.show()

	def create_widgets(self):
		""" Can be used in subclasses to separate widget creation and placement from the rest of the program,
			this method is called after the main window is created and configuration files have been loaded """
		pass

	# ===== Window Properties =====
	@property
	def window_id(self):
		""" The (unique) identifier for this window, this cannot change once the window is created """
		return self._windowid
	@property
	def content(self):
		""" Get the container for this window that all elements are placed in """
		return self._content
	@property
	def event_handler(self):
		""" Get the event handler for this window, this can be used to bind callbacks to various events """
		return self._event_handler
	@property
	def configuration(self):
		""" Get the configuration object for this window (this also has access to all configuration objects in this window's child elements """
		return self._configuration

	@property
	def is_alive(self):
		""" Returns true when this window has not been closed """
		return self._tk.winfo_exists()
	@property
	def floating(self): return None
	@floating.setter
	def floating(self, value):
		""" Sets this window to be floating: it's connected to its parent and its behavior is mirrored from the parent
		 	* update: this was renamed from the 'transient' parameter in the previous version """
		if value:
			try: self._tk.wm_transient(self._tk.master)
			except Exception as e: print("ERROR", "Failed to set window as transient, caused by:", e)

	@property
	def decorator(self):
		""" Set true to prevent the window from being decorated; only the content will be visible
		 	Useful for making custom window decorators """
		return self._tk.wm_overrideredirect()
	@decorator.setter
	def decorator(self, vl):
		self._tk.wm_overrideredirect(not vl)

	@property
	def hidden(self):
		""" Returns True if the window is currently hidden """
		return self._tk.wm_state() == "withdrawn"
	@hidden.setter
	def hidden(self, value):
		""" Hide/unhide the window, if the window is hidden all traces are removed. Can only be unhidden by updating this property """
		if value: self._tk.wm_withdraw()
		else: self._tk.wm_deiconify()
	def toggle_hidden(self): self.hidden = not self.hidden

	@property
	def screen_height(self):
		""" Get the height in pixels for the display the window is on """
		return self._tk.winfo_screenheight()
	@property
	def screen_width(self):
		""" Get the width in pixels for the display the window is on """
		return self._tk.winfo_screenwidth()
	@property
	def width(self):
		""" Get the width of this window in pixels """
		return self._tk.winfo_width()
	@width.setter
	def width(self, vl):
		""" Customize the width of this window, in most cases this value does not need to be set:
				it automatically updates to fit all widgets and the previously set value (when resized)
			* update: width clamped between 0 and screen_width """
		self._tk.configure(width=max(0, min(vl, self.screen_width)))

	@property
	def height(self):
		""" Get the height of this window in pixels """
		return self._tk.winfo_height()
	@height.setter
	def height(self, vl):
		""" Customize the height of this window, in most cases this value does not need to be set:
				it automatically updates to fit all widgets and the previously set value (when resized)
		 	* update: height clamped between 0 and screen_height """
		self._tk.configure(height=max(0, min(vl, self.screen_height)))

	@property
	def title(self):
		""" Get current window title """
		return self._tk.wm_title()
	@title.setter
	def title(self, value):
		""" Update current window title """
		self._tk.wm_title(value)

	@property
	def icon(self):
		""" Get current window icon """
		return self._tk.wm_iconbitmap()

	@icon.setter
	def icon(self, value):
		""" Set window icon, this must be a valid path to an image
			(file extension may be omitted, it is automatically selected based on platform: .iso (Windows), .png (Linux))
		 	* update: errors are no longer raised, instead they are only written to log (aside from also not being updated) """
		if not value: value = "assets/blank"

		try:
			if "linux" in sys.platform:
				path = os.path.dirname(os.path.realpath(__file__))
				self._tk.tk.call("wm", "iconphoto", self._tk._w,
									pyimage.PyImage(file=os.path.join(path, os.pardir, value + ".png")))
			elif "win" in sys.platform: self._tk.iconbitmap(value + ".ico")
		except Exception as e: print("ERROR", "Setting icon bitmap {}".format(e)); raise

	# ===== Base Operations =====
	def load_configuration(self):
		""" (Re)load configuration from file """
		self._configuration.load()
		self._tk.wm_geometry(self._configuration.get("geometry").value)
		self.autosave_delay = self._configuration.get_or_create("autosave_delay", 5)

	def write_configuration(self):
		""" Write window configuration to file (if dirty) """
		self._configuration["geometry"] = self._tk.wm_geometry()
		self._configuration["autosave_delay"] = self._autosave_delay
		self._configuration.save()

	def open_window(self, id, window):
		""" Adds new child window to this window using passed (unique) identifier
		 	(any window already assigned to this identifier will be destroyed)
		 	Returns the bound window if successful, None otherwise
		 	* update: it is no longer an error if a previously open window cannot be closed
		 	* update: now returns None instead of False """
		id = id.lower()
		self.close_window(id)
		window.id = id
		self._children[id] = window
		window.content.show()
		window.hidden = False
		return self._children.get(id)

	def close_window(self, id):
		""" Destroy and remove window assigned to passed identifier (has no effect if identifier was not bound)
		 	Returns True if call was successful, False otherwise """
		id = id.lower()
		wd = self._children.get(id)
		if self._children is not None and wd is not None:
			try: wd.destroy()
			except Exception as e: print("ERROR", "Couldn't destroy window '{}' properly: ".format(id), e); return False
		return True

	def get_window(self, id):
		""" Get the child window that was bound to given id, returns None if the id wasn't bound """
		id = id.lower()
		wd = self._children.get(id)
		return wd if wd.is_alive else None

	@property
	def always_on_top(self):
		""" If true this window will always display be displayed above others """
		return bool(self._tk.wm_attributes("-topmost"))
	@always_on_top.setter
	def always_on_top(self, value):
		""" Set this window to be always above others """
		self._tk.wm_attributes("-topmost", "1" if value else "0")

	def focus_followsmouse(self):
		""" The widget under mouse will get focus, cannot be disabled once set """
		self._tk.tk_focusFollowsMouse()

	def center_window(self, width, height):
		""" Center this widget on screen, any previously set geometry is overwritten """
		self._tk.wm_geometry("{}x{}+{}+{}".format(width, height, (self.screen_width // 2) - (width // 2), (self.screen_height // 2) - (height // 2)))

	def schedule(self, min=0, sec=0, ms=0, func=None, loop=False, **kwargs):
		""" Schedule an operation to be executed at least after the given time, all registered callbacks will stop when the window is closed
		 	 -	Amount of time to wait can be specified with minutes (keyword 'min'), seconds (keyword 'sec') and/or milliseconds (keyword 'ms')
		 	 -	The argument passed to func must be callable and accept the extra arguments passed to this function
		 	 -	The function can be called repeatedly by setting 'loop' to true;
		 	 		in this case it will be called repeatedly after the given time until an error occurs or the callback returns False
			* update: delay is allowed to be 0, in this case the callback is executed as soon as possible """
		if not callable(func): raise ValueError("'func' argument must be callable!")
		delay = (min * 60000) + (sec * 1000) + ms
		if delay < 0: raise ValueError("Delay cannot be smaller than 0")

		if loop: self._tk.after(delay, self._create_rescheduled_task(func, delay), kwargs)
		else: self._tk.after(delay, func, *kwargs.values())

	def _create_rescheduled_task(self, fn, delay):
		def _call_task(kwargs):
			try:
				fn(**kwargs)
				self._tk.after(delay, _call_task, kwargs)
			except Exception as e:
				print("WARNING", "During processing of scheduled task '{}', it won't be rescheduled!".format(fn.__name__))
				print("ERROR", "While calling scheduled task '{}':".format(fn.__name__), e)
		return _call_task

	def window_tick(self, date):
		""" Called every second with the current date on all windows, can be used to update elements inside it
		 	Note: make sure to call the super method as well if you want the call to propagate! """
		if self.is_alive:
			for c in self._children.values(): c.window_tick(date)

	def destroy(self):
		""" Close (destroy) this window and all its children """
		for cd in self._children.values():
			if cd.is_alive: cd.destroy()
		self._tk.destroy()

	def force_update(self):
		""" Forces background updates that would normally only happen when the program is idle """
		self._tk.update_idletasks()

import datetime
class PyTkRoot(PyWindow):
	""" Root window for this application (should be the first created window and should only be created once, for additional windows use 'PyWindow' instead) """
	def __init__(self, name="pyroot"):
		PyWindow.__init__(self, parent=None, id=name)
		self.decorator = False
		self.hidden = False
		self.schedule(sec=1, loop=True, func=self.window_tick, date=datetime.datetime.today())

	def open_window(self, id, window):
		""" Open connected window, after this is called the root window will automatically be set to hidden """
		PyWindow.open_window(self, id, window)
		self.hidden = True

	def start(self):
		""" Initialize and start GUI """
		try: self._tk.mainloop()
		except KeyboardInterrupt:
			print("INFO", "Received keyboard interrupt, closing program...")
			self._tk.destroy()