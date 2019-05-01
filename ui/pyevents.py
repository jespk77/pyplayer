def try_call_handler(event_name, cb, **kwargs):
	args = cb.__code__.co_varnames
	try: return cb(**{key: value for key, value in kwargs.items() if key in args})
	except Exception as e:
		import traceback
		print("ERROR", "While processing event '{}':\n".format(event_name), "".join(traceback.format_exception(e.__class__, e, e.__traceback__)))

from functools import wraps
class PyWindowEvents:
	def __init__(self, window):
		self._wd = window
		self._w = self._h = -1

	@property
	def block(self): raise AttributeError("Blocking is not possible for window events!")

	def WindowOpen(self, cb):
		""" Fired whenever the window is shown on screen for the first time
		 	- no callback keywords """
		@wraps(cb)
		def wrapper(): try_call_handler("[Open]", cb)
		return wrapper

	def WindowDestroy(self, cb):
		""" Fired before the window gets closed, used to clean up variables/close open handles
			WARNING: this is not the same as the 'WindowClosed' event, this one only fires when the window is actually getting destroyed
		 	- no callback keywords """
		event_name = "<Destroy>"
		@wraps(cb)
		def wrapper(event):
			if event.widget is self._wd._tk: try_call_handler(event_name, cb)
		self._wd._tk.bind(event_name, wrapper, add=True)
		return wrapper

	def WindowClose(self, cb):
		""" Fired when the user is trying to close the window, when this is bound the window won't be destroyed by default, to close it call 'destroy' on the window
		 	WARNING: this event is not equal to the 'WindowDestroy' event, this one is fired if the user wants to close it, the window might not actually get destroyed
		 	- no callback keywords """
		event_name = "WM_DELETE_WINDOW"
		@wraps(cb)
		def wrapper(): try_call_handler(event_name, cb)
		self._wd._tk.protocol(event_name, wrapper)
		return wrapper

	def WindowResize(self, cb):
		""" Fired if the window was resized
			callback keywords:
				* width: the new width of the window (in pixels)
				* height: the new height of the window (in pixels) """
		event_name = "<Configure>"
		self._w, self._h = self._wd.width, self._wd.height
		@wraps(cb)
		def wrapper(event):
			if event.widget is self._wd._tk and (self._w != event.width or self._h != event.height):
				try_call_handler(event_name, cb, width=event.width, height=event.height)
				self._w, self._h = event.width, event.height
		self._wd._tk.bind(event_name, wrapper, add=True)
		return wrapper

class PyElementEvents:
	def __init__(self, el):
		self._element = el
		self._w = self._h = -1

	@property
	def block(self):
		""" Return this property in an event handler method to prevent this event from being processed further """
		return "break"

	def MouseEnter(self, cb):
		""" Fired when the mouse pointer enters the element
		 	- no callback keywords """
		event_name = "<Enter>"
		@wraps(cb)
		def wrapper(event): return try_call_handler(event_name, cb)
		self._element._tk.bind(event_name, wrapper, add=True)
		return wrapper

	def MouseLeave(self, cb):
		""" Fired when the mouse pointer leaves the element
		 	- no callback keywords """
		event_name = "<Leave>"
		@wraps(cb)
		def wrapper(event): return try_call_handler(event_name, cb)
		self._element._tk.bind(event_name, wrapper, add=True)
		return wrapper

	def FocusGain(self, cb):
		""" Fired when this element gains input focus
		 	- no callback keywords """
		event_name = "<FocusIn>"
		@wraps(cb)
		def wrapper(event): return try_call_handler(event_name, cb)
		self._element._tk.bind(event_name, wrapper, add=True)
		return wrapper

	def FocusLoss(self, cb):
		""" Fired when this element loses input focus
		 	- no callback keywords """
		event_name = "<FocusOut>"
		@wraps(cb)
		def wrapper(event): return try_call_handler(event_name, cb)
		self._element._tk.bind(event_name, wrapper, add=True)
		return wrapper

	def ElementResize(self, cb):
		""" Fired when the size of this element has changed
		 	callback keywords:
		 		* height: the new height of the element (in pixels)
		 		* width: the new width of the element (in pixels) """
		event_name = "<Configure>"
		@wraps(cb)
		def wrapper(event):
			if self._w != event.width or self._h != event.height:
				self._w, self._h = event.width, event.height
				return try_call_handler(event_name, cb, width=event.width, height=event.height)
		self._element._tk.bind(event_name, wrapper, add=True)
		return wrapper


	_mouse_translations = {"left": "Button-1", "middle": "Button-2", "right": "Button-3"}
	def MouseClickEvent(self, button, doubleclick=False, include_children=False):
		""" Fired if the specified mouse button was clicked inside this widget, for double clicks add 'doubleclick=True'
			If both single and double click are bound, both are called on double click
		 \	- supported callback keywords:
		 		* x: the x position of where the mouse was clicked (relative to the top left of this element)
		 		* y: the y position of where the mouse was clicked (relative to the top left of this element) """
		bt = self._mouse_translations.get(button.lower())
		if bt: button = bt
		if doubleclick: button = "Double-" + button

		code = "<{}>".format(button)
		def wrapped(cb):
			def wrapper(event): return try_call_handler(code, cb, x=event.x, y=event.y)
			(self._element._tk.bind_all if include_children else self._element._tk.bind)(code, wrapper, add=True)
			return wrapper
		return wrapped

	def MouseScrollEvent(self, include_children=False):
		""" Fired when the mouse wheel was scrolled while the pointer is inside this widget
		 	- supported callback keywords:
		 	 	* delta: the amount the mouse wheel was scrolled """
		import sys
		code = ("<MouseWheel>",) if sys.platform == "win32" else ("<Button-4>", "<Button-5>")
		def wrapped(cb):
			def wrapper(event): return try_call_handler("".join(code), cb, delta=event.delta)
			for c in code: (self._element._tk.bind_all if include_children else self._element._tk.bind)(c, wrapper, add=True)
			return wrapper
		return wrapped

	_key_translations = {"all": "<Key>", "enter": "<Return>", "break": "<Cancel>", "shift": "<Shift_L>", "ctrl": "<Control_L>", "alt": "<Alt_L>", "pageup": "<Prior>", "pagedown": "<Next>", "capslock": "<Caps_Lock>", "numlock": "<Num_Lock>", "scrolllock": "<Scroll_Lock>", "backspace": "<BackSpace>"}
	def KeyEvent(self, key, include_children=False):
		""" Fired if the specified key was pressed or 'all' for all keypresses (only if this element currently has input focus)
		 	- supported callback keywords:
		 		* char: the key that was pressed (as character)
		 		* code: the keycode of the pressed key """
		ky = self._key_translations.get(key.lower())
		if ky: key = ky
		else: key = "<{}>".format(key.capitalize())

		def wrapped(cb):
			def wrapper(event): return try_call_handler(key, cb, char=event.char, code=event.keycode)
			(self._element._tk.bind_all if include_children else self._element._tk.bind)(key, wrapper, add=True)
			return wrapper
		return wrapped