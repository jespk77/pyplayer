from ui import pyelement, pyconfiguration, pyevents
import tkinter

class BaseWidgetContainer:
	def __init__(self, container, tk, configuration):
		if configuration is None: configuration = pyconfiguration.Configuration()
		elif isinstance(configuration, dict): configuration = pyconfiguration.Configuration(configuration)
		else: raise TypeError("Configuration (when not None) must be a dictionary, not '{.__name__}'".format(type(configuration)))
		self._container = container
		self._event_handler = pyevents.PyElementEvents(self)
		self._tk = tk
		self._elements = {}
		self._subframes = []
		self._cfg = configuration
		self.load_configuration()

	@property
	def event_handler(self): return self._event_handler

	@property
	def configuration(self): return self._cfg
	def load_configuration(self):
		try: self._tk.configure(**{key: value for key, value in self._cfg.value.items() if not isinstance(value, dict)})
		except tkinter.TclError as e: print("ERROR", "Failed to load configuration:", e)

	def row(self, index, minsize=None, padding=None, weight=None):
		""" Customize row behavior at given index:
		 		- minsize: the minimun size this row must have; this row stops shrinking when it is this size (not applied when its empty)
		 		- padding: amount of padding set to the biggest element in this row
		 		- weight: how much this row should expand when the window is resized
		 	Returns itself for simplified updating """
		self._tk.grid_rowconfigure(index, minsize=minsize, pad=padding, weight=weight)
		return self

	def column(self, index, minsize=None, padding=None, weight=None):
		""" Customize column behavior at given index:
				- minsize: the minimun size this column must have; this column stops shrinking when it is this size (not applied when its empty)
				- padding: amount of padding set to the biggest element in this column
				- weight: how much this column should expand when the window is resized
			Returns itself for simplified updating """
		self._tk.grid_columnconfigure(index, minsize=minsize, pad=padding, weight=weight)
		return self

	def place_element(self, element, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		""" Place an element (must be a variant of PyElement) on this widget, use additional arguments to position it in this container
		 	row, rowspan: the row in the frame grid layout and how many rows it should cover
		 	column, columnspan: the column in the frame grid layout and how many columns it should cover
		 	Returns the added element """
		if isinstance(element, pyelement.PyElement):
			self._elements[element.widget_id] = element
			element._tk.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
			return self._elements[element.widget_id]
		else: raise ValueError("Placed element must be a 'PyElement', not '{.__name__}'".format(type(element)))

	def place_frame(self, frame, row=0, column=0, rowspan=1, columnspan=1, sticky="news"):
		""" Create another element container (must be a 'PyFrame' or any of its variants) inside this container,
			supported arguments and their behavior are the same as for elements
			Returns the index of the added container """
		if isinstance(frame, BaseWidgetContainer):
			self._subframes.append(frame)
			frame._tk.grid(row=row, column=column, rowspan=rowspan, columnspan=columnspan, sticky=sticky)
			return len(self._subframes) - 1
		else: raise ValueError("Placed frame must be a 'PyFrame', not '{.__name__}'".format(type(frame)))

	def remove_element(self, id):
		id = id.lower()
		prev_wd = self._elements.get(id)
		if prev_wd:
			try:
				prev_wd.grid_forget()
				prev_wd.destroy()
				del self._elements[id]
			except Exception as e: print("ERROR", "Destroying previously bound widget for '{}':".format(id), e)

	def show(self):
		self._tk.pack(fill="both", expand=True)

	def destroy(self):
		self._tk.destroy()

	def schedule(self, min=0, sec=0, ms=0, func=None, loop=False, **kwargs):
		self._container.schedule(min, sec, ms, func, loop, **kwargs)

	def __getitem__(self, item):
		""" Get the element that was assigned to given name, returns this element or None if nothing bound """
		return self._elements.get(item)

	def __setitem__(self, key, value): raise AttributeError("Cannot set or replace elements directly, use 'place_element' instead!")
	def __delitem__(self, key): raise AttributeError("Cannot delete elements directly, use 'remove_element' instead!")


frame_cfg = { "background": "black" }
class PyFrame(BaseWidgetContainer):
	def __init__(self, parent, configuration=None):
		BaseWidgetContainer.__init__(self, parent, tkinter.Frame(parent._tk, **frame_cfg), configuration)


label_cfg = { "foreground": "white" }
label_cfg.update(frame_cfg)
class PyLabelFrame(BaseWidgetContainer):
	def __init__(self, parent, configuration=None):
		BaseWidgetContainer.__init__(self, parent, tkinter.LabelFrame(parent._tk, **label_cfg), configuration)

	@property
	def label(self): return self._tk.cget("text")
	@label.setter
	def label(self, lbl): self._tk.configure(text=lbl)

canvas_cfg = { "highlightthickness": 0 }
canvas_cfg.update(frame_cfg)
class PyCanvas(BaseWidgetContainer):
	def __init__(self, parent, configuration=None):
		BaseWidgetContainer.__init__(self, parent, tkinter.Canvas(parent._tk, **canvas_cfg), configuration)

	@property
	def horizontal_command(self): return self._tk.cget("xscrollcommand")
	@horizontal_command.setter
	def horizontal_command(self, cmd): self._tk.configure(xscrollcommand=cmd)

	@property
	def vertical_command(self): return self._tk.cget("yscrollcommand")
	@vertical_command.setter
	def vertical_command(self, cmd): self._tk.configure(yscrollcommand=cmd)

	@property
	def horizontal_view(self): return self._tk.xview
	@property
	def vertical_view(self): return self._tk.yview

	@property
	def scrollregion(self): return self._tk.cget("scrollregion")
	@scrollregion.setter
	def scrollregion(self, rg): self._tk.configure(scrollregion=rg)

	def get_bounds(self, tag):
		""" Get the size (in pixels) of the element with the given tag, or 'all' for the total size """
		return self._tk.bbox(tag)


class PyScrollableFrame(PyFrame):
	_content_tag = "content_frame"
	_mouse_sensitivity = 100

	def __init__(self, parent, configuration=None):
		PyFrame.__init__(self, parent, configuration)
		self._scrollable = PyCanvas(self)
		self._content = PyFrame(self._scrollable)
		PyFrame.place_frame(self, self._scrollable)
		self._scrollable.row(0, weight=1).column(0, weight=1)
		self._scrollbar_x = self._scrollbar_y = None

		PyFrame.row(self, 0, weight=1)
		PyFrame.column(self, 0, weight=1)
		self._scrollable._tk.create_window((0,0), window=self._content._tk, anchor="center", tags=self._content_tag)

		@self._scrollable.event_handler.ElementResize
		def canvas_resize(width, height):
			if not self._scrollbar_x: self._scrollable._tk.itemconfigure(self._content_tag, width=width)
			if not self._scrollbar_y: self._scrollable._tk.itemconfigure(self._content_tag, height=height)
		@self._content.event_handler.ElementResize
		def content_resize(): self._scrollable.scrollregion = self._scrollable.get_bounds("all")
		@self.event_handler.MouseScrollEvent(include_children=True)
		def scroll_mouse(delta): self._scrollable._tk.yview_scroll(-(delta//self._mouse_sensitivity), "units")

	@property
	def content(self): return self._content

	def clear_content(self):
		for f in self._content._subframes:
			try: f.destroy()
			except Exception as e: print("ERROR", "Closing subframe", e)

	_horizontal_id = "horizontal_scrollbar"
	@property
	def scrollbar_x(self): return self._scrollbar_x is not None
	@scrollbar_x.setter
	def scrollbar_x(self, enable):
		if not self.scrollbar_x and enable:
			print("INFO", "Adding horizontal scrollbar")
			self._scrollbar_x = pyelement.PyScrollbar(self, self._horizontal_id)
			self._scrollbar_x.scrollcommand = self._scrollable.horizontal_view
			self._scrollbar_x.orientation = "horizontal"
			self._scrollable.horizontal_command = self._scrollbar_x.set_command
			PyFrame.place_element(self, self._scrollbar_x, row=1, sticky="ew")
			PyFrame.row(self, 1, minsize=20)

		if self.scrollbar_x and not enable:
			print("INFO", "Removing horizontal scrollbar")
			PyFrame.remove_element(self, self._horizontal_id)
			PyFrame.row(self, 1, minsize=0)
			self._scrollbar_x = None

	_vertical_id = "vertical_scrollbar"
	@property
	def scrollbar_y(self): return self._scrollbar_y is not None
	@scrollbar_y.setter
	def scrollbar_y(self, enable):
		if not self._scrollbar_y and enable:
			print("INFO", "Adding vertical scrollbar")
			self._scrollbar_y = pyelement.PyScrollbar(self, self._vertical_id)
			self._scrollbar_y.scrollcommand = self._scrollable.vertical_view
			self._scrollbar_y.orientation = "vertical"
			self._scrollable.vertical_command = self._scrollbar_y.set_command
			PyFrame.place_element(self, self._scrollbar_y, column=1, sticky="ns")
			PyFrame.column(self, 1, minsize=20)

		if self.scrollbar_x and not enable:
			print("INFO", "Removing vertical scrollbar")
			PyFrame.remove_element(self, self._vertical_id)
			PyFrame.column(self, 1, minsize=0)
			self._scrollbar_y = None

	def row(self, index, minsize=None, padding=None, weight=None): return self._content.row(index, minsize, padding, weight)
	def column(self, index, minsize=None, padding=None, weight=None): return self._content.column(index, minsize, padding, weight)
	def place_element(self, element, row=0, column=0, rowspan=1, columnspan=1, sticky="news"): return self._content.place_element(element, row, column, rowspan, columnspan, sticky)
	def place_frame(self, frame, row=0, column=0, rowspan=1, columnspan=1, sticky="news"): return self._content.place_frame(frame, row, column, rowspan, columnspan, sticky)
	def remove_element(self, id): return self._content.remove_element(id)
	def __getitem__(self, item): return self._content[item]