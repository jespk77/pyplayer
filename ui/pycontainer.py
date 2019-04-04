from ui import pyelement
import tkinter

class BaseWidgetContainer:
	def __init__(self, window):
		self._window = window
		self._elements = {}

	def __getitem__(self, item): return self._elements.get(item.lower())
	def __setitem__(self, key, value): raise TypeError("Cannot update widgets directly, use 'set_widget' to do this")

	@property
	def items(self): return self._elements.copy()

	def set_widget(self, id, widget, initial_cfg=None, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		""" Add given widget to this container, location for the widget on this window can be customized with the various parameters
			If there is no widget specified, the widget bound to given id will be destroyed. Otherwise the new widget will be replace the old onw """
		id = id.lower()
		wd = self[id]
		if wd is not None:
			print("INFO", "Removing existing widget bound to id")
			self._window.after(.1, wd.destroy)
			del self._elements[id]
		if widget is None: return None
		elif not isinstance(widget, pyelement.PyElement): raise TypeError("Can only create widgets from 'PyElement' instances, not from '{}'".format(type(widget).__name__))

		if widget is None: return widget
		self._elements[id] = widget
		widget.id = id
		widget.window = self
		if initial_cfg is None: initial_cfg = {}

		cfg = self._window._configuration.get(id)
		if cfg is not None: initial_cfg.update(cfg)
		self._elements[id].configuration = initial_cfg
		self._elements[id].grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
		return self[id]