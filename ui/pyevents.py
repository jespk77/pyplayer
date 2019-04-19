def try_call_handler(event_name, cb, **kwargs):
	args = cb.__code__.co_varnames
	try: cb(**{key: value for key, value in kwargs.items() if key in args})
	except Exception as e: print("ERROR", "While processing event '{}':".format(event_name), e)

from functools import wraps
class PyWindowEvents:
	#create, destroy, resize, moved pos
	def __init__(self, window):
		self._wd = window
		self._w = self._h = -1

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
			if event.widget is self._wd.window_handle: try_call_handler(event_name, cb)
		self._wd.window_handle.bind(event_name, wrapper, add=True)
		return wrapper

	def WindowClose(self, cb):
		""" Fired when the user is trying to close the window, when this is bound the window won't be destroyed by default, to close it call 'destroy' on the window
		 	WARNING: this event is not equal to the 'WindowDestroy' event, this one is fired if the user wants to close it, the window might not actually get destroyed
		 	- no callback keywords """
		event_name = "WM_DELETE_WINDOW"
		@wraps(cb)
		def wrapper(): try_call_handler(event_name, cb)
		self._wd.window_handle.protocol(event_name, wrapper)
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
			if event.widget is self._wd.window_handle and (self._w != event.width or self._h != event.height):
				try_call_handler(event_name, cb, width=event.width, height=event.height)
				self._w, self._h = event.width, event.height
		self._wd.window_handle.bind(event_name, wrapper, add=True)
		return wrapper