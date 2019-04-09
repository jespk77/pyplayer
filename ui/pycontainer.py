from ui import pyelement
import tkinter

class WidgetLayer:
	def __init__(self, frame):
		self._frame = frame
		self._layers = {}

	def row(self, index, minsize=None, padding=None, weight=None):
		""" Customize row behavior at given index:
		 		- minsize: the minimun size this row must have; this row stops shrinking when it is this size (not applied when its empty)
		 		- padding: amount of padding set to the biggest element in this row
		 		- weight: how much this row should expand when the window is resized
		 	Returns itself for simplified updating """
		self._frame.grid_rowconfigure(index, minsize=minsize, pad=padding, weight=weight)
		return self

	def column(self, index, minsize=None, padding=None, weight=None):
		""" Customize column behavior at given index:
				- minsize: the minimun size this column must have; this column stops shrinking when it is this size (not applied when its empty)
				- padding: amount of padding set to the biggest element in this column
				- weight: how much this column should expand when the window is resized
			Returns itself for simplified updating """
		self._frame.grid_columnconfigure(index, minsize=minsize, pad=padding, weight=weight)
		return self

	def __getitem__(self, item):
		try: item = int(item)
		except ValueError: item = None
		if not item: raise ValueError("Index must be convertible to a number")
		elif item < 0: raise IndexError("Index cannot be negative")

		l = self._layers.get(item)
		if not l:
			l = PyFrame(self._frame, self._frame["layer_{}".format(item)])
			self._layers[item] = l
		return l

class BaseWidgetContainer:
	def __init__(self):
		self._elements = {}
		self._layer = WidgetLayer(self)

	@property
	def layer(self): return self._layer

	def place_widget(self, widget, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		if not isinstance(widget, pyelement.PyElement): raise ValueError("Passed widget must be a 'PyElement', not '{.__name__}'".format(type(widget)))

		self._elements[widget.widget_id] = widget
		widget.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
		return self._elements[widget.widget_id]

	def remove_widget(self, id):
		id = id.lower()
		prev_wd = self._elements.get(id)
		if prev_wd:
			try:
				prev_wd.grid_forget()
				prev_wd.destroy()
				del self._elements[id]
			except Exception as e: print("ERROR", "Destroying previously bound widget for '{}':".format(id), e)

class PyFrame(tkinter.Frame, BaseWidgetContainer):
	def __init__(self, root, configuration):
		tkinter.Frame.__init__(self, root)
		BaseWidgetContainer.__init__(self)
		self._cfg = configuration

	@property
	def configuration(self): return self._cfg

class PyLabelFrame(tkinter.LabelFrame, BaseWidgetContainer):
	def __init__(self, root, configuration):
		tkinter.LabelFrame.__init__(self, root)
		BaseWidgetContainer.__init__(self)
		self._cfg = configuration